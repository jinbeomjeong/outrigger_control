"""Rev. 64: summary views of r64_preready_scan.json (phases of the pre-READY steps, crawler load,
ratios; crawler force sanity of a few runs).

Usage: python -I r64_scan_view.py <r64_preready_scan.json>
Read only.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
pre = d["steps_pre_ready_gt50"]
print("pre-READY >50 bar steps by phase:", Counter(s["phase"] for s in pre))
print("  with crawler load > 2 kN at the step:", sum(s["crawler_kN"] > 2 for s in pre))
print("  after LOC:", sum(s["after_loc"] for s in pre))
print("  |dp| max by phase:", {p: max(abs(s["dp_bar"]) for s in pre if s["phase"] == p)
                                for p in {s["phase"] for s in pre}})
hi = sorted(pre, key=lambda s: -s["ratio_sum"])[:12]
for s in hi:
    print(f"   {Path(s['case']).parent.name}/{Path(s['case']).name} t {s['t']} {s['leg']} "
          f"dp {s['dp_bar']} ph {s['phase']} crawler {s['crawler_prev_kN']}->{s['crawler_kN']} kN "
          f"sum {s['ratio_sum']} imu_yaml {s.get('ratio_imu_yaml')} imu_ready {s.get('ratio_imu_ready')}")
post = d["steps_post_ready_gt100"]
print("post-READY >100 bar steps:", len(post), "phases", Counter(s["phase"] for s in post))
print("  crawler > 2 kN at step:", sum(s["crawler_kN"] > 2 for s in post))
print("  batches:", Counter(Path(s["case"]).parts[-3] for s in post).most_common(8))
runs = d["runs"]
full = [r for r in runs if not r["starts_in_ready"]]
print("full runs by batch (top):", Counter("/".join(Path(r["case"]).parts[1:3])
                                           for r in full).most_common(12))
print("full runs without READY:", Counter("/".join(Path(r["case"]).parts[1:3])
                                          for r in full if r["t_ready"] is None).most_common(10))
loc = [r for r in full if "loc" in r["masses_kg"]]
print("LOC mass source:", Counter(r.get("loc_mass_source") for r in loc))
rel = [(r["masses_kg"]["loc"] / r["masses_kg"]["ready"] - 1, Path(r["case"]).name) for r in loc
       if "ready" in r["masses_kg"]]
rel.sort()
print("LOC/READY - 1 lowest:", [(round(a, 4), b) for a, b in rel[:6]], "highest:",
      [(round(a, 4), b) for a, b in rel[-3:]])
yr = [r["masses_kg"]["ready"] / 38400.8 - 1 for r in full if "ready" in r["masses_kg"]]
print("READY/YAML - 1: min %.4f p50 %.4f max %.4f" % (min(yr), float(np.median(yr)), max(yr)))
# crawler sanity
for r in full[:3]:
    rec = np.load(Path(r["case"]) / "record" / "record.npz", allow_pickle=True)
    fc = np.asarray(rec["F_crawler"], float)
    print("crawler force sample", Path(r["case"]).name, "first", np.round(fc[0] / 1e3, 1),
          "max |z|", round(float(np.abs(fc[:, 2]).max()) / 1e3, 1), "at end",
          np.round(fc[-1] / 1e3, 1), "t_ready", r["t_ready"])

hi2 = sorted(pre, key=lambda s: -s.get("ratio_imu_yaml", 0))[:6]
print("pre-READY highest D1'' (YAML mass) ratios:")
for s in hi2:
    print(f"   {'/'.join(Path(s['case']).parts[1:])} t {s['t']} {s['leg']} dp {s['dp_bar']} ph {s['phase']} "
          f"sum {s['ratio_sum']} imu_yaml {s.get('ratio_imu_yaml')} imu_ready {s.get('ratio_imu_ready')}")
print("pre-READY >50 steps by batch:", Counter("/".join(Path(s["case"]).parts[1:3]) for s in pre).most_common(10))
