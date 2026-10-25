"""C2 soil response S-1 .. S-5 and the re-approach time limit (``s6_control_spec.md`` rev. 57
285, P-S9-1 .. P-S9-10; user decisions U-S9-C1 .. C6 of 2026-10-26).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (no CHECK, pressure judge):

* P-S9-1 settings, defaults, old pickles ("off"),
* P-S9-2 the load-sum plateau window: pinned slope, flat load sum, a retracting period, seeded
  reading noise,
* P-S9-3 soil mode: zone held, push floor, no DONE before the lift-off confirmation (LOC),
* P-S9-4 the corner bias by hand, the dead zone (commands bit for bit),
* P-S9-5 the 150 mm FAULT on a synthetic penetration,
* P-S9-6 lifetime, P-S9-7 events and meta, P-S9-8 presets, P-S9-10 the re-approach time limit.

P-S9-9 (bit-identical to the reference rules on the reduced closed loop) is
``04_scripts/03_control/s9/s9_project_check.py``.
"""

from __future__ import annotations

import json
import math
import pickle
from collections.abc import Callable
from dataclasses import dataclass, field, replace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    PERIOD_S,
    READY_SETTLE_PERIODS,
    RR,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    lifted_rr_forces,
    measurements,
    operating_strokes,
    ready_bench,
)

from outrigger_sim.control.c2 import (
    CRAWLER_XY_BOX_M,
    SOIL_EVENT_CLEARANCE_BIAS,
    SOIL_EVENT_LIFTOFF_CONFIRMED,
    SOIL_EVENT_LIFTOFF_UNCONFIRMED,
    SOIL_EVENT_MODE_START,
    SOIL_EVENT_WEIGHT_MISMATCH,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    LiftedReapproachSettings,
    SoilResponseSettings,
    TargetSettings,
    _PlateauSample,
    _RawTilt,
    _Reading,
    _RunState,
    _SoilState,
)
from outrigger_sim.control.target import AttitudeTarget
from outrigger_sim.params import load_params
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

PINNED_LOAD_RATE_N_M = 0.6e6
"""Spec 285 P-S9-2 test: load sum rising 0.6 kN per mm while the crawler carries weight."""
WINDOW_SPEED_FRACTION = 0.5
"""Mean leg speed of the direct window feeds (above the 0.15 ``v_max`` window floor)."""
NOISE_PER_LEG_N = 300.0
NOISE_TRIALS = 1000
NOISE_SAMPLES_PER_TRIAL = 30
NOISE_SEED = 20261026
HAND_PITCH_RAD = math.radians(0.5)
HAND_CORNER_CLEARANCE_M = (0.035, 0.030, 0.045, 0.040)
"""P-S9-4 hand case: unbiased corner clearances at ``t_P`` (corner order RR, RL, FR, FL)."""
HAND_TOLERANCE_M = 1e-12
PINNED_START_FRACTION = 0.9
"""Pinned sink bench: the load sum starts at 0.9 ``W_ref``, above the 0.85 plausibility
limit, so only the rising load sum keeps the LOC away."""
MAX_DURATION_S = 10.0
SINK_BENCH_LIMIT_S = 120.0


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def soil_config(**soil_changes) -> C2Config:
    return replace(bench_config(), soil=SoilResponseSettings(enable=True, **soil_changes))


def reference_weight_N(geometry: C2Geometry) -> float:
    return geometry.superstructure_mass_kg * STANDARD_GRAVITY_M_S2


def event_names(controller: C2Controller, prefix: str) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(prefix)]


# --- direct window feeds ---------------------------------------------------------------------


def level_controller(geometry: C2Geometry, **soil_changes) -> C2Controller:
    controller = C2Controller(geometry, soil_config(**soil_changes))
    controller._state.phase = C2Phase.LEVEL
    return controller


