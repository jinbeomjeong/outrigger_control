"""Gate scan (E axis): static ``ast`` search for gates that may pass on empty input.

Every rule here is a heuristic: a hit says "read this gate", not "this gate is
wrong". The auditor agent decides.

Patterns:

* ``tag_single_compare`` - a tag (``.get("controller_tag")``, ``["tag"]``, a
  name or attribute ending in a tag name) compared with ``==``/``!=`` against
  one string or UPPER_CASE constant; a new tag edition silently selects nothing.
* ``tag_set_compare`` - the same tag tested with ``in`` against a set/tuple/list
  or UPPER_CASE name (the good pattern; listed for the report).
* ``all_without_count_guard`` - ``all(...)`` feeding a ``"pass"``/``"ok"``/
  ``"verdict"`` value, a ``return`` or a pass-like assignment in a function with
  no ``len(...)`` comparison, ``bool(x) and`` or ``if not x`` guard.
* ``empty_pass_not`` - ``"pass": not <name>`` (an empty stop list passes).
* ``min_default`` / ``min_or_zero`` - ``min``/``max`` with ``default=`` or an
  ``or 0`` argument (an empty selection gets a made-up value).
* ``warn_and_continue`` - a warning call not followed, in the same block, by
  ``return``/``raise``/``sys.exit``/``continue``/``break``.
* ``empty_selection_sum_pass`` - a filtered selection (comprehension with
  ``if``, ``filter``, ``append`` under ``if``) feeds ``sum``/``any``/``all``/
  ``len`` into a decision whose ``else`` or default is a pass, and the function
  has no zero check of that selection (see ``_selection_flow``; 2026-11-17).
* ``missing_key_default_pass`` - with every looked-up key missing, a default
  (``x.get(k, 0)``, ``x.get(k) or [0]``) skips a failure action, takes a pass
  branch, makes a pass value true or leaves a failure list empty; a decision
  that reads a default in an undetermined direction is ``missing_key_default``
  info (see ``_absence_flow``; 2026-11-20). ``--bare-get`` also counts a plain
  ``x.get(k)`` (``None``) as a default.
* ``row_value_path_no_base`` - a record value (``row["file"]``,
  ``rec.get("path")``, a name assigned from one) is opened as a path with no
  base folder (``Path(v)``, ``open(v)``, ``np.load(v)``, ...): a bare file name
  resolves against the current folder. A comment saying the value is absolute
  makes it the info ``row_value_path_noted`` (see ``_row_paths``; 2026-11-21).
  ``--no-row-paths`` turns both off.
* ``count_guard`` - ``len(x) == N`` / ``== *_COUNT`` (good pattern, listed).

Usage:
    python gate_scan.py PATH [PATH ...] [--tag-names controller_tag,tag,setting]
                        [--allow-tags REGEX] [--bare-get] [--no-row-paths]
                        [--out REPORT] [--format md|json] [--fail-on error|warning]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _absence_flow import find_absence_passes
from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import collect_python_files, read_text_facts, require_output_outside
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
from _row_paths import find_row_value_paths
from _selection_flow import find_selection_passes

TOOL_NAME = "gate_scan"
DEFAULT_TAG_NAMES = "controller_tag,tag,setting"
MODULE_SCOPE = "<module>"
PASS_KEYS = frozenset({"pass", "ok", "verdict"})
PASS_LIKE_NAME = re.compile(r"^(is_)?(pass|passed|pass_|ok|verdict)$", re.IGNORECASE)
UPPER_CASE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
COUNT_NAME = re.compile(r"COUNT$", re.IGNORECASE)
WARNING_CALLS = frozenset(
    {
        "warnings.warn",
        "logging.warning",
        "logger.warning",
        "log.warning",
        "logging.warn",
    }
)
EXIT_CALLS = frozenset({"sys.exit", "exit", "os._exit"})
GOOD_PATTERN_CATEGORIES = ("count_guard", "tag_set_compare")
MAX_SOURCE_CHARS = 90


@dataclass
class Hit:
    """A finding plus the function it sits in."""

    finding: Finding
    function: str
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            **finding_to_dict(self.finding),
            "function": self.function,
            "source": self.source,
        }


@dataclass(frozen=True)
class ScanOptions:
    """Optional rules chosen on the command line."""

    include_bare_get: bool = False
    include_row_paths: bool = True


@dataclass
class ScanStats:
    files: int = 0
    functions_scanned: int = 0
    unparsable: list[str] = field(default_factory=list)


# --- expression helpers ---------------------------------------------------------


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _is_call_to(node: ast.AST, *names: str) -> bool:
    return isinstance(node, ast.Call) and _dotted_name(node.func) in names


def _is_get_call(node: ast.AST) -> bool:
    """``<x>.get(<key>, ...)``."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and bool(node.args)
    )


