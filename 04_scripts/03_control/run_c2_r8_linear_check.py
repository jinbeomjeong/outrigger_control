"""C2 R8 (10 Hz) linear robustness over the run_c2_design plant catalogue (00_docs/04_control/s6_control_spec.md
rev. 26, 99.1). Moved from the session scratchpad (s6r26_lin*.py, one file per group there).

Loop model: c2_linear.discrete_loop (ZOH plant, accelerometer tilt averaged over one control period with one-step
availability, extra input delay d steps, attitude 2-stage LPF, PI, heave P + clearance LPF, twist P), negative
feedback in the decoupled channels. Per plant and gain set: worst channel M_s with the other three loops closed,
min PM, min upper GM, closed-loop spectral radius (run_c2_design.analyse_loops).

Groups (--group):
  direct   T = 0.1 s model (tilt averaged over 100 ms; conservative for a 100 Hz multirate IMU filter)
  eq       10 Hz multirate expressed as an equivalent input delay tau_eq = T/2 + d T + tau_v in the 50 Hz model,
           steps of 20 ms (eq2 = d 0 / tau_v 0, eq7 ~ 140 ms, eq8 = 160 ms, eq10 = 200 ms, eq13 = 260 ms)
  all      both
Exports the worst plant's broken-loop matrices of selected sets for c2_r8_margin_check.jl.
Run (project root, dynamics-dev, E-cores):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_r8_linear_check.py --group all [--workers 4]
  julia --project=<control-julia> 04_scripts/03_control/c2_r8_margin_check.jl 06_analysis/02_control/r8_10hz/r8_lin_export.json
Output: 06_analysis/02_control/r8_10hz/r8_lin.json, r8_lin_export.json
"""
import argparse
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "03_control"))
sys.path.insert(0, str(_SCRIPTS / "01_dynamics"))
import c2_linear as cl  # noqa: E402
import run_c2_design as rcd  # noqa: E402

OUT_DIR = _SCRIPTS.parent / "06_analysis" / "02_control" / "r8_10hz"
_ORIG = cl.discrete_loop
G = cl.Gains
PROP = dict(Ktw=1.0, tau_z=0.2)
A8 = dict(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, tau_f=0.8)
SETS = {
    "direct": {
        "T0.02_prop_d1": (0.02, G(**PROP)),
        "T0.1_prop_d1": (0.1, G(**PROP)),
        "T0.1_prop_d0": (0.1, G(**PROP, delay_steps=0)),
        "T0.1_x0.75_d1": (0.1, G(Kp=0.3, Ki=0.015, Kz=0.375, Ktw=0.75, tau_z=0.2)),
        "T0.1_Kp0.3_d1": (0.1, G(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2)),
    },
    "eq": {
        "eq2_prop": (0.02, G(**PROP, delay_steps=2)),
        "eq4_prop": (0.02, G(**PROP, delay_steps=4)),
        "eq7_prop": (0.02, G(**PROP, delay_steps=7)),
        "eq8_prop": (0.02, G(**PROP, delay_steps=8)),
        "eq7_Kp0.3": (0.02, G(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, delay_steps=7)),
        "eq8_Kp0.3": (0.02, G(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, delay_steps=8)),
        "eq7_Kp0.2": (0.02, G(Kp=0.2, Ki=0.01, Ktw=1.0, tau_z=0.2, delay_steps=7)),
        "eq7_Kp0.15": (0.02, G(Kp=0.15, Ki=0.0075, Ktw=1.0, tau_z=0.2, delay_steps=7)),
        "eq7_tau1.0": (0.02, G(**PROP, tau_f=1.0, delay_steps=7)),
        "eq7_3st": (0.02, G(**PROP, n_stages=3, delay_steps=7)),
        "eq7_Kp0.3_3st": (0.02, G(Kp=0.3, Ki=0.015, Ktw=1.0, tau_z=0.2, n_stages=3, delay_steps=7)),
        "eq7_A8": (0.02, G(**A8, delay_steps=7)),
        "eq8_A8": (0.02, G(**A8, delay_steps=8)),
        "eq10_A8": (0.02, G(**A8, delay_steps=10)),
        "eq13_A8": (0.02, G(**A8, delay_steps=13)),
        "eq13_Kp0.15_tau1.0": (0.02, G(Kp=0.15, Ki=0.0075, Ktw=1.0, tau_z=0.2, tau_f=1.0, delay_steps=13)),
        "eq13_Kp0.15_tau1.0_Ktw0.7": (0.02, G(Kp=0.15, Ki=0.0075, Ktw=0.7, tau_z=0.2, tau_f=1.0, delay_steps=13)),
    },
}
EXPORT = ("eq7_A8", "eq8_A8", "eq10_A8", "eq13_A8")


