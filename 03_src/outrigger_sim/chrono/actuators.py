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
  speed change ``<= 9/8 a dt``: fractional final step + end clip); a command beyond the end is
  cut there (ASSUMPTION: end cushion = the command ramp);
* **acceleration limit** (user decision 2026-10-20, replaces the plan's "motor step stop"):
  the applied speed moves towards the target by at most ``a dt`` per step, ``a = v_max /
  ramp_s`` with ``ramp_s`` = YAML ``actuator.command_ramp_s`` = 0.1 s (ASSUMPTION, valve
  response size; stops are ramped too; a code constant until the YAML regeneration of
  2026-10-21). A rigid position motor turns a speed step ``dv`` into a one-step
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
with a full Update. The command itself travels as ``Snapshot.held_command``. Optional keys
(:data:`OPTIONAL_STATE_KEYS`, S3): the soft travel limits; snapshots without them restore with
the stroke range.

**Hook guard** (``dynamics_model.md`` 5.6 ruling 1, condition 1; S3): a ramp function keeps
moving with its last slope when the hook is not called (a constant function would stop), so
the actuator hook must run after every step. :meth:`L1SpeedActuator.on_step_start` (called by
``L1Model.step`` before ``DoStepDynamics``) raises :class:`ActuatorHookMissedError` when any
slope is non-zero and the last hook did not run at the current system time with the step's
``dt`` (a step without the hook, a direct ``DoStepDynamics``, a removed hook, or a time-step
change that bypassed :meth:`L1SpeedActuator.retime`). Holding still (every slope 0) is always
allowed. :meth:`L1SpeedActuator.freeze` sets every slope to 0 at the current target for code
that must step without the hook (test paths; it is a speed step, not a ramped stop).

**Soft travel limits** (S3 lift and leg-step scenarios; ``dynamics_model.md`` 5.6 ruling 3
condition 1): :meth:`L1SpeedActuator.set_soft_limits` narrows the travel range inside the
stroke range. The braking cap uses it like a stroke end, so a leg commanded towards a soft
limit brakes with the acceleration limit and stops exactly on it (S3 lift: braking starts at
``e_op / v_max`` after the start command, ``dynamics_model.md`` 5 V4).

**Time-step change** (S3 transition windows): call :meth:`L1SpeedActuator.retime` (``L1Model.
set_dt`` does) between two steps. The segment the last hook set keeps its ramp function (it is
defined over time); only the integrated end value ``s_ref`` is recomputed for the new step
length. Change ``dt`` while the applied speed is constant (no ramp or braking in progress):
otherwise one speed change may exceed ``a dt_new`` by up to ``a (dt_old - dt_new)``.

**Force saturation (210 bar, S6, law C)** (plan S6 'cad: 힘 포화'; CLAUDE.md '구동기' and
'압력 한계'; ``dynamics_model.md`` rev. 23 5.10, user decision 2026-10-21 U1 = (a) law C; YAML
``legs.<leg>.cylinder.max_force_extend_N`` = 210 bar x head area, ``.max_force_retract_N`` = 210
bar x annulus area, per leg (REXOME35; :func:`leg_force_limits_N`; without the per-leg keys the
common ``actuator.max_force_*_N``, 218.1 / 18.6 kN)), judged **every physics step** in the
actuator hook:

* judged force ``F_dec = F_cyl - m_rod (u_act,n - u_act,n-1) / dt``: the cylinder force of the
  step just taken (``GetMotorForce()``, + = pushes the pad down = extend, R4) minus the rod
  inertia of the rigid motor's own speed change (``u_act,n`` = applied speed of that step =
  Record ``u_applied``, ``u_act,n-1`` the one before; ``m_rod`` = ``legs.<leg>.moving_part.
  mass_kg``), so the reading's inertial pulse does not trigger or release the limit;
* saturated when ``F_dec >= F_ext`` and the new speed ``u > 0``, or ``F_dec <= -F_ret`` and
  ``u < 0``. Then, if the leg is moving in that direction, it **decelerates** with
  ``a_sat = v_max / t_sat``: ``u_new = sign(u) max(|u| - a_sat dt, 0)``, ``t_sat`` =
  :data:`SATURATION_STOP_S` = 2 ms (ASSUMPTION, YAML ``actuator.saturation_stop_s`` at the next
  regeneration); from rest a start in the saturated direction stays 0. Otherwise the command
  ramp applies unchanged. A rigid one-step cut (S6 stage 1) put ``m_rod v / dt`` (12 kN at
  2e-4 s, 242 kN at 1e-5 s) into the reading; with ``t_sat`` the inertia is ``m_rod v / t_sat``
  (1.2 kN) at any dt. :meth:`L1SpeedActuator.check_saturation_stop` warns when ``t_sat`` is
  outside ``10 dt <= t_sat <= 2 c_n / k_n``;
