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
def row_folder(root, bundle, name, duration, vb=False, ready=60.0, threads=4, decisions=(), patch=None,
               loc_final=40.0, fault=False):
    d = root / bundle / name
    (d / "record").mkdir(parents=True)
    n = int(duration * 1000) + 1
    t = np.arange(n) * 1e-3
    cr = np.where(t < 30.0, 50000.0, 0.0)
    cr[(t > 40.05) & (t < 40.07)] = 4000.0                     # inside the C-11 LOC period (40.0 - 0.1, 40.0]? no
    cr[(t > 39.95) & (t <= 39.96)] = 3500.0
    cr[(t > 44.95) & (t <= 44.97)] = 3900.0                     # inside (45.0 - 0.1, 45.0]: a final LOC at 45 s
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
           "phases": [{"t_s": 0.0, "phase": "check"}] + ([{"t_s": ready, "phase": "ready"}] if ready else [])
           + ([{"t_s": 70.0, "phase": "fault"}] if fault else []),
           "events": [{"t_s": 1.0, "name": "crawler_liftoff_confirmed"}]
           + ([{"t_s": 70.0, "name": "FAULT_STROKE_END:FL"}] if fault else []),
           "p3b": {"weight_N": 3.8e5, "checks": {k: True for k in x16.P3_CHECKS},
                   "P3-2_loc": {"t_loc_s": loc_final, "t_loc_first_s": 40.0, "t_loc_final_s": loc_final,
                                "soil_mode_start_t_s": None,
                                "loc_revokes": [] if loc_final == 40.0 else [{"t_s": 41.0}]},
                   "P3-5_clearance_stroke": {"t_first_ready_s": ready, "rut_clearance_end_m": 0.05},
                   "P3-6_ready": {"t_ready_after_loop_start_s": None if ready is None else ready - 5.0}}}
    (d / "result.json").write_text(json.dumps(res), "utf-8")
    return d


def identity_files(idd, stem, case, head=R2, new_reflog=(), tracked=()):
    """Identity files in the R2 schema (key names as in <OUT>\\_identity, R4 supplement 1-2)."""
    idd.mkdir(parents=True, exist_ok=True)
    fe = {e: None for e in x16.FORBIDDEN_ENV}
    pre = {"case": case, "head": head, "tracked_status": list(tracked), "forbidden_env": fe,
           "dll_sha256": x16.DLL_SHA, "env": {"OMP_WAIT_POLICY": "PASSIVE"}, "reflog_n5": ["a"] * 5}
    post = {"case": case, "head": head, "tracked_status": [], "forbidden_env": fe, "reflog_n5": ["a"] * 5,
            "reflog_new_since_pre": list(new_reflog)}
    (idd / f"{stem}_pre.json").write_text(json.dumps(pre), "utf-8")
    (idd / f"{stem}_post.json").write_text(json.dumps(post), "utf-8")


def done_file(runners, stem, rc=0, logs="logs_A", first=None):
    d = runners / logs
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}_run.done").write_text((first if first is not None else f"exit={rc} wall_s=12.5") + "\nmore\n",
                                        "utf-8")


def c16_setup(tmp_path, **over):
    root = tmp_path / "OUT"
    idd, runners = root / "_identity", root / "_runners"
    for bundle, name, dur, stem, patch in x16.C16_ROWS:
        kw = dict(over.get(name, {}))
        rc = kw.pop("rc", 0)
        row_folder(root, bundle, name, dur, vb=name.endswith("_VB"), patch=patch, **kw)
        identity_files(idd, stem, name)
        done_file(runners, stem, rc=rc)
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
    assert c9["rc_source"].endswith("C9on_run.done")
    assert abs(c9["end_rut_gap_mm"] - 50.0) < 1e-9 and abs(c9["last_sample_t_s"] - 120.0) < 1e-9
    assert c11["final_loc_period"] is None                         # no revoke: first LOC only
    assert c10["G6"] == {"G6-1": True, "G6-2": True, "G6-3": True, "G6-4": True, "G6-5": True, "G6-6": True,
                         "G6-7": True, "READY_le_120s": True}


