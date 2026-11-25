"""Run the edition 7 check runner on the a6fc3dd5 tree and the working tree for the VBM jobs
and compare the command hashes (P7-1 preview relation, changed lines). Scratch helper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS_PYTHON = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
R12 = {"case": "R12", "eps": 0.0, "offset_s": 0.0}
S5 = {"case": "S5", "eps": 0.0}
JOBS = {"VBM_R12": {**R12, "setting": "VBM"}, "VBM0_R12": {**R12, "setting": "VBM0"},
        "VBMslow_S5": {**S5, "setting": "VBMslow"}, "VBMslow_R12": {**R12, "setting": "VBMslow"}}


def main() -> None:
    scratch, old_tree, new_tree = (Path(arg) for arg in sys.argv[1:4])
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    processes = {}
    for tree_name, tree in (("old", old_tree), ("new", new_tree)):
        runner = tree / "05_tests" / "unit" / "ed7_check_runner.py"
        for name, job in JOBS.items():
            folder = scratch / "runs" / tree_name / name
            if (folder / "report.json").is_file():
                continue  # a finished run of an earlier call
            if folder.exists():
                folder.rename(folder.with_name(f"{name}_failed_{len(list(folder.parent.iterdir()))}"))
            folder.mkdir(parents=True)
            processes[(tree_name, name)] = subprocess.Popen(
                [HARNESS_PYTHON, "-I", "-B", str(runner), json.dumps(job), str(folder / "t4h"),
                 str(folder / "report.json")], cwd=folder, env=environment,
                stdout=subprocess.DEVNULL, stderr=open(folder / "stderr.txt", "w",
                                                      encoding="utf-8"))
    summary = {}
    for tree_name, name in ((tree, job) for tree in ("old", "new") for job in JOBS):
        process = processes.get((tree_name, name))
        code = 0 if process is None else process.wait(timeout=3600)
        report_path = scratch / "runs" / tree_name / name / "report.json"
        report = (json.loads(report_path.read_text(encoding="utf-8"))
                  if report_path.is_file() else {})
        summary.setdefault(name, {})[tree_name] = {
            "exit": code, "hash": report.get("hash"), "final_phase": report.get("final_phase"),
            "foreign_modules": report.get("foreign_modules")}
    for name, entry in summary.items():
        entry["same"] = entry["old"]["hash"] == entry["new"]["hash"]
    summary["p7_1_new_vbm_eq_vbm0_r12"] = (summary["VBM_R12"]["new"]["hash"]
                                         == summary["VBM0_R12"]["new"]["hash"])
    summary["p7_1_old_vbm_eq_vbm0_r12"] = (summary["VBM_R12"]["old"]["hash"]
                                         == summary["VBM0_R12"]["old"]["hash"])
    (scratch / "vbm_compare.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
