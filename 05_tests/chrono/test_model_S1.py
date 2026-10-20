"""S1 model checks (chrono_build_plan.md S1): V0 for three auger levels, contact force frames
and the callback cross-check, collision families (R14), motor sign (R4), truth extraction,
hook order, and a short static run from the analytic start."""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.contact import (  # noqa: E402
    FAMILY_ROD,
    FAMILY_SUPERSTRUCTURE,
    report_contacts,
    set_family,
)
from outrigger_sim.chrono.model import L1Model, operating_extensions_m, zero_pose  # noqa: E402
from outrigger_sim.chrono.system import make_smc_material, make_system  # noqa: E402
from outrigger_sim.params import AugerLevel, load_params  # noqa: E402
from outrigger_sim.scenarios.settle import analytic_static_pose  # noqa: E402
from outrigger_sim.verify.reference import (  # noqa: E402
    L1_CONTACT_FORCE_N,
    TOTAL_WEIGHT_INCL_RODS_N,
    load_references,
)
from outrigger_sim.verify.s1 import v0_checks  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def refs():
    return load_references()


@pytest.mark.parametrize("level", [lv.value for lv in AugerLevel])
def test_v0_all_levels(level: str) -> None:
    params = load_params(level=level)
    model = L1Model(params)
    results = v0_checks(params, model.v0_inventory())
    failed = [(r.item, r.value, r.ref) for r in results if not r.passed]
    assert not failed
    assert len(results) > 80


def test_material_values_are_float32_in_chrono() -> None:
    """ChContactMaterialSMC keeps kn / gn in single precision (V0 compares accordingly)."""
    material = make_smc_material(20813595.4, 253.061739)
    assert material.GetKn() == float(np.float32(20813595.4)) != 20813595.4
    assert material.GetGn() == float(np.float32(253.061739))


def test_contact_force_is_world_frame_and_matches_callback() -> None:
    """Rotated body (30 deg about x) on a sphere: GetContactForce stays vertical (world)."""
    params = load_params()
    bundle = make_system(params, floor_plate=False)
    system, floor = bundle.system, bundle.floor
    mat = make_smc_material(2e7, 250.0)
    floor.EnableCollision(True)
    floor.AddCollisionShape(
        ch.ChCollisionShapeBox(mat, 4, 4, 1), ch.ChFramed(ch.ChVector3d(0, 0, -0.5), ch.QUNIT)
    )
    body = ch.ChBody()
    body.SetName("probe_body")
    body.SetMass(100.0)
    body.SetInertiaXX(ch.ChVector3d(10, 10, 10))
    body.SetPos(ch.ChVector3d(0, 0, 0.06 - 100.0 * 9.80665 / 2e7))
    body.SetRot(ch.QuatFromAngleX(math.radians(30.0)))
    body.EnableCollision(True)
    body.AddCollisionShape(ch.ChCollisionShapeSphere(mat, 0.06), ch.ChFramed())
    system.Add(body)
    lock = ch.ChLinkLockAlign()  # keep the orientation, free translation
    lock.Initialize(body, floor, ch.ChFramed(body.GetPos(), ch.QUNIT))
    system.Add(lock)
    for _ in range(2000):
        system.DoStepDynamics(1e-4)
    f = body.GetContactForce()
    assert f.z == pytest.approx(100.0 * 9.80665, rel=1e-3)
    assert abs(f.y) < 1e-6 * f.z  # body-local axes would give f.y = f.z tan 30 deg
    report = report_contacts(system, ["probe_body"])
    assert report.count.tolist() == [1]
    assert np.allclose(report.force_world_N[0], [f.x, f.y, f.z], atol=1e-9)


def test_collision_family_disables_rod_superstructure_pair() -> None:
    params = load_params()

    def count(disable: bool) -> int:
        bundle = make_system(params, floor_plate=False)
        system = bundle.system
        mat = make_smc_material(1e6, 1.0)
        bodies = []
        for x in (0.0, 0.05):  # overlapping spheres
            b = ch.ChBody()
            b.SetMass(1.0)
            b.SetPos(ch.ChVector3d(x, 0, 5))
            b.EnableCollision(True)
            b.AddCollisionShape(ch.ChCollisionShapeSphere(mat, 0.05), ch.ChFramed())
            system.Add(b)
            bodies.append(b)
        set_family(bodies[0], FAMILY_SUPERSTRUCTURE)
        set_family(bodies[1], FAMILY_ROD, (FAMILY_SUPERSTRUCTURE,) if disable else ())
        system.DoStepDynamics(1e-4)
        return int(system.GetNumContacts())

    assert count(False) == 1
    assert count(True) == 0


