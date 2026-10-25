"""S9 SCM model behind the closed-loop engine boundary (the L2bEngine interface).

:class:`S9Engine` is :class:`~outrigger_sim.chrono.l2b_engine.L2bEngine` with the ground forces
read from the S9 model: the truth pad / crawler contact forces are the SCM resultant plus the
anchor-bushing force (:meth:`S9Model.contact_forces_world_N`) instead of ``GetContactForce`` (SCM
forces are loads, not contacts, so ``GetContactForce`` reads 0). Measurements (IMU truth,
``p_h``, ``p_r``, ``s_ref``, piston stroke) are the L2b definitions unchanged; the controller sees
the same interface as on the L2b-NSC model (C2 connected through ``runner.run_closed_loop``).

Snapshots / ``reset`` are not available (``S9Model.snapshot``).
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from outrigger_sim.chrono.l2b_engine import CONTACT_WINDOW_S, L2bEngine
from outrigger_sim.chrono.scm_model import S9Model, read_s9_probe
from outrigger_sim.engine import EngineInfo
from outrigger_sim.chrono.snapshot import engine_info
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M
from outrigger_sim.signals import LEG_COUNT, TruthState

ENGINE_NAME = "S9_SCM"


class S9Engine(L2bEngine):
    """Closed-loop engine around an :class:`S9Model` (module docstring)."""

    def __init__(self, model: S9Model, *, imu_mount_point_body_m: ArrayLike = IMU_MOUNT_C1_BODY_M,
                 imu_method: str = "sensors_imu",
                 contact_window_s: float | None = CONTACT_WINDOW_S) -> None:
        super().__init__(model, imu_mount_point_body_m=imu_mount_point_body_m,  # type: ignore[arg-type]
                         imu_method=imu_method, contact_window_s=contact_window_s)

    @property
    def info(self) -> EngineInfo:
        return engine_info(ENGINE_NAME)

    def meta(self) -> dict[str, Any]:
        meta = self.model.meta()
        meta.update(engine="pychrono", model=ENGINE_NAME, params_sha256=self.model.params.sha256,
                    sensor_truth=self.sensor_meta(), truth_contact=self.contact_window_meta(),
                    closed_loop_hook="step callback at the head of S9Model.actuator_hooks (after "
                                     "the anchor-bushing hooks, before the force-law hook): "
                                     "command issued at t_n drives step n+1")
        return meta

    def truth(self) -> TruthState:
        self._check_open()
        probe = self.model.last_probe
        if probe is None or probe.t_s != self.time_s:
            probe = read_s9_probe(self.model)  # type: ignore[arg-type]
        state = self.model.truth(probe)
        if self._cwin == 0 or self._cn == 0:
            return state
        mean = self._cbuf[: self._cn].mean(axis=0)
        n = np.asarray(probe.floor_normal_world, dtype=float)
        pads = mean[:LEG_COUNT]
        fn = pads @ n
        return dataclasses.replace(state, F_contact_n_N=fn, F_contact_t_N=(pads - np.outer(fn, n))[:, :2],
                                   is_pad_in_contact=fn > 0.0, F_crawler_N=mean[LEG_COUNT].copy())

    def reset(self, start: Any = None) -> TruthState:  # noqa: ARG002
        raise NotImplementedError("S9Engine: build the start with the S9Model constructor")

    def _pre_actuator_hook(self, model: Any, dt_s: float) -> None:
        del dt_s
        t = self.time_s
        forces = model.actuator.acting_force_N
        pos = model.superstructure.GetPos()
        finite = bool(np.all(np.isfinite(forces))) and all(math.isfinite(c) for c in (pos.x, pos.y, pos.z))
        self._mon_steps += 1
        if self._cwin:
            pads, crawler = model.contact_forces_world_N()
            row = self._cbuf[self._ci]
            row[:LEG_COUNT] = pads
            row[LEG_COUNT] = crawler
            self._ci = (self._ci + 1) % self._cwin
            self._cn = min(self._cn + 1, self._cwin)
        if not finite:
            self._mon_nonfinite += 1
            if self._mon_first_bad is None:
                self._mon_first_bad = t
        else:
            up = forces > self._f_max
            self._f_max = np.where(up, forces, self._f_max)
            self._f_max_t = np.where(up, t, self._f_max_t)
            down = forces < self._f_min
            self._f_min = np.where(down, forces, self._f_min)
            self._f_min_t = np.where(down, t, self._f_min_t)
        if self._callback is not None:
            self._callback(self)


__all__ = ["ENGINE_NAME", "S9Engine"]
