"""H5 reading: |dM3| by comparison on the 72 keys; equal-timing sensor swaps (A-k vs B-k, C-k vs R0) against
timing-only changes (R0-nochk vs R0) and mixed (B-k vs R0-nochk); TOUCH-start difference vs |dM3|."""
import json
import sys
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
keys = [k.strip() for k in (d / "h5_R0-nochk_keys.txt").read_text(encoding="utf-8").splitlines() if k.strip()]
print("key file lines", len(keys), keys[:2])
runs = {}
for path in sorted(d.glob("imuatt_*_*.jsonl")):
    arm = path.name.split("_")[1]
    if arm not in ("R0", "R0-nochk", "A-k", "B-k", "C-k", "B-r"):
        continue
    for text in path.read_text(encoding="utf-8").splitlines():
        if text.strip():
            ln = json.loads(text)
            runs[(ln["arm"], ln["level"], int(ln["seed_index"]), ln["case_id"])] = ln["run_metrics"]
ids = sorted({(lv, s, c) for (a, lv, s, c) in runs if a == "R0-nochk"})
print("R0-nochk runs", len(ids))


def comp(a, b):
    dm, dt, sign = [], [], []
    for lv, s, c in ids:
        x, y = runs.get((a, lv, s, c)), runs.get((b, lv, s, c))
        if x is None or y is None or x["M3_kN"] is None or y["M3_kN"] is None:
            continue
        dm.append(x["M3_kN"] - y["M3_kN"])
        dt.append((x["t_touch_start_s"] or np.nan) - (y["t_touch_start_s"] or np.nan))
    dm, dt = np.array(dm), np.array(dt)
    ad = np.abs(dm)
    return {"n": len(dm), "n_gt2": int((ad > 2).sum()), "n_gt0p5": int((ad > 0.5).sum()),
            "n_eq_0p01": int((ad <= 0.01).sum()), "med_abs": round(float(np.median(ad)), 3),
            "p90_abs": round(float(np.quantile(ad, 0.9)), 3), "max_abs": round(float(ad.max()), 3),
            "neg_gt2": int((dm < -2).sum()), "pos_gt2": int((dm > 2).sum()), "mean": round(float(dm.mean()), 3),
            "dt_touch_med": round(float(np.nanmedian(dt)), 3), "dt_touch_zero": int((np.abs(dt) < 1e-6).sum()),
            "gt2_when_dt0": int(((ad > 2) & (np.abs(dt) < 1e-6)).sum()),
            "gt2_when_dt_ne0": int(((ad > 2) & (np.abs(dt) >= 1e-6)).sum()),
            "n_dt_ne0": int((np.abs(dt) >= 1e-6).sum())}


for a, b in (("A-k", "B-k"), ("B-r", "B-k"), ("C-k", "R0"), ("R0-nochk", "R0"), ("B-k", "R0"),
             ("B-k", "R0-nochk"), ("A-k", "R0-nochk")):
    print(f"{a:9s} - {b:9s}", comp(a, b))
