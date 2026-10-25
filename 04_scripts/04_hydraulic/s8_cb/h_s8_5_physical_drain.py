"""H-S8-5 part B: physical (real machine) rod-side drain after a locked lift-off, and the P-S8-21
hold rule on 10 Hz samples.

Model (one leg, rod-side pilot check opened by an extension command, B -> T through the spool
meter-out edge; closed form in y = sqrt(p_r - p_T), theta = int a dt):
    spool opening a(t) = 1 - exp(-t / tau_v)                    (0 -> 1, fraction of the command)
    Q_out = K a sqrt(p_r - p_T),   K = kappa A_p u / sqrt(dp_c)  (edge sized like the meter-in
                                                                   edge: dp_c at head flow A_p u)
    free piston (sliding):  C dp_r/dt = A_ann u a - Q_out,  C = (V_r + V_h / phi^2) / beta + C_hose
    stuck piston (seal):    C dp_r/dt = -Q_out,             C = V_r / beta + C_hose
    hose dump at opening (B hose at p_T joins the chamber): p0 = (C_ch p_pre + C_hose p_T) / C
Counterbalance option: the same drain, clipped below at the CB regulation p_reg (rod side stops
draining when the CB closes).

Rule on readings (static sensor offset e on both samples): trigger = first period drop > 100 bar;
pending value p1, next p2. Current P-S8-21: p2 <= max(p_hi, rho p1). Excess form:
p2 <= p_hi + rho (p1 - p_hi).

Usage: python -I h_s8_5_physical_drain.py <out.json>
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
P_T = 2.0 * BAR
V_MAX = 0.0209243016
STROKE = 0.7
L0H = 0.08  # worst (largest head volume) of the 0.05 ... 0.08 m range
LEGS = {
    "front": (0.013273229, 0.00376991118),
    "rear": (0.00950331778, 0.00314159265),
}
HOSE_V = 290e-6
HOSE_BETA = 0.5e9
DP_MAX = 100.0  # D1 step threshold [bar]
P_HI = 12.0  # D2 extension rod-side upper bound, pilot check [bar g]
RHO = 0.5
PHASES = np.arange(0.0, 0.1, 0.005)
N_SAMPLES = 8


def theta_of_t(t: np.ndarray, tau_v: np.ndarray) -> np.ndarray:
    tv = np.maximum(tau_v, 1e-12)
    return np.where(tau_v > 0, t - tv * (1.0 - np.exp(-t / tv)), t)


def y_free(theta: np.ndarray, y0: np.ndarray, yinf: np.ndarray, two_c_over_k: np.ndarray
           ) -> np.ndarray:
    """Solve theta = (2C/K)[(y0 - y) + yinf ln((y0 - yinf)/(y - yinf))] for y (bisection)."""
    lo = yinf + 1e-9 * np.maximum(y0 - yinf, 1e-12)
    hi = y0.copy()
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        th = two_c_over_k * ((y0 - mid) + yinf * np.log((y0 - yinf) / (mid - yinf)))
        go_lower = th < theta  # not enough time at mid -> y is below mid
        hi = np.where(go_lower, mid, hi)
        lo = np.where(go_lower, lo, mid)
    y = 0.5 * (lo + hi)
    return np.where(theta <= 0, y0, y)


def pressure(t: np.ndarray, prm: dict) -> np.ndarray:
    """p_r [Pa g] at times t (broadcast: prm arrays shape (n, 1), t shape (1, m))."""
    th = theta_of_t(np.maximum(t, 0.0), prm["tau_v"])
    y0 = prm["y0"]
    if prm["free"]:
        y = y_free(th, np.broadcast_to(y0, th.shape).copy(),
                   np.broadcast_to(prm["yinf"], th.shape), np.broadcast_to(prm["tck"], th.shape))
    else:
        y = np.maximum(y0 - th / prm["tck"], 0.0)
    p = P_T + y * y
    p = np.maximum(p, prm["p_clip"])
    return np.where(t <= 0, prm["p_pre"], p)


def build(combos: list[tuple], free: bool) -> dict:
    a = np.array([[LEGS[c[0]][0], LEGS[c[0]][1], *c[1:]] for c in combos], dtype=float)
    (a_p, a_ann, beta, l0r, s, p_pre_bar, u_frac, tau_v, dpc_bar, kappa, hose, p_reg_bar) = a.T
    phi = a_p / a_ann
    v_r = a_ann * (STROKE - s + l0r)
    v_h = a_p * (L0H + s)
    v_eff = v_r + (v_h / phi**2 if free else 0.0)
    c_ch = v_eff / beta
    c_hose = hose * HOSE_V / HOSE_BETA
    c = c_ch + c_hose
    p_pre = p_pre_bar * BAR
    p0 = (c_ch * p_pre + c_hose * P_T) / c
    u = u_frac * V_MAX
    k = kappa * a_p * u / np.sqrt(dpc_bar * BAR)
    q = a_ann * u if free else np.zeros_like(u)
    yinf = q / k
    p_inf = P_T + yinf**2
    p_clip = np.where(p_reg_bar > 0, p_reg_bar * BAR, -np.inf)
    col = lambda v: v[:, None]  # noqa: E731
    return {
        "free": free, "tau_v": col(tau_v), "y0": col(np.sqrt(np.maximum(p0 - P_T, 0.0))),
        "yinf": col(yinf), "tck": col(2.0 * c / k), "p_pre": col(p_pre), "p_clip": col(p_clip),
        "p_inf": np.maximum(p_inf, np.where(p_reg_bar > 0, p_reg_bar * BAR, -np.inf)),
        "p_inf_raw": p_inf,
    }


def time_to_level(prm: dict, level_Pa: np.ndarray) -> np.ndarray:
    """Time [s] from opening until p_r <= level (inf if never); level > p_inf."""
    y_t = np.sqrt(np.maximum(level_Pa - P_T, 0.0))
    y0 = prm["y0"][:, 0]
    tck = prm["tck"][:, 0]
    if prm["free"]:
        yinf = prm["yinf"][:, 0]
        ok = (y_t > yinf) & (y0 > yinf)
        th = np.where(ok, tck * ((y0 - y_t) + yinf * np.log(np.where(ok, (y0 - yinf)
                                                                       / np.maximum(y_t - yinf,
                                                                                    1e-30), 1.0))),
                      np.inf)
    else:
        th = tck * (y0 - y_t)
    th = np.where(y_t >= y0, 0.0, th)
    tau_v = prm["tau_v"][:, 0]
    lo = np.zeros_like(th)
    hi = np.where(np.isfinite(th), th + tau_v + 1e-9, 0.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        f = theta_of_t(mid, tau_v) < th
        lo = np.where(f, mid, lo)
        hi = np.where(f, hi, mid)
    return np.where(np.isfinite(th), 0.5 * (lo + hi), np.inf)


def evaluate(prm: dict, p_hi_bar: np.ndarray) -> dict:
    n = prm["y0"].shape[0]
    n_ph = PHASES.size
    t = (-PHASES[:, None] + 0.1 * np.arange(N_SAMPLES)[None, :]).reshape(1, -1)
    p = (pressure(t, prm) / BAR).reshape(n, n_ph, N_SAMPLES)
    res = {}
    for e in (-4.0, 0.0, 4.0):
        r = p + e
        drop = r[:, :, :-1] - r[:, :, 1:]
        trig = drop > DP_MAX
        has = trig.any(axis=2)
        first = np.argmax(trig, axis=2) + 1  # index of the pending sample
        first = np.minimum(first, N_SAMPLES - 2)
        p1 = np.take_along_axis(r, first[..., None], axis=2)[..., 0]
        p2 = np.take_along_axis(r, (first + 1)[..., None], axis=2)[..., 0]
        p3 = np.take_along_axis(r, np.minimum(first + 2, N_SAMPLES - 1)[..., None], axis=2)[..., 0]
        hi = p_hi_bar[:, None]
        cur_fail = has & (p2 > np.maximum(hi, RHO * p1))
        exc_fail = has & (p2 > hi + RHO * np.maximum(p1 - hi, 0.0))
        two_fail = has & (p3 > np.maximum(hi, RHO * p1))  # hold two periods (current form)
        rho_cur = np.where(has & (p2 > hi), p2 / p1, 0.0)
        rho_exc = np.where(has & (p2 > hi), (p2 - hi) / np.maximum(p1 - hi, 1e-9), 0.0)
        res[e] = {
            "has": has.any(axis=1), "cur_fail": cur_fail.any(axis=1),
            "exc_fail": exc_fail.any(axis=1), "two_fail": two_fail.any(axis=1),
            "rho_cur": rho_cur.max(axis=1), "rho_exc": rho_exc.max(axis=1),
            "ratio_gauge": np.where(has, p2 / p1, 0.0).max(axis=1),
        }
    return res


def main() -> None:
    out = Path(sys.argv[1])
    grid_common = {
        "beta": (0.69e9, 1.0e9, 1.6e9), "l0r": (0.02, 0.05, 0.10), "s": (0.1, 0.3, 0.5, 0.65),
        "u": (0.05, 0.1, 0.25, 0.5, 1.0), "tau_v": (0.0, 0.02, 0.05, 0.1, 0.2),
        "dpc": (5.0, 10.0, 20.0), "kappa": (1.0, 0.5), "hose": (0.0, 1.0),
    }
    cases = {
        "pilot": {"p_pre": (125.0, 174.0, 250.0, 350.0), "p_reg": (0.0,)},
        "cb": {"p_pre": (250.0, 290.0, 324.0), "p_reg": (131.0, 143.0, 156.0, 167.0)},
    }
    rows_ref = []
    summary: dict = {}
    per_key: dict = {}
    for valve, cc in cases.items():
        for free in (True, False):
            combos = list(itertools.product(
                ("front", "rear"), grid_common["beta"], grid_common["l0r"], grid_common["s"],
                cc["p_pre"], grid_common["u"], grid_common["tau_v"], grid_common["dpc"],
                grid_common["kappa"], grid_common["hose"], cc["p_reg"]))
            chunk = 4000
            agg = {e: {k: [] for k in ("has", "cur_fail", "exc_fail", "two_fail", "rho_cur",
                                       "rho_exc", "ratio_gauge")} for e in (-4.0, 0.0, 4.0)}
            t63_all, t12_all, pinf_all = [], [], []
            for i0 in range(0, len(combos), chunk):
                sub = combos[i0:i0 + chunk]
                prm = build(sub, free)
                p_inf = prm["p_inf"]
                p_pre = prm["p_pre"][:, 0]
                p_reg = np.array([c[-1] for c in sub]) * BAR
                p_hi = np.where(p_reg > 0, p_reg / BAR + 15.0, P_HI)
                t63 = time_to_level(prm, p_inf + math.exp(-1) * (p_pre - p_inf))
                t12 = time_to_level(prm, np.where(p_reg > 0, p_reg + 15 * BAR, P_HI * BAR))
                t63_all.append(t63)
                t12_all.append(t12)
                pinf_all.append(p_inf / BAR)
                ev = evaluate(prm, p_hi)
                for e in ev:
                    for k in agg[e]:
                        agg[e][k].append(ev[e][k])
            t63 = np.concatenate(t63_all)
            t12 = np.concatenate(t12_all)
            pinf = np.concatenate(pinf_all)
            ag = {e: {k: np.concatenate(v) for k, v in d.items()} for e, d in agg.items()}
            key = f"{valve}_{'free' if free else 'stuck'}"
            names = ("leg", "beta", "l0r", "s", "p_pre", "u", "tau_v", "dpc", "kappa", "hose",
                     "p_reg")
            arr = {nm: np.array([c[j] for c in combos]) for j, nm in enumerate(names)}
            s = {"n": len(combos), "t63_s": [float(t63.min()), float(np.median(t63)),
                                             float(t63[np.isfinite(t63)].max())],
                 "p_inf_bar": [float(pinf.min()), float(pinf.max())],
                 "t_to_p_hi_s_max_finite": float(t12[np.isfinite(t12)].max()),
                 "never_below_p_hi": int((~np.isfinite(t12)).sum())}
            for e in ag:
                d = ag[e]
                s[f"e{e:+.0f}"] = {
                    "triggered": int(d["has"].sum()),
                    "current_fail": int(d["cur_fail"].sum()),
                    "excess_fail": int(d["exc_fail"].sum()),
                    "two_period_fail": int(d["two_fail"].sum()),
                    "rho_needed_current_max": float(d["rho_cur"].max()),
                    "rho_needed_excess_max": float(d["rho_exc"].max()),
                    "ratio_gauge_max": float(d["ratio_gauge"].max()),
                }
                if d["cur_fail"].any():
                    idx = np.where(d["cur_fail"])[0]
                    worst = idx[np.argmax(d["rho_cur"][idx])]
                    s[f"e{e:+.0f}"]["worst_current"] = {
                        nm: (str(arr[nm][worst]) if nm == "leg" else float(arr[nm][worst]))
                        for nm in names} | {"rho_needed": float(d["rho_cur"][worst]),
                                            "t63_s": float(t63[worst])}
                    # which factors drive failures: share of failing combos per value
                    s[f"e{e:+.0f}"]["fail_share_by"] = {
                        nm: {str(v): float(d["cur_fail"][arr[nm] == v].mean())
                             for v in np.unique(arr[nm])}
                        for nm in ("p_pre", "u", "tau_v", "dpc", "kappa", "hose", "beta", "l0r",
                                   "s")}
            summary[key] = s
            # per (beta, l0r, tau_v) table: t63 range and worst gauge ratio / rule (e = 0 / +4)
            for b, l, tv in itertools.product(grid_common["beta"], grid_common["l0r"],
                                              grid_common["tau_v"]):
                m = (arr["beta"] == b) & (arr["l0r"] == l) & (arr["tau_v"] == tv)
                d0, d4 = ag[0.0], ag[4.0]
                per_key.setdefault(key, []).append({
                    "beta_GPa": b / 1e9, "L0r_m": l, "tau_v_s": tv,
                    "t63_min_s": float(t63[m].min()), "t63_med_s": float(np.median(t63[m])),
                    "t63_max_s": float(t63[m][np.isfinite(t63[m])].max()),
                    "triggered_share": float(d0["has"][m].mean()),
                    "ratio_gauge_max_e0": float(d0["ratio_gauge"][m].max()),
                    "current_fail_e0": int(d0["cur_fail"][m].sum()),
                    "current_fail_e4": int(d4["cur_fail"][m].sum()),
                    "excess_fail_e4": int(d4["exc_fail"][m].sum()),
                    "rho_needed_current_e4": float(d4["rho_cur"][m].max()),
                })
            if valve == "pilot" and free:
                # reference rows (rear, s 0.45 ~ 0.5, u 0.25, dpc 10, kappa 1, no hose, p_pre 174)
                m = ((arr["leg"] == "rear") & (arr["s"] == 0.5) & (arr["u"] == 0.25)
                     & (arr["dpc"] == 10.0) & (arr["kappa"] == 1.0) & (arr["hose"] == 0.0)
                     & (arr["p_pre"] == 174.0))
                for j in np.where(m)[0]:
                    prm = build([combos[j]], True)
                    tt = np.array([[0.025 * k for k in range(13)]])
                    pr = pressure(tt, prm)[0] / BAR
                    rows_ref.append({
                        "beta_GPa": float(arr["beta"][j]) / 1e9, "L0r_m": float(arr["l0r"][j]),
                        "tau_v_s": float(arr["tau_v"][j]), "t63_s": float(t63[j]),
                        "p_inf_bar": float(pinf[j]),
                        "p_0.1_bar": float(pr[4]), "p_0.2_bar": float(pr[8]),
                        "p_0.3_bar": float(pr[12]),
                        "ratio_excess_0.1": float((pr[4] - pinf[j]) / (174.0 - pinf[j])),
                        "trace_25ms_bar": [float(v) for v in pr],
                        "triggered_e0": bool(ag[0.0]["has"][j]),
                        "current_fail_e4": bool(ag[4.0]["cur_fail"][j]),
                        "rho_needed_e4": float(ag[4.0]["rho_cur"][j]),
                    })
    result = {"summary": summary, "per_beta_l0r_tauv": per_key, "reference_rear": rows_ref,
              "settings": {"p_T_bar": P_T / BAR, "L0h_m": L0H, "hose_cm3": HOSE_V * 1e6,
                           "hose_beta_GPa": HOSE_BETA / 1e9, "dp_max_bar": DP_MAX,
                           "p_hi_pilot_bar": P_HI, "p_hi_cb": "p_reg + 15 bar", "rho": RHO,
                           "phases_s": PHASES.tolist(), "sensor_offset_bar": [-4, 0, 4]}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for r in rows_ref:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
               if k != "trace_25ms_bar"})


if __name__ == "__main__":
    main()
