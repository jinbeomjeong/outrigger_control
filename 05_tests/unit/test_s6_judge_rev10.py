"""S6 judge after control spec rev. 10 / 62 (J-1, J-2, J-4, J-5; user decisions U53-U58).

Synthetic case directories (result, Record, pad record, probe history) stand in for the Chrono
runs; the RE3 batches were dry-run by hand (every former failed row passes).
"""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.params import ParamsError
from outrigger_sim.verify.s6_control import (
    EventTransientSettings,
    case_metrics,
    event_force_metrics,
    event_transient_window,
    judge,
    probe_metrics,
)

PERIOD_S = 0.02
PAD_S = 0.001
LEVEL_QUAT = [1.0, 0.0, 0.0, 0.0]
KN = np.full(4, 2.0e7)


def _row(rows, item, case=None):
    return next(r for r in rows if r["item"] == item and (case is None or r["case"] == case))


def _base_metrics(case, group="G2", **extra):
    base = {"case": case, "group": group, "level": "top", "floor": "flat", "grade": "ideal",
            "final_phase": "ready", "ready_window_ok": True, "saturation_steps": 0,
            "times_s": {"ready": 30.0}}
    base.update(extra)
    return base


# --- J-2 ------------------------------------------------------------------------------------


def _level_rows(forces):
    metrics = [
        _base_metrics(f"G2-R_{lv}_fdown3.5", "G2-R", level=lv, floor="fdown3.5",
                      min_cyl_after_liftoff_kN=forces[lv], min_cyl_excl_reanchor_kN=forces[lv],
                      min_cyl_leg="RR", min_cyl_t_s=40.0)
        for lv in ("top", "middle", "bottom")
    ]
    return judge(metrics, {})


def test_level_trend_allows_one_kilonewton() -> None:
    """U54 / U64 (1.25 kN): RE3 nose-down 57.31 / 57.57 / 56.80 kN (middle > bottom by
    0.77 kN) passes; 1.37 kN does not."""
    rows = _level_rows({"top": 57.31, "middle": 57.57, "bottom": 56.80})
    assert _row(rows, "8 level trend min force (excl. REANCHOR)")["passed"] is True
    rows = _level_rows({"top": 57.31, "middle": 57.57, "bottom": 56.20})
    assert _row(rows, "8 level trend min force (excl. REANCHOR)")["passed"] is False


# --- synthetic case directory ----------------------------------------------------------------


def _case(*, event="drop_RR_30", t_event=10.0, end_s=30.0, rr_lift=(10.05, 11.0),
          fl_lift=(10.3, 10.5), fl_rise_m=0.0, probes=None, phases=None, u_cmd=None,
          probe_intervals=None, f_cyl_pad=None, level="top"):
    t_rec = np.arange(0.0, end_s + 1e-9, PERIOD_S)
    t_pad = np.arange(0.0, end_s + 1e-9, PAD_S)
    n_pad = np.full((len(t_pad), 4), 50e3)
    rr = (t_pad >= rr_lift[0]) & (t_pad < rr_lift[1])
    n_pad[rr, 3] = 0.0
    fl = (t_pad >= fl_lift[0]) & (t_pad < fl_lift[1])
    n_pad[fl, 0] = 0.0
    contact = np.zeros((len(t_pad), 4, 3))
    contact[:, :, 2] = -1.0 - 50e3 / KN  # floor point at z = -1 while loaded
    contact[fl, 0, 2] = -1.0 + fl_rise_m
    anchors = np.zeros((len(t_pad), 4, 3))
    pads = {
        "t": t_pad, "N": n_pad,
        "F_cyl": f_cyl_pad if f_cyl_pad is not None else np.full((len(t_pad), 4), 50e3),
        "F_cyl_min_interval": np.full((len(t_pad), 4), 50e3),
        "n_world": np.tile([0.0, 0.0, 1.0], (len(t_pad), 1)),
        "contact_point_world": contact, "anchor_world": anchors,
    }
    commands = np.zeros((len(t_rec), 4)) if u_cmd is None else u_cmd
    rec = {
        "t": t_rec, "body_quat_wxyz": np.tile(LEVEL_QUAT, (len(t_rec), 1)),
        "u_cmd": commands, "u_applied": commands, "F_cyl": np.full((len(t_rec), 4), 50e3),
        "F_crawler": np.zeros((len(t_rec), 3)),
        "meas.specific_force": np.tile([0.0, 0.0, 9.80665], (len(t_rec), 1)),
    }
    rec["F_crawler"][:10, 2] = 1.0  # crawler lift-off at 0.2 s
    result = {
        "case": "RE1bF_top_flat_dropRR30", "settings": {
            "start_t_s": 0.0, "group": "RE1b", "level": level, "floor": "flat",
            "grade": "ideal", "event": event, "target_deg": [0.0, 0.0]},
        "phases": phases or [[0.0, "touch"], [2.0, "level"], [5.0, "ready"],
                             [t_event + 0.02, "level"], [t_event + 8.0, "ready"]],
        "event_t_s": t_event,
        "monitor": {"cylinder_force_max_N": [60e3] * 4, "saturation_step_count": [0] * 4},
        "controller_meta": {"period_s": PERIOD_S, "probe": {"hold_s": 0.4}},
    }
    if probe_intervals is not None:
        result["probe_intervals"] = probe_intervals
    return {"result": result, "rec": rec, "pads": pads, "events": [], "probes": probes or [],
            "dir": None}


