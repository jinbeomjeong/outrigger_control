"""Fix candidates of the soft soil x slope defects (``04_scripts/03_control/s9/
s9_slope_fix_candidates.py``): candidate names, the E1 / E4 signal maths, the run metrics and the
comparison on synthetic records, and the candidate controller hooks on a project C2 without a
harness run (numba not needed)."""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

CORNERS_XY = np.array([[-1.84, -1.366], [-1.84, 1.366], [1.844, -1.366], [1.844, 1.366]])
WEIGHT_N = 376_580.0


# ------------------------------------------------------------------------------ candidates
def test_parse_candidate_tokens_and_baseline() -> None:
    assert fx.parse_candidate("current") == fx.CandidateSettings()
    settings = fx.parse_candidate("E1+E4+RA", {"e1_max_mismatch_m": 0.003})
    assert settings.e1 and settings.e4 and settings.reanchor_soil_skip
    assert not (settings.e2 or settings.e3 or settings.s4_stroke_limit)
    assert settings.e1_max_mismatch_m == 0.003


@pytest.mark.parametrize("name", ["E5", "E1+X", ""])
def test_parse_candidate_rejects_unknown_tokens(name: str) -> None:
    with pytest.raises(ValueError):
        fx.parse_candidate(name)


def test_param_overrides_are_typed() -> None:
    out = fx.parse_param_overrides(["e2_confirm_samples=3", "e3_margin_m=0.02",
                                    "s4_stroke_basis=mean"])
    assert out == {"e2_confirm_samples": 3, "e3_margin_m": 0.02, "s4_stroke_basis": "mean"}
    with pytest.raises(ValueError):
        fx.parse_param_overrides(["nope=1"])
    with pytest.raises(ValueError):
        fx.parse_candidate("S4", {"s4_stroke_basis": "min"})


# ----------------------------------------------------------------------------- signal maths
def test_kinematic_mismatch_zero_for_rigid_lift_and_tilt() -> None:
    start = np.zeros(4)
    droll, dpitch = math.radians(0.2), math.radians(-0.1)
    end = 0.01 + fx.corner_rise_m(CORNERS_XY, droll, dpitch)
    spread = fx.kinematic_mismatch_m(CORNERS_XY, start, end, (0.0, 0.0), (droll, dpitch))
    assert spread == pytest.approx(0.0, abs=1e-12)


def test_kinematic_mismatch_sees_a_pivot_on_the_crawler_edge() -> None:
    # strokes say a pure 10 mm heave, the body rolled about its right edge (y = -1.366 m)
    droll = 0.010 / (2 * 1.366)
    spread = fx.kinematic_mismatch_m(CORNERS_XY, np.zeros(4), np.full(4, 0.010), (0.0, 0.0),
                                     (droll, 0.0))
    assert spread == pytest.approx(0.010, rel=1e-9)


def test_vertical_integrator_double_integrates_from_rest() -> None:
    integrator = fx.VerticalIntegrator(gravity_samples=5)
    integrator.collect_gravity([9.81] * 10)
    integrator.start()
    for k in range(100):  # 1 s of 0.1 m/s^2 up, 10 ms samples
        integrator.integrate(0.01 * (k + 1), [9.91], 0.01)
    assert integrator.g_ref == pytest.approx(9.81)
    assert integrator.height_at(1.0) == pytest.approx(0.5 * 0.1 * 1.0**2, rel=0.02)
    assert integrator.height_at(1.0 + 5e-7) == integrator.height_at(1.0)
    assert integrator.height_at(3.0) is None


def test_rise_ratio() -> None:
    assert fx.rise_ratio(0.001, 0.006, 0.010) == pytest.approx(0.5)
    assert fx.rise_ratio(None, 0.006, 0.010) is None
    assert fx.rise_ratio(0.0, 0.006, 0.0) is None


# ------------------------------------------------------------------------------ run metrics
def _log(rows):
    return [(t, phase, crawler_kN * 1e3, load) for t, phase, crawler_kN, load in rows]


def test_run_metrics_false_loc_and_ready_recontacts() -> None:
    log = _log([(10.0, "level", 20.0, 3.7e5), (10.1, "level", 2.0, 3.7e5),
                (20.0, "ready", 0.0, 3.6e5), (20.1, "ready", 1.0, 3.5e5),
                (20.2, "ready", 1.5, 3.5e5), (20.3, "ready", 0.0, 3.6e5),
                (20.4, "ready", 0.5, 3.6e5)])
    events = [(10.0, "crawler_liftoff_confirmed"), (10.1, "crawler_liftoff_confirmed")]
    metrics = fx.run_metrics(log, events, WEIGHT_N)
    assert metrics["n_loc"] == 2
    assert metrics["loc_crawler_kN"] == [20.0, 2.0]
    assert metrics["false_loc"] == 1  # 2 kN < 0.01 W = 3.77 kN
    assert metrics["ready_recontacts"] == 2
    assert metrics["ready_crawler_max_kN"] == 1.5
    assert fx.ready_load_ratio_min(log, 3.7e5) == pytest.approx(3.5 / 3.7, abs=1e-4)
    assert fx.ready_load_ratio_min(log, None) is None


def test_run_metrics_without_weight_does_not_judge_false_loc() -> None:
    metrics = fx.run_metrics(_log([(1.0, "level", 50.0, 0.0)]),
                             [(1.0, "crawler_liftoff_confirmed")], None)
    assert metrics["false_loc"] == 0 and metrics["false_loc_limit_kN"] is None


def _record(candidate, verdict, passed, false_loc=0, ready_recontacts=0, sha="a", **extra):
    return {"suite": "slope", "id": "H1|J2|B|top|edge_nu", "candidate": candidate,
            "verdict": verdict, "passed": passed, "hash": sha, "t_ready_s": 60.0,
            "min_force_kN": 50.0, "att_end_deg": [0.01, -0.02], "final_phase": "ready",
            "metrics": {"false_loc": false_loc, "ready_recontacts": ready_recontacts,
                        "fix_events": []}, **extra}


def test_summarize_counts_e_resolution_and_hashes() -> None:
    before = _record("current", "fail", False, false_loc=1, ready_recontacts=1)
    after = _record("E1", "pass", True, sha="b", t_ready_s=70.0)
    same = _record("E3", "fail", False, false_loc=1, ready_recontacts=1)
    summary = fx.summarize([before, after, same])
    e1 = summary["by_suite_candidate"]["slope|E1"]
    assert e1["fail_to_pass"] == 1 and e1["e_cases"] == 1 and e1["e_resolved"] == 1
    assert e1["hash_same"] == 0
    e3 = summary["by_suite_candidate"]["slope|E3"]
    assert e3["hash_same"] == 1 and e3["e_resolved"] == 0
    row = next(r for r in summary["rows"] if r["candidate"] == "E1")
    assert row["d_ready_s"] == 10.0 and row["verdict_changed"]


def test_summarize_counts_errors_and_missing_baseline() -> None:
    error = {"suite": "g8", "id": "k", "candidate": "E1", "error": "boom"}
    lonely = _record("E2", "pass", True)
    summary = fx.summarize([error, lonely])["by_suite_candidate"]
    assert summary["g8|E1"]["errors"] == 1
    assert summary["slope|E2"]["no_baseline"] == 1


def test_p3_lite_gates() -> None:
    out = {"crawler_N_max_after_ready": 0.0, "n_crawler_recontact": 0,
           "min_true_Fcyl_after_off_kN": 60.0, "att_end_deg": [0.05, -0.1],
           "clear_true_ready_mm": 40.0, "final_phase": "ready", "t_ready_s": 50.0}
    assert all(fx.p3_lite_gates(out, 9.415).values())
    out.update(final_phase="fault", clear_true_ready_mm=3.0)
    gates = fx.p3_lite_gates(out, 9.415)
    assert not gates["fault_ready"] and not gates["rut"]


