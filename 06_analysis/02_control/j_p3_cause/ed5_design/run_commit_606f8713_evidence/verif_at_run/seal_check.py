"""Seal check (S axis): rule files, their ``.sha256`` seals, code pins, EOL protection.

For every rule edition (original ``<stem>.md`` and, with ``--revs auto``, the
``<stem>_rev<N>.md`` addenda in numeric order) the tool

* hashes the bytes as stored (``raw``) and with CRLF folded to LF (``lf``) and
  compares both with the first token of ``<file stem>.sha256``;
* reports CRLF, BOM and a missing final newline in the rule and seal files;
* asks ``git check-attr text eol`` (fallback: reads ``.gitattributes`` itself)
  whether each file is protected: ``-text`` (conversion off) or ``eol=lf``
  (LF checkout forced; reported as info ``attr_protected_eol_lf``);
* records per rule and seal file: ``git ls-files --eol``, tracked or not, the
  last commit time and the mtime; ``core.autocrlf`` true/input turns a missing
  protection on a rule edition into an error;
* with ``--code``, finds which editions each Python file pins - by a 64-hex
  constant equal to a seal or file hash, or by naming the edition file in a
  (non-docstring) string literal - and which editions it leaves unpinned;
* with ``--const FILE:NAME``, compares the 64-hex value(s) of one named constant
  with every edition hash;
* with ``--quoted DOC``, resolves hex runs (8-64 characters) quoted in a document
  as prefixes of edition, seal or ``--hash-files`` hashes (else: a commit?);
* checks that every cited file (editions, seals, ``--hash-files``, ``--sums``
  lists and the files they name) is in git: an untracked file matched by an
  ignore rule is ``cited_ignored``; untracked ``--sums`` entries (and, with
  ``--check-tracked``, any cited file) are ``cited_untracked``. ``--rev`` checks
  against a commit's tree instead of the index.

A seal is ``<stem>.sha256`` or, when that is absent, ``<name>.sha256``
(``spec.md.sha256``). Rule arguments may be glob patterns (``**`` allowed);
relative paths and patterns are taken from ``--repo`` (default: the current folder).

Usage:
    python seal_check.py RULE_OR_GLOB [...] [--repo DIR] [--revs auto|none]
                         [--sha-dir DIR] [--code PATH ...] [--const FILE:NAME ...]
                         [--quoted DOC ...] [--hash-files GLOB ...] [--sums GLOB ...]
                         (--code, --hash-files and --sums take several values and
                         may also be repeated; --const and --quoted take one value
                         per occurrence and are repeated)
                         [--check-tracked] [--rev REV]
                         [--gitattributes FILE] [--no-git]
                         [--out REPORT] [--format md|json] [--fail-on error|warning]

Exit codes: 0 nothing at ``--fail-on`` level, 1 findings, 2 input error, 3 bug.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import (
    TextFacts,
    collect_python_files,
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
from _git import EolInfo, GitQueries, relative_posix
from _hashrefs import (
    ConstLookup,
    ConstSpec,
    HashBasis,
    HashCandidate,
    QuotedHash,
    find_quoted_hashes,
    hash_file_candidates,
    lookup_const,
    parse_const_spec,
    resolve_quoted,
)
from _rules import (
    HASH_PATTERN,
    EditionHashes,
    RuleEdition,
    SealFile,
    SealMatch,
    classify_seal,
    editions_for_files,
    hash_edition,
    missing_revision_numbers,
    parse_seal_file,
    seal_path_candidates,
)
from _sums import SumsFile, parse_sums_file
from _tracking import CitedFile, TrackFacts, collect_track_facts, track_findings

TOOL_NAME = "seal_check"
SHORT_HASH_CHARS = 12
# core.autocrlf values that rewrite line endings on checkout or commit.
CONVERTING_AUTOCRLF = frozenset({"true", "input"})
# Commit ids are at most 40 hex characters (SHA-1 repositories).
COMMIT_ID_MAX_CHARS = 40
# A 64-hex constant counts as a rule pin candidate when its owner name looks like this.
RULE_OWNER_HINT = re.compile(r"rule|criteria|seal", re.IGNORECASE)
# A rule edition or seal file name: <stem>[_rev<N>[a-z]].md, <stem>[_rev<N>].sha256
# or <stem>[_rev<N>].md.sha256.
RULE_FILE_NAME_PATTERN = re.compile(
    r"(?P<stem>.+?)(?:_rev\d+[a-z]?)?(?:\.md)?\.(?:md|sha256)"
)
# Roles whose untracked files are always errors; --check-tracked adds the rest.
ALWAYS_REQUIRED_ROLES = frozenset({"sums_list", "sums_entry"})
ALL_CITED_ROLES = frozenset({"rule", "seal", "hash_file", *ALWAYS_REQUIRED_ROLES})
# Text traces of a hash comparison in a code file (heuristic for code_pin_unchecked).
HASH_CHECK_TRACES = ("hashlib", "sha256(", ".sha256")
GITATTRIBUTES_NAME = ".gitattributes"
PROTECTION_NO_TEXT = "-text"
PROTECTION_EOL_LF = "eol=lf"


@dataclass(frozen=True)
class LineEndingAttributes:
    """The ``text`` and ``eol`` git attributes of one file (git's value words)."""

    text: str
    eol: str

    def protection(self) -> str | None:
        """How the bytes are kept stable across checkouts, or ``None``.

        ``-text`` switches conversion off; ``eol=lf`` (with text not unset) makes
        every checkout write LF whatever ``core.autocrlf`` says.
        """
        if self.text == "unset":
            return PROTECTION_NO_TEXT
        if self.eol == "lf":
            return PROTECTION_EOL_LF
        return None


@dataclass
class EditionResult:
    """Everything measured for one rule edition."""

    edition: RuleEdition
    hashes: EditionHashes
    seal: SealFile | None
    match: SealMatch
    # Seal files of the other naming convention found beside the one used.
    unused_seal_paths: list[Path] = field(default_factory=list)

    def known_hashes(self) -> set[str]:
        hashes = {self.hashes.raw, self.hashes.lf}
        if self.seal is not None and self.seal.is_well_formed:
            hashes.add(self.seal.first_token.lower())
        return hashes

    def candidates(self) -> list[HashCandidate]:
        """The edition's raw, LF and sealed hashes as lookup candidates."""
        path, label = self.edition.path, self.edition.label
        found = [HashCandidate(self.hashes.raw, path, label, HashBasis.RAW)]
        if self.hashes.lf != self.hashes.raw:
            found.append(HashCandidate(self.hashes.lf, path, label, HashBasis.LF))
        if self.seal is not None and self.seal.is_well_formed:
            sealed = self.seal.first_token.lower()
            if sealed not in (self.hashes.raw, self.hashes.lf):
                found.append(HashCandidate(sealed, path, label, HashBasis.SEAL))
        return found

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.edition.path),
            "family": self.edition.family,
            "rev": self.edition.label,
            "sha256_raw": self.hashes.raw,
            "sha256_lf": self.hashes.lf,
            "sealed_hash": self.seal.first_token if self.seal else None,
            "sealed_at": self.seal.sealed_at if self.seal else None,
            "note": self.seal.note if self.seal else "",
            "seal_path": str(self.seal.path) if self.seal else None,
            "match": str(self.match),
        }


