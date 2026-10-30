"""Soft-patch presence check of G6-type harness results (G1 / rigid base + one soft pad): weak-leg final sinkage
and READY medians per (base, patch soil) for a result file, optionally against a reference file.

Accepts r79 result files (results[].base.*), x426 C files (results[].*) and wrapper g6 files (records[] with
metrics). Usage: python -I g6_patch_check.py <file> [<reference file>]
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

LEG = {"FL": 0, "FR": 1, "RL": 2, "RR": 3}


def rows(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for r in d.get("results") or d.get("records") or []:
        b = r.get("base") if isinstance(r.get("base"), dict) else r
        key = (r.get("key") or r.get("id") or "").split("#", 1)[-1]
        soil = b.get("soil") or ""
        wl = b.get("weak_leg")
        sink = b.get("sink_final_mm") or (b.get("metrics") or {}).get("sink_final_mm")
        if "+" not in soil or wl not in LEG or not sink:
            continue
        out[key] = (soil, sink[LEG[wl]], b.get("t_ready_s"))
    return out


def summary(rs):
    g = defaultdict(list)
    for soil, s, t in rs.values():
        base, rest = soil.split("+", 1)
        g[(base, rest.split("@")[0])].append((s, t or 0.0))
    return {f"{a}+{b}": (len(v), round(statistics.median(x[0] for x in v), 1), round(statistics.median(x[1] for x in v), 1))
            for (a, b), v in sorted(g.items())}


a = rows(sys.argv[1])
print(sys.argv[1], "n", len(a), "(n, weak-leg sink median mm, READY median s):", summary(a))
if len(sys.argv) > 2:
    b = rows(sys.argv[2])
    print(sys.argv[2], "n", len(b), summary(b))
