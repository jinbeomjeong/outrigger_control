"""Unfilled placeholders such as ``{BATCH_V7}`` in manifests and run records (I axis).

A run-start record or manifest written with ``{NAME}`` slots "to fill after the
start" breaks the judging path when a slot stays (K-2, 2026-11-10: the manifest
kept ``{BATCH_V7}`` and ``record-v7`` stopped on ``file not found``). This tool
lists every placeholder token in the given json / md (or any text) files.

The default token is ``{`` + an upper-case letter + upper-case letters, digits
or ``_`` + ``}``. The pattern ``\\{[A-Z_]+\\}`` misses ``{BATCH_V7}`` (digit), so
digits are allowed. Names given with ``--allow`` are template slots meant to
stay (``{MASK}`` in a command template); they are reported as info. For a
``.json`` file that parses, each finding also names the JSON path of the string.

``--pattern-set angle`` (or ``both``) also finds ``<name>`` slots such as
``<prelaunch>`` or ``<judge_sha256 of P-1a>`` (2026-11-21: the 436.9 J-P3
prelaunch audit searched for them by hand). The token starts with a letter or
``_`` (Hangul included, so ``<프로젝트>`` is found) and holds no ``<``, ``>``,
``"`` or line end. HTML that markdown uses for layout (``<br>``, ``<sup>``,
``<img src=a.png>``; quoted attributes never match) outside code fences and
inline code, and autolinks
(``<https://…>``, ``<a@b.c>``) anywhere, are skipped and only counted; inside
code fences and backticks every token is reported, because commands live there.

Usage:
    python placeholder_scan.py FILE_OR_GLOB [...] [--repo DIR] [--allow NAME ...]
                               [--pattern-set brace|angle|both | --pattern REGEX]
                               [--out REPORT] [--format md|json]
                               [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

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
from _slots import allowed_slot_names, is_angle_token, slot_name

TOOL_NAME = "placeholder_scan"
BRACE_PATTERN = r"\{[A-Z][A-Z0-9_]*\}"
DEFAULT_PATTERN = BRACE_PATTERN
MAX_ANGLE_INNER_CHARS = 120
ANGLE_PATTERN = rf'<[^\W\d][^<>"\n]{{0,{MAX_ANGLE_INNER_CHARS}}}>'
"""``<`` + a letter or ``_`` (any script) + up to 120 characters without ``<>"``.

