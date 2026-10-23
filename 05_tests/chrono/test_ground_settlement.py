"""S6 G4 ground settlement (chrono/ground_settlement): RR pad patch on a driven body, the
ground bushing on that body, default model unchanged, snapshot part; V17 locked mask."""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.model import L1Model, operating_extensions_m, zero_pose  # noqa: E402
from outrigger_sim.frames import quat_from_euler_zyx  # noqa: E402
from outrigger_sim.hydraulics.rod_chamber import RodChamberMode  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_snapshot  # noqa: E402
from outrigger_sim.scenarios.settle import (  # noqa: E402
    analytic_static_pose,
    linear_static_solution,
)
from outrigger_sim.verify.reference import load_references  # noqa: E402
from outrigger_sim.verify.s6 import v17_checks, v17_reports  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def _model(params, settle=("RR",)):
    sp = analytic_static_pose(params, load_references(), operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), actuator=True,
                    settlement_legs=settle)
    t0 = model.restore(load_snapshot("S1_L1_top", params_sha256=params.sha256))
    return model, t0


def test_default_model_has_no_settlement(params) -> None:
    model, _ = _model(params, settle=())
    assert model.settlement is None
    assert len(model.floor_body_patches) == len(model.patches)
    assert all(leg.floor is model.floor for leg in model.bushing._legs)  # noqa: SLF001


def test_rr_settles_and_anchor_follows(params) -> None:
    model, t0 = _model(params)
    assert [p.name for p in model.patches if p not in model.floor_body_patches] == ["pad_RR"]
    rr = model.bushing._legs[3]  # noqa: SLF001
    assert rr.floor is model.settlement.bodies[0]
    with pytest.raises(ValueError):
        model.settlement.schedule(t0, dt_s=model.dt_s)  # not two steps ahead
    model.settlement.schedule(t0 + 0.01, depth_m=0.0115, ramp_s=2.0, dt_s=model.dt_s)
    a0 = model.probe().bushing_anchor_world_m[3, 2]
    f0 = model.probe()
    for _ in range(round(2.1 / model.dt_s)):
        model.step()
    p = model.probe()
    assert model.settlement.displacement_m() == pytest.approx(0.0115)
    assert model.settlement.bodies[0].GetPos().z == pytest.approx(-0.0115, abs=1e-12)
    assert p.bushing_anchor_world_m[3, 2] - a0 == pytest.approx(-0.0115, abs=1e-9)
    # the diagonal RR-FL unloads, FR-RL take the load (locked legs)
    assert p.motor_force_N[3] < f0.motor_force_N[3] - 20e3
    assert p.motor_force_N[2] > f0.motor_force_N[2] + 20e3
    assert not model.bushing.events  # 2 s ramp (spec): RR stays on the ground
    snap = model.snapshot()
    assert {"ground_settlement.t_start_s", "ground_settlement.depth_m"} <= set(snap.payload)
    other, _ = _model(params)
    other.restore(snap)
    assert other.settlement.is_scheduled
    assert other.settlement.bodies[0].GetPos().z == pytest.approx(-0.0115, abs=1e-12)


def _l1r_settling_model(params, settle_s: float = 0.2) -> L1Model:
    """L1-R on, RR settlement leg, crawler-free linear static pose (test_rod_chamber_link; no
    L1-R snapshot needed), stepped ``settle_s`` so that the pads settle and lock."""
    ext = operating_extensions_m(params)
    z0 = zero_pose(params, ext).origin_m[2]
    kn = [params.contact.rigid_floor.L1.kn_per_pad_N_m[i] for i in range(4)]
    u_z, roll, pitch = (float(v) for v in linear_static_solution(params, kn)["q"])
    quat = tuple(float(c) for c in quat_from_euler_zyx(0.0, pitch, roll))
    model = L1Model(params, pose=BodyPose((0.0, 0.0, z0 + u_z), quat), crawler=False,
                    actuator=True, settlement_legs=("RR",), rod_side_mechanics="one_sided_parallel")
    for _ in range(round(settle_s / model.dt_s)):
        model.step()
    return model


def _body_state(model: L1Model) -> np.ndarray:
    out = []
    for body in model.bodies:
        p, q, v = body.GetPos(), body.GetRot(), body.GetPosDt()
        out += [p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3, v.x, v.y, v.z]
    out += [m.GetMotorForce() for m in model.motors]
    return np.array(out)


