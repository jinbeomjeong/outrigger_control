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


def switch_problems(stored: dict, new: dict, state: str) -> list[str]:
    """Control ``control_cm_switch/report.md`` 1.5: off = the stored tag and no
    ``d1_settings``; on = the stored tag with ``_CM`` and ``d1_settings`` on."""
    expected_tag = stored.get("controller_tag")
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


def identity_of(row: dict) -> dict:
    return {"commands_sha256": row.get("commands_sha256"), "final_phase": row.get("final_phase"),
            "warn_fault_names": warn_fault_names(row)}


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


def compare(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    stored, stored_repeated, stored_errors = lines_by_job(args.stored, args.only_setting)
    new, new_repeated, new_errors = lines_by_job(args.new, args.only_setting)
    allowed = allowed_keys(args.allowed_from, args.allowed_group)
    differing, missing, switch_mismatch = [], [], []
    for key, row in stored.items():
        if key not in new:
            missing.append(key)
            continue
        fields = [name for name in COMPARED_FIELDS
                  if identity_of(row)[name] != identity_of(new[key])[name]]
        if fields:
            differing.append({"job": key, "fields": fields,
                              "allowed": allowed is not None and key in allowed})
        if args.expect_switch is not None:
            problems = switch_problems(row, new[key], args.expect_switch)
            if problems:
                switch_mismatch.append({"job": key, "fields": problems})
    extra = sorted(set(new) - set(stored))
    compared = len(stored) - len(missing)
    not_judgeable = []
    if compared == 0:
        not_judgeable.append("0 compared jobs")
    extra_counted = 0 if args.subset_of_new else len(extra)
    for name, count in (("missing new lines", len(missing)), ("extra new lines", extra_counted),
                        ("repeated stored jobs", len(stored_repeated)),
                        ("repeated new jobs", len(new_repeated)),
                        ("stored error lines", stored_errors), ("new error lines", new_errors)):
        if count:
            not_judgeable.append(f"{name}: {count}")
    outside = [entry for entry in differing if not entry["allowed"]]
    unchanged_allowed = 0 if allowed is None else len(
        allowed - {entry["job"] for entry in differing})
    must_change = args.require_allowed_change and unchanged_allowed > 0
    if outside or switch_mismatch or must_change:
        status = "differs"
    elif not_judgeable:
        status = "not_judgeable"
    elif differing:
        status = "as_expected"
    else:
        status = "identical"
    return {"rule": "ed9_design/control_d1_rule/report.md 4.1 P9-D1-1 / P9-D1-2 (module "
                    "docstring)", "started_at": started,
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": {"stored": [{"path": str(p), "sha256": _sha256(p)} for p in args.stored],
                       "new": [{"path": str(p), "sha256": _sha256(p)} for p in args.new],
                       "allowed_from": None if args.allowed_from is None else {
                           "path": str(args.allowed_from), "group": args.allowed_group,
                           "sha256": _sha256(args.allowed_from)}},
            "compared_fields": list(COMPARED_FIELDS), "status": status,
            "counts": {"stored_jobs": len(stored), "new_jobs": len(new), "compared": compared,
                       "differing": len(differing), "differing_outside_allowed": len(outside),
                       "allowed": None if allowed is None else len(allowed),
                       "allowed_unchanged": None if allowed is None else len(
                           allowed - {entry["job"] for entry in differing}),
                       "missing": len(missing), "extra": len(extra),
                       "switch_mismatch": len(switch_mismatch)},
            "expect_switch": args.expect_switch, "not_judgeable": not_judgeable,
            "differing": differing, "switch_mismatch": switch_mismatch, "missing": missing,
            "extra": extra}


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
