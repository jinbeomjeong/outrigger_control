"""Extract "write this in the judgement" directives from rule Markdown files.

A directive is a statement that the judgement document (판정서) must record
something. Two sources are recognised:

* Sections: a heading (level 2 or deeper) that says ``판정서에 적을 것``,
  ``판정서에 기록``, ``공개`` or ``사후 관찰``. Every list item, table row,
  blockquote line and plain line below it (until a heading of the same or a
  higher level) becomes one directive.
* Inline sentences elsewhere: a sentence that names ``판정서`` together with a
  recording verb (적는다, 기록, 요약, 남긴다, 싣는다/싣고, 보인다, 밝힌다,
  넣는다 ...) is a *strong*
  directive; a sentence that only says ``공개`` or ``사후 관찰`` is *weak*.
  A blockquote right after a strong inline sentence ("다음 문구를 적는다")
  becomes a strong directive too.
* Prediction lines (2026-11-16): a ``[참고] 사전 예측 P-n`` line anywhere is a
  strong directive (origin ``prediction``): the judgement must compare the
  prediction P-n with the result (원판 10절 "사전 예측 대조").

Each directive carries the key tokens a reader would search for in the
judgement: hash prefixes, item labels (R2-3, C-4, F-6), numbers, clock times,
code spans and quoted phrases. An inline sentence without tokens of its own
borrows them from its enclosing text, then (2026-11-16) from the list right
before it: "면제 사실과 대체 점검 결과는 판정서에 공개한다" refers to the
preceding sibling item and its sub-items (scope ``preceding``). Level-1
headings are document titles and never open a directive section. The
extraction errs on the side of extracting too much: an unclear item is later
reported as ``ambiguous``, not dropped.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from _files import read_text_facts
from _rules import RuleEdition, hash_edition, parse_seal_file, seal_path_for

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
STRONG_HEADING_PATTERNS = (
    re.compile(r"판정서에\s*(적을|적는|기록|남길)"),
    re.compile(r"판정서\s*기록"),
)
# Disclosure headings also hold procedure for later revisions, so their items
# are weak unless the item itself names the judgement.
WEAK_HEADING_PATTERNS = (re.compile(r"공개"), re.compile(r"사후\s*관찰"))
# Recording verbs after "판정서". 싣다/보이다/밝히다/넣다 were added 2026-11-15:
# "판정서에 표로 싣고", "판정서 표에 싣는다", "판정서에 … 같음을 보인다" were missed.
RECORDING_VERBS = (
    "적는|적을|적고|적어|적었|기록|요약|남긴|남기|쓴다"
    "|싣|실어|실을|실린|실었"
    "|보인다|보이고|보여|보일"
    "|밝힌|밝히|밝혀|밝힐"
    "|넣는|넣고|넣어|넣을"
    "|첨부"
    # "판정서에 공개한다" (added 2026-11-16; it was weak before).
    "|공개한|공개하|공개해|공개할"
)
# Applied per sentence, so a bounded gap is enough (file names hold dots).
STRONG_SENTENCE_PATTERN = re.compile(rf"판정서.{{0,80}}?({RECORDING_VERBS})")
WEAK_SENTENCE_PATTERN = re.compile(r"공개|사후\s*관찰")
LIST_ITEM_PATTERN = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$"
)
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")
SENTENCE_BREAK_PATTERN = re.compile(r"(?<=[.!?])\s+")
UNESCAPED_PIPE_PATTERN = re.compile(r"(?<!\\)\|")
# "[참고] 사전 예측 P-16:", "[참고] 사전 예측 P-16·P-17", "[참고] 사전 예측 P-3~P-5".
PREDICTION_PATTERN = re.compile(
    r"\[참고\]\s*사전\s*예측\s*(P-\d+(?:\s*[~·,/]\s*P-\d+)*)(?![\d])"
)
PREDICTION_LABEL_PATTERN = re.compile(r"P-(\d+)")
MAX_PREDICTION_RANGE = 30  # "P-1~P-15" expands; a longer range is a typo

CODE_SPAN_PATTERN = re.compile(r"`([^`]+)`")
QUOTE_PATTERNS = (
    re.compile(r'"([^"\n]{2,120})"'),
    re.compile(r"“([^”\n]{2,120})”"),
    re.compile(r"「([^」\n]{2,120})」"),
)
HEX_PATTERN = re.compile(r"(?<![0-9A-Za-z_])[0-9a-f]{7,64}(?![0-9A-Za-z_])")
# R2-3, C-4, F-6, P3-2, U-9, A-1 and D-b style item labels.
LABEL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_\-])([A-Z][A-Z0-9]{0,3}-\d+[a-z]?|[A-Z]\d?-[a-z])(?![A-Za-z0-9_])"
)
TIME_PATTERN = re.compile(r"(?<![\d:])(\d{1,2}:\d{2}(?::\d{2})?)(?![\d:])")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
DECIMAL_PATTERN = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w.]|\s*절)")
INTEGER_PATTERN = re.compile(r"(?<![\w.,])(\d{3,})(?![\w.,]|\s*절)")
# "원판 3.1", "설계서 1.2절": section references, not values.
SECTION_REFERENCE_WORDS = ("원판", "설계서", "논문", "명세", "rev1", "rev2", "rev3")
MIN_CODE_TOKEN_CHARS = 3
MIN_HASH_WITHOUT_BACKTICKS = 7  # short commit ids such as c012404
SHA_MENTION_PATTERN = re.compile(r"sha-?256", re.IGNORECASE)


class TokenKind(StrEnum):
    """What kind of evidence a token is."""

    HASH = "hash"
    EDITION_HASH = "edition_hash"
    LABEL = "label"
    NUMBER = "number"
    TIME = "time"
    CODE = "code"
    QUOTE = "quote"
    # A prediction label P-n on a judgement line that also names a verdict
    # (맞음, 틀림 ...): the comparison itself, not just a mention of P-n.
    PREDICTION = "prediction"


class Strength(StrEnum):
    """Strong directives can be reported missing; weak ones at most ambiguous."""

    STRONG = "strong"
    WEAK = "weak"


class Scope(StrEnum):
    """Where the tokens came from."""

    ITEM = "item"  # the whole section item
    SENTENCE = "sentence"  # the directive sentence itself
    CONTEXT = "context"  # the sentence had no token; the surrounding item did
    PRECEDING = "preceding"  # no token in the item; the list before it had some


@dataclass(frozen=True)
class Token:
    """One searchable key; ``candidates`` holds full hashes for edition hashes."""

    kind: TokenKind
    value: str
    candidates: tuple[str, ...] = ()


@dataclass
class Directive:
    """One extracted "record this in the judgement" item."""

    rule_path: Path
    line: int
    edition: str
    section: str
    unit: str  # list, table, quote, paragraph
    origin: str  # section or inline
    strength: Strength
    scope: Scope
    text: str
    tokens: list[Token] = field(default_factory=list)


@dataclass
class _Unit:
    """A list item, table cell set, blockquote line or plain line of a rule file."""

    line: int
    kind: str
    text: str
    cells: list[str] = field(default_factory=list)
    indent: int = 0  # leading spaces of a list item (nesting depth)


@dataclass
class _Section:
    level: int
    title: str
    strength: Strength | None  # None: not a directive section


# --- tokens ---------------------------------------------------------------------------


def _is_section_reference(text: str, start: int) -> bool:
    before = text[max(0, start - 6) : start].rstrip()
    return before.endswith(SECTION_REFERENCE_WORDS)


def _has_digit_and_letter(text: str) -> bool:
    return any(c.isdigit() for c in text) and any(c in "abcdef" for c in text)


def _code_tokens(code: str) -> list[Token]:
    """A code span is a hash, a skipped template/generic name, or a code token."""
    stripped = code.strip().rstrip("…").rstrip("*").strip()
    if HEX_PATTERN.fullmatch(stripped) and _has_digit_and_letter(stripped):
        return [Token(TokenKind.HASH, stripped)]
    is_template = "<" in stripped or ">" in stripped
    is_generic = stripped.startswith(".") or len(stripped) < MIN_CODE_TOKEN_CHARS
    if is_template or is_generic:
        return []
    return [Token(TokenKind.CODE, stripped)]


def _plain_tokens(text: str) -> list[Token]:
    """Hashes, labels, times and numbers from text without code spans or quotes."""
    tokens: list[Token] = []
    for match in HEX_PATTERN.finditer(text):
        value = match.group(0)
        if len(value) >= MIN_HASH_WITHOUT_BACKTICKS and _has_digit_and_letter(value):
            tokens.append(Token(TokenKind.HASH, value))
    without_hex = HEX_PATTERN.sub(" ", text)
    tokens += [
        Token(TokenKind.LABEL, m.group(1)) for m in LABEL_PATTERN.finditer(without_hex)
    ]
    tokens += [
        Token(TokenKind.TIME, m.group(1)) for m in TIME_PATTERN.finditer(without_hex)
    ]
    numeric_text = TIME_PATTERN.sub(
        " ", DATE_PATTERN.sub(" ", LABEL_PATTERN.sub(" ", without_hex))
    )
    for pattern in (DECIMAL_PATTERN, INTEGER_PATTERN):
        for match in pattern.finditer(numeric_text):
            if not _is_section_reference(numeric_text, match.start()):
                tokens.append(Token(TokenKind.NUMBER, match.group(1)))
    return tokens


def extract_tokens(text: str) -> list[Token]:
    """Return the distinct key tokens of ``text`` in order of appearance."""
    clean = text.replace("**", "")
    tokens: list[Token] = []
    for match in CODE_SPAN_PATTERN.finditer(clean):
        tokens += _code_tokens(match.group(1))
    without_code = CODE_SPAN_PATTERN.sub(" ", clean)
    for pattern in QUOTE_PATTERNS:
        tokens += [
            Token(TokenKind.QUOTE, m.group(1).strip())
            for m in pattern.finditer(without_code)
        ]
        without_code = pattern.sub(" ", without_code)
    tokens += _plain_tokens(without_code)
    distinct: list[Token] = []
    for token in tokens:
        if token not in distinct:
            distinct.append(token)
    return distinct


def _edition_hash_tokens(
    editions: list[RuleEdition], current: RuleEdition
) -> list[Token]:
    """Hashes of the family's editions up to ``current`` (seal, raw and LF)."""
    tokens: list[Token] = []
    for edition in editions:
        if edition.family != current.family:
            continue
        if (edition.number, edition.suffix) > (current.number, current.suffix):
            continue
        hashes = hash_edition(edition.path)
        candidates = {hashes.raw, hashes.lf}
        seal_path = seal_path_for(edition, None)
        if seal_path.is_file():
            seal = parse_seal_file(seal_path)
            if seal.is_well_formed:
                candidates.add(seal.first_token.lower())
        tokens.append(
            Token(
                TokenKind.EDITION_HASH,
                f"{edition.label} sha256",
                tuple(sorted(candidates)),
            )
        )
    return tokens


