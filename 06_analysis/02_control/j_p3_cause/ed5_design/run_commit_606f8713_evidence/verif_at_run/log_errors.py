"""Runner step logs: find steps whose log reports ``errors N`` with N > 0 (E / I axis).

A harness can keep a failing case as an error row, print ``errors N`` and still
exit 0 (K-2 V-3, 2026-11-10: ``acc_d8.py`` wrote ``errors 48`` with rc 0 and the
runner went on for four hours). This tool reads the step logs of a runner log
folder and reports every step whose ``errors N`` count is above zero, next to
the step's ``.done`` exit line when there is one.

A step is one ``*.log`` file (the step id = the file stem, the folder relative
to the input folder). Every match of ``--pattern`` in the log counts; the
step's value is the last match (the final summary line) and the maximum is
reported too. A log without a match is ``no_errors_line`` (info; a warning with
``--require-line``): "no count" is not "zero errors".

Usage:
    python log_errors.py FOLDER_OR_LOG [...] [--glob "**/*.log"]
                         [--pattern REGEX] [--require-line]
                         [--out REPORT] [--format md|json] [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import read_text_facts, require_output_outside
from _findings import (
    Finding,
    Severity,
    add_report_arguments,
    count_by_category,
    count_by_severity,
    deliver_report,
    exit_code_for,
    finding_to_dict,
    findings_markdown,
    severity_summary_text,
    sort_findings,
)

TOOL_NAME = "log_errors"
DEFAULT_GLOB = "**/*.log"
DEFAULT_PATTERN = r"\berrors\s*[:=]?\s*(\d+)\b"
"""``done <out> errors 48`` (acc_d8), ``... -> out errors 0``, ``unmatched 1 errors 0 -> out``."""
DONE_SUFFIX = ".done"
DONE_EXIT_PATTERN = re.compile(r"\bexit=(-?\d+)")


@dataclass
class StepLog:
    """The ``errors N`` matches of one step log."""

    step: str
    log: str
    matches: list[dict[str, int]] = field(default_factory=list)
    done_exit: int | None = None
    done_line: str | None = None

    @property
    def last_count(self) -> int | None:
        return self.matches[-1]["count"] if self.matches else None

    @property
    def max_count(self) -> int | None:
        return max(match["count"] for match in self.matches) if self.matches else None

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "last_count": self.last_count,
            "max_count": self.max_count,
        }


def _compile(pattern_text: str) -> re.Pattern[str]:
    try:
        pattern = re.compile(pattern_text)
    except re.error as error:
        raise InputError(
            f"--pattern is not a valid regular expression: {error}"
        ) from error
    if pattern.groups != 1:
        raise InputError("--pattern needs exactly one capture group (the error count)")
    return pattern


def collect_logs(
    inputs: list[str], glob_pattern: str
) -> tuple[list[tuple[Path, Path]], list[Path]]:
    """Return ``[(log file, its base folder)]`` and the input folders.

    Raises:
        InputError: If an input does not exist or no log file is found
            (an empty selection must not pass silently).
    """
    logs: list[tuple[Path, Path]] = []
    folders: list[Path] = []
    for text in inputs:
        path = Path(text).expanduser().resolve()
        if path.is_dir():
            folders.append(path)
            logs += [
                (item, path)
                for item in sorted(path.glob(glob_pattern))
                if item.is_file()
            ]
        elif path.is_file():
            logs.append((path, path.parent))
        else:
            raise InputError(f"input not found: {path}")
    if not logs:
        raise InputError(f"no log file found (glob {glob_pattern!r} in {inputs})")
    return logs, folders


def _done_record(log: Path) -> tuple[int | None, str | None]:
    done = log.with_suffix(DONE_SUFFIX)
    if not done.is_file():
        return None, None
    line = read_text_facts(done).text.strip().splitlines()
    text = line[-1] if line else ""
    match = DONE_EXIT_PATTERN.search(text)
    return (int(match.group(1)) if match else None), text


def read_step(log: Path, base: Path, pattern: re.Pattern[str]) -> StepLog:
    """Every ``--pattern`` match of one log with its 1-based line number."""
    relative = log.relative_to(base) if log.is_relative_to(base) else Path(log.name)
    step = StepLog(step=str(relative.with_suffix("")), log=str(log))
    for number, line in enumerate(read_text_facts(log).text.splitlines(), start=1):
        for match in pattern.finditer(line):
            step.matches.append({"line": number, "count": int(match.group(1))})
    step.done_exit, step.done_line = _done_record(log)
    return step


def step_findings(step: StepLog, require_line: bool) -> list[Finding]:
    """``log_errors_nonzero`` (error), ``no_errors_line`` (info or warning)."""
    if not step.matches:
        severity = Severity.WARNING if require_line else Severity.INFO
        return [
            Finding(
                severity,
                "no_errors_line",
                step.log,
                0,
                "no 'errors N' line in the log",
                step.step,
            )
        ]
    nonzero = [match for match in step.matches if match["count"] > 0]
    if not nonzero:
        return []
    exit_note = "" if step.done_exit is None else f"; .done exit={step.done_exit}"
    return [
        Finding(
            Severity.ERROR,
            "log_errors_nonzero",
            step.log,
            match["line"],
            f"errors {match['count']} (last {step.last_count}, max {step.max_count}){exit_note}",
            step.step,
        )
        for match in nonzero
    ]


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    lines = [
        "# log_errors — 단계 로그 오류 수",
        "",
        f"- 로그 {summary['logs']}개, 오류 단계 {summary['steps_with_errors']}개, "
        f"오류 줄 없음 {summary['steps_without_line']}개 · {severity_summary_text(findings)}",
        "",
        "| 단계 | 마지막 N | 최대 N | .done |",
        "|---|---|---|---|",
    ]
    for step in report["steps"]:
        lines.append(
            f"| {step['step']} | {step['last_count']} | {step['max_count']} "
            f"| {step['done_line'] or ''} |"
        )
    return [*lines, "", "## 발견 사항", "", *findings_markdown(findings)]


def run_log_errors(args: argparse.Namespace) -> ToolOutcome:
    """Scan the logs and build the report."""
    pattern = _compile(args.pattern)
    logs, folders = collect_logs(args.inputs, args.glob)
    require_output_outside(args.out, [log for log, _ in logs], folders)
    steps = [read_step(log, base, pattern) for log, base in logs]
    findings: list[Finding] = []
    for step in steps:
        findings += step_findings(step, args.require_line)
    findings = sort_findings(findings)
    summary = {
        "tool": TOOL_NAME,
        "command": "scan",
        "logs": len(steps),
        "steps_with_errors": sum(1 for step in steps if (step.max_count or 0) > 0),
        "steps_without_line": sum(1 for step in steps if not step.matches),
        "error_rows_total": sum(step.last_count or 0 for step in steps),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "pattern": args.pattern,
        "glob": args.glob,
        "steps": [step.to_dict() for step in steps],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(
        args, _markdown(report, findings), report, [log for log, _ in logs]
    )
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="log_errors.py",
        description="러너 단계 로그에서 'errors N'(N > 0)을 찾는다(읽기 전용).",
    )
    parser.add_argument(
        "inputs", nargs="+", help="runner log folder(s) or .log file(s)"
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"log glob inside a folder (default {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="regular expression with one capture group = the error count",
    )
    parser.add_argument(
        "--require-line",
        action="store_true",
        help="a log without an 'errors N' line is a warning (default: info)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_log_errors(args))


if __name__ == "__main__":
    sys.exit(main())
