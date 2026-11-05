"""Raw pad normal force during the 44 J_C-missed windows, against the 20 ms airborne flag."""
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = r"C:\workspace\outrigger_control"
D = Path(ROOT) / r"06_analysis\02_control\paper\ml_jc"
h = json.load(open(D / "ml_jc_head.json", encoding="utf-8"))
SETS = ("train", "validation", "test", "OOD-1", "OOD-2", "MLJ")
LEGS = ("FL", "FR", "RL", "RR")
out = []
for s in SETS:
    for it in h[s]:
        for r in it["rows"]:
            if r["scope"] != "scored" or r["JC_first_decision_s"] is not None:
                continue
            src = it["meta"]["source"]
            folder = src if os.path.isabs(src) else os.path.join(ROOT, src)
            p = np.load(os.path.join(folder, "pads.npz"), allow_pickle=False)
            t = p["t"]
            i = LEGS.index(r["leg"])
            w = (t > r["t_on_s"] - 0.1) & (t <= r["t_on_s"] + (r["samples"] - 1) * 0.1 + 1e-9)
            raw = p["N_raw"][w, i]
            flt = p["N"][w, i]
            air = p["airborne"][w, i].astype(bool)
            zero = raw <= 0
            run_max = cur = 0
            for z in zero:
                cur = cur + 1 if z else 0
                run_max = max(run_max, cur)
            out.append({"run": r["run"], "leg": r["leg"], "lift": r["is_lift"], "air_ms": int(air.sum()), "raw_le0_ms": int(zero.sum()), "raw_run_ms": run_max, "N_le0_ms": int((flt <= 0).sum()), "F_fields": None, "F_min_field": float(p["F_cyl_min_interval"][w, i].min()) / 1e3, "F_1ms": float(p["F_cyl"][w, i].min()) / 1e3, "rec": r["true_min_kN"]})
print("n", len(out), "raw run max", max(o["raw_run_ms"] for o in out), "raw total max", max(o["raw_le0_ms"] for o in out), "air max", max(o["air_ms"] for o in out))
print("raw>0 any", sum(o["raw_le0_ms"] > 0 for o in out), "air>0", sum(o["air_ms"] > 0 for o in out), "lift & raw>0", sum(o["lift"] and o["raw_le0_ms"] > 0 for o in out), "nolift & raw>0", sum((not o["lift"]) and o["raw_le0_ms"] > 0 for o in out))
print("cross", Counter((o["lift"], o["raw_le0_ms"] > 0, o["air_ms"] > 0) for o in out))
print("lift no air rows", [(o["run"], o["raw_le0_ms"], o["raw_run_ms"]) for o in out if o["lift"] and o["air_ms"] == 0])
print("record==min_interval field max diff", max(abs(o["F_min_field"] - o["rec"]) for o in out))
print("raw run distribution", sorted(Counter(o["raw_run_ms"] for o in out).items()))
