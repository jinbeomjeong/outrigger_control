"""V5-LAS-CHRONO rows (cad 2026-11-08): LAS-b off / on Chrono check rows, definitions only (no Chrono step)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

pytest.importorskip("pychrono")

import las_chrono_rows as las  # noqa: E402
import run_S9 as r9  # noqa: E402
import s9_batch as sb  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    return sb.batches()[las.LAS_BATCH]


def _arg(argv, key):
    return argv[argv.index(key) + 1]


def test_four_rows_two_pairs(rows) -> None:
    assert len(rows) == 4
    assert sorted((r["las_crawler"], r["las"]) for r in rows) == [("K1", "off"), ("K1", "on"), ("K3", "off"),
                                                                    ("K3", "on")]
    assert not any(r.get("optional") for r in rows)  # all four required (user decision 2026-11-08)
    assert [r["case"] for r in rows][:2] == [
        "LASC_rigid_J1FR_B_top_Fs4_r2p3351_p1p5017_K1_lasoff", "LASC_rigid_J1FR_B_top_Fs4_r2p3351_p1p5017_K1_lason"]
    names = {r["case"] for r in rows}
    assert all(r["pair_case"] in names and r["pair_case"] != r["case"] for r in rows)


def test_argv_settings(rows) -> None:
    for r in rows:
        a = r["argv"]
        assert _arg(a, "--soil") == "J1" and _arg(a, "--rigid-base") == "FR" and _arg(a, "--grid") == "0.01"
        assert "--soil-patch" not in a and "--crawler-grid" not in a
        assert _arg(a, "--floor-roll") == "2.3351" and _arg(a, "--floor-pitch") == "1.5017"
        assert _arg(a, "--threads") == str(r9.SCM_THREADS_FIXED)
        assert _arg(a, "--start-limit") == r9.S9SL_START_LIMIT and _arg(a, "--duration") == "160"
        assert _arg(a, "--expect-controller") == r["controller"]
        assert a[-len(sb.v5_vb_argv()):] == sb.v5_vb_argv()
        assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE"}
        assert "--soil-override" not in a
        assert ("--crawler-kn-scale" in a) is (r["las_crawler"] == "K3")
        if r["las_crawler"] == "K3":
            assert float(_arg(a, "--crawler-kn-scale")) == 3.0
        # the two rows of a pair differ only by the controller tag (and the pre-LAS runner after the merge)
        other = next(o for o in rows if o["case"] == r["pair_case"])
        strip = [t for t in sb.strip_controller_check(a) if t != str(las.PRE_LAS_RUNNER)]
        assert strip == [t for t in sb.strip_controller_check(other["argv"]) if t != str(las.PRE_LAS_RUNNER)]


def test_merge_state(rows) -> None:
    merged = las.las_merged()
    for r in rows:
        if r["las"] == "off":
            assert r["controller"] == "final_C4G2_P3" and r["las_ready"]
            assert (str(las.PRE_LAS_RUNNER) in r["argv"]) is merged
        else:
            assert r["controller"] == "final_C4G2_P3_LAS" and r["las_ready"] is merged


def test_check_sources_ok(rows) -> None:
    """Off rows (pre-LAS runner) pass; since the K1 switch (``las_k1_rules_adopt.md`` 9.2) the on rows' tag
    ``final_C4G2_P3_LAS`` checks the order gate off, so the plain on rows are refused at that path only (a
    reproduction runs through ``pre_k1_preset_runner.py``)."""
    doc = sb.check_sources(las.LAS_BATCH, rows)
    for res in doc["rows"]:
        r = next(x for x in rows if x["case"] == res["case"])
        if not r["las_ready"]:
            assert res["status"] == "blocked_pre_merge"
        elif r["las"] == "off":
            assert res["status"] == "ok", res
        else:
            assert res["status"] == "differs", res
            (diff,) = res["diffs"]
            assert [c["path"] for c in diff["row"]] == [
                "slope_clearance_margin.flat_soil_margin_order_gate"]
    assert doc["ok"] is all(r["las"] == "off" or not r["las_ready"] for r in rows)


def test_case_env_start_env() -> None:
    env = sb._case_env("pcore", {"OMP_WAIT_POLICY": "PASSIVE"})
    assert env["OMP_WAIT_POLICY"] == "PASSIVE" and env[r9.PLACEMENT_ENV] == "pcore"


def test_run_refuses_blocked_rows(rows) -> None:
    if las.las_merged():
        pytest.skip("LAS-b merged: no blocked row")
    with pytest.raises(SystemExit, match="LAS-b"):
        sb.run_batch(las.LAS_BATCH)


def test_run_s9_main_default_argv() -> None:
    import inspect

    assert inspect.signature(r9.main).parameters["argv"].default is None
