"""C2 P-S8-36 SGS (soil guard stop) of control spec 427.9 / 427.12 (control adoption 2026-10-30):
the soil sign latched at every LOC, the stop in the first guard period and its meta (427.12.3
test list (3); the wrapper tests of ``test_427_p36s.py`` ported to ``03_src``).

Benches and helpers of ``test_c2_p28.py`` (10 Hz synthetic readings, the R8 soil response on).
The closed-loop acceptance (03_src = wrapper P36s command hashes, 1,220 runs) runs outside the
unit tests.
"""

from __future__ import annotations

import json
import math
import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_p28 import (  # same test folder
    FL,
    LEVEL_TILT_RAD,
    LIFTED_READING_N,
    RR,
    confirm_at,
    event_names,
    guard_stroke_m,
    p28_config,
    plateau_sample,
)
from test_c2_r8d1 import (  # same test folder
    NO_REAPPROACH,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    operating_strokes,
)

from outrigger_sim.control.c2 import (
    LIFT_GUARD_FAULT_EVENT,
    LIFT_GUARD_SOIL_STOP_EVENT,
    LIFT_GUARD_WARNING_EVENT,
    SOIL_SIGN_CLEARANCE_TILT,
    SOIL_SIGN_SOIL_MODE,
    SOIL_STOP_SCOPE_ANY_LOC,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    LiftGuardMode,
    LiftStrokeGuardSettings,
    _RunState,
)
from outrigger_sim.control.fault_reground import START_EVENT
from outrigger_sim.params import load_params

TILTED_RAD = (math.radians(1.2), 0.0)
LEVEL_RAD = (math.radians(0.9), math.radians(-0.5))
GUARDED_FR = np.array([False, True, False, False])
SOIL_STOP_PREFIX = f"{LIFT_GUARD_SOIL_STOP_EVENT}:"


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def sgs_config(**guard_changes) -> C2Config:
    """``p28_config`` (the preset guard, SGS on) with the ``"soil_sign"`` scope (the sign
    tests; the preset arms every LOC) and guard keys changed."""
    config = p28_config(**NO_REAPPROACH)
    guard = replace(config.lift_stroke_guard, soil_stop=True, soil_stop_scope="soil_sign")
    return replace(config, lift_stroke_guard=replace(guard, **guard_changes))


def level_controller(geometry: C2Geometry, config: C2Config | None = None) -> C2Controller:
    controller = C2Controller(geometry, sgs_config() if config is None else config)
    controller._state.phase = C2Phase.LEVEL
    return controller


def latch_loc(
    controller: C2Controller,
    t_s: float,
    *,
    soil_mode: bool = False,
    c_min_at_P_m: float | None = 0.0,
    settle_rad: tuple[float, float] = LEVEL_RAD,
) -> None:
    """The LOC state the latch reads, then the latch (as at the end of ``_confirm_liftoff``)."""
    soil = controller._soil_state()
    soil.is_liftoff_confirmed = True
    soil.soil_mode_start_s = 1.0 if soil_mode else None
    soil.clearance_at_plateau_start_m = c_min_at_P_m
    controller._settle_attitude_rad = lambda: settle_rad
    controller._latch_guard_soil_sign(t_s)


def guard_meta(controller: C2Controller) -> dict:
    return json.loads(json.dumps(controller.meta()))["lift_stroke_guard"]


# --- settings -----------------------------------------------------------------------------------


def test_class_default_off_and_preset_on() -> None:
    default = LiftStrokeGuardSettings()
    assert not default.soil_stop and default.soil_stop_scope == "soil_sign"
    preset = C2Config().with_10hz_d1().lift_stroke_guard
    assert preset.soil_stop  # on in the preset since the spec 429.11 switch
    assert preset.soil_stop_scope == SOIL_STOP_SCOPE_ANY_LOC  # 427.12.5
    switched_off = C2Config().with_10hz_d1(soil_stop=False)
    assert not switched_off.lift_stroke_guard.soil_stop
    assert switched_off == replace(
        C2Config().with_10hz_d1(),
        lift_stroke_guard=replace(preset, soil_stop=False),
    )
    assert not C2Config().lift_stroke_guard.soil_stop
    assert _RunState.guard_soil_sign is None and _RunState.soil_stop is None  # old pickles


def test_scope_validation() -> None:
    LiftStrokeGuardSettings(soil_stop_scope="any_loc")
    with pytest.raises(ValueError, match="soil_stop_scope"):
        LiftStrokeGuardSettings(soil_stop_scope="every_loc")