# --- J-4 / window ----------------------------------------------------------------------------


def test_physical_window_ends_one_rocking_period_after_rr_recontact() -> None:
    case = _case()
    tm = {"t0": 0.0, "ready": 5.0, "liftoff": 0.2, "end": 30.0}
    window = event_transient_window(case, tm)
    assert window["rr_last_recontact_s"] == pytest.approx(11.0)
    assert window["lift_end_s"] == pytest.approx(11.82)
    assert window["notes"] == []
    fixed = event_transient_window(case, tm, EventTransientSettings(transient_window="fixed"))
    assert fixed["lift_end_s"] == pytest.approx(11.0)
    assert fixed["pressure_end_s"] == pytest.approx(12.0)


def test_window_is_capped_and_lower_levels_borrow_the_top_period() -> None:
    case = _case(rr_lift=(10.05, 30.5), level="bottom")
    tm = {"t0": 0.0, "ready": 5.0, "liftoff": 0.2, "end": 30.0}
    window = event_transient_window(case, tm)
    assert window["lift_end_s"] == pytest.approx(15.0)
    assert window["notes"] == ["T3_from_top_level", "transient_window_capped"]


def _event_rows(case):
    tm = {"t0": 0.0, "ready": 5.0, "liftoff": 0.2, "end": 30.0}
    event3 = event_force_metrics(case, tm, kn_N_m=KN)
    m = _base_metrics("RE1bF_top_flat_dropRR30", "RE1b", event="drop_RR_30",
                      min_cyl_after_liftoff_kN=0.0, min_cyl_leg="RR", min_cyl_t_s=10.1,
                      event3=event3)
    return judge([m], {}), event3


def test_other_leg_lift_inside_the_window_is_allowed_with_limits() -> None:
    """U57 (spec 62.2): FL off for 0.2 s, risen 0.6 mm inside W -> allowed."""
    rows, event3 = _event_rows(_case(fl_rise_m=0.0006))
    assert event3["other_legs_rise_max_m"][0] == pytest.approx(0.0006)
    assert _row(rows, "3 lift-off other legs in the event transient")["passed"] is True
    assert _row(rows, "3 lift-off other legs after the transient")["passed"] is True


@pytest.mark.parametrize(
    ("fl_lift", "rise_m", "item"),
    [
        ((10.3, 10.9), 0.0006, "3 lift-off other legs in the event transient"),  # 0.6 s
        ((10.3, 10.5), 0.0025, "3 lift-off other legs in the event transient"),  # 2.5 mm
        ((12.0, 12.1), 0.0006, "3 lift-off other legs after the transient"),  # after W
    ],
)
def test_other_leg_lift_beyond_a_limit_fails(fl_lift, rise_m, item) -> None:
    rows, _ = _event_rows(_case(fl_lift=fl_lift, fl_rise_m=rise_m))
    assert _row(rows, item)["passed"] is False


