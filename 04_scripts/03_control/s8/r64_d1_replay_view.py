"""Summary of r64_d1_replay.py per batch: faults A / B / C, step-reason totals, new event kinds, fidelity.

Usage: python -I r64_d1_replay_view.py <json> [--list]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

d = json.load(open(sys.argv[1], encoding="utf-8"))
roots = [Path(r).name for r in d["meta"]["roots"]]


def batch_of(case):
    for r in roots:
        if r in case:
            return r
    return "?"


agg = defaultdict(lambda: defaultdict(Counter))
lists = defaultdict(list)
for r in d["runs"]:
    b = batch_of(r["case"])
    a = agg[b]
    if "skip" in r:
        a["n"]["skip:" + r["skip"][:30]] += 1
        continue
    a["n"]["cases"] += 1
    a["n"]["has_loc"] += r["has_loc"]
    for v in ("A", "B", "C", "recorded"):
        if v in r:
            a[v]["fault_cases"] += r[v]["first_fault"] is not None
            for k, c in r[v]["counts"].items():
                a[v][k] += c
    fa, fb = r["A"]["first_fault"], r["B"]["first_fault"]
    fr = r["recorded"]["first_fault"]
    if fb is not None and fa is None:
        a["n"]["B_new_fault"] += 1
        lists["B_new_fault"].append((r["case"], fb))
    if fa is not None and fb is None:
        a["n"]["B_removed_fault"] += 1
        lists["B_removed_fault"].append((r["case"], fa, fr))
    if "C" in r and r["C"]["first_fault"] is not None and fa is None:
        a["n"]["C_new_fault"] += 1
        lists["C_new_fault"].append((r["case"], r["C"]["first_fault"]))
    if (fa is None) != (fr is None):
        a["n"]["A_vs_rec_fault_differs"] += 1
        lists["A_vs_rec"].append((r["case"], fa, fr))
    if (fb is None) != (fr is None):
        a["n"]["B_vs_rec_fault_differs"] += 1
    if r["B_only"] or r["A_only"]:
        a["n"]["step_set_differs"] += 1
for b, a in agg.items():
    print("==", b)
    for k, c in a.items():
        print(f"   {k:9s}", dict(c))
if "--list" in sys.argv:
    for k, v in lists.items():
        print("--", k, len(v))
        for x in v[:40]:
            print("   ", x)
