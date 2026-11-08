"""las_chrono_records.py: event parsing and the T4h-like record of a Chrono run (J-6)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import las_chrono_records as lcr  # noqa: E402


def test_parse_events_reads_the_c2event_repr() -> None:
    lines = ["C2Event(t_s=27.999999999948084, name='crawler_liftoff_confirmed')",
             "C2Event(t_s=40.5, name='leg_reapproach_start:RR')"]
    assert lcr.parse_events(lines) == [(27.999999999948084, "crawler_liftoff_confirmed"),
                                       (40.5, "leg_reapproach_start:RR")]
    with pytest.raises(ValueError):
        lcr.parse_events(["something else"])


def _write_run(run_dir: Path, *, with_estimate: bool = True) -> None:
    run_dir.mkdir(parents=True)
    arrays = {"t": np.array([0.1, 0.2]), "phase": np.array(["level", "level"]),
              "issued_u": np.zeros((2, 4))}
    if with_estimate:
        arrays["F_lower_est_N"] = np.full((2, 4), 50e3)
    np.savez(run_dir / lcr.SERIES_NAME, **arrays)
    (run_dir / lcr.EVENTS_NAME).write_text(
        json.dumps(["C2Event(t_s=0.1, name='floor_estimate_touch')"]), encoding="utf-8")
    meta = {"controller_meta": {"geometry": {"F_min_N": 9414.589}, "period_s": 0.1,
                                "soil": {"settings": {"enable": True}}}}
    (run_dir / lcr.RESULT_NAME).write_text(json.dumps(meta), encoding="utf-8")


def test_convert_run_writes_what_the_shadow_judge_reads(tmp_path) -> None:
    run_dir = tmp_path / "batch" / "case"
    _write_run(run_dir)
    row = lcr.convert_run(run_dir, tmp_path / "out")
    assert row["status"] == "converted" and row["rows"] == 2
    with np.load(tmp_path / "out" / row["npz"], allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
        assert data["lower_estimate_N"].shape == (2, 4)
        assert list(data["phase"]) == ["level", "level"]
    assert meta["events"] == [[0.1, "floor_estimate_touch"]]
    assert meta["F_min_N"] == 9414.589 and meta["soil_enable"] is True


def test_a_run_without_the_estimate_is_not_convertible(tmp_path) -> None:
    run_dir = tmp_path / "batch" / "s9case"
    _write_run(run_dir, with_estimate=False)
    assert lcr.convert_run(run_dir, tmp_path / "out")["status"] == "not_convertible"
    assert lcr.find_run_dirs([tmp_path]) == [run_dir]
