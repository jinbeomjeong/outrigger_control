"""Handoff leak check: do the handoff texts name what the other side must not see?

Two-path judgements hand each path a text of its own (436.8 R4: one handoff
for path 1, two for path 2). A path-2 handoff must not name path 1's files,
stems, constants, subcommands, folders or branches (rev2 R2-0, 원판 9.2).
This tool scans the handoff files line by line for the names of a dictionary
JSON and, optionally, checks that marked blocks meant to be byte-identical in
every handoff ("<!-- R4 공통 블록 시작 -->" ... "끝 -->") really are.

Dictionary JSON: an object whose list values are name categories (``files``,
``stems``, ``constants``, ``subcommands``, ``folders``, ``outputs``,
``branches`` ...); other values (``"source": "..."``) are ignored. A plain
list is one category ``names``. Names shorter than ``--min-length`` (default
4) are skipped and counted. A name matches only at a word boundary: not next
to ``[A-Za-z0-9_-]`` (``--boundary substring`` turns that off). Overlapping
hits keep the longest name.

Blocks (``--blocks`` or ``--expect-block``): a block is the bytes strictly
between a start marker line and an end marker line of one label. Every file
must hold each label at most once with one start before one end. Blocks of
the same label are compared by the SHA-256 of their raw bytes; the LF
normalised hash is reported too, so a line-ending-only difference is named.

Usage:
    python handoff_leak.py FILE_OR_GLOB [...] --names DICT.json [--names ...]
        [--extra-name NAME ...] [--allow NAME ...] [--min-length 4]
        [--boundary word|substring] [--ignore-case] [--scope all|blocks]
        [--blocks] [--block-pattern REGEX] [--expect-block LABEL=SHA256 ...]
        [--repo DIR] [--out REPORT] [--format md|json] [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import decode_bytes, expand_file_patterns, require_output_outside
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

TOOL_NAME = "handoff_leak"
DEFAULT_MIN_LENGTH = 4
WORD_CHARACTERS = r"A-Za-z0-9_\-"
DEFAULT_BLOCK_PATTERN = (
    r"^\s*<!--\s*(?P<label>.+?)\s+(?P<edge>시작|끝|start|end|begin)\s*-->\s*$"
)
START_EDGES = frozenset({"시작", "start", "begin"})
MIN_EXPECT_PREFIX = 8
MAX_EXCERPT_CHARS = 160
MAX_SHORT_EXAMPLES = 10


@dataclass(frozen=True)
class Name:
    """One dictionary entry; ``category`` is the dictionary key it came from."""

    text: str
    category: str
    source: str


@dataclass(frozen=True)
class Hit:
    name: Name
    column: int  # 1-based


@dataclass(frozen=True)
class Block:
    """The bytes between one label's start and end marker lines in one file."""

    file: Path
    label: str
    start_line: int  # line of the start marker
    end_line: int  # line of the end marker
    sha256_raw: str
    sha256_lf: str
    size_bytes: int


@dataclass(frozen=True)
class Leak:
    """One handoff line that names dictionary entries."""

    file: Path
    line: int
    hits: list[Hit]
    excerpt: str


@dataclass
class _FileText:
    path: Path
    raw_lines: list[bytes]
    lines: list[str]
    block_lines: set[int] = field(default_factory=set)  # 1-based lines inside blocks


# --- dictionary --------------------------------------------------------------------


def _names_from_document(document: object, source: str) -> list[Name]:
    if isinstance(document, list):
        return [Name(str(item), "names", source) for item in document]
    if not isinstance(document, dict):
        raise InputError(f"name dictionary must be a JSON object or list: {source}")
    names: list[Name] = []
    for category, values in document.items():
        if isinstance(values, list):
            names += [Name(str(value), str(category), source) for value in values]
    return names


