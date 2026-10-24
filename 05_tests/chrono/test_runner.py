"""S6 runner on the Chrono L1 engine (chrono_build_plan.md S6 'runner', risks 1-3): zero-order
hold, Measurements-only controller input, sensor truth, IMU point argument, V13."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.chrono.bodies import BodyPose  # noqa: E402
from outrigger_sim.chrono.l1_engine import L1Engine  # noqa: E402
from outrigger_sim.chrono.model import L1Model, operating_extensions_m  # noqa: E402
from outrigger_sim.chrono.truth import (  # noqa: E402
    L1SensorTruth,
    imu_truth,
    imu_truth_direct,
    k_oil_at_extension_N_m,
)
from outrigger_sim.control.hold import HoldController  # noqa: E402
from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.runner import RunnerError, run_closed_loop  # noqa: E402
from outrigger_sim.sensors.hydraulic import LegSensorConfig  # noqa: E402
from outrigger_sim.sensors.imu import (  # noqa: E402
    IMU_MOUNT_C1_BODY_M,
    ImuErrorConfig,
    imu_config_for_grade,
)
from outrigger_sim.sensors.suite import SensorSuite  # noqa: E402
from outrigger_sim.signals import Command, Measurements, TruthState  # noqa: E402
from outrigger_sim.verify.s6 import sensor_truth_checks  # noqa: E402

pytestmark = pytest.mark.chrono

TILT = (math.radians(10.0), math.radians(-1.5), math.radians(2.0))  # yaw, pitch, roll


@pytest.fixture(scope="module")
def params():
    return load_params(level="top")


def _fixed_engine(params, *, point=IMU_MOUNT_C1_BODY_M, method="sensors_imu", fixed=True):
    q = tuple(float(c) for c in quat_from_euler_zyx(*TILT))
    pose = BodyPose((0.3, -0.2, params.ground.crawler_bottom_z_m + 4.0), q)
    model = L1Model(params, pose=pose, extensions_m=operating_extensions_m(params),
                    crawler=False, attach_bushings=False, actuator=True)
    model.superstructure.SetFixed(fixed)
    return L1Engine(model, imu_mount_point_body_m=point, imu_method=method)


def _suite(point=IMU_MOUNT_C1_BODY_M, imu=None):
    return SensorSuite(ImuErrorConfig() if imu is None else imu, LegSensorConfig(), seed=7,
                       imu_mount_point_body_m=point)


class SpyController:
    """Records what the runner hands over; commands +v_max on every leg from update 3."""

    def __init__(self, speed=0.0, start_update=3):
        self.inputs: list[Any] = []
        self.speed = speed
        self.start_update = start_update

    @property
    def period_s(self) -> float:
        return 0.02

    def reset(self) -> None:
        self.inputs.clear()

    def update(self, *args: Any, **kwargs: Any) -> Command:
        assert not kwargs and len(args) == 1
        self.inputs.append(args[0])
        u = self.speed if len(self.inputs) >= self.start_update else 0.0
        return Command(t_s=args[0].t_s, leg_speed_m_s=np.full(4, u))

    def meta(self) -> dict[str, Any]:
        return {"controller": "spy"}


@pytest.mark.parametrize("method", ["sensors_imu", "chrono_point"])
@pytest.mark.parametrize("point", [IMU_MOUNT_C1_BODY_M, (2.0, -1.0, 3.0)])
def test_static_sensor_truth(params, method, point) -> None:
    engine = _fixed_engine(params, point=point, method=method)
    res = run_closed_loop(engine, HoldController(), _suite(point), 0.1,
                          run_meta={"dt_s": engine.dt_s}, placement=None)
    arrays = {k: np.asarray(v) for k, v in res.record.arrays.items()}
    checks = sensor_truth_checks(arrays, gravity_m_s2=params.meta.gravity_m_s2,
                                 head_area_m2=engine.sensor_truth.head_area_m2,
                                 k_oil_N_m=engine.sensor_truth.k_oil_N_m, case="t",
                                 stroke_m=params.actuator.stroke_m)
    assert all(c.passed for c in checks), [c.as_dict() for c in checks if not c.passed]
    assert res.n_control == 5 and res.record.n_samples == 5


def test_imu_truth_rotating_body_both_paths(params) -> None:
    """Free-falling spinning body: f at a point = R^T (alpha x r + w x (w x r)) (no gravity
    term in free fall); the sensors/imu path and Chrono's point acceleration agree."""
    engine = _fixed_engine(params, fixed=False)
    model = engine.model
    for leg in model.legs:
        model.system.RemoveBody(leg)
    for motor in model.motors:
        model.system.RemoveLink(motor)
    model.actuator_hooks.clear()
    sup = model.superstructure
    sup.SetAngVelParent(ch.ChVector3d(0.3, -0.2, 0.5))
    for _ in range(5):
        model.system.DoStepDynamics(model.dt_s)
    point = (2.0, -1.0, 3.0)
    s = imu_truth(model, point)
    f_direct, w_direct = imu_truth_direct(model, point)
    assert np.allclose(s.specific_force_m_s2, f_direct, rtol=0, atol=1e-12)
    assert np.allclose(s.angular_rate_rad_s, w_direct, rtol=0, atol=1e-15)
    fast = L1SensorTruth(model, point, imu_method="chrono_point").imu()
    assert np.allclose(fast.specific_force_m_s2, s.specific_force_m_s2, rtol=0, atol=1e-12)
    # analytic: free fall cancels gravity; centripetal + Euler terms about the COG remain
    q = sup.GetRot()
    rot = quat_to_matrix(np.array([q.e0, q.e1, q.e2, q.e3]))
    w = np.array([sup.GetAngVelParent().x, sup.GetAngVelParent().y, sup.GetAngVelParent().z])
    al = np.array([sup.GetAngAccParent().x, sup.GetAngAccParent().y, sup.GetAngAccParent().z])
    r = rot @ (np.asarray(point) - np.asarray(model.sup_com_body_m))
    expect = rot.T @ (np.cross(al, r) + np.cross(w, np.cross(w, r)))
    assert np.allclose(s.specific_force_m_s2, expect, rtol=0, atol=1e-9)
    assert np.linalg.norm(expect) > 0.1


