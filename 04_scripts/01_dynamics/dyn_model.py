"""Reference (hand-check) dynamics model of the REXOME33 outrigger levelling system.

Reads the single source of truth ``02_params/rexome33.yaml`` and provides:

* geometry of the four legs (pad bottom centres, attachment points),
* stiffness assumptions (hydraulic oil column, rod, frame, concrete pad contact,
  lateral leg bending) - every value that is NOT in the YAML is an ASSUMPTION
  and is collected in ``ASSUMPTIONS``,
* the statically indeterminate 4-spring load distribution (with lift-off),
* linear kinematics (leg extension -> heave/roll/pitch),
* linearised 6-DoF (rigid legs) and 10-DoF (rigid body + 4 rod axial DoF)
  stiffness / mass / damping matrices and modal analysis.

Conventions (CLAUDE.md):
  body frame x forward, y left, z up (right-handed), SI units.
  roll phi about +x, pitch theta about +y, yaw psi about +z (small angles).
  With the body level the body frame is aligned with the world frame.
  Gravity g = -9.80665 z_hat m/s^2 (YAML meta.gravity_m_s2).
  Leg extension e >= 0 pushes the pad down (-z).
  Leg order FL, FR, RL, RR (index 0..3).
  Small-motion generalised coordinates (6-DoF):
     q = [ux, uy, uz, phi, theta, psi]  (translation of the reference CoM, rotation about it)
  Vertical displacement of a body point at offset d from the CoM:
     dz = uz + phi*d_y - theta*d_x
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = PROJECT_ROOT / "02_params" / "rexome33.yaml"
LEG_NAMES = ("FL", "FR", "RL", "RR")
LEVELS = ("top", "middle", "bottom")

# ---------------------------------------------------------------------------
# Assumptions (not in the YAML). Every number here must be reported as an assumption.
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    # hydraulic cylinder (plunger-type: bore D115, rod D110 per 00_docs/00_cad/cad_review.md 3.1)
    "bore_diameter_m": 0.115,          # CAD (00_docs/00_cad/cad_review.md 3.1), not an assumption but not in YAML
    "rod_diameter_m": 0.110,           # CAD (00_docs/00_cad/cad_review.md 3.1)
    "barrel_outer_diameter_m": 0.160,  # CAD (00_docs/00_cad/cad_review.md 3.1)
    "oil_bulk_modulus_eff_Pa": 1.0e9,  # ASSUMPTION: mineral oil ~1.5 GPa reduced for air/hose compliance
    "oil_bulk_modulus_range_Pa": [0.69e9, 1.6e9],  # sensitivity range (CLAUDE.md, user decision)
    "oil_dead_length_m": 0.05,         # ASSUMPTION: port/pipe volume expressed as extra column length
    "steel_E_Pa": 2.1e11,
    "frame_bracket_stiffness_N_m": 1.0e9,  # ASSUMPTION: outrigger box/bracket local vertical stiffness
    # concrete floor (slab on grade), Westergaard interior load
    "concrete_E_Pa": 30e9,             # ASSUMPTION
    "concrete_nu": 0.15,               # ASSUMPTION
    "slab_thickness_m": 0.20,          # ASSUMPTION
    "subgrade_modulus_N_m3": 80e6,     # ASSUMPTION (modulus of subgrade reaction k_s)
    # operating point
    "crawler_clearance_m": 0.05,       # ASSUMPTION: crawler lifted 50 mm above the floor in the levelled state
    # damping (user decision 2026-10-20, 00_docs/01_dynamics/damping_survey.md; literature-derived, not measured)
    "modal_damping_ratio_body": 0.03,  # ASSUMPTION: leg axial zeta, locked cylinder (L1, L2b at rest), set on heave (~7.4 Hz)
    "leg_damping_ratio_moving": 0.10,  # ASSUMPTION: leg axial zeta while the valve drives the leg (L2 / L2b oil damper)
    "leg_damping_ratio_range": [0.01, 0.10],         # sensitivity range, locked
    "leg_damping_ratio_moving_range": [0.05, 0.20],  # sensitivity range, moving
    "structure_damping_ratio": 0.015,  # ASSUMPTION: structure / mast modes, recorded only (rigid-body model now)
    # swivel pad (user decision 2026-10-19: pad joined to the rod by a spherical joint)
    "swivel_ball_height_above_pad_bottom_m": 0.06,  # ASSUMPTION: ball centre height (CAD has no swivel)
    "swivel_tilt_range_deg": 10.0,                  # ASSUMPTION: free tilt of the pad about the ball
    # contact criterion (user decision 2026-10-19): F_min = 10 % of the mean leg load
    "F_min_fraction_of_mean_leg_load": 0.10,
    "F_min_basis": "cylinder force (pressure x bore area) = superstructure weight share; contact force = cylinder force + rod weight",
}

G = None  # filled from YAML


def load_params(path: Path = YAML_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class Geometry:
    """Leg geometry in the body frame (retracted state), from the YAML."""

    pad_xy: np.ndarray          # (4,2) pad bottom centre x,y [m]
    pad_z_retracted: np.ndarray  # (4,) pad bottom z, retracted [m]
    attach_z: np.ndarray        # (4,) attachment point z (convention) [m]
    barrel_bottom_z: np.ndarray  # (4,) barrel bottom z (fixed to the superstructure) [m]
    pad_polygons: list          # list of (8,2) arrays relative to pad centre [m]
    rod_mass: np.ndarray        # (4,) [kg]
    rod_com_retracted: np.ndarray  # (4,3) [m]
    rod_inertia: list           # list of 3x3 about rod CoM [kg m^2]
    stroke: float
    v_max: float
    g: float
    crawler_bottom_z: float
    crawler_xy_box: tuple       # ((xmin,xmax),(ymin,ymax)) from parts_classified.csv bbox (see docs)

    @property
    def touch_extension(self) -> np.ndarray:
        """Extension at which each pad touches a floor at the crawler-bottom level [m]."""
        return self.pad_z_retracted - self.crawler_bottom_z


@dataclass
class Body:
    level: str
    mass: float
    com: np.ndarray
    inertia: np.ndarray  # about com, body axes


def geometry_from_params(p: dict) -> Geometry:
    legs = p["legs"]
    pad_xy = np.array([legs[n]["pad_bottom_center_retracted_m"][:2] for n in LEG_NAMES])
    pad_z = np.array([legs[n]["pad_bottom_center_retracted_m"][2] for n in LEG_NAMES])
    attach_z = np.array([legs[n]["attachment_point_m"][2] for n in LEG_NAMES])
    barrel_bot = np.array([legs[n]["barrel_z_range_m"][0] for n in LEG_NAMES])
    polys = [np.array(legs[n]["pad"]["polygon_xy_m"]) for n in LEG_NAMES]
    rod_mass = np.array([legs[n]["moving_part"]["mass_kg"] for n in LEG_NAMES])
    rod_com = np.array([legs[n]["moving_part"]["com_retracted_m"] for n in LEG_NAMES])
    rod_I = [np.array(legs[n]["moving_part"]["inertia_kg_m2"]) for n in LEG_NAMES]
    # crawler bounding box: parts_classified.csv row 'COMPOUND' (REX33-REX33 - 5J286105) bbox,
    # CAD (X,Z) -> body (y,x): x in [-1.840, 1.844], y in [-1.366, 1.366] m
    crawler_box = ((-1.840, 1.844), (-1.366, 1.366))
    return Geometry(
        pad_xy=pad_xy,
        pad_z_retracted=pad_z,
        attach_z=attach_z,
        barrel_bottom_z=barrel_bot,
        pad_polygons=polys,
        rod_mass=rod_mass,
        rod_com_retracted=rod_com,
        rod_inertia=rod_I,
        stroke=float(p["actuator"]["stroke_m"]),
        v_max=float(p["actuator"]["max_speed_m_s"]),
        g=float(p["meta"]["gravity_m_s2"]),
        crawler_bottom_z=float(p["ground"]["crawler_bottom_z_m"]),
        crawler_xy_box=crawler_box,
    )


def body_from_params(p: dict, level: str) -> Body:
    L = p["superstructure"]["auger_levels"][level]
    return Body(level, float(L["mass_kg"]), np.array(L["com_m"], float), np.array(L["inertia_kg_m2"], float))


def combine_bodies(parts: list[tuple[float, np.ndarray, np.ndarray]]):
    """Combine rigid parts (mass, com, inertia about own com, body axes) -> (m, com, I about com)."""
    m = sum(pm for pm, _, _ in parts)
    c = sum(pm * pc for pm, pc, _ in parts) / m
    I = np.zeros((3, 3))
    for pm, pc, pI in parts:
        d = pc - c
        I += pI + pm * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return m, c, I


def body_with_rods(p: dict, geo: Geometry, level: str, ext: np.ndarray) -> Body:
    """Superstructure + 4 rod/pad moving parts at extensions ext (rods rigidly fixed)."""
    b = body_from_params(p, level)
    parts = [(b.mass, b.com, b.inertia)]
    for i in range(4):
        c = geo.rod_com_retracted[i] - np.array([0.0, 0.0, ext[i]])
        parts.append((geo.rod_mass[i], c, geo.rod_inertia[i]))
    m, c, I = combine_bodies(parts)
    return Body(level + "+rods", m, c, I)


# ---------------------------------------------------------------------------
# Stiffness estimates
# ---------------------------------------------------------------------------
def piston_area() -> float:
    return math.pi / 4 * ASSUMPTIONS["bore_diameter_m"] ** 2


def k_oil(ext, beta=None, dead=None):
    """Locked oil column stiffness of the cap-side chamber [N/m] (plunger: full bore area)."""
    beta = ASSUMPTIONS["oil_bulk_modulus_eff_Pa"] if beta is None else beta
    dead = ASSUMPTIONS["oil_dead_length_m"] if dead is None else dead
    return beta * piston_area() / (dead + np.asarray(ext, float))


def k_rod(rod_length: float = 1.05) -> float:
    """Axial steel rod stiffness, piston top (z 0.35) to pad bottom (z -0.70): ~1.05 m [N/m]."""
    A = math.pi / 4 * ASSUMPTIONS["rod_diameter_m"] ** 2
    return ASSUMPTIONS["steel_E_Pa"] * A / rod_length


def k_concrete_westergaard() -> dict:
    """Vertical stiffness of a concrete slab on grade under an interior load (Westergaard).

    delta = P / (8 k_s l^2),  l = (D / k_s)^(1/4),  D = E h^3 / (12 (1 - nu^2)).
    Upper bound: rigid circular punch on an elastic half-space, k = 2 a E / (1 - nu^2),
    a = sqrt(A_pad / pi).
    """
    E, nu, h, ks = (ASSUMPTIONS[k] for k in ("concrete_E_Pa", "concrete_nu", "slab_thickness_m", "subgrade_modulus_N_m3"))
    D = E * h**3 / (12 * (1 - nu**2))
    l = (D / ks) ** 0.25
    k_slab = 8 * ks * l**2
    a = math.sqrt(0.1071 / math.pi)
    k_half = 2 * a * E / (1 - nu**2)
    return {"D_Nm": D, "l_m": l, "k_slab_N_m": k_slab, "punch_radius_m": a, "k_halfspace_N_m": k_half}


def k_leg_lateral(ext: float, guided_tip: bool, attach_z: float = 0.047, barrel_bottom_z: float = -0.4755,
                  pad_bottom_retracted_z: float = -0.6998) -> float:
    """Lateral stiffness of one leg at the load point [N/m] (Euler-Bernoulli, 2 segments, bracket clamped).

    segment 1: barrel D160/D115 from the bracket mid-height (attach_z) to the barrel bottom (barrel_bottom_z)
    segment 2: rod D110 from the barrel bottom to the load point
    guided_tip=True : rigid pad flat on the floor, load at the pad bottom, tip rotation fixed -> fixed-guided
    guided_tip=False: swivel pad, the rod receives the force at the ball centre (pad bottom + h_b) and the
                      ball transmits no moment -> fixed-free cantilever of length up to the ball centre
    Defaults are the FL geometry; use k_leg_lateral_legs() for per-leg values.
    Bracket / frame flexibility and rod-in-gland clearance are ignored (upper bound).
    """
    E = ASSUMPTIONS["steel_E_Pa"]
    Do, Di, Dr = ASSUMPTIONS["barrel_outer_diameter_m"], ASSUMPTIONS["bore_diameter_m"], ASSUMPTIONS["rod_diameter_m"]
    EI1 = E * math.pi / 64 * (Do**4 - Di**4)
    EI2 = E * math.pi / 64 * Dr**4
    tip_z = pad_bottom_retracted_z - ext + (0.0 if guided_tip else ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"])
    L1 = attach_z - barrel_bottom_z
    L2 = barrel_bottom_z - tip_z
    L = L1 + L2
    s = np.linspace(0.0, L, 20001)
    EI = np.where(s < L1, EI1, EI2)
    w = 1.0 / EI
    # unit-load method: tip load P=1 and tip moment M0; M(s) = P (L - s) - M0
    a11 = np.trapezoid((L - s) ** 2 * w, s)   # tip deflection per unit P
    a12 = np.trapezoid((L - s) * w, s)        # coupling
    a22 = np.trapezoid(w, s)                  # tip rotation per unit moment
    if not guided_tip:
        return 1.0 / a11
    M0 = a12 / a22                            # moment making the tip rotation zero
    return 1.0 / (a11 - M0 * a12)


def k_leg_lateral_legs(geo: "Geometry", ext, guided_tip: bool) -> np.ndarray:
    """Per-leg lateral stiffness [N/m] with each leg's own attachment, barrel and pad geometry."""
    ext = np.broadcast_to(np.asarray(ext, float), (4,))
    return np.array([k_leg_lateral(ext[i], guided_tip, geo.attach_z[i], geo.barrel_bottom_z[i], geo.pad_z_retracted[i])
                     for i in range(4)])


