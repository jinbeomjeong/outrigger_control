"""436.9 edition 6 probe summary and share decision (``jp3_remedy_spec_v6.md`` 4.2, Q6-8).

Reads the ``ed6_probe.py`` lines (a design input before the seal, public; not a judgement).

Per line (``rows`` of the report and the CSV beside it): the D0 summary values of
``d0_plant_split_summary.line_values`` with the same definitions (minimum force, own J1 .. J5
states, first READY, final phase, LEVEL hold fractions, event-leg features including the
diagonal release delay ``other_leg_retract_delay_max_s``, the P1 hold split), the LEVEL stall
signature of erratum 8 8-3 (:func:`is_stall_signature`, a record there) and the edition 6
counts of the line's ``lsb_record`` (A(i) triggers and cap ends, A(ii) floors, B1 blocked
periods, B episodes).

Against V0 (per plant x arm group): every line is the VB side of the j9_main ``J_vs_V0`` table
(``jp3_j9main_judge._full_items``, the 436.8 path 1 J1 .. J11 items against the stored V0 line
of the same row and phase, a J item failing only where V0 passes it) plus the R15 worsening
rule (``r15_worsening``). A key fails when it has a ``fail`` item; an R15 worsening fails both
R15 keys of the group (the rule reads the row over its two phases). The readings (1) .. (3) of
the edition 5 judgement (spec 6.2) are not applied here: they are judge tool work (spec 8 Y-5).

Share decision (spec 4.2 / Q6-8 with the stats Q-E amendment, user decision 2026-11-23):

* For each component X the arm without it is compared with the full arm ``a1a2b`` (failed
  keys against V0 over the five plants): A(i) -> ``a2b``, A(ii) -> ``a1b``, B (B1 + B3) ->
  ``a1a2``, B3 -> ``a1a2b1`` (spec revision 1 4.2, Q6-12).
* X is kept, ties included. X is dropped only when (a) it acted nowhere in the arms that have
  it, the hold variant left out (A(i): ``a1_raised_periods``, A(ii): ``a2_raised_periods``,
  B: B1 blocked periods plus B3 pre-twist periods plus B2 early starts, B3: its pre-twist
  periods; all 0), or (b) the arm without it has fewer failed keys than the full arm.
* B3 (stats s30, user decision 2026-11-23): dropped only when ``a1a2b1`` has at least
  :data:`B3_DROP_MARGIN` fewer failed keys than the full arm (no activation rule); and with B.
* A(i) is also kept when ``a2b`` has more stall-signature lines on the ``c04`` plant than the
  full arm (spec 4.2 "단").
* The hold variant ``a1a2bh`` (arm 7) joins the sealed range only when it has fewer failed
  keys than the full arm (``share.hold_variant.include``).
* The decision is ``not_judgeable`` when a compared group has a missing line, a line without
  its V0 reference, or a not-judgeable item.

======  ===================  ============================================================
exit    status               meaning
======  ===================  ============================================================
0       ``written``          report written, every check clean, the share decided
2       ``setting_defect``   report written; a line's options, tag, components, records or
                             checkout differ from the probe definition (``checks``)
2       ``incomplete``       report written; a planned job is missing, repeated, or has an
                             error line
2       ``not_judgeable``    report written; a share comparison cannot be made
2       ``input_error``      no report: missing input, another V0 sha256, a line without
                             its T4h, or an existing ``--out``
3       ``tool_error``       a tool error
======  ===================  ============================================================
(status order: setting_defect > incomplete > not_judgeable > written)

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed6_probe_share.py --rows <ed6_probe.jsonl>
      --v0 <stored v5/main.jsonl> --v0-sha256 <sha> --out <report.json>
      [--plants ...] [--arms ...] [--keys ...]
The T4h records are read from ``<rows stem>_t4h/``. The stdout's last line is JSON with
``status``, the counts and the report path.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split_summary as d0_summary  # noqa: E402
import ed6_probe as probe  # noqa: E402  (also puts the harness folders on sys.path)

from outrigger_sim.hydraulics.v5_options import HydraulicOptions  # noqa: E402

EXIT_WRITTEN, EXIT_STOP, EXIT_TOOL = 0, 2, 3
PROBE_TAG = "final_C4G2_P3W_LAS_K1_LSB"
"""Every probe line: ③ revision 6 with LAS-b, K1 and the edition 6 suffix."""
STALL_WINDOW_S = 20.0
STALL_WINDOW_TOLERANCE_S = 1e-6
STALL_SPAN_M = 1e-3
STALL_LAST_PHASES = ("level", "probe")
FAULT_PHASES = ("fault", "fault_reground")
"""Erratum 8 8-3 values (``jp3_12b_judge`` ``STALL_*``; a unit test keeps them equal)."""
LSB_FOUND_ARRAY = "lsb_read_found"
FULL_ARM = "a1a2b"
HOLD_ARM = "a1a2bh"
ARM_WITHOUT = {"A_i": "a2b", "A_ii": "a1b", "B": "a1a2", "B3": "a1a2b1"}
"""The full arm without the component (spec revision 1 4.2)."""
COMPONENT_PARTS = {"A_i": ("A_i",), "A_ii": ("A_ii",), "B": ("B1", "B3"), "B3": ("B3",)}
"""The ``lsb_components`` names a decided component stands for."""
ACTIVATION_KEYS = {"A_i": ("lsb_a1_raised_periods",), "A_ii": ("lsb_a2_raised_periods",),
                   "B": ("lsb_b1_blocked_periods", "lsb_b3_periods", "lsb_b2_early_starts"),
                   "B3": ("lsb_b3_periods",)}
"""Row counts that say a component acted (changed or held a command)."""
DECIDED = ("A_i", "A_ii", "B", "B3")
B3_DROP_MARGIN = 2
"""Stats s30: B3 goes only when leaving it out fails at least this many keys fewer."""
BASE_ARMS = ("a2", "b", "a2b", "a1b", "a1a2", "a1a2b", "a1a2b1")
DEADBAND_PLANT = "c04"
R15_KEYS = ("R15_o0.0", "R15_o0.05")


class InputError(Exception):
    """No report can be written (exit 2)."""


# ------------------------------------------------------------------------------ line values
def is_stall_signature(data) -> bool:
    """Erratum 8 8-3 on a T4h record: no READY read, no fault phase entry, the last phase
    ``level`` or ``probe`` (lower case), every leg's ``motor_stroke_m`` span below 1 mm over
    the reads at or after the last ``t_s`` - 20 s - 1e-6 s."""
    phases = [str(value).lower() for value in data["phase"]]
    times = np.asarray(data["t_s"], float)
    strokes = np.asarray(data["motor_stroke_m"], float)
    if "ready" in phases or any(phase in FAULT_PHASES for phase in phases):
        return False
    if not phases or phases[-1] not in STALL_LAST_PHASES:
        return False
    window = times >= times[-1] - STALL_WINDOW_S - STALL_WINDOW_TOLERANCE_S
    spans = strokes[window].max(axis=0) - strokes[window].min(axis=0)
    return bool((spans < STALL_SPAN_M).all())


def lsb_counts(record: dict) -> dict:
    """Run totals of the line's ``lsb_record`` (record only)."""
    record_block = record.get("lsb_record") or {}
    summed = ("a1_triggers", "a1_cap_reached", "a1_raised_periods", "a2_floors",
              "a2_raised_periods", "a2_hold_periods", "b1_blocked_periods", "b3_periods")
    totals = {f"lsb_{name}": 0 for name in summed}
    totals["lsb_b2_early_starts"] = 0
    for counts in (record_block.get("legs") or {}).values():
        for name in summed:
            totals[f"lsb_{name}"] += counts[name]
        totals["lsb_b2_early_starts"] += len(counts["b2_early_starts_s"])
    totals["lsb_b_episodes"] = len(record_block.get("b_episodes") or [])
    return totals


