"""Count D-1 (436.8 H-1) rows by record item values.probe_attitude_change_deg (E-2 opportunity proxy)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

f = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1\h1_d1.jsonl")
rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
out = {}
for s in ("V0", "VB"):
    v = []
    keys = defaultdict(list)
    for r in rows:
        if r["job"]["setting"] != s:
            continue
        x = r.get("values", {}).get("probe_attitude_change_deg")
        if isinstance(x, (int, float)):
            v.append(x)
            keys[r["job"]["d1"]["key"]].append(x)
    a = np.asarray(v)
    out[s] = {"n": int(a.size), "q50": float(np.median(a)), "q90": float(np.percentile(a, 90)),
              "n_gt_0.07": int((a > 0.07).sum()), "n_gt_0.10": int((a > 0.10).sum()),
              "keys_gt_0.07": sum(1 for k in keys.values() if max(k) > 0.07),
              "keys_gt_0.10": sum(1 for k in keys.values() if max(k) > 0.10)}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
