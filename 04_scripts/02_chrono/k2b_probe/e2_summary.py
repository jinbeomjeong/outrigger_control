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


def main(root: Path) -> None:
    res = {c: json.loads((root / c / "result.json").read_text(encoding="utf-8"))
           for c in (*LEGS, "diagFRRL", "common")}
    S = np.column_stack([res[c]["S_column_kN_per_mm"] for c in LEGS])
    hashes = {c: r["base_state_sha256"] for c, r in res.items()}
    base_N = {c: r["base"]["N"] for c, r in res.items()}
    pred_diag = S[:, 1] * res["diagFRRL"]["ds_m"][1] * 1e3 + S[:, 2] * res["diagFRRL"]["ds_m"][2] * 1e3
    pred_common = S @ (np.asarray(res["common"]["ds_m"]) * 1e3)
    out = {
        "S_chrono_kN_per_mm": S.tolist(), "S_harness_kN_per_mm": HARNESS_S_BETA1.tolist(),
        "ratio_chrono_over_harness": (S / HARNESS_S_BETA1).tolist(),
        "S_asymmetry_kN_per_mm": (S - S.T).tolist(),
        "alphas_chrono": alphas(S), "alphas_harness": alphas(HARNESS_S_BETA1),
        "diag_FRRL": {"measured_dF_kN": (np.asarray(res["diagFRRL"]["dF_N"]) * 1e-3).tolist(),
                      "ds_mm": (np.asarray(res["diagFRRL"]["ds_m"]) * 1e3).tolist(),
                      "superposition_from_S_kN": pred_diag.tolist(),
                      "harness_kN_per_mm": (HARNESS_S_BETA1[:, 1] + HARNESS_S_BETA1[:, 2]).tolist()},
        "common": {"measured_dF_kN": (np.asarray(res["common"]["dF_N"]) * 1e-3).tolist(),
                   "ds_mm": (np.asarray(res["common"]["ds_m"]) * 1e3).tolist(),
                   "superposition_from_S_kN": pred_common.tolist(),
                   "harness_kN_per_mm": HARNESS_S_BETA1.sum(axis=1).tolist()},
        "base_state_sha256": hashes, "base_identical": len(set(hashes.values())) == 1,
        "base_N_kN": {c: [v * 1e-3 for v in n] for c, n in base_N.items()},
        "ds_mm": {c: [v * 1e3 for v in r["ds_m"]] for c, r in res.items()},
        "crawler_sum_change_kN": {c: (r["response"]["cr_sum"] - r["base"]["cr_sum"]) * 1e-3 for c, r in res.items()},
        "crawler_spheres_positive": {c: [r["during_step"]["cr_n_pos_base"], r["during_step"]["cr_n_pos_min"]]
                                     for c, r in res.items()},
        "resp_window_ptp_kN": {c: [v * 1e-3 for v in r["resp_window_N_ptp_N"]] for c, r in res.items()},
        "wall_s": {c: r["timing"]["wall_s"] for c, r in res.items()},
        "identity": res["FL"]["identity"],
    }
    (root / "e2_summary.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    np.set_printoptions(precision=2, suppress=True)
    print("S chrono\n", S, "\nratio\n", S / HARNESS_S_BETA1)
    print(json.dumps({k: out[k] for k in ("alphas_chrono", "alphas_harness", "diag_FRRL", "common", "base_identical",
                                           "base_N_kN", "ds_mm", "crawler_sum_change_kN", "crawler_spheres_positive",
                                           "resp_window_ptp_kN")}, indent=0, default=float))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
