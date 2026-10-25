"""S9 soft-soil Chrono model: SCM terrain + separate swivel pads + L2b force-law legs.

``00_docs/03_chrono/chrono_build_plan.md`` S9; ``dynamics_model.md`` 2.1 (SCM pad row), 2.6,
3.11.2 / 3.11.5 (pad hull + crawler C boxes), 5.32.4 (soil sets), 5.33.7 items 1-9 (horizontal
restraint, user decisions U-S9L-1 ... 5 of 2026-10-26).

Model (one ``ChSystemSMC`` from ``make_system(params, "L1", dt=1e-4, floor_plate=False)``:
SPARSE_LU with a locked pattern, EULER_IMPLICIT_LINEARIZED, Bullet, gravity R1; no rigid
contact at all, every ground force comes from the SCM loader or from the anchor bushings):

* superstructure (``superstructure.auger_levels.<level>``) with the crawler **C envelope boxes**
  (3 per track: flat + front 2.134 deg + rear 3.187 deg ramp, 3.11.2 table; bottom = block bottom
  = ``ground.crawler_bottom_z_m + 0.004``) as SCM collision shapes; the 24 crawler spheres are
  not used;
* **SCM ray targets** (5.34.10, P1-V0): crawler boxes and pad hulls are static triangle soups
  (``ray_shape="mesh"``, default). The former ``ChCollisionShapeBox`` / ``ConvexHull`` shapes
  (``"convex"``) are ray-tested by Bullet's sub-simplex convex cast (``cbtCollisionWorld.cpp:300``),
  which stops at a squared distance of ``MAX_CONVEX_CAST_EPSILON`` = 1e-4 m^2 (single precision,
  i.e. 10 mm; ``cbtConvexCast.h``) and hit the bottoms up to 10 mm low (pads median -1 mm);
  ``cbtBvhTriangleMeshShape`` uses the exact ray-triangle test (measured |error| <= 5e-4 mm);
* per leg a **rod body** (``legs.<leg>.rod_body``) on a ``ChLinkMotorLinearForce`` (link Z =
  body -z, R4) driven by :class:`~outrigger_sim.chrono.l2b_actuator.L2bForceActuator` with the
  concrete dropped from ``k_ax`` (``include_concrete=False``; YAML ``actuator.L2b_NSC`` comment
  "on SCM drop k_concrete"), the guide **PRISMATIC** (rod laterally rigid: the rod bending
  ``k_lat`` sits in the ground bushing in series with the soil, 5.33.4, so the L2b lateral
  bushing is not used), and a **pad body** (``legs.<leg>.pad_body``, the C8 pad hull of the
  selected pad type, ``sim_shapes.add_pad_hull`` with offset ``-pad_body.com_m``) on a
  ``ChLinkLockSpherical`` at the ball centre (pad bottom + ``swivel_center_above_pad_bottom_m``);
* SCM (``pychrono.vehicle.SCMTerrain``) on the block-bottom plane (level, or rotated with the
  floor normal), soil set from ``02_params/scm_soil_sets.json`` ``sets.<key>.chrono``; active
  domains: one box per pad body and one per track (2.94 x 0.80 m, 3.11.2), height
  :data:`ACTIVE_DOMAIN_HEIGHT_M`; pre-check ``elastic_K > Kphi`` (n = 1) against the silent
  Chrono clamp (5.32.3); optional **dual terrain** (``crawler_grid_m``, U-S9G-1 M14s): the
  pad domains on one terrain (``grid_m``), the track domains on a second (``crawler_grid_m``),
  forces summed by :class:`ScmForceReader`;
* **gravity ramp** (5.34.2 P2): :meth:`S9Model.set_gravity_factor` with
  :func:`gravity_ramp_factor` (the runner applies Poly345 3 s + hold 2 s by default);
* **SCM shear** (5.33.7 #1): ``"bprime"`` (default, judgement) = ``SetSoilParameters(..., c 0,
  phi 0, ...)`` (tau = 0 exactly, normal law unchanged) + tangential force by ground-fixed
  anchor bushings; ``"native"`` = the set's c, phi in SCM and no anchor bushings (comparison
  only, not for judgement);
* **pad anchor bushings** (#2-#5): :class:`~outrigger_sim.chrono.ground_bushing.
  GroundBushingCoulomb`, body A = pad body, frame A = ball centre, frame B = projection on the
  SCM plane, axes = plane tangent + normal; ``k_t,S9 = series(k_lat, kappa K A)``, ``k_lat =
  series^-1(k_t,L1, -k_concrete)``, ``kappa`` 0.8 (ASSUMPTION), ``c_t,S9 = c_t,L1 sqrt(k_t,S9 /
  k_t,L1)`` (input / 2, R7); normal force = SCM force on the pad along the plane normal (signed;
  ``GetContactForceBody`` of the step just taken = start-of-step state, the L1 one-step lag);
  limit ``c A min(1, N / 10 kN) + N tan(phi)`` (adhesion argument of the bushing); R15 rules
  (create ``N > 100 N``, remove ``N <= 0`` for 1 ms), damping off while sliding, as L1.
  Sensitivities (U-S9L-2 / 3): ``stiffness_mode`` ``"l1_kt"`` (upper) / ``"janosi"`` (lower:
  in series with ``(c A + N_design tan(phi)) / K_J``), ``interface=True`` (0.5 c, 2/3 phi);
* **swivel stabiliser** (#6, U-S9L-4): per pad a ``ChLoadBodyBodyBushingMate`` pad <-> ground
  with translation 0 and rotation ``(k_sw, k_sw, k_sw)`` = 1.5e4 N m/rad, damping 0, neutral =
  pad parallel to the SCM plane with the pad yaw at creation; created / removed together with
  the pad anchor bushing (R15), absent in the air. ``ChLoadBodyBodyBushingMate`` instead of the
  ``...Generic`` of the spec: same diagonal law (``ChLoadsBody.cpp:483``, small-rotation vector
  times the stiffness vector) with vector arguments. Pad tilt to the plane is recorded; above
  ``legs.<leg>.pad.swivel_tilt_range_deg`` (10 deg) a warning is logged;
* **crawler track bushings** (#7, U-S9L-5): one anchor per track on the superstructure (frame A
  = block-bottom point at the centre of the flat box, y = +-1.045 m), normal force = SCM force
  on the superstructure split by its moment about the track midline (negative -> 0), limit
  ``N tan(phi)`` only, ``k = series(sum of the 6 roller k_t of the L1 crawler bushing, 0.8 K
  A_c / 2)``, damping by the ``crawler_bushing`` zeta rule ``c = (c_total / 2) sqrt(k / (kn_total
  / 2))``;
* records (#8, control spec 284 keys): SCM force on the crawler (= crawler patch force sum),
  on each pad, number of SCM contact patches, pad sinkage (geometric and node mean inside the
  pad bottom polygon, :meth:`S9Model.pad_node_stats`), crawler clearance above the rut (after
  :meth:`S9Model.mark_rut_reference`), body angular velocity (crawler rocking), running pad tilt
  maximum (P3 keys, 5.34.6).

Hook order (as L2bModel): actuator guard -> ``DoStepDynamics`` -> actuator end -> SCM force read
-> state copy -> pad anchor bushings -> swivel stabiliser -> crawler bushings -> actuator hooks
(engine callback first) -> load hooks -> record hooks. Every hook value acts in the next step.

Units SI, world Z-up; body axes x forward, y left, z up; per-leg arrays in LEG_ORDER.
Snapshots are not implemented for S9 (SCM node state is not exposed to Python).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pychrono as ch
import pychrono.vehicle as veh
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.chrono.bodies import BodyPose, make_superstructure
from outrigger_sim.chrono.contact import FAMILY_ROD, FAMILY_SUPERSTRUCTURE, set_family
from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values
from outrigger_sim.chrono.ground_bushing import (
    ADHESION_FULL_NORMAL_N,
    GroundBushingCoulomb,
    PadBushingSpec,
)
from outrigger_sim.chrono.l2b_actuator import L2bForceActuator, make_force_motor
from outrigger_sim.chrono.probes import ProbeState, chvec, truth_state
from outrigger_sim.chrono.sim_shapes import add_pad_hull
from outrigger_sim.chrono.system import gravity_vector, make_system, set_gravity
from outrigger_sim.geometry import extension_direction, pad_bottom_body_m, pad_sphere_centre_body_m
from outrigger_sim.pad_variants import PROJECT_ROOT
from outrigger_sim.params import LEG_ORDER, Params, axial_stiffness_N_m, scm_run_sha256
from outrigger_sim.signals import TruthState

SOIL_SETS_JSON = PROJECT_ROOT / "02_params" / "scm_soil_sets.json"
SCM_SHEAR_MODES = ("bprime", "native")
STIFFNESS_MODES = ("series", "l1_kt", "janosi")
KAPPA_HORIZONTAL = 0.8
"""Horizontal / vertical elastic stiffness ratio of a rigid footing (5.33.4, ASSUMPTION)."""
SWIVEL_K_N_M_RAD = 1.5e4
"""Swivel stabiliser rotational stiffness (5.33.8, U-S9L-4)."""
INTERFACE_C_FACTOR = 0.5
INTERFACE_PHI_FACTOR = 2.0 / 3.0
"""Pad-soil interface sensitivity (U-S9L-3, ASSUMPTION)."""
BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M = 0.004
"""SCM plane = crawler block bottom = crawler bottom + 4 mm (3.11.2)."""
GRID_M = 0.02
ACTIVE_DOMAIN_HEIGHT_M = 0.40
PAD_DOMAIN_XY_M = 0.50
TRACK_DOMAIN_XY_M = (2.94, 0.80)
TERRAIN_SIZE_M = (8.0, 6.0)
TRACK_Y_M = 1.045
TRACK_Y_RANGE_M = (0.80038, 1.28961)
CRAWLER_BOX_THICKNESS_M = 0.043
FLAT_X_M = (-0.92619, 0.88706)
FRONT_RAMP_X_M = (0.88706, 1.34080)
FRONT_RAMP_SLOPE = 0.037259
REAR_RAMP_X_M = (-1.35623, -0.92619)
REAR_RAMP_SLOPE = 0.055685
CRAWLER_ROLLERS_PER_TRACK = 6
SHEAR_OFF_TEXT = "off (tangential by anchor bushings)"
SCM_THREADS = 4
"""OpenMP threads of the SCM ray casting (``SetNumThreads(n, 1, 1)``; Chrono default = all
processors). Measured 2026-10-26 (machine, 2 cm, P-cores shared with other runs): ray testing
7.7 ms/step with 1 thread, 4.1 ms with 4; the contact-patch flood fill (about 9 ms) is serial."""


# --- soil sets ----------------------------------------------------------------------------


@dataclass(frozen=True)
class SoilSet:
    """One SCM soil set (``scm_soil_sets.json`` ``sets.<key>``)."""

    key: str
    chrono: Mapping[str, float]
    """``SetSoilParameters`` values of the set (Kphi, Kc, n, cohesion, friction [deg], Janosi,
    elastic_K, damping_R), after overrides."""
    crawler_contact_area_m2: float
    """``crawler_settle_P0.A_c_m2`` (both tracks)."""
    design_loads_N: tuple[float, ...]
    table_sha256: str
    table_path: str
    overrides: Mapping[str, float] = field(default_factory=dict)

    @property
    def cohesion_Pa(self) -> float:
        return float(self.chrono["cohesion"])

    @property
    def friction_deg(self) -> float:
        return float(self.chrono["friction"])

    def meta(self) -> dict[str, Any]:
        return {"key": self.key, "chrono": dict(self.chrono), "A_c_m2": self.crawler_contact_area_m2,
                "design_loads_N": list(self.design_loads_N), "table_sha256": self.table_sha256,
                "table_path": self.table_path, "overrides": dict(self.overrides)}


class SoilParameterError(ValueError):
    """A soil set that Chrono would silently change (elastic_K clamp, 5.32.3)."""


def check_soil(chrono: Mapping[str, float]) -> None:
    """Refuse ``elastic_K <= Kphi`` (n = 1) or ``elastic_K < Kphi`` (any n): ``SetSoilParameters``
    sets ``K = max(K, Kphi)`` without a message (``SCMTerrain.cpp:148-165``); with n = 1 and
    ``K <= Kphi`` the soil becomes fully elastic (no rut)."""
    k, kphi, n = float(chrono["elastic_K"]), float(chrono["Kphi"]), float(chrono["n"])
    if k < kphi or (n == 1.0 and k <= kphi):
        raise SoilParameterError(f"elastic_K {k:g} must exceed Kphi {kphi:g} (n = {n:g}); Chrono "
                                 "would clamp it silently (SCMTerrain.cpp:148-165)")
    for name in ("Kphi", "n", "elastic_K", "damping_R", "Janosi"):
        if not (float(chrono[name]) >= 0.0 and math.isfinite(float(chrono[name]))):
            raise SoilParameterError(f"{name} must be finite and >= 0: {chrono[name]!r}")


def load_soil_set(key: str, *, overrides: Mapping[str, float] | None = None,
                  path: Path = SOIL_SETS_JSON) -> SoilSet:
    """Soil set ``key`` (J1, J2, G1, S1) with optional overrides of ``chrono`` entries."""
    data_bytes = Path(path).read_bytes()
    data = json.loads(data_bytes.decode("utf-8"))
    sets = data["sets"]
    if key not in sets:
        raise KeyError(f"unknown soil set {key!r}; known {sorted(sets)}")
    entry = sets[key]
    chrono = {k: float(v) for k, v in entry["chrono"].items()}
    for name, value in dict(overrides or {}).items():
        if name not in chrono:
            raise KeyError(f"soil override {name!r} is not a chrono key of the set")
        chrono[name] = float(value)
    check_soil(chrono)
    try:
        rel = Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel = Path(path).resolve().as_posix()
    loads = data["design_loads_N"]["FL_FR_RL_RR_contact_twist_free_top"]
    return SoilSet(key=key, chrono=chrono,
                   crawler_contact_area_m2=float(entry["crawler_settle_P0"]["A_c_m2"]),
                   design_loads_N=tuple(float(v) for v in loads),
                   table_sha256=hashlib.sha256(data_bytes).hexdigest(), table_path=rel,
                   overrides=dict(overrides or {}))


def scm_call_values(soil: SoilSet, shear: str) -> tuple[float, ...]:
    """Arguments of ``SetSoilParameters`` for the shear mode (#1: bprime -> c = phi = 0)."""
    if shear not in SCM_SHEAR_MODES:
        raise ValueError(f"scm shear must be one of {SCM_SHEAR_MODES}, got {shear!r}")
    c = soil.chrono
    cohesion, friction = (0.0, 0.0) if shear == "bprime" else (c["cohesion"], c["friction"])
    return (c["Kphi"], c["Kc"], c["n"], cohesion, friction, c["Janosi"], c["elastic_K"],
            c["damping_R"])


# --- tangential values ---------------------------------------------------------------------


def _series(*k: float) -> float:
    return 1.0 / sum(1.0 / v for v in k)


@dataclass(frozen=True)
class PadTangentialValues:
    """Per-leg anchor bushing values (5.33.4 / 5.33.7 #2-#5)."""

    stiffness_N_m: tuple[float, ...]
    damping_actual_N_s_m: tuple[float, ...]
    damping_input_N_s_m: tuple[float, ...]
    adhesion_N: tuple[float, ...]
    friction: float
    k_t_L1_N_m: tuple[float, ...]
    k_lat_N_m: tuple[float, ...]
    k_soil_N_m: tuple[float, ...]
    k_janosi_N_m: tuple[float, ...] | None
    pad_area_m2: tuple[float, ...]
    cohesion_Pa: float
    friction_deg: float
    stiffness_mode: str
    interface: bool
    kappa: float = KAPPA_HORIZONTAL

    def meta(self) -> dict[str, Any]:
        out = asdict(self)
        out["basis"] = ("k = series(k_lat, kappa K A) (series), = k_t,L1 (l1_kt), series with "
                        "(c A + N_design tan phi) / K_J (janosi); k_lat = 1 / (1/k_t,L1 - "
                        "1/k_concrete); c_t = c_t,L1 sqrt(k / k_t,L1), input c_t / 2 (R7); "
                        "limit c A min(1, N / N_c) + N tan phi (5.33.7)")
        return out


def pad_tangential_values(params: Params, soil: SoilSet, pad_area_m2: Sequence[float], *,
                          stiffness_mode: str = "series", interface: bool = False
                          ) -> PadTangentialValues:
    """Values of the pad anchor bushings (module docstring)."""
    if stiffness_mode not in STIFFNESS_MODES:
        raise ValueError(f"stiffness_mode must be one of {STIFFNESS_MODES}")
    l1 = params.contact.rigid_floor.L1
    k_conc = float(params.get("contact.rigid_floor.concrete.k_N_m"))
    c = soil.cohesion_Pa * (INTERFACE_C_FACTOR if interface else 1.0)
    phi = soil.friction_deg * (INTERFACE_PHI_FACTOR if interface else 1.0)
    mu = math.tan(math.radians(phi))
    k_el = float(soil.chrono["elastic_K"])
    kt_l1, k_lat, k_soil, k_j, k_out, c_act, adh = [], [], [], [], [], [], []
    for i in range(len(LEG_ORDER)):
        kt = float(l1.bushing_stiffness_per_pad_N_m[i])
        kl = 1.0 / (1.0 / kt - 1.0 / k_conc)
        ks = KAPPA_HORIZONTAL * k_el * float(pad_area_m2[i])
        kj = (c * float(pad_area_m2[i]) + soil.design_loads_N[i] * mu) / float(soil.chrono["Janosi"])
        if stiffness_mode == "series":
            k = _series(kl, ks)
        elif stiffness_mode == "l1_kt":
            k = kt
        else:
            k = _series(kl, ks, kj)
        ct = float(l1.ct_per_pad_N_s_m[i]) * math.sqrt(k / kt)
        kt_l1.append(kt), k_lat.append(kl), k_soil.append(ks), k_j.append(kj)
        k_out.append(k), c_act.append(ct), adh.append(c * float(pad_area_m2[i]))
    return PadTangentialValues(
        stiffness_N_m=tuple(k_out), damping_actual_N_s_m=tuple(c_act),
        damping_input_N_s_m=tuple(0.5 * v for v in c_act), adhesion_N=tuple(adh), friction=mu,
        k_t_L1_N_m=tuple(kt_l1), k_lat_N_m=tuple(k_lat), k_soil_N_m=tuple(k_soil),
        k_janosi_N_m=tuple(k_j) if stiffness_mode == "janosi" else None,
        pad_area_m2=tuple(float(a) for a in pad_area_m2), cohesion_Pa=c, friction_deg=phi,
        stiffness_mode=stiffness_mode, interface=interface)


@dataclass(frozen=True)
class TrackTangentialValues:
    """Per-track anchor bushing values (5.33.7 #7)."""

    stiffness_N_m: float
    damping_actual_N_s_m: float
    damping_input_N_s_m: float
    friction: float
    k_rollers_N_m: float
    k_soil_N_m: float
    crawler_contact_area_m2: float

    def meta(self) -> dict[str, Any]:
        return {**asdict(self), "adhesion_N": 0.0,
                "basis": "k = series(6 x L1 crawler-sphere k_t, 0.8 K A_c / 2); c = (c_total/2) "
                         "sqrt(k / (kn_total/2)) (crawler_bushing zeta rule, ASSUMPTION); limit "
                         "N tan phi only (U-S9L-5)"}


def track_tangential_values(params: Params, soil: SoilSet, *, interface: bool = False
                            ) -> TrackTangentialValues:
    phi = soil.friction_deg * (INTERFACE_PHI_FACTOR if interface else 1.0)
    k_rollers = CRAWLER_ROLLERS_PER_TRACK * crawler_bushing_values(params).kt_N_m
    k_soil = KAPPA_HORIZONTAL * float(soil.chrono["elastic_K"]) * soil.crawler_contact_area_m2 / 2.0
    k = _series(k_rollers, k_soil)
    kn_track = float(params.get("contact.crawler.kn_total_N_m")) / 2.0
    c = float(params.get("contact.crawler.damping_total_N_s_m")) / 2.0 * math.sqrt(k / kn_track)
    return TrackTangentialValues(k, c, 0.5 * c, math.tan(math.radians(phi)), k_rollers, k_soil,
                                 soil.crawler_contact_area_m2)


# --- geometry helpers ----------------------------------------------------------------------


def _quat_from_matrix(m: NDArray[np.float64]) -> ch.ChQuaterniond:
    from outrigger_sim.frames import matrix_to_quat

    q = matrix_to_quat(m)
    return ch.ChQuaterniond(*(float(v) for v in q))


def _v(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


def plane_frame(params: Params, floor_normal: ArrayLike | None) -> tuple[NDArray[np.float64],
                                                                        NDArray[np.float64]]:
    """(point, rotation world <- plane) of the SCM plane: block-bottom height at x = y = 0,
    rotated about that point by ``floor_rotation(normal)`` (``scenarios.slope``)."""
    from outrigger_sim.scenarios.slope import floor_rotation

    p0 = np.array([0.0, 0.0, float(params.ground.crawler_bottom_z_m)
                   + BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M])
    rot = np.eye(3) if floor_normal is None else floor_rotation(np.asarray(floor_normal, float))
    return p0, rot


def crawler_box_specs(params: Params) -> list[dict[str, Any]]:
    """The 6 C envelope boxes (3.11.2) in body coordinates: centre, rotation about y [rad],
    size (length along the bottom, width, thickness), name. Bottom faces at the block bottom
    (``crawler_bottom_z + 0.004``) for the flat box and through the hinge lines for the ramps."""
    z0 = float(params.ground.crawler_bottom_z_m) + BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
    t = CRAWLER_BOX_THICKNESS_M
    width = TRACK_Y_RANGE_M[1] - TRACK_Y_RANGE_M[0]
    y_mid = 0.5 * (TRACK_Y_RANGE_M[0] + TRACK_Y_RANGE_M[1])
    out = []
    for side, sy in (("L", 1.0), ("R", -1.0)):
        y = sy * y_mid
        # flat
        x0, x1 = FLAT_X_M
        out.append({"name": f"crawler_{side}_flat", "centre": [0.5 * (x0 + x1), y, z0 + t / 2],
                    "angle_y_rad": 0.0, "size": [x1 - x0, width, t]})
        # front ramp: bottom z = z0 + s (x - x0), s > 0, rotation -atan(s) about +y
        for nm, (xa, xb), s, hinge in (("front", FRONT_RAMP_X_M, FRONT_RAMP_SLOPE, FRONT_RAMP_X_M[0]),
                                       ("rear", REAR_RAMP_X_M, -REAR_RAMP_SLOPE, REAR_RAMP_X_M[1])):
            ang = -math.atan(s)  # rotation about +y maps x -> (cos a, 0, -sin a)
            xm = 0.5 * (xa + xb)
            zb = z0 + s * (xm - hinge)  # bottom-face centre height
            length = (xb - xa) / math.cos(ang)
            n_up = np.array([math.sin(ang), 0.0, math.cos(ang)])  # rotated +z
            c = np.array([xm, y, zb]) + n_up * (t / 2)
            out.append({"name": f"crawler_{side}_{nm}", "centre": c.tolist(), "angle_y_rad": ang,
                        "size": [length, width, t]})
    return out


RAY_SHAPES = ("mesh", "convex")
DEFAULT_RAY_SHAPE = "mesh"
"""SCM ray-target shapes (dynamics_model.md 5.34.10, P1-V0). ``"mesh"`` (default) = static
triangle soups (``ChCollisionShapeTriangleMesh(..., is_static=True)`` -> Bullet
``cbtBvhTriangleMeshShape``, exact ray-triangle test; ``ChCollisionModelBullet.cpp:556``);
``"convex"`` = the former ``ChCollisionShapeBox`` / ``ChCollisionShapeConvexHull`` whose ray test
is the iterative sub-simplex convex cast (``cbtCollisionWorld.cpp:300``) and hits the bottom up
to about 10 mm too low. The S9 bodies have no rigid contact at all (only SCM rays), so a static
mesh on a moving body is safe here (no concave-concave narrow phase is ever needed)."""


def box_triangles(centre: ArrayLike, angle_y_rad: float, size: ArrayLike
                  ) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """(8 vertices, 12 outward triangles) of a box rotated about +y by ``angle_y_rad``."""
    hx, hy, hz = (0.5 * float(v) for v in size)
    c, s = math.cos(angle_y_rad), math.sin(angle_y_rad)
    rot = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
    corners = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1)
                        for sz in (-1, 1)])
    verts = corners @ rot.T + np.asarray(centre, dtype=float)
    # corner index = 4 * (sx > 0) + 2 * (sy > 0) + (sz > 0)
    faces = np.array([[0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3],   # -z, +z
                      [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],   # -y, +y
                      [0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5]],  # -x, +x
                     dtype=np.int64)
    return verts, faces


