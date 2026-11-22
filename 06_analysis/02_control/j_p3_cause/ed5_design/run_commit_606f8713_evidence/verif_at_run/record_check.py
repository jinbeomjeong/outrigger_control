"""Record check (I and C axes): run identity fields and an independent recount.

``identity`` checks that every record carries the identity fields the rules
require and that fields which must be uniform across a bundle are uniform.
``recount`` selects records with ``--where`` and recounts counts and min / max /
mean from the raw records, then compares them with ``--expect`` values taken
from a judgement document. It never imports a judging tool (independence).

Usage:
    python record_check.py identity FILE [FILE ...] [--require a.b,c]
        [--uniform controller_tag,job.setting] [--expect-count N]
        [--tags PATH --allowed v1,v2] [--meta a.b] [--sample N]
        [--out REPORT] [--format md|json] [--fail-on error|warning]
    python record_check.py recount FILE [FILE ...] [--where a.b=VALUE ...]
        [--count-by a.b] [--min a.b] [--max a.b] [--mean a.b]
        [--expect LABEL=VALUE ...] [--rtol 1e-9] [--sample N] ...

``--no-git`` is accepted (before or after the subcommand) and changes nothing:
record_check never starts git.

Exit codes: 0 nothing at ``--fail-on`` level, 1 findings, 2 input error, 3 bug.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import require_output_outside
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
from _records import (
    ABSENT_TEXT,
    FileKind,
    LoadedFile,
    Record,
    get_dotted,
    load_records,
    split_fields,
    value_text,
)

TOOL_NAME = "record_check"
MAX_VALUES_IN_MESSAGE = 6
STAT_NAMES = ("min", "max", "mean")
DEFAULT_RTOL = 1e-9


@dataclass(frozen=True)
class RecordRef:
    """A record together with the file it came from."""

    loaded: LoadedFile
    record: Record

    def where(self) -> str:
        return f"{self.loaded.path.name} {self.record.locator()}"


@dataclass
class Selection:
    """Records chosen by ``--where`` and the stats computed on them."""

    records: list[RecordRef] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    stats: dict[str, dict[str, object]] = field(default_factory=dict)


# --- shared loading ------------------------------------------------------------


def _load_all(args: argparse.Namespace) -> list[LoadedFile]:
    paths = [Path(text).expanduser().resolve() for text in args.files]
    require_output_outside(args.out, paths)
    if args.sample is not None and args.sample < 1:
        raise InputError("--sample must be >= 1")
    return [load_records(path, args.sample) for path in paths]


def _file_findings(loaded_files: list[LoadedFile]) -> list[Finding]:
    findings: list[Finding] = []
    for loaded in loaded_files:
        for line, message in loaded.parse_errors:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "record_parse_error",
                    str(loaded.path),
                    line,
                    message,
                )
            )
        if loaded.kind != FileKind.NPZ:
            continue
        if loaded.npz_unavailable_reason:
            message = f"npz 건너뜀: {loaded.npz_unavailable_reason}"
        else:
            arrays = "; ".join(
                f"{item['key']} {tuple(item['shape'])} {item['dtype']}"
                for item in loaded.npz_arrays
            )
            message = (
                f"npz 배열 {len(loaded.npz_arrays)}개 (키·shape·dtype만): {arrays}"
            )
        findings.append(
            Finding(Severity.INFO, "npz_keys", str(loaded.path), 0, message)
        )
    return findings


def _all_records(loaded_files: list[LoadedFile]) -> list[RecordRef]:
    return [
        RecordRef(loaded, record)
        for loaded in loaded_files
        for record in loaded.records
    ]


def _values_text(counter: Counter[str]) -> str:
    items = [
        f"{value}×{count}"
        for value, count in counter.most_common(MAX_VALUES_IN_MESSAGE)
    ]
    hidden = len(counter) - MAX_VALUES_IN_MESSAGE
    return ", ".join(items) + (f" 외 {hidden}개" if hidden > 0 else "")


def _field_value(ref: RecordRef, field_path: str) -> tuple[bool, object]:
    return get_dotted(ref.record.data, field_path)


def _sampling_note(loaded_files: list[LoadedFile]) -> list[Finding]:
    return [
        Finding(
            Severity.INFO,
            "sampled",
            str(loaded.path),
            0,
            f"--sample: 전체 {loaded.total_records}건 중 앞·뒤 {len(loaded.records)}건만 봄",
        )
        for loaded in loaded_files
        if loaded.is_sampled
    ]


# --- identity -------------------------------------------------------------------


def _no_records_findings(loaded_files: list[LoadedFile]) -> list[Finding]:
    """Report an error when the record files (jsonl/json) hold no record at all.

    npz files carry arrays, not records, so an npz-only input is not "empty".
    """
    record_files = [item for item in loaded_files if item.kind != FileKind.NPZ]
    if not record_files or any(item.total_records for item in record_files):
        return []
    names = ", ".join(item.path.name for item in record_files)
    message = f"입력 레코드 0건: {names} — 빈 집합은 통과가 아니다"
    return [
        Finding(Severity.ERROR, "no_records", str(record_files[0].path), 0, message)
    ]


def _require_findings(refs: list[RecordRef], fields: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for field_path in fields:
        missing = []
        for ref in refs:
            found, value = _field_value(ref, field_path)
            if not found or value is None:
                missing.append(ref)
        if missing:
            first = missing[0]
            message = (
                f"필수 필드 `{field_path}` 없음(또는 null): {len(missing)}/{len(refs)}건, "
                f"첫 예시 {first.where()}"
            )
            findings.append(
                Finding(
                    Severity.ERROR,
                    "identity_missing",
                    str(first.loaded.path),
                    first.record.line,
                    message,
                    field_path,
                )
            )
    return findings


def _value_counter(refs: list[RecordRef], field_path: str) -> tuple[Counter[str], int]:
    counter: Counter[str] = Counter()
    present = 0
    for ref in refs:
        found, value = _field_value(ref, field_path)
        if found:
            present += 1
        counter[value_text(value) if found else ABSENT_TEXT] += 1
    return counter, present


def _uniform_findings(
    refs: list[RecordRef], fields: list[str], uniform_values: dict[str, dict[str, int]]
) -> list[Finding]:
    findings: list[Finding] = []
    location = str(refs[0].loaded.path) if refs else ""
    for field_path in fields:
        counter, present = _value_counter(refs, field_path)
        uniform_values[field_path] = dict(counter.most_common())
        if present == 0:
            message = f"`{field_path}`가 모든 레코드에 없음"
            findings.append(
                Finding(
                    Severity.INFO,
                    "identity_field_absent",
                    location,
                    0,
                    message,
                    field_path,
                )
            )
        elif len(counter) > 1:
            message = f"`{field_path}` 고유값 {len(counter)}개: {_values_text(counter)}"
            findings.append(
                Finding(
                    Severity.ERROR, "identity_mixed", location, 0, message, field_path
                )
            )
    return findings


def _count_findings(
    loaded_files: list[LoadedFile], expected: int | None
) -> list[Finding]:
    if expected is None:
        return []
    return [
        Finding(
            Severity.ERROR,
            "count_mismatch",
            str(loaded.path),
            0,
            f"레코드 {loaded.total_records}건 ≠ 기대 {expected}건",
        )
        for loaded in loaded_files
        if loaded.kind != FileKind.NPZ and loaded.total_records != expected
    ]


def _tag_findings(
    refs: list[RecordRef], tag_path: str | None, allowed: list[str]
) -> list[Finding]:
    if not tag_path:
        return []
    counter, _ = _value_counter(refs, tag_path)
    bad = Counter(
        {value: count for value, count in counter.items() if value not in allowed}
    )
    if not bad:
        return []
    first = refs[0]
    for ref in refs:
        found, value = _field_value(ref, tag_path)
        if (value_text(value) if found else ABSENT_TEXT) in bad:
            first = ref
            break
    message = (
        f"허용 밖 `{tag_path}` {sum(bad.values())}건: {_values_text(bad)} "
        f"(허용: {', '.join(allowed)})"
    )
    return [
        Finding(
            Severity.ERROR,
            "tag_not_allowed",
            str(first.loaded.path),
            first.record.line,
            message,
            tag_path,
        )
    ]


def _first_last_findings(
    loaded_files: list[LoadedFile],
) -> tuple[list[Finding], dict[str, object]]:
    findings: list[Finding] = []
    first_keys: dict[str, object] = {}
    for loaded in loaded_files:
        dict_records = [
            record for record in loaded.records if isinstance(record.data, dict)
        ]
        if not dict_records:
            continue
        first, last = dict_records[0], dict_records[-1]
        first_keys[str(loaded.path)] = list(first.data)
        only_first = sorted(set(first.data) - set(last.data))
        only_last = sorted(set(last.data) - set(first.data))
        if only_first or only_last:
            message = (
                f"첫({first.locator()})·마지막({last.locator()}) 최상위 키 차이 — "
                f"첫에만: {', '.join(only_first) or '-'} / 마지막에만: {', '.join(only_last) or '-'}"
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "keys_first_last_differ",
                    str(loaded.path),
                    0,
                    message,
                )
            )
    return findings, first_keys


def _meta_findings(
    loaded_files: list[LoadedFile],
    meta_fields: list[str],
    meta_values: dict[str, dict[str, object]],
) -> list[Finding]:
    findings: list[Finding] = []
    for field_path in meta_fields:
        per_file: dict[str, object] = {}
        for loaded in loaded_files:
            if loaded.container is None:
                continue
            found, value = get_dotted(loaded.container, field_path)
            per_file[str(loaded.path)] = value if found else ABSENT_TEXT
        meta_values[field_path] = per_file
        distinct = {value_text(value) for value in per_file.values()}
        if len(distinct) > 1:
            message = f"파일 메타 `{field_path}`가 파일마다 다름: {', '.join(sorted(distinct))}"
            findings.append(
                Finding(Severity.ERROR, "identity_mixed", "", 0, message, field_path)
            )
        elif ABSENT_TEXT in distinct or not per_file:
            message = f"파일 메타 `{field_path}` 없음(json 묶음 파일만 메타가 있음)"
            findings.append(
                Finding(
                    Severity.INFO, "identity_field_absent", "", 0, message, field_path
                )
            )
    return findings


def run_identity(args: argparse.Namespace) -> ToolOutcome:
    """Check identity fields of the records."""
    if bool(args.tags) != bool(args.allowed):
        raise InputError("--tags and --allowed go together")
    loaded_files = _load_all(args)
    refs = _all_records(loaded_files)
    uniform_values: dict[str, dict[str, int]] = {}
    meta_values: dict[str, dict[str, object]] = {}
    findings = _file_findings(loaded_files) + _sampling_note(loaded_files)
    findings += _no_records_findings(loaded_files)
    findings += _require_findings(refs, split_fields(args.require))
    findings += _uniform_findings(refs, split_fields(args.uniform), uniform_values)
    findings += _count_findings(loaded_files, args.expect_count)
    findings += _tag_findings(refs, args.tags, split_fields(args.allowed))
    first_last, first_keys = _first_last_findings(loaded_files)
    findings += first_last
    findings += _meta_findings(loaded_files, split_fields(args.meta), meta_values)
    findings = sort_findings(findings)

    total = sum(loaded.total_records for loaded in loaded_files)
    summary = {
        "tool": TOOL_NAME,
        "command": "identity",
        "files": len(loaded_files),
        "records": total,
        "records_checked": len(refs),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "command": "identity",
        "files": [_file_summary(loaded) for loaded in loaded_files],
        "records": total,
        "first_record_keys": first_keys,
        "uniform_values": uniform_values,
        "meta_values": meta_values,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(
        args,
        _identity_markdown(report, findings),
        report,
        [loaded.path for loaded in loaded_files],
    )
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def _file_summary(loaded: LoadedFile) -> dict[str, object]:
    return {
        "path": str(loaded.path),
        "kind": str(loaded.kind),
        "records": loaded.total_records,
        "checked": len(loaded.records),
        "sampled": loaded.is_sampled,
        "container_key": loaded.container_key,
    }


def _files_table(files: list[dict[str, object]]) -> list[str]:
    lines = ["| 파일 | 형식 | 레코드 | 본 레코드 |", "|---|---|---|---|"]
    for item in files:
        lines.append(
            f"| `{Path(str(item['path'])).name}` | {item['kind']} | {item['records']} | {item['checked']} |"
        )
    return lines


def _identity_markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 실행 정체성 점검 (record_check identity)",
        "",
        *_files_table(report["files"]),
        "",
    ]
    for path, keys in report["first_record_keys"].items():
        lines.append(f"- `{Path(path).name}` 첫 레코드 최상위 키: {', '.join(keys)}")
    if report["uniform_values"]:
        lines += [
            "",
            "## 균일해야 할 필드",
            "",
            "| 필드 | 값 | 건수 |",
            "|---|---|---|",
        ]
        for field_path, values in report["uniform_values"].items():
            for value, count in values.items():
                lines.append(f"| `{field_path}` | {value} | {count} |")
    if report["meta_values"]:
        lines += ["", "## 파일 메타", "", "| 필드 | 파일 | 값 |", "|---|---|---|"]
        for field_path, per_file in report["meta_values"].items():
            for path, value in per_file.items():
                lines.append(
                    f"| `{field_path}` | `{Path(path).name}` | {value_text(value)} |"
                )
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


# --- recount ----------------------------------------------------------------------


def _as_number(text: str) -> float | None:
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _matches(value: object, expected_text: str) -> bool:
    if value_text(value) == expected_text:
        return True
    expected_number = _as_number(expected_text)
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    return expected_number is not None and is_number and float(value) == expected_number


def _parse_where(items: list[str]) -> list[tuple[str, str]]:
    conditions = []
    for item in items:
        field_path, separator, expected = item.partition("=")
        if not separator or not field_path.strip():
            raise InputError(f"--where needs FIELD=VALUE: {item!r}")
        conditions.append((field_path.strip(), expected))
    return conditions


def _select(
    refs: list[RecordRef], conditions: list[tuple[str, str]]
) -> list[RecordRef]:
    selected = []
    for ref in refs:
        is_match = True
        for field_path, expected in conditions:
            found, value = _field_value(ref, field_path)
            if not found or not _matches(value, expected):
                is_match = False
                break
        if is_match:
            selected.append(ref)
    return selected


def _numeric_stat(
    refs: list[RecordRef], field_path: str, stat: str, findings: list[Finding]
) -> dict[str, object]:
    numbers: list[float] = []
    non_numeric = absent = 0
    for ref in refs:
        found, value = _field_value(ref, field_path)
        if not found:
            absent += 1
        elif (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        ):
            numbers.append(float(value))
        else:
            non_numeric += 1
    location = str(refs[0].loaded.path) if refs else ""
    if refs and absent == len(refs):
        message = f"`{field_path}`가 고른 레코드 모두에 없음"
        findings.append(
            Finding(Severity.WARNING, "field_absent", location, 0, message, field_path)
        )
    if non_numeric:
        message = f"`{field_path}` 숫자 아님(null·문자열 등) {non_numeric}건 제외"
        findings.append(
            Finding(
                Severity.INFO, "non_numeric_skipped", location, 0, message, field_path
            )
        )
    value: float | None = None
    if numbers and stat == "min":
        value = min(numbers)
    elif numbers and stat == "max":
        value = max(numbers)
    elif numbers:
        value = math.fsum(numbers) / len(numbers)
    return {
        "field": field_path,
        "stat": stat,
        "value": value,
        "n": len(numbers),
        "non_numeric": non_numeric,
        "absent": absent,
    }


def _count_values(refs: list[RecordRef], field_path: str | None) -> dict[str, int]:
    if not field_path:
        return {}
    counter: Counter[str] = Counter()
    for ref in refs:
        found, value = _field_value(ref, field_path)
        counter[value_text(value) if found else ABSENT_TEXT] += 1
    return dict(sorted(counter.items()))


def _actual_for(
    label: str, selection: Selection, stat_fields: dict[str, list[str]]
) -> float | None:
    if label == "selected":
        return float(len(selection.records))
    for prefix in ("count:", "count_by:"):
        if label.startswith(prefix):
            return float(selection.counts.get(label[len(prefix) :], 0))
    stat, _, field_path = label.partition(":")
    if stat not in STAT_NAMES:
        raise InputError(
            f"unknown --expect label {label!r} (count:<v>, count_by:<v>, min, max, mean, selected)"
        )
    fields = [field_path] if field_path else stat_fields[stat]
    if len(fields) != 1:
        raise InputError(
            f"--expect {stat} is ambiguous or has no --{stat}: use {stat}:<field>"
        )
    key = f"{stat}:{fields[0]}"
    if key not in selection.stats:
        raise InputError(f"--expect {label}: add --{stat} {fields[0]}")
    value = selection.stats[key]["value"]
    return None if value is None else float(value)


def _expectations(
    items: list[str],
    selection: Selection,
    stat_fields: dict[str, list[str]],
    rtol: float,
) -> tuple[list[dict[str, object]], list[Finding]]:
    results: list[dict[str, object]] = []
    findings: list[Finding] = []
    for item in items:
        label, separator, expected_text = item.rpartition("=")
        expected = _as_number(expected_text)
        if not separator or not label or expected is None:
            raise InputError(f"--expect needs LABEL=NUMBER: {item!r}")
        actual = _actual_for(label, selection, stat_fields)
        diff = None if actual is None else actual - expected
        is_count = label == "selected" or label.startswith("count")
        if actual is None:
            is_ok = False
        elif is_count:
            is_ok = actual == expected
        else:
            is_ok = abs(diff) <= rtol * max(abs(expected), abs(actual))
        results.append(
            {
                "label": label,
                "expected": expected,
                "actual": actual,
                "diff": diff,
                "ok": is_ok,
            }
        )
        if not is_ok:
            message = f"{label}: 재집계 {actual} ≠ 기대 {expected} (차이 {diff}, rtol {rtol:g})"
            findings.append(
                Finding(Severity.ERROR, "expect_mismatch", "", 0, message, label)
            )
    return results, findings


def run_recount(args: argparse.Namespace) -> ToolOutcome:
    """Recount the selected records and compare with ``--expect``."""
    loaded_files = _load_all(args)
    conditions = _parse_where(args.where or [])
    findings = _file_findings(loaded_files) + _sampling_note(loaded_files)
    refs = _all_records(loaded_files)
    selection = Selection(records=_select(refs, conditions))
    if not selection.records:
        where_text = (
            " AND ".join(f"{path}={value}" for path, value in conditions)
            or "(조건 없음)"
        )
        message = f"고른 레코드 0건: {where_text} — 빈 집합은 통과가 아니다"
        location = str(loaded_files[0].path) if loaded_files else ""
        findings.append(
            Finding(Severity.ERROR, "selection_empty", location, 0, message)
        )
    selection.counts = _count_values(selection.records, args.count_by)
    stat_fields = {
        "min": args.min or [],
        "max": args.max or [],
        "mean": args.mean or [],
    }
    for stat, fields in stat_fields.items():
        for field_path in fields:
            selection.stats[f"{stat}:{field_path}"] = _numeric_stat(
                selection.records, field_path, stat, findings
            )
    expectations, expect_findings = _expectations(
        args.expect or [], selection, stat_fields, args.rtol
    )
    findings = sort_findings(findings + expect_findings)

    total = sum(loaded.total_records for loaded in loaded_files)
    summary = {
        "tool": TOOL_NAME,
        "command": "recount",
        "records": total,
        "selected": len(selection.records),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "command": "recount",
        "files": [_file_summary(loaded) for loaded in loaded_files],
        "where": [f"{path}={value}" for path, value in conditions],
        "records": total,
        "selected": len(selection.records),
        "counts": selection.counts,
        "stats": selection.stats,
        "expectations": expectations,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(
        args,
        _recount_markdown(report, findings),
        report,
        [loaded.path for loaded in loaded_files],
    )
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def _recount_markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 독립 재집계 (record_check recount)",
        "",
        *_files_table(report["files"]),
        "",
        f"- 조건: {' AND '.join(report['where']) or '(없음)'}",
        f"- 레코드 {report['records']}건 중 고른 레코드 {report['selected']}건",
    ]
    if report["counts"]:
        lines += ["", "## 값별 건수", "", "| 값 | 건수 |", "|---|---|"]
        lines += [f"| {value} | {count} |" for value, count in report["counts"].items()]
    if report["stats"]:
        lines += [
            "",
            "## 통계",
            "",
            "| 통계 | 필드 | 값 | 숫자 n | 제외 |",
            "|---|---|---|---|---|",
        ]
        for item in report["stats"].values():
            lines.append(
                f"| {item['stat']} | `{item['field']}` | {item['value']} | {item['n']} "
                f"| {item['non_numeric'] + item['absent']} |"
            )
    if report["expectations"]:
        lines += [
            "",
            "## 기대값 대조",
            "",
            "| 항목 | 기대 | 재집계 | 차이 | 일치 |",
            "|---|---|---|---|---|",
        ]
        for item in report["expectations"]:
            lines.append(
                f"| {item['label']} | {item['expected']} | {item['actual']} | {item['diff']} | {item['ok']} |"
            )
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


# --- command line --------------------------------------------------------------------


def _add_no_git(parser: argparse.ArgumentParser, default: object) -> None:
    # record_check never starts git; the flag exists so the shared tool contract
    # (every verif tool takes --no-git) does not end in an argument error.
    parser.add_argument(
        "--no-git",
        action="store_true",
        default=default,
        help="accepted for the shared contract; record_check never starts git",
    )


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", help="result files (.jsonl, .json, .npz)")
    parser.add_argument(
        "--sample", type=int, help="look only at the first and last N records"
    )
    # SUPPRESS: a --no-git given before the subcommand is not reset to False here.
    _add_no_git(parser, argparse.SUPPRESS)
    add_report_arguments(parser)


def build_parser() -> argparse.ArgumentParser:
    """Return the parser with the ``identity`` and ``recount`` subcommands."""
    parser = argparse.ArgumentParser(
        prog="record_check.py",
        description="결과 레코드의 실행 정체성 점검과 독립 재집계(읽기 전용).",
    )
    _add_no_git(parser, False)
    commands = parser.add_subparsers(dest="command", required=True)

    identity = commands.add_parser("identity", help="필수·균일 필드, 건수, 태그")
    _add_common(identity)
    identity.add_argument(
        "--require", help="comma-separated dotted fields every record needs"
    )
    identity.add_argument(
        "--uniform", help="comma-separated dotted fields with one value"
    )
    identity.add_argument("--expect-count", type=int, help="records expected per file")
    identity.add_argument("--tags", help="dotted tag field checked against --allowed")
    identity.add_argument("--allowed", help="comma-separated allowed tag values")
    identity.add_argument(
        "--meta", help="comma-separated dotted fields of the json file meta"
    )

    recount = commands.add_parser(
        "recount", help="조건 선택 후 건수·최솟값·최댓값·평균"
    )
    _add_common(recount)
    recount.add_argument("--where", action="append", help="FIELD=VALUE (repeat = AND)")
    recount.add_argument("--count-by", help="dotted field to count values of")
    recount.add_argument("--min", action="append", help="dotted numeric field")
    recount.add_argument("--max", action="append", help="dotted numeric field")
    recount.add_argument("--mean", action="append", help="dotted numeric field")
    recount.add_argument(
        "--expect",
        action="append",
        help="LABEL=NUMBER; labels count:<v>, count_by:<v>, min[:field], max[:field], "
        "mean[:field], selected",
    )
    recount.add_argument(
        "--rtol", type=float, default=DEFAULT_RTOL, help="relative tolerance"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    if args.command == "identity":
        return run_tool(lambda: run_identity(args))
    return run_tool(lambda: run_recount(args))


if __name__ == "__main__":
    sys.exit(main())
