"""S9 P3b per-probe pad sinkage change and true attitude change (dynamics_model.md rev. 53, 5.38).

For each P3b case and each probe window recorded by the runner
(``p3b.P3-5_clearance_stroke.probe_sinkage``): start / end time, per-leg sinkage change [mm]
and the true roll / pitch change [deg] from ``step_series.npz`` over the same window.

Input: ``07_results/S9/batch_P3b_20261026_122444/P3b_*/`` (result.json, step_series.npz).
Output: standard output only.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/probe_sink.py [<batch_dir>]
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    return parser.parse_args()


def main():
    batch = _parse_args().batch_dir
    for d in sorted(batch.glob("P3b_*")):
        if not d.is_dir():
            continue
        r = json.loads((d / "result.json").read_text("utf-8"))
        ps = r["p3b"]["P3-5_clearance_stroke"].get("probe_sinkage", [])
        z = np.load(d / "step_series.npz")
        t, rp = z["t_s"], z["roll_pitch_deg"]
        rows = []
        for p in ps:
            i0 = np.searchsorted(t, p["t_start_s"])
            i1 = min(np.searchsorted(t, p["t_end_s"]), len(t) - 1)
            rows.append((round(p["t_start_s"], 1), round(p["t_end_s"], 1),
                         [round(x * 1e3, 2) for x in p["d_sinkage_m"]],
                         [round(x, 4) for x in (rp[i1] - rp[i0])]))
        print(d.name[4:], rows)


if __name__ == "__main__":
    main()
