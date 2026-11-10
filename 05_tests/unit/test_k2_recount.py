"""Synthetic tests of the K-2 path 2 recount (04_scripts/03_control/k2/k2_recount.py)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("k2_recount", ROOT / "04_scripts/03_control/k2/k2_recount.py")
kr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(kr)


def _series(tmp: Path, name: str, lift_leg: int | None = None, lift_t: float | None = None,
            amp: float = 0.005) -> str:
    t = np.arange(10.0, 30.0, 0.001)
    pad = np.full((t.size, 4), 30e3)
    if lift_leg is not None:
        pad[(t >= lift_t) & (t < lift_t + 0.05), lift_leg] = 0.0
    rate = np.zeros((t.size, 3))
    rate[:, 1] = amp * np.sin(2 * np.pi * 2.5 * t)
    np.savez(tmp / name, t_s=t, pad_normal_min_N=pad, body_rate_rad_s=rate)
    return name


def _row(rid: str, tcl: bool, series: str, k1: bool = False, j1: float = 50e3, ready: float = 43.0,
         cap: bool = False, j3: int = 0, latch_t: float = 18.0) -> dict:
    events = [[19.6, "floor_estimate_touch"]]
    if tcl:
        events += [[latch_t, f"INFO_TOUCH_CREEP_LATCH:{leg}"] for leg in kr.LEGS]
        if cap:
            events.append([latch_t, "INFO_TOUCH_CREEP_CAP:RL"])
    else:
        events.append([17.0, "INFO_TOUCH_DIP_HELD:FL"])
    tag = "final_C4G2_LAS" + ("_K1" if k1 else "") + ("_TCL" if tcl else "")
    return {"id": rid, "controller_tag": tag, "k1_order_gate": k1, "touch_creep_latch": tcl,
            "commands_sha256": "c" + rid, "fails": [], "series_file": series,
            "aug_arm": "H0", "is_kplant": True,
            "d8x": {"t_touch_s": 19.6, "t_lift_s": 20.6, "t_ready_s": ready, "J1_min_cyl_after_lift_N": j1,
                    "J1_window_s": 30.0, "reanchor_intervals_s": [], "J2_min_cyl_reanchor_N": None,
                    "J3_pad_lift_samples": j3, "J4_att_max_after_ready_deg": 0.03,
                    "J6_max_moving_bar": 100.0, "events": events}}


def test_k2_row_pass_and_e4(tmp_path):
    s = _series(tmp_path, "a.npz")
    r = kr.judge_row(_row("a", True, s), kr.DEFAULT_FIELDS, "harness", tmp_path, True)
    assert kr.row_status(r) == "pass", r
    bad = _row("b", True, s)
    bad["d8x"]["events"] = bad["d8x"]["events"][:3]   # only two latch legs
    r = kr.judge_row(bad, kr.DEFAULT_FIELDS, "harness", tmp_path, True)
    assert kr.row_status(r) == "not_judgeable"
    off_with_creep = _row("c", False, s)
    off_with_creep["d8x"]["events"].append([18.0, "INFO_TOUCH_CREEP_LATCH:FL"])
    assert kr.row_status(kr.judge_row(off_with_creep, kr.DEFAULT_FIELDS, "harness", tmp_path, True)) \
        == "not_judgeable"


def test_j3_series_mismatch_and_lift(tmp_path):
    s = _series(tmp_path, "l.npz", lift_leg=2, lift_t=20.0)
    r = kr.judge_row(_row("l", True, s, j3=50), kr.DEFAULT_FIELDS, "harness", tmp_path, True)
    assert r["fail_items"] == ["J3"] and not r["not_judgeable"]
    r = kr.judge_row(_row("m", True, s, j3=0), kr.DEFAULT_FIELDS, "harness", tmp_path, True)
    assert any("series recount" in p for p in r["not_judgeable"])


def test_sh1_post_latch_lift(tmp_path):
    s = _series(tmp_path, "p.npz", lift_leg=0, lift_t=18.5)
    r = kr.judge_row(_row("p", True, s, latch_t=18.0), kr.DEFAULT_FIELDS, "harness", tmp_path, True)
    assert r["metrics"]["SH1_post_latch_lift"]["FL"] == 50
    assert r["items"]["J3"]


def test_shadow_flags(tmp_path):
    so = _series(tmp_path, "o.npz", amp=0.002)
    st = _series(tmp_path, "t.npz", amp=0.006)
    off = [kr.judge_row(_row("x", False, so, j1=50e3, ready=43.0), kr.DEFAULT_FIELDS, "harness",
                        tmp_path, True)]
    tcl = [kr.judge_row(_row("x", True, st, j1=46e3, ready=46.5, cap=True), kr.DEFAULT_FIELDS,
                        "harness", tmp_path, True)]
    sh = kr.shadow(off, tcl)
    assert set(sh["flags"]) == {"SH-2", "SH-3", "SH-4", "SH-5"}
    assert sh["SH4_delta_N"] == pytest.approx(-4e3)
    near = [kr.judge_row(_row("x", True, so, j1=kr.F_D8_N + 1000.0), kr.DEFAULT_FIELDS, "harness",
                         tmp_path, True)]
    assert "SH-6" in kr.shadow(off, near)["flags"]
    assert kr.shadow(off, [])["unpaired"] == 1


def test_cp_two_paths():
    ok = kr.cp_upper(17, 855)
    assert ok["agree"] and ok["pass"]
    bad = kr.cp_upper(18, 855)
    assert bad["agree"] and not bad["pass"] and bad["beta_ppf"] == pytest.approx(0.03106, abs=5e-5)


def test_v5_kinds(tmp_path):
    def dump(name, rows):
        p = tmp_path / name
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return [str(p)]
    off = dump("off.jsonl", [{"k": 1, "ok": True}, {"k": 2, "ok": True}])
    tcl = dump("tcl.jsonl", [{"k": 1, "ok": True}, {"k": 2, "ok": False}])
    r = kr.v5_bundle({"kind": "pass_to_fail", "off": off, "tcl": tcl, "key": "k", "status": "ok"})
    assert not r["pass"] and r["pass_to_fail"] == ["2"]
    g_off = dump("g_off.jsonl", [{"k": 1, "ready": True, "ev": ["FAULT_LIFT_STROKE_LIMIT:soil:FR"]}])
    g_tcl = dump("g_tcl.jsonl", [{"k": 1, "ready": True, "ev": ["FAULT_LIFT_STROKE_LIMIT:soil:FR"]}])
    assert kr.v5_bundle({"kind": "g8", "off": g_off, "tcl": g_tcl, "key": "k", "ready": "ready",
                         "faults": "ev"})["pass"]
    g_new = dump("g_new.jsonl", [{"k": 1, "ready": True, "ev": ["FAULT_STROKE_END:RL"]}])
    assert not kr.v5_bundle({"kind": "g8", "off": g_off, "tcl": g_new, "key": "k", "ready": "ready",
                             "faults": "ev"})["pass"]


def test_false_latch():
    t = np.arange(0.0, 2.0, 0.001)
    pad = np.full((t.size, 4), 20e3)
    pad[(t > 0.65) & (t < 0.75), 1] = 0.0
    assert kr.false_latch(t, pad, {0: 1.0}) == []
    assert kr.false_latch(t, pad, {1: 1.1}) == ["FR@0.700"]


def test_grade_order():
    assert kr.grade({"G-A": "fail", "G-B": "pass"}, [], []) == "conditional_range_limited"
    assert kr.grade({"G-A": "pass", "G-C": "fail"}, [], []) == "fail"
    assert kr.grade({"G-A": "pass"}, [("v2", "SH-3")], []) == "conditional"
    assert kr.grade({"G-A": "pass"}, [], ["E-1"]) == "not_judgeable"
    assert kr.grade({g: "pass" for g in ("G-A", "G-B", "G-C", "G-D", "G-E")}, [], []) == "pass"


def test_expect_template_counts():
    e = kr.expect_template()
    assert e["v2"]["off"]["count"] == 1102 and sum(e["v2"]["tcl"]["tags"].values()) == 1102
    assert len(e["v6"]["rows"]) == 8 and e["v3"]["per_cell"] == 273


def test_rules_seal_constants():
    k2 = ROOT / "06_analysis/02_control/k2"
    if not (k2 / kr.RULES_FILE).exists():
        pytest.skip("rules folder not present")
    assert hashlib.sha256((k2 / kr.RULES_FILE).read_bytes()).hexdigest() == kr.RULES_SHA256
    assert kr.rules_check(k2)["ok"]


def test_recount_end_to_end_runs(tmp_path):
    s = _series(tmp_path, "e.npz")

    def dump(name, rows):
        p = tmp_path / name
        p.write_text(json.dumps({"runs": rows}), encoding="utf-8")
        return [str(p)]
    v2 = {"off": dump("v2o.json", [_row("a", False, s)]), "tcl": dump("v2t.json", [_row("a", True, s)]),
          "series_root": str(tmp_path)}
    t = np.arange(10.0, 30.0, 0.001)
    np.savez(tmp_path / "pads.npz", t=t, N=np.full((t.size, 4), 45e3))
    rows6 = {}
    for arm in ("off", "tcl"):
        ev = [[18.0, f"INFO_TOUCH_CREEP_LATCH:{leg}"] for leg in kr.LEGS] if arm == "tcl" else []
        rj = {"case_id": f"K2_L2b_top_fdown3.5_Fs4_{arm}", "touch_creep_latch": arm == "tcl",
              "controller_tag": "final_C4G2_LAS" + ("_TCL" if arm == "tcl" else ""), "k1_order_gate": False,
              "t_touch_s": 19.6, "t_lift_s": 20.6, "t_ready_s": 43.0, "J1_min_cyl_after_lift_N": 50e3,
              "J1_window_s": 30.0, "reanchor_intervals_s": [], "J2_min_cyl_reanchor_N": None,
              "J4_att_max_after_ready_deg": 0.02, "J6_max_moving_bar": 100.0,
              "crawler_recontact_after_loc": 0, "events": ev}
        p = tmp_path / f"r_{arm}.json"
        p.write_text(json.dumps(rj), encoding="utf-8")
        rows6[rj["case_id"]] = {"row_json": str(p), "pads_npz": str(tmp_path / "pads.npz"),
                                "engine": "L2b", "arm": arm}
    manifest = {"v2": v2, "v4": v2, "v6": {"rows": rows6}}
    out = kr.recount(manifest, kr.expect_template(), kr.DEFAULT_FIELDS, None)
    assert out["grade"] == "not_judgeable"            # counts, v3 and v5 missing by design
    assert out["gates"]["G-A"] == "pass"
    assert out["bundles"]["v6"]["rows"]["K2_L2b_top_fdown3.5_Fs4_tcl"]["items"]["V6_false_latch"]


def _point_file(tmp: Path, pts: dict) -> Path:
    p = tmp / "pts.json"
    p.write_text(json.dumps({"ra_points": [{"tag": t, "roll_deg": r, "pitch_deg": q}
                                           for t, (r, q) in pts.items()]}), encoding="utf-8")
    return p


def test_points_check_rev1(tmp_path):
    dia = kr.v4_diamond_points()
    assert dia["d45-+"] == (-2.1389, 2.1389) and dia["r+p+0.25"] == (1.375, 2.625)
    assert kr.points_check(_point_file(tmp_path, dia))["ok"]
    exact = kr.v4_table_points()
    chk = kr.points_check(_point_file(tmp_path, exact))       # fails (i) on d45 only
    assert not chk["ok"] and all(p.startswith("d45") for p in chk["problems"])
    bad = dict(dia)
    bad["pitch+"] = (0.0, 3.5 + 1e-9)
    assert not kr.points_check(_point_file(tmp_path, bad))["ok"]


def test_e7_and_dhat(tmp_path):
    s = _series(tmp_path, "d.npz")
    pts = {"pitch+": (0.0, 3.5)}
    row = _row("a", True, s)
    row.update({"point": "pitch+", "angles_deg": [0.0, 3.5],
                "k2": {"dhat_window_open_legs": ["RR"], "dhat_window_stroke_mm": [0, 0, 0, 0.31],
                       "dhat_N": 9000.0}})
    r = kr.judge_row(row, kr.DEFAULT_FIELDS, "harness", tmp_path, True, points=pts)
    assert kr.row_status(r) == "pass", r
    moved = json.loads(json.dumps(row))
    moved["angles_deg"] = [0.0, 3.5001]
    assert any(p.startswith("E-7") for p in
               kr.judge_row(moved, kr.DEFAULT_FIELDS, "harness", tmp_path, True, points=pts)["not_judgeable"])
    off = _row("a", False, s)
    off.update({"point": "pitch+", "angles_deg": [0.0, 3.5],
                "k2": {"dhat_window_open_legs": [], "dhat_window_stroke_mm": [0, 0, 0, 0], "dhat_N": 3000.0}})
    ro = kr.judge_row(off, kr.DEFAULT_FIELDS, "harness", tmp_path, True, points=pts)
    d = kr.dhat_summary([ro], [r])
    assert d["open_leg_rows"] == 1 and d["stroke_max_mm"] == pytest.approx(0.31)
    assert d["abs_delta_ge_5kN"] == [(6000.0, "a")] and d["missing"] == 0


def test_screen_selftest():
    screen = ROOT / "06_analysis/02_control/k2/screen"
    if not screen.exists():
        pytest.skip("screen folder not present")
    r = kr.selftest_screen(screen)
    assert r["ok"], r
