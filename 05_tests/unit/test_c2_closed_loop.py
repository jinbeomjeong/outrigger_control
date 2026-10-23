"""Engine-free closed loop: C2 (and the C8 skeleton) on the reduced 6-DoF plant.

The plant is ``04_scripts/01_dynamics/run_control_comparison.py`` ``Plant`` (layout D crawler,
L1 basis, imported read-only), on which the C2 design was verified. Its kernel is jitted with
numba, which the Chrono-dev environment does not have; the module is skipped there and runs in
dynamics-dev: ``python.exe -I -m pytest 05_tests/unit/test_c2_closed_loop.py`` with the
dynamics-dev interpreter.

The controller sees only :class:`~outrigger_sim.signals.Measurements` built from the plant's
sensor outputs: the specific force at the IMU point (C1) averaged over the control period,
the head pressure, the motor stroke (``stroke_m``) and the rod stroke (``stroke_corrected_m``),
all ideal (no noise, no bias). Checks of the S6 controller list (chrono_build_plan.md S6) in the
reduced model: levelling on top flat / diagonal 3 deg / roll +3 deg, the F_min guard after a
sinking pad, refusal of a slope outside the start limit, attitude change of the probe and the
probe verdict on a lifted leg (seal friction 0).
"""

from __future__ import annotations

import copy
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("numba", reason="the reduced plant kernel needs numba (dynamics-dev)")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
import run_control_comparison as reduced_model  # noqa: E402

from outrigger_sim.control.c2 import (  # noqa: E402
    C2Config,
    C2Controller,
    C2Phase,
    C2Thresholds,
    IntegratorBandMode,
    TargetSettings,
)
from outrigger_sim.control.c8 import C8Controller, C8Phase  # noqa: E402
from outrigger_sim.control.ground_contact import (  # noqa: E402
    LoadBand,
    ProbeReading,
    ProbeRound,
    ProbeSettings,
)
from outrigger_sim.control.target import (  # noqa: E402
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
    TargetAcceptance,
    TargetCode,
)
from outrigger_sim.params import LEG_ORDER, load_params  # noqa: E402
from outrigger_sim.sensors.attitude import AttitudeEstimator  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

RUN_LIMIT_S = 150.0
HOLD_AFTER_READY_S = 5.0
ACCURACY_TARGET_DEG = 0.2  # CLAUDE.md: steady-state error +-0.2 deg
F_MIN_CRITERION_MARGIN_N = 5e3  # D8 / c2_design 16.5: F_min + 5 kN on the true force
PROBE_ATTITUDE_LIMIT_DEG = 0.1  # decision D4
DIAGONAL_3_DEG = 2.1213  # roll = pitch = 3 / sqrt(2) deg
JOINT_BAND_ROLL_LEVELLING_SPEC_S = 19.1  # spec 16.2 (P2), reduced runs, roll 5.5 deg top
JOINT_BAND_SPEC_SPEED_M_S = 0.68 / 30.0  # v_max of those runs (REXOME33 YAML, 22.67 mm/s)
RR = LEG_ORDER.index("RR")
# Sink of the RR floor that lifts the RR pad off a levelled machine (load ~70 kN, the leg's
# load sensitivity ~5e6 N/m needs ~14 mm); 30 mm leaves a clear gap for the 2 mm probe. The
# machine then teeters on the FR-RL diagonal (FL ~30-70 kN, about 1.2 Hz, lightly damped), so
# the sink is slow and the rocking decays before the probe (else the attitude limit trips).
LIFTING_SINK_M = 0.03
SINK_RAMP_S = 5.0
# A sudden sink (0.2 s) lifts RR before the C2 loops can follow it.
FAST_SINK_RAMP_S = 0.2
SINK_SETTLE_S = 20.0
# c2_design 8.2 settling scenario: RR floor sinks 11.5 mm in 2 s, 2 s after READY.
SETTLE_SINK_M = 0.0115


@dataclass
class LoopRecord:
    """True plant quantities per control period (for the checks, not seen by the controller)."""

    t_s: list[float] = field(default_factory=list)
    attitude_rad: list[tuple[float, float]] = field(default_factory=list)
    true_cylinder_force_N: list[np.ndarray] = field(default_factory=list)
    pad_contact_force_N: list[np.ndarray] = field(default_factory=list)
    crawler_force_N: list[float] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)

    def arrays(self) -> dict[str, np.ndarray]:
        return {
            "t_s": np.array(self.t_s),
            "attitude_deg": np.degrees(np.array(self.attitude_rad)),
            "force_N": np.array(self.true_cylinder_force_N),
            "contact_N": np.array(self.pad_contact_force_N),
            "crawler_N": np.array(self.crawler_force_N),
            "phase": np.array(self.phases),
        }


