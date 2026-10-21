"""Mechanical energy of the L1 model: S3 V8(a) (:class:`EnergyMeter`) and the S4 V8(b) energy
budget with the seven ``energy.*`` Record terms (:class:`EnergyBudget`).

``dynamics_model.md`` 5 V8: ``E`` = kinetic + gravity + ``sum 1/2 k_n delta^2`` (SMC Hooke
contacts: pad spheres and crawler spheres) + ``sum 1/2 k_t |d|^2`` (ground bushings, after the
return mapping).

S3 (:class:`EnergyMeter`, unchanged since S3): with the contact damping ``g_n`` = 0 the SMC
Hooke force is ``k_n delta``, so the contact spring energy is taken as ``F^2 / (2 k_n)`` from
the contact force Chrono applied (Bullet's float32 distance included) and ``k_n`` as Chrono
stores it (float32, R5); :meth:`EnergyMeter.contact_energy_geometric` gives the double-precision
geometric alternative. Motors are locked or moving rigidly: no spring energy. Gravity
potential ``-sum m g . p_cog``.

S4 (:class:`EnergyBudget`, ``chrono_build_plan.md`` S4 / 3.3 ``energy.*``; V8(b)): the seven
terms in J, the last three accumulated from :meth:`EnergyBudget.reset`:

* ``kinetic`` ``sum 1/2 m |v|^2 + 1/2 w^T I w`` (superstructure + 4 leg moving parts, COG
  frames, ``I`` in body axes);
* ``gravity`` ``-sum m g . p_cog`` (gravity read at reset; it must stay constant);
* ``contact_spring`` ``sum 1/2 k_n delta^2`` of the pad spheres, ``delta`` geometric (ball
  centre to the floor plane, double precision; ``k_n`` as Chrono stores it, float32). Crawler
  spheres are not included: the budget is for the machine on its pads and
  :attr:`EnergyBudget.crawler_contact_max_N` records any crawler contact force;
* ``bushing_spring`` ``sum 1/2 k_t |d|^2`` with ``d`` the in-plane offset of the force point
  (ball centre) from the anchor set by the last return mapping (plan: "after the return
  mapping");
* ``dissipated_viscous`` ``D_visc = int (c_n delta_dot^2 + c_t |d_dot|^2) dt``. Pads: the SMC
  Hooke damping ``c_n = g_n m_eff`` (``g_n`` float32, ``m_eff`` = moving part with the
  1e9 kg floor) acting with the step-start velocity (SMC contact is explicit), work over the
  step ``c_n delta_dot_n (delta_{n+1} - delta_n)``; Chrono's clip (no pulling force) is
  reproduced. Bushings: ``c_t`` = **actual** value = 2 x the Chrono input (R7) while the
  damping is on, with the end-of-step velocity (bushing loads are implicit);
* ``dissipated_slip`` ``D_slip = sum 1/2 k_t (|d_trial|^2 - |d|^2)`` over every yielding
  return mapping (ground-bushing accumulator; a pad with ``N = 0`` maps ``d`` to 0, so the
  spring energy left at lift-off is included);
* ``motor_work`` ``W_m = int F_cyl ds`` per step ``F_cyl,n+1 (s_n+1 - s_n)`` (``GetMotorForce``,
  + = pushing the pad down = extending; ``GetMotorPos`` = extension).

Residual ``R = (E_mech - E_mech,0) + D_visc + D_slip - W_m`` with ``E_mech`` = the first
four terms. Two known discrete contributions are recorded beside it
(:class:`EnergyBudgetTerms`): the anchor-lag term (Chrono uses the anchor set by the hook
two steps back, ``ground_bushing`` "one-step lag", while ``bushing_spring`` uses the newest)
``-sum k_t (a_new - a_used) . delta_p`` and the implicit-Euler bushing term
``-sum 1/2 k_t |delta_p|^2``; both scale with ``dt``. Two more read-only diagnostics close
the rest (dyn rev. 19): the kinetic share of the Euler step ``-sum 1/2 dv^T M dv`` (every
body, rotation in body axes) and the explicit share of the SMC pad springs
``+sum 1/2 k_n d_delta^2``. The anchor and damping that act in a step are tracked with the ground-bushing rule: a step that starts "not updated" (bushing
created or removed by the last hook) uses the newest values, otherwise those before the last
hook.

Units SI (J, m, s), world frame Z-up. Read between steps only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.chrono.contact import crawler_material_values, pad_material_values


@dataclass(frozen=True)
class EnergyTerms:
    """One energy sample [J]."""

    t_s: float
    kinetic: float
    gravity: float
    pad_contact_spring: float
    crawler_contact_spring: float
    bushing_spring: float

    @property
    def total(self) -> float:
        return (
            self.kinetic
            + self.gravity
            + self.pad_contact_spring
            + self.crawler_contact_spring
            + self.bushing_spring
        )

    def as_row(self) -> list[float]:
        return [
            self.t_s,
            self.kinetic,
            self.gravity,
            self.pad_contact_spring,
            self.crawler_contact_spring,
            self.bushing_spring,
            self.total,
        ]


ENERGY_COLUMNS = (
    "t_s",
    "kinetic_J",
    "gravity_J",
    "pad_contact_spring_J",
    "crawler_contact_spring_J",
    "bushing_spring_J",
    "total_J",
)


class EnergyMeter:
    """Reads :class:`EnergyTerms` from an ``L1Model`` (constants cached at construction).

    Args:
        model: The ``L1Model``.
        crawler: Include the crawler sphere springs (per-sphere contact report, slower).
    """

    def __init__(self, model: Any, *, crawler: bool) -> None:
        self._model = model
        params = model.params
        self._kn_pad = np.array(
            [float(np.float32(pad_material_values(params, i).kn_N_m)) for i in range(4)]
        )
        self._kn_crawler = float(np.float32(crawler_material_values(params).kn_N_m))
        self._kt = np.array(params.contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m, float)
        g = model.system.GetGravitationalAcceleration()
        self._g = np.array([g.x, g.y, g.z])
        self._crawler = bool(crawler) and model.crawler_layout is not None

    def read(self, probe: Any) -> EnergyTerms:
        """Energy at the probe's step (``probe`` = the state copy of that step)."""
        model = self._model
        kin = 0.0
        pot = 0.0
        for body in model.bodies:
            m = float(body.GetMass())
            v = body.GetPosDt()
            w = body.GetAngVelLocal()
            xx = body.GetInertiaXX()
            xy = body.GetInertiaXY()
            inertia = np.array(
                [[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z], [xy.y, xy.z, xx.z]], dtype=float
            )
            wl = np.array([w.x, w.y, w.z])
            kin += 0.5 * m * (v.x * v.x + v.y * v.y + v.z * v.z) + 0.5 * float(wl @ inertia @ wl)
            p = body.GetPos()
            pot -= m * float(self._g @ np.array([p.x, p.y, p.z]))
        n = np.asarray(probe.pad_normal_force_N, dtype=float)
        pad = float(np.sum(0.5 * n * n / self._kn_pad))
        crawler = 0.0
        if self._crawler:
            fz = model.crawler_sphere_contacts().force_world_N[:, 2]
            crawler = float(np.sum(0.5 * fz * fz)) / self._kn_crawler
        d = model.bushing.tangential_displacement_m()
        dd = np.where(np.isnan(d), 0.0, d)
        bush = float(np.sum(0.5 * self._kt * np.sum(dd * dd, axis=1)))
        return EnergyTerms(float(probe.t_s), kin, pot, pad, crawler, bush)

    def contact_energy_geometric(self, probe: Any) -> tuple[float, float]:
        """``(pads, crawler)`` contact spring energy ``1/2 k_n delta^2`` with ``delta`` from the
        sphere-centre heights over the level floor in double precision (no Bullet float32
        distance noise; level floor only)."""
        model = self._model
        floor = float(model.floor_z_m)
        z = np.asarray(probe.pad_sphere_centre_world_m, dtype=float)[:, 2]
        r = np.asarray(model.sphere_radii_m, dtype=float)
        delta = np.maximum(r - (z - floor), 0.0)
        pad = float(np.sum(0.5 * self._kn_pad * delta * delta))
        crawler = 0.0
        if self._crawler:
            dc = np.maximum(self.crawler_penetrations_m(), 0.0)
            crawler = float(np.sum(0.5 * self._kn_crawler * dc * dc))
        return pad, crawler

    def crawler_penetrations_m(self) -> NDArray[np.float64]:
        """Signed geometric penetration of every crawler sphere (> 0 = in contact), layout
        order, level floor [m]."""
        import pychrono as ch

        model = self._model
        floor = float(model.floor_z_m)
        sup = model.superstructure
        rad = model.crawler_layout.sphere_radius_m
        out = np.empty(len(model.crawler_centres_local_m))
        for i, c in enumerate(model.crawler_centres_local_m):
            p = sup.TransformPointLocalToParent(ch.ChVector3d(float(c[0]), float(c[1]),
                                                              float(c[2])))
            out[i] = rad - (p.z - floor)
        return out


