"""Rule editions (original + ``_rev<N>`` addenda) and their ``.sha256`` seal files.

A rule family is an original ``<stem>.md`` plus ``<stem>_rev<N>[a-z].md`` files
in the same folder. Revision numbers are not zero-padded, so they are sorted as
numbers (rev2 before rev10); a letter suffix (rev12a) sorts after its number.

A seal file ``<file stem>.sha256`` (or ``<file name>.sha256``, e.g.
``spec.md.sha256``) holds one line::

    <64 hex>  <file name>  sealed YYYY-MM-DD HH:MM:SS +09:00 (<note>)

Only the first token is the hash; the rest is optional. A ``*`` before the file
name (``sha256sum -b``) is not part of the name.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from _cli import InputError
from _files import TextFacts, read_text_facts, text_facts

ORIGINAL_LABEL = "rules"
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
ANY_REVISION_PATTERN = re.compile(
    r"^(?P<stem>.+)_rev(?P<number>\d+)(?P<suffix>[a-z]?)\.md$"
)
SEAL_LINE_PATTERN = re.compile(
    r"^(?P<hash>\S+)"
    r"(?:\s+(?P<name>\S+))?"
    r"(?:\s+sealed\s+(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:[ T](?P<clock>\d{2}:\d{2}(?::\d{2})?))?"
    r"(?:\s*(?P<offset>Z|[+-]\d{2}:?\d{2}))?)?"
    r"(?:\s*\((?P<note>.*)\))?\s*$",
    re.DOTALL,
)


class SealMatch(StrEnum):
    """How the sealed hash relates to the file bytes."""

    RAW = "raw"
    LF = "lf"
    NONE = "none"
    NO_SHA = "no_sha"


@dataclass(frozen=True)
class RuleEdition:
    """One file of a rule family: the original or a numbered revision."""

    path: Path
    family: str
    label: str
    number: int
    suffix: str

    @property
    def is_original(self) -> bool:
        return self.number == 0


@dataclass(frozen=True)
class SealFile:
    """A parsed ``.sha256`` file."""

    path: Path
    facts: TextFacts
    first_token: str
    is_well_formed: bool
    file_name: str | None
    sealed_at: str | None
    note: str


@dataclass(frozen=True)
class EditionHashes:
    """SHA-256 of an edition as raw bytes and with CRLF folded to LF."""

    raw: str
    lf: str
    facts: TextFacts


def _revision_pattern(stem: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(stem)}_rev(\d+)([a-z]?)\.md$")


def collect_editions(
    original_texts: list[str], include_revisions: bool
) -> list[RuleEdition]:
    """Return every edition of the given originals, each family in revision order.

    Raises:
        InputError: If an original is missing or not a ``.md`` file.
    """
    editions: list[RuleEdition] = []
    for original_text in original_texts:
        original = Path(original_text).expanduser().resolve()
        if not original.is_file():
            raise InputError(f"rule file not found: {original}")
        if original.suffix.lower() != ".md":
            raise InputError(f"rule file must be a .md file: {original}")
        family = original.stem
        editions.append(RuleEdition(original, family, ORIGINAL_LABEL, 0, ""))
        if include_revisions:
            editions += _revisions_of(original)
    return editions


def _revisions_of(original: Path) -> list[RuleEdition]:
    pattern = _revision_pattern(original.stem)
    found: list[RuleEdition] = []
    for candidate in original.parent.iterdir():
        match = pattern.match(candidate.name)
        if match and candidate.is_file():
            number, suffix = int(match.group(1)), match.group(2)
            found.append(
                RuleEdition(
                    candidate.resolve(),
                    original.stem,
                    f"rev{number}{suffix}",
                    number,
                    suffix,
                )
            )
    return sorted(found, key=lambda edition: (edition.number, edition.suffix))


def _as_revision(path: Path) -> RuleEdition | None:
    """The edition for ``<stem>_rev<N>[a-z].md`` when ``<stem>.md`` exists beside it."""
    match = ANY_REVISION_PATTERN.match(path.name)
    if match is None:
        return None
    stem = match.group("stem")
    if not (path.parent / f"{stem}.md").is_file():
        return None
    number, suffix = int(match.group("number")), match.group("suffix")
    return RuleEdition(path, stem, f"rev{number}{suffix}", number, suffix)


def editions_for_files(files: list[Path], include_revisions: bool) -> list[RuleEdition]:
    """Group rule files (e.g. glob matches) into families of editions.

    A revision file whose original sits beside it joins that original's family,
    so ``x.md`` and ``x_rev1.md`` matched by one pattern are checked once.
    With ``include_revisions`` every revision beside an original is added;
    without it only the revisions named in ``files`` are kept.

    Raises:
        InputError: If a file is missing or not a ``.md`` file.
    """
    originals: list[Path] = []
    named_revisions: list[RuleEdition] = []
    for path in files:
        revision = _as_revision(path)
        original = path if revision is None else path.parent / f"{revision.family}.md"
        if revision is not None:
            named_revisions.append(revision)
        if original.resolve() not in originals:
            originals.append(original.resolve())
    editions = collect_editions([str(path) for path in originals], include_revisions)
    if not include_revisions:
        editions += named_revisions
    family_order = {path.stem: index for index, path in enumerate(originals)}
    return sorted(
        editions,
        key=lambda edition: (family_order[edition.family], edition.number, edition.suffix),
    )


def missing_revision_numbers(editions: list[RuleEdition]) -> list[int]:
    """Revision numbers absent between 1 and the highest one present."""
    numbers = {edition.number for edition in editions if not edition.is_original}
    if not numbers:
        return []
    return [number for number in range(1, max(numbers) + 1) if number not in numbers]


def seal_path_candidates(edition: RuleEdition, sha_dir: Path | None) -> list[Path]:
    """Seal file names in lookup order: ``<stem>.sha256``, then ``<name>.sha256``.

    Both conventions are in use: ``x_rules.sha256`` beside ``x_rules.md`` and
    ``jp3_remedy_spec.md.sha256`` (``sha256sum x.md > x.md.sha256``).
    """
    folder = sha_dir if sha_dir is not None else edition.path.parent
    return [
        folder / f"{edition.path.stem}.sha256",
        folder / f"{edition.path.name}.sha256",
    ]


def seal_path_for(edition: RuleEdition, sha_dir: Path | None) -> Path:
    """The first existing seal candidate, else ``<stem>.sha256`` (for messages)."""
    candidates = seal_path_candidates(edition, sha_dir)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _iso_time(date: str, clock: str | None, offset: str | None) -> str:
    text = f"{date}T{clock}" if clock else date
    if clock and len(clock) == len("HH:MM"):
        text += ":00"
    if offset:
        normalized = (
            offset if offset == "Z" or ":" in offset else f"{offset[:3]}:{offset[3:]}"
        )
        text += "+00:00" if normalized == "Z" else normalized
    return text


def parse_seal_file(path: Path) -> SealFile:
    """Parse a ``.sha256`` file; malformed content is reported, not raised.

    Raises:
        InputError: If the file exists but cannot be read.
    """
    facts = read_text_facts(path)
    content = facts.text.strip()
    tokens = content.split()
    first_token = tokens[0] if tokens else ""
    is_well_formed = bool(HASH_PATTERN.fullmatch(first_token))
    match = SEAL_LINE_PATTERN.match(content)
    if match is None:
        return SealFile(path, facts, first_token, is_well_formed, None, None, "")
    date = match.group("date")
    sealed_at = (
        _iso_time(date, match.group("clock"), match.group("offset")) if date else None
    )
    note = " ".join((match.group("note") or "").split())
    name = match.group("name")
    # `sha256sum -b` writes "<hash> *<name>": the star marks binary mode, not the name.
    file_name = name.removeprefix("*") if name else None
    return SealFile(
        path, facts, first_token, is_well_formed, file_name, sealed_at, note
    )


def hash_edition(path: Path) -> EditionHashes:
    """Hash the file as stored and with every CRLF replaced by LF.

    Raises:
        InputError: If the file cannot be read.
    """
    try:
        data = path.read_bytes()
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    return EditionHashes(
        raw=hashlib.sha256(data).hexdigest(),
        lf=hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(),
        facts=text_facts(data),
    )


def classify_seal(hashes: EditionHashes, seal: SealFile | None) -> SealMatch:
    """Return which convention, if any, the sealed hash follows."""
    if seal is None:
        return SealMatch.NO_SHA
    sealed = seal.first_token.lower()
    if sealed == hashes.raw:
        return SealMatch.RAW
    if sealed == hashes.lf:
        return SealMatch.LF
    return SealMatch.NONE


def parse_time(text: str | None) -> datetime | None:
    """Parse ISO 8601 (date, date-time, with or without offset); ``None`` if not."""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.strip().replace(" ", "T", 1))
    except ValueError:
        return None
