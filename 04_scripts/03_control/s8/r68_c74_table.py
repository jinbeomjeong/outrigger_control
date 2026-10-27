"""C-S8-74 (spec rev. 68 357): per-case gate values vs the same C-S8-72 case (U-S8-74 re-judged), and the
355.4 classification (B = U57 outside-window lift or U-S8-74 F_min failure; A = passed but 1 ms instant < F_min).

Usage: python -I r68_c74_table.py <verify_S8C_c74.json> <verify_S8C_c72_u74.json> <out.json>
"""
import json
import re
import sys
from pathlib import Path

ORIG = {  # C-S8-74 base (without the F_s suffix) -> C-S8-72 case
    "G1L_RE1bF_FL_top_o050": "G1L_RE1bF_FL_top_Fs0", "G1L_RE1bF_FR_top_o075": "G1L_RE1bF_FR_top_Fs0",
    "G1L_FS24_FR_top_o025": "G1L_FS24_FR_top_Fs0", "G1L_FS24_FL_top_o075": "G1L_FS24_FL_top_Fs0",
    "G1L_RE1bF_FL_top_o000": "G1L_RE1bF_FL_top_Fs8", "G1R_RE1bF_FL_top_o000": "G1R_RE1bF_FL_top_Fs0",
    "G1R_FS24_FL_top_o025": "G1R_FS24_FL_top_Fs0", "G1R_RE1bF_FR_top_o075": "G1R_RE1bF_FR_top_Fs0",
}
NUM = {k: i + 1 for i, k in enumerate(ORIG)}


def per_case(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for r in d["rows"]:
        it = str(r["item"])
        if not it.startswith("C-S8-7"):
            continue
        c = out.setdefault(r["case"], {"failed": []})
        if r.get("passed") is False:
            c["failed"].append(it[:80])
        if "event state" in it:
            c["phase"] = r["value"].get("phase_at_event")
        elif "adjacent legs U57" in it and "slow" not in it:
            c["u57"] = r["value"]
        elif "event legs" in it and "slow" not in it:
            c["event_leg"] = r["value"]
        elif it.startswith("C-S8-72 F_min") and "instantaneous" not in it:
            c["fmin"] = {"value": r["value"], "passed": r["passed"]}
        elif "instantaneous" in it and "F_min" in it:
            c["fmin_instant"] = {"value": r["value"], "note": str(r.get("note", ""))[:160]}
        elif "recurrence" in it:
            c["recurrence"] = {"n": r["value"].get("n_clusters"), "max_J": r["value"].get("max_bin_after_J"),
                               "passed": r["passed"]}
        elif it.startswith("C-S8-72 record"):
            v = r["value"]
            c["late_starts"] = v.get("starts_after_1.5_s")
            c["union_s"] = v.get("event_pair_union_s")
            c["ready_back_rel_s"] = v.get("ready_back_rel_s")
        elif it.startswith("C-S8-72 end"):
            c["end_att"] = r["value"].get("last5_maxabs_deg")
    return out, d["meta"].get("summary")


c74, s74 = per_case(sys.argv[1])
c72, _ = per_case(sys.argv[2])
rows = []
for case in sorted(c74, key=lambda x: (NUM.get(re.sub(r"_Fs\d$", "", x), 99), x)):
    base = re.sub(r"_Fs\d$", "", case)
    fs = case[-1]
    v = c74[case]
    ref = c72.get(ORIG.get(base, ""), {})
    u57 = v.get("u57") or [0, 0, 0]
    fm = v.get("fmin") or {}
    fi = v.get("fmin_instant") or {}
    b_type = bool((u57[2] or 0) > 0 or fm.get("passed") is False)
    inst = fi.get("value")
    inst_min = inst.get("instant_min_kN") if isinstance(inst, dict) else inst
    a_type = (not b_type) and inst_min is not None and inst_min < 9.4146
    row = {"no": NUM.get(base), "case": case, "Fs_kN": int(fs), "c72_case": ORIG.get(base), "phase": v.get("phase"),
           "failed": v["failed"], "event_leg": v.get("event_leg"), "u57": u57, "fmin": fm, "fmin_instant": fi,
           "recurrence": v.get("recurrence"), "late_starts": v.get("late_starts"), "union_s": v.get("union_s"),
           "end_att": v.get("end_att"), "B": b_type, "A": a_type,
           "c72": {"u57": ref.get("u57"), "fmin": ref.get("fmin"), "fmin_instant": ref.get("fmin_instant"),
                   "late_starts": ref.get("late_starts"), "event_leg": ref.get("event_leg")}}
    rows.append(row)
    print(f"#{row['no']} {case}: fail {len(v['failed'])} B {b_type} A {a_type} | evleg {v.get('event_leg')} | "
          f"u57 {u57} | Fmin {fm.get('value')} {fm.get('passed')} | inst {inst_min} "
          f"{None if not isinstance(inst, dict) else inst.get('leg')} | late {v.get('late_starts')} | "
          f"recur {v.get('recurrence')} | att {v.get('end_att')}")
    print(f"      c72: u57 {ref.get('u57')} Fmin {(ref.get('fmin') or {}).get('value')} inst "
          f"{((ref.get('fmin_instant') or {}).get('value') or {}).get('instant_min_kN')} late {ref.get('late_starts')} "
          f"evleg {ref.get('event_leg')}")
print("summary", json.dumps(s74)[:300])
Path(sys.argv[3]).write_text(json.dumps({"rows": rows, "summary": s74}, indent=1), encoding="utf-8")
