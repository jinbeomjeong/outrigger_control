"""C2 revision R5 (``s6_control_spec.md`` revision 7, 42.1): B1', GE1' gate / reference, H5a.

Synthetic readings as in ``test_c2.py`` / ``test_c2_target.py``: constant leg loads (or loads
that follow the commanded REANCHOR travel), the crawler-free operating strokes, an
accelerometer that reads a fixed tilt and a gyro signal the test chooses. The closed-loop H5a
checks on the reduced plant are in ``test_c2_r5_closed_loop.py``; the R4.1 bit-for-bit replays
and the 32.1 false-flag regression are in ``test_c2.py``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    ContactJudge,
    ProbeSettings,
    TargetSettings,
)
from outrigger_sim.control.ground_contact import ProbeResult
from outrigger_sim.control.standstill import (
    GyroBiasOutcome,
    StandstillGate,
    StandstillGateSettings,
    deg_per_hour,
    gyro_bias_window_s,
    window_statistics,
)
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.sensors.imu import ImuGradeName, imu_config_for_grade
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02
LEG_LOAD_N = 80e3
TIME_LIMIT_S = 120.0
NORMAL_GRADE_NOISE_RAD_S = math.radians(0.025)
"""Spec 38: normal grade, ARW 0.30 deg/sqrt(h) -> 0.025 deg/s per 20 ms sample."""
BIAS_TARGET_RAD_S = deg_per_hour(4.0)
GRADE_BIAS_RAD_S = deg_per_hour(20.0)
ROCKING_FREQUENCY_HZ = 1.3
ROCKING_RMS_RAD_S = math.radians(0.137)
"""Spec 32.2: nose-down 3.5 deg CHECK window of the reduced plant."""
SLOW_TILT_RAD_S = math.radians(0.05)
RR = LEG_ORDER.index("RR")
LIFTED_LEG_LOAD_N = -6.8e3
"""Spec 21.2: midpoint load estimate of a lifted leg (about -W_rod)."""
FREE_AIR_S = 5.0
"""Combined judge: the first 5 s are the free-air readings of the touchdown detection."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _specific_force(roll_rad: float, pitch_rad: float) -> np.ndarray:
    up_in_body = [
        -math.sin(pitch_rad),
        math.sin(roll_rad) * math.cos(pitch_rad),
        math.cos(roll_rad) * math.cos(pitch_rad),
    ]
    return GRAVITY_M_S2 * np.array(up_in_body)


def _operating_strokes(geometry: C2Geometry) -> np.ndarray:
    return geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05


GyroSignal = Callable[[float], tuple[float, float]]
LoadSignal = Callable[["_Bench"], np.ndarray]


def _still_gyro(_: float) -> tuple[float, float]:
    return (0.0, 0.0)


@dataclass
class _Bench:
    """Feeds readings to a controller; gyro and loads are functions the test chooses."""

    controller: C2Controller
    geometry: C2Geometry
    gyro: GyroSignal = _still_gyro
    loads: LoadSignal | None = None
    tilt_rad: tuple[float, float] = (0.0, 0.0)
    t_s: float = 0.0
    commands: list[np.ndarray] = field(default_factory=list)

    def step(self) -> np.ndarray:
        self.t_s += PERIOD_S
        strokes = _operating_strokes(self.geometry)
        forces = np.full(4, LEG_LOAD_N) if self.loads is None else self.loads(self)
        roll_rate, pitch_rate = self.gyro(self.t_s)
        measurements = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=_specific_force(*self.tilt_rad),
            angular_rate_rad_s=np.array([roll_rate, pitch_rate, 0.0]),
            head_pressure_Pa=forces / self.geometry.head_area_m2,
            stroke_m=strokes,
            stroke_corrected_m=strokes,
        )
        command = np.asarray(self.controller.update(measurements).leg_speed_m_s)
        self.commands.append(command)
        return command

    def run_while(self, phase: C2Phase) -> None:
        while self.controller.phase is phase and self.t_s < TIME_LIMIT_S:
            self.step()

    def run_until(self, is_done: Callable[[], bool]) -> None:
        while not is_done() and self.t_s < TIME_LIMIT_S:
            self.step()
        assert is_done()


