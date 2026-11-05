"""Step convergence of the single-leg bench: dt 1e-5 against 5e-6 s."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench
import numpy as np
from bench import Bench, load_params, open_metrics, pin, run

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\pressure_review\m1_hopsan")
pin()
p = load_params()
rows = []
for mode, kw in (("ramp_vent", {}), ("ramp_floor_ref", {"pilot_ref_b": True}), ("ramp_block", {"neutral": "block"})):
    for a in (0.05, 0.25):
        v = a * p.v_max
        vals = {}
        for ts in (1e-5, 5e-6):
            bench.TS = ts
            b = Bench(f"conv_{mode}_{a:g}_{ts:g}", 2, 125e5, F_s=3332.0, cmd_t=np.array([0.0, 0.006 / v]), cmd_u=np.array([-v, 0.0]), **kw)
            res = run(b, p, Path(__file__).resolve().parent / "t7")
            vals[ts] = open_metrics(b, res)
        r = {"mode": mode, "alpha": a, "stroke_1e-5": vals[1e-5]["stroke_open_mm"], "stroke_5e-6": vals[5e-6]["stroke_open_mm"]}
        r["change"] = r["stroke_5e-6"] / r["stroke_1e-5"] - 1.0
        rows.append(r)
        print(r, flush=True)
(OUT / "t7_conv.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
