"""Algebraic steady state of the shared-pump circuit (hydraulic_coupling.md sec. 4).

Independent of the time integration in model.py: uses flow_share.share (bisection on the
gallery flow balance), iterates the rod back pressure, and with the rigid body finds the
self stress T from the zero twist rate n.v = 0. Pressures GAUGE. Writes a hydcalc results
JSON per scenario for xcheck.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / ".claude" / "tools" / "hydraulics"))

import numpy as np  # noqa: E402
from hydcalc import write_results_json  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

from flow_share import share  # noqa: E402
from params import LEGS, OUT_DIR, Params, load_params, twist_vector  # noqa: E402
from scenarios import SCENARIOS, Scenario  # noqa: E402


def solve_circuit(p: Params, F: np.ndarray, u: np.ndarray, eta_v: float) -> dict:
    """Gallery pressure and flows for given cylinder forces, rod back pressure iterated."""
    cfg = p.share_config()
    ext, ret = u > 0, u < 0
    u_ms = u * p.v_max
    v = u_ms.copy()
    K_bt = p.K_spool * np.abs(u) * p.bt_ratio
    Q_p = p.Q_pump(eta_v)
    for _ in range(40):
        p_r = np.where(ext, p.p_T + (p.A_r * v / np.maximum(K_bt, 1e-30)) ** 2, np.where(ret, p.p_pilot, p.p_T))
        p_h = (F + p.A_r * p_r) / p.A_h
        p_L = np.where(ret, p_r, p_h)
        r = share(u_ms, p_L, Q_p, cfg)
        if np.abs(r.v - v).max() < 1e-10:
            v = r.v
            break
        v = 0.5 * v + 0.5 * r.v
    return {"p_P": r.p_P, "Q": r.Q, "v": v, "p_h": p_h, "p_r": p_r, "Q_byp": r.Q_byp, "ls": r.ls, "Q_p": Q_p,
            "F": F, "limited": r.limited}


def solve(p: Params, sc: Scenario) -> dict:
    """Prescribed: F fixed. Rigid: F = F0 + T n with T from n.v = 0 (constant load at steady state)."""
    F0, u = sc.loads(p), np.array(sc.u)
    if not sc.coupled:
        return {**solve_circuit(p, F0, u, sc.eta_v), "T": 0.0}
    n = twist_vector(p)
    res0 = solve_circuit(p, F0, u, sc.eta_v)
    if abs(n @ res0["v"]) < 1e-7:  # compatible at T = 0: the self stress keeps its start value
        return {**res0, "T": 0.0}

    def g(T: float) -> float:
        return float(n @ solve_circuit(p, F0 + T * n, u, sc.eta_v)["v"])

    g0 = g(0.0)
    step = 1.0e3
    while True:  # widen the bracket in both directions
        if g0 * g(step) <= 0:
            b = step
            break
        if g0 * g(-step) <= 0:
            b = -step
            break
        step *= 1.5
        if step > 4e5:
            raise RuntimeError(f"{sc.name}: no twist balance within 400 kN")
    T = brentq(g, 0.0, b, xtol=1.0)
    return {**solve_circuit(p, F0 + T * n, u, sc.eta_v), "T": T}


def results_dict(r: dict) -> dict:
    out = {}
    for i, leg in enumerate(LEGS):
        out[f"v_{leg}"] = (r["v"][i], "m/s")
        out[f"Q_in_{leg}"] = (r["Q"][i], "m**3/s")
        out[f"p_h_{leg}"] = (r["p_h"][i], "Pa")
        out[f"p_r_{leg}"] = (r["p_r"][i], "Pa")
    out["p_P"] = (r["p_P"], "Pa")
    out["Q_byp"] = (r["Q_byp"], "m**3/s")
    out["T_self_stress"] = (r["T"], "N")
    return out


def main() -> None:
    p = load_params()
    hand_dir = OUT_DIR / "hand"
    hand_dir.mkdir(parents=True, exist_ok=True)
    table = {}
    for sc in SCENARIOS:
        r = solve(p, sc)
        write_results_json(results_dict(r), hand_dir / f"{sc.name}.json", pressure_ref="gauge",
                           note=f"hand_calc.py, {sc.desc}, pressures gauge")
        table[sc.name] = {
            "desc": sc.desc, "Q_pump_L_min": r["Q_p"] * 6e4, "p_P_bar_g": r["p_P"] / 1e5,
            "Q_byp_L_min": r["Q_byp"] * 6e4, "T_kN": r["T"] / 1e3,
            "v_mm_s": dict(zip(LEGS, (r["v"] * 1e3).round(4).tolist())),
            "Q_L_min": dict(zip(LEGS, (r["Q"] * 6e4).round(4).tolist())),
            "p_h_bar_g": dict(zip(LEGS, (r["p_h"] / 1e5).round(3).tolist())),
        }
        print(f"{sc.name:6s} Qp {r['Q_p']*6e4:6.2f} pP {r['p_P']/1e5:7.2f} byp {r['Q_byp']*6e4:6.3f} T {r['T']/1e3:7.2f} kN "
              f"v[mm/s] {np.round(r['v']*1e3, 3)} ph[bar] {np.round(r['p_h']/1e5, 2)}")
    (OUT_DIR / "hand_summary.json").write_text(json.dumps(table, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