def load_names(
    dictionary_paths: list[Path], extra: list[str], allowed: set[str], min_length: int
) -> tuple[list[Name], list[Name]]:
    """``(names used, names skipped as too short)``; allowed names are dropped.

    Raises:
        InputError: If a dictionary is unreadable or no name is left to check.
    """
    names: list[Name] = []
    for path in dictionary_paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise InputError(f"cannot read name dictionary {path}: {error}") from error
        names += _names_from_document(document, path.name)
    names += [Name(text, "extra", "--extra-name") for text in extra]
    distinct: dict[str, Name] = {}
    for name in names:
        if name.text.strip() and name.text not in allowed:
            distinct.setdefault(name.text, name)
    used = [name for name in distinct.values() if len(name.text) >= min_length]
    short = [name for name in distinct.values() if len(name.text) < min_length]
    if not used:
        raise InputError(
            "no name of the dictionaries is long enough to check (empty selection)"
        )
    used.sort(key=lambda name: (-len(name.text), name.text))
    return used, short


def _name_pattern(name: str, boundary: str, ignore_case: bool) -> re.Pattern[str]:
    body = re.escape(name)
    if boundary == "word":
        body = rf"(?<![{WORD_CHARACTERS}]){body}(?![{WORD_CHARACTERS}])"
    return re.compile(body, re.IGNORECASE if ignore_case else 0)


# --- scanning ----------------------------------------------------------------------


def line_hits(text: str, patterns: list[tuple[Name, re.Pattern[str]]]) -> list[Hit]:
    """Names found in ``text``; a hit inside a longer hit's span is dropped."""
    taken: list[tuple[int, int]] = []
    hits: list[Hit] = []
    for name, pattern in patterns:  # longest names first
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            if any(start <= span[0] and span[1] <= end for start, end in taken):
                continue
            taken.append(span)
            hits.append(Hit(name, match.start() + 1))
    return sorted(hits, key=lambda hit: hit.column)


def _read_file(path: Path) -> _FileText:
    data = path.read_bytes()
    raw_lines = data.splitlines(keepends=True)
    text, _ = decode_bytes(data)
    lines = text.splitlines()
    if len(lines) != len(raw_lines):  # \x0b, \x1c ... split str but not bytes
        lines = [decode_bytes(raw)[0].rstrip("\r\n") for raw in raw_lines]
    return _FileText(path, raw_lines, lines)


def _excerpt(text: str) -> str:
    stripped = text.strip()
    return (
        stripped
        if len(stripped) <= MAX_EXCERPT_CHARS
        else stripped[: MAX_EXCERPT_CHARS - 1] + "…"
    )


def scan_leaks(
    file_text: _FileText,
    patterns: list[tuple[Name, re.Pattern[str]]],
    only_blocks: bool,
) -> list[Leak]:
    """Lines of one file that name dictionary entries."""
    leaks: list[Leak] = []
    for number, text in enumerate(file_text.lines, start=1):
        if only_blocks and number not in file_text.block_lines:
            continue
        hits = line_hits(text, patterns)
        if hits:
            leaks.append(Leak(file_text.path, number, hits, _excerpt(text)))
    return leaks


def _leak_finding(leak: Leak) -> Finding:
    listed = ", ".join(f"{hit.name.text} ({hit.name.category})" for hit in leak.hits)
    return Finding(
        Severity.ERROR,
        "name_leak",
        str(leak.file),
        leak.line,
        f"{listed} — {leak.excerpt}",
        ", ".join(hit.name.text for hit in leak.hits),
    )


def _leak_dict(leak: Leak) -> dict[str, object]:
    return {
        "file": str(leak.file),
        "line": leak.line,
        "names": [
            {"name": hit.name.text, "category": hit.name.category, "column": hit.column}
            for hit in leak.hits
        ],
        "text": leak.excerpt,
    }


# --- blocks ------------------------------------------------------------------------


def _compile_block_pattern(text: str) -> re.Pattern[str]:
    try:
        pattern = re.compile(text, re.IGNORECASE)
    except re.error as error:
        raise InputError(
            f"--block-pattern is not a valid regular expression: {error}"
        ) from error
    if not {"label", "edge"} <= set(pattern.groupindex):
        raise InputError(
            "--block-pattern needs the named groups (?P<label>...) and (?P<edge>...)"
        )
    return pattern


