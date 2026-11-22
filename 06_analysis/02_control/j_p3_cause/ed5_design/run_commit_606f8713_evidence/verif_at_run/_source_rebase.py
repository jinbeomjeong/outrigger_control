"""Rewrite a copied test module so that only its stored-data paths leave the worktree.

``worktree_tests.py`` copies test files (and the ``conftest.py`` / ``__init__.py``
above them) out of a git worktree into a scratch tree. Two text edits make the
copy behave like the original except for the data it reads:

* every ``__file__`` name becomes the original file's absolute path as a string
  literal, so ``Path(__file__).resolve().parents[2]`` is still the worktree root
  and code, fixtures and helper paths stay on the worktree;
* every path expression that joins a rebased folder name (default
  ``07_results``) is wrapped in ``__import__("_wt_probe").rebase_data(...)``,
  which maps ``<worktree>/07_results/...`` to ``<data root>/07_results/...`` at
  run time. Recognised forms: ``X / "07_results"`` (also ``"07_results/S8"``),
  ``X.joinpath("07_results", ...)`` and calls of ``Path``/``PurePath``/
  ``os.path.join`` with such a literal argument.

Edits are made in place on the source bytes (no new lines), so tracebacks keep
the original line numbers. A string literal that names the folder but is not
inside a wrapped expression (``RESULTS = "07_results"``) is reported, not
guessed at: the copy would still read the worktree there.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

REBASE_CALL_PREFIX = '__import__("_wt_probe").rebase_data('
REBASE_CALL_SUFFIX = ")"
PATH_CALL_NAMES = frozenset({"Path", "PurePath", "WindowsPath", "PosixPath", "join"})
JOINPATH_NAME = "joinpath"
PATH_SEPARATORS = re.compile(r"[\\/]")
MAX_SNIPPET_CHARS = 120


@dataclass(frozen=True)
class SourceEdit:
    """Replace source bytes ``[start, end)`` with ``text`` (equal ends: insert)."""

    start: int
    end: int
    text: str

    @property
    def is_insert(self) -> bool:
        return self.start == self.end


@dataclass(frozen=True)
class SourceNote:
    """A line of the source and what was found there."""

    line: int
    text: str


@dataclass
class RebaseResult:
    """The rewritten source and what the rewrite touched."""

    text: str
    wrapped: list[SourceNote] = field(default_factory=list)
    file_references: int = 0
    unwrapped_literals: list[SourceNote] = field(default_factory=list)


def _first_component(text: str) -> str:
    parts = [part for part in PATH_SEPARATORS.split(text) if part]
    return parts[0] if parts else ""


def _names_folder(text: str, folders: frozenset[str]) -> bool:
    """True when the literal is a relative path whose first part is a rebased folder."""
    return _first_component(text) in folders


def _mentions_folder(text: str, folders: frozenset[str]) -> bool:
    """True when any path part of the literal is a rebased folder."""
    return any(part in folders for part in PATH_SEPARATORS.split(text))


def _is_folder_literal(node: ast.AST, folders: frozenset[str]) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _names_folder(node.value, folders)
    )


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _is_data_path_expression(node: ast.AST, folders: frozenset[str]) -> bool:
    """``X / "07_results"``, ``X.joinpath("07_results")``, ``Path(X, "07_results")``."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_folder_literal(node.right, folders)
    if not isinstance(node, ast.Call):
        return False
    name = _call_name(node)
    if name not in PATH_CALL_NAMES and name != JOINPATH_NAME:
        return False
    return any(_is_folder_literal(argument, folders) for argument in node.args)


def _docstring_nodes(tree: ast.Module) -> set[int]:
    owners = [tree, *ast.walk(tree)]
    docstrings: set[int] = set()
    for owner in owners:
        body = getattr(owner, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        is_string = isinstance(first, ast.Expr) and isinstance(
            first.value, ast.Constant
        )
        if is_string and isinstance(first.value.value, str):
            docstrings.add(id(first.value))
    return docstrings


class _LineOffsets:
    """Absolute byte offsets of ``(lineno, col_offset)`` AST positions (UTF-8)."""

    def __init__(self, source: bytes) -> None:
        self._starts = [0]
        for line in source.splitlines(keepends=True):
            self._starts.append(self._starts[-1] + len(line))

    def at(self, lineno: int, col_offset: int) -> int:
        return self._starts[lineno - 1] + col_offset


def _span(node: ast.AST, offsets: _LineOffsets) -> tuple[int, int]:
    start = offsets.at(node.lineno, node.col_offset)
    end = offsets.at(node.end_lineno, node.end_col_offset)  # type: ignore[arg-type]
    return start, end


def _outermost(nodes: list[ast.AST], offsets: _LineOffsets) -> list[ast.AST]:
    """Drop nodes that lie inside another selected node (one wrap per expression)."""
    spans = [(_span(node, offsets), node) for node in nodes]
    kept = []
    for (start, end), node in spans:
        inside_other = any(
            other is not node and other_start <= start and end <= other_end
            for (other_start, other_end), other in spans
        )
        if not inside_other:
            kept.append(node)
    return kept


def apply_edits(source: bytes, edits: Iterable[SourceEdit]) -> bytes:
    """Apply non-overlapping edits from the end backwards.

    At one offset a replacement goes before an insertion, so a prefix inserted
    at a node start ends up in front of a replaced name that starts there too.
    """
    result = source
    ordered = sorted(edits, key=lambda edit: (edit.start, not edit.is_insert))
    for edit in reversed(ordered):
        result = result[: edit.start] + edit.text.encode("utf-8") + result[edit.end :]
    return result


def _snippet(source_text: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source_text, node) or ""
    flat = " ".join(segment.split())
    return flat[:MAX_SNIPPET_CHARS]


def rebase_source(
    source_text: str, original_path: Path, folders: Iterable[str]
) -> RebaseResult:
    """Return the copy's source with ``__file__`` pinned and data paths wrapped.

    Args:
        source_text: Decoded source of the original module.
        original_path: Absolute path of the original module (``__file__`` value).
        folders: Folder names under the worktree root to rebase (``07_results``).

    Raises:
        SyntaxError: If the original or the rewritten source does not compile.
    """
    folder_set = frozenset(folders)
    tree = ast.parse(source_text)
    source = source_text.encode("utf-8")
    offsets = _LineOffsets(source)
    file_literal = repr(str(original_path))
    edits: list[SourceEdit] = []
    result = RebaseResult(text=source_text)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "__file__":
            start, end = _span(node, offsets)
            edits.append(SourceEdit(start, end, file_literal))
            result.file_references += 1

    selected = [
        node for node in ast.walk(tree) if _is_data_path_expression(node, folder_set)
    ]
    wrapped_spans = []
    for node in _outermost(selected, offsets):
        start, end = _span(node, offsets)
        edits.append(SourceEdit(start, start, REBASE_CALL_PREFIX))
        edits.append(SourceEdit(end, end, REBASE_CALL_SUFFIX))
        wrapped_spans.append((start, end))
        result.wrapped.append(SourceNote(node.lineno, _snippet(source_text, node)))

    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings or not _mentions_folder(node.value, folder_set):
            continue
        start, end = _span(node, offsets)
        if any(low <= start and end <= high for low, high in wrapped_spans):
            continue
        result.unwrapped_literals.append(SourceNote(node.lineno, node.value[:80]))

    rewritten = apply_edits(source, edits).decode("utf-8")
    compile(rewritten, str(original_path), "exec")
    result.text = rewritten
    result.wrapped.sort(key=lambda note: note.line)
    result.unwrapped_literals.sort(key=lambda note: note.line)
    return result
