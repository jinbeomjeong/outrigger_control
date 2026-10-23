"""L2b-NSC leg actuator: ``ChLinkMotorLinearForce`` with an explicit hydraulic force law.

``00_docs/03_chrono/chrono_build_plan.md`` S7 (``L2bForceActuator``, risks 1 and 2);
``dynamics_model.md`` 2.3 (L2b-NSC row), 4.2, 4.4 (L2b-NSC column), rev. 23 5.10 (law C).

Force law per leg (sign: + = extends = pushes the pad down, R4; = cylinder force):

    F = k_ax(s) (s_ref - s) + c (u - ds/dt)
    k_ax(s) = series(beta A_p / (L_0 + s), k_rod, k_frame, k_concrete)

* ``s`` = ``GetMotorPos()``, ``ds/dt`` = ``GetMotorPosDt()`` of the step just taken (link
  displacement along the leg axis; it contains the rod / frame / concrete compression);
* ``s_ref``, ``u`` = :class:`outrigger_sim.actuation.SpeedReference` (the L1 limiter: speed
  limit, command ramp, stroke-end braking, law C saturation with the per-leg 210 bar limits
  ``legs.<leg>.cylinder.max_force_{extend,retract}_N``). The spring uses ``s_ref`` at the time
  of the state (``t_n``, before this hook's integration) and the damper the speed ``u`` the
  hook sets for the next step;
* ``c`` = locked dashpot (valve locked, ``|u| <= lock_eps``) or moving dashpot (valve driving
  the leg), rev. 33 values ``params.l2b.actuator.damping_lock_N_s_m`` / ``damping_moving_N_s_m``
  (LOCK basis 34,403.5 / 30,348.5 and zeta 0.10 on ``k_2(e_op)`` 100,206 / 86,949 N s/m,
  ``dynamics_model.md`` 5.20.3); ``damping="yaml_pre_rev33"`` keeps the old YAML keys;
* rod-side chamber (rev. 33 5.20.2, ``hydraulics.l2b_rod_side``): with the law on, the spring
  part ``k_ax(s)(s_ref - s)`` is replaced by the L1-R state-machine law (locked: ``F_lock + k_2
  dc + (k_1 - k_2) min(dc, dc_knee)`` with ``k_h``, ``k_r`` frozen at ``s_lock``; moving: ``k_2(s)
  c`` plus the decaying release residual);
* the judged force of law C is ``F`` itself: the force-law value holds no rod inertia (in L1
  the rigid motor reaction does, hence ``F - m_rod a`` there). Same convention (judged force
  without rod inertia), no correction term.

Explicit update (risk 2): the hook after step ``n`` computes ``F`` from the state at ``t_n``
and writes it into the motor's ``ChFunctionConst``. ``ChLinkMotorLinearForce::
IntLoadResidual_F`` (``ChLinkMotorLinearForce.cpp:36``) evaluates the function when the
residual of step ``n + 1`` is loaded, i.e. the force acts during step ``n + 1`` (checked by
``05_tests/chrono/test_l2b_actuator.py``: ``dv`` of the next step = ``F dt / m``). This is the
same explicit-force pattern as an internal force evaluated at the step start (semi-implicit
Euler on the rod), stable for ``dt < (2/omega)(sqrt(1 + zeta^2) - zeta)``: rod in the air
about 78 Hz (front), zeta 0.30 locked / 1.0 moving -> 3.3 / 1.9 ms (``dynamics_model.md``
4.3) >> 1e-4 s. Fall-back if it misbehaves: ``ChLinkTSDA`` with rest length from ``s_ref``.

Motor (``make_force_motor``): ``Initialize(rod, superstructure, False, frame_rod,
frame_body)``, frames as the L1 motor (link Z = body -z, R4). Guide x, y freed:
``SetGuideConstraint(False, False, True, True, True)`` (``ChLinkMotorLinear.cpp:41``; exposed
in pychrono 10.0.0, checked 2026-10-24); rotations stay locked. The lateral leg compliance is
the lateral bushing (``chrono/lateral_bushing``).

Hook guard: :meth:`L2bForceActuator.on_step_start` raises :class:`L2bHookMissedError` when the
last hook did not run at the current time (the force would be stale).

Units SI; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.actuation import SATURATION_STOP_S, SpeedReference
from outrigger_sim.chrono.actuators import leg_force_limits_N
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.params import LEG_ORDER, Params

PART_PREFIX = "l2b_actuator"
LOCK_EPS_M_S = 1.0e-6
"""``|u| <= this`` = valve locked (locked dashpot); same value as ``actuator.rod_side.
lock_eps_m_s`` (dynamics 5.12.8 Q-D5)."""
HOOK_TIME_REL_TOL = 1.0e-12

GUIDE_FREE_XY = (False, False, True, True, True)
"""``SetGuideConstraint(c_x, c_y, c_rx, c_ry, c_rz)`` of the L2b motor (plan S7 risk 1)."""


class L2bHookMissedError(RuntimeError):
    """A step would run with a force the actuator hook did not set for it."""


def make_force_motor(
    rod: ch.ChBody,
    superstructure: ch.ChBody,
    frame_rod: ch.ChFramed,
    frame_body: ch.ChFramed,
    *,
    name: str,
    free_xy: bool = True,
) -> tuple[ch.ChLinkMotorLinearForce, ch.ChFunctionConst]:
    """Force motor with a constant force function (set by the hook) and the guide x, y freed
    (``free_xy``; False = PRISMATIC, the L2 option). Not added to the system."""
    motor = ch.ChLinkMotorLinearForce()
    motor.SetName(name)
    if free_xy:
        motor.SetGuideConstraint(*GUIDE_FREE_XY)
    motor.Initialize(rod, superstructure, False, frame_rod, frame_body)
    function = ch.ChFunctionConst(0.0)
    motor.SetForceFunction(function)
    return motor, function


class L2bForceActuator:
    """Force-law actuator of the four legs (module docstring).

    Args:
        motors: ``ChLinkMotorLinearForce`` per leg (LEG_ORDER subset order = ``legs``).
        functions: Their ``ChFunctionConst`` force functions.
        reference: Speed reference (``s_ref`` start = the initial reference).
        bulk_modulus_Pa, dead_length_m, frame_stiffness_N_m: Oil column and frame.
        head_area_m2, k_rod_N_m: Per leg.
        k_concrete_N_m: Concrete in series (None = SCM, dropped).
        damping_locked_N_s_m, damping_moving_N_s_m: Per leg, actual values.
    """

    def __init__(
        self,
        motors: Sequence[Any],
        functions: Sequence[ch.ChFunctionConst],
        reference: SpeedReference,
        *,
        bulk_modulus_Pa: float,
        dead_length_m: float,
        frame_stiffness_N_m: float,
        head_area_m2: ArrayLike,
        k_rod_N_m: ArrayLike,
        k_concrete_N_m: float | None,
        damping_locked_N_s_m: ArrayLike,
        damping_moving_N_s_m: ArrayLike,
        lock_eps_m_s: float = LOCK_EPS_M_S,
        rod_side: L2bRodSide | None = None,
    ) -> None:
        n = len(motors)
        if n == 0 or len(functions) != n or reference.n_legs != n:
            raise ValueError("need one motor, one function and one reference leg per leg")
        self._motors = tuple(motors)
        self._functions = tuple(functions)
        self.reference = reference
        self._beta = float(bulk_modulus_Pa)
        self._l0 = float(dead_length_m)
        self._k_frame = float(frame_stiffness_N_m)
        self._area = np.array(head_area_m2, dtype=float).reshape(n)
        self._k_rod = np.array(k_rod_N_m, dtype=float).reshape(n)
        self._k_c = None if k_concrete_N_m is None else float(k_concrete_N_m)
        self._c_lock = np.array(damping_locked_N_s_m, dtype=float).reshape(n)
        self._c_move = np.array(damping_moving_N_s_m, dtype=float).reshape(n)
        self._eps = float(lock_eps_m_s)
        if rod_side is not None and rod_side.n_legs != n:
            raise ValueError("rod-side law must have one leg per motor")
        self.rod_side = rod_side
        """Rod-side law (``hydraulics.l2b_rod_side``, dyn rev. 33 5.20.2); None = head only."""
        self._force = np.zeros(n)
        self._acting_force = np.zeros(n)
        self._k_last = np.full(n, np.nan)
        self._hook_t: float | None = None
        self.reset_piston_monitor()
        self._apply()

    @classmethod
    def from_params(
        cls,
        params: Params,
        motors: Sequence[Any],
        functions: Sequence[ch.ChFunctionConst],
        s_init_m: ArrayLike,
        *,
        legs: Sequence[str] = LEG_ORDER,
        force_saturation: bool = True,
        include_concrete: bool = True,
        ramp_s: float | None = None,
        damping: str = "rev33",
        rod_side: bool | None = None,
        rod_side_armed: bool = True,
    ) -> L2bForceActuator:
        """YAML values (``params`` loaded with ``model="L2b_NSC"``) for the legs ``legs``.

        Args:
            damping: ``"rev33"`` (default: locked = LOCK basis, moving = zeta 0.10 on k_2 with
                the concrete, ``params.l2b.actuator.damping_*``) or ``"yaml_pre_rev33"`` (the
                YAML ``oil_damping_*`` keys before rev. 33: head only, concrete excluded;
                regression).
            rod_side: Rod-side law on (``params.l2b.rod_side.mechanics``) when None; False =
                head only.
            rod_side_armed: Start with the rod-side law armed (False: head only until
                ``actuator.rod_side.arm()``, V12 rule 5.20.7).
        """
        if params.l2b is None:
            raise ValueError('params must be loaded with model="L2b_NSC"')
        a = params.l2b.actuator
        idx = [LEG_ORDER.index(name) for name in legs]
        f_ext = f_ret = None
        if force_saturation:
            ext, ret = leg_force_limits_N(params)
            f_ext, f_ret = [ext[i] for i in idx], [ret[i] for i in idx]
        reference = SpeedReference(
            s_init_m,
            [params.legs[i].extension_range_m for i in idx],
            max_speed_m_s=params.actuator.max_speed_m_s,
            ramp_s=params.actuator.command_ramp_s if ramp_s is None else ramp_s,
            max_force_extend_N=f_ext,
            max_force_retract_N=f_ret,
            rod_mass_kg=None,
            saturation_stop_s=SATURATION_STOP_S,
        )
        if damping == "rev33":
            c_lock, c_move = a.damping_lock_N_s_m, a.damping_moving_N_s_m
        elif damping == "yaml_pre_rev33":
            c_lock, c_move = a.oil_damping_N_s_m, a.oil_damping_moving_N_s_m
        elif damping == "zero":  # V8(a) energy check (undamped)
            c_lock, c_move = (0.0,) * 4, (0.0,) * 4
        else:
            raise ValueError(f"unknown damping basis {damping!r}")
        rs_cfg = params.l2b.rod_side
        use_rod_side = (
            (rs_cfg is not None and rs_cfg.mechanics == "one_sided_parallel")
            if rod_side is None
            else bool(rod_side)
        )
        law = (
            L2bRodSide.from_params(
                params, idx, include_concrete=include_concrete, armed=rod_side_armed,
                mechanics="one_sided_parallel",
            )
            if use_rod_side
            else None
        )
        return cls(
            motors,
            functions,
            reference,
            bulk_modulus_Pa=a.oil_bulk_modulus_eff_Pa,
            dead_length_m=a.oil_dead_length_m,
            frame_stiffness_N_m=a.frame_stiffness_N_m,
            head_area_m2=[a.head_area_m2[i] for i in idx],
            k_rod_N_m=[a.k_rod_N_m[i] for i in idx],
            k_concrete_N_m=a.k_concrete_N_m if include_concrete else None,
            damping_locked_N_s_m=[c_lock[i] for i in idx],
            damping_moving_N_s_m=[c_move[i] for i in idx],
            rod_side=law,
        )

    # --- law ------------------------------------------------------------------------------

    @property
    def n_legs(self) -> int:
        return len(self._motors)

    def axial_stiffness_N_m(self, s_m: ArrayLike) -> NDArray[np.float64]:
        """``k_ax(s)`` per leg [N/m]."""
        s = np.array(s_m, dtype=float).reshape(self.n_legs)
        column = self._l0 + s
        if np.any(column <= 0.0):
            raise ValueError(f"oil column length <= 0 at extension {s}")
        # = params.axial_stiffness_N_m per leg, vectorised (same operation order)
        flex = column / (self._beta * self._area) + 1.0 / self._k_rod + 1.0 / self._k_frame
        if self._k_c is not None:
            flex = flex + 1.0 / self._k_c
        return 1.0 / flex

    def oil_stiffness_N_m(self, s_m: ArrayLike) -> NDArray[np.float64]:
        """``k_oil(s) = beta A_p / (L_0 + s)`` per leg [N/m] (stroke sensor truth)."""
        s = np.array(s_m, dtype=float).reshape(self.n_legs)
        return self._beta * self._area / (self._l0 + s)

    def force_law(
        self, s_m: ArrayLike, ds_m_s: ArrayLike, s_ref_m: ArrayLike, u_m_s: ArrayLike
    ) -> NDArray[np.float64]:
        """``k_ax(s_ref)(s_ref - s) + c(u - ds)`` [N] (``c`` by the lock state of ``u``).

        The oil column length is taken at ``s_ref`` (column convention of dynamics_model.md
        rev. 33 supplement 1, 5.20.2: ``s_lock = s_ref``, as the reference solutions and L1-R),
        not at the rod-body coordinate ``s = s_ref - F / k``."""
        s = np.array(s_m, dtype=float).reshape(self.n_legs)
        ds = np.array(ds_m_s, dtype=float).reshape(self.n_legs)
        sr = np.array(s_ref_m, dtype=float).reshape(self.n_legs)
        u = np.array(u_m_s, dtype=float).reshape(self.n_legs)
        k = self.axial_stiffness_N_m(sr)
        c = np.where(np.abs(u) <= self._eps, self._c_lock, self._c_move)
        self._k_last = k
        return k * (sr - s) + c * (u - ds)

    # --- views ----------------------------------------------------------------------------

    @property
    def force_N(self) -> NDArray[np.float64]:
        """Force set by the last hook (acts during the next step)."""
        return self._force.copy()

    @property
    def acting_force_N(self) -> NDArray[np.float64]:
        """Force that acted during the step just taken (= cylinder force of that step)."""
        return self._acting_force.copy()

    @property
    def head_area_m2(self) -> NDArray[np.float64]:
        return self._area.copy()

    # --- per-step -------------------------------------------------------------------------

    def set_command(self, leg_speed_m_s: ArrayLike) -> None:
        self.reference.set_command(leg_speed_m_s)

    def set_initial_force(self, force_N: ArrayLike) -> None:
        """Force of the first step (before any hook), e.g. the static preload [N]."""
        self._force = np.array(force_N, dtype=float).reshape(self.n_legs)
        self._apply()

    def on_step_start(self, t_s: float) -> None:
        """Hook guard (module docstring); the first step may run without a hook."""
        if self._hook_t is None:
            return
        if abs(self._hook_t - float(t_s)) > HOOK_TIME_REL_TOL * max(abs(t_s), 1.0):
            raise L2bHookMissedError(
                f"step at t = {t_s!r} s but the L2b actuator hook last ran at {self._hook_t!r} s"
            )

    def on_step_end(self) -> None:
        """Right after ``DoStepDynamics``: the force set before the step acted in it."""
        self._acting_force = self._force.copy()

    def hook(self, t_s: float, dt_s: float) -> None:
        """After step ``n`` (state at ``t_s``): saturation judgement with the force that
        acted, ``s_ref`` integration for the next step, new force from the state."""
        s = np.array([m.GetMotorPos() for m in self._motors], dtype=float)
        ds = np.array([m.GetMotorPosDt() for m in self._motors], dtype=float)
        s_ref_now = self.reference.s_ref_m
        u_acting = self.reference.u_applied_m_s
        self.reference.advance(dt_s, cylinder_force_N=self._acting_force)
        u = self.reference.u_applied_m_s
        self._monitor_piston(t_s, s, self._acting_force)
        if self.rod_side is None:
            self._force = self.force_law(s, ds, s_ref_now, u)
        else:
            # column lengths at s_ref (5.20.2 supplement 1: s_lock = s_ref at the lock instant)
            spring = self.rod_side.spring_force_N(
                t_s, dt_s, u_acting, s_ref_now, s_ref_now - s, self._acting_force
            )
            c = np.where(np.abs(u) <= self._eps, self._c_lock, self._c_move)
            self._k_last = self.axial_stiffness_N_m(s_ref_now)
            self._force = spring + c * (u - ds)
        if not np.all(np.isfinite(self._force)):
            raise FloatingPointError(f"L2b force law not finite: {self._force}")
        self._apply()
        self._hook_t = float(t_s)

    # --- piston stop monitor (dynamics_model.md 5.20.11 supplement 1) -------------------------

    PISTON_STOP_TOL_M = 2.0e-4
    """'Stop violation' when the piston ``s_p = s + F / k_out`` leaves ``[-0.2 mm, s_max +
    0.2 mm]`` (5.20.11: covers the hanging-rod stretch ~0.06 mm). Recorded, never clipped."""

    def _monitor_piston(self, t_s: float, s: NDArray[np.float64], f: NDArray[np.float64]) -> None:
        sp = self.stroke_true_m(s, f)
        up = sp > self._sp_max
        self._sp_max = np.where(up, sp, self._sp_max)
        self._sp_max_t = np.where(up, t_s, self._sp_max_t)
        down = sp < self._sp_min
        self._sp_min = np.where(down, sp, self._sp_min)
        self._sp_min_t = np.where(down, t_s, self._sp_min_t)
        hi = self.reference.stroke_range_m[:, 1] + self.PISTON_STOP_TOL_M
        lo = self.reference.stroke_range_m[:, 0] - self.PISTON_STOP_TOL_M
        self._sp_violations += (sp > hi) | (sp < lo)

    def reset_piston_monitor(self) -> None:
        n = self.n_legs
        self._sp_max = np.full(n, -np.inf)
        self._sp_min = np.full(n, np.inf)
        self._sp_max_t = np.full(n, np.nan)
        self._sp_min_t = np.full(n, np.nan)
        self._sp_violations = np.zeros(n, dtype=np.int64)

    def piston_monitor(self) -> dict[str, Any]:
        """Per-leg piston extremes and stop-violation step counts since the last reset."""
        return {
            "piston_max_m": self._sp_max.tolist(),
            "piston_max_t_s": self._sp_max_t.tolist(),
            "piston_min_m": self._sp_min.tolist(),
            "piston_min_t_s": self._sp_min_t.tolist(),
            "stop_violation_steps": self._sp_violations.tolist(),
            "tolerance_m": self.PISTON_STOP_TOL_M,
            "definition": "s_p = s + F_acting / k_out (k_out = series(k_rod, k_frame[, "
                          "k_concrete])), violation outside [lo - tol, hi + tol]",
        }

    def mark_hooked(self, t_s: float) -> None:
        """After a restore: the stored force belongs to the hook at ``t_s``."""
        self._hook_t = float(t_s)

    # --- snapshot (R16) -------------------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        out: dict[str, NDArray[Any]] = {
            f"ref_{k}": v for k, v in self.reference.state_arrays().items()
        }
        out["force_N"] = self._force.copy()
        out["acting_force_N"] = self._acting_force.copy()
        out["hook_t_s"] = np.array([np.nan if self._hook_t is None else self._hook_t])
        if self.rod_side is not None:
            out.update({f"rod_{k}": v for k, v in self.rod_side.state_arrays().items()})
        return out

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        self.reference.restore_state(
            {k[4:]: v for k, v in arrays.items() if k.startswith("ref_")}
        )
        self._force = np.array(arrays["force_N"], dtype=float).reshape(self.n_legs)
        self._acting_force = np.array(arrays["acting_force_N"], dtype=float).reshape(self.n_legs)
        hook = float(np.asarray(arrays["hook_t_s"]).reshape(-1)[0])
        self._hook_t = None if math.isnan(hook) else hook
        if self.rod_side is not None:
            self.rod_side.restore_state(
                {k[4:]: v for k, v in arrays.items() if k.startswith("rod_")}
            )
        self._apply()

    def stroke_true_m(self, s_m: ArrayLike, force_N: ArrayLike) -> NDArray[np.float64]:
        """Piston-to-head stroke: ``s + F / k_out`` (rod, frame and concrete compression are
        outside the built-in sensor; the link displacement ``s`` contains them)."""
        s = np.array(s_m, dtype=float).reshape(self.n_legs)
        f = np.array(force_N, dtype=float).reshape(self.n_legs)
        flex = 1.0 / self._k_rod + 1.0 / self._k_frame
        if self._k_c is not None:
            flex = flex + 1.0 / self._k_c
        return s + f * flex

    def _apply(self) -> None:
        for fn, value in zip(self._functions, self._force, strict=True):
            fn.SetConstant(float(value))

    def meta(self) -> dict[str, Any]:
        return {
            "type": "ChLinkMotorLinearForce, explicit force law (hook after each step)",
            "law": "F = k_ax(s)(s_ref - s) + c(u - ds/dt)",
            "k_ax": "series(beta A_p/(L0+s), k_rod, k_frame"
            + (", k_concrete)" if self._k_c is not None else ")"),
            "bulk_modulus_Pa": self._beta,
            "dead_length_m": self._l0,
            "frame_stiffness_N_m": self._k_frame,
            "k_concrete_N_m": self._k_c,
            "head_area_m2": self._area.tolist(),
            "k_rod_N_m": self._k_rod.tolist(),
            "damping_locked_N_s_m": self._c_lock.tolist(),
            "damping_moving_N_s_m": self._c_move.tolist(),
            "lock_eps_m_s": self._eps,
            "guide": "x, y free (SetGuideConstraint(False, False, True, True, True))",
            "saturation": {
                "law": "C (judged force = force-law value, no rod-inertia term)",
                "limits_N": self.reference.force_limits_N,
                "stop_s": self.reference.saturation_stop_s,
            },
            "max_speed_m_s": self.reference.max_speed_m_s,
            "ramp_s": self.reference.ramp_s,
            "input_lag": "force from the state at t_n acts during step n+1 (explicit)",
            "rod_side": None if self.rod_side is None else self.rod_side.meta(),
        }


def static_reference_offset_m(force_N: float, k_ax_N_m: float) -> float:
    """``s_ref - s`` that gives the spring force ``force_N`` (no motion)."""
    if not (k_ax_N_m > 0.0 and math.isfinite(k_ax_N_m)):
        raise ValueError(f"k_ax must be positive: {k_ax_N_m!r}")
    return float(force_N) / float(k_ax_N_m)


__all__ = [
    "GUIDE_FREE_XY",
    "LOCK_EPS_M_S",
    "L2bForceActuator",
    "L2bHookMissedError",
    "make_force_motor",
    "static_reference_offset_m",
]