def _pressure_bench(geometry: C2Geometry, gyro: GyroSignal, **target_fields) -> _Bench:
    config = C2Config(
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
        target=TargetSettings(**target_fields),
    ).with_r5_behaviour()  # R5 mechanism
    return _Bench(C2Controller(geometry, config), geometry, gyro=gyro)


def _white_noise(std_rad_s: float, seed: int, offset_rad_s: float = 0.0) -> GyroSignal:
    rng = np.random.default_rng(seed)

    def gyro(_: float) -> tuple[float, float]:
        roll, pitch = rng.normal(0.0, std_rad_s, 2) + offset_rad_s
        return float(roll), float(pitch)

    return gyro


def _rocking(noise: GyroSignal) -> GyroSignal:
    amplitude = ROCKING_RMS_RAD_S * math.sqrt(2.0)

    def gyro(t_s: float) -> tuple[float, float]:
        roll, pitch = noise(t_s)
        return roll, pitch + amplitude * math.sin(2.0 * math.pi * ROCKING_FREQUENCY_HZ * t_s)

    return gyro


# --- B1': CHECK gyro bias (spec 39, 42.1) -------------------------------------------------


def test_bias_window_follows_the_grade_noise() -> None:
    """T_b = clamp(T (sigma / 4 deg/h)^2, 2 s, 10 s): ideal 2 s, good 2.5 s, normal 10 s."""
    windows = {}
    for grade in (ImuGradeName.IDEAL, ImuGradeName.GOOD_ZEROED, ImuGradeName.NORMAL_ZEROED):
        noise = imu_config_for_grade(grade, sample_period_s=PERIOD_S).gyro_noise_std_rad_s
        windows[grade] = gyro_bias_window_s(noise, BIAS_TARGET_RAD_S, PERIOD_S, 2.0, 10.0)
    assert windows[ImuGradeName.IDEAL] == 2.0
    assert windows[ImuGradeName.GOOD_ZEROED] == pytest.approx(2.5, abs=0.05)
    assert windows[ImuGradeName.NORMAL_ZEROED] == 10.0
    normal = imu_config_for_grade(ImuGradeName.NORMAL_ZEROED, sample_period_s=PERIOD_S)
    assert normal.gyro_noise_std_rad_s == pytest.approx(NORMAL_GRADE_NOISE_RAD_S, rel=1e-6)


def test_normal_grade_bias_is_averaged_over_ten_seconds(geometry) -> None:
    """42.1 B1' (1): sigma 0.025 deg/s + bias 20 deg/h, no motion -> 10 s, error <= 12 deg/h."""
    gyro = _white_noise(NORMAL_GRADE_NOISE_RAD_S, seed=12345, offset_rad_s=GRADE_BIAS_RAD_S)
    bench = _pressure_bench(geometry, gyro, gyro_noise_std_rad_s=NORMAL_GRADE_NOISE_RAD_S)
    bench.run_while(C2Phase.CHECK)
    estimate = bench.controller.gyro_bias_estimate
    assert estimate.outcome is GyroBiasOutcome.ACCEPTED
    assert estimate.window_s == 10.0
    assert estimate.check_duration_s == pytest.approx(10.0, abs=1e-9)
    error = np.subtract(bench.controller.gyro_bias_rad_s, GRADE_BIAS_RAD_S)
    assert np.max(np.abs(error)) <= 3.0 * BIAS_TARGET_RAD_S
    assert bench.controller.phase is C2Phase.TOUCH
    assert len(bench.commands) == round(10.0 / PERIOD_S) + 1
    # R5-B: the 10 s window is judged against the cap 0.02 deg/s, recorded in the result.
    result = bench.controller.meta()["target"]["gyro_bias"]["result"]
    assert result["motion_limit_rad_s"] == pytest.approx(math.radians(0.02), rel=1e-12)
    assert result["window_s"] == 10.0
    assert max(result["motion_rms_rad_s"]) <= result["motion_limit_rad_s"]


