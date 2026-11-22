"""Missing-input scan: names of judgement rows that could not be judged (E axis).

A judgement tool marks a row it cannot judge - the run output's row or key was
not found, or a quantity was not computable - with a list key
(``missing_inputs``), a reason string (``runner judge rows of <case>``,
``not computable``) or a counter (``runner_rows_found == 0``). Rule addenda
such as 436.8 rev23 R23-3 ask the auditor to list those rows *before* the
grades are read. This tool walks the judgement output JSON files and reports
only **where** such a marker sits and **which row** (case) it belongs to:

* the JSON path of the marker (keys and list indices, no values),
* the name of the nearest enclosing record that has a name key
  (``case``, ``name``, ``row``, ``id``, ``label``, ``key`` by default); a
  marker outside any named record is reported by its container's path,
* the rule that fired.

Grades, numbers and other values are never printed. ``--show-text`` adds the
matched strings themselves (reasons may quote values; the default leaves them
out).

Rules (repeatable, combine freely; at least one is required):

* ``--key NAME``: a key ``NAME`` whose value is non-empty (list, dict, string),
  true or a non-zero number.
* ``--text REGEX``: any string value (or string list element) matching REGEX.
* ``--text-in KEY[,KEY...]=REGEX``: the same, only for strings under those
  keys (a list's strings count as under the list's key).
* ``--where "KEY OP VALUE"``: a key compared with a number, ``null``, ``true``,
  ``false`` or a string; OP is ``== != < <= > >=``.
* ``--preset NAME``: a named rule set (see ``PRESETS``).

Exit codes: 0 no marked row, 1 at least one marked row, 2 input error (no
rule, bad regex or condition, no JSON file, unparsable JSON), 3 bug.

Usage:
    python missing_scan.py FOLDER_FILE_OR_GLOB [...] [--repo DIR] [--recursive]
                           [--key NAME ...] [--text REGEX ...]
                           [--text-in KEY[,KEY]=REGEX ...]
                           [--where "KEY OP VALUE" ...]
                           [--preset v5-resume-4368] [--name-key KEY ...]
                           [--show-text] [--out REPORT] [--format md|json]
                           [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import json
import operator
import re
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import expand_file_patterns, read_text_facts, require_output_outside
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

TOOL_NAME = "missing_scan"
DEFAULT_NAME_KEYS = ("case", "name", "row", "id", "label", "key")
MAX_TEXT_CHARS = 200
MAX_PATHS_IN_MESSAGE = 3
WHERE_PATTERN = re.compile(
    r"^\s*(?P<key>[^\s=!<>]+)\s*(?P<op>==|!=|<=|>=|<|>)\s*(?P<value>.+?)\s*$"
)
COMPARISONS: dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
ORDERING_OPERATORS = frozenset({"<", "<=", ">", ">="})
LITERAL_WORDS: dict[str, object] = {"null": None, "true": True, "false": False}

# 436.8 rev23 R23-3 (both paths): the rows an auditor lists before grading.
# Path 1 markers: missing_inputs, "runner judge rows of", "not computable"
# stops, R23-1 name-check stops, runner_rows_found == 0 / runner_file null,
# "chrono_t45_replay row missing". Path 2 markers: missing_inputs,
# not_computable, absent_inputs and reasons with missing / absent / not found /
# "no " (the path 2 tool's own missing-reason words). Stop phrases are searched
# only in reason-like keys: rule descriptions also say "not computable".
STOP_TEXT_KEYS = "reason,stops,why,note"
PRESETS: dict[str, dict[str, tuple[str, ...]]] = {
    "v5-resume-4368": {
        "key": ("missing_inputs", "not_computable", "absent_inputs"),
        "text": ("runner judge rows of", "row missing"),
        "text_in": (
            f"{STOP_TEXT_KEYS}=not computable",
            f"{STOP_TEXT_KEYS}=rev23 R23-1",
            r"reason=(?i)\bmissing\b|\babsent\b|\bnot found\b|\bno\s",
        ),
        "where": ("runner_rows_found == 0", "runner_file == null"),
    },
}


class RuleKind(StrEnum):
    """What a scan rule looks at."""

    KEY = "key"
    TEXT = "text"
    WHERE = "where"


@dataclass(frozen=True)
class ScanRule:
    """One marker of a row that could not be judged."""

    kind: RuleKind
    label: str  # shown in the report, e.g. "key:missing_inputs"
    keys: frozenset[str] | None = None  # None: any key (text rules only)
    pattern: re.Pattern[str] | None = None
    comparison: str = ""
    expected: object = None


@dataclass(frozen=True)
class _Owner:
    """The nearest enclosing record that carries a name (or the document root)."""

    path: str
    name: str | None


@dataclass
class MarkedRow:
    """A record holding at least one marker; reported once per file and path."""

    file: Path
    path: str
    name: str | None
    rules: list[str] = field(default_factory=list)
    hits: list[dict[str, str]] = field(default_factory=list)


# --- rule parsing ----------------------------------------------------------------------


def _compile(pattern_text: str, option: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern_text)
    except re.error as error:
        raise InputError(
            f"{option} {pattern_text!r} is not a valid regex: {error}"
        ) from error


def _key_rule(name: str) -> ScanRule:
    if not name.strip():
        raise InputError("--key needs a key name")
    return ScanRule(RuleKind.KEY, f"key:{name}", keys=frozenset({name}))


def _text_rule(pattern_text: str) -> ScanRule:
    return ScanRule(
        RuleKind.TEXT, f"text:{pattern_text}", pattern=_compile(pattern_text, "--text")
    )


def _text_in_rule(spec: str) -> ScanRule:
    """``KEY[,KEY...]=REGEX``: the regex is searched under those keys only."""
    key_list, separator, pattern_text = spec.partition("=")
    keys = frozenset(key.strip() for key in key_list.split(",") if key.strip())
    if not separator or not keys or not pattern_text:
        raise InputError(f"--text-in needs KEY[,KEY...]=REGEX, got {spec!r}")
    return ScanRule(
        RuleKind.TEXT,
        f"text-in:{key_list.strip()}={pattern_text}",
        keys=keys,
        pattern=_compile(pattern_text, "--text-in"),
    )


def _literal(text: str) -> object:
    """``null``/``true``/``false``, a number, or a (quotes stripped) string."""
    lowered = text.lower()
    if lowered in LITERAL_WORDS:
        return LITERAL_WORDS[lowered]
    try:
        return float(text)
    except ValueError:
        return text.strip("'\"")


def _where_rule(spec: str) -> ScanRule:
    match = WHERE_PATTERN.match(spec)
    if match is None:
        raise InputError(
            f'--where needs "KEY OP VALUE" (OP: == != < <= > >=), got {spec!r}'
        )
    comparison, expected = match.group("op"), _literal(match.group("value"))
    if comparison in ORDERING_OPERATORS and not isinstance(expected, float):
        raise InputError(f"--where {spec!r}: {comparison} needs a number")
    return ScanRule(
        RuleKind.WHERE,
        f"where:{match.group('key')} {comparison} {match.group('value')}",
        keys=frozenset({match.group("key")}),
        comparison=comparison,
        expected=expected,
    )


def build_rules(args: argparse.Namespace) -> list[ScanRule]:
    """Rules from the preset(s) and the explicit options, duplicates dropped.

    Raises:
        InputError: If no rule is given or one is malformed.
    """
    keys: list[str] = []
    texts: list[str] = []
    texts_in: list[str] = []
    wheres: list[str] = []
    for preset_name in args.preset:
        preset = PRESETS[preset_name]
        keys += preset["key"]
        texts += preset["text"]
        texts_in += preset["text_in"]
        wheres += preset["where"]
    rules = [_key_rule(name) for name in [*keys, *args.key]]
    rules += [_text_rule(text) for text in [*texts, *args.text]]
    rules += [_text_in_rule(spec) for spec in [*texts_in, *args.text_in]]
    rules += [_where_rule(spec) for spec in [*wheres, *args.where]]
    if not rules:
        raise InputError(
            "give at least one rule: --key, --text, --text-in, --where or --preset"
        )
    distinct: dict[str, ScanRule] = {}
    for rule in rules:
        distinct.setdefault(rule.label, rule)
    return list(distinct.values())


# --- matching ---------------------------------------------------------------------------


def _is_non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list, dict)):
        return len(value) > 0
    return bool(value)  # bool or number


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _compares(rule: ScanRule, actual: object) -> bool:
    """Type-strict comparison: ``0`` never equals ``false`` or ``null``."""
    expected = rule.expected
    if isinstance(expected, float):
        if not _is_number(actual):
            return False
    elif expected is None or isinstance(expected, bool):
        if rule.comparison == "==":
            return actual is expected
        return actual is not expected
    elif not isinstance(actual, str):
        return rule.comparison == "!="
    return COMPARISONS[rule.comparison](actual, expected)


def _entry_matches(rule: ScanRule, key: str, value: object) -> bool:
    """Key and where rules look at one ``key: value`` entry of a JSON object."""
    if rule.keys is None or key not in rule.keys:
        return False
    if rule.kind is RuleKind.KEY:
        return _is_non_empty(value)
    if rule.kind is RuleKind.WHERE:
        return _compares(rule, value)
    return False


def _text_matches(rule: ScanRule, key: str | None, text: str) -> bool:
    if rule.kind is not RuleKind.TEXT or rule.pattern is None:
        return False
    if rule.keys is not None and key not in rule.keys:
        return False
    return bool(rule.pattern.search(text))


def _shown_text(value: object) -> str:
    """The matched value for ``--show-text``: strings as they are, else the type."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        text = " | ".join(value)
    else:
        text = f"<{type(value).__name__}>"
    return text if len(text) <= MAX_TEXT_CHARS else text[: MAX_TEXT_CHARS - 3] + "..."


