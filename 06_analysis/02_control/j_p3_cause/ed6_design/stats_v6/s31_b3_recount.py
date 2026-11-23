"""Ed. 6 B3 recount after the dynamics judgement (ed6_design/dynamics_v6/b3_dynamics_report.md)
and the user decision 2026-11-23: B3-only protect threshold ~44 kN (F_min + 35), cumulative cap
<= 5 cycles of command travel (stats-design-expert, review, design only).

Inputs (cited, not recomputed): k_tw 21.7 MN/m, protected-leg dF per cycle rear 11.35 / front
10.34 kN (report 1 table row "four legs moving"); the output delay d = 1 leaves 2 more cycles of
motion after the last passing read (report 2); protected-leg load at the R-5 read over R12 32 rows
min 91.6 / median 99.6 kN (report 2, line 72; seen rows, O6-5 [contaminated-after]).
R-5 leg force at R-5 from control_v6/b3_early_window.csv (seen rows) as a cross-check only.
Writes s31_b3_recount.json / .txt. stdout: status only.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta, norm

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "control_v6" / "b3_early_window.csv"
F_MIN = 9.415
DF = {"rear": 11.35, "front": 10.34}
PER_CYCLE_MM = 0.25 * 20.924 * 0.1
CAP_CYCLES = 5


def cp_up(k, n, conf=0.95):
    return float(beta.ppf(conf, k + 1, n - k)) if k < n else 1.0


def worst_min(threshold, df, start):
    """Protected-leg minimum: motion continues while the read is >= threshold, plus 2 cycles
    (d = 1) after the last passing read; at most CAP_CYCLES of motion; start load `start`."""
    n_pass = 0
    load = start
    while load >= threshold and n_pass < CAP_CYCLES:
        n_pass += 1                       # this read passes -> one more cycle commanded
        load = start - df * n_pass        # read after that cycle (quasi-static, delay handled below)
    cycles = min(n_pass + 1, CAP_CYCLES) if n_pass > 0 else 0   # +1 extra cycle from d = 1
    # report 2: after the last passing read two more cycles move; our loop already counted one
    return start - df * cycles, cycles


def main() -> int:
    out = {"inputs": {"dF_per_cycle_kN": DF, "cap_cycles": CAP_CYCLES,
                      "cap_travel_mm": CAP_CYCLES * PER_CYCLE_MM,
                      "protected_at_r5_R12_32": {"min": 91.6, "median": 99.6}},
           "worst_min": {}, "blocking": {}}
    for name, thr in (("old_Fmin+5", F_MIN + 5.0), ("b3_Fmin+35", F_MIN + 35.0)):
        for side, df in DF.items():
            # closed form of report 2: worst = last passing read - 2 dF >= threshold - 2 dF
            row = {"closed_form_floor_kN": thr - 2 * df, "scan": {}}
            for start in (30.0, 44.0, 50.0, 57.0, 70.0, 91.6, 99.6):
                w, c = worst_min(thr, df, start)
                row["scan"][str(start)] = {"min_kN": w, "motion_cycles": c,
                                           "lift": bool(w < 0.0), "below_Fmin": bool(w < F_MIN)}
            out["worst_min"][f"{name}|{side}"] = row
    # blocking of a true-event start before hand-over (reads reflect <= 3 cycles of motion)
    thr = F_MIN + 35.0
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    r5_force = np.array([float(r["min_leg_force_at_r5_kN"]) for r in rows])
    handover_reads = np.array([int(float(r["window_reads"])) for r in rows])
    sd_par = (99.6 - 91.6) / norm.ppf(1 - 1 / 33)          # min of 32 ~ 1/33 quantile
    out["blocking"] = {
        "threshold_kN": thr,
        "observed_block": "0/32 (protected min 91.6 kN at R-5)",
        "cp95_upper_independent_32": cp_up(0, 32),
        "cp95_upper_key_clusters_15": cp_up(0, 15),
        "parametric_sd_kN": float(sd_par),
        "parametric_P_below_thr_at_start": float(norm.cdf((thr - 99.6) / sd_par)),
        "read_after_3_cycles_at_min_kN": 91.6 - 3 * DF["rear"],
        "read_after_4_cycles_at_min_kN": 91.6 - 4 * DF["rear"],
        "start_load_needed_to_never_block_before_handover_kN": thr + 3 * DF["rear"],
        "handover_reads_max": int(handover_reads.max()),
        "r5_leg_force_kN_min_median_max": [float(r5_force.min()), float(np.median(r5_force)),
                                           float(r5_force.max())],
        "n_csv_rows": len(rows)}
    ok = len(rows) == 32 and out["worst_min"]["b3_Fmin+35|rear"]["closed_form_floor_kN"] > F_MIN
    out["self_check"] = ok
    (HERE / "s31_b3_recount.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                              encoding="utf-8")
    L = [json.dumps(out["inputs"])]
    for k, v in out["worst_min"].items():
        L.append(f"{k:<18} floor {v['closed_form_floor_kN']:.2f} kN | " + " ".join(
            f"P{s}:{x['min_kN']:.1f}({x['motion_cycles']}c{'*LIFT' if x['lift'] else ''})"
            for s, x in v["scan"].items()))
    L.append(json.dumps(out["blocking"]))
    (HERE / "s31_b3_recount.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
