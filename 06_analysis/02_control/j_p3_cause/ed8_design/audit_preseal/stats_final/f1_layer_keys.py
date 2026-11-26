"""Ed. 8 S8-R final review, part 1: presence of the layer-input keys (no metric values printed).

Checks, on the two public stored V0 sources named in spec 5.1 / 6.3:
  - stored V0 grid runs (touch_phase/acceptance/c4g2_only/grid/grid_r6*.json): top-level run keys,
    presence of `fast` and `reapproach_starts`, and the covariate `fast` cross-tabulated by event name
  - v5/main.jsonl lines: presence of `event_output`, `event_output.fast`, `event_output.reapproach_starts`
    by setting name and whether event_output is empty
Only key names, counts and the covariate `fast` (a pre-treatment event property) are written.
Usage: python -I -B f1_layer_keys.py <out_folder>
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis")
GRID = ROOT / "02_control" / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
GRID_FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
MAIN = ROOT / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
out = Path(sys.argv[1])
res = {"grid": {}, "main": {}}

run_keys = Counter()
fast_by_event = defaultdict(Counter)
job_keys = Counter()
n_runs = 0
for fn in GRID_FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    for job in d["results"]:
        job_keys.update(job.keys())
        runs = job.get("runs") or []
        items = runs.items() if isinstance(runs, dict) else enumerate(runs)
        for _, r in items:
            n_runs += 1
            run_keys.update(r.keys())
            fast_by_event[str(r.get("event"))][repr(r.get("fast", "ABSENT"))] += 1
res["grid"]["runs"] = n_runs
res["grid"]["job_keys"] = dict(job_keys)
res["grid"]["run_keys"] = dict(run_keys)
res["grid"]["fast_by_event"] = {k: dict(v) for k, v in fast_by_event.items()}

by_setting = defaultdict(Counter)
eo_keys = Counter()
fast_by_event_main = defaultdict(Counter)
with MAIN.open(encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        s = str(r.get("setting", r.get("config", "?")))
        eo = r.get("event_output")
        c = by_setting[s]
        c["lines"] += 1
        if eo is None:
            c["event_output_absent"] += 1
        elif not eo:
            c["event_output_empty"] += 1
        else:
            c["event_output_nonempty"] += 1
            eo_keys.update(eo.keys())
            c["fast_present"] += "fast" in eo
            c["reapproach_starts_present"] += "reapproach_starts" in eo
            fast_by_event_main[str(eo.get("event", r.get("event", "?")))][repr(eo.get("fast", "ABSENT"))] += 1
res["main"]["by_setting"] = {k: dict(v) for k, v in by_setting.items()}
res["main"]["event_output_keys"] = dict(eo_keys)
res["main"]["fast_by_event"] = {k: dict(v) for k, v in fast_by_event_main.items()}
(out / "f1_layer_keys.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"status": "ok"}))
