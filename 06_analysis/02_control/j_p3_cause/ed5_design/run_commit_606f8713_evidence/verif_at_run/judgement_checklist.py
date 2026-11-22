"""Judgement checklist: does the judgement record what the rules say it must?

Rule files (an original plus ``_rev<N>`` addenda) tell the judgement document
what to record: "판정서에 적을 것" sections, "판정서에 적는다" sentences,
disclosure sections (공개, 사후 관찰). This tool extracts those directives
(see ``_directives.py``), lists them for the auditor, and looks up each
directive's key tokens (hash prefixes, item labels, numbers, clock times, code
spans, quoted phrases) in the judgement.

Per directive:

* ``found``: every token occurs in the judgement (evidence ``path:line``).
* ``missing``: a strong directive whose own tokens occur nowhere.
* ``ambiguous``: anything in between: no key token, only some tokens, a weak
  directive, or tokens borrowed from the surrounding item.

Exit code 1 when at least one directive is ``missing``. Zero directives is
``ok`` with ``items: 0`` and a note; it is not reported as a pass.

Usage:
    python judgement_checklist.py --rules RULE.md [RULE_rev1.md ...]
        --judgement JUDGEMENT.md [--repo DIR] [--out REPORT]
        [--format md|json] [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import ToolOutcome, configure_console, parse_arguments, run_tool
from _directives import (
    HEX_PATTERN,
    Directive,
    Scope,
    Strength,
    Token,
    TokenKind,
    extract_directives,
)
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
    sort_findings,
)
from _rules import RuleEdition, editions_for_files

TOOL_NAME = "judgement_checklist"
MAX_EVIDENCE_LINES = 3
MIN_JUDGEMENT_HEX_CHARS = 7
MIN_EDITION_PREFIX_CHARS = 8
NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\d])")
# Words that close a prediction comparison on the same judgement line
# ("| P-16 | ... | 맞음 |", "P-19 틀림"). Added 2026-11-16.
PREDICTION_VERDICT_PATTERN = re.compile(
    r"맞음|맞았|맞다|틀림|틀렸|틀리다|적중|빗나|부분\s*맞음|대조\s*불가|판정\s*불가|미확인"
)
EMPTY_NOTE = (
    "규칙에서 판정서 지시를 하나도 찾지 못함(items 0). 통과가 아니다 — "
    "지시가 정말 없는지 규칙 원문을 읽어 확인할 것"
)


class ItemStatus(StrEnum):
    """Outcome of one directive."""

    FOUND = "found"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class _JudgementLine:
    display: str
    number: int
    text: str

    def location(self) -> str:
        return f"{self.display}:{self.number}"


@dataclass(frozen=True)
class TokenResult:
    token: Token
    evidence: tuple[str, ...]

    @property
    def is_found(self) -> bool:
        return bool(self.evidence)


@dataclass(frozen=True)
class ItemResult:
    item_id: str
    directive: Directive
    status: ItemStatus
    reason: str
    tokens: tuple[TokenResult, ...]


# --- judgement index --------------------------------------------------------------------


def _normalise(text: str) -> str:
    return " ".join(text.replace("**", "").split())


class JudgementIndex:
    """Searchable lines, hex tokens and numbers of the judgement files."""

    def __init__(self, files: list[tuple[str, str]]) -> None:
        # A rule naming the judgement file ("판정서(`x_judgement.md`)") is
        # satisfied by the file itself; its body rarely repeats its own name.
        self.self_names = {
            re.split(r"[\\/]", display)[-1]: f"{display}:0 (판정서 자체)"
            for display, _ in files
        }
        self.lines: list[_JudgementLine] = []
        for display, text in files:
            for number, raw in enumerate(text.splitlines(), start=1):
                self.lines.append(_JudgementLine(display, number, _normalise(raw)))
        self.hexes = [
            (match.group(0), line)
            for line in self.lines
            for match in HEX_PATTERN.finditer(line.text)
            if len(match.group(0)) >= MIN_JUDGEMENT_HEX_CHARS
        ]
        self.numbers: dict[float, list[_JudgementLine]] = {}
        for line in self.lines:
            for match in NUMBER_PATTERN.finditer(line.text):
                self.numbers.setdefault(float(match.group(0)), []).append(line)
        self._joined = " ".join(line.text for line in self.lines)
        self._starts: list[int] = []
        offset = 0
        for line in self.lines:
            self._starts.append(offset)
            offset += len(line.text) + 1

    def _line_at(self, offset: int) -> _JudgementLine:
        return self.lines[bisect.bisect_right(self._starts, offset) - 1]

    def substring(self, needle: str) -> list[_JudgementLine]:
        """Lines containing ``needle``; a phrase broken across lines is found too."""
        hits = [line for line in self.lines if needle in line.text]
        if not hits and needle in self._joined:
            hits = [self._line_at(self._joined.index(needle))]
        return hits

    def pattern(self, regex: re.Pattern[str]) -> list[_JudgementLine]:
        return [line for line in self.lines if regex.search(line.text)]

    def hex_prefix(self, value: str, min_chars: int) -> list[_JudgementLine]:
        """Lines whose hex token and ``value`` share a prefix of ``min_chars`` or more."""
        hits: list[_JudgementLine] = []
        for text, line in self.hexes:
            shorter = min(len(text), len(value))
            if shorter >= min_chars and (
                text.startswith(value) or value.startswith(text)
            ):
                hits.append(line)
        return hits


# --- matching -------------------------------------------------------------------------


def _code_hits(value: str, index: JudgementIndex) -> list[_JudgementLine]:
    hits = index.substring(value)
    basename = re.split(r"[\\/]", value)[-1]
    if not hits and basename != value and len(basename) >= MIN_JUDGEMENT_HEX_CHARS:
        hits = index.substring(basename)
    return hits


def _label_pattern(label: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_:\-]){re.escape(label)}(?![A-Za-z0-9_:])")


def _prediction_hits(label: str, index: JudgementIndex) -> list[_JudgementLine]:
    """Lines naming ``label`` together with a verdict word (the comparison row)."""
    return [
        line
        for line in index.pattern(_label_pattern(label))
        if PREDICTION_VERDICT_PATTERN.search(line.text)
    ]


def _token_hits(token: Token, index: JudgementIndex) -> list[_JudgementLine]:
    if token.kind is TokenKind.PREDICTION:
        return _prediction_hits(token.value, index)
    if token.kind is TokenKind.HASH:
        return index.hex_prefix(token.value.lower(), MIN_JUDGEMENT_HEX_CHARS)
    if token.kind is TokenKind.EDITION_HASH:
        hits: list[_JudgementLine] = []
        for candidate in token.candidates:
            hits += index.hex_prefix(candidate, MIN_EDITION_PREFIX_CHARS)
        return hits
    if token.kind is TokenKind.NUMBER:
        return index.numbers.get(float(token.value), [])
    if token.kind in (TokenKind.LABEL, TokenKind.TIME):
        return index.pattern(_label_pattern(token.value))
    if token.kind is TokenKind.CODE:
        return _code_hits(token.value, index)
    return index.substring(_normalise(token.value))


def _evidence(hits: list[_JudgementLine]) -> tuple[str, ...]:
    locations: list[str] = []
    for line in hits:
        location = line.location()
        if location not in locations:
            locations.append(location)
    return tuple(locations[:MAX_EVIDENCE_LINES])


def _classify(
    directive: Directive, results: list[TokenResult]
) -> tuple[ItemStatus, str]:
    """Missing only for a strong directive whose own tokens are all absent."""
    if not results:
        return ItemStatus.AMBIGUOUS, "no_key_tokens"
    found = sum(1 for result in results if result.is_found)
    if found == len(results):
        return ItemStatus.FOUND, "all_tokens_found"
    if directive.strength is Strength.WEAK:
        return ItemStatus.AMBIGUOUS, "weak_none_found" if found == 0 else "weak_partial"
    if directive.scope is Scope.CONTEXT:
        return (
            ItemStatus.AMBIGUOUS,
            "context_none_found" if found == 0 else "context_partial",
        )
    if directive.scope is Scope.PRECEDING:
        # The sentence points at the list before it ("…는 판정서에 공개한다"):
        # none of that list's tokens in the judgement means nothing was disclosed.
        if found == 0:
            return ItemStatus.MISSING, "preceding_none_found"
        return ItemStatus.AMBIGUOUS, "preceding_partial"
    if found == 0:
        return ItemStatus.MISSING, "no_token_found"
    if directive.origin == "prediction":
        return ItemStatus.AMBIGUOUS, "prediction_not_compared"  # P-n named, no verdict
    return ItemStatus.AMBIGUOUS, "partial"


def _token_result(token: Token, index: JudgementIndex) -> TokenResult:
    if token.kind is TokenKind.CODE:
        self_location = index.self_names.get(re.split(r"[\\/]", token.value)[-1])
        if self_location is not None:
            return TokenResult(token, (self_location,))
    return TokenResult(token, _evidence(_token_hits(token, index)))


def check_directive(
    item_id: str, directive: Directive, index: JudgementIndex
) -> ItemResult:
    """Look up every token of ``directive`` and classify the item."""
    results = [_token_result(token, index) for token in directive.tokens]
    status, reason = _classify(directive, results)
    return ItemResult(item_id, directive, status, reason, tuple(results))


# --- report ------------------------------------------------------------------------------


def _display(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix() if is_within(path, repo) else str(path)


def _item_dict(result: ItemResult, repo: Path) -> dict[str, object]:
    directive = result.directive
    return {
        "id": result.item_id,
        "status": str(result.status),
        "reason": result.reason,
        "rule": f"{_display(directive.rule_path, repo)}:{directive.line}",
        "edition": directive.edition,
        "section": directive.section,
        "unit": directive.unit,
        "origin": directive.origin,
        "strength": str(directive.strength),
        "scope": str(directive.scope),
        "text": directive.text,
        "tokens": [
            {
                "kind": str(item.token.kind),
                "value": item.token.value,
                "found": item.is_found,
                "evidence": list(item.evidence),
            }
            for item in result.tokens
        ],
    }


def _token_display(token: Token) -> str:
    if token.kind is TokenKind.PREDICTION:
        return f"{token.value} 대조(맞음·틀림)"
    return token.value


def _finding(result: ItemResult) -> Finding | None:
    directive = result.directive
    if result.status is ItemStatus.FOUND:
        return None
    absent = [_token_display(item.token) for item in result.tokens if not item.is_found]
    excerpt = (
        directive.text if len(directive.text) <= 120 else directive.text[:117] + "..."
    )
    if result.status is ItemStatus.MISSING:
        message = f"판정서에 토큰 없음: {', '.join(absent)} — 지시: {excerpt}"
        severity, category = Severity.ERROR, "item_missing"
    else:
        detail = f"없는 토큰: {', '.join(absent)}" if absent else "핵심 토큰 없음"
        message = f"{result.reason} ({detail}) — 지시: {excerpt}"
        severity, category = Severity.INFO, "item_ambiguous"
    return Finding(
        severity,
        category,
        str(directive.rule_path),
        directive.line,
        message,
        result.item_id,
    )


def _escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _token_cell(result: ItemResult) -> str:
    marks = [
        f"{'✓' if item.is_found else '✗'}{_token_display(item.token)}"
        for item in result.tokens
    ]
    return ", ".join(marks) or "-"


def _evidence_cell(result: ItemResult) -> str:
    locations: list[str] = []
    for item in result.tokens:
        locations += [
            location for location in item.evidence if location not in locations
        ]
    return ", ".join(locations[:6]) or "-"


@dataclass(frozen=True)
class RuleRow:
    """One rule edition given to the tool and how many directives it yielded."""

    path: str
    family: str
    edition: str
    items: int


@dataclass(frozen=True)
class _ReportContext:
    repo: Path
    rules: list[RuleRow]
    judgements: list[str]
    summary: dict[str, object]


def _markdown(
    context: _ReportContext, results: list[ItemResult], findings: list[Finding]
) -> list[str]:
    summary = context.summary
    lines = ["# 판정서 지시 대조 (judgement_checklist)", "", "## 입력", ""]
    lines += [
        f"- 규칙 판: `{rule.path}` ({rule.edition}, 항목 {rule.items})"
        for rule in context.rules
    ]
    lines += [f"- 판정서: `{path}`" for path in context.judgements]
    lines += [
        "",
        f"항목 {summary['items']} — found {summary['found']} · missing {summary['missing']} "
        f"· ambiguous {summary['ambiguous']}",
        "",
    ]
    if "note" in summary:
        lines += [f"**참고: {summary['note']}**", ""]
    lines += [
        "## 추출 항목",
        "",
        "| # | 상태 | 규칙 위치 | 절 | 출처 | 토큰(✓ 있음, ✗ 없음) | 판정서 근거 | 지시 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        directive = result.directive
        cells = (
            result.item_id,
            f"{result.status} ({result.reason})",
            f"{_display(directive.rule_path, context.repo)}:{directive.line}",
            directive.section,
            f"{directive.origin}/{directive.unit}/{directive.strength}/{directive.scope}",
            _token_cell(result),
            _evidence_cell(result),
            directive.text,
        )
        lines.append("| " + " | ".join(_escape(cell) for cell in cells) + " |")
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


# --- run --------------------------------------------------------------------------------


def _read_judgements(paths: list[Path], repo: Path) -> JudgementIndex:
    return JudgementIndex(
        [(_display(path, repo), read_text_facts(path).text) for path in paths]
    )


def _extract_all(editions: list[RuleEdition]) -> list[Directive]:
    directives: list[Directive] = []
    for edition in editions:
        directives += extract_directives(edition, editions)
    return directives


def _summary(
    results: list[ItemResult], findings: list[Finding], rules: int, judgements: int
) -> dict[str, object]:
    counts = {
        status: sum(1 for r in results if r.status is status) for status in ItemStatus
    }
    summary: dict[str, object] = {
        "tool": TOOL_NAME,
        "command": "check",
        "rules": rules,
        "judgements": judgements,
        "items": len(results),
        "found": counts[ItemStatus.FOUND],
        "missing": counts[ItemStatus.MISSING],
        "ambiguous": counts[ItemStatus.AMBIGUOUS],
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    if not results:
        summary["note"] = EMPTY_NOTE
    return summary


def _empty_finding(editions: list[RuleEdition]) -> Finding:
    return Finding(Severity.INFO, "no_items", str(editions[0].path), 0, EMPTY_NOTE)


def run_checklist(args: argparse.Namespace) -> ToolOutcome:
    """Extract directives from the rules and look them up in the judgement."""
    repo = args.repo.expanduser().resolve()
    rule_files = expand_file_patterns(args.rules, repo)
    judgement_files = expand_file_patterns(args.judgement, repo)
    editions = editions_for_files(rule_files, include_revisions=False)
    require_output_outside(args.out, [*rule_files, *judgement_files])

    index = _read_judgements(judgement_files, repo)
    directives = _extract_all(editions)
    results = [
        check_directive(f"D{number:03d}", directive, index)
        for number, directive in enumerate(directives, start=1)
    ]
    findings = [finding for result in results if (finding := _finding(result))]
    if not results:
        findings.append(_empty_finding(editions))
    findings = sort_findings(findings)

    rule_rows = [
        RuleRow(
            _display(edition.path, repo),
            edition.family,
            edition.label,
            sum(1 for directive in directives if directive.rule_path == edition.path),
        )
        for edition in editions
    ]
    context = _ReportContext(
        repo,
        rule_rows,
        [_display(path, repo) for path in judgement_files],
        _summary(results, findings, len(editions), len(judgement_files)),
    )
    report: dict[str, object] = {
        "tool": TOOL_NAME,
        "repo": str(repo),
        "rules": [asdict(row) for row in rule_rows],
        "judgements": context.judgements,
        "items": [_item_dict(result, repo) for result in results],
        "summary": context.summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    markdown = _markdown(context, results, findings)
    lines = deliver_report(args, markdown, report, [*rule_files, *judgement_files])
    exit_code = exit_code_for(findings, Severity(args.fail_on))
    return ToolOutcome(exit_code, lines, context.summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="judgement_checklist.py",
        description="규칙의 '판정서에 적을 것'·공개 지시를 뽑아 판정서와 대조한다(읽기 전용).",
    )
    parser.add_argument(
        "--rules",
        nargs="+",
        action="extend",
        required=True,
        help="rule .md files or globs (original and _rev<N> addenda), relative to --repo",
    )
    parser.add_argument(
        "--judgement",
        nargs="+",
        action="extend",
        required=True,
        help="judgement .md file(s) or globs, relative to --repo",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="base folder of relative paths and globs (default: current folder)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_checklist(args))


if __name__ == "__main__":
    sys.exit(main())
