"""Rod-side chamber inside the L2b-NSC force law (engine independent, no pychrono).

``00_docs/01_dynamics/dynamics_model.md`` rev. 33 5.20.2. The L2b leg force law on the compression
``c = s_ref - s`` (``s`` = link displacement, the axial path rod / frame / concrete is in series
with the oil) is

    moving (EXT / RET):  F_spring = k_2(s) c + R0 exp(-(t - t_rel) / tau_v)
    locked (LOCK / FLOOR): F_spring = F_lock + k_2 dc + (k_1 - k_2) min(dc, dc_knee)

with ``k_2 = k_h (+) k_out``, ``k_1 = (k_h + k_r) (+) k_out``, ``k_h = beta A_p / (L_0h + s)``,
``k_r = beta A_ann / (s_max - s + L_0r)``, ``dc = c - c_lock``, ``dc_knee = dF_knee / k_1`` and
``dF_knee = (p_r0 - p_floor) A_ann (k_h + k_r) / k_r``. In L2b ``k_h`` and ``k_r`` are evaluated
at the extension ``s_lock`` where the leg locks and frozen while it stays locked (L1-R freezes
them at ``e_op``, Q-D7). The damping term is not part of this module (the actuator adds
``c (u - ds/dt)`` with the locked or moving dashpot).

State machine: :class:`outrigger_sim.hydraulics.rod_chamber.RodChamberLeg` (the L1-R module) with
the input "pad deflection" replaced by ``c`` (5.20.2): lock on the first step with
``|u_acting| <= eps`` (closing delay 0), ``p_r0`` = ``p_r0_after_extend`` after an extension and
``p_r0_after_retract`` (YAML, per leg) after a retraction, release on ``|u| > eps``. Its
parameters are rebuilt from the oil columns at ``s_lock`` right before a lock. The machine's own
force output clips at 0 (it models a unilateral pad contact); the L2b law is a cylinder force
that holds a hanging rod (negative), so this module keeps the anchor ``(c_lock, F_lock)`` itself
(``F_lock`` = the law value at the lock instant, so ``F`` does not step) and evaluates the
unclipped law above. Release keeps the last locked-minus-moving difference ``R0`` and decays it
with ``tau_v`` (``actuator.rod_side.release_tau_s``).

Sensor truth from the same state: rod pressure locked ``max(p_floor, p_r0 - r (F - F_lock) /
A_ann)``, ``r = k_r / (k_h + k_r)``; moving: the machine's tracked pressure (7.4 lag). Head
pressure ``(F + p_r A_ann) / A_p``.

``mechanics = "off"`` or :meth:`L2bRodSide.disarm`: ``F_spring = k_2(s) c`` (head only) on every
leg, the regression and the V12 ramp rule (5.20.7: arm after the gravity ramp and settle).

Units SI; gauge pressures except ``p_floor_abs_Pa``. Arrays per leg in the order given.
"""

from __future__ import annotations

import dataclasses
import functools
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.counterbalance import CounterbalanceLegParams
from outrigger_sim.hydraulics.rod_chamber import (
    ATMOSPHERE_PA,
    RodChamberLeg,
    RodChamberLegInput,
    RodChamberLegParams,
    RodChamberMode,
    RodChamberOptions,
    RodSideMechanics,
)
from outrigger_sim.hydraulics.rod_release import ReleaseStart, RodPressureFlowLaw

STATE_KEYS = (
    "armed",
    "locked",
    "c_lock_m",
    "F_lock_N",
    "k_h_N_m",
    "k_r_N_m",
    "p_r0_Pa",
    "release_F0_N",
    "release_t_s",
    "s_lock_m",
    "last_p_r_Pa",
    "machine",
    "machine_param_s_m",
)


M2_EXTENDED_KEY = "m2_extended_since_arm"
"""Optional snapshot key (M2 on only): per leg, an extend step since the arming (r5 anchor)."""

LOCK_ANCHOR_AFTER_EXTEND_M2 = (
    "M2 revision 5 (B): p_r0 = max(p_ext + max(p_tr - p*, 0), p_floor), p_tr = tracked M2 rod "
    "pressure of the hook before the lock, p* = moving_target_rod_pressure_Pa(EXT, F_cyl) of the "
    "lock step, p_ext = p_r0_after_extend_Pa; M2 off: p_ext")
"""Meta text of the extend lock anchor with M2 on (``r5_spec.md``, hydraulics-expert 2026-11-07)."""


def _series(*values: float) -> float:
    return 1.0 / sum(1.0 / v for v in values)


