"""Rev. 18 tables: rear-pad lateral load (start / max during H4 / final) for O3 and S. kN."""
import json
import math
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
D = (REPO / r"06_analysis\02_control")
part = sys.argv[1]
d = json.loads((D / f"h4_fs_order_check_{part}.json").read_text(encoding="utf-8"))
LEGS = ("FL", "FR", "RL", "RR")
rows = []
for r in d["runs"]:
    if "error" in r:
        print("ERROR", r["id"], r["error"]); continue
    x = r["x"]
    st, mx, fin = x["Ft_start_kN"], x["Ft_max_kN"], x["Ft_final_kN"]
    rear = max((2, 3), key=lambda i: mx[i])
    # predicted residual: T0 = Ft0 -/+ N0 sin(theta); slip if T0 > mu * floor; final = mu*floor -/+ N0 sin(theta)
    tag = r["id"].split("|")[2] if r["id"].startswith("O|") else r["id"].split("|")[3]
    th = abs(float(tag.split("pitch")[1])) * math.pi / 180
    sgn = -1.0 if "pitch-" in tag else 1.0          # nose up: Ft = T - N sin; nose down: Ft = T + N sin
    floor = min(x["P_stop_spec_kN"])
    pred = []
    for i in (2, 3):
        n0 = x["Fl_start_kN"][i]
        T0 = st[i] - sgn * n0 * math.sin(th)
        Tf = min(T0, 0.5 * floor)
        pred.append(round(Tf + sgn * n0 * math.sin(th), 2))
    rows.append((r["id"], r["min_true_cyl_force_kN"], LEGS[rear], st[rear], mx[rear], x["Fl_at_Ft_max_kN"][rear],
                 round(mx[rear] / st[rear], 3), [fin[2], fin[3]], [round(fin[i] / st[i], 2) for i in (2, 3)], pred,
                 x["duration_s"], x["P_stop_spec_kN"]))
print("id | min true | rear leg with max | Ft start | Ft max (N) | max/start | Ft final RL,RR | final/start | predicted final | dur | P_stop")
for row in sorted(rows):
    print(" | ".join(str(v) for v in row))
