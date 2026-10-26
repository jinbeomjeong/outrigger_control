"""P-S8-22 R-5 fallback slope (``s6_control_spec.md`` rev. 61 302 / 304, U-S8-60 .. 62).

V-1 on synthetic lock stretches of the two-pressure monitor and on the controller's R-5:

* (a) without a fallback leg, and with ``fallback_slope = "level"``, nothing changes;
* (b) for ``R_true`` in ``{0, R_rate, R_hi}`` the fallback prediction is not above the one of
  a healthy rod sensor (302.3 "optimism 0"), while the nominal slope alone would be;
* (c) a command inside the last ``n`` periods keeps the level rule;
* (d) above the anchor (``d = 0``) the fall is ``G(R_hi) Dh``;
* (e) 302.6: on a short L1 lock stroke ``plant_meta`` keeps the level bound below the truth;

plus the 302.5 PS2 numbers, the online ratio (304 ④), the settings (304 ①) and pickles.
"""

from __future__ import annotations

import math
import pickle
from collections import deque
from dataclasses import replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    R8_D1_SETTINGS,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    ContactJudge,
    FallbackSlope,
    FastRelevelSettings,
    SoilResponseSettings,
    TargetSettings,
)
from outrigger_sim.control.target import TargetAcceptance
from outrigger_sim.control.two_pressure import (
    FallbackRatioChoice,
    FallbackRatioSource,
    FallbackSlopeInputs,
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.control.zero_calibration import ZeroCalibrationMode
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
ROD_WEIGHT_N = np.array([1047.19, 1047.19, 717.48, 717.48])
V_MAX = 0.020924
F_MIN_N = 9414.59
STROKE_MAX_M = 0.70
KAPPA = 1.10
FALLBACK_BAND_N = 13e3
"""``B_fb``: the friction band of a fallback leg (``fallback_min_band_N``)."""
RATE_INTERVALS = 3
HORIZON_PERIODS = 4
FR = 1
FL = 0
LOCK_HEAD_PA = 97.0 * BAR
PILOT_START_PA = 13.0 * BAR
"""Pilot-check start after an extension (``locked_start_extend_Pa``): the monitor's ``M``."""
WINDOW_SAMPLES = 12
"""Command-free samples held flat after the move: the lock window (about 1.03 s) and two more."""
HEAD_FALL_PER_PERIOD_PA = 1.5 * BAR
OTHER_HEAD_PA = 80.0 * BAR
OTHER_ROD_PA = 5.0 * BAR


def _column_ratio(stroke_m: float, kappa: float = KAPPA) -> float:
    """``R_ub(s)`` of the monitor (dead lengths 0.08 / 0.02 m, ``s' = s + 5 mm``)."""
    bound_stroke_m = stroke_m + 0.005
    return kappa * (0.08 + bound_stroke_m) / (0.02 + STROKE_MAX_M - bound_stroke_m)


def _nominal_ratio(stroke_m: float) -> float:
    return (0.05 + stroke_m) / (0.05 + STROKE_MAX_M - stroke_m)


def _gain(ratio: float, leg: int = FR) -> float:
    return HEAD_AREA[leg] + ratio * ANNULUS[leg]


def _monitor() -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
                              settings=TwoPressureSettings().with_r8_period(),
                              rod_weight_N=ROD_WEIGHT_N, stroke_max_m=STROKE_MAX_M)


def _choice(source: str) -> FallbackRatioChoice:
    return FallbackRatioChoice(FallbackRatioSource(source), RATE_INTERVALS)


def _feed(monitor, samples, stroke_m, choice, leg=FR):
    """Read ``(command, head, rod)`` samples on ``leg`` at ``stroke_m`` (one value, or one per
    sample); the other legs stay locked and steady. Returns per sample (lower reading of
    ``leg``, R-5 inputs of ``leg``)."""
    strokes = np.broadcast_to(np.asarray(stroke_m, dtype=float), (len(samples),))
    rows = []
    for k, (command, head_Pa, rod_Pa) in enumerate(samples):
        commanded, head, rod = np.zeros(4), np.full(4, OTHER_HEAD_PA), np.full(4, OTHER_ROD_PA)
        commanded[leg], head[leg], rod[leg] = command, head_Pa, rod_Pa
        stroke = np.full(4, 0.4)
        stroke[leg] = strokes[k]
        forces = monitor.read(round(k * PERIOD_S, 10), head, rod, commanded, False, 2e3,
                              stroke_m=stroke, r5_fallback_ratios=choice)
        rows.append((float(forces.lower[leg]), monitor.r5_fallback_inputs(leg)))
    return rows


