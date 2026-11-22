"""Rows a rounded results CSV cannot place on either side of a threshold (C axis).

A results CSV that stores scores rounded to ``d`` decimals cannot tell whether
a row printed as ``0.25`` passed ``conf > 0.25``: the true score lies anywhere
in ``[0.25 - h, 0.25 + h]`` with ``h = 0.5 * 10**-d`` (half a unit in the last
printed place). The M3-3 D0 post-judgement audit (2026-11-15) could not recount
such rows from the CSV alone. This tool finds them before a recount is trusted.

For every row it reads the score column as an exact decimal and reports:

* ``equal`` rows: printed value == threshold;
* ``ambiguous`` rows: ``|value - threshold| <= h`` (closed band, conservative);
* per judgement unit (``--group-by`` columns, ``@file`` = the file itself) the
  pass count on the printed value, without the ambiguous rows (all fail) and
  with them (all pass); the difference is the ambiguous count.

``d`` is ``--decimals`` or, by default, the most fractional digits printed in
that file's score column (writers drop trailing zeros, so ``0.3`` in a
4-decimal file still means ``0.3000``).

Usage:
    python threshold_boundary.py CSV_OR_GLOB [...] --score COLUMN --threshold T
                                 --op {>,>=,gt,ge} [--decimals N|auto]
                                 [--group-by COLUMN ...] [--repo DIR]
                                 [--delimiter CHAR] [--max-listed N]
                                 [--out REPORT] [--format md|json]
                                 [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import (
    expand_file_patterns,
    is_within,
    read_text_facts,
    require_output_outside,
)
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

TOOL_NAME = "threshold_boundary"
AUTO_DECIMALS = "auto"
MAX_DECIMALS = 30
# Seventeen significant digits print a double exactly; 15+ decimals means the
# column was most likely written without rounding.
FULL_PRECISION_DECIMALS = 15
DEFAULT_MAX_LISTED_ROWS = 200
FILE_UNIT_COLUMN = "@file"
ALL_ROWS_LABEL = "(전체)"

# One JSON object of the report (file summary, unit counts, boundary row).
JsonRecord = dict[str, Any]


class Comparison(StrEnum):
    """The pass condition of the threshold rule."""

    GREATER = ">"
    GREATER_EQUAL = ">="

    def holds(self, value: Decimal, threshold: Decimal) -> bool:
        """True when ``value`` passes the threshold."""
        if self is Comparison.GREATER:
            return value > threshold
        return value >= threshold


# `gt`/`ge` spare shells that treat `>` as redirection.
COMPARISON_ALIASES = {
    ">": Comparison.GREATER,
    "gt": Comparison.GREATER,
    ">=": Comparison.GREATER_EQUAL,
    "ge": Comparison.GREATER_EQUAL,
}


@dataclass(frozen=True)
class BoundarySpec:
    """What to read and how to compare, taken from the command line."""

    score_column: str
    threshold: Decimal
    comparison: Comparison
    group_columns: tuple[str, ...]
    decimals: int | None  # None: estimate per file
    delimiter: str


@dataclass(frozen=True)
class ScoreRow:
    """One data row with a parsable score."""

    line: int
    unit: tuple[str, ...]
    text: str
    value: Decimal


@dataclass
class FileScores:
    """Parsed rows of one CSV file."""

    path: Path
    label: str
    rows: list[ScoreRow] = field(default_factory=list)
    unparsable_lines: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class FilePrecision:
    """The printed precision used for one file."""

    decimals: int
    source: str  # "given" or "auto"
    digit_counts: dict[int, int]

    @property
    def half_ulp(self) -> Decimal:
        """Half a unit in the last printed place: ``0.5 * 10**-decimals``."""
        return Decimal(5).scaleb(-(self.decimals + 1))


@dataclass
class UnitCounts:
    """Pass counts of one judgement unit."""

    rows: int = 0
    pass_displayed: int = 0
    ambiguous: int = 0
    equal: int = 0
    sure_pass: int = 0

    @property
    def pass_including(self) -> int:
        """Pass count when every ambiguous row passes."""
        return self.sure_pass + self.ambiguous


@dataclass(frozen=True)
class BoundaryRow:
    """A row whose true score may lie on either side of the threshold."""

    file: str
    line: int
    unit: tuple[str, ...]
    text: str
    is_equal: bool


@dataclass
class Analysis:
    """Everything the report is built from."""

    file_summaries: list[JsonRecord] = field(default_factory=list)
    units: dict[tuple[str, ...], UnitCounts] = field(default_factory=dict)
    boundary_rows: list[BoundaryRow] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


# --- argument parsing -------------------------------------------------------


def _decimals_argument(text: str) -> int | None:
    if text == AUTO_DECIMALS:
        return None
    try:
        decimals = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"expected '{AUTO_DECIMALS}' or an integer, got {text!r}"
        ) from error
    if not 0 <= decimals <= MAX_DECIMALS:
        raise argparse.ArgumentTypeError(f"must be 0..{MAX_DECIMALS}, got {decimals}")
    return decimals


def _parse_threshold(text: str) -> Decimal:
    try:
        threshold = Decimal(text.strip())
    except InvalidOperation as error:
        raise InputError(f"--threshold is not a number: {text!r}") from error
    if not threshold.is_finite():
        raise InputError(f"--threshold must be finite: {text!r}")
    return threshold


def _build_spec(args: argparse.Namespace) -> BoundarySpec:
    if len(args.delimiter) != 1:
        raise InputError(f"--delimiter must be one character: {args.delimiter!r}")
    return BoundarySpec(
        score_column=args.score,
        threshold=_parse_threshold(args.threshold),
        comparison=COMPARISON_ALIASES[args.op],
        group_columns=tuple(args.group_by),
        decimals=args.decimals,
        delimiter=args.delimiter,
    )


# --- reading ----------------------------------------------------------------


def parse_score(text: str) -> Decimal | None:
    """Exact decimal of a score cell; None for blanks, text, nan and inf."""
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def fraction_digits(value: Decimal) -> int:
    """Printed fractional digits: ``0.2500`` -> 4, ``2.5e-1`` -> 2, ``3`` -> 0."""
    exponent = value.as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def _read_records(
    path: Path, delimiter: str
) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """Header and ``(line, cells)`` of the non-blank data rows."""
    text = read_text_facts(path).text
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        header = next(reader, None)
        if header is None:
            raise InputError(f"CSV has no header row: {path}")
        records = [
            (reader.line_num, cells)
            for cells in reader
            if any(cell.strip() for cell in cells)
        ]
    except csv.Error as error:
        raise InputError(f"cannot parse CSV {path}: {error}") from error
    return header, records


def _column_index(header: list[str], column: str, path: Path) -> int:
    if column not in header:
        raise InputError(f"column {column!r} not in {path} (columns: {header})")
    return header.index(column)


def _unit_reader(
    header: list[str], spec: BoundarySpec, path: Path, label: str
) -> Callable[[list[str]], tuple[str, ...]]:
    """Function mapping the cells of a row to its judgement-unit key."""
    indices = [
        None if column == FILE_UNIT_COLUMN else _column_index(header, column, path)
        for column in spec.group_columns
    ]

    def unit_of(cells: list[str]) -> tuple[str, ...]:
        values = []
        for index in indices:
            if index is None:
                values.append(label)
            else:
                values.append(cells[index] if index < len(cells) else "")
        return tuple(values)

    return unit_of


def read_file_scores(path: Path, label: str, spec: BoundarySpec) -> FileScores:
    """Read the score and unit of every data row of one CSV file.

    Raises:
        InputError: If the file is not a CSV with the named columns.
    """
    header, records = _read_records(path, spec.delimiter)
    score_index = _column_index(header, spec.score_column, path)
    unit_of = _unit_reader(header, spec, path, label)
    scores = FileScores(path, label)
    for line, cells in records:
        text = cells[score_index] if score_index < len(cells) else ""
        value = parse_score(text)
        if value is None:
            scores.unparsable_lines.append(line)
            continue
        scores.rows.append(ScoreRow(line, unit_of(cells), text.strip(), value))
    return scores


def _file_label(path: Path, base: Path) -> str:
    return str(path.relative_to(base)) if is_within(path, base) else str(path)


# --- analysis ---------------------------------------------------------------


def file_precision(scores: FileScores, given_decimals: int | None) -> FilePrecision:
    """Printed precision of one file: the given one, or the most digits seen."""
    digit_counts = Counter(fraction_digits(row.value) for row in scores.rows)
    sorted_counts = dict(sorted(digit_counts.items()))
    if given_decimals is not None:
        return FilePrecision(given_decimals, "given", sorted_counts)
    return FilePrecision(max(digit_counts, default=0), "auto", sorted_counts)


def _tally_file(
    scores: FileScores,
    precision: FilePrecision,
    spec: BoundarySpec,
    analysis: Analysis,
) -> list[BoundaryRow]:
    """Add one file's rows to the unit counts and return its boundary rows."""
    half_ulp = precision.half_ulp
    boundary_rows: list[BoundaryRow] = []
    for row in scores.rows:
        counts = analysis.units.setdefault(row.unit, UnitCounts())
        is_ambiguous = abs(row.value - spec.threshold) <= half_ulp
        passes = spec.comparison.holds(row.value, spec.threshold)
        is_equal = row.value == spec.threshold
        counts.rows += 1
        counts.pass_displayed += passes
        counts.equal += is_equal
        counts.ambiguous += is_ambiguous
        counts.sure_pass += passes and not is_ambiguous
        if is_ambiguous:
            boundary_rows.append(
                BoundaryRow(scores.label, row.line, row.unit, row.text, is_equal)
            )
    return boundary_rows