def settled_plant(
    roll_deg: float = 0.0, pitch_deg: float = 0.0, auger_level: str = "top"
) -> reduced_model.Plant:
    """Auger level (top by default), rigid floor of the given slope, settled on the crawler
    (t = 0)."""
    plant = reduced_model.Plant(auger_level, roll_deg, pitch_deg)
    settle_steps = int(round(reduced_model.SETTLE_ON_CRAWLER_S / reduced_model.DT))
    plant.step(np.zeros(4), settle_steps)
    plant.t = 0.0
    return plant


def measurements_from_plant(plant, accumulated, head_area_m2: float) -> Measurements:
    """Ideal sensor values of the last control period (what a runner would deliver)."""
    return Measurements(
        t_s=plant.t,
        specific_force_m_s2=accumulated[0:3] / reduced_model.N_SUB,
        angular_rate_rad_s=plant.w.copy(),  # body axes; end-of-period value, not the mean
        head_pressure_Pa=plant.pressure() / head_area_m2,
        stroke_m=plant.sref.copy(),
        stroke_corrected_m=plant.x.copy(),
    )


@dataclass
class ClosedLoop:
    """Plant + controller at the 20 ms control period with a zero-order hold."""

    plant: reduced_model.Plant
    controller: C2Controller | C8Controller
    head_area_m2: float
    record: LoopRecord = field(default_factory=LoopRecord)
    command_m_s: np.ndarray = field(default_factory=lambda: np.zeros(4))
    last: Measurements | None = None

    def advance(self, command_m_s: np.ndarray | None = None) -> Measurements:
        """One control period with the held command, then record and measure."""
        held = self.command_m_s if command_m_s is None else command_m_s
        accumulated = self.plant.step(held, reduced_model.N_SUB)
        self.record.t_s.append(self.plant.t)
        self.record.attitude_rad.append(self.plant.attitude())
        self.record.true_cylinder_force_N.append(self.plant.true_cyl_force().copy())
        self.record.pad_contact_force_N.append(accumulated[11:15].copy())
        self.record.crawler_force_N.append(float(accumulated[15]))
        self.record.phases.append(str(self.controller.phase))
        self.last = measurements_from_plant(self.plant, accumulated, self.head_area_m2)
        return self.last

    def run(self, until: Callable[[], bool], limit_s: float = RUN_LIMIT_S) -> None:
        while self.plant.t < limit_s and not until():
            measurements = self.advance()
            self.command_m_s = np.array(self.controller.update(measurements).leg_speed_m_s)

    def run_for(self, duration_s: float) -> None:
        t_end = self.plant.t + duration_s
        self.run(lambda: self.plant.t >= t_end - 1e-9, limit_s=t_end + 1.0)


def c2_loop(roll_deg=0.0, pitch_deg=0.0, auger_level="top", **config_fields) -> ClosedLoop:
    params = load_params()
    command_ramp_s = params.actuator.command_ramp_s
    ramp_s = command_ramp_s if command_ramp_s > 0.0 else None
    config = C2Config(output_ramp_time_s=ramp_s, **config_fields)
    controller = C2Controller.from_params(params, config)
    return ClosedLoop(
        settled_plant(roll_deg, pitch_deg, auger_level),
        controller,
        controller.geometry.head_area_m2,
    )


def _is_ready(loop: ClosedLoop) -> Callable[[], bool]:
    return lambda: loop.controller.phase in (C2Phase.READY, C8Phase.READY)


def levelled(loop: ClosedLoop) -> ClosedLoop:
    loop.run(_is_ready(loop))
    assert loop.controller.phase in (C2Phase.READY, C8Phase.READY), loop.controller.phase
    loop.run_for(HOLD_AFTER_READY_S)
    return loop


def _after_crawler_liftoff(series: dict[str, np.ndarray]) -> np.ndarray:
    is_lifted = series["crawler_N"] == 0.0
    assert is_lifted.any(), "the crawler never left the floor"
    first = int(np.argmax(is_lifted))
    return np.arange(len(is_lifted)) >= first


