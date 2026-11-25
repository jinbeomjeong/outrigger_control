"""Edition 7 dry run: every new command reaches its argparse and lists its jobs (no harness run).

Usage: python -I -B dry_run.py <worktree> <out json>
Runs each command with the dynamics-dev interpreter from the worktree root, records the exit
code and the last stdout lines; no command writes a run output (``--list`` / refusals only).
"""
import json
import subprocess
import sys
from pathlib import Path

DYNAMICS = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
MAIN_JSONL = (r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5"
              r"\main.jsonl")


def main() -> int:
    worktree, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    scratch = out_path.parent / "dry_outputs"
    coupled = "04_scripts/04_hydraulic/coupled"
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
    }
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "none.json").write_text("{}", encoding="utf-8")
    record = {"worktree": str(worktree), "python": DYNAMICS, "runs": {}}
    for name, arguments in commands.items():
        done = subprocess.run([DYNAMICS, "-I", "-B", *arguments], cwd=worktree,
                              capture_output=True, text=True, encoding="utf-8",
                              env={**__import__("os").environ, "MKL_THREADING_LAYER": "TBB",
                                   "PYTHONDONTWRITEBYTECODE": "1"}, timeout=600)
        lines = (done.stdout + done.stderr).strip().splitlines()
        record["runs"][name] = {"argv": ["python", "-I", "-B", *arguments],
                                "exit": done.returncode, "tail": lines[-3:],
                                "stdout_lines": len(done.stdout.splitlines())}
    created = sorted(path.name for path in scratch.iterdir())
    record["files_in_scratch_after"] = created
    out_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps({name: (run["exit"], run["tail"][-1] if run["tail"] else "")
                      for name, run in record["runs"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
