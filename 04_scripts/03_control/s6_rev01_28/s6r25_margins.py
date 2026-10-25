"""Loop margins vs sensor-path delay (spec rev. 25). Continuous loops with a pure delay, dense frequency sweep:
twist  L = K_tw e^{-tau s} / s             (K_tw 1.2 s^-1: 1.0 x L1-R +20 % exchange stiffness)
guard  L = K_g  e^{-tau s} / s             (K_g 1.0 s^-1)
heave  L = K_z  e^{-tau s} / (s (0.2 s + 1))  (K_z 0.5 s^-1, clearance filter 0.2 s; stroke channel)
Negative feedback u = -L e. GM absolute and dB at the phase crossover, PM at the gain crossover, delay margin
PM / w_gc, M_s = max |1/(1+L)|. Output JSON for the Julia cross-check."""
import json
import math
from pathlib import Path

import numpy as np

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
TAUS = {"base_50Hz": 0.030, "p10i_mean": 0.080, "p10i_worst": 0.130, "p10a_mean": 0.130, "p10a_worst": 0.180,
        "c10_mean": 0.150, "c10_worst": 0.200}
LOOPS = {"twist": (1.2, 0.0), "guard": (1.0, 0.0), "heave": (0.5, 0.2)}
w = np.logspace(-3, 3, 600001)
out = {}
for ln, (K, tf) in LOOPS.items():
    for tn, tau in TAUS.items():
        s = 1j * w
        L = K * np.exp(-tau * s) / (s * (tf * s + 1))
        mag = np.abs(L); ph = np.unwrap(np.angle(L))
        i_gc = np.where(np.diff(np.sign(mag - 1)))[0]
        i_pc = np.where(np.diff(np.sign(ph + math.pi)))[0]
        wgc = float(np.interp(1.0, mag[i_gc[0]:i_gc[0] + 2][::-1], w[i_gc[0]:i_gc[0] + 2][::-1]))
        pm = 180 + math.degrees(float(np.interp(wgc, w, ph)))
        wpc = float(np.interp(-math.pi, ph[i_pc[0]:i_pc[0] + 2][::-1], w[i_pc[0]:i_pc[0] + 2][::-1]))
        gm = 1 / float(np.interp(wpc, w, mag))
        ms = float(np.max(np.abs(1 / (1 + L))))
        out[f"{ln}|{tn}"] = {"K": K, "tf": tf, "tau": tau, "wgc": wgc, "PM_deg": pm, "wpc": wpc, "GM": gm,
                             "GM_dB": 20 * math.log10(gm), "DM_s": math.radians(pm) / wgc, "Ms": ms}
OUT_DIR.joinpath("s6r25_margins_py.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items():
    print(k, {a: round(b, 4) for a, b in v.items()})
