"""C2 P-S8-28 of control spec rev. 70 369 (U-S8-78 (a) + (b), U-S8-79; user decision
2026-10-27, adopted candidate AG2c5): the LOC anchor, the stroke-budget guard, the named
stroke-end FAULT and the stroke-end re-ground (tests T1 .. T13 of 369.5).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (no CHECK, pressure judge; the bench strokes do
not follow the commands, so a case sets them). The soil response is on with the preset keys
(LOC anchor included) unless a case says otherwise; a LOC is forced through the soil state.
The closed-loop acceptance (``r70_p28_screen.py`` with the project controller against the rev. 70
AG2c5 hashes, 369.6) runs outside the unit tests.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_fault_reground import (  # same test folder
    lift_and_fault,
    ready_rig,
    reground_config,
    run_meta,
)
from test_c2_r8d1 import (  # same test folder
    NO_REAPPROACH,
    PERIOD_S,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    operating_strokes,
    ready_bench,
)

from outrigger_sim.control.c2 import (
    LIFT_GUARD_FAULT_EVENT,
    LIFT_GUARD_WARNING_EVENT,
    SOIL_EVENT_CLEARANCE_BIAS,
    SOIL_EVENT_LOC_ANCHOR,
    STROKE_END_FAULT_EVENT,
    STROKE_END_MARGIN_M,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    LiftGuardMode,
    LiftStrokeGuardSettings,
    RestoredLiftoff,
    SoilResponseSettings,
    _PlateauSample,
    _Reading,
    _RunState,
)
from outrigger_sim.control.fault_reground import (
    END_EVENT,
    START_EVENT,
    FaultRegroundRun,
    FaultRegroundSettings,
    RegroundEnd,
    RegroundTrigger,
)
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

FL, FR, RL, RR = (LEG_ORDER.index(name) for name in ("FL", "FR", "RL", "RR"))
GUARD_STROKE_MARGIN_M = 0.002
"""``extra_margin_m`` of the preset: ``s_g`` = 684.8 - 2 = 682.8 mm."""
ANCHOR_OFFSET_M = 0.005
HOLD_LIMIT_S = 3.0
LIFTED_READING_N = -3e3
"""A healthy leg reading 3 kN below zero (lifted beyond the seal band)."""
TOLERANCE_M = 1e-12
LEVEL_TILT_RAD = (math.radians(0.1), 0.0)
"""A roll error inside the conditional-integration band (0.01 .. 0.2 deg)."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def p28_config(**r8_changes) -> C2Config:
    """The bench preset with the soil response of the R8 preset (LOC anchor on)."""
    config = bench_config(**r8_changes)
    return replace(config, soil=C2Config().with_10hz_d1().soil)


def without_p28(config: C2Config) -> C2Config:
    """``config`` with every P-S8-28 key at its class default."""
    return replace(
        config,
        soil=replace(config.soil, loc_anchor_enable=False),
        lift_stroke_guard=LiftStrokeGuardSettings(),
        fault_reground=replace(config.fault_reground, stroke_end_entry=False),
    )


def event_names(controller: C2Controller, prefix: str) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(prefix)]


def guard_stroke_m(geometry: C2Geometry) -> float:
    return geometry.stroke_soft_max_m - STROKE_END_MARGIN_M - GUARD_STROKE_MARGIN_M


def force_liftoff(controller: C2Controller) -> None:
    """The LOC without a window (bias zero): the guard's precondition."""
    controller._soil_state().is_liftoff_confirmed = True


def level_bench(geometry: C2Geometry, config: C2Config, strokes_m: np.ndarray) -> Bench:
    """Touch down on ``operating_strokes``, then the bench reads ``strokes_m`` in LEVEL."""
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    bench.strokes_m = np.asarray(strokes_m, dtype=float).copy()
    return bench


def stroke_reading(
    t_s: float, motor_stroke_m: np.ndarray, rod_stroke_m: np.ndarray
) -> _Reading:
    loads = np.full(4, STEADY_LOAD_N)
    return _Reading(
        t_s=t_s,
        cylinder_force_N=loads,
        rod_stroke_m=np.asarray(rod_stroke_m, dtype=float),
        motor_stroke_m=np.asarray(motor_stroke_m, dtype=float),
        cylinder_force_lowpass_N=loads,
        cylinder_force_lower_N=loads,
        cylinder_force_upper_N=loads,
        head_only_force_N=loads,
    )


