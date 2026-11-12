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
            "patch_leg": None, "tags": [], "setting": setting, "eps": eps, "values": {}, "final_phase": "ready",
            "error": None, "T_lim_p2": 120.0, "missing": [],
            "d1": {"verdict": verdict, "F_judged_min_N": F_override if F_override is not None else F * (1 + m),
                   "F_first_level_min_N": Ffirst, "t_ready_s": None, "t_ready_limit_s": 120.0, "att_judged_deg": att,
                   "stroke_max_m": stroke, "dsb75_events": [{"name": "INFO_DIFF_SINK_HOLD"}] * holds, "j_p3": "pass",
                   "fail_items": [], "key": row, "imu_R_c": 0.0}}


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
