"""NB-1: structural presence (None / present, no values) of the C-J (i) metric inputs on stored
V0 lines and on edition 8 producer lines; the held-out slot rows, groups and A/A groups."""
import json
import sys
from collections import Counter
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2")
for sub in ("04_scripts/04_hydraulic/coupled", "03_src"):
    sys.path.insert(0, str(WT / sub))

import jp3_ed7_judge as ed7  # noqa: E402
import judge_stage1_4368 as path1  # noqa: E402
import run_v5  # noqa: E402

old = path1.old
FIELDS = {  # metric field -> items reading it
    "gates": "J1 (event)", "class": "J1 (steady)", "F_after": "J2 (steady)",
    "F_after_W_min_kN": "J2 (rigid event)", "F_after_event": "J2 (event)",
    "t_ready": "J3/J4", "case_floor": "J3 (rigid record rows)", "final": "J4",
    "t_back": "J5 (event)", "att_end": "J6 (event)", "att_last5": "J6 (steady)",
    "bad_436": "J7", "events_full": "J7", "n_rev": "J8", "post_clip": "J9",
    "p_move": "J10 (steady)", "p_move_ev": "J10 (event)", "lwa": "J11", "sa4": "SA-4 (S8)",
}
MAIN = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
P816 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design"
            r"\p816_prerun_41e107e9\p816.jsonl")
HELD = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design"
            r"\keys_seal_41e107e9\heldout_g_ed8.json")


def presence(metrics):
    out = Counter()
    for m in metrics:
        kind = "event" if m["is_event"] else "steady"
        for field, item in FIELDS.items():
            if field not in m:
                state = "absent"
            elif m[field] is None:
                state = "None"
            else:
                state = "present"
            out[f"{kind}|{field}|{item}|{state}"] += 1
    return dict(sorted(out.items()))


out = {}
v0 = [json.loads(t) for t in MAIN.read_text(encoding="utf-8").splitlines()]
v0 = [r for r in v0 if (r.get("job") or {}).get("setting") == "V0"]
out["stored_V0"] = presence([ed7.metric_of(dict(r), (), "V0") for r in v0])

impl = [json.loads(t) for t in P816.read_text(encoding="utf-8").splitlines()]
impl = [r for r in impl if isinstance(r.get("job"), dict) and "case" in r["job"]
        and "error" not in r and (r.get("ed8_probe") or {}).get("arm") == "L2_impl"]
out["p816_L2_impl_run_v5_lines"] = len(impl)
out["p816_L2_impl"] = presence([ed7.metric_of(dict(r), (), "VB") for r in impl])
lwa = Counter()
for r in impl:
    block = r.get("lock_window_alignment")
    lwa["block_dict" if isinstance(block, dict) else "block_missing"] += 1
    if isinstance(block, dict):
        lwa["n_late_fallback_by_leg_present" if "n_late_fallback_by_leg" in block
            else "n_late_fallback_by_leg_missing"] += 1
    hyd = r.get("hydraulics_record") or {}
    lwa["m2_post_clip_" + ("present" if hyd.get("m2_clipped_steps_post_lift") is not None
                           else "None")] += 1
out["p816_L2_impl_j9_j11_inputs"] = dict(lwa)

vbn = run_v5.options_of("VBN")[1].to_dict()
out["VBN_options_lock_window_follows_plant"] = vbn.get("lock_window_follows_plant")
out["VBN_options_m2_keys"] = sorted(k for k in vbn if k.startswith("m2"))
out["VBN_options_m2_values_types"] = {k: type(vbn[k]).__name__ for k in vbn if k.startswith("m2")}

held = json.loads(HELD.read_text(encoding="utf-8"))
rows, same_group, same_row, sources = Counter(), Counter(), Counter(), Counter()
twin_diff = Counter()
for line in held["lines"]:
    cond = line["v0_pair"]["job"]
    rows[old.row_name(cond)] += 1
    sources[line["source"]] += 1
    for job in line["aa_order"][:3]:
        same_group[f"{line['source']}|{old.group(job) == old.group(cond)}"] += 1
        same_row[old.row_name(job) == old.row_name(cond)] += 1
        diff = sorted(k for k in set(job.get("twin", {})) | set(cond.get("twin", {}))
                      if job.get("twin", {}).get(k) != cond.get("twin", {}).get(k))
        top = sorted(k for k in set(job) | set(cond) if k != "twin" and job.get(k) != cond.get(k))
        twin_diff[f"{line['source']}|twin:{','.join(diff)}|top:{','.join(top)}"] += 1
out["heldout"] = {"condition_rows": dict(rows), "sources": dict(sources),
                  "aa_first3_same_group": dict(same_group),
                  "aa_first3_same_row": {str(k): v for k, v in same_row.items()},
                  "aa_first3_fields_that_differ": dict(twin_diff),
                  "twin_event_names": dict(Counter(line["v0_pair"]["job"].get("twin", {})
                                                   .get("event") for line in held["lines"]))}
print(json.dumps(out, ensure_ascii=False, indent=1))
