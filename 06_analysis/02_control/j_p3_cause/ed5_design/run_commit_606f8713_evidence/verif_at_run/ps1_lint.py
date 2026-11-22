"""Static checks of PowerShell run scripts before a judged run (E·I axes).

Four checks, each from an incident in the 436.8 audits:

* (a) ``case_variant_overwrite``: PowerShell variable names ignore case, so
  ``foreach ($grid in ...)`` overwrites ``$Grid`` assigned earlier. When the
  earlier spelling is read after the loop (or the assignment) the run uses the
  overwritten value (error); without such a read it is a warning.
  ``foreach_overwrites_variable``: the same spelling reused as a loop
  variable after an ordinary assignment and read after the loop (warning).
* (b) ``tee_with_return``: a function that both pipes to ``Tee-Object``
  (output not captured) and ``return``s a value returns the tee output too.
* (c) ``placeholder_unfilled``: an unfilled slot (``M4_FULL_HASH``,
  ``{NAME}``, ``<OUT>``, ``PLACEHOLDER``) in a string or bare word. In a
  comment it is info. Slots named with ``--allow`` (``ED5_RUN_COMMIT``,
  ``<ED5_RUN_COMMIT>`` or ``{ED5_RUN_COMMIT}``, the same meaning as in
  ``placeholder_scan.py``) are ``placeholder_allowed`` info, so a script whose
  only slots are allowed ones exits 0 (2026-11-22).
* (d) ``noexit``: ``-NoExit`` (or its abbreviation ``-noe``) as a parameter or
  inside a string such as ``-ArgumentList '-NoExit'``; the window never closes,
  so a wait on the process never ends. In a comment it is info.

The parser is the PowerShell AST (``_ps1_ast.ps1`` via pwsh or Windows
PowerShell); ``--parser regex`` (or ``auto`` without PowerShell) uses a
conservative regex scanner whose limits are in the README. The scripts are
parsed, never run.

Usage:
    python ps1_lint.py FILE_OR_GLOB [...] [--repo DIR] [--parser auto|ast|regex]
        [--pwsh PATH] [--placeholder REGEX ...] [--allow TOKEN ...]
        [--out REPORT] [--format md|json] [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import expand_file_patterns, require_output_outside
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
from _ps1_facts import (
    NOEXIT_PARAMETER_PATTERN,
    AstUnavailableError,
    ScriptFacts,
    VariableEvent,
    extract_with_ast,
    extract_with_regex,
    find_powershell,
)
from _slots import allowed_slot_names, slot_name

TOOL_NAME = "ps1_lint"
PARSER_CHOICES = ("auto", "ast", "regex")
DEFAULT_PLACEHOLDER_PATTERNS = (
    r"(?<![$\w])[A-Z][A-Z0-9_]*_FULL_HASH(?!\w)",
    r"(?<![$\w])\{[A-Z][A-Z0-9_]*\}",  # ${Name} is variable syntax, not a slot
    r"<[A-Z][A-Z0-9_]*>",
    r"(?<!\w)(?:PLACEHOLDER|FILL_?ME|TO_?BE_?FILLED)(?!\w)",
)
# Automatic and preference variables: their case is conventional, not a bug.
AUTOMATIC_VARIABLES = frozenset(
    {
        "_", "psitem", "args", "input", "this", "true", "false", "null",
        "lastexitcode", "matches", "error", "psscriptroot", "pscommandpath",
        "myinvocation", "psboundparameters", "host", "home", "pwd", "pid", "ofs",
        "foreach", "switch", "erroractionpreference", "progresspreference",
        "verbosepreference", "warningpreference", "informationpreference",
        "debugpreference", "confirmpreference", "psdefaultparametervalues",
        "psnativecommanduseerroractionpreference",
    }
)  # fmt: skip
WRITE_KINDS = frozenset({"assign", "foreach", "param"})
MAX_LINES_IN_MESSAGE = 5


@dataclass(frozen=True)
class _ScopeEvents:
    """The variable events of one scope (script or one function), in offset order."""

    events: list[VariableEvent]

    def later_reads(
        self, after: VariableEvent, spelling: str | None
    ) -> list[VariableEvent]:
        """Reads after ``after`` ends that still see its value (no write between).

        ``spelling`` restricts the reads to one exact spelling; ``None`` takes all.
        """
        key = after.name.lower()
        reads: list[VariableEvent] = []
        for event in self.events:
            if event.offset <= after.end or event.name.lower() != key:
                continue
            if event.kind in WRITE_KINDS:
                break  # a new value from here on
            if spelling is None or event.name == spelling:
                reads.append(event)
        return reads


@dataclass(frozen=True)
class _Kind:
    """Severity and category of a finding."""

    severity: Severity
    category: str


CASE_VARIANT_OVERWRITE = _Kind(Severity.ERROR, "case_variant_overwrite")
CASE_VARIANT_REUSE = _Kind(Severity.WARNING, "case_variant_reuse")
FOREACH_OVERWRITE = _Kind(Severity.WARNING, "foreach_overwrites_variable")
TEE_WITH_RETURN = _Kind(Severity.WARNING, "tee_with_return")
TEE_CAPTURED = _Kind(Severity.INFO, "tee_captured_with_return")
PLACEHOLDER_UNFILLED = _Kind(Severity.ERROR, "placeholder_unfilled")
PLACEHOLDER_IN_COMMENT = _Kind(Severity.INFO, "placeholder_in_comment")
PLACEHOLDER_ALLOWED = _Kind(Severity.INFO, "placeholder_allowed")
NOEXIT = _Kind(Severity.WARNING, "noexit")
NOEXIT_IN_COMMENT = _Kind(Severity.INFO, "noexit_in_comment")
PARSE_ERROR = _Kind(Severity.ERROR, "parse_error")


def _finding(
    facts: ScriptFacts, kind: _Kind, line: int, message: str, target: str = ""
) -> Finding:
    return Finding(kind.severity, kind.category, str(facts.path), line, message, target)


def _lines_text(lines: list[int]) -> str:
    numbers = sorted(set(lines))
    shown = ", ".join(str(number) for number in numbers[:MAX_LINES_IN_MESSAGE])
    return shown + (" ..." if len(numbers) > MAX_LINES_IN_MESSAGE else "")


def _scopes(facts: ScriptFacts) -> list[_ScopeEvents]:
    grouped: dict[int, list[VariableEvent]] = defaultdict(list)
    for event in facts.variables:
        if event.qualified or event.name.lower() in AUTOMATIC_VARIABLES:
            continue
        grouped[event.scope].append(event)
    return [
        _ScopeEvents(sorted(events, key=lambda item: item.offset))
        for events in grouped.values()
    ]


def _write_text(event: VariableEvent) -> str:
    if event.kind == "foreach":
        return f"`foreach (${event.name} in ...)`"
    return f"`${event.name} =`"


def _case_variant_finding(
    facts: ScriptFacts, scope: _ScopeEvents, first: VariableEvent, event: VariableEvent
) -> Finding:
    base = (
        f"{_write_text(event)}: {first.line}행의 `${first.name}`({first.kind})와 "
        "대소문자만 다른 이름. PowerShell 변수 이름은 대소문자를 가리지 않으므로 "
        "같은 변수를 덮어쓴다"
    )
    target = f"${first.name}"
    reads = scope.later_reads(event, first.name)
    if not reads:
        return _finding(facts, CASE_VARIANT_REUSE, event.line, base, target)
    read_lines = _lines_text([read.line for read in reads])
    message = f"{base}. 덮어쓴 뒤 `${first.name}`을 읽는 줄: {read_lines}"
    return _finding(facts, CASE_VARIANT_OVERWRITE, event.line, message, target)


def _foreach_overwrite_finding(
    facts: ScriptFacts, scope: _ScopeEvents, first: VariableEvent, event: VariableEvent
) -> Finding | None:
    reads = scope.later_reads(event, None)
    if not reads:
        return None
    message = (
        f"{_write_text(event)}: {first.line}행에서 대입한 같은 변수를 루프 변수로 "
        f"덮어쓴다. 루프 뒤 그 값을 읽는 줄: {_lines_text([r.line for r in reads])}"
    )
    return _finding(facts, FOREACH_OVERWRITE, event.line, message, f"${event.name}")


def check_variable_reuse(facts: ScriptFacts) -> list[Finding]:
    """Rule (a): a write that reuses an earlier variable under another spelling."""
    findings: list[Finding] = []
    for scope in _scopes(facts):
        first_write: dict[str, VariableEvent] = {}
        for event in scope.events:
            if event.kind not in WRITE_KINDS:
                continue
            first = first_write.setdefault(event.name.lower(), event)
            if first is event or event.kind == "param":
                continue
            if first.name != event.name:
                findings.append(_case_variant_finding(facts, scope, first, event))
            elif event.kind == "foreach" and first.kind == "assign":
                finding = _foreach_overwrite_finding(facts, scope, first, event)
                if finding is not None:
                    findings.append(finding)
    return findings


def check_tee_with_return(facts: ScriptFacts) -> list[Finding]:
    """Rule (b): Tee-Object output and a returned value in one function."""
    findings: list[Finding] = []
    for function in facts.functions:
        tees = [tee for tee in facts.tees if tee.scope == function.scope]
        returns = [item.line for item in facts.returns if item.scope == function.scope]
        if not tees or not returns:
            continue
        loose = [tee.line for tee in tees if not tee.captured]
        where = f"함수 `{function.name}`"
        if loose:
            message = (
                f"{where}: Tee-Object(줄 {_lines_text(loose)})의 출력이 return 값"
                f"(줄 {_lines_text(returns)})과 함께 반환된다(반환값이 배열이 된다)"
            )
            kind = TEE_WITH_RETURN
        else:
            message = (
                f"{where}: Tee-Object 출력은 대입·Out-Null·리디렉션으로 잡혀 있다"
                f"(return 줄 {_lines_text(returns)})"
            )
            kind = TEE_CAPTURED
        findings.append(_finding(facts, kind, function.line, message, function.name))
    return findings


def _matches_in(text: str, patterns: list[re.Pattern[str]]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for pattern in patterns:
        found += [(match.start(), match.group(0)) for match in pattern.finditer(text)]
    return sorted(found)


def _placeholder_kind(token: str, text_kind: str, allowed: set[str]) -> _Kind:
    if slot_name(token) in allowed:
        return PLACEHOLDER_ALLOWED
    if text_kind == "comment":
        return PLACEHOLDER_IN_COMMENT
    return PLACEHOLDER_UNFILLED


def check_placeholders(
    facts: ScriptFacts, patterns: list[re.Pattern[str]], allowed: set[str]
) -> list[Finding]:
    """Rule (c): unfilled slots in strings and bare words (comments: info).

    ``allowed`` holds slot names (see ``_slots``); their tokens become
    ``placeholder_allowed`` info wherever they stand, as in placeholder_scan.
    """
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for text in facts.texts:
        if text.kind == "parameter":
            continue
        for start, token in _matches_in(text.text, patterns):
            line = text.line + text.text.count("\n", 0, start)
            if (line, token) in seen:
                continue
            seen.add((line, token))
            kind = _placeholder_kind(token, text.kind, allowed)
            message = f"{token} ({text.kind})"
            findings.append(_finding(facts, kind, line, message, token))
    return findings


def check_noexit(facts: ScriptFacts) -> list[Finding]:
    """Rule (d): -NoExit as a parameter or inside a string (comments: info)."""
    findings: list[Finding] = []
    for text in facts.texts:
        if text.kind == "bare":
            continue
        for match in NOEXIT_PARAMETER_PATTERN.finditer(text.text):
            line = text.line + text.text.count("\n", 0, match.start())
            kind = NOEXIT_IN_COMMENT if text.kind == "comment" else NOEXIT
            message = (
                f"{match.group(0)} ({text.kind}): 창이 닫히지 않아 "
                "프로세스 종료 대기가 끝나지 않는다"
            )
            findings.append(_finding(facts, kind, line, message, match.group(0)))
    return findings


def _parse_error_findings(facts: ScriptFacts) -> list[Finding]:
    return [
        _finding(facts, PARSE_ERROR, line, message)
        for line, message in facts.parse_errors
    ]


# --- run ---------------------------------------------------------------------------


def _compile_patterns(extra: list[str]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for text in [*DEFAULT_PLACEHOLDER_PATTERNS, *extra]:
        try:
            patterns.append(re.compile(text))
        except re.error as error:
            raise InputError(
                f"--placeholder is not a valid regular expression: {text} ({error})"
            ) from error
    return patterns


def collect_facts(
    files: list[Path], parser: str, pwsh: str | None
) -> tuple[list[ScriptFacts], list[Finding]]:
    """Facts of every file and info findings about the parser actually used.

    Raises:
        InputError: If ``--parser ast`` was asked and PowerShell is unusable.
    """
    if parser == "regex":
        return [extract_with_regex(path) for path in files], []
    powershell = find_powershell(pwsh)
    problem = "no pwsh / powershell on PATH" if powershell is None else ""
    if powershell is not None:
        try:
            return extract_with_ast(files, powershell), []
        except AstUnavailableError as error:
            problem = str(error)
    if parser == "ast":
        raise InputError(f"--parser ast: PowerShell AST unavailable ({problem})")
    message = (
        f"PowerShell AST를 쓰지 못해 정규식 파서로 검사했다({problem}). "
        "README의 한계를 볼 것"
    )
    note = Finding(Severity.INFO, "parser_fallback", str(files[0]), 0, message)
    return [extract_with_regex(path) for path in files], [note]


def lint_file(
    facts: ScriptFacts, patterns: list[re.Pattern[str]], allowed: set[str]
) -> list[Finding]:
    """All four rules plus parse errors for one script."""
    return [
        *_parse_error_findings(facts),
        *check_variable_reuse(facts),
        *check_tee_with_return(facts),
        *check_placeholders(facts, patterns, allowed),
        *check_noexit(facts),
    ]


def _file_row(facts: ScriptFacts, findings: list[Finding]) -> dict[str, object]:
    own = [item for item in findings if item.file == str(facts.path)]
    return {
        "path": str(facts.path),
        "parser": facts.parser,
        "parse_errors": len(facts.parse_errors),
        "variables": len(facts.variables),
        "functions": len(facts.functions),
        **count_by_severity(own),
    }


def _markdown(rows: list[dict[str, object]], findings: list[Finding]) -> list[str]:
    parsers = sorted({str(row["parser"]) for row in rows})
    overview = (
        f"- 파일 {len(rows)}개, 파서 {', '.join(parsers)} · "
        f"{severity_summary_text(findings)}"
    )
    lines = [
        "# ps1_lint — PowerShell 실행 스크립트 정적 검사",
        "",
        overview,
        "",
        "| 파일 | 파서 | 구문 오류 | 오류 | 경고 | 참고 |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['path']}` | {row['parser']} | {row['parse_errors']} "
            f"| {row['error']} | {row['warning']} | {row['info']} |"
        )
    return [*lines, "", "## 발견 사항", "", *findings_markdown(findings)]


def run_ps1_lint(args: argparse.Namespace) -> ToolOutcome:
    """Parse the scripts, apply the rules and build the report."""
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    files = expand_file_patterns(args.inputs, base)
    require_output_outside(args.out, files)
    patterns = _compile_patterns(args.placeholder)
    allowed = allowed_slot_names(args.allow)
    all_facts, findings = collect_facts(files, args.parser, args.pwsh)
    for facts in all_facts:
        findings += lint_file(facts, patterns, allowed)
    findings = sort_findings(findings)
    rows = [_file_row(facts, findings) for facts in all_facts]
    summary: dict[str, object] = {
        "tool": TOOL_NAME,
        "command": "lint",
        "files": len(files),
        "parsers": sorted({facts.parser for facts in all_facts}),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report: dict[str, object] = {
        "tool": TOOL_NAME,
        "placeholder_patterns": [pattern.pattern for pattern in patterns],
        "allow": sorted(allowed),
        "files": rows,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(rows, findings), report, files)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="ps1_lint.py",
        description=(
            "PowerShell 실행 스크립트의 변수 대소문자 재사용·Tee-Object+return·"
            "자리표시·-NoExit를 찾는다(읽기 전용, 실행하지 않음)."
        ),
    )
    parser.add_argument(
        "inputs", nargs="+", help=".ps1 files or globs (relative to --repo)"
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="base folder of relative paths and globs (default .)",
    )
    parser.add_argument(
        "--parser",
        choices=PARSER_CHOICES,
        default="auto",
        help=(
            "ast: PowerShell AST (exit 2 if unavailable); regex: fallback scanner; "
            "auto (default): ast, else regex with a parser_fallback info"
        ),
    )
    parser.add_argument(
        "--pwsh", help="PowerShell executable (default: pwsh, then powershell on PATH)"
    )
    parser.add_argument(
        "--placeholder",
        nargs="+",
        action="extend",
        default=[],
        help="extra placeholder regexes (added to the defaults)",
    )
    parser.add_argument(
        "--allow",
        nargs="+",
        action="extend",
        default=[],
        help=(
            "slots that may stay (MASK, {MASK} or <MASK>, as placeholder_scan); "
            "reported as placeholder_allowed info"
        ),
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_ps1_lint(args))


if __name__ == "__main__":
    sys.exit(main())
