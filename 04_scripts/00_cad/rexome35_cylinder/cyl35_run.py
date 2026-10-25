"""Run the cyl35_synth.py jobs in parallel child processes pinned to the E-cores (logical 16-27, mask 0x0FFF0000),
below-normal priority, then aggregate into the cache JSON (01_cad/02_legs/rexome35/)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
# Moved from the 2026-10-22 cad scratchpad (cad-run/cyl35/) on 2026-10-25: project root from the
# script location, job outputs (synth BREPs, per-job JSON / logs) in the project cache folder
# 01_cad/02_legs/rexome35/jobs/ instead of <scratchpad>/cyl35/jobs/.
PROJECT = Path(__file__).resolve().parents[3]
CACHE = PROJECT / "01_cad" / "02_legs" / "rexome35"
OUT = CACHE / "jobs"
E_CORES = list(range(16, 28))
JOBS = ([f"synth_moving_{l}" for l in ("RL", "RR", "FL", "FR")]
        + [f"synth_barrel_{l}" for l in ("RL", "RR", "FL", "FR")]
        + [f"cadmod_moving_{l}" for l in ("FL", "FR")] + [f"cadmod_barrel_{l}" for l in ("FL", "FR")]
        + ["synth_moving_yamlpad_FL"])
WORKERS = 12


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    psutil.Process().cpu_affinity(E_CORES)
    OUT.mkdir(exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    queue, running, t0 = list(JOBS), [], time.perf_counter()
    while queue or running:
        while queue and len(running) < WORKERS:
            j = queue.pop(0)
            log = (OUT / f"{j}.log").open("w", encoding="utf-8")
            pr = subprocess.Popen([sys.executable, "-I", "-X", "utf8", str(HERE / "cyl35_synth.py"), "--job", j,
                                   "--out", str(OUT), "--cache", str(CACHE)], stdout=log, stderr=subprocess.STDOUT,
                                  env=env, cwd=str(HERE))
            c = psutil.Process(pr.pid)
            c.cpu_affinity(E_CORES)
            c.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            running.append((j, pr))
        time.sleep(0.5)
        for item in list(running):
            if item[1].poll() is not None:
                running.remove(item)
                print(item[0], "exit", item[1].returncode, flush=True)
    results = {}
    for j in JOBS:
        p = OUT / f"{j}.json"
        results[j] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"error": "missing"}
    wall = time.perf_counter() - t0
    (OUT / "all_jobs.json").write_text(json.dumps({"wall_s": wall, "jobs": results}, indent=1), encoding="utf-8")
    print(f"wall {wall:.1f} s")


if __name__ == "__main__":
    main()
