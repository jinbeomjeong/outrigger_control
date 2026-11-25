"""Cross-check: failed keys of the adoption report (j7 ed6_share) against the edition 6 probe
share tool's own group_judgement on the same probe lines (prints only match counts)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

worktree, rows_path, v0_path, v0_sha, report_path, out_path = sys.argv[1:7]
coupled = Path(worktree) / "04_scripts" / "04_hydraulic" / "coupled"
for path in (coupled, Path(worktree) / "03_src"):
    sys.path.insert(0, str(path))

import ed6_probe_share as share  # noqa: E402

rows_path = Path(rows_path)
t4h_dir = rows_path.with_name(f"{rows_path.stem}_t4h")
groups = defaultdict(list)
with rows_path.open(encoding="utf-8") as handle:
    for text in handle:
        record = json.loads(text)
        block = record.get("ed7_probe") or {}
        if block.get("part") == "main" and block.get("arm") in ("a2", "a3", "a4"):
            groups[(block["plant"], block["arm"])].append(record)
v0_rows = share._v0_metric_rows(Path(v0_path), v0_sha)
report = json.loads(Path(report_path).read_text(encoding="utf-8"))
result = {"groups": 0, "same": 0, "differ": []}
for (plant, arm), lines in sorted(groups.items()):
    theirs = share.group_judgement(lines, t4h_dir, v0_rows)["failed_keys"]
    mine = report["groups"][f"{plant} {arm} main"]["failed_keys"]["ed6_share"]
    result["groups"] += 1
    if sorted(theirs) == sorted(mine):
        result["same"] += 1
    else:
        result["differ"].append([plant, arm])
Path(out_path).write_text(json.dumps(result), encoding="utf-8")
print(json.dumps({"groups": result["groups"], "same": result["same"]}))
