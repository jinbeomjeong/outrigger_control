"""Read-only git queries for the verif tools.

Commands used: ``rev-parse``, ``check-attr``, ``ls-files``, ``ls-tree``,
``check-ignore``, ``log``, ``diff-tree``, ``hash-object`` (no ``-w``: nothing is
written to the object store), ``config --get``.

Only query commands run; ``GIT_OPTIONAL_LOCKS=0`` keeps git from refreshing the
index. With ``--no-git`` (``enabled=False``) nothing is started at all.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

GIT_TIMEOUT_S = 30
# Keep each command line well below the Windows limit of 32,767 characters.
MAX_PATH_ARGUMENT_CHARS = 20_000
# git check-ignore exits 1 when no path matched an ignore rule (not an error).
CHECK_IGNORE_NO_MATCH = 1

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IgnoreRule:
    """The ignore rule that matches a path (``git check-ignore -v``)."""

    source: str
    line: str
    pattern: str

    def describe(self) -> str:
        return f"{self.source}:{self.line}:{self.pattern}"


def _path_chunks(relative_paths: list[str]) -> list[list[str]]:
    """Split paths into groups whose joined length stays under the argument limit."""
    chunks: list[list[str]] = []
    current: list[str] = []
    length = 0
    for path in relative_paths:
        if current and length + len(path) + 1 > MAX_PATH_ARGUMENT_CHARS:
            chunks.append(current)
            current, length = [], 0
        current.append(path)
        length += len(path) + 1
    if current:
        chunks.append(current)
    return chunks


@dataclass(frozen=True)
class EolInfo:
    """One ``git ls-files --eol`` entry: index EOL, work-tree EOL, attributes."""

    index: str
    worktree: str
    attr: str


@dataclass
class GitQueries:
    """Runs git queries; remembers why git could not be used."""

    enabled: bool = True
    unavailable_reason: str = ""
    _toplevels: dict[str, Path | None] = field(default_factory=dict)

    def _run(
        self,
        cwd: Path,
        arguments: list[str],
        accepted_codes: tuple[int, ...] = (0,),
        stdin_bytes: bytes | None = None,
    ) -> str | None:
        if not self.enabled:
            self.unavailable_reason = self.unavailable_reason or "--no-git"
            return None
        command = ["git", "-c", "core.quotepath=off", "-C", str(cwd), *arguments]
        environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        try:
            # stdin is always given (empty by default) so git never waits on a console.
            completed = subprocess.run(
                command,
                input=stdin_bytes or b"",
                capture_output=True,
                timeout=GIT_TIMEOUT_S,
                env=environment,
                check=False,
            )
        except FileNotFoundError:
            self.enabled = False
            self.unavailable_reason = "git not found on PATH"
            return None
        except subprocess.TimeoutExpired:
            logger.warning("git timed out: %s", " ".join(arguments))
            return None
        if completed.returncode not in accepted_codes:
            return None
        return completed.stdout.decode("utf-8", errors="replace")

    def toplevel(self, folder: Path) -> Path | None:
        """Return the work-tree root that contains ``folder``, or ``None``."""
        key = os.path.normcase(str(folder))
        if key not in self._toplevels:
            output = self._run(folder, ["rev-parse", "--show-toplevel"])
            root = Path(output.strip()).resolve() if output and output.strip() else None
            if root is None and self.enabled and not self.unavailable_reason:
                self.unavailable_reason = f"not a git work tree: {folder}"
            self._toplevels[key] = root
        return self._toplevels[key]

    def check_attrs(
        self, root: Path, relative_paths: list[str], attribute_names: list[str]
    ) -> dict[str, dict[str, str]]:
        """Return ``{relative path: {attribute name: value}}``.

        Values are git's: ``set``, ``unset``, ``unspecified`` or a string such
        as ``auto`` or ``lf``. Missing entries mean git could not answer.
        """
        if not relative_paths or not attribute_names:
            return {}
        output = self._run(
            root, ["check-attr", "-z", *attribute_names, "--", *relative_paths]
        )
        if output is None:
            return {}
        fields = output.split("\0")
        values: dict[str, dict[str, str]] = {}
        # -z output is a flat "path NUL attribute NUL value NUL" sequence.
        for index in range(0, len(fields) - 2, 3):
            path, name, value = fields[index : index + 3]
            values.setdefault(path, {})[name] = value
        return values

    def check_attr_text(self, root: Path, relative_paths: list[str]) -> dict[str, str]:
        """Return ``{relative path: value of the text attribute}``."""
        answer = self.check_attrs(root, relative_paths, ["text"])
        return {path: values["text"] for path, values in answer.items()}

    def ls_files_eol(self, root: Path, relative_paths: list[str]) -> dict[str, EolInfo]:
        """Return ``git ls-files --eol`` facts for the tracked paths among the given.

        Paths absent from the answer are untracked (or git could not answer).
        """
        if not relative_paths:
            return {}
        output = self._run(root, ["ls-files", "--eol", "-z", "--", *relative_paths])
        if output is None:
            return {}
        entries: dict[str, EolInfo] = {}
        for record in output.split("\0"):
            facts, separator, relative = record.partition("\t")
            if not separator:
                continue
            # "i/lf    w/crlf  attr/text eol=lf" - the attr part may contain spaces.
            index_eol, worktree_eol, *attr_tokens = facts.split()
            entries[relative] = EolInfo(
                index=index_eol.removeprefix("i/"),
                worktree=worktree_eol.removeprefix("w/"),
                attr=" ".join(attr_tokens).removeprefix("attr/"),
            )
        return entries

    def last_commit_time(self, root: Path, relative_path: str) -> str | None:
        """Committer time (ISO 8601) of the newest commit touching the file."""
        output = self._run(root, ["log", "-1", "--format=%cI", "--", relative_path])
        return _stripped_or_none(output)

    def config_value(self, root: Path, key: str) -> str | None:
        """Effective ``git config --get <key>`` in ``root`` (lower-cased), or ``None``."""
        value = _stripped_or_none(self._run(root, ["config", "--get", key]))
        return value.lower() if value else None

    def resolves_to_commit(self, root: Path, prefix: str) -> bool:
        """True when ``prefix`` names exactly one commit object in ``root``."""
        output = self._run(
            root, ["rev-parse", "--verify", "--quiet", f"{prefix}^{{commit}}"]
        )
        return bool(output and output.strip())

    def tracked_paths(
        self, root: Path, relative_paths: list[str], revision: str | None = None
    ) -> set[str] | None:
        """The given paths that git tracks: in the index, or in ``revision``'s tree.

        Returns ``None`` when git could not answer (the caller reports "unknown").
        """
        tracked: set[str] = set()
        for chunk in _path_chunks(relative_paths):
            if revision is None:
                arguments = ["--literal-pathspecs", "ls-files", "-z", "--", *chunk]
            else:
                arguments = [
                    "--literal-pathspecs",
                    "ls-tree",
                    "-r",
                    "-z",
                    "--name-only",
                    revision,
                    "--",
                    *chunk,
                ]
            output = self._run(root, arguments)
            if output is None:
                return None
            tracked.update(name for name in output.split("\0") if name)
        return tracked

    def ignore_rules(
        self, root: Path, relative_paths: list[str]
    ) -> dict[str, IgnoreRule] | None:
        """``{relative path: matching ignore rule}`` whether or not git tracks the path.

        ``--no-index`` makes git test the ignore rules even for tracked (force-added)
        files. Returns ``None`` when git could not answer.
        """
        if not relative_paths:
            return {}
        # -z needs --stdin: NUL-separated paths need no quoting and no length limit.
        output = self._run(
            root,
            ["check-ignore", "-v", "-z", "--no-index", "--stdin"],
            accepted_codes=(0, CHECK_IGNORE_NO_MATCH),
            stdin_bytes="\0".join(relative_paths).encode("utf-8") + b"\0",
        )
        if output is None:
            return None
        rules: dict[str, IgnoreRule] = {}
        fields = output.split("\0")
        # -v -z output: "source NUL line NUL pattern NUL path NUL" per match.
        for index in range(0, len(fields) - 3, 4):
            source, line, pattern, path = fields[index : index + 4]
            rules[path] = IgnoreRule(source, line, pattern)
        return rules

    def tree_paths(self, root: Path, revision: str) -> list[str] | None:
        """Every file path in ``revision``'s tree (``git ls-tree -r``), or ``None``."""
        output = self._run(root, ["ls-tree", "-r", "-z", "--name-only", revision])
        if output is None:
            return None
        return [name for name in output.split("\0") if name]

    def full_commit(self, root: Path, revision: str) -> str | None:
        """The full commit id ``revision`` names, or ``None``."""
        output = self._run(
            root, ["rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"]
        )
        return _stripped_or_none(output)

    def commit_time(self, root: Path, revision: str) -> str | None:
        """Committer time (ISO 8601) of ``revision``."""
        output = self._run(root, ["log", "-1", "--format=%cI", revision, "--"])
        return _stripped_or_none(output)

    def changed_files(self, root: Path, revision: str) -> list[str] | None:
        """Files ``revision`` added, changed or deleted against its first parent.

        A root commit is compared with the empty tree. A merge commit is compared
        with its first parent through the two-tree ``diff-tree`` form: the one-tree
        form prints nothing for a merge, so before 2026-11-23 the ``--mtime`` check
        of ``baseline_check identity`` saw 0 files on every merge run commit.
        """
        parents = self._run(root, ["log", "-1", "--format=%P", revision, "--"])
        if parents is None:
            return None
        parent_list = parents.split()
        arguments = ["diff-tree", "-r", "-z", "--name-only"]
        if parent_list:
            arguments += [parent_list[0], revision]
        else:
            arguments += ["--root", "--no-commit-id", revision]
        output = self._run(root, arguments)
        if output is None:
            return None
        return [name for name in output.split("\0") if name]

    def same_as_commit(
        self, root: Path, revision: str, relative_path: str
    ) -> bool | None:
        """True when the work-tree file hashes to the blob ``revision`` holds there.

        ``git hash-object`` applies the same clean filters and EOL conversion as
        ``git add``, so a CRLF checkout of an LF blob still compares equal.
        """
        blob_spec = f"{revision}:{relative_path}"
        committed = self._run(root, ["rev-parse", "--verify", "--quiet", blob_spec])
        current = self._run(root, ["hash-object", "--", relative_path])
        if committed is None or current is None:
            return None
        return committed.strip() == current.strip()

    def first_added_time(self, root: Path, relative_path: str) -> str | None:
        """Committer time (ISO 8601) of the commit that added the file, or ``None``."""
        output = self._run(
            root,
            [
                "log",
                "--diff-filter=A",
                "--follow",
                "--format=%cI",
                "--",
                relative_path,
            ],
        )
        if not output:
            return None
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[-1] if lines else None  # git log is newest first


def _stripped_or_none(output: str | None) -> str | None:
    if output is None:
        return None
    return output.strip() or None


def relative_posix(path: Path, root: Path) -> str | None:
    """``path`` relative to ``root`` with forward slashes, or ``None`` if outside."""
    try:
        relative = os.path.relpath(path, root)
    except ValueError:  # another drive
        return None
    if relative.startswith(".."):
        return None
    return relative.replace("\\", "/")