def unit_label(spec: BoundarySpec, unit: tuple[str, ...]) -> str:
    """``fold=0, class=pipe`` or ``(전체)`` without ``--group-by``."""
    if not spec.group_columns:
        return ALL_ROWS_LABEL
    return ", ".join(
        f"{column}={value}"
        for column, value in zip(spec.group_columns, unit, strict=True)
    )


def _boundary_findings(
    scores: FileScores,
    rows: list[BoundaryRow],
    precision: FilePrecision,
    spec: BoundarySpec,
) -> list[Finding]:
    """One error per (file, unit) that holds boundary rows."""
    by_unit: dict[tuple[str, ...], list[BoundaryRow]] = {}
    for row in rows:
        by_unit.setdefault(row.unit, []).append(row)
    findings = []
    for unit, unit_rows in by_unit.items():
        equal_count = sum(row.is_equal for row in unit_rows)
        message = (
            f"모호 {len(unit_rows)}행(표기값 = 문턱 {equal_count}행), "
            f"구간 {spec.threshold} ± {precision.half_ulp} "
            f"(자릿수 {precision.decimals})"
        )
        findings.append(
            Finding(
                Severity.ERROR,
                "boundary_rows",
                str(scores.path),
                unit_rows[0].line,
                message,
                unit_label(spec, unit),
            )
        )
    return findings


