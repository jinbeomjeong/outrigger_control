"""Engine-independent S1 pieces: geometry, analytic static start, linear statics, checks."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.frames import roll_pitch_from_quat
from outrigger_sim.geometry import (
    leg_com_body_m,
    pad_sphere_centre_body_m,
    pads_touching_origin_z_m,
)
from outrigger_sim.params import AugerLevel, load_params
from outrigger_sim.scenarios.settle import (
    analytic_static_pose,
    cross_settle_s,
    linear_static_solution,
)
from outrigger_sim.verify.checks import check_abs, check_equal, check_max, check_rel
from outrigger_sim.verify.reference import (
    L1_CONTACT_FORCE_N,
    L1_CYLINDER_FORCE_N,
    L1_STATIC_ATTITUDE_DEG,
    L1_STATIC_PENETRATION_MM,
    load_references,
)


@pytest.fixture(scope="module")
def refs():
    return load_references()


def _ext(params):
    e = params.contact.rigid_floor.L1.operating_extension_m
    return [e[i] for i in range(4)]


def test_geometry_at_operating_extension() -> None:
    params = load_params()
    ext = _ext(params)
    heights = pads_touching_origin_z_m(params, ext)
    # e_op is defined so that the crawler is lifted by the clearance with the pads touching
    assert np.allclose(heights, params.simulation.crawler_clearance_m, atol=1e-12)
    for i, leg in enumerate(params.legs):
        centre = pad_sphere_centre_body_m(params, i, ext[i])
        bottom_z = leg.pad_bottom_center_retracted_m[2] - ext[i]
        assert centre[2] == pytest.approx(bottom_z + leg.pad.swivel_center_above_pad_bottom_m)
        com = leg_com_body_m(params, i, ext[i])
        assert com[2] == pytest.approx(leg.moving_part.com_m[2] - ext[i])


def test_cross_settle_length_is_53_s() -> None:
    assert cross_settle_s(load_params()) == 53.0


@pytest.mark.parametrize("level", [lv.value for lv in AugerLevel])
def test_analytic_start_matches_reference(level: str, refs) -> None:
    params = load_params(level=level)
    pose = analytic_static_pose(params, refs, _ext(params))
    roll, pitch = roll_pitch_from_quat(np.asarray(pose.quat_wxyz))
    att = refs.get(L1_STATIC_ATTITUDE_DEG, level=level)
    assert math.degrees(float(roll)) == pytest.approx(att[0], abs=1e-12)
    assert math.degrees(float(pitch)) == pytest.approx(att[1], abs=1e-12)
    # individual penetrations follow from rounding of the reference values only
    assert np.max(np.abs(pose.penetration_residual_mm)) < 1e-3
    # small-angle model (dynamics_model.md 3.1): pad up-displacement = u_z + y phi - x theta
    pen = np.asarray(refs.get(L1_STATIC_PENETRATION_MM, level=level)) * 1e-3
    xy = np.array([leg.pad_bottom_center_retracted_m[:2] for leg in params.legs])
    phi, theta = math.radians(att[0]), math.radians(att[1])
    u_z_linear = float(np.mean(-pen - xy[:, 1] * phi + xy[:, 0] * theta))
    assert pose.u_z_m == pytest.approx(u_z_linear, abs=1e-6)


@pytest.mark.parametrize("level", [lv.value for lv in AugerLevel])
def test_linear_statics_reproduces_reference(level: str, refs) -> None:
    """Independent 3-DoF solve (dynamics_model.md 3.1) = reference values (6 digits)."""
    params = load_params(level=level)
    sol = linear_static_solution(params, params.contact.rigid_floor.L1.kn_per_pad_N_m)
    assert np.allclose(sol["contact_N"], refs.get(L1_CONTACT_FORCE_N, level=level), atol=1.0)
    assert np.allclose(sol["cylinder_N"], refs.get(L1_CYLINDER_FORCE_N, level=level), atol=1.0)
    assert np.allclose(
        sol["penetration_m"] * 1e3, refs.get(L1_STATIC_PENETRATION_MM, level=level), atol=1e-4
    )


def test_check_helpers() -> None:
    assert check_abs("V", "x", [1.0, 2.0], [1.0, 2.5], 0.5, "m").passed
    assert not check_abs("V", "x", [1.0, 2.0], [1.0, 2.6], 0.5, "m").passed
    assert check_rel("V", "x", 101.0, 100.0, 0.01, "N").passed
    assert not check_rel("V", "x", float("nan"), 100.0, 0.01, "N").passed
    assert check_max("V", "x", [0.1, 0.2], 0.2, "m").passed
    assert check_equal("V", "x", [1, 2], [1, 2]).passed
    assert check_rel("V", "x", 1.0, 1.0, 0.0, "").as_dict()["deviation"] == 0.0
