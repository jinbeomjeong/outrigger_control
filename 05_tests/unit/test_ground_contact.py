"""Unit tests of the combined ground-contact judge and the probe (control/ground_contact.py).

The closed-loop checks on the reduced plant (lifted leg, attitude change of the probe) are in
``test_c2_closed_loop.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Geometry
from outrigger_sim.control.ground_contact import (
    LoadBand,
    ProbeProfile,
    ProbeReading,
    ProbeRound,
    ProbeSample,
    ProbeSettings,
    RegroundRule,
    StiffnessWindow,
    attitude_sensitivity_rad_m,
    classify_load,
    evaluate_probe,
    load_bounds_N,
    trapezoid_speeds,
)
from outrigger_sim.params import LEG_ORDER, load_params

PERIOD_S = 0.02
# The R2 / R3 rectangular probe (its timing quirks are tested below as the regression asks).
RECT = ProbeSettings(profile=ProbeProfile.RECT)
FL = LEG_ORDER.index("FL")
# control_candidates_comparison.md 5.4: a 2 mm probe of FL tilts roll by 0.024 deg.
FL_ROLL_DEG_PER_MM = 0.0118


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


# --- physics pieces ---------------------------------------------------------------------------


def test_attitude_sensitivity_is_the_pseudo_inverse_for_equal_pads(geometry) -> None:
    support = geometry.support_matrix
    sensitivity = attitude_sensitivity_rad_m(support, np.full(4, 2.1e7))
    np.testing.assert_allclose(sensitivity, np.linalg.pinv(support)[1:3].T, rtol=0, atol=1e-12)
    fl_roll_deg_per_mm = math.degrees(sensitivity[FL, 0]) * 1e-3
    assert fl_roll_deg_per_mm == pytest.approx(FL_ROLL_DEG_PER_MM, rel=0.05)
    np.testing.assert_allclose(geometry.attitude_sensitivity_rad_m, sensitivity, rtol=1e-12)


def test_attitude_sensitivity_balances_the_pad_forces(geometry) -> None:
    """Unequal pads: the rigid-body motion leaves no net pad force or moment."""
    support = geometry.support_matrix
    stiffness = np.array([1.5e7, 2.5e7, 2.0e7, 3.0e7])
    sensitivity = attitude_sensitivity_rad_m(support, stiffness)
    extension = np.zeros(4)
    extension[2] = 1e-3
    weighted = support.T @ np.diag(stiffness)
    rigid_body = np.linalg.solve(weighted @ support, weighted @ extension)
    pad_forces = stiffness * (extension - support @ rigid_body)
    np.testing.assert_allclose(support.T @ pad_forces, 0.0, rtol=0, atol=1e-6)
    np.testing.assert_allclose(sensitivity[2] * 1e-3, rigid_body[1:3], rtol=1e-12)


def test_friction_band_classifies_each_leg() -> None:
    F_min, band = 9.45e3, 13e3
    readings = np.array([30e3, 15e3, -1e3, -5e3])
    lower, upper = load_bounds_N(readings, band)
    np.testing.assert_array_equal(lower, readings - band)
    np.testing.assert_array_equal(upper, readings + band)
    # A lifted leg reads -W_rod; with a 13 kN band it is only 'ambiguous', not 'below'.
    assert classify_load(readings, band, F_min) == [
        LoadBand.ABOVE,
        LoadBand.AMBIGUOUS,
        LoadBand.AMBIGUOUS,
        LoadBand.BELOW,
    ]


# --- evaluate_probe ---------------------------------------------------------------------------

SENSITIVITY_N_M = 5e6
KINEMATIC_RAD_M = np.array([0.2, -0.1])
PROBE_TRAVEL_M = 2e-3


def _sample(
    *,
    force_rise_N: float,
    attitude_change_rad: tuple[float, float] | None,
    seal_friction_N: float = 0.0,
) -> ProbeSample:
    start_force = 70e3
    extended = start_force + force_rise_N + seal_friction_N
    retracted = start_force - seal_friction_N
    return ProbeSample(
        leg_index=FL,
        start_force_N=start_force,
        start_rod_stroke_m=0.6,
        start_motor_stroke_m=0.605,
        extended_force_N=extended,
        extended_rod_stroke_m=0.6 + PROBE_TRAVEL_M,
        extended_motor_stroke_m=0.605 + PROBE_TRAVEL_M,
        retracted_force_N=retracted,
        retracted_rod_stroke_m=0.6,
        attitude_before_rad=(0.0, 0.0),
        attitude_extended_rad=attitude_change_rad,
    )


def test_grounded_leg_shows_stiffness_and_attitude_response() -> None:
    response = tuple(KINEMATIC_RAD_M * PROBE_TRAVEL_M)
    sample = _sample(
        force_rise_N=SENSITIVITY_N_M * PROBE_TRAVEL_M,
        attitude_change_rad=response,
        seal_friction_N=4e3,
    )
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings())
    assert result.is_grounded and result.is_grounded_by_stiffness
    assert result.incremental_stiffness_N_m == pytest.approx(SENSITIVITY_N_M + 4e3 / 2e-3)
    assert result.attitude_response_ratio == pytest.approx(1.0, rel=1e-12)
    assert result.is_attitude_consistent is True
    # Midpoint of extend / retract minus S dx / 2 = start + S dx - S dx / 2 ... cancels F_s.
    assert result.load_estimate_N == pytest.approx(70e3, abs=1e-6)
    assert result.seal_friction_estimate_N == pytest.approx(4e3, abs=1e-6)


def test_lifted_leg_moves_freely_and_leaves_the_attitude_alone() -> None:
    sample = _sample(force_rise_N=0.0, attitude_change_rad=(0.0, 0.0))
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings())
    assert not result.is_grounded
    assert result.attitude_response_ratio == pytest.approx(0.0, abs=1e-12)
    assert result.is_attitude_consistent is True


@pytest.mark.parametrize("use_attitude", [False, True])
def test_attitude_evidence_decides_only_when_enabled(use_attitude) -> None:
    """Three legs carrying the machine: no force rise, but the body tilts (cues disagree)."""
    response = tuple(2.0 * KINEMATIC_RAD_M * PROBE_TRAVEL_M)
    sample = _sample(force_rise_N=0.0, attitude_change_rad=response)
    settings = ProbeSettings(use_combined_verdict=use_attitude)
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, settings)
    assert not result.is_grounded_by_stiffness
    assert result.is_attitude_consistent is False
    assert result.is_grounded is use_attitude


def test_combined_verdict_counts_a_surely_loaded_leg_that_could_not_move() -> None:
    """A leg at the 210 bar cut-off neither moves nor tilts the body; its band says loaded."""
    sample = replace(
        _sample(force_rise_N=0.0, attitude_change_rad=(0.0, 0.0)),
        extended_rod_stroke_m=0.6,
        extended_motor_stroke_m=0.605,
        start_load_band=LoadBand.ABOVE,
    )
    combined = ProbeSettings(use_combined_verdict=True)
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, combined)
    assert result.is_grounded and result.load_band is LoadBand.ABOVE
    assert not result.is_grounded_by_stiffness
    stiffness_only = ProbeSettings(use_combined_verdict=False)
    assert not evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, stiffness_only).is_grounded
    assert ProbeSettings().use_combined_verdict  # spec 10.1 P1: on by default


def test_a_lifted_leg_stays_lifted_with_the_attitude_evidence() -> None:
    sample = _sample(force_rise_N=0.0, attitude_change_rad=(0.0, 0.0))
    settings = ProbeSettings(use_combined_verdict=True)
    assert not evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, settings).is_grounded


def test_without_attitude_samples_the_stiffness_decides() -> None:
    sample = _sample(force_rise_N=SENSITIVITY_N_M * PROBE_TRAVEL_M, attitude_change_rad=None)
    settings = ProbeSettings(use_combined_verdict=True)
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, settings)
    assert result.is_grounded
    assert math.isnan(result.attitude_response_ratio)
    assert result.attitude_change_rad is None and result.is_attitude_consistent is None


# --- R4.1: attitude-cue quality gate (spec 21.3 Q1) and stiffness window (spec 29 K1) ---------

WINDOW_SAMPLES = 15  # 0.3 s at T = 0.02 s
WINDOW_SPACING_S = 1.0
# The three-leg teeter of spec 21 (1.25 Hz) at 0.01 deg against a 0.026 deg expected response.
TEETER_FREQUENCY_HZ = 1.25
TEETER_AMPLITUDE_RAD = math.radians(0.01)
NO_GATE = {"attitude_ripple_ratio": None, "attitude_drift_ratio": None}


def _window(
    start_t_s: float, offset_rad: float, sine_rad: float = 0.0, slope_rad_s: float = 0.0
) -> tuple[tuple[float, float], ...]:
    """Rate-integrated attitude samples along the unit ``J`` of the bench."""
    direction = KINEMATIC_RAD_M / np.linalg.norm(KINEMATIC_RAD_M)
    samples = []
    for k in range(WINDOW_SAMPLES):
        t_s = start_t_s + k * PERIOD_S
        along = offset_rad + slope_rad_s * t_s
        along += sine_rad * math.sin(2.0 * math.pi * TEETER_FREQUENCY_HZ * t_s)
        samples.append((float(direction[0] * along), float(direction[1] * along)))
    return tuple(samples)


def _windowed_sample(
    *, sine_rad: float = 0.0, slope_rad_s: float = 0.0, response_ratio: float = 1.0
) -> ProbeSample:
    """No force rise (stiffness says lifted); the attitude windows carry the response."""
    response = response_ratio * float(np.linalg.norm(KINEMATIC_RAD_M)) * PROBE_TRAVEL_M
    before = _window(0.0, 0.0, sine_rad, slope_rad_s)
    after = _window(WINDOW_SPACING_S, response, sine_rad, slope_rad_s)
    return replace(
        _sample(force_rise_N=0.0, attitude_change_rad=tuple(KINEMATIC_RAD_M * PROBE_TRAVEL_M)),
        attitude_window_before_rad=before,
        attitude_window_after_rad=after,
        window_spacing_s=WINDOW_SPACING_S,
        window_period_s=PERIOD_S,
    )


def test_r41_judge_defaults() -> None:
    settings = ProbeSettings()
    assert settings.attitude_ripple_ratio == 0.15
    assert settings.attitude_drift_ratio == 0.25
    assert settings.reground_rule is RegroundRule.LOAD_FIRST
    assert settings.stiffness_window is StiffnessWindow.SECOND_HALF


def test_a_rippled_attitude_cue_abstains() -> None:
    """Q1: a 0.01 deg teeter ripple must not count as the attitude response of a lifted leg."""
    sample = _windowed_sample(sine_rad=TEETER_AMPLITUDE_RAD)
    gated = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings())
    ungated = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings(**NO_GATE))
    assert gated.attitude_ripple_ratio > 0.15
    assert gated.is_attitude_rippled and not gated.is_grounded
    assert gated.is_attitude_consistent is None
    assert ungated.is_grounded and not ungated.is_attitude_rippled  # the R4 misjudgement


def test_a_drifting_attitude_cue_abstains() -> None:
    """Q1b: a trend of 0.3 x the expected response over the window spacing abstains."""
    expected = float(np.linalg.norm(KINEMATIC_RAD_M)) * PROBE_TRAVEL_M
    sample = _windowed_sample(slope_rad_s=0.3 * expected / WINDOW_SPACING_S)
    result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings())
    assert result.attitude_drift_ratio == pytest.approx(0.3, rel=1e-9)
    assert result.attitude_ripple_ratio == pytest.approx(0.0, abs=1e-9)
    assert result.is_attitude_rippled and not result.is_grounded


def test_quiet_windows_leave_the_attitude_verdict_unchanged() -> None:
    sample = _windowed_sample()
    gated = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings())
    ungated = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, ProbeSettings(**NO_GATE))
    assert gated.attitude_ripple_ratio == pytest.approx(0.0, abs=1e-9)
    assert gated.attitude_drift_ratio == pytest.approx(0.0, abs=1e-9)
    assert not gated.is_attitude_rippled
    assert gated.attitude_response_ratio == ungated.attitude_response_ratio
    assert gated.is_grounded == ungated.is_grounded is True


def _sample_with_midpoint(*, seal_friction_N: float, stiffness_N_m: float) -> ProbeSample:
    """First move of 2 mm; the seal friction turns over (2 F_s) within its first half."""
    start_force = 70e3
    mid_force = start_force + 2.0 * seal_friction_N + stiffness_N_m * PROBE_TRAVEL_M / 2.0
    extended_force = mid_force + stiffness_N_m * PROBE_TRAVEL_M / 2.0
    return replace(
        _sample(force_rise_N=0.0, attitude_change_rad=None),
        extended_force_N=extended_force,
        retracted_force_N=start_force,
        first_move_mid_force_N=mid_force,
        first_move_mid_rod_stroke_m=0.6 + PROBE_TRAVEL_M / 2.0,
    )


def test_second_half_stiffness_leaves_out_the_seal_friction_turnover() -> None:
    """K1: a lifted leg's 8 kN friction turnover reads as 4 MN/m over the whole move."""
    lifted = _sample_with_midpoint(seal_friction_N=4e3, stiffness_N_m=0.0)
    full = ProbeSettings(stiffness_window=StiffnessWindow.FULL, use_combined_verdict=False)
    second_half = ProbeSettings(use_combined_verdict=False)
    full_result = evaluate_probe(lifted, SENSITIVITY_N_M, KINEMATIC_RAD_M, full)
    half_result = evaluate_probe(lifted, SENSITIVITY_N_M, KINEMATIC_RAD_M, second_half)
    assert full_result.incremental_stiffness_N_m == pytest.approx(4e6, rel=1e-9)
    assert full_result.is_grounded_by_stiffness  # the misjudgement K1 removes
    assert half_result.incremental_stiffness_N_m == pytest.approx(0.0, abs=1e-6)
    assert not half_result.is_grounded_by_stiffness
    grounded = _sample_with_midpoint(seal_friction_N=4e3, stiffness_N_m=SENSITIVITY_N_M)
    grounded_result = evaluate_probe(grounded, SENSITIVITY_N_M, KINEMATIC_RAD_M, second_half)
    assert grounded_result.incremental_stiffness_N_m == pytest.approx(SENSITIVITY_N_M, rel=1e-9)
    assert grounded_result.is_grounded_by_stiffness


