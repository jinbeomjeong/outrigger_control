"""File discovery, byte-level text facts and the ``--out`` location guard.

Shared by the verif tools; nothing here writes to disk.
"""

from __future__ import annotations

import glob
import os
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from _cli import InputError

UTF8_BOM = b"\xef\xbb\xbf"
GLOB_CHARACTERS = frozenset("*?[")
SKIPPED_DIR_NAMES = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache"}
)


@dataclass(frozen=True)
class TextFacts:
    """Decoded text plus the byte facts the seal checks care about."""

    text: str
    has_bom: bool
    crlf_count: int
    lone_lf_count: int
    ends_with_newline: bool
    encoding: str


def _is_inside_worktrees(parts: list[str]) -> bool:
    return any(
        first == ".claude" and second == "worktrees"
        for first, second in pairwise(parts)
    )


def _is_excluded(relative_path: Path) -> bool:
    parts = [part.lower() for part in relative_path.parts]
    return any(part in SKIPPED_DIR_NAMES for part in parts) or _is_inside_worktrees(
        parts
    )


def collect_python_files(
    path_texts: Iterable[str | Path],
) -> tuple[list[Path], list[Path]]:
    """Return ``(python files, folders given)`` for files and folders.

    Folders are searched recursively; ``__pycache__``, ``.git``, virtual
    environments and ``.claude\\worktrees`` below the given folder are skipped.

    Raises:
        InputError: If a path does not exist.
    """
    files: list[Path] = []
    folders: list[Path] = []
    seen: set[str] = set()
    for path_text in path_texts:
        path = Path(path_text).expanduser().resolve()
        if path.is_dir():
            folders.append(path)
            candidates = sorted(
                item
                for item in path.rglob("*.py")
                if item.is_file() and not _is_excluded(item.relative_to(path))
            )
        elif path.is_file():
            candidates = [path]
        else:
            raise InputError(f"path not found: {path}")
        for candidate in candidates:
            key = os.path.normcase(str(candidate))
            if key not in seen:
                seen.add(key)
                files.append(candidate)
    return files, folders


def _has_glob_characters(text: str) -> bool:
    return any(character in text for character in GLOB_CHARACTERS)


def _literal_prefix_length(pattern: str) -> int:
    """Number of leading path parts of ``pattern`` that contain no glob character."""
    length = 0
    for part in Path(pattern).parts:
        if _has_glob_characters(part):
            break
        length += 1
    return length


def _is_excluded_match(match: str, pattern: str) -> bool:
    """True when a wildcard part of ``pattern`` reached a skipped folder.

    Folders the pattern names literally (``.claude/worktrees/<wt>/...``) are
    the user's explicit choice and are never skipped; glob keeps literal parts
    verbatim, so the match shares the pattern's literal prefix part for part.
    """
    wildcard_parts = Path(match).parts[_literal_prefix_length(pattern) :]
    return bool(wildcard_parts) and _is_excluded(Path(*wildcard_parts))


def expand_file_patterns(path_texts: Iterable[str], base: Path) -> list[Path]:
    """Resolve files and glob patterns (``**`` allowed) relative to ``base``.

    Absolute paths and patterns ignore ``base``. Results keep the input order;
    each pattern's matches are sorted and duplicates are dropped. Wildcard parts
    skip hidden and excluded folders; literal parts may name them.

    Raises:
        InputError: If a plain path is not a file or a pattern matches no file
            (an empty selection must not pass silently).
    """
    files: list[Path] = []
    seen: set[str] = set()
    for path_text in path_texts:
        if _has_glob_characters(path_text):
            # Wildcards do not enter hidden or skipped folders (.git,
            # .claude\worktrees); a pattern that names them literally does.
            matches = glob.glob(path_text, root_dir=base, recursive=True)
            candidates = sorted(
                (base / match).resolve()
                for match in matches
                if (base / match).is_file() and not _is_excluded_match(match, path_text)
            )
            if not candidates:
                raise InputError(f"pattern matched no file: {path_text} (base {base})")
        else:
            candidate = (base / Path(path_text).expanduser()).resolve()
            if not candidate.is_file():
                raise InputError(f"file not found: {candidate}")
            candidates = [candidate]
        for candidate in candidates:
            key = os.path.normcase(str(candidate))
            if key not in seen:
                seen.add(key)
                files.append(candidate)
    return files


def is_within(path: Path, folder: Path) -> bool:
    """True when ``path`` is ``folder`` or lies below it (case-insensitive on Windows)."""
    path_text = os.path.normcase(str(path))
    folder_text = os.path.normcase(str(folder))
    try:
        return os.path.commonpath([path_text, folder_text]) == folder_text
    except ValueError:  # different drives
        return False


def require_output_outside(
    output: Path | None, input_files: Iterable[Path], input_folders: Iterable[Path] = ()
) -> None:
    """Refuse an ``--out`` that is an input or lies in an input's folder.

    Raises:
        InputError: If the report would land on or next to an input.
    """
    if output is None:
        return
    resolved = output.expanduser().resolve()
    protected = list(input_folders)
    for input_file in input_files:
        if os.path.normcase(str(resolved)) == os.path.normcase(str(input_file)):
            raise InputError(f"--out would overwrite an input file: {resolved}")
        protected.append(input_file.parent)
    for folder in protected:
        if is_within(resolved, folder):
            raise InputError(f"--out must not be inside an input folder ({folder})")


def decode_bytes(data: bytes) -> tuple[str, str]:
    """Decode as UTF-8 (BOM stripped), then cp949, then UTF-8 with replacement."""
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def text_facts(data: bytes) -> TextFacts:
    """Return the decoded text and its BOM / line-ending facts."""
    text, encoding = decode_bytes(data)
    crlf_count = data.count(b"\r\n")
    return TextFacts(
        text=text,
        has_bom=data.startswith(UTF8_BOM),
        crlf_count=crlf_count,
        lone_lf_count=data.count(b"\n") - crlf_count,
        ends_with_newline=data.endswith(b"\n"),
        encoding=encoding,
    )


def read_text_facts(path: Path) -> TextFacts:
    """Read ``path`` as bytes and return :func:`text_facts`.

    Raises:
        InputError: If the file cannot be read.
    """
    try:
        return text_facts(path.read_bytes())
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