def line_values(record: dict, t4h_dir: Path) -> dict:
    plant, arm = probe.split_setting_name(record["job"]["setting"])
    row = {"plant": plant, "arm": arm, **d0_summary.line_values(record, t4h_dir)}
    row.pop("variant", None)
    with np.load(t4h_dir / record["t4h_file"], allow_pickle=False) as data:
        row["stall_signature"] = is_stall_signature(data)
    row.update(lsb_counts(record))
    return row


# ------------------------------------------------------------------------------ checks
def line_problems(record: dict, t4h_dir: Path, parameters: dict) -> list[str]:
    """Definition, tag, components, record and checkout problems of one line."""
    setting = record["job"]["setting"]
    _, arm = probe.split_setting_name(setting)
    problems = []
    expected = HydraulicOptions.from_dict(probe.probe_settings(parameters)[setting][1])
    if record.get("hydraulic_options") != expected.to_dict():
        problems.append(f"options {record.get('hydraulic_options')} != {expected.to_dict()}")
    if record.get("controller_tag") != PROBE_TAG:
        problems.append(f"controller_tag {record.get('controller_tag')} != {PROBE_TAG}")
    if record.get("lsb_components") != list(probe.ARMS[arm]):
        problems.append(f"lsb_components {record.get('lsb_components')} != "
                        f"{list(probe.ARMS[arm])}")
    if (record.get("lsb_record") or {}).get("components") != list(probe.ARMS[arm]):
        problems.append("lsb_record components differ from the arm")
    block = record.get("ed6_probe") or {}
    if block.get("foreign_modules"):
        problems.append(f"modules from another checkout: {block['foreign_modules'][:3]}")
    with np.load(t4h_dir / record["t4h_file"], allow_pickle=False) as data:
        found = data[LSB_FOUND_ARRAY] if LSB_FOUND_ARRAY in data.files else None
        has_p1 = d0_summary.P1_FOUND_ARRAY in data.files
    if found is None or not found.size or not found.all():
        problems.append("lsb_* arrays missing or not on every T4h read")
    if not has_p1:
        problems.append("p1_* arrays missing")
    return problems


