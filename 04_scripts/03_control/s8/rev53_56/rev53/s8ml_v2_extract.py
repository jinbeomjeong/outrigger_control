"""Extract per-seed rows from the P-S8-19 detailed report (read only)."""
import json
import sys
from pathlib import Path

import numpy as np

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for name, runs in report["per_model"].items():
    print(f"===== {name}")
    for run in runs:
        t = run["test"]
        ml, jc = t["ML"], t["J_C"]
        print(f"seed {run['seed']} thr {run['threshold']}")
        print("  test ML  missed", ml["M1_missed"], "late", ml["M1p_late"], "M2", ml["M2_false_action_flags"],
              "M3med", ml["M3_median_delay_s"], "M4max", ml["M4_max_N"], "M4 p5/50/95", ml["M4_p5_p50_p95_N"])
        print("  test J_C missed", jc["M1_missed"], "late", jc["M1p_late"], "M2", jc["M2_false_action_flags"],
              "M3med", jc["M3_median_delay_s"], "M4max", jc["M4_max_N"], "M4 p5/50/95", jc["M4_p5_p50_p95_N"])
        d_ml = np.array(ml["M3_delays_s"]); d_jc = np.array(jc["M3_delays_s"])
        print("  delays ML n", d_ml.size, "q25/50/75", np.percentile(d_ml, [25, 50, 75]) if d_ml.size else None,
              " J_C n", d_jc.size, np.percentile(d_jc, [25, 50, 75]) if d_jc.size else None)
        rows = run["E1_rows"]
        for k in ("record_raw", "sensitivity_upper_bound", "record_threshold_0.5"):
            r = rows[k]
            print(f"  {k}: ML {r['ML_missed']} J_C {r['J_C_missed']} MLff {r['ML_false_action_flags']} JCff {r['J_C_false_action_flags']}")
        tc = run["threshold_choice"]
        cands = tc["candidates"]
        feas = [c for c in cands if c["ML_missed"] <= tc["J_C_missed"]]
        print("  val J_C missed", tc["J_C_missed"], "feasible thr range",
              (min(c["threshold"] for c in feas), max(c["threshold"] for c in feas)) if feas else None)
        compact = [(c["threshold"], c["ML_missed"], c["ML_false_action_flags"]) for c in cands
                   if c["threshold"] in (0.01, 0.02, 0.05, 0.09, 0.1, 0.2, 0.3, 0.31, 0.4, 0.5, 0.6, 0.7)]
        print("  val (thr, miss, ff):", compact)
        if "en_groups" in run:
            en = run["en_groups"]
            print("  EN M4", en["M4_max_N"], "groups", en["detail"]["groups"])
            for m in en["detail"]["missed_episodes"]:
                print("    missed", m)
        cov = run["quantile_coverage"]
        print("  coverage val", cov["validation"], "test", cov["test"])
