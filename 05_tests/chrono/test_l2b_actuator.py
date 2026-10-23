"""S7 L2b-NSC building blocks (chrono_build_plan.md S7 checklist 1-3): guide x, y release,
explicit force law with s_ref and per-step 210 bar saturation, lateral bushing.

Single-leg model ``chrono/single_leg_l2b`` (fixed frame, NSC PSOR 50). Expected values are
derived here from the YAML (no reference.json value is used; the S7 V0-V14 references are
being regenerated for REXOME35 by dynamics-expert).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.actuation import SpeedReference  # noqa: E402
from outrigger_sim.chrono.actuators import L1SpeedActuator, make_motion_function  # noqa: E402
from outrigger_sim.chrono.l2b_actuator import GUIDE_FREE_XY  # noqa: E402
from outrigger_sim.chrono.single_leg_l2b import SingleLegL2bModel, run_steps  # noqa: E402
from outrigger_sim.chrono.system import make_system  # noqa: E402
from outrigger_sim.params import Params, load_params  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def p2() -> Params:
    return load_params(model="L2b_NSC")


# --- API (risk 1) -------------------------------------------------------------------------


def test_guide_constraint_is_exposed_and_frees_x_y() -> None:
    """``SetGuideConstraint(c_x, c_y, c_rx, c_ry, c_rz)`` (ChLinkMotorLinear.cpp:41) is in
    pychrono 10.0.0; the force motor (c_z false) then has 3 bilateral constraints (rx, ry,
    rz), PRISMATIC 5, FREE 0."""
    counts = {}
    for name, args in (
        ("prismatic", None),
        ("free_xy", GUIDE_FREE_XY),
        ("free", (False, False, False, False, False)),
    ):
        sys_ = ch.ChSystemNSC()
        a, b = ch.ChBody(), ch.ChBody()
        b.SetFixed(True)
        sys_.Add(a)
        sys_.Add(b)
        motor = ch.ChLinkMotorLinearForce()
        if args is not None:
            motor.SetGuideConstraint(*args)
        motor.Initialize(a, b, False, ch.ChFramed(), ch.ChFramed())
        sys_.Add(motor)
        counts[name] = motor.GetNumConstraintsBilateral()
    assert counts == {"prismatic": 5, "free_xy": 3, "free": 0}
    assert hasattr(ch.ChLinkMotorLinear, "GuideConstraint_FREE")


def test_psor_refuses_stiff_bushing_loads() -> None:
    """Why the lateral bushing is explicit (``chrono/lateral_bushing``): PSOR rejects a
    ``ChLoadBodyBodyBushingSpherical`` (stiffness / damping matrices)."""
    sys_ = ch.ChSystemNSC()
    sys_.SetGravitationalAcceleration(ch.ChVector3d(0, 0, -9.81))
    a, b = ch.ChBody(), ch.ChBody()
    b.SetFixed(True)
    sys_.Add(a)
    sys_.Add(b)
    load = ch.ChLoadBodyBodyBushingSpherical(
        a, b, ch.ChFramed(), ch.ChVector3d(1e6, 1e6, 0), ch.ChVector3d(1e3, 1e3, 0)
    )
    container = ch.ChLoadContainer()
    container.Add(load)
    sys_.Add(container)
    with pytest.raises(RuntimeError, match="stiffness or damping"):
        sys_.DoStepDynamics(1e-4)


def test_make_system_l2b_settings(p2: Params) -> None:
    bundle = make_system(p2, "L2b_NSC")
    assert isinstance(bundle.system, ch.ChSystemNSC)
    s = bundle.settings
    assert s["solver"]["type"] == "PSOR" and s["solver"]["max_iterations"] == 50
    assert s["contact"]["crawler_material"]["friction"] == p2.l2b.rigid_floor.crawler_friction
    assert bundle.floor_material.GetStaticFriction() == pytest.approx(p2.l2b.rigid_floor.friction)
    assert bundle.dt_s == p2.l2b.dt_s


# --- speed reference = L1 limiter -----------------------------------------------------------


def test_speed_reference_matches_l1_actuator_bit_for_bit() -> None:
    """Same limiter as ``L1SpeedActuator.advance`` (ramp, braking, law C incl. the inertia
    term) for random commands, forces and stroke-end approaches."""
    rng = np.random.default_rng(7)
    n, dt, v, ramp = 3, 2e-4, 0.0209243016, 0.1
    ext = [278737.808, 278737.808, 199568.0]
    ret = [79168.1349, 79168.1349, 66000.0]
    mass = [106.78, 106.78, 73.16]
    s0 = [0.02, 0.35, 0.68]
    l1 = L1SpeedActuator(
        [object()] * n, [make_motion_function(x) for x in s0], s0, [(0.0, 0.7)] * n,
        max_speed_m_s=v, ramp_s=ramp, max_force_extend_N=ext, max_force_retract_N=ret,
        rod_mass_kg=mass,
    )
    ref = SpeedReference(
        s0, [(0.0, 0.7)] * n, max_speed_m_s=v, ramp_s=ramp, max_force_extend_N=ext,
        max_force_retract_N=ret, rod_mass_kg=mass,
    )
    t = 0.0
    for k in range(20000):
        if k % 400 == 0:
            cmd = rng.choice([-1.0, -0.01, 0.0, 0.004, 1.0], size=n)
            l1.set_command(cmd)
            ref.set_command(cmd)
        f = rng.normal(1.0e5, 1.2e5, size=n)
        l1.on_step_end()
        l1.advance(dt, t, cylinder_force_N=f)
        ref.advance(dt, cylinder_force_N=f)
        t += dt
        assert np.array_equal(l1.s_ref_m, ref.s_ref_m)
        assert np.array_equal(l1.u_applied_m_s, ref.u_applied_m_s)
        assert np.array_equal(l1.saturated, ref.saturated)
    assert ref.saturation_step_count.sum() > 0


# --- force law (risk 2) ----------------------------------------------------------------------


def test_force_set_after_a_step_acts_in_the_next_step(p2: Params) -> None:
    """Explicit update: ``dv`` of the next step = ``F dt / m`` (IntLoadResidual_F evaluates the
    function in that step, ChLinkMotorLinearForce.cpp:36)."""
    m = SingleLegL2bModel(p2, "FL", floor=False, gravity_m_s2=(0.0, 0.0, 0.0),
                          force_saturation=False)
    m.step()
    v0 = m.motor.GetMotorPosDt()
    m.actuator.set_initial_force([1000.0])
    m.system.DoStepDynamics(m.dt_s)
    dv = m.motor.GetMotorPosDt() - v0
    assert dv == pytest.approx(1000.0 * m.dt_s / m.rod_mass_kg, rel=1e-12)


@pytest.mark.parametrize("leg", ["FL", "RL"])
def test_free_decay_equals_semi_implicit_euler_replica(p2: Params, leg: str) -> None:
    """Zero gravity, rod in the air, initial lateral + axial velocity: the Chrono lateral
    offset and motor position equal a scalar semi-implicit Euler replica of the two explicit
    laws (lateral ``-k d - c d'``, axial ``k_ax(s)(s_ref - s) - c_lock s'``) to 1e-12 m."""
    m = SingleLegL2bModel(p2, leg, floor=False, gravity_m_s2=(0.0, 0.0, 0.0))
    v0 = 0.01
    m.rod.SetPosDt(ch.ChVector3d(0.0, v0, 0.5 * v0))
    r = run_steps(m, 0.1)
    k, c = m.bushings.values.stiffness_N_m[0], m.bushings.values.damping_N_s_m[0]
    mass, dt = m.rod_mass_kg, m.dt_s
    x, v, f = 0.0, -v0, 0.0  # link y = world -y
    lat = []
    for _ in r["t_s"]:
        v += dt * f / mass
        x += dt * v
        lat.append(x)
        f = -k * x - c * v
    assert np.max(np.abs(r["bushing_disp_m"][:, 1] - np.array(lat))) < 1e-12
    act = m.actuator
    i = [lg.name for lg in p2.legs].index(leg)
    c_lock = p2.l2b.actuator.damping_lock_N_s_m[i]  # rev. 33 LOCK basis (5.20.3)
    s, sd, f = m.extension0_m, -0.5 * v0, m.start_force_N
    s_ref = act.reference.s_ref_m[0]
    ax = []
    for _ in r["t_s"]:
        sd += dt * f / mass
        s += dt * sd
        ax.append(s)
        # column length at s_ref (rev. 33 supplement 1 convention), not at the rod body s
        f = act.axial_stiffness_N_m([s_ref])[0] * (s_ref - s) - c_lock * sd
    assert np.max(np.abs(r["motor_pos_m"] - np.array(ax))) < 1e-12
    # lateral damping ratio of the element = the leg zeta (0.03 basis is on the pad mass
    # share, here only the rod: informational bound)
    zeta = c / (2.0 * math.sqrt(k * mass))
    assert 0.2 < zeta < 0.4


# --- static single-leg checks ------------------------------------------------------------


def test_air_static_holds_the_rod_weight(p2: Params) -> None:
    m = SingleLegL2bModel(p2, "FL", floor=False)
    r = run_steps(m, 0.2)
    w = m.rod_mass_kg * p2.meta.gravity_m_s2
    assert r["force_N"][-1] == pytest.approx(-w, rel=1e-9)
    assert abs(r["motor_pos_m"][-1] - m.extension0_m) < 1e-12
    assert np.max(np.abs(r["bushing_force_N"])) < 1e-6


def test_tilted_gravity_loads_only_the_lateral_bushing(p2: Params) -> None:
    """30 deg gravity tilt about x: lateral offset = m g sin a / k_lat, axial force = -m g
    cos a (rotations locked by the guide, translation only)."""
    g = p2.meta.gravity_m_s2
    a = math.radians(30.0)
    tilt = (0.0, g * math.sin(a), -g * math.cos(a))
    m = SingleLegL2bModel(p2, "FL", floor=False, gravity_m_s2=tilt)
    r = run_steps(m, 1.0)
    k = p2.l2b.actuator.lateral_bushing_N_m[0]
    lat = m.rod_mass_kg * g * math.sin(a)
    assert -r["bushing_disp_m"][-1, 1] == pytest.approx(lat / k, rel=1e-6)
    assert r["bushing_force_N"][-1, 1] == pytest.approx(lat, rel=1e-6)  # restoring, +link y
    assert abs(r["bushing_disp_m"][-1, 0]) < 1e-12
    assert r["force_N"][-1] == pytest.approx(-m.rod_mass_kg * g * math.cos(a), rel=1e-6)


def test_floor_preload_contact_force_window_mean(p2: Params) -> None:
    """Pad on the NSC floor with a 100 kN preload: window mean of the contact normal force =
    mean(F + m g) (rel. 1e-4); the per-step NSC reading alternates (recorded, risk 5)."""
    m = SingleLegL2bModel(p2, "FL", floor=True, preload_N=100.0e3)
    r = run_steps(m, 1.0)
    win = slice(-5000, None)
    w = m.rod_mass_kg * p2.meta.gravity_m_s2
    nz = r["contact_force_world_N"][win, 2]
    expected = r["force_N"][win] + w
    assert nz.mean() == pytest.approx(expected.mean(), rel=1e-4)
    assert r["force_N"][-1] == pytest.approx(100.0e3, rel=1e-3)
    assert abs(r["motor_pos_m"][-1] - m.extension0_m) < 1e-6  # rigid contact
    slip = np.asarray(r["ball_centre_world_m"])[win, :2]
    assert np.max(np.ptp(slip, axis=0)) < 1e-9


def test_extend_saturation_stops_at_the_210_bar_limit(p2: Params) -> None:
    """V11b analogue (extend only; NSC cannot pull): max force <= limit x 1.01; after the
    first saturated step the reference creeps until the static spring force reaches the limit
    (law C keeps the command; stopping drops the moving dashpot c_move u, so the creep bound is
    c_move v_max / k_ax ~ 0.08 mm for FL, vs. c_n v / k_n 0.03 mm in L1)."""
    m = SingleLegL2bModel(p2, "FL", floor=True, preload_N=100.0e3)
    limit = float(p2.get("legs.FL.cylinder.max_force_extend_N"))
    r = run_steps(m, 1.0, [(0.0, 1.0)])
    sat = np.flatnonzero(r["saturated"])
    assert sat.size > 0
    assert r["force_N"].max() <= 1.01 * limit
    c_move = p2.l2b.actuator.damping_moving_N_s_m[0]  # rev. 33 (5.20.3)
    creep_bound = c_move * p2.actuator.max_speed_m_s / m.k_ax0_N_m
    creep = r["s_ref_m"][-1] - r["s_ref_m"][sat[0]]
    assert 0.0 <= creep <= 1.2 * creep_bound
    assert limit <= r["force_N"][-1] <= 1.001 * limit
    assert r["u_applied_m_s"][-1] == 0.0
    assert m.actuator.reference.saturation_start_count[0] >= 1
