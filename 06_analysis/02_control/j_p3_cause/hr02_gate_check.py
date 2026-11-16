"""P1 CheckOpenGate and the R5-4 line-fill bound gate: single-leg numerical check (read only).

Plant  = M1c VN (volume scale 1.0, c_v 0.02) line state of the harness P1 option, 1 ms chunks,
         chunk-mean valve speed of a first-order valve lag (tau_v 0.1 s); vectorised port of
         check_open_delay._extend_step / _retract_step, checked against the repo class.
Bound  = the R5-4 gate of jp3_remedy_spec.md 2.4 (kappa_x 0.8, same drain, threshold
         max(p_h_ub + p_cr, p_T + (p_hat + p_cr - p_T) / psi), p_h_ub = head reading + e_h;
         retract need_ub = retract_dead(p_h_ub, p_r = p_T, F_band, void 0, beta 0.69,
         L0r 0.10, L0h 0.08)).
Question: does the bound open no earlier than the plant (spec "tracker later") for head reading
errors, intra-period head changes and rod pressures down to the floor, and what does an early
opening cost at the next read?

Units SI inside; printed bar / ms / cm3; gauge pressures. Every valve value is an ASSUMPTION.
"""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")

from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit, CheckDelayInputs, CheckOpenDelay, RetractConfig, retract_dead)
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    RodPressureFlowLaw, flow_limited_rod_pressure)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting  # noqa: E402

BAR = 1e5
OUT = Path(__file__).with_suffix(".json")
TRACE = Path(__file__).parent / "h01_trace"
V_MAX = 0.0209243016
U_HOLD = 0.01 * V_MAX
EPS = 1e-6
TAU_V = 0.1
DT = 1e-3
T_PER = 0.1
N = 1000                       # 1 s of chunks after the step
S_MAX, L0, BETA = 0.70, 0.05, 1.0e9
P_T, P_CR, PSI = 2e5, 3e5, 3.5
V_LINE, BETA_H = 285e-6, 0.5e9
C_V, F_N, DP_C = 0.02, 0.05, 10e5
KAPPA = 0.8
P_FLOOR = 0.1e5 - 1.01325e5
NOISE3 = 3 * 0.2e5 + 0.025e5   # 3 sigma noise + chain resolution
E_READ = 4.0e5 + NOISE3        # normal grade clip + noise
A_H = {"front": 0.013273229, "rear": math.pi / 4 * 0.11**2}
A_ANN = {"front": 0.00376991118, "rear": math.pi / 4 * (0.11**2 - 0.09**2)}
E_OP = {"front": 0.4011, "rear": 0.3909}
U_EXT = (1.01 * U_HOLD, 0.5e-3, 1.0e-3, 2.0e-3, 4.71e-3, 10e-3, V_MAX)


def ratio(leg):
    return (L0 + E_OP[leg]) / (L0 + S_MAX - E_OP[leg])


def valve_means(u_prev, u_ext):
    """Chunk means of the lagged valve after a step u_prev -> u_ext at t = 0."""
    k = np.arange(N)
    start = u_ext + (u_prev - u_ext) * np.exp(-k * DT / TAU_V)
    return u_ext + (start - u_ext) * (TAU_V / DT) * (1 - math.exp(-DT / TAU_V))


def k_land(leg):
    return A_H[leg] * V_MAX / math.sqrt(DP_C)


# ---------------------------------------------------------------- extension ------------------
def ext_line(leg, u_prev, u_ext, kappa=1.0, reset=False):
    """p_A per chunk (after the chunk's fill) of the plant (kappa 1, pre-phase kept) or of the
    bound (kappa 0.8, x reset to 0 at the step). Returns p_A [N]."""
    a_h = A_H[leg]
    k_n = F_N * k_land(leg)
    x = 0.0
    line_dir = 0
    if not reset and u_prev > EPS:           # pre-phase: 1 s of the micro command (steady)
        for _ in range(1000):
            p_a = P_T + x * a_h * BETA_H / V_LINE
            g = max(1 - u_prev / (C_V * V_MAX), 0.0)
            x = max(x + (u_prev - k_n * g * math.sqrt(max(p_a - P_T, 0)) / a_h) * DT, 0.0)
        line_dir = 1
    elif not reset and u_prev < -EPS:
        line_dir = -1
    out = np.empty(N)
    for k, mean in enumerate(valve_means(u_prev, u_ext)):
        speed = abs(mean)
        d = int(np.sign(mean)) if speed > EPS else 0
        if d != 0 and line_dir not in (0, d):
            x, line_dir = 0.0, 0
        p_a = P_T + x * a_h * BETA_H / V_LINE
        g = max(1 - speed / (C_V * V_MAX), 0.0)
        drain = k_n * g * math.sqrt(max(p_a - P_T, 0)) / a_h
        if d > 0:
            line_dir = 1
            x = max(x + (kappa * speed - drain) * DT, 0.0)
        elif d == 0 and line_dir == 1:
            x = max(x - drain * DT, 0.0)
        out[k] = P_T + x * a_h * BETA_H / V_LINE
    return out