def _lock_samples(heads_Pa, true_ratio, rod_at_lock_Pa=PILOT_START_PA):
    """A move, the flat lock window, then the locked heads ``heads_Pa`` with the true rod side
    ``p_r0 + R_true (h_lock - p_h)`` (A1)."""
    samples = [(0.5 * V_MAX, LOCK_HEAD_PA, rod_at_lock_Pa)] * 5
    samples += [(0.0, LOCK_HEAD_PA, rod_at_lock_Pa)] * WINDOW_SAMPLES
    for head_Pa in heads_Pa:
        samples.append((0.0, head_Pa, rod_at_lock_Pa + true_ratio * (LOCK_HEAD_PA - head_Pa)))
    return samples


def _falling_heads(count: int) -> list[float]:
    return [LOCK_HEAD_PA - HEAD_FALL_PER_PERIOD_PA * (i + 1) for i in range(count)]


def _fallback_monitor(leg: int = FR) -> TwoPressureMonitor:
    monitor = _monitor()
    monitor.rod_state[leg] = RodSensorState.FALLBACK
    return monitor


# --- (b) optimism 0 (302.3) --------------------------------------------------------------------


def _predictions(rows, samples, true_ratio, leg=FR):
    """(fallback prediction, nominal-only prediction, healthy-sensor prediction) per eligible
    sample; the healthy band ``b`` is ``B_fb`` (the worst case of ``b <= B_fb``)."""
    out = []
    scale = HORIZON_PERIODS / RATE_INTERVALS
    for (lower_N, inputs), (_, head_Pa, rod_Pa) in zip(rows, samples, strict=True):
        if inputs is None or inputs.head_drop_Pa < 0.0:
            continue
        level_N = lower_N - FALLBACK_BAND_N
        drop_N, _ = inputs.drop_N(RATE_INTERVALS, HORIZON_PERIODS)
        nominal_N = inputs.force_gain_N_per_Pa(inputs.rate_ratio) * inputs.head_drop_Pa
        true_force_N = head_Pa * HEAD_AREA[leg] - rod_Pa * ANNULUS[leg]
        healthy_N = (true_force_N - FALLBACK_BAND_N
                     - scale * _gain(true_ratio, leg) * inputs.head_drop_Pa)
        out.append((level_N - scale * drop_N, level_N - scale * nominal_N, healthy_N))
    return np.array(out)


STROKE_LONG_M = 0.659
"""Front lock stroke of the PS2 case (302.4: ``R_ub`` 14.56, ``R_nom`` 7.77)."""


@pytest.mark.parametrize("ratio_name", ["zero", "rate", "high"])
def test_b_column_nominal_is_not_above_a_healthy_sensor(ratio_name) -> None:
    high_ratio = _column_ratio(STROKE_LONG_M) / KAPPA
    true_ratio = {"zero": 0.0, "rate": _nominal_ratio(STROKE_LONG_M), "high": high_ratio}
    samples = _lock_samples(_falling_heads(30), true_ratio[ratio_name])
    rows = _feed(_fallback_monitor(), samples, STROKE_LONG_M, _choice("column_nominal"))
    eligible = [inputs for _, inputs in rows if inputs is not None]
    assert len(eligible) >= 25
    assert eligible[-1].high_ratio == pytest.approx(high_ratio, rel=1e-12)
    assert eligible[-1].rate_ratio == pytest.approx(_nominal_ratio(STROKE_LONG_M), rel=1e-12)
    assert eligible[-1].level_ratio == pytest.approx(_column_ratio(STROKE_LONG_M), rel=1e-12)
    predictions = _predictions(rows, samples, true_ratio[ratio_name])
    fallback, nominal_only, healthy = predictions.T
    assert np.all(fallback <= healthy + 1e-6)
    if ratio_name == "high":  # 302.3: without the gap term the nominal slope is optimistic
        assert np.any(nominal_only > healthy + 100.0)


