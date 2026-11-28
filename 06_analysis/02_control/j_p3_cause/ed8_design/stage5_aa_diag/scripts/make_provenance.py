"""Write ``provenance.json`` and the ``code/`` copy of the diagnostic change (record only).

Usage (python-dev):
  python.exe -I -B make_provenance.py <stage5_aa_diag folder> <ed8-diag worktree>

``code/two_pressure.py.patch`` = ``git diff`` of the worktree against C8 for ``03_src``;
``code/test_two_pressure_d1_trace.py`` = the new (untracked) test file. Refuses files that
exist; exit 2 then or when the worktree HEAD is not C8.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

C8 = "56849248371b4916e2fe683265e7abffdd6fb8d7"
J_P3 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
TRACE_SOURCE = "03_src/outrigger_sim/control/two_pressure.py"
TEST_SOURCE = "05_tests/unit/test_two_pressure_d1_trace.py"
INPUTS = {
    "key_file": J_P3 / "ed8_design" / "keys_seal_41e107e9" / "heldout_g_ed8.json",
    "stored_ho_v0": J_P3 / "j9_runs" / "56849248" / "ho_v0_a1" / "ed8_heldout_v0.jsonl",
    "stored_ho_aa2": J_P3 / "j9_runs" / "56849248" / "ho_aa2_a1" / "ed8_heldout_aa2.jsonl",
    "stored_ho_aa3": J_P3 / "j9_runs" / "56849248" / "ho_aa3_a1" / "ed8_heldout_aa3.jsonl",
    "cause_analysis": J_P3 / "ed8_design" / "stage5_aa_cause" / "aa_cause_analysis.md",
}
TRACE_ROW_KEYS = {
    "t_s": "period time [s] (the 10 Hz read of TwoPressureMonitor.read)",
    "monitor": "hex id of the monitor object that wrote the row",
    "is_locked_phase": "READY (legs locked) as passed to read",
    "is_crawler_lifted": "LEVEL or later (D1'' applies) as passed to read",
    "commanded_m_s": "controller output of the previous period per leg [m/s]",
    "grounded": "net force - seal band >= F_min per leg (D1 input)",
    "f_z_raw_m_s2": "body-z specific force of the last 10 ms IMU partial mean [m/s^2]",
    "f_z_used_m_s2": "f_z D1'' uses: raw minus the lever term (alpha x r)_z when corrected",
    "lever_z_m_s2": "(alpha x r)_z subtracted; null when not applied (gyro missing or off)",
    "gyro_partial_means": "rows of imu_gyro_rad_s passed (null = no gyro samples)",
    "is_lever_missing": "lever correction on but < 2 finite gyro partial means "
                        "(WARN_D1_IMU_GYRO_MISSING branch, f_z uncorrected)",
    "previous_f_z_used_m_s2": "f_z_used of the period before (null = none)",
    "head_Pa": "head readings per leg [Pa] (held value for a held leg)",
    "rod_Pa": "rod readings per leg [Pa]",
    "dp_head_Pa / dp_rod_Pa": "one-period change per leg [Pa] (absent in the first period)",
    "is_step_rule_suspended": "P-S8-25 suspension (no step judged)",
    "head_range_faults": "D1 range / current / non-finite reasons of this period",
    "head_step_candidates / rod_step_candidates": "legs with |dp| > max_step_Pa",
    "net_sum_N": "sum F = sum(p_h A_p - p_r A_ann), raw readings [N]",
    "previous_net_sum_N": "sum F of the period before [N]",
    "mass_kg": "M_eff D1'' would use now (_d1_mass_kg)",
    "d1pp_inputs_ready": "explained_imu, lifted, f_z now and before, M_eff known",
    "residual_N / previous_residual_N": "r = sum F - M_eff f_z_used now / before (same M_eff)",
    "residual_change_N": "|r - r_previous| [N], every period with d1pp_inputs_ready",
    "step_rule_branch": "imu_residual (D1'') or load_redistribution (D1') when candidates",
    "judged_change_N": "the change the candidates were judged against [N]",
    "judged_ratio": "imu_residual_step_ratio or explained_step_sum_ratio",
    "judged_mass_kg": "M_eff of the judgement (null = D1' branch)",
    "candidates": "per candidate leg: dp_head_Pa, step_force_N = |dp_h| A_p, threshold_N = "
                  "ratio * step_force_N, is_unexplained (judged_change_N >= threshold_N)",
    "head_fault_reasons": "legs given D1_step (or a range reason) this period",
    "rod_steps_unexplained": "rod-side step legs that fell back this period",
    "events": "event names the diagnosis appended this period (D1 / D2 / D3 / moving)",
}
CSV_NOTES = {
    "units": "trace_<label>.csv / event_window.csv: pressures and dp in bar, forces in kN",
    "M_f_z_kN": "M_eff * f_z_used",
    "M_df_z_kN": "M_eff * (f_z_used - previous_f_z_used)",
    "sum_change_kN": "net_sum - previous_net_sum",
    "threshold_kN_<leg>": "imu_residual_step_ratio (or D1' ratio) * |dp_h| A_p of a candidate",
    "unexplained_<leg>": "True = FAULT D1_step (judged change >= threshold)",
    "repro_check.csv": "off_*: trace off run, on_*: trace on run; *_equals_*: comparison of "
                       "commands_sha256 / final_phase / the whole run_one record without "
                       "wall_s, label, trace, two_pressure_file",
    "step_candidates.csv": "every head step candidate from t_event - 0.3 s on (primary monitor)",
    "diag_summary.json": "lift_s = t_event_s + event_output.lifts[event leg].first_s; "
                         "lift_phase_in_period_s = lift_s modulo 0.1 s; "
                         "first_period_after_lift = the first traced period with t_s >= lift_s",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(worktree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(worktree), *args], capture_output=True,
                          check=True).stdout.decode("utf-8")


def main() -> int:
    folder, worktree = Path(sys.argv[1]), Path(sys.argv[2])
    code = folder / "code"
    targets = [folder / "provenance.json", code / "two_pressure.py.patch",
               code / "test_two_pressure_d1_trace.py"]
    if any(path.exists() for path in targets):
        print("refusing to overwrite provenance / code copies")
        return 2
    head = _git(worktree, "rev-parse", "HEAD").strip()
    if head != C8:
        print(f"worktree HEAD {head} is not C8")
        return 2
    code.mkdir(exist_ok=True)
    patch = _git(worktree, "diff", C8, "--", "03_src")
    (code / "two_pressure.py.patch").write_bytes(patch.encode("utf-8"))
    shutil.copyfile(worktree / TEST_SOURCE, code / "test_two_pressure_d1_trace.py")
    status = _git(worktree, "status", "--porcelain").splitlines()
    record = {
        "what": "436.9 edition 8 stage-5 A/A D1 diagnosis (closing judgement 4.5, decision "
                "stage 5-3). Record only, not a judgement; edition 9 design input.",
        "worktree": str(worktree), "branch": "ed8-diag", "base_commit": C8,
        "worktree_status": status, "committed": False,
        "trace_source": {"path": TRACE_SOURCE,
                         "base_blob": _git(worktree, "rev-parse", f"{C8}:{TRACE_SOURCE}").strip(),
                         "modified_sha256": _sha256(worktree / TRACE_SOURCE),
                         "patch_sha256": _sha256(code / "two_pressure.py.patch")},
        "test_source": {"path": TEST_SOURCE, "sha256": _sha256(worktree / TEST_SOURCE)},
        "inputs_sha256": {name: _sha256(path) for name, path in INPUTS.items()},
        "inputs_path": {name: str(path) for name, path in INPUTS.items()},
        "scripts_sha256": {path.name: _sha256(path)
                           for path in sorted((folder / "scripts").glob("*.py"))},
        "run_log": json.loads((folder / "run_log.json").read_text(encoding="utf-8")),
        "trace_row_keys": TRACE_ROW_KEYS,
        "csv_notes": CSV_NOTES,
        "outputs_sha256": {path.name: _sha256(path) for path in sorted(folder.iterdir())
                           if path.is_file() and path.name != "provenance.json"},
    }
    (folder / "provenance.json").write_text(json.dumps(record, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
