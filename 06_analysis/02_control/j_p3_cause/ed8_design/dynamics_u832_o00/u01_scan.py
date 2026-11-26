"""Summarise run_v5 jsonl lines (edition 6 / 7 stored outputs) into one CSV per run.

Usage: python -I -B u01_scan.py <out_csv> <label>=<jsonl> [<label>=<jsonl> ...]

One row per line: job identity (setting, case, twin, offset, eps), commands_sha256, the r67 event
verdict (gates, pair union, per-leg lift intervals), reapproach starts and the event time. Read only.
"""
import csv
import json
import sys

LEGS = ("FL", "FR", "RL", "RR")


def row_of(label, rec):
    job = rec.get("job", {})
    twin = job.get("twin") or {}
    ev = rec.get("event_output") or {}
    gates = ev.get("gates") or {}
    lifts = ev.get("lifts") or {}
    vals = rec.get("values") or {}
    times = vals.get("times") or {}
    out = {
        "src": label, "setting": job.get("setting"), "case": job.get("case"),
        "level": twin.get("level"), "leg": twin.get("leg"), "fs_kN": twin.get("fs_kN"),
        "event": twin.get("event"), "timing": twin.get("timing"),
        "offset_s": job.get("offset_s"), "eps": job.get("eps"),
        "error": rec.get("error"),
        "commands_sha256": rec.get("commands_sha256"),
        "final_phase": rec.get("final_phase"),
        "t_event_s": rec.get("t_event_s"),
        "t_first_ready_s": times.get("t_first_ready_s"),
        "pass": ev.get("pass"),
        "failed_gates": "|".join(k for k, v in gates.items() if not v) if gates else None,
        "pair": "+".join(ev.get("pair") or []),
        "pair_union_s": ev.get("pair_union_s"),
        "pair_last_touch_s": ev.get("pair_last_touch_s"),
        "W_end_s": ev.get("W_end_s"),
        "adj_lift_sum_W_s": ev.get("adj_lift_sum_W_s"),
        "t_ready_back_s": ev.get("t_ready_back_s"),
        "n_late_starts": ev.get("n_late_starts"),
        "reapproach_starts": json.dumps(ev.get("reapproach_starts")),
        "att_end_deg": json.dumps(ev.get("att_end_deg")),
        "max_att_change_deg": ev.get("max_att_change_deg"),
        "warnings": "|".join(ev.get("warnings") or []),
        "t4h_file": rec.get("t4h_file"),
    }
    for leg in LEGS:
        lf = lifts.get(leg) or {}
        for k in ("sum_s", "n", "first_s", "last_touch_s", "max_gap_mm"):
            out[f"{leg}_{k}"] = lf.get(k)
    return out


def main():
    out_csv = sys.argv[1]
    rows = []
    for arg in sys.argv[2:]:
        label, path = arg.split("=", 1)
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(row_of(label, json.loads(line)))
    keys = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("rows", len(rows), "->", out_csv)


if __name__ == "__main__":
    main()
