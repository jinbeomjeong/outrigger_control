"""Animated GIFs of the S1 runs (L1 superstructure + locked legs + ground bushing, static).

Reads only stored results (no simulation is run):
    07_results/S1/<case>/record.npz + meta.json   Record (outrigger_sim.record.load_record)
    07_results/S1/<case>/result.json              still window, linear cross check, checks
    06_analysis/00_dynamics/s1_pdelta_check.json  independent nonlinear statics per level
    02_params/rexome33.yaml                       geometry (pad sphere centres, auger travel)
    01_cad/01_parts/parts_classified.csv          part rows (leg, group, auger moving set)
    01_cad/05_meshes/render_mesh.npz              decimated drawing meshes, same row order

Writes (06_analysis/01_chrono/11_S1/):
    S1_settle_levels.gif   analytic-start cases top -> middle -> bottom (15 s each, compressed),
                           ending with the auger-level comparison scene
    S1_cross_top.gif       no-init drop from the zero pose (58 s), non-linear time axis
    S1_auger_levels.png    the comparison scene (final settled states, leg load bars)
    S1_cross_top_frame.png a representative frame of the cross case (rear pad lift-off)
    S1_gifs.json           frame plan, sizes, value checks

Frame content
    Left: oblique 3D view of the machine (CAD render mesh, shaded, black outlines) in its
    settled pose at true scale, level rigid floor, ground reaction arrows at the pads
    (length proportional to the pad contact force, kN labels), bushing anchors, centre of
    mass. Body displacements are millimetres, so the 3D view does not move visibly.
    Attitude and penetration are drawn magnified in two schematic insets (side x-z for pitch,
    front y-z for roll): vertical displacements from the zero pose (level, pads just touching)
    times --exaggeration (stated on the frame); horizontal positions true. One factor for
    translation and rotation keeps the pad-ground geometry consistent (all pads sink by k
    times their penetration; magnifying only the angles would show the rear pads floating).
    Right: time series with a cursor. Settle cases: contact force per leg [kN] with the
    linear (result.json linear_static_cross_check) and nonlinear (s1_pdelta_check.json)
    reference lines, roll and pitch [deg] with the V3 band (reference +- tolerance from
    result.json), penetration [mm]. Cross case: log time axis, contact force, deviation from
    the linear reference (symlog, V1 band), attitude, penetration, bushing tangential force x.

Derived quantities (body frame x forward, y left, z up; world = body at the zero pose; SI):
    roll, pitch = outrigger_sim.frames.roll_pitch_from_quat(body_quat_wxyz), pitch + = nose down
    penetration_i = r_i - (o_z + (R c_i)_z - z_floor), c_i = pad sphere centre in body
        coordinates at the locked extension s_motor (outrigger_sim.geometry), r_i = swivel
        height above the pad bottom; equals the probe definition (checked against the
        still-window mean of result.json, tolerance 1e-6 mm).

Usage (Chrono-dev python):
    python -I -u 04_scripts/02_chrono/render_S1_gifs.py [--only settle|cross|all]
        [--exaggeration 500] [--cross-exaggeration 300] [--mesh-cache PATH]
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "04_scripts" / "00_cad"))
sys.path.insert(0, str(ROOT / "03_src"))

from analyze_auger_levels import MOVING, classify  # noqa: E402
from analyze_parts import (  # noqa: E402
    CLASSIFIED_CSV,
    INK_PRIMARY,
    INK_SECONDARY,
    LEG_COLORS,
    LEG_ORDER,
    OTHER_PART_COLOR,
    SURFACE,
)
from render_auger_descent import load_render_meshes  # noqa: E402
from render_layout_views import (  # noqa: E402
    LEG_DEPTH_BIAS_M,
    VIEWS,
    EdgeStyle,
    SceneItem,
    body_vertices,
    build_topologies,
    part_topology,
    scene_collection,
    shade_scene,
)

from outrigger_sim.frames import quat_to_matrix, roll_pitch_from_quat  # noqa: E402
from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_record  # noqa: E402

RESULTS = ROOT / "07_results" / "S1"
OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "11_S1"
PDELTA_JSON = ROOT / "06_analysis" / "00_dynamics" / "s1_pdelta_check.json"
GIF_SETTLE = OUT_DIR / "S1_settle_levels.gif"
GIF_CROSS = OUT_DIR / "S1_cross_top.gif"
PNG_LEVELS = OUT_DIR / "S1_auger_levels.png"
PNG_CROSS = OUT_DIR / "S1_cross_top_frame.png"
SUMMARY_JSON = OUT_DIR / "S1_gifs.json"
SETTLE_CASES = ("top", "middle", "bottom")
CROSS_CASE = "cross_top"
LEVEL_LABEL = {"top": "상단", "middle": "중단", "bottom": "하단"}

FRAME_W, FRAME_H, DPI = 1400, 900, 100
SUPERSAMPLE = 2
EARTH_COLOR = "#8a6a45"
GROUND_COLOR = "#d9cfc0"
ACCENT = "#c0392b"
LIN_COLOR = "#7d7c78"
NL_COLOR = INK_PRIMARY
BAND_COLOR = "#cfe3f5"
INSET_BAR_H_M = 3.2  # inset: schematic body bar above the floor [display m]
INSET_Z_RANGE = (-3.5, 4.3)
FT_LINTHRESH_KN = 5.0
CROSS_SLOW_END_S = 0.4  # cross GIF: every 10 ms record sample up to here, then log-spaced
INSET_SIDE_BOX = (52, 112, 250, 200)  # output px (x, y from top, w, h)
INSET_FRONT_BOX = (52, 344, 170, 160)
ARROW_M_PER_N = 1.0 / 100e3  # ground reaction arrow: 1 m per 100 kN (world length)
PEN_CHECK_TOL_MM = 1e-6
# Oblique camera: viewer in front (+x), on the right (-y) and above.
_TOWARD = np.array([0.60, -0.66, 0.45])
_TOWARD /= np.linalg.norm(_TOWARD)
_RIGHT = np.cross([0.0, 0.0, 1.0], _TOWARD)
_RIGHT /= np.linalg.norm(_RIGHT)
_UP = np.cross(_TOWARD, _RIGHT)
VIEWS["oblique"] = (_RIGHT, _UP, _TOWARD)
GROUND_RECT_XY = ((-4.8, 5.6), (-3.2, 3.2))  # drawn floor patch [m]
GROUND_GRID_M = 1.0
BELOW_GROUND_TOL_M = 0.02  # faces lower than this under the floor are drawn below it

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# --- data --------------------------------------------------------------------------------


@dataclass
class CaseData:
    """One S1 case: Record series, derived series and reference values (SI unless named)."""

    name: str
    level: str
    params: object
    t: np.ndarray
    F: np.ndarray  # (n, 4) pad contact force normal [N]
    F_cyl: np.ndarray
    Ft_x: np.ndarray  # (n, 4) bushing tangential force, world x [N]
    roll_deg: np.ndarray
    pitch_deg: np.ndarray
    pen_mm: np.ndarray  # (n, 4), negative = gap
    contact: np.ndarray  # (n, 4) bool
    pos: np.ndarray  # (n, 3) body origin, world [m]
    rot: np.ndarray  # (n, 3, 3)
    anchors: np.ndarray  # (n, 4, 3)
    s_motor: np.ndarray  # (4,) locked extension [m]
    events: list  # (t, leg index, kind 1 create / 2 remove)
    result: dict
    lin: dict
    nl: dict
    v3_ref: np.ndarray
    v3_tol: float
    v1_tol: float
    weight_N: float
    still_start_s: float
    zero_origin: np.ndarray
    floor_z: float
    sphere_centres_body: np.ndarray  # (4, 3)
    sphere_radius: np.ndarray  # (4,)
    checks: dict = field(default_factory=dict)

    def index(self, t: float) -> int:
        return int(np.clip(np.searchsorted(self.t, t - 1e-9), 0, len(self.t) - 1))

    def pad_bottom_world(self, i: int) -> np.ndarray:
        c = self.sphere_centres_body @ self.rot[i].T + self.pos[i]
        return c - np.outer(self.sphere_radius, [0.0, 0.0, 1.0])


def _check(result: dict, check_id: str, prefix: str) -> dict:
    for c in result["checks"]:
        if c["id"] == check_id and c["item"].startswith(prefix):
            return c
    raise KeyError(f"{check_id} '{prefix}' not in result.json")


def load_case(name: str, pdelta: dict) -> CaseData:
    level = name.removeprefix("cross_")
    params = load_params(level=level)
    run_dir = RESULTS / name
    record = load_record(run_dir, params_sha256=params.sha256)
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    a = record.arrays
    rot = quat_to_matrix(a["body_quat_wxyz"])
    roll, pitch = roll_pitch_from_quat(a["body_quat_wxyz"])
    s_motor = np.array(a["s_ref"][-1], dtype=float)
    if np.abs(a["s_motor"] - s_motor).max() > 1e-9:
        raise SystemExit(f"{name}: s_motor departs from the locked s_ref (legs not locked)")
    centres = np.array([pad_sphere_centre_body_m(params, i, s_motor[i]) for i in range(4)])
    radius = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    floor = params.ground.crawler_bottom_z_m
    centre_z = np.einsum("nij,kj->nki", rot, centres)[..., 2]
    pen_mm = (radius - (a["body_pos"][:, 2:3] + centre_z - floor)) * 1e3
    still = result["still_window"]
    t = np.asarray(a["t"], dtype=float)
    in_still = t > still["t_start_s"] - 1e-9
    pen_dev = float(np.abs(pen_mm[in_still].mean(axis=0) - still["penetration_mean_mm"]).max())
    att_dev = float(max(abs(np.degrees(roll[in_still]).mean() - still["roll_mean_deg"]),
                        abs(np.degrees(pitch[in_still]).mean() - still["pitch_mean_deg"])))
    if pen_dev > PEN_CHECK_TOL_MM:
        raise SystemExit(f"{name}: penetration from the Record differs from result.json by "
                         f"{pen_dev} mm")
    lin_src = result["linear_static_cross_check"]
    lin = {"F_N": np.array(lin_src["contact_N"]), "pen_mm": np.array(lin_src["penetration_mm"]),
           "att_deg": np.array(lin_src["roll_pitch_deg"])}
    p = pdelta[level]
    nl = {"F_N": np.array(p["nonlinear_contact_N"]), "pen_mm": np.array(p["nonlinear_pen_mm"]),
          "att_deg": np.array(p["nonlinear_roll_pitch_deg"]), "h_m": p["h_cg_above_ball_m"],
          "com_m": p["com_m"]}
    v3 = _check(result, "V3", "attitude (roll, pitch)")
    v1 = _check(result, "V1", "pad contact force per leg")
    zero_z = result["start"].get("zero_pose_origin_z_m")
    if zero_z is None:  # cross case starts from the zero pose itself
        zero_z = result["start"]["origin_m"][2]
    events = list(zip(record.bushing_events["t"].tolist(), record.bushing_events["leg"].tolist(),
                      record.bushing_events["kind"].tolist(), strict=True))
    return CaseData(
        name=name, level=level, params=params, t=t, F=np.asarray(a["F_contact_n"]),
        F_cyl=np.asarray(a["F_cyl"]), Ft_x=np.asarray(a["F_contact_t"])[:, :, 0],
        roll_deg=np.degrees(roll), pitch_deg=np.degrees(pitch), pen_mm=pen_mm,
        contact=np.asarray(a["pad_in_contact"]), pos=np.asarray(a["body_pos"]), rot=rot,
        anchors=np.asarray(a["bushing_anchor"]), s_motor=s_motor, events=events, result=result,
        lin=lin, nl=nl, v3_ref=np.array(v3["ref"]), v3_tol=float(v3["tol"]),
        v1_tol=float(v1["tol"]), weight_N=float(lin_src["total_weight_N"]),
        still_start_s=float(still["t_start_s"]), zero_origin=np.array([0.0, 0.0, zero_z]),
        floor_z=floor, sphere_centres_body=centres, sphere_radius=radius,
        checks={"penetration_vs_result_json_max_abs_mm": pen_dev,
                "attitude_vs_result_json_max_abs_deg": att_dev,
                "params_sha256": params.sha256},
    )


# --- mesh scene ----------------------------------------------------------------------------


def load_meshes(cache: Path | None):
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")
    if cache is not None and cache.exists():
        with open(cache, "rb") as handle:
            render = pickle.load(handle)
    else:
        render, _ = load_render_meshes(parts["instance_path"].tolist())
        if cache is not None:
            with open(cache, "wb") as handle:
                pickle.dump(render, handle, protocol=5)
    if len(render) != len(parts):
        raise SystemExit("render mesh rows differ from parts_classified.csv")
    return parts, render, build_topologies(render)


def body_items(parts, render, topologies, params, s_motor) -> list[tuple]:
    """(body-frame vertices [m], topology, colour, depth bias, fade) at the auger level and
    the locked extensions; rods moved like render_leg_extension.build_layers."""
    motions = classify(parts)["motion"].tolist()
    travel = np.array([0.0, 0.0, params.superstructure.auger_travel_m])
    direction = extension_direction(params)
    legs = {leg.name: (i, leg) for i, leg in enumerate(params.legs)}
    items = []
    for (vertices, _), topo, row, motion in zip(render, topologies, parts.itertuples(), motions,
                                                   strict=True):
        points = body_vertices(vertices)
        if motion in MOVING:
            points = points + travel
        if row.leg:
            i, spec = legs[row.leg]
            if row.group == "leg_rod_pad":
                points = (points + spec.retracted_offset_from_cad_m * np.array(spec.axis_direction)
                          + s_motor[i] * direction)
            items.append((points, topo, LEG_COLORS[row.leg], LEG_DEPTH_BIAS_M, False))
        else:
            items.append((points, topo, OTHER_PART_COLOR, 0.0, True))
    return items


def world_items(items, pos, rot, floor_z):
    """SceneItems in world coordinates, split at the floor (below, above)."""
    below, above = [], []
    for points, topo, colour, bias, fade in items:
        world = points @ rot.T + pos
        if len(topo.faces) == 0:
            continue
        centroid_z = world[topo.faces][:, :, 2].mean(axis=1)
        low = centroid_z < floor_z - BELOW_GROUND_TOL_M
        if not low.any():
            above.append(SceneItem(world, topo, colour, bias, fade))
            continue
        for mask, target in ((low, below), (~low, above)):
            if mask.any():
                target.append(SceneItem(world, part_topology(world, topo.faces[mask]), colour,
                                        bias, fade))
    return below, above


def screen(points, view="oblique"):
    right, up, _ = VIEWS[view]
    points = np.atleast_2d(points)
    return np.stack([points @ right, points @ up], axis=1)


def ground_polygon(floor_z: float) -> np.ndarray:
    (x0, x1), (y0, y1) = GROUND_RECT_XY
    return np.array([[x0, y0, floor_z], [x1, y0, floor_z], [x1, y1, floor_z], [x0, y1, floor_z]])


def render_mesh_image(below, above, floor_z, limits, size_px, view="oblique",
                      style=EdgeStyle()) -> Image.Image:
    """Shaded mesh with the floor patch, as an RGBA image of the axes box (output px)."""
    w, h = size_px
    s = SUPERSAMPLE
    figure = plt.figure(figsize=(w * s / DPI, h * s / DPI), dpi=DPI, facecolor="none")
    ax = figure.add_axes((0, 0, 1, 1))
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_axis_off()
    ax.patch.set_alpha(0.0)
    scale = w / (limits[0][1] - limits[0][0])
    if below:
        ax.add_collection(scene_collection(shade_scene(below, view, scale, style, DPI / s),
                                           zorder=1), autolim=False)
    if view == "oblique":
        ground = screen(ground_polygon(floor_z), view)
        ax.add_patch(Polygon(ground, closed=True, facecolor=GROUND_COLOR, alpha=0.82,
                             edgecolor=EARTH_COLOR, lw=0.8 * s, zorder=2))
        (x0, x1), (y0, y1) = GROUND_RECT_XY
        for x in np.arange(np.ceil(x0), x1 + 1e-9, GROUND_GRID_M):
            seg = screen(np.array([[x, y0, floor_z], [x, y1, floor_z]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * s, alpha=0.5, zorder=2.1)
        for y in np.arange(np.ceil(y0), y1 + 1e-9, GROUND_GRID_M):
            seg = screen(np.array([[x0, y, floor_z], [x1, y, floor_z]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * s, alpha=0.5, zorder=2.1)
    else:
        ax.axhline(floor_z, color=INK_PRIMARY, lw=0.9 * s, zorder=2.2)
        ax.axhspan(limits[1][0], floor_z, color=EARTH_COLOR, alpha=0.25, lw=0, zorder=2)
    ax.add_collection(scene_collection(shade_scene(above, view, scale, style, DPI / s),
                                       zorder=3), autolim=False)
    figure.canvas.draw()
    image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")
    plt.close(figure)
    return image.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")


def fit_limits(points_2d: np.ndarray, size_px, margin_m=(0.3, 0.3)) -> tuple:
    """Equal-scale limits that hold the points in an axes box of size_px (w, h)."""
    lo, hi = points_2d.min(axis=0) - margin_m, points_2d.max(axis=0) + margin_m
    w, h = size_px
    span = hi - lo
    scale = min(w / span[0], h / span[1])
    centre = 0.5 * (lo + hi)
    half = np.array([w, h]) / scale / 2
    return ((centre[0] - half[0], centre[0] + half[0]), (centre[1] - half[1], centre[1] + half[1]))


# --- figure pieces -------------------------------------------------------------------------


def axes_px(fig, x, y, w, h):
    """Axes at output pixel box (x, y from the top-left)."""
    return fig.add_axes((x / FRAME_W, 1 - (y + h) / FRAME_H, w / FRAME_W, h / FRAME_H))


def style_axes(ax, title=None, ylabel=None, xlabel=None):
    ax.set_facecolor("white")
    ax.grid(True, color="#e4e3df", lw=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7.5, colors=INK_SECONDARY, length=2.5)
    for spine in ax.spines.values():
        spine.set_color("#b9b8b3")
        spine.set_linewidth(0.6)
    if title:
        ax.set_title(title, fontsize=9, loc="left", color=INK_PRIMARY, pad=3)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=INK_SECONDARY, labelpad=2)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8, color=INK_SECONDARY, labelpad=1)


class Cursor:
    """Vertical time cursor plus current-value dots on a set of axes."""

    def __init__(self):
        self.lines = []
        self.dots = []  # (line2d, x array, y array)

    def add_axes(self, ax):
        self.lines.append(ax.axvline(np.nan, color=ACCENT, lw=1.0, zorder=6))

    def add_dot(self, ax, t, y, colour):
        (dot,) = ax.plot([np.nan], [np.nan], "o", ms=3.8, color=colour, mec="white", mew=0.6,
                         zorder=7)
        self.dots.append((dot, t, y))

    def update(self, t_now, i):
        for line in self.lines:
            line.set_xdata([t_now, t_now])
        for dot, t, y in self.dots:
            dot.set_data([t[i]], [y[i]])


class Scene3D:
    """Oblique 3D axes: mesh image + per-frame ground reaction arrows and labels."""

    def __init__(self, fig, box, limits, image):
        self.ax = axes_px(fig, *box)
        self.ax.set_xlim(*limits[0])
        self.ax.set_ylim(*limits[1])
        self.ax.set_axis_off()
        self.image = self.ax.imshow(np.asarray(image), extent=(*limits[0], *limits[1]),
                                    origin="upper", interpolation="nearest", zorder=0,
                                    aspect="auto")
        self.arrows = []
        self.labels = []
        self.anchor_marks = []
        for leg in LEG_ORDER:
            arrow = FancyArrowPatch((0, 0), (0, 0), arrowstyle="-|>,head_length=6,head_width=3.5",
                                    color=LEG_COLORS[leg], lw=2.2, zorder=5, shrinkA=0,
                                    shrinkB=0)
            self.ax.add_patch(arrow)
            self.arrows.append(arrow)
            self.labels.append(self.ax.text(0, 0, "", fontsize=8.5, color=LEG_COLORS[leg],
                                            ha="center", va="top", zorder=6,
                                            fontweight="bold",
                                            bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                                      ec="none", alpha=0.8)))
            (mark,) = self.ax.plot([], [], "x", color=INK_PRIMARY, ms=5, mew=1.2, zorder=4)
            self.anchor_marks.append(mark)
        (self.com,) = self.ax.plot([], [], "X", ms=9, color="#e2245c", mec="white", mew=0.8,
                                   zorder=6)
        self.com_text = self.ax.text(0, 0, "", fontsize=7.5, color="#e2245c", zorder=6,
                                     va="center", bbox=dict(boxstyle="round,pad=0.15",
                                                             fc="white", ec="none", alpha=0.8))

    def update(self, case: CaseData, i: int):
        bottoms = case.pad_bottom_world(i)
        for k in range(4):
            force = case.F[i, k]
            base = bottoms[k]
            tail = base - np.array([0.0, 0.0, max(force, 0.0) * ARROW_M_PER_N])
            sb, st = screen(base)[0], screen(tail)[0]
            if case.contact[i, k] and force > 0:
                self.arrows[k].set_positions(tuple(st), tuple(sb))
                self.arrows[k].set_visible(True)
                self.labels[k].set_text(f"{LEG_ORDER[k]} {force / 1e3:6.2f} kN")
            else:
                self.arrows[k].set_visible(False)
                self.labels[k].set_text(f"{LEG_ORDER[k]} 부상")
            self.labels[k].set_position((st[0], st[1] - 0.12))
            anchor = screen(case.anchors[i, k])[0]
            self.anchor_marks[k].set_data([anchor[0]], [anchor[1]])
        com = case.pos[i] + case.rot[i] @ np.array(case.params.superstructure.mass_properties.com_m)
        sc = screen(com)[0]
        self.com.set_data([sc[0]], [sc[1]])
        self.com_text.set_position((sc[0] + 0.35, sc[1]))
        self.com_text.set_text("무게중심\n(상부체)")


class Inset:
    """Schematic magnified vertical displacements (side: pitch, front: roll)."""

    def __init__(self, fig, box, case: CaseData, k: float, view: str, z_range):
        self.ax = axes_px(fig, *box)
        self.case, self.k, self.view = case, k, view
        self.h_axis = 0 if view == "side" else 1
        style_axes(self.ax)
        self.ax.tick_params(labelsize=6.5)
        self.ax.grid(False)
        pads = case.sphere_centres_body
        self.h = pads[:, self.h_axis]
        # equal scale: the horizontal span follows the box aspect, centred on the pads
        half = 0.5 * (z_range[1] - z_range[0]) * box[2] / box[3]
        mid = 0.5 * (self.h.min() + self.h.max())
        span = (mid - half, mid + half)
        self.ax.set_xlim(*span)
        self.ax.set_ylim(*z_range)
        self.ax.axhspan(z_range[0], 0.0, color=EARTH_COLOR, alpha=0.18, lw=0)
        self.ax.axhline(0.0, color=INK_PRIMARY, lw=0.9)
        self.bar_h = INSET_BAR_H_M  # schematic body bar height above the floor [display m]
        xs = np.array(span)
        self.ax.plot(xs, [self.bar_h] * 2, ls=(0, (3, 2)), color=LIN_COLOR, lw=0.9)
        (self.bar,) = self.ax.plot([], [], color=INK_PRIMARY, lw=2.4, solid_capstyle="butt")
        self.posts, self.pads = [], []
        # nearer legs drawn on top: FR, RR seen from -y (side); FL, FR seen from +x (front)
        order = [1, 3] if view == "side" else [0, 1]
        self.legs = [0, 1, 2, 3]
        self.front = order
        for leg in self.legs:
            colour = LEG_COLORS[LEG_ORDER[leg]]
            (post,) = self.ax.plot([], [], color=colour, lw=1.6, zorder=3 if leg in order else 2)
            pad = Rectangle((0, 0), 0.5, 0.12, fc=colour, ec="white", lw=0.5,
                            zorder=4 if leg in order else 3)
            self.ax.add_patch(pad)
            self.posts.append(post)
            self.pads.append(pad)
        (self.com,) = self.ax.plot([], [], "X", ms=7, color="#e2245c", mec="white", mew=0.6,
                                   zorder=5)
        name = "pitch 확대도 (측면 x–z)" if view == "side" else "roll 확대도 (정면 y–z)"
        self.ax.set_title(f"{name}  수직 ×{k:g}", fontsize=8, loc="left",
                          color=INK_PRIMARY, pad=2)
        self.text = self.ax.text(0.98, 0.97, "", transform=self.ax.transAxes, fontsize=7.5,
                                 va="top", ha="right", color=INK_PRIMARY,
                                 bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                                           alpha=0.85))

    def dz(self, i: int, points_body: np.ndarray) -> np.ndarray:
        """True vertical displacement [m] of body points from the zero pose."""
        case = self.case
        world = points_body @ case.rot[i].T + case.pos[i]
        return world[:, 2] - (points_body[:, 2] + case.zero_origin[2])

    def update(self, i: int):
        case, k = self.case, self.k
        xs = np.linspace(self.h.min() - 0.6, self.h.max() + 0.6, 30)
        line_points = np.zeros((len(xs), 3))
        line_points[:, self.h_axis] = xs
        self.bar.set_data(xs, self.bar_h + k * self.dz(i, line_points))
        for leg in self.legs:
            pen = case.pen_mm[i, leg] * 1e-3
            h = self.h[leg]
            bottom = -k * pen
            pad_h = 0.25
            self.pads[leg].set_xy((h - 0.25, bottom))
            self.pads[leg].set_height(pad_h)
            top = self.bar_h + k * self.dz(i, case.sphere_centres_body[leg:leg + 1])[0]
            self.posts[leg].set_data([h, h], [bottom + pad_h, top])
            lifted = not case.contact[i, leg]
            self.pads[leg].set_facecolor("white" if lifted else LEG_COLORS[LEG_ORDER[leg]])
            self.pads[leg].set_edgecolor(LEG_COLORS[LEG_ORDER[leg]] if lifted else "white")
        com_body = np.array(case.params.superstructure.mass_properties.com_m)
        com_h = com_body[self.h_axis]
        # CoM drawn on the bar at its horizontal position, displaced like the body
        self.com.set_data([com_h + 0.0], [self.bar_h + k * self.dz(i, com_body[None])[0]])
        angle = case.pitch_deg[i] if self.view == "side" else case.roll_deg[i]
        sym = "θ" if self.view == "side" else "φ"
        self.text.set_text(f"{sym} = {angle:+.5f}°  (그림 {angle * k:+.2f}°)")


# --- settle segment ------------------------------------------------------------------------


def settle_figure(case: CaseData, mesh_image, limits3d, k: float):
    fig = plt.figure(figsize=(FRAME_W / DPI, FRAME_H / DPI), dpi=DPI, facecolor=SURFACE)
    scene = Scene3D(fig, (8, 96, 560, 796), limits3d, mesh_image)
    cursor = Cursor()
    t = case.t
    # contact force per leg, 2 x 2
    x0, y0, w, h, gx, gy = 640, 122, 315, 146, 70, 46
    for k_leg, leg in enumerate(LEG_ORDER):
        ax = axes_px(fig, x0 + (k_leg % 2) * (w + gx), y0 + (k_leg // 2) * (h + gy), w, h)
        style_axes(ax, title=f"{leg} 패드 접촉력", ylabel="kN")
        f = case.F[:, k_leg] / 1e3
        lin, nl = case.lin["F_N"][k_leg] / 1e3, case.nl["F_N"][k_leg] / 1e3
        ax.axvspan(case.still_start_s, t[-1], color="#f1efe9", lw=0, zorder=0)
        ax.axhline(lin, color=LIN_COLOR, ls=(0, (4, 2)), lw=1.1)
        ax.axhline(nl, color=NL_COLOR, ls=(0, (1, 1.5)), lw=1.2)
        ax.plot(t, f, color=LEG_COLORS[leg], lw=1.3)
        lo, hi = min(lin, nl, f.min()), max(lin, nl, f.max())
        pad = max(0.04, 0.35 * (hi - lo))
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlim(0, t[-1])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.2f"))
        ax.text(0.99, 0.04, f"선형 {lin:.2f} · 비선형 {nl:.2f} kN", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=7.2, color=INK_SECONDARY)
        if k_leg >= 2:
            ax.set_xlabel("t [s]", fontsize=8, color=INK_SECONDARY, labelpad=1)
        cursor.add_axes(ax)
        cursor.add_dot(ax, t, f, LEG_COLORS[leg])
    # attitude
    ya = y0 + 2 * (h + gy) + 6
    for j, (name, series) in enumerate((("roll", case.roll_deg), ("pitch", case.pitch_deg))):
        ax = axes_px(fig, x0 + j * (w + gx), ya, w, 120)
        style_axes(ax, title=f"{name} [°]  (V3 기준 ±{case.v3_tol:g}°)", xlabel="t [s]")
        ref = case.v3_ref[j]
        ax.axhspan(ref - case.v3_tol, ref + case.v3_tol, color=BAND_COLOR, lw=0, zorder=0)
        ax.axhline(ref, color=LIN_COLOR, ls=(0, (4, 2)), lw=1.1)
        ax.axhline(case.nl["att_deg"][j], color=NL_COLOR, ls=(0, (1, 1.5)), lw=1.2)
        ax.plot(t, series, color=INK_PRIMARY, lw=1.3)
        ax.set_ylim(ref - 1.6 * case.v3_tol, ref + 1.6 * case.v3_tol)
        ax.set_xlim(0, t[-1])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.4f"))
        cursor.add_axes(ax)
        cursor.add_dot(ax, t, series, ACCENT)
    # penetration (full width) with the still-window means
    yp = ya + 120 + 52
    ax = axes_px(fig, x0, yp, 2 * w + gx, 150)
    style_axes(ax, title="패드 침투 [mm]  (점선 = 비선형 기준, 오른쪽 수치 = 정지 창 평균)",
               xlabel="t [s]")
    still = case.t >= case.still_start_s - 1e-9
    for k_leg, leg in enumerate(LEG_ORDER):
        ax.plot(t, case.pen_mm[:, k_leg], color=LEG_COLORS[leg], lw=1.3)
        ax.axhline(case.nl["pen_mm"][k_leg], color=NL_COLOR, ls=(0, (1, 1.5)), lw=0.9)
        cursor.add_dot(ax, t, case.pen_mm[:, k_leg], LEG_COLORS[leg])
        mean = case.pen_mm[still, k_leg].mean()
        y_label = (mean - 2.6) / 3.6 + (0.035 if k_leg % 2 == 0 else -0.035)
        ax.text(1.005, y_label, f"{leg} {mean:.3f}", transform=ax.transAxes, fontsize=7.2, color=LEG_COLORS[leg], va="center")
    ax.set_xlim(0, t[-1])
    ax.set_ylim(2.6, 6.2)
    cursor.add_axes(ax)
    # insets (pitch side, roll front) in the free top-left corner of the 3D panel
    inset_side = Inset(fig, INSET_SIDE_BOX, case, k, "side", INSET_Z_RANGE)
    inset_front = Inset(fig, INSET_FRONT_BOX, case, k, "front", INSET_Z_RANGE)
    # legend row
    handles = [Line2D([], [], color=LIN_COLOR, ls=(0, (4, 2)), lw=1.1,
                      label="선형 3자유도 기준 (result.json)"),
               Line2D([], [], color=NL_COLOR, ls=(0, (1, 1.5)), lw=1.2,
                      label="비선형 기준 (s1_pdelta_check.json)"),
               Rectangle((0, 0), 1, 1, color="#f1efe9", label="정지 판정 창 5 s"),
               Rectangle((0, 0), 1, 1, color=BAND_COLOR, label="V3 허용 띠"),
               Line2D([], [], color=ACCENT, lw=1.0, label="현재 시각")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(x0 / FRAME_W, 1 - 76 / FRAME_H),
               ncol=5, frameon=False, fontsize=7.6, labelcolor=INK_SECONDARY,
               handlelength=2.2, columnspacing=1.2)
    header = fig.text(8 / FRAME_W, 1 - 10 / FRAME_H, "", fontsize=13, fontweight="bold",
                      va="top", color=INK_PRIMARY)
    status = fig.text(8 / FRAME_W, 1 - 38 / FRAME_H, "", fontsize=10, va="top",
                      color=INK_PRIMARY)
    note = fig.text(8 / FRAME_W, 1 - 60 / FRAME_H, "", fontsize=8.5, va="top",
                    color=INK_SECONDARY)
    return {"fig": fig, "scene": scene, "cursor": cursor, "insets": (inset_side, inset_front),
            "header": header, "status": status, "note": note}


def figure_to_image(fig) -> Image.Image:
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(), "RGB")


def render_settle_segment(case: CaseData, parts_bundle, limits3d, k, n_frames, hold_start_ms,
                          hold_end_ms, frame_ms, segment_label):
    image = case_mesh_image(case, parts_bundle, limits3d)
    pieces = settle_figure(case, image, limits3d, k)
    t_end = case.t[-1]
    times = np.linspace(case.t[0], t_end, n_frames)
    frames, durations = [], []
    level = LEVEL_LABEL[case.level]
    pieces["header"].set_text(
        f"S1 정착 · 오거 {level} · 해석 정적해 초기화 · L1 (강체 위치 모터 + 지면 부싱) · "
        f"Δt 0.1 ms · 기록 10 ms / 정지 창 1 ms   {segment_label}")
    pieces["note"].set_text(
        "3D: CAD 메시, 실제 크기(변위는 mm 수준). 화살표 = 지면 반력(패드 접촉력), "
        f"길이 1 m = 100 kN. × = 부싱 고정점.  확대도: 수직 변위 ×{k:g}(가로 실제), "
        "점선 막대 = 영 자세(수평, 패드가 막 닿음)")
    for n, t_now in enumerate(times):
        i = case.index(t_now)
        pieces["cursor"].update(case.t[i], i)
        pieces["scene"].update(case, i)
        for inset in pieces["insets"]:
            inset.update(i)
        total = case.F[i].sum()
        pieces["status"].set_text(
            f"t = {case.t[i]:6.2f} s / {t_end:.0f} s    "
            f"roll {case.roll_deg[i]:+.5f}°   pitch {case.pitch_deg[i]:+.5f}°   "
            f"ΣF = {total / 1e3:.3f} kN (총중량 {case.weight_N / 1e3:.3f} kN, "
            f"차 {total - case.weight_N:+.2f} N)")
        frames.append(figure_to_image(pieces["fig"]))
        durations.append(hold_start_ms if n == 0 else hold_end_ms if n == n_frames - 1
                         else frame_ms)
    plt.close(pieces["fig"])
    return frames, durations


MESH_IMAGES: dict = {}


def case_mesh_image(case: CaseData, bundle, limits3d, box=(560, 796)):
    key = (case.level, round(float(limits3d[0][0]), 6), box)
    if key not in MESH_IMAGES:
        parts, render, topologies = bundle
        items = body_items(parts, render, topologies, case.params, case.s_motor)
        below, above = world_items(items, case.pos[-1], case.rot[-1], case.floor_z)
        t0 = time.perf_counter()
        MESH_IMAGES[key] = render_mesh_image(below, above, case.floor_z, limits3d, box)
        print(f"  mesh image {case.level}: {time.perf_counter() - t0:.1f} s", flush=True)
    return MESH_IMAGES[key]


def scene_limits(cases, bundle, box=(560, 796)):
    """Common oblique limits for all levels (machine, floor patch, arrow room)."""
    parts, render, topologies = bundle
    pts = []
    for case in cases:
        items = body_items(parts, render, topologies, case.params, case.s_motor)
        world = np.vstack([p for p, *_ in items]) + case.zero_origin
        pts.append(screen(world[:: max(1, len(world) // 200000)]))
        pts.append(screen(ground_polygon(case.floor_z)))
        bottoms = case.pad_bottom_world(-1)
        pts.append(screen(bottoms - np.array([0, 0, 2.2])))
    return fit_limits(np.vstack(pts), box, margin_m=(0.2, 0.2))


# --- comparison scene ----------------------------------------------------------------------


def comparison_frame(cases: list[CaseData], bundle) -> Image.Image:
    """Final settled states of the three auger levels: side views + leg load bars."""
    parts, render, topologies = bundle
    fig = plt.figure(figsize=(FRAME_W / DPI, FRAME_H / DPI), dpi=DPI, facecolor=SURFACE)
    fig.text(8 / FRAME_W, 1 - 10 / FRAME_H,
             "S1 오거 3단계 비교 · 최종 정착 상태(정지 판정 창 5 s 평균) · L1 · 강체 평지",
             fontsize=13, fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(8 / FRAME_W, 1 - 38 / FRAME_H,
             "측면도(x–z, -y에서 봄): CAD 메시, 오거 구동부+공구가 마스트를 따라 이동. "
             "× = 상부체 무게중심(경우 C). 선형 기준값은 세 단계가 같고, Chrono·비선형 해는 "
             "무게중심 높이 h에 비례한 P-δ 차를 보인다.",
             fontsize=9, va="top", color=INK_SECONDARY)
    box_w, box_h, x_start, y_top = 250, 560, 10, 70
    all_points = []
    level_items = []
    for case in cases:
        items = body_items(parts, render, topologies, case.params, case.s_motor)
        level_items.append(items)
        world = np.vstack([p for p, *_ in items]) + case.zero_origin
        all_points.append(screen(world[:: max(1, len(world) // 200000)], "side"))
    lim = fit_limits(np.vstack(all_points + [np.array([[0, cases[0].floor_z - 0.3]])]),
                     (box_w, box_h), margin_m=(0.35, 0.25))
    summary = []
    for j, (case, items) in enumerate(zip(cases, level_items, strict=True)):
        below, above = world_items(items, case.pos[-1], case.rot[-1], case.floor_z)
        t0 = time.perf_counter()
        img = render_mesh_image(below, above, case.floor_z, lim, (box_w, box_h), view="side")
        print(f"  side image {case.level}: {time.perf_counter() - t0:.1f} s", flush=True)
        ax = axes_px(fig, x_start + j * (box_w + 8), y_top, box_w, box_h)
        ax.set_xlim(*lim[0])
        ax.set_ylim(*lim[1])
        ax.set_axis_off()
        ax.imshow(np.asarray(img), extent=(*lim[0], *lim[1]), origin="upper", aspect="auto",
                  interpolation="nearest")
        com = case.pos[-1] + case.rot[-1] @ np.array(case.params.superstructure.mass_properties
                                                     .com_m)
        ax.plot(com[0], com[2], "X", ms=10, color="#e2245c", mec="white", mew=0.8, zorder=5)
        m = case.t >= case.still_start_s - 1e-9
        com_z_body = case.params.superstructure.mass_properties.com_m[2]
        ax.text(0.03, 0.99, f"{LEVEL_LABEL[case.level]}\n무게중심 z(기체) = {com_z_body:.3f} m\n"
                f"h(볼 중심 위) = {case.nl['h_m']:.3f} m\n"
                f"roll {case.roll_deg[m].mean():+.5f}°\npitch {case.pitch_deg[m].mean():+.5f}°",
                transform=ax.transAxes, fontsize=8.5, va="top", color=INK_PRIMARY)
        summary.append({
            "level": case.level, "com_world_m": com.round(4).tolist(), "h_m": case.nl["h_m"],
            "contact_mean_N": case.F[m].mean(axis=0).round(2).tolist(),
            "roll_mean_deg": float(case.roll_deg[m].mean()),
            "pitch_mean_deg": float(case.pitch_deg[m].mean()),
            "penetration_mean_mm": case.pen_mm[m].mean(axis=0).round(5).tolist()})
    # value table under the side views
    cells, labels = [], []
    for item in summary:
        f = np.array(item["contact_mean_N"])
        cells.append([f"{v / 1e3:.3f}" for v in f] + [f"{f.sum() - cases[0].weight_N:+.2f}"])
        labels.append(f"{LEVEL_LABEL[item['level']]} 접촉력 [kN]")
    cells.append([f"{v / 1e3:.3f}" for v in cases[0].lin["F_N"]] + ["—"])
    labels.append("선형 기준 [kN]")
    for item in summary:
        cells.append([f"{v:.4f}" for v in item["penetration_mean_mm"]] + [""])
        labels.append(f"{LEVEL_LABEL[item['level']]} 침투 [mm]")
    cells.append([f"{v:.4f}" for v in cases[0].lin["pen_mm"]] + [""])
    labels.append("선형 기준 침투 [mm]")
    table_ax = axes_px(fig, 130, 650, 640, 210)
    table_ax.set_axis_off()
    table = table_ax.table(cellText=cells, rowLabels=labels,
                           colLabels=[*LEG_ORDER, "ΣF - W [N]"], loc="upper center",
                           cellLoc="right", rowLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.25)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#dcdbd6")
        cell.set_linewidth(0.5)
        if r == 0 and 0 <= c < 4:
            cell.get_text().set_color(LEG_COLORS[LEG_ORDER[c]])
            cell.get_text().set_fontweight("bold")
    level_colours = {"top": "#24324f", "middle": "#5f7fb3", "bottom": "#a9bfe0"}
    # absolute load bars
    ax = axes_px(fig, 830, 90, 545, 300)
    style_axes(ax, title="다리별 패드 접촉력 [kN] (정지 창 평균)", ylabel="kN")
    width = 0.24
    x = np.arange(4)
    for j, case in enumerate(cases):
        m = case.t >= case.still_start_s - 1e-9
        values = case.F[m].mean(axis=0) / 1e3
        bars = ax.bar(x + (j - 1) * width, values, width, color=level_colours[case.level],
                      label=f"{LEVEL_LABEL[case.level]}")
        if j == 1:
            for b, v in zip(bars, values, strict=True):
                ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.2f}", ha="center",
                        fontsize=8, color=INK_PRIMARY)
    lin = cases[0].lin["F_N"] / 1e3
    for k_leg in range(4):
        ax.plot([k_leg - 1.6 * width, k_leg + 1.6 * width], [lin[k_leg]] * 2, color=ACCENT,
                lw=1.4, ls=(0, (4, 2)))
    ax.set_xticks(x, [f"{leg}" for leg in LEG_ORDER])
    for tick, leg in zip(ax.get_xticklabels(), LEG_ORDER, strict=True):
        tick.set_color(LEG_COLORS[leg])
        tick.set_fontweight("bold")
    ax.set_ylim(0, 140)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([], [], color=ACCENT, lw=1.4, ls=(0, (4, 2))))
    labels.append("선형 기준(세 단계 같음)")
    ax.legend(handles, labels, fontsize=8, frameon=False, ncol=4, loc="upper right")
    # deviation from the linear reference
    ax = axes_px(fig, 830, 450, 545, 300)
    style_axes(ax, title="접촉력 - 선형 기준 [N]  (막대 = Chrono, ◆ = 비선형 기준해)",
               ylabel="N")
    for j, case in enumerate(cases):
        m = case.t >= case.still_start_s - 1e-9
        dev = case.F[m].mean(axis=0) - case.lin["F_N"]
        nl_dev = case.nl["F_N"] - case.lin["F_N"]
        xs = x + (j - 1) * width
        ax.bar(xs, dev, width, color=level_colours[case.level],
               label=f"{LEVEL_LABEL[case.level]} (h {case.nl['h_m']:.2f} m)")
        ax.plot(xs, nl_dev, "D", ms=4.5, color=ACCENT, mec="white", mew=0.5, zorder=4)
    ax.axhline(0, color=INK_PRIMARY, lw=0.8)
    ax.set_xticks(x, [f"{leg}" for leg in LEG_ORDER])
    for tick, leg in zip(ax.get_xticklabels(), LEG_ORDER, strict=True):
        tick.set_color(LEG_COLORS[leg])
        tick.set_fontweight("bold")
    ax.set_ylim(-85, 85)
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper right")
    ax.text(0.01, 0.03, f"V1 허용 ±{cases[0].v1_tol:.0f} N (선형 기준 대비) — 모두 그 안",
            transform=ax.transAxes, fontsize=8, color=INK_SECONDARY)
    fig.text(830 / FRAME_W, 1 - 790 / FRAME_H,
             "출처: 07_results/S1/<단계>/record.npz(정지 창 평균), result.json "
             "linear_static_cross_check,\n06_analysis/00_dynamics/s1_pdelta_check.json. "
             "W = 382.29 kN(상부체 + 다리 이동부).",
             fontsize=8, va="top", color=INK_SECONDARY)
    image = figure_to_image(fig)
    plt.close(fig)
    return image, summary


# --- cross segment -------------------------------------------------------------------------


def event_clusters(case: CaseData, merge_s=0.002):
    clusters = []
    for t, leg, kind in sorted(case.events):
        if clusters and t - clusters[-1][-1][0] < merge_s and clusters[-1][-1][2] == kind:
            clusters[-1].append((t, leg, kind))
        else:
            clusters.append([(t, leg, kind)])
    out = []
    for cluster in clusters:
        legs = "·".join(LEG_ORDER[leg] for _, leg, _ in cluster)
        kind = cluster[0][2]
        what = "패드 부상(부싱 제거)" if kind == 2 else "재접지(부싱 새 고정점)"
        out.append((cluster[0][0], cluster[-1][0], f"{legs} {what}"))
    return out


def _short_number(value, _pos=None) -> str:
    """Tick label for N values: 100, 1k, 10k, 100k."""
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    a = abs(value)
    return f"{sign}{a / 1e3:g}k" if a >= 1e3 else f"{sign}{a:g}"


def cross_figure(case: CaseData, mesh_image, limits3d, k: float, events):
    fig = plt.figure(figsize=(FRAME_W / DPI, FRAME_H / DPI), dpi=DPI, facecolor=SURFACE)
    scene = Scene3D(fig, (8, 96, 560, 796), limits3d, mesh_image)
    cursor = Cursor()
    t = case.t
    t_min, t_max = t[0], t[-1]
    x0, w, gx = 650, 340, 64
    rows = (124, 310, 496, 682)
    h = 140

    def time_axes(ax):
        ax.set_xscale("log")
        ax.set_xlim(t_min, t_max)
        ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.01, 0.1, 1, 10]))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.axvspan(case.still_start_s, t_max, color="#f1efe9", lw=0, zorder=0)
        for t_e, _, _ in events:
            ax.axvline(t_e, color="#9b59b6", lw=0.6, alpha=0.6, zorder=1)
        cursor.add_axes(ax)

    ax = axes_px(fig, x0, rows[0], w, h)
    style_axes(ax, title="패드 접촉력 [kN]", ylabel="kN")
    time_axes(ax)
    for k_leg, leg in enumerate(LEG_ORDER):
        f = case.F[:, k_leg] / 1e3
        ax.plot(t, f, color=LEG_COLORS[leg], lw=1.1)
        ax.axhline(case.lin["F_N"][k_leg] / 1e3, color=LIN_COLOR, ls=(0, (4, 2)), lw=0.8)
        cursor.add_dot(ax, t, f, LEG_COLORS[leg])
    ax.set_ylim(-5, 215)
    ax = axes_px(fig, x0 + w + gx, rows[0], w, h)
    style_axes(ax, title=f"접촉력 - 선형 기준 [N] (symlog, V1 ±{case.v1_tol:.0f} N)",
               ylabel="N")
    time_axes(ax)
    ax.set_yscale("symlog", linthresh=100)
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(
        [-1e5, -1e4, -1e3, -100, 0, 100, 1e3, 1e4, 1e5]))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_short_number))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.axhspan(-case.v1_tol, case.v1_tol, color=BAND_COLOR, lw=0, zorder=0)
    for k_leg, leg in enumerate(LEG_ORDER):
        dev = case.F[:, k_leg] - case.lin["F_N"][k_leg]
        ax.plot(t, dev, color=LEG_COLORS[leg], lw=1.0)
        ax.axhline(case.nl["F_N"][k_leg] - case.lin["F_N"][k_leg], color=LEG_COLORS[leg],
                   ls=(0, (1, 1.5)), lw=0.9)
        cursor.add_dot(ax, t, dev, LEG_COLORS[leg])
    ax.set_ylim(-2e5, 2e5)
    for j, (name, series) in enumerate((("roll", case.roll_deg), ("pitch", case.pitch_deg))):
        ax = axes_px(fig, x0 + j * (w + gx), rows[1], w, h)
        style_axes(ax, title=f"{name} [°]  (V3 기준 ±{case.v3_tol:g}°)")
        time_axes(ax)
        ref = case.v3_ref[j]
        ax.axhspan(ref - case.v3_tol, ref + case.v3_tol, color=BAND_COLOR, lw=0, zorder=0)
        ax.axhline(case.nl["att_deg"][j], color=NL_COLOR, ls=(0, (1, 1.5)), lw=1.0)
        ax.plot(t, series, color=INK_PRIMARY, lw=1.1)
        cursor.add_dot(ax, t, series, ACCENT)
        lo, hi = min(series.min(), ref - case.v3_tol), max(series.max(), ref + case.v3_tol)
        ax.set_ylim(lo - 0.08 * (hi - lo), hi + 0.08 * (hi - lo))
    ax = axes_px(fig, x0, rows[2], w, h)
    style_axes(ax, title="패드 침투 [mm]  (음수 = 틈, 점선 = 비선형 기준)")
    time_axes(ax)
    for k_leg, leg in enumerate(LEG_ORDER):
        ax.plot(t, case.pen_mm[:, k_leg], color=LEG_COLORS[leg], lw=1.1)
        ax.axhline(case.nl["pen_mm"][k_leg], color=LEG_COLORS[leg], ls=(0, (1, 1.5)), lw=0.8)
        cursor.add_dot(ax, t, case.pen_mm[:, k_leg], LEG_COLORS[leg])
    ax.axhline(0, color=INK_PRIMARY, lw=0.7)
    ax = axes_px(fig, x0 + w + gx, rows[2], w, h)
    style_axes(ax, title=f"부싱 접선력 x [kN]  (점선 = 합, ±{FT_LINTHRESH_KN:g} kN 안 선형 눈금)")
    time_axes(ax)
    for k_leg, leg in enumerate(LEG_ORDER):
        ax.plot(t, case.Ft_x[:, k_leg] / 1e3, color=LEG_COLORS[leg], lw=1.1)
        cursor.add_dot(ax, t, case.Ft_x[:, k_leg] / 1e3, LEG_COLORS[leg])
    total = case.Ft_x.sum(axis=1) / 1e3
    ax.plot(t, total, color=INK_PRIMARY, lw=0.9, ls=(0, (3, 1.5)))
    ax.axhline(0, color=INK_PRIMARY, lw=0.6)
    ax.set_yscale("symlog", linthresh=FT_LINTHRESH_KN)
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([-100, -10, -5, 0, 5, 10, 100]))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylim(-150, 150)
    # bottom row: insets + event list
    yi = rows[3] + 6
    inset_side = Inset(fig, INSET_SIDE_BOX, case, k, "side", INSET_Z_RANGE)
    inset_front = Inset(fig, INSET_FRONT_BOX, case, k, "front", INSET_Z_RANGE)
    event_text = fig.text(x0 / FRAME_W, 1 - (yi + 4) / FRAME_H, "", fontsize=8.8,
                          va="top", color=INK_PRIMARY, family="Malgun Gothic")
    handles = [Line2D([], [], color=LIN_COLOR, ls=(0, (4, 2)), lw=1.0, label="선형 기준"),
               Line2D([], [], color=NL_COLOR, ls=(0, (1, 1.5)), lw=1.0, label="비선형 기준"),
               Line2D([], [], color="#9b59b6", lw=0.8, label="부싱 이벤트(부상·재접지)"),
               Rectangle((0, 0), 1, 1, color="#f1efe9", label="정지 판정 창"),
               Rectangle((0, 0), 1, 1, color=BAND_COLOR, label="허용 띠"),
               Line2D([], [], color=ACCENT, lw=1.0, label="현재 시각")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(x0 / FRAME_W, 1 - 76 / FRAME_H),
               ncol=6, frameon=False, fontsize=7.6, labelcolor=INK_SECONDARY,
               handlelength=2.0, columnspacing=1.0)
    header = fig.text(8 / FRAME_W, 1 - 10 / FRAME_H, "", fontsize=13, fontweight="bold",
                      va="top", color=INK_PRIMARY)
    status = fig.text(8 / FRAME_W, 1 - 38 / FRAME_H, "", fontsize=10, va="top",
                      color=INK_PRIMARY)
    banner = fig.text(8 / FRAME_W, 1 - 60 / FRAME_H, "", fontsize=10.5, va="top",
                      color=ACCENT, fontweight="bold")
    return {"fig": fig, "scene": scene, "cursor": cursor, "insets": (inset_side, inset_front),
            "header": header, "status": status, "banner": banner, "events": event_text}


def cross_plan(case: CaseData, events, fps_fast=10.0):
    """(sample index, duration ms, banner) with slow early time and log-spaced later frames."""
    t = case.t
    frame_ms = int(round(1000 / fps_fast / 10)) * 10
    early_end = CROSS_SLOW_END_S
    idx = list(np.flatnonzero(t <= early_end + 1e-9))  # every 10 ms sample
    later = np.geomspace(early_end, case.still_start_s, 40)[1:]
    idx += [case.index(v) for v in later]
    idx += [case.index(v) for v in np.linspace(case.still_start_s + 0.5, t[-1], 6)]
    idx = sorted(set(idx))
    plan = []
    event_frames = {}
    for t_first, t_last, text in events:
        i = int(np.searchsorted(t, t_last + 1e-9))  # first sample after the event
        event_frames.setdefault(i, []).append(f"▶ {text} (t = {t_first:.4f} s)")
    for n, i in enumerate(idx):
        banner = " / ".join(event_frames.get(i, [])) or None
        if n == 0:
            duration = 1500
        elif n == len(idx) - 1:
            duration = 2500
        elif banner:
            duration = 1100
        elif t[i] <= early_end:
            duration = frame_ms
        else:
            duration = frame_ms
        plan.append((i, duration, banner))
    return plan


def render_cross(case: CaseData, bundle, limits3d, k):
    events = event_clusters(case)
    image = case_mesh_image(case, bundle, limits3d)
    pieces = cross_figure(case, image, limits3d, k, events)
    plan = cross_plan(case, events)
    slip = case.result["ground_bushing"]["slip_total_m"]
    yields = case.result["ground_bushing"]["yield_steps"]
    pieces["header"].set_text(
        "S1 교차 사례 · 오거 상단 · 무초기화(영 자세: 수평, 패드가 막 닿음, 정지)에서 놓음 · "
        f"정착 {case.result['settle_s']:.0f} s + 정지 창 {case.result['still_s']:.0f} s · L1")
    lines = ["부싱 이벤트(Record bushing_events):"]
    for t_first, _, text in events:
        lines.append(f"  {t_first:.4f} s  {text}")
    lines.append("항복 스텝 FL/FR/RL/RR: " + " / ".join(str(v) for v in yields))
    lines.append("고정점 누적 미끄럼 x [mm]: "
                 + " / ".join(f"{s[0] * 1e3:+.2f}" for s in slip))
    end_ft = case.Ft_x[-1] / 1e3
    lines.append("최종 접선 예하중 x [kN]: " + " / ".join(f"{v:+.2f}" for v in end_ft))
    lines.append(f"  합 {case.Ft_x[-1].sum():+.1f} N → 자세·수직 하중 영향 없음")
    lines.append(f"3D: CAD 메시 실제 크기(변위 mm 수준), 화살표 = 패드 접촉력(1 m = 100 kN), "
                 "× = 부싱 고정점")
    lines.append(f"확대도: 영 자세 대비 수직 변위 ×{k:g}(가로 실제), 흰 패드 = 부상")
    pieces["events"].set_text("\n".join(lines))
    frames, durations = [], []
    for i, duration, banner in plan:
        pieces["cursor"].update(case.t[i], i)
        pieces["scene"].update(case, i)
        for inset in pieces["insets"]:
            inset.update(i)
        speed = "초반 슬로모션(10 ms/프레임, 실제의 0.1배)" if case.t[i] <= CROSS_SLOW_END_S + 1e-9 else \
            "로그 시간 간격으로 가속"
        total = case.F[i].sum()
        pieces["status"].set_text(
            f"t = {case.t[i]:7.3f} s   {speed}   roll {case.roll_deg[i]:+.5f}°   "
            f"pitch {case.pitch_deg[i]:+.5f}°   ΣF = {total / 1e3:7.2f} kN "
            f"(총중량 {case.weight_N / 1e3:.2f} kN)")
        pieces["banner"].set_text(banner or "")
        frames.append(figure_to_image(pieces["fig"]))
        durations.append(duration)
    plt.close(pieces["fig"])
    return frames, durations, plan, events


# --- GIF writing ---------------------------------------------------------------------------


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


def write_gif(frames, durations, path: Path, colors=256):
    sample_ids = sorted(set(np.linspace(0, len(frames) - 1, 4).astype(int).tolist()))
    w, h = frames[0].size
    sample = Image.new("RGB", (w * len(sample_ids), h + 40))
    for k, i in enumerate(sample_ids):
        sample.paste(frames[i], (k * w, 0))
    swatches = [LEG_COLORS[leg] for leg in LEG_ORDER] + [ACCENT, INK_PRIMARY, "white",
                                                          "#e2245c", "#9b59b6", BAND_COLOR]
    sw = sample.width // len(swatches)
    for k, colour in enumerate(swatches):
        sample.paste(Image.new("RGB", (sw, 40), colour), (k * sw, h))
    # One global palette (no flicker) with the last index reserved as "unchanged" (transparent):
    # pixels equal to the previous frame are written transparent, so the LZW stream of a frame
    # only carries what moved (cursor, arrows, numbers). Disposal 1 keeps the previous frame.
    palette = sample.quantize(colors=min(colors, 255), method=Image.Quantize.MEDIANCUT)
    colours = palette.getpalette()[: 3 * 255]
    colours += [0] * (3 * 255 - len(colours)) + [255, 0, 255]
    clear = 255
    lut = np.array(colours, dtype=np.uint8).reshape(-1, 3)
    check_ids = set(np.linspace(0, len(frames) - 1, 6).astype(int).tolist())
    expected = {}
    indexed, previous = [], None
    for n, frame in enumerate(frames):
        codes = np.asarray(frame.quantize(palette=palette, dither=Image.Dither.NONE)).copy()
        if n in check_ids:
            expected[n] = lut[codes]
        coded = codes.copy()
        if previous is not None:
            coded[codes == previous] = clear
        previous = codes
        image = Image.fromarray(coded, "P")
        image.putpalette(colours)
        image.info["transparency"] = clear
        indexed.append(image)
    durations = [max(20, int(round(d / 10.0)) * 10) for d in durations]
    save_atomic(path, lambda target: indexed[0].save(
        target, save_all=True, append_images=indexed[1:], duration=durations, loop=0,
        optimize=False, disposal=1, transparency=clear))
    # Round trip: decode with Pillow (applies transparency + disposal) and compare.
    worst = 0
    with Image.open(path) as gif:
        for n in range(len(frames)):
            gif.seek(n)
            if n in expected:
                decoded = np.asarray(gif.convert("RGB"), dtype=np.int16)
                worst = max(worst, int(np.abs(decoded - expected[n]).max()))
    return {"path": str(path.relative_to(ROOT).as_posix()), "frames": len(frames),
            "roundtrip_max_abs_diff_rgb (decoded vs quantized, 6 frames)": worst,
            "size_bytes": path.stat().st_size, "loop_s": round(sum(durations) / 1000, 2),
            "resolution_px": [w, h]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=("settle", "cross", "all"), default="all")
    parser.add_argument("--exaggeration", type=float, default=500.0,
                        help="vertical displacement factor of the settle insets")
    parser.add_argument("--cross-exaggeration", type=float, default=300.0,
                        help="vertical displacement factor of the cross-case insets")
    parser.add_argument("--settle-frames", type=int, default=30, help="frames per level")
    parser.add_argument("--mesh-cache", type=Path, default=None,
                        help="optional pickle of the render meshes (speeds up reruns)")
    parser.add_argument("--frames-dir", type=Path, default=None,
                        help="optional folder for PNG copies of selected frames")
    args = parser.parse_args()
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdelta = json.loads(PDELTA_JSON.read_text(encoding="utf-8"))
    bundle = load_meshes(args.mesh_cache)
    print(f"meshes loaded {time.perf_counter() - started:.1f} s", flush=True)
    settle_cases = [load_case(name, pdelta) for name in SETTLE_CASES]
    cross_case = load_case(CROSS_CASE, pdelta)
    limits3d = scene_limits(settle_cases, bundle)
    summary = {"meta": {
        "script": "04_scripts/02_chrono/render_S1_gifs.py",
        "inputs": [f"07_results/S1/{c}" for c in (*SETTLE_CASES, CROSS_CASE)]
                  + ["06_analysis/00_dynamics/s1_pdelta_check.json"],
        "view_oblique_toward_viewer_body": _TOWARD.round(4).tolist(),
        "arrow_m_per_kN": ARROW_M_PER_N * 1e3,
        "exaggeration_settle": args.exaggeration,
        "exaggeration_cross": args.cross_exaggeration,
        "derivation": "penetration_i = r_i - (o_z + (R c_i)_z - z_floor); roll, pitch = "
                      "roll_pitch_from_quat; pitch + = nose down"},
        "checks": {c.name: c.checks for c in (*settle_cases, cross_case)}}
    if args.only in ("settle", "all"):
        frames, durations = [], []
        for n, case in enumerate(settle_cases):
            f, d = render_settle_segment(
                case, bundle, limits3d, args.exaggeration, args.settle_frames,
                hold_start_ms=1000, hold_end_ms=1200, frame_ms=90,
                segment_label=f"[{n + 1}/4]")
            frames += f
            durations += d
            if args.frames_dir:
                f[-1].save(args.frames_dir / f"settle_{case.level}_end.png")
        compare, levels = comparison_frame(settle_cases, bundle)
        save_atomic(PNG_LEVELS, compare.save)
        frames.append(compare)
        durations.append(5000)
        summary["settle_gif"] = write_gif(frames, durations, GIF_SETTLE)
        summary["auger_levels"] = levels
        summary["auger_levels_png"] = PNG_LEVELS.relative_to(ROOT).as_posix()
        print(json.dumps(summary["settle_gif"]), flush=True)
    if args.only in ("cross", "all"):
        frames, durations, plan, events = render_cross(cross_case, bundle, limits3d,
                                                       args.cross_exaggeration)
        rep = next(n for n, (_, _, b) in enumerate(plan) if b and "부상" in b)
        save_atomic(PNG_CROSS, frames[rep].save)
        if args.frames_dir:
            for n in (0, rep, len(frames) // 2, len(frames) - 1):
                frames[n].save(args.frames_dir / f"cross_{n:03d}.png")
        summary["cross_gif"] = write_gif(frames, durations, GIF_CROSS)
        summary["cross_events"] = [{"t_first_s": a, "t_last_s": b, "text": c}
                                   for a, b, c in events]
        summary["cross_frame_png"] = {"path": PNG_CROSS.relative_to(ROOT).as_posix(),
                                      "t_s": float(cross_case.t[plan[rep][0]])}
        print(json.dumps(summary["cross_gif"]), flush=True)
    summary["total_s"] = round(time.perf_counter() - started, 1)
    if args.only == "all":
        SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k in ("settle_gif", "cross_gif",
                                                                  "checks", "total_s")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
