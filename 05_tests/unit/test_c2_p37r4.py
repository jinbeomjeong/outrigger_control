"""C2 P-S8-37 R4 flat-soil clearance margin (R4c30, control spec 429.9, adopted 2026-10-30).

At a confirmed LOC where P-S8-31 did not raise the clearance target, with the soil mode used in
the lifting cycle and a level settle (tilt at most ``tilt_min_rad``), the run target becomes
``clearance_target_m + flat_soil_margin_m``. Synthetic 10 Hz benches of ``test_c2_p31.py``
(the LOC is forced through ``_confirm_liftoff``). The rule is compared with the reference
wrapper function ``p37_floor_twist.is_flat_soil_margin_due``; the closed-loop command-hash
acceptance against the wrapper ``P36sa+R4c30`` runs outside the unit tests.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_p28 import level_bench  # same test folder
from test_c2_p31 import confirm_liftoff, margin_config  # same test folder
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control.c2 import (
    FLAT_SOIL_MARGIN_EVENT,
    SLOPE_MARGIN_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Thresholds,
    SlopeClearanceMarginSettings,
    _RunState,
)
from outrigger_sim.params import load_params

ROOT = Path(__file__).resolve().parents[2]
WRAPPER_DIR = ROOT / "04_scripts" / "03_control" / "s9"
if str(WRAPPER_DIR) not in sys.path:
    sys.path.insert(0, str(WRAPPER_DIR))

import p37_floor_twist  # noqa: E402  (reference rule, read only)

TARGET_M = 0.05
FLAT_MARGIN_M = 0.03
FLAT_TARGET_M = TARGET_M + FLAT_MARGIN_M
TILT_LIMIT_RAD = math.radians(1.0)
LEVEL_SETTLE_RAD = (math.radians(0.4), math.radians(-0.3))
TILTED_SETTLE_RAD = (math.radians(1.2), 0.0)
SOIL_SIGN_CLEARANCE_M = 0.015
"""``c_min(t_P)`` above the 10 mm P-S8-31 soil sign."""
NO_SOIL_SIGN_CLEARANCE_M = 0.005
SOIL_MODE_START_S = 3.0
STEPS_AFTER_LOC = 40


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def r4_config(flat_soil_margin_m: float = FLAT_MARGIN_M, **loc_revoke_changes) -> C2Config:
    config = margin_config(flat_soil_margin_m=flat_soil_margin_m)
    if loc_revoke_changes:
        config = replace(config, loc_revoke=replace(config.loc_revoke, **loc_revoke_changes))
    return config


def controller_after_soil_mode(geometry: C2Geometry, config: C2Config) -> C2Controller:
    controller = C2Controller(geometry, config)
    controller._soil_state().soil_mode_start_s = SOIL_MODE_START_S
    return controller


def events_named(controller: C2Controller, prefix: str) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(prefix)]


def margin_meta(controller: C2Controller) -> dict:
    """``slope_clearance_margin`` meta after a JSON round trip."""
    return json.loads(json.dumps(controller.meta()))["slope_clearance_margin"]


# --- settings and preset -----------------------------------------------------------------------


def test_class_default_is_off_and_preset_default_is_on() -> None:
    """Spec 429.11: the R8 preset carries R4c30; the settings class keeps the old behaviour."""
    assert SlopeClearanceMarginSettings().flat_soil_margin_m == 0.0
    assert C2Config().slope_clearance_margin.flat_soil_margin_m == 0.0
    assert C2Config().with_10hz_d1().slope_clearance_margin.flat_soil_margin_m == FLAT_MARGIN_M
    assert _RunState.flat_soil_margin_applied_s == ()  # class attribute (old pickles)


def test_preset_keywords_turn_r4_and_sgs_off_and_keep_the_rest() -> None:
    preset = C2Config().with_10hz_d1()
    switched_off = C2Config().with_10hz_d1(soil_stop=False, flat_soil_margin_m=0.0)
    assert switched_off.slope_clearance_margin == replace(
        preset.slope_clearance_margin, flat_soil_margin_m=0.0
    )
    assert not switched_off.lift_stroke_guard.soil_stop
    assert switched_off == replace(
        preset,
        slope_clearance_margin=switched_off.slope_clearance_margin,
        lift_stroke_guard=switched_off.lift_stroke_guard,
    )


def test_negative_margin_is_refused() -> None:
    with pytest.raises(ValueError, match="flat_soil_margin_m"):
        SlopeClearanceMarginSettings(flat_soil_margin_m=-1e-3)


def test_raised_target_above_the_z1_limit_is_refused(geometry) -> None:
    C2Controller(geometry, r4_config())
    with pytest.raises(ValueError, match="clearance_target_m"):
        C2Controller(geometry, r4_config(flat_soil_margin_m=0.043))
    high_target = C2Thresholds(clearance_target_m=0.06)  # + P-S8-31 30 mm = 90 mm: allowed
    C2Controller(geometry, replace(r4_config(0.0), thresholds=high_target))
    with pytest.raises(ValueError, match="clearance_target_m"):
        C2Controller(geometry, replace(r4_config(0.035), thresholds=high_target))


# --- the three conditions ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("is_soil_mode_used", "settle_rad", "is_due"),
    [
        (True, LEVEL_SETTLE_RAD, True),
        (False, LEVEL_SETTLE_RAD, False),
        (True, (TILT_LIMIT_RAD, 0.0), True),  # at the limit: <= fires
        (True, (0.0, -TILT_LIMIT_RAD), True),
        (True, (TILT_LIMIT_RAD + 1e-9, 0.0), False),
        (True, (0.0, -(TILT_LIMIT_RAD + 1e-9)), False),
        (True, None, False),  # unknown settle
    ],
)
def test_conditions_and_tilt_boundary(geometry, is_soil_mode_used, settle_rad, is_due) -> None:
    """``c_min(t_P)`` below the P-S8-31 soil sign, so only R4 can fire."""
    controller = C2Controller(geometry, r4_config())
    if is_soil_mode_used:
        controller._soil_state().soil_mode_start_s = SOIL_MODE_START_S
    confirm_liftoff(controller, geometry, settle_rad, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M)
    expected_target_m = FLAT_TARGET_M if is_due else TARGET_M
    assert controller._clearance_target_m() == pytest.approx(expected_target_m, abs=1e-15)
    expected_events = [f"{FLAT_SOIL_MARGIN_EVENT}:80"] if is_due else []
    assert events_named(controller, FLAT_SOIL_MARGIN_EVENT) == expected_events
    assert events_named(controller, SLOPE_MARGIN_EVENT) == []


def test_slope_margin_first_excludes_r4(geometry) -> None:
    """A tilted settle with the soil sign: P-S8-31 raises the target, R4 adds nothing."""
    controller = controller_after_soil_mode(geometry, r4_config())
    confirm_liftoff(controller, geometry, TILTED_SETTLE_RAD, clearance_at_P_m=SOIL_SIGN_CLEARANCE_M)
    assert events_named(controller, SLOPE_MARGIN_EVENT) == [f"{SLOPE_MARGIN_EVENT}:80"]
    assert events_named(controller, FLAT_SOIL_MARGIN_EVENT) == []
    assert margin_meta(controller)["flat_soil_margin_applied"] is False


def test_raised_run_target_excludes_r4(geometry) -> None:
    controller = controller_after_soil_mode(geometry, r4_config())
    controller._state.clearance_target_m = 0.07  # a target raised before this LOC
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M
    )
    assert controller._clearance_target_m() == pytest.approx(0.07)
    assert events_named(controller, FLAT_SOIL_MARGIN_EVENT) == []


def test_margin_off_does_nothing(geometry) -> None:
    controller = controller_after_soil_mode(geometry, r4_config(flat_soil_margin_m=0.0))
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M
    )
    assert controller._clearance_target_m() == TARGET_M
    assert events_named(controller, FLAT_SOIL_MARGIN_EVENT) == []


@pytest.mark.parametrize("is_soil_mode_used", [True, False])
@pytest.mark.parametrize("has_run_target", [True, False])
@pytest.mark.parametrize(
    "settle_rad",
    [LEVEL_SETTLE_RAD, (TILT_LIMIT_RAD, 0.0), (0.0, TILT_LIMIT_RAD * 1.001), None],
)
def test_rule_equals_the_wrapper_rule(
    geometry, is_soil_mode_used, has_run_target, settle_rad
) -> None:
    controller = C2Controller(geometry, r4_config())
    controller._soil_state().soil_mode_start_s = SOIL_MODE_START_S if is_soil_mode_used else None
    controller._state.clearance_target_m = 0.08 if has_run_target else None
    expected = p37_floor_twist.is_flat_soil_margin_due(
        is_soil_mode_used, settle_rad, TILT_LIMIT_RAD, has_run_target
    )
    assert controller._is_flat_soil_margin_due(settle_rad) is expected


# --- LOC revocation ----------------------------------------------------------------------------


@pytest.mark.parametrize("keep", [True, False])
def test_revocation_follows_keep_slope_margin_on_revoke(geometry, keep) -> None:
    """Kept: the R4 target stays and the next LOC adds none. Not kept: the target goes with
    the LOC and the next LOC (soil mode still used in this cycle) applies R4 again."""
    controller = controller_after_soil_mode(geometry, r4_config(keep_slope_margin_on_revoke=keep))
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=5.0
    )
    controller._revoke_loc(6.0, 3000.0)
    expected_after_revoke_m = FLAT_TARGET_M if keep else TARGET_M
    assert controller._clearance_target_m() == pytest.approx(expected_after_revoke_m, abs=1e-15)
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=9.0
    )
    assert controller._clearance_target_m() == pytest.approx(FLAT_TARGET_M, abs=1e-15)
    expected_times_s = [5.0] if keep else [5.0, 9.0]
    assert len(events_named(controller, FLAT_SOIL_MARGIN_EVENT)) == len(expected_times_s)
    assert margin_meta(controller)["flat_soil_margin_t_s"] == expected_times_s


def test_second_loc_without_revocation_does_not_add_again(geometry) -> None:
    controller = controller_after_soil_mode(geometry, r4_config())
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=5.0
    )
    controller._soil_state().is_liftoff_confirmed = False
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=9.0
    )
    assert len(events_named(controller, FLAT_SOIL_MARGIN_EVENT)) == 1


def test_reset_clears_the_record(geometry) -> None:
    controller = controller_after_soil_mode(geometry, r4_config())
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M
    )
    controller.reset()
    assert controller._clearance_target_m() == TARGET_M
    assert margin_meta(controller)["flat_soil_margin_t_s"] == []


# --- meta --------------------------------------------------------------------------------------


def test_meta_serialises(geometry) -> None:
    controller = controller_after_soil_mode(geometry, r4_config())
    before = margin_meta(controller)
    assert before["settings"]["flat_soil_margin_m"] == FLAT_MARGIN_M
    assert before["flat_soil_margin_applied"] is False and before["flat_soil_margin_t_s"] == []
    confirm_liftoff(
        controller, geometry, LEVEL_SETTLE_RAD, clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=5.0
    )
    after = margin_meta(controller)
    assert after["flat_soil_margin_applied"] is True
    assert after["flat_soil_margin_t_s"] == [5.0]
    assert after["clearance_target_m"] == pytest.approx(FLAT_TARGET_M)
    assert after["is_applied"] is False  # the P-S8-31 record stays its own


# --- commands ----------------------------------------------------------------------------------


def test_no_firing_keeps_the_commands_of_the_margin_off(geometry) -> None:
    """A LOC without the soil mode: R4 on and off command bit for bit alike."""
    outputs = []
    for flat_soil_margin_m in (FLAT_MARGIN_M, 0.0):
        bench = level_bench(geometry, r4_config(flat_soil_margin_m), operating_strokes(geometry))
        confirm_liftoff(
            bench.controller,
            geometry,
            LEVEL_SETTLE_RAD,
            clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M,
            t_s=bench.t_s,
        )
        for _ in range(STEPS_AFTER_LOC):
            bench.step()
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_firing_commands_equal_a_config_with_the_raised_target(geometry) -> None:
    implementation = level_bench(geometry, r4_config(), operating_strokes(geometry))
    reference = level_bench(geometry, r4_config(0.0), operating_strokes(geometry))
    for bench in (implementation, reference):
        bench.controller._soil_state().soil_mode_start_s = SOIL_MODE_START_S
        confirm_liftoff(
            bench.controller,
            geometry,
            LEVEL_SETTLE_RAD,
            clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M,
            t_s=bench.t_s,
        )
    config = reference.controller.config
    reference.controller.config = replace(
        config, thresholds=replace(config.thresholds, clearance_target_m=FLAT_TARGET_M)
    )
    for _ in range(STEPS_AFTER_LOC):
        implementation.step()
        reference.step()
    np.testing.assert_array_equal(np.array(implementation.outputs), np.array(reference.outputs))
    assert np.any(np.array(implementation.outputs)[-STEPS_AFTER_LOC:] > 0.0)  # heave acts
