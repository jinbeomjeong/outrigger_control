"""K-2b E2 summary: Chrono L1-R S matrix (``e2_influence_step.py`` results) vs the harness linear model S (beta 1.0).

Harness S: ``06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md`` 1.3 (dynamics-expert 2026-11-11, linear
static model, crawler + 4 pads). Writes ``E2/e2_summary.json`` next to the case folders. Units kN/mm.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
HARNESS_S_BETA1 = np.array([[12.14, -4.65, -0.51, 5.74],
                            [-4.65, 12.04, 5.71, -0.61],
                            [-0.51, 5.71, 10.61, -4.63],
                            [5.74, -0.61, -4.63, 10.53]])


def alphas(S):
    return {"alpha_adj_rear_RR_on_RL": -S[2, 3] / S[3, 3], "alpha_adj_rear_RL_on_RR": -S[3, 2] / S[2, 2],
            "alpha_adj_front_FR_on_FL": -S[0, 1] / S[1, 1], "alpha_adj_front_FL_on_FR": -S[1, 0] / S[0, 0],
            "alpha_side_FR_on_RR": -S[3, 1] / S[1, 1], "alpha_side_FL_on_RL": -S[2, 0] / S[0, 0],
            "alpha_diag_FL_on_RR": -S[3, 0] / S[0, 0], "alpha_diag_FR_on_RL": -S[2, 1] / S[1, 1]}


E1_JSON = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\k2\k2b_probe\e1_smatrix.json")
"""Harness E1 (python-expert, 2026-11-11, main checkout): ``combinations[beta, kn x1].states.on_crawler.measured
.S_hold2s_kN_per_mm`` (harness own pre-load: rear pads 15.7 / 16.2 kN at beta 1.6)."""
DYN_EXTRAPOLATION = {1.6: {"C1_alpha_adj_rear": 0.66, "C3_diag_pair_on_RR": -12.2, "C4_diag_pair_on_FL": -9.3,
                           "C5_loss_per_received_kN": 0.25},
                     1.0: {"C1_alpha_adj_rear": 0.59, "C3_diag_pair_on_RR": -7.01, "C4_diag_pair_on_FL": -5.16,
                           "C5_loss_per_received_kN": 0.205}}
"""``k2_dyn_sensitivity.md`` A.4 (dynamics-expert): beta 1.6 = estimates (``lock_s.py`` beta ratio x E2 beta 1.0)."""


def harness_S(beta: float):
    if beta == 1.0:
        return HARNESS_S_BETA1, "k2_dyn_sensitivity.md 1.3 (linear model, beta 1.0)"
    d = json.loads(E1_JSON.read_text(encoding="utf-8"))
    c = [x for x in d["combinations"] if abs(x["beta_Pa"] - beta * 1e9) < 1.0 and x["crawler_kn_scale"] == 1.0][0]
    return (np.asarray(c["states"]["on_crawler"]["measured"]["S_hold2s_kN_per_mm"], float),
            f"{E1_JSON} beta {beta} kn x1 S_hold2s (harness, lock_stiffness off)")


def m2_items(S):
    """M2 items of k2_dyn_sensitivity.md B.1 by superposition of S (kN/mm)."""
    diag_rr = S[3, 1] + S[3, 2]
    received = S[1, 1] + S[1, 2] + S[2, 1] + S[2, 2]
    return {"S_RR_RL": S[3, 2], "diag_pair_FRRL_on_RR": diag_rr, "diag_pair_FRRL_on_FL": S[0, 1] + S[0, 2],
            "loss_per_received_kN": -diag_rr / received, "alpha_adj_rear_RR_from_RL": -S[3, 2] / S[2, 2],
            "S_FL_RR": S[0, 3]}


def main(root: Path) -> None:
    res = {c: json.loads((root / c / "result.json").read_text(encoding="utf-8"))
           for c in (*LEGS, "diagFRRL", "common")}
    beta = float(res["FL"].get("beta", {}).get("beta_GPa", 1.0))
    HARNESS, harness_src = harness_S(beta)
    S = np.column_stack([res[c]["S_column_kN_per_mm"] for c in LEGS])
    d = res["diagFRRL"]
    dF = np.asarray(d["dF_N"]) * 1e-3
    m2_measured = {"diag_pair_FRRL_on_RR": dF[3] / (d["ds_m"][1] * 1e3), "diag_pair_FRRL_on_FL": dF[0] / (d["ds_m"][1] * 1e3),
                   "loss_per_received_kN": -dF[3] / (dF[1] + dF[2])}
    hashes = {c: r["base_state_sha256"] for c, r in res.items()}
    base_N = {c: r["base"]["N"] for c, r in res.items()}
    pred_diag = S[:, 1] * res["diagFRRL"]["ds_m"][1] * 1e3 + S[:, 2] * res["diagFRRL"]["ds_m"][2] * 1e3
    pred_common = S @ (np.asarray(res["common"]["ds_m"]) * 1e3)
    out = {
        "S_chrono_kN_per_mm": S.tolist(), "S_harness_kN_per_mm": HARNESS.tolist(),
        "ratio_chrono_over_harness": (S / HARNESS).tolist(),
        "S_asymmetry_kN_per_mm": (S - S.T).tolist(),
        "alphas_chrono": alphas(S), "alphas_harness": alphas(HARNESS),
        "diag_FRRL": {"measured_dF_kN": (np.asarray(res["diagFRRL"]["dF_N"]) * 1e-3).tolist(),
                      "ds_mm": (np.asarray(res["diagFRRL"]["ds_m"]) * 1e3).tolist(),
                      "superposition_from_S_kN": pred_diag.tolist(),
                      "harness_kN_per_mm": (HARNESS[:, 1] + HARNESS[:, 2]).tolist()},
        "common": {"measured_dF_kN": (np.asarray(res["common"]["dF_N"]) * 1e-3).tolist(),
                   "ds_mm": (np.asarray(res["common"]["ds_m"]) * 1e3).tolist(),
                   "superposition_from_S_kN": pred_common.tolist(),
                   "harness_kN_per_mm": HARNESS.sum(axis=1).tolist()},
        "base_state_sha256": hashes, "base_identical": len(set(hashes.values())) == 1,
        "base_N_kN": {c: [v * 1e-3 for v in n] for c, n in base_N.items()},
        "ds_mm": {c: [v * 1e3 for v in r["ds_m"]] for c, r in res.items()},
        "crawler_sum_change_kN": {c: (r["response"]["cr_sum"] - r["base"]["cr_sum"]) * 1e-3 for c, r in res.items()},
        "crawler_spheres_positive": {c: [r["during_step"]["cr_n_pos_base"], r["during_step"]["cr_n_pos_min"]]
                                     for c, r in res.items()},
        "resp_window_ptp_kN": {c: [v * 1e-3 for v in r["resp_window_N_ptp_N"]] for c, r in res.items()},
        "wall_s": {c: r["timing"]["wall_s"] for c, r in res.items()},
        "identity": res["FL"]["identity"],
        "beta_GPa": beta, "harness_source": harness_src, "beta_record": res["FL"].get("beta"),
        "m2": {"chrono_superposition": m2_items(S), "chrono_measured_diag_run": m2_measured,
               "harness": m2_items(HARNESS), "dynamics_extrapolation": DYN_EXTRAPOLATION.get(beta)},
    }
    (root / "e2_summary.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    np.set_printoptions(precision=2, suppress=True)
    print("S chrono\n", S, "\nharness\n", HARNESS, "\nratio\n", S / HARNESS)
    print(json.dumps({k: out[k] for k in ("m2", "alphas_chrono", "alphas_harness", "diag_FRRL", "common", "base_identical",
                                           "base_N_kN", "ds_mm", "crawler_sum_change_kN", "crawler_spheres_positive",
                                           "resp_window_ptp_kN")}, indent=0, default=float))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
