"""Self-tests of p2_d1.py: the sealed test values of d1_selection_rules.md 12.1 (#1..#8) + gates, synthetic only."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_d1", HERE / "p2_d1.py")
d1 = importlib.util.module_from_spec(spec)
sys.modules["p2_d1"] = d1
spec.loader.exec_module(d1)
F = d1.F_MIN


def run(group="H-R-0", level="middle", slope="roll+op", setting="VB", eps=0.0, K=1.0, m=0.2, verdict="pass",
        Ffirst=50000.0, stroke=0.0, base="rigid", sink=None, holds=0, att=0.0, F_override=None):
    row = f"D1|{group}|{base}|{level}|{slope}|K{int(K)}|{(sink or {}).get('name')}@{(sink or {}).get('leg')}"
    return {"row": row, "group": group, "level": level, "slope": slope, "base": base, "K": K, "sink": sink,
            "patch_leg": None, "tags": ["ASSUMED_BOUNDARY"] if (group == "H-S-0" and slope == "fup-rec") else [],
            "setting": setting, "eps": eps, "values": {"times": {"t_first_ready_s": None}}, "final_phase": "ready",
            "error": None, "T_lim_p2": 120.0, "missing": [], "raw": {"phases": [["check", 0.0]]},
            "d1": {"verdict": verdict, "F_judged_min_N": F_override if F_override is not None else F * (1 + m),
                   "F_first_level_min_N": Ffirst, "t_ready_s": None, "t_ready_limit_s": 120.0, "att_judged_deg": att,
                   "stroke_max_m": stroke, "dsb75_events": [{"name": "INFO_DIFF_SINK_HOLD"}] * holds, "j_p3": "pass",
                   "fail_items": ["P3-5"] if verdict == "fail" else [], "items": {"P3-5": verdict != "fail"},
                   "harness_class": "stroke_limited_stop" if verdict == "allowed_stop" else None, "demoted_items": [],
                   "key": row, "imu_R_c": 0.0}}


def s1_runs(mp, mm, gp=None, gm=None, fp=None, fm=None):
    out = []
    for slope, ms, gs, ff in (("roll+op", mp, gp, fp), ("roll-op", mm, gm, fm)):
        i = 0
        for K in (1.0, 3.0):
            for e in (0.0, 2e-3):
                out.append(run(slope=slope, K=K, eps=e, m=ms[i], verdict=(gs[i] if gs else "pass"),
                               Ffirst=(ff[i] if ff else 50000.0)))
                i += 1
    return out


def pick_s1(runs):
    by_key = {(r["row"], r["setting"], r["eps"]): r for r in runs}
    cands = [d1.candidate(t.format(lv="middle"), [r for r in runs if r["slope"] == s]) for s, t in d1.S1_SIGNS.items()]
    return d1.select_cell(cands, by_key)[0]


def test_1211_lower_m():
    assert pick_s1(s1_runs([0.120, 0.118, 0.110, 0.111], [0.105, 0.109, 0.1095, 0.108])) == ["D1C2_middle_rollm4.4_Fs4"]


def test_1212_tie_first_level():
    rp = [0.120, 0.118, 0.1100, 0.111]
    rm = [0.1105, 0.112, 0.113, 0.114]
    assert pick_s1(s1_runs(rp, rm, fp=[57100.0] * 4, fm=[55000.0] * 4)) == ["D1C2_middle_rollm4.4_Fs4"]


def test_1213_allowed_stop_first():
    gp = ["allowed_stop", "pass", "pass", "pass"]
    assert pick_s1(s1_runs([0.30] * 4, [0.05] * 4, gp=gp)) == ["D1C2_middle_roll4.4_Fs4"]


def test_1214_fup_rec_excluded_no_g3():
    runs = []
    for slope, m, gv in (("diag-rec", 0.08, "pass"), ("roll-rec", 0.06, "pass"), ("fup-rec", 0.2, "fail")):
        for e in (0.0, 2e-3):
            runs.append(run(group="H-S-0", base="J1", slope=slope, eps=e, m=m, verdict=gv if e == 0.0 else "pass"))
            runs.append(run(group="H-S-0", base="J1", slope=slope, eps=e, m=m, setting="V0", verdict="pass"))
    out, _ = d1.recount(runs, 0)
    s = out["S2"]["S-01"]
    assert s["chosen"] == ["D1S_J1_B_middle_Fs4_rm2p64_p0"] and s["fup_rec_excluded"]
    assert "G-3" not in out["stop_codes"]
    assert out["gates"]["G-3"] and out["gates"]["G-3"][0]["exception_fup_rec"]


def test_1215_1216_rule8():
    bar = {("V0", 1.0): 0.20, ("V0", 3.0): 0.17, ("VB", 1.0): 0.19, ("VB", 3.0): 0.15}
    r = d1.rule8_decide(bar, 0.005)
    assert r["rule"] == 1 and abs(r["offset"] + 0.02) < 1e-12
    bar = {("V0", 1.0): 0.200, ("V0", 3.0): 0.203, ("VB", 1.0): 0.200, ("VB", 3.0): 0.198}
    assert d1.rule8_decide(bar, 0.004)["rule"] == 2


def s3_runs(fast_fl_smax=None):
    out = []
    for leg, prof in d1.S3_PROFILES:
        for e in (0.0, 2e-3):
            holds = 0 if prof == "c-slow" else 1
            smax = 0.55
            if fast_fl_smax is not None and leg == "FL" and prof == "c-fast" and e == 2e-3:
                smax = fast_fl_smax
            out.append(run(group="H-S-C", base="J1", level="top", slope="flat", eps=e, sink={"name": prof, "leg": leg},
                           holds=holds, F_override=12000.0, att=0.06, stroke=smax))
    return out


def test_1217_psc_omitted():
    r = d1.s3(s3_runs())
    assert r["omitted"] and r["rows"] == []


def test_1218_psc_fast():
    r = d1.s3(s3_runs(0.650))
    assert r["rows"] == ["D1PSC_J1_B_top_Fs4_FL_cfast", "D1PSC_J1_B_top_Fs4_spFLJ1_base"]


def test_baseline_failure_adds_second():
    runs = s1_runs([0.10] * 4, [0.30] * 4, gp=["fail", "pass", "pass", "pass"])
    runs += [dict(r, setting="V0", d1=dict(r["d1"])) for r in runs if r["slope"] == "roll+op"]
    for r in runs:
        if r["setting"] == "V0" and r["K"] == 1.0 and r["eps"] == 0.0:
            r["d1"]["verdict"] = "fail"
    by_key = {(r["row"], r["setting"], r["eps"]): r for r in runs}
    vb = [r for r in runs if r["setting"] == "VB"]
    cands = [d1.candidate(t.format(lv="middle"), [r for r in vb if r["slope"] == s]) for s, t in d1.S1_SIGNS.items()]
    chosen, baseline, _ = d1.select_cell(cands, by_key)
    assert baseline and len(chosen) == 2


def test_g3_stop_and_ready_limit():
    runs = [run(group="H-R-A", slope="flat", verdict="fail"), run(group="H-R-A", slope="flat", setting="V0")]
    out, code = d1.recount(runs, 0)
    assert "G-3" in out["stop_codes"] and code == 1
    assert d1.ready_limit_path2({"group": "H-S-0", "roll_deg": 0.0, "pitch_deg": 0.0, "base": "G1", "patch_leg": None}) == 90.0
    assert d1.ready_limit_path2({"group": "H-S-0", "roll_deg": 0.0, "pitch_deg": 0.0, "base": "J2", "patch_leg": None}) == 100.0
    assert d1.ready_limit_path2({"group": "H-S-A", "roll_deg": 0.0, "pitch_deg": 0.0, "base": "G1", "patch_leg": "FL"}) == 90.0
    assert d1.ready_limit_path2({"group": "H-R-0", "roll_deg": 0.0, "pitch_deg": 0.0, "base": "rigid"}) == 90.0
    assert d1.ready_limit_path2({"group": "H-S-0", "roll_deg": 1.925, "pitch_deg": 1.4, "base": "J1"}) == 120.0


def test_crosscheck_conflict():
    r = run(group="H-R-0", slope="flat")
    r["T_lim_p2"] = 90.0
    r["values"] = {"forces": {"after_liftoff": {"min_kN": 9.0}}, "attitude": {"end_abs_deg": {"roll": 0.0, "pitch": 0.01}},
                   "times": {"t_first_ready_s": 40.0}, "pressure": {"max_moving_bar": 100.0},
                   "events": {"fault_events": []}}
    r["d1"]["items"] = {"D8_F_after_liftoff": True}
    x = d1.crosscheck(r)
    assert x["items"]["D8_F_after_liftoff"] is False and x["grade_conflict"]
    assert "D8_F_after_liftoff" in x["item_diffs"]


def test_g2_missing_fields(tmp_path):
    r = run()
    r["missing"] = ["j_p3"]
    out, code = d1.recount([r], 0)
    assert code == 2 and "G-2" in out["stop_codes"]
    json.dumps(out, default=str)


def test_rev3_a1_exception_by_tag():
    r_vb = run(group="H-S-0", slope="fup-rec", verdict="fail", base="J1")
    r_v0 = run(group="H-S-0", slope="fup-rec", setting="V0", base="J1")
    r_vb["tags"] = []                       # tag absent: not the exception, G-3 stop
    out, _ = d1.recount([r_vb, r_v0], 0)
    assert any(s["code"] == "G-3" for s in out["stops"])
    r_vb["tags"] = ["ASSUMED_BOUNDARY"]
    out, _ = d1.recount([r_vb, r_v0], 0)
    assert not any(s["code"] == "G-3" for s in out["stops"]) and out["gates"]["G-3"][0]["exception_fup_rec"]


def test_rev3_a2_reaggregate():
    r = run(group="H-S-0", base="J1", verdict="allowed_stop")
    r["d1"]["fail_items"] = ["P3-5", "SL-1"]
    r["d1"]["items"] = {"P3-5": False, "SL-1": False}
    assert d1.reaggregate(r)["status"] == "same"
    r = run(verdict="pass")
    r["d1"]["items"] = {"P3-8": False}      # false item, no fail_items entry, not in demoted_items
    assert d1.reaggregate(r)["status"].startswith("false items - fail_items")
    r["d1"]["demoted_items"] = [{"item": "P3-8", "rule": "377", "flag": "P3-8_demoted"}]
    assert d1.reaggregate(r)["status"] == "same"
    r["d1"]["demoted_items"] = [{"item": "P3-8", "rule": "999", "flag": "x"}]
    assert d1.reaggregate(r)["status"].startswith("d1.demoted_items entry")
    r["d1"].pop("demoted_items")
    assert d1.reaggregate(r)["status"].startswith("d1.demoted_items missing")
    r = run(verdict="pass")
    r["d1"]["fail_items"] = ["P3-5"]
    assert d1.reaggregate(r)["status"] == "rebuilt verdict differs"


def test_rev3_a3_ready_origin_and_crosscheck():
    r = run()
    r["values"] = {"times": {"t_first_ready_s": 50.0}}
    r["d1"]["t_ready_s"] = 50.0
    assert d1.ready_check(r)["status"] == "ok"
    r["d1"]["t_ready_s"] = 50.1
    assert d1.ready_check(r)["status"].startswith("d1.t_ready_s differs")
    r["d1"]["t_ready_s"] = 50.0
    assert d1.ready_check(r)["origin"] == "정의에 의함"          # R4-C1 2: no F-1 field
    r["values"]["times"]["t_check_start_s"] = 0.3
    assert "> 0.1 s" in d1.ready_check(r)["status"]
    r["values"]["times"]["t_check_start_s"] = 0.1
    assert d1.ready_check(r)["origin"] == "t_check_start_s"

def g6run(flag_ok=True, mins=(12.0,), g63=True, faults=(), fail=None, demoted=None, final_phase="ready"):
    """A g6-path line with the rev7 R7-3a F-8 record (true_min_kN in kN, 0.01 kN)."""
    r = run(group="H-R-A", base="rigid+J1@FR", verdict="fail" if fail else "pass")
    r["values"] = {"times": {"t_first_ready_s": None}, "events": {"fault_events": list(faults)}}
    r["final_phase"] = final_phase
    r["d1"]["items"] = {"G6-7_preloc": False, "G6-3_Fmin": g63}
    r["d1"]["fail_items"] = list(fail or [])
    r["d1"]["demoted_items"] = list(demoted or [])
    r["d1"]["g6_preloc"] = {"preloc_flag_ok": flag_ok, "source": d1.PRELOC_SOURCE,
                            "preloc_starts": [{"leg": "RL", "t_s": 30.0 + i, "true_min_kN": m}
                                              for i, m in enumerate(mins)]}
    return r


DEM = [{"item": "G6-7_preloc", "rule": "377", "flag": "P3-8_demoted"}]
LOSS = [{"item": "G6-7_preloc", "rule": "U-S9-G6c", "flag": "P3-8_preloc_loss"}]


def test_rev6_g67_branches():
    assert d1.reaggregate(g6run(demoted=DEM))["status"] == "same"
    # recount disagrees with the recorded preloc_flag_ok
    assert "recount" in d1.reaggregate(g6run(mins=(9.0,), demoted=DEM))["status"]
    assert d1.reaggregate(g6run(flag_ok=False, mins=(9.0,), demoted=LOSS))["status"] == "same"
    # branch 2 not met (G6-3 false): G6-7 stays a failure
    r = g6run(flag_ok=False, mins=(9.0,), g63=False, fail=["G6-7_preloc", "G6-3_Fmin"])
    assert d1.reaggregate(r)["status"] == "same"
    # a FLAG branch recorded as a failure is a difference
    r = g6run(fail=["G6-7_preloc"])
    assert d1.reaggregate(r)["status"].startswith("G6-7 should be FLAG")
    # branch 3: preloc_flag_ok null (no r72 key) -> undecidable
    r = g6run(flag_ok=None, demoted=DEM)
    ra = d1.reaggregate(r)
    assert ra["status"].startswith("G6-7 branch") and not ra.get("s11")


def test_rev7_r73a_units_rounding_and_flag_definition():
    # kN unit: 9.42 kN >= 9.414589 kN; the recorded 0.01 kN value 9.41 is below F_min (rounded value compared)
    assert d1.preloc_flag_recount(g6run(mins=(9.42,))["d1"]["g6_preloc"], "ready") is True
    assert d1.preloc_flag_recount(g6run(mins=(9.41,))["d1"]["g6_preloc"], "ready") is False
    # empty start list -> false; a null minimum -> false; final phase fault / fault_reground -> false
    gp = g6run(mins=())["d1"]["g6_preloc"]
    assert gp["preloc_starts"] == [] and d1.preloc_flag_recount(gp, "ready") is False
    assert d1.preloc_flag_recount(g6run(mins=(12.0, None))["d1"]["g6_preloc"], "ready") is False
    for ph in ("fault", "fault_reground"):
        assert d1.preloc_flag_recount(g6run()["d1"]["g6_preloc"], ph) is False
    assert d1.preloc_flag_recount(g6run()["d1"]["g6_preloc"], None) is None
    # a fault final phase with a recorded true flag is a recount difference
    assert "recount" in d1.reaggregate(g6run(demoted=DEM, final_phase="fault_reground"))["status"]
    # empty starts recorded false + G6-3 true + no FAULT event -> U-S9-G6c branch
    assert d1.reaggregate(g6run(flag_ok=False, mins=(), demoted=LOSS))["status"] == "same"
    # 9.41 kN recorded false (rounded below F_min) -> branch 2
    assert d1.reaggregate(g6run(flag_ok=False, mins=(9.41,), demoted=LOSS))["status"] == "same"


def test_rev7_r73a_old_names_and_format_are_s11():
    r = g6run(demoted=DEM)
    r["d1"]["g6_preloc"]["preloc_starts"] = [{"leg": "RL", "t_s": 30.0, "true_min_N": 12000.0}]
    ra = d1.reaggregate(r)
    assert ra.get("s11") and "rev7 R7-3a" in ra["status"]
    for mutate in (lambda g: g.update(source="other"),
                   lambda g: g["preloc_starts"][0].update(true_min_kN=12.003),     # not 0.01 kN
                   lambda g: g["preloc_starts"][0].update(t_s=30.004),             # not 0.01 s
                   lambda g: g["preloc_starts"][0].update(leg="F1"),
                   lambda g: g.pop("preloc_flag_ok"),
                   lambda g: g.update(preloc_flag_ok="yes"),
                   lambda g: g.update(preloc_starts=list(reversed(g["preloc_starts"])))):   # event order
        r = g6run(mins=(12.0, 13.0), demoted=DEM)
        mutate(r["d1"]["g6_preloc"])
        assert d1.preloc_record_problems(r["d1"]["g6_preloc"]), mutate
    # recount over a set of runs: S-11 stop, exit 2, also on a line whose G6-7 is true
    ok = g6run(demoted=DEM)
    bad = g6run()
    bad["d1"]["items"]["G6-7_preloc"] = True
    bad["d1"]["g6_preloc"]["preloc_starts"][0]["true_min_kN"] = 12000.0 + 0.004
    out, code = d1.recount([ok, bad], 0)
    assert code == 2 and "S-11" in out["stop_codes"] and out["R7-3a_g6_preloc_format"] == {"checked": 2, "differ": 1}
