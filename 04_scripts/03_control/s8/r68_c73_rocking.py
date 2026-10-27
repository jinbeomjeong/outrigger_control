"""C-S8-72 / C-S8-73 PS-7: pad-load oscillation of the pre-grounded leg in TOUCH (spec rev. 68 351.1).

Per case: dominant frequency of the 1 ms pad normal force (1 s moving mean removed, Hann FFT,
> 0.5 Hz), half peak-to-peak per 2 s bin, work of that leg's motor on the oscillating load
(integral of x * ds_motor/dt, positive = pumping), motor travel in TOUCH. kN, Hz, J, mm.

Usage: python -I r68_c73_rocking.py <batch dir> [<batch dir> ...]
"""
import sys
from pathlib import Path

import numpy as np

CASES = ("PS7a_RR_R8", "PS7b_RR_R8", "PS7c_RR_R8", "PS7a_FL_R8")

for root in sys.argv[1:]:
    for case in CASES:
        d = Path(root) / case
        if not d.exists():
            continue
        z = np.load(d / "pads.npz")
        r8 = np.load(d / "r8_series.npz")
        ph = np.array([str(p) for p in r8["phase"]])
        kt = np.flatnonzero(ph == "touch")
        ta, tb = r8["t"][kt[0]], r8["t"][kt[-1]]
        t = z["t"]
        j = 3 if "RR" in case else 0
        m = (t >= ta) & (t <= tb)
        N = z["N"][m, j] / 1e3
        tt = t[m] - ta
        dt = float(np.median(np.diff(tt)))
        x = N - np.convolve(N, np.ones(1001) / 1001, mode="same")
        f = np.fft.rfftfreq(x.size, dt)
        X = np.abs(np.fft.rfft(x * np.hanning(x.size)))
        sel = f > 0.5
        f0 = f[sel][np.argmax(X[sel])]
        amps = []
        for a in np.arange(0, tt[-1], 2.0):
            w = (tt >= a) & (tt < a + 2.0)
            if w.sum() > 100:
                amps.append(round(float((N[w].max() - N[w].min()) / 2), 1))
        sm = z["s_motor"][m, j]
        work = float((x * 1e3 * np.gradient(sm, dt)).sum() * dt)
        print(f"{Path(root).name} {case}: TOUCH {tb - ta:.1f} s, f0 {f0:.2f} Hz, half p-p per 2 s {amps}, "
              f"work {work:.1f} J, motor travel {1e3 * (sm[-1] - sm[0]):.1f} mm, N min/max {N.min():.1f}/{N.max():.1f}")
