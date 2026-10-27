"""C2 FAULT_REGROUND and the D1'' applicability of control spec rev. 64 / 65 (P-S8-24 T1-T7,
P-S8-25 T6 update, T6-4a..c, T9-T12, P-S8-23 ②; user decisions U-S8-68 .. U-S8-70 of
2026-10-27).

Synthetic 10 Hz rig on the bench of ``test_c2_r8d1.py`` (no CHECK, pressure judge, soil
response off), with a rod-side pressure (so the two-pressure diagnosis D1 runs) and IMU samples
(so D1'' and the Newton cue have ``f_z``). Every leg reads ``STEADY_LOAD_N`` until a case
changes it; a head-sensor fault is a sustained +150 bar jump.

The rig runs the R8 preset, i.e. the rev. 65 corrections (``reground_config``); the rev. 64
rules (target-only contact, raw-attitude abort, no cue (d), raw plane residual, D1 steps judged
after a fault) are the class defaults of the rev. 65 keys and are tested on
``rev64_config``.

* T1 off: FAULT at once, as before; T2 nothing lifted: the outputs of the fault sample on are
  those of a controller without FAULT_REGROUND (G4-7);
* T3 (rev. 64) a healthy leg lifted (lower estimate -3 kN on two samples) and another leg's
  head fault: that leg alone at 0.25 ``v_max`` until ``F_min + 5 kN`` on three samples;
* T4 (rev. 64) the faulty leg lifted (Newton estimate below ``F_min``): 0.15 ``v_max`` until
  the relative Newton load reads ``F_min + 5 kN`` on two samples;
* T5 travel and time limits; T6 abort conditions (rev. 65: no attitude abort, only non-step
  faults of other legs; 4a..c the rod-side branch of the 345 bar abort); T7 pickles;
* T9 the four-leg contact with the 1.0 s hold; T10 cue (d); T11 the D1 step rule suspended
  after a head fault; T12 the scaled plane gap;
* P-S8-23 ②: with the soil response on, D1'' follows the LOC and the re-contact watch.

T8 (the reduced closed loop ``r64_g4_closed_loop.py`` with ``R64_VARIANTS=py`` against the
control candidate) runs outside the unit tests (spec rev. 65 335.2).
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import dataclass, field, replace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    PERIOD_S,
    READY_SETTLE_PERIODS,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    bench_config,
    operating_strokes,
    up_in_body,
)

from outrigger_sim.control.c2 import (
    STROKE_END_MARGIN_M,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    SoilResponseSettings,
    _RunState,
)
from outrigger_sim.control.fault_reground import (
    ABORT_EVENT,
    CONTACT_EVENT,
    END_EVENT,
    LIMIT_EVENT,
    START_EVENT,
    ContactRule,
    FaultRegroundSettings,
    RegroundEnd,
    ratio_lower_bound,
)
from outrigger_sim.control.two_pressure import STEP_SUSPENDED_EVENT
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.signals import Measurements

FL, FR, RL, RR = (LEG_ORDER.index(name) for name in ("FL", "FR", "RL", "RR"))
BAR_PA = 1e5
ROD_PA = 2.0 * BAR_PA
HEAD_JUMP_PA = 150.0 * BAR_PA
"""Spec 323.8: a sustained +150 bar jump of one head sensor."""
OUT_OF_RANGE_JUMP_PA = 400.0 * BAR_PA
"""A head reading beyond the 0-400 bar sensor range (D1 range fault, not a step)."""
OVER_WARNING_PA = 346.0 * BAR_PA
"""Just above the 345 bar warnings of abort 4."""
LIFTED_LOAD_N = -3e3
"""T3: a healthy leg reading 3 kN below zero (lifted beyond the seal band)."""
HOLD_SAMPLES = 10
"""Spec rev. 65 332.2: contact confirmed after 10 samples (1.0 s) in a row."""
RECORDED_GAP_M = 0.0178
"""Spec rev. 65 329 ④: the largest recorded gap (RL, 218.5)."""
IMU_SAMPLES = 10
TOLERANCE = 1e-12


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def reground_config(**fault_changes) -> C2Config:
    """The bench preset (FAULT_REGROUND on with the rev. 65 corrections, ``with_10hz_d1``)."""
    config = bench_config()
    assert config.fault_reground.enable
    return replace(config, fault_reground=replace(config.fault_reground, **fault_changes))


def rev64_config(**fault_changes) -> C2Config:
    """The bench preset with the rev. 65 keys at their class defaults (the rev. 64 rules)."""
    defaults = FaultRegroundSettings()
    config = reground_config(
        attitude_abort=True,
        contact_rule=defaults.contact_rule,
        own_pre_fault_cue=defaults.own_pre_fault_cue,
        plane_gap_scaled=defaults.plane_gap_scaled,
        **fault_changes,
    )
    two_pressure = replace(config.two_pressure, suspend_steps_after_head_fault=False)
    return replace(config, two_pressure=two_pressure)


def rig_measurements(
    t_s: float,
    geometry: C2Geometry,
    loads_N: np.ndarray,
    strokes_m: np.ndarray,
    *,
    rod_Pa: np.ndarray,
    head_jump_Pa: np.ndarray,
    tilt_rad: tuple[float, float],
) -> Measurements:
    """Net forces ``loads_N`` as two pressures (rod side ``rod_Pa``), plus a head jump."""
    head_Pa = (np.asarray(loads_N) + rod_Pa * geometry.annulus_area_m2) / geometry.head_area_m2
    up = up_in_body(tilt_rad)
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=up,
        angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=head_Pa + head_jump_Pa,
        stroke_m=strokes_m.copy(),
        stroke_corrected_m=strokes_m.copy(),
        rod_pressure_Pa=rod_Pa.copy(),
        imu_specific_force_samples_m_s2=np.tile(up, (IMU_SAMPLES, 1)),
        imu_angular_rate_samples_rad_s=np.zeros((IMU_SAMPLES, 3)),
    )


@dataclass
class Rig:
    """10 Hz rig: readings set per case; strokes integrate the returned (delayed) commands
    when ``moves_strokes``."""

    controller: C2Controller
    geometry: C2Geometry
    strokes_m: np.ndarray
    loads_N: np.ndarray = field(default_factory=lambda: np.full(4, STEADY_LOAD_N))
    rod_Pa: np.ndarray = field(default_factory=lambda: np.full(4, ROD_PA))
    head_jump_Pa: np.ndarray = field(default_factory=lambda: np.zeros(4))
    tilt_rad: tuple[float, float] = (0.0, 0.0)
    moves_strokes: bool = False
    t_s: float = 0.0
    computed: list[np.ndarray] = field(default_factory=list)
    returned: list[np.ndarray] = field(default_factory=list)
    phases: list[C2Phase] = field(default_factory=list)

    def step(self, loads_N: np.ndarray | None = None) -> np.ndarray:
        if loads_N is not None:
            self.loads_N = np.asarray(loads_N, dtype=float)
        self.t_s = round(self.t_s + PERIOD_S, 10)
        reading = rig_measurements(self.t_s, self.geometry, self.loads_N, self.strokes_m,
                                   rod_Pa=self.rod_Pa, head_jump_Pa=self.head_jump_Pa,
                                   tilt_rad=self.tilt_rad)
        command = np.array(self.controller.update(reading).leg_speed_m_s)
        if self.moves_strokes:
            self.strokes_m = self.strokes_m + command * PERIOD_S
        self.returned.append(command)
        self.computed.append(self.controller.computed_output_m_s)
        self.phases.append(self.controller.phase)
        return self.controller.computed_output_m_s

    def run_while(self, phase: C2Phase, limit_s: float = 200.0) -> None:
        while self.controller.phase is phase and self.t_s < limit_s:
            self.step()

    def jump_head(self, leg: int, jump_Pa: float = HEAD_JUMP_PA) -> None:
        self.head_jump_Pa = self.head_jump_Pa.copy()
        self.head_jump_Pa[leg] = jump_Pa

    def set_rod(self, leg: int, rod_Pa: float) -> None:
        self.rod_Pa = self.rod_Pa.copy()
        self.rod_Pa[leg] = rod_Pa

    def names(self, prefix: str = "") -> list[str]:
        return [event.name for event in self.controller.events if event.name.startswith(prefix)]


def ready_rig(geometry: C2Geometry, config: C2Config) -> Rig:
    """Touch down, level and settle in READY (as ``test_c2_r8d1.ready_bench``)."""
    rig = Rig(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        rig.step()
    assert rig.controller.phase is C2Phase.LEVEL
    rig.run_while(C2Phase.LEVEL)
    rig.run_while(C2Phase.DONE)
    assert rig.controller.phase is C2Phase.READY
    for _ in range(READY_SETTLE_PERIODS):
        rig.step()
    assert rig.controller.phase is C2Phase.READY
    return rig


def with_load(leg: int, load_N: float) -> np.ndarray:
    loads = np.full(4, STEADY_LOAD_N)
    loads[leg] = load_N
    return loads


def lift_and_fault(rig: Rig, lifted_leg: int, faulty_leg: int) -> None:
    """The healthy ``lifted_leg`` reads -3 kN on two samples, the second with the head fault
    of ``faulty_leg`` (the fault sample)."""
    rig.step(with_load(lifted_leg, LIFTED_LOAD_N))
    rig.jump_head(faulty_leg)
    rig.step()


def speed(geometry: C2Geometry, fraction: float) -> float:
    return fraction * geometry.max_speed_m_s


def extending(geometry: C2Geometry, leg: int, fraction: float) -> np.ndarray:
    """Outputs with ``leg`` alone extending at ``fraction v_max``."""
    speeds = np.zeros(4)
    speeds[leg] = speed(geometry, fraction)
    return speeds


def run_meta(rig: Rig) -> dict:
    return rig.controller.meta()["fault_reground"]["run"]


def end_reason(rig: Rig) -> str:
    return run_meta(rig)["end_reason"]


# --- settings ------------------------------------------------------------------------------------


def test_preset_turns_the_rev65_keys_on() -> None:
    """Spec rev. 65 332.5: class defaults = rev. 64 (attitude abort off), R8 preset new."""
    defaults = FaultRegroundSettings()
    assert not defaults.attitude_abort
    assert defaults.contact_rule is ContactRule.TARGET_ONLY
    assert defaults.hold_confirm_samples == HOLD_SAMPLES
    assert not defaults.own_pre_fault_cue and not defaults.plane_gap_scaled
    preset = reground_config()
    settings = preset.fault_reground
    assert not settings.attitude_abort
    assert settings.contact_rule is ContactRule.ALL_LEGS_HOLD
    assert settings.hold_confirm_samples == HOLD_SAMPLES
    assert settings.own_pre_fault_cue and settings.plane_gap_scaled
    assert preset.two_pressure.suspend_steps_after_head_fault
    assert not C2Config().two_pressure.suspend_steps_after_head_fault
    assert settings.to_meta()["contact_rule"] == "all_legs_hold"
    json.dumps(settings.to_meta())


# --- T1 / T2: off, and nothing to re-ground -----------------------------------------------------


def test_t1_off_stops_at_the_fault_sample(geometry) -> None:
    rig = ready_rig(geometry, reground_config(enable=False))
    lift_and_fault(rig, RR, FL)
    assert rig.controller.phase is C2Phase.FAULT
    np.testing.assert_array_equal(rig.computed[-1], 0.0)
    assert rig.names("fault_reground") == []
    assert run_meta(rig) is None
    for _ in range(5):
        np.testing.assert_array_equal(rig.step(), 0.0)


def test_t2_no_lifted_leg_is_the_fault_stop_bit_for_bit(geometry) -> None:
    """G4-7: every leg loaded at the fault; outputs and events equal the run without
    FAULT_REGROUND from the fault sample on (the run is still recorded in the meta)."""
    rigs = [ready_rig(geometry, reground_config(enable=is_on)) for is_on in (False, True)]
    for rig in rigs:
        rig.jump_head(FR)
        for _ in range(8):
            rig.step()
    off, on = rigs
    np.testing.assert_array_equal(np.array(on.returned), np.array(off.returned))
    np.testing.assert_array_equal(np.array(on.computed), np.array(off.computed))
    assert on.names() == off.names()
    assert on.controller.phase is C2Phase.FAULT
    run = run_meta(on)
    assert run["end_reason"] == "no_target" and run["targets"] == []
    assert run["fault_legs"] == ["FR"]
    assert on.names(ABORT_EVENT) == []


def test_two_head_faults_at_once_stop_at_once(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    rig.step(with_load(RR, LIFTED_LOAD_N))
    rig.jump_head(FL)
    rig.jump_head(FR)
    rig.step()
    assert rig.controller.phase is C2Phase.FAULT
    assert rig.names(START_EVENT) == []


def test_fault_before_level_stops_at_once(geometry) -> None:
    """Spec 323.2: FAULT_REGROUND starts only once the machine stands on its legs."""
    rig = Rig(C2Controller(geometry, reground_config()), geometry, operating_strokes(geometry))
    rig.step()
    assert rig.controller.phase is C2Phase.TOUCH
    rig.jump_head(FL)
    rig.step()
    assert rig.controller.phase is C2Phase.FAULT


# --- T3: healthy-sensor leg (rev. 64 contact) ---------------------------------------------------


def test_t3_healthy_lifted_leg_is_regrounded_alone(geometry) -> None:
    rig = ready_rig(geometry, rev64_config())
    lift_and_fault(rig, RR, FL)
    controller = rig.controller
    assert controller.phase is C2Phase.FAULT_REGROUND
    assert rig.names(START_EVENT) == [f"{START_EVENT}:RR"]
    np.testing.assert_array_equal(rig.computed[-1], 0.0)  # the fault sample stops every leg
    expected = extending(geometry, RR, 0.25)
    for _ in range(2):  # RR still lifted: it alone extends at 0.25 v_max
        np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)
    contact_N = geometry.F_min_N + 5e3
    rig.step(with_load(RR, contact_N + 1.0))
    rig.step()
    assert rig.names(CONTACT_EVENT) == []
    np.testing.assert_allclose(rig.computed[-1], expected, rtol=0, atol=TOLERANCE)
    np.testing.assert_array_equal(rig.step(), 0.0)  # third sample at the level: contact
    assert rig.names(CONTACT_EVENT) == [f"{CONTACT_EVENT}:RR"]
    assert controller.phase is C2Phase.FAULT_REGROUND
    np.testing.assert_array_equal(rig.step(), 0.0)
    assert controller.phase is C2Phase.FAULT
    assert rig.names(END_EVENT) == [f"{END_EVENT}:1/1"]
    assert rig.names(ABORT_EVENT) == []
    run = run_meta(rig)
    assert run["end_reason"] == "done"
    (target,) = run["targets"]
    assert (target["leg"], target["sensor"], target["outcome"]) == ("RR", "healthy", "contact")
    assert target["cues"] == ["lower_bound"]
    assert run["protected_legs"] == ["FR", "RL"]


def test_t3_one_low_sample_is_no_target(geometry) -> None:
    """323.3: a healthy leg needs two samples below 0 N (a rocking dip is no target)."""
    rig = ready_rig(geometry, reground_config())
    rig.jump_head(FL)
    rig.step(with_load(RR, LIFTED_LOAD_N))
    assert rig.controller.phase is C2Phase.FAULT
    assert end_reason(rig) == "no_target"


def test_faulty_head_reading_is_held_at_its_value_before_the_fault(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    lift_and_fault(rig, RR, FL)
    rig.step()
    held = rig.controller.meta()["two_pressure"]["held_head_Pa"]
    head_before_Pa = (STEADY_LOAD_N + ROD_PA * geometry.annulus_area_m2[FL]) / (
        geometry.head_area_m2[FL])
    assert held == {"FL": pytest.approx(head_before_Pa)}
    assert rig.controller._state.last_cylinder_force_N[FL] == pytest.approx(STEADY_LOAD_N)


# --- T4: faulty-sensor leg (rev. 64 contact) ----------------------------------------------------


def faulty_lift(rig: Rig) -> None:
    """RR lifts (the other three take its load: Newton estimate 0 N), then its head jumps; the
    0.3 s window of the Newton cue holds the two lifted samples and the fault sample."""
    loads = np.array([STEADY_LOAD_N + 20e3, STEADY_LOAD_N + 40e3, STEADY_LOAD_N + 20e3, 0.0])
    rig.step(loads)
    rig.step()
    rig.jump_head(RR)
    rig.step()


def test_t4_faulty_lifted_leg_extends_slowly_until_the_relative_newton_load(geometry) -> None:
    rig = ready_rig(geometry, rev64_config())
    faulty_lift(rig)
    controller = rig.controller
    assert controller.phase is C2Phase.FAULT_REGROUND
    run = run_meta(rig)
    (target,) = run["targets"]
    assert (target["leg"], target["sensor"]) == ("RR", "faulty")
    assert "newton" in target["cues"]
    assert run["faulty_cue_values"]["RR"]["newton_load_N"] == pytest.approx(0.0, abs=1e-6)
    expected = extending(geometry, RR, 0.15)
    np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)  # start (t_0)
    # RR takes 20 kN back from the other three: the 0.2 s means see 10 kN, then 20 kN.
    taken_back = rig.loads_N - np.array([5e3, 10e3, 5e3, 0.0])
    np.testing.assert_allclose(rig.step(taken_back), expected, rtol=0, atol=TOLERANCE)
    np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)  # 1st at level
    np.testing.assert_array_equal(rig.step(), 0.0)  # 2nd sample at F_min + 5 kN: contact
    assert rig.names(CONTACT_EVENT) == [f"{CONTACT_EVENT}:RR"]
    rig.step()
    assert controller.phase is C2Phase.FAULT
    assert rig.names(END_EVENT) == [f"{END_EVENT}:1/1"]


def test_t4_loaded_faulty_leg_is_no_target(geometry) -> None:
    """Newton estimate 80 kN, rod side, plane and its own readings quiet: no cue, FAULT."""
    rig = ready_rig(geometry, reground_config())
    rig.jump_head(RR)
    rig.step()
    assert rig.controller.phase is C2Phase.FAULT
    values = run_meta(rig)["faulty_cue_values"]["RR"]
    assert values["newton_load_N"] == pytest.approx(STEADY_LOAD_N, rel=1e-9)
    assert values["rod_rise_Pa"] == pytest.approx(0.0, abs=1e-6)
    assert values["own_pre_fault_N"] == [pytest.approx(STEADY_LOAD_N, rel=0.1)] * 2


def test_t4_rod_side_rise_cue(geometry) -> None:
    """323.3 (b): a locked rod side up by ``0.5 R_lb(s) p_h,lock`` marks the faulty leg."""
    rig = ready_rig(geometry, reground_config())
    controller = rig.controller
    head_lock_Pa, rod_lock_Pa = controller._state.leg_lock_pressures_Pa[RR]
    stroke = float(rig.strokes_m[RR])
    rise_Pa = 0.5 * ratio_lower_bound(stroke, geometry.stroke_max_m) * head_lock_Pa + 1.0
    run = controller._new_fault_reground_run(rig.t_s, (RR,))
    assert run.faulty_cue_values["RR"]["rod_rise_Pa"] == pytest.approx(0.0, abs=1e-6)
    for sample in controller._state.fault_reground_history:
        object.__setattr__(sample, "rod_pressure_Pa", np.full(4, rod_lock_Pa + rise_Pa))
    run = controller._new_fault_reground_run(rig.t_s, (RR,))
    assert [target.cues for target in run.targets] == [("rod_rise",)]


def test_t4_plane_residual_cue_and_gap_estimate_rev64(geometry) -> None:
    """323.3 (c) of rev. 64: the raw plane residual sees RR 12 mm up -> cue and a 17 mm
    travel limit."""
    rig = ready_rig(geometry, rev64_config())
    controller = rig.controller
    residuals = np.array([-0.012, 0.012, -0.012, 0.012])
    controller._support_shadow.leg_residual_changes_m = lambda: residuals
    run = controller._new_fault_reground_run(rig.t_s, (RR,))
    (target,) = run.targets
    assert target.cues == ("plane",)
    assert target.gap_m == pytest.approx(0.012)
    assert target.max_travel_m == pytest.approx(0.017)


# --- T5: limits ---------------------------------------------------------------------------------


def test_t5_travel_limit_without_gap_estimate(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    rig.moves_strokes = True
    lift_and_fault(rig, RR, FL)
    while rig.controller.phase is C2Phase.FAULT_REGROUND and rig.t_s < 100.0:
        rig.step()
    assert rig.names(LIMIT_EVENT) == [f"{LIMIT_EVENT}:RR:travel"]
    (target,) = run_meta(rig)["targets"]
    assert target["max_travel_m"] == pytest.approx(0.030)
    assert 0.030 <= target["travel_m"] < 0.030 + speed(geometry, 0.25) * PERIOD_S + 1e-12
    assert target["duration_s"] < 8.0
    assert target["hold_count"] == 0
    assert rig.names(END_EVENT) == [f"{END_EVENT}:0/1"]
    assert rig.names(ABORT_EVENT) == []  # done: every target ended


def test_t5_time_limit_per_leg_and_total(geometry) -> None:
    """Strokes still (the leg never gets anywhere): RR stops after 8 s, RL after the 15 s of
    the whole run (its own 8 s are not up)."""
    rig = ready_rig(geometry, reground_config())
    loads = np.full(4, STEADY_LOAD_N)
    loads[[RL, RR]] = LIFTED_LOAD_N
    rig.step(loads)
    rig.jump_head(FL)
    rig.step()
    fault_s = rig.t_s
    assert rig.names(START_EVENT) == [f"{START_EVENT}:RL,RR"]
    rig.run_while(C2Phase.FAULT_REGROUND)
    assert rig.names(LIMIT_EVENT) == [f"{LIMIT_EVENT}:RL:time", f"{LIMIT_EVENT}:RR:time"]
    run = run_meta(rig)
    assert run["end_reason"] == "total_time"
    assert run["end_s"] == pytest.approx(fault_s + 15.0)
    first, second = run["targets"]
    assert first["duration_s"] == pytest.approx(8.0)
    assert second["duration_s"] < 8.0
    assert rig.names(ABORT_EVENT) == [f"{ABORT_EVENT}:total_time"]


def test_t5_gap_estimate_shortens_the_travel_limit() -> None:
    settings = FaultRegroundSettings()
    assert settings.travel_limit_m(None) == 0.030
    assert settings.travel_limit_m(0.012) == pytest.approx(0.017)
    assert settings.travel_limit_m(0.040) == 0.030


# --- T6: abort conditions -----------------------------------------------------------------------


def started_reground(geometry: C2Geometry, config: C2Config | None = None) -> Rig:
    rig = ready_rig(geometry, config or reground_config())
    lift_and_fault(rig, RR, FL)
    rig.step()  # RR moving
    assert rig.controller.phase is C2Phase.FAULT_REGROUND
    return rig


def assert_aborted(rig: Rig, reason: RegroundEnd) -> None:
    assert rig.controller.phase is C2Phase.FAULT
    assert end_reason(rig) == str(reason)
    assert rig.names(ABORT_EVENT) == [f"{ABORT_EVENT}:{reason}"]


def test_t6_1_protected_leg_below_f_min_four_samples_goes_on(geometry) -> None:
    """323.9 ④: a rocking dip of 0.4 s on a healthy leg does not stop the re-ground."""
    rig = started_reground(geometry)
    low = rig.loads_N.copy()
    low[FR] = geometry.F_min_N - 1.0
    for _ in range(4):
        rig.step(low)
    rig.step(with_load(RR, LIFTED_LOAD_N))
    assert rig.controller.phase is C2Phase.FAULT_REGROUND
    assert rig.controller._state.fault_reground.protect_low_counts[FR] == 0


def test_t6_1_protected_leg_below_f_min_five_samples(geometry) -> None:
    rig = started_reground(geometry)
    low = rig.loads_N.copy()
    low[FR] = geometry.F_min_N - 1.0
    for _ in range(4):
        rig.step(low)
        assert rig.controller.phase is C2Phase.FAULT_REGROUND
    rig.step(low)
    assert_aborted(rig, RegroundEnd.PROTECTED_LEG_LOW)
    assert rig.names(END_EVENT) == [f"{END_EVENT}:0/1"]


ROCKING_PITCH_RAD = math.radians(0.38)
ROCKING_FREQUENCY_HZ = 1.5
"""323.9 ④ test: passive rocking 0.38 deg at 1.5 Hz (event window 220.2)."""
ATTITUDE_STEP_RAD = math.radians(0.6)


def test_t6_2_rocking_attitude_goes_on_rev64(geometry) -> None:
    rig = started_reground(geometry, rev64_config())
    start_s = rig.t_s
    for _ in range(30):
        phase_rad = 2.0 * math.pi * ROCKING_FREQUENCY_HZ * (rig.t_s + PERIOD_S - start_s)
        rig.tilt_rad = (0.0, ROCKING_PITCH_RAD * math.sin(phase_rad))
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND


def test_t6_2_attitude_step_of_0_6_deg_rev64(geometry) -> None:
    """The 0.5 s mean of a 0.6 deg step passes 0.5 deg on the fifth sample (0.48 on the
    fourth)."""
    rig = started_reground(geometry, rev64_config())
    rig.tilt_rad = (0.0, ATTITUDE_STEP_RAD)
    for _ in range(4):
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND
    rig.step()
    assert_aborted(rig, RegroundEnd.ATTITUDE)


def test_t6_2_no_attitude_abort_records_the_filtered_change(geometry) -> None:
    """Rev. 65 332.1: a 0.6 deg attitude step does not stop the re-ground; the largest change
    of the levelling attitude against the fault sample goes to the meta."""
    rig = started_reground(geometry)
    assert run_meta(rig)["max_filtered_attitude_change_rad"] < 1e-9
    rig.tilt_rad = (0.0, ATTITUDE_STEP_RAD)
    for _ in range(20):
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND
    change_rad = run_meta(rig)["max_filtered_attitude_change_rad"]
    assert 0.0 < change_rad < ATTITUDE_STEP_RAD
    state = rig.controller._state
    fault_pitch_rad = state.fault_reground.fault_filtered_attitude_rad[1]
    assert change_rad == pytest.approx(abs(state.pitch_rad - fault_pitch_rad))


def test_t6_3_another_head_step_rev64(geometry) -> None:
    """Rev. 64: any new head fault of another leg, a step too, stops the re-ground."""
    rig = started_reground(geometry, rev64_config())
    rig.jump_head(FR)
    rig.step()
    assert_aborted(rig, RegroundEnd.NEW_HEAD_FAULT)


def test_t6_3_another_head_out_of_range(geometry) -> None:
    """Rev. 65 332.1 abort 3: a non-step fault (range) of another leg stops the re-ground."""
    rig = started_reground(geometry)
    rig.jump_head(FR, OUT_OF_RANGE_JUMP_PA)
    rig.step()
    assert_aborted(rig, RegroundEnd.NEW_HEAD_FAULT)
    assert "INFO_HEAD_PRESSURE_FAULT_REASON:FR:D1_range" in rig.names()


def test_t6_4_healthy_head_above_345_bar(geometry) -> None:
    rig = started_reground(geometry)
    target_N = OVER_WARNING_PA * geometry.head_area_m2[FR] - ROD_PA * geometry.annulus_area_m2[FR]
    loads = rig.loads_N.copy()
    while loads[FR] < target_N:  # below the 100 bar step limit per sample
        loads[FR] = min(loads[FR] + 50.0 * BAR_PA * geometry.head_area_m2[FR], target_N)
        rig.step(loads)
        if loads[FR] < target_N:
            assert rig.controller.phase is C2Phase.FAULT_REGROUND
    assert_aborted(rig, RegroundEnd.PRESSURE_WARNING)


def test_t6_4a_valid_rod_side_above_345_bar(geometry) -> None:
    """Rev. 65 329: a valid rod-side reading at 346 bar stops the re-ground (its head stays
    far below 345 bar)."""
    rig = started_reground(geometry)
    rig.set_rod(FR, OVER_WARNING_PA)
    rig.step()
    assert FR not in rig.controller._pressures.fallback_legs
    assert rig.controller._state.last_reading.head_only_force_N[FR] < (
        300.0 * BAR_PA * geometry.head_area_m2[FR])
    assert_aborted(rig, RegroundEnd.PRESSURE_WARNING)


def test_t6_4b_fallback_leg_rod_side_above_345_bar_goes_on(geometry) -> None:
    """A rod sensor already in fallback is not trusted: 346 bar on it does not stop."""
    rig = started_reground(geometry)
    rig.controller._pressures._fall_back(FR, "test")
    rig.set_rod(FR, OVER_WARNING_PA)
    for _ in range(3):
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND


def test_t6_4c_faulty_leg_head_above_345_bar_goes_on(geometry) -> None:
    """The faulty leg's own head reading (346 bar, within the sensor range) does not stop."""
    rig = started_reground(geometry)
    head_steady_Pa = (STEADY_LOAD_N + ROD_PA * geometry.annulus_area_m2[FL]) / (
        geometry.head_area_m2[FL])
    rig.jump_head(FL, OVER_WARNING_PA - head_steady_Pa)
    for _ in range(3):
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND


