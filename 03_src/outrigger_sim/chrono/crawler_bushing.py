"""Circular-Coulomb anchor bushings under the 24 crawler spheres (user decision Q12, 2026-10-21).

CLAUDE.md '크롤러 접촉 배치': "경사 바닥 들어 올림 전에 롤러 구별 원형 Coulomb 고정점 부싱(mu 0.5,
접선 강성 가정 + 감도) 옵션을 도입". Without it the crawler spheres (SMC, ``kt = mu = 0``, R8)
carry no tangential load and the machine slides on a sloped floor.

Model (``L1Model(crawler_bushings=True)``; default off = the S1-S6 model unchanged):

* one :class:`~outrigger_sim.chrono.ground_bushing.GroundBushingCoulomb` with one
  :class:`~outrigger_sim.chrono.ground_bushing.PadBushingSpec` per crawler sphere (layout D
  order): body A = superstructure, frame A at the sphere centre (ball-centre force point, as
  the pads), body B = the fixed floor, same rules as the pads: circular Coulomb return
  mapping, creation at ``N > N_th`` / removal after ``t_lift`` (R15), one-step lag, damping
  input = actual / 2 (R7), damping off while sliding;
* normal force per sphere: the spheres share one body, so ``GetContactForce()`` of the body
  is the sum. :class:`CrawlerSphereNormals` reads the contact container once per step
  (``ReportAllContacts``, contacts assigned to the nearest sphere by world x, y) and gives the
  force on the body along the floor normal; when the body has no contact force at all it
  returns zeros without reading the container;
* friction ``mu`` = :data:`CRAWLER_MU` = 0.5 (Q12; = YAML ``contact.crawler.friction``, which
  the YAML labels as the L2b crawler value);
* **tangential stiffness (ASSUMPTION)** ``kt_sphere = (kt / kn)_pad x kn_sphere``: the pad ratio
  ``contact.rigid_floor.L1.kt_per_pad_N_m / kn_per_pad_N_m`` (mean of the four legs, 0.402) applied
  to ``contact.crawler.kn_per_sphere_N_m`` (8.33e6 N/m) = 3.35e6 N/m per sphere, 4.0e7 N/m for
  the 12 roller spheres (crawler total vertical 1e8 N/m). Basis: the same steel-on-concrete
  contact as the pad and no crawler shear data; sensitivity x0.3 / x3 via ``kt_scale``;
* **tangential damping (ASSUMPTION)** ``ct = cn_sphere sqrt(kt / kn)``, ``cn_sphere =
  contact.crawler.damping_total_N_s_m / 12`` (heave zeta 0.05): the same damping ratio for the
  same mass on the tangential spring; Chrono input ``ct / 2``.

Snapshot part ``crawler_bushing`` (the ground-bushing state keys).
Units SI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.ground_bushing import GroundBushingCoulomb, PadBushingSpec
from outrigger_sim.params import Params

PART_PREFIX = "crawler_bushing"
CRAWLER_MU = 0.5
"""User decision Q12 (2026-10-21)."""
KT_SCALES = (0.3, 1.0, 3.0)
"""Assumed tangential stiffness and its sensitivity factors."""


@dataclass(frozen=True)
class CrawlerBushingValues:
    """Per-sphere tangential values (module docstring, ASSUMPTION)."""

    kt_N_m: float
    ct_N_s_m: float
    damping_input_N_s_m: float
    kt_over_kn_pad: float
    kn_sphere_N_m: float
    cn_sphere_N_s_m: float
    kt_scale: float

    def meta(self) -> dict[str, Any]:
        return {**self.__dict__, "mu": CRAWLER_MU,
                "basis": "kt = (kt/kn)_pad mean x kn_sphere x kt_scale; ct = cn_sphere "
                         "sqrt(kt/kn_sphere); input ct/2 (ASSUMPTION)"}


def crawler_bushing_values(params: Params, kt_scale: float = 1.0) -> CrawlerBushingValues:
    """Values of the module docstring."""
    if not (kt_scale > 0.0 and math.isfinite(kt_scale)):
        raise ValueError(f"kt_scale must be positive: {kt_scale!r}")
    kn_pad = params.get("contact.rigid_floor.L1.kn_per_pad_N_m")
    kt_pad = params.get("contact.rigid_floor.L1.kt_per_pad_N_m")
    ratio = float(np.mean([float(kt_pad[k]) / float(kn_pad[k]) for k in kn_pad]))
    kn_s = float(params.get("contact.crawler.kn_per_sphere_N_m"))
    cn_s = float(params.get("contact.crawler.damping_total_N_s_m")) / 12.0
    kt = ratio * kn_s * float(kt_scale)
    ct = cn_s * math.sqrt(kt / kn_s)
    return CrawlerBushingValues(kt, ct, 0.5 * ct, ratio, kn_s, cn_s, float(kt_scale))


class CrawlerSphereNormals(ch.ReportContactCallback):
    """Signed normal force per crawler sphere of the step just taken (module docstring)."""

    def __init__(self, system: Any, body: Any, centres_local_m: NDArray[np.float64],
                 normal_fn: Any) -> None:
        super().__init__()
        self._system = system
        self._body = body
        self._name = str(body.GetName())
        self._local = [ch.ChVector3d(*(float(c) for c in p)) for p in centres_local_m]
        self._normal_fn = normal_fn
        self._n = len(self._local)
        self._force = [0.0] * self._n
        self._xy: list[tuple[float, float]] = []
        self._normal = (0.0, 0.0, 1.0)

    def __call__(self) -> list[float]:
        f = self._body.GetContactForce()
        if f.x == 0.0 and f.y == 0.0 and f.z == 0.0:
            return [0.0] * self._n
        self._force = [0.0] * self._n
        self._xy = []
        for c in self._local:
            w = self._body.TransformPointLocalToParent(c)
            self._xy.append((w.x, w.y))
        n = self._normal_fn()
        self._normal = (float(n[0]), float(n[1]), float(n[2]))
        self._system.GetContactContainer().ReportAllContacts(self)
        return list(self._force)

    def OnReportContact(  # noqa: N802 - Chrono callback name
        self, pA, pB, plane_coord, distance, eff_radius, react_forces, react_torques,  # noqa: N803
        contactobjA, contactobjB, constraint_offset=0,  # noqa: N803
    ) -> bool:
        name_a = contactobjA.GetPhysicsItem().GetName()
        name_b = contactobjB.GetPhysicsItem().GetName()
        if name_b == self._name:
            sign, point = 1.0, pB
        elif name_a == self._name:
            sign, point = -1.0, pA
        else:
            return True
        x, y, z = plane_coord.GetAxisX(), plane_coord.GetAxisY(), plane_coord.GetAxisZ()
        fx, fy, fz = react_forces.x, react_forces.y, react_forces.z
        nx, ny, nz = self._normal
        f_on_body_n = sign * (
            (x.x * fx + y.x * fy + z.x * fz) * nx
            + (x.y * fx + y.y * fy + z.y * fz) * ny
            + (x.z * fx + y.z * fy + z.z * fz) * nz
        )
        best, best_d = 0, math.inf
        px, py = point.x, point.y
        for i, (cx, cy) in enumerate(self._xy):
            d = (cx - px) * (cx - px) + (cy - py) * (cy - py)
            if d < best_d:
                best, best_d = i, d
        self._force[best] += f_on_body_n
        return True


def make_crawler_bushing(
    params: Params,
    system: Any,
    floor: Any,
    superstructure: Any,
    centres_local_m: NDArray[np.float64],
    radius_m: float,
    *,
    dt_s: float,
    kt_scale: float = 1.0,
    normal_fn: Any,
) -> tuple[GroundBushingCoulomb, CrawlerSphereNormals, CrawlerBushingValues]:
    """The crawler-sphere bushing set (not attached) and its normal-force source."""
    values = crawler_bushing_values(params, kt_scale)
    specs = [
        PadBushingSpec(
            name=f"crawler_{i}",
            body=superstructure,
            sphere_centre_body_local_m=tuple(float(c) for c in centre),  # type: ignore[arg-type]
            sphere_radius_m=float(radius_m),
            stiffness_N_m=values.kt_N_m,
            damping_input_N_s_m=values.damping_input_N_s_m,
        )
        for i, centre in enumerate(np.asarray(centres_local_m, dtype=float))
    ]
    normals = CrawlerSphereNormals(system, superstructure, centres_local_m, normal_fn)
    bushing = GroundBushingCoulomb(
        system,
        floor,
        specs,
        friction=CRAWLER_MU,
        slip_damping_reenable_speed_m_s=float(
            params.contact.rigid_floor.L1.slip_damping_reenable_speed_m_s
        ),
        dt_s=dt_s,
        surface_point_floor_local_m=(0.0, 0.0, params.ground.crawler_bottom_z_m),
        normal_force_source=normals,
    )
    return bushing, normals, values


__all__ = [
    "CRAWLER_MU",
    "KT_SCALES",
    "PART_PREFIX",
    "CrawlerBushingValues",
    "CrawlerSphereNormals",
    "crawler_bushing_values",
    "make_crawler_bushing",
]
