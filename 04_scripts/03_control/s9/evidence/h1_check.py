"""H-1 traces: true pad-floor change per leg vs stroke-based twist and single-leg candidates (428.5 R1').

Moved 2026-10-30 from session scratchpad ctrl-p37/h1_check.py. The input folder (h1_RR.json, h1_FL.json)
was hard-coded to scratchpad ctrl-426/; it is now the first argument and defaults to
06_analysis/02_control/s9/rev85/evidence/. Usage: python -I h1_check.py [<input_dir>]
"""
import json, sys
from pathlib import Path
import numpy as np

DEFAULT_INPUT_DIR = Path(__file__).resolve().parents[4] / "06_analysis" / "02_control" / "s9" / "rev85" / "evidence"
src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT_DIR
LEGS = ("FL", "FR", "RL", "RR")
TW = np.array([1, -1, -1, 1])  # tau = (FL - FR) - (RL - RR)
for leg in ("RR", "FL"):
    d = json.loads((src / f"h1_{leg}.json").read_text("utf-8"))
    log = d["log"]; t_ev = d["t_ev"]
    t = np.array([r["t"] for r in log])
    x = np.array([r["x_mm"] for r in log]); h = np.array([r["h_mm"] for r in log]); z = np.array([r["sink_mm"] for r in log])
    est = np.array([r["est_mm"] for r in log]); rut = np.array([r["rut_mm"] for r in log])
    k0 = int(np.searchsorted(t, t_ev)) - 1  # last row before the event
    i = LEGS.index(leg)
    print("=====", leg, "t_ev", t_ev, "rows", len(t), "pre row t", t[k0])
    print(" h pre", h[k0], "h end", h[-1], "| z pre", z[k0], "z end", z[-1])
    for lab, k in (("pre", k0), ("ev+1", k0 + 10), ("ev+3", k0 + 30), ("end", len(t) - 1)):
        dx = x[k] - x[k0]; dh = h[k] - h[k0]; dz = z[k] - z[k0]
        print(f" {lab:5s} t={t[k]:6.1f} dx={np.round(dx,1)} dh={np.round(dh,1)} dz={np.round(dz,1)} "
              f"tau_dx={float(TW @ dx):6.1f} tau_floor(dh-dz)={float(TW @ (dh - dz)):6.1f} est={est[k]} rut={rut[k]} est-rut={est[k]-rut[k]:.1f} reapp={log[k]['reapp']} att={log[k]['att_deg']}")
    print(" drift est-rut pre", round(est[k0] - rut[k0], 1), "end", round(est[-1] - rut[-1], 1))
