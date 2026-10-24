"""Replay the C2 attitude low-pass on recorded 10 ms IMU samples and compare with the CHECK value."""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])
cases = sys.argv[2:]
G = 1.0


def tilt(f):
    f = np.atleast_2d(f)
    roll = np.arctan2(f[:, 1], f[:, 2])
    pitch = np.arctan2(-f[:, 0], np.hypot(f[:, 1], f[:, 2]))
    return np.degrees(roll), np.degrees(pitch)


for c in cases:
    rec = np.load(batch / c / "record" / "record.npz")
    r8 = np.load(batch / c / "r8_series.npz")
    res = json.loads((batch / c / "result.json").read_text(encoding="utf-8"))
    t = r8["t"]
    s = r8["imu_samples"]  # (n, 10, 3)
    ph = r8["phase"]
    mean_s = s.mean(axis=1)
    diff = np.abs(mean_s - rec["meas.specific_force"]).max()
    # per-sample tilt stats
    rr, pp = tilt(s.reshape(-1, 3))
    rr = rr.reshape(s.shape[:2]); pp = pp.reshape(s.shape[:2])
    # replay filter
    gain = 0.01 / 0.8
    st = None
    froll = np.zeros(len(t)); fpitch = np.zeros(len(t))
    for k in range(len(t)):
        for j in range(10):
            x = np.array([rr[k, j], pp[k, j]])
            if st is None:
                st = [x.copy(), x.copy()]
                y = x
            else:
                inp = x
                for stg in st:
                    stg += gain * (inp - stg)
                    inp = stg
                y = inp
        froll[k], fpitch[k] = y
    chk = np.where(ph == "check")[0]
    last = list(chk[-9:]) + [chk[-1] + 1]
    print(f"== {c}: max|mean(samples)-meas.sf| = {diff:.3e} m/s2; check samples {len(chk)}")
    print(f"   replay CHECK mean (last 10 periods incl. final?) r/p = {froll[last].mean():+.4f}/{fpitch[last].mean():+.4f}")
    print(f"   +1 period r/p = {froll[chk[-9:].tolist()+[chk[-1]+1]].mean():+.4f}/{fpitch[chk[-9:].tolist()+[chk[-1]+1]].mean():+.4f}")
    print("   acceptance", res["acceptance"]["crawler_attitude_deg"])
    # raw sample spread in the final second
    w = slice(chk[-10], chk[-1] + 1)
    print(f"   raw 10ms tilt last 1 s: roll mean {rr[w].mean():+.4f} std {rr[w].std():.4f} pk {np.ptp(rr[w]):.4f}; pitch mean {pp[w].mean():+.4f} std {pp[w].std():.4f} pk {np.ptp(pp[w]):.4f}")
    # time stamps of the r8 series vs record
    print("   t check", t[chk[0]], t[chk[-1]], "rec t", rec["t"][chk[0]], rec["t"][chk[-1]])
    # print per-period first and last sample tilt for the last 1 s
    for k in range(chk[-10], chk[-1] + 1):
        print(f"     t={t[k]:.2f} pitch samples {np.round(pp[k],3)} filt {fpitch[k]:+.4f}")
