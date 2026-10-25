"""Part O per-step pairs (spec rev. 17). Rear legs RL / RR (+ FL); kN."""
import json
import sys
# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
PART = sys.argv[1] if len(sys.argv) > 1 else "O"
from pathlib import Path

d = json.loads((OUT_DIR / ("s6r17_part" + PART + ".json")).read_text(encoding="utf-8"))
L = {"FL": 0, "RL": 2, "RR": 3}
for r in sorted(d["runs"], key=lambda r: (r["id"].split("|")[2], r["id"].split("|")[4], r["id"].split("|")[1])):
    _, vn, tag, _, km, _, _ = r["id"].split("|")
    x = r["x"]
    head = f"{tag:12s} {km:4s} {vn:10s} min {r['min_true_cyl_force_kN']:6.2f} dur {x['duration_s']:5.2f} Ftfin RL/RR {x['Ft_final_kN'][2]}/{x['Ft_final_kN'][3]}"
    held = {lg: max((p["Fl_max_Ft_held_kN"][i] or 0) for p in x["step_pairs"]) for lg, i in L.items()}
    k0 = x["step_pairs"][0] if x["step_pairs"] else None
    s0 = " ".join(f"{lg}:{k0['Fl_max_kN'][i]}({k0['Ft_at_Fl_max_kN'][i]})" for lg, i in L.items()) if k0 else ""
    allmax = {lg: max(p["Fl_max_kN"][i] for p in x["step_pairs"]) for lg, i in L.items()}
    print(head, "| Fl_max while Ft held", held, "| step0 Fl(Ft)", s0, "| Fl max all", allmax)
