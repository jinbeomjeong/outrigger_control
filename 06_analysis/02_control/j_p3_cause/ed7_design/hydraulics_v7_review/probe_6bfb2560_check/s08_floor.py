"""Locked retract reads with the rod truth at its floor (reading <= -0.90 bar g; the probe rod
reading is the P4 truth plus the held fill rise, floor 0.1 bar abs = -0.913 bar g) in VBM rows:
partial fills and neutral reads, split by the interval rise evidence of s07.

Usage: python -I -B s08_floor.py <jsonl> <t4h dir>
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

JSONL, T4H = Path(sys.argv[1]), Path(sys.argv[2])
M_FAMILY = ("M", "Mslow", "Mfast", "Mc005", "Mc04")
EPS = 1e-6
FLOOR_READ_BAR = -0.90


def interval_of(lock_events, leg, t):
    locks = [e[0] for e in lock_events if int(e[1]) == leg and e[2] and e[0] <= t]
    rels = [e[0] for e in lock_events if int(e[1]) == leg and not e[2] and e[0] > t]
    return (max(locks) if locks else None), (min(rels) if rels else None)


counts = collections.Counter()
floor_values = []
examples = []
with JSONL.open(encoding="utf-8") as handle:
    for line in handle:
        row = json.loads(line)
        probe = row.get("ed7_probe") or {}
        if probe.get("plant") not in M_FAMILY:
            continue
        hr = row["hydraulics_record"]
        gate = hr["line_fill_gate"]
        with np.load(T4H / row["t4h_file"], allow_pickle=False) as d:
            t, lk, ldir = d["t_s"], d["locked"], d["p1_line_dir"]
            valve, held, x = d["p1_valve_speed_m_s"], d["p1_gate_held"], d["p1_x_m"]
            rod, found = d["rod_pressure_Pa"] / 1e5, d["p1_read_found"]
        for leg in range(4):
            for k in range(len(t)):
                if not (found[k] and lk[k, leg] and ldir[k, leg] == -1):
                    continue
                if not np.isfinite(rod[k, leg]):
                    counts[("nan_rod_reading", "any", "any")] += 1
                    continue
                if rod[k, leg] > FLOOR_READ_BAR:
                    continue
                floor_values.append(round(float(rod[k, leg]), 3))
                kind = ("fill" if valve[k, leg] < -EPS and held[k, leg]
                        else "neutral" if abs(valve[k, leg]) <= EPS else "other")
                t_lock, t_rel = interval_of(hr["lock_events"], leg, float(t[k]))
                lo = -1.0 if t_lock is None else t_lock
                hi = np.inf if t_rel is None else t_rel
                rise = ((t_rel is not None and any(int(r[1]) == leg and abs(r[0] - t_rel) < 1e-6
                                                   for r in hr["p1_fill_release_log"]))
                        or any(int(r[1]) == leg and lo < r[0] <= hi
                               for r in gate["rod_check_clear_log"]))
                cls = "rise" if rise else ("no_rise" if t_rel is not None else "open")
                counts[(cls, kind, "x_pos" if x[k, leg] > 1e-9 else "x_zero")] += 1
                if cls != "rise" and len(examples) < 15:
                    examples.append([probe["plant"], probe["arm"], row["t4h_file"], leg,
                                     round(float(t[k]), 2), kind, round(float(x[k, leg]) * 1e3, 4),
                                     round(float(rod[k, leg]), 3)])
print(json.dumps({f"{a}|{b}|{c}": n for (a, b, c), n in sorted(counts.items())}, indent=1))
print("floor reading values:", sorted(collections.Counter(floor_values).items())[:10])
for e in examples:
    print("  ", e)
