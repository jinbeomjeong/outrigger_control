"""F1 near-F_min record rows: value vs the old 0.1 kN flag and vs the R45-2 friction flag.

R45-2 calibration-friction flag = max(0.1 kN, 0.065 F_s,leg), F_s,leg = F_s (front),
0.8333 F_s (rear). Uses the worst leg in the row detail when present, else the front F_s.
Usage: python -I s8rest_nearfmin.py <verify_json> [...]
"""
import json
import sys

REAR = 0.8333
for path in sys.argv[1:]:
    v = json.load(open(path, encoding="utf-8"))
    s8m = v.get("s8_metrics", {})
    print("==", v["meta"]["batch"])
    for r in v["rows"]:
        if not r["item"].startswith("F1 near F_min"):
            continue
        case = r["case"]
        s8 = s8m.get(case, {}).get("s8", {})
        grade = s8.get("base", {}).get("scenario", {}).get("grade")
        fs = s8.get("fs_kN") or 0.0
        val = r["value"]
        vmax = max(val) if isinstance(val, list) else val
        if vmax is None:
            continue
        vmax = float(vmax)
        if vmax > 1e3:  # in N
            vmax = vmax / 1e3
        flag_front = max(0.1, 0.065 * fs)
        flag_rear = max(0.1, 0.065 * fs * REAR)
        if vmax > 0.1 or grade != "ideal":
            print(f"  {case:34s} grade {grade} Fs {fs:g} value {val} -> max {vmax:.3f} kN | old 0.1 flag {vmax > 0.1}"
                  f" | R45-2 flag front {flag_front:.3f} rear {flag_rear:.3f} -> over rear {vmax > flag_rear}, over front {vmax > flag_front}"
                  f" | note {str(r.get('note'))[:160]}")