@pytest.mark.parametrize("true_ratio", [0.0, 1.296])
def test_b_plant_meta_is_not_above_a_healthy_sensor(true_ratio) -> None:
    stroke_m = 0.40
    samples = _lock_samples(_falling_heads(30), true_ratio)
    rows = _feed(_fallback_monitor(), samples, stroke_m, _choice("plant_meta"))
    eligible = [inputs for _, inputs in rows if inputs is not None]
    assert eligible[-1].high_ratio == eligible[-1].rate_ratio == 1.296
    fallback, _, healthy = _predictions(rows, samples, true_ratio).T
    assert len(fallback) >= 25
    assert np.all(fallback <= healthy + 1e-6)


def test_b_plant_meta_takes_a_larger_plant_ratio_as_r_hi() -> None:
    plant_ratio = (1.4, 1.4, 1.3, 1.3)
    choice = replace(_choice("plant_meta"), plant_ratio=plant_ratio)
    rows = _feed(_fallback_monitor(), _lock_samples(_falling_heads(10), 1.4), 0.40, choice)
    inputs = rows[-1][1]
    assert inputs.high_ratio == inputs.rate_ratio == 1.4
    assert inputs.level_ratio == pytest.approx(max(_column_ratio(0.40), KAPPA * 1.4))


def test_fixed_locked_ratio_rule_gets_no_inputs() -> None:
    monitor = TwoPressureMonitor(
        HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S,
        settings=replace(TwoPressureSettings().with_r8_period(), locked_ratio_rule="fixed"),
        rod_weight_N=ROD_WEIGHT_N, stroke_max_m=STROKE_MAX_M)
    monitor.rod_state[FR] = RodSensorState.FALLBACK
    rows = _feed(monitor, _lock_samples(_falling_heads(10), 1.0), STROKE_LONG_M,
                 _choice("column_nominal"))
    assert all(inputs is None for _, inputs in rows)


# --- (c) a command inside the window ------------------------------------------------------------


def test_c_a_command_in_the_last_n_periods_keeps_the_level_rule() -> None:
    heads = _falling_heads(20)
    samples = _lock_samples(heads, 1.0)
    command_index = 5 + WINDOW_SAMPLES + 10
    _, head_Pa, rod_Pa = samples[command_index]
    samples[command_index] = (0.1 * V_MAX, head_Pa, rod_Pa)
    rows = _feed(_fallback_monitor(), samples, STROKE_LONG_M, _choice("column_nominal"))
    eligible = [inputs is not None for _, inputs in rows]
    first_eligible = 5 + RATE_INTERVALS
    assert not any(eligible[:first_eligible])
    assert all(eligible[first_eligible:command_index])
    # The new stretch opens one sample after the command; n samples later it qualifies again.
    reopened = command_index + 1
    assert not any(eligible[command_index:reopened + RATE_INTERVALS])
    assert all(eligible[reopened + RATE_INTERVALS:])


def test_c_a_healthy_leg_gets_no_inputs() -> None:
    samples = _lock_samples(_falling_heads(10), 1.0)
    rows = _feed(_monitor(), samples, STROKE_LONG_M, _choice("column_nominal"))
    assert all(inputs is None for _, inputs in rows)


# --- (d) above the anchor ----------------------------------------------------------------------


