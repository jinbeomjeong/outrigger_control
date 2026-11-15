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
GREF = "0123456789abcdef0123456789abcdef01234567"   # synthetic judgement git_at_start (rev11 R11-4)
CAL = {"git": {"head": GREF, "clean": True, "dirty": []}}
REPO = p2_chrono.find_repo(HERE)
PARAMS = C.load_params(REPO)
FMIN = PARAMS["F_min_N"]
RESULTS = []
CLI_REPO = []   # ["--repo", <rules repo>] when this checkout lacks a sealed file (set in main)


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
        "s9_rows": [{"t_s": float(x), "rut_clearance_m": sp["rut"], "crawler_gap_min_m": sp["rut"], "c2_phase": p}
                    for x, p in zip(t10, ph)],
        "c2_soil": {"soil_mode_t_s": None, "mode_starts": []},
        "controller_meta": {"liftoff_approach_slow": {"settings": {"enable": True}, "start_s": sp["las_start"]},
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
    k10 = np.clip(np.searchsorted(t, t10 - 1e-9), 0, n - 1)
    u_app = np.vstack([np.zeros((1, 4)), u[:-1]])
    np.savez(folder / "record" / "record.npz", t=t10, body_quat_wxyz=np.tile([1.0, 0, 0, 0], (len(t10), 1)),
             F_crawler=np.zeros((len(t10), 3)), F_cyl=Fi[k10], u_applied=u_app)
    res = {"case": folder.name, "settings": {"start_t_s": start, "floor": floor, "target_deg": [0.0, 0.0]},
           "phases": phases, "controller_tag": "final_C4G2_P3_LAS_K1",
           "expect_controller": {"name": "final_C4G2_P3_LAS_K1", "ok": True},
           "controller_meta": {"liftoff_approach_slow": {"settings": {}},
                               "slope_clearance_margin": {"order_gate": {"enabled": True, "decisions": []},
                                                          "settings": {"flat_soil_margin_order_gate": True}}}}
    (folder / "result.json").write_text(json.dumps(res), encoding="utf-8")
    (folder / "controller_events.json").write_text(json.dumps(
        ["C2Event(t_s=24.0, name='crawler_liftoff_confirmed')"]), encoding="utf-8")  # absolute (rev6 R6-1)
    return folder


L2B_ARGV = ["run_S8C.py", "run", "--tag", "x", "--expect-controller", "final_C4G2_P3_LAS_K1"]
SCM_VB_ARGV = ["run_S9.py", "level", "--extend-start-tracked", "--expect-controller", "final_C4G2_P3_LAS_K1"]
SCM_V0_ARGV = ["run_S9.py", "level", "--expect-controller", "final_C4G2_LAS_K1"]


def _edit_result(src: Path, dst: Path, fn):
    """Copy a synthetic row folder and edit its result.json with fn(res)."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    res = json.loads((dst / "result.json").read_text(encoding="utf-8"))
    fn(res)
    (dst / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return dst


def _set_npz(path: Path, **arrays):
    """Rewrite an npz with keys replaced / added (None = drop the key)."""
    z = dict(np.load(path))
    for k, v in arrays.items():
        if v is None:
            z.pop(k, None)
        else:
            z[k] = v
    np.savez(path, **z)


def write_rod_record(folder: Path, sp: dict, rod_value=5e5):
    """record/record.npz with a finite (or NaN) `meas.rod_pressure` (v5 rev9 3.1 rod reading)."""
    t10 = np.round(np.arange(sp["t0"] + 0.1, sp["t_end"] + 1e-9, 0.1), 6)
    (folder / "record").mkdir(exist_ok=True)
    np.savez(folder / "record" / "record.npz", t=t10, u_applied=np.zeros((len(t10), 4)),
             F_cyl=np.full((len(t10), 4), 50000.0), **{"meas.rod_pressure": np.full((len(t10), 4), rod_value)})


def t_rev8_jp3(tmp, sp, d18):
    """436.8 rev8 R8-2: J-P3 scope by the tag (rules 4.1 is_extend_start_tag), request record checks."""
    d_v0 = write_scm(tmp / "jp3_v0", copy.deepcopy(sp))
    j = K.jp3_item(C.load_row(d_v0, "scm", SCM_V0_ARGV))
    check("R8-2 V0 tag, no extend_start_rule key, argv / options off -> na (not counted as missing)",
          j["verdict"] == "na" and j["extend_start_tag"] is False and "stop" not in j, j)
    d_nob = _edit_result(d_v0, tmp / "jp3_v0_noblock", lambda r: r.pop("v5_hydraulics"))
    j = K.jp3_item(C.load_row(d_nob, "scm", SCM_V0_ARGV))
    check("R8-2 no v5_hydraulics block -> argv only compared, na",
          j["verdict"] == "na" and j["request_compared"] == ["argv"], j)
    j = K.jp3_item(C.load_row(d_v0, "scm", SCM_V0_ARGV + ["--extend-start-tracked"]))
    check("R8-2 V0 tag but argv --extend-start-tracked -> S-2",
          j["verdict"] == "indeterminate" and j.get("stop", "").startswith("S-2")
          and j["request_mismatch"] == ["argv --extend-start-tracked"], j)
    d_v0o = _edit_result(d_v0, tmp / "jp3_v0_opt",
                         lambda r: r["v5_hydraulics"]["hydraulic_options"].update(extend_start_tracked=True))
    j = K.jp3_item(C.load_row(d_v0o, "scm", SCM_V0_ARGV))
    check("R8-2 V0 tag but hydraulic_options.extend_start_tracked true -> S-2",
          j.get("stop", "").startswith("S-2")
          and j["request_mismatch"] == ["v5_hydraulics.hydraulic_options.extend_start_tracked"], j)
    j = K.jp3_item(C.load_row(d_v0o, "scm", SCM_VB_ARGV))
    check("R8-2 ③ tag, requests on, extend_start_rule key absent -> 판정 불가 (9.3), no stop",
          j["verdict"] == "indeterminate" and "stop" not in j and "9.3" in j["reason"], j)
    d_const = _edit_result(d18, tmp / "jp3_const",
                           lambda r: r["controller_meta"]["two_pressure"]["settings"].update(extend_start_rule="constant"))
    j = K.jp3_item(C.load_row(d_const, "scm", SCM_VB_ARGV))
    check("R8-2 ③ tag but extend_start_rule constant -> S-2",
          j["verdict"] == "indeterminate" and j.get("stop", "").startswith("S-2"), j)
    d_v0tb = _edit_result(d18, tmp / "jp3_v0tb",
                          lambda r: r["v5_hydraulics"]["hydraulic_options"].pop("extend_start_tracked"))
    j = K.jp3_item(C.load_row(d_v0tb, "scm", SCM_V0_ARGV))
    check("R8-2 V0 tag, requests off, but extend_start_rule tracked_bound -> S-2 (tag vs controller)",
          j.get("stop", "").startswith("S-2") and "tracked_bound" in j["stop"], j)
    j = K.jp3_item(C.load_row(d18, "scm", ["run_S9.py", "level", "--extend-start-tracked"]))
    check("R8-2 no argv --expect-controller -> tag not established, S-2",
          j["tag_established"] is False and j.get("stop", "").startswith("S-2"), j)
    d_nm = _edit_result(d18, tmp / "jp3_name",
                        lambda r: r["c2_setup"]["expect_controller"].update(name="final_C4G2_LAS_K1"))
    j = K.jp3_item(C.load_row(d_nm, "scm", SCM_VB_ARGV))
    check("R8-2 expect_controller.name != argv tag -> S-2", j.get("stop", "").startswith("S-2"), j)
    d_ko = _edit_result(d18, tmp / "jp3_ko", lambda r: r["c2_setup"]["expect_controller"].update(ok=False))
    j = K.jp3_item(C.load_row(d_ko, "scm", SCM_VB_ARGV))
    check("R8-2 expect check false -> S-2", j.get("stop", "").startswith("S-2"), j)
    argv_k1 = ["run_S9.py", "level", "--extend-start-tracked", "--expect-controller", "final_C4G2_P3_K1"]
    j = K.jp3_item(C.load_row(d18, "scm", argv_k1))
    check("R8-2 ③ by is_extend_start_tag whatever the suffixes (final_C4G2_P3_K1) -> judged (breach fail)",
          j["extend_start_tag"] is True and j["verdict"] == "fail", j)
    d_vbnb = _edit_result(d18, tmp / "jp3_vb_noblock", lambda r: r.pop("v5_hydraulics"))
    j = K.jp3_item(C.load_row(d_vbnb, "scm", SCM_VB_ARGV))
    check("R8-2 ③ tag, no v5_hydraulics block, argv on -> argv only, judged",
          j["request_compared"] == ["argv"] and j["verdict"] == "fail", j)
    check("rules 4.1 reading: is_extend_start_tag from v5_options of this checkout",
          [C.is_extend_start_tag(x) for x in ("final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1", "ABL_LAS_K1", None)]
          == [True, False, False, False]
          and Path(C.v5_options().__file__).resolve().is_relative_to((REPO / "03_src").resolve()),
          C.v5_options().__file__)


def t_rev8_j11(tmp, sp):
    """436.8 rev8 R8-3 / R8-3a: SCM J11 on step_series.npz law_locked (rev6 6, R6-B7, rev2 D-1)."""
    import math
    base = write_scm(tmp / "j11s", copy.deepcopy(sp))
    t10 = np.load(base / "r8_series.npz")["t"]
    ph = np.load(base / "r8_series.npz")["phase"]
    u = np.zeros((len(t10), 4))
    u[(t10 >= 39.9 - 1e-9) & (t10 <= 40.5 + 1e-9), 0] = 0.005
    np.savez(base / "r8_series.npz", t=t10, issued_u=u, phase=ph)
    tw = 40.6 + 0.1 * math.log(0.005 / 1e-4) + 0.05 + 0.1

    def tp_of(r):
        r["controller_meta"]["two_pressure"] = {
            "settings": {"lock_window_valve_tau_s": 0.1, "lock_window_eps_m_s": 1e-4,
                         "lock_window_closing_delay_s": 0.05, "extend_start_rule": "tracked_bound"},
            "fallback_lock_log": [{"leg": "FL", "t_start_s": 40.6, "window_end_s": tw}]}
        r["events"].append({"t_s": 40.0, "name": "WARN_ROD_PRESSURE_FALLBACK:FL"})
    _edit_result(base, tmp / "j11s_t", tp_of)
    base = tmp / "j11s_t"
    t = np.load(base / "step_series.npz")["t_s"]
    n = len(t)

    def variant(name, ll):
        d = tmp / name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(base, d)
        _set_npz(d / "step_series.npz", law_locked=ll)
        row = C.load_row(d, "scm", SCM_VB_ARGV)
        return row, K.j11_item(row, row.result["controller_meta"]["two_pressure"])

    ok_ll = np.ones((n, 4), dtype=np.int8)
    ok_ll[(t >= 39.9) & (t < 40.75), 0] = 0
    row, j = variant("j11s_locked", ok_ll)
    check("R8-3 SCM law_locked read from step_series.npz on t_s, well formed",
          row.law_locked is not None and row.law_locked_problems == []
          and row.law_locked_source == "step_series.npz law_locked", row.law_locked_problems)
    check("R8-3 SCM fallback leg FL locked before t_w -> window end = log, n_late 0, pass",
          j["verdict"] == "pass" and j["n_late"] == [0, 0, 0, 0] and j["log_matches"][0]["match"], j)
    late_ll = np.ones((n, 4), dtype=np.int8)
    late_ll[(t >= 39.9) & (t < 42.0), 0] = 0
    _, j = variant("j11s_late", late_ll)
    check("R8-3 SCM fallback leg still moving after t_w -> n_late 1, H-7",
          j["verdict"] == "fail" and j["n_late"][0] == 1 and j["stop"].startswith("H-7"), j)
    pre = ok_ll.copy()
    pre[t < 10.0, :] = -1
    row, j = variant("j11s_pre", pre)
    it, _, _ = K.items_c5(row, PARAMS)
    check("rev6 6: -1 before the first armed sample = locked (pass; transitions FL off 1 / on 1)",
          j["verdict"] == "pass" and it["J11_lock_transitions"]["lock_off"] == [1, 0, 0, 0]
          and it["J11_lock_transitions"]["lock_on"] == [1, 0, 0, 0], (j.get("verdict"), it["J11_lock_transitions"]))
    check("R9-3 before_first_arming pattern recorded, prefix 1999 samples",
          row.law_locked_pattern["patterns"] == ["before_first_arming"]
          and row.law_locked_pattern["unarmed_prefix_samples"] == int(np.sum(t < 10.0)), row.law_locked_pattern)
    aft = ok_ll.copy()
    aft[(t >= 50.0) & (t < 50.5), 2] = -1
    row, j = variant("j11s_after", aft)
    check("R9-3 -1 after arming -> format error R9-2.6, J11 판정 불가 + stop R9-5",
          row.law_locked is None and C.law_locked_codes(row.law_locked_problems) == ["R9-2.6"]
          and row.law_locked_pattern["patterns"] == ["after_arming"]
          and row.law_locked_pattern["after_arming_samples_per_leg"] == [0, 0, 500, 0]
          and j["verdict"] == "indeterminate" and j.get("stop", "").startswith("R9-5"), (row.law_locked_problems, j))
    whole = np.full((n, 4), -1, np.int8)
    row, j = variant("j11s_whole", whole)
    check("R9-3 whole run -1 -> format error (whole_run), J11 stop R9-5",
          row.law_locked_pattern["patterns"] == ["whole_run"] and j.get("stop", "").startswith("R9-5")
          and "R9-2.6" in j["law_locked_codes"], (row.law_locked_pattern, j.get("stop")))
    mis = ok_ll.copy()
    mis[t < 10.0, :] = -1
    mis[(t >= 10.0) & (t < 10.5), 1] = -1   # FR leaves -1 0.5 s later than the others
    row, j = variant("j11s_mis", mis)
    check("R9-3 legs leave -1 at different samples -> format error (per_leg_mismatch), stop R9-5",
          "per_leg_mismatch" in row.law_locked_pattern["patterns"] and j.get("stop", "").startswith("R9-5"),
          row.law_locked_pattern)
    pre1 = ok_ll.copy()
    pre1[0, :] = -1
    p1 = C.law_locked_pattern(pre1)
    check("R9-3 one-sample -1 prefix on all legs -> before_first_arming (allowed)",
          p1["ok"] and p1["patterns"] == ["before_first_arming"] and p1["first_armed_index_per_leg"] == [1, 1, 1, 1], p1)
    for name, bad, code in (("j11s_i64", ok_ll.astype(np.int64), "R9-2.3"),
                            ("j11s_shape", ok_ll[:, :3].copy(), "R9-2.2"),
                            ("j11s_rows", ok_ll[:-1].copy(), "R9-2.2"),
                            ("j11s_val", np.where(ok_ll == 0, 2, ok_ll).astype(np.int8), "R9-2.4")):
        row, j = variant(name, bad)
        check(f"R9-2 malformed ({code}) -> law_locked unused, J11 판정 불가 + stop R9-5",
              row.law_locked is None and code in C.law_locked_codes(row.law_locked_problems)
              and j["verdict"] == "indeterminate" and j.get("stop", "").startswith("R9-5"), (row.law_locked_problems, j))
    tg = np.r_[np.round(np.arange(0.001, 1.0, 0.001), 6), 1.5]
    check("R9-2.5 time column not 1 ms -> malformed",
          C.law_locked_codes(C.law_locked_check(np.zeros((len(tg), 4), np.int8), tg)) == ["R9-2.5"])
    tj = np.round(np.arange(0.001, 1.0, 0.001), 9)
    tj[500:] += 0.9e-6
    check("R9-2.5 a 0.9 us jitter (within 1e-6 s procedure value) -> well formed",
          C.law_locked_check(np.zeros((len(tj), 4), np.int8), tj) == [])
    tj2 = tj.copy()
    tj2[700:] += 1.2e-6
    check("R9-2.5 a 1.2 us step (> 1e-6 s) -> malformed",
          C.law_locked_codes(C.law_locked_check(np.zeros((len(tj2), 4), np.int8), tj2)) == ["R9-2.5"])
    check("R9-2.1 time column absent -> malformed",
          "R9-2.1" in C.law_locked_codes(C.law_locked_check(np.zeros((10, 4), np.int8), None)))
    row, j = variant("j11s_none", None)
    check("R9-5 SCM law_locked missing (fallback leg present) -> 판정 불가 + stop",
          row.law_locked_source is None and j["verdict"] == "indeterminate" and "missing" in j["reason"]
          and j.get("stop", "").startswith("R9-5") and j["law_locked_codes"] == ["key"], j)
    d0 = _edit_result(tmp / "j11s_none", tmp / "j11s_none_nofb", lambda r: (
        r["controller_meta"]["two_pressure"].update(fallback_lock_log=[]),
        r.update(events=[e for e in r["events"] if "FALLBACK" not in e["name"]])))
    r0 = C.load_row(d0, "scm", SCM_VB_ARGV)
    j0 = K.j11_item(r0, r0.result["controller_meta"]["two_pressure"])
    check("R9-5: SCM law_locked missing, no fallback leg -> still 판정 불가 + stop (not 'record')",
          j0["verdict"] == "indeterminate" and j0.get("stop", "").startswith("R9-5"), j0)
    # L2b: rev9 R9-5 replaces rev8 R8-3 item 4 / rev3 R3-C7: missing = 판정 불가 + stop as SCM
    dl = write_l2b(tmp / "l2b_noll")
    _set_npz(dl / "pads.npz", law_locked=None)
    rl = C.load_row(dl, "l2b", L2B_ARGV)
    jl = K.j11_item(rl, {"fallback_lock_log": [], "settings": {}})
    check("R9-5 L2b pads.npz law_locked missing, no fallback leg -> 판정 불가 + stop (was record under rev8)",
          jl["verdict"] == "indeterminate" and jl.get("stop", "").startswith("R9-5") and "pads.npz" in jl["stop"], jl)
    jr = K.j11_record_item(rl)
    check("R9-6 outside C-5: same L2b row -> J11 record, input absent counted, no stop",
          jr["verdict"] == "record" and "stop" not in jr and jr["input_absent"] is True
          and str(jr["c5_stop_would_be_record"]).startswith("R9-5"), jr)
    dl2 = write_l2b(tmp / "l2b_ll64")
    _set_npz(dl2 / "pads.npz", law_locked=np.zeros((len(np.load(dl2 / "pads.npz")["t"]), 4), np.int64))
    rl2 = C.load_row(dl2, "l2b", L2B_ARGV)
    jl2 = K.j11_item(rl2, {"fallback_lock_log": [], "settings": {}})
    check("R9-5 L2b pads.npz law_locked malformed (int64) -> 판정 불가 + stop",
          jl2["verdict"] == "indeterminate" and jl2.get("stop", "").startswith("R9-5"), jl2)
    dl3 = write_l2b(tmp / "l2b_llaft")
    ll3 = np.zeros((len(np.load(dl3 / "pads.npz")["t"]), 4), np.int8)
    ll3[5000:5100, :] = -1
    _set_npz(dl3 / "pads.npz", law_locked=ll3)
    rl3 = C.load_row(dl3, "l2b", L2B_ARGV)
    jl3 = K.j11_item(rl3, {"fallback_lock_log": [], "settings": {}})
    check("R9-2 / R9-3 same format check on L2b: -1 after arming -> R9-2.6, stop R9-5",
          jl3["law_locked_codes"] == ["R9-2.6"] and jl3.get("stop", "").startswith("R9-5"), jl3)
    rok = C.load_row(write_l2b(tmp / "l2b_llok"), "l2b", L2B_ARGV)
    jok = K.j11_record_item(rok)
    check("R9-6 outside C-5, well-formed L2b law_locked -> record, input not absent",
          jok["verdict"] == "record" and jok["input_absent"] is False, jok)


def t_rev9(tmp, sp):
    """436.8 rev9 R9-1 (expect check), R9-4 (LS rows by v5_setting), R9-7 (tag reading, check only)."""
    d = write_scm(tmp / "r9_scm", copy.deepcopy(sp))
    e = K.expect_item(C.load_row(d, "scm", SCM_VB_ARGV))
    check("R9-1 SCM c2_setup.expect_controller.ok true -> pass, no stop", e["verdict"] == "pass" and "stop" not in e, e)
    dko = _edit_result(d, tmp / "r9_scm_ko", lambda r: r["c2_setup"]["expect_controller"].update(ok=False))
    e = K.expect_item(C.load_row(dko, "scm", SCM_VB_ARGV))
    check("R9-1 ok false -> S-2 stop (G-S also S-11)", e.get("stop", "").startswith("S-2") and "S-11" in e["stop"], e)
    dnk = _edit_result(d, tmp / "r9_scm_nokey", lambda r: r["c2_setup"].pop("expect_controller"))
    e = K.expect_item(C.load_row(dnk, "scm", SCM_VB_ARGV))
    check("R9-1 expect_controller key absent -> S-2 stop", e.get("stop", "").startswith("S-2") and "absent" in e["stop"], e)
    dl = write_l2b(tmp / "r9_l2b")
    res = json.loads((dl / "result.json").read_text(encoding="utf-8"))
    res["expect_controller"].pop("ok")
    (dl / "result.json").write_text(json.dumps(res), encoding="utf-8")
    e = K.expect_item(C.load_row(dl, "l2b", L2B_ARGV))
    check("R9-1 L2b expect_controller.ok absent -> S-2 stop (source expect_controller.ok)",
          e.get("stop", "").startswith("S-2") and e["source"] == "expect_controller.ok", e)
    items = {}
    keys = []
    p2_chrono.augment_items("C-3", C.load_row(dko, "scm", SCM_VB_ARGV), items, keys)
    b = K.bundle_status([{"case": "x", "status": C.row_status(items, keys), "judged_keys": keys, "items": items}])
    check("R9-1 in a bundle (C-3) -> bundle stop S-2, 판정 불가 (not only J-P3)",
          b["status"] == "판정 불가" and any("S-2" in s for s in b["stops"]) and "J11_record" in items, b["stops"])
    items6 = {}
    p2_chrono.augment_items("C-6C7", C.load_row(dko, "scm", SCM_VB_ARGV), items6, [])
    check("R9-1 not applied to open-loop C-6C7", items6 == {}, items6)
    # R9-4 + rev10 R10-1 (input boundary)
    BN = "V5-RESUME-K1-C5"
    man = {"batches": {BN: {"rows": [
        {"case": "A_LS1", "v5_setting": "LS1"}, {"case": "B", "v5_setting": "VB"}, {"case": "C", "v5_setting": "LS4"},
        {"case": "D", "v5_setting": None}, {"case": "E_LS4", "v5_setting": "VB"}, {"case": "F", "v5_setting": None},
        {"case": "G"}, {"case": "DUP", "v5_setting": "VB"}, {"case": "DUP", "v5_setting": "VB"},
        {"case": "BDUP", "v5_setting": "VB"}]}}}
    bcases = [{"case": "A_LS1", "v5_setting": "LS1"}, {"case": "B", "v5_setting": "VB"},
              {"case": "C", "v5_setting": "LS1"}, {"case": "D"}, {"case": "E_LS4", "v5_setting": "VB"},
              {"case": "F", "v5_setting": "LS4"}, {"case": "G", "v5_setting": None}, {"case": "DUP", "v5_setting": "VB"},
              {"case": "NOMAN"}, {"case": "BDUP", "v5_setting": "VB"}, {"case": "BDUP", "v5_setting": "VB"}]
    bjson = {"batch": BN, "cases": bcases}
    bpath = Path(f"batch_{BN}_20261113_120000/batch.json")
    ctx = p2_chrono.batch_ctx(bjson, bpath, man)
    cls = {c["case"]: K.ls_classification(c, ctx)["ls"] for c in bcases}
    check("R9-4 / R10-1b LS classes: both LS1 -> LS; both VB -> not; differ -> None; both value None (one row "
          "each) -> not; name '_LS4' with VB -> not; batch value only -> None; manifest key absent + batch None -> "
          "not; manifest 2 rows -> None; manifest 0 rows (batch value absent) -> None (was 'not' in rev9 reading);"
          " batch.json 2 entries -> None",
          cls == {"A_LS1": True, "B": False, "C": None, "D": False, "E_LS4": False, "F": None, "G": False,
                  "DUP": None, "NOMAN": None, "BDUP": None}, cls)
    labs = {c["case"]: K.ls_classification(c, ctx)["input"]["blocking"] for c in bcases}
    check("R10-1b labels: manifest_rows_many, manifest_rows_0, batch_cases_many",
          labs["DUP"] == ["manifest_rows_many"] and labs["NOMAN"] == ["manifest_rows_0"]
          and labs["BDUP"] == ["batch_cases_many"] and labs["B"] == [], labs)
    c0 = K.ls_classification({"case": "B", "v5_setting": "VB"}, p2_chrono.batch_ctx({"batch": BN, "cases": []},
                                                                                    bpath, man))
    check("R10-1b batch.json has 0 entries for the case -> None (batch_cases_0)",
          c0["ls"] is None and c0["input"]["blocking"] == ["batch_cases_0"], c0)
    check("R9-4 manifest batch absent -> rows None", K.manifest_rows(man, "V5-RESUME-K1-C9") is None)
    # R10-1a full batch name
    nm = {k: p2_chrono.batch_name_of(bj, Path(f), man)[0] for k, bj, f in (
        ("key=folder", {"batch": BN}, f"batch_{BN}_20261113_120000/batch.json"),
        ("no key", {}, f"batch_{BN}_20261113_120000/batch.json"),
        ("key!=folder", {"batch": BN}, "batch_V5-RESUME-K1-GS_20261113_120000/batch.json"),
        ("key, folder not stamped", {"batch": BN}, "x/batch.json"),
        ("neither", {}, "x/batch.json"),
        ("short ID", {"batch": "C5"}, "batch_C5_20261113_120000/batch.json"),
        ("not in manifest", {}, "batch_V5-RESUME-K1-C9_20261113_120000/batch.json"))}
    check("R10-1a full batch name: key = folder -> name; no key -> folder; differ / unstamped folder / neither / "
          "short ID / not a manifest key -> unknown",
          nm == {"key=folder": BN, "no key": BN, "key!=folder": None, "key, folder not stamped": None,
                 "neither": None, "short ID": None, "not in manifest": None}, nm)
    cu = K.ls_classification({"case": "D"}, p2_chrono.batch_ctx({"batch": BN, "cases": [{"case": "D"}]},
                                                                Path("batch_V5-RESUME-K1-GS_20261113_1/batch.json"),
                                                                man))
    check("R10-1b batch name unknown + both values absent -> None (not 'not LS')",
          cu["ls"] is None and "batch_name_unknown" in cu["input"]["blocking"], cu)
    rv0 = C.load_row(d, "scm", SCM_V0_ARGV)
    li = K.ls_item(rv0, {"case": "A_LS1", "v5_setting": "LS1"}, ctx)
    check("R9-4 LS row with a non-③ tag -> S-2", li["ls"] is True and li.get("stop", "").startswith("S-2"), li)
    li2 = K.ls_item(C.load_row(d, "scm", SCM_VB_ARGV), {"case": "A_LS1", "v5_setting": "LS1"}, ctx)
    check("R9-4 LS row with a ③ tag -> record, no stop", li2["ls"] is True and "stop" not in li2
          and li2["verdict"] == "record", li2)
    it, _, _ = K.items_c5(C.load_row(d, "scm", SCM_VB_ARGV), PARAMS, case={"case": "C", "v5_setting": "LS1"},
                          ctx=ctx)
    check("R9-4 items_c5: LS_class present, mismatch -> 판정 불가, J11 ls None",
          it["LS_class"]["ls"] is None and it["LS_class"]["verdict"] == "indeterminate"
          and it["J11_window"]["ls"] is None, it["LS_class"])
    check("batch id from batch.json 'batch' (checked against the folder) or folder name",
          p2_chrono.batch_id_of({"batch": BN}, bpath) == BN
          and p2_chrono.batch_id_of({}, Path("batch_V5-RESUME-K1-GS_20261113_082117/batch.json")) == "V5-RESUME-K1-GS")
    # R10-1b manifest file: missing / not JSON / no batches -> input error (exit 2)
    class _A:
        manifest = None
    for nmx, content in (("absent", None), ("notjson", "{not json"), ("nobatches", json.dumps({"rules": {}}))):
        a = _A()
        a.manifest = str(tmp / f"man_{nmx}.json")
        if content is not None:
            Path(a.manifest).write_text(content, encoding="utf-8")
        try:
            p2_chrono.load_manifest(a, REPO, required=True)
            check(f"R10-1b manifest {nmx} -> input error", False)
        except C.InputError as ex:
            check(f"R10-1b manifest {nmx} -> input error", "R10-1b" in str(ex), ex)
    # R9-7 (check only): the ③ reading of the K1-only tags (rules 4.1 is_extend_start_tag)
    check("R9-7 tags: final_C4G2_K1 not ③, final_C4G2_P3_K1 ③ (is_extend_start_tag)",
          [C.is_extend_start_tag(x) for x in ("final_C4G2_K1", "final_C4G2_P3_K1")] == [False, True])
    import p2_rules as RR
    check("R9-2 / R9-4 constants: 1 ms +- 1e-6 s, LS1..LS4", RR.LAW_LOCK_DT_S == 1e-3 and RR.LAW_LOCK_DT_TOL_S == 1e-6
          and RR.LS_SETTINGS == ("LS1", "LS2", "LS3", "LS4"))


def t_rev11(tmp, sp):
    """436.8 rev11 R11-4 (commit identity incl. open loop) and R11-1 (Chrono expected switches)."""
    res_ok = {"code_state": {"git_at_start": {"head": GREF, "clean": True}}}
    ci = K.commit_item("C-3", {"code_at_launch": CAL}, res_ok, GREF[:7])
    check("R11-4 level row: code_at_launch head and code_state head = git_at_start (7-digit) -> pass",
          ci["verdict"] == "pass" and "stop" not in ci and ci["code_state_compared"] is True, ci)
    ci = K.commit_item("C-6C7", {"code_at_launch": CAL}, {}, GREF)
    check("R11-4 open-loop row with code_at_launch = git_at_start -> pass (code_state not compared)",
          ci["verdict"] == "pass" and ci["open_loop"] and ci["code_state_compared"] is False, ci)
    ci = K.commit_item("C-6C7", {}, {}, GREF)
    check("R11-4 open-loop row without code_at_launch -> S-12", ci.get("stop", "").startswith("S-12")
          and "missing" in ci["stop"], ci)
    other = {"git": {"head": "f" * 40, "clean": True}}
    ci = K.commit_item("C-1", {"code_at_launch": other}, res_ok, GREF)
    check("R11-4 code_at_launch head != git_at_start -> S-12", ci.get("stop", "").startswith("S-12"), ci)
    ci = K.commit_item("C-5", {"code_at_launch": CAL}, {"code_state": {"git_at_start": {"head": "e" * 40}}}, GREF)
    check("R11-4 level / L2b row: result.json code_state.git_at_start differs -> S-12",
          ci.get("stop", "").startswith("S-12") and "code_state" in ci["stop"], ci)
    ci = K.commit_item("C-1", {"code_at_launch": CAL}, {}, GREF)
    check("R11-4 closed-loop row without code_state record -> code_at_launch only ('that record exists')",
          ci["verdict"] == "pass" and ci["code_state_compared"] is False, ci)
    dirty = {"git": {"head": GREF, "clean": False, "dirty": ["03_src/x.py"], "paths": ["03_src"]}}
    ci = K.commit_item("C-3", {"code_at_launch": dirty}, res_ok, GREF)
    check("R12-2 Chrono dirty / clean false -> record only (pass, dirty_record true, paths kept)",
          ci["verdict"] == "pass" and "stop" not in ci and ci["dirty_record"] is True
          and ci["code_at_launch_paths"] == ["03_src"], ci)
    ci = K.commit_item("C-6C7", {"code_at_launch": CAL}, {"code_state": {"git_at_start": {"head": "e" * 40}}}, GREF)
    check("R12-4 open-loop row with a different result.json code_state -> record only (pass, same false)",
          ci["verdict"] == "pass" and ci["open_loop_code_state_same_record"] is False, ci)
    ci = K.commit_item("C-1", {"code_at_launch": CAL}, res_ok, None)
    check("R11-4 no judgement git_at_start -> S-12 (cannot show the commit)", "stop" in ci, ci)
    try:
        p2_chrono.git_ref_arg("xyz", required=True)
        check("R11-4 --git-at-start not hex -> input error", False)
    except C.InputError:
        check("R11-4 --git-at-start not hex -> input error", True)
    try:
        p2_chrono.git_ref_arg(None, required=True)
        check("R11-4 judge without --git-at-start -> input error", False)
    except C.InputError:
        check("R11-4 judge without --git-at-start -> input error", True)
    d = write_scm(tmp / "r11_scm", copy.deepcopy(sp))
    row = C.load_row(d, "scm", SCM_VB_ARGV)
    items6, keys6 = {}, []
    p2_chrono.augment_items("C-6C7", row, items6, keys6, {}, {}, GREF, commit=True)
    check("R11-4 augment: open-loop bundle gets the commit item only (no R9-1 / J11)",
          list(items6) == ["R11-4_commit"] and keys6 == ["R11-4_commit"]
          and items6["R11-4_commit"].get("stop", "").startswith("S-12"), items6)
    b = K.bundle_status([{"case": "ol", "status": C.row_status(items6, keys6), "judged_keys": keys6,
                          "items": items6}], record_bundle=True)
    check("R11-4 S-12 on an open-loop row -> record bundle stops (기록 불완전)",
          b["status"] == "기록 불완전" and any("S-12" in x for x in b["stops"]), b["stops"])
    # R11-1 Chrono rows: LAS-b enable by line kind
    idn = K.identity_scm(row)
    check("R11-1 Chrono row: LAS-b enable true expected -> identity pass", idn["verdict"] == "pass"
          and idn["las_settings_enable_ok"], idn)
    doff = _edit_result(d, tmp / "r11_scm_en", lambda r: r["controller_meta"]["liftoff_approach_slow"]
                        ["settings"].update(enable=False))
    idf = K.identity_scm(C.load_row(doff, "scm", SCM_VB_ARGV))
    check("R11-1 on arm with LAS-b settings.enable false -> identity 판정 불가",
          idf["verdict"] == "indeterminate" and "R11-1" in idf["reason"], idf)


def t_rev8_record(rec_dir):
    """Short SCM record made by the runner at 7527fc3 (record only, not a path 1 output)."""
    if rec_dir is None:
        print("SKIP 7527fc3 SCM record tests (no --lawlock-record)")
        return
    d = Path(rec_dir)
    row = C.load_row(d, "scm", SCM_VB_ARGV)
    check("7527fc3 record: step_series.npz law_locked [N, 4] int8 on t_s, well formed",
          row.law_locked is not None and row.law_locked.shape == (len(row.tF), 4) and row.law_locked_problems == [],
          row.law_locked_problems)
    it, _, _ = K.items_c5(row, PARAMS)
    j = it["J11_window"]
    check("7527fc3 record: J11 computed (no actual fallback leg -> record, n_late of 4 legs)",
          j["verdict"] == "record" and len(j.get("n_late", [])) == 4, j)
    tr = it["J11_lock_transitions"]
    check("7527fc3 record: lock transitions per leg off 2 / on 2, no -1 after arming",
          tr["lock_off"] == [2, 2, 2, 2] and tr["lock_on"] == [2, 2, 2, 2]
          and tr["unarmed_after_armed_samples"] == [0, 0, 0, 0], tr)
    jp = it["J-P3"]
    check("7527fc3 record: J-P3 tag ③ established, request records agree (no S-2)",
          jp["tag_established"] is True and jp["extend_start_tag"] is True
          and "S-2" not in str(jp.get("stop", "")) and jp["extend_start_rule"] == "tracked_bound", jp)


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
    sp11d = copy.deepcopy(sp11)
    sp11d["dips"] = [(0, 21.2, 21.3, FMIN - 500.0)]
    it11d, _, _ = K.items_p3(scm_row(tmp, sp11d, "p38d"), PARAMS, 120.0, True, g6=True)
    check("pre-LOC loss below F_min with P3-3 pass, FAULT 0 -> P3-8_preloc_loss FLAG (rev6 R6-C3)",
          it11d["P3-8"]["verdict"] == "flag" and it11d["P3-8"]["flags"] == ["P3-8_preloc_loss"], it11d["P3-8"])
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
    res["controller_meta"]["two_pressure"] = {"settings": {"extend_start_rule": "tracked_bound"},
                                              "fallback_lock_log": [],
                                              "review_record": {"d2_violation_start_ratio": [None] * 4}}
    res["v5_hydraulics"]["hydraulic_options"]["extend_start_tracked"] = True
    res["hydraulics_record"]["extend_bound_check"] = {"rule": "ext_moving", "breach_reads": [0, 0, 1, 0],
                                                      "margin_used_reads": [0, 0, 0, 0]}
    res["events"].append({"t_s": 30.0, "name": "WARN_ROD_PRESSURE_FALLBACK:RL"})
    res["events"].append({"t_s": 30.0, "name": "INFO_ROD_PRESSURE_FAULT_REASON:RL:D2b_rate"})
    res["events"].append({"t_s": 30.0, "name": "WARN_ROD_PRESSURE_FALLBACK:FR"})
    (d18 / "result.json").write_text(json.dumps(res), encoding="utf-8")
    write_rod_record(d18, sp18)   # rev25 CD-1 / v5 rev9 3.2: a rod reading reached the controller
    it18, k18, _ = K.items_c5(C.load_row(d18, "scm", SCM_VB_ARGV), PARAMS)
    check("J-P3 breach sum 1 -> 미달 (rev25 CD-1: grade item, H-7 label, no stop)", it18["J-P3"]["verdict"] == "fail"
          and "stop" not in it18["J-P3"] and it18["J-P3"]["original_rule_label"].startswith("H-7"), it18["J-P3"])
    check("J11 SCM row without step_series law_locked -> 판정 불가 + stop (436.8 rev9 R9-5)",
          it18["J11_window"]["verdict"] == "indeterminate"
          and it18["J11_window"].get("stop", "").startswith("R9-5"), it18["J11_window"])
    check("D2 reason from INFO_ROD_PRESSURE_FAULT_REASON (rev5 R5-B2), FR reason unreadable",
          it18["D2"]["d2_fallback_legs"] == ["RL"] and it18["D2"]["reason_unreadable_legs"] == ["FR"], it18["D2"])
    t_rev8_jp3(tmp, sp, d18)
    d19 = write_scm(tmp / "c5v0", copy.deepcopy(sp))
    # identity_scm + rev7 R7-4 (las_off key by arm)
    idn = K.identity_scm(C.load_row(d19, "scm", ["run_S9.py", "level"]))
    check("R7-4 on arm, c2_setup.las_off absent -> read as on, identity pass",
          idn["verdict"] == "pass" and idn["las_off_consistent"] and idn["c2_setup_las_off"] is None, idn)
    check("R7-4 record: on arm LAS end_s / ramp absent -> listed as absent where required (record only)",
          "controller_meta.liftoff_approach_slow.end_s" in idn["r7_4_las_keys"]["absent_where_required"]
          and "c2_setup.las_off" not in idn["r7_4_las_keys"]["absent_where_required"], idn["r7_4_las_keys"])
    ido = K.identity_scm(C.load_row(d19, "scm", ["run_S9.py", "level", "--las-off", "--k1-order-gate", "on"]))
    check("R7-4 off arm (argv --las-off), c2_setup.las_off absent -> identity 판정 불가",
          ido["verdict"] == "indeterminate" and not ido["las_off_consistent"]
          and ido["r7_4_las_keys"]["absent_where_required"] == ["c2_setup.las_off"], ido)
    r20 = json.loads((d19 / "result.json").read_text(encoding="utf-8"))
    r20["c2_setup"]["las_off"] = True
    r20["controller_meta"]["liftoff_approach_slow"]["settings"]["enable"] = False
    r20["c2_setup"]["k1_order_gate"] = "on"
    d20 = tmp / "c5off"
    shutil.copytree(d19, d20)
    (d20 / "result.json").write_text(json.dumps(r20), encoding="utf-8")
    idf = K.identity_scm(C.load_row(d20, "scm", ["run_S9.py", "level", "--las-off", "--k1-order-gate", "on"]))
    check("R7-4 off arm with c2_setup.las_off true -> identity pass", idf["verdict"] == "pass", idf)
    idx = K.identity_scm(C.load_row(d20, "scm", ["run_S9.py", "level"]))
    check("c2_setup.las_off true but argv on arm -> identity 판정 불가", idx["verdict"] == "indeterminate", idx)
    # T4 / T5 grades from a synthetic p2_t45 document
    l2r = C.load_row(write_l2b(tmp / "l2b_t45"), "l2b", L2B_ARGV)
    import p2_t45 as T45
    doc = {"tool_gate": {"ok": True}, "regression": {"ok": True},
           "replay": {"criteria": "rev7", "out_sha256": "x", "row_key": "row folder path", "mapping_problems": [],
                      "rows": {T45.row_key(l2r.folder): {"settings_equal": True, "t4_0": True,
                                                         "T4": {"over_0p6kN": 0, "judged_samples": 10},
                                                         "T5": {"over_0p6kN": 2}}}}}
    t = K.t45_items(l2r, doc)
    check("t45 grades: T4-0 pass, T4 pass, T5 over 2 -> fail + H-7", t["T4-0"]["verdict"] == "pass"
          and t["T4"]["verdict"] == "pass" and t["T5"]["verdict"] == "fail" and "H-7" in t["T5"]["stop"], t)
    doc["regression"]["ok"] = False
    t2 = K.t45_items(l2r, doc)
    check("t45 regression failed -> S-11, 판정 불가", t2["T4"]["verdict"] == "indeterminate"
          and "S-11" in t2["T4"]["stop"], t2["T4"])
    t_p2t45(tmp, l2r, doc)


def t_p2t45(tmp, l2r, doc):
    """p2_t45 fixes (2026-11-14, user decision 19): regression rows by exact folder name, replay rows keyed
    by folder path; D-29 L2b 10 Hz bracket only after rev15 is sealed."""
    import re as _re
    import p2_t45 as T45
    doc = copy.deepcopy(doc)
    doc["regression"]["ok"] = True
    check("REG_ROWS: 18 unique exact names with stamps, VB 12 + LS 6",
          len(T45.REG_ROWS) == 18 == len(set(T45.REG_ROWS))
          and all(_re.match(r"^v5s3_(VB|LS1|LS4)_.+_\d{8}_\d{6}$", n) for n in T45.REG_ROWS)
          and sum(n.startswith("v5s3_VB_") for n in T45.REG_ROWS) == 12)
    src = REPO / T45.REG_BATCH
    if src.is_dir():
        logs = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in src.glob("*.log"))
        check("REG_ROWS: every name is a runner folder in the stored stage-3 batch row logs (source)",
              all(n in logs for n in T45.REG_ROWS), [n for n in T45.REG_ROWS if n not in logs])
    else:
        print("SKIP stage-3 batch source check (batch folder not in this checkout)")
    rr = tmp / "regroot"
    for n in T45.REG_ROWS:
        (rr / "S8" / n).mkdir(parents=True, exist_ok=True)
    newer = rr / "S8" / (T45.REG_ROWS[0].rsplit("_", 2)[0] + "_20261114_125334")
    newer.mkdir(parents=True, exist_ok=True)
    f, miss = T45.regression_folders(rr)
    check("regression: a newer folder with the same tag prefix is not picked (exact names, 18 found)",
          len(f) == 18 and not miss and newer not in f, (len(f), miss))
    shutil.rmtree(rr / "S8" / T45.REG_ROWS[5])
    r = T45.regression(REPO, rr, tmp / "reg_out")
    check("regression: one stored folder missing -> ok false (S-11), tool not run",
          r["ok"] is False and r["missing"] == [T45.REG_ROWS[5]] and "rc" not in r, r)
    d2 = copy.deepcopy(doc)
    d2["regression"] = r
    t = K.t45_items(l2r, d2)
    check("regression missing row -> T4 S-11", "S-11" in t["T4"].get("stop", ""), t["T4"])
    # replay mapping: same --only name in three runner folders -> three keys
    fs = [tmp / f"run{i}" / "E_G4_Fs8" for i in range(3)] + [tmp / "run0" / "K0_top_fup3.2_Fs0"]
    rows_rep = [{"case": p.name, "t4_0": True, "i": i} for i, p in enumerate(fs)]
    m, prob = T45.map_replay(fs, rows_rep)
    check("replay mapping: 4 folders (3 share the --only name) -> 4 keys by folder path, no problem",
          len(m) == 4 and not prob and [m[T45.row_key(p)]["i"] for p in fs] == [0, 1, 2, 3], (len(m), prob))
    m2, prob2 = T45.map_replay(fs, rows_rep[:3])
    check("replay mapping: report row count differs -> empty mapping + problem", m2 == {} and prob2, prob2)
    m3, prob3 = T45.map_replay(fs, [rows_rep[1], rows_rep[0], rows_rep[3], rows_rep[2]])
    check("replay mapping: report order does not follow the input names -> empty mapping + problem",
          m3 == {} and any("position" in p for p in prob3), prob3)
    m4, prob4 = T45.map_replay([fs[0], fs[0]], rows_rep[:2])
    check("replay mapping: repeated input folder -> empty mapping + problem", m4 == {} and prob4, prob4)
    d3 = copy.deepcopy(doc)
    d3["replay"]["mapping_problems"] = ["x"]
    check("t45_items: mapping problems -> S-11", "S-11" in K.t45_items(l2r, d3)["T4"].get("stop", ""))
    d4 = copy.deepcopy(doc)
    d4["replay"].pop("row_key")
    d4["replay"]["rows"] = {l2r.folder.name: d4["replay"]["rows"][T45.row_key(l2r.folder)]}
    check("t45_items: old name-keyed replay document -> S-11 (not used)",
          "S-11" in K.t45_items(l2r, d4)["T4"].get("stop", ""))
    # D-29: L2b row without the 1 ms crawler_normal_N
    dv = write_l2b(tmp / "l2b_v0_nocr")
    _set_npz(dv / "pads.npz", crawler_normal_N=None)
    rec = dict(np.load(dv / "record" / "record.npz"))
    fc = np.zeros((len(rec["t"]), 3))
    fc[:, 2] = np.where(rec["t"] < 23.0, 300000.0, 0.0)
    rec["F_crawler"] = fc
    np.savez(dv / "record" / "record.npz", **rec)
    _edit_result(dv, tmp / "l2b_v0_nocr_nofp", lambda r: None)   # copy without floor_plane (source missing)
    rj = json.loads((dv / "result.json").read_text(encoding="utf-8"))
    rj["floor_plane"] = {"normal_world": [0.0, 0.0, 1.0]}
    (dv / "result.json").write_text(json.dumps(rj), encoding="utf-8")
    keep = list(R.SEALED)
    try:
        R.SEALED[:] = [x for x in keep if x[0] != R.D29_RULE_FILE]
        rv = C.load_row(dv, "l2b", L2B_ARGV)
        tl, basis = C.t_lift(rv)
        check("D-29 without rev15 in the sealed list: L2b row without 1 ms crawler_normal_N -> t_lift not"
              " computed (pending rev15)",
              R.d29_l2b_bracket_enabled() is False and tl is None and basis == "bracket_10Hz_d29_pending_rev15",
              (tl, basis))
    finally:
        R.SEALED[:] = keep
    rl = C.load_row(dv, "l1r", ["run_S6C.py"])
    tl1, b1 = C.t_lift(rl)
    check("R6-B1 L1-R: same record -> 10 Hz bracket t_b", b1 == "bracket_10Hz" and tl1 is not None
          and abs(tl1 - 23.0) < 0.1 + 1e-9, (tl1, b1))
    keep = list(R.SEALED)
    try:
        check("R15-7: rev15 is in the code sealed list -> D-29 L2b 10 Hz reading on",
              R.d29_l2b_bracket_enabled() is True)
        rv2 = C.load_row(dv, "l2b", L2B_ARGV)
        tl2, b2 = C.t_lift(rv2)
        check("D-29 with rev15 sealed: L2b row -> R6-B1 10 Hz bracket (same t_b as L1-R)",
              b2 == "bracket_10Hz" and tl2 == tl1, (tl2, b2))
        rnf = C.load_row(tmp / "l2b_v0_nocr_nofp", "l2b", L2B_ARGV)
        tl3, b3 = C.t_lift(rnf)
        check("R15-3: floor_plane.normal_world missing -> source missing, t_lift not computed (판정 불가)",
              tl3 is None and b3 == "bracket_10Hz_source_missing"
              and any("normal_world" in n for n in rnf.notes), (tl3, b3, rnf.notes))
    finally:
        R.SEALED[:] = keep
    # R6-B1 / R15-3 projection on a tilted floor normal (not the world z component)
    n = np.array([0.6, 0.0, 0.8])
    rec2 = {"t": np.array([0.1, 0.2, 0.3]), "F_crawler": np.array([[0.0, 0.0, 10.0], [-8.0, 0.0, 6.0],
                                                                  [-10.0, 0.0, 0.0]])}

    class _Npz(dict):
        files = property(lambda self: list(self.keys()))
    cn, tn, why = C.bracket_crawler_normal(_Npz(rec2), {"floor_plane": {"normal_world": (2 * n).tolist()}})
    check("R15-3 normal projection: F_crawler . unit normal_world (z component would stay positive)",
          np.allclose(cn, [8.0, 0.0, -6.0]) and why == "" and np.allclose(tn, rec2["t"]), cn)
    cb, _, whyb = C.bracket_crawler_normal(_Npz({"t": rec2["t"], "F_crawler": rec2["F_crawler"][:, :2]}),
                                           {"floor_plane": {"normal_world": [0, 0, 1]}})
    check("R15-3 F_crawler not [N, 3] -> source missing", cb is None and "shape" in whyb, whyb)
    cz, _, whyz = C.bracket_crawler_normal(_Npz(rec2), {"floor_plane": {"normal_world": [0, 0, 0]}})
    check("R15-3 zero normal_world -> source missing", cz is None and "zero" in whyz, whyz)


def t_l2b(tmp):
    row = C.load_row(write_l2b(tmp / "l2b_base"), "l2b", L2B_ARGV)
    items, keys, _ = K.items_d8p(row, PARAMS, judged=True, hold=True)
    check("L2b time base: events absolute, phases + start_t_s (rev6 R6-1)",
          abs(C.loc_times(row)["first"] - 24.0) < 1e-9 and abs(C.first_phase_time(row, "ready") - 39.0) < 1e-9,
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
    # J11 (rev6 6 + rev2 D-1 + rev5 R5-B1 / B3 + rev6 R6-B7)
    import math
    dj = write_l2b(tmp / "l2b_j11")
    res = json.loads((dj / "result.json").read_text(encoding="utf-8"))
    tw = 43.6 + 0.1 * math.log(0.005 / 1e-4) + 0.05 + 0.1
    res["controller_meta"]["two_pressure"] = {
        "settings": {"lock_window_valve_tau_s": 0.1, "lock_window_eps_m_s": 1e-4, "lock_window_closing_delay_s": 0.05},
        "fallback_lock_log": [{"leg": "FL", "t_start_s": 43.6, "window_end_s": tw}]}
    (dj / "result.json").write_text(json.dumps(res), encoding="utf-8")
    ev = json.loads((dj / "controller_events.json").read_text(encoding="utf-8"))
    ev.append("C2Event(t_s=43.0, name='WARN_ROD_PRESSURE_FALLBACK:FL')")
    (dj / "controller_events.json").write_text(json.dumps(ev), encoding="utf-8")
    rj = C.load_row(dj, "l2b", L2B_ARGV)
    j = K.j11_item(rj, res["controller_meta"]["two_pressure"])
    check("J11: window end recomputed = log to 1e-12, plant unlocked after t_w -> n_late 1, H-7",
          j["log_matches"][0]["match"] and j["verdict"] == "fail" and j["stop"].startswith("H-7")
          and j["n_late"][0] == 1, {k: j.get(k) for k in ("log_matches", "n_late", "verdict", "stop")})
    j2 = K.j11_item(rj, res["controller_meta"]["two_pressure"], ls=True)
    check("J11 LS row (R9-4 ls True) -> L-e stop (rev5 R5-B3)", j2["stop"].startswith("L-e"), j2.get("stop"))
    rj.case = "E_G4_Fs8_LS1"
    j2b = K.j11_item(rj, res["controller_meta"]["two_pressure"], ls=False)
    check("R9-4 name token not used: case '..._LS1' with ls False -> H-7", j2b["stop"].startswith("H-7"),
          j2b.get("stop"))
    j2c = K.j11_item(rj, res["controller_meta"]["two_pressure"], ls=None)
    check("R9-4 LS not judgeable + n_late > 0 -> stop, text 'LS 판별 불가'", "LS 판별 불가" in j2c["stop"]
          and j2c["verdict"] == "fail", j2c.get("stop"))
    res["controller_meta"]["two_pressure"]["fallback_lock_log"][0]["window_end_s"] = tw + 1e-6
    j3 = K.j11_item(rj, res["controller_meta"]["two_pressure"])
    check("J11 window end mismatch -> S-11", "S-11" in j3.get("stop", ""), j3.get("stop"))
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


def t_seal(tmp, rules_repo=None):
    """Copies of the sealed files into a temporary repo. A file this checkout does not have (rev15 before the
    seal branch is merged) is copied from `--rules-repo` (the seal worktree); without it the test is skipped."""
    repo = tmp / "repo"
    for rel, _, _ in R.SEALED:
        src_root = REPO if (REPO / rel).exists() else rules_repo
        if src_root is None or not (Path(src_root) / rel).exists():
            print(f"SKIP seal tests ({rel} not in this checkout; give --rules-repo <seal worktree>)")
            return
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(src_root) / rel, repo / rel)
        if rel in R.RAW_ONLY:
            sc = Path(rel).with_suffix(".sha256")
            shutil.copyfile(Path(src_root) / sc, repo / sc)
    ok = R.seal_check(repo)
    check("seal: copies match", ok["ok"], [r["status"] for r in ok["sealed"]])
    rel7 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.md"
    check("seal: rev7 listed, raw only, e81f7d31 (rev7 R7-7)",
          rel7 in R.RAW_ONLY and any(r == rel7 and w.startswith("e81f7d31") for r, w, _ in R.SEALED))
    sc7 = repo / Path(rel7).with_suffix(".sha256")
    keep = sc7.read_bytes()
    sc7.write_text("0" * 64 + "  v5_resume_4368_rules_rev7.md\n", encoding="utf-8")
    s5 = R.seal_check(repo)
    st5 = {r["file"]: r["status"] for r in s5["sealed"]}
    check("seal: rev7 .sha256 record differs -> S-1 (sidecar_mismatch)", not s5["ok"] and st5[rel7] == "sidecar_mismatch",
          st5[rel7])
    sc7.unlink()
    s6 = R.seal_check(repo)
    check("seal: rev7 .sha256 record missing -> S-1", not s6["ok"]
          and {r["file"]: r["status"] for r in s6["sealed"]}[rel7] == "sidecar_missing")
    sc7.write_bytes(keep)
    rel8 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.md"
    check("seal: rev8 listed, raw only, 3ecafaaf (rev8 R8-4)",
          rel8 in R.RAW_ONLY and any(r == rel8 and w.startswith("3ecafaaf") for r, w, role in R.SEALED))
    check("seal: rev8 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel8] == "match"
          and R.sidecar_sha(repo / rel8) == next(w for r, w, _ in R.SEALED if r == rel8))
    sc8 = repo / Path(rel8).with_suffix(".sha256")
    keep8 = sc8.read_bytes()
    sc8.write_text("f" * 64 + "  v5_resume_4368_rules_rev8.md\n", encoding="utf-8")
    s8 = R.seal_check(repo)
    check("seal: rev8 .sha256 record differs -> S-1 (sidecar_mismatch)",
          not s8["ok"] and {r["file"]: r["status"] for r in s8["sealed"]}[rel8] == "sidecar_mismatch")
    sc8.unlink()
    s8b = R.seal_check(repo)
    check("seal: rev8 .sha256 record missing -> S-1",
          not s8b["ok"] and {r["file"]: r["status"] for r in s8b["sealed"]}[rel8] == "sidecar_missing")
    sc8.write_bytes(keep8)
    p8 = repo / rel8
    keep_md = p8.read_bytes()
    p8.write_bytes(keep_md + b"\n")
    s8c = R.seal_check(repo)
    check("seal: rev8 file changed (.sha256 intact) -> S-1 (mismatch)",
          not s8c["ok"] and {r["file"]: r["status"] for r in s8c["sealed"]}[rel8] == "mismatch")
    p8.write_bytes(keep_md)
    rel9 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev9.md"
    check("seal: rev9 listed, raw only, 4cf7843c (rev9 R9-8)",
          rel9 in R.RAW_ONLY and any(r == rel9 and w.startswith("4cf7843c") for r, w, role in R.SEALED))
    rel10 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.md"
    check("seal: rev10 listed, raw only, 62a0bd8d (rev10 R10-3)",
          rel10 in R.RAW_ONLY and any(r == rel10 and w.startswith("62a0bd8d") for r, w, role in R.SEALED))
    check("seal: rev10 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel10] == "match"
          and R.sidecar_sha(repo / rel10) == next(w for r, w, _ in R.SEALED if r == rel10))
    sc10 = repo / Path(rel10).with_suffix(".sha256")
    keep10 = sc10.read_bytes()
    sc10.write_text("d" * 64 + "  v5_resume_4368_rules_rev10.md\n", encoding="utf-8")
    check("seal: rev10 .sha256 record differs -> S-1 (sidecar_mismatch)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel10] == "sidecar_mismatch")
    sc10.unlink()
    check("seal: rev10 .sha256 record missing -> S-1",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel10] == "sidecar_missing")
    sc10.write_bytes(keep10)
    p10 = repo / rel10
    keep10md = p10.read_bytes()
    p10.write_bytes(keep10md + b" ")
    s10 = R.seal_check(repo)
    check("seal: rev10 file changed -> S-1 (mismatch)", not s10["ok"]
          and {r["file"]: r["status"] for r in s10["sealed"]}[rel10] == "mismatch")
    p10.write_bytes(keep10md)
    rel11 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev11.md"
    check("seal: rev11 listed, raw only, 9bac4524 (rev11 R11-7)",
          rel11 in R.RAW_ONLY and any(r == rel11 and w.startswith("9bac4524") for r, w, role in R.SEALED))
    check("seal: rev11 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel11] == "match"
          and R.sidecar_sha(repo / rel11) == next(w for r, w, _ in R.SEALED if r == rel11))
    sc11 = repo / Path(rel11).with_suffix(".sha256")
    keep11 = sc11.read_bytes()
    sc11.write_text("c" * 64 + "  v5_resume_4368_rules_rev11.md\n", encoding="utf-8")
    check("seal: rev11 .sha256 record differs -> S-1 (sidecar_mismatch)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel11] == "sidecar_mismatch")
    sc11.unlink()
    check("seal: rev11 .sha256 record missing -> S-1",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel11] == "sidecar_missing")
    sc11.write_bytes(keep11)
    p11 = repo / rel11
    keep11md = p11.read_bytes()
    p11.write_bytes(keep11md.replace(b"\n", b"\r\n"))
    s11 = R.seal_check(repo)
    check("seal: rev11 CRLF copy -> S-1 (raw only)", not s11["ok"]
          and {r["file"]: r["status"] for r in s11["sealed"]}[rel11] == "mismatch")
    p11.write_bytes(keep11md)
    rel12 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev12.md"
    check("seal: rev12 listed, raw only, 78f1f99b (rev12 R12-6)",
          rel12 in R.RAW_ONLY and any(r == rel12 and w.startswith("78f1f99b") for r, w, role in R.SEALED))
    rel15 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev15.md"
    check("seal: rev15 listed, raw only, 0162561c; rev13 / rev14 not listed (R15-7)",
          rel15 in R.RAW_ONLY and any(r == rel15 and w.startswith("0162561c") for r, w, role in R.SEALED)
          and not any(r.endswith(("rules_rev13.md", "rules_rev14.md")) for r, _, _ in R.SEALED))
    # rev18 R18-1 (다): rev16..rev18 in the Chrono tool list, raw only, seal sha = .sha256 first token; rev18 wins
    want16 = {"16": "b3899194", "17": "9400660e", "18": "3693a69c", "19": "7f87b8bb", "20": "615a8fbd", "21": "ecd70949", "22": "a48a81f9", "23": "fa72e172", "24": "f475cf77", "25": "c0b778fd"}
    for n, pre in want16.items():
        reln = f"06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev{n}.md"
        check(f"seal: rev{n} listed, raw only, {pre}, match, = .sha256 first token (R18-1)",
              reln in R.RAW_ONLY and any(r == reln and w.startswith(pre) for r, w, _ in R.SEALED)
              and {r["file"]: r["status"] for r in ok["sealed"]}[reln] == "match"
              and R.sidecar_sha(repo / reln) == next(w for r, w, _ in R.SEALED if r == reln))
        pn = repo / reln
        keepn = pn.read_bytes()
        pn.write_bytes(keepn + b"x")
        check(f"seal: rev{n} edited -> S-1", not R.seal_check(repo)["ok"])
        pn.write_bytes(keepn)
    rel25 = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev25.md"
    check("seal: only rev25 wins (latest sealed revision)",
          [r for r, w, role in R.SEALED if "wins" in role] == [rel25])
    check("seal: rev15 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel15] == "match"
          and R.sidecar_sha(repo / rel15) == next(w for r, w, _ in R.SEALED if r == rel15))
    sc15 = repo / Path(rel15).with_suffix(".sha256")
    keep15 = sc15.read_bytes()
    sc15.write_text("a" * 64 + "  v5_resume_4368_rules_rev15.md\n", encoding="utf-8")
    check("seal: rev15 .sha256 record differs -> S-1 (sidecar_mismatch)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel15] == "sidecar_mismatch")
    sc15.unlink()
    check("seal: rev15 .sha256 record missing -> S-1",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel15] == "sidecar_missing")
    sc15.write_bytes(keep15)
    p15 = repo / rel15
    keep15md = p15.read_bytes()
    p15.write_bytes(keep15md.replace(b"\n", b"\r\n"))
    check("seal: rev15 CRLF copy -> S-1 (raw only)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel15] == "mismatch")
    p15.unlink()
    s15 = R.seal_check(repo)
    check("seal: rev15 file missing -> S-1", not s15["ok"]
          and {r["file"]: r["status"] for r in s15["sealed"]}[rel15] == "missing")
    p15.write_bytes(keep15md)
    check("seal: rev15 restored -> all match", R.seal_check(repo)["ok"])
    check("seal: rev12 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel12] == "match"
          and R.sidecar_sha(repo / rel12) == next(w for r, w, _ in R.SEALED if r == rel12))
    sc12 = repo / Path(rel12).with_suffix(".sha256")
    keep12 = sc12.read_bytes()
    sc12.write_text("b" * 64 + "  v5_resume_4368_rules_rev12.md\n", encoding="utf-8")
    check("seal: rev12 .sha256 record differs -> S-1 (sidecar_mismatch)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel12] == "sidecar_mismatch")
    sc12.unlink()
    check("seal: rev12 .sha256 record missing -> S-1",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel12] == "sidecar_missing")
    sc12.write_bytes(keep12)
    p12 = repo / rel12
    keep12md = p12.read_bytes()
    p12.write_bytes(keep12md + b"x")
    check("seal: rev12 file changed -> S-1 (mismatch)",
          {r["file"]: r["status"] for r in R.seal_check(repo)["sealed"]}[rel12] == "mismatch")
    p12.write_bytes(keep12md)
    check("seal: rev9 raw sha = code seal sha = .sha256 first token",
          {r["file"]: r["status"] for r in ok["sealed"]}[rel9] == "match"
          and R.sidecar_sha(repo / rel9) == next(w for r, w, _ in R.SEALED if r == rel9))
    sc9 = repo / Path(rel9).with_suffix(".sha256")
    keep9 = sc9.read_bytes()
    sc9.write_text("e" * 64 + "  v5_resume_4368_rules_rev9.md\n", encoding="utf-8")
    s9 = R.seal_check(repo)
    check("seal: rev9 .sha256 record differs -> S-1 (sidecar_mismatch)",
          not s9["ok"] and {r["file"]: r["status"] for r in s9["sealed"]}[rel9] == "sidecar_mismatch")
    sc9.unlink()
    s9b = R.seal_check(repo)
    check("seal: rev9 .sha256 record missing -> S-1",
          not s9b["ok"] and {r["file"]: r["status"] for r in s9b["sealed"]}[rel9] == "sidecar_missing")
    sc9.write_bytes(keep9)
    p9 = repo / rel9
    keep9md = p9.read_bytes()
    p9.write_bytes(keep9md.replace(b"\n", b"\r\n"))
    s9c = R.seal_check(repo)
    check("seal: rev9 CRLF copy -> S-1 (raw only)",
          not s9c["ok"] and {r["file"]: r["status"] for r in s9c["sealed"]}[rel9] == "mismatch")
    p9.unlink()
    s9d = R.seal_check(repo)
    check("seal: rev9 file missing -> S-1", not s9d["ok"]
          and {r["file"]: r["status"] for r in s9d["sealed"]}[rel9] == "missing")
    p9.write_bytes(keep9md)
    check("seal: restored copies match again", R.seal_check(repo)["ok"])
    rel_a ="06_analysis/02_control/verif_matrix/d1_selection_rules.md"
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
    if not CLI_REPO and not R.seal_check(REPO)["ok"]:
        print("SKIP CLI tests (seal check of this checkout fails: a sealed rule file is missing; give --rules-repo)")
        return
    bdir = tmp / "batch_P2TEST"
    bdir.mkdir(exist_ok=True)
    sp = scm_spec()
    write_scm(bdir / "rowA", sp)
    write_scm(bdir / "rowB", sp)
    for name in ("rowA", "rowB"):   # rev24 CD-4: P3-7 reads record.npz and c2_soil (no S-1 window -> no LOC)
        write_p37_record(bdir / name, sp, [])
    v0 = ["--expect-controller", "final_C4G2_LAS_K1"]   # rev25 CD-1: non-③ tag -> J-P3 해당 없음(③ 끔)
    batch = {"cases": [{"case": "rowA", "argv": ["python", "run_S9.py", "level"] + v0, "criteria_id": "C-3",
                        "code_at_launch": CAL},
                       {"case": "rowB", "argv": ["python", "run_S9.py", "level"] + v0, "criteria_id": "C-3",
                        "code_at_launch": CAL},
                       {"case": "gs", "argv": ["run_S9.py"], "criteria_id": "C-3", "r4368": {"role": "gs"}}]}
    (bdir / "batch.json").write_text(json.dumps(batch), encoding="utf-8")
    out = tmp / "out_c3.json"
    proc = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-3", "--git-at-start", GREF[:7],
                           "--batch", str(bdir / "batch.json"), "--out", str(out)],
                          capture_output=True, text=True, encoding="utf-8")
    last = json.loads(proc.stdout.strip().splitlines()[-1])
    import hashlib
    check("CLI C-3 synthetic: exit 0, 2 rows, 통과, out_sha256 = file sha",
          proc.returncode == 0 and last.get("rows") == 2 and last.get("status") == "통과"
          and last.get("out_sha256") == hashlib.sha256(out.read_bytes()).hexdigest(), proc.stdout[-500:] + proc.stderr[-500:])
    o1 = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    l11 = (o1.get("bundle_result") or {}).get("cd11_item_list") or {}
    check("CLI C-3 rev24: CD-11 list with 2 rows (P3-7 listed), no CD-7 empty reason, no stop",
          len(l11.get("rows") or []) == 2 and not l11.get("problems")
          and any(x["common_id"] == "P3-7" for x in l11["rows"][0]["items"])
          and (o1.get("bundle_result") or {}).get("cd7_empty_reasons") == [], l11.get("problems"))
    out1p = tmp / "o1p.json"
    subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-1",
                    "--git-at-start", GREF[:7], "--batch", str(bdir / "batch.json"), "--out", str(out1p),
                    "--s8c-dir", str(tmp / "s8c_empty")], capture_output=True, text=True, encoding="utf-8")
    pv = (json.loads(out1p.read_text(encoding="utf-8")) if out1p.exists() else {}).get("cd2_judge_provenance") or {}
    check("CLI C-1 with --s8c-dir: CD-2 (1) provenance recorded (judge code = b9f5707, ok)",
          pv.get("ok") is True and pv.get("reference") == "b9f5707", pv)
    proc2 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-1", "--git-at-start", GREF[:7],
                            "--batch", str(bdir / "batch.json"), "--out", str(tmp / "o2.json"),
                            "--row-dir", "x=y"], capture_output=True, text=True, encoding="utf-8")
    last2 = json.loads(proc2.stdout.strip().splitlines()[-1])
    check("CLI C-1 on a batch with no C-1 rows -> S-15, exit 1", proc2.returncode == 1
          and any("S-15" in s for s in last2.get("stops", [])), proc2.stdout[-300:])
    proc3 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-3", "--git-at-start", GREF[:7],
                            "--batch", str(tmp / "missing.json"), "--out", str(tmp / "o3.json")],
                           capture_output=True, text=True, encoding="utf-8")
    check("CLI missing batch -> exit 3 or 2 (input)", proc3.returncode in (2, 3), proc3.returncode)
    # gs-load on the G-S row (read-only, no verdicts in the output)
    out4 = tmp / "gs_load.json"
    proc4 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "gs-load", *CLI_REPO,
                            "--batch", str(bdir / "batch.json"), "--out", str(out4), "--git-at-start", GREF[:7],
                            "--row-dir", f"gs={bdir / 'rowA'}"], capture_output=True, text=True, encoding="utf-8")
    last4 = json.loads(proc4.stdout.strip().splitlines()[-1])
    txt4 = out4.read_text(encoding="utf-8") if out4.exists() else ""
    check("CLI gs-load: exit 0, 1 G-S row, no verdict / status keys in output",
          proc4.returncode == 0 and last4.get("rows") == 1 and '"verdict"' not in txt4
          and '"bundle_result"' not in txt4, proc4.stdout[-400:] + proc4.stderr[-400:])
    g4 = json.loads(txt4) if txt4 else {}
    gi = g4.get("rev9_R9_8_gs_items") or {}
    check("CLI gs-load rev9 R9-8 items: S-2 0, law_locked key absent counted, rev9 seal match",
          gi.get("r9_1_s2_rows") == 0 and gi.get("r9_2_rows_per_item", {}).get("key") == 1
          and gi.get("rev9_seal") == "match" and gi.get("r9_6_input_absent_rows") == 1, gi)
    g11 = g4.get("rev11_gs_items") or {}
    check("CLI gs-load rev11 items: G-S row without code_at_launch -> S-12 counted, no grades written (R11-5),"
          " rev11 seal match, git_at_start given",
          g11.get("r11_4_code_at_launch_missing_rows") == 1 and g11.get("r11_4_s12_rows") == 1
          and g11.get("r11_5_grades_written") is False
          and g11.get("rev11_seal") == "match" and g11.get("git_at_start") == GREF[:7], g11)
    proc4c = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "gs-load", *CLI_REPO,
                             "--batch", str(bdir / "batch.json"), "--out", str(tmp / "gs_load_nogit.json"),
                             "--row-dir", f"gs={bdir / 'rowA'}"], capture_output=True, text=True, encoding="utf-8")
    check("CLI gs-load without --git-at-start -> input error, exit 2 (rev12 R12-3)", proc4c.returncode == 2,
          proc4c.stdout[-300:])
    g10 = g4.get("rev10_R10_2_gs_items") or {}
    check("CLI gs-load rev10 R10-2 items: unstamped folder without batch key -> batch name unknown, S-11 row 1,"
          " rev10 seal match",
          g10.get("r10_1b_rows_per_case", {}).get("batch_name_unknown") == 1 and g10.get("r10_2_s11_rows") == 1
          and g10.get("rev10_seal") == "match", g10)
    proc4b = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "gs-load", *CLI_REPO,
                             "--batch", str(bdir / "batch.json"), "--out", str(tmp / "gs_load_noman.json"),
                             "--git-at-start", GREF[:7],
                             "--manifest", str(tmp / "no_manifest.json"), "--row-dir", f"gs={bdir / 'rowA'}"],
                            capture_output=True, text=True, encoding="utf-8")
    check("CLI gs-load without the manifest -> input error, exit 2 (R10-1b: G-S failure)",
          proc4b.returncode == 2, proc4b.stdout[-300:])
    # R9-1 in the CLI: one row with expect_controller.ok false -> bundle stop S-2, exit 1
    bko = tmp / "batch_P2KO"
    bko.mkdir(exist_ok=True)
    write_scm(bko / "rowA", sp)
    write_scm(bko / "rowB", sp)
    rb = json.loads((bko / "rowB" / "result.json").read_text(encoding="utf-8"))
    rb["c2_setup"]["expect_controller"]["ok"] = False
    (bko / "rowB" / "result.json").write_text(json.dumps(rb), encoding="utf-8")
    (bko / "batch.json").write_text(json.dumps({"cases": batch["cases"][:2]}), encoding="utf-8")
    proc5 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-3", "--git-at-start", GREF[:7],
                            "--batch", str(bko / "batch.json"), "--out", str(tmp / "o5.json")],
                           capture_output=True, text=True, encoding="utf-8")
    last5 = json.loads(proc5.stdout.strip().splitlines()[-1])
    check("CLI R9-1: expect_controller.ok false on one row -> S-2 stop, 판정 불가, exit 1",
          proc5.returncode == 1 and last5.get("status") == "판정 불가"
          and any("S-2" in s and "rowB" in s for s in last5.get("stops", [])), proc5.stdout[-500:])
    # R9-4 in the CLI: C-5 rows, LS from the manifest + batch.json v5_setting
    b5 = tmp / "batch_P2C5_20261113_120000"
    b5.mkdir(exist_ok=True)
    write_scm(b5 / "X_LS1", sp)
    write_scm(b5 / "Y", sp)
    argv5 = ["python", "run_S9.py", "level", "--extend-start-tracked", "--expect-controller", "final_C4G2_P3_LAS_K1"]
    (b5 / "batch.json").write_text(json.dumps({"batch": "P2C5", "cases": [
        {"case": "X_LS1", "argv": argv5, "criteria_id": "C-5", "v5_setting": "LS1", "code_at_launch": CAL},
        {"case": "Y", "argv": argv5, "criteria_id": "C-5", "v5_setting": "VB", "code_at_launch": CAL}]}),
        encoding="utf-8")
    man_p = tmp / "manifest_p2c5.json"
    man_p.write_text(json.dumps({"batches": {"P2C5": {"rows": [{"case": "X_LS1", "v5_setting": "LS1"},
                                                                {"case": "Y", "v5_setting": "LS4"}]}}}),
                     encoding="utf-8")
    out6 = tmp / "o6.json"
    proc6 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-5", "--git-at-start", GREF[:7],
                            "--batch", str(b5 / "batch.json"), "--manifest", str(man_p), "--out", str(out6)],
                           capture_output=True, text=True, encoding="utf-8")
    o6 = json.loads(out6.read_text(encoding="utf-8")) if out6.exists() else {}
    ls6 = (o6.get("bundle_result") or {}).get("rev9_R9_4_ls")
    check("CLI C-5 R9-4: LS1/LS1 -> LS, VB/LS4 -> 판정 불가; law_locked missing -> R9-5 stops; exit 1",
          proc6.returncode == 1 and ls6 == {"ls_rows": 1, "not_ls_rows": 0, "not_judgeable_rows": 1}
          and sum("R9-5" in s for s in (o6.get("bundle_result") or {}).get("stops", [])) == 2,
          (proc6.returncode, ls6, proc6.stdout[-300:] + proc6.stderr[-300:]))
    proc7 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", *CLI_REPO, "--bundle", "C-5", "--git-at-start", GREF[:7],
                            "--batch", str(b5 / "batch.json"), "--manifest", str(tmp / "no_manifest.json"),
                            "--out", str(tmp / "o7.json")], capture_output=True, text=True, encoding="utf-8")
    check("CLI C-5 without the manifest -> input error, exit 2", proc7.returncode == 2, proc7.stdout[-300:])


def t_resolve(tmp):
    """Row folders (path 2's own reading of the run records; rev7 R7-5 is the path 1 sentence)."""
    root = tmp / "res"
    bdir = tmp / "batch_RES"
    bdir.mkdir(parents=True, exist_ok=True)
    tag, only = "r4368_D1C2_x", "D1C2_x"
    for stamp in ("20261113_010000", "20261113_020000"):
        d = root / "S8" / f"{tag}_{stamp}" / only
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text("{}", encoding="utf-8")
    case = {"case": "D1C2_x", "argv": ["run_S8C.py", "run", "--only", only, "--tag", tag]}
    try:
        p2_chrono.resolve_dir(case, bdir, root, {})
        check("resolve: no row log, two tag folders -> input error", False)
    except C.InputError:
        check("resolve: no row log, two tag folders -> input error", True)
    want = root / "S8" / f"{tag}_20261113_020000"
    (bdir / "D1C2_x.log").write_text(f"D1C2_x: ok 1.0s\nbatch wall 1.1 s -> {want}\n", encoding="utf-8")
    d, how = p2_chrono.resolve_dir(case, bdir, root, {})
    check("resolve: row log runner line -> case_log", how == "case_log" and d == want / only, (d, how))
    moved = tmp / "elsewhere" / "07_results" / "S8" / f"{tag}_20261113_020000"
    (bdir / "D1C2_x.log").write_text(f"batch wall 1.1 s -> {moved}\n", encoding="utf-8")
    d2, how2 = p2_chrono.resolve_dir(case, bdir, root, {})
    check("resolve: logged folder moved -> same relative path under results root (case_log_relocated)",
          how2 == "case_log_relocated" and d2 == want / only, (d2, how2))
    (bdir / "D1C2_x.log").write_text(f"batch wall 1.1 s -> {root / 'S8' / 'other_20261113'}\n", encoding="utf-8")
    try:
        p2_chrono.resolve_dir(case, bdir, root, {})
        check("resolve: logged folder without the tag -> input error", False)
    except C.InputError:
        check("resolve: logged folder without the tag -> input error", True)
    (bdir / "D1C2_x.log").unlink()
    shutil.rmtree(root / "S8" / f"{tag}_20261113_010000")
    try:
        p2_chrono.resolve_dir(case, bdir, root, {})
        check("R12-5: no row log, no progress.log, unstamped batch folder -> no window, input error", False)
    except C.InputError as ex:
        check("R12-5: no row log, no progress.log, unstamped batch folder -> no window, input error",
              "window" in str(ex), ex)
    (bdir / "progress.log").write_text(
        "# batch X\nSTART D1C2_x 2026-11-13T01:59:59 pid=1 est_s=9999 pool=pcore\n"
        "END D1C2_x 2026-11-13T02:05:00 rc=0 wall_s=301\n", encoding="utf-8")
    d3, how3 = p2_chrono.resolve_dir(case, bdir, root, {})
    check("R12-5: no row log, progress.log START..END +-2 s -> time_window, one folder",
          how3 == "time_window" and d3 == want / only, (d3, how3))
    sup = root / "S8" / f"x{tag}_20261113_020001" / only
    sup.mkdir(parents=True, exist_ok=True)
    (sup / "result.json").write_text("{}", encoding="utf-8")
    d3b, _ = p2_chrono.resolve_dir(case, bdir, root, {})
    check("R12-5: a tag containing <tag> (x<tag>_<stamp>) is not a candidate (exact name)", d3b == want / only, d3b)
    dup = root / "S8" / f"{tag}_20261113_020400" / only
    dup.mkdir(parents=True, exist_ok=True)
    (dup / "result.json").write_text("{}", encoding="utf-8")
    try:
        p2_chrono.resolve_dir(case, bdir, root, {})
        check("R12-5: two folders in the window -> input error", False)
    except C.InputError:
        check("R12-5: two folders in the window -> input error", True)
    shutil.rmtree(dup.parent)
    (bdir / "progress.log").write_text("START D1C2_x 2026-11-13T02:00:02\nEND D1C2_x 2026-11-13T02:05:00\n",
                                       encoding="utf-8")
    d3d, _ = p2_chrono.resolve_dir(case, bdir, root, {})
    check("R12-5: folder stamp exactly 2 s before START is inside (pad +-2 s)", d3d == want / only, d3d)
    (bdir / "progress.log").write_text("START D1C2_x 2026-11-13T02:00:04\nEND D1C2_x 2026-11-13T02:05:00\n",
                                       encoding="utf-8")
    try:
        p2_chrono.resolve_dir(case, bdir, root, {})
        check("R12-5: folder stamps 3-4 s before START -> 0 candidates, input error", False)
    except C.InputError:
        check("R12-5: folder stamps 3-4 s before START -> 0 candidates, input error", True)
    (bdir / "progress.log").unlink()
    sb = tmp / "batch_RES2_20261113_020000"
    sb.mkdir(exist_ok=True)
    try:
        p2_chrono.resolve_dir(dict(case, est_s=600), sb, root, {})
        check("R12-5: no START..END, stamped folder, est_s only (no wall_s) -> input error (est_s not used)", False)
    except C.InputError:
        check("R12-5: no START..END, stamped folder, est_s only (no wall_s) -> input error (est_s not used)", True)
    d4, how4 = p2_chrono.resolve_dir(dict(case, wall_s=0.5), sb, root, {})
    check("R12-5: batch folder stamp + wall_s +-2 s -> time_window", how4 == "time_window" and d4 == want / only,
          (d4, how4))
    # S6 (L1-R) names: <base>_<tag>_L1R_<stamp>; <tag>_check_L1R_ is not a candidate
    t6, o6 = "r4368gs_D1C1_top", "D1C1_top"
    for nm6 in (f"bundleC_d1c1_{t6}_L1R_20261113_020000", f"bundleC_d1c1_{t6}_check_L1R_20261113_020000",
                f"bundleC_d1c1_{t6}x_L1R_20261113_020000"):
        q = root / "S6" / nm6 / o6
        q.mkdir(parents=True, exist_ok=True)
        (q / "result.json").write_text("{}", encoding="utf-8")
    c6 = {"case": "D1C1_top", "argv": ["run_S6C.py", "--only", o6, "--tag", t6], "wall_s": 10.0}
    d6, how6 = p2_chrono.resolve_dir(c6, sb, root, {})
    check("R12-5 S6: exact _<tag>_L1R_<stamp>, _check_L1R_ and <tag>x excluded -> one folder",
          how6 == "time_window" and d6 == root / "S6" / f"bundleC_d1c1_{t6}_L1R_20261113_020000" / o6, (d6, how6))
    plc = p2_chrono.placement_record({"pool": "pcore", "planned_pool": "pcore", "placement_applied": {"mask": "0xFF"},
                                      "argv": []},
                                     {"placement": {"affinity_mask_process": "0xFF", "affinity_mask_ok": False}},
                                     {"affinity_masks": {"pcore": "0xFF"}})
    check("R7-6 placement record: mask keys copied, affinity_mask_ok false -> note",
          plc["affinity_mask_process"] == "0xFF" and plc["batch_affinity_masks"] == {"pcore": "0xFF"}
          and any("affinity_mask_ok" in n for n in plc["notes"]), plc)


# ------------------------------------------------------------------ rev18 R18-2: 427.9 safe stop (S-01..04)
def write_record(folder: Path, t0, t_end, F=50000.0, u=0.0, edits=()):
    """record/record.npz (10 Hz control rows): F_cyl, u_applied; edits = (t_a, t_b, leg, F, u)."""
    t = np.round(np.arange(t0 + 0.1, t_end + 1e-9, 0.1), 6)
    Fc = np.full((len(t), 4), F)
    ua = np.full((len(t), 4), u)
    for a, b, leg, f, uu in edits:
        sel = (t >= a - 1e-9) & (t <= b + 1e-9)
        Fc[sel, leg] = f
        ua[sel, leg] = uu
    (folder / "record").mkdir(parents=True, exist_ok=True)
    np.savez(folder / "record" / "record.npz", t=t, F_cyl=Fc, u_applied=ua)


def stop_spec(reason="soil"):
    sp = scm_spec()
    sp.update(phases=[(8.1, "check"), (12.0, "touch"), (20.0, "level"), (40.0, "fault")], recontacts=[],
              events=[(24.5, C.R.EVENT_LOC), (40.0, "WARN_LIFT_STROKE_LIMITED:RL"),
                      (40.0, f"FAULT_LIFT_STROKE_LIMIT:{reason}:RL")])
    return sp


def stop_row(tmp, name, sp=None, rec_edits=(), record=True, pad_dip=None):
    d = write_scm(tmp / name, sp or stop_spec())
    if record:
        write_record(d, 8.0, 60.0, u=1e-3, edits=rec_edits)
    if pad_dip is not None:
        z = dict(np.load(d / "step_series.npz"))
        t = z["t_s"]
        pad = z["scm_pad_normal_N"].copy()
        a, b, leg = pad_dip
        pad[(t >= a) & (t <= b), leg] = 0.0
        _set_npz(d / "step_series.npz", scm_pad_normal_N=pad)
    return C.load_row(d, "scm", ["run_S9.py", "level"])


def t_safe_stop(tmp):
    import p2_b_c2 as B2
    import p2_b_c3 as B3
    A = PARAMS["head_area_m2"][0]
    row = stop_row(tmp, "ss_ok")
    it, keys, _ = K.items_p3(row, PARAMS, R.READY_SLOPE_S, ready_judged=True, g6=False, allow_stop=True)
    ss = it.get("safe_stop_427_9") or {}
    check("427.9: stop event FAULT_LIFT_STROKE_LIMIT:soil:RL, conditions 1-5 true -> allowed_stop",
          ss.get("class") == "allowed_stop" and all(v is True for v in ss["conditions"].values())
          and ss["stop_reason"] == "soil", ss)
    check("R19-1: grade by conditions 1-5 only: P3-1..P3-9 / FAULT0 / P3-6 record only, identity + K1 + 427.9 judged",
          set(keys) == {"identity", "K1_class", "safe_stop_427_9"} and it["P3-1"].get("record_only")
          and it["FAULT0"].get("record_only") and set(ss["recorded_items"]) >= {"P3-1", "P3-4", "P3-5", "P3-6", "FAULT0"},
          keys)
    check("427.9 values kept per row: lift samples from LEVEL start, moving max bar (R18-4), saturation rows",
          ss["values"]["leg_lift_samples_from_level_start"] == [0, 0, 0, 0] and ss["values"]["moving_max_bar"] is not None
          and ss["values"]["saturation_rows_per_leg"] == [0, 0, 0, 0] and abs(ss["t_level_start_s"] - 20.0) < 1e-6,
          ss["values"])
    check("R19-1: allowed_stop row (no READY) -> row 통과 (no READY item graded)", C.row_status(it, keys) == "통과",
          C.row_status(it, keys))
    sp_first = dict(stop_spec(), events=[(24.5, C.R.EVENT_LOC), (30.0, "FAULT_OTHER:FL")] + stop_spec()["events"][1:])
    cases = [
        ("1 reason not soil", stop_row(tmp, "ss_c1", stop_spec("guard")), "1_stop_reason_soil"),
        ("1 first FAULT* is another fault", stop_row(tmp, "ss_c1b", sp_first), "1_stop_reason_soil"),
        ("2 FAULT_STROKE_END", stop_row(tmp, "ss_c2", dict(stop_spec(), events=stop_spec()["events"]
                                                          + [(41.0, "FAULT_STROKE_END:RL")])), "2_no_fault_stroke_end"),
        ("3 pad normal <= 0 after t_D", stop_row(tmp, "ss_c3", pad_dip=(30.0, 30.01, 2)),
         "3_no_leg_lift_from_level_start"),
        ("3 pad normal <= 0 after LEVEL start, before t_D", stop_row(tmp, "ss_c3b", pad_dip=(21.0, 21.01, 2)),
         "3_no_leg_lift_from_level_start"),
        ("4 no departure t_D -> false", stop_row(tmp, "ss_c4b", dict(stop_spec(), crawler=[])),
         "4_min_after_departure_ge_Fmin"),
        ("4 F_cyl < F_min after t_D", stop_row(tmp, "ss_c4", dict(stop_spec(), dips=[(1, 35.0, 35.002, FMIN - 100.0)])),
         "4_min_after_departure_ge_Fmin"),
        ("5 moving 190 bar", stop_row(tmp, "ss_c5", rec_edits=[(30.0, 30.0, 0, 190e5 * A, 1e-3)]),
         "5_moving_le_180bar_saturation0"),
        ("5 saturation (extending >= 210 bar)", stop_row(tmp, "ss_c5s", rec_edits=[(30.0, 30.0, 0, 215e5 * A, 1e-3)]),
         "5_moving_le_180bar_saturation0"),
    ]
    for lab, r, cond in cases:
        i2, k2, _ = K.items_p3(r, PARAMS, R.READY_SLOPE_S, ready_judged=True, g6=False, allow_stop=True)
        s2 = i2.get("safe_stop_427_9") or {}
        others = [v for k, v in s2.get("conditions", {}).items() if k != cond]
        check(f"427.9 condition {lab}: that condition false, others true -> fail, row 미달",
              s2.get("class") == "fail" and s2["conditions"][cond] is False and all(v is True for v in others)
              and C.row_status(i2, k2) == "미달", s2.get("conditions"))
    i3e, k3e, _ = K.items_p3(stop_row(tmp, "ss_c3e", pad_dip=(15.0, 15.01, 2)), PARAMS, 120.0, True, allow_stop=True)
    check("R19-1 condition 3: a pad lift before the LEVEL start is outside the window -> allowed_stop",
          i3e["safe_stop_427_9"]["class"] == "allowed_stop", i3e["safe_stop_427_9"]["conditions"])
    d_ns = write_scm(tmp / "ss_nos9", stop_spec())
    write_record(d_ns, 8.0, 60.0, u=1e-3)
    res_ns = json.loads((d_ns / "result.json").read_text(encoding="utf-8"))
    res_ns.pop("s9_rows")
    (d_ns / "result.json").write_text(json.dumps(res_ns), encoding="utf-8")
    ins, kns, _ = K.items_p3(C.load_row(d_ns, "scm", ["run_S9.py", "level"]), PARAMS, 120.0, True, allow_stop=True)
    check("R19-1 missing input (s9_rows) -> 판정 불가 (rules 9.3)", ins["safe_stop_427_9"]["class"] == "indeterminate"
          and "result.json s9_rows" in ins["safe_stop_427_9"]["missing_inputs"] and C.row_status(ins, kns) == "판정 불가",
          ins["safe_stop_427_9"].get("missing_inputs"))
    s5s = K.items_p3(cases[-1][1], PARAMS, 120.0, True, allow_stop=True)[0]["safe_stop_427_9"]
    check("427.9 saturation row counted", s5s["values"]["saturation_rows_per_leg"][0] == 1, s5s["values"])
    r6 = stop_row(tmp, "ss_norec", record=False)
    i6, k6, _ = K.items_p3(r6, PARAMS, 120.0, True, allow_stop=True)
    check("427.9 record/record.npz missing -> missing input -> indeterminate (not allowed, not fail)",
          i6["safe_stop_427_9"]["class"] == "indeterminate"
          and i6["safe_stop_427_9"]["not_computable"] == ["5_moving_le_180bar_saturation0"]
          and "record/record.npz u_applied / F_cyl" in i6["safe_stop_427_9"]["missing_inputs"]
          and C.row_status(i6, k6) == "판정 불가", i6["safe_stop_427_9"]["conditions"])
    i7, _, _ = K.items_p3(scm_row(tmp, scm_spec(), "ss_none"), PARAMS, 120.0, True, allow_stop=True)
    check("427.9: no stroke-limit stop event -> no safe-stop branch", "safe_stop_427_9" not in i7)
    i8, k8, _ = K.items_p3(row, PARAMS, 120.0, False, g6=True, allow_stop=False)
    check("C-4 (allow_stop False): no 427.9 branch, earlier path unchanged", "safe_stop_427_9" not in i8
          and "FAULT0" in k8, k8)
    i9, k9, _ = K.items_p3(row, PARAMS, R.READY_FLAT_S, ready_judged=False, g6=True, allow_stop=True)
    check("S-03/04 (G6): allowed_stop, G6-6 record only (R19-1), row 통과",
          i9["safe_stop_427_9"]["class"] == "allowed_stop" and "G6-6" not in k9 and i9["G6-6"].get("record_only")
          and C.row_status(i9, k9) == "통과", k9)
    rows = [{"case": "S1", "d1_id": "S-01", "items": it, "kind": "P3_S", "status": "통과"},
            {"case": "S2", "d1_id": "S-02", "items": K.items_p3(cases[0][1], PARAMS, 120.0, True)[0], "kind": "P3_S",
             "status": "미달"},
            {"case": "C1", "d1_id": "C2-03", "items": {}, "kind": "D8P_judged", "status": "통과"}]
    sm = K.safe_stop_summary(rows)
    check("safe-stop summary: allowed_stop 1 / fail 1, per row lift and moving bar; phrase 통과 1 / 안전 종료 1",
          sm["counts"] == {"allowed_stop": 1, "fail": 1, "indeterminate": 0} and len(sm["rows"]) == 2
          and "moving_max_bar" in sm["rows"][0] and sm["phrase"] == "통과 1 / 안전 종료 1", sm)
    check("safe-stop summary of an empty set: no rows, all counts 0",
          K.safe_stop_summary([])["counts"] == {"allowed_stop": 0, "fail": 0, "indeterminate": 0})
    e0 = B2.bundle_status([])
    check("C-2 empty set -> 판정 불가 + S-15 (never 통과)", e0["status"] == "판정 불가"
          and any("S-15" in s for s in e0["stops"]), e0["stops"])
    check("C-3 empty set -> 판정 불가", B3.bundle_status([])["status"] == "판정 불가")


# ------------------------------------------------------------------ rev18 R18-3 1: PS-c E-1..E-7
def psc_spec():
    sp = scm_spec()
    sp.update(t_end=80.0, recontacts=[],
              phases=[(8.1, "check"), (12.0, "touch"), (20.0, "level"), (30.0, "done"), (32.0, "ready"),
                      (45.0, "level"), (50.0, "done"), (55.0, "ready")])
    return sp


def write_psc(folder, sp=None, ev=("FL", "SS", 10.0), t_ev=40.0, edit=None, fs=4.0, cols=None, block=True,
              rut=None):
    """Synthetic PS-c event row: SCM files + result.json soil_event + soil_event_series.npz (1 ms from t_ev - 0.5).
    edit(t, rows) changes the event rows in place."""
    sp = sp or psc_spec()
    d = write_scm(folder, sp)
    t = np.round(np.arange(t_ev - 0.5, sp["t_end"] + 1e-9, 0.001), 6)
    rows = np.zeros((len(t), 20))
    rows[:, 0] = t
    rows[:, 1:5] = 60000.0
    rows[:, 5:9] = 50000.0
    rows[:, 17:19] = 0.05
    if edit:
        edit(t, rows)
    np.savez(d / "soil_event_series.npz", rows=rows, t_s=t,
             columns=np.array(list(cols or R.E_ROW_COLUMNS)))
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    res["fs_kN"] = fs
    if rut is not None:
        res["s9_rows"] = [dict(r, rut_clearance_m=rut, crawler_gap_min_m=rut) for r in res["s9_rows"]]
    if block:
        res["soil_event"] = {"spec": {"leg": ev[0], "event_id": ev[1], "depth_m": 0.0115, "ramp_s": ev[2]},
                             "driver": {"t_ev_s": t_ev}, "event_reached": True,
                             "judgement": {"pass": "NOT READ"}}
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return d


def e7doc(folder, nb=0, gate=True):
    import p2_psc as P
    return {"tool_gate": {"ok": gate}, "rows": {P.row_key(folder): {"twist": {"n_bundles": nb, "bundles": []}}}}


def psc_items(tmp, name, e7=True, nb=0, gate=True, **kw):
    import p2_psc as P
    d = write_psc(tmp / name, **kw)
    row = C.load_row(d, "scm", ["run_S9.py", "level"])
    return P.e_items(row, PARAMS, e7doc(d, nb, gate) if e7 else None)


def t_psc(tmp):
    import p2_b_c2 as B2
    import p2_psc as P
    A = PARAMS["head_area_m2"]
    it, keys = psc_items(tmp, "psc_ok")
    v = {k: it[k]["verdict"] for k in P.E_KEYS}
    check("PS-c slow event all good: E-1 E-3 E-4 E-5 E-6 E-7 pass, E-2 not applicable (not judged)",
          v == {"E-1": "pass", "E-2": "not_applicable", "E-3": "pass", "E-4": "pass", "E-5": "pass",
                "E-6": "pass", "E-7": "pass"} and "E-2" not in keys and C.row_status(it, keys) == "통과", v)
    br = it["E_branch"]["branch"]
    check("PS-c branch: READY again at 55 s, held 3 s, >= ramp + 3 s after t_ev -> end 58 s (ready_held)",
          abs(br["t_end_s"] - 58.0) < 1e-6 and br["reason"] == "ready_held" and it["E_branch"]["window_end_s"] == 13.0, br)

    def ed(fn):
        return {"edit": fn}
    fails = {
        "E-1": ed(lambda t, r: r.__setitem__((slice(None), 2), np.where((t >= 45.0) & (t < 45.01), 0.0, r[:, 2]))),
        "E-3": ed(lambda t, r: r.__setitem__((slice(None), 7), np.where((t >= 50.0) & (t < 50.002), FMIN - 1.0, r[:, 7]))),
        "E-4": ed(lambda t, r: r.__setitem__((slice(None), 5), np.where((t >= 45.0) & (t < 45.002), 360e5 * A[0], r[:, 5]))),
        "E-5": ed(lambda t, r: r.__setitem__((slice(None), 17), np.where(t >= 57.0, 0.3, r[:, 17]))),
        "E-6": ed(lambda t, r: r.__setitem__((slice(None), 19), np.where((t >= 47.0) & (t < 47.01), 100.0, r[:, 19]))),
    }
    for k, kw in fails.items():
        i2, k2 = psc_items(tmp, f"psc_f_{k}", **kw)
        others = [x for x in P.E_KEYS if x not in (k, "E-2")]
        check(f"PS-c {k} condition false -> {k} fail, other E items pass, row 미달",
              i2[k]["verdict"] == "fail" and all(i2[x]["verdict"] == "pass" for x in others)
              and C.row_status(i2, k2) == "미달", {x: i2[x]["verdict"] for x in P.E_KEYS})

    def outside_moving(t, r):
        sel = (t >= 54.0) & (t < 54.002)
        r[sel, 9] = 1e-3
        r[sel, 5] = 190e5 * A[0]
    i3, _ = psc_items(tmp, "psc_f_E4out", edit=outside_moving)
    check("PS-c E-4 moving sample outside the window > 180 bar -> fail",
          i3["E-4"]["verdict"] == "fail" and i3["E-4"]["moving_outside_max_bar"] > 180.0, i3["E-4"])
    i3b, _ = psc_items(tmp, "psc_f_E4in_moving",
                       edit=lambda t, r: (r.__setitem__((slice(None), 9), np.where((t >= 45) & (t < 45.002), 1e-3, r[:, 9])),
                                          r.__setitem__((slice(None), 5), np.where((t >= 45) & (t < 45.002), 190e5 * A[0], r[:, 5]))))
    check("PS-c E-4 moving 190 bar inside the window (<= 350) -> pass", i3b["E-4"]["verdict"] == "pass", i3b["E-4"])
    spf = psc_spec()
    spf["phases"] = spf["phases"][:6] + [(46.0, "fault"), (47.0, "level")] + spf["phases"][6:]
    i4, _ = psc_items(tmp, "psc_f_E5fault", sp=spf)
    check("PS-c E-5 FAULT periods in the branch (c2_phase fault) -> fail (R19-3)",
          i4["E-5"]["verdict"] == "fail" and i4["E-5"]["fault_periods_in_branch"] == 10, i4["E-5"])
    i4b, _ = psc_items(tmp, "psc_E5fault_before", sp=dict(psc_spec(), phases=[(8.1, "check"), (10.0, "fault"),
                                                                             (12.0, "touch")] + psc_spec()["phases"][2:]))
    check("PS-c E-5 FAULT period before the branch start is not counted (R19-3 window)",
          i4b["E-5"]["verdict"] == "pass", i4b["E-5"])
    i4c, _ = psc_items(tmp, "psc_E5_60s", sp=dict(psc_spec(), t_end=110.0, phases=psc_spec()["phases"][:5]
                                                   + [(45.0, "level"), (101.0, "ready")]))
    check("PS-c branch 60 s without READY held -> max_after, last phase level -> E-5 fail",
          i4c["E_branch"]["branch"]["reason"] == "max_after" and i4c["E-5"]["verdict"] == "fail"
          and i4c["E_branch"]["after_branch_end_record"]["rows"] > 0, i4c["E_branch"]["branch"])
    i5, _ = psc_items(tmp, "psc_f_E5stroke", sp=dict(psc_spec(), stroke=0.70))
    check("PS-c E-5 run maximum stroke 700 mm > 684.8 mm -> fail", i5["E-5"]["verdict"] == "fail", i5["E-5"]["stroke_max_m"])
    i6, _ = psc_items(tmp, "psc_flag_E6", rut=0.02)
    check("PS-c E-6 end clearance 20 mm (0 < c < 25), crawler 0 -> FLAG E-6_post_event_clearance (counts as pass)",
          i6["E-6"]["verdict"] == "flag" and i6["E-6"]["flags"] == ["E-6_post_event_clearance"], i6["E-6"])
    i6b, _ = psc_items(tmp, "psc_f_E6end", edit=lambda t, r: r.__setitem__((slice(None), 19),
                                                                         np.where(t >= 57.9, 50.0, r[:, 19])))
    check("PS-c E-6 crawler load > 0 at the end -> fail", i6b["E-6"]["verdict"] == "fail", i6b["E-6"])
    # missing inputs: every item 판정 불가, never 통과
    i7, k7 = psc_items(tmp, "psc_noblock", block=False)
    check("PS-c event-row kind without a soil event block -> E-1..E-7 indeterminate, row 판정 불가",
          all(i7[k]["verdict"] == "indeterminate" for k in P.E_KEYS) and C.row_status(i7, k7) == "판정 불가", k7)
    i8, k8 = psc_items(tmp, "psc_badcols", cols=[*R.E_ROW_COLUMNS[:-1], "crawler"])
    check("PS-c soil_event_series columns differ -> all E indeterminate", all(i8[k]["verdict"] == "indeterminate"
                                                                             for k in P.E_KEYS), i8["E-1"])
    d9 = write_psc(tmp / "psc_noseries")
    (d9 / "soil_event_series.npz").unlink()
    i9, k9 = P.e_items(C.load_row(d9, "scm", ["run_S9.py", "level"]), PARAMS, None)
    check("PS-c soil_event_series.npz missing -> 판정 불가", C.row_status(i9, k9) == "판정 불가")
    i10, k10 = psc_items(tmp, "psc_noe7", e7=False)
    check("PS-c E-7 tool output not given -> E-7 indeterminate, row 판정 불가 (E-1..E-6 pass)",
          i10["E-7"]["verdict"] == "indeterminate" and C.row_status(i10, k10) == "판정 불가")
    i11, _ = psc_items(tmp, "psc_e7gate", gate=False)
    check("PS-c E-7 tool gate failed -> indeterminate + S-11 stop", i11["E-7"]["verdict"] == "indeterminate"
          and "S-11" in i11["E-7"].get("stop", ""), i11["E-7"])
    i12, _ = psc_items(tmp, "psc_e7nb2", nb=2)
    check("PS-c E-7 two twist bundles -> fail (path 2 grade <= 1)", i12["E-7"]["verdict"] == "fail")
    d13 = write_psc(tmp / "psc_e7other")
    i13, _ = P.e_items(C.load_row(d13, "scm", ["run_S9.py", "level"]), PARAMS, e7doc(tmp / "psc_ok"))
    check("PS-c E-7 output without this row -> indeterminate", i13["E-7"]["verdict"] == "indeterminate")
    i14, _ = psc_items(tmp, "psc_unknown_ev", ev=("FL", "XX", 10.0))
    check("PS-c event id not in 426.3 -> all E indeterminate", all(i14[k]["verdict"] == "indeterminate" for k in P.E_KEYS))
    i15, _ = psc_items(tmp, "psc_short", sp=dict(psc_spec(), t_end=56.0))
    check("PS-c run ends before READY held -> run_end, E-5 judged on that record (R19-3)",
          i15["E_branch"]["branch"]["reason"] == "run_end" and i15["E-5"]["verdict"] in ("pass", "fail")
          and i15["E-5"]["branch_end_reason"] == "run_end", i15["E-5"])

    # fast event (RE1bF on FL; pair FL + RR, adjacent FR, RL)
    def fast_edit(fl_lift=1.0, adj_out=None):
        def f(t, r):
            r[(t >= 40.0) & (t < 40.0 + fl_lift), 1] = 0.0
            r[(t >= 40.5) & (t < 40.7), 2] = 0.0
            r[(t >= 40.5) & (t < 40.7), 14] = 0.001
            if adj_out:
                sel = (t >= 43.0) & (t < 43.0 + adj_out)
                r[sel, 2] = 0.0
                r[sel, 14] = 0.0003
        return f
    f1, fk = psc_items(tmp, "psc_fast_ok", ev=("FL", "RE1bF", 0.05), edit=fast_edit())
    check("PS-c fast: FL lift 1.0 s (<= 1.8, touch-down 1.0 <= 3.0), W = 1.82 s, FR 0.2 s / 1 mm in W -> E-1 E-2 pass",
          f1["E-1"]["verdict"] == "pass" and f1["E-2"]["verdict"] == "pass" and abs(f1["E-2"]["W_end_s"] - 1.82) < 1e-6
          and "E-2" in fk, (f1["E-1"].get("per_leg"), f1["E-2"]))
    f2, _ = psc_items(tmp, "psc_fast_e1", ev=("FL", "RE1bF", 0.05), edit=fast_edit(fl_lift=2.0))
    check("PS-c fast: FL lift 2.0 s > 1.8 s -> E-1 fail", f2["E-1"]["verdict"] == "fail")
    f3, _ = psc_items(tmp, "psc_fast_lowf", ev=("FL", "RE1bF", 0.05), edit=fast_edit(adj_out=0.05), fs=1.0)
    check("PS-c fast: adjacent lift outside W 0.05 s / 0.3 mm, F_s 1 kN -> E-2 FLAG (U-S8-75)",
          f3["E-2"]["verdict"] == "flag", f3["E-2"])
    f4, _ = psc_items(tmp, "psc_fast_out", ev=("FL", "RE1bF", 0.05), edit=fast_edit(adj_out=0.05), fs=4.0)
    check("PS-c fast: same outside lift with F_s 4 kN -> E-2 fail", f4["E-2"]["verdict"] == "fail", f4["E-2"])
    f5, _ = psc_items(tmp, "psc_fast_e6w", ev=("FL", "RE1bF", 0.05),
                      edit=lambda t, r: (fast_edit()(t, r), r.__setitem__((slice(None), 19),
                                                                          np.where((t >= 41.0) & (t < 41.01), 80.0, r[:, 19]))))
    check("PS-c fast: crawler recontact inside W -> E-6 FLAG E-6_event_transient_recontact",
          f5["E-6"]["verdict"] == "flag" and "E-6_event_transient_recontact" in f5["E-6"]["flags"], f5["E-6"])
    # bundle: PS-c rows in C-2 counted, limit sentence attached
    B2.AUX = {}
    rows = [{"case": "P1", "d1_id": "PSC-c-slow-FL", "kind": "PSC", "items": it, "status": "통과",
             "judged_keys": keys}]
    b = B2.bundle_status(rows)
    check("C-2 bundle: PS-c E table per row and the rev4 R4-A2 limit sentence", b["psc_E"]["rows"]["P1"]["E-7"] == "pass"
          and "같은 계산 함수에 기댄다" in (b["psc_E"]["limit_disclosure"] or ""), b["psc_E"])
    # rev19 R19-2: PS-c base row = record row (no E items, not missing; P3 / D8 values recorded)
    base_case = {"case": "D1PSC_J1_B_top_Fs4_spFLJ1_base", "d1_id": "PSC-base-FL", "argv": ["run_S9.py", "level"]}
    ev_case = {"case": "D1PSC_J1_B_top_Fs4_FL_cslow", "d1_id": "PSC-c-slow-FL",
               "argv": ["run_S9.py", "level", "--soil-event", "FL:11.5:20:ready+5"]}
    check("R19-2: kind of the PS-c base row (no --soil-event) = PSC_base, event row = PSC",
          B2.kind_of(base_case) == "PSC_base" and B2.kind_of(ev_case) == "PSC")
    db = write_psc(tmp / "psc_base", block=False)
    rb = C.load_row(db, "scm", ["run_S9.py", "level"])
    ib, kb, _, recb = B2.judge_row(rb, base_case, "PSC_base", PARAMS)
    check("R19-2: base row is a record row: no E-1..E-7 items, P3 and D8 values present",
          recb is True and not any(k in ib for k in P.E_KEYS) and "P3-3" in ib and "D8_F_after_liftoff" in ib
          and ib["E_items"]["verdict"] == "record", sorted(ib)[:12])
    rows2 = rows + [{"case": "B1", "d1_id": "PSC-base-FL", "kind": "PSC_base", "items": ib, "status": "기록 완료",
                     "judged_keys": kb}]
    b2 = B2.bundle_status(rows2)
    check("R19-2: C-2 bundle lists the base row as a record row, not in the E table",
          b2["psc_E"]["record_rows"] == ["B1"] and "B1" not in b2["psc_E"]["rows"], b2["psc_E"])


def t_e7_tool(tmp):
    """p2_e7.py end to end on a synthetic PS-c row: gate at this checkout's HEAD, designated tool run."""
    import p2_e7 as E7
    import p2_psc as P
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    g = E7.tool_gate(REPO, head)
    r19 = g["r19_7"]
    b1 = [x for h in r19["hunks"] for x in h["lines"] if x["rule"] == "1b"]
    check("E-7 gate at HEAD: s9_soil_event_screen 0 commits since f46b5ab; R19-7 (2) E-7 functions the same",
          g["files"][E7.TOOL]["commits_base_to_ref"] == 0 and r19["e7_functions_same"]
          and all(r19["e7_functions_same"].values())
          and set(r19["e7_functions"]) == {"judge_event", "twist_work", "_intervals", "is_fast"}, r19["e7_functions_same"])
    check("E-7 gate at HEAD: R20-1 (1b) RESUME_K1_KEY (+ docstring) read only by record functions, no other file reads "
          "r67_g1_screen.RESUME_K1_KEY -> gate ok, hunk table + grep commands written",
          g["ok"] and r19["ok"] and b1 and all(x["defines"] == ["RESUME_K1_KEY"] and x["ok"] for x in b1)
          and r19["names_1b_cross_file_check"]["greps"] and not r19["names_1b_cross_file_check"]["readers"],
          g["problems"])
    seg = E7.segments("A = 1\ndef f():\n    return 2\n", ("A", "f"))
    check("E-7 gate: source segments of a def and a constant", seg == {"A": "A = 1", "f": "def f():\n    return 2"}, seg)
    # R19-7 on a synthetic repository (base -> record-only change -> E-7 change / module constant)
    sr = tmp / "r197repo"
    if sr.exists():
        shutil.rmtree(sr)
    f = sr / E7.R67
    f.parent.mkdir(parents=True)
    gitc = ["git", "-C", str(sr), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
    base_src = ("import numpy as np\n\n\ndef _intervals(m, t):\n    return []\n\n\ndef is_fast(ev):\n    return True\n\n\n"
                "def twist_work(t, F, v):\n    return {'n_bundles': 0}\n\n\ndef judge_event(rec):\n"
                "    _intervals(rec, rec)\n    is_fast(rec)\n    return twist_work(rec, rec, rec)\n\n\n"
                "def v5_job_record(o):\n    return {'a': 1}\n")

    def commit(src, msg):
        f.write_text(src, encoding="utf-8", newline="\n")
        subprocess.run(gitc + ["add", "-A"], capture_output=True)
        subprocess.run(gitc + ["commit", "-q", "-m", msg], capture_output=True)
        return subprocess.run(["git", "-C", str(sr), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "init", "-q", str(sr)], capture_output=True)
    b0 = commit(base_src, "base")
    keep = E7.BASE_COMMIT
    try:
        E7.BASE_COMMIT = b0
        c1 = commit(base_src.replace("return {'a': 1}", "x = 2\n    return {'a': x}")
                    + "\n\ndef resume_k1_block(c):\n    return {}\n", "record only")
        r1 = E7.r19_7_function_check(sr, c1)
        check("R19-7 synthetic: changes only inside v5_job_record + new resume_k1_block -> ok, hunk table",
              r1["ok"] and r1["hunks"] and all(h["ok"] for h in r1["hunks"]), r1["hunks"])
        c2 = commit(base_src.replace("return {'n_bundles': 0}", "return {'n_bundles': 1}"), "e7 change")
        r2 = E7.r19_7_function_check(sr, c2)
        check("R19-7 synthetic: twist_work body changed -> (1) and (2) fail (S-11)",
              not r2["ok"] and r2["e7_functions_same"]["twist_work"] is False
              and any("(1)" in p for p in r2["problems"]), r2["problems"])
        rec_key = base_src.replace("return {'a': 1}", "return {KEY: 1}") + "\n\nKEY = 'k'\n\"\"\"record key.\"\"\"\n"
        c3 = commit(rec_key, "module constant read by a record function")
        r3 = E7.r19_7_function_check(sr, c3)
        l3 = [x for h in r3["hunks"] for x in h["lines"] if x["rule"] == "1b"]
        check("R20-1 (1b) true: constant + docstring below it, read only by v5_job_record, no other file -> ok",
              r3["ok"] and len(l3) == 2 and all(x["defines"] == ["KEY"] and x["read_by"] == ["v5_job_record"]
                                                for x in l3), r3["hunks"])
        c4 = commit(base_src + "\n\nKEY = 'k'\n", "module constant read by nobody")
        r4 = E7.r19_7_function_check(sr, c4)
        check("R20-1 (1b): constant read by no function -> its readers are all record-only (none) -> ok",
              r4["ok"], r4["problems"])
        c5 = commit(rec_key.replace("return {'n_bundles': 0}", "return {'n_bundles': 0, KEY: 0}"),
                    "constant read by twist_work")
        r5 = E7.r19_7_function_check(sr, c5)
        l5 = [x for h in r5["hunks"] for x in h["lines"] if x["rule"] == "1b"]
        check("R20-1 (1b) false: the constant is also read by twist_work (not record-only) -> its line fails, S-11",
              not r5["ok"] and l5 and all(not x["ok"] and "twist_work" in x["read_by"] for x in l5), l5)
        other = sr / "04_scripts" / "other.py"
        other.write_text("import r67_g1_screen as r67\n\n\ndef f():\n    return r67.KEY\n", encoding="utf-8",
                         newline="\n")
        c6 = commit(rec_key, "other file reads r67.KEY")
        r6 = E7.r19_7_function_check(sr, c6)
        check("R20-1 (1b) false: another file reads r67_g1_screen.KEY through the import alias -> S-11, grep kept",
              not r6["ok"] and r6["names_1b_cross_file_check"]["readers"][0]["how"] == "r67.KEY"
              and any("import" in g["cmd"] for g in r6["names_1b_cross_file_check"]["greps"]), r6["problems"])
        other.write_text("from r67_g1_screen import KEY\n", encoding="utf-8", newline="\n")
        c7 = commit(rec_key, "other file from-imports KEY")
        r7 = E7.r19_7_function_check(sr, c7)
        check("R20-1 (1b) false: `from r67_g1_screen import KEY` in another file -> S-11", not r7["ok"],
              r7["names_1b_cross_file_check"]["readers"])
        other.write_text("import run_v5\nKEY = 'own'\n\n\ndef f():\n    return run_v5.KEY, KEY\n", encoding="utf-8",
                         newline="\n")
        c8 = commit(rec_key, "other module defines / reads its own KEY")
        r8 = E7.r19_7_function_check(sr, c8)
        check("R20-1 (1b): another module's own KEY and run_v5.KEY are not reads of r67_g1_screen.KEY -> ok",
              r8["ok"] and not r8["names_1b_cross_file_check"]["readers"], r8["problems"])
    finally:
        E7.BASE_COMMIT = keep
    # the tool run itself (in process, the gate bypassed only in this test): zero valve -> 0 bundles; twist -> 2
    for pth in (REPO / "04_scripts" / "03_control" / "s9", REPO / "04_scripts" / "03_control" / "s8"):
        if str(pth) not in sys.path:
            sys.path.insert(0, str(pth))
    import s9_soil_event_screen as s9e
    d = write_psc(tmp / "e7row", edit=lambda t, r: r.__setitem__((slice(None), 9), 0.0))
    rec = E7.run_row(s9e, d, ["run_S9.py", "level"], PARAMS)
    doc = {"tool_gate": {"ok": True}, "rows": {P.row_key(d): rec}}
    it, _ = P.e_items(C.load_row(d, "scm", ["run_S9.py", "level"]), PARAMS, doc)
    check("E-7 tool run on the adapter branch: twist n_bundles 0 for a zero-valve record -> E-7 pass",
          (rec.get("twist") or {}).get("n_bundles") == 0 and it["E-7"]["verdict"] == "pass"
          and rec["branch"]["reason"] == "ready_held", rec.get("error") or rec.get("branch"))

    def twist(t, r):   # two separated twist-work bundles > +20 J (rel 2.0-2.5 s and 4.0-4.5 s)
        for a in (42.0, 44.0):
            sel = (t >= a) & (t < a + 0.5)
            r[sel, 5] += 1e5
            r[sel, 9] = 0.01
    d2 = write_psc(tmp / "e7twist", edit=twist)
    rec2 = E7.run_row(s9e, d2, ["run_S9.py", "level"], PARAMS)
    it2, _ = P.e_items(C.load_row(d2, "scm", ["run_S9.py", "level"]), PARAMS,
                       {"tool_gate": {"ok": True}, "rows": {P.row_key(d2): rec2}})
    rec3 = E7.run_row(s9e, tmp / "psc_noblock", ["run_S9.py", "level"], PARAMS)
    check("E-7 tool run: two twist bundles -> path 2 grade fail; a row without an event -> row error",
          it2["E-7"]["verdict"] == "fail" and it2["E-7"]["n_bundles"] == 2 and rec3.get("error"), it2["E-7"])
    out = tmp / "e7out"
    p = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_e7.py"), str(REPO), str(out), "--git-at-start", head,
                        str(d)], capture_output=True, text=True, encoding="utf-8")
    doc_cli = json.loads((out / "e7_path2.json").read_text(encoding="utf-8"))
    it4, _ = P.e_items(C.load_row(d, "scm", ["run_S9.py", "level"]), PARAMS, doc_cli)
    check("E-7 CLI at HEAD: gate ok (R20-1) -> exit 0, tool row, E-7 pass",
          p.returncode == 0 and doc_cli["tool_gate"]["ok"] and doc_cli["tool_gate"]["r19_7"]["hunks"]
          and it4["E-7"]["verdict"] == "pass", p.stdout[-300:] + p.stderr[-600:])
    doc_bad = dict(doc_cli, tool_gate=dict(doc_cli["tool_gate"], ok=False))
    it5, _ = P.e_items(C.load_row(d, "scm", ["run_S9.py", "level"]), PARAMS, doc_bad)
    check("E-7 gate not ok -> E-7 indeterminate + S-11 stop", it5["E-7"]["verdict"] == "indeterminate"
          and "S-11" in it5["E-7"].get("stop", ""), it5["E-7"])


def t_tlift_sus(tmp):
    """rev21 R21-1 / R21-2: the D-29 t_lift of L2b D8 items = t_lift,sus (1 ms crawler <= 0.01 W, W = 376.7 kN,
    held to the record end, phase not idle / check / touch); V0 rows keep the R15-3 10 Hz t_b with the 10 Hz
    t_lift,sus counterpart as a record; rounding up to the first record.npz control instant."""
    start = 3.0
    thr = 0.01 * 376700.0

    def l2b_with_cr(name, fn, **kw):
        d = write_l2b(tmp / name, **kw)
        z = dict(np.load(d / "pads.npz"))
        z["crawler_normal_N"] = fn(z["t"], z["crawler_normal_N"].copy())
        np.savez(d / "pads.npz", **z)
        return C.load_row(d, "l2b", L2B_ARGV)
    r1 = l2b_with_cr("sus_hold", lambda t, c: c)
    d1 = C.d8_force(r1, PARAMS, rigid_nsc_hold=True)
    check("R21-1 held to the end: t_lift,sus = first sample <= 0.01 W held to the end (23.0 s), basis 1ms_sus",
          d1["t_lift_basis"] == "1ms_sus" and abs(d1["t_lift_s"] - 23.0) < 1e-9
          and d1["t_lift_first_le0_record_s"] == d1["t_lift_s"], {k: d1.get(k) for k in ("t_lift_s", "t_lift_basis")})
    r2 = l2b_with_cr("sus_recontact", lambda t, c: np.where((t >= start + 25.0) & (t < start + 25.5), 50000.0, c))
    d2 = C.d8_force(r2, PARAMS, rigid_nsc_hold=True)
    check("R21-1 re-contact after the first zero: t_lift,sus after the last re-contact (28.5 s); first <= 0 kept",
          abs(d2["t_lift_s"] - 28.5) < 1e-9 and abs(d2["t_lift_first_le0_record_s"] - 23.0) < 1e-9,
          (d2["t_lift_s"], d2["t_lift_first_le0_record_s"]))
    r2b = l2b_with_cr("sus_small", lambda t, c: np.where((t >= start + 25.0) & (t < start + 25.5), thr, c))
    d2b = C.d8_force(r2b, PARAMS, rigid_nsc_hold=True)
    check("R21-1 crawler exactly 0.01 W after the zero counts as <= 0.01 W (7.6) -> t_lift,sus 23.0 s",
          abs(d2b["t_lift_s"] - 23.0) < 1e-9, d2b["t_lift_s"])
    r3 = l2b_with_cr("sus_none", lambda t, c: np.where(t >= t[-1] - 0.0005, 2 * thr, c))
    d3 = C.d8_force(r3, PARAMS, rigid_nsc_hold=True)
    check("R21-1 crawler above 0.01 W at the record end -> no t_lift,sus -> D8 판정 불가 + stop",
          d3["verdict"] == "indeterminate" and d3["t_lift_s"] is None and "R21-1" in d3.get("stop", ""), d3.get("reason"))
    r4 = l2b_with_cr("sus_phase", lambda t, c: np.where(t >= start + 3.0, 0.0, c))
    d4 = C.d8_force(r4, PARAMS, rigid_nsc_hold=True)
    check("R21-1 phase rule: crawler 0 from the check / touch phases -> t_lift,sus = first level sample (18.0 s)",
          abs(d4["t_lift_s"] - 18.0) < 1e-9, d4["t_lift_s"])
    it, keys, _ = K.items_d8p(r3, PARAMS, judged=True, hold=True)
    b = K.bundle_status([{"case": "x", "items": it, "judged_keys": keys, "status": C.row_status(it, keys)}])
    check("R21-1 missing t_lift,sus stops the bundle (판정 불가 with the stop listed)",
          b["status"] == "판정 불가" and any("R21-1" in s for s in b["stops"]), b["stops"])
    # R21-2 rounding up to the first record.npz control instant (t >= t_sus - 1e-9)
    check("R21-2 rounding: t_lift,sus on a control instant -> same instant", abs(d1["t_lift_sus_up_10Hz_record_s"] - 23.0)
          < 1e-9, d1["t_lift_sus_up_10Hz_record_s"])
    check("R21-2 rounding boundary: 23.0 + 5e-10 -> 23.0 (within 1e-9), 23.0 + 2e-9 -> 23.1, 23.05 -> 23.1",
          abs(C.up_to_control_instant(r1, 23.0 + 5e-10) - 23.0) < 1e-12
          and abs(C.up_to_control_instant(r1, 23.0 + 2e-9) - 23.1) < 1e-9
          and abs(C.up_to_control_instant(r1, 23.05) - 23.1) < 1e-9)
    check("R21-2 rounding: past the last control instant or no time -> None",
          C.up_to_control_instant(r1, 200.0) is None and C.up_to_control_instant(r1, None) is None)
    check("R21-2 rounding uses engine absolute times (pads t and record t from 3.0 s; phases + start_t_s)",
          r1.t_offset == start and abs(C.first_phase_time(r1, "level") - (start + 15.0)) < 1e-9)
    # V0 L2b (no 1 ms crawler_normal_N): R15-3 t_b kept; 10 Hz t_lift,sus counterpart recorded
    for name, fz, want in (("sus_v0", lambda t: np.where(t < 23.0, 300000.0, 0.0), 23.0),
                           ("sus_v0_recont", lambda t: np.where((t < 23.0) | ((t >= 30.0) & (t < 31.0)), 300000.0, 0.0),
                            31.0),
                           ("sus_v0_none", lambda t: np.where((t < 23.0) | (t >= t[-1] - 0.05), 300000.0, 0.0), None)):
        dv = write_l2b(tmp / name)
        _set_npz(dv / "pads.npz", crawler_normal_N=None)
        rec = dict(np.load(dv / "record" / "record.npz"))
        fc = np.zeros((len(rec["t"]), 3))
        fc[:, 2] = fz(rec["t"])
        rec["F_crawler"] = fc
        np.savez(dv / "record" / "record.npz", **rec)
        rj = json.loads((dv / "result.json").read_text(encoding="utf-8"))
        rj["floor_plane"] = {"normal_world": [0.0, 0.0, 1.0]}
        (dv / "result.json").write_text(json.dumps(rj), encoding="utf-8")
        rv = C.load_row(dv, "l2b", L2B_ARGV)
        dd = C.d8_force(rv, PARAMS, rigid_nsc_hold=True)
        rec10 = dd.get("t_lift_sus_10Hz_record_s")
        okv = dd["t_lift_basis"] == "bracket_10Hz" and abs(dd["t_lift_s"] - 23.0) < 1e-9
        okv = okv and (rec10 == "기록 결측" if want is None else abs(rec10 - want) < 1e-9)
        check(f"R21-1 V0 ({name}): t_b 23.0 s kept (R15-3), 10 Hz t_lift,sus record = {want or '기록 결측'}, "
              f"differs flag {want not in (None, 23.0)}", okv
              and dd["t_lift_sus_10Hz_differs_from_t_b"] == (None if want is None else want != 23.0),
              {k: dd.get(k) for k in ("t_lift_s", "t_lift_basis", "t_lift_sus_10Hz_record_s")})
    rs = scm_row(tmp, scm_spec(), "sus_scm")
    ds = C.d8_force(rs, PARAMS, rigid_nsc_hold=False)
    check("R21-1 scope: SCM rows keep the rev6 5 t_lift (1ms), no t_lift,sus basis", ds["t_lift_basis"] == "1ms",
          ds["t_lift_basis"])


def t_pairs():
    """rev19 R19-6: C-5 VB <-> V0 six pairs from the batch rows and the manifest rows together."""
    import p2_b_c5 as B5
    six = [x for p in B5.PAIRS_R19_6 for x in p]

    def rows_of(names, status=None):
        return [{"case": n, "status": (status or {}).get(n, "통과")} for n in names]
    pc = B5.pair_check(rows_of(six[:6]), six[6:] + ["P3b_J2_B_top_Fs4_m1p1_t180_seed20261026", "LS1_E_G4_Fs8"])
    check("R19-6: six pairs found from batch rows + manifest rows (seed / LS rows are not pairs) -> exact, no stop",
          pc["exact"] and not pc["stops"] and len(pc["pairs"]) == 6, pc["found"])
    pc2 = B5.pair_check(rows_of(six[:-1]), [])
    check("R19-6: one V0 row missing -> pairs != six -> S-15, no grade",
          not pc2["exact"] and any("S-15" in s for s in pc2["stops"]), pc2["stops"])
    pc3 = B5.pair_check(rows_of(six + ["X_Fs0", "X_Fs0_V0"]), [])
    check("R19-6: a seventh pair -> S-15", not pc3["exact"] and pc3["stops"], pc3["found"][-1:])
    vb, v0 = B5.PAIRS_R19_6[0]
    pc4 = B5.pair_check(rows_of(six, {vb: "미달"}), [])
    check("R19-6 / v5 rev12 2.2: VB 미달 with V0 통과 -> stop and ask; pair grades recorded",
          any("2.2" in s for s in pc4["stops"]) and pc4["pairs"][0]["verdict"] == "record", pc4["stops"])
    pc5 = B5.pair_check(rows_of(six, {vb: "미달", v0: "미달"}), [])
    check("R19-6: both 미달 -> no 2.2 stop", not pc5["stops"], pc5["stops"])
    b = B5.bundle_status([dict(r, items={}, engine="scm", judged_keys=[]) for r in rows_of(six[:-1])])
    check("R19-6: C-5 bundle with a missing pair -> 판정 불가", b["status"] == "판정 불가"
          and not b["rev19_R19_6_pairs"]["exact"], b["status"])


# ------------------------------------------------------------------ rev24 common block CD-1..CD-11
W_REF = 376580.0   # synthetic C2 meta soil.W_ref_N


def write_p37_record(folder: Path, sp: dict, moving, F_of=None, meta=(None, None), mode="restart"):
    """record/record.npz with the P3-7 reading keys (10 Hz) and result.json c2_soil / LW meta. `moving` = [(a, b)]
    intervals of u_applied 0.01 m/s on all legs; meas.stroke grows 1 mm per moving sample; `F_of(t, e)` = sum
    of p_h A_p - p_r A_ann (default 0.5 W_ref)."""
    import p2_cd as CD
    t10 = np.round(np.arange(sp["t0"] + 0.1, sp["t_end"] + 1e-9, 0.1), 6)
    mov = np.zeros(len(t10), bool)
    for a, b in moving:
        mov |= (t10 >= a - 1e-9) & (t10 < b - 1e-9)
    u = np.where(mov[:, None], 0.01, 0.0) * np.ones((1, 4))
    e = 0.3 + 0.001 * np.cumsum(mov)
    F_total = F_of(t10, e) if F_of else np.full(len(t10), 0.5 * W_REF)
    head, _ = CD._cylinder_areas(REPO)
    p_h = np.repeat((F_total / head.sum())[:, None], 4, axis=1)
    (folder / "record").mkdir(exist_ok=True)
    np.savez(folder / "record" / "record.npz", t=t10, u_applied=u, F_cyl=np.repeat(F_total[:, None] / 4, 4, axis=1),
             s_motor=np.repeat(e[:, None], 4, axis=1), **{"meas.stroke": np.repeat(e[:, None], 4, axis=1),
                                                         "meas.head_pressure": p_h,
                                                         "meas.rod_pressure": np.zeros((len(t10), 4))})
    res = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    res["c2_soil"].update(W_ref_N=W_REF, t_P_s=meta[0], t_loc_s=meta[1])
    res["controller_meta"]["liftoff_window_reapproach"] = {"mode": mode, "restarts": 0}
    (folder / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return folder


def _p37_profile(slope_N_per_mm, plateau_from=23.0):
    def f(t, e):
        base = 0.80 * W_REF + slope_N_per_mm * (e - 0.3) * 1000.0
        return np.where(t >= plateau_from - 1e-9, 0.95 * W_REF, base)
    return f


def _jr(item, passed=True, kind="judged", note="", **kw):
    return dict({"item": item, "case": "case", "value": 1.0, "limit": 1.0, "passed": passed, "note": note,
                 "kind": kind}, **kw)


def write_judge_doc(s8c: Path, folder: Path, rows, liftoff_rel=20.0, event_window=None):
    import p2_cd as CD
    d = s8c / folder.parent.name
    d.mkdir(parents=True, exist_ok=True)
    metric = {"case": folder.name, "times_s": {"t0": 3.0, "liftoff": liftoff_rel}}
    if event_window is not None:
        metric["event_window"] = event_window
    doc = {"meta": {"batch": str(folder.parent), "judge_revision": "synthetic"},
           "rows": [dict(r, case="*" if r.get("case") == "*" else folder.name) for r in rows], "metrics": [metric]}
    (d / CD.JUDGE_REL_PATH).write_text(json.dumps(doc), encoding="utf-8")
    CD._DOCS.clear()


def _l2b_case(tmp, group, name="case", **kw):
    return write_l2b(tmp / "r24" / group / name, **kw)


def t_rev24(tmp):
    import types
    import p2_b_c5 as B5
    import p2_b_c8 as B8
    import p2_cd as CD
    s8c = tmp / "r24_s8c"
    CD.CONTEXT.clear()
    CD.CONTEXT.update(repo=REPO, s8c_dir=str(s8c))
    # ---- CD-2 classification and count
    check("CD-2 classify: recalc / original / t_lift prefix (suffixed 5a) / other",
          [CD.classify_item(n) for n in (CD.ITEM_C1, "D8 attitude last 5 s + mount <= 0.2 deg",
                                          "5a rocking amplitude after the re-READY", "3 F_min before the event",
                                          "3 F_min after the re-READY", "RE1b re-READY <= 60 s")]
          == ["recalc", "original", "original_tlift", "original_tlift", "original_other", "original_other"])
    check("CD-2 kinds: judged kinds / record kinds / hold / unknown -> runner_unjudged",
          [CD._use_of(k) for k in ("quality", None, "consistency", "hold", "not_applicable")]
          == ["judged", "judged", "record", "hold", "runner_unjudged"])
    g = CD._cd2_grade([{"use": "judged", "passed": False}, {"use": "hold", "passed": None}])
    check("CD-2 count: passed False wins over hold (미달)", g["verdict"] == "fail", g)
    g = CD._cd2_grade([{"use": "judged", "passed": True}, {"use": "hold", "passed": None}])
    check("CD-2 count: hold -> 판정 불가", g["verdict"] == "indeterminate", g)
    g = CD._cd2_grade([{"use": "record", "passed": True}, {"use": "runner_unjudged", "passed": None}])
    check("CD-2 count: no judged-class passed True -> 판정 불가", g["verdict"] == "indeterminate", g)
    # ---- CD-2 rows on a synthetic L2b row (non-event)
    base_rows = [_jr(CD.ITEM_C1), _jr(CD.ITEM_D8_LIFT), _jr(CD.ITEM_P4_MOVING), _jr(CD.ITEM_P4_SAT),
                 _jr("3 F_min (1 ms)"), _jr("6 relevel time"), _jr("S8-L5 crawler label", passed=None, kind="record"),
                 _jr("W weird kind", kind="weird"), _jr("J judged none", passed=None),
                 _jr("F anomaly", kind="anomaly", note="FLAG near F_min")]
    f1 = _l2b_case(tmp, "S8a_ok")
    write_judge_doc(s8c, f1, base_rows)
    row1 = C.load_row(f1, "l2b", L2B_ARGV)
    b1 = CD.cd2_items(row1, PARAMS)
    by = {e["item"]: e for e in b1["entries"]}
    check("CD-2 non-event row: recalc C1 / lift-off / moving pressure / saturation pass, CD-2 통과, no stop",
          b1["verdict"] == "pass" and "stop" not in b1
          and all(by[k]["handling"] == "recalc" and by[k]["verdict"] == "pass"
                  for k in (CD.ITEM_C1, CD.ITEM_D8_LIFT, CD.ITEM_P4_MOVING, CD.ITEM_P4_SAT)), b1)
    check("CD-2 (a) t_lift = 1 ms t_lift,sus (engine absolute 23.0 s); t_lift diff check 0 (prefix item present)",
          abs(b1["t_lift"]["t_lift_s"] - 23.0) < 1e-9 and b1["t_lift_check"]["ok"]
          and abs(b1["t_lift_check"]["diff_s"]) < 1e-9, b1.get("t_lift_check"))
    check("CD-2 runner 미판정: unknown kind and judged passed None, with note; not counted",
          by["W weird kind"]["verdict"] == "runner_unjudged" and by["J judged none"]["verdict"] == "runner_unjudged"
          and len(b1["runner_unjudged"]) == 2 and b1["n_runner_unjudged"] == 2, b1["runner_unjudged"])
    check("CD-2 FLAG: anomaly note FLAG -> flag (counts as pass); record kind -> record",
          by["F anomaly"]["verdict"] == "flag" and by["S8-L5 crawler label"]["verdict"] == "record"
          and "F anomaly" in b1["flags"])
    write_judge_doc(s8c, f1, base_rows, liftoff_rel=20.3)
    b1b = CD.cd2_items(row1, PARAMS)
    check("CD-2 t_lift 차 > 0.1 s on a prefix-item row -> stop and ask", "t_lift 차" in b1b.get("stop", ""), b1b)
    write_judge_doc(s8c, f1, [_jr(CD.ITEM_C1), _jr("6 relevel time")], liftoff_rel=20.3)
    check("CD-2 t_lift 차 not checked without a prefix item", "stop" not in CD.cd2_items(row1, PARAMS))
    write_judge_doc(s8c, f1, base_rows + [_jr(CD.ITEM_D8_CYL)])
    check("CD-2 table row 2 item (0 rows expected) appears -> stop", "D8 min true cylinder" in
          CD.cd2_items(row1, PARAMS).get("stop", ""))
    write_judge_doc(s8c, f1, [_jr(CD.ITEM_P4_OUT), _jr("6 relevel time")])
    check("CD-2/CD-3 event item on a non-event row -> stop (row class mismatch)",
          "outside the table's row class" in CD.cd2_items(row1, PARAMS).get("stop", ""))
    write_judge_doc(s8c, f1, [_jr(CD.ITEM_P4_MOVING, kind="info"), _jr("6 relevel time")])
    bi = CD.cd2_items(row1, PARAMS)
    check("CD-2 recalc item that came as a record kind -> record (both values kept, not judged)",
          bi["entries"][0]["use"] == "record" and "recalc" in bi["entries"][0] and bi["verdict"] == "pass", bi)
    f_none = _l2b_case(tmp, "S8a_none")
    check("CD-2 no original judge output -> 판정 불가 with reason",
          CD.cd2_items(C.load_row(f_none, "l2b", L2B_ARGV), PARAMS)[CD.REASON_KEY].startswith(CD.REASON_NO_JUDGE))
    # C1: R40-2 hold (rigid), fail (compliant, passed check), REANCHOR exclusion, no t_lift
    f2 = _l2b_case(tmp, "S8a_dip", dip=(1, 21.0, 21.05, 5000.0))
    write_judge_doc(s8c, f2, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
    b2 = CD.cd2_items(C.load_row(f2, "l2b", L2B_ARGV), PARAMS)
    check("CD-2 C1 recalc below F_min + 5 kN within 8 s, slow min >= limit, rigid crawler -> hold -> 판정 불가",
          b2["entries"][0]["recalc"]["verdict"] == "hold" and b2["verdict"] == "indeterminate"
          and CD.REASON_JUDGE_HOLD in b2[CD.REASON_KEY], b2)
    f2c = _edit_result(f2, tmp / "r24" / "S8a_dipc" / "case", lambda r: r["settings"].update(
        s8={"crawler_contact": "nsc_compliant", "crawler_check_passed": True}))
    write_judge_doc(s8c, f2c, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
    b2c = CD.cd2_items(C.load_row(f2c, "l2b", L2B_ARGV), PARAMS)
    check("CD-2 C1 recalc on a compliant crawler with S8-L4 passed -> 미달 (no hold), change reason recorded",
          b2c["verdict"] == "fail" and b2c["entries"][0].get("cd7_change_reason"), b2c)
    f2r = _edit_result(f2, tmp / "r24" / "S8a_reanchor" / "case", lambda r: r.update(phases=[
        [0.1, "check"], [5.0, "touch"], [15.0, "level"], [20.9, "reanchor"], [21.2, "level"], [35.0, "done"],
        [36.0, "ready"]]))
    write_judge_doc(s8c, f2r, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
    b2r = CD.cd2_items(C.load_row(f2r, "l2b", L2B_ARGV), PARAMS)
    check("CD-2 C1 recalc: the dip inside REANCHOR is excluded -> pass", b2r["verdict"] == "pass"
          and b2r["entries"][0]["recalc"]["reanchor_windows_s"], b2r["entries"][0]["recalc"])
    f3 = _l2b_case(tmp, "S8a_nolift", liftoff=200.0)
    write_judge_doc(s8c, f3, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
    b3 = CD.cd2_items(C.load_row(f3, "l2b", L2B_ARGV), PARAMS)
    check("CD-2 (a) no t_lift -> recalc item 판정 불가 (hold class), reason 't_lift 없음'",
          b3["verdict"] == "indeterminate" and CD.REASON_NO_TLIFT in b3[CD.REASON_KEY], b3)
    # ---- CD-3 event classes
    ns = types.SimpleNamespace
    ev = CD.event_class(ns(result={"settings": {"event": "drop_RR_30"}}), PARAMS["v_max_m_s"])
    check("CD-3 settings.event drop_RR_30 -> floor event", ev["class"] == "floor")
    fast = {"settings": {}, "event_t_s": 30.0, "event": {"spec": {"kind": "settle", "leg": "FL", "depth_m": 0.05,
                                                                  "ramp_s": 0.5}}}
    check("CD-3 settle FL 100 mm/s > v_max with event_t_s -> fast settle (FL + diagonal RR)",
          CD.event_class(ns(result=fast), PARAMS["v_max_m_s"]).get("event_legs") == ["FL", "RR"])
    slow = copy.deepcopy(fast)
    slow["event"]["spec"].update(depth_m=0.0115, ramp_s=2.0)
    check("CD-3 E_G4 settle 5.75 mm/s -> non-event", CD.event_class(ns(result=slow), PARAMS["v_max_m_s"])["class"]
          == "none")
    noev = copy.deepcopy(fast)
    noev.pop("event_t_s")
    zero = copy.deepcopy(fast)
    zero["event"]["spec"]["ramp_s"] = 0.0
    check("CD-3 fast settle without event_t_s -> non-event; ramp 0 -> infinite speed -> fast",
          CD.event_class(ns(result=noev), PARAMS["v_max_m_s"])["class"] == "none"
          and CD.event_class(ns(result=zero), PARAMS["v_max_m_s"])["class"] == "fast_settle")
    # ---- CD-3 floor window and pressure items
    def floor_row(group, lift=None, event_t=30.0, edit_rec=None):
        def fn(r):
            r["settings"].update(event="drop_RR_30", level="top")
            if event_t is not None:
                r["event_t_s"] = event_t
        f = _edit_result(_l2b_case(tmp, group + "_src"), tmp / "r24" / group / "case", fn)
        if lift is not None:
            z = dict(np.load(f / "pads.npz"))
            sel = (z["t"] >= lift[0]) & (z["t"] < lift[1])
            z["N"][sel, 3] = 0.0
            np.savez(f / "pads.npz", **z)
        if edit_rec is not None:
            z = dict(np.load(f / "record" / "record.npz"))
            edit_rec(z)
            np.savez(f / "record" / "record.npz", **z)
        return f
    r_nl = C.load_row(floor_row("S8f_nolift"), "l2b", L2B_ARGV)
    w = CD.event_window(r_nl, CD.event_class(r_nl, PARAMS["v_max_m_s"]), None)
    check("CD-3 floor window, RR never lifts -> W = [t_event, t_event + T_3] (abs 33.0 .. 33.82)",
          abs(w["start_s"] - 33.0) < 1e-9 and abs(w["end_s"] - 33.82) < 1e-9, w)
    r_l = C.load_row(floor_row("S8f_lift", lift=(33.5, 34.0)), "l2b", L2B_ARGV)
    w = CD.event_window(r_l, CD.event_class(r_l, PARAMS["v_max_m_s"]), None)
    check("CD-3 floor window: RR last lifted 1 ms sample 33.999 -> re-ground 34.000, end 34.82",
          abs(w["rr_last_reground_s"] - 34.0) < 1e-9 and abs(w["end_s"] - 34.82) < 1e-9, w)
    r_cap = C.load_row(floor_row("S8f_cap", lift=(33.5, 200.0)), "l2b", L2B_ARGV)
    w = CD.event_window(r_cap, CD.event_class(r_cap, PARAMS["v_max_m_s"]), None)
    check("CD-3 floor window: RR lifted to the record end -> end = t_event + 5 s", abs(w["end_s"] - 38.0) < 1e-9, w)
    r_ne = C.load_row(floor_row("S8f_noevt", event_t=None), "l2b", L2B_ARGV)
    w = CD.event_window(r_ne, CD.event_class(r_ne, PARAMS["v_max_m_s"]), None)
    check("CD-3 floor event without event_t_s -> first READY + 5 s (abs 39 + 5)",
          abs(w["t_event_s"] - 44.0) < 1e-9 and w["t_event_basis"] == "first READY + 5 s", w)
    A = PARAMS["head_area_m2"]

    def press(z):
        t = z["t"]
        z["u_applied"] = np.zeros_like(z["u_applied"])
        z["F_cyl"] = np.full_like(z["F_cyl"], 50e5 * A[0])
        k_out = int(np.argmin(np.abs(t - 50.0)))
        z["u_applied"][k_out, 0] = 0.005
        z["F_cyl"][k_out, 0] = 200e5 * A[0]           # extension outside W: 200 bar > 180
        k_ret = int(np.argmin(np.abs(t - 52.0)))
        z["u_applied"][k_ret, 1] = -0.005
        z["F_cyl"][k_ret, 1] = 300e5 * A[1]           # retraction outside W: recorded only
        k_in = int(np.argmin(np.abs(t - 33.5)))
        z["F_cyl"][k_in, 2] = 360e5 * A[2]            # hold inside W: 360 bar > 350
    r_p = C.load_row(floor_row("S8f_press", edit_rec=press), "l2b", L2B_ARGV)
    ev_p = CD.event_class(r_p, PARAMS["v_max_m_s"])
    it = CD.cd3_items(r_p, PARAMS, ev_p, CD.event_window(r_p, ev_p, None))
    check("CD-3 W 밖: extension 200 bar -> fail; retraction 300 bar recorded (leg FR), W 안 hold 360 bar -> fail",
          it[CD.ITEM_P4_OUT]["verdict"] == "fail" and it[CD.ITEM_P4_OUT]["retract_record"]["leg"] == "FR"
          and it[CD.ITEM_P4_IN]["verdict"] == "fail" and it[CD.ITEM_P4_IN]["state"] == "hold"
          and it[CD.ITEM_P4_SAT]["verdict"] == "pass", it)

    def sat(z):
        press(z)
        k_out = int(np.argmin(np.abs(z["t"] - 50.0)))
        z["F_cyl"][k_out, 0] = 215e5 * A[0]
    r_s = C.load_row(floor_row("S8f_sat", edit_rec=sat), "l2b", L2B_ARGV)
    ev_s = CD.event_class(r_s, PARAMS["v_max_m_s"])
    it_s = CD.cd3_items(r_s, PARAMS, ev_s, CD.event_window(r_s, ev_s, None))
    check("CD-3 saturation: extension 215 bar outside W -> 1 sample, fail",
          it_s[CD.ITEM_P4_SAT]["count"] == 1 and it_s[CD.ITEM_P4_SAT]["verdict"] == "fail", it_s[CD.ITEM_P4_SAT])
    f_w = floor_row("S8f_judgewin")
    write_judge_doc(s8c, f_w, [_jr(CD.ITEM_P4_OUT), _jr(CD.ITEM_P4_IN), _jr(CD.ITEM_P4_SAT)],
                    event_window={"pressure_end_s": 30.82 + 0.2})
    bw = CD.cd2_items(C.load_row(f_w, "l2b", L2B_ARGV), PARAMS)
    check("CD-3 computed window end vs original judge end differs by 0.2 s -> stop and ask",
          "CD-3: computed window end" in bw.get("stop", "") and abs(bw["window"]["diff_vs_judge_s"] + 0.2) < 1e-9, bw)
    write_judge_doc(s8c, f_w, [_jr(CD.ITEM_P4_OUT), _jr(CD.ITEM_P4_IN), _jr(CD.ITEM_P4_SAT)],
                    event_window={"pressure_end_s": 30.82})
    bw2 = CD.cd2_items(C.load_row(f_w, "l2b", L2B_ARGV), PARAMS)
    check("CD-3 equal window ends -> no stop, W items recalculated, CD-2 통과", "stop" not in bw2
          and bw2["verdict"] == "pass" and abs(bw2["window"]["diff_vs_judge_s"]) < 1e-9, bw2)
    f_fs = _edit_result(_l2b_case(tmp, "S8s_src"), tmp / "r24" / "S8s_fast" / "case", lambda r: r.update(
        event_t_s=30.0, event={"spec": {"kind": "settle", "leg": "FL", "depth_m": 0.05, "ramp_s": 0.5}}))
    r_fs = C.load_row(f_fs, "l2b", L2B_ARGV)
    ev_fs = CD.event_class(r_fs, PARAMS["v_max_m_s"])
    w_read = CD.event_window(r_fs, ev_fs, {"event_window": {"pressure_end_s": 31.0}})
    w_cap = CD.event_window(r_fs, ev_fs, None)
    check("CD-3 fast settle: original judge window read (abs 34.0); without it and without airborne -> t_event + 5",
          abs(w_read["end_s"] - 34.0) < 1e-9 and w_read["method"].startswith("original")
          and abs(w_cap["end_s"] - 38.0) < 1e-9, (w_read, w_cap))
    # ---- CD-4 P3-7 (S-1 window replay, gate, loaded windows)
    sp = scm_spec()
    sp.update(crawler=[("ramp", 22.95, 23.0)], recontacts=[])

    def p37_row(name, slope, meta, events=(), mode="restart", crawler=None):
        s = copy.deepcopy(sp)
        s["events"] = list(s["events"]) + list(events)
        if crawler is not None:
            s["crawler"] = crawler
        f = write_scm(tmp / "r24" / name, s)
        write_p37_record(f, s, [(20.0, 26.0)], _p37_profile(slope), meta=meta, mode=mode)
        return C.load_row(f, "scm", SCM_VB_ARGV)
    p = CD.p3_7(p37_row("p37_ok", 600.0, (23.0, 24.0)), PARAMS)
    check("CD-4 P3-7: gate (t_P 23.0 = first tail sample, t_LOC 24.0) ok; loaded rise 6 kN >= 4 kN -> pass",
          p["reconstruct_ok"] and p["verdict"] == "pass" and abs(p["rise_min_loaded_N"] - 6000.0) < 1e-3, p)
    p = CD.p3_7(p37_row("p37_low", 300.0, (23.0, 24.0)), PARAMS)
    check("CD-4 P3-7: loaded rise 3 kN < 4 kN -> fail", p["verdict"] == "fail"
          and abs(p["rise_min_loaded_N"] - 3000.0) < 1e-3, p)
    p = CD.p3_7(p37_row("p37_gate", 600.0, (23.1, 24.0)), PARAMS)
    check("CD-4 P3-7: meta t_P differs by 0.1 s -> reconstruction gate fails -> 판정 불가 with reason",
          p["verdict"] == "indeterminate" and "재구성 관문" in p[CD.REASON_KEY], p)
    p = CD.p3_7(p37_row("p37_revoke", 600.0, (24.1, 25.1), events=[(24.05, R.EVENT_LOC_REVOKED)]), PARAMS)
    check("CD-4 P3-7: LOC revoked at 24.05 -> scan resumes after it, last LOC (24.1, 25.1) = meta",
          p["reconstruct_ok"] and (p["t_P_rec_s"], p["t_loc_rec_s"]) == (24.1, 25.1), p)
    reap = [(23.45, "leg_reapproach_start:FL"), (23.75, "leg_reapproach_contact:FL")]
    p = CD.p3_7(p37_row("p37_lwa", 600.0, (23.8, 24.8), events=reap), PARAMS)
    check("CD-4 P3-7: LWa (mode restart) clears the window during a re-approach -> LOC (23.8, 24.8)",
          p["reconstruct_ok"], p)
    p = CD.p3_7(p37_row("p37_lwoff", 600.0, (23.8, 24.8), events=reap, mode="off"), PARAMS)
    check("CD-4 P3-7: same run read with LW off -> LOC (23.0, 24.0) != meta -> gate fails",
          not p["reconstruct_ok"] and p["verdict"] == "indeterminate", p)
    p = CD.p3_7(p37_row("p37_lwb", 600.0, (23.0, 24.0), mode="LWb"), PARAMS)
    check("CD-4 P3-7: unknown window rule (LWb) -> 판정 불가", p["verdict"] == "indeterminate", p)
    p = CD.p3_7(p37_row("p37_free", 600.0, (23.0, 24.0), crawler=[("ramp", 19.0, 19.5)]), PARAMS)
    check("CD-4 P3-7: no loaded window -> pass ('부담 창 없음')", p["verdict"] == "pass"
          and p["rise_min_loaded_N"] is None, p)
    p = CD.p3_7(p37_row("p37_rec", 300.0, (23.0, 24.0)), PARAMS, judged=False)
    check("CD-4 P3-7 recorded (C-4 / C-8 / PS-c base): verdict record, record_verdict kept",
          p["verdict"] == "record" and p["record_verdict"] == "fail", p)
    # ---- CD-5 READY none, CD-4 guard
    sp5 = scm_spec()
    sp5["phases"] = [(8.1, "check"), (12.0, "touch"), (20.0, "level"), (30.0, "done")]
    r5 = scm_row(tmp / "r24", sp5, "noready")
    it5, k5, _ = K.items_p3(r5, PARAMS, R.READY_SLOPE_S, ready_judged=True, g6=False, allow_stop=True)
    CD.apply_ready_none(it5, k5, r5)
    check("CD-5 no READY: P3-1 READY condition 해당 없음, recontact condition judged; P3-4 / P3-5 해당 없음; "
          "judged P3-6 미달",
          it5["P3-1"]["verdict"] in ("pass", "flag") and it5["P3-1"]["ready_window_condition"] == CD.NA_NO_READY
          and it5["P3-4"]["verdict"] == "na" and it5["P3-5"]["verdict"] == "na" and it5["P3-6"]["verdict"] == "fail",
          {k: it5[k]["verdict"] for k in ("P3-1", "P3-4", "P3-5", "P3-6")})
    it6, k6, _ = K.items_p3(r5, PARAMS, R.READY_FLAT_S, ready_judged=False, g6=True, allow_stop=True)
    CD.apply_ready_none(it6, k6, r5)
    check("CD-5 no READY: recorded P3-6 keeps record with value 해당 없음(READY 없음); G6-6 미달",
          it6["P3-6"]["verdict"] == "record" and it6["P3-6"]["value_cd5"] == CD.NA_NO_READY
          and it6["G6-6"]["verdict"] == "fail")
    gi = {k: {"verdict": "na"} for k in CD.P3_KEYS}
    gk = list(CD.P3_KEYS)
    check("CD-4 guard: all P3 grade items 해당 없음 -> row item CD-4_grade_guard 판정 불가",
          CD.scm_grade_guard(gi, gk)["verdict"] == "indeterminate" and "CD-4_grade_guard" in gk)
    # ---- CD-6 targets, CD-1 C-5 rows
    it_t = {"T4-0": {"verdict": "pass"}, "T4": {"verdict": "pass", "over_0p6kN": 0}, "T5": {"verdict": "pass"}}
    keys_t = ["T4-0", "T4", "T5", "J-P3"]
    CD.apply_t45_targets(it_t, keys_t, ns(case="E_G4_Fs4", engine="l2b"))
    check("CD-6 E_G4_Fs4 (not in v5 rev6 3 rows 1-18) -> T4-0 / T4 / T5 해당 없음(대상 행 아님), out of keys",
          keys_t == ["J-P3"] and it_t["T4"]["verdict"] == "na" and it_t["T4"]["value"] == CD.NA_NOT_TARGET)
    keys_t2 = ["J-P3"]
    CD.apply_t45_targets({}, keys_t2, ns(case="E_RE1bF_Fs8_LS4", engine="l2b"))
    check("CD-6 E_RE1bF_Fs8_LS4 (row 13-18) -> T4-0 / T4 / T5 graded; 18 target rows",
          keys_t2 == ["J-P3", "T4-0", "T4", "T5"] and len(CD.T45_TARGET_ROWS) == 18)
    f_c5 = _l2b_case(tmp, "S8c5", name="K0_top_fup3.2_Fs0")
    write_judge_doc(s8c, f_c5, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
    B5.AUX, B5.CTX = {}, {}
    i5, k5b, _, rec5 = B5.judge_row(C.load_row(f_c5, "l2b", L2B_ARGV), {"case": "K0_top_fup3.2_Fs0"}, "stage3",
                                    PARAMS)
    check("CD-1 C-5 L2b target row: keys = T4-0 / T4 / T5, J-P3, J11, CD-2; H-9 and K1_class not graded",
          set(k5b) == {"T4-0", "T4", "T5", "J-P3", "J11_window", "CD-2"} and not rec5
          and i5["H-9"].get("cd1_role"), k5b)
    s5 = write_scm(tmp / "r24" / "c5scm", sp)
    write_p37_record(s5, sp, [(20.0, 26.0)], _p37_profile(600.0), meta=(23.0, 24.0))
    i5s, k5s, _, _ = B5.judge_row(C.load_row(s5, "scm", SCM_VB_ARGV), {"case": "c5scm"}, "stage3", PARAMS)
    check("CD-1 / CD-4 C-5 SCM row: P3-1..P3-8 (rev25: P3-6 graded, 421.1 limit), FAULT0 graded; P3-9 record; "
          "T4 / T5 해당 없음", {"P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-6", "P3-7", "P3-8", "FAULT0"} <= set(k5s)
          and not {"P3-9", "T4", "identity"} & set(k5s) and i5s["T4"]["value"] == CD.NA_NOT_TARGET
          and i5s["P3-6"]["judged"] is True, k5s)
    ec = B5.engine_counts([{"engine": "l2b"}] * 24 + [{"engine": "scm"}] * 10)
    check("CD-1 C-5 engine counts L2b 24 / SCM 10 -> S-15", "S-15" in ec.get("stop", ""), ec)
    # ---- CD-7 reasons, CD-11 item list
    rows7 = [{"case": "a", "status": "판정 불가", "judged_keys": ["X"], "items": {"X": {"verdict": "indeterminate"}}},
             {"case": "b", "status": "판정 불가", "judged_keys": ["Y"],
              "items": {"Y": {"verdict": "indeterminate", "reason": "원 입력 결측 (x)"}}}]
    empty = CD.attach_reasons(rows7)
    check("CD-7: empty reason detected (item and row), filled reason kept as row reason",
          "a: X" in empty and "a: row" in empty and rows7[1][CD.ROW_REASON_KEY].startswith("Y: 원 입력 결측"), empty)
    rows11 = [{"case": "a", "status": "통과", "judged_keys": ["CD-2", "J-P3"],
               "items": {"CD-2": {"entries": [{"item": CD.ITEM_P4_OUT, "use": "judged", "handling": "recalc",
                                               "verdict": "pass", "cd3_sub_id": "W 밖"},
                                              {"item": "S8-L5", "use": "record", "handling": "original_other",
                                               "verdict": "record"}]},
                         "J-P3": {"verdict": "na"}}},
              {"case": "b", "status": "통과", "judged_keys": ["D2x"], "items": {"D2x": {"verdict": "record"}}}]
    for e in rows11[0]["items"]["CD-2"]["entries"]:
        e["table_line"] = CD._table_line(e["item"], e["handling"])
    lst = CD.item_list("C-5", rows11)
    by11 = {x["common_id"]: x for x in lst["rows"][0]["items"]}
    check("CD-11: CD-2 expanded (counted judge item = 등급 항목 'CD-2 표 5줄', record kind = 기록), J-P3 등급 항목 "
          "'CD-1 ①' (해당 없음), row without a graded item -> stop",
          by11[CD.ITEM_P4_OUT]["class"] == CD.CLASS_GRADED and by11[CD.ITEM_P4_OUT]["clause_id"] == "CD-2 표 5줄"
          and by11[CD.ITEM_P4_OUT]["method"] == "재계산" and by11["S8-L5"]["class"] == CD.CLASS_RECORD
          and by11["J-P3"]["clause_id"] == "CD-1 ①" and "b: 등급 항목 0" in lst.get("stop", ""), lst)
    def fin(bundle, engine):
        rows_f = [{"case": "a", "engine": engine, "status": "판정 불가", "judged_keys": ["X"],
                   "items": {"X": {"verdict": "indeterminate"}}}]
        b = {"status": "판정 불가", "stops": []}
        p2_chrono.finish_rev24(bundle, rows_f, b, None)
        return b
    b67, b3, b1 = fin("C-6C7", "scm"), fin("C-3", "scm"), fin("C-1", "l1r")
    check("CD-7 scope: C-6C7 not checked; C-3 SCM row empty reason -> stop; C-1 L1-R row outside (no CD-7 stop, "
          "CD-11 scope note)", "cd7_empty_reasons" not in b67 and not b67["stops"]
          and any(s.startswith("CD-7") for s in b3["stops"]) and b1["cd7_empty_reasons"] == []
          and b1["cd11_item_list"]["rows"][0].get("scope", "").startswith("L1-R"), (b67, b3["stops"], b1))
    # ---- CD-8 C-8 record, C-8a S-9 with the R3d output
    r8 = scm_row(tmp / "r24", copy.deepcopy(sp), "oc5_Kc3_VB_top")
    write_p37_record(r8.folder, sp, [(20.0, 26.0)], _p37_profile(600.0), meta=(23.0, 24.0))
    r8 = C.load_row(r8.folder, "scm", ["run_S9.py", "level", "--crawler-kn-scale", "3"])
    i8, k8, _, rec8 = B8.judge_row(r8, {"case": "oc5_Kc3_VB_top"}, "OC5", PARAMS)
    v8 = i8["CD-8_record"]
    check("CD-8: record values written (F^a / F^t minima, LAS-b start text, k = 3 from argv, P3-7 value), "
          "기록 완료", rec8 and "CD-8_record" in k8 and not v8["missing"] and v8["values"]["crawler_kn_scale"] == 3.0
          and v8["values"]["las_start_s"] == "시작 없음" and v8["values"]["P3-7"] in ("pass", "fail"), v8["missing"])
    m74 = {"m_N": 9000.0, "per_leg": {"min_leg": "FR"}}
    r3d = tmp / "r24_r3d_c8.json"
    r3d.write_text(json.dumps({"rows": [{"case": r8.case, "items": {"m_7_4": m74}}]}), encoding="utf-8")
    CD.CONTEXT["r3d_c8"] = str(r3d)
    s9 = CD.c8a_s9_record(r8, m74)
    check("CD-8 C-8a S-9: m and minimum leg equal R3d -> L-5 known limit, no stop",
          s9["r3d_equal"] and "stop" not in s9 and s9["known_limit"].startswith("L-5"), s9)
    s9b = CD.c8a_s9_record(r8, dict(m74, m_N=9001.0))
    check("CD-8 C-8a S-9: m differs from R3d -> 원판 7.4 stop", "S-9" in s9b.get("stop", ""), s9b)
    CD.CONTEXT["r3d_c8"] = str(tmp / "absent.json")
    check("CD-8 C-8a S-9 without the R3d output -> stop", "S-9" in CD.c8a_s9_record(r8, m74).get("stop", ""))
    check("CD-8 C-8a identified by criteria id, else by Kc3 + VB in the row name",
          CD.is_c8a({"criteria_id": "C-8a"}, ns(case="x")) and not CD.is_c8a({"criteria_id": "C-8b"}, r8)
          and CD.is_c8a({}, r8))
    # ---- CD-9 C-4 record
    r9 = scm_row(tmp / "r24", copy.deepcopy(sp), "c4_rigid")
    res9 = json.loads((r9.folder / "result.json").read_text(encoding="utf-8"))
    res9["args"]["rigid_base"] = "FR"
    (r9.folder / "result.json").write_text(json.dumps(res9), encoding="utf-8")
    write_p37_record(r9.folder, sp, [(20.0, 26.0)], _p37_profile(600.0), meta=(23.0, 24.0))
    import p2_b_c4 as B4
    i9, k9, _, _ = B4.judge_row(C.load_row(r9.folder, "scm", SCM_VB_ARGV), {}, "record_D8_G6", PARAMS)
    c9 = i9["CD-9_record"]
    check("CD-9: rigid_base row -> P3-5 해당 없음(rigid_base), values complete -> 기록 완료, row key CD-9_record",
          k9 == ["CD-9_record"] and c9["values"]["P3-5"] == CD.NA_RIGID_BASE and c9["record_status"] == "기록 완료",
          c9["missing"])
    i9["P3-3"]["min_N"] = None
    check("CD-9: per-leg minimum after departure absent -> 기록 불완전",
          CD.c4_record(C.load_row(r9.folder, "scm", SCM_VB_ARGV), i9)["record_status"] == "기록 불완전")
    # ---- CD-2 (1) judge provenance
    pv = CD.judge_provenance(REPO)
    keep = CD.JUDGE_CODE_PATHS
    CD.JUDGE_CODE_PATHS = keep + ("06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/p2_rules.py",)
    pv2 = CD.judge_provenance(REPO)
    CD.JUDGE_CODE_PATHS = keep
    check("CD-2 (1): 03_src / run_S8C / run_S6C equal b9f5707 -> ok with commit and file sha; a differing path "
          "-> S-11", pv["ok"] and len(pv["checkout_commit"]) == 40 and all(pv["judge_files_sha256"].values())
          and not pv2["ok"] and pv2["stop"].startswith("S-11"), (pv, pv2.get("stop")))
    CD.CONTEXT.clear()


def _jp3_scm_row(tmp, name, sp, rod=True, ebc=True, argv=None):
    """SCM row with the ③ settings (tracked_bound, request on) for the rev25 J-P3 tests."""
    f = write_scm(tmp / "r25" / name, copy.deepcopy(sp))
    res = json.loads((f / "result.json").read_text(encoding="utf-8"))
    res["controller_meta"]["two_pressure"] = {"settings": {"extend_start_rule": "tracked_bound"}}
    res["v5_hydraulics"]["hydraulic_options"]["extend_start_tracked"] = True
    if ebc:
        res["hydraulics_record"]["extend_bound_check"] = {"rule": "ext_moving", "breach_reads": [0, 0, 0, 0],
                                                          "margin_used_reads": [0, 0, 0, 0]}
    (f / "result.json").write_text(json.dumps(res), encoding="utf-8")
    if rod is not None:
        write_rod_record(f, sp, 5e5 if rod else np.nan)
    return C.load_row(f, "scm", argv or SCM_VB_ARGV)


def t_rev25(tmp):
    """rev25 R25-2 [경로 2] 1 (rev25 definitions) and 2 (rev24 defect fixes (가)-(나); (다) is the K-10 comparator)."""
    import types
    import p2_b_c3 as B3
    import p2_cd as CD
    ns = types.SimpleNamespace
    s8c = tmp / "r25_s8c"
    CD.CONTEXT.clear()
    CD.CONTEXT.update(repo=REPO, s8c_dir=str(s8c))
    # ---- (가) case `*` items counted as the row's items, CD-11 id suffix
    f1 = _l2b_case(tmp, "S8st_a")
    write_judge_doc(s8c, f1, [_jr(CD.ITEM_C1), _jr("6 relevel time"), _jr("I1 star", passed=False, case="*"),
                              _jr("S8-L5 crawler label", passed=None, kind="record", case="*")])
    b1 = CD.cd2_items(C.load_row(f1, "l2b", L2B_ARGV), PARAMS)
    star = [e for e in b1["entries"] if e["case_star"]]
    check("(가) case `*` judged item passed False counted -> CD-2 미달; ids carry ' [case *]', table line 12",
          b1["verdict"] == "fail" and len(star) == 2 and star[0]["common_id"] == "I1 star [case *]"
          and star[0]["table_line"] == 12, b1["entries"])
    # ---- CD-2 C1 event cut (decision 98 2)
    def l2b_ev(group, dip_rel, event_rel):
        def fn(r):
            r["event_t_s"] = event_rel
        f = _edit_result(_l2b_case(tmp, group + "_src", dip=(1, dip_rel, dip_rel + 0.05, 5000.0)),
                         tmp / "r25" / group / "case", lambda r: (fn(r), r["settings"].update(
                             s8={"crawler_contact": "nsc_compliant", "crawler_check_passed": True})))
        write_judge_doc(s8c, f, [_jr(CD.ITEM_C1), _jr("6 relevel time")])
        return CD.cd2_items(C.load_row(f, "l2b", L2B_ARGV), PARAMS)
    b_after = l2b_ev("S8ev_after", 30.0, 28.0)
    b_before = l2b_ev("S8ev_before", 22.0, 28.0)
    b_none = l2b_ev("S8ev_none", 30.0, None)
    c1a = b_after["entries"][0]["recalc"]
    check("CD-2 C1 event cut: dip after event_t_s (numeric, non-event row) excluded -> pass; dip before -> 미달; "
          "event_t_s null -> no cut -> 미달", b_after["verdict"] == "pass" and abs(c1a["event_cut_s"] - 31.0) < 1e-9
          and b_after["event"]["class"] == "none" and b_before["verdict"] == "fail" and b_none["verdict"] == "fail",
          (c1a, b_before["verdict"], b_none["verdict"]))
    # ---- (나) P3-7 loaded threshold 0.01 x mass_scale x W_ref
    sp = scm_spec()
    sp.update(crawler=[("ramp", 19.0, 19.5)], recontacts=[(20.0, 23.0, 4000.0)])

    def p37_scaled(name, scale):
        f = write_scm(tmp / "r25" / name, copy.deepcopy(sp))
        write_p37_record(f, sp, [(20.0, 26.0)], _p37_profile(600.0), meta=(23.0, 24.0))
        res = json.loads((f / "result.json").read_text(encoding="utf-8"))
        if scale is not None:
            res["args"]["mass_scale"] = scale
        (f / "result.json").write_text(json.dumps(res), encoding="utf-8")
        return CD.p3_7(C.load_row(f, "scm", SCM_VB_ARGV), PARAMS)
    p1, p11, pn = p37_scaled("p37_s1", 1.0), p37_scaled("p37_s11", 1.1), p37_scaled("p37_snone", None)
    check("(나) P3-7 threshold 0.01 x mass_scale x W_ref: crawler 4000 N at window ends is loaded at x1 (3765.8 N), "
          "not at x1.1 (4142.4 N); absent mass_scale = 1",
          abs(p1["loaded_threshold_N"] - 0.01 * W_REF) < 1e-6 and abs(p1["rise_min_loaded_N"] - 6000.0) < 1e-3
          and abs(p11["loaded_threshold_N"] - 0.011 * W_REF) < 1e-6 and p11["rise_min_loaded_N"] is None
          and p11["verdict"] == "pass" and pn["mass_scale"] == 1.0, (p1, p11))
    # ---- CD-4 P3-6 limit (spec 421.1) and role
    lim = lambda a: CD.p3_6_limit(ns(result={"args": a}))[0]   # noqa: E731
    check("CD-4 P3-6 limit: slope 120; flat B rear J1 100; flat B G1 with RL+RR:J1 patch 100; flat B G1 with FL:J1 "
          "patch 90; pad A J1 90; unreadable patch -> None",
          lim({"floor_roll": 0.5}) == 120.0 and lim({"pad_variant": "dwg_rear250", "soil": "J1"}) == 100.0
          and lim({"pad_variant": "dwg_rear250", "soil": "G1", "soil_patch": "RL+RR:J1"}) == 100.0
          and lim({"pad_variant": "dwg_rear250", "soil": "G1", "soil_patch": "FL:J1"}) == 90.0
          and lim({"pad_variant": "cad330", "soil": "J1"}) == 90.0 and lim({"soil_patch": "nonsense"}) is None)
    sp5 = scm_spec()
    sp5["phases"] = [(8.1, "check"), (12.0, "touch"), (20.0, "level"), (30.0, "done")]
    r5 = scm_row(tmp / "r25", sp5, "noready")
    it5, k5, _ = K.items_p3(r5, PARAMS, R.READY_FLAT_S, ready_judged=False, g6=False, allow_stop=True)
    CD.set_p3_6(it5, k5, r5, judged=True)
    CD.apply_ready_none(it5, k5, r5)
    it6, k6, _ = K.items_p3(r5, PARAMS, R.READY_FLAT_S, ready_judged=False, g6=False, allow_stop=True)
    CD.set_p3_6(it6, k6, r5, judged=False)
    CD.apply_ready_none(it6, k6, r5)
    check("CD-5 P3-6 row: judged (C-5 SCM) without READY -> 미달 and graded; recorded -> 해당 없음(READY 없음), not "
          "graded; limit 120 s (slope row)", it5["P3-6"]["verdict"] == "fail" and "P3-6" in k5
          and it5["P3-6"]["limit_s"] == 120.0 and it6["P3-6"]["value_cd5"] == CD.NA_NO_READY and "P3-6" not in k6)
    # ---- C-3 G6 table
    g = copy.deepcopy(scm_spec())
    g["floor"] = (0.0, 0.0)
    rg = scm_row(tmp / "r25", g, "c3g6")
    write_p37_record(rg.folder, g, [], meta=(None, None))
    rg = C.load_row(rg.folder, "scm", SCM_V0_ARGV)
    i3, k3, _, _ = B3.judge_row(rg, {}, "P3_G6", PARAMS)
    check("C-3 G6 table: grade keys P3-1..P3-5, G6-6, P3-8, READY_le_120s, P3-7; FAULT0 / P3-6 records",
          {"P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "G6-6", "P3-8", "READY_le_120s", "P3-7"} <= set(k3)
          and not {"FAULT0", "P3-6", "P3-9"} & set(k3) and i3["G6-6"]["verdict"] == "pass"
          and i3["READY_le_120s"]["verdict"] == "pass" and i3["P3-6"]["judged"] is False, k3)
    r5g = scm_row(tmp / "r25", copy.deepcopy(sp5), "c3g6_noready")
    write_p37_record(r5g.folder, sp5, [], meta=(None, None))
    i3n, k3n, _, _ = B3.judge_row(C.load_row(r5g.folder, "scm", SCM_V0_ARGV), {}, "P3_G6", PARAMS)
    check("C-3 G6 table without READY: G6-4 / G6-5 (P3-4 / P3-5) 해당 없음, G6-6 and READY_le_120s 미달",
          i3n["P3-4"]["verdict"] == "na" and i3n["P3-5"]["verdict"] == "na" and i3n["G6-6"]["verdict"] == "fail"
          and i3n["READY_le_120s"]["verdict"] == "fail")
    # ---- CD-1 J-P3 (v5 rev9 3.2) and CD-11 gates on C-1..C-3 rows
    sp_j = scm_spec()
    jp = K.jp3_item(_jp3_scm_row(tmp, "jp_ok", sp_j))
    j5 = K.jp3_item(_jp3_scm_row(tmp, "jp_nan", sp_j, rod=False))
    j4 = K.jp3_item(_jp3_scm_row(tmp, "jp_norec", sp_j, rod=None, ebc=False))
    j2 = K.jp3_item(_jp3_scm_row(tmp, "jp_noebc", sp_j, ebc=False))
    joff = K.jp3_item(_jp3_scm_row(tmp, "jp_off", sp_j, argv=SCM_V0_ARGV))
    check("CD-1 J-P3 (v5 rev9 3.2): rod + record -> pass; NaN rod + record #5, no reading no record #4, rod without "
          "record #2 -> setting-defect stops; ③ off -> 해당 없음(③ 끔)",
          jp["verdict"] == "pass" and "#5" in j5.get("stop", "") and "#4" in j4.get("stop", "")
          and "#2" in j2.get("stop", "") and joff.get("stop", "").startswith("S-2"), (jp, j5, j4, j2, joff))
    d_off = _jp3_scm_row(tmp, "jp_off2", sp_j, argv=SCM_V0_ARGV)
    res_off = json.loads((d_off.folder / "result.json").read_text(encoding="utf-8"))
    res_off["controller_meta"]["two_pressure"]["settings"].pop("extend_start_rule")
    res_off["v5_hydraulics"]["hydraulic_options"].pop("extend_start_tracked")
    (d_off.folder / "result.json").write_text(json.dumps(res_off), encoding="utf-8")
    jo = K.jp3_item(C.load_row(d_off.folder, "scm", SCM_V0_ARGV))
    check("CD-1 J-P3 ③ off row -> na, value 해당 없음(③ 끔)", jo["verdict"] == "na" and jo["value"] == K.JP3_NA_OFF, jo)
    row_j = _jp3_scm_row(tmp, "jp_gate", sp_j)
    items_g = {"identity": {"verdict": "indeterminate", "reason": "4.2 check failed"},
               "K1_class": {"verdict": "record", "cls": "inactive"}, "T4-0": {"verdict": "indeterminate"},
               "R9-1_expect_controller": {"verdict": "pass"}, "P3-1": {"verdict": "pass"}}
    keys_g = ["identity", "K1_class", "T4-0", "R9-1_expect_controller", "P3-1"]
    CD.apply_rev25_row("C-3", row_j, items_g, keys_g, record_row=False)
    check("CD-11 gates: identity / K1_class / T4-0 / R9-1 leave the grade; failing identity and T4-0 get stops; "
          "J-P3 added as a grade item on a ③-on C-3 row",
          keys_g == ["P3-1", "J-P3"] and items_g["identity"]["stop"].startswith("CD-11 관문 실패 (identity)")
          and items_g["T4-0"]["stop"].startswith("CD-11 관문 실패 (T4-0)") and "stop" not in items_g["K1_class"]
          and "stop" not in items_g["R9-1_expect_controller"], (keys_g, items_g))
    items_r, keys_r = {}, []
    CD.apply_rev25_row("C-2", row_j, items_r, keys_r, record_row=True)
    check("CD-1 J-P3 on a record row (PS-c base) -> record only (not graded)", keys_r == [] and "J-P3" in items_r)
    # ---- CD-11 list: classes, clause ids (C-3 G6, 427.9 expansion, gates)
    rows_c3 = [{"case": "g", "status": "통과", "engine": "scm", "judged_keys": ["P3-1", "G6-6", "READY_le_120s", "P3-7"],
                "items": {"P3-1": {"verdict": "pass"}, "G6-6": {"verdict": "pass"}, "READY_le_120s": {"verdict": "pass"},
                          "P3-7": {"verdict": "pass", "interval": "x"}, "FAULT0": {"verdict": "pass"},
                          "identity": {"verdict": "pass"}, "P3-9": {"verdict": "record"}}},
               {"case": "s", "status": "통과", "engine": "scm", "judged_keys": ["safe_stop_427_9"],
                "items": {"safe_stop_427_9": {"conditions": {c: True for c in CD.SAFE_STOP_CONDITIONS},
                                              "verdict": "allowed_stop"}}}]
    l3 = CD.item_list("C-3", rows_c3)
    e3 = {x["common_id"]: x for x in l3["rows"][0]["items"]}
    e_ss = [x["common_id"] for x in l3["rows"][1]["items"]]
    check("CD-11 C-3: G6 ids 'CD-11 G6 대응표', P3-7 'CD-4 P3-7', FAULT0 기록, identity 관문 'CD-11 관문'; 427.9 row "
          "expanded to 427.9-1..5 ('명세 427.9 조건 n')",
          e3["P3-1"]["clause_id"] == "CD-11 G6 대응표" and e3["READY_le_120s"]["clause_id"] == "CD-11 G6 대응표"
          and e3["P3-7"]["clause_id"] == "CD-4 P3-7" and e3["P3-7"]["interval"] == "x"
          and e3["FAULT0"]["class"] == CD.CLASS_RECORD and e3["identity"]["class"] == CD.CLASS_GATE
          and e3["identity"]["clause_id"] == "CD-11 관문" and e_ss == list(CD.SAFE_STOP_IDS)
          and l3["rows"][1]["items"][2]["clause_id"] == "명세 427.9 조건 3" and not l3["problems"], l3)
    l_rec = CD.item_list("C-2", [{"case": "base", "status": "기록 완료", "engine": "scm", "judged_keys": ["P3-1"],
                                  "items": {"P3-1": {"verdict": "pass"}}}])
    check("CD-11 record row (PS-c base) exempt from 'grade item >= 1', its items listed as 기록",
          not l_rec["problems"] and l_rec["rows"][0]["items"][0]["class"] == CD.CLASS_RECORD, l_rec)
    # ---- CD-8 values (decision 98 4 / 100 1)
    import p2_b_c8 as B8
    sp8 = copy.deepcopy(scm_spec())
    sp8.update(crawler=[("ramp", 22.95, 23.0)], recontacts=[], dips=[(2, 23.5, 23.6, 20000.0), (2, 35.0, 35.1, 15000.0)])
    r8 = scm_row(tmp / "r25", sp8, "oc5_rigid_Kc1_V0")
    res8 = json.loads((r8.folder / "result.json").read_text(encoding="utf-8"))
    res8["args"]["rigid_base"] = "FR"
    (r8.folder / "result.json").write_text(json.dumps(res8), encoding="utf-8")
    write_p37_record(r8.folder, sp8, [(20.0, 26.0)], _p37_profile(600.0), meta=(23.0, 24.0))
    i8, _, _, _ = B8.judge_row(C.load_row(r8.folder, "scm", SCM_V0_ARGV), {"criteria_id": "C-8b"}, "OC5", PARAMS)
    v8 = i8["CD-8_record"]["values"]
    check("CD-8: F^a = min t_D..end (RL 15 kN at 35.0), F^t = min [t_D, t_D + 8 s) (RL 20 kN at 23.5); rigid_base P3-5 "
          "해당 없음; SCM D8 t_lift / min / end attitude / pad lift; G6 values with READY_le_120s; 기록 완료",
          v8["Fa_min_after_departure"]["min_N"][2] == 15000.0 and v8["Ft_min_transient_8s"]["min_N"][2] == 20000.0
          and abs(v8["Ft_min_transient_8s"]["t_s"][2] - 23.5) < 1e-9 and v8["P3-5"] == CD.NA_RIGID_BASE
          and v8["D8_t_lift_s"] is not None and v8["D8_min_after_t_lift"]["leg"] == "RL"
          and v8["D8_pad_lift_samples"] == 0 and v8["G6"]["READY_le_120s"] == "pass"
          and not i8["CD-8_record"]["missing"], (v8, i8["CD-8_record"]["missing"]))
    CD.CONTEXT.clear()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp")
    ap.add_argument("--lawlock-record", help="SCM row folder recorded by the runner at 7527fc3 (optional)")
    ap.add_argument("--rules-repo", help="checkout holding sealed rule files this checkout lacks (seal worktree)")
    a = ap.parse_args()
    tmp = Path(a.tmp) if a.tmp else Path(tempfile.mkdtemp(prefix="p2chrono_"))
    if a.rules_repo and not R.seal_check(REPO)["ok"]:
        CLI_REPO[:] = ["--repo", str(a.rules_repo)]
    tmp.mkdir(parents=True, exist_ok=True)
    t_classify()
    t_scm(tmp)
    t_rev8_j11(tmp, scm_spec())
    t_rev9(tmp, scm_spec())
    t_rev11(tmp, scm_spec())
    t_rev8_record(a.lawlock_record)
    t_l2b(tmp)
    t_c67(tmp)
    t_safe_stop(tmp)
    t_psc(tmp)
    t_e7_tool(tmp)
    t_pairs()
    t_tlift_sus(tmp)
    t_seal(tmp, a.rules_repo)
    t_cli(tmp)
    t_resolve(tmp)
    t_rev24(tmp)
    t_rev25(tmp)
    n_fail = sum(1 for r in RESULTS if not r["ok"])
    tool_sha, per = p2_chrono.tool_sha(None)
    print(json.dumps({"tool": "test_p2_synthetic.py", "tests": len(RESULTS), "failed": n_fail,
                      "common_tool_sha256": tool_sha, "tmp": str(tmp)}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
