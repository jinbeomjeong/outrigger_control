"""Grid-phase band of SCM static pad sinkage (geometry + Bekker only, no Chrono).

SCM (PyChrono 10.0): node force = sigma * m_area, m_area = delta^2 (SCMTerrain.cpp:584-588, 1475);
sigma = (oob*Kc + Kphi) z^n with oob = P_hull / (2 A_hull) of the convex hull of the patch node points
(SCMTerrain.cpp:1366-1377, 1445). For a flat rigid pad all contact nodes share z, so
  z_grid = (F / (N_h d^2 (Kc/b_hull + Kphi)))^(1/n)   (P1 V16: Chrono = this within 0.05 %).
Continuum reference (harness s9_soil_closed_loop.py:143-146): A_poly, b_poly = 2A/P of the polygon.
Factor f = z_grid / z_cont = [(N_h d^2 k_hull) / (A_poly k_poly)]^(-1/n), independent of F.
Delta z between two loads scales by the same f (z ~ F^(1/n)).
"""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(r"C:\workspace\outrigger_control")
pv = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))["variants"]["dwg_rear250"]["legs"]
soils = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))["sets"]
NOFF = 24


def poly_of(leg):
    p = np.array([[float(v) for v in s.split()] if isinstance(s, str) else s for s in pv[leg]["polygon_xy_m"]], float)
    return p


def inside(poly, pts):
    n = len(poly)
    sgn = np.sign(np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
    ok = np.ones(len(pts), bool)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        cr = (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0])
        ok &= sgn * cr > 1e-12
    return ok


def scan(leg, d):
    poly = poly_of(leg)
    A = pv[leg]["bottom_area_m2"]
    bp = pv[leg]["bekker_b_m"]
    out = []
    g = np.arange(-0.4, 0.4 + 1e-9, d)
    offs = [(0.0, 0.0)] + [(ox, oy) for ox in np.arange(NOFF) * d / NOFF for oy in np.arange(NOFF) * d / NOFF]
    for ox, oy in offs:
        X, Y = np.meshgrid(g + ox, g + oy, indexing="ij")
        P = np.c_[X.ravel(), Y.ravel()]
        m = inside(poly, P)
        h = ConvexHull(P[m])
        out.append((m.sum(), m.sum() * d * d, 2 * h.volume / h.area))
    return np.array(out), A, bp


def factor(row, A, bp, s):
    N, Aeff, bh = row
    kh = s["Kc"] / bh + s["Kphi"]
    kp = s["Kc"] / bp + s["Kphi"]
    return ((Aeff * kh) / (A * kp)) ** (-1.0 / s["n"])


res = {}
for leg in ("FL", "RL"):
    for d in (0.02, 0.01, 0.005):
        a, A, bp = scan(leg, d)
        res[(leg, d)] = (a, A, bp)
        print(f"{leg} d={d}: N {int(a[1:,0].min())}..{int(a[1:,0].max())} (offset0 {int(a[0,0])}), A_eff/A "
              f"{a[1:,1].min()/A:.4f}..{a[1:,1].max()/A:.4f} (o0 {a[0,1]/A:.4f}), b_hull {a[1:,2].min():.4f}..{a[1:,2].max():.4f} "
              f"(o0 {a[0,2]:.4f}; poly {bp:.4f}); one-node dA/A {d*d/A:.4f}")
        for key in ("J1", "J2", "S1", "G1"):
            s = soils[key]["chrono"]
            f = np.array([factor(r, A, bp, s) for r in a])
            fp = f[1:]
            print(f"    {key} (n={s['n']}): f-1 phase min {fp.min()-1:+.4f} max {fp.max()-1:+.4f} mean {fp.mean()-1:+.4f} "
                  f"sd {fp.std():.4f}; offset0 {f[0]-1:+.4f}; one-node dz/z {d*d/(s['n']*A):.4f}")

print("\nSingle-pad test (offset 0, J2), loads RL 72.85->74.85 kN, FL 119.59->122.01 kN [mm]:")
s = soils["J2"]["chrono"]
for leg, (N1, N2) in (("RL", (72850.0, 74850.0)), ("FL", (119590.0, 122010.0))):
    A, bp = pv[leg]["bottom_area_m2"], pv[leg]["bekker_b_m"]
    zc = [(N / (A * (s["Kc"] / bp + s["Kphi"]))) ** (1 / s["n"]) for N in (N1, N2)]
    print(f"  {leg} continuum z1 {zc[0]*1e3:.2f} z2 {zc[1]*1e3:.2f} dz {(zc[1]-zc[0])*1e3:.2f}  dz/z2 {(zc[1]-zc[0])/zc[1]:.4f}")
    for d in (0.02, 0.01, 0.005):
        a, _, _ = res[(leg, d)]
        f0 = factor(a[0], A, bp, s)
        fp = np.array([factor(r, A, bp, s) for r in a[1:]])
        print(f"    d={d}: offset0 z2 {zc[1]*f0*1e3:7.2f} dz {(zc[1]-zc[0])*f0*1e3:6.2f}; phase z2 {zc[1]*fp.min()*1e3:.1f}..{zc[1]*fp.max()*1e3:.1f}"
              f" dz {(zc[1]-zc[0])*fp.min()*1e3:.2f}..{(zc[1]-zc[0])*fp.max()*1e3:.2f}")
