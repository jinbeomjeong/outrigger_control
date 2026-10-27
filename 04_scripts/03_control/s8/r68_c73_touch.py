"""C-S8-73 TOUCH trace of the pre-grounded leg (spec rev. 68, 353.5).

For each PS-7 case of the L1-R batch: 10 Hz controller series inside TOUCH for the pre-grounded
leg (issued command, 'touched' latch, load estimate F_hat, lower bound F_lower) and the recorded
true pad contact force / stroke, plus the stroke split into 'before the cap event', 'cap .. +2 s'
and 'later' (the second extension). Times relative to the TOUCH start [s], mm, kN, mm/s.

Usage: python -I r68_c73_touch.py <batch dir> <c73_vs_c72 table json> <out json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def main() -> None:
    batch, table_p, out_p = (Path(a) for a in sys.argv[1:4])
    table = json.loads(table_p.read_text(encoding="utf-8"))
    out = {}
    for case, row in table.items():
        if not (case.startswith("PS7") and isinstance(row, dict) and "c73" in row):
            continue  # table meta keys
        c73 = row["c73"]
        leg = case.split("_")[1]
        j = LEGS.index(leg)
        d = batch / case
        r8 = np.load(d / "r8_series.npz")
        rec = np.load(d / "record" / "record.npz")
        t0, t1 = c73["touch_span_s"]
        cap_t = c73["cap_events"][0][0] if c73["cap_events"] else None
        # the series clocks: r8 / record share the engine clock; find the offset from the
        # TOUCH phase label (first 'touch' sample) to stay independent of start_t_s
        ph = np.array([str(p) for p in r8["phase"]])
        k_touch = np.flatnonzero(np.char.lower(ph) == "touch")
        tc = r8["t"]
        off = float(tc[k_touch[0]]) - t0 if k_touch.size else 0.0
        trel = tc - off - t0
        tr = rec["t"] - off - t0
        s = rec["stroke_true"][:, j] * 1e3
        s0 = float(np.interp(0.0, tr, s))
        rows = []
        for k in np.flatnonzero((trel >= -0.05) & (trel <= (t1 - t0) + 0.05)):
            i = int(np.argmin(np.abs(tr - trel[k])))
            rows.append([round(float(trel[k]), 2), ph[k], round(float(r8["issued_u"][k, j]) * 1e3, 2),
                         round(float(r8["touched"][k, j]), 2),
                         round(float(rec["meas.head_pressure"][i, j]) / 1e5, 1),
                         round(float(r8["cmp_reapproach_u"][k, j]) * 1e3 + float(r8["cmp_guard_u"][k, j]) * 1e3, 2),
                         round(float(rec["F_contact_n"][i, j]) / 1e3, 2), round(float(s[i] - s0), 2)])
        cap_rel = None if cap_t is None else cap_t - t0

        def ds(a: float, b: float) -> float:
            return round(float(np.interp(b, tr, s) - np.interp(a, tr, s)), 2)

        latch = c73["latch_pre_leg_s"]
        split = {"cap_rel_s": cap_rel, "latch_rel_s": latch,
                 "stroke_0_to_cap_mm": None if cap_rel is None else ds(0.0, cap_rel),
                 "stroke_cap_to_cap+2_mm": None if cap_rel is None else ds(cap_rel, cap_rel + 2.0),
                 "stroke_cap+2_to_latch_mm": None if cap_rel is None else ds(cap_rel + 2.0, latch),
                 "stroke_total_to_latch_mm": ds(0.0, latch)}
        out[case] = {"leg": leg, "clock_offset_s": off, "split": split,
                     "cols": ["t_rel", "phase", "u_mm_s", "touched", "head_reading_bar", "reapp+guard_mm_s",
                              "pad_N_true_kN", "stroke_from_touch_mm"], "rows": rows}
        print("==", case, split)
        for r in rows[::5]:
            print("  ", r)
    out_p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