def test_anchor_move_limit() -> None:
    case = _case()
    case["pads"]["anchor_world"][case["pads"]["t"] >= 10.5, 0, 0] = 0.006
    rows, event3 = _event_rows(case)
    assert event3["other_slip_net_window_end_m"][0] == pytest.approx(0.006)
    assert event3["other_slip_max_excursion_m"][0] == pytest.approx(0.006)
    assert event3["other_slip_path_total_m"][0] == pytest.approx(0.006)
    assert _row(rows, "3 lift-off other legs in the event transient")["passed"] is False


# --- J-5 -------------------------------------------------------------------------------------


def _pressure_case():
    case = _case(rr_lift=(10.05, 13.0))
    t = case["rec"]["t"]
    area = np.pi / 4.0 * 0.115**2
    force = case["rec"]["F_cyl"]
    applied = case["rec"]["u_applied"]
    force[(t > 10.2) & (t < 10.4), 1] = 250e5 * area  # transient peak, locked
    force[(t > 20.0) & (t < 20.2), 0] = 190e5 * area  # retracting outside W
    applied[(t > 20.0) & (t < 20.2), 0] = -0.005
    force[(t > 22.0) & (t < 22.2), 2] = 150e5 * area  # extending outside W
    applied[(t > 22.0) & (t < 22.2), 2] = 0.005
    pad_force = case["pads"]["F_cyl"]
    tp = case["pads"]["t"]
    pad_force[(tp > 10.2) & (tp < 10.4), 1] = 252e5 * area
    return case


class _Params:
    legs = [type("Leg", (), {"pad_bottom_center_retracted_m": xy})()
            for xy in ([2.4, 1.3, 0.0], [2.4, -1.3, 0.0], [-2.4, 1.2, 0.0], [-2.4, -1.2, 0.0])]
    ground = type("Ground", (), {"crawler_bottom_z_m": -1.05})()

    def get(self, key):
        if key != "contact.rigid_floor.L1.kn_per_pad_N_m":
            raise ParamsError(key, "missing key")  # no cylinder keys: 115 mm items 4 / 5
        return dict.fromkeys(("FL", "FR", "RL", "RR"), 2.0e7)


def test_moving_pressure_outside_the_window_judges_extension_only() -> None:
    metrics = case_metrics(_pressure_case(), _Params())
    assert metrics["max_moving_pressure_excl_transient_bar"] == pytest.approx(150.0)
    assert metrics["max_retract_pressure_excl_transient_bar"] == pytest.approx(190.0)
    peak = metrics["transient_pressure_peak"]
    assert peak["max_bar"] == pytest.approx(252.0) and peak["leg"] == "FR"
    assert peak["state"] == "locked" and peak["source"] == "pads 1 ms"
    rows = judge([metrics], {})
    assert _row(rows, "4 max moving pressure outside the event transient")["passed"] is True
    assert _row(rows, "4 max pressure in the event transient")["passed"] is True
    every = case_metrics(_pressure_case(), _Params(),
                         event_settings=EventTransientSettings(moving_pressure_samples="all"))
    assert every["max_moving_pressure_excl_transient_bar"] == pytest.approx(190.0)


def test_rocking_is_judged_after_the_re_ready() -> None:
    case = _pressure_case()
    t = case["rec"]["t"]
    tilt = np.where((t > 10.0) & (t < 13.5), 0.002 * np.sin(2 * np.pi * 1.2 * t), 0.0)
    case["rec"]["body_quat_wxyz"] = np.column_stack(
        [np.cos(tilt / 2), np.sin(tilt / 2), np.zeros_like(t), np.zeros_like(t)])
    metrics = case_metrics(case, _Params())
    rows = judge([metrics], {})
    assert _row(rows, "5a rocking amplitude after the re-READY")["value"] == pytest.approx(0.0)
    report = _row(rows, "5a rocking amplitude in the event transient (report)")
    assert report["passed"] is None and report["value"] > 0.06


def test_non_event_case_keeps_the_former_item4_rows() -> None:
    case = _pressure_case()
    case["result"]["settings"]["event"] = None
    metrics = case_metrics(case, _Params())
    rows = judge([metrics], {})
    assert _row(rows, "4 max moving pressure")["value"] == pytest.approx(190.0)


# --- J-1 -------------------------------------------------------------------------------------


