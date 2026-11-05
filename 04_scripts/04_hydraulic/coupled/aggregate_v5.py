"""Values of the v5 harness runs (``run_v5.py`` lines); no verdict text (``v5_criteria.md``).

Writes ``<batch>_values.json``: one row per run (case, phase, setting, final phase, first READY,
command sign changes, M2 shift, M1c fills, lock changes, command hash), the V0 hashes against the
golden off runs (phase 0 rows that the golden set defines) and the W-2 pairs (L1 against L2 hashes).
M1c rows carry ``unit_status`` ``below_criteria_reference_only``. Batch ``item8`` adds
``item8_order`` (criteria 13.1 (1)) from its rows and the R6 / R8 / R9 rows of ``main``. Every
batch gets ``ready`` (criteria 7: S1 .. S5, S7 first READY <= 100 s, event rows back in READY
<= 60 s, S8 no READY, rigid rows FLAG over 90 / 120 s), ``s8_stop`` (criteria 6 values) and
``event_force`` (criteria 3.1, ⑦: after-window 1 ms minimum, trailing 0.5 s mean, FLAG_E3_1ms).
Batch ``pressure_only`` adds ``pressure_only`` (criteria 13.4, ⑥): the pressure-only run and the
combined run of ``main`` side by side (after-window 1 ms minimum, time below F_min, misses of
the lower estimate), each entry with ``unit_status``.

Usage: python -I -B 04_scripts/04_hydraulic/coupled/aggregate_v5.py <batch> [<batch> ...]
"""
from __future__ import annotations

import itertools
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
# Criteria 7 READY limits (s9_soil_slope.ready_limit_s is not used: S7 is judged at 100 s)
SOIL_READY_LIMIT_S = 100.0
SOIL_READY_ROWS = ("S1", "S2", "S3", "S4", "S5", "S7")
RIGID_FLAT_READY_FLAG_S = 90.0
RIGID_SLOPE_READY_FLAG_S = 120.0
EVENT_RETURN_LIMIT_S = 60.0
NO_READY_ROWS = ("S8",)
"""Criteria 7: S8 must not reach READY (``stroke_limited_stop``)."""


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
    if record.get("contact_judge"):  # criteria 13.4 (⑥) runs: every row is reference only
        out["contact_judge"] = record["contact_judge"]
        out["unit_status"] = record.get("unit_status", UNIT_STATUS)
    if record.get("event_output"):
        out["t_ready_back_s"] = record["event_output"].get("t_ready_back_s")
        if record["event_output"].get("after_window_force"):  # criteria 3.1 (⑦) values
            out["after_window_force"] = record["event_output"]["after_window_force"]
        for key in ("lower_bound_miss", "ref_10hz_episodes"):  # criteria 13.4 (⑥) values
            if record["event_output"].get(key):
                out[key] = record["event_output"][key]
    if record.get("soil_stop_crawler"):
        out["soil_stop_crawler"] = record["soil_stop_crawler"]
    if record.get("overlap_found"):
        out["overlap_found"] = record["overlap_found"]
    if "lock_window_alignment" in record:
        out["lock_window_alignment"] = record["lock_window_alignment"]
    return out


def _is_flat_rigid_row(row_name: str) -> bool:
    if str(HERE) not in sys.path:  # ``-I`` leaves the script folder off the path
        sys.path.insert(0, str(HERE))
    import verdict_cases

    case_id = "R2" if row_name == "R2ra" else row_name
    twin = verdict_cases.CASES[case_id].twin
    return twin.roll_deg == 0.0 and twin.pitch_deg == 0.0


