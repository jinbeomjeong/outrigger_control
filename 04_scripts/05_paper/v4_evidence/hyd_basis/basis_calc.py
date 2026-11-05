"""Order-of-magnitude basis for the quasi-static oil-column force law of L2b (paper 2.2).

All SI, pressures gauge unless marked. Inputs from 02_params/rexome33.yaml and
dynamics_model.md 5.20.3 (copied as constants; no project file is written).
"""

import json
import math

BETA = 1.0e9          # Pa, effective bulk modulus (ASSUMPTION, YAML)
BETA_RANGE = (0.69e9, 1.6e9)
V_MAX = 0.0209243016  # m/s
STROKE = 0.70
LEGS = {
    # A_p, A_ann, e_op, k_out, k1(e_op), k2(e_op)
    "front": dict(Ap=1.32732e-2, Aann=3.76991e-3, e=0.4011, kout=2.16648e8, k1=3.39290e7, k2=2.59057e7,
                  F_static=118.2e3, m_rod=106.784),
    "rear": dict(Ap=9.50332e-3, Aann=3.14159e-3, e=0.3909, kout=2.05103e8, k1=2.64021e7, k2=1.95046e7,
                 F_static=72.0e3, m_rod=73.163),
}
M_TOTAL = 38760.7     # kg, damping mass (superstructure + 4 moving parts)
F_HEAVE = 8.9593      # Hz, L2b LOCK 6th mode top level (dynamics 5.20.4); YAML-derived 8.88
F_ROCK = 2.0608       # Hz, 1st rocking
W_CROSS = 0.2         # rad/s, attitude loop crossover
F_SAMPLE = 10.0       # Hz
TAU_V = 0.1           # s, valve first-order lag (ASSUMPTION)
C_INT = 0.5e-6 / 60.0 / 315e5   # m3/(s Pa), internal leakage 0.5 mL/min @ 315 bar (L2 spec 2.2)
DP_BACK = 5.0e5       # Pa, rod-side return back pressure at v_max (ASSUMPTION p_rod_back_extend)
RHO = 860.0
out = {}

f_cross = W_CROSS / (2 * math.pi)
f_valve = 1.0 / (2 * math.pi * TAU_V)
out["separation"] = {
    "f_cross_Hz": f_cross,
    "f_valve_corner_Hz": f_valve,
    "f_nyquist_Hz": F_SAMPLE / 2,
    "heave_over_cross": F_HEAVE / f_cross,
    "rock_over_cross": F_ROCK / f_cross,
    "heave_over_valve_corner": F_HEAVE / f_valve,
    "valve_gain_at_heave": 1 / math.hypot(1, 2 * math.pi * F_HEAVE * TAU_V),
    "valve_gain_at_rock": 1 / math.hypot(1, 2 * math.pi * F_ROCK * TAU_V),
}

for name, p in LEGS.items():
    r = {}
    for L0h in (0.05, 0.08):
        Vh = p["Ap"] * (L0h + p["e"])
        kh = BETA * p["Ap"] / (L0h + p["e"])
        m_leg = M_TOTAL / 4
        r[f"L0h_{L0h}"] = {
            "V_head_L": Vh * 1e3,
            "k_h_N_m": kh,
            "f_h_single_leg_Hz": math.sqrt((kh * p["kout"] / (kh + p["kout"])) / m_leg) / (2 * math.pi),
            # leakage time constant of a sealed head chamber against its own oil stiffness
            "tau_leak_s": Vh / (BETA * C_INT),
            # pressure rise rate when moving at v_max against the leg spring k2 (contact, lifting)
            "dpdt_lift_bar_s": p["k2"] * V_MAX / p["Ap"] / 1e5,
            # against a rigid stop (stroke end), oil only
            "dpdt_stop_bar_s": BETA * V_MAX / (L0h + STROKE) / 1e5,
        }
    # hydraulic damping from a non-ideal pressure compensator: 5 % flow drop over 0..210 bar (ASSUMPTION)
    Q = p["Ap"] * V_MAX
    Kc = 0.05 * Q / 210e5
    Vh = p["Ap"] * (0.05 + p["e"])
    r["Kc_assumed_m3_s_Pa"] = Kc
    r["zeta_from_Kc"] = Kc / (2 * p["Ap"]) * math.sqrt(BETA * (M_TOTAL / 4) / Vh)
    r["Q_head_vmax_L_min"] = Q * 6e4
    # rod-side RC time constant through the return path, linearised orifice: tau = 2 L_r dp / (beta v)
    taus = {}
    for L0r in (0.02, 0.05, 0.10):
        for s in (0.0, p["e"], 0.6948):
            Lr = STROKE - s + L0r
            for beta in (BETA_RANGE[0], BETA, BETA_RANGE[1]):
                taus[f"L0r{L0r}_s{s:.4f}_b{beta/1e9:.2f}"] = 2 * Lr * DP_BACK / (beta * V_MAX)
    r["tau_rod_RC_s_nominal"] = 2 * (STROKE - p["e"] + 0.05) * DP_BACK / (BETA * V_MAX)
    r["tau_rod_RC_s_min"] = min(taus.values())
    r["tau_rod_RC_s_max"] = max(taus.values())
    r["tau_rod_RC_s_max_dp8bar"] = max(taus.values()) * 8 / 5
    # valve stop transient: Delta v sqrt(k m) for ideal valve stop, per leg mass
    m_leg = M_TOTAL / 4
    dF = V_MAX * math.sqrt(p["k1"] * m_leg)
    r["stop_dF_ideal_valve_kN"] = dF / 1e3
    r["stop_dp_ideal_valve_bar"] = dF / p["Ap"] / 1e5
    # same with first-order valve tau_v: amplitude reduction ~ 1/sqrt(1+(w tau)^2) (order of magnitude)
    w = math.sqrt(p["k1"] / m_leg)
    r["stop_dF_tau_v_kN"] = dF / math.hypot(1, w * TAU_V) / 1e3
    # Joukowsky in an assumed 3/8" hose (ID 9.5 mm), c = sqrt(beta/rho)
    c = math.sqrt(BETA / RHO)
    A_hose = math.pi * 0.0095**2 / 4
    v_line = Q / A_hose
    r["hose_wave_speed_m_s"] = c
    r["hose_velocity_m_s"] = v_line
    r["joukowsky_bar"] = RHO * c * v_line / 1e5
    r["hose_5m_quarter_wave_Hz"] = c / (4 * 5.0)
    r["cylinder_wave_transit_ms"] = (STROKE + 0.05) / c * 1e3
    # law-C judged net force vs head pressure: p_h = F/Ap + p_r/phi
    phi = p["Ap"] / p["Aann"]
    r["phi"] = phi
    r["head_excess_at_lawC_bar_pr5"] = 5.0 / phi
    r["friction_share_bar_4kN"] = (4e3 if name == "front" else 4e3 * 0.8333) / p["Ap"] / 1e5
    out[name] = r

print(json.dumps(out, indent=1))