def window_reading(
    geometry: C2Geometry, t_s: float, mean_stroke_m: float, load_sum_N: float | np.ndarray
) -> _Reading:
    strokes = operating_strokes(geometry) + mean_stroke_m
    loads = np.broadcast_to(np.asarray(load_sum_N, dtype=float) / 4.0, (4,)).copy()
    return _Reading(
        t_s=t_s,
        cylinder_force_N=loads,
        rod_stroke_m=strokes,
        motor_stroke_m=strokes,
        cylinder_force_lowpass_N=loads,
        cylinder_force_lower_N=loads,
        cylinder_force_upper_N=loads,
        head_only_force_N=loads,
    )


def feed_window(
    controller: C2Controller,
    geometry: C2Geometry,
    load_sum_N: Callable[[float], float | np.ndarray],
    samples: int,
    *,
    retract_at: int | None = None,
) -> list[float]:
    """Feed ``samples`` periods at ``WINDOW_SPEED_FRACTION v_max``; returns the mean-stroke
    progress of each sample. ``retract_at``: that period's applied output retracts one leg."""
    speed = WINDOW_SPEED_FRACTION * geometry.max_speed_m_s
    progress = []
    for index in range(samples):
        applied = np.full(4, speed)
        if index == retract_at:
            applied[RR] = -speed
        controller._state.applied_output_m_s = applied
        mean_stroke = index * speed * PERIOD_S
        progress.append(mean_stroke)
        reading = window_reading(
            geometry, (index + 1) * PERIOD_S, mean_stroke, load_sum_N(mean_stroke)
        )
        controller._update_liftoff_window(reading)
        if controller._soil_state().is_liftoff_confirmed:
            break
    return progress


def test_pinned_load_sum_never_confirms(geometry) -> None:
    controller = level_controller(geometry)
    weight = reference_weight_N(geometry)
    feed_window(controller, geometry, lambda stroke: weight + PINNED_LOAD_RATE_N_M * stroke, 60)
    assert not controller._soil_state().is_liftoff_confirmed
    assert event_names(controller, SOIL_EVENT_LIFTOFF_CONFIRMED) == []


def test_flat_load_sum_confirms_within_the_window_length(geometry) -> None:
    controller = level_controller(geometry)
    weight = reference_weight_N(geometry)
    progress = feed_window(controller, geometry, lambda stroke: weight, 60)
    soil = controller._soil_state()
    assert soil.is_liftoff_confirmed
    window_m = controller.config.soil.plateau_window_m
    step_m = WINDOW_SPEED_FRACTION * geometry.max_speed_m_s * PERIOD_S
    assert window_m <= progress[-1] - progress[0] < window_m + step_m
    assert soil.plateau_start_s == pytest.approx(PERIOD_S)
    assert soil.weight_estimate_N == pytest.approx(weight)
    assert event_names(controller, SOIL_EVENT_LIFTOFF_CONFIRMED) == [SOIL_EVENT_LIFTOFF_CONFIRMED]


def test_flat_load_sum_below_the_plausibility_limit_does_not_confirm(geometry) -> None:
    controller = level_controller(geometry)
    low_weight = 0.84 * reference_weight_N(geometry)
    feed_window(controller, geometry, lambda stroke: low_weight, 60)
    assert not controller._soil_state().is_liftoff_confirmed


def test_one_retracting_period_clears_the_window(geometry) -> None:
    controller = level_controller(geometry)
    weight = reference_weight_N(geometry)
    retract_at = 3
    progress = feed_window(controller, geometry, lambda stroke: weight, 60, retract_at=retract_at)
    soil = controller._soil_state()
    assert soil.is_liftoff_confirmed
    # the window restarts on the sample after the retracting period
    assert soil.plateau_start_s == pytest.approx((retract_at + 2) * PERIOD_S)
    window_m = controller.config.soil.plateau_window_m
    assert progress[-1] - progress[retract_at + 1] >= window_m


def test_slow_mean_speed_is_not_a_window_period(geometry) -> None:
    controller = level_controller(geometry)
    controller._state.applied_output_m_s = np.full(4, 0.1 * geometry.max_speed_m_s)
    controller._update_liftoff_window(window_reading(geometry, 0.1, 0.0, 4 * STEADY_LOAD_N))
    assert len(controller._soil_state().window) == 0