def _marker_lines(
    file_text: _FileText, pattern: re.Pattern[str]
) -> dict[str, dict[str, list[int]]]:
    """label -> {"start": [line numbers], "end": [line numbers]}."""
    markers: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"start": [], "end": []}
    )
    for number, text in enumerate(file_text.lines, start=1):
        match = pattern.match(text)
        if match is None:
            continue
        edge = "start" if match.group("edge").lower() in START_EDGES else "end"
        markers[match.group("label").strip()][edge].append(number)
    return markers


def find_blocks(
    file_text: _FileText, pattern: re.Pattern[str]
) -> tuple[list[Block], list[Finding]]:
    """Well-formed blocks of one file and ``block_markers`` findings for the rest."""
    blocks: list[Block] = []
    findings: list[Finding] = []
    for label, edges in _marker_lines(file_text, pattern).items():
        starts, ends = edges["start"], edges["end"]
        if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
            message = (
                f"표지 '{label}': 시작 {starts}, 끝 {ends}"
                "(시작 1개가 끝 1개보다 앞서야 한다)"
            )
            line = (starts or ends)[0]
            findings.append(
                Finding(
                    Severity.ERROR,
                    "block_markers",
                    str(file_text.path),
                    line,
                    message,
                    label,
                )
            )
            continue
        raw = b"".join(file_text.raw_lines[starts[0] : ends[0] - 1])
        file_text.block_lines.update(range(starts[0] + 1, ends[0]))
        blocks.append(
            Block(
                file_text.path,
                label,
                starts[0],
                ends[0],
                hashlib.sha256(raw).hexdigest(),
                hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
                len(raw),
            )
        )
    return blocks, findings


