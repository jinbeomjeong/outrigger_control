"""Criteria revision 8 7.2: the 22 VB lines rerun with ③ on against the stored ③-off lines.

Reads ``main.jsonl`` (stored, r5, ③ off) and ``p3_hash.jsonl`` (``run_v5.py p3_hash``) and
checks per job:

1. ``commands_sha256`` equal (64 characters);
2. ``event_names`` and ``events`` equal;
3. ``hydraulics_record`` equal apart from the ③ keys (:data:`P3_RECORD_KEYS`) and the M2 law
   rule text (:data:`TEXT_ONLY_PATHS`, a meta string corrected on 2026-11-08 without a
   behaviour change);
4. ``extend_bound_check`` present and ext_moving ``sum(breach_reads)`` = 0 (J-P3); a run
   without any rod-side reading (T4h ``rod_pressure_Pa`` all NaN, the head-only harness rows)
   has no record by construction and is reported as ``no_rod_reading`` (not judged; revision 8
   3.2 reads a missing record as a setting defect, which does not fit these rows: reported);
5. the rerun has ``controller_tag`` ``final_C4G2_P3`` and its T4h record the two-pressure
   rule ``tracked_bound`` with bound revision 4.

Read only. Exit code 0 = all 22 pass, 1 = a check failed, 2 = input missing.

Usage (dynamics-dev or python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/p3_hash_check.py <out_json>
      [--stored main.jsonl] [--rerun p3_hash.jsonl] [--t4h-dir p3_hash/t4h]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V5_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
P3_RECORD_KEYS = ("extend_bound_check", "tension_truth")
"""``hydraulics_record`` keys the ③ option adds or fills (left out of check 3)."""
TEXT_ONLY_PATHS = ("m2_law.rule",)
"""Meta text corrected without a behaviour change (``rod_release`` r5 anchor, 2026-11-08)."""
EXPECTED_TAG = "final_C4G2_P3"
EXPECTED_RULE = "tracked_bound"
EXPECTED_REVISION = 4
EXPECTED_JOBS = 22
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k not in RUNTIME_JOB_KEYS},
                      sort_keys=True)


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def first_vb_lines(stored: list[dict]) -> dict[str, dict]:
    """Job key -> the first VB line per case (``run_v5.p3_hash_jobs`` rule)."""
    seen_cases: set[str] = set()
    out = {}
    for record in stored:
        job = record["job"]
        if "error" in record or job["setting"] != "VB" or job["case"] in seen_cases:
            continue
        seen_cases.add(job["case"])
        out[job_key(job)] = record
    return out


def differing_paths(before, after, path: str = "") -> list[str]:
    """Dotted paths where two JSON values differ."""
    if isinstance(before, dict) and isinstance(after, dict):
        paths = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else str(key)
            paths += differing_paths(before.get(key), after.get(key), child)
        return paths
    return [] if before == after else [path]


def _t4h_meta(t4h_dir: Path, file_name: str | None) -> tuple[dict | None, bool | None]:
    """(T4h meta, whether the run had a rod-side reading) of a rerun; (None, None) without it."""
    if file_name is None or not (t4h_dir / file_name).is_file():
        return None, None
    import numpy as np

    with np.load(t4h_dir / file_name, allow_pickle=False) as data:
        has_rod = bool(np.isfinite(data["rod_pressure_Pa"]).any())
        return json.loads(str(data["meta_json"])), has_rod


def check_pair(stored: dict, rerun: dict, t4h_dir: Path) -> dict:
    """The five checks of one job (module docstring)."""
    stored_record = {k: v for k, v in (stored.get("hydraulics_record") or {}).items()
                     if k not in P3_RECORD_KEYS}
    rerun_record = {k: v for k, v in (rerun.get("hydraulics_record") or {}).items()
                    if k not in P3_RECORD_KEYS}
    record_paths = differing_paths(stored_record, rerun_record)
    bound_check = (rerun.get("hydraulics_record") or {}).get("extend_bound_check")
    breach_reads = None if bound_check is None else sum(bound_check["breach_reads"])
    meta, has_rod = _t4h_meta(t4h_dir, rerun.get("t4h_file"))
    meta = meta or {}
    settings = meta.get("two_pressure_settings") or {}
    # J-P3 (extend_start_bound.j_p3_judgement): no record is expected only without a rod
    # reading (the ③ tracker runs on rod readings; head-only harness rows)
    if bound_check is None:
        j_p3 = "no_rod_reading" if has_rod is False else "missing_record"
    else:
        j_p3 = "pass" if breach_reads == 0 else "H-7"
    revision = (settings.get("extend_start_bound") or {}).get("revision")
    checks = {
        "1_commands_equal": stored["commands_sha256"] == rerun["commands_sha256"],
        "2_events_equal": (stored.get("event_names") == rerun.get("event_names")
                           and stored.get("events") == rerun.get("events")),
        "3_record_equal_apart_from_p3": all(p in TEXT_ONLY_PATHS for p in record_paths),
        "4_ext_moving_breach_zero": j_p3 in ("pass", "no_rod_reading"),
        "5_p3_on": (rerun.get("controller_tag") == EXPECTED_TAG
                    and settings.get("extend_start_rule") == EXPECTED_RULE
                    and revision == EXPECTED_REVISION)}
    return {"job": rerun["job"], "pass": all(checks.values()), "checks": checks,
            "record_differing_paths": record_paths,
            "ext_moving_breach_reads": breach_reads, "j_p3": j_p3, "has_rod_reading": has_rod,
            "margin_used_reads": None if bound_check is None
            else sum(bound_check["margin_used_reads"]),
            "commands_sha256": rerun["commands_sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json")
    parser.add_argument("--stored", default=str(V5_DIR / "main.jsonl"))
    parser.add_argument("--rerun", default=str(V5_DIR / "p3_hash.jsonl"))
    parser.add_argument("--t4h-dir", default=str(V5_DIR / "p3_hash" / "t4h"))
    args = parser.parse_args()
    stored_path, rerun_path = Path(args.stored), Path(args.rerun)
    if not stored_path.is_file() or not rerun_path.is_file():
        print(json.dumps({"error": "input missing"}))
        return 2
    stored = first_vb_lines(read_lines(stored_path))
    reruns = [r for r in read_lines(rerun_path) if "error" not in r]
    errors = [r["job"] for r in read_lines(rerun_path) if "error" in r]
    rows = [check_pair(stored[job_key(r["job"])], r, Path(args.t4h_dir)) for r in reruns
            if job_key(r["job"]) in stored]
    unmatched = [r["job"] for r in reruns if job_key(r["job"]) not in stored]
    passed = (len(rows) == EXPECTED_JOBS and all(row["pass"] for row in rows)
              and not errors and not unmatched)
    report = {"rule": "criteria revision 8 7.2 (checks 1-5 of the module docstring)",
              "jobs": len(rows), "expected_jobs": EXPECTED_JOBS, "passed": passed,
              "failed_jobs": [row["job"] for row in rows if not row["pass"]],
              "run_errors": errors, "unmatched": unmatched,
              "j_p3_counts": {status: sum(row["j_p3"] == status for row in rows)
                              for status in ("pass", "no_rod_reading", "H-7", "missing_record")},
              "text_only_paths_seen": sorted({p for row in rows
                                              for p in row["record_differing_paths"]}),
              "rows": rows}
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("jobs", "passed", "failed_jobs", "run_errors",
                                             "j_p3_counts")}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
