"""S6 stage 2, G1 roll 3 deg tail: commanded vs actual pitch rate (is the P action reaching the body?).

Commanded body rates from the leg command u (u_cmd, u_applied) by least squares on the support matrix
u_i = z_dot + y_i phi_dot - x_i theta_dot (+ twist), pad xy from 02_params via outrigger_sim.params.
Actual pitch rate from the truth quaternion. Also mean-stroke rate and the stroke_true - s_motor change (oil).
Run: conda run -n dynamics-dev python -I s6s2_tail_rate.py <project_root>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "03_src"))
from outrigger_sim.params import load_params  # noqa: E402


def quat_rp(q):
    w, x, y, z = q.T
    return (np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))),
            np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))))


def main():
    p = load_params()
    xy = np.array([leg.pad_bottom_center_retracted_m[:2] for leg in p.legs]) if hasattr(p.legs[0], "pad_bottom_center_retracted_m") else None
    if xy is None:
        raw = p.raw["legs"]
        xy = np.array([raw[n]["pad_bottom_center_retracted_m"][:2] for n in ("FL", "FR", "RL", "RR")])
    n = np.array([0.476, -0.476, -0.523, 0.523])
    A = np.column_stack([np.ones(4), xy[:, 1], -xy[:, 0], n])
    Ai = np.linalg.pinv(A)
    d = ROOT / "07_results" / "S6" / "stage2_20261021_213235" / "G1_top_roll3"
    r = json.loads((d / "result.json").read_text())
    z = np.load(d / "record" / "record.npz")
    t = z["t"] - r["settings"]["start_t_s"]
    tl = next(tt for tt, nm in r["phases"] if nm == "level")
    ro, pi = quat_rp(z["body_quat_wxyz"])
    dpi = np.gradient(pi, t)
    for key in ("u_cmd", "u_applied"):
        q = z[key] @ Ai.T
        print(key)
        for k in range(8, 19, 2):
            m = (t >= tl + k) & (t < tl + k + 2)
            print(f"  {k:2d}-{k + 2:2d} s: cmd th_dot {np.degrees(q[m, 2]).mean():+.5f} deg/s, z_dot {q[m, 0].mean() * 1e3:+.4f} mm/s, "
                  f"actual th_dot {dpi[m].mean():+.5f} deg/s, pitch {pi[m].mean():+.4f}")
    so = (z["stroke_true"] - z["s_motor"]) * 1e3
    for k in (8, 12, 16):
        m = (t >= tl + k) & (t < tl + k + 2)
        print(f"  oil comp (true - motor) mm at {k}s: {so[m].mean(axis=0).round(3)}")


if __name__ == "__main__":
    main()