def test_without_a_midpoint_the_whole_move_is_used() -> None:
    sample = _sample(force_rise_N=SENSITIVITY_N_M * PROBE_TRAVEL_M, attitude_change_rad=None)
    full = ProbeSettings(stiffness_window=StiffnessWindow.FULL)
    for settings in (full, ProbeSettings()):
        result = evaluate_probe(sample, SENSITIVITY_N_M, KINEMATIC_RAD_M, settings)
        assert result.incremental_stiffness_N_m == pytest.approx(SENSITIVITY_N_M, rel=1e-12)


# --- ProbeRound on a linear bench -------------------------------------------------------------


@dataclass
class _LinearBench:
    """Four legs on springs: force and attitude follow the commanded travel of the probe."""

    geometry: C2Geometry
    grounded: np.ndarray
    attitude_gain: float = 1.0
    """Scales the attitude response (large values exercise the attitude limit)."""
    t_s: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    commands: list[np.ndarray] = field(default_factory=list)

    def reading(self) -> ProbeReading:
        sensitivity = self.geometry.load_sensitivity_diag_N_m
        force = 70e3 + np.where(self.grounded, sensitivity * self.travel_m, 0.0)
        grounded_travel = np.where(self.grounded, self.travel_m, 0.0)
        attitude = self.attitude_gain * (
            self.geometry.attitude_sensitivity_rad_m.T @ grounded_travel
        )
        tilt = (float(attitude[0]), float(attitude[1]))
        stroke = 0.6 + self.travel_m
        return ProbeReading(self.t_s, force, stroke, stroke, tilt, tilt)

    def run(self, settings: ProbeSettings, stroke_max_m: float = math.inf) -> ProbeRound:
        history = [(0.0, 0.0)] * 20
        probe = ProbeRound(
            self.reading(),
            settings,
            self.geometry.max_speed_m_s,
            PERIOD_S,
            self.geometry.load_sensitivity_diag_N_m,
            self.geometry.attitude_sensitivity_rad_m,
            history,
            stroke_max_m=stroke_max_m,
        )
        while not probe.is_finished and self.t_s < 30.0:
            command = probe.step(self.reading())
            self.commands.append(command)
            self.travel_m = self.travel_m + command * PERIOD_S
            self.t_s += PERIOD_S
        return probe


