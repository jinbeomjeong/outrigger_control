"""Reference check (I axis): do the files a spec names exist in the repository tree?

2026-11-16: a sealed spec named ``dg3_keys.txt`` as an input; the file was not in
the repository (the real key list was ``judge_932f1fb/harness_path1/dg3_hash.json``)
and nothing caught it before the run.

For every Markdown document the tool reads the inline code spans (backticks;
fenced blocks only with ``--include-fences``), keeps the tokens that look like a
file or folder (a known extension, ``SHA256SUMS``, or a trailing ``/``), drops
templates (``<run>``, ``{BATCH}``, ``$scratch``) and resolves each token in the
repository tree of ``--rev`` (default ``HEAD``, ``git ls-tree -r``), in order:

1. relative to the repository root;
2. relative to the document's folder;
3. as a path suffix (``02_chrono/x.py`` matches ``04_scripts/02_chrono/x.py``)
   or, for a bare name, by file name anywhere;
4. as a folder (a tracked path starts with it); a glob token by ``fnmatch``.

Not found -> a case-insensitive match is ``ref_case_mismatch``; a file only in
the work tree (not in the commit) is ``ref_untracked``; otherwise ``ref_missing``
with up to ``--max-candidates`` tracked files whose name stem is similar.

Usage:
    python ref_check.py DOC_OR_GLOB [...] [--repo DIR] [--rev HEAD]
        [--include-fences] [--allow REGEX ...] [--max-candidates 5] [--no-git]
        [--out REPORT] [--format md|json] [--fail-on error|warning]

Exit codes: 0 nothing at ``--fail-on`` level, 1 findings, 2 input error, 3 bug.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import math
import os
import posixpath
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import (
    SKIPPED_DIR_NAMES,
    expand_file_patterns,
    read_text_facts,
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

TOOL_NAME = "ref_check"
DEFAULT_REVISION = "HEAD"
DEFAULT_MAX_CANDIDATES = 5
KNOWN_EXTENSIONS = frozenset(
    {
        "py", "md", "json", "jsonl", "npz", "npy", "csv", "tsv", "txt", "yaml", "yml",
        "toml", "cfg", "ini", "ps1", "sh", "bat", "cmd", "sha256", "h5", "hdf5", "mat",
        "xlsx", "log", "done", "ipynb", "png", "svg", "pdf", "hwp", "hwpx", "docx",
        "pptx", "stp", "step", "graphml", "tex", "bib", "zip", "parquet", "pkl", "dll",
    }
)  # fmt: skip
KNOWN_NAMES = frozenset({"SHA256SUMS", "Makefile", "README", "LICENSE"})
INLINE_CODE_PATTERN = re.compile(r"(`+)(?P<code>.+?)\1")
FENCE_PATTERN = re.compile(r"^\s{0,3}(```|~~~)")
TEMPLATE_CHARACTERS = frozenset("<>{}$%…")
# `x.py:79·184`, `x.py:12-30`, `x.md#L12`, `test_x.py::test_name`.
LOCATION_SUFFIX_PATTERN = re.compile(r"(::.*|#L?\d.*|:[\d·,~\-]+)$")
LEADING_PUNCTUATION = "\"'([{"
TRAILING_PUNCTUATION = "\"')]},;.:!?"
ABSOLUTE_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]{2}|~[\\/]|/)")
URL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
STEM_SPLIT_PATTERN = re.compile(r"[_\-. ]+")
MIN_SHARED_TOKEN_CHARS = 3
MIN_STEM_RATIO = 0.5
SCORE_RATIO_SHARE = 0.5


@dataclass
class Reference:
    """One cited path token of one document (first line, how often)."""

    document: Path
    line: int
    token: str
    normalized: str
    count: int = 1
    status: str = "unchecked"  # ok, case_mismatch, untracked, missing
    resolved: list[str] = field(default_factory=list)
    how: str = ""
    candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "document": str(self.document),
            "line": self.line,
            "token": self.token,
            "normalized": self.normalized,
            "count": self.count,
            "status": self.status,
            "how": self.how,
            "resolved": self.resolved[:5],
            "candidates": self.candidates,
        }


@dataclass
class ExtractionStats:
    """Tokens seen but not checked, by reason."""

    templates: int = 0
    external: int = 0
    allowed: int = 0


# --- extraction ---------------------------------------------------------------


def _code_spans(text: str, include_fences: bool) -> list[tuple[int, str]]:
    """``(line, span text)`` of inline code (and fenced lines when asked)."""
    spans: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            if include_fences:
                spans.append((number, line))
            continue
        spans += [
            (number, match.group("code"))
            for match in INLINE_CODE_PATTERN.finditer(line)
        ]
    return spans


def _clean_token(raw: str) -> str:
    """Strip quotes, brackets, sentence punctuation and a ``:line``/``#L`` suffix."""
    token = raw.strip().lstrip(LEADING_PUNCTUATION).rstrip(TRAILING_PUNCTUATION)
    token = LOCATION_SUFFIX_PATTERN.sub("", token)
    return token.rstrip(TRAILING_PUNCTUATION)