def test_noisy_pinned_load_sum_gives_no_false_confirmation(geometry) -> None:
    """Spec 285 P-S9-2: sigma 0.3 kN per leg, fixed seed, 1000 trials of the pinned slope."""
    controller = level_controller(geometry)
    weight = reference_weight_N(geometry)
    rng = np.random.default_rng(NOISE_SEED)
    false_confirmations = 0
    for _ in range(NOISE_TRIALS):
        controller._state.soil = _SoilState()

        def noisy_pinned(stroke: float) -> np.ndarray:
            leg_loads = (weight + PINNED_LOAD_RATE_N_M * stroke) / 4.0
            return 4.0 * (leg_loads + rng.normal(0.0, NOISE_PER_LEG_N, 4))

        feed_window(controller, geometry, noisy_pinned, NOISE_SAMPLES_PER_TRIAL)
        false_confirmations += controller._soil_state().is_liftoff_confirmed
    assert false_confirmations == 0


def test_window_with_noise_reads_the_leg_sum(geometry) -> None:
    """The window takes the sum of the four leg readings (per-leg noise does not cancel)."""
    controller = level_controller(geometry)
    controller._state.applied_output_m_s = np.full(4, geometry.max_speed_m_s)
    loads = np.array([90e3, 95e3, 100e3, 105e3])
    reading = replace(window_reading(geometry, 0.1, 0.0, 0.0), cylinder_force_N=loads)
    controller._update_liftoff_window(reading)
    (sample,) = controller._soil_state().window
    assert sample.load_sum_N == pytest.approx(loads.sum())


# --- sink bench (strokes follow the commands) ---------------------------------------------------


@dataclass
class SinkBench:
    """10 Hz bench whose strokes integrate the applied commands; the four legs read a quarter
    of ``load_sum_N(mean stroke progress)`` each, the body stays level."""

    controller: C2Controller
    geometry: C2Geometry
    load_sum_N: Callable[[float], float]
    strokes_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    start_mean_m: float = 0.0
    t_s: float = 0.0
    outputs: list[np.ndarray] = field(default_factory=list)
    """Applied command of each period, with its sample time in ``times_s``."""
    times_s: list[float] = field(default_factory=list)
    phases: list[C2Phase] = field(default_factory=list)
    """Phase after each period's update."""

    @classmethod
    def touching(cls, geometry: C2Geometry, config: C2Config, load_sum_N) -> SinkBench:
        strokes = geometry.operating_extension_m(0.0).copy()
        return cls(
            C2Controller(geometry, config), geometry, load_sum_N, strokes, float(np.mean(strokes))
        )

    def step(self) -> np.ndarray:
        self.t_s = round(self.t_s + PERIOD_S, 10)
        progress = float(np.mean(self.strokes_m)) - self.start_mean_m
        forces = np.full(4, self.load_sum_N(progress) / 4.0)
        reading = measurements(self.t_s, self.geometry, forces, self.strokes_m.copy())
        command = np.array(self.controller.update(reading).leg_speed_m_s)
        self.strokes_m = self.strokes_m + command * PERIOD_S
        self.outputs.append(command)
        self.times_s.append(self.t_s)
        self.phases.append(self.controller.phase)
        return command

    def run_until(self, is_done: Callable[[], bool], limit_s: float = SINK_BENCH_LIMIT_S) -> None:
        while not is_done() and self.t_s < limit_s:
            self.step()


def test_flat_sink_bench_confirms_before_the_zone_release_and_reaches_ready(geometry) -> None:
    weight = reference_weight_N(geometry)
    bench = SinkBench.touching(geometry, soil_config(), lambda progress: weight)
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    assert controller.phase is C2Phase.READY
    soil = controller.meta()["soil"]
    assert soil["loc"] is True
    assert soil["soil_mode_t_s"] is None  # confirmed before the 20 mm release
    assert soil["clearance_at_loc_m"] < controller.config.thresholds.crawler_zone_release_m
    assert soil["bias_corner_m"] == [0.0] * 4
    (loc_time,) = event_times(controller, SOIL_EVENT_LIFTOFF_CONFIRMED)
    first_done = bench.times_s[bench.phases.index(C2Phase.DONE)]
    assert loc_time < first_done


