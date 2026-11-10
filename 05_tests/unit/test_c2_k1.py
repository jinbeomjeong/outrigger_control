"""C2 LAS-b K1: R4c30 order gate (``06_analysis/02_control/verif_matrix/las_k1_rules.md`` 1).

With ``SlopeClearanceMarginSettings.flat_soil_margin_order_gate`` the R4 flat-soil margin also
needs ``round(t_P / T_s) > round(t_S / T_s)`` (plateau start after the soil-mode start); a
blocked LOC leaves an ``INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`` event. Gate off: commands and
events of before, the decision record (meta ``slope_clearance_margin.order_gate``) is kept as a
shadow. Synthetic 10 Hz benches of ``test_c2_p37r4.py`` (the LOC is forced through
``_confirm_liftoff``, whose plateau sample sits at the LOC time).
"""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest
from test_c2_p28 import level_bench  # same test folder
from test_c2_p31 import confirm_liftoff  # same test folder
from test_c2_p37r4 import (  # same test folder
    FLAT_MARGIN_M,
    FLAT_TARGET_M,
    LEVEL_SETTLE_RAD,
    NO_SOIL_SIGN_CLEARANCE_M,
    SOIL_SIGN_CLEARANCE_M,
    TARGET_M,
    TILTED_SETTLE_RAD,
    events_named,
    r4_config,
)
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control.c2 import (
    FLAT_SOIL_MARGIN_EVENT,
    FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    SlopeClearanceMarginSettings,
    _RunState,
)
from outrigger_sim.params import load_params

SOIL_MODE_START_S = 3.0
"""``n_S`` = 30."""
STEPS_AFTER_LOC = 40
SKIP_EVENT_BASE = FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT.split(":", 1)[0]


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def k1_config(is_gate_on: bool, flat_soil_margin_m: float = FLAT_MARGIN_M) -> C2Config:
    config = r4_config(flat_soil_margin_m)
    margin = replace(config.slope_clearance_margin, flat_soil_margin_order_gate=is_gate_on)
    return replace(config, slope_clearance_margin=margin)


def order_gate_meta(controller: C2Controller) -> dict:
    """``slope_clearance_margin.order_gate`` meta after a JSON round trip."""
    return json.loads(json.dumps(controller.meta()))["slope_clearance_margin"]["order_gate"]


def loc_at(
    controller: C2Controller,
    geometry: C2Geometry,
    t_P_s: float,
    soil_mode_start_s: float | None = SOIL_MODE_START_S,
    settle_rad=LEVEL_SETTLE_RAD,
    clearance_at_P_m: float = NO_SOIL_SIGN_CLEARANCE_M,
) -> None:
    controller._soil_state().soil_mode_start_s = soil_mode_start_s
    confirm_liftoff(controller, geometry, settle_rad, clearance_at_P_m=clearance_at_P_m, t_s=t_P_s)


# --- settings ----------------------------------------------------------------------------------


def test_gate_is_off_in_the_class_and_on_in_the_preset() -> None:
    """``las_k1_rules_adopt.md`` 9.1: the class default stays off (the behaviour before K1), the
    R8 preset has it on since the K1 switch, and the preset keyword gives the old preset back."""
    assert SlopeClearanceMarginSettings().flat_soil_margin_order_gate is False
    assert C2Config().slope_clearance_margin.flat_soil_margin_order_gate is False
    assert C2Config().with_10hz_d1().slope_clearance_margin.flat_soil_margin_order_gate is True
    pre_k1 = C2Config().with_10hz_d1(flat_soil_margin_order_gate=False)
    assert pre_k1.slope_clearance_margin.flat_soil_margin_order_gate is False
    assert pre_k1 == replace(
        C2Config().with_10hz_d1(),
        slope_clearance_margin=replace(
            C2Config().with_10hz_d1().slope_clearance_margin, flat_soil_margin_order_gate=False
        ),
    )  # the keyword changes the gate and nothing else
    assert _RunState.flat_soil_order_decisions == ()  # class attribute (old pickles)


# --- the order rule ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("t_P_s", "dP", "would_block"),
    [
        (SOIL_MODE_START_S, 0, True),  # n_P = n_S
        (SOIL_MODE_START_S - 0.1, -1, True),  # n_P = n_S - 1
        (SOIL_MODE_START_S + 0.1, 1, False),  # n_P = n_S + 1
    ],
)
@pytest.mark.parametrize("is_gate_on", [True, False])
def test_block_and_apply_by_period_number(geometry, t_P_s, dP, would_block, is_gate_on) -> None:
    controller = C2Controller(geometry, k1_config(is_gate_on))
    loc_at(controller, geometry, t_P_s)
    is_applied = not (is_gate_on and would_block)
    expected_target_m = FLAT_TARGET_M if is_applied else TARGET_M
    assert controller._clearance_target_m() == pytest.approx(expected_target_m, abs=1e-15)
    assert events_named(controller, FLAT_SOIL_MARGIN_EVENT + ":") == (
        [f"{FLAT_SOIL_MARGIN_EVENT}:80"] if is_applied else []
    )
    expected_skips = [FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT] if not is_applied else []
    assert events_named(controller, SKIP_EVENT_BASE) == expected_skips
    meta = order_gate_meta(controller)
    assert meta["enabled"] is is_gate_on
    assert meta["decisions"] == [
        {
            "t_loc_s": t_P_s,
            "t_P_s": t_P_s,
            "t_S_s": SOIL_MODE_START_S,
            "n_P": 30 + dP,
            "n_S": 30,
            "dP": dP,
            "r4_due_without_gate": True,
            "would_block": would_block,
            "applied": is_applied,
        }
    ]