def _looks_like_file(token: str) -> bool:
    if token.endswith(("/", "\\")) and len(token) > 1:
        return True
    name = re.split(r"[\\/]", token)[-1]
    if name in KNOWN_NAMES:
        return True
    stem, dot, extension = name.rpartition(".")
    return bool(dot and stem and extension.lower() in KNOWN_EXTENSIONS)


def _normalize(token: str) -> str:
    text = token.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


@dataclass(frozen=True)
class ExtractionOptions:
    """What to read and what to skip when collecting references."""

    include_fences: bool
    allow: tuple[re.Pattern[str], ...]
    repo_root: Path


def _checked_form(
    raw: str, options: ExtractionOptions, stats: ExtractionStats
) -> tuple[str, str] | None:
    """``(token, repository-relative form)`` of a path-like word, else ``None``.

    Templates, ``--allow`` matches and paths outside the repository are counted
    in ``stats`` and skipped.
    """
    token = _clean_token(raw)
    if not token or URL_PATTERN.match(token) or not _looks_like_file(token):
        return None
    if any(character in TEMPLATE_CHARACTERS for character in token):
        stats.templates += 1
        return None
    if any(pattern.search(token) for pattern in options.allow):
        stats.allowed += 1
        return None
    normalized = _repo_relative(token, options.repo_root)
    if normalized is None:
        stats.external += 1
        return None
    return token, normalized


def extract_references(
    document: Path, text: str, options: ExtractionOptions, stats: ExtractionStats
) -> list[Reference]:
    """Path-like tokens of one document, one :class:`Reference` per distinct token."""
    found: dict[str, Reference] = {}
    for line, span in _code_spans(text, options.include_fences):
        for raw in span.split():
            checked = _checked_form(raw, options, stats)
            if checked is None:
                continue
            token, normalized = checked
            if normalized in found:
                found[normalized].count += 1
            else:
                found[normalized] = Reference(document, line, token, normalized)
    return list(found.values())


def _repo_relative(token: str, repo_root: Path) -> str | None:
    """Repository-relative form of an absolute token, the token itself if relative."""
    if not ABSOLUTE_PATTERN.match(token):
        return _normalize(token)
    absolute = Path(os.path.expanduser(token))
    try:
        relative = os.path.relpath(absolute, repo_root)
    except ValueError:  # another drive
        return None
    if relative.startswith(".."):
        return None
    suffix = "/" if token.endswith(("/", "\\")) else ""
    return _normalize(relative) + suffix


# --- the tree index -----------------------------------------------------------


