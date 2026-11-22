"""``missing_key_default_pass`` for gate_scan: a lookup default makes a check pass
when the key is missing.

The shape (2026-11-20, J-P3 baseline compare in z4369-jp3)::

    if sum(check.get("retract_tracker_dominated_reads") or [0]) or ...:
        failures.append("P4-9 ...")          # skipped when the key is absent
    failures += [... for key in JUDGED_KEYS if sum(check.get(key) or [0])]

A record that lacks the key reads exactly like a record whose count is zero, so
the failure is never recorded and the judgement passes.

Each scope (a function body or the module) is evaluated once under the scenario
"every looked-up key is missing":

* A *default source* is ``x.get(k, D)`` or ``x.get(k) or D`` with a literal ``D``
  (a constant or a container of constants). A plain ``x.get(k)`` evaluates to
  ``None`` too, but triggers a finding only with ``include_bare_get``.
* Expressions are evaluated abstractly (:class:`Value`): truthiness, the exact
  constant when known, and for containers whether they are empty and how their
  elements test. ``sum``/``any``/``all``/``len``/``max``/``min``/``bool``/``int``,
  ``and``/``or``/``not``, comparisons, ``+`` and comprehensions are followed.
  Assignments, ``+=`` and ``d[k] += ...`` carry values to names in source order;
  a name assigned twice keeps only what both assignments agree on.
* A *decision* is an ``if``/``elif`` chain, a conditional expression with a pass
  branch, a pass value (``"pass": ...``, ``ok = ...``), a boolean ``return``, a
  failure list filled by a comprehension (``failures += [...]``), or a ``for``
  loop over a default whose body records a failure.
* **warning** when, under the scenario, the decision skips a failure action
  (``failures.append``, ``raise``, a fail status), takes a pass branch, yields a
  true pass value, or leaves a failure list empty. A decision that leads to its
  failure action (a not-judgeable ``raise`` on zero rows) is the safe direction
  and is not reported. **info** when a decision reads a default but its direction
  cannot be evaluated. Findings that share their default sources with an earlier
  one are dropped (warnings first).

Heuristic only: calls to other functions, attributes and ``getattr`` defaults are
not followed, and loops are not iterated (each assignment is evaluated once).
"""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from _selection_flow import (
    PASS_TARGET_NAME,
    PASS_TEXT,
    PASS_VALUE_KEYS,
    _block_passes,
    _dotted,
    _IfChain,
    _is_pass_assignment,
    _is_pass_value,
    _is_verdict_value,
    _scope_nodes,
)

# A list, counter or flag whose name says it collects failures.
FAIL_LABEL = re.compile(
    r"(fail|problem|error|issue|violation|stop|blocker|blocked|mismatch|reject"
    r"|missing|bad)",
    re.IGNORECASE,
)
# Environment variables with a default are configuration, not record keys.
ENVIRONMENT_RECEIVERS = frozenset({"os.environ", "environ"})
STATUS_LABELS = frozenset({"status", "verdict", "outcome"})
RECORDING_METHODS = frozenset({"append", "extend", "add", "insert", "update"})
FILLING_METHODS = frozenset({"extend", "update"})
EXIT_CALLS = frozenset({"sys.exit", "exit", "os._exit"})
EMPTY_CALLS = frozenset({"list", "dict", "set", "tuple", "frozenset"})
PASSTHROUGH_CALLS = frozenset({"list", "tuple", "set", "sorted", "frozenset"})
NUMERIC_CALLS: dict[str, Callable[[float], object]] = {
    "int": int,
    "float": float,
    "abs": abs,
    "round": round,
}
BOOLEAN_RETURN_CALLS = frozenset({"all", "any", "bool"})
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
BINDING_TYPES = (
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.For,
    ast.AsyncFor,
    ast.NamedExpr,
)
COMPARISONS: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}
ARITHMETIC: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}
UPPER_CASE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
MAX_SOURCE_TEXT_CHARS = 70


@dataclass(frozen=True)
class Origin:
    """A default source: its line, its code and whether the default is explicit."""

    line: int
    text: str
    is_explicit: bool


