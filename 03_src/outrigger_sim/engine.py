"""SimEngine protocol and engine-independent snapshot type (no physics engine imported).

``00_docs/03_chrono/chrono_build_plan.md`` 3.1-3.3 and R16. Everything outside ``chrono/``
(``scenarios``, ``runner``, ``record``, ``verify``, ``sensors/imu_model``, ``control``)
talks to a physics engine only through :class:`SimEngine`, so a MuJoCo backend can later
implement the same protocol. This module must never import ``pychrono``.

Rules every implementation follows:

* **Physics step vs control period.** :meth:`SimEngine.step` advances exactly one physics
  step of :attr:`SimEngine.dt_s` (for example 1e-4 s). The control period (20 ms, assumed)
  belongs to the runner, which calls ``step()`` repeatedly between two commands. All times
  are SI seconds of simulation time.
* **Zero-order hold.** :meth:`SimEngine.apply_command` stores the command; every following
  ``step()`` uses it until the next ``apply_command``. After :meth:`SimEngine.reset` the
  held command is zero speed on every leg (legs locked).
* **Saturation inside the engine.** Speed limits, stroke ends and the 210 bar force
  cut-off are applied by the actuator model on every physics step, never only once per
  control period (9.4 kN overshoot otherwise, plan S6). Any finite command is accepted.
* **Truth is not an observation.** :meth:`SimEngine.measure` returns what the sensors see
  (ideal values at the sensor locations; noise, bias and delay are added by ``sensors``).
  :meth:`SimEngine.truth` is for recording and verification only and is never passed to a
  controller; the runner enforces this.
* **Snapshots (R16).** :meth:`SimEngine.snapshot` captures the complete dynamic state
  (bodies, motors, ``s_ref``, ground bushings, time, held command) in a :class:`Snapshot`.
  :meth:`SimEngine.restore` accepts it only from the same engine and model with the same
  ``Params.sha256`` (auger level and overrides included) and raises
  :class:`SnapshotMismatchError` otherwise, leaving the engine unchanged. Restoring and then
  stepping must reproduce the uninterrupted run (S0: position difference <= 1e-12 m).
  Saving a snapshot to disk (npz) is the ``record`` module's job.
* **Lifecycle.** Construct -> :meth:`SimEngine.reset` or :meth:`SimEngine.restore` ->
  step / command / measure ... -> :meth:`SimEngine.close`. State methods called before the
  first reset or restore raise :class:`EngineNotReadyError`, after close
  :class:`EngineClosedError`. ``close()`` is idempotent. The identity properties
  (``dt_s``, ``params_sha256``, ``info``, ``is_closed``) stay readable after close. Use
  ``contextlib.closing(engine)`` for a ``with`` block.

The auger level is not a reset argument: it is part of :class:`outrigger_sim.params.Params`
(and of ``Params.sha256``), so one engine instance simulates one level. Build another engine
from ``load_params(level=...)`` for another level.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.signals import Command, Measurements, TruthState

# Params.sha256 is a lowercase SHA-256 hex digest.
_SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")

# numpy dtype kinds allowed in a snapshot payload: bool, signed int, unsigned int, float.
# Object arrays would need pickle to save (record loads with allow_pickle=False).
_PAYLOAD_DTYPE_KINDS = frozenset("biuf")


# --- errors ------------------------------------------------------------------------------


class SnapshotMismatchError(ValueError):
    """A snapshot was taken by another engine, model or parameter set than the target."""

    def __init__(self, field_name: str, expected: str, actual: str) -> None:
        super().__init__(
            f"snapshot {field_name} {actual!r} does not match the engine's {expected!r}"
        )
        self.field_name = field_name
        self.expected = expected
        self.actual = actual


class EngineStateError(RuntimeError):
    """An engine method was called in a lifecycle state that does not allow it."""


class EngineNotReadyError(EngineStateError):
    """A state method was called before the first ``reset()`` or ``restore()``."""


class EngineClosedError(EngineStateError):
    """A method other than ``close()`` or an identity property was used after ``close()``."""


# --- value types -------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineInfo:
    """Which engine produced a state; snapshots restore only into the same name and model.

    Attributes:
        name: Engine package, for example ``"pychrono"`` or ``"mujoco"``.
        version: Engine version as reported by the package, for example ``"10.0.0"``.
            Recorded only; it does not block a restore.
        model: Model family inside the engine, for example ``"L1"`` or ``"L2b_NSC"``. The
            payload layout depends on it.
    """

    name: str
    version: str
    model: str


class AnalyticStart(StrEnum):
    """Analytic initial condition for :meth:`SimEngine.reset` (plan 2, initial-condition rules).

    A settled state saved as a :class:`Snapshot` is the other kind of start.
    """

    ON_PADS = "on_pads"
    """Static solution on four pads: body position and attitude from the V2 penetration and
    V3 attitude reference values, ground bushings created with zero tangential force."""
    ON_CRAWLER = "on_crawler"
    """Legs fully retracted (0 m), body in the crawler settle attitude."""


def _frozen_payload(payload: Mapping[str, ArrayLike]) -> Mapping[str, NDArray[Any]]:
    """Copy each payload entry into a read-only numeric array behind a read-only mapping."""
    frozen: dict[str, NDArray[Any]] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"snapshot payload keys must be non-empty strings, got {key!r}")
        array = np.array(value, copy=True)
        if array.dtype.kind not in _PAYLOAD_DTYPE_KINDS:
            raise ValueError(
                f"snapshot payload {key!r}: dtype {array.dtype} is not bool, int or float"
            )
        array.setflags(write=False)
        frozen[key] = array
    return MappingProxyType(frozen)


@dataclass(frozen=True, eq=False)
class Snapshot:
    """Complete dynamic state of one engine at one instant (R16); engine-independent container.

    Only the engine that wrote :attr:`payload` interprets it. The other fields are typed so
    that ``record`` can save and check them without knowing the engine.

    Attributes:
        engine: Engine name, version and model that produced the state.
        params_sha256: ``Params.sha256`` of the parameters the engine was built from.
        time_s: Simulation time of the state (s).
        held_command: Command held at that instant; :meth:`SimEngine.restore` holds it again.
        payload: Engine-specific state arrays by name (bodies, motors, ``s_ref``, bushing
            anchors and states, ...). Copied on construction into read-only bool, int or
            float arrays, so the snapshot can be saved to npz without pickle.
    """

    engine: EngineInfo
    params_sha256: str
    time_s: float
    held_command: Command
    payload: Mapping[str, NDArray[Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.params_sha256, str) or not _SHA256_HEX_PATTERN.fullmatch(
            self.params_sha256
        ):
            raise ValueError(f"params_sha256 must be a SHA-256 hex digest: {self.params_sha256!r}")
        if isinstance(self.time_s, bool) or not math.isfinite(self.time_s):
            raise ValueError(f"time_s must be a finite number of seconds: {self.time_s!r}")
        object.__setattr__(self, "time_s", float(self.time_s))
        object.__setattr__(self, "payload", _frozen_payload(self.payload))


def ensure_snapshot_compatible(
    snapshot: Snapshot, *, engine: EngineInfo, params_sha256: str
) -> None:
    """Check that ``snapshot`` may be restored into an engine; call before touching state.

    Engine name and model must match because the payload layout depends on them; the
    parameter fingerprint must match so that a stale settled state is never reused (plan
    risk 23). The engine version is not compared.

    Args:
        snapshot: State to restore.
        engine: Identity of the target engine.
        params_sha256: ``Params.sha256`` of the target engine.

    Raises:
        SnapshotMismatchError: Name, model or fingerprint differ (the first that differs).
    """
    checks = (
        ("engine name", engine.name, snapshot.engine.name),
        ("engine model", engine.model, snapshot.engine.model),
        ("params_sha256", params_sha256, snapshot.params_sha256),
    )
    for field_name, expected, actual in checks:
        if expected != actual:
            raise SnapshotMismatchError(field_name, expected, actual)


# --- protocol ----------------------------------------------------------------------------


@runtime_checkable
class SimEngine(Protocol):
    """A physics backend seen by scenarios, the runner, record and verify (plan 3.1-3.3).

    ``isinstance(obj, SimEngine)`` only checks that the members exist (runtime_checkable),
    not their signatures or behaviour; the contract is the module docstring.
    """

    @property
    def time_s(self) -> float:
        """Current simulation time (s)."""
        ...

    @property
    def dt_s(self) -> float:
        """Physics step length used by :meth:`step` (s)."""
        ...

    @property
    def params_sha256(self) -> str:
        """``Params.sha256`` of the parameters the engine was built from."""
        ...

    @property
    def info(self) -> EngineInfo:
        """Engine name, version and model."""
        ...

    @property
    def is_closed(self) -> bool:
        """Whether :meth:`close` has been called."""
        ...

    def meta(self) -> dict[str, Any]:
        """JSON-serialisable run metadata for ``meta.json`` (a new dict on every call).

        Includes at least ``engine``, ``engine_version``, ``model``, ``dt_s`` and
        ``params_sha256``.
        """
        ...

    def reset(self, start: AnalyticStart | Snapshot = AnalyticStart.ON_PADS) -> TruthState:
        """Start a new run at time 0 with zero held command.

        Args:
            start: Analytic initial condition, or a settled :class:`Snapshot` whose dynamic
                state is taken over (same compatibility rule as :meth:`restore`). Unlike
                :meth:`restore`, the time is set to 0, the held command to zero speed and
                run bookkeeping (events, energy sums) is cleared.

        Returns:
            Truth state at time 0, for the first Record sample.

        Raises:
            SnapshotMismatchError: ``start`` is an incompatible snapshot.
        """
        ...

    def step(self) -> float:
        """Advance one physics step of :attr:`dt_s` with the held command.

        Returns:
            Simulation time after the step (s).
        """
        ...

    def apply_command(self, command: Command) -> None:
        """Hold ``command`` from the next :meth:`step` on (zero-order hold)."""
        ...

    def measure(self) -> Measurements:
        """Ideal sensor values at the current time (the runner calls it each control period)."""
        ...

    def truth(self) -> TruthState:
        """True state at the current time; recording and verification only, never control."""
        ...

    def snapshot(self) -> Snapshot:
        """Capture the complete dynamic state, time and held command (R16)."""
        ...

    def restore(self, snapshot: Snapshot) -> None:
        """Resume exactly from ``snapshot``: state, time and held command.

        Raises:
            SnapshotMismatchError: Different engine name, model or ``Params.sha256``; the
                engine state is left unchanged.
        """
        ...

    def close(self) -> None:
        """Release engine resources; idempotent."""
        ...
