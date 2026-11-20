"""Digest of the v5 harness plant state per kernel step on the body-fixed stand-in (bit-identity
check of the record-only harness edits). Usage: python -I -B plant_digest.py <project tree>"""
import hashlib
import sys
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "05_tests" / "unit"))

import numpy as np  # noqa: E402
import v5_harness_unit_runner as base  # noqa: E402

from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions  # noqa: E402

import harness_hydraulics  # noqa: E402

assert Path(harness_hydraulics.__file__).resolve().is_relative_to(tree)
STEP_S = base.KERNEL_STEP_S
VALVE_TAU_S = base.VALVE_TAU_S
OPTIONS = {
    "r5": HydraulicOptions(rod_release_force=True),
    "j_plant": HydraulicOptions(rod_release_force=True, line_fill_gate=CheckDelaySetting("VN"),
                                lock_anchor_continuous=True, rod_flow_cap_all=True),
    "p1_only": HydraulicOptions(rod_release_force=True, line_fill_gate=CheckDelaySetting("VN")),
}


def ramp(peak_m_s: float, duration_s: float) -> list[float]:
    return [peak_m_s * (1.0 - np.exp(-(k + 1) * STEP_S / VALVE_TAU_S))
            for k in range(round(duration_s / STEP_S))]


def schedule() -> list[np.ndarray]:
    """Rest, FL retract, rest, RL retract with a band, FR extend, all legs retract."""
    steps = [np.zeros(4)] * round(0.2 / STEP_S)
    for leg, peak, duration in ((0, -4.71e-3, 0.6), (2, -4.71e-3, 0.6), (1, 4.71e-3, 0.3),
                                (3, -1.0e-3, 0.4)):
        for speed in ramp(peak, duration):
            command = np.zeros(4)
            command[leg] = speed
            steps.append(command)
        steps += [np.zeros(4)] * round(0.1 / STEP_S)
    steps += [np.full(4, speed) for speed in ramp(-2.0e-3, 0.4)]
    return steps


digest = hashlib.sha256()
for name, options in OPTIONS.items():
    plant = base._lifted_leg_plant(options)
    plant.Fs[2] = 7.0e3
    for command in schedule():
        plant.step(command, 1)
        for value in (plant.sref, plant.x, plant.Gr, plant.p_r0, plant.locked,
                      plant.rod_pressure_lag.pressure_Pa):
            digest.update(np.asarray(value, float).tobytes())
    digest.update(name.encode())
    print(name, "seeds", plant.lock_log.retract_seed_count if plant.lock_log else None,
          "locks", plant.n_lock_events, "releases", plant.n_release_events, flush=True)
print(digest.hexdigest(), harness_hydraulics.__file__)
