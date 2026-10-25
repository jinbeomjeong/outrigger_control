"""S8 V15 recorder for :class:`~outrigger_sim.chrono.l2b_model.L2bModel`: 1 ms block means of the
leg quantities and the V8(b) energy ledger of ``dynamics_model.md`` rev. 39 5.26.8.

New module (2026-10-25); it only reads the model, the actuator and the friction / rod-side law
objects (no state is changed). Hooks:

* a pre-hook inserted at ``model.actuator_hooks[0]`` keeps ``s_ref`` and ``u`` of the state time
  (the force-law hook advances ``s_ref`` for the next step);
* a post-hook appended to ``model.load_hooks`` (after the force-law hook) reads the step just
  taken: rod axial force ``F`` (``acting_force_N``), friction ``f`` (``acting_friction_N``), net
  reading ``G = F - f`` (``acting_pressure_force_N``), pad normal force ``N`` (``GetContactForce``
  along the floor normal), crawler normal force, rod pressure, piston ``s_p``, stick flags.

Block means: every quantity is averaged over :attr:`V15Recorder.block_s` of simulated time (the
block closes on a dt change too); ``t_s`` = block end time, ``lam_m`` = FL ``s_ref`` increment
since :meth:`V15Recorder.start_motion`.

Ledger (5.26.8, per step from the ledger start): ``E = E_kin + E_grav + U_lat + U_ax``,
``U_ax = sum [F_spr^2 / (2 k_out) + U_oil(c)]`` on the friction path (``c = s_ref - s_p``,
``F_spr = k_out (s_p - s)``), ``U_oil(c)`` on the S7 path (``c = s_ref - s``, the law's ``k`` with
``k_out`` in series), ``U_oil`` from :func:`outrigger_sim.verify.s8_v15.oil_energy_locked_J` /
``oil_energy_moving_J`` with the law's lock state; ``W_m = sum F_p,acting d s_ref``;
``W_L = sum 1/2 k_2'(s_ref) c^2 d s_ref`` (moving legs); ``D_visc = sum F_d,acting (d s_ref - d s)
+ sum c_lat v_n . d d`` (explicit dashpots: the force set at the hook acts in the next step),
recorded also split into ``D_visc_ax_J`` (axial dashpot) and ``D_visc_lat_J`` (lateral bushing)
(rev. 42 5.29.7 L-1, 2026-10-25; ``D_visc_J`` = the same sum as before, added term by term);
``D_f`` = the friction element's own sum; ``W_res`` = - work of the release residual
``R = G - k_2 c`` of a released leg (midpoint); ``W_switch`` = energy jump of the law switch
locked -> moving (the moving form drops the locked anchor). Private attributes of the law objects
are read (``_oil``, ``_armed``, ``_locked``, ``_c_lock``, ``_f_lock``) because no public view
exists; see ``LAW_ATTRS``.

Units SI; per-leg arrays in LEG_ORDER.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.verify.s8_v15 import oil_energy_locked_J, oil_energy_moving_J

LOCK_EPS_M_S = 1.0e-6
LAW_ATTRS = ("_oil", "_armed", "_locked", "_c_lock", "_f_lock")
"""Private attributes read (no public view in ``L2bForceActuator`` / ``L2bRodSide``)."""

BLOCK_KEYS_4 = ("s_ref_m", "s_m", "F_N", "f_N", "Fp_N", "s_p_m", "N_N", "p_r_Pa",
                "head_reading_N", "stuck_frac", "u_m_s")
LEDGER_KEYS = ("E_kin_J", "E_grav_J", "U_lat_J", "U_ax_J", "D_visc_J", "D_visc_ax_J",
               "D_visc_lat_J", "D_f_J", "W_m_J", "W_L_J", "W_res_J", "W_switch_J")


def _v3(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


class V15Recorder:
    """Block-mean recorder and V8(b) ledger (module docstring)."""

    def __init__(self, model: Any, *, block_s: float = 1.0e-3, ledger: bool = True) -> None:
        self.model = model
        self.act = model.actuator
        self.block_s = float(block_s)
        self.ledger_on = bool(ledger)
        params = model.params
        a = params.l2b.actuator
        self.c_lock = np.asarray(a.damping_lock_N_s_m, dtype=float)
        self.c_move = np.asarray(a.damping_moving_N_s_m, dtype=float)
        if model.damping == "zero":
            self.c_lock = np.zeros(4)
            self.c_move = np.zeros(4)
        elif model.damping != "rev33":
            raise ValueError(f"ledger needs damping 'rev33' or 'zero', got {model.damping!r}")
        self.a_ann = np.asarray(params.l2b.rod_side.annulus_area_m2, dtype=float)
        self.k_lat = np.asarray(model.bushings.values.stiffness_N_m, dtype=float)
        self.c_lat = np.asarray(model.bushings.values.damping_N_s_m, dtype=float)
        self.sf = self.act.seal_friction
        self.friction_path = self.sf is not None
        self.oil = getattr(self.act, "_oil", None) if self.friction_path else self.act.rod_side
        if self.friction_path:
            k_out = []
            for i in range(4):
                fl = 1.0 / a.k_rod_N_m[i] + 1.0 / a.frame_stiffness_N_m + 1.0 / a.k_concrete_N_m
                k_out.append(1.0 / fl)
            self.k_out = np.array(k_out)
        else:
            self.k_out = np.full(4, np.inf)
        g = model.system.GetGravitationalAcceleration()
        self.g = np.array([g.x, g.y, g.z], dtype=float)
        self.bodies = list(model.bodies)
        self.mass = np.array([b.GetMass() for b in self.bodies], dtype=float)
        self.inertia = []
        for b in self.bodies:
            xx, xy = b.GetInertiaXX(), b.GetInertiaXY()
            self.inertia.append(np.array([[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z],
                                          [xy.y, xy.z, xx.z]], dtype=float))
        self.recording = False
        self.lam0: float | None = None
        self.rows: dict[str, list[Any]] = {}
        self._sums: dict[str, NDArray[np.float64]] = {}
        self._n_block = 0
        self._block_t0: float | None = None
        self._block_dt: float | None = None
        self._pre_sref = np.zeros(4)
        self._pre_u = np.zeros(4)
        self._ledger_started = False
        self._prev: dict[str, Any] = {}
        self.cum = dict.fromkeys(("D_visc_J", "D_visc_ax_J", "D_visc_lat_J", "W_m_J", "W_L_J",
                                  "W_res_J", "W_switch_J"), 0.0)
        self.ledger_steps = 0
        self.switch_events: list[dict[str, Any]] = []
        model.actuator_hooks.insert(0, self._pre)
        model.load_hooks.append(self._post)

    # --- control ------------------------------------------------------------------------

    def start_recording(self) -> None:
        self.recording = True

    def start_motion(self) -> None:
        """FL ``s_ref`` origin of ``lam`` (call right before the FL command is set)."""
        self.lam0 = float(self.act.reference.s_ref_m[0])

    def start_ledger(self) -> None:
        """Ledger baseline at the next step (call before the motion starts)."""
        self._ledger_started = False
        self._prev = {}
        for k in self.cum:
            self.cum[k] = 0.0
        self.ledger_on = True
        self._ledger_armed = True

    # --- hooks --------------------------------------------------------------------------

    def _pre(self, model: Any, dt_s: float) -> None:
        ref = self.act.reference
        self._pre_sref = ref.s_ref_m.copy()
        self._pre_u = ref.u_applied_m_s.copy()

    def _law_state(self, i: int) -> tuple[Any, ...]:
        law = self.oil
        if law is None or not getattr(law, "_armed", False) or not bool(law._locked[i]):
            return ("moving",)
        return ("locked", float(law._c_lock[i]), float(law._f_lock[i]), float(law.k1_lock(i)),
                float(law.k2_lock(i)), float(law.knee_force_N(i) / law.k1_lock(i)))

    def _k2(self, i: int, s_ref: float) -> float:
        law = self.oil
        if law is None:  # S7 path without the rod-side law: k_ax(s_ref)
            v = np.full(4, s_ref)
            return float(self.act.axial_stiffness_N_m(v)[i])
        return float(law.k2_N_m(i, s_ref))

    def _u_oil(self, state: tuple[Any, ...], i: int, s_ref: float, c: float) -> float:
        if state[0] == "moving":
            return oil_energy_moving_J(self._k2(i, s_ref), c)
        _, c_lock, f_lock, k1, k2, knee_c = state
        return oil_energy_locked_J(k1_N_m=k1, k2_N_m=k2, knee_c_m=knee_c, c_lock_m=c_lock,
                                   F_lock_N=f_lock, c_m=c)

    def _post(self, model: Any, dt_s: float) -> None:
        if not self.recording:
            return
        act = self.act
        motors = model.motors
        s = np.array([m.GetMotorPos() for m in motors], dtype=float)
        ds = np.array([m.GetMotorPosDt() for m in motors], dtype=float)
        F = act.acting_force_N
        f = act.acting_friction_N
        fp = F - f
        n_hat = model.floor_normal_world()
        N = np.array([_v3(leg.GetContactForce()) @ n_hat for leg in model.legs], dtype=float)
        crawler = float(_v3(model.superstructure.GetContactForce()) @ n_hat)
        rs = act.rod_side
        p_r = (rs.rod_pressure_Pa if (rs is not None and rs.armed) else np.zeros(4))
        sp = act.acting_piston_m if self.friction_path else act.stroke_true_m(s, F)
        stuck = (self.sf.stuck.astype(float) if self.friction_path else np.zeros(4))
        values4 = {"s_ref_m": self._pre_sref, "s_m": s, "F_N": F, "f_N": f, "Fp_N": fp,
                   "s_p_m": sp, "N_N": N, "p_r_Pa": p_r, "head_reading_N": fp + p_r * self.a_ann,
                   "stuck_frac": stuck, "u_m_s": self._pre_u}
        scalars = {"crawler_N": crawler}
        if self.ledger_on and getattr(self, "_ledger_armed", False):
            scalars.update(self._ledger_step(model, s, ds, fp))
        self._accumulate(model, dt_s, values4, scalars)

    def _ledger_step(self, model: Any, s: NDArray[np.float64], ds: NDArray[np.float64],
                     fp: NDArray[np.float64]) -> dict[str, float]:
        e_kin = 0.0
        e_grav = 0.0
        for b, m, inertia in zip(self.bodies, self.mass, self.inertia, strict=True):
            v = _v3(b.GetPosDt())
            w = _v3(b.GetAngVelLocal())
            e_kin += 0.5 * m * float(v @ v) + 0.5 * float(w @ inertia @ w)
            e_grav -= m * float(self.g @ _v3(b.GetPos()))
        d = model.bushings.displacement_m()
        vl = model.bushings.velocity_m_s()
        u_lat = float(0.5 * np.sum(self.k_lat[:, None] * d * d))
        s_ref = self._pre_sref.copy()
        if self.friction_path:
            sp = self.sf.s_p.copy()
            c = s_ref - sp
            u_out = 0.5 * self.k_out * (sp - s) ** 2
        else:
            c = s_ref - s
            u_out = np.zeros(4)
        states = [self._law_state(i) for i in range(4)]
        u_oil = np.array([self._u_oil(states[i], i, float(s_ref[i]), float(c[i]))
                          for i in range(4)])
        resid = np.zeros(4)
        if self.oil is not None:
            for i in range(4):
                if states[i][0] == "moving" and getattr(self.oil, "_armed", False):
                    resid[i] = self.oil.oil_force_N(i, float(c[i])) - self._k2(i, float(s_ref[i])) * c[i]
        u_new = self.act.reference.u_applied_m_s
        c_coef = np.where(np.abs(u_new) <= LOCK_EPS_M_S, self.c_lock, self.c_move)
        fd_next = c_coef * (u_new - ds)
        p = self._prev
        if p:
            d_sref = s_ref - p["s_ref"]
            d_s = s - p["s"]
            self.cum["W_m_J"] += float(np.sum(fp * d_sref))
            d_ax = float(np.sum(p["fd_next"] * (d_sref - d_s)))
            d_lat = float(np.sum(self.c_lat[:, None] * p["vl"] * (d - p["d"])))
            self.cum["D_visc_J"] += d_ax  # term by term: D_visc_J bit-identical to before
            self.cum["D_visc_J"] += d_lat
            self.cum["D_visc_ax_J"] += d_ax
            self.cum["D_visc_lat_J"] += d_lat
            for i in range(4):
                if d_sref[i] != 0.0 and states[i][0] == "moving" and p["states"][i][0] == "moving":
                    sm = 0.5 * (s_ref[i] + p["s_ref"][i])
                    h = 1.0e-6
                    dk = (self._k2(i, sm + h) - self._k2(i, sm - h)) / (2.0 * h)
                    cm = 0.5 * (c[i] + p["c"][i])
                    self.cum["W_L_J"] += 0.5 * dk * cm * cm * float(d_sref[i])
                if states[i] != p["states"][i]:
                    old = self._u_oil(p["states"][i], i, float(s_ref[i]), float(c[i]))
                    jump = float(u_oil[i] - old)
                    self.cum["W_switch_J"] += jump
                    self.switch_events.append({"t_s": float(model.system.GetChTime()), "leg": i,
                                               "from": p["states"][i][0], "to": states[i][0],
                                               "jump_J": jump})
            self.cum["W_res_J"] -= float(np.sum(0.5 * (resid + p["resid"]) * (c - p["c"])))
        self._prev = {"s_ref": s_ref, "s": s.copy(), "c": c.copy(), "d": d, "vl": vl,
                      "fd_next": fd_next, "states": states, "resid": resid}
        self.ledger_steps += 1
        d_f = float(np.sum(self.sf.dissipation_J)) if self.friction_path else 0.0
        return {"E_kin_J": e_kin, "E_grav_J": e_grav, "U_lat_J": u_lat,
                "U_ax_J": float(np.sum(u_out) + np.sum(u_oil)), "D_f_J": d_f, **self.cum}

    # --- blocks -------------------------------------------------------------------------

    def _accumulate(self, model: Any, dt_s: float, values4: dict[str, Any],
                    scalars: dict[str, float]) -> None:
        t = float(model.system.GetChTime())
        if self._block_t0 is None:
            self._block_t0 = t - dt_s
            self._block_dt = dt_s
        elif self._block_dt != dt_s:
            self.flush()
            self._block_t0 = t - dt_s
            self._block_dt = dt_s
        for k, v in values4.items():
            arr = np.asarray(v, dtype=float)
            self._sums[k] = self._sums.get(k, 0.0) + arr
            if k in ("N_N",):
                mn = self._sums.get("N_min_N")
                self._sums["N_min_N"] = arr.copy() if mn is None else np.minimum(mn, arr)
        for k, v in scalars.items():
            if k in LEDGER_KEYS:
                self._sums[k] = np.asarray(v, dtype=float)  # cumulative: keep the block end value
            else:
                self._sums[k] = self._sums.get(k, 0.0) + np.asarray(v, dtype=float)
        self._n_block += 1
        self._t_last = t
        if t - self._block_t0 >= self.block_s - 1e-12:
            self.flush()
            self._block_t0 = t

    def flush(self) -> None:
        if self._n_block == 0:
            return
        n = self._n_block
        row: dict[str, Any] = {"t_s": self._t_last, "dt_s": float(self._block_dt or math.nan),
                               "n_steps": n}
        for k, v in self._sums.items():
            if k in LEDGER_KEYS or k == "N_min_N":
                row[k] = np.array(v, copy=True)
            else:
                row[k] = np.asarray(v) / n
        row["lam_m"] = (row["s_ref_m"][0] - self.lam0) if self.lam0 is not None else 0.0
        for k, v in row.items():
            self.rows.setdefault(k, []).append(np.array(v, copy=True))
        self._sums = {}
        self._n_block = 0

    def arrays(self) -> dict[str, NDArray[Any]]:
        self.flush()
        out = {}
        n = len(self.rows.get("t_s", []))
        for k, v in self.rows.items():
            if len(v) == n:
                out[k] = np.asarray(v)
            else:  # ledger columns start later: pad the head with NaN
                pad = [np.full_like(v[0], np.nan)] * (n - len(v))
                out[k] = np.asarray(pad + v)
        return out

    def last_block(self, key: str) -> NDArray[np.float64] | None:
        v = self.rows.get(key)
        return None if not v else np.asarray(v[-1])


__all__ = ["LAW_ATTRS", "LEDGER_KEYS", "V15Recorder"]
