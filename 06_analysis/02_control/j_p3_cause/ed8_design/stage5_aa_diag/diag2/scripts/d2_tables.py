"""Tables of diagnosis 2 (gyro supply contrast, lift-phase sweep); record only, no judgement.

Usage (python-dev):
  python.exe -I -B d2_tables.py <diag2 folder>

Reuses the row helpers of diagnosis 1 (``../scripts/d1_diag_tables.py``,
``../scripts/d1_diag_extra.py``). Writes (refuses files that exist):
  repro_check.csv                 A (switch off) vs diagnosis 1 trace-off and the stored line;
                                  B / C vs diagnosis 1 (hash, final phase, fault and GYRO events)
  first_step_period_{B..E}.csv    first head step candidate period after the lift (per leg)
  step_candidates_{B..E}.csv      every candidate from t_event - 0.3 s on
  gyro_availability_{B..E}.csv    gyro partial means and lever term per job
  compare_gyro.csv                per job: diagnosis 1 (no gyro) vs B (all) vs C (D1'' only)
  sweep_summary.csv               D + E: offset, lift phase, outcome, step period margins
Exit codes: 0 written, 2 an output exists.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIAG1_SCRIPTS = HERE.parents[1] / "scripts"
sys.path.insert(0, str(DIAG1_SCRIPTS))

import d1_diag_extra  # noqa: E402
import d1_diag_tables  # noqa: E402

SAMPLE_PERIOD_S = 0.1
STEPS = {"B": ("B_gyro_all_trace_on.jsonl", "traces_B"),
         "C": ("C_gyro_d1only_trace_on.jsonl", "traces_C"),
         "D": ("D_sweep_gyro_off_trace_on.jsonl", "traces_D"),
         "E": ("E_sweep_ext_gyro_off_trace_on.jsonl", "traces_E")}
SWEEP_STEPS = ("D", "E")
IGNORED = ("wall_s", "label", "trace", "two_pressure_file", "diag")
GYRO_WARNING = "WARN_D1_IMU_GYRO_MISSING"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()]


def _comparable(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in IGNORED}


def _events(record: dict) -> tuple[list[str], list[str]]:
    events = (record.get("values") or {}).get("events") or {}
    return list(events.get("fault_events", [])), list(events.get("warn_events", []))


def _phase_in_period(t_s: float) -> float:
    return round(t_s - SAMPLE_PERIOD_S * math.floor(t_s / SAMPLE_PERIOD_S + 1e-9), 4)


def _summary(record: dict) -> dict:
    lift_s = d1_diag_tables._lift_time_s(record)
    return {"label": record["label"], "final_phase": record.get("final_phase"),
            "t_event_s": record.get("t_event_s"), "lift_s": lift_s,
            "lift_phase_in_period_s": None if lift_s is None else _phase_in_period(lift_s)}


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _step_tables(folder: Path, step: str) -> tuple[list[dict], dict[str, list[dict]]]:
    """(records, label -> first-step rows) of one step; writes its three tables."""
    name, trace_dir = STEPS[step]
    records = _read_jsonl(folder / name)
    first_rows, candidate_rows, gyro_rows = [], [], []
    first_by_label: dict[str, list[dict]] = {}
    for record in records:
        trace = json.loads((folder / trace_dir / f"trace_{record['label']}.json").read_text(
            encoding="utf-8"))
        _, rows = d1_diag_tables._primary_rows(trace)
        summary = _summary(record)
        gyro_rows.append(d1_diag_extra._gyro_row(record["label"], rows))
        candidate_rows += d1_diag_tables._candidate_rows(record["label"], rows,
                                                         record["t_event_s"] - 0.3)
        first = d1_diag_extra._first_step_rows(summary, rows) if summary["lift_s"] else []
        first_by_label[record["label"]] = first
        first_rows += first
    _write_csv(folder / f"first_step_period_{step}.csv", first_rows)
    _write_csv(folder / f"step_candidates_{step}.csv", candidate_rows)
    _write_csv(folder / f"gyro_availability_{step}.csv", gyro_rows)
    return records, first_by_label


def _repro_rows(folder: Path, diag1_off: dict[str, dict], jobs: list[dict],
                steps: dict[str, list[dict]]) -> list[dict]:
    stored_by_label = {job["label"]: (job["stored"][0] if job["stored"] else None)
                       for job in jobs}
    rows = []
    for step, records in steps.items():
        for record in records:
            base = diag1_off[record["label"]]
            stored = stored_by_label[record["label"]]
            faults, warnings = _events(record)
            base_faults, base_warnings = _events(base)
            rows.append({
                "step": step, "label": record["label"],
                "gyro_mode": record["diag"]["gyro_mode"],
                "r51_gyro_switch": record["diag"]["r51_gyro_switch"],
                "final_phase": record.get("final_phase"),
                "commands_sha256": record.get("commands_sha256"),
                "diag1_final_phase": base.get("final_phase"),
                "diag1_commands_sha256": base.get("commands_sha256"),
                "sha_equals_diag1": record.get("commands_sha256") == base.get("commands_sha256"),
                "record_equals_diag1": _comparable(record) == _comparable(base),
                "stored_commands_sha256": None if stored is None else stored["commands_sha256"],
                "sha_equals_stored": None if stored is None
                else record.get("commands_sha256") == stored["commands_sha256"],
                "fault_events": " ".join(faults), "diag1_fault_events": " ".join(base_faults),
                "gyro_warning": GYRO_WARNING in warnings,
                "diag1_gyro_warning": GYRO_WARNING in base_warnings})
    return rows


def _first_step_brief(rows: list[dict]) -> dict:
    if not rows or rows[0].get("t_s") is None:
        return {"t_s": None}
    legs = {row["leg"]: row for row in rows}
    brief = {"t_s": rows[0]["t_s"], "residual_change_kN": round(rows[0]["residual_change_kN"], 2),
             "sum_change_kN": round(rows[0]["sum_change_kN"], 2),
             "M_df_z_kN": round(rows[0]["M_df_z_kN"], 2),
             "is_lever_missing": rows[0]["is_lever_missing"],
             "candidates": " ".join(
                 f"{leg}:{row['leg_dp_head_bar']:.1f}bar/{row['threshold_kN']:.1f}kN/"
                 f"{'FAULT' if row['is_unexplained'] else 'ok'}" for leg, row in legs.items())}
    return brief


def _lever_at(folder: Path, step: str, label: str, t_s: float | None) -> float | None:
    if t_s is None:
        return None
    trace = json.loads((folder / STEPS[step][1] / f"trace_{label}.json").read_text(
        encoding="utf-8"))
    _, rows = d1_diag_tables._primary_rows(trace)
    match = [row for row in rows if abs(row["t_s"] - t_s) < 1e-6]
    return None if not match else match[0]["lever_z_m_s2"]


def _compare_rows(folder: Path, diag1_off, diag1_first, steps_first, steps_records):
    rows = []
    for label, base in diag1_off.items():
        row = {"label": label, "diag1_final_phase": base["final_phase"],
               "diag1_faults": " ".join(_events(base)[0])}
        for key, value in _first_step_brief(diag1_first.get(label, [])).items():
            row[f"diag1_{key}"] = value
        for step in ("B", "C"):
            record = next(r for r in steps_records[step] if r["label"] == label)
            faults, warnings = _events(record)
            row[f"{step}_final_phase"] = record.get("final_phase")
            row[f"{step}_faults"] = " ".join(faults)
            row[f"{step}_gyro_warning"] = GYRO_WARNING in warnings
            brief = _first_step_brief(steps_first[step].get(label, []))
            for key, value in brief.items():
                row[f"{step}_{key}"] = value
            lever = _lever_at(folder, step, label, brief.get("t_s"))
            row[f"{step}_lever_z_m_s2"] = lever
            mass = None
            first = steps_first[step].get(label, [])
            if first and first[0].get("M_eff_kg") is not None:
                mass = first[0]["M_eff_kg"]
            row[f"{step}_M_lever_z_kN"] = (None if lever is None or mass is None
                                           else round(mass * lever / 1e3, 2))
        rows.append(row)
    return rows


def _sweep_rows(records: list[dict], first_by_label: dict[str, list[dict]],
                jobs: dict[str, dict]) -> list[dict]:
    rows = []
    for record in records:
        summary = _summary(record)
        faults, warnings = _events(record)
        first = first_by_label.get(record["label"], [])
        lift_s = summary["lift_s"]
        row = {"label": record["label"], "shape": record["label"].split("_")[0],
               "offset_s": jobs[record["label"]]["offset_s"],
               "t_event_s": record.get("t_event_s"), "lift_s": lift_s,
               "lift_phase_in_period_s": summary["lift_phase_in_period_s"],
               "final_phase": record.get("final_phase"),
               "commands_sha256": record.get("commands_sha256"),
               "fault_events": " ".join(faults), "gyro_warning": GYRO_WARNING in warnings}
        if first and first[0].get("t_s") is not None:
            row["first_step_t_s"] = first[0]["t_s"]
            row["first_step_minus_lift_ms"] = round((first[0]["t_s"] - lift_s) * 1e3, 1)
            # the step period compares sample k with sample k-1; k-1 relative to the lift
            row["prev_sample_minus_lift_ms"] = round(
                (first[0]["t_s"] - SAMPLE_PERIOD_S - lift_s) * 1e3, 1)
            row["residual_change_kN"] = round(first[0]["residual_change_kN"], 2)
            row["max_ratio_to_threshold"] = round(max(r["residual_change_over_threshold"]
                                                      for r in first), 3)
            row["candidates"] = _first_step_brief(first)["candidates"]
        rows.append(row)
    return rows


def main() -> int:
    folder = Path(sys.argv[1])
    outputs = ["repro_check.csv", "compare_gyro.csv", "sweep_summary.csv"]
    outputs += [f"{kind}_{step}.csv" for step in STEPS
                for kind in ("first_step_period", "step_candidates", "gyro_availability")]
    if any((folder / name).exists() for name in outputs):
        print("refusing to overwrite")
        return 2
    jobs = json.loads((folder / "jobs_gyro.json").read_text(encoding="utf-8"))
    sweep_jobs = {}
    for name in ("jobs_sweep.json", "jobs_sweep_ext.json"):
        for job in json.loads((folder / name).read_text(encoding="utf-8")):
            sweep_jobs[job["label"]] = job
    diag1_off = {r["label"]: r for r in _read_jsonl(folder.parent / "runs_trace_off.jsonl")}
    diag1_first: dict[str, list[dict]] = {}
    with (folder.parent / "first_step_period.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for key in ("residual_change_kN", "sum_change_kN", "M_df_z_kN", "leg_dp_head_bar",
                        "threshold_kN", "t_s"):
                row[key] = float(row[key])
            row["is_unexplained"] = row["is_unexplained"] == "True"
            row["is_lever_missing"] = row["is_lever_missing"] == "True"
            diag1_first.setdefault(row["label"], []).append(row)
    steps_records, steps_first = {}, {}
    for step in STEPS:
        steps_records[step], steps_first[step] = _step_tables(folder, step)
    records_a = _read_jsonl(folder / "A_gyro_off_trace_off.jsonl")
    repro = _repro_rows(folder, diag1_off, jobs,
                        {"A": records_a, "B": steps_records["B"], "C": steps_records["C"]})
    _write_csv(folder / "repro_check.csv", repro)
    _write_csv(folder / "compare_gyro.csv",
               _compare_rows(folder, diag1_off, diag1_first, steps_first, steps_records))
    sweep_records = [r for step in SWEEP_STEPS for r in steps_records[step]]
    sweep_first = {k: v for step in SWEEP_STEPS for k, v in steps_first[step].items()}
    sweep = _sweep_rows(sweep_records, sweep_first, sweep_jobs)
    sweep.sort(key=lambda row: (row["shape"], row["offset_s"]))
    _write_csv(folder / "sweep_summary.csv", sweep)
    for row in repro:
        print(row["step"], row["label"], row["final_phase"], row["sha_equals_diag1"],
              row["record_equals_diag1"], row["fault_events"], row["gyro_warning"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
