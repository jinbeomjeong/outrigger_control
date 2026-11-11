"""Unit tests for the path-2 recount tools (synthetic fixtures only; rules 10.2 / 11.3 item 4).

Run: conda run -n dynamics-dev python -I -m pytest -q <this file>
The modules are loaded by file path (python -I does not put the script folder on sys.path).
"""
import copy
import hashlib
import importlib.util
import json
import os

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = _load("p5k_recount")
C = _load("p5k_chrono_recount")


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_rules(tmp):
    paths = []
    for nm in ("rules.md", "rules_rev1.md", "rules_rev2.md"):
        p = os.path.join(tmp, nm)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# synthetic {nm}\n")
        s = H.sha256_file(p)
        with open(os.path.splitext(p)[0] + ".sha256", "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{s}  {nm}\n")
        paths.append((p, s))
    return paths


# ============================================================================ harness

D1_ITEMS = {"G6-1_crawler": True, "P3-1_crawler": True, "P3-5_clearance": True, "READY": True}


def hline(key, arm, h, start=None, items=None, verdict="pass", stroke=0.600, F=12000.0, t_ready=50.0,
          final="ready", events=None, decisions=None, anchor=None, setting=None, drop=()):
    setting = setting or key.split("|")[-2]
    ln = dict(
        commands_sha256=h, final_phase=final, las_candidate=H.ARM_LABEL[arm],
        controller_tag=H.TAG_VB if setting == "VB" else H.TAG_V0,
        event_names=dict(events if events is not None else {"crawler_liftoff_confirmed": 1}),
        values=dict(times=dict(t_first_ready_s=t_ready), events=dict(t_loc_first_s=30.0, t_loc_last_s=30.0)),
        las=dict(start_t_s=start, end_t_s=None if start is None else start + 1.0, end_reason=None,
                 candidate=H.ARM_LABEL[arm],
                 settings=dict(H.B0_SETTINGS if arm == "ref" else H.P5R4_SETTINGS),
                 ramp=dict(start_factor=None, periods_applied=0, end_reason=None, end_t_s=None)),
        k1=dict(enabled=True, decisions=copy.deepcopy(decisions) if decisions is not None else []),
        d1=dict(key=key, items=dict(items if items is not None else D1_ITEMS), verdict=verdict, fail_items=[],
                F_judged_min_N=F, stroke_max_m=stroke, t_ready_s=t_ready),
        job=dict(d1={}, setting=setting, eps=0.0),
        rev=dict(key=key, attempt=1, identity=dict(git_head="abc", code_diff_sha256=H.EMPTY_SHA),
                 rules_sha256=H.RULES_SHA, rules_rev1_sha256=H.RULES_REV1_SHA),
    )
    if anchor is not None:
        ln["anchor"] = anchor
    for p in drop:
        cur = ln
        parts = p.split(".")
        for q in parts[:-1]:
            cur = cur[q]
        del cur[parts[-1]]
    return ln


