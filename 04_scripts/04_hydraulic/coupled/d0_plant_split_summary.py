"""D0 plant split summary (record, not a judgement): per variant and key the values of the
``d0_plant_split.py`` lines.

Per line (``rows`` of the report and the CSV beside it):

* ``min_force_kN``: the J2 value of ``judge_stage1_4368._j2_value_N`` (rigid event rows: the
  minimum of ``event_output.min_F_after_W_kN``, 1 ms E-3; steady rows: the minimum force after
  the lift-off); ``min_force_leg`` for event rows.
* ``J1`` .. ``J5``: the row's own item states of ``jp3_j9main_judge.own_item_failures`` (the
  j9_main judge definitions without the V0 pairing): ``pass``, ``fail``, ``flag``, ``record``,
  ``undetermined``; ``n/a`` where the item has no own definition (J3 on event rows, J5 on
  steady rows).
* ``t_first_ready_s``, ``final_phase``.
* LEVEL hold (``a2_mechanism.level_hold`` / ``a3_held_all_rows.held_fraction`` of the cause
  analysis, same definitions): ``held_fraction`` = LEVEL leg-reads with the plant locked and
  ``|u| > 1e-6 m/s`` over LEVEL leg-reads with ``|u| > 1e-6 m/s``; the median / p90 of ``|u|``
  of the held reads; over the last 20 s the fraction of reads with all four legs locked and of
  leg-reads with ``|u| <= u_hold`` (0.01 v_max).
* Event rows, on the minimum leg (``a2_mechanism.r12_features`` / ``retract_delays``, same
  definitions): 10 Hz minimum of ``true_force_min_N`` in [t_ev, t_ev + 5 s] and its time after
  the event, the plant lock at the first extend read (``u > u_hold``) and the delay to the
  first unlocked read, retract reads (``u < -u_hold``) before it, and the largest delay from the
  first ``u < -1 mm/s`` read of another leg in [t_ev, t_ev + 3 s] to its first unlocked read.
* P1 record (new, D0 only; ``p1_*`` T4h arrays): of the held LEVEL leg-reads with a logged P1
  row, ``held_filling`` (line state ``x`` rose since the previous read of that leg by more than
  1 nm) and ``held_balanced`` (it did not: neutral drain balance), and ``p1_read_found`` /
  T4h reads.

Checks (``checks`` of the report): every line runs the options of its D0 variant
(``hydraulic_options``), the controller tag of its base setting, no module from another
checkout, P1 variants carry the ``p1_*`` arrays and D0-2 none; every planned job (``--variants``
/ ``--keys``, default all 64) has one line without error and no other job has one; with
``--reference`` the D0-1 command hash of each key against the reference VBJ line (606f8713
``j9_main.jsonl``).

======  ===================  ============================================================
exit    status               meaning
======  ===================  ============================================================
0       ``written``          report written, every check clean
2       ``setting_defect``   report written; a definition, tag, checkout or record check
                             failed (``checks``)
2       ``incomplete``       report written; a planned job is missing or has an error line
2       ``input_error``      no report: missing input, a line without its T4h, or an
                             existing ``--out``
3       ``tool_error``       a tool error
======  ===================  ============================================================

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/d0_plant_split_summary.py --rows <d0 jsonl>
      --out <report.json> [--reference <j9_main.jsonl>] [--variants ...] [--keys ...]
The T4h records are read from ``<rows stem>_t4h/``. The stdout's last line is JSON with
``status``, the counts and the report path.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (also puts the harness folders on sys.path)
import jp3_j9main_judge as j9judge  # noqa: E402
import judge_stage1_4368 as path1  # noqa: E402

from outrigger_sim.hydraulics.v5_options import HydraulicOptions  # noqa: E402

EXIT_WRITTEN, EXIT_STOP, EXIT_TOOL = 0, 2, 3
LEGS = ("FL", "FR", "RL", "RR")
V_MAX_M_S = 0.020924302
"""YAML ``actuator.max_speed_m_s`` (as ``a2_mechanism.V_MAX``)."""
U_HOLD_M_S = 0.01 * V_MAX_M_S
EPS_M_S = 1.0e-6
"""``check_open_delay.EPS_M_S``."""
EVENT_WINDOW_S = 5.0
RETRACT_WINDOW_S = 3.0
RETRACT_START_M_S = -1.0e-3
LAST_WINDOW_S = 20.0
X_RISE_TOL_M = 1.0e-9
J_ITEMS = ("J1", "J2", "J3", "J4", "J5")
EVENT_ONLY_ITEMS = ("J5",)
STEADY_ONLY_ITEMS = ("J3",)
P1_FOUND_ARRAY = "p1_read_found"
CONTROLLER_TAG_OF_BASE = {"VBJ": "final_C4G2_P3W_LAS_K1", "VBH": "final_C4G2_P3W_LAS_K1",
                          "VB": "final_C4G2_P3_LAS_K1"}
"""Expected recorded tag per base setting (③ revision 6 / 4 with the LAS-b and K1 switches)."""


class InputError(Exception):
    """No report can be written (exit 2)."""


# ------------------------------------------------------------------------------ T4h metrics
def _level_reads(data) -> np.ndarray:
    return np.char.lower(data["phase"].astype(str)) == "level"


def level_hold(data) -> dict:
    """``a2_mechanism.level_hold`` without the |u| list (cause analysis, same definitions)."""
    is_level = _level_reads(data)
    speed = np.abs(data["command_m_s"])
    locked = data["locked"]
    held = is_level[:, None] & locked & (speed > EPS_M_S)
    commanded = is_level[:, None] & (speed > EPS_M_S)
    t_s = data["t_s"]
    last = t_s >= t_s[-1] - LAST_WINDOW_S - 1e-6
    return {
        "held_fraction": round(float(held.sum() / max(commanded.sum(), 1)), 4),
        "held_leg_reads": int(held.sum()),
        "held_u_median_mm_s": (round(float(np.median(speed[held])) * 1e3, 4)
                               if held.any() else None),
        "held_u_p90_mm_s": (round(float(np.percentile(speed[held], 90)) * 1e3, 4)
                            if held.any() else None),
        "last20_all_locked_fraction": round(float(np.mean(np.all(locked[last], axis=1))), 3),
        "last20_cmd_le_uhold_fraction": round(float(np.mean(speed[last] <= U_HOLD_M_S)), 3),
        "t_end_s": round(float(t_s[-1]), 2),
    }


def event_leg_features(data, t_event_s: float, leg: int) -> dict:
    """``a2_mechanism.r12_features`` (subset) and ``retract_delays`` on the minimum leg."""
    t_s = data["t_s"]
    command = data["command_m_s"][:, leg]
    locked = data["locked"][:, leg]
    force_kN = data["true_force_min_N"][:, leg] / 1e3
    window = np.flatnonzero((t_s >= t_event_s - 1e-9) & (t_s <= t_event_s + EVENT_WINDOW_S + 1e-9))
    i_min = window[int(np.nanargmin(force_kN[window]))]
    extend_reads = window[command[window] > U_HOLD_M_S]
    i_ext = int(extend_reads[0]) if len(extend_reads) else None
    unlock_delay_s = None
    if i_ext is not None:
        unlocked = np.flatnonzero((np.arange(len(t_s)) >= i_ext) & ~locked)
        if len(unlocked):
            unlock_delay_s = round(float(t_s[unlocked[0]] - t_s[i_ext]), 3)
    before = window[window < (i_ext if i_ext is not None else i_min)]
    return {
        "Fmin_10hz_kN": round(float(force_kN[i_min]), 3),
        "t_min_after_event_s": round(float(t_s[i_min] - t_event_s), 3),
        "locked_at_extend": None if i_ext is None else bool(locked[i_ext]),
        "unlock_delay_s": unlock_delay_s,
        "retract_reads_before_extend": int(np.sum(command[before] < -U_HOLD_M_S)),
        "other_leg_retract_delay_max_s": _other_leg_retract_delay_max_s(data, t_event_s, leg),
    }


def _other_leg_retract_delay_max_s(data, t_event_s: float, min_leg: int) -> float | None:
    t_s = data["t_s"]
    delays = []
    for leg in range(len(LEGS)):
        if leg == min_leg:
            continue
        command = data["command_m_s"][:, leg]
        locked = data["locked"][:, leg]
        starts = np.flatnonzero((t_s >= t_event_s - 1e-9) & (t_s <= t_event_s + RETRACT_WINDOW_S)
                                & (command < RETRACT_START_M_S))
        if not len(starts):
            continue
        unlocked = np.flatnonzero((np.arange(len(t_s)) >= starts[0]) & ~locked)
        if len(unlocked):
            delays.append(round(float(t_s[unlocked[0]] - t_s[starts[0]]), 2))
    return max(delays) if delays else None


def p1_hold_split(data) -> dict | None:
    """Held LEVEL leg-reads split by the P1 line state (None without the ``p1_*`` arrays)."""
    if P1_FOUND_ARRAY not in data.files:
        return None
    found = data[P1_FOUND_ARRAY]
    x_m = data["p1_x_m"]
    is_level = _level_reads(data)
    held = (is_level[:, None] & data["locked"] & (np.abs(data["command_m_s"]) > EPS_M_S)
            & found[:, None])
    rose = np.zeros_like(held)
    rose[1:] = (x_m[1:] - x_m[:-1] > X_RISE_TOL_M) & found[:-1, None]
    return {"p1_read_found": int(found.sum()), "t4h_reads": int(len(found)),
            "held_filling": int((held & rose).sum()),
            "held_balanced": int((held & ~rose).sum())}


# ------------------------------------------------------------------------------ line values
STATE_PRIORITY = ("fail", "flag", "undetermined", "record")
"""The state an item keeps when the row has several entries for it (first = strongest)."""


def own_item_states(metric: dict) -> dict[str, str]:
    """J1 .. J5 of the row on its own (module docstring)."""
    states = {item: "pass" for item in J_ITEMS}
    not_defined = STEADY_ONLY_ITEMS if metric["is_event"] else EVENT_ONLY_ITEMS
    for item in not_defined:
        states[item] = "n/a"
    for entry in j9judge.own_item_failures(metric):
        item, state = entry["item"], entry["state"]
        if item not in states:
            continue
        current = states[item]
        if current in ("pass", "n/a") or (STATE_PRIORITY.index(state)
                                          < STATE_PRIORITY.index(current)):
            states[item] = state
    return states


def _min_force_leg(record: dict) -> str | None:
    forces = (record.get("event_output") or {}).get("min_F_after_W_kN")
    return min(forces, key=forces.get) if forces else None


def line_values(record: dict, t4h_dir: Path) -> dict:
    """The report row of one line (module docstring)."""
    metric = path1.metrics(record, (t4h_dir,))
    force_N = path1._j2_value_N(metric)
    leg = _min_force_leg(record)
    row = {"variant": record["job"]["setting"], "key": d0.key_name(record["job"]),
           "final_phase": record.get("final_phase"),
           "t_first_ready_s": metric.get("t_ready"),
           "min_force_kN": None if force_N is None else round(force_N / 1e3, 3),
           "min_force_leg": leg, **own_item_states(metric),
           "commands_sha256": record.get("commands_sha256")}
    t4h_path = t4h_dir / record["t4h_file"]
    with np.load(t4h_path, allow_pickle=False) as data:
        row.update(level_hold(data))
        if leg is not None and record.get("t_event_s") is not None:
            row.update(event_leg_features(data, float(record["t_event_s"]), LEGS.index(leg)))
        split = p1_hold_split(data)
        row.update(split or {})
    return row


# ------------------------------------------------------------------------------ checks
def line_problems(record: dict, t4h_dir: Path) -> list[str]:
    """Definition, tag, checkout and record problems of one line (empty = clean)."""
    variant = record["job"]["setting"]
    problems = []
    expected = HydraulicOptions.from_dict(d0.D0_SETTINGS[variant][1])
    if record.get("hydraulic_options") != expected.to_dict():
        problems.append(f"options {record.get('hydraulic_options')} != {expected.to_dict()}")
    expected_tag = CONTROLLER_TAG_OF_BASE[d0.D0_BASE_SETTING[variant]]
    if record.get("controller_tag") != expected_tag:
        problems.append(f"controller_tag {record.get('controller_tag')} != {expected_tag}")
    block = record.get("d0") or {}
    if block.get("foreign_modules"):
        problems.append(f"modules from another checkout: {block['foreign_modules'][:3]}")
    has_gate = expected.line_fill_gate is not None
    with np.load(t4h_dir / record["t4h_file"], allow_pickle=False) as data:
        has_arrays = P1_FOUND_ARRAY in data.files
        found = int(data[P1_FOUND_ARRAY].sum()) if has_arrays else 0
    if has_gate and found == 0:
        problems.append("P1 variant without logged p1 reads")
    if not has_gate and has_arrays:
        problems.append("variant without P1 has p1 arrays")
    return problems


def read_lines(rows_path: Path, t4h_dir: Path) -> list[dict]:
    """The lines; refuses a file that is missing or a line whose T4h file is missing."""
    if not rows_path.is_file():
        raise InputError(f"--rows {rows_path} not found")
    lines = [json.loads(text) for text in rows_path.read_text(encoding="utf-8").splitlines()
             if text.strip()]
    for record in lines:
        if "error" in record:
            continue
        if not record.get("t4h_file") or not (t4h_dir / record["t4h_file"]).is_file():
            raise InputError(f"no T4h file for {record['job']} in {t4h_dir}")
    return lines


def reference_hashes(path: Path | None) -> dict[str, str]:
    """``key_name`` -> VBJ command hash of a reference ``j9_main.jsonl`` (empty without one)."""
    if path is None:
        return {}
    if not path.is_file():
        raise InputError(f"--reference {path} not found")
    hashes = {}
    for text in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(text)
        job = dict(record["job"])
        if job.pop("setting") == "VBJ" and d0.key_name(job) in d0.D0_KEYS:
            hashes[d0.key_name(job)] = record["commands_sha256"]
    return hashes


def summarize(lines: list[dict], t4h_dir: Path, references: dict[str, str],
              planned_jobs: list[dict]) -> dict:
    planned = {d0.run_v5.job_key(job) for job in planned_jobs}
    good = [record for record in lines if "error" not in record]
    found = [d0.run_v5.job_key(record["job"]) for record in good]
    checks = {"missing_jobs": sorted(planned - set(found)),
              "unplanned_jobs": sorted(set(found) - planned),
              "repeated_jobs": sorted({key for key in found if found.count(key) > 1}),
              "error_lines": [record["job"] for record in lines if "error" in record],
              "line_problems": {}, "d0_1_reference": {}}
    rows = []
    for record in good:
        problems = line_problems(record, t4h_dir)
        if problems:
            checks["line_problems"][f"{record['job']['setting']} {d0.key_name(record['job'])}"] \
                = problems
        rows.append(line_values(record, t4h_dir))
    for row in rows:
        if row["variant"] == "D0-1" and row["key"] in references:
            checks["d0_1_reference"][row["key"]] = (row["commands_sha256"]
                                                    == references[row["key"]])
    return {"rows": rows, "by_variant": _by_variant(rows), "checks": checks}


def _by_variant(rows: list[dict]) -> dict:
    out = {}
    for variant in d0.D0_SETTINGS:
        own = [row for row in rows if row["variant"] == variant]
        forces = [row["min_force_kN"] for row in own if row["min_force_kN"] is not None]
        out[variant] = {
            "lines": len(own),
            "item_fail_lines": {item: sum(row[item] == "fail" for row in own)
                                for item in J_ITEMS},
            "ready_lines": sum(row["final_phase"] == "ready" for row in own),
            "min_force_kN_min": min(forces) if forces else None,
            "held_fraction_max": max((row["held_fraction"] for row in own), default=None),
        }
    return out


def status_of(report: dict) -> str:
    checks = report["checks"]
    if checks["line_problems"] or not all(checks["d0_1_reference"].values()):
        return "setting_defect"
    if (checks["missing_jobs"] or checks["unplanned_jobs"] or checks["repeated_jobs"]
            or checks["error_lines"]):
        return "incomplete"
    return "written"


def write_csv(rows: list[dict], path: Path) -> None:
    columns: list[str] = []
    for row in rows:
        columns += [name for name in row if name not in columns]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, required=True, help="d0_plant_split.py output")
    parser.add_argument("--out", type=Path, required=True, help="report json (new file)")
    parser.add_argument("--reference", type=Path, default=None,
                        help="j9_main.jsonl of the reference run (D0-1 hash check)")
    parser.add_argument("--variants", default=None,
                        help="planned variants as in d0_plant_split.py (default all)")
    parser.add_argument("--keys", default=None,
                        help="planned keys as in d0_plant_split.py (default all)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    d0.install_d0_switches()  # the D0-3 options build only with the test-only permission
    try:
        if args.out.exists():
            raise InputError(f"--out {args.out} exists (a report is never overwritten)")
        try:
            planned = d0.d0_jobs(d0._names(args.variants, d0.D0_SETTINGS, "variants"),
                                 d0._names(args.keys, d0.D0_KEYS, "keys"))
        except ValueError as exc:
            raise InputError(str(exc)) from exc
        rows_path = args.rows.resolve()
        t4h_dir = rows_path.with_name(f"{rows_path.stem}_t4h")
        report = summarize(read_lines(rows_path, t4h_dir), t4h_dir,
                           reference_hashes(args.reference), planned)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_STOP
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    status = status_of(report)
    report = {"status": status, "rows_file": str(rows_path), **report}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    csv_path = args.out.with_suffix(".csv")
    write_csv(report["rows"], csv_path)
    print(json.dumps({"status": status, "lines": len(report["rows"]),
                      "line_problems": len(report["checks"]["line_problems"]),
                      "missing_jobs": len(report["checks"]["missing_jobs"]),
                      "out": str(args.out), "csv": str(csv_path)}), flush=True)
    return EXIT_WRITTEN if status == "written" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
