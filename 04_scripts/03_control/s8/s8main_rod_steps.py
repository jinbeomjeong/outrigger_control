"""Rev. 51: all 10 Hz rod-pressure falls > 100 bar in the main ML batch, classified by the D1'
rod rules (rev. 48 218.3/218.4) and by plant truth.

Usage: python -I s8main_rod_steps.py <batch_dir> <out_json>
For each fall (meas.rod_pressure, engine time t_k): leg, d p_r, d p_h, issued command this and
previous period (r8 issued_u at t_{k-1}, t_{k-2}: the command in force over the past period was
issued one period earlier, d = 1), u_applied max |.| over the past period (1 ms truth), airborne
fraction of the past period, new rod reading, and the D1' reason it would get:
  check_opened  : issued(t_{k-1}) > 0 or issued(t_{k-2}) > 0, new reading in [-1, 12] bar
  regain        : head rose (ratio test not repeated here)
  none          : unexplained (a D1 fallback)
Also counts how many of the 'none' falls had the leg plant-locked (|u_applied| < 1e-6 m/s over
the whole period) and airborne.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
batch = Path(sys.argv[1])
out = Path(sys.argv[2])
falls = []
for case in sorted((batch / "episodes").iterdir()):
    if not case.is_dir() or case.name.startswith("_"):
        continue
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    rp = rec["meas.rod_pressure"] / 1e5
    hp = rec["meas.head_pressure"] / 1e5
    t = rec["t"]
    dr = np.diff(rp, axis=0)
    ks, ls = np.nonzero(dr < -100.0)
    if len(ks) == 0:
        continue
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    iu = r8["issued_u"]
    pads = np.load(case / "pads.npz", allow_pickle=True)
    tp = pads["t"]
    ev = [str(e) for e in json.loads((case / "controller_events.json").read_text(encoding="utf-8"))]
    for k0, L in zip(ks, ls):
        k = k0 + 1
        cmd_now = iu[k - 1][L] if k >= 1 else 0.0
        cmd_before = iu[k - 2][L] if k >= 2 else 0.0
        m = (tp > t[k - 1]) & (tp <= t[k])
        uap = float(np.ptp(pads["s_motor"][m, L])) if m.any() else np.nan
        uabs = float(np.abs(rec["u_applied"][k - 1][L]))
        air = float(pads["airborne"][m, L].mean()) if m.any() else np.nan
        new = rp[k, L]
        dh = hp[k, L] - hp[k - 1, L]
        if (cmd_now > 0 or cmd_before > 0) and -1.0 <= new <= 12.0:
            reason = "check_opened"
        elif dh > 0:
            reason = "regain?"
        else:
            reason = "none"
        fb = any(f"WARN_ROD_PRESSURE_FALLBACK:{LEGS[L]}" in e and abs(float(e.split('t_s=')[1].split(',')[0]) - t[k]) < 0.05 for e in ev)
        falls.append({"case": case.name, "t_s": float(t[k]), "leg": LEGS[L], "dpr_bar": float(dr[k0, L]),
                      "dph_bar": float(dh), "new_rod_bar": float(new), "cmd_now": float(cmd_now),
                      "cmd_before": float(cmd_before), "u_applied_start": uabs, "s_motor_ptp_m": uap,
                      "air_frac": air, "reason": reason, "fallback": fb})
json.dump({"falls": falls}, open(out, "w", encoding="utf-8"), indent=1)
print(f"rod falls > 100 bar: {len(falls)}")
from collections import Counter
print("by reason:", dict(Counter(f["reason"] for f in falls)))
print("fallback warnings at those samples:", sum(f["fallback"] for f in falls))
for f in falls:
    if f["reason"] != "check_opened":
        print(f"  {f['case']} {f['t_s']:.2f} {f['leg']}: dpr {f['dpr_bar']:+.1f} dph {f['dph_bar']:+.1f} new {f['new_rod_bar']:.1f} | cmd now {f['cmd_now']:+.2e} before {f['cmd_before']:+.2e} |"
              f" s_motor ptp {1e3*f['s_motor_ptp_m']:.3f} mm air {f['air_frac']:.2f} | {f['reason']} fallback {f['fallback']}")
# head-fall / airborne signature among explained falls
sig = [f for f in falls if f["dph_bar"] < 0 and f["air_frac"] > 0.5]
print(f"falls with head falling and leg airborne (> 50 % of the period): {len(sig)}; reasons {dict(Counter(f['reason'] for f in sig))}")
