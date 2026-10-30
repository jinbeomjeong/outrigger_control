"""FINAL-R-REP paper-table values (spec 432.6.2): per row the new (final controller) and source values of the
attitude, minimum force, REANCHOR minimum, maximum moving pressure, event-leg minimum rows and READY time.

Usage: python -I final_r_rep_table.py <repo root> <final_r_rep_judge.json> <final_r_rep_cmp.json> <out json>
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
J = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
C = {r["case"]: r for r in json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))}
PICK = {"att": ("2 attitude", "D8 attitude last 5 s", "mean true |roll|"),
        "min_F": ("C1 D8 min true rod force", "min true cylinder force after the crawler lift-off"),
        "reanchor_min": ("C2 REANCHOR min",),
        "p_max": ("4 max moving pressure",),
        "event_leg_min": ("event leg", "G4-4", "C-S8-72 F_min U-S8-74", "SS"),
        "stroke_max": ("maximum motor stroke",)}


def pick(items, keys, old=False):
    for i in items:
        if any(i["item"].startswith(k) or k in i["item"] for k in keys):
            return i["old_value" if old else "value"]
    return None


def ready(folder):
    p = ROOT / folder / "result.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text(encoding="utf-8"))
    return r.get("ready_t_s") if "ready_t_s" in r else (r.get("acceptance") or {}).get("t_ready_s")


out = []
for o in J:
    case = o["case"]
    c = C[case]
    row = {"case": case, "variable": o["variable"], "failed": o["failed_judged"], "flags": o["flags"],
           "commands": c["r8_series"]["status"], "final_feature_events": c["final_feature_events_new"],
           "ready_new": ready(c["new"]), "ready_old": ready(c["old"])}
    for k, keys in PICK.items():
        row[k] = pick(o["items"], keys)
        row[k + "_old"] = pick(o["items"], keys, old=True)
    out.append(row)
Path(sys.argv[4]).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for r in out:
    print(json.dumps({k: v for k, v in r.items() if k not in ("flags", "final_feature_events")}, default=str)[:700])
