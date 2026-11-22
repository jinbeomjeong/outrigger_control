"""Drill-down on the study result lines (read only).

1. top-level keys of one line; where the controller settings record step_rule / imu_outputs;
2. R0 vs R0-d1p: command hash equality and the recorded D1 rule;
3. the runs that end in FAULT (any arm): key, fault events;
4. the pair ref|rigid|B|2.7355,1.7592 (L2 seed 1, 2): M3, check duration, t_touch, LOC, gyro bias, events around
   the minimum for R0 / B-k / C-k / A-k.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1])
lines = {}
first = None
for path in sorted(d.glob("imuatt_*_*.jsonl")):
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        ln = json.loads(text)
        first = first or ln
        lines[(ln["arm"], ln["level"], int(ln["seed_index"]), ln["case_id"])] = ln
print("keys", sorted(first))


def find(obj, names, path=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k in names:
                out.append((p, v if not isinstance(v, (dict, list)) else str(v)[:80]))
            out += find(v, names, p)
    elif isinstance(obj, list) and len(obj) < 50:
        for i, v in enumerate(obj):
            out += find(v, names, f"{path}[{i}]")
    return out


for arm in ("R0", "R0-d1p", "B-k"):
    ln = lines[(arm, "L2", 0, first["case_id"])]
    print(arm, find({k: v for k, v in ln.items() if k not in ("events",)},
                    {"step_rule", "imu_outputs", "crawler_recontact_watch", "controller_tag", "probe_cue"})[:12])

same = diff = 0
diffs = []
for (arm, lv, s, cid), ln in lines.items():
    if arm != "R0-d1p":
        continue
    ref = lines.get(("R0", lv, s, cid))
    if ref is None:
        continue
    if ln.get("commands_sha256") == ref.get("commands_sha256"):
        same += 1
    else:
        diff += 1
        diffs.append((lv, s, cid))
print("R0-d1p vs R0 command hash: same", same, "differ", diff, diffs[:5])

print("== runs ending in FAULT")
for key, ln in lines.items():
    ev = ln.get("events") or []
    names = [e[1] if isinstance(e, (list, tuple)) else str(e) for e in ev]
    if ln["run_metrics"]["M5_final_phase"] == "fault" or ln["run_metrics"]["M5_fault_events"]:
        print(key, [n for n in names if n.startswith(("FAULT", "INFO_HEAD", "WARN_ROD", "WARN_D1"))][:8],
              "t_ready", ln["run_metrics"]["t_ready_s"])
print("== runs not ending in READY")
for key, ln in lines.items():
    fp = ln["run_metrics"]["M5_final_phase"]
    if fp != "ready":
        print(key, fp, "t_ready", ln["run_metrics"]["t_ready_s"], "rows", ln["run_metrics"]["rows"])

print("== pair ref|rigid|B|2.7355,1.7592")
cid = "ref|rigid|B|2.7355,1.7592"
for s in (0, 1, 2):
    for arm in ("R0", "C-k", "B-k", "A-k", "A-g", "B-r"):
        ln = lines.get((arm, "L2", s, cid))
        if ln is None:
            continue
        m = ln["run_metrics"]
        print(s, arm, "M3", m["M3_kN"], "below", m["M3_below_F_min"], "chk", m["check_duration_s"],
              "t_touch", m["t_touch_start_s"], "t_ready", m["t_ready_s"], "M2", m["M2_s"], "loc", m["M8_loc"],
              "B1", m["gyro_bias_outcome"], "dsb", m["M8_dsb75_holds"], "rev", m["M8_loc_revokes"])
ln = lines[("R0", "L2", 1, cid)]
lb = lines[("B-k", "L2", 1, cid)]
for name, x in (("R0", ln), ("B-k", lb)):
    ev = x.get("events") or []
    print(name, "events", [e for e in ev][:40])