def assert_levelled_safely(loop: ClosedLoop, target_deg=(0.0, 0.0)) -> None:
    """READY, true attitude on target within +-0.2 deg, every true force >= F_min + 5 kN."""
    series = loop.record.arrays()
    geometry = loop.controller.geometry
    after_liftoff = _after_crawler_liftoff(series)
    min_force_N = float(series["force_N"][after_liftoff].min())
    assert min_force_N >= geometry.F_min_N + F_MIN_CRITERION_MARGIN_N, min_force_N
    assert (series["contact_N"][after_liftoff] > 0.0).all(), "a pad lifted off"
    last_seconds = series["t_s"] >= series["t_s"][-1] - HOLD_AFTER_READY_S
    error_deg = series["attitude_deg"][last_seconds] - np.array(target_deg)
    assert np.abs(error_deg).max() <= ACCURACY_TARGET_DEG


# --- C2 levelling (S6 check 1, 3, 8 in the reduced model) -------------------------------------


@pytest.fixture(scope="module")
def flat_run() -> ClosedLoop:
    return levelled(c2_loop())


def test_top_flat_levels_and_probes(flat_run) -> None:
    assert_levelled_safely(flat_run)
    assert len(flat_run.controller.probe_history) == 1


def test_roll_three_degrees_levels_within_the_operating_limits() -> None:
    loop = levelled(c2_loop(3.0, 0.0))
    assert_levelled_safely(loop)


def test_diagonal_three_degrees_needs_the_check_off() -> None:
    """Diagonal 3 deg is outside the operating start limit (4.4 / 3.2 deg) and, with the crawler
    settling nose-down (+0.13-0.25 deg measured on the crawler), also just outside the D8
    verification range 5.5 / 3.5 deg; the S6 check (control comparison 7.3, item 1) has to
    switch the target check off."""
    verification = TargetSettings(slope_limit_mode=SlopeLimitMode.VERIFICATION)
    refused = c2_loop(DIAGONAL_3_DEG, DIAGONAL_3_DEG, target=verification)
    refused.run(lambda: refused.controller.phase is not C2Phase.CHECK, limit_s=10.0)
    assert refused.controller.phase is C2Phase.IDLE
    assert refused.controller.target_code is TargetCode.REJ_SLOPE_D8
    unchecked = TargetSettings(acceptance=TargetAcceptance.OFF)
    loop = levelled(c2_loop(DIAGONAL_3_DEG, DIAGONAL_3_DEG, target=unchecked))
    assert_levelled_safely(loop)


def test_slope_outside_the_start_limit_is_refused_and_held() -> None:
    """Nose-down 3.5 deg with the operating limits: IDLE after CHECK (REJ_SLOPE_D8), the
    crawler keeps carrying the machine, no FAULT."""
    loop = c2_loop(0.0, 3.5)
    loop.run(lambda: loop.controller.phase is not C2Phase.CHECK, limit_s=15.0)
    controller = loop.controller
    assert controller.phase is C2Phase.IDLE
    # R5 B1': the nose-down crawler rocks (spec 32.2), so CHECK waits up to 10 s for a quiet
    # bias window and then leaves the bias unremoved.
    # Revision 14 (spec 71-76, U71): CHECK also runs the airborne zero calibration by default;
    # with ideal sensors every leg calibrates (one INFO event per leg, before the 10 s window).
    calibration_events = [f"INFO_PRESSURE_ZERO_CALIBRATED:{name}" for name in LEG_ORDER]
    assert [event.name for event in controller.events] == [
        *calibration_events,
        "WARN_GYRO_BIAS_SKIPPED",
        "REJ_SLOPE_D8",
    ]
    assert controller.gyro_bias_estimate.check_duration_s == pytest.approx(10.0, abs=0.03)
    loop.run_for(3.0)
    assert controller.phase is C2Phase.IDLE
    np.testing.assert_array_equal(loop.command_m_s, 0.0)
    series = loop.record.arrays()
    assert (series["crawler_N"] > 0.0).all()