def ready_entry(row: dict) -> dict:
    """Criteria 7 READY item of one value row: the value, its limit and whether it holds.

    ``judged``: S1 .. S5, S7 first READY <= 100 s; event rows (with ``t_ready_back_s``) back in
    READY <= 60 s; S8 no READY. ``record``: rigid rows, first READY over 90 s (flat) / 120 s
    (slope) or none is a FLAG.
    """
    name, first_ready = row["row"], row.get("t_first_ready_s")
    entry = {"row": name, "phase": row["phase"], "setting": row["setting"]}
    if "t_ready_back_s" in row:
        back = row["t_ready_back_s"]
        return {**entry, "role": "judged", "item": "return", "value_s": back,
                "limit_s": EVENT_RETURN_LIMIT_S,
                "within": back is not None and back <= EVENT_RETURN_LIMIT_S}
    if name in SOIL_READY_ROWS:
        return {**entry, "role": "judged", "item": "first_ready", "value_s": first_ready,
                "limit_s": SOIL_READY_LIMIT_S,
                "within": first_ready is not None and first_ready <= SOIL_READY_LIMIT_S}
    if name in NO_READY_ROWS:
        return {**entry, "role": "judged", "item": "no_ready", "value_s": first_ready,
                "limit_s": None, "within": first_ready is None}
    limit_s = RIGID_FLAT_READY_FLAG_S if _is_flat_rigid_row(name) else RIGID_SLOPE_READY_FLAG_S
    return {**entry, "role": "record", "item": "first_ready", "value_s": first_ready,
            "limit_s": limit_s, "flag": first_ready is None or first_ready > limit_s}


def ready_table(rows: list[dict]) -> list[dict]:
    """Criteria 7 READY table (and the J5 return of the event rows) of the runs without error."""
    return [ready_entry(row) for row in rows if "error" not in row]


def event_force_table(rows: list[dict]) -> list[dict]:
    """Criteria 3.1 (⑦) values of the event runs: 1 ms minimum after the window, the summed
    and longest time below F_min, the trailing 0.5 s mean minimum, lift after the window and
    ``FLAG_E3_1ms`` (harness rigid events keep the 1 ms E-3; the 0.5 s mean is recorded)."""
    return [{"row": row["row"], "phase": row["phase"], "setting": row["setting"],
             **row["after_window_force"]}
            for row in rows if row.get("after_window_force")]


JUDGE_FORCE_KEYS = ("min_1ms_kN", "min_1ms_leg", "below_f_min_ms_sum", "below_f_min_ms_longest")
JUDGE_MISS_KEYS = ("miss_intervals", "miss_ms_sum", "miss_ms_longest")
REF_10HZ_KEYS = ("episodes", "missed", "late")
"""Criteria 13.4 reference value (10 Hz J_P style) in the table; not judged."""


def _judge_values(row: dict | None) -> dict | None:
    """After-window force and miss values of one run (criteria 13.4 record), None if absent."""
    if row is None or "error" in row:
        return None
    force = row.get("after_window_force") or {}
    miss = row.get("lower_bound_miss") or {}
    reference = row.get("ref_10hz_episodes") or {}
    return {"commands_sha256": row["commands_sha256"],
            **{key: force.get(key) for key in JUDGE_FORCE_KEYS},
            **{key: miss.get(key) for key in JUDGE_MISS_KEYS},
            "ref_10hz_episodes": {key: reference.get(key) for key in REF_10HZ_KEYS}}


def pressure_only_table(rows: list[dict], combined_rows: list[dict]) -> list[dict]:
    """Criteria 13.4 (⑥): per row, phase and setting the pressure-only run next to the combined
    run of ``main`` (None until ``main`` has it). Every entry carries ``unit_status``."""
    combined = {(row["row"], row["phase"], row["setting"]): row for row in combined_rows
                if not row.get("contact_judge")}
    table = []
    for row in rows:
        if not row.get("contact_judge"):
            continue
        key = (row["row"], row["phase"], row["setting"])
        table.append({"row": key[0], "phase": key[1], "setting": key[2],
                      "unit_status": row.get("unit_status", UNIT_STATUS),
                      row["contact_judge"].lower(): _judge_values(row),
                      "combined": _judge_values(combined.get(key))})
    return table


