"""Figures of IMU mounting candidate C1 (cross plate in the left deck pontoon under the cabin).

C1 is found by analyze_origin_mass_imu.py (01_cad/01_parts/origin_mass_imu.json,
imu.candidates[0]): top face of the 15 mm cross plate on the left pontoon floor of BASE DECK,
box centre on the face (0.31, 0.88, 0.040) m. The IMU position is not decided; these figures
are for review only.

Reads (cached, no STEP):
    01_cad/01_parts/parts_classified.csv, origin_mass_imu.json
    01_cad/05_meshes/parts_mesh.npz   full tessellation (3 mm deflection) for the crops/sections
    01_cad/05_meshes/render_mesh.npz  decimated meshes for the whole-machine views

Writes:
    01_cad/01_parts/imu_c1_overview.png   where C1 is on the machine (side + top, cabin removed)
    01_cad/01_parts/imu_c1_detail.png     shaded cut-away of the pontoon around C1 with the IMU
                                          box to scale, plan view with clearances (mm)
    01_cad/01_parts/imu_c1_sections.png   side (y = 0.88 m) and front (x = 0.31 m) sections,
                                          full height (ground) and zoomed

Frames: body x = Z_cad, y = X_cad, z = Y_cad in metres, origin = CAD origin (= swing-ring
bolt-circle axis on the deck underside, user decision 2026-10-20). Ground (crawler bottom)
z = -1.0509 m.

Usage:
    python -I 04_scripts/00_cad/render_imu_c1.py
"""

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
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_layout_views as rlv
from analyze_origin_mass_imu import (
    CAB_FOOTPRINT_CAD_MM,
    IMU_ASSUMED_BODY_M,
    IMU_BOX_MM,
    IMU_CLEARANCE_MM,
    OUT_JSON,
    PartMeshes,
    draw_sections,
    to_body_m,
)
from analyze_parts import CAD_TO_BODY, CLASSIFIED_CSV, INK_PRIMARY, LEG_COLORS, SURFACE
from cad_common import MM_PER_M, PARTS_DIR
from render_auger_descent import load_render_meshes

OVERVIEW_PNG = PARTS_DIR / "imu_c1_overview.png"
DETAIL_PNG = PARTS_DIR / "imu_c1_detail.png"
SECTIONS_PNG = PARTS_DIR / "imu_c1_sections.png"

GROUND_Z_M = -1.0509  # rexome33.yaml ground.crawler_bottom_z_m
# Cut-away window around C1 (body m). y > 0.56 drops the right pontoon wall so the
# viewer (front-right, above) looks into the pontoon; z < 0.30 drops the cabin.
CROP_BODY_M = {"x": (-0.90, 1.15), "y": (0.56, 1.40), "z": (-0.03, 0.30)}
# Search windows for the features drawn and dimensioned (CAD mm).
LUG_WINDOW_CAD_MM = {"x": (940.0, 1100.0), "y": (41.0, 160.0), "z": (240.0, 440.0)}
SEAT_LEVEL_CAD_MM = (203.0, 205.0)  # deck-side cabin mount seat plates, top face
PLATE_LEVEL_CAD_MM = 40.0
ISO_TOWARD = np.array([0.55, -0.70, 0.75])  # viewer direction (front, right, above)
COLOURS = {"deck": "#c9c7bf", "plate": "#eda100", "seat": "#1baf7a", "imu": "#eb6834",
           "other": "#a8a7a0", "cab": "#2a78d6"}


# ------------------------------------------------------------------------------------------
# geometry
# ------------------------------------------------------------------------------------------


def body_tris(meshes: PartMeshes, path: str) -> np.ndarray:
    v, f = meshes.arrays(path)
    return (v @ CAD_TO_BODY.T / MM_PER_M)[f]