def _is_upper_constant(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return bool(UPPER_CASE_NAME.match(node.id))
    if isinstance(node, ast.Attribute):
        return bool(UPPER_CASE_NAME.match(node.attr))
    return False


def _is_constant_like(node: ast.AST) -> bool:
    is_string = isinstance(node, ast.Constant) and isinstance(node.value, str)
    return is_string or _is_upper_constant(node)


def _constant_text(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    return _dotted_name(node)


@dataclass(frozen=True)
class TagMatcher:
    """Decides whether an expression reads a tag field."""

    tag_names: tuple[str, ...]
    allow: re.Pattern[str] | None

    def is_tag(self, node: ast.AST) -> bool:
        if _is_upper_constant(node):
            return False
        if _is_get_call(node):
            return self._is_tag_key(node.args[0])
        if isinstance(node, ast.Subscript):
            return self._is_tag_key(node.slice)
        if isinstance(node, ast.Name):
            return self._ends_with_tag(node.id)
        if isinstance(node, ast.Attribute):
            return self._ends_with_tag(node.attr)
        return False

    def is_allowed(self, constant: ast.AST) -> bool:
        return self.allow is not None and bool(
            self.allow.search(_constant_text(constant))
        )

    def _is_tag_key(self, key: ast.AST) -> bool:
        return isinstance(key, ast.Constant) and key.value in self.tag_names

    def _ends_with_tag(self, name: str) -> bool:
        lowered = name.lower()
        return any(lowered.endswith(tag.lower()) for tag in self.tag_names)


def _is_collection_like(node: ast.AST) -> bool:
    return isinstance(node, (ast.Tuple, ast.Set, ast.List)) or _is_upper_constant(node)


def _is_count_operand(node: ast.AST) -> bool:
    if _is_call_to(node, "len"):
        return True
    name = node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")
    return bool(name) and bool(COUNT_NAME.search(name))


# --- function-level guard detection ---------------------------------------------


def _has_count_guard(body_nodes: list[ast.AST]) -> bool:
    """``len(...)`` compared, ``bool(x) and ...`` or ``if not x`` anywhere in the body."""
    for root in body_nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Compare):
                operands = [node.left, *node.comparators]
                if any(_is_count_operand(operand) for operand in operands):
                    return True
            is_and = isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And)
            if is_and and _is_call_to(node.values[0], "bool"):
                return True
            if isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp):
                is_not = isinstance(node.test.op, ast.Not)
                if is_not and isinstance(
                    node.test.operand, (ast.Name, ast.Attribute, ast.Subscript)
                ):
                    return True
    return False


def _contains_all_call(node: ast.AST) -> ast.Call | None:
    for inner in ast.walk(node):
        if _is_call_to(inner, "all"):
            return inner  # type: ignore[return-value]
    return None


def _assignment_is_pass_like(node: ast.Assign) -> bool:
    for target in node.targets:
        if isinstance(target, ast.Name) and PASS_LIKE_NAME.match(target.id):
            return True
        is_constant_key = isinstance(target, ast.Subscript) and isinstance(
            target.slice, ast.Constant
        )
        if is_constant_key and target.slice.value in PASS_KEYS:
            return True
    return False


def _pass_dict_values(node: ast.Dict) -> list[ast.AST]:
    return [
        value
        for key, value in zip(node.keys, node.values, strict=False)
        if isinstance(key, ast.Constant) and key.value in PASS_KEYS
    ]


# --- the visitor ------------------------------------------------------------------


