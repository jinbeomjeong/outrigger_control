"""Step 4: condition V0(o) vs judged candidate V0(o'') line summaries for the failing pairs, the
two E slots the tool counted (10, 28) and their name twins (173, 179). Writes pair_lines.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(JUDGE))
import run_v5  # noqa: E402

OUT = Path(sys.argv[1])
RUNS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248")
FILES = {"v0": RUNS / r"ho_v0_a1\ed8_heldout_v0.jsonl", "aa2": RUNS / r"ho_aa2_a1\ed8_heldout_aa2.jsonl",
         "aa3": RUNS / r"ho_aa3_a1\ed8_heldout_aa3.jsonl"}
rows_by, file_of = {}, {}
for name, path in FILES.items():
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            k = run_v5.job_key(row["job"])
            rows_by[k] = row
            file_of[k] = name

doc = json.loads((OUT / "slots_stage5.json").read_text(encoding="utf-8"))
slots = doc["slots"]
want = sorted({r["index"] for r in slots if r["pair_unique"].get("aa_fail")} | {10, 28, 173, 179})


def summary(row):
    v, eo = row.get("values", {}), row.get("event_output", {}) or {}
    return {
        "offset_s": row["job"].get("offset_s"), "twin": row["job"].get("twin"),
        "commands_sha256": row.get("commands_sha256")[:12],
        "final_phase": row.get("final_phase"), "t_event_s": row.get("t_event_s"),
        "times": v.get("times"), "t_lift_s": v.get("forces", {}).get("t_lift_s"),
        "fault_events": v.get("events", {}).get("fault_events"),
        "warn_events": v.get("events", {}).get("warn_events"),
        "info": v.get("events", {}).get("info_rule_events"),
        "reapproach_after_liftoff": v.get("events", {}).get("reapproach_starts_after_liftoff"),
        "probe_aborts": v.get("events", {}).get("probe_aborts"),
        "eo_pair": eo.get("pair"), "eo_lifts": eo.get("lifts"),
        "eo_reapproach_starts": eo.get("reapproach_starts"),
        "eo_min_F_after_event_kN": eo.get("min_F_after_event_kN"),
        "eo_adj_min_F_in_W_kN": eo.get("adj_min_F_in_W_kN"),
        "eo_t_ready_back_s": eo.get("t_ready_back_s"), "eo_final_phase": eo.get("final_phase"),
        "eo_fault_events": eo.get("fault_events"), "eo_warnings": eo.get("warnings"),
        "eo_att_end_deg": eo.get("att_end_deg"), "eo_max_att_change_deg": eo.get("max_att_change_deg"),
        "eo_pair_union_s": eo.get("pair_union_s"), "eo_pair_last_touch_s": eo.get("pair_last_touch_s"),
        "eo_W_end_s": eo.get("W_end_s"), "eo_gates": eo.get("gates"),
        "eo_pressure": eo.get("pressure"),
        "eo_crawler_contact_ms": eo.get("crawler_contact_after_event_ms"),
        "eo_sign_changes": eo.get("sign_changes"), "eo_n_late_starts": eo.get("n_late_starts"),
        "event_names": row.get("event_names"), "events": row.get("events"),
        "command_stats": row.get("command_stats"),
        "pressure_max_moving_bar": v.get("pressure", {}).get("max_moving_bar"),
        "oil_force_max_kN": v.get("oil_force_max_kN"),
        "twist": v.get("twist"), "forces": v.get("forces"),
    }


out = []
for i in want:
    rec = slots[i]
    cond = rows_by[run_v5.job_key(rec["condition_job"])]
    pair = rec["pair_unique"]
    item = {"index": i, "source": rec["source"], "slot": rec["slot"], "layer": rec["layer"],
            "base_pass": rec["base_pass"], "pair": pair, "failed_items": rec.get("failed_items"),
            "condition_file": file_of[run_v5.job_key(rec["condition_job"])],
            "condition": summary(cond), "candidates": []}
    for c in rec["candidates"]:
        k = run_v5.job_key(c["job"])
        row = rows_by.get(k)
        item["candidates"].append({"layer": c["layer"], "hash_equal": c["hash_equal"],
                                   "aa_fail": c["aa_fail"], "file": file_of.get(k),
                                   "line": None if row is None else summary(row)})
    out.append(item)
(OUT / "pair_lines.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str),
                                     encoding="utf-8")
print(len(out), "pairs written")
