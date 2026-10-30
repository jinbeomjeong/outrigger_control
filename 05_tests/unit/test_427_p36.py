"""Wrapper tokens P36c5 / P36c8 / P36u8 of ``s9_slope_fix_candidates.py`` (control spec 427,
P-S8-36 candidate: the load-sum ratio after the lift stroke guard acted), spec 427.6 tests 1 .. 3.

The signal is driven through ``_p36_observe`` with simple readings; the branch through
``_hold_probe_or_relevel`` / ``_level`` with a pending suspicion. The command-hash part of
427.6 test 1 (three stored cases, about 25 s each) is a CLI run of the wrapper, not a unit test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

PERIOD_S = 0.1
WEIGHT_ESTIMATE_N = 400_000.0
SEAL_FRICTION_N = np.array([4000.0, 4000.0, 3332.0, 3332.0])
STROKE_WITH_MARGIN_M = 0.600
STROKE_WITHOUT_MARGIN_M = 0.650


class _Reading:
    def __init__(self, t_s: float, forces_N, stroke_m: float = STROKE_WITH_MARGIN_M) -> None:
        self.t_s = t_s
        self.cylinder_force_N = np.asarray(forces_N, float)
        self.motor_stroke_m = np.full(4, stroke_m)
        self.rod_stroke_m = self.motor_stroke_m


@pytest.fixture(scope="module")
def params():
    return load_params()


def p36_controller(params, name: str = "P36c5", *, phase=c2.C2Phase.READY, armed: bool = True):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate(name))
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    state = controller._state
    state.phase = phase
    rod_weight_N = controller._touch_rod_weight_N()
    state.free_air_force_N = rod_weight_N + SEAL_FRICTION_N
    soil = controller._soil_state()
    soil.is_liftoff_confirmed = True
    soil.weight_estimate_N = WEIGHT_ESTIMATE_N
    if armed:
        controller.fix.p36_armed_t_s = 1.0
    return controller


def forces_for_ratio(ratio_c: float, signs=(1.0, 1.0, 1.0, 1.0)) -> np.ndarray:
    """Equal leg forces whose corrected ratio rho_c is ``ratio_c``."""
    corrected_weight_N = WEIGHT_ESTIMATE_N - SEAL_FRICTION_N.sum()
    friction_term_N = float(np.dot(signs, SEAL_FRICTION_N))
    return np.full(4, (ratio_c * corrected_weight_N + friction_term_N) / 4.0)


def observe(controller, forces_N, periods: int, t_start_s: float = 2.0) -> float:
    t_s = t_start_s
    for _ in range(periods):
        t_s = round(t_s + PERIOD_S, 10)
        controller._p36_observe(_Reading(t_s, forces_N))
    return t_s


def event_names(controller) -> list[str]:
    return [e.name for e in controller.events]


# --- 1: tokens and defaults ---------------------------------------------------------------------


def test_1_tokens() -> None:
    c5, c8, u8 = (fx.parse_candidate(n) for n in ("P36c5", "P36c8", "P36u8"))
    assert c5.p36 and c5.p36_delta == pytest.approx(0.05)
    assert c5.p36_compensation == fx.P36_COMPENSATED
    assert c8.p36 and c8.p36_delta == pytest.approx(0.08)
    assert u8.p36 and u8.p36_delta == pytest.approx(0.08)
    assert u8.p36_compensation == fx.P36_UNCOMPENSATED
    current = fx.parse_candidate("current")
    assert not current.p36
    assert (current.p36_mean_s, current.p36_confirm_periods, current.p36_probe_settle_s,
            current.p36_relift_margin_m, current.p36_max_relifts) == (1.0, 2, 0.5, 0.04, 1)


def test_1_delta_override_wins_over_the_token_value() -> None:
    assert fx.parse_candidate("P36c8+p36_delta=0.06").p36_delta == pytest.approx(0.06)
    assert fx.parse_candidate("P36c5", {"p36_delta": 0.07}).p36_delta == pytest.approx(0.07)
    overridden = fx.parse_candidate("P36u8", fx.parse_param_overrides(["p36_delta=0.03"]))
    assert overridden.p36_delta == pytest.approx(0.03)
    assert overridden.p36_compensation == fx.P36_UNCOMPENSATED


def test_1_invalid_settings() -> None:
    with pytest.raises(ValueError):
        fx.parse_candidate("P36c5+P36c8")
    with pytest.raises(ValueError):
        fx.parse_candidate("P36c5", {"p36_delta": 1.2})
    with pytest.raises(ValueError):
        fx.parse_candidate("P36c5", {"p36_compensation": "both"})


# --- 2: rho_c ------------------------------------------------------------------------------------


def test_2_seal_friction_is_cut_at_the_p_s8_26_cap() -> None:
    rod_weight_N = np.array([1047.0, 1047.0, 718.0, 718.0])
    free_air_N = np.array([1047.0 + 9000.0, np.nan, 500.0, 718.0 + 2000.0])
    friction = fx.seal_friction_estimates_N(free_air_N, rod_weight_N,
                                            c2.R8_D1_TOUCH_FREE_AIR_CAP_EXCESS_N)
    np.testing.assert_allclose(friction, [8000.0, 0.0, 0.0, 2000.0])


def test_2_friction_sign_remembers_the_last_motion() -> None:
    signs = fx.friction_signs([0.01, -0.01, 0.0, 0.0], [1.0, 1.0, -1.0, 1.0])
    np.testing.assert_array_equal(signs, [1.0, -1.0, -1.0, 1.0])


def test_2_ratios() -> None:
    forces = np.array([100e3, 100e3, 90e3, 90e3])
    signs = np.array([1.0, -1.0, 1.0, 1.0])
    corrected, plain = fx.load_sum_ratios(forces, signs, SEAL_FRICTION_N, WEIGHT_ESTIMATE_N)
    expected = (forces.sum() - signs @ SEAL_FRICTION_N) / (WEIGHT_ESTIMATE_N
                                                           - SEAL_FRICTION_N.sum())
    assert corrected == pytest.approx(expected)
    assert plain == pytest.approx(forces.sum() / WEIGHT_ESTIMATE_N)
    assert fx.load_sum_ratios(forces, signs, [2e5] * 4, WEIGHT_ESTIMATE_N)[0] is None


def test_2_window_needs_five_periods_and_keeps_one_second() -> None:
    window = fx.LoadRatioWindow(1.0)
    for k in range(4):
        window.add(0.1 * (k + 1), 0.9, 0.95)
    assert window.means() == (None, None)
    window.add(0.5, 0.9, 0.95)
    assert window.means() == pytest.approx((0.9, 0.95))
    for k in range(10):
        window.add(round(0.6 + 0.1 * k, 10), 1.0, 1.0)  # the first five leave the 1 s window
    assert window.means() == pytest.approx((1.0, 1.0))


def test_2_observe_uses_the_remembered_direction(params) -> None:
    controller = p36_controller(params)
    controller._state.applied_output_m_s = np.array([-0.01, 0.01, 0.0, 0.0])
    observe(controller, forces_for_ratio(1.0), 1)
    controller._state.applied_output_m_s = np.zeros(4)  # standing: the sign is kept
    observe(controller, forces_for_ratio(1.0), 1, 2.1)
    np.testing.assert_array_equal(controller.fix.p36_signs, [-1.0, 1.0, 1.0, 1.0])


def test_2_corrected_ratio_in_the_record(params) -> None:
    controller = p36_controller(params)
    observe(controller, forces_for_ratio(0.97), 5)
    minima = controller.fix.p36_minima["ready"]
    assert minima["rho_c"] == pytest.approx(0.97)
    assert minima["mean_c"] == pytest.approx(0.97)
    assert minima["rho_u"] == pytest.approx(forces_for_ratio(0.97).sum() / WEIGHT_ESTIMATE_N)


def test_2_probe_motion_and_half_a_second_after_are_left_out(params) -> None:
    controller = p36_controller(params, phase=c2.C2Phase.PROBE)
    controller._state.applied_output_m_s = np.array([0.0, 0.0, -0.005, 0.0])
    observe(controller, forces_for_ratio(0.5), 1, 2.0)  # t 2.1: probe motion, left out
    controller._state.applied_output_m_s = np.zeros(4)
    controller._state.phase = c2.C2Phase.READY
    observe(controller, forces_for_ratio(0.5), 5, 2.1)  # t 2.2 .. 2.6: within 0.5 s
    assert "ready" not in controller.fix.p36_minima
    retracted_rl = (1.0, 1.0, -1.0, 1.0)  # the probe left RL's remembered sign at -1
    observe(controller, forces_for_ratio(0.5, retracted_rl), 1, 2.6)  # t 2.7: counted
    assert controller.fix.p36_minima["ready"]["rho_c"] == pytest.approx(0.5)


def test_2_not_armed_records_and_acts_nothing(params) -> None:
    controller = p36_controller(params, armed=False)
    observe(controller, forces_for_ratio(0.5), 12)
    assert controller.fix.p36_minima == {} and controller.fix.p36_pending is None


def test_2_record_only_without_the_token(params) -> None:
    controller = p36_controller(params, name="current")
    observe(controller, forces_for_ratio(0.5), 12)
    assert controller.fix.p36_minima["ready"]["mean_c"] == pytest.approx(0.5)
    assert controller.fix.p36_pending is None


@pytest.mark.parametrize(("ratio_c", "is_pending"), [(0.951, False), (0.949, True)])
def test_2_threshold_and_two_periods(params, ratio_c, is_pending) -> None:
    controller = p36_controller(params)
    t_s = observe(controller, forces_for_ratio(ratio_c), 5)  # first mean: one low period
    assert controller.fix.p36_pending is None
    observe(controller, forces_for_ratio(ratio_c), 1, t_s)
    assert (controller.fix.p36_pending is not None) is is_pending


def test_2_uncompensated_token_judges_the_plain_ratio(params) -> None:
    controller = p36_controller(params, name="P36u8")
    forces = np.full(4, 0.91 * WEIGHT_ESTIMATE_N / 4.0)  # rho_u 0.91 < 1 - 0.08
    observe(controller, forces, 6)
    assert controller.fix.p36_pending is not None
    assert controller.fix.p36_pending["ratio"] == pytest.approx(0.91)


# --- 3: branch -----------------------------------------------------------------------------------


def suspect(controller, stroke_m: float, t_s: float = 3.0) -> _Reading:
    controller.fix.p36_pending = {"t_s": t_s, "ratio": 0.9}
    return _Reading(t_s, forces_for_ratio(0.9), stroke_m)


def test_3_stroke_margin_relifts(params) -> None:
    controller = p36_controller(params)
    out = controller._hold_probe_or_relevel(suspect(controller, STROKE_WITH_MARGIN_M))
    assert out is None
    assert controller._state.phase is c2.C2Phase.LEVEL
    assert not controller._soil_state().is_liftoff_confirmed
    assert event_names(controller)[-2:] == ["WARN_CRAWLER_RELOAD:0.900",
                                            "INFO_LOC_REVOKED_RELOAD:0.900"]
    assert controller.fix.p36_actions[0]["branch"] == fx.P36_BRANCH_RELIFT
    assert controller.fix.p36_relifts == 1


def test_3_no_stroke_margin_faults(params) -> None:
    controller = p36_controller(params, phase=c2.C2Phase.DONE)
    out = controller._hold_probe_or_relevel(suspect(controller, STROKE_WITHOUT_MARGIN_M))
    np.testing.assert_array_equal(out, np.zeros(4))
    assert controller._state.phase in (c2.C2Phase.FAULT, c2.C2Phase.FAULT_REGROUND)
    assert event_names(controller)[-2:] == ["WARN_CRAWLER_RELOAD:0.900",
                                            "FAULT_LIFT_STROKE_LIMIT:reload"]
    assert controller.fix.p36_actions[0]["branch"] == fx.P36_BRANCH_FAULT


def test_3_relift_limit_point_is_inclusive(params) -> None:
    controller = p36_controller(params)
    limit_m = controller._lift_guard_stroke_m() - 0.040
    assert limit_m == pytest.approx(0.6428, abs=1e-6)
    controller._hold_probe_or_relevel(suspect(controller, limit_m))
    assert controller.fix.p36_actions[0]["branch"] == fx.P36_BRANCH_RELIFT


def test_3_second_suspicion_after_a_relift_faults_in_level(params) -> None:
    controller = p36_controller(params)
    controller._hold_probe_or_relevel(suspect(controller, STROKE_WITH_MARGIN_M))
    controller._soil_state().is_liftoff_confirmed = True  # the new LOC
    out = controller._level(suspect(controller, STROKE_WITH_MARGIN_M, 9.0))
    np.testing.assert_array_equal(out, np.zeros(4))
    assert event_names(controller)[-1] == "FAULT_LIFT_STROKE_LIMIT:reload"
    assert [a["branch"] for a in controller.fix.p36_actions] == [fx.P36_BRANCH_RELIFT,
                                                                 fx.P36_BRANCH_FAULT]


def test_3_guard_period_arms_the_latch_once(params) -> None:
    controller = p36_controller(params, armed=False, phase=c2.C2Phase.LEVEL)
    guarded = np.array([True, False, False, False])
    controller._record_lift_guard_period(5.0, guarded, c2.LiftGuardMode.SHIFT_DOWN)
    controller._record_lift_guard_period(5.1, guarded, c2.LiftGuardMode.SHIFT_DOWN)
    assert controller.fix.p36_armed_t_s == pytest.approx(5.0)
    controller._clear_lift_guard_latch()  # LEVEL re-entry clears the c2 latch, not P36's
    assert controller.fix.p36_armed_t_s == pytest.approx(5.0)


def test_record_and_acted() -> None:
    fix = fx._FixState()
    fix.p36_armed_t_s = 12.346
    fix.p36_minima = {"ready": {"rho_c": 0.912345, "rho_u": None, "mean_c": 0.93,
                                "mean_u": None}}
    record = fx.p36_record(fix)
    assert record["armed_t_s"] == 12.35 and record["minima"]["ready"]["rho_c"] == 0.9123
    assert not fx.has_candidate_acted({"metrics": {"p36": record}})
    record["actions"] = [{"t_s": 1.0, "ratio": 0.9, "branch": "fault"}]
    assert fx.has_candidate_acted({"metrics": {"p36": record}})


def test_x426b_suite_has_84_cases() -> None:
    cases = fx.suite_cases("x426b")
    ids = [case_id for case_id, _ in cases]
    assert len(ids) == 84 == len(set(ids))
    assert "H3|J1|B|top|roll_pos@k0.5|m1.1" in ids
    assert "H3|S1|B|middle|edge_nd@k0.75" in ids
    assert "H1|G1|B|top|nose_down|Fs0" in ids and "H1|G1|B|top|nose_down|Fs8" in ids
    statuses = {payload["settle_table_status"] for _, payload in cases}
    assert statuses == {"applied"}
