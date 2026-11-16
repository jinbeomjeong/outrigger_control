"""Step 7: F_min effect of the five J-P3 breach lines (counterfactual fallback), from records only.

For each line: rod annulus area A_ann (from the stored locked tolerance 0.6 kN / A_ann),
counterfactual optimism of the fallback lower bound at the worst breach read
``|min_gap| * A_ann`` (lower = head_only - max(13 bar, p_hat + delta_m) A_ann, truth uses the
plant p_tr: the optimism is exactly the gap times A_ann), the implied plant p_tr at that read
assuming p_hat = p_ret (retract floor of the one retracting read; tracker relief in the window
< 0.2 bar, see report 2.3), true minimum force after the event and its margin over F_min, and
for the R12 lines the true force of the breach leg at the reads 48.7-49.2 s from the T4h record.

Usage: python -I -B s07_fmin_effect.py <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

RK1 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
F_MIN_N = 9414.58911
P_RET_PA = (34.818e5, 34.352e5, 31.193e5, 30.591e5)
"""Controller p_ret per leg (two_pressure RETRACT_LOCK_ROD_PRESSURE_WITHOUT_YAML_PA = YAML)."""
DELTA_M_PA = 0.5e5
LEGS = ("FL", "FR", "RL", "RR")


def h10_line(n):
    lines = (RK1 / "h10_reuse_rerun.jsonl").read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[n - 1])
    hr = rec["hydraulics_record"]
    mins = rec["values"]["forces"]["after_liftoff"]
    return rec["job"], hr["extend_bound_check"], mins


def grid_run(fn, ri, rj):
    d = json.loads((RK1 / "h9_grid" / fn).read_text(encoding="utf-8"))
    run = d["results"][ri]["runs"][rj]
    mins = run["min_F_after_event_kN"]
    leg = min(mins, key=mins.get)
    return d["results"][ri]["key"], run["hydraulics_record"]["extend_bound_check"], {
        "min_kN": mins[leg], "leg": leg, "all_kN": mins}


def row(label, leg, ebc, mins, t4h=None):
    tol_bar = ebc["locked_tolerance_bar"][leg]
    a_ann = 600.0 / (tol_bar * 1e5)
    gap_bar = ebc["min_gap_bar"][leg]
    optimism_kN = -gap_bar * 1e5 * a_ann / 1e3
    p_tr_bar = (P_RET_PA[leg] + DELTA_M_PA) / 1e5 - gap_bar
    out = {"line": label, "leg": LEGS[leg], "breach_reads": ebc["breach_reads"][leg],
           "min_gap_bar": gap_bar, "min_gap_t_s": ebc["min_gap_t_s"][leg], "A_ann_m2": a_ann,
           "optimism_kN": optimism_kN, "implied_p_tr_bar": p_tr_bar,
           "p_ret_plus_dm_bar": (P_RET_PA[leg] + DELTA_M_PA) / 1e5,
           "true_min_after_event_kN": mins["min_kN"], "lightest_leg": mins["leg"],
           "margin_over_F_min_kN": mins["min_kN"] - F_MIN_N / 1e3}
    if t4h is not None:
        z = np.load(t4h, allow_pickle=True)
        t = z["t_s"]
        m = (t > 48.65) & (t < 49.25)
        out["breach_leg_true_force_kN"] = {f"{tt:.1f}": round(float(f) / 1e3, 3)
                                           for tt, f in zip(t[m], z["true_force_N"][m, leg])}
        out["breach_leg_true_force_min_kN"] = {f"{tt:.1f}": round(float(f) / 1e3, 3)
                                               for tt, f in zip(t[m], z["true_force_min_N"][m, leg])}
    return out


def main():
    rows = []
    t4h = RK1 / "h10_reuse_rerun_t4h"
    for n, setting in ((28, "VB"), (172, "LS2"), (245, "LS3")):
        job, ebc, mins = h10_line(n)
        assert job["setting"] == setting
        rows.append(row(f"h10 line {n} R12 {setting}", 3, ebc, mins,
                        t4h / f"R12_bottom-FL-Fs4-o0.0_{setting}.npz"))
    key, ebc, mins = grid_run("grid_r67_top.json", 13, 3)
    rows.append(row(f"grid_r67_top results[13].runs[3] {key}", 1, ebc, mins))
    key, ebc, mins = grid_run("grid_r69_bottom.json", 12, 0)
    rows.append(row(f"grid_r69_bottom results[12].runs[0] {key}", 3, ebc, mins))
    # VB 48.8 s read: plant locked after a retraction (not compared by ExtendBoundCheck), monitor
    # with a positive acting command uses the extension estimate p_hat + delta_m.
    z = np.load(t4h / "R12_bottom-FL-Fs4-o0.0_VB.npz", allow_pickle=True)
    i = int(np.argmin(np.abs(z["t_s"] - 48.8)))
    p_locked = float(z["rod_pressure_Pa"][i, 3])
    uncounted = {"read_t_s": float(z["t_s"][i]), "rod_reading_locked_bar": p_locked / 1e5,
                 "gap_bar_vs_p_ret_plus_dm": (P_RET_PA[3] + DELTA_M_PA - p_locked) / 1e5,
                 "optimism_kN": (p_locked - P_RET_PA[3] - DELTA_M_PA) * 3.14159265e-3 / 1e3,
                 "note": "rod reading of a locked harness leg = p_r0 - Gr/A_ann = plant p_tr"}
    for r in rows:
        print(json.dumps(r))
    print("VB 48.8 uncounted read:", json.dumps(uncounted))
    Path(sys.argv[1]).write_text(json.dumps({"rows": rows, "vb_48p8_uncounted": uncounted,
                                             "F_min_N": F_MIN_N}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
