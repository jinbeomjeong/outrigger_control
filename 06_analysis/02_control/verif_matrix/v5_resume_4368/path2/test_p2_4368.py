"""Self-tests of p2_4368.py on synthetic inputs only (no 436.8 result is read or produced)."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p2_4368", HERE / "p2_4368.py")
p2 = importlib.util.module_from_spec(spec)
sys.modules["p2_4368"] = p2
spec.loader.exec_module(p2)
REPO = HERE.parents[4]


def run_main(argv, capsys):
    argv = list(argv)
    if "chrono" in argv and "--rows-manifest" not in argv and "--batch" in argv:
        # synthetic batches carry their own rows manifest (rev10 R10-1: manifest = judging input)
        man = Path(argv[argv.index("--batch") + 1]).parent / "rows_manifest.json"
        if man.is_file():
            argv += ["--rows-manifest", str(man)]
    if "chrono" in argv and "--git-at-start" not in argv and "--batch" in argv:
        # rev11 R11-4: synthetic rows are compared with the head their batch.json records
        bj = Path(argv[argv.index("--batch") + 1]) / "batch.json"
        if bj.is_file():
            cases = json.loads(bj.read_text("utf-8")).get("cases") or [{}]
            head = p2.dig(cases[0], "code_at_launch.git.head", None)
            if isinstance(head, str):
                argv += ["--git-at-start", head]
    code = p2.main(["--repo", str(REPO)] + argv)
    last = capsys.readouterr().out.strip().splitlines()[-1]
    return code, json.loads(last)


# ------------------------------------------------------------------ basic numbers
def test_thresholds_and_k10():
    assert p2.t_lt(p2.F_MIN_N - 2e-9, p2.F_MIN_N)
    assert not p2.t_lt(p2.F_MIN_N - 0.5e-9, p2.F_MIN_N)
    assert p2.t_gt(1.0 + 2e-9, 1.0) and not p2.t_gt(1.0 + 0.5e-9, 1.0)
    assert p2.t_absle(0.97, 0.95, 0.02) and not p2.t_absle(0.9701, 0.95, 0.02)
    assert p2.same_value(9414.589, 9414.589 + 5e-6) and not p2.same_value(9414.589, 9414.6)
    assert p2.same_value(True, True) and not p2.same_value(True, False)


def test_rc_formula():
    # P5r4 A1 recorded attitude (key-structure check only): |2.362|/4.4 + |1.7268|/3.2
    rc = p2.resolve_rc([2.3620181222471603, 1.726765995745734])
    assert abs(rc - 1.07643667418126) < 1e-12
    assert p2.resolve_rc(None) is None and p2.resolve_rc([1.0]) is None


def test_parse_c2event():
    assert p2.parse_c2event("C2Event(t_s=7.29, name='INFO_PRESSURE_ZERO_CALIBRATED:FL')") == (
        7.29, "INFO_PRESSURE_ZERO_CALIBRATED:FL")
    assert p2.parse_c2event("C2Event(t_s=1.0, name=\"a'b\")") == (1.0, "a'b")
    assert p2.parse_c2event("garbage") is None


def test_job_key_ignores_mask_and_t4h():
    a = {"d1": {"key": "x"}, "setting": "VB", "mask": 3, "t4h_dir": "p"}
    b = {"setting": "VB", "d1": {"key": "x"}}
    assert p2.job_key(a) == p2.job_key(b)
    assert p2.line_key({"key": "k", "controller": "ABL"}) == "k|ABL"


# ------------------------------------------------------------------ family
@pytest.mark.parametrize("s,want", [
    (["D1|H-R-0|rigid|T|flat|K1"], "rigid"),
    (["D1|H-R-A|rigid+J1@FR|T|diag-op|K1"], "patch"),
    (["D1|H-S-C|J1|T|flat|K1|c-mid@FL"], "patch"),
    (["H1|J2|B|top|flat"], "uniform"),
    (["cand=current#L2|s0|g6|52|ref|J1|top|Fs0"], "uniform"),
    (["cand=current#L3|s0|g6|5|g6|G1+J1@FR|top|Fs4"], "patch"),
    (["screen|bottom|0.0|level|FL"], "unresolved"),
])
def test_family_tokens(s, want):
    assert p2.family_from_tokens(s) == want


def test_family_d1_fields():
    assert p2.family_d1({"d1": {"base": "rigid", "patch_leg": None, "sink": None}}) == "rigid"
    assert p2.family_d1({"d1": {"base": "J1", "patch_leg": None, "sink": None}}) == "uniform"
    assert p2.family_d1({"d1": {"base": "J1", "patch_leg": None, "sink": "c-mid@FL"}}) == "patch"
    assert p2.family_d1({"d1": {"base": "rigid", "patch_leg": "FR", "patch_soil": "J1"}}) == "patch"


# ------------------------------------------------------------------ K1 classification (7.2)
def dec(wb=False, due=False, applied=False):
    return {"t_loc_s": 30.0, "t_P_s": 29.0, "t_S_s": 28.0, "n_P": 290, "n_S": 280, "dP": 10,
            "r4_due_without_gate": due, "would_block": wb, "applied": applied}


def og(*ds):
    return {"enabled": True, "decisions": list(ds)}


@pytest.mark.parametrize("las,gate,sk,fam,cls,stops", [
    ({"settings": {}}, og(dec()), 0, "uniform", "unchanged", []),
    ({"settings": {}, "start_s": 31.2}, og(dec()), 0, "uniform", "las", []),
    ({"settings": {}}, og(dec(True, True)), 1, "patch", "k1_block", []),
    ({"settings": {}}, og(dec(True, True)), 1, "uniform", "k1_block", ["S-6"]),
    ({"settings": {}}, og(dec(True, True)), 1, "unresolved", "k1_block", ["S-6"]),
    ({"settings": {}, "start_s": 3.0}, og(dec(True, True)), 1, "rigid", "both", []),
    ({"settings": {}}, og(dec(True, True)), 0, "patch", "k1_block", ["S-5"]),
    ({"settings": {}}, og(dec(True, True, applied=True)), 1, "patch", "k1_block", ["S-5"]),
    ({"settings": {}}, {"enabled": False, "decisions": []}, 0, "rigid", "unchanged", ["S-3"]),
])
def test_classify(las, gate, sk, fam, cls, stops):
    f = p2.Findings()
    r = p2.classify_k1(las, gate, sk, fam, "w", f)
    assert r["class"] == cls
    assert sorted({s["code"] for s in f.stops}) == stops


def test_classify_missing_is_undecidable():
    f = p2.Findings()
    r = p2.classify_k1({"settings": {}}, {"enabled": True}, 0, "rigid", "w", f)
    assert r["class"] is None and f.status() == "undecidable"
    f = p2.Findings()
    p2.classify_k1(p2.MISSING, og(dec()), 0, "rigid", "w", f)
    assert f.status() == "undecidable"


def test_classify_off_arm_las_none():
    f = p2.Findings()
    r = p2.classify_k1(p2.MISSING, og(dec()), 0, "patch", "w", f, las_absent_ok=True)
    assert r["class"] == "las_none_unchanged" and f.status() == "pass"
    f = p2.Findings()
    r = p2.classify_k1({"settings": {"enable": False}}, og(dec(True, True)), 1, "patch", "w", f, las_absent_ok=True)
    assert r["class"] == "las_none_k1_block" and f.status() == "pass"


def test_would_block_without_due_record_conflict():
    # rev2 R2-1: line undecidable, bundle S-5
    f = p2.Findings()
    r = p2.classify_k1({"settings": {}}, og(dec(True, False)), 0, "rigid", "w", f)
    assert r["class"] == "record_conflict" and f.undecidable and {s["code"] for s in f.stops} == {"S-5"}
    f = p2.Findings()
    p2.classify_k1({"settings": {}}, og(dec(False, False, applied=True)), 0, "rigid", "w", f)
    assert {s["code"] for s in f.stops} == {"S-5"}


def test_grid_family_r2_7():
    meta = {"spec": p2.GRID_SPEC_PRESCRIBED}
    assert p2.family_grid({"event": "G4"}, meta) == "patch"
    assert p2.family_grid({"event": "XX"}, meta) == "unresolved"
    assert p2.family_grid({"event": "FS24"}, {"spec": "other"}) == "unresolved"


def test_speed_ratios_r2_4(tmp_path):
    t = np.round(np.arange(8.0, 36.0005, 0.001), 6)
    vmax = 0.0209243016
    cols = ["t"] + [f"u_{l}" for l in ("FL", "FR", "RL", "RR")] + [f"v_{l}" for l in ("FL", "FR", "RL", "RR")]
    u = np.where(t > 8.0, vmax, 0.0)
    rows = np.column_stack([t] + [u] * 4 + [0.9 * u] * 4)
    np.savez(tmp_path / "flow_series.npz", rows=rows, columns=np.array(cols))
    sm = np.column_stack([0.9 * vmax * (t - 8.0)] * 4)
    np.savez(tmp_path / "series.npz", t_s=t, s_motor_m=sm)
    rvu = p2.speed_ratio_vu(tmp_path, vmax)
    assert all(abs(v - 0.9) < 1e-12 for v in rvu["per_leg"].values())
    rv = p2.speed_ratio_v(tmp_path, vmax)
    assert all(abs(v - 0.9) < 1e-9 for v in rv["per_leg"].values()) and rv["window_s"] == [10.0, 20.0]
    assert p2.speed_ratio_vu(tmp_path / "none", vmax) is None


def test_yaml_vmax():
    assert abs(p2.yaml_vmax(REPO) - 0.020924) < 1e-5


# ------------------------------------------------------------------ 4.2 settings
def test_las_settings():
    f = p2.Findings()
    assert p2.check_las_settings(dict(p2.LAS_PRESET, min_active_periods=0, end_ramp_periods=0), "w", f)
    assert f.status() == "pass"
    f = p2.Findings()
    s = dict(p2.LAS_PRESET, light_leg_fraction_of_F_min=4.5)
    assert not p2.check_las_settings(s, "w", f) and f.stops[0]["code"] == "S-3"
    f = p2.Findings()
    assert not p2.check_las_settings(dict(p2.LAS_PRESET, end_ramp_periods=4), "w", f)
    f = p2.Findings()
    assert p2.check_las_settings(dict(p2.LAS_PRESET, require_soil_response=False), "w", f, abl=True)
    f = p2.Findings()
    assert not p2.check_las_settings(None, "w", f)


# ------------------------------------------------------------------ harness end to end
def rk_block(las_start=None, decisions=(), skipped=0, applicable=True):
    b = {"applicable": applicable}
    if not applicable:
        b["reason"] = "no C2"
        return b
    las = {"settings": dict(p2.LAS_PRESET)}
    if las_start is not None:
        las.update(start_s=las_start, end_s=las_start + 1.0, end_reason="sum_off")
    b.update(k1_order_gate_request="preset", k1_order_gate_effective=True, liftoff_approach_slow=las,
             slope_clearance_margin={"settings": {"flat_soil_margin_order_gate": True, "flat_soil_margin_m": 0.03},
                                     "order_gate": {"enabled": True, "decisions": list(decisions)}},
             event_counts={"flat_soil_margin_applied": 0, "flat_soil_margin_skipped_order": skipped,
                           "soil_mode_start": 0})
    return b


def d1_line(i, group, base, tag, **kw):
    key = f"D1|{group}|{base}|T|flat|K1|{i}"
    return {"job": {"d1": {"key": key, "group": group, "base": base, "patch_leg": None, "sink": None},
                    "setting": "V0", "eps": 0.0, "mask": i},
            "controller_tag": tag, "commands_sha256": f"{i:064x}", "resume_k1": rk_block(**kw)}


def write_jsonl(path, lines):
    path.write_text("".join(json.dumps(x) + "\n" for x in lines), "utf-8")


def test_harness_pass_and_tag_stop(tmp_path, capsys):
    lines = [d1_line(i, "H-R-0", "rigid", p2.TAG_V0) for i in range(3)]
    lines.append(d1_line(9, "H-S-A", "G1", p2.TAG_V0, decisions=[dec(True, True)], skipped=1))
    lines[-1]["job"]["d1"]["patch_leg"] = "FL"
    f = tmp_path / "h.jsonl"
    write_jsonl(f, lines)
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"files": [{"bundle": "TEST", "path": str(f), "format": "run_v5_jsonl",
                                          "kind": "V0", "expect_lines": 4}]}), "utf-8")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "harness", "--manifest", str(man)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["bundles"]["TEST"]
    assert rep["bundles"]["TEST"]["classes"] == {"unchanged": 3, "k1_block": 1}
    assert s["out_sha256"] == p2.sha256_file(out)
    lines[0]["controller_tag"] = "final_C4G2_LAS"
    write_jsonl(f, lines)
    code, s = run_main(["--out", str(out), "harness", "--manifest", str(man)], capsys)
    assert code == 2 and "S-2" in s["stop_codes"]


def test_harness_uniform_block_and_stored_hash(tmp_path, capsys):
    lines = [d1_line(1, "H-S-0", "J1", p2.TAG_V0, decisions=[dec(True, True)], skipped=1),
             d1_line(2, "H-R-0", "rigid", p2.TAG_V0)]
    stored = copy.deepcopy(lines)
    stored[1]["commands_sha256"] = "f" * 64
    f, sf = tmp_path / "h.jsonl", tmp_path / "s.jsonl"
    write_jsonl(f, lines)
    write_jsonl(sf, stored)
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"files": [{"bundle": "T2", "path": str(f), "format": "run_v5_jsonl",
                                          "kind": "V0", "stored": str(sf)}]}), "utf-8")
    code, s = run_main(["harness", "--manifest", str(man)], capsys)
    assert code == 2 and set(s["stop_codes"]) == {"S-5", "S-6"}


def test_harness_ind_not_applicable_and_forbidden_token(tmp_path, capsys):
    rec = {"records": [{"id": "H1|G1|B|top|flat", "controller": "IND",
                        "v5": {"controller_tag": "IND", "resume_k1": rk_block(applicable=False)}},
                       {"id": "H1|J1|B|top|flat|K1on", "controller": "IND",
                        "v5": {"controller_tag": "IND", "resume_k1": rk_block(applicable=False)}}]}
    f = tmp_path / "u6.json"
    f.write_text(json.dumps(rec), "utf-8")
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"files": [{"bundle": "T3", "path": str(f), "format": "u3_json", "kind": "IND"}]}), "utf-8")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "harness", "--manifest", str(man)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["bundles"]["T3"]["classes"] == {"n/a": 2}
    assert code == 2 and s["stop_codes"] == ["S-3"]


def test_harness_line_count_s15(tmp_path, capsys):
    f = tmp_path / "h.jsonl"
    write_jsonl(f, [d1_line(1, "H-R-0", "rigid", p2.TAG_V0)])
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"files": [{"bundle": "H-5", "path": str(f), "format": "run_v5_jsonl", "kind": "V0"}]}),
                   "utf-8")
    code, s = run_main(["harness", "--manifest", str(man)], capsys)
    assert code == 2 and "S-15" in s["stop_codes"]


# ------------------------------------------------------------------ 1 ms recount
def synth_law_locked(n):
    """rev8 R8-3a: [N, 4] int8, -1 unarmed then 1 locked with one moving tail (0) on RL."""
    ll = np.full((n, 4), 1, dtype=np.int8)
    ll[:500] = -1
    ll[3000:3200, 2] = 0
    return ll


def synth_step(path, dip_N=9000.0, t_dep=2.0, law_locked="ok"):
    t = np.round(np.arange(0.0, 12.0, 0.001), 6)
    W = 380000.0
    cr = np.where(t < t_dep, 0.3 * W, 0.0)
    F = np.full((t.size, 4), 95000.0)
    dip = (t > t_dep + 0.5) & (t < t_dep + 0.6)       # 99 or 100 samples below F_min
    F[dip, 2] = dip_N
    F[t < t_dep, 2] = 5000.0                          # before departure: ignored
    extra = {}
    if law_locked == "ok":
        extra["law_locked"] = synth_law_locked(t.size)
    elif law_locked == "int64":
        extra["law_locked"] = synth_law_locked(t.size).astype(np.int64)
    elif law_locked == "values":
        a = synth_law_locked(t.size)
        a[10, 0] = 2
        extra["law_locked"] = a
    elif law_locked == "shape":
        extra["law_locked"] = synth_law_locked(t.size)[:, :3].copy()
    elif law_locked == "rows":
        extra["law_locked"] = synth_law_locked(t.size - 1)
    np.savez(path, t_s=t, F_cyl_N=F, scm_crawler_normal_N=cr, **extra)
    return W


def test_series_recount(tmp_path):
    p = tmp_path / "step_series.npz"
    W = synth_step(p)
    r = p2.series_force_recount(p, W)
    assert abs(r["t_departure_s"] - 2.0) < 1e-9
    rl = r["legs"][2]
    assert rl["F_min_after_N"] == 9000.0
    n = int(np.count_nonzero((np.round(np.arange(0.0, 12.0, 0.001), 6) > 2.5) & (np.round(np.arange(0.0, 12.0, 0.001), 6) < 2.6)))
    assert abs(rl["t_below_F_min_s"] - n * 0.001) < 1e-12
    assert abs(rl["t_below_F_min_plus_2kN_s"] - n * 0.001) < 1e-12
    assert r["legs"][0]["t_below_F_min_s"] == 0.0
    assert r["max_t_below_F_min_s"] == rl["t_below_F_min_s"] and r["window_truncated_at_run_end"] is False


def test_c2_fixed_rows_r2_8(tmp_path, capsys):
    bd = tmp_path / "batch_V5-RESUME-K1-C2_20990101_000000"
    bd.mkdir()
    rows = [{"case": f"x{i}", "argv": [], "rc": 0, "criteria_id": "C-2", "d1_id": d}
            for i, d in enumerate(["C2-03", "C2-07", "S-01"])]
    (bd / "batch.json").write_text(json.dumps({"cases": rows}), "utf-8")
    code, s = run_main(["chrono", "--batch", str(bd), "--check-counts"], capsys)
    assert "S-15" in s["stop_codes"]


def test_departure_needs_hold():
    t = np.round(np.arange(0.0, 1.0, 0.001), 6)
    cr = np.ones_like(t) * 100.0
    cr[(t >= 0.2) & (t < 0.25)] = 0.0       # 50 ms: too short
    cr[t >= 0.5] = 0.0
    i = p2.departure_index(t, cr, 1000.0)
    assert abs(t[i] - 0.5) < 1e-9


# ------------------------------------------------------------------ Chrono rows (synthetic batch)
def scm_result(tag, rc_att, las_start=None, decisions=(), events=(), p3=None):
    p3 = tag in (p2.TAG_VB, p2.TAG_C4OFF_VB) if p3 is None else p3
    return {"args": {"soil": "J1", "rigid_base": "FR", "floor_roll": 2.1434, "floor_pitch": 1.3784,
                     "extend_start_tracked": True, "duration": 160.0},
            "num_threads_chrono": 4,
            "placement": {"omp_wait_policy": "PASSIVE", "power_throttling_off_ok": True},
            "hull_hook": {"requested": "fast", "mode": "fast", "fallback_reason": None, "env": {}},
            "v5_hydraulics": {"controller_tag": tag,
                              "hydraulic_options": {"extend_start_tracked": True} if p3 else {}},
            "c2_setup": {"k1_order_gate": "preset", "k1_order_gate_effective": True,
                         "expect_controller": {"name": tag, "ok": True}},
            "controller_meta": {"liftoff_approach_slow": {"settings": dict(p2.LAS_PRESET, min_active_periods=0,
                                                                           end_ramp_periods=0),
                                                          "start_s": las_start},
                                **({"two_pressure": {"settings": {"extend_start_rule": "tracked_bound"}}} if p3 else {}),
                                "slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": True},
                                                           "order_gate": {"enabled": True,
                                                                          "decisions": list(decisions)}}},
            "p3b": {"weight_N": 380000.0, "departure": {"t_departure_s": 2.0},
                    "P3-3_leg_force": {"F_min_after_N": [95000.0, 95000.0, 9000.0, 95000.0]}},
            "p3b_ext": {"start_condition": {"crawler_attitude_deg": rc_att,
                                            "R_c_operating": p2.resolve_rc(rc_att)}},
            "events": list(events)}


def write_batch_json(bd, rows, batch_key=True, manifest=True):
    """batch.json with the full batch name (rev10 R10-1a) and a rows manifest next to the batch folder."""
    name = p2.bundle_of(bd)
    b = {"mixed_hull_mode": False, "cases": rows}
    if batch_key:
        b["batch"] = name
    (bd / "batch.json").write_text(json.dumps(b), "utf-8")
    if manifest:
        mp = bd.parent / "rows_manifest.json"
        m = json.loads(mp.read_text("utf-8")) if mp.is_file() else {"batches": {}}
        m["batches"].setdefault(name, {"rows": []})["rows"] += [{"case": r["case"], "v5_setting": r.get("v5_setting")}
                                                             for r in rows]
        mp.write_text(json.dumps(m), "utf-8")


def make_batch(tmp_path, res, cid="C-8a", argv_extra=(), name="batch_V5-RESUME-K1-OC5_20990101_000000",
               law_locked="ok", est_argv=None, setting="VB"):
    bd = tmp_path / name
    case = "OC5_mixed_rigid_J1FR_Kc3_VB_top"
    (bd / case).mkdir(parents=True)
    (bd / case / "result.json").write_text(json.dumps(res), "utf-8")
    if law_locked != "nofile":
        synth_step(bd / case / "step_series.npz", law_locked=law_locked)
    if est_argv is None:
        est_argv = bool(p2.dig(res, "v5_hydraulics.hydraulic_options.extend_start_tracked", False))
    argv = ["python.exe", "run_S9.py", "level", "--threads", "4", "--floor-roll", "2.1434", "--floor-pitch", "1.3784",
            "--expect-controller", res["c2_setup"]["expect_controller"]["name"], "--start-limit", "record_only",
            *(["--extend-start-tracked"] if est_argv else []), *argv_extra]
    row = {"case": case, "argv": argv, "rc": 0, "pool": "pcore", "planned_pool": "pcore", "criteria_id": cid,
           "v5_setting": setting, "start_env": {"OMP_WAIT_POLICY": "PASSIVE"}, "hull_hook_env": None,
           "hull_hook_requested": "fast", "hull_hook_effective": {"mode": "fast", "fallback_reason": None},
           "code_at_launch": {"git": {"head": "a" * 40, "dirty": []}}}
    write_batch_json(bd, [row])
    return bd


def test_chrono_oc5_stop_s9(tmp_path, capsys):
    bd = make_batch(tmp_path, scm_result(p2.TAG_VB, [2.0, 1.5]))    # R_c = 0.92 inside
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    row = rep["rows"][0]
    assert row["oc5"]["m_path2_N"] == 9000.0 and row["oc5"]["m_leg"] == "RL"
    assert row["oc5"]["k_from_argv"] == 0.9179 and row["oc5"]["floor_consistent_with_k"]
    assert code == 2 and s["stop_codes"] == ["S-9"]


def test_chrono_oc5_outside_s10_and_tag(tmp_path, capsys):
    bd = make_batch(tmp_path, scm_result(p2.TAG_VB, [2.4, 1.8]))    # R_c > 1
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-10"]
    bd2 = make_batch(tmp_path / "b", scm_result(p2.TAG_V0, [2.0, 1.5]))
    code, s = run_main(["chrono", "--batch", str(bd2)], capsys)
    assert "S-2" in s["stop_codes"]


def test_chrono_forbidden_and_identity(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.0, 1.5])
    res["num_threads_chrono"] = 2
    bd = make_batch(tmp_path, res, cid="C-5", argv_extra=("--las-candidate", "P0"))
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and {"S-3", "S-4"} <= set(s["stop_codes"])


def test_chrono_c4_off_arm(tmp_path, capsys):
    res = scm_result(p2.TAG_C4OFF_VB, [2.4, 1.8])
    res["c2_setup"]["k1_order_gate"] = "on"
    res["c2_setup"]["las_off"] = True
    res["controller_meta"]["liftoff_approach_slow"] = {"settings": {"enable": False}}
    bd = make_batch(tmp_path, res, cid="C-4", argv_extra=("--las-off", "--k1-order-gate", "on"))
    out = tmp_path / "o.json"
    b = json.loads((bd / "batch.json").read_text("utf-8"))
    b["cases"][0]["r4368"] = {"arm": "off", "criteria_id": "C-4"}
    (bd / "batch.json").write_text(json.dumps(b), "utf-8")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    row = rep["rows"][0]
    assert row["k1"]["class"] == "las_none_unchanged"
    assert row["outside_start_condition"] is True and rep["outside_start_condition_rows"] == [row["case"]]
    assert code == 0, rep["stops"]


def gs_full_result(tag=None):
    """An SCM level result.json with every path-2 G-S key of an on-arm row (synthetic)."""
    res = scm_result(tag or p2.TAG_VB, [2.0, 1.5], las_start=None)
    res["p3b"]["P3-3_leg_force"]["F_min_transient_N"] = [90000.0] * 4
    res["controller_meta"]["liftoff_approach_slow"].update(end_s=None, end_reason=None, active_periods=0,
                                                          ramp={"periods_applied": 0})
    return res


def test_rev7_r74_conditional_absence_table():
    assert len(p2.GS_CONDITIONAL_R74) == 9
    keys = tuple(p2.GS_CONDITIONAL_R74)
    on, off = {"r4368": {"arm": "on"}}, {"r4368": {"arm": "off"}}
    res = gs_full_result()
    res["c2_setup"].pop("las_off", None)
    pres, bad = p2.gs_presence(on, res, keys)
    assert bad == [] and pres["c2_setup.las_off"] == "conditional_absent"
    assert pres["controller_meta.liftoff_approach_slow.start_s"] == "present"     # null value = key present
    # F_min keys: absence allowed only when p3b.departure.departed is False
    r2 = copy.deepcopy(res)
    del r2["p3b"]["P3-3_leg_force"]["F_min_after_N"]
    pres, bad = p2.gs_presence(on, r2, keys)
    assert pres["p3b.P3-3_leg_force.F_min_after_N"] == "result_missing"          # departed key absent
    r2["p3b"]["departure"]["departed"] = True
    assert p2.gs_presence(on, r2, keys)[0]["p3b.P3-3_leg_force.F_min_after_N"] == "result_missing"
    r2["p3b"]["departure"]["departed"] = False
    assert p2.gs_presence(on, r2, keys)[0]["p3b.P3-3_leg_force.F_min_after_N"] == "conditional_absent"
    # LAS-b keys: required on the on arm, absence allowed on the off arm; las_off the other way round
    r3 = copy.deepcopy(res)
    r3["controller_meta"]["liftoff_approach_slow"] = {"settings": {"enable": False}}
    pres, bad = p2.gs_presence(on, r3, keys)
    assert set(bad) == set(p2.LAS_R74)
    pres, bad = p2.gs_presence(off, r3, keys)
    assert bad == ["c2_setup.las_off"] and all(pres[k] == "conditional_absent" for k in p2.LAS_R74)
    r3["c2_setup"]["las_off"] = True
    assert p2.gs_presence(off, r3, keys)[1] == []
    # a row without r4368.arm counts as the on arm (arm != "off")
    assert set(p2.gs_presence({}, r3, keys)[1]) == set(p2.LAS_R74)
    # t_min_after_s is no longer a path-2 G-S key (not in the R7-4 table)
    assert "p3b.P3-3_leg_force.t_min_after_s" not in p2.GS_KEYS_SCM


def test_rev7_r74_gs_mode_end_to_end(tmp_path, capsys):
    res = gs_full_result()
    bd = make_batch(tmp_path, res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    assert rep["rows"][0]["gs_conditional_absent"] == ["c2_setup.las_off"]
    res["controller_meta"]["liftoff_approach_slow"].pop("ramp")
    bd = make_batch(tmp_path / "b", res, name="batch_V5-RESUME-K1-GS_20990101_000001")
    code, s = run_main(["chrono", "--batch", str(bd), "--gs"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-11"]


def test_rev7_r76_mask_recorded(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])
    res["placement"].update(affinity_mask_process="0xFF", affinity_mask_ok=False)
    bd = make_batch(tmp_path, res)
    out = tmp_path / "o.json"
    run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    ident = rep["rows"][0]["identity"]
    assert ident["affinity_mask_process"] == "0xFF" and ident["affinity_mask_ok"] is False
    assert any("affinity_mask_ok false" in r["what"] for r in rep["records"])


# ------------------------------------------------------------------ O-C5 k procedure
def probe(tmp_path, n, k, att, dur=7.0):
    p = tmp_path / f"probe{n}.json"
    p.write_text(json.dumps({"args": {"floor_roll": round(k * 2.3351, 4), "floor_pitch": round(k * 1.5017, 4),
                                      "duration": dur},
                             "p3b_ext": {"start_condition": ({"crawler_attitude_deg": att} if att else {})}}), "utf-8")
    return str(p)


def att_for(rc):
    return [rc * 4.4 / 2, rc * 3.2 / 2]      # |phi|/4.4 + |theta|/3.2 = rc


def test_oc5k_first_probe(tmp_path, capsys):
    out = tmp_path / "o.json"
    code, _ = run_main(["--out", str(out), "oc5k", "--row", "C-8a", "--probe", probe(tmp_path, 1, 0.9179, att_for(0.955))],
                       capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["k"] == 0.9179 and rep["floor_deg"] == [round(0.9179 * 2.3351, 4), round(0.9179 * 1.5017, 4)]


def test_oc5k_second_and_secant(tmp_path, capsys):
    k1 = 0.8829
    r1 = 1.02
    k2 = round(k1 * 0.95 / r1, 4)
    r2 = 0.99
    k3 = round(k1 + (0.95 - r1) * (k2 - k1) / (r2 - r1), 4)
    files = [probe(tmp_path, 1, k1, att_for(r1)), probe(tmp_path, 2, k2, att_for(r2)),
             probe(tmp_path, 3, k3, att_for(0.951))]
    out = tmp_path / "o.json"
    code, _ = run_main(["--out", str(out), "oc5k", "--row", "C-8b"] + sum([["--probe", f] for f in files], []), capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["k"] == k3 and rep["n_probes_counted"] == 3


def test_oc5k_doubled_rerun_and_stop(tmp_path, capsys):
    files = [probe(tmp_path, 1, 0.9179, None), probe(tmp_path, 2, 0.9179, att_for(0.95), dur=14.0)]
    out = tmp_path / "o.json"
    code, _ = run_main(["--out", str(out), "oc5k", "--row", "C-8a"] + sum([["--probe", f] for f in files], []), capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["n_probes_counted"] == 1 and rep["k"] == 0.9179
    k2 = round(0.9179 * 0.95 / 1.1, 4)
    files = [probe(tmp_path, 3, 0.9179, att_for(1.1)), probe(tmp_path, 4, k2, att_for(1.1))]
    code, s = run_main(["oc5k", "--row", "C-8a"] + sum([["--probe", f] for f in files], []), capsys)
    assert code == 2 and s["stop_codes"] == ["S-10"]       # R_c(k2) = R_c(k1)


# ------------------------------------------------------------------ J_P
def test_jp(tmp_path, capsys):
    s8 = tmp_path / "07_results" / "S8"
    rows = []
    shadow = []
    for i in range(12):
        run = s8 / f"v5jp_VB_case{i}_20990101" / f"case{i}"
        run.mkdir(parents=True)
        (run / "result.json").write_text("{}", "utf-8")
        ev = ["C2Event(t_s=1.0, name='crawler_liftoff_confirmed')"]
        if i == 5:
            ev.append("C2Event(t_s=2.0, name='INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order')")   # not the R4c30 name
        (run / "controller_events.json").write_text(json.dumps(ev), "utf-8")
        rows.append({"case": f"case{i}", "s8c_check": {"result_json": str(run / "result.json")}})
        shadow.append({"job": {"chrono_run": f"v5jp_VB_case{i}_20990101/case{i}"}, "status": "silent",
                       "first_fire_t_s": None})
    bd = tmp_path / "batch_V5-JP-VB_x"
    bd.mkdir()
    (bd / "batch.json").write_text(json.dumps({"cases": rows}), "utf-8")
    sh = tmp_path / "shadow.jsonl"
    write_jsonl(sh, shadow)
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "jp", "--shadow", str(sh), "--batch", str(bd)], capsys)
    assert code == 0 and s["decision"].startswith("reuse")
    ev_file = s8 / "v5jp_VB_case3_20990101" / "case3" / "controller_events.json"
    ev_file.write_text(json.dumps(["C2Event(t_s=1.0, name='INFO_LOC_FLAT_SOIL_MARGIN')"]), "utf-8")
    code, s = run_main(["jp", "--shadow", str(sh), "--batch", str(bd)], capsys)
    assert s["decision"].startswith("rerun")


# ------------------------------------------------------------------ K-10 compare
def test_compare(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"x": 1.0, "c": "las", "l": [1, 2]}), "utf-8")
    b.write_text(json.dumps({"x": 1.0 + 1e-12, "c": "las", "l": [1, 2]}), "utf-8")
    code, _ = run_main(["compare", "--a", str(a), "--b", str(b)], capsys)
    assert code == 0
    b.write_text(json.dumps({"x": 1.0 + 1e-6, "c": "las", "l": [1, 2]}), "utf-8")
    code, _ = run_main(["compare", "--a", str(a), "--b", str(b)], capsys)
    assert code == 1


def test_seal_ok(capsys):
    code, s = run_main(["seal"], capsys)
    assert code == 0, s


def test_rev7_seal_listed_and_checked():
    seals = p2.check_seals(REPO, appendix=False)
    assert p2.REV7_REL in seals["rules"] and seals["rules"][p2.REV7_REL]["ok"]
    assert p2.REV7_SHA == "e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502"


# ------------------------------------------------------------------ rev8 (3ecafaaf)
def test_rev8_seal_listed_and_checked():
    seals = p2.check_seals(REPO, appendix=False)
    assert p2.REV8_REL in seals["rules"] and seals["rules"][p2.REV8_REL]["ok"], seals["rules"].get(p2.REV8_REL)
    assert p2.REV8_SHA == "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56"
    item = seals["rules"][p2.REV8_REL]
    assert item["sha256"] == item["seal_file_sha"] == p2.REV8_SHA


def test_rev8_seal_mismatch_stops(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(p2, "REV8_SHA", "0" * 64)
    code, s = run_main(["seal"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-1"]


@pytest.mark.parametrize("variant, problem", [
    ("int64", "dtype"), ("values", "values"), ("shape", "shape"), ("rows", "t_s rows"),
    ("nokey", "law_locked key absent"), ("nofile", "step_series.npz absent")])
def test_rev8_r83a_law_locked_format(tmp_path, variant, problem):
    p = tmp_path / "step_series.npz"
    if variant != "nofile":
        synth_step(p, law_locked=variant)
    r = p2.law_locked_format(p)
    assert not r["ok"] and any(problem in x for x in r["problems"]), r
    assert r["present"] is (variant not in ("nokey", "nofile"))


def test_rev8_r83a_law_locked_ok_and_spacing(tmp_path):
    p = tmp_path / "step_series.npz"
    synth_step(p)
    r = p2.law_locked_format(p)
    assert r["ok"] and r["problems"] == [] and r["shape"] == [12000, 4]
    # -1 counts as locked (revision 6 section 6): only the RL tail gives transitions
    assert r["transitions_per_leg"]["FL"] == {"to_locked": 0, "to_unlocked": 0}
    assert r["transitions_per_leg"]["RL"] == {"to_locked": 1, "to_unlocked": 1}
    t = np.round(np.arange(0.0, 12.0, 0.001), 6)
    t[5000:] += 0.0005                              # one 1.5 ms step: not the 1 ms axis
    np.savez(p, t_s=t, law_locked=synth_law_locked(t.size))
    r = p2.law_locked_format(p)
    assert not r["ok"] and "spacing" in r["problems"][0]


@pytest.mark.parametrize("variant", ["ok", "nokey", "int64"])
def test_rev8_r83_gs_mode(tmp_path, capsys, variant):
    res = gs_full_result()
    bd = make_batch(tmp_path, res, name="batch_V5-RESUME-K1-GS_20990101_000000", law_locked=variant)
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    if variant == "ok":
        assert code == 0, rep["stops"]
        assert rep["R8-3_law_locked_check"] == {"rows": 1, "missing": 0, "problems": 0}
    else:
        assert code == 2 and s["stop_codes"] == ["S-11"]
        assert any("law_locked" in x["why"] for x in rep["stops"])
        assert rep["R8-3_law_locked_check"] == {"rows": 1, "missing": int(variant == "nokey"),
                                                "problems": int(variant == "int64")}


def test_rev8_r83_main_run_c5_undecidable(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])                 # R_c > 1, no O-C5 (C-5 row)
    bd = make_batch(tmp_path, res, cid="C-5", law_locked="nokey")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 1 and s["stop_codes"] == [] and any("J11 not judgeable" in u["why"] for u in rep["undecidable"])
    bd = make_batch(tmp_path / "b", res, cid="C-5")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, (rep["stops"], rep["undecidable"])
    assert rep["rows"][0]["law_locked"]["ok"] and rep["rows"][0]["jp3_scope"]["status"] == "applicable"


def test_rev8_r82_jp3_scope_and_request_records(tmp_path, capsys):
    # V0 row without the extend_start_rule key: J-P3 not applicable, not missing
    res = scm_result(p2.TAG_V0, [2.4, 1.8])
    bd = make_batch(tmp_path, res, cid="C-5", setting="V0")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    assert rep["rows"][0]["jp3_scope"]["status"] == "not_applicable"
    assert rep["R8-2_jp3_scope"] == {"not_applicable": 1}
    # V0 row with --extend-start-tracked in argv -> S-2
    bd = make_batch(tmp_path / "b", res, cid="C-5", setting="V0", est_argv=True)
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-2"]
    # VB row whose v5 record says off -> S-2; v5 block absent -> argv only
    r2 = scm_result(p2.TAG_VB, [2.4, 1.8])
    r2["v5_hydraulics"]["hydraulic_options"] = {}
    bd = make_batch(tmp_path / "c", r2, cid="C-5", est_argv=True)
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-2"]
    r3 = scm_result(p2.TAG_V0, [2.4, 1.8])
    r3["v5_hydraulics"] = {"controller_tag": p2.TAG_V0}          # no hydraulic_options: key absent = off
    bd = make_batch(tmp_path / "d", r3, cid="C-5", setting="V0")
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 0, s
    # ③ row: rule missing = J-P3 not judgeable (recorded), other value = S-2
    r4 = scm_result(p2.TAG_VB, [2.4, 1.8])
    del r4["controller_meta"]["two_pressure"]
    bd = make_batch(tmp_path / "e", r4, cid="C-5")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["rows"][0]["jp3_scope"]["status"] == "applicable_rule_missing"
    assert any("J-P3 not judgeable" in r["what"] for r in rep["records"])
    r4["controller_meta"]["two_pressure"] = {"settings": {"extend_start_rule": "constant"}}
    bd = make_batch(tmp_path / "f", r4, cid="C-5")
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-2"]


def test_rev8_r81b_dotted_controller_settings_key(tmp_path, capsys):
    lines = [d1_line(i, "H-R-0", "rigid", p2.TAG_VB) for i in range(2)]
    for ln in lines:
        ln["controller_settings"] = {"two_pressure.extend_start_rule": "tracked_bound"}
    f = tmp_path / "h.jsonl"
    write_jsonl(f, lines)
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"files": [{"bundle": "TEST", "path": str(f), "format": "run_v5_jsonl",
                                          "kind": "H6"}]}), "utf-8")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "harness", "--manifest", str(man)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep
    assert "extend_start_rule not in line" not in json.dumps(rep["bundles"]["TEST"]["records"])
    lines[0]["controller_settings"] = {"two_pressure.extend_start_rule": "constant"}
    write_jsonl(f, lines)
    code, s = run_main(["harness", "--manifest", str(man)], capsys)
    assert code == 2 and "S-2" in s["stop_codes"]


def test_rev8_r82_scm_row_without_v5_block(tmp_path, capsys):
    """V0 / S6SEED SCM rows carry no v5_hydraulics block: tag = --expect-controller + expect_controller.ok."""
    res = gs_full_result(p2.TAG_V0)
    del res["v5_hydraulics"]
    bd = make_batch(tmp_path, res, cid="C-5", setting="V0", name="batch_V5-RESUME-K1-GS_20990101_000000")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    assert "v5_hydraulics.controller_tag" not in rep["rows"][0]["gs_keys"]
    bd = make_batch(tmp_path / "m", res, cid="C-5", setting="V0")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    row = rep["rows"][0]
    assert row["tag"] == p2.TAG_V0 and row["tag_recorded"] is None and row["jp3_scope"]["v5_hydraulics_block"] is False
    res["c2_setup"]["expect_controller"]["ok"] = False             # the check must still be true
    bd = make_batch(tmp_path / "n", res, cid="C-5", setting="V0")
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-2"]
    r2 = scm_result(p2.TAG_VB, [2.4, 1.8])
    r2["v5_hydraulics"]["controller_tag"] = p2.TAG_V0                # recorded tag differs from argv
    bd = make_batch(tmp_path / "o", r2, cid="C-5")
    code, s = run_main(["chrono", "--batch", str(bd)], capsys)
    assert code == 2 and s["stop_codes"] == ["S-2"]


# ------------------------------------------------------------------ rev9 (4cf7843c)
def test_rev9_seal_listed_and_checked():
    seals = p2.check_seals(REPO, appendix=False)
    assert p2.REV9_REL in seals["rules"] and seals["rules"][p2.REV9_REL]["ok"], seals["rules"].get(p2.REV9_REL)
    assert p2.REV9_SHA == "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d"
    item = seals["rules"][p2.REV9_REL]
    assert item["sha256"] == item["seal_file_sha"] == p2.REV9_SHA


def test_rev9_seal_mismatch_stops(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(p2, "REV9_SHA", "0" * 64)
    code, s = run_main(["seal"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-1"]
    monkeypatch.setattr(p2, "REV9_SEAL_REL", "06_analysis/02_control/verif_matrix/no_such_rev9.sha256")
    monkeypatch.setattr(p2, "REV9_SHA", "4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d")
    code, s = run_main(["seal"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-1"]      # .sha256 record absent = S-1 (R9-8)


def _ll(n=1000, pre=100):
    a = np.ones((n, 4), dtype=np.int8)
    a[:pre] = -1
    return a


@pytest.mark.parametrize("variant, patterns, ok", [
    ("none", ["none"], True), ("pre", ["pre_arming"], True), ("after", ["after_arming"], False),
    ("whole", ["whole_run"], False), ("mismatch", ["leg_mismatch"], False), ("never", ["leg_mismatch"], False),
    ("rearm_via_minus1", ["after_arming"], False), ("after_and_mismatch", ["after_arming", "leg_mismatch"], False)])
def test_rev9_r93_minus1_patterns(tmp_path, variant, patterns, ok):
    a = _ll()
    if variant == "none":
        a[:] = 1
        a[400:450, 1] = 0
    elif variant == "after":
        a[500:510, 3] = -1                     # -1 after the first arming on RR
    elif variant == "whole":
        a[:] = -1
    elif variant == "mismatch":
        a[100:120, 2] = -1                     # RL leaves -1 20 samples later than the others
    elif variant == "never":
        a[:, 0] = -1                           # FL never leaves -1
    elif variant == "rearm_via_minus1":
        a[600:700] = -1                        # four legs back to -1 together: disarm is not a recorded path
    elif variant == "after_and_mismatch":
        a[100:120, 2] = -1
        a[800, 0] = -1
    p = tmp_path / "step_series.npz"
    np.savez(p, t_s=np.round(np.arange(a.shape[0]) * 1e-3, 9), law_locked=a)
    r = p2.law_locked_format(p)
    assert r["minus1_patterns"] == patterns and r["ok"] is ok, r
    if not ok:
        assert r["failed_items"] == ["6_minus1"] and all("R9-3" in x for x in r["problems"])
    if variant == "pre":
        assert r["pre_arming_samples"] == 100
        assert r["transitions_per_leg"]["FL"] == {"to_locked": 0, "to_unlocked": 0}   # -1 counts as locked


def test_rev9_r92_l2b_pads_time_column_and_items(tmp_path):
    a = _ll()
    t = np.round(np.arange(a.shape[0]) * 1e-3, 9)
    p = tmp_path / "pads.npz"
    np.savez(p, t=t, law_locked=a)
    r = p2.law_locked_format(p, "t")
    assert r["ok"] and r["file"] == "pads.npz" and r["max_abs_dt_error_s"] < 1e-12
    np.savez(p, t_s=t, law_locked=a)                       # SCM time key in an L2b file: item 1
    r = p2.law_locked_format(p, "t")
    assert not r["ok"] and r["failed_items"] == ["1_time_column"]
    t2 = t.copy()
    t2[500:] += 2e-6                                       # one step 1.002 ms: outside 1 ms +- 1e-6 s
    np.savez(p, t=t2, law_locked=a.astype(np.int16))
    r = p2.law_locked_format(p, "t")
    assert set(r["failed_items"]) == {"3_dtype", "5_spacing"}
    t3 = t.copy()
    t3[500:] += 0.9e-6                                     # inside the 1e-6 s procedure value
    np.savez(p, t=t3, law_locked=a)
    assert p2.law_locked_format(p, "t")["ok"]
    assert p2.LAW_LOCKED_FILES == {"SCM": ("step_series.npz", "t_s"), "L2b": ("pads.npz", "t")}


def l2b_result(tag=None, ok=True):
    tag = tag or p2.TAG_VB
    return {"controller_tag": tag, "expect_controller": {"ok": ok, "controller_tag": tag, "name": tag},
            "controller_meta": {"slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": True},
                                                           "order_gate": {"enabled": True, "decisions": []}},
                                "liftoff_approach_slow": {"settings": dict(p2.LAS_PRESET)}}}


def make_l2b_batch(tmp_path, res, cid="C-5", pads="ok", name="batch_V5-RESUME-K1-GS_20990101_000000",
                   setting="VB"):
    bd = tmp_path / name
    case = "L2b_case_VB"
    (bd / case).mkdir(parents=True)
    (bd / case / "result.json").write_text(json.dumps(res), "utf-8")
    (bd / case / "controller_events.json").write_text("[]", "utf-8")
    a = _ll()
    t = np.round(np.arange(a.shape[0]) * 1e-3, 9)
    if pads == "ok":
        np.savez(bd / case / "pads.npz", t=t, law_locked=a)
    elif pads == "nokey":
        np.savez(bd / case / "pads.npz", t=t)
    elif pads == "after":
        a[500, 1] = -1
        np.savez(bd / case / "pads.npz", t=t, law_locked=a)
    argv = ["python.exe", "run_S8C.py", "--expect-controller", res["expect_controller"]["controller_tag"],
            "--extend-start-tracked"]
    row = {"case": case, "argv": argv, "rc": 0, "pool": "pcore", "planned_pool": "pcore", "criteria_id": cid,
           "v5_setting": setting, "code_at_launch": {"git": {"head": "b" * 40, "dirty": []}}}
    write_batch_json(bd, [row])
    return bd


@pytest.mark.parametrize("pads, stop", [("ok", False), ("nokey", True), ("nofile", True), ("after", True)])
def test_rev9_r92_r95_gs_l2b_law_locked(tmp_path, capsys, pads, stop):
    bd = make_l2b_batch(tmp_path, l2b_result(), pads=pads)
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    ll = rep["R9-2_law_locked_check"]
    assert ll["by_engine"]["L2b"]["rows"] == 1
    if stop:
        assert code == 2 and s["stop_codes"] == ["S-11"], rep["stops"]
        assert any("L2b pads.npz" in x["why"] for x in rep["stops"])
        if pads == "after":
            assert ll["failed_items"] == {"6_minus1": 1} and ll["minus1_patterns"] == {"after_arming": 1}
    else:
        assert code == 0, rep["stops"]
        assert ll["by_engine"]["L2b"]["ok"] == 1 and ll["minus1_patterns"] == {"pre_arming": 1}


@pytest.mark.parametrize("engine, okv", [("SCM", False), ("SCM", "absent"), ("L2b", False), ("L2b", "absent")])
def test_rev9_r91_gs_expect_controller_ok(tmp_path, capsys, engine, okv):
    if engine == "SCM":
        res = gs_full_result()
        if okv == "absent":
            del res["c2_setup"]["expect_controller"]["ok"]
        else:
            res["c2_setup"]["expect_controller"]["ok"] = False
        bd = make_batch(tmp_path, res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    else:
        res = l2b_result(ok=False)
        if okv == "absent":
            del res["expect_controller"]["ok"]
        bd = make_l2b_batch(tmp_path, res)
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-11", "S-2"], rep["stops"]
    assert any(x["code"] == "S-2" and "R9-1" in x["why"] for x in rep["stops"])
    assert any(x["code"] == "S-11" and "R9-1" in x["why"] for x in rep["stops"])
    assert rep["R9-1_expect_controller"] == {"rows_checked": 1, "s2": 1}


def test_rev9_r91_main_run_ok_false_is_s2_not_jp3_only(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])
    res["c2_setup"]["expect_controller"]["ok"] = False
    bd = make_batch(tmp_path, res, cid="C-5")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-2"] and any("R9-1" in x["why"] for x in rep["stops"])


def test_rev9_r95_r96_main_run_l2b(tmp_path, capsys):
    out = tmp_path / "o.json"
    for cid, want in (("C-5", "c5_not_judgeable"), ("C-1", "outside_c5_input_missing")):
        bd = make_l2b_batch(tmp_path / cid, l2b_result(), cid=cid, pads="nokey",
                            name="batch_V5-RESUME-K1-C5_20990101_000000")
        run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
        rep = json.loads(out.read_text("utf-8"))
        ll = rep["R9-2_law_locked_check"]
        assert ll[want] == 1 and ll["missing"] == 1, ll
        if cid == "C-5":
            assert any("R9-5" in u["why"] and "J11 not judgeable" in u["why"] for u in rep["undecidable"])
        else:
            assert not any("law_locked" in u["why"] for u in rep["undecidable"])
            assert not any("law_locked" in x["why"] for x in rep["stops"])
            assert any("R9-6" in r["what"] for r in rep["records"])


def test_rev9_r96_scm_outside_c5_recorded_not_stopped(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])
    bd = make_batch(tmp_path, res, cid="C-1", law_locked="nokey")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, (rep["stops"], rep["undecidable"])
    assert rep["R9-2_law_locked_check"]["outside_c5_input_missing"] == 1


def _manifest(tmp_path, bundle, case, setting, extra_row=False):
    rows = [{"case": case, "v5_setting": setting}]
    if extra_row:
        rows.append({"case": case, "v5_setting": setting})
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"batches": {bundle: {"rows": rows}}}), "utf-8")
    return p


BD_C5 = "x/batch_V5-RESUME-K1-C5_20990101_000000"


def _r94(m_rows, b_rows, case="c", batch_key="V5-RESUME-K1-C5", bd=BD_C5):
    man = {"batches": {"V5-RESUME-K1-C5": {"rows": m_rows}}}
    batch = {"cases": b_rows}
    if batch_key is not None:
        batch["batch"] = batch_key
    return p2.r94_ls_row(man, bd, batch, {"case": case})


def test_rev9_r94_ls_reading():
    assert p2.bundle_of(BD_C5) == "V5-RESUME-K1-C5" and p2.bundle_of("x/other") is None
    one = lambda s: [{"case": "c", "v5_setting": s}]   # noqa: E731
    assert _r94(one("LS1"), one("LS1"))["class"] == "ls"
    assert _r94(one("LS4"), one("LS4"))["class"] == "ls"
    assert _r94(one("VB"), one("VB"))["class"] == "not_ls"
    r = _r94(one(None), [{"case": "c"}])                                   # value absent in both rows
    assert r["class"] == "not_ls" and r["source_case"] == "both_values_absent" and r["source_ok"]
    assert _r94(one("LS1"), one("LS4"))["source_case"] == "values_differ"
    assert _r94(one("LS1"), [{"case": "c"}])["source_case"] == "one_value_only"
    # the row name is not read: an "_LS1_" case with V0 on both sides is not an LS row
    assert _r94([{"case": "v5s3_LS1_x", "v5_setting": "V0"}], [{"case": "v5s3_LS1_x", "v5_setting": "V0"}],
                case="v5s3_LS1_x")["class"] == "not_ls"
    # exact LS1..LS4, LS on the off arm needs the ③ off-arm tag
    row = {"criteria_id": "C-4", "v5_setting": "LS1", "r4368": {"arm": "off"}}
    assert p2.expected_chrono_tag(row, {}, [])[0] == p2.TAG_C4OFF_VB
    assert p2.expected_chrono_tag({"criteria_id": "C-5", "v5_setting": "LS5"}, {}, [])[0] == p2.TAG_V0


# ------------------------------------------------------------------ rev10 (62a0bd8d)
def test_rev10_seal_listed_and_checked(tmp_path, capsys, monkeypatch):
    seals = p2.check_seals(REPO, appendix=False)
    assert p2.REV10_REL in seals["rules"] and seals["rules"][p2.REV10_REL]["ok"], seals["rules"].get(p2.REV10_REL)
    assert p2.REV10_SHA == "62a0bd8dd6644f78bf37d052e884061d8c14e1cc96e2babc72a6ac0618f12c29"
    item = seals["rules"][p2.REV10_REL]
    assert item["sha256"] == item["seal_file_sha"] == p2.REV10_SHA
    monkeypatch.setattr(p2, "REV10_SHA", "0" * 64)
    code, s = run_main(["seal"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-1"]


@pytest.mark.parametrize("batch_key, bd, case", [
    ("V5-RESUME-K1-C4", BD_C5, "batch_name_unknown"),          # key differs from the folder-name part
    (None, "x/batch_V5-RESUME-K1-C5_badstamp", "batch_name_unknown"),   # no key, folder not of the form
    ("V5-RESUME-K1-C5", "x/batch_V5-RESUME-K1-C5_badstamp", "batch_name_unknown"),
    (None, "x/batch_V5-RESUME-K1-ZZ_20990101_000000", "batch_name_unknown"),   # not a manifest batch
    (None, BD_C5, "values_equal"),                              # no key: folder-name part
    ("C5", BD_C5, "batch_name_unknown")])                       # short batch ID (original 4.3) is not the name
def test_rev10_r101a_full_batch_name(batch_key, bd, case):
    r = _r94([{"case": "c", "v5_setting": "LS1"}], [{"case": "c", "v5_setting": "LS1"}], batch_key=batch_key, bd=bd)
    assert r["source_case"] == case, r
    if case == "values_equal":
        assert r["batch_name"] == "V5-RESUME-K1-C5" and r["class"] == "ls"
    else:
        assert r["class"] == "undecidable" and r["batch_name"] is None


@pytest.mark.parametrize("m_rows, b_rows, case", [
    ([], [{"case": "c"}], "manifest_rows_0"),                   # no manifest row is not "no value"
    ([{"case": "c"}, {"case": "c"}], [{"case": "c"}], "manifest_rows_many"),
    ([{"case": "c"}], [], "batch_cases_0"),
    ([{"case": "c"}], [{"case": "c"}, {"case": "c"}], "batch_cases_many")])
def test_rev10_r101b_row_counts_not_judgeable(m_rows, b_rows, case):
    r = _r94(m_rows, b_rows)
    assert r["class"] == "undecidable" and r["source_case"] == case and not r["source_ok"], r


@pytest.mark.parametrize("variant", ["absent", "not_json", "no_batches"])
def test_rev10_r101b_manifest_input_error(tmp_path, capsys, variant):
    bd = make_batch(tmp_path, scm_result(p2.TAG_VB, [2.4, 1.8]), cid="C-5",
                    name="batch_V5-RESUME-K1-C5_20990101_000000")
    man = tmp_path / "bad_manifest.json"
    if variant == "not_json":
        man.write_text("{not json", "utf-8")
    elif variant == "no_batches":
        man.write_text(json.dumps({"rows": []}), "utf-8")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--rows-manifest", str(man)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-11"] and rep["rows"] == [], rep
    assert rep["batches_not_judged"] == [str(bd)] and "R10-1b" in rep["stops"][0]["why"]


def test_rev10_r102_gs_source_check(tmp_path, capsys):
    res = gs_full_result()
    bd = make_batch(tmp_path, res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    r94 = rep["R9-4_ls_rows"]
    assert r94["source_check"] == {"rows": 1, "ok": 1, "failed": 0}
    assert r94["source_cases"] == {"values_equal": 1} and r94["batch_names"] == {"V5-RESUME-K1-GS": 1}
    # batch key differing from the folder name -> G-S failure S-11 (R10-2)
    b = json.loads((bd / "batch.json").read_text("utf-8"))
    b["batch"] = "V5-RESUME-K1-C5"
    (bd / "batch.json").write_text(json.dumps(b), "utf-8")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-11"] and any("R10-2" in x["why"] for x in rep["stops"])
    assert rep["R9-4_ls_rows"]["source_cases"] == {"batch_name_unknown": 1}
    # manifest without the case -> S-11 in G-S
    b["batch"] = "V5-RESUME-K1-GS"
    (bd / "batch.json").write_text(json.dumps(b), "utf-8")
    mp = tmp_path / "rows_manifest.json"
    mp.write_text(json.dumps({"batches": {"V5-RESUME-K1-GS": {"rows": []}}}), "utf-8")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-11"]
    assert rep["R9-4_ls_rows"]["source_cases"] == {"manifest_rows_0": 1}


def test_rev10_main_run_unknown_source_is_recorded_on_c5(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])
    bd = make_batch(tmp_path, res, cid="C-5", name="batch_V5-RESUME-K1-C5_20990101_000000")
    (tmp_path / "rows_manifest.json").write_text(json.dumps({"batches": {"V5-RESUME-K1-C5": {"rows": []}}}), "utf-8")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, (rep["stops"], rep["undecidable"])       # recorded: n_late is judged by the J11 path
    assert rep["R9-4_ls_rows"]["c5_undecidable_rows"] == ["OC5_mixed_rigid_J1FR_Kc3_VB_top"]
    assert any("manifest_rows_0" in r["what"] and "LS 판별 불가" in r["what"] for r in rep["records"])


def test_rev9_r94_ls_row_tag_and_c5_undecidable(tmp_path, capsys):
    res = scm_result(p2.TAG_VB, [2.4, 1.8])
    bd = make_batch(tmp_path, res, cid="C-5", setting="LS1", name="batch_V5-RESUME-K1-C5_20990101_000000")
    case = "OC5_mixed_rigid_J1FR_Kc3_VB_top"
    man = _manifest(tmp_path, "V5-RESUME-K1-C5", case, "LS1")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--rows-manifest", str(man)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, (rep["stops"], rep["undecidable"])
    assert rep["R9-4_ls_rows"]["classes"] == {"ls": 1} and rep["R9-4_ls_rows"]["ls_rows"] == [case]
    # LS row whose tag is not ③ -> S-2 (R9-4)
    monkey = copy.deepcopy(res)
    monkey["v5_hydraulics"]["controller_tag"] = p2.TAG_V0
    monkey["c2_setup"]["expect_controller"]["name"] = p2.TAG_V0
    monkey["v5_hydraulics"]["hydraulic_options"] = {}
    bd2 = make_batch(tmp_path / "b", monkey, cid="C-5", setting="LS1", name="batch_V5-RESUME-K1-C5_20990101_000001")
    man2 = _manifest(tmp_path / "b", "V5-RESUME-K1-C5", case, "LS1")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd2), "--rows-manifest", str(man2)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and "S-2" in s["stop_codes"]
    assert any("R9-4" in x["why"] for x in rep["stops"])
    # one side only on a C-5 row: LS reading not judgeable, recorded with the 'LS 판별 불가' note
    man3 = _manifest(tmp_path / "b", "V5-RESUME-K1-C5", case, None)
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--rows-manifest", str(man3)], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert rep["R9-4_ls_rows"]["c5_undecidable_rows"] == [case]
    assert any("R9-4" in r["what"] and "LS 판별 불가" in r["what"] for r in rep["records"])


# ------------------------------------------------------------------ rev11 (9bac4524)
def test_rev11_seal_listed_and_checked(capsys, monkeypatch):
    seals = p2.check_seals(REPO, appendix=False)
    assert p2.REV11_REL in seals["rules"] and seals["rules"][p2.REV11_REL]["ok"], seals["rules"].get(p2.REV11_REL)
    assert p2.REV11_SHA == "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f"
    item = seals["rules"][p2.REV11_REL]
    assert item["sha256"] == item["seal_file_sha"] == p2.REV11_SHA
    monkeypatch.setattr(p2, "REV11_SHA", "0" * 64)
    code, s = run_main(["seal"], capsys)
    assert code == 2 and s["stop_codes"] == ["S-1"]


def openloop_batch(tmp_path, cal=True, head="c" * 40):
    bd = tmp_path / "batch_V5-RESUME-K1-GS_20990101_000000"
    case = "GS_P3a_G1_B_VB_prop_lift10"
    (bd / case).mkdir(parents=True)
    res = {"v5_hydraulics": {"controller_options": {"applied": False}}, "p3a": {"checks": {}},
           "num_threads_chrono": 4, "hull_hook": {"mode": "fast"}}
    (bd / case / "result.json").write_text(json.dumps(res), "utf-8")
    row = {"case": case, "argv": ["python.exe", "run_S9.py", "openloop"], "rc": 0, "criteria_id": "C-6",
           "v5_setting": "VB", "pool": "pcore", "planned_pool": "pcore"}
    if cal:
        row["code_at_launch"] = {"git": {"head": head, "dirty": [], "clean": True}}
    write_batch_json(bd, [row])
    return bd


@pytest.mark.parametrize("variant, want", [("ok", 0), ("absent", 2), ("differs", 2)])
def test_rev11_r114_open_loop_launch_head(tmp_path, capsys, variant, want):
    bd = openloop_batch(tmp_path, cal=variant != "absent")
    out = tmp_path / "o.json"
    gas = "c" * 40 if variant != "differs" else "d" * 40
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs", "--git-at-start", gas], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == want, rep["stops"]
    if want:
        assert s["stop_codes"] == ["S-12"] and any("R11-4" in x["why"] for x in rep["stops"])
    st = {"ok": "ok", "absent": "launch_head_absent", "differs": "launch_head_differs"}[variant]
    assert rep["R11-4_commit_identity"]["launch_head"] == {st: 1}
    assert rep["R11-5_gs_grades"].startswith("G-S 행 등급은 판정하지 않음")


def test_rev11_r114_abbreviated_commit_and_missing_argument(tmp_path, capsys):
    bd = openloop_batch(tmp_path)
    code, s = run_main(["chrono", "--batch", str(bd), "--gs", "--git-at-start", "ccccccc"], capsys)
    assert code == 0, s
    code, s = run_main(["chrono", "--batch", str(bd), "--gs", "--git-at-start", "cccc"], capsys)   # < 7 hex
    assert code == 2 and s["stop_codes"] == ["S-12"]
    out = tmp_path / "o.json"
    p2.main(["--repo", str(REPO), "--out", str(out), "chrono", "--batch", str(bd), "--gs",
             "--rows-manifest", str(tmp_path / "rows_manifest.json")])
    capsys.readouterr()
    rep = json.loads(out.read_text("utf-8"))
    assert any("--git-at-start not given" in u["why"] for u in rep["undecidable"])


def test_rev11_r114_level_row_code_state(tmp_path, capsys):
    res = gs_full_result()
    res["code_state"] = {"git_at_start": {"head": "a" * 40, "clean": True}}
    bd = make_batch(tmp_path, res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    out = tmp_path / "o.json"
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0, rep["stops"]
    assert rep["R11-4_commit_identity"]["code_state"] == {"ok": 1}
    res["code_state"]["git_at_start"]["head"] = "e" * 40          # result.json commit differs from git_at_start
    bd = make_batch(tmp_path / "b", res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 2 and s["stop_codes"] == ["S-12"]
    assert rep["R11-4_commit_identity"]["code_state"] == {"differs": 1}
    del res["code_state"]                                          # no record: launch head only
    bd = make_batch(tmp_path / "c", res, name="batch_V5-RESUME-K1-GS_20990101_000000")
    code, s = run_main(["--out", str(out), "chrono", "--batch", str(bd), "--gs"], capsys)
    rep = json.loads(out.read_text("utf-8"))
    assert code == 0 and rep["R11-4_commit_identity"]["code_state"] == {"absent": 1}