@dataclass
class Pin:
    """One place where a code file fixes a rule edition (or tries to)."""

    code_path: Path
    line: int
    kind: str  # "hash" or "name"
    value: str
    owner: str
    matches: list[RuleEdition] = field(default_factory=list)
    # Rule families named beside an unmatched hash constant (see _stale_families).
    named_families: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "code_path": str(self.code_path),
            "line": self.line,
            "kind": self.kind,
            "hash": self.value if self.kind == "hash" else None,
            "name": self.value if self.kind == "name" else None,
            "owner": self.owner,
            "matches": [edition.path.name for edition in self.matches],
            "named_families": list(self.named_families),
        }


@dataclass
class CodeScan:
    """Pins and counters collected from the ``--code`` files."""

    pins: list[Pin] = field(default_factory=list)
    files_scanned: int = 0
    unrelated_hex_constants: int = 0


@dataclass(frozen=True)
class FileFacts:
    """Line-ending and git facts of one rule edition or seal file."""

    path: Path
    role: str  # "rule" or "seal"
    edition: RuleEdition
    text: TextFacts
    mtime: str
    tracked: bool | None  # None: git could not tell
    eol: EolInfo | None
    last_commit_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "role": self.role,
            "family": self.edition.family,
            "rev": self.edition.label,
            "crlf": self.text.crlf_count,
            "lf": self.text.lone_lf_count,
            "bom": self.text.has_bom,
            "tracked": self.tracked,
            "git_eol": (
                {
                    "index": self.eol.index,
                    "worktree": self.eol.worktree,
                    "attr": self.eol.attr,
                }
                if self.eol
                else None
            ),
            "last_commit_at": self.last_commit_at,
            "mtime": self.mtime,
        }


# --- rule editions and seal files -------------------------------------------


def _eol_findings(path: Path, facts: TextFacts, is_seal: bool) -> list[Finding]:
    findings: list[Finding] = []
    if facts.crlf_count:
        severity = Severity.INFO if is_seal else Severity.WARNING
        message = f"CRLF {facts.crlf_count}줄, LF만 {facts.lone_lf_count}줄"
        findings.append(Finding(severity, "eol_crlf", str(path), 0, message))
    if facts.has_bom:
        findings.append(Finding(Severity.INFO, "bom", str(path), 0, "UTF-8 BOM 있음"))
    if not facts.ends_with_newline:
        findings.append(
            Finding(Severity.INFO, "no_final_newline", str(path), 0, "끝 줄바꿈 없음")
        )
    return findings


def _crlf_variant_hash(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return hashlib.sha256(data).hexdigest()


def _seal_findings(result: EditionResult) -> list[Finding]:
    edition, seal = result.edition, result.seal
    target = edition.label
    if seal is None:
        names = " 또는 ".join(
            path.name for path in seal_path_candidates(edition, None)
        )
        message = f"봉인 파일 없음: {names}"
        return [
            Finding(
                Severity.WARNING, "seal_missing", str(edition.path), 0, message, target
            )
        ]
    findings = _eol_findings(seal.path, seal.facts, is_seal=True)
    for unused in result.unused_seal_paths:
        message = f"봉인 파일이 두 이름으로 있음: {seal.path.name}을 쓰고 {unused.name}은 읽지 않음"
        findings.append(
            Finding(Severity.INFO, "seal_two_files", str(unused), 0, message, target)
        )
    if not seal.is_well_formed:
        message = f"첫 토큰이 64자리 16진수가 아님: {seal.first_token[:20]!r}"
        findings.append(
            Finding(
                Severity.WARNING,
                "sha_file_malformed",
                str(seal.path),
                1,
                message,
                target,
            )
        )
        return findings
    if seal.file_name and seal.file_name != edition.path.name:
        message = f"봉인 줄의 파일 이름 {seal.file_name} ≠ {edition.path.name}"
        findings.append(
            Finding(
                Severity.WARNING,
                "seal_name_mismatch",
                str(seal.path),
                1,
                message,
                target,
            )
        )
    sealed_short = seal.first_token[:SHORT_HASH_CHARS]
    if result.match == SealMatch.NONE:
        message = (
            f"봉인 {sealed_short}… ≠ 원시 {result.hashes.raw[:SHORT_HASH_CHARS]}… "
            f"· LF 정규화 {result.hashes.lf[:SHORT_HASH_CHARS]}…"
        )
        if _crlf_variant_hash(edition.path) == seal.first_token.lower():
            message += " (LF→CRLF 변환 해시와는 같음: 줄바꿈만 다름)"
        findings.append(
            Finding(
                Severity.ERROR, "seal_mismatch", str(edition.path), 0, message, target
            )
        )
    elif result.match == SealMatch.LF and result.hashes.raw != result.hashes.lf:
        message = (
            f"봉인 해시가 CRLF→LF 정규화 기준이다(원시 바이트 해시와 다름, "
            f"CRLF {result.hashes.facts.crlf_count}줄)"
        )
        findings.append(
            Finding(
                Severity.WARNING,
                "seal_eol_convention",
                str(edition.path),
                0,
                message,
                target,
            )
        )
    return findings


def _measure_edition(edition: RuleEdition, sha_dir: Path | None) -> EditionResult:
    existing = [
        path for path in seal_path_candidates(edition, sha_dir) if path.is_file()
    ]
    seal = parse_seal_file(existing[0]) if existing else None
    hashes = hash_edition(edition.path)
    return EditionResult(
        edition, hashes, seal, classify_seal(hashes, seal), existing[1:]
    )


def _gap_findings(editions: list[RuleEdition]) -> list[Finding]:
    findings: list[Finding] = []
    families: dict[str, list[RuleEdition]] = defaultdict(list)
    for edition in editions:
        families[edition.family].append(edition)
    for family, members in families.items():
        missing = missing_revision_numbers(members)
        if missing:
            labels = ", ".join(f"rev{number}" for number in missing)
            original = members[0].path
            findings.append(
                Finding(
                    Severity.INFO,
                    "rev_gap",
                    str(original),
                    0,
                    f"빠진 개정 번호: {labels}",
                    family,
                )
            )
    return findings


# --- code pins ----------------------------------------------------------------


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Attribute):
        return [target.attr]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for element in target.elts for name in _target_names(element)]
    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
        return [str(target.slice.value)]
    return []


