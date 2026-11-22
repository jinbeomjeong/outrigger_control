"""Key presence (I axis): which result rows lack the keys a judgement will read.

A judge that reads ``row.get(key) or 0`` turns a missing key into "0 events"
(gate_scan ``missing_key_default_pass``). Before judging, an auditor checks
that every row carries every key the rule needs (2026-11-21: the 436.9 J-P3
prelaunch audit did this with a one-off script for
``hydraulics_record.relock_step_over_1bar_count`` and
``lock_window_alignment.n_late_fallback``).

**Blind by design.** The tool only asks "is the key there, and is it null?".
It never prints, stores or aggregates a value of a required key, so it can run
on results that must not be seen before the judgement. ``--where`` reads its
own field only to compare it with the value given on the command line; do not
filter on a judged value.

Rows:

* ``.jsonl``: one row per non-blank line.
* ``.json``: a top-level list, or the first list among ``results``,
  ``entries``, ``records``, ``rows`` of a top-level object; an object without
  such a list is one row.
* ``--list-key a.b``: rows are the items of that list (in a ``.json`` file, or
  in every ``.jsonl`` line).

A key is a dotted path (``a.b.c``; a digit part also indexes a list). A key
that is present with value ``null`` counts as missing unless ``--allow-null``.

Arrays of ``.npz`` files (2026-11-21, 436.9 step (6): the judge read per-read
``jp3_*`` arrays that the r79 T4h never had, and nothing checked it before the
run): ``--npz-dir DIR`` (repeatable) with ``--array a,b`` / ``--arrays-file``
checks that every ``*.npz`` (``--npz-glob``) of each folder holds every named
array. Only the zip member names are listed (``zipfile``, no array is loaded,
no value read). An absent folder, or a folder without a matching file, is an
input error (exit 2: "nothing found" is never a pass). ``.npz`` checks and row
keys may be given in one run.

Exit codes: 0 every selected row has every key (and every npz every array), 1 a
row lacks a key or an npz lacks an array (or no row was selected, a line did
not parse, an npz did not open), 2 input error, 3 bug.

Usage:
    python key_presence.py FILE_OR_GLOB [...] --key a.b,c [--key ...]
        [--keys-file FILE] [--repo DIR] [--list-key a.b] [--where a.b=VALUE ...]
        [--allow-null] [--out R] [--format md|json] [--fail-on error|warning]
    python key_presence.py --npz-dir DIR [--npz-dir ...] --array a,b [--array ...]
        [--arrays-file FILE] [--npz-glob "*.npz"] [--repo DIR] [--out R] ...
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import decode_bytes, expand_file_patterns, require_output_outside
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
from _records import get_dotted, split_fields, value_text

TOOL_NAME = "key_presence"
AUTO_LIST_KEYS = ("results", "entries", "records", "rows")
SUPPORTED_SUFFIXES = (".jsonl", ".json")
MAX_EXAMPLES = 5
KEYS_FILE_COMMENT = "#"
NPZ_MEMBER_SUFFIX = ".npy"
"""``numpy.savez`` stores array ``name`` as the zip member ``name.npy``."""
DEFAULT_NPZ_GLOB = "*.npz"


@dataclass(frozen=True)
class Row:
    """One result row and where it came from (``line`` 0 for ``.json``)."""

    line: int
    index: int | None
    data: object

    def locator(self) -> str:
        if self.line and self.index is not None:
            return f"줄 {self.line} #{self.index}"
        if self.line:
            return f"줄 {self.line}"
        return f"항목 #{self.index}"


@dataclass
class KeyCount:
    """Rows of one key: present (not null), absent, null."""

    key: str
    present: int = 0
    absent: int = 0
    null: int = 0
    examples: list[str] = field(default_factory=list)

    def missing(self, allow_null: bool) -> int:
        return self.absent + (0 if allow_null else self.null)

    def to_dict(self, allow_null: bool) -> dict[str, object]:
        return {
            "key": self.key,
            "present": self.present,
            "absent": self.absent,
            "null": self.null,
            "missing": self.missing(allow_null),
            "first_missing": self.examples,
        }


@dataclass
class FileRows:
    """Rows of one file and the facts found while reading it."""

    path: Path
    container_key: str | None = None
    rows: list[Row] = field(default_factory=list)
    parse_errors: list[tuple[int, str]] = field(default_factory=list)
    list_key_absent: list[int] = field(default_factory=list)
    selected: list[Row] = field(default_factory=list)
    where_field_absent: int = 0
    counts: list[KeyCount] = field(default_factory=list)


@dataclass(frozen=True)
class Settings:
    """Parsed command-line choices shared by every file."""

    keys: list[str]
    conditions: list[tuple[str, str]]
    list_key: str | None
    allow_null: bool


# --- arguments ------------------------------------------------------------------


def _validated_key(text: str, role: str) -> str:
    key = text.strip()
    if not key or any(not part for part in key.split(".")):
        raise InputError(f"{role} is not a dotted key path: {text!r}")
    return key


def _keys_from_file(path_text: str) -> list[str]:
    path = Path(path_text).expanduser().resolve()
    try:
        text, _ = decode_bytes(path.read_bytes())
    except OSError as error:
        raise InputError(f"cannot read --keys-file {path}: {error}") from error
    keys: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(KEYS_FILE_COMMENT):
            keys += split_fields(stripped)
    return keys


def _required_keys(args: argparse.Namespace) -> list[str]:
    """Keys from ``--key`` and ``--keys-file``, deduplicated in order (may be empty).

    Raises:
        InputError: If a key is not a dotted path.
    """
    texts: list[str] = []
    for item in args.key or []:
        texts += split_fields(item)
    if args.keys_file:
        texts += _keys_from_file(args.keys_file)
    keys = [_validated_key(text, "--key") for text in texts]
    return list(dict.fromkeys(keys))


def _required_arrays(args: argparse.Namespace) -> list[str]:
    """Array names from ``--array`` and ``--arrays-file``, deduplicated in order.

    Raises:
        InputError: If a name is empty or holds a path separator.
    """
    texts: list[str] = []
    for item in args.array or []:
        texts += split_fields(item)
    if args.arrays_file:
        texts += _keys_from_file(args.arrays_file)
    names = [text.strip() for text in texts]
    for name in names:
        if not name or "/" in name or "\\" in name:
            raise InputError(f"--array is not an array name: {name!r}")
    return list(dict.fromkeys(names))


def _parse_where(items: list[str]) -> list[tuple[str, str]]:
    conditions = []
    for item in items:
        field_path, separator, expected = item.partition("=")
        if not separator:
            raise InputError(f"--where needs FIELD=VALUE: {item!r}")
        conditions.append((_validated_key(field_path, "--where field"), expected))
    return conditions


# --- reading rows ---------------------------------------------------------------


def _list_rows(items: list[object], line: int) -> list[Row]:
    return [Row(line, index, item) for index, item in enumerate(items, start=1)]


def _read_jsonl(loaded: FileRows, text: str, list_key: str | None) -> None:
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            loaded.parse_errors.append((number, error.msg))
            continue
        if list_key is None:
            loaded.rows.append(Row(number, None, document))
            continue
        found, value = get_dotted(document, list_key)
        if found and isinstance(value, list):
            loaded.rows += _list_rows(value, number)
        else:
            loaded.list_key_absent.append(number)


def _auto_list_key(document: dict[str, object]) -> str | None:
    for key in AUTO_LIST_KEYS:
        if isinstance(document.get(key), list):
            return key
    return None


def _read_json(loaded: FileRows, text: str, list_key: str | None) -> None:
    """Rows of a ``.json`` document.

    Raises:
        InputError: If ``--list-key`` does not name a list in the document.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        loaded.parse_errors.append((error.lineno, error.msg))
        return
    if list_key is not None:
        found, value = get_dotted(document, list_key)
        if not (found and isinstance(value, list)):
            raise InputError(f"--list-key {list_key!r} is not a list in {loaded.path}")
        loaded.container_key = list_key
        loaded.rows = _list_rows(value, 0)
    elif isinstance(document, list):
        loaded.rows = _list_rows(document, 0)
    elif isinstance(document, dict) and (key := _auto_list_key(document)):
        loaded.container_key = key
        loaded.rows = _list_rows(document[key], 0)
    else:
        loaded.rows = [Row(0, 1, document)]


