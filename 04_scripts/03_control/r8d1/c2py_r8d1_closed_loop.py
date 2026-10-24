"""Engine-free closed loop of the project C2 with the R8-D1 preset on the reduced plant.

Spec: ``00_docs/04_control/s6_control_spec.md`` revision 30, 134 / 139 (design C2). Two parts,
both written to one JSON file:

* ``harness`` - the representative C2 cases of ``export_c2_r8d1_traces.py`` run through the
  revision-30 harness (``r8d1_td2.py``: KPlant crawler, pad tangential bushings, valve lag
  0.1 s, sensor noise, the harness metrics), with the harness controller replaced by
  :class:`outrigger_sim.control.c2.C2Controller` and :meth:`C2Config.with_10hz_d1`. The output
  delay and the increment limit are the controller's (the harness queue and ramp are turned
  off). Departures from the full preset, because the harness lacks the parts: the IMU filter
  runs on the period mean (the harness gives no 10 ms samples), no CHECK / zero calibration
  (the harness starts at TOUCH; without CHECK the calibration would leave its allowance on
  every leg), no REANCHOR (the harness T / G cases have none), target check off (D8 boundary
  points), contact ``pressure`` (the harness judge; with the probe READY is about 12 s later).
* ``imu_100hz`` - top, level floor: the full preset including the 100 Hz attitude filter on
  10 ms IMU samples, valve lag 0.1 s, ideal sensors, combined judge with the probe (rigid
  mast, beta 1.0 GPa; target check off and no zero calibration as above).
* ``*_without_reapproach`` - the same runs with the lifted-leg re-approach off (P-R8-13, spec
  rev. 34 179.1; P-R8-12 before). Each run records its re-approach events and intervals and a
  SHA-256 of its leg speed commands, so a run in which no leg lifts must give the same hash
  both ways.

The harness modules patch the plant classes of their process, so the regression test runs
this file in a subprocess. Run (project root, needs numba -> dynamics-dev,
MKL_THREADING_LAYER=TBB):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I \
      04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py <out.json>
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
sys.path.insert(0, str(HERE.parent))
import export_c2_r8d1_traces as traces  # noqa: E402  (imports and patches the harness)

from outrigger_sim.control.c2 import (  # noqa: E402
    C2Config,
    C2Controller,
    C2Phase,
    ContactJudge,
    LiftedReapproachSettings,
    ReanchorSettings,
    TargetSettings,
)
from outrigger_sim.control.target import TargetAcceptance  # noqa: E402
from outrigger_sim.control.zero_calibration import ZeroCalibrationMode  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.signals import Measurements  # noqa: E402

td2, rpt, rcc, rcr = traces.td2, traces.rpt, traces.rcc, traces.rcr
rmf = td2.T1.rmf
PARAMS = load_params()
HARNESS_LOOP_OFF = {"ramp_s": 1e-9, "delay_steps": 0}
"""The harness queue off (the controller delays) and its ramp effectively off (a ramp > 0 keeps
the 1 ms valve-lag chunks of the harness)."""

VALVE_LAG_S = 0.1
IMU_SAMPLE_S = 0.01
LAG_CHUNK_S = 0.001
FLAT_RUN_LIMIT_S = 120.0
FLAT_HOLD_AFTER_READY_S = 5.0
REAPPROACH_EVENT_PREFIXES = ("leg_reapproach_", "WARN_LEG_REAPPROACH_")


def preset_config(
    contact: ContactJudge, with_imu_samples: bool, with_reapproach: bool = True
) -> C2Config:
    """``with_10hz_d1`` with the departures of the module docstring; ``with_reapproach``
    False turns the re-approach (P-R8-13) off (the regression comparison of spec 179.1)."""
    base = C2Config(
        contact=contact,
        output_ramp_time_s=None,
        reanchor=ReanchorSettings(enable=False),
        target=TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF),
    )
    config = base.with_10hz_d1()
    zero_calibration = replace(config.zero_calibration, mode=ZeroCalibrationMode.OFF)
    r8 = config.r8 if with_imu_samples else replace(config.r8, imu_sample_period_s=None)
    if not with_reapproach:
        r8 = replace(r8, lifted_reapproach=LiftedReapproachSettings())
    return replace(config, zero_calibration=zero_calibration, r8=r8)


def reapproach_record(controller: C2Controller, commands: list[np.ndarray]) -> dict:
    """Re-approach events and intervals of a run, and a hash of its leg speed commands."""
    names = [event.name for event in controller.events]
    return {
        "reapproach_events": [
            name for name in names if name.startswith(REAPPROACH_EVENT_PREFIXES)
        ],
        "reapproach_intervals": controller.meta()["lifted_reapproach"],
        "commands_sha256": hashlib.sha256(np.array(commands).tobytes()).hexdigest(),
    }


class HarnessAdapter:
    """The harness controller interface (``update(m, t)`` and the metric attributes) on top of
    the project C2."""

    def __init__(self, ctx, contact: str = "pressure", *, with_reapproach: bool = True) -> None:
        self.c = ctx
        rmf.LAST["ctrl"] = self
        config = preset_config(
            ContactJudge.PRESSURE, with_imu_samples=False, with_reapproach=with_reapproach
        )
        self.controller = C2Controller.from_params(PARAMS, config)
        self.controller.reset()
        self.commands: list[np.ndarray] = []
        self.t_touch = self.t_done = self.t_ready_first = None
        self.fault = False
        self.probe_time = 0.0
        self.probe_rounds = 0
        self.events: list = []
        self.probe_log: list = []
        self.phi_f = self.th_f = None
        self.guard_steps = 0

    @property
    def phase(self) -> str:
        return str(self.controller.phase)

    def update(self, m: dict, t: float) -> np.ndarray:
        geometry = self.controller.geometry
        measurements = Measurements(
            t_s=float(t),
            specific_force_m_s2=m["fb"],
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=np.asarray(m["P"]) / geometry.head_area_m2,
            stroke_m=m["s"],
            stroke_corrected_m=m["x"],
        )
        phase_before = self.controller.phase
        speeds = np.array(self.controller.update(measurements).leg_speed_m_s)
        self.commands.append(speeds)
        self._note_phase(phase_before, self.controller.phase, t)
        self.phi_f, self.th_f = self.controller.filtered_attitude_rad
        return speeds

    def _note_phase(self, before: C2Phase, after: C2Phase, t: float) -> None:
        if before is C2Phase.TOUCH and after is not C2Phase.TOUCH:
            self.t_touch = t
        if after is C2Phase.DONE and self.t_done is None:
            self.t_done = t
        if after is C2Phase.READY and self.t_ready_first is None:
            self.t_ready_first = t
        self.fault |= after is C2Phase.FAULT


class HarnessAdapterWithoutReapproach(HarnessAdapter):
    """:class:`HarnessAdapter` with P-R8-12 off (the harness checks the controller class, so a
    ``functools.partial`` does not pass)."""

    def __init__(self, ctx, contact: str = "pressure") -> None:
        super().__init__(ctx, contact, with_reapproach=False)


def run_harness_case(spec: dict, with_reapproach: bool = True) -> dict:
    rcr.SensorsS = traces.RecordingSensors
    rpt.C2RA = HarnessAdapter if with_reapproach else HarnessAdapterWithoutReapproach
    case = traces._harness_case(spec)
    case["rcfg"]["ca_over"] = dict(case["rcfg"]["ca_over"], **HARNESS_LOOP_OFF)
    run = td2.run(case)
    if "error" in run:
        raise RuntimeError(f"{spec['id']}: {run['error']}\n{run.get('tb')}")
    adapter = rmf.LAST["ctrl"]
    if not isinstance(adapter, HarnessAdapter):
        raise RuntimeError("the run did not use the project controller")
    return {
        "id": spec["id"],
        "metrics": traces._metrics(run),
        "fails": run.get("fails"),
        "meta_revision": adapter.controller.meta()["revision"],
        **reapproach_record(adapter.controller, adapter.commands),
    }


# --- 100 Hz IMU run on the reduced plant (own loop) -------------------------------------------


def _lagged_step(plant, command: np.ndarray, valve: np.ndarray, steps: int) -> np.ndarray:
    """Exact mean of the first-order valve lag over the chunk (as ``r8d1_td._step_lag``)."""
    duration_s = steps * plant.dt
    decay = math.exp(-duration_s / VALVE_LAG_S)
    mean_speed = command + (valve - command) * (VALVE_LAG_S / duration_s) * (1.0 - decay)
    valve[:] = command + (valve - command) * decay
    return plant.step(mean_speed, steps)


def _control_period(
    plant, command: np.ndarray, valve: np.ndarray, head_area: np.ndarray, period_s: float
):
    """One control period of 10 ms IMU samples; measurements, pad and crawler forces at its
    end."""
    lag_steps = round(LAG_CHUNK_S / plant.dt)
    chunks_per_sample = round(IMU_SAMPLE_S / LAG_CHUNK_S)
    samples_per_period = round(period_s / IMU_SAMPLE_S)
    imu_samples = []
    for _ in range(samples_per_period):
        force_sum = np.zeros(3)
        for _ in range(chunks_per_sample):
            accumulated = _lagged_step(plant, command, valve, lag_steps)
            force_sum += accumulated[0:3]
        imu_samples.append(force_sum / (lag_steps * chunks_per_sample))
    contact = np.asarray(accumulated[11:15], dtype=float)
    crawler_force = float(accumulated[15])
    measurements = Measurements(
        t_s=plant.t,
        specific_force_m_s2=np.mean(imu_samples, axis=0),
        angular_rate_rad_s=np.asarray(plant.w, dtype=float),
        head_pressure_Pa=plant.pressure() / head_area,
        stroke_m=np.asarray(plant.sref, dtype=float),
        stroke_corrected_m=np.asarray(plant.x, dtype=float),
        imu_specific_force_samples_m_s2=np.array(imu_samples),
    )
    return measurements, contact, crawler_force


def run_imu_100hz_flat(with_reapproach: bool = True) -> dict:
    """Top, level floor, rigid mast, full preset with the 100 Hz attitude filter."""
    rmf.CONFIG.clear()  # rigid mast: FlexPlant flex 0 = the original reduced kernel
    rpt.RCFG.clear()  # no harness valve lag on top of this loop's own
    plant = rmf.FlexPlant("top", 0.0, 0.0)
    plant.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    config = preset_config(
        ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=with_reapproach
    )
    controller = C2Controller.from_params(PARAMS, config)
    head_area = controller.geometry.head_area_m2
    command = np.zeros(4)
    commands = []
    valve = np.zeros(4)
    t_ready = None
    t_liftoff = None
    min_force_after_liftoff = math.inf
    min_contact_after_liftoff = math.inf
    attitude_after_ready = []
    while plant.t < FLAT_RUN_LIMIT_S:
        measurements, contact, crawler_force = _control_period(
            plant, command, valve, head_area, controller.period_s
        )
        command = np.array(controller.update(measurements).leg_speed_m_s)
        commands.append(command)
        if t_liftoff is None and crawler_force == 0.0 and controller.phase is C2Phase.LEVEL:
            t_liftoff = plant.t
        if t_liftoff is not None:
            min_force_after_liftoff = min(min_force_after_liftoff, plant.true_cyl_force().min())
            min_contact_after_liftoff = min(min_contact_after_liftoff, contact.min())
        if controller.phase is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None:
            attitude_after_ready.append(np.degrees(plant.attitude()))
            if plant.t >= t_ready + FLAT_HOLD_AFTER_READY_S:
                break
    meta = controller.meta()
    return {
        "t_ready_s": t_ready,
        "t_crawler_liftoff_s": t_liftoff,
        "min_true_cyl_force_after_liftoff_N": float(min_force_after_liftoff),
        "min_pad_contact_after_liftoff_N": float(min_contact_after_liftoff),
        "max_abs_attitude_after_ready_deg": float(np.abs(attitude_after_ready).max())
        if attitude_after_ready
        else None,
        "probe_rounds": len(controller.probe_history),
        "twist_gain_stiffness": meta["twist_gain_stiffness"],
        "timing": meta["timing"],
        "F_min_N": controller.geometry.F_min_N,
        "phase": str(controller.phase),
        **reapproach_record(controller, commands),
    }


def main() -> None:
    out_path = Path(sys.argv[1])
    result = {
        "harness": [run_harness_case(spec) for spec in traces.CASES],
        "imu_100hz": run_imu_100hz_flat(),
        # P-R8-12 regression: the same runs without the re-approach (command hashes).
        "harness_without_reapproach": [
            run_harness_case(spec, with_reapproach=False) for spec in traces.CASES
        ],
        "imu_100hz_without_reapproach": run_imu_100hz_flat(with_reapproach=False),
    }
    out_path.write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