def test_t6_5_moving_leg_near_the_stroke_end(geometry) -> None:
    rig = started_reground(geometry)
    rig.strokes_m = rig.strokes_m.copy()
    rig.strokes_m[RR] = geometry.stroke_soft_max_m - STROKE_END_MARGIN_M - 0.010
    rig.step()
    assert_aborted(rig, RegroundEnd.STROKE_END)


# --- T9: four-leg contact with the hold ---------------------------------------------------------


def test_t9_passive_touch_down_with_the_partner_lifting_is_no_contact(geometry) -> None:
    """332.2: RR reads its contact level while its diagonal partner FL drops below
    ``F_min`` (a teeter): no contact, RR extends on."""
    rig = ready_rig(geometry, reground_config())
    lift_and_fault(rig, RR, FR)
    expected = extending(geometry, RR, 0.25)
    np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)
    teeter = with_load(RR, geometry.F_min_N + 5e3 + 1.0)
    teeter[FL] = geometry.F_min_N - 1.0
    for _ in range(3):
        np.testing.assert_allclose(rig.step(teeter), expected, rtol=0, atol=TOLERANCE)
    assert rig.names(CONTACT_EVENT) == []
    assert rig.controller._state.fault_reground.active_target.contact_samples_seen == 0


def test_t9_hold_and_confirm_after_ten_samples(geometry) -> None:
    """The leg stands while the condition holds, extends again when it breaks (count back to
    0) and the contact is confirmed on the tenth sample in a row."""
    rig = ready_rig(geometry, reground_config())
    lift_and_fault(rig, RR, FR)
    expected = extending(geometry, RR, 0.25)
    np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)
    at_contact = with_load(RR, geometry.F_min_N + 5e3 + 1.0)
    np.testing.assert_array_equal(rig.step(at_contact), 0.0)  # first sample: hold
    np.testing.assert_allclose(rig.step(with_load(RR, LIFTED_LOAD_N)), expected, rtol=0,
                               atol=TOLERANCE)  # broken: extend again
    for _ in range(HOLD_SAMPLES - 1):
        np.testing.assert_array_equal(rig.step(at_contact), 0.0)
        assert rig.names(CONTACT_EVENT) == []
    np.testing.assert_array_equal(rig.step(), 0.0)  # tenth in a row: contact
    assert rig.names(CONTACT_EVENT) == [f"{CONTACT_EVENT}:RR"]
    rig.step()
    assert rig.controller.phase is C2Phase.FAULT
    (target,) = run_meta(rig)["targets"]
    assert target["outcome"] == "contact" and target["hold_count"] == 2