def series(*ks):
    return 1.0 / sum(1.0 / np.asarray(k, float) for k in ks)


# ---------------------------------------------------------------------------
# Statics: 4 vertical springs under a rigid body (small displacements)
# ---------------------------------------------------------------------------
def support_matrix(xy: np.ndarray) -> np.ndarray:
    """A (4x3): pad vertical displacement = A @ [uz, phi, theta] (about the frame origin)."""
    return np.column_stack([np.ones(len(xy)), xy[:, 1], -xy[:, 0]])


def static_loads(k, xy, W, cg_xy, delta=None, max_iter=8):
    """Vertical leg loads [N] for leg stiffnesses k (4,), weight W [N] at cg_xy.

    delta (4,): extra extension of each leg [m] (positive = leg longer = pushes body up).
    Unilateral: legs with negative force are removed (active set). Returns (F, q, active)
    where q = [uz, phi, theta] body displacement about the frame origin (up/rad).
    """
    k = np.asarray(k, float)
    delta = np.zeros(4) if delta is None else np.asarray(delta, float)
    A = support_matrix(xy)
    w = np.array([W, W * cg_xy[1], -W * cg_xy[0]])  # force, moment about x (+y lever), moment about y
    active = np.ones(4, bool)
    for _ in range(max_iter):
        Ka = np.diag(k * active)
        # compression c = delta - A q ; F = K c ; equilibrium A^T F = w
        H = A.T @ Ka @ A
        if np.linalg.matrix_rank(H) < 3:
            return np.full(4, np.nan), np.full(3, np.nan), active  # mechanism (tip-over)
        q = np.linalg.solve(H, A.T @ Ka @ delta - w)
        c = delta - A @ q
        F = k * c * active
        neg = (F < -1e-9) & active
        if not neg.any():
            return F, q, active
        active &= ~neg
    return F, q, active


