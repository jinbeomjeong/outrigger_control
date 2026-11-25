"""Detail reads of chosen (t4h, leg, t0, t1) windows and the clear events against the lock log.

Usage: python -I -B s06_detail.py <jsonl> <t4h dir> <s04 result json>
"""
import json
import sys
from pathlib import Path

import numpy as np

JSONL, T4H, RESULT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
LEGS = ("FL", "FR", "RL", "RR")
WINDOWS = [("R15_o0.05_P7-Mc04-a1.npz", 2, 51.9, 68.7),
           ("R15_o0.05_P7-Mc04-a6.npz", 2, 57.0, 67.7),
           ("R12_top-FR-Fs0-o0.0_P7-Mc04-c2.npz", 3, 69.5, 79.0)]


def dump(name, leg, t0, t1):
    with np.load(T4H / name, allow_pickle=False) as d:
        t = d["t_s"]
        sel = np.flatnonzero((t >= t0) & (t <= t1))
        print(f"== {name} leg {LEGS[leg]} {t0}-{t1}")
        print("   t  lk dir  cmd_mm_s  valve_mm_s  held  x_mm   need_mm drain_mm_s rod_bar head_bar")
        prev = None
        for k in sel:
            row = (bool(d["locked"][k, leg]), int(d["p1_line_dir"][k, leg]),
                   round(float(d["command_m_s"][k, leg]) * 1e3, 3),
                   round(float(d["p1_valve_speed_m_s"][k, leg]) * 1e3, 3),
                   bool(d["p1_gate_held"][k, leg]), round(float(d["p1_x_m"][k, leg]) * 1e3, 4),
                   round(float(d["p1_need_m"][k, leg]) * 1e3, 4),
                   round(float(d["p1_drain_m_s"][k, leg]) * 1e3, 4),
                   round(float(d["rod_pressure_Pa"][k, leg]) / 1e5, 3),
                   round(float(d["head_pressure_Pa"][k, leg]) / 1e5, 3))
            if row != prev:
                print(f"  {t[k]:7.2f}", *row)
            prev = row


for window in WINDOWS:
    dump(*window)

# rows needed for the clear-event check: lock_log truth at the release
result = json.loads(RESULT.read_text(encoding="utf-8"))
wanted = {(e["t4h"], e["leg"], e["t_release"]) for e in result["clear_events"]}
files = {w[0] for w in wanted}
print("== clear events: locked truth at release (lock log) vs rod reading at the last read before it")
with JSONL.open(encoding="utf-8") as handle:
    for line in handle:
        if not any(f'"t4h_file": "{f}"' in line for f in files):
            continue
        row = json.loads(line)
        if row["t4h_file"] not in files:
            continue
        hr = row["hydraulics_record"]
        cols = hr["lock_log_columns"]
        with np.load(T4H / row["t4h_file"], allow_pickle=False) as d:
            t = d["t_s"]
            rod = d["rod_pressure_Pa"]
            locked = d["locked"]
            for (name, leg_name, t_rel) in sorted(wanted):
                if name != row["t4h_file"]:
                    continue
                leg = LEGS.index(leg_name)
                rows = [r for r in hr["lock_log"] if int(r[1]) == leg and r[9] is not None
                        and abs(float(r[9]) - t_rel) < 1e-6]
                r = dict(zip(cols, rows[0]))
                truth_rel = (r["p_tr_after_Pa"] + r["dp_tr_lock_Pa"]) / 1e5
                k = int(np.flatnonzero(t < t_rel - 1e-6)[-1])
                print(f"  {name} {leg_name} t_rel {t_rel}: truth_at_release {truth_rel:.3f} bar, "
                      f"read t {t[k]:.2f} locked {bool(locked[k, leg])} rod {rod[k, leg] / 1e5:.3f} bar, "
                      f"diff {rod[k, leg] / 1e5 - truth_rel:+.3f}")
