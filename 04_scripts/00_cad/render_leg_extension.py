"""Animated GIF of the four outriggers extending together 0 -> 680 mm and lifting the machine.

Side view (body x-z, seen from -y) and front view (body y-z, seen from +x) side by side,
same pixel scale, fixed camera, drawn in the shaded-mesh + black-outline style of
render_layout_views.py (leg colours as in layout_views_rendered.png). Auger at the default
level of 02_params/rexome33.yaml (superstructure.default_auger_level, top).

Reads only cached data and the shared parameters (no STEP parsing, values not hard-coded):
    02_params/rexome33.yaml                via 03_src/outrigger_sim/params.load_params()
        actuator.{stroke_m, max_speed_m_s, extension_direction}
        legs.<leg>.{pad_bottom_center_retracted_m, retracted_offset_from_cad_m, axis_direction}
        ground.crawler_bottom_z_m, contact.crawler.sphere_layout (layout D, crawler_contact.py)
        superstructure.auger_levels.<level>.{com_m, auger_travel_m}
        contact.rigid_floor.L1.operating_extension_m (only for the reference comparison)
    01_cad/01_parts/parts_classified.csv   part rows (leg, group; auger moving set)
    01_cad/05_meshes/render_mesh.npz       decimated drawing meshes, same row order
    compliant V4 reference with the same crawler layout (comparison only):
        06_analysis/00_dynamics/reference.json lift_V4_compliant_crawler, layout marked
        '(YAML contact.crawler.sphere_layout)' with the YAML sphere count; otherwise
        06_analysis/00_dynamics/crawler_layout_check.json layouts.<D>.V4_quasi_static

Writes:
    01_cad/02_legs/leg_extension.gif
    01_cad/02_legs/leg_extension_kinematics.json   events, poses, comparison with reference

Kinematics (quasi-static, rigid). Body pose q = (uz, roll phi, pitch theta) about the body
origin; x, y and yaw stay 0 (no horizontal motion). Small-angle contact heights
z = p_z + uz + p_y phi - p_x theta for the 4 pad bottom centres (moved by e along
actuator.extension_direction) and the crawler contact points (contact.crawler.sphere_layout,
layout D: 12 roller points with the bottom on the floor + 12 end-shoe points raised by
end_shoe_gap_m, unilateral, so an end shoe only touches once its gap has closed). The pose
minimises the superstructure CoM height subject to z >= ground for all
points (linear programme, rigid unilateral contacts, frictionless = potential-energy minimum).
With all four pads touching and the crawler off, the pose is the least-squares solution of
the pad contacts (exact here, residual reported). Leg rod weight is left out of the
potential (rigid model: does not change the support state).

Rendering. Layers are rendered once at 2x and downsampled: the superstructure (with the leg
barrels drawn above it) and the rod/pad sets, per view split into the far and near legs.
Per frame each layer is shifted by an integer number of pixels (rigid translation of the
body, plus the extension for the rods). The in-plane rotation and out-of-plane terms of the
tiny body tilt are not drawn; their largest effect in pixels is printed and stored.

Usage:
    python -I 04_scripts/00_cad/render_leg_extension.py [--speedup 3] [--fps 12.5]
        [--width-px 900] [--colors 128] [--level top] [--no-edges] ...
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_auger_levels import MOVING, classify
from analyze_parts import CLASSIFIED_CSV, INK_PRIMARY, INK_SECONDARY, LEG_COLORS, LEG_ORDER
from cad_common import LEGS_DIR, MM_PER_M, PROJECT_ROOT
from crawler_contact import layout_from_params
from render_auger_descent import load_render_meshes
from render_layout_views import (
    LEG_DEPTH_BIAS_M,
    OTHER_PART_COLOR,
    SURFACE,
    VIEWS,
    SceneItem,
    body_vertices,
    build_topologies,
    edge_style_arguments,
    edge_style_from,
    scene_collection,
    shade_scene,
)

sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
from outrigger_sim.params import load_params  # noqa: E402

GIF_PATH = LEGS_DIR / "leg_extension.gif"
KINEMATICS_JSON = LEGS_DIR / "leg_extension_kinematics.json"
REFERENCE_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
REFERENCE_YAML_MARK = "(YAML contact.crawler.sphere_layout)"
LAYOUT_CHECK_JSON =PROJECT_ROOT / "06_analysis" / "00_dynamics" / "crawler_layout_check.json"
# Layout key of crawler_layout_check.json that equals the YAML layout D (export_params.py
# CRAWLER_LAYOUT_KEY).
LAYOUT_CHECK_KEY = "D_rollers_plus_gapped_end_shoes"
CONTACT_TOL_M = 1e-7
EVENT_TOL_S = 1e-6
EVENT_MERGE_S = 1e-3
SUPERSAMPLE = 2
EARTH_COLOR = "#8a6a45"
PANEL_VIEWS = (("side", "측면 (x–z, −y에서 봄)"), ("front", "정면 (y–z, +x에서 봄)"))
# Output pixel layout of the figure (1x).
MARGIN_LEFT, MARGIN_GAP, MARGIN_RIGHT = 58, 62, 18
MARGIN_TOP, MARGIN_BOTTOM = 150, 78


# --- kinematics --------------------------------------------------------------------------


class QuasiStaticLift:
    """Rigid body on rigid level ground, supported by the crawler points and the 4 pads."""

    def __init__(self, params):
        self.ground_z = params.ground.crawler_bottom_z_m
        self.extension_direction = np.array(params.actuator.extension_direction)
        self.pads = np.array([leg.pad_bottom_center_retracted_m for leg in params.legs])
        self.layout = layout_from_params(params)
        # Roller bottoms on the floor, end-shoe bottoms raised by their gap (unilateral).
        self.crawler = self.layout.bottoms_m(self.ground_z)
        self.end_shoe = ~self.layout.is_roller
        com = np.array(params.superstructure.mass_properties.com_m)
        self.cost = np.array([1.0, com[1], -com[0]])

    @staticmethod
    def rows(points: np.ndarray) -> np.ndarray:
        """d z / d (uz, phi, theta) of body points (small angles)."""
        return np.column_stack([np.ones(len(points)), points[:, 1], -points[:, 0]])

    def pad_points(self, extensions) -> np.ndarray:
        return self.pads + np.asarray(extensions)[:, None] * self.extension_direction[None]

    def solve(self, extensions) -> dict:
        pads = self.pad_points(extensions)
        points = np.vstack([pads, self.crawler])
        rows = self.rows(points)
        result = linprog(self.cost, A_ub=-rows, b_ub=points[:, 2] - self.ground_z,
                         bounds=[(None, None)] * 3, method="highs")
        if not result.success:
            raise RuntimeError(f"quasi-static pose LP failed: {result.message}")
        q = result.x
        gaps = points[:, 2] + rows @ q - self.ground_z
        pad_gap, crawler_gap = gaps[:4], gaps[4:]
        pad_contact = pad_gap < CONTACT_TOL_M
        crawler_contact = bool((crawler_gap < CONTACT_TOL_M).any())
        q_lp = q.copy()
        residual = 0.0
        if not crawler_contact and pad_contact.sum() >= 3:
            # Statically indeterminate 4-pad support: least squares on the touching pads.
            active = rows[:4][pad_contact]
            target = self.ground_z - pads[pad_contact, 2]
            q = np.linalg.lstsq(active, target, rcond=None)[0]
            residual = float(np.abs(active @ q - target).max())
            gaps = points[:, 2] + rows @ q - self.ground_z
            pad_gap, crawler_gap = gaps[:4], gaps[4:]
        # Crawler point contacts from the LP pose (the LP decides the support set).
        crawler_lp_gap = self.crawler[:, 2] + self.rows(self.crawler) @ q_lp - self.ground_z
        crawler_point_contact = crawler_lp_gap < CONTACT_TOL_M
        return {
            "q": q,
            "pad_gap_m": pad_gap,
            "pad_contact": pad_contact,
            "crawler_contact": crawler_contact,
            "crawler_point_contact": crawler_point_contact,
            "end_shoe_contact": bool(crawler_point_contact[self.end_shoe].any()),
            "crawler_clearance_m": float(crawler_gap.min()),
            "lstsq_residual_m": residual,
        }


def first_time(predicate, t_end: float, step: float = 0.01) -> float | None:
    """First t in [0, t_end] where predicate(t) turns true (grid scan + bisection)."""
    if predicate(0.0):
        return 0.0
    grid = np.arange(step, t_end + step, step)
    previous = 0.0
    for t in np.minimum(grid, t_end):
        if predicate(t):
            low, high = previous, t
            while high - low > EVENT_TOL_S:
                mid = 0.5 * (low + high)
                low, high = (low, mid) if predicate(mid) else (mid, high)
            return high
        previous = t
    return None


def events(model: QuasiStaticLift, schedule, t_end: float) -> dict:
    touch = [first_time(lambda t, i=i: bool(model.solve(schedule(t))["pad_contact"][i]), t_end)
             for i in range(4)]
    crawler_off = first_time(lambda t: not model.solve(schedule(t))["crawler_contact"], t_end)
    end_shoe_on = first_time(lambda t: model.solve(schedule(t))["end_shoe_contact"], t_end)
    # Crawler points that carry the body between the first pad touch and the crawler lift-off
    # (the pivot line of the pitch / roll motion), sampled in the middle of that window.
    pivot = None
    t_first = min(touch)
    if crawler_off is not None and crawler_off - t_first > 2 * EVENT_TOL_S:
        state = model.solve(schedule(0.5 * (t_first + crawler_off)))
        mask = state["crawler_point_contact"]
        pivot = {
            "t_s": round(0.5 * (t_first + crawler_off), 4),
            "points_xy_m": model.layout.xy_m[mask].round(4).tolist(),
            "kind": [k for k, m in zip(model.layout.kind, mask, strict=True) if m],
        }
    return {"touch_s": touch, "crawler_off_s": crawler_off, "end_shoe_first_contact_s": end_shoe_on,
            "crawler_pivot_between_touch_and_lift_off": pivot}


def pose_summary(state: dict) -> dict:
    q = state["q"]
    return {
        "uz_mm": round(float(q[0]) * MM_PER_M, 4),
        "roll_deg": round(float(np.degrees(q[1])), 5),
        "pitch_deg": round(float(np.degrees(q[2])), 5),
        "crawler_min_clearance_mm": round(state["crawler_clearance_m"] * MM_PER_M, 3),
        "pad_contact": [bool(c) for c in state["pad_contact"]],
        "lstsq_residual_mm": state["lstsq_residual_m"] * MM_PER_M,
    }


def load_v4_reference(layout) -> dict:
    """Compliant V4 quasi-static events for the YAML crawler layout, normalised.

    Prefers the reference.json lift_V4 layout marked as the YAML layout (key ending in
    REFERENCE_YAML_MARK) when its sphere count and track centre equal the YAML layout;
    falls back to the layout-D entry of crawler_layout_check.json (same CAD positions, gaps
    and kn per point as the YAML).
    """
    reference = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    layouts = reference["lift_V4_compliant_crawler"]["layouts"]
    key = next((k for k, v in layouts.items()
                if k.endswith(REFERENCE_YAML_MARK)
                and v.get("n_spheres") == layout.n_points
                and abs(v.get("track_centre_y_m", np.nan) - layout.track_centre_y_m) < 5e-4),
               None)
    if key is not None:
        entry = layouts[key]
        ev, end = entry["quasi_static_events_s"], entry["end_state (after the last stop)"]
        return {
            "source": f"06_analysis/00_dynamics/reference.json lift_V4_compliant_crawler."
                      f"layouts['{key}']",
            "first_touch_leg": ev["first_touch_leg"], "first_touch_s": ev["first_touch_s"],
            "touch_s": ev["touch_s (FL, FR, RL, RR)"],
            "crawler_fully_off_s": ev["crawler_fully_off_s"],
            "leg_stop_s": ev.get("leg_stop_s (FL, FR, RL, RR)"),
            "end_attitude_deg": end["attitude_deg (roll, pitch)"],
            "end_crawler_min_clearance_mm": end["crawler_min_clearance_mm"],
            "settled_on_crawler": entry["settled_on_crawler (legs at 0)"],
            "layout_check (reference value, YAML value)": {
                "n_points": [entry["n_spheres"], layout.n_points],
                "track_centre_y_m": [entry["track_centre_y_m"], layout.track_centre_y_m]},
        }
    check = json.loads(LAYOUT_CHECK_JSON.read_text(encoding="utf-8"))
    entry = check["layouts"][LAYOUT_CHECK_KEY]
    v4 = entry["V4_quasi_static"]
    same = {
        "n_points": [entry["n_points"], layout.n_points],
        "track_centre_y_m": [check["cad_measurements"]["track_centre_y_m"],
                             layout.track_centre_y_m],
        "roller_x_m": [check["cad_measurements"]["roller_axes_x_m (left)"],
                       layout.xy_m[layout.is_roller & (layout.xy_m[:, 1] > 0), 0].tolist()],
    }
    mismatch = [k for k, (a, b) in same.items() if not np.allclose(a, b, atol=5e-4)]
    if mismatch:
        raise SystemExit(f"{LAYOUT_CHECK_JSON.name} layout {LAYOUT_CHECK_KEY} differs from the "
                         f"YAML crawler layout in {mismatch}: {same}")
    return {
        "source": f"06_analysis/00_dynamics/crawler_layout_check.json layouts."
                  f"{LAYOUT_CHECK_KEY}.V4_quasi_static (no matching YAML layout in reference.json)",
        "first_touch_leg": v4["first_touch_leg"], "first_touch_s": v4["first_touch_s"],
        "touch_s": v4["touch_s (FL, FR, RL, RR)"],
        "crawler_fully_off_s": v4["crawler_fully_off_s"],
        "leg_stop_s": None,
        "end_attitude_deg": v4["end_attitude_deg (roll, pitch)"],
        "end_crawler_min_clearance_mm": v4["end_crawler_min_clearance_mm"],
        "settled_on_crawler": entry["settled_on_crawler (legs at 0)"],
        "layout_check (reference value, YAML value)": same,
    }


def compare_with_reference(model, params, speed) -> dict:
    """Same procedure as the compliant V4 (each leg stops at its e_op) in this model."""
    e_op = np.array(params.contact.rigid_floor.L1.operating_extension_m)
    stop_s = e_op / speed

    def schedule(t):
        return np.minimum(speed * t, e_op)

    t_end = float(stop_s.max())
    kin = events(model, schedule, t_end)
    end = pose_summary(model.solve(e_op))
    ref = load_v4_reference(model.layout)
    first = min(range(4), key=lambda i: kin["touch_s"][i])
    tied = [LEG_ORDER[i] for i in range(4)
            if abs(kin["touch_s"][i] - kin["touch_s"][first]) < 1e-4]
    rows = [
        ("first touch leg", ref["first_touch_leg"], "=".join(tied)),
        ("first touch [s]", ref["first_touch_s"], round(kin["touch_s"][first], 4)),
    ]
    for i, leg in enumerate(LEG_ORDER):
        rows.append((f"touch {leg} [s]", ref["touch_s"][i], round(kin["touch_s"][i], 4)))
    stops = [round(float(s), 3) for s in stop_s]
    rows += [
        ("crawler fully off [s]", ref["crawler_fully_off_s"], round(kin["crawler_off_s"], 4)),
        ("leg stop FL/FR, RL/RR [s]", ref["leg_stop_s"] or "same procedure (YAML e_op / v)",
         stops),
        ("end roll [deg]", ref["end_attitude_deg"][0], end["roll_deg"]),
        ("end pitch [deg]", ref["end_attitude_deg"][1], end["pitch_deg"]),
        ("end crawler min clearance [mm]", ref["end_crawler_min_clearance_mm"],
         end["crawler_min_clearance_mm"]),
    ]
    return {
        "procedure": "compliant V4 (lift_V4_compliant_crawler): t = 0 all legs at +v_max, "
                     "each leg stops at contact.rigid_floor.L1.operating_extension_m",
        "reference_source": ref["source"],
        "crawler_layout": model.layout.summary(),
        "operating_extension_m": e_op.tolist(),
        "rows (quantity, reference V4 compliant, this rigid kinematic model)": rows,
        "reference_settled_on_crawler": ref["settled_on_crawler"],
        "end_state_kinematic": end,
        "kinematic_events_reference_procedure": {
            "end_shoe_first_contact_s": kin["end_shoe_first_contact_s"],
            "crawler_pivot_between_touch_and_lift_off":
                kin["crawler_pivot_between_touch_and_lift_off"],
        },
    }


# --- scene -------------------------------------------------------------------------------


def build_layers(params, parts: pd.DataFrame, render) -> tuple[dict, dict]:
    """Scene items per layer in the reference state (legs retracted, auger at the level)."""
    topologies = build_topologies(render)
    motions = classify(parts)["motion"].tolist()
    travel = np.array([0.0, 0.0, params.superstructure.auger_travel_m])
    leg_params = {leg.name: leg for leg in params.legs}
    layers = {"body": [], "barrel": {n: [] for n in LEG_ORDER}, "rod": {n: [] for n in LEG_ORDER}}
    rod_min_z = {}
    for (vertices, _), topo, row, motion in zip(render, topologies, parts.itertuples(), motions,
                                                   strict=True):
        points = body_vertices(vertices)
        leg = row.leg
        if motion in MOVING:
            points = points + travel
        if leg and row.group == "leg_rod_pad":
            spec = leg_params[leg]
            points = points + spec.retracted_offset_from_cad_m * np.array(spec.axis_direction)
            rod_min_z[leg] = float(points[:, 2].min()) if len(points) else np.nan
            layers["rod"][leg].append(SceneItem(points, topo, LEG_COLORS[leg], LEG_DEPTH_BIAS_M,
                                                fade=False))
        elif leg:
            layers["barrel"][leg].append(SceneItem(points, topo, LEG_COLORS[leg],
                                                   LEG_DEPTH_BIAS_M, fade=False))
        else:
            layers["body"].append(SceneItem(points, topo, OTHER_PART_COLOR))
    # Row-order check: the lowest point of each rod/pad mesh is its pad bottom.
    check = {}
    for leg in LEG_ORDER:
        expected = leg_params[leg].pad_bottom_center_retracted_m[2]
        check[leg] = {"mesh_min_z_m": round(rod_min_z[leg], 5), "yaml_pad_bottom_z_m": expected}
        if abs(rod_min_z[leg] - expected) > 1e-3:
            raise SystemExit(f"rod mesh of {leg} does not end at the YAML pad bottom: {check[leg]}")
    return layers, check


def scene_limits(layers, lift_m: float, ground_z: float) -> dict:
    points = np.vstack([item.vertices_m for group in ("barrel", "rod")
                        for items in layers[group].values() for item in items]
                       + [item.vertices_m for item in layers["body"]])
    lower, upper = points.min(axis=0), points.max(axis=0)
    margin = 0.25
    vertical = (ground_z - 0.45, upper[2] + lift_m + margin)
    return {"side": ((lower[0] - margin, upper[0] + margin), vertical),
            "front": ((lower[1] - margin, upper[1] + margin), vertical)}


class Canvas:
    """Figure geometry: two equal-scale panels, header above, legend below (output px)."""

    def __init__(self, limits: dict, width_px: int, dpi: float):
        self.limits = limits
        widths = {v: limits[v][0][1] - limits[v][0][0] for v, _ in PANEL_VIEWS}
        height_m = limits["side"][1][1] - limits["side"][1][0]
        self.scale = (width_px - MARGIN_LEFT - MARGIN_GAP - MARGIN_RIGHT) / sum(widths.values())
        self.width = width_px
        self.height = int(round(MARGIN_TOP + MARGIN_BOTTOM + height_m * self.scale))
        self.dpi = dpi
        self.boxes = {}  # view -> (x0, y0 from top, w, h) in output px
        x = MARGIN_LEFT
        for view, _ in PANEL_VIEWS:
            w = int(round(widths[view] * self.scale))
            self.boxes[view] = (x, MARGIN_TOP, w, int(round(height_m * self.scale)))
            x += w + MARGIN_GAP

    def figure(self, factor: int, transparent: bool):
        size = (self.width * factor / self.dpi, self.height * factor / self.dpi)
        figure = plt.figure(figsize=size, dpi=self.dpi,
                            facecolor="none" if transparent else SURFACE)
        axes = {}
        for view, _ in PANEL_VIEWS:
            x0, y0, w, h = self.boxes[view]
            rect = (x0 / self.width, 1 - (y0 + h) / self.height, w / self.width, h / self.height)
            ax = figure.add_axes(rect)
            ax.set_xlim(*self.limits[view][0])
            ax.set_ylim(*self.limits[view][1])
            if transparent:
                ax.set_axis_off()
                ax.patch.set_alpha(0.0)
            axes[view] = ax
        return figure, axes

    def to_screen(self, view: str, point_m) -> tuple[float, float]:
        """Data (h, v) [m] -> output pixel (x right, y down) in the full frame."""
        x0, y0, _, _ = self.boxes[view]
        (h0, _), (_, v1) = self.limits[view]
        return x0 + (point_m[0] - h0) * self.scale, y0 + (v1 - point_m[1]) * self.scale


def render_image(figure) -> Image.Image:
    figure.canvas.draw()
    image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")
    plt.close(figure)
    return image


def downsample(image: Image.Image, size) -> Image.Image:
    return image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def render_layer(canvas: Canvas, view: str, items, style) -> Image.Image:
    """One layer of one view, cropped to the panel box, at output resolution (RGBA)."""
    figure, axes = canvas.figure(SUPERSAMPLE, transparent=True)
    if items:
        # Line widths are in points: at SUPERSAMPLE x the canvas the effective dpi is lower.
        scene = shade_scene(items, view, canvas.scale, style, canvas.dpi / SUPERSAMPLE)
        axes[view].add_collection(scene_collection(scene), autolim=False)
    image = render_image(figure)
    x0, y0, w, h = canvas.boxes[view]
    s = SUPERSAMPLE
    return downsample(image.crop((x0 * s, y0 * s, (x0 + w) * s, (y0 + h) * s)), (w, h))


def render_static(canvas: Canvas, ground_z: float) -> tuple[Image.Image, Image.Image]:
    """Background (axes, grid, earth, legend) and the ground line drawn above the meshes."""
    figure, axes = canvas.figure(SUPERSAMPLE, transparent=False)
    names = {"side": ("x 전방 [m]", "z 상방 [m]"), "front": ("y 좌측 [m]", "")}
    for view, title in PANEL_VIEWS:
        ax = axes[view]
        ax.set_facecolor(SURFACE)
        ax.grid(True, color="#e4e3df", lw=0.5 * SUPERSAMPLE)
        ax.set_axisbelow(True)
        ax.axhspan(canvas.limits[view][1][0], ground_z, color=EARTH_COLOR, alpha=0.30, lw=0)
        ax.set_title(title, fontsize=9 * SUPERSAMPLE, loc="left", color=INK_PRIMARY)
        ax.set_xlabel(names[view][0], fontsize=8 * SUPERSAMPLE, color=INK_SECONDARY)
        ax.set_ylabel(names[view][1], fontsize=8 * SUPERSAMPLE, color=INK_SECONDARY)
        ax.tick_params(labelsize=7 * SUPERSAMPLE, colors=INK_SECONDARY)
    handles = [Rectangle((0, 0), 1, 1, color=LEG_COLORS[leg], label=f"{leg} 다리")
               for leg in LEG_ORDER]
    handles.append(Rectangle((0, 0), 1, 1, color=OTHER_PART_COLOR, label="상부체(크롤러 포함)"))
    handles.append(Rectangle((0, 0), 1, 1, color=EARTH_COLOR, alpha=0.3,
                             label="지면 아래 (지면 = 크롤러 바닥, 강체 평지)"))
    figure.legend(handles=handles, loc="lower center", ncol=6, frameon=False,
                  fontsize=7.5 * SUPERSAMPLE, labelcolor=INK_SECONDARY)
    background = downsample(render_image(figure), (canvas.width, canvas.height))
    figure, axes = canvas.figure(SUPERSAMPLE, transparent=True)
    for view, _ in PANEL_VIEWS:
        axes[view].axhline(ground_z, color=INK_PRIMARY, lw=0.9 * SUPERSAMPLE)
    ground = downsample(render_image(figure), (canvas.width, canvas.height))
    return background, ground


# --- per-frame geometry ------------------------------------------------------------------


def rotation(roll: float, pitch: float) -> np.ndarray:
    cr, sr, cp, sp = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    return ry @ rx


def screen_motion(view, q, extension, extension_direction, depth_range, half_extent, scale):
    """Screen translation [px] of the body and rod layers, and the neglected tilt terms [px]."""
    right, up, toward = VIEWS[view]
    basis = np.stack([right, up])
    rot = rotation(q[1], q[2])
    shift_body = basis @ np.array([0.0, 0.0, q[0]])
    shift_rod = shift_body + basis @ (rot @ (extension * extension_direction))
    in_plane = basis @ rot @ basis.T - np.eye(2)
    out_of_plane = basis @ rot @ toward
    neglected = (np.abs(in_plane).sum(axis=1).max() * half_extent
                 + np.abs(out_of_plane).max() * depth_range) * scale
    to_px = np.array([scale, -scale])
    return shift_body * to_px, shift_rod * to_px, float(neglected)


def leg_depth_order(params, view: str) -> tuple[list[str], list[str]]:
    toward = VIEWS[view][2]
    depth = {leg.name: float(np.array(leg.pad_bottom_center_retracted_m) @ toward)
             for leg in params.legs}
    median = np.median(list(depth.values()))
    far = [n for n in LEG_ORDER if depth[n] < median]
    return far, [n for n in LEG_ORDER if n not in far]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = font_manager.findfont(font_manager.FontProperties(
        family="Malgun Gothic", weight="bold" if bold else "normal"))
    return ImageFont.truetype(path, size)


class Header:
    """Per-frame text drawn with PIL at output resolution."""

    def __init__(self, speedup: float, level: str, speed: float, stroke: float):
        self.fonts = {"title": font(15, True), "text": font(13), "small": font(11),
                      "banner": font(14, True)}
        self.title = (f"아우트리거 4개 동시 신장 0 → {stroke * MM_PER_M:.0f} mm "
                      f"({speed * MM_PER_M:.2f} mm/s) · 기구학 준정적 · 강체 평지 · 오거 {level}")
        self.speedup = speedup

    def draw(self, frame: Image.Image, t: float, extension: float, state: dict,
             banner: str | None) -> None:
        draw = ImageDraw.Draw(frame)
        x = MARGIN_LEFT
        draw.text((x, 10), self.title, font=self.fonts["title"], fill=INK_PRIMARY)
        draw.text((frame.width - MARGIN_RIGHT, 10), f"{self.speedup:g}배속",
                  font=self.fonts["title"], fill="#c0392b", anchor="ra")
        draw.text((x, 38), f"경과 시간 t = {t:6.2f} s (실제)     "
                  f"신장량 e = {extension * MM_PER_M:6.1f} mm",
                  font=self.fonts["text"], fill=INK_PRIMARY)
        cx = x
        draw.text((cx, 63), "접지:", font=self.fonts["text"], fill=INK_PRIMARY)
        cx += 44
        for leg, contact in zip(LEG_ORDER, state["pad_contact"], strict=True):
            colour = LEG_COLORS[leg]
            box = (cx, 64, cx + 76, 84)
            if contact:
                draw.rounded_rectangle(box, 5, fill=colour)
                draw.text((cx + 38, 74), f"{leg} 접지", font=self.fonts["small"], fill="white",
                          anchor="mm")
            else:
                draw.rounded_rectangle(box, 5, outline=colour, width=2)
                draw.text((cx + 38, 74), f"{leg} 공중", font=self.fonts["small"], fill=colour,
                          anchor="mm")
            cx += 84
        crawler = max(state["crawler_clearance_m"], 0.0) * MM_PER_M
        crawler_text = "접지" if state["crawler_contact"] else "들림"
        draw.text((cx + 8, 63), f"크롤러 {crawler_text}", font=self.fonts["text"],
                  fill=INK_PRIMARY)
        q = state["q"]
        draw.text((x, 92), f"크롤러 바닥 높이(지면 위, 최저점) = {crawler:6.1f} mm     "
                  f"roll = {np.degrees(q[1]) + 0.0:+.3f}°   "
                  f"pitch = {np.degrees(q[2]) + 0.0:+.3f}° (+ = 앞 내림)",
                  font=self.fonts["text"], fill=INK_PRIMARY)
        if banner:
            draw.text((x, 117), banner, font=self.fonts["banner"], fill="#c0392b")


# --- timeline ----------------------------------------------------------------------------


def timeline(t_end: float, speedup: float, fps: float, hold_start: float, hold_end: float,
             hold_event: float, event_times: dict) -> list[tuple[float, float, str | None]]:
    """(real time, duration ms, banner) per frame; event frames are held."""
    step = speedup / fps
    times = list(np.arange(0.0, t_end, step)) + [t_end]
    for t in event_times:
        times.append(t)
    times = sorted(set(round(t, 6) for t in times))
    frame_ms = 1000.0 / fps
    frames = []
    for t in times:
        banner = next((text for te, text in event_times.items() if abs(te - t) < 1e-6), None)
        if t == 0.0:
            duration = hold_start * 1000
        elif t == round(t_end, 6):
            duration = hold_end * 1000
        elif banner:
            duration = hold_event * 1000
        else:
            duration = frame_ms
        frames.append((t, duration, banner))
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--speedup", type=float, default=3.0, help="playback / real time")
    parser.add_argument("--fps", type=float, default=12.5)
    parser.add_argument("--hold-start-s", type=float, default=1.0)
    parser.add_argument("--hold-end-s", type=float, default=1.5)
    parser.add_argument("--hold-event-s", type=float, default=0.6)
    parser.add_argument("--width-px", type=int, default=900)
    parser.add_argument("--colors", type=int, default=256, help="global GIF palette size")
    parser.add_argument("--level", default=None, help="auger level (default: YAML default)")
    parser.add_argument("--output", type=Path, default=GIF_PATH)
    edge_style_arguments(parser)
    arguments = parser.parse_args()
    started = time.perf_counter()
    dpi = 100.0
    style = edge_style_from(arguments)

    params = load_params(level=arguments.level)
    speed, stroke = params.actuator.max_speed_m_s, params.actuator.stroke_m
    model = QuasiStaticLift(params)
    t_end = stroke / speed

    def schedule(t):
        return np.full(4, min(speed * t, stroke))

    gif_events = events(model, schedule, t_end)
    final_state = model.solve(schedule(t_end))
    comparison = compare_with_reference(model, params, speed)

    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")
    render, cache_valid = load_render_meshes(parts["instance_path"].tolist())
    layers, rod_check = build_layers(params, parts, render)
    limits = scene_limits(layers, float(final_state["q"][0]), model.ground_z)
    canvas = Canvas(limits, arguments.width_px, dpi)

    t0 = time.perf_counter()
    view_layers = {}
    depth_info = {}
    for view, _ in PANEL_VIEWS:
        far, near = leg_depth_order(params, view)
        stack = [("body", layers["body"])]
        for group in (far, near):
            stack.append(("rod", [i for n in group for i in layers["rod"][n]]))
            stack.append(("body", [i for n in group for i in layers["barrel"][n]]))
        view_layers[view] = [(kind, render_layer(canvas, view, items, style))
                             for kind, items in stack]
        toward = VIEWS[view][2]
        right, up = VIEWS[view][0], VIEWS[view][1]
        all_points = np.vstack([i.vertices_m for _, items in stack for i in items])
        depth = all_points @ toward
        screen = np.stack([all_points @ right, all_points @ up], axis=1)
        depth_info[view] = (float(np.abs(depth).max()), float(np.abs(screen).max()))
    background, ground_layer = render_static(canvas, model.ground_z)
    layer_s = time.perf_counter() - t0

    touch = gif_events["touch_s"]
    off = gif_events["crawler_off_s"]
    # Events closer than EVENT_MERGE_S share one held frame, drawn just after the last of them
    # so that every contact flag of the cluster is already set.
    clusters = []
    for t, label in sorted([(v, LEG_ORDER[i]) for i, v in enumerate(touch)] + [(off, None)]):
        if clusters and t - clusters[-1][-1][0] < EVENT_MERGE_S:
            clusters[-1].append((t, label))
        else:
            clusters.append([(t, label)])
    event_times = {}
    for cluster in clusters:
        t_frame = round(cluster[-1][0] + 2 * EVENT_TOL_S, 6)
        legs = [label for _, label in cluster if label]
        parts_text = []
        if legs:
            parts_text.append(f"{'·'.join(legs)} 패드 접지")
        if any(label is None for _, label in cluster):
            parts_text.append("크롤러 지면에서 떨어짐" if legs == [] else "크롤러 들림 시작")
        event_times[t_frame] = f"▶ {' → '.join(parts_text)} (t = {cluster[0][0]:.3f} s)"
    plan = timeline(t_end, arguments.speedup, arguments.fps, arguments.hold_start_s,
                    arguments.hold_end_s, arguments.hold_event_s, event_times)
    header = Header(arguments.speedup, params.level.value, speed, stroke)

    frames, durations, neglected_px, records = [], [], 0.0, []
    for t, duration, banner in plan:
        extension = min(speed * t, stroke)
        state = model.solve(np.full(4, extension))
        frame = background.copy()
        for view, _ in PANEL_VIEWS:
            x0, y0, w, h = canvas.boxes[view]
            shift_body, shift_rod, neglected = screen_motion(
                view, state["q"], extension, model.extension_direction, *depth_info[view],
                canvas.scale)
            neglected_px = max(neglected_px, neglected)
            panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            for kind, layer in view_layers[view]:
                shift = shift_rod if kind == "rod" else shift_body
                moved = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                moved.paste(layer, (int(round(shift[0])), int(round(shift[1]))))
                panel = Image.alpha_composite(panel, moved)
            frame.alpha_composite(panel, (x0, y0))
        frame = Image.alpha_composite(frame, ground_layer).convert("RGB")
        header.draw(frame, t, extension, state, banner)
        frames.append(frame)
        durations.append(int(round(duration / 10.0)) * 10)
        records.append({"t_s": round(t, 4), "extension_mm": round(extension * MM_PER_M, 2),
                        **pose_summary(state)})

    # One palette for all frames (no flicker); a swatch strip keeps the leg and text colours.
    sample_ids = [0, len(frames) // 2, len(frames) - 1]
    sample = Image.new("RGB", (frames[0].width * len(sample_ids), frames[0].height + 40))
    for k, i in enumerate(sample_ids):
        sample.paste(frames[i], (k * frames[0].width, 0))
    swatches = [LEG_COLORS[leg] for leg in LEG_ORDER] + ["#c0392b", INK_PRIMARY, "white"]
    swatch_w = sample.width // len(swatches)
    for k, colour in enumerate(swatches):
        sample.paste(Image.new("RGB", (swatch_w, 40), colour), (k * swatch_w, frames[0].height))
    palette = sample.quantize(colors=arguments.colors, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(arguments.output, save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, optimize=False, disposal=1)

    kinematics = {
        "meta": {
            "script": "04_scripts/00_cad/render_leg_extension.py",
            "params": params.source_path.relative_to(PROJECT_ROOT).as_posix(),
            "params_sha256": params.sha256,
            "auger_level": params.level.value,
            "frame": "body: x forward, y left, z up, origin = CAD origin; pitch + = nose down",
            "model": "quasi-static rigid body, rigid level ground at ground.crawler_bottom_z_m, "
                     "unilateral rigid contacts at the 4 pad bottom centres and the crawler "
                     "contact points of contact.crawler.sphere_layout (layout D: 12 roller "
                     "points on the floor + 12 end-shoe points raised by end_shoe_gap_m); "
                     "pose = min CoM height (LP); 4 pads only -> least "
                     "squares; x, y, yaw fixed; small angles; rod weight not in the potential; "
                     "pads keep the body orientation (swivel not modelled, tilt <= 0.13 deg)",
            "contact_tolerance_m": CONTACT_TOL_M,
            "crawler_layout": model.layout.summary(),
        },
        "gif_schedule": {
            "description": "all legs e(t) = min(v t, stroke)",
            "speed_m_s": speed,
            "stroke_m": stroke,
            "t_end_s": t_end,
            "touch_s (FL, FR, RL, RR)": [round(v, 4) for v in touch],
            "crawler_off_s": round(gif_events["crawler_off_s"], 4),
            "end_shoe_first_contact_s": gif_events["end_shoe_first_contact_s"],
            "crawler_pivot_between_touch_and_lift_off":
                gif_events["crawler_pivot_between_touch_and_lift_off"],
            "end_state": pose_summary(final_state),
        },
        "reference_comparison": comparison,
        "rod_mesh_check": rod_check,
        "frames": records,
    }
    KINEMATICS_JSON.write_text(json.dumps(kinematics, ensure_ascii=False, indent=1),
                               encoding="utf-8")
    report = {
        "output": str(arguments.output),
        "size_bytes": arguments.output.stat().st_size,
        "frames": len(indexed),
        "resolution_px": list(indexed[0].size),
        "fps_moving": arguments.fps,
        "loop_s": round(sum(durations) / 1000.0, 2),
        "palette_colors": arguments.colors,
        "px_per_m": round(canvas.scale, 3),
        "neglected_tilt_max_px": round(neglected_px, 3),
        "render_cache_used": cache_valid,
        "edge_style": asdict(style),
        "events_gif": kinematics["gif_schedule"],
        "reference_rows": comparison["rows (quantity, reference V4 compliant, this rigid "
                                     "kinematic model)"],
        "end_state_reference_procedure": comparison["end_state_kinematic"],
        "kinematics_json": str(KINEMATICS_JSON),
        "layer_render_s": round(layer_s, 1),
        "total_s": round(time.perf_counter() - started, 1),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