def test_motor_sign_and_cylinder_force(refs) -> None:
    """R4: motor position = extension; F_cyl = +GetMotorForce = contact - rod weight."""
    params = load_params()
    ext = operating_extensions_m(params)
    model = L1Model(params, pose=BodyPose(*_static_pose(params, refs)))
    inv = model.v0_inventory()
    assert np.allclose(inv["motor_pos_m"], ext, atol=1e-12)
    for _ in range(500):
        model.step()
    probe = model.probe()
    rods = np.array([leg.moving_part.mass_kg for leg in params.legs]) * params.meta.gravity_m_s2
    # quasi-static after 0.05 s from the analytic start: the rod acceleration term is small
    assert np.allclose(probe.motor_force_N, probe.pad_normal_force_N - rods, atol=50.0)
    truth = model.truth(probe)
    assert np.allclose(truth.s_motor_m, ext, atol=1e-9)
    k_oil = np.array(model.k_oil_N_m)
    assert np.allclose(truth.stroke_true_m, truth.s_motor_m - truth.F_cyl_N / k_oil, atol=0)
    assert 0.003 < float(np.min(truth.s_motor_m - truth.stroke_true_m)) < 0.006  # ~5 mm


def _static_pose(params, refs):
    pose = analytic_static_pose(params, refs, operating_extensions_m(params))
    return pose.origin_m, pose.quat_wxyz


def test_truth_body_origin_matches_pose_at_start(refs) -> None:
    params = load_params()
    origin, quat = _static_pose(params, refs)
    model = L1Model(params, pose=BodyPose(origin, quat))
    probe = model.probe()
    assert np.allclose(probe.body_pos_m, origin, atol=1e-12)
    assert np.allclose(probe.body_quat_wxyz, quat, atol=1e-15)
    assert np.abs(probe.leg_offset_in_body_m).max() < 1e-12
    # penetration at the start = analytic start values
    start = analytic_static_pose(params, refs, operating_extensions_m(params))
    assert np.allclose(probe.penetration_m * 1e3, start.penetration_start_mm, atol=1e-9)


def test_hook_order_and_probe_before_bushing_hook() -> None:
    params = load_params()
    model = L1Model(params)
    calls: list[str] = []
    seen: dict[str, object] = {}
    model.actuator_hooks.append(lambda m, dt: calls.append("actuator"))
    model.load_hooks.append(lambda m, dt: calls.append("load"))

    def record(m, probe):
        calls.append("record")
        seen["probe"] = probe

    model.record_hooks.append(record)
    original = model.bushing.after_step

    def wrapped(dt=None):
        calls.append("bushing")
        return original(dt)

    model.bushing.after_step = wrapped  # type: ignore[method-assign]
    model.step()
    assert calls == ["bushing", "actuator", "load", "record"]
    assert seen["probe"].t_s == pytest.approx(model.system.GetChTime())


def test_short_static_run_from_analytic_start(refs) -> None:
    """0.3 s from the analytic start stays near the reference (full judgement: verify test)."""
    params = load_params()
    model = L1Model(params, pose=BodyPose(*_static_pose(params, refs)))
    events = []
    for _ in range(3000):
        events += model.step().events
    probe = model.probe()
    quarter = refs.get(TOTAL_WEIGHT_INCL_RODS_N) / 4
    assert not events
    assert np.allclose(
        probe.pad_normal_force_N, refs.get(L1_CONTACT_FORCE_N, level="top"), atol=0.01 * quarter
    )
    assert probe.n_contacts == 4  # crawler spheres stay off the floor


def test_zero_pose_is_level_touch() -> None:
    params = load_params()
    pose = zero_pose(params, operating_extensions_m(params))
    assert pose.origin_m[2] == pytest.approx(params.simulation.crawler_clearance_m, abs=1e-12)
    with pytest.raises(ValueError):
        zero_pose(params, [0.4, 0.4, 0.4, 0.4])
