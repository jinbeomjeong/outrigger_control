"""Parse facts of PowerShell scripts for ``ps1_lint.py``: AST via pwsh, or regex.

Two extractors fill the same :class:`ScriptFacts`:

* ``ast``: ``_ps1_ast.ps1`` run by ``pwsh`` (or Windows PowerShell) with
  ``System.Management.Automation.Language.Parser``. Exact tokens, scopes and
  extents; the script is parsed, never run.
* ``regex``: a conservative fallback when no PowerShell is available. Strings
  and comments are masked by a small scanner, functions and loops are found by
  brace matching. Its limits are listed in the README (``ps1_lint.py`` 한계).

Offsets are positions in the decoded text (UTF-16 code units for ``ast``,
characters for ``regex``); they are only compared within one file and parser.
"""

from __future__ import annotations

import bisect
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from _cli import InputError
from _files import read_text_facts

AST_HELPER = Path(__file__).resolve().parent / "_ps1_ast.ps1"
POWERSHELL_NAMES = ("pwsh", "powershell")
AST_TIMEOUT_S = 120
SCRIPT_SCOPE = -1

FUNCTION_PATTERN = re.compile(r"\bfunction\s+([\w\-:.]+)", re.IGNORECASE)
PARAM_BLOCK_PATTERN = re.compile(r"\bparam\s*\(", re.IGNORECASE)
FOREACH_PATTERN = re.compile(r"\bforeach\s*\(\s*\$(\w+)\s+in\b", re.IGNORECASE)
ASSIGNMENT_PATTERN = re.compile(r"\$(\w+)\s*[+\-*/%]?=(?!=)")
VARIABLE_PATTERN = re.compile(r"\$(?:\{([^}]+)\}|((?:\w+:)?\w+))")
TEE_PATTERN = re.compile(r"\bTee-Object\b|\|\s*tee\b", re.IGNORECASE)
TEE_SINK_PATTERN = re.compile(
    # Output-stream redirection only: "> f", "1> f", "*> f", not "2> f".
    r"\|\s*(?:Out-Null|Out-File|Set-Content|Add-Content)\b|(?<=[\s1*])>(?!&)",
    re.IGNORECASE,
)
CAPTURING_START_PATTERN = re.compile(r"^\s*(?:\$\w+\s*=|\[void\])", re.IGNORECASE)
RETURN_VALUE_PATTERN = re.compile(r"\breturn\b(?=[ \t]+[^\s;}#])", re.IGNORECASE)
NOEXIT_PARAMETER_PATTERN = re.compile(
    r"(?<![\w-])-noe(?:x|xi|xit)?(?![\w-])", re.IGNORECASE
)
COMMENT_STARTERS = frozenset(" \t\r\n;({|")


@dataclass(frozen=True)
class VariableEvent:
    """One use of a variable: ``assign``, ``foreach``, ``param`` or ``read``."""

    kind: str
    name: str
    line: int
    offset: int
    end: int  # end of the statement (assign), the loop (foreach) or the name
    scope: int  # SCRIPT_SCOPE, or the start offset of the enclosing function
    qualified: bool  # $script:x, $env:x ...


@dataclass(frozen=True)
class FunctionFact:
    name: str
    line: int
    scope: int


@dataclass(frozen=True)
class TeeFact:
    line: int
    scope: int
    captured: bool  # output assigned, [void], redirected or piped to Out-Null etc.


@dataclass(frozen=True)
class ReturnFact:
    line: int
    scope: int


@dataclass(frozen=True)
class TextFact:
    """A token's raw text: ``comment``, ``string``, ``bare`` word or ``parameter``."""

    kind: str
    line: int
    text: str


@dataclass
class ScriptFacts:
    """Everything the lint rules read about one script."""

    path: Path
    parser: str
    variables: list[VariableEvent] = field(default_factory=list)
    functions: list[FunctionFact] = field(default_factory=list)
    tees: list[TeeFact] = field(default_factory=list)
    returns: list[ReturnFact] = field(default_factory=list)
    texts: list[TextFact] = field(default_factory=list)
    parse_errors: list[tuple[int, str]] = field(default_factory=list)


class AstUnavailableError(Exception):
    """No PowerShell to run the AST helper, or the helper failed."""


# --- AST extractor -----------------------------------------------------------------


def find_powershell(explicit: str | None) -> str | None:
    """The PowerShell executable to use: ``--pwsh``, else pwsh, else powershell."""
    if explicit:
        return explicit
    for name in POWERSHELL_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _facts_from_json(path: Path, record: dict) -> ScriptFacts:
    if "read_error" in record:
        raise InputError(f"cannot read {path}: {record['read_error']}")
    return ScriptFacts(
        path=path,
        parser="ast",
        variables=[VariableEvent(**item) for item in record["variables"]],
        functions=[FunctionFact(**item) for item in record["functions"]],
        tees=[TeeFact(**item) for item in record["tees"]],
        returns=[ReturnFact(**item) for item in record["returns"]],
        texts=[TextFact(**item) for item in record["texts"]],
        parse_errors=[
            (item["line"], item["message"]) for item in record["parse_errors"]
        ],
    )


