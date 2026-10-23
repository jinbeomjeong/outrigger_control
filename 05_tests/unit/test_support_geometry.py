"""Unit tests of the GE1' support-geometry shadow (c2.SupportGeometryShadow, spec 37.3, 42.1).

Pads are placed exactly on a tilted floor plane (optionally with a per-leg offset along the
floor normal) for a given body attitude, so the expected heights are known without the
shadow's own formulas.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    FLOOR_NONPLANAR_CONDITION,
    SHADOW_HOLD_S,
    SHADOW_PAD_STIFFNESS_N_M,
    C2Geometry,
    SupportGeometryShadow,
    _level_from_body,
    floor_normal,
)
from outrigger_sim.params import LEG_ORDER, load_params

PERIOD_S = 0.02
FLOOR_RAD = (math.radians(1.0), math.radians(2.0))
BODY_ATTITUDE_RAD = (math.radians(0.3), math.radians(-0.4))
FLOOR_OFFSET_M = -1.6
"""``n . q`` of the floor plane in the level frame (body origin above the floor)."""
PAD_FORCES_N = np.array([110e3, 105e3, 75e3, 80e3])
FL, RR = LEG_ORDER.index("FL"), LEG_ORDER.index("RR")
HEIGHT_TOLERANCE_M = 1e-9
# Spec 37.3: r per metre of one rear leg's offset, 0.272 (trapezoid pad layout).
REAR_RESIDUAL_PER_OFFSET = 0.272
SUNK_FLOOR_M = 0.030
FURTHER_SINK_M = 0.006


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _strokes_on_the_floor(
    geometry: C2Geometry,
    lift_m: np.ndarray,
    forces_N: np.ndarray = PAD_FORCES_N,
    attitude_rad: tuple[float, float] = BODY_ATTITUDE_RAD,
) -> np.ndarray:
    """Rod strokes that put each pad bottom ``lift_m`` above the floor along its normal."""
    normal = floor_normal(FLOOR_RAD)
    rotation = _level_from_body(*attitude_rad)
    normal_per_body_z = float(normal @ rotation[:, 2])
    in_plane = geometry.pad_xy_m @ (rotation[:, :2].T @ normal)
    pad_bottom_z = (FLOOR_OFFSET_M + lift_m - in_plane) / normal_per_body_z
    deflection = forces_N / SHADOW_PAD_STIFFNESS_N_M
    return geometry.pad_bottom_z_retracted_m - pad_bottom_z + deflection


def _shadow_on(geometry: C2Geometry, lift_m: np.ndarray) -> SupportGeometryShadow:
    """Shadow with its reference taken on a floor whose pads sit ``lift_m`` off the plane."""
    shadow = SupportGeometryShadow(geometry)
    strokes = _strokes_on_the_floor(geometry, lift_m)
    shadow.store_reference(
        0.0, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N, "touch", floor_normal(FLOOR_RAD)
    )
    return shadow


def _null_vector_share(geometry: C2Geometry, leg: int) -> float:
    """``(I - P)_RR,leg``: residual of RR per metre of leg ``leg`` off the plane."""
    basis = np.column_stack([np.ones(4), geometry.pad_xy_m])
    null_vector = np.linalg.svd(basis.T)[2][-1]
    return float(null_vector[RR] * null_vector[leg] / (null_vector @ null_vector))


def test_pads_on_the_reference_floor_have_no_change(geometry) -> None:
    shadow = _shadow_on(geometry, np.zeros(4))
    strokes = _strokes_on_the_floor(geometry, np.zeros(4))
    assert shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N) == []
    latest = shadow.latest
    np.testing.assert_allclose(
        latest.heights_delta_above_others_m, 0.0, rtol=0, atol=HEIGHT_TOLERANCE_M
    )
    assert latest.nonplanarity_delta_m == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)
    assert latest.nonplanarity_m == pytest.approx(0.0, abs=HEIGHT_TOLERANCE_M)
    assert latest.is_geometry_valid


def test_a_raised_pad_shows_its_height_change_and_the_residual_change(geometry) -> None:
    """G1': RR 6 mm up -> d_RR = +6 mm, the others 0; G2: Delta r = 0.273 x 6 = 1.64 mm."""
    shadow = _shadow_on(geometry, np.zeros(4))
    lift = np.zeros(4)
    lift[RR] = 6e-3
    shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, _strokes_on_the_floor(geometry, lift), PAD_FORCES_N)
    changes = np.array(shadow.latest.heights_delta_above_others_m)
    np.testing.assert_allclose(changes, lift, rtol=0, atol=HEIGHT_TOLERANCE_M)
    expected = lift[RR] * _null_vector_share(geometry, RR)
    assert shadow.latest.nonplanarity_delta_m == pytest.approx(expected, rel=1e-9)
    assert expected == pytest.approx(1.64e-3, abs=0.01e-3)


