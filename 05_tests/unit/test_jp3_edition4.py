"""436.9 J-P3 remedy edition 4a (``jp3_remedy_spec.md`` 13.7, 2.9, 2.10, 6.3): the test-only
rule constants, R5-7 (retract lock start with ``p_hat + delta_m``) and the per-read records.

T-JR-02 additions (refusal, pickle, options round trip), T-JR-05 (j) - (m), T-JR-18.
"""

from __future__ import annotations

import math
import pickle
from dataclasses import replace

import numpy as np
import pytest

from outrigger_sim.control import extend_start_bound as esb
from outrigger_sim.control.extend_start_bound import EXTEND_HOLD_REVISION, ExtendStartBound
from outrigger_sim.control.two_pressure import (
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.hydraulics.v5_options import HydraulicOptions

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
STROKE_MAX_M = 0.70
F_MIN_N = 9414.59
RETRACT_ANCHOR_PA = (34.818 * BAR, 34.352 * BAR, 31.193 * BAR, 30.591 * BAR)
RR = 3
HOLD_SPEED_M_S = 0.01 * V_MAX
TEST_RULES = (("carry_end_rule", "fresh_stretch", "ALLOW_FRESH_STRETCH_FOR_TEST"),
              ("retract_start_rule", "model_only", "ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST"))


def _bound(**changes) -> ExtendStartBound:
    return ExtendStartBound(revision=EXTEND_HOLD_REVISION, **changes)


def _monitor(bound: ExtendStartBound | None = None) -> TwoPressureMonitor:
    settings = replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound",
                       extend_start_bound=bound or _bound())
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                                 stroke_max_m=STROKE_MAX_M,
                                 retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
    monitor.rod_state[RR] = RodSensorState.FALLBACK
    return monitor


class Run:
    """Reads of one RR schedule; ``t_s`` continues across calls."""

    def __init__(self, monitor: TwoPressureMonitor) -> None:
        self.monitor = monitor
        self.t_s = 0.0
        self.rows: list[dict] = []

    def periods(self, command_m_s: float, count: int, head_bar: float = 60.0,
                heads_bar: list[float] | None = None) -> list[dict]:
        rows = []
        for k in range(count):
            self.t_s = round(self.t_s + PERIOD_S, 9)
            head = head_bar if heads_bar is None else heads_bar[k]
            commanded = np.zeros(4)
            commanded[RR] = command_m_s
            self.monitor.read(self.t_s, np.full(4, head * BAR), np.full(4, 5.0 * BAR),
                              commanded, False, 2e3, stroke_m=np.full(4, 0.395))
            rows.append(self.monitor.extend_bound_trace_row())
        self.rows += rows
        return rows

    @property
    def stretch(self):
        return self.monitor._lock_stretches[RR]


def _classes(rows: list[dict]) -> list[str]:
    return [row["class"][RR] for row in rows]


def _loaded_lock_then(run: Run) -> None:
    """Extension, then a lock whose head falls 90 -> 60 bar (④ well above the floor)."""
    run.periods(0.5 * V_MAX, 20)
    run.periods(0.0, 4, heads_bar=[90.0, 80.0, 70.0, 60.0])


# --- T-JR-02 (edition 4a 13.7) ------------------------------------------------------------------

@pytest.mark.parametrize(("name", "value", "constant"), TEST_RULES)
def test_t_jr_02_test_only_rules_need_their_constant(monkeypatch, name, value, constant) -> None:
    with pytest.raises(ValueError, match=constant):
        _bound(**{name: value})
    monkeypatch.setattr(esb, constant, True)
    assert getattr(_bound(**{name: value}), name) == value
    with pytest.raises(ValueError):
        _bound(**{name: "something_else"})


