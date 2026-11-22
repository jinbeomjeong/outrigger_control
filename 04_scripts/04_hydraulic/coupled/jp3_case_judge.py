"""436.9 edition 4a judges of the counterexample arm and of case F (``jp3_remedy_spec.md`` 13.3
P4-5a, 13.8 F-A / F-B / F-E; addendum 4a-1 1; addendum 4a-2 R7, B2, X11).

Sub-commands:

``x11``     P4-5a on the ``LSJ4_X11`` row of ``jp3_x11_replay.py --arm both``: identity
            (``fresh_stretch`` + ``model_only``, ``spec_edition`` of the sealed edition), its
            ``commands_sha256`` = the baseline LSJ4 row (``3672c7222519``), the J-P3b over-tolerance
            reads = 1, on FL, a HOLD read at 49.0 s with ``p_tr - ④`` = +10.674 +- 0.05 bar
            (4a-1: the fixed 13.3 value, never a later baseline row). The ``LSJ4F_X11`` row
            (``--arm fresh_only``), when given, is a record (expected 0 J-P3b violations).
``case-f``  F-A / F-B / F-E on the 15 rows of the run_v5 batch ``j9_case_f``: F-A = the VB row
            equals the stored ``grid_r67_top`` ``results[13].runs[3]`` (harness command hash and
            ``extend_bound_check`` ``breach_reads`` / ``min_gap_bar`` / ``min_gap_t_s`` per leg;
            FR 3 / -0.900 bar @ 48.7 s); F-B = VBH / LSH<n> command hash = VB / LS<n> (T8), VBH
            J-P3a 0 (LSH rows recorded); F-E = VBJ, LSJ1 .. 4 J-P3a / b / c judged keys 0 and
            ``relock_step_over_1bar_count`` 0 (hashes and bounds recorded, 4a-1 1). Every row's
            P4 evidence (4a-2 B2) and every revision 5 row's identity are checked; the F-E
            (J-P3) rows also need ① = ② > 0 (addendum 4a-7 erratum 1 9).
``case-f-path``  Addendum 4a-3 5.2, before case F: the three VB rows of the run_v5 batch
            ``j9_case_f_path`` (offsets 0.0, 0.025, 0.05 s) reproduce ``results[13].runs[0..2]``
            of the stored grid (harness hash with the 4a-3 prefixes, ``breach_reads``,
            ``min_gap_bar`` and ``min_gap_t_s`` within 1e-9); a row at 0.075 s is refused (not
            judgeable). Exit 0 reproduced, 1 a difference (fix the path, do not run case F).

``case-f`` and ``case-f-path`` refuse a grid whose sha256 is not :data:`GRID_SHA256` (4a-3 5.4).

Exit codes and ``status`` (the same for both sub-commands):

======  =================  ===================================================================
exit    status             meaning
======  =================  ===================================================================
0       ``pass``           the prediction holds
1       ``failed``         it does not (13.3 / 13.8: stop and look for the cause), whatever
                           else was found (the other kinds stay, edition 5 erratum 2 2-10)
2       ``not_judgeable``  no failure, no defect: a row, key or column missing, rows of another
                           count; an existing ``--out`` (never overwritten)
2       ``setting_defect`` no failure: a wrong identity or P4 evidence (outranks
                           ``not_judgeable``)
3       ``error``          an unexpected input error (file missing, broken JSON; addendum 4a-5
                           5.1: a tool error, not a judgement)
======  =================  ===================================================================

The report records the sha256 of every input file. The stdout's last line is JSON with
``status``, the problem counts and the report path only (no judged value).

Usage (python-dev or dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_case_judge.py x11 --out <report.json>
      --both <LSJ4_X11 jsonl> --baseline <baseline_221456d folder> [--fresh-only <jsonl>]
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_case_judge.py case-f --out <report.json>
      --rows <j9_case_f jsonl> --grid <resume_k1/h9_grid/grid_r67_top.json>
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_case_judge.py case-f-path --out <json>
      --rows <j9_case_f_path jsonl> --grid <resume_k1/h9_grid/grid_r67_top.json>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402

BAR = 1.0e5
FL, FR = 0, 1
X11_SETTING = "LSJ4_X11"
X11_FRESH_SETTING = "LSJ4F_X11"
X11_IDENTITY = {"spec_edition": compare.SPEC_EDITION, "carry_end_rule": "fresh_stretch",
                "retract_start_rule": "model_only"}
X11_REVISION = 5
"""The ③ revision of the X11 arm in every edition (P4-5a of edition 4a; edition 5 B-1)."""
X11_BASELINE_SETTING = "LSJ4"
X11_BASELINE_HASH_PREFIX = "3672c7222519"
X11_READ_T_S = 49.0
X11_GAP_BAR = 10.674
X11_GAP_TOLERANCE_BAR = 0.05
X11_OVER_TOL_READS = 1
READ_TIME_TOLERANCE_S = 1.0e-6

CASE_F_GROUPS = {"A": ("VB", "LS1", "LS2", "LS3", "LS4"),
                 "B": ("VBH", "LSH1", "LSH2", "LSH3", "LSH4"),
                 "E": ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")}
CASE_F_JOB = {"case": "R12", "eps": 0.0, "offset_s": 0.075,
              "twin": {"level": "top", "leg": "FR", "fs_kN": 8.0}}
"""``run_v5.j9_case_f_jobs`` without the setting."""
GRID_RESULT_INDEX, GRID_RUN_INDEX = 13, 3
GRID_KEY = "screen|top|8.0|ready|FR"
GRID_EVENT, GRID_OFFSET_S = "G4", 0.075
F_A_FR = {"breach_reads": 3, "min_gap_bar": -0.900, "min_gap_t_s": 48.7}
"""13.8 F-A, the documented FR values (checked besides the stored equality)."""
F_A_GAP_TOLERANCE_BAR = 0.0005
STORED_GAP_TOLERANCE_BAR = 1.0e-9
STORED_TIME_TOLERANCE_S = 1.0e-9
CHECK_LIST_KEYS = ("breach_reads", "min_gap_bar", "min_gap_t_s")
REV5_JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
HARNESS_HASH_KEY = "harness_commands_sha256"
GRID_SHA256 = fixed.GRID_SHA256
"""Addendum 4a-3 5.4: ``resume_k1/h9_grid/grid_r67_top.json`` (F-A and 5.2)."""
PATH_OFFSETS_S = (0.0, 0.025, 0.05)
"""4a-3 5.2: ``runs[0..2]`` (``run_v5.J9_CASE_F_PATH_OFFSETS_S``)."""
PATH_HASH_PREFIXES = {0.0: "4712c8fcfeb3", 0.025: "6d1d93ac77dd", 0.05: "7034ad6a41f1"}
"""4a-3 5.2: the stored ``commands_sha256`` of ``runs[0..2]`` (first 12 characters)."""


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _rows_by_setting(rows: list[dict], problems: compare.Problems) -> dict[str, dict]:
    by_setting: dict[str, list[dict]] = {}
    for row in rows:
        if "error" in row:
            problems.not_judgeable.append(f"{row['job'].get('setting')}: error row")
            continue
        by_setting.setdefault(row["job"]["setting"], []).append(row)
    out = {}
    for setting, found in by_setting.items():
        if len(found) != 1:
            problems.not_judgeable.append(f"{setting}: {len(found)} rows")
        out[setting] = found[0]
    return out


def _check(row: dict) -> dict:
    return (row.get("hydraulics_record") or {}).get("extend_bound_check") or {}


def _evidence(row: dict, problems: compare.Problems) -> None:
    setting = row["job"]["setting"]
    problems.setting_defects += [f"{setting}: {text}"
                                 for text in compare.line_evidence_problems(row)]  # 4a-8 2 k


def _key_sum(check: dict, key: str, setting: str, problems: compare.Problems) -> int | None:
    values = check.get(key)
    if not isinstance(values, list) or len(values) != 4:
        problems.not_judgeable.append(f"{setting}: key {key} missing")
        return None
    return int(sum(values))


# --- x11 (P4-5a) ----------------------------------------------------------------------------

def judge_x11(both_rows: list[dict], both_t4h_dir: Path, baseline: compare.Baseline,
              fresh_rows: list[dict] | None) -> tuple[dict, compare.Problems]:
    """P4-5a (module docstring)."""
    problems = compare.Problems()
    rows = _rows_by_setting(both_rows, problems)
    row = rows.get(X11_SETTING)
    if row is None or set(rows) != {X11_SETTING}:
        problems.not_judgeable.append(f"settings {sorted(rows)}, {X11_SETTING} alone expected")
        return {}, problems
    check = _check(row)
    # edition 5 (control review of 8a3c48c7 B-1): X11 stays the edition 4a arm on ③ rev 5
    if check.get("rule_revision") != X11_REVISION:
        problems.setting_defects.append(f"{X11_SETTING}: rule_revision "
                                        f"{check.get('rule_revision')!r}, not {X11_REVISION}")
    problems.setting_defects += [f"{X11_SETTING}: {key} {check.get(key)!r}"
                                 for key, value in X11_IDENTITY.items() if check.get(key) != value]
    _evidence(row, problems)
    baseline_hash = _baseline_hash(baseline, problems)
    if baseline_hash is not None and row["commands_sha256"] != baseline_hash:
        problems.failures.append("P4-5a commands_sha256 differs from the baseline LSJ4")
    over = check.get("jp3b_breach_over_tol_reads")
    if not isinstance(over, list) or len(over) != 4:
        problems.not_judgeable.append("P4-5a jp3b_breach_over_tol_reads missing")
    elif sum(over) != X11_OVER_TOL_READS or over[FL] != X11_OVER_TOL_READS:
        problems.failures.append("P4-5a J-P3b over-tolerance reads are not 1 on FL")
    read = _x11_read(both_t4h_dir / Path(row["t4h_file"]).name, problems)
    if read is not None and (read["class"] != "hold"
                             or abs(read["gap_bar"] - X11_GAP_BAR) > X11_GAP_TOLERANCE_BAR):
        problems.failures.append("P4-5a FL 49.0 s read is not a HOLD at +10.674 +- 0.05 bar")
    record = {"x11_read": read, "commands_sha256": row["commands_sha256"][:12]}
    if fresh_rows is not None:
        record["fresh_only_record"] = _fresh_only_record(fresh_rows)
    return record, problems


def _baseline_hash(baseline: compare.Baseline, problems: compare.Problems) -> str | None:
    rows = [row for row in baseline.rows("j9_cases.jsonl")
            if row["job"]["setting"] == X11_BASELINE_SETTING]
    if len(rows) != 1 or not rows[0]["commands_sha256"].startswith(X11_BASELINE_HASH_PREFIX):
        problems.not_judgeable.append("baseline LSJ4 row missing or of another hash")
        return None
    return rows[0]["commands_sha256"]


def _x11_read(npz: Path, problems: compare.Problems) -> dict | None:
    """The FL read at 49.0 s: class and ``p_tr - ④`` [bar] (4a-1: the fixed 13.3 value)."""
    if not npz.is_file():
        problems.not_judgeable.append(f"P4-5a T4h {npz.name} missing")
        return None
    with np.load(npz, allow_pickle=False) as data:
        missing = [name for name in ("jp3_t_s", "jp3_class", "jp3_class_names",
                                     "jp3_used_bound_Pa", "jp3_p_tr_Pa") if name not in data.files]
        if missing:
            problems.not_judgeable.append(f"P4-5a T4h without {missing}")
            return None
        hits = np.flatnonzero(np.abs(data["jp3_t_s"] - X11_READ_T_S) <= READ_TIME_TOLERANCE_S)
        if hits.size != 1:
            problems.not_judgeable.append(f"P4-5a {hits.size} reads at 49.0 s")
            return None
        read = int(hits[0])
        names = [str(name) for name in data["jp3_class_names"].tolist()]
        code = int(data["jp3_class"][read, FL])
        gap_Pa = float(data["jp3_p_tr_Pa"][read, FL] - data["jp3_used_bound_Pa"][read, FL])
        return {"t_s": float(data["jp3_t_s"][read]),
                "class": names[code] if 0 <= code < len(names) else None,
                "gap_bar": gap_Pa / BAR}


def _fresh_only_record(rows: list[dict]) -> dict:
    """13.3: the ``fresh_stretch``-only arm, a record (expected: J-P3b violations 0)."""
    found = [row for row in rows if row["job"]["setting"] == X11_FRESH_SETTING
             and "error" not in row]
    if len(found) != 1:
        return {"rows": len(found)}
    check = _check(found[0])
    return {"rows": 1, "jp3b_breach_reads": check.get("jp3b_breach_reads"),
            "jp3b_breach_over_tol_reads": check.get("jp3b_breach_over_tol_reads"),
            "expected": "jp3b violations 0 (record, not judged)"}


# --- case F ---------------------------------------------------------------------------------

def judge_case_f(rows: list[dict], grid: dict) -> tuple[dict, compare.Problems]:
    """F-A / F-B / F-E (module docstring)."""
    problems = compare.Problems()
    by_setting = _rows_by_setting(rows, problems)
    expected = {setting for settings in CASE_F_GROUPS.values() for setting in settings}
    if set(by_setting) != expected:
        problems.not_judgeable.append(f"settings {sorted(by_setting)} != the 15 of case F")
        return {}, problems
    for setting, row in by_setting.items():
        if {k: v for k, v in row["job"].items() if k != "setting"} != CASE_F_JOB:
            problems.not_judgeable.append(f"{setting}: job {row['job']} is not the case F row")
        _evidence(row, problems)
        problems.setting_defects += compare.identity_problems(row)
        if setting in CASE_F_GROUPS["E"]:  # addendum 4a-7 erratum 1 9: the J-P3 lines of F-E
            problems.setting_defects += [f"{setting}: {text}" for text in
                                         compare.judged_line_evidence_problems(
                                             row.get("hydraulics_record"),
                                             compare.is_head_only_line(row, None),
                                             compare.evidence_multiplier(row))]
    record = {"F-A": _f_a(by_setting["VB"], grid, problems),
              "F-B": _f_b(by_setting, problems), "F-E": _f_e(by_setting, problems),
              "A_LS_record": {s: _bound_record(by_setting[s]) for s in CASE_F_GROUPS["A"][1:]}}
    return record, problems


def _stored_grid_run(grid: dict, problems: compare.Problems) -> dict | None:
    try:
        result = grid["results"][GRID_RESULT_INDEX]
        run = result["runs"][GRID_RUN_INDEX]
    except (KeyError, IndexError, TypeError):
        problems.not_judgeable.append("grid has no results[13].runs[3]")
        return None
    if (result.get("key") != GRID_KEY or run.get("event") != GRID_EVENT
            or run.get("offset_s") != GRID_OFFSET_S):
        problems.not_judgeable.append("grid results[13].runs[3] is not the FR G4 0.075 s run")
        return None
    return run


def _f_a(vb: dict, grid: dict, problems: compare.Problems) -> dict:
    run = _stored_grid_run(grid, problems)
    stored = ((run or {}).get("hydraulics_record") or {}).get("extend_bound_check") or {}
    new = _check(vb)
    if run is None:
        return {}
    if HARNESS_HASH_KEY not in vb:
        problems.not_judgeable.append(f"F-A VB row without {HARNESS_HASH_KEY}")
    elif vb[HARNESS_HASH_KEY] != run.get("commands_sha256"):
        problems.failures.append("F-A harness command hash differs from the stored grid run")
    missing = [key for key in CHECK_LIST_KEYS if key not in new or key not in stored]
    if missing:
        problems.not_judgeable.append(f"F-A extend_bound_check without {missing}")
        return {"hash_equal": vb.get(HARNESS_HASH_KEY) == run.get("commands_sha256")}
    if not _same_bound_check(new, stored):
        problems.failures.append("F-A extend_bound_check differs from the stored grid run")
    fr_new = {key: new[key][FR] for key in CHECK_LIST_KEYS}
    if (fr_new["breach_reads"] != F_A_FR["breach_reads"]
            or not _close(fr_new["min_gap_bar"], F_A_FR["min_gap_bar"], F_A_GAP_TOLERANCE_BAR)
            or not _close(fr_new["min_gap_t_s"], F_A_FR["min_gap_t_s"], STORED_TIME_TOLERANCE_S)):
        problems.failures.append("F-A FR is not 3 / -0.900 bar @ 48.7 s")
    return {"hash_equal": vb.get(HARNESS_HASH_KEY) == run.get("commands_sha256"),
            "stored_equal": _same_bound_check(new, stored)}


def _close(value, expected: float, tolerance: float) -> bool:
    return value is not None and math.isfinite(value) and abs(value - expected) <= tolerance


def _same_bound_check(new: dict, stored: dict) -> bool:
    if new["breach_reads"] != stored["breach_reads"]:
        return False
    for leg in range(4):
        pairs = ((new["min_gap_bar"][leg], stored["min_gap_bar"][leg], STORED_GAP_TOLERANCE_BAR),
                 (new["min_gap_t_s"][leg], stored["min_gap_t_s"][leg], STORED_TIME_TOLERANCE_S))
        for mine, theirs, tolerance in pairs:
            if (mine is None) != (theirs is None):
                return False
            if mine is not None and abs(mine - theirs) > tolerance:
                return False
    return True


def _f_b(by_setting: dict[str, dict], problems: compare.Problems) -> dict:
    out = {}
    for old, new in zip(CASE_F_GROUPS["A"], CASE_F_GROUPS["B"], strict=True):
        is_equal = by_setting[old]["commands_sha256"] == by_setting[new]["commands_sha256"]
        out[new] = {"hash_equal_to": old, "equal": is_equal}
        if not is_equal:
            problems.failures.append(f"F-B {new} command hash differs from {old} (T8)")
    jp3a = _key_sum(_check(by_setting["VBH"]), "jp3a_breach_reads", "VBH", problems)
    if jp3a:
        problems.failures.append("F-B VBH J-P3a reads > 0")
    out["VBH_jp3a_breach_reads"] = jp3a
    out["LSH_record"] = {s: _bound_record(by_setting[s]) for s in CASE_F_GROUPS["B"][1:]}
    return out


def _f_e(by_setting: dict[str, dict], problems: compare.Problems) -> dict:
    out = {}
    for setting in CASE_F_GROUPS["E"]:
        row = by_setting[setting]
        check = _check(row)
        sums = {key: _key_sum(check, key, setting, problems) for key in REV5_JUDGED_KEYS}
        if any(sums.values()):
            problems.failures.append(f"F-E {setting} J-P3 judged keys > 0")
        relock = (row.get("hydraulics_record") or {}).get("relock_step_over_1bar_count")
        if relock is None:
            problems.not_judgeable.append(f"F-E {setting} relock_step_over_1bar_count missing")
        elif relock:
            problems.failures.append(f"F-E {setting} relock step over 1 bar")
        out[setting] = {"record": _bound_record(row),
                        "commands_sha256": row["commands_sha256"][:12]}  # 4a-1 1: a record
    return out


def judge_case_f_path(rows: list[dict], grid: dict) -> tuple[dict, compare.Problems]:
    """Addendum 4a-3 5.2: the three VB rows of ``j9_case_f_path`` reproduce the stored grid's
    ``runs[0..2]`` (harness command hash, ``breach_reads``, ``min_gap_bar`` <= 1e-9 bar,
    ``min_gap_t_s`` <= 1e-9 s). A row at the judged offset 0.075 s (``runs[3]``) is refused."""
    problems = compare.Problems()
    result = _grid_result(grid, problems)
    if result is None:
        return {}, problems
    by_offset: dict[float, list[dict]] = {}
    for row in rows:
        job = row.get("job") or {}
        offset = job.get("offset_s")
        if offset == GRID_OFFSET_S:
            problems.not_judgeable.append("a row at the judged offset 0.075 s (runs[3]) refused")
            continue
        if "error" in row:
            problems.not_judgeable.append(f"error row at offset {offset}")
            continue
        if {k: v for k, v in job.items() if k not in ("setting", "offset_s")} != {
                k: v for k, v in CASE_F_JOB.items() if k != "offset_s"} or job.get(
                "setting") != "VB":
            problems.not_judgeable.append(f"row {job} is not the case F row with VB")
            continue
        by_offset.setdefault(offset, []).append(row)
    record = {}
    for run_index, offset in enumerate(PATH_OFFSETS_S):
        stored = result["runs"][run_index]
        found = by_offset.get(offset, [])
        if len(found) != 1 or stored.get("event") != GRID_EVENT or stored.get(
                "offset_s") != offset:
            problems.not_judgeable.append(f"offset {offset}: {len(found)} rows / stored run "
                                          f"{run_index} not the G4 run of this offset")
            continue
        record[f"runs[{run_index}]"] = _path_pair(found[0], stored, offset, problems)
    return record, problems


def _grid_result(grid: dict, problems: compare.Problems) -> dict | None:
    try:
        result = grid["results"][GRID_RESULT_INDEX]
    except (KeyError, IndexError, TypeError):
        problems.not_judgeable.append("grid has no results[13]")
        return None
    if result.get("key") != GRID_KEY or len(result.get("runs") or []) <= GRID_RUN_INDEX:
        problems.not_judgeable.append("grid results[13] is not the FR row")
        return None
    return result


def _path_pair(row: dict, stored: dict, offset: float, problems: compare.Problems) -> dict:
    stored_hash = stored.get("commands_sha256") or ""
    expected_prefix = PATH_HASH_PREFIXES[offset]
    if not stored_hash.startswith(expected_prefix):
        problems.not_judgeable.append(f"offset {offset}: stored hash not {expected_prefix}")
    new_check = _check(row)
    stored_check = (stored.get("hydraulics_record") or {}).get("extend_bound_check") or {}
    is_hash_equal = row.get(HARNESS_HASH_KEY) == stored_hash
    missing = [key for key in CHECK_LIST_KEYS if key not in new_check or key not in stored_check]
    if HARNESS_HASH_KEY not in row or missing:
        problems.not_judgeable.append(f"offset {offset}: hash or {missing} missing")
        return {"hash_equal": is_hash_equal}
    is_check_equal = _same_bound_check(new_check, stored_check)
    if not (is_hash_equal and is_check_equal):
        problems.failures.append(f"offset {offset}: not the stored run (fix the path first)")
    return {"hash_equal": is_hash_equal, "extend_bound_check_equal": is_check_equal}


def _bound_record(row: dict) -> dict:
    check = _check(row)
    return {key: check.get(key) for key in (*REV5_JUDGED_KEYS, "breach_reads", "min_gap_bar")
            if key in check}


# --- command line ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    raw_help = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog=compare.EXIT_TABLE, formatter_class=raw_help)
    commands = parser.add_subparsers(dest="command", required=True)
    x11 = commands.add_parser("x11", epilog=compare.EXIT_TABLE, formatter_class=raw_help)
    x11.add_argument("--out", type=Path, required=True)
    x11.add_argument("--both", type=Path, required=True)
    x11.add_argument("--baseline", type=Path, required=True)
    x11.add_argument("--fresh-only", type=Path, default=None)
    for name in ("case-f", "case-f-path"):
        command = commands.add_parser(name, epilog=compare.EXIT_TABLE, formatter_class=raw_help)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--rows", type=Path, required=True,
                             help="run_v5 j9_case_f (case-f) or j9_case_f_path output")
        command.add_argument("--grid", type=Path, required=True,
                             help="resume_k1/h9_grid/grid_r67_top.json (sha256 7160f9f1...)")
    return parser


def _run(args: argparse.Namespace) -> tuple[dict, compare.Problems, list[Path]]:
    if args.command == "x11":
        baseline = compare.Baseline(args.baseline)
        fresh = None if args.fresh_only is None else _read_rows(args.fresh_only)
        t4h_dir = args.both.with_name(f"{args.both.stem}_t4h")
        record, problems = judge_x11(_read_rows(args.both), t4h_dir, baseline, fresh)
        inputs = [args.both, *([] if args.fresh_only is None else [args.fresh_only]),
                  *sorted(t4h_dir.glob("*.npz"))]
        return record, problems, inputs
    if compare.file_sha256(args.grid) != GRID_SHA256:
        raise compare.NotJudgeable(f"{args.grid}: sha256 is not {GRID_SHA256[:12]} (4a-3 5.4)")
    grid = json.loads(args.grid.read_text(encoding="utf-8"))
    judge = judge_case_f if args.command == "case-f" else judge_case_f_path
    record, problems = judge(_read_rows(args.rows), grid)
    return record, problems, [args.rows, args.grid]


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
    except compare.NotJudgeable as exc:
        report, status = {"not_judgeable": [str(exc)]}, compare.STATUS_NOT_JUDGEABLE
    except compare.TOOL_ERRORS as exc:
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