def _net_probe_travel_m(geometry: C2Geometry) -> np.ndarray:
    """Travel left after a round: FL one period of extension, the others none.

    Inherited from the design (14.6) and the reduced model: the first leg starts moving in the
    period that creates the round, every later stage one period after its switching period, so
    FL extends one period more than it retracts (0.11 mm per round).
    """
    one_period_m = RECT.speed_fraction * geometry.max_speed_m_s * PERIOD_S
    return np.array([one_period_m, 0.0, 0.0, 0.0])


def test_probe_round_judges_every_leg_and_returns_to_the_start(geometry) -> None:
    grounded = np.array([True, True, True, False])
    bench = _LinearBench(geometry, grounded)
    probe = bench.run(RECT)
    assert probe.is_finished
    assert [result.leg_index for result in probe.results] == [0, 1, 2, 3]
    assert [result.is_grounded for result in probe.results] == grounded.tolist()
    assert all(result.is_attitude_consistent for result in probe.results)
    np.testing.assert_allclose(bench.travel_m, _net_probe_travel_m(geometry), rtol=0, atol=1e-15)
    commands = np.array(bench.commands)
    assert np.count_nonzero(commands, axis=1).max() == 1  # one leg at a time
    speed = RECT.speed_fraction * geometry.max_speed_m_s
    assert np.abs(commands).max() == pytest.approx(speed)
    # 8 stages x (move periods + hold 20 periods + switching period) + FL's extra period:
    # move = depth / speed (17 periods at the 0.68 m YAML's 5.67 mm/s), hold 0.4 s, T 20 ms.
    move_periods = math.floor(RECT.depth_m / speed / PERIOD_S)
    hold_periods = round(RECT.hold_s / PERIOD_S)
    assert len(commands) == 8 * (move_periods + hold_periods + 1) + 1


