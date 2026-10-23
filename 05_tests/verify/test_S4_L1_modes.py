"""S4 branch A V7 check (chrono_build_plan.md S4): the judged runs of the six modes.

``sim``: initial-velocity cases from the S1 snapshot at the YAML dt through the job function of
``04_scripts/02_chrono/run_S4.py``. The judged run of each mode comes from
``verify.s4.assign_modes`` on the reference mode shapes (dynamics_model.md 5.13.8 (1-b);
REXOME35: roll for modes 1, 3, 5, pitch for 2, 4, heave for 6), and each mode must reach the
V7 frequency rule (+-3 %) with an ERA pole of MAC > 0.99 in its judged run. A close runner-up
run (amplitude ratio >= 0.8, today yaw for mode 3) is checked more loosely: frequency +-3 %,
MAC >= 0.80 and the pole resembling that mode most; its zeta is information only. The judging
run with every case is ``run_S4.py all`` (summary
``06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.batch import Case  # noqa: E402
from outrigger_sim.scenarios.impulse import modal_reference  # noqa: E402
from outrigger_sim.verify.reference import load_references  # noqa: E402
from outrigger_sim.verify.s2a import V7_FREQ_REL_TOL  # noqa: E402
from outrigger_sim.verify.s4 import (  # noqa: E402
    ModeRow,
    assign_modes_with_runner_up,
    judged_value,
)

ROOT = Path(__file__).resolve().parents[2]
LEVEL = "top"
JUDGED_RUN_MAC_MIN = 0.99
RUNNER_UP_MAC_MIN = 0.80
"""dynamics_model.md 5.13.8 (1-b): the runner-up run only has to find the same mode."""


def _assignments():
    modal = modal_reference(load_references(), LEVEL)
    return assign_modes_with_runner_up(modal.phi, modal.mass_matrix, modal.f_damped_Hz)


ASSIGNMENTS = _assignments()
JUDGED_RUNS = sorted({a.run for a in ASSIGNMENTS})
RUNNER_UP_CASES = [
    (a.runner_up, mode_index)
    for mode_index, a in enumerate(ASSIGNMENTS)
    if a.close_runner_up()[0] is not None
]


def _script():
    path = ROOT / "04_scripts" / "02_chrono" / "run_S4.py"
    spec = importlib.util.spec_from_file_location("run_S4_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_S4_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _run_case(run: str, case_dir: Path) -> dict:
    script = _script()
    case_id = f"modes_{run}"
    summary = script.job_modes(Case(case_id, script.case_settings(case_id)), case_dir).summary
    assert summary["all_passed"], [c for c in summary["checks"] if not c["passed"]]
    return summary


def _mode_row(run: str, row: dict) -> ModeRow:
    era = row["era"] or {}
    return ModeRow(mode=row["mode"], run=run, f_proj_Hz=row["f_proj_Hz"],
                   zeta_proj=row["zeta_proj"], fit_residual_rms_rel=row["fit_residual_rms_rel"],
                   f_era_Hz=era.get("f_Hz"), zeta_era=era.get("zeta"),
                   leakage=era.get("leakage"), zeta_num=row["zeta_num"],
                   f_ref_Hz=row["f_ref_Hz"], zeta_ref=row["zeta_ref"])


def _frequency_error(run: str, row: dict) -> float:
    judged = judged_value(_mode_row(run, row))
    return abs(judged.f_Hz / row["f_ref_Hz"] - 1.0)


@pytest.mark.sim
@pytest.mark.parametrize("run", JUDGED_RUNS)
def test_v7_judged_run_finds_its_modes(run: str, tmp_path: Path) -> None:
    """Every mode judged in this run: frequency +-3 % and ERA MAC > 0.99."""
    summary = _run_case(run, tmp_path)
    failures = []
    for mode_index, assignment in enumerate(ASSIGNMENTS):
        if assignment.run != run:
            continue
        row = summary["modes"][mode_index]
        mac = (row["era"] or {}).get("mac_vs_phi")
        frequency_error = _frequency_error(run, row)
        print(f"{run}: mode {mode_index + 1} f error {frequency_error:.4f}, MAC {mac}, "
              f"zeta_proj {row['zeta_proj']:.4f} (ref {row['zeta_ref']:.4f}, information)")
        if frequency_error > V7_FREQ_REL_TOL:
            failures.append(f"mode {mode_index + 1}: f error {frequency_error:.4f}")
        if mac is None or not mac > JUDGED_RUN_MAC_MIN:
            failures.append(f"mode {mode_index + 1}: MAC {mac}")
    assert not failures, f"{run}: {failures}"


@pytest.mark.sim
@pytest.mark.parametrize(("run", "mode_index"), RUNNER_UP_CASES)
def test_v7_close_runner_up_run_finds_the_same_mode(
    run: str, mode_index: int, tmp_path: Path
) -> None:
    """Runner-up run of a close mode: frequency +-3 %, MAC >= 0.80, best-MAC mode = the mode."""
    summary = _run_case(run, tmp_path)
    row = summary["modes"][mode_index]
    era = row["era"] or {}
    mac = era.get("mac_vs_phi")
    mac_by_mode = era.get("mac_vs_all_phi") or []
    best_mode = int(np.argmax(mac_by_mode)) + 1 if mac_by_mode else None
    frequency_error = _frequency_error(run, row)
    print(f"{run}: mode {mode_index + 1} f error {frequency_error:.4f}, MAC {mac}, "
          f"MAC by reference mode {np.round(mac_by_mode, 3).tolist()}, "
          f"zeta_proj {row['zeta_proj']:.4f} (ref {row['zeta_ref']:.4f}, information)")
    assert frequency_error <= V7_FREQ_REL_TOL, (mode_index + 1, frequency_error)
    assert mac is not None and mac >= RUNNER_UP_MAC_MIN, (mode_index + 1, mac)
    assert best_mode == mode_index + 1, (mode_index + 1, best_mode, mac_by_mode)
