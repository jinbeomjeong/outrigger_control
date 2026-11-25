"""Q7-H6 (2): A(i)-b ladder on a locked leg's retract line, two plant forms of the neutral vent.

* full (harness P1 VN gate, check_open_delay): drain = K_n g sqrt((p_open - p_T) x / need) / A_ann,
  g = (1 - |u| / (c_v v_max))+  -> the vent closes with the spool stroke; above c_v v_max the
  line fills at |u|.
* sub (stats s10 form): the line fills at (|u| - c_v v_max)+ (a vent that stays open by the
  spool opening c_v v_max).
Ladder (spec 3.1): 0.409 mm/s, +0.2 mm/s per 0.1 s period, cap 1.05 mm/s, end after N_cap = 50
periods at the cap. Valve: d = 1 then first order tau_v 0.1 s, 1 ms chunks. Front leg, p_open
30.6 bar (R12 FL state); the cap-phase result does not depend on p_open in the full form.

Usage: python -I -B s14_ladder.py
"""
import math

V_MAX = 0.0209243016
A_H, A_ANN = 0.013273229, 0.00376991118
N_F, DP_C, P_T, P_OPEN = 0.05, 1.0e6, 2e5, 30.6e5
TAU, DT, PERIOD = 0.1, 0.001, 0.1
K_N = N_F * A_H * V_MAX / math.sqrt(DP_C)


def ladder():
    u, out = 0.409e-3, []
    while u < 1.05e-3 - 1e-12:
        out.append(u)
        u = min(u + 0.2e-3, 1.05e-3)
    return out + [1.05e-3] * 50


def run(form, c_v, need):
    cmds = [0.0] + ladder()          # d = 1: the first period still sees the old command 0
    v = x = 0.0
    for k, cmd in enumerate(cmds):
        for _ in range(int(round(PERIOD / DT))):
            v = cmd + (v - cmd) * math.exp(-DT / TAU)
            speed = abs(v)
            if form == "full":
                g = max(1.0 - speed / (c_v * V_MAX), 0.0)
                drain = K_N * g * math.sqrt((P_OPEN - P_T) * min(x / need, 1.0)) / A_ANN
                x = max(x + (speed - drain) * DT, 0.0)
            else:
                x = max(x + max(speed - c_v * V_MAX, 0.0) * DT, 0.0)
            if x >= need:
                return k * PERIOD + _ * DT, True
    return len(cmds) * PERIOD, False


for c_v in (0.02, 0.04):
    print(f"c_v {c_v}: c_v v_max {c_v * V_MAX * 1e3:.3f} mm/s, ladder {len(ladder())} periods")
    for need_mm in (1.5, 2.3, 3.5, 4.9, 5.3):
        res = []
        for form in ("full", "sub"):
            t, opened = run(form, c_v, need_mm * 1e-3)
            res.append(f"{form}: {'open at %.2f s' % t if opened else 'NOT open (cap end %.1f s)' % t}")
        print(f"  need {need_mm} mm: " + "; ".join(res))
