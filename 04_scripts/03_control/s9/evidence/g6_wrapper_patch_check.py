"""Soft-patch sanity check of wrapper g6 records (s9_slope_fix_candidates results, ids 'g6|<base>+<soil>@<leg>|...'):
READY and max-stroke medians per (base, patch soil) for a result file against a reference (e.g. R2DS_g6.json).
A lost patch shows as G1-base rows collapsing to the uniform-G1 READY (~44-50 s).

Usage: python -I g6_wrapper_patch_check.py <file> <reference file>
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    out = defaultdict(list)
    for r in d.get("records") or []:
        i = r.get("id", "")
        if not i.startswith("g6|") or "+" not in i:
            continue
        soil = i.split("|")[1]
        base, rest = soil.split("+", 1)
        out[(base, rest.split("@")[0])].append((r.get("t_ready_s") or 0.0, r.get("max_stroke_mm") or 0.0))
    return {f"{a}+{b}": (len(v), round(statistics.median(x[0] for x in v), 1), round(statistics.median(x[1] for x in v), 1))
            for (a, b), v in sorted(out.items())}


for p in sys.argv[1:]:
    print(p, "(n, READY median s, max stroke median mm):", load(p))
