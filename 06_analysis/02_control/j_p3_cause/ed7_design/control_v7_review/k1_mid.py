"""Where the K1 mid read of a probe falls (commanded travel), edition 7 review (Q7-C2)."""
import csv
import json
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl\03_src")
from outrigger_sim.control.ground_contact import ProbeSettings, trapezoid_speeds  # noqa: E402

s = ProbeSettings()
period = 0.1
speeds = trapezoid_speeds(s.depth_m, s.move_duration_s, s.ramp_s, period)
half = len(speeds) // 2
cum = [sum(speeds[:k]) * period for k in range(len(speeds) + 1)]
out = {"n_periods": len(speeds), "speeds_mm_s": [round(v * 1e3, 4) for v in speeds],
       "total_mm": round(cum[-1] * 1e3, 4), "half_periods": half,
       "commanded_at_mid_read_mm": round(cum[half] * 1e3, 4),
       "applied_at_mid_read_mm_d1": round(cum[max(half - 1, 0)] * 1e3, 4),
       "stroke_guard_band_mm": [-(s.stroke_guard_margin_m + s.depth_m) * 1e3,
                                -s.stroke_guard_margin_m * 1e3],
       "min_travel_mm": s.min_travel_m * 1e3}

# S4 dwell counts per eps in d2_dwells.csv (events and distinct lines)
path = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design"
        r"\dynamics_v7\d2_dwells.csv")
events = defaultdict(int)
lines = defaultdict(set)
neg = defaultdict(int)
longest = defaultdict(float)
with open(path, encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        name = row["line"]
        if not name.startswith("S4_"):
            continue
        eps = name.split("_")[1]
        events[eps] += 1
        lines[eps].add((row["set"], name))
        neg[eps] += row["sign"] == "-1"
        longest[eps] = max(longest[eps], float(row["dwell_s"]))
out["s4_dwells"] = {eps: {"events": events[eps], "lines": len(lines[eps]),
                          "negative_sign_events": neg[eps], "longest_s": longest[eps]}
                    for eps in sorted(events)}
print(json.dumps(out, indent=1))
