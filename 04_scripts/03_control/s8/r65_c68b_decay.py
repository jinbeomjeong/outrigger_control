"""Rev. 65 supplement: lock-state oscillation after FAULT in the C-S8-68 re-run (c68b) and a reference run.

For each case folder: 1 ms true cylinder force (pads F_cyl) per leg from FAULT (first 'fault' phase of r8_series)
to the run end, split in 1 s windows: mean, min, peak-to-peak; dominant frequency of each leg's force (FFT of the
detrended signal over [FAULT + 1 s, end]); log-decrement estimate of the peak-to-peak envelope (fit of
ln(ptp) over the windows, zeta = -slope / (2 pi f)). Also the minimum of the 0.5 s moving mean.
A reference folder without FAULT uses its last READY entry instead (the same lock state, controller quiet).

Usage: python -I r65_c68b_decay.py <case_dir> [...]
Units: kN, s, Hz. Read only.
"""
import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
F_MIN_KN = 9.4146


def anchor_time(case: Path) -> tuple[float, str]:
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    ph = np.array([str(p).split(".")[-1].lower() for p in r8["phase"]])
    t = np.asarray(r8["t"], float)
    idx = np.flatnonzero(ph == "fault")
    if idx.size:
        return float(t[idx[0]]), "fault"
    prev = np.concatenate([np.array([""]), ph[:-1]])
    ready = np.flatnonzero((ph == "ready") & (prev != "ready"))
    return float(t[ready[-1]]), "last_ready"


for arg in sys.argv[1:]:
    case = Path(arg)
    t0, kind = anchor_time(case)
    pads = np.load(case / "pads.npz", allow_pickle=True)
    t = np.asarray(pads["t"], float)
    F = np.asarray(pads["F_cyl"], float) / 1e3
    w = t >= t0 + 1.0
    tw, Fw = t[w], F[w]
    out = {"case": case.name, "anchor": kind, "t0": round(t0, 2), "window_s": round(float(tw[-1] - tw[0]), 2)}
    dt = float(np.median(np.diff(tw)))
    n = int(round(0.5 / dt))
    cs = np.cumsum(np.vstack([np.zeros((1, 4)), Fw]), axis=0)
    mov = (cs[n:] - cs[:-n]) / n
    out["min_kN"] = dict(zip(LEGS, np.round(Fw.min(axis=0), 2).tolist()))
    out["min_mean05_kN"] = dict(zip(LEGS, np.round(mov.min(axis=0), 2).tolist()))
    per = {}
    for i, leg in enumerate(LEGS):
        x = Fw[:, i] - Fw[:, i].mean()
        spec = np.abs(np.fft.rfft(x * np.hanning(x.size)))
        freq = np.fft.rfftfreq(x.size, dt)
        k = 1 + int(np.argmax(spec[1:]))
        f = float(freq[k])
        edges = np.arange(tw[0], tw[-1] + 1e-9, 1.0)
        rows = []
        for a in edges[:-1]:
            m = (tw >= a) & (tw < a + 1.0)
            rows.append((round(a - t0, 1), round(float(Fw[m, i].mean()), 1), round(float(Fw[m, i].min()), 1),
                         round(float(np.ptp(Fw[m, i])), 1)))
        ptp = np.array([r[3] for r in rows])
        tt = np.array([r[0] for r in rows])
        ok = ptp > 0.5
        zeta = None
        if ok.sum() >= 3:
            slope = np.polyfit(tt[ok], np.log(ptp[ok]), 1)[0]
            zeta = round(float(-slope / (2 * np.pi * f)), 4)
        per[leg] = {"f_Hz": round(f, 2), "zeta_env": zeta, "windows": rows[:4] + rows[-3:]}
    out["legs"] = per
    print(json.dumps(out, ensure_ascii=True))