def test_old_pickle_reads_sgs_off(geometry) -> None:
    controller = C2Controller(geometry, C2Config())
    copied = pickle.loads(pickle.dumps(controller))
    copied.config.__dict__.pop("lift_stroke_guard")
    for name in ("guard_soil_sign", "guard_soil_sign_history", "soil_stop_due", "soil_stop"):
        copied._state.__dict__.pop(name)
    aged = pickle.loads(pickle.dumps(copied))
    assert not aged.config.lift_stroke_guard.soil_stop
    assert aged._state.guard_soil_sign_history == ()
    json.dumps(aged.meta())


# --- soil sign ----------------------------------------------------------------------------------


def test_soil_sign_from_the_soil_mode(geometry) -> None:
    controller = level_controller(geometry)
    latch_loc(controller, 20.0, soil_mode=True)
    assert controller._state.guard_soil_sign == SOIL_SIGN_SOIL_MODE
    assert controller._has_loc_soil_sign()


@pytest.mark.parametrize(
    ("c_min_at_P_m", "settle_rad", "sign"),
    [
        (0.011, TILTED_RAD, SOIL_SIGN_CLEARANCE_TILT),
        (0.009, TILTED_RAD, None),  # c_min(t_P) not above 10 mm
        (0.011, LEVEL_RAD, None),  # settle tilt not above 1 deg
        (None, TILTED_RAD, None),
    ],
)
def test_soil_sign_from_clearance_and_tilt(geometry, c_min_at_P_m, settle_rad, sign) -> None:
    controller = level_controller(geometry)
    latch_loc(controller, 20.0, c_min_at_P_m=c_min_at_P_m, settle_rad=settle_rad)
    assert controller._state.guard_soil_sign == sign
    assert controller._has_loc_soil_sign() is (sign is not None)  # the same L1gs gate


def test_confirm_liftoff_latches_the_sign(geometry) -> None:
    controller = level_controller(geometry)
    controller._soil_state().soil_mode_start_s = 3.0
    strokes_m = geometry.operating_extension_m(0.0)
    confirm_at(controller, plateau_sample(geometry, strokes_m, t_s=12.0), geometry)
    assert controller._state.guard_soil_sign == SOIL_SIGN_SOIL_MODE
    assert controller._state.guard_soil_sign_history == ({"t_s": 12.0, "sign": "soil_mode"},)


def test_no_latch_without_a_confirmed_loc(geometry) -> None:
    controller = level_controller(geometry)
    controller._soil_state().soil_mode_start_s = 1.0
    controller._latch_guard_soil_sign(20.0)
    assert controller._state.guard_soil_sign is None
    assert controller._state.guard_soil_sign_history == ()


def test_loc_revocation_clears_the_sign_and_the_next_loc_judges_again(geometry) -> None:
    controller = level_controller(geometry)
    state = controller._state
    latch_loc(controller, 20.0, soil_mode=True)
    controller._clear_guard_soil_sign_without_loc(20.5)  # LOC still confirmed: kept
    assert state.guard_soil_sign == SOIL_SIGN_SOIL_MODE
    controller._revoke_loc(21.0, 3000.0)
    controller._clear_guard_soil_sign_without_loc(21.0)  # what ``update`` runs at its end
    assert state.guard_soil_sign is None
    assert state.guard_soil_sign_history[-1] == {"t_s": 21.0, "sign": None, "cleared": True}
    latch_loc(controller, 25.0, c_min_at_P_m=0.002)
    assert state.guard_soil_sign is None  # a LOC without either sign
    latch_loc(controller, 30.0, c_min_at_P_m=0.015, settle_rad=TILTED_RAD)
    assert state.guard_soil_sign == SOIL_SIGN_CLEARANCE_TILT


# --- stop: direct periods -----------------------------------------------------------------------


def test_guard_period_with_the_sign_stops_and_blocks_done(geometry) -> None:
    controller = level_controller(geometry)
    latch_loc(controller, 20.0, soil_mode=True)
    state = controller._state
    controller._record_lift_guard_period(40.0, GUARDED_FR, LiftGuardMode.SHIFT_DOWN)
    assert state.soil_stop_due == (40.0, (1,), LiftGuardMode.SHIFT_DOWN)
    state.phase = C2Phase.DONE  # what the LEVEL step of this period decided
    state.roll_integral = 0.5  # wound during the period: the stop keeps the start values
    out = controller._stop_on_soil_guard((0.01, -0.02), np.full(4, 0.003))
    np.testing.assert_array_equal(out, np.zeros(4))
    assert state.phase is C2Phase.FAULT  # nothing lifted: no re-ground target
    assert (state.roll_integral, state.pitch_integral) == (0.01, -0.02)
    assert state.complete_since_s is None
    names = [event.name for event in controller.events]
    assert names[-2:] == [f"{LIFT_GUARD_WARNING_EVENT}:FR", f"{SOIL_STOP_PREFIX}FR"]
    assert state.soil_stop == {
        "t_s": 40.0, "legs": "FR", "mode": "shift_down",
        "soil_sign": SOIL_SIGN_SOIL_MODE, "done_blocked": True,
    }
    assert state.soil_stop_due is None


