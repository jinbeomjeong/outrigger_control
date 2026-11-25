"""Edge probes of CheckOpenGateP1Patch (worktree ed7-impl a6fc3dd5), read only.

A: tiny trapped rise + neutral: does line_dir go to 0 with x floored > 0, and does a
   following extend command read that x as A-line fill?
B: partial fill inside the void (rise 0) then neutral: is the void-filled oil trapped?
C: extend after a held (not opened) retract fill: window between the extend rod-check
   opening (rod_released) and the head-check opening; fill_rise kept through it?
D: hand numbers: M2 shift A_ann * rise / k_h, extend rod-check line difference.
"""
import math
import sys

import numpy as np

WT = r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl"
sys.path.insert(0, WT + r"\03_src")

from outrigger_sim.hydraulics import v5_options  # noqa: E402
from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit, CheckDelayInputs, CheckOpenGateP1Patch)

FRONT_A_H = math.pi / 4 * 0.13**2
FRONT_A_ANN = math.pi / 4 * (0.13**2 - 0.11**2)
REAR_A_H = math.pi / 4 * 0.11**2
REAR_A_ANN = math.pi / 4 * (0.11**2 - 0.09**2)
S_MAX, L0, P_T, V_MAX = 0.70, 0.05, 2e5, 0.020924


def gate(beta=1e9, scale=1.0, c_v=0.02):
    circuit = CheckDelayCircuit(head_area_m2=np.full(4, FRONT_A_H),
                                annulus_area_m2=np.full(4, FRONT_A_ANN), stroke_m=S_MAX,
                                rod_dead_length_m=L0, head_dead_length_m=L0,
                                bulk_modulus_Pa=1.0e9, tank_pressure_Pa=P_T, max_speed_m_s=V_MAX,
                                compensator_drop_Pa=10e5)
    patch = v5_options.P1PatchSetting(line_scale=scale, dead_scale=scale, bulk_modulus_Pa=beta)
    return CheckOpenGateP1Patch(v5_options.CheckDelaySetting("VN", 1.0, c_v), circuit, patch)


def inputs(u, *, dt=0.001, void=0.0, p_h=99.39e5, p_r=5.07e5, s=0.40836, locked=True, t=0.0):
    speed = np.zeros(4)
    speed[0] = u
    return CheckDelayInputs(t, dt, speed, np.full(4, p_h), np.full(4, p_r),
                            np.array([locked, True, True, True]), np.array([void, 0, 0, 0.0]),
                            np.zeros(4), np.full(4, s))


print("== A: tiny trapped rise, neutral at 1 ms chunks, then extend ==")
for oil_um in (93.0, 94.0, 96.0, 100.0, 150.0):
    g = gate()
    speed = 2.0e-3
    steps = round(oil_um * 1e-6 / (speed * 0.001))
    for k in range(steps):
        g.filter(inputs(-speed))
    rise = float(g.fill_rise_Pa[0])
    trapped = g._trapped_fill_m(inputs(0.0), 0, rise, 0.0) if rise > 0 else 0.0
    zero_dir_with_x = 0
    for k in range(3000):  # 3 s neutral
        g.filter(inputs(0.0))
        if g.line_dir[0] == 0 and g.x[0] > 0:
            zero_dir_with_x += 1
    x_neutral = float(g.x[0])
    line_dir = int(g.line_dir[0])
    g.filter(inputs(+speed))
    p_a = P_T + g.x[0] * FRONT_A_H * g.values.beta_hose_Pa / g.values.v_line_m3
    print(f"oil {oil_um:6.1f} um: rise {rise/1e5:7.4f} bar trapped {trapped*1e6:8.3f} um "
          f"x after neutral {x_neutral*1e6:8.3f} um line_dir {line_dir} "
          f"(steps with dir 0 and x>0: {zero_dir_with_x}); after 1 extend chunk x "
          f"{g.x[0]*1e6:8.3f} um -> p_A {p_a/1e5:6.2f} bar")

print("== B: void 1.0 mm, partial fill 0.5 mm (rise 0), then 3 s neutral ==")
g = gate()
speed = 0.5e-3
for k in range(round(0.5e-3 / (speed * 0.001))):
    g.filter(inputs(-speed, void=1.0e-3, p_r=-0.9e5))
print(f"x after fill {g.x[0]*1e3:.4f} mm, rise {g.fill_rise_Pa[0]/1e5:.3f} bar")
for k in range(3000):
    g.filter(inputs(0.0, void=1.0e-3, p_r=-0.9e5))
print(f"x after neutral {g.x[0]*1e3:.4f} mm (physical trapped void oil 0.5 mm less the line "
      f"pre-share)")

print("== C: slow corner, held retract 2.098 mm (not open), then extend at 0.209 / 0.409 / "
      "5 mm/s ==")
for ext_speed in (0.209e-3, 0.409e-3, 1.05e-3, 5e-3):
    g = gate(0.69e9, 1.5)
    rspeed = 2e-3
    for k in range(round(2.098e-3 / (rspeed * 0.001))):
        g.filter(inputs(-rspeed))
    rise = float(g.fill_rise_Pa[0])
    assert not g.is_open[0]
    t_rod = t_head = None
    for k in range(20000):
        g.filter(inputs(+ext_speed, t=k * 0.001))
        if t_rod is None and g.rod_released[0]:
            t_rod = k * 0.001
        if g.is_open[0]:
            t_head = k * 0.001
            break
    fmt = lambda v: "never" if v is None else f"{v:.3f} s"
    print(f"ext {ext_speed*1e3:5.3f} mm/s: held rise {rise/1e5:6.2f} bar, rod check opens "
          f"{fmt(t_rod)}, head check opens {fmt(t_head)}, "
          f"fill_rise at head opening {g.fill_rise_Pa[0]/1e5:6.2f} bar")

print("== D: hand numbers ==")
for name, a_h, a_ann in (("front", FRONT_A_H, FRONT_A_ANN), ("rear", REAR_A_H, REAR_A_ANN)):
    k_h = 1e9 * a_h / (L0 + 0.40836)
    for rise_bar in (5.0, 20.5, 22.4):
        shift = a_ann * rise_bar * 1e5 / k_h
        print(f"{name}: k_h {k_h/1e6:6.2f} MN/m, rise {rise_bar:5.1f} bar -> M2 shift "
              f"{shift*1e3:6.3f} mm, A_ann*rise {a_ann*rise_bar*1e5/1e3:6.2f} kN")
    c_l = 285e-6 / 0.5e9
    for rise_bar in (20.5, 22.4):
        d_line = c_l * rise_bar * 1e5 / 3.5 / a_h
        print(f"{name}: extend rod-check opening with p_r + rise needs {d_line*1e3:6.4f} mm more "
              f"A-line fill (rise {rise_bar} bar)")
