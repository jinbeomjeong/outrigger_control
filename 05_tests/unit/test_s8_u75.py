"""U-S8-75 = (b) (``s6_control_spec.md`` rev. 68 357.3, 2026-10-27): judge exception in
``verify.s8_control``.

For a fast event on a front leg (FL / FR) at the top auger level with case F_s < 2 kN, the U57
"0 outside the window" part and the U-S8-74 F_min (b) "no pad lift after the window end" pass
when the adjacent-leg lift after the window sums to <= 0.1 s with a gap <= 0.5 mm; both rows
then carry the FLAG ``U-S8-75 (b) exception``. Outside that scope nothing changes.

The numbered tests follow the 357.3 list (① ... ④); the others are boundaries."""

from __future__ import annotations

import numpy as np
import pytest
from test_s8_c_s8_68 import F_MIN  # same test folder

from outrigger_sim.verify import s8_control as s8

DT_S = 0.001
RUN_END_S = 10.0
EVENT_T_S = 2.0
T3_S = 0.82
DIAGONAL_LIFT = (2.1, 0.5)
"""Event-leg (diagonal) lift start and length [s]: window end = 2.6 + T3 = 3.42 s."""
OUTSIDE_LIFT_START_S = 5.0
NOMINAL_FORCE_N = 40e3
V_MAX_M_S = 0.020924
FAST_SETTLE = (0.030, 0.05)
"""RE1bF settlement: 30 mm in 0.05 s (600 mm/s > v_max)."""
SLOW_SETTLE = (0.010, 1.0)
"""10 mm in 1 s (10 mm/s < v_max)."""


def _span(tp: np.ndarray, start_s: float, length_s: float) -> np.ndarray:
    return (tp >= start_s - 1e-9) & (tp < start_s + length_s - 1e-9)


def _judge(*, settle_leg: str = "FL", level: str = "top", fs_kN: float = 0.0,
           settle: tuple[float, float] = FAST_SETTLE, lift_s: float = 0.054,
           gap_m: float = 0.0001, lift_leg: str | None = None,
           mean_force_N: float = NOMINAL_FORCE_N,
           adjacent_window_lift_s: float = 0.0) -> tuple[dict, dict, list[dict]]:
    """Synthetic fast case: the diagonal leg lifts inside the window, ``lift_leg`` (default the
    first adjacent leg) lifts ``lift_s`` after it with a pad rise of ``gap_m``. Returns the
    split, the F_min values and the U-S8-32 + F_min rows after the U-S8-75 step."""
    tp = np.round(np.arange(0.0, RUN_END_S + 1e-9, DT_S), 10)
    airborne = np.zeros((tp.size, 4), bool)
    ball_z = np.zeros((tp.size, 4))
    force = np.full((tp.size, 4), mean_force_N)
    diagonal = s8.DIAGONAL_LEG[settle_leg]
    adjacent = [leg for leg in s8.LEGS if leg not in (settle_leg, diagonal)]
    airborne[_span(tp, *DIAGONAL_LIFT), s8.LEGS.index(diagonal)] = True
    if adjacent_window_lift_s:
        airborne[_span(tp, 2.2, adjacent_window_lift_s), s8.LEGS.index(adjacent[1])] = True
    j = s8.LEGS.index(lift_leg or adjacent[0])
    lifted = _span(tp, OUTSIDE_LIFT_START_S, lift_s)
    airborne[lifted, j] = True
    ball_z[lifted, j] = np.linspace(0.0, gap_m, int(lifted.sum()))
    ball_z[tp >= OUTSIDE_LIFT_START_S + lift_s - 1e-9, j] = 0.0
    depth_m, ramp_s = settle
    split = s8.settle_lift_split(tp, airborne, ball_z, EVENT_T_S, settle_leg, depth_m, ramp_s,
                                 t3_s=T3_S)
    w_end = EVENT_T_S + split["window_end_rel_s"]
    fmin = s8.g1_fmin_after_window(tp, force, airborne, w_end, F_MIN)
    in_scope = s8.g1_u75_scope(is_fast=True, settle_speed_mm_s=split["settle_speed_mm_s"],
                               v_max_m_s=V_MAX_M_S, event_leg=settle_leg, level=level,
                               fs_kN=fs_kN)
    lifts = s8.adjacent_lifts_after_window(tp, airborne, ball_z, w_end, split["adjacent_legs"])
    s8._g1_apply_u75(split, fmin, lifts, in_scope)
    rows = s8.g1_u_s8_32_fast_rows("X", split) + s8.g1_fmin_fast_rows("X", fmin)
    return split, fmin, rows


def _row(rows: list[dict], prefix: str) -> dict:
    found = [r for r in rows if str(r["item"]).startswith(prefix)]
    assert len(found) == 1
    return found[0]


def _u57_row(rows: list[dict]) -> dict:
    return _row(rows, "C-S8-72 U-S8-32 adjacent legs U57")


def _fmin_row(rows: list[dict]) -> dict:
    return _row(rows, s8.G1_FMIN_ITEM)


def _assert_exception_pass(split: dict, fmin: dict, rows: list[dict]) -> None:
    for row in (_u57_row(rows), _fmin_row(rows)):
        assert row["passed"] is True and row["kind"] == "judged"
        assert row["flag"] is True and f"FLAG {s8.U75_FLAG}" in row["note"]
    assert split["u57_pass_without_u75"] is False and fmin["passed_without_u75"] is False


