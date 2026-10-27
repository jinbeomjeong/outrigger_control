"""Print the r64_g4_closed_loop.py result: summary rows; --detail per run / variant; --series per-period rows.

Usage: python -I r64_g4_view.py <json> [--detail] [--series] [--var name] [--case id]
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
args = sys.argv[2:]
var = args[args.index("--var") + 1] if "--var" in args else None
case = args[args.index("--case") + 1] if "--case" in args else None
print(json.dumps(d["meta"]))
for s in d["summary"]:
    if (var and s.get("var") != var) or (case and s["case"] != case):
        continue
    print(json.dumps(s, ensure_ascii=True))
if "--detail" in args:
    for r in d["runs"]:
        if case and r["case"] != case:
            continue
        print("=" * 100)
        print(r["case"], r["offset_s"], "fault_after", r.get("fault_after_event_s"), "rl_iv",
              r.get("rl_lift_intervals_nofault"), "loc", r.get("loc_at_branch"), "mass", r.get("mass_at_branch_kg"),
              "wall", r.get("wall_s"))
        print(" pre-branch warnings", r.get("pre_branch_warnings"))
        print(" off", json.dumps(r.get("off"), ensure_ascii=True))
        for vname, v in r.get("variants", {}).items():
            if var and vname != var:
                continue
            print(" --", vname)
            print("  inputs", json.dumps(v.get("inputs_at_fault")))
            print("  meta", json.dumps(v.get("meta_run"), ensure_ascii=True))
            print("  two_path", json.dumps(v.get("two_path"), ensure_ascii=True))
            print("  judge", json.dumps(v["judge"], ensure_ascii=True))
            print("  events", v["events"][:40])
            if "--series" in args:
                for row in v.get("series", []):
                    print("   ", row)