def test_t9_faulty_non_target_newton_below_f_min_is_no_contact(geometry) -> None:
    """332.2: a faulty leg that is no target must keep ``F_min`` by its Newton estimate; with
    the others carrying the whole weight it does not, so RR extends on."""
    rig = ready_rig(geometry, reground_config())
    lift_and_fault(rig, RR, FR)
    monitor = rig.controller._pressures
    weight_N = monitor.d1_imu_mass_kg() * monitor.imu_specific_force_z_m_s2
    contact_N = geometry.F_min_N + 5e3 + 1.0
    loads = np.array([(weight_N - contact_N) / 2.0, STEADY_LOAD_N, (weight_N - contact_N) / 2.0,
                      contact_N])
    rig.step(loads)
    expected = extending(geometry, RR, 0.25)
    for _ in range(HOLD_SAMPLES + 2):
        np.testing.assert_allclose(rig.step(), expected, rtol=0, atol=TOLERANCE)
    assert rig.names(CONTACT_EVENT) == []


# --- T10: cue (d) -------------------------------------------------------------------------------


def own_lift_and_fault(rig: Rig, low_samples: int) -> None:
    """RR reads -3 kN on ``low_samples`` samples (the other legs unchanged, so the Newton
    estimate keeps RR loaded), then its head jumps."""
    for _ in range(low_samples):
        rig.step(with_load(RR, LIFTED_LOAD_N))
    rig.jump_head(RR)
    rig.step()