def write_jsonl(path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for ln in lines:
            f.write(json.dumps(ln) + "\n")


@pytest.fixture()
def hworld(tmp_path, monkeypatch):
    """Patch baseline/rules constants to a synthetic world; returns a runner for bundle Z-C."""
    tmp = str(tmp_path)
    (r_path, r_sha), (r1_path, r1_sha), (r2_path, r2_sha) = write_rules(tmp)
    monkeypatch.setattr(H, "RULES_SHA", r_sha)
    monkeypatch.setattr(H, "RULES_REV1_SHA", r1_sha)
    monkeypatch.setattr(H, "RULES_REV2_SHA", r2_sha)
    v5 = os.path.join(tmp, "v5")

    def run(pairs_spec, zc_ref_hash=None):
        """pairs_spec: {key: (ref_line, cand_line)}; baseline s2d_SC holds the ref hashes."""
        base = {}
        for name, (rel, _w) in H.BASE_FILES.items():
            p = os.path.join(v5, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            lines = []
            if name == "s2d_SC":
                for k, (r, _c) in pairs_spec.items():
                    lines.append(dict(rev=dict(key=k), commands_sha256=(zc_ref_hash or {}).get(k, r["commands_sha256"])))
            write_jsonl(p, lines)
            base[name] = (rel, H.sha256_file(p))
        monkeypatch.setattr(H, "BASE_FILES", base)
        keys = sorted(pairs_spec)
        ls = dict(H.LIST_SHA)
        empty = H.list_sha([])
        for b in ("Z-0", "Z-A", "Z-T", "Z-S", "Y-Pa"):
            ls[b] = empty
        ls["Z-C"] = H.list_sha(keys)
        ls["Z-C-out"] = H.list_sha(keys)
        monkeypatch.setattr(H, "LIST_SHA", ls)
        run_lines = []
        for k, (r, c) in pairs_spec.items():
            for ln in (r, c):
                ln = copy.deepcopy(ln)
                ln["rev"]["rules_sha256"] = r_sha
                ln["rev"]["rules_rev1_sha256"] = r1_sha
                run_lines.append(ln)
        zc = os.path.join(tmp, "p5k_Z-C.jsonl")
        write_jsonl(zc, run_lines)
        return H.recount(None, v5, r_path, r1_path, r2_path, explicit={"Z-C": zc})
    return run


K1 = "D1|H-S-0|J1|T|flat|K1|VB|e0"
K2 = "D1|H-S-0|J2|T|flat|K1|VB|e0"


def test_combine_priority_three_cases():
    assert H.combine(["pass", "fail"]) == "fail"                     # fail only
    assert H.combine(["pass", "undecidable"]) == "undecidable"       # undecidable only
    assert H.combine(["fail", "undecidable", "pass"]) == "undecidable"  # both -> undecidable wins
    assert H.combine(["fail", "stop", "undecidable"]) == "stop"
    assert H.combine(["incomplete", "fail"]) == "undecidable"
    assert H.combine(["not_run", "pass", None]) == "pass"
    assert C.combine(["fail", "undecidable"]) == "undecidable"


def test_harness_all_equal_passes(hworld):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1")),
                  K2: (hline(K2, "ref", "h2"), hline(K2, "cand", "h2"))})
    bz = out["bundles"]["Z-C"]
    assert bz["status"] == "pass", (bz["stop_reasons"], bz["undecidable_reasons"], bz["fail_reasons"])
    assert bz["criteria"]["R-1/R-2"]["note"].startswith("hash identical")
    assert bz["bit_prediction"]["n_equal"] == 2


def test_harness_bit_prediction_mismatch_stops(hworld):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1"))}, zc_ref_hash={K1: "other"})
    assert out["bundles"]["Z-C"]["status"] == "stop"


def test_pair_diverge_premise_true_stops(hworld):
    # cand LAS-b did not start but the command hash differs -> PAIR_DIVERGE -> stop
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=None))})
    bz = out["bundles"]["Z-C"]
    assert bz["criteria"]["PAIR_DIVERGE"]["keys"] == [K1]
    assert bz["status"] == "stop"


def test_pair_cmd_diff_premise_false_records_only(hworld):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=40.0, t_ready=50.5))})
    bz = out["bundles"]["Z-C"]
    assert bz["criteria"]["PAIR_DIVERGE"]["n"] == 0
    assert bz["criteria"]["PAIR_CMD_DIFF"]["keys"] == [K1]
    assert bz["status"] == "pass", bz["fail_reasons"]


def test_ck1_r4_lost_and_gained():
    dec_app = [dict(t_loc_s=30.0, t_P_s=29.0, t_S_s=25.0, r4_due_without_gate=True, applied=True, would_block=False, dP=40)]
    dec_blk = [dict(t_loc_s=30.0, t_P_s=25.0, t_S_s=25.0, r4_due_without_gate=True, applied=False, would_block=True, dP=0)]
    p = H.eval_pair(hline(K1, "ref", "a", decisions=dec_app), hline(K1, "cand", "b", start=1.0, decisions=dec_blk), "Z-C")
    assert p["ck1"]["cls"] == "R4_LOST" and p["ck1"]["violation"] is True
    p = H.eval_pair(hline(K1, "ref", "a", decisions=dec_blk), hline(K1, "cand", "b", start=1.0, decisions=dec_app), "Z-C")
    assert p["ck1"]["cls"] == "R4_GAINED" and p["ck1"]["violation"] is False


def test_missing_field_makes_criterion_undecidable(hworld):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1", drop=("d1.items",)))})
    bz = out["bundles"]["Z-C"]
    assert bz["criteria"]["C-2"]["status"] == "undecidable"
    assert bz["status"] == "undecidable"


def test_fail_and_undecidable_together_is_undecidable(hworld):
    out = hworld({
        K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=1.0, stroke=0.6015, t_ready=50.2)),  # C-S fail
        K2: (hline(K2, "ref", "h2"), hline(K2, "cand", "h2", drop=("k1.decisions",))),  # CK-1 undecidable
    })
    bz = out["bundles"]["Z-C"]
    assert bz["criteria"]["C-S"]["status"] == "fail"
    assert bz["criteria"]["CK-1"]["status"] == "undecidable"
    assert bz["status"] == "undecidable"


