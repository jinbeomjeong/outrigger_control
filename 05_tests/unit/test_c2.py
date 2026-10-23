"""Unit tests of the C2 levelling controller (00_docs/04_control/c2_design.md 14.8).

The regression test replays control-step traces of the reduced model the design was verified
on (``04_scripts/03_control/run_c2_revision.py`` ``C2R``, gain set ``R:BS_hold`` = revision R1,
design section 16). The traces
are made by ``04_scripts/03_control/export_c2_regression_traces.py`` (needs numba, so it runs
in dynamics-dev, not here).

Revision R2 (design section 17, pad re-anchoring): the unit tests of 17.7 Q10 use synthetic
readings that follow the commanded travel; the regression (Q11, Q12) replays traces of
``04_scripts/03_control/run_c2_reanchor.py`` ``C2RN`` with option set ``H4``
(``export_c2_regression_traces.py --set r2``).
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import c2 as c2_module
from outrigger_sim.control.c2 import (
    SHADOW_EVENT_PREFIX,
    C2Config,
    C2Controller,
    C2Gains,
    C2Geometry,
    C2Phase,
    C2Thresholds,
    ContactJudge,
    IntegratorBandMode,
    ProbeSettings,
    ReanchorDirection,
    ReanchorSettings,
    RodStrokeFallback,
    TargetSettings,
    is_shadow_event,
    scale_to_speed_limit,
    twist_rate_command,
)
from outrigger_sim.control.ground_contact import ProbeProfile, RegroundRule, StiffnessWindow
from outrigger_sim.control.protocol import Controller
from outrigger_sim.control.standstill import deg_per_hour
from outrigger_sim.control.target import (
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
    TargetAcceptance,
)
from outrigger_sim.params import LEG_ORDER, Params, load_params
from outrigger_sim.signals import Measurements

TRACE_DIR = Path(__file__).resolve().parents[1] / "data"
TRACE_STEM = "c2_reduced_model_traces"
GRAVITY_M_S2 = 9.80665
# The reduced model starts F_band at 12 kN; the decided value is 13 kN (decision D5).
REDUCED_MODEL_SEAL_BAND_N = 12e3
# Pressure round trip (force / area * area) and the pad-plane fit (pinv instead of lstsq)
# differ from the reduced model in the last bits only.
REPLAY_TOLERANCE_M_S = 1e-12
# Largest effect of the reduced model's rounding of probe estimates to 0.01 kN.
PROBE_ROUNDING_N = 5.0
# Touch hold 0.5 s at T = 0.02 s: the load must be seen on 26 samples (t0 ... t0 + 0.5 s).
TOUCH_HOLD_SAMPLES = 26
# 2nd-order forward-Euler step response after 50 samples, 1 - (1 - a)^n (1 + n a), a = 0.04
# (design 14.8 as corrected in 16.6 / 16.8 P11).
ATTITUDE_STEP_RESPONSE_50 = 0.6103426194338848
# Revision R3 starts with a 2 s CHECK; these synthetic benches and the replays start at TOUCH
# like revision R2 (check_time_s 0 runs TOUCH in the first period).
NO_CHECK = TargetSettings(check_time_s=0.0)
REPLAY_TARGET_SETTINGS = TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF)
# The reduced model judges the probe by stiffness only (design 14.6; spec 10.1 P1 keeps the
# replays on that verdict, the combined verdict is the new default).
STIFFNESS_ONLY_PROBE = ProbeSettings(use_combined_verdict=False)
# Revision R4 defaults that change the R2 / R3 trajectories (spec 18.1 P1-P3, 20.2 P5, 20.4 P6):
# the replays of the R2 / R3 traces use the former rectangular probe without stroke guard, the
# per-axis integrator band and the 3 kN READY re-level margin.
# Revision R4.1 judge changes (spec 21.3 Q1 / Q2, 29 K1) that the R4 and older traces predate:
# verdict re-ground rule, no attitude quality gate, stiffness over the whole first move.
R4_JUDGE = {
    "reground_rule": RegroundRule.VERDICT,
    "attitude_ripple_ratio": None,
    "attitude_drift_ratio": None,
    "stiffness_window": StiffnessWindow.FULL,
}
R4_PROBE = ProbeSettings(**R4_JUDGE)
R2_PROBE = ProbeSettings(
    use_combined_verdict=False,
    profile=ProbeProfile.RECT,
    stroke_guard_margin_m=None,
    **R4_JUDGE,
)
R2_THRESHOLDS = C2Thresholds(
    integrator_band_mode=IntegratorBandMode.AXIS,
    relevel_load_margin_N=3000.0,
    allow_legacy_relevel_margin=True,
)
# Revision R3.1 (X9) records the shadow floor estimate at every TOUCH -> LEVEL.
TOUCH_END_EVENT = "floor_estimate_touch"
# Revision R4.1 / R5 GE1 flags; shadow only, so the event lists of older revisions leave them out.


def _decision_events(controller: C2Controller) -> list:
    """Events without the GE1 shadow flags (``shadow_*``, ``INFO_FLOOR_NONPLANAR``)."""
    return [event for event in controller.events if not is_shadow_event(event.name)]


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


LEGACY_PARAMS_PATH = (
    Path(__file__).resolve().parents[2]
    / "02_params" / "history" / "rexome33_2026-10-22_before_rexome35.yaml"
)
"""The YAML the recorded traces were made with (REXOME33 cylinder, 0.68 m stroke): the legacy
replays stay pinned to it (spec rev. 13, 68); the other tests use the current YAML."""


@pytest.fixture(scope="module")
def legacy_geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params(LEGACY_PARAMS_PATH))


@pytest.fixture(scope="module")
def trace_meta() -> dict:
    return json.loads((TRACE_DIR / f"{TRACE_STEM}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def trace_rows() -> np.ndarray:
    return np.load(TRACE_DIR / f"{TRACE_STEM}.npy", allow_pickle=False)


def _operating_strokes(geometry: C2Geometry) -> np.ndarray:
    """Strokes with every pad on the floor and the crawler 50 mm above it."""
    return geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05


def _measurements(
    t_s: float,
    geometry: C2Geometry,
    cylinder_force_N: np.ndarray,
    rod_stroke_m: np.ndarray,
    *,
    tilt_rad: tuple[float, float] = (0.0, 0.0),
) -> Measurements:
    roll, pitch = tilt_rad
    up_in_body = np.array(
        [-math.sin(pitch), math.sin(roll) * math.cos(pitch), math.cos(roll) * math.cos(pitch)]
    )
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=GRAVITY_M_S2 * up_in_body,
        angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=np.asarray(cylinder_force_N) / geometry.head_area_m2,
        stroke_m=rod_stroke_m,
        stroke_corrected_m=rod_stroke_m,
    )


def _touch_down(
    controller: C2Controller,
    geometry: C2Geometry,
    cylinder_force_N: np.ndarray,
    stroke_m: np.ndarray,
    stroke_corrected_m: np.ndarray | None = None,
) -> float:
    """Feed a steady touchdown load until LEVEL; returns the time of the last sample."""
    rod_stroke = stroke_m if stroke_corrected_m is None else stroke_corrected_m
    for k in range(TOUCH_HOLD_SAMPLES):
        t_s = 0.02 * (k + 1)
        measurements = replace(
            _measurements(t_s, geometry, cylinder_force_N, rod_stroke), stroke_m=stroke_m
        )
        controller.update(measurements)
    assert controller.phase is C2Phase.LEVEL
    return t_s


def _level_after_touch(
    geometry: C2Geometry, config: C2Config
) -> tuple[C2Controller, np.ndarray, float]:
    """Controller in LEVEL after the touch hold; returns it, the strokes and the last time."""
    controller = C2Controller(geometry, config)
    strokes = _operating_strokes(geometry)
    t_s = _touch_down(controller, geometry, np.full(4, 80e3), strokes)
    return controller, strokes, t_s


def _strokes_for_zone_estimate(
    geometry: C2Geometry, cylinder_force_N: np.ndarray, clearance_m: float
) -> tuple[np.ndarray, np.ndarray]:
    """Motor and rod strokes whose crawler-zone estimate ``c_lr(s - P / k_oil(s))`` is given.

    Shifting every stroke by ``d`` shifts the pad-plane clearance by ``d``; ``k_oil`` changes
    little with ``d``, so a few fixed-point steps converge to rounding.
    """
    motor = _operating_strokes(geometry)
    for _ in range(20):
        rod = motor - cylinder_force_N / geometry.oil_stiffness_N_m(motor)
        motor = motor + (clearance_m - geometry.clearance_estimate_m(rod))
    rod = motor - cylinder_force_N / geometry.oil_stiffness_N_m(motor)
    assert geometry.clearance_estimate_m(rod) == pytest.approx(clearance_m, abs=1e-12)
    return motor, rod


# --- geometry -------------------------------------------------------------------------------


def test_geometry_matches_the_reduced_model_context(legacy_geometry, trace_meta) -> None:
    context = trace_meta["context"]
    np.testing.assert_allclose(legacy_geometry.support_matrix, context["A"], rtol=0, atol=1e-15)
    np.testing.assert_allclose(legacy_geometry.twist_vector, context["n"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        legacy_geometry.twist_vector, [0.476, -0.476, -0.523, 0.523], rtol=0, atol=1e-3
    )
    assert legacy_geometry.nominal_pad_stiffness_N_m == pytest.approx(
        context["k_nom_N_m"], rel=1e-15
    )
    np.testing.assert_allclose(
        legacy_geometry.load_sensitivity_diag_N_m, context["S_nom_diag_N_m"], rtol=1e-9
    )
    assert legacy_geometry.F_min_N == pytest.approx(context["F_min_N"], rel=1e-8)
    assert legacy_geometry.max_speed_m_s == context["v_max_m_s"]
    assert legacy_geometry.stroke_max_m == context["stroke_max_m"]
    np.testing.assert_array_equal(
        legacy_geometry.crawler_corners_xy_m, context["crawler_corners_xy_m"]
    )
    # The exporter writes one area per leg; traces exported before rev. 30 hold one common value.
    np.testing.assert_allclose(
        legacy_geometry.head_area_m2, context["piston_area_m2"], rtol=1e-15, atol=0
    )


def test_clearance_estimate_at_the_operating_strokes(geometry) -> None:
    clearance = geometry.clearance_estimate_m(_operating_strokes(geometry))
    # Pads of the rear legs sit 2 mm higher, so the fitted plane misses one corner slightly.
    assert clearance == pytest.approx(0.05, abs=1e-3)


def test_decomposition_round_trip(geometry) -> None:
    rates = np.array([3e-3, -1.5e-3, 2e-3, -4e-3])
    leg_speeds = geometry.leg_speeds(*rates)
    np.testing.assert_allclose(geometry.decompose(leg_speeds), rates, rtol=0, atol=1e-12)
    np.testing.assert_allclose(geometry.support_matrix.T @ geometry.twist_vector, 0, atol=1e-12)


# --- control law pieces --------------------------------------------------------------------


def test_vector_scaling_keeps_the_direction_and_the_zero_twist(geometry) -> None:
    leg_speeds = geometry.leg_speeds(0.0, 0.05, -0.03, 0.0)
    scaled = scale_to_speed_limit(leg_speeds, geometry.max_speed_m_s)
    assert np.max(np.abs(scaled)) == pytest.approx(geometry.max_speed_m_s, rel=1e-15)
    np.testing.assert_allclose(
        scaled / np.linalg.norm(scaled), leg_speeds / np.linalg.norm(leg_speeds)
    )
    assert abs(geometry.twist_vector @ scaled) < 1e-15


def test_vector_scaling_leaves_small_commands_alone(geometry) -> None:
    leg_speeds = np.array([1e-3, -2e-3, 0.0, 5e-3])
    np.testing.assert_array_equal(
        scale_to_speed_limit(leg_speeds, geometry.max_speed_m_s), leg_speeds
    )


def test_twist_loop_with_dead_band(geometry) -> None:
    gains, thresholds = C2Gains(), C2Thresholds()
    high_loads = np.full(4, 80e3)
    twist = geometry.twist_vector
    inside, _ = twist_rate_command(80e3 + 1.5e3 * twist, high_loads, geometry, gains, thresholds)
    assert inside == 0.0
    rate, is_guarding = twist_rate_command(
        80e3 + 10e3 * twist, high_loads, geometry, gains, thresholds
    )
    assert not is_guarding
    assert rate == pytest.approx(-gains.twist_ktw_1_s * 8e3 / geometry.nominal_pad_stiffness_N_m)


def test_guard_priority_drops_the_opposing_twist_term(geometry) -> None:
    gains, thresholds = C2Gains(), C2Thresholds()
    # FL (n > 0) is the lightest leg; a positive twist load asks to unload FL (rate < 0).
    forces = 80e3 + 20e3 * geometry.twist_vector
    loads = np.array([12e3, 80e3, 80e3, 80e3])
    rate, is_guarding = twist_rate_command(forces, loads, geometry, gains, thresholds)
    guard_level = geometry.F_min_N + thresholds.guard_margin_N
    expected = gains.guard_kg_1_s * (guard_level - 12e3) / geometry.nominal_pad_stiffness_N_m
    assert is_guarding
    assert rate == pytest.approx(expected, rel=1e-15)


def test_guard_adds_to_a_twist_term_in_its_own_direction(geometry) -> None:
    gains, thresholds = C2Gains(), C2Thresholds()
    forces = 80e3 - 20e3 * geometry.twist_vector  # twist loop already loads FL
    loads = np.array([12e3, 80e3, 80e3, 80e3])
    rate, _ = twist_rate_command(forces, loads, geometry, gains, thresholds)
    k_nom = geometry.nominal_pad_stiffness_N_m
    twist_term = gains.twist_ktw_1_s * 18e3 / k_nom
    guard_term = gains.guard_kg_1_s * (geometry.F_min_N + 5e3 - 12e3) / k_nom
    assert rate == pytest.approx(twist_term + guard_term, rel=1e-12)


# --- filters, phases, output ---------------------------------------------------------------


def test_attitude_filter_step_response(geometry) -> None:
    controller = C2Controller(geometry, C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE))
    forces, strokes = np.zeros(4), np.full(4, 0.1)
    controller.update(_measurements(0.02, geometry, forces, strokes))
    tilt = math.radians(0.5)
    for k in range(50):
        controller.update(
            _measurements(0.04 + 0.02 * k, geometry, forces, strokes, tilt_rad=(tilt, 0))
        )
    # Both stages take this period's input (design 14.3), so after n steps
    # y = 1 - (1 - a)^n (1 + n a). The 14.8 table's (1 + n a / (1 - a)) is the response
    # when the second stage takes the previous first-stage value.
    a = 0.02 / 0.5
    expected = 1.0 - (1.0 - a) ** 50 * (1.0 + 50 * a)
    assert expected == pytest.approx(ATTITUDE_STEP_RESPONSE_50, rel=1e-14)
    roll, pitch = controller.filtered_attitude_rad
    assert roll / tilt == pytest.approx(ATTITUDE_STEP_RESPONSE_50, rel=1e-12)
    assert pitch == 0.0


def test_touch_waits_for_the_hold_then_latches(geometry) -> None:
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    strokes = np.full(4, 0.1)
    v_max = geometry.max_speed_m_s
    forces = np.array([20e3, 0.0, 0.0, 0.0])
    for k in range(TOUCH_HOLD_SAMPLES - 1):
        command = controller.update(_measurements(0.02 * (k + 1), geometry, forces, strokes))
        # FL is a candidate: it stops while the others extend at full speed.
        np.testing.assert_array_equal(command.leg_speed_m_s, [0.0, v_max, v_max, v_max])
    t_s = 0.02 * TOUCH_HOLD_SAMPLES
    command = controller.update(_measurements(t_s, geometry, forces, strokes))
    np.testing.assert_array_equal(command.leg_speed_m_s, [0.0, v_max, v_max, v_max])
    assert controller.phase is C2Phase.TOUCH
    # FL stays latched even when its load drops; the others now hold for 0.5 s.
    for k in range(TOUCH_HOLD_SAMPLES):
        loads = np.array([0.0, 20e3, 20e3, 20e3])
        controller.update(_measurements(t_s + 0.02 * (k + 1), geometry, loads, strokes))
    assert controller.phase is C2Phase.LEVEL


def test_touch_load_broken_before_the_hold_keeps_the_leg_free(geometry) -> None:
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    strokes = np.full(4, 0.1)
    v_max = geometry.max_speed_m_s
    approach = C2Thresholds().touch_approach_speed_fraction * v_max
    loaded = np.array([20e3, 0.0, 0.0, 0.0])
    # Load above the touch level for 0.48 s (25 samples), then gone: no latch.
    for k in range(TOUCH_HOLD_SAMPLES - 1):
        controller.update(_measurements(0.02 * (k + 1), geometry, loaded, strokes))
    t_s = 0.02 * TOUCH_HOLD_SAMPLES
    command = controller.update(_measurements(t_s, geometry, np.zeros(4), strokes))
    np.testing.assert_array_equal(command.leg_speed_m_s, [approach, v_max, v_max, v_max])
    # A new unbroken 0.5 s run latches FL: it stops for good.
    for k in range(TOUCH_HOLD_SAMPLES):
        command = controller.update(_measurements(t_s + 0.02 * (k + 1), geometry, loaded, strokes))
    t_s += 0.02 * TOUCH_HOLD_SAMPLES
    command = controller.update(_measurements(t_s + 0.02, geometry, np.zeros(4), strokes))
    np.testing.assert_array_equal(command.leg_speed_m_s, [0.0, v_max, v_max, v_max])
    assert controller.phase is C2Phase.TOUCH


def test_output_ramp_limits_the_change_per_period(geometry) -> None:
    controller = C2Controller(geometry, C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE))
    max_step = 0.2 * geometry.max_speed_m_s
    previous = np.zeros(4)
    for k in range(8):
        command = controller.update(
            _measurements(0.02 * (k + 1), geometry, np.zeros(4), np.full(4, 0.1))
        )
        assert np.max(np.abs(command.leg_speed_m_s - previous)) <= max_step * (1 + 1e-12)
        previous = command.leg_speed_m_s
    np.testing.assert_allclose(previous, geometry.max_speed_m_s, rtol=1e-12)


def test_level_command_holds_a_level_balanced_machine(geometry) -> None:
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller, strokes, t_s = _level_after_touch(geometry, config)
    command = controller.update(_measurements(t_s + 0.02, geometry, np.full(4, 80e3), strokes))
    assert not controller.is_in_crawler_zone
    heave, roll, pitch, twist = geometry.decompose(command.leg_speed_m_s)
    clearance = geometry.clearance_estimate_m(strokes)
    assert heave == pytest.approx(0.5 * (0.05 - clearance), abs=1e-15)
    assert (roll, pitch, twist) == pytest.approx((0.0, 0.0, 0.0), abs=1e-15)


def test_completion_after_the_hold_time_then_ready(geometry) -> None:
    config = C2Config(
        target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None
    ).with_r5_behaviour()  # R5 mechanism (R6 lock tails off)
    controller, strokes, level_entry_s = _level_after_touch(geometry, config)
    t_s = level_entry_s
    while controller.phase is C2Phase.LEVEL and t_s < 5.0:
        t_s += 0.02
        controller.update(_measurements(t_s, geometry, np.full(4, 80e3), strokes))
    assert controller.phase is C2Phase.DONE
    assert t_s == pytest.approx(level_entry_s + 0.02 + 1.0)
    command = controller.update(_measurements(t_s + 0.02, geometry, np.full(4, 80e3), strokes))
    assert controller.phase is C2Phase.READY
    np.testing.assert_array_equal(command.leg_speed_m_s, np.zeros(4))
    tilted = _measurements(t_s + 0.04, geometry, np.full(4, 80e3), strokes, tilt_rad=(0.01, 0))
    for _ in range(200):
        controller.update(tilted)
        if controller.phase is C2Phase.LEVEL:
            break
    assert controller.phase is C2Phase.LEVEL


OIL_COMPRESSION_M = 3e-3  # rod 3 mm short of the motor under ~70 kN (design 16.4)


@pytest.mark.parametrize("end_reading", ["stroke_m", "stroke_corrected_m"])
def test_stroke_end_fault_judges_stroke_m(geometry, end_reading) -> None:
    """Design 14.8 (R1): only ``stroke_m`` at the end faults; the rod reading alone does not."""
    forces = np.full(4, 80e3)
    # 30 mm under the operating strokes: the heave loop asks every leg to extend.
    motor = _operating_strokes(geometry) - 0.03
    if end_reading == "stroke_m":
        rod = motor - OIL_COMPRESSION_M
        stroke_max = float(motor.max())
    else:
        rod = motor + OIL_COMPRESSION_M  # only the rod reading reaches the end
        stroke_max = float(rod.max())
    clip_margin = C2Thresholds().stroke_end_clip_margin_m
    is_clipped = motor >= stroke_max - clip_margin  # the front legs share one stroke
    assert is_clipped.any() == (end_reading == "stroke_m")
    short_geometry = replace(geometry, stroke_max_m=stroke_max)
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(short_geometry, config)
    t_s = _touch_down(controller, short_geometry, forces, motor, rod)
    fault_step = round(C2Thresholds().stroke_end_fault_time_s / config.period_s) + 1
    for k in range(fault_step):
        measurements = replace(
            _measurements(t_s + 0.02 * (k + 1), short_geometry, forces, rod), stroke_m=motor
        )
        command = controller.update(measurements)
        if k < fault_step - 1:
            assert controller.phase is C2Phase.LEVEL
            assert np.all(command.leg_speed_m_s[is_clipped] == 0.0)
            assert np.all(command.leg_speed_m_s[~is_clipped] > 0.0)
    if end_reading == "stroke_corrected_m":
        assert controller.phase is C2Phase.LEVEL
        return
    assert controller.phase is C2Phase.FAULT
    level = _measurements(t_s + 3.0, geometry, forces, _operating_strokes(geometry))
    np.testing.assert_array_equal(controller.update(level).leg_speed_m_s, np.zeros(4))
    assert controller.phase is C2Phase.FAULT


def test_crawler_zone_latch_has_hysteresis(geometry) -> None:
    """Design 14.8 (R1): release at 20 mm, re-arm only below 10 mm, no chatter in between."""
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    forces = np.full(4, 80e3)

    def strokes_at(clearance_mm: float) -> tuple[np.ndarray, np.ndarray]:
        return _strokes_for_zone_estimate(geometry, forces, clearance_mm * 1e-3)

    t_s = _touch_down(controller, geometry, forces, *strokes_at(19.9))
    assert controller.is_in_crawler_zone
    estimates_mm = [19.9, 20.1, 19.9, 20.1, 19.9, 20.1, 10.1, 9.9, 19.9, 10.1, 20.1]
    zone_states = []
    for clearance_mm in estimates_mm:
        motor, rod = strokes_at(clearance_mm)
        t_s += 0.02
        controller.update(replace(_measurements(t_s, geometry, forces, rod), stroke_m=motor))
        zone_states.append(controller.is_in_crawler_zone)
    expected = [True, False, False, False, False, False, False, True, True, True, False]
    assert zone_states == expected


def test_crawler_zone_blocks_retraction(geometry) -> None:
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    forces = np.full(4, 80e3)
    motor, _ = _strokes_for_zone_estimate(geometry, forces, 0.015)
    # A rod reading 50 mm longer makes the heave loop ask every leg to retract; the zone,
    # judged on the motor strokes, turns that into a standstill.
    rod = motor + 0.05
    t_s = _touch_down(controller, geometry, forces, motor, rod)
    measurements = replace(_measurements(t_s + 0.02, geometry, forces, rod), stroke_m=motor)
    command = controller.update(measurements)
    assert controller.is_in_crawler_zone
    np.testing.assert_allclose(command.leg_speed_m_s, 0.0, rtol=0, atol=1e-15)


def test_level_guard_loads_the_lightest_leg(geometry) -> None:
    """The F_min guard acts inside LEVEL (moved here from the regression replay, R1)."""
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller, strokes, t_s = _level_after_touch(geometry, config)
    forces = np.array([12e3, 80e3, 80e3, 80e3])
    command = controller.update(_measurements(t_s + 0.02, geometry, forces, strokes))
    # 76.4 (3) a: calibration on without CHECK -> the E-6 allowance on the guard reading
    lower = forces - controller._pressures.offset_allowance_N
    expected_twist, is_guarding = twist_rate_command(
        forces, lower, geometry, config.gains, config.thresholds
    )
    assert is_guarding
    _, _, _, twist = geometry.decompose(command.leg_speed_m_s)
    assert twist == pytest.approx(expected_twist, rel=1e-9)
    assert twist > 0.0  # n[FL] > 0: the guard extends FL relative to its neighbours


def test_probe_regrounds_a_leg_that_did_not_move(geometry) -> None:
    """Combined judge: a probe round without stroke travel finds no grounded leg.

    The R1 regression traces no longer re-ground (every pad is loaded at LEVEL entry), so this
    covers the re-grounding branch of design 14.6 directly.
    """
    config = C2Config(target=NO_CHECK, probe=STIFFNESS_ONLY_PROBE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    strokes = _operating_strokes(geometry)
    t_s = 0.0

    def step(forces: np.ndarray, rod_stroke: np.ndarray) -> np.ndarray:
        nonlocal t_s
        t_s += 0.02
        return controller.update(_measurements(t_s, geometry, forces, rod_stroke)).leg_speed_m_s

    while t_s < C2Thresholds().free_air_window_s:
        step(np.zeros(4), strokes)
    loaded = np.full(4, 80e3)
    while controller.phase is not C2Phase.PROBE and t_s < 15.0:
        step(loaded, strokes)
    assert controller.phase is C2Phase.PROBE
    while not controller.probe_history and t_s < 30.0:
        command = step(loaded, strokes)
    assert all(not result.is_grounded for result in controller.probe_history[0])
    command = step(loaded, strokes)
    probe_speed = ProbeSettings().speed_fraction * geometry.max_speed_m_s
    np.testing.assert_array_equal(command, [probe_speed, 0.0, 0.0, 0.0])
    assert controller.phase is C2Phase.PROBE
    step(loaded, strokes + np.array([0.05, 0.0, 0.0, 0.0]))
    assert controller.phase is C2Phase.LEVEL


def _probe_with_loads(
    geometry: C2Geometry, probe_loads_N: np.ndarray, level_loads_N: np.ndarray | None = None
) -> C2Controller:
    """Combined judge (default verdict): touch at 80 kN, then level and probe at the given loads.

    The strokes never move, so neither stiffness nor attitude shows contact; only the friction
    band of the readings decides (spec 10.1 P1). ``level_loads_N`` (default: the probe loads)
    are fed until DONE, so that a leg too light for LEVEL to complete can still be probed.
    """
    config = C2Config(target=NO_CHECK, output_ramp_time_s=None).with_r5_behaviour()  # R5
    controller = C2Controller(geometry, config)
    strokes = _operating_strokes(geometry)
    level_loads = probe_loads_N if level_loads_N is None else level_loads_N
    t_s = 0.0
    while t_s < C2Thresholds().free_air_window_s:
        t_s += 0.02
        controller.update(_measurements(t_s, geometry, np.zeros(4), strokes))
    while controller.phase is C2Phase.TOUCH:
        t_s += 0.02
        controller.update(_measurements(t_s, geometry, np.full(4, 80e3), strokes))
    while not controller.probe_history and t_s < 60.0:
        t_s += 0.02
        is_probing = controller.phase in (C2Phase.DONE, C2Phase.PROBE)
        loads = probe_loads_N if is_probing else level_loads
        controller.update(_measurements(t_s, geometry, loads, strokes))
    return controller


def test_combined_probe_regrounds_the_lowest_ungrounded_reading(geometry) -> None:
    """RL and RR ambiguous (13 / 12 kN against F_band 13 kN), FL, FR loaded: RR, not RL."""
    controller = _probe_with_loads(geometry, np.array([80e3, 80e3, 13e3, 12e3]))
    verdicts = [result.is_grounded for result in controller.probe_history[0]]
    assert verdicts == [True, True, False, False]
    assert controller.phase is C2Phase.PROBE  # re-grounding
    assert controller.reground_leg == LEG_ORDER.index("RR")


def test_combined_probe_with_four_ungrounded_legs_is_unresolved(geometry) -> None:
    controller = _probe_with_loads(geometry, np.full(4, 15e3))
    assert not any(result.is_grounded for result in controller.probe_history[0])
    assert controller.phase is C2Phase.READY
    # R5 (H5a): the REANCHOR decision follows the probe, so its skip comes last.
    assert [event.name for event in _decision_events(controller)][-2:] == [
        "probe_unresolved",
        "reanchor_skipped:theta_below_min",
    ]


# Spec 21.2: the midpoint load estimate of a lifted leg is about -W_rod.
LIFTED_LEG_LOAD_N = -6.8e3
RR = LEG_ORDER.index("RR")
RL = LEG_ORDER.index("RL")


def test_load_first_regrounds_a_light_leg_judged_grounded(geometry) -> None:
    """Q2: lifted RR judged grounded by a fooled attitude cue, RL ambiguous: RR, not RL."""
    loads = np.array([80e3, 80e3, 13e3, LIFTED_LEG_LOAD_N])
    controller = _probe_with_loads(geometry, loads, level_loads_N=np.full(4, 80e3))
    results = list(controller.probe_history[0])
    assert [result.is_grounded for result in results] == [True, True, False, False]
    results[RR] = replace(results[RR], is_grounded=True)  # the R4 misjudgement of spec 21
    reading = controller._state.last_reading  # the decision is internal; call it directly
    assert controller._leg_to_reground(tuple(results), reading).leg_index == RR
    verdict = C2Controller(geometry, replace(controller.config, probe=R4_PROBE))
    assert verdict._leg_to_reground(tuple(results), reading).leg_index == RL


def test_load_first_resolves_a_round_with_four_ungrounded_legs(geometry) -> None:
    """Q2: all four ungrounded, RR reads -W_rod: RR is re-grounded, no ``probe_unresolved``."""
    loads = np.array([15e3, 15e3, 15e3, LIFTED_LEG_LOAD_N])
    controller = _probe_with_loads(geometry, loads, level_loads_N=np.full(4, 80e3))
    assert not any(result.is_grounded for result in controller.probe_history[0])
    assert controller.reground_leg == RR
    assert controller.phase is C2Phase.PROBE
    assert "probe_unresolved" not in [event.name for event in controller.events]


def test_support_geometry_shadow_is_refreshed_and_recorded(geometry) -> None:
    """GE1': stored at TOUCH end, refreshed in READY once the gate opens after a probe round
    with four grounded legs; in meta, JSON-serialisable."""
    controller = C2Controller(geometry, C2Config(target=NO_CHECK, output_ramp_time_s=None))
    assert controller.support_geometry is None
    controller = _probe_with_loads(geometry, np.full(4, 80e3))
    assert controller.phase is C2Phase.READY
    strokes = _operating_strokes(geometry)
    t_s = controller._state.last_reading.t_s  # continue the bench clock
    for _ in range(round(2.0 / 0.02)):  # command-free 1 s + rates quiet 0.5 s
        t_s += 0.02
        controller.update(_measurements(t_s, geometry, np.full(4, 80e3), strokes))
    meta = controller.meta()["support_geometry"]
    json.dumps(controller.meta())
    assert [update["source"] for update in meta["reference_updates"]] == ["touch", "ready"]
    assert meta["reference_updates"][1]["max_abs_height_change_m"] == pytest.approx(0, abs=1e-9)
    assert controller.support_geometry.is_geometry_valid
    # Pads on one plane (the bench strokes never move): no height change, no flag.
    np.testing.assert_allclose(meta["max_abs_heights_delta_above_others_m"], 0.0, atol=1e-9)
    assert meta["flags_t_s"] == {}


def _rod_stroke_controllers(
    geometry: C2Geometry, fallback: RodStrokeFallback
) -> tuple[C2Controller, C2Controller]:
    config = C2Config(
        target=NO_CHECK,
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
        rod_stroke_fallback=fallback,
    )
    return C2Controller(geometry, config), C2Controller(geometry, config)


def _assert_fallback_matches(
    geometry: C2Geometry, fallback: RodStrokeFallback, oil_stiffness_N_m: np.ndarray
) -> None:
    """A reading without ``stroke_corrected_m`` acts as the given rod ``s - F / k_oil``."""
    forces = np.full(4, 80e3)
    motor = _operating_strokes(geometry)
    rod = motor - forces / oil_stiffness_N_m
    with_rod, without_rod = _rod_stroke_controllers(geometry, fallback)
    for k in range(3):
        given = replace(_measurements(0.02 * (k + 1), geometry, forces, rod), stroke_m=motor)
        derived = replace(given, stroke_corrected_m=None)
        np.testing.assert_allclose(
            without_rod.update(derived).leg_speed_m_s,
            with_rod.update(given).leg_speed_m_s,
            rtol=0,
            atol=1e-15,
        )


def test_missing_corrected_stroke_uses_the_oil_column(geometry) -> None:
    """R4.1 option (L2 / L2b): ``k_oil(s)`` at the measured stroke."""
    motor = _operating_strokes(geometry)
    _assert_fallback_matches(
        geometry, RodStrokeFallback.STROKE_OIL_COLUMN, geometry.oil_stiffness_N_m(motor)
    )


def test_l1_fallback_keeps_the_operating_oil_column(geometry) -> None:
    """R5 default (dynamics-expert): ``k_oil(e_op)``, so the L1 split ``1 / k_oil + 1 / k_s =
    1 / k_n`` holds at any stroke; 0.15 m from ``e_op`` the two columns differ by > 0.5 mm per
    50 kN, which the default does not pass on."""
    e_op = geometry.operating_extension_m(C2Thresholds().clearance_target_m)
    np.testing.assert_allclose(e_op, _operating_strokes(geometry), rtol=0, atol=1e-15)
    _assert_fallback_matches(
        geometry, RodStrokeFallback.OPERATING_OIL_COLUMN, geometry.oil_stiffness_N_m(e_op)
    )
    load_change_N = 50e3
    far_stroke = e_op + 0.15
    split_error_m = load_change_N / geometry.oil_stiffness_N_m(far_stroke) - (
        load_change_N / geometry.oil_stiffness_N_m(e_op)
    )
    assert np.all(np.abs(split_error_m) > 0.5e-3)
    controller = C2Controller(geometry, C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE))
    forces = np.full(4, load_change_N)
    reading = _measurements(0.02, geometry, forces, far_stroke)
    rod = controller._rod_stroke_without_sensor(far_stroke, forces)  # the fallback itself
    np.testing.assert_allclose(rod, far_stroke - forces / geometry.oil_stiffness_N_m(e_op))
    required = C2Controller(
        geometry, C2Config(target=NO_CHECK, rod_stroke_fallback=RodStrokeFallback.REQUIRED)
    )
    with pytest.raises(ValueError, match="stroke_corrected_m"):
        required.update(replace(reading, stroke_corrected_m=None))


def test_protocol_reset_and_meta() -> None:
    controller = C2Controller.from_params(load_params())
    geometry = controller.geometry
    assert isinstance(controller, Controller)
    assert controller.period_s == 0.02
    meta = controller.meta()
    json.dumps(meta)
    assert meta["controller"] == "C2"
    assert meta["revision"] == "R7"
    assert meta["reanchor_direction"] == "nose_down_only"  # spec 86.1 / 86.6 return condition 1
    reanchor = meta["reanchor"]
    assert reanchor["outcome"] is None
    assert reanchor["settings"]["stair_N"] == [45e3, 30e3, 20e3, 20e3]
    assert reanchor["settings"]["targets"] == ["RR", "RL"]
    assert reanchor["settings"]["theta_min_rad"] == pytest.approx(math.radians(2.5))
    assert meta["filters"]["crawler_rule_pressure_time_constant_s"] == 0.2
    thresholds = meta["thresholds"]
    assert (thresholds["crawler_zone_release_m"], thresholds["crawler_zone_rearm_m"]) == (
        0.02,
        0.01,
    )
    assert (thresholds["touch_hold_s"], thresholds["touch_approach_speed_fraction"]) == (
        0.5,
        0.25,
    )
    assert "crawler_zone_clearance_m" not in thresholds
    assert meta["contact"] == "combined"
    assert meta["seal_band_N"] == 13e3
    assert meta["gains"]["twist_ktw_1_s"] == 1.0
    first = [
        controller.update(_measurements(0.02 * (k + 1), geometry, np.zeros(4), np.full(4, 0.1)))
        for k in range(5)
    ]
    controller.reset()
    second = [
        controller.update(_measurements(0.02 * (k + 1), geometry, np.zeros(4), np.full(4, 0.1)))
        for k in range(5)
    ]
    for before, after in zip(first, second, strict=True):
        np.testing.assert_array_equal(before.leg_speed_m_s, after.leg_speed_m_s)


def _params_with_command_ramp(command_ramp_s: float) -> Params:
    return load_params(overrides={"actuator.command_ramp_s": command_ramp_s})


def test_from_params_takes_the_output_ramp_from_the_yaml() -> None:
    params = load_params()
    controller = C2Controller.from_params(params)
    assert controller.config.output_ramp_time_s == params.actuator.command_ramp_s

    changed = C2Controller.from_params(_params_with_command_ramp(0.25))
    assert changed.config.output_ramp_time_s == 0.25
    assert changed.meta()["output_ramp_time_s"] == 0.25


def test_from_params_turns_the_ramp_off_without_an_actuator_limit() -> None:
    controller = C2Controller.from_params(_params_with_command_ramp(0.0))
    assert controller.config.output_ramp_time_s is None


def test_explicit_config_keeps_its_own_output_ramp(geometry) -> None:
    params = _params_with_command_ramp(0.25)
    explicit = C2Controller.from_params(params, C2Config(output_ramp_time_s=None))
    assert explicit.config.output_ramp_time_s is None
    assert C2Controller(geometry).config.output_ramp_time_s == 0.1
    assert C2Config().output_ramp_time_s == 0.1


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        C2Config(output_ramp_time_s=0.0)
    with pytest.raises(ValueError):
        C2Config(period_s=0.0)
    with pytest.raises(ValueError):
        C2Config(contact="pressure-only")


def test_invalid_reanchor_settings_are_rejected() -> None:
    with pytest.raises(ValueError):
        ReanchorSettings(speed_fraction=0.0)
    with pytest.raises(ValueError):
        ReanchorSettings(stair_N=())
    with pytest.raises(ValueError):
        ReanchorSettings(targets=("RR", "XX"))


# --- REANCHOR (revision R2, design 17.7 Q10) -------------------------------------------------

RR, RL = LEG_ORDER.index("RR"), LEG_ORDER.index("RL")
# Q10 quotes 32.4526 kN from the rounded F_min 9452.55 N of the design scripts; with the YAML
# F_min (9452.5475 N) the stop is 32452.5475 N.
Q10_STOP_TOLERANCE_N = 0.1
# Synthetic readings: every leg carries 80 kN and gains this much per metre of commanded
# extension during REANCHOR, so the 45 kN stop needs about 2.2 mm (design: 1.2-2.9 mm).
BENCH_LOAD_N = 80e3
BENCH_LOAD_STIFFNESS_N_M = 1.6e7
BENCH_TIME_LIMIT_S = 120.0


@dataclass
class _ReanchorBench:
    """Drives a controller with readings that follow the commanded REANCHOR travel."""

    controller: C2Controller
    geometry: C2Geometry
    rod_stroke_m: np.ndarray
    motor_stroke_m: np.ndarray
    t_s: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    reanchor_outputs: list[np.ndarray] = field(default_factory=list)

    def forces_N(self) -> np.ndarray:
        return BENCH_LOAD_N + BENCH_LOAD_STIFFNESS_N_M * self.travel_m

    def step(
        self, *, tilt_rad: tuple[float, float] = (0.0, 0.0), forces_N: np.ndarray | None = None
    ) -> np.ndarray:
        self.t_s += 0.02
        forces = self.forces_N() if forces_N is None else forces_N
        measurements = replace(
            _measurements(self.t_s, self.geometry, forces, self.rod_stroke_m, tilt_rad=tilt_rad),
            stroke_m=self.motor_stroke_m,
        )
        command = self.controller.update(measurements).leg_speed_m_s
        if self.controller.phase is C2Phase.REANCHOR:
            self.travel_m = self.travel_m + command * self.controller.period_s
            self.reanchor_outputs.append(command)
        return command

    def run_while(self, phase: C2Phase) -> None:
        while self.controller.phase is phase and self.t_s < BENCH_TIME_LIMIT_S:
            self.step()


def _bench_at_first_done(
    geometry: C2Geometry,
    theta_crawler_deg: float,
    *,
    config: C2Config | None = None,
    rod_stroke_m: np.ndarray | None = None,
    motor_stroke_m: np.ndarray | None = None,
    direction: ReanchorDirection | None = None,
) -> _ReanchorBench:
    """Touch down on a crawler pitched ``theta_crawler_deg``, then level until the first DONE.

    ``direction`` overrides the ``both`` of the R5 preset (spec 82.5 option).
    """
    if config is None:
        config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    config = config.with_r5_behaviour()  # R2 / R5 REANCHOR mechanism, no R6 lock tails
    if direction is not None:
        config = replace(config, reanchor=replace(config.reanchor, direction=direction))
    rod = _operating_strokes(geometry) if rod_stroke_m is None else rod_stroke_m
    motor = rod if motor_stroke_m is None else motor_stroke_m
    bench = _ReanchorBench(C2Controller(geometry, config), geometry, rod, motor)
    crawler_tilt = (0.0, math.radians(theta_crawler_deg))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step(tilt_rad=crawler_tilt)
    assert bench.controller.phase is C2Phase.LEVEL
    bench.run_while(C2Phase.LEVEL)
    assert bench.controller.phase is C2Phase.DONE
    return bench


def _reanchor_speed(geometry: C2Geometry) -> float:
    return ReanchorSettings().speed_fraction * geometry.max_speed_m_s


@pytest.mark.parametrize(("target", "sign"), [(RR, 1.0), (RL, -1.0)])
def test_reanchor_direction_is_the_twist_mode(geometry, target, sign) -> None:
    """Q10-1: target RR -> u / v_r = (-0.910, +0.910, +1.000, -1.000), RL the opposite."""
    controller = C2Controller(geometry)
    direction = controller.reanchor_direction(target)
    expected = sign * np.array([-0.910, 0.910, 1.000, -1.000])
    np.testing.assert_allclose(direction, expected, rtol=0, atol=1e-3)
    assert direction[target] == -1.0
    assert np.linalg.norm(geometry.support_matrix.T @ direction) < 1e-12


def test_reanchor_stop_thresholds_follow_the_seal_band(geometry) -> None:
    """Q10-2: P_stop = max(stair, 20 kN, F_min + F_band + margin) with the YAML F_min (rev. 13):
    R5 margin 10 kN, U69 (R6) 11.5 kN; a small band leaves the stairs (45, 30, 20, 20) kN."""
    f_min = geometry.F_min_N
    controller = C2Controller(geometry, C2Config().with_r5_behaviour())
    floor_r5 = f_min + 13e3 + 10e3
    np.testing.assert_allclose(controller.reanchor_stop_forces_N(13e3),
                               [45e3, floor_r5, floor_r5, floor_r5], rtol=0, atol=1e-9)
    assert controller.reanchor_stop_forces_N(0.5e3) == (45e3, 30e3, 20e3, 20e3)
    floor_r6 = f_min + 13e3 + 11.5e3
    np.testing.assert_allclose(C2Controller(geometry).reanchor_stop_forces_N(13e3),
                               [45e3, floor_r6, floor_r6, floor_r6], rtol=0, atol=1e-9)


@pytest.mark.parametrize(("theta_deg", "is_applied"), [(2.49, False), (2.51, True)])
def test_reanchor_applies_from_the_slope_threshold(geometry, theta_deg, is_applied) -> None:
    """Q10-3: the pitch on the crawler decides; below 2.5 deg the run goes on to READY."""
    bench = _bench_at_first_done(geometry, theta_deg)
    command = bench.step()
    np.testing.assert_array_equal(command, np.zeros(4))
    controller = bench.controller
    assert controller.phase is (C2Phase.REANCHOR if is_applied else C2Phase.READY)
    expected_outcome = None if is_applied else "skipped:theta_below_min"
    assert controller.reanchor_outcome == expected_outcome
    assert controller.meta()["reanchor"]["theta_crawler_rad"] == pytest.approx(
        math.radians(theta_deg), rel=1e-12
    )


def _bench_in_crawler_zone(geometry: C2Geometry) -> _ReanchorBench:
    # Motor strokes whose slow clearance estimate stays at 15 mm keep the zone latched, while
    # the rod strokes let the heave loop complete.
    motor, _ = _strokes_for_zone_estimate(geometry, np.full(4, BENCH_LOAD_N), 0.015)
    return _bench_at_first_done(geometry, 3.0, motor_stroke_m=motor)


def _bench_near_the_stroke_end(geometry: C2Geometry) -> _ReanchorBench:
    strokes = _operating_strokes(geometry)
    short = replace(geometry, stroke_max_m=float(strokes.max()) + 0.009)  # 9 mm left
    return _bench_at_first_done(short, 3.0)


def _bench_not_lifted(geometry: C2Geometry) -> _ReanchorBench:
    thresholds = replace(C2Thresholds(), clearance_target_m=0.0)
    config = C2Config(
        target=NO_CHECK,
        thresholds=thresholds,
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
    )
    return _bench_at_first_done(
        geometry, 3.0, config=config, rod_stroke_m=_operating_strokes(geometry) - 0.05
    )


def _bench_disabled(geometry: C2Geometry) -> _ReanchorBench:
    config = C2Config(
        target=NO_CHECK,
        reanchor=ReanchorSettings(enable=False),
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
    )
    return _bench_at_first_done(geometry, 3.0, config=config)


@pytest.mark.parametrize(
    ("make_bench", "reason"),
    [
        (_bench_in_crawler_zone, "crawler_zone"),
        (_bench_near_the_stroke_end, "stroke_margin"),
        (_bench_not_lifted, "not_lifted"),
        (_bench_disabled, "disabled"),
    ],
)
def test_reanchor_is_skipped_outside_its_conditions(geometry, make_bench, reason) -> None:
    """Q10-3: crawler-zone latch on or a stroke 9 mm from its end -> skipped (17.2.2)."""
    bench = make_bench(geometry)
    bench.step()
    assert bench.controller.reanchor_outcome == f"skipped:{reason}"
    assert bench.controller.phase is C2Phase.READY
    assert [event.name for event in _decision_events(bench.controller)] == [
        TOUCH_END_EVENT,
        f"reanchor_skipped:{reason}",
    ]


def _bench_moving(geometry: C2Geometry, move_periods: int = 5) -> _ReanchorBench:
    """REANCHOR started on a 3 deg slope and ``move_periods`` periods into the first MOVE."""
    bench = _bench_at_first_done(geometry, 3.0)
    decision_s = bench.t_s + 0.02
    command = bench.step()
    while not np.any(command) and bench.t_s < BENCH_TIME_LIMIT_S:
        command = bench.step()
    # WAIT ends on the first period with t >= start + wait (the sample times carry rounding).
    assert bench.t_s - decision_s == pytest.approx(ReanchorSettings().wait_s, abs=0.02 + 1e-9)
    v_r = _reanchor_speed(geometry)
    for k in range(move_periods):
        if k > 0:
            command = bench.step()
        np.testing.assert_allclose(
            command / v_r, bench.controller.reanchor_direction(RR), rtol=0, atol=1e-15
        )
    return bench


def test_reanchor_aborts_on_a_light_other_leg_and_returns(geometry) -> None:
    """Q10-4: other leg at F_min + 4.9 kN -> return at once, c back to 0, then LEVEL."""
    bench = _bench_moving(geometry)
    controller = bench.controller
    v_r = _reanchor_speed(geometry)
    forces = bench.forces_N()
    forces[LEG_ORDER.index("FL")] = geometry.F_min_N + 4.9e3
    command = bench.step(forces_N=forces)
    np.testing.assert_allclose(
        command / v_r, -controller.reanchor_direction(RR), rtol=0, atol=1e-15
    )
    assert controller.reanchor_outcome is None  # still returning
    bench.run_while(C2Phase.REANCHOR)
    assert controller.phase is C2Phase.LEVEL
    assert controller.reanchor_outcome == "aborted:other_low"
    np.testing.assert_allclose(bench.travel_m, 0.0, rtol=0, atol=1e-15)
    assert np.max(np.abs(bench.reanchor_outputs)) <= v_r * (1 + 1e-12)
    names = [event.name for event in _decision_events(controller)]
    assert names == [TOUCH_END_EVENT, "reanchor_started", "reanchor_aborted:other_low"]


def test_reanchor_return_scales_the_last_period(geometry) -> None:
    """Q10-5: the last RETURN period runs at lambda < 1 so that c ends exactly at zero.

    MOVE commands whole periods, so in a run lambda < 1 only takes up rounding residue; the
    return law is therefore driven directly with 2.5 periods of travel (private helper).
    """
    controller = C2Controller(geometry)
    v_r = _reanchor_speed(geometry)
    direction = controller.reanchor_direction(RR)
    run = c2_module._ReanchorRun(
        stop_force_N=(45e3,),
        seal_band_used_N=13e3,
        stage_start_s=0.0,
        commanded_m=2.5 * v_r * 0.02 * direction,
    )
    sizes = []
    while (leg_speeds := controller._return_speeds(run)) is not None:
        np.testing.assert_allclose(leg_speeds / np.max(np.abs(leg_speeds)), -direction, atol=1e-12)
        sizes.append(np.max(np.abs(leg_speeds)) / v_r)
    np.testing.assert_allclose(sizes, [1.0, 1.0, 0.5], rtol=1e-9)
    np.testing.assert_allclose(run.commanded_m, 0.0, rtol=0, atol=1e-18)


def test_reanchor_aborts_on_attitude(geometry) -> None:
    bench = _bench_moving(geometry)
    tilt = (math.radians(0.5), 0.0)
    while bench.controller.reanchor_outcome is None and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(tilt_rad=tilt)
    assert bench.controller.reanchor_outcome == "aborted:attitude"
    np.testing.assert_allclose(bench.travel_m, 0.0, rtol=0, atol=1e-15)


def test_reanchor_aborts_at_the_stroke_cap(geometry) -> None:
    """A target that does not unload (floating diagonal, soft floor) stops at 8 mm."""
    bench = _bench_moving(geometry)
    steady = np.full(4, BENCH_LOAD_N)
    while bench.controller.reanchor_outcome is None and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(forces_N=steady)
    assert bench.controller.reanchor_outcome == "aborted:stroke_cap"
    assert bench.controller.phase is C2Phase.LEVEL


def test_reanchor_aborts_on_a_load_drop_in_the_hold(geometry) -> None:
    bench = _bench_moving(geometry, move_periods=1)
    while bench.forces_N()[RR] > 45e3:
        bench.step()
    bench.step()  # MOVE -> HOLD on this reading
    forces = bench.forces_N()
    forces[RR] = geometry.F_min_N - 1.0
    bench.step(forces_N=forces)
    bench.run_while(C2Phase.REANCHOR)
    assert bench.controller.reanchor_outcome == "aborted:hold_low"


def test_reanchor_aborts_on_attitude_while_waiting(geometry) -> None:
    bench = _bench_at_first_done(geometry, 3.0)
    tilt = (math.radians(0.5), 0.0)
    while bench.controller.reanchor_outcome is None and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(tilt_rad=tilt)
    assert bench.controller.reanchor_outcome == "aborted:attitude_wait"
    assert bench.reanchor_outputs and not np.any(bench.reanchor_outputs)


def test_reanchor_runs_once_per_lifting_cycle(geometry) -> None:
    """Four steps RR, RL, RR, RL to the stops, trim to READY; a re-level does not re-anchor
    (Q10-6), ``reset`` arms it again."""
    bench = _bench_at_first_done(geometry, 3.0)
    controller = bench.controller
    bench.step()
    bench.run_while(C2Phase.REANCHOR)
    assert controller.reanchor_outcome == "completed"
    np.testing.assert_allclose(bench.travel_m, 0.0, rtol=0, atol=1e-15)
    stop_readings = controller.meta()["reanchor"]["stop_readings_N"]
    assert [reading["leg"] for reading in stop_readings] == ["RR", "RL", "RR", "RL"]
    stops = controller.reanchor_stop_forces_N(controller.config.initial_seal_band_N)
    for reading, stop in zip(stop_readings, stops, strict=True):
        assert (
            stop - 0.02 * _reanchor_speed(geometry) * BENCH_LOAD_STIFFNESS_N_M
            <= (reading["reading_N"])
        )
        assert reading["reading_N"] <= stop
    bench.run_while(C2Phase.LEVEL)
    bench.step()
    assert controller.phase is C2Phase.READY

    tilt = (math.radians(0.1), 0.0)
    while controller.phase is C2Phase.READY and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(tilt_rad=tilt)
    assert controller.phase is C2Phase.LEVEL
    phases = []
    while controller.phase is not C2Phase.READY and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step()
        phases.append(controller.phase)
    assert controller.phase is C2Phase.READY
    assert C2Phase.REANCHOR not in phases
    assert [event.name for event in _decision_events(controller)] == [
        TOUCH_END_EVENT,
        "reanchor_started",
        "reanchor_completed",
    ]
    controller.reset()
    assert controller.reanchor_outcome is None
    assert _decision_events(controller) == []


# --- REANCHOR direction (spec 82.5, R7 candidate) ---------------------------------------------

NOSE_UP_SLOPE_DEG = -3.2  # 82.5 case P:pitch-3.2 (theta > 0 = nose down)
NOSE_DOWN_SLOPE_DEG = 3.0


@dataclass
class _BenchRun:
    commands: np.ndarray
    phases: list[C2Phase]
    events: list
    outcome: str | None


def _run_bench_to_ready(
    geometry: C2Geometry, theta_crawler_deg: float, direction: ReanchorDirection
) -> _BenchRun:
    """First DONE -> (REANCHOR) -> READY on the synthetic bench, every period recorded."""
    bench = _bench_at_first_done(geometry, theta_crawler_deg, direction=direction)
    controller = bench.controller
    commands, phases = [], []
    while not phases or (controller.phase is not C2Phase.READY and bench.t_s < BENCH_TIME_LIMIT_S):
        commands.append(bench.step())
        phases.append(controller.phase)
    assert controller.phase is C2Phase.READY
    return _BenchRun(
        np.array(commands), phases, _decision_events(controller), controller.reanchor_outcome
    )


def test_reanchor_direction_default_is_nose_down_only() -> None:
    """Decision C first; the R6 and older presets keep both directions."""
    config = C2Config()
    assert config.reanchor.direction is ReanchorDirection.NOSE_DOWN_ONLY
    for legacy in (
        config.with_r6_behaviour(),
        config.with_r5_behaviour(),
        config.with_r41_behaviour(),
    ):
        assert legacy.reanchor.direction is ReanchorDirection.BOTH
    assert replace(config.with_r6_behaviour(), reanchor=config.reanchor) == config
    assert ReanchorSettings(direction="off").direction is ReanchorDirection.OFF
    with pytest.raises(ValueError):
        ReanchorSettings(direction="nose_up_only")


@pytest.mark.parametrize(
    ("direction", "theta_deg", "outcome"),
    [
        (ReanchorDirection.BOTH, NOSE_UP_SLOPE_DEG, "completed"),
        (ReanchorDirection.NOSE_DOWN_ONLY, NOSE_UP_SLOPE_DEG, "skipped:nose_up"),
        (ReanchorDirection.NOSE_DOWN_ONLY, NOSE_DOWN_SLOPE_DEG, "completed"),
        (ReanchorDirection.OFF, NOSE_DOWN_SLOPE_DEG, "skipped:direction_off"),
        (ReanchorDirection.OFF, NOSE_UP_SLOPE_DEG, "skipped:direction_off"),
    ],
)
def test_reanchor_direction_rule(geometry, direction, theta_deg, outcome) -> None:
    """82.5: ``nose_down_only`` applies on ``theta_c - theta_t >= 2.5 deg`` only; a skip is one
    event and the run goes straight on to READY without moving a leg."""
    run = _run_bench_to_ready(geometry, theta_deg, direction)
    assert run.outcome == outcome
    names = [event.name for event in run.events]
    if outcome == "completed":
        assert names == [TOUCH_END_EVENT, "reanchor_started", "reanchor_completed"]
        assert C2Phase.REANCHOR in run.phases
        return
    reason = outcome.removeprefix("skipped:")
    assert names == [TOUCH_END_EVENT, f"reanchor_skipped:{reason}"]
    assert run.phases == [C2Phase.READY]
    np.testing.assert_array_equal(run.commands, 0.0)


def test_nose_down_only_leaves_a_nose_down_run_bit_identical(geometry) -> None:
    """82.5: on a nose-down slope ``nose_down_only`` reproduces ``both`` (R6) bit for bit."""
    both = _run_bench_to_ready(geometry, NOSE_DOWN_SLOPE_DEG, ReanchorDirection.BOTH)
    nose_down = _run_bench_to_ready(geometry, NOSE_DOWN_SLOPE_DEG, ReanchorDirection.NOSE_DOWN_ONLY)
    np.testing.assert_array_equal(nose_down.commands, both.commands)
    assert nose_down.phases == both.phases
    assert nose_down.events == both.events


# --- REANCHOR direction sign (spec revision 20 86.2; dynamics_model.md 5.13.5 supplement 5) ---

# theta_anchor = theta_g + delta_c with the crawler settle offset delta_c 0.17 deg (86.2 table);
# T6 / T7 start from an anchor a completed REANCHOR left at the former target (U3).
CRAWLER_SETTLE_OFFSET_DEG = 0.17
DIRECTION_SIGN_CASES = [
    # (anchor deg, target deg, skip reason of nose_down_only; None = REANCHOR runs)
    pytest.param(-2.0 + CRAWLER_SETTLE_OFFSET_DEG, 1.0, "nose_up", id="T1-up-2.83"),
    pytest.param(2.0 + CRAWLER_SETTLE_OFFSET_DEG, -1.0, None, id="T2-down-3.17"),
    # T3 / T4: the floor sign and the relative sign differ (target != 0)
    pytest.param(-0.5 + CRAWLER_SETTLE_OFFSET_DEG, -3.0, None, id="T3-floor-up-rel-down-2.67"),
    pytest.param(0.3 + CRAWLER_SETTLE_OFFSET_DEG, 3.0, "nose_up", id="T4-floor-down-rel-up-2.53"),
    pytest.param(-2.0 + CRAWLER_SETTLE_OFFSET_DEG, 0.5, "theta_below_min", id="T5-below-2.33"),
    # T6 / T7: after a target change, the anchor is the target of the completed REANCHOR
    pytest.param(3.0, 0.0, None, id="T6-changed-down-3.0"),
    pytest.param(-0.5, 2.5, "nose_up", id="T7-changed-up-3.0"),
]


def _skip_reason_for(
    geometry: C2Geometry,
    anchor_pitch_deg: float,
    target_pitch_deg: float,
    direction: ReanchorDirection = ReanchorDirection.NOSE_DOWN_ONLY,
) -> str | None:
    """``_reanchor_skip_reason`` with ``theta_anchor`` and ``theta_t`` given directly.

    Every other condition holds (lifted, out of the crawler zone, mid stroke, no fallback), so
    only the direction rule and the 2.5 deg threshold decide.
    """
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    config = replace(config, reanchor=replace(config.reanchor, direction=direction))
    controller = C2Controller(geometry, config)
    forces = np.full(4, BENCH_LOAD_N)
    reading = controller._read(_measurements(0.02, geometry, forces, _operating_strokes(geometry)))
    state = controller._state  # the decision is internal; set its inputs directly
    state.reanchor_anchor_pitch_rad = math.radians(anchor_pitch_deg)
    state.active_target = AttitudeTarget.from_degrees(0.0, target_pitch_deg)
    state.is_lifted, state.in_crawler_zone = True, False
    return controller._reanchor_skip_reason(reading)


@pytest.mark.parametrize(("anchor_deg", "target_deg", "reason"), DIRECTION_SIGN_CASES)
def test_reanchor_direction_sign_t1_to_t7(geometry, anchor_deg, target_deg, reason) -> None:
    """86.2 T1-T7: relative nose-up is ``theta_anchor - theta_t < 0`` (theta > 0 = nose down),
    also when the floor sign differs from the relative sign (T3, T4) and after a target change
    (T6, T7); below 2.5 deg the threshold decides first (T5)."""
    assert _skip_reason_for(geometry, anchor_deg, target_deg) == reason


@pytest.mark.parametrize(("anchor_deg", "target_deg", "reason"), DIRECTION_SIGN_CASES)
def test_reanchor_direction_sign_with_both(geometry, anchor_deg, target_deg, reason) -> None:
    """``both`` (R6) runs every T case above the threshold; only T5 is skipped."""
    expected = "theta_below_min" if reason == "theta_below_min" else None
    assert _skip_reason_for(geometry, anchor_deg, target_deg, ReanchorDirection.BOTH) == expected


def test_completed_reanchor_anchors_at_the_target_not_the_attitude(geometry) -> None:
    """5.13.5 supplement 5 (ii), pinned as is: a completed REANCHOR sets ``theta_anchor`` to the
    target pitch ``theta_t``, not to the attitude measured at that moment (here 0.03 deg)."""
    bench = _bench_at_first_done(geometry, NOSE_DOWN_SLOPE_DEG)
    controller = bench.controller
    measured_tilt = (0.0, math.radians(0.03))  # below the 0.07 deg REANCHOR attitude abort
    while controller.reanchor_outcome is None and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(tilt_rad=measured_tilt)
    assert controller.reanchor_outcome == "completed"
    _, target_pitch = controller._target_rad()
    anchor = controller.meta()["reanchor"]["anchor_pitch_rad"]
    assert anchor == target_pitch == 0.0
    assert controller.filtered_attitude_rad[1] > math.radians(0.02)


def test_aborted_reanchor_keeps_the_touch_anchor(geometry) -> None:
    """5.13.5 supplement 5 (ii), pinned as is: an aborted REANCHOR leaves ``theta_anchor`` at
    the TOUCH-end pitch ``theta_crawler``."""
    bench = _bench_moving(geometry)
    steady = np.full(4, BENCH_LOAD_N)  # the target leg never unloads: stroke-cap abort
    while bench.controller.reanchor_outcome is None and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(forces_N=steady)
    meta = bench.controller.meta()["reanchor"]
    assert meta["outcome"] == "aborted:stroke_cap"
    assert meta["anchor_pitch_rad"] == meta["theta_crawler_rad"]


def test_relevel_after_a_disturbance_keeps_the_anchor(geometry) -> None:
    """5.13.5 supplement 5 (ii), pinned as is: there is no slip detection, so a READY re-level
    after an attitude change (as a pad slip would cause) leaves ``theta_anchor`` unchanged."""
    bench = _bench_at_first_done(
        geometry, NOSE_UP_SLOPE_DEG, direction=ReanchorDirection.NOSE_DOWN_ONLY
    )
    controller = bench.controller
    bench.step()
    assert controller.reanchor_outcome == "skipped:nose_up"
    anchor_before = controller.meta()["reanchor"]["anchor_pitch_rad"]
    assert anchor_before == controller.meta()["reanchor"]["theta_crawler_rad"]
    disturbed = (0.0, math.radians(0.1))
    while controller.phase is C2Phase.READY and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step(tilt_rad=disturbed)
    assert controller.phase is C2Phase.LEVEL
    while controller.phase is not C2Phase.READY and bench.t_s < BENCH_TIME_LIMIT_S:
        bench.step()
    assert controller.phase is C2Phase.READY
    assert controller.meta()["reanchor"]["anchor_pitch_rad"] == anchor_before


def test_meta_records_the_reanchor_direction() -> None:
    """86.1 / 86.6 (return condition 1): revision R7 and the direction of every preset."""
    config = C2Config()
    expected = {
        "default": (config, "nose_down_only"),
        "r6": (config.with_r6_behaviour(), "both"),
        "r5": (config.with_r5_behaviour(), "both"),
        "r41": (config.with_r41_behaviour(), "both"),
        "off": (replace(config, reanchor=ReanchorSettings(direction="off")), "off"),
    }
    for name, (preset, direction) in expected.items():
        meta = C2Controller.from_params(load_params(), preset).meta()
        json.dumps(meta)
        assert meta["revision"] == "R7", name
        assert meta["reanchor_direction"] == direction, name
        assert meta["reanchor"]["settings"]["direction"] == direction, name


# --- regression against the reduced model ----------------------------------------------------


def _replay(
    geometry: C2Geometry,
    rows: np.ndarray,
    contact: ContactJudge,
    *,
    seal_band_N: float = REDUCED_MODEL_SEAL_BAND_N,
    reanchor: ReanchorSettings | None = None,
) -> tuple[np.ndarray, list[str], C2Controller]:
    # The reduced model has no CHECK phase and no target check; the traces go beyond the D8
    # operating and verification limits (roll 5.7, pitch +-3.7 deg).
    config = C2Config(
        contact=contact,
        initial_seal_band_N=seal_band_N,
        output_ramp_time_s=None,
        reanchor=ReanchorSettings() if reanchor is None else reanchor,
        target=REPLAY_TARGET_SETTINGS,
        probe=R2_PROBE,
        thresholds=R2_THRESHOLDS,
    ).with_r41_behaviour()
    controller = C2Controller(geometry, config)
    outputs, phases = [], []
    for row in rows:
        measurements = Measurements(
            t_s=float(row["t_s"]),
            specific_force_m_s2=row["specific_force_m_s2"],
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=row["cylinder_force_N"] / geometry.head_area_m2,
            stroke_m=row["motor_stroke_m"],
            stroke_corrected_m=row["rod_stroke_m"],
        )
        outputs.append(controller.update(measurements).leg_speed_m_s)
        phases.append(controller.phase.name)
    return np.array(outputs), phases, controller


def _expected_phases(meta: dict, rows: np.ndarray) -> list[str]:
    code_to_name = {code: name for name, code in meta["phase_codes"].items()}
    return [code_to_name[int(code)] for code in rows["phase_code"]]


def _assert_matches_trace(
    geometry: C2Geometry,
    case_name: str,
    rows: np.ndarray,
    expected_phases: list[str],
    outputs: np.ndarray,
    phases: list[str],
) -> None:
    """Phases equal; outputs to the last bits up to the first READY, then within the rounding.

    The reduced model rounds the probe estimates to 0.01 kN before it sets F_band, and F_band
    enters the guard through P - F_band. After the first probe the outputs may therefore differ
    by up to K_g (5 N) / k_nom. A run that never reaches READY is compared to the last bits.
    """
    first_phase_mismatch = next(
        (
            k
            for k, pair in enumerate(zip(phases, expected_phases, strict=True))
            if pair[0] != pair[1]
        ),
        None,
    )
    assert first_phase_mismatch is None, (
        f"{case_name}: phase differs from step {first_phase_mismatch} "
        f"(t {rows['t_s'][first_phase_mismatch]:.2f} s)"
    )
    expected_outputs = rows["leg_speed_m_s"]
    first_ready = (
        expected_phases.index("READY") if "READY" in expected_phases else len(expected_phases)
    )
    np.testing.assert_allclose(
        outputs[: first_ready + 1],
        expected_outputs[: first_ready + 1],
        rtol=0,
        atol=REPLAY_TOLERANCE_M_S,
        err_msg=case_name,
    )
    rounding_tolerance = (
        C2Gains().guard_kg_1_s * PROBE_ROUNDING_N / geometry.nominal_pad_stiffness_N_m
    )
    np.testing.assert_allclose(
        outputs, expected_outputs, rtol=0, atol=rounding_tolerance, err_msg=case_name
    )


REPLAY_CASE_COUNT = 8  # cases 6 (top pitch +3.5 deg) and 7 (stroke-end fault) came with R1
# R1 case on a fore-aft slope >= 2.5 deg: R2 re-anchors at its first DONE, where the R1 trace
# went on to READY; the R2 traces below are the reference from there on.
R1_CASES_WITH_REANCHOR = (6,)


def test_trace_file_holds_every_replay_case(trace_meta) -> None:
    assert len(trace_meta["cases"]) == REPLAY_CASE_COUNT
    assert trace_meta["revision"].startswith("R1")


@pytest.mark.parametrize("case_index", range(REPLAY_CASE_COUNT))
def test_replay_matches_the_reduced_model(
    legacy_geometry, trace_meta, trace_rows, case_index
) -> None:
    """Revision R1 traces with the R2 default: unchanged wherever REANCHOR does not apply."""
    case = trace_meta["cases"][case_index]
    rows = trace_rows[trace_rows["case"] == case_index]
    contact = ContactJudge(case["kwargs"].get("contact", "pressure"))
    outputs, phases, controller = _replay(legacy_geometry, rows, contact)
    expected_phases = _expected_phases(trace_meta, rows)

    if case_index not in R1_CASES_WITH_REANCHOR:
        outcome = controller.reanchor_outcome
        assert outcome is None or outcome.startswith("skipped:"), outcome
        _assert_matches_trace(legacy_geometry, case["name"], rows, expected_phases, outputs, phases)
        return
    start = phases.index("REANCHOR")
    assert expected_phases[start - 1 : start + 1] == ["DONE", "READY"]
    _assert_matches_trace(
        legacy_geometry,
        case["name"],
        rows[:start],
        expected_phases[:start],
        outputs[:start],
        phases[:start],
    )


@pytest.mark.parametrize("case_index", R1_CASES_WITH_REANCHOR)
def test_replay_without_reanchor_is_revision_r1(
    legacy_geometry, trace_meta, trace_rows, case_index
) -> None:
    case = trace_meta["cases"][case_index]
    rows = trace_rows[trace_rows["case"] == case_index]
    outputs, phases, controller = _replay(
        legacy_geometry, rows, ContactJudge.PRESSURE, reanchor=ReanchorSettings(enable=False)
    )
    assert controller.reanchor_outcome == "skipped:disabled"
    expected_phases = _expected_phases(trace_meta, rows)
    _assert_matches_trace(legacy_geometry, case["name"], rows, expected_phases, outputs, phases)


def test_replay_of_the_stroke_end_case_faults(legacy_geometry, trace_meta, trace_rows) -> None:
    case_index = 7
    assert trace_meta["cases"][case_index]["fails"] == ["stroke_end_fault"]
    rows = trace_rows[trace_rows["case"] == case_index]
    outputs, phases, _ = _replay(legacy_geometry, rows, ContactJudge.PRESSURE)
    assert phases[-1] == "FAULT"
    fault_start = phases.index("FAULT")
    np.testing.assert_array_equal(outputs[fault_start:], 0.0)


def test_replay_of_the_combined_judge_probes_twice(legacy_geometry, trace_meta, trace_rows) -> None:
    case_index = 5
    case = trace_meta["cases"][case_index]
    # R1: every pad is loaded at LEVEL entry, so no leg needs re-grounding (it3 had 3 rounds
    # with an FR re-grounding). The second round follows the low-load re-level after settling.
    assert case["probe_rounds"] == 2
    assert [name for _, name in case["events"]] == ["crawler_zone_off", "relevel_lowload"]
    rows = trace_rows[trace_rows["case"] == case_index]
    assert rows["guard_steps"][-1] > 0, "the settling case should exercise the F_min guard"
    _, phases, controller = _replay(legacy_geometry, rows, ContactJudge.COMBINED)
    history = controller.probe_history
    assert len(history) == 2
    assert all(len(results) == 4 for results in history)
    guard_level = legacy_geometry.F_min_N + C2Thresholds().guard_margin_N
    first_round = history[0]
    assert all(r.is_grounded and r.load_estimate_N >= guard_level for r in first_round)
    assert controller.seal_band_N >= REDUCED_MODEL_SEAL_BAND_N
    assert phases[-1] == "READY"


# --- regression of revision R2 (design 17.7 Q11, Q12) ----------------------------------------

REANCHOR_TRACE_STEM = "c2_reanchor_traces"
REANCHOR_CASE_COUNT = 2
REANCHOR_SEAL_BAND_N = 13e3  # D5 start value, as the re-anchoring design runs
# Q11 regression values (top, nose-down 3.5 deg, rigid mast, seed 12345, delay 1, pressure).
Q11_STOP_READINGS_KN = [44.73, 32.32, 32.39, 32.21]
Q11_THETA_CRAWLER_DEG = 3.755


@pytest.fixture(scope="module")
def reanchor_meta() -> dict:
    path = TRACE_DIR / f"{REANCHOR_TRACE_STEM}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reanchor_rows() -> np.ndarray:
    return np.load(TRACE_DIR / f"{REANCHOR_TRACE_STEM}.npy", allow_pickle=False)


def _replay_reanchor_case(
    geometry: C2Geometry, meta: dict, all_rows: np.ndarray, case_index: int
) -> tuple[np.ndarray, list[str], C2Controller, np.ndarray]:
    case = meta["cases"][case_index]
    rows = all_rows[all_rows["case"] == case_index]
    contact = ContactJudge(case["kwargs"].get("contact", "pressure"))
    outputs, phases, controller = _replay(geometry, rows, contact, seal_band_N=REANCHOR_SEAL_BAND_N)
    return outputs, phases, controller, rows


def test_reanchor_trace_file(reanchor_meta) -> None:
    assert len(reanchor_meta["cases"]) == REANCHOR_CASE_COUNT
    assert reanchor_meta["revision"].startswith("R2")
    assert reanchor_meta["reanchor_variant"] == "H4"
    assert reanchor_meta["seal_band_N"] == REANCHOR_SEAL_BAND_N


@pytest.mark.parametrize("case_index", range(REANCHOR_CASE_COUNT))
def test_replay_matches_the_reanchor_model(
    legacy_geometry, reanchor_meta, reanchor_rows, case_index
) -> None:
    """Q12: c2.py reproduces ``C2RN`` (H4) including REANCHOR, trim, probe and READY."""
    outputs, phases, controller, rows = _replay_reanchor_case(
        legacy_geometry, reanchor_meta, reanchor_rows, case_index
    )
    case = reanchor_meta["cases"][case_index]
    expected_phases = _expected_phases(reanchor_meta, rows)
    _assert_matches_trace(legacy_geometry, case["name"], rows, expected_phases, outputs, phases)
    reference = case["reanchor"]
    assert controller.reanchor_outcome == reference["outcome"] == "completed"
    reanchor = controller.meta()["reanchor"]
    # F_min of the YAML and of the reduced model agree to 1e-8 (legacy_geometry test above).
    np.testing.assert_allclose(reanchor["stop_force_N"], reference["P_stop_N"], rtol=1e-8)
    reference_stops = [entry["P_kN"] for entry in reference["log"] if entry["what"] == "hold"]
    readings_kN = [round(entry["reading_N"] / 1e3, 2) for entry in reanchor["stop_readings_N"]]
    assert readings_kN == reference_stops
    assert math.degrees(reanchor["theta_crawler_rad"]) == pytest.approx(
        reference["theta_ground_deg"], abs=5e-4
    )


def test_reanchor_regression_values(legacy_geometry, reanchor_meta, reanchor_rows) -> None:
    """Q11: REANCHOR 38.10 -> 52.58 s, READY 53.64 s, stops 44.73 / 32.32 / 32.39 / 32.21 kN."""
    outputs, phases, controller, rows = _replay_reanchor_case(
        legacy_geometry, reanchor_meta, reanchor_rows, 0
    )
    times = rows["t_s"]
    is_moving = (np.array(phases) == "REANCHOR") & np.any(outputs != 0.0, axis=1)
    assert times[np.argmax(is_moving)] == pytest.approx(38.10, abs=1e-9)
    assert times[phases.index("READY")] == pytest.approx(53.64, abs=1e-9)
    event_times = {event.name: event.t_s for event in _decision_events(controller)}
    assert event_times.pop(TOUCH_END_EVENT) < event_times["reanchor_started"]
    assert event_times == pytest.approx({"reanchor_started": 36.08, "reanchor_completed": 52.58})

    reanchor = controller.meta()["reanchor"]
    assert [entry["leg"] for entry in reanchor["stop_readings_N"]] == ["RR", "RL", "RR", "RL"]
    readings_kN = [round(entry["reading_N"] / 1e3, 2) for entry in reanchor["stop_readings_N"]]
    assert readings_kN == Q11_STOP_READINGS_KN
    assert round(math.degrees(reanchor["theta_crawler_rad"]), 3) == Q11_THETA_CRAWLER_DEG
    np.testing.assert_allclose(
        reanchor["stop_force_N"],
        [45e3, 32452.6, 32452.6, 32452.6],
        rtol=0,
        atol=Q10_STOP_TOLERANCE_N,
    )
    assert reanchor["seal_band_used_N"] == REANCHOR_SEAL_BAND_N
    # Plant-side values of the same run (reference model record, not seen by c2.py).
    reference = reanchor_meta["cases"][0]["reanchor"]
    assert reference["Ft_maxleg_final_kN"] == 16.81
    assert reference["min_true_cyl_force_substep_kN"] == 29.61


def test_reanchor_band_exceeded_after_the_probe(
    legacy_geometry, reanchor_meta, reanchor_rows
) -> None:
    """Q8: the probe after the trim widens F_band past the 13 kN the stops used -> event."""
    _, phases, controller, _ = _replay_reanchor_case(
        legacy_geometry, reanchor_meta, reanchor_rows, 1
    )
    assert phases[-1] == "READY"
    assert len(controller.probe_history) == reanchor_meta["cases"][1]["probe_rounds"] == 1
    assert controller.seal_band_N > REANCHOR_SEAL_BAND_N
    names = [event.name for event in _decision_events(controller)]
    assert names == [
        TOUCH_END_EVENT,
        "reanchor_started",
        "reanchor_completed",
        "reanchor_band_exceeded",
    ]


# --- revision R4 (spec 18.1 P1-P3, 20.2 P5, 20.4 P6) -----------------------------------------

R4_TRACE_STEM = "c2_r4_traces"


@pytest.fixture(scope="module")
def r4_meta() -> dict:
    return json.loads((TRACE_DIR / f"{R4_TRACE_STEM}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r4_rows() -> np.ndarray:
    return np.load(TRACE_DIR / f"{R4_TRACE_STEM}.npy", allow_pickle=False)


def _trace_controller(
    case: dict, probe: ProbeSettings, *, is_r41_behaviour: bool = True
) -> C2Controller:
    """Controller of ``export_c2_r4_traces.py``; R5 changes off unless ``is_r41_behaviour``
    is False; the legacy YAML the traces were recorded with."""
    params = load_params(LEGACY_PARAMS_PATH)
    target = TargetSettings()
    if case["is_verification"]:
        target = TargetSettings(
            slope_limit_mode=SlopeLimitMode.VERIFICATION,
            crawler_settle_map=CrawlerSettleMap.for_level("top"),
        )
    ramp_s = params.actuator.command_ramp_s
    config = C2Config(target=target, probe=probe, output_ramp_time_s=ramp_s if ramp_s > 0 else None)
    if is_r41_behaviour:
        config = config.with_r41_behaviour()
    return C2Controller.from_params(params, config)


def _replay_trace(
    controller: C2Controller,
    summary: dict,
    rows: np.ndarray,
    after_step: Callable[[], None] | None = None,
) -> tuple[np.ndarray, list[str]]:
    change_t_s = summary["target_change_t_s"]
    change = summary["case"]["target_change_deg"]
    outputs, phases = [], []
    for row in rows:
        if change_t_s is not None and float(row["t_s"]) == change_t_s:
            controller.request_target(AttitudeTarget.from_degrees(*change))
        measurements = Measurements(
            t_s=float(row["t_s"]),
            specific_force_m_s2=row["specific_force_m_s2"],
            angular_rate_rad_s=row["angular_rate_rad_s"],
            head_pressure_Pa=row["head_pressure_Pa"],
            stroke_m=row["stroke_m"],
            stroke_corrected_m=row["stroke_corrected_m"],
        )
        outputs.append(controller.update(measurements).leg_speed_m_s)
        phases.append(str(controller.phase))
        if after_step is not None:
            after_step()
    return np.array(outputs), phases


@pytest.mark.parametrize("case_index", range(4))
def test_replay_matches_the_r4_traces(r4_meta, r4_rows, case_index) -> None:
    """P3: the R4 settings (R4.1 judge changes off) reproduce the R4 traces bit for bit."""
    assert r4_meta["revision"] == "R4"
    summary = r4_meta["cases"][case_index]
    rows = r4_rows[r4_rows["case"] == case_index]
    controller = _trace_controller(summary["case"], R4_PROBE)
    outputs, phases = _replay_trace(controller, summary, rows)
    np.testing.assert_array_equal(outputs, rows["leg_speed_m_s"])
    assert phases == rows["phase"].tolist()
    decisions = [[event.t_s, event.name] for event in _decision_events(controller)]
    assert decisions == summary["events"]


# --- revision R4.1 (spec 21.3 Q1-Q3, 29 K1 / GE1) --------------------------------------------

R41_TRACE_STEM = "c2_r41_traces"


@pytest.fixture(scope="module")
def r41_meta() -> dict:
    return json.loads((TRACE_DIR / f"{R41_TRACE_STEM}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def r41_rows() -> np.ndarray:
    return np.load(TRACE_DIR / f"{R41_TRACE_STEM}.npy", allow_pickle=False)


@pytest.mark.parametrize("case_index", range(4))
def test_replay_matches_the_r41_traces(r41_meta, r41_rows, case_index) -> None:
    """R5 legacy (``with_r41_behaviour``) against the R4.1 traces (spec 44.5, R5-L).

    Bit for bit: every command ``u``, every phase, every event with its time except the
    ``shadow_*`` events (the GE1' shadow is R5 in either setting and decides nothing), and the
    probe-round count and REANCHOR outcomes the traces record. Only ``shadow_*`` is left out:
    an ``INFO_FLOOR_NONPLANAR`` (or any other event) would make the lists differ. The R4.1
    trace files keep no per-leg probe results, so those are compared through their effects
    (commands, phases, events, round count).
    """
    assert r41_meta["revision"] == "R4.1"
    summary = r41_meta["cases"][case_index]
    rows = r41_rows[r41_rows["case"] == case_index]
    controller = _trace_controller(summary["case"], ProbeSettings())
    outputs, phases = _replay_trace(controller, summary, rows)
    np.testing.assert_array_equal(outputs, rows["leg_speed_m_s"])
    assert phases == rows["phase"].tolist()

    def without_shadow(events: list[list]) -> list[list]:
        return [event for event in events if not event[1].startswith(SHADOW_EVENT_PREFIX)]

    events = [[event.t_s, event.name] for event in controller.events]
    assert without_shadow(events) == without_shadow(summary["events"])
    assert len(controller.probe_history) == summary["probe_rounds"]
    reanchor = controller.meta()["reanchor"]
    assert reanchor["outcomes"] == summary["reanchor_outcomes"]
    assert str(controller.phase) == summary["final_phase"]


@pytest.mark.parametrize("case_index", range(4))
def test_r41_traces_raise_no_shadow_flag_while_the_body_turns(
    r41_meta, r41_rows, case_index
) -> None:
    """Spec 32.1 / 42.1 GE1'-c regression: R4.1 flagged G1' in LEVEL (attitude filter lag);
    replayed through the R5 shadow the gate opens only in DONE / PROBE / READY and no flag is
    raised."""
    summary = r41_meta["cases"][case_index]
    assert any(name.startswith("shadow_G1") for _, name in summary["events"])  # R4.1 did
    rows = r41_rows[r41_rows["case"] == case_index]
    controller = _trace_controller(summary["case"], ProbeSettings())
    phases_with_valid_geometry: set[str] = set()

    def note_gate() -> None:
        if controller.is_geometry_valid:
            phases_with_valid_geometry.add(str(controller.phase))

    _replay_trace(controller, summary, rows, after_step=note_gate)
    assert phases_with_valid_geometry <= {"done", "probe", "ready"}
    if summary["name"] == "top_pitch+3.5":
        # The R4.1 CHECK bias absorbed the 1.3 Hz crawler rocking (spec 32.2): -105 deg/h is
        # left on the bias-removed rate in READY (0.029 deg/s > 0.02), so the gate stays shut.
        # R5 B1' would not accept that estimate (> 60 deg/h plausibility).
        assert abs(controller.gyro_bias_rad_s[1]) > deg_per_hour(60.0)
        assert phases_with_valid_geometry == set()
    else:
        assert "ready" in phases_with_valid_geometry
    flags = [event.name for event in controller.events if event.name.startswith("shadow_")]
    assert flags == []


def test_r4_defaults() -> None:
    config = C2Config()
    assert config.probe.profile is ProbeProfile.TRAPEZOID
    assert config.probe.stroke_guard_margin_m == 5e-3
    assert config.thresholds.integrator_band_mode is IntegratorBandMode.JOINT
    assert config.thresholds.relevel_load_margin_N == 7500.0  # U68 (R6)
    assert config.with_r5_behaviour().thresholds.relevel_load_margin_N == 7000.0


def test_relevel_margin_must_clear_the_guard() -> None:
    """P5 / 65.2: relevel_load_margin_N >= guard_margin_N + 2.5 kN unless replaying R2-R5."""
    with pytest.raises(ValueError, match="relevel_load_margin_N"):
        C2Thresholds(relevel_load_margin_N=3000.0)
    with pytest.raises(ValueError, match="relevel_load_margin_N"):
        C2Thresholds(relevel_load_margin_N=7000.0)
    C2Thresholds(relevel_load_margin_N=7500.0)
    C2Thresholds(relevel_load_margin_N=3000.0, allow_legacy_relevel_margin=True)


@pytest.mark.parametrize(
    ("mode", "pitch_charges"), [(IntegratorBandMode.JOINT, False), (IntegratorBandMode.AXIS, True)]
)
def test_joint_band_keeps_the_quiet_axis_from_charging(geometry, mode, pitch_charges) -> None:
    """P2: roll error 0.5 deg (outside the band), pitch 0.05 deg (inside), from the start."""
    thresholds = C2Thresholds(integrator_band_mode=mode)
    config = C2Config(target=NO_CHECK, contact=ContactJudge.PRESSURE, thresholds=thresholds)
    controller = C2Controller(geometry, config)
    strokes = _operating_strokes(geometry)
    tilt = (math.radians(0.5), math.radians(0.05))
    for k in range(TOUCH_HOLD_SAMPLES + 100):
        measurements = _measurements(
            0.02 * (k + 1), geometry, np.full(4, 80e3), strokes, tilt_rad=tilt
        )
        controller.update(measurements)
    assert controller.phase is C2Phase.LEVEL
    state = controller._state  # integrators are internal; read them directly in this test
    assert (abs(state.pitch_integral) > 0.0) is pitch_charges
    assert state.roll_integral == 0.0


def test_probe_skips_a_leg_at_the_stroke_end(geometry) -> None:
    """P6: legs with s > s_max - 5 mm are not probed; event, no re-grounding of them."""
    strokes = _operating_strokes(geometry)
    short = replace(geometry, stroke_max_m=float(strokes.min()) + 0.004)  # all s > s_max - 5 mm
    controller = _probe_with_loads(short, np.full(4, 80e3))
    assert all(result.is_skipped for result in controller.probe_history[0])
    names = [event.name for event in _decision_events(controller)]
    assert names.count("probe_skipped:stroke_margin") == 4
    assert controller.phase is C2Phase.READY