@pytest.mark.parametrize(("name", "value", "constant"), TEST_RULES)
def test_t_jr_02_pickle_with_a_test_rule_fails_with_the_constant_off(
        monkeypatch, name, value, constant) -> None:
    """A pickle skips ``__post_init__``: the monitor refuses at construction and on its first
    revision 5 read (``check_allowed``)."""
    monkeypatch.setattr(esb, constant, True)
    bound = _bound(**{name: value})
    monitor = _monitor(bound)
    Run(monitor).periods(0.5 * V_MAX, 2)
    monitor_bytes, bound_bytes = pickle.dumps(monitor), pickle.dumps(bound)
    monkeypatch.setattr(esb, constant, False)
    restored_bound = pickle.loads(bound_bytes)
    with pytest.raises(ValueError, match=constant):
        restored_bound.check_allowed()
    with pytest.raises(ValueError, match=constant):
        _monitor(restored_bound)
    restored = pickle.loads(monitor_bytes)
    with pytest.raises(ValueError, match=constant):
        Run(restored).periods(0.0, 1)


@pytest.mark.parametrize(("name", "value", "constant"), TEST_RULES)
def test_t_jr_02_options_have_no_path_to_the_test_rules(name, value, constant) -> None:
    """``HydraulicOptions`` round trip neither writes nor takes the two rules: a stored dict
    with the key reads back as the same options (the key has no field to go to), and the
    controller bound they build keeps the default rule."""
    options = HydraulicOptions(extend_start_tracked=True, extend_start_hold=True)
    values = options.to_dict()
    assert name not in values
    assert HydraulicOptions.from_dict(values) == options
    assert HydraulicOptions.from_dict({**values, name: value}) == options
    assert not any(name in field for field in HydraulicOptions.__dataclass_fields__)
    assert getattr(_bound(), name) != value


def test_t_jr_02_meta_carries_the_rule_identity() -> None:
    bound = _bound()
    assert bound.to_meta()["retract_start_rule"] == "with_tracker"
    assert "retract_start_rule" not in ExtendStartBound().to_meta()  # revision 4 unchanged
    assert bound.identity() == {"spec_edition": "8be9de22",
                                "carry_end_rule": "inherit_when_gate_shut",
                                "retract_start_rule": "with_tracker"}


# --- T-JR-05 (j) - (m) ---------------------------------------------------------------------------

def _carry_ret_ret_lock(bound=None, lock_command_m_s: float = 0.0, lock_periods: int = 3):
    run = Run(_monitor(bound))
    _loaded_lock_then(run)
    moves = run.periods(-0.5 * V_MAX, 8)
    locks = run.periods(lock_command_m_s, lock_periods)
    return run, moves, locks


def test_t_jr_05_j_lock_after_a_retraction_takes_the_tracker_term(monkeypatch) -> None:
    """(j) RET -> LOCK: the first window candidate is ``max(13 + p_h / 3, p_ret, p_hat +
    delta_m, lookback)``, source ``retract_tracker``; ``model_only`` leaves the term out."""
    run, moves, locks = _carry_ret_ret_lock()
    assert "ret" in _classes(moves) and _classes(locks)[0] == "lock"
    stretch = run.stretch
    start_Pa, head_Pa = stretch.candidates[0]
    tracker_Pa = locks[0]["ext_bound_Pa"][RR]
    model_Pa = run.monitor._lock_start_model_Pa(RR, -1.0, head_Pa)
    assert start_Pa == max(model_Pa, tracker_Pa, stretch.previous_moving_max_Pa)
    assert start_Pa >= tracker_Pa > model_Pa
    assert stretch.candidate_sources[0] == "retract_tracker"
    assert locks[0]["model_bound_source"][RR] == "retract_tracker"
    monkeypatch.setattr(esb, "ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST", True)
    old_run, _, _ = _carry_ret_ret_lock(_bound(retract_start_rule="model_only"))
    old_start_Pa = old_run.stretch.candidates[0][0]
    assert old_start_Pa < start_Pa
    assert old_run.stretch.candidate_sources[0] != "retract_tracker"


def test_r5_both_application_points_call_the_one_r5_7_function(monkeypatch) -> None:
    """Addendum 4a-2 R5: the ret / carry_ret start value and the window candidate after a
    retraction both take their value from ``_retract_lock_start_model_Pa``."""
    import sys

    callers: list[str] = []
    original = TwoPressureMonitor._retract_lock_start_model_Pa

    def counted(self, *args):
        callers.append(sys._getframe(1).f_code.co_name)
        return original(self, *args)

    monkeypatch.setattr(TwoPressureMonitor, "_retract_lock_start_model_Pa", counted)
    _carry_ret_ret_lock()
    assert {"_track_moving_leg", "_add_lock_candidate"} <= set(callers)


