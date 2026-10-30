"""H-6 gap margin check: final-harness soft (J1/J2/S1) slope rows with verdict pass and READY gap < 25 + margin.

Reads finB2_harness_rejudged.json, finB2_h9.json, finB2_x426b_rejudged.json (read-only). Prints JSON to stdout and
writes <out json>.
Usage: python -I gap_rows.py <rev85 dir> <out json>
"""
import json
import sys
from collections import Counter
from pathlib import Path

R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
FILES = ("finB2_harness_rejudged.json", "finB2_h9.json", "finB2_x426b_rejudged.json")
SOFT = ("J1", "J2", "S1")
DIRS = ("nose_down", "nose_up", "roll_pos", "roll_neg", "edge_nd", "edge_nu", "rpB")
P35 = 25.0


def soil(i):
    p = i.split("|")
    return p[1] if len(p) > 1 else ""


def is_slope(i):
    return any(d in i for d in DIRS) and "flat" not in i


rows, seen = [], set()
suites = Counter()
for fn in FILES:
    d = json.loads((R / fn).read_text(encoding="utf-8"))
    for r in d["records"]:
        i = r["id"]
        suites[(fn, r.get("suite"), is_slope(i), soil(i))] += 1
        if soil(i).split("+")[0] not in SOFT or not is_slope(i):
            continue
        key = (i, r.get("candidate"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"file": fn, "id": i, "candidate": r.get("candidate"), "verdict": r.get("verdict"),
                     "gap_mm": r.get("rut_ready_mm"), "stroke_mm": r.get("max_stroke_mm"),
                     "t_ready_s": r.get("t_ready_s")})
pas = [r for r in rows if r["verdict"] == "pass" and r["gap_mm"] is not None]
out = {"definition": "soft J1/J2/S1 slope rows (id has a slope direction, not 'flat'), final harness, verdict pass; "
                     "gap = rut_ready_mm; boundary if gap - 25 mm < margin",
       "n_slope_rows": len(rows), "n_slope_pass": len(pas),
       "verdicts": dict(Counter(r["verdict"] for r in rows)),
       "gap_min_pass_mm": min(r["gap_mm"] for r in pas)}
for m in (13.0, 15.0):
    b = sorted([r for r in pas if r["gap_mm"] - P35 < m], key=lambda r: r["gap_mm"])
    out[f"boundary_m{int(m)}"] = {"n": len(b), "rows": b}
new = [r for r in pas if 13.0 <= r["gap_mm"] - P35 < 15.0]
out["new_between_13_15"] = sorted(new, key=lambda r: r["gap_mm"])
also_stroke = [r for r in out["boundary_m15"]["rows"] if r["stroke_mm"] is not None and 682.8 - r["stroke_mm"] < 23.0]
out["boundary_m15_also_stroke_boundary"] = [r["id"] for r in also_stroke]
out["suite_counts"] = [list(k) + [v] for k, v in sorted(suites.items(), key=str)]
OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "suite_counts"}, default=float, indent=0)[:6000])
