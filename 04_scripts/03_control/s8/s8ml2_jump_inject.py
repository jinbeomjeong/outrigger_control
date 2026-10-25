"""Rev. 48: detection power of the D1 head-step explanation rules against an injected head jump.

For every 10 Hz period of the ML pilot episodes after the event (crawler off), and every leg,
adds a persistent head-reading jump J (bar) from that period on, and asks whether the period's
step (physical change + J) is (a) a D1 candidate (|dp| > 100 bar) and (b) flagged as a fault by
  - the D1' sum rule:   |d sum| >= 0.5 |dp| A_p      (rev. 47, implemented)
  - the D1'' IMU rule:  |d r|   >= 0.5 |dp| A_p, r = sum F_read - M_eff f_z(last 10 ms sub-mean)
Periods are split into quiet (all |dp_h| <= 30 bar) and transient. Reports detection rates.
Also the false-fault rate of each rule on the real (uninjected) steps > 100 bar.
Usage: python -I s8ml2_jump_inject.py <batch_dir> [J_bar ...]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
batch = Path(sys.argv[1])
jumps = [float(x) for x in sys.argv[2:]] or [100.0, -100.0, 150.0, -150.0]
stats = {}
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "result.json").exists():
        continue
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res["event_t_s"])
    rec = np.load(d / "record" / "record.npz", allow_pickle=True)
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    t = rec["t"]
    hm = rec["meas.head_pressure"] / 1e5
    rm = rec["meas.rod_pressure"] / 1e5
    phase = np.array([str(p) for p in r8["phase"]])
    s = ((hm * A_P - rm * A_ANN) * 1e2).sum(axis=1)
    f = r8["imu_samples"][:, -1, 2]
    rd = (phase == "ready") & (t < t_ev - 0.05)
    if rd.sum() < 3:
        continue
    m_eff = np.median(s[rd] / f[rd])
    r = s - m_eff * f
    dh = np.diff(hm, axis=0)
    ds = np.diff(s)
    dr = np.diff(r)
    ok = (t[1:] >= t_ev) & (phase[1:] != "fault")
    trans = np.abs(dh).max(axis=1) > 30.0
    for J in jumps:
        for L in range(4):
            jf = J * A_P[L] * 1e2  # kN
            dp = dh[:, L] + J
            cand = ok & (np.abs(dp) > 100.0)
            own = np.abs(dp) * A_P[L] * 1e2
            sum_fault = np.abs(ds + jf) >= 0.5 * own
            imu_fault = np.abs(dr + jf) >= 0.5 * own
            for key, sel in (("quiet", cand & ~trans), ("transient", cand & trans)):
                st = stats.setdefault((J, key), [0, 0, 0])
                st[0] += int(sel.sum())
                st[1] += int((sel & sum_fault).sum())
                st[2] += int((sel & imu_fault).sum())
for (J, key), (n, a, b) in sorted(stats.items()):
    if n:
        print(f"J {J:+6.0f} bar {key:9s}: candidates {n:6d}  detected sum-rule {a/n:6.1%}  IMU-rule {b/n:6.1%}")