def energy_table(rows: list[EnergyTerms]) -> NDArray[np.float64]:
    """(n, 7) array in :data:`ENERGY_COLUMNS` order."""
    return np.asarray([r.as_row() for r in rows], dtype=float)


# --- S4 energy budget (V8(b)) --------------------------------------------------------------

BUSHING_DAMPING_ACTUAL_FACTOR = 2.0
"""Chrono's ``ChLoadBodyBodyBushingSpherical`` damping acts at twice the input (R7)."""


def return_mapping_slip_energy(
    d_trial_norm_m: float, limit_N: float, k_N_m: float
) -> tuple[float, float]:
    """``(1/2 k (|d_trial|^2 - |d|^2), limit |delta a|)`` of one circular Coulomb return mapping.

    Same arithmetic as ``GroundBushingCoulomb._return_mapping``: with ``s = 1 - limit /
    (k |d_trial|)`` the anchor moves by ``s |d_trial|`` and ``|d| = limit / k`` remains, so the
    first value is ``limit |delta a| + 1/2 k |delta a|^2`` (the second term is the discrete
    excess over Coulomb's ``mu N |delta a|``). ``(0, 0)`` when the trial force is inside the
    friction circle.
    """
    dn = float(d_trial_norm_m)
    k = float(k_N_m)
    limit = float(limit_N)
    if not k * dn > limit:
        return 0.0, 0.0
    s = 1.0 - limit / (k * dn)
    return 0.5 * k * dn * dn * s * (2.0 - s), limit * dn * s