def plant_ext_open(leg, p_a, p_h0, p_r0, amp, s_ref=0.395):
    """First chunk index at which the plant head check opens (np.inf: none in 1 s).
    Vectorised over cases (p_h0, p_r0, amp arrays of one shape)."""
    t = (np.arange(N) + 1) * DT
    bump = np.sin(np.pi * ((t % T_PER) / T_PER))[None, :]
    p_h = p_h0[:, None] + amp[:, None] * bump
    p_r = np.maximum(p_r0[:, None] - ratio(leg) * amp[:, None] * bump, P_FLOOR)
    c_r = A_ANN[leg] * (L0 + S_MAX - s_ref) / BETA
    c_l = V_LINE / BETA_H
    rod_ok = P_T + PSI * (p_a[None, :] - P_T) - p_r - P_CR > 0
    released = np.maximum.accumulate(rod_ok, axis=1)
    first = np.argmax(rod_ok, axis=1)
    p_r_at = p_r[np.arange(len(p_r0)), first]
    p_b_after = (c_r * p_r_at + c_l * P_T) / (c_r + c_l)
    p_b = np.minimum(p_b_after[:, None], p_r)
    head_ok = released & (p_a[None, :] + PSI * p_b - p_h - P_CR > 0)
    idx = np.where(head_ok.any(axis=1), np.argmax(head_ok, axis=1), np.iinfo(np.int64).max)
    return idx, np.where(rod_ok.any(axis=1), first, np.iinfo(np.int64).max)


def bound_ext_open(p_a_hat, thr):
    """First substep index at which the bound line pressure reaches thr (vectorised)."""
    runmax = np.maximum.accumulate(p_a_hat)
    idx = np.searchsorted(runmax, thr, side="left")
    return np.where(idx < N, idx, np.iinfo(np.int64).max)


def validate_ext(rng):
    """Vectorised plant against the repo CheckOpenDelay (VN 1.0, c_v 0.02), 60 cases."""
    worst = 0
    for _ in range(60):
        leg = ("front", "rear")[rng.integers(2)]
        u_prev = float(rng.choice([0.0, 0.5 * U_HOLD]))
        u_ext = float(rng.choice(U_EXT))
        p_h0 = float(rng.uniform(5, 200)) * BAR
        p_r0 = float(rng.uniform(-0.9, 80)) * BAR
        p_a = ext_line(leg, u_prev, u_ext)
        mine, _ = plant_ext_open(leg, p_a, np.array([p_h0]), np.array([p_r0]), np.array([0.0]))
        i = 0 if leg == "front" else 3
        circ = CheckDelayCircuit(np.array([A_H["front"]] * 2 + [A_H["rear"]] * 2),
                                 np.array([A_ANN["front"]] * 2 + [A_ANN["rear"]] * 2),
                                 S_MAX, L0, L0, BETA, P_T, V_MAX, DP_C)
        model = CheckOpenDelay(CheckDelaySetting(kind="VN"), circ)
        ref = np.iinfo(np.int64).max
        steps = [(u_prev, 1000)] if u_prev > 0 else []
        k_global = 0
        for u_c, n in steps:              # pre-phase, steady valve
            for _ in range(n):
                u = np.zeros(4)
                u[i] = u_c
                model.filter(CheckDelayInputs(0.0, DT, u, np.full(4, p_h0), np.full(4, p_r0),
                                              np.ones(4, bool), np.zeros(4), np.zeros(4),
                                              np.full(4, 0.395)))
        for k, mean in enumerate(valve_means(u_prev, u_ext)):
            u = np.zeros(4)
            u[i] = mean
            model.filter(CheckDelayInputs(k * DT, DT, u, np.full(4, p_h0), np.full(4, p_r0),
                                          np.ones(4, bool), np.zeros(4), np.zeros(4),
                                          np.full(4, 0.395)))
            if model.is_open[i]:
                ref = k
                break
        k_global += 1
        worst = max(worst, abs(int(min(ref, 10**6)) - int(min(mine[0], 10**6))))
    return worst