def test_l1r_on_measures_the_settling_patch(params) -> None:
    """L1-R on with an RR settlement leg (rod_chamber_link): the machine deflection of RR is
    taken against the moving patch (fixed-floor height minus the patch offset), its rate is
    the time derivative of that deflection, the other legs keep the fixed-floor expression,
    and the machine's elastic force follows the Chrono contact force of the settled pad."""
    model = _l1r_settling_model(params)
    t0 = float(model.system.GetChTime())
    rod = model.rod_chamber
    assert rod.meta()["settlement_deflection"]["legs"] == ["RR"]
    patch = model.settlement.bodies[0]
    model.settlement.schedule(t0 + 0.01, depth_m=0.0115, ramp_s=0.2, dt_s=model.dt_s)
    n = model.bushing.normal_world()
    p0 = np.asarray(model.floor_point_world_m)
    floor_pos = np.array([model.floor.GetPos().x, model.floor.GetPos().y, model.floor.GetPos().z])
    deltas, rates, times = [], [], []
    for _ in range(round(0.4 / model.dt_s)):
        model.step()
        centres = np.array([
            [c.x, c.y, c.z]
            for c in (body.TransformPointLocalToParent(local)
                      for body, local in zip(model.legs, model.sphere_centres_local_ch,
                                             strict=True))
        ])
        fixed_floor = np.asarray(model.sphere_radii_m) - (centres - p0) @ n
        offset = (np.array([patch.GetPos().x, patch.GetPos().y, patch.GetPos().z]) - floor_pos) @ n
        np.testing.assert_array_equal(rod.last_deflection_m[:3], fixed_floor[:3])
        assert rod.last_deflection_m[3] == pytest.approx(fixed_floor[3] + offset, abs=1e-12)
        deltas.append(rod.last_deflection_m[3])
        rates.append(rod.last_deflection_rate_m_s[3])
        times.append(float(model.system.GetChTime()))
    assert model.settlement.displacement_m() == pytest.approx(0.0115)
    deltas, rates, times = np.array(deltas), np.array(rates), np.array(times)
    finite_difference = np.diff(deltas) / np.diff(times)
    np.testing.assert_allclose(finite_difference, 0.5 * (rates[1:] + rates[:-1]), atol=2e-3)
    probe = model.probe()
    elastic = rod.last_step.normal_force_N[3] - rod.last_step.extra_force_N[3]
    assert probe.pad_normal_force_N[3] == pytest.approx(elastic, abs=2.0e3)


def test_l1r_on_fast_drop_has_no_contact_suction(params) -> None:
    """rod_side_pressure.md 17.1 A' (M1): RR ground drops 30 mm in 0.05 s at dt 1e-5 s; with
    the one-sided pad force the RR cylinder force never pulls more than the rod weight
    (min F_cyl >= -m_rod g - 0.5 kN; before M1 about -18.6 kN) and RR lifts off."""
    model = _l1r_settling_model(params)
    t0 = float(model.system.GetChTime())
    model.settlement.schedule(t0 + 0.02, depth_m=0.030, ramp_s=0.05, dt_s=model.dt_s)
    model.set_dt(1.0e-5)
    rod_weight_N = params.legs[3].moving_part.mass_kg * params.meta.gravity_m_s2
    min_force_N = math.inf
    lifted = False
    while float(model.system.GetChTime()) < t0 + 0.12:
        model.step()
        min_force_N = min(min_force_N, float(model.motors[3].GetMotorForce()))
        lifted = lifted or model.rod_chamber.last_step.mode[3] == RodChamberMode.LIFT
    assert lifted
    assert min_force_N >= -rod_weight_N - 500.0


def test_l1r_on_snapshot_during_settlement_continues(params) -> None:
    """rod_side_pressure.md 17.3 (a): a snapshot taken mid-ramp restores the settlement
    schedule with the bodies and the L1-R state; the restored run continues like the
    original."""
    model = _l1r_settling_model(params)
    t0 = float(model.system.GetChTime())
    model.settlement.schedule(t0 + 0.01, depth_m=0.0115, ramp_s=0.2, dt_s=model.dt_s)
    for _ in range(round(0.1 / model.dt_s)):
        model.step()
    snap = model.snapshot()
    steps_after = round(0.15 / model.dt_s)
    for _ in range(steps_after):
        model.step()
    original = _body_state(model)
    other = _l1r_settling_model(params, settle_s=0.0)
    other.restore(snap)
    plan = (other.settlement.t_start_s, other.settlement.depth_m, other.settlement.ramp_s)
    assert plan == (t0 + 0.01, 0.0115, 0.2)
    assert other.settlement.displacement_m() == pytest.approx(
        model.settlement.displacement_m(float(snap.time_s)), abs=1e-15
    )
    for _ in range(steps_after):
        other.step()
    # Not bit for bit: a model with settlement legs restores the patch bodies by sync, not
    # from the snapshot (L1-R off diverges the same way: 8e-7 m/s, 4.6 N after 0.15 s,
    # measured 2026-10-22), so the continuation is compared with tolerances.
    restored = _body_state(other)
    kinematics = slice(0, 10 * len(model.bodies))
    np.testing.assert_allclose(restored[kinematics], original[kinematics], rtol=0.0, atol=1e-6)
    np.testing.assert_allclose(restored[kinematics.stop:], original[kinematics.stop:],
                               rtol=0.0, atol=20.0)
    np.testing.assert_array_equal(
        other.rod_chamber.last_step.mode, model.rod_chamber.last_step.mode
    )


def test_v17_locked_mask_judgement() -> None:
    t = np.arange(4) * 0.02
    p = np.full((4, 4), 1.0e7)
    p[1, 0] = 3.6e7  # above 350 bar while the leg moves (u_cmd != 0): not judged
    u_cmd = np.zeros((4, 4))
    u_cmd[1, 0] = 0.01
    reps = v17_reports(t, p, 3.5e7, u_cmd, u_cmd)
    checks = {c.id: c for c in v17_checks(reps, level="x", ref_max_Pa=None, tol_Pa=1.0,
                                          relief_Pa=2.1e7)}
    assert checks["V17.x.not_exceeded"].passed
    assert checks["V17.x.all_samples.info"].value is True
    assert not checks["V17.x.moving_relief"].passed  # 360 bar while moving > 210 bar relief