def _precision_findings(
    scores: FileScores, precision: FilePrecision, spec: BoundarySpec
) -> list[Finding]:
    """Notes on how trustworthy the printed precision of one file is."""
    path = str(scores.path)
    findings = []
    max_seen = max(precision.digit_counts, default=0)
    if precision.source == "auto":
        message = (
            f"자릿수 {precision.decimals} 추정"
            f"(소수 자릿수별 행 수 {precision.digit_counts})"
        )
        findings.append(Finding(Severity.INFO, "decimals_estimated", path, 0, message))
    elif max_seen > precision.decimals:
        message = (
            f"--decimals {precision.decimals}보다 긴 값이 있다(최대 {max_seen}자리)"
        )
        findings.append(
            Finding(Severity.WARNING, "decimals_below_data", path, 0, message)
        )
    if precision.decimals >= FULL_PRECISION_DECIMALS:
        message = f"자릿수 {precision.decimals}: 반올림하지 않고 저장했을 가능성이 크다"
        findings.append(Finding(Severity.INFO, "full_precision", path, 0, message))
    threshold_digits = fraction_digits(spec.threshold)
    if threshold_digits > precision.decimals:
        message = (
            f"문턱 자릿수 {threshold_digits} > 표기 자릿수 {precision.decimals}: "
            "표기값이 문턱과 달라도 구간에 든다"
        )
        findings.append(Finding(Severity.INFO, "threshold_finer", path, 0, message))
    return findings


def _row_findings(scores: FileScores) -> list[Finding]:
    """Empty files and score cells that are not numbers."""
    path = str(scores.path)
    if not scores.rows and not scores.unparsable_lines:
        return [Finding(Severity.WARNING, "empty_file", path, 0, "데이터 행이 없다")]
    if not scores.unparsable_lines:
        return []
    message = (
        f"점수 해석 불가 {len(scores.unparsable_lines)}행"
        "(빈칸·글자·nan·inf) — 집계에서 뺐다"
    )
    first_line = scores.unparsable_lines[0]
    return [Finding(Severity.WARNING, "score_unparsable", path, first_line, message)]


def _file_summary(
    scores: FileScores, precision: FilePrecision, rows: list[BoundaryRow]
) -> JsonRecord:
    return {
        "path": str(scores.path),
        "label": scores.label,
        "rows": len(scores.rows),
        "unparsable": len(scores.unparsable_lines),
        "decimals": precision.decimals,
        "decimals_source": precision.source,
        "fraction_digits": {str(k): v for k, v in precision.digit_counts.items()},
        "half_ulp": str(precision.half_ulp),
        "ambiguous": len(rows),
        "equal": sum(row.is_equal for row in rows),
    }


