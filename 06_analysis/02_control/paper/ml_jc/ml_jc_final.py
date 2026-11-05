"""Final tallies for the ML-set J_C misses and the stored LEVEL-event Chrono batch."""
import glob
import json
import os
import re
from collections import Counter

import numpy as np

S = r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_v4den"
ROOT = r"C:\workspace\outrigger_control"
h = json.load(open(S + r"\ml_jc_head.json", encoding="utf-8"))
d = json.load(open(S + r"\ml_jc_missed_detail.json", encoding="utf-8"))
SETS = ("test", "OOD-1", "OOD-2", "MLJ", "validation", "train")
tot = Counter()
sub = Counter()
for name in SETS:
    for it in h[name]:
        m = it["meta"]
        for r in it["rows"]:
            if r["scope"] != "scored":
                continue
            jm, pm = r["JC_first_decision_s"] is None, r["JP_first_decision_s"] is None
            tot["ep"] += 1
            tot["jc"] += jm
            tot["jp"] += pm
            tot["jc_not_jp"] += jm and not pm
            cond = "normal+zc" if (m["sensor_grade"] == "normal" and m["zero_calibration"]) else ("conservative" if m["sensor_grade"] == "conservative" else "no zero cal")
            sub[(name, cond, "ep")] += 1
            sub[(name, cond, "jc")] += jm
            sub[(cond, "ep")] += 1
            sub[(cond, "jc")] += jm
            if jm:
                ad = r["JC_action_delay_s"]
                tot["act_by_tau"] += ad is not None and ad <= 0.3
                tot["act_early"] += ad is not None and ad < 0
print(dict(tot))
for k in sorted(sub, key=str):
    print(k, sub[k])
print("non-ready ends", [(o["set"], o["run"], o["leg"], o["end_phase"], o["air_ms"], o["under_ms"]) for o in d if o["end_phase"] != "ready"])
print("lift-flag misses", sum(o["lift_flag"] for o in d), "with air>0", sum(o["lift_flag"] and o["air_ms"] > 0 for o in d), "air ms list asked sets", [(o["set"], o["run"], o["air_ms"]) for o in d if o["lift_flag"] and o["set"] in SETS[:4]])
print("event-leg asked sets", sum(o["ev_leg"] == o["leg"] for o in d if o["set"] in SETS[:3]), "dt_ev<=0.1", sum((o["dt_ev"] or 9) <= 0.1 for o in d if o["set"] in SETS[:3]))
print("est-Fmin min per set", {n: min(o["est_minus_Fmin"] for o in d if o["set"] == n) for n in SETS}, "true-at-sample min", min(o["true_at_sample_kN"] for o in d))
print("EN transient", [(r["run"], r["leg"]) for it in h["EN"] for r in it["rows"] if r["scope"] == "transient"])
print("EN E_ scored", Counter(r["run"] for it in h["EN"] for r in it["rows"] if r["scope"] == "scored" and r["run"].startswith("E_")))
print("EN phases", Counter(r["phase_on"] for it in h["EN"] for r in it["rows"] if r["run"].startswith(("E_", "N_"))))
print("sets floor/roll range", {n: (round(min(abs(i["meta"]["floor_roll_deg"] or 0) for i in h[n]), 2), round(max(abs(i["meta"]["floor_roll_deg"] or 0) for i in h[n]), 2), round(max(abs(i["meta"]["floor_pitch_deg"] or 0) for i in h[n]), 2)) for n in SETS[:3]})
print("levels", {n: Counter(i["meta"]["level"] for i in h[n]) for n in SETS[:3]})
print("Fs0 range", {n: (round(min((i["meta"]["seal_friction_N"] or [0])[0] for i in h[n]) / 1e3, 2), round(max((i["meta"]["seal_friction_N"] or [0])[0] for i in h[n]) / 1e3, 2)) for n in SETS[:3]})
ramps = []
for o in d:
    if o["set"] in SETS[:3] and o["ev_leg"]:
        src = [i for i in h[o["set"]] if i["meta"]["episode_id"] == o["run"]][0]["meta"]["source"]
        p = src if os.path.isabs(src) else os.path.join(ROOT, src)
        e = json.load(open(os.path.join(p, "result.json"), encoding="utf-8"))["episode"]
        ramps.append((o["run"], e["depth_m"] * 1e3, e["ramp_s"]))
print("depth mm / ramp s", [(a, round(b, 1), round(c, 3)) for a, b, c in ramps])
print("=== Chrono LEVEL-event batch item-9 rows")
for batch in sorted(glob.glob(os.path.join(ROOT, r"07_results\S8\c7*")) + glob.glob(os.path.join(ROOT, r"07_results\S8\c6*"))):
    for f in glob.glob(os.path.join(batch, "verify_*.json")):
        v = json.load(open(f, encoding="utf-8"))
        t = {"J_C": [0, 0, 0], "J_P": [0, 0, 0]}
        cases = set()
        missed = []
        for r in v["rows"]:
            if r["item"].startswith(("item 9 J_C M1", "item 9 J_P M1")):
                m = re.search(r"episodes (\d+)", r.get("note") or "")
                if m:
                    j = r["judge"]
                    t[j][0] += int(m[1])
                    t[j][1] += r["value"][0] or 0
                    t[j][2] += 1
                    if (r["value"][0] or 0) and j == "J_C":
                        missed.append(r["case"])
                    cases.add(r["case"])
        print(os.path.basename(batch), os.path.basename(f)[:30], "cases", len(cases), "[ep, M1, rows]", t, "J_C missed in", missed[:12], "G1L cases", sum(c.startswith("G1L") for c in cases))