@dataclass
class TreeIndex:
    """Tracked paths of one revision with lookups by path, name and folder."""

    paths: set[str]
    folded: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_name: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    folders: set[str] = field(default_factory=set)
    # stem part -> number of distinct file names that contain it
    part_frequency: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @classmethod
    def build(cls, paths: list[str]) -> TreeIndex:
        index = cls(set(paths))
        for path in paths:
            name = posixpath.basename(path)
            index.folded[path.casefold()].append(path)
            if name not in index.by_name:
                for part in _stem_tokens(_stem_of(name)):
                    index.part_frequency[part] += 1
            index.by_name[name].append(path)
            folder = posixpath.dirname(path)
            while folder and folder not in index.folders:
                index.folders.add(folder)
                folder = posixpath.dirname(folder)
        return index

    def suffix_matches(self, token: str) -> list[str]:
        name = posixpath.basename(token)
        if "/" not in token:
            return list(self.by_name.get(name, []))
        tail = "/" + token
        return [
            path
            for path in self.by_name.get(name, [])
            if path.endswith(tail) or path == token
        ]

    def folder_matches(self, token: str) -> list[str]:
        folder = token.rstrip("/")
        if folder in self.folders:
            return [folder]
        tail = "/" + folder
        return sorted(item for item in self.folders if item.endswith(tail))

    def glob_matches(self, token: str) -> list[str]:
        return sorted(
            path
            for path in self.paths
            if fnmatch.fnmatchcase(path, token)
            or fnmatch.fnmatchcase(path, f"*/{token}")
        )


def _tree_from_git(repo_root: Path, revision: str, git: GitQueries) -> list[str]:
    root = git.toplevel(repo_root)
    if root is None:
        raise InputError(
            f"not a git work tree (use --no-git to read the folder): {repo_root}"
        )
    paths = git.tree_paths(root, revision)
    if paths is None:
        raise InputError(f"cannot list the tree of {revision!r} in {root}")
    if not paths:
        raise InputError(
            f"the tree of {revision!r} is empty: nothing to resolve against"
        )
    return paths


def _load_tree(
    args: argparse.Namespace, repo_root: Path
) -> tuple[str, list[str], Path]:
    """``(label, tracked paths, root)``; with git the root is the work-tree root."""
    if args.no_git:
        return "작업 트리(--no-git)", _tree_from_disk(repo_root), repo_root
    git = GitQueries()
    paths = _tree_from_git(repo_root, args.rev, git)
    # The tree paths are relative to the work-tree root, which --repo may be below.
    root = git.toplevel(repo_root) or repo_root
    return f"git {args.rev}", paths, root


def _tree_from_disk(repo_root: Path) -> list[str]:
    paths = []
    for path in repo_root.rglob("*"):
        relative = path.relative_to(repo_root)
        if path.is_file() and not any(
            part in SKIPPED_DIR_NAMES for part in relative.parts
        ):
            paths.append(relative.as_posix())
    return paths


# --- resolution ---------------------------------------------------------------


def _document_relative(reference: Reference, repo_root: Path) -> str | None:
    try:
        folder = reference.document.parent.relative_to(repo_root).as_posix()
    except ValueError:
        return None
    joined = posixpath.normpath(posixpath.join(folder, reference.normalized))
    return None if joined.startswith("..") else joined


def _exact_matches(
    reference: Reference, index: TreeIndex, repo_root: Path
) -> tuple[list[str], str]:
    token = reference.normalized
    if token.endswith("/"):
        return index.folder_matches(token), "folder"
    if any(character in token for character in "*?["):
        return index.glob_matches(token), "glob"
    if token in index.paths:
        return [token], "root"
    document_relative = _document_relative(reference, repo_root)
    if document_relative and document_relative in index.paths:
        return [document_relative], "document"
    matches = index.suffix_matches(token)
    if matches:
        return matches, "suffix" if "/" in token else "name"
    return index.folder_matches(token), "folder"


def _case_matches(reference: Reference, index: TreeIndex) -> list[str]:
    folded = reference.normalized.casefold()
    exact = index.folded.get(folded, [])
    if exact:
        return exact
    tail = "/" + folded
    return sorted(path for path in index.paths if path.casefold().endswith(tail))


