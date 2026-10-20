"""L1 contact geometry, materials, collision families and a per-body contact reporter.

``00_docs/03_chrono/chrono_build_plan.md`` S1 (``chrono/contact``), R5, R8, R13, R14;
``00_docs/01_dynamics/dynamics_model.md`` 2.1, 4.1, 4.2 and the V0 crawler addendum.

* Pad contact: one sphere per leg on the leg moving part (rod body), radius = swivel-centre
  height ``legs.<leg>.pad.swivel_center_above_pad_bottom_m`` (ASSUMPTION 0.06 m), centre =
  swivel centre. Material ``kn = contact.rigid_floor.L1.kn_per_pad_N_m``, ``gn =
  .gn_per_pad_1_s`` (per effective mass, R5), ``kt = gt = mu = 0`` (R8).
* Crawler contact (layout D, R13): 24 spheres on the superstructure body, 12 at the roller
  stations (sphere bottom = ``ground.crawler_bottom_z_m``) and 12 raised end-shoe spheres
  (bottom = floor + ``end_shoe_gap_m``, unilateral). Material ``contact.crawler.
  kn_per_sphere_N_m`` / ``gn_per_sphere_1_s``, ``kt = gt = mu = 0``. Positions are body
  coordinates (CAD pose, body origin = CAD origin).
* Floor patches (R13, risk 1): Chrono combines the two SMC materials of a contact pair, so
  every floor shape carries exactly the material of the bodies that touch it: one patch per
  leg with that leg's pad material, two crawler strips with the crawler material. Patches
  must not overlap (a sphere over two patches would get two contacts).
* Collision families (R14): floor 0, superstructure incl. crawler spheres 1, leg rods 2. The
  rod family does not collide with the superstructure family (this removes rod-superstructure
  and rod-crawler pairs at once). pychrono 10.0.0 API (checked 2026-10-20 for S1):
  ``body.GetCollisionModel().SetFamily(k)``, ``.DisallowCollisionsWith(k)``,
  ``.CollidesWith(k)``; the plan's ``SetFamilyMaskNoCollisionWithFamily`` does not exist in
  pychrono 10 (it was the Chrono 8 name).

Contact force frames (pychrono 10.0.0, checked 2026-10-20 with a body rotated 30 deg):
``ChBody.GetContactForce()`` is the total contact force on the body in **world** axes.
``ReportContactCallback.OnReportContact`` gives ``react_forces`` in the contact-plane frame
``plane_coord`` (column x = contact normal pointing from object A to object B), as the force
on object B; the world force on B is ``plane_coord @ react_forces`` and on A its negative.

Units SI, world Z-up (R3).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.system import make_smc_material
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.scenarios.crawler_settle import (  # noqa: F401 - re-exported (S1 API)
    CRAWLER_LAYOUT_KEY,
    CRAWLER_SCHEME,
    END_SHOE,
    ROLLER,
    CrawlerSphereLayout,
    crawler_layout,
)

# --- collision families (R14) ------------------------------------------------------------

FAMILY_FLOOR = 0
FAMILY_SUPERSTRUCTURE = 1
"""Superstructure body and its crawler spheres."""
FAMILY_ROD = 2
"""Leg moving parts (pad spheres)."""


# Floor patch geometry: geometric convention, not a physical parameter. Pad patches are
# squares around the pad centre (pads move < 1 mm sideways in S1-S3), crawler strips extend
# the sphere row by a margin; the boxes are thick so that Bullet never tunnels.
PAD_PATCH_HALF_SIZE_M = 0.4
CRAWLER_PATCH_MARGIN_M = 0.25
PATCH_HALF_THICKNESS_M = 0.5


@dataclass(frozen=True)
class SmcMaterialValues:
    """SMC Hooke material of the L1 model (R5, R8) with its YAML source."""

    kn_N_m: float
    gn_1_s: float
    source: str
    kt_N_m: float = 0.0
    gt_1_s: float = 0.0
    friction: float = 0.0

    def make(self) -> ch.ChContactMaterialSMC:
        return make_smc_material(self.kn_N_m, self.gn_1_s)


def pad_material_values(params: Params, leg_index: int) -> SmcMaterialValues:
    """Pad sphere / pad patch material of one leg (R5, R8)."""
    l1 = params.contact.rigid_floor.L1
    name = LEG_ORDER[leg_index]
    return SmcMaterialValues(
        kn_N_m=l1.kn_per_pad_N_m[leg_index],
        gn_1_s=l1.gn_per_pad_1_s[leg_index],
        source=f"contact.rigid_floor.L1.kn_per_pad_N_m.{name}, .gn_per_pad_1_s.{name}",
    )


def crawler_material_values(params: Params) -> SmcMaterialValues:
    """Crawler sphere / crawler patch material (R13)."""
    return SmcMaterialValues(
        kn_N_m=float(params.get("contact.crawler.kn_per_sphere_N_m")),
        gn_1_s=float(params.get("contact.crawler.gn_per_sphere_1_s")),
        source="contact.crawler.kn_per_sphere_N_m, .gn_per_sphere_1_s",
    )


# --- floor patches -------------------------------------------------------------------------


@dataclass(frozen=True)
class FloorPatch:
    """One floor collision box (top face at the floor surface)."""

    name: str
    x_range_m: tuple[float, float]
    y_range_m: tuple[float, float]
    material: SmcMaterialValues

    def overlaps(self, other: FloorPatch) -> bool:
        return (
            self.x_range_m[0] < other.x_range_m[1]
            and other.x_range_m[0] < self.x_range_m[1]
            and self.y_range_m[0] < other.y_range_m[1]
            and other.y_range_m[0] < self.y_range_m[1]
        )


def floor_patches(params: Params, layout: CrawlerSphereLayout | None) -> tuple[FloorPatch, ...]:
    """Per-leg pad patches and (if ``layout``) the two crawler strips (R13, risk 1).

    Raises:
        ValueError: Two patches overlap.
    """
    patches: list[FloorPatch] = []
    h = PAD_PATCH_HALF_SIZE_M
    for i, leg in enumerate(params.legs):
        cx, cy = leg.pad_bottom_center_retracted_m[0], leg.pad_bottom_center_retracted_m[1]
        patches.append(
            FloorPatch(
                f"pad_{leg.name}",
                (cx - h, cx + h),
                (cy - h, cy + h),
                pad_material_values(params, i),
            )
        )
    if layout is not None:
        x0, x1 = layout.x_extent_m
        m = CRAWLER_PATCH_MARGIN_M
        material = crawler_material_values(params)
        for label, y in (("left", layout.track_centre_y_m), ("right", -layout.track_centre_y_m)):
            patches.append(
                FloorPatch(f"crawler_{label}", (x0 - m, x1 + m), (y - m, y + m), material)
            )
    for a in range(len(patches)):
        for b in range(a + 1, len(patches)):
            if patches[a].overlaps(patches[b]):
                raise ValueError(f"floor patches overlap: {patches[a].name} / {patches[b].name}")
    return tuple(patches)


def add_floor_patches(
    floor: ch.ChBody, patches: Sequence[FloorPatch], floor_z_m: float
) -> list[ch.ChContactMaterialSMC]:
    """Add the patches as boxes (top face at ``floor_z_m``, floor-body coordinates)."""
    floor.EnableCollision(True)
    materials = []
    hz = PATCH_HALF_THICKNESS_M
    for patch in patches:
        material = patch.material.make()
        (x0, x1), (y0, y1) = patch.x_range_m, patch.y_range_m
        floor.AddCollisionShape(
            ch.ChCollisionShapeBox(material, x1 - x0, y1 - y0, 2.0 * hz),
            ch.ChFramed(ch.ChVector3d(0.5 * (x0 + x1), 0.5 * (y0 + y1), floor_z_m - hz), ch.QUNIT),
        )
        materials.append(material)
    floor.GetCollisionModel().SetFamily(FAMILY_FLOOR)
    return materials


def set_family(body: ch.ChBody, family: int, no_collision_with: Sequence[int] = ()) -> None:
    """Collision family of ``body`` and the families it must not collide with (R14)."""
    model = body.GetCollisionModel()
    model.SetFamily(family)
    for other in no_collision_with:
        model.DisallowCollisionsWith(other)


# --- reading materials back (V0) ---------------------------------------------------------


def shape_materials(body: ch.ChBody) -> list[dict[str, Any]]:
    """Material values and local position of every collision shape of ``body`` (V0)."""
    model = body.GetCollisionModel()
    out = []
    for i in range(model.GetNumShapes()):
        instance = model.GetShapeInstance(i)
        shape, frame = instance.shape, instance.frame
        material = ch.CastToChContactMaterialSMC(shape.GetMaterial())
        pos = frame.GetPos()
        entry: dict[str, Any] = {
            "type": str(ch.ChCollisionShape.GetTypeAsString(shape.GetType())),
            "pos_local_m": [float(pos.x), float(pos.y), float(pos.z)],
        }
        if material is not None:
            entry.update(
                kn_N_m=float(material.GetKn()),
                gn_1_s=float(material.GetGn()),
                kt_N_m=float(material.GetKt()),
                gt_1_s=float(material.GetGt()),
                friction=float(material.GetSlidingFriction()),
                static_friction=float(material.GetStaticFriction()),
            )
        sphere = ch.CastToChCollisionShapeSphere(shape)
        if sphere is not None:
            entry["radius_m"] = float(sphere.GetRadius())
        out.append(entry)
    return out


# --- contact reporter (per-body force and count) -----------------------------------------


class _Reporter(ch.ReportContactCallback):
    def __init__(self, names: Mapping[str, int]) -> None:
        super().__init__()
        self._names = names
        self.force = np.zeros((len(names), 3))
        self.count = np.zeros(len(names), dtype=np.int64)
        self.other = 0

    def OnReportContact(  # noqa: N802 - Chrono callback name
        self,
        pA: Any,  # noqa: N803
        pB: Any,  # noqa: N803
        plane_coord: Any,
        distance: float,
        eff_radius: float,
        react_forces: Any,
        react_torques: Any,
        contactobjA: Any,  # noqa: N803
        contactobjB: Any,  # noqa: N803
        constraint_offset: int = 0,
    ) -> bool:
        x, y, z = plane_coord.GetAxisX(), plane_coord.GetAxisY(), plane_coord.GetAxisZ()
        fx, fy, fz = react_forces.x, react_forces.y, react_forces.z
        f_b = np.array(
            [
                x.x * fx + y.x * fy + z.x * fz,
                x.y * fx + y.y * fy + z.y * fz,
                x.z * fx + y.z * fy + z.z * fz,
            ]
        )
        name_a = contactobjA.GetPhysicsItem().GetName()
        name_b = contactobjB.GetPhysicsItem().GetName()
        hit = False
        if name_b in self._names:
            k = self._names[name_b]
            self.force[k] += f_b
            self.count[k] += 1
            hit = True
        if name_a in self._names:
            k = self._names[name_a]
            self.force[k] -= f_b
            self.count[k] += 1
            hit = True
        if not hit:
            self.other += 1
        return True


@dataclass(frozen=True)
class ContactReport:
    """Contact forces (world) and contact counts per named body, from the callback."""

    names: tuple[str, ...]
    force_world_N: NDArray[np.float64]
    """(n, 3) sum of contact forces on each body, world axes."""
    count: NDArray[np.int64]
    """(n,) number of contacts involving each body."""
    n_other: int
    """Contacts involving none of the named bodies."""


def report_contacts(system: ch.ChSystem, body_names: Sequence[str]) -> ContactReport:
    """Sum the contacts of the system per body with ``ReportContactCallback`` (risk 2 check)."""
    names = {name: i for i, name in enumerate(body_names)}
    reporter = _Reporter(names)
    system.GetContactContainer().ReportAllContacts(reporter)
    return ContactReport(
        tuple(body_names), reporter.force.copy(), reporter.count.copy(), int(reporter.other)
    )


# --- per-sphere crawler contact forces (S2b) -------------------------------------------------


class _SphereReporter(ch.ReportContactCallback):
    """Contacts of one body, assigned to the nearest sphere by the contact point's x, y."""

    def __init__(self, body_name: str, centres_xy: NDArray[np.float64]) -> None:
        super().__init__()
        self._name = body_name
        self._xy = centres_xy
        n = centres_xy.shape[0]
        self.force = np.zeros((n, 3))
        self.count = np.zeros(n, dtype=np.int64)
        self.max_xy_miss = 0.0

    def OnReportContact(  # noqa: N802 - Chrono callback name
        self,
        pA: Any,  # noqa: N803
        pB: Any,  # noqa: N803
        plane_coord: Any,
        distance: float,
        eff_radius: float,
        react_forces: Any,
        react_torques: Any,
        contactobjA: Any,  # noqa: N803
        contactobjB: Any,  # noqa: N803
        constraint_offset: int = 0,
    ) -> bool:
        name_a = contactobjA.GetPhysicsItem().GetName()
        name_b = contactobjB.GetPhysicsItem().GetName()
        if self._name not in (name_a, name_b):
            return True
        x, y, z = plane_coord.GetAxisX(), plane_coord.GetAxisY(), plane_coord.GetAxisZ()
        fx, fy, fz = react_forces.x, react_forces.y, react_forces.z
        f_b = np.array(
            [
                x.x * fx + y.x * fy + z.x * fz,
                x.y * fx + y.y * fy + z.y * fz,
                x.z * fx + y.z * fy + z.z * fz,
            ]
        )
        point = pB if name_b == self._name else pA
        force = f_b if name_b == self._name else -f_b
        d = np.hypot(self._xy[:, 0] - point.x, self._xy[:, 1] - point.y)
        k = int(np.argmin(d))
        self.max_xy_miss = max(self.max_xy_miss, float(d[k]))
        self.force[k] += force
        self.count[k] += 1
        return True


@dataclass(frozen=True)
class SphereContactReport:
    """Per-sphere contact force (world, on the body) and contact count of one body."""

    force_world_N: NDArray[np.float64]
    """(n, 3)."""
    count: NDArray[np.int64]
    max_xy_miss_m: float
    """Largest horizontal distance between a contact point and its assigned sphere centre."""


def report_sphere_contacts(
    system: ch.ChSystem, body: ch.ChBody, centres_local_m: Sequence[Sequence[float]]
) -> SphereContactReport:
    """Contact force per collision sphere of ``body`` (``centres_local_m`` in the body's COG
    frame, e.g. the crawler spheres of the superstructure). Contacts within the collision
    envelope but without overlap are counted with zero force."""
    centres = np.array(
        [
            [v.x, v.y, v.z]
            for v in (
                body.TransformPointLocalToParent(ch.ChVector3d(*map(float, c)))
                for c in centres_local_m
            )
        ]
    )
    reporter = _SphereReporter(str(body.GetName()), centres[:, :2])
    system.GetContactContainer().ReportAllContacts(reporter)
    return SphereContactReport(reporter.force.copy(), reporter.count.copy(), reporter.max_xy_miss)