# ----------------------------------------------------------------------- controller hooks
@pytest.fixture(scope="module")
def params():
    return load_params()


def _controller(params, name: str, **overrides):
    settings = fx.parse_candidate(name, overrides)
    cls = fx.make_candidate_class(c2, c2.C2Controller, settings)
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    return controller


def _tail(corner_end_m, attitude_end_rad, strokes=(0.300, 0.310)):
    first = c2._PlateauSample(t_s=10.0, mean_motor_stroke_m=strokes[0], load_sum_N=3.7e5,
                              corner_clearance_m=np.zeros(4), raw_attitude_rad=(0.0, 0.0))
    last = c2._PlateauSample(t_s=12.0, mean_motor_stroke_m=strokes[1], load_sum_N=3.7e5,
                             corner_clearance_m=np.asarray(corner_end_m, float),
                             raw_attitude_rad=attitude_end_rad)
    return [first, last]


def _pivot_tail(controller):
    corners = controller.geometry.crawler_corners_xy_m
    width = float(np.ptp(corners[:, 1]))
    return _tail(np.full(4, 0.010), (0.010 / width, 0.0))


def test_e1_vetoes_a_pivoting_window(params) -> None:
    controller = _controller(params, "E1")
    controller._soil_state().window.extend(_pivot_tail(controller))
    controller._confirm_liftoff(12.0, _pivot_tail(controller), 3.7e5)
    soil = controller._soil_state()
    assert not soil.is_liftoff_confirmed and not soil.window
    assert controller.fix.window_checks[0]["vetoed"].startswith("E1:")
    assert any(e.name.startswith(fx.WINDOW_VETO_EVENT) for e in controller.events)


def test_baseline_records_but_confirms(params) -> None:
    controller = _controller(params, "current")
    controller._confirm_liftoff(12.0, _pivot_tail(controller), 3.7e5)
    assert controller._soil_state().is_liftoff_confirmed
    check = controller.fix.window_checks[0]
    assert check["vetoed"] is None and check["e1_spread_mm"] == pytest.approx(10.0, abs=0.01)


def test_e4_vetoes_a_window_without_body_rise(params) -> None:
    controller = _controller(params, "E4")
    vertical = controller._vertical
    vertical.collect_gravity([9.81])
    vertical.start()
    vertical.integrate(10.0, [9.81], 0.01)
    vertical.integrate(12.0, [9.81], 0.01)  # no rise while the strokes advanced 10 mm
    controller._confirm_liftoff(12.0, _tail(np.full(4, 0.010), (0.0, 0.0)), 3.7e5)
    assert not controller._soil_state().is_liftoff_confirmed
    assert controller.fix.window_checks[0]["vetoed"] == "E4:0.00"


def test_e3_raises_the_target_on_a_tilted_soil_run_and_reset_restores(params) -> None:
    controller = _controller(params, "E3")
    soil = controller._soil_state()
    soil.soil_mode_start_s = 5.0
    soil.settle_attitude_rad = (math.radians(2.0), 0.0)
    controller._state.crawler_attitude_rad = soil.settle_attitude_rad  # the preset has CHECK
    target_m = controller.config.thresholds.clearance_target_m
    controller._confirm_liftoff(12.0, _tail(np.full(4, 0.010), (0.0, 0.0)), 3.7e5)
    assert controller.config.thresholds.clearance_target_m == pytest.approx(target_m + 0.030)
    controller.reset()
    assert controller.config.thresholds.clearance_target_m == target_m


def test_e3_keeps_the_target_on_a_level_settle(params) -> None:
    controller = _controller(params, "E3")
    soil = controller._soil_state()
    soil.soil_mode_start_s = 5.0
    soil.settle_attitude_rad = (math.radians(0.5), math.radians(-0.5))
    controller._state.crawler_attitude_rad = soil.settle_attitude_rad  # the preset has CHECK
    target_m = controller.config.thresholds.clearance_target_m
    controller._confirm_liftoff(12.0, _tail(np.full(4, 0.010), (0.0, 0.0)), 3.7e5)
    assert controller.config.thresholds.clearance_target_m == target_m


def test_e3_without_soil_use_needs_the_relaxed_option(params) -> None:
    for require, expected_add in ((True, 0.0), (False, 0.030)):
        overrides = fx.parse_param_overrides([f"e3_require_soil_use={int(require)}"])
        controller = _controller(params, "E3", **overrides)
        controller._state.crawler_attitude_rad = (0.0, math.radians(2.0))
        target_m = controller.config.thresholds.clearance_target_m
        controller._confirm_liftoff(12.0, _tail(np.zeros(4), (0.0, 0.0)), 3.7e5)
        assert controller.config.thresholds.clearance_target_m == pytest.approx(
            target_m + expected_add)


def test_composite_e3_tokens() -> None:
    wide = fx.parse_candidate("E3w")
    assert wide == fx.parse_candidate("E3", {"e3_require_soil_use": False})
    assert wide.e3_min_clearance_at_P_m < 0.0
    assert fx.parse_candidate("E3c7").e3_min_clearance_at_P_m == pytest.approx(0.007)
    c10 = fx.parse_candidate("E3c10", {"e3_min_clearance_at_P_m": 0.5})
    assert c10.e3_min_clearance_at_P_m == pytest.approx(0.010)  # the preset wins
    assert not c10.e3_require_soil_use


@pytest.mark.parametrize(("c_min_tP_m", "expected_add"),
                         ((0.0065, 0.0), (0.007, 0.0), (0.0077, 0.030)))
def test_e3c7_needs_the_soil_sign(params, c_min_tP_m, expected_add) -> None:
    controller = _controller(params, "E3c7")
    controller._state.crawler_attitude_rad = (math.radians(2.0), 0.0)
    target_m = controller.config.thresholds.clearance_target_m
    tail = _tail(np.full(4, c_min_tP_m), (0.0, 0.0))
    tail[0] = c2._PlateauSample(t_s=10.0, mean_motor_stroke_m=0.300, load_sum_N=3.7e5,
                                corner_clearance_m=np.full(4, c_min_tP_m),
                                raw_attitude_rad=(0.0, 0.0))
    # c_min(t_P) = min corner clearance of the first tail sample (c2 _confirm_liftoff)
    controller._confirm_liftoff(12.0, tail, 3.7e5)
    assert controller._soil_state().clearance_at_plateau_start_m == pytest.approx(c_min_tP_m)
    assert controller.config.thresholds.clearance_target_m == pytest.approx(
        target_m + expected_add)


def test_lw_tokens_are_alternatives() -> None:
    assert fx.parse_candidate("LWa").lw_restart and not fx.parse_candidate("LWa").lw_exclude
    assert fx.parse_candidate("LWb").lw_exclude
    assert fx.parse_candidate("E3c10+LWb").e3_min_clearance_at_P_m == pytest.approx(0.010)
    with pytest.raises(ValueError):
        fx.parse_candidate("LWa+LWb")


class _WindowReading:
    def __init__(self, t_s, strokes_m, load_N=3.7e5):
        self.t_s = t_s
        self.motor_stroke_m = np.asarray(strokes_m, float)
        self.rod_stroke_m = np.asarray(strokes_m, float)
        self.cylinder_force_N = np.full(4, load_N / 4.0)


def _lw_controller(params, name, monkeypatch):
    controller = _controller(params, name)
    monkeypatch.setattr(controller, "_period_raw_attitude_rad", lambda: (0.0, 0.0))
    controller._state.applied_output_m_s = np.full(4, controller.geometry.max_speed_m_s)
    return controller


def test_lwa_clears_the_window_during_a_reapproach(params, monkeypatch) -> None:
    controller = _lw_controller(params, "LWa", monkeypatch)
    soil = controller._soil_state()
    controller._update_liftoff_window(_WindowReading(10.0, [0.300] * 4))
    assert len(soil.window) == 1
    controller._state.active_reapproaches[3] = object()
    controller._update_liftoff_window(_WindowReading(10.1, [0.301] * 4))
    assert not soil.window and controller.fix.lw_clears == 1
    assert any(e.name == f"{fx.LW_RESTART_EVENT}:RR" for e in controller.events)