def test_a_non_planar_reference_floor_reads_zero_change(geometry) -> None:
    """Spec 42.1 GE1'-a: reference on a floor with RR 30 mm low -> d = 0, Delta r = 0, absolute
    r = -0.272 x 30 mm; RR 6 mm lower still -> d_RR = -6 mm, the others 0, Delta r = -1.63 mm."""
    sunk = np.zeros(4)
    sunk[RR] = -SUNK_FLOOR_M
    shadow = _shadow_on(geometry, sunk)
    strokes = _strokes_on_the_floor(geometry, sunk)
    shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N)
    latest = shadow.latest
    np.testing.assert_allclose(latest.heights_delta_above_others_m, 0.0, rtol=0, atol=1e-9)
    assert latest.nonplanarity_delta_m == pytest.approx(0.0, abs=1e-9)
    expected_r = -_null_vector_share(geometry, RR) * SUNK_FLOOR_M
    assert latest.nonplanarity_m == pytest.approx(expected_r, rel=1e-9)
    # Spec rounds the share to 0.272; the trapezoid gives 0.2734 (r = -8.20 mm).
    assert expected_r == pytest.approx(-REAR_RESIDUAL_PER_OFFSET * SUNK_FLOOR_M, abs=0.05e-3)
    # The R4.1 absolute d keeps the non-planarity (+-15 mm): the reason for the change (37.2).
    assert max(map(abs, latest.heights_above_others_m)) > 0.01

    sunk_further = sunk.copy()
    sunk_further[RR] -= FURTHER_SINK_M
    strokes = _strokes_on_the_floor(geometry, sunk_further)
    shadow.update(2 * PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N)
    expected = np.zeros(4)
    expected[RR] = -FURTHER_SINK_M
    np.testing.assert_allclose(shadow.latest.heights_delta_above_others_m, expected, atol=1e-9)
    expected_delta_r = -_null_vector_share(geometry, RR) * FURTHER_SINK_M
    assert shadow.latest.nonplanarity_delta_m == pytest.approx(expected_delta_r, rel=1e-9)
    assert expected_delta_r == pytest.approx(-1.63e-3, abs=0.02e-3)  # spec: 0.272 x 6 mm


def test_the_residual_sign_is_fixed_by_rr(geometry) -> None:
    """r = [(I - P) h]_RR is linear: a 2 + 2 pattern of equal residual magnitudes keeps its
    sign under small perturbations (R4.1 picked a residual element and flipped)."""
    pattern = np.array([-1.0, 1.0, 1.0, -1.0]) * 8e-3
    shadow = _shadow_on(geometry, np.zeros(4))
    rng = np.random.default_rng(20261022)
    signs = set()
    for _ in range(50):
        lift = pattern + rng.normal(0.0, 0.05e-3, 4)
        strokes = _strokes_on_the_floor(geometry, lift)
        shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N)
        signs.add(math.copysign(1.0, shadow.latest.nonplanarity_m))
        expected_r = sum(_null_vector_share(geometry, leg) * lift[leg] for leg in range(4))
        assert shadow.latest.nonplanarity_m == pytest.approx(expected_r, rel=1e-6)
    assert signs == {-1.0}


def test_a_load_rise_reads_as_the_deflection_above(geometry) -> None:
    """Spec 34 GE1': +50 kN on FL at the same strokes -> FL 0.23 mm higher (sign +F / k_s)."""
    shadow = _shadow_on(geometry, np.zeros(4))
    strokes = _strokes_on_the_floor(geometry, np.zeros(4))
    forces = PAD_FORCES_N.copy()
    forces[FL] += 50e3
    shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, strokes, forces)
    changes = np.array(shadow.latest.heights_delta_above_others_m)
    normal_per_body_z = float(floor_normal(FLOOR_RAD) @ _level_from_body(*BODY_ATTITUDE_RAD)[:, 2])
    expected_fl = 50e3 / SHADOW_PAD_STIFFNESS_N_M * normal_per_body_z
    assert changes[FL] == pytest.approx(expected_fl, rel=1e-9)
    assert changes[FL] == pytest.approx(0.23e-3, abs=0.005e-3)
    np.testing.assert_allclose(np.delete(changes, FL), 0.0, atol=1e-12)


def test_the_reference_can_be_taken_from_the_pads(geometry) -> None:
    shadow = SupportGeometryShadow(geometry)
    strokes = _strokes_on_the_floor(geometry, np.zeros(4))
    reference = shadow.store_reference(0.0, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N, "done")
    np.testing.assert_allclose(reference.normal, floor_normal(FLOOR_RAD), atol=1e-12)
    assert reference.source == "done"
    assert reference.max_abs_height_change_m is None