# --- Markdown units --------------------------------------------------------------------


def _table_cells(line: str) -> list[str]:
    body = line.strip()
    body = body.removeprefix("|").removesuffix("|")
    return [
        cell.strip().replace("\\|", "|") for cell in UNESCAPED_PIPE_PATTERN.split(body)
    ]


def _is_table_header(lines: list[str], index: int) -> bool:
    next_index = index + 1
    return next_index < len(lines) and bool(
        TABLE_SEPARATOR_PATTERN.match(lines[next_index])
    )


def _units_of(lines: list[str]) -> list[tuple[_Unit, int]]:
    """Split body lines into units, each paired with the index of its heading line.

    Fenced code blocks, table headers and separators are skipped. Indented
    lines without a list marker continue the previous list item.
    """
    units: list[tuple[_Unit, int]] = []
    pending: _Unit | None = None
    heading_index = -1
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if pending is not None and _continues_list_item(pending, line):
            pending.text += " " + line.strip()
            continue
        if pending is not None:
            units.append((pending, heading_index))
            pending = None
        if HEADING_PATTERN.match(line):
            heading_index = index
            continue
        unit = _unit_for_line(lines, index)
        if unit is not None and unit.kind == "list":
            pending = unit  # may continue on the next indented lines
        elif unit is not None:
            units.append((unit, heading_index))
    if pending is not None:
        units.append((pending, heading_index))
    return units


