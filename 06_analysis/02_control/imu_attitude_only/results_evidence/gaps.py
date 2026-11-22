"""Why the report says incomplete: not-judgeable cells, missing keys per arm, error keys, run counts."""
import json
import sys
from collections import Counter
from pathlib import Path

d = Path(sys.argv[1])
s = json.load(open(d / "imuatt_summary.json", encoding="utf-8"))
print("pair_rows", s["pair_rows"])
print("not_judgeable", len(s["not_judgeable_cells"]))
print(Counter("|".join(k.split("|")[:2]) for k in s["not_judgeable_cells"]))
print("error_keys", len(s["error_keys"]), s["error_keys"][:5])
for arm, keys in s["missing_keys"].items():
    c = Counter("|".join(k.split("|")[:2]) for k in keys)
    print("missing", arm, len(keys), dict(c))
runs = json.load(open(d / "imuatt_metrics_runs.json", encoding="utf-8"))
print("runs", len(runs))
cnt = Counter((r["arm"], r["level"], r["seed_index"]) for r in runs)
for k in sorted(cnt):
    print(k, cnt[k])
none_metric = Counter((r["arm"], r["level"]) for r in runs if not r.get("run_metrics"))
print("runs without metrics", dict(none_metric))