@dataclass(frozen=True)
class Value:
    """What an expression evaluates to when every looked-up key is missing.

    ``truth`` is the truthiness (``None`` = unknown). ``constant`` is the exact
    value when ``is_known``. Containers also carry ``empty`` and ``elements`` (the
    truthiness every element shares; ``None`` = unknown or mixed).
    """

    truth: bool | None = None
    constant: object = None
    is_known: bool = False
    is_container: bool = False
    empty: bool | None = None
    elements: bool | None = None
    origins: frozenset[Origin] = frozenset()

    def with_origins(self, origins: frozenset[Origin]) -> Value:
        return replace(self, origins=self.origins | origins)

    def without_origins(self) -> Value:
        return replace(self, origins=frozenset())


UNKNOWN = Value()


def _scalar(constant: object, origins: frozenset[Origin] = frozenset()) -> Value:
    return Value(
        truth=bool(constant), constant=constant, is_known=True, origins=origins
    )


def _truth(truth: bool | None, origins: frozenset[Origin]) -> Value:
    return Value(truth=truth, origins=origins)


def _container(
    empty: bool | None, elements: bool | None, origins: frozenset[Origin]
) -> Value:
    truth = None if empty is None else not empty
    return Value(
        truth=truth, is_container=True, empty=empty, elements=elements, origins=origins
    )


def _shared_truth(values: list[Value]) -> bool | None:
    truths = {value.truth for value in values}
    return truths.pop() if len(truths) == 1 else None


def _origins_of(values: list[Value]) -> frozenset[Origin]:
    return frozenset().union(*(value.origins for value in values))


def _join(old: Value, new: Value) -> Value:
    """The value of a name assigned twice: what both assignments agree on."""
    origins = old.origins | new.origins
    if old.without_origins() == new.without_origins():
        return old.with_origins(origins)
    if old.truth is not None and old.truth == new.truth:
        return _truth(old.truth, origins)
    return _truth(None, origins)


def _both_empty(first: bool | None, second: bool | None) -> bool | None:
    if first is False or second is False:
        return False
    if first is True and second is True:
        return True
    return None


def _arithmetic(left: Value, operation: ast.operator, right: Value) -> Value:
    """``left <op> right`` for known numbers, or list concatenation."""
    origins = left.origins | right.origins
    function = ARITHMETIC.get(type(operation))
    are_numbers = all(
        value.is_known and isinstance(value.constant, (int, float))
        for value in (left, right)
    )
    if function is not None and are_numbers:
        return _scalar(function(left.constant, right.constant), origins)
    is_concatenation = isinstance(operation, ast.Add) and (
        left.is_container and right.is_container
    )
    if is_concatenation:
        elements = left.elements if left.elements == right.elements else None
        return _container(_both_empty(left.empty, right.empty), elements, origins)
    return _truth(None, origins)


def _is_all_false(container: Value) -> bool:
    """Empty, or every element false: ``sum`` is 0 and ``any`` is False."""
    return container.empty is True or container.elements is False


def _is_all_true(container: Value) -> bool:
    return container.empty is False and container.elements is True


def _fold_len(container: Value) -> Value:
    if container.empty is True:
        return _scalar(0, container.origins)
    return _truth(True if container.empty is False else None, container.origins)


def _fold_sum(container: Value) -> Value:
    if _is_all_false(container):
        return _scalar(0, container.origins)
    return _truth(True if _is_all_true(container) else None, container.origins)


def _fold_any(container: Value) -> Value:
    if _is_all_false(container):
        return _scalar(False, container.origins)
    if _is_all_true(container):
        return _scalar(True, container.origins)
    return _truth(None, container.origins)


def _fold_all(container: Value) -> Value:
    if container.empty is True or container.elements is True:
        return _scalar(True, container.origins)  # all([]) is True
    if container.empty is False and container.elements is False:
        return _scalar(False, container.origins)
    return _truth(None, container.origins)


def _fold_extreme(container: Value) -> Value:
    """``max``/``min`` of a non-empty container share the elements' truthiness."""
    truth = container.elements if container.empty is False else None
    return _truth(truth, container.origins)


FOLDS: dict[str, Callable[[Value], Value]] = {
    "len": _fold_len,
    "sum": _fold_sum,
    "any": _fold_any,
    "all": _fold_all,
    "max": _fold_extreme,
    "min": _fold_extreme,
}


