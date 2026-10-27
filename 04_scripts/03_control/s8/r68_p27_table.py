"""Table of the P-S8-27 candidate screen (spec rev. 68 356): per case x level x F_s, variant values and the
command-hash equality with ``proj`` (ref runs = TOUCH without pre-grounding).

Usage: python -I r68_p27_table.py <r68_p27_screen.json> <out_json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = defaultdict(dict)
errors = [r for r in d["results"] if "error" in r]
for r in d["results"]:
    if "error" in r:
        continue
    rows[(r["case"], r["level"], r["fs_kN"])][r["variant"]] = r
table = []
for (case, lv, fs), vs in sorted(rows.items()):
    p = vs.get("proj")
    line = {"case": case, "level": lv, "fs_kN": fs}
    for v in ("proj", "c1", "c2"):
        r = vs.get(v)
        if r is None:
            continue
        tch = r.get("touch", {})
        osc = tch.get("pre_leg_oscillation") or {}
        amps = osc.get("half_pp_per_2s_kN") or []
        line[v] = {"pass": r.get("pass"), "min_F_kN": r.get("min_F_after_liftoff_kN"),
                   "touch_s": tch.get("duration_s"), "latch": tch.get("latch_rel_s"),
                   "extra_mm": tch.get("extra_stroke_mm"), "max_att": tch.get("max_abs_att_deg"),
                   "crawler_min_kN": tch.get("min_crawler_kN"), "t_ready": r.get("t_ready"),
                   "osc_first_last_max": [amps[0], amps[-1], max(amps)] if amps else None,
                   "same_cmd_as_proj": None if p is None else r["cmd_sha256"] == p["cmd_sha256"],
                   "used": r.get("p27_used_legs"), "events": r.get("events")}
    table.append(line)
    def s(v):
        x = line.get(v)
        if not x:
            return "-"
        return (f"{v}: pass {x['pass']} ext {x['extra_mm']} att {x['max_att']} touch {x['touch_s']} "
                f"crawl {x['crawler_min_kN']} ready {x['t_ready']} same {x['same_cmd_as_proj']} used {x['used']} "
                f"osc {x['osc_first_last_max']}")
    print(f"{case:8s} {lv:6s} Fs{fs:g}\n   {s('proj')}\n   {s('c1')}\n   {s('c2')}")
print("errors:", [(e["key"], e["error"]) for e in errors])
Path(sys.argv[2]).write_text(json.dumps({"rows": table, "errors": errors}, indent=1, default=str), encoding="utf-8")