def plateau_sample(geometry: C2Geometry, strokes_m: np.ndarray, t_s: float = 5.0) -> _PlateauSample:
    """A ``t_P`` sample with the stroke-plane corner clearances of ``strokes_m`` and no tilt."""
    return _PlateauSample(
        t_s=t_s,
        mean_motor_stroke_m=float(np.mean(strokes_m)),
        load_sum_N=4 * STEADY_LOAD_N,
        corner_clearance_m=geometry.clearance_corners_m(strokes_m),
        raw_attitude_rad=(0.0, 0.0),
    )


def confirm_at(controller: C2Controller, sample: _PlateauSample, geometry: C2Geometry) -> None:
    controller._soil_state().settle_attitude_rad = (0.0, 0.0)
    weight_N = geometry.superstructure_mass_kg * STANDARD_GRAVITY_M_S2
    controller._confirm_liftoff(sample.t_s, [sample], weight_N)


class GuardRecorder(C2Controller):
    """C2 that keeps every output of the stroke-budget guard and the integrals around it."""

    def __init__(self, geometry: C2Geometry, config: C2Config) -> None:
        super().__init__(geometry, config)
        self.guard_outputs: list[np.ndarray] = []

    def _apply_lift_stroke_guard(self, reading, leg_speeds):
        guarded = super()._apply_lift_stroke_guard(reading, leg_speeds)
        if self._state.lift_guard_mode is not None:
            self.guard_outputs.append(np.array(guarded, dtype=float))
        return guarded


# --- T1 / T13 settings -------------------------------------------------------------------------


def test_t1_class_defaults_keep_the_old_behaviour() -> None:
    config = C2Config()
    assert not config.soil.loc_anchor_enable
    assert config.lift_stroke_guard == LiftStrokeGuardSettings()
    assert not config.lift_stroke_guard.enable
    assert not config.lift_stroke_guard.name_stroke_end_fault
    assert not config.fault_reground.stroke_end_entry
    assert _RunState.lift_stroke_limited is False  # class attribute (old pickles)
    assert FaultRegroundRun.trigger is RegroundTrigger.HEAD_FAULT


def test_t1_preset_on_a_level_bench_commands_as_without_p28(geometry) -> None:
    """Nothing of P-S8-28 acts on a level floor: the R8 bench run is bit for bit the run with
    every P-S8-28 key off (the unit tests and the harness hashes cover the rest)."""
    preset = ready_bench(geometry, bench_config())
    old = ready_bench(geometry, without_p28(bench_config()))
    np.testing.assert_array_equal(np.array(preset.outputs), np.array(old.outputs))


def test_t13_preset_values() -> None:
    preset = C2Config().with_10hz_d1()
    soil = preset.soil
    assert soil.loc_anchor_enable
    assert (soil.loc_anchor_deadzone_m, soil.loc_anchor_offset_m) == (0.020, 0.005)
    assert preset.lift_stroke_guard == LiftStrokeGuardSettings(
        enable=True,
        extra_margin_m=0.002,
        lookahead_periods=2,
        hold_limit_s=3.0,
        shift_clearance_margin_m=0.005,
        name_stroke_end_fault=True,
        soil_stop=True,  # P-S8-36 SGS, on in the preset since spec 429.11 (test_c2_p36.py)
        soil_stop_scope="any_loc",
    )
    assert preset.fault_reground.stroke_end_entry
    assert preset.fault_reground.stroke_end_travel_m == 0.030


def test_t13_settings_validation() -> None:
    for bad in ({"loc_anchor_deadzone_m": -0.001}, {"loc_anchor_offset_m": -0.001}):
        with pytest.raises(ValueError):
            SoilResponseSettings(**bad)
    for bad in (
        {"extra_margin_m": -0.001},
        {"shift_clearance_margin_m": -0.001},
        {"hold_limit_s": 0.0},
        {"lookahead_periods": 0},
        {"lookahead_periods": True},
    ):
        with pytest.raises(ValueError):
            LiftStrokeGuardSettings(**bad)
    with pytest.raises(ValueError):
        FaultRegroundSettings(stroke_end_travel_m=0.0)


