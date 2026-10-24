"""Summarise c2py_variants output per variant (S: D8 boundary 48, G: settlement 12).

Inputs: 06_analysis/02_control/r8_10hz/d1/v_all.json, v_pre.json (spec rev. 31 143, 145, 146).
"""
import json
import sys
from collections import defaultdict

rows = []
for f in sys.argv[1:]:
    rows += json.load(open(f))
by = defaultdict(list)
for r in rows:
    by[(r["variant"], r["id"][0])].append(r)
print("errors:", [(r["variant"], r["id"]) for r in rows if "error" in r][:5])
for (v, g), rs in sorted(by.items()):
    rs = [r for r in rs if "error" not in r]
    m = [r["metrics"] for r in rs]
    if g == "T":
        worst = min(rs, key=lambda r: r["metrics"]["min_true_cyl_force_kN"])
        tr = [x["t_ready_s"] for x in m if x["t_ready_s"] is not None]
        print(f"S {v:6s} n {len(rs)} minF {min(x['min_true_cyl_force_kN'] for x in m):6.2f} ({worst['id'][9:]}) "
              f"READY max/mean {max(tr):5.1f}/{sum(tr)/len(tr):5.1f} att {max(x['ss_true_att_deg_maxabs'] for x in m):.3f} "
              f"pmax {max(x['max_pressure_bar'] for x in m):.1f} fails {sum(bool(r['fails']) for r in rs)} notready {len(m)-len(tr)}")
    else:
        a = [x.get("min_true_after_sink_kN") for x in m]
        b16 = [x.get("min_true_after_sink_kN") for r, x in zip(rs, m) if "1.6e+09" in r["id"]]
        b10 = [x.get("min_true_after_sink_kN") for r, x in zip(rs, m) if "1e+09" in r["id"]]
        print(f"G {v:6s} n {len(rs)} after-sink min b1.0 {min(b10):.2f}..{max(b10):.2f} b1.6 {min(b16):.2f}..{max(b16):.2f} "
              f"final {min(x.get('final_true_kN') if not isinstance(x.get('final_true_kN'), list) else min(x['final_true_kN']) for x in m):.2f} fails {sum(bool(r['fails']) for r in rs)}")
# per-case paired differences vs base for S
base = {r["id"]: r for r in rows if r["variant"] == "base" and "error" not in r}
for v in sorted({r["variant"] for r in rows} - {"base"}):
    d = [r["metrics"]["min_true_cyl_force_kN"] - base[r["id"]]["metrics"]["min_true_cyl_force_kN"]
         for r in rows if r["variant"] == v and r["id"] in base and "error" not in r and r["id"].startswith("T|")]
    dt = [r["metrics"]["t_ready_s"] - base[r["id"]]["metrics"]["t_ready_s"]
          for r in rows if r["variant"] == v and r["id"] in base and "error" not in r and r["id"].startswith("T|")
          and r["metrics"]["t_ready_s"] and base[r["id"]]["metrics"]["t_ready_s"]]
    if d:
        print(f"  {v:6s} vs base: dminF {min(d):+.2f}..{max(d):+.2f} (mean {sum(d)/len(d):+.2f}) dREADY {min(dt):+.2f}..{max(dt):+.2f}")
