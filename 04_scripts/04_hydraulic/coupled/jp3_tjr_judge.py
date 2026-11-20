"""436.9 edition 4a J4a-15 (``jp3_remedy_spec.md`` 5.5 T-JR-10 .. T-JR-15, 13.9; addendum 4a-2
B4, R9, B2, B3): the batch judges of the T8 pairs and of Dg-3, and the record bundle.

Sub-commands:

``t8``       T-JR-10 (VBH against the stored VB line of the same job) and T-JR-11 (VBJ against
             VBJ0) on the run_v5 batch ``j9_t8`` (the 22 jobs of the revision 8 7.2 rule):
             ``commands_sha256`` equal on exactly 22 pairs each. The 20-row T-P3-5 sample has no
             list in the repository (``v5_criteria_rev8.md`` 7.2): without ``--t-p3-5-jobs`` (a
             file of exactly 20 job objects, one JSON per line) that part, and so the bundle, is
             not judgeable.
``t12``      T-JR-12 (13.9) of one bundle: ``--bundle VBH`` = VBH against the stored H-6 (rev 4),
             ``--bundle VBJ`` = VBJ against VBJ0. Exactly 135 pairs by plain key, exactly 1 L2
             (normal grade) line; failure: a key whose base line passes (pass / flag of
             ``r79_sensor_judge``, ``h8_noise_judge_4368.grade_line``) and whose new line fails, a
             new FAULT name, a first READY more than 30 s after the base one (a new line that never
             reaches READY counts as over). VBJ: J-P3 (``j_p3_judgement_rev5``, 1 judged row
             expected, the record's sensor grade) and the P4 evidence (4a-2 B2: VBJ needs
             ``R79_ROD_MODEL=plant_truth``). Records: the R5-7 columns of 5.5 with the
             ``ret_after_gate_s`` resolution (R9).
``records``  T-JR-13 .. T-JR-15 (records, 4a-2 B4): Dg-2 replay reports (runs, errors), the
             ``lock_window_alignment`` J11 ``n_late`` of the Dg-3 lines, and per-lock records
             (``relock_step_over_1bar_count``, seed rows) with the seed net force of 4a-2 3.4
             (``net_force_seed_step_N`` <= 1 N, its not-judgeable rules reported).

Exit codes and ``status`` (all sub-commands):

======  =================  ===================================================================
exit    status             meaning
======  =================  ===================================================================
0       ``pass``           the bundle passes (``records``: written, nothing not judgeable)
1       ``failed``         a failure of 5.5 / 13.9 (T8 hash, pass -> fail, new FAULT, READY,
                           J-P3 H-7); ``records`` never fails
2       ``not_judgeable``  a pair without a result, another pair or L2 count, a missing key
                           or grade, the T-P3-5 list missing; an existing ``--out``
2       ``setting_defect`` a wrong rev 5 identity or P4 evidence (outranks the others)
3       ``error``          an unexpected input error
======  =================  ===================================================================

The report records the sha256 of every input. The stdout's last line is JSON with ``status``,
the problem counts and the report path only.

Batch commands (dynamics-dev, project root; the main session launches them):
  run_v5.py j9_t8 --out <folder>/j9_t8.jsonl --mask <hex>                     (T-JR-10 / 11)
  for VBH / VBJ / VBJ0 (T-JR-12, the 135 stored dg3 keys of resume_k1/h6_dg3_v4on.json):
    env R79_V5_SETTING=<setting> R79_T4H_DIR=<folder>/<setting>_t4h LAS_T3_DG3_LAS=on
        LAS_T3_DG3_K1=on LAS_T3_DG3_P3=on [R79_ROD_MODEL=plant_truth for VBJ / VBJ0]
    las_t3_dg3.py <root> run <folder>/dg3_<setting>.json --levels L2,L3 --keys "<keys>"
  then r79_sensor_judge.py judge <judge.json> <dg3 file> <H-8 VB L1 extract> --s4-late-loc
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_baseline_compare as compare  # noqa: E402
from j_p3_inputs import rod_reading_evidence_problems  # noqa: E402

T8_JOBS = 22
T_P3_5_JOBS = 20
T8_PAIRS = {"T-JR-10": ("VBH", "VB"), "T-JR-11": ("VBJ", "VBJ0")}
"""T-JR-10 compares VBH with the stored VB line; T-JR-11 VBJ with VBJ0 of the same batch."""
DG3_PAIRS = 135
DG3_L2_LINES = 1
READY_DELAY_LIMIT_S = 30.0
BUNDLE_BASE = {"VBH": "stored H-6 (rev 4)", "VBJ": "VBJ0"}
NEW_FAULT_PREFIX = "FAULT"
RET_AFTER_GATE_RESOLUTION = (
    "read grid 0.1 s: ret_after_gate_s = first RET read - T (the read before it), so it differs "
    "from the gate-opening sub-step by up to 0.1 s; a record, not a judged column (4a-2 R9)")
RECORD_COLUMNS = ("retract_tracker_dominated_reads", "retract_tracker_over_tol_reads",
                  "retract_tracker_false_drop_reads")


def _read_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _job_identity(job: dict) -> str:
    return json.dumps({k: v for k, v in sorted(job.items()) if k != "setting"}, sort_keys=True)


# --- t8 (T-JR-10 / T-JR-11) -----------------------------------------------------------------

def judge_t8(stored: list[dict], rerun: list[dict], sample_jobs: list[dict] | None
             ) -> tuple[dict, compare.Problems]:
    """T-JR-10 / T-JR-11 (module docstring)."""
    problems = compare.Problems()
    lines = {"stored": _by_setting_job(stored, problems, "stored"),
             "rerun": _by_setting_job(rerun, problems, "rerun")}
    report = {}
    for name, (new_setting, base_setting) in T8_PAIRS.items():
        base_lines = lines["stored" if name == "T-JR-10" else "rerun"].get(base_setting, {})
        new_lines = lines["rerun"].get(new_setting, {})
        report[name] = {"22_jobs": _t8_part(name, new_lines, base_lines, None, problems)}
        if sample_jobs is None:
            problems.not_judgeable.append(
                f"{name}: the T-P3-5 20-row list is not in the repository (rev8 7.2)")
            report[name]["20_rows"] = "not judgeable: no list"
        else:
            keys = [_job_identity(job) for job in sample_jobs]
            report[name]["20_rows"] = _t8_part(name, new_lines, base_lines, keys, problems)
    return report, problems


def _by_setting_job(rows: list[dict], problems: compare.Problems,
                    label: str) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for row in rows:
        if "error" in row:
            problems.not_judgeable.append(f"{label}: error row {row['job']}")
            continue
        setting_lines = out.setdefault(row["job"]["setting"], {})
        key = _job_identity(row["job"])
        if key in setting_lines:
            problems.not_judgeable.append(f"{label}: two lines of {row['job']}")
        setting_lines[key] = row
    return out


def _t8_part(name: str, new_lines: dict[str, dict], base_lines: dict[str, dict],
             keys: list[str] | None, problems: compare.Problems) -> dict:
    """One count of 5.5 T8 (22 jobs, or the 20 listed ones): every pair with a result."""
    expected = T8_JOBS if keys is None else T_P3_5_JOBS
    keys = sorted(new_lines) if keys is None else keys
    if len(keys) != expected or len(set(keys)) != expected:
        problems.not_judgeable.append(f"{name}: {len(keys)} jobs, {expected} expected")
        return {"pairs": len(keys)}
    missing = [key for key in keys if key not in new_lines or key not in base_lines]
    if missing:
        problems.not_judgeable.append(f"{name}: {len(missing)} pairs without a result")
        return {"pairs": len(keys) - len(missing), "missing": missing[:10]}
    differing = [key for key in keys
                 if new_lines[key]["commands_sha256"] != base_lines[key]["commands_sha256"]]
    if differing:
        problems.failures.append(f"{name}: {len(differing)}/{expected} command hashes differ")
    return {"pairs": expected, "equal": expected - len(differing), "differing": differing[:10]}


# --- t12 (T-JR-12) --------------------------------------------------------------------------

def judge_t12(bundle: str, base: dict, base_judge: dict, new: dict, new_judge: dict
              ) -> tuple[dict, compare.Problems]:
    """T-JR-12 of one bundle (module docstring)."""
    import h8_noise_judge_4368 as h8

    problems = compare.Problems()
    base_lines = _dg3_lines(base["results"], "base", problems)
    new_lines = _dg3_lines(new["results"], "new", problems)
    if len(base_lines) != DG3_PAIRS or set(base_lines) != set(new_lines):
        problems.not_judgeable.append(f"{bundle}: {len(base_lines)} base / {len(new_lines)} new "
                                      f"keys, {DG3_PAIRS} equal keys expected")
        return {"pairs": len(set(base_lines) & set(new_lines))}, problems
    l2_lines = sum(line.get("level") == "L2" for line in new_lines.values())
    if l2_lines != DG3_L2_LINES:
        problems.not_judgeable.append(f"{bundle}: {l2_lines} L2 lines, {DG3_L2_LINES} expected")
    base_grades = h8.grade_lines(list(base_lines.values()), base_judge)
    new_grades = h8.grade_lines(list(new_lines.values()), new_judge)
    report = {"bundle": bundle, "base": BUNDLE_BASE[bundle], "pairs": DG3_PAIRS,
              "pass_to_fail": _pass_to_fail(base_grades, new_grades, h8, problems),
              "new_fault": _new_faults(base_lines, new_lines, problems),
              "ready_over_30_s": _late_ready(base_lines, new_lines, problems)}
    for key in ("pass_to_fail", "new_fault", "ready_over_30_s"):
        if report[key]:
            problems.failures.append(f"{bundle}: {len(report[key])} {key} keys")
    for key, line in new_lines.items():
        problems.setting_defects += [f"{key}: {text}" for text in _dg3_identity(line)]
        problems.setting_defects += [f"{key}: {text}" for text in rod_reading_evidence_problems(
            line.get("hydraulics_record"), line.get("hydraulic_options"))]
    if bundle == "VBJ":
        report["J-P3"] = _dg3_j_p3(list(new_lines.values()), problems)
    report["records"] = _r5_7_records(list(new_lines.values()))
    return report, problems


def _dg3_lines(results: list[dict], label: str, problems: compare.Problems) -> dict[str, dict]:
    import h8_noise_judge_4368 as h8

    lines = {}
    for run in results:
        key = h8.plain_key(run["key"])
        if "error" in run:
            problems.not_judgeable.append(f"{label} {key}: error line (no result)")
            continue
        lines[key] = run
    return lines


def _pass_to_fail(base_grades: dict, new_grades: dict, h8, problems: compare.Problems) -> list:
    passing = (h8.GRADE_PASS, h8.GRADE_FLAG)
    keys = []
    for key, grade in new_grades.items():
        old = base_grades.get(key)
        if old is None or h8.GRADE_NOT_JUDGEABLE in (grade["grade"], old["grade"]):
            problems.not_judgeable.append(f"{key}: no judge grade")
            continue
        if old["grade"] in passing and grade["grade"] == h8.GRADE_FAIL:
            keys.append(key)
    return sorted(keys)


def _fault_names(line: dict) -> set[str] | None:
    names = (line.get("r79") or {}).get("warn_fault")
    return None if names is None else {name for name in names
                                       if str(name).startswith(NEW_FAULT_PREFIX)}


def _new_faults(base_lines: dict, new_lines: dict, problems: compare.Problems) -> list:
    keys = []
    for key, line in new_lines.items():
        mine, theirs = _fault_names(line), _fault_names(base_lines[key])
        if mine is None or theirs is None:
            problems.not_judgeable.append(f"{key}: no warn_fault record")
        elif mine - theirs:
            keys.append(key)
    return sorted(keys)


def _ready_s(line: dict) -> float | None:
    return (line.get("base") or {}).get("t_ready_s")


def _late_ready(base_lines: dict, new_lines: dict, problems: compare.Problems) -> list:
    """13.9: first READY later than the base one + 30 s; a new line without READY is late."""
    keys = []
    for key, line in new_lines.items():
        base_s, new_s = _ready_s(base_lines[key]), _ready_s(line)
        if base_s is None:
            problems.not_judgeable.append(f"{key}: the base line has no READY")
        elif new_s is None or new_s > base_s + READY_DELAY_LIMIT_S:
            keys.append(key)
    return sorted(keys)


def _dg3_identity(line: dict) -> list[str]:
    check = (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}
    if check.get("rule_revision") != 5:
        return []
    return [f"{key} {check.get(key)!r}" for key, value in compare.DEFAULT_IDENTITY.items()
            if check.get(key) != value]


def _dg3_j_p3(lines: list[dict], problems: compare.Problems) -> dict:
    """J-P3 of the VBJ bundle: exactly 1 judged (normal grade) row (13.9)."""
    from outrigger_sim.control.extend_start_bound import j_p3_judgement_rev5

    records = [(line.get("hydraulics_record") or {}).get("extend_bound_check") for line in lines]
    rods = [bool(line.get("has_rod_reading", True)) for line in lines]
    judgement = j_p3_judgement_rev5(records, rods, [False] * len(lines),
                                    expected_judged_runs=DG3_L2_LINES)
    status = judgement["status"]
    if status == "H-7":
        problems.failures.append("VBJ: J-P3 H-7")
    elif status == "setting_defect":
        problems.setting_defects.append("VBJ: J-P3 setting defect")
    elif status != "pass":
        problems.not_judgeable.append(f"VBJ: J-P3 {status}")
    return {key: judgement[key] for key in ("status", "runs", "runs_judged", "runs_by_case")}


def _r5_7_records(lines: list[dict]) -> dict:
    """5.5 records of the R5-7 term (sums over the lines) with the R9 resolution note."""
    sums = dict.fromkeys(RECORD_COLUMNS, 0)
    after = []
    for line in lines:
        check = (line.get("hydraulics_record") or {}).get("extend_bound_check") or {}
        for column in RECORD_COLUMNS:
            sums[column] += int(sum(check.get(column) or []))
        after += [row.get("ret_after_gate_s") for row in check.get("retract_tracker_stretch_log")
                  or [] if row.get("ret_after_gate_s") is not None]
    return {**sums, "ret_after_gate_s_values": len(after),
            "ret_after_gate_s_max": max(after) if after else None,
            "ret_after_gate_s_resolution": RET_AFTER_GATE_RESOLUTION}


# --- records (T-JR-13 .. 15) ----------------------------------------------------------------

def judge_records(replays: list[dict], dg3_files: list[dict], lock_rows: list[dict]
                  ) -> tuple[dict, compare.Problems]:
    """T-JR-13 .. 15 records (module docstring); only the seed net force rules of 4a-2 3.4
    can make the bundle not judgeable."""
    problems = compare.Problems()
    seed_rows = [_lock_record(row) for row in lock_rows]
    for row in seed_rows:
        if row["seed"]["not_judgeable"] is not None:
            problems.not_judgeable.append(f"T-JR-15 {row['setting']}: "
                                          f"{row['seed']['not_judgeable']}")
    if lock_rows and not sum(row["seed"]["rows"] for row in seed_rows):
        problems.not_judgeable.append("T-JR-15: zero seed rows over the rows (4a-2 3.4)")
    report = {"T-JR-13": [{"runs": replay.get("runs"), "runs_over": replay.get("runs_over"),
                           "J-P3": (replay.get("J-P3") or {}).get("status")}
                          for replay in replays],
              "T-JR-14": [_alignment_record(line) for document in dg3_files
                          for line in document.get("results") or []],
              "T-JR-15": seed_rows,
              "T-JR-15_seed_rows_over_1N": sum(row["seed"]["over_1N_rows"] for row in seed_rows)}
    return report, problems


def _alignment_record(line: dict) -> dict:
    alignment = line.get("lock_window_alignment") or {}
    late = alignment.get("n_late_fallback_by_leg") or {}
    return {"key": line.get("key"), "n_late_fallback_by_leg": late,
            "n_late_over_0": any((value or 0) > 0 for value in late.values())}


def _lock_record(row: dict) -> dict:
    """T-JR-15 per row: relock counts and the 3.4 seed force check of its seed rows."""
    record = row.get("hydraulics_record") or {}
    return {"setting": (row.get("job") or {}).get("setting") or row.get("key"),
            "relock_step_over_1bar_count": record.get("relock_step_over_1bar_count"),
            "p1_retract_seed_count": record.get("p1_retract_seed_count"),
            "p1_retract_seed_step_max_bar": record.get("p1_retract_seed_step_max_bar"),
            "seed": compare.seed_force_check(record)}


# --- command line ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    t8 = commands.add_parser("t8")
    t8.add_argument("--out", type=Path, required=True)
    t8.add_argument("--stored", type=Path, required=True,
                    help="stored VB lines of the current controller (resume_k1/h10_reuse_rerun)")
    t8.add_argument("--rerun", type=Path, required=True, help="run_v5 j9_t8 output")
    t8.add_argument("--t-p3-5-jobs", type=Path, default=None)
    t12 = commands.add_parser("t12")
    t12.add_argument("--out", type=Path, required=True)
    t12.add_argument("--bundle", choices=sorted(BUNDLE_BASE), required=True)
    for name in ("base", "base-judge", "new", "new-judge"):
        t12.add_argument(f"--{name}", type=Path, required=True)
    records = commands.add_parser("records")
    records.add_argument("--out", type=Path, required=True)
    records.add_argument("--replay", type=Path, nargs="*", default=[])
    records.add_argument("--dg3", type=Path, nargs="*", default=[])
    records.add_argument("--lock-rows", type=Path, nargs="*", default=[],
                         help="run_v5 jsonl files (VBJ 135 rows, case E)")
    return parser


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(args: argparse.Namespace) -> tuple[dict, compare.Problems, list[Path]]:
    if args.command == "t8":
        sample = None if args.t_p3_5_jobs is None else _read_json_lines(args.t_p3_5_jobs)
        report, problems = judge_t8(_read_json_lines(args.stored), _read_json_lines(args.rerun),
                                    sample)
        inputs = [args.stored, args.rerun, *([args.t_p3_5_jobs] if args.t_p3_5_jobs else [])]
        return report, problems, inputs
    if args.command == "t12":
        report, problems = judge_t12(args.bundle, _read_json(args.base),
                                     _read_json(args.base_judge), _read_json(args.new),
                                     _read_json(args.new_judge))
        return report, problems, [args.base, args.base_judge, args.new, args.new_judge]
    lock_rows = [row for path in args.lock_rows for row in _read_json_lines(path)]
    report, problems = judge_records([_read_json(path) for path in args.replay],
                                     [_read_json(path) for path in args.dg3], lock_rows)
    return report, problems, [*args.replay, *args.dg3, *args.lock_rows]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists (a new report never overwrites one)")
    inputs: list[Path] = []
    try:
        report, problems, inputs = _run(args)
        report.update(problems.as_dict())
        status = problems.status()
    except (OSError, KeyError, ValueError) as exc:
        report, status = {"error": f"{type(exc).__name__}: {exc}"}, compare.STATUS_ERROR
    report.update(status=status, command=args.command,
                  inputs=[{"path": str(path), "sha256": compare.file_sha256(path)}
                          for path in inputs if path.is_file()])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out),
                      **{f"{kind}_count": len(report.get(kind) or [])
                         for kind in ("setting_defects", "not_judgeable", "failures")}}))
    return compare.STATUS_EXIT[status]


if __name__ == "__main__":
    sys.exit(main())