def test_rocking_through_the_whole_check_leaves_the_bias_unremoved(geometry) -> None:
    """42.1 B1' (2): same noise + 1.3 Hz 0.137 deg/s rocking -> not quiet in 10 s -> None."""
    noise = _white_noise(NORMAL_GRADE_NOISE_RAD_S, seed=12345, offset_rad_s=GRADE_BIAS_RAD_S)
    bench = _pressure_bench(
        geometry, _rocking(noise), gyro_noise_std_rad_s=NORMAL_GRADE_NOISE_RAD_S
    )
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    estimate = controller.gyro_bias_estimate
    assert estimate.outcome is GyroBiasOutcome.SKIPPED_MOTION
    assert estimate.check_duration_s == pytest.approx(10.0, abs=1e-9)
    assert controller.gyro_bias_rad_s is None
    assert [event.name for event in controller.events] == ["WARN_GYRO_BIAS_SKIPPED"]
    meta = controller.meta()["target"]["gyro_bias"]
    assert meta["result"]["is_accepted"] is False
    assert meta["result"]["motion_rms_rad_s"][1] > math.radians(0.1)


def test_ideal_grade_takes_two_seconds_and_the_r41_value(geometry) -> None:
    """42.1 B1' (3): ideal grade, still -> 2 s and the R4.1 mean bit for bit."""
    bias = (deg_per_hour(7.0), deg_per_hour(-3.0))
    r5 = _pressure_bench(geometry, lambda _: bias)
    r5.run_while(C2Phase.CHECK)
    legacy_config = r5.controller.config.with_r41_behaviour()
    r41 = _Bench(C2Controller(geometry, legacy_config), geometry, gyro=lambda _: bias)
    r41.run_while(C2Phase.CHECK)
    assert r5.controller.gyro_bias_estimate.window_s == 2.0
    assert r5.controller.gyro_bias_estimate.check_duration_s == pytest.approx(2.0, abs=1e-9)
    assert r5.controller.gyro_bias_rad_s == r41.controller.gyro_bias_rad_s
    assert r5.controller.gyro_bias_rad_s == pytest.approx(bias, rel=1e-12)


def test_r41_settings_keep_the_two_second_mean_of_a_moving_check(geometry) -> None:
    """42.1 B1' (4): the R4.1 settings neither extend nor reject; mean of every CHECK sample."""
    rates: list[tuple[float, float]] = []
    rocking = _rocking(_white_noise(0.0, seed=1))

    def recorded(t_s: float) -> tuple[float, float]:
        rates.append(rocking(t_s))
        return rates[-1]

    config = C2Config(contact=ContactJudge.PRESSURE, output_ramp_time_s=None).with_r41_behaviour()
    bench = _Bench(C2Controller(geometry, config), geometry, gyro=recorded)
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.gyro_bias_estimate.outcome is GyroBiasOutcome.ACCEPTED
    assert len(rates) == round(2.0 / PERIOD_S) + 1
    roll, pitch = np.mean(np.array(rates), axis=0)
    assert controller.gyro_bias_rad_s == (float(roll), float(pitch))


def test_an_implausible_bias_is_dropped(geometry) -> None:
    """32.2: a 100 deg/h estimate (> 60 deg/h) is not removed; WARN_GYRO_BIAS_IMPLAUSIBLE."""
    bench = _pressure_bench(geometry, lambda _: (deg_per_hour(100.0), 0.0))
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.gyro_bias_estimate.outcome is GyroBiasOutcome.REJECTED_IMPLAUSIBLE
    assert controller.gyro_bias_estimate.estimate_rad_s[0] == pytest.approx(deg_per_hour(100.0))
    assert controller.gyro_bias_rad_s is None
    assert [event.name for event in controller.events] == ["WARN_GYRO_BIAS_IMPLAUSIBLE"]