def contact_damping_work_J(
    kn_N_m: float, cn_N_s_m: float, delta0_m: float, delta_dot0_m_s: float, delta1_m: float
) -> float:
    """Energy taken out by the SMC Hooke damping over one explicit step [J].

    Chrono computes the normal force at the step start, ``F = k_n delta_0 + c_n delta_dot_0``
    (``delta_dot`` = penetration rate), and applies ``F = 0`` when this is negative; no force
    without overlap. The damping part ``F - k_n delta_0`` does the work
    ``-(F - k_n delta_0)(delta_1 - delta_0)`` on the bodies; the value returned is its negative
    (positive = dissipated).
    """
    if not delta0_m > 0.0:
        return 0.0
    total = kn_N_m * delta0_m + cn_N_s_m * delta_dot0_m_s
    damping_force = cn_N_s_m * delta_dot0_m_s if total > 0.0 else -kn_N_m * delta0_m
    return damping_force * (delta1_m - delta0_m)


def rigid_kinetic_energy_J(
    mass_kg: float,
    velocity_m_s: Any,
    inertia_body_kg_m2: Any,
    omega_body_rad_s: Any,
) -> float:
    """``1/2 m |v|^2 + 1/2 w^T I w`` (``v`` of the COG, ``I`` about the COG in body axes, ``w`` in
    body axes) [J]."""
    v = np.asarray(velocity_m_s, dtype=float)
    w = np.asarray(omega_body_rad_s, dtype=float)
    return 0.5 * mass_kg * float(v @ v) + 0.5 * float(w @ np.asarray(inertia_body_kg_m2) @ w)