class L2bRodSide:
    """Rod-side law of the L2b legs (module docstring).

    Args:
        head_area_m2, annulus_area_m2: ``A_p``, ``A_ann`` per leg.
        k_out_N_m: ``series(k_rod, k_frame[, k_concrete])`` per leg (the non-oil axial path).
        bulk_modulus_Pa, head_dead_length_m: ``beta``, ``L_0h``.
        rod_dead_length_m: ``L_0r`` per leg.
        stroke_m: ``s_max``.
        p_r0_after_extend_Pa, p_r0_after_retract_Pa: Lock pressures per leg (gauge).
        p_floor_abs_Pa: Rod-side floor (absolute).
        release_tau_s: ``tau_v``.
        lock_eps_m_s: ``eps``.
        mechanics: ``"one_sided_parallel"`` or ``"off"``.
        armed: Start with the law on (False: head only until :meth:`arm`).
        closing_delay_s: ``t_c`` from the flow cut (``|u| <= eps``) to the lock (LC, v5 spec
            2.5); 0 = the lock in the first standstill step (the default, bit for bit).
    """

    def __init__(
        self,
        *,
        head_area_m2: ArrayLike,
        annulus_area_m2: ArrayLike,
        k_out_N_m: ArrayLike,
        bulk_modulus_Pa: float,
        head_dead_length_m: float,
        rod_dead_length_m: ArrayLike,
        stroke_m: float,
        p_r0_after_extend_Pa: ArrayLike,
        p_r0_after_retract_Pa: ArrayLike,
        p_floor_abs_Pa: float,
        release_tau_s: float,
        lock_eps_m_s: float,
        mechanics: str = "one_sided_parallel",
        armed: bool = True,
        counterbalance: Any = None,
        closing_delay_s: float = 0.0,
    ) -> None:
        self._a_p = np.array(head_area_m2, dtype=float).reshape(-1)
        n = self._a_p.size
        self._a_r = np.array(annulus_area_m2, dtype=float).reshape(n)
        self._k_out = np.array(k_out_N_m, dtype=float).reshape(n)
        self._beta = float(bulk_modulus_Pa)
        self._l0h = float(head_dead_length_m)
        self._l0r = np.array(rod_dead_length_m, dtype=float).reshape(n)
        self._stroke = float(stroke_m)
        self._p_ext = np.array(p_r0_after_extend_Pa, dtype=float).reshape(n)
        self._p_ret = np.array(p_r0_after_retract_Pa, dtype=float).reshape(n)
        self._p_floor_abs = float(p_floor_abs_Pa)
        self._tau = float(release_tau_s)
        self._eps = float(lock_eps_m_s)
        self._cb = counterbalance
        """CB parameters (S8 spec 4.3) or None (pilot-operated check)."""
        self.arm_count = 0
        """Number of :meth:`arm` calls (the seal friction re-arms with the law, spec 2.6)."""
        self.mechanics = RodSideMechanics(str(mechanics))
        self._options = RodChamberOptions(
            mechanics=RodSideMechanics.ONE_SIDED_PARALLEL,
            predictor=False,
            mode_epsilon_m_s=self._eps,
            poc_close_delay_s=float(closing_delay_s),
            rod_pressure_lag_s=self._tau,
        )
        self._legs = [RodChamberLeg(self._leg_params(i, 0.5 * stroke_m), self._options)
                      for i in range(n)]
        self._rod_pressure_flow_law: RodPressureFlowLaw | None = None
        self._n = n
        self._armed = bool(armed) and self.mechanics is RodSideMechanics.ONE_SIDED_PARALLEL
        self._reset_state()

    def _reset_state(self) -> None:
        n = self._n
        self._last_s = np.full(n, np.nan)
        self._last_t = math.nan
        self._locked = np.zeros(n, dtype=bool)
        self._c_lock = np.full(n, np.nan)
        self._s_lock = np.full(n, np.nan)
        self._f_lock = np.full(n, np.nan)
        self._k_h = np.full(n, np.nan)
        self._k_r = np.full(n, np.nan)
        self._p_r0 = np.full(n, np.nan)
        self._r0 = np.zeros(n)
        self._t_rel = np.full(n, np.nan)
        self._last_force = np.zeros(n)
        self._last_p_r = np.zeros(n)
        self._releases_of_last_call: dict[int, ReleaseStart] = {}
        self._m2_extended = np.zeros(n, dtype=bool)
        """M2 r5: the leg took an extend step (u > eps) since the arming (optional snapshot key
        :data:`M2_EXTENDED_KEY`, written with M2 on only)."""
        for leg in self._legs:
            leg.reset()

    @classmethod
    def from_params(cls, params: Any, legs: Sequence[int], *, include_concrete: bool = True,
                    armed: bool = True, mechanics: str | None = None,
                    oil_only: bool = False, counterbalance: Any = None,
                    closing_delay_s: float = 0.0) -> L2bRodSide:
        """From ``params.l2b`` (loaded with ``model="L2b_NSC"``) for the leg indices ``legs``.

        ``oil_only``: ``k_out = inf`` (the oil law G of the seal-friction / CB path, S8 spec
        2.2). ``counterbalance``: CB parameters (moving rod-side regulation and lock pressure,
        spec 4.3); None = pilot-operated check."""
        a = params.l2b.actuator
        rs = params.l2b.rod_side
        idx = list(legs)
        k_out = []
        for i in idx:
            parts = [a.k_rod_N_m[i], a.frame_stiffness_N_m]
            if include_concrete:
                parts.append(a.k_concrete_N_m)
            k_out.append(math.inf if oil_only else _series(*parts))
        return cls(
            head_area_m2=[a.head_area_m2[i] for i in idx],
            annulus_area_m2=[rs.annulus_area_m2[i] for i in idx],
            k_out_N_m=k_out,
            bulk_modulus_Pa=a.oil_bulk_modulus_eff_Pa,
            head_dead_length_m=a.oil_dead_length_m,
            rod_dead_length_m=[rs.rod_dead_length_m[i] for i in idx],
            stroke_m=rs.stroke_m,
            p_r0_after_extend_Pa=[rs.p_r0_after_extend_Pa[i] for i in idx],
            p_r0_after_retract_Pa=[rs.p_r0_after_retract_Pa[i] for i in idx],
            p_floor_abs_Pa=rs.p_floor_abs_Pa,
            release_tau_s=rs.release_tau_s,
            lock_eps_m_s=rs.lock_eps_m_s,
            mechanics=rs.mechanics if mechanics is None else mechanics,
            armed=armed,
            counterbalance=counterbalance,
            closing_delay_s=closing_delay_s,
        )

    @property
    def closing_delay_s(self) -> float:
        return self._options.poc_close_delay_s

    def set_closing_delay(self, closing_delay_s: float) -> None:
        """LC (v5 spec 2.5): a leg waits ``t_c`` in the moving law after the flow cut before it
        locks; a new command inside it releases without a lock (H5). Call before the run."""
        self._options = dataclasses.replace(self._options,
                                            poc_close_delay_s=float(closing_delay_s))
        for leg in self._legs:
            leg.options = self._options

    def set_rod_pressure_flow_law(self, law: RodPressureFlowLaw) -> None:
        """M2 (v5 spec 2.3, revision 3 pressure law): the moving rod pressure of every leg
        lags towards its target no faster than the valve flow allows; ``C_r`` from ``k_h``,
        ``k_r`` at the step's column coordinate. Call before the run (not in the snapshot)."""
        self._rod_pressure_flow_law = law
        for i, leg in enumerate(self._legs):
            leg.set_rod_pressure_flow_law(law, functools.partial(self.oil_stiffness_N_m, i))

    @property
    def rod_pressure_flow_law(self) -> RodPressureFlowLaw | None:
        return self._rod_pressure_flow_law

    @property
    def releases_of_last_call(self) -> dict[int, ReleaseStart]:
        """Legs that left their lock in the last :meth:`spring_force_N` call (M2 revision 4):
        the moving pressure lag start and ``Delta = p_r0 - p_r`` of the locked law at the
        release compression. Not in the snapshot: M2 reads it in the same hook."""
        return dict(self._releases_of_last_call)

    @property
    def lock_anchor_rod_pressure_Pa(self) -> NDArray[np.float64]:
        """``p_r0`` of the current or last lock per leg (NaN before the first lock); read-only
        view for the v5 stage 3 M2 release record (R-1)."""
        return self._p_r0.copy()

    @property
    def release_residual_N(self) -> NDArray[np.float64]:
        """``r0`` per leg: the locked-law residual the base release decay carries from the last
        release (0 while locked); read-only view for the M2 release record (R-1)."""
        return self._r0.copy()

    def release_weight(self, i: int) -> float:
        """``w`` of leg ``i`` at the last call: the machine's release decay (0 while locked)."""
        return self._legs[i].release_decay()

    # --- stiffness of the oil columns -------------------------------------------------------

    def head_stiffness_N_m(self, i: int, s_m: float) -> float:
        return self._beta * self._a_p[i] / (self._l0h + s_m)

    def rod_stiffness_N_m(self, i: int, s_m: float) -> float:
        return self._beta * self._a_r[i] / (self._stroke - s_m + self._l0r[i])

    def oil_stiffness_N_m(self, i: int, s_m: float) -> tuple[float, float]:
        """``(k_h, k_r)`` of leg ``i`` at the column coordinate ``s_m``."""
        return self.head_stiffness_N_m(i, s_m), self.rod_stiffness_N_m(i, s_m)

    def k2_N_m(self, i: int, s_m: float) -> float:
        return _series(self.head_stiffness_N_m(i, s_m), self._k_out[i])

    def k1_N_m(self, i: int, s_m: float) -> float:
        return _series(self.head_stiffness_N_m(i, s_m) + self.rod_stiffness_N_m(i, s_m),
                       self._k_out[i])

    def _leg_params(self, i: int, s_m: float) -> RodChamberLegParams:
        if self._cb is not None:
            return CounterbalanceLegParams(
                head_area_m2=float(self._a_p[i]),
                annulus_area_m2=float(self._a_r[i]),
                head_stiffness_N_m=self.head_stiffness_N_m(i, s_m),
                rod_stiffness_N_m=self.rod_stiffness_N_m(i, s_m),
                outer_stiffness_N_m=float(self._k_out[i]),
                rod_weight_N=0.0,
                p_rod_locked_after_extend_Pa=float(self._p_ext[i]),
                cavitation_floor_abs_Pa=self._p_floor_abs,
                cb_p_set_Pa=float(self._cb.p_set_Pa),
                cb_pilot_ratio=float(self._cb.pilot_ratio),
                cb_back_pressure_Pa=float(self._cb.back_pressure_Pa),
            )
        return RodChamberLegParams(
            head_area_m2=float(self._a_p[i]),
            annulus_area_m2=float(self._a_r[i]),
            head_stiffness_N_m=self.head_stiffness_N_m(i, s_m),
            rod_stiffness_N_m=self.rod_stiffness_N_m(i, s_m),
            outer_stiffness_N_m=float(self._k_out[i]),
            rod_weight_N=0.0,
            p_rod_locked_after_extend_Pa=float(self._p_ext[i]),
            cavitation_floor_abs_Pa=self._p_floor_abs,
        )

    @property
    def p_floor_gauge_Pa(self) -> float:
        return self._p_floor_abs - ATMOSPHERE_PA

    def knee_force_N(self, i: int) -> float:
        """``dF_knee`` of the current lock (NaN when moving)."""
        if not self._locked[i]:
            return math.nan
        share = self._k_r[i] / (self._k_h[i] + self._k_r[i])
        margin = max(self._p_r0[i] - self.p_floor_gauge_Pa, 0.0)
        return margin * self._a_r[i] / share

    # --- views ------------------------------------------------------------------------------

    @property
    def n_legs(self) -> int:
        return self._n

    @property
    def armed(self) -> bool:
        return self._armed

    @property
    def locked(self) -> NDArray[np.bool_]:
        return self._locked.copy()

    @property
    def rod_pressure_Pa(self) -> NDArray[np.float64]:
        """Rod pressure of the last :meth:`spring_force_N` call (gauge)."""
        return self._last_p_r.copy()

    def mode(self) -> list[str]:
        out = []
        for i in range(self._n):
            if not self._armed:
                out.append("HEAD_ONLY")
            elif not self._locked[i]:
                out.append(self._legs[i].moving_mode.name)
            else:
                dc = self._last_c[i] - self._c_lock[i] if hasattr(self, "_last_c") else 0.0
                knee = self.knee_force_N(i) / self.k1_lock(i)
                out.append("FLOOR" if dc >= knee else "LOCK")
        return out

    def k1_lock(self, i: int) -> float:
        return _series(self._k_h[i] + self._k_r[i], self._k_out[i])

    def k2_lock(self, i: int) -> float:
        return _series(self._k_h[i], self._k_out[i])

    def head_pressure_Pa(self, force_N: ArrayLike) -> NDArray[np.float64]:
        f = np.array(force_N, dtype=float).reshape(self._n)
        return (f + self._last_p_r * self._a_r) / self._a_p

    # --- arming -----------------------------------------------------------------------------

    def arm(self) -> None:
        """Switch the law on (fresh machine: each leg locks on its next standstill step at the
        force of that instant, Q-D6)."""
        if self.mechanics is not RodSideMechanics.ONE_SIDED_PARALLEL:
            raise RuntimeError("rod-side mechanics is off")
        self._reset_state()
        self._armed = True
        self.arm_count += 1

    def disarm(self) -> None:
        self._reset_state()
        self._armed = False

    # --- law --------------------------------------------------------------------------------

    def _locked_force(self, i: int, c: float) -> float:
        dc = c - self._c_lock[i]
        k1 = self.k1_lock(i)
        k2 = self.k2_lock(i)
        knee_c = self.knee_force_N(i) / k1
        return float(self._f_lock[i] + k2 * dc + (k1 - k2) * min(dc, knee_c))

    def _locked_rod_pressure_Pa(self, i: int, locked_force_N: float) -> float:
        """Rod pressure of the locked law at the force ``locked_force_N`` (module docstring)."""
        share = self._k_r[i] / (self._k_h[i] + self._k_r[i])
        return max(self.p_floor_gauge_Pa,
                   float(self._p_r0[i] - share * (locked_force_N - self._f_lock[i]) / self._a_r[i]))

    def _moving_force(self, i: int, s: float, c: float, t: float) -> float:
        residual = 0.0
        if math.isfinite(self._t_rel[i]) and self._tau > 0.0:
            residual = self._r0[i] * math.exp(-max(t - self._t_rel[i], 0.0) / self._tau)
        return self.k2_N_m(i, s) * c + residual

    def spring_force_N(
        self,
        t_s: float,
        dt_s: float,
        u_acting_m_s: ArrayLike,
        s_m: ArrayLike,
        c_m: ArrayLike,
        cylinder_force_N: ArrayLike,
    ) -> NDArray[np.float64]:
        """Advance the state to ``t_s`` and return the spring part of ``F`` per leg [N].

        Args:
            u_acting_m_s: Applied speed that acted during the step just taken.
            s_m: Column coordinate of the oil columns: ``s_ref`` at ``t_s`` (rev. 33
                supplement 1, 5.20.2: ``s_lock = s_ref`` at the lock instant, not the rod-body
                ``s``); ``k_h``, ``k_r`` and the moving ``k_2`` are evaluated here.
            c_m: ``s_ref - s`` at ``t_s`` (``s_ref`` of the force law of the next step).
            cylinder_force_N: Force that acted during the step (machine input).
        """
        u = np.array(u_acting_m_s, dtype=float).reshape(self._n)
        s = np.array(s_m, dtype=float).reshape(self._n)
        c = np.array(c_m, dtype=float).reshape(self._n)
        f_cyl = np.array(cylinder_force_N, dtype=float).reshape(self._n)
        self._last_c = c.copy()
        self._last_s = s.copy()
        self._last_t = float(t_s)
        self._releases_of_last_call = {}
        out = np.empty(self._n)
        p_r = np.zeros(self._n)
        if not self._armed:
            for i in range(self._n):
                out[i] = self.k2_N_m(i, float(s[i])) * float(c[i])
            self._last_force = out
            self._last_p_r = p_r
            return out.copy()
        for i in range(self._n):
            leg = self._legs[i]
            was_locked = bool(self._locked[i])
            standstill = abs(u[i]) <= self._eps
            if was_locked and standstill:
                # locked and staying locked: the machine has no transition to make (its
                # outputs are not used here); skip it (cost, 2026-10-24: 190 us/step for 4 legs)
                out[i] = self._locked_force(i, float(c[i]))
                share = self._k_r[i] / (self._k_h[i] + self._k_r[i])
                p_r[i] = max(self.p_floor_gauge_Pa,
                             self._p_r0[i] - share * (out[i] - self._f_lock[i]) / self._a_r[i])
                continue
            if self._rod_pressure_flow_law is not None and u[i] > self._eps:
                self._m2_extended[i] = True
            if not was_locked and standstill:
                # the machine locks in this step: its parameters at s_lock (5.20.2)
                leg.params = self._leg_params(i, float(s[i]))
            override = math.nan
            if not was_locked and standstill and self._cb is not None:
                # CB: lock pressure from the regulation at the lock instant (spec 4.3)
                override = leg.params.moving_target_rod_pressure_Pa(
                    leg.last_direction, float(f_cyl[i]))
            elif not was_locked and standstill and leg.last_direction is RodChamberMode.RET:
                override = float(self._p_ret[i])
            elif (not was_locked and standstill and self._rod_pressure_flow_law is not None
                  and leg.last_direction is RodChamberMode.EXT and self._m2_extended[i]):
                # M2 revision 5 (B, user decision 2026-11-07): the extend anchor keeps the part
                # of the tracked pressure above the extend target, p_r0 = max(p_ext + max(p_tr -
                # p*, 0), p_floor) (the floor in _lock_rod_pressure_Pa); M2 off keeps p_ext.
                # Only after an extension of this arming: the first lock of a leg that has not
                # moved keeps p_ext (its EXT direction and tracked p_ext are the initial values,
                # spec "first lock at arming = p_ext"; matters when p_ext > p*)
                target_Pa = leg.params.moving_target_rod_pressure_Pa(RodChamberMode.EXT,
                                                                     float(f_cyl[i]))
                override = float(self._p_ext[i]) + max(
                    float(leg.tracked_rod_pressure_Pa) - target_Pa, 0.0)
            f_before = (
                self._locked_force(i, float(c[i])) if was_locked
                else self._moving_force(i, float(s[i]), float(c[i]), t_s)
            )
            if was_locked:
                # C-S8-35 / H-S8-4 F1 (hydraulics 12.3, 12.7): the locked fast path above does
                # not step the machine, so its tracked pressure still holds the lock-instant
                # p_r0; the release step must start the moving pressure lag from the locked-law
                # rod pressure of the last call (continuity), not from p_r0
                leg.tracked_rod_pressure_Pa = float(self._last_p_r[i])
            leg.step(
                RodChamberLegInput(
                    time_s=float(t_s),
                    step_s=float(dt_s),
                    applied_speed_m_s=float(u[i]),
                    pad_deflection_m=float(c[i]),
                    pad_deflection_rate_m_s=0.0,
                    motor_position_m=float(s[i]),
                    cylinder_force_N=float(f_cyl[i]),
                    rod_pressure_at_lock_Pa=override,
                )
            )
            now_locked = leg.is_locked
            if now_locked and not was_locked:
                anchor = leg.anchor
                assert anchor is not None
                self._locked[i] = True
                self._c_lock[i] = float(c[i])
                self._s_lock[i] = float(s[i])
                self._f_lock[i] = f_before  # law value at the lock instant: no step in F
                self._k_h[i] = leg.params.head_stiffness_N_m
                self._k_r[i] = leg.params.rod_stiffness_N_m
                self._p_r0[i] = anchor.rod_pressure_Pa
                self._r0[i] = 0.0
                self._t_rel[i] = math.nan
                leg.anchor = dataclasses.replace(anchor, pad_force_N=max(f_before, 0.0),
                                                 deflection_m=float(c[i]))
            elif was_locked and not now_locked:
                locked_value = self._locked_force(i, float(c[i]))
                self._releases_of_last_call[i] = ReleaseStart(
                    start_pressure_Pa=float(self._last_p_r[i]),
                    drop_Pa=float(self._p_r0[i] - self._locked_rod_pressure_Pa(i, locked_value)))
                self._locked[i] = False
                self._r0[i] = locked_value - self.k2_N_m(i, float(s[i])) * float(c[i])
                self._t_rel[i] = float(t_s)
            if self._locked[i]:
                out[i] = self._locked_force(i, float(c[i]))
                share = self._k_r[i] / (self._k_h[i] + self._k_r[i])
                p_r[i] = max(self.p_floor_gauge_Pa,
                             self._p_r0[i] - share * (out[i] - self._f_lock[i]) / self._a_r[i])
            else:
                out[i] = self._moving_force(i, float(s[i]), float(c[i]), t_s)
                p_r[i] = leg.tracked_rod_pressure_Pa
        self._last_force = out
        self._last_p_r = p_r
        return out.copy()

    # --- pure evaluation (S8 seal-friction path, spec 2.5 / C-2) -----------------------------

    def oil_force_N(self, i: int, c_m: float) -> float:
        """Law value of leg ``i`` at compression ``c_m`` with the state of the last
        :meth:`spring_force_N` call (column coordinate and time of that call); state unchanged."""
        s = float(self._last_s[i])
        if not self._armed:
            return self.k2_N_m(i, s) * c_m
        if self._locked[i]:
            return self._locked_force(i, c_m)
        return self._moving_force(i, s, c_m, self._last_t)

    def oil_slope_N_m(self, i: int, c_m: float) -> float:
        """``dG/dc`` of leg ``i`` at ``c_m`` (piecewise constant: one knee while locked)."""
        if self._armed and self._locked[i]:
            knee_c = self.knee_force_N(i) / self.k1_lock(i)
            return self.k1_lock(i) if c_m - self._c_lock[i] < knee_c else self.k2_lock(i)
        return self.k2_N_m(i, float(self._last_s[i]))

    def refresh_readings(self, c_m: ArrayLike) -> None:
        """Re-evaluate the law value and the rod pressure at the final compression of the step
        (the seal-friction solve moved ``c`` after :meth:`spring_force_N`); state unchanged."""
        c = np.array(c_m, dtype=float).reshape(self._n)
        self._last_c = c.copy()
        out = np.array([self.oil_force_N(i, float(c[i])) for i in range(self._n)])
        if self._armed:
            for i in range(self._n):
                if self._locked[i]:
                    share = self._k_r[i] / (self._k_h[i] + self._k_r[i])
                    self._last_p_r[i] = max(self.p_floor_gauge_Pa,
                                            self._p_r0[i] - share * (out[i] - self._f_lock[i])
                                            / self._a_r[i])
        self._last_force = out

    def void_m(self) -> NDArray[np.float64]:
        """Per leg ``(dc - dc_knee)+`` of a locked leg at the last call: the oil the floor-limited
        rod spring did not get (M1c input, v5 spec 2.4); 0 while moving or disarmed."""
        out = np.zeros(self._n)
        if not self._armed or not hasattr(self, "_last_c"):
            return out
        for i in np.flatnonzero(self._locked):
            knee_c = self.knee_force_N(int(i)) / self.k1_lock(int(i))
            out[i] = max(float(self._last_c[i] - self._c_lock[i]) - knee_c, 0.0)
        return out

    def seed_release_pressure(self, i: int, pressure_Pa: float) -> None:
        """M1c retract opening (v5 spec 2.4): the moving pressure lag of the next release starts
        at ``pressure_Pa`` (the release step reads ``_last_p_r``)."""
        self._last_p_r[i] = pressure_Pa

    def shift_head(self, i: int, delta_m: float) -> None:
        """Head-only shift of ``delta_m = dV / A_p`` (CB discharge spec 4.2, M1c creep v5 spec
        2.4): the caller lowers ``s_ref`` by ``delta_m``; on a locked leg ``dc`` keeps the rod
        side, and the knee moves by ``k_h delta / k_out`` in ``c``
        (``c_lock -= delta (1 + k_h / k_out)``, ``F_lock -= k_h delta``). With ``k_out = inf``
        (oil-only law) the ratio is 0.0 and the shift is the plain ``c_lock -= delta``."""
        if self._armed and self._locked[i]:
            ratio = self._k_h[i] / self._k_out[i]
            self._c_lock[i] -= delta_m * (1.0 + ratio)
            self._f_lock[i] -= self._k_h[i] * delta_m

    def vent_rod(self, i: int, volume_m3: float) -> None:
        """CB rod-side discharge (spec 4.2): ``p_r0 -= k_r dV / A_ann^2``, ``F_lock += k_r dV /
        A_ann`` (locked legs only)."""
        if volume_m3 == 0.0 or not (self._armed and self._locked[i]):
            return
        self._p_r0[i] -= self._k_r[i] * volume_m3 / self._a_r[i] ** 2
        self._f_lock[i] += self._k_r[i] * volume_m3 / self._a_r[i]

    @property
    def annulus_area_m2(self) -> NDArray[np.float64]:
        return self._a_r.copy()

    @property
    def oil_only(self) -> bool:
        """``k_out = inf`` on every leg (oil law G of the seal-friction / CB path)."""
        return bool(np.all(np.isinf(self._k_out)))

    # --- snapshot ---------------------------------------------------------------------------

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        out = self._base_state_arrays()
        if self._rod_pressure_flow_law is not None:  # M2 r5 only; M2-off snapshots unchanged
            out[M2_EXTENDED_KEY] = self._m2_extended.copy()
        return out

    def _base_state_arrays(self) -> dict[str, NDArray[Any]]:
        machine = [leg.state_values() for leg in self._legs]
        keys = sorted(machine[0])
        return {
            "armed": np.array([self._armed]),
            "locked": self._locked.copy(),
            "c_lock_m": self._c_lock.copy(),
            "F_lock_N": self._f_lock.copy(),
            "k_h_N_m": self._k_h.copy(),
            "k_r_N_m": self._k_r.copy(),
            "p_r0_Pa": self._p_r0.copy(),
            "release_F0_N": self._r0.copy(),
            "release_t_s": self._t_rel.copy(),
            "s_lock_m": self._s_lock.copy(),
            "last_p_r_Pa": self._last_p_r.copy(),
            "machine": np.array([[m[k] for k in keys] for m in machine], dtype=float),
            "machine_param_s_m": np.array(
                [self._s_of_params(i) for i in range(self._n)], dtype=float
            ),
        }

    def _s_of_params(self, i: int) -> float:
        """Extension the machine parameters of leg ``i`` were built at (from ``k_h``)."""
        k_h = self._legs[i].params.head_stiffness_N_m
        return self._beta * self._a_p[i] / k_h - self._l0h

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"L2b rod-side state lacks {missing}")
        self._armed = bool(np.asarray(arrays["armed"]).reshape(-1)[0])
        self._releases_of_last_call = {}
        self._locked = np.array(arrays["locked"], dtype=bool).reshape(self._n)
        for name, attr in (("c_lock_m", "_c_lock"), ("F_lock_N", "_f_lock"),
                           ("k_h_N_m", "_k_h"), ("k_r_N_m", "_k_r"), ("p_r0_Pa", "_p_r0"),
                           ("release_F0_N", "_r0"), ("release_t_s", "_t_rel"), ("s_lock_m", "_s_lock"),
                           ("last_p_r_Pa", "_last_p_r")):
            setattr(self, attr, np.array(arrays[name], dtype=float).reshape(self._n))
        keys = sorted(self._legs[0].state_values())
        table = np.asarray(arrays["machine"], dtype=float)
        s_params = np.asarray(arrays["machine_param_s_m"], dtype=float).reshape(self._n)
        for i, leg in enumerate(self._legs):
            leg.params = self._leg_params(i, float(s_params[i]))
            leg.restore_values({k: float(v) for k, v in zip(keys, table[i], strict=True)})
        self._m2_extended = (np.array(arrays[M2_EXTENDED_KEY], dtype=bool).reshape(self._n)
                             if M2_EXTENDED_KEY in arrays else np.zeros(self._n, dtype=bool))

    def lock_table(self) -> dict[str, Any]:
        """Per-leg lock record for the run record (5.20.11 supplement 1: the judge first
        checks ``s_lock``, ``k_h``, ``k_r``, ``L_0r`` against the reference within 1e-6)."""
        return {
            "locked": self._locked.tolist(),
            "s_lock_m (s_ref at the lock instant)": self._s_lock.tolist(),
            "k_h_N_m": self._k_h.tolist(),
            "k_r_N_m": self._k_r.tolist(),
            "L0r_m": self._l0r.tolist(),
            "L0h_m": self._l0h,
            "p_r0_Pa": self._p_r0.tolist(),
            "F_lock_N": self._f_lock.tolist(),
            "c_lock_m": self._c_lock.tolist(),
            "knee_N": [self.knee_force_N(i) for i in range(self._n)],
        }

    def meta(self) -> dict[str, Any]:
        out = self._base_meta()
        if self._rod_pressure_flow_law is not None:  # key only with M2 (M2-off meta unchanged)
            out["lock_anchor_after_extend"] = LOCK_ANCHOR_AFTER_EXTEND_M2
        return out

    def _base_meta(self) -> dict[str, Any]:
        return {
            "law": "moving k2(s) c + R0 exp(-(t - t_rel)/tau); locked F_lock + k2 dc + "
                   "(k1 - k2) min(dc, dc_knee), k_h and k_r frozen at s_lock (dyn rev. 33 5.20.2)",
            "mechanics": str(self.mechanics),
            "armed": self._armed,
            "state_machine": "outrigger_sim.hydraulics.rod_chamber.RodChamberLeg (input c = "
                             "s_ref - s; closing delay 0; predictor off: explicit law)",
            "rod_dead_length_m": self._l0r.tolist(),
            "head_dead_length_m": self._l0h,
            "stroke_m": self._stroke,
            "k_out_N_m": [float(v) if math.isfinite(v) else "inf" for v in self._k_out],
            "oil_only": self.oil_only,
            "lock_valve": "pilot_check" if self._cb is None else "counterbalance",
            "p_r0_after_extend_Pa": self._p_ext.tolist(),
            "p_r0_after_retract_Pa": self._p_ret.tolist(),
            "p_floor_abs_Pa": self._p_floor_abs,
            "release_tau_s": self._tau,
            "lock_eps_m_s": self._eps,
        }


__all__ = ["STATE_KEYS", "L2bRodSide"]