def test_probe_stops_extending_at_the_attitude_limit(geometry) -> None:
    """D4: a leg whose extension tilts the body past the limit stops early and returns."""
    grounded = np.ones(4, dtype=bool)
    bench = _LinearBench(geometry, grounded, attitude_gain=10.0)  # ~0.24 deg for 2 mm of FL
    probe = bench.run(RECT)
    fl_result = probe.results[FL]
    assert fl_result.is_attitude_limited
    np.testing.assert_allclose(bench.travel_m, _net_probe_travel_m(geometry), rtol=0, atol=1e-15)
    commands = np.array(bench.commands)
    extend_periods = int(np.count_nonzero(commands[:, FL] > 0))
    retract_periods = int(np.count_nonzero(commands[:, FL] < 0))
    assert extend_periods == retract_periods + 1 < 18
    # The limit is checked on the reading before each command, so the peak overshoots it by at
    # most one period of travel (0.24 deg / 18 periods).
    speed = RECT.speed_fraction * geometry.max_speed_m_s
    peak_travel_m = extend_periods * PERIOD_S * speed
    peak_tilt_rad = 10.0 * np.max(np.abs(geometry.attitude_sensitivity_rad_m[FL])) * peak_travel_m
    one_period_rad = peak_tilt_rad / extend_periods
    assert peak_tilt_rad <= RECT.attitude_limit_rad + one_period_rad + 1e-15


