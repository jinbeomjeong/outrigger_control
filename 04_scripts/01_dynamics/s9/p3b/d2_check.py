"""S9 time-step check D2 on a common 1 ms grid (dynamics_model.md rev. 53, 5.37.10 D2).

Compares the P3a G1 B lift run at dt 5e-5 s (``batch_DT_20261026_122444/DT_P3a_G1_B_dt5e-5``)
with the dt 1e-4 s run (``batch_P3a_20261026_092653/P3a_G1_B``), interpolated onto the 1 ms
rows of the dt 1e-4 run: end-point sinkage and attitude, trajectory max differences
(sinkage, attitude, F_cyl / peak), settle references, P3a-7 end attitude, lift-off time,
P3a checks and the abort flag. The printed values are the source of ``D2_end_point`` in
``merge_out.py`` (copied there by hand).

Inputs: ``07_results/S9/`` (git-external raw data).
Output: standard output only.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/d2_check.py
"""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
RESULTS_S9 = ROOT / "07_results" / "S9"
RUN_DT_HALF = RESULTS_S9 / "batch_DT_20261026_122444" / "DT_P3a_G1_B_dt5e-5"
RUN_DT_REF = RESULTS_S9 / "batch_P3a_20261026_092653" / "P3a_G1_B"


def main():
    a = np.load(RUN_DT_HALF / "series.npz")
    b = np.load(RUN_DT_REF / "series.npz")
    ra = json.loads((RUN_DT_HALF / "result.json").read_text("utf-8"))
    rb = json.loads((RUN_DT_REF / "result.json").read_text("utf-8"))
    ta, tb = a["t_s"], b["t_s"]
    print("len", len(ta), len(tb), ta[-1], tb[-1], "dt", ra["meta"]["dt_s"], rb["meta"]["dt_s"])

    def on(key):
        """Series `key` of run a interpolated onto the 1 ms grid of run b, and run b's series."""
        xa, xb = a[key], b[key]
        if xa.ndim == 1:
            return np.interp(tb, ta, xa), xb
        return np.stack([np.interp(tb, ta, xa[:, j]) for j in range(xa.shape[1])], 1), xb

    sa, sb = on("pad_sinkage_geometric_m")
    rpa, rpb = on("roll_pitch_deg")
    fa, fb = on("F_cyl_N")
    ea = sa[-1]
    eb = sb[-1]
    print("end point sink mm", ea * 1e3, eb * 1e3, "rel %", 100 * (ea / eb - 1))
    print("end point rp diff deg", rpa[-1] - rpb[-1], "norm", np.linalg.norm(rpa[-1] - rpb[-1]))
    print("max |d sink| over run mm", np.abs(sa - sb).max() * 1e3)
    print("max |d rp| over run deg", np.abs(rpa - rpb).max(axis=0))
    print("max |dF|/Fmax %", 100 * np.abs(fa - fb).max(axis=0) / fb.max(axis=0))
    attitude_a = ra["p3a"]["P3a-7_attitude"]
    attitude_b = rb["p3a"]["P3a-7_attitude"]
    ref_a = np.array(attitude_a["settle_end_roll_pitch_deg"])
    ref_b = np.array(attitude_b["settle_end_roll_pitch_deg"])
    print("settle ref a/b", ref_a, ref_b, "diff", ref_a - ref_b)
    print("d_end a/b", attitude_a["d_roll_pitch_end_deg"], attitude_b["d_roll_pitch_end_deg"])
    for k in ("P3a-2_liftoff",):
        print(k, ra["p3a"][k]["t_liftoff_s"], rb["p3a"][k]["t_liftoff_s"])
    print("checks a", ra["p3a"]["checks"])
    print("abort", ra["args"].get("abort_on_limit"))


if __name__ == "__main__":
    main()
