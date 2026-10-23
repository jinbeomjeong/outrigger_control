"""Crawler layout D, analytic settle pose and linear modes (scenarios/crawler_settle, S2b),
and the S2b command schedules (scenarios/stroke)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.frames import quat_to_matrix
from outrigger_sim.geometry import pad_sphere_centre_body_m
from outrigger_sim.params import load_params
from outrigger_sim.scenarios.crawler_settle import (
    crawler_layout,
    crawler_linear_modes,
    crawler_static_pose,
    pad_touch_extension_m,
)
from outrigger_sim.scenarios.stroke import (
    V11_END_HOLD_S,
    V11_HALF_GRID_S,
    Schedule,
    Segment,
    event_cases,
    expected_full_stroke_time_s,
    v11_schedule,
)
from outrigger_sim.verify.reference import (
    LIFT_V4_CRAWLER_ON_FLOOR_MODES,
    LIFT_V4_LAYOUT_D,
    load_references,
)


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


@pytest.fixture(scope="module")
def refs():
    return load_references()


def test_layout_d_counts_and_reference_order(params) -> None:
    layout = crawler_layout(params)
    assert layout.n_points == 24
    assert int(layout.is_roller.sum()) == 12
    order = layout.reference_order()
    assert sorted(order.tolist()) == list(range(24))
    assert layout.is_roller[order[:12]].all() and not layout.is_roller[order[12:]].any()


def test_linear_pose_reproduces_the_reference(params, refs) -> None:
    settled = refs.get(LIFT_V4_LAYOUT_D)["settled_on_crawler (legs at 0)"]
    q_ref = settled["q_about_origin (uz_mm, roll_deg, pitch_deg)"]
    pose = crawler_static_pose(params, linear=True)
    assert pose.u_z_m * 1e3 == pytest.approx(q_ref[0], abs=1e-3)
    assert pose.roll_deg == pytest.approx(q_ref[1], abs=1e-6)
    assert pose.pitch_deg == pytest.approx(q_ref[2], abs=1e-5)
    forces = pose.sphere_force_N[crawler_layout(params).reference_order()]
    np.testing.assert_allclose(forces, settled["crawler_sphere_forces_N"], atol=1.0)
    assert int(pose.active.sum()) == 14


def test_exact_pose_has_p_delta_and_equilibrium(params) -> None:
    exact = crawler_static_pose(params)
    linear = crawler_static_pose(params, linear=True)
    assert np.all(np.abs(exact.residual) < 1e-6)
    assert exact.sphere_force_N.sum() == pytest.approx(exact.weight_N, rel=1e-12)
    # P-delta tilts further forward (about 2.5 % at the top level)
    assert exact.pitch_deg > linear.pitch_deg
    assert exact.pitch_deg / linear.pitch_deg == pytest.approx(1.025, abs=0.005)


def test_modes_with_geometric_stiffness_match_reference(params, refs) -> None:
    modes = crawler_linear_modes(params, crawler_static_pose(params))
    ref = refs.get(LIFT_V4_CRAWLER_ON_FLOOR_MODES)
    assert modes.names == ("pitch", "roll", "heave")
    np.testing.assert_allclose(modes.f_undamped_Hz, ref["f_Hz"], rtol=0.005)
    np.testing.assert_allclose(modes.zeta, ref["zeta"], rtol=0.01)


def test_pad_touch_extension_puts_the_sphere_on_the_floor(params) -> None:
    pose = crawler_static_pose(params)
    rot = quat_to_matrix(np.asarray(pose.quat_wxyz))
    for i in range(4):
        e = pad_touch_extension_m(params, i, pose.origin_m, pose.quat_wxyz)
        centre = np.asarray(pose.origin_m) + rot @ pad_sphere_centre_body_m(params, i, e)
        radius = params.legs[i].pad.swivel_center_above_pad_bottom_m
        assert centre[2] - radius == pytest.approx(params.ground.crawler_bottom_z_m, abs=1e-12)
        assert 0.3 < e < 0.4


def test_schedule_emits_each_segment_once() -> None:
    sched = Schedule([Segment(0.0, (1, 0, 0, 0)), Segment(0.5, (0, 0, 0, 0))], 1.0)
    got = [sched(10.0 + k * 0.1) for k in range(10)]
    emitted = [g for g in got if g is not None]
    assert len(emitted) == 2
    assert got[0] is not None and got[5] is not None
    np.testing.assert_array_equal(sched.command_at(0.7), [0, 0, 0, 0])


LEGACY_PARAMS_PATH = (
    Path(__file__).resolve().parents[2]
    / "02_params" / "history" / "rexome33_2026-10-22_before_rexome35.yaml"
)


def test_v11_schedule_keeps_the_0_68_m_times_on_the_old_yaml() -> None:
    """The 0.68 m stroke YAML still gives the 31 s / 62 s schedule bit for bit."""
    sched = v11_schedule(load_params(LEGACY_PARAMS_PATH, level="top"))
    assert sched.segments[1].t0_s == 31.0
    assert sched.end_s == 62.0


def test_v11_and_event_schedules(params) -> None:
    sched = v11_schedule(params)
    half_s = sched.segments[1].t0_s
    assert sched.end_s == 2.0 * half_s
    # each half = ceil_0.1(full stroke + fixed end hold 0.9 s) (dynamics_model.md 5.12.12)
    full_with_ramp_s = expected_full_stroke_time_s(params)
    assert full_with_ramp_s + V11_END_HOLD_S <= half_s
    assert half_s < full_with_ramp_s + V11_END_HOLD_S + V11_HALF_GRID_S
    assert round(half_s / V11_HALF_GRID_S, 9).is_integer()
    full_stroke_s = params.actuator.stroke_m / params.actuator.max_speed_m_s + 0.1
    assert expected_full_stroke_time_s(params, 0.1) == pytest.approx(full_stroke_s, rel=1e-12)
    for case in event_cases(params):
        assert case.expected_events() == [(0, 1), (0, 2), (0, 1)]
        assert case.schedule().end_s > 0.0