TRAPEZOID = ProbeSettings()


def _residual_ratio(speeds: np.ndarray, depth_m: float, frequency_hz: float) -> float:
    """|V(omega)| / depth of the zero-order-held speed sequence (spec 16.1 R(f))."""
    omega = 2.0 * math.pi * frequency_hz
    centres = (np.arange(len(speeds)) + 0.5) * PERIOD_S
    half = 0.5 * omega * PERIOD_S
    hold_gain = PERIOD_S * math.sin(half) / half
    spectrum = np.sum(speeds * np.exp(-1j * omega * centres)) * hold_gain
    return float(abs(spectrum)) / depth_m


def test_trapezoid_profile_depth_speed_and_residual() -> None:
    """P1: depth 2 mm (+-1e-9), peak speed 2 mm / 0.56 s, residual ratio <= 0.05 (1.70-2.95 Hz)."""
    speeds = trapezoid_speeds(2e-3, 0.56, 0.36, PERIOD_S)
    assert float(np.sum(speeds)) * PERIOD_S == pytest.approx(2e-3, abs=1e-9)
    assert speeds.max() == pytest.approx(2e-3 / 0.56, rel=1e-12)
    assert len(speeds) == 46  # (0.56 + 0.36) s / 20 ms
    ratios = [_residual_ratio(speeds, 2e-3, f) for f in np.linspace(1.70, 2.95, 126)]
    assert max(ratios) <= 0.05
    rect = np.full(18, RECT.speed_fraction * 0.68 / 30.0)
    assert _residual_ratio(rect, 2e-3, 1.78) > 0.4  # the R2 / R3 probe (spec 16.1: 0.469)


