"""Paper placeholder values ([[TBD:B5:C2:<case>:<metric>]]) from b5_final_compare.json.

The 16 table rows follow ``b5_baseline_compare.CASES`` order (same as paper table 24). The C2 value is the first
element of the "C2 / ABL / IND" cell. Rows outside the wide set (F_s / event overrides) carry the previous C2 value
flagged ``inferred`` (final run missing). Usage (dynamics-dev):
  python -I b5_final_tbd.py <b5_final_compare.json> <paper 04_results.md> <out json>
"""
import json
import re
import sys
from pathlib import Path

compare = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
paper = Path(sys.argv[2]).read_text(encoding="utf-8")
METRIC = {"att": "att", "READY": "ready", "minF": "fmin", "gap": "crawler", "pmax": "p"}
names = []
for m in re.finditer(r"\[\[TBD:B5:C2:([^:\]]+):att\]\]", paper):
    names.append(m.group(1))
rows = list(compare["table16"].items())
assert len(names) == len(rows) == 16, (len(names), len(rows))
out = {}
for name, (case, row) in zip(names, rows):
    final = "cells_new" in row
    src = row["cells_new"] if final else row["cells_old_main_all"]
    for tag, key in METRIC.items():
        c2, abl, ind = src[key].split(" / ")
        out[f"[[TBD:B5:C2:{name}:{tag}]]"] = {
            "case": case, "value": c2, "status": "final" if final else "inferred (previous C2, final run missing)",
            "previous_C2": row["cells_old_main_all"][key].split(" / ")[0],
            "ABL_IND_now": f"{abl} / {ind}"}
Path(sys.argv[3]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
for k, v in out.items():
    line = f"{k}\t{v['value']}\t(prev {v['previous_C2']})\t{'' if v['status'] == 'final' else 'INFERRED'}"
    sys.stdout.buffer.write((line + "\n").encode("utf-8"))
