"""D-S8-5 (1): what moves the airborne link force during the CHECK holds.

Per case and leg (1 ms truth, hold windows 4.1-5.2 s and 6.3-7.7 s record time):
std of F_cyl, dominant frequency (FFT of the detrended signal), std of the body acceleration
along world z (a_world) times m_rod, share of 1 ms rows where the seal slips, and the hold-mean
friction. Usage: python -I ds85_hold_vibration.py <batch dir> <case> [<case> ...]
"""
import os
import sys

import numpy as np

B = sys.argv[1]
M_ROD = np.array([1047.2, 1047.2, 718.0, 718.0]) / 9.81
HOLDS = ((4.15, 5.2), (6.35, 7.7))
print(f"{'case':28s} leg hold  std(F_cyl)[N] f_dom[Hz] std(m a_z)[N] slip% mean f[N]")
for c in sys.argv[2:]:
    p = np.load(os.path.join(B, c, "pads.npz"))
    t = p["t"]
    az = p["a_world"][:, 2]
    for leg in range(4):
        for h, (a, b) in enumerate(HOLDS):
            m = (t >= a) & (t < b)
            x = p["F_cyl"][m, leg]
            x = x - np.polyval(np.polyfit(t[m], x, 1), t[m])
            dt = np.median(np.diff(t[m]))
            spec = np.abs(np.fft.rfft(x * np.hanning(x.size)))
            fr = np.fft.rfftfreq(x.size, dt)
            fdom = fr[1:][np.argmax(spec[1:])]
            slip = 100.0 * (~p["seal_stuck"][m, leg]).mean()
            print(f"{c:28s} {leg}   {'ER'[h]}    {x.std():9.1f}   {fdom:7.1f}   {np.std(M_ROD[leg] * az[m]):9.1f}"
                  f"   {slip:5.1f}  {p['f_seal'][m, leg].mean():8.1f}")
