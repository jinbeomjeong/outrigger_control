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
    """+-2 um/s for 1 s: no release with P1 (the base law alone releases). Edition 4 (J4a-11):
    4.7 mm/s through the valve lag releases between the M1c rod check release and path B
    ``t_B`` + 5 ms, ``t_B`` = the head check fill without the ``psi p_B`` help and with the VN
    drain (front 87 bar 160.16 ms, review ``cr04``; without the drain 160.08 ms; the R12 RR
    case at 35.2 bar 94.02 ms, its plant release 70 ms)."""
    report = _run_check("p1_gate", tmp_path)
    p1 = report["p1"]
    assert p1["micro_unlocked_steps"] == 0
    release_s, path_b_s = p1["release_after_s"], p1["hand_head_check_open_drain_s"]
    assert release_s is not None and p1["rod_check_release_after_s"] is not None
    assert p1["rod_check_release_after_s"] <= release_s <= path_b_s + 5e-3
    assert p1["gate_summary_mode"] == "gate_only"
    assert report["off"]["micro_unlocked_steps"] > 0
    reference = report["path_b_reference_s"]
    assert reference["front_87bar_drain"] == pytest.approx(0.16016, abs=5e-5)
    assert reference["front_87bar_no_drain"] == pytest.approx(0.16008, abs=5e-5)
    # cr04's 94.02 ms at 35.2 bar is the front head area (the rear area of R12 RR gives
    # about 114 ms); both lie above the R12 RR plant release of 70 ms (the psi p_B help)
    assert reference["front_area_35p2bar_drain"] == pytest.approx(0.09402, abs=5e-5)
    assert reference["rear_area_35p2bar_drain"] >= 0.070


SEED_FORCE_TOLERANCE_N = 1.0
"""Addendum 4a-2 3.4: ``|net_force_seed_step_N|`` <= 1 N per seed row."""
MUTATED_SEED_FORCE_MIN_N = 1.0e3
"""Addendum 4a-2 3.3: the column must see a seed held back from the M2 re-anchor."""


def _seed_rows(report: dict) -> list[dict]:
    columns = report["seed_log_columns"]
    return [dict(zip(columns, row, strict=True)) for row in report["seed_log"]]


def test_t_jr_15_retract_seed_rows_and_net_force(tmp_path) -> None:
    """T-JR-15 / T-JR-18 (edition 4, addendum 4a-2 3.4): one ``p1_retract_seed_log`` row per
    counted seed; the judged seed net force ``net_force_seed_step_N`` <= 1 N on every row, no
    row clipped (a clipped row is not judgeable). ``net_force_step_N`` is the read net force
    identity (0 by definition, an implementation check column)."""
    report = _run_check("p1_seed", tmp_path)
    assert report["seed_count"] >= 1
    rows = _seed_rows(report)
    assert len(rows) == report["seed_count"]
    for values in rows:
        assert values["step_Pa"] == pytest.approx(values["seed_Pa"] - values["p_r_locked_Pa"])
        assert values["m2_shift_clipped"] is False and values["m2_previous_unset"] is False
        assert abs(values["net_force_seed_step_N"]) <= SEED_FORCE_TOLERANCE_N
        assert abs(values["net_force_step_N"]) <= SEED_FORCE_TOLERANCE_N


def test_4a2_3_3_seed_force_column_sees_a_held_back_seed(tmp_path) -> None:
    """Addendum 4a-2 3.3 (counterexample, both hard): RL at ``p_h`` 120.6 bar, the locked rod
    side at the floor, band 7 kN. As built ``|net_force_seed_step_N|`` <= 1 N; with the seed
    held back from ``release()`` (test hook) >= 1 kN (about ``A_ann`` x 33.8 bar = 10.6 kN,
    ``k_h`` = ``k_o`` on the harness). The records-off run moves the plant bit for bit alike
    (the column only reads)."""
    report = _run_check("seed_counterexample", tmp_path)
    normal, mutated = report["normal"], report["mutated"]
    assert normal["head_bar"] == pytest.approx(120.6, abs=0.05)
    assert normal["rod_bar"] == pytest.approx(normal["p_floor_bar"], abs=1e-9)
    assert normal["band_N"] == pytest.approx(7.0e3)
    normal_rows, mutated_rows = _seed_rows(normal), _seed_rows(mutated)
    assert len(normal_rows) == normal["seed_count"] >= 1
    assert len(mutated_rows) == mutated["seed_count"] == len(normal_rows)
    for values in normal_rows:
        assert values["m2_shift_clipped"] is False
        assert abs(values["net_force_seed_step_N"]) <= SEED_FORCE_TOLERANCE_N
    assert max(abs(values["net_force_seed_step_N"]) for values in mutated_rows) >= (
        MUTATED_SEED_FORCE_MIN_N)
    assert report["records_off_bit_equal"] is True


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