def add_ray_mesh(body: ch.ChBody, pieces: Sequence[tuple[ArrayLike, ArrayLike]],
                 material: ch.ChContactMaterial) -> int:
    """Add one static triangle-soup collision shape (all ``pieces`` (vertices in the body COG
    frame, triangles)) to ``body``; returns the number of triangles."""
    soup = ch.ChTriangleMeshSoup()
    n = 0
    for verts, faces in pieces:
        v = np.asarray(verts, dtype=float)
        for a, b, c in np.asarray(faces, dtype=np.int64):
            soup.AddTriangle(chvec(v[a]), chvec(v[b]), chvec(v[c]))
            n += 1
    body.AddCollisionShape(ch.ChCollisionShapeTriangleMesh(material, soup, True, False, 0.0),
                           ch.ChFramed())
    return n


def add_pad_ray_mesh(body: ch.ChBody, leg_index: int, material: ch.ChContactMaterial, *,
                     pad_variant: str | None, offset_m: ArrayLike) -> int:
    """The C8 pad hull of the pad type as a static triangle soup (OBJ triangles + ``offset_m``)."""
    from outrigger_sim.chrono.sim_shapes import _require_file, pad_shape_entries, read_obj_pieces

    _, hull = pad_shape_entries(LEG_ORDER[leg_index], pad_variant)
    off = np.asarray(offset_m, dtype=float)
    pieces = [(v + off, f) for v, f in read_obj_pieces(_require_file(hull))]
    body.EnableCollision(True)
    return add_ray_mesh(body, pieces, material)


