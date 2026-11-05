"""Minimum true force rows of the one-pad soft suites (g6 / g6r) and x426 C (read-only)."""
import json
import re
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
F_MIN = 9.415


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, (int, float)):
        yield path, o


for name in ("finB2_p0.json", "fin_x426_C.json"):
    doc = json.loads((D / name).read_text(encoding="utf-8"))
    recs = doc.get("records") or doc.get("results")
    items = recs.items() if isinstance(recs, dict) else [(r.get("id") or r.get("key"), r) for r in recs]
    out = []
    for rid, r in items:
        if not str(rid).startswith("g6"):
            continue
        vals = {p: v for p, v in walk(r) if re.search(r"min.*(Fcyl|true|F_)", p, re.I) and "kN" in p}
        fs = re.search(r"Fs([0-9.]+)", str(rid))
        if vals:
            key = min(vals, key=vals.get)
            out.append((vals[key], rid, key, fs.group(1) if fs else "?", r.get("pass", r.get("verdict"))))
    out.sort()
    print("==", name, len(out))
    for v, rid, key, fs, verdict in out[:12]:
        print(f"   {v:7.2f} kN  Fs {fs}  {rid}  [{key}]  {verdict}")
