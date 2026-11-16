"""436.9 plant options P1 and P2 on the harness plant (``jp3_remedy_spec.md`` 5.2 T-JR-06,
T-JR-07). The checks run in dynamics-dev through ``jp3_harness_unit_runner.py``; these tests
read its JSON (``test_v5_harness_units.py`` precedent)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
RUNNER = Path(__file__).resolve().with_name("jp3_harness_unit_runner.py")
TIMEOUT_S = 900
STEP_TOLERANCE_PA = 0.01e5
"""T-JR-07: the locked truth steps by at most 0.01 bar at a relock with P2."""


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


def test_t_jr_06_micro_command_keeps_the_lock_and_a_real_command_releases(tmp_path) -> None:
    """+-2 um/s for 1 s: no release with P1 (the base law alone releases); 4.7 mm/s through
    the valve lag releases no later than the hand fill of the head check without the
    ``psi p_B`` help (path B upper bound, +5 ms; the released rod check lets M1c open a few ms
    earlier) and not at once. The spec's "within 0.1 s" is the R12 RR head of 35 bar; the
    stand-in FL stands at about 87 bar, where the fill takes about 0.15 s."""
    report = _run_check("p1_gate", tmp_path)
    assert report["p1"]["micro_unlocked_steps"] == 0
    release_s, hand_s = report["p1"]["release_after_s"], report["p1"]["hand_head_check_open_s"]
    assert release_s is not None
    assert 0.5 * hand_s <= release_s <= hand_s + 5e-3
    assert report["p1"]["gate_summary_mode"] == "gate_only"
    assert report["off"]["micro_unlocked_steps"] > 0


def test_t_jr_07_relock_is_continuous_with_p2(tmp_path) -> None:
    """A relock with ``G_r,lock != 0``: P2 keeps the locked truth on the lag (<= 0.01 bar, the
    head likewise), the truth reaches the floor at the knee (+-1 Pa), the locked ratio of RR is
    -1.2278; the r5 anchor steps (the 436.8 plant artefact)."""
    report = _run_check("p2_anchor", tmp_path)
    p2, r5 = report["p2"], report["r5"]
    relock = p2["relock"]
    assert relock is not None and abs(relock["Gr_lock_N"]) > 1.0
    assert abs(relock["truth_after_Pa"] - relock["lag_before_Pa"]) <= STEP_TOLERANCE_PA
    assert abs(relock["head_step_Pa"]) <= STEP_TOLERANCE_PA
    assert abs(p2["knee_truth_minus_floor_Pa"]) <= 1.0
    assert p2["rr_locked_ratio"] == pytest.approx(1.2278, abs=1e-4)
    assert p2["relock_step_over_1bar_count"] == 0
    r5_relock = r5["relock"]
    assert abs(r5_relock["truth_after_Pa"] - r5_relock["lag_before_Pa"]) > STEP_TOLERANCE_PA
