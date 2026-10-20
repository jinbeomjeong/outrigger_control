"""L1 leg actuator: position motor driven by an integrated, rate-limited speed reference.

``00_docs/03_chrono/chrono_build_plan.md`` S2b (``chrono/actuators.L1SpeedActuator``, plan
rev. 8), R4, R15 (one-step lag), R16; ``dynamics_model.md`` 4.4, 4.6 ruling 2 step 3, 5.2
ruling 4; CLAUDE.md '구동기' (command acceleration limit, user decision 2026-10-20).

Model (per leg, applied in the actuator hook after every step, plan hook order step 3):

* command ``u_cmd`` [m/s] (controller, zero-order hold, positive = extend = pad down);
* saturation ``|u| <= v_max`` (``actuator.max_speed_m_s``);
* stroke ends ``legs.<leg>.extension_range_m`` (0 ... 0.68 m): the target speed towards an
  end ``d`` away is limited to the discrete braking speed ``sqrt((a dt / 2)^2 + 2 a d) - a dt
  / 2``, so the leg brakes with the same acceleration limit and stops exactly at the end (last
  speed step ``a dt``); a command beyond the end is cut there (ASSUMPTION: end cushion = the
  command ramp);
* **acceleration limit** (user decision 2026-10-20, replaces the plan's "motor step stop"):
  the applied speed moves towards the target by at most ``a dt`` per step, ``a = v_max /
  ramp_s`` with ``ramp_s`` = :data:`ACCEL_RAMP_S` = 0.1 s (ASSUMPTION, valve response size;
  stops are ramped too). A rigid position motor turns a speed step ``dv`` into a one-step
  inertial reaction ``m_rod dv / dt`` (107 kg, ``dv = v_max``: 24 kN at dt 1e-4 s, 242 kN at
  1e-5 s); with the ramp it is ``m_rod a`` = 24 N, independent of dt;
* integration ``s_ref <- clip(s_ref + u dt, lo, hi)``; the leg's ``ChLinkMotorLinearPosition``
  (guide PRISMATIC, link Z = body -z, R4) gets the motion function ``ChFunctionRamp``
  ``f(t) = s(t_n) + u (t - t_n)`` (start value and slope set in the hook at ``t_n``).
  ``ChLinkMotorLinearSpeed`` is not used (its internal integrator state cannot be put in an
  R16 snapshot); ``ChFunctionSetpoint`` is not used (not verified, plan S2b).

Why a ramp function and not ``ChFunctionConst(s_ref)`` (plan rev. 8; found in the S2b event
test, 2026-10-20): Chrono evaluates the motor violation ``C = s - f(t)`` and ``Ct = -f'(t)``
in the system Update at the end of a step, so a value set by the hook acts one step later
(``dynamics_model.md`` 4.6). A step that starts "not updated" (a ground bushing was created
or removed, R15) first runs a full Update and uses the hook value at once. With a constant
function whose value the hook changes, the target then jumps one step ahead and stalls on the
next step: the rod velocity goes about +v_max / -v_max for one step each, the motor force
-25 / +47 kN, and on lift-off the pad damping force (about 530 N > N_th) re-created the
bushing (chatter). The ramp is defined over time and the hook never changes its value at the
current time ``t_n`` (only the slope from then on), so the full and the normal Update see the
same target; they differ only in the slope, by at most ``a dt`` (``a dt^2`` = 2.3e-9 m of
position at dt 1e-4 s). The motor velocity comes from ``Ct`` (``u`` of the previous segment)
instead of the constraint stabilisation alone.

Timing: the hook at ``t_n`` sets the segment that ends at ``s_ref = s(t_{n+1})``; after step
``n + 1`` the motor position equals it within the slope lag above. The model therefore takes
:attr:`L1SpeedActuator.acting_s_ref_m` = ``s(t_{n+1})`` and ``acting_u_m_s`` = ``u_n`` at the
end of each step (:meth:`L1SpeedActuator.on_step_end`) for the probe, the constraint check
(V13) and the Record fields ``s_ref`` / ``u_applied`` (``TruthState.s_ref_m`` 'equal to
s_motor_m for the L1 position motor').

Snapshot (R16, part prefix :data:`PART_PREFIX`): reference, slope and ramp parameters after
the hook, the parameters Chrono had loaded at the last Update (the slope acts one step later;
rebuilt exactly like the ground bushing), the acting values and whether the next step starts
with a full Update. The command itself travels as ``Snapshot.held_command``.

Units SI; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import Params

ACCEL_RAMP_S = 0.1
"""Command acceleration limit: 0 -> v_max in this time [s]. ASSUMPTION (user decision
2026-10-20, CLAUDE.md '구동기 명령 가속 제한'; valve response size, no hydraulic data)."""

PART_PREFIX = "l1_actuator"
"""Snapshot key prefix of the actuator state (``l1_actuator.<key>``)."""

STATE_KEYS = (
    "s_ref_m",
    "u_applied_m_s",
    "ramp_start_m",
    "ramp_slope_m_s",
    "loaded_ramp_start_m",
    "loaded_ramp_slope_m_s",
    "acting_s_ref_m",
    "acting_u_m_s",
    "next_step_full_update",
    "ramp_s",
)


def _vector(value: ArrayLike, n: int, name: str) -> NDArray[np.float64]:
    out = np.array(value, dtype=float).reshape(-1)
    if out.shape != (n,):
        raise ValueError(f"{name}: expected {n} values, got shape {out.shape}")
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name}: non-finite value in {out}")
    return out


def make_motion_function(s_m: float) -> ch.ChFunctionRamp:
    """Motion function of an actuated leg: ``ChFunctionRamp(s, 0)`` (holds ``s``)."""
    return ch.ChFunctionRamp(float(s_m), 0.0)


class L1SpeedActuator:
    """Rate-limited speed reference integrated into ``ChLinkMotorLinearPosition`` targets.

    Args:
        motors: One position motor per leg (LEG_ORDER).
        functions: The ``ChFunctionRamp`` of each motor (kept alive here).
        s_init_m: Initial reference = motor target per leg [m].
        ranges_m: ``(lo, hi)`` stroke range per leg [m] (``legs.<leg>.extension_range_m``).
        max_speed_m_s: ``v_max`` (``actuator.max_speed_m_s``).
        ramp_s: 0 -> v_max time of the acceleration limit; 0 = no limit (speed steps, only
            for the inertial-spike comparison).
    """

    def __init__(
        self,
        motors: Sequence[Any],
        functions: Sequence[ch.ChFunctionRamp],
        s_init_m: ArrayLike,
        ranges_m: Sequence[Sequence[float]],
        *,
        max_speed_m_s: float,
        ramp_s: float = ACCEL_RAMP_S,
    ) -> None:
        n = len(motors)
        if n == 0 or len(functions) != n or len(ranges_m) != n:
            raise ValueError("need one motor, one function and one range per leg")
        if not (max_speed_m_s > 0.0 and math.isfinite(max_speed_m_s)):
            raise ValueError(f"max speed must be positive: {max_speed_m_s!r}")
        if not (ramp_s >= 0.0 and math.isfinite(ramp_s)):
            raise ValueError(f"ramp time must be >= 0: {ramp_s!r}")
        for fn in functions:
            if not isinstance(fn, ch.ChFunctionRamp):
                raise TypeError(f"actuated legs need ChFunctionRamp motion functions, got {fn!r}")
        self._motors = tuple(motors)
        self._functions = tuple(functions)
        lo_hi = np.array([[float(r[0]), float(r[1])] for r in ranges_m])
        if np.any(lo_hi[:, 1] <= lo_hi[:, 0]):
            raise ValueError(f"empty stroke range in {lo_hi.tolist()}")
        self._lo = lo_hi[:, 0]
        self._hi = lo_hi[:, 1]
        self._v_max = float(max_speed_m_s)
        self._ramp_s = float(ramp_s)
        s0 = _vector(s_init_m, n, "s_init_m")
        if np.any(s0 < self._lo) or np.any(s0 > self._hi):
            raise ValueError(f"initial reference {s0} outside the stroke range")
        self._u_cmd = np.zeros(n)
        self._pending_post_restore: tuple[NDArray[np.float64], NDArray[np.float64]] | None = None
        self.reset_to(s0)
        # a fresh system is "not updated" (its first step runs a full Update)
        self._next_full_update = True

    @classmethod
    def from_params(
        cls,
        params: Params,
        motors: Sequence[Any],
        functions: Sequence[ch.ChFunctionRamp],
        s_init_m: ArrayLike,
        *,
        ramp_s: float = ACCEL_RAMP_S,
    ) -> L1SpeedActuator:
        """YAML keys ``actuator.max_speed_m_s``, ``legs.<leg>.extension_range_m``."""
        return cls(
            motors,
            functions,
            s_init_m,
            [leg.extension_range_m for leg in params.legs],
            max_speed_m_s=params.actuator.max_speed_m_s,
            ramp_s=ramp_s,
        )

    # --- read-only views --------------------------------------------------------------

    @property
    def n_legs(self) -> int:
        return len(self._motors)

    @property
    def max_speed_m_s(self) -> float:
        return self._v_max

    @property
    def ramp_s(self) -> float:
        return self._ramp_s

    @property
    def accel_limit_m_s2(self) -> float:
        """``v_max / ramp_s`` (inf without a ramp)."""
        return math.inf if self._ramp_s == 0.0 else self._v_max / self._ramp_s

    @property
    def stroke_range_m(self) -> NDArray[np.float64]:
        """(n, 2) ``lo, hi`` per leg."""
        return np.column_stack([self._lo, self._hi])

    @property
    def command_m_s(self) -> NDArray[np.float64]:
        return self._u_cmd.copy()

    @property
    def s_ref_m(self) -> NDArray[np.float64]:
        """Integrated reference after the last hook: ``s(t_{n+1})``."""
        return self._s_ref.copy()

    @property
    def u_applied_m_s(self) -> NDArray[np.float64]:
        """Rate-limited speed of the current segment (limiter state)."""
        return self._u.copy()

    @property
    def acting_s_ref_m(self) -> NDArray[np.float64]:
        """Motor target at the end of the step just taken (module docstring, timing)."""
        return self._acting_s.copy()

    @property
    def acting_u_m_s(self) -> NDArray[np.float64]:
        """Applied speed of the segment that ended at :attr:`acting_s_ref_m`."""
        return self._acting_u.copy()

    # --- inputs -----------------------------------------------------------------------

    def set_command(self, leg_speed_m_s: ArrayLike) -> None:
        """Hold a new speed command (m/s per leg, any finite value; saturation is applied in
        the hook)."""
        self._u_cmd = _vector(leg_speed_m_s, self.n_legs, "leg_speed_m_s")

    # --- per-step hooks ---------------------------------------------------------------

    def on_step_start(self, full_update: bool) -> None:
        """Called by the model right before ``DoStepDynamics`` (clears the restore flag)."""
        del full_update  # same target either way (module docstring)
        self._next_full_update = False

    def on_step_end(self) -> None:
        """Called by the model right after ``DoStepDynamics``: the end-of-step Update read the
        current ramp parameters, and the motor now sits at ``s_ref``."""
        self._loaded_start = self._ramp_start.copy()
        self._loaded_slope = self._ramp_slope.copy()
        self._acting_s = self._s_ref.copy()
        self._acting_u = self._u.copy()

    def hook(self, model: Any, dt_s: float) -> None:
        """Actuator hook (``L1Model.actuator_hooks``): limit, ramp, integrate, set targets."""
        self.advance(dt_s, float(model.system.GetChTime()))

    def advance(self, dt_s: float, t_s: float) -> None:
        """One integration step of length ``dt_s`` starting at simulation time ``t_s``."""
        dt = float(dt_s)
        a = self.accel_limit_m_s2
        s = self._s_ref
        u = self._u
        target = np.clip(self._u_cmd, -self._v_max, self._v_max)
        if math.isfinite(a):
            # brake towards the stroke ends with the same acceleration limit; discrete-exact
            # cap: from speed w, stepping w, w - a dt, ... covers w^2 / (2 a) + w dt / 2, so
            # w <= -a dt / 2 + sqrt((a dt / 2)^2 + 2 a d) stops exactly at the end (the plain
            # sqrt(2 a d) drifts by sqrt(n) a dt over n braking steps and ends with a jump)
            step = a * dt
            half = 0.5 * step
            up = np.sqrt(half * half + 2.0 * a * np.maximum(self._hi - s, 0.0)) - half
            down = np.sqrt(half * half + 2.0 * a * np.maximum(s - self._lo, 0.0)) - half
            target = np.minimum(np.maximum(target, -down), up)
            u_new = u + np.clip(target - u, -step, step)
        else:
            target = np.where((s >= self._hi) & (target > 0.0), 0.0, target)
            target = np.where((s <= self._lo) & (target < 0.0), 0.0, target)
            u_new = target
        s_new = s + u_new * dt
        clipped = (s_new > self._hi) | (s_new < self._lo)
        if np.any(clipped):
            s_new = np.clip(s_new, self._lo, self._hi)
            u_new = np.where(clipped, (s_new - s) / dt, u_new)
        # f(t) = s(t_n) + u_new (t - t_n) = start + slope t
        self._ramp_start = s - u_new * float(t_s)
        self._ramp_slope = u_new
        self._s_ref = s_new
        self._u = u_new
        self._apply(self._ramp_start, self._ramp_slope)

    def _apply(self, start: NDArray[np.float64], slope: NDArray[np.float64]) -> None:
        for fn, y0, k in zip(self._functions, start, slope, strict=True):
            fn.SetStartVal(float(y0))
            fn.SetAngularCoeff(float(k))

    # --- snapshot (R16) -----------------------------------------------------------------

    def state_arrays(self, *, next_step_full_update: bool | None = None) -> dict[str, NDArray]:
        """Actuator state for a snapshot.

        Args:
            next_step_full_update: Whether the next step starts with a full Update (the model
                passes ``not system.IsUpdated()``); None = the actuator's own flag.
        """
        full = self._next_full_update if next_step_full_update is None else next_step_full_update
        return {
            "s_ref_m": self._s_ref.copy(),
            "u_applied_m_s": self._u.copy(),
            "ramp_start_m": self._ramp_start.copy(),
            "ramp_slope_m_s": self._ramp_slope.copy(),
            "loaded_ramp_start_m": self._loaded_start.copy(),
            "loaded_ramp_slope_m_s": self._loaded_slope.copy(),
            "acting_s_ref_m": self._acting_s.copy(),
            "acting_u_m_s": self._acting_u.copy(),
            "next_step_full_update": np.array([bool(full)]),
            "ramp_s": np.array([self._ramp_s]),
        }

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """Set the state of :meth:`state_arrays`; the motor functions get the loaded
        parameters (the restore runs the system Update, then :meth:`finish_restore`).

        Raises:
            ValueError: Missing keys, wrong leg count or another ramp time.
        """
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"actuator state lacks {missing}")
        ramp = float(np.asarray(arrays["ramp_s"]).reshape(-1)[0])
        if ramp != self._ramp_s:
            raise ValueError(
                f"snapshot actuator ramp {ramp} s differs from this model {self._ramp_s} s"
            )
        n = self.n_legs
        self._s_ref = _vector(arrays["s_ref_m"], n, "s_ref_m")
        self._u = _vector(arrays["u_applied_m_s"], n, "u_applied_m_s")
        self._ramp_start = _vector(arrays["ramp_start_m"], n, "ramp_start_m")
        self._ramp_slope = _vector(arrays["ramp_slope_m_s"], n, "ramp_slope_m_s")
        self._loaded_start = _vector(arrays["loaded_ramp_start_m"], n, "loaded_ramp_start_m")
        self._loaded_slope = _vector(arrays["loaded_ramp_slope_m_s"], n, "loaded_ramp_slope_m_s")
        self._acting_s = _vector(arrays["acting_s_ref_m"], n, "acting_s_ref_m")
        self._acting_u = _vector(arrays["acting_u_m_s"], n, "acting_u_m_s")
        full = bool(np.asarray(arrays["next_step_full_update"]).reshape(-1)[0])
        self._next_full_update = full
        if full:
            # the uninterrupted run starts the next step with a full Update of the post-hook
            # parameters: use them now, nothing to do afterwards
            self._apply(self._ramp_start, self._ramp_slope)
            self._pending_post_restore = None
        else:
            self._apply(self._loaded_start, self._loaded_slope)
            self._pending_post_restore = (self._ramp_start.copy(), self._ramp_slope.copy())

    def finish_restore(self) -> None:
        """Set the post-hook ramp parameters after the restore's system Update."""
        if self._pending_post_restore is not None:
            self._apply(*self._pending_post_restore)
            self._pending_post_restore = None

    def reset_to(self, s_m: ArrayLike) -> None:
        """Hold still at ``s_m`` (constant functions, zero speed, all histories equal); used
        at construction and when restoring a snapshot without actuator state (S1 / S2a)."""
        s = _vector(s_m, self.n_legs, "s_m")
        zero = np.zeros(self.n_legs)
        self._s_ref = s.copy()
        self._u = zero.copy()
        self._ramp_start = s.copy()
        self._ramp_slope = zero.copy()
        self._loaded_start = s.copy()
        self._loaded_slope = zero.copy()
        self._acting_s = s.copy()
        self._acting_u = zero.copy()
        self._next_full_update = False
        self._pending_post_restore = None
        self._apply(self._ramp_start, self._ramp_slope)
