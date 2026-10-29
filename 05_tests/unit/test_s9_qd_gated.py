"""Wrapper tokens L1g / L1gs / L2g of ``s9_slope_fix_candidates.py`` (control spec 424.10.1,
gated Q-D after the L1+L2 regression).

The LOC is forced through ``_confirm_liftoff`` on the R8 preset, the L1 watch is fed through
``_l1_watch_step`` (what the wrapper ``update`` calls after the command).
"""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

LOAD_SUM_N = 3.7e5
RISE_N = 8000.0
"""Load-sum rise well above the 2 kN revocation limit."""
TILTED_RAD = (math.radians(1.2), 0.0)
LEVEL_RAD = (0.0, 0.0)
SOIL_SIGN_M = 0.015
GUARD_LIMIT_M = 0.6428
"""Lift guard stroke 682.8 mm minus the 40 mm L1-s margin (spec 424.10.1)."""


class _Reading:
    def __init__(self, t_s: float, stroke_m: float, load_sum_N: float = LOAD_SUM_N) -> None:
        self.t_s = t_s
        self.motor_stroke_m = np.full(4, stroke_m)
        self.rod_stroke_m = np.full(4, stroke_m)
        self.cylinder_force_N = np.full(4, load_sum_N / 4.0)


@pytest.fixture(scope="module")
def params():
    return load_params()


def candidate(params, name: str, monkeypatch, settle_rad=LEVEL_RAD):
    settings = fx.parse_candidate(name)
    cls = fx.make_candidate_class(c2, c2.C2Controller, settings)
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    controller._state.phase = c2.C2Phase.LEVEL
    monkeypatch.setattr(controller, "_settle_attitude_rad", lambda: settle_rad)
    return controller


def tail(clearance_m: float, strokes=(0.300, 0.310)) -> list:
    first = c2._PlateauSample(t_s=10.0, mean_motor_stroke_m=strokes[0], load_sum_N=LOAD_SUM_N,
                              corner_clearance_m=np.full(4, clearance_m),
                              raw_attitude_rad=(0.0, 0.0))
    return [first, replace(first, t_s=12.0, mean_motor_stroke_m=strokes[1])]


def force_loc(controller, clearance_m: float = 0.0, stroke_m: float = 0.30,
              soil_mode_ran: bool = False) -> None:
    if soil_mode_ran:
        controller._soil_state().soil_mode_start_s = 5.0
    controller._state.last_reading = _Reading(12.0, stroke_m)
    controller._confirm_liftoff(12.0, tail(clearance_m), LOAD_SUM_N)


def feed_rise(controller, stroke_m: float = 0.30, periods: int = 4) -> None:
    for k in range(periods):
        controller._state.last_reading = _Reading(12.1 + 0.1 * k, stroke_m, LOAD_SUM_N + RISE_N)
        controller._l1_watch_step()


def event_names(controller, prefix: str) -> list[str]:
    return [e.name for e in controller.events if e.name.startswith(prefix)]


# --- tokens ------------------------------------------------------------------------------------


def test_tokens_set_the_gates() -> None:
    l1g = fx.parse_candidate("L1g")
    assert l1g.l1_revoke and l1g.l1_soil_gate and not l1g.l1_stroke_guard
    both = fx.parse_candidate("L1gs+L2g")
    assert both.l1_revoke and both.l1_soil_gate and both.l1_stroke_guard
    assert both.l2_confirm_window and both.l2_soil_gate
    assert both.l1_stroke_margin_m == pytest.approx(0.040)
    assert not fx.parse_candidate("L1+L2").l2_soil_gate
    for token in ("L1g", "L1gs", "L2g"):
        assert token in fx.CANDIDATE_TOKENS


@pytest.mark.parametrize("overrides", [{"l1_soil_gate": True}, {"l1_stroke_guard": True},
                                       {"l2_soil_gate": True}])
def test_a_gate_without_its_rule_is_refused(overrides) -> None:
    with pytest.raises(ValueError, match="gate"):
        fx.parse_candidate("current", overrides)


