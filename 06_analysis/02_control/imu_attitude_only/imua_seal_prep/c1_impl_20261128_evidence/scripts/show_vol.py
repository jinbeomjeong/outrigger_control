"""Print the volatile JSON leaves of compare.py reports."""
import json
import sys
from pathlib import Path

for p in sys.argv[1:]:
    rep = json.loads(Path(p).read_text(encoding="utf-8"))
    for rel, r in rep["json"].items():
        if r["volatile_count"]:
            print(Path(p).name, rel, r["volatile"])