def test_no_stop_without_the_sign(geometry) -> None:
    controller = level_controller(geometry)
    latch_loc(controller, 20.0, c_min_at_P_m=0.002)
    controller._record_lift_guard_period(40.0, GUARDED_FR, LiftGuardMode.HOLD_ALL)
    assert controller._state.soil_stop_due is None
    assert controller._state.soil_guard_first_s is None


def test_record_only_with_soil_stop_off(geometry) -> None:
    controller = level_controller(geometry, sgs_config(soil_stop=False))
    latch_loc(controller, 20.0, soil_mode=True)
    controller._record_lift_guard_period(40.0, GUARDED_FR, LiftGuardMode.HOLD_ALL)
    controller._record_lift_guard_period(40.1, GUARDED_FR, LiftGuardMode.HOLD_ALL)
    assert controller._state.soil_stop_due is None
    meta = guard_meta(controller)
    assert meta["soil_guard_first_s"] == 40.0 and meta["soil_stop"] is None
    assert meta["soil_sign"] == SOIL_SIGN_SOIL_MODE and not meta["soil_stop_enabled"]


def test_any_loc_scope_arms_a_loc_without_the_sign(geometry) -> None:
    for scope, is_due in (("soil_sign", False), (SOIL_STOP_SCOPE_ANY_LOC, True)):
        controller = level_controller(geometry, sgs_config(soil_stop_scope=scope))
        latch_loc(controller, 20.0, c_min_at_P_m=0.002)
        assert controller._state.guard_soil_sign is None
        controller._record_lift_guard_period(40.0, GUARDED_FR, LiftGuardMode.SHIFT_DOWN)
        assert (controller._state.soil_stop_due is not None) is is_due


def test_any_loc_is_disarmed_after_a_revocation(geometry) -> None:
    """SA-6: a revoked LOC (and no LOC at all) disarms the ``"any_loc"`` scope."""
    controller = level_controller(geometry, sgs_config(soil_stop_scope=SOIL_STOP_SCOPE_ANY_LOC))
    assert not controller._is_soil_stop_scope_met()  # no LOC yet
    latch_loc(controller, 20.0, c_min_at_P_m=0.002)
    assert controller._is_soil_stop_scope_met()
    controller._revoke_loc(21.0, 3000.0)
    assert not controller._is_soil_stop_scope_met()
    controller._record_lift_guard_period(21.1, GUARDED_FR, LiftGuardMode.SHIFT_DOWN)
    assert controller._state.soil_stop_due is None
    assert controller._state.soil_guard_first_s is None


def test_a_fault_of_the_level_step_is_kept(geometry) -> None:
    controller = level_controller(geometry)
    latch_loc(controller, 20.0, soil_mode=True)
    controller._record_lift_guard_period(40.0, GUARDED_FR, LiftGuardMode.HOLD_ALL)
    controller._state.phase = C2Phase.FAULT  # e.g. FAULT_STROKE_END in the same period
    speeds = np.zeros(4)
    assert controller._stop_on_soil_guard((0.0, 0.0), speeds) is speeds
    assert controller._state.soil_stop is None
    assert controller._state.soil_stop_preempted == "fault"
    assert not event_names(controller, SOIL_STOP_PREFIX)


# --- stop: closed bench -------------------------------------------------------------------------


def hold_bench(geometry: C2Geometry, config: C2Config) -> Bench:
    """LEVEL in the crawler zone with a LOC, FL 0.5 mm below ``s_g`` and a small roll: the
    heave lifts every leg, the guard holds them all (``test_c2_p28.hold_bench``)."""
    strokes = geometry.operating_extension_m(0.0)
    strokes[FL] = guard_stroke_m(geometry) - 0.0005
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    bench.strokes_m = strokes
    bench.tilt_rad = LEVEL_TILT_RAD
    return bench