LOCK_WINDOW_GATE_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")
"""Criteria J11 / L-e: n_late of the fallback legs gates these; L1 and the rest are records."""


def _lock_window_side(alignments: list[dict], *, fallback_only: bool) -> dict:
    late_key = "n_late_fallback_by_leg" if fallback_only else "n_late_by_leg"
    late_per_run = [sum(a[late_key].values()) for a in alignments]
    if fallback_only:
        margins = [a["margin_min_s_fallback"] for a in alignments
                   if a.get("margin_min_s_fallback") is not None]
    else:
        margins = [margin for a in alignments for margin in a["margin_min_s_by_leg"].values()
                   if margin is not None]
    return {"late_stretches": sum(late_per_run),
            "runs_with_late": sum(count > 0 for count in late_per_run),
            "margin_min_s": min(margins) if margins else None}


def lock_window_table(rows: list[dict]) -> dict:
    """Criteria J11 per setting: stretches, late stretches, runs with n_late > 0 and the least
    margin, all legs and fallback legs apart."""
    by_setting = defaultdict(list)
    skipped = defaultdict(int)
    for row in rows:
        alignment = row.get("lock_window_alignment")
        if alignment is None:
            continue
        if alignment.get("n_late", 0) is None:
            skipped[row["setting"]] += 1
            continue
        by_setting[row["setting"]].append(alignment)
    table = {}
    for setting, alignments in sorted(by_setting.items()):
        table[setting] = {
            "role": "gate" if setting in LOCK_WINDOW_GATE_SETTINGS else "record",
            "runs": len(alignments), "runs_without_stretches": skipped.get(setting, 0),
            "stretches": sum(sum(a["stretches_by_leg"].values()) for a in alignments),
            "judged": sum(sum(a["judged_by_leg"].values()) for a in alignments),
            "unlock_in_stretch": sum(a["unlock_in_stretch"] for a in alignments),
            "all_legs": _lock_window_side(alignments, fallback_only=False),
            "fallback_legs": _lock_window_side(alignments, fallback_only=True),
            "n_late_fallback": sum(a["n_late_fallback"] for a in alignments)}
    return table


def s8_stop_table(rows: list[dict]) -> list[dict]:
    """Criteria 6 S8 values per run: crawler at the stop (1 ms), 1 s maximum before it, +-0.1 s
    range, maximum after it and the clause margins [kN]."""
    return [{"phase": row["phase"], "setting": row["setting"], **row["soil_stop_crawler"]}
            for row in rows if row["row"] in NO_READY_ROWS and row.get("soil_stop_crawler")]


def golden_check(rows: list[dict]) -> list[dict]:
    """V0 phase-0 rows of cases in the golden set: hash equal to ``golden_off/OFF_<case>.json``."""
    checks = []
    for row in rows:
        if row["setting"] != "V0" or row["phase"] not in ("eps 0.0", "offset 0.0") \
                or "error" in row or row.get("contact_judge"):  # golden runs: screen judge
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
    for lower, upper in itertools.pairwise(summaries):
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
                  "golden_v0": golden_check(rows), "w2": w2_pairs(rows), "rows": rows,
                  "ready": ready_table(rows), "s8_stop": s8_stop_table(rows),
                  "event_force": event_force_table(rows),
                  "lock_window": lock_window_table(rows)}
        if batch == "item8":
            regression = [row for row in _value_rows("main") if row["row"] in ITEM8_LEVELS]
            report["item8_order"] = item8_order(rows + regression)
        if batch == "pressure_only":
            main_path = OUT_DIR / "main.jsonl"
            combined = _value_rows("main") if main_path.exists() else []
            report["pressure_only"] = pressure_only_table(rows, combined)
        out = OUT_DIR / f"{batch}_values.json"
        out.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("batch", "runs", "errors", "golden_v0", "w2")}))


if __name__ == "__main__":
    main()