@dataclass(frozen=True)
class EnergyBudgetTerms:
    """One sample of the S4 energy budget [J] (accumulated terms since the budget reset)."""

    t_s: float
    kinetic: float
    gravity: float
    contact_spring: float
    bushing_spring: float
    dissipated_viscous: float
    dissipated_slip: float
    motor_work: float
    dissipated_viscous_contact: float
    dissipated_viscous_bushing: float
    slip_coulomb_work: float
    """``sum mu N |delta a|`` over the same return mappings as ``dissipated_slip``."""
    bushing_lag: float
    """``-sum k_t (a_new - a_used) . delta_p``: residual share of the anchor lag."""
    bushing_implicit: float
    """``-sum 1/2 k_t |delta_p|^2``: implicit-Euler share of the bushing springs."""
    bushing_spring_acting: float
    """``bushing_spring`` with the anchors Chrono uses in the next step (lag included)."""
    kinetic_implicit: float = 0.0
    """``-sum 1/2 dv^T M dv`` per step (every body, translation + rotation in body axes): the
    kinetic share of the Euler step (``M dv = dt F``, ``x1 = x0 + dt v1``)."""
    contact_explicit: float = 0.0
    """``+sum 1/2 k_n d_delta^2`` per step of the pads in contact: the explicit (step-start
    force) share of the SMC springs."""

    @property
    def mechanical(self) -> float:
        return self.kinetic + self.gravity + self.contact_spring + self.bushing_spring

    def record_terms(self) -> dict[str, float]:
        """The seven ``energy.*`` Record terms (``signals.ENERGY_TERMS`` names)."""
        return {
            "kinetic": self.kinetic,
            "gravity": self.gravity,
            "contact_spring": self.contact_spring,
            "bushing_spring": self.bushing_spring,
            "dissipated_viscous": self.dissipated_viscous,
            "dissipated_slip": self.dissipated_slip,
            "motor_work": self.motor_work,
        }

    def as_row(self) -> list[float]:
        return [getattr(self, name) for name in BUDGET_FIELDS]


BUDGET_FIELDS = (
    "t_s",
    "kinetic",
    "gravity",
    "contact_spring",
    "bushing_spring",
    "dissipated_viscous",
    "dissipated_slip",
    "motor_work",
    "dissipated_viscous_contact",
    "dissipated_viscous_bushing",
    "slip_coulomb_work",
    "bushing_lag",
    "bushing_implicit",
    "bushing_spring_acting",
    "kinetic_implicit",
    "contact_explicit",
)
"""Column order of :func:`budget_table` (J, ``t_s`` in s)."""


def budget_table(rows: list[EnergyBudgetTerms]) -> NDArray[np.float64]:
    """(n, 16) array in :data:`BUDGET_FIELDS` order."""
    return np.asarray([r.as_row() for r in rows], dtype=float)


def energy_residual_J(start: EnergyBudgetTerms, now: EnergyBudgetTerms) -> float:
    """``R = (E_mech - E_mech,0) + D_visc + D_slip - W_m`` between two samples [J]
    (dissipation and motor work counted from ``start``)."""
    return (
        now.mechanical
        - start.mechanical
        + (now.dissipated_viscous - start.dissipated_viscous)
        + (now.dissipated_slip - start.dissipated_slip)
        - (now.motor_work - start.motor_work)
    )


def _in_plane(
    dx: float, dy: float, dz: float, nx: float, ny: float, nz: float
) -> tuple[float, float, float]:
    dn = dx * nx + dy * ny + dz * nz
    return dx - dn * nx, dy - dn * ny, dz - dn * nz