def read_rows(path: Path, list_key: str | None) -> FileRows:
    """Read the rows of one ``.jsonl`` / ``.json`` file.

    Raises:
        InputError: If the file is unreadable, of another type, or lacks ``--list-key``.
    """
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise InputError(f"unsupported file (jsonl, json): {path}")
    try:
        text, _ = decode_bytes(path.read_bytes())
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    loaded = FileRows(path)
    if path.suffix.lower() == ".jsonl":
        _read_jsonl(loaded, text, list_key)
    else:
        _read_json(loaded, text, list_key)
    return loaded


# --- counting -------------------------------------------------------------------


def _as_number(text: str) -> float | None:
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _matches(value: object, expected_text: str) -> bool:
    """Same rule as ``record_check --where``: text form, or equal numbers."""
    if value_text(value) == expected_text:
        return True
    expected_number = _as_number(expected_text)
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    return expected_number is not None and is_number and float(value) == expected_number


def _select(loaded: FileRows, conditions: list[tuple[str, str]]) -> None:
    for row in loaded.rows:
        is_selected = True
        for field_path, expected in conditions:
            found, value = get_dotted(row.data, field_path)
            if not found:
                loaded.where_field_absent += 1
                is_selected = False
                break
            if not _matches(value, expected):
                is_selected = False
                break
        if is_selected:
            loaded.selected.append(row)


