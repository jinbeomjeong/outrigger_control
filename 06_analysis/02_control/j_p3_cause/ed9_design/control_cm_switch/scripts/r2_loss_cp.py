"""R2 (ml_inject_cm.csv) C0 -> C-m loss: count, point rate, one-sided 95 % CP upper bound.

C-m flags a subset of C0 (two_pressure.py 2131-2136), so the loss count is c0 - cm (no gains).
Also the n_out (candidates outside k1) needed for the all-period losses to stay <= 3 %p
outside k1 when every lost candidate were outside k1 (worst case).
"""
import csv
import json
import sys

from scipy.stats import beta

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
out = []
for row in rows:
    if row["period_class"] != "transient" or row["injected_jump_bar"] == "real_steps":
        continue
    n = int(row["candidates"])
    lost = int(row["c0_flagged"]) - int(row["cm_flagged"])
    upper = float(beta.ppf(0.95, lost + 1, n - lost)) if lost < n else 1.0
    out.append({"jump_bar": row["injected_jump_bar"], "n": n, "lost": lost,
                "loss_pp": round(100 * lost / n, 3), "cp95_upper_pp": round(100 * upper, 3),
                "cm_minus_d1p_pp": round(100 * (int(row["cm_flagged"])
                                                - int(row["d1p_flagged"])) / n, 3),
                "n_out_needed_for_3pp_worst": -(-lost * 100 // 3)})
print(json.dumps(out, indent=1))
