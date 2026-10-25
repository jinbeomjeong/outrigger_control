"""Grid / phase sensitivity of the S9 crawler settle replica (Poly345 ramp 3 s + hold 2 s, G1).

Node grids: (a) the replica default (np.arange from the active-domain corner, = P0 grid),
(b) Chrono phase: nodes at integer multiples of h in the SCM plane frame
    (SCMTerrain.cpp:1178 x = i * delta; S9 plane origin x = y = 0, body origin x = y = 0 at t = 0),
(c) phase sweep: offset (dx, dy) in [0, h) to show the grid-phase range.
Frame: body x forward, z up, pitch > 0 nose down; SI.
Gravity (0, 0, -9.80665) ramped (Poly345 3 s).
Usage (dynamics-dev):
  python -I 04_scripts/01_dynamics/s9_crawler_replica_grid_phase.py <out.json> [conv]
  conv = grid convergence 4 / 2 / 1 / 0.5 cm on the Chrono phase; default = phase sweep.
Output: JSON to argv[1].
"""
import json
import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT / "04_scripts" / "01_dynamics"))
import run_pad_bekker_p0 as p0  # noqa: E402
import s9_crawler_rocking_replica as rr  # noqa: E402

orig_nodes = p0.crawler_nodes


def nodes_phase(h, ox, oy):
    def f(hh=h):
        x0, x1 = p0.DOM["x_m"]
        y0, y1 = p0.DOM["y_m"]
        xs = (np.ceil((x0 - ox) / hh) + np.arange(0, int((x1 - x0) / hh) + 2)) * hh + ox
        xs = xs[(xs >= x0) & (xs < x1)]
        ys = (np.ceil((y0 - oy) / hh) + np.arange(0, int((y1 - y0) / hh) + 2)) * hh + oy
        ys = ys[(ys >= y0) & (ys < y1)]
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        hb = np.full(X.shape, np.inf)
        xr0, xf0 = -p0.RAMP["rear"]["x0"], p0.RAMP["front"]["x0"]
        boxes = [(xr0, xf0, 0.0, 0.0, 0.0),
                 (xf0, max(p0.END_ST) + p0.BLK_X / 2, 0.0, xf0, p0.RAMP["front"]["slope"]),
                 (min(p0.END_ST) - p0.BLK_X / 2, xr0, 0.0, xr0, -p0.RAMP["rear"]["slope"])]
        for (a, b, h0, xr, s) in boxes:
            m = (X >= a) & (X <= b) & (Y >= p0.BLK_Y0) & (Y <= p0.BLK_Y1)
            hb = np.where(m, np.minimum(hb, h0 + s * (X - xr)), hb)
        return X, Y, hb
    return f


def run(h, phase=None):
    p0.crawler_nodes = orig_nodes if phase is None else nodes_phase(h, *phase)
    md = rr.build("G1", h)
    out, _ = rr.simulate(md, 5.0, ramp=3.0, shape="poly345")
    t, th, zo = out[:, 0], out[:, 1], out[:, 3]
    sel = t >= 4.0
    return dict(h=h, phase=phase, pitch_mean=float(th[sel].mean()),
                pitch_pp=float(np.ptp(th[sel])),
                z0_mm=float(zo[sel].mean() * 1e3), ncols=int(len(md["x"])),
                area=float(md["w"].sum()))


P0 = dict(pitch=0.14184448177581582, z0=-1.2267655100074597)
res = []
if len(sys.argv) > 2 and sys.argv[2] == "conv":
    x0, x1 = p0.DOM["x_m"]
    print("DOM", p0.DOM, "block y", p0.BLK_Y0, p0.BLK_Y1, "width", p0.BLK_Y1 - p0.BLK_Y0)
    for h in (0.04, 0.02, 0.01, 0.005):
        r = run(h, (0.0, 0.0))
        r["pitch_rel_P0"] = r["pitch_mean"] / P0["pitch"] - 1
        r["z0_rel_P0"] = r["z0_mm"] / P0["z0"] - 1
        print(json.dumps(r))
        res.append(r)
    Path(sys.argv[1]).write_text(json.dumps(dict(P0=P0, runs=res), indent=1), "utf-8")
    sys.exit(0)
res.append(run(0.02))
res.append(run(0.02, (0.0, 0.0)))
res.append(run(0.04, (0.0, 0.0)))
for ox in (0.01, 0.02, 0.03):
    res.append(run(0.04, (ox, 0.0)))
for oy in (0.01, 0.02, 0.03):
    res.append(run(0.04, (0.0, oy)))
for ox in (0.005, 0.01, 0.015):
    res.append(run(0.02, (ox, 0.0)))
for r in res:
    r["pitch_rel_P0"] = r["pitch_mean"] / P0["pitch"] - 1
    r["z0_rel_P0"] = r["z0_mm"] / P0["z0"] - 1
    print(json.dumps(r))
Path(sys.argv[1]).write_text(json.dumps(dict(P0=P0, runs=res), indent=1), "utf-8")
