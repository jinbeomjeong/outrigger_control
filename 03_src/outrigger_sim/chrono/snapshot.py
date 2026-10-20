"""Chrono side of the R16 state snapshot: fill and restore an engine-independent ``Snapshot``.

``00_docs/03_chrono/chrono_build_plan.md`` R16, S0; ``outrigger_sim.engine.Snapshot``. Saving a
snapshot to disk (npz + meta.json) belongs to ``record``; this module stops at the
:class:`~outrigger_sim.engine.Snapshot` object and does not change its fields.

What is captured (payload keys, all bool / int / float arrays):

* ``bodies.*``: per body, in the order given by the caller, the COG frame of the Chrono body
  in world coordinates: position ``pos_m`` (n, 3), orientation ``quat_wxyz`` (n, 4, R10),
  velocity ``vel_m_s`` (n, 3), angular velocity in body coordinates ``omega_local_rad_s``
  (n, 3), and the accelerations ``acc_m_s2`` / ``angacc_local_rad_s2`` of the last step
  (not needed by ``EULER_IMPLICIT_LINEARIZED``; restored so that reads after the restore
  match). ``bodies.layout_sha256`` (32 uint8) fingerprints the body count and names, so a
  snapshot cannot be scattered onto another model layout.
* ``motors.pos_m`` / ``motors.vel_m_s``: ``GetMotorPos`` / ``GetMotorPosDt`` of each linear
  motor (recorded; after a restore they are recomputed from the bodies and compared, which
  catches a motor function that is not at the same state, for example a wrong time).
* ``actuator.s_ref_m``: the actuator reference ``s_ref`` per leg (Python-side state of the
  actuator model), when given.
* ``<prefix>.<key>``: Python-side state of other parts, e.g. ``ground_bushing.*`` from
  :meth:`outrigger_sim.chrono.ground_bushing.GroundBushingCoulomb.state_arrays` (anchors,
  frames, sliding flags, lift timers, event table).

The simulation time is ``Snapshot.time_s`` (``ChSystem.GetChTime``). The held command is the
engine's (``Snapshot.held_command``). Chrono internal states that are not captured, and why
that is exact for the L1 model: the timestepper ``EULER_IMPLICIT_LINEARIZED`` has no history;
direct solvers have no warm start; SMC contacts are rebuilt by collision detection at the start
of every step (``kt = 0``, R8, so no tangential history matters); position motors have no
internal state (the motion function is evaluated at the system time). Speed motors
(``ChLinkMotorLinearSpeed``) carry internal integrator variables that are not reachable from
Python (``ChState`` cannot be constructed in pychrono 10.0.0); they are rejected.

One-step lag of Python changes (pychrono 10.0.0, measured 2026-10-20): Chrono evaluates load
forces and Jacobians (e.g. the ground bushing) in the system Update at the end of a step. A
change made from Python after the step (the bushing hook moves the anchor and switches the
damping) is therefore used from the step after next, unless the system is flagged "not up to
date" (any ``Add`` / ``Remove``, ``ForceUpdate``), in which case the next step starts with a
full Update and uses it at once. ``ChSystem.Update()`` called from Python does not clear that
flag. An exact restore therefore (1) rebuilds the parts with the values Chrono had loaded,
(2) if the system is flagged, takes one throw-away step of :data:`FLUSH_STEP_S` and resets
bodies and time, (3) calls ``Update`` and (4) lets the parts set their post-hook values
(``finish_restore``). Without this, a snapshot taken while a pad slides continued with a
position error of 6e-8 m after 10 ms (block test); with it the continuation is bit-identical.

``ChSystem.StateGather`` / ``StateScatter`` were not usable: the pychrono 10.0.0 bindings do
not accept the system as the ``ChIntegrable*`` argument of the ``ChState`` constructors
(probe 2026-10-20), so the state is gathered per body.

Units SI, world frame Z-up (R3); every Chrono value is copied when read (R9).
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.engine import EngineInfo, Snapshot, ensure_snapshot_compatible
from outrigger_sim.signals import Command

ENGINE_NAME = "pychrono"

BODY_KEYS = (
    "bodies.pos_m",
    "bodies.quat_wxyz",
    "bodies.vel_m_s",
    "bodies.omega_local_rad_s",
    "bodies.acc_m_s2",
    "bodies.angacc_local_rad_s2",
    "bodies.layout_sha256",
)
MOTOR_KEYS = ("motors.pos_m", "motors.vel_m_s")
S_REF_KEY = "actuator.s_ref_m"

FLUSH_STEP_S = 1.0e-6
"""Length of the throw-away step that clears Chrono's update flag during a restore [s]."""

