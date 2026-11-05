"""Single leg with line volumes and two pilot-operated checks: start delay and stroke lag on reversal.

Current REXOME35 dimensions (FL, front 130/110) from 02_params/rexome33.yaml through coupled/params.py.
Compensated valve = flow source (meter-in, compensator ideal), meter-out land = turbulent orifice.
Compared with what L1/L2b assume: s_ref = integral of the commanded speed, no delay.

usage: poc_reversal.py [--quick]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import OUT, P_ATM, SCRATCH, Hmf, dump, lag_series, pin_two_cores

import numpy as np

from hopsan_run import run_hopsan
from params import load_params, series, static_loads

TS = 1.0e-5
TAU_V = 0.1  # ASSUMPTION: spool lag, YAML/R8 nominal
PSI = 3.5  # ASSUMPTION: pilot ratio (hydraulic_circuit Q-M2)
P_CRACK = 3.0e5  # ASSUMPTION: check cracking pressure [Pa]
POC_KS = 7.0e-7  # ASSUMPTION: POC fully open 30 L/min at 5 bar
V_LINE = 2.85e-4  # ASSUMPTION: 3/8 in hose x 4 m (Q-M9)
BETA_HOSE = 0.5e9  # ASSUMPTION: rubber hose effective bulk modulus
P_T = 2.0e5  # ASSUMPTION: tank line back pressure, gauge
P_R0 = 2.0e5  # YAML p_r0_after_extend, gauge
NEUTRAL_OPEN_FRACTION = 0.05  # ASSUMPTION: A,B->T centre opening relative to the full land
STROKE_STEP = 3.0e-3  # each motion commands this displacement
HOLD = 1.0
RHO, CQ = 860.0, 0.67
C_LOCK = 34403.5  # YAML damping_lock FL [N s/m] (rev33 note in l2b_actuator)
METER_OUT_RATIO = 1.0  # A->T land area / P->A land area; poc_extra.py overrides (Q-M1, ASSUMPTION)
LEG_INDEX = 0  # 0 FL, 2 RL
ROD_FS = 0.0  # seal friction limit on the rod [N], poc_friction.py overrides


def motions(alpha: float, v_max: float):
    """Sequence: R, hold, R, hold, E, hold, E, hold. Returns (t_grid, cmd, [(name, t_on, t_off, sign)])."""
    dur = STROKE_STEP / (alpha * v_max)
    t, seq = 0.5, []
    for name, sign in (("ret_after_ext", -1), ("ret_again", -1), ("ext_after_ret", 1), ("ext_again", 1)):
        seq.append((name, t, t + dur, sign))
        t += dur + HOLD
    grid = np.arange(0.0, t + 1e-9, 1.0e-3)
    cmd = np.zeros_like(grid)
    for _, a, b, sign in seq:
        cmd[(grid >= a) & (grid < b)] = sign * alpha * v_max
    return grid, cmd, seq


def build(case: str, folder, p, alpha: float, neutral_open: bool, beta_hose: float, p_r0_g: float):
    i = LEG_INDEX
    A_h, A_r = float(p.A_h[i]), float(p.A_r[i])
    F0 = float(static_loads(p)[i])
    M = F0 / 9.80665
    F0_hop = F0 + (A_h - A_r) * P_ATM  # Hopsan cylinder force has no atmosphere term
    k_g = float(p.k_st[i])
    s0 = float(p.s0[i])
    p_r_abs = P_ATM + p_r0_g
    p_h_abs = (F0_hop + A_r * p_r_abs) / A_h
    grid, cmd, seq = motions(alpha, p.v_max)
    u = lag_series(grid, cmd, TAU_V)
    k_land = A_h * p.v_max / np.sqrt(p.dp_comp)  # full P->A land; A->T and B->T same size (ASSUMPTION)
    a_full = k_land / (CQ * np.sqrt(2.0 / RHO))
    a_neutral = NEUTRAL_OPEN_FRACTION * a_full if neutral_open else 0.0
    frac = np.abs(u) / p.v_max

    h = Hmf(case, float(grid[-1]), TS)
    h.comp("SignalTime", "Clock")
    h.comp("HydraulicTankC", "TankA", {"p": P_ATM + P_T})
    h.comp("HydraulicTankC", "TankB", {"p": P_ATM + P_T})
    p_line = P_ATM + P_T
    h.comp("HydraulicVolumeMultiPort", "LineA", {"V#Value": V_LINE, "Beta_e#Value": beta_hose, "P1#Pressure": p_line})
    h.comp("HydraulicVolumeMultiPort", "LineB", {"V#Value": V_LINE, "Beta_e#Value": beta_hose, "P1#Pressure": p_line})
    h.comp("HydraulicFlowSourceQ", "QA", {"q#Value": 0.0})
    h.comp("HydraulicFlowSourceQ", "QB", {"q#Value": 0.0})
    h.connect("QA", "P1", "LineA", "P1")
    h.connect("QB", "P1", "LineB", "P1")
    h.comp("HydraulicTurbulentOrifice", "OA", {"A#Value": a_neutral, "C_q#Value": CQ, "rho#Value": RHO})
    h.comp("HydraulicTurbulentOrifice", "OB", {"A#Value": a_neutral, "C_q#Value": CQ, "rho#Value": RHO})
    h.connect("OA", "P1", "LineA", "P1")
    h.connect("OA", "P2", "TankA", "P1")
    h.connect("OB", "P1", "LineB", "P1")
    h.connect("OB", "P2", "TankB", "P1")
    # Hopsan pilot check: open if c1 + phi c_pilot - c2 > p_f, all absolute (memory hopsan-pressure-valves-absolute)
    pf = P_CRACK + P_ATM * PSI
    for name, line, chamber_port, pilot in (("POCA", "LineA", "P1", "LineB"), ("POCB", "LineB", "P2", "LineA")):
        h.comp("HydraulicPilotControlledCheckValve", name, {"phi#Value": PSI, "p_f#Value": pf, "K_s": POC_KS})
        h.connect(name, "P1", line, "P1")
        h.connect(name, "P2", "Cyl", chamber_port)
        h.connect(name, "P_PILOT", pilot, "P1")
    h.comp("HydraulicCylinderC", "Cyl", {
        "P1#Pressure": p_h_abs, "P1#WaveVariable": p_h_abs, "P2#Pressure": p_r_abs, "P2#WaveVariable": p_r_abs,
        "P3#Position": -s0, "P3#Force": F0_hop, "P3#WaveVariable": F0_hop,
        "A_1#Value": A_h, "A_2#Value": A_r, "s_l#Value": p.stroke,
        "V_1#Value": A_h * p.L0h, "V_2#Value": A_r * p.L0r, "B_p#Value": C_LOCK, "Beta_e#Value": p.beta,
        "c_leak#Value": 0.0, "use_sl": False})
    if ROD_FS > 0.0:
        h.comp("MechanicTranslationalMassWithCoulombFriction", "Rod", {
            "m": float(p.m_rod[i]), "b#Value": 0.0, "f_s#Value": ROD_FS, "f_k#Value": ROD_FS,
            "x_min#Value": -1e3, "x_max#Value": 1e3})
    else:
        h.comp("MechanicTranslationalMass", "Rod", {"m": float(p.m_rod[i]), "B#Value": 0.0, "k#Value": 0.0,
                                                     "x_min#Value": -1e3, "x_max#Value": 1e3})
    h.comp("MechanicTranslationalSpring", "Kg", {"k#Value": k_g, "P1#Force": F0_hop, "P2#Force": F0_hop,
                                                  "P1#Position": s0, "P2#Position": 0.0,
                                                  "P1#WaveVariable": F0_hop, "P2#WaveVariable": F0_hop})
    h.comp("MechanicTranslationalMass", "Sup", {"m": M, "B#Value": 0.0, "k#Value": 0.0,
                                                 "x_min#Value": -1e3, "x_max#Value": 1e3})
    h.comp("MechanicForceTransformer", "Load", {"F#Value": F0_hop, "P1#Force": F0_hop, "P1#Position": 0.0})
    h.connect("Cyl", "P3", "Rod", "P1")
    h.connect("Rod", "P2", "Kg", "P1")
    h.connect("Kg", "P2", "Sup", "P1")
    h.connect("Sup", "P2", "Load", "P1")
    h.lookup(folder, "LUqa", grid, A_h * np.maximum(u, 0.0), "QA", "q")
    h.lookup(folder, "LUqb", grid, A_r * np.maximum(-u, 0.0), "QB", "q")
    # the centre vent closes while the spool leaves neutral (full closure at 2 % opening, ASSUMPTION)
    vent = a_neutral * np.clip(1.0 - frac / 0.02, 0.0, 1.0)
    h.lookup(folder, "LUoa", grid, vent + METER_OUT_RATIO * a_full * frac * (u < 0), "OA", "A")
    h.lookup(folder, "LUob", grid, vent + a_full * frac * (u > 0), "OB", "A")
    model = h.write(folder / f"{case}.hmf", n_log=int(grid[-1] / 5e-4) + 1)
    return model, grid, u, seq, F0, A_h, A_r


def metrics(df, grid, u, seq, F0):
    time_s = df.index.to_numpy()
    v = df["Rod#P2#Velocity"].to_numpy()  # Rod P2 is positive when extending (coupled model reads the same port)
    s = np.concatenate([[0.0], np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(time_s))])
    ideal = np.interp(time_s, grid, np.concatenate([[0.0], np.cumsum(0.5 * (u[1:] + u[:-1]) * np.diff(grid))]))
    p_h = df["POCA#P2#Pressure"].to_numpy() / 1e5 - 1.0
    p_r = df["POCB#P2#Pressure"].to_numpy() / 1e5 - 1.0
    line_a = df["POCA#P1#Pressure"].to_numpy() / 1e5 - 1.0
    line_b = df["POCB#P1#Pressure"].to_numpy() / 1e5 - 1.0
    force = df["Kg#P1#Force"].to_numpy()
    rows = []
    for k, (name, on, off, sign) in enumerate(seq):
        end = seq[k + 1][1] if k + 1 < len(seq) else time_s[-1]
        win = (time_s >= on) & (time_s < end)
        s_rel = sign * (s - np.interp(on, time_s, s))
        # sustained motion: last time the piston is still inside 0.2 mm of the start before leaving
        moved = np.flatnonzero(win & (s_rel > 2.0e-4))
        t_move = float(time_s[moved[0]] - on) if moved.size else float("nan")
        ideal_rel = sign * (ideal - np.interp(on, time_s, ideal))
        t_ideal = float(time_s[np.flatnonzero(win & (ideal_rel > 2.0e-4))[0]] - on)
        lag = ideal_rel - s_rel
        offwin = (time_s >= off - 0.02) & (time_s < off)
        endwin = (time_s >= end - 0.05) & (time_s < end)
        pre = (time_s >= on - 0.05) & (time_s < on)
        # lurch: largest motion in the commanded direction per 20 ms just after the check opens
        dt = time_s[1] - time_s[0]
        rows.append({
            "motion": name, "sign": sign,
            "t_move_after_cmd_s": t_move, "t_move_ideal_s": t_ideal, "extra_delay_s": t_move - t_ideal,
            "stroke_lag_at_cmd_end_mm": float(np.mean(lag[offwin]) * 1e3),
            "stroke_lag_at_hold_end_mm": float(np.mean(lag[endwin]) * 1e3),
            "lag_rel_step": float(np.mean(lag[endwin]) / STROKE_STEP),
            "peak_abs_dF_kN": float(np.max(np.abs(force[win] - np.mean(force[pre]))) / 1e3),
            "peak_abs_dF_vs_F0_kN": float(np.max(np.abs(force[win] - F0)) / 1e3),
            "p_h_pre_bar_g": float(np.mean(p_h[pre])), "p_r_pre_bar_g": float(np.mean(p_r[pre])),
            "p_h_min_bar_g": float(np.min(p_h[win])), "p_h_max_bar_g": float(np.max(p_h[win])),
            "p_r_max_bar_g": float(np.max(p_r[win])), "p_r_min_bar_g": float(np.min(p_r[win])),
            "p_r_cmd_end_bar_g": float(np.mean(p_r[offwin])), "p_h_cmd_end_bar_g": float(np.mean(p_h[offwin])),
            "p_r_hold_end_bar_g": float(np.mean(p_r[endwin])), "p_h_hold_end_bar_g": float(np.mean(p_h[endwin])),
            "line_a_hold_end_bar_g": float(np.mean(line_a[endwin])), "line_b_hold_end_bar_g": float(np.mean(line_b[endwin])),
            "v_ripple_mm_s_in_cmd": float(np.std(v[(time_s > on + 0.6 * (off - on)) & (time_s < off)]) * 1e3),
            "dt_log_s": float(dt),
        })
    return rows


def main() -> None:
    pin_two_cores()
    quick = "--quick" in sys.argv
    p = load_params()
    cases = []
    alphas = (0.25,) if quick else (0.05, 0.1, 0.25, 1.0)
    for alpha in alphas:
        cases.append((f"a{alpha:g}_openT", alpha, True, BETA_HOSE, P_R0))
    if not quick:
        cases.append(("a0.1_blocked", 0.1, False, BETA_HOSE, P_R0))
        cases.append(("a0.25_blocked", 0.25, False, BETA_HOSE, P_R0))
        cases.append(("a0.1_openT_hose1GPa", 0.1, True, 1.0e9, P_R0))
    results = {}
    log = ["Rod#P2#Velocity", "Rod#P2#Position", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure",
           "POCB#P1#Pressure", "Kg#P1#Force"]
    for case, alpha, neutral_open, beta_h, p_r0 in cases:
        folder = SCRATCH / "poc" / case
        model, grid, u, seq, F0, A_h, A_r = build(case, folder, p, alpha, neutral_open, beta_h, p_r0)
        t0 = time.perf_counter()
        df, _units, info = run_hopsan(model, folder, sim=(0.0, TS, float(grid[-1])), log_only=log,
                                      num_log_samples=int(grid[-1] / 5e-4) + 1, timeout=280.0)
        rows = metrics(df, grid, u, seq, F0)
        results[case] = {"alpha": alpha, "neutral_open_to_tank": neutral_open, "beta_hose_Pa": beta_h,
                         "wall_s": time.perf_counter() - t0, "csv": info["csv"], "rows": rows}
        print(case, f"wall {info['wall_s']} s")
        for r in rows:
            print(f"  {r['motion']:14s} t_move {r['t_move_after_cmd_s']:.3f} (ideal {r['t_move_ideal_s']:.3f}) "
                  f"lag {r['stroke_lag_at_cmd_end_mm']:.3f}/{r['stroke_lag_at_hold_end_mm']:.3f} mm "
                  f"dF {r['peak_abs_dF_kN']:.2f} kN p_r pre {r['p_r_pre_bar_g']:.1f} end {r['p_r_cmd_end_bar_g']:.1f} "
                  f"hold {r['p_r_hold_end_bar_g']:.1f} p_h {r['p_h_pre_bar_g']:.1f}->{r['p_h_cmd_end_bar_g']:.1f} "
                  f"rip {r['v_ripple_mm_s_in_cmd']:.3f}")
    meta = {
        "dimensions": "current REXOME35, FL front 130/110, yaml 02_params/rexome33.yaml (not the L2 history)",
        "pressure_reference": "bar gauge (Hopsan absolute minus 1e5 Pa)",
        "fluid": {"beta_chamber_Pa": p.beta, "beta_hose_Pa": BETA_HOSE, "rho": RHO, "note": "VG46 50 C, ASSUMPTION"},
        "assumptions": {"tau_v_s": TAU_V, "pilot_ratio": PSI, "crack_bar": P_CRACK / 1e5, "poc_Ks": POC_KS,
                        "V_line_m3": V_LINE, "p_T_bar_g": P_T / 1e5, "p_r0_bar_g": P_R0 / 1e5,
                        "neutral_open_fraction": NEUTRAL_OPEN_FRACTION, "stroke_step_m": STROKE_STEP,
                        "valve": "ideal flow source, meter-out land = P->A land size, parallel B_p = C_LOCK"},
        "ts_s": TS,
    }
    dump("poc_reversal_quick.json" if quick else "poc_reversal.json", {"meta": meta, "cases": results})
    print("out", OUT)


if __name__ == "__main__":
    main()
