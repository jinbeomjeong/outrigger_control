"""S6 spec revision 3: levelling tail from cross-axis integrator charge (items 1a, 3) - joint conditional band.

Current C2 (c2_design 14.5, reduced C1.outer): each axis integrates while 0.01 deg < |e_axis| < 0.2 deg. During a
long roll move the pitch error sits inside its band and the pitch integrator charges; after the roll converges the
pitch overshoots to about -0.035 deg and the tail waits for Ki to unwind (DONE needs 0.03 deg).
Variant 'joint': both integrators run only while max(|e_phi|, |e_theta|) < 0.2 deg (the band edge on the vector).
Variant 'joint+reset': as 'joint', and the integrators of both axes are cleared when the max error leaves 0.2 deg.
Runs (reduced 6-DoF, s6_target_sim.run_tgt by import, R2 + H4 rel, pressure unless noted): top flat / roll 3 /
diag 3 / roll 5.5 / fdown 3.5 / fup 3.5, bottom roll 5.5, middle roll 5.5; G5-like change 0 -> pitch +3 (ramp,
U3 rerun) on flat. Reports LEVEL->DONE, READY, steady error vs target, min true force, max stroke.
Run: conda run -n dynamics-dev python -I s6s2_joint_band.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
import s6_target_sim as sts  # noqa: E402

rcc = sts.rcc
DEG = math.pi / 180
MODE = {"band": "axis"}
_orig_outer = rcc.C1.outer


def outer_joint(self, m):
    if MODE["band"] == "axis":
        return _orig_outer(self, m)
    c = self.c
    e_phi, e_th = -self.phi_f, -self.th_f
    db = 0.01 * DEG
    emax = max(abs(e_phi), abs(e_th))
    if emax < 0.2 * DEG:
        if abs(e_phi) > db:
            self.Iphi = np.clip(self.Iphi + e_phi * rcc.T_CTRL, -0.02, 0.02)
        if abs(e_th) > db:
            self.Ith = np.clip(self.Ith + e_th * rcc.T_CTRL, -0.02, 0.02)
    elif MODE["band"] == "joint+reset":
        self.Iphi = 0.0; self.Ith = 0.0
    phid = rcc.CA["Kp_att_1_s"] * e_phi + rcc.CA["Ki_att_1_s2"] * self.Iphi
    thd = rcc.CA["Kp_att_1_s"] * e_th + rcc.CA["Ki_att_1_s2"] * self.Ith
    clr = c.clearance_est(m["x"])
    zd = float(np.clip(rcc.CA["Kz_1_s"] * (rcc.CA["clearance_target_m"] - clr), -c.vmax, c.vmax))
    return zd, phid, thd, clr


rcc.C1.outer = outer_joint


def run(case):
    MODE["band"] = case["band"]
    out = sts.run_tgt(case)
    out["band"] = case["band"]
    return out


def cases():
    C = []
    floors = [("top", "flat", (0.0, 0.0)), ("top", "roll3", (3.0, 0.0)), ("top", "diag3", (3 / math.sqrt(2),) * 2),
              ("top", "roll5.5", (5.5, 0.0)), ("top", "fdown3.5", (0.0, 3.5)), ("top", "fup3.5", (0.0, -3.5)),
              ("middle", "roll5.5", (5.5, 0.0)), ("bottom", "roll5.5", (5.5, 0.0))]
    for band in ("axis", "joint", "joint+reset"):
        for lvl, nm, fl in floors:
            C.append(dict(id=f"{band}|{lvl}|{nm}", band=band, floor_deg=fl, level=lvl,
                          tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
        C.append(dict(id=f"{band}|top|flat|0->p+3", band=band, floor_deg=(0.0, 0.0), level="top", t_hold=100.0,
                      tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel", "change": (2.0, (0.0, 3.0)),
                           "ramp_deg_s": (0.4, 0.25), "ramp_norm": "diamond", "rerun_reanchor": True}))
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    import run_c2_timedomain as c2t
    c2t.set_affinity()
    import multiprocessing as mp
    C = cases()
    t0 = time.time()
    res = []
    with mp.get_context("spawn").Pool(min(workers, len(C))) as pool:
        for r in pool.imap_unordered(run, C):
            res.append(r)
    order = {c["id"]: i for i, c in enumerate(C)}
    res.sort(key=lambda r: order[r["id"]])
    for r in res:
        if "error" in r:
            print(r["id"], r["error"]); continue
        lvl_done = None if r.get("t_done_s") is None else round(r["t_done_s"] - r["t_touch_s"], 2)
        print(f"{r['id']:28s} level->done {lvl_done}  ready {r.get('t_ready_s')}  chg->ready {r.get('t_change_to_ready_s')} "
              f"ss {r.get('ss_err_vs_target_deg')}  Fmin {r.get('min_true_cyl_force_kN')}  smax {max(r['s_max_seen_mm']):.1f} "
              f"ra {r['ra'].get('outcome')} fails {r.get('fails')}")
    out_json.write_text(json.dumps({"runs": res, "runtime_s": time.time() - t0}, indent=1, default=float))


if __name__ == "__main__":
    main()