def analyse(all_scores: list[FileScores], spec: BoundarySpec) -> Analysis:
    """Classify every row and collect unit counts, boundary rows and findings."""
    analysis = Analysis()
    for scores in all_scores:
        precision = file_precision(scores, spec.decimals)
        rows = _tally_file(scores, precision, spec, analysis)
        analysis.boundary_rows += rows
        analysis.file_summaries.append(_file_summary(scores, precision, rows))
        analysis.findings += _boundary_findings(scores, rows, precision, spec)
        analysis.findings += _row_findings(scores)
        if scores.rows:
            analysis.findings += _precision_findings(scores, precision, spec)
    analysis.findings = sort_findings(analysis.findings)
    return analysis


# --- report -----------------------------------------------------------------


def _natural_unit_key(unit: tuple[str, ...]) -> tuple[tuple[int, Decimal, str], ...]:
    """Sort numbers by value (fold 2 before fold 10), then text."""
    key = []
    for value in unit:
        number = parse_score(value)
        key.append((0, number, "") if number is not None else (1, Decimal(0), value))
    return tuple(key)


def _unit_records(analysis: Analysis, spec: BoundarySpec) -> list[JsonRecord]:
    records = []
    ordered = sorted(
        analysis.units.items(), key=lambda item: _natural_unit_key(item[0])
    )
    for unit, counts in ordered:
        records.append(
            {
                "unit": dict(zip(spec.group_columns, unit, strict=True)),
                "label": unit_label(spec, unit),
                "rows": counts.rows,
                "pass_displayed": counts.pass_displayed,
                "ambiguous": counts.ambiguous,
                "equal": counts.equal,
                "pass_excluding_ambiguous": counts.sure_pass,
                "pass_including_ambiguous": counts.pass_including,
                "difference": counts.ambiguous,
            }
        )
    return records


def _boundary_row_records(analysis: Analysis, spec: BoundarySpec) -> list[JsonRecord]:
    return [
        {
            "file": row.file,
            "line": row.line,
            "unit": unit_label(spec, row.unit),
            "value": row.text,
            "equal": row.is_equal,
        }
        for row in analysis.boundary_rows
    ]


def _summary(analysis: Analysis, units: list[JsonRecord]) -> JsonRecord:
    files = analysis.file_summaries
    return {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": len(files),
        "rows": sum(item["rows"] for item in files),
        "unparsable": sum(item["unparsable"] for item in files),
        "equal": sum(item["equal"] for item in files),
        "ambiguous": len(analysis.boundary_rows),
        "units": len(units),
        "units_with_ambiguous": sum(1 for unit in units if unit["ambiguous"]),
        **count_by_severity(analysis.findings),
        "categories": count_by_category(analysis.findings),
    }