def test_lwb_takes_the_mean_stroke_without_the_reapproaching_leg(params, monkeypatch) -> None:
    controller = _lw_controller(params, "LWb", monkeypatch)
    soil = controller._soil_state()
    controller._state.active_reapproaches[3] = object()
    # RR runs 10 mm ahead: with LWb the window mean stroke ignores it
    controller._update_liftoff_window(_WindowReading(10.0, [0.300, 0.300, 0.300, 0.310]))
    assert soil.window[-1].mean_motor_stroke_m == pytest.approx(0.300)
    assert controller.fix.lw_window_legs == frozenset({3})
    del controller._state.active_reapproaches[3]
    controller._update_liftoff_window(_WindowReading(10.1, [0.300, 0.300, 0.300, 0.312]))
    assert len(soil.window) == 1 and controller.fix.lw_clears == 1  # set changed: new window
    assert soil.window[-1].mean_motor_stroke_m == pytest.approx(0.303)


def test_lw_off_keeps_the_project_window(params, monkeypatch) -> None:
    """Since P-S8-32 (2026-10-29) the project preset is LWa itself ("current" clears the
    window during a re-approach); with the project rule off the window keeps all four legs."""
    controller = _lw_controller(params, "current", monkeypatch)
    controller._state.active_reapproaches[3] = object()
    controller._update_liftoff_window(_WindowReading(10.0, [0.300, 0.300, 0.300, 0.310]))
    assert not controller._soil_state().window and controller.fix.lw_clears == 0
    settings = fx.parse_candidate("current", {})
    cls = fx.make_candidate_class(c2, c2.C2Controller, settings)
    window_off = replace(c2.C2Config().with_10hz_d1(),
                         liftoff_window_reapproach=c2.LiftoffWindowReapproachSettings())
    controller = cls.from_params(params, window_off)
    controller.reset()
    monkeypatch.setattr(controller, "_period_raw_attitude_rad", lambda: (0.0, 0.0))
    controller._state.applied_output_m_s = np.full(4, controller.geometry.max_speed_m_s)
    controller._state.active_reapproaches[3] = object()
    controller._update_liftoff_window(_WindowReading(10.0, [0.300, 0.300, 0.300, 0.310]))
    assert controller._soil_state().window[-1].mean_motor_stroke_m == pytest.approx(0.3025)


class _Reading:
    def __init__(self, t_s, forces_N, motor_stroke_m=(0.3, 0.3, 0.3, 0.3)):
        self.t_s = t_s
        self.cylinder_force_N = np.asarray(forces_N, float)
        self.motor_stroke_m = np.asarray(motor_stroke_m, float)


def test_e2_undoes_the_loc_after_two_low_samples(params) -> None:
    controller = _controller(params, "E2")
    soil = controller._soil_state()
    soil.is_liftoff_confirmed, soil.weight_estimate_N = True, 4.0e5
    low = _Reading(30.0, [0.9e5] * 4)  # sum 3.6e5 = 0.90 W_hat
    assert not controller._is_recontact_suspected(low)
    assert controller._is_recontact_suspected(low)
    controller._undo_liftoff(30.0)
    assert not soil.is_liftoff_confirmed and controller.fix.e2_relifts == 1
    soil.is_liftoff_confirmed = True
    assert not controller._is_recontact_suspected(_Reading(31.0, [0.98e5] * 4))


def test_reanchor_soil_skip_only_where_reanchor_would_start(params, monkeypatch) -> None:
    controller = _controller(params, "RA")
    base = fx._RUNNING.get("original_class", c2.C2Controller)
    monkeypatch.setattr(base, "_reanchor_skip_reason", lambda self, reading: None)
    assert controller._reanchor_skip_reason(None) is None
    controller._soil_state().soil_mode_start_s = 5.0
    assert controller._reanchor_skip_reason(None) == fx.REANCHOR_SOIL_REASON
    monkeypatch.setattr(base, "_reanchor_skip_reason", lambda self, reading: "theta_below_min")
    assert controller._reanchor_skip_reason(None) == "theta_below_min"


def test_s4_faults_at_the_guard_stroke_before_the_loc(params, monkeypatch) -> None:
    controller = _controller(params, "S4")
    base = fx._RUNNING.get("original_class", c2.C2Controller)
    monkeypatch.setattr(base, "_hold_crawler_zone_until_liftoff", lambda self, reading: None)
    controller._state.phase = c2.C2Phase.LEVEL
    soil = controller._soil_state()
    soil.is_soil_mode = True
    guard_m = controller._lift_guard_stroke_m()
    controller._hold_crawler_zone_until_liftoff(_Reading(40.0, [1e5] * 4, [guard_m - 0.01] * 4))
    assert controller.phase is c2.C2Phase.LEVEL
    strokes = [guard_m - 0.05, guard_m - 0.05, guard_m - 0.05, guard_m + 1e-4]
    controller._hold_crawler_zone_until_liftoff(_Reading(40.1, [1e5] * 4, strokes))
    assert controller.phase is c2.C2Phase.FAULT and controller.fix.s4_fired
    assert any(e.name == fx.S4_STROKE_EVENT for e in controller.events)


# ------------------------------------------------------------- spec 424.3 / 424.4 candidates
def test_424_tokens_parse_and_d1_d2_are_alternatives() -> None:
    settings = fx.parse_candidate("L1+L2+L4")
    assert settings.l1_revoke and settings.l2_confirm_window and settings.l4_probe_reuse
    both = fx.parse_candidate("D2+D3")
    assert both.d2_fall_slow and both.d3_repeat_reapproach_slow and not both.d1_fall_hold
    assert both.has_qc_token and not fx.parse_candidate("current").has_qc_token
    with pytest.raises(ValueError, match="alternatives"):
        fx.parse_candidate("D1+D2")
    assert "h6" in fx.SUITES


def _loc_reading(load_sum_N: float, stroke_m: float = 0.30, t_s: float = 12.0):
    return _WindowReading(t_s, [stroke_m] * 4, load_N=load_sum_N)


def _l1_controller(params):
    controller = _controller(params, "L1")
    controller._state.last_reading = _loc_reading(3.7e5)
    controller._state.phase = c2.C2Phase.LEVEL
    controller._confirm_liftoff(12.0, _tail(np.zeros(4), (0.0, 0.0)), 3.7e5)
    assert controller.fix.l1_watch is not None
    return controller


def test_l1_keeps_a_loc_without_a_load_rise(params) -> None:
    controller = _l1_controller(params)
    for k in range(10):
        controller._state.last_reading = _loc_reading(3.7e5 + 1500.0, t_s=12.1 + 0.1 * k)
        controller._l1_watch_step()
    assert controller._soil_state().is_liftoff_confirmed and controller.fix.l1_revokes == 0


def test_l1_revokes_after_two_periods_above_the_limit(params) -> None:
    controller = _l1_controller(params)
    for k in range(6):
        controller._state.last_reading = _loc_reading(3.7e5 + 8000.0, t_s=12.1 + 0.1 * k)
        controller._l1_watch_step()
    soil = controller._soil_state()
    assert not soil.is_liftoff_confirmed and soil.weight_estimate_N is None
    assert controller.fix.l1_revokes == 1 and controller._state.clearance_target_m is None
    assert any(e.name.startswith(fx.LOC_REVOKE_EVENT) for e in controller.events)


def test_l1_watch_ends_after_20_mm_of_stroke(params) -> None:
    controller = _l1_controller(params)
    controller._state.last_reading = _loc_reading(3.7e5 + 8000.0, stroke_m=0.321, t_s=12.1)
    controller._l1_watch_step()
    assert controller.fix.l1_watch is None and controller._soil_state().is_liftoff_confirmed


