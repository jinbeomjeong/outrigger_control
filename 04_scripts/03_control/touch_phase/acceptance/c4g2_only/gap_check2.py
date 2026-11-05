"""Second pass of the gap check: base hash per soil job against stored off and clip_A, re-approach fields of the regression records and crawler rows. E core 27. Appends to gap_check.json."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
REV85 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


off = {r["key"]: r for r in load(REV85 / "finB2_A.json")["results"]}
soil = {r["key"]: r for r in load(ACC / "soil/soil_A.json")["results"]}
clip = {r["key"]: r for r in load(ACC / "regression/clip_A.json")["results"]}
print("soil base same as off", {k: soil[k]["base"]["commands_sha256"] == off[k]["base"]["commands_sha256"] for k in soil})
print("clip_A vs soil_A", {k: (clip[k]["base"]["commands_sha256"] == soil[k]["base"]["commands_sha256"], all(a["commands_sha256"] == b["commands_sha256"] for a, b in zip(clip[k]["runs"], soil[k]["runs"]))) for k in clip})
print("off D row pass", {k: [(r["event"], r["timing"], r["pass"]) for r in off[k]["runs"] if not r["pass"]] for k in off if any(not r["pass"] for r in off[k]["runs"])})
print("soil fail", {k: [(r["event"], r["timing"]) for r in soil[k]["runs"] if not r["pass"]] for k in soil if any(not r["pass"] for r in soil[k]["runs"])})
cr = load(ACC / "crawler/crawler_both.json")
rows = cr["runs"]
print("crawler meta wall", cr["meta"].get("wall_s"), "workers", cr["meta"].get("workers"), "first keys", list(rows[0])[:20])
print("crawler reapproach after liftoff >0", sum((r.get("values", {}).get("events") or {}).get("reapproach_starts_after_liftoff", 0) > 0 for r in rows), "values keys", [k for k in rows[0].get("values", {})][:25])
print("crawler reapproach counted elsewhere", {k: v for k, v in rows[0].items() if "reapp" in k.lower()})


def hunt(o, path="", out=None, depth=0):
    out = {} if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            if "reapp" in k.lower() and not isinstance(v, (dict, list)):
                out[path + "/" + k] = v
            elif depth < 5:
                hunt(v, path + "/" + k, out, depth + 1)
    return out


for fname in ("clip_harness", "clip_p0"):
    rec = load(ACC / f"regression/{fname}.json")["records"]
    print(fname, "first reapp fields", list(hunt(rec[0]).items())[:10], "failed", [r["id"] for r in rec if not r.get("passed")][:6])
    table = [(r["id"], {k.rsplit("/", 1)[1]: v for k, v in hunt(r).items() if k.rsplit("/", 1)[1] in ("n_reapproach", "reapproach_starts", "n_reapproach_starts", "leg_reapproach_start", "reapproach_count", "reapproach_starts_after_liftoff")}) for r in rec]
    print("  ", table[:17])
print("x426_C", [(r["key"], r.get("n_reapproach")) for r in load(ACC / "regression/clip_x426_C.json")["results"]])
print("d8", sum(r["reapproach_starts"] > 0 for r in load(ACC / "d8/d8_both.json")["runs"]))
