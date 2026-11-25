"""Where the 7.68 bar locked margin occurs (R12 top-RR-Fs0-o0.0-RE1bF, FR, M a2)."""
import json

import numpy as np

RUN = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
       r"\6bfb2560\ed7_probe_a1\ed7_probe_t4h")
name = "R12_top-RR-Fs0-o0.0-RE1bF-level_P7-M-a2.npz"
leg = 1
with np.load(f"{RUN}\\{name}") as d:
    meta = json.loads(str(d["meta_json"]))
    te = None
    jt = d["jp3_t_s"]
    cls = [str(s) for s in d["jp3_class_names"]]
    pst = [str(s) for s in d["jp3_plant_state_names"]]
    src = [str(s) for s in d["jp3_source_names"]]
    gap = (d["jp3_model_bound_Pa"][:, leg] - d["jp3_p_tr_Pa"][:, leg]) / 1e5
    lock = np.array([cls[c] == "lock" for c in d["jp3_class"][:, leg]]) & np.isfinite(gap)
    k = int(np.flatnonzero(lock)[np.argmin(gap[lock])])
    print("min locked gap", gap[k], "at t", jt[k])
    ph = [str(p) for p in d["phase"]]
    for j in range(max(0, k - 12), min(len(jt), k + 6)):
        print(f"{jt[j]:6.1f} {ph[j]:5s} {cls[d['jp3_class'][j, leg]]:9s} {pst[d['jp3_plant_state'][j, leg]]:10s} "
              f"model {d['jp3_model_bound_Pa'][j, leg]/1e5:7.2f} used {d['jp3_used_bound_Pa'][j, leg]/1e5:7.2f} "
              f"p_tr {d['jp3_p_tr_Pa'][j, leg]/1e5:7.2f} head {d['jp3_head_read_Pa'][j, leg]/1e5:7.2f} "
              f"mb_head {d['jp3_model_bound_head_Pa'][j, leg]/1e5:7.2f} src {src[d['jp3_model_bound_source'][j, leg]]} "
              f"x {d['p1_x_m'][j, leg]*1e3:6.3f} rod_rel {int(d['p1_rod_released'][j, leg])} u {d['jp3_u_m_s'][j, leg]*1e3:6.3f}")