def test_t_jr_05_k_hold_and_carry_candidates_have_no_tracker_term() -> None:
    """(k) R9: the R5-2 hold candidates of an open stretch and the carry candidates stay at
    ``max(retract model, p_ret)``."""
    run, _, _ = _carry_ret_ret_lock(lock_periods=15)
    holds = run.periods(-0.5 * HOLD_SPEED_M_S, 3)
    assert _classes(holds) == ["hold"] * 3
    stretch = run.stretch
    hold_candidates = [candidate for candidate, source in
                       zip(stretch.candidates, stretch.candidate_sources, strict=True)
                       if source == "retract_hold"]
    assert len(hold_candidates) == 3
    for value, head in hold_candidates:
        assert value == run.monitor._lock_start_model_Pa(RR, -1.0, head)
    # (m) the open stretch's retracting holds after the window add no R5-7 candidate
    assert stretch.candidate_sources[-3:] == ("retract_hold",) * 3


def test_t_jr_05_k_carry_candidate_has_no_tracker_term() -> None:
    run = Run(_monitor())
    _loaded_lock_then(run)
    rows = run.periods(-0.015 * V_MAX, 2, heads_bar=[58.0, 56.0])
    assert _classes(rows) == ["carry_ret", "carry_ret"]
    carry = run.monitor._carry_states[RR]
    value, head = carry.candidates[-1]
    assert carry.candidate_sources[-1] == "retract_hold"
    assert value == run.monitor._lock_start_model_Pa(RR, -1.0, head)


RETRACT_FLOOR_PA = RETRACT_ANCHOR_PA[RR]
ALLOWANCE_PA = 1.0
"""(k′) 1 Pa allowance."""


def _retract_floor_Pa(head_Pa: float) -> float:
    """The floor input of a retract period, ``max(p_ret, 13 + p_h / 3)`` (4a-2 1.2 (k′);
    ``test_t_jr_05_k_prime_floor_is_the_monitor_floor`` ties it to the monitor's own)."""
    return max(RETRACT_FLOOR_PA, 13.0 * BAR + head_Pa / 3.0)


@pytest.mark.parametrize("head_bar", [45.0, 50.0, 60.0, 70.0])
def test_t_jr_05_k_prime_floor_is_the_monitor_floor(head_bar) -> None:
    """The (k′) floor is the monitor's tracker floor input (``_advance_hold_bound``)."""
    monitor = _monitor()
    head_Pa = head_bar * BAR
    floor_Pa = max(monitor._retract_lock_floor_Pa[RR], monitor._retract_rod_estimate_Pa(head_Pa))
    assert floor_Pa == pytest.approx(_retract_floor_Pa(head_Pa), abs=ALLOWANCE_PA)


def _ret_then_lock(retract_head_bar: float, window_head_bar: float, *, loaded: bool):
    """A retraction at one head, then a lock read at the window head: (last ret row, lock
    row, stretch)."""
    run = Run(_monitor())
    if loaded:
        _loaded_lock_then(run)
        moves = run.periods(-0.5 * V_MAX, 8, head_bar=retract_head_bar)
    else:
        run.periods(0.5 * V_MAX, 5, head_bar=retract_head_bar)
        moves = run.periods(-0.5 * V_MAX, 3, head_bar=retract_head_bar)
    assert _classes(moves)[-1] == "ret"
    lock = run.periods(0.0, 1, head_bar=window_head_bar)[0]
    assert lock["class"][RR] == "lock"
    return moves[-1], lock, run.stretch


@pytest.mark.parametrize(("loaded", "retract_head_bar", "window_head_bar"),
                         [(True, 60.0, 60.0), (True, 60.0, 50.0), (False, 60.0, 60.0),
                          (False, 60.0, 70.0)])
