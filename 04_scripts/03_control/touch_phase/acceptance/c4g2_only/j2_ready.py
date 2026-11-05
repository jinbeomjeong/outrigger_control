"""J2 soil rows: event time and return to READY, C4G2 only against stored off, READY of the base run, hold state via first command difference is not stored. E core 27."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
a = {r["key"]: r for r in load(ACC / "c4g2_only/soil/soil_A.json")["results"]}
o = {r["key"]: r for r in load(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85\finB2_A.json")["results"]}
worst = []
for k in a:
    if "|J2|" not in k:
        continue
    print(k, "base t_ready c/o", a[k]["base"]["t_ready"], o[k]["base"]["t_ready"], "t_done c/o", a[k]["base"]["t_done"], o[k]["base"]["t_done"], "t_loc", a[k]["base"]["t_loc"], o[k]["base"]["t_loc"])
    for r, s in zip(a[k]["runs"], o[k]["runs"]):
        if r["timing"] == "level":
            print("   ", r["event"], "t_ev c/o", r["t_ev_s"], s["t_ev_s"], "ready c/o", r["t_ready_back_s"], s["t_ready_back_s"], "abs c/o", round(r["t_ev_s"] + (r["t_ready_back_s"] or 0), 1), round(s["t_ev_s"] + (s["t_ready_back_s"] or 0), 1))
            worst.append(r["t_ev_s"] + (r["t_ready_back_s"] or 0))
print("max absolute READY s", round(max(worst), 1))
