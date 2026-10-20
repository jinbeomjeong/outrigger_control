"""Ground-bushing force point (user decision 2026-10-20, ``dynamics_model.md`` 5.3 ruling 4 A).

* Default: frame A at the pad ball centre, zero in-plane deformation at attach.
* A tangential bushing force at the ball centre puts no moment on the leg body about the
  ball centre; the contact-point option does (``r F`` about the tangent axis), the linear
  response is the same. Free body, no contact, one implicit step (test assumption values).
* Snapshots: the force point is stored; an older state without the key is a contact-point
  state; restoring another force point raises before anything is changed.
* Hold safety: a hold that outlives the deadline aborts the gravity-ramp run.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.ground_bushing import (  # noqa: E402
    DEFAULT_FORCE_POINT,
    FORCE_POINT_BALL_CENTRE,
    FORCE_POINT_CONTACT,
    FORCE_POINT_STATE_KEY,
    FORCE_POINTS,
    ForcePointMismatchError,
    GroundBushingCoulomb,
    HoldNotReleasedError,
    PadBushingSpec,
)
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.chrono.runs import run_gravity_ramp  # noqa: E402
from outrigger_sim.chrono.system import gravity_vector, make_system, set_gravity  # noqa: E402
from outrigger_sim.params import Params, load_params  # noqa: E402
from outrigger_sim.scenarios.slope import gravity_ramp, slope_start  # noqa: E402
from outrigger_sim.verify.reference import SLOPE_V12_CASES, load_references  # noqa: E402
from outrigger_sim.verify.s2a import hold_checks  # noqa: E402

pytestmark = pytest.mark.chrono

# Free-body probe (test assumptions): 1 t body, ball radius 6 cm, kt 1e6 N/m, 1 mm offset.
PROBE_MASS_KG = 1000.0
PROBE_INERTIA_KG_M2 = 100.0
PROBE_RADIUS_M = 0.06
PROBE_KT_N_M = 1.0e6
PROBE_OFFSET_M = 1.0e-3
PROBE_DT_S = 1.0e-4


def test_default_is_ball_centre() -> None:
    assert DEFAULT_FORCE_POINT == FORCE_POINT_BALL_CENTRE
    assert FORCE_POINTS.index(FORCE_POINT_CONTACT) == 0  # snapshot code of older files


def test_l1_model_frame_a_at_ball_centre(params: Params) -> None:
    model = L1Model(params)
    gb = model.bushing
    assert gb.force_point == FORCE_POINT_BALL_CENTRE
    arrays = gb.state_arrays()
    assert np.array_equal(
        arrays["frame_a_pos_body_local_m"], np.array(model.sphere_centres_local_m)
    )
    assert int(arrays[FORCE_POINT_STATE_KEY][0]) == FORCE_POINTS.index(FORCE_POINT_BALL_CENTRE)
    assert np.nanmax(np.abs(gb.tangential_displacement_m())) < 1e-12
    # anchors stay on the floor surface under the ball centres
    anchors = gb.anchors_world_m()
    assert np.allclose(anchors[:, 2], params.ground.crawler_bottom_z_m, atol=1e-12)
    centres = np.array(
        [
            [c.x, c.y, c.z]
            for c in (
                leg.TransformPointLocalToParent(ch.ChVector3d(*map(float, centre)))
                for leg, centre in zip(model.legs, model.sphere_centres_local_m, strict=True)
            )
        ]
    )
    assert np.allclose(anchors[:, :2], centres[:, :2], atol=1e-12)
    assert model.meta()["ground_bushing_force_point"] == FORCE_POINT_BALL_CENTRE
    legacy = L1Model(params, bushing_force_point=FORCE_POINT_CONTACT)
    a_legacy = legacy.bushing.state_arrays()["frame_a_pos_body_local_m"]
    # contact point = ball centre - r along the floor normal (level floor, level body)
    shift = np.array(model.sphere_centres_local_m) - a_legacy
    assert np.allclose(shift[:, :2], 0.0, atol=1e-12)
    assert np.allclose(shift[:, 2], model.sphere_radii_m, atol=1e-12)


def _free_probe(params: Params, force_point: str) -> tuple[np.ndarray, np.ndarray]:
    """Velocity and angular velocity after one step with the ball centre moved by 1 mm in x."""
    bundle = make_system(params, dt=PROBE_DT_S, floor_plate=False)
    system, floor = bundle.system, bundle.floor
    set_gravity(system, (0.0, 0.0, 0.0))
    body = ch.ChBody()
    body.SetMass(PROBE_MASS_KG)
    body.SetInertiaXX(ch.ChVector3d(1.0, 1.0, 1.0) * PROBE_INERTIA_KG_M2)
    body.SetPos(ch.ChVector3d(0.0, 0.0, PROBE_RADIUS_M))
    system.Add(body)
    pad = PadBushingSpec(
        name="probe",
        body=body,
        sphere_centre_body_local_m=(0.0, 0.0, 0.0),
        sphere_radius_m=PROBE_RADIUS_M,
        stiffness_N_m=PROBE_KT_N_M,
        damping_input_N_s_m=0.0,
    )
    gb = GroundBushingCoulomb(
        system,
        floor,
        [pad],
        friction=0.5,
        slip_damping_reenable_speed_m_s=1e-3,
        dt_s=PROBE_DT_S,
        force_point=force_point,
    )
    gb.attach()
    body.SetPos(ch.ChVector3d(PROBE_OFFSET_M, 0.0, PROBE_RADIUS_M))
    system.DoStepDynamics(PROBE_DT_S)  # no hook: the anchor stays (pure spring response)
    v = body.GetPosDt()
    w = body.GetAngVelParent()
    return np.array([v.x, v.y, v.z]), np.array([w.x, w.y, w.z])


def test_ball_centre_force_has_no_moment(params: Params) -> None:
    force = PROBE_KT_N_M * PROBE_OFFSET_M  # restoring force -x on the body [N]
    v_expected = -force * PROBE_DT_S / PROBE_MASS_KG
    v_ball, w_ball = _free_probe(params, FORCE_POINT_BALL_CENTRE)
    v_cp, w_cp = _free_probe(params, FORCE_POINT_CONTACT)
    assert v_ball[0] == pytest.approx(v_expected, rel=1e-3)
    assert v_cp[0] == pytest.approx(v_expected, rel=1e-3)
    assert abs(v_ball[2]) < 1e-12 and abs(v_cp[2]) < 1e-12  # normal offset not loaded
    assert np.abs(w_ball).max() < 1e-12
    # contact point r below the centre: tau_y = r F (force -x at z = -r)
    w_expected = PROBE_RADIUS_M * force * PROBE_DT_S / PROBE_INERTIA_KG_M2
    assert w_cp[1] == pytest.approx(w_expected, rel=1e-2)
    assert abs(w_cp[0]) < 1e-12 and abs(w_cp[2]) < 1e-12


def test_snapshot_force_point_policy(params: Params) -> None:
    model = L1Model(params)
    arrays = model.bushing.state_arrays()
    legacy = {k: v for k, v in arrays.items() if k != FORCE_POINT_STATE_KEY}
    before = model.bushing.state_arrays()
    with pytest.raises(ForcePointMismatchError, match="older file"):
        model.bushing.restore_state(legacy)
    after = model.bushing.state_arrays()  # refused before anything changed
    for key, value in before.items():
        assert np.array_equal(value, after[key], equal_nan=value.dtype.kind == "f"), key
    contact = L1Model(params, bushing_force_point=FORCE_POINT_CONTACT)
    contact_arrays = contact.bushing.state_arrays()
    contact.bushing.restore_state(
        {k: v for k, v in contact_arrays.items() if k != FORCE_POINT_STATE_KEY}
    )
    contact.bushing.finish_restore()
    with pytest.raises(ForcePointMismatchError, match="stored"):
        contact.bushing.restore_state(arrays)
    model.bushing.restore_state(arrays)  # same force point: fine
    model.bushing.finish_restore()
    # whole-model path (snapshot.restore_snapshot -> restore_state)
    with pytest.raises(ForcePointMismatchError):
        contact.restore(model.snapshot())


def _slope_model() -> L1Model:
    params = load_params(level="top")
    st = slope_start(params, load_references(), SLOPE_V12_CASES[0])
    model = L1Model(
        params,
        pose=BodyPose(st.body_origin_m),
        extensions_m=st.extensions_m,
        attach_bushings=False,
        floor_pose=BodyPose(st.floor_pos_m, st.floor_quat_wxyz),
    )
    model.bushing.attach(hold_until_loaded=True)
    set_gravity(model.system, (0.0, 0.0, 0.0))
    return model


def test_hold_outliving_the_deadline_aborts_the_run() -> None:
    model = _slope_model()
    # the contact force reads 0 for about 30 ms of the 3 s ramp (module docstring)
    with pytest.raises(HoldNotReleasedError, match="FL"):
        run_gravity_ramp(
            model,
            gravity_vector(model.params),
            gravity_ramp,
            0.05,
            fine_from_s=0.05,
            hold_deadline_s=0.01,
        )


def test_hold_checks_record_release_and_max_tangential_force() -> None:
    model = _slope_model()
    run_gravity_ramp(
        model,
        gravity_vector(model.params),
        gravity_ramp,
        0.12,
        fine_from_s=0.12,
        hold_deadline_s=0.11,
    )
    gb = model.bushing
    t_max = gb.hold_max_tangential_N
    assert np.all(t_max > 0.0) and np.all(t_max < 50.0)
    checks = hold_checks(
        "pitch 2",
        release_t_s=gb.hold_release_t_s,
        max_tangential_N=t_max,
        ramp_end_s=0.11,
        friction=model.params.contact.rigid_floor.friction,
        touch_threshold_N=gb.touch_threshold_N,
    )
    assert all(c.passed for c in checks)
    failed = hold_checks(
        "x",
        release_t_s=[0.07, np.nan, 0.07, 0.07],
        max_tangential_N=[1.0, 1.0, 60.0, 1.0],
        ramp_end_s=3.0,
        friction=0.5,
        touch_threshold_N=100.0,
    )
    assert [c.passed for c in failed] == [False, False]
    arrays = gb.state_arrays()
    assert np.array_equal(arrays["hold_max_tangential_N"], t_max)
