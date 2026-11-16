"""Self-tests of p2_x16.py (H-11 G-3, C-9~C-11 records, RD-13 item lists) on synthetic inputs only."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_x16", HERE / "p2_x16.py")
x16 = importlib.util.module_from_spec(spec)
sys.modules["p2_x16"] = x16
spec.loader.exec_module(x16)
core = x16.core
REPO = HERE.parents[4]
FAKE_M4 = "4" * 40
core.git_head = lambda repo: FAKE_M4          # R4 RD-1 5: tests stand in for the M4 checkout HEAD
R2 = core.R2_COMMIT


def run(argv, capsys):
    if "--expect-head" not in argv and argv[argv.index("--out") + 2] in ("g3", "c16"):
        argv = argv + ["--expect-head", FAKE_M4]
    code = x16.main(["--repo", str(REPO)] + argv)
    last = capsys.readouterr().out.strip().splitlines()[-1]
    return code, json.loads(last)


# ------------------------------------------------------------------ H-11 G-3
def ident(head=R2, clean=True):
    rec = {"git": {"head": head, "is_clean": clean, "status_porcelain": "" if clean else " M x.py"}}
    return {"start": [rec], "end": [rec]}


def h11_setup(tmp_path, change=None, dup=None, bad_ident=None):
    h11, lk = tmp_path / "H-11", tmp_path / "las_k1"
    h11.mkdir()
    lk.mkdir()
    files = {}
    for script, key, none_name, cmp_ref, cont, field, ctrl in x16.G3_PAIRS:
        idf = "id" if cont == "records" and ctrl is None else ("case" if ctrl else ("id" if "run." in field else "key"))
        h = f"{abs(hash(key)) % (16 ** 16):016x}"
        item = {idf: key}
        if ctrl:
            item["controller"] = ctrl
        cur = item
        parts = field.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = h
        for target in (("h11", none_name), tuple(cmp_ref.split(":", 1))):
            files.setdefault(target, {"cont": cont, "items": []})["items"].append(json.loads(json.dumps(item)))
    if change:
        tgt, key = change
        for it in files[tgt]["items"]:
            if key in json.dumps(it):
                it.update({k: ("f" * 16 if isinstance(v, str) and k in ("hash", "commands_sha256") else v)
                           for k, v in it.items()})
                if "run" in it:
                    it["run"]["commands_sha256"] = "f" * 16
    if dup:
        tgt, key = dup
        files[tgt]["items"] += [dict(it) for it in files[tgt]["items"] if key in json.dumps(it)]
    for (d, name), v in files.items():
        p = (h11 if d == "h11" else lk) / name
        p.write_text(json.dumps({"meta": {}, v["cont"]: v["items"]}), "utf-8")
        if d == "h11":
            idn = h11 / (Path(name).stem + ".identity.json")
            bad = bad_ident is not None and bad_ident[0] == name
            idn.write_text(json.dumps(ident(**bad_ident[1]) if bad else ident()), "utf-8")
    return h11, lk


def test_g3_true(tmp_path, capsys):
    h11, lk = h11_setup(tmp_path)
    out = tmp_path / "g3.json"
    code, s = run(["--out", str(out), "g3", "--h11-dir", str(h11), "--las-k1-dir", str(lk)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["G-3"] is True and rep["n_pairs"] == 8 and rep["G-3_false_list"]["rows"] == []
    assert all(v["ok"] for v in rep["identity"].values()) and len(rep["identity"]) == 6   # 5 option-free + b5 V0


def test_g3_false_hash_and_list(tmp_path, capsys):
    h11, lk = h11_setup(tmp_path, change=(("las_k1", "u3_C_V0.json"), "g6r|rigid+J1@FL|top|Fs8"))
    out = tmp_path / "g3.json"
    code, s = run(["--out", str(out), "g3", "--h11-dir", str(h11), "--las-k1-dir", str(lk)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and rep["G-3"] is False and rep["marker"] == x16.G3_MARKER
    rows = rep["G-3_false_list"]["rows"]
    assert len(rows) == 1 and rows[0]["script"] == "r72_g6_screen.py" and rows[0]["compare_hash"] == "f" * 16
    assert rows[0]["none_lines"] == rows[0]["compare_lines"] == 1
    assert rep["consequence"].startswith("H-3 / H-4 not judged")


def test_g3_count_check_duplicate_line(tmp_path, capsys):
    h11, lk = h11_setup(tmp_path, dup=(("h11", "u6_b5_A1_none.json"), "A1-J1"))
    out = tmp_path / "g3.json"
    code, s = run(["--out", str(out), "g3", "--h11-dir", str(h11), "--las-k1-dir", str(lk)], capsys)
    rows = json.loads(out.read_text("utf-8"))["G-3_false_list"]["rows"]
    assert code == 2 and [r["key"] for r in rows] == ["A1-J1"] and rows[0]["none_lines"] == 2


@pytest.mark.parametrize("bad", [{"head": "a" * 40}, {"clean": False}])
def test_g3_identity_s12(tmp_path, capsys, bad):
    h11, lk = h11_setup(tmp_path, bad_ident=("u3_p3b_none.json", bad))
    out = tmp_path / "g3.json"
    code, s = run(["--out", str(out), "g3", "--h11-dir", str(h11), "--las-k1-dir", str(lk)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and "S-12" in rep["stop_codes"] and rep["G-3"] is True


# ------------------------------------------------------------------ C-9 ~ C-11
def row_folder(root, bundle, name, duration, vb=False, ready=60.0, threads=4, decisions=(), patch=None):
    d = root / bundle / name
    (d / "record").mkdir(parents=True)
    n = int(duration * 1000) + 1
    t = np.arange(n) * 1e-3
    cr = np.where(t < 30.0, 50000.0, 0.0)
    cr[(t > 40.05) & (t < 40.07)] = 4000.0                     # inside the C-11 LOC period (40.0 - 0.1, 40.0]? no
    cr[(t > 39.95) & (t <= 39.96)] = 3500.0
    F = np.full((n, 4), 60000.0)
    F[(t > 31.0) & (t < 31.2), 2] = 9000.0
    s = np.tile(np.linspace(0.0, 0.3, n)[:, None], (1, 4))
    sink = np.full((n, 4), 0.01)
    np.savez(d / "step_series.npz", t_s=t, scm_crawler_normal_N=cr, F_cyl_N=F, s_motor_m=s,
             pad_sinkage_geometric_m=sink)
    for f in ("controller_commands.npz", "r8_series.npz", "completion_series.npz", "record/record.npz"):
        np.savez(d / f, x=np.arange(3) if "commands" not in f else np.arange(5))
    (d / "record" / "meta.json").write_text("{}", "utf-8")
    if vb:
        np.savez(d / "flow_series.npz", x=np.arange(2))
    res = {"args": {"duration": duration, "flow_eta_v": 0.85 if vb else None}, "num_threads_chrono": threads,
           "placement": {"omp_wait_policy": "PASSIVE", "requested": "pcore", "affinity_mask_process": "0xF"},
           "hull_hook": {"mode": "fast", "dll_sha_validated": True, "dll_sha256": x16.DLL_SHA, "fallback_reason": None},
           "code_state": {"git_at_start": {"head": R2}},
           "controller_meta": {"slope_clearance_margin": {"order_gate": {"enabled": True,
                                                                          "decisions": list(decisions)}}},
           "phases": [{"t_s": 0.0, "phase": "check"}, {"t_s": ready, "phase": "ready"}],
           "p3b": {"weight_N": 3.8e5, "checks": {k: True for k in x16.P3_CHECKS},
                   "P3-2_loc": {"t_loc_s": 40.0, "t_loc_first_s": 40.0, "t_loc_final_s": 40.0,
                                "soil_mode_start_t_s": None, "loc_revokes": []},
                   "P3-5_clearance_stroke": {"t_first_ready_s": ready, "rut_clearance_end_m": 0.05}}}
    (d / "result.json").write_text(json.dumps(res), "utf-8")
    return d


def identity_files(idd, stem, rc=0, head=R2):
    idd.mkdir(exist_ok=True)
    pre = {"git": {"head": head, "status_porcelain": ""}, "env": {"OMP_WAIT_POLICY": "PASSIVE"},
           "forbidden": {e: {"set": False} for e in x16.FORBIDDEN_ENV}, "dll_sha256": x16.DLL_SHA}
    post = {"git": {"head": head, "status_porcelain": "", "reflog": ["a", "b"]}, "rc": rc,
            "forbidden": {e: {"set": False} for e in x16.FORBIDDEN_ENV}}
    (idd / f"{stem}_pre.json").write_text(json.dumps(pre), "utf-8")
    (idd / f"{stem}_post.json").write_text(json.dumps(post), "utf-8")


def c16_setup(tmp_path, **over):
    root, idd = tmp_path / "OUT", tmp_path / "OUT" / "_identity"
    for bundle, name, dur, stem, patch in x16.C16_ROWS:
        kw = dict(over.get(name, {}))
        rc = kw.pop("rc", 0)
        row_folder(root, bundle, name, dur, vb=name.endswith("_VB"), patch=patch, **kw)
        identity_files(idd, stem, rc=rc)
    return root, idd


def test_c16_complete_and_items(tmp_path, capsys):
    root, idd = c16_setup(tmp_path)
    out = tmp_path / "c16.json"
    code, s = run(["--out", str(out), "c16", "--out-root", str(root), "--identity-dir", str(idd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["undecidable"][:3]
    assert {b: v["status"] for b, v in rep["bundles"].items()} == {"C-9": "기록 완료", "C-10": "기록 완료",
                                                                    "C-11": "기록 완료"}
    assert rep["C-9_P-18"]["premise"] is True and rep["C-9_P-18"]["commands_equal"] is True
    c10 = rep["rows"]["R4368X_rigidS1FL_B_top_Fs4_V0"]["items"]
    assert c10["patch_leg"] == "FL" and abs(c10["patch_leg_sinkage_mm"] - 10.0) < 1e-9
    assert c10["force"]["legs"][2]["F_min_after_N"] == 9000.0 and abs(c10["force"]["t_departure_s"] - 30.0) < 1e-9
    assert abs(c10["force"]["legs"][2]["t_below_F_min_s"] - 0.199) < 2e-3
    c11 = rep["rows"]["R4368X_J2_B_top_Fs0_L2_V0"]["items"]
    assert c11["loc_period_crawler_max_N"] == 3500.0 and c11["above_0p01W"] is False and c11["loc_revokes"] == 0
    assert abs(c11["loc_period_crawler_max_over_W"] - 3500.0 / 3.8e5) < 1e-12
    c9 = rep["rows"]["R4368X_G1_B_top_Fs4_V0_gateon"]["items"]
    assert c9["rc"] == 0 and c9["first_ready_s"] == 60.0 and abs(c9["max_stroke_mm"] - 300.0) < 1e-9
    assert abs(c9["end_rut_gap_mm"] - 50.0) < 1e-9 and abs(c9["last_sample_t_s"] - 120.0) < 1e-9


def test_c16_p18_premise_and_missing_identity(tmp_path, capsys):
    root, idd = c16_setup(tmp_path, R4368X_G1_B_top_Fs4_V0_gateoff={"rc": 1})
    out = tmp_path / "c16.json"
    code, s = run(["--out", str(out), "c16", "--out-root", str(root), "--identity-dir", str(idd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["C-9_P-18"]["premise"] is False and rep["bundles"]["C-9"]["status"] == "기록 불완전"
    assert rep["bundles"]["C-11"]["status"] == "기록 완료" and code == 1
    (idd / "C11VB_post.json").unlink()
    code, s = run(["--out", str(out), "c16", "--out-root", str(root), "--identity-dir", str(idd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["bundles"]["C-11"]["status"] == "기록 불완전"


def test_c16_identity_stops(tmp_path, capsys):
    root, idd = c16_setup(tmp_path, R4368X_J2_B_top_Fs0_L2_VB={"threads": 8})
    out = tmp_path / "c16.json"
    code, s = run(["--out", str(out), "c16", "--out-root", str(root), "--identity-dir", str(idd)], capsys)
    assert code == 2 and "S-4" in s["stop_codes"]
    identity_files(idd, "C9on", head="b" * 40)
    code, s = run(["--out", str(out), "c16", "--out-root", str(root), "--identity-dir", str(idd)], capsys)
    assert "S-12" in s["stop_codes"]


# ------------------------------------------------------------------ RD-13 items, HEAD, seals
def test_items_lists_and_sha(tmp_path, capsys):
    out = tmp_path / "items.json"
    code, s = run(["--out", str(out), "items"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and set(rep["lists"]) == {"H-1", "H-2", "H-3", "H-4", "H-5", "H-6", "H-7", "H-8", "H-9", "H-10",
                                               "H-11", "C-9", "C-10", "C-11", "J_P"}
    for b, lst in rep["lists"].items():
        assert all(r["kind"] in ("등급 항목", "기록", "관문") and r["clause"] for r in lst), b
        assert rep["list_sha256"][b] == x16.canonical_sha(lst)
    assert s["list_sha256"] == rep["list_sha256"]


def test_head_check_s12_and_seals(tmp_path, capsys):
    out = tmp_path / "o.json"
    code, s = run(["--out", str(out), "g3", "--h11-dir", str(tmp_path), "--expect-head", "5" * 40], capsys)
    assert code == 2 and s["stop_codes"] == ["S-12"]
    code, s = run(["--out", str(out), "items"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["seals"]["r4_common_block_sha256"] == core.R4_BLOCK_SHA and len(rep["seals"]["r4_rev13_25_sha256"]) == 13
