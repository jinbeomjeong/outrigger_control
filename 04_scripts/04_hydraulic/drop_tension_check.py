"""RR ground drop (RE1b-F): L1-R lumped-contact tension artefact vs a rod-mass hydraulic model.

Paths:
  A  L1-R replica (rigid leg, SMC Kelvin-Voigt with Chrono's clamp N_smc >= 0, unclipped F_x)
  A' same with the proposed fix F_x = max(0, Phi + c dd) - max(0, k_n d + c dd)
  B  rod mass between locked oil columns (head + rod chamber, floors) and a unilateral
     concrete/structure contact (k_out), prescribed Poly345 ground drop; seal Coulomb friction
  C  closed form: tension ~ v_sep sqrt((k_h + k_r) m_rod) x overshoot(zeta)

SI units, gauge pressures (floor 0.1 bar abs = -0.913 bar g). Body (machine corner) fixed:
upper bound on the separation speed (assumption, the corner also starts to fall).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

# --- RR parameters (02_params/rexome33.yaml, rod_side_pressure.md 14.3 / 14.7 (5)) ---
A_P = math.pi / 4 * 0.110**2
A_ANN = A_P - math.pi / 4 * 0.090**2
BETA = 1.0e9
K_H = 2.1554e7  # derivation.k_oil_N_m (rear)
K_R = 8.748517e6  # rod_side.k_rod_side_N_m
K_N = 19504614.9  # head-only pad stiffness (SMC)
K_OUT = 1.0 / (1.0 / K_N - 1.0 / K_H)
K_NP = 1.0 / (1.0 / (K_H + K_R) + 1.0 / K_OUT)
C_N = 30348.4527  # L1 LOCK pad dashpot (cn_per_pad_N_s_m)
M_ROD = 73.163
G = 9.80665
F_CYL0 = 70282.0
F_PAD0 = F_CYL0 + M_ROD * G
P_R0 = 2.0e5
P_FLOOR = 1.0e4 - 1.01325e5  # gauge
R_SHARE = K_R / (K_H + K_R)
K_CONC = 323661912.0  # L2 concrete kn
C_CONC = 78713.0116  # L2 contact cn (ASSUMPTION, rod local mode zeta 0.30)

DEPTH = 0.030


def poly345(t: np.ndarray | float, ramp: float):
    tau = np.clip(np.asarray(t, dtype=float) / ramp, 0.0, 1.0)
    z = DEPTH * (10 * tau**3 - 15 * tau**4 + 6 * tau**5)
    v = DEPTH / ramp * (30 * tau**2 - 60 * tau**3 + 30 * tau**4)
    return z, v


def path_a(ramp: float, fixed: bool, dt: float = 1.0e-6) -> dict:
    """L1-R replica: delta = delta_lock - ground drop (leg rigid and fixed)."""
    d_lock = F_PAD0 / K_N  # anchor at head-only SMC equilibrium (F_x = 0 at lock)
    t = np.arange(0.0, 3.0 * ramp, dt)
    z, v = poly345(t, ramp)
    d = d_lock - z
    dd = -v
    phi = F_PAD0 + K_NP * (d - d_lock)  # unloading side, below the knee
    smc = np.where(d > 0, np.maximum(0.0, K_N * d + C_N * dd), 0.0)
    fx = np.where(d > 0, np.maximum(phi, 0.0) - K_N * np.maximum(d, 0.0), 0.0)
    if fixed:
        fx = np.where(d > 0, np.maximum(0.0, phi + C_N * dd) - smc, 0.0)
    net = smc + fx
    f_cyl = net - M_ROD * G  # rigid leg, no acceleration
    i = int(np.argmin(f_cyl))
    lift = int(np.argmax(phi <= 0.0))
    neg = f_cyl < -2.0 * M_ROD * G
    width = float(neg.sum() * dt)
    return {
        "F_cyl_min_kN": f_cyl[i] / 1e3,
        "t_min_ms": t[i] * 1e3,
        "delta_at_lift_mm": d[lift] * 1e3,
        "Fx_at_lift_kN": fx[lift] / 1e3,
        "sep_speed_at_lift_m_s": float(-dd[lift]),
        "t_lift_ms": t[lift] * 1e3,
        "tension_width_ms(F_cyl<-2mg)": width * 1e3,
    }


def path_b(ramp: float, c_oil: float, f_s: float, dt: float = 2.0e-7) -> dict:
    """Rod mass on locked oil columns, unilateral contact to the prescribed ground.

    x = rod extension from the locked equilibrium (+ = out, toward the ground).
    """
    p_h0 = (F_CYL0 + P_R0 * A_ANN) / A_P
    x0_c = F_PAD0 / K_CONC_SERIES  # contact pre-compression
    t_end = 0.5 * ramp + 0.03
    n = int(t_end / dt)
    x = 0.0
    vx = 0.0
    out_min = (math.inf, 0.0)
    ph_min, pr_max = math.inf, -math.inf
    t_lift = None
    v_lift = None
    for k in range(n):
        tk = k * dt
        tau = min(max(tk / ramp, 0.0), 1.0)
        zg = DEPTH * (10 * tau**3 - 15 * tau**4 + 6 * tau**5)
        vg = DEPTH / ramp * (30 * tau**2 - 60 * tau**3 + 30 * tau**4)
        p_h = max(P_FLOOR, p_h0 - K_H / A_P * x)
        p_r = max(P_FLOOR, P_R0 + K_R / A_ANN * x)
        f_oil = p_h * A_P - p_r * A_ANN  # sensor net force (pushes the rod out)
        pen = x0_c + x - zg
        f_c = max(0.0, K_CONC_SERIES * pen + C_C * (vx - vg)) if pen > 0 else 0.0
        if f_c == 0.0 and t_lift is None and tk > 0:
            t_lift, v_lift = tk, vx
        f_fric = -f_s * math.tanh(vx / 1.0e-3)
        acc = (f_oil + M_ROD * G - f_c + f_fric - c_oil * vx) / M_ROD
        vx += acc * dt
        x += vx * dt
        if f_oil < out_min[0]:
            out_min = (f_oil, tk)
        ph_min = min(ph_min, p_h)
        pr_max = max(pr_max, p_r)
    return {
        "F_oil_min_kN": out_min[0] / 1e3,
        "t_min_ms": out_min[1] * 1e3,
        "t_lift_ms": None if t_lift is None else t_lift * 1e3,
        "rod_speed_at_lift_m_s": v_lift,
        "p_h_min_bar_g": ph_min / 1e5,
        "p_r_max_bar_g": pr_max / 1e5,
    }


def path_c(v_sep: float, zeta: float) -> float:
    k = K_H + K_R
    ov = math.exp(-zeta / math.sqrt(1 - zeta**2) * math.atan2(math.sqrt(1 - zeta**2), zeta))
    return -(v_sep * math.sqrt(k * M_ROD) * ov) / 1e3


# contact path outside the oil: k_out (rod + frame + concrete) as one unilateral spring
K_CONC_SERIES = K_OUT
C_C = C_CONC


def main() -> None:
    out_path = Path(sys.argv[1])
    res: dict = {
        "params": {
            "A_p": A_P, "A_ann": A_ANN, "k_h": K_H, "k_r": K_R, "k_n": K_N, "k_n_locked": K_NP,
            "k_out": K_OUT, "c_n": C_N, "m_rod": M_ROD, "F_pad0": F_PAD0, "r": R_SHARE,
            "delta_lift_formula_mm": F_PAD0 * (1 / K_N - 1 / K_NP) * 1e3,
            "Fx_lift_formula_kN": -K_N * F_PAD0 * (1 / K_N - 1 / K_NP) / 1e3,
            "rod_oil_mode_Hz": math.sqrt((K_H + K_R) / M_ROD) / 2 / math.pi,
            "sqrt_km_N_s_m": math.sqrt((K_H + K_R) * M_ROD),
        },
        "A": {}, "A_fix": {}, "B": {}, "C": {},
    }
    for ramp in (0.05, 0.1, 0.2, 2.0):
        res["A"][f"ramp_{ramp}"] = path_a(ramp, fixed=False)
        res["A_fix"][f"ramp_{ramp}"] = path_a(ramp, fixed=True)
    sqrt_km = math.sqrt((K_H + K_R) * M_ROD)
    for ramp in (0.05, 0.1, 0.2):
        for zeta in (0.0, 0.1, 0.3):
            for f_s in (0.0, 3700.0):
                key = f"ramp_{ramp}_zeta_{zeta}_Fs_{f_s:.0f}"
                res["B"][key] = path_b(ramp, c_oil=2 * zeta * sqrt_km, f_s=f_s,
                                       dt=1.0e-6)
    for ramp in (0.05, 0.1, 0.2):
        v = res["B"][f"ramp_{ramp}_zeta_0.0_Fs_0"]["rod_speed_at_lift_m_s"] or 0.0
        res["C"][f"ramp_{ramp}"] = {
            "v_sep_from_B_m_s": v,
            **{f"zeta_{z}": path_c(v, z) for z in (0.0, 0.1, 0.3)},
        }
    out_path.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
