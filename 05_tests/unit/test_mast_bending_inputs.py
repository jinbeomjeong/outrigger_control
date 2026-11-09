"""R8 C2 inputs of ``04_scripts/01_dynamics/run_mast_bending_check.py``.

* ``control_crossover.load_levelling_crossover`` replaces the R7 crossover constant 0.064 Hz
  with the pad-supported maximum of ``r8d1_final.json`` (small temporary JSON files, plus the
  project file against the control-expert value 0.2049 rad/s).
* ``TAU_FILTER`` is a copy of ``c2.R8_D1_ATTITUDE_TIME_CONSTANT_S`` (the script does not import
  03_src), so the two must agree.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))

import control_crossover as cc  # noqa: E402

# control-expert check 2026-11-09: max pad-supported wgc of C2_tv0.1 (roll / pitch)
PROJECT_CROSSOVER_RAD_S = 0.2049
PROJECT_CROSSOVER_HZ = 0.0326


def _row(name: str, phi: float, theta: float) -> list[Any]:
    return [name, {cc.CONTROLLER_KEY: {cc.CROSSOVER_KEY: {"z": 0.5, "phi": phi, "theta": theta}}}]


ROWS: dict[str, Any] = {
    "cfgs": {},
    "summary": {},
    "rows": [
        _row("top_pads_b1_rigid", 0.2039, 0.2027),
        _row("top_pads_b1_sup_lower_k0.5-1-1-0.5", 0.2049, 0.2030),
        _row("bottom_pads_b0.69_rigid", 0.2035, 0.2026),
        # crawler-supported rows are excluded even where they are larger in pitch
        _row("top_crawler_b1_rigid", 0.1072, 0.2100),
    ],
}


def _write(tmp_path: Path, tree: Any) -> Path:
    path = tmp_path / "r8d1_final.json"
    path.write_text(json.dumps(tree), encoding="utf-8")
    return path


def test_crossover_is_pad_maximum(tmp_path: Path) -> None:
    path = _write(tmp_path, ROWS)
    result = cc.load_levelling_crossover(path)
    assert result.crossover_rad_s == 0.2049
    assert result.crossover_hz == pytest.approx(0.2049 / (2 * math.pi), rel=1e-15)
    assert (result.row_name, result.axis) == ("top_pads_b1_sup_lower_k0.5-1-1-0.5", "phi")
    assert result.n_pad_rows == 3
    assert result.crawler_min_hz == pytest.approx(0.1072 / (2 * math.pi), rel=1e-15)
    assert result.source["n_crawler_rows_excluded"] == 1
    assert result.source["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_crossover_key_raises(tmp_path: Path) -> None:
    tree = copy.deepcopy(ROWS)
    del tree["rows"][2][1][cc.CONTROLLER_KEY][cc.CROSSOVER_KEY]["theta"]
    with pytest.raises(cc.ControlCrossoverError, match="theta"):
        cc.load_levelling_crossover(_write(tmp_path, tree))


def test_missing_controller_raises(tmp_path: Path) -> None:
    tree = copy.deepcopy(ROWS)
    del tree["rows"][0][1][cc.CONTROLLER_KEY]
    with pytest.raises(cc.ControlCrossoverError, match=cc.CONTROLLER_KEY):
        cc.load_levelling_crossover(_write(tmp_path, tree))


def test_no_pad_row_raises(tmp_path: Path) -> None:
    tree = {"rows": [_row("top_crawler_b1_rigid", 0.1072, 0.19)]}
    with pytest.raises(cc.ControlCrossoverError, match="no pad-supported row"):
        cc.load_levelling_crossover(_write(tmp_path, tree))


def test_unknown_support_token_raises(tmp_path: Path) -> None:
    tree = copy.deepcopy(ROWS)
    tree["rows"].append(_row("top_tracks_b1_rigid", 0.3, 0.3))
    with pytest.raises(cc.ControlCrossoverError, match="tracks"):
        cc.load_levelling_crossover(_write(tmp_path, tree))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(cc.ControlCrossoverError, match="not found"):
        cc.load_levelling_crossover(tmp_path / "absent.json")


def test_project_crossover_matches_control_expert() -> None:
    result = cc.load_levelling_crossover()
    assert result.crossover_rad_s == pytest.approx(PROJECT_CROSSOVER_RAD_S, abs=5e-5)
    assert result.crossover_hz == pytest.approx(PROJECT_CROSSOVER_HZ, abs=5e-5)
    assert result.row_name.split("_")[1] == cc.PAD_SUPPORT


def test_filter_tau_matches_c2() -> None:
    pytest.importorskip("scipy")
    import run_mast_bending_check as mbc

    from outrigger_sim.control import c2

    assert mbc.TAU_FILTER == c2.R8_D1_ATTITUDE_TIME_CONSTANT_S
    assert mbc.CONTROL_PERIOD_S == c2.R8_PERIOD_S
    assert mbc.TAU_FILTERS[0] == mbc.TAU_FILTER
    assert mbc.filtered_tilt_key(2.0, mbc.TAU_FILTER) == (
        "filtered_IMU_tilt_dev_max_deg_after_last_stop+2s (roll, pitch)"
    )
    assert mbc.filtered_tilt_key(2.0, 0.5) == (
        "filtered_IMU_tilt_dev_max_deg_after_last_stop+2s_tau0.5 (roll, pitch)"
    )