def static_unilateral(xy, k, delta, W, cg_xy, max_iter=50):
    """Vertical statics with any number of unilateral springs (pads and crawler points), rigid body.

    xy (n,2) spring points, k (n,) stiffness, delta (n,) prestrain [m]: compression c = delta - A q
    (delta < 0 = initial gap). q = [uz, phi, theta] about the frame origin (up / rad). Weight W [N] at cg_xy.
    Full active set (springs can be added and removed). Returns (F (n,), q (3,), active (n,)).
    """
    xy = np.asarray(xy, float); k = np.asarray(k, float); delta = np.asarray(delta, float)
    A = support_matrix(xy)
    w = np.array([W, W * cg_xy[1], -W * cg_xy[0]])
    active = delta >= 0
    if not active.any():
        active = delta >= delta.max()
    for _ in range(max_iter):
        Ka = np.diag(k * active)
        H = A.T @ Ka @ A
        if np.linalg.matrix_rank(H) < 3:
            # fewer than 3 independent springs: add the closest inactive ones
            cand = np.where(active, -np.inf, delta)
            active[int(np.argmax(cand))] = True
            continue
        q = np.linalg.solve(H, A.T @ Ka @ delta - w)
        c = delta - A @ q
        new = c > 0
        if (new == active).all():
            return k * c * active, q, active
        active = new
    raise RuntimeError("active set did not converge")