MOTOR_CHECK_TOL_M = 1.0e-9
"""Restored motor position must match the stored one within this [m] (after ``Update``)."""


class SnapshotPart(Protocol):
    """Python-side model part with state that a snapshot must carry (e.g. ground bushing).

    ``restore_state`` may add or remove Chrono items. A part may also define
    ``finish_restore()``; :func:`restore_snapshot` calls it after the final system Update
    (used for values that Chrono must not have evaluated yet, see the module docstring).
    """

    def state_arrays(self) -> dict[str, NDArray[Any]]: ...

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None: ...


@dataclass(frozen=True)
class RestoredState:
    """What :func:`restore_snapshot` hands back to the engine.

    Attributes:
        time_s: Simulation time after the restore [s].
        held_command: Command to hold again (zero-order hold continues).
        s_ref_m: Actuator reference per leg [m], or None if the snapshot has none.
    """

    time_s: float
    held_command: Command
    s_ref_m: NDArray[np.float64] | None


@cache
def pychrono_version() -> str:
    """pychrono version from the conda metadata (the package has no ``__version__``)."""
    version = getattr(ch, "__version__", None)
    if isinstance(version, str) and version:
        return version
    for meta in sorted((Path(sys.prefix) / "conda-meta").glob("pychrono-*.json")):
        try:
            return str(json.loads(meta.read_text(encoding="utf-8"))["version"])
        except (OSError, ValueError, KeyError):
            continue
    return "unknown"


def engine_info(model: str) -> EngineInfo:
    """``EngineInfo("pychrono", <version>, model)``; ``model`` e.g. ``"L1"``."""
    return EngineInfo(name=ENGINE_NAME, version=pychrono_version(), model=str(model))


def _vec(v: Any) -> list[float]:
    return [float(v.x), float(v.y), float(v.z)]


def _quat(q: Any) -> list[float]:
    return [float(q.e0), float(q.e1), float(q.e2), float(q.e3)]


def _chvec(a: ArrayLike) -> ch.ChVector3d:
    x, y, z = (float(c) for c in np.asarray(a, dtype=float))
    return ch.ChVector3d(x, y, z)


def _layout_digest(bodies: Sequence[ch.ChBody]) -> NDArray[np.uint8]:
    names = [str(body.GetName()) for body in bodies]
    text = json.dumps({"count": len(bodies), "names": names}, separators=(",", ":"))
    return np.frombuffer(hashlib.sha256(text.encode("utf-8")).digest(), dtype=np.uint8).copy()


def _check_motors(motors: Sequence[Any]) -> None:
    for motor in motors:
        if isinstance(motor, ch.ChLinkMotorLinearSpeed):
            raise TypeError(
                "ChLinkMotorLinearSpeed has internal integrator state that a snapshot cannot "
                "capture in pychrono 10.0.0; use a position or force motor"
            )
        if not hasattr(motor, "GetMotorPos"):
            raise TypeError(f"not a linear motor: {motor!r}")


