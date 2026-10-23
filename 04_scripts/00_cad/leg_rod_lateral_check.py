"""Leg rod / cylinder check under the pad tangential (lateral) force on sloped ground (revision 3.3).

Revision 3.3 (2026-10-22): --h4-set LABEL MODE_TOKEN FILE [FILE ...] (repeatable) for several H4 sets, e.g. the R6
coupled-judgement runs 'O|R6|*' + sensitivity bundle 'S|R6|*' (worst governs); key 'h4_sets'. Variants: bound /
nofloor, carry rule 'hold' (bracketing run above the angle not reduced), margins at --h4-check-deg angles.

Revision 3.2 (2026-10-22): optional --h4-pairs <json> (control-expert adopted H4 runs, runs[].x.step_pairs) adds the
key 'h4_adopted' with the re-anchoring criterion RA_A_H4 and the judgement pair ALR_H4 = AL and RA_A_H4 for the
fore-aft slopes (dynamics_model.md 5.13.5 supplement 2). Without the option the output is the same as revision 3.1.
Revision 3 / 3.1: REXOME35 per-leg cylinders, stroke 0.70 m, per-leg 350 bar lock; 'd8_boundary_scan' key.

Revision 2 (2026-10-21): the lateral loads now come from the dynamics-expert reduced-model matrix
(00_docs/01_dynamics/dynamics_model.md rev. 18, section 3.10; 06_analysis/00_dynamics/pad_tangential_check.json)
instead of the kinematic estimate scaled to 36 kN. The 36 kN at pitch +3.7 deg was clipped at the rear mu N
(stick demand 43-44 kN with the YAML k_t, 29 kN with the secant k_t), so the old calibration factor 0.838 is dropped.
Two lateral stiffness models are carried side by side:
  - secant k_t(e)  : series(leg bending at the levelled extension, concrete)  -> best estimate
  - YAML k_t       : contact.rigid_floor.L1.kt_per_pad_N_m (beam at e 0.40 m) -> upper bound

The script checks the leg rod, barrel, rod-end neck, guides (gland bush, piston) and buckling under the per-leg
lateral force at the swivel ball centre with the concurrent axial force, on the D8 verification boundary
(roll 5.5 / pitch 3.5 deg) and the provisional limit boundary (roll 4.4 / pitch 3.2 deg), derives slope limits
for rod yield safety factor 1.5 per rod material, and evaluates the re-anchoring manoeuvre (3.10.7).

Inputs (read only):
  - 02_params/rexome33.yaml                    leg geometry, loads, stiffness (single source of parameters)
  - 01_cad/02_legs/leg_faces.csv               leg cylinder faces (CAD mm, Y-up) from the B-rep cache
  - 01_cad/07_faces/instance_faces.csv.gz      convexity of the jack cylinder faces (face_index.py)
  - 01_cad/02_legs/legs/*_10_1.brep            moving part B-rep (volume check)
  - 06_analysis/00_dynamics/pad_tangential_check.json  pad tangential force matrix (dynamics-expert, rev. 18)
Outputs:
  - 01_cad/02_legs/leg_rod_lateral_check.json
  - 01_cad/02_legs/leg_rod_lateral_check.png

Coordinates: body frame (x forward, y left, z up), origin = CAD origin, metres. CAD Y (mm) -> body z = Y / 1000.
Slope sign (dynamics_model.md 3.10.1): pitch > 0 nose down (front low), roll > 0 left up (right low).
Units: SI (m, N, Pa); tables convert to kN, kN m, MPa for reporting.

Run (project root, Chrono-dev, OPENBLAS_NUM_THREADS=1):
  C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I 04_scripts/00_cad/leg_rod_lateral_check.py
"""
from __future__ import annotations

import csv
import functools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import scipy.linalg as sla
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cad_common import LEGS_DIR, PROJECT_ROOT  # noqa: E402

YAML_PATH = PROJECT_ROOT / "02_params" / "rexome33.yaml"
FACES_CSV = LEGS_DIR / "leg_faces.csv"
PTC_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "pad_tangential_check.json"
OUT_JSON = LEGS_DIR / "leg_rod_lateral_check.json"
OUT_PNG = LEGS_DIR / "leg_rod_lateral_check.png"

LEG_NAMES = ("FL", "FR", "RL", "RR")
CAD_INSTANCE = {"FL": "FRONT JACK CYL:1", "FR": "FRONT JACK CYL:2", "RL": "REAR JACK CYL:1", "RR": "REAR JACK CYL:2"}

# ---------------------------------------------------------------------------
# Assumptions (not in the CAD / YAML). Every value is reported as an assumption in the JSON.
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    "rod_yield_Pa": {"C45_normalised": 305e6, "20MnV6": 450e6},  # chrome-plated bar, induction hardened surface ignored
    "barrel_yield_Pa": 355e6,          # E355 (ST52) honed tube
    "required_yield_safety_factor": 1.5,
    "required_buckling_safety_factor": 3.5,
    "straightness_per_length": 1.0e-3,  # initial bow of rod + barrel (conservative vs. 0.2 mm/m bar tolerance)
    "guide_diametral_clearance_m": 0.3e-3,  # total of gland bush + piston guide clearance (rod tilt in the barrel)
    "guide_allowable_pressure_Pa": {"PTFE_bronze_dynamic": 15e6, "phenolic_fabric_ring": 40e6, "phenolic_static_upper": 100e6},
    "gland_effective_bearing_length_m": 0.040,  # guide band width inside the 125 mm CAD gland (CAD has no bush detail)
    "piston_effective_bearing_length_m": 0.020,  # = CAD piston thickness (CAD has no guide ring detail)
    "lateral_force_source": "dynamics_model.md rev.18 3.10 matrix (pad_tangential_check.json), mu 0.5, "
                            "secant k_t = best estimate, YAML k_t = upper bound; between / beyond the simulated "
                            "angles: anchored-pad kinematics scaled per leg to the provisional-boundary vertex",
    "lock_pressure_Pa": 350e5,         # CLAUDE.md: locked cylinder max 350 bar
    "dynamic_peak_axial_N": 141.0e3,   # dynamics_model.md 3.7: dynamic max pad reaction (levelling on flat floor)
    "reanchor_residual_independent_of_slope": True,  # residual ~ mu * P_stop (3.10.7), used for the sustained phase
    "lock_check_SF": 1.0,              # 350 bar lock (364 kN) is an exceptional load: no yield required
    "criterion_B_peak_SF": 1.0,        # option B (with re-anchoring only): one-off levelling-end peak may reach yield
}

STEEL_DENSITY = 7850.0
RANGES = {"V": (5.5, 3.5), "P": (4.4, 3.2)}  # (Phi, Theta) deg: D8 verification range, provisional limit
# rev. 3 (REXOME35 cylinders, dynamics_model.md 5.12.1 / 5.12.7): cylinder section (bore, rod, barrel outer) [m] behind
# the closed-loop matrix 06_analysis/00_dynamics/pad_tangential_check.json rev. 18 (REXOME33 CAD, common to all legs).
# When that file's k_t (meta.kt_yaml_N_m) differs from the YAML k_t, its envelopes are rescaled per slope and leg by the
# anchored-pad kinematics ratio raw(YAML) / raw(PTC basis), then capped at mu N (dynamics order R method, ASSUMPTION:
# the dynamic factor simulated / anchored kinematics does not change with k_t). Rerun run_pad_tangential_check.py with
# the new k_t to remove the rescale (dynamics order 6).
PTC_CYLINDERS_M = (0.115, 0.110, 0.160)
PTC_KT_REL_TOL = 1e-6


def load_params() -> dict:
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cylinder_of(p: dict, leg: str) -> tuple[float, float, float]:
    """(bore, rod, barrel outer) [m] of one leg: YAML legs.<leg>.cylinder (rev. 30) or the old common actuator keys."""
    c = p["legs"][leg].get("cylinder")
    if c:
        return float(c["bore_diameter_m"]), float(c["rod_diameter_m"]), float(c["barrel_outer_diameter_m"])
    a = p["actuator"]
    return float(a["bore_diameter_m"]), float(a["rod_diameter_m"]), float(a["barrel_outer_diameter_m"])


def per_leg_cylinders(p: dict) -> bool:
    return all(p["legs"][leg].get("cylinder") for leg in LEG_NAMES)


def static_cylinder_forces_kn(p: dict) -> np.ndarray:
    """Static cylinder forces [N] (top level, level floor) of the L1 k_n distribution: dyn_model.static_loads with
    YAML contact.rigid_floor.L1.kn_per_pad_N_m, superstructure top + 4 moving parts at e_op, minus the rod weights
    (same as the dynamics order R input, dynamics_model.md 5.12.1)."""
    sys.path.insert(0, str(PROJECT_ROOT / "04_scripts" / "01_dynamics"))
    sys.dont_write_bytecode = True
    import dyn_model as dm  # noqa: PLC0415

    dm.set_cylinders_from_params(p)
    geo = dm.geometry_from_params(p)
    L1 = p["contact"]["rigid_floor"]["L1"]
    kn = np.array([float(L1["kn_per_pad_N_m"][n]) for n in LEG_NAMES])
    e_op = np.array([float(L1["derivation"]["operating_extension_m"][n]) for n in LEG_NAMES])
    bw = dm.body_with_rods(p, geo, "top", e_op)
    Fc, _, _ = dm.static_loads(kn, geo.pad_xy, bw.mass * geo.g, bw.com[:2])
    return np.asarray(Fc, float) - geo.rod_mass * geo.g


