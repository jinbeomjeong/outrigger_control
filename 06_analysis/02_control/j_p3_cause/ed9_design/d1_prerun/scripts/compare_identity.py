"""P9-D1-1 / P9-D1-2 (ed9_design/control_d1_rule/report.md 4.1): compare re-run V0 lines with
the stored lines of the same jobs, line by line.

Per job (the job without the per-run fields ``mask`` and ``t4h_dir``) it compares
``commands_sha256``, ``final_phase`` and the WARN / FAULT name sets (:func:`warn_fault_names`).
With ``--allowed-from
<scan_d1_step.json>`` (group ``--allowed-group``, default ``stage5_v0``) the differing jobs must
be among that scan's ``d1_step_keys`` (P9-D1-2, switch on); without it every job must be
identical (P9-D1-1, switch off). ``--expect-switch off|on`` also compares the C-m state of
every line (:func:`switch_problems`: off = the stored ``controller_tag`` and no
``d1_settings``; on = the stored tag with ``_CM`` before a trailing ``_ED8`` and
``d1_settings`` on); a mismatch makes the status ``differs``. ``--require-allowed-change``:
an allowed job that stayed the same is also ``differs`` (P9-D1-3). ``--only-setting V0``
compares the lines of one setting (the stored ``v5/main.jsonl`` holds every setting).
``--stored-tag-absent <tag>``: a stored line without ``controller_tag`` stands for that tag
(``v5/main.jsonl`` V0 lines carry none; audit B-2). ``--require-prior <report.json>``
(repeatable): the comparison runs only after each prior report is ``identical`` and has this
run's ``--stored`` files among its inputs (else ``not_judgeable``, nothing compared; stats 3.2
condition 3). An ``--allowed-from``
file is any JSON with ``groups.<group>.d1_step_keys`` (job JSON strings): ``scan_d1_step.json``,
``scan_d1_step_rows.py`` output, ``r3c_expected_d1_step.json``.

R3c gates (control ``control_r3_check/report.md`` 5): ``--with-d1-reasons`` also compares the
D1 INFO reason names (:func:`d1_info_reasons`; ③ ≡ ②); ``--stored-path-under`` /
``--new-path-under <folder>``: every line's ``diag.two_pressure_file`` lies under that worktree
(else ``differs``); ``--only-common --expect-compared N``: only the jobs both sides have, exactly
N of them (② ≡ R3b, 5 jobs).

No value is printed: stdout's last line is JSON with ``status`` and counts; the written report
holds the job keys of the differing, missing and extra lines and which fields differ (no field
value).

Usage (python-dev ``python.exe -I -B``)::

    python compare_identity.py --stored <jsonl> [...] --new <jsonl> [...]
        [--allowed-from <scan_d1_step.json> [--allowed-group stage5_v0]] --out <report.json>

Exit codes (one table for the whole tool):

====  ===============  ==========================================================================
exit  status           meaning
====  ===============  ==========================================================================
0     ``identical``    every stored job has one new line and nothing differs (P9-D1-1)
0     ``as_expected``  with ``--allowed-from``: only allowed jobs differ (P9-D1-2), none missing
1     ``differs``      a job outside the allowed set differs (or any, without it)
2     ``not_judgeable``  0 compared jobs, a missing / repeated / extra line, an error line, an
                       input error or an existing ``--out``
3     ``error``        a tool error
====  ===============  ==========================================================================
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

EXIT_PASS, EXIT_DIFFERS, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3
RUN_ONLY_JOB_FIELDS = ("mask", "t4h_dir")
"""Job fields a runner adds per run (``run_v5.main``), not part of the job identity."""
COMPARED_FIELDS = ("commands_sha256", "final_phase", "warn_fault_names")
D1_REASON_FIELD = "d1_info_reasons"
"""Compared too with ``--with-d1-reasons`` (control ``control_r3_check/report.md`` 5 condition
1: the ③ ≡ ② gate)."""
D1_INFO_PREFIX = "INFO_HEAD_PRESSURE_FAULT_REASON"
D1_MEDIAN_SUFFIX = "_CM"
ED8_SUFFIX = "_ED8"
D1_SETTINGS_ON = {"imu_residual_median_check": True}
SWITCH_STATES = ("off", "on")


def with_d1_median_tag(tag: str | None) -> str | None:
    """The stored tag with ``_CM`` (``v5_options.with_d1_median_tag``: before a trailing
    ``_ED8``); written out here so the tool needs no project import."""
    if tag is None:
        return None
    if tag.endswith(ED8_SUFFIX):
        return tag[: -len(ED8_SUFFIX)] + D1_MEDIAN_SUFFIX + ED8_SUFFIX
    return tag + D1_MEDIAN_SUFFIX


def stored_tag_of(stored: dict, absent_tag: str | None) -> str | None:
    """The stored line's ``controller_tag``; a line without the key (``v5/main.jsonl`` V0, run
    before the tag was recorded on lines without options) reads ``absent_tag`` when given
    (audit ``audit_r3_prerun/report.md`` B-2), else None."""
    if stored.get("controller_tag") is None:
        return absent_tag
    return stored["controller_tag"]


def switch_problems(stored: dict, new: dict, state: str,
                    absent_tag: str | None = None) -> list[str]:
    """Control ``control_cm_switch/report.md`` 1.5: off = the stored tag and no
    ``d1_settings``; on = the stored tag with ``_CM`` and ``d1_settings`` on (the stored tag
    of :func:`stored_tag_of`)."""
    expected_tag = stored_tag_of(stored, absent_tag)
    expected_settings = None
    if state == "on":
        expected_tag = with_d1_median_tag(expected_tag)
        expected_settings = D1_SETTINGS_ON
    problems = []
    if new.get("controller_tag") != expected_tag:
        problems.append("controller_tag")
    if new.get("d1_settings") != expected_settings:
        problems.append("d1_settings")
    return problems


class InputError(ValueError):
    """A missing input, an unreadable scan or an existing output."""


def job_key(job: dict) -> str:
    plain = {key: value for key, value in job.items() if key not in RUN_ONLY_JOB_FIELDS}
    return json.dumps(plain, sort_keys=True)


def _strings(items: Iterable) -> Iterable[str]:
    for item in items or []:
        values = item if isinstance(item, (list, tuple)) else [item]
        for value in values:
            if isinstance(value, str):
                yield value


def warn_fault_names(row: dict) -> list[str]:
    """WARN / FAULT names of the line: ``event_names`` (first ``:`` token only), the timed
    ``events`` and ``event_output.warnings`` / ``fault_events`` (full names with the leg)."""
    event_output = row.get("event_output") or {}
    sources = (row.get("event_names"), row.get("events"), event_output.get("warnings"),
               event_output.get("fault_events"))
    names = {name for source in sources for name in _strings(source)
             if name.startswith(("WARN", "FAULT"))}
    return sorted(names)


def d1_info_reasons(row: dict) -> list[str]:
    """The D1 INFO reason names of the line (``INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:<reason>``,
    full names from the timed ``events`` and ``event_output.warnings``; ``event_names`` keeps
    only the first ``:`` token and is not read)."""
    event_output = row.get("event_output") or {}
    sources = (row.get("events"), event_output.get("warnings"))
    names = {name for source in sources for name in _strings(source)
             if name.startswith(D1_INFO_PREFIX)}
    return sorted(names)


def identity_of(row: dict) -> dict:
    return {"commands_sha256": row.get("commands_sha256"), "final_phase": row.get("final_phase"),
            "warn_fault_names": warn_fault_names(row), "d1_info_reasons": d1_info_reasons(row)}


def path_marker_problem(row: dict, root: Path | None) -> str | None:
    """Control ``control_r3_check/report.md`` 5 condition 3: the line's
    ``diag.two_pressure_file`` (``r3c_run.py``) lies under ``root``; None = no check or fine."""
    if root is None:
        return None
    marker = (row.get("diag") or {}).get("two_pressure_file")
    if not marker:
        return "no diag.two_pressure_file"
    try:
        Path(marker).resolve().relative_to(root.resolve())
    except ValueError:
        return f"diag.two_pressure_file outside {root}"
    return None


def lines_by_job(paths: Iterable[Path], only_setting: str | None = None
                 ) -> tuple[dict[str, dict], list[str], int]:
    """(job key -> line, repeated keys, error lines); with ``only_setting`` the lines of that
    ``job.setting`` only (``v5/main.jsonl`` holds every setting)."""
    out: dict[str, dict] = {}
    repeated, errors = [], 0
    for path in paths:
        if not path.is_file():
            raise InputError(f"missing: {path}")
        with path.open(encoding="utf-8") as handle:
            for text in handle:
                if not text.strip():
                    continue
                row = json.loads(text)
                if only_setting is not None and (row.get("job") or {}).get(
                        "setting") != only_setting:
                    continue
                if "error" in row:
                    errors += 1
                    continue
                key = job_key(row.get("job") or {})
                if key in out:
                    repeated.append(key)
                out[key] = row
    return out, repeated, errors


def allowed_keys(scan_path: Path | None, group: str) -> set[str] | None:
    if scan_path is None:
        return None
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    try:
        keys = scan["groups"][group]["d1_step_keys"]
    except KeyError as exc:
        raise InputError(f"{scan_path}: no groups.{group}.d1_step_keys") from exc
    return {job_key(json.loads(key)) for key in keys}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_priors(prior_paths: Iterable[Path], stored_paths: Iterable[Path]) -> list[dict]:
    """Order assertion (stats ``stats_r3_check/report.md`` 3.2 condition 3: ① before ②, ④
    before ⑤): every prior comparison report exists, is ``identical``, and this comparison's
    ``--stored`` files are among its inputs (by sha256: ⑤'s stored = ④'s new, ②'s stored =
    ①'s stored).

    Raises:
        InputError: No prior report, another status, or files the prior did not compare.
    """
    stored = {_sha256(path) for path in stored_paths}
    records = []
    for prior_path in prior_paths:
        if not prior_path.is_file():
            raise InputError(f"prior comparison {prior_path} missing (run it first)")
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        if prior.get("status") != "identical":
            raise InputError(f"prior comparison {prior_path.name} is {prior.get('status')!r}, "
                             "not identical: this comparison is not run")
        inputs = prior.get("inputs") or {}
        compared = {entry["sha256"] for side in ("stored", "new")
                    for entry in inputs.get(side, [])}
        if not stored <= compared:
            raise InputError(f"the --stored files are not inputs of {prior_path.name}")
        records.append({"path": str(prior_path), "sha256": _sha256(prior_path),
                        "status": prior["status"]})
    return records


def compared_fields(args: argparse.Namespace) -> tuple[str, ...]:
    return (*COMPARED_FIELDS, D1_REASON_FIELD) if args.with_d1_reasons else COMPARED_FIELDS


def _job_differences(args: argparse.Namespace, stored: dict, new: dict,
                     allowed: set[str] | None) -> dict[str, list]:
    """Per stored job present in ``new``: the differing fields, the C-m switch mismatch and
    the path marker problems; the stored jobs ``new`` lacks."""
    fields_compared = compared_fields(args)
    found: dict[str, list] = {"differing": [], "missing": [], "switch_mismatch": [],
                              "path_marker": []}
    for key, row in stored.items():
        if key not in new:
            found["missing"].append(key)
            continue
        old_identity, new_identity = identity_of(row), identity_of(new[key])
        fields = [name for name in fields_compared if old_identity[name] != new_identity[name]]
        if fields:
            found["differing"].append({"job": key, "fields": fields,
                                       "allowed": allowed is not None and key in allowed})
        if args.expect_switch is not None:
            problems = switch_problems(row, new[key], args.expect_switch,
                                       args.stored_tag_absent)
            if problems:
                found["switch_mismatch"].append({"job": key, "fields": problems})
        for side, line, root in (("stored", row, args.stored_path_under),
                                 ("new", new[key], args.new_path_under)):
            problem = path_marker_problem(line, root)
            if problem is not None:
                found["path_marker"].append({"job": key, "side": side, "problem": problem})
    return found


def _not_judgeable_reasons(args: argparse.Namespace, compared: int, counts: dict) -> list[str]:
    reasons = []
    if compared == 0:
        reasons.append("0 compared jobs")
    if args.expect_compared is not None and compared != args.expect_compared:
        reasons.append(f"{compared} compared jobs, {args.expect_compared} expected")
    for name, count in counts.items():
        if count:
            reasons.append(f"{name}: {count}")
    return reasons


def _status(found: dict, not_judgeable: list[str], must_change: bool) -> str:
    outside = [entry for entry in found["differing"] if not entry["allowed"]]
    if outside or found["switch_mismatch"] or found["path_marker"] or must_change:
        return "differs"
    if not_judgeable:
        return "not_judgeable"
    return "as_expected" if found["differing"] else "identical"


def compare(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    prior = checked_priors(args.require_prior, args.stored)
    stored, stored_repeated, stored_errors = lines_by_job(args.stored, args.only_setting)
    new, new_repeated, new_errors = lines_by_job(args.new, args.only_setting)
    allowed = allowed_keys(args.allowed_from, args.allowed_group)
    if args.only_common:  # the overlap only: a job of one side alone is out of scope
        stored = {key: row for key, row in stored.items() if key in new}
        stored_repeated = [key for key in stored_repeated if key in stored]
        new_repeated = [key for key in new_repeated if key in stored]
    found = _job_differences(args, stored, new, allowed)
    differing, missing = found["differing"], found["missing"]
    switch_mismatch = found["switch_mismatch"]
    extra = sorted(set(new) - set(stored))
    compared = len(stored) - len(missing)
    is_extra_counted = not (args.subset_of_new or args.only_common)
    not_judgeable = _not_judgeable_reasons(args, compared, {
        "missing new lines": len(missing), "extra new lines": len(extra) * is_extra_counted,
        "repeated stored jobs": len(stored_repeated), "repeated new jobs": len(new_repeated),
        "stored error lines": stored_errors, "new error lines": new_errors})
    outside = [entry for entry in differing if not entry["allowed"]]
    unchanged_allowed = 0 if allowed is None else len(
        allowed - {entry["job"] for entry in differing})
    must_change = args.require_allowed_change and unchanged_allowed > 0
    status = _status(found, not_judgeable, must_change)
    return {"rule": "ed9_design/control_d1_rule/report.md 4.1 P9-D1-1 / P9-D1-2 (module "
                    "docstring)", "started_at": started,
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": {"stored": [{"path": str(p), "sha256": _sha256(p)} for p in args.stored],
                       "new": [{"path": str(p), "sha256": _sha256(p)} for p in args.new],
                       "allowed_from": None if args.allowed_from is None else {
                           "path": str(args.allowed_from), "group": args.allowed_group,
                           "sha256": _sha256(args.allowed_from)},
                       "priors": prior},
            "stored_tag_absent": args.stored_tag_absent,
            "stored_lines_without_tag": sum(row.get("controller_tag") is None
                                            for row in stored.values()),
            "compared_fields": list(compared_fields(args)), "status": status,
            "only_common": args.only_common,
            "path_under": {"stored": None if args.stored_path_under is None else str(
                args.stored_path_under), "new": None if args.new_path_under is None else str(
                args.new_path_under)},
            "counts": {"stored_jobs": len(stored), "new_jobs": len(new), "compared": compared,
                       "differing": len(differing), "differing_outside_allowed": len(outside),
                       "allowed": None if allowed is None else len(allowed),
                       "allowed_unchanged": None if allowed is None else unchanged_allowed,
                       "missing": len(missing), "extra": len(extra),
                       "switch_mismatch": len(switch_mismatch),
                       "path_marker_problems": len(found["path_marker"])},
            "expect_switch": args.expect_switch, "not_judgeable": not_judgeable,
            "differing": differing, "switch_mismatch": switch_mismatch,
            "path_marker": found["path_marker"], "missing": missing, "extra": extra}


EXIT_OF_STATUS = {"identical": EXIT_PASS, "as_expected": EXIT_PASS, "differs": EXIT_DIFFERS,
                  "not_judgeable": EXIT_NOT_JUDGEABLE}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--stored", type=Path, action="append", required=True)
    parser.add_argument("--new", type=Path, action="append", required=True)
    parser.add_argument("--allowed-from", type=Path, default=None)
    parser.add_argument("--allowed-group", default="stage5_v0")
    parser.add_argument("--require-allowed-change", action="store_true",
                        help="with --allowed-from: an allowed job that did not change differs "
                             "(P9-D1-3, stats stats_impl_check 3 condition 5)")
    parser.add_argument("--subset-of-new", action="store_true",
                        help="the stored lines are a part of the new ones (one stored file of "
                             "several): extra new lines are recorded, not a reason")
    parser.add_argument("--only-setting", default=None,
                        help="compare the lines of this job.setting only (e.g. V0)")
    parser.add_argument("--expect-switch", choices=SWITCH_STATES, default=None,
                        help="C-m state of the new lines: off = the stored tag, on = the stored "
                             "tag with _CM and d1_settings on (a mismatch differs)")
    parser.add_argument("--stored-tag-absent", default=None,
                        help="the tag a stored line without controller_tag stands for (e.g. "
                             "final_C4G2_LAS_K1 for v5/main.jsonl V0)")
    parser.add_argument("--require-prior", type=Path, action="append", default=[],
                        help="a prior comparison report (repeatable) that must be identical "
                             "and have this run's --stored files among its inputs (① before ②, "
                             "④ before ⑤)")
    parser.add_argument("--with-d1-reasons", action="store_true",
                        help="also compare the D1 INFO reason names (③ ≡ ② gate)")
    parser.add_argument("--stored-path-under", type=Path, default=None,
                        help="every stored line's diag.two_pressure_file lies under this folder")
    parser.add_argument("--new-path-under", type=Path, default=None,
                        help="every new line's diag.two_pressure_file lies under this folder")
    parser.add_argument("--only-common", action="store_true",
                        help="compare the jobs both sides have (② ≡ R3b overlap); give "
                             "--expect-compared")
    parser.add_argument("--expect-compared", type=int, default=None,
                        help="the number of compared jobs (another number is not judgeable)")
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.out.exists():
            raise InputError(f"{args.out} exists")
        report = compare(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)
        print(json.dumps({"status": report["status"], "counts": report["counts"],
                          "out": str(args.out)}))
        return EXIT_OF_STATUS[report["status"]]
    except SystemExit as exc:
        return EXIT_NOT_JUDGEABLE if exc.code else EXIT_PASS
    except InputError as exc:
        print(json.dumps({"status": "not_judgeable", "reason": str(exc)}))
        return EXIT_NOT_JUDGEABLE
    except Exception:  # noqa: BLE001 - every unexpected exception is a tool error
        traceback.print_exc()
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
