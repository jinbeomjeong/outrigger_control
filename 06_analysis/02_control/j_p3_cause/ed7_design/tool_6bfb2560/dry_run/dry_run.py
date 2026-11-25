"""Edition 7 dry run: every new command reaches its argparse and lists its jobs (no harness run).

Usage: python -I -B dry_run.py <worktree> <out json>
Runs each command with the dynamics-dev interpreter from the worktree root, records the exit
code and the last stdout lines; no command writes a run output (``--list`` / refusals only).
The 12b ``--edition 7`` command runs on a synthetic root (blind-named folders included) and
writes its plans into ``dry_outputs/plans_12b`` (the one command that writes, by design).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

DYNAMICS = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
MAIN_JSONL = (r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5"
              r"\main.jsonl")
NOISE_VB = (r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1"
            r"\h8_noise_VB.json")


def synthetic_root(scratch: Path) -> tuple[Path, Path, Path]:
    """A ``06_analysis`` with the edition 7 blind layout (their files hold a colliding key)."""
    root = scratch / "synthetic" / "06_analysis"
    run = root / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713"
    key_text = json.dumps({"key": "L2|s50|g6|0|x0|top|Fs0"})
    for folder in (run / "cdry_a1" / "VBK_c92_b1", run / "cdry_a1" / "logs",
                   run / "cdry_a1" / "VBK0_c92"):
        folder.mkdir(parents=True)
        text = "{}" if folder.name == "VBK0_c92" else key_text
        (folder / "run.json").write_text(text, encoding="utf-8")
    tests = scratch / "synthetic" / "05_tests"
    tests.mkdir()
    return root, tests, run


def main() -> int:
    worktree, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    scratch = out_path.parent / "dry_outputs"
    coupled = "04_scripts/04_hydraulic/coupled"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "none.json").write_text("{}", encoding="utf-8")
    scan_root, tests, run = synthetic_root(scratch)
    commands = {
        "probe_list_all": [f"{coupled}/ed7_probe.py", "--out", str(scratch / "p.jsonl"),
                           "--list", "--workers", "20", "--mask", "0x0FFFFFFF"],
        "probe_list_d": [f"{coupled}/ed7_probe.py", "--out", str(scratch / "p.jsonl"),
                         "--list", "--part", "d"],
        "probe_bad_arm": [f"{coupled}/ed7_probe.py", "--out", str(scratch / "p.jsonl"),
                          "--arms", "a9"],
        "j9_main_list": [f"{coupled}/run_v5.py", "ed7_j9_main", "--list", "--out",
                         str(scratch / "ed7_j9_main.jsonl")],
        "cases_list": [f"{coupled}/run_v5.py", "ed7_cases", "--list", "--out",
                       str(scratch / "ed7_cases.jsonl")],
        "t8_list": [f"{coupled}/run_v5.py", "ed7_t8", "--list", "--out",
                    str(scratch / "ed7_t8.jsonl"), "--p3-hash-source", MAIN_JSONL],
        "keys_refused": [f"{coupled}/run_v5.py", "ed7_keys", "--list", "--out",
                         str(scratch / "ed7_keys.jsonl"), "--jobs-file",
                         str(scratch / "none.json")],
        "condition_input_error": [f"{coupled}/jp3_rev7_condition.py", "--rows",
                                  str(scratch / "none.jsonl"), "--out",
                                  str(scratch / "condition.json")],
        "plan_12b_ed7_synthetic": [f"{coupled}/jp3_12b_plan.py", "--noise", NOISE_VB,
                                   "--scan-root", str(scan_root), "--scan-extra", str(tests),
                                   "--scan-required", str(run), "--edition", "7",
                                   "--out-dir", str(scratch / "plans_12b")],
        "plan_12b_ed7_blind_root_refused": [
            f"{coupled}/jp3_12b_plan.py", "--noise", NOISE_VB, "--scan-root", str(scan_root),
            "--scan-extra", str(tests), "--scan-required", str(run / "cdry_a1" / "logs"),
            "--edition", "7", "--out-dir", str(scratch / "plans_12b_refused")],
    }
    record = {"worktree": str(worktree), "python": DYNAMICS, "runs": {}}
    for name, arguments in commands.items():
        done = subprocess.run([DYNAMICS, "-I", "-B", *arguments], cwd=worktree,
                              capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "MKL_THREADING_LAYER": "TBB",
                                   "PYTHONDONTWRITEBYTECODE": "1"}, timeout=600)
        lines = (done.stdout + done.stderr).strip().splitlines()
        record["runs"][name] = {"argv": ["python", "-I", "-B", *arguments],
                                "exit": done.returncode, "tail": lines[-3:],
                                "stdout_lines": len(done.stdout.splitlines())}
    selection = scratch / "plans_12b" / "selection.json"
    if selection.is_file():
        text = selection.read_text(encoding="utf-8")
        document = json.loads(text)
        record["plan_12b_check"] = {
            "seeds": [block["seed_index"] for block in document["blocks"].values()],
            "blind_prefixes_applied": document["inputs"].get("blind_prefixes_applied"),
            "blind_names_in_outputs": sorted(
                {name for path in selection.parent.iterdir()
                 for name in ("VBK_c92", "VBK_c93", "cdry_a1/logs", "cdry_a1\\\\logs")
                 if name in path.read_text(encoding="utf-8")})}
    record["files_in_scratch_after"] = sorted(path.name for path in scratch.iterdir())
    out_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps({name: (run["exit"], run["tail"][-1] if run["tail"] else "")
                      for name, run in record["runs"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