def test_fail_only(hworld):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=1.0, stroke=0.6015, t_ready=50.2))})
    assert out["bundles"]["Z-C"]["status"] == "fail"


def test_ready_population_empty_two_cases(hworld):
    # hash changed but cand READY None -> C-2 (b) violation and population empty -> R undecidable
    out = hworld({K1: (hline(K1, "ref", "h1", t_ready=None, final="fault"),
                       hline(K1, "cand", "h1x", start=1.0, t_ready=None, final="fault"))})
    r = out["bundles"]["Z-C"]["criteria"]["R-1/R-2"]
    assert r["status"] == "undecidable" and r["n_changed"] == 1 and r["n_population"] == 0
    # no changed pair -> holds by hash identity
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1"))})
    r = out["bundles"]["Z-C"]["criteria"]["R-1/R-2"]
    assert r["status"] == "pass" and r["n_changed"] == 0


def test_event_names_exact_match():
    ref = hline(K1, "ref", "a", events={"WARN_LIFT_STROKE_LIMITED": 1})
    cand = hline(K1, "cand", "b", start=1.0, events={"WARN_LIFT_STROKE_LIMITED_SKIPPED:x": 1})
    p = H.eval_pair(ref, cand, "Z-C")
    assert any(v.startswith("c:new_events:WARN_LIFT_STROKE_LIMITED_SKIPPED") for v in p["c2_violations"])
    cand = hline(K1, "cand", "b", start=1.0, events={"WARN_LIFT_STROKE_LIMITED:arg": 2})
    assert not any(v.startswith("c:") for v in H.eval_pair(ref, cand, "Z-C")["c2_violations"])


def test_items_union_rules():
    ref = hline(K1, "ref", "a", items={"X": True, "Y": False})
    cand = hline(K1, "cand", "b", start=1.0, items={"Y": False, "Z": False, "P3-1_crawler": False})
    p = H.eval_pair(ref, cand, "Z-C")
    assert "a:item:X:True->None" in p["c2_violations"]
    assert "a:item:Z:None->False" in p["c2_violations"]
    assert p["items_only_ref"] == ["X"] and sorted(p["items_only_cand"]) == ["P3-1_crawler", "Z"]
    assert p["p3_violations"] == ["P3-1_crawler:None->False"]
    ref = hline(K1, "ref", "a", items={"P3-5_clear": False})
    p = H.eval_pair(ref, hline(K1, "cand", "a", items={"P3-5_clear": False}), "Z-C")
    assert p["p3_violations"] == [] and p["p3_baseline_false"] == ["P3-5_clear"]


def test_r13_judge_drift_undecidable():
    p = H.eval_pair(hline(K1, "ref", "same", items={"A": True}), hline(K1, "cand", "same", items={"A": False}), "Z-C")
    assert "C-2" in p["undecidable_reasons"]


def test_anchor_flag_and_effect(hworld):
    def anc(tp):
        return dict(soil_meta=dict(t_P_s=tp, t_loc_s=31.0, bias_corner_raw_m=[0.01, 0, 0, 0], bias_corner_m=[0.01, 0, 0, 0],
                                   loc_anchor_applied=False, corner_order=["a", "b", "c", "d"]),
                    loc_calls=[dict(t_loc_s=31.0, t_P_s=tp)])
    ev1 = {"crawler_liftoff_confirmed": 1, "INFO_CLEARANCE_BIAS:FL=1": 1}
    out = hworld({K1: (hline(K1, "ref", "h1", events=ev1, anchor=anc(30.0)),
                       hline(K1, "cand", "h1x", start=1.0, events=ev1, anchor=anc(30.1), stroke=0.6015, t_ready=50.1))})
    bz = out["bundles"]["Z-C"]
    p = bz["pairs"][K1]
    assert p["anchor"]["flag"] is True and p["anchor"]["d_n_P_first"] == 1
    assert p["anchor"]["ref"]["path"] == "1" and p["anchor"]["ref"]["anchor_meta_agree"] is True
    assert bz["criteria"]["flags"]["anchor_effect_possible"] == [K1]
    assert bz["status"] == "fail"   # rev1 RV1-3: the grade is not changed by the FLAG


def test_anchor_flag_path3_and_missing():
    a = dict(path="3", n_P_first=1, n_P_last=1)
    assert H.anchor_shift(a, dict(a))[0] is False
    b = dict(path="2", n_P_first=None, n_P_last=None)
    assert H.anchor_shift(b, dict(path="3", n_P_first=5, n_P_last=5))[0] is None
    assert H.anchor_shift(dict(path=None), dict(path=None))[0] is None


