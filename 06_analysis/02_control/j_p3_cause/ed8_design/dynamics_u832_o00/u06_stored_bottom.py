"""Stored edition 6 (VBL grid) / edition 7 (VBM G1) lines of the bottom RE1bF / FS24 ready
clusters: pair lift intervals and re-approach starts (from the u01 scans).

Usage: python -I -B u06_stored_bottom.py <folder>
"""
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 120)
folder = Path(sys.argv[1])
d = pd.concat([pd.read_csv(folder / "u01_scan_ed6.csv").assign(ed=6),
               pd.read_csv(folder / "u01_scan_ed7.csv").assign(ed=7)], ignore_index=True)
s = d[(d["level"] == "bottom") & (d["timing"] == "ready") & d["event"].isin(["RE1bF", "FS24"])
      & d["src"].isin(["ed6_grid", "g1"])].copy()
legs = ("FL", "FR", "RL", "RR")


def pair_detail(r):
    out = []
    for leg in str(r["pair"]).split("+"):
        if leg in legs and pd.notna(r.get(f"{leg}_first_s")):
            out.append(f"{leg}({r[f'{leg}_first_s']},{r[f'{leg}_sum_s']},{r[f'{leg}_last_touch_s']},"
                       f"n{int(r[f'{leg}_n'])})")
    return " ".join(out)


s["pair_lifts(first,sum,last,n)"] = s.apply(pair_detail, axis=1)
cols = ["ed", "setting", "event", "leg", "fs_kN", "offset_s", "pass", "failed_gates", "pair_union_s",
        "pair_last_touch_s", "pair_lifts(first,sum,last,n)", "reapproach_starts"]
s = s.sort_values(["event", "leg", "fs_kN", "ed", "offset_s"])
print(s[cols].to_string(index=False))
s[cols].to_csv(folder / "u06_stored_bottom_ready.csv", index=False)
