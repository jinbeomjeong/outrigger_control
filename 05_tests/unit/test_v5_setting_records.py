"""v5 harness run records (user decisions 2026-11-08): the E-6 pressure-zero allowance record and
its use by ``t4h_replay``.

The harness runs go through ``v5_setting_run_runner.py`` in dynamics-dev (numba harness) and are
compared with the stored ``run_v5`` batch lines (``06_analysis/.../v5/main.jsonl``, git-ignored:
skipped when absent).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
RUNNER = Path(__file__).resolve().with_name("v5_setting_run_runner.py")
TIMEOUT_S = 900
FAILURE_ALLOWANCE_N = (5500.0, 5500.0, 4000.0, 4000.0)
"""``ZeroCalibrationSettings.failure_allowance_N`` (front 5.5, rear 4.0 kN)."""
LS1_JOB = {"case": "S8", "eps": 0.003, "setting": "LS1"}
LS1_STORED_HASH = "991926ff424247fb8a7fce94331884468fcdc0a405d4443cb2bf3ed11648aa23"
"""``main.jsonl`` line of ``LS1_JOB`` (stage 2 harness batch, M2 r5, final_C4G2)."""


@pytest.fixture(scope="module")
def t4h_replay():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import t4h_replay as module

        yield module
    finally:
        sys.path.remove(str(COUPLED_DIR))


def run_job(job: dict, tmp_path: Path) -> dict:
    """``job`` through ``run_v5.run_one`` in dynamics-dev; the runner's report."""
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / "report.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(RUNNER), json.dumps(job),
                    str(tmp_path / "t4h"), str(out_path)],
                   check=True, env=environment, timeout=TIMEOUT_S)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report.pop("foreign_modules") == []
    return report


# ------------------------------------------------------------------ E-6 allowance in the replay
def test_rebuilt_allowance_takes_the_failed_legs_from_the_calibration_events(t4h_replay) -> None:
    events = [(1.0, "INFO_D1_X"), (4.3, "INFO_PRESSURE_ZERO_CALIBRATED:FL"),
              (4.3, "WARN_PRESSURE_ZERO_SKIPPED:FR:grounded"),
              (4.3, "WARN_PRESSURE_ZERO_IMPLAUSIBLE:RR"), (4.3, "INFO_PRESSURE_ZERO_CALIBRATED:RL")]
    allowance = t4h_replay.rebuilt_offset_allowance(events, FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert allowance.deduction_N.tolist() == [0.0, 5500.0, 0.0, 4000.0]
    assert allowance.from_s == 4.3


def test_rebuilt_allowance_of_a_run_without_a_check_or_a_calibration(t4h_replay) -> None:
    all_skipped = [(0.0, "WARN_PRESSURE_ZERO_SKIPPED:all:no_check")]
    allowance = t4h_replay.rebuilt_offset_allowance(all_skipped, FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert allowance.deduction_N.tolist() == list(FAILURE_ALLOWANCE_N)
    none = t4h_replay.rebuilt_offset_allowance([], FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert none.deduction_N.tolist() == [0.0] * 4 and none.from_s is None
    with pytest.raises(ValueError, match="setting"):
        t4h_replay.rebuilt_offset_allowance([], FAILURE_ALLOWANCE_N, (1.0, 0.0, 0.0, 0.0))


def test_recorded_allowance_comes_before_the_rebuilt_one(t4h_replay) -> None:
    meta = {"pressure_offset_allowance_N": [0.0, 0.0, 4000.0, 0.0],
            "pressure_offset_allowance_from_s": 4.7,
            "events": [(4.7, "WARN_PRESSURE_ZERO_SKIPPED:FL:grounded")]}
    allowance = t4h_replay.offset_allowance_of(meta, config=None)
    assert allowance.deduction_N.tolist() == [0.0, 0.0, 4000.0, 0.0]
    assert allowance.from_s == 4.7 and allowance.note == "recorded"


# ---------------------------------------------------------------------- harness runs (dynamics-dev)
V5_RESULTS = PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
DG3_OFF_T4H = V5_RESULTS / "dg3" / "off" / "t4h"
"""Dg-3 r79 records (135, ③ off, written before the allowance record), git-ignored."""
DG3_RECORDS = 135
DG3_ALLOWANCE_RECORDS = 42
RECORDED_LOWER_TOLERANCE_N = 1e-6


@pytest.mark.slow
@pytest.mark.skipif(not DG3_OFF_T4H.is_dir(), reason="Dg-3 records not present")
def test_rebuilt_allowance_replays_the_dg3_lower_readings(t4h_replay) -> None:
    """control-expert check (2026-11-08): with the run's own events and the rebuilt allowance
    the replay gives each run's own lower reading (42 records have a failed calibration)."""
    files = sorted(DG3_OFF_T4H.glob("*.npz"))
    assert len(files) == DG3_RECORDS
    rows = [t4h_replay.replay_values(path, check_recorded=True) for path in files]
    assert max(row["recorded_lower_max_abs_N"] for row in rows) <= RECORDED_LOWER_TOLERANCE_N
    assert sum(any(row["offset_allowance_N"]) for row in rows) == DG3_ALLOWANCE_RECORDS


@pytest.mark.slow
def test_allowance_record_leaves_the_command_hash_alone(tmp_path: Path) -> None:
    """The allowance fields are read after the run: an LS1 row with its T4h record keeps the
    stored command hash, and its T4h meta carries the fields (no calibration: 0, no start)."""
    report = run_job(LS1_JOB, tmp_path)
    assert report["hash"] == LS1_STORED_HASH
    t4h = report["t4h"]
    assert t4h["pressure_offset_allowance_N"] == [0.0] * 4
    # the stage 2 rows run without a CHECK zero calibration: no calibration end
    assert t4h["pressure_offset_allowance_from_s"] is None
