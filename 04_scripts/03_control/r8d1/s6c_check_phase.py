"""CHECK-phase attitude of D8 boundary cases: true attitude, IMU-derived tilt, leg motion."""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])
cases = sys.argv[2:]


def rp_from_quat(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def tilt_from_f(f):
    # specific force in body frame at rest = R^T [0,0,g]; roll = atan2(fy, fz), pitch = -asin(fx/|f|)
    roll = np.degrees(np.arctan2(f[:, 1], f[:, 2]))
    pitch = np.degrees(-np.arcsin(f[:, 0] / np.linalg.norm(f, axis=1)))
    return roll, pitch


for c in cases:
    rec = np.load(batch / c / "record" / "record.npz")
    r8 = np.load(batch / c / "r8_series.npz")
    res = json.loads((batch / c / "result.json").read_text(encoding="utf-8"))
    t = rec["t"]
    ph = r8["phase"]
    roll, pitch = rp_from_quat(rec["body_quat_wxyz"])
    fr, fp = tilt_from_f(rec["meas.specific_force"])
    chk = ph == "check"
    tc = t[chk]
    print(f"== {c}: check t {tc.min():.2f}..{tc.max():.2f} s, n={chk.sum()}")
    print("   phases", res["phases"][:3])
    idx = np.where(chk)[0]
    for i in idx[:: max(1, len(idx) // 12)]:
        print(f"   t={t[i]:7.2f} true r/p={roll[i]:+.4f}/{pitch[i]:+.4f}  imu r/p={fr[i]:+.4f}/{fp[i]:+.4f}  "
              f"s_motor mm={np.round(rec['s_motor'][i]*1e3,2)} u_iss={np.round(r8['issued_u'][i]*1e3,2)} "
              f"pad={rec['pad_in_contact'][i].astype(int)} Fcr_z={rec['F_crawler'][i][2]/1e3:.1f}kN omega={np.round(np.degrees(rec['body_omega'][i]),4)}")
    i_last = idx[-1]
    w = idx[-10:]
    print(f"   last 1 s mean true r/p {roll[w].mean():+.4f}/{pitch[w].mean():+.4f}  imu {fr[w].mean():+.4f}/{fp[w].mean():+.4f}")
    print("   acceptance crawler deg", res["acceptance"]["crawler_attitude_deg"])