def test_d_above_the_anchor_the_fall_is_the_high_ratio_slope() -> None:
    rising = [LOCK_HEAD_PA + 2.0 * BAR * (i + 1) for i in range(5)]
    falling = [rising[-1] - HEAD_FALL_PER_PERIOD_PA * (i + 1) for i in range(5)]
    samples = _lock_samples(rising + falling, 0.0)
    rows = _feed(_fallback_monitor(), samples, STROKE_LONG_M, _choice("column_nominal"))
    inputs = rows[-1][1]
    assert inputs.depth_Pa == 0.0 and inputs.level_reserve_N == 0.0
    assert inputs.head_drop_Pa == pytest.approx(RATE_INTERVALS * HEAD_FALL_PER_PERIOD_PA)
    drop_N, gap_N = inputs.drop_N(RATE_INTERVALS, HORIZON_PERIODS)
    assert drop_N == pytest.approx(_gain(inputs.high_ratio) * inputs.head_drop_Pa, rel=1e-12)
    assert gap_N > 0.0


# --- (e) 302.6 level raise on a short L1 stroke -------------------------------------------------


L1_PLANT_RATIO_FRONT = 1.293
"""Spec 302.4: the L1-R plant meta ratio of the front legs."""


def _short_stroke_lower_and_truth(choice):
    """Front 0.30 m, start ``M`` equal to the true lock pressure, head -10 bar, L1-R law."""
    heads = [LOCK_HEAD_PA - 1.0 * BAR * (i + 1) for i in range(10)]
    samples = _lock_samples(heads, L1_PLANT_RATIO_FRONT)
    rows = _feed(_fallback_monitor(), samples, 0.30, choice)
    _, head_Pa, rod_Pa = samples[-1]
    return rows[-1][0], head_Pa * HEAD_AREA[FR] - rod_Pa * ANNULUS[FR]


def test_e_plant_meta_keeps_the_level_bound_on_a_short_stroke() -> None:
    assert _column_ratio(0.30) < L1_PLANT_RATIO_FRONT  # the 302.6 region (s' < 0.347 m)
    lower_off, truth = _short_stroke_lower_and_truth(None)
    assert lower_off - truth == pytest.approx(1.0e3, abs=0.1e3)  # 302.6: 1.0 kN optimistic
    lower_on, truth = _short_stroke_lower_and_truth(_choice("plant_meta"))
    assert lower_on <= truth
    # column_nominal (machine, L2b) leaves the level bound as it is
    lower_column, _ = _short_stroke_lower_and_truth(_choice("column_nominal"))
    assert lower_column == lower_off


# --- (a) no change without a fallback leg or with "level" -----------------------------------


@pytest.mark.parametrize("source", ["plant_meta", "column_nominal", "online"])
def test_a_readings_without_a_fallback_leg_are_unchanged(source) -> None:
    samples = _lock_samples(_falling_heads(15), 1.0)
    off = [lower for lower, _ in _feed(_monitor(), samples, 0.30, None)]
    on = [lower for lower, _ in _feed(_monitor(), samples, 0.30, _choice(source))]
    assert on == off


def test_a_column_nominal_leaves_the_fallback_level_unchanged() -> None:
    samples = _lock_samples(_falling_heads(15), 1.0)
    off = [lower for lower, _ in _feed(_fallback_monitor(), samples, STROKE_LONG_M, None)]
    on = [lower for lower, _ in
          _feed(_fallback_monitor(), samples, STROKE_LONG_M, _choice("column_nominal"))]
    assert on == off


# --- 302.5 PS2 numbers ---------------------------------------------------------------------------


def _ps2_inputs(rate_ratio: float, high_ratio: float) -> FallbackSlopeInputs:
    """Controller 127.8 s of 299.3: anchor 97.28 bar, head 89.25 bar, 3-period drop 4.73 bar."""
    return FallbackSlopeInputs(
        head_drop_Pa=4.73 * BAR, depth_Pa=(97.28 - 89.25) * BAR, level_ratio=14.56,
        high_ratio=high_ratio, rate_ratio=rate_ratio,
        head_area_m2=HEAD_AREA[FL], annulus_area_m2=ANNULUS[FL],
    )


PS2_HIGH_RATIO = 14.56 / KAPPA
"""``R_hi = R_ub / kappa`` (302.4: 13.24)."""
PS2_TOLERANCE_KN = 0.1
"""The 299.3 inputs are rounded to the table digits (head drop 4.73 bar, ``R_ub`` 14.56)."""