# --- default sources ----------------------------------------------------------


def _is_get_call(node: ast.AST, argument_counts: tuple[int, ...]) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and _dotted(node.func.value) not in ENVIRONMENT_RECEIVERS
        and len(node.args) in argument_counts
        and not node.keywords
    )


def _literal_value(node: ast.AST) -> Value | None:
    """The value of a literal default: a constant or a container of constants."""
    if isinstance(node, ast.Constant):
        return _scalar(node.value)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        constants = [item for item in node.elts if isinstance(item, ast.Constant)]
        if len(constants) != len(node.elts):
            return None
        elements = [_scalar(item.value) for item in constants]
        return _container(not elements, _shared_truth(elements), frozenset())
    if isinstance(node, ast.Dict):
        if not all(isinstance(item, ast.Constant) for item in node.values):
            return None
        return _container(not node.values, None, frozenset())
    is_empty_call = (
        isinstance(node, ast.Call)
        and _dotted(node.func) in EMPTY_CALLS
        and not node.args
        and not node.keywords
    )
    return _container(True, None, frozenset()) if is_empty_call else None


def _source_text(node: ast.AST) -> str:
    text = ast.unparse(node)
    if len(text) > MAX_SOURCE_TEXT_CHARS:
        return text[: MAX_SOURCE_TEXT_CHARS - 1] + "…"
    return text


def _origin(node: ast.expr, is_explicit: bool) -> frozenset[Origin]:
    return frozenset({Origin(node.lineno, _source_text(node), is_explicit)})


def _yields_none_or_literal(node: ast.expr) -> bool:
    """``x.get(k)`` or ``x.get(k, <literal>)``: known when the key is missing."""
    if _is_get_call(node, (1,)):
        return True
    if not (isinstance(node, ast.Call) and _is_get_call(node, (2,))):
        return False
    return _literal_value(node.args[1]) is not None


def _default_source(node: ast.expr) -> Value | None:
    """``x.get(k, D)``, ``x.get(k) or D`` (explicit) or ``x.get(k)`` (``None``)."""
    literal = None
    if isinstance(node, ast.Call) and _is_get_call(node, (2,)):
        literal = _literal_value(node.args[1])
    elif (
        isinstance(node, ast.BoolOp)
        and isinstance(node.op, ast.Or)
        and all(_yields_none_or_literal(item) for item in node.values[:-1])
    ):
        literal = _literal_value(node.values[-1])
    if literal is not None:
        return literal.with_origins(_origin(node, is_explicit=True))
    if _is_get_call(node, (1,)):
        return _scalar(None, _origin(node, is_explicit=False))
    return None


# --- the abstract evaluator ---------------------------------------------------


def _element_slot(node: ast.Subscript) -> tuple[str, str | None] | None:
    """``("d", "key")`` for ``d["key"]``, ``("d", None)`` for ``d[name]``."""
    if not isinstance(node.value, ast.Name):
        return None
    key = node.slice
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return (node.value.id, key.value)
    return (node.value.id, None)


