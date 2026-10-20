"""scenarios/slope (S2a V12): floor plane, start pose, gravity ramp, reference split."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.frames import quat_to_matrix
from outrigger_sim.params import load_params
from outrigger_sim.scenarios.slope import (
    RAMP_S,
    floor_normal,
    floor_rotation,
    gravity_ramp,
    parse_case,
    reference_reaction_world_N,
    settle_after_ramp_s,
    slope_start,
    split_normal_tangential,
)
from outrigger_sim.verify.reference import SLOPE_V12_CASES, SLOPE_V12_L1, load_references


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


@pytest.fixture(scope="module")
def refs():
    return load_references()


def test_parse_case_names() -> None:
    assert parse_case("ground roll -2 deg, pitch 1.5 deg") == (-2.0, 1.5)
    assert [parse_case(c) for c in SLOPE_V12_CASES] == [(0.0, 2.0), (2.0, 0.0), (-2.0, 1.5)]
    with pytest.raises(ValueError):
        parse_case("roll 2, pitch 0")


def test_floor_normal_sign_convention() -> None:
    # pitch + = nose down: the floor falls towards +x, so its normal leans to +x
    n = floor_normal(0.0, 2.0)
    assert n[0] == pytest.approx(math.sin(math.radians(2.0)))
    assert n[1] == 0.0
    # roll +: floor z = tan(roll) y rises to +y, normal leans to -y
    n = floor_normal(2.0, 0.0)
    assert n[1] == pytest.approx(-math.sin(math.radians(2.0)))
    assert np.linalg.norm(floor_normal(-2.0, 1.5)) == pytest.approx(1.0)


def test_floor_rotation_is_proper_and_maps_z_to_normal() -> None:
    n = floor_normal(-2.0, 1.5)
    r = floor_rotation(n)
    assert np.allclose(r.T @ r, np.eye(3), atol=1e-15)
    assert np.linalg.det(r) == pytest.approx(1.0)
    assert np.allclose(r[:, 2], n)
    # x axis = world x projected onto the plane
    x_proj = np.array([1.0, 0.0, 0.0]) - n[0] * n
    assert np.allclose(r[:, 0], x_proj / np.linalg.norm(x_proj), atol=1e-15)


def test_gravity_ramp_is_c1_half_cosine() -> None:
    assert gravity_ramp(-1.0) == 0.0
    assert gravity_ramp(0.0) == 0.0
    assert gravity_ramp(RAMP_S) == 1.0
    assert gravity_ramp(10.0) == 1.0
    assert gravity_ramp(0.5 * RAMP_S) == pytest.approx(0.5)
    t = np.linspace(0.0, RAMP_S, 3001)
    g = np.array([gravity_ramp(v) for v in t])
    assert np.all(np.diff(g) >= 0.0)
    slope = np.diff(g) / np.diff(t)
    assert slope[0] < 1e-3 and slope[-1] < 1e-3  # zero slope at both ends


def test_settle_after_ramp_is_ceil_of_yaml(params) -> None:
    assert settle_after_ramp_s(params) == 53.0


@pytest.mark.parametrize("case", SLOPE_V12_CASES)
def test_slope_start_touches_plane_and_matches_reference_extensions(params, refs, case) -> None:
    st = slope_start(params, refs, case)
    assert np.max(np.abs(st.sphere_gap_m)) < 1e-12
    # the reference extensions are rounded to 0.1 mm
    assert np.max(np.abs(st.extension_minus_ref_mm)) <= 0.05 + 1e-9
    assert np.mean(st.extension_minus_ref_mm) == pytest.approx(0.0, abs=1e-12)
    # the world point (0, 0, z_floor) stays on the rotated floor surface
    rot = quat_to_matrix(np.asarray(st.floor_quat_wxyz))
    local = rot.T @ (np.asarray(st.floor_point_world_m) - np.asarray(st.floor_pos_m))
    assert local[2] == pytest.approx(params.ground.crawler_bottom_z_m, abs=1e-14)
    assert np.allclose(rot[:, 2], st.normal_world)


@pytest.mark.parametrize("case", SLOPE_V12_CASES)
def test_reference_split_reproduces_friction_utilisation(refs, case) -> None:
    block = refs.get(SLOPE_V12_L1, case=case)
    reaction = reference_reaction_world_N(
        block["contact_vertical_N"], block["contact_horizontal_xy_N"]
    )
    n_part, t_part = split_normal_tangential(reaction, floor_normal(*parse_case(case)))
    assert np.allclose(
        t_part / n_part, block["friction_utilisation_T_over_N"], rtol=2e-3, atol=2e-5
    )
