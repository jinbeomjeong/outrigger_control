"""1 ms pad record of the S8 L2b-NSC runs: S7 fields + seal friction + time-based sampling.

``s6_control_spec.md`` rev. 39 201.1 / 209.1 C-S8-2: the record must separate

* ``F_cyl`` / ``F_cyl_min_interval``: the **rod axial force** = force-law output (oil + seal
  friction), the truth ``F_i`` of C1 / C8 / C9 / F rows (unchanged name, so the S6 / S7 judges
  read it as before);
* ``F_pressure`` / ``F_pressure_min_interval`` / ``F_pressure_max_interval``: the pressure force
  ``F - f`` (two-sensor net force truth, the source of the reading ``F_hat``);
* ``f_seal``, ``seal_stuck``, ``s_piston``, ``F_seal_limit`` (1 ms samples of the state that
  belongs to the acting force) and the CB state ``cb_y``, ``cb_delta``;
* ``head_pressure`` = ``(F_p + p_r A_ann) / A_p`` (was ``F`` in S7: equal without friction),
  ``stroke_true`` = ``s_p`` (friction state) or ``s + F / k_out``.

Sampling is on **time** (every :attr:`sample_s`, crossing rule): a dt window of 1e-5 s keeps the
1 ms grid (the S7 recorder counted steps). The per-interval contact mean is step-length
weighted. All quantities come through :mod:`outrigger_sim.chrono.s8_plant_adapter`; without a
friction element ``f_seal`` = 0, ``seal_stuck`` False, ``F_pressure`` = ``F_cyl``.

Format ``l2b_pad_record_v1`` (the S7 judge checks this name) + meta ``s8_fields``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.chrono import s8_plant_adapter as plant
from outrigger_sim.chrono.l2b_pad_record import (
    CONTACT_WINDOW_S,
    FIELDS,
    L2bPadRecorder,
    centred_moving_mean,
)
from outrigger_sim.frames import quat_to_matrix

S8_FIELDS = ("F_pressure", "F_pressure_min_interval", "F_pressure_max_interval", "f_seal",
             "seal_stuck", "s_piston", "F_seal_limit", "cb_y", "cb_delta", "dt_interval",
             "F_cyl_mean_interval")
DERIVED_AIR_FIELDS = ("F_cyl_mean_20ms", "airborne")
"""S8-A2 (``dynamics_model.md`` 5.26.10): ``F_cyl_mean_20ms`` = centred 20 ms mean of the
step-weighted 1 ms mean rod force, ``airborne`` = 20 ms pad normal ``N <= 0``. Airborne samples
are not judged on the 1 ms rod-force minimum (rod ringing); both values are recorded."""


class L2bPadRecorderS8(L2bPadRecorder):
    """Time-sampled S8 pad record (module docstring)."""

    def __init__(self, engine: Any, sample_s: float = 1.0e-3, *, friction: float | None = None,
                 window_s: float = CONTACT_WINDOW_S) -> None:
        every = max(1, round(float(sample_s) / float(engine.model.dt_s)))
        super().__init__(engine, every_steps=every, friction=friction, window_s=window_s)
        self.sample_s = float(sample_s)
        self.window_samples = max(1, round(float(window_s) / self.sample_s))
        self.window_s = self.window_samples * self.sample_s
        for k in S8_FIELDS:
            self._rows[k] = []
        n = len(self.model.legs)
        self._fp_min = np.full(n, np.inf)
        self._fp_max = np.full(n, -np.inf)
        self._r_sum_w = np.zeros((n, 3))
        self._f_sum_w = np.zeros(n)
        self._w = 0.0
        self._next_t: float | None = None
        self._plant_seen = {"friction": False, "cb": False}

    def __call__(self, engine: Any) -> None:
        model = self.model
        act = model.actuator
        t = float(model.system.GetChTime())
        dt = float(model.dt_s)
        if self._next_t is None:
            self._next_t = t - dt + self.sample_s
        f = act.acting_force_N
        fp = plant.pressure_force_N(act, f)
        self._f_min = np.minimum(self._f_min, f)
        self._f_sum_w += f * dt
        self._fp_min = np.minimum(self._fp_min, fp)
        self._fp_max = np.maximum(self._fp_max, fp)
        for i, leg in enumerate(model.legs):
            c = leg.GetContactForce()
            self._r_sum_w[i, 0] += c.x * dt
            self._r_sum_w[i, 1] += c.y * dt
            self._r_sum_w[i, 2] += c.z * dt
        self._w += dt
        if t < self._next_t - 0.5 * dt:
            return
        while self._next_t <= t + 0.5 * dt:
            self._next_t += self.sample_s
        n_world = model.floor_normal_world()
        q = model.superstructure.GetRot()
        quat = np.array([q.e0, q.e1, q.e2, q.e3], dtype=float)
        a = quat_to_matrix(quat) @ self.direction_body
        centres = np.array([[p.x, p.y, p.z] for p in (
            leg.TransformPointLocalToParent(c)
            for leg, c in zip(model.legs, model.sphere_centres_local_ch, strict=True))])
        raw = np.array([[v.x, v.y, v.z] for v in (leg.GetContactForce() for leg in model.legs)])
        s_link = np.array([m.GetMotorPos() for m in model.motors], dtype=float)
        nleg = len(f)
        p_r = (np.zeros(nleg) if act.rod_side is None or not act.rod_side.armed
               else act.rod_side.rod_pressure_Pa)
        split = getattr(act, "pressure_split", None)
        if callable(split):  # S8-A1 head floor
            p_h, p_r, hit = split(fp, p_r, act.reference.u_applied_m_s)
            self.pressure_floor_samples += hit
        else:
            p_h = (fp + p_r * self._a_ann) / act.head_area_m2
        fr = plant.friction_state(act)
        cb = plant.cb_state(act)
        self._plant_seen["friction"] |= fr is not None
        self._plant_seen["cb"] |= cb is not None
        row = {
            "t": t, "R_world_1ms": self._r_sum_w / self._w, "N_raw": raw @ n_world,
            "n_world": n_world, "a_world": a, "ball_centre_world": centres,
            "contact_point_world": centres - np.outer(self.radii, n_world),
            "anchor_world": np.full((nleg, 3), np.nan), "slip_total": np.zeros((nleg, 3)),
            "sliding": np.zeros(nleg, dtype=bool), "F_cyl": f,
            "F_cyl_min_interval": self._f_min.copy(),
            "head_pressure": p_h, "rod_pressure": p_r,
            "s_motor": act.reference.s_ref_m, "s_link": s_link,
            "stroke_true": plant.piston_position_m(act, s_link, f),
            "lateral_force_world": np.asarray(model.bushings.acting_force_on_rod_N, dtype=float),
            "body_quat_wxyz": quat,
            "F_pressure": fp, "F_pressure_min_interval": self._fp_min.copy(),
            "F_pressure_max_interval": self._fp_max.copy(),
            "f_seal": np.zeros(nleg) if fr is None else np.nan_to_num(fr["f_N"]),
            "seal_stuck": np.zeros(nleg, bool) if fr is None else fr["stuck"],
            "s_piston": plant.piston_position_m(act, s_link, f),
            "F_seal_limit": np.zeros(nleg) if fr is None else fr["F_s_N"],
            "cb_y": np.full(nleg, np.nan) if cb is None else cb["cb_y"],
            "cb_delta": np.full(nleg, np.nan) if cb is None else cb["cb_delta_m"],
            "dt_interval": self._w,
            "F_cyl_mean_interval": self._f_sum_w / self._w,
        }
        for key, value in row.items():
            self._rows[key].append(np.array(value, copy=True))
        self._f_min[:] = np.inf
        self._f_sum_w[:] = 0.0
        self._fp_min[:] = np.inf
        self._fp_max[:] = -np.inf
        self._r_sum_w[:] = 0.0
        self._w = 0.0

    def meta(self) -> dict[str, Any]:
        out = super().meta()
        out.update(sample_s=self.sample_s, contact_window_s=self.window_s,
                   contact_window_samples=self.window_samples,
                   sampling="time (crossing rule), contact mean step-length weighted",
                   s8_fields=list(S8_FIELDS), base_fields=list(FIELDS),
                   derived_air_fields=list(DERIVED_AIR_FIELDS),
                   air_rule="S8-A2: airborne (20 ms N <= 0) samples are not judged on the 1 ms "
                            "rod-force minimum; F_cyl_mean_20ms and the 1 ms minimum are "
                            "recorded",
                   plant_seen=dict(self._plant_seen),
                   s8_rule="C-S8-2: F_cyl = rod axial force (oil + seal friction, truth); "
                           "F_pressure = F - f (two-sensor net force truth); head_pressure from "
                           "F_pressure; stroke_true = piston s_p",
                   plant_adapter=plant.adapter_meta())
        return out

    def arrays(self) -> dict[str, NDArray[Any]]:
        out = super().arrays()
        if out["t"].size == 0:
            return out
        out["F_cyl_mean_20ms"] = centred_moving_mean(out["F_cyl_mean_interval"],
                                                     self.window_samples)
        out["airborne"] = ~(out["N"] > 0.0)
        return out


__all__ = ["S8_FIELDS", "L2bPadRecorderS8"]
