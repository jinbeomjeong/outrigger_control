"""H-S8-2: upper bound of -dp_r/dp_h on a locked leg, Chrono comparison, fallback estimate check.

Spec ``00_docs/04_control/s6_control_spec.md`` rev. 47 217.11 (H-S8-2, P-S8-13); law
``03_src/outrigger_sim/hydraulics/l2b_rod_side.py`` (read only).

Locked law (L2b, k_h and k_r frozen at s_lock):
    p_r = max(p_floor, p_r0 - r (F_p - F_p,lock) / A_ann),  r = k_r / (k_h + k_r)
    p_h = (F_p + p_r A_ann) / A_p
=> above the floor  -dp_r/dp_h = r A_p / ((1 - r) A_ann) = (k_r / k_h)(A_p / A_ann)
                                = (beta_r / beta_h) (L_0h + s) / (L_0r + s_max - s)  =: R(s)
(cylinder areas and a common beta cancel; the ratio of the two oil column lengths).

Parts
  A  tables: R(s) over L_0h, L_0r, s; trapped-preload rod pressure at lift-off; beta(p) and
     entrained-air sensitivity of the integrated ratio.
  B  Chrono 1 ms records: every lock run (s_ref constant), law residual, observed ratio,
     underestimate with the current fallback ratio 1.296 / 1.232 and with the bound R_ub(s).
  C  10 Hz replica of the fallback estimate (current code and proposal P-S8-13) on every
     command-free stretch of every case: min(p_r_hat - p_r_true) and the lower-bound
     error (p_r_true - p_r_hat) A_ann.

Usage: python -I h_s8_2_lock_ratio.py <out.json> <batch_dir> [<batch_dir> ...]
Read only on the batches. No random numbers.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

BAR = 1e5
LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_R = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
W_ROD = np.array([1047.19, 1047.19, 717.48, 717.48])  # m_rod g [N] (controller meta)
S_MAX = 0.7
FLOOR_G = 1.0e4 - 1.01325e5  # 0.1 bar abs as gauge [Pa]
R_FB = np.array([1.296, 1.296, 1.232, 1.232])  # current fallback_locked_ratio
L0H_MAX, L0R_MIN = 0.08, 0.02  # sensitivity range ends (user decision 2026-10-22)
DS_BOUND = 0.005  # stroke margin of the bound [m] (sensor 0.35 mm + s_ref vs reading)
KAPPA_BETA = 1.10  # beta(p) / finite-displacement factor of the bound (part A sensitivity, rod <= 350 bar)
WINDOW_S = 1.0  # (legacy constant, reported only) see lock_window_s()
LOCK_EPS = 1.0e-6  # plant lock threshold |u| <= eps [m/s] (l2b rod side lock_eps_m_s)
LIFT_CAP_MARGIN_N = math.inf  # no lift-off cap: seal friction and rod inertia (-13.7 kN seen) break it
PROP_EXT = 13.0 * BAR  # P-S8-13 pilot extend start: D2 extend upper 12 bar + 1 bar
PREV_S = 0.3  # moving samples this long before the stretch also give start candidates [s]
P_RET_YAML = np.array([34.818, 34.352, 31.193, 30.591]) * BAR  # YAML rod_side.p_r0_after_retract_Pa


def lock_window_s(u_last, tau_v):
    """Time after the first command-free sample within which the plant locks: the valve lag
    tau_v decays |u_last| to eps, plus one controller period."""
    return tau_v * math.log(max(abs(u_last), LOCK_EPS) / LOCK_EPS) + 0.1
# current model start values (two_pressure.py 250-254, CB 77-83)
FB_EXT = 8.0 * BAR
FB_PSI, FB_BACK, FB_CR = 3.0, 15.0 * BAR, 3.0 * BAR
CB_EXT_M, CB_RET_M = 11.4 * BAR, 0.7 * BAR


def ratio(s, l0h, l0r):
    return (l0h + s) / (l0r + S_MAX - s)


def ratio_ub(s):
    s = np.clip(s + DS_BOUND, 0.0, S_MAX)
    return KAPPA_BETA * (L0H_MAX + s) / (L0R_MIN + S_MAX - s)


def share(rr, leg):
    """r = k_r / (k_h + k_r) from R: r / (1 - r) = R A_ann / A_p."""
    x = rr * A_R[leg] / A_P[leg]
    return x / (1.0 + x)


# ---------------------------------------------------------------------------------------------
# Part A
# ---------------------------------------------------------------------------------------------

def part_a():
    s_grid = [0.0, 0.1, 0.2, 0.3, 0.35, 0.39, 0.40, 0.45, 0.5, 0.55, 0.6, 0.65, 0.68, 0.6948]
    tab = []
    for l0h in (0.05, 0.08):
        for l0r in (0.02, 0.0361, 0.05, 0.1):
            tab.append({"L0h": l0h, "L0r": l0r,
                        "R": [round(ratio(s, l0h, l0r), 4) for s in s_grid]})
    ub = [round(float(ratio_ub(s)), 4) for s in s_grid]
    # trapped preload at lift-off: F_p -> -W_rod
    lift = []
    for leg, name in ((1, "front"), (2, "rear")):
        for s in (0.30, 0.40, 0.50, 0.60, 0.65):
            for l0r in (0.02, 0.05, 0.1):
                rr = ratio(s, 0.05, l0r)
                r = share(rr, leg)
                row = {"side": name, "s": s, "L0r": l0r, "R": round(rr, 3), "r": round(r, 4)}
                for lab, f_lock in (("static", 118.1e3 if leg < 2 else 72.1e3),
                                    ("210bar", 278.7e3 if leg < 2 else 199.6e3),
                                    ("350bar", 464.6e3 if leg < 2 else 332.6e3)):
                    pr = 2.0 * BAR + r * (f_lock + W_ROD[leg]) / A_R[leg]
                    ph = (-W_ROD[leg] + pr * A_R[leg]) / A_P[leg]
                    row[lab] = [round(pr / BAR, 1), round(ph / BAR, 1)]
                lift.append(row)
    return {"s_grid_m": s_grid, "R_table": tab, "R_ub_grid": ub, "liftoff": lift,
            "beta_sensitivity": beta_sensitivity()}


def beta_sensitivity():
    """Integrated -dp_r/dp_h of a locked front leg with beta(p) = tangent oil modulus
    (K0 + K1 p) and entrained free air (isothermal-polytropic, n = 1.4) in both chambers.
    Piston moves out (load loss): head expands, rod compresses."""
    leg = 1
    out = []
    a_p, a_r = A_P[leg], A_R[leg]
    for s, l0r in ((0.40, 0.05), (0.468, 0.0361), (0.65, 0.05)):
        v_h0 = a_p * (0.05 + s)
        v_r0 = a_r * (l0r + S_MAX - s)
        r_lin = ratio(s, 0.05, l0r)
        for p_h0, p_r0 in ((171e5, 2e5), (89e5, 2e5), (89e5, 35e5)):
            for k1, x_air in ((0.0, 0.0), (10.0, 0.0), (0.0, 0.002), (10.0, 0.002), (10.0, 0.01)):
                def beta(p, k1=k1, x_air=x_air):
                    p_abs = max(p + 1.01325e5, 1.0e3)
                    oil = 1.0e9 + k1 * (p - 100e5)
                    air = x_air * (1.01325e5 / p_abs) ** (1 / 1.4) / (1.4 * p_abs)
                    return 1.0 / (1.0 / oil + air)

                def rhs(_x, y):
                    ph, pr = y
                    vh = v_h0 + a_p * _x
                    vr = v_r0 - a_r * _x
                    return [-beta(ph) * a_p / vh, beta(pr) * a_r / vr]

                def hit(_x, y):
                    return y[0] - (p_h0 - 100e5 if p_h0 > 120e5 else p_h0 - 29e5)
                hit.terminal = True
                sol = solve_ivp(rhs, (0.0, 0.05), [p_h0, p_r0], events=hit, rtol=1e-9,
                                atol=1.0, max_step=1e-5)
                ph1, pr1 = sol.y[0, -1], sol.y[1, -1]
                r_eff = (pr1 - p_r0) / (p_h0 - ph1)
                out.append({"s": s, "L0r": l0r, "p_h0_bar": p_h0 / BAR, "p_r0_bar": p_r0 / BAR,
                            "K1": k1, "x_air": x_air, "dp_h_bar": round((ph1 - p_h0) / BAR, 2),
                            "dp_r_bar": round((pr1 - p_r0) / BAR, 2), "R_eff": round(r_eff, 4),
                            "R_lin": round(r_lin, 4), "R_eff/R_lin": round(r_eff / r_lin, 4)})
    return out


# ---------------------------------------------------------------------------------------------
# case loading
# ---------------------------------------------------------------------------------------------

def find_cases(batch: Path):
    out = []
    for p in sorted(batch.rglob("pads.npz")):
        c = p.parent
        if (c / "record" / "meta.json").exists() and (c / "r8_series.npz").exists():
            out.append(c)
    return out


def load_case(c: Path):
    meta = json.loads((c / "record" / "meta.json").read_text(encoding="utf-8"))
    act = meta.get("run", {}).get("engine", {}).get("actuator", {})
    rs = act.get("rod_side")
    if not isinstance(rs, dict) or rs.get("mechanics") != "one_sided_parallel":
        return None
    s8 = act.get("s8", {}) if isinstance(act.get("s8"), dict) else {}
    cb = None
    if s8.get("lock_valve") == "counterbalance":
        cb = s8["counterbalance"]["params"]
    with np.load(c / "pads.npz", allow_pickle=True) as z:
        pads = {k: z[k] for k in ("t", "head_pressure", "rod_pressure", "s_motor", "F_pressure",
                                  "airborne", "cb_delta")}
    with np.load(c / "r8_series.npz", allow_pickle=True) as z:
        r8 = {k: z[k] for k in ("t", "issued_u", "F_lower_est_N", "phase")}
    with np.load(c / "record" / "record.npz", allow_pickle=True) as z:
        rec = {k: z[k] for k in ("t", "meas.head_pressure", "meas.rod_pressure", "meas.stroke")}
    valve = act.get("valve") if isinstance(act.get("valve"), dict) else {}
    tau_v = float(valve.get("tau_v_s", 0.0)) if valve.get("valve_model_on", False) else 0.0
    return {"name": c.name, "batch": c.parents[0].name if c.parent.name != "episodes" else
            "ml_pilot", "path": str(c), "L0r": np.array(rs["rod_dead_length_m"], float),
            "L0h": float(rs["head_dead_length_m"]), "cb": cb, "pads": pads, "r8": r8, "rec": rec,
            "tau_v": tau_v}


# ---------------------------------------------------------------------------------------------
# Part B: 1 ms lock runs
# ---------------------------------------------------------------------------------------------

def lock_runs(sm, min_len):
    still = np.abs(np.diff(sm)) <= 1.0e-9  # |u| <= 1e-6 m/s over 1 ms
    locked = np.r_[False, still]
    edges = np.flatnonzero(np.diff(locked.astype(np.int8)))
    starts = list(edges[~locked[edges]] + 1) if edges.size else []
    runs = []
    for j0 in starts:
        j1 = j0
        while j1 + 1 < locked.size and locked[j1 + 1]:
            j1 += 1
        if j1 - j0 + 1 >= min_len:
            runs.append((j0, j1))
    return runs


def part_b(case):
    p = case["pads"]
    t = p["t"]
    rows = []
    for leg in range(4):
        sm = p["s_motor"][:, leg]
        ph, pr = p["head_pressure"][:, leg], p["rod_pressure"][:, leg]
        for j0, j1 in lock_runs(sm, 200):
            j0 = min(j0 + 5, j1)  # skip the lock step (p_r0 override lands within ~5 ms)
            s_l = sm[j0]
            p_h0, p_r0 = ph[j0], pr[j0]
            seg = slice(j0, j1 + 1)
            rm = ratio(s_l, case["L0h"], case["L0r"][leg])
            drop = p_h0 - ph[seg]
            pred = np.maximum(FLOOR_G, p_r0 + rm * drop)
            resid = pr[seg] - pred
            vent = float(np.ptp(p["cb_delta"][seg, leg])) if case["cb"] is not None else 0.0
            m = (drop > 10 * BAR) & (pr[seg] > FLOOR_G + BAR)
            obs = float(np.max((pr[seg][m] - p_r0) / drop[m])) if m.any() else math.nan
            ml = pr[seg] > FLOOR_G + BAR
            fit = math.nan
            if ml.sum() > 20 and np.ptp(ph[seg][ml]) > 10 * BAR:
                fit = float(-np.polyfit(ph[seg][ml], pr[seg][ml], 1)[0])
            est_fb = p_r0 + R_FB[leg] * np.maximum(drop, 0.0)
            est_ub = p_r0 + ratio_ub(s_l) * np.maximum(drop, 0.0)
            k_max = int(np.argmax(pr[seg]))
            back = max(j0 - 50, 0)
            direction = float(np.sign(sm[j0] - sm[back]))
            rows.append({
                "case": case["name"], "leg": LEGS[leg], "t0": round(float(t[j0]), 3),
                "t1": round(float(t[j1]), 3), "s_lock": round(float(s_l), 4),
                "L0r": float(case["L0r"][leg]), "dir_before": direction,
                "p_h0": round(p_h0 / BAR, 2), "p_r0": round(p_r0 / BAR, 2),
                "F_lock_kN": round(float(p["F_pressure"][j0, leg]) / 1e3, 2),
                "R_model": round(float(rm), 4), "R_ub": round(float(ratio_ub(s_l)), 4),
                "R_obs_max": None if math.isnan(obs) else round(obs, 4),
                "R_fit": None if math.isnan(fit) else round(fit, 4),
                "max_drop_bar": round(float(drop.max()) / BAR, 2),
                "p_r_max": round(float(pr[seg].max()) / BAR, 2),
                "law_resid_bar": round(float(np.max(np.abs(resid))) / BAR, 3),
                "under_fb_bar": round(float(np.max(pr[seg] - est_fb)) / BAR, 2),
                "under_fb_kN": round(float(np.max(pr[seg] - est_fb)) * A_R[leg] / 1e3, 2),
                "under_ub_bar": round(float(np.max(pr[seg] - est_ub)) / BAR, 3),
                "over_ub_at_prmax_kN": round(float(est_ub[k_max] - pr[seg][k_max]) * A_R[leg] / 1e3, 2),
                "airborne": bool(p["airborne"][seg, leg].any()),
                "cb_vent_m": vent,
            })
    return rows


# ---------------------------------------------------------------------------------------------
# Part C: 10 Hz replica of the fallback estimate
# ---------------------------------------------------------------------------------------------

def model_moving(case, sign, head, leg, current=False):
    """Moving-state rod estimate (start value of a lock). ``current``: the code as of
    2026-10-25 (two_pressure.py); otherwise the P-S8-13 retract start also covers the plant's
    fixed after-retract lock pressure (YAML p_r0_after_retract)."""
    cb = case["cb"]
    if cb is None:
        if sign > 0:
            return FB_EXT if current else PROP_EXT
        formula = FB_BACK + (head - FB_BACK) / FB_PSI + FB_CR
        return formula if current else max(formula, P_RET_YAML[leg])
    p_set, psi, back = cb["p_set_Pa"], cb["pilot_ratio"], cb["back_pressure_Pa"]
    if sign > 0:
        return max(back, p_set - psi * head) + CB_EXT_M
    return max(0.0, (p_set - head) / psi) + CB_RET_M


def true_lock_time(p, leg, t_from, t_to):
    """First 1 ms sample in [t_from, t_to] that starts a still run of >= 50 ms (plant lock)."""
    t = p["t"]
    j0 = int(np.searchsorted(t, t_from - 1e-9))
    j1 = int(np.searchsorted(t, t_to + 1e-9))
    sm = p["s_motor"][j0:j1 + 51, leg]
    still = np.abs(np.diff(sm)) <= 1.0e-9
    run = 0
    for j in range(still.size):
        run = run + 1 if still[j] else 0
        if run >= 50:
            return j0 + j - 49  # index of the first still sample of the run
    return None


def window_estimate(case, sign, hm, st, cand, leg, m_prev=-np.inf):
    """P-S8-13 locked fallback estimate over one command-free stretch (10 Hz samples).

    ``cand``: samples that may be the lock instant (the lock window). For every sample k
    p_hat(k) = max over candidates j <= k of  M(sign, h_j) + R_ub(s_k) (h_j - h_k)^+
    with M the moving-state model of the last command direction (start value) and R_ub from
    the running max of the measured stroke over the candidates."""
    n = hm.size
    est = np.empty(n)
    starts = np.array([max(model_moving(case, sign, h, leg), m_prev) for h in hm])
    s_run = -np.inf
    for k in range(n):
        if cand[k]:
            s_run = max(s_run, st[k])
        s_use = s_run if np.isfinite(s_run) else st[k]
        j = np.flatnonzero(cand[: k + 1])
        if j.size == 0:
            est[k] = starts[k]
            continue
        est[k] = float(np.max(starts[j] + ratio_ub(s_use) * np.maximum(hm[j] - hm[k], 0.0)))
    return est


def part_c(case):
    r8, rec, p = case["r8"], case["rec"], case["pads"]
    t = r8["t"]
    ir = np.clip(np.searchsorted(rec["t"], t - 1e-9), 0, rec["t"].size - 1)
    ip = np.clip(np.searchsorted(p["t"], t - 1e-9), 0, p["t"].size - 1)
    out = []
    n = t.size
    for leg in range(4):
        cmd = np.r_[0.0, r8["issued_u"][:-1, leg]]  # applied = output of the previous period
        hm = rec["meas.head_pressure"][ir, leg]
        rm_ = rec["meas.rod_pressure"][ir, leg]
        st = rec["meas.stroke"][ir, leg]
        ph_true = p["head_pressure"][ip, leg]
        pr_true = p["rod_pressure"][ip, leg]
        f_true = p["F_pressure"][ip, leg]
        f_floor = -(W_ROD[leg] + LIFT_CAP_MARGIN_N)
        k = 0
        last_est, last_sign, last_u = 0.0, 1.0, 0.0
        moving_hist = []  # (t, P-S8-13 moving model value)
        while k < n:
            if cmd[k] != 0.0:
                moving_hist.append((t[k], model_moving(case, float(np.sign(cmd[k])), hm[k], leg)))
                last_sign = float(np.sign(cmd[k]))
                last_u = float(cmd[k])
                last_est = model_moving(case, last_sign, hm[k], leg, current=True)
                k += 1
                continue
            k0 = k
            while k < n and cmd[k] == 0.0:
                k += 1
            k1 = k  # exclusive
            if k0 == 0:
                continue  # no moving history (start of record)
            idx = np.arange(k0, k1)
            m_prev = max([v for (tt, v) in moving_hist if tt >= t[k0] - PREV_S - 1e-9], default=-np.inf)
            w_s = lock_window_s(last_u, case["tau_v"])
            in_w = t[idx] < t[k0] + w_s - 1e-9
            in_w[0] = True
            # plant lock instant (1 ms) and the anchor miss of the 10 Hz window max
            jl = true_lock_time(p, leg, t[k0] - 0.1, t[k1 - 1])
            if jl is not None:
                delay = float(p["t"][jl] - t[k0])
                ph_lock = float(p["head_pressure"][jl, leg])
                ph_win = float(np.max(ph_true[idx][in_w]))
                miss = ph_lock - ph_win
            else:
                delay, ph_lock, miss = math.nan, math.nan, math.nan
            # current code
            est_cur = last_est + R_FB[leg] * np.maximum(hm[k0] - hm[idx], 0.0)
            # proposal A (P-S8-13): every window sample j is a lock-instant candidate;
            # p_hat(k) = max_j [M(h_j) + R_ub(s) (h_j - h_k)^+]  (M = moving model at h_j)
            est_m = window_estimate(case, last_sign, hm[idx], st[idx], in_w, leg, m_prev)
            hmax = np.maximum.accumulate(np.where(in_w, hm[idx], -np.inf))
            # variant B: candidates only at the two samples around the predicted lock instant
            t_pred = t[k0] + w_s - 0.1
            cand_b = np.abs(t[idx] - t_pred) <= 0.1 + 1e-9
            if not cand_b.any():
                cand_b = in_w.copy()
            est_b = window_estimate(case, last_sign, hm[idx], st[idx], cand_b, leg, m_prev)
            # reading candidate: rod sensor valid up to sample jv, fallback after it;
            # V = r(jv) + R_ub (H - h)^+ with H the max head over [jv, window end]; max(V, A)
            worst_v = math.inf
            for jv in range(idx.size):
                rest = idx[jv:]
                w_rest = in_w[jv:].copy()
                w_rest[0] = True
                hv = np.maximum.accumulate(np.where(w_rest, hm[rest], -np.inf))
                sv = np.maximum.accumulate(np.where(w_rest, st[rest], -np.inf))
                vv = rm_[rest[0]] + ratio_ub(sv) * np.maximum(hv - hm[rest], 0.0)
                vv = np.maximum(vv, est_m[jv:])
                f_low = np.maximum(ph_true[rest] * A_P[leg] - vv * A_R[leg], f_floor)
                worst_v = min(worst_v, float(np.min(f_true[rest] - f_low)))

            def lower(est):
                return np.maximum(ph_true[idx] * A_P[leg] - est * A_R[leg], f_floor)

            err_cur = lower(est_cur) - f_true[idx]
            err_m = lower(est_m) - f_true[idx]
            err_b = lower(est_b) - f_true[idx]
            post = ~in_w  # after the lock window (leg certainly locked)
            raw_m = ph_true[idx] * A_P[leg] - est_m * A_R[leg]
            out.append({
                "case": case["name"], "leg": LEGS[leg], "t0": round(float(t[k0]), 2),
                "t1": round(float(t[k1 - 1]), 2), "n": int(idx.size), "start_sign": last_sign,
                "u_last_mm_s": round(1e3 * last_u, 3), "window_s": round(w_s, 3),
                "lock_delay_s": None if math.isnan(delay) else round(delay, 3),
                "p_h_lock_1ms_bar": None if math.isnan(ph_lock) else round(ph_lock / BAR, 2),
                "anchor_miss_bar": None if math.isnan(miss) else round(miss / BAR, 2),
                "p_h_anchor_bar": round(float(hm[k0]) / BAR, 2),
                "p_h_max_window_bar": round(float(hmax[-1]) / BAR, 2),
                "p_r_true_max_bar": round(float(pr_true[idx].max()) / BAR, 2),
                "F_true_min_kN": round(float(f_true[idx].min()) / 1e3, 2),
                "cur_err_max_kN": round(float(err_cur.max()) / 1e3, 2),
                "prop_err_max_kN": round(float(err_m.max()) / 1e3, 2),
                "prop_reading_err_max_kN": round(-worst_v / 1e3, 2),
                "prop_over_median_kN": round(float(np.median(-err_m)) / 1e3, 2),
                "prop_over_end_kN": round(float(-err_m[-1]) / 1e3, 2),
                "prop_cap_active_frac": round(float(np.mean(raw_m < f_floor)), 3),
                "cur_over_end_kN": round(float(-err_cur[-1]) / 1e3, 2),
                "varB_err_max_kN": round(float(err_b.max()) / 1e3, 2),
                "varB_over_end_kN": round(float(-err_b[-1]) / 1e3, 2),
                "cur_err_max_post_kN": round(float(err_cur[post].max()) / 1e3, 2) if post.any() else None,
                "prop_err_max_post_kN": round(float(err_m[post].max()) / 1e3, 2) if post.any() else None,
                "t_cur_err_max": round(float(t[idx][int(np.argmax(err_cur))]), 2),
            })
    return out


def main():
    out_path = Path(sys.argv[1])
    batches = [Path(b) for b in sys.argv[2:]]
    result = {"part_a": part_a(), "constants": {
        "L0H_MAX": L0H_MAX, "KAPPA_BETA": KAPPA_BETA, "PROP_EXT_Pa": PROP_EXT, "PREV_S": PREV_S, "P_RET_YAML_Pa": P_RET_YAML.tolist(), "L0R_MIN": L0R_MIN, "DS_BOUND_m": DS_BOUND, "WINDOW_S": WINDOW_S,
        "R_FB": R_FB.tolist(), "S_MAX": S_MAX, "FLOOR_G_Pa": FLOOR_G}}
    runs, stretches, skipped, capcheck = [], [], [], []
    for b in batches:
        for c in find_cases(b):
            case = load_case(c)
            if case is None:
                skipped.append(str(c))
                continue
            for r in part_b(case):
                r["batch"] = b.name
                runs.append(r)
            for r in part_c(case):
                r["batch"] = b.name
                stretches.append(r)
            fpw = case["pads"]["F_pressure"] + W_ROD[None, :]
            j = np.unravel_index(int(np.argmin(fpw)), fpw.shape)
            capcheck.append({"case": case["name"], "batch": b.name, "leg": LEGS[j[1]],
                             "t": round(float(case["pads"]["t"][j[0]]), 3),
                             "min_Fp_plus_Wrod_kN": round(float(fpw[j]) / 1e3, 3)})
            print(f"{b.name}/{c.name}: runs {len(runs)} stretches {len(stretches)}", flush=True)
    result["runs"] = runs
    result["stretches"] = stretches
    result["skipped"] = skipped
    result["lift_cap_check"] = capcheck
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
