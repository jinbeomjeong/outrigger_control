"""G' window shift, part 4: calibrate the 5-DoF reduced model (g00_rock_model) to the stored V0 reruns
of the stored shape (30 mm / 0.05 s) and keep an ensemble of good parameter sets.

Grid: kf (axial stiffness factor) x cf (all dashpots) x h (CoM height above the pad plane) x ktf
(tangential stiffness factor); mu 0.5 (ASSUMPTION, pad friction coefficient of the L1 bushing model).
(A first coarser grid kf 0.75..1.0, h 1.70..2.05, ktf 0.5..2 put the optimum at the h edge 2.05; this is the
refined grid.)
Targets per stored run (event leg / diagonal of the same key, own valve history):
  t_contact, t_relift, t_r* and t_h* (controller-effective edges, g03 offsets), v_imp, F_peak, gap max,
  diagonal lift / land.
Cost = sum of squared errors with weights (ms^2 for times, kN^2 x 0.05, (mm/s)^2 x 1e-3, mm^2).
Stage 1 grid on the two o0.0 runs; stage 2 evaluates the 12 best sets on all 8 V0 runs; ensemble = 6 best.
Usage: python -I -B g04_calibrate.py <rerun_dir> <out_folder>
"""
import csv
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g00_rock_model as rm  # noqa: E402

rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
STEMS = [(f"R12_bottom-{lg}-Fs{fs}-o{o}-RE1bF-ready_V0", 0 if lg == "FL" else 1, float(fs))
         for lg, fs in (("FL", 2), ("FR", 4)) for o in ("0.0", "0.025", "0.05", "0.075")]
WT = {"t_contact": 1e6, "t_relift": 1e6, "t_r_star": 1e6, "t_h_star": 1e6, "d_lift": 2.5e5, "d_land": 2.5e5,
      "F_peak_kN": 0.05, "v_imp": 1e3, "gap_max_mm": 1.0}


def cost(f, ref):
    return float(sum(w * (f[k] - ref[k]) ** 2 for k, w in WT.items() if np.isfinite(f[k]) and np.isfinite(ref[k])))


data = {}
for stem, leg, fs in STEMS:
    valve, t, rows = rm.load_valve(rerun, stem)
    w = (t >= -0.01) & (t <= 1.0)
    data[stem] = (leg, fs, valve, rm.window_features(t[w], rows[w, 1:5], rows[w, 13:17], leg, fs))

t0 = time.time()
grid = []
stage1 = [s for s in data if "-o0.0-" in s]
for kf, cf, h, ktf in itertools.product((0.75, 0.775, 0.8, 0.825, 0.85), (0.5, 1.0, 2.0), (1.88, 2.05, 2.2, 2.35),
                                        (0.75, 1.0, 1.5)):
    c = 0.0
    feats = {}
    for stem in stage1:
        leg, fs, valve, ref = data[stem]
        tt, F, g = rm.simulate(leg, 0.03, 0.05, kf, cf, valve, h=h, ktf=ktf)
        f = rm.window_features(tt, F, g, leg, fs)
        if f is None:
            c = np.inf
            break
        feats[stem] = f
        c += cost(f, ref)
    grid.append({"kf": kf, "cf": cf, "h": h, "ktf": ktf, "cost_stage1": c})
grid.sort(key=lambda r: r["cost_stage1"])
stage2 = []
for g_ in grid[:12]:
    c = 0.0
    per = {}
    for stem, (leg, fs, valve, ref) in data.items():
        tt, F, g = rm.simulate(leg, 0.03, 0.05, g_["kf"], g_["cf"], valve, h=g_["h"], ktf=g_["ktf"])
        f = rm.window_features(tt, F, g, leg, fs)
        per[stem] = {k: round(f[k] - ref[k], 4) for k in WT}
        c += cost(f, ref)
    stage2.append({**g_, "cost_stage2": c, "errors": per})
stage2.sort(key=lambda r: r["cost_stage2"])
ens = [{k: r[k] for k in ("kf", "cf", "h", "ktf")} for r in stage2[:6]]
with (out / "g04_calibration_grid.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(grid[0]))
    w.writeheader()
    w.writerows(grid)
refs = {s: {k: round(v, 4) for k, v in d[3].items()} for s, d in data.items()}
(out / "g04_calibration.json").write_text(json.dumps({"mu": 0.5, "targets": refs, "stage2": stage2, "ensemble": ens},
                                                     indent=1), encoding="utf-8")
for r in stage2[:6]:
    worst = {k: max(abs(e[k]) for e in r["errors"].values()) for k in WT}
    print(json.dumps({k: r[k] for k in ("kf", "cf", "h", "ktf", "cost_stage2")}), "max|err|",
          json.dumps({k: round(v, 4) for k, v in worst.items()}))
print(json.dumps({"status": "ok", "grid": len(grid), "elapsed_s": round(time.time() - t0, 1)}))
