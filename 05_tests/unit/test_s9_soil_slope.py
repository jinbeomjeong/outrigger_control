"""Study 1 soft soil x floor slope screen (``04_scripts/03_control/s9/s9_soil_slope.py``): the case
set H1..H5 (177), the run_case arguments, the settle-correction hook table, the judgement rows on
synthetic records, the k* table and the affinity argument. No harness run (numba not needed)."""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import s9_soil_slope as ss  # noqa: E402

F_MIN_KN = 9.415
PAD_XY = [[2.0, 1.5], [2.0, -1.5], [-2.0, 1.5], [-2.0, -1.5]]


# ------------------------------------------------------------------------------------ cases
def test_case_counts_and_ids() -> None:
    cases = ss.build_cases()
    assert len(cases) == 177
    assert Counter(c.group for c in cases) == ss.GROUP_SIZES
    ids = [c.case_id for c in cases]
    assert len(set(ids)) == len(ids)
    assert all(c.reanchor == (c.group == "H4") for c in cases)


def test_group_contents() -> None:
    by_group: dict[str, list] = {}
    for case in ss.build_cases():
        by_group.setdefault(case.group, []).append(case)
    assert {(c.soil, c.pad, c.level) for c in by_group["H2"]} == {
        (s, "B", "bottom") for s in ss.SOILS}
    assert {c.soil for c in by_group["H5"]} == {"rigid"}
    assert len({c.slope_name for c in by_group["H1"]}) == 8
    assert {c.soil for c in by_group["H3"]} == {"J1", "J2", "S1"}
    h4 = {(c.soil, c.pad, c.roll_deg, c.pitch_deg) for c in by_group["H4"]}
    assert ("rigid", "B", 0.0, 3.2) in h4 and ("rigid", "B", 0.0, 2.8) in h4
    assert ("J1", "B", 0.0, -3.2) in h4 and ("rigid", "A", 0.0, 3.2) not in h4


def test_boundary_slopes_are_scaled() -> None:
    cases = {c.case_id: c for c in ss.build_cases(("H3",))}
    edge = cases["H3|S1|A|top|edge_nd@k0.875"]
    assert (edge.roll_deg, edge.pitch_deg) == (1.925, 1.4)
    assert (edge.direction, edge.k) == ("edge_nd", 0.875)
    nose = cases["H3|J1|B|top|nose_down@k0.5"]
    assert (nose.roll_deg, nose.pitch_deg) == (0.0, 1.6)
    assert nose.settle_key == "J1|B|top|0,1.6"


def test_unknown_group_raises() -> None:
    with pytest.raises(ValueError, match="unknown case groups"):
        ss.build_cases(("H9",))


def test_run_case_input() -> None:
    case = next(c for c in ss.build_cases(("H4",)) if c.soil == "G1").to_dict()
    arg = ss.run_case_input(case)
    assert arg == {"id": "H4|G1|B|top|nose_down", "soil": "G1", "pad": "B", "level": "top",
                   "fs_kN": 4.0, "slope": (0.0, 3.2), "variant": {"reanchor": True},
                   "trace": False}


def test_settle_corrections_attach() -> None:
    cases = ss.build_cases(("H1", "H5"))
    table = {"J1|B|top|0,3.2": {"dz_m": 0.004, "droll_deg": 0.0, "dpitch_deg": 0.15}}
    out = ss.attach_settle_corrections(cases, table)
    hit = [c for c in out if c.settle is not None]
    assert [c.case_id for c in hit] == ["H1|J1|B|top|nose_down"]
    assert hit[0].to_dict()["settle"] == {"dz_m": 0.004, "droll_deg": 0.0, "dpitch_deg": 0.15}
    with pytest.raises(ValueError, match="unknown cases"):
        ss.attach_settle_corrections(cases, {"X|B|top|0,0": {"dz_m": 0.0}})
    with pytest.raises(ValueError, match="rigid floor"):
        ss.attach_settle_corrections(cases, {"rigid|B|top|0,3.2": {"dz_m": 0.001}})


