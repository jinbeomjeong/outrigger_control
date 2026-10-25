"""Spec revision 9 supplement: block effects with the hydraulics-expert rod-side model.

Model (00_docs/02_hydraulic/rod_side_pressure.md): locked after extension p_r0 = 2 bar,
locked unload share r = 0.1047 (front) / 0.0999 (rear) with L0r 0.05 m (0.042 with 0.6 m),
after retraction trapped 31-37 bar, sigma 0.3 bar each sensor.
"""

import json
import math
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
A_P = math.pi / 4 * 0.115**2
A_ANN = 0.000883572934
F_MIN = 9452.54751
MG = 1047.0
GUARD = F_MIN + 5e3
RELEVEL = F_MIN + 7e3
SIG_F = math.hypot(0.3e5 * A_P, 0.3e5 * A_ANN)
P_R0 = 2e5
LEGS = {"front": (118.25e3, 0.1047), "rear": (71.9e3, 0.0999)}
out = {"sigma_dual_N": SIG_F}


def true_at(threshold, f0, r, p_r0=P_R0):
    """True net force when the head-only estimate hits threshold during a locked unload."""
    return (threshold - p_r0 * A_ANN - r * f0) / (1.0 - r)


for name, (f0, r) in LEGS.items():
    for r_case, rr in (("L0r_0.05", r), ("L0r_0.6", 0.042)):
        key = f"{name}_{r_case}"
        out[key] = {
            "r": rr,
            "guard_true_N": true_at(GUARD, f0, rr),
            "relevel_true_N": true_at(RELEVEL, f0, rr),
            # lift with F_s 0: head-only reading
            "lift_headonly_N": -MG + P_R0 * A_ANN + rr * (f0 + MG),
            # lift held by friction F_s 12 kN: friction takes the first F_s of the unload
            "lift_fs12_headonly_N": (12e3 - MG) + P_R0 * A_ANN + rr * max(0.0, f0 + MG - 12e3),
        }

# after-retraction lock (probe end, G9 stop): 31-37 bar
out["after_retract_bias_N"] = [31e5 * A_ANN, 37e5 * A_ANN]
out["after_extend_bias_N"] = P_R0 * A_ANN
# P5 / guard with after-retract bias (leg near guard)
out["guard_true_after_retract_N"] = [GUARD - b for b in out["after_retract_bias_N"]]
out["relevel_min_after_retract_N"] = [RELEVEL - 1e3 - b for b in out["after_retract_bias_N"]]
# pressure-only lift visibility, dual: F_s < F_min + mg - 3 sigma
out["dual_lift_visible_Fs_max_N"] = F_MIN + MG - 3 * SIG_F
# twist coordinate: worst |n^T b| with mixed last-move directions (after-retract on two legs)
n = [0.476, -0.476, -0.523, 0.523]
b_hi, b_lo = 37e5 * A_ANN, P_R0 * A_ANN
out["twist_worst_N"] = sum(abs(x) for x in n[:2]) * (b_hi - b_lo) / 2 + sum(
    abs(x) for x in n[2:]) * (b_hi - b_lo) / 2
# rod 350 bar: lift-off rod pressure for a locked leg of load F0 (front r)
out["rod_liftoff_bar"] = {f"{int(f/1e3)}kN": (P_R0 + 0.1047 * (f + MG) / A_ANN) / 1e5
                          for f in (118.25e3, 200e3, 292e3)}
out["rod_thermal_K_to_350_from_144bar"] = (350 - 144) / 5.9
# retraction one-sided band: airborne net reading -mg - F_s; pad force upper bound
for fs in (0.0, 5e3, 12e3):
    band = fs + 1e3
    f2s = -MG - fs
    out[f"airborne_retract_Fs{int(fs/1e3)}"] = {
        "F2s_N": f2s, "pad_upper_N": f2s + MG + band, "below_test": f2s + band < F_MIN}

path = (OUT_DIR / _Path(__file__).name).with_suffix(".json")
path.write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