def _files_markdown(file_summaries: list[JsonRecord]) -> list[str]:
    lines = [
        "| 파일 | 행 | 해석 불가 | 자릿수(근거) | ½ulp | 표기값 = 문턱 | 모호 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in file_summaries:
        lines.append(
            f"| {item['label']} | {item['rows']} | {item['unparsable']} "
            f"| {item['decimals']} ({item['decimals_source']}) | {item['half_ulp']} "
            f"| {item['equal']} | {item['ambiguous']} |"
        )
    return lines


def _units_markdown(units: list[JsonRecord]) -> list[str]:
    lines = [
        "| 단위 | 행 | 표기값 기준 통과 | 표기값 = 문턱 | 모호 "
        "| 통과(모호 제외) | 통과(모호 포함) | 차이 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for unit in units:
        lines.append(
            f"| {unit['label']} | {unit['rows']} | {unit['pass_displayed']} "
            f"| {unit['equal']} | {unit['ambiguous']} "
            f"| {unit['pass_excluding_ambiguous']} "
            f"| {unit['pass_including_ambiguous']} | {unit['difference']} |"
        )
    return lines


def _boundary_rows_markdown(rows: list[JsonRecord], limit: int) -> list[str]:
    if not rows:
        return ["모호 행 없음."]
    lines = ["| 파일:줄 | 단위 | 표기값 | 표기값 = 문턱 |", "|---|---|---|---|"]
    for row in rows[:limit]:
        equal_mark = "예" if row["equal"] else "아니오"
        lines.append(
            f"| {row['file']}:{row['line']} | {row['unit']} | {row['value']} "
            f"| {equal_mark} |"
        )
    if len(rows) > limit:
        lines += ["", f"(앞 {limit}행만 표시, 전체 {len(rows)}행은 `--format json`)"]
    return lines


def _markdown(report: JsonRecord, findings: list[Finding], limit: int) -> list[str]:
    summary = report["summary"]
    group_columns = ", ".join(f"`{column}`" for column in report["group_by"])
    return [
        "# threshold_boundary — 반올림 저장으로 문턱 판정을 다시 셀 수 없는 행",
        "",
        f"- 통과 조건 `{report['score_column']} {report['op']} "
        f"{report['threshold']}`, 단위 열 {group_columns or '없음'}",
        f"- 파일 {summary['files']}개, 행 {summary['rows']}개"
        f"(해석 불가 {summary['unparsable']}), 표기값 = 문턱 {summary['equal']}행, "
        f"모호 {summary['ambiguous']}행(단위 {summary['units_with_ambiguous']}"
        f"/{summary['units']}) · {severity_summary_text(findings)}",
        "- 모호 = |표기값 - 문턱| ≤ ½ulp(닫힌 구간). 통과(모호 제외)는 모호 행이 "
        "모두 탈락, 통과(모호 포함)는 모두 통과한 경우다.",
        "",
        "## 파일",
        "",
        *_files_markdown(report["files"]),
        "",
        "## 판정 단위",
        "",
        *_units_markdown(report["units"]),
        "",
        "## 모호 행",
        "",
        *_boundary_rows_markdown(report["boundary_rows"], limit),
        "",
        "## 발견 사항",
        "",
        *findings_markdown(findings),
    ]


def run_threshold_boundary(args: argparse.Namespace) -> ToolOutcome:
    """Read the CSV files, classify the rows and build the report."""
    spec = _build_spec(args)
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    files = expand_file_patterns(args.inputs, base)
    require_output_outside(args.out, files)
    all_scores = [
        read_file_scores(path, _file_label(path, base), spec) for path in files
    ]
    if not any(scores.rows for scores in all_scores):
        # An empty selection must not pass as "no boundary rows".
        raise InputError(f"no numeric value in column {spec.score_column!r}")
    analysis = analyse(all_scores, spec)
    units = _unit_records(analysis, spec)
    summary = _summary(analysis, units)
    report: JsonRecord = {
        "tool": TOOL_NAME,
        "score_column": spec.score_column,
        "threshold": str(spec.threshold),
        "op": str(spec.comparison),
        "group_by": list(spec.group_columns),
        "decimals": AUTO_DECIMALS if spec.decimals is None else spec.decimals,
        "files": analysis.file_summaries,
        "units": units,
        "boundary_rows": _boundary_row_records(analysis, spec),
        "summary": summary,
        "findings": [finding_to_dict(item) for item in analysis.findings],
    }
    markdown = _markdown(report, analysis.findings, args.max_listed)
    lines = deliver_report(args, markdown, report, files)
    return ToolOutcome(
        exit_code_for(analysis.findings, Severity(args.fail_on)), lines, summary
    )


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="threshold_boundary.py",
        description=(
            "반올림 저장한 결과 CSV에서 문턱 경계(|표기값 - 문턱| <= 1/2 ulp) 행을 "
            "찾고 판정 단위별 통과 수 범위를 낸다(읽기 전용)."
        ),
    )
    parser.add_argument(
        "inputs", nargs="+", help="CSV files or glob patterns (relative to --repo)"
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="base folder of relative paths and globs (default .)",
    )
    parser.add_argument("--score", required=True, help="score column name")
    parser.add_argument("--threshold", required=True, help="threshold value, e.g. 0.25")
    parser.add_argument(
        "--op",
        required=True,
        choices=list(COMPARISON_ALIASES),
        help="pass condition: '>' (gt) or '>=' (ge)",
    )
    parser.add_argument(
        "--decimals",
        type=_decimals_argument,
        default=None,
        metavar="N|auto",
        help="printed decimals of the score (default auto: most digits seen per file)",
    )
    parser.add_argument(
        "--group-by",
        nargs="+",
        action="extend",
        default=[],
        metavar="COLUMN",
        help=f"judgement-unit columns ({FILE_UNIT_COLUMN} = the file); repeatable",
    )
    parser.add_argument(
        "--delimiter", default=",", help="CSV field delimiter (default ,)"
    )
    parser.add_argument(
        "--max-listed",
        type=int,
        default=DEFAULT_MAX_LISTED_ROWS,
        help=f"boundary rows listed in the md report "
        f"(default {DEFAULT_MAX_LISTED_ROWS})",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_threshold_boundary(args))


if __name__ == "__main__":
    sys.exit(main())
