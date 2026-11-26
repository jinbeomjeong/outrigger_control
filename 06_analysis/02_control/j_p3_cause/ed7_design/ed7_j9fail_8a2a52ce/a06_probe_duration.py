"""a06: (a) stiffness WARN table of the VBM / LSM j9main lines, (b) PROBE phase durations and
(i-b) retract-extra totals, VBM vs VBL (same job keys, j9main), (c) post-event t_back margin
to the 60 s post-event window. Output a06_probe_duration.csv / .json."""
import csv
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
rows = list(csv.DictReader(open(os.path.join(OUT, "a01_line_summary.csv"), encoding="utf-8")))

print("== (a) stiffness WARN lines, ed7 j9main")
for r in rows:
    if r["source"] == "ed7_j9main" and int(r["stiff_n"]) > 0 and r["setting"] in ("VBM", "LSM4"):
        print(r["setting"], r["key"], r["stiff_ratios"], r["stiff_t_s"], r["t_event_s"])
print("== (a2) stiffness WARN, sens (setting: lines, ratio range)")
agg = {}
for r in rows:
    if r["source"] == "ed7_sens" and int(r["stiff_n"]) > 0:
        v = [float(x) for x in r["stiff_ratios"].split(";")]
        a = agg.setdefault(r["setting"], [0, 9, 0])
        a[0] += 1
        a[1] = min(a[1], min(v))
        a[2] = max(a[2], max(v))
print(json.dumps(agg))


def probe_info(path):
    z = np.load(path, allow_pickle=False)
    t = z["t_s"]
    ph = z["phase"].astype(str)
    runs = []
    s = 0
    for i in range(1, len(ph) + 1):
        if i == len(ph) or ph[i] != ph[s]:
            runs.append((ph[s], float(t[s]), float(t[i - 1])))
            s = i
    probes = [round(b - a + 0.1, 1) for (p, a, b) in runs if p == "probe"]
    meta = json.loads(str(z["meta_json"]))
    rec = meta.get("probe_d6_record") or {}
    extra = [r.get("retract_extra_m") for r in rec.get("rounds", []) if r.get("retract_extra_m") is not None]
    return probes, round(float(np.sum(extra)) * 1e3, 2) if extra else None, len(extra)


tab = []
d7 = J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h"
d6 = J9 + r"\79495405\records_after_stop\B_a1\j9_main_t4h"
for f in sorted(os.listdir(d7)):
    if not f.endswith("_VBM.npz"):
        continue
    stem = f[:-len("_VBM.npz")]
    p6 = os.path.join(d6, stem + "_VBL.npz")
    if not os.path.exists(p6):
        continue
    pr7, ex7, n7 = probe_info(os.path.join(d7, f))
    pr6, _, _ = probe_info(p6)
    tab.append({"key": stem, "probe_s_VBM": pr7, "probe_s_VBL": pr6,
                "probe1_delta_s": round(pr7[0] - pr6[0], 1) if pr7 and pr6 else None,
                "extra_retract_mm_total": ex7, "extra_rounds": n7})
with open(os.path.join(OUT, "a06_probe_duration.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(tab[0].keys()))
    w.writeheader()
    for r in tab:
        w.writerow({k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()})
deltas = [r["probe1_delta_s"] for r in tab if r["probe1_delta_s"] is not None]
print("== (b) first PROBE duration VBM - VBL over", len(deltas), "keys: min/median/max",
      min(deltas), float(np.median(deltas)), max(deltas))
first = [r["probe_s_VBL"][0] for r in tab if r["probe_s_VBL"]]
print("   VBL first probe s median", float(np.median(first)), "VBM", float(np.median([r["probe_s_VBM"][0] for r in tab if r["probe_s_VBM"]])))

print("== (c) event rows: t_back margin to the post-event window (run end - t_event)")
by = {}
for r in rows:
    if r["source"] in ("ed7_j9main", "ed6rec_j9main", "ed5_j9main") and r["t_event_s"] not in ("", "None"):
        fam = {"ed7_j9main": "ed7", "ed6rec_j9main": "ed6", "ed5_j9main": "ed5"}[r["source"]]
        tb = r["t_ready_back_s"]
        by.setdefault(fam, []).append(None if tb in ("", "None") else float(tb))
summary = {}
for fam, v in by.items():
    vals = [x for x in v if x is not None]
    summary[fam] = {"event_lines": len(v), "no_back": sum(x is None for x in v),
                    "t_back_median": float(np.median(vals)), "t_back_p90": float(np.percentile(vals, 90)),
                    "t_back_max": max(vals), "over_50s": sum(x > 50 for x in vals)}
print(json.dumps(summary, indent=1))
json.dump({"stiff_sens": agg, "probe_delta": {"n": len(deltas), "min": min(deltas),
           "median": float(np.median(deltas)), "max": max(deltas)}, "t_back": summary},
          open(os.path.join(OUT, "a06_probe_duration.json"), "w", encoding="utf-8"), indent=1)
