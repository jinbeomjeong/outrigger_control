"""S6 stage 2 item 1c: share of the final corrective loads A+F caused by the pad horizontal forces (Chrono).

At the run end (mean of the last 1 s, pads.npz 1 ms): horizontal world part of every pad reaction R_world, its
moment about the body COM line through the contact points (only the height differences between pads and the
lever arm to the COM height matter for a horizontal couple), converted to the per-leg vertical corrective loads that
balance it: dF = A+ [0, M_x, M_y] with A rows (1, y_i, -x_i) (roll / pitch moment of vertical leg loads).
Compared with the item-1c difference (Chrono - reduced corrective) of verify_S6_L1_closed_loop.json.
Run: conda run -n dynamics-dev python -I s6s2_corrective.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
CASES = ["G1_top_flat", "G1_top_roll3", "G1_top_diag3"]


def main():
    out = {}
    for c in CASES:
        d = ROOT / "07_results" / "S6" / "stage2_20261021_213235" / c
        pz = np.load(d / "pads.npz")
        t = pz["t"]
        m = t >= t[-1] - 1.0
        R = pz["R_world"][m].mean(axis=0)            # (4, 3) N
        P = pz["contact_point_world"][m].mean(axis=0)  # (4, 3) m
        H = R.copy(); H[:, 2] = 0.0
        ref = P.mean(axis=0)
        M = np.sum(np.cross(P - ref, H), axis=0)     # moment of the horizontal forces about the pad centroid
        xy = P[:, :2] - ref[:2]
        A = np.column_stack([np.ones(4), xy[:, 1], -xy[:, 0]])  # vertical loads -> (Fz, M_x, M_y) (world, deck level)
        dF = np.linalg.pinv(A.T) @ np.array([0.0, -M[0], -M[1]])
        out[c] = {"H_kN": (H[:, :2] / 1e3).round(2).tolist(), "pad_z_mm": ((P[:, 2] - ref[2]) * 1e3).round(1).tolist(),
                  "M_kNm": (M / 1e3).round(3).tolist(), "dF_corrective_kN": (dF / 1e3).round(3).tolist(),
                  "dF_max_kN": round(float(np.max(np.abs(dF))) / 1e3, 3)}
        print(c, out[c])
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