def up_face_clusters(tris_cad: np.ndarray, level: tuple[float, float]):
    """Union polygons (CAD X, Z) of up-facing triangles whose height lies in level."""
    n = np.cross(tris_cad[:, 1] - tris_cad[:, 0], tris_cad[:, 2] - tris_cad[:, 0])
    area = np.linalg.norm(n, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ny = n[:, 1] / area
    y = tris_cad[:, :, 1].mean(axis=1)
    sel = (ny > 0.9999) & (y >= level[0]) & (y <= level[1])
    union = shapely.union_all([Polygon(t[:, [0, 2]]) for t in tris_cad[sel]])
    return list(union.geoms) if hasattr(union, "geoms") else [union]


def c1_geometry(meshes: PartMeshes, parts: pd.DataFrame, c1: dict) -> dict:
    """Plate, lug, mount seats, cabin floor and horizontal clearances around the C1 box."""
    deck_path = parts.loc[parts["instance_path"].str.endswith("BASE DECK:1"),
                          "instance_path"].iloc[0]
    cab_path = parts.loc[parts["instance_path"].str.contains("Shrinkwrap_11"),
                         "instance_path"].iloc[0]
    v, f = meshes.arrays(deck_path)
    deck = v[f]
    centre = np.asarray(c1["box_centre_on_face_cad_mm"])  # CAD (X, Y, Z)
    half = IMU_BOX_MM[0] / 2
    footprint = box(centre[0] - half, centre[2] - half, centre[0] + half, centre[2] + half)

    plates = [g for g in up_face_clusters(deck, (PLATE_LEVEL_CAD_MM - 0.05,
                                                 PLATE_LEVEL_CAD_MM + 0.05))
              if g.intersects(footprint)]
    plate = shapely.union_all(plates)
    plate_bounds = plate.bounds  # X min, Z min, X max, Z max

    lo = deck.min(axis=1)
    hi = deck.max(axis=1)
    w = LUG_WINDOW_CAD_MM
    lug_sel = ((lo[:, 0] >= w["x"][0]) & (hi[:, 0] <= w["x"][1]) & (lo[:, 1] >= w["y"][0])
               & (hi[:, 1] <= w["y"][1]) & (lo[:, 2] >= w["z"][0]) & (hi[:, 2] <= w["z"][1]))
    lug_pts = deck[lug_sel].reshape(-1, 3)
    lug = {"bbox_cad_mm": [lug_pts.min(axis=0), lug_pts.max(axis=0)]}
    lug_poly = box(lug_pts[:, 0].min(), lug_pts[:, 2].min(), lug_pts[:, 0].max(),
                   lug_pts[:, 2].max())
    lug["gap_to_box_mm"] = footprint.distance(lug_poly)

    seats = [g for g in up_face_clusters(deck, SEAT_LEVEL_CAD_MM) if g.area > 500.0]
    seat_rows = [{"centre_body_m": to_body_m([g.centroid.x, SEAT_LEVEL_CAD_MM[1], g.centroid.y]),
                  "size_mm": [g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]],
                  "area_mm2": g.area} for g in seats]

    cv, cf = meshes.arrays(cab_path)
    cab = cv[cf]
    above = cab[(cab[:, :, 1].min(axis=1) > PLATE_LEVEL_CAD_MM)]
    hits = [t for t in above if Polygon(t[:, [0, 2]]).buffer(0.5).intersects(footprint)]
    cab_floor_y = float(min(t[:, 1].min() for t in hits)) if hits else None

    # nearest obstacles beside the box: any triangle (all parts) in the band
    # plate top ... cabin floor, distance in plan (CAD X-Z)
    near = []
    band = (PLATE_LEVEL_CAD_MM + 0.5, cab_floor_y or PLATE_LEVEL_CAD_MM + 300.0)
    for path in parts["instance_path"]:
        bounds = meshes.bounds(path)
        if bounds is None or bounds[1][1] < band[0] or bounds[0][1] > band[1]:
            continue
        if bounds[1][0] < centre[0] - 600 or bounds[0][0] > centre[0] + 600 \
                or bounds[1][2] < centre[2] - 600 or bounds[0][2] > centre[2] + 600:
            continue
        pv, pf = meshes.arrays(path)
        t = pv[pf]
        keep = (t[:, :, 1].max(axis=1) > band[0]) & (t[:, :, 1].min(axis=1) < band[1])
        if not keep.any():
            continue
        geom = shapely.union_all([Polygon(x[:, [0, 2]]).buffer(0.5) for x in t[keep]])
        dist = footprint.distance(geom)
        if dist < 400.0:
            near.append({"part": path.split(" / ", 1)[-1], "plan_gap_mm": dist})
    near.sort(key=lambda item: item["plan_gap_mm"])

    edges = {  # footprint to plate edges, CAD X = body y, CAD Z = body x
        "to_plate_aft_edge_x_mm": (centre[2] - half) - plate_bounds[1],
        "to_plate_fwd_edge_x_mm": plate_bounds[3] - (centre[2] + half),
        "to_plate_right_edge_y_mm": (centre[0] - half) - plate_bounds[0],
        "to_plate_left_edge_y_mm": plate_bounds[2] - (centre[0] + half),
    }
    return {
        "box_centre_body_m": to_body_m(centre),
        "plate_body_m": {"x": [plate_bounds[1] / MM_PER_M, plate_bounds[3] / MM_PER_M],
                         "y": [plate_bounds[0] / MM_PER_M, plate_bounds[2] / MM_PER_M],
                         "z_top": PLATE_LEVEL_CAD_MM / MM_PER_M},
        "plate_polygon_cad_xz": np.asarray(plate.exterior.coords) if plate.geom_type ==
        "Polygon" else None,
        "lug": lug,
        "seats": seat_rows,
        "cab_floor_z_m": cab_floor_y / MM_PER_M if cab_floor_y else None,
        "free_above_box_top_mm": (cab_floor_y - PLATE_LEVEL_CAD_MM - IMU_BOX_MM[2])
        if cab_floor_y else None,
        "free_above_face_mm": (cab_floor_y - PLATE_LEVEL_CAD_MM) if cab_floor_y else None,
        "edges": edges,
        "nearest_plan_obstacles": near[:8],
    }