def test_trapezoid_round_returns_every_leg_exactly(geometry) -> None:
    grounded = np.array([True, True, True, False])
    bench = _LinearBench(geometry, grounded)
    probe = bench.run(TRAPEZOID)
    assert [result.is_grounded for result in probe.results] == grounded.tolist()
    np.testing.assert_allclose(bench.travel_m, 0.0, rtol=0, atol=1e-15)
    commands = np.array(bench.commands)
    assert np.abs(commands).max() == pytest.approx(2e-3 / 0.56, rel=1e-12)
    for leg in range(4):
        assert np.count_nonzero(commands[:, leg] > 0) == np.count_nonzero(commands[:, leg] < 0)


@pytest.mark.parametrize("settings", [TRAPEZOID, RECT], ids=["trapezoid", "rect"])
def test_round_feeds_the_quality_windows_and_the_midpoint(geometry, settings) -> None:
    """Q1 / K1 plumbing: quiet windows give finite zero ratios, the half-move stiffness is S."""
    grounded = np.array([True, True, True, False])
    probe = _LinearBench(geometry, grounded).run(settings)
    sensitivity = geometry.load_sensitivity_diag_N_m
    for leg, result in enumerate(probe.results):
        assert result.attitude_ripple_ratio == pytest.approx(0.0, abs=1e-9)
        assert result.attitude_drift_ratio == pytest.approx(0.0, abs=1e-9)
        assert not result.is_attitude_rippled
        expected_stiffness = sensitivity[leg] if grounded[leg] else 0.0
        assert result.incremental_stiffness_N_m == pytest.approx(
            expected_stiffness, rel=1e-9, abs=1e-6
        )


def test_trapezoid_ramps_down_at_the_attitude_limit(geometry) -> None:
    bench = _LinearBench(geometry, np.ones(4, dtype=bool), attitude_gain=10.0)
    probe = bench.run(TRAPEZOID)
    assert probe.results[FL].is_attitude_limited
    np.testing.assert_allclose(bench.travel_m, 0.0, rtol=0, atol=1e-15)
    fl_speeds = np.array(bench.commands)[:, FL]
    extension = fl_speeds[fl_speeds > 0]
    assert extension.sum() * PERIOD_S < 2e-3
    assert np.all(np.abs(np.diff(fl_speeds)) <= 2e-3 / 0.56 / (0.36 / PERIOD_S) * 1.5)


def _bench_near_the_stroke_end(geometry: C2Geometry, stroke_max_m: float, settings):
    bench = _LinearBench(geometry, np.ones(4, dtype=bool))
    probe = bench.run(settings, stroke_max_m=stroke_max_m)
    return bench, probe


@pytest.mark.parametrize("settings", [TRAPEZOID, RECT], ids=["trapezoid", "rect"])
def test_stroke_guard_retracts_first_near_the_stroke_end(geometry, settings) -> None:
    """P6: s + 2 mm > s_max - 5 mm -> retract first; travel nets to the same, same verdicts."""
    normal_bench, normal = _bench_near_the_stroke_end(geometry, math.inf, settings)
    stroke_max = 0.6 + 0.006  # s 0.600 m: 0.600 + 0.002 > 0.601, 0.600 <= 0.601
    bench, guarded = _bench_near_the_stroke_end(geometry, stroke_max, settings)
    assert all(result.is_reversed for result in guarded.results)
    commands = np.array(bench.commands)
    first_moves = [commands[np.flatnonzero(commands[:, leg])[0], leg] for leg in range(4)]
    assert all(speed < 0.0 for speed in first_moves)
    # Trapezoid: both net 0. Rect: the FL extra period (P4) now falls on the retraction.
    np.testing.assert_allclose(bench.travel_m, -normal_bench.travel_m, rtol=0, atol=1e-15)
    for reversed_result, normal_result in zip(guarded.results, normal.results, strict=True):
        assert reversed_result.is_grounded == normal_result.is_grounded
        assert reversed_result.incremental_stiffness_N_m == pytest.approx(
            normal_result.incremental_stiffness_N_m, rel=1e-6
        )
        # Rect: FL ends one period (0.11 mm) off its start (P4), about S_ii x 0.11 mm / 2.
        assert reversed_result.load_estimate_N == pytest.approx(70e3, abs=1e3)
        assert reversed_result.attitude_response_ratio == pytest.approx(1.0, rel=1e-6)