def event_times(controller: C2Controller, name: str) -> list[float]:
    return [event.t_s for event in controller.events if event.name.startswith(name)]


def pinned_sink_bench(geometry: C2Geometry, **soil_changes) -> SinkBench:
    weight = reference_weight_N(geometry)
    return SinkBench.touching(
        geometry,
        soil_config(**soil_changes),
        lambda progress: PINNED_START_FRACTION * weight + PINNED_LOAD_RATE_N_M * progress,
    )


def test_pinned_sink_bench_holds_the_zone_pushes_and_faults_after_150_mm(geometry) -> None:
    """P-S9-3 / P-S9-5 on a synthetic penetration: no LOC, soil mode at the zone release, no
    leg ever retracts, no DONE, FAULT once the soil-mode push passes 0.15 m."""
    bench = pinned_sink_bench(geometry)
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.FAULT)
    assert controller.phase is C2Phase.FAULT
    for _ in range(2):  # the delayed (d = 1) last command, then the FAULT hold
        bench.step()
    assert event_names(controller, SOIL_EVENT_MODE_START) == [SOIL_EVENT_MODE_START]
    assert event_names(controller, SOIL_EVENT_LIFTOFF_UNCONFIRMED) == [
        SOIL_EVENT_LIFTOFF_UNCONFIRMED
    ]
    assert event_names(controller, SOIL_EVENT_LIFTOFF_CONFIRMED) == []
    assert C2Phase.DONE not in bench.phases
    soil = controller.meta()["soil"]
    max_push_m = controller.config.soil.max_push_m
    step_m = geometry.max_speed_m_s * PERIOD_S
    assert max_push_m < soil["push_m"] <= max_push_m + step_m
    outputs = np.array(bench.outputs)
    assert outputs.min() >= 0.0
    np.testing.assert_array_equal(outputs[-1], 0.0)  # FAULT holds every leg


def test_soil_mode_periods_push_every_leg(geometry) -> None:
    """From the period after the soil-mode start (d = 1) until the FAULT every output keeps
    each leg at >= 0.25 v_max (the heave alone would retract them above the 50 mm target)."""
    bench = pinned_sink_bench(geometry)
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.FAULT)
    (start_s,) = event_times(controller, SOIL_EVENT_MODE_START)
    (fault_s,) = event_times(controller, SOIL_EVENT_LIFTOFF_UNCONFIRMED)
    floor_m_s = controller.config.soil.push_speed_fraction * geometry.max_speed_m_s
    pushed = [
        output
        for t_s, output in zip(bench.times_s, bench.outputs, strict=True)
        if start_s + PERIOD_S - 1e-9 <= t_s <= fault_s + 1e-9
    ]
    assert len(pushed) > 10
    assert min(float(np.min(output)) for output in pushed) >= floor_m_s * (1.0 - 1e-12)
    heave_only = controller.command_components_m_s["heave"]
    assert float(np.max(heave_only)) < 0.0  # above the target: the heave asks to retract