def _owner_names(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> list[str]:
    """Names that own a constant: dict keys, keyword names, assignment targets."""
    names: list[str] = []
    child, current = node, parents.get(node)
    while current is not None:
        if isinstance(current, ast.Dict):
            for key, value in zip(current.keys, current.values, strict=False):
                if value is child and isinstance(key, ast.Constant):
                    names.append(str(key.value))
        elif isinstance(current, ast.keyword) and current.arg:
            names.append(current.arg)
        elif isinstance(current, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                current.targets if isinstance(current, ast.Assign) else [current.target]
            )
            names += [name for target in targets for name in _target_names(target)]
            break
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        child, current = current, parents.get(current)
    return names


@dataclass(frozen=True)
class _CodeString:
    """One non-docstring string literal of a code file and what surrounds it."""

    line: int
    value: str
    owners: list[str]
    # Rule families named by sibling literals: ("x_rules_rev3.md", "<hash>") -> x_rules.
    sibling_families: tuple[str, ...]


def _sibling_nodes(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> list[ast.AST]:
    """Nodes that sit next to ``node`` in one tuple, list, dict entry or call."""
    parent = parents.get(node)
    if isinstance(parent, ast.keyword):
        parent = parents.get(parent)
    if isinstance(parent, (ast.Tuple, ast.List, ast.Set)):
        return [element for element in parent.elts if element is not node]
    if isinstance(parent, ast.Dict):
        siblings: list[ast.AST] = []
        for key, value in zip(parent.keys, parent.values, strict=False):
            if value is node and key is not None:
                siblings.append(key)
            elif key is node:
                siblings.append(value)
        return siblings
    if isinstance(parent, ast.Call):
        arguments = [*parent.args, *(keyword.value for keyword in parent.keywords)]
        return [argument for argument in arguments if argument is not node]
    return []


def rule_family_of_name(literal: str) -> str | None:
    """``x_rules`` for ``.../x_rules_rev3a.md`` or ``x_rules.sha256``; else ``None``."""
    match = RULE_FILE_NAME_PATTERN.fullmatch(_edition_file_name(literal))
    return match.group("stem") if match else None


def _sibling_families(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    families: list[str] = []
    for sibling in _sibling_nodes(node, parents):
        if not (isinstance(sibling, ast.Constant) and isinstance(sibling.value, str)):
            continue
        family = rule_family_of_name(sibling.value)
        if family is not None and family not in families:
            families.append(family)
    return tuple(families)


def _code_strings(source: str) -> list[_CodeString] | None:
    """Every non-docstring string literal with its owners and sibling rule names."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    parents = _parent_map(tree)
    strings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if isinstance(parents.get(node), ast.Expr):
            continue  # docstring or bare string statement
        strings.append(
            _CodeString(
                node.lineno,
                node.value,
                _owner_names(node, parents),
                _sibling_families(node, parents),
            )
        )
    return strings


def _edition_file_name(literal: str) -> str:
    return literal.strip().replace("\\", "/").rsplit("/", 1)[-1]


def _pins_of_file(
    path: Path,
    strings: list[_CodeString],
    hash_index: dict[str, list[RuleEdition]],
    name_index: dict[str, RuleEdition],
) -> tuple[list[Pin], list[Pin], int]:
    """Return (pins that match, unmatched rule-like hash constants, unrelated count)."""
    pins: list[Pin] = []
    unmatched: list[Pin] = []
    unrelated = 0
    for string in strings:
        owner = ", ".join(string.owners)
        literal = string.value.strip().lower()
        if HASH_PATTERN.fullmatch(literal):
            if literal in hash_index:
                pins.append(
                    Pin(path, string.line, "hash", literal, owner, hash_index[literal])
                )
            # Only the nearest owner counts: a data hash inside SEALED_SHA256 = {...}
            # is owned by its dict key ("u_applied"), not by the outer name.
            elif string.owners and RULE_OWNER_HINT.search(string.owners[0]):
                unmatched.append(
                    Pin(
                        path,
                        string.line,
                        "hash",
                        literal,
                        owner,
                        named_families=string.sibling_families,
                    )
                )
            else:
                unrelated += 1
            continue
        edition = name_index.get(_edition_file_name(string.value))
        if edition is not None:
            pins.append(
                Pin(path, string.line, "name", string.value.strip(), owner, [edition])
            )
    return pins, unmatched, unrelated


def _stale_families(
    pin: Pin, families: dict[str, list[RuleEdition]], source: str
) -> list[str]:
    """Checked families an unmatched hash constant claims to pin.

    A constant written next to a rule file name (``("x_rules_rev3.md", "<hash>")``)
    belongs to that file's family only; a pin of another family (``v5_criteria``
    beside ``v5_resume_4368_rules``) is not stale for the checked one. Without a
    sibling name, any checked family mentioned in the file counts (old rule).
    """
    if pin.named_families:
        return [family for family in pin.named_families if family in families]
    return [family for family in families if family in source]


def _pin_findings(
    path: Path,
    source: str,
    pins: list[Pin],
    unmatched: list[Pin],
    families: dict[str, list[RuleEdition]],
) -> list[Finding]:
    findings: list[Finding] = []
    # family -> edition label -> pin kinds ("hash", "name")
    pinned_by_family: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    first_line: dict[str, int] = {}
    for pin in sorted(pins, key=lambda item: item.line):
        for edition in pin.matches:
            pinned_by_family[edition.family][edition.label].add(pin.kind)
            first_line.setdefault(edition.family, pin.line)
    for family, pinned in pinned_by_family.items():
        labels = [edition.label for edition in families[family]]
        missing = [label for label in labels if label not in pinned]
        if not missing:
            continue
        pinned_text = ", ".join(
            f"{label}({'+'.join(sorted(pinned[label]))})"
            for label in labels
            if label in pinned
        )
        message = (
            f"이 코드가 고정한 판: {pinned_text} / 빠진 판: {', '.join(missing)} "
            f"(최신 {labels[-1]})"
        )
        findings.append(
            Finding(
                Severity.WARNING,
                "code_pin_missing",
                str(path),
                first_line[family],
                message,
                family,
            )
        )
    stale_pins = [
        (pin, stale) for pin in unmatched if (stale := _stale_families(pin, families, source))
    ]
    for pin, stale in stale_pins:
        basis = "옆 문자열이 가리키는 규칙" if pin.named_families else "언급된 규칙"
        message = (
            f"{pin.owner or '상수'} = {pin.value[:SHORT_HASH_CHARS]}… 가 어느 봉인·파일 "
            f"해시와도 맞지 않음 ({basis}: {', '.join(stale)})"
        )
        findings.append(
            Finding(
                Severity.WARNING,
                "code_pin_stale",
                str(path),
                pin.line,
                message,
                pin.owner,
            )
        )
    has_pins = bool(pins) or bool(stale_pins)
    if has_pins and not any(trace in source for trace in HASH_CHECK_TRACES):
        message = "고정 상수는 있으나 hashlib·sha256(·.sha256 비교 흔적이 없음(텍스트 휴리스틱)"
        findings.append(
            Finding(Severity.INFO, "code_pin_unchecked", str(path), 0, message)
        )
    return findings


def _scan_code(
    code_files: list[Path], results: list[EditionResult], findings: list[Finding]
) -> CodeScan:
    hash_index: dict[str, list[RuleEdition]] = defaultdict(list)
    name_index: dict[str, RuleEdition] = {}
    families: dict[str, list[RuleEdition]] = defaultdict(list)
    for result in results:
        families[result.edition.family].append(result.edition)
        name_index[result.edition.path.name] = result.edition
        name_index[f"{result.edition.path.stem}.sha256"] = result.edition
        name_index[f"{result.edition.path.name}.sha256"] = result.edition
        for known in result.known_hashes():
            hash_index[known].append(result.edition)
    scan = CodeScan()
    for path in code_files:
        source = read_text_facts(path).text
        strings = _code_strings(source)
        if strings is None:
            findings.append(
                Finding(
                    Severity.INFO,
                    "code_unparsable",
                    str(path),
                    0,
                    "파이썬 구문 오류로 건너뜀",
                )
            )
            continue
        scan.files_scanned += 1
        pins, unmatched, unrelated = _pins_of_file(
            path, strings, hash_index, name_index
        )
        scan.unrelated_hex_constants += unrelated
        scan.pins += pins
        scan.pins += [
            pin for pin in unmatched if _stale_families(pin, families, source)
        ]
        findings += _pin_findings(path, source, pins, unmatched, families)
    return scan


# --- line-ending protection (.gitattributes) -------------------------------------


def _glob_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    # Windows checkouts compare names case-insensitively (core.ignorecase).
    return re.compile("".join(parts) + r"\Z", re.IGNORECASE)


def _text_state(tokens: list[str]) -> str | None:
    state = None
    for token in tokens:
        if token in ("-text", "binary"):
            state = "unset"
        elif token == "text":
            state = "set"
        elif token == "!text":
            state = "unspecified"
        elif token.startswith("text="):
            state = token.split("=", 1)[1]
    return state


def _eol_state(tokens: list[str]) -> str | None:
    state = None
    for token in tokens:
        if token.startswith("eol="):
            state = token.split("=", 1)[1]
        elif token in ("-eol", "!eol"):
            state = "unspecified"
    return state


def _attributes_from_file(gitattributes: Path, path: Path) -> LineEndingAttributes:
    """Read ``text`` and ``eol`` for ``path`` from one ``.gitattributes`` file."""
    relative = relative_posix(path, gitattributes.parent)
    text_state, eol_state = "unspecified", "unspecified"
    if relative is None:
        return LineEndingAttributes(text_state, eol_state)
    for raw_line in read_text_facts(gitattributes).text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "[attr]")):
            continue
        pattern, *tokens = line.split()
        line_text, line_eol = _text_state(tokens), _eol_state(tokens)
        if line_text is None and line_eol is None:
            continue
        is_anchored = "/" in pattern.rstrip("/")
        subject = relative if is_anchored else relative.rsplit("/", 1)[-1]
        if not _glob_regex(pattern.lstrip("/")).match(subject):
            continue
        # Later lines win, attribute by attribute.
        text_state = line_text or text_state
        eol_state = line_eol or eol_state
    return LineEndingAttributes(text_state, eol_state)


def _find_gitattributes(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        candidate = folder / GITATTRIBUTES_NAME
        if candidate.is_file():
            return candidate
    return None


def _group_by_git_root(
    paths: list[Path], git: GitQueries
) -> dict[Path, list[tuple[Path, str]]]:
    """``{work-tree root: [(path, relative posix path)]}`` for paths inside a work tree."""
    by_root: dict[Path, list[tuple[Path, str]]] = defaultdict(list)
    for path in paths:
        root = git.toplevel(path.parent)
        relative = relative_posix(path, root) if root else None
        if root is not None and relative is not None:
            by_root[root].append((path, relative))
    return by_root


def _unprotected_finding(
    path: Path,
    attributes: LineEndingAttributes,
    source: str,
    autocrlf: str | None,
    is_rule: bool,
) -> Finding:
    message = (
        f"줄바꿈 보호(-text 또는 eol=lf) 없음: text={attributes.text}, "
        f"eol={attributes.eol} (출처 {source})"
    )
    if autocrlf in CONVERTING_AUTOCRLF:
        message += f", core.autocrlf={autocrlf}: 체크아웃·커밋 때 줄바꿈이 바뀐다"
        if is_rule:
            return Finding(
                Severity.ERROR, "attr_unprotected_autocrlf", str(path), 0, message
            )
    return Finding(Severity.WARNING, "attr_unprotected", str(path), 0, message)


def _eol_lf_finding(path: Path, source: str) -> Finding:
    message = (
        f"eol=lf로 LF 체크아웃 고정(출처 {source}): core.autocrlf와 무관하게 "
        "작업 트리가 LF다. -text와 달리 CRLF로 커밋된 내용은 다음 add 때 "
        "LF로 정규화될 수 있다"
    )
    return Finding(Severity.INFO, "attr_protected_eol_lf", str(path), 0, message)


def _git_line_ending_attributes(
    paths: list[Path], git: GitQueries
) -> tuple[dict[str, LineEndingAttributes], dict[str, str | None]]:
    """``git check-attr text eol`` and ``core.autocrlf`` per path (git answers only)."""
    attributes_by_path: dict[str, LineEndingAttributes] = {}
    autocrlf_by_path: dict[str, str | None] = {}
    for root, members in _group_by_git_root(paths, git).items():
        answer = git.check_attrs(
            root, [relative for _, relative in members], ["text", "eol"]
        )
        autocrlf = git.config_value(root, "core.autocrlf")
        for path, relative in members:
            autocrlf_by_path[str(path)] = autocrlf
            values = answer.get(relative)
            if values and "text" in values:
                attributes_by_path[str(path)] = LineEndingAttributes(
                    values["text"], values.get("eol", "unspecified")
                )
    return attributes_by_path, autocrlf_by_path


def _check_attributes(
    paths: list[Path],
    rule_paths: set[Path],
    git: GitQueries,
    explicit: Path | None,
) -> tuple[list[dict[str, object]], list[Finding]]:
    git_attributes, autocrlf_by_path = _git_line_ending_attributes(paths, git)
    attributes: list[dict[str, object]] = []
    findings: list[Finding] = []
    for path in paths:
        values = git_attributes.get(str(path))
        source = "git check-attr"
        if values is None:
            gitattributes = explicit or _find_gitattributes(path.parent)
            if gitattributes is None:
                values = LineEndingAttributes("unspecified", "unspecified")
                source = "none"
            else:
                values = _attributes_from_file(gitattributes, path)
                source = f"file:{gitattributes}"
        protection = values.protection()
        autocrlf = autocrlf_by_path.get(str(path))
        attributes.append(
            {
                "path": str(path),
                "protected": protection is not None,
                "protection": protection,
                "text": values.text,
                "eol": values.eol,
                "source": source,
                "autocrlf": autocrlf,
            }
        )
        if protection == PROTECTION_EOL_LF:
            findings.append(_eol_lf_finding(path, source))
        elif protection is None:
            findings.append(
                _unprotected_finding(path, values, source, autocrlf, path in rule_paths)
            )
    return attributes, findings


# --- per-file git and line-ending facts --------------------------------------------


def _mtime_text(path: Path) -> str:
    stamp = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    return stamp.isoformat(timespec="seconds")


def _fact_subjects(
    results: list[EditionResult],
) -> list[tuple[Path, str, RuleEdition, TextFacts]]:
    subjects = []
    for result in results:
        subjects.append(
            (result.edition.path, "rule", result.edition, result.hashes.facts)
        )
        if result.seal is not None:
            subjects.append((result.seal.path, "seal", result.edition, result.seal.facts))
    return subjects


def _collect_file_facts(
    results: list[EditionResult], git: GitQueries
) -> list[FileFacts]:
    """Gather ls-files EOL, tracked state, last commit time and mtime per file."""
    subjects = _fact_subjects(results)
    by_root = _group_by_git_root([path for path, *_ in subjects], git)
    relative_of: dict[str, tuple[Path, str]] = {}
    eol_of: dict[str, EolInfo] = {}
    for root, members in by_root.items():
        answer = git.ls_files_eol(root, [relative for _, relative in members])
        for path, relative in members:
            relative_of[str(path)] = (root, relative)
            if relative in answer:
                eol_of[str(path)] = answer[relative]
    facts = []
    for path, role, edition, text in subjects:
        location = relative_of.get(str(path))
        is_tracked = None if location is None else str(path) in eol_of
        last_commit = None
        if location is not None and is_tracked:
            last_commit = git.last_commit_time(*location)
        facts.append(
            FileFacts(
                path,
                role,
                edition,
                text,
                _mtime_text(path),
                is_tracked,
                eol_of.get(str(path)),
                last_commit,
            )
        )
    return facts


def _untracked_findings(facts: list[FileFacts]) -> list[Finding]:
    return [
        Finding(
            Severity.INFO,
            "rule_untracked",
            str(item.path),
            0,
            "git이 추적하지 않음: 봉인 시각의 git 근거가 없다",
            item.edition.label,
        )
        for item in facts
        if item.tracked is False
    ]


# --- --const and --quoted ----------------------------------------------------------


def _const_findings(lookup: ConstLookup) -> list[Finding]:
    spec = lookup.spec
    if lookup.assignment_line is None:
        message = f"상수 {spec.name}의 대입을 찾지 못함"
        return [
            Finding(
                Severity.ERROR, "const_not_found", str(spec.path), 0, message, spec.name
            )
        ]
    if not lookup.values:
        message = f"상수 {spec.name}에 64자리 16진 문자열이 없음"
        return [
            Finding(
                Severity.WARNING,
                "const_no_hash",
                str(spec.path),
                lookup.assignment_line,
                message,
                spec.name,
            )
        ]
    findings = []
    for value in lookup.values:
        if value.matches:
            continue
        message = (
            f"{spec.name} = {value.digest[:SHORT_HASH_CHARS]}… 가 어느 판의 원시·LF·봉인 "
            "해시와도 맞지 않음"
        )
        findings.append(
            Finding(
                Severity.ERROR,
                "const_mismatch",
                str(spec.path),
                value.line,
                message,
                spec.name,
            )
        )
    return findings


def _quoted_finding(quoted: QuotedHash) -> Finding | None:
    location = (str(quoted.document), quoted.line)
    if quoted.matches:
        distinct_files = {candidate.path for candidate in quoted.matches}
        if len(distinct_files) < 2:
            return None
        names = ", ".join(sorted(path.name for path in distinct_files))
        message = f"접두 {quoted.prefix}가 여러 파일 해시와 맞음: {names}"
        return Finding(Severity.INFO, "quoted_ambiguous", *location, message, quoted.prefix)
    if quoted.is_commit:
        message = f"{quoted.prefix}: 파일 해시가 아니라 git 커밋으로 풀림"
        return Finding(Severity.INFO, "quoted_commit", *location, message, quoted.prefix)
    message = f"인용 해시 {quoted.prefix}가 어느 파일 해시와도 맞지 않음: …{quoted.context}…"
    return Finding(
        Severity.WARNING, "quoted_unresolved", *location, message, quoted.prefix
    )


def _check_quoted(
    documents: list[Path], candidates: list[HashCandidate], git: GitQueries
) -> tuple[list[QuotedHash], list[Finding]]:
    quoted_all: list[QuotedHash] = []
    findings: list[Finding] = []
    for document in documents:
        root = git.toplevel(document.parent)
        for quoted in find_quoted_hashes(document):
            resolve_quoted(quoted, candidates)
            if (
                not quoted.matches
                and root is not None
                and len(quoted.prefix) <= COMMIT_ID_MAX_CHARS
            ):
                quoted.is_commit = git.resolves_to_commit(root, quoted.prefix)
            quoted_all.append(quoted)
            finding = _quoted_finding(quoted)
            if finding is not None:
                findings.append(finding)
    return quoted_all, findings


# --- report ----------------------------------------------------------------------


def _short(text: str | None) -> str:
    return f"{text[:SHORT_HASH_CHARS]}…" if text else "-"


def _facts_table(report: dict[str, object]) -> list[str]:
    lines = [
        "",
        "## 파일 사실 (줄바꿈·git)",
        "",
        "| 파일 | 역할 | 추적 | git eol i/w/attr | CRLF | LF | BOM | 마지막 커밋 | mtime |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in report["files"]:
        eol = item["git_eol"]
        eol_text = f"{eol['index']}/{eol['worktree']}/{eol['attr']}" if eol else "-"
        tracked = "?" if item["tracked"] is None else item["tracked"]
        lines.append(
            f"| `{Path(item['path']).name}` | {item['role']} | {tracked} | {eol_text} "
            f"| {item['crlf']} | {item['lf']} | {item['bom']} "
            f"| {item['last_commit_at'] or '-'} | {item['mtime']} |"
        )
    return lines


def _consts_table(report: dict[str, object]) -> list[str]:
    if not report["consts"]:
        return []
    lines = [
        "",
        "## 도구 상수 (--const)",
        "",
        "| 상수 | 줄 | 값 | 맞는 판(근거) |",
        "|---|---|---|---|",
    ]
    for item in report["consts"]:
        matches = ", ".join(
            f"{Path(match['path']).name}({match['basis']})" for match in item["matches"]
        )
        lines.append(
            f"| `{item['spec']}` | {item['line'] or '-'} | {_short(item['hash'])} "
            f"| {matches or '없음'} |"
        )
    return lines


def _quoted_table(report: dict[str, object]) -> list[str]:
    if not report["quoted"]:
        return []
    lines = [
        "",
        "## 인용 해시 (--quoted)",
        "",
        "| 문서:줄 | 접두 | 풀림 |",
        "|---|---|---|",
    ]
    for item in report["quoted"]:
        resolved = ", ".join(
            f"{Path(match['path']).name}({match['basis']})" for match in item["matches"]
        )
        if not resolved:
            resolved = "git 커밋" if item["is_commit"] else "**없음**"
        location = f"`{Path(item['document']).name}`:{item['line']}"
        lines.append(f"| {location} | `{item['prefix']}` | {resolved} |")
    return lines


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    lines = [
        "# 봉인 점검 (seal_check)",
        "",
        f"- 규칙 판: {summary['editions']}개 (규칙 묶음 {summary['families']}개)",
        f"- 코드 파일: {summary['code_files']}개, 고정 {summary['pins']}곳",
        f"- 도구 상수: {summary['consts']}개, 인용 해시: {summary['quoted']}개"
        f"(풀리지 않음 {summary['quoted_unresolved']})",
        f"- git: {report['git']}",
        "",
        "## 규칙 판과 봉인",
        "",
        "| 묶음 | 판 | 봉인 시각 | 일치 | 원시 해시 | LF 해시 | 봉인 해시 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in report["rules"]:
        lines.append(
            f"| {item['family']} | {item['rev']} | {item['sealed_at'] or '-'} | {item['match']} "
            f"| {_short(item['sha256_raw'])} | {_short(item['sha256_lf'])} "
            f"| {_short(item['sealed_hash'])} |"
        )
    if report["pins"]:
        lines += [
            "",
            "## 코드 고정",
            "",
            "| 코드 | 줄 | 종류 | 값 | 맞는 판 |",
            "|---|---|---|---|---|",
        ]
        for pin in report["pins"]:
            value = _short(pin["hash"]) if pin["kind"] == "hash" else f"`{pin['name']}`"
            matches = ", ".join(pin["matches"]) or "없음"
            lines.append(
                f"| `{Path(pin['code_path']).name}` | {pin['line']} | {pin['kind']} | {value} | {matches} |"
            )
    lines += [
        "",
        "## 줄바꿈 보호",
        "",
        "| 파일 | 보호 | text | eol | 출처 | core.autocrlf |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["attributes"]:
        lines.append(
            f"| `{Path(item['path']).name}` | {item['protection'] or '없음'} "
            f"| {item['text']} | {item['eol']} "
            f"| {item['source']} | {item['autocrlf'] or '-'} |"
        )
    lines += _facts_table(report)
    lines += _tracking_table(report)
    lines += _consts_table(report)
    lines += _quoted_table(report)
    lines += ["", "## 발견 사항", ""]
    lines += findings_markdown(findings)
    return lines


@dataclass(frozen=True)
class SealInputs:
    """Every resolved input path of one run."""

    base: Path
    results: list[EditionResult]
    seal_paths: list[Path]
    code_files: list[Path]
    code_folders: list[Path]
    const_specs: list[ConstSpec]
    quoted_documents: list[Path]
    hash_files: list[Path]
    sums_files: list[SumsFile]
    sha_dir: Path | None
    gitattributes: Path | None

    @property
    def editions(self) -> list[RuleEdition]:
        return [result.edition for result in self.results]

    def files(self) -> list[Path]:
        """Every file the run reads (none of them may be overwritten)."""
        return [
            *(edition.path for edition in self.editions),
            *self.seal_paths,
            *self.code_files,
            *(spec.path for spec in self.const_specs),
            *self.quoted_documents,
            *self.hash_files,
            *(sums.path for sums in self.sums_files),
        ]

    def cited_files(self) -> list[CitedFile]:
        """Files the seals rely on; each must reach the commit."""
        cited = [CitedFile(edition.path, "rule") for edition in self.editions]
        cited += [CitedFile(path, "seal") for path in self.seal_paths]
        cited += [CitedFile(path, "hash_file") for path in self.hash_files]
        for sums in self.sums_files:
            cited.append(CitedFile(sums.path, "sums_list"))
            cited += [
                CitedFile(entry.path, "sums_entry")
                for entry in sums.entries
                if entry.path.is_file()
            ]
        return cited


def _resolve_base(repo: Path | None) -> Path:
    if repo is None:
        return Path.cwd()
    base = repo.expanduser().resolve()
    if not base.is_dir():
        raise InputError(f"--repo is not a folder: {base}")
    return base


def _optional_path(path: Path | None, base: Path) -> Path | None:
    return (base / path.expanduser()).resolve() if path else None


def _gather_inputs(args: argparse.Namespace) -> SealInputs:
    """Resolve rule globs, seals, code, constants and documents against ``--repo``.

    Raises:
        InputError: If no rule is given, a path is missing or a pattern is empty.
    """
    base = _resolve_base(args.repo)
    if not args.rules:
        raise InputError("give at least one rule file or glob pattern")
    rule_files = expand_file_patterns(args.rules, base)
    editions = editions_for_files(rule_files, include_revisions=args.revs == "auto")
    sha_dir = _optional_path(args.sha_dir, base)
    results = [_measure_edition(edition, sha_dir) for edition in editions]
    code_files, code_folders = collect_python_files(
        str(base / Path(text).expanduser()) for text in args.code or []
    )
    return SealInputs(
        base=base,
        results=results,
        seal_paths=[result.seal.path for result in results if result.seal],
        code_files=code_files,
        code_folders=code_folders,
        const_specs=[parse_const_spec(text, base) for text in args.const or []],
        quoted_documents=expand_file_patterns(args.quoted or [], base),
        hash_files=expand_file_patterns(args.hash_files or [], base),
        sums_files=[
            parse_sums_file(path)
            for path in expand_file_patterns(args.sums or [], base)
        ],
        sha_dir=sha_dir,
        gitattributes=_optional_path(args.gitattributes, base),
    )


def _all_candidates(inputs: SealInputs) -> list[HashCandidate]:
    candidates = [item for result in inputs.results for item in result.candidates()]
    for path in inputs.hash_files:
        candidates += hash_file_candidates(path)
    return candidates


def _edition_findings(inputs: SealInputs) -> list[Finding]:
    findings: list[Finding] = []
    for result in inputs.results:
        findings += _eol_findings(
            result.edition.path, result.hashes.facts, is_seal=False
        )
        findings += _seal_findings(result)
    findings += _gap_findings(inputs.editions)
    return findings


def _resolve_revision(
    revision: str | None, base: Path, git: GitQueries
) -> str | None:
    """Full commit id of ``--rev``.

    Raises:
        InputError: With ``--no-git``, outside a work tree, or an unknown revision.
    """
    if revision is None:
        return None
    if not git.enabled:
        raise InputError("--rev needs git (drop --no-git)")
    root = git.toplevel(base)
    if root is None:
        raise InputError(f"--rev needs a git work tree: {base}")
    commit = git.full_commit(root, revision)
    if commit is None:
        raise InputError(f"--rev is not a commit: {revision}")
    return commit


def _sums_entry_findings(sums_files: list[SumsFile]) -> list[Finding]:
    findings = []
    for sums in sums_files:
        for entry in sums.entries:
            if not entry.path.is_file():
                message = f"목록의 파일 없음: {entry.name} (해시 대조는 baseline_check.py sums)"
                findings.append(
                    Finding(
                        Severity.WARNING,
                        "sums_entry_missing",
                        str(sums.path),
                        entry.line,
                        message,
                        entry.name,
                    )
                )
    return findings


def _tracking_findings(
    inputs: SealInputs,
    git: GitQueries,
    revision: str | None,
    check_tracked: bool,
) -> tuple[list[TrackFacts], list[Finding]]:
    facts = collect_track_facts(inputs.cited_files(), git, revision)
    required = ALL_CITED_ROLES if check_tracked else ALWAYS_REQUIRED_ROLES
    findings = track_findings(facts, revision, required, git.enabled)
    return facts, findings + _sums_entry_findings(inputs.sums_files)


def _tracking_table(report: dict[str, object]) -> list[str]:
    problems = [
        item
        for item in report["tracking"]
        if item["tracked"] is False or item["ignore_rule"]
    ]
    lines = [
        "",
        "## 인용 파일 git 추적",
        "",
        f"- 인용 파일 {len(report['tracking'])}개, 기준: {report['tracking_basis']}",
    ]
    if not problems:
        return [*lines, "- 추적 안 함·무시 규칙 해당 없음"]
    lines += ["", "| 파일 | 역할 | 추적 | 무시 규칙 |", "|---|---|---|---|"]
    for item in problems:
        lines.append(
            f"| `{item['relative'] or item['path']}` | {item['role']} "
            f"| {item['tracked']} | {item['ignore_rule'] or '-'} |"
        )
    return lines


def run_seal_check(args: argparse.Namespace) -> ToolOutcome:
    """Check the seals of the given rule families."""
    inputs = _gather_inputs(args)
    folders = [edition.path.parent for edition in inputs.editions]
    if inputs.sha_dir:
        folders.append(inputs.sha_dir)
    require_output_outside(args.out, inputs.files(), [*folders, *inputs.code_folders])
    git = GitQueries(enabled=not args.no_git)
    revision = _resolve_revision(args.rev, inputs.base, git)

    findings = _edition_findings(inputs)
    scan = (
        _scan_code(inputs.code_files, inputs.results, findings)
        if inputs.code_files
        else CodeScan()
    )
    rule_paths = [edition.path for edition in inputs.editions]
    attributes, attribute_findings = _check_attributes(
        [*rule_paths, *inputs.seal_paths], set(rule_paths), git, inputs.gitattributes
    )
    file_facts = _collect_file_facts(inputs.results, git)
    candidates = _all_candidates(inputs)
    const_lookups = [lookup_const(spec, candidates) for spec in inputs.const_specs]
    quoted, quoted_findings = _check_quoted(inputs.quoted_documents, candidates, git)
    tracking, tracking_findings = _tracking_findings(
        inputs, git, revision, args.check_tracked
    )
    # With --check-tracked an untracked rule is cited_untracked (error), not info.
    untracked_notes = [] if args.check_tracked else _untracked_findings(file_facts)
    findings += attribute_findings + untracked_notes + quoted_findings
    findings += tracking_findings
    for lookup in const_lookups:
        findings += _const_findings(lookup)
    findings = sort_findings(findings)

    const_values = [value for lookup in const_lookups for value in lookup.values]
    summary = {
        "tool": TOOL_NAME,
        "command": "check",
        "findings": len(findings),
        "editions": len(inputs.editions),
        "families": len({edition.family for edition in inputs.editions}),
        "code_files": scan.files_scanned,
        "pins": len(scan.pins),
        "unrelated_hex_constants": scan.unrelated_hex_constants,
        "consts": len(inputs.const_specs),
        "quoted": len(quoted),
        "quoted_unresolved": sum(
            1 for item in quoted if not item.matches and not item.is_commit
        ),
        "sums_lists": len(inputs.sums_files),
        "cited_files": len(tracking),
        "cited_untracked": sum(1 for item in tracking if item.tracked is False),
        "cited_ignored": sum(
            1 for item in tracking if item.tracked is False and item.ignore_rule
        ),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report: dict[str, object] = {
        "tool": TOOL_NAME,
        "repo": str(inputs.base),
        "git": git.unavailable_reason or "used",
        "tracking_basis": f"commit {revision}" if revision else "index",
        "tracking": [item.to_dict() for item in tracking],
        "rules": [result.to_dict() for result in inputs.results],
        "files": [item.to_dict() for item in file_facts],
        "pins": [
            pin.to_dict()
            for pin in sorted(
                scan.pins, key=lambda item: (str(item.code_path), item.line)
            )
        ],
        "attributes": attributes,
        "consts": [value.to_dict() for value in const_values]
        + [_unresolved_const_dict(lookup) for lookup in const_lookups if not lookup.values],
        "quoted": [item.to_dict() for item in quoted],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(report, findings), report, inputs.files())
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def _unresolved_const_dict(lookup: ConstLookup) -> dict[str, object]:
    """Report row for a ``--const`` without a 64-hex value (not found or no hash)."""
    return {
        "spec": lookup.spec.text,
        "path": str(lookup.spec.path),
        "name": lookup.spec.name,
        "line": lookup.assignment_line,
        "hash": None,
        "matches": [],
    }


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="seal_check.py",
        description="규칙 원판·개정판의 봉인 해시, 코드 고정, 줄바꿈 보호를 점검한다(읽기 전용).",
    )
    parser.add_argument(
        "rules",
        nargs="*",
        help="rule .md files or glob patterns (relative to --repo); a matched "
        "<stem>_rev<N>.md joins the family of <stem>.md",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        help="base folder for relative paths and patterns (default: current folder)",
    )
    parser.add_argument(
        "--revs",
        choices=("auto", "none"),
        default="auto",
        help="auto: also check <stem>_rev<N>.md next to each original (default)",
    )
    parser.add_argument("--sha-dir", type=Path, help="folder of the .sha256 files")
    # "extend": repeating a multi-value option adds to the list; plain nargs="+"
    # would keep only the last occurrence (argparse last-wins).
    parser.add_argument(
        "--code",
        nargs="+",
        action="extend",
        metavar="PATH",
        help="Python files or folders that pin seals (repeatable)",
    )
    parser.add_argument(
        "--const",
        action="append",
        metavar="FILE:NAME",
        help="compare the 64-hex value(s) of constant NAME in FILE (repeatable)",
    )
    parser.add_argument(
        "--quoted",
        action="append",
        metavar="DOC",
        help="resolve hash prefixes (8-64 hex) quoted in DOC; globs allowed (repeatable)",
    )
    parser.add_argument(
        "--hash-files",
        nargs="+",
        action="extend",
        metavar="GLOB",
        help="extra files (results) whose hashes --quoted prefixes may refer to "
        "(repeatable)",
    )
    parser.add_argument(
        "--sums",
        nargs="+",
        action="extend",
        metavar="GLOB",
        help="checksum lists (SHA256SUMS); the lists and the files they name must "
        "be tracked by git (repeatable)",
    )
    parser.add_argument(
        "--check-tracked",
        action="store_true",
        help="also report untracked rule, seal and --hash-files files as errors",
    )
    parser.add_argument(
        "--rev",
        help="check tracked state against this commit's tree instead of the index",
    )
    parser.add_argument(
        "--gitattributes", type=Path, help=".gitattributes for the fallback"
    )
    parser.add_argument("--no-git", action="store_true", help="never start git")
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_seal_check(args))


if __name__ == "__main__":
    sys.exit(main())
