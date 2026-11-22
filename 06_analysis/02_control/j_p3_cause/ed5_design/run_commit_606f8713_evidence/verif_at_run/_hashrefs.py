"""Hash references outside the seal files: code constants and hashes quoted in documents.

* ``--const FILE:NAME`` - the 64-hex string(s) assigned to ``NAME`` in a Python
  file, compared with every known edition hash.
* ``--quoted DOC`` - hex runs of 8 to 64 characters in a document, resolved as
  prefixes of known file hashes (rule editions, seals, ``--hash-files``).

Nothing here writes to disk or runs git; callers pass the candidate hashes in.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from _cli import InputError
from _files import read_text_facts
from _rules import HASH_PATTERN

# Hex runs not glued to other word characters ("0x1f2e3d4c", "id_1234abcd" are skipped).
QUOTED_HEX_PATTERN = re.compile(r"(?<![0-9A-Za-z_])([0-9a-fA-F]{8,64})(?![0-9A-Za-z_])")
UUID_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_])[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{12}(?![0-9A-Za-z_])"
)
HASH_CHUNK_BYTES = 1 << 20


class HashBasis(StrEnum):
    """How a candidate hash was obtained from its file."""

    RAW = "raw"  # bytes as stored
    LF = "lf"  # CRLF folded to LF
    SEAL = "seal"  # first token of the edition's .sha256


@dataclass(frozen=True)
class HashCandidate:
    """A hash that a constant or a quoted prefix may refer to."""

    digest: str
    path: Path
    label: str  # edition label ("rules", "rev3") or "file" for --hash-files
    basis: HashBasis

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "label": self.label,
            "basis": str(self.basis),
            "hash": self.digest,
        }


@dataclass(frozen=True)
class ConstSpec:
    """``--const FILE:NAME`` after parsing."""

    text: str
    path: Path
    name: str


@dataclass
class ConstValue:
    """One 64-hex value found in the constant and the candidates it equals."""

    spec: ConstSpec
    line: int
    digest: str
    matches: list[HashCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.text,
            "path": str(self.spec.path),
            "name": self.spec.name,
            "line": self.line,
            "hash": self.digest,
            "matches": [candidate.to_dict() for candidate in self.matches],
        }


@dataclass
class ConstLookup:
    """Result of looking one ``--const`` up: values, or why there are none."""

    spec: ConstSpec
    assignment_line: int | None
    values: list[ConstValue] = field(default_factory=list)


@dataclass
class QuotedHash:
    """One hex run quoted in a document."""

    document: Path
    line: int
    prefix: str
    context: str
    matches: list[HashCandidate] = field(default_factory=list)
    is_commit: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "document": str(self.document),
            "line": self.line,
            "prefix": self.prefix,
            "context": self.context,
            "is_commit": self.is_commit,
            "matches": [candidate.to_dict() for candidate in self.matches],
        }


# --- candidates ------------------------------------------------------------------


def hash_file_candidates(path: Path) -> list[HashCandidate]:
    """Raw and LF-folded SHA-256 of an extra file (streamed; LF needs the bytes).

    Raises:
        InputError: If the file cannot be read.
    """
    raw = hashlib.sha256()
    folded = hashlib.sha256()
    pending_cr = False
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(HASH_CHUNK_BYTES):
                raw.update(chunk)
                # Keep a trailing "\r" until the next chunk shows whether "\n" follows.
                if pending_cr:
                    chunk = b"\r" + chunk
                pending_cr = chunk.endswith(b"\r")
                body = chunk[:-1] if pending_cr else chunk
                folded.update(body.replace(b"\r\n", b"\n"))
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    if pending_cr:
        folded.update(b"\r")
    candidates = [HashCandidate(raw.hexdigest(), path, "file", HashBasis.RAW)]
    if folded.hexdigest() != raw.hexdigest():
        candidates.append(HashCandidate(folded.hexdigest(), path, "file", HashBasis.LF))
    return candidates


# --- --const ---------------------------------------------------------------------


def parse_const_spec(text: str, base: Path) -> ConstSpec:
    """Split ``FILE:NAME`` at the last colon (``C:\\...`` paths keep their drive).

    Raises:
        InputError: If the form is wrong or the file does not exist.
    """
    file_text, separator, name = text.rpartition(":")
    if not separator or not file_text or not name.isidentifier():
        raise InputError(f"--const must be FILE:NAME, got {text!r}")
    path = (base / Path(file_text).expanduser()).resolve()
    if not path.is_file():
        raise InputError(f"--const file not found: {path}")
    return ConstSpec(text, path, name)


def _assigned_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return []
    names = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Attribute):
            names.append(target.attr)
    return names


def _hex_strings(value: ast.AST) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(value):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literal = node.value.strip().lower()
            if HASH_PATTERN.fullmatch(literal):
                found.append((node.lineno, literal))
    return found


def lookup_const(spec: ConstSpec, candidates: list[HashCandidate]) -> ConstLookup:
    """Find the first assignment to ``spec.name`` and match its 64-hex strings.

    Raises:
        InputError: If the file is not valid Python.
    """
    source = read_text_facts(spec.path).text
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        message = f"--const file is not valid Python: {spec.path}: {error}"
        raise InputError(message) from error
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        and node.value is not None
        and spec.name in _assigned_names(node)
    ]
    if not assignments:
        return ConstLookup(spec, None)
    first = min(assignments, key=lambda node: node.lineno)
    lookup = ConstLookup(spec, first.lineno)
    if first.value is None:  # filtered above; this narrows AnnAssign.value
        return lookup
    for line, digest in _hex_strings(first.value):
        matches = [item for item in candidates if item.digest == digest]
        lookup.values.append(ConstValue(spec, line, digest, matches))
    return lookup


# --- --quoted --------------------------------------------------------------------


def _looks_like_hash_prefix(token: str) -> bool:
    # Pure digits are dates, counts and ids far more often than hash prefixes.
    return not token.isdigit()


def find_quoted_hashes(document: Path) -> list[QuotedHash]:
    """Every distinct (line, hex run) in the document that could be a hash prefix."""
    quoted: list[QuotedHash] = []
    text = read_text_facts(document).text
    for line_number, line in enumerate(text.splitlines(), start=1):
        seen_on_line: set[str] = set()
        # Session and run ids (UUIDs) are hex too but never file hashes.
        searchable = UUID_PATTERN.sub(lambda found: "-" * len(found.group()), line)
        for match in QUOTED_HEX_PATTERN.finditer(searchable):
            token = match.group(1).lower()
            if not _looks_like_hash_prefix(token) or token in seen_on_line:
                continue
            seen_on_line.add(token)
            start = max(match.start() - 30, 0)
            context = " ".join(line[start : match.end() + 30].split())
            quoted.append(QuotedHash(document, line_number, token, context))
    return quoted


def resolve_quoted(quoted: QuotedHash, candidates: list[HashCandidate]) -> None:
    """Fill ``quoted.matches`` with candidates whose digest starts with the prefix."""
    quoted.matches = [
        candidate for candidate in candidates if candidate.digest.startswith(quoted.prefix)
    ]
