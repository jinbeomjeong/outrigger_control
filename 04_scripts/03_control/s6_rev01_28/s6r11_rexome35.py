"""Revision 9 / section 53 numbers recomputed for the REXOME35 cylinders (per leg).

Inputs: hydraulics rod_side_pressure.md 12.2 (r, trapped pressures), dynamics 5.11.2 / 5.11.10
(areas, saturation, k_s, m_rod), CLAUDE.md (F_min). Algebraic, linear in the locked unload
(the hydraulics nonlinear values are quoted next to it for comparison).
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
F_MIN = 9452.54751
SIG_BAR = 0.3e5
N_TWIST = [0.476, -0.476, -0.523, 0.523]
LEG = {
    "front": dict(Ap=math.pi / 4 * 0.130**2, Aann=math.pi / 4 * (0.130**2 - 0.110**2),
                  r=0.269, mg=1047.0, F0=118.25e3, p_ext=2e5, p_ret=34.9e5,
                  p_ret_moving_surge=68e5, ks=2.166e8),
    "rear": dict(Ap=math.pi / 4 * 0.110**2, Aann=math.pi / 4 * (0.110**2 - 0.090**2),
                 r=0.289, mg=701.4, F0=72.8e3, p_ext=2e5, p_ret=31.4e5,
                 p_ret_moving_surge=68e5, ks=2.051e8),
}
out = {}
for name, g in LEG.items():
    Ap, Aa, r, mg, F0 = g["Ap"], g["Aann"], g["r"], g["mg"], g["F0"]
    sig_head = SIG_BAR * Ap
    sig_dual = math.hypot(SIG_BAR * Ap, SIG_BAR * Aa)
    b_ext, b_ret = g["p_ext"] * Aa, g["p_ret"] * Aa
    d = {
        "Ap_m2": Ap, "Aann_m2": Aa, "phi": Ap / Aa,
        "sigma_head_only_N": sig_head, "sigma_dual_N": sig_dual,
        "sigma_dual_mean_0p5s_N": sig_dual / 5.0,
        "bias_extend_lock_N": b_ext, "bias_retract_lock_N": b_ret,
        "sat_extend_N": 210e5 * Ap, "sat_retract_N": 210e5 * Aa,
        "head_350bar_N": 350e5 * Ap, "rod_350bar_pull_N": 350e5 * Aa,
        "item4_180bar_N": 180e5 * Ap, "Fmin_bar": F_MIN / Ap / 1e5,
        # head-only true trigger after an extend-lock at F0 (locked unload, linear share r)
        "P5_true_trigger_head_only_N": (F_MIN + 7e3 - b_ext - r * F0) / (1 - r),
        "guard_true_trigger_head_only_N": (F_MIN + 5e3 - b_ext - r * F0) / (1 - r),
        # after a probe ending in retraction (static): P5 minimum (1 kN overshoot)
        "P5_min_after_retract_probe_head_only_N": F_MIN + 7e3 - 1e3 - b_ret,
        # lift readings (linear share), head only, F_s 0 and F_s 12 kN friction-held
        "lift_head_only_extend_lock_N": -mg + b_ext + r * (F0 + mg),
        "lift_head_only_retract_lock_N": -mg + b_ret + r * (F0 + mg),
        "lift_Fs12_head_only_N": (12e3 - mg) + b_ext + r * max(0.0, F0 + mg - 12e3),
        "dual_static_lift_visible_Fs_max_N": F_MIN + mg - 3 * sig_dual,
        "dual_P5_catches_friction_lift_Fs_max_N": F_MIN + 7e3 + mg,
        # predicted lift-off rod pressure from a lock state (bar), F0 at lock
        "rod_liftoff_bar_extend_lock": (g["p_ext"] + r * (F0 + mg) / Aa) / 1e5,
        "rod_liftoff_bar_retract_lock": (g["p_ret"] + r * (F0 + mg) / Aa) / 1e5,
        "F0_rod350_extend_lock_N": (350e5 - g["p_ext"]) * Aa / r - mg,
        "F0_rod350_retract_lock_N": (350e5 - g["p_ret"]) * Aa / r - mg,
        "F0_rod350_retract_moving_lock_N": (350e5 - g["p_ret_moving_surge"]) * Aa / r - mg,
        "F0_rod350_meter_out_N": (350e5 - 210e5) * Aa / r - mg,
        "dp_r_per_100kN_bar": r * 1e5 / Aa / 1e5,
        "D8_ratio": None,
        "rod_bias_per_bar_N": 1e5 * Aa,
        "ks_N_m": g["ks"], "deflection_mm_per_10kN": 10e3 / g["ks"] * 1e3,
    }
    out[name] = d
# twist coordinate worst head-only bias: two legs extend-locked, two retract-locked
b = {"front": (out["front"]["bias_extend_lock_N"], out["front"]["bias_retract_lock_N"]),
     "rear": (out["rear"]["bias_extend_lock_N"], out["rear"]["bias_retract_lock_N"])}
worst = 0.0
for mask in range(16):
    bias = []
    for i in range(4):
        lo, hi = b["front"] if i < 2 else b["rear"]
        bias.append(hi if mask >> i & 1 else lo)
    worst = max(worst, abs(sum(n * x for n, x in zip(N_TWIST, bias))))
out["twist_worst_head_only_N"] = worst
out["trend_tolerance_3sigma_N"] = {k: 3 * v["sigma_dual_N"] for k, v in out.items()
                                   if isinstance(v, dict)}
(OUT_DIR / _Path(__file__).name).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
