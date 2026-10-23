"""C2 revision R3: CHECK / IDLE, READY target changes, ramp, H1 trigger, A5, Z1.

``00_docs/04_control/s6_control_spec.md`` 2.2-2.6 and the test list of 2.9. Synthetic readings
as in ``test_c2.py``: constant leg loads, the crawler-free operating strokes and an
accelerometer that reads a fixed tilt. The rules A0-A4 themselves are in ``test_target.py``;
the target-0 regression against the R2 traces is ``test_c2.py`` (``check_time_s`` 0).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    C2Thresholds,
    ContactJudge,
    ReanchorDirection,
    TargetSettings,
)
from outrigger_sim.control.target import AttitudeTarget, SlopeLimitMode, TargetCode
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02
LEG_LOAD_N = 80e3
TIME_LIMIT_S = 120.0
# Loads of the levelled machine, top level (control_candidates_comparison, final loads).
LEVELLED_LOADS_N = np.array([118e3, 116e3, 72e3, 71e3])


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
    """Rod strokes with every pad on the floor and the crawler 50 mm above it."""
    return geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + 0.05


@dataclass
class _Bench:
    """Feeds constant loads and strokes; the tilt is whatever the test sets."""

    controller: C2Controller
    geometry: C2Geometry
    tilt_rad: tuple[float, float] = (0.0, 0.0)
    forces_N: np.ndarray | None = None
    t_s: float = 0.0

    def step(self) -> np.ndarray:
        self.t_s += PERIOD_S
        strokes = _operating_strokes(self.geometry)
        forces = np.full(4, LEG_LOAD_N) if self.forces_N is None else self.forces_N
        measurements = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=_specific_force(*self.tilt_rad),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=forces / self.geometry.head_area_m2,
            stroke_m=strokes,
            stroke_corrected_m=strokes,
        )
        return self.controller.update(measurements).leg_speed_m_s

    def run_while(self, phase: C2Phase) -> list[np.ndarray]:
        commands = []
        while self.controller.phase is phase and self.t_s < TIME_LIMIT_S:
            commands.append(self.step())
        return commands

    def run_until(self, phase: C2Phase) -> None:
        while self.controller.phase is not phase and self.t_s < TIME_LIMIT_S:
            self.step()
        assert self.controller.phase is phase


def _bench(geometry: C2Geometry, crawler_tilt_deg=(0.0, 0.0), **target_fields) -> _Bench:
    """Controller (pressure judge, no output ramp) on a crawler tilted by the given angles."""
    config = C2Config(
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
        target=TargetSettings(**target_fields),
    ).with_r5_behaviour()  # R3 target mechanism, no R6 lock tails
    tilt = tuple(math.radians(value) for value in crawler_tilt_deg)
    return _Bench(C2Controller(geometry, config), geometry, tilt_rad=tilt)


def _event_names(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events]


def _ready_bench(geometry: C2Geometry, **target_fields) -> _Bench:
    bench = _bench(geometry, **target_fields)
    bench.run_until(C2Phase.READY)
    return bench


# --- CHECK / IDLE (C1, C2) --------------------------------------------------------------------


def test_check_holds_two_seconds_then_touches(geometry) -> None:
    bench = _bench(geometry, crawler_tilt_deg=(1.0, 2.0))
    commands = bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.phase is C2Phase.TOUCH
    assert len(commands) == round(2.0 / PERIOD_S) + 1  # samples t0 ... t0 + 2 s; the last touches
    np.testing.assert_array_equal(np.array(commands), 0.0)  # loads present: TOUCH waits too
    roll, pitch = controller.crawler_attitude_rad
    assert (math.degrees(roll), math.degrees(pitch)) == pytest.approx((1.0, 2.0), abs=1e-9)
    assert controller.target_code is TargetCode.ACCEPTED
    assert controller.target == controller.reference == AttitudeTarget()


def test_rejected_check_idles_with_one_event(geometry) -> None:
    """D8: a 3.4 deg slope -> IDLE, all u = 0, the code once, not a FAULT."""
    bench = _bench(geometry, crawler_tilt_deg=(0.0, 3.4))
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.phase is C2Phase.IDLE
    commands = [bench.step() for _ in range(50)]
    np.testing.assert_array_equal(np.array(commands), 0.0)
    assert controller.phase is C2Phase.IDLE
    assert _event_names(controller) == ["REJ_SLOPE_D8"]
    assert controller.target is None
    meta = controller.meta()
    json.dumps(meta)
    assert meta["revision"] == "R7"
    assert meta["target"]["code"] == "REJ_SLOPE_D8"
    assert meta["target"]["crawler_attitude_rad"][1] == pytest.approx(math.radians(3.4))


GYRO_BIAS_RAD_S = (math.radians(20.0) / 3600.0, -math.radians(5.0) / 3600.0)


def _measurements_with_gyro(bench: _Bench, rate_rad_s: tuple[float, float]) -> Measurements:
    bench.t_s += PERIOD_S
    strokes = _operating_strokes(bench.geometry)
    return Measurements(
        t_s=bench.t_s,
        specific_force_m_s2=_specific_force(*bench.tilt_rad),
        angular_rate_rad_s=np.array([rate_rad_s[0], rate_rad_s[1], 0.0]),
        head_pressure_Pa=np.full(4, LEG_LOAD_N) / bench.geometry.head_area_m2,
        stroke_m=strokes,
        stroke_corrected_m=strokes,
    )


def test_check_measures_and_removes_the_gyro_bias(geometry) -> None:
    """P3: the mean gyro rate of the CHECK standstill is the bias; afterwards a gyro reading
    of only that bias leaves the rate-integrated attitude unchanged."""
    bench = _bench(geometry)
    controller = bench.controller
    while controller.phase is C2Phase.CHECK:
        controller.update(_measurements_with_gyro(bench, GYRO_BIAS_RAD_S))
    assert controller.gyro_bias_rad_s == pytest.approx(GYRO_BIAS_RAD_S, rel=1e-12)
    assert controller.meta()["target"]["gyro_bias_rad_s"] == pytest.approx(list(GYRO_BIAS_RAD_S))
    integrated_at_check_end = controller.rate_attitude_rad
    for _ in range(100):
        controller.update(_measurements_with_gyro(bench, GYRO_BIAS_RAD_S))
    np.testing.assert_allclose(
        controller.rate_attitude_rad, integrated_at_check_end, rtol=0, atol=1e-15
    )


def test_without_check_the_gyro_bias_is_not_removed(geometry) -> None:
    bench = _bench(geometry, check_time_s=0.0)
    bench.controller.update(_measurements_with_gyro(bench, GYRO_BIAS_RAD_S))
    assert bench.controller.phase is C2Phase.TOUCH
    assert bench.controller.gyro_bias_rad_s is None


def test_verification_mode_accepts_the_same_slope(geometry) -> None:
    bench = _bench(
        geometry, crawler_tilt_deg=(0.0, 3.4), slope_limit_mode=SlopeLimitMode.VERIFICATION
    )
    bench.run_while(C2Phase.CHECK)
    assert bench.controller.phase is C2Phase.TOUCH


def test_request_in_idle_restarts_check(geometry) -> None:
    bench = _bench(
        geometry, crawler_tilt_deg=(0.0, -1.0), target=AttitudeTarget.from_degrees(0.0, 3.0)
    )
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.phase is C2Phase.IDLE
    assert controller.target_code is TargetCode.REJ_TARGET_REL  # 4 deg relative tilt
    check = controller.request_target(AttitudeTarget.from_degrees(0.0, 1.5))
    assert check.code is TargetCode.PENDING_CHECK
    assert controller.phase is C2Phase.CHECK and controller.crawler_attitude_rad is None
    bench.run_while(C2Phase.CHECK)
    assert controller.phase is C2Phase.TOUCH
    assert controller.target == AttitudeTarget.from_degrees(0.0, 1.5)


# --- READY changes (C3, A5, R1, T2) -----------------------------------------------------------


def test_rejected_change_keeps_ready_and_the_target(geometry) -> None:
    bench = _ready_bench(geometry)
    controller = bench.controller
    check = controller.request_target(AttitudeTarget.from_degrees(4.0, 3.0))
    assert check.code is TargetCode.REJ_TARGET_ABS
    bench.step()
    assert controller.phase is C2Phase.READY
    assert controller.target == AttitudeTarget()
    assert controller.events[-1].name == "REJ_TARGET_ABS"


def test_request_while_levelling_is_busy(geometry) -> None:
    bench = _bench(geometry, crawler_tilt_deg=(0.0, 1.0))
    bench.run_until(C2Phase.LEVEL)
    controller = bench.controller
    check = controller.request_target(AttitudeTarget.from_degrees(0.0, 1.0))
    assert check.code is TargetCode.REJ_BUSY
    assert controller.target == AttitudeTarget()
    assert controller.phase is C2Phase.LEVEL
    assert controller.events[-1].name == "REJ_BUSY"


def test_accepted_change_ramps_the_reference_and_completes_after_it(geometry) -> None:
    """0 -> (2.2, 1.6) deg: rate diamond per period, arrival 11.9 s +- T, no DONE before."""
    bench = _ready_bench(geometry)
    controller = bench.controller
    target = AttitudeTarget.from_degrees(2.2, 1.6)
    assert controller.request_target(target).code is TargetCode.ACCEPTED
    assert controller.phase is C2Phase.LEVEL and controller.reference == AttitudeTarget()
    bench.tilt_rad = (target.roll_rad, target.pitch_rad)  # the body already there: only T2 waits
    previous = controller.reference
    periods = 0
    while controller.reference != target and bench.t_s < TIME_LIMIT_S:
        bench.step()
        periods += 1
        reference = controller.reference
        roll_step = abs(math.degrees(reference.roll_rad - previous.roll_rad))
        pitch_step = abs(math.degrees(reference.pitch_rad - previous.pitch_rad))
        assert roll_step / 0.4 + pitch_step / 0.25 <= PERIOD_S * (1 + 1e-9)
        assert controller.phase is C2Phase.LEVEL, "completed while the reference ramps"
        previous = reference
    assert periods * PERIOD_S == pytest.approx(2.2 / 0.4 + 1.6 / 0.25, abs=PERIOD_S)
    bench.run_until(C2Phase.READY)
    assert "target_changed" in _event_names(controller)


def test_attitude_error_uses_the_ramped_reference(geometry) -> None:
    """T1: the first period after the change commands only one ramp step of pitch."""
    bench = _ready_bench(geometry)
    controller = bench.controller
    controller.request_target(AttitudeTarget.from_degrees(0.0, 1.0))
    command = bench.step()
    _, roll_rate, pitch_rate, _ = geometry.decompose(command)
    one_step_rad = math.radians(0.25) * PERIOD_S
    assert controller.reference.pitch_rad == pytest.approx(one_step_rad, rel=1e-12)
    assert pitch_rate == pytest.approx(0.4 * one_step_rad, rel=1e-6)
    assert roll_rate == pytest.approx(0.0, abs=1e-15)


def _levelled_strokes(geometry: C2Geometry) -> tuple[np.ndarray, np.ndarray]:
    """Motor and rod strokes of a level machine on a flat floor, crawler 50 mm up."""
    rod = _operating_strokes(geometry)
    motor = rod.copy()
    for _ in range(20):
        motor = rod + LEVELLED_LOADS_N / geometry.oil_stiffness_N_m(motor)
    return motor, rod


def test_stroke_predictor_matches_the_envelope_map(geometry) -> None:
    """A5: flat, level, target pitch 3 deg -> largest predicted stroke 626 +- 3 mm (map 626.0)."""
    motor, rod = _levelled_strokes(geometry)
    strokes = geometry.predicted_strokes_m(motor, rod, (0.0, math.radians(3.0)), 0.05)
    assert strokes.max() == pytest.approx(0.626, abs=3e-3)
    corners = geometry.clearance_corners_m(rod)
    assert corners.min() == pytest.approx(0.05, abs=1e-9)
    assert geometry.clearance_estimate_m(rod) == corners.min()


def test_stroke_predictor_rejects_a_change_beyond_the_stroke(geometry) -> None:
    """A5 on a shortened stroke: pitch 3 deg would need ~626 mm, s_max 600 mm leaves 587 mm."""
    short = replace(geometry, stroke_max_m=0.600)
    bench = _ready_bench(short)
    check = bench.controller.request_target(AttitudeTarget.from_degrees(0.0, 3.0))
    assert check.code is TargetCode.REJ_TARGET_STROKE
    assert bench.controller.phase is C2Phase.READY


# --- H1 (U2) and Z1 ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("target_pitch_deg", "is_applied"), [(-3.0, True), (2.6, False)], ids=["-3deg", "+2.6deg"]
)
def test_reanchor_trigger_uses_the_relative_pitch(geometry, target_pitch_deg, is_applied) -> None:
    """H1: theta_c 0.13 deg; target -3 deg (relative 3.13) applies, +2.6 (2.47) is skipped."""
    target = AttitudeTarget.from_degrees(0.0, target_pitch_deg)
    bench = _bench(geometry, crawler_tilt_deg=(0.0, 0.13), target=target)
    bench.run_until(C2Phase.LEVEL)
    bench.tilt_rad = (target.roll_rad, target.pitch_rad)
    bench.run_while(C2Phase.LEVEL)
    assert bench.controller.phase is C2Phase.DONE
    bench.step()
    controller = bench.controller
    assert controller.phase is (C2Phase.REANCHOR if is_applied else C2Phase.READY)
    assert controller.reanchor_outcome == (None if is_applied else "skipped:theta_below_min")


@pytest.mark.parametrize(
    ("target_pitch_deg", "skip_reason"),
    [(-3.0, None), (3.0, "nose_up")],
    ids=["-3deg", "+3deg"],
)
def test_nose_down_only_judges_the_pitch_relative_to_the_target(
    geometry, target_pitch_deg, skip_reason
) -> None:
    """Spec 82.5: theta_c 0.13 deg; target -3 deg (``theta_c - theta_t`` = +3.13, relative
    nose-down) applies, target +3 deg (-2.87, relative nose-up) is skipped as ``nose_up``."""
    target = AttitudeTarget.from_degrees(0.0, target_pitch_deg)
    bench = _bench(geometry, crawler_tilt_deg=(0.0, 0.13), target=target)
    config = bench.controller.config  # R5 preset: direction "both"
    nose_down_only = replace(config.reanchor, direction=ReanchorDirection.NOSE_DOWN_ONLY)
    bench.controller = C2Controller(geometry, replace(config, reanchor=nose_down_only))
    bench.run_until(C2Phase.LEVEL)
    bench.tilt_rad = (target.roll_rad, target.pitch_rad)
    bench.run_while(C2Phase.LEVEL)
    assert bench.controller.phase is C2Phase.DONE
    bench.step()
    controller = bench.controller
    is_applied = skip_reason is None
    assert controller.phase is (C2Phase.REANCHOR if is_applied else C2Phase.READY)
    assert controller.reanchor_outcome == (None if is_applied else f"skipped:{skip_reason}")


# --- provisional B nose-up limit (spec revision 20 86.3, R7) ----------------------------------


def _interim_b_bench(geometry: C2Geometry, crawler_tilt_deg=(0.0, 0.0)) -> _Bench:
    """:func:`_bench` with :meth:`C2Config.with_interim_b` on top."""
    bench = _bench(geometry, crawler_tilt_deg=crawler_tilt_deg)
    config = bench.controller.config.with_interim_b()
    bench.controller = C2Controller(geometry, config)
    return bench


def test_interim_b_preset_and_default() -> None:
    """The preset sets 3.1 deg, the default stays ``None`` (3.2 deg), ``with_r6_behaviour``
    drops it again; the meta shows the half-span in use."""
    default = C2Config()
    interim = default.with_interim_b()
    assert default.target.relative_pitch_span_nose_up_rad is None
    assert default.target.limits.relative_pitch_span_nose_up_rad is None
    assert interim.target.limits.relative_pitch_span_nose_up_rad == math.radians(3.1)
    assert interim.target.limits.relative_pitch_span_rad == math.radians(3.2)
    assert interim.with_r6_behaviour().target == default.target
    assert replace(interim, target=default.target) == default
    params = load_params()
    meta = C2Controller.from_params(params, interim).meta()["target"]["limits_rad"]
    assert meta["relative_pitch_span_nose_up_rad"] == math.radians(3.1)


def test_interim_b_is_refused_in_the_verification_mode() -> None:
    """Spec revision 22 90.2: B is an operating limit; on a verification-mode config the preset
    (and the key itself) raises, so the 3.5 deg nose-up verification cases keep their range."""
    verification = C2Config(target=TargetSettings(slope_limit_mode=SlopeLimitMode.VERIFICATION))
    with pytest.raises(ValueError, match="relative_pitch_span_nose_up_rad"):
        verification.with_interim_b()
    with pytest.raises(ValueError, match="relative_pitch_span_nose_up_rad"):
        TargetSettings(
            slope_limit_mode=SlopeLimitMode.VERIFICATION,
            relative_pitch_span_nose_up_rad=math.radians(3.1),
        )
    assert verification.with_r6_behaviour().target == verification.target
    limits = verification.target.limits
    assert limits.relative_pitch_span_nose_up_rad is None
    assert limits.relative_pitch_span_rad == math.radians(3.5)


@pytest.mark.parametrize(("use_interim_b", "phase"), [(True, C2Phase.IDLE), (False, C2Phase.TOUCH)])
def test_interim_b_rejects_a_nose_up_floor_of_3_15_deg(geometry, use_interim_b, phase) -> None:
    """D8 start check: crawler nose up 3.15 deg, level target -> B rejects, default accepts."""
    tilt = (0.0, -3.15)
    bench = _interim_b_bench(geometry, tilt) if use_interim_b else _bench(geometry, tilt)
    bench.run_while(C2Phase.CHECK)
    controller = bench.controller
    assert controller.phase is phase
    expected = TargetCode.REJ_SLOPE_D8 if use_interim_b else TargetCode.ACCEPTED
    assert controller.target_code is expected


@pytest.mark.parametrize(
    ("use_interim_b", "code"),
    [(True, TargetCode.REJ_TARGET_REL), (False, TargetCode.ACCEPTED)],
)
def test_interim_b_rejects_a_relative_nose_up_target_of_3_15_deg(
    geometry, use_interim_b, code
) -> None:
    """Relative diamond in READY: floor -1 deg, target +2.15 deg (``theta_t - theta_g`` =
    +3.15 deg, nose-up side) -> B rejects, default accepts."""
    tilt = (0.0, -1.0)
    bench = _interim_b_bench(geometry, tilt) if use_interim_b else _bench(geometry, tilt)
    bench.run_until(C2Phase.LEVEL)
    bench.tilt_rad = (0.0, 0.0)
    bench.run_until(C2Phase.READY)
    check = bench.controller.request_target(AttitudeTarget.from_degrees(0.0, 2.15))
    assert check.code is code


def test_target_change_re_arms_the_reanchor(geometry) -> None:
    """U3 / H2: level (skipped) -> pitch -3 deg in READY re-anchors at the next DONE."""
    bench = _ready_bench(geometry)
    controller = bench.controller
    assert controller.reanchor_outcome == "skipped:theta_below_min"
    target = AttitudeTarget.from_degrees(0.0, -3.0)
    assert controller.request_target(target).code is TargetCode.ACCEPTED
    bench.tilt_rad = (target.roll_rad, target.pitch_rad)
    bench.run_until(C2Phase.REANCHOR)
    assert controller.meta()["reanchor"]["outcomes"] == ["skipped:theta_below_min"]


@pytest.mark.parametrize(("clearance_m", "is_valid"), [(0.0923, True), (0.0925, False)])
def test_clearance_target_rule(geometry, clearance_m, is_valid) -> None:
    """Z1 / 65.3: 642.2 + 1.005 (c* - 50) <= 684.8 mm -> c* <= 92.39 mm (spec 92)."""
    config = C2Config(thresholds=C2Thresholds(clearance_target_m=clearance_m))
    if is_valid:
        C2Controller(geometry, config)
    else:
        with pytest.raises(ValueError, match="clearance_target_m"):
            C2Controller(geometry, config)


# --- READY monitoring -------------------------------------------------------------------------


def test_ready_reports_a_locked_pressure_above_350_bar_once(geometry) -> None:
    bench = _ready_bench(geometry)
    over_limit = float(geometry.locked_force_limit_N[1]) + 1e3
    assert over_limit == pytest.approx(350e5 * geometry.head_area_m2[1] + 1e3)
    bench.forces_N = np.array([LEG_LOAD_N, over_limit, LEG_LOAD_N, LEG_LOAD_N])
    for _ in range(3):
        bench.step()
    assert bench.controller.phase is C2Phase.READY
    assert _event_names(bench.controller).count("locked_pressure_over_limit:FR") == 1


def test_reset_starts_a_new_check(geometry) -> None:
    bench = _ready_bench(geometry)
    controller = bench.controller
    controller.reset()
    assert controller.phase is C2Phase.CHECK
    assert controller.target is None and controller.crawler_attitude_rad is None
    assert controller.meta()["target"]["checks"] == []