def _continues_list_item(pending: _Unit, line: str) -> bool:
    stripped = line.strip()
    return (
        pending.kind == "list"
        and bool(stripped)
        and line[:1].isspace()
        and not LIST_ITEM_PATTERN.match(line)
        and not stripped.startswith(("|", ">"))
    )


def _unit_for_line(lines: list[str], index: int) -> _Unit | None:
    """The unit a non-heading line starts; ``None`` for blank, separator or header lines."""
    line = lines[index]
    stripped = line.strip()
    if not stripped or (TABLE_SEPARATOR_PATTERN.match(line) and "-" in stripped):
        return None
    list_match = LIST_ITEM_PATTERN.match(line)
    if list_match:
        indent = len(list_match.group(1).expandtabs(4))
        return _Unit(index + 1, "list", list_match.group(2).strip(), indent=indent)
    if stripped.startswith("|"):
        if _is_table_header(lines, index):
            return None
        return _Unit(index + 1, "table", stripped, _table_cells(stripped))
    if stripped.startswith(">"):
        text = stripped.lstrip(">").strip()
        return _Unit(index + 1, "quote", text) if text else None
    return _Unit(index + 1, "paragraph", stripped)


def _sections_by_heading(lines: list[str]) -> dict[int, list[_Section]]:
    """Heading line index -> the stack of open sections at that heading."""
    stacks: dict[int, list[_Section]] = {-1: []}
    stack: list[_Section] = []
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
        match = None if in_fence else HEADING_PATTERN.match(line)
        if match is None:
            continue
        level, title = len(match.group(1)), match.group(2)
        while stack and stack[-1].level >= level:
            stack.pop()
        stack.append(_Section(level, title, _heading_strength(level, title)))
        stacks[index] = list(stack)
    return stacks


