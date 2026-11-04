"""Choose eps from the stored flow-off run: first contact per leg at 1 ms, approach speed, travel in TOUCH, window margin."""
import json
import sys
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(MAIN / "03_src"))
from outrigger_sim.control.c2 import C2Config, C2Controller  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

D = MAIN / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
LEGS = ("FL", "FR", "RL", "RR")
s9 = np.load(D / "step_series.npz", allow_pickle=False)
rec = np.load(D / "record/record.npz", allow_pickle=False)
t, Fn, sm = s9["t_s"], s9["scm_pad_normal_N"], s9["s_motor_m"] * 1e3
print("t range", t[0], t[-1], "Fn shape", Fn.shape, "abs time of first record", rec["t"][0])
EPS = (1.0e-3, 2.0e-3)
GATE = 12.85
s_gate = np.array([sm[int(np.searchsorted(t, GATE)), i] for i in range(4)])
print("stroke at gate mm", np.round(s_gate, 3))
rows = {}
for i, leg in enumerate(LEGS):
    k0, k3, k14 = (int(np.argmax(Fn[:, i] > v)) for v in (1.0, 3000.0, 14122.0))
    rows[leg] = {"t_F1N": float(t[k0]), "t_F3kN": float(t[k3]), "t_F14kN": float(t[k14]), "s_F3kN_mm": float(sm[k3, i]),
                 "travel_from_gate_mm": float(sm[k3, i] - s_gate[i])}
    print(leg, {k: round(v, 3) for k, v in rows[leg].items()}, "phase of t_F3kN in 0.1 s", round(float(t[k3] % 0.1), 3))
first = min(r["t_F3kN"] for r in rows.values())
k_first = int(np.searchsorted(t, first))
travel = sm[k_first] - s_gate
print("first contact (3 kN) t", first, "strokes", np.round(sm[k_first], 3), "travel", np.round(travel, 3))
V = 10.462
for e in EPS:
    d = e * travel
    print("eps", e, "deficit mm", np.round(d, 3), "delay s", np.round(d / V, 4), "period fraction", np.round(d / V / 0.1, 3))
print("eps for one period, rear travel", 0.1 * V / travel[2:].mean())
# window start margin (touch window, spec R-2)
params = load_params(level="top")
c2 = C2Controller.from_params(params, C2Config().with_10hz_d1())
w = c2._touch_extension_m - c2.config.r8.touch_window_m  # noqa: SLF001
print("touch window start mm", w * 1e3, "touch extension", c2._touch_extension_m * 1e3)  # noqa: SLF001
tr = rec["t"]
sr = rec["meas.stroke"] * 1e3
sm10 = rec["s_motor"] * 1e3
u = rec["u_cmd"] * 1e3
for i, leg in enumerate(LEGS):
    k = int(np.argmax((tr > 13.5) & (u[:, i] < 15.0)))
    print(leg, "speed drop seen at t", round(float(tr[k]), 1), "s_motor before / at", np.round(sm10[k - 2:k + 1, i], 3), "margin above window mm",
          np.round(sm10[k - 2:k + 1, i] - w[i] * 1e3, 3))
print("phases", [(round(p["t_s"], 1), p["phase"]) for p in json.loads((D / "result.json").read_text(encoding="utf-8"))["phases"]])
