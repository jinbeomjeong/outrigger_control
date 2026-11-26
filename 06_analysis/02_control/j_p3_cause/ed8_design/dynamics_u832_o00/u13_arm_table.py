"""a2 (VBM) vs direction A (U8-A) on the seen keys, plus the V0 grid reruns: gate values.

Usage: python -I -B u13_arm_table.py <rerun_dir> <folder>
"""
import csv
import json
import sys
from pathlib import Path

rerun, folder = Path(sys.argv[1]), Path(sys.argv[2])
rows = []
for line in (rerun / "runs.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    job = r["job"]
    if job["case"] != "R12":
        continue
    ev = r["event_output"]
    tw = job["twin"]
    rows.append({"setting": job["setting"], "key": f"{tw['level']}-{tw['leg']}-Fs{tw['fs_kN']:g}-o{job['offset_s']}-{tw['event']}-ready",
                 "pass": ev["pass"], "failed": "|".join(k for k, v in ev["gates"].items() if not v),
                 "pair_union_s": ev["pair_union_s"], "pair_last_touch_s": ev["pair_last_touch_s"],
                 "final_phase": ev["final_phase"], "att_end_deg": json.dumps(ev["att_end_deg"]),
                 "t_ready_back_s": ev["t_ready_back_s"], "run_after_s": ev["run_after_s"],
                 "reapproach_starts": json.dumps(ev["reapproach_starts"]),
                 "n_late_starts": ev["n_late_starts"],
                 "min_F_after_W_kN": json.dumps(ev["min_F_after_W_kN"]),
                 "commands_sha256": r["commands_sha256"][:16]})
rows.sort(key=lambda x: (x["key"], x["setting"]))
with (folder / "u13_arm_table.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
for x in rows:
    print(x["key"], x["setting"], x["pass"], x["failed"], x["pair_union_s"], x["pair_last_touch_s"],
          x["final_phase"], x["att_end_deg"], x["t_ready_back_s"], x["run_after_s"], x["n_late_starts"])
