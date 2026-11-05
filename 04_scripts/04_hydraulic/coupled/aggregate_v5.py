"""Values of the v5 harness runs (``run_v5.py`` lines); no verdict text (``v5_criteria.md``).

Writes ``<batch>_values.json``: one row per run (case, phase, setting, final phase, first READY,
command sign changes, M2 shift, M1c fills, lock changes, command hash), the V0 hashes against the
golden off runs (phase 0 rows that the golden set defines) and the W-2 pairs (L1 against L2 hashes).
M1c rows carry ``unit_status`` ``below_criteria_reference_only``.

Usage: python -I -B 04_scripts/04_hydraulic/coupled/aggregate_v5.py <batch> [<batch> ...]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parents[2] / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
GOLDEN_DIR = OUT_DIR / "golden_off"
UNIT_STATUS = "below_criteria_reference_only"


def _phase(job: dict) -> str:
    if job.get("twin"):
        twin = job["twin"]
        return f"{twin['level']}|{twin['leg']}|{twin['fs_kN']:g}|{job.get('offset_s')}"
    if job.get("offset_s") is not None:
        return f"offset {job['offset_s']}"
    return f"eps {job.get('eps', 0.0)}"


def _row_name(job: dict) -> str:
    return "R2ra" if job.get("decision") == "reanchor_on" else job["case"]


def value_row(record: dict) -> dict:
    """The values of one run line (spec 3.3 list, what the record holds)."""
    job = record["job"]
    out = {"row": _row_name(job), "phase": _phase(job), "setting": job["setting"]}
    if "error" in record:
        return {**out, "error": record["error"]}
    times = (record.get("values") or {}).get("times", {})
    hydraulics = record.get("hydraulics_record") or {}
    out.update(final_phase=record["final_phase"], t_first_ready_s=times.get("t_first_ready_s"),
               n_rev=record["command_stats"]["n_rev"],
               warn_fault={k: v for k, v in record["event_names"].items()
                           if k.startswith(("WARN", "FAULT"))},
               m2_shift_total_mm=hydraulics.get("m2_shift_total_mm"),
               lock_changes=len(hydraulics.get("lock_events", [])),
               commands_sha256=record["commands_sha256"])
    if "check_delay" in hydraulics:
        out["m1c_n_fills"] = hydraulics["check_delay"]["n_fills"]
        out["unit_status"] = UNIT_STATUS
    if record.get("event_output"):
        out["t_ready_back_s"] = record["event_output"].get("t_ready_back_s")
    return out


def golden_check(rows: list[dict]) -> list[dict]:
    """V0 phase-0 rows of cases in the golden set: hash equal to ``golden_off/OFF_<case>.json``."""
    checks = []
    for row in rows:
        if row["setting"] != "V0" or row["phase"] not in ("eps 0.0", "offset 0.0") \
                or "error" in row:
            continue
        golden = GOLDEN_DIR / f"OFF_{row['row']}.json"
        if row["row"] == "R2ra" or not golden.exists():
            continue
        stored = json.loads(golden.read_text(encoding="utf-8"))["commands_sha256"]
        checks.append({"row": row["row"], "phase": row["phase"],
                       "equal": stored == row["commands_sha256"]})
    return checks


def w2_pairs(rows: list[dict]) -> list[dict]:
    by_key = defaultdict(dict)
    for row in rows:
        if row["setting"] in ("L1", "L2") and "error" not in row:
            by_key[(row["row"], row["phase"])][row["setting"]] = row["commands_sha256"]
    return [{"row": key[0], "phase": key[1], "equal": pair["L1"] == pair["L2"]}
            for key, pair in sorted(by_key.items()) if len(pair) == 2]


def main() -> None:
    for batch in sys.argv[1:]:
        lines = (OUT_DIR / f"{batch}.jsonl").read_text(encoding="utf-8").splitlines()
        rows = [value_row(json.loads(line)) for line in lines]
        report = {"batch": batch, "runs": len(rows),
                  "errors": sum("error" in row for row in rows),
                  "golden_v0": golden_check(rows), "w2": w2_pairs(rows), "rows": rows}
        out = OUT_DIR / f"{batch}_values.json"
        out.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("batch", "runs", "errors", "golden_v0", "w2")}))


if __name__ == "__main__":
    main()