def test_old_pickle_reads_the_p28_keys_off(geometry) -> None:
    """Configs and run states pickled before rev. 70 read the class-level defaults."""
    controller = C2Controller(geometry, C2Config())
    copied = pickle.loads(pickle.dumps(controller))
    copied.config.__dict__.pop("lift_stroke_guard")
    for name in ("lift_stroke_limited", "is_lift_guard_warned", "lift_guard_hold_since_s"):
        copied._state.__dict__.pop(name)
    aged = pickle.loads(pickle.dumps(copied))
    assert aged.config.lift_stroke_guard == LiftStrokeGuardSettings()
    assert aged._state.lift_stroke_limited is False
    assert aged._state.lift_guard_hold_since_s is None
    json.dumps(aged.meta())


# --- T2 .. T4 LOC anchor ----------------------------------------------------------------------


def test_t2_anchor_bias_rule(geometry) -> None:
    controller = C2Controller(geometry, p28_config())
    raw_m = np.array([-0.030, -0.010, 0.004, 0.020])
    anchored = controller._loc_anchor_bias_m(raw_m, -0.030)
    np.testing.assert_allclose(anchored, raw_m + ANCHOR_OFFSET_M, rtol=0.0, atol=TOLERANCE_M)
    assert controller._loc_anchor_bias_m(raw_m, -0.015) is None  # inside the dead zone
    assert controller._loc_anchor_bias_m(raw_m, 0.030) is None  # the S-3 bias (①) case
    off = C2Controller(geometry, bench_config())  # anchor off
    assert off._loc_anchor_bias_m(raw_m, -0.030) is None


def test_t3_planar_pads_give_no_anchor_and_the_same_commands(geometry) -> None:
    """A LOC with ``c_min(t_P)`` inside the dead zone: bias zero, commands as with the anchor
    off (the harness flat references are checked against ``r70_flatref_AG2.json``)."""
    benches = []
    for config in (p28_config(), replace(p28_config(), soil=replace(
            p28_config().soil, loc_anchor_enable=False))):
        bench = level_bench(geometry, config, operating_strokes(geometry))
        sample = plateau_sample(geometry, geometry.operating_extension_m(-0.004), bench.t_s)
        confirm_at(bench.controller, sample, geometry)
        assert not bench.controller._soil_state().is_loc_anchor_applied
        assert bench.controller._active_corner_bias_m() is None
        for _ in range(40):
            bench.step()
        benches.append(bench)
    np.testing.assert_array_equal(np.array(benches[0].outputs), np.array(benches[1].outputs))
    assert event_names(benches[0].controller, SOIL_EVENT_LOC_ANCHOR) == []


def test_t4_raised_pad_floor_anchors_the_lowest_corner_at_minus_5_mm(geometry) -> None:
    """FL's pad floor raised by 100 mm: at ``t_P`` (crawler just clear) the FL stroke is 100 mm
    short of a level floor and the stroke plane reads the crawler deep in the floor. After the
    anchor the lowest corner reads -5 mm, and the estimate then follows the stroke change."""
    controller = C2Controller(geometry, p28_config())
    strokes_at_P = geometry.operating_extension_m(0.0)
    strokes_at_P[FL] -= 0.100
    sample = plateau_sample(geometry, strokes_at_P)
    assert float(sample.corner_clearance_m.min()) < -0.020
    confirm_at(controller, sample, geometry)
    soil = controller._soil_state()
    assert soil.is_loc_anchor_applied
    assert controller._clearance_estimate_m(strokes_at_P) == pytest.approx(-0.005, abs=1e-4)
    rises_m = (0.0, 0.02, 0.04)
    estimates = [controller._clearance_estimate_m(strokes_at_P + rise) for rise in rises_m]
    assert estimates[1] - estimates[0] == pytest.approx(0.02, abs=1e-9)
    assert estimates[2] - estimates[0] == pytest.approx(0.04, abs=1e-9)
    (anchor_event,) = event_names(controller, SOIL_EVENT_LOC_ANCHOR)
    values_mm = [float(value) for value in anchor_event.split(":", 1)[1].split(",")]
    meta = json.loads(json.dumps(controller.meta()))["soil"]
    assert meta["loc_anchor_applied"] is True
    assert values_mm == pytest.approx(
        [meta["loc_anchor_bias_mm"][name] for name in LEG_ORDER], abs=0.051
    )
    assert event_names(controller, SOIL_EVENT_CLEARANCE_BIAS) == []