def capture_snapshot(
    system: ch.ChSystem,
    *,
    engine: EngineInfo,
    params_sha256: str,
    held_command: Command,
    bodies: Sequence[ch.ChBody],
    motors: Sequence[Any] = (),
    s_ref_m: ArrayLike | None = None,
    parts: Mapping[str, SnapshotPart] | None = None,
) -> Snapshot:
    """Capture the dynamic state of ``system`` into an engine-independent :class:`Snapshot`.

    Args:
        system: Chrono system (time from ``GetChTime``).
        engine: Engine identity, see :func:`engine_info`.
        params_sha256: ``Params.sha256`` of the parameters the model was built from.
        held_command: Command the engine currently holds.
        bodies: Every non-fixed body of the model, in a fixed order (the restore uses the
            same order; names are fingerprinted).
        motors: Linear motors (position or force); their positions are recorded and checked.
        s_ref_m: Actuator reference per leg [m] (stored as ``actuator.s_ref_m``).
        parts: Python-side parts by key prefix (no dots in the prefix), e.g.
            ``{"ground_bushing": bushing}``.

    Returns:
        Snapshot with read-only payload copies.
    """
    _check_motors(motors)
    payload: dict[str, NDArray[Any]] = {
        "bodies.pos_m": np.array([_vec(b.GetPos()) for b in bodies], dtype=float).reshape(-1, 3),
        "bodies.quat_wxyz": np.array([_quat(b.GetRot()) for b in bodies], dtype=float).reshape(
            -1, 4
        ),
        "bodies.vel_m_s": np.array([_vec(b.GetPosDt()) for b in bodies], dtype=float).reshape(
            -1, 3
        ),
        "bodies.omega_local_rad_s": np.array(
            [_vec(b.GetAngVelLocal()) for b in bodies], dtype=float
        ).reshape(-1, 3),
        "bodies.acc_m_s2": np.array([_vec(b.GetPosDt2()) for b in bodies], dtype=float).reshape(
            -1, 3
        ),
        "bodies.angacc_local_rad_s2": np.array(
            [_vec(b.GetAngAccLocal()) for b in bodies], dtype=float
        ).reshape(-1, 3),
        "bodies.layout_sha256": _layout_digest(bodies),
        "motors.pos_m": np.array([float(m.GetMotorPos()) for m in motors], dtype=float),
        "motors.vel_m_s": np.array([float(m.GetMotorPosDt()) for m in motors], dtype=float),
    }
    if s_ref_m is not None:
        payload[S_REF_KEY] = np.array(s_ref_m, dtype=float).reshape(-1)
    for prefix, part in (parts or {}).items():
        if not prefix or "." in prefix:
            raise ValueError(f"part prefix must be a non-empty name without dots: {prefix!r}")
        for key, value in part.state_arrays().items():
            payload[f"{prefix}.{key}"] = np.asarray(value)
    return Snapshot(
        engine=engine,
        params_sha256=params_sha256,
        time_s=float(system.GetChTime()),
        held_command=held_command,
        payload=payload,
    )


def _part_arrays(snapshot: Snapshot, prefix: str) -> dict[str, NDArray[Any]]:
    head = f"{prefix}."
    return {
        key[len(head) :]: value for key, value in snapshot.payload.items() if key.startswith(head)
    }


def _set_bodies(
    bodies: Sequence[ch.ChBody],
    payload: Mapping[str, NDArray[Any]],
    time_s: float,
    system: ch.ChSystem,
) -> None:
    for i, body in enumerate(bodies):
        body.SetPos(_chvec(payload["bodies.pos_m"][i]))
        w, x, y, z = (float(c) for c in payload["bodies.quat_wxyz"][i])
        body.SetRot(ch.ChQuaterniond(w, x, y, z))
        body.SetPosDt(_chvec(payload["bodies.vel_m_s"][i]))
        body.SetAngVelLocal(_chvec(payload["bodies.omega_local_rad_s"][i]))
        body.SetPosDt2(_chvec(payload["bodies.acc_m_s2"][i]))
        body.SetAngAccLocal(_chvec(payload["bodies.angacc_local_rad_s2"][i]))
    system.SetChTime(time_s)


