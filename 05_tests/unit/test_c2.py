"""Unit tests of the C2 levelling controller (00_docs/04_control/c2_design.md 14.8).

The regression test replays control-step traces of the reduced model the design was verified
on (``04_scripts/03_control/run_c2_timedomain.py``, gain set ``it3_proposal``). The traces
are made by ``04_scripts/03_control/export_c2_regression_traces.py`` (needs numba, so it runs
in dynamics-dev, not here).
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Gains,
    C2Geometry,
    C2Phase,
    C2Thresholds,
    ContactJudge,
    scale_to_speed_limit,
    twist_rate_command,
)
from outrigger_sim.control.protocol import Controller
from outrigger_sim.params import load_params
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


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


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


def _level_after_touch(geometry: C2Geometry, config: C2Config) -> tuple[C2Controller, np.ndarray]:
    """Controller in LEVEL after one touchdown sample; returns it and the strokes used."""
    controller = C2Controller(geometry, config)
    strokes = _operating_strokes(geometry)
    controller.update(_measurements(0.02, geometry, np.full(4, 80e3), strokes))
    assert controller.phase is C2Phase.LEVEL
    return controller, strokes


# --- geometry -------------------------------------------------------------------------------


def test_geometry_matches_the_reduced_model_context(geometry, trace_meta) -> None:
    context = trace_meta["context"]
    np.testing.assert_allclose(geometry.support_matrix, context["A"], rtol=0, atol=1e-15)
    np.testing.assert_allclose(geometry.twist_vector, context["n"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        geometry.twist_vector, [0.476, -0.476, -0.523, 0.523], rtol=0, atol=1e-3
    )
    assert geometry.nominal_pad_stiffness_N_m == pytest.approx(context["k_nom_N_m"], rel=1e-15)
    np.testing.assert_allclose(
        geometry.load_sensitivity_diag_N_m, context["S_nom_diag_N_m"], rtol=1e-9
    )
    assert geometry.F_min_N == pytest.approx(context["F_min_N"], rel=1e-8)
    assert geometry.max_speed_m_s == context["v_max_m_s"]
    assert geometry.stroke_max_m == context["stroke_max_m"]
    np.testing.assert_array_equal(geometry.crawler_corners_xy_m, context["crawler_corners_xy_m"])
    assert geometry.head_area_m2 == pytest.approx(context["piston_area_m2"], rel=1e-15)


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
    controller = C2Controller(geometry, C2Config(contact=ContactJudge.PRESSURE))
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
    roll, pitch = controller.filtered_attitude_rad
    assert roll / tilt == pytest.approx(expected, rel=1e-12)
    assert pitch == 0.0


def test_touch_extends_until_each_leg_bears_load(geometry) -> None:
    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller = C2Controller(geometry, config)
    strokes = np.full(4, 0.1)
    v_max = geometry.max_speed_m_s
    forces = np.array([20e3, 0.0, 0.0, 0.0])
    command = controller.update(_measurements(0.02, geometry, forces, strokes))
    np.testing.assert_array_equal(command.leg_speed_m_s, [0.0, v_max, v_max, v_max])
    assert controller.phase is C2Phase.TOUCH
    controller.update(_measurements(0.04, geometry, np.full(4, 20e3), strokes))
    assert controller.phase is C2Phase.LEVEL


def test_output_ramp_limits_the_change_per_period(geometry) -> None:
    controller = C2Controller(geometry, C2Config(contact=ContactJudge.PRESSURE))
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
    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller, strokes = _level_after_touch(geometry, config)
    command = controller.update(_measurements(0.04, geometry, np.full(4, 80e3), strokes))
    heave, roll, pitch, twist = geometry.decompose(command.leg_speed_m_s)
    clearance = geometry.clearance_estimate_m(strokes)
    assert heave == pytest.approx(0.5 * (0.05 - clearance), abs=1e-15)
    assert (roll, pitch, twist) == pytest.approx((0.0, 0.0, 0.0), abs=1e-15)


def test_completion_after_the_hold_time_then_ready(geometry) -> None:
    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller, strokes = _level_after_touch(geometry, config)
    t_s = 0.02
    while controller.phase is C2Phase.LEVEL and t_s < 5.0:
        t_s += 0.02
        controller.update(_measurements(t_s, geometry, np.full(4, 80e3), strokes))
    assert controller.phase is C2Phase.DONE
    assert t_s == pytest.approx(0.04 + 1.0)
    command = controller.update(_measurements(t_s + 0.02, geometry, np.full(4, 80e3), strokes))
    assert controller.phase is C2Phase.READY
    np.testing.assert_array_equal(command.leg_speed_m_s, np.zeros(4))
    tilted = _measurements(t_s + 0.04, geometry, np.full(4, 80e3), strokes, tilt_rad=(0.01, 0))
    for _ in range(200):
        controller.update(tilted)
        if controller.phase is C2Phase.LEVEL:
            break
    assert controller.phase is C2Phase.LEVEL


def test_stroke_end_fault_after_two_seconds(geometry) -> None:
    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    controller, _ = _level_after_touch(geometry, config)
    # Every leg at its end with a low clearance estimate: the crawler zone asks to extend.
    at_end = np.full(4, geometry.stroke_max_m)
    rod_strokes = np.zeros(4)
    for k in range(101):
        measurements = Measurements(
            t_s=0.04 + 0.02 * k,
            specific_force_m_s2=[0.0, 0.0, GRAVITY_M_S2],
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=np.full(4, 80e3 / geometry.head_area_m2),
            stroke_m=at_end,
            stroke_corrected_m=rod_strokes,
        )
        command = controller.update(measurements)
        if k < 100:
            assert controller.phase is C2Phase.LEVEL
            np.testing.assert_array_equal(command.leg_speed_m_s, np.zeros(4))
    assert controller.phase is C2Phase.FAULT
    level = _measurements(3.0, geometry, np.full(4, 80e3), _operating_strokes(geometry))
    np.testing.assert_array_equal(controller.update(level).leg_speed_m_s, np.zeros(4))
    assert controller.phase is C2Phase.FAULT


def test_missing_corrected_stroke_uses_the_oil_column(geometry) -> None:
    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None)
    forces = np.full(4, 80e3)
    motor = _operating_strokes(geometry)
    rod = motor - forces / geometry.oil_stiffness_N_m(motor)
    with_rod = C2Controller(geometry, config)
    without_rod = C2Controller(geometry, config)
    for k in range(3):
        given = replace(_measurements(0.02 * (k + 1), geometry, forces, rod), stroke_m=motor)
        derived = replace(given, stroke_corrected_m=None)
        np.testing.assert_allclose(
            without_rod.update(derived).leg_speed_m_s,
            with_rod.update(given).leg_speed_m_s,
            rtol=0,
            atol=1e-15,
        )


def test_protocol_reset_and_meta() -> None:
    controller = C2Controller.from_params(load_params())
    geometry = controller.geometry
    assert isinstance(controller, Controller)
    assert controller.period_s == 0.02
    meta = controller.meta()
    json.dumps(meta)
    assert meta["controller"] == "C2"
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


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        C2Config(output_ramp_time_s=0.0)
    with pytest.raises(ValueError):
        C2Config(period_s=0.0)
    with pytest.raises(ValueError):
        C2Config(contact="pressure-only")


# --- regression against the reduced model ----------------------------------------------------


def _replay(
    geometry: C2Geometry, rows: np.ndarray, contact: ContactJudge
) -> tuple[np.ndarray, list[str], C2Controller]:
    config = C2Config(
        contact=contact,
        initial_seal_band_N=REDUCED_MODEL_SEAL_BAND_N,
        output_ramp_time_s=None,
    )
    controller = C2Controller(geometry, config)
    outputs, phases = [], []
    for row in rows:
        measurements = Measurements(
            t_s=float(row["t_s"]),
            specific_force_m_s2=row["specific_force_m_s2"],
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=row["cylinder_force_N"] / geometry.head_area_m2,
            stroke_m=row["rod_stroke_m"],
            stroke_corrected_m=row["rod_stroke_m"],
        )
        outputs.append(controller.update(measurements).leg_speed_m_s)
        phases.append(controller.phase.name)
    return np.array(outputs), phases, controller


@pytest.mark.parametrize("case_index", range(6))
def test_replay_matches_the_reduced_model(geometry, trace_meta, trace_rows, case_index) -> None:
    case = trace_meta["cases"][case_index]
    rows = trace_rows[trace_rows["case"] == case_index]
    contact = ContactJudge(case["kwargs"].get("contact", "pressure"))
    outputs, phases, _ = _replay(geometry, rows, contact)

    code_to_name = {code: name for name, code in trace_meta["phase_codes"].items()}
    expected_phases = [code_to_name[int(code)] for code in rows["phase_code"]]
    first_phase_mismatch = next(
        (
            k
            for k, pair in enumerate(zip(phases, expected_phases, strict=True))
            if pair[0] != pair[1]
        ),
        None,
    )
    assert first_phase_mismatch is None, (
        f"{case['name']}: phase differs from step {first_phase_mismatch} "
        f"(t {rows['t_s'][first_phase_mismatch]:.2f} s)"
    )
    expected_outputs = rows["leg_speed_m_s"]
    # The reduced model rounds the probe estimates to 0.01 kN before it sets F_band, and F_band
    # enters the guard through P - F_band. After the first probe the outputs may therefore
    # differ by up to K_g (5 N) / k_nom; up to then they must agree to the last bits.
    first_ready = expected_phases.index("READY")
    np.testing.assert_allclose(
        outputs[: first_ready + 1],
        expected_outputs[: first_ready + 1],
        rtol=0,
        atol=REPLAY_TOLERANCE_M_S,
        err_msg=case["name"],
    )
    rounding_tolerance = (
        C2Gains().guard_kg_1_s * PROBE_ROUNDING_N / geometry.nominal_pad_stiffness_N_m
    )
    np.testing.assert_allclose(
        outputs, expected_outputs, rtol=0, atol=rounding_tolerance, err_msg=case["name"]
    )
    assert rows["guard_steps"][-1] > 0, "the case should exercise the F_min guard"


def test_replay_of_the_combined_judge_probes_and_regrounds(
    geometry, trace_meta, trace_rows
) -> None:
    case_index = 5
    assert trace_meta["cases"][case_index]["probe_rounds"] == 3
    rows = trace_rows[trace_rows["case"] == case_index]
    _, _, controller = _replay(geometry, rows, ContactJudge.COMBINED)
    history = controller.probe_history
    assert len(history) == 3
    assert all(len(results) == 4 for results in history)
    assert controller.seal_band_N >= REDUCED_MODEL_SEAL_BAND_N
    # The FR re-grounding of the reduced model (event 'probe_reground_FR').
    front_right = history[1][1]
    assert front_right.leg_index == 1
    is_weak = not front_right.is_grounded or front_right.load_estimate_N < geometry.F_min_N + 5e3
    assert is_weak
