"""End-to-end check of the runner path: one regression id and one r79 filter through make_runner + pwsh, commit per process.

Everything is written under ``probe_out/runner_test`` next to this file, the provenance
files included (``steps_E1.json`` points ``ACC_PROVENANCE`` at the main checkout's
``acceptance/provenance/reg*.json``, which a run from a worktree used to overwrite). The
work runs only as a script: pytest collects ``*_test.py`` files, and importing this one
must not start a run.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_out" / "runner_test"
STEP_IDS = ("reg1", "reg4")


def _steps() -> list[dict]:
    """reg1 / reg4 of ``steps_E1.json`` shrunk to one case each, every output under OUT."""
    steps = json.loads((HERE / "steps_E1.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in steps}
    reg1 = dict(by_id["reg1"])
    reg1["cmd"] = re.sub(r'--ids "[^"]*"', '--ids "H1|J1|B|top|flat"', reg1["cmd"])
    reg1["cmd"] = re.sub(r"--out \S+", lambda m: f"--out {OUT / 'clip_harness.json'}", reg1["cmd"])
    reg1["cmd"] = reg1["cmd"].replace("--workers 8", "--workers 1").replace("0x00FF0000", "0x0F000000")
    reg4 = dict(by_id["reg4"])
    reg4["cmd"] = re.sub(r"\S+clip_r79_L1L2\.json", lambda m: str(OUT / "clip_r79.json"), reg4["cmd"]).rstrip()
    reg4["cmd"] = reg4["cmd"][:-2] + " 2"
    reg4["env"] = {**reg4["env"], "R79_FILTER": "L1|s0|ref|16|,L2|s0|ref|16|", "R79_AFFINITY": "0x0F000000"}
    for step in (reg1, reg4):
        provenance = OUT / "provenance" / f"{step['id']}.json"
        step["env"] = {**step["env"], "ACC_PROVENANCE": str(provenance)}
    return [reg1, reg4]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "provenance").mkdir(parents=True)
    steps_file = OUT / "steps.json"
    steps_file.write_text(json.dumps(_steps(), indent=1), encoding="utf-8")
    py = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe"
    runner = OUT / "runner.ps1"
    subprocess.run([py, "-I", "-B", r"C:\Users\jinbeom\.claude\tools\cpu-scheduler\make_runner.py", "--steps", str(steps_file), "--out", str(runner), "--mask", "0x0F000000",
                    "--priority", "BelowNormal", "--skip-done", "--log-dir", str(OUT / "logs"), "--job-memory-mb", "3500", "--job-kill-on-close"], check=True, capture_output=True, timeout=60)
    t0 = time.perf_counter()
    proc = subprocess.Popen(["pwsh", "-NoProfile", "-File", str(runner)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    parent = psutil.Process(proc.pid)
    peak_commit, peak_total = 0.0, 0.0
    while proc.poll() is None:
        total = 0.0
        try:
            for p in parent.children(recursive=True):
                try:
                    if "python" in p.name().lower():
                        v = p.memory_info().vms
                        total += v
                        peak_commit = max(peak_commit, v)
                except psutil.Error:
                    pass
        except psutil.Error:
            break
        peak_total = max(peak_total, total)
        time.sleep(1)
    print("exit", proc.returncode, "wall", round(time.perf_counter() - t0, 1), "peak commit one python MB", round(peak_commit / 2**20), "tree MB", round(peak_total / 2**20))
    for name in STEP_IDS:
        log = (OUT / "logs" / f"{name}.log")
        print(name, "done", (OUT / "logs" / f"{name}.done").exists(), log.read_text(encoding="utf-8", errors="replace")[-500:] if log.exists() else "no log")
    for f in OUT.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f.name, list(d.keys())[:5], len(d.get("records", d.get("results", []))))


if __name__ == "__main__":
    main()
