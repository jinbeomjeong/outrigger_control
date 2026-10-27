"""Spec rev. 74: V-3 runs changed by P-S8-30 - judgement quantities old (07_results/S9/v3) vs new, per changed id.

Quantities (s9 harness records): READY time, final phase, crawler load after READY / re-contacts, min true F after the
crawler lift-off and its margin, attitude max after lift-off / after READY / at the end, clearance at READY (true /
estimate), max motor stroke, LOC event time, re-approach / re-level / warning counts, INFO_LIFT_PAUSED events.

Usage: python -I r75_v3_diff.py <out_json> <old dir> <new dir> [set ...]   (sets: rigid soil sensor beta)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KEYS = ("t_ready_s", "final_phase", "crawler_N_max_after_ready", "n_crawler_recontact", "min_true_Fcyl_after_off_kN",
        "min_margin_after_off_kN", "att_max_after_off_deg", "att_after_ready_max_deg", "clear_true_ready_mm",
        "clear_est_ready_mm", "max_motor_stroke_mm", "n_reapproach", "n_relevel", "n_warn", "t_crawler_off_first_s")


def ev_time(r, name):
    for e in r.get("events", []):
        t, n = e.split(" ", 1)
        if n.startswith(name):
            return float(t)
    return None


def main():
    out, old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sets = sys.argv[4:] or ["rigid", "soil", "sensor", "beta"]
    res = {"script": "04_scripts/03_control/s8/r75_v3_diff.py", "old": str(old_dir), "new": str(new_dir), "sets": {}}
    for s in sets:
        old = {r["id"]: r for r in json.loads((old_dir / f"{s}.json").read_text(encoding="utf-8"))["runs"]}
        new = {r["id"]: r for r in json.loads((new_dir / f"{s}.json").read_text(encoding="utf-8"))["runs"]}
        changed = []
        for k, n in new.items():
            o = old.get(k)
            if o is None or o.get("commands_sha256") == n.get("commands_sha256"):
                continue
            row = {"id": k}
            for q in KEYS:
                a, b = o.get(q), n.get(q)
                row[q] = [a, b] if not isinstance(a, float) else [round(a, 3), None if b is None else round(b, 3)]
            row["att_end_deg"] = [o.get("att_end_deg"), n.get("att_end_deg")]
            row["t_loc_s"] = [ev_time(o, "crawler_liftoff_confirmed"), ev_time(n, "crawler_liftoff_confirmed")]
            row["pauses"] = [e for e in n.get("events", []) if "INFO_LIFT_PAUSED" in e]
            changed.append(row)
        res["sets"][s] = {"n_old": len(old), "n_new": len(new), "n_changed": len(changed), "changed": changed}
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for s, v in res["sets"].items():
        print(s, "changed", v["n_changed"], "/", v["n_new"])
        for r in v["changed"]:
            print(" ", r["id"], "READY", r["t_ready_s"], "phase", r["final_phase"], "minF", r["min_true_Fcyl_after_off_kN"],
                  "att_off", r["att_max_after_off_deg"], "att_end", r["att_end_deg"], "cr_after_ready",
                  r["crawler_N_max_after_ready"], "recontact", r["n_crawler_recontact"], "clear", r["clear_true_ready_mm"],
                  "stroke", r["max_motor_stroke_mm"], "LOC", r["t_loc_s"], "off", r["t_crawler_off_first_s"],
                  "reapp", r["n_reapproach"], "warn", r["n_warn"], r["pauses"])


if __name__ == "__main__":
    main()