* the command is kept, so the leg resumes with the acceleration limit as soon as ``F_dec``
  drops below the limit (pressure-compensated valve: the leg creeps until the static force
  equals the limit, about ``c_n v / k_n`` = 0.03 mm on the L1 pad); a command towards the
  other direction is followed at once.

State: ``u_act,n-1`` is snapshot key ``prev_applied_u_m_s`` (R16 optional key; absent = the
current applied speed). Diagnostics :attr:`L1SpeedActuator.saturated`,
:attr:`~L1SpeedActuator.saturation_step_count`, :attr:`~L1SpeedActuator.saturation_start_count`
are not R16 state. Runs that never reach the limits are bit-identical to the model without the
rule. ``from_params`` enables it by default; ``force_saturation=False`` or the constructor
without limits reproduces the S2b-S5 actuator.

**Valve lag and amplifier ramp (R8, ``s6_control_spec.md`` rev. 31 148 R-2 / R-3)**
(:meth:`L1SpeedActuator.configure_valve`, default off = everything above unchanged): the 10 Hz
valve command passes ``amplifier ramp -> spool first-order lag -> leg speed``:

* amplifier ramp ``amp_ramp`` (ASSUMPTION, Q-M6 / U-R8-12 open): ``"none"``; ``"full_scale"``
  = ``|du/dt| <= v_max / amp_ramp_s`` (0 -> 100 % in ``amp_ramp_s``); ``"per_step"`` = every
  command change is ramped in ``amp_ramp_s`` whatever its size (rate ``|Delta u| /
  amp_ramp_s``, set when the command changes). Advanced once per step; its value at the step
  end is the lag input of that step (lead of at most ``dt / 2`` against the exact ramp);
* spool lag ``du_a/dt = (u_r - u_a) / tau_v`` per leg, integrated **exactly** over each step
  for the constant input ``u_r``: ``u_a <- u_r + (u_a - u_r) e^(-dt/tau)``; the leg moves with
  the **step mean** ``u_r + (u_a - u_r) tau / dt (1 - e^(-dt/tau))`` (the ramp function slope
  of the step, so ``s_ref`` is the exact integral). ``tau_v = 0`` = no lag;
* the command acceleration limit (``command_ramp_s``) is **off** while the valve model is on
  (they model the same thing twice); the stroke-end braking cap stays, with the deceleration
  ``v_max / command_ramp_s`` as an end cushion (ASSUMPTION, as before) and no step limit;
* force saturation (law C) acts on the resulting leg speed as before; the spool state keeps
  following its command (pressure-compensated valve, the leg is blocked, not the spool);
* state (``u_a``, ramp output / target / rate) survives ``dt`` changes (:meth:`retime`
  re-integrates the pending step from its start state) and snapshots (optional keys
  :data:`VALVE_STATE_KEYS`, written only with the valve model on; absent at a run start = 0).

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

OPTIONAL_STATE_KEYS = ("soft_lo_m", "soft_hi_m", "prev_applied_u_m_s")
"""Snapshot keys added in S3 (soft travel limits); absent = the stroke range."""

VALVE_STATE_KEYS = ("valve_u_m_s", "amp_u_m_s", "amp_target_m_s", "amp_rate_m_s2")
"""Snapshot keys of the R8 valve model (written only when it is on; absent = zero state)."""

AMP_RAMP_MODES = ("none", "full_scale", "per_step")
"""``configure_valve(amp_ramp=...)`` choices (module docstring)."""

SATURATION_STOP_S = 2.0e-3
"""ASSUMPTION (dyn rev. 23 law C, user decision 2026-10-21): stop time of the saturation
deceleration, ``a_sat = v_max / t_sat``; YAML ``actuator.saturation_stop_s`` at the next
regeneration."""

HOOK_TIME_REL_TOL = 1.0e-12
"""Relative tolerance of the hook-time and hook-dt match in the guard (same float path)."""


class ActuatorHookMissedError(RuntimeError):
    """A step would run with a moving ramp segment that the actuator hook did not set for it
    (module docstring, hook guard)."""


