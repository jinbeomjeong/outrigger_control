"""Totals of hydraulics_record.extend_bound_check keys over the 436.8 VB / LS harness records.

Baseline for the 436.9 J-P3 definition draft (which keys are already non-zero in 436.8). Read only.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
KEYS = ("reads", "breach_reads", "margin_used_reads", "locked_reads", "locked_unpaired_reads",
        "locked_breach_reads", "locked_breach_over_tol_reads", "locked_vs_extend_bound_reads",
        "retract_reads", "retract_breach_reads")


def find_checks(obj, out):
    if isinstance(obj, dict):
        hyd = obj.get("hydraulics_record")
        if isinstance(hyd, dict) and "extend_bound_check" in hyd:
            out.append((hyd.get("extend_bound_check"), obj))
        for key, value in obj.items():
            if key == "hydraulics_record":
                continue
            find_checks(value, out)
    elif isinstance(obj, list):
        for value in obj:
            find_checks(value, out)


def tally(name, records):
    totals = defaultdict(int)
    runs = 0
    null = 0
    min_locked_gap = None
    min_retract_rows = 0
    for check, _ in records:
        if not check:
            null += 1
            continue
        runs += 1
        for key in KEYS:
            totals[key] += int(sum(check.get(key) or []))
        for value in check.get("locked_min_gap_bar") or []:
            if value is not None and (min_locked_gap is None or value < min_locked_gap):
                min_locked_gap = value
        min_retract_rows += int(sum(check.get("retract_breach_reads") or []) > 0)
    return {"file": name, "runs_with_record": runs, "null_records": null, **totals,
            "locked_min_gap_bar_min": min_locked_gap, "runs_with_retract_breach": min_retract_rows}


def main():
    sources = []
    for path in [ROOT / "h10_reuse_rerun.jsonl", ROOT / "h1_d1.jsonl", ROOT / "h9_family_F.jsonl",
                 ROOT / "h6_dg3_v4on.json.partial.jsonl", ROOT / "h8_noise_VB.json.partial.jsonl",
                 ROOT / "h8_seedext_VB.json.partial.jsonl"]:
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                find_checks(json.loads(line), records)
        sources.append(tally(path.name, records))
    for grid in sorted((ROOT / "h9_grid").glob("grid_*.json")):
        if grid.name.endswith(".identity.json"):
            continue
        records = []
        find_checks(json.loads(grid.read_text(encoding="utf-8")), records)
        sources.append(tally("h9_grid/" + grid.name, records))
    json.dump(sources, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