# ------------------------------------------------------------------------------------------
# drawing helpers
# ------------------------------------------------------------------------------------------


def iso_axes(toward: np.ndarray):
    toward = toward / np.linalg.norm(toward)
    right = np.cross([0.0, 0.0, 1.0], toward)
    right /= np.linalg.norm(right)
    up = np.cross(toward, right)
    return right, up, toward


def crop_item(tris_body_vertices: np.ndarray, faces: np.ndarray, colour: str):
    """SceneItem of the faces whose three vertices lie inside CROP_BODY_M."""
    v = tris_body_vertices
    inside = np.ones(len(v), dtype=bool)
    for k, axis in enumerate("xyz"):
        lo, hi = CROP_BODY_M[axis]
        inside &= (v[:, k] >= lo) & (v[:, k] <= hi)
    keep = inside[faces].all(axis=1)
    if not keep.any():
        return None
    return rlv.SceneItem(v, rlv.part_topology(v, faces[keep]), colour)


def box_item(centre_body: np.ndarray, extents_m, colour: str):
    mesh = trimesh.creation.box(extents=extents_m)
    v = mesh.vertices + centre_body
    return rlv.SceneItem(v, rlv.part_topology(v, mesh.faces), colour, fade=False)


def box_edges(centre_body, extents_m):
    c = np.asarray(centre_body)
    e = np.asarray(extents_m) / 2
    corners = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    pts = c + corners * e
    pairs = [(i, j) for i in range(8) for j in range(i + 1, 8)
             if np.sum(corners[i] != corners[j]) == 1]
    return pts, pairs


def dim_h(ax, x0, x1, y, text, colour=INK_PRIMARY, fs=7.5):
    ax.annotate("", xy=(x0, y), xytext=(x1, y),
                arrowprops={"arrowstyle": "<->", "color": colour, "lw": 0.8})
    ax.text(0.5 * (x0 + x1), y, text, ha="center", va="bottom", fontsize=fs, color=colour)


def dim_v(ax, x, y0, y1, text, colour=INK_PRIMARY, fs=7.5):
    ax.annotate("", xy=(x, y0), xytext=(x, y1),
                arrowprops={"arrowstyle": "<->", "color": colour, "lw": 0.8})
    ax.text(x, 0.5 * (y0 + y1), " " + text, ha="left", va="center", fontsize=fs, color=colour)


# ------------------------------------------------------------------------------------------
# figures
# ------------------------------------------------------------------------------------------


