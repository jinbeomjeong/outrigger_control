"""Per-step target tangential rise and residual ratio from s6r17 outputs (spec rev. 18). kN."""
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
HERE = Path(__file__).resolve().parent
fn = sys.argv[1] if len(sys.argv) > 1 else "s6r17_partO.json"
filt = sys.argv[2] if len(sys.argv) > 2 else "|base|"
d = json.loads((OUT_DIR / fn).read_text(encoding="utf-8"))
LEGS = ("FL", "FR", "RL", "RR")
for r in d["runs"]:
    if filt not in r["id"] or "error" in r:
        continue
    x = r["x"]
    st = x["Ft_start_kN"]; fin = x["Ft_final_kN"]
    ratio = [round(f / s, 2) for f, s in zip(fin, st)]
    line = [f"{r['id']}: Ft start {st} final {fin} ratio {ratio} min {r['min_true_cyl_force_kN']}"]
    targets = [s["leg"] for s in x.get("steps", [])]
    for k, p in enumerate(x.get("step_pairs", [])):
        tg = targets[k] if k < len(targets) else None
        if tg is None:
            continue
        i = LEGS.index(tg)
        line.append(f"   k{k} {tg}: Ft_max {p['Ft_max_kN'][i]} (N {p['Fl_at_Ft_max_kN'][i]}) vs start {st[i]}; "
                    f"others Ft_max {[p['Ft_max_kN'][j] for j in range(4) if j != i]}")
    print("\n".join(line))