def _heading_strength(level: int, title: str) -> Strength | None:
    """Level-1 headings are document titles and never open a directive section."""
    if level < 2:
        return None
    if any(pattern.search(title) for pattern in STRONG_HEADING_PATTERNS):
        return Strength.STRONG
    if any(pattern.search(title) for pattern in WEAK_HEADING_PATTERNS):
        return Strength.WEAK
    return None


def _section_strength(stack: list[_Section]) -> Strength | None:
    """The strongest directive heading among the open sections."""
    strengths = {section.strength for section in stack}
    if Strength.STRONG in strengths:
        return Strength.STRONG
    return Strength.WEAK if Strength.WEAK in strengths else None


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_BREAK_PATTERN.split(text) if part.strip()]


def _unit_texts(unit: _Unit) -> list[str]:
    """Table rows are searched cell by cell; other units as a whole."""
    return (
        [cell for cell in unit.cells if cell] if unit.kind == "table" else [unit.text]
    )


# --- directives ------------------------------------------------------------------------


def _inline_directives(unit: _Unit) -> list[tuple[str, str, Strength]]:
    """``(sentence, enclosing text, strength)`` for directive sentences in ``unit``."""
    found: list[tuple[str, str, Strength]] = []
    for text in _unit_texts(unit):
        for sentence in _sentences(text):
            if STRONG_SENTENCE_PATTERN.search(sentence):
                found.append((sentence, text, Strength.STRONG))
            elif WEAK_SENTENCE_PATTERN.search(sentence):
                found.append((sentence, text, Strength.WEAK))
    return found


def _make_directive(
    edition: RuleEdition,
    unit: _Unit,
    section: str,
    origin: str,
    strength: Strength,
    text: str,
    fallbacks: Sequence[tuple[str, Scope]] = (),
) -> Directive:
    """A directive with the tokens of ``text``, else of the first fallback having any."""
    tokens = extract_tokens(text)
    scope = Scope.ITEM if origin == "section" else Scope.SENTENCE
    for fallback_text, fallback_scope in fallbacks:
        if tokens:
            break
        tokens = extract_tokens(fallback_text)
        scope = fallback_scope if tokens else scope
    return Directive(
        edition.path,
        unit.line,
        edition.label,
        section,
        unit.kind,
        origin,
        strength,
        scope,
        text,
        tokens,
    )


def _add_edition_hashes(
    directive: Directive, editions: list[RuleEdition], edition: RuleEdition
) -> None:
    if directive.origin == "prediction":
        return  # "sha256이 같다" in a prediction is the predicted fact, not a seal
    has_explicit_hash = any(token.kind is TokenKind.HASH for token in directive.tokens)
    if SHA_MENTION_PATTERN.search(directive.text) and not has_explicit_hash:
        directive.tokens += _edition_hash_tokens(editions, edition)
        if directive.scope in (Scope.CONTEXT, Scope.PRECEDING):
            directive.scope = Scope.SENTENCE