# ---------------------------------------------------------------- retract --------------------
def need_vec(p_h, p_r, band, s, void, a_h, a_ann, beta, l0r, l0h):
    """Vectorised retract_dead (VN: rod_forward, delta = p_cr); returns need [m], rise [Pa]."""
    p_h = np.maximum(p_h, 0.0)
    delta = P_CR
    drive = p_h + P_CR - P_T
    p_free = np.maximum(drive / PSI, 0.0)
    limited = a_ann * (p_free - delta - p_r) > band
    p_b = np.where(limited, (drive - (a_ann * (delta + p_r) + band) / a_h) / (PSI - a_ann / a_h),
                   p_free)
    p_rod = np.maximum(p_b - delta, p_r)
    dp_h = np.maximum(a_ann * (p_rod - p_r) - band, 0.0) / a_h
    v_head = a_h * (l0h + s)
    v_rod = a_ann * (l0r + S_MAX - s)
    volume = (V_LINE * np.maximum(p_b - P_T, 0.0) / BETA_H + v_rod * (p_rod - p_r) / beta
              + a_ann * v_head * dp_h / (beta * a_h))
    return volume / a_ann + void, np.maximum(p_b - P_T, 0.0)


def ret_open(leg, need_fn, means, kappa, x0):
    """First chunk index with x >= need for vectorised cases; need_fn(k) -> (need, rise)."""
    k_n = F_N * k_land(leg)
    x = x0.copy()
    idx = np.full(x.shape, np.iinfo(np.int64).max)
    for k, mean in enumerate(means):
        speed = abs(mean)
        need, rise = need_fn(k)
        g = max(1 - speed / (C_V * V_MAX), 0.0)
        level = np.where(need > 0, np.minimum(x / np.where(need > 0, need, 1.0), 1.0), 0.0)
        drain = k_n * g * np.sqrt(rise * level) / A_ANN[leg]
        if mean < -EPS:
            x = np.maximum(x + (kappa * speed - drain) * DT, 0.0)
        else:
            x = np.maximum(x - drain * DT, 0.0)
        hit = (x >= need) & (idx == np.iinfo(np.int64).max) & (mean < -EPS)
        idx[hit] = k
    return idx