def _probe_result(leg, start, first, second, estimate_N=50e3, grounded=True):
    return {"leg_index": leg, "is_grounded": grounded, "load_estimate_N": estimate_N,
            "seal_friction_estimate_N": 0.0, "attitude_response_ratio": 1.0,
            "is_skipped": False, "t_move_start_s": start, "t_first_hold_end_s": first,
            "t_second_hold_end_s": second}


def test_probe_truth_is_per_round_and_leg_and_split_by_the_event() -> None:
    """U53: round 1 before the drop (all grounded), round 2 after; the old single window
    called RR 'lifted' because it spanned the event."""
    round1 = [_probe_result(leg, 6.0 + leg, 6.5 + leg, 6.9 + leg) for leg in range(4)]
    round2 = [_probe_result(leg, 20.0 + leg, 20.5 + leg, 20.9 + leg) for leg in range(4)]
    phases = [[0.0, "touch"], [2.0, "level"], [5.0, "probe"], [10.0, "ready"],
              [10.02, "level"], [19.0, "probe"], [25.0, "ready"]]
    intervals = [{"t_start_s": 5.0, "t_end_s": 10.0, "rounds_completed": 1},
                 {"t_start_s": 19.0, "t_end_s": 25.0, "rounds_completed": 1}]
    case = _case(t_event=9.95, rr_lift=(10.0, 11.0), phases=phases, probes=[round1, round2],
                 probe_intervals=intervals)
    case["pads"]["F_cyl"][:, 3] = np.where(case["pads"]["t"] < 15.0, 60e3, 40e3)
    pr = probe_metrics(case)
    assert {r["event_class"] for r in pr["legs"]} == {"pre", "post"}
    assert pr["verdict_match"] is True
    rr_rows = [r for r in pr["legs"] if r["leg"] == "RR"]
    assert [r["truth_cyl_kN"] for r in rr_rows] == pytest.approx([60.0, 40.0])
    assert rr_rows[0]["timing_source"] == "controller (J-0)"


def _single_probe_case(estimate_N, allowance_N=0.0, events=()):
    """FL probe 6.0 / 6.5 / 6.9 s: true force 50 kN before the move, 56 kN at the first hold
    end, 50 kN at the second (midpoint 53 kN = start + S d / 2)."""
    probe = [_probe_result(0, 6.0, 6.5, 6.9, estimate_N=estimate_N)]
    phases = [[0.0, "touch"], [2.0, "level"], [5.0, "probe"], [9.0, "ready"]]
    t_pad = np.arange(0.0, 20.0 + 1e-9, PAD_S)
    force = np.full((len(t_pad), 4), 50e3)
    force[(t_pad > 6.3) & (t_pad < 6.7), 0] = 56e3
    case = _case(event=None, end_s=20.0, phases=phases, probes=[probe], f_cyl_pad=force)
    case["result"]["controller_meta"]["zero_calibration"] = {
        "is_active": True,
        "result": {"legs": {"FL": {"allowance_N": allowance_N}}}}
    case["events"] = [f"C2Event(t_s=1.0, name='{name}')" for name in events]
    return case


def test_probe_load_truth_is_the_start_load() -> None:
    """Spec rev. 27 102.1: truth = 0.5 s mean before the move (50 kN), midpoint recorded."""
    pr = probe_metrics(_single_probe_case(estimate_N=50e3))
    leg = pr["legs"][0]
    assert leg["truth_cyl_kN"] == pytest.approx(50.0)
    assert leg["truth_midpoint_kN"] == pytest.approx(53.0)
    assert pr["load_error_margin_kN"] == pytest.approx(-5.0)


def test_deduction_leg_is_judged_on_the_dangerous_side_only() -> None:
    """Spec rev. 27 102.1 / 103.3: 18 kN low passes one-sided, 6 kN high fails; the leg's
    calibration warning event is a judged row."""
    low = probe_metrics(_single_probe_case(
        estimate_N=32e3, allowance_N=5500.0, events=["WARN_PRESSURE_ZERO_IMPLAUSIBLE:FL"]))
    assert low["load_error_margin_kN"] == pytest.approx(-23.0)
    rows = judge([_base_metrics("PS7")], {"PS7": low})
    assert _row(rows, "7c load estimate error")["passed"] is True
    assert _row(rows, "7c zero-calibration deduction legs: warning event")["passed"] is True
    high = probe_metrics(_single_probe_case(estimate_N=56e3, allowance_N=5500.0))
    assert high["load_error_margin_kN"] == pytest.approx(1.0)
    assert high["zero_cal_deduction_warning_event"] == {"FL": False}
    plain = probe_metrics(_single_probe_case(estimate_N=32e3))
    assert plain["load_error_margin_kN"] == pytest.approx(13.0)


