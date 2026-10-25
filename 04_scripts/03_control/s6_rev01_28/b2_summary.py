"""Summarize S6 B2 verify JSON (and bundle B) for control-expert judgement."""
import json
import sys
from collections import Counter, defaultdict

# migrated 2026-10-25 from session scratchpad a06eea4a ctrl-run; repository-relative
ROOT = (__import__("pathlib").Path(__file__).resolve().parents[3] / "06_analysis" / "01_chrono" / "16_S6").as_posix() + "/"
fn = sys.argv[1] if len(sys.argv) > 1 else "verify_S6_L1_closed_loop_L1R_B2.json"
mode = sys.argv[2] if len(sys.argv) > 2 else "all"
d = json.load(open(ROOT + fn, encoding="utf-8"))

rows = d["rows"]
print("counts", d["counts"])
print("lists", d["lists"])
print("\n== FAILED rows")
for r in rows:
    if r["passed"] is False:
        print(r)
print("\n== not judged items")
nj = Counter(r["item"] for r in rows if r["passed"] is None)
print(nj)
items = Counter(r["item"] for r in rows)
print("\n== items", items)

if mode in ("all", "cases"):
    print("\n== per case")
    for cid, c in d["cases"].items():
        print(f"{cid:40s} ph={c['final_phase']:6s} att={c['att_err_last5_maxabs_deg']:.4f} "
              f"minF={c['min_cyl_after_liftoff_kN']:.2f}({c['min_cyl_leg']}@{c['min_cyl_t_s']:.1f}) "
              f"exclRA={c['min_cyl_excl_reanchor_kN']:.2f} pmax={c['max_pressure_any_step_bar']:.1f} "
              f"sat={c['saturation_steps']} grade={c['grade']} ev={c['event']}")

if mode in ("all", "rows"):
    print("\n== rows by case (selected items)")
    by = defaultdict(list)
    for r in rows:
        by[r["case"]].append(r)
    for cid, rr in by.items():
        print("--", cid)
        for r in rr:
            if r["item"] in ("run",):
                continue
            print(f"   {r['item']:28s} v={str(r['value'])[:60]:60s} lim={str(r['limit'])[:40]:40s} "
                  f"p={r['passed']} {r.get('note','')[:80]}")