def crawler_points(p: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Crawler contact sphere layout from YAML contact.crawler (ASSUMPTION layout, 00_docs/01_dynamics/dynamics_model.md 4.2).

    Returns (xy (n,2), k (n,), c (n,)) per sphere. Falls back to the documented default layout if the YAML has no
    layout keys yet: 2 tracks x 9 spheres, track centre lines y = +/-1.066 m, x evenly from -1.840 to 1.844 m.
    """
    cr = p["contact"]["crawler"]
    lay = cr.get("sphere_layout", {})
    nx = int(lay.get("spheres_per_track", CRAWLER_DEFAULTS["spheres_per_track"]))
    yt = float(lay.get("track_centre_y_m", CRAWLER_DEFAULTS["track_centre_y_m"]))
    x0, x1 = lay.get("x_range_m", CRAWLER_DEFAULTS["x_range_m"])
    xs = np.linspace(float(x0), float(x1), nx)
    xy = np.array([[x, s * yt] for s in (1.0, -1.0) for x in xs])
    n = len(xy)
    k = np.full(n, float(cr["kn_total_N_m"]) / n)
    c_tot = float(cr.get("damping_total_N_s_m", CRAWLER_DEFAULTS["damping_total_N_s_m"]))
    return xy, k, np.full(n, c_tot / n)


# crawler contact defaults (ASSUMPTIONS, rev. 5; mirrored in 00_docs/01_dynamics/dynamics_model.md section 10)
CRAWLER_DEFAULTS = {
    "spheres_per_track": 9,          # ASSUMPTION: 2 tracks x 9 spheres, ends included
    "track_centre_y_m": 1.066,       # ASSUMPTION: crawler bbox |y| 1.366 minus half an assumed 0.6 m shoe width
    "x_range_m": [-1.840, 1.844],    # crawler bbox x (parts_classified.csv), body frame
    "sphere_radius_m": 0.05,         # ASSUMPTION: bottom of each sphere at crawler_bottom_z
    "damping_ratio_heave": 0.05,     # ASSUMPTION: crawler-on-floor heave zeta, concrete (user decision 2026-10-20)
    "damping_ratio_heave_soil": 0.2,  # ASSUMPTION: crawler heave zeta on soil (SCM stage only)
    "damping_ratio_heave_range": [0.02, 0.3],  # sensitivity range
    "damping_total_N_s_m": None,     # filled by crawler_damping_total()
}


def crawler_damping_total(kn_total: float, mass_total: float, zeta: float = None) -> float:
    """Total crawler-floor dashpot [N s/m] giving zeta in heave of the whole machine on the crawler."""
    zeta = CRAWLER_DEFAULTS["damping_ratio_heave"] if zeta is None else zeta
    return 2 * zeta * math.sqrt(kn_total * mass_total)


def twist_vector(xy: np.ndarray) -> np.ndarray:
    """Unit vector n with A^T n = 0 (load pattern that changes no resultant)."""
    A = support_matrix(xy)
    u, s, vt = np.linalg.svd(A.T)
    n = vt[-1]
    return n / np.linalg.norm(n) * np.sign(n[0])


def load_sensitivity(k, xy) -> np.ndarray:
    """dF/d(delta) (4x4) [N/m]: change of leg loads per unit extension change (all legs in contact)."""
    k = np.asarray(k, float)
    K = np.diag(k)
    A = support_matrix(xy)
    return K - K @ A @ np.linalg.solve(A.T @ K @ A, A.T @ K)


def attitude_sensitivity(k, xy) -> np.ndarray:
    """dq/d(delta) (3x4): [uz, phi, theta] per unit leg extension (stiffness-weighted pseudo-inverse)."""
    k = np.asarray(k, float)
    K = np.diag(k)
    A = support_matrix(xy)
    return np.linalg.solve(A.T @ K @ A, A.T @ K)


# ---------------------------------------------------------------------------
# Linear 6-DoF model (rods rigidly attached to the body), pads as 3D springs to ground
# ---------------------------------------------------------------------------
def a_vec(d):
    """Gradients of (dx, dy, dz) of a body point at offset d w.r.t. q=[ux,uy,uz,phi,theta,psi]."""
    dx, dy, dz = d
    ax = np.array([1, 0, 0, 0, dz, -dy], float)
    ay = np.array([0, 1, 0, -dz, 0, dx], float)
    az = np.array([0, 0, 1, dy, -dx, 0], float)
    return ax, ay, az


def stiffness_6dof(body: Body, pad_pts: np.ndarray, kv, kh, F0) -> np.ndarray:
    """6x6 stiffness about the CoM: elastic pads (kv vertical, kh horizontal) + geometric term.

    F0: static vertical pad forces (must satisfy equilibrium with the weight).
    Geometric (preload) term: for each pad, -F0 * Hessian of the 2nd-order vertical displacement;
    in roll/pitch it equals -F0 * h_i (h_i = CoM height above the pad) -> -W h overall.
    """
    K = np.zeros((6, 6))
    for i in range(4):
        d = pad_pts[i] - body.com
        ax, ay, az = a_vec(d)
        K += kv[i] * np.outer(az, az) + kh[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K[3:, 3:] -= F0[i] * _hz(d)
    return K


def _hz(d):
    """Hessian of the 2nd-order vertical displacement of a body point at offset d w.r.t. (phi,theta,psi)."""
    dx, dy, dz = d
    return np.array([[-dz, 0, dx / 2], [0, -dz, dy / 2], [dx / 2, dy / 2, 0.0]])


def mass_6dof(body: Body) -> np.ndarray:
    M = np.zeros((6, 6))
    M[:3, :3] = body.mass * np.eye(3)
    M[3:, 3:] = body.inertia
    return M


DOF6 = ("surge x", "sway y", "heave z", "roll", "pitch", "yaw")


def classify_modes(M, Phi, labels):
    """Fraction of kinetic energy per coordinate for each mass-normalised mode."""
    out = []
    for j in range(Phi.shape[1]):
        v = Phi[:, j]
        e = v * (M @ v)
        e = np.abs(e) / np.abs(e).sum()
        top = np.argsort(e)[::-1]
        out.append({labels[t]: round(float(e[t]), 3) for t in top[:3] if e[t] > 0.02})
    return out


def modal(M, K, labels):
    from scipy.linalg import eigh

    w2, Phi = eigh(K, M)
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
    orth = np.abs(Phi.T @ M @ Phi - np.eye(len(w2))).max()
    return w2, f, Phi, classify_modes(M, Phi, labels), orth


# ---------------------------------------------------------------------------
# Linear 10-DoF model: superstructure 6-DoF + 4 rod axial DoF (oil column in series with contact)
# ---------------------------------------------------------------------------
def model_10dof(body: Body, geo: Geometry, ext, ko, kc, kh, co=None, cc=None, ch=None):
    """Returns M, K, C (10x10), DoF labels, static contact forces.

    q = [ux, uy, uz, phi, theta, psi, w_FL, w_FR, w_RL, w_RR]
    w_i: absolute vertical displacement of rod i (up +).
    oil spring i between the body point above the leg (attachment) and the rod: force ko (dz_att - w_i)
    contact spring i between rod and floor: kc (vertical), kh horizontal acts on the body at the pad
    (rod is laterally rigid with the body; rod lateral inertia neglected, 0.3 % of the mass).
    """
    ext = np.asarray(ext, float)
    W = body.mass * geo.g
    # oil carries the body share; contact carries body share + rod weight
    F_body, _, _ = static_loads(series(ko, kc), geo.pad_xy, W, body.com[:2])
    F_contact = F_body + geo.rod_mass * geo.g
    n = 10
    M = np.zeros((n, n)); K = np.zeros((n, n)); C = np.zeros((n, n))
    M[:6, :6] = mass_6dof(body)
    for i in range(4):
        M[6 + i, 6 + i] = geo.rod_mass[i]
    co = np.zeros(4) if co is None else np.asarray(co, float)
    cc = np.zeros(4) if cc is None else np.asarray(cc, float)
    ch = np.zeros(4) if ch is None else np.asarray(ch, float)
    for i in range(4):
        d_att = np.array([*geo.pad_xy[i], geo.attach_z[i]]) - body.com
        d_pad = np.array([*geo.pad_xy[i], geo.pad_z_retracted[i] - ext[i]]) - body.com
        _, _, az_att = a_vec(d_att)
        ax_p, ay_p, _ = a_vec(d_pad)
        b = np.zeros(n); b[:6] = az_att; b[6 + i] = -1.0  # oil compression rate = dz_att - w_i
        K += ko[i] * np.outer(b, b); C += co[i] * np.outer(b, b)
        e = np.zeros(n); e[6 + i] = 1.0
        K += kc[i] * np.outer(e, e); C += cc[i] * np.outer(e, e)
        for a in (ax_p, ay_p):
            aa = np.zeros(n); aa[:6] = a
            K += kh[i] * np.outer(aa, aa); C += ch[i] * np.outer(aa, aa)
        # geometric (preload) stiffness of the external forces: upward contact force at the pad,
        # downward rod weight at the rod CoM (rod moves laterally with the body)
        K[3:6, 3:6] -= F_contact[i] * _hz(d_pad)
        d_rod = geo.rod_com_retracted[i] - np.array([0, 0, ext[i]]) - body.com
        K[3:6, 3:6] += geo.rod_mass[i] * geo.g * _hz(d_rod)
    labels = list(DOF6) + [f"rod {nm}" for nm in LEG_NAMES]
    return M, K, C, labels, F_contact


def complex_modes(M, K, C):
    """Damped eigenvalues of M q'' + C q' + K q = 0 -> (f_n [Hz], zeta), sorted by f_n."""
    n = M.shape[0]
    Minv = np.linalg.inv(M)
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-Minv @ K, -Minv @ C]])
    lam = np.linalg.eigvals(A)
    lam = lam[np.imag(lam) >= 0]
    wn = np.abs(lam)
    zeta = -np.real(lam) / np.where(wn > 0, wn, 1)
    idx = np.argsort(wn)
    return wn[idx] / (2 * np.pi), zeta[idx]