def test_check_ends_once_the_rocking_has_decayed(geometry) -> None:
    """32.2: CHECK goes on past 2 s while the 2 s window moves, and ends when it is quiet."""
    quiet_from_s = 4.0

    def decaying(t_s: float) -> tuple[float, float]:
        if t_s >= quiet_from_s:
            return (0.0, 0.0)
        return (0.0, ROCKING_RMS_RAD_S * math.sin(2.0 * math.pi * ROCKING_FREQUENCY_HZ * t_s))

    bench = _pressure_bench(geometry, decaying)
    bench.run_while(C2Phase.CHECK)
    estimate = bench.controller.gyro_bias_estimate
    assert estimate.outcome is GyroBiasOutcome.ACCEPTED
    # The 2 s window (both ends included) must start at or after 4.0 s.
    assert estimate.check_duration_s == pytest.approx(quiet_from_s + 2.0 - PERIOD_S, abs=1e-9)
    assert bench.controller.gyro_bias_rad_s == (0.0, 0.0)


@pytest.mark.parametrize(
    ("window_s", "limit_deg_s"), [(2.0, 0.01), (2.5, 0.01 * math.sqrt(1.25)), (10.0, 0.02)]
)
def test_motion_limit_follows_the_window(window_s, limit_deg_s) -> None:
    """R5-B (spec 44.2): omega_th(T_b) = min(0.01 sqrt(T_b / 2), 0.02) deg/s."""
    limit = TargetSettings().gyro_bias_motion_limit_rad_s(window_s)
    assert limit == pytest.approx(math.radians(limit_deg_s), rel=1e-12)
    assert (
        TargetSettings(gyro_bias_max_rate_rms_rad_s=None).gyro_bias_motion_limit_rad_s(2.0) is None
    )


B1_TRIALS = 2000
B1_WINDOW_S = 10.0
B1_SKIP_RATE_MAX = 0.001
B1_SKIP_RATE_NOISY_MAX = 0.01
NOISE_ABOVE_SPEC = 1.10


def _still_check_skip_rate(actual_noise_rad_s: float, seed: int) -> float:
    """Share of still 10 s CHECK windows (normal grade setting) whose noise-corrected RMS is
    above omega_th(10 s): the B1' statistics of the controller on white noise only."""
    settings = TargetSettings(gyro_noise_std_rad_s=NORMAL_GRADE_NOISE_RAD_S)
    window_s = settings.gyro_bias_window_s(PERIOD_S)
    assert window_s == B1_WINDOW_S
    limit = settings.gyro_bias_motion_limit_rad_s(window_s)
    sample_count = round(B1_WINDOW_S / PERIOD_S) + 1
    times = np.arange(sample_count) * PERIOD_S
    rng = np.random.default_rng(seed)
    skipped = 0
    for _ in range(B1_TRIALS):
        rates = rng.normal(GRADE_BIAS_RAD_S, actual_noise_rad_s, (sample_count, 2))
        statistics = window_statistics(
            times, rates, float(times[-1]), window_s, NORMAL_GRADE_NOISE_RAD_S
        )
        skipped += max(statistics.motion_rms_rad_s) > limit
    return skipped / B1_TRIALS


def test_a_still_check_is_rarely_skipped() -> None:
    """R5-B: still normal grade, 10 s window: SKIPPED <= 0.1 % (2000 trials)."""
    assert _still_check_skip_rate(NORMAL_GRADE_NOISE_RAD_S, seed=20261022) <= B1_SKIP_RATE_MAX


def test_a_still_check_with_noise_above_its_spec_is_rarely_skipped() -> None:
    """R5-B: actual noise 1.10 x the grade setting: SKIPPED <= 1 % (0.01 deg/s fixed: 92 %)."""
    noisy = NOISE_ABOVE_SPEC * NORMAL_GRADE_NOISE_RAD_S
    assert _still_check_skip_rate(noisy, seed=20261023) <= B1_SKIP_RATE_NOISY_MAX


# --- GE1'-c: standstill gate (spec 38) ----------------------------------------------------


