"""Soil-mode push length (mean rod-stroke progress from soil_mode_start to the LOC) and max sink rates per run."""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
for r in d["runs"]:
    m = r.get("soil_rule_meta") or {}
    rate = max(r["sink_rate_max_mm_s"]) if r.get("sink_rate_max_mm_s") else None
    push = None
    if r.get("trace") and m.get("soil_mode_entered") is not None:
        cols = r["trace_cols"]
        ix = [cols.index(c) for c in ("x_FL", "x_FR", "x_RL", "x_RR")]
        t0, t1 = m["soil_mode_entered"], m["t_loc_s"]
        def mean_x(t):
            row = min(r["trace"], key=lambda q: abs(q[0] - t))
            return sum(row[i] for i in ix) / 4
        push = mean_x(t1) - mean_x(t0)
    print(r["id"], "sink_rate_max", None if rate is None else round(rate, 1), "soil_mode", m.get("soil_mode_entered"),
          "loc", m.get("t_loc_s") and round(m["t_loc_s"], 1), "push_mm", None if push is None else round(push, 1),
          "W_hat_kN", m.get("W_hat_N") and round(m["W_hat_N"] / 1e3, 1), "W_cyl_kN", round(r["W_cyl_N"] / 1e3, 1))
