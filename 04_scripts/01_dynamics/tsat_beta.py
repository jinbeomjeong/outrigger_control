"""Law C saturation stop vs beta: static overshoot k v t/2 - c v, window 10 dt .. 2 c / k."""
import math

V = 0.020924          # v_max [m/s] (YAML actuator.max_speed_m_s, CLAUDE.md)
DT = 2e-4             # L1 dt [s]
T_SAT = 2e-3          # law C stop time [s]
M_ROD = {"FL": 34403.519 / 322.179602, "RL": 30348.4527 / 414.806054}  # c_n / g_n [kg]
C_N = {"FL": 34403.519, "RL": 30348.4527}                              # YAML LOCK dashpot [N s/m]
K_N = {  # reference L1_beta_sensitivity_top k_L1_N_m (head-only pad k_n)
    0.69: {"FL": 18563100.0, "RL": 13867000.0},
    1.0: {"FL": 25905700.0, "RL": 19504600.0},
    1.6: {"FL": 38674500.0, "RL": 29522900.0},
}
LIM = {"FL": (278.7e3, 79.2e3), "RL": (199.6e3, 66.0e3)}  # extend / retract 210 bar [N]

for beta, kk in K_N.items():
    for leg in ("FL", "RL"):
        k, c, m = kk[leg], C_N[leg], M_ROD[leg]
        upper = 2 * c / k
        over = V * (k * T_SAT / 2 - c)
        step = k * V * DT
        zr = math.sqrt(K_N[1.0][leg] / k)  # zeta ratio at fixed c (single-dof, same mass)
        c_keep = c / zr
        upper_keep = 2 * c_keep / k
        over_keep = V * (k * T_SAT / 2 - c_keep)
        t_window = (10 * DT, upper)
        print(f"beta {beta:4.2f} {leg}: k {k:.4e} 2c/k {upper*1e3:.3f} ms  overshoot {over:+7.1f} N "
              f"({over/LIM[leg][0]*100:+.3f} % ext, {over/LIM[leg][1]*100:+.3f} % ret)  "
              f"one-step k v dt {step:6.1f} N  zeta ratio {zr:.4f} (0.03 -> {0.03*zr:.4f})  "
              f"c-rescaled: 2c/k {upper_keep*1e3:.3f} ms overshoot {over_keep:+7.1f} N  "
              f"inertia m v/t {m*V/T_SAT:6.1f} N  window {t_window[0]*1e3:.2f}..{t_window[1]*1e3:.3f} ms")
