"""Adapter: the v5 plant options on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 2.0).

It holds no controller logic. :func:`make_hydraulics_plant_class` puts the options on the
flow-limited plant the way ``harness_flow`` does; ``verdict_runs.execute(..., hydraulics=...)``
installs it. Without options no line of this module runs and the commands stay bit for bit.

Inner step of an armed plant (spec 2.0, the numbers are the rows of its table):
  5   ``_rod_force``: law, then the M2 shift of ``sref``, then the kernel (law C, friction)

M2 (spec 2.3): the harness has no tracked rod pressure, so this class solves its first-order lag.
The start is ``p_r0 - G_r / A_ann`` at the release, the target comes from
``RodChamberLegParams.moving_target_rod_pressure_Pa`` (the law is not copied here) with the net oil
force. All pressures are model values and ASSUMPTIONS.

Pressures gauge [Pa], speeds m/s, extension positive.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SOURCE_DIR = Path(__file__).resolve().parents[3] / "03_src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from outrigger_sim.hydraulics.rod_chamber import (  # noqa: E402
    RodChamberLegParams,
    RodChamberMode,
)
from outrigger_sim.hydraulics.rod_release import RodReleaseShift  # noqa: E402
from outrigger_sim.hydraulics.v5_options import HydraulicOptions  # noqa: E402

LEG_COUNT = 4
UNUSED_OUTER_STIFFNESS_N_M = math.inf
"""``moving_target_rod_pressure_Pa`` does not read the outer stiffness; soil rows change it."""
STROKE_LOWER_END_M = 0.0
HARNESS_VALVE_TAU_S = 0.1
"""The harness valve lag is always on with this value (``c2py_r8d1_closed_loop.VALVE_LAG_S``)."""
_LAST_ARMED: list = [None]
"""The plant armed last in this process (the event branch runs on it), for the run record."""
_INSTALLED: dict = {}


class _RodPressureLag:
    """First-order lag of the moving rod pressure of one plant (module docstring)."""

    def __init__(self, plant) -> None:
        head_area_m2 = plant.flow_limiter.params.A_h
        self._legs = [
            RodChamberLegParams(
                head_area_m2=float(head_area_m2[i]),
                annulus_area_m2=float(plant.A_ann[i]),
                head_stiffness_N_m=float(plant.kh[i]),
                rod_stiffness_N_m=float(plant.kr[i]),
                outer_stiffness_N_m=UNUSED_OUTER_STIFFNESS_N_M,
                rod_weight_N=0.0)
            for i in range(LEG_COUNT)]
        self._keep = math.exp(-plant.dt / plant.tau)
        self.pressure_Pa = np.zeros(LEG_COUNT)

    def start(self, leg: int, pressure_Pa: float) -> None:
        self.pressure_Pa[leg] = pressure_Pa

    def relax(self, leg: int, direction: float, force_N: float) -> float:
        mode = RodChamberMode.EXT if direction > 0.0 else RodChamberMode.RET
        target_Pa = self._legs[leg].moving_target_rod_pressure_Pa(mode, force_N)
        self.pressure_Pa[leg] = target_Pa + (self.pressure_Pa[leg] - target_Pa) * self._keep
        return self.pressure_Pa[leg]


def make_hydraulics_plant_class(base: type, options: HydraulicOptions) -> type:
    """Subclass of the flow-limited plant ``base`` with the v5 options.

    Args:
        base: Class from ``harness_flow.make_flow_plant_class``.
        options: The options; ``flow`` is the job of ``FlowSetting`` on the harness.

    Returns:
        The plant class, deep-copied state included (the event branches copy plants).
    """

    class HydraulicsPlant(base):
        """Harness plant with the v5 options (module docstring)."""

        def arm(self):
            result = super().arm()
            _LAST_ARMED[0] = self
            self.rod_release = None
            if options.rod_release_force:
                self.rod_release = RodReleaseShift(self.A_ann)
                self.rod_pressure_lag = _RodPressureLag(self)
            return result

        def _rod_force(self, u):
            was_locked = self.locked.copy()
            rod_force_N = super()._rod_force(u)
            if self.rod_release is not None:
                self._shift_reference_for_rod_pressure(rod_force_N, was_locked)
            return rod_force_N

        def _shift_reference_for_rod_pressure(self, rod_force_N, was_locked) -> None:
            """Spec 2.3: M2 on the state after the law; acts from this inner step on."""
            pressure_Pa = self.p_r0 - rod_force_N / self.A_ann
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            for i in np.flatnonzero(~self.locked):
                if was_locked[i]:
                    lag.start(i, float(pressure_Pa[i]))
                pressure_Pa[i] = lag.relax(i, float(self.last_dir[i]), float(net_force_N[i]))
            shift_m = self.rod_release.shift_m(
                pressure_Pa, self.kh, ~self.locked, STROKE_LOWER_END_M - self.sref,
                self.geo.stroke - self.sref)
            self.sref += shift_m

    return HydraulicsPlant


def plant_record(plant) -> dict:
    """Per-leg v5 totals of one plant for the result (M2 shift, clipped steps)."""
    if plant is None:
        return {}
    record = {}
    if getattr(plant, "rod_release", None) is not None:
        record.update(plant.rod_release.record())
    return record


def last_armed_record() -> dict:
    return plant_record(_LAST_ARMED[0])


def install(verdict_runs_module, options: HydraulicOptions) -> None:
    """Every plant built from now on in this process carries ``options``.

    The patch stays for the rest of the process, so a worker runs one such case.

    Raises:
        ValueError: Options the harness takes elsewhere or does not have.
    """
    if options.flow is not None:
        raise ValueError("the harness flow limit is the FlowSetting of the run, not options.flow")
    if options.lock_window_follows_plant:
        raise ValueError("the controller lock window is not connected yet (spec commit 7)")
    if options.valve_tau_s is not None and options.valve_tau_s != HARNESS_VALVE_TAU_S:
        raise ValueError(f"the harness valve lag is fixed at {HARNESS_VALVE_TAU_S} s")
    if _INSTALLED.get(id(verdict_runs_module)) is not None:
        if _INSTALLED[id(verdict_runs_module)] != options:
            raise RuntimeError("other v5 options are installed in this process already")
        return
    _INSTALLED[id(verdict_runs_module)] = options
    make_flow_plant_class = verdict_runs_module.make_flow_plant_class

    def make_class(base, setting):
        return make_hydraulics_plant_class(make_flow_plant_class(base, setting), options)

    verdict_runs_module.make_flow_plant_class = make_class