def set_T(T):
    rcd.T = T; rcd.W_NYQ = math.pi / T
    cl.discrete_loop = lambda lp, g, **k: _ORIG(lp, g, T=T, **k)


def worker(args):
    lp, gainsets = args
    warnings.filterwarnings("ignore")
    res = {}
    for name, (T, g) in gainsets.items():
        set_T(T)
        try:
            out, _, _ = rcd.analyse_loops(lp, g, others_closed=True, mimo=True)
        except Exception as e:  # noqa: BLE001
            res[name] = {"error": repr(e)}; continue
        ch = {c: out[c]["closed_others"] for c in rcd.CH}
        res[name] = {"Ms_max": max(v["Ms"] for v in ch.values()), "Ms_ch": max(ch, key=lambda c: ch[c]["Ms"]),
                     "PM_min": min(v["PM_min_deg"] for v in ch.values() if v["PM_min_deg"] is not None),
                     "GM_up_min": min(v["GM_upper"] for v in ch.values()), "rho": out["cl_spectral_radius"],
                     "Ms_by_ch": {c: v["Ms"] for c, v in ch.items()}}
    return lp.case.tag(), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all", choices=("direct", "eq", "all"))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    import psutil
    psutil.Process().cpu_affinity(list(range(16, 28)))
    gainsets = {}
    for grp in (("direct", "eq") if a.group == "all" else (a.group,)):
        gainsets.update(SETS[grp])
    plants = [cl.build_plant(c) for c in rcd.catalogue(full=True)]
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        rows = p.map(worker, [(lp, gainsets) for lp in plants], chunksize=1)
    summ = {}
    for name in gainsets:
        good = [(t, r[name]) for t, r in rows if "error" not in r[name]]
        summ[name] = {"n": len(good), "errors": len(rows) - len(good),
                      "Ms_worst": max((v["Ms_max"], t, v["Ms_ch"]) for t, v in good),
                      "Ms_over_1.5": sum(v["Ms_max"] > 1.5 for t, v in good),
                      "rho_max": max(v["rho"] for t, v in good), "PM_min": min(v["PM_min"] for t, v in good)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "r8_lin.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, default=str),
                                         encoding="utf-8")
    for k, v in summ.items():
        print(k, v)
    exp = {}
    for name in [n for n in EXPORT if n in gainsets]:
        tag = summ[name]["Ms_worst"][1]
        lp = next(p for p in plants if p.case.tag() == tag)
        T, g = gainsets[name]; set_T(T)
        L, _ = cl.loop_matrix(cl.discrete_loop(lp, g))
        exp[name] = {"tag": tag, "T": T, "A": np.asarray(L.A).tolist(), "B": np.asarray(L.B).tolist(),
                     "C": np.asarray(L.C).tolist(), "D": np.asarray(L.D).tolist(),
                     "python_Ms": next(r for t, r in rows if t == tag)[name]["Ms_by_ch"]}
    (OUT_DIR / "r8_lin_export.json").write_text(json.dumps({"loops": exp}), encoding="utf-8")


if __name__ == "__main__":
    main()