def pad_bottom_outline_local_m(pad_variant: str | None, leg_index: int, offset_m: ArrayLike,
                               *, tol_m: float = 1.0e-4) -> NDArray[np.float64]:
    """Bottom-face polygon of the pad hull OBJ (vertices within ``tol_m`` of the lowest one),
    counter-clockwise in xy, as (k, 3) points in the body frame given by ``offset_m`` (the
    ``add_pad_ray_mesh`` offset)."""
    from outrigger_sim.chrono.sim_shapes import _require_file, pad_shape_entries, read_obj_pieces

    _, hull = pad_shape_entries(LEG_ORDER[leg_index], pad_variant)
    v = np.vstack([p[0] for p in read_obj_pieces(_require_file(hull))]) + np.asarray(offset_m, float)
    zmin = float(v[:, 2].min())
    bottom = v[v[:, 2] <= zmin + tol_m]
    idx = convex_hull_2d(bottom[:, :2])
    out = bottom[idx].copy()
    out[:, 2] = zmin
    return out


def convex_hull_2d(xy: ArrayLike) -> NDArray[np.int64]:
    """Indices of the 2D convex hull, counter-clockwise (monotone chain, collinear dropped)."""
    p = np.asarray(xy, dtype=float)
    order = np.lexsort((p[:, 1], p[:, 0]))

    def cross(o: int, a: int, b: int) -> float:
        return float((p[a, 0] - p[o, 0]) * (p[b, 1] - p[o, 1]) - (p[a, 1] - p[o, 1]) * (p[b, 0] - p[o, 0]))

    lower: list[int] = []
    for i in order:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], i) <= 1e-15:
            lower.pop()
        lower.append(int(i))
    upper: list[int] = []
    for i in order[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], i) <= 1e-15:
            upper.pop()
        upper.append(int(i))
    return np.array(lower[:-1] + upper[:-1], dtype=np.int64)


def inside_convex_polygon(poly_xy: ArrayLike, pts_xy: ArrayLike, *, tol: float = 1e-12) -> NDArray[np.bool_]:
    """True for points strictly inside a counter-clockwise convex polygon (edges excluded)."""
    poly = np.asarray(poly_xy, dtype=float)
    pts = np.asarray(pts_xy, dtype=float).reshape(-1, 2)
    inside = np.ones(len(pts), dtype=bool)
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        c = (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0])
        inside &= c > tol * max(1.0, float(np.hypot(*(b - a))))
    return inside


