"""a09: probe 6bfb2560 arms (stored, before the seal): which arms switch the (i-b) retract
position target / A_ib, and per (arm, plant) the stiffness WARN incidence, S7 t_ready and
post-event t_back. Used to separate the (i-b) controller change from the plant patch.
Output a09_probe_arms.csv / .json."""
import csv
import json
import os
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
P = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560"
     r"\ed7_probe_a1\ed7_probe.jsonl")
STIFF = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
agg = defaultdict(lambda: {"lines": 0, "stiff_lines": 0, "keys": []})
rows = []
arm_settings = {}
with open(P, encoding="utf-8") as f:
    for ln in f:
        d = json.loads(ln)
        job = d.get("job", {})
        name = d.get("t4h_file") or ""
        arm = name.rsplit("-", 1)[-1].replace(".npz", "") if name else job.get("arm")
        # file name form: <key>_P7-<plant>-<arm>.npz
        tail = name.rsplit("_P7-", 1)[-1].replace(".npz", "") if "_P7-" in name else ""
        plant = tail.rsplit("-", 1)[0] if tail else None
        pd6 = d.get("probe_d6_settings") or {}
        comps = d.get("lsb_components")
        arm_settings.setdefault(arm, {"retract_position_target": pd6.get("retract_position_target"),
                                      "witness": pd6.get("witness"), "lsb_components": comps})
        events = d.get("events") or []
        stiff = [n for _, n in events if str(n).startswith(STIFF)]
        key = name.split("_P7-")[0] if "_P7-" in name else name
        a = agg[(arm, plant)]
        a["lines"] += 1
        a["stiff_lines"] += bool(stiff)
        if stiff:
            a["keys"].append(key)
        eo = d.get("event_output") or {}
        rows.append({"arm": arm, "plant": plant, "key": key, "case": job.get("case"),
                     "stiff": ";".join(s.split(":")[1] for s in stiff),
                     "t_first_ready_s": ((d.get("values") or {}).get("times") or {}).get("t_first_ready_s"),
                     "t_back_s": eo.get("t_ready_back_s"), "final": d.get("final_phase"),
                     "rpt": pd6.get("retract_position_target")})
with open(os.path.join(OUT, "a09_probe_arms.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("arm settings", json.dumps(arm_settings))
for k, v in sorted(agg.items(), key=lambda x: str(x[0])):
    print(k, v["lines"], v["stiff_lines"], v["keys"][:12])
print("== same (plant, key) in arm c2 vs a2: S7 t_ready, R12 event t_back, stiff")
idx = {(r["arm"], r["plant"], r["key"]): r for r in rows}
pairs = []
for (arm, plant, key), r in idx.items():
    if arm != "c2":
        continue
    o = idx.get(("a2", plant, key))
    if o is None:
        continue
    pairs.append({"plant": plant, "key": key, "c2_ready": r["t_first_ready_s"],
                  "a2_ready": o["t_first_ready_s"], "c2_back": r["t_back_s"], "a2_back": o["t_back_s"],
                  "c2_stiff": r["stiff"], "a2_stiff": o["stiff"], "c2_final": r["final"],
                  "a2_final": o["final"]})
for p in sorted(pairs, key=lambda x: (x["plant"], x["key"])):
    print(json.dumps(p))
with open(os.path.join(OUT, "a09_probe_c2_vs_a2.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
    w.writeheader()
    w.writerows(pairs)
json.dump({"arm_settings": arm_settings,
           "agg": {f"{k[0]}|{k[1]}": v for k, v in agg.items()}},
          open(os.path.join(OUT, "a09_probe_arms.json"), "w", encoding="utf-8"), indent=1)