# ---------------------------------------------------------------------------
# 1. Geometry from the leg face table (CAD mm) -> body z, retracted state
# ---------------------------------------------------------------------------
def leg_geometry(p: dict) -> dict:
    rows = list(csv.DictReader(open(FACES_CSV, encoding="utf-8-sig")))
    out = {}
    for leg in LEG_NAMES:
        inst = CAD_INSTANCE[leg]
        mine = [r for r in rows if f"/ {inst} /" in r["instance_path"]]
        off = float(p["legs"][leg]["retracted_offset_from_cad_m"])

        def cyl(solid: str, radius: float, pick: str = "all"):
            sel = [r for r in mine if f"{solid}:1" in r["instance_path"] and r["surface_type"] == "cylinder"
                   and abs(float(r["radius_mm"]) - radius) < 0.01 and abs(float(r["axis_or_normal_y"])) > 0.99]
            if not sel:
                raise RuntimeError(f"{leg}: no cylinder R{radius} in {solid}")
            if pick == "largest":
                sel = [max(sel, key=lambda r: float(r["area_mm2"]))]
            lo = min(float(r["bbox_min_y_mm"]) for r in sel) / 1000.0
            hi = max(float(r["bbox_max_y_mm"]) for r in sel) / 1000.0
            return lo, hi

        # moving part (solid10) is shifted up by the retracted offset; barrel (solid17) is fixed
        rod = tuple(z + off for z in cyl("솔리드10", 55.0))
        piston = tuple(z + off for z in cyl("솔리드10", 57.5))
        neck = tuple(z + off for z in cyl("솔리드10", 40.0))
        boss = tuple(z + off for z in cyl("솔리드10", 85.0))
        bore = cyl("솔리드17", 57.5)
        gland = cyl("솔리드17", 55.0)
        barrel = cyl("솔리드17", 80.0, pick="largest")
        holes = sorted({round((float(r["bbox_min_y_mm"]) + float(r["bbox_max_y_mm"])) / 2000.0, 4)
                        for r in mine if r["surface_type"] == "cylinder" and abs(float(r["radius_mm"]) - 13.0) < 0.01})
        pad_bottom = float(p["legs"][leg]["pad_bottom_center_retracted_m"][2])
        dims = cylinder_of(p, leg)
        out[leg] = {
            "leg": leg, "dims": dims,  # rev. 3: per-leg section (bore, rod, barrel outer) [m]
            "P_lock_N": ASSUMPTIONS["lock_pressure_Pa"] * math.pi / 4 * dims[0] ** 2,  # 350 bar x head area of this leg
            "rod_R55_z_m": rod, "piston_z_m": piston, "neck_R40_z_m": neck, "boss_R85_z_m": boss,
            "bore_z_m": bore, "gland_z_m": gland, "barrel_R80_z_m": barrel, "bolt_row_z_m": holes,
            "pad_bottom_z_m": pad_bottom,
            "attach_z_m": float(p["legs"][leg]["attachment_point_m"][2]),
            "neck_above_pad_bottom_m": (neck[0] - pad_bottom, neck[1] - pad_bottom),
            "rod_bottom_above_pad_bottom_m": rod[0] - pad_bottom,
            "piston_top_minus_bore_top_m": piston[1] - bore[1],
            "yaml_barrel_z_range_m": p["legs"][leg]["barrel_z_range_m"],
            "yaml_bore_z_range_m": p["legs"][leg]["bore_z_range_m"],
        }
    return out


def convexity_and_volume() -> dict:
    """Check that the rod is solid (no concave cylinder in the moving part) and compare the B-rep volume."""
    res = {}
    try:
        import face_index  # noqa: E402
        df = face_index.query(kind="cylinder", top_assembly="FRONT JACK CYL:1")
        mv = df[df["instance_path"].str.contains("솔리드10")]
        res["moving_part_concave_cylinders"] = [
            {"radius_mm": float(r.radius_mm), "z_min_m": float(r.bbox_min_z_body_m), "z_max_m": float(r.bbox_max_z_body_m)}
            for r in mv.itertuples() if not bool(r.convex)]
        bar = df[df["instance_path"].str.contains("솔리드17")]
        res["barrel_concave_cylinders_R_mm"] = sorted({round(float(r.radius_mm), 2) for r in bar.itertuples() if not bool(r.convex)})
    except Exception as exc:  # pragma: no cover - diagnostic only
        res["face_index_error"] = repr(exc)
    try:
        from OCC.Core.BRepGProp import brepgprop
        from OCC.Core.GProp import GProp_GProps
        import brep_cache  # noqa: E402
        vols = {}
        for tag in ("10", "17"):
            fp = LEGS_DIR / "legs" / f"FRONT_JACK_CYL_1___{tag}_1.brep"
            shp = brep_cache.read_brep(fp)
            g = GProp_GProps()
            brepgprop.VolumeProperties(shp, g)
            vols[f"solid{tag}_volume_m3"] = g.Mass() * 1e-9  # B-rep in mm
        res.update(vols)
    except Exception as exc:  # pragma: no cover
        res["brep_error"] = repr(exc)
    return res


# ---------------------------------------------------------------------------
# 2. Levelling extensions on a plane (crawler box clearance), and the anchored-pad internal force estimate
# ---------------------------------------------------------------------------
def rot_ground(phi: float, theta: float) -> np.ndarray:
    """Ground orientation in the levelled body frame: R = Rx(phi) Ry(theta); n = R e_z.
    theta > 0: front low (pitch + when the body stands on the crawler), phi > 0: right low."""
    cx, sx, cy, sy = math.cos(phi), math.sin(phi), math.cos(theta), math.sin(theta)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    return Rx @ Ry


def levelling_extension(p: dict, phi_deg: float, theta_deg: float) -> np.ndarray:
    """Extensions [m] that level the body with the lowest crawler-box corner at the clearance (sphere-touch form)."""
    R = rot_ground(math.radians(phi_deg), math.radians(theta_deg))
    n = R[:, 2]
    zc = float(p["ground"]["crawler_bottom_z_m"])
    clr = float(p["simulation"]["crawler_clearance_m"])
    corners = np.array([[x, y] for x in (-1.840, 1.844) for y in (-1.366, 1.366)])  # dyn_model.geometry_from_params

    def zg_rel(xy):  # plane height relative to z0
        return -(n[0] * xy[..., 0] + n[1] * xy[..., 1]) / n[2]
    z0 = np.min(zc - clr - zg_rel(corners))  # every corner at least clr above the plane
    hb = float(p["legs"]["FL"]["pad"].get("swivel_center_above_pad_bottom_m", 0.06))
    e = []
    for leg in LEG_NAMES:
        x, y, zp = p["legs"][leg]["pad_bottom_center_retracted_m"]
        zg = z0 + zg_rel(np.array([x, y]))
        e.append(zp - zg - hb * (1.0 / n[2] - 1.0))
    return np.array(e)


def anchored_internal_force(p: dict, phi_deg: float, theta_deg: float, kt: np.ndarray) -> np.ndarray:
    """Internal pad tangential forces [N] (4x2, body x/y) from the 'slope extension' mechanism.

    Each pad is anchored to the ground at first touch while the body stands on the crawler parallel to the ground
    (body z = ground normal, so extension until then is purely normal). After crawler lift-off the body rotates to
    level. Ball tangential displacement relative to its anchor (ground-plane coordinates):
        d_i = (t1 . r_i, t2 . r_i) - (x_i, y_i),  t1 = R e_x, t2 = R e_y, r_i = ball centre (levelled body frame)
    The body is free to translate and yaw, so the rigid planar part of d_i is removed (weighted least squares).
    Uncapped linear springs kt; returns k_i (d_i - rigid fit)."""
    R = rot_ground(math.radians(phi_deg), math.radians(theta_deg))
    t1, t2 = R[:, 0], R[:, 1]
    e = levelling_extension(p, phi_deg, theta_deg)
    hb = float(p["legs"]["FL"]["pad"].get("swivel_center_above_pad_bottom_m", 0.06))
    d, xy = [], []
    for i, leg in enumerate(LEG_NAMES):
        x, y, zp = p["legs"][leg]["pad_bottom_center_retracted_m"]
        r = np.array([x, y, zp - e[i] + hb])
        d.append([t1 @ r - x, t2 @ r - y])
        xy.append([x, y])
    d, xy = np.array(d), np.array(xy)
    # rigid planar fit: u_i = c + w * (-y_i, x_i)
    A = np.zeros((8, 3)); b = d.reshape(-1); W = np.repeat(kt, 2)
    A[0::2, 0] = 1.0; A[1::2, 1] = 1.0
    A[0::2, 2] = -xy[:, 1]; A[1::2, 2] = xy[:, 0]
    sw = np.sqrt(W)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
    res = (b - A @ sol).reshape(4, 2)
    # force on the pad from the ground opposes the pad displacement relative to the anchor
    return -kt[:, None] * res


# ---------------------------------------------------------------------------
# 3. Beam models
# ---------------------------------------------------------------------------
def sec_rod(d):
    A = math.pi / 4 * d**2
    I = math.pi / 64 * d**4
    return A, I, I / (d / 2)


def sec_tube(do, di):
    A = math.pi / 4 * (do**2 - di**2)
    I = math.pi / 64 * (do**4 - di**4)
    return A, I, I / (do / 2)


