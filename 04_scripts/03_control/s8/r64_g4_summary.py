"""Pass counts of r64_g4_closed_loop.py per case x variant (4 start phases each) and the two-path totals.

Usage: python -I r64_g4_summary.py <json>
"""
import json
import sys
from collections import defaultdict

d = json.load(open(sys.argv[1], encoding="utf-8"))
cnt = defaultdict(lambda: defaultdict(int))
two = defaultdict(lambda: [0, 0])
for r in d["runs"]:
    for vname, v in r["variants"].items():
        j = v["judge"]
        c = cnt[(r["case"], vname)]
        c["n"] += 1
        for k in ("G4_1", "G4_2", "G4_3", "G4_4", "G4_4_mean05", "G4_5", "G4_6"):
            c[k] += bool(j.get(k))
        c["G4_7"] += bool(j.get("G4_7_bit_identical"))
        m = v["meta_run"] or {}
        c["end:" + str(m.get("end_reason"))] += 1
        tp = v.get("two_path")
        if tp is not None:
            two[vname][0] += 1
            two[vname][1] += bool(tp["same"])
    c = cnt[(r["case"], "OFF")]
    c["n"] += 1
    c["G4_4"] += bool(r["off"]["G4_4"])
    c["G4_4_mean05"] += bool(r["off"].get("G4_4_mean05"))
for (case, vname), c in cnt.items():
    print(f"{case:14s} {vname:28s} " + " ".join(f"{k}={v}" for k, v in c.items()))
print("two-path (python meta vs independent state machine, same inputs):",
      {k: f"{v[1]}/{v[0]}" for k, v in two.items()})
