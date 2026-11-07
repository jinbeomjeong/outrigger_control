"""``extend_start_rule`` of ``control/two_pressure`` (spec ``p3_extend_start_spec.md`` 4,
T-P3-1 meta, T-P3-4 retract reset, refusals and pickles; review 2026-11-07 records)."""

from __future__ import annotations

import pickle
import types
from dataclasses import replace

import numpy as np
import pytest

from outrigger_sim.control.extend_start_bound import ExtendStartBound
from outrigger_sim.control.two_pressure import (
    ExtendStartRule,
    LockedRatioRule,
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.hydraulics.v5_options import (
    CheckDelaySetting,
    HydraulicOptions,
    check_extend_start,
)
from outrigger_sim.params import load_params

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
RETRACT_ANCHOR_PA = (34.818 * BAR, 34.352 * BAR, 31.193 * BAR, 30.591 * BAR)
CONSTANT_START_PA = 13.0 * BAR
FL = 0
EXTEND_KEYS = {"extend_start_rule", "extend_start_bound"}


def _settings(**changes) -> TwoPressureSettings:
    return replace(TwoPressureSettings().with_r8_period(), **changes)


def _tracked() -> TwoPressureSettings:
    return _settings(extend_start_rule="tracked_bound")


def _monitor(settings: TwoPressureSettings) -> TwoPressureMonitor:
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                                 stroke_max_m=0.70,
                                 retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
    monitor.rod_state[FL] = RodSensorState.FALLBACK
    return monitor


def _read(monitor: TwoPressureMonitor, t_s: float, command_FL: float,
          stroke_m: float = 0.3) -> None:
    commanded = np.zeros(4)
    commanded[FL] = command_FL
    monitor.read(t_s, np.full(4, 80.0 * BAR), np.full(4, 5.0 * BAR), commanded, False, 2e3,
                 stroke_m=np.full(4, stroke_m))


def _run(monitor: TwoPressureMonitor, commands: list[float], t0_s: float = 0.0) -> float:
    t_s = t0_s
    for command in commands:
        t_s += PERIOD_S
        _read(monitor, t_s, command)
    return t_s


def test_t_p3_1_meta_has_the_keys_only_with_the_option() -> None:
    assert not EXTEND_KEYS & set(_settings().to_meta())
    assert _settings().extend_start_rule is ExtendStartRule.CONSTANT
    meta = _tracked().to_meta()
    assert meta["extend_start_rule"] == "tracked_bound"
    assert meta["extend_start_bound"] == ExtendStartBound().to_meta()
    assert meta["extend_start_bound"]["hose_factor"] == 1.40


def test_t_p3_1_option_off_reads_bit_for_bit() -> None:
    """``constant`` is the default: the estimate of a fallback leg is the old one."""
    commands = [0.25 * V_MAX] * 5 + [0.0] * 10 + [-0.1 * V_MAX] * 3 + [0.0] * 5
    off, default = _monitor(_settings(extend_start_rule="constant")), _monitor(_settings())
    for k, command in enumerate(commands):
        _read(off, (k + 1) * PERIOD_S, command)
        _read(default, (k + 1) * PERIOD_S, command)
        assert off._legs[FL].rod_estimate_Pa == default._legs[FL].rod_estimate_Pa
    assert off.meta() == default.meta()


def test_moving_and_start_estimates_take_the_bound() -> None:
    """A short extension from the run start (``p = p_ret``): moving estimate and lock start are
    ``max(13 bar, p + delta_m)``, above the constant 13 bar."""
    monitor = _monitor(_tracked())
    _run(monitor, [0.25 * V_MAX] * 2)
    tracker = monitor._extend_tracker
    moving_Pa = monitor._legs[FL].rod_estimate_Pa
    assert moving_Pa == max(CONSTANT_START_PA, tracker.bound_Pa(FL))
    assert moving_Pa > CONSTANT_START_PA
    constant = _monitor(_settings())
    _run(constant, [0.25 * V_MAX] * 2)
    assert constant._legs[FL].rod_estimate_Pa == CONSTANT_START_PA
    t_s = _run(monitor, [0.0], t0_s=0.2)
    stretch = monitor._lock_stretches[FL]
    assert stretch.candidates[0][0] >= tracker.bound_Pa(FL)
    current = monitor.meta()["fallback_lock_current"][0]
    assert current["extend_bound_Pa"] == tracker.bound_Pa(FL)  # at the stretch start
    _run(constant, [0.0], t0_s=0.2)
    assert "extend_bound_Pa" not in constant.meta()["fallback_lock_current"][0]
    assert t_s == pytest.approx(0.3)


def test_long_extension_comes_back_to_the_constant() -> None:
    monitor = _monitor(_tracked())
    _run(monitor, [0.5 * V_MAX] * 30)
    assert monitor._legs[FL].rod_estimate_Pa == CONSTANT_START_PA


def test_t_p3_4_retract_resets_the_bound_to_p_ret() -> None:
    monitor = _monitor(_tracked())
    _run(monitor, [0.5 * V_MAX] * 30)
    assert monitor._extend_tracker.pressure_Pa[FL] < 10.0 * BAR
    _run(monitor, [-0.1 * V_MAX], t0_s=3.0)
    assert monitor._extend_tracker.pressure_Pa[FL] >= RETRACT_ANCHOR_PA[FL]


def test_t_p3_4_counterbalance_and_fixed_are_refused() -> None:
    params = load_params(level="top", model="L2b_NSC").l2b.counterbalance
    with pytest.raises(ValueError, match="extend_start_rule"):
        _tracked().with_lock_valve("counterbalance", params)
    with pytest.raises(ValueError, match="extend_start_rule"):
        _settings(extend_start_rule="tracked_bound", locked_ratio_rule=LockedRatioRule.FIXED)
    with pytest.raises(ValueError):
        _settings(extend_start_rule="other")


def test_t_p3_4_m1c_is_refused() -> None:
    """Review 2026-11-07 (2c): the bound with M1c is refused."""
    with_m1c = HydraulicOptions(rod_release_force=True, check_delay=CheckDelaySetting("VN"))
    with pytest.raises(ValueError, match="M1c"):
        check_extend_start(with_m1c, "tracked_bound")
    check_extend_start(with_m1c, "constant")
    check_extend_start(HydraulicOptions(rod_release_force=True), "tracked_bound")


def test_t_p3_4_pickle_round_trip_continues_bit_for_bit() -> None:
    monitor = _monitor(_tracked())
    t_s = _run(monitor, [0.25 * V_MAX] * 3)
    copy = pickle.loads(pickle.dumps(monitor))
    for command in (0.25 * V_MAX, 0.0, 0.0, -0.1 * V_MAX, 0.3 * V_MAX):
        t_s += PERIOD_S
        _read(monitor, t_s, command)
        _read(copy, t_s, command)
        assert copy._legs[FL].rod_estimate_Pa == monitor._legs[FL].rod_estimate_Pa
    assert copy.meta() == monitor.meta()


def test_t_p3_4_old_pickle_starts_at_p_ret() -> None:
    """A monitor pickled before the option has no tracker: the first read creates it with
    ``p = p_ret`` and ``u_v = 0`` (10.4 ⑧ precedent)."""
    monitor = _monitor(_settings())
    _run(monitor, [0.25 * V_MAX] * 3)
    old = pickle.loads(pickle.dumps(monitor))
    assert "_extend_tracker" not in old.__dict__
    old.refresh_settings(_tracked())
    _read(old, 0.4, 0.25 * V_MAX)
    fresh = _monitor(_tracked())
    _read(fresh, 0.4, 0.25 * V_MAX)
    assert np.array_equal(old._extend_tracker.pressure_Pa, fresh._extend_tracker.pressure_Pa)


def test_review_record_is_kept_with_the_option_on_and_off() -> None:
    """Criteria rev. 6 14.5 (user decision 2026-11-07): tension sub-steps and the delivered /
    commanded ratio at a D2 violation start are in ``review_record`` on and off, equal for the
    same reads; the bound state stays in ``extend_start_record`` (option on only)."""
    metas = []
    for settings in (_settings(), _tracked()):
        monitor = _monitor(settings)
        _run(monitor, [0.25 * V_MAX] * 2)
        metas.append(monitor.meta())
    off, on = metas
    assert "extend_start_record" not in off
    assert set(on["extend_start_record"]) == {"extend_bound_Pa", "valve_estimate_m_s",
                                              "saturated_substeps", "saturation_stop_periods"}
    assert off["review_record"] == on["review_record"]
    assert off["review_record"]["tension_substeps"] == [0, 0, 0, 0]
    assert off["review_record"]["d2_violation_start_ratio"] == [[], [], [], []]


def _pulled_rod_Pa(head_Pa: float, pull_N: np.ndarray) -> np.ndarray:
    """Rod readings whose raw net force ``p_h A_h - p_r A_ann`` is ``-pull_N``."""
    return (head_Pa * HEAD_AREA + pull_N) / ANNULUS


def test_review_record_counts_tension_and_a_d2_start_with_the_option_off() -> None:
    """``tension_premise.md`` S-1 (option off): the zero offset is removed before the
    threshold. FL raw -1.9 kN with the offset -4.286 kN (the L3 FR false count) is a push; RL
    raw -2.6 kN with an offset of +0.1 kN pulls beyond 2.171 kN; FR raw -3.0 kN without an
    offset goes to the uncalibrated count. A D2 violation start records its ratio."""
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
                                 settings=_settings(), stroke_max_m=0.70,
                                 retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
    monitor.set_zero_offsets_N([-4.286e3, 0.0, 0.1e3, 0.2e3])
    head_Pa = 10.0 * BAR
    rod = _pulled_rod_Pa(head_Pa, np.array([1.9e3, 3.0e3, 2.6e3, 1.0e3]))
    commanded = np.full(4, 0.3 * V_MAX)
    monitor.read(0.1, np.full(4, head_Pa), rod, commanded, False, 2e3,
                 stroke_m=np.full(4, 0.3))
    record = monitor.meta()["review_record"]
    assert record["tension_substeps"] == [0, 0, 100, 0]
    assert record["tension_substeps_uncalibrated"] == [0, 100, 0, 0]
    monitor._stroke_rate_m_s = np.array([0.006, 0.0, 0.0, 0.0])
    monitor._record_d2_start(FL, 0.3 * V_MAX)
    ratios = monitor.meta()["review_record"]["d2_violation_start_ratio"]
    assert ratios[FL] == [pytest.approx(0.006 / (0.3 * V_MAX))]


def test_extend_bound_accessor_is_none_off_and_the_tracker_bound_on() -> None:
    """5.5 #1: ``extend_bound_Pa()`` = ``p_hat + delta_m`` per leg after a read; None with the
    option off or before the first read."""
    off = _monitor(_settings())
    _run(off, [0.25 * V_MAX] * 2)
    assert off.extend_bound_Pa() is None
    on = _monitor(_tracked())
    assert on.extend_bound_Pa() is None
    _run(on, [0.25 * V_MAX] * 2)
    expected = [on._extend_tracker.bound_Pa(leg) for leg in range(4)]
    assert on.extend_bound_Pa().tolist() == expected


def test_locked_model_bound_is_the_column_model_part_with_its_source() -> None:
    """6.4 #1: ④ per leg of an open lock stretch (NaN while moving), equal to the estimate of
    a fallback leg (no reading bound ⑤ there); the pilot extend model sets ``M_j``."""
    monitor = _monitor(_settings())
    _run(monitor, [0.25 * V_MAX] * 2)
    assert np.isnan(monitor.locked_model_bound_Pa()[FL])
    assert monitor.locked_model_bound_sources()[FL] is None
    _run(monitor, [0.0] * 3, t0_s=0.2)
    model_Pa = monitor.locked_model_bound_Pa()
    assert model_Pa[FL] == monitor._legs[FL].rod_estimate_Pa
    assert model_Pa[FL] >= CONSTANT_START_PA
    assert monitor.locked_model_bound_sources()[FL] == "pilot_model"


def test_runner_hands_the_bound_through_controller_wrappers() -> None:
    """5.5 #2 (Chrono): the runner finds the bound through ``inner`` / ``ctrl`` wrappers and
    calls the engine check only when the bound is not None."""
    from outrigger_sim import runner

    calls = []
    engine = types.SimpleNamespace(
        check_extend_bound=lambda t, bound, model, sources: calls.append((t, model, sources)))
    c2_like = types.SimpleNamespace(extend_bound_Pa=lambda: np.full(4, 5.5e5),
                                    locked_model_bound_Pa=lambda: np.full(4, 13.0e5),
                                    locked_model_bound_sources=lambda: ["pilot_model"] * 4)
    wrapper = types.SimpleNamespace(inner=types.SimpleNamespace(ctrl=c2_like))
    runner._check_extend_bound(engine, wrapper, 1.5)
    runner._check_extend_bound(engine, types.SimpleNamespace(extend_bound_Pa=lambda: None), 1.6)
    runner._check_extend_bound(types.SimpleNamespace(), wrapper, 1.7)
    assert len(calls) == 1 and calls[0][0] == 1.5
    assert calls[0][1].tolist() == [13.0e5] * 4 and calls[0][2] == ["pilot_model"] * 4


def test_t_p3_1_meta_carries_the_bound_revision() -> None:
    """The option meta carries ``revision`` 3 (spec 10); the off meta has no ③ key."""
    assert _tracked().to_meta()["extend_start_bound"]["revision"] == 3
    assert "extend_start_bound" not in _settings().to_meta()