class _Evaluator:
    """Evaluates expressions of one scope with every looked-up key missing."""

    def __init__(self) -> None:
        self.names: dict[str, Value] = {}
        # (d, "key") -> the value of d["key"]; (d, None) -> d[<any other key>].
        self.elements: dict[tuple[str, str | None], Value] = {}
        # Each handler takes the node type it is registered for.
        self._handlers: dict[type[ast.AST], Callable[[Any], Value]] = {
            ast.Constant: self._constant,
            ast.Name: self._name,
            ast.Subscript: self._subscript,
            ast.List: self._literal_container,
            ast.Tuple: self._literal_container,
            ast.Set: self._literal_container,
            ast.BoolOp: self._bool_op,
            ast.UnaryOp: self._negation,
            ast.Compare: self._compare,
            ast.BinOp: self._binary,
            ast.Call: self._call,
            **dict.fromkeys(COMPREHENSIONS, self._comprehension),
        }

    def evaluate(self, node: ast.expr) -> Value:
        source = _default_source(node)
        if source is not None:
            return source
        handler = self._handlers.get(type(node))
        return handler(node) if handler is not None else UNKNOWN

    # expressions -------------------------------------------------------------
    @staticmethod
    def _constant(node: ast.Constant) -> Value:
        return _scalar(node.value)

    def _name(self, node: ast.Name) -> Value:
        if node.id in self.names:
            return self.names[node.id]
        if UPPER_CASE_NAME.match(node.id):
            # A module constant such as JUDGED_KEYS: assumed to be a non-empty set.
            return _container(False, None, frozenset())
        return UNKNOWN

    def _subscript(self, node: ast.Subscript) -> Value:
        slot = _element_slot(node)
        if slot is None:
            return UNKNOWN
        if slot in self.elements:
            return self.elements[slot]
        return self.elements.get((slot[0], None), UNKNOWN)

    def _literal_container(self, node: ast.List | ast.Tuple | ast.Set) -> Value:
        values = [self.evaluate(item) for item in node.elts]
        if any(isinstance(item, ast.Starred) for item in node.elts):
            return _truth(None, _origins_of(values))
        elements = _shared_truth(values) if values else None
        return _container(not values, elements, _origins_of(values))

    def _bool_op(self, node: ast.BoolOp) -> Value:
        values = [self.evaluate(item) for item in node.values]
        origins = _origins_of(values)
        # `or` stops at the first true value, `and` at the first false one.
        stop_truth = isinstance(node.op, ast.Or)
        if all(value.truth is (not stop_truth) for value in values[:-1]):
            return values[-1].with_origins(origins)  # every operand was evaluated
        # Only the operands that decide the result carry their sources.
        deciding = [value for value in values if value.truth is stop_truth]
        if deciding:
            return _truth(stop_truth, _origins_of(deciding))
        return _truth(None, origins)

    def _negation(self, node: ast.UnaryOp) -> Value:
        operand = self.evaluate(node.operand)
        if not isinstance(node.op, ast.Not) or operand.truth is None:
            return _truth(None, operand.origins)
        return _scalar(not operand.truth, operand.origins)

    def _compare(self, node: ast.Compare) -> Value:
        values = [self.evaluate(item) for item in (node.left, *node.comparators)]
        origins = _origins_of(values)
        compare = COMPARISONS.get(type(node.ops[0]))
        left, right = values[0], values[-1]
        is_single_known = len(node.ops) == 1 and left.is_known and right.is_known
        if compare is None or not is_single_known:
            return _truth(None, origins)
        try:
            return _scalar(bool(compare(left.constant, right.constant)), origins)
        except TypeError:  # None < 0
            return _truth(None, origins)

    def _binary(self, node: ast.BinOp) -> Value:
        return _arithmetic(self.evaluate(node.left), node.op, self.evaluate(node.right))

    def _call(self, node: ast.Call) -> Value:
        name = _dotted(node.func)
        if len(node.args) != 1 or node.keywords:
            return UNKNOWN
        argument = self.evaluate(node.args[0])
        if name in FOLDS:
            if argument.is_container:
                return FOLDS[name](argument)
            return _truth(None, argument.origins)
        if name in PASSTHROUGH_CALLS and argument.is_container:
            return argument
        if name == "bool":
            if argument.truth is None:
                return _truth(None, argument.origins)
            return _scalar(argument.truth, argument.origins)
        if name in NUMERIC_CALLS and not argument.is_container:
            return self._numeric(NUMERIC_CALLS[name], argument)
        return UNKNOWN

    @staticmethod
    def _numeric(function: Callable[[float], object], argument: Value) -> Value:
        if argument.is_known and isinstance(argument.constant, (int, float)):
            return _scalar(function(argument.constant), argument.origins)
        return _truth(argument.truth, argument.origins)

    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp
    ) -> Value:
        iterables = [self.evaluate(generator.iter) for generator in node.generators]
        filters = [
            self.evaluate(test)
            for generator in node.generators
            for test in generator.ifs
        ]
        emptying = [value for value in iterables if value.empty is True]
        emptying += [value for value in filters if value.truth is False]
        if emptying:
            return _container(True, None, _origins_of(emptying))
        item = node.value if isinstance(node, ast.DictComp) else node.elt
        element = self.evaluate(item)
        origins = _origins_of([*iterables, *filters, element])
        is_full = all(value.empty is False for value in iterables) and all(
            value.truth is True for value in filters
        )
        return _container(False if is_full else None, element.truth, origins)

    # statements --------------------------------------------------------------
    def bind_assignments(self, nodes: list[ast.AST]) -> None:
        """Evaluate every assignment of the scope once, in source order."""
        bindings = [node for node in nodes if isinstance(node, BINDING_TYPES)]
        bindings.sort(key=lambda node: (node.lineno, node.col_offset))
        for node in bindings:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._store(target, node.value)
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
                if node.value is not None:
                    self._store(node.target, node.value)
            elif isinstance(node, ast.AugAssign):
                self._augment(node.target, node.op, self.evaluate(node.value))
            else:
                self._forget(node.target)

    def _store(self, target: ast.expr, value_node: ast.expr) -> None:
        value = self.evaluate(value_node)
        if isinstance(target, ast.Name):
            old = self.names.get(target.id)
            self.names[target.id] = value if old is None else _join(old, value)
            self._store_mapping_values(target.id, value_node)
        elif isinstance(target, ast.Subscript) and (slot := _element_slot(target)):
            self._store_element(slot, value)
        else:
            self._forget(target)

    def _store_element(self, slot: tuple[str, str | None], value: Value) -> None:
        old = self.elements.get(slot)
        self.elements[slot] = value if old is None else _join(old, value)

    def _store_mapping_values(self, name: str, value_node: ast.expr) -> None:
        """``d = dict.fromkeys(keys, 0)``, ``{k: 0 for ...}``, ``{"a": x}``: d[k]."""
        if isinstance(value_node, ast.Call):
            is_fromkeys = _dotted(value_node.func) == "dict.fromkeys"
            if is_fromkeys and len(value_node.args) == 2:
                self.elements[(name, None)] = self.evaluate(value_node.args[1])
        elif isinstance(value_node, ast.DictComp):
            self.elements[(name, None)] = self.evaluate(value_node.value)
        elif isinstance(value_node, ast.Dict):
            for key, item in zip(value_node.keys, value_node.values, strict=False):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    self.elements[(name, key.value)] = self.evaluate(item)

    def _augment(self, target: ast.expr, operation: ast.operator, value: Value) -> None:
        if isinstance(target, ast.Name):
            old = self.names.get(target.id, UNKNOWN)
            self.names[target.id] = _arithmetic(old, operation, value)
        elif isinstance(target, ast.Subscript) and (slot := _element_slot(target)):
            old = self.elements.get(slot, self.elements.get((slot[0], None), UNKNOWN))
            self.elements[slot] = _arithmetic(old, operation, value)

    def _forget(self, target: ast.expr) -> None:
        for node in ast.walk(target):
            if isinstance(node, ast.Name):
                self.names[node.id] = UNKNOWN


