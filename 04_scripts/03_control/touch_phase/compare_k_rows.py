"""Rows of C4G1 + K1 against the C4G1 rows and the stored flow-off rows; which rows K1 changes.

Output: krows_C4G1K1_compare.json and stdout. Forces kN, READY s. R2 is read from the kextra batch (stored decision).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TP = ROOT / "06_analysis" / "02_control" / "touch_phase"
VD = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "verdict"


def load(name: str) -> dict:
    return {json.loads(l)["job"]["case"]: json.loads(l) for l in (TP / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()}


c4 = load("rows_C4G1")
k1 = load("krows_C4G1K1")
out = []
for case, rec in k1.items():
    if "error" in rec:
        print(case, rec["error"][:200])
        continue
    base = json.loads((VD / f"OFF_{case}.json").read_text(encoding="utf-8"))
    other = c4.get(case, {})
    warn = lambda events: sorted({e[1].split(":")[0] for e in events if e[1].startswith(("WARN", "FAULT"))})
    row = {"case": case, "same_as_C4G1": rec["commands_sha256"] == other.get("commands_sha256"),
           "phase": rec["final_phase"], "class": rec.get("harness_class"), "class_base": base.get("harness_class"),
           "fail": rec.get("failed_rows"), "fail_base": base.get("failed_rows"),
           "Fmin_base": base["values"]["forces"]["after_liftoff"]["min_kN"],
           "Fmin_C4G1": other.get("forces", {}).get("after_liftoff", {}).get("min_kN"),
           "Fmin": rec["forces"]["after_liftoff"]["min_kN"],
           "ready_base": base["values"]["times"]["t_first_ready_s"], "ready": rec["times"]["t_first_ready_s"],
           "held": rec["trim"].get("n_retrigger_held", 0), "stroke": round(rec["max_stroke_reading_mm"], 1),
           "stroke_base": round(base["max_motor_stroke_reading_mm"], 1), "new_warn": [w for w in warn(rec["events"]) if w not in warn(base["events"])]}
    if rec.get("event_output"):
        row["adj"] = rec["event_output"]["adj_min_F_in_W_kN"]
        row["adj_base"] = base["event_output"]["adj_min_F_in_W_kN"]
        row["lift"] = rec["event_output"]["pair_union_s"]
    out.append(row)
    print(row)
(TP / "krows_C4G1K1_compare.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("same as C4G1:", sum(r["same_as_C4G1"] for r in out), "of", len(out))
