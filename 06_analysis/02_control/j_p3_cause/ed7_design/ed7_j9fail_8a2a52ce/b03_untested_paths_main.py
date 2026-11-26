"""b03: in the edition 7 main-run lines, counts of the paths the probe never exercised
(spec 12, revision 5): reversed probe rounds, D6 not-judgeable rounds, retract WARN,
A_ib latch / n_rev / protect-blocked periods / completion-unknown triggers, A_ib triggers.
Read only. Output b03_untested_paths_main.json."""
import json
import os
from collections import Counter

OUT = os.path.dirname(os.path.abspath(__file__))
R = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce"
FILES = {"j9main": R + r"\j9main_a1\j9_main.jsonl", "sens": R + r"\sens_a1\sens.jsonl",
         "confirm_g1": R + r"\confirm_a1\confirm_g1.jsonl", "confirm_d": R + r"\confirm_a1\ed7_probe_d.jsonl"}
res = {}
for name, path in FILES.items():
    c = Counter()
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            d = json.loads(ln)
            c["lines"] += 1
            d6 = d.get("probe_d6_record") or {}
            for r in d6.get("rounds") or []:
                c["d6_rounds"] += 1
                c["reversed_rounds"] += bool(r.get("is_reversed"))
                c["rounds_not_opened"] += r.get("is_opened") is False
            c["not_judgeable_rounds"] += sum(d6.get("not_judgeable_rounds") or [0])
            en = d.get("event_names") or {}
            c["warn_retract_not_opened"] += en.get("WARN_PROBE_RETRACT_NOT_OPENED", 0)
            c["info_d6_not_opened"] += en.get("INFO_D6_NOT_OPENED", 0)
            c["warn_rod_fallback"] += en.get("WARN_ROD_PRESSURE_FALLBACK", 0)
            c["stiff_warn"] += en.get("WARN_PROBE_STIFFNESS_OUT_OF_RANGE", 0)
            blind = ((d.get("lsb_record") or {}).get("blind") or {})
            for leg, v in (blind.get("legs") or {}).items():
                c["ib_triggers"] += v.get("triggers", 0)
                c["ib_latches"] += v.get("latches", 0)
                c["ib_n_rev"] += v.get("n_rev", 0)
                c["ib_protect_blocked_periods"] += v.get("protect_blocked_periods", 0)
                c["ib_triggers_completion_unknown"] += v.get("triggers_completion_unknown", 0)
            c["ib_shots"] += len(blind.get("shots") or [])
            c["ib_four_leg"] += blind.get("four_leg_twist_triggers", 0) or 0
            lvd = blind.get("level_done") or []
            c["level_done_relax"] += sum(1 for x in lvd if x.get("path") == "relax")
            c["level_done_strict"] += sum(1 for x in lvd if x.get("path") == "strict")
    res[name] = dict(c)
    print(name, json.dumps(res[name]))
json.dump(res, open(os.path.join(OUT, "b03_untested_paths_main.json"), "w", encoding="utf-8"), indent=1)
