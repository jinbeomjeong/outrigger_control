"""Per-run wall time of the stored noise L1 / L2 acceptance runs for the C4G2-only rerun estimate. Reads the job rows; prints count, sum and estimate by worker count."""
import json
from pathlib import Path

p = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\noise\r79_L1L2.json.partial.jsonl")
wall = {}
for line in p.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    key = r.get("key") or r.get("job") or str(len(wall))
    w = r.get("wall_s")
    if w is None:
        continue
    wall[key] = float(w)
total = sum(wall.values())
print("rows with wall", len(wall), "sum_s", round(total), "mean_s", round(total / max(len(wall), 1), 1))
lv = {}
for k, w in wall.items():
    lv.setdefault(k.split("|")[0], []).append(w)
print({k: (len(v), round(sum(v) / len(v), 1)) for k, v in lv.items()})
for workers in (4, 8):
    print("workers", workers, "E cores, h", round(total / workers / 3600, 2))
print("P 8 workers, E/P 1.7 ASSUMPTION, h", round(total / 8 / 1.7 / 3600, 2))