def _count_keys(loaded: FileRows, keys: list[str], allow_null: bool) -> None:
    """Presence only: the value of a required key is compared with None, nothing else."""
    loaded.counts = [KeyCount(key) for key in keys]
    for row in loaded.selected:
        for count in loaded.counts:
            found, value = get_dotted(row.data, count.key)
            if found and value is not None:
                count.present += 1
                continue
            if not found:
                count.absent += 1
            else:
                count.null += 1
                if allow_null:
                    continue
            if len(count.examples) < MAX_EXAMPLES:
                count.examples.append(row.locator())


def _merge_counts(files: list[FileRows], keys: list[str]) -> list[KeyCount]:
    totals = [KeyCount(key) for key in keys]
    for loaded in files:
        for total, count in zip(totals, loaded.counts, strict=True):
            total.present += count.present
            total.absent += count.absent
            total.null += count.null
            for example in count.examples:
                if len(total.examples) < MAX_EXAMPLES:
                    total.examples.append(f"{loaded.path.name} {example}")
    return totals


# --- npz arrays -----------------------------------------------------------------


@dataclass
class NpzFile:
    """The array names of one ``.npz`` file (``None``: it did not open as a zip)."""

    path: Path
    arrays: set[str] | None
    error: str | None = None


def npz_array_names(path: Path) -> NpzFile:
    """The arrays of ``path`` from its zip member names only (no array is loaded)."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as error:
        return NpzFile(path, None, f"{type(error).__name__}: {error}")
    return NpzFile(path, {name.removesuffix(NPZ_MEMBER_SUFFIX) for name in names
                          if name.endswith(NPZ_MEMBER_SUFFIX)})


def read_npz_dirs(dirs: list[str], pattern: str, base: Path) -> list[NpzFile]:
    """Every file of ``pattern`` in each folder (not recursive), in name order.

    Raises:
        InputError: A folder that does not exist or holds no matching file.
    """
    found: list[NpzFile] = []
    for text in dirs:
        folder = Path(text).expanduser()
        folder = (folder if folder.is_absolute() else base / folder).resolve()
        if not folder.is_dir():
            raise InputError(f"--npz-dir is not a folder: {folder}")
        paths = sorted(path for path in folder.glob(pattern) if path.is_file())
        if not paths:
            raise InputError(f"--npz-dir {folder}: no {pattern} file (an empty folder is "
                             "never a pass)")
        found += [npz_array_names(path) for path in paths]
    return found


def _npz_counts(files: list[NpzFile], arrays: list[str]) -> list[dict[str, object]]:
    counts = []
    for name in arrays:
        readable = [item for item in files if item.arrays is not None]
        absent = [item.path.name for item in readable if name not in item.arrays]
        counts.append({"array": name, "present": len(readable) - len(absent),
                       "absent": len(absent), "first_missing": absent[:MAX_EXAMPLES]})
    return counts


def _npz_findings(files: list[NpzFile], arrays: list[str]) -> list[Finding]:
    findings = []
    for item in files:
        location = str(item.path)
        if item.arrays is None:
            text = f"npz로 열 수 없음: {item.error}"
            findings.append(Finding(Severity.ERROR, "npz_unreadable", location, 0, text))
            continue
        missing = [name for name in arrays if name not in item.arrays]
        if missing:
            text = f"배열 없음 {len(missing)}/{len(arrays)}: {', '.join(missing)}"
            findings.append(Finding(Severity.ERROR, "npz_array_absent", location, 0, text,
                                    ",".join(missing)))
    return findings


# --- findings and report --------------------------------------------------------


def _key_findings(loaded: FileRows, allow_null: bool) -> list[Finding]:
    findings = []
    location, total = str(loaded.path), len(loaded.selected)
    for count in loaded.counts:
        examples = ", ".join(count.examples) or "-"
        if count.absent:
            message = f"`{count.key}` 없음 {count.absent}/{total}줄 (처음: {examples})"
            findings.append(
                Finding(Severity.ERROR, "key_absent", location, 0, message, count.key)
            )
        if count.null and not allow_null:
            message = (
                f"`{count.key}` 값이 null {count.null}/{total}줄"
                " (null을 있음으로 보려면 --allow-null)"
            )
            findings.append(
                Finding(Severity.ERROR, "key_null", location, 0, message, count.key)
            )
    return findings


def _file_findings(loaded: FileRows, has_conditions: bool) -> list[Finding]:
    findings = []
    location = str(loaded.path)
    for line, message in loaded.parse_errors:
        text = f"JSON으로 읽을 수 없음: {message}"
        findings.append(
            Finding(Severity.ERROR, "record_parse_error", location, line, text)
        )
    if loaded.list_key_absent:
        shown = ", ".join(str(line) for line in loaded.list_key_absent[:MAX_EXAMPLES])
        text = f"--list-key 목록이 없는 줄 {len(loaded.list_key_absent)}개(줄 {shown})"
        findings.append(Finding(Severity.ERROR, "list_key_absent", location, 0, text))
    if not loaded.rows:
        text = "행 0개: 빈 입력은 통과가 아니다"
        findings.append(Finding(Severity.ERROR, "no_rows", location, 0, text))
    elif has_conditions and not loaded.selected:
        text = "--where로 고른 행 0개: 빈 선택은 통과가 아니다"
        findings.append(Finding(Severity.ERROR, "selection_empty", location, 0, text))
    if loaded.where_field_absent:
        text = f"--where 필드가 없어 빠진 행 {loaded.where_field_absent}개"
        findings.append(Finding(Severity.INFO, "where_field_absent", location, 0, text))
    return findings


def _file_dict(loaded: FileRows, allow_null: bool) -> dict[str, object]:
    return {
        "path": str(loaded.path),
        "container_key": loaded.container_key,
        "rows": len(loaded.rows),
        "selected": len(loaded.selected),
        "where_field_absent": loaded.where_field_absent,
        "parse_errors": len(loaded.parse_errors),
        "list_key_absent": len(loaded.list_key_absent),
        "keys": [count.to_dict(allow_null) for count in loaded.counts],
    }


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    lines = [
        "# key_presence — 필수 키 존재 점검 (값은 읽지 않음)",
        "",
        (
            f"- 파일 {summary['files']}개, 행 {summary['rows']}개 중 대상 "
            f"{summary['selected']}개, 키 {summary['keys']}개 · "
            f"{severity_summary_text(findings)}"
        ),
        (
            f"- 조건: {' AND '.join(report['where']) or '(없음)'}, "
            f"null은 {'있음' if report['allow_null'] else '없음'}으로 셈"
        ),
        "",
        "| 키 | 있음 | 없음 | null | 대상 행 |",
        "|---|---|---|---|---|",
    ]
    if report["npz"]["files"]:
        npz = report["npz"]
        text = f"- npz 파일 {len(npz['files'])}개, 배열 {len(npz['arrays'])}개 (zip 이름만)"
        lines[2:2] = [text]
    for item in report["keys"]:
        lines.append(
            f"| `{item['key']}` | {item['present']} | {item['absent']} "
            f"| {item['null']} | {summary['selected']} |"
        )
    lines += ["", "## 파일별", "", "| 파일 | 목록 키 | 행 | 대상 | 빠진 키 |"]
    lines.append("|---|---|---|---|---|")
    for item in report["files"]:
        incomplete = sum(1 for key in item["keys"] if key["missing"])
        lines.append(
            f"| `{Path(item['path']).name}` | {item['container_key'] or '-'} "
            f"| {item['rows']} | {item['selected']} | {incomplete} |"
        )
    if report["npz"]["arrays"]:
        lines += ["", "## npz 배열", "", "| 배열 | 있음 | 없음 | 처음 빠진 파일 |",
                  "|---|---|---|---|"]
        lines += [f"| `{item['array']}` | {item['present']} | {item['absent']} "
                  f"| {', '.join(item['first_missing']) or '-'} |"
                  for item in report["npz"]["arrays"]]
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def _summary(
    files: list[FileRows], totals: list[KeyCount], settings: Settings
) -> dict[str, object]:
    return {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": len(files),
        "rows": sum(len(item.rows) for item in files),
        "selected": sum(len(item.selected) for item in files),
        "keys": len(totals),
        "keys_complete": sum(
            1 for count in totals if not count.missing(settings.allow_null)
        ),
        "keys_incomplete": sum(
            1 for count in totals if count.missing(settings.allow_null)
        ),
    }


def run_key_presence(args: argparse.Namespace) -> ToolOutcome:
    """Count, per required key, the selected rows that carry it."""
    settings = Settings(
        _required_keys(args),
        _parse_where(args.where or []),
        _validated_key(args.list_key, "--list-key") if args.list_key else None,
        args.allow_null,
    )
    arrays = _required_arrays(args)
    if bool(args.inputs) != bool(settings.keys):
        raise InputError("row files need --key / --keys-file and the other way round")
    if bool(args.npz_dir) != bool(arrays):
        raise InputError("--npz-dir needs --array / --arrays-file and the other way round")
    if not args.inputs and not args.npz_dir:
        raise InputError("nothing to check: give row files with --key, or --npz-dir with "
                         "--array")
    base = Path(args.repo).expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    paths = expand_file_patterns(args.inputs, base) if args.inputs else []
    npz_files = read_npz_dirs(args.npz_dir or [], args.npz_glob, base)
    require_output_outside(args.out, [*paths, *(item.path for item in npz_files)])
    files = [read_rows(path, settings.list_key) for path in paths]
    findings: list[Finding] = []
    for loaded in files:
        _select(loaded, settings.conditions)
        _count_keys(loaded, settings.keys, settings.allow_null)
        findings += _file_findings(loaded, bool(settings.conditions))
        findings += _key_findings(loaded, settings.allow_null)
    findings += _npz_findings(npz_files, arrays)
    findings = sort_findings(findings)
    totals = _merge_counts(files, settings.keys)
    npz_counts = _npz_counts(npz_files, arrays)
    summary = {
        **_summary(files, totals, settings),
        "npz_files": len(npz_files),
        "arrays": len(arrays),
        "arrays_incomplete": sum(1 for item in npz_counts if item["absent"]),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "keys_required": settings.keys,
        "where": [f"{path}={value}" for path, value in settings.conditions],
        "list_key": settings.list_key,
        "allow_null": settings.allow_null,
        "keys": [count.to_dict(settings.allow_null) for count in totals],
        "files": [_file_dict(loaded, settings.allow_null) for loaded in files],
        "npz": {"glob": args.npz_glob, "dirs": list(args.npz_dir or []),
                "arrays_required": arrays, "arrays": npz_counts,
                "files": [{"path": str(item.path), "readable": item.arrays is not None,
                           "missing": [] if item.arrays is None
                           else [name for name in arrays if name not in item.arrays]}
                          for item in npz_files]},
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(report, findings), report, paths)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="key_presence.py",
        description="결과 행마다 필수 키가 있는지만 센다(값은 읽지 않음, 읽기 전용).",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="jsonl/json files or glob patterns (relative to --repo)",
    )
    parser.add_argument(
        "--npz-dir",
        action="append",
        help="folder of .npz files whose arrays are checked (repeatable, not recursive)",
    )
    parser.add_argument(
        "--npz-glob", default=DEFAULT_NPZ_GLOB, help="file pattern in --npz-dir (*.npz)"
    )
    parser.add_argument(
        "--array", action="append", help="required array name(s), comma-separated"
    )
    parser.add_argument(
        "--arrays-file", help="file with one array name per line (# comments)"
    )
    parser.add_argument(
        "--key",
        action="append",
        help="required dotted key(s), comma-separated, repeatable",
    )
    parser.add_argument(
        "--keys-file", help="file with one dotted key per line (# comments)"
    )
    parser.add_argument(
        "--repo", default=".", help="base folder of relative paths (default .)"
    )
    parser.add_argument(
        "--list-key",
        help="dotted key of the row list (json document or each jsonl line); "
        f"default for json: first of {', '.join(AUTO_LIST_KEYS)}",
    )
    parser.add_argument(
        "--where", action="append", help="FIELD=VALUE row filter (repeat = AND)"
    )
    parser.add_argument(
        "--allow-null", action="store_true", help="count a null value as present"
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_key_presence(args))


if __name__ == "__main__":
    sys.exit(main())
