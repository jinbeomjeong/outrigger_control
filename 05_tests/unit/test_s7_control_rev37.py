"""Spec rev. 37 196.1 cad work (no Chrono run): C-R16 (A1 rejection of a rigid-crawler case
judged with the identity map), C-R17 (``run_S7C.py`` identity settle map for L2b, ``ctrl3_rerun``
set), C-R18 (slow component of the D8 pair difference), C-R19 (sensitivity D8 / REANCHOR rows
reported)."""

from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s6_bundle_c as bc
from outrigger_sim.verify.s7_control import (
    OSC_WINDOW_S,
    centred_mean,
    slow_force_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"


@pytest.fixture(scope="module")
def run_s7c():
    """Load ``run_S7C.py`` as a module; import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S7C_test37", SCRIPTS / "run_S7C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


# --- C-R17 ---------------------------------------------------------------------------------


def test_settle_map_by_engine(run_s7c) -> None:
    from outrigger_sim.control.target import CrawlerSettleMap

    kind, smap = run_s7c.controller_settle_map("L2b_NSC", "top")
    assert kind == "identity" and smap.is_identity
    kind, smap = run_s7c.controller_settle_map("L1R", "top")
    assert kind == "level" and smap == CrawlerSettleMap.for_level("top")
    assert not smap.is_identity


def test_apply_settle_map_l2b_identity(run_s7c) -> None:
    """The L2b controller config differs from the L1 twin's only in the settle map."""
    from outrigger_sim.params import load_params

    cases = {c.case_id: c for c in run_s7c.ctrl3_cases()}
    l2b = cases["L2b_D8_top_fup3.5_b1.0"]
    params = load_params(level="top")
    base = run_s7c.s6c.controller_config(params, l2b.base)
    assert base.target.crawler_settle_map is not None  # the L1 (13.1) map
    cfg, meta = run_s7c.apply_settle_map(base, "L2b_NSC", "top")
    assert cfg.target.crawler_settle_map is None and cfg.target.settle_map.is_identity
    assert meta["kind"] == "identity" and meta["coefficients"]["k_up"] == 0.0
    from dataclasses import replace

    assert cfg == replace(base, target=replace(base.target, crawler_settle_map=None))
    cfg1, meta1 = run_s7c.apply_settle_map(base, "L1R", "top")
    assert cfg1 == base and meta1["kind"] == "level"


def test_ctrl3_rerun_set(run_s7c) -> None:
    rerun = run_s7c.ctrl3_rerun_cases()
    assert [c.case_id for c in rerun] == ["L2b_D8_top_fup3.5_b1.0", "L2b_D8_top_roll5.5_b1.0"]
    base = run_s7c.case_table("ctrl3")
    for c in rerun:
        assert c.engine == "L2b_NSC" and c.pair_batch == run_s7c.CTRL3_PAIR_BATCH
        assert c.pair_l1 == c.case_id.replace("L2b_", "L1_", 1)
        assert c.base == base[c.case_id].base  # same scenario as the ctrl3 run
        meta = c.to_meta()
        assert meta["controller_settle_map"] == "identity"
        assert meta["pair_batch"] == run_s7c.CTRL3_PAIR_BATCH
    assert set(run_s7c.case_table("ctrl3_rerun")) == {c.case_id for c in rerun}
    for c in run_s7c.ctrl3_cases():
        want = "identity" if c.engine == "L2b_NSC" else "level"
        assert c.to_meta()["controller_settle_map"] == want


# --- C-R16 ---------------------------------------------------------------------------------


def _reject_metrics(u_ctrl, u_map, u_true, *, identity_map: bool, basis: str):
    ca = {"code": bc.REJ_SLOPE_D8, "usage_controller": u_ctrl, "usage_truth_crawler": u_map,
          "usage_truth": u_true, "usage_truth_identity": u_true, "usage_floor_nominal": 1.0,
          "usage_tolerance": 0.01, "error_deg": [0.001, 0.003],
          "settle_map_is_identity": identity_map, "truth_map_basis": basis}
    return {"final_phase": "idle", "check_attitude": ca}


def test_a1_reject_settle_map_mismatch() -> None:
    """ctrl3 L2b fup3.5: controller 1.0235, run map 1.0242, identity 1.0000 -> false rejection
    (settle map mismatch), failed."""
    row = {"item": "run", "value": "idle", "passed": False, "note": "", "kind": "function"}
    bc._a1_reject_run_row(row, _reject_metrics(1.0235, 1.0242, 1.0000, identity_map=False,
                                               basis="identity (rigid crawler)"))
    assert row["passed"] is False
    assert row["note"].startswith("false rejection (settle map mismatch)")
    assert row["value"]["usage_truth"] == pytest.approx(1.0)


def test_a1_reject_controller_error_and_correct() -> None:
    row = {"item": "run", "value": "idle", "passed": False, "note": "", "kind": "function"}
    bc._a1_reject_run_row(row, _reject_metrics(1.02, 1.005, 1.005, identity_map=False,
                                               basis="run settle map"))
    assert row["note"].startswith("false rejection (controller CHECK error)")
    row = {"item": "run", "value": "idle", "passed": False, "note": "", "kind": "function"}
    bc._a1_reject_run_row(row, _reject_metrics(1.05, 1.04, 1.04, identity_map=True,
                                               basis="run settle map"))
    assert row["passed"] is None and row["kind"] == "info"
    assert row["note"].startswith("correct rejection")


def test_a1_reject_old_metrics_without_usage_truth() -> None:
    """Metrics written before C-R16 (no ``usage_truth``) keep the run-map rule."""
    m = _reject_metrics(1.02, 1.02, None, identity_map=False, basis="x")
    for k in ("usage_truth", "usage_truth_identity", "settle_map_is_identity", "truth_map_basis"):
        m["check_attitude"].pop(k)
    row = {"item": "run", "value": "idle", "passed": False, "note": "", "kind": "function"}
    bc._a1_reject_run_row(row, m)
    assert row["passed"] is None and row["kind"] == "info"


def test_identity_engines() -> None:
    assert "L2b_NSC" in bc.IDENTITY_PHYSICAL_MAP_ENGINES
    assert "L1R" not in bc.IDENTITY_PHYSICAL_MAP_ENGINES


# --- C-R18 ---------------------------------------------------------------------------------


def test_centred_mean_odd_and_truncated() -> None:
    x = np.arange(10.0)
    y = centred_mean(x, 3)
    assert y[5] == pytest.approx(5.0)
    assert y[0] == pytest.approx(0.5) and y[9] == pytest.approx(8.5)
    assert np.allclose(centred_mean(x, 4), centred_mean(x, 5))  # made odd
    assert np.array_equal(centred_mean(x, 1), x)


def test_slow_force_metrics_split() -> None:
    """Slow ramp + 2 Hz ripple: the 1 s centred mean removes the ripple (two whole periods),
    the half-amplitude is the ripple amplitude, the late window reads the raw minimum."""
    dt = 1e-3
    t = np.arange(0.0, 20.0, dt)
    # 50 -> 48 kN over 5..7 s, 48 kN on 7..10 s, back to 50 kN by 12 s
    slow = 50e3 - 1e3 * np.clip(t - 5.0, 0.0, 2.0) + 1e3 * np.clip(t - 10.0, 0.0, 2.0)
    # ripple 5..12 s: the windows across its start / end keep a partial-cycle mean (<= 0.3 kN);
    # they lie where the slow part is >= 49 kN, so the 48 kN plateau stays the minimum
    ripple = np.where((t >= 5.0) & (t < 12.0), 4e3 * np.sin(2 * math.pi * 2.0 * t), 0.0)
    f = np.stack([slow + ripple, slow + 0.5 * ripple, slow + 10e3, slow + 10e3], axis=1)
    out = slow_force_metrics(t, f, 5.0, 15.0)
    assert out["slow_window_samples"] == 1001
    assert out["min_cyl_slow_after_liftoff_kN"] == pytest.approx(48.0, abs=0.05)
    assert out["min_cyl_slow_leg"] in ("FL", "FR")
    amp = out["osc_half_amp_kN"]
    # coarse index (spec 193.2): onset partial cycle and the ramp corner at 7 s add <= 0.3 kN
    assert amp[0] == pytest.approx(4.0, abs=0.3) and amp[1] == pytest.approx(2.0, abs=0.3)
    assert amp[2] < 0.15 and amp[3] < 0.15
    # late window [10, 15] s: first ripple trough at 10.375 s, slow 48.375 kN - 4 kN
    assert out["min_cyl_late_kN"] == pytest.approx(44.375, abs=0.01)
    assert OSC_WINDOW_S == (0.0, 3.0)
    assert slow_force_metrics(t, f, None, 15.0) == {}
    assert "min_cyl_late_kN" not in slow_force_metrics(t, f, 5.0, None)


# --- C-R19 ---------------------------------------------------------------------------------


def test_sensitivity_force_rows_reported() -> None:
    by_id = {"S": {"condition": "sensitivity", "condition_reasons": ["zero calibration off"]},
             "B": {"condition": "base"}}
    rows = [
        {"item": "D8 min true cylinder force >= F_min + 5 kN", "case": "S", "passed": False,
         "note": "", "kind": "judged"},
        {"item": "REANCHOR min >= F_min + 7 kN", "case": "S", "passed": False, "note": "x",
         "kind": "judged"},
        {"item": "D8 no pad lift-off", "case": "S", "passed": True, "note": "",
         "kind": "judged"},
        {"item": "D8 min true cylinder force >= F_min + 5 kN", "case": "B", "passed": False,
         "note": "", "kind": "judged"},
    ]
    bc.report_sensitivity_force_rows(rows, by_id)
    assert [r["passed"] for r in rows] == [None, None, True, False]
    assert rows[0]["kind"] == "report" and rows[0]["passed_raw"] is False
    assert "sensitivity (103.2)" in rows[0]["note"] and rows[1]["note"].endswith("; x")
    assert rows[2]["kind"] == "judged" and rows[3]["kind"] == "judged"


# --- re-judged ctrl3 batch (skipped when the local result folder is absent) -------------------

CTRL3 = ROOT / "07_results" / "S7" / "ctrl3_20261024_154939"


@pytest.mark.skipif(not (CTRL3 / "verify_S7C.json").exists(), reason="ctrl3 batch not present")
def test_ctrl3_rejudged_file() -> None:
    """The rev. 37 judgement of the ctrl3 batch (written by ``run_S7C.py judge``)."""
    import json

    doc = json.loads((CTRL3 / "verify_S7C.json").read_text(encoding="utf-8"))
    if "pair_flag_basis" not in doc["meta"]:
        pytest.skip("verify_S7C.json predates rev. 37")
    rows = doc["rows"]
    failed = [(r["case"], r["item"]) for r in rows if r["passed"] is False]
    assert sorted(failed) == [("L2b_D8_top_fup3.5_b1.0", "run"),
                              ("L2b_D8_top_roll5.5_b1.0", "run")]
    for cid, _ in failed:
        row = next(r for r in rows if r["case"] == cid and r["item"] == "run")
        assert row["note"].startswith("false rejection (settle map mismatch)")
    rpb = next(r for r in rows if r["case"] == "L2b_D8_top_rpB_b1.0"
               and r["item"].endswith("1 s centred mean [kN]"))
    assert rpb["value"] == pytest.approx(-0.94, abs=0.05) and rpb["pair_flag"] is False
    assert doc["meta"]["pair_flags"] == []