def _table_row(pitch_add: float = -0.036) -> dict:
    return {"floor_roll_add_deg": 0.0, "floor_pitch_add_deg": pitch_add,
            "pad_h_m": [0.0006, 0.0006, 0.0037, 0.0036],
            "target_q_floor": [-0.0012, 2.0e-6, 0.0025],
            "gap_target_mm": [340.2, 340.2, 342.0, 342.0], "harness_settle_pitch_pp_deg": 0.0004,
            "residual_pitch_deg": 0.0}


def test_settle_table_attach() -> None:
    cases = ss.build_cases(("H1", "H3", "H5"))
    rows = {"J1|top|0|3.2": _table_row(), "J1|top|0|0": _table_row(0.0)}
    out = {c.case_id: c for c in ss.attach_settle_table(cases, rows)}
    hit = out["H1|J1|A|top|nose_down"]  # no pad in the key: A and B share the row
    assert hit.settle_table_status == "applied" and hit.harness_settle_key == "J1|top|0|3.2"
    assert hit.settle_table.pad_h_m == (0.0006, 0.0006, 0.0037, 0.0036)
    assert hit.to_dict()["settle_table"]["floor_pitch_add_deg"] == -0.036
    assert out["H1|J1|B|top|flat"].settle_table_status == "applied"
    assert out["H3|J1|B|top|nose_down@k0.5"].settle_table_status == "no_table_row"
    assert out["H5|rigid|B|top|flat"].settle_table_status == "rigid_reference"
    assert out["H5|rigid|B|top|flat"].settle_table is None


def test_settle_table_rules() -> None:
    cases = ss.build_cases(("H5",))
    zero = {"floor_roll_add_deg": 0.0, "floor_pitch_add_deg": 0.0, "pad_h_m": [0, 0, 0, 0],
            "target_q_floor": [0, 0, 0], "gap_target_mm": [0, 0, 0, 0]}
    assert all(c.settle_table_status == "rigid_reference"
               for c in ss.attach_settle_table(cases, {"rigid|top|0|0": zero}))
    with pytest.raises(ValueError, match="non-zero rigid row"):
        ss.attach_settle_table(cases, {"rigid|top|0|0": _table_row()})
    corrected = ss.attach_settle_corrections(ss.build_cases(("H1",)),
                                             {"J1|B|top|0,0": {"dz_m": 0.001}})
    with pytest.raises(ValueError, match="both given"):
        ss.attach_settle_table(corrected, {})


def test_settle_check() -> None:
    target, gap = [-0.0012, 2.0e-6, 0.0025], [340.2, 340.2, 342.0, 342.0]
    ok = ss.settle_check(target, gap, [2.0e-6, 0.0025], [-340.0, -340.5, -342.9, -341.2])
    assert ok["ok"] is True
    gap_miss = ss.settle_check(target, gap, [2.0e-6, 0.0025], [-338.9, -340.2, -342.0, -342.0])
    assert gap_miss["ok"] is False and gap_miss["gap_ok"] is False
    tilt = 0.0025 + math.radians(0.006)
    att_miss = ss.settle_check(target, gap, [2.0e-6, tilt], [-340.2, -340.2, -342.0, -342.0])
    assert att_miss["attitude_ok"] is False and att_miss["attitude_error_deg"][1] == \
        pytest.approx(0.006)


def test_settle_window_mean() -> None:
    log = {"t_s": [0.1 * (i + 1) for i in range(80)],
           "q_floor_deg": [[0.0, 0.14 + (0.04 if i % 2 else -0.04)] for i in range(80)]}
    q_mean, t_end = ss.settle_window_attitude_rad(log, [6.0, 6.0, 7.0, None])
    assert t_end == pytest.approx(5.0) and math.degrees(q_mean[1]) == pytest.approx(0.14)
    _, t_cut = ss.settle_window_attitude_rad(log, [3.0, None, None, None])
    assert t_cut == pytest.approx(3.0)


def test_floor_axes_attitude() -> None:
    roll, pitch, d_phi, d_theta = 2.2, 1.6, 1e-3, 2e-3

    def rot_y(a: float) -> np.ndarray:
        return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])

    def rot_x(a: float) -> np.ndarray:
        return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])

    floor = rot_y(math.radians(pitch)) @ rot_x(math.radians(roll))
    body = floor @ rot_y(d_theta) @ rot_x(d_phi)
    phi, theta = ss.floor_axes_attitude_rad(body, roll, pitch)
    assert (phi, theta) == (pytest.approx(d_phi), pytest.approx(d_theta))


