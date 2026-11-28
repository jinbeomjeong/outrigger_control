"""Step 6: front-leg RE1bF lines: lift phase in the 10 Hz period vs FAULT, by shape/timing.
Writes front_re1bf_lift_phase.csv (summary)."""
import csv
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(sys.argv[1])
rows = list(csv.DictReader(open(OUT / "stage5_line_census.csv", encoding="utf-8")))
front = [r for r in rows if r["event"] == "RE1bF" and r["leg"] in ("FL", "FR")]
tab = defaultdict(lambda: [0, 0, []])
for r in front:
    shape = "default" if not r["depth_m"] else f"{float(r['depth_m'])*1000:.0f}mm/{r['ramp_s']}s"
    k = (r["timing"], shape, r["offset_s"])
    tab[k][0] += 1
    tab[k][1] += r["final_phase"] == "fault"
    tab[k][2].append(r["lift_phase_in_period_s"])
with open(OUT / "front_re1bf_lift_phase.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["timing", "shape", "offset_s", "lines", "fault", "lift_phase_min_s", "lift_phase_max_s"])
    for k in sorted(tab):
        ph = [float(x) for x in tab[k][2] if x]
        w.writerow([*k, tab[k][0], tab[k][1], min(ph) if ph else "", max(ph) if ph else ""])
        print(k, tab[k][0], tab[k][1], (min(ph), max(ph)) if ph else None)
# fs and level split at 0.0875
print("== 0.0875 front lines")
for r in front:
    if r["offset_s"] == "0.0875":
        print(r["file"], r["level"], r["timing"], r["leg"], r["fs_kN"], r["depth_m"], r["ramp_s"],
              r["final_phase"], r["lift_phase_in_period_s"], r["reapproach_starts"])
