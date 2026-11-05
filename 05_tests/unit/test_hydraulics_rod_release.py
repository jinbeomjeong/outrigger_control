"""M2 rule of ``hydraulics.rod_release`` (spec ``v5_hydraulic_impl_spec.md`` 2.3, M2-5, M2-8)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.hydraulics.rod_release import (
    CLIPPED_STEPS_KEY,
    PREVIOUS_PRESSURE_KEY,
    SHIFT_TOTAL_KEY,
    RodReleaseShift,
)

BAR = 1.0e5
BULK_MODULUS_PA = 1.0e9
HEAD_DEAD_LENGTH_M = 0.05
ROD_DIAMETER_FL_M, BORE_DIAMETER_FL_M = 0.110, 0.130
HEAD_AREA_FL_M2 = np.pi / 4.0 * BORE_DIAMETER_FL_M**2
ANNULUS_FL_M2 = np.pi / 4.0 * (BORE_DIAMETER_FL_M**2 - ROD_DIAMETER_FL_M**2)
OPERATING_EXTENSION_FL_M = 0.4011
K_H_FL_N_M = BULK_MODULUS_PA * HEAD_AREA_FL_M2 / (HEAD_DEAD_LENGTH_M + OPERATING_EXTENSION_FL_M)
WIDE_ROOM_M = 1.0


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


def test_snapshot_round_trip_continues_bit_identically() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    _one_leg_shift(rule, 34.0 * BAR)
    _one_leg_shift(rule, 33.0 * BAR)
    copy = RodReleaseShift([ANNULUS_FL_M2])
    copy.restore_state(rule.state_arrays())
    for pressure_bar in (31.0, 27.0, 11.0):
        assert _one_leg_shift(rule, pressure_bar * BAR) == _one_leg_shift(copy, pressure_bar * BAR)
    assert rule.shift_total_m[0] == copy.shift_total_m[0]


def test_snapshot_without_keys_starts_at_the_current_pressure() -> None:
    rule = RodReleaseShift([ANNULUS_FL_M2])
    rule.restore_state({})
    assert _one_leg_shift(rule, 20.0 * BAR) == 0.0
    assert rule.shift_total_m[0] == 0.0
    assert set(rule.state_arrays()) == {PREVIOUS_PRESSURE_KEY, SHIFT_TOTAL_KEY, CLIPPED_STEPS_KEY}
