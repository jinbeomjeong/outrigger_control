"""Assemble m1_m2_reference.json from the saved review results; print hand vs simulation errors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import common
from common import OUT, dump, pin_two_cores
import poc_friction as pf
import poc_reversal as pr
from params import load_params

ALPHAS = ("0.05", "0.1", "0.25", "1")
FS = ("0", "2", "4", "8")
MOVE_THRESHOLD_M = 2.0e-4


def main() -> None:
    pin_two_cores()
    p = load_params()
    fr = json.loads((OUT / "poc_friction.json").read_text(encoding="utf-8"))
    su = json.loads((OUT / "poc_sustained.json").read_text(encoding="utf-8"))
    m2 = json.loads((OUT / "m2_check.json").read_text(encoding="utf-8"))
    table = {}
    errs_open, errs_ext = [], []
    for leg in ("FL", "RL"):
        table[leg] = {}
        for fs in FS:
            hand = fr["hand"][f"{leg}_Fs{fs}"]
            table[leg][f"Fs{fs}"] = {"hand_inputs": {k: hand[k] for k in ("p_h0_bar_g", "p_open_line_B_bar_g", "dp_h_at_open_bar", "piston_creep_before_open_mm", "V_line_cm3", "V_rod_cm3", "V_creep_cm3", "retract_open_V_cm3", "retract_open_stroke_mm", "extend_open_V_cm3", "extend_friction_V_cm3", "extend_dead_stroke_mm", "head_dump_stroke_mm")},
                                     "F_s_N": fr["hopsan"][f"{leg}_Fs{fs}_a0.05"]["F_s_N"], "by_command": {}}
            for a in ALPHAS:
                run = fr["hopsan"][f"{leg}_Fs{fs}_a{a}"]["motions"]
                ret, ext = run["ret_after_ext"], run["ext_after_ret"]
                v = float(a) * p.v_max
                hand_open = hand["retract_open_t_s"][a]
                hand_ext = pf.time_to_stroke(hand["extend_dead_stroke_mm"] * 1e-3 + MOVE_THRESHOLD_M, v)
                table[leg][f"Fs{fs}"]["by_command"][a] = {
                    "retract_check_open_s": {"hopsan": ret["t_poc_a_open_after_cmd_s"], "hand": hand_open},
                    "retract_piston_0p2mm_s": {"hopsan": ret["t_move_after_cmd_s"]},
                    "extend_piston_0p2mm_s": {"hopsan": ext["t_move_after_cmd_s"], "hand": hand_ext},
                    "ideal_0p2mm_s": ret["t_move_ideal_s"],
                    "stroke_lag_retract_mm": ret["stroke_lag_at_hold_end_mm"], "stroke_lag_extend_mm": ext["stroke_lag_at_hold_end_mm"],
                    "line_b_at_open_bar_g": ret["line_b_at_open_bar_g"], "p_h_at_open_bar_g": ret["p_h_at_open_bar_g"]}
                errs_open.append((abs(hand_open / ret["t_poc_a_open_after_cmd_s"] - 1.0), leg, fs, a))
                # the extend after retract at v_max still rings from the retract: not a clean reference
                if a != "1":
                    errs_ext.append((abs(hand_ext / ext["t_move_after_cmd_s"] - 1.0), leg, fs, a))
    print("retract open hand vs Hopsan max", max(errs_open))
    print("extend hand vs Hopsan max", max(errs_ext), "FsO only", max(e for e in errs_ext if e[2] == "0"))
    fixed = m2["fixed_body"]
    closed = m2["closed"]
    ref = {
        "status": "reference values for unit tests; every hydraulic input below is an ASSUMPTION until the maker answers V-6, L-1 and the hose data",
        "dimensions": "current REXOME35 (02_params/rexome33.yaml); L2 history not used",
        "pressure_reference": "bar gauge unless named Pa",
        "user_decision_2026_11_05": "M2 joins the v5 scope, M1 is decided after the harness test, the full two-chamber model stays out",
        "inputs": fr["meta"]["assumptions"] | {"beta_chamber_Pa": p.beta, "L0h_m": p.L0h, "L0r_m": p.L0r, "stroke_m": p.stroke,
                                                  "A_h_m2": {"FL": float(p.A_h[0]), "RL": float(p.A_h[2])}, "A_ann_m2": {"FL": float(p.A_r[0]), "RL": float(p.A_r[2])},
                                                  "s0_m": {"FL": float(p.s0[0]), "RL": float(p.s0[2])}, "static_load_note": "flat, top auger, single leg mass = F0 / g",
                                                  "piston_damper_N_s_m": {"FL": 34403.5, "RL": 30348.5}, "rear_friction_scale": 0.833},
        "M1": {
            "purpose": "start delay until the check valves pass flow; off by default",
            "retract": {"opening_condition": "p_T + psi p_B - p_h - p_crack = 0 with p_h rising by (A_ann dp_r - F_s)+ / A_h while the rod creeps on the compressible head",
                        "volume": "V_line (p_open - p_T) / beta_hose + V_r (p_open - p_r0) / beta + A_ann creep, creep = V_h dp_h / (beta A_h)",
                        "after_opening": "the head chamber charges line A: extra piston travel V_line (p_h - p_T) / (beta_hose A_h)"},
            "extend": {"volume": "V_line (p_h + p_crack - p_T) / beta_hose + (V_line / beta_hose + V_h / beta) F_s / A_h"},
            "time_from_volume": "invert s = v (t - tau_v (1 - exp(-t / tau_v))) for the lagged command; see the hand values",
            "metrics": {"retract_check_open_s": "first time POC-A is open after the command", "extend_piston_0p2mm_s": "piston moved 0.2 mm (hand: dead stroke + 0.2 mm)",
                        "warning": "retract_piston_0p2mm_s is reached by elastic creep before the check opens when F_s is small; use check opening for retract"},
            "tolerance_proposal": {"retract_check_open": "+-5 % against hopsan", "extend_0p2mm": "+-10 % against hopsan for F_s 0; +-15 % with friction"},
            "table": table,
            "neutral_variants": "poc_reversal.json cases a0.1_blocked, a0.25_blocked: same-direction restart delay nearly gone with A,B blocked; first motion after a reversal remains",
        },
        "hand_16_percent_mismatch": {
            "result": "resolved: the first hand calculation left out the piston creep and compared check opening with a 0.2 mm stroke mark",
            "numbers_FL_Fs0_0p05": {"first_hand_open_s": 1.24, "piston_0p2mm_hopsan_s": 1.043, "corrected_hand_open_s": table["FL"]["Fs0"]["by_command"]["0.05"]["retract_check_open_s"]["hand"],
                                    "check_open_hopsan_s": table["FL"]["Fs0"]["by_command"]["0.05"]["retract_check_open_s"]["hopsan"]},
            "max_error_corrected_retract_open": float(max(errs_open)[0]),
        },
        "M2": {
            "rule": "moving leg, armed law: s_ref += A_ann (p_r_prev - p_r) / k_h(s_ref) each step, k_h = beta A_h / (L0h + s_ref); force then moves by (k2 / k_h) A_ann dp",
            "coefficient": {"k_h_N_m": fixed["k_h_N_m"], "k_out_N_m": fixed["k_out_N_m"], "k2_N_m": fixed["k2_N_m"], "k2_over_k_h": fixed["k2_over_k_h"], "leg": "FL at s0",
                            "derivation": "oil force G = k_h (s_ref - s_p) - A_ann p_r + const: a rod pressure drop acts as s_ref shift A_ann dp / k_h; series k_out gives k2 / k_h"},
            "body_fixed_unit_case": {"description": "FL, body held, extend 0.25 v_max 0.5 s, end force of rod start 34.818 against 2 bar g", "expected_kN": fixed["expected_end_diff_kN"],
                                     "numpy_kN": fixed["end_diff_numpy_kN"], "law_with_M2_wrapper_kN": fixed["end_diff_law_m2_kN"], "law_without_M2_kN": fixed["end_diff_law_kN"], "tolerance_kN": 0.3,
                                     "implied_coefficient": {"numpy": fixed["implied_coefficient_numpy"], "wrapper": fixed["implied_coefficient_law_m2"]},
                                     "hopsan_excluded": {"value_kN": fixed["end_diff_hopsan_kN"], "reason": "end pressures differ (5.84 / 4.78 bar g) and the mass Position drift enters k_st directly with the body held; cause not separated"}},
            "free_body_cases": {name: {k: closed[name][k]["dF_max_kN"] for k in ("hopsan", "numpy", "law", "law_m2")} | {f"{k}_F_end_kN": closed[name][k]["F_end_kN"] for k in ("hopsan", "numpy", "law", "law_m2")}
                                for name in ("C2_release_ground", "C3_release_ground_r2", "B_twist", "A_stop_all_eta95")},
            "free_body_net_force_10Hz_error_kN": {name: {k: closed[name][f"{k}_vs_hopsan"]["F_net_10Hz_abs_max_kN"] for k in ("law", "law_m2")} for name in ("C2_release_ground", "C3_release_ground_r2", "B_twist", "A_stop_all_eta95")},
            "tolerance_proposal": {"C2_minus_C3_F_end_FL_kN": {"hopsan": closed["C2_release_ground"]["hopsan"]["F_end_kN"][0] - closed["C3_release_ground_r2"]["hopsan"]["F_end_kN"][0],
                                                                   "numpy": closed["C2_release_ground"]["numpy"]["F_end_kN"][0] - closed["C3_release_ground_r2"]["numpy"]["F_end_kN"][0],
                                                                   "wrapper": closed["C2_release_ground"]["law_m2"]["F_end_kN"][0] - closed["C3_release_ground_r2"]["law_m2"]["F_end_kN"][0], "tolerance_kN": 0.5},
                                   "A_stop_all": "no change beyond 0.05 kN against the law without M2"},
            "implementation_notes": ["03_src not changed; the wrapper is scratch code m2_check.py", "off by default, absent = bit identical", "snapshot must keep the previous rod pressure",
                                     "friction path: use the oil-law rod pressure before the head-floor split; check k_h is the same oil k_h", "CB path not tested", "retract after extend not tested in the four-leg model (no check valve there)",
                                     "L1 and the reduced harness need their own decision: the wrapper is L2b only"],
        },
        "sources": ["poc_friction.json", "poc_sustained.json", "m2_check.json", "poc_reversal.json", "four_leg.json"],
    }
    dump("m1_m2_reference.json", ref)
    print(json.dumps(ref["M2"]["tolerance_proposal"]["C2_minus_C3_F_end_FL_kN"]))
    print({k: round(v, 3) for k, v in ref["hand_16_percent_mismatch"]["numbers_FL_Fs0_0p05"].items()})
    for leg in ("FL", "RL"):
        for fs in FS:
            print(leg, fs, [(a, round(table[leg][f"Fs{fs}"]["by_command"][a]["retract_check_open_s"]["hopsan"], 3), round(table[leg][f"Fs{fs}"]["by_command"][a]["extend_piston_0p2mm_s"]["hopsan"], 3), round(table[leg][f"Fs{fs}"]["by_command"][a]["extend_piston_0p2mm_s"]["hand"], 3)) for a in ALPHAS])


if __name__ == "__main__":
    main()