def restore_snapshot(
    snapshot: Snapshot,
    system: ch.ChSystem,
    *,
    engine: EngineInfo,
    params_sha256: str,
    bodies: Sequence[ch.ChBody],
    motors: Sequence[Any] = (),
    parts: Mapping[str, SnapshotPart] | None = None,
    motor_check_tol_m: float = MOTOR_CHECK_TOL_M,
) -> RestoredState:
    """Put ``system`` into the state of ``snapshot`` (same model built from the same params).

    All checks run before any state is touched: engine name / model and ``Params.sha256``
    (:func:`~outrigger_sim.engine.ensure_snapshot_compatible`), body layout, motor count,
    presence of every part's keys. Then bodies, system time and parts are set, the system is
    updated once and the motor positions are compared with the stored ones.

    Args:
        snapshot: State to restore.
        system: Target system (a fresh build of the same model, or the same system to rewind).
        engine: Identity of the target engine.
        params_sha256: ``Params.sha256`` of the target model.
        bodies: Same bodies in the same order as at capture.
        motors: Same motors in the same order as at capture.
        parts: Same part prefixes as at capture.
        motor_check_tol_m: Allowed motor position mismatch after the restore [m].

    Returns:
        :class:`RestoredState` (time, held command, ``s_ref``) for the engine.

    Raises:
        SnapshotMismatchError: Engine name, model or parameter fingerprint differ.
        ValueError: Layout mismatch (bodies, motors, part keys) or motor positions that do
            not match after the restore (the state was already written in that case).
    """
    ensure_snapshot_compatible(snapshot, engine=engine, params_sha256=params_sha256)
    _check_motors(motors)
    payload = snapshot.payload
    missing = [key for key in (*BODY_KEYS, *MOTOR_KEYS) if key not in payload]
    if missing:
        raise ValueError(f"snapshot payload lacks {missing}")
    if not np.array_equal(payload["bodies.layout_sha256"], _layout_digest(bodies)):
        raise ValueError(
            f"snapshot body layout ({payload['bodies.pos_m'].shape[0]} bodies) does not match "
            f"the target ({len(bodies)} bodies, names {[b.GetName() for b in bodies]})"
        )
    if payload["motors.pos_m"].shape != (len(motors),):
        raise ValueError(
            f"snapshot has {payload['motors.pos_m'].shape[0]} motors, target has {len(motors)}"
        )
    part_arrays = {prefix: _part_arrays(snapshot, prefix) for prefix in (parts or {})}
    for prefix, arrays in part_arrays.items():
        if not arrays:
            raise ValueError(f"snapshot has no state for part {prefix!r}")

    parts = parts or {}
    _set_bodies(bodies, payload, snapshot.time_s, system)
    for prefix, part in parts.items():
        part.restore_state(part_arrays[prefix])  # may add / remove items (structural)
    if not system.IsUpdated():
        # Clear Chrono's "not up to date" flag (set by the structural changes and by a fresh
        # system) with one throw-away step, then put bodies and time back. Otherwise the next
        # step would start with a full Update and evaluate the loads with the post-hook values,
        # which the uninterrupted run does not do (module docstring, "one-step lag").
        system.DoStepDynamics(FLUSH_STEP_S)
        _set_bodies(bodies, payload, snapshot.time_s, system)
    system.Update()  # loads, links and motor positions at the restored state
    for part in parts.values():
        finish = getattr(part, "finish_restore", None)
        if finish is not None:
            finish()
    if motors:
        restored = np.array([float(m.GetMotorPos()) for m in motors])
        gap = np.abs(restored - payload["motors.pos_m"])
        if np.any(gap > motor_check_tol_m):
            raise ValueError(
                f"motor positions after restore differ from the snapshot by {gap.max():.3e} m "
                f"(> {motor_check_tol_m:g} m): motor function or time not in the saved state"
            )
    s_ref = payload.get(S_REF_KEY)
    return RestoredState(
        time_s=float(system.GetChTime()),
        held_command=snapshot.held_command,
        s_ref_m=None if s_ref is None else np.array(s_ref, dtype=float),
    )
