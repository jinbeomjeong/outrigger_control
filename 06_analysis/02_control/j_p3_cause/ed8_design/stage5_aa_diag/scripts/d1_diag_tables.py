"""Tables of the stage-5 A/A D1 diagnosis (record only; no judgement).

Usage (python-dev or dynamics-dev):
  python.exe -I -B d1_diag_tables.py <stage5_aa_diag folder>

Reads ``diag_jobs.json``, ``runs_trace_off.jsonl``, ``runs_trace_on.jsonl``,
``trace_<label>.json`` and the stored stage-5 lines the jobs name; writes (refuses files that
exist):
  repro_check.csv        trace off vs stored line, trace on vs trace off
  trace_<label>.csv      every traced period, flat (columns in provenance.json)
  event_window.csv       all jobs, periods from t_event - 0.3 s to t_event + 1.0 s
  step_candidates.csv    every head step candidate after t_event - 0.3 s, with its threshold
  diag_summary.json      per job: lift time and phase in the 10 Hz period, the first period
                         after the lift, the FAULT periods

Exit codes: 0 written, 2 an input is missing or an output exists.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

LEGS = ("FL", "FR", "RL", "RR")
J_P3 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
STORED_RUN = J_P3 / "j9_runs" / "56849248"
WINDOW_BEFORE_S = 0.3
WINDOW_AFTER_S = 1.0
SAMPLE_PERIOD_S = 0.1
RECORD_FIELDS_IGNORED = ("wall_s", "label", "trace", "two_pressure_file")
"""Fields that differ between runs by design (not part of the reproduction comparison)."""

TRACE_COLUMNS = (
    ["t_s", "monitor", "is_locked_phase", "is_crawler_lifted", "max_abs_command_m_s"]
    + [f"head_bar_{leg}" for leg in LEGS] + [f"rod_bar_{leg}" for leg in LEGS]
    + [f"dp_head_bar_{leg}" for leg in LEGS] + [f"dp_rod_bar_{leg}" for leg in LEGS]
    + ["net_sum_kN", "previous_net_sum_kN", "sum_change_kN", "f_z_raw_m_s2", "f_z_used_m_s2",
       "lever_z_m_s2", "gyro_partial_means", "is_lever_missing", "previous_f_z_used_m_s2",
       "mass_kg", "M_f_z_kN", "M_df_z_kN", "d1pp_inputs_ready", "residual_kN",
       "previous_residual_kN", "residual_change_kN", "is_step_rule_suspended",
       "head_step_candidates", "rod_step_candidates", "step_rule_branch", "judged_change_kN",
       "judged_ratio"]
    + [f"threshold_kN_{leg}" for leg in LEGS] + [f"unexplained_{leg}" for leg in LEGS]
    + ["head_fault_reasons", "rod_steps_unexplained", "events"]
)


def _kilo(value: float | None) -> float | None:
    return None if value is None else value / 1e3


def _bar(values: list[float] | None, leg_index: int) -> float | None:
    return None if values is None else values[leg_index] / 1e5


def _flat_row(row: dict) -> dict:
    """One trace row as the :data:`TRACE_COLUMNS` (kN, bar)."""
    flat = {"t_s": row["t_s"], "monitor": row["monitor"],
            "is_locked_phase": row["is_locked_phase"],
            "is_crawler_lifted": row["is_crawler_lifted"],
            "max_abs_command_m_s": max(abs(v) for v in row["commanded_m_s"])}
    for index, leg in enumerate(LEGS):
        flat[f"head_bar_{leg}"] = _bar(row.get("head_Pa"), index)
        flat[f"rod_bar_{leg}"] = _bar(row.get("rod_Pa"), index)
        flat[f"dp_head_bar_{leg}"] = _bar(row.get("dp_head_Pa"), index)
        flat[f"dp_rod_bar_{leg}"] = _bar(row.get("dp_rod_Pa"), index)
    net_sum, previous_sum = row.get("net_sum_N"), row.get("previous_net_sum_N")
    flat["net_sum_kN"] = _kilo(net_sum)
    flat["previous_net_sum_kN"] = _kilo(previous_sum)
    flat["sum_change_kN"] = None if previous_sum is None else _kilo(net_sum - previous_sum)
    for key in ("f_z_raw_m_s2", "f_z_used_m_s2", "lever_z_m_s2", "gyro_partial_means",
                "is_lever_missing", "previous_f_z_used_m_s2", "mass_kg", "d1pp_inputs_ready",
                "is_step_rule_suspended", "step_rule_branch", "judged_ratio"):
        flat[key] = row.get(key)
    mass, f_z, previous_f_z = row.get("mass_kg"), row.get("f_z_used_m_s2"), row.get(
        "previous_f_z_used_m_s2")
    flat["M_f_z_kN"] = None if mass is None or f_z is None else _kilo(mass * f_z)
    has_pair = mass is not None and f_z is not None and previous_f_z is not None
    flat["M_df_z_kN"] = _kilo(mass * (f_z - previous_f_z)) if has_pair else None
    flat["residual_kN"] = _kilo(row.get("residual_N"))
    flat["previous_residual_kN"] = _kilo(row.get("previous_residual_N"))
    flat["residual_change_kN"] = _kilo(row.get("residual_change_N"))
    flat["judged_change_kN"] = _kilo(row.get("judged_change_N"))
    candidates = row.get("candidates", {})
    for leg in LEGS:
        candidate = candidates.get(leg)
        flat[f"threshold_kN_{leg}"] = None if candidate is None else _kilo(
            candidate["threshold_N"])
        flat[f"unexplained_{leg}"] = None if candidate is None else candidate["is_unexplained"]
    flat["head_step_candidates"] = " ".join(row.get("head_step_candidates", []))
    flat["rod_step_candidates"] = " ".join(row.get("rod_step_candidates", []))
    flat["head_fault_reasons"] = " ".join(f"{k}:{v}" for k, v in
                                          row.get("head_fault_reasons", {}).items())
    flat["rod_steps_unexplained"] = " ".join(row.get("rod_steps_unexplained", []))
    flat["events"] = " ".join(row.get("events", []))
    return flat


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()]


def _comparable(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in RECORD_FIELDS_IGNORED}


def _stored_record(stored: dict) -> dict:
    lines = (STORED_RUN / stored["file"]).read_text(encoding="utf-8").splitlines()
    return json.loads(lines[stored["file_line"] - 1])


def _repro_rows(entries, off_runs, on_runs) -> list[dict]:
    rows = []
    for entry, off, on in zip(entries, off_runs, on_runs, strict=True):
        stored = entry["stored"][0] if entry["stored"] else None
        row = {"label": entry["label"], "off_final_phase": off.get("final_phase"),
               "off_commands_sha256": off.get("commands_sha256"),
               "on_final_phase": on.get("final_phase"),
               "on_commands_sha256": on.get("commands_sha256"),
               "on_record_equals_off": _comparable(on) == _comparable(off),
               "stored_file": None, "stored_line": None, "stored_final_phase": None,
               "stored_commands_sha256": None, "off_sha_equals_stored": None,
               "off_phase_equals_stored": None, "off_record_equals_stored": None}
        if stored is not None:
            stored_record = _stored_record(stored)
            row.update({"stored_file": stored["file"], "stored_line": stored["file_line"],
                        "stored_final_phase": stored["final_phase"],
                        "stored_commands_sha256": stored["commands_sha256"],
                        "off_sha_equals_stored":
                            off.get("commands_sha256") == stored["commands_sha256"],
                        "off_phase_equals_stored":
                            off.get("final_phase") == stored["final_phase"],
                        "off_record_equals_stored":
                            _comparable(off) == _comparable(stored_record)})
        rows.append(row)
    return rows


def _primary_rows(trace: dict) -> tuple[str, list[dict]]:
    """The monitor with the most rows (the controller's) and its rows in time order."""
    counts: dict[str, int] = {}
    for row in trace["rows"]:
        counts[row["monitor"]] = counts.get(row["monitor"], 0) + 1
    primary = max(counts, key=counts.get)
    return primary, [row for row in trace["rows"] if row["monitor"] == primary]


def _lift_time_s(record: dict) -> float | None:
    leg = record["job"]["twin"]["leg"]
    lift = (record.get("event_output") or {}).get("lifts", {}).get(leg)
    if lift is None or record.get("t_event_s") is None or lift.get("first_s") is None:
        return None
    return record["t_event_s"] + lift["first_s"]


def _candidate_rows(label: str, rows: list[dict], t_from_s: float) -> list[dict]:
    out = []
    for row in rows:
        if row["t_s"] < t_from_s - 1e-9:
            continue
        for leg, candidate in row.get("candidates", {}).items():
            out.append({"label": label, "t_s": row["t_s"], "leg": leg,
                        "dp_head_bar": candidate["dp_head_Pa"] / 1e5,
                        "step_force_kN": candidate["step_force_N"] / 1e3,
                        "threshold_kN": candidate["threshold_N"] / 1e3,
                        "judged_change_kN": row["judged_change_N"] / 1e3,
                        "branch": row["step_rule_branch"],
                        "judged_ratio": row["judged_ratio"],
                        "judged_mass_kg": row.get("judged_mass_kg"),
                        "is_lever_missing": row["is_lever_missing"],
                        "gyro_partial_means": row["gyro_partial_means"],
                        "lever_z_m_s2": row["lever_z_m_s2"],
                        "sum_change_kN": (row["net_sum_N"] - row["previous_net_sum_N"]) / 1e3,
                        "M_df_z_kN": _flat_row(row)["M_df_z_kN"],
                        "is_unexplained": candidate["is_unexplained"],
                        "events": " ".join(row.get("events", []))})
    return out


def _job_summary(entry: dict, record: dict, trace: dict) -> dict:
    primary, rows = _primary_rows(trace)
    lift_s = _lift_time_s(record)
    summary = {"label": entry["label"], "job": entry["job"], "final_phase":
               record.get("final_phase"), "t_event_s": record.get("t_event_s"),
               "lift_s": lift_s, "monitors": {m: sum(r["monitor"] == m for r in trace["rows"])
                                              for m in trace["monitors"]},
               "primary_monitor": primary,
               "max_step_Pa": trace["monitors"][primary]["settings"]["max_step_Pa"],
               "imu_residual_step_ratio":
                   trace["monitors"][primary]["settings"].get("imu_residual_step_ratio"),
               "head_area_m2": trace["monitors"][primary]["head_area_m2"],
               "gyro_missing_periods": [r["t_s"] for r in rows if r["is_lever_missing"]],
               "fault_periods": [r["t_s"] for r in rows if r.get("head_fault_reasons")]}
    if lift_s is not None:
        summary["lift_phase_in_period_s"] = round(lift_s - SAMPLE_PERIOD_S
                                                  * int(lift_s / SAMPLE_PERIOD_S + 1e-9), 4)
        after = [r for r in rows if r["t_s"] > lift_s - 1e-9]
        if after:
            summary["first_period_after_lift"] = _flat_row(after[0])
    return summary


def main() -> int:
    folder = Path(sys.argv[1])
    entries = json.loads((folder / "diag_jobs.json").read_text(encoding="utf-8"))
    off_runs = _read_jsonl(folder / "runs_trace_off.jsonl")
    on_runs = _read_jsonl(folder / "runs_trace_on.jsonl")
    outputs = [folder / name for name in ("repro_check.csv", "event_window.csv",
                                          "step_candidates.csv", "diag_summary.json")]
    outputs += [folder / f"trace_{entry['label']}.csv" for entry in entries]
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        print(f"refusing to overwrite {existing}")
        return 2
    repro = _repro_rows(entries, off_runs, on_runs)
    _write_csv(folder / "repro_check.csv", list(repro[0]), repro)
    window_rows, candidate_rows, summaries = [], [], []
    for entry, record in zip(entries, on_runs, strict=True):
        trace = json.loads((folder / f"trace_{entry['label']}.json").read_text(
            encoding="utf-8"))
        flat = [_flat_row(row) for row in trace["rows"]]
        _write_csv(folder / f"trace_{entry['label']}.csv", TRACE_COLUMNS, flat)
        _, rows = _primary_rows(trace)
        t_event = record["t_event_s"]
        for row in rows:
            if t_event - WINDOW_BEFORE_S - 1e-9 <= row["t_s"] <= t_event + WINDOW_AFTER_S:
                window_rows.append({"label": entry["label"], **_flat_row(row)})
        candidate_rows += _candidate_rows(entry["label"], rows, t_event - WINDOW_BEFORE_S)
        summaries.append(_job_summary(entry, record, trace))
    _write_csv(folder / "event_window.csv", ["label", *TRACE_COLUMNS], window_rows)
    if candidate_rows:
        _write_csv(folder / "step_candidates.csv", list(candidate_rows[0]), candidate_rows)
    (folder / "diag_summary.json").write_text(json.dumps(summaries, indent=1),
                                              encoding="utf-8")
    for row in repro:
        print(row["label"], row["off_final_phase"], row["on_record_equals_off"],
              row["off_sha_equals_stored"], row["off_record_equals_stored"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