@pytest.mark.parametrize(("rate_ratio", "high_ratio", "predicted_kN"), [
    (1.296, 1.296, 45.06),             # L1 setting (plant ratio)
    (7.77, PS2_HIGH_RATIO, 20.70),     # machine setting R_nom + gap
    (0.0, PS2_HIGH_RATIO, 20.70),      # head only + gap: the same while the gap term decides
])
def test_ps2_reconstruction_of_spec_302_5(rate_ratio, high_ratio, predicted_kN) -> None:
    level_N = 56.50e3
    drop_N, _ = _ps2_inputs(rate_ratio, high_ratio).drop_N(RATE_INTERVALS, HORIZON_PERIODS)
    predicted_N = level_N - HORIZON_PERIODS / RATE_INTERVALS * drop_N
    assert predicted_N / 1e3 == pytest.approx(predicted_kN, abs=PS2_TOLERANCE_KN)
    assert predicted_N > F_MIN_N + 7.5e3  # no trigger (P5 16.91 kN)


# --- ④ online ratio --------------------------------------------------------------------------


def test_online_ratio_is_learned_healthy_and_kept_after_the_fallback() -> None:
    learned_ratio = 6.0
    monitor = _monitor()
    healthy = _lock_samples(_falling_heads(8), learned_ratio)
    _feed(monitor, healthy, STROKE_LONG_M, _choice("online"))
    assert monitor._online_ratios[FR] == pytest.approx(learned_ratio, rel=1e-9)
    monitor.rod_state[FR] = RodSensorState.FALLBACK
    later = _lock_samples(_falling_heads(10), 12.0)  # a fallback leg is never re-learned
    rows = _feed(monitor, later, STROKE_LONG_M, _choice("online"))
    assert monitor._online_ratios[FR] == pytest.approx(learned_ratio, rel=1e-9)
    assert rows[-1][1].rate_ratio == pytest.approx(learned_ratio, rel=1e-9)
    assert monitor.meta()["r5_online_ratio"][FR] == pytest.approx(learned_ratio)


def test_online_ratio_needs_the_stroke_within_5_mm() -> None:
    monitor = _monitor()
    samples = _lock_samples(_falling_heads(8), 6.0)
    window_end = 5 + WINDOW_SAMPLES
    strokes = [STROKE_LONG_M] * window_end + [STROKE_LONG_M + 0.006] * 8
    _feed(monitor, samples, strokes, _choice("online"))
    assert monitor._online_ratios[FR] is None


def test_online_without_a_ratio_uses_the_nominal_one_and_warns_once() -> None:
    monitor = _fallback_monitor()
    samples = _lock_samples(_falling_heads(10), 1.0)
    rows = _feed(monitor, samples, STROKE_LONG_M, _choice("online"))
    assert rows[-1][1].rate_ratio == pytest.approx(_nominal_ratio(STROKE_LONG_M), rel=1e-12)
    events = [name for name, _ in monitor.pop_events()]
    assert events.count("WARN_R5_ONLINE_RATIO_MISSING:FR") == 1


# --- ③ the controller's R-5 --------------------------------------------------------------------


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _config(**fast_relevel_changes) -> C2Config:
    """The preset on a synthetic bench (no CHECK, pressure judge, no calibration, no soil)."""
    base = C2Config(
        target=TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF),
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
    ).with_10hz_d1()
    fast_relevel = replace(base.r8.fast_relevel, **fast_relevel_changes)
    return replace(
        base,
        r8=replace(base.r8, imu_sample_period_s=None, fast_relevel=fast_relevel),
        zero_calibration=replace(base.zero_calibration, mode=ZeroCalibrationMode.OFF),
        soil=SoilResponseSettings(),
    )


P5_N = F_MIN_N + 7.5e3


def _falling_controller(geometry, config, fallback_inputs):
    """A controller whose FL lower estimate fell 60 -> 30 kN over 3 periods (100 kN/s,
    predicted -10 kN) and whose monitor gives ``fallback_inputs`` for FL."""
    controller = C2Controller(geometry, config)
    history = deque(maxlen=RATE_INTERVALS + 1)
    for level_N in (60e3, 50e3, 40e3, 30e3):
        loads = np.full(4, 80e3)
        loads[FL] = level_N
        history.append(loads)
    controller._state.load_estimate_history = history
    controller._pressures.r5_fallback_inputs = lambda leg: fallback_inputs if leg == FL else None
    return controller


