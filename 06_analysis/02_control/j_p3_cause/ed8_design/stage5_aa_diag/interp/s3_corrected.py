"""Interp step 3: per label, the lift-adjacent period k and the step period k+1 from
residual_split.csv: event-leg unloaded fraction at k, r_k, r_k+1, the shares, the change with an
ideal lever correction (dr - d lever_share = d window_share), against the candidate thresholds
(first_step_period.csv). Also one-sided 95 % Clopper-Pearson upper bounds x/310 for x = 0..11.
Writes interp/pair_periods.csv and interp/cp95_table.csv (estimates, record only)."""
import csv
import sys
from pathlib import Path

from scipy.stats import beta

D = Path(sys.argv[1])
split = list(csv.DictReader(open(D / "interp" / "residual_split.csv", encoding="utf-8")))
first = list(csv.DictReader(open(D / "first_step_period.csv", encoding="utf-8")))
win = list(csv.DictReader(open(D / "interp" / "window_rows.csv", encoding="utf-8")))
EVENT_LEG = {"J1": "FR", "J2": "FR", "J3": "FL", "J4": "FR", "S1": "FL", "S2": "FR", "S3": "FL"}
out = []
for lab in EVENT_LEG:
    f = [r for r in first if r["label"].startswith(lab)]
    t_step = float(f[0]["t_s"])
    thr = {r["leg"]: float(r["threshold_kN"]) for r in f}
    rows = sorted([r for r in split if r["label"] == lab], key=lambda r: float(r["t_s"]))
    k1 = next(i for i, r in enumerate(rows) if abs(float(r["t_s"]) - t_step) < 1e-3)
    a, b = rows[k1 - 1], rows[k1]
    w = sorted([r for r in win if r["label"].startswith(lab)], key=lambda r: float(r["t_s"]))
    leg = EVENT_LEG[lab]
    p0 = float(w[0][f"head_bar_{leg}"])
    pk = float(next(r for r in w if abs(float(r["t_s"]) - float(a["t_s"])) < 1e-3)[f"head_bar_{leg}"])
    dr = float(b["residual_kN"]) - float(a["residual_kN"])
    dlev = float(b["lever_share_kN"]) - float(a["lever_share_kN"])
    dwin = float(b["window_share_kN"]) - float(a["window_share_kN"])
    out.append({"label": lab, "final": f[0]["final_phase"], "lift_phase_s": f[0]["lift_phase_in_period_s"],
                "t_k_minus_lift_ms": round(float(a["t_rel_lift_s"]) * 1000, 1),
                "event_leg_unloaded_at_k": round(1 - pk / p0, 3),
                "r_k_kN": a["residual_kN"], "r_k1_kN": b["residual_kN"],
                "lever_k_kN": a["lever_share_kN"], "window_k_kN": a["window_share_kN"],
                "abs_dr_kN": round(abs(dr), 1), "d_lever_kN": round(dlev, 1), "d_window_kN": round(dwin, 1),
                "abs_dr_lever_corrected_kN": round(abs(dwin), 1),
                "thresholds_kN": ";".join(f"{k}:{v:.1f}" for k, v in thr.items()),
                "unexplained_now": ";".join(k for k, v in thr.items() if abs(dr) >= v),
                "unexplained_if_lever_corrected": ";".join(k for k, v in thr.items() if abs(dwin) >= v)})
with open(D / "interp" / "pair_periods.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(out[0]))
    wr.writeheader()
    wr.writerows(out)
for o in out:
    print(o)
with open(D / "interp" / "cp95_table.csv", "w", newline="", encoding="utf-8") as fh:
    wr = csv.writer(fh)
    wr.writerow(["x_aa", "n_aa", "cp95_upper_one_sided"])
    for x in range(0, 12):
        u = 1.0 if x == 310 else float(beta.ppf(0.95, x + 1, 310 - x))
        wr.writerow([x, 310, round(u, 5)])
        print("cp95", x, round(u, 5))
