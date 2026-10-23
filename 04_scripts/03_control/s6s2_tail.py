"""S6 stage 2: the levelling tail (G1 roll 3 deg): true attitude, IMU-measured attitude, heave (strokes) per second
from LEVEL + 6 s to DONE, Chrono vs reduced. Chrono IMU attitude from record meas.specific_force (atan2 as the
reduced Sensors), mean stroke from meas.stroke_corrected.
Run: conda run -n dynamics-dev python -I s6s2_tail.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
import s6_target_sim as sts  # noqa: E402


def quat_rp(q):
    w, x, y, z = q.T
    return (np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))),
            np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))))


def filt2(x, T=0.02, tau=0.5):
    a = T / tau; y1 = np.empty_like(x); y2 = np.empty_like(x); y1[0] = y2[0] = x[0]
    for i in range(1, len(x)):
        y1[i] = y1[i - 1] + a * (x[i] - y1[i - 1]); y2[i] = y2[i - 1] + a * (y1[i] - y2[i - 1])
    return y2


_LAST = {}


def main():
    name = "G1_top_roll3"
    d = ROOT / "07_results" / "S6" / "stage2_20261021_213235" / name
    r = json.loads((d / "result.json").read_text())
    z = np.load(d / "record" / "record.npz")
    t = z["t"] - r["settings"]["start_t_s"]
    tl = next(tt for tt, n in r["phases"] if n == "level"); td = next(tt for tt, n in r["phases"] if n == "done")
    ro, pi = quat_rp(z["body_quat_wxyz"])
    fb = z["meas.specific_force"]
    imu_r = filt2(np.degrees(np.arctan2(fb[:, 1], fb[:, 2])))
    imu_p = filt2(np.degrees(np.arctan2(-fb[:, 0], np.hypot(fb[:, 1], fb[:, 2]))))
    s = z["meas.stroke_corrected"].mean(axis=1) * 1e3
    rows_c = []
    for k in np.arange(6, td - tl + 1.0, 1.0):
        tt = tl + k
        rows_c.append([float(k), round(float(np.interp(tt, t, ro)), 4), round(float(np.interp(tt, t, pi)), 4),
                       round(float(np.interp(tt, t, imu_r)), 4), round(float(np.interp(tt, t, imu_p)), 4),
                       round(float(np.interp(tt, t, s)), 2)])
    import run_c2_timedomain as c2t
    orig = c2t.run_case

    def wrapped(*a, **kk):
        rr = orig(*a, **kk); _LAST["S"] = rr.get("_series"); return rr
    c2t.run_case = wrapped
    o = sts.run_tgt(dict(id="red|roll3", floor_deg=(3.0, 0.0), level="top", contact="pressure",
                         tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
    S = _LAST["S"]
    ts = np.asarray(S["t"]); tl2 = o["t_touch_s"]; td2 = o["t_done_s"]
    att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
    im = np.column_stack([filt2(np.degrees(np.asarray(S["phi_m"]))), filt2(np.degrees(np.asarray(S["theta_m"])))])
    x = np.asarray(S["x"]).mean(axis=1) * 1e3
    clr = np.asarray(S["clr"]) * 1e3
    rows_r = []
    for k in np.arange(6, td2 - tl2 + 1.0, 1.0):
        tt = tl2 + k
        rows_r.append([float(k), round(float(np.interp(tt, ts, att[:, 0])), 4), round(float(np.interp(tt, ts, att[:, 1])), 4),
                       round(float(np.interp(tt, ts, im[:, 0])), 4), round(float(np.interp(tt, ts, im[:, 1])), 4),
                       round(float(np.interp(tt, ts, x)), 2), round(float(np.interp(tt, ts, clr)), 2)])
    out = {"cols": ["s_after_level", "true_roll", "true_pitch", "imu_f_roll", "imu_f_pitch", "mean_stroke_mm", "clr_mm"],
           "chrono": rows_c, "reduced": rows_r, "chrono_done_after_level": td - tl, "reduced_done_after_level": td2 - tl2}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
    print("chrono"); [print(rw) for rw in rows_c]
    print("reduced"); [print(rw) for rw in rows_r]


if __name__ == "__main__":
    main()