@pytest.mark.parametrize("soil_mode", [True, False], ids=["sign", "no_sign"])
def test_bench_first_guard_period(geometry, soil_mode) -> None:
    """With the sign the first HOLD_ALL period is the stop; without it the old 3 s hold."""
    bench = hold_bench(geometry, sgs_config())
    controller, state = bench.controller, bench.controller._state
    latch_loc(controller, bench.t_s, soil_mode=soil_mode)
    integrals_before = (state.roll_integral, state.pitch_integral)
    bench.step()
    if soil_mode:
        assert controller.phase is C2Phase.FAULT
        guard_names = event_names(controller, LIFT_GUARD_WARNING_EVENT) + event_names(
            controller, LIFT_GUARD_FAULT_EVENT
        )
        assert guard_names == [f"{LIFT_GUARD_WARNING_EVENT}:FL", f"{SOIL_STOP_PREFIX}FL"]
        assert (state.roll_integral, state.pitch_integral) == integrals_before
        np.testing.assert_array_equal(controller.computed_output_m_s, np.zeros(4))
        meta = guard_meta(controller)
        assert meta["soil_stop"]["mode"] == "hold_all"
        assert meta["soil_stop"]["t_s"] == meta["soil_guard_first_s"] == round(bench.t_s, 2)
        return
    assert controller.phase is C2Phase.LEVEL
    bench.run_while(C2Phase.LEVEL, limit_s=bench.t_s + 10.0)
    assert event_names(controller, LIFT_GUARD_FAULT_EVENT) == [f"{LIFT_GUARD_FAULT_EVENT}:FL"]


def test_bench_any_loc_stops_without_the_sign(geometry) -> None:
    """Preset scope ``"any_loc"``: a LOC without a soil sign still arms the stop."""
    bench = hold_bench(geometry, sgs_config(soil_stop_scope=SOIL_STOP_SCOPE_ANY_LOC))
    controller = bench.controller
    latch_loc(controller, bench.t_s, c_min_at_P_m=0.002)
    assert controller._state.guard_soil_sign is None
    bench.step()
    assert controller.phase is C2Phase.FAULT
    assert event_names(controller, SOIL_STOP_PREFIX) == [f"{SOIL_STOP_PREFIX}FL"]
    assert guard_meta(controller)["soil_stop"]["soil_sign"] is None


def test_bench_without_sign_commands_as_soil_stop_off(geometry) -> None:
    """No sign: SGS on commands bit for bit as SGS off (the hold limit FAULT included)."""
    outputs = []
    for soil_stop in (True, False):
        bench = hold_bench(geometry, sgs_config(soil_stop=soil_stop))
        latch_loc(bench.controller, bench.t_s, c_min_at_P_m=0.002)
        bench.run_while(C2Phase.LEVEL, limit_s=bench.t_s + 10.0)
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_bench_stop_regrounds_a_lifted_leg(geometry) -> None:
    """RR reads lifted: the stop goes to the U-S8-79 re-ground (R30) as the guard FAULT."""
    bench = hold_bench(geometry, sgs_config())
    controller = bench.controller
    lifted_rr = np.full(4, STEADY_LOAD_N)
    lifted_rr[RR] = LIFTED_READING_N
    for _ in range(2):  # guard periods before the LOC sign: hold only (two lifted samples)
        latch_loc(controller, bench.t_s, c_min_at_P_m=0.002)
        bench.step(lifted_rr)
    assert controller.phase is C2Phase.LEVEL
    latch_loc(controller, bench.t_s, soil_mode=True)
    bench.step(lifted_rr)
    assert controller.phase is C2Phase.FAULT_REGROUND
    assert event_names(controller, SOIL_STOP_PREFIX) == [f"{SOIL_STOP_PREFIX}FL"]
    assert event_names(controller, START_EVENT) == [f"{START_EVENT}:RR"]
    run = controller._state.fault_reground
    assert [target.max_travel_m for target in run.targets] == [0.030]


def test_meta_is_json_and_history_capped(geometry) -> None:
    controller = level_controller(geometry)
    for k in range(12):
        latch_loc(controller, 20.0 + k, soil_mode=k % 2 == 0)
    meta = guard_meta(controller)
    assert len(meta["soil_sign_history"]) == 10
    assert meta["soil_sign_history"][0] == {"t_s": 20.0, "sign": SOIL_SIGN_SOIL_MODE}
    assert meta["settings"]["soil_stop"] is True
    assert meta["settings"]["soil_stop_scope"] == "soil_sign"
    assert meta["soil_stop_preempted"] is None
