"""Post-event LEVEL series of one T4h file: every 1 s the command [mm/s], A(i) / A(ii) flags,
oil stroke [mm] per leg, and the sign reversals per leg of the command (|u| > u_hold)."""
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
U_HOLD = 2.09243016e-4


def main(name: str, t_from: float, t_to: float, step: float) -> None:
    with np.load(T4H / name, allow_pickle=False) as d:
        t = d["t_s"]
        ph = d["phase"]
        u = d["command_m_s"]
        s = d["motor_stroke_m"]
        a1 = d["lsb_a1_on"]
        a2 = d["lsb_a2_on"]
        fl = d["lsb_a1_floor_m_s"]
        locked = d["locked"]
    sel = (t >= t_from) & (t <= t_to)
    signs = np.sign(np.where(np.abs(u) > U_HOLD, u, 0.0))
    rev = []
    for k in range(4):
        sg = [x for x in signs[sel, k] if x != 0]
        rev.append(sum(1 for a, b in zip(sg, sg[1:]) if a != b))
    print(name, "reversals per leg", rev, "A(i) reads", a1[sel].sum(axis=0).tolist(),
          "A(ii) reads", a2[sel].sum(axis=0).tolist())
    next_t = t_from
    for i in np.flatnonzero(sel):
        if t[i] + 1e-9 < next_t:
            continue
        next_t = t[i] + step
        print(f"{t[i]:6.1f} {ph[i]:6s} u " + " ".join(f"{x * 1e3:6.2f}" for x in u[i])
              + " | s " + " ".join(f"{x * 1e3:7.2f}" for x in s[i])
              + " | a1 " + "".join("1" if x else "." for x in a1[i])
              + " fl " + " ".join("nan" if np.isnan(x) else f"{x * 1e3:4.2f}" for x in fl[i])
              + " | lk " + "".join("L" if x else "." for x in locked[i]))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]))