def figure_overview(parts, render, c1_body, cab_row_mask) -> None:
    fig, (ax_side, ax_top) = plt.subplots(2, 1, figsize=(12, 11.5), facecolor=SURFACE,
                                          gridspec_kw={"height_ratios": [1.5, 1.0]})
    for ax in (ax_side, ax_top):
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")
        ax.set_xlim(-3.3, 4.3)
    ax_side.set_ylim(-1.3, 3.0)
    ax_top.set_ylim(-1.8, 1.8)
    for ax, view in ((ax_side, "side"), (ax_top, "top")):
        items = []
        for row, (vertices, faces) in enumerate(render):
            if cab_row_mask[row] or len(faces) == 0:
                continue
            leg = parts.at[row, "leg"]
            colour = LEG_COLORS.get(leg, COLOURS["other"]) if isinstance(leg, str) \
                else COLOURS["other"]
            if parts.at[row, "instance_path"].endswith("BASE DECK:1"):
                colour = COLOURS["deck"]
            vb = vertices @ CAD_TO_BODY.T / MM_PER_M
            items.append(rlv.SceneItem(vb, rlv.part_topology(vertices, faces), colour))
        ax.add_collection(rlv.scene_collection(
            rlv.shade_scene(items, view, rlv.px_per_metre(ax), rlv.EdgeStyle(), 130)))
    lo = to_body_m([CAB_FOOTPRINT_CAD_MM["x"][0], 235.0, CAB_FOOTPRINT_CAD_MM["z"][0]])
    hi = to_body_m([CAB_FOOTPRINT_CAD_MM["x"][1], 2082.7, CAB_FOOTPRINT_CAD_MM["z"][1]])
    ax_side.add_patch(Rectangle((lo[0], lo[2]), hi[0] - lo[0], hi[2] - lo[2], fill=False,
                                ls="--", lw=1.2, ec=COLOURS["cab"], zorder=6))
    ax_top.add_patch(Rectangle((lo[0], lo[1]), hi[0] - lo[0], hi[1] - lo[1], fill=False,
                               ls="--", lw=1.2, ec=COLOURS["cab"], zorder=6,
                               label="cabin bbox (cabin removed)"))
    a0 = IMU_ASSUMED_BODY_M
    for ax, (h, v) in ((ax_side, (0, 2)), (ax_top, (0, 1))):
        ax.plot(c1_body[h], c1_body[v], "o", ms=11, color=COLOURS["imu"], mec="black",
                zorder=9, label=f"C1 ({c1_body[0]:.2f}, {c1_body[1]:.2f}, {c1_body[2]:.3f}) m")
        ax.plot(a0[h], a0[v], "*", ms=13, color="#d62a2a", mec="white", zorder=9,
                label="assumed (0.20, 0.88, 0.30) m")
    ax_side.axhline(GROUND_Z_M, color="#8c6d46", lw=0.9, ls="--")
    ax_side.text(4.25, GROUND_Z_M + 0.03, "ground (crawler bottom) z = -1.0509 m",
                 ha="right", fontsize=8, color="#8c6d46")
    ax_side.axhline(0.0, color=INK_PRIMARY, lw=0.5, ls=":")
    ax_side.text(4.25, 0.03, "z = 0: deck underside (body origin)", ha="right", fontsize=8)
    ax_side.annotate(f"C1 z = {c1_body[2]:.3f} m\n{c1_body[2] - GROUND_Z_M:.3f} m above ground",
                     xy=(c1_body[0], c1_body[2]), xytext=(1.25, -0.30), fontsize=8,
                     bbox={"fc": "white", "ec": "none", "alpha": 0.85},
                     arrowprops={"arrowstyle": "->", "lw": 0.8})
    ax_side.set_title("side view (x-z), cabin removed; C1 is inside the left deck pontoon "
                      "(seen through the deck side)")
    ax_top.set_title("top view (x-y), cabin removed")
    ax_side.set_xlabel("x [m] (forward)")
    ax_side.set_ylabel("z [m]")
    ax_top.set_xlabel("x [m] (forward)")
    ax_top.set_ylabel("y [m] (left)")
    ax_top.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.suptitle("IMU candidate C1: position on the machine (not decided; for review)",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(OVERVIEW_PNG, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def figure_detail(parts, meshes, geo, c1_body) -> None:
    fig = plt.figure(figsize=(17, 8.6), facecolor=SURFACE)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0])
    ax_iso = fig.add_subplot(grid[0])
    ax_plan = fig.add_subplot(grid[1])
    for ax in (ax_iso, ax_plan):
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")

    # --- iso cut-away (full-resolution meshes cropped to the pontoon) ---
    rlv.VIEWS["iso_c1"] = iso_axes(ISO_TOWARD)
    right, up, _ = rlv.VIEWS["iso_c1"]
    items = []
    seat_xy = [s["centre_body_m"] for s in geo["seats"]]
    for path in parts["instance_path"]:
        bounds = meshes.bounds(path)
        if bounds is None or "BUMA" in path:
            continue
        lo = to_body_m(bounds[0])
        hi = to_body_m(bounds[1])
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        if any(hi[k] < CROP_BODY_M[a][0] or lo[k] > CROP_BODY_M[a][1]
               for k, a in enumerate("xyz")):
            continue
        v, f = meshes.arrays(path)
        vb = v @ CAD_TO_BODY.T / MM_PER_M
        colour = COLOURS["deck"] if path.endswith("BASE DECK:1") else COLOURS["other"]
        item = crop_item(vb, f, colour)
        if item is None:
            continue
        if path.endswith("BASE DECK:1"):  # recolour the cross plate and the mount seats
            tri = vb[item.topology.faces]
            cz = tri[:, :, 2]
            cx, cy = tri[:, :, 0].mean(axis=1), tri[:, :, 1].mean(axis=1)
            pb = geo["plate_body_m"]
            plate_mask = ((cz.min(axis=1) >= 0.0249) & (cz.max(axis=1) >= 0.0399)
                          & (cz.max(axis=1) <= 0.0401)
                          & (cx >= pb["x"][0] - 1e-3) & (cx <= pb["x"][1] + 1e-3)
                          & (cy >= pb["y"][0] - 1e-3) & (cy <= pb["y"][1] + 1e-3))
            seat_mask = (cz.min(axis=1) >= 0.1939) & (cz.max(axis=1) <= 0.2041)
            seat_mask &= np.array([min(np.hypot(px - s[0], py - s[1]) for s in seat_xy) < 0.08
                                   for px, py in zip(cx, cy, strict=True)]) if seat_xy \
                else False
            for mask, colour in ((plate_mask, COLOURS["plate"]), (seat_mask, COLOURS["seat"])):
                if mask.any():
                    faces = item.topology.faces[mask]
                    items.append(rlv.SceneItem(vb, rlv.part_topology(vb, faces), colour))
            rest = item.topology.faces[~(plate_mask | seat_mask)]
            item = rlv.SceneItem(vb, rlv.part_topology(vb, rest), COLOURS["deck"])
        items.append(item)
    imu_extent = np.array(IMU_BOX_MM) / MM_PER_M  # (a, b, h): a along y, b along x
    box_centre = np.array([c1_body[0], c1_body[1], c1_body[2] + imu_extent[2] / 2])
    extents = (imu_extent[1], imu_extent[0], imu_extent[2])
    items.append(box_item(box_centre, extents, COLOURS["imu"]))
    scene = rlv.shade_scene(items, "iso_c1", 900.0, rlv.EdgeStyle(), 150)
    polys = scene[0]
    ax_iso.add_collection(rlv.scene_collection(scene))
    # clearance envelope (box + 10 mm) as a dashed wireframe on top
    clr = IMU_CLEARANCE_MM / MM_PER_M
    env_c = box_centre + np.array([0, 0, clr / 2])
    pts, pairs = box_edges(env_c, (extents[0] + 2 * clr, extents[1] + 2 * clr,
                                   extents[2] + clr))
    scr = np.stack([pts @ right, pts @ up], axis=1)
    for i, j in pairs:
        ax_iso.plot(scr[[i, j], 0], scr[[i, j], 1], ls="--", lw=0.7, color="#d62a2a", zorder=5)
    # cabin floor underside (above C1) as a translucent outline
    cab_path = parts.loc[parts["instance_path"].str.contains("Shrinkwrap_11"),
                         "instance_path"].iloc[0]
    cv, cf = meshes.arrays(cab_path)
    ct = (cv @ CAD_TO_BODY.T / MM_PER_M)[cf]
    n = np.cross(ct[:, 1] - ct[:, 0], ct[:, 2] - ct[:, 0])
    with np.errstate(invalid="ignore", divide="ignore"):
        nz = n[:, 2] / np.linalg.norm(n, axis=1)
    floor = ct[(nz < -0.999) & (ct[:, :, 2].max(axis=1) < 0.37)]
    floor_scr = np.stack([floor @ right, floor @ up], axis=2)
    ax_iso.add_collection(PolyCollection(floor_scr, facecolors=(0.16, 0.47, 0.84, 0.10),
                                         edgecolors="none", zorder=4))
    for label, p, off in (
            ("IMU box 100x100x50 mm\n(dashed: +10 mm clearance)", box_centre, (0.15, 0.20)),
            (f"15 mm cross plate, top z {geo['plate_body_m']['z_top']:.3f} m",
             np.array([geo["plate_body_m"]["x"][0], 0.65, 0.04]), (-0.25, -0.14)),
            ("pin lug on the plate", to_body_m(np.mean(geo["lug"]["bbox_cad_mm"], axis=0)),
             (0.25, 0.10)),
            ("cabin mount seat (deck side)\ntop z 0.204 m",
             geo["seats"][0]["centre_body_m"] if geo["seats"] else box_centre, (0.10, 0.18)),
            ("C-channel wall (pontoon left side)", np.array([-0.4, 1.30, 0.20]),
             (-0.10, 0.20)),
            ("pontoon floor: 2.3 mm perforated sheet", np.array([-0.5, 0.95, 0.025]),
             (-0.05, -0.18))):
        s = np.array([p @ right, p @ up])
        ax_iso.annotate(label, xy=s, xytext=s + np.array(off), fontsize=8,
                        arrowprops={"arrowstyle": "->", "lw": 0.7}, zorder=8)
    allp = polys.reshape(-1, 2)
    ax_iso.set_xlim(allp[:, 0].min() - 0.05, allp[:, 0].max() + 0.05)
    ax_iso.set_ylim(allp[:, 1].min() - 0.25, allp[:, 1].max() + 0.30)
    ax_iso.set_xticks([])
    ax_iso.set_yticks([])
    ax_iso.set_title("cut-away of the left deck pontoon under the cabin (cabin removed, "
                     "right wall cut at y 0.56 m;\nblue tint = cabin floor underside), "
                     "view from front-right above, orthographic")

    # --- plan view with clearances (mm) ---
    window = ((c1_body[0] - 0.35, c1_body[0] + 0.35), (0.50, 1.36))
    items = []
    for path in parts["instance_path"]:
        bounds = meshes.bounds(path)
        if bounds is None or "BUMA" in path:
            continue
        lo = to_body_m(bounds[0])
        hi = to_body_m(bounds[1])
        if hi[0] < window[0][0] or lo[0] > window[0][1] or hi[1] < window[1][0] \
                or lo[1] > window[1][1] or lo[2] > 0.30:
            continue
        v, f = meshes.arrays(path)
        vb = v @ CAD_TO_BODY.T / MM_PER_M
        keep = (vb[f][:, :, 2].max(axis=1) <= 0.30)
        if keep.any():
            colour = COLOURS["deck"] if path.endswith("BASE DECK:1") else COLOURS["other"]
            items.append(rlv.SceneItem(vb, rlv.part_topology(vb, f[keep]), colour))
    ax_plan.set_xlim(*window[0])
    ax_plan.set_ylim(*window[1])
    ax_plan.add_collection(rlv.scene_collection(
        rlv.shade_scene(items, "top", rlv.px_per_metre(ax_plan), rlv.EdgeStyle(), 150)))
    a, b = IMU_BOX_MM[0] / MM_PER_M, IMU_BOX_MM[1] / MM_PER_M
    x0, y0 = c1_body[0] - b / 2, c1_body[1] - a / 2
    ax_plan.add_patch(Rectangle((x0, y0), b, a, fc=COLOURS["imu"], ec="black", lw=0.8,
                                zorder=6, alpha=0.9))
    ax_plan.add_patch(Rectangle((x0 - clr, y0 - clr), b + 2 * clr, a + 2 * clr, fill=False,
                                ec="#d62a2a", ls="--", lw=0.8, zorder=6))
    pb = geo["plate_body_m"]
    ax_plan.add_patch(Rectangle((pb["x"][0], pb["y"][0]), pb["x"][1] - pb["x"][0],
                                pb["y"][1] - pb["y"][0], fill=False, ec=COLOURS["plate"],
                                lw=1.6, zorder=5, label="15 mm cross plate (top z 0.040 m)"))
    lug_lo = to_body_m(geo["lug"]["bbox_cad_mm"][0])
    lug_hi = to_body_m(geo["lug"]["bbox_cad_mm"][1])
    ax_plan.add_patch(Rectangle((lug_lo[0], lug_lo[1]), lug_hi[0] - lug_lo[0],
                                lug_hi[1] - lug_lo[1], fc="#7a3fc4", ec="black", lw=0.6,
                                alpha=0.7, zorder=6,
                                label=f"pin lug (z up to {lug_hi[2]:.3f} m)"))
    for seat in geo["seats"]:
        c = seat["centre_body_m"]
        sx, sy = seat["size_mm"][1] / MM_PER_M, seat["size_mm"][0] / MM_PER_M
        ax_plan.add_patch(Rectangle((c[0] - sx / 2, c[1] - sy / 2), sx, sy,
                                    fc=COLOURS["seat"], ec="black", lw=0.5, alpha=0.8,
                                    zorder=6))
    ax_plan.plot([], [], "s", color=COLOURS["seat"], label="cabin mount seats (z 0.204 m)")
    ax_plan.plot(IMU_ASSUMED_BODY_M[0], IMU_ASSUMED_BODY_M[1], "*", ms=13, color="#d62a2a",
                 mec="white", zorder=7, label="assumed point (z 0.30 m, no face there)")
    e = geo["edges"]
    dim_h(ax_plan, pb["x"][0], x0, c1_body[1] + 0.07, f"{e['to_plate_aft_edge_x_mm']:.0f}")
    dim_h(ax_plan, x0 + b, pb["x"][1], c1_body[1] + 0.07, f"{e['to_plate_fwd_edge_x_mm']:.0f}")
    dim_v(ax_plan, c1_body[0] + 0.10, lug_lo[1], y0 + a,
          f"{geo['lug']['gap_to_box_mm']:.0f} to lug")
    dim_v(ax_plan, c1_body[0] - 0.10, pb["y"][0], y0, f"{e['to_plate_right_edge_y_mm']:.0f}")
    ax_plan.text(c1_body[0], c1_body[1], "IMU\n100x100", ha="center", va="center",
                 fontsize=7, zorder=8)
    ax_plan.set_title("plan view (x-y), parts below z 0.30 m; dimensions in mm\n"
                      f"free height above the face {geo['free_above_face_mm']:.0f} mm "
                      f"(above the box {geo['free_above_box_top_mm']:.0f} mm) to the cabin "
                      f"floor z {geo['cab_floor_z_m']:.3f} m")
    ax_plan.set_xlabel("x [m] (forward)")
    ax_plan.set_ylabel("y [m] (left)")
    ax_plan.legend(loc="lower left", fontsize=7.5, framealpha=0.9)
    fig.suptitle(f"IMU candidate C1 on the BASE DECK cross plate: box centre on the face "
                 f"({c1_body[0]:.2f}, {c1_body[1]:.2f}, {c1_body[2]:.3f}) m (not decided)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(DETAIL_PNG, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def figure_sections(parts, meshes, geo, c1_body) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(17, 11), facecolor=SURFACE,
                             gridspec_kw={"width_ratios": [1.5, 1.0]})
    a, b, h = (x / MM_PER_M for x in IMU_BOX_MM)
    clr = IMU_CLEARANCE_MM / MM_PER_M
    lug_lo = to_body_m(geo["lug"]["bbox_cad_mm"][0])
    lug_hi = to_body_m(geo["lug"]["bbox_cad_mm"][1])
    specs = [  # axis (CAD), value, h, v, window (body m), horizontal body index, title
        (0, c1_body[1], 2, 1, ((-2.0, 2.6), (-1.15, 0.6)), 0,
         f"side section y = {c1_body[1]:.2f} m"),
        (2, c1_body[0], 0, 1, ((-1.45, 1.45), (-1.15, 0.6)), 1,
         f"front section x = {c1_body[0]:.2f} m"),
        (0, c1_body[1], 2, 1, ((-0.30, 0.95), (-0.05, 0.42)), 0, "zoom"),
        (2, c1_body[0], 0, 1, ((0.35, 1.38), (-0.05, 0.42)), 1, "zoom"),
    ]
    order = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for (axis, value_m, hh, vv, win, hidx, title), (r_, c_) in zip(specs, order, strict=True):
        ax = axes[r_, c_]
        ax.set_facecolor(SURFACE)
        ax.set_aspect("equal")
        win_mm = ((win[0][0] * MM_PER_M, win[0][1] * MM_PER_M),
                  (win[1][0] * MM_PER_M, win[1][1] * MM_PER_M))
        draw_sections(ax, meshes, parts, axis, value_m * MM_PER_M, hh, vv, win_mm)
        ax.set_xlim(*win[0]) if hidx == 0 else ax.set_xlim(win[0][1], win[0][0])
        ax.set_ylim(*win[1])
        width = b if hidx == 0 else a
        hpos = c1_body[hidx]
        ax.add_patch(Rectangle((hpos - width / 2, c1_body[2]), width, h, fc=COLOURS["imu"],
                               ec="black", lw=0.6, zorder=6))
        ax.add_patch(Rectangle((hpos - width / 2 - clr, c1_body[2]), width + 2 * clr, h + clr,
                               fill=False, ec="#d62a2a", ls="--", lw=0.7, zorder=6))
        ax.axhline(GROUND_Z_M, color="#8c6d46", lw=0.9, ls="--")
        ax.plot(IMU_ASSUMED_BODY_M[hidx], IMU_ASSUMED_BODY_M[2], "*", ms=12, color="#d62a2a",
                mec="white", zorder=7, label="assumed (0.20, 0.88, 0.30) m")
        ax.plot(c1_body[hidx], c1_body[2], "o", ms=5, color="black", zorder=7,
                label=f"C1 face point ({c1_body[0]:.2f}, {c1_body[1]:.2f}, {c1_body[2]:.3f}) m")
        lug_h = (lug_lo[hidx], lug_hi[hidx])
        ax.add_patch(Rectangle((min(lug_h), lug_lo[2]), abs(lug_h[1] - lug_h[0]),
                               lug_hi[2] - lug_lo[2], fill=False, ec="#7a3fc4", lw=1.2,
                               zorder=6, label="pin lug bbox (projected)"))
        ax.grid(True, lw=0.2)
        if title == "zoom":
            top = c1_body[2] + h
            floor = geo["cab_floor_z_m"]
            xd = hpos + width / 2 + 0.06 if hidx == 0 else hpos - width / 2 - 0.06
            dim_v(ax, xd, top, floor, f"{(floor - top) * MM_PER_M:.0f} mm to cabin floor")
            dim_v(ax, hpos + (0.12 if hidx == 0 else -0.12), c1_body[2], floor,
                  f"{(floor - c1_body[2]) * MM_PER_M:.0f} mm face to floor")
            ax.axhline(0.204, color=COLOURS["seat"], lw=0.8, ls=":")
            ax.text(win[0][0] if hidx == 0 else win[0][1], 0.207, " mount seat top z 0.204 m",
                    fontsize=7.5, color=COLOURS["seat"], ha="left")
            ax.set_title(f"{'side' if hidx == 0 else 'front'} section zoom; "
                         "orange = IMU box, dashed = +10 mm clearance")
        else:
            ax.text(win[0][0] + 0.05 if hidx == 0 else win[0][1] - 0.05, GROUND_Z_M + 0.03,
                    "ground (crawler bottom) z -1.0509 m", fontsize=8, color="#8c6d46")
            dim_v(ax, hpos + (0.25 if hidx == 0 else -0.25), GROUND_Z_M, c1_body[2],
                  f"{(c1_body[2] - GROUND_Z_M) * MM_PER_M:.0f} mm above ground")
            ax.set_title(f"{title} (black deck, blue cabin, brown crawler)")
            ax.legend(loc="upper right", fontsize=7.5, framealpha=0.9)
        ax.set_xlabel("x [m] (forward)" if hidx == 0 else "y [m] (left, +y on the left)")
        ax.set_ylabel("z [m]")
    fig.suptitle("IMU candidate C1: sections through the box centre (not decided)", fontsize=12)
    fig.tight_layout()
    fig.savefig(SECTIONS_PNG, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    t0 = time.perf_counter()
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    report = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    c1 = next(c for c in report["imu"]["candidates"] if c["id"] == "C1")
    c1_body = np.asarray(c1["box_centre_on_face_body_m"])
    meshes = PartMeshes()
    geo = c1_geometry(meshes, parts, c1)
    summary = {k: v for k, v in geo.items() if k != "plate_polygon_cad_xz"}
    print(json.dumps(summary, default=lambda o: np.round(np.asarray(o, dtype=float), 4)
                     .tolist(), ensure_ascii=False, indent=1))
    t1 = time.perf_counter()
    figure_sections(parts, meshes, geo, c1_body)
    t2 = time.perf_counter()
    figure_detail(parts, meshes, geo, c1_body)
    t3 = time.perf_counter()
    render, _ = load_render_meshes(parts["instance_path"].tolist())
    cab_rows = parts["instance_path"].str.contains("BUMA").to_numpy()
    figure_overview(parts, render, c1_body, cab_rows)
    t4 = time.perf_counter()
    print(f"geometry {t1 - t0:.1f} s, sections {t2 - t1:.1f} s, detail {t3 - t2:.1f} s, "
          f"overview {t4 - t3:.1f} s")


if __name__ == "__main__":
    main()
