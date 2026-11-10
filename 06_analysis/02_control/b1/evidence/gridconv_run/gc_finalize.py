"""Assemble <batch>/batch.json from per-row records written by gc_run_lane.ps1."""
import json
import sys
from pathlib import Path

batch = Path(sys.argv[1])
order = ["GC1_J2_B_RL_1cm", "GC2_J2_B_RL_0p5cm", "GC3_J2_B_FL_1cm", "GC4_J2_B_FL_0p5cm"]
cases = []
for c in order:
    p = batch / "rowrec" / f"{c}.json"
    if p.is_file():
        cases.append(json.loads(p.read_text(encoding="utf-8-sig")))
    else:
        cases.append({"case": c, "rc": None, "missing": True})
doc = {"batch": "B1-GRIDCONV", "plan_sha256": "0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24",
       "plan_rev1_sha256": "3f354eb7c122584c7e65e66bb2eeaf33e27cfa9b445521a9802bdf8962d1da9e", "cases": cases}
(batch / "batch.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({"cases": [(c["case"], c.get("rc")) for c in cases]}))