def _gate_open_fraction(gyro: GyroSignal, duration_s: float, warm_up_s: float = 1.5) -> float:
    gate = StandstillGate(StandstillGateSettings(), NORMAL_GRADE_NOISE_RAD_S, PERIOD_S)
    states = []
    for k in range(round(duration_s / PERIOD_S)):
        t_s = (k + 1) * PERIOD_S
        is_open = gate.update(
            t_s, gyro(t_s), zero_command_duration_s=math.inf, is_phase_allowed=True
        )
        if t_s > warm_up_s:
            states.append(is_open)
    return float(np.mean(states))


GATE_OPEN_FRACTION_MIN = 0.90
"""Spec 42.1 GE1'-c / 45.1 R5-G: lowest open fraction over ten seeds (1.0 s RMS window)."""
GATE_SEEDS = range(10)
GATE_RECORD_S = 120.0
ROCKING_GATE_RMS_RAD_S = math.radians(0.05)
"""Spec 45.1 R5-G: 1.3 Hz rocking of RMS 0.05 deg/s must close the gate within 0.3 s."""
GATE_CLOSE_DELAY_MAX_S = 0.3


def test_gate_opens_on_a_still_normal_grade_gyro() -> None:
    """R5-G: sigma 0.025 deg/s white noise at standstill, 10 seeds x 120 s -> open >= 90 %
    (the 0.5 s window of the first R5 draft gave 0.79-0.86)."""
    fractions = [
        _gate_open_fraction(_white_noise(NORMAL_GRADE_NOISE_RAD_S, seed=seed), GATE_RECORD_S)
        for seed in GATE_SEEDS
    ]
    assert min(fractions) >= GATE_OPEN_FRACTION_MIN


def test_gate_closes_soon_after_rocking_starts() -> None:
    """R5-G: open on a still record, then 1.3 Hz rocking of RMS 0.05 deg/s -> shut <= 0.3 s."""
    gate = StandstillGate(StandstillGateSettings(), 0.0, PERIOD_S)
    rocking_start_s = 3.0
    amplitude = ROCKING_GATE_RMS_RAD_S * math.sqrt(2.0)
    closed_at_s = None
    for k in range(round(6.0 / PERIOD_S)):
        t_s = (k + 1) * PERIOD_S
        rocking_s = t_s - rocking_start_s
        pitch_rate = amplitude * math.sin(2.0 * math.pi * ROCKING_FREQUENCY_HZ * rocking_s)
        is_open = gate.update(t_s, (0.0, pitch_rate if rocking_s > 0.0 else 0.0), math.inf, True)
        if rocking_s <= 0.0:
            assert is_open or t_s < 1.6  # windows full (1 s) + 0.5 s hold
        elif not is_open and closed_at_s is None:
            closed_at_s = t_s
    assert closed_at_s is not None
    assert closed_at_s - rocking_start_s <= GATE_CLOSE_DELAY_MAX_S


def test_gate_stays_shut_while_the_body_tilts_slowly() -> None:
    """42.1 GE1'-c: a steady 0.05 deg/s tilt rate (mean > 0.02 deg/s) keeps the gate shut."""
    noise = _white_noise(NORMAL_GRADE_NOISE_RAD_S, seed=12345, offset_rad_s=SLOW_TILT_RAD_S)
    assert _gate_open_fraction(noise, 30.0) == 0.0


def test_gate_needs_one_second_without_commands_and_an_allowed_phase() -> None:
    gate = StandstillGate(StandstillGateSettings(), 0.0, PERIOD_S)
    for k in range(100):  # rates still; fill the windows
        gate.update((k + 1) * PERIOD_S, (0.0, 0.0), 0.0, True)
    assert not gate.is_open  # commands were running until now
    assert not gate.update(2.02, (0.0, 0.0), 0.98, True)
    assert gate.update(2.04, (0.0, 0.0), 1.0, True)
    assert not gate.update(2.06, (0.0, 0.0), 1.02, False)  # LEVEL, CHECK, ...


# --- GE1'-a/b/d inside the controller -----------------------------------------------------