def test_settle_check_fail_verdict_and_first_contact() -> None:
    rec = _record()
    rec["settle"] = {**rec["settle"], "check": {"ok": False}}
    out = ss.judge_case(rec)
    assert out["verdict"] == ss.VERDICT_SETTLE_CHECK_FAIL and out["verdict_rows"] == "pass"
    log = {"t_s": [0.1, 0.2, 0.3], "fmin_kN": [[-1.0, -1.0, -1.0, -1.0], [0.5, -1.0, -1.0, -1.0],
                                                 [0.5, -0.5, -1.0, -1.0]]}
    assert ss.first_contact_times(log, [1.0] * 4) == [0.2, 0.3, None, None]


# ------------------------------------------------------------------------------- judgement
def _record(**over) -> dict:
    """Synthetic run record of a passing soil run (t 0..60 s at 10 Hz)."""
    n = 600
    t = [round(0.1 * (i + 1), 1) for i in range(n)]
    phase = ["touch"] * 50 + ["level"] * 250 + ["done"] * 50 + ["ready"] * 250
    case = next(c for c in ss.build_cases(("H1",))
                if c.case_id == "H1|J1|B|top|nose_down").to_dict()
    rec = {
        "case": case, "F_min_kN": F_MIN_KN, "rod_weight_kN": [1.0] * 4,
        "run": {"t_level_s": 5.1, "t_done_s": 30.0, "t_ready_s": 35.0, "final_phase": "ready",
                "t_crawler_off_first_s": 20.0, "n_crawler_recontact": 0,
                "crawler_N_max_after_ready": 0.0, "clear_true_ready_mm": 60.0,
                "min_true_Fcyl_after_off_kN": 40.0, "att_end_deg": [0.01, -0.02],
                "max_motor_stroke_mm": 650.0, "sink_final_mm": [70.0, 60.0, 90.0, 80.0]},
        "events": [(21.0, "crawler_liftoff_confirmed")],
        "log": {"t_s": t, "phase": phase, "fmin_kN": [[40.0] * 4] * n,
                "rut_clear_mm": [30.0] * n, "clear_est_mm": [20.0] * n, "sink_mm": None},
        "settle": {"att_true_deg": [0.0, 3.0], "att_ctrl_deg": [0.0, 3.0],
                   "anchor_pitch_deg": None},
        "soil_state": {"t_P_s": 20.5, "c_min_tP_mm": 21.0, "corner_bias_mm": [0, 0, 0, 0],
                       "anchor_applied": False},
        "rut_end_mm": 61.0, "pad_xy": PAD_XY,
    }
    for key, value in over.items():
        rec[key] = value
    return rec


def test_passing_record() -> None:
    out = ss.judge_case(_record())
    assert out["verdict"] == ss.VERDICT_PASS and out["failed_rows"] == []
    rows = out["rows"]
    assert rows["P3-2"]["loc_delay_s"] == pytest.approx(1.0)
    assert rows["P3-6"]["limit_s"] == 120.0 and rows["P3-6"]["flag"] is False
    assert rows["SL-1"]["k_minus_prediction"] == pytest.approx(1.0 - 0.84)
    assert rows["SL-2"]["R_c"] == pytest.approx(3.0 / 3.2) and rows["SL-2"]["flag"] is False
    assert "RA-1" not in rows


def test_start_condition_flag_and_plant_fallback() -> None:
    rec = _record(settle={"att_true_deg": [2.2, 1.7], "att_ctrl_deg": None,
                          "anchor_pitch_deg": None})
    row = ss.start_condition_row(rec)
    assert row["source"] == "plant" and row["flag"] is True
    assert row["R_c"] == pytest.approx(0.5 + 1.7 / 3.2)


def _stroke_limited_record(**run_over) -> dict:
    """Stroke-guarded run whose rut clearance at READY is short (P3-5 fails, the relaxed row)."""
    events = [(21.0, "crawler_liftoff_confirmed"), (25.0, "WARN_LIFT_STROKE_LIMITED:FR")]
    rec = _record(events=events)
    rec["run"] = {**rec["run"], "clear_true_ready_mm": 20.0, **run_over}
    return rec