def static_slope_10dof(body: Body, geo: Geometry, ext, ko, kn, kt, slope_pitch_deg=0.0, slope_roll_deg=0.0,
                       delta=None):
    """Linear statics, levelled body on a sloped rigid floor, swivel pads (force through the ball centre).

    "Place and settle" procedure: pads placed on the floor with zero spring force, then gravity applied.
    DoF: body [ux,uy,uz,phi,theta,psi] about the superstructure CoM + rod vertical w_i (rods laterally
    rigid with the body = rigid prismatic guide). Oil spring ko (body attachment <-> rod, axial = z),
    contact spring at the ball centre: kn along the floor normal, kt in the floor plane (stick).
    Floor z = sx x + sy y with sx = -tan(pitch), sy = tan(roll) (sign as in run_reference levelling).
    Returns dict: contact reaction vectors R (4,3) on the rods [N], cylinder force (oil) [N],
    normal / tangential components, friction utilisation |T|/N.
    delta (4,), optional: extra reference extension of each leg after placing [m] (oil spring prestrain,
    + = leg longer, i.e. s_ref advanced). None reproduces the plain place-and-settle solution.
    """
    ext = np.asarray(ext, float)
    sx = -math.tan(math.radians(slope_pitch_deg)); sy = math.tan(math.radians(slope_roll_deg))
    nrm = np.array([-sx, -sy, 1.0]); nrm /= np.linalg.norm(nrm)
    P_n = np.outer(nrm, nrm)
    kn = np.broadcast_to(np.asarray(kn, float), (4,)); kt = np.broadcast_to(np.asarray(kt, float), (4,))
    hb = ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"]
    n = 10
    K = np.zeros((n, n)); f = np.zeros(n)
    f[2] = -body.mass * geo.g
    f[6:] = -geo.rod_mass * geo.g
    Bc = []
    for i in range(4):
        d_att = np.array([*geo.pad_xy[i], geo.attach_z[i]]) - body.com
        d_ball = np.array([*geo.pad_xy[i], geo.pad_z_retracted[i] - ext[i] + hb]) - body.com
        _, _, az_att = a_vec(d_att)
        d_cont = d_ball - hb * nrm  # sphere (radius hb, centred at the ball) touches the floor here
        ax_b, ay_b, _ = a_vec(d_cont)
        b = np.zeros(n); b[:6] = az_att; b[6 + i] = -1.0
        K += ko[i] * np.outer(b, b)
        # contact-point displacement: x,y from the body (rigid guide), z from the rod
        G = np.zeros((3, n)); G[0, :6] = ax_b; G[1, :6] = ay_b; G[2, 6 + i] = 1.0
        Kc = kn[i] * P_n + kt[i] * (np.eye(3) - P_n)  # contact stiffness tensor (world)
        K += G.T @ Kc @ G
        Bc.append((G, b, Kc))
    if delta is None:
        q = np.linalg.solve(K, f)
        F_cyl = np.array([-ko[i] * (Bc[i][1] @ q) for i in range(4)])  # oil force (compression +)
    else:
        delta = np.asarray(delta, float)
        # oil compression = delta - b q -> generalised force sum ko delta b
        q = np.linalg.solve(K, f + sum(ko[i] * delta[i] * Bc[i][1] for i in range(4)))
        F_cyl = np.array([ko[i] * (delta[i] - Bc[i][1] @ q) for i in range(4)])
    R = np.array([-(Kc @ (G @ q)) for G, _, Kc in Bc])              # floor -> rod
    N = R @ nrm
    T = np.linalg.norm(R - np.outer(N, nrm), axis=1)
    return {"R": R, "F_cyl": F_cyl, "N": N, "T": T, "mu_used": T / N, "q": q, "normal": nrm}


