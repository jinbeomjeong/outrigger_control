"""IMU 10 ms specific-force tilt noise per controller phase, L1 vs L2b (read-only).

Spec ``s6_control_spec.md`` rev. 37 195.1 (control-expert re-analysis, moved from the session
scratchpad 2026-10-24). Reads ``r8_series.npz`` (``phase``, ``imu_samples`` = the ten 10 ms box
means of each 0.1 s control period) of every case of a ``run_S7C.py`` batch and prints, per
phase, the within-period standard deviation of roll / pitch [deg] and the standard deviation of
the period-mean differences.

Run (project root; dynamics-dev or Chrono-dev)::

    python -I 04_scripts/03_control/s7c/imu_noise.py [--batch 07_results/S7/<batch>]
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BATCH = "07_results/S7/ctrl3_20261024_154939"

ap = argparse.ArgumentParser()
ap.add_argument("--batch", default=DEFAULT_BATCH, help="batch dir (relative to the project root)")
args = ap.parse_args()
B = Path(args.batch) if Path(args.batch).is_absolute() else ROOT / args.batch
vj = json.loads((B / "verify_S7C.json").read_text(encoding="utf-8"))
cases = [m["case"] for m in vj["metrics"]]


def tilt_deg(f):
    """Roll, pitch [deg] from the specific force in body axes (at rest f = +g up)."""
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    roll = np.degrees(np.arctan2(fy, fz))
    pitch = np.degrees(np.arctan2(-fx, np.hypot(fy, fz)))
    return roll, pitch


print(f"{'case':34s} {'phase':8s} {'n':>5s} {'std roll':>9s} {'std pitch':>9s} "
      f"{'per-period mean std r/p [deg]':>30s}")
for c in cases:
    s = np.load(B / c / "r8_series.npz")
    ph = s["phase"]
    imu = s["imu_samples"]  # (n, 10, 3) 10 ms box means within each 0.1 s period
    r, p = tilt_deg(imu)
    for name in ("check", "touch", "level", "probe", "ready"):
        k = ph == name
        if k.sum() < 3:
            continue
        rr, pp = r[k], p[k]
        # within-period scatter (noise around the period mean) and std of period means
        within_r = (rr - rr.mean(1, keepdims=True)).std()
        within_p = (pp - pp.mean(1, keepdims=True)).std()
        print(f"{c:34s} {name:8s} {k.sum():5d} {within_r:9.4f} {within_p:9.4f} "
              f"{np.std(np.diff(rr.mean(1))):14.4f} {np.std(np.diff(pp.mean(1))):9.4f}")