def test_restore_refuses_a_liftoff_the_anchor_would_bias(geometry) -> None:
    restored = RestoredLiftoff(
        plateau_start_s=5.0,
        liftoff_s=6.0,
        weight_estimate_N=4 * STEADY_LOAD_N,
        clearance_at_plateau_start_m=-0.030,
        clearance_at_liftoff_m=-0.020,
        source="test",
    )
    with pytest.raises(ValueError, match="anchor"):
        C2Controller(geometry, p28_config()).restore_liftoff_confirmation(restored)
    no_anchor = replace(p28_config(), soil=replace(p28_config().soil, loc_anchor_enable=False))
    C2Controller(geometry, no_anchor).restore_liftoff_confirmation(restored)


# --- T5 .. T9 stroke-budget guard ---------------------------------------------------------------


def guard_controller(geometry: C2Geometry, *, in_crawler_zone: bool) -> C2Controller:
    controller = C2Controller(geometry, p28_config())
    controller._state.phase = C2Phase.LEVEL
    controller._state.in_crawler_zone = in_crawler_zone
    force_liftoff(controller)
    return controller


def near_end_strokes(geometry: C2Geometry, leg: int, below_guard_m: float = 0.001) -> np.ndarray:
    strokes = np.full(4, 0.5)
    strokes[leg] = guard_stroke_m(geometry) - below_guard_m
    return strokes


LEG_SPEEDS_M_S = np.array([0.010, 0.004, -0.002, 0.003])


def guard_reading(
    geometry: C2Geometry, clearance_m: float = 0.08, below_guard_m: float = 0.001
) -> _Reading:
    """FL ``below_guard_m`` under ``s_g`` (motor stroke), rod strokes at ``clearance_m``."""
    return stroke_reading(
        1.0,
        near_end_strokes(geometry, FL, below_guard_m),
        geometry.operating_extension_m(clearance_m),
    )


def test_t5_guard_shifts_every_leg_down_when_the_crawler_is_clear(geometry) -> None:
    controller = guard_controller(geometry, in_crawler_zone=False)
    reading = guard_reading(geometry)
    assert controller._clearance_estimate_m(reading.rod_stroke_m) == pytest.approx(0.08)
    guarded = controller._apply_lift_stroke_guard(reading, LEG_SPEEDS_M_S)
    np.testing.assert_array_equal(guarded, LEG_SPEEDS_M_S - LEG_SPEEDS_M_S[FL])
    assert guarded[FL] <= 0.0
    # the attitude and twist parts are differences between legs: unchanged
    np.testing.assert_allclose(np.diff(guarded), np.diff(LEG_SPEEDS_M_S), atol=TOLERANCE_M)
    state = controller._state
    assert state.lift_guard_mode is LiftGuardMode.SHIFT_DOWN
    assert state.lift_stroke_limited and state.lift_guard_legs == (FL,)
    assert event_names(controller, LIFT_GUARD_WARNING_EVENT) == [f"{LIFT_GUARD_WARNING_EVENT}:FL"]
    controller._apply_lift_stroke_guard(reading, LEG_SPEEDS_M_S)
    assert len(event_names(controller, LIFT_GUARD_WARNING_EVENT)) == 1  # once per LEVEL entry


def test_t5_a_leg_far_from_the_end_is_not_guarded(geometry) -> None:
    controller = guard_controller(geometry, in_crawler_zone=False)
    reading = guard_reading(geometry, below_guard_m=0.003)  # 2 mm of lookahead at 10 mm/s
    guarded = controller._apply_lift_stroke_guard(reading, LEG_SPEEDS_M_S)
    assert guarded is LEG_SPEEDS_M_S
    assert controller._state.lift_guard_mode is None


@pytest.mark.parametrize(
    ("in_crawler_zone", "clearance_m"), [(True, 0.08), (False, 0.012)], ids=["zone", "low"]
)
def test_t6_guard_holds_every_leg_in_the_zone_or_low(
    geometry, in_crawler_zone, clearance_m
) -> None:
    controller = guard_controller(geometry, in_crawler_zone=in_crawler_zone)
    reading = guard_reading(geometry, clearance_m)
    guarded = controller._apply_lift_stroke_guard(reading, LEG_SPEEDS_M_S)
    np.testing.assert_array_equal(guarded, np.zeros(4))
    assert controller._state.lift_guard_mode is LiftGuardMode.HOLD_ALL


def test_t9_no_guard_before_the_liftoff_confirmation(geometry) -> None:
    controller = guard_controller(geometry, in_crawler_zone=False)
    controller._soil_state().is_liftoff_confirmed = False
    reading = guard_reading(geometry)
    assert controller._apply_lift_stroke_guard(reading, LEG_SPEEDS_M_S) is LEG_SPEEDS_M_S
    assert not controller._state.lift_stroke_limited
    assert controller.events == ()


