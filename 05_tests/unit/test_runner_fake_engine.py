"""Runner logic without a physics engine (chrono_build_plan.md S6 'runner', risk 1): control
period count, control-period IMU average, Record rows, u_cmd convention, Measurements only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from outrigger_sim.control.hold import HoldController
from outrigger_sim.runner import ClosedLoopEngine, RunnerError, run_closed_loop
from outrigger_sim.sensors.hydraulic import LegSensorConfig
from outrigger_sim.sensors.imu import ImuErrorConfig
from outrigger_sim.sensors.suite import SensorSuite
from outrigger_sim.signals import Command, Measurements, TruthState


@dataclass
class _Sample:
    t_s: float
    specific_force_m_s2: np.ndarray
    angular_rate_rad_s: np.ndarray


class FakeEngine:
    """Point mass with a known specific force ``(sin(2 pi t), 0, g)`` and legs that integrate
    the held command (ZOH from the callback, like ``chrono/l1_engine``)."""

    def __init__(self, dt=1e-3):
        self.dt = dt
        self.t = 0.0
        self.s = np.full(4, 0.3)
        self.u = np.zeros(4)
        self.pending = np.zeros(4)
        self.callback = None

    @property
    def time_s(self):
        return self.t

    @property
    def dt_s(self):
        return self.dt

    def meta(self):
        return {"dt_s": self.dt}

    def step(self, *, capture=False):
        del capture
        self.s = self.s + self.u * self.dt
        self.t = round(self.t + self.dt, 12)
        if self.callback is not None:
            self.callback(self)
        self.u = self.pending.copy()  # "actuator hook" after the callback
        return self.t

    def apply_command(self, command):
        self.pending = np.asarray(command.leg_speed_m_s, dtype=float).copy()

    def truth(self):
        return TruthState(
            t_s=self.t, body_pos_m=np.zeros(3), body_quat_wxyz=np.array([1.0, 0, 0, 0]),
            body_vel_m_s=np.zeros(3), body_omega_rad_s=np.zeros(3), s_motor_m=self.s,
            s_ref_m=self.s, u_applied_m_s=self.u, F_cyl_N=np.full(4, 1e5),
            F_contact_n_N=np.full(4, 1e5), F_contact_t_N=np.zeros((4, 2)),
            is_pad_in_contact=np.ones(4, dtype=bool), F_crawler_N=np.zeros(3),
            bushing_anchor_m=np.zeros((4, 3)), stroke_true_m=self.s,
        )

    def set_step_callback(self, callback):
        self.callback = callback

    def imu_sample(self):
        return _Sample(self.t, np.array([np.sin(2 * np.pi * self.t), 0.0, 9.8]), np.zeros(3))

    def ideal_measurements(self, avg):
        assert avg.t_s == self.t
        return Measurements(t_s=avg.t_s, specific_force_m_s2=avg.specific_force_m_s2,
                            angular_rate_rad_s=avg.angular_rate_rad_s,
                            head_pressure_Pa=np.full(4, 1e7), stroke_m=self.s,
                            stroke_corrected_m=self.s)


class Spy:
    def __init__(self):
        self.seen: list[Any] = []

    @property
    def period_s(self):
        return 0.02

    def reset(self):
        self.seen.clear()

    def update(self, m):
        self.seen.append(m)
        return Command(t_s=m.t_s, leg_speed_m_s=np.full(4, 0.01 * len(self.seen)))

    def meta(self):
        return {"controller": "spy"}


def _suite():
    return SensorSuite(ImuErrorConfig(), LegSensorConfig(), seed=1)


def test_fake_engine_follows_protocol() -> None:
    assert isinstance(FakeEngine(), ClosedLoopEngine)


def test_period_count_average_and_u_cmd_convention() -> None:
    eng = FakeEngine(dt=1e-3)
    spy = Spy()
    res = run_closed_loop(eng, spy, _suite(), 0.1, run_meta={"dt_s": 1e-3}, placement=None)
    assert res.n_steps == 100 and res.n_control == 5 and res.steps_per_period == 20
    assert all(type(m) is Measurements for m in spy.seen)
    # control-period average of sin(2 pi t) over (t_k - 0.02, t_k], step-end samples
    for m in spy.seen:
        ts = m.t_s - 0.02 + 1e-3 * np.arange(1, 21)
        assert m.specific_force_m_s2[0] == pytest.approx(np.mean(np.sin(2 * np.pi * ts)))
    rec = res.record.arrays
    assert rec["t"].tolist() == pytest.approx([0.02, 0.04, 0.06, 0.08, 0.1])
    # u_cmd at sample k = command issued at sample k-1 (held during the steps up to t_k)
    assert rec["u_cmd"][:, 0].tolist() == pytest.approx([0.0, 0.01, 0.02, 0.03, 0.04])
    # ZOH: the leg speed during the steps after t_k is the command issued at t_k
    assert rec["u_applied"][1:, 0].tolist() == pytest.approx([0.01, 0.02, 0.03, 0.04])


def test_no_record_without_meta_and_period_error() -> None:
    res = run_closed_loop(FakeEngine(), HoldController(), _suite(), 0.04, placement=None)
    assert res.record is None and res.n_control == 2
    with pytest.raises(RunnerError):
        run_closed_loop(FakeEngine(dt=3e-3), HoldController(), _suite(), 0.04, placement=None)


def test_command_delay_one_period_and_step_hook() -> None:
    eng = FakeEngine(dt=1e-3)
    spy = Spy()
    calls = []
    res = run_closed_loop(eng, spy, _suite(), 0.1, run_meta={"dt_s": 1e-3}, placement=None,
                          command_delay_periods=1, step_hook=lambda e: calls.append(e.t))
    assert len(calls) == 100
    rec = res.record.arrays
    # issued 0.01 at t=0.02 is applied at t=0.04 -> acts in the steps after 0.04
    assert rec["u_applied"][:, 0].tolist() == pytest.approx([0.0, 0.0, 0.01, 0.02, 0.03])
    assert rec["u_cmd"][:, 0].tolist() == pytest.approx([0.0, 0.0, 0.01, 0.02, 0.03])
    assert res.command_m_s[:, 0].tolist() == pytest.approx([0.01, 0.02, 0.03, 0.04, 0.05])
    assert res.meta["command_delay_periods"] == 1
    with pytest.raises(ValueError):
        run_closed_loop(FakeEngine(), spy, _suite(), 0.04, placement=None,
                        command_delay_periods=-1)
