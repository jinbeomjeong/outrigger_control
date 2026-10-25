"""Level-trend (J4) inputs: min rod force outside REANCHOR per fdown3.5 / rpB case and level.

Reads the "metrics" list of each verify_S8C.json and prints level, floor, F_s, beta,
min_cyl_excl_reanchor_kN, its leg / time, REANCHOR min and READY time.
Usage: python -I s8rest_trend.py <verify_json> [<verify_json> ...]
"""
import json
import sys

for path in sys.argv[1:]:
    v = json.load(open(path, encoding="utf-8"))
    s8m = v.get("s8_metrics", {})
    print("==", v["meta"]["batch"])
    for m in v["metrics"]:
        case = m["case"]
        if m.get("floor") not in ("fdown3.5", "rpB") or m.get("event"):
            continue
        s8 = s8m.get(case, {}).get("s8", {})
        print(f"  {case:34s} level {m.get('level'):6s} floor {m.get('floor'):9s} Fs {s8.get('fs_kN')}"
              f" contact {s8.get('contact')}  min_excl_reanchor {m.get('min_cyl_excl_reanchor_kN')}"
              f"  min_reanchor {m.get('min_cyl_reanchor_kN')}  leg {m.get('min_cyl_leg')} t {m.get('min_cyl_t_s')}"
              f"  ready {m['times_s'].get('ready')}")
    for r in v["rows"]:
        if r["item"].startswith("8 level trend"):
            print("  ROW:", json.dumps(r, ensure_ascii=False)[:900])