def _assert_fails_without_flag(rows: list[dict], reason: str) -> None:
    for row in (_u57_row(rows), _fmin_row(rows)):
        assert row["passed"] is False and "flag" not in row
        assert f"{s8.U75_FLAG} not applied ({reason})" in row["note"]


@pytest.mark.parametrize(("event", "lift_s", "gap_m"),
                         [("#1 RE1bF FL LEVEL", 0.054, 0.00010),
                          ("#7 FS24 FL READY", 0.083, 0.00030)])
def test_1_c72_cases_pass_with_flag(event: str, lift_s: float, gap_m: float) -> None:
    """① C-S8-72 #1 / #7 (F_s 0, top, FL): the adjacent RL lift after the window passes."""
    split, fmin, rows = _judge(lift_s=lift_s, gap_m=gap_m)
    assert split["adjacent_outside_window_s"] == pytest.approx(lift_s), event
    exception = split["u75_exception"]
    assert exception["outside_gap_max_m"] == pytest.approx(gap_m)
    assert fmin["u75_exception"]["adjacent_lift_s"] == pytest.approx(lift_s)
    assert fmin["mean05_min_all_kN"] >= F_MIN / 1e3
    _assert_exception_pass(split, fmin, rows)


def test_2_case_without_outside_lift_is_untouched() -> None:
    """② c74 / c68b form: no adjacent lift after the window -> no exception record, no FLAG."""
    split, fmin, rows = _judge(lift_s=0.0)
    assert "u75_exception" not in split and "u75_exception" not in fmin
    assert split["u57_pass"] is True and fmin["passed"] is True
    for row in (_u57_row(rows), _fmin_row(rows)):
        assert "flag" not in row and s8.U75_FLAG not in row["note"]


@pytest.mark.parametrize("scope_change", [
    {"settle_leg": "RL"},
    {"level": "bottom"},
    {"level": "middle"},
    {"fs_kN": 2.0},
    {"fs_kN": 4.0},
    {"settle": SLOW_SETTLE},
])
def test_3_outside_the_scope_still_fails(scope_change: dict) -> None:
    """③ rear event, other level, F_s >= 2 kN or a settlement slower than v_max: the outside
    lift still fails both rows (record says why)."""
    split, fmin, rows = _judge(**scope_change)
    assert split["u75_exception"]["in_scope"] is False
    assert split["u57_pass"] is False and fmin["passed"] is False
    _assert_fails_without_flag(rows, "out of scope")


@pytest.mark.parametrize(("lift_s", "gap_m"), [(0.054, 0.0006), (0.12, 0.0001)])
def test_4_over_the_limits_fails_inside_the_scope(lift_s: float, gap_m: float) -> None:
    """④ gap 0.6 mm or 0.12 s fails although the case is inside the scope."""
    split, fmin, rows = _judge(lift_s=lift_s, gap_m=gap_m)
    assert split["u75_exception"]["in_scope"] is True
    assert split["u75_exception"]["within_limits"] is False
    assert split["u57_pass"] is False and fmin["passed"] is False
    _assert_fails_without_flag(rows, "limits or other parts not met")


def test_limits_are_inclusive() -> None:
    """Boundary: exactly 0.1 s and 0.5 mm pass; F_s just below 2 kN is inside the scope."""
    split, fmin, rows = _judge(lift_s=s8.U75_LIFT_MAX_S, gap_m=s8.U75_GAP_MAX_M, fs_kN=1.999)
    _assert_exception_pass(split, fmin, rows)


def test_front_right_event_is_in_scope() -> None:
    split, fmin, rows = _judge(settle_leg="FR")
    _assert_exception_pass(split, fmin, rows)


def test_event_leg_lift_after_window_is_not_excepted() -> None:
    """The F_min (b) exception covers adjacent-leg lift only: a late lift of the settled leg
    (event leg, shorter than the diagonal's, so the window end stays) is not excepted."""
    split, fmin, rows = _judge(lift_leg="FL")
    assert "u75_exception" not in split
    assert fmin["u75_exception"]["event_leg_lift_s"] == pytest.approx(0.054)
    assert fmin["passed"] is False and "flag" not in _fmin_row(rows)


def test_mean_below_f_min_is_not_excepted() -> None:
    """(a) 0.5 s mean unchanged: a mean below F_min fails although the lift is within limits."""
    _split, fmin, rows = _judge(mean_force_N=F_MIN * 0.9)
    assert fmin["u75_exception"]["mean_ok"] is False
    assert fmin["passed"] is False and "flag" not in _fmin_row(rows)


def test_in_window_u57_failure_is_not_excepted() -> None:
    """The exception covers the outside part only: an in-window adjacent sum > 0.5 s fails."""
    split, _fmin, rows = _judge(adjacent_window_lift_s=0.6)
    assert split["u75_exception"]["inside_window_ok"] is False
    assert split["u57_pass"] is False and "flag" not in _u57_row(rows)


def test_step_settlement_counts_as_fast() -> None:
    """A step settlement (ramp 0, no speed) is faster than v_max."""
    assert s8.g1_u75_scope(is_fast=True, settle_speed_mm_s=None, v_max_m_s=V_MAX_M_S,
                           event_leg="FL", level="top", fs_kN=0.0) is True
    assert s8.g1_u75_scope(is_fast=False, settle_speed_mm_s=600.0, v_max_m_s=V_MAX_M_S,
                           event_leg="FL", level="top", fs_kN=0.0) is False