def _exists_on_disk(reference: Reference, repo_root: Path) -> str | None:
    candidates = [
        repo_root / reference.normalized,
        reference.document.parent / reference.normalized,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _stem_tokens(stem: str) -> set[str]:
    return {
        part
        for part in STEM_SPLIT_PATTERN.split(stem.lower())
        if len(part) >= MIN_SHARED_TOKEN_CHARS
    }


def _stem_of(name: str) -> str:
    return name.rsplit(".", 1)[0].lower()


def similar_files(token: str, index: TreeIndex, limit: int) -> list[str]:
    """Tracked files whose name stem resembles the token's.

    Score = half the difflib ratio of the stems + half the share of the token's
    stem parts (``dg3``, ``keys``) found in the candidate, each part weighted by
    rarity: a rare part such as ``dg3`` says more than a common one such as ``keys``.
    """
    stem = _stem_of(posixpath.basename(token.rstrip("/")))
    wanted_parts = _stem_tokens(stem)
    part_weight = {
        part: 1.0 / math.log2(2 + index.part_frequency.get(part, 0))
        for part in wanted_parts
    }
    total_weight = sum(part_weight.values()) or 1.0
    scored: list[tuple[float, str]] = []
    matcher = difflib.SequenceMatcher(b=stem)
    for candidate_name, paths in index.by_name.items():
        candidate_stem = _stem_of(candidate_name)
        shared = wanted_parts & _stem_tokens(candidate_stem)
        matcher.set_seq1(candidate_stem)
        if not shared and matcher.quick_ratio() < MIN_STEM_RATIO:
            continue
        ratio = matcher.ratio()
        if not shared and ratio < MIN_STEM_RATIO:
            continue
        overlap = sum(part_weight[part] for part in shared) / total_weight
        score = SCORE_RATIO_SHARE * ratio + (1 - SCORE_RATIO_SHARE) * overlap
        scored += [(score, path) for path in paths]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in scored[:limit]]


def resolve(
    reference: Reference, index: TreeIndex, repo_root: Path, limit: int
) -> None:
    """Fill ``status``, ``resolved``, ``how`` and ``candidates`` of one reference."""
    matches, how = _exact_matches(reference, index, repo_root)
    if matches:
        reference.status, reference.resolved, reference.how = "ok", matches, how
        return
    case_matches = _case_matches(reference, index)
    if case_matches:
        reference.status, reference.resolved, reference.how = (
            "case_mismatch",
            case_matches,
            "casefold",
        )
        return
    on_disk = _exists_on_disk(reference, repo_root)
    if on_disk:
        reference.status, reference.resolved, reference.how = (
            "untracked",
            [on_disk],
            "disk",
        )
        return
    reference.status = "missing"
    reference.candidates = similar_files(reference.normalized, index, limit)


def _reference_finding(reference: Reference, revision_label: str) -> Finding | None:
    location = (str(reference.document), reference.line)
    if reference.status == "case_mismatch":
        message = f"`{reference.token}`: 대소문자만 다른 파일 {', '.join(reference.resolved[:3])}"
        return Finding(
            Severity.WARNING, "ref_case_mismatch", *location, message, reference.token
        )
    if reference.status == "untracked":
        message = (
            f"`{reference.token}`: 작업 트리에만 있고 {revision_label}에 없음(새 체크아웃·다른 "
            f"worktree에는 없다): {reference.resolved[0]}"
        )
        return Finding(
            Severity.WARNING, "ref_untracked", *location, message, reference.token
        )
    if reference.status == "missing":
        candidates = ", ".join(f"`{path}`" for path in reference.candidates) or "없음"
        message = f"`{reference.token}`: {revision_label}에도 작업 트리에도 없음. 비슷한 이름: {candidates}"
        return Finding(
            Severity.ERROR, "ref_missing", *location, message, reference.token
        )
    return None


