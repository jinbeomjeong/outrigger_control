"""h05: which sensitivity keys warn per setting (case / twin F_s), from h03_rows.csv (read only).

Output: h05_out.txt
"""
import csv
import os
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8")))
keys = defaultdict(lambda: defaultdict(set))
allkeys = defaultdict(set)
for r in rows:
    allkeys[r["setting"]].add(r["key"])
    if r["round_warn_ratio"] != "":
        keys[r["setting"]][r["key"]].add((r["round"], r["round_warn_ratio"]))
lines = []
for s in sorted(allkeys):
    lines.append(f"== {s}: keys {len(allkeys[s])}, warning keys {len(keys[s])}")
    fs = defaultdict(lambda: [0, 0])
    for k in allkeys[s]:
        tag = k.split("|")[-1] if "Fs" in k else "noTwin"
        fs[tag][0] += 1
        fs[tag][1] += k in keys[s]
    lines.append("   by twin tag (keys, warning keys): " + ", ".join(f"{a} {b}" for a, b in sorted(fs.items())))
    for k in sorted(keys[s]):
        lines.append(f"   {k}: {sorted(keys[s][k])}")
with open(os.path.join(OUT, "h05_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print(len(lines))