def node_stats_in_outline(terrain: Any, plane_point: ArrayLike, plane_rot: NDArray[np.float64],
                          grid_m: float, outline_world_m: ArrayLike) -> dict[str, Any]:
    """SCM node state (``GetNodeInfo``) of the grid nodes strictly inside a footprint polygon
    projected on the SCM plane. Returns the node count inside, the count in contact (sigma > 0),
    the mean sinkage of the nodes inside and of the contact nodes [m] (``NodeInfo.sinkage`` =
    initial level - level, along the plane normal; nodes never touched read 0) and the mean
    pressure of the contact nodes [Pa]. Record rate only (one Python call per node)."""
    p0 = np.asarray(plane_point, dtype=float)
    r = np.asarray(plane_rot, dtype=float)
    q = (np.asarray(outline_world_m, dtype=float) - p0) @ r  # plane coordinates
    poly = q[convex_hull_2d(q[:, :2]), :2]
    d = float(grid_m)
    i0, i1 = int(math.floor(poly[:, 0].min() / d)), int(math.ceil(poly[:, 0].max() / d))
    j0, j1 = int(math.floor(poly[:, 1].min() / d)), int(math.ceil(poly[:, 1].max() / d))
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    nodes = np.column_stack([ii.ravel() * d, jj.ravel() * d])
    nodes = nodes[inside_convex_polygon(poly, nodes)]
    sink, sigma = np.empty(len(nodes)), np.empty(len(nodes))
    for k, (x, y) in enumerate(nodes):
        w = p0 + r @ np.array([x, y, 0.0])
        info = terrain.GetNodeInfo(ch.ChVector3d(float(w[0]), float(w[1]), float(w[2])))
        sink[k], sigma[k] = float(info.sinkage), float(info.sigma)
    contact = sigma > 0.0
    # convex hull of the contact node points (the SCM patch b = 2 area / perimeter of the hull of
    # the patch node points, SCMTerrain.cpp:1316-1378; P1-V16a discrete reference)
    hull_area = hull_perimeter = None
    if int(contact.sum()) >= 3:
        pc = nodes[contact]
        hidx = convex_hull_2d(pc)
        if len(hidx) >= 3:
            h = pc[hidx]
            hn = np.roll(h, -1, axis=0)
            hull_area = float(0.5 * abs(np.sum(h[:, 0] * hn[:, 1] - hn[:, 0] * h[:, 1])))
            hull_perimeter = float(np.sum(np.hypot(*(hn - h).T)))
    return {"n_inside": int(len(nodes)), "n_contact": int(contact.sum()),
            "n_sigma_negative": int((sigma < 0.0).sum()),
            "sinkage_mean_inside_m": float(sink.mean()) if len(nodes) else None,
            "sinkage_mean_contact_m": float(sink[contact].mean()) if contact.any() else None,
            "sigma_mean_contact_Pa": float(sigma[contact].mean()) if contact.any() else None,
            "sigma_sum_area_N": float(sigma.sum() * d * d),
            "contact_hull_area_m2": hull_area, "contact_hull_perimeter_m": hull_perimeter}


GRAVITY_RAMP_SHAPES = ("poly345", "linear", "step")
MACHINE_GRAVITY_RAMP_S = 3.0
MACHINE_GRAVITY_HOLD_S = 2.0
"""P2 settle rule (dynamics_model.md 5.34.2): gravity magnitude Poly345 over 3 s, hold 2 s,
judge on the last 1 s mean."""
SINGLE_PAD_LOAD_RAMP_S = 1.0
"""P1 single pad: vertical load Poly345 over 1 s (5.34.3 P1-V0 (iii), V16: no sudden load)."""


def gravity_ramp_factor(t_s: float, ramp_s: float, shape: str = "poly345") -> float:
    """Gravity (load) factor in [0, 1]: Poly345 ``10u^3 - 15u^4 + 6u^5``, linear ``u``
    (``u = t / ramp``), or ``step`` (1 from t = 0, the former sudden load)."""
    if shape not in GRAVITY_RAMP_SHAPES:
        raise ValueError(f"ramp shape must be one of {GRAVITY_RAMP_SHAPES}, got {shape!r}")
    if shape == "step" or ramp_s <= 0.0:
        return 1.0
    u = min(max(float(t_s) / float(ramp_s), 0.0), 1.0)
    return u if shape == "linear" else 10.0 * u ** 3 - 15.0 * u ** 4 + 6.0 * u ** 5


def _rigid_body(name: str, mass: float, inertia: ArrayLike, com_body: ArrayLike,
                pose: BodyPose) -> ch.ChBody:
    i = np.asarray(inertia, dtype=float)
    body = ch.ChBody()
    body.SetName(name)
    body.SetMass(float(mass))
    body.SetInertiaXX(ch.ChVector3d(i[0, 0], i[1, 1], i[2, 2]))
    body.SetInertiaXY(ch.ChVector3d(i[0, 1], i[0, 2], i[1, 2]))
    body.SetPos(chvec(pose.to_world(com_body)))
    body.SetRot(pose.chrono_quat())
    return body


def split_body_props(params: Params, leg_index: int, part: str) -> tuple[float, NDArray, NDArray]:
    """(mass, com_retracted_body, inertia) of ``legs.<leg>.pad_body`` / ``rod_body``."""
    leg = LEG_ORDER[leg_index]
    base = f"legs.{leg}.{part}"
    return (float(params.get(f"{base}.mass_kg")),
            np.asarray(params.get(f"{base}.com_m"), dtype=float),
            np.asarray(params.get(f"{base}.inertia_kg_m2"), dtype=float))


# --- SCM force reader and normal sources -----------------------------------------------------


class ScmForceReader:
    """Reads the SCM resultant on the pads and the superstructure once per step (copies).

    ``GetContactForceBody`` gives the force (world) and the moment about the body COM (world)
    accumulated by the loader at the start of the step just taken (``SCMTerrain.cpp:1489``).
    ``terrain`` is one ``SCMTerrain`` or a sequence of them (dual terrain, U-S9G-1): the force
    and moment on each body are the sums over the terrains (each loader only knows the hits of
    its own active domains; the moments are all about the body COM, so they add). With one
    terrain the values are those of that terrain unchanged (no extra addition)."""

    def __init__(self, terrain: Any, pads: Sequence[ch.ChBody], superstructure: ch.ChBody) -> None:
        self.terrains: tuple[Any, ...] = (tuple(terrain) if isinstance(terrain, (list, tuple))
                                          else (terrain,))
        self.terrain = self.terrains[0]
        self.pads = tuple(pads)
        self.superstructure = superstructure
        self.pad_force_N = np.zeros((len(pads), 3))
        self.pad_torque_Nm = np.zeros((len(pads), 3))
        self.sup_force_N = np.zeros(3)
        self.sup_torque_Nm = np.zeros(3)
        self._f = ch.ChVector3d(0, 0, 0)
        self._t = ch.ChVector3d(0, 0, 0)

    def _body(self, body: ch.ChBody) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        f, t = self._f, self._t
        first = self.terrains[0]
        first.GetContactForceBody(body, f, t)
        force = np.array([f.x, f.y, f.z])
        torque = np.array([t.x, t.y, t.z])
        for terrain in self.terrains[1:]:
            terrain.GetContactForceBody(body, f, t)
            force += (f.x, f.y, f.z)
            torque += (t.x, t.y, t.z)
        return force, torque

    def refresh(self) -> None:
        for i, pad in enumerate(self.pads):
            self.pad_force_N[i], self.pad_torque_Nm[i] = self._body(pad)
        self.sup_force_N, self.sup_torque_Nm = self._body(self.superstructure)


class PadNormals:
    """Signed SCM normal force per pad along the plane normal (``normal_force_source``)."""

    def __init__(self, reader: ScmForceReader, normal: NDArray[np.float64]) -> None:
        self.reader = reader
        self.normal = np.asarray(normal, dtype=float)

    def __call__(self) -> list[float]:
        n = self.normal
        return [float(f[0] * n[0] + f[1] * n[1] + f[2] * n[2]) for f in self.reader.pad_force_N]


class TrackNormals:
    """SCM normal force on the superstructure split onto the two tracks (5.33.7 #7): moment
    about the body x line through the block-bottom centre, ``N_L,R = (N +- M_x / y_t) / 2``,
    negatives clipped to 0."""

    def __init__(self, reader: ScmForceReader, normal: NDArray[np.float64],
                 midline_point_body_m: ArrayLike, com_body_m: ArrayLike) -> None:
        self.reader = reader
        self.normal = np.asarray(normal, dtype=float)
        self.p_local = np.asarray(midline_point_body_m, dtype=float) - np.asarray(com_body_m, float)
        self.last_raw_N = np.zeros(2)

    def __call__(self) -> list[float]:
        sup = self.reader.superstructure
        f = self.reader.sup_force_N
        n_tot = float(f @ self.normal)
        p = _v(sup.TransformPointLocalToParent(chvec(self.p_local)))
        cog = _v(sup.GetPos())
        moment = self.reader.sup_torque_Nm + np.cross(cog - p, f)
        x_axis = _v(sup.GetRot().GetAxisX())
        mx = float(moment @ x_axis)
        n_l = 0.5 * (n_tot + mx / TRACK_Y_M)
        n_r = 0.5 * (n_tot - mx / TRACK_Y_M)
        self.last_raw_N = np.array([n_l, n_r])
        return [max(n_l, 0.0), max(n_r, 0.0)]


# --- swivel stabiliser -----------------------------------------------------------------------