# --- failure actions ----------------------------------------------------------


def _label(target: ast.AST) -> str:
    """``failures`` for ``failures``, ``self.failures`` or ``report["failures"]``."""
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Subscript):
        key = target.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            return key.value
        return _label(target.value)
    return ""


def _is_fail_label(label: str) -> bool:
    return bool(label) and bool(FAIL_LABEL.search(label))


def _is_fail_constant(node: ast.AST | None) -> bool:
    """``False`` or a status string that is not a pass (``"fail"``, ``"H-7"``)."""
    if not isinstance(node, ast.Constant):
        return False
    if node.value is False:
        return True
    return isinstance(node.value, str) and not PASS_TEXT.match(node.value.strip())


def _assigns_failure(node: ast.Assign | ast.AnnAssign) -> bool:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    for target in targets:
        label = _label(target)
        is_flag = isinstance(node.value, ast.Constant) and node.value.value is True
        if _is_fail_label(label) and is_flag:
            return True
        is_status = label in STATUS_LABELS or bool(PASS_TARGET_NAME.match(label))
        if is_status and _is_fail_constant(node.value):
            return True
    return False


def _is_fail_action(node: ast.AST) -> bool:
    """``raise``, ``sys.exit(1)``, ``failures.append(...)``, ``ok = False`` ..."""
    if isinstance(node, ast.Raise):
        return True
    if isinstance(node, ast.Call):
        if _dotted(node.func) in EXIT_CALLS:
            is_zero = bool(node.args) and _is_zero_constant(node.args[0])
            return not is_zero
        return (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in RECORDING_METHODS
            and _is_fail_label(_label(node.func.value))
        )
    if isinstance(node, ast.AugAssign):
        return _is_fail_label(_label(node.target))
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return _assigns_failure(node)
    if isinstance(node, ast.Return):
        return _is_fail_constant(node.value)
    return False


