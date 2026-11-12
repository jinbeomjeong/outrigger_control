"""Self-tests of p2_t3k.py (H-0 T-3K) on synthetic lines built from the sealed key lists (no run results)."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_t3k", HERE / "p2_t3k.py")
t3 = importlib.util.module_from_spec(spec)
sys.modules["p2_t3k"] = t3
spec.loader.exec_module(t3)
core = t3.core
REPO = HERE.parents[4]
IS_P3 = lambda t: t is not None and "_P3" in t   # noqa: E731 - stand-in for v5_options in unit tests
KEYS = json.loads((REPO / t3.REV3_KEYS_REL).read_text("utf-8"))
R0K = json.loads((REPO / t3.R0K_KEYS_REL).read_text("utf-8"))["R-0K"]


def rk_block(bundle, wb=False):
    las = {"settings": dict(t3.LAS_B0)} if bundle == "T-3K" else {"settings": {"enable": False}}
    return {"liftoff_approach_slow": las, "k1_order_gate_effective": bundle != "R-0",
            "slope_clearance_margin": {"settings": {"enable": True, "flat_soil_margin_m": 0.03,
                                                    "flat_soil_margin_order_gate": bundle != "R-0"},
                                       "order_gate": {"decisions": [{"would_block": wb, "applied": False,
                                                                     "n_P": 10, "n_S": 12}] if wb else []}}}


def line(key, bundle, h, verdict="pass", p32=True, g62=None, ready=50.0, stroke=0.4, names=None, wb=False):
    setting = key.split("|")[-2]
    items = {}
    if p32 is not None:
        items["P3-2"] = p32
    if g62 is not None:
        items["G6-2_loc"] = g62
    return {"job": {}, "commands_sha256": h, "controller_tag": t3.TAGS[bundle][setting],
            "event_names": dict(names or {}), "resume_k1": rk_block(bundle, wb),
            "d1": {"key": key, "verdict": verdict, "fail_items": [], "items": items, "t_ready_s": ready,
                   "stroke_max_m": stroke}}


def kl_line(e, bundle, **kw):
    base = dict(h=e["commands_sha256"], verdict=e["verdict"], p32=e.get("P3-2"), ready=e.get("t_ready_s"),
                stroke=e.get("stroke_max_m"), names={n: 1 for n in e.get("fault_names") or []})
    base.update(kw)
    return line(e["key"], bundle, **base)


def all_inputs():
    kl = {e["key"]: e for b in ("T-3a", "T-3c") for e in KEYS[b]}
    r0k = {e["key"]: e for e in R0K}
    r0 = []
    for k in KEYS["R-0"]["d1"]:
        h = kl[k]["commands_sha256"] if k in kl else r0k[k]["stored_commands_sha256"]
        r0.append(kl_line(kl[k], "R-0") if k in kl else line(k, "R-0", h))
    r0kl = [kl_line(kl[k], "R-0K", h=e["stored_commands_sha256"], wb=e["class"] == "patch_r4") if k in kl
            else line(k, "R-0K", e["stored_commands_sha256"]) for k, e in r0k.items()]
    t3l = []
    for k, e in kl.items():
        if k in r0k:
            b = next(x for x in r0kl if x["d1"]["key"] == k)
            t3l.append(dict(copy.deepcopy(b), controller_tag=t3.TAGS["T-3K"][e["setting"]], resume_k1=rk_block("T-3K")))
        else:
            t3l.append(kl_line(e, "T-3K"))
    hd = lambda e: {"commands_sha256": e["shadow_commands_sha256_all_folders"][0], "events": []}  # noqa: E731
    d0 = [(f, k, hd(next(x for x in KEYS["T-3b"] if (x["folder"], x["key"]) == (f, k)))) for f, k in KEYS["R-0"]["dg3"]]
    dt = [(e["folder"], e["key"], hd(e)) for e in KEYS["T-3b"]]
    return r0, r0kl, t3l, d0, dt


def run(r0, r0k, t3l, d0, dt):
    return t3.recount(REPO, r0, r0k, t3l, d0, dt, None, IS_P3)


def stop_codes(f):
    return {s["code"] for s in f.stops}


def test_counts_of_key_lists():
    assert len(KEYS["T-3a"]) == 228 and len(KEYS["T-3b"]) == 4 and len(KEYS["T-3c"]) == 76 and len(R0K) == 45


def test_all_pass():
    body, f = run(*all_inputs())
    assert f.status() == "pass", f.as_dict()["stops"][:3]
    assert body["T-3K"]["counts"]["T-3a"] == 228 and body["T-3K"]["counts"]["T-3c"] == 76
    assert body["T-3K"]["counts"]["active"] == 0


def test_r0_hash_change_is_h_t3_1():
    r0, *rest = all_inputs()
    r0[0]["commands_sha256"] = "0" * 64
    _, f = run(r0, *rest)
    assert "H-T3-1" in stop_codes(f)


def test_r0k_uniform_block_is_h_t3_1q_and_no_r4_hash_is_1k():
    r0, r0k, *rest = all_inputs()
    u = next(x for x in r0k if dict((e["key"], e["class"]) for e in R0K)[x["d1"]["key"]] == "uniform_r4")
    u["resume_k1"] = rk_block("R-0K", wb=True)
    n = next(x for x in r0k if dict((e["key"], e["class"]) for e in R0K)[x["d1"]["key"]] == "r0_no_r4")
    n["commands_sha256"] = "1" * 64
    _, f = run(r0, r0k, *rest)
    assert {"H-T3-1Q", "H-T3-1K"} <= stop_codes(f)


def test_t3k_tag_las_without_k1_and_config():
    r0, r0k, t3l, d0, dt = all_inputs()
    t3l[0]["controller_tag"] = "final_C4G2_LAS"
    t3l[1]["resume_k1"]["liftoff_approach_slow"]["settings"]["rho_on"] = 0.2
    _, f = run(r0, r0k, t3l, d0, dt)
    assert "H-T3-3" in stop_codes(f)


def test_g1_uniform_active_is_h_t3_4_and_inactive_hash_is_h_t3_5():
    r0, r0k, t3l, d0, dt = all_inputs()
    g1 = [x for x in t3l if "|G1|" in x["d1"]["key"] and "H-S-0" in x["d1"]["key"]]
    g1[0]["event_names"]["INFO_LIFTOFF_SLOW"] = 1
    other = next(x for x in t3l if "|J1|" in x["d1"]["key"])
    other["commands_sha256"] = "2" * 64
    _, f = run(r0, r0k, t3l, d0, dt)
    assert {"H-T3-4", "H-T3-5"} <= stop_codes(f)


def test_active_row_k6_pass_and_fail():
    r0, r0k, t3l, d0, dt = all_inputs()
    j = next(x for x in t3l if "|J1|" in x["d1"]["key"] and x["d1"]["t_ready_s"] is not None)
    j["event_names"]["INFO_LIFTOFF_SLOW"] = 1
    j["commands_sha256"] = "3" * 64
    j["d1"]["t_ready_s"] += 4.0
    body, f = run(r0, r0k, t3l, d0, dt)
    assert f.status() == "pass" and body["T-3K"]["counts"]["active"] == 1
    j["d1"]["t_ready_s"] += 1.5                  # +5.5 s
    j["d1"]["stroke_max_m"] += 0.002
    j["event_names"]["FAULT_STROKE_END"] = 1
    body, f = run(r0, r0k, t3l, d0, dt)
    v = {c for c, _ in body["T-3K"]["K-6_violations"][0]["violations"]}
    assert {"K-6c", "K-6d", "K-6e"} <= v and "H-T3-6" in stop_codes(f)


def test_k6_items_and_fail_items():
    base = {"verdict": "fail", "fail_items": ["A"], "P3-2": True, "G6-2_loc": core.MISSING, "t_ready_s": None,
            "stroke_max_m": 0.4, "faults": set()}
    new = dict(base, fail_items=["A", "B"], **{"P3-2": core.MISSING})
    v = {c for c, _ in t3.k6(new, base)}
    assert v == {"K-6a", "K-6b"}
    ok = dict(base)
    assert t3.k6(ok, base) == []                # both READY None: pass


def test_dg3_t3b_active_and_key_set():
    r0, r0k, t3l, d0, dt = all_inputs()
    dt[0][2]["events"] = [[30.0, "INFO_LIFTOFF_SLOW"]]
    _, f = run(r0, r0k, t3l, d0, dt)
    assert "H-T3-4" in stop_codes(f)
    _, f = run(r0, r0k, t3l, d0, dt[1:])
    assert "H-T3-3" in stop_codes(f)


def test_error_line_and_missing_key():
    r0, r0k, t3l, d0, dt = all_inputs()
    t3l[5]["error"] = "boom"
    _, f = run(r0, r0k, t3l, d0, dt)
    assert {"H-T3-2", "H-T3-3"} <= stop_codes(f)


def test_inactive_non_r0k_with_would_block_is_h_t3_5():
    r0, r0k, t3l, d0, dt = all_inputs()
    r0k_keys = {e["key"] for e in R0K}
    x = next(x for x in t3l if x["d1"]["key"] not in r0k_keys)
    x["resume_k1"] = rk_block("T-3K", wb=True)
    _, f = run(r0, r0k, t3l, d0, dt)
    assert "H-T3-5" in stop_codes(f)


def test_seals_real():
    ok, out = t3.check_las_seals(REPO)
    assert ok, {k: v for k, v in out.items() if not v["ok"]}


def test_rev3_dg3_key_prefix_and_folder_from_record(tmp_path):
    p = tmp_path / "dg3.jsonl"
    recs = [{"key": "L3|s0|g6|48|ref|G1|top|Fs0", "commands_sha256": "a", "events": [],
             "preset_settings": {"two_pressure.extend_start_rule": "constant"}},
            {"key": "cand=current#L3|s2|ref|14|G1|B|0,0", "commands_sha256": "b", "events": [],
             "controller_settings": {"two_pressure": {"extend_start_rule": "tracked_bound"}}},
            {"key": "x", "commands_sha256": "c"}]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", "utf-8")
    got = [(f, k) for f, k, _ in t3.dg3_records(p)]
    assert got == [("off", "L3|s0|g6|48|ref|G1|top|Fs0"), ("v4_on", "L3|s2|ref|14|G1|B|0,0"), (None, "x")]
    conflict = [r for _, _, r in t3.dg3_records(p, "v4_on")][0]
    assert conflict.get("_folder_conflict")


def test_rev3_dg3_folder_missing_is_h_t3_3():
    r0, r0k, t3l, d0, dt = all_inputs()
    dt[0] = (None, dt[0][1], dt[0][2])
    _, f = run(r0, r0k, t3l, d0, dt)
    assert "H-T3-3" in stop_codes(f)


def test_rev3_r0_v0_tag_empty_string_is_h_t3_3():
    r0, *rest = all_inputs()
    v0 = next(x for x in r0 if x["d1"]["key"].split("|")[-2] == "V0")
    v0["controller_tag"] = ""
    _, f = run(r0, *rest)
    assert "H-T3-3" in stop_codes(f)


def ident(head="abc", clean=True, threads=None, seals_ok=True):
    th = threads or {"MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                     "NUMBA_NUM_THREADS": "1", "MKL_THREADING_LAYER": "TBB"}
    rec = {"python": "x", "threads": th, "affinity_mask": "0xff", "git": {"head": head, "is_clean": clean,
           "status_porcelain": ""}, "rules_seals": {"v5_resume_4368_rules.md": {"ok": seals_ok}}}
    return {"start": rec, "end": rec}


def outputs(tmp_path, idents, line_ids=None):
    paths = {}
    for n in ("R-0", "R-0K", "T-3K"):
        p = tmp_path / f"{n}.jsonl"
        li = (line_ids or {}).get(n, {"git_head": "abc", "c2_sha256": "c", "tool_sha256": "t", "threads": 1})
        p.write_text(json.dumps({"identity": li, "k": 1}) + "\n" + json.dumps({"identity": li, "k": 2}) + "\n", "utf-8")
        (tmp_path / f"{n}.jsonl.identity.json").write_text(json.dumps(idents.get(n, ident())), "utf-8")
        paths[n] = str(p)
    steps = tmp_path / "steps_h0.json"
    steps.write_text(json.dumps({"env": {"MKL_THREADING_LAYER": "TBB"}}), "utf-8")
    return paths, str(steps)


def test_rev6_k0_identity(tmp_path):
    paths, steps = outputs(tmp_path, {})
    fnd = core.Findings()
    out = t3.identity_check(paths, fnd, steps=(steps,))
    assert fnd.status() == "pass" and out["line_identity_same_across_outputs"]
    fnd = core.Findings()
    t3.identity_check(paths, fnd)                       # no step files: env item undecidable
    assert fnd.status() == "undecidable"
    paths, steps = outputs(tmp_path, {"T-3K": ident(head="xyz")}, )
    fnd = core.Findings()
    t3.identity_check(paths, fnd, git_at_start="abc", steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd)
    paths, steps = outputs(tmp_path, {"R-0": ident(seals_ok=False)})
    fnd = core.Findings()
    out = t3.identity_check(paths, fnd, steps=(steps,))
    assert out["R-0"]["checks"]["rules_seals"] is False
    paths, steps = outputs(tmp_path, {}, {"T-3K": {"git_head": "abc", "c2_sha256": "OTHER", "tool_sha256": "t"}})
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd)
    Path(steps).write_text(json.dumps({"env": {"OUTRIGGER_LOC_SHADOW": "1"}}), "utf-8")
    paths, _ = outputs(tmp_path, {})
    Path(steps).write_text(json.dumps({"env": {"OUTRIGGER_LOC_SHADOW": "1"}}), "utf-8")
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd)