def beam_fe(z_top: float, z_tip: float, z_step: float, EI_top: float, EI_bot: float, n_el: int = 80):
    """Clamped (top) stepped Euler-Bernoulli column along z, tip at the bottom. Returns K, Kg (unit axial
    compression) and node coordinates s (distance from the clamp)."""
    L = z_top - z_tip
    Ls = min(max(z_top - z_step, 0.0), L)  # node exactly at the section step
    n1 = int(np.clip(round(n_el * Ls / L), 1, n_el - 1))
    s = np.concatenate([np.linspace(0.0, Ls, n1 + 1)[:-1], np.linspace(Ls, L, n_el - n1 + 1)])
    ndof = 2 * (n_el + 1)
    K = np.zeros((ndof, ndof)); Kg = np.zeros((ndof, ndof))
    for e in range(n_el):
        h = s[e + 1] - s[e]
        zm = z_top - 0.5 * (s[e] + s[e + 1])
        EI = EI_top if zm > z_step else EI_bot
        ke = EI / h**3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                   [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
        kg = 1.0 / (30 * h) * np.array([[36, 3 * h, -36, 3 * h], [3 * h, 4 * h * h, -3 * h, -h * h],
                                        [-36, -3 * h, 36, -3 * h], [3 * h, -h * h, -3 * h, 4 * h * h]])
        idx = slice(2 * e, 2 * e + 4)
        K[idx, idx] += ke; Kg[idx, idx] += kg
    return K, Kg, s


def free_dofs(n_nodes: int, tip_fix_v: bool, tip_fix_rot: bool):
    fixed = {0, 1}
    if tip_fix_v:
        fixed.add(2 * (n_nodes - 1))
    if tip_fix_rot:
        fixed.add(2 * (n_nodes - 1) + 1)
    return np.array([i for i in range(2 * n_nodes) if i not in fixed])


def critical_load(K, Kg, s, tip_fix_v, tip_fix_rot) -> float:
    fd = free_dofs(len(s), tip_fix_v, tip_fix_rot)
    w = sla.eigh(K[np.ix_(fd, fd)], Kg[np.ix_(fd, fd)], eigvals_only=True, subset_by_index=[0, 0])
    return float(w[0])


def tip_response(K, s, tip_fix_rot: bool):
    """Unit lateral tip force: tip deflection [m/N] and tip moment reaction [N m/N] (rigid pad: rotation fixed)."""
    n = len(s)
    fd = free_dofs(n, False, tip_fix_rot)
    f = np.zeros(2 * n); f[2 * (n - 1)] = 1.0
    u = np.zeros(2 * n)
    u[fd] = np.linalg.solve(K[np.ix_(fd, fd)], f[fd])
    if not tip_fix_rot:
        return u[2 * (n - 1)], 0.0
    r = K @ u - f
    return u[2 * (n - 1)], float(r[2 * (n - 1) + 1])  # reaction moment at the tip (sign: element convention)


@functools.lru_cache(maxsize=None)
def _fe_cached(z_clamp, z_load, z_step, EI_top, EI_bot, swivel):
    K, Kg, s = beam_fe(z_clamp, z_load, z_step, EI_top, EI_bot)
    P_sway = critical_load(K, Kg, s, tip_fix_v=False, tip_fix_rot=not swivel)
    P_nonsway = critical_load(K, Kg, s, tip_fix_v=True, tip_fix_rot=not swivel)
    flex, m_tip_unit = tip_response(K, s, tip_fix_rot=not swivel)
    return P_sway, P_nonsway, flex, m_tip_unit


def johnson(P_E: float, A: float, sy: float) -> float:
    Py = A * sy
    return P_E if P_E < Py / 2 else Py * (1.0 - Py / (4.0 * P_E))


# ---------------------------------------------------------------------------
# 4. Leg check for one (extension, lateral force, axial force) case
# ---------------------------------------------------------------------------
def leg_case(g: dict, p: dict, e: float, F: float, P: float, pad: str, sy_rod: float) -> dict:
    E = 2.1e11
    D_bore, D_rod, D_bar = g["dims"] if "dims" in g else cylinder_of(p, "FL")  # rev. 3: per leg
    A_r, I_r, Z_r = sec_rod(D_rod)
    A_n, I_n, Z_n = sec_rod(0.080)
    A_b, I_b, Z_b = sec_tube(D_bar, D_bore)
    hb = float(p["legs"]["FL"]["pad"].get("swivel_center_above_pad_bottom_m", 0.06))
    z_pb = g["pad_bottom_z_m"] - e
    z_ball = z_pb + hb
    z_load = z_ball if pad == "swivel" else z_pb
    gl_lo, gl_hi = g["gland_z_m"]
    gl_c = 0.5 * (gl_lo + gl_hi)
    bore_top = g["bore_z_m"][1]
    t_p = g["piston_z_m"][1] - g["piston_z_m"][0]
    p_hi = bore_top - e
    p_c = p_hi - t_p / 2
    z_bolt_lo = min(g["bolt_row_z_m"])
    z_clamp = g["attach_z_m"]

    # FE: clamp at the bolt-group centre (as dyn_model.k_leg_lateral), barrel EI down to the barrel bottom
    swivel = pad == "swivel"
    P_E_sway, P_E_nonsway, flex, m_tip_unit = _fe_cached(round(z_clamp, 6), round(z_load, 6),
                                                         round(g["barrel_R80_z_m"][0], 6), E * I_b, E * I_r, swivel)
    k_lat = 1.0 / flex
    M_tip = abs(m_tip_unit) * F  # rigid pad: moment taken by the pad on the ground

    # imperfection: straightness over the clamp-to-load length + rod tilt in the guide clearance
    a_edge = gl_lo - z_load
    b_edge = max(p_hi - gl_lo, 1e-3)
    e0 = ASSUMPTIONS["straightness_per_length"] * (z_clamp - z_load) + ASSUMPTIONS["guide_diametral_clearance_m"] / b_edge * a_edge
    delta = F * flex
    AF = 1.0 / (1.0 - P / P_E_sway)  # sway amplification (Cm = 1)

    def m_at(z):  # first-order moment at section z (above the load point), N m
        return F * (z - z_load) - (M_tip if not swivel else 0.0)

    a_c = gl_c - z_load
    b_c = max(p_c - gl_c, 1e-3)
    M_rod0 = abs(m_at(gl_c))
    M_rod = (M_rod0 + P * (delta + e0)) * AF
    # neck (D80) at the bottom of the rod: lever from the load point to the top of the neck
    z_neck_top = g["neck_R40_z_m"][1] - e
    M_neck = abs(m_at(z_neck_top)) if z_neck_top > z_load else 0.0
    M_neck_lo = abs(m_at(g["neck_R40_z_m"][0] - e))
    M_neck = max(M_neck, M_neck_lo)
    M_bar = (abs(m_at(z_bolt_lo)) + P * (delta + e0)) * AF
    M_clamp = abs(m_at(z_clamp)) + P * (delta + e0)

    # guide reactions (rod as a lever on two supports: piston guide and gland bush), centre and edge models
    V = abs(F)  # shear carried into the barrel (moment from M_tip changes the reactions, include it)
    Mg = M_rod0
    R_pis_c = Mg / b_c
    R_gl_c = R_pis_c + V
    R_pis_e = abs(m_at(gl_lo)) / b_edge
    R_gl_e = R_pis_e + V
    Dg = D_rod; Dp = D_bore
    w_gl = ASSUMPTIONS["gland_effective_bearing_length_m"]; w_gl_cad = gl_hi - gl_lo
    w_p = ASSUMPTIONS["piston_effective_bearing_length_m"]

    # stresses
    sig_rod = P / A_r + M_rod / Z_r
    sig_neck = P / A_n + M_neck * AF / Z_n
    p_oil = P / (math.pi / 4 * D_bore**2)
    ro, ri = D_bar / 2, D_bore / 2
    hoop_o = 2 * p_oil * ri**2 / (ro**2 - ri**2)
    hoop_i = p_oil * (ro**2 + ri**2) / (ro**2 - ri**2)
    sb_o = M_bar / Z_b
    sb_i = sb_o * ri / ro
    vm_o = math.sqrt(sb_o**2 + hoop_o**2 - sb_o * hoop_o)
    vm_i = math.sqrt(sb_i**2 + hoop_i**2 + p_oil**2 - sb_i * hoop_i + sb_i * p_oil + hoop_i * p_oil)
    sig_bar = max(vm_o, vm_i)
    P_cr_sway = johnson(P_E_sway, A_r, sy_rod)
    P_cr_nonsway = johnson(P_E_nonsway, A_r, sy_rod)
    sb = ASSUMPTIONS["barrel_yield_Pa"]
    return {
        "extension_m": e, "lateral_force_N": F, "axial_force_N": P, "pad_model": pad, "rod_yield_Pa": sy_rod,
        "load_point_z_m": z_load, "lever_gland_centre_m": a_c, "guide_span_centre_m": b_c,
        "lever_gland_lower_edge_m": a_edge, "guide_span_edge_m": b_edge,
        "k_lat_bending_N_m": k_lat, "tip_deflection_m": delta, "imperfection_m": e0,
        "P_euler_sway_N": P_E_sway, "P_euler_nonsway_N": P_E_nonsway,
        "P_cr_sway_johnson_N": P_cr_sway, "P_cr_nonsway_johnson_N": P_cr_nonsway,
        "amplification_sway": AF, "M_tip_pad_Nm": M_tip,
        "M_rod_gland_first_order_Nm": M_rod0, "M_rod_gland_Nm": M_rod,
        "M_neck_Nm": M_neck, "M_barrel_bottom_bolt_row_Nm": M_bar, "M_bracket_bolt_centre_Nm": M_clamp,
        "sigma_rod_Pa": sig_rod, "sigma_neck_Pa": sig_neck, "sigma_barrel_vm_Pa": sig_bar,
        "oil_pressure_Pa": p_oil,
        "SF_rod_yield": sy_rod / sig_rod, "SF_neck_yield": sy_rod / sig_neck, "SF_barrel_yield": sb / sig_bar,
        "SF_buckling_sway": P_cr_sway / P if P > 0 else None, "SF_buckling_nonsway": P_cr_nonsway / P if P > 0 else None,
        "R_gland_centre_N": R_gl_c, "R_piston_centre_N": R_pis_c, "R_gland_edge_N": R_gl_e, "R_piston_edge_N": R_pis_e,
        "p_gland_N_per_m2": {"band_40mm_centre": R_gl_c / (Dg * w_gl), "cad_125mm_centre": R_gl_c / (Dg * w_gl_cad),
                             "band_40mm_edge": R_gl_e / (Dg * w_gl)},
        "p_piston_N_per_m2": {"cad_20mm_centre": R_pis_c / (Dp * w_p), "cad_20mm_edge": R_pis_e / (Dp * w_p)},
    }


def allowable_lateral(g, p, e, P, pad, sy_rod, sf):
    """Largest lateral force with SF_rod_yield >= sf. sigma_rod is affine in F for a fixed P:
    sigma(F) = sigma(0) + F * (sigma(1 N) - sigma(0))."""
    s0 = leg_case(g, p, e, 0.0, P, pad, sy_rod)["sigma_rod_Pa"]
    s1 = leg_case(g, p, e, 1.0, P, pad, sy_rod)["sigma_rod_Pa"]
    return max(0.0, (sy_rod / sf - s0) / (s1 - s0))


def allowable_lateral_guide(g, p, e, pad, p_allow, which="piston"):
    c = leg_case(g, p, e, 1.0, 0.0, pad, 305e6)
    if which == "piston":
        per_N = c["p_piston_N_per_m2"]["cad_20mm_centre"]
    else:
        per_N = c["p_gland_N_per_m2"]["band_40mm_centre"]
    return p_allow / per_N


# ---------------------------------------------------------------------------
# 5. Dynamics matrix (pad_tangential_check.json, dynamics_model.md rev. 18 3.10)
# ---------------------------------------------------------------------------
ENV_GROUPS = {"yaml": ("main", "robust_d0", "robust_seed"), "ext": ("ktext",)}
MODE_LABEL = {"ext": "secant k_t(e) (best estimate)", "yaml": "YAML k_t (upper bound)"}
DIRS = {"pitch+": (0.0, 1.0), "pitch-": (0.0, -1.0), "roll+": (1.0, 0.0), "roll-": (-1.0, 0.0)}


def dir_slope(direction: str, rng: str) -> str:
    Phi, Th = RANGES[rng]
    return f"{rng}:pitch{direction[-1]}{Th}" if direction.startswith("pitch") else f"{rng}:roll{direction[-1]}{Phi}"


def slope_angles(slope: str):
    """'V:r+p-0.5' -> (range, roll deg, pitch deg); marker points on |phi|/Phi + |theta|/Theta = 1."""
    rng, name = slope.split(":")
    Phi, Th = RANGES[rng]
    if name.startswith("pitch"):
        return rng, 0.0, float(name[5:])
    if name.startswith("roll"):
        return rng, float(name[4:]), 0.0
    rs = 1.0 if name[1] == "+" else -1.0
    ps = 1.0 if name[3] == "+" else -1.0
    s = float(name[4:])
    return rng, rs * Phi * s, ps * Th * (1.0 - s)


def envelope(ptc: dict, groups, kt_mode: str, mu: float, gainset: str | None = None) -> dict:
    """Per slope and leg: max over runs of the levelling-end and dynamic-max pad tangential force [kN] with the
    concurrent leg-axis contact force [kN], the auger level and run id of the max."""
    env = {}
    for g in groups:
        for r in ptc[g]["runs"]:
            if r["kt_mode"] != kt_mode or abs(float(r["mu_pad"]) - mu) > 1e-9 or float(r.get("Fs_kN", 0.0)) != 0.0:
                continue
            if gainset is not None and r["gainset"] != gainset:
                continue
            t = r["tang"]
            ent = env.setdefault(r["slope"], {"ready": [None] * 4, "dyn": [None] * 4, "n_runs": 0})
            ent["n_runs"] += 1
            for i in range(4):
                for key, F, Fl in (("ready", t["ready"]["Ft_kN"][i], t["ready"]["Fl_kN"][i]),
                                   ("dyn", t["dyn_max_kN"][i], t["dyn_max_Fl_kN"][i])):
                    cur = ent[key][i]
                    if cur is None or F > cur["F_kN"]:
                        ent[key][i] = {"F_kN": float(F), "axial_kN": float(Fl), "level": r["level"], "run": r["id"]}
    return env


def compare_with_report(env: dict, rep: dict) -> float:
    """Largest |own envelope - dynamics report max| [kN] over slopes, legs, ready/dyn."""
    worst = 0.0
    for key in ("ready", "dyn"):
        for slope, v in rep.get(key, {}).items():
            if slope not in env:
                continue
            own = [x["F_kN"] for x in env[slope][key]]
            worst = max(worst, float(np.max(np.abs(np.array(own) - np.array(v["max_kN"])))))
    return worst


# ---------------------------------------------------------------------------
def load_h4_pairs(paths, mode_token: str = "base", sensitivity: bool = False) -> dict:
    """H4 re-anchoring runs of control-expert (runs[].x.step_pairs). Selects ids whose 2nd token is mode_token:
      O|base|V:pitch-3.5|rigid|yaml|Fs0|0        (s6r17 part O, rigid mast, F_s 0 only)
      O|R6|V:pitch-3.5|rigid|yaml|Fs0|0          (h4_fs_order_check_O3)
      S|R6|seed12346|P:pitch-3.2|stiff|yaml|Fs0|top  (h4_fs_order_check_S, sensitivity set: all variants kept)
    Returns {(direction, range, kt_mode): [run summary, ...]} with the per-step (tangential, axial) pairs [kN]."""
    out = {}
    for path in paths:
        d = json.load(open(path, encoding="utf-8"))
        for r in d["runs"]:
            parts = r["id"].split("|")
            if len(parts) < 6 or parts[1] != mode_token:
                continue
            js = next((j for j, s in enumerate(parts) if ":" in s), None)
            if js is None or js + 2 >= len(parts):
                continue
            is_sens = parts[0] in ("S", "N")  # sensitivity bundles (N: nose-down bundle with series, rev. 3.4)
            if not is_sens and (parts[js + 1] != "rigid" or float(r.get("Fs_kN", 0.0)) != 0.0):
                continue
            if is_sens and not sensitivity:
                continue
            rng, name = parts[js].split(":")
            kt_mode = parts[js + 2]
            if not name.startswith("pitch"):
                continue
            direction = "pitch" + name[5]
            a_run = abs(float(name[5:]))
            x = r["x"]
            pairs = [[] for _ in range(4)]  # per leg: (Ft, Fl, tag)
            series = [[] for _ in range(4)]  # rev. 3.4: 20 ms samples (Ft, Fl, tag) of the step series
            for sp in x["step_pairs"]:
                for i in range(4):
                    for ft_key, fl_key, tag in (("Ft_at_Fl_max_kN", "Fl_max_kN", "Fl_max"),
                                                ("Ft_max_kN", "Fl_at_Ft_max_kN", "Ft_max"),
                                                ("Ft_max_kN", "Fl_max_Ft_held_kN", "Fl_max_Ft_held"),
                                                ("Ft_at_Fl_max_Ft_held_kN", "Fl_max_Ft_held_kN",
                                                 "Fl_max_Ft_held_exact")):
                        if ft_key not in sp or fl_key not in sp:
                            continue
                        ft, fl = sp[ft_key][i], sp[fl_key][i]
                        if ft is None or fl is None:
                            continue
                        pairs[i].append((float(ft), float(fl), f"k{sp['k']}:{tag}"))
                ser = sp.get("series_20ms")
                if ser:
                    for t, fl_row, ft_row in zip(ser["t_s"], ser["Fl_kN"], ser["Ft_kN"]):
                        for i in range(4):
                            series[i].append((float(ft_row[i]), float(fl_row[i]), f"k{sp['k']}:series@{t:.3f}"))
            # the allowable lateral force falls monotonically with the axial force, and every Ft of a run is carried
            # by the same factor, so only the Pareto front (no sample with both larger Ft and larger Fl) can govern
            for i in range(4):
                front, best_fl = [], -1e9
                for ft, fl, tag in sorted(series[i], key=lambda s: (-s[0], -s[1])):
                    if fl > best_fl:
                        front.append((ft, fl, tag))
                        best_fl = fl
                pairs[i].extend(front)
            out.setdefault((direction, rng, kt_mode), []).append({
                "id": r["id"], "source": str(path), "angle_deg": a_run, "Ft_start_kN": x["Ft_start_kN"],
                "Fl_start_kN": x["Fl_start_kN"], "Ft_final_kN": x["Ft_final_kN"], "pairs": pairs,
                "min_true_cyl_kN": r["min_true_cyl_force_kN"], "P_stop_spec_kN": x.get("P_stop_spec_kN"),
                "P_stop_reading_kN": [s.get("P_stop_reading_kN") for s in x["steps"]]})
    return out


def main():
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h4-pairs", type=Path, default=None,
                    help="control-expert H4 run JSON, ids O|base|* (rev. 3.2 set 'A'); same as --h4-set A base FILE")
    ap.add_argument("--h4-set", nargs="+", action="append", default=[], metavar="ARG",
                    help="LABEL MODE_TOKEN FILE [FILE ...]: one H4 set; ids '<O|S>|MODE_TOKEN|...'; S|* ids "
                         "(sensitivity bundle) are kept as extra runs and the worst governs (rev. 3.3)")
    ap.add_argument("--h4-check-deg", type=float, nargs="*", default=[3.1, 3.2],
                    help="fore-aft angles [deg] at which the margins of the judgement pairs are reported")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="write leg_rod_lateral_check.json / .png here instead of the project legs folder "
                         "(sensitivity runs, e.g. modified H4 inputs); default unchanged")
    args = ap.parse_args()
    if args.out_dir is not None:
        global OUT_JSON, OUT_PNG
        args.out_dir.mkdir(parents=True, exist_ok=True)
        OUT_JSON = args.out_dir / OUT_JSON.name
        OUT_PNG = args.out_dir / OUT_PNG.name
    h4_sets = []
    if args.h4_pairs is not None:
        h4_sets.append(("A", "base", [args.h4_pairs]))
    for s in args.h4_set:
        if len(s) < 3:
            ap.error("--h4-set needs LABEL MODE_TOKEN FILE [FILE ...]")
        h4_sets.append((s[0], s[1], [Path(x) for x in s[2:]]))
    t0 = time.time()
    p = load_params()
    geo = leg_geometry(p)
    print(f"[{time.time() - t0:6.1f} s] geometry", flush=True)
    chk = convexity_and_volume()
    print(f"[{time.time() - t0:6.1f} s] convexity / volume", flush=True)
    ptc = json.load(open(PTC_JSON, encoding="utf-8"))
    mu = float(p["contact"]["rigid_floor"]["friction"])
    L1 = p["contact"]["rigid_floor"]["L1"]
    kt_yaml = np.array([float(L1["kt_per_pad_N_m"][n]) for n in LEG_NAMES])
    k_lat_yaml = np.array([float(L1["derivation"]["k_lateral_leg_swivel_N_m"][n]) for n in LEG_NAMES])
    k_conc = 1.0 / (1.0 / kt_yaml - 1.0 / k_lat_yaml)  # concrete tangential k in series (derived, same as YAML)
    g0 = float(p["meta"]["gravity_m_s2"])
    per_leg = per_leg_cylinders(p)
    # rev. 3: rod weight per leg (REXOME35 rear moving part differs); the old script used the FL value for every leg
    W_rod = np.array([float(p["legs"][n]["moving_part"]["mass_kg"]) * g0 for n in LEG_NAMES]) if per_leg \
        else float(p["legs"]["FL"]["moving_part"]["mass_kg"]) * g0
    if per_leg:
        # rev. 3: static cylinder forces of the L1 k_n distribution (dyn_model.static_loads, superstructure top + rods
        # at e_op), as dynamics order R; the YAML static_leg_loads_N are the equal-spring values
        Ncyl, static_basis = static_cylinder_forces_kn(p), "L1 kn distribution (dyn_model.static_loads, top, e_op)"
    else:
        Ncyl = np.array([float(p["superstructure"]["auger_levels"]["top"]["static_leg_loads_N"][n]) for n in LEG_NAMES])
        static_basis = "YAML superstructure.auger_levels.top.static_leg_loads_N (4 equal springs)"
    Npad = Ncyl + W_rod
    sy_list = ASSUMPTIONS["rod_yield_Pa"]
    SF_req = ASSUMPTIONS["required_yield_safety_factor"]
    P_lock_leg = {leg: geo[leg]["P_lock_N"] for leg in LEG_NAMES}  # rev. 3: 350 bar x head area per leg
    P_lock = max(P_lock_leg.values())
    P_dyn = ASSUMPTIONS["dynamic_peak_axial_N"]
    stroke = float(p["actuator"]["stroke_m"])

    # --- checks against the YAML and the dynamics document ---
    table = {(0, 0): [0.4011, 0.4011, 0.3909, 0.3909], (0, 1): [0.4733, 0.4733, 0.3784, 0.3784],
             (2, 0): [0.4026, 0.4950, 0.3978, 0.4820], (0, 2): [0.5455, 0.5455, 0.3659, 0.3659],
             (-2, 1.5): [0.6033, 0.5108, 0.4606, 0.3764]}
    lev_check = {f"roll {k[0]}, pitch {k[1]}": {"computed_m": levelling_extension(p, *k).round(4).tolist(), "doc_m": v,
                                               "max_abs_diff_m": float(np.max(np.abs(levelling_extension(p, *k) - np.array(v))))}
                 for k, v in table.items()}
    klat_chk = {}
    for leg in LEG_NAMES:
        e_op = float(L1["derivation"]["operating_extension_m"][leg])
        k = leg_case(geo[leg], p, e_op, 1.0, 0.0, "swivel", 305e6)["k_lat_bending_N_m"]
        ky = float(L1["derivation"]["k_lateral_leg_swivel_N_m"][leg])
        klat_chk[leg] = {"fe_N_m": k, "yaml_N_m": ky, "rel_diff": k / ky - 1.0}

    def kt_of(mode: str, e: np.ndarray) -> np.ndarray:
        if mode == "yaml":
            return kt_yaml.copy()
        kb = np.array([leg_case(geo[leg], p, float(e[i]), 1.0, 0.0, "swivel", 305e6)["k_lat_bending_N_m"]
                       for i, leg in enumerate(LEG_NAMES)])
        return 1.0 / (1.0 / kb + 1.0 / k_conc)

    # secant k_t vs the dynamics run (checks.kt_ext_N_m) at the same slopes
    kt_sec_chk = {}
    for slope, v in ptc["checks"]["kt_ext_N_m"].items():
        _, ph, th = slope_angles(slope)
        own = kt_of("ext", levelling_extension(p, ph, th))
        kt_sec_chk[slope] = {"own_N_m": own.round(0).tolist(), "dynamics_N_m": v,
                             "max_rel_diff": float(np.max(np.abs(own / np.array(v) - 1.0)))}
    lev_vs_kin = {}
    for key, v in ptc["kin"].items():
        if not key.startswith("top|") or key == "note":
            continue
        slope = key.split("|", 1)[1]
        if ":" not in slope:
            continue
        _, ph, th = slope_angles(slope)
        lev_vs_kin[slope] = float(np.max(np.abs(levelling_extension(p, ph, th) - np.array(v["yaml"]["levelled_ext_m"]))))
    print(f"[{time.time() - t0:6.1f} s] checks", flush=True)

    # --- dynamics envelopes (mu 0.5) and stick demand (mu 5) ---
    # rev. 3: rescale the closed-loop envelopes when pad_tangential_check.json was run with another k_t (see PTC_*)
    kt_ptc = np.array(ptc["meta"]["kt_yaml_N_m"], float)
    rescale = bool(np.max(np.abs(kt_ptc / kt_yaml - 1.0)) > PTC_KT_REL_TOL)
    geo_ptc = {leg: dict(geo[leg], dims=PTC_CYLINDERS_M) for leg in LEG_NAMES}
    scale_log, scale_cache = {}, {}

    def raw_kin(mode: str, ph: float, th: float, g_: dict, kty: np.ndarray) -> np.ndarray:
        e = levelling_extension(p, ph, th)
        if mode == "yaml":
            kt = kty
        else:
            kb = np.array([leg_case(g_[leg], p, float(e[i]), 1.0, 0.0, "swivel", 305e6)["k_lat_bending_N_m"]
                           for i, leg in enumerate(LEG_NAMES)])
            kt = 1.0 / (1.0 / kb + 1.0 / k_conc)
        return np.linalg.norm(anchored_internal_force(p, ph, th, kt), axis=1)

    def slope_to_angles(slope: str):
        if ":" in slope:
            _, ph, th = slope_angles(slope)
            return ph, th
        return (0.0, float(slope[5:])) if slope.startswith("pitch") else (float(slope[4:]), 0.0)  # 'pitch+3.7' runs

    def scaled(env_m: dict, mode: str, mu_run: float) -> dict:
        if not rescale:
            return env_m
        out_m = json.loads(json.dumps(env_m))
        for slope, ent in out_m.items():
            if (slope, mode) not in scale_cache:
                ph, th = slope_to_angles(slope)
                r_old = raw_kin(mode, ph, th, geo_ptc, kt_ptc)
                r_new = raw_kin(mode, ph, th, geo, kt_yaml)
                s = np.where(r_old > 1e-6, r_new / np.maximum(r_old, 1e-6), 1.0)
                nz = math.cos(math.radians(ph)) * math.cos(math.radians(th))
                scale_cache[(slope, mode)] = (s, mu * Npad * nz)
                scale_log[f"{slope}|{mode}"] = s.round(4).tolist()
            s, cap = scale_cache[(slope, mode)]
            for key in ("ready", "dyn"):
                for i in range(4):
                    x = ent[key][i]
                    if x is None:
                        continue
                    F = x["F_kN"] * float(s[i])
                    x["F_kN"] = float(min(F, cap[i] / 1e3) if mu_run < 1.0 else F)
        return out_m

    env_raw = {m: envelope(ptc, ENV_GROUPS[m], m, mu) for m in ("ext", "yaml")}
    env = {m: scaled(env_raw[m], m, mu) for m in ("ext", "yaml")}
    env_stick = {m: scaled(envelope(ptc, ("stick",), m, 5.0), m, 5.0) for m in ("ext", "yaml")}
    env_stick_raw = {m: envelope(ptc, ("stick",), m, 5.0) for m in ("ext", "yaml")}
    rep_diff = {}  # envelope extraction vs the dynamics report (unscaled)
    for rk, rep in ptc["report"].items():
        if rk not in ("verification_5.5_3.5", "provisional_4.4_3.2"):
            continue
        rep_diff[rk] = {"yaml": compare_with_report(env_raw["yaml"], rep["kt_yaml_all"]),
                        "ext": compare_with_report(env_raw["ext"], rep["kt_ext"])}
        if "stick_mu5" in rep:
            rep_diff[rk]["stick_yaml_vs_report_stick_mu5"] = compare_with_report(env_stick_raw["yaml"], rep["stick_mu5"])

    def ext_of(level: str, slope: str, mode: str) -> list:
        k = ptc["kin"].get(f"{level}|{slope}") or ptc["kin"][f"top|{slope}"]
        return k.get(mode, k["yaml"])["levelled_ext_m"]

    # --- structural check at every simulated boundary point, per leg, both k_t models ---
    def check(leg: str, e: float, F: float, P: float) -> dict:
        out = {}
        for mat, sy in sy_list.items():
            c = leg_case(geo[leg], p, e, F, P, "swivel", sy)
            out[f"SF_rod_{mat}"] = c["SF_rod_yield"]
            out[f"SF_buckling_sway_{mat}"] = c["SF_buckling_sway"]
            out[f"SF_rod_lock364kN_{mat}"] = leg_case(geo[leg], p, e, F, P_lock_leg[leg], "swivel", sy)["SF_rod_yield"]
        out.update({"sigma_rod_MPa": c["sigma_rod_Pa"] / 1e6, "SF_barrel": c["SF_barrel_yield"],
                    "SF_neck_C45": sy_list["C45_normalised"] / c["sigma_neck_Pa"],
                    "R_gland_kN": c["R_gland_centre_N"] / 1e3, "R_piston_kN": c["R_piston_centre_N"] / 1e3,
                    "p_piston_20mm_MPa": c["p_piston_N_per_m2"]["cad_20mm_centre"] / 1e6,
                    "p_piston_20mm_edge_MPa": c["p_piston_N_per_m2"]["cad_20mm_edge"] / 1e6,
                    "p_gland_40mm_MPa": c["p_gland_N_per_m2"]["band_40mm_centre"] / 1e6,
                    "M_bracket_kNm": c["M_bracket_bolt_centre_Nm"] / 1e3})
        return out

    points = []
    for mode in ("ext", "yaml"):
        for slope, ent in env[mode].items():
            rng, ph, th = slope_angles(slope)
            for i, leg in enumerate(LEG_NAMES):
                d = ent["dyn"][i]
                rdy = ent["ready"][i]
                e = float(ext_of(d["level"], slope, mode)[i])
                row = {"range": rng, "slope": slope, "roll_deg": round(ph, 4), "pitch_deg": round(th, 4), "kt_mode": mode,
                       "leg": leg, "extension_m": e, "F_ready_kN": rdy["F_kN"], "F_dyn_kN": d["F_kN"],
                       "axial_at_dyn_kN": d["axial_kN"], "level": d["level"], "run": d["run"],
                       "n_runs": ent["n_runs"]}
                row.update(check(leg, e, d["F_kN"] * 1e3, d["axial_kN"] * 1e3))
                points.append(row)
    print(f"[{time.time() - t0:6.1f} s] boundary points ({len(points)})", flush=True)

    per_leg_max, boundary_min = {}, {}
    for rng in RANGES:
        for mode in ("ext", "yaml"):
            rows = [r for r in points if r["range"] == rng and r["kt_mode"] == mode]
            per_leg_max.setdefault(rng, {})[mode] = {
                leg: min([r for r in rows if r["leg"] == leg], key=lambda r: r["SF_rod_C45_normalised"]) for leg in LEG_NAMES}
            boundary_min.setdefault(rng, {})[mode] = {
                mat: {k: v for k, v in min(rows, key=lambda r: r[f"SF_rod_{mat}"]).items()
                      if k in ("slope", "leg", "extension_m", "F_dyn_kN", "axial_at_dyn_kN", f"SF_rod_{mat}", "sigma_rod_MPa")}
                for mat in sy_list}

    # pitch +3.7 deg (old basis), R:BS_hold, top: clipped vs stick vs secant
    clip37 = {}
    for mode in ("yaml", "ext"):
        for m_mu in (0.5, 5.0):
            e_ = scaled(envelope(ptc, ("clip",), mode, m_mu, gainset="R:BS_hold"), mode, m_mu).get("pitch+3.7")
            if not e_:
                continue
            ext37 = ptc["kin"]["top|pitch+3.7"][mode]["levelled_ext_m"]
            d = e_["dyn"][0]
            rr = {"F_ready_kN": [x["F_kN"] for x in e_["ready"]], "F_dyn_kN": [x["F_kN"] for x in e_["dyn"]],
                  "FL_extension_m": ext37[0]}
            rr.update({f"FL_{k}": v for k, v in check("FL", float(ext37[0]), d["F_kN"] * 1e3, d["axial_kN"] * 1e3).items()
                       if k.startswith("SF_rod_") or k == "sigma_rod_MPa"})
            clip37[f"{mode}|mu{m_mu}"] = rr

    # --- continuous model for the limits: anchored-pad kinematics, per-leg scaled to the provisional vertex ---
    def model_raw(mode: str, ph: float, th: float):
        e = levelling_extension(p, ph, th)
        f = anchored_internal_force(p, ph, th, kt_of(mode, e))
        return np.linalg.norm(f, axis=1), e

    def mu_cap(direction: str, ph: float, th: float) -> np.ndarray:
        nz = math.cos(math.radians(ph)) * math.cos(math.radians(th))
        cap = mu * Npad * nz
        if direction.startswith("pitch"):  # front pair balanced by the rear pair (sum F_t = 0)
            rear = (2, 3)
            cap = np.full(4, min(cap[j] for j in rear))
        return cap

    cal, model_check = {}, {}
    for direction, (sp, st) in DIRS.items():
        for mode in ("ext", "yaml"):
            sP = dir_slope(direction, "P")
            _, ph, th = slope_angles(sP)
            raw, _ = model_raw(mode, ph, th)
            sim = np.array([x["F_kN"] for x in env[mode][sP]["dyn"]]) * 1e3
            c = sim / raw
            cal[(direction, mode)] = c
            sV = dir_slope(direction, "V")
            _, phv, thv = slope_angles(sV)
            rawV, _ = model_raw(mode, phv, thv)
            mV = c * rawV
            mVc = np.minimum(mV, mu_cap(direction, phv, thv))
            simV = np.array([x["F_kN"] for x in env[mode][sV]["dyn"]]) * 1e3
            stickV = np.array([x["F_kN"] for x in env_stick[mode][sV]["ready"]]) * 1e3 if sV in env_stick[mode] else None
            model_check[f"{direction}|{mode}"] = {
                "scale_per_leg": c.round(4).tolist(),
                "V_model_capped_kN": (mVc / 1e3).round(2).tolist(), "V_sim_dyn_kN": (simV / 1e3).round(2).tolist(),
                "V_capped_max_rel_diff": float(np.max(np.abs(mVc / simV - 1.0))),
                "V_model_stick_kN": (mV / 1e3).round(2).tolist(),
                "V_sim_stick_mu5_ready_kN": None if stickV is None else (stickV / 1e3).round(2).tolist(),
                "V_stick_max_rel_diff": None if stickV is None else float(np.max(np.abs(mV / stickV - 1.0)))}

    def model_force(direction: str, mode: str, a: float, capped: bool = True):
        sp, st = DIRS[direction]
        ph, th = sp * a, st * a
        raw, e = model_raw(mode, ph, th)
        F = cal[(direction, mode)] * raw
        if capped:
            F = np.minimum(F, mu_cap(direction, ph, th))
        return F, e

    # --- re-anchoring manoeuvre (3.10.7), proposed motion: twist, 0.1 v_max, stepped P_stop ---
    ra_rep = ptc["report"].get("reanchor", {})
    ra_runs = {r["id"]: r for g in ("reanchor", "reanchor2", "reanchor3") for r in ptc.get(g, {}).get("runs", [])}
    RA_IDS = {
        ("pitch+", "V", "yaml"): "ra3|twist|V:pitch+3.5|rigid|yaml|v0.1|stair",
        ("pitch+", "V", "ext"): "ra3|twist|V:pitch+3.5|rigid|ext|v0.1|stair",
        ("pitch-", "V", "yaml"): "ra3|twist|V:pitch-3.5|rigid|yaml|v0.1|stair",
        ("pitch-", "V", "ext"): "ra3|twist|V:pitch-3.5|rigid|ext|v0.1|stair",
        ("pitch-", "P", "yaml"): "ra3|twist|P:pitch-3.2|rigid|yaml|v0.1|stair",
        ("pitch-", "P", "ext"): "ra3|twist|P:pitch-3.2|rigid|ext|v0.1|stair",
        ("pitch+", "P", "yaml"): "ra2|twist|P:pitch+3.2|rigid|yaml|v0.1|Pstop20",
        ("roll+", "V", "yaml"): "ra3|twist|V:roll+5.5|rigid|yaml|v0.1|stair",
        ("roll+", "V", "ext"): "ra3|twist|V:roll+5.5|rigid|ext|v0.1|stair",
        ("roll-", "V", "yaml"): "ra3|twist|V:roll-5.5|rigid|yaml|v0.1|stair",
        ("roll-", "V", "ext"): "ra3|twist|V:roll-5.5|rigid|ext|v0.1|stair",
        ("roll+", "P", "yaml"): "ra2|twist|P:roll+4.4|rigid|yaml|v0.1|Pstop20",
    }
    reanchor = []
    ra_factor = {}
    for (direction, rng, mode), rid in RA_IDS.items():
        if rid not in ra_rep or rid not in ra_runs:
            continue
        s = ra_rep[rid]
        run = ra_runs[rid]
        slope = run["slope"]
        e = ext_of(run["level"], slope, mode)
        F0 = np.array(s["Ft0_kN"]); Ff = np.array(s["Ft_final_kN"])
        # peak over the whole run (levelling + manoeuvre) with the concurrent leg-axis force (same pairing as the
        # main envelope); Ft_max_during_kN of the report is the manoeuvre-only max and is kept for the table
        Fm = np.maximum(np.array(run["tang"]["dyn_max_kN"]), np.array(s["Ft_max_during_kN"]))
        Flmax = np.array(run["tang"]["dyn_max_Fl_kN"])
        rows = []
        for i, leg in enumerate(LEG_NAMES):
            peak = check(leg, float(e[i]), float(Fm[i]) * 1e3, float(max(Flmax[i], Npad[i] / 1e3)) * 1e3)
            sus = check(leg, float(e[i]), float(Ff[i]) * 1e3, float(Npad[i]))
            sus_lock = {mat: sus[f"SF_rod_lock364kN_{mat}"] for mat in sy_list}
            rows.append({"leg": leg, "extension_m": float(e[i]), "F_start_kN": float(F0[i]), "F_final_kN": float(Ff[i]),
                         "F_max_manoeuvre_kN": float(s["Ft_max_during_kN"][i]),
                         "F_peak_run_kN": float(Fm[i]), "axial_at_peak_kN": float(Flmax[i]),
                         "peak_SF_rod": {mat: peak[f"SF_rod_{mat}"] for mat in sy_list},
                         "final_SF_rod_static": {mat: sus[f"SF_rod_{mat}"] for mat in sy_list},
                         "final_SF_rod_lock364kN": sus_lock,
                         "final_p_piston_20mm_MPa": sus["p_piston_20mm_MPa"]})
        reanchor.append({"direction": direction, "range": rng, "kt_mode": mode, "run": rid, "slope": slope,
                         "min_true_cyl_kN": s.get("min_true_cyl_kN"), "legs": rows})
        if rng == "V":
            # manoeuvre increase over the levelling-end value (the model force is already the dynamic envelope);
            # axial: concurrent value when the run peak falls in the manoeuvre ('levelled' phase), else static
            in_man = np.array([ph == "levelled" for ph in run["tang"]["dyn_max_phase"]])
            ra_factor[(direction, mode)] = {"peak_over_start": np.maximum(np.array(s["Ft_max_during_kN"]) / F0, 1.0),
                                            "residual_N": Ff * 1e3,
                                            "axial_max_N": np.where(in_man, np.maximum(Flmax * 1e3, Npad), Npad)}
    print(f"[{time.time() - t0:6.1f} s] reanchor ({len(reanchor)} runs)", flush=True)

    # --- allowable lateral force per leg as a function of extension (cached by e) ---
    @functools.lru_cache(maxsize=None)
    def F_allow(leg: str, e: float, P: float, mat: str, sf: float) -> float:
        return allowable_lateral(geo[leg], p, e, P, "swivel", sy_list[mat], sf)

    @functools.lru_cache(maxsize=None)
    def F_allow_piston(leg: str, e: float, p_allow: float) -> float:
        return allowable_lateral_guide(geo[leg], p, e, "swivel", p_allow, "piston")

    angles = np.round(np.arange(0.5, 7.001, 0.02), 4)
    scan_cache = {}

    def scan(direction, mode, capped=True):
        key = (direction, mode, capped)
        if key not in scan_cache:
            scan_cache[key] = [(float(a),) + model_force(direction, mode, float(a), capped) for a in angles]
        return scan_cache[key]

    def first_fail(direction, mode, ok_fn, capped=True) -> dict:
        """Largest angle (contiguous from 0.5 deg) with every leg passing; stops at the stroke end."""
        best = 0.0
        for a, F, e in scan(direction, mode, capped):
            if float(np.max(e)) > stroke:
                return {"deg": best, "by": "stroke"}
            if all(ok_fn(i, leg, round(float(e[i]), 5), F[i]) for i, leg in enumerate(LEG_NAMES)):
                best = a
            else:
                return {"deg": best, "by": "criterion"}
        return {"deg": best, "by": "scan_end"}

    SF_lock = ASSUMPTIONS["lock_check_SF"]
    SF_peak_B = ASSUMPTIONS["criterion_B_peak_SF"]
    limits = []
    for direction in DIRS:
        for mode in ("ext", "yaml"):
            variants = [("capped", True)] + ([("stick", False)] if mode == "yaml" else [])
            for vname, capped in variants:
                row = {"direction": direction, "kt_mode": mode, "variant": vname,
                       "stroke_deg": first_fail(direction, mode, lambda *a: True, capped)["deg"]}
                for mat in sy_list:
                    # A: peak lateral (levelling end / dynamic max) with the static axial force, SF >= 1.5
                    row[f"A_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: F <= F_allow(leg, e, float(Npad[i]), m, SF_req), capped)
                    # A with the dynamic peak axial force 141 kN on every leg (sensitivity)
                    row[f"A_Pdyn141_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: F <= F_allow(leg, e, max(P_dyn, float(Npad[i])), m, SF_req), capped)
                    # L: the same lateral force sustained while the locked cylinder reaches 350 bar (364 kN), no yield
                    row[f"L_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: F <= F_allow(leg, e, P_lock_leg[leg], m, SF_lock), capped)
                    row[f"AL_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: F <= F_allow(leg, e, float(Npad[i]), m, SF_req) and F <= F_allow(leg, e, P_lock_leg[leg], m, SF_lock), capped)
                    rf = ra_factor.get((direction, mode))
                    if rf is not None and direction.startswith("pitch"):
                        def peak_ok(i, leg, e, F, m, sf, rf=rf):
                            return F * rf["peak_over_start"][i] <= F_allow(leg, e, float(rf["axial_max_N"][i]), m, sf)

                        def sustained_ok(i, leg, e, m, rf=rf):
                            Fr = float(rf["residual_N"][i])
                            return Fr <= F_allow(leg, e, float(Npad[i]), m, SF_req) and Fr <= F_allow(leg, e, P_lock_leg[leg], m, SF_lock)
                        # RA_A: with re-anchoring, the levelling-end peak (x manoeuvre factor) still has to meet SF 1.5
                        row[f"RA_A_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: peak_ok(i, leg, e, F, m, SF_req) and sustained_ok(i, leg, e, m), capped)
                        # RA_B (option): one-off peak SF >= 1.0, sustained residual SF >= 1.5 (static) and no yield at 364 kN
                        row[f"RA_B_{mat}"] = first_fail(direction, mode, lambda i, leg, e, F, m=mat: peak_ok(i, leg, e, F, m, SF_peak_B) and sustained_ok(i, leg, e, m), capped)
                for nm, pa in (("piston40MPa", 40e6), ("piston100MPa", 100e6)):
                    row[f"guide_{nm}"] = first_fail(direction, mode, lambda i, leg, e, F, pa=pa: F <= F_allow_piston(leg, e, pa), capped)
                limits.append(row)
    print(f"[{time.time() - t0:6.1f} s] limits", flush=True)

    # --- rev. 3.2: adopted H4 (control-expert s6r17 part O, P_stop 45 / 32.41 / 32.41 / 32.41 kN) ---
    # Every (tangential, axial) pair of every re-anchoring step and the residual are checked at SF 1.5 (residual also
    # at the 350 bar lock, SF 1.0). Pair tangential forces are carried to another slope a with the scaled kinematics
    # ratio F_model(a) / F_start(run); above the run angle the ratio is floored at 1 (released pads keep their value).
    # The V (3.5 deg) and P (3.2 deg) runs are both used and the worse governs. Axial forces are taken as they are
    # (ASSUMPTION: the axial redistribution of the twist steps is set by P_stop, not by the slope).
    h4 = None
    h4_out = {}

    @functools.lru_cache(maxsize=None)
    def F_allow_q(leg: str, e: float, P_kN01: int, mat: str, sf: float) -> float:
        return allowable_lateral(geo[leg], p, e, P_kN01 * 100.0, "swivel", sy_list[mat], sf)

    for set_label, set_mode, set_files in h4_sets:
        h4_runs = load_h4_pairs(set_files, set_mode, sensitivity=True)

        def carry(F_run: float, F0: float, Fm: float, a: float, a_run: float, cmode: str = "ratio") -> float:
            """'ratio': x F_model(a)/F_start, floored at 1 above the run angle; 'hold': floored at 1 everywhere
            (no reduction below the run angle - conservative for angles under the run angle)."""
            r = Fm / max(F0 * 1e3, 1e-6)
            if cmode == "hold" or a >= a_run - 1e-9:
                r = max(1.0, r)
            return F_run * 1e3 * r

        # simultaneous pairs only (Ft at Fl max, Fl max), (Ft max, Fl at Ft max) = primary; the bound variant adds the
        # non-simultaneous (Ft max of the step, Fl max while the pad still holds) combination
        # '*_nofloor' (sensitivity): the recorded axial force without the static floor max(Fl, N_static)
        TAGS = {"simul": ("Fl_max", "Ft_max"), "bound": ("Fl_max", "Ft_max", "Fl_max_Ft_held"),
                "simul_nofloor": ("Fl_max", "Ft_max"), "bound_nofloor": ("Fl_max", "Ft_max", "Fl_max_Ft_held"),
                # rev. 3.4: exact simultaneous pairs incl. the held-axial-max instant and the 20 ms series front
                "exact": ("Fl_max", "Ft_max", "Fl_max_Ft_held_exact", "series"),
                "exact_nofloor": ("Fl_max", "Ft_max", "Fl_max_Ft_held_exact", "series")}

        def h4_ok(direction, mode, mat, i, leg, e, Fm, a, runs, detail=None, variant="simul", cmode="ratio"):
            floor = 0.0 if variant.endswith("_nofloor") else float(Npad[i])
            if cmode == "hold":
                # bracket: runs at or below a (ratio rule, floored at 1) and the runs of the nearest angle above a
                # with their tangential forces not reduced (internal force grows with the slope)
                above = [R["angle_deg"] for R in runs if R["angle_deg"] > a + 1e-9]
                a_ref = min(above) if above else None
                runs = [R for R in runs if R["angle_deg"] <= a + 1e-9 or (a_ref is not None
                                                                            and abs(R["angle_deg"] - a_ref) < 1e-9)]
            for R in runs:
                F0 = R["Ft_start_kN"][i]
                checks = [(carry(ft, F0, Fm, a, R["angle_deg"], cmode), max(fl * 1e3, floor), SF_req, tag)
                          for ft, fl, tag in R["pairs"][i] if tag.split(":")[1].split("@")[0] in TAGS[variant]]
                Fr = carry(R["Ft_final_kN"][i], F0, Fm, a, R["angle_deg"], cmode)
                checks += [(Fr, float(Npad[i]), SF_req, "residual"), (Fr, P_lock_leg[leg], SF_lock, "residual_lock")]
                for F, P, sf, tag in checks:
                    Fa = F_allow_q(leg, e, int(round(P / 100.0)), mat, sf)
                    if detail is not None:
                        detail.append({"run": R["id"], "tag": tag, "F_kN": F / 1e3, "axial_kN": P / 1e3, "SF_req": sf,
                                       "F_allow_kN": Fa / 1e3, "util": F / Fa if Fa > 0 else float("inf")})
                    if F > Fa and detail is None:
                        return False
            return True

        def h4_first_fail(direction, mode, mat, runs, variant="simul", cmode="ratio") -> dict:
            """As first_fail (contiguous from 0.5 deg, stops at the stroke end) for the H4 criterion."""
            best = 0.0
            for a, F, e in scan(direction, mode, True):
                if float(np.max(e)) > stroke:
                    return {"deg": best, "by": "stroke"}
                if all(h4_ok(direction, mode, mat, i, leg, round(float(e[i]), 5), float(F[i]), a, runs, None, variant,
                             cmode) for i, leg in enumerate(LEG_NAMES)):
                    best = a
                else:
                    return {"deg": best, "by": "criterion"}
            return {"deg": best, "by": "scan_end"}

        VARIANTS = {"H4": "simul", "H4bound": "bound", "H4nofloor": "simul_nofloor", "H4boundnofloor": "bound_nofloor",
                    "H4exact": "exact", "H4exactnofloor": "exact_nofloor"}
        h4_limits, h4_points, h4_margins = [], [], []
        for direction in ("pitch+", "pitch-"):
            for mode in ("ext", "yaml"):
                runs = [R for k in ((direction, "V", mode), (direction, "P", mode)) for R in h4_runs.get(k, [])]
                if not runs:
                    continue
                row = {"direction": direction, "kt_mode": mode, "runs": [R["id"] for R in runs]}
                base = next(r for r in limits if r["direction"] == direction and r["kt_mode"] == mode
                            and r["variant"] == "capped")
                for mat in sy_list:
                    al = base[f"AL_{mat}"]
                    for key, variant in VARIANTS.items():
                        for cmode in ("ratio", "hold"):
                            sfx = key if cmode == "ratio" else key + "hold"
                            ra = h4_first_fail(direction, mode, mat, runs, variant, cmode)
                            row[f"RA_A_{sfx}_{mat}"] = ra
                            row[f"ALR_{sfx}_{mat}"] = al if al["deg"] <= ra["deg"] else ra
                    old = base.get(f"RA_A_{mat}")
                    if old is not None:
                        row[f"ALR_reanchor3_{mat}"] = al if al["deg"] <= old["deg"] else old
                h4_limits.append(row)
                # margins at the requested angles: A and L from the envelope model, RA from every pair (all runs)
                for a in args.h4_check_deg:
                    F_m, e_m = model_force(direction, mode, float(a))
                    for mat in sy_list:
                        ent = {"direction": direction, "kt_mode": mode, "angle_deg": float(a), "material": mat,
                               "legs": {}}
                        for i, leg in enumerate(LEG_NAMES):
                            e_i = round(float(e_m[i]), 5)
                            c = check(leg, e_i, float(F_m[i]), float(Npad[i]))
                            L_ = {"SF_A": c[f"SF_rod_{mat}"], "SF_L": c[f"SF_rod_lock364kN_{mat}"],
                                  "F_model_kN": float(F_m[i]) / 1e3, "extension_m": e_i}
                            for variant in ("simul", "bound_nofloor", "simul_nofloor", "bound", "exact", "exact_nofloor"):
                                for cmode in ("ratio", "hold"):
                                    det = []
                                    h4_ok(direction, mode, mat, i, leg, e_i, float(F_m[i]), float(a), runs, det,
                                          variant, cmode)
                                    w = max(det, key=lambda x: x["util"])
                                    L_[f"RA_{variant}_{cmode}"] = {"SF_eff": w["SF_req"] / w["util"], "governing": w}
                            ent["legs"][leg] = L_
                        h4_margins.append(ent)
                # utilisation of every pair at the run angles (governing pair per leg), primary variants only
                for R in runs:
                    a = R["angle_deg"]
                    F_m, e_m = model_force(direction, mode, a)
                    for i, leg in enumerate(LEG_NAMES):
                        for mat in sy_list:
                            for variant in TAGS:
                                det = []
                                h4_ok(direction, mode, mat, i, leg, round(float(e_m[i]), 5), float(F_m[i]), a, [R], det,
                                      variant)
                                w = max(det, key=lambda x: x["util"])
                                h4_points.append({"direction": direction, "kt_mode": mode, "run": R["id"],
                                                  "angle_deg": a, "leg": leg, "material": mat, "variant": variant,
                                                  "extension_m": float(e_m[i]), "F_model_kN": float(F_m[i]) / 1e3,
                                                  "governing": w, "SF_governing": w["SF_req"] / w["util"]})
        h4_out[set_label] = {
            "mode_token": set_mode,
            "sources": [{"path": str(f), "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))}
                        for f in set_files],
            "note": "pairs = per step (Ft at Fl max, Fl max), (Ft max, Fl at Ft max) [variant simul = RA_A_H4]; bound "
                    "adds (Ft max, Fl max while Ft held) [not simultaneous]; *nofloor: recorded axial without the "
                    "static floor; carry 'ratio': Ft x F_model(a)/F_start, floored at 1 above the run angle; carry "
                    "'hold' (suffix 'hold'): floored at 1 at every angle (no reduction below the run angle); all V/P "
                    "runs of the set (S|* sensitivity runs included) are checked and the worst governs; axial "
                    "unchanged (ASSUMPTION); SF 1.5 for every pair and the residual, residual also SF 1.0 at the "
                    "350 bar lock",
            "runs": {R["id"]: {kk: v for kk, v in R.items() if kk != "pairs"} | {
                "pairs": [[list(t) for t in R["pairs"][i]] for i in range(4)]}
                for lst in h4_runs.values() for R in lst},
            "limits_deg": h4_limits, "margins_at_deg": h4_margins, "run_angle_check": h4_points}
        print(f"[{time.time() - t0:6.1f} s] H4 set {set_label} ({sum(len(v) for v in h4_runs.values())} runs)",
              flush=True)
    if h4_out:
        h4 = h4_out.get("A") or next(iter(h4_out.values()))

    # model curves for the figure (governing long leg per direction)
    gov = {"pitch+": 0, "pitch-": 2, "roll+": 1, "roll-": 0}
    curves_model = {}
    for direction, i in gov.items():
        for mode in ("ext", "yaml"):
            sc = scan(direction, mode)
            curves_model[f"{direction}|{mode}"] = {
                "leg": LEG_NAMES[i], "angle_deg": [s[0] for s in sc], "F_N": [float(s[1][i]) for s in sc],
                "extension_m": [float(s[2][i]) for s in sc],
                **{f"F_allow_{mat}_N": [F_allow(LEG_NAMES[i], round(float(s[2][i]), 5), float(Npad[i]), mat, SF_req) for s in sc]
                   for mat in sy_list}}

    # allowable lateral force vs. extension (front and rear geometry)
    ee = np.linspace(0.0, stroke, 35)  # rev. 3: actuator.stroke_m (was 0.68)
    curves = {}
    for leg, P in (("FL", Npad[0]), ("RL", Npad[2])):
        cv = {"extension_m": ee.tolist(), "axial_N": float(P)}
        for mat, sy in sy_list.items():
            cv[f"F_allow_rod_SF1.5_{mat}_N"] = [allowable_lateral(geo[leg], p, float(x), float(P), "swivel", sy, 1.5) for x in ee]
        cv["F_allow_rod_SF1.5_C45_Pdyn_N"] = [allowable_lateral(geo[leg], p, float(x), P_dyn, "swivel", 305e6, 1.5) for x in ee]
        for nm, pa in ASSUMPTIONS["guide_allowable_pressure_Pa"].items():
            cv[f"F_allow_piston_{nm}_N"] = [allowable_lateral_guide(geo[leg], p, float(x), "swivel", pa, "piston") for x in ee]
            cv[f"F_allow_gland40_{nm}_N"] = [allowable_lateral_guide(geo[leg], p, float(x), "swivel", pa, "gland") for x in ee]
        curves[leg] = cv
    print(f"[{time.time() - t0:6.1f} s] curves", flush=True)

    # rev. 3.1 (2026-10-22): 'd8_boundary_scan' compatibility list for run_pad_tangential_check.py figures() (rev. 1 key,
    # dropped in rev. 2). Each entry = continuous CAD model (anchored-pad kinematics, per-leg calibrated to the
    # provisional vertex, mu N cap), YAML k_t, at the axis vertices of both ranges. At the P vertices it equals the
    # simulated envelope by construction; at the V vertices it is the model extrapolation (model_calibration_check).
    # Diagonal vertices are not covered (the model is calibrated per axis direction only).
    d8_scan = []
    for rng in RANGES:
        for direction, (sp, st) in DIRS.items():
            Phi, Th = RANGES[rng]
            a = Th if direction.startswith("pitch") else Phi
            F, e = model_force(direction, "yaml", float(a), capped=True)
            d8_scan.append({"range": rng, "direction": direction, "phi_deg": sp * a, "theta_deg": st * a,
                            "kt_mode": "yaml", "F_design_kN": (np.asarray(F) / 1e3).round(3).tolist(),
                            "extension_m": np.asarray(e).round(5).tolist()})

    out = {
        "meta": {"script": "04_scripts/00_cad/leg_rod_lateral_check.py", "revision": 3, "date": time.strftime("%Y-%m-%d"),
                 "d8_boundary_scan_note": "rev. 3.1 compatibility key for run_pad_tangential_check.py figures(): "
                                          "CAD continuous model (anchored kinematics calibrated per leg at the P axis "
                                          "vertex, mu N capped), YAML k_t, axis vertices of V and P only; phi = roll, "
                                          "theta = pitch [deg]; F_design_kN per leg FL, FR, RL, RR",
                 "frame": "body (x fwd, y left, z up), origin CAD origin, m; pitch > 0 nose down, roll > 0 right low",
                 "units": "SI unless a key says kN / MPa / deg", "runtime_s": None,
                 "limit_criteria": {
                     "A": "rod yield SF >= 1.5 at the levelling-end / dynamic-max lateral force with the static axial force",
                     "A_Pdyn141": "as A with axial max(141 kN, static) on every leg (sensitivity)",
                     "L": "the same lateral force sustained with the 350 bar lock axial (350 bar x head area of the leg; key names *lock364kN* kept from rev. 2): SF >= 1.0 (no yield)",
                     "AL": "A and L together (no re-anchoring)",
                     "RA_A": "with re-anchoring (3.10.7): peak = levelling end x manoeuvre factor at the run max axial, "
                             "SF >= 1.5; residual after re-anchoring: SF >= 1.5 static and >= 1.0 at 364 kN",
                     "RA_B": "option (design-criterion decision): as RA_A but the one-off peak only SF >= 1.0",
                     "guide": "piston guide pressure (20 mm CAD width, centre model) <= 40 / 100 MPa (information only)",
                     "by": f"criterion = first failing angle; stroke = a leg reaches the {stroke * 1e3:.0f} mm stroke first; "
                           "angles beyond the simulated vertices are extrapolated with the scaled kinematics"}},
        "assumptions": ASSUMPTIONS,
        "inputs": {"yaml": str(YAML_PATH.relative_to(PROJECT_ROOT)), "faces": str(FACES_CSV.relative_to(PROJECT_ROOT)),
                   "dynamics": str(PTC_JSON.relative_to(PROJECT_ROOT)), "mu_pad": mu,
                   "kt_yaml_N_m": kt_yaml.tolist(), "k_concrete_N_m": k_conc.tolist(),
                   "pad_force_static_N": Npad.tolist(), "rod_weight_N": W_rod, "P_lock_N": P_lock, "P_dyn_N": P_dyn,
                   "stroke_m": stroke, "P_lock_per_leg_N": P_lock_leg, "cylinders_m": {leg: geo[leg]["dims"] for leg in LEG_NAMES},
                   "static_cylinder_force_basis": static_basis, "cylinder_force_static_N": Ncyl.tolist(),
                   "envelope_rescale": {"applied": rescale, "kt_ptc_N_m": kt_ptc.tolist(), "ptc_cylinders_m": PTC_CYLINDERS_M,
                                        "scale_raw_new_over_ptc": scale_log},
                   "envelope_groups": ENV_GROUPS},
        "geometry": geo, "geometry_checks": chk, "levelling_extension_check": lev_check, "k_lat_check": klat_chk,
        "secant_kt_vs_dynamics": kt_sec_chk, "levelled_extension_vs_dynamics_kin_max_abs_m": lev_vs_kin,
        "envelope_vs_dynamics_report_max_abs_kN": rep_diff, "model_calibration_check": model_check,
        "pitch3.7_clip_check": clip37,
        "boundary_points": points, "per_leg_max": per_leg_max, "boundary_min_SF": boundary_min,
        "reanchor": reanchor, "limits_deg": limits, "model_curves": curves_model, "allowable_curves": curves,
        "d8_boundary_scan": d8_scan,
    }
    if h4 is not None:
        out["h4_adopted"] = h4  # rev. 3.2 (= set A, or the first set)
        out["h4_sets"] = h4_out  # rev. 3.3
    out["meta"]["runtime_s"] = round(time.time() - t0, 2)

    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, tuple):
            return list(o)
        raise TypeError(type(o))
    OUT_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=conv), encoding="utf-8")
    plot(out)
    print("wrote", OUT_JSON, OUT_PNG, "runtime", out["meta"]["runtime_s"], "s")


def plot(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.4))
    cols = {"C45_normalised": "#1f5fa8", "20MnV6": "#2e8b57"}
    cv = out["allowable_curves"]["FL"]
    e = np.array(cv["extension_m"]) * 1e3
    for mat, c in cols.items():
        ax[0].plot(e, np.array(cv[f"F_allow_rod_SF1.5_{mat}_N"]) / 1e3, "-", color=c, lw=1.6, label=f"rod yield / 1.5, {mat}")
    ax[0].plot(e, np.array(cv["F_allow_piston_phenolic_fabric_ring_N"]) / 1e3, "-", color="#c0392b", lw=1.2,
               label="piston guide 20 mm @ 40 MPa")
    ax[0].plot(e, np.array(cv["F_allow_piston_phenolic_static_upper_N"]) / 1e3, ":", color="#c0392b", lw=1.2,
               label="piston guide 20 mm @ 100 MPa")
    mk = {("V", "yaml"): ("s", "#444444", "D8 verification, YAML k_t"), ("V", "ext"): ("o", "#444444", "D8 verification, secant k_t"),
          ("P", "yaml"): ("s", "#d68910", "provisional limit, YAML k_t"), ("P", "ext"): ("o", "#d68910", "provisional limit, secant k_t")}
    for (rng, mode), (m, c, lab) in mk.items():
        pts = [r for r in out["boundary_points"] if r["range"] == rng and r["kt_mode"] == mode]
        ax[0].plot([r["extension_m"] * 1e3 for r in pts], [r["F_dyn_kN"] for r in pts], m, color=c, mfc="none", ms=5,
                   label=f"{lab} (all legs, 12 points)")
    ax[0].set_xlabel("leg extension e [mm]")
    ax[0].set_ylabel("lateral force at the ball centre [kN]")
    ax[0].set_ylim(0, 80); ax[0].set_xlim(300, 690); ax[0].grid(alpha=0.3)
    ax[0].set_title("FL geometry, static axial: allowable lateral force\nvs simulated pad tangential force (dynamic max)", fontsize=9)
    ax[0].legend(fontsize=6.5, loc="upper right")
    for k, (axi, dirs) in enumerate(((ax[1], ("pitch+", "pitch-")), (ax[2], ("roll+", "roll-")))):
        for direction, ls in zip(dirs, ("-", "--")):
            for mode, c in (("ext", "#1f5fa8"), ("yaml", "#c0392b")):
                mc = out["model_curves"][f"{direction}|{mode}"]
                ok = np.array(mc["extension_m"]) <= out["inputs"]["stroke_m"]  # stop the curves at the stroke end
                axi.plot(np.array(mc["angle_deg"])[ok], np.array(mc["F_N"])[ok] / 1e3, ls, color=c, lw=1.5,
                         label=f"{direction} {mc['leg']}, {'secant' if mode == 'ext' else 'YAML'} k_t")
            mc = out["model_curves"][f"{direction}|ext"]
            ok = np.array(mc["extension_m"]) <= out["inputs"]["stroke_m"]
            for mat, c in cols.items():
                axi.plot(np.array(mc["angle_deg"])[ok], np.array(mc[f"F_allow_{mat}_N"])[ok] / 1e3, ls, color=c, lw=0.9,
                         alpha=0.6, label=f"allowable {mat} (SF 1.5), {direction} {mc['leg']}")
        for r in out["boundary_points"]:
            if (k == 0 and r["roll_deg"] == 0) or (k == 1 and r["pitch_deg"] == 0):
                a = abs(r["pitch_deg"] if k == 0 else r["roll_deg"])
                axi.plot(a, r["F_dyn_kN"], "s" if r["kt_mode"] == "yaml" else "o", color="k", mfc="none", ms=4)
        axi.set_xlabel(("ground pitch |theta|" if k == 0 else "ground roll |phi|") + " [deg]")
        axi.set_ylabel("pad tangential force, governing long leg [kN]")
        axi.set_xlim(0.5, 6.2); axi.set_ylim(0, 80); axi.grid(alpha=0.3); axi.legend(fontsize=6, loc="upper left")
        axi.set_title(("front-rear slope" if k == 0 else "side slope") +
                      ": model (kinematics scaled to the simulated vertex, mu N cap)\nmarkers: simulated, all legs", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