# --- L1-g --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clearance_m", "settle_rad", "soil_mode_ran", "is_watched"),
    [
        (0.0, LEVEL_RAD, False, False),  # level rigid floor: no soil sign
        (SOIL_SIGN_M, LEVEL_RAD, False, False),  # c_min alone is not the E3c10 sign
        (0.0, TILTED_RAD, False, False),  # tilt alone neither
        (SOIL_SIGN_M, TILTED_RAD, False, True),  # E3c10 sign
        (0.0, LEVEL_RAD, True, True),  # soil mode ran
    ],
)
def test_l1g_watches_only_a_loc_with_a_soil_sign(
    params, monkeypatch, clearance_m, settle_rad, soil_mode_ran, is_watched
) -> None:
    controller = candidate(params, "L1g", monkeypatch, settle_rad)
    force_loc(controller, clearance_m, soil_mode_ran=soil_mode_ran)
    assert controller._soil_state().is_liftoff_confirmed
    assert (controller.fix.l1_watch is not None) is is_watched
    feed_rise(controller)
    assert controller.fix.l1_revokes == (1 if is_watched else 0)


def test_l1g_at_the_10_mm_boundary_needs_more_than_10_mm(params, monkeypatch) -> None:
    controller = candidate(params, "L1g", monkeypatch, TILTED_RAD)
    force_loc(controller, 0.010)
    assert controller.fix.l1_watch is None


# --- L1-s --------------------------------------------------------------------------------------


def test_l1s_limit_is_the_lift_guard_minus_40_mm(params, monkeypatch) -> None:
    controller = candidate(params, "L1gs", monkeypatch)
    limit_m = controller._lift_guard_stroke_m() - 0.040
    assert limit_m == pytest.approx(GUARD_LIMIT_M, abs=1e-6)


def test_l1s_withholds_the_revocation_near_the_stroke_budget(params, monkeypatch) -> None:
    controller = candidate(params, "L1gs", monkeypatch)
    stroke_m = GUARD_LIMIT_M + 0.001
    force_loc(controller, stroke_m=stroke_m, soil_mode_ran=True)
    feed_rise(controller, stroke_m)
    assert controller._soil_state().is_liftoff_confirmed and controller.fix.l1_revokes == 0
    assert controller.fix.l1_skips == 1 and controller.fix.l1_watch is None
    assert event_names(controller, fx.LOC_REVOKE_EVENT) == [
        f"{fx.LOC_REVOKE_SKIPPED_EVENT}:stroke"]


def test_l1s_revocation_keeps_the_slope_margin(params, monkeypatch) -> None:
    """Below the stroke limit L1gs revokes; the P-S8-31 margin of the first LOC stays (no
    second application), while plain L1 resets it."""
    for name, kept in (("L1gs", True), ("L1g", False)):
        controller = candidate(params, name, monkeypatch)
        stroke_m = GUARD_LIMIT_M - 0.005
        force_loc(controller, stroke_m=stroke_m, soil_mode_ran=True)
        state = controller._state
        state.clearance_target_m, state.slope_margin_applied_s = 0.08, 12.0
        feed_rise(controller, stroke_m)
        assert controller.fix.l1_revokes == 1 and controller.fix.l1_skips == 0
        assert (state.slope_margin_applied_s == 12.0) is kept
        assert (state.clearance_target_m == 0.08) is kept


# --- L2-g --------------------------------------------------------------------------------------


@pytest.mark.parametrize(("soil_mode_ran", "is_held"), [(False, False), (True, True)])
def test_l2g_holds_only_after_soil_mode(params, monkeypatch, soil_mode_ran, is_held) -> None:
    controller = candidate(params, "L2g", monkeypatch)
    force_loc(controller, SOIL_SIGN_M, soil_mode_ran=soil_mode_ran)
    assert (controller.fix.l2_pending is not None) is is_held
    assert controller._soil_state().is_liftoff_confirmed is not is_held


def test_plain_l2_still_holds_without_soil_mode(params, monkeypatch) -> None:
    controller = candidate(params, "L2", monkeypatch)
    force_loc(controller, SOIL_SIGN_M)
    assert controller.fix.l2_pending is not None


# --- records -----------------------------------------------------------------------------------


def test_skip_record_is_neither_an_action_nor_a_revocation() -> None:
    skipped = {"metrics": {"fix_events": [[30.0, "FIX_LOC_REVOKE_SKIPPED:stroke"]]}}
    assert not fx.has_candidate_acted(skipped)
    revoked = {"metrics": {"fix_events": [[30.0, "FIX_LOC_REVOKE:2.3"]]}}
    assert fx.has_candidate_acted(revoked)
    metrics = {"window_checks": [{"t_s": 20.0, "vetoed": None}],
               "fix_events": [[30.0, "FIX_LOC_REVOKE_SKIPPED:stroke"],
                              [31.0, "FIX_LOC_REVOKE:2.3"]]}
    assert fx._stored_loc_events(metrics) == [(20.0, fx.LOC_EVENT), (31.0, "FIX_LOC_REVOKE:2.3")]
