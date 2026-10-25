"""S-TH1 judgement tables from s6r16_touch_hold_sweep.json (spec 77.4). Units kN / s."""
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
d = json.loads((OUT_DIR / "s6r16_touch_hold_sweep.json").read_text(encoding="utf-8"))
G = d["meta"]["guard_kN"]
runs = [r for r in d["runs"] if "error" not in r]
print("meta n", d["meta"]["n_cases"], "wall", d["meta"].get("wall_s"), "errors", len(d["runs"]) - len(runs), "guard", G)


def ltype(r):
    return r.get("min_true_leg_substep") in ("RR", "FL") and (r.get("t_min_after_liftoff_s") or 9) <= 0.1


grp = defaultdict(list)
for r in runs:
    p = r["id"].split("|")
    grp[(p[0], p[1], p[2] if p[0] != "C" else p[2] + "|" + p[3])].append(r)
print("group | h | point -> n, min, L-type n, below guard, fails, liftoff-touch range, worst")
for k in sorted(grp):
    L = grp[k]
    m = min(L, key=lambda r: r["min_true_cyl_force_substep_kN"])
    tt = [r["t_touch_s"] for r in L if r.get("t_touch_s")]
    print(k, len(L), m["min_true_cyl_force_substep_kN"], sum(ltype(r) for r in L),
          sum(r["min_true_cyl_force_substep_kN"] < G for r in L), sum(bool(r["fails"]) for r in L),
          [min(tt), max(tt)] if tt else None, m["id"], m.get("min_true_leg_substep"), m.get("t_min_after_liftoff_s"),
          sorted({f for r in L for f in (r["fails"] or [])}))
hg = defaultdict(list)
for r in runs:
    p = r["id"].split("|")
    hg[(p[0], p[1])].append(r)
print("\nsummary group|h -> n, min, L-type, below guard, t_ready max")
for k in sorted(hg):
    L = hg[k]
    print(k, len(L), min(r["min_true_cyl_force_substep_kN"] for r in L), sum(ltype(r) for r in L),
          sum(r["min_true_cyl_force_substep_kN"] < G for r in L), max((r.get("t_ready_s") or 0) for r in L),
          "t_touch mean", round(sum(r["t_touch_s"] for r in L) / len(L), 3))
