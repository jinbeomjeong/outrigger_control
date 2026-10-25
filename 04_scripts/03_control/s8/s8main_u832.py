"""Rev. 51: U-S8-32 rows of the main ML batch (event legs, adjacent U57) with base conditions.

Usage: python -I s8main_u832.py <batch_dir> <out_json>
For every U-S8-32 event-leg / adjacent row: settle leg, depth, speed, event-leg cumulative lift,
last re-contact, adjacent lift sum and gap, joined with base level / F_s / beta / leg_scale /
floor from case.json. Prints tails (re-contact > 2.0 s, adjacent gap > 1 mm), front vs rear
statistics, and the rank of ML78 episodes. Read only.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
batch = Path(sys.argv[1])
out = Path(sys.argv[2])
v = json.loads((batch / "verify_S8ML.json").read_text(encoding="utf-8"))
ev_rows, adj_rows = {}, {}
for r in v["rows"]:
    it = r.get("item", "")
    if it.startswith("U-S8-32 event legs"):
        ev_rows[r["case"]] = r
    elif it.startswith("U-S8-32 adjacent legs"):
        adj_rows[r["case"]] = r
rows = []
for case, r in ev_rows.items():
    sp = r.get("split", {})
    a = adj_rows.get(case, {}).get("split", {})
    cj = json.loads((batch / "episodes" / case / "case.json").read_text(encoding="utf-8"))
    b = cj["settings"]["base"]
    rows.append({
        "case": case, "settle_leg": sp.get("settle_leg"), "depth_mm": 1e3 * sp.get("depth_m", 0.0),
        "speed_mm_s": sp.get("settle_speed_mm_s"), "event_cum_s": sp.get("event_cum_max_s"),
        "recontact_s": sp.get("event_recontact_max_rel_s"), "fault": sp.get("fault_t_s") is not None,
        "adj_sum_s": a.get("adjacent_sum_s"), "adj_gap_mm": 1e3 * (a.get("adjacent_gap_max_m") or 0.0),
        "adj_outside_s": a.get("adjacent_outside_window_s"),
        "event_pass": r.get("passed"), "adj_pass": adj_rows.get(case, {}).get("passed"),
        "level": b["level"], "fs_kN": b["fs_kN"], "beta_GPa": b["beta_GPa"], "leg_scale": b["leg_scale"],
        "floor_deg": b["floor_deg"],
    })
json.dump({"rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
print(f"event rows {len(ev_rows)}, adjacent rows {len(adj_rows)}, joined {len(rows)}")
front = [x for x in rows if x["settle_leg"] in ("FL", "FR")]
rear = [x for x in rows if x["settle_leg"] in ("RL", "RR")]
for name, grp in (("front", front), ("rear", rear)):
    rc = np.array([x["recontact_s"] or 0 for x in grp])
    gp = np.array([x["adj_gap_mm"] for x in grp])
    sm = np.array([x["adj_sum_s"] or 0 for x in grp])
    print(f"{name}: n {len(grp)}, recontact p50 {np.median(rc):.3f} p95 {np.percentile(rc,95):.3f} max {rc.max():.3f} s, >2.5 s {int((rc>2.5).sum())}, >3.0 s {int((rc>3.0).sum())};"
          f" adj gap p95 {np.percentile(gp,95):.2f} max {gp.max():.2f} mm, >2 mm {int((gp>2).sum())}; adj sum max {sm.max():.3f} s")
print("\ntail: re-contact > 2.0 s or adjacent gap > 1.0 mm (sorted by re-contact)")
tail = [x for x in rows if (x["recontact_s"] or 0) > 2.0 or x["adj_gap_mm"] > 1.0]
for x in sorted(tail, key=lambda x: -(x["recontact_s"] or 0)):
    print(f"  {x['case']:9s} {x['settle_leg']} {x['depth_mm']:5.1f} mm {x['speed_mm_s']:6.0f} mm/s | cum {x['event_cum_s']:.3f} recon {x['recontact_s']:.3f} | adj {x['adj_sum_s']:.3f} s gap {x['adj_gap_mm']:.2f} mm | "
          f"{x['level']:6s} Fs {x['fs_kN']:.2f} beta {x['beta_GPa']:.2f} scale {x['leg_scale']} floor {x['floor_deg']} | pass ev {x['event_pass']} adj {x['adj_pass']}")
# fast front settles: conditions of the worst vs the rest
ff = [x for x in front if (x["speed_mm_s"] or 0) > 50 and (x["depth_mm"] > 15)]
print(f"\nfast (> 50 mm/s) deep (> 15 mm) front settles: {len(ff)}")
for x in sorted(ff, key=lambda x: -(x["recontact_s"] or 0))[:25]:
    print(f"  {x['case']:9s} {x['settle_leg']} {x['depth_mm']:5.1f} {x['speed_mm_s']:5.0f} | recon {x['recontact_s']:.3f} cum {x['event_cum_s']:.3f} adj gap {x['adj_gap_mm']:.2f} sum {x['adj_sum_s']:.3f} | {x['level']} Fs {x['fs_kN']:.2f} beta {x['beta_GPa']:.2f} scale {x['leg_scale']}")
