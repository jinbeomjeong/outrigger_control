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


M2_6_SETTLED_DIFFERENCE_KN = 2.43
"""dynamics-expert 3-DOF reference 2.433 kN (harness 2.436 kN), settled C2 - C3 of FL."""
M2_6_TOLERANCE_KN = 0.25


def test_m2_6_harness_release_pair(tmp_path: Path) -> None:
    """Spec M2-6, revised (user decision 2026-11-06; v5_criteria revision section to follow):
    lift, FL 0.25 v_max for 0.5 s, stand still 30 s; settled C2 - C3 FL force (mean 10 .. 30 s
    after the move) 2.43 +- 0.25 kN; 0 without the option. The old 4.13 .. 4.25 +- 1 kN value
    was a 3 s value inside the rocking transient."""
    report = _run_check("m2_6", tmp_path)
    assert report["difference_off_kN"] == 0.0
    assert report["difference_on_kN"] == pytest.approx(M2_6_SETTLED_DIFFERENCE_KN,
                                                       abs=M2_6_TOLERANCE_KN)


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


def test_c8_m2_and_m1c_do_not_count_the_retract_creep_twice(tmp_path: Path) -> None:
    """Spec C-8 on the harness: after the M1c opening M2 starts from p_rod, so in the first
    chunks it adds almost nothing to the creep (without the seed it would add about -creep)."""
    report = _run_check("c8", tmp_path)
    assert report["opened_chunk"] is not None
    assert abs(report["m2_first_5_chunks_mm"]) < 0.1 * report["creep_mm"]
