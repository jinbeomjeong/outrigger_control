"""Step 5: census of all 1356 stage 5 V0 lines: FAULT / D1 warnings by (event, leg, timing,
shape, fs, offset); the lift-to-sample phase of each line. Writes stage5_line_census.csv and
fault_by_offset.csv."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(sys.argv[1])
RUNS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248")
FILES = {"v0": RUNS / r"ho_v0_a1\ed8_heldout_v0.jsonl", "aa2": RUNS / r"ho_aa2_a1\ed8_heldout_aa2.jsonl",
         "aa3": RUNS / r"ho_aa3_a1\ed8_heldout_aa3.jsonl"}
PERIOD = 0.1
rows = []
seen = set()
for name, path in FILES.items():
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            job, twin = row["job"], row["job"].get("twin") or {}
            v, eo = row.get("values", {}), row.get("event_output") or {}
            t_ev = row.get("t_event_s")
            lifts = eo.get("lifts") or {}
            leg = twin.get("leg")
            first = (lifts.get(leg) or {}).get("first_s")
            t_lift = None if (t_ev is None or first is None) else t_ev + first
            def phase(t):
                return None if t is None else round((t / PERIOD - math.floor(t / PERIOD + 1e-9)) * PERIOD, 4)
            warns = set(eo.get("warnings") or []) | set(v.get("events", {}).get("warn_events") or [])
            faults = v.get("events", {}).get("fault_events") or []
            key = (json.dumps(job, sort_keys=True))
            dup = key in seen
            seen.add(key)
            rows.append({
                "file": name, "case": job.get("case"), "level": twin.get("level"), "timing": twin.get("timing"),
                "leg": leg, "event": twin.get("event"), "fs_kN": twin.get("fs_kN"),
                "depth_m": twin.get("depth_m"), "ramp_s": twin.get("ramp_s"), "offset_s": job.get("offset_s"),
                "t_event_s": t_ev, "event_phase_in_period_s": phase(t_ev),
                "t_lift_event_leg_s": None if t_lift is None else round(t_lift, 4),
                "lift_phase_in_period_s": phase(t_lift),
                "final_phase": row.get("final_phase"), "faults": ";".join(faults),
                "head_fault_reason": ";".join(w for w in sorted(warns) if w.startswith("INFO_HEAD_PRESSURE_FAULT_REASON")),
                "gyro_missing": "WARN_D1_IMU_GYRO_MISSING" in warns,
                "rod_fallback_D6": any(w.endswith(":D6") for w in warns),
                "reapproach_starts": ";".join(f"{a}:{b}" for a, b in (eo.get("reapproach_starts") or [])),
                "n_rev": (row.get("command_stats") or {}).get("n_rev"),
                "pass": eo.get("pass"), "duplicate_job": dup,
            })
with open(OUT / "stage5_line_census.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

uniq = [r for r in rows if not r["duplicate_job"]]
tab = defaultdict(lambda: [0, 0, 0, 0])
for r in uniq:
    if r["event"] is None:
        continue
    k = (r["event"], "front" if r["leg"] in ("FL", "FR") else "rear", r["timing"], r["offset_s"])
    tab[k][0] += 1
    tab[k][1] += r["final_phase"] == "fault"
    tab[k][2] += bool(r["gyro_missing"])
    tab[k][3] += bool(r["rod_fallback_D6"])
with open(OUT / "fault_by_offset.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["event", "leg_side", "timing", "offset_s", "lines", "fault", "gyro_missing_warn", "rod_fallback_D6"])
    for k in sorted(tab, key=lambda k: tuple(str(x) for x in k)):
        w.writerow([*k, *tab[k]])
print("lines", len(rows), "unique jobs", len(uniq))
for k in sorted(tab, key=lambda k: tuple(str(x) for x in k)):
    if tab[k][1] or k[0] == "RE1bF":
        print(k, tab[k])
print("== fault lines")
for r in uniq:
    if r["final_phase"] == "fault":
        print(r["file"], r["level"], r["timing"], r["leg"], r["event"], r["fs_kN"], r["depth_m"], r["ramp_s"],
              r["offset_s"], "tev", r["t_event_s"], "lift", r["t_lift_event_leg_s"], r["faults"], r["head_fault_reason"])
