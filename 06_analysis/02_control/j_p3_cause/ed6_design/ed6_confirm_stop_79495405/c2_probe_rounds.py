"""Probe rounds of one leg in confirmation (가) T4h files: phase segments, and per PROBE segment
the leg's command sign changes, rod / head pressure at the extend and retract hold ends (last
zero-command read of each hold), the rise rod(retract) - rod(extend) against max(3 bar, p_h/12),
and the lsb A(i) / A(ii) flags in the segment."""
import json
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def holds(u):
    """Runs of zero command (|u| <= 1e-9) inside a segment: list of (start, end) indices."""
    zero = np.abs(u) <= 1e-9
    out, i = [], 0
    while i < len(u):
        if zero[i]:
            j = i
            while j + 1 < len(u) and zero[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def main(names, leg_name="FL"):
    leg = LEGS.index(leg_name)
    for name in names:
        with np.load(T4H / name, allow_pickle=False) as d:
            t = d["t_s"]
            ph = d["phase"]
            u = d["command_m_s"][:, leg]
            pr = d["rod_pressure_Pa"][:, leg]
            phd = d["head_pressure_Pa"][:, leg]
            a1 = d["lsb_a1_on"][:, leg]
            a2 = d["lsb_a2_on"][:, leg]
            meta = json.loads(str(d["meta_json"]))
        print(f"== {name} leg {leg_name} final {ph[-1]} t_end {t[-1]:.1f}")
        events = [e for e in meta["events"] if any(k in e[1] for k in
                  ("ROD_PRESSURE", "relevel", "reapproach", "LSB", "probe", "ready_heave"))]
        for e in events:
            print(f"   ev {e[0]:.1f} {e[1]}")
        for name_ph, i0, i1 in segments(ph):
            line = f"   {name_ph:6s} {t[i0]:6.1f}-{t[i1]:6.1f}"
            if name_ph == "probe":
                seg_u = u[i0:i1 + 1]
                signs = [int(np.sign(x)) for x in seg_u if abs(x) > 1e-9]
                order = [s for k, s in enumerate(signs) if k == 0 or s != signs[k - 1]]
                hs = holds(seg_u)
                vals = []
                for a, b in hs:
                    k = i0 + b
                    vals.append(f"hold@{t[k]:.1f} pr {pr[k] / BAR:6.2f} ph {phd[k] / BAR:6.1f}")
                line += f" signs {order} a1 {int(a1[i0:i1 + 1].sum())} a2 {int(a2[i0:i1 + 1].sum())}"
                line += " | " + " ; ".join(vals)
            print(line)


if __name__ == "__main__":
    leg = sys.argv[1]
    main(sys.argv[2:], leg)
