"""D8 576 summary (spec rev. 26). Usage: python -I s6r26_d8report.py <json>. kN / s / deg."""
import json
import sys
from collections import defaultdict
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
runs = d["runs"]
G = 14.4146
ok = [r for r in runs if "error" not in r]
print("wall", d["wall_s"], "n", len(runs), "errors", len(runs) - len(ok))
mins = [r.get("min_true_cyl_force_substep_kN") for r in ok]
print("min true", min(mins), "below guard", sum(m < G for m in mins), "fails", sum(bool(r.get("fails")) for r in ok),
      "fail kinds", sorted({f for r in ok for f in (r.get("fails") or [])}))
print("ss att max", max(r.get("ss_true_att_deg_maxabs") or 0 for r in ok), "t_ready max",
      max(r.get("t_ready_s") or 0 for r in ok), "not ready", sum(r.get("t_ready_s") is None for r in ok),
      "pmax", max(r.get("max_pressure_bar") or 0 for r in ok))
g = defaultdict(list)
for r in ok:
    g[r["id"].split("|")[0]].append(r)
for k, L in sorted(g.items()):
    m = min(L, key=lambda r: r["min_true_cyl_force_substep_kN"])
    print(k, len(L), m["min_true_cyl_force_substep_kN"], m["id"], "t_ready max", max(r.get("t_ready_s") or 0 for r in L))