def hold_bench(
    geometry: C2Geometry, config: C2Config | None = None
) -> tuple[Bench, GuardRecorder]:
    """LEVEL in the crawler zone with the LOC forced, FL 0.5 mm below ``s_g`` and a small roll:
    the heave lifts every leg, the guard holds them all."""
    strokes = geometry.operating_extension_m(0.0)
    strokes[FL] = guard_stroke_m(geometry) - 0.0005
    controller = GuardRecorder(geometry, p28_config() if config is None else config)
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    force_liftoff(controller)
    bench.strokes_m = strokes
    bench.tilt_rad = LEVEL_TILT_RAD
    return bench, controller


def test_t6_hold_keeps_the_attitude_integrators_and_warns_once(geometry) -> None:
    bench, controller = hold_bench(geometry)
    state = controller._state
    for _ in range(10):
        integrals_before = (state.roll_integral, state.pitch_integral)
        bench.step()
        assert state.lift_guard_mode is LiftGuardMode.HOLD_ALL
        assert (state.roll_integral, state.pitch_integral) == integrals_before
    for output in controller.guard_outputs:
        np.testing.assert_array_equal(output, np.zeros(4))
    assert event_names(controller, LIFT_GUARD_WARNING_EVENT) == [f"{LIFT_GUARD_WARNING_EVENT}:FL"]
    # the same bench without the guard integrates the roll error
    unguarded = replace(p28_config(), lift_stroke_guard=LiftStrokeGuardSettings())
    free = C2Controller(geometry, unguarded)
    free_bench = Bench(free, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        free_bench.step()
    force_liftoff(free)
    free_bench.strokes_m, free_bench.tilt_rad = bench.strokes_m, LEVEL_TILT_RAD
    for _ in range(10):  # the 2 x 0.8 s attitude filter takes the roll into the band
        free_bench.step()
    assert free._state.roll_integral != 0.0


def test_t7_hold_limit_faults_after_3_s(geometry) -> None:
    """The 3 s hold limit itself: P-S8-36 SGS (preset since spec 429.11) would stop the run in
    the first guard period after the LOC, so it is off here (test_c2_p36.py covers it)."""
    config = p28_config()
    config = replace(config, lift_stroke_guard=replace(config.lift_stroke_guard, soil_stop=False))
    bench, controller = hold_bench(geometry, config)
    bench.step()
    hold_start_s = controller._state.lift_guard_hold_since_s
    assert hold_start_s == bench.t_s
    bench.run_while(C2Phase.LEVEL, limit_s=bench.t_s + 10.0)
    assert controller.phase is C2Phase.FAULT
    assert bench.t_s - hold_start_s == pytest.approx(HOLD_LIMIT_S, abs=1e-9)
    assert event_names(controller, LIFT_GUARD_FAULT_EVENT) == [f"{LIFT_GUARD_FAULT_EVENT}:FL"]
    np.testing.assert_array_equal(controller.computed_output_m_s, np.zeros(4))
    run = run_meta_of(controller)
    assert run["trigger"] == "stroke_end" and run["end_reason"] == "no_target"
    meta = json.loads(json.dumps(controller.meta()))["lift_stroke_guard"]
    assert meta["mode_counts"]["hold_all"] == meta["periods"] == 31
    assert meta["hold_s"] == pytest.approx(HOLD_LIMIT_S)


def test_t8_limited_lift_completes_at_the_lifted_level(geometry) -> None:
    """With the guard latch, DONE needs the clearance only at ``lifted_clearance_m`` (10 mm)."""
    outcomes = {}
    for is_limited in (True, False):
        bench = level_bench(geometry, p28_config(), geometry.operating_extension_m(0.03))
        force_liftoff(bench.controller)
        bench.controller._state.lift_stroke_limited = is_limited
        bench.run_while(C2Phase.LEVEL, limit_s=bench.t_s + 10.0)
        outcomes[is_limited] = bench.controller.phase
    assert outcomes[True] is C2Phase.DONE
    assert outcomes[False] is C2Phase.LEVEL


def test_relevel_clears_the_guard_latch(geometry) -> None:
    controller = guard_controller(geometry, in_crawler_zone=False)
    controller._state.lift_stroke_limited = True
    controller._state.is_lift_guard_warned = True
    controller._start_relevel()
    assert not controller._state.lift_stroke_limited
    assert not controller._state.is_lift_guard_warned


# --- T10 / T11 stroke-end FAULT and re-ground -----------------------------------------------------


def run_meta_of(controller: C2Controller) -> dict:
    return json.loads(json.dumps(controller.meta()))["fault_reground"]["run"]


def stroke_end_bench(geometry: C2Geometry, config: C2Config) -> Bench:
    """LEVEL without LOC (no guard), FL at its stroke end; the heave keeps FL pushing."""
    strokes = geometry.operating_extension_m(0.0)
    strokes[FL] = geometry.stroke_soft_max_m
    return level_bench(geometry, config, strokes)


@pytest.mark.parametrize("is_named", [True, False])
def test_t10_stroke_end_fault_is_named(geometry, is_named) -> None:
    config = p28_config()
    guard = replace(config.lift_stroke_guard, name_stroke_end_fault=is_named)
    bench = stroke_end_bench(geometry, replace(config, lift_stroke_guard=guard))
    start_s = bench.t_s
    bench.run_while(C2Phase.LEVEL, limit_s=bench.t_s + 10.0)
    controller = bench.controller
    assert controller.phase is C2Phase.FAULT
    assert bench.t_s - start_s > 2.0
    names = event_names(controller, STROKE_END_FAULT_EVENT)
    assert names == ([f"{STROKE_END_FAULT_EVENT}:FL"] if is_named else [])
    assert run_meta_of(controller)["end_reason"] == "no_target"  # nothing lifted


def test_t11_stroke_end_fault_regrounds_the_lifted_leg(geometry) -> None:
    bench = stroke_end_bench(geometry, p28_config(**NO_REAPPROACH))
    controller = bench.controller
    lifted_rr = np.full(4, STEADY_LOAD_N)
    lifted_rr[RR] = LIFTED_READING_N
    while controller.phase is C2Phase.LEVEL and bench.t_s < 30.0:
        bench.step(lifted_rr)
    assert controller.phase is C2Phase.FAULT_REGROUND
    run = controller._state.fault_reground
    assert run.trigger is RegroundTrigger.STROKE_END
    assert [target.leg for target in run.targets] == [RR]
    assert [target.max_travel_m for target in run.targets] == [0.030]
    assert event_names(controller, START_EVENT) == [f"{START_EVENT}:RR"]
    assert event_names(controller, STROKE_END_FAULT_EVENT) == [f"{STROKE_END_FAULT_EVENT}:FL"]
    bench.step(lifted_rr)
    assert controller.computed_output_m_s[RR] > 0.0  # RR alone extends
    np.testing.assert_array_equal(np.delete(controller.computed_output_m_s, RR), 0.0)
    bench.run_while(C2Phase.FAULT_REGROUND, limit_s=bench.t_s + 20.0)  # RR reads steady again
    assert controller.phase is C2Phase.FAULT
    assert run.end_reason is RegroundEnd.DONE and run.contact_count == 1
    assert event_names(controller, END_EVENT) == [f"{END_EVENT}:1/1"]


def test_t11_stroke_end_entry_off_stops_at_once(geometry) -> None:
    config = p28_config(**NO_REAPPROACH)
    config = replace(config, fault_reground=replace(config.fault_reground, stroke_end_entry=False))
    bench = stroke_end_bench(geometry, config)
    lifted_rr = np.full(4, STEADY_LOAD_N)
    lifted_rr[RR] = LIFTED_READING_N
    while bench.controller.phase is C2Phase.LEVEL and bench.t_s < 30.0:
        bench.step(lifted_rr)
    assert bench.controller.phase is C2Phase.FAULT
    assert bench.controller._state.fault_reground is None


# --- T12 head-fault path ---------------------------------------------------------------------


def test_t12_head_fault_path_unchanged(geometry) -> None:
    """The G4 path (P-S8-24 / 25) commands the same with or without the stroke-end entry, and
    its run record says ``head_fault``."""
    outputs = []
    for stroke_end_entry in (True, False):
        rig = ready_rig(geometry, reground_config(stroke_end_entry=stroke_end_entry))
        lift_and_fault(rig, RR, FL)
        rig.run_while(C2Phase.FAULT_REGROUND, limit_s=rig.t_s + 20.0)
        outputs.append(np.array(rig.returned))
        assert run_meta(rig)["trigger"] == "head_fault"
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_period_is_the_bench_period() -> None:
    assert C2Config().with_10hz_d1().period_s == PERIOD_S