def test_c16_rc_from_done_file(tmp_path, capsys):
    # R4 supplement 2-4: rc = exit=N of the .done first line; none / two files / no exit= -> 기록 불완전
    root, idd = c16_setup(tmp_path, R4368X_G1_B_top_Fs4_V0_gateoff={"rc": 1})
    out = tmp_path / "c16.json"
    args = ["--out", str(out), "c16", "--out-root", str(root)]
    code, s = run(args, capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["rows"]["R4368X_G1_B_top_Fs4_V0_gateoff"]["items"]["rc"] == 1
    assert rep["C-9_P-18"]["premise"] is False and rep["bundles"]["C-9"]["status"] == "기록 불완전"
    assert rep["bundles"]["C-11"]["status"] == "기록 완료" and code == 1
    done_file(root / "_runners", "C11VB", logs="logs_B")                      # second .done for one row
    done_file(root / "_runners", "C10FLV0", first="wall_s=3.0")              # first line without exit=
    (root / "_runners" / "logs_A" / "C10FRV0_run.done").unlink()             # no .done
    code, s = run(args, capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["bundles"]["C-11"]["status"] == "기록 불완전" and rep["bundles"]["C-10"]["status"] == "기록 불완전"
    whys = " ".join(x["why"] for x in rep["bundles"]["C-10"]["incomplete"] + rep["bundles"]["C-11"]["incomplete"])
    assert "2 C11VB_run.done" in whys and "0 C10FRV0_run.done" in whys and "no exit=" in whys


def test_c16_identity_schema_and_stops(tmp_path, capsys):
    root, idd = c16_setup(tmp_path, R4368X_J2_B_top_Fs0_L2_VB={"threads": 8})
    out = tmp_path / "c16.json"
    args = ["--out", str(out), "c16", "--out-root", str(root)]
    code, s = run(args, capsys)
    assert code == 2 and "S-4" in s["stop_codes"]
    identity_files(idd, "C9on", "R4368X_G1_B_top_Fs4_V0_gateon", head="b" * 40)
    code, s = run(args, capsys)
    assert "S-12" in s["stop_codes"]
    root2, idd2 = c16_setup(tmp_path / "t2")
    identity_files(idd2, "C11V0", "R4368X_J2_B_top_Fs0_L2_V0", new_reflog=["x"])
    code, s = run(["--out", str(out), "c16", "--out-root", str(root2)], capsys)
    assert code == 2 and "S-12" in s["stop_codes"]
    identity_files(idd2, "C11V0", "R4368X_J2_B_top_Fs0_L2_V0", tracked=[" M a.py"])
    code, s = run(["--out", str(out), "c16", "--out-root", str(root2)], capsys)
    assert "S-12" in s["stop_codes"]
    identity_files(idd2, "C11V0", "wrong_case")
    code, s = run(["--out", str(out), "c16", "--out-root", str(root2)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 1 and rep["bundles"]["C-11"]["status"] == "기록 불완전"
    (idd2 / "C11VB_post.json").unlink()
    code, s = run(["--out", str(out), "c16", "--out-root", str(root2)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert any("identity file post missing" in x["why"] for x in rep["bundles"]["C-11"]["incomplete"])


def test_c16_g6_from_p3b_without_ready_and_fault(tmp_path):
    d = row_folder(tmp_path, "C-10", "r", 160.0, ready=None)
    g6, _ = x16.g6_from_p3b(json.loads((d / "result.json").read_text("utf-8")))
    assert g6["G6-4"] == g6["G6-5"] == "해당 없음(READY 없음)" and g6["G6-6"] == "미달" and g6["READY_le_120s"] == "미달"
    d = row_folder(tmp_path, "C-10", "f", 160.0, fault=True)
    res = json.loads((d / "result.json").read_text("utf-8"))
    g6, src = x16.g6_from_p3b(res)
    assert g6["G6-6"] is False and src["fault_events"] == ["FAULT_STROKE_END:FL"]
    res["p3b"]["P3-6_ready"]["t_ready_after_loop_start_s"] = 120.0 + 2e-9
    assert x16.g6_from_p3b(res)[0]["READY_le_120s"] is False
    res["p3b"]["checks"]["P3-1_recontact_pass"] = False
    assert x16.g6_from_p3b(res)[0]["G6-1"] is False


def test_c11_final_loc_with_revoke(tmp_path, capsys):
    root, idd = c16_setup(tmp_path, R4368X_J2_B_top_Fs0_L2_V0={"loc_final": 45.0})
    out = tmp_path / "c16.json"
    run(["--out", str(out), "c16", "--out-root", str(root)], capsys)
    c11 = json.loads(out.read_text("utf-8"))["rows"]["R4368X_J2_B_top_Fs0_L2_V0"]["items"]
    assert c11["loc_period_crawler_max_N"] == 3500.0 and c11["loc_revokes"] == 1   # first LOC (40 s)
    fin = c11["final_loc_period"]
    assert fin["t_loc_s"] == 45.0 and fin["crawler_max_N"] == 3900.0 and fin["above_0p01W"] is True


# ------------------------------------------------------------------ RD-13 items, HEAD, seals
def test_d1_wrapper_head_check(tmp_path, capsys):
    # B-1 / audit A-2: p2_d1.py is outside the R4 edit list; the d1 sub-command checks HEAD first
    h1 = tmp_path / "h1.jsonl"
    h1.write_text("", "utf-8")
    code = x16.main(["--repo", str(REPO), "d1", "--expect-head", "5" * 40, "--", "--h1", str(h1),
                     "--out", str(tmp_path / "d1.json")])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 2 and json.loads(lines[-1])["stop_codes"] == ["S-12"] and not (tmp_path / "d1.json").exists()
    code = x16.main(["--repo", str(REPO), "d1", "--expect-head", FAKE_M4, "--", "--h1", str(h1),
                     "--out", str(tmp_path / "d1.json")])
    lines = capsys.readouterr().out.strip().splitlines()
    first, last = json.loads(lines[0]), json.loads(lines[-1])
    assert first["head_check"]["ok"] and first["p2_d1_argv"][:2] == ["--repo", str(REPO)]
    assert last.get("tool") == "p2_d1.py" and code == last.get("exit")


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
