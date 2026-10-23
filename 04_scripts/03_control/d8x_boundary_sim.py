"""S6 spec revision 2: C2 R2 (H4) behaviour near the extended verification boundary (reduced 6-DoF plant).

Re-uses 04_scripts/03_control/s6_target_sim.py (run_tgt, C2RT) by import only. The reduced plant (layout D crawler,
tangential crawler stiffness) reproduces the Chrono stage-2 settled attitudes within 0.05 deg (d8x_settle_probe.py),
so a floor of 3.5 deg here is read on the crawler as about 3.87 deg, as in Chrono (3.82 deg).
Added: the crawler attitude averaged over the first 1 s of measured (raw IMU) samples after the settle = the CHECK
value (phi_c, theta_c) (the reduced controller has no CHECK phase and no A1 gate; every case runs).
Conventions as s6_target_sim: roll > 0 left up, pitch > 0 nose down, negative feedback, T = 20 ms ZOH, plant dt 5e-4 s,
1 step delay + 0.1 s ramp, H4 relative trigger, pressure-only verdict, beta 1.0 GPa, F_s 0, ideal IMU, seed 12345.
Run: conda run -n dynamics-dev python -I d8x_boundary_sim.py <project_root> <out_json> [workers]
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
sys.argv = [sys.argv[0], str(ROOT)] + sys.argv[2:]   # s6_target_sim reads sys.argv[1] as root at import
import s6_target_sim as sts  # noqa: E402

DEG = math.pi / 180.0


class C2RTc(sts.C2RT):
    """C2RT + CHECK-equivalent crawler attitude (mean of the first 50 measured samples)."""

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self.chk = []

    def update(self, m, t):
        if len(self.chk) < 50:
            self.chk.append((m["phi"], m["theta"]))
        return super().update(m, t)


sts.C2RT = C2RTc
_RUN = sts.run_tgt


def run(case):
    import run_mast_flex_c2_check as rmf
    out = _RUN(case)
    ctrl = rmf.LAST.get("ctrl")
    pl = rmf.LAST.get("plant")
    if ctrl is not None and getattr(ctrl, "chk", None):
        out["check_att_deg"] = (np.degrees(np.mean(np.array(ctrl.chk), axis=0))).round(4).tolist()
        out["fault"] = bool(getattr(ctrl, "fault", False))
    if pl is not None:
        out["stroke_max_final_mm"] = round(float(np.max(pl.sref)) * 1e3, 2)
    return out


def cases():
    C = []

    def add(cid, floor, level="top", **kw):
        C.append(dict(id=cid, group="d8x", floor_deg=floor, level=level,
                      tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0, **kw))

    add("top|fdown3.5", (0.0, 3.5))
    add("top|fdown3.6", (0.0, 3.6))
    add("top|fdown3.82", (0.0, 3.82))
    add("top|roll5.5", (5.5, 0.0))
    add("top|roll5.56", (5.56, 0.0))
    add("top|roll5.6", (5.6, 0.0))
    add("top|fup3.5", (0.0, -3.5))
    add("top|fup3.6", (0.0, -3.6))
    add("top|fup3.94", (0.0, -3.94))
    add("top|diag3", (3 / math.sqrt(2), 3 / math.sqrt(2)))
    add("top|fdown3.82|H4off", (0.0, 3.82))
    C[-1]["tgt"]["ra_mode"] = "off"
    add("bottom|fdown3.5", (0.0, 3.5), level="bottom")
    add("bottom|fup3.5", (0.0, -3.5), level="bottom")
    add("bottom|roll5.5", (5.5, 0.0), level="bottom")
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    import run_c2_timedomain as c2t
    cores = c2t.set_affinity()
    C = cases()
    import multiprocessing as mp
    t0 = time.time()
    res = []
    with mp.get_context("spawn").Pool(min(workers, len(C))) as pool:
        for r in pool.imap_unordered(run, C):
            res.append(r)
            print(f"{time.time() - t0:7.1f} s  {r['id']}  wall {r.get('wall_s')}  {r.get('error', '')}", flush=True)
    order = {c["id"]: i for i, c in enumerate(C)}
    res.sort(key=lambda r: order[r["id"]])
    out_json.write_text(json.dumps({"meta": {"script": __file__, "affinity": str(cores),
                                             "runtime_s": time.time() - t0, "n_runs": len(C)}, "runs": res},
                                   indent=1, default=float))
    print("written", out_json)


if __name__ == "__main__":
    main()
