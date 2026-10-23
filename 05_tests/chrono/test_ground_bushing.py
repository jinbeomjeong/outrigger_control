"""S0 checks of ``chrono/ground_bushing.GroundBushingCoulomb`` (chrono_build_plan.md S0, R7, R15).

* Block regression (plan S0 table): the library port against ``stick_friction.json``
  cases "Bushing 2deg", "Bushing flat v0", "Bushing 30deg (tan>mu, must slide)" at the
  baseline dt 2e-4 s, with the default L1 solver (SPARSE_LU, locked pattern).
* Hysteresis (R15): lift a block off the floor and put it down again: one removal, one
  creation, no chatter; lift-off ``n_lift`` steps after the first ``N <= 0`` step at dt 1e-4
  and 1e-5 s; re-created anchor at the landing point; locked vs unlocked sparsity pattern
  identical across the add/remove events.
* Four legs from the YAML (``from_params``): values, independence of the legs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.ground_bushing import (  # noqa: E402
    EVENT_CREATE,
    EVENT_REMOVE,
    LIFT_TIME_S,
    TOUCH_THRESHOLD_N,
    GroundBushingCoulomb,
    lift_step_count,
    surface_rotation_wxyz,
)
from outrigger_sim.chrono.system import make_system  # noqa: E402
from outrigger_sim.params import LEG_ORDER, Params  # noqa: E402

pytestmark = pytest.mark.chrono

# Plan S0 tolerances.
SLIP_2DEG_MAX_M = 1.0e-6  # < 1e-3 mm
ELASTIC_REL_TOL = 1.0e-3  # +-0.1 %
FREQ_REL_TOL = 1.0e-3  # +-0.1 %
ZETA_REL_TOL = 2.0e-2  # +-2 %
SLIDE_REL_TOL = 5.0e-3  # +-0.5 %
RECORD_EVERY_S = 1.0e-3  # sampling of the baseline script (1e-3 / dt steps)
FLOAT32_ULP_REL = 2.0**-23
NORMAL_FORCE_ULP_MARGIN = 1.5  # dynamics 5.12.12: tolerance 1.5 k_n ulp (about 4.7 N)

# Lift-and-drop profile (test assumption): vertical force as a fraction of the block weight,
# ramps slow against the 7.4 Hz normal mode so that the block leaves and lands gently.
# 0.2-0.5 s ramp 0 -> 1.01 W (leaves the floor near 0.5 s), hold to 0.55 s, ramp to 0.5 W by
# 0.6 s (lands at about 0.6 s with half the weight, no bounce), 0.8-1.0 s ramp to 0.
# A horizontal push of 0.002 W in 0.5-0.6 s moves the landing point.
LIFT_END_S = 1.2
LIFT_HORIZONTAL_FRACTION = 0.002


def _lift_profile(t: float) -> tuple[float, float]:
    if t < 0.2:
        up = 0.0
    elif t < 0.5:
        up = 1.01 * (t - 0.2) / 0.3
    elif t < 0.55:
        up = 1.01
    elif t < 0.6:
        up = 1.01 - 0.51 * (t - 0.55) / 0.05
    elif t < 0.8:
        up = 0.5
    elif t < 1.0:
        up = 0.5 * (1.0 - (t - 0.8) / 0.2)
    else:
        up = 0.0
    horizontal = LIFT_HORIZONTAL_FRACTION if 0.5 <= t < 0.6 else 0.0
    return up, horizontal


def _run_cases(model: Any, t_end: float) -> tuple[np.ndarray, np.ndarray]:
    every = max(1, round(RECORD_EVERY_S / model.dt_s))
    steps = round(t_end / model.dt_s)
    times, along = [], []
    for k in range(steps + 1):
        if k % every == 0:
            times.append(model.system.GetChTime())
            along.append(float((model.pos() - model.start_pos) @ model.tangent))
        if k == steps:
            break
        model.step()
    return np.array(times), np.array(along)


def _osc_fit(t: np.ndarray, x: np.ndarray, f_guess: float) -> tuple[float, float]:
    from scipy.optimize import curve_fit

    y = x - x[-1]

    def fun(tt: np.ndarray, a: float, b: float, s: float, w: float) -> np.ndarray:
        return np.exp(-s * tt) * (a * np.cos(w * tt) + b * np.sin(w * tt))

    p, _ = curve_fit(
        fun, t, y, p0=[y[0], np.max(np.abs(y)), 1.0, 2 * math.pi * f_guess], maxfev=20000
    )
    wn = math.hypot(p[2], p[3])
    return wn / (2 * math.pi), p[2] / wn


# --- unit-level ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dt", "expected"), [(1e-4, 10), (1e-5, 100), (2e-4, 5), (3e-4, 4), (1e-3, 1), (5e-3, 1)]
)
def test_lift_step_count_is_time_based(dt: float, expected: int) -> None:
    assert lift_step_count(LIFT_TIME_S, dt) == expected


def test_r15_assumed_constants() -> None:
    assert LIFT_TIME_S == 1.0e-3
    assert TOUCH_THRESHOLD_N == 100.0


@pytest.mark.parametrize("normal", [(0, 0, 1), (math.sin(0.3), 0, math.cos(0.3)), (1, 0, 0)])
def test_surface_rotation_maps_z_to_normal(normal: tuple[float, float, float]) -> None:
    w, x, y, z = surface_rotation_wxyz(normal)
    rotated = ch.ChQuaterniond(w, x, y, z).Rotate(ch.ChVector3d(0, 0, 1))
    n = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    assert np.allclose([rotated.x, rotated.y, rotated.z], n, atol=1e-14)


def test_slope_frame_equals_baseline_quaternion() -> None:
    q = ch.QuatFromAngleY(math.radians(30.0))
    ours = surface_rotation_wxyz((math.sin(math.radians(30)), 0, math.cos(math.radians(30))))
    assert np.allclose(ours, [q.e0, q.e1, q.e2, q.e3], atol=1e-15)


# --- block regression (plan S0) ---------------------------------------------------------


def test_block_2deg_sticks(
    block_factory: Callable[..., Any], stick_reference: dict[str, Any]
) -> None:
    ref = stick_reference["cases"]["Bushing 2deg"]
    model = block_factory(2.0)
    _, along = _run_cases(model, ref["t_end_s"])
    slip = float(model.bushing.slip_total_m[0] @ model.tangent)
    elastic = along[-1] - slip
    assert abs(slip) < SLIP_2DEG_MAX_M
    assert model.bushing.yield_steps[0] == ref["bushing_yield_steps"] == 0
    assert elastic == pytest.approx(ref["bushing_elastic_disp_m"], rel=ELASTIC_REL_TOL)
    assert model.bushing.events == ()


def test_block_flat_v0_frequency_and_damping(
    block_factory: Callable[..., Any], stick_reference: dict[str, Any]
) -> None:
    ref = stick_reference["cases"]["Bushing flat v0"]
    model = block_factory(0.0, v0=tuple(ref["v0_m_s"]))
    t, along = _run_cases(model, ref["t_end_s"])
    f_hz, zeta = _osc_fit(t, along, stick_reference["reference"]["f_tangential_Hz"])
    assert f_hz == pytest.approx(ref["f_tangential_Hz"], rel=FREQ_REL_TOL)
    assert zeta == pytest.approx(ref["zeta_tangential"], rel=ZETA_REL_TOL)


def test_block_30deg_slides(
    block_factory: Callable[..., Any], stick_reference: dict[str, Any]
) -> None:
    ref = stick_reference["cases"]["Bushing 30deg (tan>mu, must slide)"]
    model = block_factory(30.0)
    _, along = _run_cases(model, ref["t_end_s"])
    slip = float(model.bushing.slip_total_m[0] @ model.tangent)
    assert slip == pytest.approx(ref["bushing_slip_along_slope_m"], rel=SLIDE_REL_TOL)
    assert along[-1] == pytest.approx(ref["disp_end_m"], rel=SLIDE_REL_TOL)
    assert model.bushing.sliding[0]


# --- hysteresis (R15) ---------------------------------------------------------------------


def _lift_and_drop(model: Any) -> dict[str, Any]:
    accumulator = model.block.AddAccumulator()
    steps = round(LIFT_END_S / model.dt_s)
    times = np.empty(steps)
    normal_raw = np.empty(steps)
    positions = np.empty((steps, 3))
    landing: dict[str, Any] = {}
    for k in range(steps):
        up, horizontal = _lift_profile(model.system.GetChTime())
        model.block.EmptyAccumulator(accumulator)
        model.block.AccumulateForce(
            accumulator,
            ch.ChVector3d(horizontal * model.weight_N, 0.0, up * model.weight_N),
            ch.ChVector3d(*model.pos()),
            False,
        )
        events = model.step()
        times[k] = model.system.GetChTime()
        normal_raw[k] = model.bushing.normal_force_raw_N[0]
        positions[k] = model.pos()
        for event in events:
            if event.kind == EVENT_CREATE:
                landing = {
                    "block_xy": model.pos()[:2].copy(),
                    "anchor_xy": model.bushing.anchors_world_m()[0, :2].copy(),
                }
    return {
        "t": times,
        "N": normal_raw,
        "pos": positions,
        "events": model.bushing.events,
        "landing": landing,
    }


@pytest.mark.parametrize("dt", [1.0e-4, 1.0e-5])
def test_lift_and_drop_hysteresis(block_factory: Callable[..., Any], dt: float) -> None:
    model = block_factory(0.0, dt=dt)
    run = _lift_and_drop(model)
    kinds = [e.kind for e in run["events"]]
    assert kinds == [EVENT_REMOVE, EVENT_CREATE]  # one lift-off, one re-touch, no chatter
    zero = run["N"] <= 0.0
    # exactly one contact-loss interval in the force signal, so the count is not luck
    assert int(np.count_nonzero(np.diff(zero.astype(int)) == 1)) == 1
    first_zero = int(np.argmax(zero))
    n_lift = lift_step_count(LIFT_TIME_S, dt)
    removal_t = run["events"][0].t_s
    assert removal_t == pytest.approx(run["t"][first_zero + n_lift - 1], abs=0.1 * dt)
    assert np.all(zero[first_zero : first_zero + n_lift])
    # re-touch on the first step with N > N_th
    touch_index = int(np.argmax((run["N"] > TOUCH_THRESHOLD_N) & (run["t"] > removal_t)))
    assert run["events"][1].t_s == pytest.approx(run["t"][touch_index], abs=0.1 * dt)
    # the block really left the floor and moved sideways before landing
    assert run["pos"][:, 2].max() - model.start_pos[2] > 1.0e-3
    landing = run["landing"]
    assert np.linalg.norm(landing["block_xy"] - model.start_pos[:2]) > 5.0e-5
    # new anchor = contact point under the sphere centre at creation (zero tangential force)
    assert np.allclose(landing["anchor_xy"], landing["block_xy"], atol=1e-12)
    assert model.bushing.in_contact[0]


def test_lift_and_drop_sparsity_lock_is_transparent(block_factory: Callable[..., Any]) -> None:
    """Bushing add/remove through the system re-analyses the locked pattern (R11, R15)."""
    locked = _lift_and_drop(block_factory(0.0, dt=1.0e-4, lock=True))
    unlocked = _lift_and_drop(block_factory(0.0, dt=1.0e-4, lock=False))
    assert [e.kind for e in locked["events"]] == [e.kind for e in unlocked["events"]]
    assert [e.t_s for e in locked["events"]] == [e.t_s for e in unlocked["events"]]
    assert np.max(np.abs(locked["pos"] - unlocked["pos"])) <= 1.0e-12


# --- four legs from the YAML ------------------------------------------------------------


def test_four_legs_from_params(params: Params) -> None:
    """Four independent pad blocks on the default floor; only the pushed leg responds."""
    bundle = make_system(params)  # default floor plate at ground.crawler_bottom_z_m, FL values
    system, floor = bundle.system, bundle.floor
    top_z = params.ground.crawler_bottom_z_m
    g = params.meta.gravity_m_s2
    kn = params.contact.rigid_floor.L1.kn_per_pad_N_m[0]
    bodies, centres = [], []
    for i, leg in enumerate(params.legs):
        mass = leg.moving_part.mass_kg
        radius = leg.pad.swivel_center_above_pad_bottom_m
        body = ch.ChBody()
        body.SetName(f"moving_{leg.name}")
        body.SetMass(mass)
        body.SetInertiaXX(ch.ChVector3d(1.0, 1.0, 1.0))
        body.SetPos(ch.ChVector3d(3.0 * i, 0.0, top_z + radius - mass * g / kn))
        body.EnableCollision(True)
        body.AddCollisionShape(
            ch.ChCollisionShapeSphere(bundle.floor_material, radius), ch.ChFramed()
        )
        system.Add(body)
        align = ch.ChLinkLockAlign()
        align.Initialize(body, floor, ch.ChFramed(body.GetPos(), ch.QUNIT))
        system.Add(align)
        bodies.append(body)
        centres.append((0.0, 0.0, 0.0))
    gb = GroundBushingCoulomb.from_params(params, system, floor, bodies, centres, dt_s=bundle.dt_s)
    l1 = params.contact.rigid_floor.L1
    assert gb.leg_names == LEG_ORDER
    assert gb.n_lift == lift_step_count(LIFT_TIME_S, bundle.dt_s)
    gb.attach()
    assert gb.in_contact.all()
    anchors = gb.anchors_world_m()
    assert np.allclose(anchors[:, 2], top_z, atol=1e-12)
    for i, leg in enumerate(gb._legs):  # noqa: SLF001 - check the Chrono inputs directly
        k = leg.bushing.GetStiffness()
        c = leg.bushing.GetDamping()
        assert (k.x, k.y, k.z) == (
            l1.bushing_stiffness_per_pad_N_m[i],
            l1.bushing_stiffness_per_pad_N_m[i],
            0.0,
        )
        assert c.x == l1.bushing_damping_input_per_pad_N_s_m[i]
        assert c.x == pytest.approx(0.5 * l1.ct_per_pad_N_s_m[i], rel=1e-8)  # R7
    push = bodies[1].AddAccumulator()
    for _ in range(round(0.2 / bundle.dt_s)):
        bodies[1].EmptyAccumulator(push)
        bodies[1].AccumulateForce(push, ch.ChVector3d(0.0, 500.0, 0.0), bodies[1].GetPos(), False)
        system.DoStepDynamics(bundle.dt_s)
        gb.after_step()
    force = gb.tangential_force_world_N()
    assert gb.events == ()
    assert force[1, 1] == pytest.approx(-500.0, rel=1e-2)  # bushing holds the push (stick)
    others = np.delete(np.abs(force), 1, axis=0)
    # Bullet contact noise at |z| ~ 1 m gives ~0.01 N on the unpushed legs (2e-5 of the push)
    assert others.max() < 0.1
    for i, leg in enumerate(params.legs):
        height_m = abs(bodies[i].GetPos().z)
        # Bullet contact distance is float32: one ulp (2^-23 relative, |z| >= 1 m) times k_n
        tolerance_N = NORMAL_FORCE_ULP_MARGIN * kn * FLOAT32_ULP_REL * max(1.0, height_m)
        expected_N = leg.moving_part.mass_kg * g
        assert gb.normal_force_N[i] == pytest.approx(expected_N, abs=tolerance_N), leg.name