def _inputs_with_drop(drop_N: float) -> FallbackSlopeInputs:
    """Inputs whose ``D`` is ``drop_N`` (nominal term only: anchor depth large, no reserve)."""
    gain = _gain(1.0, FL)
    return FallbackSlopeInputs(drop_N / gain, 0.0, 1.0, 1.0, 1.0, HEAD_AREA[FL], ANNULUS[FL])


def _r5_names(controller) -> list[str]:
    return [event.name for event in controller.events]


def test_level_rule_ignores_the_fallback_inputs(geometry) -> None:
    controller = _falling_controller(
        geometry, _config(fallback_slope="level"), _inputs_with_drop(1e3))
    assert controller._leg_falling_below(P5_N, 10.0, None) == FL
    assert _r5_names(controller) == ["relevel_predicted:FL"]


def test_nominal_gap_slow_fall_neither_triggers_nor_reports(geometry) -> None:
    controller = _falling_controller(geometry, _config(), _inputs_with_drop(6e3))  # 20 kN/s
    assert controller._leg_falling_below(P5_N, 10.0, None) is None
    assert _r5_names(controller) == []


def test_nominal_gap_fast_fall_above_p5_reports_without_trigger(geometry) -> None:
    controller = _falling_controller(geometry, _config(), _inputs_with_drop(9e3))  # 30 kN/s
    assert controller._leg_falling_below(P5_N, 10.0, None) is None  # 30 - 12 = 18 > 16.91
    assert _r5_names(controller) == ["INFO_R5_FALLBACK_SLOPE:FL:9.00:0.00"]


def test_nominal_gap_fast_fall_below_p5_triggers(geometry) -> None:
    controller = _falling_controller(geometry, _config(), _inputs_with_drop(12e3))
    assert controller._leg_falling_below(P5_N, 10.0, None) == FL  # 30 - 16 = 14 < 16.91
    assert _r5_names(controller) == ["INFO_R5_FALLBACK_SLOPE:FL:12.00:0.00",
                                     "relevel_predicted:FL"]


def test_nominal_gap_without_inputs_is_the_level_rule(geometry) -> None:
    controller = _falling_controller(geometry, _config(), None)
    assert controller._leg_falling_below(P5_N, 10.0, None) == FL
    assert _r5_names(controller) == ["relevel_predicted:FL"]


def test_probed_leg_is_neither_watched_nor_reported(geometry) -> None:
    controller = _falling_controller(geometry, _config(), _inputs_with_drop(12e3))
    assert controller._leg_falling_below(P5_N, 10.0, FL) is None
    assert _r5_names(controller) == []


# --- (a) closed bench: no fallback leg -> bit for bit ----------------------------------------


STEADY_LOAD_N = 80e3
ROD_PRESSURE_PA = 5.0 * BAR


def _bench_outputs(geometry, config, steps: int = 200):
    """Touch, level and READY on synthetic two-pressure readings, then RR unloads at 70 kN/s:
    the outputs and the event names."""
    controller = C2Controller(geometry, config)
    strokes = geometry.operating_extension_m(0.05)
    outputs = []
    forces = np.full(4, STEADY_LOAD_N)
    for k in range(steps):
        if k > 100:
            forces[3] = max(forces[3] - 7e3, 0.0)
        head = (forces + ROD_PRESSURE_PA * geometry.annulus_area_m2) / geometry.head_area_m2
        measurement = Measurements(
            t_s=round((k + 1) * PERIOD_S, 10),
            specific_force_m_s2=np.array([0.0, 0.0, 9.80665]),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head,
            rod_pressure_Pa=np.full(4, ROD_PRESSURE_PA),
            stroke_m=strokes,
            stroke_corrected_m=strokes,
        )
        outputs.append(np.array(controller.update(measurement).leg_speed_m_s))
    return np.array(outputs), [event.name for event in controller.events], controller