The quote is left out so that one-line JSON (``"a<b", "c>d"``) does not join
two strings into one token."""
PATTERN_SETS = {
    "brace": BRACE_PATTERN,
    "angle": ANGLE_PATTERN,
    "both": f"{BRACE_PATTERN}|{ANGLE_PATTERN}",
}
DEFAULT_PATTERN_SET = "brace"
CUSTOM_PATTERN_SET = "custom"
MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
# Layout HTML seen in markdown. Names that also read as placeholders (head,
# time, data, path, input, output, source, title, label) are left out on purpose.
MARKDOWN_HTML_TAGS = frozenset(
    {
        "a", "abbr", "b", "blockquote", "br", "caption", "center", "code",
        "col", "colgroup", "dd", "del", "details", "div", "dl", "dt", "em",
        "figcaption", "figure", "font", "hr", "i", "img", "ins", "kbd", "li",
        "mark", "nobr", "ol", "p", "picture", "pre", "s", "small", "span",
        "strong", "sub", "summary", "sup", "table", "tbody", "td", "th",
        "thead", "tr", "u", "ul", "video", "wbr",
    }
)  # fmt: skip
HTML_TAG_SHAPE = re.compile(r"^<(?P<name>[A-Za-z][A-Za-z0-9]*)(?:\s[^<>]*)?/?>$")
AUTOLINK_SHAPE = re.compile(
    r"^<(?:https?|ftp|file|mailto):[^\s<>]*>$|^<[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+>$",
    re.IGNORECASE,
)
CODE_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(?P<ticks>`+).+?(?P=ticks)")


class SkipReason:
    """Why an angle token is not a placeholder (report values)."""

    HTML_TAG = "html_tag"
    AUTOLINK = "autolink"


@dataclass(frozen=True)
class ScanPattern:
    """The compiled token regex and whether the angle filters apply."""

    regex: re.Pattern[str]
    text: str
    set_name: str

    @property
    def filters_angle(self) -> bool:
        return self.set_name in ("angle", "both")


def _compile(pattern_text: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern_text)
    except re.error as error:
        raise InputError(
            f"--pattern is not a valid regular expression: {error}"
        ) from error


def _scan_pattern(args: argparse.Namespace) -> ScanPattern:
    """``--pattern`` (custom) or ``--pattern-set`` (default brace), never both.

    Raises:
        InputError: If both are given or the regex does not compile.
    """
    if args.pattern is not None and args.pattern_set is not None:
        raise InputError("give --pattern or --pattern-set, not both")
    if args.pattern is not None:
        return ScanPattern(_compile(args.pattern), args.pattern, CUSTOM_PATTERN_SET)
    set_name = args.pattern_set or DEFAULT_PATTERN_SET
    text = PATTERN_SETS[set_name]
    return ScanPattern(_compile(text), text, set_name)


def json_string_paths(value: object, path: str = "$") -> Iterator[tuple[str, str]]:
    """``(JSON path, string)`` of every string value and key in a parsed document."""
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            yield f"{path} (key)", str(key)
            yield from json_string_paths(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from json_string_paths(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _json_paths_by_token(
    path: Path, text: str, pattern: re.Pattern[str]
) -> dict[str, list[str]]:
    """Token -> JSON paths of the strings holding it ({} when the file is not JSON)."""
    if path.suffix.lower() != ".json":
        return {}
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return {}
    paths: dict[str, list[str]] = {}
    for json_path, string in json_string_paths(document):
        for token in pattern.findall(string):
            paths.setdefault(token, []).append(json_path)
    return paths


def _code_line_flags(lines: list[str]) -> list[bool]:
    """Per line: True inside a fenced code block (the fence lines included)."""
    flags: list[bool] = []
    open_fence = ""
    for line in lines:
        match = CODE_FENCE.match(line)
        if open_fence:
            flags.append(True)
            closes = match and match["fence"][0] == open_fence[0]
            if closes and len(match["fence"]) >= len(open_fence):
                open_fence = ""
        elif match:
            flags.append(True)
            open_fence = match["fence"]
        else:
            flags.append(False)
    return flags


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in INLINE_CODE.finditer(line)]


def _skip_reason(token: str, is_markdown_prose: bool) -> str | None:
    """Why an angle token is skipped, or None when it is a placeholder."""
    if AUTOLINK_SHAPE.match(token):
        return SkipReason.AUTOLINK
    if not is_markdown_prose:
        return None
    shape = HTML_TAG_SHAPE.match(token)
    if shape and shape["name"].lower() in MARKDOWN_HTML_TAGS:
        return SkipReason.HTML_TAG
    return None


@dataclass(frozen=True)
class LineContext:
    """Where a line sits: markdown prose filters apply only outside code."""

    is_markdown: bool
    in_fence: bool
    inline_spans: tuple[tuple[int, int], ...]

    def is_prose_at(self, column: int) -> bool:
        if not self.is_markdown or self.in_fence:
            return False
        return not any(start <= column < end for start, end in self.inline_spans)


def _line_contexts(path: Path, lines: list[str]) -> list[LineContext]:
    is_markdown = path.suffix.lower() in MARKDOWN_SUFFIXES
    fences = _code_line_flags(lines) if is_markdown else [False] * len(lines)
    return [
        LineContext(
            is_markdown,
            in_fence,
            tuple(_inline_code_spans(line)) if is_markdown else (),
        )
        for line, in_fence in zip(lines, fences, strict=True)
    ]


def _finding_for(
    path: Path, number: int, token: str, is_allowed: bool, where: list[str]
) -> Finding:
    category = "placeholder_allowed" if is_allowed else "placeholder_unfilled"
    severity = Severity.INFO if is_allowed else Severity.ERROR
    path_note = (
        f" (JSON {', '.join(where[:3])}{' ...' if len(where) > 3 else ''})"
        if where
        else ""
    )
    return Finding(severity, category, str(path), number, f"{token}{path_note}", token)


@dataclass
class FileScan:
    """Findings, match records and skipped angle tokens of one file."""

    findings: list[Finding]
    matches: list[dict]
    skipped: list[dict]


def scan_file(path: Path, pattern: ScanPattern, allowed: set[str]) -> FileScan:
    """Findings and match records (line, column, token, JSON paths) of one file."""
    text = read_text_facts(path).text
    json_paths = _json_paths_by_token(path, text, pattern.regex)
    lines = text.splitlines()
    contexts = _line_contexts(path, lines)
    scan = FileScan([], [], [])
    for number, (line, context) in enumerate(zip(lines, contexts, strict=True), 1):
        for match in pattern.regex.finditer(line):
            token = match.group(0)
            location = {"file": str(path), "line": number, "column": match.start() + 1}
            reason = None
            if pattern.filters_angle and is_angle_token(token):
                reason = _skip_reason(token, context.is_prose_at(match.start()))
            if reason is not None:
                scan.skipped.append({**location, "token": token, "reason": reason})
                continue
            is_allowed = slot_name(token) in allowed
            where = json_paths.get(token, [])
            scan.matches.append(
                {**location, "token": token, "allowed": is_allowed, "json_paths": where}
            )
            scan.findings.append(_finding_for(path, number, token, is_allowed, where))
    return scan


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    tokens = (
        ", ".join(f"`{token}` {count}" for token, count in summary["tokens"].items())
        or "없음"
    )
    skipped = Counter(item["reason"] for item in report["skipped"])
    skipped_text = ", ".join(f"{reason} {count}" for reason, count in skipped.items())
    return [
        "# placeholder_scan — 채워지지 않은 자리표시",
        "",
        f"- 파일 {summary['files']}개, 자리표시 {summary['unfilled']}개"
        f"(허용 {summary['allowed']}개) · {severity_summary_text(findings)}",
        (
            f"- 패턴 묶음 `{report['pattern_set']}`, 패턴 `{report['pattern']}`, "
            f"토큰: {tokens}"
        ),
        f"- 자리표시로 보지 않고 건너뜀 {summary['skipped']}개"
        + (f" ({skipped_text})" if skipped_text else ""),
        "",
        "## 발견 사항",
        "",
        *findings_markdown(findings),
    ]


def run_placeholder_scan(args: argparse.Namespace) -> ToolOutcome:
    """Scan the files and build the report."""
    pattern = _scan_pattern(args)
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    files = expand_file_patterns(args.inputs, base)
    require_output_outside(args.out, files)
    allowed = allowed_slot_names(args.allow)
    total = FileScan([], [], [])
    for path in files:
        scan = scan_file(path, pattern, allowed)
        total.findings += scan.findings
        total.matches += scan.matches
        total.skipped += scan.skipped
    findings = sort_findings(total.findings)
    matches = total.matches
    summary = {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": len(files),
        "unfilled": sum(1 for match in matches if not match["allowed"]),
        "allowed": sum(1 for match in matches if match["allowed"]),
        "tokens": dict(sorted(Counter(match["token"] for match in matches).items())),
        "skipped": len(total.skipped),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "pattern": pattern.text,
        "pattern_set": pattern.set_name,
        "allow": sorted(allowed),
        "files": [str(path) for path in files],
        "matches": matches,
        "skipped": total.skipped,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(report, findings), report, files)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="placeholder_scan.py",
        description="manifest·실행 전 기록의 채워지지 않은 {NAME}·<name> 자리표시를 찾는다(읽기 전용).",
    )
    parser.add_argument(
        "inputs", nargs="+", help="files or glob patterns (relative to --repo)"
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="base folder of relative paths and globs (default .)",
    )
    parser.add_argument(
        "--allow",
        nargs="+",
        action="extend",
        default=[],
        help="template slot names that may stay (MASK, {MASK} or <MASK>); "
        "reported as info",
    )
    parser.add_argument(
        "--pattern-set",
        choices=sorted(PATTERN_SETS),
        help="built-in tokens: brace {NAME} (default), angle <name>, or both",
    )
    parser.add_argument(
        "--pattern",
        help=f"custom token regex instead of a pattern set (brace = {BRACE_PATTERN})",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_placeholder_scan(args))


if __name__ == "__main__":
    sys.exit(main())