# --- walking ------------------------------------------------------------------------------


@dataclass
class _Walker:
    """Walks one JSON document and collects the marked rows."""

    file: Path
    rules: list[ScanRule]
    name_keys: tuple[str, ...]
    rows: dict[str, MarkedRow] = field(default_factory=dict)

    def _owner_of(self, record: dict, path: str, outer: _Owner) -> _Owner:
        for name_key in self.name_keys:
            name = record.get(name_key)
            if isinstance(name, str) and name:
                return _Owner(path, name)
        return outer

    def _mark(
        self, owner: _Owner, container: str, path: str, rule: ScanRule, value: object
    ) -> None:
        # Without a named record the marker's own container is the row, so two
        # unnamed markers in different places do not merge into "$".
        row_path = owner.path if owner.name is not None else container
        row = self.rows.setdefault(row_path, MarkedRow(self.file, row_path, owner.name))
        if rule.label not in row.rules:
            row.rules.append(rule.label)
        row.hits.append({"path": path, "rule": rule.label, "text": _shown_text(value)})

    def walk(
        self, value: object, path: str, key: str | None, owner: _Owner, container: str
    ) -> None:
        """Visit ``value`` at ``path``; ``key`` is its key (lists pass theirs on)."""
        if isinstance(value, dict):
            owner = self._owner_of(value, path, owner)
            for child_key, child in value.items():
                child_path = f"{path}.{child_key}"
                for rule in self.rules:
                    if _entry_matches(rule, str(child_key), child):
                        self._mark(owner, path, child_path, rule, child)
                self.walk(child, child_path, str(child_key), owner, path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.walk(child, f"{path}[{index}]", key, owner, path)
        elif isinstance(value, str):
            for rule in self.rules:
                if _text_matches(rule, key, value):
                    self._mark(owner, container, path, rule, value)


def scan_document(
    path: Path, rules: list[ScanRule], name_keys: tuple[str, ...]
) -> list[MarkedRow]:
    """Marked rows of one JSON file, in document order.

    Raises:
        InputError: If the file is not valid JSON (the scan would be incomplete).
    """
    try:
        document = json.loads(read_text_facts(path).text)
    except json.JSONDecodeError as error:
        raise InputError(f"not valid JSON: {path} ({error})") from error
    walker = _Walker(path, rules, name_keys)
    walker.walk(document, "$", None, _Owner("$", None), "$")
    return list(walker.rows.values())


# --- inputs ---------------------------------------------------------------------------------


def collect_json_files(
    inputs: list[str], base: Path, recursive: bool
) -> tuple[list[Path], list[Path]]:
    """``(json files, folders given)``; a folder contributes its ``*.json`` files.

    Raises:
        InputError: If a path is missing, a pattern matches nothing or a folder
            holds no JSON file.
    """
    files: list[Path] = []
    folders: list[Path] = []
    for text in inputs:
        candidate = (base / Path(text).expanduser()).resolve()
        if candidate.is_dir():
            folders.append(candidate)
            found = sorted(candidate.glob("**/*.json" if recursive else "*.json"))
            if not found:
                raise InputError(f"no .json file in folder: {candidate}")
            files += [path for path in found if path.is_file()]
        else:
            files += expand_file_patterns([text], base)
    distinct: list[Path] = []
    for path in files:
        if path not in distinct:
            distinct.append(path)
    return distinct, folders


# --- report -------------------------------------------------------------------------------


def _finding(row: MarkedRow) -> Finding:
    paths = [hit["path"] for hit in row.hits]
    shown = ", ".join(paths[:MAX_PATHS_IN_MESSAGE])
    more = (
        f" 외 {len(paths) - MAX_PATHS_IN_MESSAGE}곳"
        if len(paths) > MAX_PATHS_IN_MESSAGE
        else ""
    )
    name = row.name or "(이름 키 없음)"
    message = f"{name} — {'; '.join(row.rules)} @ {shown}{more}"
    return Finding(Severity.ERROR, "missing_row", str(row.file), 0, message, name)


def _row_dict(row: MarkedRow, show_text: bool) -> dict[str, object]:
    hits = [
        hit if show_text else {"path": hit["path"], "rule": hit["rule"]}
        for hit in row.hits
    ]
    return {
        "file": str(row.file),
        "path": row.path,
        "name": row.name,
        "rules": row.rules,
        "hits": hits,
    }


def _names_by_file(rows: list[MarkedRow]) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for row in rows:
        listed = names.setdefault(str(row.file), [])
        name = row.name or row.path
        if name not in listed:
            listed.append(name)
    return names


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


@dataclass(frozen=True)
class _ScanCounts:
    """Numbers shown at the top of the Markdown report."""

    files: int
    rows: int
    names: int


def _markdown_header(
    counts: _ScanCounts,
    rule_labels: list[str],
    findings: list[Finding],
    show_text: bool,
) -> list[str]:
    count_line = (
        f"- 파일 {counts.files}개, 표시된 행 {counts.rows}개"
        f"(이름 {counts.names}개) · {severity_summary_text(findings)}"
    )
    text_note = " — `--show-text`로 문자열을 함께 싣는다" if show_text else ""
    return [
        "# missing_scan — 판정 불가·결측 행 이름",
        "",
        count_line,
        f"- 규칙: {', '.join(f'`{label}`' for label in rule_labels)}",
        f"- 값(등급·수치)은 싣지 않는다{text_note}",
        "",
        "## 표시된 행",
        "",
    ]


def _markdown(
    counts: _ScanCounts,
    rule_labels: list[str],
    rows: list[MarkedRow],
    findings: list[Finding],
    show_text: bool,
) -> list[str]:
    lines = _markdown_header(counts, rule_labels, findings, show_text)
    if not rows:
        return [
            *lines,
            "표시된 행 없음.",
            "",
            "## 발견 사항",
            "",
            *findings_markdown(findings),
        ]
    header = "| 파일 | 행 이름 | 행 경로 | 규칙 | 표시 위치 |"
    lines += [
        header + (" 문자열 |" if show_text else ""),
        "|---|---|---|---|---|" + ("---|" if show_text else ""),
    ]
    for row in rows:
        cells = [
            row.file.name,
            row.name or "-",
            row.path,
            "; ".join(row.rules),
            ", ".join(hit["path"] for hit in row.hits),
        ]
        if show_text:
            cells.append(" / ".join(hit["text"] for hit in row.hits))
        lines.append("| " + " | ".join(_escape(cell) for cell in cells) + " |")
    return [*lines, "", "## 발견 사항", "", *findings_markdown(findings)]


def run_missing_scan(args: argparse.Namespace) -> ToolOutcome:
    """Scan the judgement outputs and build the report."""
    rules = build_rules(args)
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    files, folders = collect_json_files(args.inputs, base, args.recursive)
    require_output_outside(args.out, files, folders)
    name_keys = tuple(args.name_key) if args.name_key else DEFAULT_NAME_KEYS

    rows: list[MarkedRow] = []
    for path in files:
        rows += scan_document(path, rules, name_keys)
    findings = sort_findings(_finding(row) for row in rows)
    rule_counts = Counter(label for row in rows for label in row.rules)
    rule_labels = [rule.label for rule in rules]
    names = _names_by_file(rows)
    counts = _ScanCounts(
        len(files), len(rows), sum(len(listed) for listed in names.values())
    )
    summary = {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": counts.files,
        "rows": counts.rows,
        "names": counts.names,
        "by_rule": {label: rule_counts.get(label, 0) for label in rule_labels},
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "preset": args.preset,
        "rules": rule_labels,
        "name_keys": list(name_keys),
        "files": [str(path) for path in files],
        "names_by_file": names,
        "rows": [_row_dict(row, args.show_text) for row in rows],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    markdown = _markdown(counts, rule_labels, rows, findings, args.show_text)
    lines = deliver_report(args, markdown, report, files)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="missing_scan.py",
        description="판정 출력 JSON에서 판정 불가·계산 불가 행의 이름만 뽑는다(읽기 전용).",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="judgement output folders (their *.json), JSON files or globs (relative to --repo)",
    )
    parser.add_argument(
        "--repo", default=".", help="base folder of relative paths (default .)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="folders: also read *.json in subfolders",
    )
    parser.add_argument(
        "--key",
        nargs="+",
        action="extend",
        default=[],
        metavar="NAME",
        help="key whose value is non-empty, true or non-zero (repeatable)",
    )
    parser.add_argument(
        "--text",
        nargs="+",
        action="extend",
        default=[],
        metavar="REGEX",
        help="regex searched in every string value (repeatable)",
    )
    parser.add_argument(
        "--text-in",
        nargs="+",
        action="extend",
        default=[],
        metavar="KEY[,KEY]=REGEX",
        help="regex searched in the strings under these keys only (repeatable)",
    )
    parser.add_argument(
        "--where",
        nargs="+",
        action="extend",
        default=[],
        metavar='"KEY OP VALUE"',
        help="condition on a key: OP is == != < <= > >=, VALUE a number, null, true, "
        "false or a string (repeatable)",
    )
    parser.add_argument(
        "--preset",
        nargs="+",
        action="extend",
        default=[],
        choices=sorted(PRESETS),
        help="named rule set added to the explicit rules",
    )
    parser.add_argument(
        "--name-key",
        nargs="+",
        action="extend",
        default=[],
        metavar="KEY",
        help=f"keys that name a record (default: {' '.join(DEFAULT_NAME_KEYS)})",
    )
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="also report the matched strings (they may quote values)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_missing_scan(args))


if __name__ == "__main__":
    sys.exit(main())
