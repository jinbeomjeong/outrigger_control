"""Tables of the 11b grid (q1_trapped_after_ret*.json): largest HOLD excess over the retract model
by leg x F and by speed, and the plan A margin. Usage: python -I q1_table.py <json> [<json> ...]"""
import json
import sys
from collections import defaultdict
from pathlib import Path

rows = []
for p in sys.argv[1:]:
    rows += json.loads(Path(p).read_text(encoding="utf-8"))["rows"]
print("cases", len(rows), "min plan A margin [bar]", round(min(r["min_planA_margin_bar"] for r in rows), 3))
by_f = defaultdict(list)
by_u = defaultdict(list)
for r in rows:
    by_f[(r["leg"], r["F_kN"])].append(r)
    by_u[(r["leg"], r["U_mm_s"])].append(r)
print("\nleg F[kN]: n, max excess [bar] / [kN] at a HOLD read, its p_r0, p_h0, U, window_ms; "
      "start excess of that case")
for key in sorted(by_f):
    sel = by_f[key]
    w = max(sel, key=lambda r: r["worst_hold_read"]["excess_bar"])
    pos = sum(r["worst_hold_read"]["excess_bar"] > 0 for r in sel)
    print(key, len(sel), "positive", pos, round(w["worst_hold_read"]["excess_bar"], 2),
          round(w["worst_hold_read"]["excess_kN"], 2), w["p_r0_bar"], w["p_h0_bar"], w["U_mm_s"],
          w["window_ms"], round(w["start_excess_bar"], 2))
print("\nleg U[mm/s]: n, positive, max excess bar/kN, window ms range, n_ret max, decay s range")
for key in sorted(by_u):
    sel = by_u[key]
    w = max(sel, key=lambda r: r["worst_hold_read"]["excess_bar"])
    print(key, len(sel), sum(r["worst_hold_read"]["excess_bar"] > 0 for r in sel),
          round(w["worst_hold_read"]["excess_bar"], 2), round(w["worst_hold_read"]["excess_kN"], 2),
          "F", w["F_kN"], "p_r0", w["p_r0_bar"],
          [min(r["window_ms"] for r in sel), max(r["window_ms"] for r in sel)],
          max(r["n_ret"] for r in sel),
          [round(min(r["decay_to_model_s"] for r in sel), 3),
           round(max(r["decay_to_model_s"] for r in sel), 3)])
# false-OK for F_min: F_true < F_min while F_true + excess*A_ann >= F_min (plan-A-free 11b)
F_MIN = 9.415
fo = [r for r in rows if r["F_kN"] < F_MIN and r["F_kN"] + r["worst_hold_read"]["excess_kN"] >= F_MIN]
print("\nF_true < F_min but retract-model F_lb >= F_min:", len(fo), "of",
      sum(r["F_kN"] < F_MIN for r in rows))
for r in sorted(fo, key=lambda r: -r["worst_hold_read"]["excess_kN"])[:6]:
    print("  ", r["leg"], r["F_kN"], r["p_r0_bar"], r["p_h0_bar"], r["U_mm_s"],
          round(r["worst_hold_read"]["excess_kN"], 2))
A_ANN = {"front": 0.00376991118, "rear": 3.14159265e-3}
print("\nplan A over-conservatism at the first HOLD read (p_r0 + delta - p_tr) [kN]: leg F -> "
      "min / median / max; false-low (F_true >= F_min, F_true - over < F_min) count")
for key in sorted(by_f):
    sel = by_f[key]
    over = sorted(r["first_hold"]["planA_margin_bar"] * A_ANN[key[0]] * 100 for r in sel)
    fl = sum(key[1] >= F_MIN and key[1] - o < F_MIN for o in over)
    print(key, round(over[0], 2), round(over[len(over) // 2], 2), round(over[-1], 2), "false-low", fl,
          "of", len(over))
print("\np_r0 <= 60 bar subset: leg F -> max excess bar/kN (U, p_r0)")
for key in sorted(by_f):
    sel = [r for r in by_f[key] if r["p_r0_bar"] <= 60.0]
    if not sel:
        continue
    w = max(sel, key=lambda r: r["worst_hold_read"]["excess_bar"])
    print(key, len(sel), round(w["worst_hold_read"]["excess_bar"], 2),
          round(w["worst_hold_read"]["excess_kN"], 2), w["U_mm_s"], w["p_r0_bar"],
          "start", round(w["start_excess_bar"], 2))
