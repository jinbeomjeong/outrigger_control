"""Q7-H1 detail of one breach leg: lock events (plant step times), the commanded / acting
speeds, the stroke, and the ③ class over a long window (read only).

Run: hydraulics-dev python.exe -I -B h7r2_release_detail.py <npz> <leg> <t_from> <t_to>
"""
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
CLASS = ["lock", "hold", "c_ext", "c_ret", "ext", "ret"]
STATE = ["mv_ext", "mv_ret", "lk_ext", "lk_ret"]
LEGS = ["FL", "FR", "RL", "RR"]


def main() -> None:
    path = Path(sys.argv[1])
    leg = LEGS.index(sys.argv[2])
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    d = np.load(path, allow_pickle=False)
    ev = d["lock_events"]
    print("lock events (t, leg, locked) of the leg in the window:")
    for t, lg, lk in ev:
        if int(lg) == leg and t0 - 5 <= t <= t1:
            print(f"  {t:9.4f} {LEGS[int(lg)]} locked={int(lk)}")
    t = d["t_s"]
    jt = d["jp3_t_s"]
    jidx = {round(v, 4): i for i, v in enumerate(jt)}
    print(" t     phase cls   state   cmd[mm/s] u_act  stroke  lk  rod   head   F[kN]  Fmin  "
          "p1x  p1need held open line rodrel")
    for i in np.flatnonzero((t >= t0) & (t <= t1)):
        j = jidx.get(round(float(t[i]), 4))
        cls = CLASS[d["jp3_class"][j, leg]] if j is not None and d["jp3_class"][j, leg] >= 0 else "-"
        st = (STATE[d["jp3_plant_state"][j, leg]]
              if j is not None and d["jp3_plant_state"][j, leg] >= 0 else "-")
        uact = d["jp3_u_m_s"][j, leg] * 1e3 if j is not None else np.nan
        print(f"{t[i]:5.1f} {str(d['phase'][i])[:5]:5s} {cls:5s} {st:6s} "
              f"{d['command_m_s'][i, leg] * 1e3:8.3f} {uact:7.3f} "
              f"{d['motor_stroke_m'][i, leg] * 1e3:8.3f} {int(d['locked'][i, leg])} "
              f"{d['rod_pressure_Pa'][i, leg] / BAR:6.2f} {d['head_pressure_Pa'][i, leg] / BAR:6.2f} "
              f"{d['true_force_N'][i, leg] / 1e3:7.2f} {d['true_force_min_N'][i, leg] / 1e3:7.2f} "
              f"{d['p1_x_m'][i, leg] * 1e3:6.3f} {d['p1_need_m'][i, leg] * 1e3:6.3f} "
              f"{int(d['p1_gate_held'][i, leg])} {int(d['p1_is_open'][i, leg])} "
              f"{int(d['p1_line_dir'][i, leg]):2d} {int(d['p1_rod_released'][i, leg])}")


if __name__ == "__main__":
    main()
