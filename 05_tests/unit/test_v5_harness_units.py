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
"""dynamics-expert 3-DOF reference 2.433 kN, settled C2 - C3 of FL. Revision 3 of the M2 law
(flow_limited_r3, 2026-11-06): 3-DOF wrapper 2.456 kN, harness 2.475 kN (plain lag: 2.436).
Revision 4 (flow_limited_r4, 2026-11-07): harness 2.475 kN, the revision 3 value to the last bit
(FL releases right after the arm, before its locked rod force has changed: ``Delta`` about 0)."""
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


M2_14_INDEPENDENT_KICK_MM = {"0.25": 1.0556, "1.0": 1.0305}
"""hydraulics-expert independent two-chamber model (``liftoff_release.json`` 2026-11-07), FR
lifted off a 2 bar lock, body fixed, kick at 1.2 s per command fraction of v_max."""
M2_14_KICK_TOLERANCE = 0.05
M2_14_EQUAL_FORMS_PA = 1e-6
"""``Delta w`` and the harness ``Gr / A_ann`` agree to rounding (about 1e-9 Pa at 85 bar)."""


def test_m2_14_lifted_leg_release(tmp_path: Path) -> None:
    """Spec M2-14 (revision 4, 2026-11-07): released lifted leg; M2 total = A_ann (p_r0 - p*) /
    k_h; the kick (pad travel beyond the integrated speed) within 5 % of the independent model;
    M2 off leaves the base release decay alone (r F_lock / k_h, about 1.06 mm)."""
    report = _run_check("m2_14", tmp_path)
    for fraction, independent_mm in M2_14_INDEPENDENT_KICK_MM.items():
        on = report[f"on_{fraction}"]
        assert on["m2_total_mm"] == pytest.approx(on["expected_total_mm"], rel=1e-4)
        assert on["kick_mm"] == pytest.approx(independent_mm, rel=M2_14_KICK_TOLERANCE)
        assert on["max_delta_w_minus_gr_over_a_Pa"] <= M2_14_EQUAL_FORMS_PA
        assert on["rod_pressure_at_release_bar"] == pytest.approx(84.72, abs=0.01)
        assert report[f"off_{fraction}"]["kick_mm"] == pytest.approx(1.0599, abs=0.001)


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


def test_x1_lc_plant_locked_follows_the_closing_delay(tmp_path: Path) -> None:
    """v5 X-1 (5): the r79 ``DynMapRodModel`` reads ``plant.locked``; with LC that flag turns
    True t_c after the cut (one 1 ms chunk tolerance), at the lock event, and the rod reading
    is then the locked value."""
    report = _run_check("x1_locked", tmp_path)
    chunk_s = 1.0e-3
    assert report["first_locked_chunk_end"] is not None and report["cut_t"] is not None
    elapsed_s = report["first_locked_chunk_end"] - report["cut_t"]
    assert abs(elapsed_s - report["delay_s"]) <= 2 * chunk_s
    assert abs(report["first_locked_chunk_end"] - report["lock_event_t"]) <= chunk_s
    assert report["rod_reading_at_lock_Pa"] == report["locked_value_Pa"]


def test_c8_m2_and_m1c_do_not_count_the_retract_creep_twice(tmp_path: Path) -> None:
    """Spec C-8 on the harness: after the M1c opening M2 starts from p_rod, so in the first
    chunks it adds almost nothing to the creep (without the seed it would add about -creep)."""
    report = _run_check("c8", tmp_path)
    assert report["opened_chunk"] is not None
    assert abs(report["m2_first_5_chunks_mm"]) < 0.1 * report["creep_mm"]