def test_a_bench_without_fallback_is_bit_identical(geometry) -> None:
    on, on_events, controller = _bench_outputs(geometry, _config())
    off, off_events, _ = _bench_outputs(geometry, _config(fallback_slope="level"))
    assert controller.phase is not C2Phase.TOUCH  # the bench got past the touchdown
    assert "relevel_predicted:RR" in on_events
    np.testing.assert_array_equal(on, off)
    assert on_events == off_events


# --- ① settings and meta --------------------------------------------------------------------


def test_preset_is_the_operating_default_of_u_s8_61() -> None:
    fast_relevel = R8_D1_SETTINGS.fast_relevel
    assert fast_relevel.fallback_slope is FallbackSlope.NOMINAL_GAP
    assert fast_relevel.fallback_ratio_source is FallbackRatioSource.COLUMN_NOMINAL
    assert FastRelevelSettings().fallback_slope is FallbackSlope.LEVEL


def test_l1_runs_switch_to_plant_meta() -> None:
    config = C2Config().with_10hz_d1().with_fallback_ratio_source(
        "plant_meta", (1.293, 1.293, 1.228, 1.228))
    fast_relevel = config.r8.fast_relevel
    assert fast_relevel.fallback_ratio_source is FallbackRatioSource.PLANT_META
    assert fast_relevel.fallback_plant_ratio == (1.293, 1.293, 1.228, 1.228)
    with pytest.raises(ValueError):
        C2Config().with_fallback_ratio_source("plant_meta")  # R-5 off


@pytest.mark.parametrize("changes", [
    {"fallback_slope": "nominal"},
    {"fallback_ratio_source": "plant"},
    {"fallback_nominal_head_dead_m": 0.0},
    {"fallback_nominal_rod_dead_m": math.nan},
    {"fallback_plant_ratio": (1.3, 1.3, 1.2)},
    {"fallback_plant_ratio": (1.3, 1.3, 1.2, -1.0)},
])
def test_invalid_fallback_settings_are_rejected(changes) -> None:
    with pytest.raises(ValueError):
        FastRelevelSettings(**changes)


def test_meta_records_the_fallback_settings(geometry) -> None:
    meta = C2Controller(geometry, C2Config().with_10hz_d1()).meta()
    fast_relevel = meta["r8"]["fast_relevel"]
    assert fast_relevel["fallback_slope"] == "nominal_gap"
    assert fast_relevel["fallback_ratio_source"] == "column_nominal"
    assert type(fast_relevel["fallback_slope"]) is str
    assert fast_relevel["fallback_nominal_head_dead_m"] == 0.05


def test_controller_pickled_before_p_s8_22_reads_level(geometry) -> None:
    controller = C2Controller(geometry, _config())
    measurement = Measurements(
        t_s=0.1, specific_force_m_s2=np.array([0.0, 0.0, 9.80665]),
        angular_rate_rad_s=np.zeros(3), head_pressure_Pa=np.full(4, 60 * BAR),
        rod_pressure_Pa=np.full(4, ROD_PRESSURE_PA),
        stroke_m=np.full(4, 0.3), stroke_corrected_m=np.full(4, 0.3),
    )
    controller.update(measurement)
    copied = pickle.loads(pickle.dumps(controller))
    for key in ("fallback_slope", "fallback_ratio_source", "fallback_nominal_head_dead_m",
                "fallback_nominal_rod_dead_m", "fallback_plant_ratio"):
        copied.config.r8.fast_relevel.__dict__.pop(key)
    for key in ("_r5_ratio_choice", "_r5_inputs", "_online_ratios"):
        copied._pressures.__dict__.pop(key)
    for stretch in copied._pressures._lock_stretches:
        stretch.__dict__.pop("ratio_stroke_m")
        stretch.__dict__.pop("online_reference")
    restored = pickle.loads(pickle.dumps(copied))
    assert restored.config.r8.fast_relevel.fallback_slope is FallbackSlope.LEVEL
    assert restored._r5_fallback_ratio_choice() is None
    restored.update(replace(measurement, t_s=0.2))
    assert restored._pressures.r5_fallback_inputs(FL) is None