def test_stroke_limited_class() -> None:
    out = ss.judge_case(_stroke_limited_record())
    assert out["verdict"] == ss.VERDICT_STROKE_LIMITED_PASS
    assert out["failed_rows"] == ["P3-5"]  # recorded, relaxed by the stroke-limit class
    failing = {"P3-1": {"n_crawler_recontact": 1}, "P3-3": {"min_true_Fcyl_after_off_kN": 5.0},
               "P3-4": {"att_end_deg": [0.5, 0.0]}}
    for row, over in failing.items():
        out = ss.judge_case(_stroke_limited_record(**over))
        assert out["verdict"] == ss.VERDICT_STROKE_LIMITED_FAIL, row
        assert row in out["failed_rows"]


def test_rejudge_stored_result() -> None:
    stored = {"id": "x", "verdict": ss.VERDICT_STROKE_LIMITED_PASS, "settle": {"check": None},
              **ss.judge_case(_stroke_limited_record(n_crawler_recontact=1))}
    stored["verdict"] = ss.VERDICT_STROKE_LIMITED_PASS  # as written by the first rule
    stored["rows"]["SL-1"]["stroke_limited_pass"] = True
    out = ss.rejudge_stored(stored)
    assert out["verdict"] == ss.VERDICT_STROKE_LIMITED_FAIL
    assert out["verdict_stored"] == ss.VERDICT_STROKE_LIMITED_PASS
    assert out["rows"]["SL-1"]["stroke_limited_pass"] is False
    assert stored["rows"]["SL-1"]["stroke_limited_pass"] is True  # input left unchanged
    assert out["rut_definition"] == ss.RUT_DEFINITION_OLD


def test_stroke_fault_fails_and_leg_lift_counts() -> None:
    events = [(21.0, "crawler_liftoff_confirmed"), (25.0, "WARN_LIFT_STROKE_LIMITED:FR"),
              (28.0, "FAULT_LIFT_STROKE_LIMIT:FR")]
    rec = _record(events=events)
    rec["run"] = {**rec["run"], "final_phase": "fault"}
    assert ss.judge_case(rec)["verdict"] == ss.VERDICT_FAIL
    lifted = _record()
    fmin = [list(row) for row in lifted["log"]["fmin_kN"]]
    fmin[100][2] = -1.5  # pad contact = -1.5 + 1.0 kN < 0 in LEVEL
    lifted["log"] = {**lifted["log"], "fmin_kN": fmin}
    assert ss.stroke_row(lifted)["lifted_legs"] == ["RL"]


def test_preloc_reapproach_demotion() -> None:
    events = [(15.0, "leg_reapproach_start:RL"), (21.0, "crawler_liftoff_confirmed")]
    out = ss.judge_case(_record(events=events))
    assert out["rows"]["P3-8"]["pass"] is True and out["rows"]["P3-8"]["flag"] is True
    rec = _record(events=events)
    fmin = [list(row) for row in rec["log"]["fmin_kN"]]
    fmin[160][2] = 5.0  # t 16.1 s, RL below F_min before LOC + 1 s
    rec["log"] = {**rec["log"], "fmin_kN": fmin}
    row = ss.judge_case(rec)["rows"]["P3-8"]
    assert row["pass"] is False and row["starts"][0]["true_min_kN"] == 5.0


def test_clearance_row_under_lift_flag() -> None:
    rec = _record()
    est = [20.0] * 600
    est[210] = 45.0  # row after the LOC at t 21.0 (index 209)
    rec["log"] = {**rec["log"], "clear_est_mm": est}
    row = ss.clearance_row(rec)
    assert row["true_at_loc_mm"] == 30.0 and row["estimate_after_loc_mm"] == 45.0
    assert row["true_minus_estimate_mm"] == -15.0 and row["flag"] is False
    est[210] = 51.0
    assert ss.clearance_row(rec)["flag"] is True


