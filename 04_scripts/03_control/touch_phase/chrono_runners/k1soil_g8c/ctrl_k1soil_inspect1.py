"""Print structure of K1 soil result files: top keys, soil_event, judgement, npz key lists, job side."""
import json
import sys
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
d = BATCH / "S9EV_G1_FLFs0_RE1bF_on"
res = json.loads((d / "result.json").read_text(encoding="utf-8"))
print("TOP", {k: type(v).__name__ for k, v in res.items()})
se = res.get("soil_event")
print("SOIL_EVENT keys", list(se) if isinstance(se, dict) else se)
for k, v in se.items():
    if k != "judgement":
        s = json.dumps(v, default=str)
        print(" ", k, s[:400])
print("JUDGEMENT")
for k, v in se["judgement"].items():
    print(" ", k, json.dumps(v, default=str)[:600])
print("SIDE", (d / "k1soil_job_side.json").read_text(encoding="utf-8")[:2500])
for name in ("soil_event_series.npz", "r8_series.npz", "controller_commands.npz", "completion_series.npz", "step_series.npz"):
    z = np.load(d / name, allow_pickle=True)
    print(name, {k: z[k].shape for k in z.files})
print("record", [p.name for p in (d / "record").iterdir()][:30])