class GateVisitor(ast.NodeVisitor):
    """Walks one module and records hits with their enclosing function."""

    def __init__(
        self,
        path: Path,
        source: str,
        matcher: TagMatcher,
        include_bare_get: bool = False,
        include_row_paths: bool = True,
    ) -> None:
        self.path = path
        self.module = path.stem
        self.lines = source.splitlines()
        self.matcher = matcher
        self.include_bare_get = include_bare_get
        self.include_row_paths = include_row_paths
        self.scope: list[str] = []
        self.hits: list[Hit] = []
        self.functions = 0
        self._guarded: list[bool] = []

    # scope handling
    def _function(self) -> str:
        return ".".join(self.scope) if self.scope else MODULE_SCOPE

    def _add(
        self, severity: Severity, category: str, node: ast.AST, message: str
    ) -> None:
        line = getattr(node, "lineno", 0)
        source = (
            self.lines[line - 1].strip()[:MAX_SOURCE_CHARS]
            if 0 < line <= len(self.lines)
            else ""
        )
        target = f"{self.module}:{self._function()}"
        finding = Finding(severity, category, str(self.path), line, message, target)
        self.hits.append(Hit(finding, self._function(), source))

    def scan_module(self, tree: ast.Module) -> None:
        self._guarded.append(_has_count_guard(tree.body))
        self._scan_blocks(tree)
        self._scan_scope_flows(tree.body)
        self.generic_visit(tree)
        self._guarded.pop()

    def _scan_scope_flows(self, statements: list[ast.stmt]) -> None:
        """Findings that follow names through one function body (or the module)."""
        for selection_pass in find_selection_passes(statements):
            self._add(
                Severity.WARNING,
                "empty_selection_sum_pass",
                selection_pass.node,
                selection_pass.message(),
            )
        for absence in find_absence_passes(statements, self.include_bare_get):
            if absence.is_warning:
                severity, category = Severity.WARNING, "missing_key_default_pass"
            else:
                severity, category = Severity.INFO, "missing_key_default"
            self._add(severity, category, absence.node, absence.message())
        if not self.include_row_paths:
            return
        for row_path in find_row_value_paths(statements, self.lines):
            if row_path.is_noted:
                severity, category = Severity.INFO, "row_value_path_noted"
            else:
                severity, category = Severity.WARNING, "row_value_path_no_base"
            self._add(severity, category, row_path.node, row_path.message())

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.functions += 1
        self.scope.append(node.name)
        self._guarded.append(_has_count_guard(node.body))
        self._scan_blocks(node)
        self._scan_scope_flows(node.body)
        self.generic_visit(node)
        self._guarded.pop()
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    # patterns on single nodes
    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        for left, operator, right in zip(
            operands, node.ops, operands[1:], strict=False
        ):
            self._check_tag_pair(node, left, operator, right)
            if isinstance(operator, ast.Eq) and (
                _is_count_operand(left) or _is_count_operand(right)
            ):
                self._add(Severity.INFO, "count_guard", node, "건수 대조(좋은 패턴)")
        self.generic_visit(node)

    def _check_tag_pair(
        self, node: ast.Compare, left: ast.AST, operator: ast.cmpop, right: ast.AST
    ) -> None:
        if isinstance(operator, (ast.Eq, ast.NotEq)):
            for tag_side, other in ((left, right), (right, left)):
                if self.matcher.is_tag(tag_side) and _is_constant_like(other):
                    if self.matcher.is_allowed(other):
                        return
                    symbol = "==" if isinstance(operator, ast.Eq) else "!="
                    message = (
                        f"태그 단일 비교 {symbol} {_constant_text(other)!r}: 새 태그 판에서 "
                        "아무것도 고르지 못할 수 있음 → 태그 집합·meta 판별 권장"
                    )
                    self._add(Severity.WARNING, "tag_single_compare", node, message)
                    return
        is_membership = isinstance(operator, (ast.In, ast.NotIn))
        if is_membership and self.matcher.is_tag(left) and _is_collection_like(right):
            self._add(
                Severity.INFO, "tag_set_compare", node, "태그 집합 비교(좋은 패턴)"
            )

    def visit_Call(self, node: ast.Call) -> None:
        if _is_call_to(node, "min", "max"):
            name = _dotted_name(node.func)
            if any(keyword.arg == "default" for keyword in node.keywords):
                self._add(
                    Severity.INFO,
                    "min_default",
                    node,
                    f"{name}(..., default=): 빈 입력에 기본값",
                )
            if any(self._has_or_zero(argument) for argument in node.args):
                self._add(
                    Severity.INFO,
                    "min_or_zero",
                    node,
                    f"{name}() 인자에 `or 0`: 빈 값을 0으로 대체",
                )
        self.generic_visit(node)

    @staticmethod
    def _has_or_zero(argument: ast.AST) -> bool:
        for inner in ast.walk(argument):
            if isinstance(inner, ast.BoolOp) and isinstance(inner.op, ast.Or):
                last = inner.values[-1]
                if (
                    isinstance(last, ast.Constant)
                    and last.value == 0
                    and not isinstance(last.value, bool)
                ):
                    return True
        return False

    def visit_Dict(self, node: ast.Dict) -> None:
        for value in _pass_dict_values(node):
            self._check_pass_value(value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if _assignment_is_pass_like(node):
            self._check_pass_value(node.value)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self._check_all_call(node.value)
        self.generic_visit(node)

    def _check_pass_value(self, value: ast.AST) -> None:
        is_not = isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not)
        if is_not and isinstance(
            value.operand, (ast.Name, ast.Subscript, ast.Attribute)
        ):
            message = '`"pass": not <목록>`: 멈춤 목록이 비면(선택 0건 포함) 통과'
            self._add(Severity.WARNING, "empty_pass_not", value, message)
        self._check_all_call(value)

    def _check_all_call(self, value: ast.AST) -> None:
        call = _contains_all_call(value)
        if call is None or (self._guarded and self._guarded[-1]):
            return
        message = "all(...)이 판정값인데 같은 함수에 건수 가드(len 비교·bool(x) and·if not x)가 없음: all([])은 참"
        self._add(Severity.WARNING, "all_without_count_guard", call, message)

    # warn-and-continue needs statement lists
    def _scan_blocks(self, owner: ast.AST) -> None:
        for block in _own_blocks(owner):
            self._check_block(block)

    def _check_block(self, block: list[ast.stmt]) -> None:
        for position, statement in enumerate(block):
            if not (
                isinstance(statement, ast.Expr)
                and self._is_warning_call(statement.value)
            ):
                continue
            rest = block[position + 1 :]
            if not any(_stops_flow(item) for item in rest):
                message = "경고만 내고 같은 블록에서 return·raise·exit·continue·break 없이 진행"
                self._add(Severity.INFO, "warn_and_continue", statement, message)

    @staticmethod
    def _is_warning_call(node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        if _dotted_name(node.func) in WARNING_CALLS:
            return True
        if _dotted_name(node.func) == "print" and node.args:
            first = node.args[0]
            if isinstance(first, ast.JoinedStr) and first.values:
                first = first.values[0]
            return isinstance(first, ast.Constant) and str(first.value).startswith(
                "WARN"
            )
        return False


def _own_blocks(owner: ast.AST) -> list[list[ast.stmt]]:
    """Statement lists of ``owner``, not descending into nested defs and classes.

    Nested functions are scanned when the visitor reaches them, with their own scope.
    """
    blocks: list[list[ast.stmt]] = []
    pending = [owner]
    while pending:
        node = pending.pop()
        for attribute in ("body", "orelse", "finalbody"):
            block = getattr(node, attribute, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                blocks.append(block)
        for child in ast.iter_child_nodes(node):
            if not isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                pending.append(child)
    return blocks


def _stops_flow(statement: ast.stmt) -> bool:
    for node in ast.walk(statement):
        if isinstance(node, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
            return True
        if isinstance(node, ast.Call) and _dotted_name(node.func) in EXIT_CALLS:
            return True
    return False


# --- running ------------------------------------------------------------------------


def _scan_file(
    path: Path, matcher: TagMatcher, stats: ScanStats, options: ScanOptions
) -> list[Hit]:
    source = read_text_facts(path).text
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        stats.unparsable.append(str(path))
        finding = Finding(
            Severity.INFO,
            "unparsable",
            str(path),
            error.lineno or 0,
            f"구문 오류: {error.msg}",
        )
        return [Hit(finding, MODULE_SCOPE)]
    visitor = GateVisitor(
        path, source, matcher, options.include_bare_get, options.include_row_paths
    )
    visitor.scan_module(tree)
    stats.files += 1
    stats.functions_scanned += visitor.functions
    # A dict inside a return is reached twice (via the return and the dict).
    unique: dict[tuple[int, str, str], Hit] = {}
    for hit in visitor.hits:
        key = (hit.finding.line, hit.finding.category, hit.finding.message)
        unique.setdefault(key, hit)
    return list(unique.values())


def _good_pattern_table(hits: list[Hit]) -> list[str]:
    good = [hit for hit in hits if hit.finding.category in GOOD_PATTERN_CATEGORIES]
    if not good:
        return ["좋은 패턴 없음."]
    lines = ["| 분류 | 위치 | 함수 | 코드 |", "|---|---|---|---|"]
    for hit in good:
        code = hit.source.replace("|", "\\|")
        lines.append(
            f"| {hit.finding.category} | {Path(hit.finding.file).name}:{hit.finding.line} "
            f"| {hit.function} | `{code}` |"
        )
    return lines


def _markdown(stats: ScanStats, hits: list[Hit]) -> list[str]:
    risky = [
        hit.finding
        for hit in hits
        if hit.finding.category not in GOOD_PATTERN_CATEGORIES
    ]
    lines = [
        "# 관문 빈 집합 점검 (gate_scan)",
        "",
        f"- 파일 {stats.files}개, 함수 {stats.functions_scanned}개",
        "- 모두 휴리스틱이다. 확정 판정은 감사 에이전트가 코드를 읽고 내린다.",
        "",
        "## 점검할 관문",
        "",
        *findings_markdown(sort_findings(risky)),
        "",
        "## 좋은 패턴 (건수 대조·태그 집합)",
        "",
        *_good_pattern_table(hits),
    ]
    return lines


def run_gate_scan(args: argparse.Namespace) -> ToolOutcome:
    """Scan the given Python files and folders."""
    files, folders = collect_python_files(args.paths)
    if not files:
        raise InputError("no Python files found")
    require_output_outside(args.out, files, folders)
    try:
        allow = re.compile(args.allow_tags) if args.allow_tags else None
    except re.error as error:
        raise InputError(f"invalid --allow-tags regex: {error}") from error
    tag_names = tuple(
        name.strip() for name in args.tag_names.split(",") if name.strip()
    )
    matcher = TagMatcher(tag_names, allow)

    stats = ScanStats()
    options = ScanOptions(args.bare_get, not args.no_row_paths)
    hits: list[Hit] = []
    for path in files:
        hits += _scan_file(path, matcher, stats, options)
    hits.sort(
        key=lambda hit: (hit.finding.file, hit.finding.line, hit.finding.category)
    )
    findings = [hit.finding for hit in hits]

    summary = {
        "tool": TOOL_NAME,
        "command": "scan",
        "files": stats.files,
        "functions_scanned": stats.functions_scanned,
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "tag_names": list(tag_names),
        "allow_tags": args.allow_tags,
        "bare_get": args.bare_get,
        "row_paths": not args.no_row_paths,
        "summary": summary,
        "findings": [hit.to_dict() for hit in hits],
    }
    lines = deliver_report(args, _markdown(stats, hits), report, files)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="gate_scan.py",
        description="빈 선택·0건에서 통과로 끝날 수 있는 관문을 정적으로 찾는다(휴리스틱).",
    )
    parser.add_argument("paths", nargs="+", help="Python files or folders")
    parser.add_argument(
        "--tag-names",
        default=DEFAULT_TAG_NAMES,
        help=f"comma-separated tag field names (default {DEFAULT_TAG_NAMES})",
    )
    parser.add_argument(
        "--allow-tags", help="regex; matching constants are not reported"
    )
    parser.add_argument(
        "--bare-get",
        action="store_true",
        help="also report x.get(k) without a default (None) in missing_key_default*",
    )
    parser.add_argument(
        "--no-row-paths",
        action="store_true",
        help="skip row_value_path_no_base / row_value_path_noted (the rules "
        "before 2026-11-21)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_gate_scan(args))


if __name__ == "__main__":
    sys.exit(main())
