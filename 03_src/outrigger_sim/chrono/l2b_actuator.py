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

import dataclasses
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.actuation import SATURATION_STOP_S, FlowLimit, SpeedReference
from outrigger_sim.chrono.actuators import leg_force_limits_N
from outrigger_sim.chrono.m2_release_log import M2ReleaseLog, release_record
from outrigger_sim.control.extend_start_bound import (
    ExtendBoundCheck,
    TensionTruthCounter,
    extend_bound_states,
)
from outrigger_sim.hydraulics.check_open_delay import (
    CheckDelayInputs,
    CheckDelayOutput,
    CheckOpenDelay,
)
from outrigger_sim.hydraulics.counterbalance import Counterbalance
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.rod_release import (
    PREVIOUS_PRESSURE_KEY,
    RodPressureFlowLaw,
    RodReleaseShift,
)
from outrigger_sim.hydraulics.seal_friction import SealFriction, leg_limits_N
from outrigger_sim.params import LEG_ORDER, Params

PART_PREFIX = "l2b_actuator"
LOCK_EPS_M_S = 1.0e-6
"""``|u| <= this`` = valve locked (locked dashpot); same value as ``actuator.rod_side.
lock_eps_m_s`` (dynamics 5.12.8 Q-D5)."""
HOOK_TIME_REL_TOL = 1.0e-12

GUIDE_FREE_XY = (False, False, True, True, True)
"""``SetGuideConstraint(c_x, c_y, c_rx, c_ry, c_rz)`` of the L2b motor (plan S7 risk 1)."""

HEAD_RETURN_BACK_PRESSURE_PA = 2.0e5
"""S8-A1 (``dynamics_model.md`` 5.26.10): head-side floor of the pressure split while the valve
drives the leg (``|u| > lock_eps``): return back pressure 2 bar g (ASSUMPTION). Locked legs use
the cavitation floor of the rod-side law (``actuator.rod_side.p_floor_Pa``, 0.1 bar abs)."""


def split_pressures(force_N: ArrayLike, rod_pressure_Pa: ArrayLike, head_area_m2: ArrayLike,
                    annulus_area_m2: ArrayLike, floor_Pa: ArrayLike
                    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.bool_]]:
    """S8-A1 pressure split of the net (pressure) force ``F_p = p_h A_p - p_r A_ann``:
    ``p_h = max(floor, (F_p + p_r A_ann) / A_p)``; where the floor binds, ``p_r = (p_h A_p -
    F_p) / A_ann`` (net force unchanged). Returns (``p_h``, ``p_r``, hit mask). Legs above the
    floor keep the unfloored expression bit for bit."""
    f = np.asarray(force_N, dtype=float)
    p_r = np.asarray(rod_pressure_Pa, dtype=float)
    a_p = np.asarray(head_area_m2, dtype=float)
    a_r = np.asarray(annulus_area_m2, dtype=float)
    p_h = (f + p_r * a_r) / a_p
    floor = np.broadcast_to(np.asarray(floor_Pa, dtype=float), p_h.shape)
    hit = p_h < floor
    if not np.any(hit):
        return p_h, p_r.copy(), hit
    p_h = np.where(hit, floor, p_h)
    p_r = np.where(hit, (floor * a_p - f) / a_r, p_r)
    return p_h, p_r, hit


class L2bHookMissedError(RuntimeError):
    """A step would run with a force the actuator hook did not set for it."""