class EnergyBudget:
    """S4 energy budget of an ``L1Model`` standing on its pads (module docstring).

    Usage: build when the model is in its start state, call :meth:`reset` at the budget start
    (between steps, after any velocity change), :meth:`after_step` after **every**
    ``model.step()`` (all hooks done), and :meth:`read` at sample times. Gravity and the floor
    must stay fixed after :meth:`reset`.

    Args:
        model: The ``L1Model`` (pad spheres, ground bushing at the ball centre, position
            motors).
    """

    def __init__(self, model: Any) -> None:
        from outrigger_sim.chrono.ground_bushing import FORCE_POINT_BALL_CENTRE

        if model.bushing.force_point != FORCE_POINT_BALL_CENTRE:
            raise ValueError("EnergyBudget expects the ball-centre bushing force point")
        self._model = model
        params = model.params
        self._legs = tuple(model.legs)
        self._motors = tuple(model.motors)
        self._centres = tuple(model.sphere_centres_local_ch)
        self._radii = tuple(float(r) for r in model.sphere_radii_m)
        m_floor = float(model.floor.GetMass())
        kn: list[float] = []
        cn: list[float] = []
        for i, leg in enumerate(self._legs):
            mat = pad_material_values(params, i)
            m_leg = float(leg.GetMass())
            kn.append(float(np.float32(mat.kn_N_m)))
            cn.append(float(np.float32(mat.gn_1_s)) * m_leg * m_floor / (m_leg + m_floor))
        self._kn = tuple(kn)
        self._cn = tuple(cn)
        l1 = params.contact.rigid_floor.L1
        self._kt = tuple(float(k) for k in l1.bushing_stiffness_per_pad_N_m)
        self._ct_actual = tuple(
            BUSHING_DAMPING_ACTUAL_FACTOR * float(c) for c in l1.bushing_damping_input_per_pad_N_s_m
        )
        self._bodies = tuple(model.bodies)
        self._masses = tuple(float(b.GetMass()) for b in self._bodies)
        inertia = []
        for b in self._bodies:
            xx = b.GetInertiaXX()
            xy = b.GetInertiaXY()
            inertia.append(
                np.array([[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z], [xy.y, xy.z, xx.z]], dtype=float)
            )
        self._inertia = tuple(inertia)
        self._sup = model.superstructure
        self._max_dev_t_s = float("nan")
        self._max_dev_leg = -1
        self.reset()

    # --- set-up ------------------------------------------------------------------------

    @property
    def pad_contact_damping_N_s_m(self) -> tuple[float, ...]:
        """``c_n = g_n m_eff`` per pad as Chrono applies it [N s/m]."""
        return self._cn

    @property
    def bushing_damping_actual_N_s_m(self) -> tuple[float, ...]:
        """``c_t`` acting in Chrono (2 x input) per pad [N s/m]."""
        return self._ct_actual

    def _read_floor(self) -> None:
        floor = self._model.floor
        p = floor.GetPos()
        q = floor.GetRot()
        self._floor_key = (p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3)
        w, x, y, z = q.e0, q.e1, q.e2, q.e3
        self._rf = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
            ]
        )
        self._of = np.array([p.x, p.y, p.z])
        n = self._model.bushing.normal_world()
        self._n = (float(n[0]), float(n[1]), float(n[2]))
        p0 = np.asarray(self._model.floor_point_world_m, dtype=float)
        self._p0 = (float(p0[0]), float(p0[1]), float(p0[2]))

    def _anchors_world(self, local: NDArray[np.float64]) -> list[tuple[float, float, float] | None]:
        out: list[tuple[float, float, float] | None] = []
        for row in local:
            if np.any(np.isnan(row)):
                out.append(None)
            else:
                w = self._of + self._rf @ row
                out.append((float(w[0]), float(w[1]), float(w[2])))
        return out

    def _pending(self) -> None:
        """Newest anchors, and the anchors / damping that act in the next step.

        A step that starts "not updated" (bushing created or removed by the last hook) runs a
        full Update first and uses the newest values; otherwise it uses the values read by
        the Update at the end of the last step, i.e. those before the last hook.
        """
        anchor, loaded, sliding, loaded_sliding = self._model.bushing.anchor_bookkeeping()
        self._a_new = self._anchors_world(anchor)
        if not self._model.system.IsUpdated():
            self._a_used = list(self._a_new)
            used_sliding = sliding
        else:
            self._a_used = self._anchors_world(loaded)
            used_sliding = loaded_sliding
        self._c_used = tuple(
            0.0 if used_sliding[i] else self._ct_actual[i] for i in range(len(self._legs))
        )

    @staticmethod
    def _body_velocity(body: Any) -> tuple[float, float, float, float, float, float]:
        v = body.GetPosDt()
        w = body.GetAngVelLocal()
        return v.x, v.y, v.z, w.x, w.y, w.z

    def _pad_state(self, i: int) -> tuple[float, float, float, float, float, float]:
        leg = self._legs[i]
        c = leg.TransformPointLocalToParent(self._centres[i])
        v = leg.PointSpeedLocalToParent(self._centres[i])
        return c.x, c.y, c.z, v.x, v.y, v.z

    def _penetration(self, i: int, px: float, py: float, pz: float) -> float:
        nx, ny, nz = self._n
        p0x, p0y, p0z = self._p0
        return self._radii[i] - ((px - p0x) * nx + (py - p0y) * ny + (pz - p0z) * nz)

    def reset(self) -> None:
        """Start the budget now: accumulators to 0, step-start state read from Chrono."""
        self._read_floor()
        nx, ny, nz = self._n
        self._p: list[tuple[float, float, float]] = []
        self._delta: list[float] = []
        self._delta_dot: list[float] = []
        for i in range(len(self._legs)):
            px, py, pz, vx, vy, vz = self._pad_state(i)
            self._p.append((px, py, pz))
            self._delta.append(self._penetration(i, px, py, pz))
            self._delta_dot.append(-(vx * nx + vy * ny + vz * nz))
        self._s = [float(m.GetMotorPos()) for m in self._motors]
        self._dv_contact = 0.0
        self._dv_bushing = 0.0
        self._w_motor = 0.0
        self._lag = 0.0
        self._implicit = 0.0
        gb = self._model.bushing
        self._slip0 = float(np.sum(gb.slip_dissipation_J))
        self._coulomb0 = float(np.sum(gb.slip_coulomb_work_J))
        g = self._model.system.GetGravitationalAcceleration()
        self._g = (float(g.x), float(g.y), float(g.z))
        self._crawler_max_N = 0.0
        self._contact_check_max_N = 0.0
        self._max_dev_t_s = float("nan")
        self._max_dev_leg = -1
        self._kin_implicit = 0.0
        self._contact_explicit = 0.0
        self._v_prev = [self._body_velocity(b) for b in self._bodies]
        self._steps = 0
        self._pending()

    # --- views ---------------------------------------------------------------------------

    @property
    def crawler_contact_max_N(self) -> float:
        """Largest crawler (superstructure) contact force magnitude since reset [N]."""
        return self._crawler_max_N

    @property
    def contact_force_check_max_N(self) -> float:
        """Largest ``|N_Chrono - max(k_n delta + c_n delta_dot, 0)|`` of a pad in contact since
        reset [N] (geometric ``delta`` in double against Bullet's float32 distance)."""
        return self._contact_check_max_N

    @property
    def contact_force_check_max_at(self) -> tuple[float, int]:
        """``(t, leg)`` of :attr:`contact_force_check_max_N` (NaN, -1 before any contact)."""
        return self._max_dev_t_s, self._max_dev_leg

    @property
    def steps(self) -> int:
        return self._steps

    # --- per step ------------------------------------------------------------------------

    def after_step(self, dt_s: float) -> None:
        """Accumulate the step just taken (call after ``model.step()``, every step)."""
        nx, ny, nz = self._n
        dt = float(dt_s)
        for i in range(len(self._legs)):
            px, py, pz, vx, vy, vz = self._pad_state(i)
            delta1 = self._penetration(i, px, py, pz)
            d0 = self._delta[i]
            if d0 > 0.0:
                kn = self._kn[i]
                cn = self._cn[i]
                ddot0 = self._delta_dot[i]
                self._dv_contact += contact_damping_work_J(kn, cn, d0, ddot0, delta1)
                f = self._legs[i].GetContactForce()
                err = abs(f.x * nx + f.y * ny + f.z * nz - max(kn * d0 + cn * ddot0, 0.0))
                if err > self._contact_check_max_N:
                    self._contact_check_max_N = err
                    self._max_dev_t_s = float(self._model.system.GetChTime())
                    self._max_dev_leg = i
                dd = delta1 - d0
                self._contact_explicit += 0.5 * kn * dd * dd
            a = self._a_used[i]
            if a is not None:
                k = self._kt[i]
                ox, oy, oz = self._p[i]
                dx, dy, dz = _in_plane(px - ox, py - oy, pz - oz, nx, ny, nz)
                self._implicit -= 0.5 * k * (dx * dx + dy * dy + dz * dz)
                b = self._a_new[i]  # anchor of the bookkeeping spring during this step
                if b is not None and b != a:
                    self._lag -= k * ((b[0] - a[0]) * dx + (b[1] - a[1]) * dy + (b[2] - a[2]) * dz)
                c = self._c_used[i]
                if c > 0.0:
                    tx, ty, tz = _in_plane(vx, vy, vz, nx, ny, nz)
                    self._dv_bushing += c * (tx * tx + ty * ty + tz * tz) * dt
            self._p[i] = (px, py, pz)
            self._delta[i] = delta1
            self._delta_dot[i] = -(vx * nx + vy * ny + vz * nz)
            motor = self._motors[i]
            s1 = float(motor.GetMotorPos())
            self._w_motor += float(motor.GetMotorForce()) * (s1 - self._s[i])
            self._s[i] = s1
        for j, body in enumerate(self._bodies):
            v1 = self._body_velocity(body)
            v0 = self._v_prev[j]
            dv = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            dw = np.array((v1[3] - v0[3], v1[4] - v0[4], v1[5] - v0[5]))
            self._kin_implicit -= 0.5 * self._masses[j] * (
                dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]
            ) + 0.5 * float(dw @ self._inertia[j] @ dw)
            self._v_prev[j] = v1
        fc = self._sup.GetContactForce()
        fmag = math.sqrt(fc.x * fc.x + fc.y * fc.y + fc.z * fc.z)
        if fmag > self._crawler_max_N:
            self._crawler_max_N = fmag
        self._steps += 1
        self._pending()

    def read(self) -> EnergyBudgetTerms:
        """The budget at the current state (between steps, after the hooks)."""
        floor = self._model.floor
        p = floor.GetPos()
        q = floor.GetRot()
        if (p.x, p.y, p.z, q.e0, q.e1, q.e2, q.e3) != self._floor_key:
            raise RuntimeError("the floor moved after the energy-budget reset")
        gx, gy, gz = self._g
        kin = 0.0
        pot = 0.0
        for body, m, inertia in zip(self._bodies, self._masses, self._inertia, strict=True):
            v = body.GetPosDt()
            w = body.GetAngVelLocal()
            kin += rigid_kinetic_energy_J(m, (v.x, v.y, v.z), inertia, (w.x, w.y, w.z))
            c = body.GetPos()
            pot -= m * (gx * c.x + gy * c.y + gz * c.z)
        nx, ny, nz = self._n
        contact = 0.0
        bush = 0.0
        bush_acting = 0.0
        for i in range(len(self._legs)):
            d = self._delta[i]
            if d > 0.0:
                contact += 0.5 * self._kn[i] * d * d
            px, py, pz = self._p[i]
            a = self._a_new[i]
            if a is not None:
                dx, dy, dz = _in_plane(px - a[0], py - a[1], pz - a[2], nx, ny, nz)
                bush += 0.5 * self._kt[i] * (dx * dx + dy * dy + dz * dz)
            a = self._a_used[i]
            if a is not None:
                dx, dy, dz = _in_plane(px - a[0], py - a[1], pz - a[2], nx, ny, nz)
                bush_acting += 0.5 * self._kt[i] * (dx * dx + dy * dy + dz * dz)
        gb = self._model.bushing
        return EnergyBudgetTerms(
            t_s=float(self._model.system.GetChTime()),
            kinetic=kin,
            gravity=pot,
            contact_spring=contact,
            bushing_spring=bush,
            dissipated_viscous=self._dv_contact + self._dv_bushing,
            dissipated_slip=float(np.sum(gb.slip_dissipation_J)) - self._slip0,
            motor_work=self._w_motor,
            dissipated_viscous_contact=self._dv_contact,
            dissipated_viscous_bushing=self._dv_bushing,
            slip_coulomb_work=float(np.sum(gb.slip_coulomb_work_J)) - self._coulomb0,
            bushing_lag=self._lag,
            bushing_implicit=self._implicit,
            bushing_spring_acting=bush_acting,
            kinetic_implicit=self._kin_implicit,
            contact_explicit=self._contact_explicit,
        )
