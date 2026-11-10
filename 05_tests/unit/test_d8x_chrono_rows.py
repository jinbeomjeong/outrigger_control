"""D8x Chrono rows (cad 2026-11-10): definitions only, no Chrono run.

Rules ``06_analysis/02_control/d8x/d8x_rules.md`` (``s6_stage2.D8X_RULES``): 1.2 points, 4.4 rows, 5.1 / 5.2
W / V, 9.3 cad part. The point and row tables are parsed from the rules file itself, so a rules revision
(``D8X_RULES`` pointed at ``d8x_rules_rev1.md``) is checked the same way. Rev2 (``d8x_rules_rev2.md``): settle map
per engine (1, E-4b), tag / LAS-b (4), run length (5), scenario group (6), and the judge keys (``d8x`` block,
verify metrics J4 / J10).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip("pychrono")

import d8x_case_hashes as hashes  # noqa: E402
import run_S6C as s6  # noqa: E402
import run_S8C as s8  # noqa: E402

st = s6.st
W_TAGS = tuple(st.D8X_W_FLOOR_OF_POINT)


def _num(text: str) -> float:
    return float(text.strip().strip("*").replace("−", "-"))


def _rules_text(rev1: bool = False) -> str:
    return (ROOT / (st.D8X_RULES_REV1 if rev1 else st.D8X_RULES)).read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def _points_of(sec: str) -> dict[str, tuple[float, float]]:
    out = {}
    for m in re.finditer(r"^\|\s*\**`([^`]+)`\**\s*\|\s*([^|]+)\|\s*([^|]+)\|", sec, re.M):
        out[m.group(1)] = (_num(m.group(2)), _num(m.group(3)))
    return out


def rules_points() -> dict[str, tuple[float, float]]:
    """Rules 1.2 tables (A) / (B) / (C) in force: rev1 1.2 replaces the original 1.2 (rev1 0)."""
    rev1 = _points_of(_section(_rules_text(True), "## 1.2", "## 1.3"))
    assert len(rev1) == 24  # 16 + 4 + 4, the whole table replaced
    return rev1


def rules_rows() -> list[tuple]:
    """Rules 4.4 table: (number, name, engine, beta, F_s or None, level, floor, order), with rev1 4.4
    ('fup3.7' read as 'fup3.6' everywhere)."""
    assert "`fup3.7`을 모두 `fup3.6`으로" in _rules_text(True)
    sec = _section(_rules_text(), "### 4.4", "## 5.").replace("fup3.7", "fup3.6")
    rows = []
    pat = r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(\S+)\s*\|\s*([\d.]+)\s*\|\s*([^|]+)\|\s*(\w+)\s*\|\s*([^|]+)\|\s*(\d)\s*\|"
    for m in re.finditer(pat, sec, re.M):
        fs = m.group(5).strip()
        fs_v = None if fs.startswith("–") or fs.startswith("-") else float(fs)
        floor = m.group(7).strip()
        floor = {"W(5.1)": "<W>", "V(5.2)": "<V>"}.get(floor, floor)
        engine = {"L1-R": "L1R"}.get(m.group(3), m.group(3))
        rows.append((int(m.group(1)), m.group(2), engine, float(m.group(4)), fs_v, m.group(6),
                     floor, int(m.group(8))))
    return rows


@pytest.mark.parametrize("path,sha", [(st.D8X_RULES, st.D8X_RULES_SHA256),
                                      (st.D8X_RULES_REV1, st.D8X_RULES_REV1_SHA256),
                                      (st.D8X_RULES_REV2, st.D8X_RULES_REV2_SHA256)])
def test_rules_files_are_the_sealed_ones(path: str, sha: str) -> None:
    data = (ROOT / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    seal = (ROOT / path).with_suffix(".sha256").read_text(encoding="utf-8")
    assert sha in seal


def test_rev1_floor_changes() -> None:
    assert "fup3.7" not in st.D8X_FLOORS and "fup3.7" not in st.FLOORS
    assert tuple(st.FLOORS["fup3.6"]) == (0.0, -3.6)
    assert st.D8X_HALF_SPANS_DEG == {"roll": 5.7, "pitch_nose_down": 3.7, "pitch_nose_up": 3.6}
    names = {r.number: r.name for r in st.D8X_ROWS}
    assert (names[2], names[8], names[15]) == ("D8X_K24_top_fup3.6_Fs4", "D8X_C1_D8_top_fup3.6_b1.6",
                                               "D8X_K0V_top_fup3.6_Fs0")
    want = {"dxpm025": (1.425, -2.7), "dxpm050": (2.85, -1.8), "dxpm075": (4.275, -0.9),
            "dxmm050": (-2.85, -1.8), "d45pm": (2.2064, -2.2064), "d45mm": (-2.2064, -2.2064)}
    for f, rp in want.items():
        assert tuple(st.FLOORS[f]) == rp


def test_floors_equal_rules_points() -> None:
    pts = rules_points()
    for name in {**st.D8X_RPX_FLOORS, **st.D8X_AXIS_FLOORS}:
        assert tuple(st.FLOORS[name]) == pts[name], name  # difference 0 (I-3 / I-4)
    for tag, floor in st.D8X_W_FLOOR_OF_POINT.items():
        assert tuple(st.FLOORS[floor]) == pts[tag], tag  # 5.1: the R-a coordinates
    assert len(st.D8X_FLOORS) == 19 and set(st.D8X_FLOORS) <= set(st.FLOORS)
    # rules 5.1 candidate list, literal order
    sec = _section(_rules_text(), "### 5.1", "### 5.2")
    table = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", sec, re.M)
    assert tuple(table) == tuple(st.D8X_W_FLOOR_OF_POINT.items())


def test_rows_equal_rules_table() -> None:
    want = rules_rows()
    assert len(want) == 19
    got = [(r.number, r.name, r.engine, r.beta_GPa, r.fs_kN, r.level, r.floor, r.order) for r in st.D8X_ROWS]
    assert got == want


@pytest.mark.parametrize("w", W_TAGS)
def test_sets_w1_w2(w: str) -> None:
    wf = st.D8X_W_FLOOR_OF_POINT[w]
    l2b = s8.case_set("d8x_w1", w=w)
    l1r = s6.CASE_SETS["d8x_w1"]()
    assert len(l2b) == 13 and len(l1r) == 5
    names = {c.case_id for c in l2b} | {c.case_id for c in l1r}
    want = {r.resolved(wf).name for r in st.D8X_ROWS if r.order == 1}
    assert names == want and len(names) == 18
    assert f"D8X_K24_top_{wf}_Fs4" in names
    assert [c.case_id for c in s8.case_set("d8x_w2", w=w, v=wf)] == [f"D8X_K8_top_{wf}_Fs8"]
    assert s8.case_set("d8x_w1", w=wf)[5].case_id == f"D8X_K24_top_{wf}_Fs4"  # floor name works too


def test_w_v_arguments_checked() -> None:
    with pytest.raises(SystemExit):
        s8.case_set("d8x_w1")
    with pytest.raises(SystemExit):
        s8.case_set("d8x_w2")
    with pytest.raises(ValueError):
        s8.case_set("d8x_w1", w="pitch+")  # not a W candidate (5.1 excludes it)
    with pytest.raises(ValueError):
        s8.case_set("d8x_w2", v="dxpm050")  # a W floor as V needs the same --w
    with pytest.raises(ValueError):
        s8.case_set("d8x_w2", w="d45++", v="dxpm050")
    fixed = [r.floor for r in st.D8X_ROWS if r.number <= 5]
    for f in fixed:
        (c,) = s8.case_set("d8x_w2", v=f)
        assert c.case_id == f"D8X_K8_top_{f}_Fs8" and c.pair_fs0 == f"D8X_K0V_top_{f}_Fs0"


def test_case_definitions() -> None:
    table = s8.case_table()
    for r in st.D8X_ROWS:
        if r.engine != "L2b" or r.floor.startswith("<"):
            continue
        c = table[r.name]
        meta = c.to_meta()
        assert c.group == "D8X" and c.engine == "L2b_NSC" and c.fs_kN == r.fs_kN
        assert c.scenario.level == r.level and c.floor == r.floor
        assert meta["base"]["slope_limit_mode"] == "verification_ext"
        assert meta["base"]["d8x_row"] == r.number and meta["base"]["beta_GPa"] == 1.0
        assert c.lock_valve == "pilot_check" and c.event is None and not c.base.sensor_model
    # the families' scenarios (rules 4.4: as the family): fdown = H4V, else D8
    assert table["D8X_K24_top_fdown3.7_Fs4"].scenario.group == "G2-R"
    assert table["D8X_K24_top_roll5.7_Fs4"].scenario.group == "D8"
    s6t = s6.case_table()
    for r in st.D8X_ROWS:
        if r.engine != "L1R":
            continue
        c = s6t[r.name]
        assert c.config == "C-1" and c.beta_GPa == r.beta_GPa and c.d8x_row == r.number
        assert c.slope_limit_mode == "verification_ext" and c.snapshot == st.snapshot_name(r.level, r.floor)
    assert s6t["D8X_C1_H4V_top_fdown3.7"].scenario.items == ("R", "2", "3", "8")
    # rev2 5: no roll 5.5 levelling time assumed for roll 5.7 (the plain family rule; T_run takes T^_R + 20 s)
    assert st._length("roll5.7", h4=True, check_s=2.0) == st._length("flat", h4=True, check_s=2.0)
    assert st._length("rollm5.7", h4=True, check_s=2.0) == st._length("flat", h4=True, check_s=2.0)
    assert st._length("roll5.5", h4=True, check_s=2.0) == 2.0 + 17.0 + 40.0 + 11.0 + 10.0  # unchanged


def test_start_states_declared() -> None:
    states = st.d8x_start_states("r+p-0.5")
    snaps = [s for s in states if s["kind"] == "snapshot"]
    assert [(s["level"], s["floor"]) for s in snaps] == list(s6.D8X_SNAPSHOTS)
    assert [s["snapshot"] for s in snaps] == ["S6_crawler_top_fdown3.7", "S6_crawler_top_fup3.6",
                                              "S6_crawler_top_roll5.7", "S6_crawler_top_rpX"]
    l2b = [(s["level"], s["floor"]) for s in states if s["engine"] == "L2b" and s["floor"] != "<V>"]
    assert l2b == [("top", "fdown3.7"), ("top", "fup3.6"), ("top", "roll5.7"), ("top", "rollm5.7"),
                   ("top", "rpX"), ("top", "dxpm050"), ("middle", "rpX"), ("bottom", "rpX")]
    rows = sorted(n for s in states for n in s["rows"])
    assert rows == list(range(1, 20))  # every row has exactly one start state


def test_plan_document() -> None:
    doc = s8.d8x_plan("r+p-0.5", "rpX")
    assert doc["counts"] == {"d8x_w1": 18, "d8x_w2": 1}
    assert [r["row"] for r in doc["rows"]] == list(range(1, 20))
    assert doc["rows"][5]["name"] == "D8X_K24_top_dxpm050_Fs4"
    assert doc["rows"][18]["name"] == "D8X_K8_top_rpX_Fs8"
    json.dumps(s6._plain(doc))


def test_earlier_rows_meta_argv_unchanged() -> None:
    base = json.loads(hashes.BASELINE.read_text(encoding="utf-8"))
    d = hashes.diff(base, hashes.current_hashes())
    for sec, res in d.items():
        assert not res["missing"] and not res["changed"], (sec, res["missing"][:5], res["changed"][:5])
        assert not res["added"], (sec, res["added"][:5])  # D8x entries are filtered out by the helper


@pytest.mark.skipif(not s6.d8x_mode_available(),
                    reason="SlopeLimitMode.VERIFICATION_EXT not installed (python-expert, rules 9.2 item 1)")
def test_controller_config_uses_verification_ext() -> None:
    from outrigger_sim.control.target import SlopeLimitMode, TargetLimits
    from outrigger_sim.params import load_params

    c6 = s6.case_table()["D8X_C1_D8_top_rpX_b1.6"]
    cfg = s6.controller_config(load_params(level="top"), c6)
    assert cfg.target.slope_limit_mode is SlopeLimitMode("verification_ext")
    lim = TargetLimits.for_mode(SlopeLimitMode("verification_ext"))
    assert lim.usage_tolerance == pytest.approx(0.01)
    spans = s6.half_spans_deg(cfg)  # rev1 1.3: 5.7 / 3.7 / 3.6
    assert spans["roll"] == pytest.approx(5.7, abs=1e-12)
    assert spans["pitch_nose_down"] == pytest.approx(3.7, abs=1e-12)
    assert spans["pitch_nose_up"] == pytest.approx(3.6, abs=1e-12)
    rec = s8.d8x_preflight(s8.case_set("d8x_w1", w="d45++"), None)
    assert {r["slope_limit_mode"] for r in rec["rows"].values()} == {"verification_ext"}
    assert rec["rules_rev"] == "rev5" and rec["expected_tag"] == st.D8X_EXPECTED_TAG
    assert rec["rules_rev4_sha256"].startswith("5233c517")
    assert rec["rules_rev3_sha256"].startswith("2318fb5c")
    assert rec["rules_rev5_sha256"].startswith("63437019")
    assert {r["settle_map"]["kind"] for r in rec["rows"].values()} == {"identity"}
    rec6 = s6.d8x_preflight(s6.CASE_SETS["d8x_w1"](), None)
    assert len(rec6["rows"]) == 5
    assert {(r["settle_map"]["kind"], r["settle_map"]["level"]) for r in rec6["rows"].values()} == {("level", "top")}
    assert all(r["las_b_enabled"] and r["expected_tag"] == "final_C4G2_LAS_K1" for r in rec6["rows"].values())


@pytest.mark.skipif(s6.d8x_mode_available(), reason="VERIFICATION_EXT installed")
def test_refuses_without_verification_ext() -> None:
    with pytest.raises(SystemExit):
        s8.d8x_preflight(s8.case_set("d8x_w1", w="d45++"), None)
    c6 = s6.case_table()["D8X_C1_D8_top_rpX_b1.6"]
    with pytest.raises(RuntimeError):
        s6.slope_limit_mode(c6)


T_RUN_W1 = {  # rev2 5 (W = dxpm050 / r+p-0.5, V = rpX): row -> (T^_R, T_run) s
    1: (82.0, 102.0), 2: (60.7, 93.0), 3: (61.4, 81.4), 4: (61.4, 81.4), 5: (60.5, 80.5), 6: (60.5, 80.5),
    7: (86.4, 106.4), 8: (60.3, 93.0), 9: (61.9, 81.9), 10: (61.4, 81.4), 11: (89.6, 109.6),
    12: (60.5, 80.5), 13: (60.7, 80.7), 14: (83.5, 103.5), 15: (60.8, 93.0), 16: (61.4, 81.4),
    17: (61.4, 81.4), 18: (60.5, 80.5), 19: (60.5, 80.5),
}


def test_rev2_run_length_table() -> None:
    doc = s8.d8x_plan("r+p-0.5", "rpX")
    assert doc["expected_tag"] == "final_C4G2_LAS_K1" and doc["rules_rev"] == "rev5"
    got = {r["row"]: (r["ready_hat_s"], r["T_run_s"]) for r in doc["rows"]}
    assert set(got) == set(T_RUN_W1)
    for k, v in T_RUN_W1.items():
        assert got[k] == pytest.approx(v, abs=1e-6), k
    for r in doc["rows"]:
        assert r["T_run_s"] >= r["family_run_s"] - 1e-9
        assert r["T_run_s"] >= r["ready_hat_s"] + 20.0 - 1e-9
        assert r["expected_tag"] == "final_C4G2_LAS_K1"
    # rev2 5 table: roll 5.7 = 59.2 x 5.7 / 5.5 -> 61.4 s, T_run >= 81.4 s (no 40 s levelling assumption)
    assert got[3] == pytest.approx((61.4, 81.4))
    # K24 references are the rev2 table values
    assert st.D8X_READY_REFS[("K24", "top", "fdown3.5")][0] == 77.5
    assert st.D8X_READY_REFS[("K24", "top", "fup3.5")][0] == 59.0
    assert st.D8X_READY_REFS[("K24", "top", "rpB")][0] == 57.8
    # every W / V candidate has a length
    for c in s8.d8x_cases():
        rec = s6.d8x_length_record(c.base)
        assert rec["run_s_matches"], c.case_id


def test_rev2_settle_scenario_records() -> None:
    plan = {r["row"]: r for r in s8.d8x_plan("r+p-0.5", "rpX")["rows"]}
    for n, r in plan.items():
        want = ("level", "top") if 7 <= n <= 11 else ("identity", None)
        assert (r["settle_map_expected"]["kind"], r["settle_map_expected"]["level"]) == want, n
    groups = {n: r["scenario_group"] for n, r in plan.items()}
    assert groups[1] == groups[14] == "G2-R" and groups[7] == "D8" and groups[11] == "G2-R"
    assert plan[1]["scenario_id"] == "H4V_top_fdown3.7" and plan[7]["scenario_id"] == "D8_top_fdown3.7"
    t6 = s6.case_table()
    assert t6["D8X_C1_H4V_top_fdown3.7"].d8x_scenario_id == "H4V_top_fdown3.7"
    assert s8.case_table()["D8X_K0V_top_fdown3.7_Fs0"].scenario.group == "G2-R"


@pytest.mark.skipif(not s6.d8x_mode_available(), reason="VERIFICATION_EXT not installed")
def test_rev2_meta_keys_and_refusals() -> None:
    from dataclasses import replace

    from outrigger_sim.params import load_params

    c6 = s6.case_table()["D8X_C1_H4V_top_fdown3.7"]
    cfg = s6.controller_config(load_params(level="top"), c6)
    meta = s6.d8x_meta(c6, cfg, None)
    for key in ("row", "slope_limit_mode", "floor_true_deg", "half_spans_deg", "level", "beta_GPa",
                "controller_tag", "liftoff_slow_enabled", "settle_map", "scenario_group", "scenario_id", "fs_kN"):
        assert key in meta, key
    assert meta["settle_map"]["kind"] == "level" and meta["settle_map"]["coefficients"]["k_dn"] > 0.0
    assert meta["liftoff_slow_enabled"] is True and meta["rev2_problems"] == []
    assert meta["scenario_group"] == "G2-R" and meta["scenario_id"] == "H4V_top_fdown3.7"
    assert meta["run_s"] == pytest.approx(109.6) and c6.duration_s == pytest.approx(109.6)
    # LAS-b off / another tag / wrong settle map -> refused before any run
    off = replace(cfg, liftoff_approach_slow=replace(cfg.liftoff_approach_slow, enable=False))
    with pytest.raises(SystemExit):
        s6.d8x_refuse(c6.case_id, s6.d8x_record(c6, off, None))
    with pytest.raises(SystemExit):
        s6.d8x_refuse(c6.case_id, s6.d8x_record(c6, cfg, "final_C4G2"))
    with pytest.raises(SystemExit):  # the tag before the K1 switch
        s6.d8x_refuse(c6.case_id, s6.d8x_record(c6, cfg, "final_C4G2_LAS"))
    ident = replace(cfg, target=replace(cfg.target, crawler_settle_map=None))
    rec = s6.d8x_record(c6, ident, None)
    assert any("E-4b" in p for p in rec["problems"])
    # L2b row: identity map, fs_kN recorded by run_S8C (d8x_meta fs_kN argument)
    c8 = s8.case_table()["D8X_K24_top_roll5.7_Fs4"]
    import run_S7C as s7c  # noqa: PLC0415

    cfg8, _ = s7c.apply_settle_map(s6.controller_config(load_params(level="top"), c8.base), "L2b_NSC", "top")
    m8 = s6.d8x_meta(c8.base, cfg8, None, fs_kN=c8.fs_kN)
    assert m8["settle_map"]["kind"] == "identity" and m8["fs_kN"] == 4.0 and m8["rev2_problems"] == []


def test_rev2_verify_metrics_j4_j10() -> None:
    import numpy as np

    from outrigger_sim.verify import s6_control as v

    t0 = 3.0
    t = np.arange(0.0, 20.0, 0.1)
    fz = np.where((t < 5.0) | ((t >= 12.0) & (t < 12.5)) | (t >= 18.0), 1.0e5, 0.0)
    rec = {"t": t + t0, "F_crawler": np.column_stack([np.zeros_like(t), np.zeros_like(t), fz])}
    events = ["C2Event(t_s=9.0, name='crawler_liftoff_confirmed')"]  # engine time -> 6.0 s
    err = np.zeros((t.size, 2))
    err[t >= 10.0, 0] = 0.05
    err[t >= 15.0, 1] = -0.12
    err[t < 10.0, 0] = 0.9  # before READY: not counted
    case = {"rec": rec, "events": events}
    tm = {"t0": t0, "ready": 10.0}
    out = v.d8x_metrics(case, t, err, tm)
    assert out["att_err_after_ready_maxabs_deg"] == pytest.approx(0.12)
    assert out["crawler_recontact_after_loc_count"] == 2 and out["crawler_recontact_anchor"] == "loc_event"
    assert out["crawler_recontact_t_s"] == pytest.approx([12.0, 18.0])
    out = v.d8x_metrics({"rec": rec, "events": []}, t, err, {"t0": t0, "ready": None})
    assert out["att_err_after_ready_maxabs_deg"] is None
    assert out["crawler_recontact_anchor"] == "first_crawler_off_edge"
    assert out["crawler_recontact_after_loc_count"] == 2


def test_earlier_case_controller_mode_unchanged() -> None:
    from outrigger_sim.control.target import SlopeLimitMode

    c = s6.case_table()["C1_D8_top_rpB_b1.6"]
    assert s6.slope_limit_mode(c) is SlopeLimitMode.VERIFICATION
    assert "slope_limit_mode" not in c.to_meta() and "d8x_row" not in c.to_meta()


@pytest.mark.skipif(not s6.d8x_mode_available(), reason="VERIFICATION_EXT not installed")
def test_rev3_k1_gate_recorded_from_the_controller() -> None:
    """Rev3 2 / E-6d (Chrono row): the ``d8x`` block records ``controller_tag`` (built from the controller's own
    config), ``k1_order_gate`` (``controller.config.slope_clearance_margin.flat_soil_margin_order_gate``),
    ``liftoff_slow_enabled``, and the gate read back from the run's controller meta; ``result.json``
    ``controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`` survives ``_plain`` / JSON.
    Chrono 19 rows run the preset as is (no install): expected tag ``final_C4G2_LAS_K1``."""
    from dataclasses import replace

    from outrigger_sim.control.c2 import C2Controller
    from outrigger_sim.hydraulics.v5_options import LAS_K1_CONTROLLER_TAG
    from outrigger_sim.params import load_params

    assert st.D8X_EXPECTED_TAG == LAS_K1_CONTROLLER_TAG == "final_C4G2_LAS_K1"
    c6 = s6.case_table()["D8X_C1_H4V_top_fdown3.7"]
    params = load_params(level="top")
    cfg = s6.controller_config(params, c6)
    c2 = C2Controller.from_params(params, cfg)
    ctl_meta = json.loads(json.dumps(s6._plain(c2.meta()), ensure_ascii=False))
    assert ctl_meta["slope_clearance_margin"]["settings"]["flat_soil_margin_order_gate"] is True
    meta = json.loads(json.dumps(s6._plain(s6.d8x_meta(c6, c2.config, None, controller_meta=ctl_meta))))
    assert meta["controller_tag"] == "final_C4G2_LAS_K1" and meta["expected_tag"] == "final_C4G2_LAS_K1"
    assert meta["k1_order_gate"] is True and meta["liftoff_slow_enabled"] is True
    assert meta["controller_meta_order_gate"] is True and meta["k1_order_gate_matches_meta"] is True
    assert meta["controller_tag_matches"] is True and meta["rev2_problems"] == []
    # without the controller meta: the gate of the config is still recorded, the read-back is None
    bare = s6.d8x_meta(c6, c2.config, None)
    assert bare["k1_order_gate"] is True and bare["controller_meta_order_gate"] is None
    assert bare["k1_order_gate_matches_meta"] is None
    assert s6.controller_meta_order_gate({}) is None and s6.controller_meta_order_gate(None) is None
    # gate off in the controller config: tag loses _K1, refused before any run (tag and E-6d)
    off = replace(cfg, slope_clearance_margin=replace(cfg.slope_clearance_margin,
                                                      flat_soil_margin_order_gate=False))
    c2_off = C2Controller.from_params(params, off)
    rec = s6.d8x_record(c6, c2_off.config, None)
    assert rec["k1_order_gate"] is False and rec["controller_tag"] == "final_C4G2_LAS"
    assert any("E-6d" in p for p in rec["problems"]) and any("controller tag" in p for p in rec["problems"])
    with pytest.raises(SystemExit):
        s6.d8x_refuse(c6.case_id, rec)
    m_off = s6.d8x_meta(c6, c2_off.config, None, controller_meta=c2_off.meta())
    assert m_off["controller_meta_order_gate"] is False and m_off["k1_order_gate_matches_meta"] is True
    # a mismatch between the config passed and the run's meta is recorded, not hidden
    mixed = s6.d8x_meta(c6, c2.config, None, controller_meta=c2_off.meta())
    assert mixed["k1_order_gate_matches_meta"] is False
    # preflight rows carry the gate too (run_S6C / run_S8C d8x_preflight copy the record)
    pre = s6.d8x_preflight([c6], None)
    assert pre["rows"][c6.case_id]["k1_order_gate"] is True
    assert pre["expected_tag"] == "final_C4G2_LAS_K1"
    # L2b row (run_S8C): same keys
    import run_S7C as s7c  # noqa: PLC0415

    c8 = s8.case_table()["D8X_K24_top_roll5.7_Fs4"]
    cfg8, _ = s7c.apply_settle_map(s6.controller_config(params, c8.base), "L2b_NSC", "top")
    c2_8 = C2Controller.from_params(params, cfg8)
    m8 = s6.d8x_meta(c8.base, c2_8.config, None, fs_kN=c8.fs_kN, controller_meta=c2_8.meta())
    assert m8["k1_order_gate"] is True and m8["controller_meta_order_gate"] is True
    assert m8["controller_tag"] == "final_C4G2_LAS_K1" and m8["rev2_problems"] == []
