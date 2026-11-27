"""Key forms (no values) of the stored V0 jobs: case, job keys, twin keys -> count."""
import json
import sys
from collections import Counter
from pathlib import Path

forms = Counter()
with (Path(sys.argv[1]) / "06_analysis/03_hydraulic/coupled/v5/main.jsonl").open(
        encoding="utf-8") as handle:
    for text in handle:
        job = json.loads(text).get("job") or {}
        if job.get("setting") != "V0":
            continue
        forms[(job.get("case"), tuple(sorted(job)), tuple(sorted(job.get("twin") or {})))] += 1
for form, count in sorted(forms.items(), key=str):
    print(count, form)
