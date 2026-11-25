"""Per-read P1 trace of one leg around a time (argv: npz name, leg, t0, t1)."""
import sys

import numpy as np

DIR = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
       r"\6bfb2560\ed7_probe_a1\ed7_probe_t4h")
name, leg, t0, t1 = sys.argv[1], "FL FR RL RR".split().index(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
with np.load(f"{DIR}\\{name}", allow_pickle=False) as d:
    t = d["t_s"]
    sel = np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9))
    print("t phase cmd[mm/s] s[mm] p_h p_r p_tr x[mm] need[mm] open charged rod_rel held dir class pstate")
    cls = [str(s) for s in d["jp3_class_names"]]
    pst = [str(s) for s in d["jp3_plant_state_names"]]
    for k in sel:
        print(f"{t[k]:6.1f} {str(d['phase'][k]):5s} {d['command_m_s'][k, leg]*1e3:7.3f} "
              f"{d['motor_stroke_m'][k, leg]*1e3:9.4f} {d['head_pressure_Pa'][k, leg]/1e5:7.2f} "
              f"{d['rod_pressure_Pa'][k, leg]/1e5:6.2f} {d['jp3_p_tr_Pa'][k, leg]/1e5:6.2f} "
              f"{d['p1_x_m'][k, leg]*1e3:6.3f} {d['p1_need_m'][k, leg]*1e3:6.3f} "
              f"{int(d['p1_is_open'][k, leg])} {int(d['p1_charged'][k, leg])} "
              f"{int(d['p1_rod_released'][k, leg])} {int(d['p1_gate_held'][k, leg])} "
              f"{int(d['p1_line_dir'][k, leg]):2d} {cls[d['jp3_class'][k, leg]]:9s} {pst[d['jp3_plant_state'][k, leg]]}")
