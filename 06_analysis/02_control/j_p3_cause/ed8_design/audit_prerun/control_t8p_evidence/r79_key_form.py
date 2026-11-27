"""Form of the r79 line keys of the P8-14 raw file and of the P8-14 plan (no values)."""
import json
from collections import Counter
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design"
         r"\control_level_deadlock\probe_8a2a52ce")
forms = Counter()
for text in (D / "raw" / "runs.jsonl").read_text(encoding="utf-8").splitlines():
    row = json.loads(text)
    if "job" in row:
        continue
    key = str(row.get("key"))
    prefix = key.split("#", 1)[0] + "#" if "#" in key else "<none>"
    tokens = key.split("#", 1)[-1].split("|")
    forms[(prefix, len(tokens), tokens[1][:1] + ("digits" if tokens[1][1:].isdigit() else "?"))] += 1
print("raw r79 key forms:", dict(forms))
plan = json.loads((D / "raw" / "plans" / "P814-B-VBKM0.json").read_text(encoding="utf-8"))
print("plan top fields:", sorted(plan))
pf = Counter()
for key in plan["faults"]:
    prefix = key.split("#", 1)[0] + "#" if "#" in key else "<none>"
    pf[(prefix, len(key.split("#", 1)[-1].split("|")))] += 1
print("plan fault key forms:", dict(pf))
