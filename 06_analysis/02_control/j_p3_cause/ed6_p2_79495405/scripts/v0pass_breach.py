"""Record: v0_pass flag (key list) of the grid (b) breach rows."""
import json
import sys
from collections import Counter
from pathlib import Path

rep = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
kl = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
v0 = {json.dumps(l["job"], sort_keys=True, separators=(",", ":")): l["v0_pair"].get("v0_pass")
      for l in kl["lines"]}
br = [b["line"].split(" ", 2)[2] for b in rep["breach_rows"]]
print("breach rows by v0_pass", Counter(v0[j] for j in br), "all lines", Counter(v0.values()))
