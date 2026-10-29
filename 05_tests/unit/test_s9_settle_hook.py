"""S9 reduced harness settle hook (``04_scripts/03_control/s9/s9_soil_closed_loop.py``).

"p0" (default) keeps the flat P0 soil-minus-rigid settle of every result up to rev. 79; "harness"
takes the dynamics row ``hook_harness`` of ``slope_crawler_settle.json``. The settle check runs the
harness plant through the crawler settle (numba, about 10 s per case) and compares the settle state
with the row targets on a flat floor. Run in dynamics-dev (numba)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba")

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_soil_closed_loop as sl  # noqa: E402

ATTITUDE_TOL_DEG = 0.001
GAP_TOL_MM = 0.1
FLAT = (0.0, 0.0)
SETTLE_CASES = [("G1", "top"), ("J1", "top"), ("S1", "top"), ("J2", "bottom")]


def _table_rows() -> dict:
    table = json.loads(sl.DEFAULT_SETTLE_TABLE.read_text(encoding="utf-8"))
    return table[sl.SETTLE_TABLE_BLOCK]


@pytest.fixture(scope="module")
def harness():
    """The harness modules (``c2py_r8d1_closed_loop`` patches its own imports)."""
    cl, _, _ = sl._imports()
    return cl


def _settled_plant(cl, soil: str, level: str, hook: str):
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = sl.make_plant(cl, level, soil, "B", 4.0, slope=FLAT, settle_hook=hook)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    return plant


# ------------------------------------------------------------------------------ hook selection
def test_hook_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sl.SETTLE_HOOK_ENV, raising=False)
    assert sl.resolve_settle_hook() == "p0"
    monkeypatch.setenv(sl.SETTLE_HOOK_ENV, "harness")
    assert sl.resolve_settle_hook() == "harness"
    assert sl.resolve_settle_hook("p0") == "p0"  # the argument wins over the environment
    with pytest.raises(ValueError, match="settle hook"):
        sl.resolve_settle_hook("chrono")


def test_table_row_lookup() -> None:
    assert sl.settle_table_key("J1", "top", (2.7355, 1.7592)) == "J1|top|2.7355|1.7592"
    assert sl.settle_table_key("G1", "top", (0, 3.2)) == "G1|top|0|3.2"
    row = sl.load_settle_row("G1", "top", FLAT)
    assert row == _table_rows()["G1|top|0|0"]
    with pytest.raises(KeyError, match="no hook_harness row"):
        sl.load_settle_row("G1", "top", (0.0, 9.9))


def test_p0_pads_unchanged_and_harness_pads_from_table() -> None:
    pad_xy = np.array([[2.0, 1.5], [2.0, -1.5], [-2.0, 1.5], [-2.0, -1.5]])
    ks = np.full(4, 1.0e8)
    p0_pads = sl.SoilPads("J1", "B", pad_xy, ks)
    soil, rigid = sl.P0_SETTLE["J1"]["q"], sl.P0_SETTLE["rigid"]["q"]
    dtheta = soil[2] - rigid[2]
    assert p0_pads.settle_row is None
    assert np.array_equal(p0_pads.h, (rigid[0] - soil[0]) + pad_xy[:, 0] * math.tan(dtheta))
    row = _table_rows()["J1|top|0|0"]
    table_pads = sl.SoilPads("J1", "B", pad_xy, ks, settle_row=row)
    assert np.array_equal(table_pads.h, np.asarray(row["pad_h_m"], float))


def test_settle_row_needs_the_harness_hook(harness) -> None:
    row = _table_rows()["G1|top|0|0"]
    with pytest.raises(ValueError, match="settle_row needs"):
        sl.make_plant(harness, "top", "G1", "B", 0.0, settle_hook="p0", settle_row=row)


def test_rigid_floor_ignores_the_hook(harness) -> None:
    p0 = sl.make_plant(harness, "top", "rigid", "B", 0.0, settle_hook="p0")
    table = sl.make_plant(harness, "top", "rigid", "B", 0.0, settle_hook="harness")
    assert table.soil is None and table.settle_info["row_key"] is None
    assert np.array_equal(np.asarray(p0.nrm), np.asarray(table.nrm))


# ------------------------------------------------------------------------------ settle check
@pytest.mark.parametrize(("soil", "level"), SETTLE_CASES)
def test_harness_settle_meets_the_table_targets(harness, soil: str, level: str) -> None:
    plant = _settled_plant(harness, soil, level, "harness")
    snap = sl.settle_snapshot(harness, plant)
    assert snap["hook"] == "harness" and snap["row_key"] == f"{soil}|{level}|0|0"
    assert np.max(np.abs(snap["att_error_deg"])) <= ATTITUDE_TOL_DEG, snap["att_error_deg"]
    assert np.max(np.abs(snap["gap_error_mm"])) <= GAP_TOL_MM, snap["gap_error_mm"]


def test_p0_settle_keeps_the_flat_bias(harness) -> None:
    """The bias the hook removes: on G1 top the p0 settle is about 0.11 deg less nose down and
    the front pads sit about 8 mm higher than the P0 soil settle."""
    plant = _settled_plant(harness, "G1", "top", "p0")
    snap = sl.settle_snapshot(harness, plant)
    row = _table_rows()["G1|top|0|0"]
    pitch_error_deg = snap["att_floor_deg"][1] - math.degrees(row["target_q_floor"][2])
    front_gap_error_mm = np.mean(snap["gap_mm"][:2]) - np.mean(row["gap_target_mm"][:2])
    assert snap["hook"] == "p0" and "att_error_deg" not in snap
    assert pitch_error_deg == pytest.approx(-0.11, abs=0.02)
    assert front_gap_error_mm == pytest.approx(8.5, abs=1.5)
