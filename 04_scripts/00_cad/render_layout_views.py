"""Shaded-mesh version of layout_views.png: top (x-y), side (x-z) and front (y-z) views.

Same figure layout, axis ranges, leg colours, CoG markers and ground line as
analyze_parts.draw_layout (01_cad/01_parts/layout_views.png, part bounding boxes), but the
parts are drawn as shaded triangle meshes with thin black outlines instead of bounding-box
wireframes.

Reads only cached data (no STEP parsing):
    01_cad/01_parts/parts_classified.csv   part rows, leg names, bounding boxes (analyze_parts.py)
    01_cad/01_parts/cad_summary.json       CoG of the superstructure and of the whole assembly
                                           (case A)
    01_cad/05_meshes/render_mesh_v5.npz    drawing mesh, undecimated CAD tessellation
                                           (build_render_mesh_v5.py, via analyze_mast.render_meshes)

Writes:
    01_cad/01_parts/layout_views_rendered.png

Renderer (2026-11-09). Default "zbuffer" (mesh_zbuffer.py): exact per-pixel visibility of the
6.4 M V5 triangles, drawn as one raster; outlines come from the part-id / normal buffers
(part changes and creases > --edge-angle), so hidden lines stay hidden. "painter" (environment
variable OUTRIGGER_MESH_RENDERER=painter, or renderer="painter") is the method below with the
edge segments; it needs about 10 GB per figure already for the old 1.2 M-triangle decimated
mesh and is kept for the small part sets (render_crawler_contact_parts.py).

Method (painter). Each view is an orthographic projection of the body-frame meshes (x = Z_cad,
y = X_cad, z = Y_cad, metres, origin = CAD origin), painter-sorted by depth. Shading
= Lambert term against a light from the viewer and above, plus depth cueing (far faces
fade toward the background). The four jack cylinders (barrel + rod/pad) are drawn
in the leg colours and on top of the other parts, like the filled boxes of the
original figure. The axis ranges are the ones the bounding-box figure gets
(draw_layout's autoscale), so both images line up. The auger is at the CAD pose.

Outlines. Per part, an edge of the (welded, consistently wound) render mesh is drawn when
it is a boundary edge, a silhouette edge for this view (one adjacent face toward the
viewer, the other away) or a sharp feature edge (dihedral angle above --edge-angle).
Every edge is a degenerate triangle (a, b, a) in the same painter-sorted collection as the
faces, keyed just behind the nearer of its two faces, so nearer faces hide it (hidden
lines are not drawn). Parts whose projected size is below --edge-min-part-px get no
outline, which keeps bolts and small fittings from turning into black blots. The edge
colour takes the same depth fade as the faces. render_leg_extension.py reuses these
functions.

Usage:
    python -I 04_scripts/00_cad/render_layout_views.py [--dpi 130] [--no-edges]
        [--edge-angle 35] [--edge-width-px 0.4] [--edge-min-part-px 6]
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_parts import (
    CAD_TO_BODY,
    CLASSIFIED_CSV,
    INK_PRIMARY,
    LEG_COLORS,
    LEG_ORDER,
    OTHER_PART_COLOR,
    SURFACE,
    _draw_view,
)
import mesh_zbuffer
from cad_common import MM_PER_M, PARTS_DIR, SUMMARY_JSON
from render_auger_descent import RENDER_NPZ, load_render_meshes

OUTPUT_PNG = PARTS_DIR / "layout_views_rendered.png"
RENDER_MESH_NAME = RENDER_NPZ.name  # drawing mesh (render_mesh_v5.npz, build_render_mesh_v5.py)
# Hidden-surface method of shade_scene / scene_collection (module docstring).
RENDERER = os.environ.get("OUTRIGGER_MESH_RENDERER", "zbuffer").strip().lower()
if RENDERER not in ("zbuffer", "painter"):
    raise SystemExit(f"OUTRIGGER_MESH_RENDERER={RENDERER!r}: use zbuffer or painter")
if RENDERER == "zbuffer" and not mesh_zbuffer.available():  # pragma: no cover
    RENDERER = "painter"
# (screen right, screen up, toward viewer) in body axes; right x up = toward.
VIEWS = {
    "top": (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])),
    "side": (np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, -1.0, 0])),
    "front": (np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0])),
}
DEPTH_FADE = 0.35  # farthest faces are blended this much toward the background
LEG_DEPTH_BIAS_M = 100.0
EDGE_DEPTH_EPS_M = 1e-5  # an edge is drawn right after the nearer of its two faces
EDGE_COLOR = (0.0, 0.0, 0.0)
TRANSPARENT = (0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class EdgeStyle:
    """Outline settings (see the module docstring)."""

    enabled: bool = True
    angle_deg: float = 35.0
    width_px: float = 0.4
    min_part_px: float = 6.0


@dataclass(frozen=True)
class Topology:
    """View-independent edge data of one part mesh (degenerate faces removed)."""

    faces: np.ndarray  # (F, 3) valid faces
    edge_vertices: np.ndarray  # (E, 2) vertex indices
    edge_faces: np.ndarray  # (E, 2) adjacent faces; second = -1 on a boundary edge
    winding: np.ndarray  # (E,) +1 if the two faces are wound consistently, else -1


@dataclass
class SceneItem:
    """One part to draw: body-frame vertices [m], its topology and drawing attributes."""

    vertices_m: np.ndarray
    topology: Topology
    colour: str
    depth_bias_m: float = 0.0
    fade: bool = True


def part_topology(vertices: np.ndarray, faces: np.ndarray, edges: bool = True) -> Topology:
    """Edges of a welded triangle mesh with their adjacent faces.

    Non-manifold edges (more than two faces) keep the first two faces; boundary edges
    (one face) get -1 as the second face. ``edges=False`` keeps only the valid faces (the
    z-buffer renderer finds outlines in pixel buffers and needs no edge table).
    """
    if len(faces):
        triangles = vertices[faces]
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        faces = faces[np.linalg.norm(cross, axis=1) > 0]
    if len(faces) == 0 or not edges:
        empty = np.zeros((0, 2), dtype=np.int64)
        return Topology(faces if len(faces) else np.zeros((0, 3), dtype=np.int64), empty, empty, np.zeros(0))
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    owner = np.tile(np.arange(len(faces)), 3)
    keys = np.sort(directed, axis=1)
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    keys, directed, owner = keys[order], directed[order], owner[order]
    start = np.ones(len(keys), dtype=bool)
    start[1:] = np.any(keys[1:] != keys[:-1], axis=1)
    first = np.flatnonzero(start)
    counts = np.diff(np.append(first, len(keys)))
    has_pair = counts >= 2
    second = np.where(has_pair, first + 1, first)
    edge_faces = np.stack([owner[first], np.where(has_pair, owner[second], -1)], axis=1)
    # Consistent winding: the shared edge runs in opposite directions in the two faces.
    same_direction = directed[first, 0] == directed[second, 0]
    winding = np.where(has_pair & same_direction, -1.0, 1.0)
    return Topology(faces, keys[first], edge_faces, winding)


def build_topologies(render, edges: bool | None = None) -> list[Topology]:
    """Topologies of all parts; edge tables only for the painter renderer (default)."""
    if edges is None:
        edges = RENDERER == "painter"
    return [part_topology(vertices, faces, edges) for vertices, faces in render]


def body_vertices(vertices_cad_mm: np.ndarray) -> np.ndarray:
    """CAD mm -> body frame m (x = Z_cad, y = X_cad, z = Y_cad)."""
    return vertices_cad_mm @ CAD_TO_BODY.T / MM_PER_M


class ZScene(tuple):
    """shade_scene result of the z-buffer renderer.

    As a tuple it looks like the painter result (polygons (N, 3, 2) depth-sorted, face RGBA
    (N, 4), None, None, edge flags (N,) all False) so callers that read ``scene[0]`` or
    ``scene[4]`` keep working; the attributes carry what mesh_zbuffer.ZBufferCollection needs.
    """

    depths: np.ndarray        # (N, 3) per-vertex depth toward the viewer [m], incl. depth bias
    part_ids: np.ndarray      # (N,) 1-based item index
    normals: np.ndarray       # (N, 3) unit normals turned toward the viewer
    outline_parts: np.ndarray  # (items + 1,) outline allowed per part id (0 = background)
    edge_rgb: np.ndarray      # (N, 3) outline colour (depth-faded EDGE_COLOR)
    width_pt: float
    crease_angle_deg: float


def _zbuffer_scene(items: list[SceneItem], view: str, px_per_m: float, style: EdgeStyle,
                   dpi: float, depth_fade: bool) -> ZScene:
    right, up, toward = VIEWS[view]
    light = toward + 0.6 * up + 0.3 * right
    light /= np.linalg.norm(light)
    background = np.array(matplotlib.colors.to_rgb(SURFACE))
    polygons, colours, depths, ids, normals_all, fadeable = [], [], [], [], [], []
    outline = np.zeros(len(items) + 1, dtype=bool)
    outline[0] = True
    for part_id, item in enumerate(items, start=1):
        faces = item.topology.faces
        if len(faces) == 0:
            continue
        triangles = item.vertices_m[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        shade = 0.40 + 0.60 * np.abs(normals @ light)
        base = np.array(matplotlib.colors.to_rgb(item.colour))
        colours.append(np.clip(base[None] * shade[:, None] + 0.10 * (1 - shade[:, None]), 0, 1))
        screen = np.stack([item.vertices_m @ right, item.vertices_m @ up], axis=1)
        polygons.append(screen[faces])
        depths.append(triangles @ toward + item.depth_bias_m)
        ids.append(np.full(len(faces), part_id, dtype=np.int32))
        normals_all.append(normals * np.where(normals @ toward < 0, -1.0, 1.0)[:, None])
        fadeable.append(np.full(len(faces), item.fade))
        extent_px = np.linalg.norm(screen.max(axis=0) - screen.min(axis=0)) * px_per_m
        outline[part_id] = style.enabled and extent_px >= style.min_part_px
    if not polygons:
        empty = np.zeros((0, 3, 2))
        scene = ZScene((empty, np.zeros((0, 4)), None, None, np.zeros(0, dtype=bool)))
        scene.depths, scene.part_ids, scene.normals = np.zeros((0, 3)), np.zeros(0, np.int32), np.zeros((0, 3))
        scene.outline_parts, scene.edge_rgb = outline, np.zeros((0, 3))
        scene.width_pt, scene.crease_angle_deg = 0.0, style.angle_deg
        return scene
    depth = np.concatenate(depths)
    rgb = np.concatenate(colours)
    fade_mask = np.concatenate(fadeable)
    edge_rgb = np.tile(np.array(EDGE_COLOR, dtype=float), (len(rgb), 1))
    if depth_fade:
        centre = depth.mean(axis=1)
        unbiased = centre[fade_mask]
        near, far = np.percentile(unbiased, [99.5, 0.5]) if len(unbiased) else (1.0, 0.0)
        fade = DEPTH_FADE * np.clip((near - centre) / (near - far), 0, 1) * fade_mask
        rgb = rgb * (1 - fade[:, None]) + background[None] * fade[:, None]
        edge_rgb = edge_rgb * (1 - fade[:, None]) + background[None] * fade[:, None]
    order = np.argsort(depth.mean(axis=1), kind="stable")
    rgba = np.concatenate([rgb, np.ones((len(rgb), 1))], axis=1)[order].astype(np.float32)
    scene = ZScene((np.concatenate(polygons)[order], rgba, None, None, np.zeros(len(rgba), dtype=bool)))
    scene.depths = depth[order]
    scene.part_ids = np.concatenate(ids)[order]
    scene.normals = np.concatenate(normals_all)[order].astype(np.float32)
    scene.outline_parts = outline
    scene.edge_rgb = edge_rgb[order].astype(np.float32)
    scene.width_pt = style.width_px * 72.0 / dpi if style.enabled else 0.0
    scene.crease_angle_deg = style.angle_deg
    return scene


def shade_scene(items: list[SceneItem], view: str, px_per_m: float, style: EdgeStyle,
                dpi: float, depth_fade: bool = True, renderer: str | None = None):
    """Faces and outlines of all items for one view.

    ``renderer`` (default RENDERER): "zbuffer" returns a :class:`ZScene` for
    mesh_zbuffer.ZBufferCollection (outlines from pixel buffers); "painter" returns the
    painter-sorted faces and outline segments (needs topologies with edge tables):

    Returns (painter):
        polygons (N, 3, 2) in screen metres, face RGBA (N, 4), edge RGBA (N, 4),
        line widths in points (N,), antialiasing flags (N,); faces have no edge and
        outline segments (a, b, a) have no face.
    """
    if (renderer or RENDERER) == "zbuffer":
        return _zbuffer_scene(items, view, px_per_m, style, dpi, depth_fade)
    right, up, toward = VIEWS[view]
    light = toward + 0.6 * up + 0.3 * right
    light /= np.linalg.norm(light)
    background = np.array(matplotlib.colors.to_rgb(SURFACE))
    cos_feature = np.cos(np.radians(style.angle_deg))
    width_pt = style.width_px * 72.0 / dpi
    polygons, colours, depths, is_edge, fadeable = [], [], [], [], []
    for item in items:
        topo = item.topology
        if len(topo.faces) == 0:
            continue
        triangles = item.vertices_m[topo.faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        shade = 0.40 + 0.60 * np.abs(normals @ light)
        base = np.array(matplotlib.colors.to_rgb(item.colour))
        face_rgb = np.clip(base[None] * shade[:, None] + 0.10 * (1 - shade[:, None]), 0, 1)
        screen = np.stack([item.vertices_m @ right, item.vertices_m @ up], axis=1)
        face_depth = (triangles @ toward).mean(axis=1) + item.depth_bias_m
        polygons.append(screen[topo.faces])
        colours.append(face_rgb)
        depths.append(face_depth)
        is_edge.append(np.zeros(len(face_depth), dtype=bool))
        fadeable.append(np.full(len(face_depth), item.fade))
        if not style.enabled:
            continue
        extent_px = np.linalg.norm(screen.max(axis=0) - screen.min(axis=0)) * px_per_m
        if extent_px < style.min_part_px:
            continue
        f1, f2 = topo.edge_faces[:, 0], topo.edge_faces[:, 1]
        boundary = f2 < 0
        f2_safe = np.where(boundary, f1, f2)
        n1 = normals[f1]
        n2 = normals[f2_safe] * topo.winding[:, None]
        facing1, facing2 = n1 @ toward, n2 @ toward
        silhouette = facing1 * facing2 < 0
        feature = np.einsum("ij,ij->i", n1, n2) < cos_feature
        selected = boundary | silhouette | feature
        if not selected.any():
            continue
        ends = screen[topo.edge_vertices[selected]]
        polygons.append(np.stack([ends[:, 0], ends[:, 1], ends[:, 0]], axis=1))
        edge_depth = np.maximum(face_depth[f1[selected]], face_depth[f2_safe[selected]])
        depths.append(edge_depth + EDGE_DEPTH_EPS_M)
        colours.append(np.tile(EDGE_COLOR, (len(edge_depth), 1)))
        is_edge.append(np.ones(len(edge_depth), dtype=bool))
        fadeable.append(np.full(len(edge_depth), item.fade))
    depth = np.concatenate(depths)
    rgb = np.concatenate(colours)
    edge = np.concatenate(is_edge)
    fade_mask = np.concatenate(fadeable)
    if depth_fade:
        unbiased = depth[fade_mask & ~edge]
        near, far = np.percentile(unbiased, [99.5, 0.5]) if len(unbiased) else (1.0, 0.0)
        fade = DEPTH_FADE * np.clip((near - depth) / (near - far), 0, 1) * fade_mask
        rgb = rgb * (1 - fade[:, None]) + background[None] * fade[:, None]
    order = np.argsort(depth, kind="stable")
    rgba = np.concatenate([rgb, np.ones((len(rgb), 1))], axis=1)[order]
    edge = edge[order]
    face_rgba = np.where(edge[:, None], np.array(TRANSPARENT), rgba)
    edge_rgba = np.where(edge[:, None], rgba, np.array(TRANSPARENT))
    widths = np.where(edge, width_pt, 0.0)
    return np.concatenate(polygons)[order], face_rgba, edge_rgba, widths, edge


def scene_collection(scene, zorder: float = 1.8):
    """Artist of shade_scene output: z-buffer raster for a :class:`ZScene`, else a
    PolyCollection (faces aliased, outlines antialiased)."""
    if isinstance(scene, ZScene):
        return mesh_zbuffer.ZBufferCollection(
            scene[0], scene.depths, scene[1], part_ids=scene.part_ids, normals=scene.normals,
            outline_parts=scene.outline_parts, edge_colours=scene.edge_rgb,
            outline_width_pt=scene.width_pt, crease_angle_deg=scene.crease_angle_deg, zorder=zorder)
    polygons, face_rgba, edge_rgba, widths, edge = scene
    return PolyCollection(polygons, facecolors=face_rgba, edgecolors=edge_rgba,
                          linewidths=widths, antialiaseds=edge, zorder=zorder)


def px_per_metre(ax) -> float:
    ax.apply_aspect()
    origin = ax.transData.transform((0.0, 0.0))
    return float(ax.transData.transform((1.0, 0.0))[0] - origin[0])


def layout_items(render, topologies, legs) -> list[SceneItem]:
    return [
        SceneItem(body_vertices(vertices), topo, LEG_COLORS.get(leg, OTHER_PART_COLOR),
                  LEG_DEPTH_BIAS_M if leg else 0.0, fade=not leg)
        for (vertices, _), topo, leg in zip(render, topologies, legs, strict=True)
    ]


def draw(parts: pd.DataFrame, report: dict, render, dpi: float, style: EdgeStyle) -> dict:
    """Same construction as analyze_parts.draw_layout, boxes replaced by the shaded mesh."""
    step_case = report["step"]
    cogs = {
        "CoG superstructure": (
            np.array(step_case["superstructure"]["cog_body_m"]),
            {"marker": "X", "markersize": 8, "color": INK_PRIMARY, "zorder": 5,
             "markeredgecolor": "white", "markeredgewidth": 0.8},
        ),
        "CoG total": (
            np.array(step_case["total_assembly"]["cog_body_m"]),
            {"marker": "o", "markersize": 16, "markerfacecolor": "none",
             "markeredgecolor": INK_PRIMARY, "markeredgewidth": 1.6, "zorder": 6},
        ),
    }
    figure, axes = plt.subplots(1, 3, figsize=(18, 7), facecolor=SURFACE,
                                gridspec_kw={"width_ratios": [1.6, 1.6, 1.0]})
    legs = parts["leg"].tolist()
    items = layout_items(render, build_topologies(render), legs)
    views = (
        (axes[0], "top", (0, 1), "Top view (x-y), body frame, seen from above"),
        (axes[1], "side", (0, 2), "Side view (x-z), seen from the right (-y)"),
        (axes[2], "front", (1, 2), "Front view (y-z), seen from the front (+x)"),
    )
    limits = {}
    for ax, view, view_axes, title in views:
        _draw_view(ax, parts, view_axes, cogs, title)
        # Keep the bounding-box autoscale limits, then swap the boxes for the mesh.
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        for patch in list(ax.patches):
            patch.remove()
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_axisbelow(True)
        limits[view] = {"horizontal_m": [round(v, 3) for v in xlim],
                        "vertical_m": [round(v, 3) for v in ylim]}
    handles = [Rectangle((0, 0), 1, 1, color=LEG_COLORS[leg]) for leg in LEG_ORDER]
    handles.append(Rectangle((0, 0), 1, 1, color=OTHER_PART_COLOR))
    labels = [f"{leg} jack cylinder" for leg in LEG_ORDER] + ["other parts (shaded mesh)"]
    marker_handles, marker_labels = axes[0].get_legend_handles_labels()
    figure.legend(handles + marker_handles, labels + marker_labels, loc="lower center", ncol=7,
                  frameon=False, labelcolor="#52514e")
    outline = (f"black outlines: silhouette + edges > {style.angle_deg:g} deg"
               if style.enabled else "no outlines")
    figure.suptitle(
        "REXOME33 shaded mesh, auger at CAD pose  (x_body = Z_cad, y_body = X_cad, "
        f"z_body = Y_cad; origin = CAD origin; CoG case A = STEP densities; {outline})",
        color=INK_PRIMARY,
    )
    # Fix the layout first so that the pixel scale used by the outline filter is final.
    figure.tight_layout(rect=(0, 0.06, 1, 0.95))
    figure.set_dpi(dpi)
    edge_counts, artists = {}, {}
    for ax, view, _, _ in views:
        scene = shade_scene(items, view, px_per_metre(ax), style, dpi)
        edge_counts[view] = int(scene[4].sum())
        artists[view] = ax.add_collection(scene_collection(scene), autolim=False)
        del scene
    figure.savefig(OUTPUT_PNG, dpi=dpi, facecolor=SURFACE)
    plt.close(figure)
    result = {"renderer": RENDERER, "axis_limits_body_m": limits}
    if RENDERER == "zbuffer":
        result["zbuffer"] = {view: getattr(artist, "stats", {}) for view, artist in artists.items()}
    else:
        result["outline_segments"] = edge_counts
    return result


def edge_style_arguments(parser: argparse.ArgumentParser) -> None:
    """Outline options shared with render_leg_extension.py."""
    defaults = EdgeStyle()
    parser.add_argument("--no-edges", action="store_true", help="faces only, no black outlines")
    parser.add_argument("--edge-angle", type=float, default=defaults.angle_deg,
                        help="feature-edge dihedral angle threshold [deg]")
    parser.add_argument("--edge-width-px", type=float, default=defaults.width_px,
                        help="outline width [output px]")
    parser.add_argument("--edge-min-part-px", type=float, default=defaults.min_part_px,
                        help="parts smaller than this on screen [px] get no outline")


def edge_style_from(arguments: argparse.Namespace) -> EdgeStyle:
    return EdgeStyle(not arguments.no_edges, arguments.edge_angle, arguments.edge_width_px,
                     arguments.edge_min_part_px)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dpi", type=float, default=130.0, help="same as layout_views.png")
    edge_style_arguments(parser)
    arguments = parser.parse_args()
    started = time.perf_counter()
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")  # CSV round trip turns "" into NaN
    report = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))["mass_properties"]
    render, cache_valid = load_render_meshes(parts["instance_path"].tolist())
    style = edge_style_from(arguments)
    result = draw(parts, report, render, arguments.dpi, style)
    print(json.dumps({
        "output": str(OUTPUT_PNG),
        "size_bytes": OUTPUT_PNG.stat().st_size,
        "render_mesh": RENDER_MESH_NAME,
        "render_cache_used": cache_valid,
        "triangles": int(sum(len(f) for _, f in render)),
        "edge_style": asdict(style),
        **result,
        "total_s": round(time.perf_counter() - started, 1),
    }, indent=1))


if __name__ == "__main__":
    main()
