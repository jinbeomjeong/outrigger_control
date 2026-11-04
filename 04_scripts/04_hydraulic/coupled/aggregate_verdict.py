"""Pair table of the coupling verdict: values with the flow limit on and off (criteria 7, V-5).

Reads the result files of ``run_verdict.py``. Output values only, no verdict text: the T-1 .. T-3
inputs, R-1 .. R-7 and E-1 .. E-5, the V-2 (a) values and the T-4 inputs of each run, and the on-off
command difference (V-1). T-4 itself is control-expert's.

Also checks the off runs against the stored harness hashes (finB2_*).

Usage:
  <python> -I -B aggregate_verdict.py [--dir DIR] [--bundles A,B,C,D,E] [--out-prefix NAME]
Writes <dir>/<name>.json and <dir>/<name>.csv (long form: run, metric, on, off, delta).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from verdict_cases import CASES, REANCHOR_ON, EventTwin, SteadyTwin  # noqa: E402

ROOT = HERE.parents[2]
DEFAULT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "verdict"
STORED_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev85"
GUARD_STROKE_MM = 682.8
"""Lift guard stroke: the H-6 stroke input is the reading margin to it."""
OFF_BUNDLE = "OFF"


def _dig(record: dict, path: str):
    """Value at a dotted path; None when a step is missing."""
    node = record
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


PAIR_METRICS = {
    # metric name -> dotted path in the run result
    "item2_max_abs_att_last_5s_deg": "values.attitude.max_abs_last_5s_deg",
    "item3_min_force_after_liftoff_kN": "values.forces.after_liftoff.min_kN",
    "item4_max_moving_bar": "values.pressure.max_moving_bar",
    "item4_saturation_leg_chunks": "values.pressure.saturation_leg_chunks",
    "item5_rocking_amplitude_deg": "values.attitude.rocking_amplitude_deg",
    "item5_filter_residual_deg": "values.attitude.filter_residual_last_5s_deg",
    "item7_probe_att_change_deg": "values.probe_attitude_change_deg",
    "S8C1_min_force_first_8s_kN": "values.forces.first_8s.min_kN",
    "S8C1_min_force_after_8s_kN": "values.forces.after_8s.min_kN",
    "P3_1_crawler_max_after_ready_N": "rows.P3-1.crawler_N_max_after_ready",
    "P3_1_n_recontact": "rows.P3-1.n_recontact",
    "P3_2_loc_delay_s": "rows.P3-2.loc_delay_s",
    "P3_3_min_force_after_off_kN": "rows.P3-3.min_true_Fcyl_after_off_kN",
    "P3_5_rut_ready_mm": "rows.P3-5.rut_ready_mm",
    "P3_5_rut_end_mm": "rows.P3-5.rut_end_mm",
    "P3_5_max_stroke_reading_mm": "rows.P3-5.max_motor_stroke_mm",
    "P3_6_t_ready_s": "rows.P3-6.t_ready_s",
    "R2_max_abs_att_after_liftoff_deg": "values.attitude.max_abs_after_liftoff_deg",
    "R3_peak_abs_D_kN": "values.twist.peak_abs_after_liftoff_kN",
    "R3_abs_D_at_done_kN": "values.twist.abs_at_first_done_kN",
    "R5_t_loc_last_s": "values.events.t_loc_last_s",
    "R5_t_lift_s": "values.forces.t_lift_s",
    "R6_reapproach_after_liftoff": "values.events.reapproach_starts_after_liftoff",
    "R6_p5_relevels": "values.events.p5_relevels_after_liftoff",
    "R6_guard_active_s": "values.guard_active_s",
    "R6_t_touch_end_s": "values.times.t_touch_end_s",
    "t_first_ready_s": "values.times.t_first_ready_s",
    "t_first_done_s": "values.times.t_first_done_s",
    "max_stroke_reading_mm": "max_motor_stroke_reading_mm",
    "event_min_F_after_event_FL_kN": "event_output.min_F_after_event_kN.FL",
    "event_min_F_after_event_FR_kN": "event_output.min_F_after_event_kN.FR",
    "event_min_F_after_event_RL_kN": "event_output.min_F_after_event_kN.RL",
    "event_min_F_after_event_RR_kN": "event_output.min_F_after_event_kN.RR",
    "event_pair_union_s": "event_output.pair_union_s",
    "event_pair_last_touch_s": "event_output.pair_last_touch_s",
    "event_adj_lift_sum_W_s": "event_output.adj_lift_sum_W_s",
    "event_adj_max_gap_W_mm": "event_output.adj_max_gap_W_mm",
    "event_adj_lift_outside_W_s": "event_output.adj_lift_outside_W_s",
    "event_t_ready_back_s": "event_output.t_ready_back_s",
    "event_moving_outside_max_bar": "event_output.pressure.moving_outside_max_bar",
    "event_max_att_change_deg": "event_output.max_att_change_deg",
    "event_fault_periods": "event_output.fault_periods",
}
"""Numeric values compared on against off."""
SET_METRICS = {
    # T-2, R-5: the on value and the off value side by side; no delta
    "T2_harness_class": "harness_class",
    "T2_failed_rows": "failed_rows",
    "T2_final_phase": "final_phase",
    "T2_fault_events": "values.events.fault_events",
    "T2_warn_events": "values.events.warn_events",
    "R5_info_rule_events": "values.events.info_rule_events",
    "R5_soil_mode_started": "values.events.soil_mode_started",
}
RUN_ONLY_BLOCKS = {
    "V2_a": "values.V2_a", "E1": "values.E1", "E2": "values.E2", "E3": "values.E3",
    "E4": "values.E4", "E5": "values.E5", "T4_inputs": "values.T4_inputs",
    "supply_L_min": "values.supply_L_min",
}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _delta(on, off):
    return on - off if _is_number(on) and _is_number(off) else None


def _load_runs(directory: Path) -> dict[str, dict]:
    runs = {}
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".error.json"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if "run_id" in record:
            runs[record["run_id"]] = record
    return runs


def _stored_hash(case_id: str, cache: dict) -> str | None:
    """Stored final-harness command hash of a case; None when no such row exists."""
    twin = CASES[case_id].twin
    if isinstance(twin, SteadyTwin):
        records = _stored_file(twin.stored_file, cache).get("records", [])
        return next((r.get("hash") for r in records if r.get("id") == twin.stored_id), None)
    if isinstance(twin, EventTwin) and twin.stored_key is not None:
        results = _stored_file(twin.stored_file, cache).get("results", [])
        result = next((r for r in results if r.get("key") == twin.stored_key), None)
        if result is None:
            return None
        return next((run["commands_sha256"] for run in result["runs"]
                     if run["event"] == twin.event and run["offset_s"] == twin.offset_s), None)
    return None


def _stored_file(name: str, cache: dict) -> dict:
    if name not in cache:
        cache[name] = json.loads((STORED_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return cache[name]


def off_identity(runs: dict[str, dict]) -> list[dict]:
    """The off runs against the stored harness hashes (flow limit off = bit identical)."""
    cache: dict = {}
    table = []
    for record in runs.values():
        if record["bundle"] != OFF_BUNDLE:
            continue
        # the stored row has REANCHOR off: another definition, nothing to compare with
        is_other_definition = record.get("decision") == REANCHOR_ON
        stored = None if is_other_definition else _stored_hash(record["case_id"], cache)
        computed = record.get("harness_commands_sha256")
        table.append({"case_id": record["case_id"], "stored_sha256": stored,
                      "off_sha256": computed,
                      "is_same": None if stored is None else stored == computed})
    return table


def command_difference(directory: Path, on_id: str, off_id: str) -> dict:
    """V-1: largest |command on - command off| over the common periods [m/s]."""
    with np.load(directory / f"{on_id}.npz", allow_pickle=False) as on_file:
        on = on_file["command"]
    with np.load(directory / f"{off_id}.npz", allow_pickle=False) as off_file:
        off = off_file["command"]
    common = min(len(on), len(off))
    difference = float(np.abs(on[:common] - off[:common]).max()) if common else None
    return {"periods_on": len(on), "periods_off": len(off),
            "max_abs_command_difference_m_s": difference}


def pair_row(record: dict, off: dict | None, directory: Path) -> dict:
    """Values of one on run against its off run."""
    metrics = {}
    for name, path in PAIR_METRICS.items():
        on_value = _dig(record, path)
        off_value = None if off is None else _dig(off, path)
        if on_value is None and off_value is None:
            continue
        metrics[name] = {"on": on_value, "off": off_value, "delta": _delta(on_value, off_value)}
    sets = {name: {"on": _dig(record, path), "off": None if off is None else _dig(off, path)}
            for name, path in SET_METRICS.items()}
    stroke = _dig(record, "run.max_motor_stroke_mm")
    stroke_off = None if off is None else _dig(off, "run.max_motor_stroke_mm")
    if stroke is not None:
        metrics["T3_guard_reading_margin_mm"] = {
            "on": GUARD_STROKE_MM - stroke,
            "off": None if stroke_off is None else GUARD_STROKE_MM - stroke_off,
            "delta": None if stroke_off is None else stroke_off - stroke}
    row = {"run_id": record["run_id"], "bundle": record["bundle"], "case_id": record["case_id"],
           "chrono_name": record["chrono_name"], "setting": record["setting"],
           "off_run": None if off is None else off["run_id"], "metrics": metrics, "sets": sets,
           "run_only": {name: _dig(record, path) for name, path in RUN_ONLY_BLOCKS.items()},
           "hash_on": record.get("harness_commands_sha256"),
           "hash_off": None if off is None else off.get("harness_commands_sha256")}
    if off is not None:
        row["V1_commands"] = command_difference(directory, record["run_id"], off["run_id"])
        row["V1_commands"]["is_hash_same"] = row["hash_on"] == row["hash_off"]
    return row


def _write_long_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "bundle", "case_id", "metric", "on", "off", "delta"])
        for row in rows:
            for name, cell in row["metrics"].items():
                writer.writerow([row["run_id"], row["bundle"], row["case_id"], name, cell["on"],
                                 cell["off"], cell["delta"]])
            for name, cell in row["sets"].items():
                writer.writerow([row["run_id"], row["bundle"], row["case_id"], name,
                                 json.dumps(cell["on"]), json.dumps(cell["off"]), ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--bundles", default="A,B,C,D,E")
    parser.add_argument("--out-prefix", default="verdict_pairs")
    args = parser.parse_args()
    runs = _load_runs(args.dir)
    bundles = args.bundles.split(",")
    rows = []
    for record in runs.values():
        if record["bundle"] in bundles:
            off = runs.get(f"{OFF_BUNDLE}_{record['case_id']}")
            rows.append(pair_row(record, off, args.dir))
    payload = {"note": "values only; verdicts by control-expert (criteria 13)",
               "off_identity": off_identity(runs), "pairs": rows}
    json_path = args.dir / f"{args.out_prefix}.json"
    json_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    _write_long_csv(args.dir / f"{args.out_prefix}.csv", rows)
    print(f"{len(rows)} pairs, {len(payload['off_identity'])} off rows -> {json_path}")


if __name__ == "__main__":
    main()
