"""Analytic settled pose of the machine on the crawler on a sloped floor (S6 stage-2 starts).

Extends :func:`outrigger_sim.scenarios.crawler_settle.crawler_static_pose` (S2b, level floor)
to a floor tilted as in :mod:`outrigger_sim.scenarios.slope` (plane through ``(0, 0,
ground.crawler_bottom_z_m)``, ``floor_normal(roll, pitch)``, ``floor_rotation``). Engine
independent (numpy).

Formulation in floor coordinates (z = floor normal, floor plane ``z = z_floor``): the whole
machine (superstructure + four moving parts at the given extensions) is one rigid body on the
24 one-sided normal springs ``F_i = kn max(delta_i, 0)`` (exact sphere-plane overlap) plus the
crawler anchor bushings (``chrono/crawler_bushing``), which carry the in-plane part of gravity
``T = -m g_xy`` (floor axes). ASSUMPTION of the start: ``T`` is shared equally by the active
spheres (equal ``kt``, rigid in-plane translation) and acts at the sphere centres (ball-centre
force point). Unknowns ``z0``, roll, pitch of the body relative to the floor frame (yaw 0, in-
plane position 0); equations: normal force sum = ``m g cos(beta)``, moments about the composite
centre of mass (x, y) = 0. Newton with a numerical Jacobian (as S2b).

The Chrono run starts there with the anchor bushings at zero deformation (preload 0, user
instruction 2026-10-21), so the in-plane load builds up in a short transient (bushing stretch
``|T| / sum kt``, about 0.6 mm at 3.5 deg) before the settle window.

Units SI; angles in rad unless named ``*_deg``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import matrix_to_quat, quat_from_euler_zyx, quat_to_matrix
from outrigger_sim.params import Params
from outrigger_sim.scenarios.crawler_settle import (
    FD_STEP,
    NEWTON_MAX_ITER,
    NEWTON_TOL_N,
    composite_mass,
    crawler_layout,
)
from outrigger_sim.scenarios.slope import floor_normal, floor_rotation


@dataclass(frozen=True)
class CrawlerSlopePose:
    """Start of a crawler settle on a sloped floor (world frame unless named ``*_floor``)."""

    floor_roll_deg: float
    floor_pitch_deg: float
    floor_pos_m: tuple[float, float, float]
    floor_quat_wxyz: tuple[float, float, float, float]
    origin_m: tuple[float, float, float]
    quat_wxyz: tuple[float, float, float, float]
    body_roll_deg: float
    body_pitch_deg: float
    """Body attitude in the world (ZYX), what the IMU sees on the crawler."""
    rel_roll_deg: float
    rel_pitch_deg: float
    """Body attitude relative to the floor plane (crawler compliance)."""
    sphere_force_N: NDArray[np.float64]
    """(24,) normal force per sphere, layout order."""
    sphere_penetration_m: NDArray[np.float64]
    tangential_per_active_N: NDArray[np.float64]
    """(2,) in-plane force per active sphere, floor axes."""
    active: NDArray[np.bool_]
    weight_N: float
    residual: NDArray[np.float64]
    iterations: int


def _state(q, centres, radius, floor_z, kn, com_body, m_g_floor, tangential=True):
    z0, roll, pitch = (float(v) for v in q)
    rot = quat_to_matrix(quat_from_euler_zyx(0.0, pitch, roll))
    origin = np.array([0.0, 0.0, z0])
    world = origin + centres @ rot.T
    g = origin + rot @ com_body
    overlap = radius - (world[:, 2] - floor_z)
    force = kn * np.maximum(overlap, 0.0)
    active = overlap > 0.0
    n_act = max(int(active.sum()), 1)
    t_each = -m_g_floor[:2] / n_act if tangential else np.zeros(2)  # in-plane share
    r = world - g
    mx = float(np.sum(force * r[:, 1]) - np.sum(np.where(active, r[:, 2], 0.0)) * t_each[1])
    my = float(-np.sum(force * r[:, 0]) + np.sum(np.where(active, r[:, 2], 0.0)) * t_each[0])
    return np.array([float(force.sum()) + m_g_floor[2], mx, my]), force, overlap, t_each


def crawler_slope_pose(
    params: Params,
    floor_roll_deg: float,
    floor_pitch_deg: float,
    *,
    float32_kn: bool = True,
    tangential: bool = True,
) -> CrawlerSlopePose:
    """Static start on the crawler for a floor named like ``scenarios/slope`` (roll, pitch
    of the floor = the body attitude it would give a rigid machine; pitch + = nose down).

    Args:
        tangential: Include the in-plane gravity share in the moment balance (the settled
            end state, default); False = the start of a run whose in-plane gravity is ramped
            from 0 (normal-only balance with the normal gravity component, S6 snapshots).

    Raises:
        RuntimeError: Newton did not converge.
    """
    layout = crawler_layout(params)
    z_floor = params.ground.crawler_bottom_z_m
    kn = float(params.get("contact.crawler.kn_per_sphere_N_m"))
    if float32_kn:
        kn = float(np.float32(kn))
    ext = tuple(0.0 for _ in params.legs)
    comp = composite_mass(params, ext)
    weight = comp.mass_kg * params.meta.gravity_m_s2
    rf = floor_rotation(floor_normal(floor_roll_deg, floor_pitch_deg))
    m_g_floor = comp.mass_kg * (rf.T @ np.array([0.0, 0.0, -params.meta.gravity_m_s2]))
    centres = layout.centres_body_m(z_floor)
    r = layout.sphere_radius_m
    q = np.array([m_g_floor[2] / (kn * int(layout.is_roller.sum())), 0.0, 0.0])
    h = np.asarray(FD_STEP)
    res = np.full(3, np.inf)
    iterations = 0
    for iterations in range(1, NEWTON_MAX_ITER + 1):  # noqa: B007
        res, _, _, _ = _state(q, centres, r, z_floor, kn, comp.com_body_m, m_g_floor, tangential)
        if np.all(np.abs(res) < NEWTON_TOL_N):
            break
        jac = np.empty((3, 3))
        for j in range(3):
            dq = np.zeros(3)
            dq[j] = h[j]
            rp = _state(q + dq, centres, r, z_floor, kn, comp.com_body_m, m_g_floor, tangential)[0]
            rm = _state(q - dq, centres, r, z_floor, kn, comp.com_body_m, m_g_floor, tangential)[0]
            jac[:, j] = (rp - rm) / (2.0 * h[j])
        q = q - np.linalg.solve(jac, res)
    else:
        raise RuntimeError(f"crawler slope pose did not converge: residual {res}")
    res, force, overlap, t_each = _state(q, centres, r, z_floor, kn, comp.com_body_m, m_g_floor, tangential)
    q_rel = quat_from_euler_zyx(0.0, float(q[2]), float(q[1]))
    p0 = np.array([0.0, 0.0, z_floor])
    floor_pos = p0 - rf @ p0
    origin_world = floor_pos + rf @ np.array([0.0, 0.0, float(q[0])])
    rot_world = rf @ quat_to_matrix(q_rel)
    quat_world = matrix_to_quat(rot_world)
    yaw_w = math.atan2(rot_world[1, 0], rot_world[0, 0])
    pitch_w = math.asin(-max(-1.0, min(1.0, rot_world[2, 0])))
    roll_w = math.atan2(rot_world[2, 1], rot_world[2, 2])
    del yaw_w
    return CrawlerSlopePose(
        floor_roll_deg=float(floor_roll_deg),
        floor_pitch_deg=float(floor_pitch_deg),
        floor_pos_m=tuple(float(v) for v in floor_pos),  # type: ignore[arg-type]
        floor_quat_wxyz=tuple(float(v) for v in matrix_to_quat(rf)),  # type: ignore[arg-type]
        origin_m=tuple(float(v) for v in origin_world),  # type: ignore[arg-type]
        quat_wxyz=tuple(float(v) for v in quat_world),  # type: ignore[arg-type]
        body_roll_deg=math.degrees(roll_w),
        body_pitch_deg=math.degrees(pitch_w),
        rel_roll_deg=math.degrees(float(q[1])),
        rel_pitch_deg=math.degrees(float(q[2])),
        sphere_force_N=force,
        sphere_penetration_m=overlap,
        tangential_per_active_N=t_each,
        active=overlap > 0.0,
        weight_N=weight,
        residual=res,
        iterations=iterations,
    )


__all__ = ["CrawlerSlopePose", "crawler_slope_pose"]
