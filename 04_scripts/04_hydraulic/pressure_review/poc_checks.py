"""Hand calculation of the start dead volume, retract limit cycle with more damping, time-step check of the POC model."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import poc_numpy as pn
import poc_reversal as pr
from common import SCRATCH, dump, pin_two_cores
from hopsan_run import run_hopsan
from params import LEGS, load_params, static_loads

LOG = ["Rod#P2#Velocity", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure", "POCB#P1#Pressure", "Kg#P1#Force"]


def hand(p):
    f0 = static_loads(p)
    rows = {}
    for beta_h in (0.5e9, 1.0e9):
        for i, leg in enumerate(LEGS):
            a_h, a_r = float(p.A_h[i]), float(p.A_r[i])
            p_r0 = 2.0e5
            p_h = (f0[i] + a_r * p_r0) / a_h
            # extend: line A from tank to the load pressure (forward check needs p_h + crack)
            dv_ext = pr.V_LINE * (p_h + pr.P_CRACK - pr.P_T) / beta_h
            ds_ext = dv_ext / a_h
            # retract: line B and the rod chamber to the opening pressure of POC-A (Hopsan rule, gauge form)
            p_open = (p_h - pr.P_T + pr.P_CRACK) / pr.PSI
            v_r = a_r * (p.L0r + p.stroke - float(p.s0[i]))
            dv_ret = pr.V_LINE * (p_open - pr.P_T) / beta_h + v_r * max(p_open - p_r0, 0.0) / p.beta
            ds_ret = dv_ret / a_r
            # POC-A opens: the head chamber charges line A from tank to p_h, the piston gives that volume
            dump_v = pr.V_LINE * (p_h - pr.P_T) / beta_h
            ds_dump = dump_v / a_h
            rows[f"{leg}_beta{beta_h / 1e9:g}"] = {
                "p_h_bar_g": p_h / 1e5, "p_open_line_B_bar_g": p_open / 1e5,
                "ext_dead_cm3": dv_ext * 1e6, "ext_dead_stroke_mm": ds_ext * 1e3,
                "ret_dead_cm3": dv_ret * 1e6, "ret_dead_stroke_mm": ds_ret * 1e3,
                "ret_head_dump_stroke_mm": ds_dump * 1e3, "ret_net_lag_mm": (ds_ret - ds_dump) * 1e3,
                "ext_delay_s_at_0.05_vmax": ds_ext / (0.05 * p.v_max), "ret_delay_s_at_0.05_vmax": ds_ret / (0.05 * p.v_max),
                "ext_delay_s_at_0.25_vmax": ds_ext / (0.25 * p.v_max), "ret_delay_s_at_0.25_vmax": ds_ret / (0.25 * p.v_max),
                "ext_delay_s_at_1_vmax": ds_ext / p.v_max, "ret_delay_s_at_1_vmax": ds_ret / p.v_max,
            }
    return rows


def main() -> None:
    pin_two_cores()
    p = load_params()
    out = {"meta": {"dimensions": "current REXOME35", "pressure": "gauge", "hand": "dead volume to reach the check-valve opening pressure; beta chamber 1.0 GPa, line beta below"},
           "hand": hand(p), "hopsan_variants": {}, "numpy_variants": {}}
    for key in ("FL_beta0.5", "RL_beta0.5", "FL_beta1"):
        print(key, {k: round(v, 3) for k, v in out["hand"][key].items()})
    # (a) moving-leg damper on the piston (L2b moving zeta 0.1 value) and time-step half on the nominal case
    pr.C_LOCK = 100206.0
    for alpha in (0.05, 0.25):
        case = f"Bmove_a{alpha:g}"
        folder = SCRATCH / "poc3" / case
        model, grid, u, seq, f0, _ah, _ar = pr.build(case, folder, p, alpha, True, pr.BETA_HOSE, pr.P_R0)
        df, _un, info = run_hopsan(model, folder, sim=(0.0, pr.TS, float(grid[-1])), log_only=LOG, num_log_samples=int(grid[-1] / 5e-4) + 1, timeout=250.0)
        rows = pr.metrics(df, grid, u, seq, f0)
        out["hopsan_variants"][case] = rows
        r = rows[0]
        print(case, "t_move", round(r["t_move_after_cmd_s"], 3), "lag", round(r["stroke_lag_at_hold_end_mm"], 3), "dF", round(r["peak_abs_dF_kN"], 2), "rip", round(r["v_ripple_mm_s_in_cmd"], 3))
    pr.C_LOCK = 34403.5
    for ts in (1.0e-5, 5.0e-6):
        case = f"conv_a0.1_ts{ts:g}"
        folder = SCRATCH / "poc3" / case
        pr.TS = ts
        model, grid, u, seq, f0, _ah, _ar = pr.build(case, folder, p, 0.1, True, pr.BETA_HOSE, pr.P_R0)
        df, _un, info = run_hopsan(model, folder, sim=(0.0, ts, float(grid[-1])), log_only=LOG, num_log_samples=int(grid[-1] / 5e-4) + 1, timeout=280.0)
        rows = pr.metrics(df, grid, u, seq, f0)
        out["hopsan_variants"][case] = rows
        print(case, [(round(r["t_move_after_cmd_s"], 3), round(r["stroke_lag_at_hold_end_mm"], 3), round(r["peak_abs_dF_kN"], 2)) for r in rows])
    pr.TS = 1.0e-5
    # (b) slow progressive pilot check (heavily damped pilot) in the second path
    for alpha, tau, band in ((0.05, 0.1, 30e5), (0.25, 0.1, 30e5)):
        rows, grid, u, seq, f0 = pn.run_two_chamber(p, alpha, tau, band, True)
        m = pn.metrics_tc(rows, grid, u, seq, f0)
        out["numpy_variants"][f"a{alpha:g}_tau{tau:g}_band{band / 1e5:g}"] = m
        r = m[0]
        print("numpy", alpha, tau, "t_move", round(r["t_move_after_cmd_s"], 3), "lag", round(r["stroke_lag_at_hold_end_mm"], 3), "dF", round(r["peak_abs_dF_kN"], 2), "rip", round(r["v_ripple_mm_s_in_cmd"], 3))
    dump("poc_checks.json", out)


if __name__ == "__main__":
    main()
