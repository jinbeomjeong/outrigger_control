"""Settle check of the rev80 harness-hook runs split by pad type (read-only).

Sources (spec rev. 76 396): 160 = V-3 uniform soil 72 + sensor 72 + beta 16 (soil_harness, sensor_harness,
beta_harness); 72 = reference controller soil runs (base_harness).  Per run: max |att_error_deg| (roll, pitch)
and max |gap_error_mm| (4 pads), from the record block 'settle'.
"""
import json
from collections import defaultdict
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev80")
groups = {"V3_160": ("soil_harness.json", "sensor_harness.json", "beta_harness.json"),
          "ref_72": ("base_harness.json",)}
for gname, files in groups.items():
    stat = defaultdict(lambda: [0, 0.0, 0.0, set(), set()])
    for f in files:
        runs = json.loads((D / f).read_text(encoding="utf-8"))["runs"]
        seq = list(runs.values()) if isinstance(runs, dict) else runs
        for r in seq:
            pad = r["case"]["pad"]
            st = r["settle"]
            att = max(abs(x) for x in st["att_error_deg"])
            gap = max(abs(x) for x in st["gap_error_mm"])
            for key in (pad, "all"):
                s = stat[key]
                s[0] += 1
                s[1] = max(s[1], att)
                s[2] = max(s[2], gap)
                s[3].add(r["case"]["soil"])
                s[4].add(st.get("hook"))
    print("==", gname)
    for key in ("all", "A", "B"):
        n, att, gap, soils, hooks = stat[key]
        print(f"   {key}: n {n}  max|att err| {att:.3e} deg  max|gap err| {gap:.4f} mm  soils {sorted(soils)} hooks {sorted(hooks)}")
