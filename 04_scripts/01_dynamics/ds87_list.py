"""D-S8-7: list the 'settle' episodes of an ML batch (leg, depth, ramp, speed, level, F_s, beta)
and print the pads.npz meta_json of one episode.

Usage: python -I ds87_list.py <batch_dir> [<episode_for_meta>]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
batch = Path(sys.argv[1])
n = 0
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "result.json").exists():
        continue
    case = json.loads((d / "case.json").read_text(encoding="utf-8"))["settings"]
    ep, base = case["episode"], case["base"]
    if ep.get("kind") != "settle":
        continue
    n += 1
    v = ep["depth_m"] / ep["ramp_s"] * 1e3
    print(f"{d.name:9s} {ep['leg']} {ep['depth_m']*1e3:5.1f} mm {ep['ramp_s']:.3f} s {v:6.1f} mm/s"
          f" {base['level']:6s} Fs {base['fs_kN']:5.2f} beta {base['beta_GPa']:.3f} L0r {base['rod_dead_length_m']:.3f}"
          f" floor {base['floor_deg']}")
print("settle episodes", n)
if len(sys.argv) > 2:
    z = np.load(batch / "episodes" / sys.argv[2] / "pads.npz", allow_pickle=True)
    print(json.dumps(json.loads(str(z["meta_json"])), indent=1))
