"""Linear catalogue robustness at T = 0.1 s (spec rev. 26): the run_c2_design loop model (cl.discrete_loop: ZOH
plant, accelerometer tilt averaged over one control period with one-step availability, extra input delay d steps,
attitude 2-stage LPF, PI, heave P + clearance LPF, twist P) evaluated with T = 0.1 s instead of 0.02 s.
The 100 ms tilt average is conservative for an IMU filtered at 100 Hz (multirate) - its group delay is 50 ms.
Per plant and gain set: worst channel M_s (loop-at-a-time, others closed), min PM, min upper GM, closed-loop spectral
radius. Exports the worst plant's loops for the Julia cross-check (s6r26_lin_check.jl).
Run (project root, dynamics-dev, E-cores): conda run -n dynamics-dev python -I <this file>"""
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
sys.path.insert(0, str(REPO / r"04_scripts\03_control"))
sys.path.insert(0, str(REPO / r"04_scripts\01_dynamics"))
import c2_linear as cl  # noqa: E402
import run_c2_design as rcd  # noqa: E402

HERE = Path(__file__).resolve().parent
_orig = cl.discrete_loop
GAINSETS = {
    "eq10_Kp0.2_tau0.8": (0.02, cl.Gains(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, tau_f=0.8, delay_steps=10)),
    "eq13_Kp0.2_tau0.8": (0.02, cl.Gains(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, tau_f=0.8, delay_steps=13)),
    "eq13_Kp0.15_tau1.0": (0.02, cl.Gains(Kp=0.15, Ki=0.0075, Ktw=1.0, tau_z=0.2, tau_f=1.0, delay_steps=13)),
    "eq13_Kp0.15_tau1.0_Ktw0.7": (0.02, cl.Gains(Kp=0.15, Ki=0.0075, Ktw=0.7, tau_z=0.2, tau_f=1.0, delay_steps=13)),
}
_UNUSED3 = {
    "eq4_prop": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=4)),
    "eq7_Kp0.2": (0.02, cl.Gains(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, delay_steps=7)),
    "eq7_Kp0.15": (0.02, cl.Gains(Kp=0.15, Ki=0.0075, Ktw=1.0, tau_z=0.2, delay_steps=7)),
    "eq7_tau1.0": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, tau_f=1.0, delay_steps=7)),
    "eq7_3st": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, n_stages=3, delay_steps=7)),
    "eq7_Kp0.2_tau0.8": (0.02, cl.Gains(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, tau_f=0.8, delay_steps=7)),
    "eq7_Kp0.3_3st": (0.02, cl.Gains(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, n_stages=3, delay_steps=7)),
    "eq8_Kp0.2_tau0.8": (0.02, cl.Gains(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, tau_f=0.8, delay_steps=8)),
}
_UNUSED2 = {
    "MR_d0_eq2": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=2)),
    "MR_d1_eq7": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=7)),
    "MR_d1_eq8": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=8)),
    "MR_d1_eq7_Kp0.3": (0.02, cl.Gains(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, delay_steps=7)),
    "MR_d1_eq8_Kp0.3": (0.02, cl.Gains(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, delay_steps=8)),
}
_UNUSED = {
    "T0.02_prop_d1": (0.02, cl.Gains(Ktw=1.0, tau_z=0.2)),
    "T0.1_prop_d1": (0.1, cl.Gains(Ktw=1.0, tau_z=0.2)),
    "T0.1_prop_d0": (0.1, cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=0)),
    "T0.1_x0.75_d1": (0.1, cl.Gains(Kp=0.3, Ki=0.015, Kz=0.375, Ktw=0.75, tau_z=0.2)),
    "T0.1_Kp0.3_d1": (0.1, cl.Gains(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2)),
}


def set_T(T):
    rcd.T = T; rcd.W_NYQ = math.pi / T
    cl.discrete_loop = lambda lp, g, **k: _orig(lp, g, T=T, **k)


def worker(lp):
    warnings.filterwarnings("ignore")
    res = {}
    for name, (T, g) in GAINSETS.items():
        set_T(T)
        try:
            out, dl, L = rcd.analyse_loops(lp, g, others_closed=True, mimo=True)
        except Exception as e:  # noqa: BLE001
            res[name] = {"error": repr(e)}; continue
        ch = {c: out[c]["closed_others"] for c in rcd.CH}
        res[name] = {"Ms_max": max(v["Ms"] for v in ch.values()),
                     "Ms_ch": max(ch, key=lambda c: ch[c]["Ms"]),
                     "PM_min": min(v["PM_min_deg"] for v in ch.values() if v["PM_min_deg"] is not None),
                     "GM_up_min": min(v["GM_upper"] for v in ch.values()),
                     "rho": out["cl_spectral_radius"], "Ms_by_ch": {c: v["Ms"] for c, v in ch.items()}}
    return lp.case.tag(), res


def main():
    import psutil
    psutil.Process().cpu_affinity(list(range(16, 28)))
    plants = [cl.build_plant(c) for c in rcd.catalogue(full=True)]
    from multiprocessing import Pool
    with Pool(4) as p:
        rows = p.map(worker, plants, chunksize=1)
    summ = {}
    for name in GAINSETS:
        vals = [(r[name]["Ms_max"], tag, r[name]["Ms_ch"]) for tag, r in rows if "error" not in r[name]]
        rho = max(r[name]["rho"] for tag, r in rows if "error" not in r[name])
        pm = min(r[name]["PM_min"] for tag, r in rows if "error" not in r[name])
        errs = sum("error" in r[name] for tag, r in rows)
        summ[name] = {"n": len(vals), "errors": errs, "Ms_worst": max(vals), "Ms_over_1.5": sum(v[0] > 1.5 for v in vals),
                      "rho_max": rho, "PM_min": pm}
    (OUT_DIR / "s6r26_lin_sweep2.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, default=str),
                                         encoding="utf-8")
    for k, v in summ.items():
        print(k, v)
    # export the worst plant of T0.1_prop_d1 for Julia: open loops per channel (others closed)
    tag = summ["eq13_Kp0.2_tau0.8"]["Ms_worst"][1]
    lp = next(p for p in plants if p.case.tag() == tag)
    exp = {}
    for name in ("eq10_Kp0.2_tau0.8", "eq13_Kp0.2_tau0.8"):
        T, g = GAINSETS[name]; set_T(T)
        import control as ct
        dl = cl.discrete_loop(lp, g)
        L, Kd = cl.loop_matrix(dl)
        exp[name] = {"T": T, "A": np.asarray(L.A).tolist(), "B": np.asarray(L.B).tolist(), "C": np.asarray(L.C).tolist(),
                     "D": np.asarray(L.D).tolist(), "python_Ms": {c: next(r for t, r in rows if t == tag)[name]["Ms_by_ch"][c]
                                                                  for c in rcd.CH}}
    (OUT_DIR / "s6r26_lin_sweep2_export.json").write_text(json.dumps({"tag": tag, "loops": exp}), encoding="utf-8")


if __name__ == "__main__":
    main()
