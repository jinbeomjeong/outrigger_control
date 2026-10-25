"""D-S8-5 (1): per-case zero-calibration table of an S8 batch.

For every case: pressure grade, F_s, c_i (offset), F_s,air, and checks
  F_nominal - (F_hat - c_i)          (should be 0: nominal = calibrated reading)
  F_pressure - (p_h A_p - p_r A_ann) (areas fitted per leg by least squares)
  F_pressure - (F_cyl - f_seal)      (reading law of the ideal sensor, 199)
Usage: python -I ds85_calib_table.py <batch dir>
"""
import json
import os
import sys

import numpy as np

B = sys.argv[1]
cases = sorted(c for c in os.listdir(B) if os.path.isdir(os.path.join(B, c)))
print(f"{'case':38s} {'grade':7s} Fs  c_FL    c_FR    c_RL    c_RR   [kN] | Fs_air[kN]       | nom-chk[N] law[N] A_p/A_ann")
for c in cases:
    d = os.path.join(B, c)
    try:
        with open(os.path.join(d, "result.json"), encoding="utf-8") as fh:
            r = json.load(fh)
    except FileNotFoundError:
        continue
    st = r["settings"]
    grade = st.get("pressure_grade")
    fs = st.get("s8", {}).get("fs_kN")
    zc = r["controller_meta"].get("zero_calibration", {})
    res = (zc.get("result") or {}).get("legs", {})
    off = np.array(zc.get("offsets_N", [np.nan] * 4))
    fair = [res.get(k, {}).get("air_seal_friction_N") for k in ("FL", "FR", "RL", "RR")]
    status = [res.get(k, {}).get("status", "-")[:3] for k in ("FL", "FR", "RL", "RR")]
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    pads = np.load(os.path.join(d, "pads.npz"))
    chk = np.nan
    if "F_nominal_N" in r8.files:
        post = r8["t"] > (zc.get("result") or {}).get("t_end_s", 1e9) + 0.05
        chk = np.abs(r8["F_nominal_N"][post] - (r8["F_hat_N"][post] - off)).max()
    ph, pr, Fp = pads["head_pressure"], pads["rod_pressure"], pads["F_pressure"]
    areas = []
    for leg in range(4):
        X = np.c_[ph[:, leg], -pr[:, leg]]
        sol, *_ = np.linalg.lstsq(X, Fp[:, leg], rcond=None)
        areas.append(sol)
    areas = np.array(areas)
    law = np.abs(Fp - (pads["F_cyl"] - pads["f_seal"])).max()
    print(f"{c:38s} {str(grade):7s} {fs:3.0f} " + " ".join(f"{v / 1e3:+6.3f}" for v in off)
          + " | " + " ".join("  -  " if v is None else f"{v / 1e3:5.2f}" for v in fair)
          + f" | {chk:8.2e} {law:7.1e} " + " ".join(f"{a[0]:.6f}/{a[1]:.6f}" for a in areas[[0, 2]])
          + " " + "".join(status))
