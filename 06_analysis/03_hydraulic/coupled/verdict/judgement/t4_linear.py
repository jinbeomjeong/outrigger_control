"""T-4: C2 exact multirate loop (r8d1_lin, 80 plants) with the flow-saturation input structures.

Structures (criteria 5.4):
  single leg s : M row s = -A_j / A_s (j != s), M_ss = 0, other rows identity (areas only).
  set P        : dv_i = g_i du_i + h_i (dp_P - dp_i), g_i = r_i kappa_i, h_i = v_i / (2 D_i) for i in P,
                 dv_j = du_j otherwise, sum_P A_i dv_i + sum_notP A_j du_j = 0, dp_i = dF_i / A_i.
The structure sits between the valve output and the plant speed input, so the plant becomes
  v = W (Mu u + Mf C_P x),  W = (I - Mf D_P)^-1.
Loop broken at the decoupled command, negative feedback (r8d1_lin). T = 0.1 s, d = 1, tau_v = 0.1 s,
C2 gains. Channel M_s = max |1 / (1 + H_j)|, H_j = [(I + L F_j)^-1 L]_jj with the other loops closed.
rho = largest |z| of the closed loop after removing the one eigenvalue at z = 1 of the fixed-flow
direction (criteria T-4). Writes t4_results.json and t4_export.json (Julia cross check).
Run: conda run -n dynamics-dev python -I -B t4_linear.py [workers]
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

HERE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement")
V = HERE.parent
sys.path.insert(0, r"C:\workspace\outrigger_control\04_scripts\03_control\r8d1")
import r8d1_lin as R  # noqa: E402
import c2_linear as cl  # noqa: E402
import dyn_model as dm  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
A_H = np.pi / 4 * np.array([0.13, 0.13, 0.11, 0.11]) ** 2
CFG = R.Cfg(d=1, tau_v=0.1, Ktw=0.5, tau_tw=0.2, Kp=0.2, Ki=0.01, tau_f=0.8)
JUDGED = ("phi", "theta", "tw")
CC = cl.nominal_controller_constants()


def single_leg_structure(s: int):
    Mu = np.eye(4)
    Mu[s] = -A_H / A_H[s]
    Mu[s, s] = 0.0
    return Mu, np.zeros((4, 4))


def set_structure(names, op, constants):
    """Mu, Mf of the set P at one operating point (criteria 5.4 general form)."""
    idx = [LEGS.index(n) for n in names]
    X2 = constants["X_comp"] ** 2
    dpc = constants["dp_comp_Pa"]
    u = np.array([op["u_m_s"][n] for n in LEGS])
    v = np.array([op["v_m_s"][n] for n in LEGS])
    pl = np.array([op["p_load_Pa"][n] for n in LEGS])
    Ah = np.asarray(constants["A_h_m2"])
    K2 = (Ah * np.abs(u)) ** 2 / dpc
    kappa = X2 / (X2 + K2)
    D = op["p_P_Pa"] - pl
    r = np.divide(v, u, out=np.ones(4), where=u != 0)
    g = r * kappa
    h = np.divide(v, 2.0 * D, out=np.zeros(4), where=D > 0)
    W = float(sum(Ah[i] * h[i] for i in idx))
    Mu = np.eye(4)
    Mf = np.zeros((4, 4))
    for i in idx:
        Mu[i] = 0.0
        Mu[i, i] = g[i]
        for k in range(4):
            coef = Ah[k] * g[k] if k in idx else Ah[k]
            Mu[i, k] -= h[i] / W * coef
        Mf[i, i] = -h[i] / Ah[i]
        for k in idx:
            Mf[i, k] += h[i] * h[k] / W
    return Mu, Mf


def apply_structure(lp, Mu, Mf):
    """Plant with the leg-speed input through the structure (P rows in N, cylinder force)."""
    iP = [lp.idx(f"P_{nm}") for nm in dm.LEG_NAMES]
    CP, DP = lp.C[iP], lp.D[iP]
    W = np.linalg.inv(np.eye(4) - Mf @ DP)
    new = copy.copy(lp)
    new.A = lp.A + lp.B @ W @ Mf @ CP
    new.B = lp.B @ W @ Mu
    new.C = lp.C + lp.D @ W @ Mf @ CP
    new.D = lp.D @ W @ Mu
    return new


def eval_loop(lp, cfg=CFG, n_grid=2500):
    """Channel M_s by the frequency response of L, closed-loop eigenvalues."""
    import control as ct
    R.set_T(cfg.T)
    L = R.loop(lp, cfg)
    w = np.logspace(-3, math.log10(math.pi / cfg.T * 0.9999), n_grid)
    H = R.rcd.freq_resp(L, w)
    res = {}
    for j, ch in enumerate(R.CH):
        F = np.eye(4)
        F[j, j] = 0.0
        Cl = np.linalg.solve(np.eye(4)[None] + H @ F, H)
        Sj = 1.0 / (1.0 + Cl[:, j, j])
        k = int(np.argmax(np.abs(Sj)))
        res[ch] = {"Ms": float(np.abs(Sj[k])), "w": float(w[k])}
    p = np.asarray(ct.feedback(L, np.eye(4)).poles())
    z1 = np.abs(p - 1.0)
    i1 = int(np.argmin(z1))
    rest = np.delete(p, i1)
    res["rho_all"] = float(np.max(np.abs(p)))
    res["dist_nearest_to_1"] = float(z1[i1])
    res["n_within_1e-6_of_1"] = int(np.sum(z1 < 1e-6))
    res["rho_excl"] = float(np.max(np.abs(rest)))
    return res


def job(args):
    item_i, struct_key, Mu, Mf = args
    item = R.catalogue_ext()[item_i]
    lp = R.make_plant(item)
    tag = R.tag(lp)
    if Mu is not None:
        lp = apply_structure(lp, np.array(Mu), np.array(Mf))
    r = eval_loop(lp)
    r.update(plant=tag, struct=struct_key)
    return r


def collect_sets():
    d = json.loads((V / "verdict_pairs.json").read_text(encoding="utf-8"))
    uniq = {}
    for p in d["pairs"]:
        j = json.loads((V / f"{p['run_id']}.json").read_text(encoding="utf-8"))
        t4 = j["values"]["T4_inputs"]
        const = t4["valve_constants"]
        for name, s in t4["sets"].items():
            op = s["operating_point"]
            mu, mf = set_structure(name.split("+"), op, const)
            # phase at the operating point from the E1-style phase path is only a label
            key = (name, const["law"], tuple(np.round(mu.ravel(), 2)), tuple(np.round(mf.ravel() * 1e9, 1)))
            rec = uniq.setdefault(key, {"set": name, "law": const["law"], "runs": [], "Mu": mu.tolist(), "Mf": mf.tolist(),
                                        "op_t_s": op["t_s"], "op": op})
            rec["runs"].append(p["run_id"])
    return list(uniq.values())


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    t0 = time.perf_counter()
    items = R.catalogue_ext()
    sets_ = collect_sets()
    print("plants", len(items), "unique set structures", len(sets_), {s["set"]: sum(1 for x in sets_ if x["set"] == s["set"]) for s in sets_})
    jobs = [(i, "nominal", None, None) for i in range(len(items))]
    for s in range(4):
        mu, mf = single_leg_structure(s)
        jobs += [(i, f"single_{LEGS[s]}", mu.tolist(), mf.tolist()) for i in range(len(items))]
    for n, s in enumerate(sets_):
        jobs += [(i, f"set{n}_{s['set']}", s["Mu"], s["Mf"]) for i in range(len(items))]
    print("jobs", len(jobs), flush=True)
    with Pool(workers) as pool:
        rows = pool.map(job, jobs, chunksize=4)
    out = {"cfg": {k: v for k, v in CFG.__dict__.items()}, "sets": [{k: v for k, v in s.items() if k != "op"} for s in sets_],
           "rows": rows, "wall_s": time.perf_counter() - t0}
    (HERE / "t4_results.json").write_text(json.dumps(out, default=float), encoding="utf-8")
    summ = {}
    for r in rows:
        s = summ.setdefault(r["struct"], {"Ms_max": 0.0, "plant": None, "ch": None, "rho": 0.0, "rho_plant": None, "Ms_z": 0.0, "n1": set()})
        for ch in JUDGED:
            if r[ch]["Ms"] > s["Ms_max"]:
                s.update(Ms_max=r[ch]["Ms"], plant=r["plant"], ch=ch, w=r[ch]["w"])
        s["Ms_z"] = max(s["Ms_z"], r["z"]["Ms"])
        if r["rho_excl"] > s["rho"]:
            s.update(rho=r["rho_excl"], rho_plant=r["plant"])
        s["n1"].add(r["n_within_1e-6_of_1"])
    for k, s in summ.items():
        s["n1"] = sorted(s["n1"])
        print(k, json.dumps(s, default=float))
    (HERE / "t4_summary.json").write_text(json.dumps(summ, default=float, indent=1), encoding="utf-8")
    print("wall", round(time.perf_counter() - t0, 1))


if __name__ == "__main__":
    main()