def _combined_bench(
    geometry: C2Geometry, probe: ProbeSettings | None = None, **config_fields
) -> _Bench:
    """Combined judge without CHECK: free air for 5 s, then 80 kN legs (touchdown)."""
    config = C2Config(
        target=TargetSettings(check_time_s=0.0),
        output_ramp_time_s=None,
        probe=ProbeSettings() if probe is None else probe,
        **config_fields,
    ).with_r5_behaviour()  # R5 mechanism (R6 has its own tests)
    bench = _Bench(C2Controller(geometry, config), geometry)
    bench.loads = lambda b: np.zeros(4) if b.t_s < FREE_AIR_S else np.full(4, LEG_LOAD_N)
    return bench


def _reference_sources(controller: C2Controller) -> list[str]:
    return [entry["source"] for entry in controller.meta()["support_geometry"]["reference_updates"]]


def test_geometry_is_invalid_while_the_legs_move_and_valid_a_second_after(geometry) -> None:
    """Spec 34 GE1': no validity (and no flag) while commanded; valid 1 s after the stop."""
    bench = _combined_bench(geometry)
    controller = bench.controller
    bench.run_until(lambda: bool(controller.probe_history))
    assert controller.phase is C2Phase.READY
    moving = [k for k, command in enumerate(bench.commands) if np.any(command != 0.0)]
    assert moving, "the probe should have moved the legs"
    stop_s = bench.t_s
    bench.run_until(lambda: controller.is_geometry_valid)
    assert bench.t_s - stop_s <= 1.0 + PERIOD_S + 1e-9
    assert controller.stationary_gate.zero_command_duration_s >= 1.0 - 1e-9
    assert not [event for event in controller.events if event.name.startswith("shadow_")]
    assert _reference_sources(controller) == ["touch", "ready"]


def test_reference_is_kept_while_a_leg_is_left_to_re_ground(geometry) -> None:
    """42.1 GE1'-b: READY with a light RR still to re-ground (rounds used up) keeps the TOUCH
    reference, however long the gate is open."""
    bench = _combined_bench(geometry, probe=ProbeSettings(max_rounds=1))
    controller = bench.controller

    def loads(b: _Bench) -> np.ndarray:
        # RR reads light only while probed; READY sees 80 kN so that no re-level starts.
        if b.t_s < FREE_AIR_S:
            return np.zeros(4)
        forces = np.full(4, LEG_LOAD_N)
        if controller.phase in (C2Phase.DONE, C2Phase.PROBE):
            forces[RR] = LIFTED_LEG_LOAD_N
        return forces

    bench.loads = loads
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    assert not controller._state.does_last_probe_accept_support  # internal GE1'-b flag
    for _ in range(round(3.0 / PERIOD_S)):
        bench.step()
    assert controller.is_geometry_valid
    assert _reference_sources(controller) == ["touch"]


def test_reference_is_kept_after_an_unresolved_probe(geometry) -> None:
    bench = _combined_bench(geometry)
    controller = bench.controller

    def loads(b: _Bench) -> np.ndarray:
        # 15 kN legs (all ambiguous) only while probed; READY sees 80 kN (no re-level).
        if b.t_s < FREE_AIR_S:
            return np.zeros(4)
        is_probing = controller.phase in (C2Phase.DONE, C2Phase.PROBE)
        return np.full(4, 15e3 if is_probing else LEG_LOAD_N)

    bench.loads = loads
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    assert "probe_unresolved" in [event.name for event in controller.events]
    for _ in range(round(3.0 / PERIOD_S)):
        bench.step()
    assert _reference_sources(controller) == ["touch"]


def test_pressure_judge_keeps_the_touch_reference_only(geometry) -> None:
    """R5-M (spec 44.4): no probe, so the TOUCH reference stays; meta says ``touch_only``."""
    bench = _pressure_bench(geometry, _still_gyro, check_time_s=0.0)
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    for _ in range(round(3.0 / PERIOD_S)):
        bench.step()
    assert controller.is_geometry_valid
    meta = controller.meta()["support_geometry"]
    assert meta["reference_source"] == "touch_only"
    assert [update["source"] for update in meta["reference_updates"]] == ["touch"]


