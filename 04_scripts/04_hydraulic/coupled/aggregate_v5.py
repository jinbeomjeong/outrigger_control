"""Values of the v5 harness runs (``run_v5.py`` lines); no verdict text (``v5_criteria.md``).

Writes ``<batch>_values.json``: one row per run (case, phase, setting, final phase, first READY,
command sign changes, M2 shift, M1c fills, lock changes, command hash), the V0 hashes against the
golden off runs (phase 0 rows that the golden set defines) and the W-2 pairs (L1 against L2 hashes).
M1c rows carry ``unit_status`` ``below_criteria_reference_only``. Batch ``item8`` adds
``item8_order`` (criteria 13.1 (1)) from its rows and the R6 / R8 / R9 rows of ``main``.

Usage: python -I -B 04_scripts/04_hydraulic/coupled/aggregate_v5.py <batch> [<batch> ...]
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parents[2] / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
GOLDEN_DIR = OUT_DIR / "golden_off"
UNIT_STATUS = "below_criteria_reference_only"
ITEM8_LEVELS = {"R6": "top", "R8": "middle", "R9": "bottom"}
ITEM8_SETTINGS = ("V0", "VB")
ITEM8_PHASES = ("eps 0.0", "eps 0.001", "eps 0.002", "eps 0.003")


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
    after_liftoff = ((record.get("values") or {}).get("forces") or {}).get("after_liftoff")
    out.update(final_phase=record["final_phase"], t_first_ready_s=times.get("t_first_ready_s"),
               min_force_after_liftoff_kN=None if after_liftoff is None
               else after_liftoff["min_kN"],
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


def _level_summary(rows: list[dict], row_name: str, setting: str) -> dict:
    """Median and range of the minimum force after the lift-off over the phases of one row."""
    values = sorted(row["min_force_after_liftoff_kN"] for row in rows
                    if row["row"] == row_name and row["setting"] == setting
                    and "error" not in row and row.get("min_force_after_liftoff_kN") is not None)
    phases = sorted(row["phase"] for row in rows
                    if row["row"] == row_name and row["setting"] == setting and "error" not in row)
    if not values:
        return {"phases": phases, "median_kN": None, "range_kN": None}
    return {"phases": phases, "median_kN": float(statistics.median(values)),
            "range_kN": [values[0], values[-1]]}


def _is_ordered_and_apart(summaries: list[dict]) -> bool:
    """Medians strictly rising and each range wholly below the next one."""
    for lower, upper in zip(summaries, summaries[1:]):
        if lower["median_kN"] >= upper["median_kN"]:
            return False
        if lower["range_kN"][1] >= upper["range_kN"][0]:
            return False
    return True


def item8_order(rows: list[dict]) -> dict:
    """Criteria 13.1 (1): order of the top / middle / bottom minimum force per setting.

    ``kept``: m_top < m_middle < m_bottom and neighbouring ranges apart; ``reversed``: the
    reverse order with ranges apart; ``undetermined`` otherwise or with a phase missing. The
    criteria reads ``reversed`` as a failure on VB only while V0 is ``kept``.
    """
    out = {}
    for setting in ITEM8_SETTINGS:
        levels = {level: _level_summary(rows, row_name, setting)
                  for row_name, level in ITEM8_LEVELS.items()}
        summaries = list(levels.values())
        complete = all(len(s["phases"]) == len(ITEM8_PHASES) and s["median_kN"] is not None
                       for s in summaries)
        if not complete:
            order = "undetermined"
        elif _is_ordered_and_apart(summaries):
            order = "kept"
        elif _is_ordered_and_apart(summaries[::-1]):
            order = "reversed"
        else:
            order = "undetermined"
        out[setting] = {"levels": levels, "order": order}
    return out


def _value_rows(batch: str) -> list[dict]:
    lines = (OUT_DIR / f"{batch}.jsonl").read_text(encoding="utf-8").splitlines()
    return [value_row(json.loads(line)) for line in lines]


def main() -> None:
    for batch in sys.argv[1:]:
        rows = _value_rows(batch)
        report = {"batch": batch, "runs": len(rows),
                  "errors": sum("error" in row for row in rows),
                  "golden_v0": golden_check(rows), "w2": w2_pairs(rows), "rows": rows}
        if batch == "item8":
            regression = [row for row in _value_rows("main") if row["row"] in ITEM8_LEVELS]
            report["item8_order"] = item8_order(rows + regression)
        out = OUT_DIR / f"{batch}_values.json"
        out.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("batch", "runs", "errors", "golden_v0", "w2")}))


if __name__ == "__main__":
    main()
