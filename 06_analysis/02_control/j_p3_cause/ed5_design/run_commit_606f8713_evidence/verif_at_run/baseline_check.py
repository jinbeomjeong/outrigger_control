"""Baseline check (I axis): checksum lists and run identity of a sealed baseline folder.

``sums`` verifies ``SHA256SUMS``-style lists (2026-11-16: a list committed with
``-text`` kept CRLF, and 18 of its npz files never reached the commit because
``.gitignore`` has ``*.npz``):

* every entry's file exists and its SHA-256 equals the listed digest (an LF/CRLF
  only difference is named);
* files in the list's folder that the list does not name (``--allow-extra``);
* CRLF line ends (removed before parsing, reported), BOM, duplicates, bad lines;
* the list and each listed file are tracked by git (index, or ``--rev`` tree)
  and not matched by an ignore rule (``cited_untracked``/``cited_ignored``).

Entry names are relative to the list's own folder (``--base sums-dir``, the
default and the only behaviour before 2026-11-21) or to the repository root
(``--base repo-root``: ``--repo`` when given, else the git work tree that holds
the list). When every entry of a list is missing, the other base is tried and
an info ``sums_base_hint`` says how many entries exist (and match) there, so a
wrong base is told apart from really missing files.

``identity`` reads every ``*identity*.json`` of a baseline folder and checks
each git block (``"git": {"head": …, "is_clean": …}`` at any depth): the head
equals ``--expect-commit`` (or, without it, all heads agree), the tree was
clean, and optionally (``--mtime``) that no file the baseline commit changed
was edited after the commit but before the run started. A head that is not a
full hex commit (``""`` from a failed git call, a short or broken value) or a
block with a git failure mark (``error``) is an error whatever ``is_clean``
says (2026-11-21: ``d8x_record.git_state`` writes head ``""`` and
``is_clean: true`` when git fails, and ``""`` used to match any expected commit).

Usage:
    python baseline_check.py sums SUMS_OR_GLOB [...] [--repo DIR] [--rev REV]
        [--base sums-dir|repo-root] [--allow-extra GLOB ...] [--no-git] [--out R]
        [--format md|json] [--fail-on …]
    python baseline_check.py identity FOLDER_OR_FILE [...] [--glob "**/*identity*.json"]
        [--expect-commit SHA] [--repo DIR] [--mtime] [--no-git] [--out R] …

Exit codes: 0 nothing at ``--fail-on`` level, 1 findings, 2 input error, 3 bug.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import (
    SKIPPED_DIR_NAMES,
    decode_bytes,
    expand_file_patterns,
    require_output_outside,
)
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
    sort_findings,
)
from _git import GitQueries
from _rules import parse_time
from _sums import SumsEntry, SumsFile, parse_sums_file, resolve_entry_name
from _tracking import CitedFile, collect_track_facts, track_findings

TOOL_NAME = "baseline_check"
SHORT_HASH_CHARS = 12
SUMS_ROLES = frozenset({"sums_list", "sums_entry"})
DEFAULT_IDENTITY_GLOB = "**/*identity*.json"
GIT_BLOCK_KEY = "git"
RUN_TIME_KEYS = ("time", "started", "start_time", "started_at")
IDENTITY_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S")
MIN_COMMIT_PREFIX_CHARS = 7
FULL_COMMIT_LENGTHS = (40, 64)
"""A recorded head is a full SHA-1 (or SHA-256 object format) commit."""
GIT_ERROR_KEYS = ("error",)
"""Git failure marks of an identity block (``run_with_identity.git_state``)."""
MAX_PORCELAIN_LINES_SHOWN = 5


class EntryBase(StrEnum):
    """Folder the names in a checksum list are relative to."""

    SUMS_DIR = "sums-dir"
    REPO_ROOT = "repo-root"


DEFAULT_ENTRY_BASE = EntryBase.SUMS_DIR
ENTRY_BASE_LABELS = {
    EntryBase.SUMS_DIR: "목록 파일의 폴더",
    EntryBase.REPO_ROOT: "저장소 최상위(--repo, 없으면 git 작업 트리)",
}


# --- sums ---------------------------------------------------------------------


@dataclass
class EntryResult:
    """One listed file: whether it exists and how its hash compares."""

    entry: SumsEntry
    status: str  # "ok", "missing", "mismatch"
    actual_raw: str | None = None
    actual_lf: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "line": self.entry.line,
            "name": self.entry.name,
            "path": str(self.entry.path),
            "listed": self.entry.digest,
            "actual": self.actual_raw,
            "actual_lf": self.actual_lf,
            "status": self.status,
        }


def _check_entry(entry: SumsEntry) -> EntryResult:
    if not entry.path.is_file():
        return EntryResult(entry, "missing")
    data = entry.path.read_bytes()
    raw = hashlib.sha256(data).hexdigest()
    lf = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    status = "ok" if raw == entry.digest else "mismatch"
    return EntryResult(entry, status, raw, lf)


def _entry_findings(sums: SumsFile, results: list[EntryResult]) -> list[Finding]:
    findings = []
    location = str(sums.path)
    for result in results:
        entry = result.entry
        if result.status == "missing":
            message = f"목록의 파일 없음: {entry.name}"
            findings.append(
                Finding(
                    Severity.ERROR,
                    "sums_file_missing",
                    location,
                    entry.line,
                    message,
                    entry.name,
                )
            )
        elif result.status == "mismatch":
            message = (
                f"{entry.name}: 목록 {entry.digest[:SHORT_HASH_CHARS]}… ≠ "
                f"실제 {result.actual_raw[:SHORT_HASH_CHARS]}…"
            )
            if result.actual_lf == entry.digest:
                message += " (CRLF→LF 정규화 해시와는 같음: 줄바꿈만 다름)"
            findings.append(
                Finding(
                    Severity.ERROR,
                    "sums_hash_mismatch",
                    location,
                    entry.line,
                    message,
                    entry.name,
                )
            )
    return findings


def _format_findings(sums: SumsFile) -> list[Finding]:
    findings = []
    location = str(sums.path)
    if not sums.entries:
        message = "목록 항목 0개: 빈 목록은 통과가 아니다"
        findings.append(Finding(Severity.ERROR, "sums_empty", location, 0, message))
    if sums.crlf_lines:
        message = (
            f"CRLF 줄 {sums.crlf_lines}개(LF만 {sums.lone_lf_lines}개): 이 도구는 `\\r`을 떼고 "
            "읽었지만 공백으로 나누는 판독기는 마지막 이름에 `\\r`이 남는다"
        )
        findings.append(Finding(Severity.WARNING, "sums_crlf", location, 0, message))
    if sums.has_bom:
        findings.append(
            Finding(Severity.INFO, "sums_bom", location, 0, "UTF-8 BOM 있음")
        )
    for line, text in sums.malformed_lines:
        message = f"해시 줄로 읽히지 않음: {text!r}"
        findings.append(
            Finding(Severity.WARNING, "sums_malformed_line", location, line, message)
        )
    seen: dict[str, int] = {}
    for entry in sums.entries:
        key = entry.posix_name.casefold()
        if key in seen:
            message = f"{entry.name}이 두 번 나옴(처음 줄 {seen[key]})"
            findings.append(
                Finding(
                    Severity.WARNING,
                    "sums_duplicate",
                    location,
                    entry.line,
                    message,
                    entry.name,
                )
            )
        else:
            seen[key] = entry.line
    return findings


def _folder_files(folder: Path) -> list[Path]:
    files = []
    for path in sorted(folder.rglob("*")):
        relative_parts = path.relative_to(folder).parts
        if path.is_file() and not any(
            part in SKIPPED_DIR_NAMES for part in relative_parts
        ):
            files.append(path)
    return files


def _unlisted_findings(
    sums: SumsFile,
    other_lists: set[Path],
    allow_globs: list[str],
    base: EntryBase = EntryBase.SUMS_DIR,
) -> tuple[list[Finding], list[str], list[str]]:
    """Files in the list's folder that no entry names (lists themselves excepted).

    With ``--base repo-root`` the list names files anywhere in the repository, so its
    own folder is not the listed set: the files are still reported, as info
    (2026-11-21 re-audit N-6: a fixed-input list beside the run scripts gave
    ``sums_unlisted`` warnings for every neighbour and exit 1).
    """
    severity = Severity.INFO if base == EntryBase.REPO_ROOT else Severity.WARNING
    note = " - repo-root 목록이라 기록만" if base == EntryBase.REPO_ROOT else ""
    listed = {entry.path for entry in sums.entries}
    findings, unlisted, allowed = [], [], []
    for path in _folder_files(sums.folder):
        if path in listed or path == sums.path or path in other_lists:
            continue
        relative = path.relative_to(sums.folder).as_posix()
        if any(fnmatch.fnmatch(relative, pattern) for pattern in allow_globs):
            allowed.append(relative)
            continue
        unlisted.append(relative)
        message = f"목록에 없는 파일: {relative} (의도한 것이면 --allow-extra){note}"
        findings.append(
            Finding(severity, "sums_unlisted", str(sums.path), 0, message, relative)
        )
    return findings, unlisted, allowed


def _resolve_revision(revision: str | None, base: Path, git: GitQueries) -> str | None:
    """Full commit id of ``--rev``.

    Raises:
        InputError: With ``--no-git``, outside a work tree, or an unknown revision.
    """
    if revision is None:
        return None
    if not git.enabled:
        raise InputError("--rev needs git (drop --no-git)")
    root = git.toplevel(base)
    commit = git.full_commit(root, revision) if root else None
    if commit is None:
        raise InputError(f"--rev is not a commit of a work tree at {base}: {revision}")
    return commit


def _base_folder(repo: Path | None) -> Path:
    if repo is None:
        return Path.cwd()
    base = repo.expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    return base


@dataclass(frozen=True)
class EntryBaseChoice:
    """``--base`` plus what ``repo-root`` means for this run."""

    base: EntryBase
    explicit_repo: Path | None
    git: GitQueries

    def repo_root_of(self, list_path: Path) -> Path | None:
        """``--repo`` when given, else the git work tree holding the list."""
        if self.explicit_repo is not None:
            return self.explicit_repo
        if not self.git.enabled:
            return None
        return self.git.toplevel(list_path.parent)

    def folder_for(self, list_path: Path) -> Path:
        """Folder the entries of ``list_path`` are resolved against.

        Raises:
            InputError: For ``repo-root`` without ``--repo`` and outside git.
        """
        if self.base == EntryBase.SUMS_DIR:
            return list_path.parent
        root = self.repo_root_of(list_path)
        if root is None:
            raise InputError(
                f"--base repo-root needs --repo or a git work tree: {list_path}"
            )
        return root

    def other_for(self, list_path: Path) -> tuple[EntryBase, Path | None]:
        """The base not chosen and its folder (None when it cannot be found)."""
        if self.base == EntryBase.SUMS_DIR:
            return EntryBase.REPO_ROOT, self.repo_root_of(list_path)
        return EntryBase.SUMS_DIR, list_path.parent


@dataclass(frozen=True)
class BaseHint:
    """How the entries of an all-missing list fare under the other base."""

    base: EntryBase
    folder: Path
    present: int
    hash_ok: int
    entries: int

    def to_dict(self) -> dict[str, object]:
        return {
            "base": str(self.base),
            "folder": str(self.folder),
            "present": self.present,
            "hash_ok": self.hash_ok,
            "entries": self.entries,
        }


def _other_base_hint(
    sums: SumsFile, results: list[EntryResult], choice: EntryBaseChoice
) -> BaseHint | None:
    """Try the other base when every entry is missing (a wrong base looks like that)."""
    if not results or any(item.status != "missing" for item in results):
        return None
    other, folder = choice.other_for(sums.path)
    if folder is None or folder == sums.resolve_base:
        return None
    present = hash_ok = 0
    for entry in sums.entries:
        candidate = resolve_entry_name(folder, entry.name)
        if not candidate.is_file():
            continue
        present += 1
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == entry.digest:
            hash_ok += 1
    return BaseHint(other, folder, present, hash_ok, len(sums.entries))


def _hint_finding(sums: SumsFile, hint: BaseHint) -> Finding:
    if hint.present:
        message = (
            f"목록의 파일이 모두 없음: 기준 `--base {hint.base}`({hint.folder})로는 "
            f"{hint.present}/{hint.entries}개가 있고 해시 일치 {hint.hash_ok}개 — "
            "기준을 바꿔 다시 실행해 확인"
        )
    else:
        message = (
            f"목록의 파일이 모두 없음: 기준 `--base {hint.base}`({hint.folder})로도 "
            "0개 — 기준 문제가 아니라 파일이 없다"
        )
    return Finding(
        Severity.INFO, "sums_base_hint", str(sums.path), 0, message, str(hint.base)
    )


@dataclass
class SumsReport:
    """Per-list results collected for the report."""

    sums: SumsFile
    entries: list[EntryResult]
    unlisted: list[str]
    allowed_extra: list[str]
    base_hint: BaseHint | None = None

    def count(self, status: str) -> int:
        return sum(1 for item in self.entries if item.status == status)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.sums.path),
            "entry_base": str(self.sums.resolve_base),
            "base_hint": None if self.base_hint is None else self.base_hint.to_dict(),
            "entries": len(self.sums.entries),
            "crlf_lines": self.sums.crlf_lines,
            "lf_lines": self.sums.lone_lf_lines,
            "malformed_lines": len(self.sums.malformed_lines),
            "ok": self.count("ok"),
            "missing": self.count("missing"),
            "mismatch": self.count("mismatch"),
            "unlisted": self.unlisted,
            "allowed_extra": self.allowed_extra,
            "results": [item.to_dict() for item in self.entries],
        }


def _table_row(*cells: object) -> str:
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def _sums_markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 기준선 해시 목록 점검 (baseline_check sums)",
        "",
        f"- git 추적 기준: {report['tracking_basis']} ({report['git']})",
        (
            f"- 항목 경로 기준: `{report['base']}` "
            f"({ENTRY_BASE_LABELS[EntryBase(report['base'])]})"
        ),
        "",
        "| 목록 | 항목 | 일치 | 없음 | 불일치 | 목록 밖 | CRLF 줄 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report["lists"]:
        counts = (item[key] for key in ("entries", "ok", "missing", "mismatch"))
        lines.append(
            _table_row(
                f"`{item['path']}`", *counts, len(item["unlisted"]), item["crlf_lines"]
            )
        )
    problems = [
        item
        for item in report["tracking"]
        if item["tracked"] is False or item["ignore_rule"]
    ]
    lines += ["", "## git 추적", ""]
    if problems:
        lines += ["| 파일 | 역할 | 추적 | 무시 규칙 |", "|---|---|---|---|"]
        lines += [
            _table_row(
                f"`{item['relative'] or item['path']}`",
                item["role"],
                item["tracked"],
                item["ignore_rule"] or "-",
            )
            for item in problems
        ]
    else:
        lines.append("추적 안 함·무시 규칙 해당 없음(git을 쓰지 않았으면 확인 안 함).")
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def run_sums(args: argparse.Namespace) -> ToolOutcome:
    """Verify checksum lists: hashes, unlisted files, line ends and git tracking."""
    base = _base_folder(args.repo)
    paths = expand_file_patterns(args.lists, base)
    require_output_outside(args.out, paths)
    git = GitQueries(enabled=not args.no_git)
    revision = _resolve_revision(args.rev, base, git)
    choice = EntryBaseChoice(
        EntryBase(args.base), base if args.repo is not None else None, git
    )
    lists = [parse_sums_file(path, choice.folder_for(path)) for path in paths]
    list_paths = set(paths)

    findings: list[Finding] = []
    reports: list[SumsReport] = []
    cited: list[CitedFile] = []
    for sums in lists:
        results = [_check_entry(entry) for entry in sums.entries]
        unlisted_findings, unlisted, allowed = _unlisted_findings(
            sums, list_paths, args.allow_extra or [], choice.base
        )
        findings += (
            _format_findings(sums) + _entry_findings(sums, results) + unlisted_findings
        )
        hint = _other_base_hint(sums, results, choice)
        if hint is not None:
            findings.append(_hint_finding(sums, hint))
        reports.append(SumsReport(sums, results, unlisted, allowed, hint))
        cited.append(CitedFile(sums.path, "sums_list"))
        cited += [
            CitedFile(item.entry.path, "sums_entry")
            for item in results
            if item.status != "missing"
        ]
    tracking = collect_track_facts(cited, git, revision)
    findings += track_findings(tracking, revision, SUMS_ROLES, git.enabled)
    findings = sort_findings(findings)

    summary = {
        "tool": TOOL_NAME,
        "command": "sums",
        "base": str(choice.base),
        "lists": len(lists),
        "entries": sum(len(sums.entries) for sums in lists),
        "mismatch": sum(item.count("mismatch") for item in reports),
        "missing": sum(item.count("missing") for item in reports),
        "unlisted": sum(len(item.unlisted) for item in reports),
        "crlf_lines": sum(sums.crlf_lines for sums in lists),
        "cited_untracked": sum(1 for item in tracking if item.tracked is False),
        "cited_ignored": sum(
            1 for item in tracking if item.tracked is False and item.ignore_rule
        ),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "command": "sums",
        "repo": str(base),
        "git": git.unavailable_reason or "used",
        "tracking_basis": f"commit {revision}" if revision else "index",
        "base": str(choice.base),
        "lists": [item.to_dict() for item in reports],
        "tracking": [item.to_dict() for item in tracking],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _sums_markdown(report, findings), report, paths)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


# --- identity -----------------------------------------------------------------


@dataclass(frozen=True)
class GitBlock:
    """One ``"git": {...}`` block of an identity file and the run time beside it."""

    file: Path
    json_path: str
    head: str | None
    is_clean: bool | None
    porcelain: str | None
    run_time: str | None
    git_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "file": str(self.file),
            "json_path": self.json_path,
            "head": self.head,
            "is_clean": self.is_clean,
            "status_porcelain": self.porcelain,
            "run_time": self.run_time,
            "git_error": self.git_error,
        }


def _run_time_of(owner: dict[str, object]) -> str | None:
    for key in RUN_TIME_KEYS:
        value = owner.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _git_error_of(block: dict[str, object]) -> str | None:
    """The git failure mark of a block (None: no mark)."""
    for key in GIT_ERROR_KEYS:
        value = block.get(key)
        if value:
            return str(value)
    return None


def _is_full_commit(head: str) -> bool:
    return len(head) in FULL_COMMIT_LENGTHS and all(
        char in "0123456789abcdef" for char in head.lower()
    )


def _git_blocks(file: Path, document: object, json_path: str = "$") -> list[GitBlock]:
    """Every ``"git"`` dict below ``document``, depth first, in file order."""
    blocks: list[GitBlock] = []
    if isinstance(document, dict):
        block = document.get(GIT_BLOCK_KEY)
        if isinstance(block, dict):
            head = block.get("head")
            is_clean = block.get("is_clean")
            porcelain = block.get("status_porcelain")
            blocks.append(
                GitBlock(
                    file,
                    f"{json_path}.{GIT_BLOCK_KEY}",
                    head if isinstance(head, str) else None,
                    is_clean if isinstance(is_clean, bool) else None,
                    porcelain if isinstance(porcelain, str) else None,
                    _run_time_of(document),
                    _git_error_of(block),
                )
            )
        for key, value in document.items():
            if key != GIT_BLOCK_KEY:
                blocks += _git_blocks(file, value, f"{json_path}.{key}")
    elif isinstance(document, list):
        for index, value in enumerate(document):
            blocks += _git_blocks(file, value, f"{json_path}[{index}]")
    return blocks


def _identity_files(args: argparse.Namespace, base: Path) -> list[Path]:
    files: list[Path] = []
    for text in args.paths:
        candidate = (base / Path(text).expanduser()).resolve()
        if candidate.is_dir():
            files += sorted(
                path for path in candidate.glob(args.glob) if path.is_file()
            )
        else:
            files += expand_file_patterns([text], base)
    if not files:
        raise InputError(
            f"no identity files found (glob {args.glob!r}): "
            "an empty baseline is not a pass"
        )
    return list(dict.fromkeys(files))


def _load_json(path: Path) -> object:
    try:
        text, _ = decode_bytes(path.read_bytes())
        return json.loads(text)
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise InputError(f"not JSON: {path}: {error}") from error


def _heads_match(head: str, expected: str) -> bool:
    """A full recorded head starts with the expected commit (a prefix is allowed only on the
    expected side: an empty or short head never matches)."""
    return head.lower().startswith(expected.lower())


def _block_findings(block: GitBlock, expected: str | None) -> list[Finding]:
    findings = []
    location, target = str(block.file), block.json_path
    if block.git_error is not None:
        message = f"git 조회 실패 표지: {block.git_error[:120]}"
        findings.append(
            Finding(Severity.ERROR, "identity_git_error", location, 0, message, target)
        )
    if block.head is None:
        findings.append(
            Finding(
                Severity.ERROR,
                "baseline_head_missing",
                location,
                0,
                "git.head 없음",
                target,
            )
        )
    elif not _is_full_commit(block.head):
        message = (
            f"git.head {block.head[:SHORT_HASH_CHARS]!r}는 전체 커밋 해시가 아님"
            " (빈 값 = git 조회 실패; is_clean 값과 무관하게 정체성 없음)"
        )
        findings.append(
            Finding(Severity.ERROR, "baseline_head_invalid", location, 0, message, target)
        )
    elif expected and not _heads_match(block.head, expected):
        message = f"git.head {block.head[:SHORT_HASH_CHARS]} ≠ 기대 {expected[:SHORT_HASH_CHARS]}"
        findings.append(
            Finding(
                Severity.ERROR, "baseline_head_mismatch", location, 0, message, target
            )
        )
    if block.is_clean is False:
        changed = [
            line for line in (block.porcelain or "").splitlines() if line.strip()
        ]
        shown = "; ".join(changed[:MAX_PORCELAIN_LINES_SHOWN]) or "(목록 없음)"
        message = f"is_clean false: 깨끗하지 않은 트리에서 만든 기준선 — 변경 {len(changed)}줄: {shown}"
        findings.append(
            Finding(Severity.ERROR, "baseline_dirty", location, 0, message, target)
        )
    elif block.is_clean is None:
        message = "git.is_clean 없음: 트리가 깨끗했는지 모름"
        findings.append(
            Finding(
                Severity.WARNING, "baseline_clean_unknown", location, 0, message, target
            )
        )
    elif block.porcelain and block.porcelain.strip():
        message = "is_clean true인데 status_porcelain이 비어 있지 않음"
        findings.append(
            Finding(
                Severity.WARNING,
                "baseline_clean_inconsistent",
                location,
                0,
                message,
                target,
            )
        )
    return findings


def _parse_run_time(text: str | None) -> datetime | None:
    if not text:
        return None
    for time_format in IDENTITY_TIME_FORMATS:
        try:
            return datetime.strptime(text, time_format)
        except ValueError:
            continue
    return parse_time(text)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.astimezone()


@dataclass
class MtimeCheck:
    """Result of the optional ``--mtime`` check."""

    commit: str | None = None
    commit_time: str | None = None
    earliest_run: str | None = None
    changed_files: int = 0
    late_files: list[dict[str, object]] = field(default_factory=list)
    note: str = ""


def _mtime_findings(
    blocks: list[GitBlock], commit_text: str | None, base: Path, git: GitQueries
) -> tuple[MtimeCheck, list[Finding]]:
    """Files the baseline commit changed whose mtime is later than the commit."""
    check = MtimeCheck()
    root = git.toplevel(base) if git.enabled else None
    if root is None or commit_text is None:
        check.note = "git 작업 트리·기준 커밋이 없어 mtime 검사를 하지 않음"
        return check, []
    check.commit = git.full_commit(root, commit_text)
    commit_time = (
        parse_time(git.commit_time(root, check.commit)) if check.commit else None
    )
    changed = git.changed_files(root, check.commit) if check.commit else None
    if commit_time is None or changed is None:
        check.note = f"커밋 {commit_text}의 시각·변경 파일을 읽지 못함"
        return check, []
    check.commit_time = commit_time.isoformat()
    check.changed_files = len(changed)
    run_times = [
        moment for block in blocks if (moment := _parse_run_time(block.run_time))
    ]
    earliest_run = min((_aware(moment) for moment in run_times), default=None)
    check.earliest_run = earliest_run.isoformat() if earliest_run else None
    findings = []
    for relative in changed:
        path = root / relative
        if not path.is_file():
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        if modified <= commit_time:
            continue
        before_run = earliest_run is not None and modified < earliest_run
        same_now = git.same_as_commit(root, check.commit, relative)
        check.late_files.append(
            {
                "path": relative,
                "mtime": modified.isoformat(timespec="seconds"),
                "before_run": before_run,
                "same_as_commit_now": same_now,
            }
        )
        if before_run or earliest_run is None:
            content_note = {
                True: "지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)",
                False: "지금 내용도 커밋과 다르다",
                None: "내용 비교 못 함",
            }[same_now]
            message = (
                f"{relative}: mtime {modified:%Y-%m-%d %H:%M:%S}이 커밋 뒤"
                + (
                    f", 실행 시작 {earliest_run:%Y-%m-%d %H:%M:%S} 전"
                    if before_run
                    else ""
                )
                + f": 실행이 커밋과 다른 내용을 읽었을 수 있다({content_note})"
            )
            findings.append(
                Finding(
                    Severity.WARNING,
                    "mtime_after_commit_before_run",
                    str(path),
                    0,
                    message,
                )
            )
        else:
            message = f"{relative}: mtime이 커밋과 실행 시작 뒤(이후 편집·체크아웃)"
            findings.append(
                Finding(Severity.INFO, "mtime_after_commit", str(path), 0, message)
            )
    return check, findings


def _identity_markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    lines = [
        "# 기준선 실행 정체성 점검 (baseline_check identity)",
        "",
        f"- 파일 {len(report['files'])}개, git 블록 {len(report['blocks'])}개, "
        f"기대 커밋 {report['expect_commit'] or '(없음: 전부 같은지만 봄)'}",
        f"- head 값: {', '.join(report['heads']) or '-'}",
        "",
        "| 파일 | 위치 | head | is_clean | 실행 시각 |",
        "|---|---|---|---|---|",
    ]
    for block in report["blocks"]:
        head = (block["head"] or "-")[:SHORT_HASH_CHARS]
        lines.append(
            f"| `{Path(block['file']).name}` | `{block['json_path']}` | {head} "
            f"| {block['is_clean']} | {block['run_time'] or '-'} |"
        )
    mtime = report.get("mtime")
    if mtime:
        lines += [
            "",
            "## mtime 검사",
            "",
            f"- 커밋 {mtime['commit'] or '-'} 시각 {mtime['commit_time'] or '-'}, "
            f"변경 파일 {mtime['changed_files']}개, 가장 이른 실행 {mtime['earliest_run'] or '-'}",
            f"- 커밋 뒤에 바뀐 파일 {len(mtime['late_files'])}개 {mtime['note']}",
        ]
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def run_identity(args: argparse.Namespace) -> ToolOutcome:
    """Check head, clean tree and (optionally) mtimes of the identity files."""
    base = _base_folder(args.repo)
    files = _identity_files(args, base)
    require_output_outside(args.out, files, [path.parent for path in files])
    git = GitQueries(enabled=not args.no_git)

    blocks: list[GitBlock] = []
    findings: list[Finding] = []
    for path in files:
        found = _git_blocks(path, _load_json(path))
        if not found:
            message = 'git 블록(`"git": {"head", "is_clean"}`)이 없음: 정체성을 확인할 수 없다'
            findings.append(
                Finding(Severity.ERROR, "identity_git_absent", str(path), 0, message)
            )
        blocks += found
    for block in blocks:
        findings += _block_findings(block, args.expect_commit)
    heads = sorted(
        {block.head for block in blocks if block.head and _is_full_commit(block.head)}
    )
    if not args.expect_commit and len(heads) > 1:
        message = f"git.head가 {len(heads)}가지: {', '.join(head[:SHORT_HASH_CHARS] for head in heads)}"
        findings.append(
            Finding(Severity.ERROR, "baseline_head_mixed", str(files[0]), 0, message)
        )

    mtime_check: MtimeCheck | None = None
    if args.mtime:
        commit_text = args.expect_commit or (heads[0] if len(heads) == 1 else None)
        mtime_check, mtime_findings = _mtime_findings(blocks, commit_text, base, git)
        findings += mtime_findings
    findings = sort_findings(findings)

    summary = {
        "tool": TOOL_NAME,
        "command": "identity",
        "files": len(files),
        "git_blocks": len(blocks),
        "heads": len(heads),
        "dirty": sum(1 for block in blocks if block.is_clean is False),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "command": "identity",
        "expect_commit": args.expect_commit,
        "files": [str(path) for path in files],
        "heads": heads,
        "blocks": [block.to_dict() for block in blocks],
        "mtime": None if mtime_check is None else asdict(mtime_check),
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _identity_markdown(report, findings), report, files)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


# --- command line -------------------------------------------------------------


def _validate_expect_commit(text: str | None) -> None:
    if text is None:
        return
    is_hex = all(character in "0123456789abcdefABCDEF" for character in text)
    if len(text) < MIN_COMMIT_PREFIX_CHARS or not is_hex:
        raise InputError(
            f"--expect-commit needs at least {MIN_COMMIT_PREFIX_CHARS} hex "
            f"characters: {text!r}"
        )


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo",
        type=Path,
        help="base folder for relative paths (default: current folder)",
    )
    parser.add_argument("--no-git", action="store_true", help="never start git")
    add_report_arguments(parser)


def build_parser() -> argparse.ArgumentParser:
    """Return the parser with the ``sums`` and ``identity`` subcommands."""
    parser = argparse.ArgumentParser(
        prog="baseline_check.py",
        description="봉인 기준선 폴더의 해시 목록(SHA256SUMS)과 실행 정체성을 점검한다(읽기 전용).",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    sums = commands.add_parser("sums", help="목록 해시·목록 밖 파일·CRLF·git 추적")
    sums.add_argument("lists", nargs="+", help="SHA256SUMS files or glob patterns")
    sums.add_argument("--rev", help="check tracked state against this commit's tree")
    sums.add_argument(
        "--base",
        choices=[str(item) for item in EntryBase],
        default=str(DEFAULT_ENTRY_BASE),
        help="folder the listed names are relative to: the list's folder "
        f"(default {DEFAULT_ENTRY_BASE}) or the repository root (--repo, else git)",
    )
    sums.add_argument(
        "--allow-extra",
        action="append",
        metavar="GLOB",
        help="files in the list's folder that need not be listed "
        "(relative glob, repeatable)",
    )
    _add_common(sums)

    identity = commands.add_parser("identity", help="git.head·is_clean·mtime")
    identity.add_argument(
        "paths", nargs="+", help="baseline folders or identity json files"
    )
    identity.add_argument(
        "--glob",
        default=DEFAULT_IDENTITY_GLOB,
        help=f"identity files inside a folder (default {DEFAULT_IDENTITY_GLOB})",
    )
    identity.add_argument(
        "--expect-commit", help="commit every git.head must equal (prefix ok)"
    )
    identity.add_argument(
        "--mtime",
        action="store_true",
        help="report files the commit changed whose mtime is after the commit "
        "(needs git)",
    )
    _add_common(identity)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    if args.command == "sums":
        return run_tool(lambda: run_sums(args))

    def identity_work() -> ToolOutcome:
        _validate_expect_commit(args.expect_commit)
        return run_identity(args)

    return run_tool(identity_work)


if __name__ == "__main__":
    sys.exit(main())
