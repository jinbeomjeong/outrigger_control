"""Build line-range index files for large Markdown documents.

Agents should not read a 1 MB specification in full. This script writes a
``<stem>_index.md`` next to each source document that lists every heading
(down to ``--depth``) with its start line, end line, line count, size and first
body sentence, so an agent can pass ``offset=start`` and ``limit=line count``
to its Read tool. Sections longer than ``--split-lines`` get extra rows for the
bold paragraph heads and tables inside them. A revision summary is copied in
front of the index when the document preamble has one.

Usage:
    python -I 04_scripts/00_docs/build_doc_index.py [md files ...] [--depth 4]
        [--split-lines 400]

Without file arguments, the two large specifications plus every
``00_docs/**/*.md`` over 100 KB (excluding ``history``/``drafts`` folders and
``*_index.md``/``*_current.md``) are indexed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "00_docs"
DEFAULT_DOCS = (
    DOCS_DIR / "04_control" / "s6_control_spec.md",
    DOCS_DIR / "01_dynamics" / "dynamics_model.md",
)
LARGE_DOC_MIN_BYTES = 100 * 1024
EXCLUDED_DIR_NAMES = frozenset({"history", "drafts"})
EXCLUDED_NAME_SUFFIXES = ("_index.md", "_current.md")
INDEX_SUFFIX = "_index.md"

DEFAULT_DEPTH = 4
DEFAULT_SPLIT_LINES = 400
TITLE_MAX_CHARS = 80
SENTENCE_MAX_CHARS = 100
# Anchors closer than this to the previous kept anchor are merged into it, so a
# long table-heavy section does not explode into one row per table.
MIN_SPLIT_CHUNK_DIVISOR = 10
MIN_SPLIT_CHUNK_LINES = 10
BYTES_PER_KB = 1024

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?(?=\s|$|\()")
REVISION_NUMBER_PATTERN = re.compile(r"^개정\s*(\d+)")
FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
# A bold paragraph head, optionally as an unindented list item ("- **개정 32 보완 4**: ...").
BOLD_HEAD_PATTERN = re.compile(r"^(?:[-*]\s+)?\*\*(.+?)\*\*")
SENTENCE_END_PATTERN = re.compile(r"[.!?。](?=\s|$)")
LIST_MARKER_PATTERN = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
REVISION_TABLE_HEADER_PATTERN = re.compile(r"^\|\s*개정\s*\|\s*날짜\s*\|")
REVISION_PARAGRAPH_PATTERN = re.compile(
    r"^개정\s*(\d+)\s*\(\s*(\d{4}-\d{2}-\d{2})[^*]*\*\*(.+?)\*\*"
)
SECTION_REF_PATTERN = re.compile(r"\d+(?:\.\d+)+(?:\s*~\s*\d+(?:\.\d+)*)?")
SECTION_RANGE_PART_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)(?:\s*~\s*(\d+(?:\.\d+)*))?$")


@dataclass(frozen=True)
class SourceDocument:
    """A Markdown file split into lines, with per-line byte sizes."""

    path: Path
    lines: list[str]
    line_bytes: list[int]
    sha256: str

    @property
    def total_bytes(self) -> int:
        return sum(self.line_bytes)


@dataclass(frozen=True)
class Heading:
    """A Markdown heading outside code fences and math blocks (1-based line)."""

    level: int
    line: int
    title: str


@dataclass(frozen=True)
class IndexEntry:
    """One index row: a heading or a split anchor inside a long section."""

    kind: str
    number: str
    title: str
    start_line: int
    end_line: int
    first_sentence: str

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


# --------------------------------------------------------------------------- reading


def load_document(path: Path) -> SourceDocument:
    """Read a Markdown file so that line numbers match the Read tool (``\\n`` split)."""
    raw = path.read_bytes()
    chunks = raw.split(b"\n")
    if chunks and chunks[-1] == b"":
        chunks.pop()
    line_bytes = [len(chunk) + 1 for chunk in chunks]
    if not raw.endswith(b"\n") and line_bytes:
        line_bytes[-1] -= 1
    lines = [chunk.decode("utf-8").rstrip("\r") for chunk in chunks]
    if lines and lines[0].startswith("﻿"):
        lines[0] = lines[0][1:]
    return SourceDocument(
        path=path,
        lines=lines,
        line_bytes=line_bytes,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _is_math_delimiter(stripped: str) -> bool:
    """True if a ``$$`` line opens a block (``$$ x $$`` on one line does not)."""
    return stripped.startswith("$$") and stripped.count("$$") % 2 == 1


def mark_block_lines(lines: Sequence[str]) -> list[bool]:
    """Flag lines that belong to a code fence or a ``$$`` math block, delimiters included."""
    is_block = [False] * len(lines)
    open_fence = ""
    is_in_math = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        fence_match = FENCE_PATTERN.match(line)
        if open_fence:
            is_block[i] = True
            is_closing = fence_match and fence_match.group(1)[0] == open_fence[0]
            if is_closing and len(fence_match.group(1)) >= len(open_fence):
                open_fence = ""
            continue
        if fence_match and not is_in_math:
            open_fence = fence_match.group(1)
            is_block[i] = True
            continue
        if is_in_math:
            # A block such as "$$J = ...\n...\end{bmatrix}$$" closes mid-line.
            is_block[i] = True
            is_in_math = stripped.count("$$") % 2 == 0
            continue
        if stripped.startswith("$$"):
            is_block[i] = True
            is_in_math = _is_math_delimiter(stripped)
    return is_block


def find_headings(lines: Sequence[str], is_block: Sequence[bool], max_level: int) -> list[Heading]:
    """Return headings up to ``max_level``, skipping code fences and math blocks."""
    headings = []
    for i, line in enumerate(lines):
        if is_block[i]:
            continue
        match = HEADING_PATTERN.match(line)
        if match and len(match.group(1)) <= max_level:
            headings.append(Heading(level=len(match.group(1)), line=i + 1, title=match.group(2)))
    return headings


def extract_section_number(title: str) -> str:
    """Section number from a heading title: ``3.9.7``, ``0``, ``개정 12`` or ``""``."""
    match = SECTION_NUMBER_PATTERN.match(title)
    if match:
        return match.group(1)
    match = REVISION_NUMBER_PATTERN.match(title)
    if match:
        return f"개정 {match.group(1)}"
    return ""


def strip_section_number(title: str) -> str:
    """Title without its leading numeric section number (already in the number column)."""
    match = SECTION_NUMBER_PATTERN.match(title)
    if not match:
        return title
    return title[match.end() :].lstrip(". ") or title


# --------------------------------------------------------------------------- text helpers


def truncate(text: str, max_chars: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _is_skippable_line(stripped: str) -> bool:
    """Tables, images and HTML comments are not prose for the first-sentence column."""
    return stripped.startswith(("|", "![", "<!--"))


def _clean_prose_line(stripped: str) -> str:
    text = stripped
    while text.startswith(">"):
        text = text[1:].lstrip()
    text = LIST_MARKER_PATTERN.sub("", text)
    return text.replace("**", "")


def first_sentence(lines: Sequence[str], is_block: Sequence[bool], start: int, stop: int) -> str:
    """First sentence of the first prose paragraph in 0-based lines ``[start, stop)``."""
    paragraph: list[str] = []
    for i in range(start, stop):
        stripped = lines[i].strip()
        is_prose = bool(stripped) and not is_block[i] and not _is_skippable_line(stripped)
        if is_prose and HEADING_PATTERN.match(lines[i]):
            break
        if is_prose:
            paragraph.append(_clean_prose_line(stripped))
        elif paragraph:
            break
    return leading_sentence(" ".join(paragraph))


def leading_sentence(text: str) -> str:
    """First sentence of ``text`` (ends at ``.``/``!``/``?`` before whitespace), truncated."""
    text = " ".join(text.split())
    end_match = SENTENCE_END_PATTERN.search(text)
    sentence = text[: end_match.end()] if end_match else text
    return truncate(sentence, SENTENCE_MAX_CHARS)


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


# --------------------------------------------------------------------------- entries


def _section_end_lines(headings: Sequence[Heading], total_lines: int) -> list[int]:
    """Last line of each section: the line before the next heading of the same or higher level."""
    end_lines = []
    for position, heading in enumerate(headings):
        end_line = total_lines
        for later in headings[position + 1 :]:
            if later.level <= heading.level:
                end_line = later.line - 1
                break
        end_lines.append(end_line)
    return end_lines


def _is_split_anchor(lines: Sequence[str], i: int) -> bool:
    """Bold paragraph head, table start, or a heading deeper than ``--depth``."""
    line = lines[i]
    is_table_start = line.startswith("|") and not lines[i - 1].startswith("|")
    return bool(BOLD_HEAD_PATTERN.match(line) or HEADING_PATTERN.match(line) or is_table_start)


def _split_anchor_lines(
    lines: Sequence[str], is_block: Sequence[bool], body_start: int, body_end: int, min_gap: int
) -> list[int]:
    """0-based split anchors in ``[body_start, body_end)``, at least ``min_gap`` lines apart."""
    anchors = []
    last_kept = body_start - 1
    for i in range(body_start, body_end):
        if is_block[i] or i - last_kept < min_gap:
            continue
        if _is_split_anchor(lines, i):
            anchors.append(i)
            last_kept = i
    return anchors


def _anchor_entry(
    lines: Sequence[str], is_block: Sequence[bool], anchor: int, end: int, number: str
) -> IndexEntry:
    """Index row for a split anchor (0-based ``anchor``, exclusive 0-based ``end``)."""
    line = lines[anchor]
    heading_match = HEADING_PATTERN.match(line)
    bold_match = BOLD_HEAD_PATTERN.match(line)
    if heading_match:
        kind = "+" + heading_match.group(1)
        number = extract_section_number(heading_match.group(2)) or number
        title = strip_section_number(heading_match.group(2))
        sentence = first_sentence(lines, is_block, anchor + 1, end)
    elif bold_match:
        kind = "+단락"
        title = bold_match.group(1)
        remainder = _clean_prose_line(line[bold_match.end() :].strip(" :："))
        sentence = leading_sentence(remainder) or first_sentence(lines, is_block, anchor + 1, end)
    else:
        kind = "+표"
        header_cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        title = "표: " + " / ".join(cell for cell in header_cells if cell)
        sentence = ""
    return IndexEntry(
        kind=kind,
        number=number,
        title=truncate(title.replace("**", ""), TITLE_MAX_CHARS),
        start_line=anchor + 1,
        end_line=end,
        first_sentence=truncate(sentence, SENTENCE_MAX_CHARS),
    )


def _split_entries(
    lines: Sequence[str],
    is_block: Sequence[bool],
    heading: Heading,
    body_end_line: int,
    number: str,
    split_lines: int,
) -> list[IndexEntry]:
    """Extra rows for a section whose own body (up to the next heading) exceeds ``split_lines``."""
    if body_end_line - heading.line + 1 <= split_lines:
        return []
    min_gap = max(MIN_SPLIT_CHUNK_LINES, split_lines // MIN_SPLIT_CHUNK_DIVISOR)
    anchors = _split_anchor_lines(lines, is_block, heading.line, body_end_line, min_gap)
    entries = []
    for position, anchor in enumerate(anchors):
        is_last = position + 1 == len(anchors)
        end = body_end_line if is_last else anchors[position + 1]
        entries.append(_anchor_entry(lines, is_block, anchor, end, number))
    return entries


def build_entries(document: SourceDocument, depth: int, split_lines: int) -> list[IndexEntry]:
    """Heading rows (plus split rows for long sections) in document order."""
    lines = document.lines
    is_block = mark_block_lines(lines)
    headings = find_headings(lines, is_block, depth)
    end_lines = _section_end_lines(headings, len(lines))
    entries = []
    for position, (heading, end_line) in enumerate(zip(headings, end_lines, strict=True)):
        is_last = position + 1 == len(headings)
        body_end_line = len(lines) if is_last else headings[position + 1].line - 1
        number = extract_section_number(heading.title)
        entries.append(
            IndexEntry(
                kind="#" * heading.level,
                number=number,
                title=truncate(strip_section_number(heading.title), TITLE_MAX_CHARS),
                start_line=heading.line,
                end_line=end_line,
                first_sentence=first_sentence(lines, is_block, heading.line, body_end_line),
            )
        )
        entries.extend(_split_entries(lines, is_block, heading, body_end_line, number, split_lines))
    return entries


# --------------------------------------------------------------------------- revisions


def _preamble_end(lines: Sequence[str], is_block: Sequence[bool]) -> int:
    """0-based index of the first level-2 heading (the preamble ends there)."""
    for heading in find_headings(lines, is_block, 2):
        if heading.level == 2:
            return heading.line - 1
    return len(lines)


def _span_for_section_ref(ref: str, entries_by_number: dict[str, IndexEntry]) -> str:
    """Turn ``"10~11, 284.1"`` into line spans such as ``"423–523, 9001–9050"``."""
    spans = []
    for part in re.split(r"[,·]", ref):
        match = SECTION_RANGE_PART_PATTERN.match(part.strip())
        if not match:
            continue
        first = entries_by_number.get(match.group(1))
        last = entries_by_number.get(match.group(2) or match.group(1))
        if first and last:
            spans.append(f"{first.start_line}–{last.end_line}")
    return ", ".join(spans)


def _number_lookup(entries: Iterable[IndexEntry]) -> dict[str, IndexEntry]:
    """Heading rows by section number; numbers used more than once are left out."""
    lookup: dict[str, IndexEntry] = {}
    duplicates = set()
    for entry in entries:
        if not entry.number or entry.kind.startswith("+"):
            continue
        if entry.number in lookup:
            duplicates.add(entry.number)
        lookup[entry.number] = entry
    for number in duplicates:
        del lookup[number]
    return lookup


def _revision_table_rows(lines: Sequence[str], preamble_end: int) -> list[str]:
    """Copy of the ``| 개정 | 날짜 | ...`` table in the preamble, or ``[]``."""
    for i in range(preamble_end):
        if REVISION_TABLE_HEADER_PATTERN.match(lines[i]):
            rows = []
            for line in lines[i:preamble_end]:
                if not line.startswith("|"):
                    break
                rows.append(line)
            return rows
    return []


def _with_line_column(table_rows: Sequence[str], lookup: dict[str, IndexEntry]) -> list[str]:
    """Append a "줄" column resolved from the last ("절") column of a revision table."""
    if len(table_rows) < 2:
        return list(table_rows)
    result = [table_rows[0].rstrip() + " 줄 |", table_rows[1].rstrip() + "---|"]
    for row in table_rows[2:]:
        cells = row.strip().strip("|").split("|")
        span = _span_for_section_ref(cells[-1].strip(), lookup)
        result.append(f"{row.rstrip()} {span} |")
    return result


def _revision_paragraph_rows(
    lines: Sequence[str], preamble_end: int, lookup: dict[str, IndexEntry]
) -> list[str]:
    """Summary table built from ``개정 N(YYYY-MM-DD, **title**...)`` preamble paragraphs."""
    rows = []
    for line in lines[:preamble_end]:
        match = REVISION_PARAGRAPH_PATTERN.match(line)
        if not match:
            continue
        number, date, bold_title = match.groups()
        section_refs = ", ".join(SECTION_REF_PATTERN.findall(bold_title))
        span = _span_for_section_ref(section_refs, lookup)
        title = escape_cell(truncate(bold_title, TITLE_MAX_CHARS))
        rows.append(f"| {number} | {date} | {title} | {section_refs} | {span} |")
    if not rows:
        return []
    return ["| 개정 | 날짜 | 제목(굵은 글씨 요약) | 절 | 줄 |", "|---|---|---|---|---|", *rows]


def build_revision_summary(document: SourceDocument, entries: Sequence[IndexEntry]) -> list[str]:
    """Revision table lines from the preamble (copied table or parsed paragraphs)."""
    is_block = mark_block_lines(document.lines)
    preamble_end = _preamble_end(document.lines, is_block)
    lookup = _number_lookup(entries)
    table_rows = _revision_table_rows(document.lines, preamble_end)
    if table_rows:
        return _with_line_column(table_rows, lookup)
    return _revision_paragraph_rows(document.lines, preamble_end, lookup)


# --------------------------------------------------------------------------- rendering


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _entry_row(entry: IndexEntry, document: SourceDocument) -> str:
    size_bytes = sum(document.line_bytes[entry.start_line - 1 : entry.end_line])
    cells = [
        entry.kind,
        entry.number,
        escape_cell(entry.title),
        str(entry.start_line),
        str(entry.end_line),
        str(entry.line_count),
        f"{size_bytes / BYTES_PER_KB:.1f}",
        escape_cell(entry.first_sentence),
    ]
    return "| " + " | ".join(cells) + " |"


def render_index(
    document: SourceDocument,
    entries: Sequence[IndexEntry],
    revision_rows: Sequence[str],
    depth: int,
    split_lines: int,
    generated_at: datetime,
) -> str:
    """Full Markdown text of the index file."""
    source = display_path(document.path)
    out = [
        f"# 색인: {document.path.name}",
        "",
        f"- 원본: `{source}`",
        f"- 원본 SHA-256(앞 12자): `{document.sha256[:12]}`",
        f"- 생성: {generated_at:%Y-%m-%d %H:%M:%S} "
        f"(`04_scripts/00_docs/build_doc_index.py`, depth {depth}, split-lines {split_lines})",
        f"- 총 줄 수: {len(document.lines):,} ({document.total_bytes / BYTES_PER_KB:,.1f} KB)",
        "- 사용법: Read에 offset=시작 줄, limit=줄 수. "
        "끝 줄은 하위 절을 포함한다. `+단락`·`+표`는 긴 절 안의 위치 안내다. "
        "원본 SHA가 다르면 색인을 다시 만든다.",
        "",
    ]
    if revision_rows:
        out += ["## 개정 → 절 범위", "", *revision_rows, ""]
    out += [
        "## 절 색인",
        "",
        "| 수준 | 번호 | 제목 | 시작 줄 | 끝 줄 | 줄 수 | KB | 첫 문장 |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    out += [_entry_row(entry, document) for entry in entries]
    return "\n".join(out) + "\n"


def index_path_for(source: Path) -> Path:
    return source.with_name(f"{source.stem}{INDEX_SUFFIX}")


def write_index(source: Path, depth: int, split_lines: int) -> Path:
    """Build and write ``<stem>_index.md`` next to ``source``; return its path."""
    document = load_document(source)
    entries = build_entries(document, depth, split_lines)
    revision_rows = build_revision_summary(document, entries)
    text = render_index(document, entries, revision_rows, depth, split_lines, datetime.now())
    target = index_path_for(source)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


# --------------------------------------------------------------------------- discovery


def _is_excluded(path: Path) -> bool:
    relative_parts = path.relative_to(DOCS_DIR).parts[:-1]
    if EXCLUDED_DIR_NAMES.intersection(relative_parts):
        return True
    return path.name.endswith(EXCLUDED_NAME_SUFFIXES)


def default_sources() -> list[Path]:
    """The two large specifications plus every non-excluded ``00_docs`` page over 100 KB."""
    sources = {path.resolve() for path in DEFAULT_DOCS}
    for path in DOCS_DIR.rglob("*.md"):
        if not _is_excluded(path) and path.stat().st_size > LARGE_DOC_MIN_BYTES:
            sources.add(path.resolve())
    return sorted(sources)


# --------------------------------------------------------------------------- CLI


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="*", type=Path, help="Markdown files to index")
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        choices=range(1, 7),
        metavar="1-6",
        help=f"deepest heading level to list (default {DEFAULT_DEPTH})",
    )
    parser.add_argument(
        "--split-lines",
        type=int,
        default=DEFAULT_SPLIT_LINES,
        help="split sections whose own body is longer than this many lines "
        f"(default {DEFAULT_SPLIT_LINES})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    sources = args.sources or default_sources()
    for source in sources:
        target = write_index(source, args.depth, args.split_lines)
        source_bytes = source.stat().st_size
        index_bytes = target.stat().st_size
        print(
            f"{display_path(target)}: {index_bytes / BYTES_PER_KB:,.1f} KB "
            f"/ source {source_bytes / BYTES_PER_KB:,.1f} KB "
            f"= {index_bytes / source_bytes:.1%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
