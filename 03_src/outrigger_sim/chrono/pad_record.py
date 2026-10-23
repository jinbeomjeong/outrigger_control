"""1 ms pad record for the S6 slope / H4 runs (``00_docs/04_control/s6_control_spec.md`` 6, G6).

A ``runner.run_closed_loop(step_hook=...)`` hook for :class:`~outrigger_sim.chrono.l1_engine.
L1Engine`. Every ``every_steps`` steps (default 5 = 1 ms at dt 2e-4 s; run the loop with
``capture_every_steps=every_steps``) it stores per leg, from the state copy of the step taken
before the ground-bushing hook (R9):

* ``R_world`` total ground reaction on the pad = SMC contact force (normal only, mu = 0) +
  ground-bushing tangential force, world axes (N); ``N`` = ``R . n`` (N); ``n`` floor normal;
* ``a_world`` leg axis unit vector (body -z in world, pad-down direction);
* ``T`` = ``|R - (R . n) n|`` (floor-plane force, the Coulomb-limited part), ``L`` =
  ``|R - (R . a) a|`` (force normal to the leg axis, rod bending), utilisation ``|T| / (mu N)``;
* ball centre and contact point (world), anchor (``ApplicationFrameB``, world) and its
  cumulative travel vector ``slip_total`` (world, m), ``sliding`` flag of the return mapping
  of that step;
* cylinder force, head pressure, motor stroke, rod stroke (``stroke_true``);
* ``F_cyl_min_interval``: the minimum cylinder force over **every physics step** of the
  interval ending at the sample (spec 3 item 3, "all physics steps").

Units SI. ``arrays()`` returns numpy arrays; ``save(path)`` writes an npz.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import quat_to_matrix

FIELDS = (
    "t", "R_world", "N", "n_world", "a_world", "T", "L", "utilisation", "ball_centre_world",
    "contact_point_world", "anchor_world", "slip_total", "sliding", "F_cyl",
    "F_cyl_min_interval", "head_pressure", "s_motor", "stroke_true",
)


class PadRecorder:
    """Per-leg pad record every ``every_steps`` steps (module docstring)."""

    def __init__(self, engine: Any, every_steps: int = 5, *, friction: float | None = None,
                 sample_s: float | None = None):
        """``sample_s`` (variable-dt runs, runner ``dt_schedule``): record at the first step
        that ends at or after the next ``sample_s`` grid time counted from the construction time
        (crossing rule, robust to the step-time sum drift), instead of every ``every_steps``
        steps (run the loop with ``capture_every_s=sample_s``, same rule)."""
        if every_steps < 1:
            raise ValueError("every_steps must be >= 1")
        if sample_s is not None and not sample_s > 0.0:
            raise ValueError("sample_s must be > 0")
        self.engine = engine
        self.model = engine.model
        self.every_steps = int(every_steps)
        self.sample_s = None if sample_s is None else float(sample_s)
        self._t_ref = float(self.model.system.GetChTime())
        self._next_t = None if self.sample_s is None else self._t_ref + self.sample_s
        mu = friction
        if mu is None:
            mu = float(self.model.params.get("contact.rigid_floor.friction"))
        self.mu = float(mu)
        self._rows: dict[str, list[Any]] = {k: [] for k in FIELDS}
        self._k = 0
        self._f_min = np.full(len(self.model.motors), np.inf)
        self.direction_body = np.asarray(self.model.params.actuator.extension_direction, float)

    def __call__(self, engine: Any) -> None:
        model = self.model
        f = np.array([m.GetMotorForce() for m in model.motors], dtype=float)
        self._f_min = np.minimum(self._f_min, f)
        self._k += 1
        t = float(model.system.GetChTime())
        if self.sample_s is None:
            if self._k % self.every_steps:
                return
        else:
            half = 0.5 * float(model.dt_s)
            if t < self._next_t - half:
                return
            while self._next_t <= t + half:
                self._next_t += self.sample_s
        probe = model.last_probe
        if probe is None or probe.t_s != t:
            raise RuntimeError("PadRecorder needs the step's state copy: run the loop with "
                               f"capture_every_steps={self.every_steps} (or capture_every_s)")
        n = np.asarray(probe.floor_normal_world, dtype=float)
        bush = np.nan_to_num(np.asarray(probe.bushing_force_world_N, dtype=float))
        r = np.asarray(probe.pad_contact_world_N, dtype=float) + bush
        a = quat_to_matrix(probe.body_quat_wxyz) @ self.direction_body
        rn = r @ n
        t_vec = r - np.outer(rn, n)
        ra = r @ a
        l_vec = r - np.outer(ra, a)
        t_mag = np.linalg.norm(t_vec, axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            util = np.where(rn > 0.0, t_mag / (self.mu * rn), np.nan)
        centres = np.asarray(probe.pad_sphere_centre_world_m, dtype=float)
        radii = np.asarray(probe.pad_sphere_radius_m, dtype=float)
        truth = model.truth(probe)
        gb = model.bushing
        row = {
            "t": t, "R_world": r, "N": rn, "n_world": n, "a_world": a, "T": t_mag,
            "L": np.linalg.norm(l_vec, axis=1), "utilisation": util,
            "ball_centre_world": centres, "contact_point_world": centres - np.outer(radii, n),
            "anchor_world": np.asarray(probe.bushing_anchor_world_m, dtype=float),
            "slip_total": np.asarray(gb.slip_total_m, dtype=float),
            "sliding": np.asarray(gb.sliding, dtype=bool),
            "F_cyl": probe.motor_force_N.copy(), "F_cyl_min_interval": self._f_min.copy(),
            "head_pressure": probe.motor_force_N / engine.sensor_truth.head_area_m2,
            "s_motor": probe.motor_pos_m.copy(),
            "stroke_true": np.asarray(truth.stroke_true_m, dtype=float),
        }
        for k, v in row.items():
            self._rows[k].append(v)
        self._f_min[:] = np.inf

    def arrays(self) -> dict[str, NDArray[Any]]:
        return {k: np.asarray(v) for k, v in self._rows.items()}

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        np.savez_compressed(p, **self.arrays(), mu=self.mu, every_steps=self.every_steps,
                            sample_s=np.nan if self.sample_s is None else self.sample_s)
        return p


__all__ = ["FIELDS", "PadRecorder"]
