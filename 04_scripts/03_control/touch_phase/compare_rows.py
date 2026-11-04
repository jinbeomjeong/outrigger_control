"""Candidate rows against the stored flow-off verdict rows, same harness, same case (no phase sweep).

Usage: python -I compare_rows.py <candidate>. Output: rows_<candidate>_compare.json and a table on stdout.
Values: minimum force after lift-off kN (true cylinder force), READY s, TOUCH end s, largest stroke mm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TP = ROOT / "06_analysis" / "02_control" / "touch_phase"
VD = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "verdict"


def warn_set(events) -> list[str]:
    return sorted({e[1] for e in events if e[1].startswith(("WARN", "FAULT"))})


def main() -> None:
    cand = sys.argv[1]
    out = []
    for line in (TP / f"rows_{cand}.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        case = rec["job"]["case"]
        if "error" in rec:
            print(case, "ERROR", rec["error"][:200])
            out.append({"case": case, "error": rec["error"]})
            continue
        base = json.loads((VD / f"OFF_{case}.json").read_text(encoding="utf-8"))
        bv, cv = base["values"], rec
        fb, fc = bv["forces"]["after_liftoff"]["min_kN"], rec["forces"]["after_liftoff"]["min_kN"]
        tb, tc = bv["times"]["t_first_ready_s"], rec["times"]["t_first_ready_s"]
        row = {"case": case, "phase": (base["final_phase"], rec["final_phase"]),
               "F_min_base": fb, "F_min_cand": fc, "ready_base": tb, "ready_cand": tc,
               "dready": None if tb is None or tc is None else round(tc - tb, 2),
               "guard_base": bv.get("guard_active_s"), "guard_cand": rec.get("guard_active_s"),
               "fail_base": base.get("failed_rows"), "fail_cand": rec.get("failed_rows"),
               "class_base": base.get("harness_class"), "class_cand": rec.get("harness_class"),
               "new_warn": [w for w in warn_set(rec["events"]) if w not in warn_set(base["events"])],
               "gone_warn": [w for w in warn_set(base["events"]) if w not in warn_set(rec["events"])],
               "D_hat": rec["trim"].get("D_hat_kN"), "delta_tau": rec["trim"].get("delta_tau_mm"),
               "stroke_cand": max(rec["stroke_max_mm"]), "stroke_read_base": base.get("max_motor_stroke_reading_mm"),
               "stroke_read_cand": rec.get("max_stroke_reading_mm"),
               "rut": (base.get("rut_ready_mm"), rec.get("rut_ready_mm"))}
        if rec.get("event_output"):
            row["adj_base"] = base["event_output"]["adj_min_F_in_W_kN"]
            row["adj_cand"] = rec["event_output"]["adj_min_F_in_W_kN"]
            row["lift_base"] = base["event_output"]["pair_union_s"]
            row["lift_cand"] = rec["event_output"]["pair_union_s"]
            row["after_W"] = (base["event_output"]["min_F_after_W_kN"], rec["event_output"]["min_F_after_W_kN"])
        out.append(row)
        print(case, row["phase"], "Fmin", fb, "->", fc, "ready", tb, "->", tc, "class", row["class_base"], row["class_cand"],
              "fail", row["fail_base"], row["fail_cand"], "new", row["new_warn"], "gone", row["gone_warn"],
              "dT", row["delta_tau"], "stroke", row["stroke_read_base"], row["stroke_read_cand"], "adj", row.get("adj_base"), row.get("adj_cand"))
    (TP / f"rows_{cand}_compare.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
