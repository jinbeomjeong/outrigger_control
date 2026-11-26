"""Proposed U832 signature on the stored edition 6 grid / edition 7 G1 lines (post-result check).

Signature (all): fast event; false gates exactly {U832_pair_union}; 1.8 < pair_union_s <= 2.1;
the diagonal leg of the event leg starts a re-approach at t - t_ev <= 0.5 s (early hand-over).
The V0-pair condition is not checked here (the scans hold the treatment lines only).

Usage: python -I -B u15_signature_check.py <folder>
"""
import json
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250)
folder = Path(sys.argv[1])
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
d = pd.concat([pd.read_csv(folder / "u01_scan_ed6.csv").assign(ed=6),
               pd.read_csv(folder / "u01_scan_ed7.csv").assign(ed=7)], ignore_index=True)
d = d[d["src"].isin(["ed6_grid", "g1"]) & d["event"].isin(["RE1bF", "FS24"])].copy()


def diag_start(r):
    starts = json.loads(r["reapproach_starts"]) if isinstance(r["reapproach_starts"], str) else []
    t = [s for s, leg in starts if leg == DIAG.get(r["leg"])]
    return min(t) if t else None


d["diag_start_s"] = d.apply(diag_start, axis=1)
d["only_u832"] = d["failed_gates"].fillna("") == "U832_pair_union"
d["sig"] = d["only_u832"] & (d["pair_union_s"] > 1.8) & (d["pair_union_s"] <= 2.1) & \
    d["diag_start_s"].notna() & (d["diag_start_s"] <= 0.5)
fails = d[d["failed_gates"].fillna("").str.contains("U832")]
print(fails[["ed", "level", "leg", "fs_kN", "event", "timing", "offset_s", "failed_gates", "pair_union_s",
             "diag_start_s", "sig"]].to_string(index=False))
print("\nU832 failures:", len(fails), "signature:", int(fails["sig"].sum()))
early = d[d["diag_start_s"].notna() & (d["diag_start_s"] <= 0.5)]
print("lines with early hand-over (diag start <= 0.5 s):", len(early), "of", len(d),
      "; their pair union max", early["pair_union_s"].max())
print(early.groupby(["ed", "level", "event", "timing"])["pair_union_s"].agg(["count", "min", "max"]).to_string())
fails.to_csv(folder / "u15_signature_check.csv", index=False)