def test_probe_round_overlapping_the_event_is_reported_only() -> None:
    round1 = [_probe_result(leg, 9.0 + leg, 9.5 + leg, 9.9 + leg) for leg in range(4)]
    phases = [[0.0, "touch"], [2.0, "level"], [8.9, "probe"], [13.0, "ready"]]
    case = _case(t_event=10.0, rr_lift=(10.05, 12.5), phases=phases, probes=[round1],
                 fl_lift=(30.0, 30.0))
    pr = probe_metrics(case)
    assert {r["event_class"] for r in pr["legs"]} == {"overlap"}
    assert "verdict_match" not in pr and pr["overlap_verdict_match"] is False
    rows = judge([_base_metrics("RE1bP", "RE1b")], {"RE1bP": pr})
    assert _row(rows, "7b verdict = truth (event overlap)")["kind"] == "info"
    assert all(r["item"] != "7b verdict = truth" for r in rows)


def test_probe_times_are_rebuilt_from_the_record_commands() -> None:
    """Batches before J-0: each move = a run of same-sign commands, hold end = last command +
    period + hold_s."""
    t = np.arange(0.0, 30.0 + 1e-9, PERIOD_S)
    commands = np.zeros((len(t), 4))
    commands[(t >= 6.0) & (t < 6.9), 0] = 0.002
    commands[(t >= 7.3) & (t < 8.2), 0] = -0.002
    old = {k: v for k, v in _probe_result(0, 0, 0, 0).items() if not k.startswith("t_")}
    phases = [[0.0, "touch"], [2.0, "level"], [5.0, "probe"], [9.0, "ready"]]
    case = _case(event=None, phases=phases, probes=[[old]], u_cmd=commands)
    leg = probe_metrics(case)["legs"][0]
    assert leg["timing_source"] == "record u_cmd (rebuilt)"
    assert leg["probe_times_s"] == pytest.approx([6.0, 6.88 + 0.42, 8.18 + 0.42])
    assert leg["event_class"] is None


def test_anchor_judged_on_the_net_move_at_the_window_end() -> None:
    """Spec 62.2 (rev. 12): a 6 mm excursion that comes back to 1 mm by the window end passes;
    the excursion and the path are reported."""
    case = _case()
    tp = case["pads"]["t"]
    case["pads"]["anchor_world"][(tp >= 10.5) & (tp < 11.0), 0, 0] = 0.006
    case["pads"]["anchor_world"][tp >= 11.0, 0, 0] = 0.001
    rows, event3 = _event_rows(case)
    assert event3["other_slip_net_window_end_m"][0] == pytest.approx(0.001)
    assert event3["other_slip_max_excursion_m"][0] == pytest.approx(0.006)
    assert event3["other_slip_path_total_m"][0] == pytest.approx(0.011)
    assert _row(rows, "3 lift-off other legs in the event transient")["passed"] is True


def test_item4_uses_the_per_leg_head_area() -> None:
    """Spec 64.2: item 4 divides by the run's own per-leg head areas (REXOME35 front / rear when
    the YAML has them), else the 115 mm area."""
    from outrigger_sim.verify.s6_control import _head_areas_m2

    class _Rexome35(_Params):
        def get(self, key):
            areas = {"FL": 1.3273e-2, "FR": 1.3273e-2, "RL": 9.5033e-3, "RR": 9.5033e-3}
            for leg, area in areas.items():
                if key == f"legs.{leg}.cylinder.head_area_m2":
                    return area
            if key == "actuator.bore_diameter_m":
                return 0.115
            return super().get(key)

    np.testing.assert_allclose(_head_areas_m2(_Rexome35()), [1.3273e-2] * 2 + [9.5033e-3] * 2)
    np.testing.assert_allclose(_head_areas_m2(_Params()), np.pi / 4 * 0.115**2)
