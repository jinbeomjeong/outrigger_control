"""Sensitivity of the T3 reading (not the judgement): rule estimate, g = 1, and B-anchored estimate C_B + h_B(d) - h_B(d_a). Distinct phases in one period, repeat check of wide phases,
suffix-minimum check against the stored judge minima. Writes sweep\\sweep_sens.json."""
import json
from pathlib import Path

import numpy as np

S = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\sweep")
V = json.loads((S / "sweep_values.json").read_text(encoding="utf-8"))
LEGS = ("FL", "FR", "RL", "RR")
FMIN = 9.4146
ROWS = ("FLFs0", "FLFs8", "RRFs0")
PERIOD = [f"{0.01 * k:.2f}" for k in range(10)]
out = {}
for row in ROWS:
    r = V["rows"][row]
    ph = r["phases"]
    e = r["estimate"]
    a = f"{e['anchor_delta']:.2f}"
    CA, CB = e["chrono_common_A"], e["chrono_common_B"]
    rec = {"phases": {}}
    for d in ph:
        Ah = {l: CA[l] + ph[d]["A"][l] - ph[a]["A"][l] for l in LEGS}
        g1 = {l: Ah[l] + ph[d]["B"][l] - ph[d]["A"][l] for l in LEGS}
        banch = {l: CB[l] + ph[d]["B"][l] - ph[a]["B"][l] for l in LEGS}
        rec["phases"][d] = {"M_A": round(min(Ah.values()) - FMIN, 2), "M_rule": e["phases"][d]["MB"], "M_g1": round(min(g1.values()) - FMIN, 2), "M_Banchor": round(min(banch.values()) - FMIN, 2), "worst_leg_g1": min(g1, key=g1.get), "worst_leg_Banchor": min(banch, key=banch.get)}
    P = rec["phases"]
    for name in ("M_A", "M_rule", "M_g1", "M_Banchor"):
        rec[name + "_min"] = min(P[d][name] for d in P)
        rec[name + "_below_period"] = sum(P[d][name] < 0 for d in PERIOD)
        rec[name + "_min_phase"] = min(P, key=lambda d: P[d][name])
    rec["harness_K1_RR"] = {d: round(ph[d]["B"]["RR"] - ph[d]["A"]["RR"], 2) for d in PERIOD}
    rec["harness_deferred"] = {d: ph[d]["deferred"] for d in PERIOD}
    wide = {"0.10": "0.00", "0.20": "0.00", "0.50": "0.00", "0.70": "0.00", "0.35": "0.05"}
    rec["wide_repeat_max_diff_kN"] = round(max(abs(ph[w][arm][l] - ph[b][arm][l]) for w, b in wide.items() for arm in ("A", "B") for l in LEGS), 3)
    out[row] = rec
    print(row, {k: v for k, v in rec.items() if k != "phases"})
    for d in PERIOD:
        print("  ", d, P[d])
# suffix minimum vs stored judge
worst = 0.0
for arm in ("A", "B", "Af", "Bf"):
    z = np.load(S / f"{arm}.npz")
    for line in (S / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        key = f"{rec['row']}_{rec['delta']:.2f}"
        t, suf = z[key + "_t"], z[key + "_sufmin"]
        k = int(np.searchsorted(t, rec["W_end_s"], side="right"))
        for i, l in enumerate(LEGS):
            worst = max(worst, abs(float(suf[k, i]) / 1e3 - rec["min_F_after_W_kN"][l]))
out["suffix_vs_stored_max_kN"] = round(worst, 4)
print("suffix vs stored", worst)
(S / "sweep_sens.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
