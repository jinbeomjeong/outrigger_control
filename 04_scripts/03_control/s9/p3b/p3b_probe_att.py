"""S9 P3b attitude change across each probe vs per-leg probe sinkage (spec rev. 60, 311).

Cause check for the P3-4 residual-budget misses: for each case and each probe, the per-leg
sinkage change is fitted with a plane z = a + b x + c y (pads go down by the sinkage) and the
predicted roll / pitch change is printed next to the measured true change. Also prints the
true attitude at the last READY entry, the end mean attitude, and the crawler load / P3-2
flags at LOC.

Pad plan positions: the script looks for a pad-centre key in YAML ``legs.<leg>``; the current
YAML has none, so it prints the available keys and falls back to the approximate positions
x +2.0 / -2.7 m, y +-1.324 / +-1.168 m (ASSUMPTION, spec 311: approximate, used only for the
prediction-vs-measurement match).

Inputs: ``06_analysis/02_control/s9/p3b/p3b_collect.json`` (from ``p3b_collect.py``),
``07_results/S9/batch_P3b_20261026_122444/P3b_*/step_series.npz``, ``02_params/rexome33.yaml``.
Output: standard output only.

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p3b_probe_att.py
      [<collect_json> [<batch_dir>]]
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DEFAULT_COLLECT = ROOT / "06_analysis" / "02_control" / "s9" / "p3b" / "p3b_collect.json"
PARAMS_YAML = ROOT / "02_params" / "rexome33.yaml"
LEG_NAMES = ["FL", "FR", "RL", "RR"]
PAD_XY_KEYS = ("pad_center_xy_m", "pad_xy_m", "ground_point_m", "pad_position_m")
FALLBACK_PAD_XY = [[2.0, 1.324], [2.0, -1.324], [-2.7, 1.168], [-2.7, -1.168]]  # ASSUMPTION


def find_xy(legs, leg):
    """Pad plan position (x, y) of a leg from the YAML legs block, or None if no known key."""
    blk = legs[leg]
    for key in PAD_XY_KEYS:
        if key in blk:
            return blk[key][:2]
    return None


def _pad_plan_positions():
    params = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
    legs = params["legs"]
    xy = [find_xy(legs, n) for n in LEG_NAMES]
    if any(v is None for v in xy):
        print("pad keys:", list(legs["FL"].keys()))
        xy = FALLBACK_PAD_XY
        print("using fallback xy (ASSUMPTION)", xy)
    return np.array(xy, dtype=float)


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("collect_json", nargs="?", type=Path, default=DEFAULT_COLLECT)
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    return parser.parse_args()


def main():
    args = _parse_args()
    d = json.loads(args.collect_json.read_text(encoding="utf-8"))
    batch = args.batch_dir
    xy = _pad_plan_positions()
    A = np.column_stack([np.ones(4), xy[:, 0], xy[:, 1]])

    for k, v in d.items():
        ss = np.load(batch / k / "step_series.npz")
        ts, rp = ss["t_s"], ss["roll_pitch_deg"]

        def att(t, ts=ts, rp=rp):
            i = int(np.clip(np.searchsorted(ts, t), 0, len(ts) - 1))
            return rp[i]

        phases = v["phases"]
        readies = [p["t_s"] for p in phases if p["phase"] == "ready"]
        line = [k[4:]]
        for pr in v["P3-5"]["probe_sinkage"]:
            dsk = np.array(pr["d_sinkage_m"])
            # plane fit z = a + b x + c y to -sinkage (pad goes down by sinkage)
            coef, *_ = np.linalg.lstsq(A, -dsk, rcond=None)
            # pitch > 0 nose down: a front-low plane has dz/dx < 0, hence the minus sign
            # (spec 311 checks the sign against the measured change)
            pitch_pred = math.degrees(-coef[1])
            roll_pred = math.degrees(coef[2])
            a0, a1 = att(pr["t_start_s"]), att(pr["t_end_s"])
            line.append(f"probe {pr['t_start_s']:.1f}-{pr['t_end_s']:.1f} "
                        f"dsink mm {np.round(dsk*1e3,1).tolist()} "
                        f"att chg {np.round(a1-a0,4).tolist()} "
                        f"pred(roll,pitch?) {roll_pred:.4f},{pitch_pred:.4f}")
        a_ready = att(readies[-1]) if readies else None
        line.append(f"att@lastREADY {np.round(a_ready,4).tolist()} "
                    f"end {np.round(v['P3-4']['end_mean_roll_pitch_deg'],4).tolist()}")
        p2 = v["P3-2"]
        line.append(f"crawler@LOC {p2['crawler_normal_at_loc_N']:.0f} N "
                    f"loaded {p2['crawler_loaded_at_loc']} "
                    f"LOC<DONE {p2['loc_before_first_done']}")
        print(" | ".join(line))


if __name__ == "__main__":
    main()
