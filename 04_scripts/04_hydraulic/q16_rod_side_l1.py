"""Q16: should the rod-side chamber enter the L1 leg stiffness? Short algebraic estimates.

Inputs: dynamics_model.md 5.11.2 (REXOME35, same mounting geometry, e_op 0.4011 / 0.3909 m,
stroke 0.70 m): k_oil, k_ann, outer series stiffness k_out (rod + frame + contact).
Rod-side floor: 0.1 bar abs (ASSUMPTION). p_r0 states: 2 bar (locked after extension),
pilot threshold after a grounded retraction (rod_side_rexome35.py: 34.9 / 31.4 bar).
Run: conda run -n hydraulics-dev python -I q16_rod_side_l1.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

BAR = 1.0e5
P_ATM = 1.01325e5
FLOOR_G = 0.1e5 - P_ATM  # gauge floor
LEGS = {
    "front": {"k_oil": 2.942e7, "k_ann": 1.081e7, "k_out": 2.166e8, "A_ann": 3.770e-3,
              "F_static": 118.25e3, "p_r_after_retract": 34.9 * BAR},
    "rear": {"k_oil": 2.155e7, "k_ann": 8.75e6, "k_out": 2.051e8, "A_ann": 3.142e-3,
             "F_static": 72.8e3, "p_r_after_retract": 31.4 * BAR},
}
MG = 106.784 * 9.80665
ZETA_NUM_SHARE_NOW = 0.082  # dynamics 5.11.0: max numerical-damping share at L1 dt 2e-4 s (REXOME35)


def series(*k: float) -> float:
    return 1.0 / sum(1.0 / x for x in k)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "06_analysis" / "03_hydraulic")
    args = ap.parse_args()
    res = {}
    for leg, c in LEGS.items():
        kh, kr, ko = c["k_oil"], c["k_ann"], c["k_out"]
        r = kr / (kh + kr)
        kn_head = series(kh, ko)
        kn_both = series(kh + kr, ko)
        q = kn_both / kn_head
        w = math.sqrt(q)
        # bilinear oscillator (stiff on the unloading half cycle): equal-time harmonic mean of omegas
        w_bilin = 2 * w / (1 + w)
        # twist-type load exchange: unloading legs stiff, loading legs soft -> per-leg effective
        k_twist = 2 / (1 / kn_head + 1 / kn_both)
        sym = {}
        for name, pr0 in (("after_extension_2bar", 2 * BAR), ("after_retract_threshold", c["p_r_after_retract"])):
            # load increase that drives the rod side from p_r0 to the floor (linear, beta const):
            # dp_r = -r dF / A_ann  -> dF = (p_r0 - floor) A_ann / r
            dF = (pr0 - FLOOR_G) * c["A_ann"] / r
            sym[name] = {"p_r0_bar": pr0 / BAR, "symmetric_band_load_increase_kN": dF / 1e3,
                         "unloading_side_band_kN": "to lift-off (always stiff)"}
        res[leg] = {
            "k_ann_over_k_oil": kr / kh, "r": r,
            "kn_head_only_N_m": kn_head, "kn_with_rod_N_m": kn_both, "kn_ratio": q,
            "leg_mode_freq_ratio_linear": w, "leg_mode_freq_ratio_bilinear": w_bilin,
            "twist_exchange_stiffness_ratio": k_twist / kn_head,
            "liftoff_travel_ratio": kn_head / kn_both,
            "liftoff_travel_static_mm": {"head_only": (c["F_static"] + MG) / kn_head * 1e3,
                                         "with_rod": (c["F_static"] + MG) / kn_both * 1e3},
            "numerical_damping_share_if_linear_stiff": ZETA_NUM_SHARE_NOW * w,
            "symmetric_zone": sym,
            "stroke_sensor_piston_shift_mm_per_10kN": {"head_only": 1e4 / kh * 1e3, "with_rod": 1e4 / (kh + kr) * 1e3},
        }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "q16_rod_side_l1.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