def test_error_lines_counted_separately(hworld, tmp_path):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1"))})
    assert out["error_lines_total"] == 0
    groups, errs, _s = H.group_lines([dict(error="boom", rev=dict(key=K1), __lineno__=3), hline(K1, "ref", "a")],
                                     ("ref", "cand"), H.line_key)
    assert len(errs) == 1 and errs[0]["lineno"] == 3 and ("ref", K1) in groups


def test_c4_exception():
    cand = hline(K1, "cand", "x", start=10.0)
    cand["las"]["end_t_s"] = 11.0
    cand["done_clock"] = dict(loss_s=3.0, clock_starts_s=[20.0, 23.0], resets=[dict(t_s=22.0, names=["twist_ok"])])
    ref = hline(K1, "ref", "r")
    zx = copy.deepcopy(ref)
    zx["done_clock"] = dict(loss_s=0.0, clock_starts_s=[20.0], resets=[])
    assert H.c4_exception(cand, zx, ref, 3.0)["exception"] is True
    assert H.c4_exception(cand, zx, ref, 4.0)["exception"] is False          # E < 0.8 dt
    assert H.c4_exception(cand, None, ref, 3.0)["exception"] is False        # no Z-X -> stays in population
    zx2 = copy.deepcopy(zx)
    zx2["commands_sha256"] = "other"
    assert H.c4_exception(cand, zx2, ref, 3.0)["exception"] is False


def test_gate_effective_value_from_line_meta(hworld):
    c = hline(K1, "cand", "h1")
    c["k1"]["enabled"] = False                      # executed controller meta says gate off -> K-4 -> stop
    out = hworld({K1: (hline(K1, "ref", "h1"), c)})
    assert out["bundles"]["Z-C"]["status"] == "stop"
    assert any(s.startswith("K-4:k1.enabled_true") for s in out["bundles"]["Z-C"]["stop_reasons"])


def test_wrong_las_settings_stop(hworld):
    c = hline(K1, "cand", "h1")
    c["las"]["settings"]["end_ramp_periods"] = 0     # cand without the ramp (K-5 / K-A8)
    out = hworld({K1: (hline(K1, "ref", "h1"), c)})
    assert out["bundles"]["Z-C"]["status"] == "stop"


def test_duplicate_line_stop(hworld, monkeypatch):
    orig = H.group_lines

    def dup(lines, arms, keyfun):
        g, e, s = orig(lines, arms, keyfun)
        for k in list(g):
            g[k] = g[k] * 2
        return g, e, s
    monkeypatch.setattr(H, "group_lines", dup)
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1"))})
    assert out["bundles"]["Z-C"]["status"] == "stop"


def test_ka5_ka6():
    ln = hline("D1|H-R-A|x|T|diag-op|K3|VB|e0.002", "cand", "n")
    ln["rev"]["label"] = "P5r4-LQ-c1-j0p25"
    ln["las"].update(end_reason="sum", ramp=dict(start_factor=0.4, periods_applied=4, end_reason="done", end_t_s=3.0))
    ln["diag"] = dict(summary=dict(F_RL_kN=12.5, F_judged_min_kN=12.6, gate_consistent=True),
                      touch_budget=dict(level_budget_periods=0, centre="1", j=0.25))
    key = (ln["rev"]["key"], ln["rev"]["label"])
    res = H.za_criteria({key: ln}, {}, {})
    assert res["KA"]["K-A5"]["ok"] and res["G2p"]["ok"] and res["G3"]["LQ"]["ok"]
    ln["las"]["ramp"]["periods_applied"] = 3            # done but fewer than N_r periods -> K-A5 false
    assert H.za_criteria({key: ln}, {}, {})["KA"]["K-A5"]["ok"] is False
    ln["las"].update(end_reason="loc", ramp=dict(start_factor=None, periods_applied=1))
    assert H.za_criteria({key: ln}, {}, {})["KA"]["K-A6"]["ok"] is False
    ln["las"]["ramp"]["periods_applied"] = 0
    ln["diag"]["summary"]["F_RL_kN"] = 11.40              # below G-2' 11.414589
    r = H.za_criteria({key: ln}, {}, {})
    assert r["G2p"]["ok"] is False and r["G1"]["LQ"]["ok"] is True


