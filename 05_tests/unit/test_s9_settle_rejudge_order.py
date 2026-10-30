"""``rebuild_row_verdict`` follows the ``s9_soil_slope.classify`` order (spec 398.1 SL-1).

A stroke guard warning gives the stroke limited class even with no failed row; the cross table
builds the same synthetic run as ``classify`` rows and as a ``records`` entry and compares the two
verdicts. Synthetic inputs only, no simulation."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_settle_rejudge as rj  # noqa: E402
import s9_soil_slope as ss  # noqa: E402

GUARD_WARNING = "WARN_LIFT_STROKE_LIMITED:FL"
STROKE_FAULT_WARNING = "FAULT_STROKE_END:RL"
OTHER_FAULT_WARNING = "FAULT_REGROUND:FL"
P3_JUDGED_ROWS = ("P3-1", "P3-2", "P3-3", "P3-4", "P3-5", "P3-8")
# rows whose failure separates the classify branches: required (P3-1, P3-3), relaxed (P3-5),
# outside both (P3-8)
VARIED_FAILED_ROWS = ("P3-1", "P3-3", "P3-5", "P3-8")


def _record(failed_rows: list[str], warnings: list[str], *, final_phase: str = "ready",
            soil_stop: dict | None = None) -> dict:
    return {"id": "H3|S1|A|top|nose_down@k0.75", "verdict": "settle_check_fail",
            "failed_rows": failed_rows, "warnings": warnings, "final_phase": final_phase,
            "soil_stop": soil_stop}


def test_guard_without_failed_rows_is_stroke_limited_pass() -> None:
    record = _record([], [GUARD_WARNING])
    assert rj.rebuild_row_verdict(record) == ss.VERDICT_STROKE_LIMITED_PASS


def test_no_guard_without_failed_rows_is_pass() -> None:
    assert rj.rebuild_row_verdict(_record([], [])) == ss.VERDICT_PASS


def test_guard_with_a_non_stroke_fault_is_stroke_limited_fail() -> None:
    record = _record(["fault_ready"], [GUARD_WARNING, OTHER_FAULT_WARNING],
                     final_phase="fault_reground")
    assert rj.rebuild_row_verdict(record) == ss.VERDICT_STROKE_LIMITED_FAIL


@pytest.mark.parametrize(("is_stop_pass", "expected"), [
    (True, ss.VERDICT_STROKE_LIMITED_STOP),
    (False, ss.VERDICT_FAIL),
])
def test_soil_stop_comes_first(is_stop_pass: bool, expected: str) -> None:
    record = _record(["fault_ready", "SL-1"], [GUARD_WARNING, "FAULT_LIFT_STROKE_LIMIT:soil:FL"],
                     final_phase="fault", soil_stop={"pass": is_stop_pass})
    assert rj.rebuild_row_verdict(record) == expected


def _classify_inputs(*, failed: set[str], has_guard: bool, has_stroke_fault: bool,
                     has_other_fault: bool, soil_stop: dict | None,
                     lifted_legs: list[str]) -> tuple[dict, dict]:
    has_fault = has_stroke_fault or has_other_fault
    p3 = {row: {"pass": row not in failed} for row in P3_JUDGED_ROWS}
    p3["fault_ready"] = {"pass": not has_fault, "has_fault": has_fault}
    stroke = {"pass": not has_stroke_fault and "SL-1" not in failed,
              "stroke_faults": ["FAULT_STROKE_END"] if has_stroke_fault else [],
              "guard_warning": has_guard, "lifted_legs": lifted_legs}
    if soil_stop is not None:
        stroke["soil_stop"] = soil_stop
    return p3, stroke


def _record_from(p3: dict, stroke: dict, *, has_stroke_fault: bool,
                 has_other_fault: bool, keeps_lifted_legs: bool = True) -> dict:
    """The ``records`` entry s9_slope_fix_candidates writes for the same run
    (``keeps_lifted_legs`` False: an older record without the SL-1 ``lifted_legs`` key)."""
    rows = {**p3, "SL-1": stroke}
    failed_rows = sorted(name for name, row in rows.items() if row.get("pass") is False)
    warnings = []
    if stroke["guard_warning"]:
        warnings.append(GUARD_WARNING)
    if has_stroke_fault:
        warnings.append(STROKE_FAULT_WARNING)
    if has_other_fault:
        warnings.append(OTHER_FAULT_WARNING)
    final_phase = "fault" if has_stroke_fault or has_other_fault else "ready"
    record = _record(failed_rows, warnings, final_phase=final_phase,
                     soil_stop=stroke.get("soil_stop"))
    if keeps_lifted_legs:
        record["lifted_legs"] = list(stroke["lifted_legs"])
    return record


def _failed_row_sets() -> list[frozenset[str]]:
    sets = []
    for size in range(len(VARIED_FAILED_ROWS) + 1):
        sets += [frozenset(rows) for rows in itertools.combinations(VARIED_FAILED_ROWS, size)]
    return sets


CROSS_TABLE = list(itertools.product(
    _failed_row_sets(),                       # failed P3 rows
    (False, True),                            # SL-1 over the stroke limit
    (False, True),                            # guard warning
    (False, True),                            # stroke FAULT
    (False, True),                            # other FAULT
    (None, {"pass": True}, {"pass": False}),  # soil-guard stop row
))


@pytest.mark.parametrize(("failed", "is_over_stroke", "has_guard", "has_stroke_fault",
                          "has_other_fault", "soil_stop"), CROSS_TABLE)
@pytest.mark.parametrize("lifted_legs", [[], ["FL"]])
def test_cross_table_matches_classify(failed, is_over_stroke, has_guard, has_stroke_fault,
                                      has_other_fault, soil_stop, lifted_legs) -> None:
    failed_rows = set(failed) | ({"SL-1"} if is_over_stroke else set())
    p3, stroke = _classify_inputs(failed=failed_rows, has_guard=has_guard,
                                  has_stroke_fault=has_stroke_fault,
                                  has_other_fault=has_other_fault, soil_stop=soil_stop,
                                  lifted_legs=lifted_legs)
    record = _record_from(p3, stroke, has_stroke_fault=has_stroke_fault,
                          has_other_fault=has_other_fault)
    assert rj.rebuild_row_verdict(record) == ss.classify(p3, stroke, None)


def test_lifted_leg_follows_classify() -> None:
    """A guarded run with a lifted leg and no failed row: stroke limited fail, as classify."""
    p3, stroke = _classify_inputs(failed=set(), has_guard=True, has_stroke_fault=False,
                                  has_other_fault=False, soil_stop=None, lifted_legs=["FL"])
    record = _record_from(p3, stroke, has_stroke_fault=False, has_other_fault=False)
    assert ss.classify(p3, stroke, None) == ss.VERDICT_STROKE_LIMITED_FAIL
    assert rj.rebuild_row_verdict(record) == ss.VERDICT_STROKE_LIMITED_FAIL


def test_older_record_without_lifted_legs_keeps_the_old_verdict() -> None:
    """A record written before the key existed skips the lift test (the previous behaviour)."""
    p3, stroke = _classify_inputs(failed=set(), has_guard=True, has_stroke_fault=False,
                                  has_other_fault=False, soil_stop=None, lifted_legs=["FL"])
    record = _record_from(p3, stroke, has_stroke_fault=False, has_other_fault=False,
                          keeps_lifted_legs=False)
    assert "lifted_legs" not in record
    assert rj.rebuild_row_verdict(record) == ss.VERDICT_STROKE_LIMITED_PASS
