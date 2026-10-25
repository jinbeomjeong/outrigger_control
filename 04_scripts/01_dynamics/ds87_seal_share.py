"""D-S8-7: per-episode seal-friction share of the D1'' residual vs the friction limits, and the M_eff bias.

Reads 06_analysis/00_dynamics/ds87_imu.json and the extract index.json. Prints the 15 largest one-period
seal terms with 2 sum F_s,i (all four seals flipping), and the correlation of M_eff(READY) - M with F_s.
Usage: python -I ds87_seal_share.py <extract_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
d = json.loads((ROOT / "06_analysis/00_dynamics/ds87_imu.json").read_text(encoding="utf-8"))["runs"]
idx = {e["run"]: e for e in json.loads((Path(sys.argv[1]) / "index.json").read_text(encoding="utf-8"))}
rows = sorted(((r["d_seal"]["max"], 2 * sum(idx[k]["seal_limits_N"]) / 1e3, idx[k]["fs_kN"], k, r["dr_spec"]["max"],
                r["d_lever"]["max"], r["d_timing"]["max"], r["dr_rot"]["max"], r["M_eff_ready"]) for k, r in d.items()),
              reverse=True)
print("seal_max  2sumFs  Fs  run  dr_spec_max lever_max timing_max dr_rot_max M_eff_ready")
for x in rows[:15]:
    print(x)
a = np.array([(x[0], x[1]) for x in rows])
m = a[:, 1] > 0
print("max seal / 2 sum F_s:", round(float((a[m, 0] / a[m, 1]).max()), 3))
Me = np.array([(x[8] - 38400.8366, x[2]) for x in rows])
print("M_eff(READY) - M [kg]: min", round(Me[:, 0].min(), 1), "max", round(Me[:, 0].max(), 1),
      "corr with F_s", round(float(np.corrcoef(Me[:, 0], Me[:, 1])[0, 1]), 3))
print("F_s = 0 runs M_eff - M:", [round(x[8] - 38400.8366, 1) for x in rows if x[2] == 0.0])