def test_rev2_cs_cf_none_rules(hworld):
    # RV2-2: cand None -> violation (fail, not undecidable); ref None -> out of scope (ref_none)
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=1.0, stroke=None, t_ready=50.1))})
    cs = out["bundles"]["Z-C"]["criteria"]["C-S"]
    assert cs["status"] == "fail" and K1 in cs["violations"]
    assert out["bundles"]["Z-C"]["status"] == "fail"
    out = hworld({K1: (hline(K1, "ref", "h1", stroke=None, F=None), hline(K1, "cand", "h1x", start=1.0, t_ready=50.1))})
    crit = out["bundles"]["Z-C"]["criteria"]
    assert crit["C-S"]["status"] == "pass" and crit["C-S"]["ref_none"] == [K1]
    assert crit["C-F"]["status"] == "pass" and crit["C-F"]["ref_none"] == [K1]
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1x", start=1.0, F=None, t_ready=50.1))})
    assert out["bundles"]["Z-C"]["criteria"]["C-F"]["status"] == "fail"
    # key absent stays undecidable
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1", drop=("d1.stroke_max_m",)))})
    assert out["bundles"]["Z-C"]["criteria"]["C-S"]["status"] == "undecidable"


def test_rev2_errors_left(hworld, tmp_path):
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1")),
                  K2: (hline(K2, "ref", "h2"), hline(K2, "cand", "h2"))})
    assert out["errors_total"] == 0 and out["errors_left"] == 0
    assert out["bundles"]["Z-C"]["errors_left"] == 0


def test_rev2_errors_left_counts_keys_without_normal_line(hworld, monkeypatch):
    orig = H.group_lines

    def drop_cand_k2(lines, arms, keyfun):
        keep = []
        for ln in lines:
            if H.line_key(ln) == K2 and H.line_arm(ln) == "cand":
                ln = dict(error="boom", rev=ln["rev"], __lineno__=ln.get("__lineno__"))
            keep.append(ln)
        return orig(keep, arms, keyfun)
    monkeypatch.setattr(H, "group_lines", drop_cand_k2)
    out = hworld({K1: (hline(K1, "ref", "h1"), hline(K1, "cand", "h1")),
                  K2: (hline(K2, "ref", "h2"), hline(K2, "cand", "h2"))})
    bz = out["bundles"]["Z-C"]
    assert bz["errors_total"] == 1 and bz["errors_left"] == 1 and bz["status"] == "undecidable"


def test_rev2_k1_token_job_keys(hworld):
    c = hline(K1, "cand", "h1")
    c["job"]["k1_order_gate"] = "on"
    out = hworld({K1: (hline(K1, "ref", "h1"), c)})
    assert out["bundles"]["Z-C"]["status"] == "stop"
    c = hline(K1, "cand", "h1")
    c["job"]["k1_note"] = "x"                       # not in the RV2-14 key set -> no stop
    out = hworld({K1: (hline(K1, "ref", "h1"), c)})
    assert out["bundles"]["Z-C"]["status"] == "pass"


def test_periods_round():
    assert H.per(34.95) == 350 and H.per(34.85) == 348 and C.per(29.999999999975) == 300


# ============================================================================ Chrono

def write_npz(path, t_end, scale=1.0):
    t = np.arange(8.0, t_end + 1e-9, 0.1)
    u = np.outer(np.sin(t), np.ones(4)) * 0.001 * scale
    np.savez(path, t_s=t, issued_u_m_s=u)