def test_verification_map_leaves_the_reanchor_pitch_measured() -> None:
    """X7 / H4: nose-down 3.5 deg floor (about 3.8 deg on the crawler) is accepted with the top
    map; ``theta_crawler`` and the REANCHOR anchor stay the measured TOUCH-end pitch. The
    shadow plane estimate (X9) is close to the floor."""
    settings = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    loop = c2_loop(0.0, 3.5, target=settings)
    controller = loop.controller
    loop.run(lambda: controller.phase is C2Phase.LEVEL, limit_s=60.0)
    assert controller.phase is C2Phase.LEVEL
    meta = controller.meta()
    reanchor = meta["reanchor"]
    assert reanchor["anchor_pitch_rad"] == reanchor["theta_crawler_rad"]
    assert math.degrees(reanchor["theta_crawler_rad"]) > 3.6  # measured, not the floor 3.44
    floor_estimate_deg = math.degrees(meta["target"]["floor_estimate_rad"][1])
    assert floor_estimate_deg < math.degrees(reanchor["theta_crawler_rad"]) - 0.2
    shadow_pitch_deg = math.degrees(meta["floor_estimate_touch"]["floor_rad"][1])
    assert shadow_pitch_deg == pytest.approx(3.5, abs=0.05)


def _level_to_done_s(loop: ClosedLoop) -> float:
    series = loop.record.arrays()
    phases, times = series["phase"], series["t_s"]
    level_start = times[np.argmax(phases == str(C2Phase.LEVEL))]
    return float(times[np.argmax(phases == str(C2Phase.DONE))] - level_start)