# ---------------------------------------------------------------------------
# Support polygon / tip-over
# ---------------------------------------------------------------------------
def support_polygon(geo: Geometry, swivel: bool = True) -> np.ndarray:
    """Support polygon (CCW). swivel=True: the leg force passes through the ball centre, so the support points
    are the pad centres (default, CLAUDE.md 2026-10-19). swivel=False: convex hull of the pad octagons (rigid pads)."""
    from scipy.spatial import ConvexHull

    if swivel:
        pts = geo.pad_xy.copy()
        hull = ConvexHull(pts)
        return pts[hull.vertices]
    pts = np.vstack([geo.pad_xy[i] + geo.pad_polygons[i] for i in range(4)])
    hull = ConvexHull(pts)
    return pts[hull.vertices]  # counter-clockwise


def edge_margins(poly: np.ndarray, p: np.ndarray):
    """Signed distances of point p to every edge of a CCW polygon (positive = inside)."""
    out = []
    n = len(poly)
    for j in range(n):
        a, b = poly[j], poly[(j + 1) % n]
        t = b - a
        nrm = np.array([t[1], -t[0]]) / np.linalg.norm(t)  # outward normal for CCW
        out.append((float(-(p - a) @ nrm), a, b, -nrm))     # inward normal returned
    return out
