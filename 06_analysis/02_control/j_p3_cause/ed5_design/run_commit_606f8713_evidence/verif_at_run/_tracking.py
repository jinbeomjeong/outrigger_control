"""Is a cited file in git? Tracked state and ignore rules of files a check relies on.

A sealed list (``.sha256``, ``SHA256SUMS``, ``--hash-files``) is only evidence
if the files it names reach the commit. A ``*.npz`` line in ``.gitignore`` makes
``git add -A`` skip them without a word (2026-11-16, 18 baseline npz files), so
each cited file is checked twice:

* tracked: in the index (``git ls-files``) or, with a revision, in that commit's
  tree (``git ls-tree -r``);
* ignored: ``git check-ignore -v --no-index`` names the rule even for a tracked
  (force-added) file.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from _findings import Finding, Severity
from _git import GitQueries, IgnoreRule, relative_posix

CATEGORY_IGNORED = "cited_ignored"
CATEGORY_UNTRACKED = "cited_untracked"
CATEGORY_IGNORED_TRACKED = "cited_ignored_tracked"
CATEGORY_OUTSIDE_REPO = "cited_outside_repo"


@dataclass(frozen=True)
class CitedFile:
    """A file a check relies on and why (``rule``, ``seal``, ``hash_file`` …)."""

    path: Path
    role: str


@dataclass(frozen=True)
class TrackFacts:
    """Git facts of one cited file; ``tracked`` is ``None`` when git cannot tell."""

    cited: CitedFile
    relative: str | None
    tracked: bool | None
    ignore_rule: IgnoreRule | None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.cited.path),
            "role": self.cited.role,
            "relative": self.relative,
            "tracked": self.tracked,
            "ignore_rule": self.ignore_rule.describe() if self.ignore_rule else None,
        }


def _contains(names: set[str], relative: str) -> bool:
    """Membership that also accepts a case-only difference (Windows checkouts)."""
    if relative in names:
        return True
    folded = relative.casefold()
    return any(name.casefold() == folded for name in names)


def _rule_for(rules: dict[str, IgnoreRule], relative: str) -> IgnoreRule | None:
    if relative in rules:
        return rules[relative]
    folded = relative.casefold()
    for name, rule in rules.items():
        if name.casefold() == folded:
            return rule
    return None


def _facts_in_root(
    root: Path,
    members: list[tuple[CitedFile, str]],
    git: GitQueries,
    revision: str | None,
) -> list[TrackFacts]:
    relatives = [relative for _, relative in members]
    tracked = git.tracked_paths(root, relatives, revision)
    rules = git.ignore_rules(root, relatives) or {}
    return [
        TrackFacts(
            cited,
            relative,
            None if tracked is None else _contains(tracked, relative),
            _rule_for(rules, relative),
        )
        for cited, relative in members
    ]


def collect_track_facts(
    cited_files: list[CitedFile], git: GitQueries, revision: str | None = None
) -> list[TrackFacts]:
    """Tracked state and ignore rule of every cited file (one git call per root)."""
    by_root: dict[Path, list[tuple[CitedFile, str]]] = defaultdict(list)
    outside: list[TrackFacts] = []
    seen: set[str] = set()
    for cited in cited_files:
        key = os.path.normcase(str(cited.path))
        if key in seen:
            continue
        seen.add(key)
        root = git.toplevel(cited.path.parent) if git.enabled else None
        relative = relative_posix(cited.path, root) if root else None
        if root is None or relative is None:
            outside.append(TrackFacts(cited, None, None, None))
            continue
        by_root[root].append((cited, relative))
    facts = list(outside)
    for root, members in by_root.items():
        facts += _facts_in_root(root, members, git, revision)
    return facts


def _where(revision: str | None) -> str:
    return f"커밋 {revision}에 없음" if revision else "git 색인에 없음(추적 안 함)"


def track_findings(
    facts: list[TrackFacts],
    revision: str | None,
    required_roles: frozenset[str],
    git_enabled: bool,
) -> list[Finding]:
    """Findings for ignored and (for ``required_roles``) untracked cited files.

    * untracked and ignored -> ``cited_ignored`` (error), whatever the role;
    * untracked, not ignored, role required -> ``cited_untracked`` (error);
    * tracked but matched by an ignore rule (force-added) -> info;
    * outside any work tree while git runs -> info.
    """
    findings: list[Finding] = []
    for item in facts:
        path, role = str(item.cited.path), item.cited.role
        if item.tracked is None:
            if git_enabled and item.relative is None:
                message = "git 작업 트리 밖이라 추적 여부를 모름"
                findings.append(
                    Finding(
                        Severity.INFO, CATEGORY_OUTSIDE_REPO, path, 0, message, role
                    )
                )
            continue
        rule = item.ignore_rule
        if not item.tracked and rule is not None:
            message = (
                f"{_where(revision)}, 무시 규칙 `{rule.describe()}`에 걸림: "
                "`git add`가 조용히 빼므로 커밋에 들어가지 않는다(`git add -f` 또는 규칙 예외 필요)"
            )
            findings.append(
                Finding(Severity.ERROR, CATEGORY_IGNORED, path, 0, message, role)
            )
        elif not item.tracked and role in required_roles:
            message = f"{_where(revision)}: 인용한 파일이 커밋 근거가 없다"
            findings.append(
                Finding(Severity.ERROR, CATEGORY_UNTRACKED, path, 0, message, role)
            )
        elif item.tracked and rule is not None:
            message = (
                f"추적 중이지만 무시 규칙 `{rule.describe()}`에 걸림(강제 추가): "
                "같은 규칙의 새 파일은 커밋에서 조용히 빠진다"
            )
            findings.append(
                Finding(Severity.INFO, CATEGORY_IGNORED_TRACKED, path, 0, message, role)
            )
    return findings
