"""v5 options on the reduced harness plant (spec ``v5_hydraulic_impl_spec.md`` 3.1, harness rows).

The checks run in dynamics-dev through ``v5_harness_unit_runner.py`` (numba harness); these tests
run in Chrono-dev and read its JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
RUNNER = Path(__file__).resolve().with_name("v5_harness_unit_runner.py")
TIMEOUT_S = 900


def _run_check(check: str, tmp_path: Path) -> dict:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / f"{check}.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(RUNNER), check, str(out_path)],
                   check=True, env=environment, timeout=TIMEOUT_S)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report.pop("foreign_modules") == []
    return report


def test_m2_6_harness_release_pair(tmp_path: Path) -> None:
    """Spec M2-6: C2 - C3 end force of FL 4.13 .. 4.25 +- 1 kN; 0 without the option."""
    report = _run_check("m2_6", tmp_path)
    assert report["difference_off_kN"] == 0.0
    assert 4.13 - 1.0 <= report["difference_on_kN"] <= 4.25 + 1.0


def test_lc_harness_cut_lock_restart_and_copy(tmp_path: Path) -> None:
    """Spec L-1, L-4, L-5, L-7 on the harness plant: one 1 ms chunk tolerance."""
    report = _run_check("lc", tmp_path)
    chunk_s = 1.0e-3
    for fraction in ("0.25", "1.0"):
        elapsed_s = report[f"l1_cut_after_zero_s_{fraction}"]
        assert abs(elapsed_s - report[f"l1_formula_s_{fraction}"]) <= chunk_s
        assert abs(elapsed_s - report[f"l1_table_s_{fraction}"]) <= 0.001 + 1e-9
    for delay in ("0.02", "0.05", "0.1"):
        assert abs(report[f"l4_lock_after_cut_s_{delay}"] - float(delay)) <= chunk_s
    assert report["l5_lock_time_after_restart"] is None
    assert report["l7_copy_equal"] is True
