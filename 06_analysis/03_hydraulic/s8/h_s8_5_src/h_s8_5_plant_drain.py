"""H-S8-5 part A: rod-side drain after a locked lift-off in the L2b plant law (after F1).

Drives ``outrigger_sim.hydraulics.l2b_rod_side.L2bRodSide`` (read only, one leg, oil only):
extend -> lock under load F_lock -> unload to the airborne force (rod side rises to p_pre) ->
release with an extension command through the valve lag tau_v -> record the rod pressure.
Sweeps beta, L0r, s_lock, lock valve (pilot check / CB), tau_v, p_pre and reports the drain time
constant tau_d (log-linear fit of the excess over the moving target) and the 10 Hz sample ratios.

Usage: python -I h_s8_5_plant_drain.py <repo_root> <out.json>
"""

from __future__ import annotations

import itertools
import json
import math
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[1])
sys.path.insert(0, str(REPO / "03_src"))

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide  # noqa: E402

LEGS = {
    "front": {"A_p": 0.013273229, "A_ann": 0.00376991118, "m_rod_g": 1050.0},
    "rear": {"A_p": 0.00950331778, "A_ann": 0.00314159265, "m_rod_g": 720.0},
}
V_MAX = 0.0209243016
DT = 1e-4
CB = types.SimpleNamespace(p_set_Pa=330e5, pilot_ratio=4.0, back_pressure_Pa=2e5)


def run_case(leg: str, beta: float, l0r: float, s_lock: float, valve: str, tau_v: float,
             p_pre_bar: float, u_frac: float, release_tau: float = 0.05) -> dict:
    g = LEGS[leg]
    rs = L2bRodSide(
        head_area_m2=[g["A_p"]], annulus_area_m2=[g["A_ann"]], k_out_N_m=[math.inf],
        bulk_modulus_Pa=beta, head_dead_length_m=0.05, rod_dead_length_m=[l0r], stroke_m=0.7,
        p_r0_after_extend_Pa=[2e5], p_r0_after_retract_Pa=[30e5], p_floor_abs_Pa=1e4,
        release_tau_s=release_tau, lock_eps_m_s=1e-6,
        counterbalance=CB if valve == "cb" else None,
    )
    k_h = beta * g["A_p"] / (0.05 + s_lock)
    k_r = beta * g["A_ann"] / (0.7 - s_lock + l0r)
    share = k_r / (k_h + k_r)
    f_air = -g["m_rod_g"]
    # lock force so that the airborne locked rod pressure is p_pre (p_r0 after extend 2 bar g,
    # CB: regulation at the lock force, 2 bar g when the load is above the regulation end)
    f_lock = f_air + (p_pre_bar - 2.0) * 1e5 * g["A_ann"] / share
    k2 = k_h
    c_lock = f_lock / k2
    t = 0.0
    # moving (extension) a few steps, then lock
    for _ in range(20):
        t += DT
        rs.spring_force_N(t, DT, [0.005], [s_lock], [c_lock], [f_lock])
    for _ in range(5):
        t += DT
        rs.spring_force_N(t, DT, [0.0], [s_lock], [c_lock], [f_lock])
    p_r0 = float(rs.lock_table()["p_r0_Pa"][0])
    k1 = k_h + k_r
    # unload while locked (piston fixed in the oil sense: c moves)
    n_unload = 200
    for j in range(1, n_unload + 1):
        f_target = f_lock + (f_air - f_lock) * j / n_unload
        c = c_lock + (f_target - f_lock) / k1
        t += DT
        rs.spring_force_N(t, DT, [0.0], [s_lock], [c], [f_target])
    p_pre = float(rs.rod_pressure_Pa[0])
    # release: commanded u_frac v_max through the first-order valve lag tau_v
    t_rel0 = t
    times, pr = [0.0], [p_pre]
    u_cmd = u_frac * V_MAX
    for j in range(1, int(0.6 / DT) + 1):
        tt = j * DT
        u = u_cmd * (1.0 - math.exp(-tt / tau_v)) if tau_v > 0 else u_cmd
        t = t_rel0 + tt
        rs.spring_force_N(t, DT, [u], [s_lock], [c], [f_air])
        times.append(tt)
        pr.append(float(rs.rod_pressure_Pa[0]))
    times_a = np.array(times)
    pr_a = np.array(pr) / 1e5
    p_inf = pr_a[-1]
    exc = pr_a - p_inf
    m = (times_a > 0.002) & (exc > 0.02 * (p_pre / 1e5 - p_inf)) & (exc > 0)
    tau_fit = math.nan
    if m.sum() > 10:
        slope = np.polyfit(times_a[m], np.log(exc[m]), 1)[0]
        tau_fit = -1.0 / slope
    # 10 Hz samples: pre at -phi, then 0.1 - phi, 0.2 - phi, ...
    worst = {"ratio_gauge_max": 0.0, "ratio_excess_max": 0.0}
    rule = {"current_fail": 0, "excess_fail": 0, "triggered": 0, "phases": 0}
    for phi in np.arange(0.0, 0.1, 0.005):
        ts = [-phi + 0.1 * n for n in range(0, 6)]
        vals = [p_pre / 1e5 if tt <= 0 else float(np.interp(tt, times_a, pr_a)) for tt in ts]
        rule["phases"] += 1
        for n in range(1, 5):
            if vals[n - 1] - vals[n] > 100.0:
                p1, p2 = vals[n], vals[n + 1]
                rule["triggered"] += 1
                worst["ratio_gauge_max"] = max(worst["ratio_gauge_max"], p2 / p1)
                worst["ratio_excess_max"] = max(worst["ratio_excess_max"],
                                                (p2 - p_inf) / max(p1 - p_inf, 1e-9))
                p_hi = 12.0 if valve == "pilot" else p_inf + 15.0
                if p2 > max(p_hi, 0.5 * p1):
                    rule["current_fail"] += 1
                if p2 > p_hi + 0.5 * max(p1 - p_hi, 0.0):
                    rule["excess_fail"] += 1
                break
    return {
        "leg": leg, "beta_GPa": beta / 1e9, "L0r_m": l0r, "s_lock_m": s_lock, "valve": valve,
        "tau_v_s": tau_v, "u_frac": u_frac, "p_r0_bar": p_r0 / 1e5, "p_pre_bar": p_pre / 1e5,
        "p_inf_bar": float(p_inf), "tau_d_fit_s": tau_fit,
        "p_at_0.1s_bar": float(np.interp(0.1, times_a, pr_a)),
        "p_at_0.2s_bar": float(np.interp(0.2, times_a, pr_a)),
        "ratio_excess_0.1s": float((np.interp(0.1, times_a, pr_a) - p_inf) / (p_pre / 1e5 - p_inf)),
        **worst, **rule,
        "trace_25ms_bar": [float(np.interp(k * 0.025, times_a, pr_a)) for k in range(9)],
    }


