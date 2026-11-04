"""S8 safe stop detail (criteria 9.1, spec 427 SA-4, 430.4.1): crawler load around the stop, limit on vs stored off.

Reads the run folders only. Sensitivity of the clause "crawler after the stop <= crawler at the stop + 0.01 W" to the
reference sample, crawler recontact history, leg forces after the stop, the flow state in LEVEL. Writes
s8_stop_detail.json and the CSV for the Julia cross check (scratch folder given as argv[1]).

Run: conda run -n dynamics-dev python -I s8_stop_detail.py <scratch folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
S9 = ROOT / "07_results/S9"
CASE = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
SIDES = {"on": S9 / "batch_COUPLED_eta085_20261104_142213" / CASE, "off": S9 / "batch_FINAL-REP_20261030_223359" / CASE}
RUNS_FOR_CSV = {
    "S8_on": S9 / "batch_COUPLED_eta085_20261104_142213" / CASE,
    "S8_off": S9 / "batch_FINAL-REP_20261030_223359" / CASE,
    "S6_on": S9 / "batch_COUPLED_eta085_20261104_142213" / "P3b_J2_B_top_Fs4_m1p1_t180",
    "S6_off": S9 / "batch_FINAL-REP-X_20261031_020716" / "P3b_J2_B_top_Fs4_m1p1_t180",
    "S1_on": S9 / "batch_COUPLED_eta085_20261104_142213" / "P3b_J1_B_top_Fs4",
    "S1_off": S9 / "batch_FINAL-REP_20261030_223359" / "P3b_J1_B_top_Fs4",
}
WEIGHT_KN = 380.11291206408396
LIMIT_FRAC = 0.01
FLAT_KN = LIMIT_FRAC * WEIGHT_KN


def contacts(t, c, thr):
    """Spans where the crawler normal is at or above thr."""
    a = c >= thr
    edges = np.diff(np.concatenate(([0], a.astype(int), [0])))
    return [[round(float(t[i]), 3), round(float(t[j - 1]), 3), round(float(c[i:j].max()), 3)]
            for i, j in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]


def side(path: Path) -> dict:
    res = json.loads((path / "result.json").read_text(encoding="utf-8"))
    t0 = float(res["t_loop_start_s"])
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        t = np.asarray(z["t_s"])
        c = np.asarray(z["scm_crawler_normal_N"]) / 1e3
        F = np.asarray(z["F_cyl_N"]) / 1e3
        rp = np.asarray(z["roll_pitch_deg"])
        patches = np.asarray(z["scm_crawler_patches"])
    t_stop = next(float(e["t_s"]) for e in res["events"] if str(e["name"]).startswith("FAULT_LIFT_STROKE_LIMIT"))
    k = int(np.searchsorted(t, t_stop))
    k_end_first = min(k + 1000, len(t))
    rel = t - t0
    refs = {}
    for name, val in (("at_stop_sample", c[k]), ("mean_1s_before", c[k - 1000:k].mean()), ("mean_0p2s_before", c[k - 200:k].mean()),
                      ("median_1s_before", float(np.median(c[k - 1000:k]))), ("max_1s_before", c[k - 1000:k].max()),
                      ("max_5s_before", c[k - 5000:k].max()), ("mean_0p2s_around", c[k - 100:k + 100].mean())):
        refs[name] = {"ref_kN": float(val), "limit_kN": float(val + FLAT_KN), "passes": bool(c[k:].max() <= val + FLAT_KN)}
    j = k + int(np.argmax(c[k:]))
    i0 = int(np.searchsorted(t, t0 + 25.0))
    cmax_prestop = int(i0 + np.argmax(c[i0:k]))
    grid = [-1.0, -0.5, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]
    return {"t_stop_rel_s": t_stop - t0, "crawler_at_stop_kN": float(c[k]), "crawler_max_after_kN": float(c[k:].max()),
            "crawler_max_after_t_after_stop_s": float(t[j] - t_stop), "crawler_end_kN": float(c[-1]),
            "rise_after_stop_kN": float(c[k:].max() - c[k]), "limit_rise_kN": FLAT_KN,
            "reference_sensitivity": refs,
            "crawler_trace_rel_stop": {str(g): float(c[int(np.searchsorted(t, t_stop + g))]) for g in grid},
            "crawler_max_before_stop_kN": float(c[cmax_prestop]), "crawler_max_before_stop_rel_s": float(rel[cmax_prestop]),
            "crawler_std_1s_before_kN": float(c[k - 1000:k].std()), "crawler_ptp_1s_before_kN": float(np.ptp(c[k - 1000:k])),
            "crawler_ptp_1s_after_kN": float(np.ptp(c[k:k_end_first])),
            "contact_spans_ge_0p01W_rel_s": contacts(rel[i0:], c[i0:], FLAT_KN),
            "patches_at_stop": int(patches[k]),
            "F_after_stop_min_kN": F[k:].min(axis=0).round(3).tolist(), "F_after_stop_min_t_after_s": (t[k + F[k:].argmin(axis=0)] - t_stop).round(3).tolist(),
            "F_at_stop_kN": F[k].round(3).tolist(), "F_end_kN": F[-1].round(3).tolist(),
            "attitude_at_stop_deg": rp[k].round(4).tolist(), "attitude_end_deg": rp[-1000:].mean(axis=0).round(4).tolist()}


def main() -> None:
    scratch = Path(sys.argv[1])
    out = {name: side(path) for name, path in SIDES.items()}
    (HERE / "s8_stop_detail.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=0))
    for name, path in RUNS_FOR_CSV.items():
        with np.load(path / "step_series.npz", allow_pickle=False) as z:
            t, c, F = z["t_s"], z["scm_crawler_normal_N"], z["F_cyl_N"]
        np.savetxt(scratch / f"{name}.csv", np.column_stack([t, c, F]), delimiter=",", fmt="%.17g",
                   header="t_s,crawler_N,F_FL_N,F_FR_N,F_RL_N,F_RR_N", comments="")


if __name__ == "__main__":
    main()
