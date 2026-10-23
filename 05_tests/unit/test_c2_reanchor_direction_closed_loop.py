"""C2 REANCHOR direction rule (spec 82.5, R7 candidate) on the reduced 6-DoF plant.

``s6_control_spec.md`` revision 18 section 82.5 tests: on the nose-up slope P:pitch-3.2 deg
REANCHOR is skipped with one ``reanchor_skipped:nose_up`` event, and on a nose-down slope the
``nose_down_only`` default reproduces the R6 run (``both``) bit for bit. Revision 20 86.2: floor
-2 deg with target +1 deg is a relative nose-up slope (skipped). Top auger, verification
mode, ideal sensors, Chrono-type pad friction (``fric_mode`` 1), the current YAML. The plant is
``04_scripts/01_dynamics/run_control_comparison.py`` ``Plant`` (imported read-only, numba); the
module is skipped without numba.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba", reason="the reduced plant kernel needs numba")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
import run_control_comparison as reduced_model  # noqa: E402

from outrigger_sim.control.c2 import (  # noqa: E402
    C2Config,
    C2Controller,
    C2Phase,
    ReanchorDirection,
    TargetSettings,
    is_shadow_event,
)
from outrigger_sim.control.target import (  # noqa: E402
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
)
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

CHRONO_PAD_FRICTION_MODE = 1
RUN_LIMIT_S = 200.0
HOLD_AFTER_READY_S = 5.0
NOSE_UP_PITCH_DEG = -3.2  # 82.5 case P:pitch-3.2 (theta > 0 = nose down)
NOSE_DOWN_PITCH_DEG = 3.5


@dataclass
class ClosedLoopRun:
    controller: C2Controller
    commands: np.ndarray
    phases: list[C2Phase]

    @property
    def decision_events(self) -> list[tuple[float, str]]:
        """Events without the GE1 shadow flags."""
        return [
            (event.t_s, event.name)
            for event in self.controller.events
            if not is_shadow_event(event.name)
        ]


def _config(direction: ReanchorDirection | None) -> C2Config:
    """R6 defaults with the 82.5 direction rule; ``None`` keeps the default direction."""
    params = load_params()
    target = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    config = C2Config(target=target, output_ramp_time_s=params.actuator.command_ramp_s)
    if direction is ReanchorDirection.BOTH:
        return config.with_r6_behaviour()
    return config


def _run(pitch_deg: float, config: C2Config) -> ClosedLoopRun:
    """Level on the top-auger plant pitched ``pitch_deg`` until READY has held 5 s."""
    controller = C2Controller.from_params(load_params(), config)
    plant = reduced_model.Plant("top", 0.0, pitch_deg)
    plant.step(np.zeros(4), int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT)))
    plant.t = 0.0
    command = np.zeros(4)
    commands, phases = [], []
    ready_s = 0.0
    while plant.t < RUN_LIMIT_S and ready_s < HOLD_AFTER_READY_S:
        accumulated = plant.step(command, reduced_model.N_SUB)
        measurements = Measurements(
            t_s=plant.t,
            specific_force_m_s2=accumulated[0:3] / reduced_model.N_SUB,
            angular_rate_rad_s=plant.w.copy(),
            head_pressure_Pa=plant.pressure() / controller.geometry.head_area_m2,
            stroke_m=plant.sref.copy(),
            stroke_corrected_m=plant.x.copy(),
        )
        command = np.array(controller.update(measurements).leg_speed_m_s)
        commands.append(command)
        phases.append(controller.phase)
        is_ready = controller.phase is C2Phase.READY
        ready_s = ready_s + reduced_model.T_CTRL if is_ready else 0.0
    assert controller.phase is C2Phase.READY
    return ClosedLoopRun(controller, np.array(commands), phases)


@pytest.fixture(scope="module")
def chrono_friction_mode():
    """The plant reads its friction mode at construction (module global, restored after)."""
    previous = reduced_model.PAD_FRICTION_MODE
    reduced_model.PAD_FRICTION_MODE = CHRONO_PAD_FRICTION_MODE
    yield
    reduced_model.PAD_FRICTION_MODE = previous


def test_nose_up_slope_skips_the_reanchor_once(chrono_friction_mode) -> None:
    """82.5: P:pitch-3.2 deg with the default ``nose_down_only`` -> skipped, one event, no
    REANCHOR phase; the run still reaches READY."""
    run = _run(NOSE_UP_PITCH_DEG, _config(direction=None))
    controller = run.controller
    assert controller.config.reanchor.direction is ReanchorDirection.NOSE_DOWN_ONLY
    assert controller.reanchor_outcome == "skipped:nose_up"
    reanchor_events = [name for _, name in run.decision_events if name.startswith("reanchor_")]
    assert reanchor_events == ["reanchor_skipped:nose_up"]
    assert C2Phase.REANCHOR not in run.phases


def test_nose_up_slope_still_reanchors_with_both(chrono_friction_mode) -> None:
    """``both`` (R6, ``with_r6_behaviour``) keeps H4 on the nose-up slope."""
    run = _run(NOSE_UP_PITCH_DEG, _config(ReanchorDirection.BOTH))
    assert run.controller.config.reanchor.direction is ReanchorDirection.BOTH
    assert run.controller.reanchor_outcome == "completed"
    assert C2Phase.REANCHOR in run.phases


def test_nonzero_target_judges_the_relative_nose_up(chrono_friction_mode) -> None:
    """86.2 closed loop: floor -2 deg (nose up), target +1 deg -> relative nose-up 2.8 deg ->
    one ``reanchor_skipped:nose_up``, READY on the target."""
    target_pitch_deg = 1.0
    config = _config(direction=None)
    target = replace(config.target, target=AttitudeTarget.from_degrees(0.0, target_pitch_deg))
    run = _run(-2.0, replace(config, target=target))
    controller = run.controller
    assert controller.target == AttitudeTarget.from_degrees(0.0, target_pitch_deg)
    anchor_pitch = controller.meta()["reanchor"]["anchor_pitch_rad"]
    assert anchor_pitch - math.radians(target_pitch_deg) < -math.radians(2.5)
    reanchor_events = [name for _, name in run.decision_events if name.startswith("reanchor_")]
    assert reanchor_events == ["reanchor_skipped:nose_up"]
    assert C2Phase.REANCHOR not in run.phases
    assert run.phases[-1] is C2Phase.READY


def test_nose_down_slope_is_bit_identical_to_r6(chrono_friction_mode) -> None:
    """82.5: on a nose-down slope ``nose_down_only`` reproduces ``both`` (R6) bit for bit."""
    r6 = _run(NOSE_DOWN_PITCH_DEG, _config(ReanchorDirection.BOTH))
    r7 = _run(NOSE_DOWN_PITCH_DEG, _config(direction=None))
    assert r6.controller.reanchor_outcome == r7.controller.reanchor_outcome == "completed"
    np.testing.assert_array_equal(r7.commands, r6.commands)
    assert r7.phases == r6.phases
    assert r7.decision_events == r6.decision_events