def test_downhill_minus_uphill() -> None:
    sink = [70.0, 60.0, 90.0, 80.0]
    assert ss.downhill_minus_uphill(sink, PAD_XY, 0.0, 3.2) == pytest.approx(65.0 - 85.0)
    assert ss.downhill_minus_uphill(sink, PAD_XY, 4.4, 0.0) == pytest.approx(70.0 - 80.0)
    assert ss.downhill_minus_uphill(sink, PAD_XY, 0.0, 0.0) is None


def test_reanchor_rows() -> None:
    case = next(c for c in ss.build_cases(("H4",)) if c.soil == "J1").to_dict()
    phase = ["touch"] * 50 + ["level"] * 250 + ["done"] * 20 + ["reanchor"] * 100 + \
        ["level"] * 30 + ["ready"] * 150
    sink = [[10.0, 10.0, 10.0, 10.0]] * 330 + [[11.5, 11.0, 12.0, 12.0]] * 270
    events = [(21.0, "crawler_liftoff_confirmed"), (32.1, "reanchor_started"),
              (40.0, "reanchor_aborted:stroke_cap"), (42.1, "reanchor_completed")]
    rec = _record(case=case, events=events)
    rec["log"] = {**rec["log"], "phase": phase, "sink_mm": sink}
    rec["settle"] = {**rec["settle"], "anchor_pitch_deg": 3.3}
    rows = ss.reanchor_rows(rec)
    assert rows["RA-1"]["pass"] is True and rows["RA-1"]["completed"] is True
    assert rows["RA-2"]["pass"] is True and rows["RA-2"]["window_s"][1] == pytest.approx(42.2)
    assert rows["RA-4"]["sink_increase_mm"] == {"FL": pytest.approx(1.5),
                                                "FR": pytest.approx(1.0)}
    assert rows["RA-6"]["n_stroke_cap_aborts"] == 1
    rec["settle"] = {**rec["settle"], "anchor_pitch_deg": 2.0}
    assert ss.reanchor_rows(rec)["RA-1"]["pass"] is False
    low = [list(r) for r in rec["log"]["fmin_kN"]]
    low[350][0] = F_MIN_KN + 4.0
    rec["log"] = {**rec["log"], "fmin_kN": low}
    assert ss.reanchor_rows(rec)["RA-2"]["pass"] is False


# --------------------------------------------------------------------------------- summary
def _result(case, verdict: str, stroke_mm: float, guarded: bool = False) -> dict:
    return {"case": case.to_dict(), "verdict": verdict,
            "rows": {"SL-1": {"guard_warning": guarded, "max_motor_stroke_mm": stroke_mm}}}


def test_k_star_table() -> None:
    cases = {c.case_id: c for c in ss.build_cases(("H1", "H3"))}
    points = [("H1|J1|B|top|flat", ss.VERDICT_PASS, 600.0, False),
              ("H3|J1|B|top|nose_down@k0.5", ss.VERDICT_PASS, 640.0, False),
              ("H3|J1|B|top|nose_down@k0.75", ss.VERDICT_PASS, 670.0, False),
              ("H3|J1|B|top|nose_down@k0.875", ss.VERDICT_STROKE_LIMITED_PASS, 684.0, True),
              ("H1|J1|B|top|nose_down", ss.VERDICT_PASS, 681.0, False)]
    results = [_result(cases[key], v, s, g) for key, v, s, g in points]
    row = next(r for r in ss.k_star_rows(results) if r["direction"] == "nose_down")
    assert row["is_complete"] is True and row["k_star"] == 0.75
    assert row["k_stroke_interp"] == pytest.approx(0.75 + 0.125 * 12.8 / 14.0)
    assert row["k_star_minus_prediction"] == pytest.approx(0.75 - 0.84)
    partial = ss.k_star_rows(results[1:])
    assert next(r for r in partial if r["direction"] == "nose_down")["k_star"] is None


# ------------------------------------------------------------------------------ placement
def test_parse_affinity() -> None:
    assert ss.parse_affinity("ecore") == 0x0FFF0000
    assert ss.parse_affinity("PCORE") == 0x0000FFFF
    assert ss.parse_affinity("0x0FFF0000") == 0x0FFF0000
    assert ss.parse_affinity(None) is None and ss.parse_affinity("os") is None
    with pytest.raises(ValueError):
        ss.parse_affinity("fast")
