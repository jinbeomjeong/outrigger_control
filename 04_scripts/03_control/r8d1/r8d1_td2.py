"""R8 d = 1 time-domain, second batch: final candidates C1 (late IMU read, Kp 0.3 / Ki 0.015 / tau_f 0.6, Ktw 0.8,
guard 0.25) and C2 (no late read, Kp 0.2 / Ki 0.01 / tau_f 0.8, Ktw 0.5, twist LPF 0.2 s on n^T P, guard 0.15),
both with R-1 / R-2 / increment limit 0.25 v_max per period and valve lag tau_v. Adds
  * twist-loop low-pass 'tau_tw' (guard keeps the raw per-leg load),
  * G4-type settlement case (RR sinks 11.5 mm in 2 s, 2 s after READY, 40 s hold) through c2t.run_case(settle=True),
    with the minimum true cylinder force after the sink and the leg-speed activity in the last 20 s (limit-cycle check).
Run: conda run -n dynamics-dev python -I r8d1_td2.py --group S|G|D8 --cfgs a,b  (D8: --cfg name)"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r8d1_td as T1  # noqa: E402  (valve lag patch, late scheme, C2R8L)
import numpy as np  # noqa: E402

r8, rpt, rcc, rsb, rmf = T1.r8, T1.rpt, T1.rcc, T1.rsb, T1.rmf
import run_c2_timedomain as c2t  # noqa: E402

LASTR = {}
_ORIG_RUN_CASE = c2t.run_case


def _run_case(*a, **k):
    if rpt.RCFG.get("settle"):
        k["settle"] = True
    r = _ORIG_RUN_CASE(*a, **k)
    sr = r.get("settle_result")
    if sr is not None and "_series" in r:
        S = r["_series"]
        t = np.asarray(S["t"]); F = np.asarray(S["Ftrue"]); u = np.asarray(S["u"])
        aft = t >= sr["t_sink_s"]
        fmin = F[aft].min(axis=1)
        j = int(np.argmin(fmin))
        sr["min_true_after_sink_kN"] = round(float(fmin[j]) / 1e3, 2)
        sr["t_min_after_sink_s"] = round(float(t[aft][j] - sr["t_sink_s"]), 2)
        late = t >= t[-1] - 20.0
        sr["max_leg_speed_last20s_mm_s"] = round(float(np.abs(u[late]).max()) * 1e3, 3)
        sr["min_true_last20s_kN"] = round(float(F[late].min()) / 1e3, 2)
    LASTR["r"] = r
    return r


c2t.run_case = _run_case


class C2R8F(T1.C2R8L):
    name = "C2R8F"

    def twist_rate(self, m):
        tt = float(rpt.RCFG.get("tau_tw", 0.0) or 0.0)
        if tt <= 0.0:
            return super().twist_rate(m)
        CA = rcc.CA
        c = self.c
        raw = float(c.n @ m["P"])
        if getattr(self, "_twf", None) is None:
            self._twf = raw
        else:
            self._twf += (rcc.T_CTRL / tt) * (raw - self._twf)
        tw = self._twf
        db = CA["twist_deadband_N"]
        e = 0.0 if abs(tw) < db else (tw - math.copysign(db, tw))
        rate = -CA["Ktw_1_s"] * e / c.k_nom
        lo = c.F_min + 5e3
        L = self.load_est(m)
        i = int(np.argmin(L))
        if L[i] < lo:
            sgn = math.copysign(1.0, c.n[i])
            if CA.get("guard_priority", False) and rate * sgn < 0:
                rate = 0.0
            rate += sgn * CA.get("guard_gain_1_s", CA["Ktw_1_s"]) * (lo - L[i]) / c.k_nom
            self.guard_steps = getattr(self, "guard_steps", 0) + 1
        return rate


rpt.C2RA = C2R8F

R12 = dict(T=0.1, pred=True, touch_W=0.04, touch_f=0.5)
C1CA = {"Kp_att_1_s": 0.3, "Ki_att_1_s2": 0.015, "imu_lpf_tau_s": 0.6, "ramp_s": 0.4, "delay_steps": 0,
        "Ktw_1_s": 0.8, "guard_gain_1_s": 0.25}
C2CA = {"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8, "ramp_s": 0.4, "Ktw_1_s": 0.5,
        "guard_gain_1_s": 0.15}
for tv in (0.05, 0.1, 0.15):
    r8.CONFIGS[f"C1_tv{tv:g}"] = dict(R12, ca_over=dict(C1CA), tau_v=tv, late=True)
    r8.CONFIGS[f"C2_tv{tv:g}"] = dict(R12, ca_over=dict(C2CA), tau_v=tv, tau_tw=0.2)
r8.CONFIGS["R12AR_tv1_G"] = dict(R12, ca_over={"Kp_att_1_s": 0.2, "Ki_att_1_s2": 0.01, "imu_lpf_tau_s": 0.8,
                                               "ramp_s": 0.4}, tau_v=0.1)     # rev. 26 R8 as is, d = 1
r8.CONFIGS["base50_tv1"] = dict(T=0.02, tau_v=0.1)


def run(case):
    out = T1.run(case)
    if case["rcfg"].get("settle") and "error" not in out:
        r = LASTR.get("r", {})
        sr = r.get("settle_result") or {}
        out["settle_result"] = sr
        out["guard_active_s"] = r.get("guard_active_s")
    return out


def cases_G(cfgs):
    C = []
    for cn in cfgs:
        for mast in ("rigid", "upper"):
            for s in (12345, 12346, 12347):
                for b in (1.0e9, 1.6e9):
                    c = r8.apply(rsb.mkc(f"G|flat|{mast}|{s}|{b:g}", "top", (0.0, 0.0), mast, seed=s, beta=b), cn)
                    c["rcfg"]["settle"] = True
                    C.append(c)
    return C


def summarise_G(runs):
    S = {}
    for cfg in sorted({r.get("cfg") for r in runs}):
        rr = [r for r in runs if r.get("cfg") == cfg and "error" not in r]
        S[cfg] = {"n": len([r for r in runs if r.get("cfg") == cfg]), "errors": sum("error" in r for r in runs if r.get("cfg") == cfg),
                  "min_true_kN": min(r["min_true_cyl_force_kN"] for r in rr),
                  "below_Fmin_after_sink_s_max": max(r["settle_result"].get("t_below_Fmin_true_after_sink_s", 0) for r in rr),
                  "final_min_true_kN": min(min(r["settle_result"]["final_true_kN"]) for r in rr),
                  "min_true_after_sink_kN": min(r["settle_result"]["min_true_after_sink_kN"] for r in rr),
                  "max_leg_speed_last20s_mm_s": max(r["settle_result"]["max_leg_speed_last20s_mm_s"] for r in rr),
                  "min_true_last20s_kN": min(r["settle_result"]["min_true_last20s_kN"] for r in rr),
                  "final_att_maxabs_deg": max(max(abs(v) for v in r["settle_result"]["final_att_deg"]) for r in rr),
                  "guard_active_s_max": max(r.get("guard_active_s") or 0 for r in rr),
                  "fails": sum(bool(r.get("fails")) for r in rr)}
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=("S", "G", "D8"))
    ap.add_argument("--cfgs", default="C1_tv0.1")
    ap.add_argument("--cfg", default="C1_tv0.1")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    import psutil
    psutil.Process().cpu_affinity(r8.E_CORES)
    cf = a.cfgs.split(",")
    C = r8.cases_S(cf) if a.group == "S" else (cases_G(cf) if a.group == "G" else r8.cases_D8(a.cfg))
    print("cases", len(C), flush=True)
    t0 = time.perf_counter()
    r0 = run(C[0])
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        runs = [r0] + p.map(run, C[1:], chunksize=1)
    summ = summarise_G(runs) if a.group == "G" else T1.summarise(runs)
    name = f"td2_{a.group}_{a.tag or (a.cfg if a.group == 'D8' else '_'.join(cf))}.json"
    (HERE / name).write_text(json.dumps({"wall_s": round(time.perf_counter() - t0, 1), "summary": summ, "runs": runs},
                                        indent=1, default=float), encoding="utf-8")
    print(json.dumps(summ, indent=1))
    print("wall", round(time.perf_counter() - t0, 1), "errors", sum("error" in r for r in runs), flush=True)


if __name__ == "__main__":
    main()
