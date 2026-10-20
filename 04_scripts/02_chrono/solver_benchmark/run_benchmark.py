"""Linear-solver benchmark driver: one bench_case.py process per configuration, serially.

Usage (Chrono-dev python, from any folder):
  python -I -u run_benchmark.py <l1|scm|scale|all> [--smoke] [--report]
    l1 / scm / scale / all : benchmark phases (all ~45 min on the 2026-10-20 PC, of which the two
                             N = 500 SPARSE_QR cases take ~27 min)
    --smoke                : short windows, results under 07_results/solver_benchmark_smoke
    --report               : afterwards run summarize.py and make_gifs.py (all three GIFs)
Results: 07_results/solver_benchmark/<phase>/<case>.json and log.txt (git-ignored).
MKL_NUM_THREADS is set only in the child environment. stdin = DEVNULL, timeout per process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I: the script folder is not on sys.path
import bench_common as bcm  # noqa: E402

PY = sys.executable
RES = bcm.RESULTS_DIR
SCM_PARAMS = bcm.SCM_PARAMS

SOLVER_VARIANTS = [  # (solver, lock, MKL_NUM_THREADS or None = default)
    ("SPARSE_QR", False, None),
    ("SPARSE_QR", True, None),
    ("SPARSE_LU", False, None),
    ("SPARSE_LU", True, None),
    ("PARDISO_MKL", False, None),
    ("PARDISO_MKL", True, None),
    ("PARDISO_MKL", False, "1"),
    ("PARDISO_MKL", True, "1"),
]


def tag(solver: str, lock: bool, thr: str | None) -> str:
    short = {"SPARSE_QR": "QR", "SPARSE_LU": "LU", "PARDISO_MKL": "PARDISO"}[solver]
    return f"{short}_lock{int(lock)}_thr{thr or 'def'}"


def run(phase: str, name: str, cfg: dict, thr: str | None, timeout: float) -> dict | None:
    out_dir = RES / phase
    RES.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.json"
    cfg = dict(cfg, out=str(out))
    cfg_path = out_dir / f"{name}.cfg.json"
    cfg_path.write_text(json.dumps(cfg))
    env = dict(os.environ)
    env.pop("MKL_NUM_THREADS", None)
    if thr is not None:
        env["MKL_NUM_THREADS"] = thr
    t0 = time.perf_counter()
    try:
        done = subprocess.run(
            [PY, "-I", "-u", str(HERE / "bench_case.py"), str(cfg_path)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        status = f"rc={done.returncode & 0xFFFFFFFF:#x}"
        tail = (done.stdout.strip().splitlines() or [""])[-1]
        err = (done.stderr.strip().splitlines() or [""])[-3:]
    except subprocess.TimeoutExpired:
        status, tail, err = "TIMEOUT", "", []
    wall = time.perf_counter() - t0
    err_text = " | ".join(err) if status != "rc=0x0" else ""
    line = f"{phase}/{name}: {status} {wall:.1f}s {tail} {err_text}"
    print(line, flush=True)
    with open(RES / "log.txt", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    if out.is_file() and status == "rc=0x0":
        r = json.loads(out.read_text())
        r["process_wall_s"] = wall
        out.write_text(json.dumps(r, indent=1))
        return r
    return None


def phase_l1(smoke: bool) -> None:
    for dt in (1e-4, 1e-5):
        for solver, lock, thr in SOLVER_VARIANTS:
            cfg = {
                "model": "l1",
                "solver": solver,
                "lock": lock,
                "dt": dt,
                "warmup": 200 if smoke else 1000,
                "steps": 200 if smoke else 3000,
                "reps": 3,
            }
            run("l1", f"dt{dt:.0e}_{tag(solver, lock, thr)}", cfg, thr, 600)


def phase_scm(smoke: bool, variants=None) -> None:
    variants = variants or [v for v in SOLVER_VARIANTS if v[1] or v[0] == "SPARSE_QR"]
    for delta in (0.05, 0.02, 0.01):
        for solver, lock, thr in variants:
            cfg = {
                "model": "scm",
                "solver": solver,
                "lock": lock,
                "dt": 1e-4,
                "scm_params": SCM_PARAMS,
                "scm_size": [8.0, 6.0],
                "scm_delta": delta,
                "scm_domains": True,
                "warmup": 100 if smoke else 1000,
                "steps": 100 if smoke else 1000,
                "reps": 3,
            }
            run("scm", f"d{delta:g}_{tag(solver, lock, thr)}", cfg, thr, 900)


def phase_scale(smoke: bool, Ns=(5, 20, 50, 100, 200, 500), variants=None) -> None:
    variants = variants or [
        v for v in SOLVER_VARIANTS if v[1] or (v[0] == "PARDISO_MKL" and v[2] is None)
    ]
    for topo in ("grid", "chain"):
        for N in Ns:
            for solver, lock, thr in variants:
                cfg = {
                    "model": topo,
                    "N": N,
                    "solver": solver,
                    "lock": lock,
                    "dt": 1e-4,
                    "warmup": 100,
                    "steps": 200 if smoke else 5000,
                    "reps": 3,
                    "target_s": 0.5 if smoke else 2.0,
                    "min_steps": 30,
                }
                run("scale", f"{topo}_N{N}_{tag(solver, lock, thr)}", cfg, thr, 900)


if __name__ == "__main__":
    phase = sys.argv[1]
    smoke = "--smoke" in sys.argv
    if smoke:
        RES = bcm.RESULTS_DIR.with_name("solver_benchmark_smoke")
    t = time.perf_counter()
    if phase in ("l1", "all"):
        phase_l1(smoke)
    if phase in ("scm", "all"):
        phase_scm(smoke)
    if phase in ("scale", "all"):
        phase_scale(smoke)
    if phase == "smoke1":
        RES = bcm.RESULTS_DIR.with_name("solver_benchmark_smoke")
        run(
            "smoke",
            "l1_qr",
            {
                "model": "l1",
                "solver": "SPARSE_QR",
                "lock": False,
                "dt": 1e-4,
                "warmup": 200,
                "steps": 200,
                "reps": 2,
            },
            None,
            300,
        )
        run(
            "smoke",
            "l1_pardiso",
            {
                "model": "l1",
                "solver": "PARDISO_MKL",
                "lock": True,
                "dt": 1e-4,
                "warmup": 200,
                "steps": 200,
                "reps": 2,
            },
            None,
            300,
        )
        run(
            "smoke",
            "scm_qr",
            {
                "model": "scm",
                "solver": "SPARSE_QR",
                "lock": False,
                "dt": 1e-4,
                "scm_params": SCM_PARAMS,
                "scm_size": [8.0, 6.0],
                "scm_delta": 0.05,
                "warmup": 200,
                "steps": 200,
                "reps": 2,
            },
            None,
            300,
        )
        run(
            "smoke",
            "grid_qr",
            {
                "model": "grid",
                "N": 20,
                "solver": "SPARSE_QR",
                "dt": 1e-4,
                "warmup": 50,
                "steps": 200,
                "reps": 2,
            },
            None,
            300,
        )
        run(
            "smoke",
            "chain_pardiso",
            {
                "model": "chain",
                "N": 20,
                "solver": "PARDISO_MKL",
                "dt": 1e-4,
                "warmup": 50,
                "steps": 200,
                "reps": 2,
            },
            None,
            300,
        )
    if "--report" in sys.argv and phase != "smoke1":
        for script, arg in (("summarize.py", None), ("make_gifs.py", "all")):
            cmd = [PY, "-I", "-u", str(HERE / script)] + ([arg] if arg else [])
            subprocess.run(cmd, stdin=subprocess.DEVNULL, timeout=1800, check=True)
    print(f"total {time.perf_counter() - t:.1f}s", flush=True)
