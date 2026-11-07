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
(FL releases right after the arm, before its locked rod force has changed: ``Delta`` about 0).
Revision 5 (flow_limited_r5, 2026-11-07): 2.4745938373796 kN, r4 + 3e-14 kN (the FL lock after
the 0.5 s move keeps a tiny unrelieved share)."""
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


M2_14B_LOST_STROKE_MM = {"VN_0.25": 0.1041, "BL_0.25": 0.0963, "VN_1.0": 0.0994,
                         "BL_1.0": 0.0937}
"""hydraulics-expert 1-leg replica ``m2_14b_m1c.json`` (2026-11-07): command minus M1c output."""
M2_14B_LOST_TOLERANCE = 0.10
M2_14B_KICK_DIFFERENCE_MM = 0.005
M2_14B_TOTAL_TOLERANCE_M = 1e-9


def test_m2_14b_lifted_leg_release_with_m1c(tmp_path: Path) -> None:
    """Spec M2-14b (hydraulics-expert 2026-11-07): the M2-14 lift-off with M1c VN / BL. An
    extension re-approach gets no seed (start = p_r,rel); M2 total = A_ann (p_start + Delta -
    p_end - Delta w_end) / k_h within 1e-9 m; the kick against the M1c output speed within 5 %
    of the independent model and within 0.005 mm of M1c off (revision 3: about 2.08 mm); lost
    stroke (command - output) within 10 % of the replica. Release delays are recorded only."""
    report = _run_check("m2_14b", tmp_path)
    for fraction, independent_mm in M2_14_INDEPENDENT_KICK_MM.items():
        without = report[f"off_{fraction}"]
        for kind in ("VN", "BL"):
            row = report[f"{kind}_{fraction}"]
            assert row["start_bar"] == pytest.approx(row["rod_pressure_at_release_bar"],
                                                     abs=1e-9)  # no seed
            total_m = row["m2_total_mm"] / 1e3
            assert abs(total_m - row["formula_total_mm"] / 1e3) <= M2_14B_TOTAL_TOLERANCE_M
            assert row["kick_vs_delivered_mm"] == pytest.approx(independent_mm,
                                                                rel=M2_14_KICK_TOLERANCE)
            assert abs(row["kick_vs_delivered_mm"] - without["kick_vs_delivered_mm"]) \
                <= M2_14B_KICK_DIFFERENCE_MM
            assert row["lost_stroke_mm"] == pytest.approx(
                M2_14B_LOST_STROKE_MM[f"{kind}_{fraction}"], rel=M2_14B_LOST_TOLERANCE)


M2_14C_CREEP_MM = {"VN": -0.336, "BL": -0.375}
M2_14C_SEED_BAR = {"VN": 25.11, "BL": 28.14}
"""hydraulics-expert 1-leg replica (2026-11-07), retract after a 0.5 mm floor rise."""
M2_14C_PRESSURE_GAP_BAR = 0.5
"""``|p_k - p|`` at 1.2 s (replica 0.21 / 0.23 bar; revision 3 about 3.1 bar)."""


def test_m2_14c_retract_with_m1c_counts_g_r_once(tmp_path: Path) -> None:
    """Spec M2-14c (optional, hydraulics-expert 2026-11-07): FR loaded while locked (Delta
    2.91 bar), 0.25 v_max retract with M1c. The kernel pressure p_r0 - G_r / A_ann - (k_h /
    A_ann) (S_M2 + S_creep) (head opening shift left out) meets the tracked p within 0.5 bar;
    the seed goes into p only, Delta stays."""
    report = _run_check("m2_14c", tmp_path)
    for kind in ("VN", "BL"):
        row = report[kind]
        assert abs(row["kernel_minus_tracked_bar"]) <= M2_14C_PRESSURE_GAP_BAR
        assert row["delta_bar"] == pytest.approx(2.91, abs=0.01)
        assert row["start_bar"] == pytest.approx(M2_14C_SEED_BAR[kind], abs=0.05)
        assert row["creep_mm"] == pytest.approx(M2_14C_CREEP_MM[kind], rel=0.05)
        total_m = row["m2_total_mm"] / 1e3
        assert abs(total_m - row["formula_total_mm"] / 1e3) <= M2_14B_TOTAL_TOLERANCE_M


ANCHOR_P_R0_TOLERANCE_BAR = 0.05
ANCHOR_KNEE_TOLERANCE_KN = 0.1
"""Spec ``r5_spec.md`` harness comparison (kernel step 5e-4 s against the 1e-4 s replica)."""
ANCHOR_EXACT_PA = 1e-6
ANCHOR_RAISED_CASES = ("U1_0", "U1_2", "U2_0", "U2_2", "U2b_0", "U3b_0")
ANCHOR_P_EXT_CASES = ("U3_0", "U3_2", "U4_0")
"""U3 (relieved extension) and U4 (hanging leg, ``p_tr`` = ``p*``) keep ``p_ext`` = 2 bar."""
P_EXT_PA = 2.0e5


def test_r5_extension_lock_anchor_on_the_harness(tmp_path: Path) -> None:
    """M2 revision 5 (plan B, user decision 2026-11-07) on the harness law: ``p_r0`` = ``p_ext +
    max(p_tr - p*, 0)`` against the 1-leg replica at the harness ``k_h``, ``k_r`` (the spec table
    is at s 0.30 m; the harness columns are frozen at e_op); the lock step keeps the moving
    force; the knee measured by loading the locked leg up is ``dF_knee``; M2 off and retract
    locks unchanged."""
    report = _run_check("anchor_r5", tmp_path)
    for case in ANCHOR_RAISED_CASES + ANCHOR_P_EXT_CASES:
        row = report[case]
        assert row["locked"]
        # same function and dt; the hanging leg's harness force carries the tiny moving Gr
        assert row["p_tr_bar"] == pytest.approx(row["replica_harness_step_p_tr_bar"], rel=1e-12)
        assert row["p_r0_bar"] == pytest.approx(row["replica_p_r0_bar"],
                                                abs=ANCHOR_P_R0_TOLERANCE_BAR)
        assert row["knee_formula_kN"] == pytest.approx(row["replica_knee_kN"],
                                                       abs=ANCHOR_KNEE_TOLERANCE_KN)
        assert row["lock_step_force_minus_before_N"] == 0.0
        if "measured_knee_kN" in row:
            assert row["measured_knee_kN"] == pytest.approx(row["knee_formula_kN"],
                                                            abs=ANCHOR_KNEE_TOLERANCE_KN)
    for case in ANCHOR_RAISED_CASES:
        record = report[case]["record"]
        assert report[case]["p_r0_bar"] > 2.1
        assert record["anchor_excess_over_0p1bar_locks"] == 1
    for case in ANCHOR_P_EXT_CASES:
        assert abs(report[case]["p_r0_Pa"] - P_EXT_PA) <= ANCHOR_EXACT_PA
        assert report[case]["record"]["anchor_excess_over_0p1bar_locks"] == 0
    for leg in (0, 2):
        assert report[f"U1_off_{leg}"]["p_r0_Pa"] == P_EXT_PA
        for state in ("on", "off"):
            row = report[f"U10_{state}_{leg}"]
            assert row["locked"] and row["p_r0_Pa"] == row["p_ret_Pa"]


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
