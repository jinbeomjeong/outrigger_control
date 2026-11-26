"""h11: key numbers for the report (read only, from h03_rows.csv): retract need of the plant at the
probe retract opening, net stroke after the probe, extend fill and mid-read order per setting.

Output: h11_key_numbers.json
"""
import csv
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8"))
        if r["reversed"] == "False"]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def q(v):
    v = np.array(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    p = np.percentile(v, [5, 50, 95])
    return {"n": int(len(v)), "p05": round(float(p[0]), 3), "med": round(float(p[1]), 3),
            "p95": round(float(p[2]), 3), "min": round(float(v.min()), 3),
            "max": round(float(v.max()), 3)}


res = {}
SETS = ["sens:VBMh05", "sens:VBMfast", "j9main:VBM", "sens:VBMd15", "sens:VBMh15", "sens:VBMslow",
        "probe:P7-M-a2", "probe:P7-M-c2", "probe:P7-Mslow-a2", "probe:P7-Mslow-c2", "probe:P7-L-a2",
        "probe:P7-L-c2"]
for s in SETS:
    src, setting = s.split(":")
    sub = [r for r in rows if r["src"] == src and r["setting"] == setting]
    filled = [r for r in sub if r["x_open_mm"] != ""]
    after = [r for r in filled if r["open_after_mid"] == "True"]
    res[s] = {
        "windows": len(sub), "windows_line_filled": len(filled),
        "open_after_mid": len(after),
        "open_minus_mid_s": q([f(r["open_minus_mid_s"]) for r in filled]),
        "x_open_mm": q([f(r["x_open_mm"]) for r in filled]),
        "ds_mid_mm": q([f(r["ds_mid_mm"]) for r in filled]),
        "ret_need_mm": q([f(r["ret_need_mm"]) for r in sub]),
        "ret_open_share": round(float(np.mean([r["ret_open"] == "True" for r in sub])), 3),
        "net_stroke_after_mm": q([f(r["net_stroke_after_mm"]) for r in sub]),
        "ib_extra_mm": q([f(r["ib_extra_mm"]) for r in sub]),
        "d6_witness_mm": q([f(r["d6_witness_mm"]) for r in sub]),
    }
with open(os.path.join(OUT, "h11_key_numbers.json"), "w", encoding="utf-8", newline="\n") as fo:
    json.dump(res, fo, indent=1)
for s, v in res.items():
    print(s, v["windows"], v["open_after_mid"], v["x_open_mm"]["med"] if v["x_open_mm"] else None,
          v["ret_need_mm"], v["ret_open_share"], v["net_stroke_after_mm"]["med"])
