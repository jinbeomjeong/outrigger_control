"""Rev. 51: rod-pressure behaviour at pad lift-off (1 ms truth) for all lift-offs of the main ML
batch: is the plant valve locked at lift-off (|u_applied| <= 1e-6 m/s, 10 Hz hold) and how much
does the rod pressure change from 5 ms before to 10 ms after the airborne onset?

Usage: python -I s8main_liftoff_rod.py <batch_dir> <events_json> <out_json>
Only episodes with an L event (events_json from s8main_events.py) are read.
Lock-law expectation (H-S8-2 table 3, locked leg unloading): rod pressure rises or stays high.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
batch = Path(sys.argv[1])
ev = json.load(open(sys.argv[2], encoding="utf-8"))["rows"]
out = Path(sys.argv[3])
items = []
for r in ev:
    if not r["any_l"]:
        continue
    case = batch / "episodes" / r["case"]
    with np.load(case / "pads.npz", allow_pickle=True) as p:
        tp = p["t"]
        air = p["airborne"].astype(bool)
        rp = p["rod_pressure"] / 1e5
        hp = p["head_pressure"] / 1e5
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    t10 = rec["t"]
    ua = rec["u_applied"]
    for L in range(4):
        on = np.flatnonzero(np.diff(air[:, L].astype(int)) == 1) + 1
        for i in on:
            if i < 6 or i + 10 >= len(tp):
                continue
            k = np.searchsorted(t10, tp[i], side="right") - 1
            locked = abs(float(ua[k, L])) <= 1e-6 if k >= 0 else False
            items.append({"case": r["case"], "leg": LEGS[L], "t_s": float(tp[i]), "locked": bool(locked),
                          "rod_before": float(rp[i - 5, L]), "rod_after": float(rp[i + 10, L]),
                          "rod_max_before": float(rp[max(i - 50, 0):i, L].max()),
                          "head_before": float(hp[i - 5, L]), "head_after": float(hp[i + 10, L])})
json.dump({"liftoffs": items}, open(out, "w", encoding="utf-8"), indent=1)
lk = [x for x in items if x["locked"]]
print(f"lift-offs {len(items)}; locked at lift-off {len(lk)}")
drop = [x for x in lk if x["rod_before"] - x["rod_after"] > 50]
rise = [x for x in lk if x["rod_after"] - x["rod_before"] > 5]
print(f"  locked: rod drop > 50 bar across lift-off {len(drop)}; rod rise > 5 bar {len(rise)}")
for x in drop[:20]:
    print(f"    {x['case']} {x['leg']} {x['t_s']:.3f}: rod {x['rod_before']:.1f} -> {x['rod_after']:.1f} (max 50 ms before {x['rod_max_before']:.1f}), head {x['head_before']:.1f} -> {x['head_after']:.1f}")
mv = [x for x in items if not x["locked"]]
dmv = [x for x in mv if x["rod_before"] - x["rod_after"] > 50]
print(f"  valve open at lift-off: {len(mv)}, rod drop > 50 bar {len(dmv)}")
rb = np.array([x["rod_before"] for x in lk])
ra = np.array([x["rod_after"] for x in lk])
if len(lk):
    print(f"  locked: rod before p50 {np.median(rb):.1f} max {rb.max():.1f}; after p50 {np.median(ra):.1f} max {ra.max():.1f} bar")
