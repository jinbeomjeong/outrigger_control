"""Mechanical energy of the L1 model (S3 V8(a); the ``energy.*`` Record terms of S4 later).

``dynamics_model.md`` 5 V8: ``E`` = kinetic + gravity + ``sum 1/2 k_n delta^2`` (SMC Hooke
contacts: pad spheres and crawler spheres) + ``sum 1/2 k_t |d|^2`` (ground bushings, after the
return mapping). With the contact damping ``g_n`` = 0 the SMC Hooke force is ``k_n delta``, so
the contact spring energy is taken as ``F^2 / (2 k_n)`` from the contact force Chrono applied
(Bullet's float32 distance included) and ``k_n`` as Chrono stores it (float32, R5). Motors are
locked or moving rigidly: no spring energy. Gravity potential ``-sum m g . p_cog``.

Units SI (J). Read between steps only (contact forces of the last step).
"""

from __future__ import annotations

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
