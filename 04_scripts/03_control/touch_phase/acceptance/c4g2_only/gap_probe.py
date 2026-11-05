"""Structure of the stored bundles not rerun: does a row keep controller events, re-approach starts, command hashes. Short output. E core 27 only."""
import json
import os
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")


def walk(o, path="", out=None, depth=0):
    out = {} if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("events", "reapproach_starts", "commands_sha256", "reapproach_events", "deferred", "c2_events", "warnings"):
                out.setdefault(path + "/" + k, type(v).__name__)
            if depth < 4:
                walk(v, path + "/" + k if not k.startswith(("A|", "cand=")) else path + "/*", out, depth + 1)
    elif isinstance(o, list) and o and isinstance(o[0], (dict, list)):
        walk(o[0], path + "[]", out, depth + 1)
    return out


for p in sorted((ACC / "regression").glob("*.json")) + [ACC / "crawler/crawler_both.json", ACC / "soil/soil_A.json", ACC / "d8/d8_both.json"]:
    if "judgement" in p.name:
        continue
    txt = p.read_text(encoding="utf-8")
    d = json.loads(txt)
    res = d.get("results", d) if isinstance(d, dict) else d
    n = len(res) if hasattr(res, "__len__") else None
    first = res[0] if isinstance(res, list) and res else None
    print(p.name, "size", len(txt), "top", list(d)[:5] if isinstance(d, dict) else "list", "n", n, "retrigger text", txt.count(":retrigger"), "deferred text", txt.count("leg_reapproach_deferred"))
    print("  paths", walk(d))
    if isinstance(first, dict):
        print("  first keys", list(first)[:25])
