"""``row_value_path_no_base`` for gate_scan: a value read from a record or row is
opened as a path with no base folder, so a bare file name resolves against the
current folder (CWD).

The case (2026-11-21, 436.9 J-P3 ``jp3_baseline_compare.py``)::

    new_npz = Path(new["t4h_file"])          # run_v5 stores the file NAME only
    reads = compare_reads(..., new_npz, ...)  # FileNotFoundError unless CWD is right

* A *record value* is ``x["key"]`` or ``x.get("key"[, default])`` with a string
  constant key (``os.environ`` excluded), also through ``str(...)``,
  ``os.fspath(...)`` and ``... or default``; a name assigned once from one
  (``name = row["file"]``) or a ``for`` / comprehension target over one
  (``for name in rec["files"]``) carries it.
* An *opener* is ``Path(v)`` / ``PurePath(v)`` with one argument, ``open``,
  ``np.load`` / ``loadtxt`` / ``genfromtxt`` / ``fromfile``, ``pd.read_*``,
  ``h5py.File``, ``loadmat``, ``Image.open``, ``cv2.imread``, ``ZipFile``,
  ``tarfile.open``, given the record value as its path argument.
* Not reported: ``base / Path(v)`` (joined at once); ``Path(v).name`` and other
  attributes that only read the name (``stem``, ``suffix``, ``parts``,
  ``is_absolute``, ...); a ``Path(v)`` assigned to a name that is later joined
  (``base / p``, ``x.joinpath(p)``, ``os.path.join(a, p)``); a value whose name
  or key is tested with ``.is_absolute()`` / ``os.path.isabs`` in the scope.
* A comment on the opener's line or the line above saying the value is absolute
  (``absolute``, ``abs path``, ``절대``) turns the warning into the info
  ``row_value_path_noted``: the auditor still checks that the writer stores an
  absolute path.

Heuristic only: values passed through other functions, attributes or
containers are not followed.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

PATH_CONSTRUCTORS = frozenset({"Path", "pathlib.Path", "PurePath", "pathlib.PurePath"})
FILE_OPENERS = frozenset(
    {
        "open", "io.open", "builtins.open",
        "np.load", "numpy.load", "np.loadtxt", "numpy.loadtxt",
        "np.genfromtxt", "numpy.genfromtxt", "np.fromfile", "numpy.fromfile",
        "pd.read_csv", "pandas.read_csv", "pd.read_json", "pandas.read_json",
        "pd.read_parquet", "pandas.read_parquet", "pd.read_excel", "pandas.read_excel",
        "pd.read_table", "pandas.read_table",
        "h5py.File", "scipy.io.loadmat", "sio.loadmat", "loadmat",
        "Image.open", "PIL.Image.open", "cv2.imread",
        "zipfile.ZipFile", "ZipFile", "tarfile.open",
    }
)  # fmt: skip
PATH_KEYWORDS = frozenset(
    {"file", "path", "fname", "filename", "filepath_or_buffer", "name", "fp"}
)
UNWRAP_CALLS = frozenset({"str", "os.fspath", "fspath"})
NAME_ONLY_ATTRIBUTES = frozenset(
    {"name", "stem", "suffix", "suffixes", "parts", "is_absolute", "anchor",
     "drive", "root", "match"}
)  # fmt: skip
JOIN_CALLS = frozenset({"os.path.join", "path.join", "posixpath.join", "ntpath.join"})
ABSOLUTE_CHECK_CALLS = frozenset({"os.path.isabs", "path.isabs"})
ENVIRONMENT_RECEIVERS = ("environ",)
NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
ABSOLUTE_NOTE = re.compile(r"#.*\b(absolute|abs[\s_-]?path)|#.*절대", re.IGNORECASE)
MAX_EXPRESSION_CHARS = 60


@dataclass(frozen=True)
class RecordValue:
    """Where a path value came from: the record expression and its key."""

    key: str
    source: str
    line: int
    via_name: str | None = None


@dataclass(frozen=True)
class RowValuePath:
    """One opener that receives a record value with no base folder."""

    node: ast.Call
    opener: str
    value: RecordValue
    note: str | None

    @property
    def is_noted(self) -> bool:
        return self.note is not None

    def message(self) -> str:
        origin = f"`{self.value.source}`(키 `{self.value.key}`)"
        if self.value.via_name:
            origin = f"`{self.value.via_name}` ← {origin}, 줄 {self.value.line}"
        text = (
            f"레코드 값 {origin}을 기준 폴더 없이 `{self.opener}(...)`로 엶: "
            "값이 파일 이름·상대 경로면 현재 폴더(CWD) 기준으로 열린다 "
            "→ `<기준 폴더> / 값`으로 잇거나 절대 경로를 단언"
        )
        if self.note:
            text += f" (절대 경로 주석: {self.note})"
        return text


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _scope_nodes(statements: list[ast.stmt]) -> Iterator[ast.AST]:
    """Every node of the scope, not entering nested functions and classes."""
    pending: list[ast.AST] = [
        statement
        for statement in statements
        if not isinstance(statement, NESTED_SCOPES)
    ]
    while pending:
        node = pending.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, NESTED_SCOPES):
                pending.append(child)


def _source_of(node: ast.AST) -> str:
    return ast.unparse(node)[:MAX_EXPRESSION_CHARS]


def _string_key(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_environment(receiver: ast.AST) -> bool:
    return _dotted_name(receiver).endswith(ENVIRONMENT_RECEIVERS)


def _unwrapped(node: ast.AST) -> ast.AST:
    """Strip ``str(...)``, ``os.fspath(...)`` and ``x or default``."""
    while True:
        if isinstance(node, ast.Call) and _dotted_name(node.func) in UNWRAP_CALLS:
            if len(node.args) != 1:
                return node
            node = node.args[0]
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            node = node.values[0]
        else:
            return node


def direct_record_value(node: ast.AST) -> RecordValue | None:
    """``x["key"]`` / ``x.get("key")`` (possibly wrapped), else None."""
    node = _unwrapped(node)
    line = getattr(node, "lineno", 0)
    if isinstance(node, ast.Subscript):
        key = _string_key(node.slice)
        if key is not None and not _is_environment(node.value):
            return RecordValue(key, _source_of(node), line)
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
    ):
        return None
    if _is_environment(node.func.value):
        return None
    key = _string_key(node.args[0])
    return None if key is None else RecordValue(key, _source_of(node), line)


class RowPathAnalysis:
    """Find record values opened as paths in one scope."""

    def __init__(self, statements: list[ast.stmt], lines: list[str]) -> None:
        self.nodes = list(_scope_nodes(statements))
        self.lines = lines
        self.parents: dict[int, ast.AST] = {}
        for node in self.nodes:
            for child in ast.iter_child_nodes(node):
                self.parents[id(child)] = node
        self.carriers = self._carrier_names()
        self.joined_names = self._joined_names()
        self.checked = self._absolute_checked()

    # names that carry a record value ----------------------------------------
    def _bindings(self) -> Iterator[tuple[str, ast.AST, bool]]:
        """``(name, value, is_iteration)`` for each simple binding of the scope."""
        for node in self.nodes:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    yield target.id, node.value, False
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                if isinstance(node.target, ast.Name):
                    yield node.target.id, node.value, False
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                if isinstance(node.target, ast.Name):
                    yield node.target.id, node.iter, True

    def _carrier_names(self) -> dict[str, RecordValue]:
        """Names bound exactly once to a record value (or to ``Path(record value)``).

        A ``Path(...)`` carrier is kept apart in ``path_carriers``: it is not a
        path argument of its own (its ``Path(...)`` call is the finding), but an
        absolute check of it covers the record key.
        """
        bound_count: dict[str, int] = {}
        carriers: dict[str, RecordValue] = {}
        self.path_carriers: dict[str, RecordValue] = {}
        for name, value, is_iteration in self._bindings():
            bound_count[name] = bound_count.get(name, 0) + 1
            if _is_path_constructor(value):
                record = direct_record_value(value.args[0])  # type: ignore[attr-defined]
                if record is not None:
                    self.path_carriers[name] = record
                continue
            record = direct_record_value(value)
            if record is not None:
                key = f"{record.key}[]" if is_iteration else record.key
                carriers[name] = RecordValue(key, record.source, record.line, name)
        # A lambda parameter shadows a scope name of the same spelling.
        for name in self._lambda_parameters():
            bound_count[name] = bound_count.get(name, 0) + 1
        self.path_carriers = {
            name: value
            for name, value in self.path_carriers.items()
            if bound_count[name] == 1
        }
        return {
            name: value for name, value in carriers.items() if bound_count[name] == 1
        }

    def _lambda_parameters(self) -> set[str]:
        names: set[str] = set()
        for node in self.nodes:
            if isinstance(node, ast.Lambda):
                arguments = node.args
                every = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
                names |= {argument.arg for argument in every}
        return names

    def record_value(self, node: ast.AST) -> RecordValue | None:
        direct = direct_record_value(node)
        if direct is not None:
            return direct
        node = _unwrapped(node)
        if isinstance(node, ast.Name):
            return self.carriers.get(node.id)
        return None

    # joins and absolute checks ------------------------------------------------
    def _joined_names(self) -> set[str]:
        """Names used as the right side of ``/`` or a join argument after the first."""
        joined: set[str] = set()
        for node in self.nodes:
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Name):
                    joined.add(node.right.id)
            elif isinstance(node, ast.Call):
                is_joinpath = (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "joinpath"
                )
                arguments = node.args if is_joinpath else []
                if _dotted_name(node.func) in JOIN_CALLS:
                    arguments = node.args[1:]
                joined |= {arg.id for arg in arguments if isinstance(arg, ast.Name)}
        return joined

    def _absolute_checked(self) -> set[str]:
        """Names and record keys tested with ``is_absolute()`` / ``os.path.isabs``."""
        checked: set[str] = set()
        for node in self.nodes:
            if not isinstance(node, ast.Call):
                continue
            subject: ast.AST | None = None
            if isinstance(node.func, ast.Attribute) and node.func.attr == "is_absolute":
                subject = node.func.value
                if _is_path_constructor(subject):
                    subject = subject.args[0]  # type: ignore[attr-defined]
            elif _dotted_name(node.func) in ABSOLUTE_CHECK_CALLS and node.args:
                subject = node.args[0]
            if subject is None:
                continue
            record = self.record_value(subject)
            if record is not None:
                checked |= {record.key, record.via_name or ""}
            subject = _unwrapped(subject)
            if isinstance(subject, ast.Name):
                checked.add(subject.id)
                path_record = self.path_carriers.get(subject.id)
                if path_record is not None:
                    checked.add(path_record.key)
        checked.discard("")
        return checked

    # openers -----------------------------------------------------------------
    def _path_argument(self, call: ast.Call) -> ast.AST | None:
        name = _dotted_name(call.func)
        if name in PATH_CONSTRUCTORS:
            return call.args[0] if len(call.args) == 1 and not call.keywords else None
        if name not in FILE_OPENERS:
            return None
        if call.args:
            return call.args[0]
        for keyword in call.keywords:
            if keyword.arg in PATH_KEYWORDS:
                return keyword.value
        return None

    def _name_only_use(self, call: ast.Call) -> bool:
        """``Path(v).name``, also through ``.parent`` (``Path(v).parent.name``)."""
        node: ast.AST = call
        parent = self.parents.get(id(node))
        while isinstance(parent, ast.Attribute) and parent.attr == "parent":
            node, parent = parent, self.parents.get(id(parent))
        return isinstance(parent, ast.Attribute) and parent.attr in NAME_ONLY_ATTRIBUTES

    def _is_joined_or_name_only(self, call: ast.Call) -> bool:
        """``base / Path(v)``, ``Path(v).name`` or ``p = Path(v)`` joined later."""
        if not _is_path_constructor(call):
            return False
        if self._name_only_use(call):
            return True
        parent = self.parents.get(id(call))
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
            return parent.right is call
        if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
            target = parent.targets[0]
            covered = self.joined_names | self.checked
            return isinstance(target, ast.Name) and target.id in covered
        return False

    def _note_near(self, line: int) -> str | None:
        for number in (line, line - 1):
            if 0 < number <= len(self.lines):
                match = ABSOLUTE_NOTE.search(self.lines[number - 1])
                if match:
                    return match.group(0)[:MAX_EXPRESSION_CHARS]
        return None

    def run(self) -> list[RowValuePath]:
        found: list[RowValuePath] = []
        for node in self.nodes:
            if not isinstance(node, ast.Call):
                continue
            argument = self._path_argument(node)
            record = self.record_value(argument) if argument is not None else None
            if record is None or self._is_joined_or_name_only(node):
                continue
            if record.key in self.checked or (record.via_name in self.checked):
                continue
            note = self._note_near(node.lineno)
            found.append(RowValuePath(node, _dotted_name(node.func), record, note))
        return sorted(found, key=lambda item: item.node.lineno)


def _is_path_constructor(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _dotted_name(node.func) in PATH_CONSTRUCTORS
        and len(node.args) == 1
    )


def find_row_value_paths(
    statements: list[ast.stmt], lines: list[str]
) -> list[RowValuePath]:
    """Record values opened as paths without a base folder in one scope."""
    return RowPathAnalysis(statements, lines).run()
