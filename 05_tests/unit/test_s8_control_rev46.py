"""S8 judge rev. 46 (C-S8-22, ``s6_control_spec.md`` 216.7 ①-⑦, U-S8-21 / 24 / 25): pressure-only
comparison rows, grouped level trend, forced window, rod-pressure fallback warnings, C11 twins
from the reference batches, R46-1 friction flag, WIKA std pooled per side, ML judge."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
S8_DIR = ROOT / "07_results" / "S8"
P1R = S8_DIR / "p1r_20261024_222013"
REST = S8_DIR / "rest_20261024_233615"
CB = S8_DIR / "cb_20261025_000840"
ML = S8_DIR / "ml_pilot_20261025_002044"


def _rev46(p: Path) -> dict:
    doc = json.loads((p / "verify_S8C.json").read_text(encoding="utf-8"))
    if not str(doc["meta"].get("judge_revision", "")).startswith("spec rev. 46"):
        pytest.skip(f"{p.name} not re-judged with rev. 46")
    return doc


def test_friction_flag_r46_1() -> None:
    np.testing.assert_allclose(s8.friction_flag_limit_N([0.0, 1.0, 2e3, 6666.4]),
                               [100.0, 750.0, 750.0, 750.0])


def test_forced_window_re1c_and_ml() -> None:
    """RE1c: relative event time .. run end; ML retract: engine time - start; others None."""
    res = {"event_t_s": 47.6, "settings": {"start_t_s": 0.2, "s8": {
        "event": "RE1c", "event_spec": {"leg": "RR"}}}}
    t = np.arange(0.0, 100.0, 0.1) + 0.2
    u = np.zeros((t.size, 4))
    u[(t - 0.2 >= 47.6) & (t - 0.2 <= 52.4), 3] = -5e-3
    fw = s8.forced_window(res, 92.6, {"t": t, "issued_u": u})
    assert fw["start_s"] == 47.6 and fw["end_s"] == 92.6 and fw["leg"] == "RR"
    assert fw["done_s"] == pytest.approx(52.4, abs=0.11)
    ml = {"event_t_s": 61.0, "settings": {"start_t_s": 3.0, "episode": {"kind": "retract",
                                                                         "leg": "RL"}}}
    assert s8.forced_window(ml, 89.0)["start_s"] == pytest.approx(58.0)
    assert s8.forced_window({"event_t_s": 5.0, "settings": {"s8": {"event": "G4"}}}, 9.0) is None
    m = s8.forced_mask(np.array([57.0, 58.0, 89.0, 91.9, 92.1]), s8.forced_window(ml, 89.0),
                       extra_s=3.0)
    assert m.tolist() == [False, True, True, True, False]


def test_rod_fallback_events_split_by_window() -> None:
    ev = [(26.2, "WARN_ROD_PRESSURE_FALLBACK:RR"), (26.2, "INFO_ROD_PRESSURE_FAULT_REASON:RR:D2"),
          (51.8, "WARN_ROD_PRESSURE_FALLBACK:FL"), (51.8, "INFO_ROD_PRESSURE_FAULT_REASON:FL:D2")]
    out = s8.rod_fallback_events(ev, {"start_s": 47.6, "end_s": 92.6})
    assert [(e["leg"], e["reason"], e["in_forced_window"]) for e in out] == [
        ("RR", "D2", False), ("FL", "D2", True)]
    assert s8.rod_fault_injected({"a": {"rod_sensor_fault": {"leg": 1}}}) is True
    assert s8.rod_fault_injected({"s8": {"event": "G4"}}) is False


def test_pooled_side_std_exact() -> None:
    rng = np.random.default_rng(5)
    laws, data = [], []
    for _ in range(2):
        x = rng.normal([10.0, -5.0, 3.0, 0.0], [276.0, 270.0, 200.0, 205.0], (700, 4))
        m = s8.f1_law_metrics(x, np.array([276.0, 276.0, 200.0, 200.0]), np.ones(700, bool))
        laws.append({"metrics": m})
        data.append(x)
    p = s8.pooled_side_std(laws)
    allx = np.concatenate(data)
    assert p["front"]["std_N"] == pytest.approx(allx[:, :2].std(ddof=1), rel=1e-12)
    assert p["rear"]["n"] == 2800


def test_apply_rev46_rows_pressure_comparison_and_fallback() -> None:
    sms = {"N": {"s8": {"contact": "pressure"}, "rod_fallback": {"events": []}},
           "C": {"s8": {"contact": "combined"}, "rod_fallback": {
               "events": [{"t_s": 26.2, "leg": "RR", "reason": "D2", "in_forced_window": False}],
               "injected": False}}}
    rows = [s8._row("3 F_min (1 ms)", "N", 6.5, 9.4, False, kind="function"),
            s8._row("G4 item 6 (1) min after settlement >= F_min", "N", 6.5, 9.4, False),
            s8._row("3 F_min (1 ms)", "C", 12.0, 9.4, True, kind="function"),
            s8._row(s8.DIAG_ITEM, "C", {"WARN_PRESSURE_DRIFT": 0}, "0", True, kind="function"),
            s8._row(s8.WARN_ITEM, "C", 0, 0, True, kind="anomaly")]
    extra = s8.apply_rev46_rows(rows, sms)
    assert [r["passed"] for r in rows[:2]] == [None, None]
    assert [r["kind"] for r in rows[:2]] == ["comparison", "comparison"]
    assert rows[0]["passed_raw"] is False and rows[2]["passed"] is True
    assert rows[3]["passed"] is False and rows[3]["value"][s8.ROD_FALLBACK_WARNING] == 1
    assert rows[4]["value"] == 1 and "FLAG" in rows[4]["note"]
    assert extra == []


def test_level_trend_groups_and_reference_levels() -> None:
    def m(cid, level, v, fs=0.0, contact="combined", beta=1.0):
        return ({"case": cid, "group": "D8", "floor": "rpB", "level": level,
                 "min_cyl_excl_reanchor_kN": v, "F_min_N": 9414.59, "contact": contact},
                {"s8": {"fs_kN": fs, "contact": contact, "condition": "judged",
                        "engine": "L2b_NSC", "lock_valve": "pilot_check",
                        "base": {"beta_GPa": beta, "sensor_model": False}}})
    here = [m("A_bottom", "bottom", 44.5), m("A_middle", "middle", 41.9),
            m("N_top_p", "top", 99.0, contact="pressure")]
    ref = [m("K0V_top", "top", 35.7), m("K8_top", "top", 37.7, fs=8.0)]
    doc = {"metrics": [x[0] for x in ref], "s8_metrics": {x[0]["case"]: x[1] for x in ref}}
    rows = s8.level_trend_rows_s8([x[0] for x in here], {x[0]["case"]: x[1] for x in here},
                                  [("batch ref", doc)])
    trend = [r for r in rows if r["item"] == s8.TREND_ITEM_S8]
    assert len(trend) == 1 and trend[0]["case"].startswith("rpB F_s 0")
    assert trend[0]["value"] == {"bottom": 44.5, "middle": 41.9, "top": 35.7}
    assert trend[0]["passed"] is True


@pytest.mark.skipif(not (REST / "verify_S8C.json").exists(), reason="rest not present")
def test_rest_rev46_zero_failures() -> None:
    """C-S8-22 ①-③: rest re-judged (ref p1r) has no failed row; RE1c forced-window rows."""
    doc = _rev46(REST)
    assert doc["meta"]["failed"] == 0
    assert (REST / "verify_S8C_rev45judge.json").exists()
    forced = [r for r in doc["rows"] if r["item"] == s8.F2_FORCED_ITEM]
    assert {r["case"] for r in forced} == {"N_RE1c_Fs0_combined", "N_RE1c_Fs8_combined"}
    trend = [r for r in doc["rows"] if r["item"] == s8.TREND_ITEM_S8 and r["passed"] is not None]
    assert len(trend) == 4 and all(r["passed"] for r in trend)
    near = [r for r in doc["rows"] if r["item"].startswith("F1 near F_min") and r.get("flag")]
    assert near == []


@pytest.mark.skipif(not (P1R / "verify_S8C.json").exists(), reason="p1r not present")
def test_p1r_rev46_c11_twins_from_rest() -> None:
    """C-S8-22 ⑤: p1r (lookup rest) has the C11 rows of the four K0 cases with a twin value."""
    doc = _rev46(P1R)
    assert doc["meta"]["failed"] == 0
    c11 = [r for r in doc["rows"] if r["item"] == "C11 L2b - L1: min slow (1 s) after lift-off [kN]"]
    assert len(c11) == 4 and all(r["value"] is not None for r in c11)


@pytest.mark.skipif(not (CB / "verify_S8C.json").exists(), reason="CB not present")
def test_cb_rev46_fallback_caught() -> None:
    """C-S8-22 ④: the two CB F_s 0 false fallbacks fail the 72.1 (6) row (+ F2 as before)."""
    doc = _rev46(CB)
    diag = [r["case"] for r in doc["rows"] if r["item"] == s8.DIAG_ITEM and r["passed"] is False]
    assert sorted(diag) == ["CB_G4_Fs0", "CB_RE1bF_Fs0"]


@pytest.mark.skipif(not (ML / "verify_S8ML.json").exists(), reason="ML pilot not judged")
def test_ml_judge_rows() -> None:
    doc = json.loads((ML / "verify_S8ML.json").read_text(encoding="utf-8"))
    items = {r["item"].split(" ")[0] + " " + r["item"].split(" ")[1] for r in doc["rows"]}
    assert {"ML-0 base", "ML-0 episode", "ML-3 R45-4"} <= items
    base = next(r for r in doc["rows"] if r["item"].startswith("ML-0 base"))
    assert base["passed"] is True
    for mask in doc["ml_masks"].values():
        assert mask["end_s"] > mask["start_s"]


def test_ml_run_status(tmp_path: Path) -> None:
    ok = tmp_path / "ok"
    ok.mkdir()
    (ok / "case.log").write_text("x INFO outrigger_sim.batch: case ok finished: ok\n", "utf-8")
    (ok / "result.json").write_text("{}", "utf-8")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "case.log").write_text("x ERROR outrigger_sim.batch: case bad failed\nAttributeError: "
                                  "boom\nx INFO outrigger_sim.batch: case bad finished: failed\n",
                                  "utf-8")
    run = tmp_path / "run"
    run.mkdir()
    (run / "case.log").write_text("x INFO outrigger_sim.batch: case run started\n", "utf-8")
    assert s8.ml_run_status(ok)["status"] == "ok"
    st = s8.ml_run_status(bad)
    assert st["status"] == "failed" and "AttributeError" in st["error"]
    assert s8.ml_run_status(run)["status"] == "running"
