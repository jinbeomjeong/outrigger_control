"""Parse checksum list files such as ``SHA256SUMS``.

Accepted line forms (one entry per line, blank lines and ``#`` comments skipped):

* GNU ``sha256sum``: ``<64 hex>  <name>`` or ``<64 hex> *<name>`` (binary marker);
* BSD ``shasum --tag``: ``SHA256 (<name>) = <64 hex>``.

A CRLF line end is removed before parsing and counted, so a list committed with
``-text`` from a Windows checkout still parses; the count is reported because a
plain ``split()`` reader keeps the ``\\r`` in the last file name.

Entry names are resolved against the list's own folder unless ``entry_base``
names another folder (``baseline_check sums --base repo-root``, 2026-11-21).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _cli import InputError
from _files import decode_bytes

GNU_LINE_PATTERN = re.compile(r"^(?P<hash>[0-9A-Fa-f]{64}) (?P<mode>[ *])(?P<name>.+)$")
BSD_LINE_PATTERN = re.compile(
    r"^SHA256 \((?P<name>.+)\) = (?P<hash>[0-9A-Fa-f]{64})$", re.IGNORECASE
)
COMMENT_PREFIX = "#"
UTF8_BOM = b"\xef\xbb\xbf"
MAX_SHOWN_CHARS = 80


@dataclass(frozen=True)
class SumsEntry:
    """One listed file: its digest, the name as written and the resolved path."""

    line: int
    digest: str
    name: str
    path: Path

    @property
    def posix_name(self) -> str:
        return self.name.replace("\\", "/")


@dataclass
class SumsFile:
    """A parsed checksum list and its line-ending facts."""

    path: Path
    entries: list[SumsEntry] = field(default_factory=list)
    malformed_lines: list[tuple[int, str]] = field(default_factory=list)
    crlf_lines: int = 0
    lone_lf_lines: int = 0
    has_bom: bool = False
    entry_base: Path | None = None

    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def resolve_base(self) -> Path:
        """Folder the entry names are relative to (default: the list's folder)."""
        return self.entry_base if self.entry_base is not None else self.folder


def resolve_entry_name(base: Path, name: str) -> Path:
    """Absolute path of a listed name below ``base`` (``\\`` read as ``/``)."""
    return (base / name.replace("\\", "/")).resolve()


def _parse_line(text: str) -> tuple[str, str] | None:
    """Return ``(digest, name)`` of one line, or ``None`` when it is not an entry."""
    for pattern in (GNU_LINE_PATTERN, BSD_LINE_PATTERN):
        match = pattern.match(text)
        if match:
            return match.group("hash").lower(), match.group("name")
    return None


def parse_sums_file(path: Path, entry_base: Path | None = None) -> SumsFile:
    """Read and parse a checksum list; malformed lines are kept, not raised.

    Args:
        path: The list file.
        entry_base: Folder the entry names are relative to; ``None`` = the
            list's own folder.

    Raises:
        InputError: If the file cannot be read.
    """
    try:
        data = path.read_bytes()
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    text, _ = decode_bytes(data)
    sums = SumsFile(path, has_bom=data.startswith(UTF8_BOM), entry_base=entry_base)
    newline_count = text.count("\n")
    for number, raw_line in enumerate(text.split("\n"), start=1):
        if number <= newline_count:  # the part after the last "\n" has no line end
            _count_line_end(sums, raw_line)
        _add_line(sums, number, raw_line.rstrip())
    return sums


def _count_line_end(sums: SumsFile, raw_line: str) -> None:
    if raw_line.endswith("\r"):
        sums.crlf_lines += 1
    else:
        sums.lone_lf_lines += 1


def _add_line(sums: SumsFile, number: int, line: str) -> None:
    """Parse one line (``\\r`` and trailing blanks already removed) into ``sums``."""
    stripped = line.strip()
    if not stripped or stripped.startswith(COMMENT_PREFIX):
        return
    parsed = _parse_line(line)
    if parsed is None:
        sums.malformed_lines.append((number, stripped[:MAX_SHOWN_CHARS]))
        return
    digest, name = parsed
    resolved = resolve_entry_name(sums.resolve_base, name)
    sums.entries.append(SumsEntry(number, digest, name, resolved))
