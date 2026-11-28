"""R1 (ed9_design/control_d1_rule/report.md 4.2): which stored V0 lines carry the D1'' head
fault reason ``D1_step`` (P9-D1-2: the set S of lines C-m may change).

Reads the lines and looks only for event names (``events``, ``event_names``,
``event_output.warnings`` / ``fault_events`` of a result line; ``warnings`` / ``fault_events``
of a stored grid run); no line value is printed or written. Per input group it records the
line count, the lines with ``INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:<reason>`` by reason, the
lines with ``FAULT_HEAD_PRESSURE`` (and those of them without any reason: their S membership
is unknown, an upper bound), and the job keys of the ``D1_step`` lines.

Usage (python-dev ``python.exe -I -B``)::

    python scan_d1_step.py --stage5-rows <ho_v0 jsonl> [--stage5-rows ...]
        --main-jsonl <v5/main.jsonl> --grid-keys <key json with v0_pair.file> [...]
        --grid-root <main checkout> --out <scan_d1_step.json>

Exit codes: 0 written; 2 input error (a missing file, an existing ``--out``); 3 tool error.
The stdout's last line is JSON with ``status``, the per-group counts and ``out``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import traceback
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path

EXIT_OK, EXIT_INPUT, EXIT_ERROR = 0, 2, 3
REASON_EVENT = re.compile(r"^INFO_HEAD_PRESSURE_FAULT_REASON:(FL|FR|RL|RR):(\w+)$")
FAULT_EVENT = re.compile(r"^FAULT_HEAD_PRESSURE:(FL|FR|RL|RR)$")
STEP_REASON = "D1_step"
V0_SETTING = "V0"


class InputError(ValueError):
    """A missing input file or an existing output."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def job_key(job: dict) -> str:
    """The job as sorted JSON (a definition of the run, no result value)."""
    return json.dumps(job, sort_keys=True)


def event_names(events: Iterable) -> Iterator[str]:
    """The string items of an event list (``[t, name]``, ``[t, name, is_warning]`` or names)."""
    for event in events or []:
        items = event if isinstance(event, (list, tuple)) else [event]
        for item in items:
            if isinstance(item, str):
                yield item


def classify(names: Iterable[str]) -> tuple[set[str], bool]:
    """(the head fault reasons, whether a ``FAULT_HEAD_PRESSURE`` event is there)."""
    reasons, has_fault = set(), False
    for name in names:
        match = REASON_EVENT.match(name)
        if match:
            reasons.add(match.group(2))
        if FAULT_EVENT.match(name):
            has_fault = True
    return reasons, has_fault


def _empty_group() -> dict:
    return {"lines": 0, "lines_by_reason": Counter(), "fault_head_lines": 0,
            "fault_head_without_reason_lines": 0, "d1_step_keys": []}


def _add_line(group: dict, job: dict, names: Iterable[str]) -> None:
    reasons, has_fault = classify(names)
    group["lines"] += 1
    group["fault_head_lines"] += has_fault
    group["fault_head_without_reason_lines"] += has_fault and not reasons
    for reason in reasons:
        group["lines_by_reason"][reason] += 1
    if STEP_REASON in reasons:
        group["d1_step_keys"].append(job_key(job))


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def scan_result_lines(path: Path, *, only_v0: bool) -> dict:
    group = _empty_group()
    group["error_lines"] = 0
    for row in read_jsonl(path):
        job = row.get("job") or {}
        if only_v0 and job.get("setting", V0_SETTING) != V0_SETTING:
            continue
        if "error" in row:
            group["error_lines"] += 1
            continue
        # run_v5 lines: "event_names" keeps only the first ":" token of a name; the full
        # INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:<reason> is in event_output.warnings
        event_output = row.get("event_output") or {}
        names = [*event_names(row.get("events")), *event_names(row.get("event_names")),
                 *event_names(event_output.get("warnings")),
                 *event_names(event_output.get("fault_events"))]
        _add_line(group, job, names)
    return group


def grid_files(key_paths: Iterable[Path]) -> list[str]:
    names = set()
    for path in key_paths:
        for line in json.loads(path.read_text(encoding="utf-8"))["lines"]:
            file_name = (line.get("v0_pair") or {}).get("file")
            if file_name:
                names.add(file_name)
    return sorted(names)


def scan_grid(root: Path, names: list[str]) -> dict:
    """Stored grid runs (``warnings`` and ``fault_events`` of each run)."""
    group = _empty_group()
    group["files"] = []
    for name in names:
        path = root / name
        if not path.is_file():
            raise InputError(f"grid file missing: {name}")
        group["files"].append({"name": name, "sha256": sha256_of(path)})
        for result in json.loads(path.read_text(encoding="utf-8"))["results"]:
            runs = result.get("runs") or []
            for run in runs.values() if isinstance(runs, dict) else runs:
                names_of_run = [*event_names(run.get("fault_events")),
                                *event_names(run.get("warnings"))]
                job = {"grid_key": result.get("key"), "offset_s": run.get("offset_s"),
                       "event": run.get("event")}
                _add_line(group, job, names_of_run)
    return group


def _finished(group: dict) -> dict:
    out = dict(group)
    out["lines_by_reason"] = dict(sorted(group["lines_by_reason"].items()))
    out["d1_step_lines"] = len(group["d1_step_keys"])
    return out


def _checked(paths: Iterable[Path]) -> list[dict]:
    records = []
    for path in paths:
        if not path.is_file():
            raise InputError(f"missing: {path}")
        records.append({"path": str(path), "sha256": sha256_of(path)})
    return records


def scan(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    inputs = {"stage5_rows": _checked(args.stage5_rows), "main_jsonl": _checked([args.main_jsonl]),
              "grid_keys": _checked(args.grid_keys)}
    stage5 = _empty_group()
    stage5["error_lines"] = 0
    for path in args.stage5_rows:
        part = scan_result_lines(path, only_v0=False)
        for name in ("lines", "fault_head_lines", "error_lines"):
            stage5[name] += part[name]
        stage5["lines_by_reason"].update(part["lines_by_reason"])
        stage5["d1_step_keys"] += part["d1_step_keys"]
    groups = {"stage5_v0": _finished(stage5),
              "census_v0_main": _finished(scan_result_lines(args.main_jsonl, only_v0=True)),
              "stored_grid_v0": _finished(scan_grid(args.grid_root, grid_files(args.grid_keys)))}
    return {"rule": "ed9_design/control_d1_rule/report.md 4.2 R1 (P9-D1-2 set S); event names "
                    "only, no line value", "started_at": started,
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": inputs, "groups": groups,
            "notes": ["S of a group = d1_step_lines; a FAULT_HEAD_PRESSURE line without any "
                      "reason (fault_head_without_reason_lines) is unknown for S"]}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--stage5-rows", type=Path, action="append", required=True)
    parser.add_argument("--main-jsonl", type=Path, required=True)
    parser.add_argument("--grid-keys", type=Path, action="append", required=True)
    parser.add_argument("--grid-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.out.exists():
            raise InputError(f"{args.out} exists")
        report = scan(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)
        counts = {name: {"lines": group["lines"], "d1_step_lines": group["d1_step_lines"],
                         "fault_head_lines": group["fault_head_lines"],
                         "without_reason": group["fault_head_without_reason_lines"]}
                  for name, group in report["groups"].items()}
        print(json.dumps({"status": "ok", "counts": counts, "out": str(args.out)}))
        return EXIT_OK
    except SystemExit as exc:
        return EXIT_INPUT if exc.code else EXIT_OK
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # noqa: BLE001 - every unexpected exception is a tool error
        traceback.print_exc()
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
