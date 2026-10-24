"""1 ms pad record of the L2b-NSC closed-loop runs (S7 control ③ preparation).

Counterpart of :class:`outrigger_sim.chrono.pad_record.PadRecorder` (L1) with the same field
names, so that ``verify.s6_control`` / ``verify.s6_bundle_c`` read the file unchanged. A
``runner.run_closed_loop(step_hook=...)`` hook for :class:`~outrigger_sim.chrono.l2b_engine.
L2bEngine`; it reads the model directly every physics step (no state copy needed).

NSC read-out rule (``dynamics_model.md`` 5.22.3, rev. 35): the NSC pad contact force carries a
step noise that grows as ``1 / dt^2`` (std 0.8-1.2 kN at 1e-4 s, 124 kN at 1e-5 s), the
force-law output ``F`` only as ``1 / dt`` (18-22 N at 1e-4 s). Therefore

* loads are read from the force-law output: ``F_cyl`` (the value that acted in the step) and
  ``F_cyl_min_interval`` = its minimum over **every physics step** of the 1 ms interval;
* the contact force is averaged: per 1 ms interval the mean over every step
  (``R_world_1ms``), then a centred moving mean over :data:`CONTACT_WINDOW_S` = 20 ms
  (``R_world``, applied in :meth:`L2bPadRecorder.arrays`; truncated windows at the ends);
  ``N``, ``T``, ``L`` and ``utilisation`` are derived from the 20 ms ``R_world``. ``N_raw`` is
  the single-step normal force at the sample (diagnostic only).

Fields (per leg unless noted; world axes; units SI):

* ``t``; ``R_world`` / ``N`` / ``T`` / ``L`` / ``utilisation`` (20 ms, above); ``R_world_1ms``;
  ``N_raw``; ``n_world`` floor normal; ``a_world`` leg axis (body -z, pad down);
* ``ball_centre_world``, ``contact_point_world`` (centre - r n); ``anchor_world`` NaN,
  ``slip_total`` 0, ``sliding`` False (no ground bushing in L2b: stick is the NSC contact);
* ``F_cyl``, ``F_cyl_min_interval`` (force law), ``head_pressure`` ``(F + p_r A_ann) / A_p``,
  ``rod_pressure`` ``p_r``; ``s_motor`` = ``s_ref`` (L1 motor-position equivalent), ``s_link``
  = link displacement ``GetMotorPos()``, ``stroke_true`` = piston ``s + F / k_out``;
* ``lateral_force_world`` lateral bushing force on the rod (rod bending load), ``L_lateral`` its
  magnitude; ``body_quat_wxyz`` (1 ms attitude truth).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import quat_to_matrix

CONTACT_WINDOW_S = 0.020
"""Centred moving-mean window of the NSC contact force (5.22.3: >= 20 ms)."""

FIELDS = (
    "t", "R_world_1ms", "N_raw", "n_world", "a_world", "ball_centre_world",
    "contact_point_world", "anchor_world", "slip_total", "sliding", "F_cyl",
    "F_cyl_min_interval", "head_pressure", "rod_pressure", "s_motor", "s_link", "stroke_true",
    "lateral_force_world", "body_quat_wxyz",
)


def centred_moving_mean(x: NDArray[np.float64], n: int) -> NDArray[np.float64]:
    """Centred moving mean of ``n`` samples along axis 0 (window ``[k - n//2, k - n//2 + n)``),
    truncated and renormalised at the ends."""
    x = np.asarray(x, dtype=float)
    if n <= 1 or x.shape[0] == 0:
        return x.copy()
    flat = x.reshape(x.shape[0], -1)
    c = np.vstack([np.zeros((1, flat.shape[1])), np.cumsum(flat, axis=0)])
    k = np.arange(x.shape[0])
    lo = np.clip(k - n // 2, 0, x.shape[0])
    hi = np.clip(k - n // 2 + n, 0, x.shape[0])
    out = (c[hi] - c[lo]) / (hi - lo)[:, None]
    return out.reshape(x.shape)


class L2bPadRecorder:
    """Per-leg pad record every ``every_steps`` steps (module docstring)."""

    def __init__(self, engine: Any, every_steps: int = 10, *, friction: float | None = None,
                 window_s: float = CONTACT_WINDOW_S) -> None:
        if every_steps < 1:
            raise ValueError("every_steps must be >= 1")
        self.engine = engine
        self.model = engine.model
        self.every_steps = int(every_steps)
        model = self.model
        self.mu = float(model.params.l2b.rigid_floor.friction if friction is None else friction)
        self.sample_s = self.every_steps * float(model.dt_s)
        self.window_samples = max(1, round(float(window_s) / self.sample_s))
        self.window_s = self.window_samples * self.sample_s
        self.direction_body = np.asarray(model.params.actuator.extension_direction, float)
        self.radii = np.asarray(model.sphere_radii_m, dtype=float)
        n = len(model.legs)
        self._rows: dict[str, list[Any]] = {k: [] for k in FIELDS}
        self._k = 0
        self._f_min = np.full(n, np.inf)
        self._r_sum = np.zeros((n, 3))
        self._a_ann = np.asarray(model.params.l2b.rod_side.annulus_area_m2, dtype=float)

    def __call__(self, engine: Any) -> None:
        model = self.model
        act = model.actuator
        f = act.acting_force_N
        self._f_min = np.minimum(self._f_min, f)
        for i, leg in enumerate(model.legs):
            c = leg.GetContactForce()
            self._r_sum[i, 0] += c.x
            self._r_sum[i, 1] += c.y
            self._r_sum[i, 2] += c.z
        self._k += 1
        if self._k % self.every_steps:
            return
        t = float(model.system.GetChTime())
        n = model.floor_normal_world()
        sup = model.superstructure
        q = sup.GetRot()
        quat = np.array([q.e0, q.e1, q.e2, q.e3], dtype=float)
        a = quat_to_matrix(quat) @ self.direction_body
        centres = np.array([[p.x, p.y, p.z] for p in (
            leg.TransformPointLocalToParent(c)
            for leg, c in zip(model.legs, model.sphere_centres_local_ch, strict=True))])
        raw = np.array([[v.x, v.y, v.z] for v in (leg.GetContactForce() for leg in model.legs)])
        s_link = np.array([m.GetMotorPos() for m in model.motors], dtype=float)
        p_r = (np.zeros(len(f)) if act.rod_side is None or not act.rod_side.armed
               else act.rod_side.rod_pressure_Pa)
        row = {
            "t": t, "R_world_1ms": self._r_sum / self.every_steps, "N_raw": raw @ n,
            "n_world": n, "a_world": a, "ball_centre_world": centres,
            "contact_point_world": centres - np.outer(self.radii, n),
            "anchor_world": np.full((len(f), 3), np.nan), "slip_total": np.zeros((len(f), 3)),
            "sliding": np.zeros(len(f), dtype=bool), "F_cyl": f,
            "F_cyl_min_interval": self._f_min.copy(),
            "head_pressure": (f + p_r * self._a_ann) / act.head_area_m2, "rod_pressure": p_r,
            "s_motor": act.reference.s_ref_m, "s_link": s_link,
            "stroke_true": act.stroke_true_m(s_link, f),
            "lateral_force_world": np.asarray(model.bushings.acting_force_on_rod_N, dtype=float),
            "body_quat_wxyz": quat,
        }
        for key, value in row.items():
            self._rows[key].append(np.array(value, copy=True))
        self._f_min[:] = np.inf
        self._r_sum[:] = 0.0

    def arrays(self) -> dict[str, NDArray[Any]]:
        out = {k: np.asarray(v) for k, v in self._rows.items()}
        if out["t"].size == 0:
            return out
        r = centred_moving_mean(out["R_world_1ms"], self.window_samples)
        n = out["n_world"]
        rn = np.einsum("kij,kj->ki", r, n)
        t_vec = r - rn[:, :, None] * n[:, None, :]
        ra = np.einsum("kij,kj->ki", r, out["a_world"])
        l_vec = r - ra[:, :, None] * out["a_world"][:, None, :]
        t_mag = np.linalg.norm(t_vec, axis=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            util = np.where(rn > 0.0, t_mag / (self.mu * rn), np.nan)
        out.update(R_world=r, N=rn, T=t_mag, L=np.linalg.norm(l_vec, axis=2), utilisation=util,
                   L_lateral=np.linalg.norm(out["lateral_force_world"], axis=2))
        return out

    def meta(self) -> dict[str, Any]:
        return {"format": "l2b_pad_record_v1", "sample_s": self.sample_s,
                "every_steps": self.every_steps, "contact_window_s": self.window_s,
                "contact_window_samples": self.window_samples, "mu": self.mu,
                "rule": "dynamics_model.md 5.22.3: loads from the force-law output (every-step "
                        "minimum per 1 ms); NSC contact force as a 20 ms centred mean of the "
                        "per-step 1 ms means (N, T, L, utilisation, R_world)"}

    def save(self, path: str | Path) -> Path:
        import json

        p = Path(path)
        np.savez_compressed(p, **self.arrays(), mu=self.mu, every_steps=self.every_steps,
                            sample_s=self.sample_s, meta_json=np.array(json.dumps(self.meta())))
        return p


__all__ = ["CONTACT_WINDOW_S", "FIELDS", "L2bPadRecorder", "centred_moving_mean"]
