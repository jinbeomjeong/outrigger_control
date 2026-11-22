"""``empty_selection_sum_pass`` for gate_scan: an aggregate over a filtered selection
decides a pass, and nothing handles the selection being empty.

The shape (2026-11-16, J-P3 judgement at commit 221456d)::

    judged = [record for record, case in zip(records, cases) if case == JUDGED]
    sums = {key: sum(total(record, key) for record in judged) for key in KEYS}
    if not records:            # guards the input, not the selection
        status = "no_runs"
    elif any(sums.values()):   # decision from an aggregate over the selection
        status = "H-7"
    else:
        status = "pass"        # zero judged rows also land here

* A *selection* is a name bound to a filtered comprehension (``... if ...``),
  ``filter(...)`` (also inside ``list``/``sorted``), an empty list filled by
  ``append``/``add`` under an ``if`` inside a ``for`` loop, or a plain mapping
  comprehension over another selection (it carries that selection's emptiness).
* A selection is *aggregated* when it is passed whole to ``all``/``sum``/``max``/
  ``min``/``fsum``/``mean``, when a comprehension passed to those or to ``any``
  iterates it, or when a ``for`` loop over it accumulates (``+=``, ``x = f(x)``,
  a ``True``/``False`` flag, ``append``). Names assigned from an aggregate are
  followed (two passes). A truth test, ``any(x)`` or ``len`` of a selection is not
  an aggregate: that is the failure-set idiom (``"fail" if failed else "pass"``),
  where an empty set is the normal pass.
* A *decision* is an ``if``/``elif`` chain whose tests read an aggregate and
  which passes in a branch, in its ``else``, through a pass default assigned
  before it, or through a ``return "pass"`` after a stopping branch; a
  conditional expression with a pass branch; or a pass-like value
  (``ok = ...``, ``"pass": ...``).
* A *zero check* of a name is ``not x``, ``not len(x)``, ``bool(x)`` or a
  comparison with ``len(x)`` (or with a name bound to ``len(x)``) anywhere in the
  same function, except inside a test or value that itself yields the pass; there
  only ``x and ...`` / ``len(x) > 0 and ...`` count. A selection is also covered
  when a selection it was filtered from is covered (a failure subset of checked
  rows); a raw input such as a parameter never covers it.

Heuristic only: data flow through calls, attributes, containers and other
functions is not followed.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

# Calls that fold a whole collection into one value; a selection passed to them
# as an argument is aggregated (``all([])`` is True, ``sum([])`` is 0).
POPULATION_CALLS = frozenset(
    {"all", "sum", "max", "min", "fsum", "math.fsum", "statistics.mean", "mean"}
)
# ... and these also aggregate a comprehension passed to them (any(f(r) for r in x)).
ITERATING_CALLS = POPULATION_CALLS | {"any"}
ACCUMULATING_METHODS = frozenset({"append", "add", "extend", "update"})
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
NON_VERDICT_VALUES = (*COMPREHENSIONS, ast.List, ast.Tuple, ast.Set, ast.Dict)
LEN_CALL = frozenset({"len"})
BOOL_CALL = frozenset({"bool"})
FILTER_CALL = frozenset({"filter"})
COLLECTION_ADD_METHODS = frozenset({"append", "add", "extend"})
EMPTY_COLLECTION_CALLS = frozenset({"list", "set", "dict"})
WRAPPER_CALLS = frozenset({"list", "tuple", "set", "sorted"})
PASS_TEXT = re.compile(r"^(pass|passed|ok|통과)$", re.IGNORECASE)
PASS_CONSTANT_NAME = re.compile(r"(^|_)(PASS|PASSED|OK)$")
PASS_TARGET_NAME = re.compile(r"^(is_)?(pass|passed|pass_|ok|verdict)$", re.IGNORECASE)
PASS_KEYS = frozenset({"pass", "ok", "verdict", "status", "result"})
PASS_VALUE_KEYS = frozenset({"pass", "ok"})
NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
# A loop counter compared as a minimum: `counted < K` or `K > counted`.
MINIMUM_ON_LEFT = (ast.Lt, ast.LtE, ast.Eq)
MINIMUM_ON_RIGHT = (ast.Gt, ast.GtE, ast.Eq)
MAX_PARENT_DEPTH = 8


@dataclass(frozen=True)
class Selection:
    """A name bound to a filtered collection and the names it was filtered from."""

    name: str
    line: int
    parents: tuple[str, ...]


@dataclass(frozen=True)
class SelectionPass:
    """One decision that passes when an unchecked selection is empty."""

    node: ast.AST
    unguarded: tuple[Selection, ...]
    shape: str

    def message(self) -> str:
        names = ", ".join(f"`{item.name}`(줄 {item.line})" for item in self.unguarded)
        return (
            f"필터 선택 {names}의 합계·any·all로 분기하고 {self.shape}에서 pass인데 "
            "그 선택의 0건 처리(`not x`·`len(x) == 0`·raise)가 같은 함수에 없음: "
            "판정 대상 0개면 pass"
        )


# --- small AST helpers --------------------------------------------------------


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _is_call(node: ast.AST | None, names: frozenset[str]) -> bool:
    return isinstance(node, ast.Call) and _dotted(node.func) in names


def _first_argument_name(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Name):
        return call.args[0].id
    return None


def _scope_nodes(statements: list[ast.stmt]) -> Iterator[ast.AST]:
    """Every node of ``statements`` without entering nested functions or classes."""
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


def _scope_blocks(statements: list[ast.stmt]) -> Iterator[list[ast.stmt]]:
    """Every statement list (bodies, else blocks, handlers) of the scope."""
    yield statements
    for node in _scope_nodes(statements):
        # ExceptHandler nodes are visited too, so their bodies come from "body".
        for attribute in ("body", "orelse", "finalbody"):
            block = getattr(node, attribute, None)
            if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                yield block


def _names_in(node: ast.AST) -> list[str]:
    return [inner.id for inner in ast.walk(node) if isinstance(inner, ast.Name)]


def _comprehension_iter_name_ids(node: ast.AST) -> set[int]:
    """Ids of the names that the comprehensions inside ``node`` iterate over."""
    return {
        id(name)
        for inner in ast.walk(node)
        if isinstance(inner, ast.comprehension)
        for name in ast.walk(inner.iter)
        if isinstance(name, ast.Name)
    }


def _added_collection(node: ast.AST, methods: frozenset[str]) -> str | None:
    """``rows`` for a call ``rows.append(...)`` (or another of ``methods``)."""
    is_method_call = (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in methods
        and isinstance(node.func.value, ast.Name)
    )
    return node.func.value.id if is_method_call else None


def _counter_name(node: ast.AST) -> str | None:
    """``n`` for ``n += <int constant>``."""
    is_counter = (
        isinstance(node, ast.AugAssign)
        and isinstance(node.op, ast.Add)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, int)
        and isinstance(node.target, ast.Name)
    )
    return node.target.id if is_counter else None


def _accumulated_names(statements: list[ast.stmt]) -> set[str]:
    """Names a loop body accumulates into.

    ``total += x``, ``worst = max(worst, x)``, ``found = True``, ``rows.append(x)``.
    """
    names: set[str] = set()
    for node in _scope_nodes(statements):
        name = _single_target(node)
        value = getattr(node, "value", None)
        if isinstance(node, ast.AugAssign) and name:
            names.add(name)
        elif name and value is not None:
            is_flag = isinstance(value, ast.Constant) and isinstance(value.value, bool)
            if is_flag or name in _names_in(value):
                names.add(name)
        elif added := _added_collection(node, ACCUMULATING_METHODS):
            names.add(added)
    return names


def _single_target(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        target = node.target
    else:
        return None
    return target.id if isinstance(target, ast.Name) else None


# --- pass-like values ---------------------------------------------------------


def _is_pass_constant(node: ast.AST | None) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(PASS_TEXT.match(node.value.strip()))
    if isinstance(node, ast.Name):
        return bool(PASS_CONSTANT_NAME.search(node.id))
    if isinstance(node, ast.Attribute):
        return bool(PASS_CONSTANT_NAME.search(node.attr))
    return False


def _is_pass_value(node: ast.AST | None) -> bool:
    """``"pass"``, ``Verdict.PASS``, or a dict whose status-like key holds one."""
    if _is_pass_constant(node):
        return True
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=False):
            is_status_key = isinstance(key, ast.Constant) and key.value in PASS_KEYS
            is_true = isinstance(value, ast.Constant) and value.value is True
            if is_status_key and (_is_pass_constant(value) or is_true):
                return True
    return False


def _statement_passes(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Return):
        return _is_pass_value(statement.value)
    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        if _is_pass_value(statement.value):
            return True
        is_true = (
            isinstance(statement.value, ast.Constant) and statement.value.value is True
        )
        name = _single_target(statement)
        return is_true and bool(name and PASS_TARGET_NAME.match(name))
    return False


def _block_passes(block: list[ast.stmt]) -> bool:
    return any(_statement_passes(statement) for statement in block)


def _block_stops(block: list[ast.stmt]) -> bool:
    return bool(block) and isinstance(block[-1], (ast.Return, ast.Raise))


def _pass_targets(block: list[ast.stmt]) -> set[str]:
    return {
        name
        for statement in block
        if _statement_passes(statement) and (name := _single_target(statement))
    }


def _is_pass_assignment(node: ast.AST) -> bool:
    """``ok = ...``, ``passed: bool = ...``, ``result["pass"] = ...``."""
    if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
        return False  # `x: int` declares without a value
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    for target in targets:
        if isinstance(target, ast.Name) and PASS_TARGET_NAME.match(target.id):
            return True
        is_key = isinstance(target, ast.Subscript) and isinstance(
            target.slice, ast.Constant
        )
        if is_key and target.slice.value in PASS_KEYS:
            return True
    return False


def _is_verdict_value(value: ast.AST | None) -> bool:
    """A value that can be a verdict: not a container, not a conditional expression.

    A conditional expression is reported once, as such; ``ok = [r for r in x ...]``
    names a list, not a verdict.
    """
    return value is not None and not isinstance(value, (*NON_VERDICT_VALUES, ast.IfExp))


@dataclass
class _IfChain:
    """``if``/``elif``/``else`` as (test, body) links plus the final ``else``."""

    links: list[tuple[ast.expr, list[ast.stmt]]] = field(default_factory=list)
    final_else: list[ast.stmt] = field(default_factory=list)

    @classmethod
    def from_if(cls, node: ast.If) -> _IfChain:
        chain = cls()
        current = node
        while True:
            chain.links.append((current.test, current.body))
            orelse = current.orelse
            if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                current = orelse[0]
                continue
            chain.final_else = orelse
            return chain

    def assigned(self) -> set[str]:
        blocks = [body for _, body in self.links] + [self.final_else]
        return {
            name for block in blocks for item in block if (name := _single_target(item))
        }


# --- the per-scope analysis ---------------------------------------------------


class ScopeAnalysis:
    """Selections, names derived from them, zero checks and decisions of one scope."""

    def __init__(self, statements: list[ast.stmt]) -> None:
        self.statements = statements
        self.nodes = list(_scope_nodes(statements))
        self.selections: dict[str, Selection] = {}
        self.derived: dict[str, set[str]] = {}  # name -> selections it aggregates
        self.count_names: dict[str, str] = {}  # n -> x for n = len(x)
        # n -> selections for `n += 1` inside a loop over them
        self.loop_counters: dict[str, set[str]] = {}
        self.guarded: set[str] = set()

    # selections ---------------------------------------------------------------
    def _filtered_selection(self, name: str, value: ast.AST) -> Selection | None:
        """A filtered comprehension or ``filter``; also a plain mapping of a selection.

        ``messages = [f"{r}" for r in failed]`` carries ``failed``'s emptiness, so it
        is a selection whose only parent is ``failed``.
        """
        while _is_call(value, WRAPPER_CALLS) and value.args:  # list(filter(...))
            value = value.args[0]
        if _is_call(value, FILTER_CALL) and len(value.args) == 2:
            return Selection(name, value.lineno, tuple(_names_in(value.args[1])))
        if not isinstance(value, COMPREHENSIONS):
            return None
        parents = tuple(
            parent
            for generator in value.generators
            for parent in _names_in(generator.iter)
        )
        is_filtered = any(generator.ifs for generator in value.generators)
        maps_a_selection = any(parent in self.selections for parent in parents)
        if is_filtered or maps_a_selection:
            return Selection(name, value.lineno, parents)
        return None

    def _empty_initialised(self) -> set[str]:
        names = set()
        for node in self.nodes:
            name = _single_target(node)
            value = getattr(node, "value", None)
            is_empty_literal = isinstance(value, (ast.List, ast.Set)) and not value.elts
            is_empty_call = _is_call(value, EMPTY_COLLECTION_CALLS) and not value.args
            if name and (is_empty_literal or is_empty_call):
                names.add(name)
        return names

    def _appended_selections(self) -> list[Selection]:
        """``x = []`` then ``x.append(...)`` under an ``if`` inside a ``for`` loop."""
        candidates = self._empty_initialised()
        found = []
        for loop in self.nodes:
            if not isinstance(loop, (ast.For, ast.AsyncFor)):
                continue
            parents = tuple(_names_in(loop.iter))
            branches = [
                node for node in _scope_nodes(loop.body) if isinstance(node, ast.If)
            ]
            for branch in branches:
                for node in _scope_nodes(branch.body + branch.orelse):
                    name = _added_collection(node, COLLECTION_ADD_METHODS)
                    if name in candidates:
                        found.append(Selection(name, loop.lineno, parents))
        return found

    def find_selections(self) -> None:
        for selection in self._appended_selections():
            self.selections.setdefault(selection.name, selection)
        # Two passes: a mapping of a selection is found once its source is known.
        for _ in range(2):
            for node in self.nodes:
                name = _single_target(node)
                value = getattr(node, "value", None)
                if not name or value is None or isinstance(node, ast.AugAssign):
                    continue
                selection = self._filtered_selection(name, value)
                if selection is not None:
                    self.selections.setdefault(name, selection)

    # aggregates and derived names ---------------------------------------------
    def aggregated(self, expression: ast.AST) -> set[str]:
        """Selections ``expression`` aggregates, itself or through derived names."""
        population_ids: set[int] = set()
        for node in ast.walk(expression):
            if not _is_call(node, ITERATING_CALLS):
                continue
            for argument in node.args:
                if isinstance(argument, ast.Name):
                    # any(failed) is the failure-set truth test, all(rows) is not.
                    if _is_call(node, POPULATION_CALLS):
                        population_ids.add(id(argument))
                    continue
                population_ids.update(_comprehension_iter_name_ids(argument))
        found: set[str] = set()
        for node in ast.walk(expression):
            if not isinstance(node, ast.Name):
                continue
            if node.id in self.selections and id(node) in population_ids:
                found.add(node.id)
            elif node.id in self.derived:
                found |= self.derived[node.id]
        return found

    def _derive_from_assignments(self) -> None:
        for node in self.nodes:
            name = _single_target(node)
            value = getattr(node, "value", None)
            if not name or value is None or name in self.selections:
                continue
            if _is_call(value, LEN_CALL) and (counted := _first_argument_name(value)):
                self.count_names[name] = counted
            found = self.aggregated(value)
            if found:
                self.derived.setdefault(name, set()).update(found)

    def _derive_from_loops(self) -> None:
        for loop in self.nodes:
            if not isinstance(loop, (ast.For, ast.AsyncFor)):
                continue
            iterated = {
                name for name in _names_in(loop.iter) if name in self.selections
            }
            if not iterated:
                continue
            for name in _accumulated_names(loop.body) - set(self.selections):
                self.derived.setdefault(name, set()).update(iterated)
            for node in _scope_nodes(loop.body):
                counter = _counter_name(node)
                if counter:
                    self.loop_counters.setdefault(counter, set()).update(iterated)

    def find_derived(self) -> None:
        # Two passes reach names derived from names derived from a selection.
        for _ in range(2):
            self._derive_from_assignments()
            self._derive_from_loops()

    # zero checks --------------------------------------------------------------
    def _pass_yielding_roots(self) -> list[ast.AST]:
        """Tests and values that themselves yield a pass."""
        roots: list[ast.AST] = []
        for node in self.nodes:
            branch_passes = (isinstance(node, ast.If) and _block_passes(node.body)) or (
                isinstance(node, ast.IfExp) and _is_pass_value(node.body)
            )
            if branch_passes:
                roots.append(node.test)
            elif _is_pass_assignment(node):
                roots.append(node.value)
        return roots

    def _compared_names(self, node: ast.Compare) -> set[str]:
        """Selections whose size a comparison checks.

        Any comparison with ``len(x)`` (or ``n = len(x)``) counts; a loop counter
        counts only as a minimum (``n < K``, ``n <= K``, ``n == K``, ``K > n``),
        since ``failures > 0`` tests a failure count, not the population size.
        """
        names = set()
        operands = [node.left, *node.comparators]
        for operand in operands:
            if _is_call(operand, LEN_CALL) and (
                counted := _first_argument_name(operand)
            ):
                names.add(counted)
            elif isinstance(operand, ast.Name) and operand.id in self.count_names:
                names.add(self.count_names[operand.id])
        for left, operator, right in zip(
            operands, node.ops, operands[1:], strict=False
        ):
            if isinstance(left, ast.Name) and isinstance(operator, MINIMUM_ON_LEFT):
                names |= self.loop_counters.get(left.id, set())
            if isinstance(right, ast.Name) and isinstance(operator, MINIMUM_ON_RIGHT):
                names |= self.loop_counters.get(right.id, set())
        return names

    def _conjunct_guards(self, root: ast.AST) -> set[str]:
        """Names a pass needs non-empty: ``judged and ...``, ``len(x) > 0 and ...``."""
        names: set[str] = set()
        for node in ast.walk(root):
            if not (isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And)):
                continue
            for value in node.values:
                if isinstance(value, ast.Name):
                    names.add(self.count_names.get(value.id, value.id))
                elif isinstance(value, ast.Compare):
                    names |= self._compared_names(value)
                elif _is_call(value, BOOL_CALL) and (
                    checked := _first_argument_name(value)
                ):
                    names.add(checked)
        return names

    @staticmethod
    def _negated_name(node: ast.AST) -> str | None:
        """``x`` for ``not x``, ``not len(x)`` and ``bool(x)``."""
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            operand = node.operand
            if _is_call(operand, LEN_CALL) and isinstance(operand, ast.Call):
                return _first_argument_name(operand)
            return operand.id if isinstance(operand, ast.Name) else None
        if _is_call(node, BOOL_CALL) and isinstance(node, ast.Call):
            return _first_argument_name(node)
        return None

    def find_zero_checks(self) -> None:
        roots = self._pass_yielding_roots()
        excluded = {id(inner) for root in roots for inner in ast.walk(root)}
        for root in roots:
            self.guarded |= self._conjunct_guards(root)
        for node in self.nodes:
            if id(node) in excluded:
                continue
            if isinstance(node, ast.Compare):
                self.guarded |= self._compared_names(node)
            elif name := self._negated_name(node):
                self.guarded.add(name)

    def is_covered(self, name: str, depth: int = 0) -> bool:
        """Zero-checked itself, or filtered from a zero-checked selection."""
        if name in self.guarded:
            return True
        if name not in self.selections or depth > MAX_PARENT_DEPTH:
            return False
        return any(
            self.is_covered(parent, depth + 1)
            for parent in self.selections[name].parents
            if parent in self.selections and parent != name
        )

    def unguarded(self, names: set[str]) -> tuple[Selection, ...]:
        return tuple(
            self.selections[name] for name in sorted(names) if not self.is_covered(name)
        )

    # decisions ----------------------------------------------------------------
    @staticmethod
    def _chain_shape(
        chain: _IfChain, block: list[ast.stmt], position: int
    ) -> str | None:
        """Where the chain passes, or ``None`` when it never yields a pass."""
        if any(_block_passes(body) for _, body in chain.links):
            return "분기"
        if _block_passes(chain.final_else):
            return "else"
        defaults = {
            name for earlier in block[:position] for name in _pass_targets([earlier])
        }
        if defaults & chain.assigned():
            return "앞선 기본값"
        stops = any(_block_stops(body) for _, body in chain.links)
        later_pass = any(
            isinstance(item, ast.Return) and _is_pass_value(item.value)
            for item in block[position + 1 :]
        )
        if stops and not chain.final_else and later_pass:
            return "뒤따르는 return"
        return None

    def _chain_decisions(self) -> list[SelectionPass]:
        elif_ids = {
            id(node.orelse[0])
            for node in self.nodes
            if isinstance(node, ast.If)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
        }
        decisions = []
        for block in _scope_blocks(self.statements):
            for position, statement in enumerate(block):
                if not isinstance(statement, ast.If) or id(statement) in elif_ids:
                    continue
                chain = _IfChain.from_if(statement)
                aggregated = set().union(
                    *(self.aggregated(test) for test, _ in chain.links)
                )
                unguarded = self.unguarded(aggregated)
                shape = self._chain_shape(chain, block, position) if unguarded else None
                if shape:
                    decisions.append(SelectionPass(statement, unguarded, shape))
        return decisions

    def _value_decision(
        self, node: ast.AST, value: ast.AST, shape: str
    ) -> list[SelectionPass]:
        unguarded = self.unguarded(self.aggregated(value))
        return [SelectionPass(node, unguarded, shape)] if unguarded else []

    def _expression_decisions(self) -> list[SelectionPass]:
        decisions = []
        reported_names: set[str] = set()
        for node in self.nodes:
            if isinstance(node, ast.IfExp):
                if _is_pass_value(node.body) or _is_pass_value(node.orelse):
                    decisions += self._value_decision(node, node.test, "조건식 분기")
            elif _is_pass_assignment(node) and _is_verdict_value(node.value):
                found = self._value_decision(node, node.value, "판정값")
                decisions += found
                if found and (name := _single_target(node)):
                    reported_names.add(name)
        for node in self.nodes:
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=False):
                is_pass_key = (
                    isinstance(key, ast.Constant) and key.value in PASS_VALUE_KEYS
                )
                # {"ok": ok} repeats a verdict already reported at its assignment.
                is_repeat = isinstance(value, ast.Name) and value.id in reported_names
                if is_pass_key and _is_verdict_value(value) and not is_repeat:
                    decisions += self._value_decision(value, value, "판정값")
        return decisions

    def decisions(self) -> list[SelectionPass]:
        self.find_selections()
        if not self.selections:
            return []
        self.find_derived()
        self.find_zero_checks()
        return self._chain_decisions() + self._expression_decisions()


def find_selection_passes(statements: list[ast.stmt]) -> list[SelectionPass]:
    """Decisions in one scope (a function body or module) that pass on empty input."""
    return ScopeAnalysis(statements).decisions()