def test_periods_not_floats_decide(geometry) -> None:
    """Rules 5.0.2: 29.999999999975 s is period 300, so a plateau at 30.0 s does not follow."""
    controller = C2Controller(geometry, k1_config(True))
    loc_at(controller, geometry, 30.0, soil_mode_start_s=29.999999999975)
    decision = order_gate_meta(controller)["decisions"][0]
    assert (decision["n_P"], decision["n_S"], decision["dP"]) == (300, 300, 0)
    assert decision["would_block"] is True and decision["applied"] is False


@pytest.mark.parametrize("is_gate_on", [True, False])
def test_no_soil_mode_no_record(geometry, is_gate_on) -> None:
    """Rules 7: a LOC without a soil-mode start is not an R4 evaluation (no t_S, no record)."""
    controller = C2Controller(geometry, k1_config(is_gate_on))
    loc_at(controller, geometry, 5.0, soil_mode_start_s=None)
    assert order_gate_meta(controller)["decisions"] == []
    assert events_named(controller, SKIP_EVENT_BASE) == []
    assert controller._clearance_target_m() == TARGET_M


def test_slope_margin_first_no_record(geometry) -> None:
    """Rules 1.1: the P-S8-31 branch is judged first; that LOC is no R4 evaluation."""
    controller = C2Controller(geometry, k1_config(True))
    loc_at(controller, geometry, 5.0, settle_rad=TILTED_SETTLE_RAD,
           clearance_at_P_m=SOIL_SIGN_CLEARANCE_M)
    assert order_gate_meta(controller)["decisions"] == []
    assert events_named(controller, SKIP_EVENT_BASE) == []


def test_r4_not_due_is_recorded_without_block(geometry) -> None:
    """A tilted settle without the soil sign: R4 evaluated and not due, nothing to block."""
    controller = C2Controller(geometry, k1_config(True))
    loc_at(controller, geometry, SOIL_MODE_START_S, settle_rad=TILTED_SETTLE_RAD)
    decision = order_gate_meta(controller)["decisions"][0]
    assert decision["r4_due_without_gate"] is False
    assert decision["would_block"] is False and decision["applied"] is False
    assert events_named(controller, SKIP_EVENT_BASE) == []


def test_r4_off_keeps_no_record(geometry) -> None:
    controller = C2Controller(geometry, k1_config(True, flat_soil_margin_m=0.0))
    loc_at(controller, geometry, SOIL_MODE_START_S)
    assert order_gate_meta(controller)["decisions"] == []


def test_every_loc_after_a_revocation_is_recorded(geometry) -> None:
    """Rules 1.2: one record per evaluated LOC, a LOC found again after a revocation too."""
    controller = C2Controller(geometry, k1_config(True))
    loc_at(controller, geometry, SOIL_MODE_START_S)  # blocked
    controller._revoke_loc(4.0, 3000.0)
    loc_at(controller, geometry, 9.0, soil_mode_start_s=6.0)  # new soil mode, then the LOC
    decisions = order_gate_meta(controller)["decisions"]
    assert [d["applied"] for d in decisions] == [False, True]
    assert [d["dP"] for d in decisions] == [0, 30]
    assert controller._clearance_target_m() == pytest.approx(FLAT_TARGET_M, abs=1e-15)


def test_reset_clears_the_decisions(geometry) -> None:
    controller = C2Controller(geometry, k1_config(False))
    loc_at(controller, geometry, SOIL_MODE_START_S)
    controller.reset()
    assert order_gate_meta(controller)["decisions"] == []


# --- commands ----------------------------------------------------------------------------------


def bench_outputs(geometry, config: C2Config, soil_mode_offset_s: float) -> np.ndarray:
    """Outputs of a level bench with a forced LOC at the bench time; the soil mode started
    ``soil_mode_offset_s`` before it."""
    bench = level_bench(geometry, config, operating_strokes(geometry))
    controller = bench.controller
    controller._soil_state().soil_mode_start_s = bench.t_s - soil_mode_offset_s
    confirm_liftoff(controller, geometry, LEVEL_SETTLE_RAD,
                    clearance_at_P_m=NO_SOIL_SIGN_CLEARANCE_M, t_s=bench.t_s)
    for _ in range(STEPS_AFTER_LOC):
        bench.step()
    return np.array(bench.outputs)


def test_not_blocked_gate_on_commands_equal_gate_off(geometry) -> None:
    """K-4 on a bench: a LOC the gate does not block commands bit for bit as the gate off."""
    gate_on = bench_outputs(geometry, k1_config(True), soil_mode_offset_s=0.5)
    gate_off = bench_outputs(geometry, k1_config(False), soil_mode_offset_s=0.5)
    np.testing.assert_array_equal(gate_on, gate_off)


def test_blocked_commands_equal_r4_off(geometry) -> None:
    """A blocked LOC commands bit for bit as R4 off (the target stays the configured one)."""
    blocked = bench_outputs(geometry, k1_config(True), soil_mode_offset_s=0.0)
    r4_off = bench_outputs(geometry, k1_config(False, flat_soil_margin_m=0.0),
                           soil_mode_offset_s=0.0)
    applied = bench_outputs(geometry, k1_config(False), soil_mode_offset_s=0.0)
    np.testing.assert_array_equal(blocked, r4_off)
    assert not np.array_equal(blocked, applied)  # the gate changed something here
