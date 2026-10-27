"""Compact table of r64_g4_closed_loop.py: per case x variant the four start phases.

Usage: python -I r64_g4_table.py <json>
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
rows = {}
for r in d["runs"]:
    if "error" in r:
        print("ERROR", r["case"], r["offset_s"], r["error"])
        continue
    for vname, v in r["variants"].items():
        j = v["judge"]
        m = v["meta_run"] or {}
        tg = ",".join(f"{x['leg']}:{x['outcome']}@{(x['duration_s'] or 0):.1f}s/{(x['travel_m'] or 0) * 1e3:.1f}mm"
                      for x in m.get("targets", []))
        faults = [n for _, n in v["events"] if n.startswith("FAULT_") or n.startswith("WARN_FAULT")]
        rows.setdefault((r["case"], vname), []).append(
            f"  off {r['offset_s']:.3f} tf {j.get('t_f_rel_s')} F {j.get('t_fault_rel_s')} end {m.get('end_reason')}"
            f" [{tg}] true {j.get('true_targets')} G4-4 {j.get('G4_4')}/{j.get('G4_4_mean05')} min {j.get('G4_4_min_kN')}"
            f" m05 {j.get('G4_4_mean05_min_kN')}"
            f" G4-5 {j.get('G4_5')} G4-6 {j.get('G4_6')}({j.get('G4_6_mean_change_deg')}) G4-7 {j.get('G4_7_bit_identical')}"
            f" 2path {v.get('two_path', {}).get('same')} faults {faults}")
    rows.setdefault((r["case"], "OFF"), []).append(
        f"  off {r['offset_s']:.3f} F {r['off']['t_fault_rel_s']} G4-4 {r['off']['G4_4']}/{r['off'].get('G4_4_mean05')}"
        f" min {r['off']['G4_4_min_kN']} m05 {r['off'].get('G4_4_mean05_min_kN')}")
for (case, vname), lines in rows.items():
    print(case, vname)
    for line in lines:
        print(line)