class SwivelStabiliser:
    """Rotational pad <-> ground bushing that lives while the pad anchor bushing exists (#6)."""

    def __init__(self, system: ch.ChSystem, ground: ch.ChBody, pads: Sequence[ch.ChBody],
                 plane_rot: NDArray[np.float64], stiffness_N_m_rad: float = SWIVEL_K_N_M_RAD,
                 tilt_warn_deg: Sequence[float] = (10.0,) * 4) -> None:
        self.system = system
        self.ground = ground
        self.pads = tuple(pads)
        self.plane_rot = np.asarray(plane_rot, dtype=float)
        self.k = float(stiffness_N_m_rad)
        self.tilt_warn_deg = tuple(float(v) for v in tilt_warn_deg)
        self._containers: list[Any] = [None] * len(pads)
        self._loads: list[Any] = [None] * len(pads)
        self.active = np.zeros(len(pads), dtype=bool)
        self.tilt_max_deg = np.zeros(len(pads))
        self.tilt_last_deg = np.zeros(len(pads))
        self.events: list[tuple[float, int, int]] = []
        self.warnings: list[str] = []
        self._warned = np.zeros(len(pads), dtype=bool)

    def tilt_deg(self) -> NDArray[np.float64]:
        """Angle between each pad's z axis (pad normal) and the plane normal [deg]."""
        n = self.plane_rot[:, 2]
        out = np.empty(len(self.pads))
        for i, pad in enumerate(self.pads):
            z = _v(pad.GetRot().GetAxisZ())
            out[i] = math.degrees(math.acos(max(-1.0, min(1.0, float(z @ n)))))
        return out

    def _create(self, i: int) -> None:
        pad = self.pads[i]
        r_pad = _quat_to_mat(pad.GetRot())
        rel = self.plane_rot.T @ r_pad
        yaw = math.atan2(rel[1, 0], rel[0, 0])
        rz = np.array([[math.cos(yaw), -math.sin(yaw), 0.0], [math.sin(yaw), math.cos(yaw), 0.0],
                       [0.0, 0.0, 1.0]])
        q_b = _quat_from_matrix(self.plane_rot @ rz)
        pos = ch.ChVector3d(pad.GetPos())
        zero = ch.ChVector3d(0.0, 0.0, 0.0)
        kv = ch.ChVector3d(self.k, self.k, self.k)
        load = ch.ChLoadBodyBodyBushingMate(pad, self.ground, ch.ChFramed(pos, q_b), zero, zero,
                                            kv, zero)
        # neutral = pad parallel to the plane (pad axes = plane axes turned by the yaw)
        load.SetApplicationFrameA(ch.ChFramed(ch.ChVector3d(0.0, 0.0, 0.0), ch.QUNIT))
        load.SetApplicationFrameB(ch.ChFramed(self.ground.TransformPointParentToLocal(pos),
                                              self.ground.GetRot().GetConjugate() * q_b))
        container = ch.ChLoadContainer()
        self.system.Add(container)
        container.Add(load)
        self._containers[i] = container
        self._loads[i] = load
        self.active[i] = True

    def _remove(self, i: int) -> None:
        if self._containers[i] is not None:
            self.system.RemoveOtherPhysicsItem(self._containers[i])
        self._containers[i] = None
        self._loads[i] = None
        self.active[i] = False

    def update(self, in_contact: NDArray[np.bool_], t_s: float) -> None:
        for i, on in enumerate(np.asarray(in_contact, dtype=bool)):
            if on and not self.active[i]:
                self._create(i)
                self.events.append((t_s, i, 1))
            elif not on and self.active[i]:
                self._remove(i)
                self.events.append((t_s, i, 2))
        tilt = self.tilt_deg()
        self.tilt_last_deg = tilt
        self.tilt_max_deg = np.maximum(self.tilt_max_deg, np.where(self.active, tilt, 0.0))
        for i in range(len(self.pads)):
            if self.active[i] and tilt[i] > self.tilt_warn_deg[i] and not self._warned[i]:
                self._warned[i] = True
                self.warnings.append(f"WARN_PAD_TILT_OVER_RANGE:{LEG_ORDER[i] if len(self.pads) == 4 else i}"
                                     f":{tilt[i]:.2f}deg@t={t_s:.4f}s")

    def torque_on_pad_world_Nm(self) -> NDArray[np.float64]:
        """Stabiliser torque on each pad (world) from the small-rotation law (0 when absent)."""
        out = np.zeros((len(self.pads), 3))
        for i, load in enumerate(self._loads):
            if load is None:
                continue
            fa = load.GetAbsoluteFrameA() if hasattr(load, "GetAbsoluteFrameA") else None
            fb = load.GetAbsoluteFrameB()
            r_b = _quat_to_mat(fb.GetRot())
            r_a = _quat_to_mat(self.pads[i].GetRot()) if fa is None else _quat_to_mat(fa.GetRot())
            rel = r_b.T @ r_a
            ang = math.acos(max(-1.0, min(1.0, (np.trace(rel) - 1.0) / 2.0)))
            if ang < 1e-15:
                continue
            axis = np.array([rel[2, 1] - rel[1, 2], rel[0, 2] - rel[2, 0], rel[1, 0] - rel[0, 1]])
            axis /= 2.0 * math.sin(ang)
            out[i] = -r_b @ (self.k * ang * axis)
        return out

    def meta(self) -> dict[str, Any]:
        return {"type": "ChLoadBodyBodyBushingMate pad <-> ground (translation 0, rotation k_sw, "
                        "damping 0), neutral = parallel to the SCM plane with the pad yaw at "
                        "creation; created / removed with the pad anchor bushing (R15)",
                "stiffness_N_m_rad": self.k, "tilt_warn_deg": list(self.tilt_warn_deg),
                "tilt_max_deg": self.tilt_max_deg.tolist(), "events": [list(e) for e in self.events],
                "warnings": list(self.warnings)}


def _quat_to_mat(q: Any) -> NDArray[np.float64]:
    from outrigger_sim.frames import quat_to_matrix

    return quat_to_matrix(np.array([q.e0, q.e1, q.e2, q.e3], dtype=float))


# --- SCM terrain -------------------------------------------------------------------------------


def make_terrain(system: ch.ChSystem, soil: SoilSet, shear: str, plane_point: ArrayLike,
                 plane_rot: NDArray[np.float64], *, grid_m: float = GRID_M,
                 size_m: tuple[float, float] = TERRAIN_SIZE_M) -> tuple[Any, dict[str, Any]]:
    """SCMTerrain on the plane with the soil set (no visualisation mesh); returns (terrain,
    meta). Active domains are added by the caller before :func:`initialize_terrain`."""
    terrain = veh.SCMTerrain(system, False)
    terrain.SetReferenceFrame(ch.ChCoordsysd(chvec(plane_point), _quat_from_matrix(plane_rot)))
    values = scm_call_values(soil, shear)
    terrain.SetSoilParameters(*values)
    meta = {"soil": soil.meta(), "scm_shear": SHEAR_OFF_TEXT if shear == "bprime"
            else "native (set c, phi in SCM; no anchor bushings; comparison only)",
            "scm_shear_mode": shear,
            "SetSoilParameters": dict(zip(("Kphi", "Kc", "n", "cohesion", "friction", "Janosi",
                                           "elastic_K", "damping_R"), values, strict=True)),
            "grid_m": grid_m, "size_m": list(size_m),
            "plane_point_world_m": np.asarray(plane_point, float).tolist(),
            "plane_rotation": np.asarray(plane_rot, float).tolist(),
            "bulldozing": False, "active_domains": []}
    return terrain, meta


def add_active_domain(terrain: Any, meta: dict[str, Any], body: ch.ChBody, centre_local: ArrayLike,
                      dims: ArrayLike, name: str) -> None:
    terrain.AddActiveDomain(body, chvec(centre_local), chvec(dims))
    meta["active_domains"].append({"name": name, "body": str(body.GetName()),
                                   "centre_body_local_m": np.asarray(centre_local, float).tolist(),
                                   "dims_m": np.asarray(dims, float).tolist()})


def initialize_terrain(terrain: Any, meta: Mapping[str, Any]) -> None:
    sx, sy = meta["size_m"]
    terrain.Initialize(float(sx), float(sy), float(meta["grid_m"]))


# --- the machine model -------------------------------------------------------------------------


StepHook = Callable[["S9Model", float], None]
RecordHook = Callable[["S9Model", ProbeState], None]


