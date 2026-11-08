"""Mixed ground for the S9 model: rigid SMC base + SCM soil only under chosen pads (``S9Model(rigid_base=...)``).

Design (cad 2026-11-08, user decision "강체 + SCM 혼합 지형, 구현 뒤 LAS 확인"; Chrono 10 pattern
``demo_VEH_RigidSCMTerrain_MixedPatches.cpp:148``: rigid patches + SCM patches in one system, SCM active domains only
for the bodies on the SCM patch, ``SCMTerrain::AddActiveDomain`` ``SCMTerrain.cpp:228``):

* **rigid base** = the L1 SMC floor-patch path (``chrono/contact.py`` R5 / R8 / R13 / R14) in the S9 ``ChSystemSMC``
  (Hooke, ``UseMaterialProperties(False)``, normal only, ``kt = gt = mu = 0``): one floor box per **rigid** pad and
  the two crawler strips, on the fixed floor body (mass ``contact.rigid_floor.ground_body_mass_kg``), turned with the
  floor plane about the plane point (0, 0, ``ground.crawler_bottom_z_m``);
* **rigid pad contact**: one sphere on the pad body at the swivel ball centre, radius = swivel height (as the L1 pad
  sphere), ``kn = contact.rigid_floor.concrete.k_N_m`` (3.24e8 N/m, the concrete term that the S9 L2b force law drops
  with ``include_concrete=False``; oil, rod and frame stay in the force law, so the leg is
  ``series(k_oil, k_rod, k_frame) + k_concrete`` in series as in L2b-NSC), ``gn = contact.rigid_floor.L2.cn_per_pad /
  m_pad`` (ASSUMPTION: the L2 rod-local-mode dashpot, zeta 0.30 of the leg + concrete, ``m_eff`` = pad body mass with
  the 1e9 kg floor);
* **rigid crawler contact**: the 24 L1 layout-D spheres (12 rollers + 12 gapped end shoes) on the superstructure,
  ``kn = contact.crawler.kn_per_sphere_N_m x crawler_kn_scale``, ``gn = gn_per_sphere x sqrt(crawler_kn_scale)``
  (same heave zeta, YAML ``kn_total_sensitivity_range_N_m``; K1 = 1, K3 = 3); the S9 C envelope boxes are not
  collision shapes then (kept as geometry for the crawler-gap records, which read a flat rigid ground);
* **tangential**: the S9 ground-fixed Coulomb anchors stay (SMC has no stick, CLAUDE.md); a rigid pad takes the L1
  values ``contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m`` / ``ct_per_pad_N_s_m`` (input / 2), adhesion 0,
  ``mu = contact.rigid_floor.friction`` (0.5); the tracks take ``k = 6 x crawler_bushing_values().kt_N_m`` (no soil in
  series), ``c = (c_total sqrt(scale) / 2) sqrt(k / (kn_total scale / 2))``, ``mu`` 0.5 (:data:`CRAWLER_MU`);
* **normal forces**: :class:`RigidContactReader` sums the contact container once per step (``ReportAllContacts``):
  force on each pad, force and moment (about the COM, world) on the superstructure. :class:`~outrigger_sim.chrono.
  scm_model.ScmForceReader` adds them to the SCM values, so the pad / track normals, the records and the probe read
  "SCM + rigid contact" unchanged (one-step lag as SCM and L1);
* **SCM legs**: one SCMTerrain (the given soil) on the same plane as the rigid surface with the active domains of the
  SCM pads only (no track domains): the soil under that pad wherever it goes, like the G6 patch.

Default off: ``S9Model(rigid_base=None)`` builds the former model bit for bit (no code of this module runs).
Units SI, world Z-up.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import NDArray

from outrigger_sim.chrono.contact import CRAWLER_PATCH_MARGIN_M, FAMILY_FLOOR, PAD_PATCH_HALF_SIZE_M, \
    PATCH_HALF_THICKNESS_M
from outrigger_sim.chrono.crawler_bushing import CRAWLER_MU, crawler_bushing_values
from outrigger_sim.chrono.system import make_smc_material
from outrigger_sim.params import LEG_ORDER, Params

CRAWLER_KN_SCALES = (1.0, 3.0)
"""K1 (YAML nominal kn_total 1e8 N/m) and K3 (x3, the measured-crawler sensitivity of the user decision)."""
CRAWLER_ROLLERS_PER_TRACK = 6


@dataclass(frozen=True)
class RigidBaseSpec:
    """Mixed ground: ``scm_legs`` on SCM (the model's soil), every other pad and the crawler on the rigid base."""

    scm_legs: tuple[str, ...] = ()
    crawler_kn_scale: float = 1.0

    def __post_init__(self) -> None:
        bad = [n for n in self.scm_legs if n not in LEG_ORDER]
        if bad or len(set(self.scm_legs)) != len(self.scm_legs):
            raise ValueError(f"scm_legs must be distinct names of {LEG_ORDER}, got {self.scm_legs!r}")
        if not (self.crawler_kn_scale > 0.0 and math.isfinite(self.crawler_kn_scale)):
            raise ValueError(f"crawler_kn_scale must be positive: {self.crawler_kn_scale!r}")

    @property
    def rigid_legs(self) -> tuple[str, ...]:
        return tuple(n for n in LEG_ORDER if n not in self.scm_legs)

    @classmethod
    def parse(cls, text: str, crawler_kn_scale: float = 1.0) -> RigidBaseSpec:
        """CLI value: ``rigid`` / ``-`` (no SCM leg) or legs joined by ``,`` / ``+`` (``FR``, ``FR+RL``)."""
        t = text.strip()
        legs = () if t.lower() in ("rigid", "-", "none", "") else tuple(
            s.strip().upper() for s in t.replace("+", ",").split(",") if s.strip())
        return cls(legs, float(crawler_kn_scale))

    def tag(self) -> str:
        return "rigid" + "".join(f"+{n}" for n in self.scm_legs) + f"_K{self.crawler_kn_scale:g}"


@dataclass(frozen=True)
class RigidPadValues:
    """Rigid pad: SMC sphere material and anchor bushing values (module docstring; per leg, LEG_ORDER)."""

    kn_N_m: tuple[float, ...]
    cn_N_s_m: tuple[float, ...]
    gn_1_s: tuple[float, ...]
    pad_mass_kg: tuple[float, ...]
    kt_N_m: tuple[float, ...]
    ct_actual_N_s_m: tuple[float, ...]
    ct_input_N_s_m: tuple[float, ...]
    friction: float
    sources: Mapping[str, str] = field(default_factory=dict)

    def meta(self) -> dict[str, Any]:
        return {k: (list(v) if isinstance(v, tuple) else (dict(v) if isinstance(v, Mapping) else v))
                for k, v in self.__dict__.items()}


def rigid_pad_values(params: Params, pad_mass_kg: Sequence[float]) -> RigidPadValues:
    l1 = params.contact.rigid_floor.L1
    k_conc = float(params.get("contact.rigid_floor.concrete.k_N_m"))
    cn = params.get("contact.rigid_floor.L2.cn_per_pad_N_s_m")
    cn_t = tuple(float(cn[n]) for n in LEG_ORDER)
    m = tuple(float(v) for v in pad_mass_kg)
    ct = tuple(float(l1.ct_per_pad_N_s_m[i]) for i in range(4))
    return RigidPadValues(
        kn_N_m=(k_conc,) * 4, cn_N_s_m=cn_t, gn_1_s=tuple(c / mi for c, mi in zip(cn_t, m, strict=True)),
        pad_mass_kg=m, kt_N_m=tuple(float(l1.bushing_stiffness_per_pad_N_m[i]) for i in range(4)),
        ct_actual_N_s_m=ct, ct_input_N_s_m=tuple(0.5 * v for v in ct),
        friction=float(params.get("contact.rigid_floor.friction")),
        sources={"kn": "contact.rigid_floor.concrete.k_N_m",
                 "gn": "ASSUMPTION contact.rigid_floor.L2.cn_per_pad_N_s_m / pad body mass (m_eff, floor 1e9 kg)",
                 "kt": "contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m (= L1 k_t, concrete in series)",
                 "ct": "contact.rigid_floor.L1.ct_per_pad_N_s_m (input / 2, R7)",
                 "friction": "contact.rigid_floor.friction"})


@dataclass(frozen=True)
class RigidCrawlerValues:
    kn_per_sphere_N_m: float
    gn_per_sphere_1_s: float
    kn_scale: float
    track_k_N_m: float
    track_c_actual_N_s_m: float
    track_c_input_N_s_m: float
    friction: float

    def meta(self) -> dict[str, Any]:
        return {**self.__dict__, "basis": (
            "spheres: kn_per_sphere x scale, gn_per_sphere x sqrt(scale) (same heave zeta); tracks: k = 6 x "
            "crawler_bushing_values().kt_N_m (no soil), c = (c_total sqrt(scale)/2) sqrt(k / (kn_total scale / 2)), "
            "mu = CRAWLER_MU (ASSUMPTION, as L1 Q12)")}


def rigid_crawler_values(params: Params, kn_scale: float) -> RigidCrawlerValues:
    s = float(kn_scale)
    kn_s = float(params.get("contact.crawler.kn_per_sphere_N_m")) * s
    gn_s = float(params.get("contact.crawler.gn_per_sphere_1_s")) * math.sqrt(s)
    k = CRAWLER_ROLLERS_PER_TRACK * crawler_bushing_values(params).kt_N_m
    kn_track = float(params.get("contact.crawler.kn_total_N_m")) * s / 2.0
    c = float(params.get("contact.crawler.damping_total_N_s_m")) * math.sqrt(s) / 2.0 * math.sqrt(k / kn_track)
    return RigidCrawlerValues(kn_s, gn_s, s, k, c, 0.5 * c, CRAWLER_MU)


def add_rigid_floor(floor: ch.ChBody, params: Params, plane_point: NDArray[np.float64],
                    plane_rot: NDArray[np.float64], rigid_legs: Sequence[str], pads: RigidPadValues,
                    crawler: RigidCrawlerValues, crawler_x_extent_m: tuple[float, float],
                    track_centre_y_m: float) -> list[dict[str, Any]]:
    """Floor boxes (top face on the plane) for the rigid pads and the two crawler strips (R13: each box carries the
    material of the bodies that touch it). Box centres in body coordinates are mapped like the machine pose:
    ``world = p0 + R (b - p0)``. Returns the patch meta."""
    floor.EnableCollision(True)
    p0 = np.asarray(plane_point, float)
    rot = np.asarray(plane_rot, float)
    from outrigger_sim.chrono.scm_model import _quat_from_matrix, chvec  # noqa: PLC0415

    q = _quat_from_matrix(rot)
    hz = PATCH_HALF_THICKNESS_M
    z_top = float(p0[2])
    out = []

    def _box(name: str, x: tuple[float, float], y: tuple[float, float], kn: float, gn: float) -> None:
        centre_b = np.array([0.5 * (x[0] + x[1]), 0.5 * (y[0] + y[1]), z_top - hz])
        centre_w = p0 + rot @ (centre_b - p0)
        mat = make_smc_material(kn, gn)
        floor.AddCollisionShape(ch.ChCollisionShapeBox(mat, x[1] - x[0], y[1] - y[0], 2.0 * hz),
                                ch.ChFramed(chvec(centre_w), q))
        out.append({"name": name, "x_range_body_m": list(x), "y_range_body_m": list(y), "kn_N_m": kn, "gn_1_s": gn})

    h = PAD_PATCH_HALF_SIZE_M
    for i, leg in enumerate(params.legs):
        if leg.name not in rigid_legs:
            continue
        cx, cy = leg.pad_bottom_center_retracted_m[0], leg.pad_bottom_center_retracted_m[1]
        _box(f"pad_{leg.name}", (cx - h, cx + h), (cy - h, cy + h), pads.kn_N_m[i], pads.gn_1_s[i])
    m = CRAWLER_PATCH_MARGIN_M
    x0, x1 = crawler_x_extent_m
    for label, y in (("left", track_centre_y_m), ("right", -track_centre_y_m)):
        _box(f"crawler_{label}", (x0 - m, x1 + m), (y - m, y + m), crawler.kn_per_sphere_N_m,
             crawler.gn_per_sphere_1_s)
    floor.GetCollisionModel().SetFamily(FAMILY_FLOOR)
    return out


class RigidContactReader(ch.ReportContactCallback):
    """Contact force on each pad (world) and force + moment about the COM (world) on the superstructure, of the
    step just taken (contact container sum, once per :meth:`refresh`)."""

    def __init__(self, system: ch.ChSystem, pads: Sequence[ch.ChBody], superstructure: ch.ChBody) -> None:
        super().__init__()
        self._system = system
        self._pad_index = {str(p.GetName()): i for i, p in enumerate(pads)}
        self._sup = superstructure
        self._sup_name = str(superstructure.GetName())
        self.pad_force_N = np.zeros((len(pads), 3))
        self.sup_force_N = np.zeros(3)
        self.sup_torque_Nm = np.zeros(3)
        self.n_contacts = 0
        self.n_crawler_contacts = 0
        self._com = np.zeros(3)

    def refresh(self) -> None:
        self.pad_force_N[:] = 0.0
        self.sup_force_N[:] = 0.0
        self.sup_torque_Nm[:] = 0.0
        self.n_contacts = 0
        self.n_crawler_contacts = 0
        c = self._sup.GetPos()
        self._com = np.array([c.x, c.y, c.z])
        self._system.GetContactContainer().ReportAllContacts(self)

    def OnReportContact(self, pA: Any, pB: Any, plane_coord: Any, distance: float,  # noqa: N802, N803
                        eff_radius: float, react_forces: Any, react_torques: Any, contactobjA: Any,  # noqa: N803
                        contactobjB: Any, constraint_offset: int = 0) -> bool:  # noqa: N803
        x, y, z = plane_coord.GetAxisX(), plane_coord.GetAxisY(), plane_coord.GetAxisZ()
        fx, fy, fz = react_forces.x, react_forces.y, react_forces.z
        f_b = np.array([x.x * fx + y.x * fy + z.x * fz, x.y * fx + y.y * fy + z.y * fz,
                        x.z * fx + y.z * fy + z.z * fz])
        self.n_contacts += 1
        for obj, point, f in ((contactobjB, pB, f_b), (contactobjA, pA, -f_b)):
            name = str(obj.GetPhysicsItem().GetName())
            if name in self._pad_index:
                self.pad_force_N[self._pad_index[name]] += f
            elif name == self._sup_name:
                self.sup_force_N += f
                r = np.array([point.x, point.y, point.z]) - self._com
                self.sup_torque_Nm += np.cross(r, f)
                self.n_crawler_contacts += 1
        return True


@dataclass
class _NodeInfo:
    sinkage: float = 0.0
    sinkage_plastic: float = 0.0
    sinkage_elastic: float = 0.0
    sigma: float = 0.0
    sigma_yield: float = 0.0
    kshear: float = 0.0
    tau: float = 0.0


class RigidGroundStub:
    """Stands for ``S9Model.crawler_terrain`` on the rigid base: flat ground, no sinkage (crawler-gap records read
    the clearance above the rigid surface); patch count = crawler contacts of the last step."""

    def __init__(self, reader: RigidContactReader) -> None:
        self._reader = reader

    def GetNodeInfo(self, p: Any) -> _NodeInfo:  # noqa: N802 - SCMTerrain name
        return _NodeInfo()

    def GetNumContactPatches(self) -> int:  # noqa: N802
        return int(self._reader.n_crawler_contacts > 0)

    def GetNumRayHits(self) -> int:  # noqa: N802
        return 0