def read_lines(rows_path: Path, t4h_dir: Path) -> list[dict]:
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


def run_parameters(lines: list[dict]) -> tuple[dict, list[str]]:
    """The ``--lsb-param`` values of the run (one set for every line) and the problems."""
    found = {json.dumps((line.get("ed6_probe") or {}).get("lsb_parameters") or {},
                        sort_keys=True) for line in lines if "error" not in line}
    if len(found) > 1:
        return {}, [f"lines with {len(found)} different lsb_parameters"]
    return (json.loads(found.pop()) if found else {}), []


# ------------------------------------------------------------------------------ V0 pairing
def _v0_metric_rows(v0_path: Path, v0_sha256: str) -> list[dict]:
    """Path 1 metrics of the stored V0 lines (``jp3_j9main_judge.stored_v0_rows``).

    Raises:
        InputError: Another sha256 or no V0 line.
    """
    import jp3_j9main_judge as j9judge

    try:
        rows = j9judge.stored_v0_rows(v0_path, v0_sha256)
    except j9judge.NotJudgeable as exc:
        raise InputError(str(exc)) from exc
    import judge4368_common as common

    folders = tuple(common.t4h_folders(v0_path, rows))
    return j9judge._metric_rows(rows, folders, relabel=False)


def group_judgement(group_lines: list[dict], t4h_dir: Path, v0_rows: list[dict]) -> dict:
    """The ``J_vs_V0`` items of one plant x arm group and its failed keys."""
    import jp3_j9main_judge as j9judge
    import judge_stage1_4368 as path1

    metrics = []
    for record in group_lines:
        metric = path1.metrics(record, (t4h_dir,))
        metric["setting"] = path1.JUDGED_SETTING
        metric["key"] = probe.d0.key_name(record["job"])
        metrics.append(metric)
    rows_by = path1._by_setting(metrics + v0_rows)
    table = j9judge._full_items(rows_by, (path1.JUDGED_SETTING,), j9judge.V0_SETTING)
    part = table[path1.JUDGED_SETTING]
    key_of = {(metric["row"], metric["phase"]): metric["key"] for metric in metrics}
    failed = sorted({key_of[(item["row"], item["phase"])] for item in part["items"]
                     if item["kind"] == "fail"})
    r15 = j9judge.r15_worsening(rows_by)
    if r15["failures"]:
        failed = sorted(set(failed) | {key for key in R15_KEYS if key in key_of.values()})
    unjudgeable = [item for item in part["items"] if item["kind"] == "not_judgeable"]
    unjudgeable += j9judge.r15_not_judgeable(r15)
    return {"lines": len(group_lines), "failed_keys": failed,
            "fail_items": [item for item in part["items"] if item["kind"] == "fail"],
            "no_reference": part["no_reference"], "not_judgeable_items": unjudgeable,
            "r15_worsening": {key: r15[key] for key in ("pairs", "state") if key in r15}}


