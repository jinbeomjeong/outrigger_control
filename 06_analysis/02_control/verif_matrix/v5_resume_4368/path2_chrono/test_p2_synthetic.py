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
    it18, k18, _ = K.items_c5(C.load_row(d18, "scm", SCM_VB_ARGV), PARAMS)
    check("J-P3 breach sum 1 -> fail + H-7 (rev8 3.2)", it18["J-P3"]["verdict"] == "fail"
          and it18["J-P3"].get("stop") == "H-7 (rev8 3.2)", it18["J-P3"])
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


def t_seal(tmp):
    repo = tmp / "repo"
    for rel, _, _ in R.SEALED:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, repo / rel)
        if rel in R.RAW_ONLY:
            sc = Path(rel).with_suffix(".sha256")
            shutil.copyfile(REPO / sc, repo / sc)
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
    check("seal: rev10 listed, raw only, 62a0bd8d, only rev10 wins (rev10 R10-3)",
          rel10 in R.RAW_ONLY and any(r == rel10 and w.startswith("62a0bd8d") and "wins" in role
                                      for r, w, role in R.SEALED)
          and [r for r, w, role in R.SEALED if "wins" in role] == [rel10])
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
    # gs-load on the G-S row (read-only, no verdicts in the output)
    out4 = tmp / "gs_load.json"
    proc4 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "gs-load",
                            "--batch", str(bdir / "batch.json"), "--out", str(out4),
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
    g10 = g4.get("rev10_R10_2_gs_items") or {}
    check("CLI gs-load rev10 R10-2 items: unstamped folder without batch key -> batch name unknown, S-11 row 1,"
          " rev10 seal match",
          g10.get("r10_1b_rows_per_case", {}).get("batch_name_unknown") == 1 and g10.get("r10_2_s11_rows") == 1
          and g10.get("rev10_seal") == "match", g10)
    proc4b = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "gs-load",
                             "--batch", str(bdir / "batch.json"), "--out", str(tmp / "gs_load_noman.json"),
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
    proc5 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-3",
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
        {"case": "X_LS1", "argv": argv5, "criteria_id": "C-5", "v5_setting": "LS1"},
        {"case": "Y", "argv": argv5, "criteria_id": "C-5", "v5_setting": "VB"}]}), encoding="utf-8")
    man_p = tmp / "manifest_p2c5.json"
    man_p.write_text(json.dumps({"batches": {"P2C5": {"rows": [{"case": "X_LS1", "v5_setting": "LS1"},
                                                                {"case": "Y", "v5_setting": "LS4"}]}}}),
                     encoding="utf-8")
    out6 = tmp / "o6.json"
    proc6 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-5",
                            "--batch", str(b5 / "batch.json"), "--manifest", str(man_p), "--out", str(out6)],
                           capture_output=True, text=True, encoding="utf-8")
    o6 = json.loads(out6.read_text(encoding="utf-8")) if out6.exists() else {}
    ls6 = (o6.get("bundle_result") or {}).get("rev9_R9_4_ls")
    check("CLI C-5 R9-4: LS1/LS1 -> LS, VB/LS4 -> 판정 불가; law_locked missing -> R9-5 stops; exit 1",
          proc6.returncode == 1 and ls6 == {"ls_rows": 1, "not_ls_rows": 0, "not_judgeable_rows": 1}
          and sum("R9-5" in s for s in (o6.get("bundle_result") or {}).get("stops", [])) == 2,
          (proc6.returncode, ls6, proc6.stdout[-300:] + proc6.stderr[-300:]))
    proc7 = subprocess.run([sys.executable, "-I", "-B", str(HERE / "p2_chrono.py"), "judge", "--bundle", "C-5",
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
    d3, how3 = p2_chrono.resolve_dir(case, bdir, root, {})
    check("resolve: no row log, one tag folder -> tag_glob", how3 == "tag_glob" and d3 == want / only, (d3, how3))
    plc = p2_chrono.placement_record({"pool": "pcore", "planned_pool": "pcore", "placement_applied": {"mask": "0xFF"},
                                      "argv": []},
                                     {"placement": {"affinity_mask_process": "0xFF", "affinity_mask_ok": False}},
                                     {"affinity_masks": {"pcore": "0xFF"}})
    check("R7-6 placement record: mask keys copied, affinity_mask_ok false -> note",
          plc["affinity_mask_process"] == "0xFF" and plc["batch_affinity_masks"] == {"pcore": "0xFF"}
          and any("affinity_mask_ok" in n for n in plc["notes"]), plc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp")
    ap.add_argument("--lawlock-record", help="SCM row folder recorded by the runner at 7527fc3 (optional)")
    a = ap.parse_args()
    tmp = Path(a.tmp) if a.tmp else Path(tempfile.mkdtemp(prefix="p2chrono_"))
    tmp.mkdir(parents=True, exist_ok=True)
    t_classify()
    t_scm(tmp)
    t_rev8_j11(tmp, scm_spec())
    t_rev9(tmp, scm_spec())
    t_rev8_record(a.lawlock_record)
    t_l2b(tmp)
    t_c67(tmp)
    t_seal(tmp)
    t_cli(tmp)
    t_resolve(tmp)
    n_fail = sum(1 for r in RESULTS if not r["ok"])
    tool_sha, per = p2_chrono.tool_sha(None)
    print(json.dumps({"tool": "test_p2_synthetic.py", "tests": len(RESULTS), "failed": n_fail,
                      "common_tool_sha256": tool_sha, "tmp": str(tmp)}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