def test_stroke_guard_skips_a_leg_at_the_stroke_end(geometry) -> None:
    bench, probe = _bench_near_the_stroke_end(geometry, 0.6 + 0.004, TRAPEZOID)
    assert probe.skipped_legs == [0, 1, 2, 3]
    assert all(result.is_skipped for result in probe.results)
    np.testing.assert_array_equal(np.array(bench.commands), 0.0)


def test_invalid_probe_settings_are_rejected() -> None:
    with pytest.raises(ValueError):
        ProbeSettings(speed_fraction=0.0)
    with pytest.raises(ValueError):
        ProbeSettings(depth_m=0.0)


def test_probe_results_carry_the_leg_timing(geometry) -> None:
    """J-0 (spec 59.1): each result keeps its move start and the two hold-end reading times,
    the times of the commands it issued (trapezoid default profile)."""
    bench = _LinearBench(geometry, np.array([True, True, True, True]))
    probe = bench.run(ProbeSettings())
    commands = np.array(bench.commands)
    times = np.arange(len(commands)) * PERIOD_S
    for result in probe.results:
        moving = times[commands[:, result.leg_index] != 0.0]
        assert result.t_move_start_s == pytest.approx(moving[0])
        assert result.t_move_start_s < result.t_first_hold_end_s < result.t_second_hold_end_s
        assert result.t_second_hold_end_s == pytest.approx(
            moving[-1] + PERIOD_S + ProbeSettings().hold_s, abs=PERIOD_S / 2)


def test_tail_sequence_option_returns_each_leg_and_ends_extending(geometry) -> None:
    """Rev. 11 option: +d -> E -> -(d + tail) -> R -> +tail -> settle; every leg comes back to
    its start and its last move extends; the readings E and R stay the midpoint basis."""
    from outrigger_sim.control.ground_contact import ProbeSequence

    bench = _LinearBench(geometry, np.array([True, True, True, True]))
    probe = bench.run(ProbeSettings(sequence=ProbeSequence.EXTEND_RETRACT_TAIL))
    assert probe.is_finished and len(probe.results) == 4
    np.testing.assert_allclose(bench.travel_m, 0.0, atol=1e-12)
    commands = np.array(bench.commands)
    for leg in range(4):
        moving = commands[:, leg][commands[:, leg] != 0.0]
        assert moving[-1] > 0.0


def test_u63_correction_uses_the_measured_secant_when_grounded() -> None:
    """U63: a given correction S_ii replaces the nominal one; with ``measured_if_grounded`` the
    measured secant replaces it for a grounded stiffness cue."""
    from outrigger_sim.control.ground_contact import ProbeSample, ProbeSensitivity, evaluate_probe

    nominal, secant = 5e6, 6e6
    sample = ProbeSample(leg_index=0, start_force_N=50e3, start_rod_stroke_m=0.4,
                         start_motor_stroke_m=0.4, extended_force_N=50e3 + secant * 2e-3,
                         extended_rod_stroke_m=0.402, extended_motor_stroke_m=0.402,
                         retracted_force_N=50e3, retracted_rod_stroke_m=0.4)
    plain = evaluate_probe(sample, nominal, (0.0, 0.0), ProbeSettings())
    given = evaluate_probe(sample, nominal, (0.0, 0.0), ProbeSettings(), 5.83e6)
    measured = evaluate_probe(
        sample, nominal, (0.0, 0.0),
        ProbeSettings(sensitivity=ProbeSensitivity.MEASURED_IF_GROUNDED), 5.83e6)
    assert plain.seal_friction_estimate_N == pytest.approx(0.5 * (secant - nominal) * 2e-3)
    assert given.seal_friction_estimate_N == pytest.approx(0.5 * (secant - 5.83e6) * 2e-3)
    assert measured.seal_friction_estimate_N == pytest.approx(0.0, abs=1e-6)
    assert measured.load_estimate_N == pytest.approx(50e3)
