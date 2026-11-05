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