def test_meta_exposes_the_r5_records(geometry) -> None:
    bench = _combined_bench(geometry)
    controller = bench.controller
    bench.run_until(lambda: controller.is_geometry_valid)
    meta = controller.meta()
    assert meta["revision"] == "R7"
    assert meta["is_geometry_valid"] is True
    assert meta["stationary_gate"]["is_open"] is True
    assert meta["support_geometry"]["settings"]["nonplanarity_threshold_m"] == 1.4e-3
    assert meta["support_geometry"]["reference_source"] == "ready"
    assert meta["stationary_gate"]["settings"]["rms_window_s"] == 1.0
    assert meta["target"]["gyro_bias"]["result"]["outcome"] == "no_check"
    sample = controller.support_geometry
    assert sample.is_geometry_valid
    assert len(sample.heights_delta_above_others_m) == 4


# --- H5a: probe before REANCHOR, measured band (spec 22.4) ----------------------------------

REANCHOR_LOAD_STIFFNESS_N_M = 1.6e7
"""Synthetic readings gain this much per metre of commanded travel during REANCHOR."""
SEAL_FRICTION_N = 12e3


@dataclass
class _TravelLoads:
    """Loads that follow the commanded REANCHOR travel; optional seal friction while probing
    (+F_s after an extension, -F_s after a retraction, as the reading of a real seal)."""

    controller: C2Controller
    seal_friction_N: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    friction_sign: np.ndarray = field(default_factory=lambda: np.zeros(4))
    low_leg_during_move: int | None = None

    def __call__(self, bench: _Bench) -> np.ndarray:
        if bench.t_s < FREE_AIR_S:
            return np.zeros(4)
        if bench.commands and self.controller.phase is C2Phase.REANCHOR:
            self.travel_m = self.travel_m + bench.commands[-1] * PERIOD_S
        if bench.commands and self.controller.phase is C2Phase.PROBE:
            moving = bench.commands[-1] != 0.0
            self.friction_sign[moving] = np.sign(bench.commands[-1][moving])
        forces = LEG_LOAD_N + REANCHOR_LOAD_STIFFNESS_N_M * self.travel_m
        forces = forces + self.seal_friction_N * self.friction_sign
        is_moving = np.any(self.travel_m != 0.0)
        if self.low_leg_during_move is not None and is_moving:
            forces[self.low_leg_during_move] = self.controller.geometry.F_min_N
        return forces


def _slope_bench(geometry: C2Geometry, *, after_probe: bool = True) -> tuple[_Bench, _TravelLoads]:
    """Combined judge on a crawler pitched 3 deg (REANCHOR applies), then level readings."""
    config = C2Config(
        target=TargetSettings(check_time_s=0.0), output_ramp_time_s=None
    ).with_r5_behaviour()  # R5 H5a mechanism
    if not after_probe:
        config = config.with_r41_behaviour()
    controller = C2Controller(geometry, config)
    bench = _Bench(controller, geometry, tilt_rad=(0.0, math.radians(3.0)))
    loads = _TravelLoads(controller)
    bench.loads = loads
    bench.run_until(lambda: controller.phase is C2Phase.LEVEL)
    bench.tilt_rad = (0.0, 0.0)
    return bench, loads


def _decision_names(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events if not event.name.startswith("shadow_")]