def test_t_jr_05_k_prime_1_tracker_term_is_above_the_last_retract_floor(
        loaded, retract_head_bar, window_head_bar) -> None:
    """(k′) 1 (addendum 4a-2 1.2): after a retraction the R5-7 term of the window
    ``p_hat + delta_m >= max(p_ret, 13 + h_R / 3) + delta_m`` (1 Pa), ``h_R`` = the head
    reading of the last retract period."""
    last_ret, lock, _ = _ret_then_lock(retract_head_bar, window_head_bar, loaded=loaded)
    head_R_Pa = last_ret["head_read_Pa"][RR]
    term_Pa = lock["ext_bound_Pa"][RR]
    assert term_Pa >= _retract_floor_Pa(head_R_Pa) + esb.BOUND_MARGIN_PA - ALLOWANCE_PA


@pytest.mark.parametrize(("loaded", "retract_head_bar", "window_head_bar"),
                         [(True, 60.0, 60.0), (True, 60.0, 50.0), (False, 60.0, 60.0),
                          (False, 60.0, 45.0)])
def test_t_jr_05_k_prime_2_window_at_or_below_the_retract_head_takes_the_term(
        loaded, retract_head_bar, window_head_bar) -> None:
    """(k′) 2: ``h_w <= h_R``: the window candidate is the R5-7 term (source
    ``retract_tracker``) and lies ``delta_m`` or more above the retract model candidate
    ``max(p_ret, 13 + h_w / 3)``."""
    last_ret, lock, stretch = _ret_then_lock(retract_head_bar, window_head_bar, loaded=loaded)
    start_Pa, head_w_Pa = stretch.candidates[0]
    assert head_w_Pa <= last_ret["head_read_Pa"][RR]
    assert stretch.candidate_sources[0] == "retract_tracker"
    assert lock["model_bound_source"][RR] == "retract_tracker"
    assert start_Pa >= _retract_floor_Pa(head_w_Pa) + esb.BOUND_MARGIN_PA - ALLOWANCE_PA
    assert start_Pa == max(lock["ext_bound_Pa"][RR], stretch.previous_moving_max_Pa)


def test_t_jr_05_k_prime_3_higher_window_head_keeps_the_retract_model() -> None:
    """(k′) 3: ``h_w > h_R + 3 delta_m`` with ``p_hat`` at the last retract period's floor:
    the window candidate is the retract model candidate (the R5-7 term does not win, the
    source is the model side)."""
    retract_head_bar, window_head_bar = 60.0, 70.0
    last_ret, lock, stretch = _ret_then_lock(retract_head_bar, window_head_bar, loaded=False)
    head_R_Pa = last_ret["head_read_Pa"][RR]
    # premise: p_hat is the floor of the last retract period (p_hat + delta_m = floor + delta_m)
    assert last_ret["ext_bound_Pa"][RR] == pytest.approx(
        _retract_floor_Pa(head_R_Pa) + esb.BOUND_MARGIN_PA, abs=ALLOWANCE_PA)
    start_Pa, head_w_Pa = stretch.candidates[0]
    assert head_w_Pa > head_R_Pa + 3.0 * esb.BOUND_MARGIN_PA
    assert start_Pa == pytest.approx(_retract_floor_Pa(head_w_Pa), abs=ALLOWANCE_PA)
    assert stretch.candidate_sources[0] != "retract_tracker"
    assert lock["model_bound_source"][RR] != "retract_tracker"


def test_t_jr_05_l_tracker_candidate_pairs_with_the_window_head() -> None:
    """(l) A4: retract at a low head, lock at a higher head: the R5-7 candidate's head is the
    window head; a later head drop adds ``R_ub (p_h,window - p_h)``."""
    run = Run(_monitor())
    _loaded_lock_then(run)
    run.periods(-0.5 * V_MAX, 8, head_bar=40.0)
    locks = run.periods(0.0, 12, head_bar=70.0)
    stretch = run.stretch
    tracker_index = stretch.candidate_sources.index("retract_tracker")
    start_Pa, head_Pa = stretch.candidates[tracker_index]
    assert head_Pa == 70.0 * BAR
    assert locks[0]["model_bound_head_Pa"][RR] == 70.0 * BAR
    dropped = run.periods(0.0, 1, head_bar=50.0)
    bound_Pa = dropped[0]["model_bound_Pa"][RR]
    assert bound_Pa >= start_Pa + stretch.ratio_bound * 20.0 * BAR - 1.0


