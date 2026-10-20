"""V-check results and comparison helpers (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` 3.1 (``verify/checks``) and 3.4. A check
compares one value (scalar or array) with a reference under a tolerance and returns a
:class:`CheckResult`. Automatic pass / fail is a pre-check; the final physical judgement is
the dynamics-expert's.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike


def _plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


@dataclass(frozen=True)
class CheckResult:
    """One check. ``tol`` is described by ``tol_kind`` (``abs``, ``rel``, ``max`` ...)."""

    id: str
    item: str
    value: Any
    ref: Any
    tol: Any
    tol_kind: str
    unit: str
    passed: bool
    ref_key: str = ""
    deviation: Any = None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: _plain(v) for k, v in asdict(self).items()}


def check_abs(
    id_: str, item: str, value: ArrayLike, ref: ArrayLike, tol: float, unit: str, **kw: Any
) -> CheckResult:
    """``|value - ref| <= tol`` element-wise."""
    v = np.asarray(value, dtype=float)
    r = np.asarray(ref, dtype=float)
    dev = v - r
    passed = bool(np.all(np.isfinite(v)) and np.all(np.abs(dev) <= tol))
    return CheckResult(id_, item, v, r, tol, "abs", unit, passed, deviation=dev, **kw)


def check_rel(
    id_: str, item: str, value: ArrayLike, ref: ArrayLike, tol: float, unit: str, **kw: Any
) -> CheckResult:
    """``|value - ref| <= tol |ref|`` element-wise (``deviation`` = relative difference)."""
    v = np.asarray(value, dtype=float)
    r = np.asarray(ref, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        dev = np.where(r != 0.0, (v - r) / np.abs(r), v - r)
    passed = bool(np.all(np.isfinite(v)) and np.all(np.abs(v - r) <= tol * np.abs(r)))
    return CheckResult(id_, item, v, r, tol, "rel", unit, passed, deviation=dev, **kw)


def check_max(
    id_: str, item: str, value: ArrayLike, limit: float, unit: str, **kw: Any
) -> CheckResult:
    """``max(value) <= limit`` (``value`` non-negative measure, e.g. a span or a violation)."""
    v = np.asarray(value, dtype=float)
    passed = bool(np.all(np.isfinite(v)) and np.all(v <= limit))
    return CheckResult(id_, item, v, None, limit, "max", unit, passed, **kw)


def check_equal(
    id_: str, item: str, value: Any, ref: Any, unit: str = "", **kw: Any
) -> CheckResult:
    """Exact equality (flags, counts, settings)."""
    passed = bool(np.array_equal(np.asarray(value), np.asarray(ref)))
    return CheckResult(id_, item, value, ref, 0, "equal", unit, passed, **kw)


def all_passed(results: Iterable[CheckResult]) -> bool:
    return all(r.passed for r in results)


def summary_table(results: Sequence[CheckResult]) -> list[dict[str, Any]]:
    """JSON-ready list of the results."""
    return [r.as_dict() for r in results]