def _preceding_list_text(
    previous: list[tuple[_Unit, int]], unit: _Unit, heading_index: int
) -> str | None:
    """Text of the list right before ``unit`` in the same section, or ``None``.

    A list item borrows from its preceding sibling item and that item's
    sub-items ("면제 사실과 대체 점검 결과는 판정서에 공개한다" after the item
    that lists the checks); a paragraph borrows from the whole list above it.
    """
    if unit.kind not in ("list", "paragraph"):
        return None
    borrowed: list[_Unit] = []
    for earlier, earlier_heading in reversed(previous):
        if earlier_heading != heading_index or earlier.kind != "list":
            break
        if unit.kind == "list" and earlier.indent < unit.indent:
            break  # reached the parent item: there is no preceding sibling
        borrowed.append(earlier)
        if unit.kind == "list" and earlier.indent == unit.indent:
            break  # the preceding sibling closes the borrowed range
    if not borrowed:
        return None
    return " ".join(item.text for item in reversed(borrowed))


def _prediction_labels(text: str) -> list[str]:
    """``P-n`` labels of a ``[참고] 사전 예측 P-n`` line (ranges expanded), else []."""
    match = PREDICTION_PATTERN.search(text.replace("**", ""))
    if match is None:
        return []
    listed = match.group(1)
    numbers = [int(number) for number in PREDICTION_LABEL_PATTERN.findall(listed)]
    is_range = "~" in listed and len(numbers) == 2
    if is_range and 0 < numbers[1] - numbers[0] <= MAX_PREDICTION_RANGE:
        numbers = list(range(numbers[0], numbers[1] + 1))
    return [f"P-{number}" for number in dict.fromkeys(numbers)]


def _prediction_directive(
    edition: RuleEdition, unit: _Unit, section: str, labels: list[str]
) -> Directive:
    """The judgement must compare each prediction with the result (원판 10절)."""
    tokens: list[Token] = []
    for label in labels:
        tokens += [Token(TokenKind.LABEL, label), Token(TokenKind.PREDICTION, label)]
    return Directive(
        edition.path,
        unit.line,
        edition.label,
        section,
        unit.kind,
        "prediction",
        Strength.STRONG,
        Scope.ITEM,
        unit.text,
        tokens,
    )


def extract_directives(
    edition: RuleEdition, editions: list[RuleEdition]
) -> list[Directive]:
    """Return every directive of one rule edition in file order.

    Args:
        edition: The rule file to read.
        editions: All editions given to the tool (for ``sha256`` items).
    """
    lines = read_text_facts(edition.path).text.splitlines()
    sections = _sections_by_heading(lines)
    directives: list[Directive] = []
    previous: list[tuple[_Unit, int]] = []
    follows_strong = False  # a quote right after a strong directive is the wording
    for unit, heading_index in _units_of(lines):
        stack = sections.get(heading_index, [])
        section_title = stack[-1].title if stack else ""
        section_strength = _section_strength(stack)
        preceding = _preceding_list_text(previous, unit, heading_index)
        previous.append((unit, heading_index))
        prediction_labels = _prediction_labels(unit.text)
        if prediction_labels:
            directives.append(
                _prediction_directive(edition, unit, section_title, prediction_labels)
            )
            follows_strong = False
            continue
        if unit.kind == "quote" and follows_strong:
            directives.append(
                _make_directive(
                    edition,
                    unit,
                    section_title,
                    "section" if section_strength else "inline",
                    Strength.STRONG,
                    unit.text,
                )
            )
            continue
        inline = _inline_directives(unit)
        names_judgement = any(item[2] is Strength.STRONG for item in inline)
        if section_strength is not None:
            strength = Strength.STRONG if names_judgement else section_strength
            directives.append(
                _make_directive(
                    edition, unit, section_title, "section", strength, unit.text
                )
            )
            follows_strong = strength is Strength.STRONG
            continue
        for sentence, context, strength in inline:
            fallbacks = [(context, Scope.CONTEXT)]
            if preceding is not None:
                fallbacks.append((preceding, Scope.PRECEDING))
            directives.append(
                _make_directive(
                    edition,
                    unit,
                    section_title,
                    "inline",
                    strength,
                    sentence,
                    fallbacks,
                )
            )
        follows_strong = names_judgement
    for directive in directives:
        _add_edition_hashes(directive, editions, edition)
    return directives
