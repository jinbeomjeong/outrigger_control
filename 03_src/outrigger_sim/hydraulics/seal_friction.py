"""Cylinder seal friction of the L2b legs (engine independent, no pychrono).

Specification ``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 2 (hydraulics-expert,
2026-10-24); user decisions U-S8-H1..H4 (2026-10-24): the level ``L`` is the Coulomb limit of the
**front** legs (static = kinetic), constant in a run (nominal 4 kN, sensitivity 0 / 2 / 4 / 8 kN);
rear legs ``0.833 L``; pressure dependence, static > kinetic and a seal stick stiffness are
sensitivity options only; L1 has no seal friction.

Model (2.1): massless piston, Coulomb friction ``f`` parallel to the oil spring only, in series
with the outer path ``k_out = series(k_rod, k_frame[, k_concrete])``::

    F = k_out (s_p - s),   F = G(s_ref - s_p) + f,   |f| <= F_s

``s`` = link displacement, ``s_p`` = piston position (stroke sensor truth), ``G`` = oil law
(``L2bRodSide`` with ``k_out = inf``: head column, rod column below the knee, release residual),
``f`` + = pushes the piston towards extension. Pressure force (two-sensor net force truth)
``F_p = F - f``.

Step (2.5, explicit, once per hook and leg): trial ``c_tr = s_ref - s_p^{n-1}``; stick test
``f_tr = k_out (s_p^{n-1} - s) - G(c_tr)``; stuck if ``|f_tr| <= r_s F_s`` (was stuck) or
``<= F_s`` (was sliding), else ``f = sign(f_tr) F_s`` and ``s_p`` solves
``k_out (s_p - s) - G(s_ref - s_p) - f = 0`` (piecewise-linear ``G``: exact segment solve, at most
a few re-anchorings). Optional stick stiffness ``k_st`` (2.5 last paragraph): elastic trial with
the stick point ``w``, ``f = k_st (w - s_p)``; on sliding ``w = s_p + f / k_st``.

Dissipation (V8(b)): ``-f (s_p^n - s_p^{n-1})`` on sliding steps (rigid stick), ``-f dw`` with
``k_st`` (plus the stored seal energy ``f^2 / (2 k_st)``, :meth:`SealFriction.stored_energy_J`).

Pressure option (2.4, ``pressure_model = "seal_geometry"``): ``F_s,i = L_i phi(p_h, p_r) /
phi(p_ref,h, p_ref,r)``, ``phi = F0 (D + d) / (D_0 + d_0) + kappa (pi D |p_h - p_r| + pi d p_r)``
with the pressures of the previous hook (explicit).

Units SI (gauge pressures); per-leg arrays in the order given.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

STATE_KEYS = (
    "armed", "s_p_m", "f_N", "stuck", "w_m", "dissipation_J", "slip_starts", "F_s_N",
    "solver_reanchors",
)

SOLVER_MAX_ANCHORS = 6

CHATTER_WINDOW_S = 1.0e-3
"""S8-A3 (``dynamics_model.md`` 5.26.10): a stick or slide stay shorter than this between two
transitions counts as one band-edge chatter (stick <-> slip round trip inside 1 ms)."""


def leg_limits_N(level_N: float, rear_scale: float, leg_names: Sequence[str]) -> NDArray[np.float64]:
    """Per-leg Coulomb limit: front (``F*``) = level, rear (``R*``) = level x rear_scale."""
    out = []
    for name in leg_names:
        if name.startswith("F"):
            out.append(float(level_N))
        elif name.startswith("R"):
            out.append(float(level_N) * float(rear_scale))
        else:
            raise ValueError(f"leg name {name!r} is neither front (F*) nor rear (R*)")
    return np.array(out, dtype=float)


def solve_piston_m(s: float, s_ref: float, k_out: float, extra_k: float, extra_const: float,
                   oil_force: Callable[[float], float], oil_slope: Callable[[float], float],
                   c_start: float) -> tuple[float, int]:
    """Root of ``(k_out + extra_k) s_p - k_out s - extra_const - G(s_ref - s_p) = 0``.

    ``G`` piecewise linear and non-decreasing: anchor the line of the segment at ``c``, solve,
    re-anchor on the segment of the new ``c`` until the slope agrees (exact). Returns
    (``s_p``, number of re-anchorings)."""
    c = c_start
    s_p = s_ref - c
    for k in range(SOLVER_MAX_ANCHORS):
        g = oil_force(c)
        kg = oil_slope(c)
        s_p = (k_out * s + extra_const + g + kg * (s_ref - c)) / (k_out + extra_k + kg)
        c_new = s_ref - s_p
        if oil_slope(c_new) == kg:
            return s_p, k
        c = c_new
    return s_p, SOLVER_MAX_ANCHORS


class SealFriction:
    """Seal friction state of all legs (module docstring).

    Args:
        limits_N: Coulomb limit per leg at the reference pressures (level x front/rear factor).
        k_out_N_m: Outer path per leg.
        static_ratio: ``r_s`` (>= 1; 1 = static = kinetic).
        stick_stiffness_N_m: ``k_st``; 0 = rigid stick.
        pressure_model: ``"constant"`` or ``"seal_geometry"``.
        seal: For ``seal_geometry``: dict with ``kappa_N_per_m_Pa``, ``F0_N``,
            ``F0_seal_diameter_sum_m``, ``p_ref_head_Pa`` (per leg), ``p_ref_rod_Pa``,
            ``bore_diameter_m`` and ``rod_diameter_m`` (per leg).
    """

    def __init__(self, limits_N: ArrayLike, k_out_N_m: ArrayLike, *, static_ratio: float = 1.0,
                 stick_stiffness_N_m: float = 0.0, pressure_model: str = "constant",
                 seal: Mapping[str, Any] | None = None) -> None:
        self._limits = np.array(limits_N, dtype=float).reshape(-1)
        n = self._limits.size
        self._n = n
        self._k_out = np.array(k_out_N_m, dtype=float).reshape(n)
        if np.any(self._limits < 0.0) or np.any(self._k_out <= 0.0):
            raise ValueError("limits >= 0 and k_out > 0 required")
        self.static_ratio = float(static_ratio)
        if self.static_ratio < 1.0:
            raise ValueError("static_ratio must be >= 1")
        self.k_st = float(stick_stiffness_N_m)
        if self.k_st < 0.0:
            raise ValueError("stick_stiffness_N_m must be >= 0 (0 = rigid)")
        self.pressure_model = str(pressure_model)
        if self.pressure_model not in ("constant", "seal_geometry"):
            raise ValueError(f"unknown pressure model {pressure_model!r}")
        self._seal = None
        if self.pressure_model == "seal_geometry":
            if seal is None:
                raise ValueError("seal_geometry needs the seal parameters")
            self._seal = {k: (np.array(v, dtype=float).reshape(n) if np.ndim(v) else float(v))
                          for k, v in seal.items()}
            self._phi_ref = self._phi(self._seal["p_ref_head_Pa"],
                                      np.full(n, self._seal["p_ref_rod_Pa"]))
        self.reset()

    # --- state ---------------------------------------------------------------------------

    def reset(self) -> None:
        n = self._n
        self.armed = False
        self.s_p = np.full(n, np.nan)
        self.f = np.zeros(n)
        self.stuck = np.ones(n, dtype=bool)
        self.w = np.full(n, np.nan)
        self.dissipation_J = np.zeros(n)
        self.slip_starts = np.zeros(n, dtype=np.int64)
        self.F_s = self._limits.copy()
        self.solver_reanchors = np.zeros(n, dtype=np.int64)
        self.chatter_count = np.zeros(n, dtype=np.int64)
        """S8-A3: stick / slide stays < :data:`CHATTER_WINDOW_S` between two transitions."""
        self.stay_start_t = np.full(n, np.nan)
        """Time of the last stick <-> slide transition per leg (NaN = none since arming)."""

    def arm(self, piston_m: ArrayLike) -> None:
        """Start (2.6): ``s_p`` given, ``f = 0``, stuck (ASSUMPTION: ``f = 0`` at arming)."""
        self.s_p = np.array(piston_m, dtype=float).reshape(self._n)
        self.f = np.zeros(self._n)
        self.stuck = np.ones(self._n, dtype=bool)
        self.w = self.s_p.copy()
        self.stay_start_t = np.full(self._n, np.nan)
        self.armed = True

    @property
    def n_legs(self) -> int:
        return self._n

    @property
    def limits_N(self) -> NDArray[np.float64]:
        """Limits at the reference pressures (constant model: the limits in use)."""
        return self._limits.copy()

    @property
    def active(self) -> bool:
        """Any non-zero limit (a zero level keeps the friction at 0 everywhere)."""
        return bool(np.any(self._limits > 0.0))

    # read-only views with unit suffixes (names of chrono/s8_plant_adapter)
    @property
    def f_N(self) -> NDArray[np.float64]:
        """Friction on the piston ``f`` [N] (+ = pushes the piston outward)."""
        return self.f.copy()

    @property
    def s_p_m(self) -> NDArray[np.float64]:
        """Piston position ``s_p`` [m] (stroke sensor truth)."""
        return self.s_p.copy()

    @property
    def F_s_N(self) -> NDArray[np.float64]:
        """Coulomb limit in use per leg [N]."""
        return self.F_s.copy()

    @property
    def slip_transitions(self) -> NDArray[np.int64]:
        """Stuck -> sliding transitions per leg since arming / reset."""
        return self.slip_starts.copy()

    def stored_energy_J(self) -> NDArray[np.float64]:
        """Seal spring energy ``f^2 / (2 k_st)`` (0 for the rigid stick)."""
        if self.k_st == 0.0:
            return np.zeros(self._n)
        return self.f**2 / (2.0 * self.k_st)

    # --- pressure option -------------------------------------------------------------------

    def _phi(self, p_h: NDArray[np.float64], p_r: NDArray[np.float64]) -> NDArray[np.float64]:
        s = self._seal
        assert s is not None
        d_sum = s["bore_diameter_m"] + s["rod_diameter_m"]
        return (s["F0_N"] * d_sum / s["F0_seal_diameter_sum_m"]
                + s["kappa_N_per_m_Pa"] * (math.pi * s["bore_diameter_m"] * np.abs(p_h - p_r)
                                           + math.pi * s["rod_diameter_m"] * p_r))

    def update_limits(self, head_pressure_Pa: ArrayLike | None,
                      rod_pressure_Pa: ArrayLike | None) -> None:
        """``F_s`` for this step (constant model: unchanged)."""
        if self._seal is None or head_pressure_Pa is None:
            return
        p_h = np.array(head_pressure_Pa, dtype=float).reshape(self._n)
        p_r = (np.zeros(self._n) if rod_pressure_Pa is None
               else np.array(rod_pressure_Pa, dtype=float).reshape(self._n))
        self.F_s = self._limits * self._phi(p_h, p_r) / self._phi_ref

    # --- step ------------------------------------------------------------------------------

    def step(self, s_m: ArrayLike, s_ref_m: ArrayLike,
             oil_force: Callable[[int, float], float],
             oil_slope: Callable[[int, float], float],
             *, enabled: bool = True, t_s: float | None = None) -> NDArray[np.float64]:
        """One hook (2.5 steps 2-3, 6). Returns the spring part ``F_spr = k_out (s_p - s)``.

        ``oil_force(i, c)`` / ``oil_slope(i, c)``: pure oil law of leg ``i`` at the oil
        compression ``c`` (state already advanced to this hook). ``enabled`` False = limit 0
        (before arming the rod-side law, V12 rule). ``t_s`` (hook time) feeds the S8-A3
        band-edge chatter count only (None = not counted); the law does not use it."""
        s = np.array(s_m, dtype=float).reshape(self._n)
        sr = np.array(s_ref_m, dtype=float).reshape(self._n)
        if not self.armed:
            raise RuntimeError("seal friction not armed")
        out = np.empty(self._n)
        for i in range(self._n):
            k_out = float(self._k_out[i])
            sp0 = float(self.s_p[i])
            si, sri = float(s[i]), float(sr[i])
            lim_slide = float(self.F_s[i]) if enabled else 0.0
            lim_stick = self.static_ratio * lim_slide if self.stuck[i] else lim_slide

            def g(c: float, i: int = i) -> float:
                return oil_force(i, c)

            def dg(c: float, i: int = i) -> float:
                return oil_slope(i, c)

            c_tr = sri - sp0
            if self.k_st == 0.0:
                f_tr = k_out * (sp0 - si) - g(c_tr)
                if abs(f_tr) <= lim_stick:
                    sp, f, stuck = sp0, f_tr, True
                else:
                    f = math.copysign(lim_slide, f_tr)
                    sp, nre = solve_piston_m(si, sri, k_out, 0.0, f, g, dg, c_tr)
                    self.solver_reanchors[i] += nre
                    stuck = False
                    self.dissipation_J[i] += -f * (sp - sp0)
            else:
                w0 = float(self.w[i])
                sp_tr, nre = solve_piston_m(si, sri, k_out, self.k_st, self.k_st * w0, g, dg, c_tr)
                self.solver_reanchors[i] += nre
                f_tr = self.k_st * (w0 - sp_tr)
                if abs(f_tr) <= lim_stick:
                    sp, f, stuck = sp_tr, f_tr, True
                else:
                    f = math.copysign(lim_slide, f_tr)
                    sp, nre = solve_piston_m(si, sri, k_out, 0.0, f, g, dg, c_tr)
                    self.solver_reanchors[i] += nre
                    w_new = sp + f / self.k_st
                    self.dissipation_J[i] += -f * (w_new - w0)
                    self.w[i] = w_new
                    stuck = False
            if self.stuck[i] and not stuck:
                self.slip_starts[i] += 1
            if t_s is not None and bool(self.stuck[i]) != stuck:
                t0 = float(self.stay_start_t[i])
                if math.isfinite(t0) and float(t_s) - t0 <= CHATTER_WINDOW_S + 1e-12:
                    self.chatter_count[i] += 1
                self.stay_start_t[i] = float(t_s)
            self.s_p[i], self.f[i], self.stuck[i] = sp, f, stuck
            out[i] = k_out * (sp - si)
        return out

    # --- record / snapshot -----------------------------------------------------------------

    def record(self) -> dict[str, Any]:
        return {"armed": self.armed, "s_p_m": self.s_p.tolist(), "f_N": self.f.tolist(),
                "stuck": self.stuck.tolist(), "F_s_N": self.F_s.tolist(),
                "dissipation_J": self.dissipation_J.tolist(),
                "stored_energy_J": self.stored_energy_J().tolist(),
                "slip_starts": self.slip_starts.tolist(),
                "solver_reanchors": self.solver_reanchors.tolist(),
                "band_edge_chatter": self.chatter_count.tolist(),
                "band_edge_chatter_window_s": CHATTER_WINDOW_S}

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        return {"armed": np.array([self.armed]), "s_p_m": self.s_p.copy(), "f_N": self.f.copy(),
                "stuck": self.stuck.copy(), "w_m": self.w.copy(),
                "dissipation_J": self.dissipation_J.copy(), "slip_starts": self.slip_starts.copy(),
                "F_s_N": self.F_s.copy(), "solver_reanchors": self.solver_reanchors.copy(),
                "chatter_count": self.chatter_count.copy(),
                "stay_start_t_s": self.stay_start_t.copy()}

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        missing = [k for k in STATE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"seal friction state lacks {missing}")
        n = self._n
        self.armed = bool(np.asarray(arrays["armed"]).reshape(-1)[0])
        self.s_p = np.array(arrays["s_p_m"], dtype=float).reshape(n)
        self.f = np.array(arrays["f_N"], dtype=float).reshape(n)
        self.stuck = np.array(arrays["stuck"], dtype=bool).reshape(n)
        self.w = np.array(arrays["w_m"], dtype=float).reshape(n)
        self.dissipation_J = np.array(arrays["dissipation_J"], dtype=float).reshape(n)
        self.slip_starts = np.array(arrays["slip_starts"], dtype=np.int64).reshape(n)
        self.F_s = np.array(arrays["F_s_N"], dtype=float).reshape(n)
        self.solver_reanchors = np.array(arrays["solver_reanchors"], dtype=np.int64).reshape(n)
        # S8-A3 bookkeeping (absent in snapshots written before it: count from 0)
        self.chatter_count = (np.array(arrays["chatter_count"], dtype=np.int64).reshape(n)
                              if "chatter_count" in arrays else np.zeros(n, dtype=np.int64))
        self.stay_start_t = (np.array(arrays["stay_start_t_s"], dtype=float).reshape(n)
                             if "stay_start_t_s" in arrays else np.full(n, np.nan))

    def meta(self) -> dict[str, Any]:
        return {
            "model": "Coulomb, massless piston, parallel to the oil spring, series k_out "
                     "(S8 spec 2.1); explicit return mapping per hook (2.5)",
            "limits_N": self._limits.tolist(),
            "static_ratio": self.static_ratio,
            "stick_stiffness_N_m": self.k_st if self.k_st > 0.0 else "rigid",
            "pressure_model": self.pressure_model,
            "k_out_N_m": self._k_out.tolist(),
            "initial_state": "f = 0, stuck at arming (ASSUMPTION, spec 2.6)",
        }


__all__ = ["STATE_KEYS", "SealFriction", "leg_limits_N", "solve_piston_m"]
