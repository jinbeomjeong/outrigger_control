"""Item 9 (pressure-only J_P vs combined J_C) table over several S8 batches (read only).

For every case with item-9 rows: F_s, closed-loop judge (contact), per judge
[M1 missed, M1' late, M3 median, M2, M4 max] and episode count, and M5 closed loop.
Then sums by (F_s, closed-loop judge) and the paired closed-loop table (N vs E).
Usage: python -I s8rest_item9.py <out_json> <verify_json> [<verify_json> ...]
"""
import json
import re
import sys
from collections import defaultdict


def fs_of(meta, case):
    s8 = meta.get(case, {}).get("s8", {})
    if "fs_kN" in s8:
        return s8["fs_kN"]
    m = re.search(r"Fs(\d+)", case)
    return float(m.group(1)) if m else None


out = {"cases": {}, "sums": {}}
for path in sys.argv[2:]:
    v = json.load(open(path, encoding="utf-8"))
    meta = v.get("s8_metrics", {})
    batch = v["meta"]["batch"]
    for r in v["rows"]:
        if not r["item"].startswith("item 9"):
            continue
        case = r["case"]
        rec = out["cases"].setdefault(case, {"batch": batch, "fs_kN": fs_of(meta, case),
                                             "contact": meta.get(case, {}).get("s8", {}).get("contact"),
                                             "event": meta.get(case, {}).get("s8", {}).get("event")})
        if r["item"].startswith("item 9 M5"):
            rec["M5"] = r["value"]
        else:
            m = re.search(r"episodes (\d+) \(crawler_transient (\d+)\)", r["note"] or "")
            rec[r["judge"]] = {"value": r["value"],
                               "episodes": int(m.group(1)) if m else None,
                               "transient": int(m.group(2)) if m else None}
# sums: episodes and misses per (F_s, closed-loop contact, judge)
sums = defaultdict(lambda: {"cases": 0, "episodes": 0, "M1": 0, "M1p": 0, "M2": 0})
for case, rec in out["cases"].items():
    for judge in ("J_P", "J_C"):
        if judge not in rec:
            continue
        key = f"Fs{rec['fs_kN']:g}|{rec['contact']}|{judge}"
        s = sums[key]
        val = rec[judge]["value"]
        s["cases"] += 1
        s["episodes"] += rec[judge]["episodes"] or 0
        s["M1"] += val[0] or 0
        s["M1p"] += val[1] or 0
        s["M2"] += val[3] or 0
out["sums"] = dict(sorted(sums.items()))
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("case | Fs | contact | event | J_P [M1,M1',M3,M2,M4] ep | J_C [...] ep | M5 [min,under,lift]")
for case, rec in sorted(out["cases"].items(), key=lambda kv: (kv[1]["event"] or "", kv[1]["fs_kN"] or 0, kv[0])):
    if not rec.get("event") and not case.startswith("N_"):
        continue
    def fmt(j):
        if j not in rec:
            return "-"
        v = rec[j]["value"]
        return "[" + ",".join("-" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x)) for x in v) + f"] ep{rec[j]['episodes']}"
    m5 = rec.get("M5")
    m5s = "-" if m5 is None else ",".join("-" if x is None else f"{x:.2f}" for x in m5)
    print(f"{case:32s} {rec['fs_kN']:>4} {str(rec['contact']):9s} {str(rec['event']):6s} | {fmt('J_P'):38s} | {fmt('J_C'):38s} | {m5s}")
print("\nsums (all cases with item-9 rows, incl. D8):")
for k, s in out["sums"].items():
    print(f"  {k:28s} {s}")
