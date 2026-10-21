"""CAD-track overview figures of 2026-10-21 (C7 crawler ground sheet, C8 simulation shapes,
C11 STEP colours) and the shared C8 + C11 mesh renderer used by the S4 GIFs.

Reads only cached data (the STEP file is not opened; nothing is modified):
    01_cad/09_sim_shapes/sim_shapes.json        C8 index (visual / collision entries, frame)
    01_cad/09_sim_shapes/work/<name>.npz        C8 visual meshes (same vertices / faces as the
                                                visual/*.obj files; counts checked against
                                                sim_shapes.json)
    01_cad/09_sim_shapes/collision/*.obj        C8 collision candidates (CoACD pieces)
    01_cad/05_meshes/parts_mesh.npz + index.json  per-instance 3 mm tessellation (colour lookup)
    01_cad/08_style/instance_styles.csv         C11 display colours (style_index.colours_for,
                                                mode "display" = with assembly overrides)
    01_cad/06_brep/derived/crawler/crawler_ground_sheet.png / .json   C7 plan view (embedded)
    02_params/rexome33.yaml                      crawler layout D spheres, ground height

Writes:
    01_cad/cad_tracks_2026-10-21.png     3 panels: (1) whole assembly, C8 meshes in the C11
                                         display colours; (2) C8 visual mesh vs collision
                                         candidates (CoACD pieces) + the contact primitives
                                         the model really uses; (3) C7 ground plan
    01_cad/cad_tracks_turntable.gif      360 deg turntable of (1)
    01_cad/cad_tracks_summary.json       inputs (sha256), settings, counts, timings

C11 colour on the C8 meshes: the C8 visual meshes are merged per group (deck, mast, auger,
crawler) and carry no instance id. Each simplified face gets the display colour of the
instance whose 3 mm tessellation vertex is nearest to the face centroid (KD-tree, body frame).
The median / 99th-percentile lookup distance is reported. Glass transparency is not drawn.

Renderer: painter-sorted, Lambert-shaded faces with hidden-line outlines
(render_layout_views.shade_scene), 2x supersampled, orthographic.

Usage (project root, Chrono-dev python):
    python -I 04_scripts/00_cad/render_cad_tracks_summary.py [--only summary|turntable ...]
        [--mesh-cache DIR] [--cpu pcore|os] [--frames 48]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))

import render_layout_views as rlv  # noqa: E402
import style_index  # noqa: E402
from cad_common import CAD_DIR  # noqa: E402

SIM_DIR = CAD_DIR / "09_sim_shapes"
SIM_JSON = SIM_DIR / "sim_shapes.json"
WORK_DIR = SIM_DIR / "work"
PARTS_MESH_NPZ = CAD_DIR / "05_meshes" / "parts_mesh.npz"
PARTS_MESH_INDEX = CAD_DIR / "05_meshes" / "index.json"
GROUND_PNG = CAD_DIR / "06_brep" / "derived" / "crawler" / "crawler_ground_sheet.png"
GROUND_JSON = CAD_DIR / "06_brep" / "derived" / "crawler" / "crawler_ground_sheet.json"
OUT_PNG = CAD_DIR / "cad_tracks_2026-10-21.png"
OUT_GIF = CAD_DIR / "cad_tracks_turntable.gif"
OUT_JSON = CAD_DIR / "cad_tracks_summary.json"

CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
LEG_ORDER = ("FL", "FR", "RL", "RR")
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
GROUND_COLOR = "#d9cfc0"
EARTH_COLOR = "#8a6a45"
CONTACT_COLOR = "#e34948"
DPI = 100
SUPERSAMPLE = 2
CLUSTER_CELL_M = 0.025
"""Vertex-clustering cell of the drawn meshes (deck, mast, auger, crawler) [m]."""
CLUSTER_MIN_FACES = 5000
MIN_AREA2_M2 = 1e-10
"""Faces with |cross| (= 2 x area) below this [m^2] are not drawn (sliver triangles)."""

plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# =============================================================================================
# helpers
# =============================================================================================


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def source(path: Path) -> dict:
    return {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def place_cpu(mode: str) -> dict:
    """P-core pinning (outrigger_sim.hostcpu.place_process); ``os`` leaves the process alone."""
    if mode == "os":
        return {"mode": "os"}
    try:
        from outrigger_sim.hostcpu import place_process

        return place_process("pcore")
    except Exception as error:  # noqa: BLE001 - placement is optional
        return {"mode": mode, "error": repr(error)}


def save_atomic(path: Path, write) -> None:
    """Write through a temporary file and rename (retries: a viewer may hold the file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp" + path.suffix)
    write(temporary)
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except OSError:
            time.sleep(0.5 * (attempt + 1))
    raise OSError(f"cannot replace {path}")


def iso_view(toward) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    toward = np.asarray(toward, float)
    toward = toward / np.linalg.norm(toward)
    right = np.cross([0.0, 0.0, 1.0], toward)
    right /= np.linalg.norm(right)
    return right, np.cross(toward, right), toward


def register_view(name: str, toward) -> str:
    rlv.VIEWS[name] = iso_view(toward)
    return name


def screen(points, view: str) -> np.ndarray:
    right, up, _ = rlv.VIEWS[view]
    p = np.atleast_2d(points)
    return np.stack([p @ right, p @ up], axis=1)


def cluster_mesh(vertices, faces, cell):
    """Vertex-clustering decimation (as render_S2_gifs.cluster_mesh)."""
    key = np.floor(vertices / cell).astype(np.int64)
    unique, inverse = np.unique(key, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    sums = np.zeros((len(unique), 3))
    np.add.at(sums, inverse, vertices)
    counts = np.bincount(inverse, minlength=len(unique))
    new_vertices = sums / counts[:, None]
    new_faces = inverse[faces]
    ok = ((new_faces[:, 0] != new_faces[:, 1]) & (new_faces[:, 1] != new_faces[:, 2])
          & (new_faces[:, 0] != new_faces[:, 2]))
    new_faces = new_faces[ok]
    if len(new_faces):
        _, first = np.unique(np.sort(new_faces, axis=1), axis=0, return_index=True)
        new_faces = new_faces[np.sort(first)]
    return new_vertices, new_faces


# =============================================================================================
# C8 meshes with C11 colours
# =============================================================================================


@dataclass
class Piece:
    """Faces of one colour of one C8 visual mesh (body frame, CAD pose, legs retracted)."""

    vertices: np.ndarray
    topology: rlv.Topology
    colour: str


@dataclass
class Part:
    name: str
    kind: str  # body / barrel / rod / pad
    leg: str | None
    moves_with_auger: bool
    pieces: list[Piece] = field(default_factory=list)
    faces_source: int = 0
    faces_drawn: int = 0


def _work_key(name: str) -> str:
    if name.startswith("pad_") and name.endswith("_simple"):
        return f"pad_simple_{name.split('_')[1]}"
    for group in ("deck", "mast", "auger", "crawler"):
        if name == group:
            return group
    return name


def _kind(name: str, entry: dict) -> str:
    if entry["leg"] is None:
        return "body"
    return name.split("_")[0]  # barrel / rod / pad


def colour_lookup():
    """(KD-tree over the 3 mm instance tessellation in body metres, vertex -> colour id,
    colour list, instance count)."""
    from scipy.spatial import cKDTree

    data = np.load(PARTS_MESH_NPZ)
    paths = json.loads(PARTS_MESH_INDEX.read_text(encoding="utf-8"))["instance_paths"]
    v_off = data["vertex_offsets"]
    if len(v_off) != len(paths) + 1:
        raise SystemExit("parts_mesh.npz offsets do not match index.json instance_paths")
    colours = style_index.colours_for(paths, mode="display")
    palette = sorted(set(colours))
    cid = np.array([palette.index(c) for c in colours])
    owner = np.repeat(np.arange(len(paths)), np.diff(v_off))
    points = (data["vertices"].astype(np.float64) @ CAD_TO_BODY.T) * 1e-3
    return cKDTree(points), cid[owner], palette, len(paths)


def load_coloured_parts(cache_dir: Path | None = None, cell_m: float = CLUSTER_CELL_M):
    """Default C8 visual shapes (sim_shapes.json ``default``), decimated, split by C11 colour.

    Returns (parts, stats). Cached as a pickle in ``cache_dir`` when given (key: cell, input
    sha256 prefixes)."""
    index = json.loads(SIM_JSON.read_text(encoding="utf-8"))
    names = [n for n, e in index["visual"].items() if e["default"]]
    key = hashlib.sha256((str(cell_m) + str(MIN_AREA2_M2) + sha256_file(SIM_JSON)
                          + str(PARTS_MESH_NPZ.stat().st_mtime_ns)
                          + str(style_index.INSTANCE_STYLES_CSV.stat().st_mtime_ns))
                         .encode()).hexdigest()[:12]
    cached = cache_dir / f"c8_c11_parts_{key}.pkl" if cache_dir else None
    if cached is not None and cached.exists():
        with open(cached, "rb") as handle:
            data = pickle.load(handle)
        return data["parts"], data["stats"]
    t0 = time.perf_counter()
    tree, vertex_colour, palette, n_instances = colour_lookup()
    t_tree = time.perf_counter() - t0
    parts, distances, count_checks = [], [], {}
    for name in names:
        entry = index["visual"][name]
        npz = WORK_DIR / f"{_work_key(name)}.npz"
        mesh = np.load(npz)
        vertices, faces = mesh["vertices"].astype(float), mesh["faces"].astype(np.int64)
        count_checks[name] = int(len(faces)) == int(entry["faces"])
        n_src = len(faces)
        if len(faces) > CLUSTER_MIN_FACES:
            vertices, faces = cluster_mesh(vertices, faces, cell_m)
        centroids = vertices[faces].mean(axis=1)
        dist, idx = tree.query(centroids, workers=4)
        distances.append(dist)
        face_cid = vertex_colour[idx]
        part = Part(name, _kind(name, entry), entry["leg"], bool(entry["moves_with_auger"]),
                    faces_source=n_src, faces_drawn=len(faces))
        tri = vertices[faces]
        area2 = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        keep = area2 > MIN_AREA2_M2  # slivers give NaN normals after a rigid transform
        for c in np.unique(face_cid):
            sub = faces[(face_cid == c) & keep]
            part.pieces.append(Piece(vertices, rlv.part_topology(vertices, sub), palette[c]))
        parts.append(part)
    dist = np.concatenate(distances)
    stats = {
        "visual_names": names,
        "face_count_equals_index": count_checks,
        "cluster_cell_m": cell_m, "cluster_min_faces": CLUSTER_MIN_FACES,
        "faces_source": int(sum(p.faces_source for p in parts)),
        "faces_drawn": int(sum(p.faces_drawn for p in parts)),
        "colour_lookup": {
            "method": "nearest 3 mm tessellation vertex of any instance to each drawn face "
                      "centroid (scipy cKDTree, body frame m); colour = style_index display "
                      "colour of that instance",
            "instances": n_instances,
            "distance_median_mm": float(np.median(dist) * 1e3),
            "distance_p99_mm": float(np.percentile(dist, 99) * 1e3),
            "distance_max_mm": float(dist.max() * 1e3),
            "colours_used": sorted({pc.colour for p in parts for pc in p.pieces}),
            "tree_build_s": t_tree,
        },
        "build_s": time.perf_counter() - t0,
    }
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        with open(cached, "wb") as handle:
            pickle.dump({"parts": parts, "stats": stats}, handle, protocol=5)
    return parts, stats


def posed_items(parts, *, auger_travel_m=0.0, s_motor=(0, 0, 0, 0), direction=(0, 0, -1.0),
                pos=np.zeros(3), rot=np.eye(3), pad_world=None, colour_override=None,
                kinds=None):
    """World SceneItems of the parts.

    Body parts move rigidly (pos, rot). Rods and pads also move along the leg ``direction`` by
    ``s_motor``. ``pad_world``: optional {leg: (pos, rot)} that overrides the pose of a pad
    (e.g. exaggerated motion with the pads kept on the floor). ``colour_override``: {kind or
    leg kind: colour}."""
    direction = np.asarray(direction, float)
    items = []
    for part in parts:
        if kinds is not None and part.kind not in kinds:
            continue
        shift = np.zeros(3)
        if part.moves_with_auger:
            shift = shift + np.array([0.0, 0.0, auger_travel_m])
        if part.kind in ("rod", "pad"):
            shift = shift + s_motor[LEG_ORDER.index(part.leg)] * direction
        p, r = pos, rot
        if part.kind == "pad" and pad_world is not None and part.leg in pad_world:
            p, r = pad_world[part.leg]
        for piece in part.pieces:
            world = (piece.vertices + shift) @ np.asarray(r).T + p
            colour = piece.colour
            if colour_override and part.kind in colour_override:
                colour = colour_override[part.kind]
            items.append(rlv.SceneItem(world, piece.topology, colour,
                                       0.0, True))
    return items


def floor_patch(ax, view, point, normal, rect, ss=1.0, grid=1.0, alpha=0.85):
    """Draw a floor rectangle (x, y ranges in world) in the plane (point, normal)."""
    n = np.asarray(normal, float)
    p0 = np.asarray(point, float)

    def z(x, y):
        return p0[2] - (n[0] * (x - p0[0]) + n[1] * (y - p0[1])) / n[2]

    (x0, x1), (y0, y1) = rect
    poly = np.array([[x, y, z(x, y)] for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
    ax.add_patch(Polygon(screen(poly, view), closed=True, facecolor=GROUND_COLOR, alpha=alpha,
                         edgecolor=EARTH_COLOR, lw=0.8 * ss, zorder=0.5))
    if grid:
        for x in np.arange(np.ceil(x0 / grid) * grid, x1 + 1e-9, grid):
            seg = screen(np.array([[x, y0, z(x, y0)], [x, y1, z(x, y1)]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * ss, alpha=0.5, zorder=0.6)
        for y in np.arange(np.ceil(y0 / grid) * grid, y1 + 1e-9, grid):
            seg = screen(np.array([[x0, y, z(x0, y)], [x1, y, z(x1, y)]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * ss, alpha=0.5, zorder=0.6)


def render_items(items, view, limits, size_px, *, floor=None, edges=True, depth_fade=True,
                 overlay=None, background=None) -> Image.Image:
    """Painter render of SceneItems -> RGBA image of ``size_px`` (2x supersampled).

    floor: (point, normal, rect) drawn behind everything. overlay: callable(ax, ss) drawn on
    top (screen-metre coordinates). background: colour or None (transparent)."""
    w, h = size_px
    s = SUPERSAMPLE
    figure = plt.figure(figsize=(w * s / DPI, h * s / DPI), dpi=DPI,
                        facecolor=background or "none")
    ax = figure.add_axes((0, 0, 1, 1))
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_axis_off()
    ax.patch.set_alpha(0.0)
    px_per_m = w * s / (limits[0][1] - limits[0][0])
    if floor is not None:
        floor_patch(ax, view, *floor, ss=s)
    if items:
        style = rlv.EdgeStyle(enabled=edges, width_px=0.45 * s)
        scene = rlv.shade_scene(items, view, px_per_m, style, DPI, depth_fade=depth_fade)
        ax.add_collection(rlv.scene_collection(scene, zorder=1.0), autolim=False)
    if overlay is not None:
        overlay(ax, s)
    figure.canvas.draw()
    image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")
    plt.close(figure)
    return image.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")


def fit_limits(points_2d, size_px, margin=0.3):
    lo, hi = points_2d.min(axis=0) - margin, points_2d.max(axis=0) + margin
    w, h = size_px
    span_x, span_y = hi[0] - lo[0], hi[1] - lo[1]
    scale = max(span_x / w, span_y / h)
    cx, cy = (lo + hi) / 2
    return ((cx - scale * w / 2, cx + scale * w / 2), (cy - scale * h / 2, cy + scale * h / 2))


def items_points(items, step=7):
    return np.vstack([it.vertices_m[::step] for it in items])


# =============================================================================================
# CAD summary PNG + turntable
# =============================================================================================


def cad_pose(params):
    """CAD pose: legs retracted (s 0), auger at the CAD position, crawler on the floor."""
    return {"auger_travel_m": 0.0, "s_motor": np.zeros(4),
            "direction": _direction(params), "floor_z": float(params.ground.crawler_bottom_z_m)}


def _direction(params):
    from outrigger_sim.geometry import extension_direction

    return extension_direction(params)


def collision_items(index, view_colours):
    """CoACD candidates of C8 (one colour per object, alternate pieces lighter)."""
    from outrigger_sim.chrono.sim_shapes import read_obj_pieces

    names = ["track_L_coacd", "track_R_coacd", "deck_coacd", "mast_coacd", "auger_coacd",
             *[f"moving_{leg}_coacd" for leg in LEG_ORDER]]
    items, counts = [], {}
    for name in names:
        entry = index["collision"][name]
        pieces = read_obj_pieces(ROOT / entry["file"])
        base = np.array(matplotlib.colors.to_rgb(view_colours[name.split("_")[0]]))
        for k, (v, f) in enumerate(pieces):
            colour = base if k % 2 == 0 else 0.55 * base + 0.45
            items.append(rlv.SceneItem(np.asarray(v, float),
                                       rlv.part_topology(np.asarray(v, float),
                                                         np.asarray(f, np.int64)),
                                       matplotlib.colors.to_hex(colour), 0.0, True))
        counts[name] = {"pieces": len(pieces), "faces": int(sum(len(f) for _, f in pieces))}
    return items, counts


def render_summary(parts, stats, params, summary):
    view = register_view("cad_iso", [1.0, -1.0, 0.75])
    pose = cad_pose(params)
    items = posed_items(parts, auger_travel_m=pose["auger_travel_m"], s_motor=pose["s_motor"],
                        direction=pose["direction"])
    floor_pt = (0.0, 0.0, pose["floor_z"])
    rect = ((-3.8, 4.6), (-2.6, 2.6))
    W, H = 2000, 1400
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=SURFACE)

    def box(x, y, w, h):
        return fig.add_axes((x / W, 1 - (y + h) / H, w / W, h / H))

    fig.text(14 / W, 1 - 12 / H, "CAD 트랙 종합 (2026-10-21): C11 STEP 표시색 · C8 시각화/충돌 형상 · "
             "C7 크롤러 접지 시트", fontsize=17, fontweight="bold", va="top", color=INK_PRIMARY)
    lookup = stats["colour_lookup"]
    fig.text(14 / W, 1 - 46 / H,
             f"기체 좌표(x 전방, y 좌측, z 상방, m), CAD 자세(다리 완전 수축, 오거 CAD 위치), 바닥 z = "
             f"{pose['floor_z']:.4f} m. 메시: C8 시각화 메시 {stats['faces_source']:,}면 → 그림용 정점 "
             f"군집 {stats['cluster_cell_m'] * 1e3:.0f} mm {stats['faces_drawn']:,}면. 색: 단순화 면마다 "
             f"가장 가까운 인스턴스(3 mm 테셀레이션)의 C11 표시색(거리 중앙값 "
             f"{lookup['distance_median_mm']:.1f} mm, 99 % {lookup['distance_p99_mm']:.1f} mm). "
             "유리 투명도는 그리지 않음.", fontsize=9.2, va="top", color=INK_SECONDARY, wrap=True)
    # (1) whole assembly
    size1 = (640, 1220)
    pts = screen(np.vstack([items_points(items), [[x, y, pose["floor_z"]] for x in rect[0]
                                                  for y in rect[1]]]), view)
    lim1 = fit_limits(pts, size1, 0.2)
    img1 = render_items(items, view, lim1, size1, floor=(floor_pt, (0, 0, 1), rect))
    ax = box(10, 110, *size1)
    ax.imshow(img1)
    ax.set_axis_off()
    ax.set_title("(1) 전체 조립 · C8 단순화 메시 + C11 표시색(조립 외관 재정의 적용)", fontsize=11,
                 loc="left", color=INK_PRIMARY)
    counts = {}
    for it in items:
        counts[it.colour] = counts.get(it.colour, 0) + len(it.topology.faces)
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
    for k, (c, n) in enumerate(top):
        y = 1346 + (k // 3) * 22
        x = 20 + (k % 3) * 215
        fig.patches.append(matplotlib.patches.Rectangle((x / W, 1 - (y + 12) / H), 26 / W,
                                                        12 / H, transform=fig.transFigure,
                                                        facecolor=c, edgecolor=INK_SECONDARY,
                                                        lw=0.4))
        label = " (STEP 색 없음)" if c == style_index.FALLBACK_COLOUR else ""
        fig.text((x + 32) / W, 1 - (y + 6) / H, f"{c}{label} · {n / 1e3:.1f}k면", fontsize=8.6,
                 va="center", color=INK_PRIMARY)
    # (2) visual vs collision
    index = json.loads(SIM_JSON.read_text(encoding="utf-8"))
    view2 = register_view("cad_iso_low", [1.0, -1.1, 0.45])
    group_col = {"track": "#7b7f86", "deck": "#c9c6bd", "mast": "#696969", "auger": "#ff4d06",
                 "moving": "#3087e3"}
    coll, coll_counts = collision_items(index, group_col)
    vis_low = [it for it in posed_items(parts, auger_travel_m=0.0, s_motor=np.zeros(4),
                                        direction=pose["direction"])]
    size2 = (640, 540)
    pts2 = screen(items_points(vis_low + coll), view2)
    lim2 = fit_limits(pts2, size2, 0.25)
    from outrigger_sim.scenarios.crawler_settle import crawler_layout

    layout = crawler_layout(params)
    centres = layout.centres_body_m(pose["floor_z"])
    radius = layout.sphere_radius_m

    def spheres(ax_, ss):
        sc = screen(centres, view2)
        for c in sc:
            ax_.add_patch(Circle(c, radius, facecolor=CONTACT_COLOR, edgecolor="white",
                                 lw=0.6 * ss, zorder=5, alpha=0.95))

    img_vis = render_items(vis_low, view2, lim2, size2, floor=(floor_pt, (0, 0, 1), rect))
    img_col = render_items(coll, view2, lim2, size2, floor=(floor_pt, (0, 0, 1), rect),
                           overlay=spheres)
    ax = box(670, 110, *size2)
    ax.imshow(img_vis)
    ax.set_axis_off()
    ax.set_title(f"(2a) C8 시각화 메시 (표시 전용, {stats['faces_source'] / 1e6:.2f} M면 원본)",
                 fontsize=10.5, loc="left", color=INK_PRIMARY)
    ax = box(1340, 110, *size2)
    ax.imshow(img_col)
    ax.set_axis_off()
    n_pieces = sum(v["pieces"] for v in coll_counts.values())
    ax.set_title(f"(2b) 충돌 후보 CoACD {n_pieces}조각(기본 미사용) + 실제 접촉 구", fontsize=10.5,
                 loc="left", color=INK_PRIMARY)
    lines = [
        "충돌 후보 부피/B-rep: 트랙 3.0배(고리 안쪽을 메움), deck 7.7 · mast 10.5 · auger 2.9배(참고용),",
        "다리(로드+패드) 1.21배. 같은 색 짙음/옅음 = 이웃 조각 구분. 빨간 원 = 모델이 실제로 쓰는 크롤러",
        f"D안 접촉 구 {len(centres)}개(반지름 {radius * 1e3:.0f} mm). 패드 접촉은 구 + 지면 부싱(R14, 형상 아님).",
    ]
    fig.text(1340 / W, 1 - 664 / H, "\n".join(lines), fontsize=8.4, va="top", color=INK_SECONDARY,
             linespacing=1.4)
    vis_lines = [
        "시각화 메시: 3 mm 테셀레이션 → 성분별 2차 감축/군집, 볼트류(대각 < 40 mm) 제거.",
        "부피 vs B-rep: mast -0.18 %, crawler -1.12 %, deck -2.34 %, auger -15.6 %(원 메시부터 -10.2 %).",
        "Chrono 부착: sim_shapes.attach_model_visuals(model) — 질량·접촉 모델을 바꾸지 않음.",
    ]
    fig.text(670 / W, 1 - 664 / H, "\n".join(vis_lines), fontsize=8.4, va="top",
             color=INK_SECONDARY, linespacing=1.4)
    # (3) C7 ground plan (embedded figure of build_crawler_ground_sheet.py)
    ground = Image.open(GROUND_PNG).convert("RGB")
    gw, gh = ground.size
    crop = ground.crop((int(gw * 0.10), 0, int(gw * 0.88), gh))
    ax = box(670, 770, 1320, 620)
    ax.imshow(crop, interpolation="lanczos")
    ax.set_axis_off()
    ax.set_anchor("W")
    ax.set_title("(3) C7 크롤러 접지 평면도: 평탄 접지 슈·끝 슈(틈 mm)·롤러·+1 mm 접지 사각형·SCM 활성 "
                 "영역(원본 crawler_ground_sheet.png)", fontsize=10.5, loc="left", color=INK_PRIMARY)
    save_atomic(OUT_PNG, lambda target: fig.savefig(target, dpi=DPI, facecolor=SURFACE,
                                                    format="png"))
    plt.close(fig)
    summary["summary_png"] = {"path": rel(OUT_PNG), "size_bytes": OUT_PNG.stat().st_size,
                              "resolution_px": [W, H], "views": {
                                  "panel1_toward_viewer": rlv.VIEWS[view][2].round(4).tolist(),
                                  "panel2_toward_viewer": rlv.VIEWS[view2][2].round(4).tolist()},
                              "collision_candidates": coll_counts,
                              "crawler_contact_spheres": len(centres),
                              "ground_png_crop_x_fraction": [0.10, 0.88]}


def render_turntable(parts, params, summary, n_frames=48, size=(640, 760)):
    pose = cad_pose(params)
    items0 = posed_items(parts, direction=pose["direction"])
    pts = items_points(items0)
    centre = np.array([(pts[:, 0].min() + pts[:, 0].max()) / 2,
                       (pts[:, 1].min() + pts[:, 1].max()) / 2, 0.0])
    rect = ((-4.6, 5.2), (-3.0, 3.0))
    floor_corners = np.array([[x, y, pose["floor_z"]] for x in rect[0] for y in rect[1]])
    sample = np.vstack([pts[::5], floor_corners])
    elev = np.radians(22.0)
    views = []
    half = np.zeros(2)
    for k in range(n_frames):
        az = np.radians(-45.0) + 2 * np.pi * k / n_frames
        toward = np.array([np.cos(az) * np.cos(elev), np.sin(az) * np.cos(elev), np.sin(elev)])
        right, up, _ = iso_view(toward)
        sx, sy = sample @ right, sample @ up
        cx, cy = centre @ right, (sy.max() + sy.min()) / 2
        half = np.maximum(half, [np.abs(sx - cx).max(), np.abs(sy - cy).max()])
        views.append((az, toward, cx, cy))
    half = half + 0.15
    scale = max(half[0] / size[0], half[1] / size[1])
    hw, hh = scale * size[0], scale * size[1]
    frames = []
    t0 = time.perf_counter()
    for az, toward, cx, cy in views:
        view = register_view("turn", toward)
        lim = ((cx - hw, cx + hw), (cy - hh, cy + hh * 1.06))
        img = render_items(items0, view, lim, size, floor=((0, 0, pose["floor_z"]), (0, 0, 1),
                                                            rect), background=SURFACE)
        frame = Image.new("RGB", size, SURFACE)
        frame.paste(img, (0, 0), img)
        fig_text(frame, f"C8 단순화 메시 + C11 STEP 표시색 · 방위 {np.degrees(az) % 360:5.1f}°")
        frames.append(frame)
    write_simple_gif(frames, [90] * n_frames, OUT_GIF)
    summary["turntable_gif"] = {"path": rel(OUT_GIF), "frames": n_frames,
                                "size_bytes": OUT_GIF.stat().st_size,
                                "resolution_px": list(size), "frame_ms": 90,
                                "elevation_deg": 22.0, "render_s": time.perf_counter() - t0}


def fig_text(frame: Image.Image, text: str):
    """Caption strip at the top of a turntable frame (matplotlib text, Malgun Gothic)."""
    w, h = frame.size
    fig = plt.figure(figsize=(w / DPI, 30 / DPI), dpi=DPI, facecolor=SURFACE)
    fig.text(0.015, 0.5, text, fontsize=10, va="center", color=INK_PRIMARY)
    fig.canvas.draw()
    strip = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
    plt.close(fig)
    frame.paste(strip, (0, 0))


def write_simple_gif(frames, durations, path: Path):
    """Global palette GIF (MEDIANCUT over 6 sample frames, no dithering)."""
    ids = sorted(set(np.linspace(0, len(frames) - 1, 6).astype(int).tolist()))
    w, h = frames[0].size
    sample = Image.new("RGB", (w * len(ids), h))
    for k, i in enumerate(ids):
        sample.paste(frames[i], (k * w, 0))
    palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    save_atomic(path, lambda target: indexed[0].save(target, save_all=True,
                                                     append_images=indexed[1:],
                                                     duration=durations, loop=0, optimize=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", default=["summary", "turntable"])
    parser.add_argument("--mesh-cache", type=Path, default=None)
    parser.add_argument("--cpu", default="pcore", choices=["pcore", "os"])
    parser.add_argument("--frames", type=int, default=48)
    args = parser.parse_args()
    t0 = time.perf_counter()
    summary = {"script": rel(Path(__file__)), "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "cpu": place_cpu(args.cpu)}
    from outrigger_sim.params import load_params

    params = load_params(level="top")
    parts, stats = load_coloured_parts(args.mesh_cache)
    summary["meshes"] = stats
    print(f"meshes {time.perf_counter() - t0:.1f} s, {stats['faces_drawn']:,} faces", flush=True)
    if "summary" in args.only:
        render_summary(parts, stats, params, summary)
        print(f"summary {time.perf_counter() - t0:.1f} s", flush=True)
    if "turntable" in args.only:
        render_turntable(parts, params, summary, n_frames=args.frames)
        print(f"turntable {time.perf_counter() - t0:.1f} s", flush=True)
    index = json.loads(SIM_JSON.read_text(encoding="utf-8"))
    inputs = [SIM_JSON, PARTS_MESH_NPZ, PARTS_MESH_INDEX, style_index.INSTANCE_STYLES_CSV,
              GROUND_PNG, GROUND_JSON, ROOT / "02_params" / "rexome33.yaml"]
    inputs += [WORK_DIR / f"{_work_key(n)}.npz" for n in stats["visual_names"]]
    inputs += [ROOT / index["collision"][n]["file"] for n in
               ["track_L_coacd", "track_R_coacd", "deck_coacd", "mast_coacd", "auger_coacd",
                *[f"moving_{leg}_coacd" for leg in LEG_ORDER]]]
    summary["inputs"] = [source(p) for p in inputs]
    summary["wall_s"] = time.perf_counter() - t0
    if OUT_JSON.exists() and set(args.only) != {"summary", "turntable"}:
        old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        old.update(summary)
        summary = old
    OUT_JSON.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"done {summary['wall_s']:.1f} s", flush=True)


if __name__ == "__main__":
    main()