def share_decision(groups: dict, rows: list[dict], plants: tuple[str, ...]) -> dict:
    """Spec 4.2 / Q6-8 with the stats Q-E amendment (module docstring)."""
    def failed_count(arm: str) -> int | None:
        counts = [len(groups[(plant, arm)]["failed_keys"]) for plant in plants
                  if (plant, arm) in groups]
        return sum(counts) if len(counts) == len(plants) else None

    def stall_lines(plant: str, arm: str) -> int:
        return sum(row["stall_signature"] for row in rows
                   if row["plant"] == plant and row["arm"] == arm)

    def activations(component: str) -> int:
        return sum(row[key] for row in rows if row["arm"] in BASE_ARMS
                   and set(COMPONENT_PARTS[component]) & set(probe.ARMS[row["arm"]])
                   for key in ACTIVATION_KEYS[component])

    problems = [f"{plant} {arm}: {reason}" for (plant, arm), group in groups.items()
                for reason, has_it in (("no_reference", group["no_reference"]),
                                       ("not-judgeable items", group["not_judgeable_items"]))
                if has_it]
    counts = {arm: failed_count(arm) for arm in probe.ARMS}
    compared = (FULL_ARM, *ARM_WITHOUT.values())
    problems += [f"arm {arm}: not every plant has its group" for arm in compared
                 if counts[arm] is None]
    if DEADBAND_PLANT not in plants:
        problems.append(f"no {DEADBAND_PLANT} plant: A(i) cannot be decided")
    decision: dict = {"failed_keys_by_arm": counts, "problems": problems,
                      "full_arm": FULL_ARM, "components": {}}
    if problems:
        decision["status"] = "not_judgeable"
        return decision
    for component, arm in ARM_WITHOUT.items():
        decision["components"][component] = _component_decision(
            component, arm, counts, activations(component))
    stall_without = stall_lines(DEADBAND_PLANT, ARM_WITHOUT["A_i"])
    stall_full = stall_lines(DEADBAND_PLANT, FULL_ARM)
    a1 = decision["components"]["A_i"]
    a1["c04_stall_lines"] = {ARM_WITHOUT["A_i"]: stall_without, FULL_ARM: stall_full}
    if stall_without > stall_full and not a1["keep"]:
        a1.update(keep=True, rule=a1["rule"] + f"; kept: {DEADBAND_PLANT} stall lines "
                                               f"{stall_without} > {stall_full}")
    b3 = decision["components"]["B3"]
    if b3["keep"] and not decision["components"]["B"]["keep"]:
        b3.update(keep=False, rule=b3["rule"] + "; dropped with B")
    if counts.get(HOLD_ARM) is not None:
        decision["hold_variant"] = {"failed_keys": counts[HOLD_ARM],
                                    "full_arm_failed_keys": counts[FULL_ARM],
                                    "include": counts[HOLD_ARM] < counts[FULL_ARM],
                                    "c04_stall_lines": stall_lines(DEADBAND_PLANT, HOLD_ARM)}
    decision["kept"] = [name for name in DECIDED if decision["components"][name]["keep"]]
    decision["status"] = "decided"
    return decision


def _component_decision(component: str, arm: str, counts: dict, activation: int) -> dict:
    """Keep (ties too) unless the component never acted or leaving it out fails fewer keys
    (B3: at least :data:`B3_DROP_MARGIN` fewer, no activation rule)."""
    without, full = counts[arm], counts[FULL_ARM]
    if component == "B3":
        keep = without > full - B3_DROP_MARGIN
        verdict = "kept" if keep else "dropped"
        return {"keep": keep, "activation": activation,
                "rule": f"{verdict}: failed keys {arm} {without} vs {FULL_ARM} {full} "
                        f"(drop at {B3_DROP_MARGIN} fewer)"}
    if activation == 0:
        return {"keep": False, "rule": f"dropped: no activation ({activation})",
                "activation": activation}
    if without < full:
        return {"keep": False, "rule": f"dropped: failed keys {arm} {without} < {FULL_ARM} "
                                       f"{full}", "activation": activation}
    return {"keep": True, "rule": f"kept: failed keys {arm} {without} >= {FULL_ARM} {full}",
            "activation": activation}


