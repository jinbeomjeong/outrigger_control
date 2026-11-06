"""M2 rule of ``hydraulics.rod_release`` (spec ``v5_hydraulic_impl_spec.md`` 2.3, M2-5, M2-8;
revision 3 flow-limited pressure M2-9 .. M2-11)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.flow_share import FlowShareAssumptions
from outrigger_sim.hydraulics.rod_release import (
    CLIPPED_STEPS_KEY,
    FLOW_LIMITED_LAW,
    PREVIOUS_PRESSURE_KEY,
    SHIFT_TOTAL_KEY,
    RodPressureFlowLaw,
    RodReleaseShift,
    flow_limited_rod_pressure,
)

BAR = 1.0e5
BULK_MODULUS_PA = 1.0e9
HEAD_DEAD_LENGTH_M = 0.05
ROD_DEAD_LENGTH_M = 0.05
STROKE_M = 0.70
ROD_DIAMETER_FL_M, BORE_DIAMETER_FL_M = 0.110, 0.130
HEAD_AREA_FL_M2 = np.pi / 4.0 * BORE_DIAMETER_FL_M**2
ANNULUS_FL_M2 = np.pi / 4.0 * (BORE_DIAMETER_FL_M**2 - ROD_DIAMETER_FL_M**2)
OPERATING_EXTENSION_FL_M = 0.4011
K_H_FL_N_M = BULK_MODULUS_PA * HEAD_AREA_FL_M2 / (HEAD_DEAD_LENGTH_M + OPERATING_EXTENSION_FL_M)
K_R_FL_N_M = BULK_MODULUS_PA * ANNULUS_FL_M2 / (STROKE_M - OPERATING_EXTENSION_FL_M
                                                + ROD_DEAD_LENGTH_M)
WIDE_ROOM_M = 1.0
MAX_SPEED_M_S = 20.9243016e-3
SLOW_SPEED_M_S = 0.01 * MAX_SPEED_M_S
"""M2-9, M2-10: 1 % v_max."""
STEP_S = 1.0e-4
"""The L2b step (spec: the harness uses its inner step)."""
LAG_S = 0.05
ROD_PRESSURE_RETRACT_PA = 34.818 * BAR
ROD_PRESSURE_EXTEND_PA = 5.0 * BAR


def _one_leg_shift(rule: RodReleaseShift, pressure_Pa: float, *, is_moving: bool = True,
                   room_down_m: float = -WIDE_ROOM_M, room_up_m: float = WIDE_ROOM_M) -> float:
    shift = rule.shift_m([pressure_Pa], [K_H_FL_N_M], [is_moving], [room_down_m], [room_up_m])
    return float(shift[0])


def test_m2_5_shift_sum_34p818_to_5_bar_is_the_hand_value() -> None:
    """Spec M2-5: fixed ``s_ref``, FL, hand value 0.3820 mm; the step sum within 1e-9 m of it.

    The spec prints the hand value to 4 decimals of a mm: the closed form must round to it, and
    the summed steps must equal the closed form within 1e-9 m.
    """
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 34.818 * BAR)
    total_m = 0.0
    for pressure_bar in np.linspace(34.818, 5.0, 501)[1:]:
        total_m += _one_leg_shift(rule, float(pressure_bar) * BAR)
    hand_m = ANNULUS_FL_M2 * (34.818 - 5.0) * BAR / K_H_FL_N_M
    assert round(hand_m * 1e3, 4) == 0.3820
    assert total_m == pytest.approx(hand_m, abs=1.0e-9)
    assert rule.shift_total_m[0] == pytest.approx(total_m, abs=1.0e-15)


def test_m2_8_rising_pressure_shifts_the_other_way_and_the_sum_holds() -> None:
    """Spec M2-8: no Hopsan reference for a retract start; sign and sum only."""
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 2.0 * BAR)
    total_m = sum(_one_leg_shift(rule, pressure_bar * BAR) for pressure_bar in (10.0, 20.0, 34.818))
    assert total_m < 0.0
    assert total_m == pytest.approx(-ANNULUS_FL_M2 * 32.818 * BAR / K_H_FL_N_M, rel=1.0e-12)


def test_locked_leg_does_not_shift_but_its_pressure_is_remembered() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 34.818 * BAR, is_moving=False)
    assert _one_leg_shift(rule, 30.0 * BAR, is_moving=False) == 0.0
    moving_shift_m = _one_leg_shift(rule, 29.0 * BAR)
    assert moving_shift_m == pytest.approx(ANNULUS_FL_M2 * 1.0 * BAR / K_H_FL_N_M, rel=1.0e-12)


def test_first_call_and_forgotten_pressure_start_without_a_shift() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    assert _one_leg_shift(rule, 10.0 * BAR) == 0.0
    rule.forget_pressure()
    assert _one_leg_shift(rule, 30.0 * BAR) == 0.0


def test_seed_replaces_the_previous_pressure_of_one_leg() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 2.0 * BAR)
    rule.seed_pressure(0, 27.96 * BAR)
    assert _one_leg_shift(rule, 27.96 * BAR) == 0.0


def test_shift_stays_inside_the_travel_room_and_is_counted() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 34.818 * BAR)
    room_up_m = 1.0e-5
    assert _one_leg_shift(rule, 5.0 * BAR, room_up_m=room_up_m) == room_up_m
    assert rule.clipped_steps[0] == 1


def test_clip_times_are_kept_only_with_a_step_time_and_not_in_the_snapshot() -> None:
    """v5 criteria rev. 2 2.1: a clipped step given ``t_s`` records its time; the total and
    the snapshot keys stay as before."""
    rule = RodReleaseShift([ANNULUS_FL_M2])
    rule.shift_m([34.818 * BAR], [K_H_FL_N_M], [True], [-WIDE_ROOM_M], [1.0e-5], t_s=0.5)
    rule.shift_m([5.0 * BAR], [K_H_FL_N_M], [True], [-WIDE_ROOM_M], [1.0e-5], t_s=1.25)
    _one_leg_shift(rule, 4.0 * BAR, room_up_m=0.0)  # clipped, no time given
    assert rule.clipped_steps[0] == 2
    assert rule.clip_times_s == [[1.25]]
    assert set(rule.state_arrays()) == {PREVIOUS_PRESSURE_KEY, SHIFT_TOTAL_KEY, CLIPPED_STEPS_KEY}
    rule.restore_state(rule.state_arrays())
    assert rule.clip_times_s == [[]]


def test_snapshot_round_trip_continues_bit_identically() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 34.0 * BAR)
    _one_leg_shift(rule, 33.0 * BAR)
    copy = RodReleaseShift([ANNULUS_FL_M2])
    copy.restore_state(rule.state_arrays())
    for pressure_bar in (31.0, 27.0, 11.0):
        assert _one_leg_shift(rule, pressure_bar * BAR) == _one_leg_shift(copy, pressure_bar * BAR)
    assert rule.shift_total_m[0] == copy.shift_total_m[0]


def _front_left_compliance_m3_Pa() -> float:
    return RodPressureFlowLaw.rod_compliance_m3_Pa(ANNULUS_FL_M2, K_H_FL_N_M, K_R_FL_N_M)


def _flow_limited_step(previous_Pa: float, target_Pa: float, speed_m_s: float) -> float:
    return RodPressureFlowLaw().rod_pressure_Pa(
        previous_Pa, target_Pa, speed_m_s, STEP_S, LAG_S, _front_left_compliance_m3_Pa(),
        HEAD_AREA_FL_M2, ANNULUS_FL_M2, is_retract=speed_m_s < 0.0)


def test_flow_law_constants_are_the_flow_share_assumptions() -> None:
    """``p_T``, ``dp_c`` and ``b_T`` are the values the flow model uses (spec: same ASSUMPTION)."""
    law = RodPressureFlowLaw()
    shared = FlowShareAssumptions(eta_v=1.0)
    assert law.tank_pressure_Pa == shared.tank_pressure_Pa
    assert law.spool_reference_drop_Pa == shared.compensator_drop_Pa
    assert law.meter_out_ratio == shared.back_land_ratio
    assert law.meta()["law"] == FLOW_LIMITED_LAW == "flow_limited_r3"
    assert _front_left_compliance_m3_Pa() == pytest.approx(1.80e-12, rel=0.005)


def test_m2_9_slow_retract_builds_the_rod_pressure_at_the_meter_in_flow() -> None:
    """Spec M2-9: FL, body fixed, 1 % v_max retract from 5 bar: dp/dt = A_ann u / C_r =
    4.39 bar/s and the M2 shift moves at r u = 0.0562 mm/s (r = k_r / (k_h + k_r)), 1 %."""
    duration_s = 1.0
    rule = RodReleaseShift([ANNULUS_FL_M2])
    pressure_Pa = ROD_PRESSURE_EXTEND_PA
    _one_leg_shift(rule, pressure_Pa)
    for _ in range(round(duration_s / STEP_S)):
        pressure_Pa = _flow_limited_step(pressure_Pa, ROD_PRESSURE_RETRACT_PA, -SLOW_SPEED_M_S)
        _one_leg_shift(rule, pressure_Pa)
    slope_bar_s = (pressure_Pa - ROD_PRESSURE_EXTEND_PA) / BAR / duration_s
    shift_speed_mm_s = -rule.shift_total_m[0] / duration_s * 1e3
    rod_share = K_R_FL_N_M / (K_H_FL_N_M + K_R_FL_N_M)
    assert slope_bar_s == pytest.approx(
        ANNULUS_FL_M2 * SLOW_SPEED_M_S / _front_left_compliance_m3_Pa() / BAR, rel=1e-9)
    assert slope_bar_s == pytest.approx(4.39, rel=0.01)
    assert shift_speed_mm_s == pytest.approx(rod_share * SLOW_SPEED_M_S * 1e3, rel=1e-9)
    assert shift_speed_mm_s == pytest.approx(0.0562, rel=0.01)


def test_m2_10_slow_extend_drains_through_the_meter_out_orifice() -> None:
    """Spec M2-10: FL 1 % v_max extend, 34.818 -> 10 bar in
    t = 2 C_r sqrt(dp_c) (sqrt(p0 - p_T) - sqrt(p1 - p_T)) / (b_T A_h u) = 1.188 s (1 %)."""
    law = RodPressureFlowLaw()
    end_Pa = 10.0 * BAR
    pressure_Pa = ROD_PRESSURE_RETRACT_PA
    steps = 0
    while pressure_Pa > end_Pa:
        pressure_Pa = _flow_limited_step(pressure_Pa, ROD_PRESSURE_EXTEND_PA, SLOW_SPEED_M_S)
        steps += 1
    closed_form_s = (2.0 * _front_left_compliance_m3_Pa() * math.sqrt(law.spool_reference_drop_Pa)
                     * (math.sqrt(ROD_PRESSURE_RETRACT_PA - law.tank_pressure_Pa)
                        - math.sqrt(end_Pa - law.tank_pressure_Pa))
                     / (law.meter_out_ratio * HEAD_AREA_FL_M2 * SLOW_SPEED_M_S))
    assert steps * STEP_S == pytest.approx(closed_form_s, rel=0.01)
    assert steps * STEP_S == pytest.approx(1.188, rel=0.01)


@pytest.mark.parametrize("is_retract, target_Pa", [(True, ROD_PRESSURE_RETRACT_PA),
                                                   (False, ROD_PRESSURE_EXTEND_PA)])
def test_m2_11_no_flow_holds_the_pressure_on_the_flow_side(is_retract, target_Pa) -> None:
    """Spec M2-11: u = 0 -> the side the valve flow fills or drains keeps its pressure."""
    start_Pa = 20.0 * BAR
    held_Pa = flow_limited_rod_pressure(start_Pa, target_Pa, 0.0, STEP_S, LAG_S,
                                        _front_left_compliance_m3_Pa(), HEAD_AREA_FL_M2,
                                        ANNULUS_FL_M2, is_retract)
    assert held_Pa == start_Pa


def test_flow_law_lags_freely_away_from_the_flow_side() -> None:
    """A retracting leg whose target is below its pressure (and an extending one above it)
    follows the plain lag, bit for bit."""
    start_Pa = 20.0 * BAR
    lagged_Pa = 5.0 * BAR + (start_Pa - 5.0 * BAR) * math.exp(-STEP_S / LAG_S)
    assert _flow_limited_step(start_Pa, 5.0 * BAR, -SLOW_SPEED_M_S) == lagged_Pa
    raised_Pa = 30.0 * BAR + (start_Pa - 30.0 * BAR) * math.exp(-STEP_S / LAG_S)
    assert _flow_limited_step(start_Pa, 30.0 * BAR, SLOW_SPEED_M_S) == raised_Pa


def test_flow_cap_never_passes_the_lagged_pressure() -> None:
    """A flow cap wider than the lag step (here 100 v_max) leaves the lagged value."""
    start_Pa = 6.0 * BAR
    lagged_Pa = (ROD_PRESSURE_RETRACT_PA
                 + (start_Pa - ROD_PRESSURE_RETRACT_PA) * math.exp(-STEP_S / LAG_S))
    fast_Pa = _flow_limited_step(start_Pa, ROD_PRESSURE_RETRACT_PA, -MAX_SPEED_M_S * 100.0)
    assert fast_Pa == lagged_Pa


def test_snapshot_without_keys_starts_at_the_current_pressure() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    rule.restore_state({})
    assert _one_leg_shift(rule, 20.0 * BAR) == 0.0
    assert rule.shift_total_m[0] == 0.0
    assert set(rule.state_arrays()) == {PREVIOUS_PRESSURE_KEY, SHIFT_TOTAL_KEY, CLIPPED_STEPS_KEY}
