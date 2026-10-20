"""Body-origin candidates, mass audit and IMU mounting faces from the cached CAD tables.

Three reviews for 00_docs/00_cad/cad_origin_mass_imu.md. The STEP file is not read.

Reads (cached):
    01_cad/01_parts/parts_classified.csv   part rows: volume, centroid, density, mass (A, B)
    01_cad/03_auger/auger_parts.csv        same rows: motion class, case C mass
    01_cad/03_auger/auger_levels.json      superstructure mass properties per auger level
    01_cad/00_step/step_products.csv       all STEP products (names, materials)
    01_cad/05_meshes/parts_mesh.npz        full tessellation (3 mm deflection), index.json order
    01_cad/05_meshes/render_mesh.npz       decimated drawing meshes, parts_classified.csv order
    02_params/rexome33.yaml                pad positions, crawler contact assumptions

Writes:
    01_cad/01_parts/origin_mass_imu.json   all numbers of the three reviews
    01_cad/01_parts/mass_audit_parts.csv   per-part case C mass with audit flags
    01_cad/01_parts/origin_candidates.png  origin candidates on the shaded top and side views
    01_cad/01_parts/imu_candidates.png     IMU mounting faces: top view and two sections

Frames. CAD: mm, Y up. Body: x = Z_cad, y = X_cad, z = Y_cad in metres, origin = CAD
origin (frames.BODY_ORIGIN_IN_CAD_MM is still zero). Inertia is not used here.

Mass cases. A = STEP densities, B = 'generic' 1.0 -> 7.85 and glass 2.5 (comparison),
C = STEP densities except the 5 AUGER TOOL rows -> 7.85 g/cm^3 (reference, CLAUDE.md).

Usage:
    python -I 04_scripts/00_cad/analyze_origin_mass_imu.py [--skip-render]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely
import trimesh
import yaml
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_parts import CAD_TO_BODY, CLASSIFIED_CSV, INK_PRIMARY, LEG_COLORS, SURFACE
from cad_common import AUGER_DIR, MESH_DIR, MM_PER_M, PARTS_DIR, PRODUCTS_CSV, PROJECT_ROOT
from crawler_contact import layout_from_params
from render_auger_descent import load_render_meshes
from render_layout_views import (
    EdgeStyle,
    SceneItem,
    part_topology,
    px_per_metre,
    scene_collection,
    shade_scene,
)

AUGER_PARTS_CSV = AUGER_DIR / "auger_parts.csv"
AUGER_LEVELS_JSON = AUGER_DIR / "auger_levels.json"
PARTS_MESH_NPZ = MESH_DIR / "parts_mesh.npz"
MESH_INDEX_JSON = MESH_DIR / "index.json"
PARAMS_YAML = PROJECT_ROOT / "02_params" / "rexome33.yaml"
OUT_JSON = PARTS_DIR / "origin_mass_imu.json"
OUT_CSV = PARTS_DIR / "mass_audit_parts.csv"
ORIGIN_PNG = PARTS_DIR / "origin_candidates.png"
IMU_PNG = PARTS_DIR / "imu_candidates.png"

G = 9.80665
LEG_ORDER = ("FL", "FR", "RL", "RR")
CASES = {"A": "mass_step_kg", "B": "mass_generic_as_steel_kg", "C": "mass_tool_steel_kg"}

# --- origin -------------------------------------------------------------------------------
CONTACT_TOL_MM = (1.0, 3.0)  # crawler vertices this close to the lowest point form the patch
DECK_BOLT_SECTION_Y_MM = 12.0  # inside the deck bottom plate (Y 0 ... 25)
CRAWLER_BOLT_SECTION_Y_MM = -30.0  # inside the crawler mounting ring (top at Y -15)
BOLT_DISTANCE_RANGE_MM = (300.0, 800.0)  # bolt holes this far from the CAD Y axis
BOLT_FIT_RESIDUAL_MM = 2.0  # drop holes off the circle (other holes in the same band)

# --- IMU ----------------------------------------------------------------------------------
IMU_ASSUMED_BODY_M = np.array([0.20, 0.88, 0.30])  # CLAUDE.md
IMU_BOX_MM = (100.0, 100.0, 50.0)  # footprint a x b, height (ASSUMPTION: small IMU box)
IMU_CLEARANCE_MM = 10.0  # free margin around the box (bolt heads, cable gland)
IMU_GRID_MM = 10.0
IMU_REGION_CAD_MM = {"x": (250.0, 1450.0), "y": (-60.0, 800.0), "z": (-1150.0, 1400.0)}
CAB_FOOTPRINT_CAD_MM = {"x": (409.8, 1360.0), "z": (-826.5, 1221.7)}  # Shrinkwrap_11 bbox
FLAT_NORMAL_COS = 0.9999
MOUNT_SEARCHES = (
    # id, deck face direction (CAD axis, sign), plane level window along that axis (mm)
    {"id": "C1", "axis": 1, "sign": 1, "level": (39.0, 41.0),
     "label": "15 mm cross plate on the pontoon floor, top face"},
    {"id": "C2", "axis": 0, "sign": -1, "level": (1280.0, 1300.0),
     "label": "left pontoon C-channel web, inner face (inside the channel)"},
    {"id": "C3", "axis": 0, "sign": 1, "level": (1300.0, 1310.0),
     "label": "left pontoon C-channel web, outer face (machine left side)"},
    {"id": "C4", "axis": 1, "sign": 1, "level": (429.0, 431.0),
     "label": "centre spine top plate beside the cabin (reference: higher)"},
)
# Deck face that sits on the crawler mounting ring: down faces inside this annulus.
MATING_ANNULUS_MM = (500.0, 650.0)
# Rocking modes at the top auger level (00_docs/05_sensors/imu_cabin_and_accuracy_review.md
# 2.2, gain G at the assumed point).
ROCKING_TOP = ({"mode": "1 roll-sway", "f_hz": 1.784, "gain_at_assumed": 26.8},
               {"mode": "2 pitch-surge", "f_hz": 2.984, "gain_at_assumed": 130.5})

# --- mass audit ---------------------------------------------------------------------------
TOP_N = 30
SUSPECT_MIN_VOLUME_M3 = 0.005
SUSPECT_NAME_KEYS = ("COVER", "HOUSING", "CABIN", "TANK", "BOX", "SHRINKWRAP", "부마",
                     "COUNTER", "5J286105", "DOOR", "ROOF")
MISSING_KEYS = {
    "engine block": ("ENGINE", "엔진"),
    "hydraulic / fuel tank": ("TANK", "탱크", "FUEL", "연료"),
    "main pump / valve block": ("PUMP", "펌프", "VALVE", "밸브", "MCV"),
    "battery cells": ("BATTERY", "배터리", "BYHT"),
    "radiator / oil cooler": ("RADIATOR", "COOL", "라디에이터"),
    "hoses / wire rope": ("HOSE", "호스", "WIRE", "ROPE", "와이어"),
    "operator seat / controls": ("SEAT", "시트", "좌석", "JOYSTICK", "LEVER"),
    "counterweight": ("COUNTER",),
    "track shoes / rollers": ("SHOE", "ROLLER", "IDLER", "SPROCKET", "TRACK", "5J286105"),
}
# Locations for the +1 t sensitivity (resolved from the part table in sensitivity_points).
SENSITIVITY_ASSUMED_MASS_T = {  # ASSUMPTION: illustrative ranges, not from any data sheet
    "engine_bay": (1.0, 2.0),
    "rear_left_housing": (0.2, 0.5),
    "cabin": (0.2, 0.8),
    "counterweight": (-0.6, 0.6),
    "crawler": (-2.3, 2.3),
    "auger_tool_top": (0.0, 1.5),
}


# ==========================================================================================
# helpers
# ==========================================================================================


def to_body_m(cad_mm) -> np.ndarray:
    """CAD mm -> body m with the current origin (= CAD origin)."""
    return np.asarray(cad_mm, dtype=float) @ CAD_TO_BODY.T / MM_PER_M


def r(value, digits=4):
    """Round numbers inside nested lists / arrays for the JSON output."""
    if isinstance(value, dict):
        return {k: r(v, digits) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [r(v, digits) for v in value]
    if isinstance(value, (np.floating, float)):
        return round(float(value), digits)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


class PartMeshes:
    """Full tessellation cache addressed by instance path (index.json order differs)."""

    def __init__(self) -> None:
        data = np.load(PARTS_MESH_NPZ)
        self.vertices = data["vertices"]
        self.faces = data["faces"]
        self.vertex_offsets = data["vertex_offsets"]
        self.face_offsets = data["face_offsets"]
        index = json.loads(MESH_INDEX_JSON.read_text(encoding="utf-8"))
        self.meta = {k: index[k] for k in ("mesher", "linear_deflection_mm",
                                           "angular_deflection_rad", "frame")}
        self.paths = index["instance_paths"]
        self.row = {path: i for i, path in enumerate(self.paths)}

    def arrays(self, path: str) -> tuple[np.ndarray, np.ndarray]:
        i = self.row[path]
        v = self.vertices[self.vertex_offsets[i]:self.vertex_offsets[i + 1]].astype(np.float64)
        f = self.faces[self.face_offsets[i]:self.face_offsets[i + 1]].astype(np.int64)
        if len(f) and f.max() >= len(v):
            f = f - self.vertex_offsets[i]
        return v, f

    def trimesh(self, path: str) -> trimesh.Trimesh:
        v, f = self.arrays(path)
        return trimesh.Trimesh(v, f, process=False)

    def bounds(self, path: str):
        i = self.row[path]
        v = self.vertices[self.vertex_offsets[i]:self.vertex_offsets[i + 1]]
        return (v.min(axis=0), v.max(axis=0)) if len(v) else None

    def area_mm2(self, path: str) -> float:
        v, f = self.arrays(path)
        if len(f) == 0:
            return 0.0
        t = v[f]
        return float(0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]),
                                          axis=1).sum())


def load_tables():
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    auger = pd.read_csv(AUGER_PARTS_CSV, encoding="utf-8-sig")
    if not (auger["instance_path"] == parts["instance_path"]).all():
        raise SystemExit("auger_parts.csv row order differs from parts_classified.csv")
    parts["motion"] = auger["motion"]
    parts["mass_tool_steel_kg"] = auger["mass_tool_steel_kg"]
    with np.errstate(divide="ignore", invalid="ignore"):
        parts["density_tool_steel_g_cm3"] = np.where(
            parts["volume_used_mm3"] > 0,
            parts["mass_tool_steel_kg"] / (parts["volume_used_mm3"] * 1e-6), np.nan)
    parts["centroid_body_m"] = list(to_body_m(
        parts[["centroid_x_mm", "centroid_y_mm", "centroid_z_mm"]].to_numpy()))
    return parts


def path_of(parts: pd.DataFrame, suffix: str) -> str:
    hits = parts.loc[parts["instance_path"].str.endswith(suffix), "instance_path"]
    if len(hits) != 1:
        raise SystemExit(f"expected one part ending with {suffix!r}, got {len(hits)}")
    return hits.iloc[0]


def section_loops(mesh: trimesh.Trimesh, y_mm: float):
    """Closed loops of a horizontal section: (centre XZ, mean radius, radius std)."""
    section = mesh.section(plane_origin=[0.0, y_mm, 0.0], plane_normal=[0.0, 1.0, 0.0])
    loops = []
    for points in section.discrete:
        xz = np.asarray(points)[:, [0, 2]]
        centre = xz.mean(axis=0)
        radius = np.hypot(*(xz - centre).T)
        loops.append((centre, radius.mean(), radius.std()))
    return loops


def fit_circle(points: np.ndarray):
    """Algebraic least-squares circle; drops points off the circle and refits."""
    keep = np.ones(len(points), dtype=bool)
    for _ in range(5):
        a = np.c_[2 * points[keep], np.ones(keep.sum())]
        b = (points[keep] ** 2).sum(axis=1)
        sol = np.linalg.lstsq(a, b, rcond=None)[0]
        centre = sol[:2]
        radius = float(np.sqrt(sol[2] + centre @ centre))
        residual = np.hypot(*(points - centre).T) - radius
        new_keep = np.abs(residual) < BOLT_FIT_RESIDUAL_MM
        if (new_keep == keep).all():
            break
        keep = new_keep
    return centre, radius, residual, keep


def bolt_circle(mesh: trimesh.Trimesh, y_mm: float) -> dict:
    holes = [(c, rad) for c, rad, sd in section_loops(mesh, y_mm) if 5 < rad < 30 and sd < 1.5]
    centres = np.array([c for c, _ in holes])
    radii = np.array([rad for _, rad in holes])
    dist = np.hypot(*centres.T)
    band = (dist > BOLT_DISTANCE_RANGE_MM[0]) & (dist < BOLT_DISTANCE_RANGE_MM[1])
    centre, radius, residual, keep = fit_circle(centres[band])
    angles = np.sort(np.degrees(np.arctan2(*(centres[band][keep] - centre).T)))
    spacing = np.diff(np.append(angles, angles[0] + 360.0))
    return {
        "section_y_cad_mm": y_mm,
        "centre_cad_xz_mm": centre,
        "pitch_circle_radius_mm": radius,
        "pitch_circle_diameter_mm": 2 * radius,
        "holes_on_circle": int(keep.sum()),
        "holes_dropped": int((~keep).sum()),
        "hole_radius_mm": float(np.median(radii[band][keep])),
        "residual_max_mm": float(np.abs(residual[keep]).max()),
        "angular_spacing_deg_median": float(np.median(spacing)),
    }


def leg_unit_loads(pads_xy: np.ndarray, point_xy) -> np.ndarray:
    """Leg load shares for a unit vertical load at point_xy.

    ASSUMPTION (as in cad_auger_levels.md 4.4): rigid body on four equal vertical springs,
    rigid level floor -> F_i = a + b x_i + c y_i with force and moment balance.
    """
    a = np.c_[np.ones(4), pads_xy]
    m = a.T @ a
    coef = np.linalg.solve(m, np.array([1.0, point_xy[0], point_xy[1]]))
    return a @ coef


# ==========================================================================================
# 1. origin candidates
# ==========================================================================================


def crawler_patch(meshes: PartMeshes, crawler_path: str) -> dict:
    v, _ = meshes.arrays(crawler_path)
    y_min = float(v[:, 1].min())
    out = {"lowest_y_cad_mm": y_min, "tolerances": {}}
    for tol in CONTACT_TOL_MM:
        low = v[v[:, 1] < y_min + tol]
        sides = {}
        for name, mask in (("left(+X)", low[:, 0] > 0), ("right(-X)", low[:, 0] < 0)):
            q = low[mask]
            sides[name] = {"x_range_cad_mm": [q[:, 0].min(), q[:, 0].max()],
                           "z_range_cad_mm": [q[:, 2].min(), q[:, 2].max()],
                           "track_centre_x_cad_mm": 0.5 * (q[:, 0].min() + q[:, 0].max()),
                           "shoe_contact_width_mm": q[:, 0].max() - q[:, 0].min(),
                           "flat_length_mm": q[:, 2].max() - q[:, 2].min()}
        both = np.array([[s["track_centre_x_cad_mm"], 0.5 * sum(s["z_range_cad_mm"])]
                         for s in sides.values()])
        out["tolerances"][f"{tol:g}mm"] = {"sides": sides,
                                           "patch_centre_cad_xz_mm": both.mean(axis=0)}
    lo, hi = v.min(axis=0), v.max(axis=0)
    out["bbox_cad_mm"] = [lo, hi]
    out["bbox_centre_cad_xz_mm"] = [0.5 * (lo[0] + hi[0]), 0.5 * (lo[2] + hi[2])]
    return out


def origin_candidates(parts, meshes: PartMeshes, params: dict, levels: dict) -> dict:
    crawler_path = path_of(parts, "=>[0:1:1:746]")
    deck_path = path_of(parts, "BASE DECK:1")
    deck = meshes.trimesh(deck_path)
    crawler = meshes.trimesh(crawler_path)
    patch = crawler_patch(meshes, crawler_path)
    deck_bolts = bolt_circle(deck, DECK_BOLT_SECTION_Y_MM)
    crawler_bolts = bolt_circle(crawler, CRAWLER_BOLT_SECTION_Y_MM)
    centre_hole = [
        {"centre_cad_xz_mm": c, "radius_mm": rad}
        for c, rad, sd in section_loops(deck, DECK_BOLT_SECTION_Y_MM)
        if 80 < rad < 120 and sd < 1.5 and np.hypot(*c) < 50
    ]
    # deck mating face = largest down-facing plane of the deck over the bolt-circle annulus
    normals, centres, areas = deck.face_normals, deck.triangles_center, deck.area_faces
    radial = np.hypot(centres[:, 0], centres[:, 2])
    down = ((normals[:, 1] < -FLAT_NORMAL_COS) & (radial > MATING_ANNULUS_MM[0])
            & (radial < MATING_ANNULUS_MM[1]))
    planes = pd.Series(areas[down]).groupby(np.round(centres[down, 1], 1)).sum()
    deck_underside_y = float(planes.idxmax())
    ring_top_y = float(crawler.bounds[1][1])

    ground_y = patch["lowest_y_cad_mm"]
    pads = {leg: np.array(params["legs"][leg]["pad_bottom_center_retracted_m"])
            for leg in LEG_ORDER}
    pad_mean = np.mean([pads[leg] for leg in LEG_ORDER], axis=0)
    com = {lvl: {case: np.array(levels["levels"][lvl]["mass"][key]["cog_body_m"])
                 for case, key in (("A", "step"), ("B", "generic_as_steel"),
                                   ("C", "tool_steel"))}
           for lvl in ("top", "middle", "bottom")}

    swing_xz = crawler_bolts["centre_cad_xz_mm"]
    tol_key = f"{CONTACT_TOL_MM[0]:g}mm"
    patch_xz = patch["tolerances"][tol_key]["patch_centre_cad_xz_mm"]
    cands = {
        "O0_cad_origin": {
            "label": "CAD origin (current) = swing bolt-circle axis on the deck underside",
            "cad_mm": [0.0, 0.0, 0.0],
            "basis": "X, Z: crawler and deck bolt circles centred within 0.05 / 4.7 mm of X=Z=0; "
                     f"Y: deck underside plane (largest down face) Y = {deck_underside_y:g} mm",
        },
        "O1_crawler_bottom_centre": {
            "label": "crawler bottom centre (middle of the two track contact patches)",
            "cad_mm": [patch_xz[0], ground_y, patch_xz[1]],
            "basis": f"crawler vertices within {CONTACT_TOL_MM[0]:g} mm of the lowest point "
                     "(grouser tips), centre of both patches",
        },
        "O2_swing_axis_on_crawler_bottom": {
            "label": "swing (slewing-ring bolt circle) axis x crawler bottom plane",
            "cad_mm": [swing_xz[0], ground_y, swing_xz[1]],
            "basis": "crawler mounting-ring bolt circle centre (48 holes) at the grouser plane",
        },
        "O3_pad_mean_on_crawler_bottom": {
            "label": "mean of the four pad bottom centres, projected on the crawler bottom plane",
            "cad_mm": [pad_mean[1] * MM_PER_M, ground_y, pad_mean[0] * MM_PER_M],
            "basis": "rexome33.yaml legs.*.pad_bottom_center_retracted_m (mean); z = crawler "
                     f"bottom (pad mean z itself = {pad_mean[2]:.4f} m, front/rear differ 10.2 mm)",
        },
        "O4_com_projection_case_C": {
            "label": "superstructure CoM (case C, auger top) projected on the crawler bottom",
            "cad_mm": [com["top"]["C"][1] * MM_PER_M, ground_y, com["top"]["C"][0] * MM_PER_M],
            "basis": "auger_levels.json levels.top.mass.tool_steel.cog_body_m; reference only",
        },
    }
    crawler_bottom_body_z = ground_y / MM_PER_M
    for cand in cands.values():
        o_body = to_body_m(cand["cad_mm"])
        cand["body_m_current_frame"] = o_body
        cand["offset_from_cad_origin_body_m"] = o_body
        cand["BODY_ORIGIN_IN_CAD_MM"] = cand["cad_mm"]
        cand["in_new_frame"] = {
            "ground_crawler_bottom_z_m": crawler_bottom_body_z - o_body[2],
            "com_top_C_m": com["top"]["C"] - o_body,
            "com_bottom_C_m": com["bottom"]["C"] - o_body,
            "pad_FL_m": pads["FL"] - o_body,
            "pad_RR_m": pads["RR"] - o_body,
            "imu_assumed_m": IMU_ASSUMED_BODY_M - o_body,
        }
    com_xy_spread = {
        "x_by_case_m": {c: com["top"][c][0] for c in "ABC"},
        "y_by_case_m": {c: com["top"][c][1] for c in "ABC"},
        "xy_same_for_all_levels": bool(all(
            np.allclose(com[lvl][c][:2], com["top"][c][:2], atol=1e-9)
            for lvl in com for c in "ABC")),
    }
    return {
        "crawler_contact": patch,
        "swing_ring": {
            "crawler_mounting_ring_bolt_circle": crawler_bolts,
            "deck_bolt_circle": deck_bolts,
            "deck_centre_hole": centre_hole,
            "deck_underside_y_cad_mm": deck_underside_y,
            "deck_underside_area_m2": float(planes.max() * 1e-6),
            "crawler_ring_top_y_cad_mm": ring_top_y,
            "gap_deck_to_ring_mm": deck_underside_y - ring_top_y,
            "slewing_bearing_part_in_model": False,
            "note": "no slewing-ring / turntable product in step_products.csv (bearings found are "
                    "all inside DRIVE AUGER ASSY, outer diameter <= 460 mm)",
        },
        "pads_retracted_body_m": pads,
        "pad_mean_body_m": pad_mean,
        "com_body_m": com,
        "com_xy_by_case": com_xy_spread,
        "candidates": cands,
        # YAML crawler contact layout D (CAD-derived positions, crawler_contact.py).
        "yaml_crawler_layout": crawler_layout_record(params),
    }


def crawler_layout_record(params: dict) -> dict:
    """YAML contact.crawler.sphere_layout (layout D) as used by the contact models."""
    layout = layout_from_params(params)
    raw = params["contact"]["crawler"]["sphere_layout"]
    return {
        **layout.summary(),
        "roller_x_m": raw["roller_x_m"],
        "end_shoe_x_m": raw["end_shoe_x_m"],
        "end_shoe_gap_m": raw["end_shoe_gap_m"],
        "basis": "CAD B-rep cache 01_cad/06_brep/derived/crawler via export_params.py "
                 "(REXOME25 undercarriage drawn in the STEP: ASSUMPTION)",
    }


def origin_change_impact(params: dict) -> dict:
    """YAML position keys that change when the body origin moves (counted from the file)."""
    shifted_z, shifted_xy = [], []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
            return
        name = path.rsplit(".", 1)[-1]
        if name in ("crawler_bottom_z_m", "lowest_pad_bottom_z_m") or name.endswith("z_range_m"):
            shifted_z.append(path)
        elif name in ("com_m", "com_retracted_m", "attachment_point_m",
                      "pad_bottom_center_retracted_m"):
            shifted_z.append(path)
            shifted_xy.append(path)
        elif name in ("cylinder_axis_xy_m", "track_centre_y_m", "roller_x_m", "end_shoe_x_m"):
            shifted_xy.append(path)

    walk(params, "")
    return {"keys_changed_by_z_shift": shifted_z, "keys_changed_by_xy_shift": shifted_xy,
            "n_z": len(shifted_z), "n_xy": len(shifted_xy),
            "n_z_or_xy": len(set(shifted_z) | set(shifted_xy))}


# ==========================================================================================
# 2. mass audit
# ==========================================================================================


def mass_audit(parts: pd.DataFrame, meshes: PartMeshes, levels: dict, origin: dict) -> dict:
    products = pd.read_csv(PRODUCTS_CSV, encoding="utf-8-sig")
    vol_m3 = parts["volume_used_mm3"].fillna(0) * 1e-9
    parts["volume_m3"] = vol_m3
    parts["mesh_area_m2"] = [meshes.area_mm2(p) * 1e-6 if p in meshes.row else np.nan
                             for p in parts["instance_path"]]
    with np.errstate(divide="ignore", invalid="ignore"):
        parts["equivalent_thickness_mm"] = 2.0 * vol_m3 / parts["mesh_area_m2"] * MM_PER_M
    dens = parts["density_step_g_cm3"]
    material = parts["material_resolved"].fillna("")
    parts["flag_generic_material"] = material.eq("일반")
    parts["flag_density_1"] = dens.eq(1.0)
    parts["flag_assumed_steel"] = parts["density_source"].eq("assumed")
    parts["flag_density_invalid"] = dens.isna() | (dens <= 0)
    parts["flag_no_solid"] = vol_m3 <= 0
    parts["flag_placeholder"] = (parts["flag_generic_material"] | parts["flag_density_1"]
                                 | parts["flag_assumed_steel"] | parts["flag_density_invalid"])
    parts["flag_tool_steel_override"] = parts["motion"].eq("moving_tool")
    parts["superstructure"] = parts["group"].ne("leg_rod_pad")
    total_c = parts["mass_tool_steel_kg"].sum()
    sup = parts["superstructure"]

    def summary(mask):
        sub = parts[mask]
        return {"rows": int(len(sub)), "volume_m3": sub["volume_m3"].sum(),
                **{f"mass_{c}_kg": sub[col].sum() for c, col in CASES.items()},
                "share_of_C_total_pct": 100 * sub["mass_tool_steel_kg"].sum() / total_c}

    placeholder = parts[parts["flag_placeholder"]].sort_values("mass_tool_steel_kg",
                                                                ascending=False)
    placeholder_rows = [
        {"product": row.product_name, "top_assembly": row.top_assembly,
         "material": row.material_resolved, "density_step_g_cm3": row.density_step_g_cm3,
         "density_C_g_cm3": row.density_tool_steel_g_cm3, "source": row.density_source,
         "volume_m3": row.volume_m3, "mass_A_kg": row.mass_step_kg,
         "mass_B_kg": row.mass_generic_as_steel_kg, "mass_C_kg": row.mass_tool_steel_kg,
         "tool_override_in_C": bool(row.flag_tool_steel_override),
         "centroid_body_m": row.centroid_body_m}
        for row in placeholder.itertuples()
    ]
    no_solid = parts[parts["flag_no_solid"]]
    no_solid_groups = no_solid.groupby("top_assembly").size().sort_values(ascending=False)

    # density histogram (case C densities)
    dens_c = parts["density_tool_steel_g_cm3"].round(3)
    hist = (parts.assign(d=dens_c).groupby("d", dropna=False)
            .agg(rows=("d", "size"), volume_m3=("volume_m3", "sum"),
                 mass_C_kg=("mass_tool_steel_kg", "sum")))
    hist["mass_share_pct"] = 100 * hist["mass_C_kg"] / total_c

    # top contributors
    top = parts.sort_values("mass_tool_steel_kg", ascending=False).head(TOP_N)
    top_rows = [
        {"rank": k + 1, "product": row.product_name, "top_assembly": row.top_assembly,
         "material": row.material_resolved, "density_C_g_cm3": row.density_tool_steel_g_cm3,
         "mass_C_kg": row.mass_tool_steel_kg,
         "share_pct": 100 * row.mass_tool_steel_kg / total_c,
         "centroid_body_m_cad_pose": row.centroid_body_m, "motion": row.motion,
         "bbox_fill_ratio": row.bbox_fill_ratio,
         "equivalent_thickness_mm": row.equivalent_thickness_mm}
        for k, row in enumerate(top.itertuples())
    ]
    top_share = 100 * top["mass_tool_steel_kg"].sum() / total_c

    # suspicious volume / density
    upper = (parts["product_name"].fillna("").astype(str).str.upper() + " "
             + parts["top_assembly"].str.upper())
    named = upper.apply(lambda s: any(k.upper() in s for k in SUSPECT_NAME_KEYS))
    suspect = parts[(parts["volume_m3"] >= SUSPECT_MIN_VOLUME_M3) & named].sort_values(
        "volume_m3", ascending=False)
    suspect_rows = [
        {"product": row.product_name, "top_assembly": row.top_assembly,
         "density_C_g_cm3": row.density_tool_steel_g_cm3, "volume_m3": row.volume_m3,
         "mass_C_kg": row.mass_tool_steel_kg, "bbox_fill_ratio": row.bbox_fill_ratio,
         "equivalent_thickness_mm": row.equivalent_thickness_mm,
         "solid_count": row.solid_count, "centroid_body_m": row.centroid_body_m}
        for row in suspect.itertuples()
    ]

    # products that would carry the usually-missing masses
    names = (products["product_name"].fillna("").astype(str) + " | "
             + products["product_description"].fillna("").astype(str))
    missing = {}
    for item, keys in MISSING_KEYS.items():
        hit_products = products[names.str.upper().apply(
            lambda s, ks=keys: any(k.upper() in s for k in ks))]["product_name"].tolist()
        label = parts["product_name"].fillna("").astype(str) + " " + parts["instance_path"]
        rows = parts[label.str.upper()
                     .apply(lambda s, ks=keys: any(k.upper() in s for k in ks))]
        missing[item] = {"keywords": keys, "matching_products": sorted(set(hit_products))[:25],
                         "n_matching_products": len(set(hit_products)),
                         "mass_C_kg_of_matching_rows": rows["mass_tool_steel_kg"].sum()}

    # A / B / C totals (independent re-sum) and the auger_levels.json values
    cases = {}
    for case, col in CASES.items():
        for name, mask in (("whole_assembly", np.ones(len(parts), dtype=bool)),
                           ("superstructure", sup.to_numpy())):
            sub = parts[mask]
            m = sub[col].sum()
            c = (np.stack(sub["centroid_body_m"].to_numpy()) * sub[[col]].to_numpy()).sum(0) / m
            cases[f"{case}_{name}_cad_pose"] = {"mass_kg": m, "com_body_m": c}
    key = {"A": "step", "B": "generic_as_steel", "C": "tool_steel"}
    checks = {}
    for case in "ABC":
        ref = levels["current_cad_pose"]["mass"][key[case]]
        mine = cases[f"{case}_superstructure_cad_pose"]
        checks[case] = {
            "mass_rel_diff": abs(mine["mass_kg"] - ref["mass_kg"]) / ref["mass_kg"],
            "com_max_abs_diff_m": float(np.abs(mine["com_body_m"]
                                               - np.array(ref["cog_body_m"])).max()),
            "note": "auger_levels.json values are rounded to 0.1 kg / 0.1 mm",
        }
    by_level = {lvl: {c: {"mass_kg": levels["levels"][lvl]["mass"][key[c]]["mass_kg"],
                          "com_body_m": levels["levels"][lvl]["mass"][key[c]]["cog_body_m"],
                          "leg_loads_kN": levels["levels"][lvl]["mass"][key[c]]["leg_loads_kN"]}
                      for c in "ABC"}
                for lvl in ("top", "middle", "bottom")}

    by_assembly = (parts[sup].groupby("top_assembly")
                   .agg(mass_A_kg=("mass_step_kg", "sum"),
                        mass_C_kg=("mass_tool_steel_kg", "sum"),
                        placeholder_C_kg=("mass_tool_steel_kg",
                                          lambda s: s[parts.loc[s.index,
                                                                "flag_placeholder"]].sum()))
                   .sort_values("mass_C_kg", ascending=False))

    sensitivity = mass_sensitivity(parts, levels, origin)
    return {
        "placeholder_summary": summary(parts["flag_placeholder"]),
        "placeholder_breakdown": {
            "generic_material": summary(parts["flag_generic_material"]),
            "density_1_any_material": summary(parts["flag_density_1"]),
            "assumed_steel_unknown_material": summary(parts["flag_assumed_steel"]),
            "density_invalid": summary(parts["flag_density_invalid"]),
            "generic_overridden_in_C_tool": summary(parts["flag_placeholder"]
                                                    & parts["flag_tool_steel_override"]),
            "generic_kept_in_C": summary(parts["flag_placeholder"]
                                         & ~parts["flag_tool_steel_override"]),
        },
        "placeholder_parts": placeholder_rows,
        "no_solid_rows": {"rows": int(len(no_solid)),
                          "by_top_assembly": no_solid_groups.to_dict(),
                          "note": "mass 0 in all cases (gear placeholders, open shells)"},
        "density_histogram_C": [
            {"density_g_cm3": None if pd.isna(d) else float(d), **row}
            for d, row in hist.reset_index().set_index("d").to_dict(orient="index").items()
        ],
        "top_contributors_C": top_rows,
        "top_contributors_share_pct": top_share,
        "suspect_volume_density": suspect_rows,
        "possibly_missing": missing,
        "cases_cad_pose": cases,
        "cases_check_vs_auger_levels": checks,
        "cases_by_auger_level": by_level,
        "superstructure_by_top_assembly_kg": by_assembly.round(1).to_dict(orient="index"),
        "total_C_kg": total_c,
        "sensitivity": sensitivity,
    }


def mass_sensitivity(parts: pd.DataFrame, levels: dict, origin: dict) -> dict:
    """Leg-load and CoM change for +1 t at characteristic locations (case C, auger top)."""
    pads = origin["pads_retracted_body_m"]
    pads_xy = np.array([pads[leg][:2] for leg in LEG_ORDER])
    ref = levels["levels"]["top"]["mass"]["tool_steel"]
    mass = ref["mass_kg"]
    com = np.array(ref["cog_body_m"])

    def group_centroid(mask):
        sub = parts[mask]
        w = sub["mass_tool_steel_kg"].to_numpy()
        return (np.stack(sub["centroid_body_m"].to_numpy()) * w[:, None]).sum(0) / w.sum()

    def bbox_centre(mask):
        sub = parts[mask]
        lo = to_body_m([sub["bbox_min_x_mm"].min(), sub["bbox_min_y_mm"].min(),
                        sub["bbox_min_z_mm"].min()])
        hi = to_body_m([sub["bbox_max_x_mm"].max(), sub["bbox_max_y_mm"].max(),
                        sub["bbox_max_z_mm"].max()])
        return 0.5 * (lo + hi), lo, hi

    ta = parts["top_assembly"]
    engine_c, engine_lo, engine_hi = bbox_centre(ta.str.startswith("SIDE HOUSING_(ENGINE)"))
    rear_c, rear_lo, rear_hi = bbox_centre(ta.str.startswith("CABIN HOUSING_R1"))
    cab_c, cab_lo, cab_hi = bbox_centre(ta.str.startswith("BUMA"))
    tool = levels["levels"]["top"]["mass"]["tool_steel"]["moving_set_cog_body_m"]
    points = {
        "engine_bay": {"point_body_m": engine_c, "basis": "SIDE HOUSING_(ENGINE)_R1 bbox centre "
                       f"(bbox {r(engine_lo, 2)} ... {r(engine_hi, 2)} m)"},
        "rear_left_housing": {"point_body_m": rear_c, "basis": "CABIN HOUSING_R1 bbox centre "
                              "(cooler covers, behind the cabin)"},
        "cabin": {"point_body_m": cab_c, "basis": "BUMA CE cabin bbox centre"},
        "counterweight": {"point_body_m": group_centroid(ta.str.startswith("COUNTER WEIGHT")),
                          "basis": "COUNTER WEIGHT mass centroid"},
        "crawler": {"point_body_m": group_centroid(parts["is_crawler"]),
                    "basis": "crawler compound mass centroid"},
        "auger_tool_top": {"point_body_m": np.array(tool), "basis": "drive + tool CoM at the "
                           "top level (auger_levels.json moving_set_cog_body_m)"},
        "superstructure_com": {"point_body_m": com, "basis": "uniform scaling of the total"},
    }
    base_loads = mass * G * leg_unit_loads(pads_xy, com[:2]) / 1000.0
    out = {"reference": {"case": "C", "level": "top", "mass_kg": mass, "com_body_m": com,
                         "leg_loads_kN": dict(zip(LEG_ORDER, base_loads, strict=True)),
                         "model": "4 equal vertical springs, rigid level floor, pads at "
                                  "pad_bottom_center_retracted_m (ASSUMPTION)"},
           "per_tonne": {}}
    for name, item in points.items():
        p = np.asarray(item["point_body_m"], dtype=float)
        d_loads = 1000.0 * G * leg_unit_loads(pads_xy, p[:2]) / 1000.0
        d_com = 1000.0 * (p - com) / (mass + 1000.0)
        row = {"point_body_m": p, "basis": item["basis"],
               "dF_kN_per_t": dict(zip(LEG_ORDER, d_loads, strict=True)),
               "dCoM_mm_per_t": d_com * MM_PER_M}
        if name in SENSITIVITY_ASSUMED_MASS_T:
            lo, hi = SENSITIVITY_ASSUMED_MASS_T[name]
            row["illustrative_range_t_ASSUMPTION"] = [lo, hi]
            row["dF_kN_at_range"] = {leg: [lo * d_loads[k], hi * d_loads[k]]
                                     for k, leg in enumerate(LEG_ORDER)}
            row["dCoM_z_mm_at_range"] = [lo * d_com[2] * MM_PER_M, hi * d_com[2] * MM_PER_M]
        out["per_tonne"][name] = row
    return out


# ==========================================================================================
# 3. IMU mounting faces
# ==========================================================================================


def region_triangles(parts: pd.DataFrame, meshes: PartMeshes):
    """Triangles (CAD mm) of all parts inside the IMU search region, with their owner rows."""
    rx, ry, rz = (IMU_REGION_CAD_MM[k] for k in "xyz")
    tris, owners = [], []
    for row, path in enumerate(parts["instance_path"]):
        bounds = meshes.bounds(path)
        if bounds is None:
            continue
        lo, hi = bounds
        if hi[0] < rx[0] or lo[0] > rx[1] or hi[1] < ry[0] or lo[1] > ry[1] \
                or hi[2] < rz[0] or lo[2] > rz[1]:
            continue
        v, f = meshes.arrays(path)
        t = v[f]
        tlo, thi = t.min(axis=1), t.max(axis=1)
        keep = ((thi[:, 0] > rx[0]) & (tlo[:, 0] < rx[1]) & (thi[:, 1] > ry[0])
                & (tlo[:, 1] < ry[1]) & (thi[:, 2] > rz[0]) & (tlo[:, 2] < rz[1]))
        tris.append(t[keep])
        owners.append(np.full(int(keep.sum()), row))
    return np.concatenate(tris), np.concatenate(owners)


def mount_search(spec: dict, tris: np.ndarray, owners: np.ndarray, deck_row: int,
                 parts: pd.DataFrame) -> dict:
    """Feasible centres of an IMU box on one deck face family.

    The box footprint (IMU_BOX_MM a x b) must lie on the support face, and no triangle of
    any part may enter the volume footprint + clearance x (box height + clearance) above it.
    """
    a = spec["axis"]
    s = spec["sign"]
    b, c = [k for k in range(3) if k != a]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        na = s * n[:, a] / (2 * area)
    level_coord = tris[:, :, a].mean(axis=1)
    on = ((owners == deck_row) & (na > FLAT_NORMAL_COS) & (area > 0)
          & (level_coord >= spec["level"][0]) & (level_coord <= spec["level"][1]))
    if not on.any():
        return {**spec, "feasible": 0}
    levels = pd.Series(area[on]).groupby(np.round(level_coord[on], 1)).sum()
    level = float(levels.idxmax())
    on &= np.abs(level_coord - level) < 0.05
    support = shapely.union_all([Polygon(t[:, [b, c]]) for t in tris[on]])
    height = IMU_BOX_MM[2] + IMU_CLEARANCE_MM
    lo_a, hi_a = tris[:, :, a].min(axis=1), tris[:, :, a].max(axis=1)
    if s > 0:
        slab = (hi_a > level + 0.5) & (lo_a < level + height)
    else:
        slab = (lo_a < level - 0.5) & (hi_a > level - height)
    obstacles = shapely.union_all([Polygon(t[:, [b, c]]).buffer(0.5) for t in tris[slab]])
    shapely.prepare(support)
    shapely.prepare(obstacles)
    sb = support.bounds
    half_a, half_b = IMU_BOX_MM[0] / 2, IMU_BOX_MM[1] / 2
    ok = []
    for u in np.arange(np.floor(sb[0] / 10) * 10, sb[2] + 1e-6, IMU_GRID_MM):
        for v in np.arange(np.floor(sb[1] / 10) * 10, sb[3] + 1e-6, IMU_GRID_MM):
            footprint = box(u - half_a, v - half_b, u + half_a, v + half_b)
            if support.contains(footprint) and not obstacles.intersects(
                    footprint.buffer(IMU_CLEARANCE_MM, join_style="mitre")):
                ok.append((u, v))
    ok = np.array(ok)
    out = {**spec, "plane_level_cad_mm": level, "support_area_m2": support.area * 1e-6,
           "feasible": int(len(ok))}
    if not len(ok):
        return out
    target = np.zeros(3)
    target_cad = CAD_TO_BODY.T @ IMU_ASSUMED_BODY_M * MM_PER_M  # body -> CAD (rotation only)
    target[[b, c]] = target_cad[[b, c]]
    if a == 1:  # horizontal face (in-plane X, Z): nearest to the assumed point
        pick = int(np.argmin(np.hypot(ok[:, 0] - target[b], ok[:, 1] - target[c])))
    else:  # vertical X face (in-plane Y, Z): lowest centre, then nearest to the assumed x
        lowest = np.flatnonzero(ok[:, 0] <= ok[:, 0].min() + 1e-6)
        pick = int(lowest[np.argmin(np.abs(ok[lowest, 1] - target[2]))])
    point = np.zeros(3)
    point[a] = level
    point[[b, c]] = ok[pick]
    # free distance along the normal above the chosen footprint
    footprint = box(ok[pick][0] - half_a, ok[pick][1] - half_b, ok[pick][0] + half_a,
                    ok[pick][1] + half_b)
    beyond = (hi_a > level + 0.5) if s > 0 else (lo_a < level - 0.5)
    idx = np.flatnonzero(beyond)
    proj = [Polygon(t[:, [b, c]]).buffer(0.5) for t in tris[idx]]
    hit = [k for k, g in zip(idx, proj, strict=True) if g.intersects(footprint)]
    if hit:
        dist_along = (tris[hit, :, a].min(axis=1) - level) if s > 0 else \
            (level - tris[hit, :, a].max(axis=1))
        j = int(np.argmin(dist_along))
        free = float(dist_along[j])
        blocker = parts["instance_path"].iloc[owners[hit[j]]].split(" / ", 1)[-1]
    else:
        free, blocker = None, None
    normal_cad = np.zeros(3)
    normal_cad[a] = s
    body = to_body_m(point)
    feasible_body = np.zeros((len(ok), 3))
    feasible_body[:, a] = level
    feasible_body[:, b] = ok[:, 0]
    feasible_body[:, c] = ok[:, 1]
    feasible_body = to_body_m(feasible_body)
    # G = 1 - r_eff w^2 / g with r_eff < 0 (rotation centre below the IMU): moving the IMU
    # by dz along z changes G by +w^2 dz / g (rotation part only; x, y offsets ignored).
    dz = body[2] - IMU_ASSUMED_BODY_M[2]
    rocking = [{"mode": m["mode"], "gain_at_assumed": m["gain_at_assumed"],
                "gain_estimate": m["gain_at_assumed"] + (2 * np.pi * m["f_hz"]) ** 2 * dz / G}
               for m in ROCKING_TOP]
    cab_x, cab_z = CAB_FOOTPRINT_CAD_MM["x"], CAB_FOOTPRINT_CAD_MM["z"]
    return {
        **out,
        "box_centre_on_face_cad_mm": point,
        "box_centre_on_face_body_m": body,
        "box_centroid_body_m": body + CAD_TO_BODY @ normal_cad * IMU_BOX_MM[2] / 2 / MM_PER_M,
        "face_normal_body": CAD_TO_BODY @ normal_cad,
        "offset_from_assumed_m": body - IMU_ASSUMED_BODY_M,
        "free_distance_along_normal_mm": free,
        "first_obstacle_along_normal": blocker,
        "under_cab_footprint": bool(cab_x[0] <= point[0] <= cab_x[1]
                                    and cab_z[0] <= point[2] <= cab_z[1]),
        "feasible_body_range_m": [feasible_body.min(axis=0), feasible_body.max(axis=0)],
        "feasible_centres_body_m": feasible_body,
        "rocking_gain_estimate_top": rocking,
    }


def imu_candidates(parts: pd.DataFrame, meshes: PartMeshes) -> dict:
    tris, owners = region_triangles(parts, meshes)
    deck_row = int(np.flatnonzero(parts["instance_path"].str.endswith("BASE DECK:1"))[0])
    results = [mount_search(spec, tris, owners, deck_row, parts) for spec in MOUNT_SEARCHES]
    # cabin mount seats (structure side of the cab mounts): deck plates at Y 194 ... 204
    return {"box_mm": IMU_BOX_MM, "clearance_mm": IMU_CLEARANCE_MM, "grid_mm": IMU_GRID_MM,
            "search_region_cad_mm": IMU_REGION_CAD_MM, "triangles_in_region": int(len(tris)),
            "assumed_point_body_m": IMU_ASSUMED_BODY_M, "candidates": results}


# ==========================================================================================
# figures
# ==========================================================================================


def draw_sections(ax, meshes: PartMeshes, parts, axis: int, value_mm: float, h: int, v: int,
                  window):
    normal = np.zeros(3)
    normal[axis] = 1.0
    origin = np.zeros(3)
    origin[axis] = value_mm
    colours = {"BASE DECK": INK_PRIMARY, "BUMA": "#2a78d6", "BATTERY": "#1baf7a",
               "5J286105": "#8c6d46"}
    for path in parts["instance_path"]:
        bounds = meshes.bounds(path)
        if bounds is None or not (bounds[0][axis] <= value_mm <= bounds[1][axis]):
            continue
        lo, hi = bounds
        if hi[h] < window[0][0] or lo[h] > window[0][1] or hi[v] < window[1][0] \
                or lo[v] > window[1][1]:
            continue
        segs = trimesh.intersections.mesh_plane(meshes.trimesh(path), normal, origin)
        colour = next((c for k, c in colours.items() if k in path), "#a8a7a0")
        for seg in segs:
            ax.plot(seg[:, h] / MM_PER_M, seg[:, v] / MM_PER_M, color=colour, lw=0.6)


DEFAULT_EDGE_STYLE = EdgeStyle()


def render_view(ax, render, rows, view, colours, style=DEFAULT_EDGE_STYLE, dpi=150):
    items = []
    for row in rows:
        vertices, faces = render[row]
        if len(faces) == 0:
            continue
        items.append(SceneItem(vertices @ CAD_TO_BODY.T / MM_PER_M,
                               part_topology(vertices, faces), colours[row]))
    scene = shade_scene(items, view, px_per_metre(ax), style, dpi)
    ax.add_collection(scene_collection(scene))


def figure_imu(parts, meshes, render, imu: dict) -> None:
    fig = plt.figure(figsize=(16, 7.2), facecolor=SURFACE)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.25], height_ratios=[1.0, 1.0])
    ax_top = fig.add_subplot(grid[:, 0])
    ax_side = fig.add_subplot(grid[0, 1])
    ax_front = fig.add_subplot(grid[1, 1])
    for ax in (ax_top, ax_side, ax_front):
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")
    # top view: shaded render cache, cabin hidden, window around the cabin
    window_xy = ((-1.15, 1.45), (0.2, 1.5))
    ax_top.set_xlim(*window_xy[0])
    ax_top.set_ylim(*window_xy[1])
    rows, colours = [], {}
    for row, path in enumerate(parts["instance_path"]):
        if "BUMA" in path:
            continue
        lo = to_body_m([parts.at[row, "bbox_min_x_mm"], parts.at[row, "bbox_min_y_mm"],
                        parts.at[row, "bbox_min_z_mm"]])
        hi = to_body_m([parts.at[row, "bbox_max_x_mm"], parts.at[row, "bbox_max_y_mm"],
                        parts.at[row, "bbox_max_z_mm"]])
        if hi[0] < window_xy[0][0] or lo[0] > window_xy[0][1] or hi[1] < window_xy[1][0] \
                or lo[1] > window_xy[1][1] or lo[2] > 0.8:
            continue
        rows.append(row)
        colours[row] = "#c9c7bf" if "BASE DECK" in path else "#a8a7a0"
    render_view(ax_top, render, rows, "top", colours)
    cab_lo = to_body_m([CAB_FOOTPRINT_CAD_MM["x"][0], 0, CAB_FOOTPRINT_CAD_MM["z"][0]])
    cab_hi = to_body_m([CAB_FOOTPRINT_CAD_MM["x"][1], 0, CAB_FOOTPRINT_CAD_MM["z"][1]])
    ax_top.add_patch(Rectangle((cab_lo[0], cab_lo[1]), cab_hi[0] - cab_lo[0],
                               cab_hi[1] - cab_lo[1], fill=False, ls="--", lw=1.2,
                               ec="#2a78d6", zorder=4, label="cabin footprint (hidden)"))
    ax_top.set_title("top view (x-y), parts below z 0.8 m, cabin removed")
    ax_top.set_xlabel("x [m] (forward)")
    ax_top.set_ylabel("y [m] (left)")
    # sections through the recommended candidate
    c1 = imu["candidates"][0]
    p = c1["box_centre_on_face_body_m"]
    side_window = ((-1.0, 1.3), (-0.08, 0.45))
    draw_sections(ax_side, meshes, parts, 0, p[1] * MM_PER_M, 2, 1,
                  ((side_window[0][0] * MM_PER_M, side_window[0][1] * MM_PER_M),
                   (side_window[1][0] * MM_PER_M, side_window[1][1] * MM_PER_M)))
    ax_side.set_xlim(*side_window[0])
    ax_side.set_ylim(*side_window[1])
    ax_side.set_title(f"side section at y = {p[1]:.2f} m "
                      "(black deck, blue cabin; markers projected)")
    ax_side.set_xlabel("x [m]")
    ax_side.set_ylabel("z [m]")
    front_window = ((0.25, 1.45), (-0.08, 0.45))
    draw_sections(ax_front, meshes, parts, 2, p[0] * MM_PER_M, 0, 1,
                  ((front_window[0][0] * MM_PER_M, front_window[0][1] * MM_PER_M),
                   (front_window[1][0] * MM_PER_M, front_window[1][1] * MM_PER_M)))
    ax_front.set_xlim(front_window[0][1], front_window[0][0])  # left (+y) on the left
    ax_front.set_ylim(*front_window[1])
    ax_front.set_title(f"front section at x = {p[0]:.2f} m, looking aft (+y left)")
    ax_front.set_xlabel("y [m]")
    ax_front.set_ylabel("z [m]")
    marks = {"C1": "#eb6834", "C2": "#1baf7a", "C3": "#7a3fc4", "C4": "#eda100"}
    a0 = IMU_ASSUMED_BODY_M
    for ax, (h, v) in ((ax_top, (0, 1)), (ax_side, (0, 2)), (ax_front, (1, 2))):
        ax.plot(a0[h], a0[v], marker="*", ms=13, color="#d62a2a", mec="white", zorder=6,
                ls="none", label="assumed (0.20, 0.88, 0.30)")
        for cand in imu["candidates"]:
            if cand.get("feasible", 0) == 0:
                continue
            q = cand["box_centre_on_face_body_m"]
            colour = marks[cand["id"]]
            if ax is ax_top:
                fb = np.asarray(cand["feasible_centres_body_m"])
                ax.scatter(fb[:, 0], fb[:, 1], s=2, color=colour, alpha=0.35, zorder=5)
            ax.plot(q[h], q[v], marker="o", ms=8, color=colour, mec="black", zorder=7,
                    ls="none", label=f"{cand['id']} ({q[0]:.2f}, {q[1]:.2f}, {q[2]:.3f})")
    ax_top.legend(loc="lower left", fontsize=8, framealpha=0.9)
    fig.suptitle("IMU mounting faces on the upper frame (BASE DECK) under the cabin, "
                 "box 100 x 100 x 50 mm + 10 mm clearance; dots = feasible box centres",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(IMU_PNG, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def figure_origin(parts, render, origin: dict) -> None:
    fig, (ax_top, ax_side) = plt.subplots(2, 1, figsize=(12, 13), facecolor=SURFACE,
                                          gridspec_kw={"height_ratios": [1.0, 1.7]})
    for ax in (ax_top, ax_side):
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")
    ax_top.set_xlim(-3.3, 4.3)
    ax_top.set_ylim(-1.8, 1.8)
    ax_side.set_xlim(-3.3, 4.3)
    ax_side.set_ylim(-1.3, 3.4)
    colours = {}
    rows = []
    for row in range(len(parts)):
        leg = parts.at[row, "leg"]
        colours[row] = LEG_COLORS.get(leg, "#a8a7a0") if isinstance(leg, str) else "#a8a7a0"
        rows.append(row)
    render_view(ax_top, render, rows, "top", colours)
    render_view(ax_side, render, rows, "side", colours)
    marks = {"O0_cad_origin": ("o", "#0b0b0b"), "O1_crawler_bottom_centre": ("s", "#2a78d6"),
             "O2_swing_axis_on_crawler_bottom": ("D", "#eb6834"),
             "O3_pad_mean_on_crawler_bottom": ("^", "#1baf7a"),
             "O4_com_projection_case_C": ("v", "#eda100")}
    com_top = origin["com_body_m"]["top"]["C"]
    for key, cand in origin["candidates"].items():
        p = np.asarray(cand["body_m_current_frame"])
        marker, colour = marks[key]
        label = f"{key.split('_', 1)[0]} ({p[0]:+.3f}, {p[1]:+.3f}, {p[2]:+.3f})"
        for ax, (h, v) in ((ax_top, (0, 1)), (ax_side, (0, 2))):
            ax.plot(p[h], p[v], marker=marker, ms=9, color=colour, mec="white", mew=0.8,
                    ls="none", zorder=8, label=label if ax is ax_top else None)
    for ax, (h, v) in ((ax_top, (0, 1)), (ax_side, (0, 2))):
        ax.plot(com_top[h], com_top[v], marker="X", ms=10, color="#d62a2a", mec="white",
                ls="none", zorder=8, label="CoM case C, auger top" if ax is ax_top else None)
    ax_side.axhline(origin["crawler_contact"]["lowest_y_cad_mm"] / MM_PER_M, color="#8c6d46",
                    lw=0.8, ls="--")
    ax_side.axhline(0.0, color="#0b0b0b", lw=0.5, ls=":")
    ax_top.set_title("top view (x-y), current frame = CAD origin")
    ax_side.set_title("side view (x-z); dashed = crawler bottom plane z -1.0509 m, "
                      "dotted = deck underside z 0")
    ax_top.set_xlabel("x [m]")
    ax_top.set_ylabel("y [m]")
    ax_side.set_xlabel("x [m]")
    ax_side.set_ylabel("z [m]")
    ax_top.legend(loc="upper right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(ORIGIN_PNG, dpi=130, facecolor=SURFACE)
    plt.close(fig)


# ==========================================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--skip-render", action="store_true", help="do not draw the PNGs")
    args = parser.parse_args()
    timings = {}
    t0 = time.perf_counter()
    parts = load_tables()
    meshes = PartMeshes()
    params = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
    levels = json.loads(AUGER_LEVELS_JSON.read_text(encoding="utf-8"))
    timings["load_s"] = time.perf_counter() - t0

    t = time.perf_counter()
    origin = origin_candidates(parts, meshes, params, levels)
    origin["impact_of_change"] = origin_change_impact(params)
    timings["origin_s"] = time.perf_counter() - t

    t = time.perf_counter()
    audit = mass_audit(parts, meshes, levels, origin)
    timings["mass_audit_s"] = time.perf_counter() - t

    t = time.perf_counter()
    imu = imu_candidates(parts, meshes)
    timings["imu_s"] = time.perf_counter() - t

    if not args.skip_render:
        t = time.perf_counter()
        render, _ = load_render_meshes(parts["instance_path"].tolist())
        figure_imu(parts, meshes, render, imu)
        figure_origin(parts, render, origin)
        timings["render_s"] = time.perf_counter() - t

    csv_cols = ["instance_path", "top_assembly", "product_name", "material_resolved",
                "density_step_g_cm3", "density_source", "density_tool_steel_g_cm3",
                "volume_m3", "mesh_area_m2", "equivalent_thickness_mm", "bbox_fill_ratio",
                "mass_step_kg", "mass_generic_as_steel_kg", "mass_tool_steel_kg", "motion",
                "group", "superstructure", "flag_placeholder", "flag_generic_material",
                "flag_density_1", "flag_assumed_steel", "flag_density_invalid",
                "flag_no_solid", "flag_tool_steel_override"]
    table = parts[csv_cols].copy()
    body = np.stack(parts["centroid_body_m"].to_numpy())
    table["centroid_x_body_m_cad_pose"] = body[:, 0]
    table["centroid_y_body_m_cad_pose"] = body[:, 1]
    table["centroid_z_body_m_cad_pose"] = body[:, 2]
    table.sort_values("mass_tool_steel_kg", ascending=False).to_csv(
        OUT_CSV, index=False, encoding="utf-8-sig", float_format="%.6g")

    for cand in imu["candidates"]:
        cand.pop("feasible_centres_body_m", None)
    timings["total_s"] = time.perf_counter() - t0
    report = {
        "frames": {"cad": "mm, Y up", "body": "x = Z_cad, y = X_cad, z = Y_cad, m, origin = "
                   "CAD origin (frames.BODY_ORIGIN_IN_CAD_MM = 0)"},
        "mesh_cache": meshes.meta,
        "origin": origin,
        "mass_audit": audit,
        "imu": imu,
        "timings_s": timings,
    }
    OUT_JSON.write_text(json.dumps(r(report, 6), ensure_ascii=False, indent=1,
                                   default=lambda o: r(o, 6)), encoding="utf-8")
    print(f"wrote {OUT_JSON.name}, {OUT_CSV.name}; timings {r(timings, 1)}")


if __name__ == "__main__":
    main()
