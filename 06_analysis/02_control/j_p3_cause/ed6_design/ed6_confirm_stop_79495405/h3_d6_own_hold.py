"""D6 quantity at each leg's OWN probe hold ends (read only).

The controller probes the legs one after another (FL, FR, RL, RR). D6 (two_pressure.py
probe_round_finished) reads p_r at the leg's own first hold end (``t_first_hold_end_s``) and at
its own second hold end (``t_second_hold_end_s`` = the read that closed the leg's second hold,
ground_contact.py 1050-1051), not at the end of the probe phase. Here: per probe phase and leg,
move 1 / move 2 = the first two non-zero command runs of the leg that contain a command above
``BIG_M_S``, hold 1 end = the read before move 2, hold 2 end = the read before the next leg's
move 1 (last leg: phase end). A reversed probe (move 1 retracting) takes the rise the other way,
as D6 does. A probe cut by the end of the run is listed with one move and skipped. Printed: rise = p_r(hold 2 end) - p_r(hold 1 end), required = max(3 bar, p_h(hold 2 end) / 12),
whether the leg left its lock during move 2 + 0.5 s, and its motor stroke change over move 2 and
hold 2 [mm]."""
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5
EPS = 1e-9
BIG_M_S = 1.3e-3
"""Probe moves reach 1.7-3.6 mm/s; the LEVEL tail commands entering the probe phase stay below
0.7 mm/s and the A(i) cap is 1.05 mm/s, so a probe move is a non-zero run that contains a
command above this."""


def runs(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def probe_segments(phase):
    return runs(phase == "probe")


def main(names):
    for name in names:
        with np.load(T4H / name, allow_pickle=False) as d:
            t, ph = d["t_s"], d["phase"]
            u, s = d["command_m_s"], d["motor_stroke_m"]
            locked = d["locked"]
            p_h, p_r = d["head_pressure_Pa"], d["rod_pressure_Pa"]
        print(f"== {name}")
        for i0, i1 in probe_segments(ph):
            moves_of = {}
            for leg in range(4):
                big = np.abs(u[i0:i1 + 1, leg]) > BIG_M_S
                nonzero = np.abs(u[i0:i1 + 1, leg]) > EPS
                found = []
                for a, b in runs(big):
                    while a > 0 and nonzero[a - 1]:  # widen to the whole non-zero run
                        a -= 1
                    while b + 1 < len(nonzero) and nonzero[b + 1]:
                        b += 1
                    if not found or found[-1] != (i0 + a, i0 + b):
                        found.append((i0 + a, i0 + b))
                moves_of[leg] = found
            order = sorted((k for k in moves_of if moves_of[k]), key=lambda k: moves_of[k][0][0])
            print(f"  probe {t[i0]:.1f}-{t[i1]:.1f} order {[LEGS[k] for k in order]}")
            for pos, leg in enumerate(order):
                moves = moves_of[leg]
                if len(moves) < 2:
                    print(f"    {LEGS[leg]} probe moves {len(moves)}: skipped")
                    continue
                m1, m2 = moves[0], moves[1]
                k_h1 = m2[0] - 1
                k_h2 = (moves_of[order[pos + 1]][0][0] - 1) if pos + 1 < len(order) else i1
                sign1 = int(np.sign(u[m1[0], leg]))
                rise = (p_r[k_h2, leg] - p_r[k_h1, leg]) / BAR
                if sign1 < 0:
                    rise = -rise
                need = max(3.0, p_h[k_h2, leg] / BAR / 12.0)
                k_rel = min(m2[1] + 5, i1)
                released = bool((~locked[m2[0]:k_rel + 1, leg]).any())
                ds = (s[k_h2, leg] - s[m2[0], leg]) * 1e3
                oil = np.abs(u[m2[0]:m2[1] + 1, leg]).sum() * 0.1 * 1e3
                flag = "MISS" if rise < need else "ok"
                print(f"    {LEGS[leg]} sign1 {sign1:+d} hold1 {t[k_h1]:.1f} p_r {p_r[k_h1, leg] / BAR:6.2f}"
                      f" | hold2 {t[k_h2]:.1f} p_r {p_r[k_h2, leg] / BAR:6.2f} p_h {p_h[k_h2, leg] / BAR:6.2f}"
                      f" | rise {rise:6.2f} req {need:5.2f} {flag:4s} | move2 oil {oil:5.3f} mm"
                      f" released {released} ds {ds:7.3f} mm")


if __name__ == "__main__":
    main(sys.argv[1:])
