"""Findings, severities and report delivery shared by the integrity tools."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from _cli import EXIT_FINDINGS, EXIT_OK, require_distinct_output, write_report

REPORT_FORMATS = ("md", "json")


class Severity(StrEnum):
    """How much a finding matters; ``--fail-on`` picks the exit-code threshold."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
SEVERITY_LABELS = {
    Severity.ERROR: "오류 (error)",
    Severity.WARNING: "경고 (warning)",
    Severity.INFO: "참고 (info)",
}


@dataclass(frozen=True)
class Finding:
    """One problem found in one file.

    ``line`` is 1-based; 0 means the finding concerns the whole file.
    """

    severity: Severity
    category: str
    file: str
    line: int
    message: str
    target: str = ""

    def location(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Order by severity, then file and line."""
    return sorted(
        findings, key=lambda item: (SEVERITY_RANK[item.severity], item.file, item.line)
    )


def count_by_severity(findings: Iterable[Finding]) -> dict[str, int]:
    """Return ``{"error": n, "warning": n, "info": n}`` (all keys present)."""
    counts = Counter(item.severity for item in findings)
    return {str(severity): counts.get(severity, 0) for severity in Severity}


def severity_summary_text(findings: Iterable[Finding]) -> str:
    """Korean one-liner such as ``오류 1 · 경고 0 · 참고 2``."""
    counts = count_by_severity(findings)
    return f"오류 {counts['error']} · 경고 {counts['warning']} · 참고 {counts['info']}"


def count_by_category(findings: Iterable[Finding]) -> dict[str, int]:
    """Return finding counts per category, sorted by category name."""
    counts = Counter(item.category for item in findings)
    return dict(sorted(counts.items()))


def exit_code_for(findings: Iterable[Finding], fail_on: Severity) -> int:
    """Return ``EXIT_FINDINGS`` if any finding is at least as severe as ``fail_on``."""
    threshold = SEVERITY_RANK[fail_on]
    for item in findings:
        if SEVERITY_RANK[item.severity] <= threshold:
            return EXIT_FINDINGS
    return EXIT_OK


def finding_to_dict(item: Finding) -> dict[str, object]:
    record = asdict(item)
    record["severity"] = str(item.severity)
    return record


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def findings_markdown(findings: list[Finding]) -> list[str]:
    """Render findings as Markdown tables, one section per severity."""
    if not findings:
        return ["발견 사항 없음."]
    lines: list[str] = []
    for severity in Severity:
        group = [item for item in findings if item.severity == severity]
        if not group:
            continue
        lines += [f"### {SEVERITY_LABELS[severity]} — {len(group)}건", ""]
        lines += ["| 분류 | 위치 | 대상 | 내용 |", "|---|---|---|---|"]
        for item in group:
            cells = (item.category, item.location(), item.target, item.message)
            lines.append("| " + " | ".join(_escape_cell(cell) for cell in cells) + " |")
        lines.append("")
    return lines


def add_report_arguments(parser: argparse.ArgumentParser) -> None:
    """Add ``--out``, ``--format`` and ``--fail-on`` to a tool's parser."""
    parser.add_argument(
        "--out",
        type=Path,
        help="report file (UTF-8). Without it the full report is printed to stdout.",
    )
    parser.add_argument("--format", choices=REPORT_FORMATS, default="md")
    parser.add_argument(
        "--fail-on",
        choices=[str(severity) for severity in (Severity.ERROR, Severity.WARNING)],
        default=str(Severity.WARNING),
        help="lowest severity that makes the exit code 1 (default: warning)",
    )


def deliver_report(
    args: argparse.Namespace,
    markdown_lines: list[str],
    json_report: dict[str, object],
    input_paths: list[Path],
) -> list[str]:
    """Write the report to ``--out`` or return it for stdout.

    Returns:
        Lines to print before the JSON summary line.

    Raises:
        InputError: If ``--out`` points at one of the input files.
    """
    if args.format == "json":
        text = json.dumps(json_report, ensure_ascii=False, indent=2) + "\n"
    else:
        text = "\n".join(markdown_lines).rstrip() + "\n"
    if args.out is None:
        return text.rstrip("\n").splitlines()
    output_path = args.out.expanduser().resolve()
    require_distinct_output(output_path, input_paths)
    write_report(output_path, text)
    return [f"report: {output_path}"]