def _is_zero_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == 0


def _fail_line(block: list[ast.stmt]) -> int | None:
    """Line of the first failure action in ``block`` (nested statements included)."""
    lines = [
        getattr(node, "lineno", 0)
        for node in _scope_nodes(block)
        if _is_fail_action(node)
    ]
    return min(lines) if lines else None


def _is_boolean_expression(node: ast.AST | None) -> bool:
    if isinstance(node, (ast.Compare, ast.BoolOp)):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    return isinstance(node, ast.Call) and _dotted(node.func) in BOOLEAN_RETURN_CALLS


# --- the per-scope analysis ---------------------------------------------------


@dataclass(frozen=True)
class AbsencePass:
    """One decision that reads a default; a warning when the default makes it pass."""

    node: ast.AST  # an expression or statement: it has a line number
    is_warning: bool
    origins: frozenset[Origin]
    effect: str

    def message(self) -> str:
        ordered = sorted(self.origins, key=lambda origin: (origin.line, origin.text))
        sources = ", ".join(f"`{origin.text}`(줄 {origin.line})" for origin in ordered)
        if self.is_warning:
            return (
                f"키가 없으면 기본값 {sources} 때문에 {self.effect}: 키 누락이 통과로 "
                "읽힘 → 키 존재 확인(`k in x`)·`x[k]`·결측을 판정 불가로"
            )
        return f"판정 조건이 키 기본값 {sources}을 읽음({self.effect})"


