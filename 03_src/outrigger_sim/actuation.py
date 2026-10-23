"""Engine-independent leg speed reference: rate limit, stroke-end braking, law C saturation.

The same per-step rule as :meth:`outrigger_sim.chrono.actuators.L1SpeedActuator.advance` (L1,
``dynamics_model.md`` 4.4, rev. 23 5.10 law C), without the Chrono motor functions, so that
the L2b-NSC force actuator (plan S7, ``chrono/l2b_actuator``) integrates its ``s_ref`` with
the identical limiter. ``05_tests/chrono/test_l2b_actuator.py`` checks bit equality with the
L1 actuator for random command and force sequences.

Per step of length ``dt`` (called once after every physics step, hook order step 3):

* target ``clip(u_cmd, -v_max, v_max)``;
* stroke-end braking cap ``sqrt((a dt / 2)^2 + 2 a d) - a dt / 2`` towards each (soft) end
  ``d`` away, ``a = v_max / ramp_s`` (``actuator.command_ramp_s``, ASSUMPTION 0.1 s);
* acceleration limit: the applied speed moves by at most ``a dt``;
* force saturation (law C, per-leg limits = 210 bar x head / annulus area): with the judged
  force ``F_dec >= F_ext`` and ``u > 0`` (or ``<= -F_ret`` and ``u < 0``) the leg decelerates
  with ``v_max / t_sat`` (``t_sat`` = 2 ms, ASSUMPTION) and a start from rest in that direction
  stays 0. ``F_dec = F - m_rod (u_n - u_{n-1}) / dt`` when a rod mass is given (L1: removes
  the rigid motor's own inertial pulse from the motor reaction); ``F_dec = F`` without one
  (L2b: the force-law value contains no rod inertia, so it is already the judged force);
* integration ``s_ref <- clip(s_ref + u dt, lo, hi)`` (the speed of a clipped step is
  ``(s_new - s) / dt``).

Units SI; arrays per leg in LEG_ORDER. No pychrono import.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

SATURATION_STOP_S = 2.0e-3
"""ASSUMPTION (dyn rev. 23 law C, user decision 2026-10-21): saturation stop time; equal to
``outrigger_sim.chrono.actuators.SATURATION_STOP_S``."""

STATE_KEYS = (
    "s_ref_m",
    "u_applied_m_s",
    "prev_applied_u_m_s",
    "u_cmd_m_s",
    "soft_lo_m",
    "soft_hi_m",
)
"""Keys of :meth:`SpeedReference.state_arrays` (snapshot part, R16)."""


def _vector(value: ArrayLike, n: int, name: str) -> NDArray[np.float64]:
    out = np.array(value, dtype=float).reshape(-1)
    if out.shape != (n,):
        raise ValueError(f"{name}: expected {n} values, got shape {out.shape}")
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name}: non-finite value in {out}")
    return out


def _limit(value: ArrayLike, n: int, name: str) -> float | NDArray[np.float64]:
    arr = np.array(value, dtype=float).reshape(-1)
    if arr.size not in (1, n):
        raise ValueError(f"{name}: expected 1 or {n} values, got {arr}")
    if not (np.all(arr > 0.0) and np.all(np.isfinite(arr))):
        raise ValueError(f"{name}: limits must be positive, got {arr.tolist()!r}")
    return float(arr[0]) if bool(np.all(arr == arr[0])) else arr


class SpeedReference:
    """Rate-limited, force-saturated speed reference and its integral ``s_ref``.

    Args:
        s_init_m: Initial reference per leg [m].
        ranges_m: ``(lo, hi)`` stroke range per leg [m].
        max_speed_m_s: ``v_max``.
        ramp_s: 0 -> v_max time of the acceleration limit (0 = no limit).
        max_force_extend_N, max_force_retract_N: Force limits (positive; one value or one per
            leg); None for both = no force saturation.
        rod_mass_kg: Inertia correction of the judged force (module docstring); None = none.
        saturation_stop_s: ``t_sat`` (> 0).
    """

    def __init__(
        self,
        s_init_m: ArrayLike,
        ranges_m: Sequence[Sequence[float]],
        *,
        max_speed_m_s: float,
        ramp_s: float,
        max_force_extend_N: ArrayLike | None = None,
        max_force_retract_N: ArrayLike | None = None,
        rod_mass_kg: ArrayLike | None = None,
        saturation_stop_s: float = SATURATION_STOP_S,
    ) -> None:
        n = len(ranges_m)
        if n == 0:
            raise ValueError("need at least one leg")
        lo_hi = np.array([[float(r[0]), float(r[1])] for r in ranges_m])
        if np.any(lo_hi[:, 1] <= lo_hi[:, 0]):
            raise ValueError(f"empty stroke range in {lo_hi.tolist()}")
        if not (max_speed_m_s > 0.0 and math.isfinite(max_speed_m_s)):
            raise ValueError(f"max speed must be positive: {max_speed_m_s!r}")
        if not (ramp_s >= 0.0 and math.isfinite(ramp_s)):
            raise ValueError(f"ramp time must be >= 0: {ramp_s!r}")
        if not (saturation_stop_s > 0.0 and math.isfinite(saturation_stop_s)):
            raise ValueError(f"saturation_stop_s must be positive: {saturation_stop_s!r}")
        if (max_force_extend_N is None) != (max_force_retract_N is None):
            raise ValueError("give both force limits or none")
        self._n = n
        self._lo = lo_hi[:, 0]
        self._hi = lo_hi[:, 1]
        self._v_max = float(max_speed_m_s)
        self._ramp_s = float(ramp_s)
        self._t_sat = float(saturation_stop_s)
        self._f_ext = (
            None if max_force_extend_N is None else _limit(max_force_extend_N, n, "extend")
        )
        self._f_ret = (
            None if max_force_retract_N is None else _limit(max_force_retract_N, n, "retract")
        )
        self._m_rod = None if rod_mass_kg is None else _vector(rod_mass_kg, n, "rod_mass_kg")
        s0 = _vector(s_init_m, n, "s_init_m")
        if np.any(s0 < self._lo) or np.any(s0 > self._hi):
            raise ValueError(f"initial reference {s0} outside the stroke range")
        self._s_ref = s0
        self._u = np.zeros(n)
        self._u_prev = np.zeros(n)
        self._u_cmd = np.zeros(n)
        self._soft_lo = self._lo.copy()
        self._soft_hi = self._hi.copy()
        self._saturated = np.zeros(n, dtype=bool)
        self._saturation_steps = np.zeros(n, dtype=np.int64)
        self._saturation_starts = np.zeros(n, dtype=np.int64)
        self._last_judged = np.full(n, np.nan)

    # --- views ----------------------------------------------------------------------------

    @property
    def n_legs(self) -> int:
        return self._n

    @property
    def max_speed_m_s(self) -> float:
        return self._v_max

    @property
    def ramp_s(self) -> float:
        return self._ramp_s

    @property
    def saturation_stop_s(self) -> float:
        return self._t_sat

    @property
    def accel_limit_m_s2(self) -> float:
        return math.inf if self._ramp_s == 0.0 else self._v_max / self._ramp_s

    @property
    def force_limits_N(self) -> tuple[Any, Any] | None:
        if self._f_ext is None or self._f_ret is None:
            return None

        def plain(v: float | NDArray[np.float64]) -> float | list[float]:
            return v if isinstance(v, float) else [float(x) for x in v]

        return (plain(self._f_ext), plain(self._f_ret))

    @property
    def s_ref_m(self) -> NDArray[np.float64]:
        """Reference after the last :meth:`advance` (end of the next step)."""
        return self._s_ref.copy()

    @property
    def u_applied_m_s(self) -> NDArray[np.float64]:
        """Applied speed set by the last :meth:`advance` (acts during the next step)."""
        return self._u.copy()

    @property
    def command_m_s(self) -> NDArray[np.float64]:
        return self._u_cmd.copy()

    @property
    def saturated(self) -> NDArray[np.bool_]:
        return self._saturated.copy()

    @property
    def saturation_step_count(self) -> NDArray[np.int64]:
        return self._saturation_steps.copy()

    @property
    def saturation_start_count(self) -> NDArray[np.int64]:
        return self._saturation_starts.copy()

    @property
    def last_judged_force_N(self) -> NDArray[np.float64]:
        return self._last_judged.copy()

    @property
    def soft_limits_m(self) -> NDArray[np.float64]:
        return np.column_stack([self._soft_lo, self._soft_hi])

    @property
    def stroke_range_m(self) -> NDArray[np.float64]:
        return np.column_stack([self._lo, self._hi])

    # --- inputs ---------------------------------------------------------------------------

    def set_command(self, leg_speed_m_s: ArrayLike) -> None:
        self._u_cmd = _vector(leg_speed_m_s, self._n, "leg_speed_m_s")

    def set_soft_limits(self, lo_m: ArrayLike | None = None, hi_m: ArrayLike | None = None) -> None:
        """Narrow the travel range inside the stroke range (``s_ref`` must lie inside)."""
        lo = self._soft_lo if lo_m is None else _vector(lo_m, self._n, "lo_m")
        hi = self._soft_hi if hi_m is None else _vector(hi_m, self._n, "hi_m")
        if np.any(lo < self._lo) or np.any(hi > self._hi) or np.any(lo > hi):
            raise ValueError(f"soft limits {lo.tolist()} .. {hi.tolist()} not inside the stroke")
        if np.any(self._s_ref < lo) or np.any(self._s_ref > hi):
            raise ValueError(f"reference {self._s_ref.tolist()} outside the new soft limits")
        self._soft_lo = lo.copy()
        self._soft_hi = hi.copy()

    def reset_saturation_counters(self) -> None:
        self._saturation_steps[:] = 0

    # --- step -----------------------------------------------------------------------------

    def advance(self, dt_s: float, *, cylinder_force_N: ArrayLike | None = None) -> None:
        """One step of length ``dt_s`` (module docstring).

        Args:
            cylinder_force_N: Cylinder force per leg of the step just taken (+ = extend);
                judged against the force limits when given and the limits exist.
        """
        dt = float(dt_s)
        if not (dt > 0.0 and math.isfinite(dt)):
            raise ValueError(f"dt must be positive: {dt_s!r}")
        a = self.accel_limit_m_s2
        s = self._s_ref
        u = self._u
        lo, hi = self._soft_lo, self._soft_hi
        target = np.clip(self._u_cmd, -self._v_max, self._v_max)
        if math.isfinite(a):
            step = a * dt
            half = 0.5 * step
            up = np.sqrt(half * half + 2.0 * a * np.maximum(hi - s, 0.0)) - half
            down = np.sqrt(half * half + 2.0 * a * np.maximum(s - lo, 0.0)) - half
            target = np.minimum(np.maximum(target, -down), up)
            u_new = u + np.clip(target - u, -step, step)
        else:
            target = np.where((s >= hi) & (target > 0.0), 0.0, target)
            target = np.where((s <= lo) & (target < 0.0), 0.0, target)
            u_new = target
        if cylinder_force_N is not None and self._f_ext is not None and self._f_ret is not None:
            f = _vector(cylinder_force_N, self._n, "cylinder_force_N")
            f_dec = f if self._m_rod is None else f - self._m_rod * (u - self._u_prev) / dt
            cut = ((f_dec >= self._f_ext) & (u_new > 0.0)) | (
                (f_dec <= -self._f_ret) & (u_new < 0.0)
            )
            self._last_judged = f_dec
            if np.any(cut):
                step_sat = self._v_max / self._t_sat * dt
                same_dir = np.sign(u) == np.sign(u_new)
                decel = np.sign(u) * np.maximum(np.abs(u) - step_sat, 0.0)
                u_new = np.where(cut, np.where(same_dir & (u != 0.0), decel, 0.0), u_new)
                self._saturation_steps += cut
                self._saturation_starts += cut & ~self._saturated
            self._saturated = cut
        s_new = s + u_new * dt
        clipped = (s_new > hi) | (s_new < lo)
        if np.any(clipped):
            s_new = np.clip(s_new, lo, hi)
            u_new = np.where(clipped, (s_new - s) / dt, u_new)
        self._u_prev = u
        self._u = u_new
        self._s_ref = s_new

    # --- snapshot -------------------------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return {
            "s_ref_m": self._s_ref.copy(),
            "u_applied_m_s": self._u.copy(),
            "prev_applied_u_m_s": self._u_prev.copy(),
            "u_cmd_m_s": self._u_cmd.copy(),
            "soft_lo_m": self._soft_lo.copy(),
            "soft_hi_m": self._soft_hi.copy(),
        }

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"speed reference state lacks {missing}")
        n = self._n
        self._s_ref = _vector(arrays["s_ref_m"], n, "s_ref_m")
        self._u = _vector(arrays["u_applied_m_s"], n, "u_applied_m_s")
        self._u_prev = _vector(arrays["prev_applied_u_m_s"], n, "prev_applied_u_m_s")
        self._u_cmd = _vector(arrays["u_cmd_m_s"], n, "u_cmd_m_s")
        self._soft_lo = _vector(arrays["soft_lo_m"], n, "soft_lo_m")
        self._soft_hi = _vector(arrays["soft_hi_m"], n, "soft_hi_m")


__all__ = ["SATURATION_STOP_S", "STATE_KEYS", "SpeedReference"]
