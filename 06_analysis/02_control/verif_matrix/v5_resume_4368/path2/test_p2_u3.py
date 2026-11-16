"""Self-tests of p2_u3.py on synthetic records only."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_u3", HERE / "p2_u3.py")
u3 = importlib.util.module_from_spec(spec)
sys.modules["p2_u3"] = u3
spec.loader.exec_module(u3)
IS_P3 = lambda t: t is not None and "_P3" in t   # noqa: E731 - stand-in for v5_options in unit tests


def rec(i, suite="slope", verdict="pass", setting="V0", tag=None, flags=(), rod=False, j_p3=None, fb=None, **kw):
    v5 = {"v5_setting": setting, "controller_tag": tag or u3.TAG[setting], "definition_sha256": "x", "code": {},
          "head_only_declared": suite != "g8", "has_rod_reading": rod,
          "j_p3": j_p3 or ("no_rod_reading" if setting == "VB" else "not_applicable"),
          "commands_sha256": f"{i:064x}"}
    if fb is not None:
        v5["rod_pressure_fallback_events"] = fb
    r = {"suite": suite, "id": f"H1|J1|B|top|k{i}", "verdict": verdict, "flags": list(flags), "t_ready_s": 50.0,
         "min_force_kN": 40.0, "max_stroke_mm": 500.0, "rut_ready_mm": 40.0, "att_end_deg": [0.01, -0.02], "v5": v5}
    if suite in u3.SETTLE_V2_SUITES and "settle_v2" not in kw:
        r["settle_v2"] = settle_block(ok=verdict != "settle_check_fail")
    r.update(kw)
    return r


def settle_block(ok=True, gate="judged", pen=(-10.0, -10.0, -10.0, -10.0), gap=(10.0, 10.0, 10.0, 10.0)):
    """A settle v2 record whose result matches the 398.3 recount (pad xy 1 m, attitude change 0)."""
    pen = list(pen) if ok else [p + 2.0 for p in pen]
    plus = [p + g for p, g in zip(pen, gap)]
    return {"status": "checked", "gate": "settle_check_fail" if not ok else gate,
            "tolerances": {"gap_mm": 1.0, "attitude_floor_deg": 0.005, "attitude_add_deg": 0.002},
            "inputs": {"pen_inst_mm": pen, "pad_xy_m": [[1, 1], [1, -1], [-1, 1], [-1, -1]], "d_attitude_deg": [0.0, 0.0],
                       "gap_target_mm": list(gap), "residual_deg": 0.001, "attitude_error_deg": 0.004,
                       "gap_target_source": "table", "table_gap_target_mm": list(gap)},
            "result": {"pen_mean_mm": pen, "pen_plus_gap_mm": plus, "gap_ok": [abs(x) <= 1.0 for x in plus],
                       "attitude_tol_deg": 0.005, "attitude_ok": True, "ok": ok}}


def write(tmp_path, name, recs, meta=None):
    p = tmp_path / name
    p.write_text(json.dumps({"meta": meta or {}, "records": recs}), "utf-8")
    return str(p)


def test_grades():
    assert u3.grade_u3({"verdict": "pass", "flags": []}) == ("pass", None)
    assert u3.grade_u3({"verdict": "pass", "flags": ["P3-2_late_loc_reapproach"]})[0] == "flag"
    assert u3.grade_u3({"verdict": "stroke_limited_stop", "soil_stop": {"pass": True}})[0] == "safe_stop"
    assert u3.grade_u3({"verdict": "stroke_limited_stop", "soil_stop": {"pass": False}})[0] == "fail"
    assert u3.grade_u3({"verdict": "settle_check_fail"})[0] is None


def test_vb_unique_fail_and_table(tmp_path):
    v0 = write(tmp_path, "u3_slope_V0.json", [rec(1), rec(2, verdict="fail"), rec(3, verdict="fail")])
    vb = write(tmp_path, "u3_slope_VB.json", [rec(1, setting="VB", verdict="fail"), rec(2, setting="VB", verdict="fail"),
                                               rec(3, setting="VB")])
    out, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert out["vb_unique_fail"] == ["slope|H1|J1|B|top|k1"]
    assert out["baseline_fail"] == ["slope|H1|J1|B|top|k2"] and out["vb_improve"] == ["slope|H1|J1|B|top|k3"]
    assert out["transition"]["pass"]["fail"] == 1 and out["sentence_VB"]["fail"] == 2
    codes = {s["code"] for s in f.stops}
    assert "G-5" in codes and "G-1" in codes          # counts are not the 1,114 of the rules
    assert "G-4" not in codes and "G-2" not in codes


def test_g8_rod_and_fallback(tmp_path):
    v0 = write(tmp_path, "a_V0.json", [rec(1, suite="g8")])
    vb = write(tmp_path, "a_VB.json", [rec(1, suite="g8", setting="VB", rod=True, j_p3="pass", fb=[{"t": 1}])])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert "G-6" in {s["code"] for s in f.stops} and "G-4" not in {s["code"] for s in f.stops}
    vb = write(tmp_path, "b_VB.json", [rec(1, suite="g8", setting="VB", rod=False, j_p3="no_rod_reading", fb=0)])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert "G-4" in {s["code"] for s in f.stops}


def test_tag_mix(tmp_path):
    v0 = write(tmp_path, "c_V0.json", [rec(1), rec(2, tag="final_C4G2_LAS")])
    _, f = u3.recount_u3([{"setting": "V0", "path": v0}], None, IS_P3)
    assert any(s["code"] == "G-2" and "tags in one file" in s["why"] for s in f.stops)


def test_d1_reuse(tmp_path):
    h1 = tmp_path / "h1.jsonl"
    line = {"job": {"d1": {"key": "D1|H-S-0|J1|T|flat|K1"}, "setting": "VB", "eps": 0.0},
            "d1": {"key": "D1|H-S-0|J1|T|flat|K1|VB|e0"},
            "controller_tag": u3.TAG["VB"], "commands_sha256": f"{7:064x}"}
    h1.write_text(json.dumps(line) + "\n", "utf-8")
    meta = {"v5": {"reuse_d1": {"slope": {"reused": ["D1|H-S-0|J1|T|flat|K1|VB|e0"], "setting": "VB"}}}}
    r = rec(7, setting="VB", reuse="d1", d1_key="D1|H-S-0|J1|T|flat|K1|VB|e0")
    r["u3"] = {"settle_v2": r.pop("settle_v2")}
    vb = write(tmp_path, "d_VB.json", [r], meta)
    out, f = u3.recount_u3([{"setting": "VB", "path": vb}], str(h1), IS_P3)
    assert out["d1_reuse"]["checked"] == 1 and not out["d1_reuse"]["problems"]
    vb = write(tmp_path, "e_VB.json", [rec(7, setting="VB", reuse="d1", reuse_key="D1|H-S-0|J1|T|flat|K1")], meta)
    out, f = u3.recount_u3([{"setting": "VB", "path": vb}], str(h1), IS_P3)
    assert out["d1_reuse"]["problems"]           # rev3 R3-B3: reuse_key is not a record field


def b5(case, ctrl, h="a", lite=True, ov="pass"):
    tag = {"C2": u3.TAG["C2"], "ABL": u3.TAG["ABL"], "IND": "IND", "IND_LAS": "IND_LAS"}[ctrl]
    return {"case": case, "controller": ctrl, "lite_pass": lite, "official_verdict": ov, "crawler_liftoff_fail": False,
            "commands_sha256": h, "v5": {"controller_tag": tag}}


def test_u6(tmp_path):
    recs = [b5(f"c{i}", c, h=f"h{i}{c}") for i in range(3) for c in ("C2", "ABL", "IND")]
    recs[0]["official_verdict"] = "stroke_limited_stop"
    main = tmp_path / "u6_b5_main_VB.json"
    main.write_text(json.dumps({"records": recs}), "utf-8")
    il = [b5(f"c{i}", "IND_LAS", h=(f"h{i}IND" if i < 2 else "zz")) for i in range(3)]
    ilp = tmp_path / "u6_b5_main_VB_IND_LAS.json"
    ilp.write_text(json.dumps({"records": il}), "utf-8")
    out, f = u3.recount_u6([{"controller": None, "path": str(main)}, {"controller": "IND_LAS", "path": str(ilp)}], IS_P3)
    assert out["table"]["C2"]["safe_stop"] == 1 and out["IND_LAS_hash_equal_to_IND"] == 2
    assert out["judged_runs"] == 9
    codes = {s["code"] for s in f.stops}
    assert codes == {"G-1"}                            # 3 cases, rules say 242


def test_rev3_settle_v2_recount():
    assert u3.settle_v2_recount(settle_block())["status"] == "checked"
    assert u3.settle_v2_recount(settle_block())["ok"] is True
    b = settle_block()
    b["result"]["ok"] = False
    assert u3.settle_v2_recount(b)["status"] == "undecidable"            # result differs from the recount
    b = settle_block()
    b["tolerances"]["gap_mm"] = 2.0
    assert u3.settle_v2_recount(b)["status"] == "tolerance_differs"
    g, why, _ = u3.settle_grade({"verdict": "settle_check_fail"}, settle_block(ok=False), None)
    assert g == "fail"
    g, why, _ = u3.settle_grade({"verdict": "settle_check_fail"}, settle_block(ok=True), None)
    assert g == "undecidable"
    g, _, _ = u3.settle_grade({"verdict": "pass"}, {"status": "no_table_check"}, None)
    assert g is None
    g, _, _ = u3.settle_grade({"verdict": "pass"}, None, None)
    assert g == "undecidable"
    b = settle_block()
    b["inputs"]["d_attitude_deg"] = [0.05, 0.0]                         # y * dphi enters pen_mean (mm)
    r = u3.settle_v2_recount(b)
    assert r["status"] == "undecidable" and "pen_mean_mm differs" in r["issues"]


def test_rev3_settle_fail_grade_in_transition(tmp_path):
    v0 = write(tmp_path, "u3_slope_V0.json", [rec(1)])
    vb = write(tmp_path, "u3_slope_VB.json", [rec(1, setting="VB", verdict="settle_check_fail")])
    out, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3)
    assert out["vb_unique_fail"] == ["slope|H1|J1|B|top|k1"] and out["settle_v2"]["fail_confirmed"] == 1


def test_rev3_ind_las_gate(tmp_path):
    recs = [b5(f"c{i}", "IND", h=f"h{i}") for i in range(3)]
    main = tmp_path / "u6_b5_main_VB.json"
    main.write_text(json.dumps({"records": recs}), "utf-8")
    il = [b5("c0", "IND_LAS", h="h0"), b5("c1", "IND_LAS", h="zz"), b5("c2", "IND_LAS", h="h2")]
    il[0]["events"] = [[1.0, "INFO_LIFTOFF_SLOW_END:time"]]           # not a start event
    il[1]["events"] = [[1.0, "INFO_LIFTOFF_SLOW:RL"]]                 # gated: hash may differ
    ilp = tmp_path / "il.json"
    ilp.write_text(json.dumps({"records": il}), "utf-8")
    out, _ = u3.recount_u6([{"controller": None, "path": str(main)}, {"controller": "IND_LAS", "path": str(ilp)}], IS_P3)
    g = out["IND_LAS_gate_R3-B5"]
    assert g["gated"] == 1 and g["not_gated"] == 1 and g["unreadable"] == 1 and g["not_gated_hash_same"] == 1
    assert g["IND_LAS_column"] == "기록 불완전"


def test_rev3_study_key_files_real():
    repo = HERE.parents[4]
    assert {s: len(u3.study_keys(repo, s)) for s in ("B", "C", "D")} == {"B": 84, "C": 34, "D": 33}


def test_rev4_settle_table_target_and_tolerance():
    b = settle_block()
    b["inputs"]["table_gap_target_mm"] = [10.0, 10.0, 10.0, 11.0]
    r = u3.settle_v2_recount(b)
    assert r["status"] == "undecidable" and "gap_target_mm != table_gap_target_mm on a table pad" in r["issues"]
    b = settle_block()
    b["inputs"].pop("table_gap_target_mm")
    assert "table_gap_target_mm missing (F-5)" in u3.settle_v2_recount(b)["issues"]
    b = settle_block()
    b["tolerances"]["gap_mm"] = 1.0 + 5e-10                       # within 1e-9
    assert u3.settle_v2_recount(b)["status"] == "checked"
    b["tolerances"]["gap_mm"] = 1.0 + 1e-6
    assert u3.settle_v2_recount(b)["status"] == "tolerance_differs"


# ------------------------------------------------------------------ R4 (rev16 R16-10 2 (a) (b), RD-7 G-5 / G-6)
def settle_axes(err=(0.004, 0.0075), res=(0.001, 0.006), gap_ok_bool=True):
    """R2 record form: per-axis residual / error lists, result attitude_tol_deg list, gap_ok / attitude_ok bool."""
    b = settle_block()
    b["tolerances"] = {"gap_mm": 1.0, "attitude_min_deg": 0.005, "attitude_residual_margin_deg": 0.002}
    b["inputs"]["residual_deg"] = list(res)
    b["inputs"]["attitude_error_deg"] = list(err)
    tol = [max(0.005, r + 0.002) for r in res]
    ok_axes = [e <= t for e, t in zip(err, tol)]
    b["result"]["attitude_tol_deg"] = tol
    b["result"]["attitude_ok"] = all(ok_axes)
    if gap_ok_bool:
        b["result"]["gap_ok"] = all(b["result"]["gap_ok"])
    b["result"]["ok"] = all(ok_axes) and (b["result"]["gap_ok"] if gap_ok_bool else True)
    return b


def test_r4_settle_v2_per_axis():
    r = u3.settle_v2_recount(settle_axes())
    assert r["status"] == "checked" and r["ok"] is True and r["attitude_tol_deg"] == [0.005, 0.008]
    r = u3.settle_v2_recount(settle_axes(err=(0.004, 0.0081)))       # pitch error over its own tolerance
    assert r["status"] == "checked" and r["ok"] is False
    b = settle_axes()
    b["result"]["attitude_tol_deg"] = [0.005, 0.005]                 # recorded tolerance not per axis
    assert "attitude_tol_deg differs" in u3.settle_v2_recount(b)["issues"]
    b = settle_axes()
    b["result"]["attitude_ok"] = False                               # recorded bool differs from all axes
    assert "attitude_ok differs" in u3.settle_v2_recount(b)["issues"]
    b = settle_axes(gap_ok_bool=False)                               # per-pad list form still accepted
    assert u3.settle_v2_recount(b)["status"] == "checked"
    b = settle_axes()
    b["inputs"]["residual_deg"] = [0.001]                            # axis count mismatch -> incomplete
    assert u3.settle_v2_recount(b)["status"] == "undecidable"


def g6rec(gates=None, preloc=True, fp="ready", conds=None, events=None, t_ready=None, wrapper=True, revokes=None):
    g = {k: True for k in u3.G6_GATES}
    g.update(gates or {})
    llr = {"conditions": {c: True for c in u3.LATE_LOC_CONDITIONS}, "t_loc_s": 34.0, "t_off_s": 30.0,
           "limit_s": 2.9, "t_reapproach_end_s": None, "crawler_normal_loc_period_max_N": 1000.0,
           "crawler_threshold_N": 3800.0}
    if conds:
        llr["conditions"].update(conds)
    rce = {"events": list(events or []), "t_ready_s": t_ready}
    if wrapper:     # u3 g6 wrapper form (metrics.fix_events carries the wrapper LOC revoke events)
        return {"final_phase": fp, "late_loc_reapproach": llr, "verdict": "pass", "passed": True,
                "metrics": {"crawler_recontact": {"recontact_events": rce}, "l1_revokes": len(revokes or []),
                            "fix_events": [[t, "FIX_LOC_REVOKE:x"] for t in (revokes or [])]},
                "v5": {"r72": {"gates": g, "preloc_flag_ok": preloc, "verdict": None, "pass": True}}}
    return {"final_phase": fp, "late_loc_reapproach": llr, "gates": g, "preloc_flag_ok": preloc, "pass": True,
            "crawler_recontact": {"recontact_events": rce}}


def ev(t0=40.0, dur=0.05, ow=0.012, ol=1.1, sal=0.2, ebl=False):
    return {"t_start_s": t0, "t_end_s": t0 + dur, "duration_s": dur, "max_over_W": ow, "max_over_limit": ol,
            "max_normal_N": 1.0, "start_after_loc_s": sal, "ended_before_loc": ebl, "class": "ignored"}


def test_r4_grade_r72_branches():
    assert u3.grade_r72(g6rec())[0] == "pass"
    assert u3.grade_r72(g6rec(wrapper=False))[0] == "pass"            # study C screen form
    g, _, d = u3.grade_r72(g6rec({"G6-7_preloc": False}, preloc=True))
    assert g == "flag" and d["flags"] == ["P3-8_demoted"]
    g, _, d = u3.grade_r72(g6rec({"G6-7_preloc": False}, preloc=False))
    assert g == "flag" and d["flags"] == ["P3-8_preloc_loss"]
    assert u3.grade_r72(g6rec({"G6-7_preloc": False, "G6-3_Fmin": False}, preloc=False))[0] == "fail"
    assert u3.grade_r72(g6rec({"G6-7_preloc": False}, preloc=False, fp="fault"))[0] == "fail"
    assert u3.grade_r72(g6rec({"G6-7_preloc": False}, preloc=None))[0] is None       # R6-C3 3: undecidable
    g, _, d = u3.grade_r72(g6rec({"G6-2_loc": False}))
    assert g == "flag" and "G6-2_late_loc_reapproach" in d["flags"]
    assert u3.grade_r72(g6rec({"G6-2_loc": False}, conds={"4_load_strict": False}))[0] == "fail"
    # study C form has no revoke record: G6-2 false without the 419.8 FLAG cannot be read (424.8.1 input missing)
    assert u3.grade_r72(g6rec({"G6-2_loc": False}, conds={"1_restart": False}, wrapper=False))[0] is None
    # the recorded verdict / pass are not used
    r = g6rec({"G6-4_att": False})
    r["verdict"], r["v5"]["r72"]["pass"] = "pass", True
    assert u3.grade_r72(r)[0] == "fail"


def test_r4_supplement_2_3_late_loc_revoked():
    # 424.11.2 강등 = 424.8.1 FLAG G6-2_late_loc_revoked, conditions 1~6 (R4 supplement 2-3)
    no419 = {"1_restart": False}
    g, _, d = u3.grade_r72(g6rec({"G6-2_loc": False}, conds=no419, revokes=[32.0]))
    assert g == "flag" and d["flags"] == ["G6-2_late_loc_revoked"]
    assert d["424.8.1_conditions"] == {"why": None, "n_revoke": 1, "c1": True, "c2": True, "c3": True, "c4": True,
                                       "c5": True, "c6": True}
    assert u3.grade_r72(g6rec({"G6-2_loc": False}, conds=no419, revokes=[]))[0] == "fail"         # c1 false
    assert u3.grade_r72(g6rec({"G6-2_loc": False}, conds=no419, revokes=[30.5]))[0] == "fail"     # c2: 3.5 > 2.9
    r = g6rec({"G6-2_loc": False}, conds=no419, revokes=[32.0])
    r["late_loc_reapproach"]["t_loc_s"], r["late_loc_reapproach"]["t_off_s"] = 34.0, 28.0         # c6: 6 > 5.8
    r["metrics"]["fix_events"] = [[33.0, "FIX_LOC_REVOKE:x"]]
    assert u3.grade_r72(r)[0] == "fail"
    r["metrics"]["fix_events"] = [[31.0, "FIX_LOC_REVOKE:x"], [33.0, "FIX_LOC_REVOKE:y"]]          # n 2: 6 <= 8.7
    assert u3.grade_r72(r)[0] == "flag"
    r = g6rec({"G6-2_loc": False}, conds=no419, revokes=[32.0])
    r["late_loc_reapproach"]["crawler_normal_loc_period_max_N"] = 3800.0                           # c3 strict <
    assert u3.grade_r72(r)[0] == "fail"
    r = g6rec({"G6-2_loc": False}, conds={**no419, "5_loc_before_first_done": False}, revokes=[32.0])
    assert u3.grade_r72(r)[0] == "fail"                                                             # c5
    g, _, d = u3.grade_r72(g6rec({"G6-2_loc": False}, revokes=[32.0]))                             # both FLAGs
    assert g == "flag" and d["flags"] == ["G6-2_late_loc_reapproach", "G6-2_late_loc_revoked"]
    r = g6rec({"G6-2_loc": False}, conds=no419)
    r["metrics"].pop("fix_events")
    r["metrics"]["l1_revokes"] = 2                                                                  # count, no times
    assert u3.grade_r72(r)[0] is None


def test_r4_grade_r72_recontact_classes():
    assert u3.classify_recontact(ev(ebl=True, sal=-0.3, dur=0.4, ow=0.1), None) == "transient_flag"
    assert u3.classify_recontact(ev(ebl=True, sal=-0.3, dur=0.6, ow=0.1), None) == "strict_fail"
    assert u3.classify_recontact(ev(sal=0.1, dur=0.07, ol=1.06), None) == "threshold_chatter"
    assert u3.classify_recontact(ev(sal=0.1, dur=0.11, ol=1.06), None) == "strict_fail"     # 423.4 test 2
    assert u3.classify_recontact(ev(sal=0.1, dur=0.07, ol=1.21), None) == "strict_fail"     # 423.4 test 3
    assert u3.classify_recontact(ev(sal=1.05, dur=0.07, ol=1.06), None) == "strict_fail"    # 423.4 test 4
    assert u3.classify_recontact(ev(t0=70.0, sal=0.1, dur=0.07, ol=1.06), 60.0) == "strict_fail"   # after READY
    assert u3.classify_recontact({"t_start_s": 1.0}, None) is None
    g, _, d = u3.grade_r72(g6rec({"G6-1_crawler": False}, events=[ev(sal=0.1, dur=0.07, ol=1.06)]))
    assert g == "flag" and d["flags"] == ["P3-1_threshold_chatter"]
    assert u3.grade_r72(g6rec({"G6-1_crawler": False}, events=[ev(sal=2.0)]))[0] == "fail"
    assert u3.grade_r72(g6rec({"G6-1_crawler": False}, events=[]))[0] == "fail"
    assert u3.grade_r72(g6rec(events=[ev(sal=2.0)]))[0] is None          # gate true but strict recounted


def g6full(i, setting="V0", **kw):
    r = rec(i, suite="g6", setting=setting)
    gr = g6rec(**kw)
    r["v5"]["r72"] = gr["v5"]["r72"]
    r.update({k: v for k, v in gr.items() if k != "v5"})
    return r


def test_r4_g5_g6_lists_and_r72_in_transition(tmp_path):
    v0 = write(tmp_path, "u3_g6_V0.json", [g6full(1), g6full(2)])
    vb = write(tmp_path, "u3_g6_VB.json", [g6full(1, "VB"), g6full(2, "VB", gates={"G6-5_rut_stroke": False})])
    out, f = u3.recount_u3([{"setting": "V0", "path": v0}, {"setting": "VB", "path": vb}], None, IS_P3,
                           repo=None)
    assert out["vb_unique_fail"] == ["g6|H1|J1|B|top|k2"]
    rows = out["G-5_list"]["rows"]
    assert rows == [{"bundle": "H-3", "result_file": Path(vb).as_posix(), "position": "records[1]",
                     "key": "H1|J1|B|top|k2"}]
    assert out["r72_family_grade"]["graded"] == 4
    g8v0 = write(tmp_path, "u3_g8_V0.json", [rec(1, suite="g8"), rec(2, suite="g8")])
    g8vb = write(tmp_path, "u3_g8_VB.json", [rec(1, suite="g8", setting="VB", rod=True, j_p3="pass", fb=0),
                                             rec(2, suite="g8", setting="VB", rod=True, j_p3="pass", fb=2)])
    out, f = u3.recount_u3([{"setting": "V0", "path": g8v0}, {"setting": "VB", "path": g8vb}], None, IS_P3)
    assert [r["position"] for r in out["G-6_list"]["rows"]] == ["records[1]"]
    assert "G-6" in {s["code"] for s in f.stops}


def test_r4_cli_head_check(tmp_path, capsys):
    v0 = write(tmp_path, "u3_slope_V0.json", [rec(1)])
    u3.core.git_head = lambda repo: "4" * 40
    code = u3.main(["--repo", str(HERE.parents[4]), "--out", str(tmp_path / "o.json"), "--u3", f"V0={v0}",
                    "--expect-head", "5" * 40])
    rep = json.loads((tmp_path / "o.json").read_text("utf-8"))
    assert code == 2 and rep["stop_codes"] == ["S-12"] and rep["head_check"]["why"].startswith("HEAD differs")
    code = u3.main(["--repo", str(HERE.parents[4]), "--out", str(tmp_path / "o.json"), "--u3", f"V0={v0}",
                    "--expect-head", "4" * 40])
    rep = json.loads((tmp_path / "o.json").read_text("utf-8"))
    assert rep["head_check"]["ok"] and "rev25" in "".join(rep["r4_rev13_25_sha256"])
    capsys.readouterr()
