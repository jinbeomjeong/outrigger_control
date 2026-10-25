"""R51-1 / P-S8-16: which main-ML episodes would the re-trigger rule change (offline, recorded controller events).

Rule (rev. 52): a re-approach that starts within ``retrigger_window_s`` (2.0 s) of the end of the previous one runs at
``retrigger_speed_factor`` (0.6); a start on the other diagonal (twist sign differs from the last run) within
``opposite_window_s`` (0.8 s) of that end needs the lower load estimate < 0 N on 2 samples. The recorded trajectory is
unchanged up to the first such start, so an episode is "affected" iff it has one after the event. Read only.
Usage: python -I r51_affected.py <batch_dir> <out_json>
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SIGN = {"FL": 1, "FR": -1, "RL": -1, "RR": 1}
RETRIGGER_S, OPPOSITE_S = 2.0, 0.8
batch = Path(sys.argv[1])
rows = []
for case in sorted((batch / "episodes").iterdir()):
    if not case.is_dir() or case.name.startswith("_"):
        continue
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    cj = json.loads((case / "case.json").read_text(encoding="utf-8"))
    ep, b = cj["settings"]["episode"], cj["settings"]["base"]
    t_ev = float(res.get("event_t_s") or res.get("branch_t_s"))
    seq = []
    for e in json.loads((case / "controller_events.json").read_text(encoding="utf-8")):
        s = str(e)
        for tag in ("leg_reapproach_start:", "leg_reapproach_contact:", "WARN_LEG_REAPPROACH_NO_CONTACT:"):
            if tag in s:
                seq.append((float(s.split("t_s=")[1].split(",")[0]), tag, s.split(tag)[1][:2]))
    seq.sort()
    last_end, last_sign = None, 0
    retrig = opp = 0
    first = None
    for t, tag, leg in seq:
        if tag == "leg_reapproach_start:":
            if last_end is not None and t >= t_ev - 1e-6:
                dt = t - last_end
                if dt < RETRIGGER_S - 1e-9:
                    retrig += 1
                    first = first if first is not None else round(t - t_ev, 2)
                if dt < OPPOSITE_S - 1e-9 and SIGN[leg] != last_sign:
                    opp += 1
            last_sign = SIGN[leg]
        else:
            last_end = t
    rows.append({"case": case.name, "kind": ep.get("kind"), "leg": ep.get("leg"),
                 "depth_mm": round(1e3 * float(ep.get("depth_m") or 0), 2), "ramp_s": ep.get("ramp_s"),
                 "level": b["level"], "retriggers": retrig, "opposite_in_window": opp, "first_change_rel_s": first})
aff = [r for r in rows if r["retriggers"] > 0]
json.dump({"rule": {"retrigger_window_s": RETRIGGER_S, "opposite_window_s": OPPOSITE_S}, "n_episodes": len(rows),
           "affected": [r["case"] for r in aff], "rows": rows},
          open(sys.argv[2], "w", encoding="utf-8"), indent=1)
print("episodes", len(rows), "affected", len(aff), "with opposite-in-window", sum(1 for r in aff if r["opposite_in_window"]))
from collections import Counter
print("by kind/level", Counter((r["kind"], r["level"], r["leg"][:1] if r["leg"] else None) for r in aff))
for r in sorted(aff, key=lambda r: -r["retriggers"])[:60]:
    print(f"  {r['case']:9s} {r['kind']:7s} {r['leg']} {r['depth_mm']:6.2f} mm ramp {r['ramp_s']} {r['level']:6s} "
          f"retrig {r['retriggers']} opp {r['opposite_in_window']} first {r['first_change_rel_s']}")
