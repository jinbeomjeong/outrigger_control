"""Ed. 7 Q7-S5: T-JR-12b P-pred (spec v6 6.4, inherited by spec v7 6.4) when its input floor comes
from the new plant VBKM0 (P1 fix + ed. 7 components incl. A_ib in both arms). Re-checks the
whole-procedure false failure and power over truth scenarios that the new plant may produce.
stats-design-expert, 2026-11-24. Reuses the s71 model/procedure code of ed6_design/stats_v6
(same author; imported from file, unchanged).
Truths (per-line no-READY rate of the control arm, case clustering rho, |dREADY| > 30 s rate r2):
  T0 ed5 point (pC 6/168, pR 1/166, rho 0.6, r2 1/324)       - unchanged floor
  Tlow  floor / 10 (A_ib removes most LEVEL deadlocks)
  Tzero pC = pR = 0.001
  Tx2   floor x 2 (P1 fix (a)/(d) adds stalls)
  Tr2x5 T0 with r2 x 5 (A_ib pulses spread READY times)
  Tlow_r2x5, Trho0 (T0, rho 0), Trho09 (T0, rho 0.9)
Procedure: spec b1/b2 inputs ('spec'), and b1/b2/b4 B-plan ('b124B', TRw rate = pR).
Outputs (argv[1]): s50_12b_recheck.json / .txt. stdout: status only.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

S71 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\stats_v6"
           r"\s71_ppred_rev9.py")
spec = importlib.util.spec_from_file_location("s71", S71)
s71 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s71)


def main() -> int:
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(20261124)
    base = {"pC": 6 / 168, "pR": 1 / 166, "rho": 0.6, "r2": 1 / 324, "cross": "shared",
            "f_pre": 0.0, "pT": 1 / 166}
    truths = {
        "T0": base,
        "Tlow": {**base, "pC": base["pC"] / 10, "pR": base["pR"] / 10, "pT": base["pT"] / 10},
        "Tzero": {**base, "pC": 0.001, "pR": 0.001, "pT": 0.001},
        "Tx2": {**base, "pC": base["pC"] * 2, "pR": base["pR"] * 2, "pT": base["pT"] * 2},
        "Tr2x5": {**base, "r2": 5 / 324},
        "Tlow_r2x5": {**base, "pC": base["pC"] / 10, "pR": base["pR"] / 10, "pT": base["pT"] / 10,
                      "r2": 5 / 324},
        "Trho0": {**base, "rho": 0.0},
        "Trho09": {**base, "rho": 0.9},
    }
    res = {"s71_source": str(S71), "seed": 20261124, "alpha": s71.ALPHA, "configs": {}}
    for name, t in truths.items():
        res["configs"][f"{name}|spec"] = s71.run(rng, t, "spec", None, reps=120)
        res["configs"][f"{name}|b124B"] = s71.run(rng, t, "spec", "B", reps=80)
    (out_dir / "s50_12b_recheck.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item()),
                                                  encoding="utf-8")
    L = [f"alpha {s71.ALPHA}"]
    for n, r in res["configs"].items():
        L.append(f"{n:<18} k q05/50/95 {r['k_q05_50_95']} | FPR {100*r['fpr']:.2f}% "
                 f"(cond p95 {100*r['fpr_cond_p95']:.1f}%) | power d2 {100*r['power_d2']:.1f}% "
                 f"d3 {100*r['power_d3']:.1f}%")
    (out_dir / "s50_12b_recheck.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