def test_reanchor_follows_the_probe_with_the_measured_band(geometry) -> None:
    """H5a: DONE -> PROBE -> REANCHOR (stops 45 / 30 / F_min + 11 kN x 2 with F_band 1 kN) ->
    LEVEL trim -> READY without a second probe."""
    bench, _ = _slope_bench(geometry)
    controller = bench.controller
    phases: list[C2Phase] = []

    def is_ready() -> bool:
        phases.append(controller.phase)
        return controller.phase is C2Phase.READY

    bench.run_until(is_ready)
    first_probe = phases.index(C2Phase.PROBE)
    assert phases.index(C2Phase.REANCHOR) > first_probe
    assert len(controller.probe_history) == 1
    assert controller.seal_band_N == 1e3
    stops = controller.meta()["reanchor"]["stop_force_N"]
    floor_N = geometry.F_min_N + 1e3 + 10e3
    np.testing.assert_allclose(stops, [45e3, 30e3, floor_N, floor_N], rtol=0, atol=1e-6)
    assert controller.reanchor_outcome == "completed"
    assert _decision_names(controller) == [
        "floor_estimate_touch",
        "reanchor_started",
        "reanchor_completed",
    ]


def test_r41_order_reanchors_before_the_probe(geometry) -> None:
    """``after_probe`` off (legacy): REANCHOR at the first DONE with F_band 13 kN, probe after."""
    bench, _ = _slope_bench(geometry, after_probe=False)
    controller = bench.controller
    phases: list[C2Phase] = []

    def is_ready() -> bool:
        phases.append(controller.phase)
        return controller.phase is C2Phase.READY

    bench.run_until(is_ready)
    assert phases.index(C2Phase.REANCHOR) < phases.index(C2Phase.PROBE)
    stops = controller.meta()["reanchor"]["stop_force_N"]
    assert stops[1] == pytest.approx(geometry.F_min_N + 13e3 + 10e3)
    assert controller.seal_band_N == 13e3  # widen only


def test_an_aborted_reanchor_probes_again_before_ready(geometry) -> None:
    bench, loads = _slope_bench(geometry)
    loads.low_leg_during_move = LEG_ORDER.index("FL")
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.READY)
    assert controller.reanchor_outcome == "aborted:other_low"
    assert len(controller.probe_history) == 2


def test_seal_friction_keeps_the_band_and_the_stop_floor_high(geometry) -> None:
    """22.4 H5a (c): F_s 12 kN -> F_band >= 13 kN -> stop floor >= F_min + 23 kN (H4 values)."""
    bench, loads = _slope_bench(geometry)
    loads.seal_friction_N = SEAL_FRICTION_N
    controller = bench.controller
    bench.run_until(lambda: controller.phase is C2Phase.REANCHOR)
    assert controller.seal_band_N >= 13e3
    stops = controller.meta()["reanchor"]["stop_force_N"]
    assert min(stops) >= geometry.F_min_N + 13e3 + 10e3 - 1e-6
    assert min(stops) == pytest.approx(geometry.F_min_N + controller.seal_band_N + 10e3, abs=1e-6)


def test_later_rounds_only_widen_the_measured_band(geometry) -> None:
    """D5 (spec 22.4): the first round sets the band; a later smaller estimate keeps it."""
    controller = C2Controller(geometry, C2Config(target=TargetSettings(check_time_s=0.0)))
    first = [_result(leg, 3e3) for leg in range(4)]
    controller._update_seal_band(tuple(first))  # the rule itself; rounds need a long bench
    assert controller.seal_band_N == 4e3
    controller._update_seal_band(tuple(_result(leg, 0.0) for leg in range(4)))
    assert controller.seal_band_N == 4e3
    controller._update_seal_band(tuple(_result(leg, 5e3) for leg in range(4)))
    assert controller.seal_band_N == 6e3


def _result(leg: int, seal_friction_N: float) -> ProbeResult:
    return ProbeResult(
        leg_index=leg,
        load_estimate_N=LEG_LOAD_N,
        seal_friction_estimate_N=seal_friction_N,
        incremental_stiffness_N_m=1e7,
        is_grounded=True,
    )


def test_invalid_r5_settings_are_rejected() -> None:
    with pytest.raises(ValueError, match="check_max_s"):
        TargetSettings(check_time_s=2.0, check_max_s=1.0)
    with pytest.raises(ValueError, match="gyro_noise_std_rad_s"):
        TargetSettings(gyro_noise_std_rad_s=-1.0)
    with pytest.raises(ValueError, match="gate windows"):
        StandstillGateSettings(rms_window_s=0.0)
