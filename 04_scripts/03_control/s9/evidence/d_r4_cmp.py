"""Study D (x426 D, H8 non-planar start on soft soil): final controller (fin_x426_D, SGS + R4c30) vs former
(x426_D, 05708b2). Per id: verdict, max stroke, R4 applied (INFO_LOC_FLAT_SOIL_MARGIN), guard events, READY,
ready gap. Prints a table and the stroke-increase distribution of the R4-applied rows."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
A = ROOT / "06_analysis/02_control/s9/rev85"
GUARD = 682.8


def load(name):
    d = json.loads((A / name).read_text(encoding="utf-8"))
    return {r["id"]: r for r in d["results"]}


def ev_names(r):
    out = []
    for e in r.get("events", []):
        s = e[1] if isinstance(e, (list, tuple)) and len(e) > 1 else (e.get("name") if isinstance(e, dict) else str(e))
        out.append(str(s))
    return out


old, new = load("x426_D.json"), load("fin_x426_D.json")
rows = []
for i in sorted(new):
    n, o = new[i], old.get(i)
    rn, ro = n["run"], (o or {}).get("run", {})
    names = ev_names(n)
    r4 = any("FLAT_SOIL_MARGIN" in s for s in names) or bool(
        (n.get("controller_meta") or {}).get("flat_soil_margin_applied"))
    rows.append({
        "id": i, "v_old": (o or {}).get("verdict"), "v_new": n["verdict"],
        "s_old": ro.get("max_motor_stroke_mm"), "s_new": rn.get("max_motor_stroke_mm"),
        "ready_old": ro.get("t_ready_s"), "ready_new": rn.get("t_ready_s"),
        "gap_old": (o or {}).get("rut_ready_mm"), "gap_new": n.get("rut_ready_mm"),
        "minF_new": rn.get("min_true_Fcyl_after_off_kN"),
        "r4": r4, "guard": [s for s in names if "STROKE" in s or "FAULT" in s],
        "r4_events": [s for s in names if "FLAT_SOIL" in s or "CLEARANCE_MARGIN" in s]})

print(f"{'id':34s} {'v_old':6s} {'v_new':6s} {'s_old':>7s} {'s_new':>7s} {'ds':>6s} {'margin':>7s} {'R4':3s} "
      f"{'rdy_o':>6s} {'rdy_n':>6s} {'gap_o':>6s} {'gap_n':>6s} ev")
for r in rows:
    ds = (r["s_new"] - r["s_old"]) if r["s_new"] is not None and r["s_old"] is not None else None
    r["ds"] = ds
    f = lambda x: "-" if x is None else f"{x:.1f}"
    print(f"{r['id']:34s} {str(r['v_old'])[:6]:6s} {str(r['v_new'])[:6]:6s} {f(r['s_old']):>7s} {f(r['s_new']):>7s} "
          f"{f(ds):>6s} {f(GUARD - r['s_new'] if r['s_new'] else None):>7s} {'Y' if r['r4'] else 'n':3s} "
          f"{f(r['ready_old']):>6s} {f(r['ready_new']):>6s} {f(r['gap_old']):>6s} {f(r['gap_new']):>6s} "
          f"{(r['guard'] + r['r4_events'])[:3]}")
act = [r for r in rows if r["r4"] and r["ds"] is not None]
non = [r for r in rows if not r["r4"] and r["ds"] is not None]
for name, grp in (("R4 applied", act), ("R4 not applied", non)):
    if grp:
        d = sorted(r["ds"] for r in grp)
        print(f"{name}: n={len(d)} ds min {d[0]:.1f} median {statistics.median(d):.1f} max {d[-1]:.1f} mm; "
              f"margin min {min(GUARD - r['s_new'] for r in grp):.1f} mm; "
              f"n margin<16 mm = {sum(GUARD - r['s_new'] < 16 for r in grp)}")
by = {}
for r in act:
    k = r["id"].split("|")[1] + ("|base" if r["id"].count("|") == 4 else "|" + r["id"].split("|")[5][:4])
    by.setdefault(k, []).append(round(r["ds"], 1))
print("by soil|leg:kind", by)
Path(sys.argv[2]).write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