def test_l2_without_the_soil_sign_confirms_at_once(params) -> None:
    controller = _controller(params, "L2")
    controller._state.last_reading = _loc_reading(3.7e5)
    controller._confirm_liftoff(12.0, _tail(np.zeros(4), (0.0, 0.0)), 3.7e5)
    assert controller._soil_state().is_liftoff_confirmed and controller.fix.l2_pending is None


def test_l2_holds_a_soil_sign_window_and_confirms_after_a_flat_extra_stroke(params) -> None:
    controller = _controller(params, "L2")
    soil = controller._soil_state()
    first = c2._PlateauSample(t_s=10.0, mean_motor_stroke_m=0.300, load_sum_N=3.7e5,
                              corner_clearance_m=np.full(4, 0.015), raw_attitude_rad=(0.0, 0.0))
    last = replace(first, t_s=12.0, mean_motor_stroke_m=0.310)
    soil.window.extend([first, last])
    controller._confirm_liftoff(12.0, [first, last], 3.7e5)
    assert not soil.is_liftoff_confirmed and controller.fix.l2_pending is not None
    soil.window.append(replace(last, t_s=12.6, mean_motor_stroke_m=0.3125, load_sum_N=3.7e5))
    controller._l2_check(_loc_reading(3.7e5, t_s=12.6))
    assert not soil.is_liftoff_confirmed  # 2.5 mm of the 5 mm
    soil.window.append(replace(last, t_s=13.2, mean_motor_stroke_m=0.3151, load_sum_N=3.7e5))
    controller._l2_check(_loc_reading(3.7e5, t_s=13.2))
    assert soil.is_liftoff_confirmed and controller.fix.l2_confirms == 1


def test_l2_clears_the_window_on_a_rising_extra_stroke(params) -> None:
    controller = _controller(params, "L2")
    soil = controller._soil_state()
    first = c2._PlateauSample(t_s=10.0, mean_motor_stroke_m=0.300, load_sum_N=3.7e5,
                              corner_clearance_m=np.full(4, 0.015), raw_attitude_rad=(0.0, 0.0))
    last = replace(first, t_s=12.0, mean_motor_stroke_m=0.310)
    soil.window.extend([first, last])
    controller._confirm_liftoff(12.0, [first, last], 3.7e5)
    soil.window.append(replace(last, t_s=13.2, mean_motor_stroke_m=0.3155, load_sum_N=3.75e5))
    controller._l2_check(_loc_reading(3.75e5, t_s=13.2))
    assert not soil.is_liftoff_confirmed and not soil.window and controller.fix.l2_rejects == 1


class _FakeRound:
    """The ``ProbeRound`` interface ``_install_probe_reuse`` patches."""

    def __init__(self) -> None:
        self.leg = 0
        self.results: list = []
        self.skipped_legs: list = []
        self._stage_start_s = 0.0

    def _first_move_sign(self, reading):
        return 1.0

    def _skip_leg(self, reading):
        self.skipped_legs.append(self.leg)
        self.leg += 1


def test_l4_reuses_a_confirmed_leg_without_a_skip_warning(params) -> None:
    controller = _controller(params, "L4")
    probe_round = _FakeRound()
    confirmed = {0: "FL result"}
    fx._install_probe_reuse(probe_round, confirmed, controller)
    reading = _loc_reading(3.7e5)
    assert probe_round._first_move_sign(reading) is None
    probe_round._skip_leg(reading)
    assert probe_round.results == ["FL result"] and probe_round.leg == 1
    assert probe_round.skipped_legs == [] and controller.fix.l4_reused
    assert probe_round._first_move_sign(reading) == 1.0  # FR: probed as before


class _LowerReading:
    def __init__(self, t_s, lower_N):
        self.t_s = t_s
        self.cylinder_force_lower_N = np.asarray(lower_N, float)


def test_falling_leg_below_picks_the_lowest_fallen_leg() -> None:
    previous = [30e3, 30e3, 30e3, 30e3]
    assert fx.falling_leg_below([29.5e3, 20e3, 25e3, 30e3], previous, 28e3, 1e3) == 1
    assert fx.falling_leg_below([29.5e3, 29.5e3, 30e3, 30e3], previous, 28e3, 1e3) is None
    assert fx.falling_leg_below([29e3, 30e3, 30e3, 30e3], previous, 28e3, 1e3) is None


def test_slow_lift_keeps_a_slow_command_and_slows_a_fast_one() -> None:
    np.testing.assert_array_equal(fx.slow_lift([1e-3, 2e-3, 0.0], 3e-3), [1e-3, 2e-3, 0.0])
    out = fx.slow_lift([10e-3, 12e-3, 11e-3], 3e-3)
    assert float(np.mean(out)) == pytest.approx(3e-3)
    assert out[1] - out[0] == pytest.approx(2e-3)  # the differential part stays


def _pre_loc_controller(params, name, monkeypatch):
    controller = _controller(params, name)
    monkeypatch.setattr(controller, "_is_in_pre_loc_window", lambda: True)
    return controller


@pytest.mark.parametrize("name", ["D1", "D2", "D2+D3"])
def test_fall_watch_on_the_reapproaching_leg_itself(params, name, monkeypatch) -> None:
    """424.4.1: the re-approaching leg (RR) losing its load starts the watch (r79 L2 s0)."""
    controller = _pre_loc_controller(params, name, monkeypatch)
    controller._state.active_reapproaches[3] = object()
    f_min = controller.geometry.F_min_N
    loads = [5e4, 5e4, 5e4, 2.0 * f_min + 3e3]
    controller._update_fall_watch(_LowerReading(20.0, loads))
    controller._update_fall_watch(_LowerReading(20.1, loads[:3] + [2.0 * f_min + 2.5e3]))
    assert controller.fix.fall_watch is None  # fell 0.5 kN: below the 1 kN drop
    controller._update_fall_watch(_LowerReading(20.2, loads[:3] + [2.0 * f_min + 1e3]))
    assert controller.fix.fall_watch == {"leg": 3, "t_start_s": 20.2}
    assert controller.fix.diag_events == 1
    event = fx.FALL_HOLD_EVENT if "D1" in name else fx.FALL_SLOW_EVENT
    assert any(e.name == f"{event}:RR" for e in controller.events)
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    controller._state.pre_loc_prev_loads_N = None  # P30fz: first window period, no slowdown
    out = controller._apply_pre_loc_lift_pause(_LowerReading(20.2, [5e4] * 4), speeds)
    assert out[3] == speeds[3]  # the falling, re-approaching leg keeps its command
    if "D1" in name:
        np.testing.assert_array_equal(out[:3], 0.0)
    else:
        assert float(np.mean(out[:3])) == pytest.approx(0.16 * controller.geometry.max_speed_m_s)
    assert controller.fix.restrain_periods == 1


def test_fall_watch_ends_on_release_level_contact_and_time(params, monkeypatch) -> None:
    controller = _pre_loc_controller(params, "D1", monkeypatch)
    f_min = controller.geometry.F_min_N
    watch = {"leg": 2, "t_start_s": 10.0}
    low = np.full(4, 2.0 * f_min)
    assert not controller._has_fall_watch_ended(watch, low, 11.0)
    assert controller._has_fall_watch_ended(watch, np.full(4, 3.5 * f_min), 11.0)
    assert not controller._has_fall_watch_ended(watch, np.full(4, 3.4 * f_min), 11.0)
    assert controller._has_fall_watch_ended(watch, low, 13.0)  # 3 s
    run = c2._Reapproach(2, 10.5, 0.3, controller.config.r8.lifted_reapproach.mode,
                         end_s=11.0, outcome="contact")
    controller._state.reapproach_history.append(run)
    assert controller._has_fall_watch_ended(watch, low, 11.1)


