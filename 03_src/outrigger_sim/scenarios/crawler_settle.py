"""Crawler contact layout D, analytic settle pose on the crawler and its linear modes (S2b).

``00_docs/03_chrono/chrono_build_plan.md`` R13, section 2 rule 2, S2b "크롤러 정착";
``dynamics_model.md`` 3.8 (layout D), 4.5 item 1. Engine independent (numpy only).

Layout (``contact.crawler.sphere_layout``, scheme ``rollers_plus_gapped_end_shoes``): per
track (y = +-``track_centre_y_m``) one sphere per roller station (``roller_x_m``, sphere
bottom = crawler bottom plane) and one per end shoe (``end_shoe_x_m``, sphere bottom =
plane + ``end_shoe_gap_m``, i.e. unilateral: it carries load only once the gap is closed).
Order: left rollers, left end shoes, right rollers, right end shoes (the order of
``04_scripts/00_cad/crawler_contact.py``; the reference ``crawler_sphere_forces_N`` list
uses another order, see :data:`REFERENCE_ORDER`).

Analytic settle (:func:`crawler_static_pose`): the whole machine with the legs at
``extensions_m`` (0 = fully retracted, pads about 0.34 m above the floor) is one rigid body
on 24 vertical one-sided springs ``F_i = kn max(delta_i, 0)``, ``delta_i = r - (z_ci -
z_floor)`` (exact sphere-plane overlap of the rotated body, the SMC Hooke normal force of
the Chrono model). Unknowns: origin height ``z0``, roll, pitch (ZYX, yaw 0); horizontal
position and yaw are free (zero stiffness, R8 ``kt = mu = 0``) and stay at 0. Equations:
sum of the vertical forces = total weight, moments about the composite centre of mass = 0.
Newton iteration with a numerical Jacobian; the active set is re-evaluated every iteration.
``kn`` defaults to the float32 value Chrono stores (V0 rule).

Linear modes (:func:`crawler_linear_modes`): heave / roll / pitch about the composite centre
of mass with the active springs and the geometric (P-delta) stiffness of gravity, ``-sum F_i
h_i`` on roll and pitch (``h_i`` = COG height above contact ``i``). The roll-pitch inertia is
condensed over the free yaw (``I_rr - I_ry I_yy^-1 I_yr``; the yaw has inertia coupling but no
stiffness); the plain 3x3
sub-matrix (as in ``crawler_on_floor_modes``, note "omitted") is reported too. Damping: SMC
Hooke ``c_i = gn m_eff`` with ``m_eff`` = superstructure body mass x floor mass / sum (the
crawler spheres sit on the superstructure body, the legs are separate Chrono bodies).

Units SI; angles in rad unless named ``*_deg``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix
from outrigger_sim.geometry import leg_com_body_m
from outrigger_sim.params import Params

CRAWLER_LAYOUT_KEY = "contact.crawler.sphere_layout"
CRAWLER_SCHEME = "rollers_plus_gapped_end_shoes"
ROLLER = "roller"
END_SHOE = "end_shoe"

NEWTON_TOL_N = 1.0e-6
"""Force / moment residual [N, N m] at which the static Newton iteration stops."""
NEWTON_MAX_ITER = 50
FD_STEP = (1.0e-7, 1.0e-8, 1.0e-8)
"""Finite-difference steps for (z0 [m], roll [rad], pitch [rad])."""


# --- layout --------------------------------------------------------------------------------


@dataclass(frozen=True)
class CrawlerSphereLayout:
    """Crawler contact spheres of ``contact.crawler.sphere_layout`` (layout D)."""

    scheme: str
    track_centre_y_m: float
    sphere_radius_m: float
    xy_m: NDArray[np.float64]
    """(n, 2) contact point x, y (body coordinates)."""
    gap_m: NDArray[np.float64]
    """(n,) sphere bottom above the crawler bottom plane (0 for rollers)."""
    kind: tuple[str, ...]

    @property
    def n_points(self) -> int:
        return int(self.gap_m.shape[0])

    @property
    def is_roller(self) -> NDArray[np.bool_]:
        return np.array([k == ROLLER for k in self.kind])

    @property
    def x_extent_m(self) -> tuple[float, float]:
        return float(self.xy_m[:, 0].min()), float(self.xy_m[:, 0].max())

    def centres_body_m(self, crawler_bottom_z_m: float) -> NDArray[np.float64]:
        """(n, 3) sphere centres in body coordinates (bottom + gap + radius)."""
        z = crawler_bottom_z_m + self.gap_m + self.sphere_radius_m
        return np.column_stack([self.xy_m, z])

    def labels(self) -> list[str]:
        """``L-roller-0`` ... ``R-end_shoe-5`` in layout order."""
        out = []
        counters: dict[tuple[str, str], int] = {}
        for (_, y), kind in zip(self.xy_m, self.kind, strict=True):
            side = "L" if y > 0.0 else "R"
            k = counters.get((side, kind), 0)
            counters[(side, kind)] = k + 1
            out.append(f"{side}-{kind}-{k}")
        return out

    def reference_order(self) -> NDArray[np.int64]:
        """Indices that reorder layout arrays into the reference list order
        (:data:`REFERENCE_ORDER`): left rollers, right rollers, left end shoes, right end
        shoes."""
        roller = self.is_roller
        left = self.xy_m[:, 1] > 0.0
        idx = np.arange(self.n_points)
        return np.concatenate(
            [idx[roller & left], idx[roller & ~left], idx[~roller & left], idx[~roller & ~left]]
        )


REFERENCE_ORDER = "left rollers, right rollers, left end shoes, right end shoes"
"""Order of ``reference.json / lift_V4_compliant_crawler / layouts / D ... / settled_on_crawler
(legs at 0) / crawler_sphere_forces_N`` (checked 2026-10-20: 12 roller values then the end
shoes in ``end_shoe_x_m`` order, left before right)."""


def crawler_layout(params: Params) -> CrawlerSphereLayout:
    """Read ``contact.crawler.sphere_layout`` (only the layout-D scheme is supported)."""
    node = params.get(CRAWLER_LAYOUT_KEY)
    scheme = str(node["scheme"])
    if scheme != CRAWLER_SCHEME:
        raise ValueError(f"{CRAWLER_LAYOUT_KEY}.scheme = {scheme!r}; expected {CRAWLER_SCHEME!r}")
    yc = float(node["track_centre_y_m"])
    rollers = [float(x) for x in node["roller_x_m"]]
    shoes = [float(x) for x in node["end_shoe_x_m"]]
    gaps = [float(g) for g in node["end_shoe_gap_m"]]
    radius = float(node["sphere_radius_m"])
    if len(shoes) != len(gaps) or not rollers or yc <= 0.0 or radius <= 0.0:
        raise ValueError(f"{CRAWLER_LAYOUT_KEY}: inconsistent layout")
    if min(gaps) < 0.0:
        raise ValueError(f"{CRAWLER_LAYOUT_KEY}.end_shoe_gap_m must be >= 0")
    xy: list[tuple[float, float]] = []
    gap: list[float] = []
    kind: list[str] = []
    for y in (yc, -yc):
        for x in rollers:
            xy.append((x, y))
            gap.append(0.0)
            kind.append(ROLLER)
        for x, g in zip(shoes, gaps, strict=True):
            xy.append((x, y))
            gap.append(g)
            kind.append(END_SHOE)
    return CrawlerSphereLayout(
        scheme, yc, radius, np.array(xy, dtype=float), np.array(gap, dtype=float), tuple(kind)
    )


# --- composite rigid machine ---------------------------------------------------------------


@dataclass(frozen=True)
class CompositeMass:
    """Superstructure + four leg moving parts as one rigid body (body axes)."""

    mass_kg: float
    com_body_m: NDArray[np.float64]
    inertia_com_kg_m2: NDArray[np.float64]
    """3x3 about the composite COG, body axes (off-diagonal = -integral(x y dm))."""
    superstructure_mass_kg: float


def composite_mass(params: Params, extensions_m: Sequence[float]) -> CompositeMass:
    """Mass, COG and inertia of the machine with the legs locked at ``extensions_m``."""
    sup = params.superstructure.mass_properties
    parts = [(sup.mass_kg, np.asarray(sup.com_m, float), np.asarray(sup.inertia_kg_m2, float))]
    for i, leg in enumerate(params.legs):
        mp = leg.moving_part
        parts.append(
            (
                mp.mass_kg,
                leg_com_body_m(params, i, float(extensions_m[i])),
                np.asarray(mp.inertia_kg_m2, float),
            )
        )
    m = sum(p[0] for p in parts)
    c = sum(p[0] * p[1] for p in parts) / m
    inertia = np.zeros((3, 3))
    for mi, ci, ii in parts:
        d = ci - c
        inertia += ii + mi * (float(d @ d) * np.eye(3) - np.outer(d, d))
    return CompositeMass(float(m), c, inertia, float(sup.mass_kg))


# --- static pose -----------------------------------------------------------------------------


@dataclass(frozen=True)
class CrawlerStartPose:
    """Analytic static pose on the crawler (legs off the ground)."""

    origin_m: tuple[float, float, float]
    quat_wxyz: tuple[float, float, float, float]
    roll_deg: float
    pitch_deg: float
    u_z_m: float
    """Origin height relative to the zero pose (crawler bottom plane on the floor, level)."""
    sphere_force_N: NDArray[np.float64]
    """(n,) normal force per sphere, layout order."""
    sphere_penetration_m: NDArray[np.float64]
    """(n,) signed overlap ``r - (z_c - z_floor)`` (negative = gap)."""
    active: NDArray[np.bool_]
    kn_per_sphere_N_m: float
    weight_N: float
    residual: NDArray[np.float64]
    """Final (force - weight [N], moment x, moment y [N m])."""
    iterations: int
    extensions_m: tuple[float, ...]


def _sphere_state(
    q: NDArray[np.float64],
    centres_body: NDArray[np.float64],
    radius: float,
    floor_z: float,
    kn: float,
    com_body: NDArray[np.float64],
    weight: float,
    linear: bool = False,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """(residual (3,), forces (n,), overlap (n,)) for q = (z0, roll, pitch).

    linear: small-angle model with the moment arms of the zero pose (no P-delta), the
    convention of the linear reference solution.
    """
    z0, roll, pitch = (float(v) for v in q)
    origin = np.array([0.0, 0.0, z0])
    if linear:
        world = centres_body.copy()
        world[:, 2] += z0 + roll * centres_body[:, 1] - pitch * centres_body[:, 0]
        g = com_body.copy()
    else:
        rot = quat_to_matrix(quat_from_euler_zyx(0.0, pitch, roll))
        world = origin + centres_body @ rot.T
        g = origin + rot @ com_body
    overlap = radius - (world[:, 2] - floor_z)
    force = kn * np.maximum(overlap, 0.0)
    mx = float(np.sum(force * (world[:, 1] - g[1])))
    my = float(-np.sum(force * (world[:, 0] - g[0])))
    return np.array([float(force.sum()) - weight, mx, my]), force, overlap


def crawler_static_pose(
    params: Params,
    extensions_m: Sequence[float] | None = None,
    *,
    kn_N_m: float | None = None,
    float32_kn: bool = True,
    floor_z_m: float | None = None,
    linear: bool = False,
) -> CrawlerStartPose:
    """Static pose of the rigid machine on the crawler spheres (module docstring).

    Args:
        extensions_m: Leg extensions (default 0, fully retracted). The legs must not touch.
        kn_N_m: Sphere stiffness; default ``contact.crawler.kn_per_sphere_N_m``.
        float32_kn: Round ``kn`` to float32 as Chrono stores it.
        floor_z_m: Floor height; default ``ground.crawler_bottom_z_m``.
        linear: Small-angle model without P-delta (reproduces the linear reference
            ``settled_on_crawler (legs at 0)``); default exact geometry (what Chrono holds).

    Raises:
        RuntimeError: Newton did not converge.
    """
    ext = tuple(0.0 for _ in params.legs) if extensions_m is None else tuple(extensions_m)
    layout = crawler_layout(params)
    floor = params.ground.crawler_bottom_z_m if floor_z_m is None else float(floor_z_m)
    kn = float(params.get("contact.crawler.kn_per_sphere_N_m")) if kn_N_m is None else kn_N_m
    if float32_kn:
        kn = float(np.float32(kn))
    comp = composite_mass(params, ext)
    weight = comp.mass_kg * params.meta.gravity_m_s2
    centres = layout.centres_body_m(params.ground.crawler_bottom_z_m)
    r = layout.sphere_radius_m
    q = np.array([-weight / (kn * int(layout.is_roller.sum())), 0.0, 0.0])
    h = np.asarray(FD_STEP)
    iterations = 0
    for iterations in range(1, NEWTON_MAX_ITER + 1):  # noqa: B007 - kept for the result
        res, _, _ = _sphere_state(q, centres, r, floor, kn, comp.com_body_m, weight, linear)
        if np.all(np.abs(res) < NEWTON_TOL_N):
            break
        jac = np.empty((3, 3))
        for j in range(3):
            dq = np.zeros(3)
            dq[j] = h[j]
            rp, _, _ = _sphere_state(q + dq, centres, r, floor, kn, comp.com_body_m, weight, linear)
            rm, _, _ = _sphere_state(q - dq, centres, r, floor, kn, comp.com_body_m, weight, linear)
            jac[:, j] = (rp - rm) / (2.0 * h[j])
        q = q - np.linalg.solve(jac, res)
    else:
        raise RuntimeError(f"crawler static pose did not converge: residual {res}")
    res, force, overlap = _sphere_state(q, centres, r, floor, kn, comp.com_body_m, weight, linear)
    quat = quat_from_euler_zyx(0.0, float(q[2]), float(q[1]))
    return CrawlerStartPose(
        origin_m=(0.0, 0.0, float(q[0])),
        quat_wxyz=tuple(float(v) for v in quat),  # type: ignore[arg-type]
        roll_deg=math.degrees(float(q[1])),
        pitch_deg=math.degrees(float(q[2])),
        u_z_m=float(q[0]),
        sphere_force_N=force,
        sphere_penetration_m=overlap,
        active=overlap > 0.0,
        kn_per_sphere_N_m=kn,
        weight_N=weight,
        residual=res,
        iterations=iterations,
        extensions_m=ext,
    )


# --- linear modes ----------------------------------------------------------------------------


@dataclass(frozen=True)
class CrawlerModes:
    """Heave / roll / pitch modes on the active crawler springs (sorted by frequency)."""

    f_undamped_Hz: NDArray[np.float64]
    f_damped_Hz: NDArray[np.float64]
    zeta: NDArray[np.float64]
    names: tuple[str, ...]
    """Dominant coordinate of each mode (``heave``, ``roll``, ``pitch``)."""
    phi: NDArray[np.float64]
    """(3, 3) mass-normalised undamped mode shapes, columns; coordinates (z_G [m], roll,
    pitch [rad]) about the composite COG."""
    mass_matrix: NDArray[np.float64]
    stiffness_matrix: NDArray[np.float64]
    """Contact springs minus the geometric (P-delta) term ``sum F_i h_i`` on roll and pitch."""
    damping_matrix: NDArray[np.float64]
    f_undamped_plain_Hz: NDArray[np.float64]
    """Same with the plain 3x3 inertia sub-matrix (yaw coupling ignored)."""
    com_body_m: NDArray[np.float64]
    n_active: int


def crawler_linear_modes(params: Params, pose: CrawlerStartPose) -> CrawlerModes:
    """Linear modes about the static pose (module docstring)."""
    layout = crawler_layout(params)
    comp = composite_mass(params, pose.extensions_m)
    rot = quat_to_matrix(np.asarray(pose.quat_wxyz))
    origin = np.asarray(pose.origin_m)
    centres = origin + layout.centres_body_m(params.ground.crawler_bottom_z_m) @ rot.T
    g = origin + rot @ comp.com_body_m
    active = pose.active
    kn = pose.kn_per_sphere_N_m
    floor_mass = float(params.contact.rigid_floor.ground_body_mass_kg)
    m_eff = comp.superstructure_mass_kg * floor_mass / (comp.superstructure_mass_kg + floor_mass)
    gn = float(np.float32(params.get("contact.crawler.gn_per_sphere_1_s")))
    c_sphere = gn * m_eff
    # small-motion vertical displacement at sphere i: dz_G + roll (y_i - y_G) - pitch (x_i - x_G)
    b = np.column_stack([np.ones(layout.n_points), centres[:, 1] - g[1], -(centres[:, 0] - g[0])])[
        active
    ]
    stiffness = kn * b.T @ b
    # geometric (P-delta) stiffness of the vertical contact forces acting below the COG: a
    # rotation shifts each contact point horizontally by angle x (z_i - z_G) -> -sum F_i h_i
    heights = g[2] - centres[active, 2]
    geometric = float(np.sum(pose.sphere_force_N[active] * heights))
    stiffness[1, 1] -= geometric
    stiffness[2, 2] -= geometric
    damping = c_sphere * b.T @ b
    inertia_world = rot @ comp.inertia_com_kg_m2 @ rot.T
    i_rr = inertia_world[:2, :2]
    i_ry = inertia_world[:2, 2:3]
    condensed = i_rr - i_ry @ i_ry.T / inertia_world[2, 2]
    mass = np.zeros((3, 3))
    mass[0, 0] = comp.mass_kg
    mass[1:, 1:] = condensed
    plain = mass.copy()
    plain[1:, 1:] = i_rr

    def undamped(mm: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        lc = np.linalg.cholesky(mm)
        li = np.linalg.inv(lc)
        w2, v = np.linalg.eigh(li @ stiffness @ li.T)
        order = np.argsort(w2)
        return np.sqrt(w2[order]), li.T @ v[:, order]

    omega, phi = undamped(mass)
    omega_plain, _ = undamped(plain)
    # damped: state-space eigenvalues, matched to the undamped modes by frequency order
    a = np.block(
        [
            [np.zeros((3, 3)), np.eye(3)],
            [-np.linalg.solve(mass, stiffness), -np.linalg.solve(mass, damping)],
        ]
    )
    lam = np.linalg.eigvals(a)
    lam = lam[lam.imag > 0.0]
    lam = lam[np.argsort(np.abs(lam))]
    f_d = lam.imag / (2.0 * math.pi)
    zeta = -lam.real / np.abs(lam)
    names = tuple(
        ("heave", "roll", "pitch")[int(np.argmax(np.abs(phi[:, k]) * [1.0, 2.0, 2.0]))]
        for k in range(3)
    )
    return CrawlerModes(
        f_undamped_Hz=omega / (2.0 * math.pi),
        f_damped_Hz=f_d,
        zeta=zeta,
        names=names,
        phi=phi,
        mass_matrix=mass,
        stiffness_matrix=stiffness,
        damping_matrix=damping,
        f_undamped_plain_Hz=omega_plain / (2.0 * math.pi),
        com_body_m=comp.com_body_m,
        n_active=int(active.sum()),
    )


def pad_touch_extension_m(
    params: Params, leg_index: int, pose_origin_m: Sequence[float], quat_wxyz: Sequence[float]
) -> float:
    """Extension at which the pad sphere of ``leg_index`` touches the level floor for a body
    held at the given pose (the sphere centre moves linearly with the extension)."""
    from outrigger_sim.geometry import pad_sphere_centre_body_m

    rot = quat_to_matrix(np.asarray(quat_wxyz, dtype=float))
    origin = np.asarray(pose_origin_m, dtype=float)
    radius = params.legs[leg_index].pad.swivel_center_above_pad_bottom_m
    floor = params.ground.crawler_bottom_z_m
    z0 = (origin + rot @ pad_sphere_centre_body_m(params, leg_index, 0.0))[2]
    z1 = (origin + rot @ pad_sphere_centre_body_m(params, leg_index, 1.0))[2]
    return float((floor + radius - z0) / (z1 - z0))
