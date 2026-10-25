"""Tables of s6r26_S.json (spec rev. 25). kN / s / deg."""
import json
from collections import defaultdict
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
d = json.loads((OUT_DIR / "s6r26_S.json").read_text(encoding="utf-8"))
runs = d["runs"]
print("wall", d["wall_s"], "n", len(runs), "errors", [(r.get("id"), r["error"]) for r in runs if "error" in r][:3])
G = 14.4146
g = defaultdict(list)
for r in runs:
    if "error" in r:
        continue
    p = r["id"].split("|")
    g[(p[0], p[1], p[2])].append(r)
print("group|rate|slope -> n, min true, below guard, fails, t_touch range, t_ready max, ss att max, pmax bar")
for k in sorted(g):
    L = g[k]
    mins = [r.get("min_true_cyl_force_substep_kN", r.get("min_true_cyl_force_kN")) for r in L]
    tt = [r.get("t_touch_s") for r in L if r.get("t_touch_s")]
    tr = [r.get("t_ready_s") for r in L if r.get("t_ready_s")]
    ss = [r.get("ss_true_att_deg_maxabs") for r in L if r.get("ss_true_att_deg_maxabs") is not None]
    pm = [r.get("max_pressure_bar") for r in L if r.get("max_pressure_bar") is not None]
    fails = sorted({f for r in L for f in (r.get("fails") or [])})
    extra = ""
    if k[0] == "H":
        ra = [r["x"].get("min_true_ra_kN") for r in L]
        ft = [max(r["x"]["Ft_final_kN"]) for r in L]
        gaps = [s["gap_kN"] for r in L for s in r["x"].get("steps", [])]
        stops = [s["P_stop_reading_kN"] for r in L for s in r["x"].get("steps", [])]
        extra = f" RA min {min(ra)} Ft_end max {max(ft)} gap max {max(gaps)} stop reading min {min(stops)}"
    print(k, len(L), round(min(mins), 2), sum(m < G for m in mins), fails, [min(tt), max(tt)] if tt else None,
          max(tr) if tr else None, round(max(ss), 4) if ss else None, max(pm) if pm else None,
          "not_ready", sum(r.get("t_ready_s") is None for r in L), extra)
