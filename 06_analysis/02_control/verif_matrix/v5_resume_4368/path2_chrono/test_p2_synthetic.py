"""Synthetic-input self tests for the path 2 Chrono tool (no real results are read).

Run: conda run -n dynamics-dev python -I -B test_p2_synthetic.py [--tmp <empty dir>]
Exit 0 = all pass, 1 = a test failed. Last line: JSON summary.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import p2_chrono  # noqa: E402
import p2_core as C  # noqa: E402
import p2_kinds as K  # noqa: E402
import p2_rules as R  # noqa: E402

W = 380000.0
REPO = p2_chrono.find_repo(HERE)
PARAMS = C.load_params(REPO)
FMIN = PARAMS["F_min_N"]
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append({"test": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))


# ------------------------------------------------------------------ synthetic SCM row
def scm_spec():
    return {"t0": 8.0, "t_end": 60.0, "phases": [(8.1, "check"), (12.0, "touch"), (20.0, "level"),
                                                 (30.0, "done"), (32.0, "ready")],
            "events": [(24.5, C.R.EVENT_LOC)], "crawler": [("ramp", 22.0, 23.0)],
            "recontacts": [(24.0, 24.05, 5000.0)], "dips": [], "att": 0.05, "rut": 0.05,
            "stroke": 0.5, "floor": (2.0, 1.0), "las_start": None, "decisions": [],
            "creep_until": None, "attitude_crawler": [2.0, 1.0]}


def write_scm(folder: Path, sp: dict):
    folder.mkdir(parents=True, exist_ok=True)
    t = np.round(np.arange(sp["t0"] + 0.001, sp["t_end"] + 1e-9, 0.001), 6)
    n = len(t)
    cr = np.full(n, 0.95 * W)
    for kind, a, b in sp["crawler"]:
        cr = np.where(t >= b, 0.0, np.where(t >= a, 0.95 * W * (b - t) / (b - a), cr))
    for a, b, v in sp["recontacts"]:
        cr = np.where((t >= a - 1e-9) & (t <= b + 1e-9), v, cr)
    F = np.full((n, 4), 50000.0)
    for leg, a, b, v in sp["dips"]:
        F[(t >= a) & (t <= b), leg] = v
    att = np.full((n, 2), sp["att"])
    sink = np.zeros((n, 4))
    if sp["creep_until"] is not None:
        sel = t < sp["creep_until"]
        sink[sel] = (t[sel, None] - t[0]) * 1e-3
        sink[~sel] = (sp["creep_until"] - t[0]) * 1e-3
    s_motor = np.full((n, 4), sp["stroke"])
    pad = np.full((n, 4), 60000.0)
    np.savez(folder / "step_series.npz", t_s=t, F_cyl_N=F, s_motor_m=s_motor, roll_pitch_deg=att,
             scm_crawler_normal_N=cr, scm_pad_normal_N=pad, pad_sinkage_geometric_m=sink)
    t10 = np.round(np.arange(sp["t0"] + 0.1, sp["t_end"] + 1e-9, 0.1), 6)
    ph = [""] * len(t10)
    for i, tt in enumerate(t10):
        cur = "check"
        for tp, name in sp["phases"]:
            if tt >= tp - 1e-9:
                cur = name
        ph[i] = cur
    np.savez(folder / "r8_series.npz", t=t10, issued_u=np.zeros((len(t10), 4)), phase=np.array(ph))
    res = {
        "t_loop_start_s": sp["t0"], "phases": [{"t_s": a, "phase": b} for a, b in sp["phases"]],
        "events": [{"t_s": a, "name": b} for a, b in sp["events"]],
        "args": {"floor_roll": sp["floor"][0], "floor_pitch": sp["floor"][1]},
        "p3b": {"weight_N": W}, "mass_scale": {"judgement_weights": {"weight_N": W}},
        "s9_rows": [{"t_s": float(x), "rut_clearance_m": sp["rut"]} for x in t10],
        "c2_soil": {"soil_mode_t_s": None, "mode_starts": []},
        "controller_meta": {"liftoff_approach_slow": {"settings": {}, "start_s": sp["las_start"]},
                            "slope_clearance_margin": {"order_gate": {"enabled": True, "decisions": sp["decisions"]},
                                                       "settings": {"flat_soil_margin_order_gate": True}}},
        "c2_setup": {"k1_order_gate": "preset", "k1_order_gate_effective": True, "expect_controller": {"ok": True}},
        "num_threads_chrono": 4, "placement": {"omp_wait_policy": "PASSIVE"},
        "hull_hook": {"mode": "fast", "fallback_reason": None},
        "v5_hydraulics": {"controller_tag": "final_C4G2_P3_LAS_K1", "hydraulic_options": {"m2_law": "flow_limited_r5"}},
        "hydraulics_record": {"m2_clip_times_s": [[8.3], [8.3], [8.3], [8.3]], "m2_clip_times_complete": True},
        "p3b_ext": {"start_condition": {"crawler_attitude_deg": sp["attitude_crawler"]}},
    }
    (folder / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return folder


def scm_row(tmp, sp, name):
    return C.load_row(write_scm(tmp / name, sp), "scm", ["run_S9.py", "level"])


# ------------------------------------------------------------------ synthetic L2b row
def write_l2b(folder: Path, liftoff=20.0, dip=None, moving_bar=None, end_att=0.05, floor="fdown3.2"):
    folder.mkdir(parents=True, exist_ok=True)
    start = 3.0
    t = np.round(np.arange(start + 0.001, start + 90.0 + 1e-9, 0.001), 6)
    n = len(t)
    cr = np.where(t < start + liftoff, 300000.0, 0.0)
    F = np.full((n, 4), 60000.0)
    if dip is not None:
        leg, a, b, v = dip
        F[(t >= start + a) & (t <= start + b), leg] = v
    Fi = F.copy()
    if moving_bar is not None:
        A = PARAMS["head_area_m2"][0]
        Fi[(t >= start + 40.0) & (t <= start + 40.5), 0] = moving_bar * 1e5 * A
    q = np.zeros((n, 4))
    q[:, 0] = 1.0
    ang = np.radians(end_att)
    q[:, 0] = np.cos(ang / 2)
    q[:, 2] = np.sin(ang / 2)  # pitch about y
    np.savez(folder / "pads.npz", t=t, F_cyl=Fi, F_cyl_min_interval=F, s_motor=np.full((n, 4), 0.4),
             body_quat_wxyz=q, crawler_normal_N=cr, N=np.full((n, 4), 60000.0),
             law_locked=np.zeros((n, 4), dtype=np.int8))
    t10 = np.round(np.arange(start + 0.1, start + 90.0 + 1e-9, 0.1), 6)
    phases = [[0.1, "check"], [5.0, "touch"], [15.0, "level"], [35.0, "done"], [36.0, "ready"]]
    ph = []
    for tt in t10:
        cur = "check"
        for tp, nm in phases:
            if tt - start >= tp - 1e-9:
                cur = nm
        ph.append(cur)
    u = np.zeros((len(t10), 4))
    u[(t10 >= start + 39.9) & (t10 <= start + 40.5), 0] = 0.005
    np.savez(folder / "r8_series.npz", t=t10, issued_u=u, phase=np.array(ph))
    (folder / "record").mkdir(exist_ok=True)
    np.savez(folder / "record" / "record.npz", t=t10, body_quat_wxyz=np.tile([1.0, 0, 0, 0], (len(t10), 1)),
             F_crawler=np.zeros((len(t10), 3)))
    res = {"case": folder.name, "settings": {"start_t_s": start, "floor": floor, "target_deg": [0.0, 0.0]},
           "phases": phases, "controller_tag": "final_C4G2_P3_LAS_K1",
           "expect_controller": {"name": "final_C4G2_P3_LAS_K1", "ok": True},
           "controller_meta": {"liftoff_approach_slow": {"settings": {}},
                               "slope_clearance_margin": {"order_gate": {"enabled": True, "decisions": []},
                                                          "settings": {"flat_soil_margin_order_gate": True}}}}
    (folder / "result.json").write_text(json.dumps(res), encoding="utf-8")
    (folder / "controller_events.json").write_text(json.dumps(
        ["C2Event(t_s=21.0, name='crawler_liftoff_confirmed')"]), encoding="utf-8")
    return folder


L2B_ARGV = ["run_S8C.py", "run", "--tag", "x", "--expect-controller", "final_C4G2_P3_LAS_K1"]


# ------------------------------------------------------------------ tests
def t_classify():
    thr = 0.01 * W
    loc, ready = 30.0, 50.0
    cases = [
        ({"start_s": 30.1, "end_s": 30.17, "duration_s": 0.07, "max_N": 1.06 * thr}, "threshold_chatter"),
        ({"start_s": 30.1, "end_s": 30.21, "duration_s": 0.11, "max_N": 1.06 * thr}, "strict_fail"),
        ({"start_s": 30.1, "end_s": 30.17, "duration_s": 0.07, "max_N": 1.21 * thr}, "strict_fail"),
        ({"start_s": 31.05, "end_s": 31.1, "duration_s": 0.05, "max_N": 1.06 * thr}, "strict_fail"),
        ({"start_s": 29.0, "end_s": 29.3, "duration_s": 0.3, "max_N": 0.1 * W}, "transient_flag"),
        ({"start_s": 29.0, "end_s": 30.2, "duration_s": 1.2, "max_N": 0.1 * W}, "strict_fail"),
        ({"start_s": 50.5, "end_s": 50.52, "duration_s": 0.02, "max_N": 1.0 * thr}, "strict_fail"),
    ]
    for i, (ev, want) in enumerate(cases, 1):
        got = C.classify_recontact(ev, loc, ready, W)
        check(f"423.3 / G6d classify case {i}", got == want, f"{got} != {want}")


def t_scm(tmp):
    sp = scm_spec()
    row = scm_row(tmp, sp, "base")
    items, keys, _ = K.items_p3(row, PARAMS, R.READY_SLOPE_S, True, g6=True)
    tD = items["departure"]["t_D_s"]
    want_tD = 22.0 + (1 - 0.01 / 0.95) * 1.0
    check("t_D = first sample < 0.01 W lasting 0.1 s", tD is not None and abs(tD - want_tD) < 0.0015, tD)
    check("P3-1 transient recontact before LOC -> flag", items["P3-1"]["verdict"] == "flag", items["P3-1"])
    check("P3-2 pass", items["P3-2"]["verdict"] == "pass", items["P3-2"])
    check("P3-3 pass", items["P3-3"]["verdict"] == "pass", items["P3-3"].get("min_all_N"))
    check("P3-4 pass, window from last READY", items["P3-4"]["verdict"] == "pass"
          and abs(items["P3-4"]["window_s"][0] - 32.0) < 1e-9, items["P3-4"])
    check("P3-5 pass", items["P3-5"]["verdict"] == "pass", items["P3-5"])
    check("row 통과", C.row_status(items, keys) == "통과", C.row_status(items, keys))

    sp2 = copy.deepcopy(sp)
    sp2["recontacts"] = [(24.6, 24.65, 4000.0)]
    it2, k2, _ = K.items_p3(scm_row(tmp, sp2, "chatter"), PARAMS, 120.0, True)
    check("P3-1 after-LOC short recontact -> chatter flag", it2["P3-1"]["flags"] == ["P3-1_threshold_chatter"],
          it2["P3-1"])
    sp3 = copy.deepcopy(sp)
    sp3["recontacts"] = [(26.0, 26.2, 5000.0)]
    it3, k3, _ = K.items_p3(scm_row(tmp, sp3, "strict"), PARAMS, 120.0, True)
    check("P3-1 after-LOC long recontact -> fail, row 미달", it3["P3-1"]["verdict"] == "fail"
          and C.row_status(it3, k3) == "미달", it3["P3-1"])

    sp4 = copy.deepcopy(sp)
    sp4["dips"] = [(2, 25.0, 25.1995, 9000.0)]
    it4, _, _ = K.items_p3(scm_row(tmp, sp4, "dip"), PARAMS, 120.0, True)
    p33 = it4["P3-3"]
    check("P3-3 dip -> fail, min RL 9000", p33["verdict"] == "fail" and p33["min_leg"] == "RL"
          and abs(p33["min_all_N"] - 9000) < 1e-9, p33.get("min_all_N"))
    check("F<F_min time = 200 samples x 1 ms", abs(p33["t_below_Fmin_s"][2] - 0.2) < 1.5e-3, p33["t_below_Fmin_s"])

    sp5 = copy.deepcopy(sp)
    sp5["events"] = [(26.5, C.R.EVENT_LOC), (23.0, "leg_reapproach_start:RL"), (23.5, "INFO_LOC_WINDOW_RESTART:RL"),
                     (25.0, "leg_reapproach_contact:RL")]
    sp5["recontacts"] = []
    it5, _, _ = K.items_p3(scm_row(tmp, sp5, "late"), PARAMS, 120.0, True)
    check("P3-2 late LOC after reapproach -> 419.8 flag", it5["P3-2"]["verdict"] == "flag"
          and "P3-2_late_loc_reapproach" in it5["P3-2"]["flags"], it5["P3-2"])
    sp6 = copy.deepcopy(sp5)
    sp6["events"] = [(26.5, C.R.EVENT_LOC)]
    it6, _, _ = K.items_p3(scm_row(tmp, sp6, "late2"), PARAMS, 120.0, True)
    check("P3-2 late LOC without reapproach -> fail", it6["P3-2"]["verdict"] == "fail", it6["P3-2"])
    sp7 = copy.deepcopy(sp)
    sp7["events"] = [(24.5, C.R.EVENT_LOC), (25.0, "INFO_LOC_REVOKED"), (27.0, C.R.EVENT_LOC)]
    sp7["recontacts"] = []
    it7, _, _ = K.items_p3(scm_row(tmp, sp7, "revoke"), PARAMS, 120.0, True)
    check("final LOC = last non-revoked; 424.8.1 revoked-LOC flag", it7["P3-2"]["t_loc_final_s"] == 27.0
          and "P3-2_late_loc_revoked" in it7["P3-2"].get("flags", []), it7["P3-2"])
    check("revoked LOC under load recorded only (Q-17)", it7["P3-2"]["revoked_loc_under_load_record_s"] == [],
          it7["P3-2"]["revoked_loc_under_load_record_s"])
    sp7b = copy.deepcopy(sp7)
    sp7b["events"] = [(24.5, C.R.EVENT_LOC), (25.0, "INFO_LOC_REVOKED"), (30.5, C.R.EVENT_LOC)]
    sp7b["phases"] = [(8.1, "check"), (12.0, "touch"), (20.0, "level"), (31.0, "done"), (32.0, "ready")]
    it7b, _, _ = K.items_p3(scm_row(tmp, sp7b, "revoke6"), PARAMS, 120.0, True)
    check("condition 6: delay 7.5 s > 2 T_lim -> revoked flag refused, P3-2 fail (rev3 R3-G12)",
          it7b["P3-2"]["verdict"] == "fail" and it7b["P3-2"]["late_loc_revoked"]["c6_total_delay_ok"] is False,
          it7b["P3-2"])

    sp8 = copy.deepcopy(sp)
    sp8["phases"] = sp["phases"][:-1] + [(57.0, "ready")]
    it8, k8, _ = K.items_p3(scm_row(tmp, sp8, "short"), PARAMS, 120.0, True)
    check("P3-4 window < 5 s -> window_short FLAG, row not failed (rev3 R3-G7)",
          "window_short" in it8["P3-4"].get("flags", []) and it8["P3-4"]["verdict"] == "flag"
          and C.row_status({"P3-4": it8["P3-4"]}, ["P3-4"]) == "통과", it8["P3-4"])
    sp9 = copy.deepcopy(sp)
    sp9["creep_until"] = 40.0
    it9, _, _ = K.items_p3(scm_row(tmp, sp9, "creep"), PARAMS, 120.0, True)
    # creep 1 mm/s until 40 s; the 1.0 s backward rate drops below 0.1 mm/s once less than 0.1 s
    # of creep remains in the window: t > 40.9 s
    check("P3-4 two-sided creep stop with the 1.0 s backward rate (433.6)",
          abs(it9["P3-4"]["t_final_two_sided_s"] - 40.901) < 0.0015, it9["P3-4"]["t_final_two_sided_s"])
    sp10 = copy.deepcopy(sp)
    sp10["rut"] = 0.02
    it10, _, _ = K.items_p3(scm_row(tmp, sp10, "rut"), PARAMS, 120.0, True)
    check("P3-5 clearance 20 mm -> fail", it10["P3-5"]["verdict"] == "fail", it10["P3-5"])
    sp11 = copy.deepcopy(sp)
    sp11["events"] = [(24.5, C.R.EVENT_LOC), (21.0, "leg_reapproach_start:FL"), (21.5, "leg_reapproach_contact:FL")]
    sp11["recontacts"] = []
    it11, _, _ = K.items_p3(scm_row(tmp, sp11, "p38"), PARAMS, 120.0, True, g6=True)
    check("P3-8 pre-LOC reapproach with min >= F_min -> 377 demoted flag", it11["P3-8"]["verdict"] == "flag",
          it11["P3-8"])
    sp11c = copy.deepcopy(sp11)
    sp11c["dips"] = [(0, 21.2, 21.3, FMIN + 100.0)]
    it11c, _, _ = K.items_p3(scm_row(tmp, sp11c, "p38c"), PARAMS, 120.0, True, g6=True)
    check("377 threshold is F_min (F_min + 100 N demotes, rev3 R3-G8)", it11c["P3-8"]["verdict"] == "flag",
          it11c["P3-8"])
    it11b, _, _ = K.items_p3(scm_row(tmp, sp11, "p38b"), PARAMS, 120.0, True, g6=False)
    check("P3-8 without G6 demotion -> fail", it11b["P3-8"]["verdict"] == "fail", it11b["P3-8"])

    sp12 = copy.deepcopy(sp)
    sp12["decisions"] = [{"would_block": True, "r4_due_without_gate": False, "applied": False}]
    k12 = C.k1_classification(scm_row(tmp, sp12, "k1c"))
    check("K1 would_block & not due -> S-5 (rev2 R2-1)", k12.get("stop") == "S-5", k12)
    sp13 = copy.deepcopy(sp)
    sp13["decisions"] = [{"would_block": True, "r4_due_without_gate": True, "applied": False}]
    sp13["events"] = sp["events"] + [(24.6, "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order")]
    k13 = C.k1_classification(scm_row(tmp, sp13, "k1b"))
    check("K1 block with one _SKIPPED:order -> k1_block", k13.get("cls") == "k1_block", k13)
    sp14 = copy.deepcopy(sp)
    sp14["las_start"] = 23.0
    k14 = C.k1_classification(scm_row(tmp, sp14, "las"))
    check("LAS-b start_s number -> las_active (rev2 R2-2)", k14.get("cls") == "las_active", k14)
    k15 = C.k1_classification(row)
    check("start_s None & no block -> inactive", k15.get("cls") == "inactive", k15)

    # C-8 treatment (7.4)
    if not (HERE / "p2_b_c8.py").exists():
        print("SKIP C-8 tests (p2_b_c8.py not in this commit)")
        return
    import p2_b_c8 as B8
    sp16 = copy.deepcopy(sp)
    sp16["attitude_crawler"] = [2.0, 0.9]
    sp16["dips"] = [(2, 25.0, 25.1, FMIN + 1000.0)]
    it16, _, _, _ = B8.judge_row(scm_row(tmp, sp16, "oc5"), {}, "OC5", PARAMS)
    rc_want = 2.0 / 4.4 + 0.9 / 3.2
    check("C-8 R_c from crawler attitude", abs(it16["R_c"]["R_c"] - rc_want) < 1e-12, it16["R_c"])
    check("C-8 m in [F_min, F_min+2 kN) -> margin record", it16["m_7_4"]["treatment"] == "margin record", it16["m_7_4"])
    sp17 = copy.deepcopy(sp16)
    sp17["dips"] = [(2, 25.0, 25.1, FMIN - 1.0)]
    it17, _, _, _ = B8.judge_row(scm_row(tmp, sp17, "oc5b"), {}, "OC5", PARAMS)
    check("C-8 m < F_min -> S-9", it17["m_7_4"].get("stop") == "S-9", it17["m_7_4"])

    # C-5 (rev4 R4-A2)
    hr = K.items_c5(row, PARAMS)[0]
    check("C-5 H-9 clips before t_lift only -> pass; SCM T4 -> na",
          hr["H-9"]["verdict"] == "pass" and hr["T4"]["verdict"] == "na", hr["H-9"])
    sp18 = copy.deepcopy(sp)
    d18 = write_scm(tmp / "c5rec", sp18)
    res = json.loads((d18 / "result.json").read_text(encoding="utf-8"))
    res["controller_meta"]["two_pressure"] = {"extend_start_rule": "tracked_bound", "fallback_lock_log": [],
                                              "review_record": {"d2_violation_start_ratio": [None] * 4}}
    res["hydraulics_record"]["extend_bound_check"] = {"rule": "ext_moving", "breach_reads": [0, 0, 1, 0],
                                                      "margin_used_reads": [0, 0, 0, 0]}
    res["events"].append({"t_s": 30.0, "name": "WARN_ROD_PRESSURE_FALLBACK:RL:D2"})
    (d18 / "result.json").write_text(json.dumps(res), encoding="utf-8")
    it18, k18, _ = K.items_c5(C.load_row(d18, "scm", ["run_S9.py"]), PARAMS)
    check("J-P3 breach sum 1 -> fail + H-7 (rev8 3.2)", it18["J-P3"]["verdict"] == "fail"
          and it18["J-P3"].get("stop") == "H-7 (rev8 3.2)", it18["J-P3"])
    check("J11 with empty fallback_lock_log -> not_computed record (rev3 R3-C7)",
          it18["J11_window"]["status"] == "not_computed" and it18["J11_window"]["verdict"] == "record",
          it18["J11_window"])
    check("D2 fallback events with reason D2 counted (record)", it18["D2"]["d2_fallback_events"] == 1, it18["D2"])
    # T4 / T5 grades from a synthetic p2_t45 document
    l2r = C.load_row(write_l2b(tmp / "l2b_t45"), "l2b", L2B_ARGV)
    doc = {"tool_gate": {"ok": True}, "regression": {"ok": True},
           "replay": {"criteria": "rev7", "out_sha256": "x",
                      "rows": {"l2b_t45": {"settings_equal": True, "t4_0": True,
                                           "T4": {"over_0p6kN": 0, "judged_samples": 10},
                                           "T5": {"over_0p6kN": 2}}}}}
    t = K.t45_items(l2r, doc)
    check("t45 grades: T4-0 pass, T4 pass, T5 over 2 -> fail + H-7", t["T4-0"]["verdict"] == "pass"
          and t["T4"]["verdict"] == "pass" and t["T5"]["verdict"] == "fail" and "H-7" in t["T5"]["stop"], t)
    doc["regression"]["ok"] = False
    t2 = K.t45_items(l2r, doc)
    check("t45 regression failed -> S-11, 판정 불가", t2["T4"]["verdict"] == "indeterminate"
          and "S-11" in t2["T4"]["stop"], t2["T4"])


def t_l2b(tmp):
    row = C.load_row(write_l2b(tmp / "l2b_base"), "l2b", L2B_ARGV)
    items, keys, _ = K.items_d8p(row, PARAMS, judged=True, hold=True)
    check("L2b time base: events relative + start_t_s", abs(C.loc_times(row)["first"] - 24.0) < 1e-9,
          C.loc_times(row))
    check("D8 t_lift = first crawler <= 0 outside check/touch", abs(items["D8_F_after_liftoff"]["t_lift_s"] - 23.0) < 1e-9,
          items["D8_F_after_liftoff"]["t_lift_s"])
    check("D8 base row 통과", C.row_status(items, keys) == "통과",
          {k: items[k]["verdict"] for k in keys})
    row2 = C.load_row(write_l2b(tmp / "l2b_hold", dip=(2, 21.0, 21.05, 9000.0)), "l2b", L2B_ARGV)
    it2, k2, _ = K.items_d8p(row2, PARAMS, judged=True, hold=True)
    check("R40-2: raw min < F_min in 8 s, slow min >= 14.41 kN -> hold (판정 불가)",
          it2["D8_F_after_liftoff"]["verdict"] == "hold" and C.row_status(it2, k2) == "판정 불가",
          it2["D8_F_after_liftoff"])
    row3 = C.load_row(write_l2b(tmp / "l2b_late", dip=(2, 50.0, 51.5, 9000.0)), "l2b", L2B_ARGV)
    it3, _, _ = K.items_d8p(row3, PARAMS, judged=True, hold=True)
    check("dip after 8 s -> fail (no hold)", it3["D8_F_after_liftoff"]["verdict"] == "fail", it3["D8_F_after_liftoff"])
    row4 = C.load_row(write_l2b(tmp / "l2b_press", moving_bar=185.0), "l2b", L2B_ARGV)
    it4, _, _ = K.items_d8p(row4, PARAMS, judged=True, hold=True)
    check("moving sample 185 bar -> pressure fail", it4["D8_pressure"]["verdict"] == "fail"
          and abs(it4["D8_pressure"]["moving_max_bar"] - 185.0) < 1e-6, it4["D8_pressure"])
    row5 = C.load_row(write_l2b(tmp / "l2b_att", end_att=0.19), "l2b", L2B_ARGV)
    it5, _, _ = K.items_d8p(row5, PARAMS, judged=True, hold=True)
    check("end attitude 0.19 + 0.02 > 0.2 -> fail", it5["D8_end_attitude"]["verdict"] == "fail", it5["D8_end_attitude"])
    bad_argv = L2B_ARGV + ["--k1-order-gate", "on"]
    row6 = C.load_row(write_l2b(tmp / "l2b_k1"), "l2b", bad_argv)
    it6 = K.identity_l2b(row6, PARAMS)
    check("argv --k1-order-gate -> identity 판정 불가 (R2-3 / S-3)", it6["verdict"] == "indeterminate", it6)


def t_c67(tmp):
    if not (HERE / "p2_b_c67.py").exists():
        print("SKIP C-6/C-7 tests (p2_b_c67.py not in this commit)")
        return
    import p2_b_c67 as B
    d = tmp / "ol"
    d.mkdir(exist_ok=True)
    vmax = PARAMS["v_max_m_s"]
    t = np.round(np.arange(8.0001, 30.0 + 1e-9, 0.001), 6)
    cols = ["t"] + [f"u_{l}" for l in R.LEGS] + [f"v_{l}" for l in R.LEGS]
    u = np.where(t[:, None] > 9.0, vmax, 0.01 * vmax) * np.ones((1, 4))
    v = u * np.array([0.9, 0.8, 0.7, 0.6])[None, :]
    np.savez(d / "flow_series.npz", rows=np.c_[t, u, v], columns=np.array(cols))
    ts = np.round(np.arange(0.001, 30.0 + 1e-9, 0.001), 6)
    sm = np.outer(ts, np.array([0.5, 0.6, 0.7, 0.8]) * vmax)
    np.savez(d / "series.npz", t_s=ts, s_motor_m=sm)
    sr = B.speed_ratios(d, vmax)
    check("R2-4 r_vu = median v/u in window with u >= 0.1 v_max", np.allclose(sr["r_vu"], [0.9, 0.8, 0.7, 0.6]), sr["r_vu"])
    check("R2-4 r_v = s_motor slope 10..20 s / v_max", np.allclose(sr["r_v"], [0.5, 0.6, 0.7, 0.8], rtol=1e-9), sr["r_v"])
    an, sha = B.load_analyse()
    check("openloop_compare.analyse loaded without running its driver", callable(an) and len(sha) == 64, sha)
    check("C-6/C-7 kinds from names (rev4 R4-A3)", [B.kind_of({"case": n, "criteria_id": "C-6"}) for n in
                                       ("P3a_G1_B_VB_prop", "P3a_G1_B_VB_FB", "P3a_G1_B_V0_FB")] == ["C-6", "C-7a", "C-7b"])


def t_seal(tmp):
    repo = tmp / "repo"
    for rel, _, _ in R.SEALED:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, repo / rel)
    ok = R.seal_check(repo)
    check("seal: copies match", ok["ok"], [r["status"] for r in ok["sealed"]])
    rel_a = "06_analysis/02_control/verif_matrix/d1_selection_rules.md"
    p = repo / rel_a
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    s2 = R.seal_check(repo)
    st = {r["file"]: r["status"] for r in s2["sealed"]}
    check("seal: Appendix A CRLF-only -> pass, disclosed", s2["ok"] and st[rel_a] == "match_after_lf_normalisation", st[rel_a])
    rel_r = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev2.md"
    q = repo / rel_r
    q.write_bytes(q.read_bytes().replace(b"\n", b"\r\n"))
    s3 = R.seal_check(repo)
    check("seal: rule file CRLF -> mismatch (raw only, R2-9)", not s3["ok"], [r["status"] for r in s3["sealed"]])
    q.write_bytes(q.read_bytes().replace(b"\r\n", b"\n") + b" ")
    s4 = R.seal_check(repo)
    check("seal: changed byte -> mismatch", not s4["ok"])


def t_cli(tmp):
    if not (HERE / "p2_b_c3.py").exists():
        print("SKIP CLI tests (p2_b_c3.py not in this commit)")
        return
    bdir = tmp / "batch_P2TEST"
    bdir.mkdir(exist_ok=True)
    sp = scm_spec()
    write_scm(bdir / "rowA", sp)
    write_scm(bdir / "rowB", sp)
    batch = {"cases": [{"case": "rowA", "argv": ["python", "run_S9.py", "level"], "criteria_id": "C-3"},
                       {"case": "rowB", "argv": ["python", "run_S9.py", "level"], "criteria_id": "C-3"},
                       {"case": "gs", "argv": ["run_S9.py"], "criteria_id": "C-3", "r4368": {"role": "gs"}}]}
    (bdir / "batch.json").write_text(json.dumps(batch), encoding="utf-8")
    out = tmp / "out_c3.json"
    proc = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-3",
                           "--batch", str(bdir / "batch.json"), "--out", str(out)],
                          capture_output=True, text=True, encoding="utf-8")
    last = json.loads(proc.stdout.strip().splitlines()[-1])
    import hashlib
    check("CLI C-3 synthetic: exit 0, 2 rows, 통과, out_sha256 = file sha",
          proc.returncode == 0 and last.get("rows") == 2 and last.get("status") == "통과"
          and last.get("out_sha256") == hashlib.sha256(out.read_bytes()).hexdigest(), proc.stdout[-500:] + proc.stderr[-500:])
    proc2 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-1",
                            "--batch", str(bdir / "batch.json"), "--out", str(tmp / "o2.json"),
                            "--row-dir", "x=y"], capture_output=True, text=True, encoding="utf-8")
    last2 = json.loads(proc2.stdout.strip().splitlines()[-1])
    check("CLI C-1 on a batch with no C-1 rows -> S-15, exit 1", proc2.returncode == 1
          and any("S-15" in s for s in last2.get("stops", [])), proc2.stdout[-300:])
    proc3 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-3",
                            "--batch", str(tmp / "missing.json"), "--out", str(tmp / "o3.json")],
                           capture_output=True, text=True, encoding="utf-8")
    check("CLI missing batch -> exit 3 or 2 (input)", proc3.returncode in (2, 3), proc3.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp")
    a = ap.parse_args()
    tmp = Path(a.tmp) if a.tmp else Path(tempfile.mkdtemp(prefix="p2chrono_"))
    tmp.mkdir(parents=True, exist_ok=True)
    t_classify()
    t_scm(tmp)
    t_l2b(tmp)
    t_c67(tmp)
    t_seal(tmp)
    t_cli(tmp)
    n_fail = sum(1 for r in RESULTS if not r["ok"])
    tool_sha, per = p2_chrono.tool_sha(None)
    print(json.dumps({"tool": "test_p2_synthetic.py", "tests": len(RESULTS), "failed": n_fail,
                      "common_tool_sha256": tool_sha, "tmp": str(tmp)}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
