"""P7-7 fill budget (Mslow c2 FL, 32.1-33.2 s): where 2.098 mm of command becomes x = 2.001 mm.

Rebuild of the harness path from the T4h commands (record check, not a plant run):
* command of read k acts over (t_k, t_k + 0.1 s] (checked: valve 32.3 s -1.06 mm/s vs T4h -1.057)
* valve: first order, tau_v 0.1 s (harness_hydraulics.HARNESS_VALVE_TAU_S), 1 ms chunks
* overlap cut (spec 2.5): a zero command's chunk mean valve speed <= u_ol = 0.02 v_max -> 0
* P1 retract line (check_open_delay._retract_step, d < 0): x += (|u| - drain) dt,
  drain = K_n g sqrt(rise * x / need) / A_ann, g = (1 - |u| / (c_v v_max))+
Values: v_max 20.9243 mm/s, c_v 0.02, n_f 0.05, dp_c 10 bar, need 2.3219 mm, p_open 30.62 bar.

Usage: python -I -B s11_fill_budget.py
"""
import math

V_MAX = 0.0209243016
A_H, A_ANN = 0.013273229, 0.00376991118
C_V, N_F, DP_C = 0.02, 0.05, 1.0e6
NEED, P_OPEN, P_T = 2.3219e-3, 30.62e5, 2e5
TAU, DT = 0.1, 0.001
U_OL = 0.02 * V_MAX
CMD_MM_S = [-0.020, -1.670, -1.687, -2.679, -3.492, -3.571, -3.393, -2.480, -1.488, -0.496,
            0.0, 0.0]          # reads 32.1 ... 33.2 s
K_N = N_F * A_H * V_MAX / math.sqrt(DP_C)

v = 0.0
x = 0.0
valve_int = 0.0
cut_int = 0.0      # oil the cut removed (what the valve would still have delivered)
drain_int = 0.0
low_speed_int = 0.0
neutral_int = 0.0
x_peak = 0.0
for k, cmd in enumerate(CMD_MM_S):
    u_cmd = cmd * 1e-3
    for _ in range(int(round(0.1 / DT))):
        v_new = u_cmd + (v - u_cmd) * math.exp(-DT / TAU)
        mean = 0.5 * (v + v_new)
        v = v_new
        if u_cmd == 0.0 and abs(mean) <= U_OL:
            cut_int += abs(mean) * DT
            mean = 0.0
            v = 0.0 if abs(v) <= U_OL else v
        speed = abs(mean)
        valve_int += speed * DT
        if speed <= 1e-6:  # neutral (d = 0): the line share drains (g = 1) down to the
            # trapped floor (1.4689 mm in T4h from 33.3 s, not reached before 33.2 s)
            level = min(x / NEED, 1.0)
            drain = K_N * math.sqrt((P_OPEN - P_T) * level) / A_ANN
            x_peak = max(x_peak, x)
            neutral_int += min(drain * DT, x)
            x = max(x - drain * DT, min(1.4689e-3, x))
            continue
        gate = max(1.0 - speed / (C_V * V_MAX), 0.0)
        level = min(x / NEED, 1.0)
        drain = K_N * gate * math.sqrt((P_OPEN - P_T) * level) / A_ANN
        if gate > 0.0:
            low_speed_int += speed * DT
        drain_int += min(drain * DT, x + speed * DT)
        x = max(x + (speed - drain) * DT, 0.0)
    print(f"  t {32.1 + 0.1 * (k + 1):5.2f}: valve {mean * 1e3:7.3f} mm/s, x {x * 1e3:7.4f} mm")
print(f"command integral {sum(abs(c) for c in CMD_MM_S) * 0.1:.4f} mm")
print(f"valve integral delivered {valve_int * 1e3:.4f} mm; cut by overlap {cut_int * 1e3:.4f} mm "
      f"(+ the tail after the last chunk {abs(v) * TAU * 1e3:.4f} mm)")
print(f"drain while |u| < c_v v_max {drain_int * 1e3:.4f} mm (oil sent at those speeds "
      f"{low_speed_int * 1e3:.4f} mm)")
print(f"x peak {x_peak * 1e3:.4f} mm, neutral drain before the next reads {neutral_int * 1e3:.4f} mm")
print(f"x end {x * 1e3:.4f} mm (T4h 33.2 s: 2.0013 mm, 33.3 s: 1.4689 mm)")
