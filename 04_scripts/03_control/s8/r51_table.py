"""R51-1 comparison table from r51_reapp_closed_loop.py JSON: worst over the start phases per (base, event, variant).
Rows: ML events (U-S8-32 gate: pair union <= 1.8 s, pair last touch-down <= 3.0 s, adjacent gap <= 2 mm) and
regression events (G4 / SS: min true cylinder force; RE1bF / RE1bP / FLdrop: diagonal-leg lift sum and gap (U57),
event-leg last touch-down). Usage: python -I r51_table.py <json> [<out_json>]
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
LEGS = ("FL", "FR", "RL", "RR")
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
EV_LEG = {"G4": "RR", "SS": "RR", "RE1bF": "RR", "RE1bP": "RR", "FLdrop": "FL"}
table = {}
for r in d["runs"]:
    if "error" in r:
        continue
    for e in r["events"]:
        if "error" in e:
            continue
        key = (r["base"], e["event"])
        cell = table.setdefault(key, {}).setdefault(r["variant"], {"n": 0, "fail": 0, "pairU": 0, "pairLast": 0, "adjGap": 0,
                                                                     "late": 0, "W": 0, "minF": 1e9, "diagLift": 0,
                                                                     "diagGap": 0, "evLast": 0, "starts": 0, "D8": None})
        cell["n"] += 1
        cell["fail"] += 0 if all(e["gate_U832"].values()) else 1
        cell["pairU"] = max(cell["pairU"], e["pair_union_s"])
        cell["pairLast"] = max(cell["pairLast"], e["pair_last_touch_s"])
        cell["adjGap"] = max(cell["adjGap"], e["adj_max_gap_mm"])
        cell["late"] = max(cell["late"], e["n_late_starts"])
        cell["starts"] = max(cell["starts"], e["n_starts"])
        cell["W"] = max(cell["W"], e["W_after1.5_pos_J"])
        cell["minF"] = min(cell["minF"], e["min_true_kN"])
        cell["D8"] = r["D8_min_true_after_liftoff_kN"]
        ev = EV_LEG.get(e["event"])
        if ev:
            dl = e["lifts"].get(DIAG[ev], {})
            cell["diagLift"] = max(cell["diagLift"], dl.get("sum_s", 0.0))
            cell["diagGap"] = max(cell["diagGap"], dl.get("max_gap_mm", 0.0))
            cell["evLast"] = max(cell["evLast"], e["lifts"].get(ev, {}).get("last_touch_s", 0.0))
            # min true force while no leg is lifted is not separable per chunk here: report the window min
variants = list(dict.fromkeys(r["variant"] for r in d["runs"]))
for (base, ev), cells in table.items():
    print(f"== {base} {ev}")
    for v in variants:
        c = cells.get(v)
        if not c:
            continue
        if ev in EV_LEG:
            print(f"   {v:7s} D8 {c['D8']:.1f} minF {c['minF']:.2f} diagLift {c['diagLift']:.3f} diagGap {c['diagGap']:.2f} "
                  f"evLast {c['evLast']:.3f} starts {c['starts']} late {c['late']} W+ {c['W']:.0f}")
        else:
            print(f"   {v:7s} fail {c['fail']}/{c['n']} pairU {c['pairU']:.3f} pairLast {c['pairLast']:.3f} "
                  f"adjGap {c['adjGap']:.2f} late {c['late']} W+ {c['W']:.0f}")
if len(sys.argv) > 2:
    json.dump({f"{b}|{e}": v for (b, e), v in table.items()}, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
