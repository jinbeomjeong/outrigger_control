"""Timeline (T axis): were the rules and their revisions fixed before the results?

Rule time, best evidence first: the ``sealed <time>`` of the ``.sha256`` file,
the commit that added the rule file (``git log --diff-filter=A --follow``), a
date in the file head (``봉인(YYYY-MM-DD)``, ``작성: ..., YYYY-MM-DD``).
Result time is the earliest of: the minimum of ``--time-field`` in the records
(``.jsonl``/``.json``: dotted path, ``.csv``: column name), the commit that
added the result file, the file mtime (mtime alone is only an estimate:
checkouts and appends move it). ``.md``/``.txt`` results have no records, so
only the commit and the mtime count. Every result row names its basis.

Times without an offset stay naive; when compared with an aware time they are
read as the local time zone and the ``basis`` says so.

Usage:
    python timeline.py --rules RULE.md [RULE.md ...] --results FILE [FILE ...]
                       [--repo DIR] [--revs auto|none] [--sha-dir DIR]
                       [--time-field a.b] [--no-git] [--out REPORT]
                       [--format md|json] [--fail-on error|warning]

``--rules`` and ``--results`` take several values and may be repeated; every
occurrence counts (a file given twice is compared once). Relative paths (and
``--results`` glob patterns) are taken from ``--repo`` (default: the current
folder).
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import (
    decode_bytes,
    expand_file_patterns,
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
    sort_findings,
)
from _git import GitQueries, relative_posix
from _records import get_dotted, load_records
from _rules import (
    RuleEdition,
    collect_editions,
    parse_seal_file,
    parse_time,
    seal_path_for,
)

TOOL_NAME = "timeline"
HEADER_LINES = 40
HEADER_DATE_PATTERNS = (
    re.compile(r"봉인\s*\((\d{4}-\d{2}-\d{2})"),
    re.compile(r"작성:[^\n]*?(\d{4}-\d{2}-\d{2})"),
)
AFTER_DECLARATIONS = (
    re.compile(r"AFTER"),
    re.compile(r"after seeing", re.IGNORECASE),
    re.compile(r"결과를 본 뒤|결과 뒤|결과를 보고"),
)
# Epoch numbers below this are durations, not wall-clock times.
MIN_EPOCH_S = 1e9


class ResultKind(StrEnum):
    """How a result file is read: records with fields, a table, or plain text."""

    RECORDS = "records"  # .jsonl / .json / .npz via _records
    TABLE = "table"  # .csv: --time-field names a column
    DOCUMENT = "document"  # .md / .txt: only git and mtime


RESULT_KIND_BY_SUFFIX = {
    ".jsonl": ResultKind.RECORDS,
    ".json": ResultKind.RECORDS,
    ".npz": ResultKind.RECORDS,
    ".csv": ResultKind.TABLE,
    ".md": ResultKind.DOCUMENT,
    ".txt": ResultKind.DOCUMENT,
}


@dataclass(frozen=True)
class Stamp:
    """A point in time and where it came from (``date_only`` for header dates)."""

    moment: datetime
    basis: str
    is_date_only: bool = False

    def text(self) -> str:
        if self.is_date_only:
            return self.moment.date().isoformat()
        return self.moment.isoformat(timespec="seconds")


@dataclass
class RuleTimes:
    edition: RuleEdition
    sealed_at: Stamp | None
    git_added_at: Stamp | None
    header_date: Stamp | None
    declares_after: bool

    def best(self) -> Stamp | None:
        return self.sealed_at or self.git_added_at or self.header_date

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.edition.path),
            "rev": self.edition.label,
            "sealed_at": self.sealed_at.text() if self.sealed_at else None,
            "git_added_at": self.git_added_at.text() if self.git_added_at else None,
            "header_date": self.header_date.text() if self.header_date else None,
            "declares_after": self.declares_after,
        }


@dataclass
class ResultTimes:
    path: Path
    kind: ResultKind
    mtime: Stamp
    git_added_at: Stamp | None
    field_min: Stamp | None
    field_max: Stamp | None

    def earliest(self) -> Stamp:
        candidates = [stamp for stamp in (self.field_min, self.git_added_at) if stamp]
        candidates.append(self.mtime)
        return min(candidates, key=lambda stamp: _comparable(stamp.moment))

    def to_dict(self) -> dict[str, object]:
        earliest = self.earliest()
        return {
            "path": str(self.path),
            "kind": str(self.kind),
            "mtime": self.mtime.text(),
            "git_added_at": self.git_added_at.text() if self.git_added_at else None,
            "field_min": self.field_min.text() if self.field_min else None,
            "field_max": self.field_max.text() if self.field_max else None,
            "earliest": earliest.text(),
            "earliest_basis": earliest.basis,
        }


def _comparable(moment: datetime) -> datetime:
    """Aware datetime; a naive one is read as local time."""
    return moment if moment.tzinfo else moment.astimezone()


def _stamp(text: str | None, basis: str) -> Stamp | None:
    moment = parse_time(text)
    if moment is None:
        return None
    return Stamp(moment, basis if moment.tzinfo else f"{basis}(오프셋 없음)")


# --- rule side ------------------------------------------------------------------


def _header_date(text: str) -> Stamp | None:
    head = "\n".join(text.splitlines()[:HEADER_LINES])
    for pattern in HEADER_DATE_PATTERNS:
        match = pattern.search(head)
        if match:
            day = date.fromisoformat(match.group(1))
            return Stamp(
                datetime.combine(day, time()), "header(날짜만)", is_date_only=True
            )
    return None


def _git_added(path: Path, git: GitQueries) -> Stamp | None:
    root = git.toplevel(path.parent)
    relative = relative_posix(path, root) if root else None
    if root is None or relative is None:
        return None
    return _stamp(git.first_added_time(root, relative), "git")


def _rule_times(
    edition: RuleEdition, sha_dir: Path | None, git: GitQueries
) -> RuleTimes:
    seal_path = seal_path_for(edition, sha_dir)
    seal = parse_seal_file(seal_path) if seal_path.is_file() else None
    body = read_text_facts(edition.path).text
    declared_text = f"{seal.note if seal else ''}\n{body}"
    return RuleTimes(
        edition=edition,
        sealed_at=_stamp(seal.sealed_at if seal else None, "sha256"),
        git_added_at=_git_added(edition.path, git),
        header_date=_header_date(body),
        declares_after=any(
            pattern.search(declared_text) for pattern in AFTER_DECLARATIONS
        ),
    )


# --- result side ----------------------------------------------------------------------


def _record_time(value: object) -> datetime | None:
    if isinstance(value, str):
        return parse_time(value)
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if is_number and value >= MIN_EPOCH_S:
        return datetime.fromtimestamp(float(value)).astimezone()
    return None


def result_kind(path: Path) -> ResultKind:
    """The reading mode for a result file, chosen by its suffix.

    Raises:
        InputError: If the suffix is not a supported result format.
    """
    kind = RESULT_KIND_BY_SUFFIX.get(path.suffix.lower())
    if kind is None:
        supported = ", ".join(sorted(RESULT_KIND_BY_SUFFIX))
        raise InputError(f"unsupported result file ({supported}): {path}")
    return kind


def _csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        text, _ = decode_bytes(path.read_bytes())
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    return list(csv.DictReader(io.StringIO(text, newline="")))


def _field_values(path: Path, kind: ResultKind, field_path: str) -> Iterator[object]:
    """Values of ``field_path`` in every record or row that has it."""
    if kind == ResultKind.TABLE:
        for row in _csv_rows(path):
            value = row.get(field_path)
            if value:
                yield value
        return
    if kind == ResultKind.RECORDS:
        for record in load_records(path).records:
            found, value = get_dotted(record.data, field_path)
            if found:
                yield value


def _field_range(
    path: Path, kind: ResultKind, field_path: str | None
) -> tuple[Stamp | None, Stamp | None]:
    if not field_path:
        return None, None
    moments = []
    for value in _field_values(path, kind, field_path):
        moment = _record_time(value)
        if moment is not None:
            moments.append(moment)
    if not moments:
        return None, None
    basis = f"field:{field_path}"
    earliest = min(moments, key=_comparable)
    latest = max(moments, key=_comparable)
    return Stamp(earliest, basis), Stamp(latest, basis)


def _result_times(path: Path, field_path: str | None, git: GitQueries) -> ResultTimes:
    kind = result_kind(path)
    mtime = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    field_min, field_max = _field_range(path, kind, field_path)
    return ResultTimes(
        path, kind, Stamp(mtime, "mtime"), _git_added(path, git), field_min, field_max
    )


def _validate_result(path: Path) -> None:
    """Fail early on an unsupported or unreadable result file."""
    if result_kind(path) == ResultKind.RECORDS:
        load_records(path, sample=1)


# --- comparing ----------------------------------------------------------------------------


def _is_later(rule: Stamp, result: Stamp) -> bool:
    """True if the rule time is after the result time; date-only stamps compare by day."""
    rule_moment, result_moment = _comparable(rule.moment), _comparable(result.moment)
    if rule.is_date_only:
        return rule.moment.date() > result_moment.date()
    return rule_moment > result_moment


def _basis_text(stamp: Stamp, other: Stamp) -> str:
    if stamp.is_date_only:
        return stamp.basis  # compared by calendar day, no time zone involved
    is_mixed = (stamp.moment.tzinfo is None) != (other.moment.tzinfo is None)
    return (
        f"{stamp.basis} [로컬 시간대로 비교]"
        if is_mixed and stamp.moment.tzinfo is None
        else stamp.basis
    )


def _compare(
    rule: RuleTimes, result: ResultTimes
) -> tuple[dict[str, object], list[Finding]]:
    rule_stamp, result_stamp = rule.best(), result.earliest()
    row: dict[str, object] = {
        "rule": str(rule.edition.path),
        "rev": rule.edition.label,
        "result": str(result.path),
        "rule_time": rule_stamp.text() if rule_stamp else None,
        "rule_basis": _basis_text(rule_stamp, result_stamp) if rule_stamp else None,
        "result_time": result_stamp.text(),
        "result_basis": _basis_text(result_stamp, rule_stamp)
        if rule_stamp
        else result_stamp.basis,
        "verdict": "unknown",
    }
    if rule_stamp is None:
        return row, []
    is_after = _is_later(rule_stamp, result_stamp)
    row["verdict"] = "after" if is_after else "before"
    if not is_after:
        return row, []
    message = (
        f"{rule.edition.label} {rule_stamp.text()}({rule_stamp.basis}) > "
        f"{result.path.name} {result_stamp.text()}({result_stamp.basis})"
    )
    if rule.edition.is_original:
        severity, category = Severity.ERROR, "rule_after_results"
    elif rule.declares_after:
        severity, category = Severity.INFO, "rev_after_results_declared"
        message += " — 개정판이 결과 뒤 개정임을 밝힘"
    else:
        severity, category = Severity.WARNING, "rev_after_results"
    return row, [
        Finding(
            severity, category, str(rule.edition.path), 0, message, result.path.name
        )
    ]


def _mtime_only_message(result: ResultTimes) -> str:
    message = "결과 최초 시각의 근거가 mtime이다 [추정]: 체크아웃·덧붙임으로 바뀜"
    if result.kind == ResultKind.DOCUMENT:
        return message + " (md·txt는 레코드 시각이 없어 git 추가 시각과 mtime만 본다)"
    return message + " (--time-field로 레코드 안 시각을 주면 그것을 쓴다)"


def _time_field_findings(
    results: list[ResultTimes], time_field: str | None
) -> list[Finding]:
    if not time_field:
        return []
    return [
        Finding(
            Severity.INFO,
            "time_field_not_applicable",
            str(result.path),
            0,
            f"--time-field {time_field}: md·txt 결과에는 레코드가 없어 쓰지 않았다",
        )
        for result in results
        if result.kind == ResultKind.DOCUMENT
    ]


def _basis_findings(
    rules: list[RuleTimes], results: list[ResultTimes], git: GitQueries
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.sealed_at is None:
            message = "`.sha256`에 봉인 시각 없음(git·머리 날짜로 대신)"
            findings.append(
                Finding(
                    Severity.WARNING,
                    "seal_time_missing",
                    str(rule.edition.path),
                    0,
                    message,
                )
            )
    for result in results:
        if result.earliest().basis == "mtime":
            message = _mtime_only_message(result)
            findings.append(
                Finding(Severity.INFO, "mtime_only_basis", str(result.path), 0, message)
            )
    if git.unavailable_reason:
        findings.append(
            Finding(
                Severity.INFO,
                "git_unavailable",
                "",
                0,
                f"git 미사용: {git.unavailable_reason}",
            )
        )
    return findings


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 시간 순서 점검 (timeline)",
        "",
        "## 규칙 판",
        "",
        "| 판 | 파일 | 봉인 시각 | git 추가 | 머리 날짜 | AFTER 선언 |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["rules"]:
        lines.append(
            f"| {item['rev']} | `{Path(item['path']).name}` | {item['sealed_at'] or '-'} "
            f"| {item['git_added_at'] or '-'} | {item['header_date'] or '-'} | {item['declares_after']} |"
        )
    lines += [
        "",
        "## 결과",
        "",
        "| 파일 | 종류 | mtime | git 추가 | 필드 최소 | 필드 최대 | 최초(근거) |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report["results"]:
        lines.append(
            f"| `{Path(item['path']).name}` | {item['kind']} | {item['mtime']} "
            f"| {item['git_added_at'] or '-'} "
            f"| {item['field_min'] or '-'} | {item['field_max'] or '-'} "
            f"| {item['earliest']} ({item['earliest_basis']}) |"
        )
    lines += [
        "",
        "## 비교",
        "",
        "| 판 | 결과 | 규칙 시각(근거) | 결과 시각(근거) | 판정 |",
        "|---|---|---|---|---|",
    ]
    for row in report["comparisons"]:
        lines.append(
            f"| {row['rev']} | `{Path(row['result']).name}` | {row['rule_time'] or '-'} ({row['rule_basis'] or '-'}) "
            f"| {row['result_time']} ({row['result_basis']}) | {row['verdict']} |"
        )
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    """Drop repeated paths (case-insensitive on Windows), keeping the first order."""
    unique: dict[str, Path] = {}
    for path in paths:
        unique.setdefault(os.path.normcase(str(path)), path)
    return list(unique.values())


def _unique_editions(editions: list[RuleEdition]) -> list[RuleEdition]:
    """One entry per edition file: a rule given twice must not be compared twice."""
    unique: dict[str, RuleEdition] = {}
    for edition in editions:
        unique.setdefault(os.path.normcase(str(edition.path)), edition)
    return list(unique.values())


def _resolve_base(repo: Path | None) -> Path:
    if repo is None:
        return Path.cwd()
    base = repo.expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    return base


def _from_base(path_text: str | Path, base: Path) -> Path:
    """``path_text`` resolved against ``base`` (an absolute path ignores ``base``)."""
    return (base / Path(path_text).expanduser()).resolve()


def run_timeline(args: argparse.Namespace) -> ToolOutcome:
    """Compare rule edition times with result times."""
    base = _resolve_base(args.repo)
    rule_texts = [str(_from_base(text, base)) for text in args.rules]
    editions = _unique_editions(
        collect_editions(rule_texts, include_revisions=args.revs == "auto")
    )
    sha_dir = _from_base(args.sha_dir, base) if args.sha_dir else None
    result_paths = _unique_paths(expand_file_patterns(args.results, base))
    for path in result_paths:
        _validate_result(path)
    require_output_outside(
        args.out,
        [*(edition.path for edition in editions), *result_paths],
        [sha_dir] if sha_dir else [],
    )
    git = GitQueries(enabled=not args.no_git)
    rules = [_rule_times(edition, sha_dir, git) for edition in editions]
    results = [_result_times(path, args.time_field, git) for path in result_paths]

    comparisons: list[dict[str, object]] = []
    findings: list[Finding] = []
    for rule in rules:
        for result in results:
            row, row_findings = _compare(rule, result)
            comparisons.append(row)
            findings += row_findings
    findings += _basis_findings(rules, results, git)
    findings += _time_field_findings(results, args.time_field)
    findings = sort_findings(findings)

    summary = {
        "tool": TOOL_NAME,
        "command": "compare",
        "rules": len(rules),
        "results": len(results),
        "comparisons": len(comparisons),
        "after": sum(1 for row in comparisons if row["verdict"] == "after"),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "repo": str(base),
        "git": git.unavailable_reason or "used",
        "rules": [rule.to_dict() for rule in rules],
        "results": [result.to_dict() for result in results],
        "comparisons": comparisons,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    inputs = [*(edition.path for edition in editions), *result_paths]
    lines = deliver_report(args, _markdown(report, findings), report, inputs)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="timeline.py",
        description="규칙·개정판이 결과보다 먼저 정해졌는지 시각을 비교한다(읽기 전용).",
    )
    # "extend": repeating a multi-value option adds to the list; plain nargs="+"
    # would keep only the last occurrence (argparse last-wins).
    parser.add_argument(
        "--rules",
        nargs="+",
        action="extend",
        required=True,
        help="original rule .md files, relative to --repo (repeatable)",
    )
    parser.add_argument(
        "--results",
        nargs="+",
        action="extend",
        required=True,
        help="result files or glob patterns (.jsonl/.json/.npz/.csv/.md/.txt), "
        "relative to --repo (repeatable)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        help="base folder for relative paths and patterns (default: current folder)",
    )
    parser.add_argument("--revs", choices=("auto", "none"), default="auto")
    parser.add_argument("--sha-dir", type=Path, help="folder of the .sha256 files")
    parser.add_argument(
        "--time-field",
        help="record field holding a time (dotted path; a column name for .csv)",
    )
    parser.add_argument("--no-git", action="store_true", help="never start git")
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_timeline(args))


if __name__ == "__main__":
    sys.exit(main())
