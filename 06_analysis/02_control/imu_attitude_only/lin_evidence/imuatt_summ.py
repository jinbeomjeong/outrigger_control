"""Summarise imuatt_lin.py output: per variant worst channel M_s, attitude PM / GM / delay margin, guard M_s."""
import json
import math
import sys

data = json.load(open(sys.argv[1]))
rows = data["results"]
errs = [r for r in rows if "error" in r]
print("errors", len(errs))
out = {}
for v in data["variants"]:
    nog = [r for r in rows if r["variant"] == v and r["guard_leg"] < 0 and "error" not in r]
    g = [r for r in rows if r["variant"] == v and r["guard_leg"] >= 0 and "error" not in r]
    if not nog:
        continue
    w = max(nog, key=lambda r: r["Ms_max"])
    att = [(r[ch], r["plant"], ch) for r in nog for ch in ("phi", "theta")]
    pm = min((a[0]["PM"] for a in att if a[0]["PM"] is not None), default=None)  # primary crossing
    dm = min((a[0]["DM"] for a in att if a[0]["DM"] is not None), default=None)
    gm = min((a[0]["GMup"] for a in att if a[0]["GMup"] is not None), default=None)
    wgc = [a[0]["wgc"] for a in att if a[0]["wgc"] is not None]
    att_ms = max(att, key=lambda a: a[0]["Ms"])
    s = {"n": len(nog), "Ms_worst": round(w["Ms_max"], 4), "Ms_worst_where": f'{w["plant"]} {w["Ms_ch"]}',
         "Ms_over_1.5": sum(r["Ms_max"] > 1.5 for r in nog),
         "att_Ms_worst": round(att_ms[0]["Ms"], 4), "att_Ms_where": f"{att_ms[1]} {att_ms[2]}",
         "att_w_Ms": round(att_ms[0]["w_Ms"], 3),
         "att_PM_min_deg": None if pm is None else round(pm, 2),
         "att_GM_min": None if gm is None else round(gm, 3),
         "att_GM_min_dB": None if gm is None or not math.isfinite(gm) else round(20 * math.log10(gm), 2),
         "att_DM_min_s": None if dm is None else round(dm, 3),
         "att_wgc_range": [round(min(wgc), 4), round(max(wgc), 4)] if wgc else None,
         "rho_max": round(max(r["rho"] for r in nog), 6)}
    if g:
        gw = max(g, key=lambda r: r["Ms_max"])
        s["guard_Ms_worst"] = round(gw["Ms_max"], 4)
        s["guard_where"] = f'{gw["plant"]} leg{gw["guard_leg"]} {gw["Ms_ch"]}'
        s["guard_n"] = len(g)
    out[v] = s
for v, s in out.items():
    print(v, json.dumps(s))
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), indent=1)
