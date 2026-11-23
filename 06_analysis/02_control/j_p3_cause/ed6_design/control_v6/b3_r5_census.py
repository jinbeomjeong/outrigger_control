"""Census of R-5 relevel_predicted events on the judged VBJ / LSJ rows (606f8713, read only).

Counts per case the rows with at least one relevel_predicted event (event_names counter) and
the total count; tells how often a B3 start on the R-5 prediction would fire outside the
R12/G4 settlement rows. Output: b3_r5_census.json (this folder). control-expert 2026-11-23.
"""
import json
from collections import defaultdict
from pathlib import Path

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1")
OUT = Path(__file__).resolve().parent
by = defaultdict(lambda: {"rows": 0, "rows_with_r5": 0, "r5_events": 0})
with open(RUN / "j9_main.jsonl", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        key = f"{d['job']['setting']}|{d['job']['case']}"
        n = sum(v for k, v in (d.get("event_names") or {}).items() if k.startswith("relevel_predicted"))
        by[key]["rows"] += 1
        by[key]["rows_with_r5"] += int(n > 0)
        by[key]["r5_events"] += n
res = dict(sorted(by.items()))
(OUT / "b3_r5_census.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
for k, v in res.items():
    if k.startswith("VBJ"):
        print(k, v)
