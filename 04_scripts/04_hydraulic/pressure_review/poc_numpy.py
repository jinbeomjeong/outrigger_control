"""Second path for poc_reversal.py: same leg in plain Python, with a progressive (damped) pilot check.

Also runs the plant law of L1/L2b (L2bRodSide + SpeedReference, no delay) on the same command, one mass.
Gauge pressures [Pa]. Current REXOME35 FL dimensions. Output: poc_numpy.json.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from common import P_ATM, dump, lag_series, pin_two_cores
from params import load_params, static_loads
from poc_reversal import BETA_HOSE, C_LOCK, HOLD, NEUTRAL_OPEN_FRACTION, P_CRACK, P_R0, P_T, POC_KS, PSI, STROKE_STEP, V_LINE, motions

from outrigger_sim.actuation import SpeedReference
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide

DT = 1.0e-5
P_FLOOR = -0.9e5
EPS_DP = 1.0e2


def sqrt_flow(k: float, dp: float) -> float:
    return k * dp / math.sqrt(abs(dp) + EPS_DP)


def run_two_chamber(p, alpha: float, tau_poc: float, band: float, neutral_open: bool, volume_scale: float = 1.0, fs: float = 0.0, leg: int = 0):
    i = leg
    a_h, a_r = float(p.A_h[i]), float(p.A_r[i])
    f0 = float(static_loads(p)[i])
    m_b = f0 / 9.80665
    m_r = float(p.m_rod[i])
    k_g = float(p.k_st[i])
    s0 = float(p.s0[i])
    grid, cmd, seq = motions(alpha, p.v_max)
    u_grid = lag_series(grid, cmd, 0.1)
    k_land = a_h * p.v_max / math.sqrt(p.dp_comp)
    k_vent = (NEUTRAL_OPEN_FRACTION * k_land) if neutral_open else 0.0
    beta, beta_h = p.beta, BETA_HOSE
    v_line = V_LINE * volume_scale
    # state
    p_r = P_R0
    p_h = (f0 + a_r * p_r) / a_h
    p_a = p_b = P_T
    s, v = s0, 0.0
    # spring zero so that the initial spring force is f0: x_b = body rise
    x_b, v_b = 0.0, 0.0
    x_a = x_b_poc = 0.0
    n = int(round(grid[-1] / DT))
    log_every = 50
    rows = []
    dt_tau = DT / tau_poc if tau_poc > 0 else 1.0
    raw_h, raw_r, raw_a, raw_b = p_h, p_r, p_a, p_b  # oil mass kept below the floor
    for kstep in range(n + 1):
        t = kstep * DT
        p_h, p_r, p_a, p_b = max(raw_h, P_FLOOR), max(raw_r, P_FLOOR), max(raw_a, P_FLOOR), max(raw_b, P_FLOOR)
        j = min(int(t * 1000.0), len(grid) - 2)
        u = u_grid[j] + (u_grid[j + 1] - u_grid[j]) * (t * 1000.0 - j)
        frac = abs(u) / p.v_max
        vent = k_vent * max(1.0 - frac / 0.02, 0.0)
        q_a_src = a_h * max(u, 0.0)
        q_b_src = a_r * max(-u, 0.0)
        k_oa = vent + (k_land * frac if u < 0 else 0.0)
        k_ob = vent + (k_land * frac if u > 0 else 0.0)
        # pilot checks: forward opening by pressure, reverse opening by the pilot of the other line
        tgt_a = min(max((p_a + PSI * p_b - p_h - P_CRACK) / band, 0.0), 1.0)
        tgt_b = min(max((p_b + PSI * p_a - p_r - P_CRACK) / band, 0.0), 1.0)
        x_a += (tgt_a - x_a) * dt_tau
        x_b_poc += (tgt_b - x_b_poc) * dt_tau
        q_poc_a = sqrt_flow(POC_KS * x_a, p_a - p_h)
        q_poc_b = sqrt_flow(POC_KS * x_b_poc, p_b - p_r)
        q_oa = sqrt_flow(k_oa, p_a - P_T)
        q_ob = sqrt_flow(k_ob, p_b - P_T)
        v_h = a_h * (p.L0h + s)
        v_r = a_r * (p.L0r + p.stroke - s)
        dp_h = beta / v_h * (q_poc_a - a_h * v)
        dp_r = beta / v_r * (q_poc_b + a_r * v)
        dp_a = beta_h / v_line * (q_a_src - q_oa - q_poc_a)
        dp_b = beta_h / v_line * (q_b_src - q_ob - q_poc_b)
        spring = f0 + k_g * ((s - s0) - x_b)
        f_cyl = a_h * p_h - a_r * p_r - C_LOCK * v
        net = f_cyl - spring
        a_b = (spring - f0) / m_b
        if kstep % log_every == 0:
            rows.append((t, s, v, p_h, p_r, p_a, p_b, spring, u, x_a))
        # Coulomb seal friction: stuck while the net force stays inside the limit, stops at a zero crossing
        if v == 0.0 and abs(net) <= fs:
            pass
        else:
            drive = v if v != 0.0 else net
            v_new = v + (net - math.copysign(fs, drive)) / m_r * DT
            v = 0.0 if (v != 0.0 and v_new * v < 0.0) else v_new
        s += v * DT
        v_b += a_b * DT
        x_b += v_b * DT
        raw_h += dp_h * DT
        raw_r += dp_r * DT
        raw_a += dp_a * DT
        raw_b += dp_b * DT
    return np.array(rows), grid, u_grid, seq, f0


def run_law(p, alpha: float):
    i = 0
    a_h, a_r = float(p.A_h[i]), float(p.A_r[i])
    f0 = float(static_loads(p)[i])
    m_b = f0 / 9.80665
    k_g = float(p.k_st[i])
    s0 = float(p.s0[i])
    grid, cmd, seq = motions(alpha, p.v_max)
    law = L2bRodSide(head_area_m2=[a_h], annulus_area_m2=[a_r], k_out_N_m=[k_g], bulk_modulus_Pa=p.beta,
                     head_dead_length_m=p.L0h, rod_dead_length_m=[p.L0r], stroke_m=p.stroke,
                     p_r0_after_extend_Pa=[P_R0], p_r0_after_retract_Pa=[3.4818e6], p_floor_abs_Pa=1.0e4,
                     release_tau_s=0.05, lock_eps_m_s=1.0e-6, mechanics="one_sided_parallel", armed=True)
    dt = 1.0e-4
    k2 = law.k2_N_m(0, s0)
    ref = SpeedReference([s0 + f0 / k2], [[0.0, p.stroke]], max_speed_m_s=p.v_max, ramp_s=0.1)
    ref.configure_valve(tau_s=0.1)
    c_lock, c_move = 34403.5, 100206.0
    x, vx = s0, 0.0  # link coordinate s; body moves with it (massless rod)
    force = f0
    u_acting = np.zeros(1)
    rows = []
    n = int(round(grid[-1] / dt))
    for k in range(n + 1):
        t = k * dt
        ref.set_command([float(np.interp(t, grid, cmd))])
        s_ref_now = ref.s_ref_m
        ref.advance(dt, cylinder_force_N=[force], t_s=t)
        u = ref.u_applied_m_s
        spring = law.spring_force_N(t, dt, u_acting, s_ref_now, s_ref_now - x, [force])
        c = c_lock if abs(u[0]) <= 1e-6 else c_move
        force = float(spring[0] + c * (u[0] - vx))
        p_r_now = float(law.rod_pressure_Pa[0])
        p_h_now = (force + p_r_now * a_r) / a_h
        rows.append((t, x, vx, p_h_now, p_r_now, float(s_ref_now[0]), force))
        vx += (force - f0) / m_b * dt
        x += vx * dt
        u_acting = u
    return np.array(rows), seq, f0


def metrics_tc(rows, grid, u, seq, f0):
    t, s, v, p_h, p_r, spring = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3], rows[:, 4], rows[:, 7]
    ideal = np.interp(t, grid, np.concatenate([[0.0], np.cumsum(0.5 * (u[1:] + u[:-1]) * np.diff(grid))]))
    out = []
    for k, (name, on, off, sign) in enumerate(seq):
        end = seq[k + 1][1] if k + 1 < len(seq) else t[-1]
        win = (t >= on) & (t < end)
        s_rel = sign * (s - np.interp(on, t, s))
        ideal_rel = sign * (ideal - np.interp(on, t, ideal))
        moved = np.flatnonzero(win & (s_rel > 2e-4))
        ideal_idx = np.flatnonzero(win & (ideal_rel > 2e-4))
        offwin = (t >= off - 0.02) & (t < off)
        endwin = (t >= end - 0.05) & (t < end)
        pre = (t >= on - 0.05) & (t < on)
        lag = ideal_rel - s_rel
        move_win = (t > on + 0.6 * (off - on)) & (t < off)
        out.append({
            "motion": name,
            "t_move_after_cmd_s": float(t[moved[0]] - on) if moved.size else float("nan"),
            "t_move_ideal_s": float(t[ideal_idx[0]] - on),
            "stroke_lag_at_hold_end_mm": float(np.mean(lag[endwin]) * 1e3),
            "peak_abs_dF_kN": float(np.max(np.abs(spring[win] - np.mean(spring[pre]))) / 1e3),
            "p_r_cmd_end_bar_g": float(np.mean(p_r[offwin]) / 1e5),
            "p_h_cmd_end_bar_g": float(np.mean(p_h[offwin]) / 1e5),
            "p_r_max_bar_g": float(np.max(p_r[win]) / 1e5),
            "v_ripple_mm_s_in_cmd": float(np.std(v[move_win]) * 1e3),
        })
    return out


def metrics_law(rows, seq):
    t, x, p_h, p_r, s_ref, force = rows[:, 0], rows[:, 1], rows[:, 3], rows[:, 4], rows[:, 5], rows[:, 6]
    out = []
    for k, (name, on, off, sign) in enumerate(seq):
        end = seq[k + 1][1] if k + 1 < len(seq) else t[-1]
        win = (t >= on) & (t < end)
        pre = (t >= on - 0.05) & (t < on)
        offwin = (t >= off - 0.02) & (t < off)
        endwin = (t >= end - 0.05) & (t < end)
        out.append({
            "motion": name,
            "peak_abs_dF_kN": float(np.max(np.abs(force[win] - np.mean(force[pre]))) / 1e3),
            "lag_sref_minus_link_hold_end_mm": float(np.mean(sign * ((s_ref[endwin] - s_ref[pre].mean()) - (x[endwin] - x[pre].mean()))) * 1e3),
            "p_r_pre_bar_g": float(np.mean(p_r[pre]) / 1e5),
            "p_r_cmd_end_bar_g": float(np.mean(p_r[offwin]) / 1e5),
            "p_h_cmd_end_bar_g": float(np.mean(p_h[offwin]) / 1e5),
            "p_r_hold_end_bar_g": float(np.mean(p_r[endwin]) / 1e5),
        })
    return out


def main() -> None:
    pin_two_cores()
    p = load_params()
    res = {"meta": {"dimensions": "current REXOME35, FL", "pressure": "bar gauge", "dt_s": DT,
                    "poc": "progressive: x -> clip((p_line + psi p_pilot - p_chamber - p_crack)/band, 0, 1), 1st order tau",
                    "assumption": "tau_poc and band are ASSUMPTION (no maker data, Q-M2); same volumes as poc_reversal.py",
                    "law": "L2bRodSide + SpeedReference (valve lag 0.1 s), massless rod, FL mass = F0/g"}, "two_chamber": {}, "law": {}}
    for alpha in (0.05, 0.1, 0.25, 1.0):
        rows, seq, _f0 = run_law(p, alpha)
        res["law"][f"a{alpha:g}"] = metrics_law(rows, seq)
        print("law", alpha, [(r["motion"], round(r["peak_abs_dF_kN"], 2), round(r["p_r_cmd_end_bar_g"], 1)) for r in res["law"][f"a{alpha:g}"]])
    for alpha, tau, band in ((0.1, 0.02, 10e5), (0.25, 0.02, 10e5), (0.05, 0.02, 10e5), (1.0, 0.02, 10e5), (0.1, 0.005, 2e5)):
        t0 = time.perf_counter()
        rows, grid, u, seq, f0 = run_two_chamber(p, alpha, tau, band, True)
        key = f"a{alpha:g}_tau{tau:g}_band{band / 1e5:g}"
        res["two_chamber"][key] = {"rows": metrics_tc(rows, grid, u, seq, f0), "wall_s": time.perf_counter() - t0}
        print(key, round(time.perf_counter() - t0, 1), "s")
        for r in res["two_chamber"][key]["rows"]:
            print("  ", r["motion"], round(r["t_move_after_cmd_s"], 3), round(r["t_move_ideal_s"], 3), "lag", round(r["stroke_lag_at_hold_end_mm"], 3),
                  "dF", round(r["peak_abs_dF_kN"], 2), "pr", round(r["p_r_cmd_end_bar_g"], 1), "rip", round(r["v_ripple_mm_s_in_cmd"], 3))
    dump("poc_numpy.json", res)


if __name__ == "__main__":
    main()
