"""Seal friction on the single-leg POC circuit: limit cycle, check opening time, hand calculation. Current REXOME35.

Rear friction = front x 0.833 (project rule). Output poc_friction.json.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import poc_numpy as pn
import poc_reversal as pr
from common import SCRATCH, dump, pin_two_cores
from hopsan_run import run_hopsan
from params import LEGS, load_params, static_loads

LOG = ["Rod#P2#Velocity", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure", "POCB#P1#Pressure", "Kg#P1#Force", "POCA#x#Value", "POCB#x#Value"]
FS_FRONT = (0.0, 2.0e3, 4.0e3, 8.0e3)
REAR_SCALE = 0.833
ALPHAS = (0.05, 0.1, 0.25, 1.0)


def time_to_stroke(ds: float, v: float, tau: float = pr.TAU_V) -> float:
    """Time for the lagged command v(1 - exp(-t/tau)) to integrate to ds."""
    lo, hi = 0.0, ds / v + 2.0 * tau + 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if v * (mid - tau * (1.0 - math.exp(-mid / tau))) < ds:
            lo = mid
        else:
            hi = mid
    return hi


def hand_opening(p, i: int, fs: float, beta_h: float = pr.BETA_HOSE) -> dict:
    """Volumes to the check opening with the piston free to creep on the compressible head (slow, load constant)."""
    a_h, a_r = float(p.A_h[i]), float(p.A_r[i])
    s0 = float(p.s0[i])
    f0 = float(static_loads(p)[i])
    p_r0 = pr.P_R0
    p_h0 = (f0 + a_r * p_r0) / a_h
    p_line0 = pr.P_T
    v_r = a_r * (p.L0r + p.stroke - s0)
    v_h = a_h * (p.L0h + s0)
    # retract: p_b rises with the rod chamber; head pressure rises by (A_r dp - fs)+ / A_h while the rod moves in
    phi = a_h / a_r
    psi = pr.PSI
    # open when p_a + psi p_b - p_h - p_cr = 0, p_a = p_T
    def gap(dp: float) -> float:
        dph = max(a_r * dp - fs, 0.0) / a_h
        return pr.P_T + psi * (p_r0 + dp) - (p_h0 + dph) - pr.P_CRACK
    lo, hi = 0.0, 400e5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if gap(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    dp = hi
    dph = max(a_r * dp - fs, 0.0) / a_h
    creep = v_h * dph / (p.beta * a_h)
    v_line = pr.V_LINE * (p_r0 + dp - p_line0) / beta_h
    v_rod = v_r * dp / p.beta
    v_creep = a_r * creep
    # stroke 0.2 mm is reached before the opening when the creep is larger than that
    out = {"p_h0_bar_g": p_h0 / 1e5, "p_open_line_B_bar_g": (p_r0 + dp) / 1e5, "dp_h_at_open_bar": dph / 1e5,
           "phi": phi, "piston_creep_before_open_mm": creep * 1e3,
           "V_line_cm3": v_line * 1e6, "V_rod_cm3": v_rod * 1e6, "V_creep_cm3": v_creep * 1e6,
           "retract_open_V_cm3": (v_line + v_rod + v_creep) * 1e6,
           "retract_open_stroke_mm": (v_line + v_rod + v_creep) / a_r * 1e3}
    # extend: line A to p_h + cracking; with friction the head and the line rise by fs / A_h more before motion
    v_ext = pr.V_LINE * (p_h0 + pr.P_CRACK - pr.P_T) / beta_h
    dph_f = fs / a_h
    v_ext_f = (pr.V_LINE / beta_h + v_h / p.beta) * dph_f
    out.update({"extend_open_V_cm3": v_ext * 1e6, "extend_friction_V_cm3": v_ext_f * 1e6,
                "extend_dead_stroke_mm": (v_ext + v_ext_f) / a_h * 1e3,
                "head_dump_stroke_mm": pr.V_LINE * (p_h0 + dph - pr.P_T) / beta_h / a_h * 1e3})
    return out


def analyse(df, grid, u, seq, a_h, a_r):
    t = df.index.to_numpy()
    v = df["Rod#P2#Velocity"].to_numpy()
    x_a = df["POCA#x#Value"].to_numpy()
    p_h = df["POCA#P2#Pressure"].to_numpy() / 1e5 - 1.0
    p_r = df["POCB#P2#Pressure"].to_numpy() / 1e5 - 1.0
    line_b = df["POCB#P1#Pressure"].to_numpy() / 1e5 - 1.0
    force = df["Kg#P1#Force"].to_numpy()
    rows = {}
    for k, (name, on, off, sign) in enumerate(seq):
        end = seq[k + 1][1] if k + 1 < len(seq) else t[-1]
        win = (t >= on) & (t < end)
        cmd = (t > on + 0.6 * (off - on)) & (t < off)
        opened = np.flatnonzero(win & (x_a > 0.5)) if sign < 0 else np.array([], dtype=int)
        entry = {
            "t_poc_a_open_after_cmd_s": float(t[opened[0]] - on) if opened.size else float("nan"),
            "line_b_at_open_bar_g": float(line_b[opened[0]]) if opened.size else float("nan"),
            "p_h_at_open_bar_g": float(p_h[opened[0]]) if opened.size else float("nan"),
            "cmd_window_v_mean_mm_s": float(v[cmd].mean() * 1e3), "cmd_window_v_std_mm_s": float(v[cmd].std() * 1e3),
            "cmd_window_force_ptp_kN": float(np.ptp(force[cmd]) / 1e3),
            "cmd_window_p_r_min": float(p_r[cmd].min()), "cmd_window_p_r_max": float(p_r[cmd].max()),
            "cmd_window_poc_toggles_per_s": float(np.sum(np.abs(np.diff((x_a[cmd] > 0.5).astype(int)))) / max(off - on, 1e-3) / 0.4),
        }
        y = v[cmd] - v[cmd].mean()
        if len(y) > 16 and y.std() > 1e-6:
            spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
            entry["cmd_window_v_dom_Hz"] = float(np.fft.rfftfreq(len(y), t[1] - t[0])[int(np.argmax(spec[1:])) + 1])
        else:
            entry["cmd_window_v_dom_Hz"] = 0.0
        rows[name] = entry
    return rows


def main() -> None:
    pin_two_cores()
    p = load_params()
    out = {"meta": {"dimensions": "current REXOME35 per-leg YAML", "pressure": "bar gauge", "ts_s": pr.TS, "friction": "Coulomb f_s = f_k on the rod, front value; rear = front x 0.833",
                    "assumptions": {"V_line_m3": pr.V_LINE, "beta_hose_Pa": pr.BETA_HOSE, "beta_Pa": p.beta, "psi": pr.PSI, "p_crack_bar": pr.P_CRACK / 1e5, "tau_v_s": pr.TAU_V, "p_T_bar_g": pr.P_T / 1e5, "p_r0_bar_g": pr.P_R0 / 1e5, "neutral": "A,B->T", "stroke_step_mm": pr.STROKE_STEP * 1e3}},
           "hand": {}, "hopsan": {}, "numpy": {}}
    for i in (0, 2):
        leg = LEGS[i]
        scale = 1.0 if i < 2 else REAR_SCALE
        for fs0 in FS_FRONT:
            fs = fs0 * scale
            h = hand_opening(p, i, fs)
            h["retract_open_t_s"] = {f"{a:g}": time_to_stroke(h["retract_open_stroke_mm"] * 1e-3, a * p.v_max) for a in ALPHAS}
            h["extend_move_t_s"] = {f"{a:g}": time_to_stroke(h["extend_dead_stroke_mm"] * 1e-3, a * p.v_max) for a in ALPHAS}
            out["hand"][f"{leg}_Fs{fs0 / 1e3:g}"] = h
            pr.LEG_INDEX = i
            pr.ROD_FS = fs
            pr.C_LOCK = 34403.5 if i < 2 else 30348.5
            for alpha in ALPHAS:
                case = f"{leg}_Fs{fs0 / 1e3:g}_a{alpha:g}"
                folder = SCRATCH / "pocf" / case
                model, grid, u, seq, f0, a_h, a_r = pr.build(case, folder, p, alpha, True, pr.BETA_HOSE, pr.P_R0)
                df, _un, info = run_hopsan(model, folder, sim=(0.0, pr.TS, float(grid[-1])), log_only=LOG,
                                           num_log_samples=int(grid[-1] / 2e-4) + 1, timeout=250.0)
                rows = pr.metrics(df, grid, u, seq, f0)
                extra = analyse(df, grid, u, seq, a_h, a_r)
                merged = {}
                for r in rows:
                    merged[r["motion"]] = {k: r[k] for k in ("t_move_after_cmd_s", "t_move_ideal_s", "stroke_lag_at_hold_end_mm", "peak_abs_dF_kN", "p_r_cmd_end_bar_g", "p_h_cmd_end_bar_g")} | extra[r["motion"]]
                out["hopsan"][case] = {"wall_s": info["wall_s"], "F_s_N": fs, "alpha": alpha, "motions": merged}
                m = merged["ret_after_ext"]
                print(case, "wall", info["wall_s"], "open", round(m["t_poc_a_open_after_cmd_s"], 3), "move", round(m["t_move_after_cmd_s"], 3),
                      "pB", round(m["line_b_at_open_bar_g"], 1), "| v", round(m["cmd_window_v_mean_mm_s"], 2), "+-", round(m["cmd_window_v_std_mm_s"], 2), "ptpF", round(m["cmd_window_force_ptp_kN"], 1),
                      "f", round(m["cmd_window_v_dom_Hz"], 1), "| lag", round(m["stroke_lag_at_hold_end_mm"], 3), "ext move", round(merged["ext_after_ret"]["t_move_after_cmd_s"], 3), flush=True)
            print("  hand", leg, fs0, "open t", {k: round(v, 3) for k, v in h["retract_open_t_s"].items()}, "ext t", {k: round(v, 3) for k, v in h["extend_move_t_s"].items()}, "p_open", round(h["p_open_line_B_bar_g"], 2), flush=True)
    pr.LEG_INDEX, pr.ROD_FS, pr.C_LOCK = 0, 0.0, 34403.5
    pr_lock = 34403.5
    pn.C_LOCK = pr_lock
    for fs0, alpha, tau, band in ((4.0e3, 0.05, 0.02, 10e5), (4.0e3, 0.25, 0.02, 10e5), (8.0e3, 0.25, 0.02, 10e5), (0.0, 0.05, 0.02, 10e5)):
        res, grid, u, seq, f0 = pn.run_two_chamber(p, alpha, tau, band, True, fs=fs0)
        m = pn.metrics_tc(res, grid, u, seq, f0)
        t, xa = res[:, 0], res[:, 9]
        on = seq[0][1]
        opened = np.flatnonzero((t >= on) & (t < seq[1][1]) & (xa > 0.5))
        key = f"FL_Fs{fs0 / 1e3:g}_a{alpha:g}_tau{tau:g}_band{band / 1e5:g}"
        out["numpy"][key] = {"motions": m, "t_poc_a_open_after_cmd_s": float(t[opened[0]] - on) if opened.size else float("nan")}
        r = m[0]
        print("numpy", key, "open", out["numpy"][key]["t_poc_a_open_after_cmd_s"], "move", r["t_move_after_cmd_s"], "rip", round(r["v_ripple_mm_s_in_cmd"], 3), "dF", round(r["peak_abs_dF_kN"], 2), "lag", round(r["stroke_lag_at_hold_end_mm"], 3), flush=True)
    dump("poc_friction.json", out)


if __name__ == "__main__":
    main()
