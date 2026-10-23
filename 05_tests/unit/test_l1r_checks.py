"""L1-R checks (``verify/l1r``): V7a gate, V7b metrics, V5 +0.3 mm / V9-1 (5.14.12 rule)
and V9-2."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.verify.l1r import (
    V7B_FLOOR_DWELL_ABS_TOL_S,
    KneeRecord,
    ModalRecord,
    ModuleRecord,
    floor_distance_record,
    knee_record,
    local_maxima,
    modal_record,
    mode_amplitude_phase_at,
    predictor_off_order_check,
    predictor_off_record,
    smooth_step_record,
    smooth_validity_checks,
    transient_match_record,
    up_crossing_times,
    v5_smooth_checks,
    v7a_gate_checks,
    v7a_mode_checks,
    v7b_checks,
    v9_free_checks,
    v9_smooth_checks,
)
from outrigger_sim.verify.s4 import ModeRow

LOCK = int(RodChamberMode.LOCK)
FLOOR = int(RodChamberMode.FLOOR)
LIFT = int(RodChamberMode.LIFT)
KNEE_N = [4089.04, 4089.04, 3170.13, 3170.13]
DT_S = 1.0e-3


def _module(normal_N: np.ndarray, mode: np.ndarray, dt_s: float = DT_S) -> ModuleRecord:
    t_s = dt_s * np.arange(1, len(normal_N) + 1)
    return ModuleRecord.from_arrays(t_s, normal_N, mode, dt_s)


def _all_lock(n_steps: int) -> np.ndarray:
    return np.full((n_steps, 4), LOCK)


# --- module records ---------------------------------------------------------------------------


def test_knee_record_counts_lock_floor_changes_and_dwell() -> None:
    mode = _all_lock(10)
    mode[3:6, 3] = FLOOR  # RR: up at step 3, down at step 6
    mode[8, 0] = LIFT  # FL: LOCK -> LIFT is not a knee crossing
    normal = np.zeros((10, 4))
    normal[:, 2] = np.linspace(0.0, -90.0, 10)
    record = knee_record(_module(normal, mode))
    assert record.n_knee_crossings == 2
    assert record.first_knee_crossing_s == pytest.approx(4 * DT_S)
    assert record.first_knee_crossing_leg == "RR"
    assert record.floor_dwell_s == pytest.approx([0.0, 0.0, 0.0, 3 * DT_S])
    assert record.lift_steps == [1, 0, 0, 0]
    assert record.floor_or_lift_steps == [1, 0, 0, 3]
    assert record.min_dN_N[2] == pytest.approx(-90.0)
    assert record.end_all_lock is True


def test_module_elastic_change_is_relative_to_the_first_step() -> None:
    normal = np.array([[100.0, 200.0, 300.0, 400.0], [110.0, 190.0, 300.0, 401.0]])
    module = _module(normal, _all_lock(2))
    assert module.elastic_change_N[-1] == pytest.approx([10.0, -10.0, 0.0, 1.0])


# --- modal records ----------------------------------------------------------------------------


def test_local_maxima_refine_a_sampled_parabola_exactly() -> None:
    t = np.arange(0.0, 1.0, 0.1)
    y = 1.0 - (t - 0.43) ** 2
    t_peak, y_peak = local_maxima(t, y)
    assert t_peak == pytest.approx([0.43])
    assert y_peak == pytest.approx([1.0])


def test_modal_record_of_a_damped_cosine() -> None:
    f_d, sigma = 2.0, 0.1
    t = np.arange(0.0, 8.0, 1.0e-3)
    eta = np.exp(-sigma * t) * np.sin(2.0 * math.pi * f_d * t)
    crossings = up_crossing_times(t, eta)
    assert crossings[0] == pytest.approx(0.5, abs=1e-9)  # y(0) = 0 is not a crossing
    record = modal_record(t, eta)
    assert len(record.periods_s) == 10
    assert record.mean_period_s == pytest.approx(1.0 / f_d, rel=1e-6)
    assert len(record.positive_peaks) == 3
    assert record.positive_peaks[1] / record.positive_peaks[0] == pytest.approx(
        math.exp(-sigma / f_d), rel=1e-4)


# --- V7a gate ---------------------------------------------------------------------------------


def _gate(**overrides):
    kwargs = {"non_lock_steps": [0, 0, 0, 0], "dN_max_N": [1600.0, 1500.0, 1150.0, 1050.0],
              "knee_N": KNEE_N, "yield_steps": [0, 0, 0, 0],
              "predicted_peak_N": [1614.0, 1513.0, 1154.0, 1066.0]}
    kwargs.update(overrides)
    return v7a_gate_checks("v7a_top_roll", **kwargs)


def test_v7a_gate_passes_below_half_the_knee() -> None:
    checks = _gate()
    assert all(c.passed for c in checks)
    assert "measured / predicted 0.991" in checks[1].note


@pytest.mark.parametrize(
    ("override", "failed_index"),
    [
        ({"non_lock_steps": [0, 0, 0, 1]}, 0),
        ({"dN_max_N": [1600.0, 1500.0, 1585.2, 1050.0]}, 1),
        ({"yield_steps": [0, 2, 0, 0]}, 2),
    ],
)
def test_v7a_gate_fails_each_condition(override: dict, failed_index: int) -> None:
    passed = [c.passed for c in _gate(**override)]
    assert passed == [i != failed_index for i in range(3)]


# --- V7b --------------------------------------------------------------------------------------


REPLICA = {
    "dominant_LOCK_mode (1-based)": 1,
    "eta_peaks_first10 (t_s, sqrt(kg) m)": [[0.37, 0.2846], [0.87, 0.2704], [1.36, 0.2556]],
    "mean_period_first10_s": 0.4928,
    "max_elastic_dN_N": [11104.0, 10326.0, 7863.7, 7199.2],
    "FLOOR_dwell_s (dN > knee)": [2.218, 2.377, 1.974, 0.02],
    "knee_crossings (t_s, leg)": [[0.0123245, "FR"], [0.0131615, "RR"]],
    "n_knee_crossings": 136,
}


def _knee(**overrides) -> KneeRecord:
    values = {"max_dN_N": [11100.0, 10320.0, 7865.0, 7204.0], "min_dN_N": [-1.0] * 4,
              "floor_dwell_s": [2.25, 2.39, 1.96, 0.024], "floor_or_lift_steps": [1, 1, 1, 1],
              "lift_steps": [0, 0, 0, 0], "n_knee_crossings": 136,
              "first_knee_crossing_s": 0.01229, "first_knee_crossing_leg": "FR",
              "end_all_lock": True}
    values.update(overrides)
    return KneeRecord(**values)


MODAL = ModalRecord(periods_s=[0.4928] * 10, mean_period_s=0.49281,
                    positive_peaks=[0.2845, 0.2703, 0.2555])


def test_v7b_checks_pass_near_the_replica() -> None:
    checks = v7b_checks("v7b_roll_dt1e-05", knee=_knee(), modal=MODAL, replica=REPLICA,
                        yield_steps=[0, 0, 0, 0], ref_key="k")
    assert [c.passed for c in checks] == [True] * 8
    assert all(c.id == "V7b" for c in checks)


def test_v7b_floor_dwell_uses_the_larger_of_10_percent_and_5_ms() -> None:
    # RR replica 0.02 s: 10 % is 2 ms, so 5 ms applies; 0.024 s passes, 0.026 s fails
    late = _knee(floor_dwell_s=[2.25, 2.39, 1.96, 0.02 + V7B_FLOOR_DWELL_ABS_TOL_S + 1e-3])
    checks = v7b_checks("c", knee=late, modal=MODAL, replica=REPLICA, yield_steps=[0] * 4,
                        ref_key="k")
    dwell = next(c for c in checks if "FLOOR dwell" in c.item)
    assert not dwell.passed
    assert dwell.tol[3] == pytest.approx(V7B_FLOOR_DWELL_ABS_TOL_S)
    assert dwell.tol[0] == pytest.approx(0.2218)


def test_v7b_fails_without_the_knee() -> None:
    no_knee = _knee(floor_dwell_s=[0.0] * 4, max_dN_N=[11930.0, 11182.0, 8529.0, 7881.8],
                    n_knee_crossings=0, first_knee_crossing_s=None, first_knee_crossing_leg=None)
    checks = v7b_checks("c", knee=no_knee, modal=MODAL, replica=REPLICA, yield_steps=[0] * 4,
                        ref_key="k")
    failed = {c.item.split(": ", 1)[1] for c in checks if not c.passed}
    assert "max module elastic dN per leg" in failed
    assert "FLOOR dwell per leg (module FLOOR steps x dt)" in failed
    assert "first knee crossing time (record)" in failed


# --- V5 +0.3 mm / V9-1 ------------------------------------------------------------------------


def _smooth_run(rl_min_N: float, end_dN_N: list[float], dt_s: float = 1.0e-2):
    """A module record with an RL dip at 1.25 s inside the transient window and constant end
    values after 6 s; attitude steps from (0, 0) to (0.0037, -0.0016) deg."""
    t = dt_s * np.arange(1, int(round(12.0 / dt_s)) + 1)
    dN = np.zeros((len(t), 4))
    dN[t >= 6.0] = end_dN_N
    dN[np.argmin(np.abs(t - 1.25)), 2] = rl_min_N
    normal = 1.0e5 + dN
    attitude = np.where(t[:, None] >= 6.0, [0.0037, -0.0016], [0.0, 0.0])
    module = ModuleRecord.from_arrays(t, normal, _all_lock(len(t)), dt_s)
    return smooth_step_record(module, t_s=t, attitude_deg=attitude, end_window_s=(10.55, 12.0))


END_REF = [1850.11, -1857.52, -2063.17, 2070.58]


def test_smooth_step_record_reads_the_transient_and_end_window() -> None:
    record = _smooth_run(-2376.9, END_REF)
    assert record.transient_min_dN_RL_N == pytest.approx(-2376.9)
    assert record.transient_t_min_RL_s == pytest.approx(1.25)
    assert record.end_dN_N == pytest.approx(END_REF)
    assert record.end_dattitude_deg == pytest.approx([0.0037, -0.0016])
    assert all(c.passed for c in smooth_validity_checks("c", record, KNEE_N))


def test_smooth_validity_fails_above_0_8_knee_at_rr() -> None:
    record = _smooth_run(-2376.9, [0.0, 0.0, 0.0, 0.81 * KNEE_N[3]])
    checks = smooth_validity_checks("c", record, KNEE_N)
    assert [c.passed for c in checks] == [True, False]


def test_v9_smooth_checks_first_order_series_passes() -> None:
    reference = -2375.0
    records = {dt: _smooth_run(reference + 4.0e3 * dt, END_REF)
               for dt in (2.0e-4, 1.0e-4, 5.0e-5, 1.0e-5)}
    checks, record = v9_smooth_checks("V9-1", records, ref_dt_s=1.0e-5, total_weight_N=380113.0)
    assert all(c.passed for c in checks)
    assert record["order_successive_differences (judged)"]["ratio"] == pytest.approx(2.0)
    # errors against the 1e-5 s run: (2e-4 - 1e-5) / (1e-4 - 1e-5) = 19 / 9
    assert record["error_ratio_vs_ref (information)"][0] == pytest.approx(19.0 / 9.0)


REF_RL_MIN_N = -2374.977
"""5.14.12 values (transient RL min elastic dN): predictor on 2e-4 / 1e-4 / 5e-5 / 1e-5 s and
predictor off 2e-4 / 1e-4 s."""
ON_RL_MIN_N = {2.0e-4: -2374.352, 1.0e-4: -2374.781, 5.0e-5: -2374.953, 1.0e-5: REF_RL_MIN_N}
OFF_RL_MIN_N = {2.0e-4: -2375.820, 1.0e-4: -2375.430}


def _records(values: dict[float, float]) -> dict:
    return {dt: _smooth_run(v, END_REF) for dt, v in values.items()}


def test_v9_smooth_5_14_12_values_record_the_ratio_and_judge_predictor_off() -> None:
    checks, record = v9_smooth_checks("V9-1", _records(ON_RL_MIN_N), ref_dt_s=1.0e-5,
                                      total_weight_N=380113.0,
                                      predictor_off_by_dt=_records(OFF_RL_MIN_N))
    assert all(c.passed for c in checks)
    assert not any("error ratio transient" in c.item for c in checks)
    off_checks = [c for c in checks if "predictor-off error ratio" in c.item]
    assert len(off_checks) == 1
    assert off_checks[0].value == pytest.approx(0.843 / 0.453, rel=1e-3)  # 5.14.12: 1.86
    assert record["order_successive_differences (record, 5.14.12)"]["ratio"] == pytest.approx(
        2.50, abs=0.01)
    rule = record["order_rule_5_14_12"]
    assert rule["applies"] is True
    assert rule["order_ratio_judged"] is False
    assert rule["run_dt_relative_error"] == pytest.approx(0.625 / 2374.977, rel=1e-3)


def test_v9_smooth_judges_the_ratio_when_the_run_dt_error_exceeds_a_tenth_of_1_percent() -> None:
    # 2e-4 s error 1.5e4 x 1.9e-4 = 2.85 N = 0.12 % > 0.1 %: the successive ratio stays judged
    values = {dt: REF_RL_MIN_N + 1.5e4 * dt for dt in ON_RL_MIN_N}
    checks, record = v9_smooth_checks("V9-1", _records(values), ref_dt_s=1.0e-5,
                                      total_weight_N=380113.0,
                                      predictor_off_by_dt=_records(OFF_RL_MIN_N))
    assert record["order_rule_5_14_12"]["applies"] is False
    assert any("error ratio transient" in c.item and c.passed for c in checks)
    assert any("predictor-off error ratio" in c.item for c in checks)


def test_v9_smooth_without_predictor_off_keeps_the_ratio_judged() -> None:
    checks, record = v9_smooth_checks("V9-1", _records(ON_RL_MIN_N), ref_dt_s=1.0e-5,
                                      total_weight_N=380113.0)
    order_checks = [c for c in checks if "error ratio transient" in c.item]
    assert len(order_checks) == 1
    assert order_checks[0].passed is False  # 2.50 outside 2 +- 20 %
    assert record["order_rule_5_14_12"]["order_ratio_judged"] is True


def test_predictor_off_order_check_fails_outside_20_percent_and_needs_2_to_1() -> None:
    check, record = predictor_off_order_check("V9-1", {2.0e-4: -2376.0, 1.0e-4: -2375.5},
                                              ref_transient_N=-2375.0)
    assert record["ratio"] == pytest.approx(1.0 / 0.5)
    assert check.passed
    check, _ = predictor_off_order_check("V9-1", {2.0e-4: -2376.0, 1.0e-4: -2375.8},
                                         ref_transient_N=-2375.0)
    assert check.value == pytest.approx(1.25)
    assert check.passed is False
    with pytest.raises(ValueError, match="2:1"):
        predictor_off_order_check("V9-1", {2.0e-4: -2376.0, 5.0e-5: -2375.1},
                                  ref_transient_N=-2375.0)
    with pytest.raises(ValueError, match="2:1"):
        predictor_off_order_check("V9-1", {2.0e-4: -2376.0}, ref_transient_N=-2375.0)


def test_v5_smooth_checks_tolerance_is_5_percent_of_the_largest_component() -> None:
    final_ref = {"dF_N": END_REF, "dattitude_deg (roll, pitch)": [0.0037211, -0.0016354]}
    inside = [END_REF[0] - 100.0, *END_REF[1:]]
    checks = v5_smooth_checks(2.0e-4, _smooth_run(-2376.9, inside), final_ref=final_ref,
                              ref_key="k")
    assert checks[0].tol == pytest.approx(0.05 * 2070.58)
    assert checks[0].passed
    assert checks[0].item.startswith("dt 0.0002 s, FL +0.3 mm")


def test_transient_match_record_flags_3_percent_and_10_ms() -> None:
    record = _smooth_run(-2376.9 * 1.04, END_REF)
    match = transient_match_record(record, {"min_dF_N": [0.0, -2257.1, -2376.9, -59.8],
                                            "t_min_RL_s": 1.2519})
    assert match["within_3_percent"] is False
    assert match["within_10_ms"] is True


# --- V9-2 -------------------------------------------------------------------------------------


def test_mode_amplitude_phase_at_reproduces_a_damped_cosine() -> None:
    f_d, sigma, amplitude = 2.0748, 0.11, 0.04
    t = np.arange(1.0e-3, 6.0, 1.0e-3)
    eta = amplitude * np.exp(-sigma * t) * np.cos(2.0 * math.pi * f_d * t)
    fit = mode_amplitude_phase_at(t, eta, f_d)
    assert fit["amplitude_at_s"] == pytest.approx(amplitude * math.exp(-sigma * 5.0), rel=1e-6)
    assert math.cos(fit["phase_at_s_rad_unwrapped"]) == pytest.approx(
        math.cos(2.0 * math.pi * f_d * 5.0), abs=1e-6)


def test_v9_free_checks_judge_the_amplitude_order_only() -> None:
    amplitude = {dt: 0.0223 - 0.8 * dt for dt in (2.0e-4, 1.0e-4, 5.0e-5, 1.0e-5)}
    phase = {dt: 66.7496 + 3.5 * dt for dt in amplitude}
    checks, record = v9_free_checks("V9-2", amplitude, phase, ref_dt_s=1.0e-5)
    assert len(checks) == 1
    assert checks[0].passed
    assert record["amplitude_within_1_percent (record)"][2.0e-4] is True


def test_predictor_off_record_compares_with_reference_and_same_dt() -> None:
    on = {dt: _smooth_run(-2375.0 + 4.0e3 * dt, END_REF) for dt in (2.0e-4, 1.0e-5)}
    off = {2.0e-4: _smooth_run(-2375.0 - 0.8, END_REF)}
    record = predictor_off_record(off, on, ref_dt_s=1.0e-5)["dt 0.0002 s"]
    assert record["transient_minus_predictor_on_N"] == pytest.approx(-1.6)
    assert record["within_V9_transient_1_percent"] is True
    assert record["end_dN_minus_ref_N"] == pytest.approx([0.0] * 4)


# --- V7a modes --------------------------------------------------------------------------------


def test_v7a_mode_checks_judge_frequency_and_zeta_of_lock() -> None:
    row = ModeRow(mode=1, run="roll", f_proj_Hz=2.0748, zeta_proj=0.0110, fit_residual_rms_rel=0.01,
                  f_era_Hz=None, zeta_era=None, leakage=None, zeta_num=2.64e-4, f_ref_Hz=2.0748,
                  zeta_ref=0.008574)
    checks = v7a_mode_checks([row], level="top", ref_key_f="f", ref_key_zeta="z")
    assert [c.id for c in checks] == ["V7a", "V7a"]
    assert [c.passed for c in checks] == [True, True]  # zeta +28 % is inside +-30 %
    assert floor_distance_record([2.0748], [1.8454]) == pytest.approx([2.0748 / 1.8454 - 1.0])