def test_lift_without_retracting_floor_and_rescale(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    soil = controller._soil_state()
    soil.is_soil_mode = True
    max_speed = geometry.max_speed_m_s
    floor = controller.config.soil.push_speed_fraction * max_speed
    small = np.array([-0.2, 0.0, 0.1, 0.3]) * max_speed
    lifted = controller._lift_without_retracting(small)
    assert float(lifted.min()) == pytest.approx(floor, rel=1e-12)
    np.testing.assert_allclose(lifted - small, floor + 0.2 * max_speed, rtol=1e-12)
    large = np.array([-0.5, 0.2, 0.9, 1.0]) * max_speed
    scaled = controller._lift_without_retracting(large)
    shifted = large + floor + 0.5 * max_speed
    np.testing.assert_allclose(scaled, shifted * max_speed / shifted.max(), rtol=1e-12)
    soil.is_liftoff_confirmed = True  # after the LOC: the R1 rule (floor zero)
    np.testing.assert_allclose(controller._lift_without_retracting(small), small + 0.2 * max_speed)


def test_no_done_before_the_liftoff_confirmation(geometry) -> None:
    """Constant strokes: the window never spans 10 mm, so there is no LOC and no DONE, while
    the same bench without the soil response reaches READY."""
    without_soil = ready_bench(geometry, bench_config())
    assert without_soil.controller.phase is C2Phase.READY
    controller = C2Controller(geometry, soil_config())
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(round(without_soil.t_s / PERIOD_S) + 100):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    assert controller._state.complete_since_s is None


# --- corner bias, dead zone, lifetime -------------------------------------------------------


def hand_sample(t_s: float = 5.0) -> _PlateauSample:
    return _PlateauSample(
        t_s=t_s,
        mean_motor_stroke_m=0.5,
        load_sum_N=4 * STEADY_LOAD_N,
        corner_clearance_m=np.array(HAND_CORNER_CLEARANCE_M),
        raw_attitude_rad=(0.0, HAND_PITCH_RAD),
    )


def hand_bias_m() -> np.ndarray:
    (x_min, x_max), (y_min, y_max) = CRAWLER_XY_BOX_M
    corners_x = np.array([x_min, x_min, x_max, x_max])
    rise = -corners_x * HAND_PITCH_RAD  # y_k * 0 - x_k * d_theta
    return np.array(HAND_CORNER_CLEARANCE_M) - (rise - rise.min())


def test_corner_bias_matches_the_hand_calculation(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    raw_bias = controller._corner_bias_m(hand_sample())
    np.testing.assert_allclose(raw_bias, hand_bias_m(), rtol=0.0, atol=HAND_TOLERANCE_M)


def test_confirmation_applies_the_bias_to_every_clearance_path(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    sample = hand_sample()
    controller._confirm_liftoff(sample.t_s, [sample], reference_weight_N(geometry))
    expected = np.maximum(hand_bias_m(), 0.0)
    assert expected.max() > controller.config.soil.corner_bias_deadzone_m
    soil = controller._soil_state()
    np.testing.assert_allclose(soil.corner_bias_m, expected, atol=HAND_TOLERANCE_M)
    strokes = operating_strokes(geometry)
    np.testing.assert_allclose(
        controller._clearance_corners_m(strokes),
        geometry.clearance_corners_m(strokes) - expected,
        atol=HAND_TOLERANCE_M,
    )
    assert controller._clearance_estimate_m(strokes) == pytest.approx(
        float(np.min(geometry.clearance_corners_m(strokes) - expected)), abs=HAND_TOLERANCE_M
    )
    predicted = geometry.predicted_strokes_m(strokes, strokes, (0.0, 0.0), 0.05, expected)
    unbiased = geometry.predicted_strokes_m(strokes, strokes, (0.0, 0.0), 0.05)
    shift = float(np.min(geometry.clearance_corners_m(strokes))) - float(
        np.min(geometry.clearance_corners_m(strokes) - expected)
    )
    np.testing.assert_allclose(predicted - unbiased, shift, atol=HAND_TOLERANCE_M)
    (bias_event,) = event_names(controller, SOIL_EVENT_CLEARANCE_BIAS)
    by_corner = dict(item.split("=") for item in bias_event.split(":", 1)[1].split(","))
    assert list(by_corner) == ["FL", "FR", "RL", "RR"]
    assert float(by_corner["RR"]) == pytest.approx(expected[0] * 1e3, abs=0.05)
    assert float(by_corner["FL"]) == pytest.approx(expected[3] * 1e3, abs=0.05)


def test_bias_inside_the_dead_zone_is_dropped(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    sample = replace(
        hand_sample(), corner_clearance_m=np.full(4, 0.012), raw_attitude_rad=(0.0, 0.0)
    )
    controller._confirm_liftoff(sample.t_s, [sample], reference_weight_N(geometry))
    soil = controller._soil_state()
    np.testing.assert_allclose(soil.corner_bias_raw_m, 0.012)
    np.testing.assert_array_equal(soil.corner_bias_m, 0.0)
    assert controller._active_corner_bias_m() is None
    assert event_names(controller, SOIL_EVENT_CLEARANCE_BIAS) == []


def ready_bench_with_forced_liftoff(geometry: C2Geometry, config: C2Config) -> Bench:
    """``ready_bench`` with the LOC forced (dead-zone bias) right after TOUCH."""
    controller = C2Controller(geometry, config)
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    sample = replace(
        hand_sample(bench.t_s), corner_clearance_m=np.full(4, 0.005), raw_attitude_rad=(0.0, 0.0)
    )
    controller._confirm_liftoff(bench.t_s, [sample], reference_weight_N(geometry))
    bench.run_while(C2Phase.LEVEL)
    bench.run_while(C2Phase.DONE)
    assert controller.phase is C2Phase.READY
    for _ in range(READY_SETTLE_PERIODS):
        bench.step()
    return bench


def test_commands_are_bit_identical_once_confirmed_inside_the_dead_zone(geometry) -> None:
    reference = ready_bench(geometry, bench_config())
    soil_bench = ready_bench_with_forced_liftoff(geometry, soil_config())
    np.testing.assert_array_equal(np.array(soil_bench.outputs), np.array(reference.outputs))
    low_rr = lifted_rr_forces(geometry.F_min_N + 1e3)  # P5 / re-approach in READY
    for _ in range(20):
        reference.step(low_rr)
        soil_bench.step(low_rr)
    np.testing.assert_array_equal(np.array(soil_bench.outputs), np.array(reference.outputs))


def test_liftoff_survives_a_relevel_and_clears_at_a_new_touch(geometry) -> None:
    bench = ready_bench_with_forced_liftoff(geometry, soil_config())
    controller = bench.controller
    for _ in range(3):
        bench.step(lifted_rr_forces(geometry.F_min_N + 1e3))
        if controller.phase is C2Phase.LEVEL:
            break
    assert controller.phase is C2Phase.LEVEL  # READY -> LEVEL re-level
    confirmed = controller._soil_state()
    assert confirmed.is_liftoff_confirmed
    controller._restart_check(AttitudeTarget())  # IDLE -> CHECK -> TOUCH: a new lift cycle
    bench.step()
    # the legs are still latched as touched, so TOUCH hands over to LEVEL in the same period
    soil = controller._soil_state()
    assert soil is not confirmed
    assert not soil.is_liftoff_confirmed and not soil.is_soil_mode
    assert soil.corner_bias_raw_m is None and soil.liftoff_s is None


def test_settle_attitude_is_the_mean_tilt_of_the_first_touch_periods(geometry) -> None:
    """No CHECK: the first ``settle_tilt_samples`` TOUCH periods (legs still in the air here,
    zero readings) give the settle attitude; bench_config has no IMU-rate samples, so the
    filtered attitude stands in for the raw tilt."""
    controller = C2Controller(geometry, soil_config())
    bench = Bench(controller, geometry, operating_strokes(geometry))
    bench.tilt_rad = (math.radians(0.4), math.radians(-0.3))
    samples = controller.config.soil.settle_tilt_samples
    filtered = []
    for _ in range(samples + 5):
        bench.step(np.zeros(4))
        filtered.append((controller._state.roll_rad, controller._state.pitch_rad))
    assert controller.phase is C2Phase.TOUCH
    soil = controller._soil_state()
    # period 1 is CHECK (-> TOUCH inside its phase step), so TOUCH samples start at period 2
    assert soil.settle_tilts == filtered[1 : samples + 1]
    roll, pitch = np.mean(filtered[1 : samples + 1], axis=0)
    assert soil.settle_attitude_rad == (float(roll), float(pitch))


def test_settle_attitude_with_check_is_the_check_attitude(geometry) -> None:
    """P-S9-4 with CHECK: the settle attitude is ``(phi_c, theta_c)``, no TOUCH samples."""
    config = replace(soil_config(), target=TargetSettings(check_time_s=2.0))
    controller = C2Controller(geometry, config)
    controller._state.crawler_attitude_rad = (0.01, -0.02)
    controller._state.phase = C2Phase.TOUCH
    controller._record_settle_tilt()
    assert controller._soil_state().settle_tilts == []
    assert controller._settle_attitude_rad() == (0.01, -0.02)


def test_period_raw_attitude_is_the_mean_of_the_imu_rate_tilts(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    controller._state.period_raw_tilts = [
        _RawTilt(0.01, 0.010, -0.020),
        _RawTilt(0.02, 0.012, -0.024),
    ]
    roll, pitch = controller._period_raw_attitude_rad()
    assert (roll, pitch) == (pytest.approx(0.011, abs=1e-15), pytest.approx(-0.022, abs=1e-15))


# --- events, meta, settings, presets, old pickles -----------------------------------------------


def test_weight_mismatch_is_only_recorded(geometry) -> None:
    controller = C2Controller(geometry, soil_config())
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    sample = replace(
        hand_sample(), corner_clearance_m=np.full(4, 0.005), raw_attitude_rad=(0.0, 0.0)
    )
    heavy = 1.2 * reference_weight_N(geometry)
    controller._confirm_liftoff(sample.t_s, [sample], heavy)
    (warning,) = event_names(controller, SOIL_EVENT_WEIGHT_MISMATCH)
    assert warning == f"{SOIL_EVENT_WEIGHT_MISMATCH}:1.200"
    assert controller._soil_state().is_liftoff_confirmed


def test_meta_soil_block_is_json_serialisable(geometry) -> None:
    off = C2Controller(geometry, bench_config()).meta()["soil"]
    assert off == {"settings": SoilResponseSettings().to_meta()}
    controller = C2Controller(geometry, soil_config())
    keys = {
        "loc",
        "t_P_s",
        "t_loc_s",
        "W_hat_N",
        "W_ratio",
        "bias_corner_m",
        "bias_corner_raw_m",
        "settle_attitude_rad",
        "soil_mode_t_s",
        "push_m",
    }
    assert keys <= set(controller.meta()["soil"])
    json.dumps(controller.meta())
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    sample = hand_sample()
    controller._confirm_liftoff(sample.t_s, [sample], reference_weight_N(geometry))
    meta = json.loads(json.dumps(controller.meta()))["soil"]
    assert meta["loc"] is True and meta["t_P_s"] == sample.t_s
    assert meta["W_ratio"] == pytest.approx(1.0)
    assert meta["corner_order"] == ["RR", "RL", "FR", "FL"]


def test_settings_defaults_and_validation() -> None:
    settings = SoilResponseSettings()
    assert not settings.enable
    assert (settings.plateau_window_m, settings.plateau_mean_speed_fraction) == (0.010, 0.15)
    assert (settings.plateau_rise_max_N, settings.plausibility_fraction) == (2000.0, 0.85)
    assert (settings.push_speed_fraction, settings.corner_bias_deadzone_m) == (0.25, 0.020)
    assert (settings.max_push_m, settings.weight_record_range) == (0.15, (0.9, 1.15))
    assert settings.settle_tilt_samples == 10
    for bad in (
        {"plateau_window_m": 0.0},
        {"push_speed_fraction": 1.5},
        {"plateau_rise_max_N": -1.0},
        {"weight_record_range": (1.2, 1.1)},
        {"settle_tilt_samples": 0},
    ):
        with pytest.raises(ValueError):
            SoilResponseSettings(**bad)
    with pytest.raises(ValueError):
        LiftedReapproachSettings(max_duration_s=0.0)


def test_presets() -> None:
    base = C2Config()
    assert not base.soil.enable
    assert not base.r8.lifted_reapproach.max_duration_s
    r8 = base.with_10hz_d1()
    soil = base.with_soil_response()
    assert soil.soil.enable
    assert replace(soil, soil=r8.soil) == r8
    # U-S9-C1 / U-S9-C4 (2026-10-26): the R8 preset carries both
    assert r8.soil == SoilResponseSettings(enable=True)
    assert r8.r8.lifted_reapproach.max_duration_s == MAX_DURATION_S
    custom = C2Config(soil=SoilResponseSettings(plateau_rise_max_N=3000.0)).with_10hz_d1()
    assert custom.soil == SoilResponseSettings(enable=True, plateau_rise_max_N=3000.0)


def aged(controller: C2Controller) -> C2Controller:
    """``controller`` as unpickled from code without the soil response and P-S9-10 keys."""
    copied = pickle.loads(pickle.dumps(controller))
    copied.config.__dict__.pop("soil")
    copied.config.r8.lifted_reapproach.__dict__.pop("max_duration_s")
    copied._state.__dict__.pop("soil")
    return pickle.loads(pickle.dumps(copied))


def test_old_pickle_reads_off_and_behaves_as_before(geometry) -> None:
    reference = ready_bench(geometry, bench_config())
    restored = Bench(aged(reference.controller), geometry, reference.strokes_m.copy())
    restored.t_s = reference.t_s
    controller = restored.controller
    assert "soil" not in controller.config.__dict__
    assert controller.config.soil == SoilResponseSettings()
    assert controller.config.r8.lifted_reapproach.max_duration_s is None
    assert controller._state.soil is _RunState.soil is None
    low_rr = lifted_rr_forces(geometry.F_min_N + 1e3)
    for forces in (None, low_rr, low_rr, None, None):
        reference.step(forces)
        restored.step(forces)
    np.testing.assert_array_equal(np.array(reference.outputs[-5:]), np.array(restored.outputs))
    json.dumps(controller.meta())


# --- P-S9-10 re-approach time limit -------------------------------------------------------


def duration_config(max_duration_s: float | None) -> C2Config:
    config = bench_config()
    reapproach = replace(config.r8.lifted_reapproach, max_duration_s=max_duration_s)
    return replace(config, r8=replace(config.r8, lifted_reapproach=reapproach))


def reapproach_events(controller: C2Controller) -> list[tuple[float, str]]:
    return [
        (event.t_s, event.name)
        for event in controller.events
        if event.name.startswith(("leg_reapproach_", "WARN_LEG_REAPPROACH_"))
    ]


def test_reapproach_time_limit_ends_a_run_that_never_moves(geometry) -> None:
    """The bench strokes do not follow the commands, so RR never travels 40 mm: with the limit
    the run ends after 10 s (``no_contact``, guard path); without it, it is still active."""
    limited = ready_bench(geometry, duration_config(MAX_DURATION_S))
    unlimited = ready_bench(geometry, duration_config(None))
    lifted = lifted_rr_forces()
    for _ in range(round(1.5 * MAX_DURATION_S / PERIOD_S)):
        limited.step(lifted)
        unlimited.step(lifted)
    (start_s, start), (end_s, end) = reapproach_events(limited.controller)[:2]
    assert start == "leg_reapproach_start:RR"
    assert end == "WARN_LEG_REAPPROACH_NO_CONTACT:RR"
    assert end_s - start_s == pytest.approx(MAX_DURATION_S)
    (run,) = limited.controller.meta()["lifted_reapproach"][:1]
    assert run["outcome"] == "no_contact"
    assert not limited.controller._state.is_reapproach_armed[RR]
    assert [name for _, name in reapproach_events(unlimited.controller)] == [
        "leg_reapproach_start:RR"
    ]


def test_reapproach_time_limit_changes_nothing_before_it_is_reached(geometry) -> None:
    """Up to the period the limit ends the run, the commands with and without it are the same
    bits (``None`` = the behaviour before P-S9-10)."""
    limited = ready_bench(geometry, duration_config(MAX_DURATION_S))
    unlimited = ready_bench(geometry, duration_config(None))
    lifted = lifted_rr_forces()
    periods_before_end = round(MAX_DURATION_S / PERIOD_S)
    for _ in range(periods_before_end):
        limited.step(lifted)
        unlimited.step(lifted)
    np.testing.assert_array_equal(np.array(limited.outputs), np.array(unlimited.outputs))
    assert len(reapproach_events(limited.controller)) == 1  # still active
