"""Compare a candidate run of the study A / r67 event screens with the "current" run (spec 427.11
stage 1 / 429.5 for the screens outside ``s9_slope_fix_candidates.py``).

Inputs: two result JSONs of ``s9_soil_event_screen.py`` (``R426A_CANDIDATE``) or
``s8/r67_g1_screen.py`` (``R67_CANDIDATE``), the "current" run first. Runs are paired by job key
and branch (study A: timing + event; r67: event + offset). Per run: pass before / after, the
command hash (prefix + branch) equal or not, which candidate parts acted (``candidate_record``),
READY return delta, crawler maximum after the event (study A). Summary: n, acted, idle runs
with a changed hash (the 427.11 identity rule), pass -> fail, fail -> pass, part counts.

Usage (standard library only):
  python -I screen_candidate_compare.py <current.json> <candidate.json> --out <compare.json>
Writes ``<compare>.json`` (summary + rows) and ``<compare>_rows.csv``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def _branch_key(job_key: str, run: dict) -> str:
    if "timing" in run:  # study A
        return f"{job_key}|{run['timing']}|{run['event']}"
    return f"{job_key}|{run['event']}|{run.get('offset_s')}"


def _run_hash(run: dict) -> str | None:
    """Study A: prefix + branch hashes combined; r67: the stored prefix + branch hash."""
    branch_hash = run.get("commands_sha256")
    prefix_hash = run.get("prefix_commands_sha256")
    if branch_hash is None:
        return None
    if prefix_hash is None:  # r67 hashes already cover the prefix
        return branch_hash
    return hashlib.sha256(f"{prefix_hash}:{branch_hash}".encode()).hexdigest()


def index_runs(payload: dict) -> dict[str, dict]:
    """Branch key -> {run, hash, error} of one screen result file."""
    out = {}
    for job in payload["results"]:
        if "error" in job:
            out[f"{job['key']}|ERROR"] = {"error": job["error"]}
            continue
        for run in job.get("runs", []):
            out[_branch_key(job["key"], run)] = {"run": run, "hash": _run_hash(run)}
    return out


def _ready_back(run: dict) -> float | None:
    return run.get("t_ready_back_s")


def compare_run(key: str, before: dict, after: dict) -> dict:
    run_before, run_after = before["run"], after["run"]
    record = run_after.get("candidate_record") or {}
    parts = record.get("acted_parts") or []
    ready_before, ready_after = _ready_back(run_before), _ready_back(run_after)
    crawler_before = (run_before.get("crawler") or {}).get("max_after_event_kN")
    crawler_after = (run_after.get("crawler") or {}).get("max_after_event_kN")
    return {
        "key": key, "pass_before": run_before.get("pass"), "pass_after": run_after.get("pass"),
        "hash_same": before["hash"] is not None and before["hash"] == after["hash"],
        "acted": bool(record.get("acted")), "acted_parts": "+".join(parts),
        "failed_after": ";".join(k for k, v in (run_after.get("gates") or {}).items() if not v),
        "d_ready_back_s": None if ready_before is None or ready_after is None
        else round(ready_after - ready_before, 3),
        "crawler_max_kN_before": crawler_before, "crawler_max_kN_after": crawler_after,
        "flags_after": ";".join(run_after.get("flags") or []),
    }


def summarize(rows: list[dict], missing: list[str]) -> dict:
    summary = {"n": len(rows), "missing_or_error": missing, "acted": 0, "hash_same": 0,
               "idle_hash_differs": 0, "pass_to_fail": 0, "fail_to_pass": 0}
    for row in rows:
        summary["acted"] += row["acted"]
        summary["hash_same"] += row["hash_same"]
        summary["idle_hash_differs"] += not row["acted"] and not row["hash_same"]
        summary["pass_to_fail"] += bool(row["pass_before"] and not row["pass_after"])
        summary["fail_to_pass"] += bool(not row["pass_before"] and row["pass_after"])
        for part in filter(None, row["acted_parts"].split("+")):
            summary[f"acted_{part}"] = summary.get(f"acted_{part}", 0) + 1
    return summary


def compare_files(current_path: Path, candidate_path: Path) -> dict:
    before = index_runs(json.loads(current_path.read_text(encoding="utf-8")))
    after = index_runs(json.loads(candidate_path.read_text(encoding="utf-8")))
    rows, missing = [], []
    for key in sorted(after):  # a candidate run may cover a subset (spec 427.11 stage 2)
        if "run" not in before.get(key, {}) or "run" not in after.get(key, {}):
            missing.append(key)
            continue
        rows.append(compare_run(key, before[key], after[key]))
    return {"inputs": [str(current_path), str(candidate_path)],
            "summary": summarize(rows, missing), "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("current", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare_files(args.current, args.candidate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    if result["rows"]:
        csv_path = args.out.with_name(args.out.stem + "_rows.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result["rows"][0]))
            writer.writeheader()
            writer.writerows(result["rows"])
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    main()
