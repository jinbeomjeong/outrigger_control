"""Figures of the crawler contact parts of layout D (rollers + gapped end shoes).

Layout D (CLAUDE.md '크롤러 접촉 배치', 00_docs/01_dynamics/dynamics_model.md 3.8): per track
6 roller stations (contact sphere bottom on the floor) and 3 raised end shoes per end
(sphere bottom = floor + end_shoe_gap_m). The parts are the B-rep caches written by
derive_crawler_parts.py; the 10 flat shoes per track (under the rollers, on the floor) are
drawn as well in a neutral colour because they are where the roller load actually reaches
the floor (pinned link chain), but they carry no contact sphere of their own.

Reads (cached, no STEP):
    01_cad/06_brep/derived/crawler/crawler_contact_parts.csv   part table (kind, side, order,
                                                                 gap, file)
    01_cad/06_brep/derived/crawler/parts/*.bbrep                44 part B-reps (CAD world, mm)
    01_cad/06_brep/derived/crawler/crawler_lowres.obj           decimated whole crawler (grey
                                                                 context, optional)
    02_params/rexome33.yaml   contact.crawler.sphere_layout (24 contact spheres, via
                              crawler_contact.layout_from_mapping), ground.crawler_bottom_z_m

Writes:
    01_cad/06_brep/derived/crawler/crawler_contact_parts_views.png   side (from -y), front
        (from +x), bottom (from below) and isometric view, contact spheres overlaid
    01_cad/06_brep/derived/crawler/crawler_contact_parts_gap_detail.png   end-shoe gaps to the
        floor (rear and front end, side view, true scale), CAD gap vs YAML sphere bottoms

Frames: body x = Z_cad (forward), y = X_cad (left), z = Y_cad (up), metres, origin = CAD
origin. Ground (crawler bottom) z = ground.crawler_bottom_z_m = -1.0509 m.

Method: every part is meshed with BRepMesh_IncrementalMesh (absolute linear deflection
--linear-mm, angular --angular-rad), welded by trimesh (STL round trip), and drawn with the
painter-sorted shading and hidden-line outlines of render_layout_views.py. The context
crawler is drawn in a separate, lower layer (it never hides a contact part). The gap labels
come from the meshed parts (lowest vertex of the grouser side, i.e. tessellation of the
B-rep) and are compared with the CSV gap (B-rep) and the YAML sphere bottoms.

Usage:
    python -I 04_scripts/00_cad/render_crawler_contact_parts.py [--dpi 150]
        [--linear-mm 1.0] [--angular-rad 0.5] [--no-context]
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import trimesh
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_layout_views as rlv
from analyze_parts import INK_PRIMARY, INK_SECONDARY, SURFACE
from brep_cache import CRAWLER_PARTS_CSV, read_brep
from cad_common import PROJECT_ROOT
from crawler_contact import LAYOUT_PATH, layout_from_mapping

CRAWLER_DIR = CRAWLER_PARTS_CSV.parent
LOWRES_OBJ = CRAWLER_DIR / "crawler_lowres.obj"
PARAMS_YAML = PROJECT_ROOT / "02_params" / "rexome33.yaml"
OUT_VIEWS = CRAWLER_DIR / "crawler_contact_parts_views.png"
OUT_GAP = CRAWLER_DIR / "crawler_contact_parts_gap_detail.png"

KIND_COLOURS = {"roller": "#2a78d6", "end_shoe": "#eb6834", "flat_shoe": "#c4bfae"}
KIND_LABELS = {
    "roller": "track roller (contact sphere, gap 0)",
    "end_shoe": "end shoe, gapped (contact sphere at floor + gap)",
    "flat_shoe": "flat shoe on the floor (no sphere; carries the roller load)",
}
CONTEXT_COLOUR = "#dad9d4"
POINT_COLOUR = "#0b0b0b"
SPHERE_COLOUR = "#7a2fb3"
# (screen right, screen up, toward viewer) in body axes, right x up = toward.
EXTRA_VIEWS = {
    "bottom": (np.array([1.0, 0, 0]), np.array([0, -1.0, 0]), np.array([0, 0, -1.0])),
}


def iso_view(azimuth_deg: float = -40.0, elevation_deg: float = 25.0):
    """Viewer direction from azimuth (from +x toward +y) and elevation; returns the triad."""
    az, el = np.radians(azimuth_deg), np.radians(elevation_deg)
    toward = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.cross([0.0, 0.0, 1.0], toward)
    right /= np.linalg.norm(right)
    up = np.cross(toward, right)
    return right, up, toward


def mesh_shape(shape, linear_mm: float, angular_rad: float, work: Path):
    """Welded triangle mesh of a B-rep shape (vertices in the shape frame, mm)."""
    BRepMesh_IncrementalMesh(shape, linear_mm, False, angular_rad, True)
    path = work / "part.stl"
    writer = StlAPI_Writer()
    writer.SetASCIIMode(False)
    if not writer.Write(shape, str(path)):
        raise RuntimeError("STL write failed")
    mesh = trimesh.load_mesh(str(path), file_type="stl", process=True)
    return np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.int64)


def load_parts(linear_mm: float, angular_rad: float) -> pd.DataFrame:
    """Part table with body-frame meshes (columns vertices_m, faces, topology)."""
    table = pd.read_csv(CRAWLER_PARTS_CSV, encoding="utf-8-sig")
    vertices, faces, topologies = [], [], []
    with tempfile.TemporaryDirectory() as work_dir:
        for file in table["file"]:
            shape = read_brep(PROJECT_ROOT / file)
            v_mm, f = mesh_shape(shape, linear_mm, angular_rad, Path(work_dir))
            v_m = rlv.body_vertices(v_mm)
            vertices.append(v_m)
            faces.append(f)
            topologies.append(rlv.part_topology(v_m, f))
    table["vertices_m"] = vertices
    table["faces"] = faces
    table["topology"] = topologies
    return table


def load_context():
    """Decimated whole crawler (CAD mm -> body m), or None."""
    if not LOWRES_OBJ.exists():
        return None
    mesh = trimesh.load_mesh(str(LOWRES_OBJ), process=True)
    v_m = rlv.body_vertices(np.asarray(mesh.vertices))
    f = np.asarray(mesh.faces, dtype=np.int64)
    return v_m, f, rlv.part_topology(v_m, f)


def scene_items(parts: pd.DataFrame, mask=None) -> list:
    rows = parts if mask is None else parts[mask]
    return [rlv.SceneItem(r.vertices_m, r.topology, KIND_COLOURS[r.kind])
            for r in rows.itertuples()]


def project(points: np.ndarray, view: str) -> np.ndarray:
    right, up, _ = rlv.VIEWS[view]
    screen = np.stack([points @ right, points @ up], axis=-1)
    if view == "bottom":  # plotted as (x, y) with an inverted y axis (true view from below)
        screen[..., 1] *= -1
    return screen


def add_scene(ax, items, view, style, dpi, zorder, alpha=1.0, depth_fade=True):
    scene = rlv.shade_scene(items, view, rlv.px_per_metre(ax), style, dpi, depth_fade)
    polygons, face_rgba, edge_rgba, widths, edge = scene
    if view == "bottom":
        polygons = polygons.copy()
        polygons[..., 1] *= -1
    if alpha < 1.0:
        face_rgba = face_rgba.copy()
        face_rgba[:, 3] *= alpha
        edge_rgba = edge_rgba.copy()
        edge_rgba[:, 3] *= alpha
    ax.add_collection(rlv.scene_collection((polygons, face_rgba, edge_rgba, widths, edge),
                                           zorder), autolim=False)
    return int(edge.sum())


def style_axes(ax, title: str, xlabel: str | None, ylabel: str | None) -> None:
    ax.set_aspect("equal")
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK_PRIMARY, fontsize=10.5, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_SECONDARY)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_SECONDARY)
    ax.tick_params(colors=INK_SECONDARY, labelsize=8.5)
    ax.grid(True, color="#e6e5e0", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color("#c9c8c2")


def draw_points(ax, view, layout, floor_z, radius, circles: bool) -> None:
    """Sphere centres (dots), sphere outlines (circles) and bottoms (ticks) of the 24 spheres."""
    centres = layout.sphere_centres_m(floor_z)
    bottoms = layout.bottoms_m(floor_z)
    roller = layout.is_roller
    c2, b2 = project(centres, view), project(bottoms, view)
    if circles:
        for (cx, cy) in c2:
            ax.add_patch(Circle((cx, cy), radius, fill=False, edgecolor=SPHERE_COLOUR,
                                linewidth=0.7, linestyle=(0, (3, 2)), zorder=6))
    ax.plot(c2[roller, 0], c2[roller, 1], "o", ms=4.5, color=POINT_COLOUR, mec="white",
            mew=0.7, zorder=8, linestyle="none")
    ax.plot(c2[~roller, 0], c2[~roller, 1], "D", ms=4.2, color=SPHERE_COLOUR, mec="white",
            mew=0.7, zorder=8, linestyle="none")
    if view != "bottom" and view != "iso":
        ax.plot(b2[:, 0], b2[:, 1], "_", ms=7, color=SPHERE_COLOUR, mew=1.2, zorder=8,
                linestyle="none")


def limits(points2: np.ndarray, pad: float):
    lo, hi = points2.min(axis=0) - pad, points2.max(axis=0) + pad
    return (lo[0], hi[0]), (lo[1], hi[1])


def draw_views(parts, context, layout, floor_z, dpi, style) -> dict:
    radius = layout.sphere_radius_m
    figure = plt.figure(figsize=(17, 11.5), facecolor=SURFACE)
    grid = figure.add_gridspec(2, 2, width_ratios=[2.15, 1.0], height_ratios=[1.0, 1.0],
                               left=0.05, right=0.985, top=0.925, bottom=0.10,
                               wspace=0.10, hspace=0.20)
    axes = {
        "side": figure.add_subplot(grid[0, 0]),
        "front": figure.add_subplot(grid[0, 1]),
        "bottom": figure.add_subplot(grid[1, 0]),
        "iso": figure.add_subplot(grid[1, 1]),
    }
    all_parts = np.concatenate(parts["vertices_m"].tolist())
    context_v = context[0] if context is not None else all_parts
    # Context crawler extends upward; show it up to its top, parts set the lower bound.
    ranges = {}
    for view in ("side", "front", "bottom"):
        p2 = project(all_parts, view)
        c2 = project(context_v, view)
        both = np.concatenate([p2, c2])
        (x0, x1), (y0, y1) = limits(both, 0.06)
        if view in ("side", "front"):
            y0 = min(y0, floor_z - 0.05)
        ranges[view] = ((x0, x1), (y0, y1))
    titles = {
        "side": ("Side view (x-z) from the right (-y): right track in front", "x (m)",
                 "z (m)"),
        "front": ("Front view (y-z) from the front (+x)", "y (m)", "z (m)"),
        "bottom": ("Bottom view (x-y) from below (+y down the page = left track at bottom)",
                   "x (m)", "y (m)"),
        "iso": ("Isometric view from front-right, 25 deg above (no scale)", None, None),
    }
    for view, ax in axes.items():
        style_axes(ax, *titles[view])
    for view in ("side", "front", "bottom"):
        ax = axes[view]
        ax.set_xlim(*ranges[view][0])
        ax.set_ylim(*ranges[view][1])
        if view == "bottom":
            ax.invert_yaxis()
    # isometric limits from the projected context + parts
    iso2 = np.concatenate([project(all_parts, "iso"), project(context_v, "iso")])
    (ix0, ix1), (iy0, iy1) = limits(iso2, 0.08)
    axes["iso"].set_xlim(ix0, ix1)
    axes["iso"].set_ylim(iy0, iy1)
    axes["iso"].set_xticks([])
    axes["iso"].set_yticks([])
    axes["iso"].grid(False)

    figure.set_dpi(dpi)
    outline_counts = {}
    for view, ax in axes.items():
        if context is not None:
            ctx_item = rlv.SceneItem(context[0], context[2], CONTEXT_COLOUR)
            add_scene(ax, [ctx_item], view, rlv.EdgeStyle(enabled=False), dpi, zorder=1.5,
                      alpha=0.85, depth_fade=False)
        outline_counts[view] = add_scene(ax, scene_items(parts), view, style, dpi, zorder=2.0)
        draw_points(ax, view, layout, floor_z, radius, circles=view != "iso")
        if view in ("side", "front"):
            ax.axhline(floor_z, color=INK_SECONDARY, linestyle="--", linewidth=0.9, zorder=7)
            x_text = ax.get_xlim()[0] + 0.02 * np.diff(ax.get_xlim())[0]
            ax.text(x_text, floor_z - 0.012, f"ground z = {floor_z:.4f} m", va="top",
                    ha="left", fontsize=8, color=INK_SECONDARY, zorder=9)
    # iso: ground rectangle under the footprint and an axis triad
    ax = axes["iso"]
    lo, hi = all_parts.min(axis=0), all_parts.max(axis=0)
    corners = np.array([[lo[0] - 0.1, lo[1] - 0.1], [hi[0] + 0.1, lo[1] - 0.1],
                        [hi[0] + 0.1, hi[1] + 0.1], [lo[0] - 0.1, hi[1] + 0.1],
                        [lo[0] - 0.1, lo[1] - 0.1]])
    ground3 = np.column_stack([corners, np.full(len(corners), floor_z)])
    g2 = project(ground3, "iso")
    ax.plot(g2[:, 0], g2[:, 1], "--", color=INK_SECONDARY, linewidth=0.9, zorder=1.4)
    ax.text(g2[1, 0], g2[1, 1] - 0.03, f"ground z = {floor_z:.4f} m", fontsize=8,
            color=INK_SECONDARY, ha="center", va="top")
    origin2 = np.array([ix0 + 0.12 * (ix1 - ix0), iy0 + 0.80 * (iy1 - iy0)])
    for axis, name in zip(np.eye(3), "xyz", strict=True):
        tip = project(axis * 0.4, "iso")
        ax.annotate("", origin2 + tip, origin2, arrowprops={"arrowstyle": "-|>", "lw": 1.0,
                                                          "color": INK_PRIMARY})
        ax.text(*(origin2 + tip * 1.18), name, fontsize=9, color=INK_PRIMARY, ha="center",
                va="center")
    ax.text(origin2[0] - 0.05, origin2[1] + 0.50, "axes 0.4 m", fontsize=7.5, color=INK_SECONDARY,
            ha="center")

    handles = [Rectangle((0, 0), 1, 1, facecolor=KIND_COLOURS[k], edgecolor="black",
                         linewidth=0.4) for k in ("roller", "end_shoe", "flat_shoe")]
    labels = [KIND_LABELS[k] for k in ("roller", "end_shoe", "flat_shoe")]
    if context is not None:
        handles.append(Rectangle((0, 0), 1, 1, facecolor=CONTEXT_COLOUR))
        labels.append("rest of the crawler (decimated, drawn behind)")
    handles += [
        Line2D([], [], marker="o", ms=5, color=POINT_COLOUR, mec="white", linestyle="none"),
        Line2D([], [], marker="D", ms=5, color=SPHERE_COLOUR, mec="white", linestyle="none"),
        Line2D([], [], color=SPHERE_COLOUR, linestyle=(0, (3, 2)), linewidth=0.8),
        Line2D([], [], marker="_", ms=8, mew=1.2, color=SPHERE_COLOUR, linestyle="none"),
        Line2D([], [], color=INK_SECONDARY, linestyle="--", linewidth=0.9),
    ]
    labels += [
        "roller sphere centre (12)",
        "end-shoe sphere centre (12)",
        f"contact sphere r = {radius * 1000:.0f} mm",
        "sphere bottom (floor + gap)",
        "ground (crawler bottom)",
    ]
    figure.legend(handles, labels, loc="lower center", ncol=5, frameon=False, fontsize=9,
                  labelcolor=INK_SECONDARY)
    figure.suptitle(
        "Crawler contact parts, layout D: 6 roller stations per track + 3 gapped end shoes "
        "per end, 24 contact spheres from 02_params/rexome33.yaml\n"
        "body frame (x forward = Z_cad, y left = X_cad, z up = Y_cad), m; parts = B-rep cache "
        "01_cad/06_brep/derived/crawler/parts (undercarriage drawn as REXOME25)",
        color=INK_PRIMARY, fontsize=11.5)
    figure.savefig(OUT_VIEWS, dpi=dpi, facecolor=SURFACE)
    plt.close(figure)
    return {"outline_segments": outline_counts,
            "axis_limits_m": {k: [list(map(lambda v: round(float(v), 3), a)) for a in r]
                              for k, r in ranges.items()}}


def gap_rows(parts: pd.DataFrame, layout, floor_z: float, side: str) -> list[dict]:
    """End shoes of one side: lowest mesh point vs CSV gap vs YAML sphere bottom."""
    shoes = parts[(parts["kind"] == "end_shoe") & (parts["side"] == side)]
    shoes = shoes.sort_values("order_index")
    mask = np.array([(k == "end_shoe") and (s == side)
                     for k, s in zip(layout.kind, layout.side, strict=True)])
    yaml_x = layout.xy_m[mask, 0]
    yaml_gap = layout.gap_m[mask]
    rows = []
    for (row, x_yaml, g_yaml) in zip(shoes.itertuples(), yaml_x, yaml_gap, strict=True):
        v = row.vertices_m
        low = int(np.argmin(v[:, 2]))
        rows.append({
            "part_id": row.part_id,
            "lowest_x_m": float(v[low, 0]),
            "mesh_gap_mm": float((v[low, 2] - floor_z) * 1000),
            "csv_gap_mm": float(row.gap_m * 1000),
            "csv_lowest_above_ground_mm": float(row.lowest_above_ground_mm),
            "yaml_x_m": float(x_yaml),
            "yaml_gap_mm": float(g_yaml * 1000),
            "part_x_range_m": [float(v[:, 0].min()), float(v[:, 0].max())],
        })
    return rows


def draw_gap_profile(ax, track, rows, layout, side, floor_z) -> None:
    """Lowest point above the floor [mm] of every part of one track (B-rep, CSV) vs x, with
    the YAML sphere bottoms (vertical axis exaggerated, horizontal = part x extent)."""
    for row in track.itertuples():
        if row.kind == "roller":
            continue
        low = float(row.lowest_above_ground_mm)
        ax.hlines(low, row.bbox_min_x_body_m, row.bbox_max_x_body_m,
                  color=KIND_COLOURS[row.kind], linewidth=4.0, zorder=3,
                  )
    for r in rows:
        ax.plot(r["lowest_x_m"], r["mesh_gap_mm"], "x", color=INK_PRIMARY, ms=6, zorder=5)
    mask = np.array([s == side for s in layout.side])
    xy, gap, roller = layout.xy_m[mask], layout.gap_m[mask], layout.is_roller[mask]
    ax.plot(xy[roller, 0], gap[roller] * 1000, "o", ms=5, color=POINT_COLOUR, mec="white",
            zorder=6)
    ax.plot(xy[~roller, 0], gap[~roller] * 1000, "D", ms=5, color=SPHERE_COLOUR, mec="white",
            zorder=6)
    rollers = track[track["kind"] == "roller"]
    for row in rollers.itertuples():
        ax.axvspan(row.bbox_min_x_body_m, row.bbox_max_x_body_m, color=KIND_COLOURS["roller"],
                   alpha=0.10, zorder=1, linewidth=0)
    ax.axhline(0.0, color=INK_SECONDARY, linestyle="--", linewidth=0.9)
    style_axes(ax, f"Lowest point above the floor along track {side} (vertical scale "
               "exaggerated)\n"
               "bars = part x extent at its lowest height (CSV), x = lowest "
               "mesh point, markers = YAML sphere bottoms, blue bands = roller x extent",
               "x (m)", "height above floor (mm)")
    ax.set_aspect("auto")
    ax.set_ylim(-2.0, 25.0)
    ax.set_xlim(-1.55, 1.55)


def draw_gap_detail(parts, layout, floor_z, dpi, style, side="R") -> dict:
    """Side view (from -y) of one track's ends, true scale, gaps annotated."""
    track = parts[parts["side"] == side]
    rows = gap_rows(parts, layout, floor_z, side)
    figure, all_axes = plt.subplots(3, 1, figsize=(15, 10.2), facecolor=SURFACE,
                                    gridspec_kw={"height_ratios": [1.0, 1.0, 0.75]})
    axes, profile = all_axes[:2], all_axes[2]
    radius = layout.sphere_radius_m
    side_mask = np.array([s == side for s in layout.side])
    centres = layout.sphere_centres_m(floor_z)[side_mask]
    bottoms = layout.bottoms_m(floor_z)[side_mask]
    roller = layout.is_roller[side_mask]
    end_x = np.array([r["yaml_x_m"] for r in rows])
    panels = (("rear", end_x[end_x < 0]), ("front", end_x[end_x > 0]))
    for ax, (name, xs) in zip(axes, panels, strict=True):
        x0, x1 = xs.min() - 0.30, xs.max() + 0.30
        if name == "rear":
            x0 = xs.min() - 0.22
            x1 = xs.max() + 0.40
        else:
            x0 = xs.min() - 0.40
            x1 = xs.max() + 0.22
        style_axes(ax, f"{name.capitalize()} end, track {side} "
                   f"({'right, y = -1.045 m' if side == 'R' else 'left'}), seen from -y, "
                   "true scale", "x (m)", "z (m)")
        ax.set_xlim(x0, x1)
        ax.set_ylim(floor_z - 0.035, floor_z + 0.20)
        figure.set_dpi(dpi)
        in_window = track[[bool((v[:, 0].max() > x0) and (v[:, 0].min() < x1))
                           for v in track["vertices_m"]]]
        add_scene(ax, scene_items(in_window), "side", style, dpi, zorder=2.0)
        ax.axhline(floor_z, color=INK_SECONDARY, linestyle="--", linewidth=0.9, zorder=7)
        ax.text(x0 + 0.01, floor_z - 0.004, f"ground z = {floor_z:.4f} m", va="top",
                fontsize=8, color=INK_SECONDARY)
        for c, b, is_r in zip(centres, bottoms, roller, strict=True):
            if not (x0 < c[0] < x1):
                continue
            ax.add_patch(Circle((c[0], c[2]), radius, fill=False, edgecolor=SPHERE_COLOUR,
                                linewidth=0.8, linestyle=(0, (3, 2)), zorder=6))
            ax.plot(c[0], c[2], "o" if is_r else "D", ms=5, mec="white", mew=0.7,
                    color=POINT_COLOUR if is_r else SPHERE_COLOUR, zorder=8)
            ax.plot(b[0], b[2], "_", ms=9, mew=1.4, color=SPHERE_COLOUR, zorder=8)
        for r in rows:
            if not (x0 < r["lowest_x_m"] < x1):
                continue
            x, gap = r["lowest_x_m"], r["mesh_gap_mm"] / 1000
            ax.annotate("", (x, floor_z), (x, floor_z + gap),
                        arrowprops={"arrowstyle": "<->", "lw": 0.9, "color": INK_PRIMARY,
                                    "shrinkA": 0, "shrinkB": 0}, zorder=9)
            ax.text(x, floor_z - 0.008, f"{r['part_id']}\ngap {r['mesh_gap_mm']:.1f} mm\n"
                    f"(YAML {r['yaml_gap_mm']:.1f})", ha="center", va="top", fontsize=7.5,
                    color=INK_PRIMARY, zorder=9,
                    bbox={"boxstyle": "round,pad=0.15", "fc": SURFACE, "ec": "none",
                          "alpha": 0.85})
        ax.set_ylim(floor_z - 0.06, floor_z + 0.20)
    draw_gap_profile(profile, track, rows, layout, side, floor_z)
    handles = [Rectangle((0, 0), 1, 1, facecolor=KIND_COLOURS[k], edgecolor="black",
                         linewidth=0.4) for k in ("roller", "end_shoe", "flat_shoe")]
    labels = [KIND_LABELS[k] for k in ("roller", "end_shoe", "flat_shoe")]
    handles += [
        Line2D([], [], marker="o", ms=5, color=POINT_COLOUR, mec="white", linestyle="none"),
        Line2D([], [], marker="D", ms=5, color=SPHERE_COLOUR, mec="white", linestyle="none"),
        Line2D([], [], marker="_", ms=8, mew=1.2, color=SPHERE_COLOUR, linestyle="none"),
        Line2D([], [], color=INK_PRIMARY, marker="$↕$", linestyle="none", ms=9),
    ]
    handles.append(Line2D([], [], marker="x", ms=6, color=INK_PRIMARY, linestyle="none"))
    labels += ["roller sphere centre", "end-shoe sphere centre (sphere dashed)",
               "sphere bottom = floor + YAML gap",
               "CAD gap: lowest point of the end shoe (mesh) to the floor",
               "lowest mesh point of the end shoe (profile)"]
    figure.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8.5,
                  labelcolor=INK_SECONDARY)
    figure.suptitle(
        "End-shoe gaps of layout D (3 raised shoes per end; left track identical): the end "
        "shoes follow the chain up the idler/sprocket\nbody frame, m, equal scale on both "
        "axes; gaps from the tessellated B-rep, YAML = contact.crawler.sphere_layout."
        "end_shoe_gap_m", color=INK_PRIMARY, fontsize=11)
    figure.tight_layout(rect=(0, 0.05, 1, 0.95))
    figure.savefig(OUT_GAP, dpi=dpi, facecolor=SURFACE)
    plt.close(figure)
    return {"side": side, "end_shoes": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dpi", type=float, default=150.0)
    parser.add_argument("--linear-mm", type=float, default=1.0,
                        help="BRepMesh absolute linear deflection [mm]")
    parser.add_argument("--angular-rad", type=float, default=0.5,
                        help="BRepMesh angular deflection [rad]")
    parser.add_argument("--no-context", action="store_true",
                        help="do not draw crawler_lowres.obj")
    rlv.edge_style_arguments(parser)
    arguments = parser.parse_args()
    rlv.VIEWS.update(EXTRA_VIEWS)
    rlv.VIEWS["iso"] = iso_view()
    started = time.perf_counter()
    params = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
    node = params
    for key in LAYOUT_PATH.split("."):
        node = node[key]
    layout = layout_from_mapping(node)
    floor_z = float(params["ground"]["crawler_bottom_z_m"])
    parts = load_parts(arguments.linear_mm, arguments.angular_rad)
    t_mesh = time.perf_counter() - started
    context = None if arguments.no_context else load_context()
    style = rlv.edge_style_from(arguments)
    views = draw_views(parts, context, layout, floor_z, arguments.dpi, style)
    gaps = draw_gap_detail(parts, layout, floor_z, arguments.dpi, style)
    # sphere vs part checks: each sphere's xy inside the footprint of a part of its kind
    checks = []
    for (x, y), kind, side, gap in zip(layout.xy_m, layout.kind, layout.side, layout.gap_m,
                                       strict=True):
        rows = parts[(parts["kind"] == kind) & (parts["side"] == side)]
        hits = [r.part_id for r in rows.itertuples()
                if r.vertices_m[:, 0].min() <= x <= r.vertices_m[:, 0].max()
                and r.vertices_m[:, 1].min() <= y <= r.vertices_m[:, 1].max()]
        under = parts[(parts["side"] == side)]
        floor_parts = [r.part_id for r in under.itertuples()
                       if r.vertices_m[:, 0].min() <= x <= r.vertices_m[:, 0].max()
                       and r.vertices_m[:, 2].min() - floor_z < 1e-3]
        checks.append({"kind": kind, "side": side, "x_m": float(x), "y_m": float(y),
                       "gap_mm": float(gap * 1000), "inside_part_xy": hits,
                       "parts_on_floor_at_x": floor_parts})
    print(json.dumps({
        "outputs": {str(OUT_VIEWS): OUT_VIEWS.stat().st_size,
                    str(OUT_GAP): OUT_GAP.stat().st_size},
        "mesh": {"linear_deflection_mm": arguments.linear_mm,
                 "angular_deflection_rad": arguments.angular_rad,
                 "parts": len(parts),
                 "triangles": int(sum(len(f) for f in parts["faces"])),
                 "context_triangles": None if context is None else int(len(context[1]))},
        "floor_z_m": floor_z,
        "layout": layout.summary(),
        **views,
        "gaps": gaps,
        "sphere_checks": checks,
        "mesh_s": round(t_mesh, 1),
        "total_s": round(time.perf_counter() - started, 1),
    }, indent=1))


if __name__ == "__main__":
    main()
