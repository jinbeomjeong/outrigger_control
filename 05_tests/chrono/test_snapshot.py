"""R16 snapshot round trip on small Chrono systems (chrono_build_plan.md S0 table, R16).

Save -> restore into a freshly built system -> 1 s must reproduce the uninterrupted run
(position difference <= 1e-12 m). Systems (test assumptions, not machine data):

* "slide": the stick-friction block on a 10 deg slope, started downhill at 0.3 m/s so it slides
  and then sticks (ground bushing anchor moves, damping switched off and on), with a 500 kg
  rider on a ``ChLinkMotorLinearPosition`` driven by a sine of the system time (checks that
  time and motor state come back). Snapshot at 0.05 s, while sliding.
* "lift_event": as "air", snapshot taken right after the step whose hook removed the bushing
  (Chrono then starts the next step with a full Update; the restore must reproduce that too).
* "air": the block lifted off a level floor by a time-profiled force and put down again;
  snapshot at 0.55 s while it is in the air (bushing removed), so the restored run must
  re-create the bushing at the same step.

Also: the same through ``record.save_snapshot`` / ``load_snapshot`` (npz + meta.json in a
temporary directory), rewinding the original system, and refusal of a snapshot with another
``Params.sha256`` or body layout without touching the state.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.ground_bushing import EVENT_CREATE, EVENT_REMOVE  # noqa: E402
from outrigger_sim.chrono.snapshot import (  # noqa: E402
    ENGINE_NAME,
    S_REF_KEY,
    capture_snapshot,
    engine_info,
    pychrono_version,
    restore_snapshot,
)
from outrigger_sim.engine import SnapshotMismatchError  # noqa: E402
from outrigger_sim.params import Params  # noqa: E402
from outrigger_sim.record import load_snapshot, save_snapshot  # noqa: E402
from outrigger_sim.signals import Command  # noqa: E402

pytestmark = pytest.mark.chrono

POSITION_TOL_M = 1.0e-12  # plan S0 table, R16
RUN_AFTER_S = 1.0
RIDER_MASS_KG = 500.0
RIDER_HEIGHT_M = 0.5
RIDER_SINE_AMPLITUDE_M = 0.02
RIDER_SINE_FREQUENCY_HZ = 2.0
SLIDE_SLOPE_DEG = 10.0
SLIDE_V0_M_S = 0.3
SLIDE_SNAPSHOT_S = 0.05  # sliding stops near 0.1 s (decel. g (mu cos a - sin a) = 3.1 m/s^2)
AIR_SNAPSHOT_S = 0.55
S_REF_EXAMPLE_M = (0.1, 0.2, 0.3, 0.4)
HELD_COMMAND = Command(t_s=0.28, leg_speed_m_s=np.array([0.001, -0.002, 0.0, 0.02267]))


def _air_force(t: float) -> float:
    """Upward force / weight: leaves the floor near 0.5 s, lands near 0.6 s (no bounce)."""
    if t < 0.2:
        return 0.0
    if t < 0.5:
        return 1.01 * (t - 0.2) / 0.3
    if t < 0.55:
        return 1.01
    if t < 0.6:
        return 1.01 - 0.51 * (t - 0.55) / 0.05
    if t < 0.8:
        return 0.5
    if t < 1.0:
        return 0.5 * (1.0 - (t - 0.8) / 0.2)
    return 0.0


class ExternalForcePart:
    """Snapshot part for the Python-applied lift force (body accumulator).

    Chrono reads body accumulators in the system Update at the end of a step, so the force
    set before a step acts in the following one (same one-step lag as the bushing hook,
    ``chrono/snapshot.py`` docstring). The force that Chrono has loaded is therefore state and
    is restored before the restore's system Update. The engine's load module (S3 D2
    disturbance) will need the same treatment.
    """

    def __init__(self, body: Any, accumulator: int) -> None:
        self.body = body
        self.accumulator = accumulator
        self.force_N = np.zeros(3)

    def apply(self, force_N: np.ndarray) -> None:
        self.force_N = np.array(force_N, dtype=float)
        self.body.EmptyAccumulator(self.accumulator)
        p = self.body.GetPos()
        self.body.AccumulateForce(
            self.accumulator,
            ch.ChVector3d(*self.force_N),
            ch.ChVector3d(p.x, p.y, p.z),
            False,
        )

    def state_arrays(self) -> dict[str, np.ndarray]:
        return {"force_N": self.force_N.copy()}

    def restore_state(self, arrays: Any) -> None:
        self.apply(arrays["force_N"])


class SmallSystem:
    """Block (+ rider for "slide") with the step loop used by both runs."""

    def __init__(self, factory: Callable[..., Any], case: str) -> None:
        self.case = case
        if case == "slide":
            a = math.radians(SLIDE_SLOPE_DEG)
            v0 = (SLIDE_V0_M_S * math.cos(a), 0.0, -SLIDE_V0_M_S * math.sin(a))
            self.model = factory(SLIDE_SLOPE_DEG, v0=v0)
            rider = ch.ChBody()
            rider.SetName("rider")
            rider.SetMass(RIDER_MASS_KG)
            rider.SetInertiaXX(ch.ChVector3d(10.0, 10.0, 10.0))
            p0 = self.model.pos() + np.array([0.0, 0.0, RIDER_HEIGHT_M])
            rider.SetPos(ch.ChVector3d(*p0))
            rider.SetPosDt(ch.ChVector3d(*v0))
            self.model.system.Add(rider)
            motor = ch.ChLinkMotorLinearPosition()
            motor.Initialize(rider, self.model.block, ch.ChFramed(ch.ChVector3d(*p0), ch.QUNIT))
            motor.SetMotionFunction(
                ch.ChFunctionSine(RIDER_SINE_AMPLITUDE_M, RIDER_SINE_FREQUENCY_HZ)
            )
            self.model.system.Add(motor)
            self.bodies = [self.model.block, rider]
            self.motors = [motor]
            self.parts = {"ground_bushing": self.model.bushing}
            self.lift = None
        else:
            self.model = factory(0.0)
            self.bodies = [self.model.block]
            self.motors = []
            self.lift = ExternalForcePart(self.model.block, self.model.block.AddAccumulator())
            self.parts = {"ground_bushing": self.model.bushing, "lift": self.lift}

    def step(self) -> None:
        if self.lift is not None:
            up = _air_force(self.model.system.GetChTime()) * self.model.weight_N
            self.lift.apply(np.array([0.0, 0.0, up]))
        self.model.step()

    def run(self, seconds: float) -> np.ndarray:
        """Step ``seconds``; return body positions per step, shape (steps, bodies, 3)."""
        steps = round(seconds / self.model.dt_s)
        out = np.empty((steps, len(self.bodies), 3))
        for k in range(steps):
            self.step()
            for j, body in enumerate(self.bodies):
                p = body.GetPos()
                out[k, j] = (p.x, p.y, p.z)
        return out

    def snapshot(self, params: Params) -> Any:
        return capture_snapshot(
            self.model.system,
            engine=engine_info("L1"),
            params_sha256=params.sha256,
            held_command=HELD_COMMAND,
            bodies=self.bodies,
            motors=self.motors,
            s_ref_m=S_REF_EXAMPLE_M,
            parts=self.parts,
        )

    def restore(self, snapshot: Any, params: Params, sha: str | None = None) -> Any:
        return restore_snapshot(
            snapshot,
            self.model.system,
            engine=engine_info("L1"),
            params_sha256=params.sha256 if sha is None else sha,
            bodies=self.bodies,
            motors=self.motors,
            parts=self.parts,
        )


def _snapshot_time(case: str) -> float:
    return SLIDE_SNAPSHOT_S if case == "slide" else AIR_SNAPSHOT_S


@pytest.fixture(scope="module", params=["slide", "air", "lift_event"])
def reference_run(
    request: pytest.FixtureRequest, block_factory: Callable[..., Any], params: Params
) -> dict[str, Any]:
    case = request.param
    system = SmallSystem(block_factory, case)
    if case == "lift_event":
        while not system.model.bushing.events:
            system.step()
    else:
        system.run(_snapshot_time(case))
    snap = system.snapshot(params)
    trajectory = system.run(RUN_AFTER_S)
    return {
        "case": case,
        "system": system,
        "snapshot": snap,
        "trajectory": trajectory,
        "events": system.model.bushing.events,
        "anchors": system.model.bushing.anchors_world_m(),
        "time": system.model.system.GetChTime(),
    }


def _assert_same_continuation(restored: SmallSystem, ref: dict[str, Any]) -> None:
    trajectory = restored.run(RUN_AFTER_S)
    gap = float(np.max(np.abs(trajectory - ref["trajectory"])))
    assert gap <= POSITION_TOL_M, f"max position gap {gap:.3e} m"
    assert restored.model.system.GetChTime() == ref["time"]
    assert [(e.t_s, e.leg, e.kind) for e in restored.model.bushing.events] == [
        (e.t_s, e.leg, e.kind) for e in ref["events"]
    ]
    np.testing.assert_allclose(
        restored.model.bushing.anchors_world_m(), ref["anchors"], atol=POSITION_TOL_M
    )


def test_snapshot_content(reference_run: dict[str, Any], params: Params) -> None:
    snap = reference_run["snapshot"]
    assert snap.engine.name == ENGINE_NAME == "pychrono"
    assert snap.engine.version == pychrono_version() == "10.0.0"
    assert snap.params_sha256 == params.sha256
    if reference_run["case"] != "lift_event":
        assert snap.time_s == pytest.approx(_snapshot_time(reference_run["case"]), abs=1e-9)
    np.testing.assert_array_equal(snap.payload[S_REF_KEY], S_REF_EXAMPLE_M)
    in_contact = snap.payload["ground_bushing.in_contact"]
    if reference_run["case"] == "slide":
        assert in_contact.tolist() == [True]
        assert snap.payload["ground_bushing.sliding"].tolist() == [True]
        assert snap.payload["motors.pos_m"].shape == (1,)
        assert snap.payload["bodies.pos_m"].shape == (2, 3)
    else:
        assert in_contact.tolist() == [False]
        assert snap.payload["ground_bushing.event_kind"].tolist() == [EVENT_REMOVE]
        changed = snap.payload["ground_bushing.structure_changed"].tolist()
        assert changed == [reference_run["case"] == "lift_event"]
        kinds = [e.kind for e in reference_run["events"]]
        assert kinds == [EVENT_REMOVE, EVENT_CREATE]  # the re-touch happens after the snapshot


def test_restore_into_fresh_system(
    reference_run: dict[str, Any], block_factory: Callable[..., Any], params: Params
) -> None:
    fresh = SmallSystem(block_factory, reference_run["case"])
    restored = fresh.restore(reference_run["snapshot"], params)
    assert restored.time_s == reference_run["snapshot"].time_s
    assert restored.held_command is reference_run["snapshot"].held_command
    np.testing.assert_array_equal(restored.s_ref_m, S_REF_EXAMPLE_M)
    _assert_same_continuation(fresh, reference_run)


def test_restore_through_record_files(
    reference_run: dict[str, Any],
    block_factory: Callable[..., Any],
    params: Params,
    tmp_path: Path,
) -> None:
    name = f"r16_{reference_run['case']}"
    save_snapshot(reference_run["snapshot"], name, directory=tmp_path)
    loaded = load_snapshot(
        name, params_sha256=params.sha256, directory=tmp_path, engine=engine_info("L1")
    )
    fresh = SmallSystem(block_factory, reference_run["case"])
    restored = fresh.restore(loaded, params)
    np.testing.assert_array_equal(restored.held_command.leg_speed_m_s, HELD_COMMAND.leg_speed_m_s)
    _assert_same_continuation(fresh, reference_run)


def test_rewind_same_system(reference_run: dict[str, Any], params: Params) -> None:
    system: SmallSystem = reference_run["system"]
    system.restore(reference_run["snapshot"], params)
    _assert_same_continuation(system, reference_run)


def test_restore_refuses_other_params(
    reference_run: dict[str, Any], block_factory: Callable[..., Any], params: Params
) -> None:
    fresh = SmallSystem(block_factory, reference_run["case"])
    before = fresh.model.pos()
    with pytest.raises(SnapshotMismatchError):
        fresh.restore(reference_run["snapshot"], params, sha="0" * 64)
    np.testing.assert_array_equal(fresh.model.pos(), before)
    assert fresh.model.system.GetChTime() == 0.0
    assert fresh.model.bushing.in_contact.tolist() == [True]


def test_restore_refuses_other_layout(
    reference_run: dict[str, Any], block_factory: Callable[..., Any], params: Params
) -> None:
    other = "air" if reference_run["case"] == "slide" else "slide"
    fresh = SmallSystem(block_factory, other)
    before = fresh.model.pos()
    with pytest.raises(ValueError, match="layout"):
        fresh.restore(reference_run["snapshot"], params)
    np.testing.assert_array_equal(fresh.model.pos(), before)


def test_speed_motor_is_rejected(block_factory: Callable[..., Any], params: Params) -> None:
    model = block_factory(0.0)
    with pytest.raises(TypeError, match="ChLinkMotorLinearSpeed"):
        capture_snapshot(
            model.system,
            engine=engine_info("L1"),
            params_sha256=params.sha256,
            held_command=HELD_COMMAND,
            bodies=[model.block],
            motors=[ch.ChLinkMotorLinearSpeed()],
        )
