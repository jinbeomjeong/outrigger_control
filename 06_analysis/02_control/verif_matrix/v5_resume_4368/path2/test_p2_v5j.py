"""Self-tests of p2_v5j.py (v5 J items, H-5 U-9) on synthetic lines only."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_v5j", HERE / "p2_v5j.py")
vj = importlib.util.module_from_spec(spec)
sys.modules["p2_v5j"] = vj
spec.loader.exec_module(vj)
core = vj.core
IS_P3 = lambda t: t is not None and "_P3" in t   # noqa: E731 - stand-in for v5_options in unit tests


def steady(case="S2", eps=0.0, setting="V0", eta=None, cls="pass", minf=50.0, ready=80.0, att=0.05,
           press=120.0, nrev=14, fp="ready", events=(), post=(0, 0, 0, 0), nlf=0, ebc=None, u9=None, e5=None,
           att_after=0.4):
    job = {"case": case, "eps": eps, "setting": setting, "u9_metrics": True}
    if eta is not None:
        job["eta_v"] = eta
    ln = {"job": job, "commands_sha256": f"{hash((case, eps, setting, eta)) & (2**64 - 1):064x}",
          "final_phase": fp, "t_event_s": None, "event_output": {}, "harness_class": cls,
          "events": [list(e) for e in events], "command_stats": {"n_rev": nrev}, "head_only_declared": True,
          "controller_tag": core.TAG_V0 if setting == "V0" else core.TAG_VB,
          "values": {"times": {"t_first_ready_s": ready}, "forces": {"after_liftoff": {"min_kN": minf}},
                     "attitude": {"max_abs_last_5s_deg": att, "max_abs_after_liftoff_deg": att_after},
                     "pressure": {"max_moving_bar": press}, "events": {"fault_events": [], "warn_events": []},
                     "U9": u9 if u9 is not None else {},
                     "E5": e5 if e5 is not None else {"integral_limit_rad_s": 0.02, "max_abs_integral_rad_s": 0.01,
                                                      "back_in_band_after_saturation_s": 14.0}}}
    if setting != "V0":
        ln["hydraulic_options"] = {"m2_law": "flow_limited_r5", "lock_closure": {}}
        ln["hydraulics_record"] = {"m2_clipped_steps_post_lift": list(post), "m2_clipped_steps_pre_lift": [25] * 4,
                                   "extend_bound_check": ebc}
        ln["lock_window_alignment"] = {"n_late_fallback": nlf, "n_late_by_leg": {}}
    return ln


def u9_block(longest=0.2, delta=0.02, fs=0.06, fe=0.06):
    run = {"max_abs_delta_deg": {"roll": delta, "pitch": delta}, "filtered_start_deg": {"roll": fs, "pitch": fs},
           "filtered_end_deg": {"roll": fe, "pitch": fe}}
    return {"level_count_s": {"1": 1.0}, "longest_ge3_s": longest, "longest_eq4_s": 0.0, "ge3_runs": [run]}


def full_set(over=None):
    v0, vb = [], []
    for case, eps in sorted(vj.U9_KEYS):
        v0.append(steady(case, eps, "V0"))
        vb.append(steady(case, eps, "VB", 0.85, u9=u9_block()))
        kw = dict((over or {}).get((case, eps), {}))
        vb.append(steady(case, eps, "VB", 0.80, u9=kw.pop("u9", u9_block()), **kw))
    ref = [steady(c, e, "VB") for c, e in sorted(vj.U9_H0)]
    for r in ref:   # main VB line (no u9 keys), same commands as the eta 0.85 line of the same key
        r["job"].pop("u9_metrics")
        r["commands_sha256"] = next(x for x in vb if vj.u9_key(x["job"]) == vj.u9_key(r["job"])
                                    and x["job"].get("eta_v") == 0.85)["commands_sha256"]
    return v0, vb, ref


def test_j_items_pass_and_fail():
    a, b = steady(setting="V0"), steady(setting="VB", eta=0.80)
    it, f = vj.judge_pair(b, a, 14, IS_P3)
    assert f.status() == "pass", f.as_dict()
    assert it["J-P3"]["result"] == "no_rod_reading"
    b2 = steady(setting="VB", eta=0.80, minf=9.0, ready=101.0, att=0.25, press=181.0, fp="level",
                events=[(50.0, "WARN_ROD_PRESSURE_FALLBACK:FR")], nrev=40)
    it, f = vj.judge_pair(b2, a, 14, IS_P3)
    for j in ("J2", "J3", "J4", "J6", "J7", "J8", "J10"):
        assert it[j]["result"] == "fail", (j, it[j])
    assert f.status() == "fail"


def test_threshold_tolerance_and_baseline_fail():
    a, b = steady(setting="V0", minf=9.0), steady(setting="VB", eta=0.80, minf=8.0)
    it, _ = vj.judge_pair(b, a, 14, IS_P3)
    assert it["J2"]["result"] == "baseline_fail"          # V0 also below F_min: not a J2 fail
    b = steady(setting="VB", eta=0.80, minf=core.F_MIN_N / 1000 - 0.5e-9)
    it, _ = vj.judge_pair(b, steady(setting="V0"), 14, IS_P3)
    assert it["J2"]["result"] == "pass"                   # 7.6 tolerance 1e-9


def test_j8_limit_cycle_needs_both_conditions():
    a = steady(setting="V0")
    _, f = vj.judge_pair(steady(setting="VB", nrev=26), a, 14, IS_P3)    # 2x not reached
    assert f.status() == "pass"
    _, f = vj.judge_pair(steady(setting="VB", nrev=10), a, 4, IS_P3)     # 2x reached, +6 reached
    assert f.status() == "fail"


def test_stops_j9_j11_jp3():
    a = steady(setting="V0")
    _, f = vj.judge_pair(steady(setting="VB", post=(0, 1, 0, 0)), a, 14, IS_P3)
    assert "H-9" in f.as_dict()["stop_codes"]
    _, f = vj.judge_pair(steady(setting="VB", nlf=1), a, 14, IS_P3)
    assert "H-7" in f.as_dict()["stop_codes"]
    ln = steady(setting="VB", ebc={"breach_reads": [0, 2, 0, 0]})
    ln["head_only_declared"] = False
    _, f = vj.judge_pair(ln, a, 14, IS_P3, rod_reading=True)   # T4h shows a rod reading
    assert "H-7" in f.as_dict()["stop_codes"]
    ln = steady(setting="VB", ebc={"breach_reads": [0, 0, 0, 0]})
    ln["head_only_declared"] = False                            # steady, no T4h: no rod reading by config, #4
    _, f = vj.judge_pair(ln, a, 14, IS_P3)
    assert "J-P3-defect" in f.as_dict()["stop_codes"]
    ln = steady(setting="VB", ebc={"breach_reads": [0, 0, 0, 0]})      # declared head-only but a record: #5
    _, f = vj.judge_pair(ln, a, 14, IS_P3)
    assert "J-P3-defect" in f.as_dict()["stop_codes"]


def test_j11_reason_record_is_not_undecidable():
    b = steady(setting="VB")
    b["lock_window_alignment"] = {"n_late": None, "reason": "no rod reading"}
    it, f = vj.judge_pair(b, steady(setting="V0"), 14, IS_P3)
    assert it["J11"]["result"] == "not_computed" and f.status() == "pass"


def test_names_strip_numeric_suffix():
    ln = steady(events=[(1.0, "WARN_PROBE_STIFFNESS_OUT_OF_RANGE:3.6"), (2.0, "INFO_ROD_PRESSURE_FAULT_REASON:FR:D1")])
    n, r, _ = vj.names_of(ln)
    assert n == {"WARN_PROBE_STIFFNESS_OUT_OF_RANGE"} and r == {"INFO_ROD_PRESSURE_FAULT_REASON:FR:D1"}


def test_u9_class_b_and_a():
    v0, vb, ref = full_set()
    body, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert f.status() == "pass", f.as_dict()
    assert body["classification"] == "B"
    v0, vb, ref = full_set({("S5", 0.0): {"u9": u9_block(longest=0.6)}})
    body, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["classification"] == "A"


def test_u9_class_c_t3a_t4_and_cause_fail():
    v0, vb, ref = full_set({("S2", 0.001): {"u9": u9_block(delta=0.11)}})
    body, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["classification"] == "C" and f.status() == "pass" and body["ask_user_before_v5_sentence"]
    v0, vb, ref = full_set({("S2", 0.001): {"e5": {"integral_limit_rad_s": 0.02, "max_abs_integral_rad_s": 0.02,
                                                     "back_in_band_after_saturation_s": None}}})
    body, _ = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["classification"] == "C" and body["class_flags"]["T4"] and body["class_flags"]["T4_flag_integral"]
    v0, vb, ref = full_set({("R3", 0.002): {"minf": 5.0}})
    body, _ = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["classification"] == "C" and body["class_flags"]["cause_fail"] == ["R3|eps 0.002"]


def test_u9_t3c_only_and_d_record():
    v0, vb, ref = full_set({("S3", 0.0): {"att_after": 0.6}})
    body, _ = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["classification"].startswith("C (T3c only")
    v0, vb, ref = full_set()
    for x in vb:   # baseline 0.85 also fails J2 on one key -> D (recorded), not a cause fail
        if vj.u9_key(x["job"]) == ("S2", 0.0):
            x["values"]["forces"]["after_liftoff"]["min_kN"] = 5.0
    body, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert body["class_flags"]["baseline_or_v0_fail"] == ["S2|eps 0.0"] and body["classification"] == "B"
    assert f.status() == "fail"          # R3-C2: eta 0.85 T1 failure = 미달


def test_u9_h0_stop_tag_stop_and_counts():
    v0, vb, ref = full_set()
    ref[0]["commands_sha256"] = "0" * 64
    _, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert "U9-H0" in f.as_dict()["stop_codes"]
    v0, vb, ref = full_set()
    v0[0]["controller_tag"] = "final_C4G2"
    _, f = vj.recount_u9(v0, vb, ref, IS_P3)
    assert "S-2" in f.as_dict()["stop_codes"]
    v0, vb, ref = full_set()
    _, f = vj.recount_u9(v0[1:], vb, ref, IS_P3)
    assert "S-15" in f.as_dict()["stop_codes"]


def test_u9_missing_value_is_undecidable():
    v0, vb, ref = full_set()
    bad = copy.deepcopy(vb)
    for x in bad:
        if x["job"].get("eta_v") == 0.80:
            x["values"]["U9"].pop("ge3_runs")
            break
    body, f = vj.recount_u9(v0, bad, ref, IS_P3)
    assert f.status() == "pass" and body["classification"] == "undecidable"   # eta 0.80 = record (R3-C2)
    bad = copy.deepcopy(vb)
    for x in bad:
        if x["job"].get("eta_v") == 0.85:
            x["values"]["attitude"].pop("max_abs_last_5s_deg")
            break
    _, f = vj.recount_u9(v0, bad, ref, IS_P3)
    assert f.status() == "undecidable"


def test_rules_sha_real():
    repo = HERE.parents[4]
    for rel, want in vj.U9_RULES.items():
        assert core.sha256_file(repo / rel) == want


def test_rev3_j1_safe_stop_move_and_s8():
    a, b = steady(setting="V0"), steady(setting="VB", cls="stroke_limited_stop")
    it, f = vj.judge_pair(b, a, 14, IS_P3)
    assert it["J1"]["result"] == "pass" and it["J1"]["safe_stop_move"] and f.status() == "pass"
    a, b = steady("S8", setting="V0", cls="stroke_limited_stop", ready=None), steady("S8", setting="VB", ready=None)
    it, f = vj.judge_pair(b, a, 14, IS_P3)
    assert it["J1"]["result"] == "fail"


def test_rev3_j7_numeric_segments_and_j11_fallback():
    ln = steady(events=[(1.0, "FAULT_LIFT_STROKE_LIMIT:soil:FR"), (2.0, "WARN_X:3.5:FL")])
    n, _, _ = vj.names_of(ln)
    assert n == {"FAULT_LIFT_STROKE_LIMIT:soil:FR", "WARN_X:FL"}
    b = steady(setting="VB", events=[(50.0, "WARN_ROD_PRESSURE_FALLBACK:FR")])
    b["lock_window_alignment"] = {"n_late": None, "reason": "x"}
    it, f = vj.judge_pair(b, steady(setting="V0", events=[(50.0, "WARN_ROD_PRESSURE_FALLBACK:FR")]), 14, IS_P3)
    assert it["J11"]["result"] == "undecidable" and f.status() == "undecidable"


def test_rev3_j3_floor_angle_and_jp3_config():
    b = steady("R5", setting="VB", ready=100.0)
    it, _ = vj.judge_pair(b, steady("R5", setting="V0"), 14, IS_P3)
    assert it["J3"]["result"] == "record" and "case_floor_deg" in it["J3"]["why"]
    b["values"]["case_floor_deg"] = [0.0, 3.5]
    it, _ = vj.judge_pair(b, steady("R5", setting="V0"), 14, IS_P3)
    assert it["J3"]["limit_s"] == 120.0 and it["J3"]["result"] == "record"
    b["values"]["case_floor_deg"] = [0.0, 0.0]
    it, _ = vj.judge_pair(b, steady("R5", setting="V0"), 14, IS_P3)
    assert it["J3"]["result"] == "flag"
    ln = steady("X9", setting="VB")
    ln.pop("head_only_declared")
    it, f = vj.judge_pair(ln, steady("X9", setting="V0"), 14, IS_P3)
    assert it["J-P3"]["result"] == "undecidable"
    ln = steady("S2", setting="VB")
    ln.pop("head_only_declared")
    it, _ = vj.judge_pair(ln, steady("S2", setting="V0"), 14, IS_P3)
    assert it["J-P3"]["result"] == "no_rod_reading" and it["J-P3"]["declaration_source"] == "configuration"

def test_rev5_ls_j11_is_l_e():
    b = steady(setting="LS1", nlf=1)
    b["controller_tag"] = core.TAG_VB
    _, f = vj.judge_pair(b, steady(setting="V0"), 14, IS_P3)
    assert "L-e" in f.as_dict()["stop_codes"] and "H-7" not in f.as_dict()["stop_codes"]