def _parse_expectations(texts: list[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for text in texts:
        label, separator, digest = text.rpartition("=")
        digest = digest.strip().lower()
        if not separator or not label.strip():
            raise InputError(f"--expect-block must be LABEL=SHA256: {text}")
        if not re.fullmatch(rf"[0-9a-f]{{{MIN_EXPECT_PREFIX},64}}", digest):
            raise InputError(
                f"--expect-block hash must be {MIN_EXPECT_PREFIX}~64 hex: {text}"
            )
        expected[label.strip()] = digest
    return expected


def _block_finding(
    severity: Severity, category: str, block: Block, message: str
) -> Finding:
    return Finding(
        severity, category, str(block.file), block.start_line, message, block.label
    )


def _eol_note(block: Block, reference_lf: str) -> str:
    if block.sha256_lf == reference_lf:
        return " (LF 정규화 값은 같음: 줄바꿈만 다름)"
    return ""


def _same_label_findings(group: list[Block], has_expectation: bool) -> list[Finding]:
    """Blocks of one label against the first one (input order)."""
    reference = group[0]
    findings: list[Finding] = []
    for block in group[1:]:
        if block.sha256_raw == reference.sha256_raw:
            continue
        message = (
            f"'{block.label}' 블록 sha256 {block.sha256_raw[:12]} ≠ 기준 "
            f"{reference.file.name}의 {reference.sha256_raw[:12]}"
            f"{_eol_note(block, reference.sha256_lf)}"
        )
        findings.append(
            _block_finding(Severity.ERROR, "block_mismatch", block, message)
        )
    if len(group) == 1 and not has_expectation:
        message = f"'{reference.label}' 블록이 이 파일에만 있어 대조할 짝이 없다"
        findings.append(
            _block_finding(Severity.INFO, "block_single", reference, message)
        )
    elif len(group) > 1 and not findings:
        message = (
            f"'{reference.label}' 블록 {len(group)}개 같음"
            f"(sha256 {reference.sha256_raw})"
        )
        findings.append(_block_finding(Severity.INFO, "block_same", reference, message))
    return findings


def _expectation_findings(group: list[Block], digest: str) -> list[Finding]:
    """Every block of the label must start with the expected hash (raw bytes)."""
    findings: list[Finding] = []
    for block in group:
        if block.sha256_raw.startswith(digest):
            continue
        note = " (LF 정규화 값과는 같음)" if block.sha256_lf.startswith(digest) else ""
        message = (
            f"'{block.label}' 블록 sha256 {block.sha256_raw[:12]} "
            f"≠ 기대 {digest[:12]}{note}"
        )
        findings.append(
            _block_finding(Severity.ERROR, "block_expect_mismatch", block, message)
        )
    return findings


def compare_blocks(blocks: list[Block], expected: dict[str, str]) -> list[Finding]:
    """Same-label blocks must have the same raw bytes; expected hashes must match."""
    by_label: dict[str, list[Block]] = defaultdict(list)
    for block in blocks:
        by_label[block.label].append(block)
    findings: list[Finding] = []
    for label, group in by_label.items():
        findings += _same_label_findings(group, label in expected)
    for label, digest in expected.items():
        if label in by_label:
            findings += _expectation_findings(by_label[label], digest)
            continue
        message = f"'{label}' 블록이 어느 파일에도 없다"
        findings.append(
            Finding(Severity.ERROR, "block_expect_absent", "", 0, message, label)
        )
    return findings


# --- run ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Results:
    files: list[_FileText]
    names: list[Name]
    short: list[Name]
    blocks: list[Block]
    leaks: list[Leak]
    findings: list[Finding]


def _short_names_finding(
    short: list[Name], first_file: Path, min_length: int
) -> Finding:
    examples = ", ".join(name.text for name in short[:MAX_SHORT_EXAMPLES])
    more = " ..." if len(short) > MAX_SHORT_EXAMPLES else ""
    message = (
        f"{min_length}자 미만이라 검사하지 않은 이름 {len(short)}개: {examples}{more}"
    )
    return Finding(Severity.INFO, "names_skipped_short", str(first_file), 0, message)


def _check(args: argparse.Namespace, base: Path) -> _Results:
    files = expand_file_patterns(args.inputs, base)
    dictionaries = expand_file_patterns(args.names, base)
    require_output_outside(args.out, [*files, *dictionaries])
    expected = _parse_expectations(args.expect_block)
    use_blocks = args.blocks or bool(expected) or args.scope == "blocks"
    block_pattern = _compile_block_pattern(args.block_pattern)
    names, short = load_names(
        dictionaries, args.extra_name, set(args.allow), args.min_length
    )
    patterns = [
        (name, _name_pattern(name.text, args.boundary, args.ignore_case))
        for name in names
    ]

    texts = [_read_file(path) for path in files]
    findings: list[Finding] = []
    blocks: list[Block] = []
    if use_blocks:  # first: it marks the block lines that --scope blocks reads
        for file_text in texts:
            file_blocks, marker_findings = find_blocks(file_text, block_pattern)
            blocks += file_blocks
            findings += marker_findings
        findings += compare_blocks(blocks, expected)
    leaks: list[Leak] = []
    for file_text in texts:
        leaks += scan_leaks(file_text, patterns, args.scope == "blocks")
    findings += [_leak_finding(leak) for leak in leaks]
    if short:
        findings.append(_short_names_finding(short, files[0], args.min_length))
    return _Results(texts, names, short, blocks, leaks, sort_findings(findings))


def _block_dict(block: Block) -> dict[str, object]:
    return {
        "file": str(block.file),
        "label": block.label,
        "start_line": block.start_line,
        "end_line": block.end_line,
        "sha256_raw": block.sha256_raw,
        "sha256_lf": block.sha256_lf,
        "bytes": block.size_bytes,
    }


def _markdown(results: _Results) -> list[str]:
    overview = (
        f"- 파일 {len(results.files)}개, 이름 {len(results.names)}개(짧아서 뺀 것 "
        f"{len(results.short)}개), 누설 줄 {len(results.leaks)}개 · "
        f"{severity_summary_text(results.findings)}"
    )
    lines = ["# handoff_leak — 넘김 글머리 누설 검사", "", overview, ""]
    if results.blocks:
        lines += [
            "## 블록",
            "",
            "| 파일 | 표지 | 줄 | 바이트 | sha256(원시) | sha256(LF) |",
            "|---|---|---|---|---|---|",
        ]
        for block in results.blocks:
            lines.append(
                f"| `{block.file}` | {block.label} "
                f"| {block.start_line}~{block.end_line} | {block.size_bytes} "
                f"| `{block.sha256_raw}` | `{block.sha256_lf}` |"
            )
        lines.append("")
    return [*lines, "## 발견 사항", "", *findings_markdown(results.findings)]


def run_handoff_leak(args: argparse.Namespace) -> ToolOutcome:
    """Scan the handoffs, compare the blocks and build the report."""
    if args.min_length < 1:
        raise InputError("--min-length must be at least 1")
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    results = _check(args, base)
    leak_names = sorted({hit.name.text for leak in results.leaks for hit in leak.hits})
    summary: dict[str, object] = {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": len(results.files),
        "names_used": len(results.names),
        "names_skipped_short": len(results.short),
        "leak_lines": len(results.leaks),
        "leak_names": len(leak_names),
        "blocks": len(results.blocks),
        **count_by_severity(results.findings),
        "categories": count_by_category(results.findings),
    }
    report: dict[str, object] = {
        "tool": TOOL_NAME,
        "boundary": args.boundary,
        "ignore_case": args.ignore_case,
        "min_length": args.min_length,
        "scope": args.scope,
        "files": [str(item.path) for item in results.files],
        "leaks": [_leak_dict(leak) for leak in results.leaks],
        "leak_names": leak_names,
        "blocks": [_block_dict(block) for block in results.blocks],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in results.findings],
    }
    inputs = [item.path for item in results.files]
    lines = deliver_report(args, _markdown(results), report, inputs)
    return ToolOutcome(
        exit_code_for(results.findings, Severity(args.fail_on)), lines, summary
    )


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="handoff_leak.py",
        description=(
            "넘김 파일에서 이름 사전(파일·줄기·상수·하위 명령·폴더·브랜치)의 "
            "이름을 찾고, 같은 바이트여야 하는 표지 사이 블록의 sha256을 "
            "대조한다(읽기 전용)."
        ),
    )
    parser.add_argument(
        "inputs", nargs="+", help="handoff files or globs (relative to --repo)"
    )
    parser.add_argument(
        "--names",
        nargs="+",
        action="extend",
        required=True,
        help="name dictionary JSON file(s)",
    )
    parser.add_argument(
        "--extra-name",
        nargs="+",
        action="extend",
        default=[],
        help="more names (category extra)",
    )
    parser.add_argument(
        "--allow",
        nargs="+",
        action="extend",
        default=[],
        help="names that may appear (dropped from the check)",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=DEFAULT_MIN_LENGTH,
        help=f"skip names shorter than this (default {DEFAULT_MIN_LENGTH})",
    )
    parser.add_argument(
        "--boundary",
        choices=("word", "substring"),
        default="word",
        help="word (default): not next to [A-Za-z0-9_-]; substring: anywhere",
    )
    parser.add_argument(
        "--ignore-case", action="store_true", help="case-insensitive name match"
    )
    parser.add_argument(
        "--scope",
        choices=("all", "blocks"),
        default="all",
        help="all (default): every line; blocks: only lines inside marked blocks",
    )
    parser.add_argument(
        "--blocks",
        action="store_true",
        help="find marked blocks and compare their sha256",
    )
    parser.add_argument(
        "--block-pattern",
        default=DEFAULT_BLOCK_PATTERN,
        help=(
            "marker line regex with (?P<label>) and (?P<edge>) groups "
            "(default: <!-- LABEL 시작|끝 -->)"
        ),
    )
    parser.add_argument(
        "--expect-block",
        nargs="+",
        action="extend",
        default=[],
        help="LABEL=SHA256 (or an 8+ hex prefix) every block of the label must have",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="base folder of relative paths and globs (default .)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_handoff_leak(args))


if __name__ == "__main__":
    sys.exit(main())