def _vector(value: ArrayLike, n: int, name: str) -> NDArray[np.float64]:
    out = np.array(value, dtype=float).reshape(-1)
    if out.shape != (n,):
        raise ValueError(f"{name}: expected {n} values, got shape {out.shape}")
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name}: non-finite value in {out}")
    return out


def leg_force_limits_N(params: Params) -> tuple[list[float], list[float]]:
    """Per-leg (LEG_ORDER) force saturation limits ``(extend, retract)`` [N]:
    ``legs.<leg>.cylinder.max_force_{extend,retract}_N`` (REXOME35, 210 bar x head / annulus
    area) when every leg has both keys, else (YAML from before the bundle of 2026-10-25) the
    common ``actuator.max_force_*_N``."""
    from outrigger_sim.params import LEG_ORDER, ParamsError

    try:
        ext = [float(params.get(f"legs.{leg}.cylinder.max_force_extend_N")) for leg in LEG_ORDER]
        ret = [float(params.get(f"legs.{leg}.cylinder.max_force_retract_N")) for leg in LEG_ORDER]
    except ParamsError:
        n = len(LEG_ORDER)
        ext = [float(params.get("actuator.max_force_extend_N"))] * n
        ret = [float(params.get("actuator.max_force_retract_N"))] * n
    return ext, ret


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
        ramp_s: 0 -> v_max time of the acceleration limit (YAML ``actuator.command_ramp_s``
            via :meth:`from_params`); 0 = no limit (speed steps, only for the inertial-spike
            comparison).
        max_force_extend_N, max_force_retract_N: Force saturation limits (module docstring,
            both positive); None (default) = no force saturation (S2b-S5 behaviour).
            :meth:`from_params` takes the YAML values.
        rod_mass_kg: Moving-part mass per leg for the judged force ``F_dec`` (None = 0, no
            inertia correction).
        saturation_stop_s: ``t_sat`` of the saturation deceleration (> 0).
        saturation_stop_max_s: Upper bound ``2 c_n / k_n`` per leg for the warning of
            :meth:`check_saturation_stop` (None = no upper check).
    """

    def __init__(
        self,
        motors: Sequence[Any],
        functions: Sequence[ch.ChFunctionRamp],
        s_init_m: ArrayLike,
        ranges_m: Sequence[Sequence[float]],
        *,
        max_speed_m_s: float,
        ramp_s: float,
        max_force_extend_N: float | None = None,
        max_force_retract_N: float | None = None,
        rod_mass_kg: ArrayLike | None = None,
        saturation_stop_s: float = SATURATION_STOP_S,
        saturation_stop_max_s: ArrayLike | None = None,
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
        self._soft_lo = self._lo.copy()
        self._soft_hi = self._hi.copy()
        self._hook_t: float | None = None
        self._hook_dt: float | None = None
        if (max_force_extend_N is None) != (max_force_retract_N is None):
            raise ValueError("give both force limits or none")
        self._f_ext: float | NDArray[np.float64] | None = None
        self._f_ret: float | NDArray[np.float64] | None = None
        if max_force_extend_N is not None and max_force_retract_N is not None:
            # one value or one per leg (REXOME35: legs.<leg>.cylinder.*); kept a scalar when
            # every leg has the same value (bit-identical to the common-limit actuator)
            limits = []
            for value, name in ((max_force_extend_N, "extend"), (max_force_retract_N, "retract")):
                arr = np.array(value, dtype=float).reshape(-1)
                if arr.size not in (1, n):
                    raise ValueError(f"{name} force limit: expected 1 or {n} values, got {arr}")
                if not (np.all(arr > 0.0) and np.all(np.isfinite(arr))):
                    raise ValueError(f"force limits must be positive: {arr.tolist()!r}")
                limits.append(float(arr[0]) if bool(np.all(arr == arr[0])) else arr)
            self._f_ext, self._f_ret = limits
        self._saturated = np.zeros(n, dtype=bool)
        self._saturation_steps = np.zeros(n, dtype=np.int64)
        self._saturation_starts = np.zeros(n, dtype=np.int64)
        self._last_force = np.full(n, np.nan)
        self._last_judged = np.full(n, np.nan)
        self._m_rod = np.zeros(n) if rod_mass_kg is None else _vector(rod_mass_kg, n, "rod_mass_kg")
        if not (saturation_stop_s > 0.0 and math.isfinite(saturation_stop_s)):
            raise ValueError(f"saturation_stop_s must be positive: {saturation_stop_s!r}")
        self._t_sat = float(saturation_stop_s)
        self._t_sat_max = (
            None if saturation_stop_max_s is None
            else _vector(saturation_stop_max_s, n, "saturation_stop_max_s")
        )
        self._t_sat_checked_dt: float | None = None
        # R8 valve model (configure_valve; off = the actuator above, bit for bit)
        self._valve_on = False
        self._valve_tau_s = 0.0
        self._amp_mode = "none"
        self._amp_ramp_s = 0.0
        self._zero_valve_state()
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
        ramp_s: float | None = None,
        force_saturation: bool = True,
    ) -> L1SpeedActuator:
        """YAML keys ``actuator.max_speed_m_s``, ``actuator.command_ramp_s`` (used when
        ``ramp_s`` is None), ``legs.<leg>.extension_range_m`` and, with ``force_saturation``
        (default, S6), the per-leg force limits of :func:`leg_force_limits_N`."""
        f_ext = f_ret = None
        if force_saturation:
            f_ext, f_ret = leg_force_limits_N(params)
        kn = params.get("contact.rigid_floor.L1.kn_per_pad_N_m")
        cn = params.get("contact.rigid_floor.L1.cn_per_pad_N_s_m")
        return cls(
            motors,
            functions,
            s_init_m,
            [leg.extension_range_m for leg in params.legs],
            max_speed_m_s=params.actuator.max_speed_m_s,
            ramp_s=params.actuator.command_ramp_s if ramp_s is None else ramp_s,
            max_force_extend_N=f_ext,
            max_force_retract_N=f_ret,
            rod_mass_kg=[leg.moving_part.mass_kg for leg in params.legs],
            saturation_stop_max_s=[
                2.0 * float(cn[leg.name]) / float(kn[leg.name]) for leg in params.legs
            ],
        )

    # --- R8 valve model (module docstring) ------------------------------------------------

    def configure_valve(
        self, *, tau_s: float, amp_ramp: str = "none", amp_ramp_s: float = 0.1
    ) -> None:
        """Turn the valve model on (module docstring, R-2 / R-3); call before the run.

        Args:
            tau_s: Spool first-order lag ``tau_v`` [s] (>= 0; 0 = no lag).
            amp_ramp: ``"none"`` / ``"full_scale"`` / ``"per_step"``.
            amp_ramp_s: Amplifier ramp time [s] (> 0 when a ramp is used).

        The command acceleration limit (``ramp_s``) is switched off with it; the valve state
        starts at zero.
        """
        tau = float(tau_s)
        if not (math.isfinite(tau) and tau >= 0.0):
            raise ValueError(f"tau_s must be >= 0: {tau_s!r}")
        if amp_ramp not in AMP_RAMP_MODES:
            raise ValueError(f"amp_ramp must be one of {AMP_RAMP_MODES}: {amp_ramp!r}")
        ramp = float(amp_ramp_s)
        if amp_ramp != "none" and not (math.isfinite(ramp) and ramp > 0.0):
            raise ValueError(f"amp_ramp_s must be > 0: {amp_ramp_s!r}")
        self._valve_on = True
        self._valve_tau_s = tau
        self._amp_mode = amp_ramp
        self._amp_ramp_s = ramp if amp_ramp != "none" else 0.0
        self._zero_valve_state()

    @property
    def valve_on(self) -> bool:
        return self._valve_on

    @property
    def command_ramp_active(self) -> bool:
        """Whether the command acceleration limit acts (off with the valve model)."""
        return not self._valve_on and self._ramp_s > 0.0

    @property
    def valve_state_m_s(self) -> NDArray[np.float64]:
        """Spool state ``u_a`` per leg after the last hook (end of the next step)."""
        return self._valve_u.copy()

    @property
    def amp_output_m_s(self) -> NDArray[np.float64]:
        """Amplifier ramp output per leg after the last hook."""
        return self._amp_u.copy()

    def valve_meta(self) -> dict[str, Any]:
        """JSON-ready valve settings (run meta)."""
        return {
            "valve_model_on": self._valve_on,
            "tau_v_s": self._valve_tau_s if self._valve_on else None,
            "amp_ramp": self._amp_mode if self._valve_on else None,
            "amp_ramp_s": self._amp_ramp_s if self._valve_on else None,
            "command_ramp_active": self.command_ramp_active,
            "end_cushion_decel_m_s2": (self._v_max / self._ramp_s
                                       if self._valve_on and self._ramp_s > 0.0 else None),
            "integration": "exact exponential per step, leg speed = step mean (s6 spec 148 R-2)",
        }

    def _zero_valve_state(self) -> None:
        n = self.n_legs
        self._valve_u = np.zeros(n)
        self._amp_u = np.zeros(n)
        self._amp_target = np.zeros(n)
        self._amp_rate = np.zeros(n)
        self._valve_start: tuple[NDArray[np.float64], ...] | None = None

    def _valve_step(
        self, dt: float, start: tuple[NDArray[np.float64], ...]
    ) -> tuple[NDArray[np.float64], tuple[NDArray[np.float64], ...]]:
        """One step of amplifier ramp + spool lag from ``start`` = (u_a, amp_u, amp_target,
        amp_rate): returns (step-mean speed, end state)."""
        va, amp_u, amp_target, amp_rate = (a.copy() for a in start)
        u_c = np.clip(self._u_cmd, -self._v_max, self._v_max)
        if self._amp_mode == "none":
            amp_u = u_c.copy()
            amp_target = u_c.copy()
        elif self._amp_mode == "full_scale":
            step = self._v_max / self._amp_ramp_s * dt
            amp_u = amp_u + np.clip(u_c - amp_u, -step, step)
            amp_target = u_c.copy()
        else:  # per_step: a changed command restarts a ramp of fixed duration
            changed = u_c != amp_target
            if np.any(changed):
                amp_rate = np.where(changed, np.abs(u_c - amp_u) / self._amp_ramp_s, amp_rate)
                amp_target = np.where(changed, u_c, amp_target)
            step = amp_rate * dt
            amp_u = amp_u + np.clip(amp_target - amp_u, -step, step)
        tau = self._valve_tau_s
        if tau > 0.0:
            decay = math.exp(-dt / tau)
            mean_factor = tau / dt * -math.expm1(-dt / tau)
            gap = va - amp_u
            u_mean = amp_u + gap * mean_factor
            va = amp_u + gap * decay
        else:
            u_mean = amp_u.copy()
            va = amp_u.copy()
        return u_mean, (va, amp_u, amp_target, amp_rate)

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
    def soft_limits_m(self) -> NDArray[np.float64]:
        """(n, 2) soft travel limits ``lo, hi`` per leg (default: the stroke range)."""
        return np.column_stack([self._soft_lo, self._soft_hi])

    @property
    def force_limits_N(self) -> tuple[float | list[float], float | list[float]] | None:
        """``(max_force_extend_N, max_force_retract_N)`` (a float, or a per-leg list when the
        legs differ) or None without force saturation."""
        if self._f_ext is None or self._f_ret is None:
            return None

        def plain(v: float | NDArray[np.float64]) -> float | list[float]:
            return v if isinstance(v, float) else [float(x) for x in v]

        return (plain(self._f_ext), plain(self._f_ret))

    @property
    def saturated(self) -> NDArray[np.bool_]:
        """Legs whose speed the last hook cut by the force saturation (diagnostic)."""
        return self._saturated.copy()

    @property
    def saturation_step_count(self) -> NDArray[np.int64]:
        """Hooks per leg in which the force saturation cut the speed (diagnostic, not R16)."""
        return self._saturation_steps.copy()

    @property
    def saturation_start_count(self) -> NDArray[np.int64]:
        """Per leg: hooks in which the saturation began (not saturated in the hook before)."""
        return self._saturation_starts.copy()

    @property
    def saturation_stop_s(self) -> float:
        return self._t_sat

    @property
    def last_judged_force_N(self) -> NDArray[np.float64]:
        """``F_dec`` of the last hook (module docstring); NaN before the first hook."""
        return self._last_judged.copy()

    def check_saturation_stop(self, dt_s: float) -> bool:
        """Warn (``RuntimeWarning``) when ``t_sat`` is outside ``10 dt <= t_sat <= 2 c_n /
        k_n``; returns whether it is inside."""
        import warnings

        ok = self._t_sat >= 10.0 * float(dt_s) * (1.0 - 1e-9)
        if self._t_sat_max is not None:
            ok = ok and bool(np.all(self._t_sat <= self._t_sat_max * (1.0 + 1e-9)))
        if not ok:
            warnings.warn(
                f"saturation stop time {self._t_sat} s outside 10 dt = {10.0 * dt_s} s .. "
                f"2 c_n / k_n = {None if self._t_sat_max is None else self._t_sat_max.tolist()} s",
                RuntimeWarning,
                stacklevel=2,
            )
        return ok

    @property
    def last_cylinder_force_N(self) -> NDArray[np.float64]:
        """Cylinder forces the last hook judged (NaN before the first hook or without
        saturation)."""
        return self._last_force.copy()

    def reset_saturation_counters(self) -> None:
        """Zero :attr:`saturation_step_count` (start of a scenario window)."""
        self._saturation_steps[:] = 0

    @property
    def is_moving_segment(self) -> bool:
        """Whether any motor function has a non-zero slope (stepping needs the hook)."""
        return bool(np.any(self._ramp_slope != 0.0))

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

    def set_soft_limits(
        self, lo_m: ArrayLike | None = None, hi_m: ArrayLike | None = None
    ) -> None:
        """Narrow the travel range (module docstring, soft travel limits).

        Args:
            lo_m, hi_m: Per-leg limits [m]; None keeps the current value. Each must lie in the
                stroke range, and the current reference ``s_ref`` must lie between them (a
                limit is approached by braking, never by a jump).

        Raises:
            ValueError: A limit outside the stroke range, ``lo > hi``, or ``s_ref`` outside.
        """
        n = self.n_legs
        lo = self._soft_lo if lo_m is None else _vector(lo_m, n, "lo_m")
        hi = self._soft_hi if hi_m is None else _vector(hi_m, n, "hi_m")
        if np.any(lo < self._lo) or np.any(hi > self._hi) or np.any(lo > hi):
            raise ValueError(
                f"soft limits {lo.tolist()} .. {hi.tolist()} not inside the stroke range "
                f"{self._lo.tolist()} .. {self._hi.tolist()}"
            )
        if np.any(self._s_ref < lo) or np.any(self._s_ref > hi):
            raise ValueError(f"reference {self._s_ref.tolist()} outside the new soft limits")
        self._soft_lo = lo.copy()
        self._soft_hi = hi.copy()

    def clear_soft_limits(self) -> None:
        """Soft limits back to the stroke range."""
        self._soft_lo = self._lo.copy()
        self._soft_hi = self._hi.copy()

    # --- per-step hooks ---------------------------------------------------------------

    def on_step_start(
        self, full_update: bool, t_s: float | None = None, dt_s: float | None = None
    ) -> None:
        """Called by the model right before ``DoStepDynamics`` (clears the restore flag).

        With ``t_s`` and ``dt_s`` (the step's start time and length) the hook guard runs
        (module docstring).

        Raises:
            ActuatorHookMissedError: A motor function is moving and the last hook was not
                run at ``t_s`` for a step of ``dt_s``.
        """
        del full_update  # same target either way (module docstring)
        if t_s is not None and dt_s is not None:
            self.check_hook(float(t_s), float(dt_s))
        self._next_full_update = False

    def check_hook(self, t_s: float, dt_s: float) -> None:
        """Hook guard (module docstring).

        Raises:
            ActuatorHookMissedError: see :meth:`on_step_start`.
        """
        if not self.is_moving_segment:
            return
        ht, hdt = self._hook_t, self._hook_dt
        scale = max(abs(t_s), 1.0)
        if ht is None or hdt is None or abs(ht - t_s) > HOOK_TIME_REL_TOL * scale:
            raise ActuatorHookMissedError(
                f"moving ramp segment (slopes {self._ramp_slope.tolist()} m/s) at t = {t_s!r} s, "
                f"but the actuator hook last ran at t = {ht!r} s: the hook must run after every "
                "step (or call freeze() before stepping without it)"
            )
        if abs(hdt - dt_s) > HOOK_TIME_REL_TOL * max(abs(dt_s), 1e-300):
            raise ActuatorHookMissedError(
                f"the hook integrated a step of {hdt!r} s but the step is {dt_s!r} s: change the "
                "time step with L1Model.set_dt / L1SpeedActuator.retime"
            )

    def mark_hooked(self, t_s: float, dt_s: float) -> None:
        """Declare the current ramp parameters as set by a hook at ``t_s`` for a step of
        ``dt_s`` (after a snapshot restore, whose state was captured after the hook)."""
        self._hook_t = float(t_s)
        self._hook_dt = float(dt_s)

    def retime(self, t_s: float, dt_s: float) -> None:
        """Re-integrate the pending segment for a new step length (module docstring).

        Args:
            t_s: Current system time = start of the next step (the last hook's time).
            dt_s: Length of the next step [s].
        """
        dt = float(dt_s)
        if not (dt > 0.0 and math.isfinite(dt)):
            raise ValueError(f"dt must be positive: {dt_s!r}")
        t = float(t_s)
        if self._valve_on and self._valve_start is not None:
            # the valve state of the pending step was integrated for the old dt: redo it from
            # the step's start state (the ramp slope of that step is kept, docstring above)
            _, end_state = self._valve_step(dt, self._valve_start)
            self._valve_u, self._amp_u, self._amp_target, self._amp_rate = end_state
        s_now = self._ramp_start + self._ramp_slope * t
        u = self._ramp_slope
        s_new = s_now + u * dt
        clipped = (s_new > self._soft_hi) | (s_new < self._soft_lo)
        if np.any(clipped):
            s_new = np.clip(s_new, self._soft_lo, self._soft_hi)
            u = np.where(clipped, (s_new - s_now) / dt, u)
            self._ramp_start = s_now - u * t
            self._ramp_slope = u
            self._u = u.copy()
            self._apply(self._ramp_start, self._ramp_slope)
        self._s_ref = s_new
        self._hook_t = t
        self._hook_dt = dt

    def retime_if_needed(self, t_s: float, dt_s: float, tol_m: float = 1.0e-12) -> bool:
        """:meth:`retime` only when the pending ``s_ref`` was integrated for another step
        length (more than ``tol_m`` away from ``s(t) + u dt``); returns whether it did. A
        restore into a model with the snapshot's own ``dt`` stays bit-identical."""
        s_now = self._ramp_start + self._ramp_slope * float(t_s)
        expected = s_now + self._ramp_slope * float(dt_s)
        if float(np.max(np.abs(expected - self._s_ref))) <= tol_m:
            self._hook_t = float(t_s)
            self._hook_dt = float(dt_s)
            return False
        self.retime(t_s, dt_s)
        return True

    def freeze(self, t_s: float) -> None:
        """Stop every leg at its target value at ``t_s`` (every slope 0, applied speed 0,
        command 0), so that stepping without the hook cannot move the motors. A speed step:
        for test paths only. Like any hook input it acts from the step after next (one-step
        lag, module docstring)."""
        t = float(t_s)
        s_now = self._ramp_start + self._ramp_slope * t
        zero = np.zeros(self.n_legs)
        self._u_cmd = zero.copy()
        self._s_ref = s_now.copy()
        self._u = zero.copy()
        self._ramp_start = s_now.copy()
        self._ramp_slope = zero.copy()
        self._apply(self._ramp_start, self._ramp_slope)

    def on_step_end(self) -> None:
        """Called by the model right after ``DoStepDynamics``: the end-of-step Update read the
        current ramp parameters, and the motor now sits at ``s_ref``."""
        self._loaded_start = self._ramp_start.copy()
        self._loaded_slope = self._ramp_slope.copy()
        self._acting_s = self._s_ref.copy()
        self._prev_acting_u = self._acting_u
        self._acting_u = self._u.copy()

    def hook(self, model: Any, dt_s: float) -> None:
        """Actuator hook (``L1Model.actuator_hooks``): limit, ramp, integrate, set targets.

        ``dt_s`` must be the length of the **next** step (``L1Model`` passes its ``dt_s``,
        which ``L1Model.set_dt`` changes only between steps, together with :meth:`retime`).
        With force limits, the cylinder forces of the step just taken are read from the
        motors (module docstring, force saturation).
        """
        forces = None
        if self._f_ext is not None:
            forces = np.array([m.GetMotorForce() for m in self._motors], dtype=float)
        self.advance(dt_s, float(model.system.GetChTime()), cylinder_force_N=forces)

    def advance(
        self, dt_s: float, t_s: float, *, cylinder_force_N: ArrayLike | None = None
    ) -> None:
        """One integration step of length ``dt_s`` starting at simulation time ``t_s``.

        Args:
            cylinder_force_N: Cylinder force per leg of the step just taken (+ = extend);
                judged against the force limits when the actuator has them (module
                docstring). None = no force saturation in this step.
        """
        dt = float(dt_s)
        a = self.accel_limit_m_s2
        s = self._s_ref
        u = self._u
        lo, hi = self._soft_lo, self._soft_hi
        target = np.clip(self._u_cmd, -self._v_max, self._v_max)
        if self._valve_on:
            # R8 valve model: amplifier ramp + exact spool lag, step-mean speed; the
            # acceleration limit is off, the stroke-end braking cap stays (module docstring)
            start = (self._valve_u, self._amp_u, self._amp_target, self._amp_rate)
            target, end_state = self._valve_step(dt, start)
            self._valve_start = start
            self._valve_u, self._amp_u, self._amp_target, self._amp_rate = end_state
            if math.isfinite(a):
                half = 0.5 * a * dt
                up = np.sqrt(half * half + 2.0 * a * np.maximum(hi - s, 0.0)) - half
                down = np.sqrt(half * half + 2.0 * a * np.maximum(s - lo, 0.0)) - half
                u_new = np.minimum(np.maximum(target, -down), up)
            else:
                u_new = np.where((s >= hi) & (target > 0.0), 0.0, target)
                u_new = np.where((s <= lo) & (u_new < 0.0), 0.0, u_new)
        elif math.isfinite(a):
            # brake towards the stroke ends with the same acceleration limit; discrete-exact
            # cap: from speed w, stepping w, w - a dt, ... covers w^2 / (2 a) + w dt / 2, so
            # w <= -a dt / 2 + sqrt((a dt / 2)^2 + 2 a d) stops exactly at the end (the plain
            # sqrt(2 a d) drifts by sqrt(n) a dt over n braking steps and ends with a jump)
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
            f = _vector(cylinder_force_N, self.n_legs, "cylinder_force_N")
            if self._t_sat_checked_dt != dt:
                self.check_saturation_stop(dt)
                self._t_sat_checked_dt = dt
            # judged force without the rod inertia of the motor's own speed change (law C)
            f_dec = f - self._m_rod * (self._acting_u - self._prev_acting_u) / dt
            cut = ((f_dec >= self._f_ext) & (u_new > 0.0)) | (
                (f_dec <= -self._f_ret) & (u_new < 0.0)
            )
            self._last_force = f
            self._last_judged = f_dec
            if np.any(cut):
                # decelerate in the saturated direction with a_sat = v_max / t_sat; from rest
                # (or moving the other way) the start is suppressed; legs that are not cut
                # keep their values bit for bit (module docstring)
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
        # f(t) = s(t_n) + u_new (t - t_n) = start + slope t
        self._ramp_start = s - u_new * float(t_s)
        self._ramp_slope = u_new
        self._s_ref = s_new
        self._u = u_new
        self._hook_t = float(t_s)
        self._hook_dt = dt
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
        valve = {}
        if self._valve_on:
            valve = {"valve_u_m_s": self._valve_u.copy(), "amp_u_m_s": self._amp_u.copy(),
                     "amp_target_m_s": self._amp_target.copy(),
                     "amp_rate_m_s2": self._amp_rate.copy()}
        return valve | {
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
            "soft_lo_m": self._soft_lo.copy(),
            "soft_hi_m": self._soft_hi.copy(),
            "prev_applied_u_m_s": self._prev_acting_u.copy(),
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
        self._prev_acting_u = (
            _vector(arrays["prev_applied_u_m_s"], n, "prev_applied_u_m_s")
            if "prev_applied_u_m_s" in arrays
            else self._acting_u.copy()
        )
        self._soft_lo = (
            _vector(arrays["soft_lo_m"], n, "soft_lo_m")
            if "soft_lo_m" in arrays
            else self._lo.copy()
        )
        self._soft_hi = (
            _vector(arrays["soft_hi_m"], n, "soft_hi_m")
            if "soft_hi_m" in arrays
            else self._hi.copy()
        )
        self._hook_t = None  # the model marks the restored time (mark_hooked)
        self._hook_dt = None
        if self._valve_on:
            self._zero_valve_state()  # a snapshot without valve keys = a run start (u_a = 0)
            if all(k in arrays for k in VALVE_STATE_KEYS):
                self._valve_u = _vector(arrays["valve_u_m_s"], n, "valve_u_m_s")
                self._amp_u = _vector(arrays["amp_u_m_s"], n, "amp_u_m_s")
                self._amp_target = _vector(arrays["amp_target_m_s"], n, "amp_target_m_s")
                self._amp_rate = _vector(arrays["amp_rate_m_s2"], n, "amp_rate_m_s2")
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
        self._prev_acting_u = zero.copy()
        self._next_full_update = False
        self._pending_post_restore = None
        self._hook_t = None
        self._hook_dt = None
        self._apply(self._ramp_start, self._ramp_slope)