class S9Model:
    """S9 SCM four-leg model (module docstring).

    Args:
        params: Loaded with ``model="L2b_NSC"`` and the pad type applied
            (``pad_variants.apply_pad_variant``).
        soil: Soil set (:func:`load_soil_set`).
        pad_variant_meta: ``pad_variants.pad_variant_meta`` of the same type (pad areas).
        shear: ``"bprime"`` (default) or ``"native"``.
        floor_normal: SCM plane normal (world); None = level. The machine starts on the crawler
            rotated with the plane (as ``run_S7C.l2b_crawler_start``).
        extensions_m: Start references (default 0 = retracted, legs hanging).
        dt_s: Step (default ``simulation.L2b_NSC.dt_s`` = 1e-4 s).
        stiffness_mode, interface: Anchor sensitivities (U-S9L-2 / 3).
        swivel_stiffness_N_m_rad: ``k_sw``; 0 = no stabiliser (P1-L4 comparison).
        crawler_bushings: Track anchors (bprime only).
        grid_m: SCM grid (the pad terrain grid when ``crawler_grid_m`` is set).
        ray_shape: SCM ray targets, ``"mesh"`` (default) or ``"convex"`` (:data:`RAY_SHAPES`).
        crawler_grid_m: None = one SCM terrain for pads and tracks; a value = dual terrain, the
            tracks on a second terrain with this grid (U-S9G-1 M14s: pads 1 / 2 cm, crawler 4 cm).
    """

    def __init__(self, params: Params, soil: SoilSet, pad_variant_meta: Mapping[str, Any], *,
                 shear: str = "bprime", floor_normal: ArrayLike | None = None,
                 extensions_m: Sequence[float] | None = None, dt_s: float | None = None,
                 stiffness_mode: str = "series", interface: bool = False,
                 swivel_stiffness_N_m_rad: float = SWIVEL_K_N_M_RAD, crawler_bushings: bool = True,
                 grid_m: float = GRID_M, force_saturation: bool = True,
                 actuator_ramp_s: float | None = None, num_threads: int = SCM_THREADS,
                 ray_shape: str = DEFAULT_RAY_SHAPE, crawler_grid_m: float | None = None) -> None:
        if params.l2b is None:
            raise ValueError('params must be loaded with model="L2b_NSC"')
        if shear not in SCM_SHEAR_MODES:
            raise ValueError(f"shear must be one of {SCM_SHEAR_MODES}")
        if ray_shape not in RAY_SHAPES:
            raise ValueError(f"ray_shape must be one of {RAY_SHAPES}, got {ray_shape!r}")
        self.ray_shape = ray_shape
        self.params = params
        self.soil = soil
        self.shear = shear
        self.pad_variant_meta = dict(pad_variant_meta)
        areas = [float(self.pad_variant_meta["pad_bottom_area_m2"][leg]) for leg in LEG_ORDER]
        dt = float(params.get("simulation.L2b_NSC.dt_s")) if dt_s is None else float(dt_s)
        bundle = make_system(params, "L1", dt=dt, floor_plate=False)
        self.bundle = bundle
        self.system: ch.ChSystem = bundle.system
        self.floor: ch.ChBody = bundle.floor
        self.dt_s = bundle.dt_s
        self.num_threads = int(num_threads)
        if self.num_threads > 0:  # SCM ray casting uses num_threads_chrono (OpenMP)
            self.system.SetNumThreads(self.num_threads, 1, 1)
        p_plane, r_plane = plane_frame(params, floor_normal)
        self.plane_point_world_m = p_plane
        self.plane_rot = r_plane
        self.normal_world = r_plane[:, 2].copy()
        self.floor_point_world_m = tuple(float(v) for v in p_plane)
        # machine pose: rotated with the plane about the plane point (crawler start)
        from outrigger_sim.frames import matrix_to_quat

        origin = p_plane - r_plane @ p_plane
        self.pose = BodyPose(tuple(float(v) for v in origin),
                             tuple(float(v) for v in matrix_to_quat(r_plane)))
        direction = extension_direction(params)
        s_ref0 = np.zeros(4) if extensions_m is None else np.asarray(extensions_m, float).reshape(4)
        a = params.l2b.actuator
        k0 = np.array([axial_stiffness_N_m(float(s_ref0[i]), bulk_modulus_Pa=a.oil_bulk_modulus_eff_Pa,
                                           head_area_m2=a.head_area_m2[i],
                                           dead_length_m=a.oil_dead_length_m,
                                           k_rod_N_m=a.k_rod_N_m[i], k_frame_N_m=a.frame_stiffness_N_m,
                                           k_concrete_N_m=None) for i in range(4)])
        g_axis = float(np.asarray(gravity_vector(params)) @ (self.pose.rotation @ direction))
        m_moving = np.array([leg.moving_part.mass_kg for leg in params.legs])
        f0 = -m_moving * g_axis  # legs hanging (rod + pad on the force law)
        ext = s_ref0 - f0 / k0
        self.extensions_m = tuple(float(v) for v in ext)
        self.start_s_ref_m = tuple(float(v) for v in s_ref0)
        self.start_forces_N = f0
        self.k_ax0_N_m = k0

        # superstructure + crawler C boxes
        sup = make_superstructure(params, self.pose)
        com_body = np.asarray(params.superstructure.mass_properties.com_m, dtype=float)
        sup.EnableCollision(True)
        self.crawler_boxes = crawler_box_specs(params)
        if ray_shape == "mesh":
            add_ray_mesh(sup, [box_triangles(np.asarray(b["centre"]) - com_body, float(b["angle_y_rad"]),
                                             b["size"]) for b in self.crawler_boxes],
                         ch.ChContactMaterialSMC())
        else:
            for box in self.crawler_boxes:
                q = ch.QuatFromAngleY(float(box["angle_y_rad"]))
                sx, sy, sz = box["size"]
                sup.AddCollisionShape(ch.ChCollisionShapeBox(ch.ChContactMaterialSMC(), sx, sy, sz),
                                      ch.ChFramed(chvec(np.asarray(box["centre"]) - com_body), q))
        set_family(sup, FAMILY_SUPERSTRUCTURE, no_collision_with=(FAMILY_ROD,))
        self.system.Add(sup)
        self.superstructure = sup
        self.sup_com_body_m = com_body
        self.origin_in_cog_frame_ch = chvec(-com_body)

        # legs: rod + pad, force motors (PRISMATIC), spherical joints
        q_link = self.pose.chrono_quat() * ch.QuatFromAngleX(np.pi)
        rods, pads, motors, functions, joints = [], [], [], [], []
        self.ball_local_pad_m, self.pad_bottom_local_pad_m, self.rod_com_retracted_m = [], [], []
        self.pad_com_retracted_m = []
        for i, leg in enumerate(params.legs):
            m_r, c_r, i_r = split_body_props(params, i, "rod_body")
            m_p, c_p, i_p = split_body_props(params, i, "pad_body")
            rod = _rigid_body(f"rod_{leg.name}", m_r, i_r, c_r + ext[i] * direction, self.pose)
            pad = _rigid_body(f"pad_{leg.name}", m_p, i_p, c_p + ext[i] * direction, self.pose)
            self.rod_com_retracted_m.append(c_r)
            self.pad_com_retracted_m.append(c_p)
            pad.EnableCollision(True)
            if ray_shape == "mesh":
                add_pad_ray_mesh(pad, i, ch.ChContactMaterialSMC(),
                                 pad_variant=self.pad_variant_meta["pad_variant"], offset_m=-c_p)
            else:
                add_pad_hull(pad, params, i, ch.ChContactMaterialSMC(),
                             pad_variant=self.pad_variant_meta["pad_variant"], offset_m=-c_p)
            set_family(pad, FAMILY_ROD, no_collision_with=(FAMILY_SUPERSTRUCTURE, FAMILY_ROD))
            self.system.Add(rod)
            self.system.Add(pad)
            attachment = np.asarray(leg.attachment_point_m, dtype=float)
            frame_body = ch.ChFramed(chvec(self.pose.to_world(attachment)), q_link)
            frame_rod = ch.ChFramed(chvec(self.pose.to_world(attachment + ext[i] * direction)), q_link)
            motor, function = make_force_motor(rod, sup, frame_rod, frame_body,
                                               name=f"motor_{leg.name}", free_xy=False)
            self.system.Add(motor)
            ball_body = pad_sphere_centre_body_m(params, i, float(ext[i]))
            joint = ch.ChLinkLockSpherical()
            joint.SetName(f"swivel_{leg.name}")
            joint.Initialize(pad, rod, ch.ChFramed(chvec(self.pose.to_world(ball_body)), ch.QUNIT))
            self.system.Add(joint)
            self.ball_local_pad_m.append(ball_body - (c_p + ext[i] * direction))
            self.pad_bottom_local_pad_m.append(pad_bottom_body_m(params, i, float(ext[i]))
                                               - (c_p + ext[i] * direction))
            rods.append(rod), pads.append(pad), motors.append(motor), functions.append(function)
            joints.append(joint)
        self.legs: tuple[ch.ChBody, ...] = tuple(rods)
        """Rod bodies (motor body 1; the L2bEngine 'legs')."""
        self.pads: tuple[ch.ChBody, ...] = tuple(pads)
        self.motors = tuple(motors)
        self.joints = tuple(joints)
        self.sphere_radii_m = tuple(leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs)

        self.actuator = L2bForceActuator.from_params(
            params, self.motors, functions, s_ref0, force_saturation=force_saturation,
            include_concrete=False, ramp_s=actuator_ramp_s)
        self.actuator.set_initial_force(f0)

        # SCM terrain: one (pads + tracks) or two (pad terrain + crawler terrain, U-S9G-1 M14s;
        # active domains of the two do not overlap, so no node is cast twice, 5.34.5)
        self.dual_terrain = crawler_grid_m is not None
        terrain, tmeta = make_terrain(self.system, soil, shear, p_plane, r_plane, grid_m=grid_m)
        if self.dual_terrain:
            c_terrain, c_meta = make_terrain(self.system, soil, shear, p_plane, r_plane,
                                             grid_m=float(crawler_grid_m))
        else:
            c_terrain, c_meta = terrain, tmeta
        self.terrain = terrain
        """Pad terrain (the only terrain when single)."""
        self.pad_terrain = terrain
        self.crawler_terrain = c_terrain
        self.terrains: tuple[Any, ...] = (terrain, c_terrain) if self.dual_terrain else (terrain,)
        self.pad_grid_m = float(grid_m)
        self.crawler_grid_m = float(crawler_grid_m) if self.dual_terrain else float(grid_m)
        for i, pad in enumerate(pads):
            centre = np.asarray(self.pad_bottom_local_pad_m[i])
            add_active_domain(terrain, tmeta, pad, centre,
                              (PAD_DOMAIN_XY_M, PAD_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M),
                              f"pad_{LEG_ORDER[i]}")
        z_block = float(params.ground.crawler_bottom_z_m) + BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
        x_mid = 0.5 * (REAR_RAMP_X_M[0] + FRONT_RAMP_X_M[1])
        for side, sy in (("L", 1.0), ("R", -1.0)):
            centre = np.array([x_mid, sy * TRACK_Y_M, z_block]) - com_body
            add_active_domain(c_terrain, c_meta, sup, centre,
                              (*TRACK_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M), f"track_{side}")
        initialize_terrain(terrain, tmeta)
        if self.dual_terrain:
            initialize_terrain(c_terrain, c_meta)
        tmeta["layout"] = "dual (pad terrain + crawler terrain)" if self.dual_terrain else "single"
        tmeta["crawler_terrain"] = c_meta if self.dual_terrain else None
        tmeta["ray_shape"] = ray_shape
        self.terrain_meta = tmeta
        self.forces = ScmForceReader(list(self.terrains), pads, sup)
        self.pad_outline_local_m = [
            pad_bottom_outline_local_m(self.pad_variant_meta["pad_variant"], i, -self.pad_com_retracted_m[i])
            for i in range(len(pads))]
        self.gravity_factor = 1.0

        # anchor bushings (bprime)
        self.pad_values = pad_tangential_values(params, soil, areas, stiffness_mode=stiffness_mode,
                                                interface=interface)
        self.track_values = track_tangential_values(params, soil, interface=interface)
        surface_point = p_plane
        self.pad_bushing: GroundBushingCoulomb | None = None
        self.crawler_bushing: GroundBushingCoulomb | None = None
        self.swivel: SwivelStabiliser | None = None
        slip_v = float(params.contact.rigid_floor.L1.slip_damping_reenable_speed_m_s)
        self.pad_normals = PadNormals(self.forces, self.normal_world)
        flat_centre_x = 0.5 * (FLAT_X_M[0] + FLAT_X_M[1])
        self.track_points_body_m = [np.array([flat_centre_x, sy * TRACK_Y_M, z_block])
                                    for sy in (1.0, -1.0)]
        self.track_normals = TrackNormals(self.forces, self.normal_world,
                                          (flat_centre_x, 0.0, z_block), com_body)
        if shear == "bprime":
            specs = [PadBushingSpec(name=leg.name, body=pads[i],
                                    sphere_centre_body_local_m=tuple(float(c) for c in self.ball_local_pad_m[i]),
                                    sphere_radius_m=self.sphere_radii_m[i],
                                    stiffness_N_m=self.pad_values.stiffness_N_m[i],
                                    damping_input_N_s_m=self.pad_values.damping_input_N_s_m[i],
                                    adhesion_N=self.pad_values.adhesion_N[i])
                     for i, leg in enumerate(params.legs)]
            self.pad_bushing = GroundBushingCoulomb(
                self.system, self.floor, specs, friction=self.pad_values.friction,
                slip_damping_reenable_speed_m_s=slip_v, dt_s=self.dt_s,
                surface_point_floor_local_m=surface_point, surface_normal_floor_local=self.normal_world,
                normal_force_source=self.pad_normals, adhesion_full_normal_N=ADHESION_FULL_NORMAL_N)
            if crawler_bushings:
                tv = self.track_values
                tspecs = [PadBushingSpec(name=f"track_{side}", body=sup,
                                         sphere_centre_body_local_m=tuple(float(c) for c in (pt - com_body)),
                                         sphere_radius_m=1.0e-3, stiffness_N_m=tv.stiffness_N_m,
                                         damping_input_N_s_m=tv.damping_input_N_s_m)
                          for side, pt in zip(("L", "R"), self.track_points_body_m, strict=True)]
                self.crawler_bushing = GroundBushingCoulomb(
                    self.system, self.floor, tspecs, friction=tv.friction,
                    slip_damping_reenable_speed_m_s=slip_v, dt_s=self.dt_s,
                    surface_point_floor_local_m=surface_point,
                    surface_normal_floor_local=self.normal_world, normal_force_source=self.track_normals)
        if swivel_stiffness_N_m_rad > 0.0:
            self.swivel = SwivelStabiliser(self.system, self.floor, pads, r_plane,
                                           swivel_stiffness_N_m_rad,
                                           [math.degrees(leg.pad.swivel_tilt_range_rad) for leg in params.legs])
        self.last_probe: ProbeState | None = None
        self.actuator_hooks: list[StepHook] = [self._actuator_hook]
        self.load_hooks: list[StepHook] = []
        self.record_hooks: list[RecordHook] = []
        self._rut: dict[str, Any] | None = None
        self.n_patches_last = 0

    # --- L2bModel-compatible members ---------------------------------------------------------

    def floor_normal_world(self) -> NDArray[np.float64]:
        return self.normal_world.copy()

    @property
    def bodies(self) -> tuple[ch.ChBody, ...]:
        return (self.superstructure, *self.legs, *self.pads)

    @property
    def s_ref_m(self) -> NDArray[np.float64]:
        return self.actuator.reference.s_ref_m

    @property
    def u_applied_m_s(self) -> NDArray[np.float64]:
        return self.actuator.reference.u_applied_m_s

    def set_command(self, leg_speed_m_s: ArrayLike) -> None:
        self.actuator.set_command(leg_speed_m_s)

    def set_dt(self, dt_s: float) -> None:
        dt = float(dt_s)
        if not (dt > 0.0 and math.isfinite(dt)):
            raise ValueError(f"dt must be positive: {dt_s!r}")
        self.dt_s = dt
        for b in (self.pad_bushing, self.crawler_bushing):
            if b is not None:
                b.dt_s = dt

    def set_gravity_factor(self, factor: float) -> None:
        """World gravity = ``factor`` x ``gravity_vector(params)`` (settle ramp, 5.34.2 P2)."""
        f = float(factor)
        if not (0.0 <= f <= 1.0):
            raise ValueError(f"gravity factor must be in [0, 1]: {factor!r}")
        self.gravity_factor = f
        set_gravity(self.system, [f * g for g in gravity_vector(self.params)])

    def system_gravity(self) -> tuple[float, float, float]:
        g = self.system.GetGravitationalAcceleration()
        return (float(g.x), float(g.y), float(g.z))

    # --- stepping ---------------------------------------------------------------------------------

    def step(self, *, capture: bool = False) -> ProbeState | None:
        t0 = float(self.system.GetChTime())
        self.actuator.on_step_start(t0)
        self.system.DoStepDynamics(self.dt_s)
        self.actuator.on_step_end()
        return self.after_step(self.dt_s, capture=capture)

    def after_step(self, dt_s: float, *, capture: bool = False) -> ProbeState | None:
        self.forces.refresh()
        probe = read_s9_probe(self) if (capture or self.record_hooks) else None
        self.last_probe = probe
        t = float(self.system.GetChTime())
        if self.pad_bushing is not None:
            self.pad_bushing.after_step(dt_s)
        if self.swivel is not None:
            in_contact = (self.pad_bushing.in_contact if self.pad_bushing is not None
                          else np.array(self.pad_normals(), dtype=float) > 100.0)
            self.swivel.update(in_contact, t)
        if self.crawler_bushing is not None:
            self.crawler_bushing.after_step(dt_s)
        for hook in self.actuator_hooks:
            hook(self, dt_s)
        for hook in self.load_hooks:
            hook(self, dt_s)
        if probe is not None:
            for record in self.record_hooks:
                record(self, probe)
        return probe

    def _actuator_hook(self, model: S9Model, dt_s: float) -> None:
        self.actuator.hook(float(self.system.GetChTime()), dt_s)

    def probe(self) -> ProbeState:
        return read_s9_probe(self)

    def truth(self, probe: ProbeState) -> TruthState:
        import dataclasses

        state = truth_state(probe, s_ref_m=self.s_ref_m, u_applied_m_s=self.u_applied_m_s,
                            k_oil_N_m=[np.inf] * len(LEG_ORDER))
        stroke = (self.actuator.stroke_sensor_true_m(probe.motor_pos_m) if self.actuator.friction_path
                  else self.actuator.stroke_true_m(probe.motor_pos_m, probe.motor_force_N))
        return dataclasses.replace(state, stroke_true_m=stroke)

    def snapshot(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("S9 SCM: snapshots are not implemented (SCM node state)")

    def restore(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("S9 SCM: snapshots are not implemented (SCM node state)")

    # --- S9 records ---------------------------------------------------------------------------------

    def contact_forces_world_N(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """(pads (4, 3), crawler (3,)) total ground force of the step just taken: SCM + anchor
        bushings (the bushing force is the last load evaluation, same convention as L1)."""
        pads = self.forces.pad_force_N.copy()
        crawler = self.forces.sup_force_N.copy()
        if self.pad_bushing is not None:
            pads = pads + self.pad_bushing.tangential_force_world_N()
        if self.crawler_bushing is not None:
            crawler = crawler + self.crawler_bushing.tangential_force_world_N().sum(axis=0)
        return pads, crawler

    def pad_sinkage_m(self) -> NDArray[np.float64]:
        """Geometric sinkage of each pad bottom centre below the SCM plane [m] (+ = below)."""
        out = np.empty(4)
        for i, pad in enumerate(self.pads):
            p = _v(pad.TransformPointLocalToParent(chvec(self.pad_bottom_local_pad_m[i])))
            out[i] = -float((p - self.plane_point_world_m) @ self.normal_world)
        return out

    def pad_outline_world_m(self, i: int) -> NDArray[np.float64]:
        """Bottom polygon of pad ``i`` (hull OBJ bottom face) in world coordinates (k, 3)."""
        pad = self.pads[i]
        return np.array([_v(pad.TransformPointLocalToParent(chvec(p))) for p in self.pad_outline_local_m[i]])

    def pad_node_stats(self) -> list[dict[str, Any]]:
        """Per pad: SCM node state inside the projected pad bottom polygon
        (:func:`node_stats_in_outline` on the pad terrain) plus the geometric sinkage of the pad
        bottom centre; ``node_minus_geometric_m`` = node mean (contact nodes) - geometric (the
        P1-V0 (iii) / P3-S1 quantity). Record rate only."""
        geo = self.pad_sinkage_m()
        out = []
        for i in range(len(self.pads)):
            st = node_stats_in_outline(self.pad_terrain, self.plane_point_world_m, self.plane_rot,
                                       self.pad_grid_m, self.pad_outline_world_m(i))
            st["sinkage_geometric_m"] = float(geo[i])
            sc = st["sinkage_mean_contact_m"]
            st["node_minus_geometric_m"] = None if sc is None else float(sc - geo[i])
            out.append(st)
        return out

    def pad_node_sinkage_m(self) -> NDArray[np.float64]:
        """Mean SCM node sinkage (``GetNodeInfo``) of the nodes inside each projected pad bottom
        polygon [m] (contact nodes; NaN when none). Record rate only (Python per node)."""
        return np.array([np.nan if s["sinkage_mean_contact_m"] is None else s["sinkage_mean_contact_m"]
                         for s in self.pad_node_stats()])

    def num_contact_patches(self) -> int:
        return int(sum(t.GetNumContactPatches() for t in self.terrains))

    def num_ray_hits(self) -> int:
        """SCM ray hits of the last step (all terrains; hit = ray met a shape, not necessarily
        a loaded node)."""
        return int(sum(t.GetNumRayHits() for t in self.terrains))

    def mark_rut_reference(self, *, step_m: float = 0.1) -> dict[str, Any]:
        """Remember the crawler block-bottom points that touch the soil now (node sinkage > 0 at
        their xy): the rut reference of 283.1. Points on the C boxes, ``step_m`` grid."""
        sup = self.superstructure
        pts, heights = [], []
        z_block = float(self.params.ground.crawler_bottom_z_m) + BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
        ys = np.arange(TRACK_Y_RANGE_M[0] + 0.02, TRACK_Y_RANGE_M[1] - 0.02 + 1e-9, step_m)
        xs = np.arange(REAR_RAMP_X_M[0] + 0.02, FRONT_RAMP_X_M[1] - 0.02 + 1e-9, step_m)
        for sy in (1.0, -1.0):
            for x in xs:
                if x > FRONT_RAMP_X_M[0]:
                    zb = z_block + FRONT_RAMP_SLOPE * (x - FRONT_RAMP_X_M[0])
                elif x < REAR_RAMP_X_M[1]:
                    zb = z_block + REAR_RAMP_SLOPE * (REAR_RAMP_X_M[1] - x)
                else:
                    zb = z_block
                for y in ys:
                    local = np.array([x, sy * y, zb]) - self.sup_com_body_m
                    p = sup.TransformPointLocalToParent(chvec(local))
                    if float(self.crawler_terrain.GetNodeInfo(p).sinkage) > 0.0:
                        pts.append(local)
                        heights.append(float(_v(p) @ self.normal_world))
        self._rut = {"points_local_m": np.array(pts).reshape(-1, 3), "height_m": np.array(heights),
                     "t_s": float(self.system.GetChTime())}
        return {"t_s": self._rut["t_s"], "n_points": len(pts), "step_m": step_m}

    def rut_clearance_m(self) -> float | None:
        """Minimum rise of the rut-reference points above their settle height [m] (283.1
        'clearance above the rut'; includes the soil's elastic rebound as clearance)."""
        if self._rut is None or len(self._rut["height_m"]) == 0:
            return None
        sup = self.superstructure
        h = np.array([float(_v(sup.TransformPointLocalToParent(chvec(p))) @ self.normal_world)
                      for p in self._rut["points_local_m"]])
        return float(np.min(h - self._rut["height_m"]))

    def s9_record(self) -> dict[str, Any]:
        """One record row of the S9 keys (control spec 284; SI)."""
        n = self.normal_world
        pads, crawler = self.contact_forces_world_N()
        row = {
            "t_s": float(self.system.GetChTime()),
            "scm_crawler_force_world_N": self.forces.sup_force_N.tolist(),
            "scm_crawler_normal_N": float(self.forces.sup_force_N @ n),
            "scm_track_normal_raw_N": self.track_normals.last_raw_N.tolist(),
            "scm_pad_normal_N": (self.forces.pad_force_N @ n).tolist(),
            "pad_total_force_world_N": pads.tolist(),
            "crawler_total_force_world_N": crawler.tolist(),
            "scm_contact_patches": self.num_contact_patches(),
            "pad_sinkage_geometric_m": self.pad_sinkage_m().tolist(),
            "rut_clearance_m": self.rut_clearance_m(),
            "pad_tilt_deg": None if self.swivel is None else self.swivel.tilt_deg().tolist(),
            # P3 keys (dynamics 5.34.6): crawler rocking (truth rate), running pad tilt maximum
            "pad_tilt_max_deg": None if self.swivel is None else self.swivel.tilt_max_deg.tolist(),
            "body_omega_world_rad_s": _v(self.superstructure.GetAngVelParent()).tolist(),
            "scm_ray_hits": self.num_ray_hits(),
            "gravity_factor": self.gravity_factor,
        }
        if self.pad_bushing is not None:
            row["pad_slip_total_m"] = self.pad_bushing.slip_total_m.tolist()
            row["pad_in_contact"] = self.pad_bushing.in_contact.tolist()
            row["pad_tangential_N"] = self.pad_bushing.tangential_force_world_N().tolist()
        if self.crawler_bushing is not None:
            tn = np.asarray(self.track_normals.last_raw_N)
            ft = self.crawler_bushing.tangential_force_world_N()
            lim = self.crawler_bushing.tangential_limit_N(tn)
            row["track_utilisation"] = [float(np.linalg.norm(ft[k]) / lim[k]) if lim[k] > 0 else None
                                        for k in range(2)]
        return row

    def meta(self) -> dict[str, Any]:
        meta = self.bundle.meta()
        meta.update(
            model="S9 SCM four legs (L2b force law, concrete dropped; SMC system, no rigid contact)",
            auger_level=self.params.level.value,
            params_sha256=self.params.sha256,
            scm_run_sha256=scm_run_sha256(self.params),
            pad_variant=self.pad_variant_meta,
            scm=self.terrain_meta,
            extensions_m=list(self.extensions_m),
            start_s_ref_m=list(self.start_s_ref_m),
            start_forces_N=np.asarray(self.start_forces_N).tolist(),
            k_ax0_N_m=self.k_ax0_N_m.tolist(),
            initial_pose={"origin_m": list(self.pose.origin_m), "quat_wxyz": list(self.pose.quat_wxyz)},
            crawler_shape={"kind": "C envelope boxes, 3 per track (dynamics_model.md 3.11.2)",
                           "boxes": self.crawler_boxes},
            ray_shape={"mode": self.ray_shape,
                       "basis": ("static triangle soups (cbtBvhTriangleMeshShape, exact ray-triangle) "
                                 "for the crawler boxes and the pad hulls (P1-V0, 5.34.10)")
                       if self.ray_shape == "mesh" else
                       "ChCollisionShapeBox / ConvexHull (sub-simplex convex-cast ray test, up to 10 mm low)"},
            terrain_layout={"dual": self.dual_terrain, "pad_grid_m": self.pad_grid_m,
                            "crawler_grid_m": self.crawler_grid_m},
            gravity_factor_now=self.gravity_factor,
            lateral_leg="PRISMATIC guide (rod laterally rigid); k_lat in the anchor bushing series",
            pad_anchor=None if self.pad_bushing is None else {
                **self.pad_values.meta(), "adhesion_full_normal_N": ADHESION_FULL_NORMAL_N,
                "force_point": self.pad_bushing.force_point, "R15": {
                    "touch_N": self.pad_bushing.touch_threshold_N, "lift_s": self.pad_bushing.lift_time_s}},
            crawler_anchor=None if self.crawler_bushing is None else {
                **self.track_values.meta(), "points_body_m": [p.tolist() for p in self.track_points_body_m]},
            swivel_stabiliser=None if self.swivel is None else self.swivel.meta(),
            actuator=self.actuator.meta(),
            input_lag_steps=1,
            num_threads_chrono=self.num_threads,
            c2_soil=None,
        )
        return meta


def read_s9_probe(model: S9Model) -> ProbeState:
    """State copy in the L1 :class:`ProbeState` layout; contact forces = SCM + anchor bushing."""
    sup = model.superstructure
    origin_local = model.origin_in_cog_frame_ch
    origin = sup.TransformPointLocalToParent(origin_local)
    vel = sup.PointSpeedLocalToParent(origin_local)
    q = sup.GetRot()
    motor_pos = np.array([m.GetMotorPos() for m in model.motors], dtype=float)
    centres = np.array([_v(p.TransformPointLocalToParent(chvec(c)))
                        for p, c in zip(model.pads, model.ball_local_pad_m, strict=True)])
    direction = extension_direction(model.params)
    offsets = np.empty((4, 3))
    for i, rod in enumerate(model.legs):
        local = _v(sup.TransformPointParentToLocal(rod.GetPos())) + model.sup_com_body_m
        offsets[i] = local - (model.rod_com_retracted_m[i] + motor_pos[i] * direction)
    pads, crawler = model.contact_forces_world_N()
    pb = model.pad_bushing
    in_contact = (pb.in_contact if pb is not None
                  else (model.forces.pad_force_N @ model.normal_world) > 0.0)
    anchors = pb.anchors_world_m() if pb is not None else np.full((4, 3), np.nan)
    bforce = pads
    return ProbeState(
        t_s=float(model.system.GetChTime()), body_pos_m=_v(origin),
        body_quat_wxyz=np.array([q.e0, q.e1, q.e2, q.e3], dtype=float), body_vel_m_s=_v(vel),
        body_omega_rad_s=_v(sup.GetAngVelParent()), cog_pos_m=_v(sup.GetPos()),
        motor_pos_m=motor_pos, motor_force_N=model.actuator.acting_force_N,
        pad_contact_world_N=pads, pad_sphere_centre_world_m=centres,
        pad_sphere_radius_m=np.array(model.sphere_radii_m, dtype=float),
        leg_offset_in_body_m=offsets, crawler_contact_world_N=crawler,
        floor_normal_world=model.normal_world.copy(),
        floor_point_world_m=np.asarray(model.plane_point_world_m, dtype=float).copy(),
        bushing_in_contact=np.asarray(in_contact, dtype=bool), bushing_anchor_world_m=anchors,
        bushing_force_world_N=bforce, n_contacts=int(model.system.GetNumContacts()))


__all__ = [
    "ACTIVE_DOMAIN_HEIGHT_M", "DEFAULT_RAY_SHAPE", "GRAVITY_RAMP_SHAPES", "GRID_M",
    "KAPPA_HORIZONTAL", "MACHINE_GRAVITY_HOLD_S", "MACHINE_GRAVITY_RAMP_S", "RAY_SHAPES",
    "SCM_SHEAR_MODES", "SINGLE_PAD_LOAD_RAMP_S", "STIFFNESS_MODES", "SWIVEL_K_N_M_RAD",
    "PadNormals", "PadTangentialValues", "S9Model", "ScmForceReader", "SoilParameterError",
    "SoilSet", "SwivelStabiliser", "TrackNormals", "TrackTangentialValues", "add_active_domain",
    "add_pad_ray_mesh", "add_ray_mesh", "box_triangles", "check_soil", "convex_hull_2d",
    "crawler_box_specs", "gravity_ramp_factor", "initialize_terrain", "inside_convex_polygon",
    "load_soil_set", "make_terrain", "node_stats_in_outline", "pad_bottom_outline_local_m",
    "pad_tangential_values", "plane_frame", "read_s9_probe", "scm_call_values",
    "split_body_props", "track_tangential_values",
]
