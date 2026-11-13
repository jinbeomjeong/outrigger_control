"""Self-tests of p2_t3k.py (H-0 T-3K) on synthetic lines built from the sealed key lists (no run results)."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

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
    return {"liftoff_approach_slow": las, "k1_order_gate_effective": bundle != "R-0", "k1_order_gate_request": "preset",
            "slope_clearance_margin": {"settings": {"enable": True, "flat_soil_margin_m": 0.03,
                                                    "flat_soil_margin_order_gate": bundle != "R-0"},
                                       "order_gate": {"decisions": [{"would_block": wb, "applied": False,
                                                                     "n_P": 10, "n_S": 12}] if wb else []}}}


def line(key, bundle, h, verdict="pass", p32=True, g62=None, ready=50.0, stroke=0.4, names=None, wb=False, sub=None):
    setting = key.split("|")[-2]
    items = {}
    if p32 is not None:
        items["P3-2"] = p32
    if g62 is not None:
        items["G6-2_loc"] = g62
    return {"job": {}, "commands_sha256": h, "controller_tag": t3.TAGS[bundle][setting],
            "t3": {"bundle": sub or bundle, "las": "on" if bundle == "T-3K" else "off", "gate": "off" if bundle == "R-0" else "on"},
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
    sub = {e["key"]: b for b in ("T-3a", "T-3c") for e in KEYS[b]}
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
            t3l.append(dict(copy.deepcopy(b), controller_tag=t3.TAGS["T-3K"][e["setting"]], resume_k1=rk_block("T-3K"),
                            t3={"bundle": sub[k], "las": "on", "gate": "on"}))
        else:
            t3l.append(kl_line(e, "T-3K", sub=sub[k]))
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


def r73b_identity(**kw):
    """A rev7 R7-3b identity block."""
    li = {"git_head": "a" * 40, "sha256": {f: "b" * 64 for f in t3.IDENTITY_TOOL_FILES}, "c2_sha256": "c" * 64,
          "threads": {"MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                      "NUMBA_NUM_THREADS": "1", "MKL_THREADING_LAYER": "TBB"},
          "workers": 8, "affinity": "0x00FF0000"}
    li.update(kw)
    return li


def r73b_lines(li, line_li=None, header=True, mirror=None):
    """Header + two lines: ``header.identity`` and per line ``t3.identity`` with its mirrors."""
    line_li = line_li or li
    t3b = {"las": "off", "gate": "off", "identity": line_li, "commit": line_li.get("git_head"),
           "workers": line_li.get("workers"), "affinity_hex": line_li.get("affinity")}
    t3b.update(mirror or {})
    recs = ([{"header": {"identity": li}}] if header else []) + [{"t3": dict(t3b), "k": 1}, {"t3": dict(t3b), "k": 2}]
    return "".join(json.dumps(r) + "\n" for r in recs)


def outputs(tmp_path, idents, line_ids=None, text=None):
    paths = {}
    for n in ("R-0", "R-0K", "T-3K"):
        p = tmp_path / f"{n}.jsonl"
        li = (line_ids or {}).get(n, r73b_identity())
        p.write_text((text or {}).get(n) or r73b_lines(li), "utf-8")
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
    paths, steps = outputs(tmp_path, {}, {"T-3K": r73b_identity(c2_sha256="d" * 64)})
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd)
    Path(steps).write_text(json.dumps({"env": {"OUTRIGGER_LOC_SHADOW": "1"}}), "utf-8")
    paths, _ = outputs(tmp_path, {})
    Path(steps).write_text(json.dumps({"env": {"OUTRIGGER_LOC_SHADOW": "1"}}), "utf-8")
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd)


def test_rev7_r73b_identity_names_and_mirrors(tmp_path):
    paths, steps = outputs(tmp_path, {})
    fnd = core.Findings()
    out = t3.identity_check(paths, fnd, steps=(steps,))
    assert fnd.status() == "pass" and out["T-3K"]["checks"]["line_identity_format"] is True
    bad_cases = {
        "old names": r73b_lines({"git_head": "a" * 40, "c2_sha256": "c" * 64, "tool_sha256": "t" * 64,
                                 "affinity_mask": "0xff", "threads": 1, "workers": 8}),
        "sha256 not a dict of six": r73b_lines(r73b_identity(sha256="b" * 64)),
        "threads keys": r73b_lines(r73b_identity(threads={"MKL_NUM_THREADS": "1"})),
        "affinity_hex mirror": r73b_lines(r73b_identity(), mirror={"affinity_hex": "0xFF"}),
        "commit mirror": r73b_lines(r73b_identity(), mirror={"commit": "e" * 40}),
        "no header": r73b_lines(r73b_identity(), header=False),
    }
    for why, text in bad_cases.items():
        paths, steps = outputs(tmp_path, {}, text={"T-3K": text})
        fnd = core.Findings()
        out = t3.identity_check(paths, fnd, steps=(steps,))
        assert "S-11" in stop_codes(fnd), why
        assert out["T-3K"]["checks"]["line_identity_format"] is False, why
    # header measured by the parent vs a worker line that differs: R6-C2 "header and every line the same"
    text = r73b_lines(r73b_identity(), line_li=r73b_identity(workers=4))
    paths, steps = outputs(tmp_path, {}, text={"T-3K": text})
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert "H-T3-3" in stop_codes(fnd) and "S-11" not in stop_codes(fnd)
    # affinity null (no --affinity) is a valid record
    li = r73b_identity(affinity=None)
    paths, steps = outputs(tmp_path, {}, {n: li for n in ("R-0", "R-0K", "T-3K")})
    fnd = core.Findings()
    t3.identity_check(paths, fnd, steps=(steps,))
    assert fnd.status() == "pass"


def test_rev7_header_line_skipped_in_recount():
    r0, r0k, t3l, d0, dt = all_inputs()
    hdr = {"header": {"identity": r73b_identity()}}
    _, f = run([hdr] + r0, [hdr] + r0k, [hdr] + t3l, d0, dt)
    assert f.status() == "pass", f.as_dict()["stops"][:3]


def test_rev7_r71c_all_off_reads_final_c4g2():
    r0, *rest = all_inputs()
    v0 = next(x for x in r0 if x["d1"]["key"].split("|")[-2] == "V0")
    v0.pop("controller_tag")                       # no key at all
    body, f = run(r0, *rest)
    assert f.status() == "pass", f.as_dict()["stops"][:3]
    row = next(x for x in body["R-0"] if x.get("key") == v0["d1"]["key"])
    assert row["tag_read"] == "final_C4G2" and row["tag_read_source"] == "R7-1c all-off"
    assert body["R7-1c_tag_reading"]["R-0"]["R7-1c all-off"] >= 1
    # K-2 unchanged: a recorded "final_C4G2" on the R-0 V0 line is still H-T3-3 (R3-D2)
    v0["controller_tag"] = "final_C4G2"
    _, f = run(r0, *rest)
    assert "H-T3-3" in stop_codes(f) and "S-11" not in stop_codes(f)
    # no tag key and not all-off (gate on) -> a missing key, S-11
    v0.pop("controller_tag")
    v0["t3"]["gate"] = "on"
    _, f = run(r0, *rest)
    assert "S-11" in stop_codes(f)
    # an R-0K line without its tag: S-11 (key missing) besides H-T3-3 (K-2K tag)
    r0b, r0k, t3l, d0, dt = all_inputs()
    r0k[0].pop("controller_tag")
    _, f = run(r0b, r0k, t3l, d0, dt)
    assert {"S-11", "H-T3-3"} <= stop_codes(f)
    codes = sorted(stop_codes(f), key=lambda c: t3.ORDER.index(c) if c in t3.ORDER else 99)
    assert codes[0] == "S-11" and t3.EXIT_OF["S-11"] == 2


# ------------------------------------------------------------------ 436.8 rev11 R11-1
def test_rev11_r111_kinds_and_all_off_r0_passes():
    body, f = run(*all_inputs())
    assert f.status() == "pass", f.as_dict()["stops"][:3]
    r = body["R11-1_record_check"]
    assert r["R-0"]["kinds"] == {"R-0": 5} and r["R-0K"]["kinds"] == {"R-0K": 45}
    assert r["T-3K"]["kinds"]["T-3K"] == 304 and "kind_defect" not in r["T-3K"]
    assert r["R-0"]["gate_request_recorded"] == {"R-0": {"preset": 5}}
    assert t3.line_kind({"t3": {"bundle": "R-0", "las": "off", "gate": "off"}}) == ("R-0", None)
    assert t3.line_kind({"t3": {"bundle": "T-3b", "las": "on", "gate": "on"}}) == ("T-3K", None)


def test_rev11_r111_r0_line_with_gate_off_record_is_not_s3():
    """The R-0 line records gate off / LAS-b off (path 1 read 'on' and gave S-3): no S-3 here."""
    r0, *rest = all_inputs()
    assert r0[0]["resume_k1"]["k1_order_gate_effective"] is False
    assert r0[0]["resume_k1"]["liftoff_approach_slow"]["settings"] == {"enable": False}
    _, f = run(r0, *rest)
    assert "S-3" not in stop_codes(f)


@pytest.mark.parametrize("bundle_idx, mutate, want", [
    (0, lambda ln: ln["t3"].pop("bundle"), "S-3"),                                    # kind field missing
    (0, lambda ln: ln["t3"].update(gate="on"), "S-3"),                                # R-0 with gate on
    (1, lambda ln: ln["t3"].update(bundle="R-0"), "S-3"),                             # R-0 kind in the R-0K file
    (2, lambda ln: ln["t3"].update(bundle="T-3c" if ln["t3"]["bundle"] == "T-3a" else "T-3a"), "S-3"),
    (0, lambda ln: ln["resume_k1"].update(k1_order_gate_effective=True), "S-3"),      # R-0 gate effective on
    (0, lambda ln: ln["resume_k1"]["slope_clearance_margin"]["settings"].pop("flat_soil_margin_order_gate"), "S-3"),
    (1, lambda ln: ln["resume_k1"]["liftoff_approach_slow"]["settings"].update(enable=True), "S-3"),
    (2, lambda ln: ln["resume_k1"].update(k1_order_gate_request="on"), "S-3"),        # T-3K request = preset
])
def test_rev11_r111_defects(bundle_idx, mutate, want):
    inp = list(all_inputs())
    mutate(inp[bundle_idx][0])
    _, f = run(*inp)
    assert want in stop_codes(f), f.as_dict()["stops"][:3]
    assert t3.ORDER.index("S-3") == 2 and t3.EXIT_OF["S-3"] == 2


def test_rev11_r111_request_record_only_on_r0_and_r0k_and_gs_code():
    inp = list(all_inputs())
    inp[0][0]["resume_k1"]["k1_order_gate_request"] = "on"       # R-0 / R-0K request: record only
    inp[1][0]["resume_k1"]["k1_order_gate_request"] = None
    body, f = run(*inp)
    assert "S-3" not in stop_codes(f)
    rr = body["R11-1_record_check"]
    assert rr["R-0"]["gate_request_recorded"]["R-0"] == {"on": 1, "preset": 4}
    assert rr["R-0K"]["gate_request_recorded"]["R-0K"]["None"] == 1
    inp[0][0]["t3"].pop("las")                                   # kind input defect in G-S = S-11
    _, f = t3.recount(REPO, *inp, None, IS_P3, gs=True)
    assert "S-11" in stop_codes(f) and not any(s["code"] == "S-3" and "R11-1: t3" in s["why"] for s in f.stops)