def cres(pid, start=None, ramp_applied=0, checks=None, F=12500.0, Ftr=12000.0, smax=0.62, t_ready=60.0,
         final="ready", events=None, decisions=None, drop_I=None, soil_extra=None, late=False,
         departed=True, drop_F=False, loc_corr=None):
    spec = C.ROWS[pid]
    arm = spec["arm"]
    tag = C.TAG_V0 if spec["v5"] == "V0" else C.TAG_VB
    ch = {k: True for k in C.I_KEYS}
    ch.update(checks or {})
    ch["P3-2_late_loc_reapproach"] = late
    ch["P3-2_late_loc_revoked"] = False
    if drop_I:
        del ch[drop_I]
    soil = dict(mode_starts=[], t_P_s=29.0, t_loc_s=30.0, bias_corner_raw_m=[0.0] * 4, bias_corner_m=[0.0] * 4,
                loc_anchor_applied=False, corner_order=["a", "b", "c", "d"], restored_from=None)
    soil.update(soil_extra or {})
    leg = dict(F_min_after_N=[F, F + 1000, F + 2000, F + 3000], F_min_transient_N=[Ftr] * 4)
    if drop_F:
        leg = {}
    out = dict(
        loc_corrections=loc_corr,
        args=dict(FIXED_ARGS_COPY, duration=spec["duration"], mass_scale=spec["mass"], expect_controller=tag),
        num_threads_chrono=4,
        placement=dict(mode="pcore", omp_wait_policy="PASSIVE", affinity_ok=True, power_throttling_off_ok=True),
        hull_hook=dict(mode="fast", requested="fast", fallback_reason=None, dll_sha256=C.DLL_SHA),
        code_state=dict(git_at_start=dict(head="abc", dirty=[]),
                        files_at_start=dict(c2=dict(path="03_src/outrigger_sim/control/c2.py", sha256="s"))),
        c2_setup=dict(expect_controller=dict(ok=True, name=tag), k1_order_gate="preset",
                      k1_forced_block=dict(requested="off", **{"class": "x.C2Controller"}),
                      las_candidate=dict(requested=C.ARM_LABEL[arm])),
        controller_meta=dict(
            soil=soil,
            slope_clearance_margin=dict(settings=dict(flat_soil_margin_order_gate=True),
                                        order_gate=dict(enabled=True, decisions=decisions or [])),
            loc_revoke=dict(t_revoke_s=[], revokes=0),
            liftoff_approach_slow=dict(start_s=start, end_s=None if start is None else start + 1, end_reason=None,
                                       active_periods=0, ramp=dict(periods_applied=ramp_applied),
                                       settings=dict(C.B0 if arm == "ref" else C.P5R4))),
        events=events if events is not None else [dict(name="crawler_liftoff_confirmed", t_s=30.0)],
        phases=[dict(phase="level", t_s=10.0), dict(phase=final, t_s=60.0)],
        p3b={"checks": ch, "P3-3_leg_force": leg, "departure": dict(departed=departed),
             "P3-5_clearance_stroke": dict(s_motor_max_m=[smax, smax - 0.01, smax - 0.02, smax - 0.03]),
             "P3-6_ready": dict(t_ready_after_loop_start_s=t_ready)},
    )
    if loc_corr is None:
        del out["loc_corrections"]
    return out


FIXED_ARGS_COPY = dict(C.FIXED_ARGS)


def argv_for(pid):
    spec = C.ROWS[pid]
    av = ["level", "--case", f"case_{pid}", "--las-candidate", C.ARM_LABEL[spec["arm"]],
          "--expect-controller", C.TAG_V0 if spec["v5"] == "V0" else C.TAG_VB]
    if spec["group"] == "A":
        av += ["--rigid-base", "FR"]
        if spec["kc"] == 3.0:
            av += ["--crawler-kn-scale", "3"]
    if spec["group"] == "B":
        av += ["--soil-patch", "J1@FL"]
    if spec["mass"] == 1.1:
        av += ["--mass-scale", "1.1"]
    return av


