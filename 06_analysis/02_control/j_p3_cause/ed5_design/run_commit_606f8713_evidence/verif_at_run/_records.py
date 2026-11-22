"""Load result records from jsonl, json and npz files, and read dotted fields.

* ``.jsonl``: one JSON value per non-blank line (CRLF/LF, BOM allowed).
* ``.json``: a list of records, or an object whose ``entries`` or ``records``
  key holds the list; the other keys of that object are the file meta.
* ``.npz``: only array names, shapes and dtypes (needs numpy; the arrays are
  not loaded and pickled objects are never unpickled).

``sample`` keeps only the first and last N records (the total is still counted).
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from _cli import InputError
from _files import decode_bytes

RECORD_LIST_KEYS = ("entries", "records")
ABSENT_TEXT = "<없음>"


class FileKind(StrEnum):
    """Supported result file formats."""

    JSONL = "jsonl"
    JSON = "json"
    NPZ = "npz"


@dataclass(frozen=True)
class Record:
    """One result record; ``line`` is its file line (0 for .json entries)."""

    index: int
    line: int
    data: object

    def locator(self) -> str:
        return f"줄 {self.line}" if self.line else f"항목 #{self.index}"


@dataclass
class LoadedFile:
    """Records (possibly sampled) and file-level facts of one result file."""

    path: Path
    kind: FileKind
    records: list[Record] = field(default_factory=list)
    total_records: int = 0
    is_sampled: bool = False
    container: dict[str, object] | None = None
    container_key: str | None = None
    parse_errors: list[tuple[int, str]] = field(default_factory=list)
    npz_arrays: list[dict[str, object]] = field(default_factory=list)
    npz_unavailable_reason: str = ""


def get_dotted(value: object, dotted_path: str) -> tuple[bool, object]:
    """Follow ``a.b.c`` through dicts (and list indices); return ``(found, value)``."""
    current = value
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


def value_text(value: object) -> str:
    """Stable text form of a field value, used as a grouping key."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _kind_of(path: Path) -> FileKind:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return FileKind.JSONL
    if suffix == ".json":
        return FileKind.JSON
    if suffix == ".npz":
        return FileKind.NPZ
    raise InputError(f"unsupported result file (jsonl, json, npz): {path}")


def _keep_sample(
    records: list[Record], sample: int | None
) -> tuple[list[Record], bool]:
    if sample is None or len(records) <= 2 * sample:
        return records, False
    return records[:sample] + records[-sample:], True


def _load_jsonl(loaded: LoadedFile, text: str, sample: int | None) -> None:
    numbered_lines = [
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]
    loaded.total_records = len(numbered_lines)
    if sample is not None and len(numbered_lines) > 2 * sample:
        numbered_lines = numbered_lines[:sample] + numbered_lines[-sample:]
        loaded.is_sampled = True
    for index, (number, line) in enumerate(numbered_lines, start=1):
        try:
            loaded.records.append(Record(index, number, json.loads(line)))
        except json.JSONDecodeError as error:
            loaded.parse_errors.append((number, error.msg))


def _load_json(loaded: LoadedFile, text: str, sample: int | None) -> None:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        loaded.parse_errors.append((error.lineno, error.msg))
        return
    entries: object = document
    if isinstance(document, dict):
        loaded.container = document
        list_key = next(
            (key for key in RECORD_LIST_KEYS if isinstance(document.get(key), list)),
            None,
        )
        loaded.container_key = list_key
        entries = document[list_key] if list_key else [document]
    if not isinstance(entries, list):
        entries = [entries]
    records = [Record(index, 0, item) for index, item in enumerate(entries, start=1)]
    loaded.total_records = len(records)
    loaded.records, loaded.is_sampled = _keep_sample(records, sample)


def _npz_array_headers(path: Path) -> list[dict[str, object]]:
    from numpy.lib import format as npy_format  # optional dependency

    arrays: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            if not member.endswith(".npy"):
                continue
            with archive.open(member) as handle:
                version = npy_format.read_magic(handle)
                if version == (1, 0):
                    shape, _, dtype = npy_format.read_array_header_1_0(handle)
                else:
                    shape, _, dtype = npy_format.read_array_header_2_0(handle)
            arrays.append(
                {
                    "key": member[: -len(".npy")],
                    "shape": list(shape),
                    "dtype": str(dtype),
                }
            )
    return arrays


def _load_npz(loaded: LoadedFile) -> None:
    try:
        loaded.npz_arrays = _npz_array_headers(loaded.path)
    except ImportError:
        loaded.npz_unavailable_reason = "numpy not installed"
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        loaded.parse_errors.append((0, f"npz unreadable: {error}"))


def load_records(path: Path, sample: int | None = None) -> LoadedFile:
    """Load one result file.

    Raises:
        InputError: If the file is missing, unreadable or of an unknown type.
    """
    if not path.is_file():
        raise InputError(f"result file not found: {path}")
    loaded = LoadedFile(path, _kind_of(path))
    if loaded.kind == FileKind.NPZ:
        _load_npz(loaded)
        return loaded
    try:
        text, _ = decode_bytes(path.read_bytes())
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    if loaded.kind == FileKind.JSONL:
        _load_jsonl(loaded, text, sample)
    else:
        _load_json(loaded, text, sample)
    return loaded


def split_fields(text: str | None) -> list[str]:
    """``"a.b, c"`` -> ``["a.b", "c"]`` (empty items dropped)."""
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]
