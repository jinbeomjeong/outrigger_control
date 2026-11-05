"""Move the M1 rows run with the first (superseded) dead volume out of the batch files. OFF rows stay in main.

Usage (dynamics-dev): python -I split_old.py
Output: <batch>_oldinputs.jsonl next to the batch file (first review values, retract 1.19 mm FL).
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1"
for batch in ("main", "smoke", "hash"):
    path = OUT / f"{batch}.jsonl"
    if not path.exists():
        continue
    keep, old = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        (keep if json.loads(line)["job"]["variant"] == "OFF" else old).append(line)
    (OUT / f"{batch}_oldinputs.jsonl").write_text("".join(l + "\n" for l in old), encoding="utf-8")
    path.write_text("".join(l + "\n" for l in keep), encoding="utf-8")
    print(batch, "kept", len(keep), "moved", len(old))