def test_p30fz_slowdown_wins_the_period(params, monkeypatch) -> None:
    controller = _pre_loc_controller(params, "D1", monkeypatch)
    controller.fix.fall_watch = {"leg": 3, "t_start_s": 20.0}
    project_class = type(controller).__mro__[1]
    monkeypatch.setattr(project_class, "_apply_pre_loc_lift_pause",
                        lambda self, reading, speeds: speeds)
    controller._state.pre_loc_pause_leg = 3
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    out = controller._apply_pre_loc_lift_pause(_LowerReading(20.1, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out, speeds)
    assert controller.fix.yielded_periods == 1 and controller.fix.restrain_periods == 0


def test_d1p_token_is_d1_with_the_p30fz_overlay() -> None:
    settings = fx.parse_candidate("D1p")
    assert settings.d1_fall_hold and settings.d1p_over_p30fz and settings.has_qc_token
    assert not fx.parse_candidate("D1").d1p_over_p30fz
    assert fx.parse_candidate("D1p+D3").d3_repeat_reapproach_slow
    with pytest.raises(ValueError, match="alternatives"):
        fx.parse_candidate("D1p+D2")
    with pytest.raises(ValueError, match="d1_fall_hold"):
        fx.CandidateSettings(d1p_over_p30fz=True)


def _p30fz_controller(params, name, monkeypatch):
    controller = _pre_loc_controller(params, name, monkeypatch)
    project_class = type(controller).__mro__[1]
    monkeypatch.setattr(project_class, "_apply_pre_loc_lift_pause",
                        lambda self, reading, speeds: speeds)
    controller._state.pre_loc_pause_leg = 3
    return controller


def test_d1p_stops_over_p30fz_while_the_watched_leg_keeps_falling(params, monkeypatch) -> None:
    """424.9: watched leg RR falls 1.5 kN per period below 2 F_min during P30fz -> D1 stop;
    the stop holds (latched) when the fall slows, until the D1 release."""
    controller = _p30fz_controller(params, "D1p", monkeypatch)
    f_min = controller.geometry.F_min_N
    monkeypatch.setattr(controller, "_load_estimate_N", lambda force_N: force_N)  # no seal band
    others = [5e4, 5e4, 5e4]
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    controller._update_fall_watch(_LowerReading(30.4, others + [2.0 * f_min + 2e3]))
    controller._update_fall_watch(_LowerReading(30.5, others + [2.0 * f_min + 0.5e3]))
    assert controller.fix.fall_watch == {"leg": 3, "t_start_s": 30.5}
    out = controller._apply_pre_loc_lift_pause(_LowerReading(30.5, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out, speeds)  # 2 F_min + 0.5 kN: P30fz keeps the period
    assert controller.fix.yielded_periods == 1
    controller._update_fall_watch(_LowerReading(30.6, others + [2.0 * f_min - 1e3]))
    out = controller._apply_pre_loc_lift_pause(_LowerReading(30.6, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out[:3], 0.0)
    assert out[3] == speeds[3]
    assert controller.fix.p30fz_overrides == 1 and controller.fix.p30fz_override_periods == 1
    assert any(e.name == f"{fx.FALL_HOLD_OVER_P30FZ_EVENT}:RR" for e in controller.events)
    controller._update_fall_watch(_LowerReading(30.7, others + [2.0 * f_min - 1.2e3]))
    out = controller._apply_pre_loc_lift_pause(_LowerReading(30.7, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out[:3], 0.0)  # latched: fell only 0.2 kN
    assert controller.fix.p30fz_overrides == 1 and controller.fix.p30fz_override_periods == 2
    controller._update_fall_watch(_LowerReading(30.8, others + [3.5 * f_min]))
    assert controller.fix.fall_watch is None  # D1 release


def test_d1_still_yields_to_p30fz_on_the_same_fall(params, monkeypatch) -> None:
    controller = _p30fz_controller(params, "D1", monkeypatch)
    f_min = controller.geometry.F_min_N
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    controller._update_fall_watch(_LowerReading(30.5, [5e4] * 3 + [2.0 * f_min + 1e3]))
    controller._update_fall_watch(_LowerReading(30.6, [5e4] * 3 + [2.0 * f_min - 1e3]))
    out = controller._apply_pre_loc_lift_pause(_LowerReading(30.6, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out, speeds)
    assert controller.fix.p30fz_overrides == 0 and controller.fix.yielded_periods == 1


def test_d1r_token_and_alternatives() -> None:
    settings = fx.parse_candidate("D1r+D3")
    assert settings.d1r_predicted_hold and settings.d3_repeat_reapproach_slow
    assert settings.has_qc_token
    for name in ("D1r+D1", "D1r+D2", "D1r+D1p0"):
        with pytest.raises(ValueError, match="alternatives"):
            fx.parse_candidate(name)


def _set_history(controller, loads_by_period) -> None:
    history = controller._state.load_estimate_history
    history.clear()
    for loads in loads_by_period:
        history.append(np.asarray(loads, float))


def test_r5_prediction_is_the_c2_arithmetic(params, monkeypatch) -> None:
    controller = _pre_loc_controller(params, "D1r", monkeypatch)
    r5 = controller.config.r8.fast_relevel
    n = r5.rate_intervals
    falling = [[5e4, 5e4, 5e4, 40e3 - 3e3 * k] for k in range(n + 1)]
    _set_history(controller, falling)
    predicted = controller._r5_predicted_lower_N()
    horizon = r5.horizon_periods or 1 + controller.config.r8.output_delay_periods
    if not r5.uses_fallback_slope:
        assert predicted[3] == pytest.approx(falling[-1][3] - 3e3 * horizon)
    assert predicted[0] == pytest.approx(5e4)
    _set_history(controller, falling[:n])
    assert controller._r5_predicted_lower_N() is None  # history not full


def test_d1r_stops_the_other_legs_over_p30fz_and_releases(params, monkeypatch) -> None:
    controller = _p30fz_controller(params, "D1r", monkeypatch)
    monkeypatch.setattr(controller, "_load_estimate_N", lambda force_N: force_N)
    f_min = controller.geometry.F_min_N
    predictions = {"value": np.array([5e4, 5e4, 5e4, f_min + 4e3])}
    monkeypatch.setattr(controller, "_r5_predicted_lower_N", lambda: predictions["value"])
    controller._state.active_reapproaches[2] = object()  # RL re-approaching: not stopped
    controller._update_predicted_watch(_LowerReading(30.4, [5e4, 5e4, 5e4, 2.5 * f_min]))
    assert controller.fix.pred_watch == {"leg": 3, "t_start_s": 30.4}
    assert any(e.name == f"{fx.DIAG_HOLD_PRED_EVENT}:RR" for e in controller.events)
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    out = controller._apply_pre_loc_lift_pause(_LowerReading(30.4, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out, [0.0, 0.0, 4e-3, 4e-3])  # P30fz period: still stops
    predictions["value"] = np.array([5e4, 5e4, 5e4, f_min + 9e3])
    controller._update_predicted_watch(_LowerReading(30.5, [5e4] * 3 + [2.0 * f_min]))
    assert controller.fix.pred_watch is not None  # below F_min + 10 kN: held
    predictions["value"] = np.array([5e4, 5e4, 5e4, f_min + 10e3])
    controller._update_predicted_watch(_LowerReading(30.6, [5e4] * 3 + [2.0 * f_min]))
    assert controller.fix.pred_watch is None


def test_d1r_needs_a_low_current_load(params, monkeypatch) -> None:
    """A low prediction on a leg that still reads >= 3 F_min starts nothing (firm ground)."""
    controller = _pre_loc_controller(params, "D1r", monkeypatch)
    monkeypatch.setattr(controller, "_load_estimate_N", lambda force_N: force_N)
    f_min = controller.geometry.F_min_N
    monkeypatch.setattr(controller, "_r5_predicted_lower_N",
                        lambda: np.array([5e4, 5e4, 5e4, f_min + 1e3]))
    controller._update_predicted_watch(_LowerReading(30.4, [5e4, 5e4, 5e4, 3.0 * f_min]))
    assert controller.fix.pred_watch is None and controller.fix.pred_hold_events == 0


# ------------------------------------------------------------------ spec 424.9.3 D1q
def test_d1q_tokens_parameters_and_alternatives() -> None:
    d1q = fx.parse_candidate("D1q")
    assert d1q.d1q_hold and d1q.d1q_gate_a and d1q.d1q_gate_b and not d1q.d1q_slow
    assert d1q.quick_hold_reason == "ab" and d1q.has_qc_token
    assert fx.parse_candidate("D1qa").quick_hold_reason == "a"
    assert fx.parse_candidate("D1qb").quick_hold_reason == "b"
    assert fx.parse_candidate("D2q").d1q_slow
    assert fx.parse_candidate("D1q+D3").d3_repeat_reapproach_slow
    assert fx.parse_candidate("D1q+d1q_twist_m=0.010").d1q_twist_m == pytest.approx(0.010)
    assert fx.parse_candidate("D1q", {"d1q_twist_m": 0.020}).d1q_twist_m == pytest.approx(0.020)
    for name in ("D1q+D1", "D1q+D2", "D1q+D1p", "D1q+D1p0", "D1q+D1r", "D1q+D1qa",
                 "D2q+D1qb"):
        with pytest.raises(ValueError, match="alternatives"):
            fx.parse_candidate(name)
    with pytest.raises(ValueError, match="D2q"):
        fx.CandidateSettings(d1q_slow=True)
    with pytest.raises(ValueError, match="unknown parameter"):
        fx.parse_candidate("D1q+d1q_twist=0.010")


def test_extrapolated_lower_load_uses_the_last_fall() -> None:
    assert fx.extrapolated_lower_N(20e3, 23e3, 4) == pytest.approx(8e3)
    assert fx.extrapolated_lower_N(20e3, 19e3, 4) == pytest.approx(24e3)  # rising


RECTANGLE_PADS_XY = np.array([[2.0, 1.5], [2.0, -1.5], [-2.0, 1.5], [-2.0, -1.5]])
"""FL, FR, RL, RR on a rectangle (x forward, y left)."""


def test_stroke_twist_residual_removes_heave_and_tilt() -> None:
    roll, pitch, heave = 0.02, -0.01, 0.03
    planar = heave + RECTANGLE_PADS_XY[:, 1] * roll - RECTANGLE_PADS_XY[:, 0] * pitch
    assert fx.stroke_twist_residual_m(RECTANGLE_PADS_XY, planar) == pytest.approx(0.0, abs=1e-12)
    one_pad = planar + np.array([0.0, 0.0, 0.0, 0.016])  # RR sinks 16 mm more
    assert fx.stroke_twist_residual_m(RECTANGLE_PADS_XY, one_pad) == pytest.approx(0.016)
    fr_pad = np.array([0.0, 0.012, 0.0, 0.0])
    assert fx.stroke_twist_residual_m(RECTANGLE_PADS_XY, fr_pad) == pytest.approx(-0.012)


class _StrokeReading(_LowerReading):
    def __init__(self, t_s, lower_N, rod_stroke_m):
        super().__init__(t_s, lower_N)
        self.rod_stroke_m = np.asarray(rod_stroke_m, float)


def _quick_controller(params, name, monkeypatch):
    """D1q controller in the pre-LOC window; P30fz stubbed (its state set by the test)."""
    controller = _pre_loc_controller(params, name, monkeypatch)
    project_class = type(controller).__mro__[1]
    monkeypatch.setattr(project_class, "_apply_pre_loc_lift_pause",
                        lambda self, reading, speeds: speeds)
    monkeypatch.setattr(controller, "_load_estimate_N", lambda force_N: force_N)
    return controller


def _machine_twist_mm(controller, stroke_change_m) -> float:
    return fx.stroke_twist_residual_m(controller.geometry.pad_xy_m, stroke_change_m) * 1e3


def _quick_period(controller, t_s, lower_N, strokes_m, previous_N=None, p30fz_start=False):
    state = controller._state
    if previous_N is not None:
        state.pre_loc_prev_loads_N = np.asarray(previous_N, float)
    if p30fz_start:
        state.pre_loc_pause_leg, state.pre_loc_pause_since_s = 3, t_s
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    return controller._apply_pre_loc_lift_pause(_StrokeReading(t_s, lower_N, strokes_m), speeds)


def _rr_falls_into_a_soft_pad(controller, t_start_s=30.0, rr_sink_m=0.020):
    """First pre-LOC period (twist reference), then P30fz starts on RR: 18 -> 15 kN."""
    f_min = controller.geometry.F_min_N
    _quick_period(controller, t_start_s - 1.0, [5e4] * 4, [0.30] * 4)
    loads = [5e4, 5e4, 5e4, 15e3]
    strokes = [0.32, 0.32, 0.32, 0.32 + rr_sink_m]
    out = _quick_period(controller, t_start_s, loads, strokes,
                        previous_N=[5e4, 5e4, 5e4, 18e3], p30fz_start=True)
    assert 15e3 - 4 * 3e3 < f_min + 5e3  # G-a holds on these numbers
    return out, loads, strokes


def test_d1q_stops_the_other_legs_in_the_p30fz_start_period(params, monkeypatch) -> None:
    controller = _quick_controller(params, "D1q", monkeypatch)
    controller._state.active_reapproaches[1] = object()  # FR re-approaching: not stopped
    out, loads, strokes = _rr_falls_into_a_soft_pad(controller)
    np.testing.assert_array_equal(out, [0.0, 4e-3, 0.0, 4e-3])
    assert controller.fix.quick_watch == {"leg": 3, "t_start_s": 30.0, "reason": "ab"}
    assert any(e.name == f"{fx.DIAG_HOLD_QUICK_EVENT}:RR:ab" for e in controller.events)
    check = controller.fix.quick_gate_checks[0]
    assert check["a"] and check["b"] and check["started"]
    assert check["twist_mm"] == pytest.approx(
        _machine_twist_mm(controller, [0.02, 0.02, 0.02, 0.04]), abs=0.01)
    assert check["twist_mm"] > 15.0
    for k in range(1, 15):  # held until 1.5 s
        out = _quick_period(controller, 30.0 + 0.1 * k, loads, strokes)
        assert out[0] == 0.0
    out = _quick_period(controller, 31.5, loads, strokes)
    assert controller.fix.quick_watch is None and out[0] == pytest.approx(5e-3)
    assert controller.fix.quick_hold_total_s == pytest.approx(1.5)


def test_d1q_releases_at_3p5_f_min_and_keeps_a_run_budget(params, monkeypatch) -> None:
    controller = _quick_controller(params, "D1q", monkeypatch)
    f_min = controller.geometry.F_min_N
    _, loads, strokes = _rr_falls_into_a_soft_pad(controller)
    _quick_period(controller, 30.1, loads[:3] + [3.5 * f_min], strokes)
    assert controller.fix.quick_watch is None  # released by the load
    controller.fix.quick_hold_total_s = 3.0  # budget spent: the next P30fz start holds nothing
    out = _quick_period(controller, 40.0, loads, strokes, previous_N=[5e4, 5e4, 5e4, 18e3],
                        p30fz_start=True)
    np.testing.assert_array_equal(out, [5e-3, 4e-3, 4e-3, 4e-3])
    assert controller.fix.quick_gate_checks[-1]["started"] is False
    assert controller.fix.quick_hold_events == 1


@pytest.mark.parametrize(("name", "rr_sink_m", "is_started"),
                         [("D1q", 0.010, False), ("D1qa", 0.010, True),
                          ("D1qb", 0.010, False), ("D1q+d1q_twist_m=0.009", 0.010, True)])
def test_d1q_variants_follow_their_gates(params, monkeypatch, name, rr_sink_m,
                                         is_started) -> None:
    controller = _quick_controller(params, name, monkeypatch)
    _rr_falls_into_a_soft_pad(controller, rr_sink_m=rr_sink_m)
    assert (controller.fix.quick_watch is not None) is is_started
    twist_mm = _machine_twist_mm(controller, [0.02, 0.02, 0.02, 0.02 + rr_sink_m])
    assert controller.fix.quick_gate_checks[0]["twist_mm"] == pytest.approx(twist_mm, abs=0.01)
    assert 9.0 < twist_mm < 15.0  # between the two thresholds of the parametrisation


def test_d1qb_needs_no_deep_fall(params, monkeypatch) -> None:
    controller = _quick_controller(params, "D1qb", monkeypatch)
    _quick_period(controller, 29.0, [5e4] * 4, [0.30] * 4)
    _quick_period(controller, 30.0, [5e4, 5e4, 5e4, 25e3], [0.32, 0.32, 0.32, 0.34],
                  previous_N=[5e4, 5e4, 5e4, 27.5e3], p30fz_start=True)
    check = controller.fix.quick_gate_checks[0]
    assert not check["a"] and check["b"]
    assert controller.fix.quick_watch == {"leg": 3, "t_start_s": 30.0, "reason": "b"}


def test_d2q_slows_instead_of_stopping(params, monkeypatch) -> None:
    controller = _quick_controller(params, "D2q", monkeypatch)
    out, _, _ = _rr_falls_into_a_soft_pad(controller)
    assert out[3] == pytest.approx(4e-3)
    slow_m_s = 0.16 * controller.geometry.max_speed_m_s
    assert float(np.mean(out[:3])) == pytest.approx(slow_m_s)


def test_d1q_starts_only_in_the_p30fz_start_period(params, monkeypatch) -> None:
    controller = _quick_controller(params, "D1q", monkeypatch)
    _quick_period(controller, 29.0, [5e4] * 4, [0.30] * 4)
    controller._state.pre_loc_pause_leg, controller._state.pre_loc_pause_since_s = 3, 29.9
    out = _quick_period(controller, 30.0, [5e4, 5e4, 5e4, 15e3], [0.32, 0.32, 0.32, 0.34],
                        previous_N=[5e4, 5e4, 5e4, 18e3])
    assert controller.fix.quick_watch is None and not controller.fix.quick_gate_checks
    np.testing.assert_array_equal(out, [5e-3, 4e-3, 4e-3, 4e-3])  # P30fz period, D off


def _start_run(controller, leg: int, t_s: float) -> None:
    run = c2._Reapproach(leg, t_s, 0.3, controller.config.r8.lifted_reapproach.mode)
    controller._state.active_reapproaches[leg] = run
    controller._state.reapproach_history.append(run)


def test_d3_slows_the_second_reapproach_of_a_leg(params, monkeypatch) -> None:
    controller = _pre_loc_controller(params, "D3", monkeypatch)
    controller.config = replace(controller.config, pre_loc_lift_pause=replace(
        controller.config.pre_loc_lift_pause, enable=True))
    _start_run(controller, 3, 30.0)
    controller._count_pre_loc_reapproaches(_LowerReading(30.0, [5e4] * 4))
    assert not controller.fix.slow_reapproach_legs  # the first one runs at x 4
    fast = controller._reapproach_speed_factor(3)
    controller._state.active_reapproaches.pop(3)
    _start_run(controller, 3, 31.0)
    controller._count_pre_loc_reapproaches(_LowerReading(31.0, [5e4] * 4))
    assert controller.fix.slow_reapproach_legs == {3}
    assert controller.fix.pre_loc_reapproach_counts == [0, 0, 0, 2]
    pause_factor = controller.config.pre_loc_lift_pause.reapproach_speed_factor
    assert controller._reapproach_speed_factor(3) == pytest.approx(fast / pause_factor * 2.0)
    assert any(e.name == f"{fx.REPEAT_REAPPROACH_SLOW_EVENT}:RR" for e in controller.events)
    speeds = np.array([10e-3, 10e-3, 10e-3, 15e-3])
    out = controller._apply_pre_loc_lift_pause(_LowerReading(31.0, [5e4] * 4), speeds)
    assert out[3] == speeds[3]
    assert float(np.mean(out[:3])) == pytest.approx(0.16 * controller.geometry.max_speed_m_s)
    controller._state.active_reapproaches.pop(3)  # the slow run ended
    controller._count_pre_loc_reapproaches(_LowerReading(32.0, [5e4] * 4))
    assert not controller.fix.slow_reapproach_legs


@pytest.mark.parametrize("name", ["D1", "D2", "D3", "D2+D3"])
def test_qc_tokens_idle_without_a_falling_leg(params, name, monkeypatch) -> None:
    controller = _pre_loc_controller(params, name, monkeypatch)
    for k in range(5):
        reading = _LowerReading(20.0 + 0.1 * k, [5e4 - 2e3 * k] * 4)  # falls, stays high
        controller._count_pre_loc_reapproaches(reading)
        if name != "D3":
            controller._update_fall_watch(reading)
    speeds = np.array([5e-3, 4e-3, 4e-3, 4e-3])
    out = controller._apply_pre_loc_lift_pause(_LowerReading(20.5, [5e4] * 4), speeds)
    np.testing.assert_array_equal(out, speeds)
    assert controller.fix.diag_events == 0


# ------------------------------------------------------------- spec 424.6 A-3 / A-5
def _a3_record(candidate, soil, sha, passed=True, t_ready_s=60.0, failed_rows=(),
               fix_events=()):
    return {"suite": "h6", "id": f"H6|{soil}|B|top|flat|m1.2", "candidate": candidate,
            "verdict": "pass" if passed else "fail", "passed": passed, "hash": sha,
            "t_ready_s": t_ready_s, "failed_rows": list(failed_rows),
            "metrics": {"fix_events": [(1.0, name) for name in fix_events]}}


def test_a3_hard_ground_needs_the_current_hash() -> None:
    before = _a3_record("current", "G1", "a")
    assert fx.acceptance_a3("h6", before["id"], before, _a3_record("L2", "G1", "a"))["pass"]
    acted = _a3_record("L2", "G1", "b", fix_events=["FIX_L2_CONFIRM"])
    assert not fx.acceptance_a3("h6", acted["id"], before, acted)["pass"]
    assert fx.acceptance_a3("g6", "x|y", before, acted) is None


def test_a3_soft_ground_relaxed_where_a_fix_acted() -> None:
    before = _a3_record("current", "J1", "a", t_ready_s=60.0)
    fine = _a3_record("L2", "J1", "b", t_ready_s=64.0, fix_events=["FIX_L2_CONFIRM"])
    assert fx.acceptance_a3("h6", fine["id"], before, fine)["pass"]
    late = _a3_record("L2", "J1", "b", t_ready_s=66.0, fix_events=["FIX_L2_CONFIRM"])
    assert fx.acceptance_a3("h6", late["id"], before, late)["reasons"] == ["READY +6.0 s"]
    p32 = _a3_record("L2", "J1", "b", passed=False, failed_rows=["P3-2"],
                     fix_events=["FIX_L2_CONFIRM"])
    assert fx.acceptance_a3("h6", p32["id"], before, p32)["reasons"] == [
        "pass -> fail", "new P3-2 violation"]
    idle = _a3_record("L2", "J1", "b")
    assert fx.acceptance_a3("h6", idle["id"], before, idle)["reasons"] == [
        "hash differs without a candidate event"]


def test_summarize_counts_a3_and_idle_hash() -> None:
    before = _a3_record("current", "rigid", "a")
    after = _a3_record("L1", "rigid", "b")
    entry = fx.summarize([before, after])["by_suite_candidate"]["h6|L1"]
    assert entry["a3_checked"] == 1 and entry["a3_fail"] == 1
    assert entry["idle_hash_differs"] == 1 and entry["acted"] == 0



# ------------------------------------------------------- spec 424.8.1 stored re-judgement
def _stored(revoke: bool, recontact_s: float = 0.13) -> dict:
    weight_N = 4.18e5
    fix_events = [[36.6, "FIX_LOC_REVOKE:2.3"]] if revoke else []
    return {"suite": "h6", "id": "H6|J1|B|top|flat|m1.1", "candidate": "L1", "verdict": "fail",
            "passed": False, "failed_rows": ["P3-1"], "t_ready_s": 80.6, "min_force_kN": 74.5,
            "final_phase": "ready", "crawler_N_max_after_ready": 0.0, "warnings": [],
            "late_loc_reapproach": {"t_off_s": 35.8, "crawler_threshold_N": 0.01 * weight_N,
                                    "reapproach_intervals": []},
            "metrics": {"window_checks": [{"t_s": 35.2, "vetoed": None},
                                          {"t_s": 38.0, "vetoed": None}],
                        "fix_events": fix_events, "loc_crawler_kN": [1.92, 0.0],
                        "crawler_recontact": {"recontact_events": {"weight_N": weight_N, "events": [
                            {"t_start_s": 35.417, "t_end_s": 35.417 + recontact_s,
                             "duration_s": recontact_s, "max_normal_N": 0.013 * weight_N,
                             "class": "strict_fail"}]}}}}


def test_rejudge_final_loc_turns_the_early_recontact_into_a_transient() -> None:
    after = fx.rejudge_final_loc(_stored(revoke=True), 9.415)
    assert after["verdict"] == "pass" and after["failed_rows"] == []
    block = after["rejudge_finloc"]
    assert block["t_loc_final_s"] == 38.0 and block["P3-1"]["classes"] == ["transient_flag"]
    assert block["P3-2"]["loc_delay_s"] == pytest.approx(2.2)
    long_event = fx.rejudge_final_loc(_stored(revoke=True, recontact_s=0.6), 9.415)
    assert long_event["verdict"] == "fail" and long_event["failed_rows"] == ["P3-1"]
    unchanged = _stored(revoke=False)
    assert fx.rejudge_final_loc(unchanged, 9.415) is unchanged


# ------------------------------------------------------------- spec 424.8.2 S5 / S6
def test_s6_needs_l1_and_s5_s6_parse() -> None:
    with pytest.raises(ValueError, match="L1"):
        fx.parse_candidate("S6")
    settings = fx.parse_candidate("L1+L2+S5+S6")
    assert settings.s5_push_extend and settings.s6_saturation_loc and settings.l1_revoke


def _soil_mode_controller(params, name):
    controller = _controller(params, name)
    controller._state.phase = c2.C2Phase.LEVEL
    controller._state.in_crawler_zone = True
    soil = controller._soil_state()
    soil.is_soil_mode, soil.soil_mode_start_s, soil.soil_mode_start_stroke_m = True, 30.0, 0.40
    return controller


def _push(controller, push_m: float, load_N: float, t_s: float, longest_m: float = 0.0):
    strokes = [0.40 + push_m] * 3 + [max(0.40 + push_m, longest_m)]
    controller._hold_crawler_zone_until_liftoff(_Reading(t_s, [load_N / 4.0] * 4, strokes))


@pytest.mark.parametrize(("rise_N", "longest_m", "extends"), [
    (10e3, 0.0, True),  # progress 10 kN per 50 mm (> 0.02 W_ref)
    (2e3, 0.0, False),  # no progress
    (10e3, 0.62, False),  # 0.62 + 0.05 > guard - 0.03
])
def test_s5_extends_the_push_limit_only_with_progress_and_stroke(params, rise_N, longest_m,
                                                                 extends) -> None:
    controller = _soil_mode_controller(params, "S5")
    for k, push_m in enumerate(np.arange(0.0, 0.145, 0.01)):
        _push(controller, push_m, 3.0e5 + rise_N * push_m / 0.05, 30.0 + 0.1 * k)
    assert controller.phase is c2.C2Phase.LEVEL and not controller.fix.push_extensions
    _push(controller, 0.16, 3.0e5 + rise_N * 0.16 / 0.05, 32.0, longest_m)
    if extends:
        assert controller.phase is c2.C2Phase.LEVEL
        assert controller.config.soil.max_push_m == pytest.approx(0.20)
        assert any(e.name == f"{fx.PUSH_EXTEND_EVENT}:200" for e in controller.events)
    else:
        assert controller.phase is c2.C2Phase.FAULT and not controller.fix.push_extensions


def test_s5_stops_at_the_300_mm_limit(params) -> None:
    controller = _soil_mode_controller(params, "S5")
    controller.config = replace(controller.config,
                                soil=replace(controller.config.soil, max_push_m=0.30))
    for k, push_m in enumerate(np.arange(0.25, 0.301, 0.01)):
        _push(controller, push_m, 3.0e5 + 1e4 * push_m / 0.05, 30.0 + 0.1 * k)
    _push(controller, 0.31, 3.0e5 + 1e4 * 0.31 / 0.05, 31.0)
    assert controller.phase is c2.C2Phase.FAULT and not controller.fix.push_extensions


def _rise_rows(controller, rises_kN, t0_s=40.0):
    """``s1_rise_trace`` rows 2 mm apart in stroke (window ends)."""
    for k, rise in enumerate(rises_kN):
        controller.fix.s1_rise_trace.append((round(t0_s + 0.1 * k, 2), 400.0 + 2.0 * k, rise,
                                             370.0, 100.0))


@pytest.mark.parametrize(("previous_kN", "current_N", "confirms"), [
    (8.0, 2.2e3, True),  # 2.2 <= 0.3 x 8 and <= 4 kN
    (8.0, 2.6e3, False),  # above 0.3 x 8
    (20.0, 4.5e3, False),  # above 4 kN
])
def test_s6_confirms_on_a_saturating_rise(params, monkeypatch, previous_kN, current_N,
                                          confirms) -> None:
    controller = _soil_mode_controller(params, "L1+S6")
    soil = controller._soil_state()
    first = c2._PlateauSample(t_s=40.0, mean_motor_stroke_m=0.400, load_sum_N=3.7e5,
                              corner_clearance_m=np.zeros(4), raw_attitude_rad=(0.0, 0.0))
    last = replace(first, t_s=41.0, mean_motor_stroke_m=0.420)
    soil.window.extend([first, last])
    _rise_rows(controller, [previous_kN] * 6)  # strokes 400 .. 410 mm
    monkeypatch.setattr(controller, "_plateau_tail", lambda: [replace(first, t_s=40.5,
                        mean_motor_stroke_m=0.410), last])
    monkeypatch.setattr(controller, "_plateau_rise_N", lambda tail: current_N)
    controller._state.last_reading = _loc_reading(3.7e5, stroke_m=0.42, t_s=41.0)
    controller._s6_check(_loc_reading(3.7e5, stroke_m=0.42, t_s=41.0))
    assert soil.is_liftoff_confirmed is confirms
    assert controller.fix.s6_confirms == int(confirms)


def test_s1_rise_trace_records_every_candidate(params, monkeypatch) -> None:
    controller = _lw_controller(params, "current", monkeypatch)
    soil = controller._soil_state()
    for k in range(8):
        reading = _WindowReading(40.0 + 0.1 * k, [0.400 + 0.002 * k] * 4, load_N=3.0e5 + 1e3 * k)
        controller._state.last_reading = reading
        soil.window.append(c2._PlateauSample(
            t_s=reading.t_s, mean_motor_stroke_m=0.400 + 0.002 * k, load_sum_N=3.0e5 + 1e3 * k,
            corner_clearance_m=np.zeros(4), raw_attitude_rad=(0.0, 0.0)))
        controller._record_s1_rise(reading)
    rows = controller.fix.s1_rise_trace
    assert rows and rows[0][1] == pytest.approx(410.0)
    assert rows[0][2] == pytest.approx(5.0, abs=1e-6)  # 1 kN per 2 mm = 5 kN per 10 mm