def main():
    rng = np.random.default_rng(20261116)
    res = {"validation_ext_max_chunk_diff": validate_ext(rng)}
    # ---- extension grid
    p_h0s = np.array([5, 10, 20, 35, 50, 77, 100, 150, 200]) * BAR
    p_r0s = np.array([P_FLOOR / BAR, 0, 2, 5, 13, 30, 54, 80]) * BAR
    amps = np.array([0.0, 1.0, 3.0]) * BAR
    u_prevs = (0.0, 0.5 * U_HOLD, -0.5 * U_HOLD)
    e_ss = np.array([-E_READ, 0.0, E_READ])
    d_hats = np.array([-1.91, 0.0, 10.0]) * BAR
    e_hs = np.arange(0.0, 12.01, 0.5) * BAR
    rows = []
    for leg, u_prev, u_ext in itertools.product(("front", "rear"), u_prevs, U_EXT):
        p_a = ext_line(leg, u_prev, u_ext)
        p_a_hat = ext_line(leg, u_prev, u_ext, kappa=KAPPA, reset=True)
        ph, pr, am = (a.ravel() for a in np.meshgrid(p_h0s, p_r0s, amps, indexing="ij"))
        k_plant, k_rod = plant_ext_open(leg, p_a, ph, pr, am)
        for (ci, (h, r, a)), es, dh in itertools.product(enumerate(zip(ph, pr, am)), e_ss,
                                                       d_hats):
            p_hat = max(r + dh, P_FLOOR)
            thr = np.maximum(h + es + e_hs + P_CR, P_T + (p_hat + P_CR - P_T) / PSI)
            k_b = bound_ext_open(p_a_hat, thr)
            rows.append((leg, u_prev, u_ext, h, r, a, es, dh, int(k_plant[ci]), k_b))
    # required e_h per class: smallest e_h with bound counting start >= plant release
    big = np.iinfo(np.int64).max

    def lead(row, j):
        kp, kb = row[8], row[9][j]
        if kp == big:
            return math.inf if kb == big else -math.inf  # plant never opens: bound must not
        if kb == big:
            return math.inf
        return (kb + 1 - kp) * DT
    classes = {}
    for row in rows:
        leg, u_prev, u_ext, h, r, a, es, dh, kp, kb = row
        key = (f"p_r<0:{r < 0}", f"amp{a / BAR:g}", f"err{es / BAR:+.2f}",
               f"dhat{dh / BAR:+.2f}")
        need = None
        for j, eh in enumerate(e_hs):
            if lead(row, j) >= 0:
                need = eh / BAR
                break
        cur = classes.setdefault(key, {"cases": 0, "max_required_e_h_bar": 0.0,
                                       "never_ok": 0, "lead_at_5bar_min_ms": math.inf})
        cur["cases"] += 1
        if need is None:
            cur["never_ok"] += 1
        else:
            cur["max_required_e_h_bar"] = max(cur["max_required_e_h_bar"], need)
        j5 = int(np.argmin(np.abs(e_hs - 5e5)))
        cur["lead_at_5bar_min_ms"] = min(cur["lead_at_5bar_min_ms"], lead(row, j5) * 1e3)
    res["ext_classes"] = {" ".join(k): v for k, v in sorted(classes.items())}
    # worst early openings at e_h 5 bar and their cost at the next reads
    j5 = int(np.argmin(np.abs(e_hs - 5e5)))
    early = [row for row in rows if lead(row, j5) < 0 and row[8] != big]
    res["ext_early_at_5bar_count"] = len(early)
    res["ext_cases"] = len(rows)
    costs = []
    for row in sorted(early, key=lambda r: lead(r, j5))[:400]:
        leg, u_prev, u_ext, h, r, a, es, dh, kp, kb = row
        a_h, a_ann = A_H[leg], A_ANN[leg]
        k_h = BETA * a_h / (L0 + E_OP[leg])
        k_r = BETA * a_ann / (L0 + S_MAX - E_OP[leg])
        c_pl = RodPressureFlowLaw.rod_compliance_m3_Pa(a_ann, k_h, k_r)
        tk_h = 0.69e9 * a_h / (0.08 + 0.395)
        tk_r = 0.69e9 * a_ann / (0.10 + S_MAX - 0.395)
        c_tr = 1.40 * RodPressureFlowLaw.rod_compliance_m3_Pa(a_ann, tk_h, tk_r)
        force = h * a_h - r * a_ann
        p_star = max(5e5, -force / a_ann)
        means = valve_means(u_prev, u_ext)
        p_tr, p_hat = r, max(r + dh, P_FLOOR)
        gaps = []
        for k in range(300):
            if k >= kp:
                for _ in range(2):
                    p_tr = flow_limited_rod_pressure(p_tr, p_star, means[k], 5e-4, 0.05, c_pl,
                                                     a_h, a_ann, False)
            if k > kb[j5]:
                p_hat = flow_limited_rod_pressure(p_hat, 5e5, KAPPA * max(means[k], 0.0), DT,
                                                  0.05, c_tr, a_h, a_ann, False)
            if (k + 1) % 100 == 0:
                gaps.append((p_hat + 0.5e5 - p_tr) / BAR)
        costs.append({"leg": leg, "u_prev_mm_s": u_prev * 1e3, "u_ext_mm_s": u_ext * 1e3,
                      "p_h_bar": h / BAR, "p_r_bar": r / BAR, "amp_bar": a / BAR,
                      "err_bar": es / BAR, "dhat_bar": dh / BAR,
                      "lead_ms": lead(row, j5) * 1e3, "gap_reads_bar": gaps})
    # gap includes the start deficit dhat (-1.91 bar rows start below p_tr); the early-opening
    # cost itself (early minus ideal) is in hr03_gate_consequence.json
    res["ext_early_min_gap_incl_start_deficit_bar"] = (
        min(min(c["gap_reads_bar"]) for c in costs) if costs else None)
    res["ext_early_cost_worst"] = sorted(costs, key=lambda c: min(c["gap_reads_bar"]))[:8]
    # ---- retract: static need monotonicity and spec vs alternative inputs
    stat = {}
    for leg in ("front", "rear"):
        a_h, a_ann = A_H[leg], A_ANN[leg]
        ph, pr, bd, ss, vd = (a.ravel() for a in np.meshgrid(
            np.array([5, 10, 20, 35, 50, 77, 100, 150, 200]) * BAR,
            np.array([P_FLOOR / BAR, 0, 2, 5, 13, 30, 54]) * BAR,
            np.array([0, 2, 4, 8, 12, 16]) * 1e3, np.array([0.05, 0.395, 0.65]),
            np.array([0.0, 0.2e-3]), indexing="ij"))
        need_pl, _ = need_vec(ph, pr, bd, ss, vd, a_h, a_ann, BETA, L0, L0)
        for name, band_ub, pr_ub in (("spec_Fband8_prT", 8e3, P_T), ("Fband0_prT", 0.0, P_T),
                                     ("Fband0_prfloor", 0.0, P_FLOOR)):
            need_ub, _ = need_vec(ph + 5e5, np.full_like(pr, pr_ub), np.full_like(bd, band_ub),
                                  ss, 0.0, a_h, a_ann, 0.69e9, 0.10, 0.08)
            short = need_ub < need_pl - 1e-12
            excl = short & ~((pr < P_T) | (vd > 0))
            stat[f"{leg}:{name}"] = {
                "cases": int(short.size), "need_ub_below_plant": int(short.sum()),
                "below_with_p_r>=p_T_and_void0": int(excl.sum()),
                "worst_ratio_all": float((need_ub / need_pl).min()),
                "worst_ratio_p_r>=p_T_void0": float(np.where(
                    (pr >= P_T) & (vd == 0), need_ub / need_pl, np.inf).min()),
                "worst_band_kN_if_below": (float(bd[excl][np.argmin((need_ub / need_pl)[excl])]
                                                 / 1e3) if excl.any() else None)}
        # monotonicity of the plant need in band (should decrease) and p_r (decrease)
        d_band = need_vec(ph, pr, bd + 100.0, ss, vd, a_h, a_ann, BETA, L0, L0)[0] - need_pl
        d_pr = need_vec(ph, pr + 100.0, bd, ss, vd, a_h, a_ann, BETA, L0, L0)[0] - need_pl
        d_ph = need_vec(ph + 100.0, pr, bd, ss, vd, a_h, a_ann, BETA, L0, L0)[0] - need_pl
        d_s = need_vec(ph, pr, bd, ss + 1e-3, vd, a_h, a_ann, BETA, L0, L0)[0] - need_pl
        stat[f"{leg}:monotone"] = {"dneed_dband_max": float(d_band.max()),
                                   "dneed_dpr_max": float(d_pr.max()),
                                   "dneed_dph_min": float(d_ph.min()),
                                   "dneed_ds_max": float(d_s.max())}
        # volume of the 8 kN choice at the R12-like point (p_h 35 bar, p_r 54 bar) and a loaded one
        for tag, h, r in (("R12", 35.2e5, 53.9e5), ("loaded", 77e5, 2e5), ("heavy", 150e5, 5e5)):
            vals = {}
            for b in (0.0, 8e3, 16e3):
                n_, _ = need_vec(np.array([h]), np.array([r]), np.array([b]),
                                 np.array([0.395]), 0.0, a_h, a_ann, BETA, L0, L0)
                vals[f"band{b / 1e3:g}kN_need_mm"] = float(n_[0] * 1e3)
            stat[f"{leg}:point_{tag}"] = vals
    res["ret_static"] = stat
    # ---- retract timing (plant need from its true inputs each chunk, bound need_ub constant)
    timing = {}
    for leg in ("front", "rear"):
        a_h, a_ann = A_H[leg], A_ANN[leg]
        ph, pr, bd, vd, am = (a.ravel() for a in np.meshgrid(
            np.array([5, 20, 50, 77, 100, 150, 200]) * BAR,
            np.array([2, 5, 13, 30, 54]) * BAR, np.array([0, 4, 8, 16]) * 1e3,
            np.array([0.0]), np.array([0.0, 3.0]) * BAR, indexing="ij"))
        for u_prev, u_ret, es in itertools.product((0.0, -0.5 * U_HOLD),
                                                   (1.01 * U_HOLD, 0.5e-3, 1e-3, 4.71e-3, V_MAX),
                                                   (-E_READ, 0.0)):
            means = valve_means(u_prev, -u_ret)
            t = (np.arange(N) + 1) * DT
            bump = np.sin(np.pi * ((t % T_PER) / T_PER))

            def plant_need(k, ph=ph, pr=pr, bd=bd, vd=vd, am=am, bump=bump, a_h=a_h,
                           a_ann=a_ann, leg=leg):
                h = ph + am * bump[k]
                r = np.maximum(pr - ratio(leg) * am * bump[k], P_FLOOR)
                return need_vec(h, r, bd, 0.395, vd, a_h, a_ann, BETA, L0, L0)
            x0 = np.zeros_like(ph)
            if u_prev < -EPS:                 # pre-phase fill of the plant (1 s steady micro)
                pre = np.full(1000, u_prev)
                x_pre = x0.copy()
                k_n = F_N * k_land(leg)
                for _ in range(1000):
                    need, rise = plant_need(0)
                    g = max(1 - abs(u_prev) / (C_V * V_MAX), 0.0)
                    level = np.minimum(x_pre / np.where(need > 0, need, 1.0), 1.0)
                    x_pre = np.maximum(x_pre + (abs(u_prev) - k_n * g * np.sqrt(rise * level)
                                                / a_ann) * DT, 0.0)
                x0 = x_pre
                del pre
            k_pl = ret_open(leg, plant_need, means, 1.0, x0)
            for name, band_ub, pr_ub in (("spec_Fband8", 8e3, P_T), ("Fband0", 0.0, P_T)):
                need_ub, rise_ub = need_vec(ph + es + 5e5, np.full_like(pr, pr_ub),
                                            np.full_like(bd, band_ub), 0.395, 0.0, a_h, a_ann,
                                            0.69e9, 0.10, 0.08)
                k_b = ret_open(leg, lambda k, n=need_ub, ru=rise_ub: (n, ru), means, KAPPA,
                               np.zeros_like(ph))
                both = k_pl < np.iinfo(np.int64).max
                lead_ms = np.where(both & (k_b < np.iinfo(np.int64).max),
                                   (k_b + 1 - k_pl) * 1e3 * DT,
                                   np.where(both, np.inf, np.where(
                                       k_b < np.iinfo(np.int64).max, -np.inf, np.inf)))
                key = f"{leg}:{name}"
                cur = timing.setdefault(key, {"cases": 0, "early": 0, "min_lead_ms": math.inf,
                                              "early_band_kN": set()})
                cur["cases"] += int(lead_ms.size)
                bad = lead_ms < 0
                cur["early"] += int(bad.sum())
                cur["min_lead_ms"] = min(cur["min_lead_ms"], float(lead_ms.min()))
                cur["early_band_kN"].update((bd[bad] / 1e3).tolist())
    for v in timing.values():
        v["early_band_kN"] = sorted(v["early_band_kN"])
    res["ret_timing"] = timing
    # ---- intra-period head excursion in the stored R12 RR traces (5e-4 s)
    exc = {}
    for name in ("VB", "LS2", "LS3"):
        d = np.load(TRACE / f"trace_{name}.npz")
        cols = [str(c) for c in d["cols"]]
        a = d["data"]
        col = {c: a[:, cols.index(c)] for c in cols}
        a_ann, a_h = A_ANN["rear"], A_H["rear"]
        locked = col["locked"] > 0.5
        p_tr = np.where(locked, col["p_r0"] - col["Gr"] / a_ann, col["p_lag"])
        p_h = (col["net_N"] + p_tr * a_ann) / a_h
        t = col["t"]
        worst = 0.0
        per = []
        for t0 in np.arange(48.3, 49.35, 0.1):
            m = (t >= t0 - 1e-9) & (t <= t0 + 0.1 + 1e-9)
            if m.sum() < 150:
                continue
            ends = max(p_h[m][0], p_h[m][-1])
            over = p_h[m].max() - ends
            per.append(round(float(over / BAR), 3))
            worst = max(worst, over)
        exc[name] = {"max_bar": float(worst / BAR), "per_period_bar": per}
    res["intra_period_head_excess_R12_RR"] = exc
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    brief = {k: v for k, v in res.items() if k not in ("ext_early_cost_worst",)}
    print(json.dumps(brief, indent=1, default=float))
    print(json.dumps(res["ext_early_cost_worst"][:4], indent=1, default=float))


if __name__ == "__main__":
    main()