class _CheckDelayAdapter:
    """M1c between the hook and the speed reference: the hook sets the plant inputs before
    ``advance``, the reference calls :meth:`filter_speed` behind the valve (v5 spec 2.0 row 3)."""

    def __init__(self, model: CheckOpenDelay) -> None:
        self.model = model
        self.inputs: CheckDelayInputs | None = None
        self.output: CheckDelayOutput | None = None
        self.pending_opening_m = np.zeros(len(model.A_h))

    def filter_speed(self, t_s: float, dt_s: float, request_m_s: ArrayLike) -> NDArray[np.float64]:
        if self.inputs is None:
            raise RuntimeError("M1c filter without the hook inputs")
        inputs = dataclasses.replace(self.inputs, t_s=float(t_s), dt_s=float(dt_s),
                                     u_m_s=np.asarray(request_m_s, dtype=float))
        self.output = self.model.filter(inputs)
        return self.output.speed_m_s


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
        seal_friction: SealFriction | None = None,
        counterbalance: Counterbalance | None = None,
        oil_law: L2bRodSide | None = None,
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
        # S8 seal friction / counterbalance path (module docstring "S8")
        if counterbalance is not None and seal_friction is None:
            raise ValueError("the counterbalance path needs a SealFriction (limit 0 allowed)")
        self.seal_friction = seal_friction
        """Seal friction element (S8, ``hydraulics.seal_friction``); None = S7 path."""
        self.counterbalance = counterbalance
        """Counterbalance element (``lock_valve = "counterbalance"``); None = pilot check."""
        self._oil = rod_side if oil_law is None else oil_law
        if seal_friction is not None:
            if self._oil is None or not self._oil.oil_only:
                raise ValueError("the friction path needs an oil-only law (L2bRodSide, k_out = inf)")
            if seal_friction.n_legs != n or self._oil.n_legs != n:
                raise ValueError("friction / oil law must have one leg per motor")
        flex = 1.0 / self._k_rod + 1.0 / self._k_frame
        if self._k_c is not None:
            flex = flex + 1.0 / self._k_c
        self._k_out = 1.0 / flex
        self._acting_f = np.zeros(n)
        self._f_next = np.zeros(n)
        self._acting_sp = np.full(n, np.nan)
        self._sp_next = np.full(n, np.nan)
        self._oil_arm_seen = -1
        self._last_spring: NDArray[np.float64] | None = None
        self._last_ph: NDArray[np.float64] | None = None
        self._last_pr: NDArray[np.float64] | None = None
        self.friction_state_defaulted = False
        self.cb_below_soft_limit_steps = np.zeros(n, dtype=np.int64)
        self.pressure_floor_enabled = True
        """S8-A1 head-side floor of the pressure split (False = the S7 split, regression)."""
        self.pressure_floor_hook_hits = np.zeros(n, dtype=np.int64)
        """Hook steps (friction path) whose ``p_h`` (CB / pressure-model input) hit the floor."""
        self._force = np.zeros(n)
        self._acting_force = np.zeros(n)
        self._k_last = np.full(n, np.nan)
        self._hook_t: float | None = None
        self._rod_release: RodReleaseShift | None = None
        """M2 (v5 spec 2.3, :meth:`configure_rod_release`); None = off, no line of it runs."""
        self._m2_log: M2ReleaseLog | None = None
        """M2 release record (v5 stage 3 R-1); exists with M2 only."""
        self._lock_closure: Any = None
        """LC setting (v5 spec 2.5, :meth:`configure_lock_closure`); None = off."""
        self._check_delay: _CheckDelayAdapter | None = None
        """M1c (v5 spec 2.4, :meth:`configure_check_delay`); None = off."""
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
        rod_release: bool | None = None,
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
            rod_release: True = M2 on (:meth:`configure_rod_release`); None / False = off.
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
        # S8 (C-1/C-3/C-4): friction level from actuator.seal_friction.level_N, CB from
        # actuator.lock_valve; level 0 + pilot check = the S7 path (bypass, bit-identical)
        sf_cfg = params.l2b.seal_friction
        level = 0.0 if sf_cfg is None else float(sf_cfg.level_N)
        cb_cfg = params.l2b.counterbalance if params.l2b.lock_valve == "counterbalance" else None
        friction_path = level > 0.0 or cb_cfg is not None
        law = (
            L2bRodSide.from_params(
                params, idx, include_concrete=include_concrete, armed=rod_side_armed,
                mechanics="one_sided_parallel", oil_only=friction_path, counterbalance=cb_cfg,
            )
            if use_rod_side
            else None
        )
        friction = counterbalance = oil = None
        if friction_path:
            oil = law if law is not None else L2bRodSide.from_params(
                params, idx, include_concrete=include_concrete, armed=False, mechanics="off",
                oil_only=True)
            names = [LEG_ORDER[i] for i in idx]
            rear_scale = 1.0 if sf_cfg is None else sf_cfg.rear_scale
            seal = None
            if sf_cfg is not None and sf_cfg.pressure_model == "seal_geometry":
                seal = {"kappa_N_per_m_Pa": sf_cfg.kappa_N_per_m_Pa, "F0_N": sf_cfg.F0_N,
                        "F0_seal_diameter_sum_m": sf_cfg.F0_seal_diameter_sum_m,
                        "p_ref_head_Pa": [sf_cfg.p_ref_head_Pa[i] for i in idx],
                        "p_ref_rod_Pa": sf_cfg.p_ref_rod_Pa,
                        "bore_diameter_m": [sf_cfg.bore_diameter_m[i] for i in idx],
                        "rod_diameter_m": [sf_cfg.rod_diameter_m[i] for i in idx]}
            k_out = []
            for i in idx:
                fl = 1.0 / a.k_rod_N_m[i] + 1.0 / a.frame_stiffness_N_m
                if include_concrete:
                    fl = fl + 1.0 / a.k_concrete_N_m
                k_out.append(1.0 / fl)
            # ML input (python-expert spec): limit = level x rear 0.833 x leg_scale[i]
            leg_scale = (1.0,) * 4 if sf_cfg is None else sf_cfg.leg_scale
            limits = leg_limits_N(level, rear_scale, names)
            if any(float(leg_scale[i]) != 1.0 for i in idx):
                limits = limits * np.array([float(leg_scale[i]) for i in idx])
            friction = SealFriction(
                limits, k_out,
                static_ratio=1.0 if sf_cfg is None else sf_cfg.static_ratio,
                stick_stiffness_N_m=0.0 if sf_cfg is None else sf_cfg.stick_stiffness_N_m,
                pressure_model="constant" if sf_cfg is None else sf_cfg.pressure_model,
                seal=seal,
            )
            if cb_cfg is not None:
                counterbalance = Counterbalance(
                    cb_cfg, [a.head_area_m2[i] for i in idx],
                    [params.l2b.rod_side.annulus_area_m2[i] for i in idx])
        actuator = cls(
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
            seal_friction=friction,
            counterbalance=counterbalance,
            oil_law=oil,
        )
        if rod_release:
            actuator.configure_rod_release()
        return actuator

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

    def head_floor_Pa(self, u_m_s: ArrayLike) -> NDArray[np.float64]:
        """S8-A1 floor per leg: return back pressure while moving, cavitation floor locked."""
        u = np.asarray(u_m_s, dtype=float).reshape(self.n_legs)
        locked_floor = (self.rod_side.p_floor_gauge_Pa if self.rod_side is not None
                        else -np.inf)
        return np.where(np.abs(u) > self._eps, HEAD_RETURN_BACK_PRESSURE_PA, locked_floor)

    def pressure_split(self, pressure_force_N: ArrayLike, rod_pressure_Pa: ArrayLike,
                       u_m_s: ArrayLike
                       ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.bool_]]:
        """Head / rod pressure of the net force ``F_p`` (S8-A1, :func:`split_pressures`); the
        S7 split ``p_h = (F_p + p_r A_ann) / A_p`` when the rod-side law is off or the floor is
        disabled. Returns (``p_h``, ``p_r``, hit mask)."""
        f = np.asarray(pressure_force_N, dtype=float).reshape(self.n_legs)
        p_r = np.asarray(rod_pressure_Pa, dtype=float).reshape(self.n_legs)
        if self.rod_side is None:
            return f / self._area, p_r.copy(), np.zeros(self.n_legs, dtype=bool)
        a_r = self.rod_side.annulus_area_m2
        if not self.pressure_floor_enabled:
            return (f + p_r * a_r) / self._area, p_r.copy(), np.zeros(self.n_legs, dtype=bool)
        return split_pressures(f, p_r, self._area, a_r, self.head_floor_Pa(u_m_s))

    # --- R8 valve model and law-C views (same names as L1SpeedActuator, run_S6C helpers) ----

    def configure_valve(self, *, tau_s: float, amp_ramp: str = "none",
                        amp_ramp_s: float = 0.1) -> None:
        """Valve lag on the speed reference (``SpeedReference.configure_valve``): the spool
        output is the flow / ``A_p`` that integrates into ``s_ref`` and drives the dashpot."""
        self.reference.configure_valve(tau_s=tau_s, amp_ramp=amp_ramp, amp_ramp_s=amp_ramp_s)

    def set_flow_limit(self, flow_limit: FlowLimit | None) -> None:
        """Shared-pump flow limit on the speed reference (``SpeedReference.set_flow_limit``, default
        none). It reads the force law C judges: ``F`` on the S7 path, ``F - f`` on the friction path."""
        self.reference.set_flow_limit(flow_limit)

    # --- M2 rod release force (v5 spec 2.3) -----------------------------------------------------

    def configure_rod_release(self) -> None:
        """Turn M2 on: the rod pressure of a moving leg shifts ``s_ref`` (both directions, D-4).

        The shift ``A_ann (p_r^(k-1) - p_r^k) / k_h(s_ref)`` is computed after the force of this
        hook, so it acts from the next hook on. Locked legs and a disarmed law do not shift. The
        moving rod pressure follows revision 3 (user decision 2026-11-06): its lag is capped by
        the valve flow (``rod_release.flow_limited_rod_pressure``). Revision 4
        (``flow_limited_r4``, 2026-11-07): the shift reads ``p_r + Delta w`` with ``Delta`` of
        the release and ``w`` the release decay of the rod-side machine (no double count).

        Raises:
            ValueError: No rod-side law, or the counterbalance path (never tested with M2).
        """
        if self.rod_side is None:
            raise ValueError("M2 needs the rod-side law (its rod pressure)")
        if self.counterbalance is not None:
            raise ValueError("M2 with lock_valve = counterbalance is refused (untested path)")
        self._rod_release = RodReleaseShift(self.rod_side.annulus_area_m2)
        # v5 stage 3 R-1: read-only release record (never feeds back)
        self._m2_log = M2ReleaseLog(self.rod_side.annulus_area_m2)
        # premise ① truth of the ③ bound (tension_premise.md S-2): record only
        self._tension_truth = TensionTruthCounter()
        self._extend_bound_check: ExtendBoundCheck | None = None
        """Created on the first controller read with the ③ bound on (5.5); None = off."""
        # revision 3 pressure law: the moving rod pressure M2 reads is capped by the valve
        # flow; the friction path reads it from its oil law G, which may be another object
        law = RodPressureFlowLaw()
        self.rod_side.set_rod_pressure_flow_law(law)
        if self._oil is not None and self._oil is not self.rod_side:
            self._oil.set_rod_pressure_flow_law(law)

    # --- LC overlap cut and check closing delay (v5 spec 2.5) ------------------------------------

    def configure_lock_closure(self, setting: Any) -> None:
        """Turn LC on: the spool tail of a zero command stops at the overlap end, the leg locks
        ``t_c`` later and the dashpot follows the law's lock state instead of ``|u| <= eps``.

        Args:
            setting: ``hydraulics.v5_options.LockClosureSetting``.

        Raises:
            ValueError: No rod-side law, the counterbalance path, or the valve model off.
        """
        if self.rod_side is None:
            raise ValueError("LC needs the rod-side law (its lock state machine)")
        if self.counterbalance is not None:
            raise ValueError("LC with lock_valve = counterbalance is refused (other lock rule)")
        self.reference.configure_lock_closure(setting, zero_command_m_s=self._eps)
        self.rod_side.set_closing_delay(setting.closing_delay_s)
        self._lock_closure = setting

    def _dashpot_N_s_m(self, u: NDArray[np.float64]) -> NDArray[np.float64]:
        """Locked or moving dashpot per leg; with LC by the law's lock state (spec 2.5); a leg
        that M1c holds takes the locked dashpot (spec 2.4)."""
        if self._lock_closure is not None and self.rod_side is not None and self.rod_side.armed:
            c = np.where(self.rod_side.locked, self._c_lock, self._c_move)
        else:
            c = np.where(np.abs(u) <= self._eps, self._c_lock, self._c_move)
        if self._check_delay is not None and self._check_delay.output is not None:
            c = np.where(self._check_delay.output.lock_damping, self._c_lock, c)
        return c

    # --- M1c check opening delay (v5 spec 2.4, reference values) --------------------------------

    def configure_check_delay(self, setting: Any, circuit: Any) -> None:
        """Turn M1c on (``hydraulics.check_open_delay``; the units missed their criteria, the
        results are reference values).

        Args:
            setting: ``CheckDelaySetting`` (VN or BL).
            circuit: ``CheckDelayCircuit`` of these legs.

        Raises:
            ValueError: No rod-side law, the counterbalance path or the valve model off.
        """
        if self.rod_side is None:
            raise ValueError("M1c needs the rod-side law (its lock state and pressures)")
        if self.counterbalance is not None:
            raise ValueError("M1c with lock_valve = counterbalance is refused (untested path)")
        adapter = _CheckDelayAdapter(CheckOpenDelay(setting, circuit))
        self.reference.set_check_delay(adapter)
        self._check_delay = adapter

    def check_delay_summary(self) -> dict[str, Any] | None:
        return None if self._check_delay is None else self._check_delay.model.summary()

    def _prepare_check_delay(self, pressure_force_N: NDArray[np.float64]) -> None:
        """Inputs of the M1c filter from the state at the hook (before ``advance``)."""
        oil = self._oil
        assert oil is not None
        rod_Pa = oil.rod_pressure_Pa
        head_Pa = (pressure_force_N + rod_Pa * oil.annulus_area_m2) / self._area
        band_N = np.zeros(self.n_legs)
        if self.seal_friction is not None:
            band_N = self.seal_friction.F_s_N - self._acting_f
        self._check_delay.inputs = CheckDelayInputs(
            math.nan, math.nan, np.zeros(self.n_legs), head_Pa, rod_Pa, oil.locked, oil.void_m(),
            band_N, self.reference.s_ref_m)

    def _apply_check_delay(self) -> None:
        """After the force of this hook: seeds, the creep now, the opening shift one hook later
        (after the law has released, as the harness applies it after the chunk)."""
        adapter = self._check_delay
        oil = self._oil
        assert adapter is not None and oil is not None
        if adapter.pending_opening_m.any():
            self.reference.shift_reference(adapter.pending_opening_m)
            # guard: a leg still locked here keeps its head anchor with the reference (a
            # released leg is a no-op in shift_head)
            for i in np.flatnonzero(adapter.pending_opening_m != 0.0):
                oil.shift_head(int(i), float(adapter.pending_opening_m[i]))
            adapter.pending_opening_m = np.zeros(self.n_legs)
        output = adapter.output
        if output is None:
            return
        for i in np.flatnonzero(np.isfinite(output.opening_rod_pressure_Pa)):
            # M2 takes the seed as the start of the release lag (``releases_of_last_call``)
            oil.seed_release_pressure(int(i), float(output.opening_rod_pressure_Pa[i]))
        if output.creep_shift_m.any():
            self.reference.shift_reference(output.creep_shift_m)
            for i in np.flatnonzero(output.creep_shift_m != 0.0):
                oil.shift_head(int(i), float(output.creep_shift_m[i]))
        adapter.pending_opening_m = output.opening_shift_m.copy()

    def rod_release_record(self) -> dict[str, Any] | None:
        """M2 totals per leg (they move the stroke reading too); None when M2 is off."""
        return None if self._rod_release is None else self._rod_release.record()

    def m2_release_record(self) -> dict[str, Any] | None:
        """v5 stage 3 R-1 / R-2 block (``chrono.m2_release_log.release_record``); None when M2
        is off. Closes the open releases at the last hook (call once, at the run end)."""
        if self._rod_release is None:
            return None
        law = self._oil.rod_pressure_flow_law
        record = self._rod_release.record()
        out = release_record(self._m2_log, None if law is None else law.meta(),
                             self._rod_release.clip_times_s, record["m2_clipped_steps"],
                             record["m2_shift_total_mm"])
        out["tension_truth"] = self._tension_truth.record()
        check = self._extend_bound_check
        out["extend_bound_check"] = None if check is None else check.record()
        return out

    def _count_tension_truth(self, t_s: float, dt_s: float, u_acting_m_s: NDArray[np.float64],
                             cylinder_force_N: NDArray[np.float64]) -> None:
        """Premise ① truth of the step just taken (``tension_premise.md`` S-2, record only):
        an unlocked leg with an applied speed > 0 whose machine extend target ``p*`` (the
        state machine's ``moving_target_rod_pressure_Pa(EXT, F)`` of the force that acted) is
        above ``p_bB``."""
        oil = self._oil
        if oil is None or not oil.armed:
            return
        is_extending = ~np.asarray(oil.locked, bool) & (np.asarray(u_acting_m_s, float) > 0.0)
        if not is_extending.any():
            return
        target_Pa = oil.extension_targets_Pa(cylinder_force_N)
        self._tension_truth.add(is_extending, target_Pa, float(dt_s), float(t_s),
                                oil.rod_pressure_Pa)

    def check_extend_bound(self, t_s: float, bound_Pa: ArrayLike,
                           locked_model_bound_Pa: ArrayLike | None = None,
                           locked_sources: list[str | None] | None = None) -> None:
        """``tension_premise.md`` 5.5 / 6.4: the controller's ③ bound (and its locked model
        bound ④) of the read at ``t_s`` against the rod-side machine (its tracked pressure
        while moving, its locked pressure); record only, kept with M2 on
        (``m2_release_record``)."""
        oil = self._oil
        if self._rod_release is None or oil is None or not oil.armed:
            return
        if self._extend_bound_check is None:
            self._extend_bound_check = ExtendBoundCheck(oil.annulus_area_m2)
        self._extend_bound_check.add(t_s, bound_Pa, oil.rod_pressure_Pa,
                                     extend_bound_states(oil.locked, oil.last_directions),
                                     locked_model_bound_Pa, locked_sources)

    def m2_state(self) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None:
        """v5 stage 3 R-5: (``p_hat`` of the last hook, accumulated shift ``s_ref`` sign) per
        leg; None when M2 is off."""
        if self._rod_release is None:
            return None
        return self._m2_p_hat(), self._rod_release.shift_total_m

    def _m2_p_hat(self) -> NDArray[np.float64]:
        """``p_hat`` of the last M2 hook from the snapshot view (NaN before the first hook)."""
        arrays = self._rod_release.state_arrays()
        if PREVIOUS_PRESSURE_KEY not in arrays:
            return np.full(self.n_legs, np.nan)
        return np.asarray(arrays[PREVIOUS_PRESSURE_KEY], dtype=float)

    def _shift_reference_for_rod_pressure(self, s_ref_now: NDArray[np.float64],
                                          t_s: float) -> None:
        release = self._rod_release
        oil = self._oil
        assert release is not None and oil is not None
        if not oil.armed:
            release.forget_pressure()
            self._m2_log.disarmed(t_s)
            return
        releases = oil.releases_of_last_call
        for leg, start in releases.items():
            release.release(leg, start)
        head_stiffness = np.array([oil.head_stiffness_N_m(i, float(s_ref_now[i]))
                                   for i in range(self.n_legs)])
        weight = np.array([oil.release_weight(i) for i in range(self.n_legs)])
        s_ref = self.reference.s_ref_m
        soft = self.reference.soft_limits_m
        clipped_before = release.clipped_steps
        # t_s: the clipped steps get their time (R-2, criteria rev. 2 2.1); values unchanged
        shift = release.shift_m(oil.rod_pressure_Pa, head_stiffness, ~oil.locked,
                                soft[:, 0] - s_ref, soft[:, 1] - s_ref, release_weight=weight,
                                t_s=float(t_s))
        if np.any(shift != 0.0):
            self.reference.shift_reference(-shift)
        self._m2_log.observe(t_s, oil, releases, shift, release.clipped_steps > clipped_before,
                             head_stiffness, weight, p_hat_Pa=self._m2_p_hat(),
                             s_ref_now_m=s_ref_now, s_ref_after_m=self.reference.s_ref_m)

    @property
    def valve_state_m_s(self) -> NDArray[np.float64]:
        return self.reference.valve_state_m_s

    @property
    def amp_output_m_s(self) -> NDArray[np.float64]:
        return self.reference.amp_output_m_s

    def valve_meta(self) -> dict[str, Any]:
        return self.reference.valve_meta()

    @property
    def saturated(self) -> NDArray[np.bool_]:
        return self.reference.saturated

    @property
    def saturation_step_count(self) -> NDArray[np.int64]:
        return self.reference.saturation_step_count

    @property
    def saturation_start_count(self) -> NDArray[np.int64]:
        return self.reference.saturation_start_count

    @property
    def force_limits_N(self) -> tuple[Any, Any] | None:
        return self.reference.force_limits_N

    @property
    def saturation_stop_s(self) -> float:
        return self.reference.saturation_stop_s

    @property
    def last_judged_force_N(self) -> NDArray[np.float64]:
        """Law C judged force of the last hook (= the acting force-law value, no inertia)."""
        return self.reference.last_judged_force_N

    @property
    def last_cylinder_force_N(self) -> NDArray[np.float64]:
        return self.acting_force_N

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
        if self.seal_friction is not None:
            self._acting_f = self._f_next.copy()
            self._acting_sp = self._sp_next.copy()

    def hook(self, t_s: float, dt_s: float) -> None:
        """After step ``n`` (state at ``t_s``): saturation judgement with the force that
        acted, ``s_ref`` integration for the next step, new force from the state."""
        s = np.array([m.GetMotorPos() for m in self._motors], dtype=float)
        ds = np.array([m.GetMotorPosDt() for m in self._motors], dtype=float)
        s_ref_now = self.reference.s_ref_m
        u_acting = self.reference.u_applied_m_s
        if self.seal_friction is not None:
            self._friction_hook(t_s, dt_s, s, ds, s_ref_now, u_acting)
            return
        if self._check_delay is not None:
            self._prepare_check_delay(self._acting_force)
        self.reference.advance(dt_s, cylinder_force_N=self._acting_force, t_s=t_s)
        u = self.reference.u_applied_m_s
        self._monitor_piston(t_s, s, self._acting_force)
        if self.rod_side is None:
            self._force = self.force_law(s, ds, s_ref_now, u)
        else:
            # column lengths at s_ref (5.20.2 supplement 1: s_lock = s_ref at the lock instant)
            spring = self.rod_side.spring_force_N(
                t_s, dt_s, u_acting, s_ref_now, s_ref_now - s, self._acting_force
            )
            c = self._dashpot_N_s_m(u)
            self._k_last = self.axial_stiffness_N_m(s_ref_now)
            self._force = spring + c * (u - ds)
            if self._check_delay is not None:
                self._apply_check_delay()
            if self._rod_release is not None:
                self._shift_reference_for_rod_pressure(s_ref_now, t_s)
                self._count_tension_truth(t_s, dt_s, u_acting, self._acting_force)
        if not np.all(np.isfinite(self._force)):
            raise FloatingPointError(f"L2b force law not finite: {self._force}")
        self._apply()
        self._hook_t = float(t_s)

    def _friction_hook(self, t_s: float, dt_s: float, s: NDArray[np.float64],
                       ds: NDArray[np.float64], s_ref_now: NDArray[np.float64],
                       u_acting: NDArray[np.float64]) -> None:
        """S8 path (spec 2.5, 4.2): oil law G (k_out = inf) || seal friction, series k_out; law C
        on the pressure force F - f; counterbalance discharge for the next step."""
        sf = self.seal_friction
        oil = self._oil
        assert sf is not None and oil is not None
        fp_acting = self._acting_force - self._acting_f
        if self._check_delay is not None:
            self._prepare_check_delay(fp_acting)
        self.reference.advance(dt_s, cylinder_force_N=fp_acting, t_s=t_s)
        u = self.reference.u_applied_m_s
        if not sf.armed or oil.arm_count != self._oil_arm_seen:
            # arming (2.6): s_p = s + F_spr / k_out, f = 0, stuck (ASSUMPTION f = 0)
            spring0 = self._acting_force if self._last_spring is None else self._last_spring
            sf.arm(self.stroke_true_m(s, spring0))
            self._oil_arm_seen = oil.arm_count
            self._acting_sp = sf.s_p.copy()
        oil.spring_force_N(t_s, dt_s, u_acting, s_ref_now, s_ref_now - sf.s_p, fp_acting)
        sf.update_limits(self._last_ph, self._last_pr)
        enabled = self.rod_side is None or self.rod_side.armed
        spring = sf.step(s, s_ref_now, oil.oil_force_N, oil.oil_slope_N_m, enabled=enabled,
                         t_s=t_s)
        oil.refresh_readings(s_ref_now - sf.s_p)
        self._monitor_piston_sp(t_s, self._acting_sp)
        c = self._dashpot_N_s_m(u)
        self._k_last = self.axial_stiffness_N_m(s_ref_now)
        force = spring + c * (u - ds)
        if not np.all(np.isfinite(force)):
            raise FloatingPointError(f"L2b force law not finite: {force}")
        if self._check_delay is not None:
            self._apply_check_delay()
        if self._rod_release is not None:
            self._shift_reference_for_rod_pressure(s_ref_now, t_s)
            self._count_tension_truth(t_s, dt_s, u_acting, fp_acting)
        f_p = force - sf.f
        p_r = (oil.rod_pressure_Pa if (self.rod_side is not None and self.rod_side.armed)
               else np.zeros(self.n_legs))
        if self.rod_side is None or not self.pressure_floor_enabled:
            p_h = (f_p + p_r * oil.annulus_area_m2) / self._area
        else:
            # S8-A1: head floor (CB cracking / pressure-model input never below vacuum)
            p_h, p_r, hit = split_pressures(f_p, p_r, self._area, oil.annulus_area_m2,
                                            self.head_floor_Pa(u))
            self.pressure_floor_hook_hits += hit
        cb = self.counterbalance
        if cb is not None:
            locked = np.abs(u) <= self._eps
            dv_h, dv_r = cb.step(dt_s, locked, p_h, p_r)
            if np.any(dv_h > 0.0):
                delta = dv_h / self._area
                low = self.reference.shift_reference(delta)
                self.cb_below_soft_limit_steps += low
                for i in np.flatnonzero(dv_h > 0.0):
                    oil.shift_head(int(i), float(delta[i]))
            for i in np.flatnonzero(dv_r > 0.0):
                oil.vent_rod(int(i), float(dv_r[i]))
        self._last_spring = spring
        self._last_ph, self._last_pr = p_h, p_r
        self._f_next = sf.f.copy()
        self._sp_next = sf.s_p.copy()
        self._force = force
        self._apply()
        self._hook_t = float(t_s)

    # --- S8 views ---------------------------------------------------------------------------

    @property
    def friction_path(self) -> bool:
        """True when the S8 seal-friction / counterbalance force law is in use."""
        return self.seal_friction is not None

    @property
    def acting_friction_N(self) -> NDArray[np.float64]:
        """Seal friction ``f`` that belongs to the acting force (0 on the S7 path)."""
        return self._acting_f.copy()

    @property
    def acting_pressure_force_N(self) -> NDArray[np.float64]:
        """Pressure force ``F_p = F - f`` of the step just taken (= two-sensor net force
        truth ``p_h A_p - p_r A_ann``); ``= acting_force_N`` on the S7 path."""
        if self.seal_friction is None:
            return self._acting_force.copy()
        return self._acting_force - self._acting_f

    @property
    def acting_piston_m(self) -> NDArray[np.float64] | None:
        """Piston position ``s_p`` that belongs to the acting force (None on the S7 path)."""
        return None if self.seal_friction is None else self._acting_sp.copy()

    def stroke_sensor_true_m(self, s_m: ArrayLike) -> NDArray[np.float64]:
        """Stroke sensor truth (C-6): the piston state ``s_p`` on the friction path, else the
        S7 formula ``s + F / k_out`` with the acting force (bit-identical)."""
        if self.seal_friction is None or not np.all(np.isfinite(self._acting_sp)):
            return self.stroke_true_m(s_m, self._acting_force)
        return self._acting_sp.copy()

    def s8_record(self) -> dict[str, Any]:
        """Friction and CB state (C-7) for the run summary; None parts on the S7 path."""
        return {
            "friction_path": self.friction_path,
            "seal_friction": None if self.seal_friction is None else self.seal_friction.record(),
            "counterbalance": None if self.counterbalance is None else self.counterbalance.record(),
            "cb_below_soft_limit_steps": self.cb_below_soft_limit_steps.tolist(),
            "friction_state_defaulted": self.friction_state_defaulted,
            "pressure_floor": {"enabled": self.pressure_floor_enabled,
                               "hook_hit_steps": self.pressure_floor_hook_hits.tolist(),
                               "rule": "S8-A1: p_h = max(floor, (F_p + p_r A_ann) / A_p), p_r "
                                       "re-solved where it binds; floor = return 2 bar g moving, "
                                       "rod-side cavitation floor locked"},
        }

    # --- piston stop monitor (dynamics_model.md 5.20.11 supplement 1) -------------------------

    PISTON_STOP_TOL_M = 2.0e-4
    """'Stop violation' when the piston ``s_p = s + F / k_out`` leaves ``[-0.2 mm, s_max +
    0.2 mm]`` (5.20.11: covers the hanging-rod stretch ~0.06 mm). Recorded, never clipped."""

    def _monitor_piston(self, t_s: float, s: NDArray[np.float64], f: NDArray[np.float64]) -> None:
        self._monitor_piston_sp(t_s, self.stroke_true_m(s, f))

    def _monitor_piston_sp(self, t_s: float, sp: NDArray[np.float64]) -> None:
        if not np.all(np.isfinite(sp)):
            return
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
        if self.seal_friction is not None:
            # S8 (C-8): friction, CB, the private head-only oil law and the hook carry-overs
            out.update({f"fr_{k}": v for k, v in self.seal_friction.state_arrays().items()})
            if self.counterbalance is not None:
                out.update({f"cb_{k}": v for k, v in self.counterbalance.state_arrays().items()})
            if self.rod_side is None and self._oil is not None:
                out.update({f"oil_{k}": v for k, v in self._oil.state_arrays().items()})
            nan4 = np.full(self.n_legs, np.nan)
            out.update({
                "s8_acting_f_N": self._acting_f.copy(), "s8_f_next_N": self._f_next.copy(),
                "s8_acting_sp_m": self._acting_sp.copy(), "s8_sp_next_m": self._sp_next.copy(),
                "s8_oil_arm_seen": np.array([self._oil_arm_seen]),
                "s8_last_spring_N": nan4 if self._last_spring is None else self._last_spring.copy(),
                "s8_last_ph_Pa": nan4 if self._last_ph is None else self._last_ph.copy(),
                "s8_last_pr_Pa": nan4 if self._last_pr is None else self._last_pr.copy(),
                "s8_cb_below_soft_limit_steps": self.cb_below_soft_limit_steps.copy(),
                "s8_pressure_floor_hook_hits": self.pressure_floor_hook_hits.copy(),
            })
        if self._rod_release is not None:  # M2 keys only with M2 on
            out.update(self._rod_release.state_arrays())
        if self._check_delay is not None:  # M1c keys only with M1c on
            out.update(self._check_delay.model.state_arrays())
            out["m1c_pending_opening_m"] = self._check_delay.pending_opening_m.copy()
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
        if self.seal_friction is not None:
            self._restore_s8(arrays)
        if self._rod_release is not None:
            self._rod_release.restore_state(arrays)
        if self._check_delay is not None:
            self._check_delay.model.restore_state(arrays)
            if "m1c_pending_opening_m" in arrays:
                self._check_delay.pending_opening_m = np.array(arrays["m1c_pending_opening_m"],
                                                               dtype=float)
        self._apply()

    def _restore_s8(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """S8 part of :meth:`restore_state`; a snapshot without friction keys re-arms at the
        next hook (spec 2.6: s_p from the force, f = 0, stuck) and sets
        :attr:`friction_state_defaulted`."""
        sf = self.seal_friction
        assert sf is not None
        fr = {k[3:]: v for k, v in arrays.items() if k.startswith("fr_")}
        if not fr:
            sf.reset()
            self.friction_state_defaulted = True
            self._acting_f = np.zeros(self.n_legs)
            self._f_next = np.zeros(self.n_legs)
            self._acting_sp = np.full(self.n_legs, np.nan)
            self._sp_next = np.full(self.n_legs, np.nan)
            self._last_spring = self._last_ph = self._last_pr = None
            if self.counterbalance is not None:
                self.counterbalance.reset()
            return
        sf.restore_state(fr)
        if self.counterbalance is not None:
            self.counterbalance.restore_state(
                {k[3:]: v for k, v in arrays.items() if k.startswith("cb_")})
        if self.rod_side is None and self._oil is not None:
            self._oil.restore_state({k[4:]: v for k, v in arrays.items() if k.startswith("oil_")})

        def opt(key: str) -> NDArray[np.float64] | None:
            v = np.array(arrays[key], dtype=float).reshape(self.n_legs)
            return None if np.all(np.isnan(v)) else v

        self._acting_f = np.array(arrays["s8_acting_f_N"], dtype=float).reshape(self.n_legs)
        self._f_next = np.array(arrays["s8_f_next_N"], dtype=float).reshape(self.n_legs)
        self._acting_sp = np.array(arrays["s8_acting_sp_m"], dtype=float).reshape(self.n_legs)
        self._sp_next = np.array(arrays["s8_sp_next_m"], dtype=float).reshape(self.n_legs)
        self._oil_arm_seen = int(np.asarray(arrays["s8_oil_arm_seen"]).reshape(-1)[0])
        if self._oil is not None and self._oil_arm_seen >= 0:
            self._oil.arm_count = self._oil_arm_seen
        self._last_spring = opt("s8_last_spring_N")
        self._last_ph = opt("s8_last_ph_Pa")
        self._last_pr = opt("s8_last_pr_Pa")
        self.cb_below_soft_limit_steps = np.array(
            arrays["s8_cb_below_soft_limit_steps"], dtype=np.int64).reshape(self.n_legs)
        if "s8_pressure_floor_hook_hits" in arrays:  # absent in snapshots before S8-A1
            self.pressure_floor_hook_hits = np.array(
                arrays["s8_pressure_floor_hook_hits"], dtype=np.int64).reshape(self.n_legs)
        self.friction_state_defaulted = False

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
        out = self._base_meta()
        if self._rod_release is not None:  # key only with M2 on: the off meta stays as it was
            flow_law = self.rod_side.rod_pressure_flow_law
            assert flow_law is not None
            law_meta = flow_law.meta()
            out["rod_release"] = {
                "rule": "moving leg: s_ref += A_ann (p_hat_prev - p_hat) / k_h(s_ref), both "
                        "directions (v5 spec 2.3, D-4); p_hat = p_r + Delta w (revision 4), p_r = "
                        "rod-side law value before the pressure floor",
                "status": "ASSUMPTION p_bB, tau, p_r0 (spec 2.3)",
                "law": law_meta.pop("law"),
                "pressure_law": law_meta}
        if self._check_delay is not None:  # key only with M1c on
            out["check_delay"] = self._check_delay.model.meta()
        if self._lock_closure is not None:  # key only with LC on
            out["lock_closure"] = {
                "overlap_ratio": self._lock_closure.overlap_ratio,
                "closing_delay_s": self._lock_closure.closing_delay_s,
                "rule": "zero command: u = 0 once the step mean spool speed <= overlap_ratio "
                        "v_max; lock closing_delay_s later; dashpot by the law's lock state "
                        "(v5 spec 2.5)",
                "status": "ASSUMPTION (V-5, V-6, L-6, L-7 unanswered)"}
        return out

    def _base_meta(self) -> dict[str, Any]:
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
            "valve": self.reference.valve_meta(),
            "s8": self.s8_meta(),
        }

    def s8_meta(self) -> dict[str, Any]:
        """S8 force-law description (C-7, C-8): friction path, friction and CB parameters."""
        if self.seal_friction is None:
            return {"friction_path": False, "lock_valve": "pilot_check",
                    "seal_friction": None, "counterbalance": None,
                    "law": "S7 series law (seal friction level 0, pilot check)"}
        return {
            "friction_path": True,
            "lock_valve": "pilot_check" if self.counterbalance is None else "counterbalance",
            "law": "F = k_out (s_p - s) + c (u - ds), k_out (s_p - s) = G(s_ref - s_p) + f, "
                   "|f| <= F_s (S8 spec 2.1 / 2.5); law C on F - f; stroke truth s_p",
            "k_out_N_m": self._k_out.tolist(),
            "seal_friction": self.seal_friction.meta(),
            "counterbalance": None if self.counterbalance is None else self.counterbalance.meta(),
            "oil_law": None if self._oil is None else self._oil.meta(),
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
