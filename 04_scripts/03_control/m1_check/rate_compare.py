"""Harness vs Hopsan replay on R12, command-free part of the sink (read only).

Usage (dynamics-dev): python -I rate_compare.py <hopsan t4 folder> <out.json>
Separates the reported differences: the RR load per sink depth (8.1 vs 6.9 kN/mm) and the absolute level at the minimum.
Sink law: harness quintic depth(t) = D tau^3 (10 - 15 tau + 6 tau^2) (r67 branch), Hopsan t4 linear D tau (t4_replay.py),
tau = t / 2 s, D = 11.5 mm. Both are compared against time and against their own depth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[3] / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1b"
D_MM = 11.5
RAMP_S = 2.0
LEGS = ("FL", "FR", "RL", "RR")


def quintic(t):
    tau = np.clip(t / RAMP_S, 0.0, 1.0)
    return D_MM * tau**3 * (10.0 - 15.0 * tau + 6.0 * tau**2)


def linear(t):
    return D_MM * np.clip(t / RAMP_S, 0.0, 1.0)


def slope(depth, force, lo, hi):
    keep = (depth >= lo) & (depth <= hi)
    return float(np.polyfit(depth[keep], force[keep], 1)[0]) if keep.sum() > 5 else None


def main() -> None:
    hop_dir = Path(sys.argv[1])
    result = {"cases": {}}
    pairs = {"OFF_0.0": ("R12_OFF_0.0.npz", ("nocheck_OFF_0.npz", "vent_OFF_0.npz", "block_OFF_0.npz")),
             "OFF_0.025": ("R12_OFF_0.025.npz", ("nocheck_OFF_0.025.npz", "vent_OFF_0.025.npz", "block_OFF_0.025.npz"))}
    for tag, (harness_file, hop_files) in pairs.items():
        h = np.load(OUT / "series_r12" / harness_file)
        t = h["t"]
        F = h["F"] / 1e3
        moving = np.abs(h["u"]).max(axis=1) > 1e-6
        t_first_cmd = float(t[(t > 0) & moving][0])
        k0 = int(np.searchsorted(t, 0.0))
        row = {"t_first_command_s": t_first_cmd, "harness_F0": F[k0].tolist()}
        free = (t >= 0.0) & (t <= t_first_cmd)
        depth_q = quintic(t)
        row["harness_rate_vs_quintic_kN_mm"] = {leg: slope(depth_q[free], F[free, i], 0.5, 8.0) for i, leg in enumerate(LEGS)}
        row["harness_rate_vs_linear_wrong_kN_mm"] = {leg: slope(linear(t)[free], F[free, i], 0.5, 8.0) for i, leg in enumerate(LEGS)}
        row["harness_at"] = {f"+{v:g}": {"depth_quintic_mm": float(quintic(np.array(v))), "depth_linear_mm": float(linear(np.array(v))), "F": F[int(np.searchsorted(t, v))].round(2).tolist()} for v in (0.5, 0.8, 1.0, 1.2, 1.3, 1.4, 1.5)}
        k_min = int(np.argmin(F[t > 0, 3]))
        row["harness_RR_min"] = {"F": float(F[t > 0, 3][k_min]), "t": float(t[t > 0][k_min]), "depth_quintic_mm": float(quintic(t[t > 0][k_min]))}
        row["hopsan"] = {}
        for name in hop_files:
            d = np.load(hop_dir / name)
            th = d["t"]
            Fh = d["F"] / 1e3
            free_h = (th >= 0.0) & (th <= t_first_cmd)
            depth_l = linear(th)
            kmin = int(np.argmin(np.where(th > 0, Fh[:, 3], np.inf)))
            shifted = np.interp(row["harness_RR_min"]["t"], th, Fh[:, 3])
            same_depth_t = float(np.interp(row["harness_RR_min"]["depth_quintic_mm"], depth_l[th >= 0], th[th >= 0]))
            row["hopsan"][name] = {
                "F0": Fh[int(np.searchsorted(th, 0.0))].round(2).tolist(),
                "rate_vs_linear_kN_mm": {leg: slope(depth_l[free_h], Fh[free_h, i], 0.5, 8.0) for i, leg in enumerate(LEGS)},
                "at": {f"+{v:g}": {"depth_linear_mm": float(linear(np.array(v))), "F": Fh[int(np.searchsorted(th, v))].round(2).tolist()} for v in (0.5, 0.8, 1.0, 1.2, 1.3, 1.4, 1.5)},
                "RR_min": {"F": float(Fh[kmin, 3]), "t": float(th[kmin]), "depth_linear_mm": float(depth_l[kmin])},
                "RR_at_harness_min_time": float(shifted),
                "t_with_harness_min_depth_s": same_depth_t,
                "RR_at_harness_min_depth": float(np.interp(same_depth_t, th, Fh[:, 3]))}
        result["cases"][tag] = row
    (OUT / "rate_compare.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
