"""Step 8: where the FAULT lines sit in the slots (condition or candidate, slot layer, crossed or
judged). Writes fault_line_slots.csv."""
import csv
import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(JUDGE))
import run_v5  # noqa: E402

OUT = Path(sys.argv[1])
RUNS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248")
final = {}
for p in (r"ho_v0_a1\ed8_heldout_v0.jsonl", r"ho_aa2_a1\ed8_heldout_aa2.jsonl", r"ho_aa3_a1\ed8_heldout_aa3.jsonl"):
    with (RUNS / p).open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            final[run_v5.job_key(row["job"])] = row.get("final_phase")
slots = json.loads((OUT / "slots_stage5.json").read_text(encoding="utf-8"))["slots"]
out = []
for rec in slots:
    pair = rec["pair_unique"]
    roles = [("condition", rec["condition_job"], rec["layer"], None)]
    roles += [(f"candidate{i+1}", c["job"], c["layer"], c) for i, c in enumerate(rec["candidates"])]
    for role, job, layer, c in roles:
        if final.get(run_v5.job_key(job)) != "fault":
            continue
        if c is None:
            use = "condition (base fail -> slot not counted)"
        elif pair["state"] == "pair" and pair["tries"] == int(role[-1]):
            use = "judged A/A candidate"
        elif int(role[-1]) in pair["crossed"]:
            use = "crossed (other layer, skipped)"
        else:
            use = "after decided try (ignored)"
        out.append({"index": rec["index"], "source": rec["source"], "slot": rec["slot"],
                    "slot_layer": rec["layer"], "role": role, "line_layer": layer,
                    "offset_s": job.get("offset_s"), "depth_m": (job.get("twin") or {}).get("depth_m"),
                    "ramp_s": (job.get("twin") or {}).get("ramp_s"), "use": use})
with open(OUT / "fault_line_slots.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
for r in out:
    print(r)