def extract_with_ast(paths: list[Path], powershell: str) -> list[ScriptFacts]:
    """Run ``_ps1_ast.ps1`` once for all files.

    Raises:
        AstUnavailableError: If PowerShell cannot start, fails or prints no JSON.
    """
    command = [
        powershell,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",  # this process only; the helper is a local unsigned file
        "-File",
        str(AST_HELPER),
        *[str(path) for path in paths],
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, timeout=AST_TIMEOUT_S, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AstUnavailableError(f"{powershell}: {error}") from error
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0:
        raise AstUnavailableError(
            f"{powershell} exit {completed.returncode}: {stderr[:300]}"
        )
    try:
        records = json.loads(completed.stdout.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AstUnavailableError(f"{powershell} printed no JSON: {error}") from error
    if isinstance(records, dict):  # one file: older ConvertTo-Json may unwrap
        records = [records]
    return [
        _facts_from_json(path, record)
        for path, record in zip(paths, records, strict=True)
    ]


# --- regex extractor ---------------------------------------------------------------


@dataclass(frozen=True)
class _Segment:
    kind: str  # string_single, string_double, comment
    start: int
    end: int  # exclusive


def _here_string_end(text: str, start: int, quote: str) -> int:
    """End (exclusive) of a here-string whose ``@'`` / ``@"`` opener is at ``start``."""
    closing = re.compile(rf"^{quote}@", re.MULTILINE)
    match = closing.search(text, start + 2)
    return len(text) if match is None else match.end()


def _quoted_end(text: str, start: int, quote: str) -> int:
    """End (exclusive) of the quoted string that starts at ``start``."""
    index = start + 1
    while index < len(text):
        character = text[index]
        if quote == '"' and character == "`":
            index += 2
            continue
        if character == quote:
            if index + 1 < len(text) and text[index + 1] == quote:
                index += 2  # '' or "" escape
                continue
            return index + 1
        index += 1
    return len(text)


def _scan_segments(text: str) -> list[_Segment]:
    """Strings and comments of ``text`` in order (a small PowerShell lexer)."""
    segments: list[_Segment] = []
    index = 0
    while index < len(text):
        pair = text[index : index + 2]
        character = text[index]
        previous = text[index - 1] if index else "\n"
        if pair == "<#":
            end = text.find("#>", index + 2)
            end = len(text) if end < 0 else end + 2
            segments.append(_Segment("comment", index, end))
        elif pair in ("@'", '@"') and text[index + 2 : index + 3] in ("\n", "\r"):
            end = _here_string_end(text, index, pair[1])
            kind = "string_single" if pair[1] == "'" else "string_double"
            segments.append(_Segment(kind, index, end))
        elif character == "#" and previous in COMMENT_STARTERS:
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            segments.append(_Segment("comment", index, end))
        elif character in ("'", '"'):
            end = _quoted_end(text, index, character)
            kind = "string_single" if character == "'" else "string_double"
            segments.append(_Segment(kind, index, end))
        else:
            index += 1
            continue
        index = end
    return segments


def _masked_code(text: str, segments: list[_Segment]) -> str:
    """``text`` with string and comment contents blanked (newlines kept)."""
    characters = list(text)
    for segment in segments:
        for index in range(segment.start, segment.end):
            if characters[index] not in "\r\n":
                characters[index] = " "
    return "".join(characters)


def _matching_close(code: str, open_index: int, opener: str, closer: str) -> int:
    depth = 0
    for index in range(open_index, len(code)):
        if code[index] == opener:
            depth += 1
        elif code[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    return len(code) - 1


@dataclass(frozen=True)
class _Region:
    start: int  # scope id (offset of the keyword)
    header_end: int  # offset of the body's opening brace
    end: int  # offset of the body's closing brace


def _function_regions(code: str) -> list[tuple[str, _Region]]:
    regions: list[tuple[str, _Region]] = []
    for match in FUNCTION_PATTERN.finditer(code):
        brace = code.find("{", match.end())
        if brace < 0:
            continue
        regions.append(
            (
                match.group(1),
                _Region(match.start(), brace, _matching_close(code, brace, "{", "}")),
            )
        )
    return regions


class _Lines:
    def __init__(self, text: str) -> None:
        self._starts = [0] + [match.end() for match in re.finditer(r"\n", text)]

    def number(self, offset: int) -> int:
        return bisect.bisect_right(self._starts, offset)


def _scope_of(offset: int, regions: list[tuple[str, _Region]]) -> int:
    """The innermost function whose header or body contains ``offset``."""
    best = SCRIPT_SCOPE
    best_size = None
    for _, region in regions:
        if region.start <= offset <= region.end:
            size = region.end - region.start
            if best_size is None or size < best_size:
                best, best_size = region.start, size
    return best


def _param_spans(
    code: str, regions: list[tuple[str, _Region]]
) -> list[tuple[int, int]]:
    """Function headers ``function F(...)`` and ``param(...)`` blocks."""
    spans = [(region.start, region.header_end) for _, region in regions]
    for match in PARAM_BLOCK_PATTERN.finditer(code):
        open_index = match.end() - 1
        spans.append((open_index, _matching_close(code, open_index, "(", ")")))
    return spans


def _code_with_expandable_strings(
    text: str, code: str, segments: list[_Segment]
) -> str:
    """Masked code with double-quoted strings restored: "$Out/x" reads ``$Out``."""
    characters = list(code)
    for segment in segments:
        if segment.kind == "string_double":
            characters[segment.start : segment.end] = text[segment.start : segment.end]
    return "".join(characters)


class _EventCollector:
    """Collects variable events of one script; a write offset is never a read."""

    def __init__(self, text: str, regions: list[tuple[str, _Region]]) -> None:
        self._lines = _Lines(text)
        self._regions = regions
        self.events: list[VariableEvent] = []
        self.writes: set[int] = set()

    def add(self, kind: str, name: str, offset: int, end: int) -> None:
        scope = _scope_of(offset, self._regions)
        line = self._lines.number(offset)
        self.events.append(
            VariableEvent(kind, name, line, offset, end, scope, ":" in name)
        )
        if kind != "read":
            self.writes.add(offset)


def _variable_name(match: re.Match[str]) -> str:
    return match.group(2) or match.group(1)


def _collect_params(
    code: str, collector: _EventCollector, regions: list[tuple[str, _Region]]
) -> None:
    spans = _param_spans(code, regions)
    for match in VARIABLE_PATTERN.finditer(code):
        if any(start <= match.start() <= end for start, end in spans):
            collector.add("param", _variable_name(match), match.start(), match.end())


def _collect_foreach(code: str, collector: _EventCollector) -> None:
    for match in FOREACH_PATTERN.finditer(code):
        header_close = _matching_close(code, code.find("(", match.start()), "(", ")")
        body = code.find("{", header_close)
        loop_end = _matching_close(code, body, "{", "}") if body >= 0 else header_close
        collector.add("foreach", match.group(1), match.start(1) - 1, loop_end)


def _collect_assignments(code: str, collector: _EventCollector) -> None:
    for match in ASSIGNMENT_PATTERN.finditer(code):
        if match.start() in collector.writes:
            continue  # a parameter default value
        line_end = code.find("\n", match.end())
        statement_end = len(code) if line_end < 0 else line_end
        collector.add("assign", match.group(1), match.start(), statement_end)


def _variable_events(
    text: str, code: str, segments: list[_Segment], regions: list[tuple[str, _Region]]
) -> list[VariableEvent]:
    collector = _EventCollector(text, regions)
    _collect_params(code, collector, regions)
    _collect_foreach(code, collector)
    _collect_assignments(code, collector)
    readable = _code_with_expandable_strings(text, code, segments)
    for match in VARIABLE_PATTERN.finditer(readable):
        if match.start() not in collector.writes:
            collector.add("read", _variable_name(match), match.start(), match.end())
    return sorted(collector.events, key=lambda event: event.offset)


def _tee_and_returns(
    text: str, code: str, regions: list[tuple[str, _Region]]
) -> tuple[list[TeeFact], list[ReturnFact]]:
    lines = _Lines(text)
    tees: list[TeeFact] = []
    for match in TEE_PATTERN.finditer(code):
        line_start = code.rfind("\n", 0, match.start()) + 1
        line_end = code.find("\n", match.start())
        line_code = code[line_start : len(code) if line_end < 0 else line_end]
        after_tee = code[match.start() : line_start + len(line_code)]
        captured = bool(
            TEE_SINK_PATTERN.search(after_tee)
            or CAPTURING_START_PATTERN.match(line_code)
        )
        tees.append(
            TeeFact(
                lines.number(match.start()), _scope_of(match.start(), regions), captured
            )
        )
    returns = [
        ReturnFact(lines.number(match.start()), _scope_of(match.start(), regions))
        for match in RETURN_VALUE_PATTERN.finditer(code)
    ]
    return tees, returns


def _text_facts(text: str, code: str, segments: list[_Segment]) -> list[TextFact]:
    lines = _Lines(text)
    facts = [
        TextFact(
            "comment" if segment.kind == "comment" else "string",
            lines.number(segment.start),
            text[segment.start : segment.end],
        )
        for segment in segments
    ]
    for number, line_code in enumerate(code.splitlines(), start=1):
        if line_code.strip():
            facts.append(TextFact("bare", number, line_code))
    facts += [
        TextFact("parameter", lines.number(match.start()), match.group(0))
        for match in NOEXIT_PARAMETER_PATTERN.finditer(code)
    ]
    return facts


def extract_with_regex(path: Path) -> ScriptFacts:
    """Conservative facts without PowerShell (see the README limits)."""
    text = read_text_facts(path).text
    segments = _scan_segments(text)
    code = _masked_code(text, segments)
    regions = _function_regions(code)
    tees, returns = _tee_and_returns(text, code, regions)
    lines = _Lines(text)
    return ScriptFacts(
        path=path,
        parser="regex",
        variables=_variable_events(text, code, segments, regions),
        functions=[
            FunctionFact(name, lines.number(region.start), region.start)
            for name, region in regions
        ],
        tees=tees,
        returns=returns,
        texts=_text_facts(text, code, segments),
    )