def main() -> None:
    out = Path(sys.argv[2])
    rows = []
    for leg, beta, l0r, s_lock, valve, tau_v, p_pre in itertools.product(
            ("front", "rear"), (0.69e9, 1.0e9, 1.6e9), (0.02, 0.05, 0.10), (0.2, 0.45, 0.65),
            ("pilot", "cb"), (0.0, 0.05, 0.1), (125.0, 174.0, 250.0, 345.0)):
        rows.append(run_case(leg, beta, l0r, s_lock, valve, tau_v, p_pre, 0.25))
    taus = [r["tau_d_fit_s"] for r in rows if math.isfinite(r["tau_d_fit_s"])]
    summary = {
        "n": len(rows),
        "tau_d_fit_min_s": min(taus), "tau_d_fit_max_s": max(taus),
        "ratio_gauge_max": max(r["ratio_gauge_max"] for r in rows),
        "ratio_excess_max": max(r["ratio_excess_max"] for r in rows),
        "triggered": sum(r["triggered"] for r in rows),
        "current_rule_fail": sum(r["current_fail"] for r in rows),
        "excess_rule_fail": sum(r["excess_fail"] for r in rows),
        "by_valve": {},
    }
    for v in ("pilot", "cb"):
        sub = [r for r in rows if r["valve"] == v]
        summary["by_valve"][v] = {
            "p_inf_bar_range": [min(r["p_inf_bar"] for r in sub), max(r["p_inf_bar"] for r in sub)],
            "triggered": sum(r["triggered"] for r in sub),
            "current_fail": sum(r["current_fail"] for r in sub),
            "excess_fail": sum(r["excess_fail"] for r in sub),
            "ratio_gauge_max": max(r["ratio_gauge_max"] for r in sub),
            "fail_cases": [{k: r[k] for k in ("leg", "beta_GPa", "L0r_m", "s_lock_m", "tau_v_s",
                                             "p_pre_bar", "p_inf_bar", "current_fail",
                                             "triggered")}
                           for r in sub if r["current_fail"]][:20],
        }
    # sensitivity of the plant time constant itself to release_tau_s (not beta / L0r)
    summary["release_tau_sweep"] = [
        {"release_tau_s": rt, **{k: v for k, v in run_case("rear", 1e9, 0.05, 0.45, "pilot", 0.1,
                                                            174.0, 0.25, rt).items()
                                 if k in ("tau_d_fit_s", "ratio_gauge_max", "current_fail",
                                          "triggered", "p_at_0.1s_bar", "p_at_0.2s_bar")}}
        for rt in (0.02, 0.05, 0.1, 0.15, 0.2)]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