def test_a_refresh_records_the_change_against_the_previous_reference(geometry) -> None:
    """Spec 37.3: max |Delta h| at a refresh (soft ground could hide accumulated sinking)."""
    shadow = _shadow_on(geometry, np.zeros(4))
    lift = np.array([0.0, 0.0, 0.0, -4e-3])
    strokes = _strokes_on_the_floor(geometry, lift)
    reference = shadow.store_reference(1.0, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N, "ready")
    assert reference.max_abs_height_change_m == pytest.approx(4e-3, rel=1e-9)
    assert [entry.source for entry in shadow.reference_history] == ["touch", "ready"]


def test_conditions_are_flagged_after_holding_half_a_second(geometry) -> None:
    """U28: G1-L of RR and G2 for an 8 mm lift, once per reference; a break restarts."""
    shadow = _shadow_on(geometry, np.zeros(4))
    lift = np.zeros(4)
    lift[RR] = 8e-3
    lifted = _strokes_on_the_floor(geometry, lift)
    grounded = _strokes_on_the_floor(geometry, np.zeros(4))
    hold_periods = round(SHADOW_HOLD_S / PERIOD_S)
    t_s = 0.0
    for strokes in [lifted] * (hold_periods - 1) + [grounded]:  # 0.48 s, then a break
        t_s += PERIOD_S
        assert shadow.update(t_s, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N) == []
    flagged = []
    for _ in range(hold_periods + 1):
        t_s += PERIOD_S
        flagged.append(shadow.update(t_s, BODY_ATTITUDE_RAD, lifted, PAD_FORCES_N))
    assert flagged[:-1] == [[]] * hold_periods
    # 8 mm RR also makes the absolute r 2.2 mm (> 1.4 mm): the floor information.
    assert sorted(flagged[-1]) == sorted(["G1L:RR", "G2", FLOOR_NONPLANAR_CONDITION])
    assert shadow.flags_t_s["G1L:RR"] == pytest.approx(t_s)
    t_s += PERIOD_S
    assert shadow.update(t_s, BODY_ATTITUDE_RAD, lifted, PAD_FORCES_N) == []  # once only
    shadow.store_reference(t_s, BODY_ATTITUDE_RAD, lifted, PAD_FORCES_N, "ready")
    assert shadow.flags_t_s == {}


def test_nothing_is_flagged_while_the_gate_is_closed(geometry) -> None:
    """GE1'-d: the 0.5 s run only counts with ``is_geometry_valid``; a closed gate restarts it."""
    shadow = _shadow_on(geometry, np.zeros(4))
    lift = np.zeros(4)
    lift[RR] = 8e-3
    lifted = _strokes_on_the_floor(geometry, lift)
    hold_periods = round(SHADOW_HOLD_S / PERIOD_S)
    t_s = 0.0
    for _ in range(3 * hold_periods):
        t_s += PERIOD_S
        assert shadow.update(t_s, BODY_ATTITUDE_RAD, lifted, PAD_FORCES_N, False) == []
    assert shadow.latest.heights_delta_above_others_m[RR] == pytest.approx(8e-3)
    assert not shadow.latest.is_geometry_valid
    assert shadow.max_abs_heights_delta_m.tolist() == [0.0] * 4  # gate-open samples only
    flagged = []
    for _ in range(hold_periods + 1):
        t_s += PERIOD_S
        flagged += shadow.update(t_s, BODY_ATTITUDE_RAD, lifted, PAD_FORCES_N, True)
    assert "G1L:RR" in flagged


def test_a_sunk_pad_is_flagged_below(geometry) -> None:
    shadow = _shadow_on(geometry, np.zeros(4))
    lift = np.zeros(4)
    lift[RR] = -8e-3
    strokes = _strokes_on_the_floor(geometry, lift)
    flagged = []
    for k in range(round(SHADOW_HOLD_S / PERIOD_S) + 1):
        flagged += shadow.update((k + 1) * PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N)
    assert sorted(flagged) == sorted(["G1S:RR", "G2", FLOOR_NONPLANAR_CONDITION])
    assert shadow.latest.nonplanarity_delta_m < 0.0


def test_nothing_is_recorded_before_a_reference_is_stored(geometry) -> None:
    shadow = SupportGeometryShadow(geometry)
    strokes = _strokes_on_the_floor(geometry, np.zeros(4))
    assert shadow.update(PERIOD_S, BODY_ATTITUDE_RAD, strokes, PAD_FORCES_N) == []
    assert shadow.latest is None
    meta = shadow.to_meta()
    assert meta["reference"] is None and meta["flags_t_s"] == {}
