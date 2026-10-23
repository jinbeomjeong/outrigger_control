"""C2 at 10 Hz (R8 candidate, spec rev. 26): controller period 0.1 s (valve output, pressure, stroke all 10 Hz,
instantaneous samples), IMU per-period mean as before. Prototype changes in a harness subclass of
run_pad_tangential_check.C2RA (read-only imports of the project scripts):
  R-1  REANCHOR stop on the predicted reading P_hat = P - r_hat T (1 + d), r_hat = 3-sample mean unloading rate of
       the target reading (d = extra delay steps), optional stair speed fraction.
  R-2  TOUCH window: before the touch load has been seen, a leg whose motor stroke is within W of the flat-floor
       touch extension (dyn_model geometry, crawler parallel) extends at f_w v_max.
Gains / CA overrides per configuration ('ca_over'): attitude Kp_att_1_s / Ki_att_1_s2, imu_lpf_tau_s, ramp_s (the
output increment limit: ramp_s 0.4 = 0.25 v_max per 0.1 s period, 1.0 = 0.1 v_max). imu_lpf_tau_s is restored to
the run_control_comparison default after every run (it is a CA key outside the gain sets).
Spec: 00_docs/04_control/s6_control_spec.md rev. 26 (99-101). Moved from the session scratchpad (s6r26_c10.py).
Groups: 'S' = 216-case set of rev. 25 (D8 top 4 points x rigid/upper x 3 seeds x beta 1.0/1.6, H4 nose-down 6),
        'D8' = td_main 144 + td_robust 432 (run_s6_slope_boundary_check) for one configuration.
Run (project root, dynamics-dev, E-cores): conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_r8_10hz_check.py --group S|D8 [--cfg name]"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "03_control"))
sys.path.insert(0, str(_SCRIPTS / "01_dynamics"))
sys.path.insert(0, str(_SCRIPTS / "00_cad"))
import numpy as np  # noqa: E402
import run_h4_fs_order_check as hk  # noqa: E402
import run_s6_slope_boundary_check as rsb  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_c2_timedomain as c2t  # noqa: E402
import dyn_model as dm  # noqa: E402

rpt = hk.rpt
HERE = _SCRIPTS.parent / "06_analysis" / "02_control" / "r8_10hz"
E_CORES = list(range(16, 28))
_GEO = dm.geometry_from_params(dm.load_params())
TOUCH_EXT = np.asarray(_GEO.touch_extension, float)

CONFIGS = {
    "base50": dict(T=0.02),
    "c10": dict(T=0.1),
    "c10_R1": dict(T=0.1, pred=True),
    "c10_R1v05": dict(T=0.1, pred=True, ra_speed=0.05),
    "c10_R2": dict(T=0.1, touch_W=0.04, touch_f=0.5),
    "c10_R12": dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5),
    "c10_R12A": dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5,
                     ca_over={"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8}),
    "c10_R12AR": dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5,
                      ca_over={"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8, "ramp_s": 0.4}),
    "c10_R12AR10": dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5,
                        ca_over={"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8, "ramp_s": 1.0}),
}

_BaseC2RA = rpt.C2RA


class C2R8(_BaseC2RA):
    name = "C2R8"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self._ra_hist = []; self._ra_key = None

    # R-2 ------------------------------------------------------------------------------------------------
    def _touch(self, m, t):
        W = rpt.RCFG.get("touch_W")
        if not W:
            return super()._touch(m, t)
        CA = rcc.CA
        c = self.c
        load = m["P"]
        cond = load >= CA["P_touch_N"]
        hold = CA["touch_hold_s"]
        cand = np.zeros(4, bool)
        for i in range(4):
            if self.touched[i]:
                continue
            if cond[i]:
                if self.cand_t[i] is None:
                    self.cand_t[i] = t
                if t - self.cand_t[i] >= hold - 1e-9:
                    self.touched[i] = True
                else:
                    cand[i] = True
            else:
                self.cand_t[i] = None
        self.seen |= cond
        in_win = np.asarray(m["s"]) >= TOUCH_EXT - W
        v_free = np.where(self.seen, CA["touch_approach_frac"] * c.vmax,
                          np.where(in_win, rpt.RCFG.get("touch_f", 0.5) * c.vmax, c.vmax))
        u = np.where(self.touched | cand, 0.0, v_free)
        if self.touched.all():
            self.phase = "level"; self.t_touch = t
            self.on_touch(m)
        return u

    # R-1 ------------------------------------------------------------------------------------------------
    def _ra(self, m, t, spec):
        ra = self.ra
        if rpt.RCFG.get("pred") and ra is not None and ra.get("st") == "move" and ra["k"] < len(spec["steps"]):
            tgt = hk.LEGS.index(spec["steps"][ra["k"]])
            key = (ra["k"], tgt)
            if key != self._ra_key:
                self._ra_key = key; self._ra_hist = []
            P = np.array(m["P"], float)
            self._ra_hist.append(P[tgt]); self._ra_hist = self._ra_hist[-4:]
            if len(self._ra_hist) >= 2:
                h = self._ra_hist
                rate = (h[0] - h[-1]) / (len(h) - 1)          # per control step, > 0 when unloading
                d = int(rcc.CA.get("delay_steps", 1))
                P[tgt] = P[tgt] - max(rate, 0.0) * (1 + d)
                m = dict(m); m["P"] = P
        return super()._ra(m, t, spec)


rpt.C2RA = C2R8


def apply(case, cfg_name):
    cfg = CONFIGS[cfg_name]
    case = dict(case); case["rcfg"] = dict(case.get("rcfg", {}))
    case["rcfg"].update({k: v for k, v in cfg.items() if k != "T"}); case["rcfg"]["cfg"] = cfg_name
    if "ra_speed" in cfg and "reanchor" in case["rcfg"]:
        sp = dict(case["rcfg"]["reanchor"]); sp["speed_frac"] = cfg["ra_speed"]; case["rcfg"]["reanchor"] = sp
    case["id"] = case["id"].replace("|", f"|{cfg_name}|", 1)
    return case


def run(case):
    cfg = CONFIGS[case["rcfg"]["cfg"]]
    t_old = rcc.T_CTRL
    over = case["rcfg"].get("ca_over")
    saved = None
    lpf_default = rcc.CA.get("imu_lpf_tau_s")
    try:
        rcc.T_CTRL = cfg["T"]
        if over:
            gname = case["gainset"]; saved = dict(c2t.GAINSETS[gname])
            c2t.GAINSETS[gname] = dict(saved, **over)
        out = hk.one(case) if "reanchor" in case["rcfg"] else rsb.td_one(case)
    finally:
        rcc.T_CTRL = t_old
        rcc.CA["imu_lpf_tau_s"] = lpf_default
        if saved is not None:
            c2t.GAINSETS[case["gainset"]] = saved
    out["cfg"] = case["rcfg"]["cfg"]
    return out


def cases_S(cfgs):
    d = rsb.load(); pts = rsb.td_points(d); C = []
    for cn in cfgs:
        for tag in ("pitch+", "pitch-", "roll+", "r+p+0.5"):
            for mast in ("rigid", "upper"):
                for s in (12345, 12346, 12347):
                    for b in (1.0e9, 1.6e9):
                        C.append(apply(rsb.mkc(f"T|{tag}|{mast}|{s}|{b:g}", "top", pts[("top", tag)], mast, seed=s, beta=b), cn))
        for tag in ("V:pitch+3.5", "P:pitch+3.2"):
            for s in (12345, 12346, 12347):
                C.append(apply(hk.mk(f"H|{tag}|rigid|yaml|{s}", tag, "rigid", "yaml", 0.0,
                                     hk.spec(hk.stair(45e3, hk.R6_FLOOR_N)), seed=s), cn))
    return C


def cases_D8(cn):
    d = rsb.load()
    return [apply(c, cn) for st in ("td_main", "td_robust") for c in rsb.td_cases(st, d)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=("S", "D8"))
    ap.add_argument("--cfg", default="c10_R12")
    ap.add_argument("--cfgs", default="c10,c10_R1,c10_R1v05,c10_R2,c10_R12,c10_R12g")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    import psutil
    psutil.Process().cpu_affinity(E_CORES)
    C = cases_S(a.cfgs.split(",")) if a.group == "S" else cases_D8(a.cfg)
    print("cases", len(C), flush=True)
    t0 = time.perf_counter()
    r0 = run(C[0])
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        runs = [r0] + p.map(run, C[1:], chunksize=1)
    HERE.mkdir(parents=True, exist_ok=True)
    out = HERE / (f"r8_S_{'_'.join(a.cfgs.split(','))}.json" if a.group == "S" else f"r8_D8_{a.cfg}.json")
    out.write_text(json.dumps({"wall_s": round(time.perf_counter() - t0, 1), "runs": runs}, indent=1, default=float),
                   encoding="utf-8")
    print("wall", round(time.perf_counter() - t0, 1), "errors", sum("error" in r for r in runs), flush=True)


if __name__ == "__main__":
    main()
