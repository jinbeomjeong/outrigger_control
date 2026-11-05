"""Phase history around the event of ML episodes; start phase census; LEVEL-event Chrono verify files."""
import glob
import json
import os
import re
from collections import Counter
from pathlib import Path

import numpy as np

ML = Path(r"C:\workspace\outrigger_control\07_results\S8\ml_main_20261025_090131\ml_dataset")
for run, te in (("ML38_ep1", 59.0), ("ML42_ep0", 65.0), ("ML17_ep4", 66.0)):
    e = np.load(ML / f"{run}.npz", allow_pickle=False)
    t, p = e["t_s"], e["phase"]
    ch = [(round(float(t[i]), 1), str(p[i])) for i in range(len(t)) if i == 0 or p[i] != p[i - 1]]
    print(run, "start", round(float(t[0]), 1), "phase changes", ch[:12])
start = Counter()
at_event = Counter()
for f in sorted(ML.glob("ML*_ep*.npz")):
    e = np.load(f, allow_pickle=False)
    meta = json.loads(str(e["meta_json"])) if "meta_json" in e.files else {}
    t, p = e["t_s"], e["phase"]
    start[str(p[0])] += 1
    te = meta.get("event_t_s")
    if te is not None:
        at_event[str(p[np.searchsorted(t, float(te)) - 1])] += 1
print("episode start phase", start, "phase just before event", at_event)
R = r"C:\workspace\outrigger_control"
hits = []
for f in glob.glob(os.path.join(R, r"07_results\S8\c7*\**\verify*.json"), recursive=True) + glob.glob(os.path.join(R, r"06_analysis\02_control\s8\**\verify*c7*.json"), recursive=True):
    hits.append(f)
print("verify files", hits[:10])
print("c72 listing", os.listdir(os.path.join(R, r"07_results\S8\c72_20261027_155426"))[:12])
for f in hits:
    v = json.load(open(f, encoding="utf-8"))
    t = {"J_C": [0, 0], "J_P": [0, 0]}
    cases = set()
    miss = []
    for r in v.get("rows", []):
        if r["item"].startswith(("item 9 J_C M1", "item 9 J_P M1")):
            m = re.search(r"episodes (\d+)", r.get("note") or "")
            if m:
                t[r["judge"]][0] += int(m[1])
                t[r["judge"]][1] += r["value"][0] or 0
                cases.add(r["case"])
                if r["judge"] == "J_C" and r["value"][0]:
                    miss.append(r["case"])
    print(os.path.relpath(f, R), "cases", len(cases), t, "J_C miss", miss[:10])
