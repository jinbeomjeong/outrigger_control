"""Spec revision 9: what a rod-side pressure sensor changes in the C2 load estimate.

Algebraic study only (no simulation). Hypotheses on the rod chamber pressure p_r:
  H0  user/hydraulics interim assumption: locked back pressure p_r0 (a few bar), lifted leg
      p_r = m_rod g / A_ann (head chamber near 0), rod chamber does not intensify.
  H1  upper bound: locked rod chamber is a stiff oil column (beta_r) in parallel with the head
      column, so an unload dF after locking shows up as kappa dF on the rod side.
  H2  hypothesis: after a retraction the rod chamber is trapped at the pilot-opening pressure
      p_h / rho (rho = pilot ratio, unknown, 3..4 typical).
Output: JSON next to this script.
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
A_P = math.pi / 4 * 0.115**2  # head area, m^2 (YAML bore 0.115 m)
A_ANN = 0.000883572934  # annulus area, m^2 (YAML)
S_MAX = 0.68
L0 = 0.05  # dead length, both chambers (ASSUMPTION for rod side)
BETA_H = 1.0e9
F_MIN = 9452.54751
M_ROD_G = 1047.0  # dynamics_model.md table, N
SIGMA_BAR = 0.3
GUARD = F_MIN + 5e3
RELEVEL = F_MIN + 7e3
LOADS = {"FL": 119.1e3, "FR": 117.3e3, "RL": 73.8e3, "RR": 71.9e3}  # RE1b truth before event
N_TWIST = [0.476, -0.476, -0.523, 0.523]

out = {}

# 1. noise
s_h = SIGMA_BAR * 1e5 * A_P
s_r = SIGMA_BAR * 1e5 * A_ANN
out["noise_N"] = {"head_only": s_h, "rod_only": s_r, "dual": math.hypot(s_h, s_r),
                  "dual_over_head": math.hypot(s_h, s_r) / s_h}

# 2. H0 bias b = p_r A_ann
out["H0_bias_N"] = {f"p_r_{p}bar": p * 1e5 * A_ANN for p in (2, 3, 5, 10)}
out["H0_bias_N"]["lifted_p_r_bar"] = M_ROD_G / A_ANN / 1e5
out["H0_bias_N"]["lifted"] = M_ROD_G
out["area_ratio"] = A_ANN / A_P

# 3. H2 trapped after retraction
h2 = {}
for rho in (3.0, 4.0):
    row = {}
    for name, f in [("guard_14.45kN", GUARD), ("relevel_16.45kN", RELEVEL), ("RL_73.8kN", 73.8e3),
                    ("FL_119.1kN", 119.1e3)]:
        p_h = f / A_P
        p_r = p_h / rho
        row[name] = {"p_r_bar": p_r / 1e5, "bias_N": p_r * A_ANN}
    h2[f"rho_{rho:g}"] = row
out["H2_bias"] = h2


# 4. H1 stiff rod chamber share kappa(e)
def kappa(e, beta_r):
    k_h = BETA_H * A_P / (L0 + e)
    k_r = beta_r * A_ANN / (S_MAX - e + L0)
    return k_r / (k_h + k_r)


h1 = {}
for beta_r in (1.0e9, 0.1e9):
    rows = {}
    for e in (0.2, 0.39, 0.40, 0.55, 0.65):
        k = kappa(e, beta_r)
        rows[f"e_{e:.2f}"] = {
            "kappa": k,
            # lifted leg, F_s 0: true F = -m g, head-only reads F + kappa*(F0 - F) + p_r0 A
            "lift_from_72kN_headonly_N": -M_ROD_G + k * (71.9e3 + M_ROD_G) + 3e5 * A_ANN,
            "lift_from_119kN_headonly_N": -M_ROD_G + k * (119.1e3 + M_ROD_G) + 3e5 * A_ANN,
            "lift_from_119kN_p_r_bar": (k * (119.1e3 + M_ROD_G)) / A_ANN / 1e5 + 3,
            # relevel trigger: true force when the head-only estimate says F_min + 7 kN,
            # unloading from 72 kN: F_hat = F + k (F0 - F) -> F = (F_hat - k F0) / (1 - k)
            "relevel_true_N_from_72kN": (RELEVEL - 3e5 * A_ANN - k * 71.9e3) / (1 - k),
            "guard_true_N_from_72kN": (GUARD - 3e5 * A_ANN - k * 71.9e3) / (1 - k),
        }
    h1[f"beta_r_{beta_r:.0e}"] = rows
out["H1"] = h1

# 5. block thresholds with bias b: true force when the biased estimate hits the threshold
blocks = {}
for label, b in [("H0_p_r0_5bar", 5e5 * A_ANN), ("H0_lift_11.85bar", M_ROD_G),
                 ("H2_rho3_at_guard", GUARD / A_P / 3 * A_ANN)]:
    blocks[label] = {
        "bias_N": b,
        "guard_true_N": GUARD - b,
        "relevel_true_min_N": RELEVEL - b - 1e3,  # 1 kN overshoot (spec 20.2)
        "relevel_margin_left_N": RELEVEL - b - 1e3 - GUARD,
        "Q2_threshold_true_N": GUARD - b,
    }
out["blocks"] = blocks

# 6. probe midpoint / band with H2 (retract-hold trapped at p_h/rho, extend-hold at p_r0)
probe = {}
for rho in (3.0, 4.0):
    for name, f in [("RL_73.8kN", 73.8e3), ("FL_119.1kN", 119.1e3), ("guard", GUARD)]:
        b_ret = f / A_P / rho * A_ANN
        b_ext = 3e5 * A_ANN
        probe[f"rho{rho:g}_{name}"] = {
            "band_under_N": 0.5 * (b_ret - b_ext),  # head-only F_s estimate too small by this
            "midpoint_over_N": 0.5 * (b_ret + b_ext),
        }
out["probe_H2"] = probe

# 7. twist coordinate error from per-leg bias (worst sign pattern)
for label, bias in [("H0_0_to_5bar", [5e5 * A_ANN] * 4),
                    ("H2_rho3", [LOADS[k] / A_P / 3 * A_ANN for k in ("FL", "FR", "RL", "RR")])]:
    worst = sum(abs(n) * b for n, b in zip(N_TWIST, bias))
    out[f"twist_worst_N_{label}"] = worst

# 8. seal friction miss: lifted leg, F_s 12 kN, stick, reading of both estimators
f_s = 12e3
f_hyd = f_s - M_ROD_G
p_h = (f_hyd + 3e5 * A_ANN) / A_P
out["friction_miss"] = {
    "net_force_dual_N": f_hyd,
    "head_only_N_H0": f_hyd + 3e5 * A_ANN,
    "p_h_bar": p_h / 1e5,
    "p_r_bar_unchanged": 3.0,
    "net_minus_Fmin_N": f_hyd - F_MIN,
    "friction_threshold_for_detection_N": F_MIN + M_ROD_G,  # F_s below this -> net < F_min
}

# 9. 350 bar: head pressure vs net force / A_p, and rod-side pull for 350 bar
out["p350"] = {
    "net_over_Ap_underreads_bar_at_11.85bar_rod": 11.85 * A_ANN / A_P,
    "rod_350bar_force_N": 350e5 * A_ANN,
    "head_350bar_force_N": 350e5 * A_P,
}

path = (OUT_DIR / _Path(__file__).name).with_suffix(".json")
path.write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