def test_controller_gets_measurements_only_and_zoh(params) -> None:
    engine = _fixed_engine(params)
    spy = SpyController(speed=0.01, start_update=3)
    res = run_closed_loop(engine, spy, _suite(), 0.12, run_meta={"dt_s": engine.dt_s},
                          placement=None)
    assert len(spy.inputs) == 6
    assert all(type(m) is Measurements for m in spy.inputs)
    assert not any(isinstance(m, TruthState) for m in spy.inputs)
    # the controller cannot reach the engine through what it got
    for m in spy.inputs:
        assert not any(isinstance(v, (L1Engine, L1Model)) for v in vars(m).values())
    rec = res.record.arrays
    # Record u_cmd = command held during the step ending at the sample: zero up to the 3rd
    # sample, the 0.01 m/s issued at sample 3 appears from sample 4 on
    assert np.all(rec["u_cmd"][:3] == 0.0)
    assert np.allclose(rec["u_cmd"][3:], 0.01)
    # zero-order hold from t_3: the actuator moves from the first step after t_3
    assert np.all(rec["u_applied"][:3] == 0.0)
    assert np.all(rec["u_applied"][3] > 0.0)
    assert res.command_t_s.tolist() == rec["t"].tolist()


def test_runner_refuses_bad_setups(params) -> None:
    engine = _fixed_engine(params)

    class Late(SpyController):
        def update(self, measurements):
            return Command(t_s=measurements.t_s - 0.02, leg_speed_m_s=np.zeros(4))

    with pytest.raises(RunnerError, match="issued at"):
        run_closed_loop(engine, Late(), _suite(), 0.04, placement=None)
    with pytest.raises(RunnerError, match="not a multiple"):
        run_closed_loop(engine, HoldController(period_s=0.0201), _suite(), 0.04, placement=None)
    # R8 (spec 148 R-1): the control period must be an integer multiple of the IMU sample
    # period (10 ms in 20 ms is allowed now; 30 ms in 20 ms is not)
    graded = _suite(imu=imu_config_for_grade("ideal", sample_period_s=0.03))
    with pytest.raises(RunnerError, match="sample period"):
        run_closed_loop(engine, HoldController(), graded, 0.04, placement=None)
    graded = _suite(imu=imu_config_for_grade("ideal", sample_period_s=0.0075))
    with pytest.raises(RunnerError, match="sample period"):
        run_closed_loop(engine, HoldController(), graded, 0.04, placement=None)


def test_k_oil_at_operating_extension_equals_yaml(params) -> None:
    ext = np.asarray(operating_extensions_m(params))
    k_yaml = params.get("contact.rigid_floor.L1.derivation.k_oil_N_m")
    k = k_oil_at_extension_N_m(params, ext)
    for i, leg in enumerate(("FL", "FR", "RL", "RR")):
        assert k[i] == pytest.approx(float(k_yaml[leg]), rel=1e-6)


def test_pad_recorder_on_settled_state(params) -> None:
    from outrigger_sim.chrono.pad_record import PadRecorder
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose
    from outrigger_sim.verify.reference import load_references

    sp = analytic_static_pose(params, load_references(), operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), actuator=True)
    model.restore(load_snapshot("S1_L1_top", params_sha256=params.sha256))
    engine = L1Engine(model)
    pads = PadRecorder(engine, every_steps=5)
    run_closed_loop(engine, HoldController(), _suite(), 0.1, placement=None, step_hook=pads,
                    capture_every_steps=5)
    a = pads.arrays()
    assert a["t"].shape == (100,)
    assert np.all(a["F_cyl_min_interval"] <= a["F_cyl"] + 1e-9)
    # level floor, level deck: R almost along n and a; N = cylinder force + rod weight
    assert np.all(a["T"] < 1e-3 * a["N"]) and np.all(a["L"] < 1e-2 * a["N"])
    rod_w = np.array([leg.moving_part.mass_kg for leg in params.legs]) * params.meta.gravity_m_s2
    assert np.allclose(a["N"].mean(axis=0), a["F_cyl"].mean(axis=0) + rod_w, rtol=1e-3)
