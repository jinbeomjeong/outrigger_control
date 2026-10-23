"""S6 stage 2 extra checks for spec revision 3 (integrity-checker items 2, 3, 5).

(2) REANCHOR attitude change: max |true roll/pitch - value at REANCHOR start| during REANCHOR (record.npz, 20 ms).
(3) Item 8 levelling-time trend: LEVEL -> READY per level for each floor (Chrono) - differences between levels.
(5) Item 2 linearity: (grade mean attitude error - ideal mean error) vs the grade zero angle (IMU_GRADES), per axis.
Run: conda run -n dynamics-dev python -I s6s2_extra_checks.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "03_src"))
from outrigger_sim.sensors.imu import IMU_GRADES  # noqa: E402

B1 = ROOT / "07_results" / "S6" / "stage2_20261021_213235"
B2 = ROOT / "07_results" / "S6" / "stage2_20261021_214443"


def cdir(name):
    return B2 / name if (B2 / name).is_dir() else B1 / name


def quat_rp(q):
    w, x, y, z = q.T
    return (np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))),
            np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))))


def load(name):
    d = cdir(name)
    r = json.loads((d / "result.json").read_text())
    z = np.load(d / "record" / "record.npz")
    t = z["t"] - r["settings"]["start_t_s"]
    ro, pi = quat_rp(z["body_quat_wxyz"])
    return r, t, np.column_stack([ro, pi])


def main():
    out = {"reanchor": {}, "level_time": {}, "linearity": {}}
    for d in sorted(B1.iterdir()):
        if not d.is_dir():
            continue
        r, t, att = load(d.name)
        ph = r["phases"]
        for i, (t0, n) in enumerate(ph):
            if n == "reanchor":
                t1 = ph[i + 1][0] if i + 1 < len(ph) else t[-1]
                m = (t >= t0) & (t <= t1)
                a0 = att[np.searchsorted(t, t0)]
                out["reanchor"].setdefault(d.name, []).append(
                    round(float(np.max(np.abs(att[m] - a0))), 4))
    for floor in ("flat", "roll5.5", "fdown3.5", "fup3.5"):
        row = {}
        for lvl in ("top", "middle", "bottom"):
            g = "G2-R" if floor in ("fdown3.5", "fup3.5") else "G2"
            r, t, _ = load(f"{g}_{lvl}_{floor}")
            tl = next(tt for tt, n in r["phases"] if n == "level")
            row[lvl] = round(r["ready_t_s"] - tl, 2)
        row["mid-top"] = round(row["middle"] - row["top"], 2); row["bot-mid"] = round(row["bottom"] - row["middle"], 2)
        out["level_time"][floor] = row
    summ = json.loads((ROOT / "06_analysis" / "01_chrono" / "16_S6" / "verify_S6_L1_closed_loop.json").read_text())
    cases = summ["cases"]
    for floor, ideal in (("flat", "G2_top_flat"), ("fdown3.5", "G2-R_top_fdown3.5")):
        e0 = np.array(cases[ideal]["att_err_last5_mean_deg"])
        for g in ("good_zeroed", "normal_zeroed", "normal_zeroed_repeatability", "normal_as_shipped"):
            name = f"G3_top_{floor}_{g}"
            if name not in cases:
                continue
            e = np.array(cases[name]["att_err_last5_mean_deg"])
            b = IMU_GRADES[g].zero_error_deg
            expect = np.array([-b, +b])   # +y bias reads +roll -> true roll -b; +x bias reads nose-up -> true pitch +b
            out["linearity"][name] = {"zero_deg": b, "delta_deg": (e - e0).round(4).tolist(),
                                      "delta_minus_expect_deg": (e - e0 - expect).round(4).tolist()}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
