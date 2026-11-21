"""436.9 edition 5 P5-2 / P5-4 (``jp3_remedy_spec_v5.md`` 5): the fixed values computed after
the implementation and before the run (records for the seal; this script prepares them, the
main session runs it).

``p52``  Case replay rows (``run_v5`` JSON lines of ``j9_cases`` / ``j9_case_f`` /
         ``jp3_case_replay.py`` / ``jp3_x11_replay.py``, or an r79 run file) to the P5-2 record:
         per row its setting, job, ``rule_revision``, the J-P3 judged key sums
         (``jp3a_breach_reads``, ``jp3b_breach_over_tol_reads``, ``jp3c_breach_reads``) and the
         rev 6 counts ``jp3_r58_witness_carries``, ``jp3_r59_substeps``, ``jp3_r510_candidates``
         (per leg and summed). A row without its ``extend_bound_check`` or without a judged key
         is listed in ``problems`` (never read as 0).
``p54``  Open-loop replay (commands fixed) of stored T4h records (P5-4: the stored VBH T4h) with
         the run's own monitor setting at ③ revision 5 and at revision 6
         (``t4h_replay.checked_run_config``), the rod fallbacks forced at the run's own
         ``WARN_ROD_PRESSURE_FALLBACK`` events (``contact_replay.fallback_rows_from_events``).
         Per revision: ``retract_tracker_dominated_reads`` (lock / hold reads of a fallback leg
         whose ④ comes from an R5-7 ``retract_tracker`` candidate) and the ``max_over_kN``
         distribution of their stretches; the reduction of rev 6 against rev 5 (P5-4 record,
         expected about 23 %, F8). The plant rod pressure is not in a T4h record, so
         ``max_over_kN`` uses ``p_tr ~ (p_h,read A_h - F_true) / A_ann`` (T4h ``true_force_N``):
         the head reading error enters both revisions alike (a record, not a judged value).

Usage (dynamics-dev or Chrono-dev, project root; read only, one output file each):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_p5_fixed_values.py p52 --rows <file> [...]
      --out <p52.json>
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_p5_fixed_values.py p54 --t4h <folder>
      --out <p54.json>
Exit 0 written, 2 an existing ``--out`` or no input, 3 a tool error. The stdout's last line is
JSON with ``status``, the counts and the output path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
COVERAGE_KEYS = ("jp3_r58_witness_carries", "jp3_r59_substeps", "jp3_r510_candidates")
REVISIONS = (5, 6)
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3


# ------------------------------------------------------------------------------- P5-2
def read_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(document, dict):
        return document["results"] if "results" in document else [document]
    return document


def _check_of(row: dict) -> dict | None:
    record = row.get("hydraulics_record") or {}
    return record.get("extend_bound_check") or row.get("extend_bound_check")


def p52_row(row: dict, problems: list[str]) -> dict:
    """The P5-2 values of one case replay row."""
    label = row.get("key") or json.dumps(row.get("job"), sort_keys=True)
    check = _check_of(row)
    out = {"row": label, "setting": row.get("v5_setting") or (row.get("job") or {}).get("setting"),
           "rule_revision": None if check is None else check.get("rule_revision")}
    if check is None:
        problems.append(f"{label}: no extend_bound_check")
        return out
    for key in (*JUDGED_KEYS, *COVERAGE_KEYS):
        values = check.get(key)
        if not (isinstance(values, list) and len(values) == 4):
            if key in JUDGED_KEYS or check.get("rule_revision") == 6:
                problems.append(f"{label}: {key} missing")
            continue
        out[key] = values
        out[f"{key}_sum"] = int(sum(values))
    return out


def p52(paths: list[Path]) -> dict:
    problems: list[str] = []
    rows = [p52_row(row, problems) for path in paths for row in read_rows(path)]
    return {"rule": "jp3_remedy_spec_v5.md P5-2 (fixed after implementation, before the run)",
            "inputs": [str(path) for path in paths], "rows": rows, "problems": problems,
            "judged_key_total": sum(row.get(f"{key}_sum", 0) for row in rows
                                    for key in JUDGED_KEYS)}


# ------------------------------------------------------------------------------- P5-4
def p54_record(path: Path, revision: int) -> dict:
    """Dominated reads of one stored T4h record replayed at ``revision`` (module docstring)."""
    import t4h_replay

    from outrigger_sim.control import contact_replay as replay
    from outrigger_sim.control.c2 import C2Geometry, C2Phase
    from outrigger_sim.control.extend_start_bound import _DominatedReads
    from outrigger_sim.control.two_pressure import RodSensorState

    arrays, meta = t4h_replay.load_record(path)
    closed_loop, config, _ = t4h_replay.checked_run_config(path.name, meta, "tracked_bound",
                                                          revision)
    geometry = C2Geometry.from_params(closed_loop.PARAMS)
    allowance = t4h_replay.offset_allowance_of(meta, config)
    events = [(float(t), str(name)) for t, name in meta.get("events") or []]
    t_s = np.asarray(arrays["t_s"], float)
    head = np.asarray(arrays["head_pressure_Pa"], float)
    rod = np.asarray(arrays["rod_pressure_Pa"], float)
    stroke = np.asarray(arrays["motor_stroke_m"], float)
    acting = replay._previous(np.asarray(arrays["command_m_s"], float), fill=0.0)
    is_ready = replay._previous(np.asarray(arrays["phase"]), fill="") == C2Phase.READY.value
    seal_band = replay._previous(np.asarray(arrays["seal_band_N"], float))
    true_force = np.asarray(arrays["true_force_N"], float)
    head_area = np.asarray(geometry.head_area_m2, float)
    annulus = np.asarray(geometry.annulus_area_m2, float)
    monitor = replay._offline_monitor(geometry, config)
    fallback_rows = replay.fallback_rows_from_events(events, t_s, config.period_s)
    calibration_rows = replay._calibration_rows(events, t_s, config.period_s)
    offsets = np.asarray(meta.get("zero_offset_N") or np.zeros(4), float)
    dominated = _DominatedReads(600.0 / annulus)
    for row in range(t_s.size):
        is_calibrated = calibration_rows <= row
        monitor.set_zero_offsets_N(np.where(is_calibrated, offsets, 0.0))
        has_allowance = (is_calibrated if allowance.from_s is None
                         else np.full(4, t_s[row] > allowance.from_s + 1e-9))
        monitor.set_offset_allowance_N(np.where(has_allowance, allowance.deduction_N, 0.0))
        for leg, first_row in enumerate(fallback_rows):
            if first_row == row:
                monitor.rod_state[leg] = RodSensorState.FALLBACK
        monitor.read(float(t_s[row]), head[row], rod[row], acting[row], bool(is_ready[row]),
                     seal_band[row], stroke_m=stroke[row])
        trace = monitor.extend_bound_trace_row()
        if trace is None:
            continue
        plant_Pa = (head[row] * head_area - true_force[row]) / annulus  # p_tr proxy
        classes = [_class(value) for value in trace["class"]]
        dominated.add(classes, np.asarray(trace["used_bound_Pa"], float), plant_Pa, trace,
                      true_force[row])
    record = dominated.record()
    over = [row["max_over_kN"] for row in record["retract_tracker_stretch_log"]
            if row["max_over_kN"] is not None]
    return {"file": path.name, "revision": revision,
            "dominated_reads": int(sum(record["retract_tracker_dominated_reads"])),
            "stretches": len(record["retract_tracker_stretch_log"]), "max_over_kN": over}


def _class(value):
    from outrigger_sim.control.extend_start_bound import PeriodClass

    return None if value is None else PeriodClass(value)


def p54(folder: Path) -> dict:
    files = sorted(folder.glob("*.npz"))
    per_revision = {}
    for revision in REVISIONS:
        rows = [p54_record(path, revision) for path in files]
        over = [value for row in rows for value in row["max_over_kN"]]
        per_revision[str(revision)] = {
            "dominated_reads": sum(row["dominated_reads"] for row in rows),
            "stretches": sum(row["stretches"] for row in rows),
            "max_over_kN_p50": float(np.percentile(over, 50)) if over else None,
            "max_over_kN_p90": float(np.percentile(over, 90)) if over else None,
            "max_over_kN_max": max(over) if over else None, "files": rows}
    before, after = (per_revision[str(revision)]["dominated_reads"] for revision in REVISIONS)
    return {"rule": "jp3_remedy_spec_v5.md P5-4 (record; expected reduction about 23 %, F8)",
            "t4h_folder": str(folder), "files": len(files), "by_revision": per_revision,
            "dominated_reduction": None if before == 0 else 1.0 - after / before,
            "plant_rod_pressure": "(head reading x A_h - true_force_N) / A_ann (T4h proxy)"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rows = sub.add_parser("p52")
    rows.add_argument("--rows", type=Path, nargs="+", required=True)
    rows.add_argument("--out", type=Path, required=True)
    replay_parser = sub.add_parser("p54")
    replay_parser.add_argument("--t4h", type=Path, required=True)
    replay_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_usable", "reason": "--out exists"}))
        return EXIT_NOT_USABLE
    try:
        document = p52(args.rows) if args.command == "p52" else p54(args.t4h)
    except Exception as exc:  # a tool error
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1)
    count = len(document.get("rows", [])) or document.get("files", 0)
    if not count:
        print(json.dumps({"status": "not_usable", "reason": "no input row", "out": str(args.out)}))
        return EXIT_NOT_USABLE
    print(json.dumps({"status": "written", "count": count,
                      "problems": len(document.get("problems", [])), "out": str(args.out)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