@pytest.fixture()
def cworld(tmp_path, monkeypatch):
    tmp = str(tmp_path)
    (r_path, r_sha), (r1_path, r1_sha), (r2_path, r2_sha) = write_rules(tmp)
    monkeypatch.setattr(C, "RULES_SHA", r_sha)
    monkeypatch.setattr(C, "RULES_REV1_SHA", r1_sha)
    monkeypatch.setattr(C, "RULES_REV2_SHA", r2_sha)
    rem = os.path.join(tmp, "rem")
    for case, _s in (C.REM_R7, C.REM_R8):
        os.makedirs(os.path.join(rem, case), exist_ok=True)
    write_npz(os.path.join(rem, C.REM_R7[0], "controller_commands.npz"), 128.0)
    write_npz(os.path.join(rem, C.REM_R8[0], "controller_commands.npz"), 128.0)
    monkeypatch.setattr(C, "REM_R7", (C.REM_R7[0], C.sha256_file(os.path.join(rem, C.REM_R7[0], "controller_commands.npz"))))
    monkeypatch.setattr(C, "REM_R8", (C.REM_R8[0], C.sha256_file(os.path.join(rem, C.REM_R8[0], "controller_commands.npz"))))

    def run(over=None, cmd_scale=None):
        over = over or {}
        cmd_scale = cmd_scale or {}
        bdir = os.path.join(tmp, "batch")
        os.makedirs(bdir, exist_ok=True)
        cases = []
        for pid, spec in C.ROWS.items():
            kw = dict(start=1.0, ramp_applied=4) if (spec["arm"] == "cand" and spec["group"] == "A") else {}
            kw.update(over.get(pid, {}))
            res = cres(pid, **kw)
            d = os.path.join(bdir, f"case_{pid}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "result.json"), "w", encoding="utf-8") as f:
                json.dump(res, f)
            t_end = {"C3": 188.0, "C4": 188.0}.get(pid, 128.0)
            write_npz(os.path.join(d, "controller_commands.npz"), t_end,
                      scale=cmd_scale.get(pid, 1.0 if spec["group"] != "A" else (2.0 if spec["arm"] == "cand" else 1.0)))
            cases.append(dict(case=f"case_{pid}", p5k_id=pid, rc=0, argv=argv_for(pid), las_candidate=C.ARM_LABEL[spec["arm"]],
                              omp_wait_policy="PASSIVE", planned_pool="pcore", pool="pcore"))
        with open(os.path.join(bdir, "batch.json"), "w", encoding="utf-8") as f:
            json.dump(dict(cases=cases, mixed_hull_mode=False), f)
        return C.recount(bdir, r_path, r1_path, r2_path, rem)
    return run


def test_chrono_baseline_pass(cworld):
    out = cworld()
    assert out["grade_provisional"] == "pass", (out["stop_reasons"], out["undecidable_reasons"], out["fail_reasons"])
    assert out["bt_c"]["C1"]["ok"] and out["bt_c"]["C3"]["ok"]
    assert out["observation"]["ok"] is True
    assert out["pairs"]["B1/B2"]["note"].startswith("P5r4 not acting")


def test_chrono_I_key_missing_undecidable(cworld):
    out = cworld({"B2": dict(drop_I="P3-7_within")})
    assert out["grade_provisional"] == "undecidable"
    assert out["pairs"]["B1/B2"]["undecidable"]


def test_chrono_late_loc_p32_exception(cworld):
    out = cworld({"C2": dict(checks={"P3-2_within": False}, late=True)})
    assert out["pairs"]["C1/C2"]["LATE_LOC_P32"] == ["P3-2_within"]
    assert out["criteria"]["CC-2"]["status"] == "pass"
    out = cworld({"C2": dict(checks={"P3-2_within": False}, late=False)})
    assert out["criteria"]["CC-2"]["status"] == "fail" and out["grade_provisional"] == "fail"


def test_chrono_observation_requirement(cworld):
    out = cworld({p: dict(start=None, ramp_applied=0) for p in ("A2", "A4", "A6")},
                 cmd_scale={"A2": 1.0, "A4": 1.0, "A6": 1.0})
    assert out["observation"]["ok"] is False
    assert out["grade_provisional"] == "undecidable"
    assert "NO_P5R4_OBSERVATION" in out["undecidable_reasons"]


def test_chrono_pair_diverge_stop(cworld):
    out = cworld(cmd_scale={"C2": 3.0})          # cand C2 not started but commands differ
    assert out["flags"]["PAIR_CMD_DIFF"] == ["A1/A2", "A3/A4", "A5/A6"]
    assert out["pairs"]["C1/C2"]["PAIR_DIVERGE"] is True
    assert out["grade_provisional"] == "stop"


def test_chrono_btc_mismatch_stop(cworld):
    out = cworld(cmd_scale={"C1": 1.5, "C2": 1.5})
    assert out["bt_c"]["C1"]["ok"] is False and out["grade_provisional"] == "stop"


def test_chrono_fail_plus_undecidable(cworld):
    out = cworld({"A2": dict(F=11000.0), "B2": dict(drop_I="P3-1_recontact_pass")})
    assert out["criteria"]["G-2'C"]["status"] == "fail"
    assert out["grade_provisional"] == "undecidable"


def test_chrono_g2c_transient(cworld):
    out = cworld({"A4": dict(Ftr=11400.0)})
    assert out["criteria"]["G-2'C"]["violations"] == {"A3/A4": ["cand below 11414.589 N"]}
    assert out["grade_provisional"] == "fail"


def test_chrono_ck1c_r4_lost(cworld):
    app = [dict(t_loc_s=30.0, t_P_s=29.0, t_S_s=20.0, r4_due_without_gate=True, applied=True, would_block=False, dP=90)]
    blk = [dict(t_loc_s=30.0, t_P_s=20.0, t_S_s=20.0, r4_due_without_gate=True, applied=False, would_block=True, dP=0)]
    ev_a = [dict(name="soil_mode_start", t_s=20.0), dict(name="crawler_liftoff_confirmed", t_s=30.0),
            dict(name="INFO_LOC_FLAT_SOIL_MARGIN:x", t_s=30.0)]
    ev_b = [dict(name="soil_mode_start", t_s=20.0), dict(name="crawler_liftoff_confirmed", t_s=30.0),
            dict(name="INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order", t_s=30.0)]
    se = dict(mode_starts=[dict(t_s=20.0)])
    out = cworld({"C1": dict(decisions=app, events=ev_a, soil_extra=se),
                  "C2": dict(decisions=blk, events=ev_b, soil_extra=se, start=2.0)},
                 cmd_scale={"C2": 1.0})
    assert out["k_checks"]["K-8"]["ok"] is True      # SKIPPED:order is not counted as an applied event
    assert out["criteria"]["CK-1C"]["violations"] == {"C1/C2": ["R4_LOST"]}


def test_chrono_no_departure_is_judged_not_missing(cworld):
    # cand A2 never departed: P3-3 force keys absent, p3b.departure.departed False -> judged (rules 10.1)
    out = cworld({"A2": dict(departed=False, drop_F=True)})
    p = out["pairs"]["A1/A2"]
    assert p["F_state"] == ["present", "no_departure"]
    assert out["criteria"]["G-2'C"]["status"] == "fail"
    assert out["criteria"]["CC-F"]["violations"] == {"A1/A2": ["cand no value (no departure)"]}
    assert out["grade_provisional"] == "fail"
    # ref without departure: CC-F out of scope for that pair
    out = cworld({"C1": dict(departed=False, drop_F=True)})
    assert out["pairs"]["C1/C2"]["CC-F"]["in_scope"] is False
    assert out["criteria"]["CC-F"]["status"] == "pass"


def test_chrono_force_keys_missing_with_departure_undecidable(cworld):
    out = cworld({"A4": dict(departed=True, drop_F=True)})
    assert out["criteria"]["G-2'C"]["status"] == "undecidable"
    assert out["criteria"]["CC-F"]["status"] == "undecidable"
    assert out["criteria"]["CC-S"]["status"] == "pass"   # other criteria of the pair stay decidable
    assert out["grade_provisional"] == "undecidable"


def test_chrono_rev2_ccs_none(cworld, monkeypatch):
    orig = C.recount_row

    def none_smax(res):
        r = orig(res)
        if res["args"]["expect_controller"] and res["c2_setup"]["las_candidate"]["requested"] == "P5r4" \
                and res["args"]["duration"] == 120.0:
            r["s_max_m"] = None                      # cand C2 stroke value None
        return r
    monkeypatch.setattr(C, "recount_row", none_smax)
    out = cworld()
    assert out["criteria"]["CC-S"]["violations"] == {"C1/C2": ["cand value None"]}
    assert out["grade_provisional"] == "fail"
    assert out["errors_total"] == 0 and out["errors_left"] == 0


def test_chrono_loc_corrections_cross_check(cworld):
    ev = [dict(name="crawler_liftoff_confirmed", t_s=30.0), dict(name="INFO_CLEARANCE_BIAS:FL=3", t_s=30.0)]
    lc = dict(locs=[dict(path=1, n_P=290, n_L=300, t_P_s=29.0, t_L_s=30.0)], n_locs=1)
    out = cworld({"B1": dict(events=ev, soil_extra=dict(bias_corner_m=[0.003, 0, 0, 0]), loc_corr=lc)})
    a = out["pairs"]["B1/B2"]["anchor"]["ref"]["loc_corrections"]
    assert a["path"] == "1" and all(a["agree"].values())
    lc_bad = dict(locs=[dict(path=3, n_P=290)], n_locs=1)
    out = cworld({"B1": dict(events=ev, soil_extra=dict(bias_corner_m=[0.003, 0, 0, 0]), loc_corr=lc_bad)})
    assert out["pairs"]["B1/B2"]["anchor"]["ref"]["loc_corrections"]["agree"]["path"] is False
    assert out["grade_provisional"] == "pass"           # record only


def test_chrono_anchor_flag(cworld):
    ev = [dict(name="crawler_liftoff_confirmed", t_s=30.0), dict(name="INFO_CLEARANCE_BIAS:FL=3", t_s=30.0)]
    se1 = dict(t_P_s=29.0, bias_corner_m=[0.003, 0, 0, 0], bias_corner_raw_m=[0.003, 0, 0, 0])
    se2 = dict(t_P_s=29.1, bias_corner_m=[0.003, 0, 0, 0], bias_corner_raw_m=[0.003, 0, 0, 0])
    out = cworld({"C1": dict(events=ev, soil_extra=se1),
                  "C2": dict(events=ev, soil_extra=se2, start=2.0, smax=0.6215)},
                 cmd_scale={"C2": 1.2})
    p = out["pairs"]["C1/C2"]
    assert p["anchor"]["flag"] is True and p["anchor"]["d_n_P_last"] == 1
    assert out["flags"]["anchor_effect_possible"] == ["C1/C2"]
    assert out["criteria"]["CC-S"]["status"] == "fail"
