"""Which diag jobs are stage 5 batch jobs (ho_v0 / aa2 / aa3) or edition 9 same-shape jobs.

Reads the sealed held-out key file (job definitions only) and the diag job lists. Prints
labels and batch names only (no run values). Job key = run_v5.job_key form (sorted JSON
without runtime keys).
"""
import json
import sys
from pathlib import Path

DIAG = Path(sys.argv[1])
KEYS = Path(sys.argv[2])
RE1BF = (0.030, 0.05)


def key(job):
    return json.dumps({k: job[k] for k in sorted(job) if k not in ("mask", "t4h_dir")},
                      sort_keys=True)


def shape(job):
    twin = job.get("twin") or {}
    if twin.get("depth_m") is None or twin.get("ramp_s") is None:
        return RE1BF
    return float(twin["depth_m"]), float(twin["ramp_s"])


lines = json.loads(KEYS.read_bytes())["lines"]
batch_of = {}
for line in lines:
    batch_of.setdefault(key(line["v0_pair"]["job"]), set()).add("ho_v0(condition)")
    for index, job in enumerate(line["aa_order"]):
        name = {0: "ho_v0(aa1)", 1: "aa2", 2: "aa3"}.get(index, f"aa_order[{index}]")
        batch_of.setdefault(key(job), set()).add(name)
same_shape = []
for line in lines:
    cond = shape(line["v0_pair"]["job"])
    for index, job in enumerate(line["aa_order"]):
        if shape(job) != cond:
            continue
        if index > 2:
            same_shape.append(key(job))
        break
files = [DIAG / "diag_jobs.json", DIAG / "diag2" / "jobs_sweep.json",
         DIAG / "diag2" / "jobs_sweep_ext.json"]
rows = []
seen = set()
for path in files:
    for entry in json.loads(path.read_text(encoding="utf-8")):
        k = key(entry["job"])
        if k in seen:
            continue
        seen.add(k)
        places = sorted(batch_of.get(k, set()))
        rows.append({"label": entry["label"],
                     "stage5_batch": [p for p in places if not p.startswith("aa_order[")],
                     "other_key_places": [p for p in places if p.startswith("aa_order[")],
                     "ed9_same_shape": k in same_shape})
summary = {"unique_jobs": len(rows),
           "in_stage5_batches": sum(1 for r in rows if r["stage5_batch"]),
           "in_ed9_same_shape": sum(1 for r in rows if r["ed9_same_shape"]),
           "same_shape_jobs_total": len(same_shape),
           "not_in_any_run_batch": sum(1 for r in rows
                                       if not r["stage5_batch"] and not r["ed9_same_shape"])}
print(json.dumps({"summary": summary,
                  "rows": [r for r in rows if r["stage5_batch"] or r["ed9_same_shape"]
                           or r["other_key_places"]]}, indent=1))
