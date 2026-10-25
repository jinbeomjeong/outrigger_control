"""Sensor-rate study (spec rev. 25): pressure + stroke at 10 Hz (instantaneous ZOH or 100 ms mean then ZOH), IMU
unchanged (per control period mean), and the whole controller at 10 Hz. Reduced L1 plant + pad bushings + crawler,
C2 R1 'R:BS_hold' (dynamics harness, read-only imports). E-cores (16-27) pinned, workers inherit.
Variants: base (50 Hz all), p10i (P/x/s instantaneous sample every 100 ms, held), p10a (100 ms mean of the 50 Hz
samples, updated every 100 ms, held), c10 (controller period 0.1 s, all sensors 10 Hz).
Run (project root, dynamics-dev): conda run -n dynamics-dev python -I <this file>"""
import json
import os
import sys
import time
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
sys.path.insert(0, str(REPO / r"04_scripts\03_control"))
sys.path.insert(0, str(REPO / r"04_scripts\01_dynamics"))
import numpy as np  # noqa: E402
import run_h4_fs_order_check as hk  # noqa: E402  (imports rpf, rpt, rmf)
import run_s6_slope_boundary_check as rsb  # noqa: E402
import run_c2_revision as rcr  # noqa: E402
import run_control_comparison as rcc  # noqa: E402

OUT = OUT_DIR / "s6r25_rate.json"
E_CORES = list(range(16, 28))
HELD = ("P", "x", "s")
VARIANTS = ("base", "p10i", "p10a", "c10")


class RateSensors(rcr.SensorsS):
    """SensorsS with the pressure / stroke channels decimated to 10 Hz (mode from rpt.RCFG['rate'])."""

    def __init__(self, imu, rng, g):
        super().__init__(imu, rng, g)
        self.k = 0; self.buf = []; self.held = None
        self.mode = hk.rpt.RCFG.get("rate", "base")

    def read(self, plant, acc, nsub):
        m = super().read(plant, acc, nsub)
        if self.mode not in ("p10i", "p10a"):
            return m
        n = 5                                   # 100 ms / 20 ms
        self.buf.append({k: np.array(m[k], float) for k in HELD})
        self.buf = self.buf[-n:]
        if self.held is None or self.k % n == 0:
            if self.mode == "p10i":
                self.held = {k: np.array(m[k], float) for k in HELD}
            else:
                self.held = {k: np.mean([b[k] for b in self.buf], axis=0) for k in HELD}
        self.k += 1
        for k in HELD:
            m[k] = self.held[k].copy()
        return m


rcr.SensorsS = RateSensors      # run_one assigns rcc.Sensors = rcr.SensorsS (module attribute) in every worker


def apply_rate(case, v):
    case = dict(case); case["rcfg"] = dict(case.get("rcfg", {})); case["rcfg"]["rate"] = v
    return case


def run(case):
    v = case["rcfg"].get("rate", "base")
    t_old = rcc.T_CTRL
    try:
        if v == "c10":
            rcc.T_CTRL = 0.1
        if "reanchor" in case["rcfg"]:
            out = hk.one(case)
        else:
            out = rsb.td_one(case)
    finally:
        rcc.T_CTRL = t_old
    out["rate"] = v
    return out


def cases():
    d = rsb.load()
    pts = rsb.td_points(d)
    C = []
    for tag in ("pitch+", "pitch-", "roll+", "r+p+0.5"):
        ang = pts[("top", tag)]
        for mast in ("rigid", "upper"):
            for s in (12345, 12346, 12347):
                for b in (1.0e9, 1.6e9):
                    for v in VARIANTS:
                        C.append(apply_rate(rsb.mkc(f"T|{v}|{tag}|{mast}|{s}|{b:g}", "top", ang, mast, seed=s, beta=b), v))
    for tag in ("V:pitch+3.5", "P:pitch+3.2"):
        for s in (12345, 12346, 12347):
            for v in VARIANTS:
                c = hk.mk(f"H|{v}|{tag}|rigid|yaml|{s}", tag, "rigid", "yaml", 0.0, hk.spec(hk.stair(45e3, hk.R6_FLOOR_N)),
                          seed=s)
                C.append(apply_rate(c, v))
    return C


def main():
    import psutil
    psutil.Process().cpu_affinity(E_CORES)
    C = cases()
    print("cases", len(C), flush=True)
    t0 = time.perf_counter()
    r0 = run(C[0])
    from multiprocessing import Pool
    with Pool(12) as p:
        runs = [r0] + p.map(run, C[1:], chunksize=1)
    OUT.write_text(json.dumps({"wall_s": round(time.perf_counter() - t0, 1), "runs": runs}, indent=1, default=float),
                   encoding="utf-8")
    print("wall", round(time.perf_counter() - t0, 1), "errors", sum("error" in r for r in runs), flush=True)


if __name__ == "__main__":
    main()
