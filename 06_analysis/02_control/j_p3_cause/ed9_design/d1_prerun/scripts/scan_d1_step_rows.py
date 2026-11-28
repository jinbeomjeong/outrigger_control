"""The R1 reason scan (``scan_d1_step.py``) on any run_v5 result files, as one named group: the
lines with ``INFO_HEAD_PRESSURE_FAULT_REASON:<leg>:D1_step`` and their job keys (stats
``stats_r3_check/report.md`` 3.2 condition 2: the off twin of the same-shape batch, the allowed
set of comparison ③).

Event names only, the same fields and rules as ``scan_d1_step.py`` (imported, unchanged); no
line value is printed or written. The output has ``groups.<--group>.d1_step_keys``, the form
``compare_identity.py --allowed-from`` reads.

Usage (python-dev ``python.exe -I -B``)::

    python scan_d1_step_rows.py --rows <jsonl> [--rows ...] --group <name> --out <scan.json>

Exit codes: 0 written; 2 input error (a missing file, an existing ``--out``); 3 tool error.
The stdout's last line is JSON with ``status``, the line count and ``out`` (the D1_step count
stays in the file).
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_d1_step as base_scan  # noqa: E402

EXIT_OK, EXIT_INPUT, EXIT_ERROR = 0, 2, 3


def scan(args: argparse.Namespace) -> dict:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    inputs = base_scan._checked(args.rows)
    group = base_scan._empty_group()
    group["error_lines"] = 0
    for path in args.rows:
        part = base_scan.scan_result_lines(path, only_v0=False)
        for name in ("lines", "fault_head_lines", "fault_head_without_reason_lines",
                     "error_lines"):
            group[name] += part[name]
        group["lines_by_reason"].update(part["lines_by_reason"])
        group["d1_step_keys"] += part["d1_step_keys"]
    return {"rule": "scan_d1_step.py rules on given rows (module docstring); event names only",
            "started_at": started,
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": {"rows": inputs, "scan_script_sha256": base_scan.sha256_of(
                Path(base_scan.__file__))},
            "groups": {args.group: base_scan._finished(group)}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rows", type=Path, action="append", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--out", type=Path, required=True)
    try:
        args = parser.parse_args(argv)
        if args.out.exists():
            raise base_scan.InputError(f"{args.out} exists")
        report = scan(args)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)
        group = report["groups"][args.group]
        # the D1_step count is a measured value: in the file only, never on the console
        print(json.dumps({"status": "ok", "lines": group["lines"], "out": str(args.out)}))
        return EXIT_OK
    except SystemExit as exc:
        return EXIT_INPUT if exc.code else EXIT_OK
    except base_scan.InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # noqa: BLE001 - every unexpected exception is a tool error
        traceback.print_exc()
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
