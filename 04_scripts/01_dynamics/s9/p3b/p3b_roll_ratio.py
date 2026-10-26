"""S9 P3b end-state roll stiffness ratio W h / K_roll (dynamics_model.md rev. 53, 5.37.3 / 5.38).

End-state roll tangent stiffness on the virgin branch (k_t = n N / s per pad, 5.37.3),
K_roll = sum k_t (y - y_c)^2 about the load centre, against W h for the 24 P3b cases; plus
the LEVEL-phase count, creep stop - last READY entry and the 5 s DONE shift (5.38.3).

Inputs: the ``p3b_judge.py`` intermediate JSON (``soil_n``, ``pad_N_end_kN``, ``sink_end_mm``),
``06_analysis/01_chrono/19_S9/s9_P3b_summary.json`` and
``07_results/S9/batch_P3b_20261026_122444/P3b_*/result.json``.
Output: one intermediate JSON (merged by ``merge_out.py``) plus one printed line per case.

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/p3b_roll_ratio.py
      <judge_json> <out_json>
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
B = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
SUMMARY_JSON = ROOT / "06_analysis" / "01_chrono" / "19_S9" / "s9_P3b_summary.json"
PAD_Y_M = np.array([1.3238, -1.3238, 1.1679, -1.2429])  # pad y, body frame
COM_HEIGHT_ABOVE_PAD_BOTTOM_M = 3.468  # (5.37.3, top auger)
WEIGHT_N = 380112.9  # superstructure + rods / pads (5.38 W)
MIN_SINKAGE_M = 1e-4  # floor for s in k_t = n N / s


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("judge_json", type=Path)
    parser.add_argument("out_json", type=Path)
    return parser.parse_args()


def main():
    args = _parse_args()
    S = json.loads(SUMMARY_JSON.read_text("utf-8"))["rows"]
    J = json.loads(args.judge_json.read_text("utf-8"))["cases"]
    Y = PAD_Y_M
    H = COM_HEIGHT_ABOVE_PAD_BOTTOM_M
    W = WEIGHT_N
    out = {}
    for k, s in S.items():
        c = J[k]
        n = c["soil_n"]
        N = np.array(c["pad_N_end_kN"]) * 1e3
        z = np.array(c["sink_end_mm"]) * 1e-3
        kt = n * N / np.maximum(z, MIN_SINKAGE_M)
        Kroll = float(np.sum(kt * (Y - np.sum(N * Y) / N.sum()) ** 2))
        r = json.loads((B / k / "result.json").read_text("utf-8"))
        nlevel = sum(1 for p in r["phases"] if p["phase"] == "level")
        cs_minus_ready = (s["creep_stop"]["t_final_two_sided_s"]
                          - s["P3-4_attitude"]["t_ready_last_entry_s"])
        out[k] = dict(ratio_Wh_over_Kroll=W * H / Kroll, Kroll=Kroll, n_level=nlevel,
                      cs_minus_ready=cs_minus_ready,
                      shift5=s["P3-4_attitude"]["done"]["shift_5s_end_minus_done_deg"])
        print(k[4:], f"Wh/K {W*H/Kroll:.3f}", "levels", nlevel,
              f"cs-ready {out[k]['cs_minus_ready']:.1f}",
              [round(x, 4) for x in out[k]["shift5"]])
    args.out_json.write_text(json.dumps(out, indent=1), "utf-8")


if __name__ == "__main__":
    main()