# --- report -------------------------------------------------------------------


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    lines = [
        "# 명세 참조 경로 점검 (ref_check)",
        "",
        f"- 기준 트리: {report['tree']} (파일 {report['tree_files']}개)",
        f"- 문서 {summary['documents']}개, 참조 {summary['references']}개: 확인 {summary['resolved']}, "
        f"없음 {summary['missing']}, 작업 트리에만 {summary['untracked']}, 대소문자 {summary['case_mismatch']}",
        f"- 확인하지 않은 토큰: 자리표시 {summary['templates']}, 저장소 밖 {summary['external']}, "
        f"--allow {summary['allowed']}",
        "",
        "| 문서:줄 | 참조 | 결과 | 찾은 방법 | 찾은 곳·후보 |",
        "|---|---|---|---|---|",
    ]
    for item in report["references"]:
        where = (
            ", ".join(item["resolved"][:2]) or ", ".join(item["candidates"][:3]) or "-"
        )
        location = f"`{Path(item['document']).name}`:{item['line']}"
        token = item["token"].replace("|", "\\|")
        cells = (location, f"`{token}`", item["status"], item["how"] or "-", where)
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## 발견 사항", "", *findings_markdown(findings)]
    return lines


def run_ref_check(args: argparse.Namespace) -> ToolOutcome:
    """Resolve the path tokens of the given documents in the repository tree."""
    if args.max_candidates < 0:
        raise InputError("--max-candidates must not be negative")
    repo_root = Path(args.repo).expanduser().resolve() if args.repo else Path.cwd()
    if not repo_root.is_dir():
        raise InputError(f"--repo is not a folder: {repo_root}")
    try:
        allow = [re.compile(pattern) for pattern in args.allow or []]
    except re.error as error:
        raise InputError(f"invalid --allow regex: {error}") from error
    documents = expand_file_patterns(args.documents, repo_root)
    require_output_outside(args.out, documents)
    tree_label, tree_paths, repo_root = _load_tree(args, repo_root)
    index = TreeIndex.build(tree_paths)

    stats = ExtractionStats()
    options = ExtractionOptions(args.include_fences, tuple(allow), repo_root)
    references: list[Reference] = []
    for document in documents:
        text = read_text_facts(document).text
        references += extract_references(document, text, options, stats)
    findings = []
    for reference in references:
        resolve(reference, index, repo_root, args.max_candidates)
        finding = _reference_finding(reference, tree_label)
        if finding is not None:
            findings.append(finding)
    findings = sort_findings(findings)

    def count(status: str) -> int:
        return sum(1 for item in references if item.status == status)

    summary = {
        "tool": TOOL_NAME,
        "command": "check",
        "documents": len(documents),
        "references": len(references),
        "resolved": count("ok"),
        "missing": count("missing"),
        "untracked": count("untracked"),
        "case_mismatch": count("case_mismatch"),
        "templates": stats.templates,
        "external": stats.external,
        "allowed": stats.allowed,
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "repo": str(repo_root),
        "tree": tree_label,
        "tree_files": len(tree_paths),
        "references": [item.to_dict() for item in references],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(report, findings), report, documents)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="ref_check.py",
        description="명세(md)가 백틱으로 가리킨 파일·폴더가 저장소 트리에 있는지 본다(읽기 전용).",
    )
    parser.add_argument("documents", nargs="+", help="Markdown files or glob patterns")
    parser.add_argument("--repo", help="repository folder (default: current folder)")
    parser.add_argument(
        "--rev",
        default=DEFAULT_REVISION,
        help=f"tree to resolve in (default {DEFAULT_REVISION})",
    )
    parser.add_argument(
        "--include-fences", action="store_true", help="also read fenced code blocks"
    )
    parser.add_argument(
        "--allow", action="append", metavar="REGEX", help="tokens to skip (repeatable)"
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=DEFAULT_MAX_CANDIDATES,
        help="similar file names listed per missing reference "
        f"(default {DEFAULT_MAX_CANDIDATES})",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="resolve in the folder on disk instead of a git tree",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_ref_check(args))


if __name__ == "__main__":
    sys.exit(main())
