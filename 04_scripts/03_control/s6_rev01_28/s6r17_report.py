"""Tables from s6r17_h4_fs_order.json (spec rev. 17). Units kN / s."""
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
d = json.loads((OUT_DIR / "s6r17_h4_fs_order.json").read_text(encoding="utf-8"))
G = d["meta"]["guard_kN"]
print("meta", d["meta"])
runs = d["runs"]
errs = [r for r in runs if "error" in r]
print("errors", len(errs), [e.get("error") for e in errs[:3]])
aff = {tuple(r.get("worker_affinity") or []) for r in runs}
print("worker affinities", [list(a)[:3] + ["..."] + [len(a)] for a in aff])

print("\n== Part F: spec | F_s | slope -> n, min run, min RA, worst id, fails, not completed, relevel, Ft final max, min gap")
grp = defaultdict(list)
for r in runs:
    if r["id"].startswith("F|") and "error" not in r:
        _, sn, tag, mast, km, fs, s = r["id"].split("|")
        grp[(sn, fs, tag)].append(r)
for k in sorted(grp):
    L = grp[k]
    mins = [(r["min_true_cyl_force_kN"], r["id"]) for r in L]
    ra = [r["x"].get("min_true_ra_kN") for r in L]
    ftf = max(max(r["x"].get("Ft_final_kN", [0])[i] for i in (0, 1, 2, 3)) for r in L)
    ftr = max(max(r["x"].get("Ft_start_kN", [0])) for r in L)
    gaps = [st["gap_kN"] for r in L for st in r["x"].get("steps", [])]
    stops = sorted({round(st["P_stop_reading_kN"]) for r in L for st in r["x"].get("steps", [])})
    print(k, len(L), min(mins)[0], min(x for x in ra if x is not None), min(mins)[1].split("|", 2)[2],
          sum(bool(r["fails"]) for r in L), sum(not r["x"].get("completed") for r in L),
          sum(r["x"].get("relevel_events", 0) for r in L), "Ft start/final max", ftr, ftf,
          "gap max", max(gaps) if gaps else None, "stop readings", stops,
          "below guard", sum(m < G for m, _ in mins))

print("\n== Part O: variant | slope | kt -> min run, RA dur, rear: Ft_max(Fl at), Fl_max(Ft at), Ft final; front FL")
for r in sorted((r for r in runs if r["id"].startswith("O|") and "error" not in r), key=lambda r: (r["id"].split("|")[2], r["id"].split("|")[4], r["id"].split("|")[1])):
    _, vn, tag, mast, km, fs, s = r["id"].split("|")
    x = r["x"]
    rear = {lg: (x["Ft_max_kN"][i], x["Fl_at_Ft_max_kN"][i], x["Fl_max_kN"][i], x["Ft_at_Fl_max_kN"][i], x["Ft_final_kN"][i])
            for i, lg in ((0, "FL"), (2, "RL"), (3, "RR"))}
    print(f"{tag:12s} {km:4s} {vn:10s} min {r['min_true_cyl_force_kN']:6.2f} dur {x.get('duration_s')} "
          f"start Ft {x['Ft_start_kN']} Fl {x['Fl_start_kN']} | " +
          " ".join(f"{lg}: Ft {a}({b}) Fl {c}({e_}) fin {f}" for lg, (a, b, c, e_, f) in rear.items()),
          "reasons", x.get("reasons"))
