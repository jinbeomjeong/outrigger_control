"""Replay recount (I and C axes): join replayed records to the stored originals.

A replay run re-executes stored result lines and writes one record per run
(its key, the new command hash, often a copy of the stored hash). This tool
joins those records to the stored original jsonl by key and checks, without
importing any project code:

(a) selection - the replayed keys are exactly the keys the selection rule picks
    from the originals (e.g. ``r4+20`` = every line with an applied R4 event
    plus the first 20 others): nothing missing, nothing extra, no duplicate;
(b) hashes - replay hash == original hash, and the replay's stored-hash copy
    == original hash (when ``--replay-stored-hash`` is given);
(c) counts - how many selected originals (``--count``) or replay records
    (``--count-replay``) satisfy a predicate, e.g. ``k1.would_block_any``.

Several replay files (a stopped run resumed as part 1 + part 2) are merged; a
key that appears twice is an error.

Key specs (``--replay-key`` / ``--source-key``; repeat = fallbacks, the first
spec that resolves wins, like ``a or b`` in a harness):
    ``rev.key``                       one dotted field
    ``rev.key,k1.sub_bundle``         several fields -> a tuple key
    ``{job.d1.key}({job.setting!r}, {job.eps!r})``
                                      a template; ``!r`` is the Python repr of
                                      the JSON value (``'VB'``, ``0.002``)
A spec does not resolve when a field is missing, ``null`` or ``""``.

Predicates (``--source-where``, ``--select-flagged``, ``--count``):
    ``PATH`` truthy, ``not:PATH`` falsy, ``has:PATH`` present,
    ``no:PATH`` absent, ``PATH=VALUE`` equal (numbers compare as numbers).

Usage:
    python replay_recount.py --replay PART1.jsonl PART2.jsonl --source d1.jsonl
        --replay-key key --source-key rev.key
        --source-key "{job.d1.key}({job.setting!r}, {job.eps!r})"
        --source-where no:error
        --select-flagged has:event_names.INFO_LOC_FLAT_SOIL_MARGIN --select-others 20
        --replay-stored-hash stored_hash --count k1.would_block_any
        [--expect selected=189 ...] [--out REPORT] [--format md|json]

Exit codes: 0 everything matches, 1 mismatch (findings), 2 input or argument
error, 3 bug.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
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
from _records import LoadedFile, Record, get_dotted, load_records, value_text

TOOL_NAME = "replay_recount"
MAX_KEYS_IN_MESSAGE = 5
MAX_KEYS_IN_MARKDOWN = 30
PLACEHOLDER = re.compile(r"\{([^{}!]+)(?:!(r))?\}")
KEY_JOINER = " / "
DEFAULT_REPLAY_KEY = "key"
DEFAULT_REPLAY_HASH = "hash"
DEFAULT_SOURCE_HASH = "commands_sha256"
DEFAULT_REPLAY_ERROR_FIELD = "error"
COUNT_PREFIX = "count:"
REPLAY_COUNT_PREFIX = "replay_count:"

Key = tuple[str, ...]


class DuplicatePolicy(StrEnum):
    """What to do with an original key that occurs more than once."""

    ERROR = "error"
    LAST = "last"  # later attempt wins (resumed harness runs), first position kept
    FIRST = "first"


class PredicateKind(StrEnum):
    """How a predicate tests its field."""

    TRUTHY = "truthy"
    FALSY = "falsy"
    PRESENT = "present"
    ABSENT = "absent"
    EQUALS = "equals"


PREDICATE_PREFIXES = {
    "not:": PredicateKind.FALSY,
    "has:": PredicateKind.PRESENT,
    "no:": PredicateKind.ABSENT,
}


def _as_number(text: str) -> float | None:
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _equals(value: object, expected_text: str) -> bool:
    if value_text(value) == expected_text:
        return True
    expected_number = _as_number(expected_text)
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    return expected_number is not None and is_number and float(value) == expected_number


def _is_blank(value: object) -> bool:
    return value is None or value == ""


@dataclass(frozen=True)
class Predicate:
    """A test on one record, kept with its command-line text."""

    text: str
    kind: PredicateKind
    path: str
    expected: str = ""

    def holds(self, data: object) -> bool:
        found, value = get_dotted(data, self.path)
        if self.kind == PredicateKind.PRESENT:
            return found
        if self.kind == PredicateKind.ABSENT:
            return not found
        if self.kind == PredicateKind.EQUALS:
            return found and _equals(value, self.expected)
        is_truthy = found and bool(value)
        return is_truthy if self.kind == PredicateKind.TRUTHY else not is_truthy


def _render_template(template: str, data: object) -> str | None:
    is_resolved = True

    def substitute(match: re.Match[str]) -> str:
        nonlocal is_resolved
        found, value = get_dotted(data, match.group(1).strip())
        if not found or _is_blank(value):
            is_resolved = False
            return ""
        return repr(value) if match.group(2) == "r" else value_text(value)

    rendered = PLACEHOLDER.sub(substitute, template)
    return rendered if is_resolved else None


@dataclass(frozen=True)
class KeySpec:
    """One way to build a record key: dotted fields or a template."""

    text: str
    fields: tuple[str, ...] = ()
    template: str = ""

    def resolve(self, data: object) -> Key | None:
        if self.template:
            rendered = _render_template(self.template, data)
            return None if rendered is None else (rendered,)
        parts = []
        for field_path in self.fields:
            found, value = get_dotted(data, field_path)
            if not found or _is_blank(value):
                return None
            parts.append(value_text(value))
        return tuple(parts)


@dataclass(frozen=True)
class KeyedRecord:
    """A record, the file it came from and its resolved key."""

    loaded: LoadedFile
    record: Record
    key: Key

    def where(self) -> str:
        return f"{self.loaded.path.name} {self.record.locator()}"

    def field_text(self, field_path: str) -> str | None:
        found, value = get_dotted(self.record.data, field_path)
        return None if not found or _is_blank(value) else value_text(value)


@dataclass(frozen=True)
class SourceRules:
    """How original records are filtered, keyed, de-duplicated and selected."""

    key_specs: list[KeySpec]
    conditions: list[Predicate]
    memberships: list[tuple[str, frozenset[str]]]
    duplicates: DuplicatePolicy
    flag: Predicate | None
    others: int | None


@dataclass(frozen=True)
class HashFields:
    """Field names of the hashes on each side."""

    replay: str
    stored: str | None
    source: str


@dataclass
class Joined:
    """Everything collected while joining the replay to the originals."""

    replay: dict[Key, KeyedRecord] = field(default_factory=dict)
    source: dict[Key, KeyedRecord] = field(default_factory=dict)
    selected: dict[Key, KeyedRecord] = field(default_factory=dict)
    flagged: set[Key] = field(default_factory=set)
    problems: dict[str, list[str]] = field(default_factory=dict)
    numbers: dict[str, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    replay_counts: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add_problem(self, category: str, items: Iterable[str], what: str) -> None:
        """Record a list-type problem once: count and first items; all in JSON."""
        listed = list(items)
        if not listed:
            return
        self.problems[category] = listed
        shown = "; ".join(listed[:MAX_KEYS_IN_MESSAGE])
        hidden = len(listed) - MAX_KEYS_IN_MESSAGE
        more = f" 외 {hidden}개" if hidden > 0 else ""
        message = f"{what} {len(listed)}건: {shown}{more}"
        self.findings.append(Finding(Severity.ERROR, category, "", 0, message))


def key_text(key: Key) -> str:
    """Readable form of a key (fields joined by `` / ``)."""
    return KEY_JOINER.join(key)


# --- parsing specs ------------------------------------------------------------------


def parse_predicate(text: str) -> Predicate:
    """Parse ``PATH``, ``not:PATH``, ``has:PATH``, ``no:PATH`` or ``PATH=VALUE``.

    Raises:
        InputError: If the field path is empty.
    """
    for prefix, kind in PREDICATE_PREFIXES.items():
        if text.startswith(prefix):
            path = text[len(prefix) :].strip()
            if not path:
                raise InputError(f"predicate without a field: {text!r}")
            return Predicate(text, kind, path)
    path, separator, expected = text.partition("=")
    if not path.strip():
        raise InputError(f"predicate without a field: {text!r}")
    if separator:
        return Predicate(text, PredicateKind.EQUALS, path.strip(), expected)
    return Predicate(text, PredicateKind.TRUTHY, path.strip())


def parse_key_spec(text: str) -> KeySpec:
    """Parse a key spec: ``a.b,c`` (fields) or a template with ``{a.b}``.

    Raises:
        InputError: If the spec names no field.
    """
    if "{" in text:
        if not PLACEHOLDER.search(text):
            raise InputError(f"key template without a {{field}}: {text!r}")
        return KeySpec(text, template=text)
    fields = tuple(item.strip() for item in text.split(",") if item.strip())
    if not fields:
        raise InputError(f"empty key spec: {text!r}")
    return KeySpec(text, fields=fields)


def _parse_membership(text: str) -> tuple[str, frozenset[str]]:
    path, separator, values = text.partition("=")
    members = frozenset(item.strip() for item in values.split(",") if item.strip())
    if not separator or not path.strip() or not members:
        raise InputError(f"--source-in needs FIELD=V1,V2,...: {text!r}")
    return path.strip(), members


def _resolve_key(data: object, specs: list[KeySpec]) -> Key | None:
    for spec in specs:
        key = spec.resolve(data)
        if key is not None:
            return key
    return None


def _source_rules(args: argparse.Namespace) -> SourceRules:
    if args.select_others is not None and args.select_others < 0:
        raise InputError("--select-others must be >= 0")
    return SourceRules(
        key_specs=[parse_key_spec(text) for text in args.source_key],
        conditions=[parse_predicate(text) for text in args.source_where or []],
        memberships=[_parse_membership(text) for text in args.source_in or []],
        duplicates=DuplicatePolicy(args.source_duplicates),
        flag=parse_predicate(args.select_flagged) if args.select_flagged else None,
        others=args.select_others,
    )


# --- joining --------------------------------------------------------------------------


def _parse_error_findings(loaded_files: list[LoadedFile]) -> list[Finding]:
    return [
        Finding(Severity.ERROR, "record_parse_error", str(loaded.path), line, message)
        for loaded in loaded_files
        for line, message in loaded.parse_errors
    ]


def _key_replay(
    loaded_files: list[LoadedFile], specs: list[KeySpec], joined: Joined
) -> None:
    unkeyed: list[str] = []
    duplicates: list[str] = []
    for loaded in loaded_files:
        for record in loaded.records:
            key = _resolve_key(record.data, specs)
            if key is None:
                unkeyed.append(f"{loaded.path.name} {record.locator()}")
            elif key in joined.replay:
                first = joined.replay[key].where()
                second = f"{loaded.path.name} {record.locator()}"
                duplicates.append(f"{key_text(key)} ({first} · {second})")
            else:
                joined.replay[key] = KeyedRecord(loaded, record, key)
    joined.add_problem("replay_key_missing", unkeyed, "재생 키를 못 만든 줄")
    joined.add_problem("replay_key_duplicate", duplicates, "재생 키 중복")


def _passes_filters(data: object, rules: SourceRules) -> bool:
    if not all(condition.holds(data) for condition in rules.conditions):
        return False
    for path, members in rules.memberships:
        found, value = get_dotted(data, path)
        if not found or value_text(value) not in members:
            return False
    return True


def _key_source(
    loaded_files: list[LoadedFile], rules: SourceRules, joined: Joined
) -> None:
    unkeyed: list[str] = []
    repeated: list[str] = []
    filtered = 0
    for loaded in loaded_files:
        for record in loaded.records:
            if not _passes_filters(record.data, rules):
                continue
            filtered += 1
            key = _resolve_key(record.data, rules.key_specs)
            if key is None:
                unkeyed.append(f"{loaded.path.name} {record.locator()}")
                continue
            keyed = KeyedRecord(loaded, record, key)
            if key in joined.source:
                repeated.append(
                    f"{key_text(key)} ({joined.source[key].where()} · {keyed.where()})"
                )
                if rules.duplicates != DuplicatePolicy.LAST:
                    continue
            joined.source[key] = keyed  # re-assigning keeps the first position
    joined.numbers["source_filtered"] = filtered
    joined.add_problem("source_key_missing", unkeyed, "원본 키를 못 만든 줄")
    _report_source_duplicates(joined, repeated, rules.duplicates)


def _report_source_duplicates(
    joined: Joined, repeated: list[str], policy: DuplicatePolicy
) -> None:
    if policy == DuplicatePolicy.ERROR:
        what = "원본 키 중복(정책은 --source-duplicates last|first로 정한다)"
        joined.add_problem("source_key_duplicate", repeated, what)
        return
    if not repeated:
        return
    joined.problems["source_key_duplicate_resolved"] = repeated
    message = f"원본 키 중복 {len(repeated)}건을 `{policy}` 정책으로 하나씩 남김"
    joined.findings.append(
        Finding(Severity.INFO, "source_key_duplicate_resolved", "", 0, message)
    )


def _select(rules: SourceRules, joined: Joined) -> None:
    """Flagged originals all, then the first ``others`` unflagged (source order)."""
    if rules.flag is None and rules.others is None:
        joined.selected = dict(joined.source)
        return
    others_left = rules.others or 0
    for key, keyed in joined.source.items():
        if rules.flag is not None and rules.flag.holds(keyed.record.data):
            joined.selected[key] = keyed
            joined.flagged.add(key)
        elif others_left > 0:
            joined.selected[key] = keyed
            others_left -= 1


def _compare_selection(joined: Joined) -> None:
    missing = [key_text(key) for key in joined.selected if key not in joined.replay]
    not_selected = []
    unknown = []
    for key in joined.replay:
        if key not in joined.source:
            unknown.append(key_text(key))
        elif key not in joined.selected:
            not_selected.append(key_text(key))
    joined.add_problem("selection_missing", missing, "선택됐는데 재생되지 않은 키")
    joined.add_problem(
        "replay_not_selected", not_selected, "선택 규칙 밖인데 재생된 키"
    )
    joined.add_problem("replay_key_unknown", unknown, "원본(필터 뒤)에 없는 재생 키")
    joined.numbers["matched"] = sum(1 for key in joined.replay if key in joined.source)


def _compare_hashes(joined: Joined, fields: HashFields) -> None:
    missing: list[str] = []
    different: list[str] = []
    stored_different: list[str] = []
    same = 0
    for key, replayed in joined.replay.items():
        original = joined.source.get(key)
        if original is None:
            continue
        source_hash = original.field_text(fields.source)
        replay_hash = replayed.field_text(fields.replay)
        if source_hash is None or replay_hash is None:
            side = "원본" if source_hash is None else "재생"
            missing.append(f"{key_text(key)} ({side})")
        elif replay_hash != source_hash:
            different.append(
                f"{key_text(key)} ({replay_hash[:12]} ≠ {source_hash[:12]})"
            )
        else:
            same += 1
        if fields.stored and replayed.field_text(fields.stored) != source_hash:
            stored_different.append(key_text(key))
    joined.numbers["hash_same"] = same
    joined.add_problem("hash_missing", missing, "해시 없음(null 포함)")
    joined.add_problem("hash_mismatch", different, "재생 해시 ≠ 원본 해시")
    joined.add_problem(
        "stored_hash_mismatch", stored_different, "재생 기록의 저장 해시 ≠ 원본 해시"
    )


def _replay_errors(joined: Joined, error_field: str) -> None:
    has_error = Predicate(error_field, PredicateKind.TRUTHY, error_field)
    failed = [
        f"{key_text(key)} ({keyed.where()})"
        for key, keyed in joined.replay.items()
        if has_error.holds(keyed.record.data)
    ]
    joined.add_problem("replay_error", failed, f"재생 실패(`{error_field}` 값 있음)")


def _count_predicates(
    records: Iterable[KeyedRecord], texts: list[str]
) -> dict[str, int]:
    kept = list(records)
    counts: dict[str, int] = {}
    for text in texts:
        predicate = parse_predicate(text)
        counts[text] = sum(1 for keyed in kept if predicate.holds(keyed.record.data))
    return counts


def _empty_findings(joined: Joined) -> None:
    if not joined.replay:
        message = "재생 레코드(키 있는 것) 0건 — 빈 집합은 일치가 아니다"
        joined.findings.append(Finding(Severity.ERROR, "replay_empty", "", 0, message))
    if not joined.selected:
        message = "선택된 원본 0건 — 빈 집합은 일치가 아니다"
        joined.findings.append(
            Finding(Severity.ERROR, "selection_empty", "", 0, message)
        )


# --- expectations -----------------------------------------------------------------------


def _actual_for(label: str, joined: Joined) -> int:
    if label.startswith(REPLAY_COUNT_PREFIX):
        counts, name, option = (
            joined.replay_counts,
            label[len(REPLAY_COUNT_PREFIX) :],
            "--count-replay",
        )
    elif label.startswith(COUNT_PREFIX):
        counts, name, option = joined.counts, label[len(COUNT_PREFIX) :], "--count"
    elif label in joined.numbers:
        return joined.numbers[label]
    else:
        known = ", ".join(sorted(joined.numbers))
        raise InputError(
            f"unknown --expect label {label!r} ({known}, count:<pred>, replay_count:<pred>)"
        )
    if name not in counts:
        raise InputError(f"--expect {label}: add {option} {name}")
    return counts[name]


def _check_expectations(items: list[str], joined: Joined) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for item in items:
        label, separator, expected_text = item.rpartition("=")
        if not separator or not label or not expected_text.strip().isdigit():
            raise InputError(f"--expect needs LABEL=COUNT: {item!r}")
        expected = int(expected_text)
        actual = _actual_for(label, joined)
        is_ok = actual == expected
        results.append(
            {"label": label, "expected": expected, "actual": actual, "ok": is_ok}
        )
        if not is_ok:
            message = f"{label}: 재집계 {actual} ≠ 기대 {expected}"
            joined.findings.append(
                Finding(Severity.ERROR, "expect_mismatch", "", 0, message, label)
            )
    return results


# --- report -------------------------------------------------------------------------------


def _file_rows(loaded_files: list[LoadedFile], role: str) -> list[dict[str, object]]:
    return [
        {"role": role, "path": str(loaded.path), "records": loaded.total_records}
        for loaded in loaded_files
    ]


def _parts_finding(replay_files: list[LoadedFile]) -> list[Finding]:
    if len(replay_files) < 2:
        return []
    parts = ", ".join(
        f"{loaded.path.name} {loaded.total_records}건" for loaded in replay_files
    )
    message = f"재생 파일 {len(replay_files)}개를 합침: {parts}"
    return [Finding(Severity.INFO, "replay_parts", "", 0, message)]


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 재생 대조 재집계 (replay_recount)",
        "",
        "| 역할 | 파일 | 레코드 |",
        "|---|---|---|",
    ]
    for item in report["files"]:
        lines.append(
            f"| {item['role']} | `{Path(str(item['path'])).name}` | {item['records']} |"
        )
    lines += ["", "## 건수", "", "| 항목 | 값 |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in report["numbers"].items()]
    for title, counts in (
        ("판별 건수 (선택된 원본)", report["counts"]),
        ("판별 건수 (재생)", report["replay_counts"]),
    ):
        if counts:
            lines += ["", f"## {title}", "", "| 조건 | 건수 |", "|---|---|"]
            lines += [f"| `{name}` | {value} |" for name, value in counts.items()]
    if report["expectations"]:
        lines += ["", "## 기대값 대조", "", "| 항목 | 기대 | 재집계 | 일치 |"]
        lines += ["|---|---|---|---|"]
        lines += [
            f"| {item['label']} | {item['expected']} | {item['actual']} | {item['ok']} |"
            for item in report["expectations"]
        ]
    for category, items in report["problems"].items():
        lines += ["", f"## {category} ({len(items)}건)", ""]
        lines += [f"- `{item}`" for item in items[:MAX_KEYS_IN_MARKDOWN]]
        if len(items) > MAX_KEYS_IN_MARKDOWN:
            lines.append(
                f"- … 외 {len(items) - MAX_KEYS_IN_MARKDOWN}개(JSON 보고서에 전부)"
            )
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def _join(
    args: argparse.Namespace,
    replay_files: list[LoadedFile],
    source_files: list[LoadedFile],
) -> Joined:
    rules = _source_rules(args)
    replay_specs = [
        parse_key_spec(text) for text in args.replay_key or [DEFAULT_REPLAY_KEY]
    ]
    joined = Joined()
    joined.findings += _parse_error_findings(replay_files + source_files)
    joined.findings += _parts_finding(replay_files)
    _key_replay(replay_files, replay_specs, joined)
    _key_source(source_files, rules, joined)
    _select(rules, joined)
    joined.numbers = {
        "replay_records": sum(loaded.total_records for loaded in replay_files),
        "replayed": len(joined.replay),
        "source_records": sum(loaded.total_records for loaded in source_files),
        "source_filtered": joined.numbers["source_filtered"],
        "source_unique": len(joined.source),
        "selected": len(joined.selected),
        "flagged": len(joined.flagged),
        "others": len(joined.selected) - len(joined.flagged),
    }
    _compare_selection(joined)
    hash_fields = HashFields(
        args.replay_hash, args.replay_stored_hash, args.source_hash
    )
    _compare_hashes(joined, hash_fields)
    _replay_errors(joined, args.replay_error_field)
    _empty_findings(joined)
    joined.counts = _count_predicates(joined.selected.values(), args.count or [])
    joined.replay_counts = _count_predicates(
        joined.replay.values(), args.count_replay or []
    )
    return joined


def run_replay_recount(args: argparse.Namespace) -> ToolOutcome:
    """Join the replay records to the originals and check selection, hashes, counts."""
    replay_paths = [Path(text).expanduser().resolve() for text in args.replay]
    source_paths = [Path(text).expanduser().resolve() for text in args.source]
    require_output_outside(args.out, replay_paths + source_paths)
    replay_files = [load_records(path) for path in replay_paths]
    source_files = [load_records(path) for path in source_paths]
    joined = _join(args, replay_files, source_files)
    expectations = _check_expectations(args.expect or [], joined)
    findings = sort_findings(joined.findings)

    summary = {
        "tool": TOOL_NAME,
        "command": "join",
        **joined.numbers,
        "counts": joined.counts,
        "replay_counts": joined.replay_counts,
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "files": _file_rows(replay_files, "replay")
        + _file_rows(source_files, "source"),
        "replay_key": args.replay_key or [DEFAULT_REPLAY_KEY],
        "source_key": args.source_key,
        "numbers": joined.numbers,
        "counts": joined.counts,
        "replay_counts": joined.replay_counts,
        "expectations": expectations,
        "problems": joined.problems,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(
        args, _markdown(report, findings), report, replay_paths + source_paths
    )
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


# --- command line ----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="replay_recount.py",
        description="재생 jsonl을 저장 원본과 키로 이어 선택·해시·판별 건수를 대조한다(읽기 전용).",
    )
    # "extend": repeating a multi-value option adds to the list (no last-wins).
    parser.add_argument(
        "--replay",
        nargs="+",
        action="extend",
        required=True,
        metavar="FILE",
        help="replay jsonl files; parts are merged",
    )
    parser.add_argument(
        "--source",
        nargs="+",
        action="extend",
        required=True,
        metavar="FILE",
        help="stored original jsonl/json files",
    )
    parser.add_argument(
        "--replay-key",
        action="append",
        metavar="SPEC",
        help=f"key spec of replay records (default {DEFAULT_REPLAY_KEY}); "
        "repeat = fallbacks",
    )
    parser.add_argument(
        "--source-key",
        action="append",
        required=True,
        metavar="SPEC",
        help="key spec of original records; repeat = fallbacks",
    )
    parser.add_argument("--replay-hash", default=DEFAULT_REPLAY_HASH, metavar="FIELD")
    parser.add_argument(
        "--replay-stored-hash",
        metavar="FIELD",
        help="replay field holding its copy of the stored hash",
    )
    parser.add_argument("--source-hash", default=DEFAULT_SOURCE_HASH, metavar="FIELD")
    parser.add_argument(
        "--source-where",
        action="append",
        metavar="PRED",
        help="keep originals where PRED holds (repeat = AND)",
    )
    parser.add_argument(
        "--source-in",
        action="append",
        metavar="FIELD=V1,V2",
        help="keep originals whose FIELD is one of the values",
    )
    parser.add_argument(
        "--source-duplicates",
        choices=[str(item) for item in DuplicatePolicy],
        default=str(DuplicatePolicy.ERROR),
        help="repeated original key: error (default), last, first",
    )
    parser.add_argument(
        "--select-flagged",
        metavar="PRED",
        help="select every original where PRED holds",
    )
    parser.add_argument(
        "--select-others",
        type=int,
        metavar="N",
        help="also select the first N originals without the flag",
    )
    parser.add_argument(
        "--count",
        action="append",
        metavar="PRED",
        help="count selected originals where PRED holds (repeatable)",
    )
    parser.add_argument(
        "--count-replay",
        action="append",
        metavar="PRED",
        help="count replay records where PRED holds (repeatable)",
    )
    parser.add_argument(
        "--replay-error-field",
        default=DEFAULT_REPLAY_ERROR_FIELD,
        metavar="FIELD",
        help="truthy value = failed replay run",
    )
    parser.add_argument(
        "--expect",
        action="append",
        metavar="LABEL=COUNT",
        help="labels: replay_records, replayed, source_records, "
        "source_filtered, source_unique, selected, flagged, others, "
        "matched, hash_same, count:<pred>, replay_count:<pred>",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="accepted for the shared contract; this tool never starts git",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_replay_recount(args))


if __name__ == "__main__":
    sys.exit(main())
