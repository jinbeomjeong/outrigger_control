"""Copy the rev. 17 scratchpad outputs into 06_analysis/02_control with the project script names; part F is filtered
out of the combined 'all' file. Then (--compare) compare a fresh project run of part O with the copied file."""
import json
import sys
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
SRC = OUT_DIR
DST = (REPO / r"06_analysis\02_control")
if "--compare" in sys.argv:
    a = json.loads((SRC / "s6r17_partO.json").read_text(encoding="utf-8"))
    b = json.loads((DST / "h4_fs_order_check_O.json").read_text(encoding="utf-8"))
    ra = {r["id"]: r for r in a["runs"]}; rb = {r["id"]: r for r in b["runs"]}
    diff = 0
    for k in ra:
        for key in ("min_true_cyl_force_kN", "t_ready_s"):
            if ra[k].get(key) != rb[k].get(key):
                diff += 1
        if ra[k]["x"].get("step_pairs") != rb[k]["x"].get("step_pairs") or ra[k]["x"].get("Ft_final_kN") != rb[k]["x"].get("Ft_final_kN"):
            diff += 1
    print("ids", len(ra), len(rb), "same ids", set(ra) == set(rb), "differences", diff)
    sys.exit(0)
d = json.loads((SRC / "s6r17_h4_fs_order.json").read_text(encoding="utf-8"))
runs = [r for r in d["runs"] if r["id"].startswith("F|")]
meta = dict(d["meta"], part="F", n=len(runs), source="scratchpad s6r17_h4_fs_order.json (rev. 17 run, filtered to part F)",
            script="04_scripts/03_control/run_h4_fs_order_check.py (scratchpad original s6r17_h4_fs_order.py)")
(DST / "h4_fs_order_check_F.json").write_text(json.dumps({"meta": meta, "runs": runs}, indent=1), encoding="utf-8")
for p in ("O", "O2"):
    e = json.loads((SRC / f"s6r17_part{p}.json").read_text(encoding="utf-8"))
    e["meta"].update(part=p, source=f"scratchpad s6r17_part{p}.json (rev. 17 run)",
                     script="04_scripts/03_control/run_h4_fs_order_check.py (scratchpad original s6r17_h4_fs_order.py)")
    (DST / f"h4_fs_order_check_{p}.json").write_text(json.dumps(e, indent=1), encoding="utf-8")
print("copied F", len(runs))
