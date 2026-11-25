"""Void share trap check over every VBM row (record evidence only).

A lock interval of a leg has a fill rise > 0 at some time iff its release has a
``p1_fill_release_log`` row or a ``rod_check_clear_log`` row falls inside it (the rise never
decreases inside a lock interval except by those two). In an interval without that evidence the
rise was 0 throughout, so a locked retract line that keeps ``x > 0`` in neutral (drain > 0) can
only be held by ``min(void_fill_m, void)``.

Counted per interval class (closed: ends by a release; open: still locked at the run end):
* neutral reads: both reads of a pair locked, line_dir -1, |valve| <= 1e-6, x0 > 0, drain > 0
* held: x1 >= x0 - 0.5 * min(drain * dt, x0)   (drained less than half of the free drain)
* partial fills: locked reads with valve < 0 and gate_held (a retract fill held by the gate)

Usage: python -I -B s07_void.py <jsonl> <t4h dir> <out json>
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

JSONL, T4H, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
M_FAMILY = ("M", "Mslow", "Mfast", "Mc005", "Mc04")
LEGS = ("FL", "FR", "RL", "RR")
EPS = 1e-6


def interval_of(lock_events, leg, t):
    locks = [e[0] for e in lock_events if int(e[1]) == leg and e[2] and e[0] <= t]
    rels = [e[0] for e in lock_events if int(e[1]) == leg and not e[2] and e[0] > t]
    return (max(locks) if locks else None), (min(rels) if rels else None)


counts = collections.Counter()
examples = collections.defaultdict(list)
with JSONL.open(encoding="utf-8") as handle:
    for line in handle:
        row = json.loads(line)
        probe = row.get("ed7_probe") or {}
        if probe.get("plant") not in M_FAMILY:
            continue
        hr = row["hydraulics_record"]
        gate = hr["line_fill_gate"]
        lock_events = hr["lock_events"]
        rel_rows = hr["p1_fill_release_log"]
        clear_rows = gate["rod_check_clear_log"]
        peak = gate["fill_rise_peak_bar"]
        with np.load(T4H / row["t4h_file"], allow_pickle=False) as d:
            t, lk = d["t_s"], d["locked"]
            ldir, valve = d["p1_line_dir"], d["p1_valve_speed_m_s"]
            x, drain, held = d["p1_x_m"], d["p1_drain_m_s"], d["p1_gate_held"]
            found = d["p1_read_found"]
            rod = d["rod_pressure_Pa"]
        for leg in range(4):
            for k in range(len(t) - 1):
                if not (found[k] and found[k + 1]):
                    continue
                is_fill = bool(lk[k, leg] and valve[k, leg] < -EPS and held[k, leg]
                               and ldir[k, leg] == -1)
                is_neutral = all(lk[j, leg] and ldir[j, leg] == -1 and abs(valve[j, leg]) <= EPS
                                 for j in (k, k + 1))
                if not (is_fill or is_neutral):
                    continue
                t_lock, t_rel = interval_of(lock_events, leg, float(t[k + 1]))
                lo = -1.0 if t_lock is None else t_lock
                hi = np.inf if t_rel is None else t_rel
                rise = ((t_rel is not None and any(int(r[1]) == leg and abs(r[0] - t_rel) < 1e-6
                                                   for r in rel_rows))
                        or any(int(r[1]) == leg and lo < r[0] <= hi for r in clear_rows))
                if t_rel is None and not rise:
                    cls = "open_no_rise" if peak[leg] == 0 else "open_unknown"
                else:
                    cls = "rise" if rise else "no_rise"
                if is_fill:
                    counts[(cls, "partial_fill_reads")] += 1
                    continue
                x0, x1, dr = float(x[k, leg]), float(x[k + 1, leg]), float(drain[k + 1, leg])
                if not (x0 > 1e-9 and np.isfinite(dr) and dr > 0):
                    continue
                dt = float(t[k + 1] - t[k])
                counts[(cls, "neutral_x_pos_reads")] += 1
                if x1 >= x0 - 0.5 * min(dr * dt, x0):
                    counts[(cls, "neutral_held_reads")] += 1
                    reading = float(rod[k + 1, leg]) / 1e5
                    tag = ("rod_nan" if not np.isfinite(reading)
                           else "rod_at_floor" if reading <= -0.90 else "rod_above_floor")
                    counts[(cls, "neutral_held_" + tag)] += 1
                    if cls != "rise" and len(examples[cls]) < 20:
                        examples[cls].append([probe["plant"], probe["arm"], row["t4h_file"],
                                              LEGS[leg], round(float(t[k + 1]), 2),
                                              round(x1 * 1e3, 4), t_lock, t_rel])
out = {"counts": {f"{a}|{b}": n for (a, b), n in sorted(counts.items())},
       "examples": examples}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
print(json.dumps(out["counts"], indent=1))
for cls, rows in examples.items():
    print(cls)
    for r in rows:
        print("  ", r)
