"""Which pairs change M3 by more than 2 kN in the gyro-free arms, are they the same across A-k / B-k / B-r, and
where do the event sequences of R0 and B-k first differ (name and time)?"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

d = Path(sys.argv[1])
pairs = list(csv.DictReader(open(d / "imuatt_pairs.csv", encoding="utf-8")))
sets = defaultdict(set)
for p in pairs:
    if p["d_M3_kN"] and abs(float(p["d_M3_kN"])) > 2.0:
        sets[p["arm"]].add((p["level"], p["seed_index"], p["case_id"], "-" if float(p["d_M3_kN"]) < 0 else "+"))
for arm, s in sorted(sets.items()):
    print(arm, len(s))
ak, bk, br = sets["A-k"], sets["B-k"], sets["B-r"]
print("A-k == B-k", ak == bk, "|A-k & B-k|", len(ak & bk), "|B-k & B-r|", len(bk & br))
print("groups", Counter(k[2].split("|")[0] for k in bk), "levels", Counter(k[0] for k in bk))
print("case families", Counter("|".join(k[2].split("|")[:3]) for k in bk).most_common(12))

lines = {}
for path in sorted(d.glob("imuatt_*_*.jsonl")):
    if not any(a in path.name for a in ("_R0_", "_B-k_", "_C-k_")):
        continue
    for text in path.read_text(encoding="utf-8").splitlines():
        if text.strip():
            ln = json.loads(text)
            lines[(ln["arm"], ln["level"], str(ln["seed_index"]), ln["case_id"])] = ln

skip = ("WARN_GYRO_BIAS", "INFO_GYRO_BIAS", "INFO_D1_IMU_MASS_SOURCE")
first_diff = Counter()
examples = []
for lv, s, cid, sign in sorted(bk):
    r0 = [e[1] for e in lines[("R0", lv, s, cid)]["events"] if not e[1].startswith(skip)]
    b = [e[1] for e in lines[("B-k", lv, s, cid)]["events"] if not e[1].startswith(skip)]
    t0 = [e[0] for e in lines[("R0", lv, s, cid)]["events"] if not e[1].startswith(skip)]
    i = next((j for j, (x, y) in enumerate(zip(r0, b)) if x != y), min(len(r0), len(b)))
    tag = (r0[i] if i < len(r0) else "<end>").split(":")[0] + " | " + (b[i] if i < len(b) else "<end>").split(":")[0]
    first_diff[tag] += 1
    if len(examples) < 8:
        examples.append((lv, s, cid, sign, i, t0[i] if i < len(t0) else None, tag,
                         lines[("R0", lv, s, cid)]["run_metrics"]["M3_kN"],
                         lines[("B-k", lv, s, cid)]["run_metrics"]["M3_kN"]))
print("first differing event (R0 | B-k):", first_diff.most_common(10))
for e in examples:
    print(e)
# commands identical before TOUCH? compare t_touch and TOUCH duration
dt = Counter()
for lv, s, cid, sign in sorted(bk):
    a = lines[("R0", lv, s, cid)]["run_metrics"]
    b = lines[("B-k", lv, s, cid)]["run_metrics"]
    dt[(round((b["t_touch_start_s"] or 0) - (a["t_touch_start_s"] or 0), 1), sign)] += 1
print("t_touch shift (B-k - R0), sign of dM3:", dt.most_common(10))
