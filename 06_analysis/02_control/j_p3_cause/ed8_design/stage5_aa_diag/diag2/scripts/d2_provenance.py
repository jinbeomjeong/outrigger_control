"""Write ``provenance.json`` and ``code/r51_gyro_switch.patch`` of diagnosis 2 (record only).

Usage (python-dev):
  python.exe -I -B d2_provenance.py <diag2 folder> <ed8-diag worktree> [<patch commit>]

Without a patch commit the patch is ``git diff`` of the worktree against the trace commit
b040274c for ``04_scripts``; with it, ``git show <commit>`` of that path. Refuses files that
exist (exit 2).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

C8 = "56849248371b4916e2fe683265e7abffdd6fb8d7"
TRACE_COMMIT = "b040274c"
PATCHED = "04_scripts/03_control/s8/r51_reapp_closed_loop.py"
J_P3 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
INPUTS = {
    "key_file": J_P3 / "ed8_design" / "keys_seal_41e107e9" / "heldout_g_ed8.json",
    "diag1_jobs": J_P3 / "ed8_design" / "stage5_aa_diag" / "diag_jobs.json",
    "diag1_runs_trace_off": J_P3 / "ed8_design" / "stage5_aa_diag" / "runs_trace_off.jsonl",
    "diag1_first_step_period": J_P3 / "ed8_design" / "stage5_aa_diag" / "first_step_period.csv",
    "diag1_provenance": J_P3 / "ed8_design" / "stage5_aa_diag" / "provenance.json",
    "interpretation": J_P3 / "ed8_design" / "stage5_aa_diag" / "diag_interpretation.md",
}
NOTES = {
    "steps": {
        "A": "gyro switch off (R51_DIAG_GYRO_SAMPLES unset), trace off, the 7 jobs: bit check of "
             "the harness patch against diagnosis 1 trace-off records and the stored lines",
        "B": "gyro switch on (all consumers: D1'' lever term and DSb75 gyro window), trace on",
        "C": "gyro switch on, DSb75 gyro window fed without the samples (driver patch of "
             "C2Controller._diff_sink_feed_gyro in the worker), trace on: D1'' only",
        "D": "sweep, gyro off, trace on: J1 shape (FR Fs0 level 30 mm / 0.04 s) and J3 shape "
             "(FL Fs2 level 25 mm / 0.05 s) at offsets 0.0845 .. 0.1005 s (1 ms)",
    },
    "gyro_samples": "per IMU window (10 ms): trapezoid mean of plant.w at the 11 chunk "
                    "boundaries (1 ms), the same window as the specific force samples; plant "
                    "sub-steps inside a 1 ms chunk are not sampled (approximation)",
    "trace_columns": "as diagnosis 1 (../provenance.json trace_row_keys, csv_notes)",
    "repro_check.csv": "sha_equals_diag1 / record_equals_diag1: against ../runs_trace_off.jsonl "
                       "(record without wall_s, label, trace, two_pressure_file, diag); "
                       "sha_equals_stored: against the stored stage-5 line (5 jobs)",
    "compare_gyro.csv": "diag1_* = diagnosis 1 (no gyro), B_* / C_* = this run; "
                        "<step>_lever_z_m_s2 = lever term subtracted from f_z in the first step "
                        "period, <step>_M_lever_z_kN = M_eff times it; candidates = "
                        "leg:dp_h/threshold/outcome",
    "sweep_summary.csv": "lift_phase_in_period_s = lift time modulo 0.1 s (lift - the sample "
                         "before it); first_step_minus_lift_ms = first sample with a head step "
                         "candidate after the lift minus the lift; max_ratio_to_threshold = "
                         "|dr| / threshold, largest candidate (>= 1 = FAULT)",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(worktree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(worktree), *args], capture_output=True,
                          check=True).stdout.decode("utf-8")


def main() -> int:
    folder, worktree = Path(sys.argv[1]), Path(sys.argv[2])
    patch_commit = sys.argv[3] if len(sys.argv) > 3 else None
    patch_path = folder / "code" / "r51_gyro_switch.patch"
    if (folder / "provenance.json").exists() or patch_path.exists():
        print("refusing to overwrite")
        return 2
    patch_path.parent.mkdir(exist_ok=True)
    if patch_commit is None:
        patch = _git(worktree, "diff", TRACE_COMMIT, "--", PATCHED)
    else:
        patch = _git(worktree, "show", patch_commit, "--", PATCHED)
    patch_path.write_bytes(patch.encode("utf-8"))
    logs = {path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.log.json"))}
    record = {
        "what": "436.9 edition 8 stage-5 A/A D1 diagnosis 2 (gyro supply contrast, lift-phase "
                "sweep), approved by the user; record only, not a judgement",
        "worktree": str(worktree), "branch": "ed8-diag", "base_commit": C8,
        "trace_commit": _git(worktree, "rev-parse", TRACE_COMMIT).strip(),
        "head": _git(worktree, "rev-parse", "HEAD").strip(),
        "patch_commit": patch_commit,
        "worktree_status": _git(worktree, "status", "--porcelain").splitlines(),
        "patched_file": {"path": PATCHED, "sha256": _sha256(worktree / PATCHED),
                         "patch_sha256": _sha256(patch_path)},
        "inputs_sha256": {name: _sha256(path) for name, path in INPUTS.items()},
        "scripts_sha256": {p.name: _sha256(p) for p in sorted((folder / "scripts").glob("*"))},
        "run_logs": logs,
        "notes": NOTES,
        "outputs_sha256": {
            str(p.relative_to(folder)).replace("\\", "/"): _sha256(p)
            for p in sorted(folder.rglob("*")) if p.is_file()
            and p.name != "provenance.json" and "scripts" not in p.parts},
    }
    (folder / "provenance.json").write_text(json.dumps(record, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