def summarize(lines: list[dict], t4h_dir: Path, v0_rows: list[dict],
              planned_jobs: list[dict], plants: tuple[str, ...]) -> dict:
    run_v5 = probe.run_v5
    planned = {run_v5.job_key(job) for job in planned_jobs}
    good = [record for record in lines if "error" not in record]
    found = [run_v5.job_key(record["job"]) for record in good]
    parameters, parameter_problems = run_parameters(lines)
    checks = {"missing_jobs": sorted(planned - set(found)),
              "unplanned_jobs": sorted(set(found) - planned),
              "repeated_jobs": sorted({key for key in found if found.count(key) > 1}),
              "error_lines": [record["job"] for record in lines if "error" in record],
              "line_problems": {}, "parameter_problems": parameter_problems}
    rows = []
    for record in good:
        problems = line_problems(record, t4h_dir, parameters)
        if problems:
            name = f"{record['job']['setting']} {probe.d0.key_name(record['job'])}"
            checks["line_problems"][name] = problems
        rows.append(line_values(record, t4h_dir))
    grouped: dict[tuple[str, str], list[dict]] = {}
    for record in good:
        grouped.setdefault(probe.split_setting_name(record["job"]["setting"]), []).append(record)
    groups = {key: group_judgement(group, t4h_dir, v0_rows) for key, group in grouped.items()}
    share = share_decision(groups, rows, plants)
    return {"lsb_parameters": parameters, "rows": rows, "checks": checks,
            "groups": {f"{plant} {arm}": group for (plant, arm), group in groups.items()},
            "share": share}


def status_of(report: dict) -> str:
    checks = report["checks"]
    if checks["line_problems"] or checks["parameter_problems"]:
        return "setting_defect"
    if (checks["missing_jobs"] or checks["unplanned_jobs"] or checks["repeated_jobs"]
            or checks["error_lines"]):
        return "incomplete"
    if report["share"]["status"] != "decided":
        return "not_judgeable"
    return "written"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, required=True, help="ed6_probe.py output")
    parser.add_argument("--v0", type=Path, required=True, help="stored v5 main.jsonl")
    parser.add_argument("--v0-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True, help="report json (new file)")
    parser.add_argument("--plants", default=None, help="planned plants (default all)")
    parser.add_argument("--arms", default=None, help="planned arms (default all)")
    parser.add_argument("--keys", default=None, help="planned keys (default all)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    probe.install_probe_switches()
    try:
        if args.out.exists():
            raise InputError(f"--out {args.out} exists (a report is never overwritten)")
        try:
            plants = probe.d0._names(args.plants, probe.PLANTS, "plants")
            planned = probe.probe_jobs(plants, probe.d0._names(args.arms, probe.ARMS, "arms"),
                                       probe.d0._names(args.keys, probe.d0.D0_KEYS, "keys"))
        except ValueError as exc:
            raise InputError(str(exc)) from exc
        rows_path = args.rows.resolve()
        t4h_dir = rows_path.with_name(f"{rows_path.stem}_t4h")
        lines = read_lines(rows_path, t4h_dir)
        report = summarize(lines, t4h_dir, _v0_metric_rows(args.v0, args.v0_sha256), planned,
                           plants)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_STOP
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    status = status_of(report)
    report = {"status": status, "rows_file": str(rows_path),
              "v0": {"path": str(args.v0), "sha256": args.v0_sha256}, **report}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, default=str)
    csv_path = args.out.with_suffix(".csv")
    d0_summary.write_csv(report["rows"], csv_path)
    print(json.dumps({"status": status, "lines": len(report["rows"]),
                      "share": report["share"]["status"],
                      "line_problems": len(report["checks"]["line_problems"]),
                      "missing_jobs": len(report["checks"]["missing_jobs"]),
                      "out": str(args.out), "csv": str(csv_path)}), flush=True)
    return EXIT_WRITTEN if status == "written" else EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
