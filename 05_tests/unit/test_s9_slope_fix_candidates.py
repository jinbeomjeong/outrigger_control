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