def _roll_levelling_s(band_mode: IntegratorBandMode) -> float:
    settings = TargetSettings(
        slope_limit_mode=SlopeLimitMode.VERIFICATION,
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    thresholds = C2Thresholds(integrator_band_mode=band_mode)
    loop = c2_loop(5.5, 0.0, target=settings, thresholds=thresholds)
    loop.run(lambda: loop.controller.phase is C2Phase.DONE, limit_s=RUN_LIMIT_S)
    loop.run_for(0.1)
    return _level_to_done_s(loop)


def _joint_band_roll_levelling_expected_s() -> float:
    """Spec 16.2 joint-band time scaled from the spec's leg speed to the YAML ``v_max``.

    The levelling is mostly speed-limited leg travel, so the spec time (REXOME33, 22.67 mm/s)
    is scaled by ``v_spec / v_max``. Measured on this harness (scaled value in brackets):
    19.32 s (19.1) at 22.67 mm/s, 19.62 s (19.66) at 22.03 mm/s, 20.30 s (20.69) at
    20.924 mm/s (REXOME35, dynamics_model.md revision 31 5.13); the unscaled part (PI tail)
    keeps the residue inside the 1 s tolerance.
    """
    max_speed_m_s = load_params().actuator.max_speed_m_s
    return JOINT_BAND_ROLL_LEVELLING_SPEC_S * JOINT_BAND_SPEC_SPEED_M_S / max_speed_m_s


def test_joint_integrator_band_shortens_roll_levelling() -> None:
    """P2 (U17), spec 16.2: roll 5.5 deg top, LEVEL -> DONE 19.1 s +- 1 s with the joint band
    (at the spec's 22.67 mm/s; scaled to the YAML leg speed).

    The per-axis band takes longer (spec: 24.9 s in the reduced runs with the nominal IMU and
    one period of delay; this harness has ideal sensors and no delay, so only the gap is
    checked)."""
    joint_s = _roll_levelling_s(IntegratorBandMode.JOINT)
    axis_s = _roll_levelling_s(IntegratorBandMode.AXIS)
    assert joint_s == pytest.approx(_joint_band_roll_levelling_expected_s(), abs=1.0)
    assert axis_s - joint_s >= 3.0


def test_level_target_pitch_two_degrees_on_a_flat_floor() -> None:
    target = AttitudeTarget.from_degrees(0.0, 2.0)
    loop = levelled(c2_loop(target=TargetSettings(target=target)))
    assert loop.controller.target == target
    assert_levelled_safely(loop, target_deg=(0.0, 2.0))


def test_guard_recovers_a_sinking_pad() -> None:
    """S6 check 6: RR floor sinks 11.5 mm after READY (F_s 0); all legs >= F_min again."""
    loop = levelled(c2_loop())
    plant = loop.plant
    t_start = plant.t
    controller = loop.controller

    has_relevelled = False

    def sink_and_check_ready() -> bool:
        nonlocal has_relevelled
        plant.goff[RR] = SETTLE_SINK_M * min(1.0, (plant.t - t_start) / 2.0)
        has_relevelled |= controller.phase is C2Phase.LEVEL
        return has_relevelled and controller.phase is C2Phase.READY

    loop.run(sink_and_check_ready, limit_s=t_start + RUN_LIMIT_S)
    assert has_relevelled and controller.phase is C2Phase.READY
    loop.run_for(HOLD_AFTER_READY_S)
    final_force_N = loop.record.arrays()["force_N"][-1]
    assert final_force_N.min() >= controller.geometry.F_min_N


def test_c2_with_the_combined_verdict_recovers_a_lifted_rr() -> None:
    """Spec 10.1 P1 default (combined verdict): the RR floor sinks 30 mm in READY, RR lifts off;
    C2 re-levels and probes, and ends READY with every pad on the floor and above F_min."""
    loop = levelled(c2_loop())
    controller = loop.controller
    assert controller.config.probe.use_combined_verdict
    plant = loop.plant
    t_start = plant.t
    has_lifted = has_relevelled = False

    def sink_then_ready() -> bool:
        nonlocal has_lifted, has_relevelled
        plant.goff[RR] = LIFTING_SINK_M * min(1.0, (plant.t - t_start) / FAST_SINK_RAMP_S)
        if loop.record.pad_contact_force_N:
            has_lifted |= bool(loop.record.pad_contact_force_N[-1][RR] == 0.0)
        has_relevelled |= controller.phase is C2Phase.LEVEL
        return has_relevelled and controller.phase is C2Phase.READY

    loop.run(sink_then_ready, limit_s=t_start + RUN_LIMIT_S)
    assert controller.phase is C2Phase.READY
    loop.run_for(HOLD_AFTER_READY_S)
    series = loop.record.arrays()
    assert (series["contact_N"][-1] > 0.0).all()
    assert series["force_N"][-1].min() >= controller.geometry.F_min_N
    assert all(result.is_grounded for result in controller.probe_history[-1])
    assert "probe_unresolved" not in [event.name for event in controller.events]
    assert len(controller.probe_history) >= 2  # the re-level after the sink probed again
    assert has_lifted, "the sink should lift RR before C2 recovers it"


# --- probe and combined contact judge (S6 check 7 in the reduced model) -----------------------


def test_probe_keeps_the_attitude_change_within_the_limit(flat_run) -> None:
    series = flat_run.record.arrays()
    in_probe = series["phase"] == str(C2Phase.PROBE)
    assert in_probe.any()
    start = int(np.argmax(in_probe))
    change_deg = series["attitude_deg"][in_probe] - series["attitude_deg"][start]
    assert np.abs(change_deg).max() <= PROBE_ATTITUDE_LIMIT_DEG


def test_probe_verdict_matches_the_pad_contact(flat_run) -> None:
    results = flat_run.controller.probe_history[0]
    assert all(result.is_grounded for result in results)
    # Ideal IMU: each grounded leg shows its kinematic attitude response.
    assert all(result.is_attitude_consistent for result in results)


def _probe_round_without_controller(loop: ClosedLoop, settings: ProbeSettings) -> ProbeRound:
    """Run one probe round on the plant directly (controller frozen)."""
    geometry = loop.controller.geometry
    period_s = loop.controller.period_s
    estimator = AttitudeEstimator()
    history: list[tuple[float, float]] = []
    rate_attitude = np.zeros(2)

    def probe_reading(measurements: Measurements) -> ProbeReading:
        nonlocal rate_attitude
        force = measurements.head_pressure_Pa * geometry.head_area_m2
        estimate = estimator.update(measurements.t_s, measurements.specific_force_m_s2)
        rate_attitude = rate_attitude + measurements.angular_rate_rad_s[:2] * period_s
        filtered = (estimate.roll_rad, estimate.pitch_rad)
        return ProbeReading(
            measurements.t_s,
            force,
            np.asarray(measurements.stroke_corrected_m),
            np.asarray(measurements.stroke_m),
            (float(rate_attitude[0]), float(rate_attitude[1])),
            filtered,
        )

    reading = probe_reading(loop.advance(np.zeros(4)))
    for _ in range(25):  # fill the attitude window and settle the filter on the new state
        history.append(reading.rate_attitude_rad)
        reading = probe_reading(loop.advance(np.zeros(4)))
    probe = ProbeRound(
        reading,
        settings,
        geometry.max_speed_m_s,
        loop.controller.period_s,
        geometry.load_sensitivity_diag_N_m,
        geometry.attitude_sensitivity_rad_m,
        history,
        load_band_limits_N=(loop.controller.seal_band_N, geometry.F_min_N),
    )
    command = probe.step(reading)
    while not probe.is_finished and loop.plant.t < RUN_LIMIT_S + 60.0:
        reading = probe_reading(loop.advance(command))
        command = probe.step(reading)
    return probe


def _sink_rr(loop: ClosedLoop, settle_s: float) -> None:
    """Sink the RR floor 30 mm over 5 s and hold ``settle_s`` (controller frozen)."""
    plant = loop.plant
    t_start = plant.t
    sink_steps = int(round((SINK_RAMP_S + settle_s) / loop.controller.period_s))
    for _ in range(sink_steps):
        plant.goff[RR] = LIFTING_SINK_M * min(1.0, (plant.t - t_start) / SINK_RAMP_S)
        loop.advance(np.zeros(4))


@pytest.fixture(scope="module")
def lifted_rr_loop() -> ClosedLoop:
    """Levelled machine whose RR floor then sank 30 mm: RR in the air, controller frozen."""
    loop = levelled(c2_loop())
    _sink_rr(loop, SINK_SETTLE_S)
    assert loop.record.pad_contact_force_N[-1][RR] == 0.0
    return loop


def _assert_rr_found_lifted(loop: ClosedLoop, probe: ProbeRound) -> None:
    contact = loop.record.arrays()["contact_N"]
    geometry = loop.controller.geometry
    assert (contact[-1] > 0.0).tolist() == [True, True, True, False]
    assert [result.is_grounded for result in probe.results] == [True, True, True, False]
    # R5 (H5a / D5): the first probe of the levelling measured F_band = 1 kN (no seal
    # friction; 2.2-2.4 kN with the probe's estimation residue), so the RR reading (-W_rod)
    # is surely below F_min (ambiguous with 13 kN).
    assert 1e3 <= loop.controller.seal_band_N < 5e3
    assert probe.results[RR].load_band is LoadBand.BELOW
    assert not probe.results[RR].is_grounded_by_stiffness
    # Q2: the -W_rod midpoint estimate puts RR first whatever the verdict.
    guard_level = geometry.F_min_N + loop.controller.config.thresholds.guard_margin_N
    assert probe.results[RR].load_estimate_N < guard_level


def test_combined_verdict_finds_the_lifted_leg(lifted_rr_loop) -> None:
    """Truth: RR in the air. The RR reading (-W_rod) was only 'ambiguous' with the 13 kN band
    (R4.1) and is 'below' with the measured R5 band; the default verdict (trapezoid probe,
    R4.1 Q1 gate, K1) says FL, FR, RL grounded, RR lifted (spec 21.3 Q3: the R4 trapezoid
    without Q1 read a false RR attitude response)."""
    probe = _probe_round_without_controller(lifted_rr_loop, ProbeSettings())
    _assert_rr_found_lifted(lifted_rr_loop, probe)


# Spec 21.3 Q3: settle phases of the three-leg teeter (1.25-2.12 Hz) at the probe start.
LIFTED_SETTLE_TIMES_S = (12.0, 18.0, 24.0)


@pytest.mark.parametrize("auger_level", ["top", "middle", "bottom"])
def test_lifted_rr_is_found_at_every_settle_phase(auger_level) -> None:
    """Q3: RR 30 mm in the air, default probe, three settle times per auger level."""
    loop = levelled(c2_loop(auger_level=auger_level))
    _sink_rr(loop, LIFTED_SETTLE_TIMES_S[0])
    settled_s = LIFTED_SETTLE_TIMES_S[0]
    for settle_s in LIFTED_SETTLE_TIMES_S:
        for _ in range(int(round((settle_s - settled_s) / loop.controller.period_s))):
            loop.advance(np.zeros(4))
        settled_s = settle_s
        trial = copy.deepcopy(loop)
        probe = _probe_round_without_controller(trial, ProbeSettings())
        _assert_rr_found_lifted(trial, probe)


# --- C8 skeleton on the same boundary ---------------------------------------------------------


def test_c8_skeleton_runs_on_the_same_boundary() -> None:
    """The C8 skeleton drives the same plant through the same Measurements / Command types.

    Only the boundary is checked; C8's levelling quality is not part of this task (skeleton).
    """
    params = load_params()
    controller = C8Controller.from_params(params)
    loop = ClosedLoop(settled_plant(), controller, controller.geometry.head_area_m2)
    loop.run(lambda: controller.phase is not C8Phase.TOUCH, limit_s=40.0)
    assert controller.phase is C8Phase.ATTITUDE
    loop.run_for(5.0)
    assert np.all(np.isfinite(loop.command_m_s))
    assert loop.command_m_s.min() >= 0.0  # extend-only
    assert math.isfinite(loop.plant.attitude()[0])
