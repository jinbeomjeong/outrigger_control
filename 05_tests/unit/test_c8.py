"""C8 skeleton on the controller boundary (control/c8.py); levelling quality is not tested."""

from __future__ import annotations

import json
import math

import numpy as np

from outrigger_sim.control.c8 import C8Controller, C8Phase
from outrigger_sim.control.protocol import Controller
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665


def _measurements(t_s: float, controller: C8Controller, pitch_rad: float, force_N: float):
    geometry = controller.geometry
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m
    specific_force = GRAVITY_M_S2 * np.array([-math.sin(pitch_rad), 0.0, math.cos(pitch_rad)])
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=specific_force,
        angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=np.full(4, force_N) / geometry.head_area_m2,
        stroke_m=strokes,
        stroke_corrected_m=strokes,
    )


def test_c8_follows_the_protocol_and_extends_only() -> None:
    controller = C8Controller.from_params(load_params())
    assert isinstance(controller, Controller)
    json.dumps(controller.meta())
    pitch = math.radians(1.0)  # nose down: the front legs are low and extend
    first = controller.update(_measurements(0.02, controller, pitch, 0.0))
    assert controller.phase is C8Phase.TOUCH and first.leg_speed_m_s.min() > 0.0
    commands = [
        controller.update(_measurements(0.02 * (k + 2), controller, pitch, 80e3)).leg_speed_m_s
        for k in range(50)
    ]
    assert controller.phase is C8Phase.ATTITUDE
    assert np.min(commands) >= 0.0
    front, rear = commands[-1][:2], commands[-1][2:]
    assert front.min() > rear.max()
    controller.reset()
    assert controller.phase is C8Phase.TOUCH
