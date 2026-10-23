"""C2 R5 H5a on the reduced 6-DoF plant with the Chrono-type pad friction (``fric_mode`` 1).

``s6_control_spec.md`` 22.4 H5a test (b) / (c): top auger, nose-down and nose-up 3.5 deg in the
verification mode, ideal sensors, no delay. The plant is
``04_scripts/01_dynamics/run_control_comparison.py`` ``Plant`` (imported read-only, numba);
the module is skipped without numba. The H4lb reference values are spec rev. 21 88.3
(REXOME35 ``k_t``; they replace the spec 22.1 column), compared within the spec's +-1.5 kN.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba", reason="the reduced plant kernel needs numba")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
import run_control_comparison as reduced_model  # noqa: E402

from outrigger_sim.control.c2 import C2Config, C2Controller, C2Phase, TargetSettings  # noqa: E402
from outrigger_sim.control.target import CrawlerSettleMap, SlopeLimitMode  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

CHRONO_PAD_FRICTION_MODE = 1
RUN_LIMIT_S = 200.0
HOLD_AFTER_READY_S = 5.0
MIN_TRUE_FORCE_MARGIN_N = 5e3
"""D8 design margin above F_min (spec 22.4 H5a (b): F_min + 5 kN). The floor is computed from
the YAML F_min (``geometry.F_min_N``); the spec's 14.45 kN was the REXOME33 F_min 9.45 kN."""
LATERAL_LOAD_TOLERANCE_N = 1.5e3
H4LB_LATERAL_LOAD_MAX_N = {3.5: 15.7e3, -3.5: 6.9e3}
"""H4lb, YAML k_t: largest end rod lateral load of the four legs (spec rev. 21 88.3, REXOME35;
it replaces the REXOME33 spec 22.1 values 18.0 / 7.9 kN)."""
MEASURED_BAND_MAX_N = 3e3
"""F_s 0: the probe measures the band near its 1 kN floor (2.3 kN on this plant)."""
SEAL_FRICTION_N = 12e3


@dataclass
class H5aRun:
    controller: C2Controller
    min_true_force_N: float
    lateral_loads_N: list[float]


def _lateral_loads_N(plant) -> list[float]:
    """Rod lateral load per leg: body-xy part of ``N n + T`` (static part, no damping).

    Same decomposition as the plant kernel (fric_mode 1): normal ``N = k_s c`` along the floor
    normal, tangential bushing force from the anchor, capped at ``mu N``.
    """
    rotation = reduced_model._R(plant.q)
    leg_axis = rotation[:, 2]
    axis_along_normal = float(plant.nrm @ leg_axis)
    loads = []
    for leg in range(4):
        to_pad = rotation @ plant.pad_rel[leg]
        gap_axis = (plant.nrm @ (plant.r + to_pad) + plant.goff[leg]) / axis_along_normal
        compression = plant.x[leg] - gap_axis
        if compression <= 0.0:
            loads.append(0.0)
            continue
        pad_point = plant.r + to_pad - plant.x[leg] * leg_axis
        normal_force = plant.ks[leg] * compression
        slip = pad_point - plant.panc[leg]
        tangential = -plant.kt[leg] * (slip - (slip @ plant.nrm) * plant.nrm)
        magnitude = float(np.linalg.norm(tangential))
        if magnitude > plant.mu * normal_force:
            tangential *= plant.mu * normal_force / magnitude
        pad_force_body = rotation.T @ (normal_force * plant.nrm + tangential)
        loads.append(float(np.hypot(pad_force_body[0], pad_force_body[1])))
    return loads


def _run_h5a(pitch_deg: float, seal_friction_N: float = 0.0) -> H5aRun:
    params = load_params()
    target = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    config = C2Config(
        target=target, output_ramp_time_s=params.actuator.command_ramp_s
    ).with_r5_behaviour()  # the R5 H5a check (10 kN floor margin, no READY heave)
    controller = C2Controller.from_params(params, config)
    plant = reduced_model.Plant("top", 0.0, pitch_deg, Fs=seal_friction_N)
    plant.step(np.zeros(4), int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT)))
    plant.t = 0.0
    command = np.zeros(4)
    min_true_force = math.inf
    has_crawler_lifted = False
    ready_s = 0.0
    while plant.t < RUN_LIMIT_S and ready_s < HOLD_AFTER_READY_S:
        accumulated = plant.step(command, reduced_model.N_SUB)
        has_crawler_lifted |= accumulated[15] == 0.0
        if has_crawler_lifted:
            min_true_force = min(min_true_force, float(plant.true_cyl_force().min()))
        measurements = Measurements(
            t_s=plant.t,
            specific_force_m_s2=accumulated[0:3] / reduced_model.N_SUB,
            angular_rate_rad_s=plant.w.copy(),
            head_pressure_Pa=plant.pressure() / controller.geometry.head_area_m2,
            stroke_m=plant.sref.copy(),
            stroke_corrected_m=plant.x.copy(),
        )
        command = np.array(controller.update(measurements).leg_speed_m_s)
        is_ready = controller.phase is C2Phase.READY
        ready_s = ready_s + reduced_model.T_CTRL if is_ready else 0.0
    assert controller.phase is C2Phase.READY
    return H5aRun(controller, min_true_force, _lateral_loads_N(plant))


@pytest.fixture(scope="module")
def chrono_friction_mode():
    """The plant reads its friction mode at construction (module global, restored after)."""
    previous = reduced_model.PAD_FRICTION_MODE
    reduced_model.PAD_FRICTION_MODE = CHRONO_PAD_FRICTION_MODE
    yield
    reduced_model.PAD_FRICTION_MODE = previous


@pytest.mark.parametrize("pitch_deg", [3.5, -3.5])
def test_reanchor_after_the_probe_uses_the_measured_band(chrono_friction_mode, pitch_deg) -> None:
    """H5a (b): min true force >= F_min + 5 kN, rear stops at F_min + F_band + 10 kN (20.45 kN for a
    1 kN band; 21.8 kN here), end lateral load within 1.5 kN of H4lb, one probe round."""
    run = _run_h5a(pitch_deg)
    controller = run.controller
    geometry = controller.geometry
    assert controller.reanchor_outcome == "completed"
    assert len(controller.probe_history) == 1  # no second probe after the REANCHOR trim
    assert 1e3 <= controller.seal_band_N < MEASURED_BAND_MAX_N
    reanchor = controller.meta()["reanchor"]
    floor_N = geometry.F_min_N + controller.seal_band_N + 10e3
    np.testing.assert_allclose(reanchor["stop_force_N"][2:], floor_N, rtol=0, atol=1e-6)
    rear_readings = [entry["reading_N"] for entry in reanchor["stop_readings_N"][2:]]
    assert all(reading <= floor_N for reading in rear_readings)
    assert run.min_true_force_N >= geometry.F_min_N + MIN_TRUE_FORCE_MARGIN_N
    assert max(run.lateral_loads_N) == pytest.approx(
        H4LB_LATERAL_LOAD_MAX_N[pitch_deg], abs=LATERAL_LOAD_TOLERANCE_N
    )


def test_seal_friction_keeps_the_h4_stop_floor(chrono_friction_mode) -> None:
    """H5a (c): F_s 12 kN -> F_band >= 13 kN -> stop floor >= 32.45 kN."""
    run = _run_h5a(3.5, seal_friction_N=SEAL_FRICTION_N)
    controller = run.controller
    assert controller.seal_band_N >= 13e3
    stops = controller.meta()["reanchor"]["stop_force_N"]
    assert min(stops) >= controller.geometry.F_min_N + 13e3 + 10e3