class AbsenceAnalysis:
    """Decisions of one scope evaluated with every looked-up key missing."""

    def __init__(self, statements: list[ast.stmt], include_bare_get: bool) -> None:
        self.nodes = list(_scope_nodes(statements))
        self.include_bare_get = include_bare_get
        self.evaluator = _Evaluator()
        self.found: list[AbsencePass] = []
        # Sources whose missing key some decision already turns into a failure.
        self.caught: set[Origin] = set()

    def _sources(self, value: Value) -> frozenset[Origin]:
        return frozenset(
            origin
            for origin in value.origins
            if origin.is_explicit or self.include_bare_get
        )

    def _report(
        self, node: ast.AST, value: Value, is_warning: bool, effect: str
    ) -> None:
        sources = self._sources(value)
        if sources:
            self.found.append(AbsencePass(node, is_warning, sources, effect))

    # decisions ----------------------------------------------------------------
    def _check_chains(self) -> None:
        elif_ids = {
            id(node.orelse[0])
            for node in self.nodes
            if isinstance(node, ast.If)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
        }
        for node in self.nodes:
            if isinstance(node, ast.If) and id(node) not in elif_ids:
                self._check_chain(node, _IfChain.from_if(node))

    def _check_chain(self, node: ast.If, chain: _IfChain) -> None:
        """Follow the chain the way the scenario would run it."""
        tested: frozenset[Origin] = frozenset()
        for test, body in chain.links:
            value = self.evaluator.evaluate(test)
            tested |= value.origins
            fail_line = _fail_line(body)
            if value.truth is None:
                if fail_line or _block_passes(body):
                    self._report(test, value, False, "방향 미정")
                return
            if value.truth:
                if fail_line:
                    self.caught |= value.origins
                elif _block_passes(body):
                    self._report(
                        test, value, True, f"통과 가지(줄 {body[0].lineno})로 감"
                    )
                return
            if fail_line:
                self._report(test, value, True, f"실패 기록(줄 {fail_line})을 건너뜀")
                return
        if _fail_line(chain.final_else):
            self.caught |= tested
        elif _block_passes(chain.final_else):
            effect = f"else의 통과(줄 {chain.final_else[0].lineno})로 감"
            self._report(node, _truth(False, tested), True, effect)

    def _check_conditional_expressions(self) -> None:
        for node in self.nodes:
            if not isinstance(node, ast.IfExp):
                continue
            if not (_is_pass_value(node.body) or _is_pass_value(node.orelse)):
                continue
            value = self.evaluator.evaluate(node.test)
            if value.truth is None:
                self._report(node, value, False, "조건식 방향 미정")
                continue
            chosen = node.body if value.truth else node.orelse
            if _is_pass_value(chosen):
                self._report(node, value, True, "조건식이 통과 값으로 감")

    def _check_verdict(self, value_node: ast.expr) -> None:
        value = self.evaluator.evaluate(value_node)
        if value.truth is True:
            self._report(value_node, value, True, "판정값이 참(통과)")
        elif value.truth is None:
            self._report(value_node, value, False, "판정값 방향 미정")

    def _check_pass_values(self) -> None:
        for node in self.nodes:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value_node = node.value
                if value_node is None or not _is_pass_assignment(node):
                    continue
                if _is_verdict_value(value_node):
                    self._check_verdict(value_node)
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=False):
                    is_pass_key = (
                        isinstance(key, ast.Constant) and key.value in PASS_VALUE_KEYS
                    )
                    if is_pass_key and _is_verdict_value(value):
                        self._check_verdict(value)

    def _check_returns(self) -> None:
        for node in self.nodes:
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            if _is_boolean_expression(node.value):
                value = self.evaluator.evaluate(node.value)
                if value.truth is True:
                    self._report(node, value, True, "반환 판정값이 참(통과)")

    def _check_failure_lists(self) -> None:
        for node in self.nodes:
            for label, value_node in _failure_list_fillings(node):
                value = self.evaluator.evaluate(value_node)
                if value.is_container and value.empty is False:
                    self.caught |= value.origins
                elif value.is_container and value.empty is True:
                    effect = f"실패 목록 `{label}`에 아무것도 넣지 않음"
                    self._report(node, value, True, effect)

    def _check_loops(self) -> None:
        for node in self.nodes:
            if not isinstance(node, (ast.For, ast.AsyncFor)):
                continue
            value = self.evaluator.evaluate(node.iter)
            fail_line = _fail_line(node.body)
            if value.is_container and value.empty is True and fail_line:
                effect = f"빈 기본값을 도는 루프의 실패 기록(줄 {fail_line})을 건너뜀"
                self._report(node, value, True, effect)

    def _deduplicated(self) -> list[AbsencePass]:
        """Keep one finding per set of default sources, warnings first.

        Sources that another decision of the scope already turns into a failure
        (``if len(rows) != count: problems.append(...)``) are not reported again.
        """
        ordered = sorted(
            self.found,
            key=lambda item: (not item.is_warning, getattr(item.node, "lineno", 0)),
        )
        covered: set[Origin] = set(self.caught)
        kept = []
        for item in ordered:
            if item.origins <= covered:
                continue
            kept.append(item)
            covered |= item.origins
        return kept

    def run(self) -> list[AbsencePass]:
        self.evaluator.bind_assignments(self.nodes)
        self._check_chains()
        self._check_conditional_expressions()
        self._check_pass_values()
        self._check_returns()
        self._check_failure_lists()
        self._check_loops()
        return self._deduplicated()


def _failure_list_fillings(node: ast.AST) -> list[tuple[str, ast.expr]]:
    """``(label, value)`` of ``failures = x``, ``failures += x``, ``.extend(x)``."""
    if isinstance(node, ast.Assign):
        pairs = [(_label(target), node.value) for target in node.targets]
    elif isinstance(node, ast.AugAssign):
        pairs = [(_label(node.target), node.value)]
    elif (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr in FILLING_METHODS
        and len(node.value.args) == 1
    ):
        pairs = [(_label(node.value.func.value), node.value.args[0])]
    else:
        pairs = []
    return [(label, value) for label, value in pairs if _is_fail_label(label)]


def find_absence_passes(
    statements: list[ast.stmt], include_bare_get: bool = False
) -> list[AbsencePass]:
    """Decisions in one scope that pass, or may pass, because a key is missing."""
    return AbsenceAnalysis(statements, include_bare_get).run()
