"""Illustrative phase factor f of the 4 machine pads on a level SCM plane (origin = world 0, grid 1 cm),
pad centre = YAML legs.<leg>.pad_bottom_center_retracted_m xy (ASSUMPTION: body origin at world xy 0, no tilt,
no horizontal pad shift). Also the sensitivity: f over a +-6 mm shift of the pad centre in x (tilted leg)."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(r"C:\workspace\outrigger_control")
pv = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))["variants"]["dwg_rear250"]["legs"]
soils = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))["sets"]
CENTRES = {"FL": (2.2938, 1.3238), "FR": (2.2938, -1.3238), "RL": (-2.556, 1.1679), "RR": (-2.556, -1.2429)}


def f_of(leg, cx, cy, d, s):
    poly = np.asarray(pv[leg]["polygon_xy_m"], float) + [cx, cy]
    A, bp = pv[leg]["bottom_area_m2"], pv[leg]["bekker_b_m"]
    i0, i1 = int(np.floor(poly[:, 0].min() / d)) - 1, int(np.ceil(poly[:, 0].max() / d)) + 1
    j0, j1 = int(np.floor(poly[:, 1].min() / d)) - 1, int(np.ceil(poly[:, 1].max() / d)) + 1
    I, J = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    P = np.c_[I.ravel() * d, J.ravel() * d]
    sgn = np.sign(np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
    ok = np.ones(len(P), bool)
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        ok &= sgn * ((b[0] - a[0]) * (P[:, 1] - a[1]) - (b[1] - a[1]) * (P[:, 0] - a[0])) > 1e-12
    h = ConvexHull(P[ok])
    bh = 2 * h.volume / h.area
    kh, kp = s["Kc"] / bh + s["Kphi"], s["Kc"] / bp + s["Kphi"]
    return int(ok.sum()), ((ok.sum() * d * d * kh) / (A * kp)) ** (-1 / s["n"])


for key in ("J1", "J2"):
    s = soils[key]["chrono"]
    for leg, (cx, cy) in CENTRES.items():
        N, f = f_of(leg, cx, cy, 0.01, s)
        fs = [f_of(leg, cx + dx, cy, 0.01, s)[1] for dx in np.linspace(-0.006, 0.006, 13)]
        print(f"{key} {leg}: nominal N {N} f-1 {f-1:+.4f}; x shift +-6 mm: f-1 {min(fs)-1:+.4f}..{max(fs)-1:+.4f}")