def test_t10_own_low_readings_before_the_fault_make_a_target(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    own_lift_and_fault(rig, 2)
    assert rig.controller.phase is C2Phase.FAULT_REGROUND
    run = run_meta(rig)
    (target,) = run["targets"]
    assert (target["leg"], target["sensor"]) == ("RR", "faulty")
    assert target["cues"] == ["own_pre_fault"]
    values = run["faulty_cue_values"]["RR"]
    assert values["newton_load_N"] > geometry.F_min_N
    assert all(load_N < 0.0 for load_N in values["own_pre_fault_N"])
    np.testing.assert_allclose(rig.step(), extending(geometry, RR, 0.15), rtol=0, atol=TOLERANCE)


def test_t10_one_low_reading_is_no_target(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    own_lift_and_fault(rig, 1)
    assert rig.controller.phase is C2Phase.FAULT
    assert end_reason(rig) == "no_target"


def test_t10_cue_off_in_rev64(geometry) -> None:
    rig = ready_rig(geometry, rev64_config())
    own_lift_and_fault(rig, 2)
    assert rig.controller.phase is C2Phase.FAULT
    assert "own_pre_fault_N" not in run_meta(rig)["faulty_cue_values"]["RR"]


# --- T11: D1 step rule suspended after a head fault ---------------------------------------------


def test_t11_step_of_another_head_after_the_fault_is_no_fault(geometry) -> None:
    rig = started_reground(geometry)
    assert rig.names(STEP_SUSPENDED_EVENT) == [f"{STEP_SUSPENDED_EVENT}:FL"]
    rig.jump_head(FR)  # +150 bar: a step, within the range
    for _ in range(3):
        rig.step()
        assert rig.controller.phase is C2Phase.FAULT_REGROUND
    assert rig.names("FAULT_HEAD_PRESSURE") == ["FAULT_HEAD_PRESSURE:FL"]
    assert rig.controller.meta()["two_pressure"]["d1_step_suspended_by"] == "FL"
    rig.jump_head(FR, OUT_OF_RANGE_JUMP_PA)  # a range fault is still judged
    rig.step()
    assert_aborted(rig, RegroundEnd.NEW_HEAD_FAULT)
    assert rig.names(STEP_SUSPENDED_EVENT) == [f"{STEP_SUSPENDED_EVENT}:FL"]


def test_t11_fault_without_target_suspends_too(geometry) -> None:
    """332.4: the suspension follows every confirmed head fault (FAULT at once as well)."""
    rig = ready_rig(geometry, reground_config())
    rig.jump_head(FR)
    rig.step()
    assert rig.controller.phase is C2Phase.FAULT
    assert rig.names(STEP_SUSPENDED_EVENT) == [f"{STEP_SUSPENDED_EVENT}:FR"]


def test_t11_rev64_keeps_the_step_rule(geometry) -> None:
    rig = started_reground(geometry, rev64_config())
    assert rig.names(STEP_SUSPENDED_EVENT) == []
    assert "d1_step_suspended_by" not in rig.controller.meta()["two_pressure"]


# --- T12: scaled plane gap ----------------------------------------------------------------------


def single_pad_residual_changes(geometry: C2Geometry, leg: int, gap_m: float) -> np.ndarray:
    """Residual changes of the four pads when ``leg`` alone is ``gap_m`` off the plane:
    ``(I - P) e_leg gap``."""
    plane_basis = np.column_stack([np.ones(4), geometry.pad_xy_m])
    residual_operator = np.eye(4) - plane_basis @ np.linalg.pinv(plane_basis)
    return residual_operator[:, leg] * gap_m


def test_t12_residual_diagonal_of_the_yaml_pads(geometry) -> None:
    """329 ④: ``(I - P)_ii`` 0.227 front, 0.273 rear."""
    controller = C2Controller(geometry, reground_config())
    diagonal = controller._support_shadow.residual_diagonal()
    np.testing.assert_allclose(diagonal, [0.227, 0.227, 0.273, 0.273], atol=1e-3)


def test_t12_recorded_gap_is_recovered_and_limits_the_travel(geometry) -> None:
    """RL 17.8 mm synthetic: the scaled gap reads 17.8 mm -> cue (c) and a 22.8 mm limit (the
    raw residual 4.87 mm would cut it at 9.9 mm)."""
    rig = ready_rig(geometry, reground_config())
    controller = rig.controller
    residuals = single_pad_residual_changes(geometry, RL, RECORDED_GAP_M)
    controller._support_shadow.leg_residual_changes_m = lambda: residuals
    gaps = controller._support_shadow.leg_gap_estimates_m()
    assert gaps[RL] == pytest.approx(RECORDED_GAP_M)
    run = controller._new_fault_reground_run(rig.t_s, (RL,))
    (target,) = run.targets
    assert target.cues == ("plane",)
    assert target.gap_m == pytest.approx(RECORDED_GAP_M)
    assert target.max_travel_m == pytest.approx(RECORDED_GAP_M + 0.005)
    assert run.faulty_cue_values["RL"]["plane_gap_m"] == pytest.approx(RECORDED_GAP_M)


def test_t12_raw_residual_of_rev64_cuts_the_limit(geometry) -> None:
    rig = ready_rig(geometry, rev64_config())
    controller = rig.controller
    residuals = single_pad_residual_changes(geometry, RL, RECORDED_GAP_M)
    controller._support_shadow.leg_residual_changes_m = lambda: residuals
    (target,) = controller._new_fault_reground_run(rig.t_s, (RL,)).targets
    assert target.max_travel_m == pytest.approx(0.273 * RECORDED_GAP_M + 0.005, abs=5e-5)


def test_t12_scaled_gap_below_5_mm_is_no_cue(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    controller = rig.controller
    residuals = single_pad_residual_changes(geometry, RL, 0.0049)
    controller._support_shadow.leg_residual_changes_m = lambda: residuals
    assert controller._new_fault_reground_run(rig.t_s, (RL,)).targets == []


# --- T7: pickles --------------------------------------------------------------------------------


def test_t7_config_pickled_before_p_s8_24_reads_off() -> None:
    old = object.__new__(C2Config)
    state = dict(C2Config().__dict__)
    del state["fault_reground"]
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.fault_reground == FaultRegroundSettings()
    assert not restored.fault_reground.enable


def test_t7_settings_pickled_before_p_s8_25_read_the_rev64_rules() -> None:
    old = object.__new__(FaultRegroundSettings)
    state = dict(replace(FaultRegroundSettings(), enable=True).__dict__)
    for key in ("attitude_abort", "contact_rule", "hold_confirm_samples", "own_pre_fault_cue",
                "plane_gap_scaled", "plane_gap_threshold_m"):
        del state[key]
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.enable
    assert restored.contact_rule is ContactRule.TARGET_ONLY
    assert not (restored.attitude_abort or restored.own_pre_fault_cue
                or restored.plane_gap_scaled)
    json.dumps(restored.to_meta())


def test_t7_run_state_pickled_before_p_s8_24_runs(geometry) -> None:
    rig = ready_rig(geometry, reground_config())
    state = rig.controller._state
    for name in ("fault_reground", "fault_reground_history", "leg_lock_pressures_Pa"):
        del state.__dict__[name]
    rig.controller._state = pickle.loads(pickle.dumps(state))
    assert isinstance(rig.controller._state, _RunState)
    assert rig.controller._state.fault_reground is None
    lift_and_fault(rig, RR, FL)
    assert rig.controller.phase is C2Phase.FAULT_REGROUND
    json.dumps(rig.controller.meta(), default=float)


def test_invalid_settings_are_rejected() -> None:
    with pytest.raises(ValueError):
        FaultRegroundSettings(speed_fraction_faulty=0.0)
    with pytest.raises(ValueError):
        FaultRegroundSettings(healthy_contact_samples=0)
    with pytest.raises(ValueError):
        FaultRegroundSettings(max_total_duration_s=-1.0)
    with pytest.raises(ValueError):
        FaultRegroundSettings(hold_confirm_samples=0)
    with pytest.raises(ValueError):
        FaultRegroundSettings(contact_rule="all_legs")


# --- P-S8-23 ②: D1'' applicability ---------------------------------------------------------------


def test_soil_on_d1_double_prime_follows_the_loc_and_the_recontact_watch(geometry) -> None:
    config = replace(reground_config(), soil=SoilResponseSettings(enable=True))
    controller = C2Controller(geometry, config)
    controller._state.phase = C2Phase.LEVEL
    assert not controller._is_crawler_lifted_for_d1()  # LEVEL without the LOC
    controller._soil_state().is_liftoff_confirmed = True
    assert controller._is_crawler_lifted_for_d1()
    controller._state.phase = C2Phase.FAULT
    assert controller._is_crawler_lifted_for_d1()  # the LOC, not the phase
    watch = controller._pressures._recontact_watch()
    watch.is_suspected = True
    assert not controller._is_crawler_lifted_for_d1()


def test_soil_off_keeps_the_phase_rule(geometry) -> None:
    """FAULT_REGROUND counts as lifted (rev. 65 332.4: entered from lifted phases only)."""
    controller = C2Controller(geometry, reground_config())
    for phase, expected in ((C2Phase.TOUCH, False), (C2Phase.LEVEL, True),
                            (C2Phase.READY, True), (C2Phase.FAULT_REGROUND, True),
                            (C2Phase.FAULT, False)):
        controller._state.phase = phase
        assert controller._is_crawler_lifted_for_d1() is expected
