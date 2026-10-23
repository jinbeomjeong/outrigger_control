"""R8 d = 1 time-domain check on the reduced plant (spec rev. 30). Extends the project harness
04_scripts/03_control/run_c2_r8_10hz_check.py (read-only import) with
  * valve first-order lag tau_v on the applied leg speed (after the increment / ramp limit), exact exponential
    update per physics chunk (1 ms chunks while ramp_s > 0), rcfg key 'tau_v';
  * 'late' timing: pressure / stroke / saturation fields one control period old, IMU per-period mean of the
    period just ended, output applied at once (CA delay_steps 0). Same pressure-path latency as d = 1, attitude
    latency ~ 0 + period mean (approximation of the 'late IMU read' of the multirate design, see r8d1_lin);
    R-1 prediction horizon kept at 2 periods.
The d = 1 configurations use the harness queue (CA delay_steps 1 of gain set R1): read at t_k, applied from t_{k+1}.
IMU = per-period mean and the controller's 2-stage filter at the control period (as rev. 26, conservative w.r.t.
the 100 Hz multirate filter for the attitude lag; see r8d1_lin 'harn' group for the linear equivalence).
Run: conda run -n dynamics-dev python -I r8d1_td.py --group S --cfgs a,b,...  |  --group D8 --cfg name
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\03_control")
import run_c2_r8_10hz_check as r8  # noqa: E402
import numpy as np  # noqa: E402

rpt, rcc, hk, rsb = r8.rpt, r8.rcc, r8.hk, r8.rsb
import run_mast_flex_c2_check as rmf  # noqa: E402

# ------------------------------------------------------------------ valve lag on the plant input
_ORIG_STEP = rmf.FlexPlant.step


def _step_lag(self, u, nsteps):
    tv = float(rpt.RCFG.get("tau_v", 0.0) or 0.0)
    u = np.asarray(u, float)
    if tv <= 0.0:
        return _ORIG_STEP(self, u, nsteps)
    uf = getattr(self, "_uf", None)
    if uf is None:
        uf = np.zeros(4)
    if nsteps > 20:                      # crawler settle before the run: zero command, zero valve state required
        if np.any(u != 0.0) or np.any(uf != 0.0):
            raise RuntimeError("long step with a non-zero valve state")
        self._uf = uf
        return _ORIG_STEP(self, u, nsteps)
    h = nsteps * self.dt
    e = math.exp(-h / tv)
    u_avg = u + (uf - u) * (tv / h) * (1.0 - e)        # exact mean of the lagged speed over the chunk
    self._uf = u + (uf - u) * e
    self.lag_n = getattr(self, "lag_n", 0) + 1
    return _ORIG_STEP(self, u_avg, nsteps)


rmf.FlexPlant.step = _step_lag

# ------------------------------------------------------------------ late scheme controller
PKEYS = ("P", "x", "s", "sat_ext")


class C2R8L(r8.C2R8):
    name = "C2R8L"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self._prevP = None

    def update(self, m, t):
        if rpt.RCFG.get("late"):
            cur = {k: (np.array(m[k], copy=True) if k in m else None) for k in PKEYS}
            prev = self._prevP if self._prevP is not None else cur
            self._prevP = cur
            m = dict(m)
            for k, v in prev.items():
                if v is not None:
                    m[k] = v
        return super().update(m, t)

    def _ra(self, m, t, spec):
        if rpt.RCFG.get("late"):
            old = rcc.CA.get("delay_steps")
            rcc.CA["delay_steps"] = 1               # prediction horizon 1 + 1 periods (reading age + output)
            try:
                return super()._ra(m, t, spec)
            finally:
                rcc.CA["delay_steps"] = old
        return super()._ra(m, t, spec)


rpt.C2RA = C2R8L

A8 = {"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8, "ramp_s": 0.4}
R12 = dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5)
r8.CONFIGS.update({
    "c10_R12AR_tv0": dict(R12, ca_over=dict(A8), tau_v=0.0),          # regression anchor (= c10_R12AR)
    "c10_R12AR_tv1": dict(R12, ca_over=dict(A8), tau_v=0.1),
    "c10_A8k08_tv1": dict(R12, ca_over=dict(A8, Ktw_1_s=0.8), tau_v=0.1),
    "c10_M5L_tv1": dict(R12, ca_over={"Kp_att_1_s": 0.3, "Ki_att_1_s2": 0.015, "imu_lpf_tau_s": 0.5, "ramp_s": 0.4,
                                       "delay_steps": 0}, tau_v=0.1, late=True),
    "c10_M6L_tv1": dict(R12, ca_over={"Kp_att_1_s": 0.3, "Ki_att_1_s2": 0.015, "imu_lpf_tau_s": 0.6, "ramp_s": 0.4,
                                       "delay_steps": 0}, tau_v=0.1, late=True),
    "c10_G7L_tv1": dict(R12, ca_over={"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "imu_lpf_tau_s": 0.5, "ramp_s": 0.4,
                                       "delay_steps": 0}, tau_v=0.1, late=True),
    "base50_tv1": dict(T=0.02, tau_v=0.1),
    "c20_G7_tv1": dict(T=0.05, pred=True, touch_W=0.04, touch_f=0.5,
                       ca_over={"ramp_s": 0.2}, tau_v=0.1),                # 20 Hz, R7 gains, d = 1 (info)
    "c10_A8k08_tv1_late": dict(R12, ca_over=dict(A8, Ktw_1_s=0.8, delay_steps=0), tau_v=0.1, late=True),
})


def run(case):
    out = r8.run(case)
    pl = rmf.LAST.get("plant")
    want = float(case["rcfg"].get("tau_v", 0.0) or 0.0)
    if "error" not in out:
        if want > 0 and getattr(pl, "lag_n", 0) == 0:
            raise RuntimeError("valve lag not applied")
        out["lag_chunks"] = int(getattr(pl, "lag_n", 0))
        out["late"] = bool(case["rcfg"].get("late", False))
    return out


def summarise(runs):
    S = {}
    for cfg in sorted({r.get("cfg") for r in runs}):
        rr = [r for r in runs if r.get("cfg") == cfg]
        T = [r for r in rr if str(r.get("id", "")).startswith("T|") or str(r.get("id", "")).startswith("main|")
             or str(r.get("id", "")).split("|")[0] in ("seed", "d0", "beta")]
        H = [r for r in rr if str(r.get("id", "")).startswith("H|")]
        err = [r for r in rr if "error" in r]
        okT = [r for r in T if "error" not in r]
        s = {"n": len(rr), "errors": len(err)}
        if okT:
            s.update({"D8_min_true_kN": min(r["min_true_cyl_force_kN"] for r in okT),
                      "D8_min_case": min(okT, key=lambda r: r["min_true_cyl_force_kN"])["id"],
                      "D8_below_guard": sum(r["min_true_cyl_force_kN"] < 14.41 for r in okT),
                      "D8_fails": sum(bool(r.get("fails")) for r in okT),
                      "ready_max_s": max((r["t_ready_s"] or 1e9) for r in okT),
                      "ready_mean_s": round(float(np.mean([r["t_ready_s"] for r in okT if r["t_ready_s"]])), 2),
                      "touch_max_s": max((r["t_touch_s"] or 1e9) for r in okT),
                      "ss_att_max_deg": max(r["ss_true_att_deg_maxabs"] for r in okT),
                      "pmax_bar": max(r["max_pressure_bar"] for r in okT)})
        okH = [r for r in H if "error" not in r]
        if okH:
            mins = [r["x"].get("min_true_ra_kN") for r in okH if r.get("x")]
            stops = [min(st["P_stop_reading_kN"] for st in r["x"]["steps"]) for r in okH if r.get("x", {}).get("steps")]
            s.update({"H4_min_true_ra_kN": min(v for v in mins if v is not None) if mins else None,
                      "H4_below_guard": sum(v is not None and v < 14.41 for v in mins),
                      "H4_stop_reading_min_kN": min(stops) if stops else None,
                      "H4_ready_max_s": max(r["t_ready_s"] or 1e9 for r in okH),
                      "H4_fails": sum(bool(r.get("fails")) for r in okH)})
        S[cfg] = s
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=("S", "D8"))
    ap.add_argument("--cfg", default="c10_A8k08_tv1")
    ap.add_argument("--cfgs", default="c10_R12AR_tv0")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import psutil
    psutil.Process().cpu_affinity(r8.E_CORES)
    C = r8.cases_S(a.cfgs.split(",")) if a.group == "S" else r8.cases_D8(a.cfg)
    print("cases", len(C), flush=True)
    t0 = time.perf_counter()
    r0 = run(C[0])
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        runs = [r0] + p.map(run, C[1:], chunksize=1)
    out = HERE / (f"td_S_{a.tag or '_'.join(a.cfgs.split(','))}.json" if a.group == "S" else f"td_D8_{a.cfg}.json")
    summ = summarise(runs)
    out.write_text(json.dumps({"wall_s": round(time.perf_counter() - t0, 1), "summary": summ, "runs": runs},
                              indent=1, default=float), encoding="utf-8")
    print(json.dumps(summ, indent=1))
    print("wall", round(time.perf_counter() - t0, 1), "errors", sum("error" in r for r in runs), flush=True)


if __name__ == "__main__":
    main()