@pytest.mark.parametrize("path", ["carry_ret_ret_lock", "carry_ret_ret_hold", "ext_ret_hold",
                                  "shut_carry_hold"])
def test_t_jr_05_m_every_stretch_after_a_retraction_starts_with_the_tracker(path) -> None:
    """(m) A5: the four paths all have an R5-7 candidate from the stretch's first period."""
    run = Run(_monitor())
    if path == "ext_ret_hold":
        run.periods(0.5 * V_MAX, 20)
        moves = run.periods(-0.5 * V_MAX, 5)
        assert _classes(moves) == ["ret"] * 5
    else:
        _loaded_lock_then(run)
        if path == "shut_carry_hold":
            moves = run.periods(-0.015 * V_MAX, 2, heads_bar=[58.0, 56.0])
            assert _classes(moves) == ["carry_ret"] * 2
        else:
            moves = run.periods(-0.5 * V_MAX, 8)
            assert "ret" in _classes(moves)
    command = 0.0 if path == "carry_ret_ret_lock" else -0.5 * HOLD_SPEED_M_S
    first = run.periods(command, 1)[0]
    assert first["class"][RR] == ("lock" if command == 0.0 else "hold")
    assert "retract_tracker" in run.stretch.candidate_sources
    if path == "shut_carry_hold":
        assert run.stretch.inherited_candidates > 0  # R5-6 together with R5-7
        assert run.stretch.ret_after_gate_s == 0.0
    else:
        assert run.stretch.ret_after_gate_s > 0.0


# --- T-JR-18 (records) ---------------------------------------------------------------------------

def test_t_jr_18_dominant_candidate_columns_match_the_bound() -> None:
    """Per read: the source / age / head / inherited columns belong to the candidate that
    makes ④ (recomputed within 1 Pa); ``carry_log`` rows of shut-gate carries ending in a lock
    or hold = ``gate_never_opened_carries``."""
    monitor = _monitor()
    run = Run(monitor)
    _loaded_lock_then(run)
    checked = 0
    schedule = [(-0.015 * V_MAX, 2, [58.0, 56.0]), (-0.2e-3, 2, [55.0, 54.0]),
                (-0.5 * V_MAX, 8, None), (0.0, 5, None), (0.5 * V_MAX, 4, None),
                (0.0, 3, [65.0, 60.0, 55.0])]
    for command, count, heads in schedule:
        rows = run.periods(command, count, heads_bar=heads)
        for row in rows:
            if row["class"][RR] not in ("lock", "hold"):
                assert row["model_bound_source"][RR] is None
                continue
            stretch = run.stretch
            ratio = stretch.ratio_bound
            head_Pa = row["head_read_Pa"][RR]
            values = [start + ratio * max(head - head_Pa, 0.0)
                      for start, head in stretch.candidates]
            index = int(np.argmax(values))
            assert values[index] == pytest.approx(row["model_bound_Pa"][RR], abs=1.0)
            assert row["model_bound_head_Pa"][RR] == stretch.candidates[index][1]
            assert row["model_bound_source"][RR] == stretch.candidate_sources[index]
            age = row["t_s"] - stretch.candidate_times[index]
            assert row["model_bound_age_s"][RR] == pytest.approx(age)
            assert row["model_bound_inherited"][RR] == stretch.candidate_inherited[index]
            checked += 1
    assert checked >= 10
    log = monitor.meta()["extend_start_record"]["carry_log"]
    shut = [row for row in log if row["end_class"] in ("lock", "hold") and not row["gate_opened"]]
    assert len(shut) == monitor._extend_tracker.gate_never_opened_carries[RR]
    assert all(row["leg"] == "RR" for row in log)
    assert math.isfinite(log[0]["sum_abs_u_T_m"])
