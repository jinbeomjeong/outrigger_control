"""Animated GIFs and PNGs of the S2a and S2b runs (L1; stored results only, no simulation).

Reads (nothing is simulated; the inputs are not modified):
    07_results/S2a/<case>/{record.npz, meta.json, result.json}
        v7_roll, v7_pitch, v7_yaw (judging runs at the YAML dt),
        v7_yaw_dt5e-05, v7_yaw_dt1e-04, v7_yaw_dt2e-04 (dt study: the three suffixed folders only;
        drawn only if v7_yaw_dt_study has three distinct dt that match the folder names, else
        the reason goes to S2_gifs.json dt_study.skip_reason),
        v12_pitch2, v12_roll2, v12_rollm2_pitch1.5
    07_results/S2b/<case>/{record.npz, meta.json, result.json}
        air_short, v11, crawler_{top,middle,bottom}, event_{fast,slow}_FL_dt{1e-04,1e-05}
    06_analysis/01_chrono/12_S2/verify_S2a_L1.json, verify_S2b_L1.json
                                                     automatic pre-check summaries
    06_analysis/00_dynamics/s2b_crawler_check.json                  independent crawler checks
    06_analysis/00_dynamics/reference.json   slope_V12 / <case> /
                             L1_plan_A_expected_chrono_minus_reference_rev13 (independent V12
                             statics of the current YAML: P-delta prediction, rev-12 sphere lever
                             part, rev-12 contact-point model values) and chrono_test_references
                             (V7 rev-5 / rev-13 frequencies). The V12 / V13 caption numbers are
                             computed from these and verify_S2a_L1.json (v12, table,
                             v12_plan_a_diagnosis); s2a_slope_pdelta_check.json (2026-10-20 YAML)
                             is no longer read.
    --before-dir (default 06_analysis/01_chrono/12_S2/history/before_planA/)
                             result.json backups of the rev-12 S2a run (contact-point bushing,
                             before plan A): S2a_v12_<case>.json. Used only if the backup was run
                             with the current YAML (params sha when the backup records one, else
                             total weight W = sum of the reference vertical reactions, rel. 1e-5).
                             Otherwise the rev-12 values are the independent contact-point model
                             values of reference.json (.../rev12_contact_point_bushing (S2a run
                             before plan A) / chrono_model_minus_reference_vertical_N).
    02_params/rexome33.yaml, CAD drawing meshes (as render_S1_gifs.py)

Writes (06_analysis/01_chrono/12_S2/):
    S2a_v7_free_vibration.gif   V7 free vibration (roll, pitch, yaw excitation), 3D at
                                exaggerated displacement + modal coordinate and envelopes
    S2a_dt_study.png            zeta3 against dt (3 runs), implicit-damping vs c_t-scale
    S2a_v12_slope.gif           V12 sloped floor: gravity ramp, hold release, settling
    S2a_v12_summary.png         V12 vertical Chrono - reference per leg, before / after plan A
    S2b_v11_stroke.gif          V11 legs in the air, full stroke out and back, command ramp
    S2b_ramp_effect.png         inertial reaction with / without the 0.1 s command ramp
    S2b_crawler_settle.gif      machine on the 24 crawler spheres, 3 auger levels, P-delta
    S2b_contact_events.gif      FL down / touch / lift / re-touch, R15 bushing events, 2 dt
    S2a_summary.png, S2b_summary.png        one-page dashboards (verdict table + key plots)
    S2a_v12_slope_frame.png, S2b_contact_events_frame.png   representative GIF frames
    S2_gifs.json                frame plans, sizes, value checks, sources

Drawing conventions (body / world frame: x forward, y left, z up; SI; roll / pitch ZYX, pitch
+ = nose down; leg order FL, FR, RL, RR):
    3D: oblique orthographic view of the CAD drawing meshes (render_S1_gifs: shaded, black
        outlines; z-buffer by default, render_layout_views.RENDERER). Since 2026-11-09 the
        undecimated V5 mesh (render_mesh_v5.npz, 6.38 M faces) is drawn in every scene
        (--cluster-mm 0). Until then the old 1.22 M-face mesh was decimated by vertex
        clustering (12 mm; 0.33 M faces), which tore thin plates; --cluster-mm > 0 restores it.
        Body displacements in S2 are millimetres (true scale shows nothing), so V7 draws the
        pose with displacement and rotation multiplied by a stated factor; V12 / crawler /
        event scenes are drawn at true scale with magnified insets.
    Forces: ground reaction arrows at the pad contact point (sphere centre - r n), 1 m per
        100 kN (normal); tangential (bushing) force arrows 1 m per 5 kN (x20 against normal).
    V7 modal coordinate: eta = Phi^T M q from result.json series (eta_judged, sqrt(kg) m); the
        envelope is refitted here with outrigger_sim.verify.metrics.fit_damped_sine (same fit
        as the judgement; deviation from result.json recorded in S2_gifs.json).
    Crawler sphere forces: k_n max(delta, 0) of the recorded pose (k_n = result.json
        analytic_exact.kn_per_sphere_float32_N_m, equal to s2b_crawler_check.json
        meta.kn_per_sphere_float32_N_m; sphere radius, centres and end-shoe gaps from YAML via
        scenarios.crawler_settle.crawler_layout); the still-window mean (window t >= settle_s
        of meta.json run.scenario.settings, length still_s) is checked against result.json
        sphere_force_chrono_mean_N. Active spheres per kind = result.json
        sphere_force_chrono_mean_N > 0 by sphere_labels (total = window.active_min/max). The
        weight W of the ΣF - W panel is the run's result.json analytic_exact.weight_N (YAML
        composite mass x g), checked against s2b_crawler_check.json <level>.W_N (rel. 1e-9).
        Crawler panel axis ranges come from the data and reference lines. Missing keys stop.
    V12 frame plan: settling frames are log-spaced up to the verify mean window start and end
        at the window end (clipped to the record end), so no frame lies past the run.

CPU: the process (and the V7 workers) is pinned to the E-cores
(outrigger_sim.hostcpu.place_process("ecore")) at below-normal priority (other agents run on
the P-cores); --cpu pcore pins to the P-cores instead, --cpu os disables placement.

Usage (Chrono-dev python):
    python -I -u 04_scripts/02_chrono/render_S2_gifs.py [--only NAME ...] [--workers 4]
        [--mesh-cache DIR] [--before-dir DIR] [--frames-dir DIR]
    NAME: v7, dt, v12, v12png, v11, ramp, crawler, events, summary (default: all)
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
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
from scipy.signal import find_peaks
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "04_scripts" / "00_cad"))
sys.path.insert(0, str(ROOT / "03_src"))

import render_S1_gifs as s1  # noqa: E402  (registers VIEWS["oblique"], Malgun Gothic)
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
from render_auger_descent import RENDER_NPZ, load_render_meshes  # noqa: E402
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
from run_S2a import dt_case_name  # noqa: E402  (dt-study folder naming rule)

from outrigger_sim.chrono.ground_bushing import (  # noqa: E402  (R15 N_th, t_lift)
    LIFT_TIME_S,
    TOUCH_THRESHOLD_N,
)
from outrigger_sim.frames import quat_to_matrix, roll_pitch_from_quat  # noqa: E402
from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_record  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import crawler_layout  # noqa: E402
from outrigger_sim.scenarios.stroke import (  # noqa: E402
    expected_full_stroke_time_s,
    v11_schedule,
)
from outrigger_sim.verify.metrics import fit_damped_sine  # noqa: E402


def _stroke_time(times: dict, prefix: str) -> float:
    """V11 stroke time by key prefix ("FL 0->").

    The key carries the stroke (0.68 before, 0.7 since REXOME35).
    """
    hits = [v for k, v in times.items() if k.startswith(prefix)]
    if len(hits) != 1:
        raise KeyError(f"V11 stroke time {prefix!r}: keys {list(times)}")
    return float(hits[0])


@dataclass(frozen=True)
class ActuatorCaptionValues:
    """Actuator numbers quoted in the S2b captions, computed from the YAML instead of literals."""

    stroke_mm: float
    v_max_mm_s: float
    ramp_s: float
    rod_mass_front_kg: float
    rod_mass_rear_kg: float
    ramp_force_front_N: float
    ramp_force_rear_N: float
    full_stroke_time_s: float
    v11_half_s: float
    v11_end_s: float


def actuator_caption_values(params) -> ActuatorCaptionValues:
    """Caption values of ``params`` (front = FL, rear = RL; m_rod a with a = v_max / ramp)."""
    actuator = params.actuator
    acceleration_m_s2 = actuator.max_speed_m_s / actuator.command_ramp_s
    front_kg = float(params.legs[LEG_ORDER.index("FL")].moving_part.mass_kg)
    rear_kg = float(params.legs[LEG_ORDER.index("RL")].moving_part.mass_kg)
    schedule = v11_schedule(params)
    return ActuatorCaptionValues(
        stroke_mm=actuator.stroke_m * 1e3,
        v_max_mm_s=actuator.max_speed_m_s * 1e3,
        ramp_s=actuator.command_ramp_s,
        rod_mass_front_kg=front_kg,
        rod_mass_rear_kg=rear_kg,
        ramp_force_front_N=front_kg * acceleration_m_s2,
        ramp_force_rear_N=rear_kg * acceleration_m_s2,
        full_stroke_time_s=expected_full_stroke_time_s(params),
        v11_half_s=schedule.segments[1].t0_s,
        v11_end_s=schedule.end_s,
    )


RES_A = ROOT / "07_results" / "S2a"
RES_B = ROOT / "07_results" / "S2b"
OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "12_S2"
VERIFY_A = OUT_DIR / "verify_S2a_L1.json"
VERIFY_B = OUT_DIR / "verify_S2b_L1.json"
CRAWLER_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s2b_crawler_check.json"
REFERENCE_JSON = ROOT / "06_analysis" / "00_dynamics" / "reference.json"
OUT = {
    "v7": OUT_DIR / "S2a_v7_free_vibration.gif",
    "dt": OUT_DIR / "S2a_dt_study.png",
    "v12": OUT_DIR / "S2a_v12_slope.gif",
    "v12_frame": OUT_DIR / "S2a_v12_slope_frame.png",
    "v12png": OUT_DIR / "S2a_v12_summary.png",
    "v11": OUT_DIR / "S2b_v11_stroke.gif",
    "ramp": OUT_DIR / "S2b_ramp_effect.png",
    "crawler": OUT_DIR / "S2b_crawler_settle.gif",
    "events": OUT_DIR / "S2b_contact_events.gif",
    "events_frame": OUT_DIR / "S2b_contact_events_frame.png",
    "summary_a": OUT_DIR / "S2a_summary.png",
    "summary_b": OUT_DIR / "S2b_summary.png",
    "json": OUT_DIR / "S2_gifs.json",
}
ALL_PARTS = ("v7", "dt", "v12", "v12png", "v11", "ramp", "crawler", "events", "summary")
DEFAULT_BEFORE_DIR = OUT_DIR / "history" / "before_planA"

FRAME_W, FRAME_H, DPI = s1.FRAME_W, s1.FRAME_H, s1.DPI
ACCENT = s1.ACCENT
LIN_COLOR = s1.LIN_COLOR
BAND_COLOR = s1.BAND_COLOR
EARTH_COLOR = s1.EARTH_COLOR
GROUND_COLOR = s1.GROUND_COLOR
COM_COLOR = "#e2245c"
EVENT_COLOR = "#9b59b6"
DT2_COLOR = "#0b0b0b"  # second time step overlay (thin black dashed)
BEFORE_COLOR = "#b9b8b3"
ARROW_N_M_PER_N = 1.0 / 100e3  # normal force arrow: 1 m per 100 kN (as S1)
ARROW_T_M_PER_N = 1.0 / 5e3  # tangential force arrow: 1 m per 5 kN (x20)
GROUND_RECT_XY = s1.GROUND_RECT_XY
LEVEL_LABEL = s1.LEVEL_LABEL
CRAWLER_W_REL_TOL = 1e-9  # result.json analytic_exact.weight_N vs s2b_crawler_check W_N
# Crawler sphere k_n: no constant here; crawler_kn_N_m() reads result.json
# analytic_exact.kn_per_sphere_float32_N_m and requires s2b_crawler_check.json
# meta.kn_per_sphere_float32_N_m to be the same number.

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# Second oblique camera for the FL events: viewer in front (+x), on the LEFT (+y) and above.
_TOWARD_L = np.array([0.60, 0.66, 0.45])
_TOWARD_L /= np.linalg.norm(_TOWARD_L)
_RIGHT_L = np.cross([0.0, 0.0, 1.0], _TOWARD_L)
_RIGHT_L /= np.linalg.norm(_RIGHT_L)
VIEWS["oblique_left"] = (_RIGHT_L, np.cross(_TOWARD_L, _RIGHT_L), _TOWARD_L)
CURRENT_VIEW = ["oblique"]


def scr(points):
    """Screen coordinates [m] in the current oblique view."""
    return s1.screen(points, CURRENT_VIEW[0])


# --- small helpers ---------------------------------------------------------------------------


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def place_cpu(mode: str) -> dict:
    info = {"mode": mode}
    if mode == "os":
        return info
    try:
        from outrigger_sim.hostcpu import place_process

        info.update(place_process(mode))
    except Exception as error:  # noqa: BLE001 - placement is optional
        info["error"] = repr(error)
    try:
        import psutil

        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        info["priority"] = "below_normal"
    except Exception as error:  # noqa: BLE001
        info["priority_error"] = repr(error)
    return info


def new_figure(width=FRAME_W, height=FRAME_H):
    return plt.figure(figsize=(width / DPI, height / DPI), dpi=DPI, facecolor=SURFACE)


def axes_box(fig, x, y, w, h, width=FRAME_W, height=FRAME_H):
    """Axes at an output pixel box (x, y from the top-left) of a figure of width x height px."""
    return fig.add_axes((x / width, 1 - (y + h) / height, w / width, h / height))


def leg_ticks(ax):
    ax.set_xticks(np.arange(4), LEG_ORDER)
    for tick, leg in zip(ax.get_xticklabels(), LEG_ORDER, strict=True):
        tick.set_color(LEG_COLORS[leg])
        tick.set_fontweight("bold")


def log_time_axis(ax, t_min, t_max, ticks=(0.01, 0.1, 1, 10)):
    ax.set_xscale("log")
    ax.set_xlim(t_min, t_max)
    ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([*ticks, t_max]))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def plain_log_formatter(ax, axis="y"):
    formatter = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_formatter(formatter)
    target.set_minor_formatter(matplotlib.ticker.NullFormatter())


def text_block(fig, x, y, lines, size=8.2, colour=INK_PRIMARY, width=FRAME_W, height=FRAME_H,
               **kwargs):
    return fig.text(x / width, 1 - y / height, "\n".join(lines), fontsize=size, va="top",
                    color=colour, linespacing=1.35, **kwargs)


def header_texts(fig):
    header = fig.text(8 / FRAME_W, 1 - 10 / FRAME_H, "", fontsize=13, fontweight="bold",
                      va="top", color=INK_PRIMARY)
    status = fig.text(8 / FRAME_W, 1 - 38 / FRAME_H, "", fontsize=10, va="top",
                      color=INK_PRIMARY)
    note = fig.text(8 / FRAME_W, 1 - 60 / FRAME_H, "", fontsize=8.3, va="top",
                    color=INK_SECONDARY)
    return header, status, note


def banner_text(fig, x=FRAME_W / 2, y=82):
    return fig.text(x / FRAME_W, 1 - y / FRAME_H, "", fontsize=12, fontweight="bold",
                    color="white", ha="center", va="center", zorder=20,
                    bbox=dict(boxstyle="round,pad=0.45", fc=EVENT_COLOR, ec="none"))


def set_banner(text_artist, text):
    text_artist.set_text(text or "")
    text_artist.set_visible(bool(text))


def _swatches() -> list[tuple[int, int, int]]:
    """Palette anchors: UI colours and the shaded / depth-faded leg colours of shade_scene
    (rgb * s + 0.1 (1 - s), s = 0.4..1; faded toward SURFACE by up to 0.35)."""
    out = []
    background = np.array(matplotlib.colors.to_rgb(SURFACE))
    for colour in [*LEG_COLORS.values(), OTHER_PART_COLOR]:
        base = np.array(matplotlib.colors.to_rgb(colour))
        for shade in (0.4, 0.55, 0.7, 0.85, 1.0):
            rgb = np.clip(base * shade + 0.1 * (1 - shade), 0, 1)
            for fade in (0.0, 0.2):
                out.append(tuple(int(round(v * 255)) for v in rgb * (1 - fade) + background * fade))
    for colour in (ACCENT, INK_PRIMARY, "white", COM_COLOR, EVENT_COLOR, BAND_COLOR, LIN_COLOR,
                   GROUND_COLOR, EARTH_COLOR, "#24324f", "#5f7fb3", "#a9bfe0", BEFORE_COLOR,
                   "#f7e9ef", "#f1efe9"):
        out.append(tuple(int(round(v * 255)) for v in matplotlib.colors.to_rgb(colour)))
    return out


def write_gif(frames, durations, path: Path) -> dict:
    """GIF as render_S1_gifs.write_gif (one global palette, unchanged pixels written as a
    reserved transparent index, disposal 1, round-trip check), with two changes: identical
    consecutive frames are merged first (Pillow would drop them silently), and the palette is
    taken from 8 frames plus the shaded leg colours (moving meshes otherwise lose the yellow)."""
    n_input = len(frames)
    merged, merged_d = [], []
    previous = None
    for frame, duration in zip(frames, durations, strict=True):
        data = np.asarray(frame)
        if previous is not None and np.array_equal(data, previous):
            merged_d[-1] += duration
            continue
        merged.append(frame)
        merged_d.append(duration)
        previous = data
    frames, durations = merged, merged_d
    sample_ids = sorted(set(np.linspace(0, len(frames) - 1, 8).astype(int).tolist()))
    w, h = frames[0].size
    swatches = _swatches()
    sample = Image.new("RGB", (w * len(sample_ids), h + 60))
    for k, i in enumerate(sample_ids):
        sample.paste(frames[i], (k * w, 0))
    sw = sample.width // len(swatches)
    for k, colour in enumerate(swatches):
        sample.paste(Image.new("RGB", (sw, 60), colour), (k * sw, h))
    palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colours = palette.getpalette()[: 3 * 255]
    colours += [0] * (3 * 255 - len(colours)) + [255, 0, 255]
    clear = 255
    lut = np.array(colours, dtype=np.uint8).reshape(-1, 3)
    check_ids = set(np.linspace(0, len(frames) - 1, 6).astype(int).tolist())
    expected, indexed, previous_codes = {}, [], None
    for n, frame in enumerate(frames):
        codes = np.asarray(frame.quantize(palette=palette, dither=Image.Dither.NONE)).copy()
        if n in check_ids:
            expected[n] = lut[codes]
        coded = codes.copy()
        if previous_codes is not None:
            coded[codes == previous_codes] = clear
        previous_codes = codes
        image = Image.fromarray(coded, "P")
        image.putpalette(colours)
        image.info["transparency"] = clear
        indexed.append(image)
    # a frame equal to the previous one after quantisation would be dropped by Pillow too
    keep = [0] + [n for n in range(1, len(indexed))
                  if (np.asarray(indexed[n]) != clear).any()]
    if len(keep) != len(indexed):
        new_d = []
        for n in range(len(indexed)):
            if n in keep:
                new_d.append(durations[n])
            else:
                new_d[-1] += durations[n]
        expected = {keep.index(n): v for n, v in expected.items() if n in keep}
        indexed = [indexed[n] for n in keep]
        durations = new_d
    durations = [max(20, int(round(d / 10.0)) * 10) for d in durations]
    s1.save_atomic(path, lambda target: indexed[0].save(
        target, save_all=True, append_images=indexed[1:], duration=durations, loop=0,
        optimize=False, disposal=1, transparency=clear))
    worst = 0
    with Image.open(path) as gif:
        n_frames = gif.n_frames
        for n in range(n_frames):
            gif.seek(n)
            if n in expected:
                decoded = np.asarray(gif.convert("RGB"), dtype=np.int16)
                worst = max(worst, int(np.abs(decoded - expected[n]).max()))
    return {"path": rel(path), "frames": n_frames,
            "roundtrip_max_abs_diff_rgb (decoded vs quantized, 6 frames)": worst,
            "size_bytes": path.stat().st_size, "loop_s": round(sum(durations) / 1000, 2),
            "resolution_px": [w, h], "merged_identical_frames": n_input - n_frames}


# --- meshes ----------------------------------------------------------------------------------


def cluster_mesh(vertices, faces, cell):
    """Vertex-clustering decimation: snap to a cubic grid of `cell` (mesh units), average the
    vertices of a cell, drop degenerate and duplicate faces (winding of the first copy kept)."""
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


def load_drawing_meshes(cache_dir: Path | None, cell_mm: float):
    """(parts table, decimated render meshes) in parts_classified.csv row order (+ stats)."""
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")
    # cache names carry the drawing-mesh file stem (render_mesh_v5 since 2026-11-09), so a cache of
    # the old decimated render_mesh.npz is not picked up
    cached = cache_dir / f"{RENDER_NPZ.stem}_cluster{cell_mm:g}mm.pkl" if cache_dir else None
    if cell_mm > 0 and cached is not None and cached.exists():
        with open(cached, "rb") as handle:
            data = pickle.load(handle)
        return parts, data["render"], data["stats"], cached
    full_cache = cache_dir / f"{RENDER_NPZ.stem}_full.pkl" if cache_dir else None
    if full_cache is not None and full_cache.exists():
        with open(full_cache, "rb") as handle:
            render = pickle.load(handle)
    else:
        render, _ = load_render_meshes(parts["instance_path"].tolist())
        if full_cache is not None:
            full_cache.parent.mkdir(parents=True, exist_ok=True)
            with open(full_cache, "wb") as handle:
                pickle.dump(render, handle, protocol=5)
    if len(render) != len(parts):
        raise SystemExit("render mesh rows differ from parts_classified.csv")
    if cell_mm > 0:
        decimated = [cluster_mesh(v, f, cell_mm) if len(f) > 200 else (v, f) for v, f in render]
    else:
        # cell 0 (default since 2026-11-09): the undecimated V5 mesh is drawn with the z-buffer;
        # vertex clustering of it collapsed thin plates and tore grilles and drums
        decimated = render
    stats = {"faces_full": int(sum(len(f) for _, f in render)),
             "faces_drawn": int(sum(len(f) for _, f in decimated)),
             "cluster_cell_mm": cell_mm, "parts": len(render),
             **{k: v for k, v in s1.drawing_mesh_record().items()}}
    if cell_mm <= 0 and full_cache is not None:
        return parts, decimated, stats, full_cache
    if cached is not None:
        with open(cached, "wb") as handle:
            pickle.dump({"render": decimated, "stats": stats}, handle, protocol=5)
    return parts, decimated, stats, cached


@dataclass
class MeshBank:
    parts: pd.DataFrame
    render: list
    topologies: list
    motions: list

    @classmethod
    def build(cls, parts, render):
        return cls(parts, render, build_topologies(render), classify(parts)["motion"].tolist())

    def items(self, params, s_motor, groups=None):
        """Body-frame items (vertices m, topology, colour, depth bias, fade, kind, leg) at the
        auger level of `params` and extensions `s_motor`. kind: body / barrel / rod."""
        travel = np.array([0.0, 0.0, params.superstructure.auger_travel_m])
        direction = extension_direction(params)
        legs = {leg.name: (i, leg) for i, leg in enumerate(params.legs)}
        out = []
        for (vertices, _), topo, row, motion in zip(self.render, self.topologies,
                                                       self.parts.itertuples(), self.motions,
                                                       strict=True):
            points = body_vertices(vertices)
            if motion in MOVING:
                points = points + travel
            if row.leg:
                i, spec = legs[row.leg]
                if row.group == "leg_rod_pad":
                    points = (points + spec.retracted_offset_from_cad_m
                              * np.array(spec.axis_direction) + s_motor[i] * direction)
                    kind = "rod"
                else:
                    kind = "barrel"
                item = (points, topo, LEG_COLORS[row.leg], LEG_DEPTH_BIAS_M, False, kind, row.leg)
            else:
                item = (points, topo, OTHER_PART_COLOR, 0.0, True, "body", "")
            if groups is None or (kind if row.leg else "body") in groups:
                out.append(item)
        return out


def plane_split(items, pos, rot, plane_point, plane_normal, tol=0.02):
    """World SceneItems split at a floor plane (below, above); signed distance along n."""
    below, above = [], []
    n = np.asarray(plane_normal, float)
    p0 = np.asarray(plane_point, float)
    for points, topo, colour, bias, fade, *_ in items:
        if len(topo.faces) == 0:
            continue
        world = points @ rot.T + pos
        dist = ((world[topo.faces].mean(axis=1) - p0) @ n)
        low = dist < -tol
        if not low.any():
            above.append(SceneItem(world, topo, colour, bias, fade))
            continue
        for mask, target in ((low, below), (~low, above)):
            if mask.any():
                target.append(SceneItem(world, part_topology(world, topo.faces[mask]), colour,
                                        bias, fade))
    return below, above


def floor_polygon(plane_point, plane_normal, rect=GROUND_RECT_XY):
    (x0, x1), (y0, y1) = rect
    n = np.asarray(plane_normal, float)
    p0 = np.asarray(plane_point, float)

    def z(x, y):
        return p0[2] - (n[0] * (x - p0[0]) + n[1] * (y - p0[1])) / n[2]

    return np.array([[x, y, z(x, y)] for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]), z


DEFAULT_EDGE_STYLE = EdgeStyle()


def render_scene(below, above, limits, size_px, floor=None, transparent_bg=True,
                 style=DEFAULT_EDGE_STYLE, view=None) -> Image.Image:
    """render_S1_gifs.render_mesh_image with an optional tilted floor plane (point, normal)."""
    view = view or CURRENT_VIEW[0]
    w, h = size_px
    s = s1.SUPERSAMPLE
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
    if floor is not None:
        polygon, zf = floor_polygon(*floor)
        ax.add_patch(Polygon(s1.screen(polygon, view), closed=True, facecolor=GROUND_COLOR,
                             alpha=0.82, edgecolor=EARTH_COLOR, lw=0.8 * s, zorder=2))
        (x0, x1), (y0, y1) = GROUND_RECT_XY
        for x in np.arange(np.ceil(x0), x1 + 1e-9, 1.0):
            seg = s1.screen(np.array([[x, y0, zf(x, y0)], [x, y1, zf(x, y1)]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * s, alpha=0.5, zorder=2.1)
        for y in np.arange(np.ceil(y0), y1 + 1e-9, 1.0):
            seg = s1.screen(np.array([[x0, y, zf(x0, y)], [x1, y, zf(x1, y)]]), view)
            ax.plot(seg[:, 0], seg[:, 1], color=EARTH_COLOR, lw=0.35 * s, alpha=0.5, zorder=2.1)
    if above:
        ax.add_collection(scene_collection(shade_scene(above, view, scale, style, DPI / s),
                                           zorder=3), autolim=False)
    figure.canvas.draw()
    image = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")
    plt.close(figure)
    return image.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")


class Scene:
    """3D panel: a mesh image in screen metres plus overlay artists."""

    def __init__(self, fig, box, limits, image):
        self.ax = axes_box(fig, *box)
        self.ax.set_xlim(*limits[0])
        self.ax.set_ylim(*limits[1])
        self.ax.set_axis_off()
        self.limits = limits
        self.image = self.ax.imshow(np.asarray(image), extent=(*limits[0], *limits[1]),
                                    origin="upper", interpolation="nearest", zorder=0,
                                    aspect="auto")

    def set_image(self, image):
        self.image.set_data(np.asarray(image))

    def arrow(self, colour, lw=2.2, head=(6, 3.5), z=5):
        patch = FancyArrowPatch((0, 0), (0, 0), arrowstyle=f"-|>,head_length={head[0]},"
                                f"head_width={head[1]}", color=colour, lw=lw, zorder=z,
                                shrinkA=0, shrinkB=0)
        self.ax.add_patch(patch)
        return patch

    def label(self, colour, size=8.0, **kwargs):
        return self.ax.text(0, 0, "", fontsize=size, color=colour, zorder=7,
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                                      alpha=0.85), **kwargs)


def set_arrow(arrow, tail_world, head_world, visible=True):
    if not visible or np.allclose(tail_world, head_world):
        arrow.set_visible(False)
        return
    st, sh = scr(tail_world)[0], scr(head_world)[0]
    arrow.set_positions(tuple(st), tuple(sh))
    arrow.set_visible(True)


def scene_limits_for(items, poses, size, extra_world=(), margin=(0.25, 0.25)):
    pts = []
    for pos, rot in poses:
        world = np.vstack([p for p, *_ in items]) @ rot.T + pos
        pts.append(scr(world[:: max(1, len(world) // 150000)]))
    for extra in extra_world:
        pts.append(scr(np.atleast_2d(extra)))
    return s1.fit_limits(np.vstack(pts), size, margin_m=margin)


# --- records ---------------------------------------------------------------------------------


@dataclass
class Run:
    name: str
    params: object
    a: dict
    result: dict
    events: list
    t: np.ndarray = field(init=False)
    rot: np.ndarray = field(init=False)

    def __post_init__(self):
        self.t = np.asarray(self.a["t"], float)
        self.rot = quat_to_matrix(self.a["body_quat_wxyz"])

    def index(self, t):
        return int(np.clip(np.searchsorted(self.t, t - 1e-12), 0, len(self.t) - 1))

    @property
    def pos(self):
        return np.asarray(self.a["body_pos"], float)


def load_run(stage_dir: Path, name: str, level: str = "top") -> Run:
    params = load_params(s1.PARAMS_PATH[0], level=level)  # --params (render_S1_gifs.PARAMS_PATH)
    record = load_record(stage_dir / name, params_sha256=params.sha256)
    result = read_json(stage_dir / name / "result.json")
    ev = record.bushing_events
    events = list(zip(ev["t"].tolist(), ev["leg"].tolist(), ev["kind"].tolist(), strict=True))
    return Run(name, params, {k: np.asarray(v) for k, v in record.arrays.items()}, result,
               events)


def sphere_centres_world(run: Run, i: int, s_motor) -> np.ndarray:
    centres = np.array([pad_sphere_centre_body_m(run.params, k, s_motor[k]) for k in range(4)])
    return centres @ run.rot[i].T + run.pos[i]


def swivel_radius(params) -> np.ndarray:
    return np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])


def tangential_world(ft_xy, normal):
    """Bushing force (world x, y from the Record) completed with z so that T . n = 0."""
    ft_xy = np.atleast_2d(ft_xy)
    tz = -(ft_xy[:, 0] * normal[0] + ft_xy[:, 1] * normal[1]) / normal[2]
    return np.column_stack([ft_xy, tz])


# =============================================================================================
# S2a V7 free vibration
# =============================================================================================

V7_CASES = (("v7_roll", 400.0, 0, "roll"), ("v7_pitch", 400.0, 1, "pitch"),
            ("v7_yaw", 600.0, 2, "yaw"))
MODE_NAMES = {1: "1차 roll-sway", 2: "2차 pitch-surge", 3: "3차 yaw-sway",
              4: "4차 pitch-surge-heave", 5: "5차 heave", 6: "6차 yaw-roll"}
V7_BOX = (8, 96, 560, 796)

_WORKER: dict = {}


def _v7_worker_init(mesh_pickle, s_motor, floor_z, cpu_mode="ecore", params_path=None):
    place_cpu(cpu_mode)
    s1.PARAMS_PATH[0] = params_path
    with open(mesh_pickle, "rb") as handle:
        data = pickle.load(handle)
    parts = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    parts["leg"] = parts["leg"].fillna("")
    # decimated cache: {"render", "stats"}; full-mesh cache (cluster 0): plain list
    bank = MeshBank.build(parts, data["render"] if isinstance(data, dict) else data)
    params = load_params(params_path, level="top")
    _WORKER["items"] = bank.items(params, np.asarray(s_motor))
    _WORKER["floor_z"] = floor_z


def _v7_worker_render(task):
    pos, rot, limits, size = task
    floor_z = _WORKER["floor_z"]
    below, above = plane_split(_WORKER["items"], pos, rot, (0.0, 0.0, floor_z), (0, 0, 1.0))
    image = render_scene(below, above, limits, size, floor=((0.0, 0.0, floor_z), (0, 0, 1.0)))
    return image.tobytes(), image.size


@dataclass
class V7Case:
    run: Run
    k: float
    axis: int
    label: str
    p0: np.ndarray
    R0: np.ndarray
    rotvec: np.ndarray  # (n, 3) world rotation vector relative to the equilibrium [rad]
    mode: dict
    modes: list
    ts: np.ndarray
    eta: np.ndarray
    fit: object
    plan: list
    checks: dict


def load_v7(name, k, axis, label) -> V7Case:
    run = load_run(RES_A, name)
    a, res = run.a, run.result
    # The Record keeps the snapshot clock (S1 top state at 15 s); use time since the kick.
    run.t = run.t - res["start_snapshot"]["t_s"]
    t0 = run.t[0]
    p0 = run.pos[0] - a["body_vel"][0] * t0
    R0 = Rotation.from_rotvec(-a["body_omega"][0] * t0).as_matrix() @ run.rot[0]
    rotvec = Rotation.from_matrix(run.rot @ R0.T).as_rotvec()
    judged = int(res["judged_mode"])
    mode = res["modes"][judged - 1]
    ts = np.asarray(res["series"]["t_s"], float)
    eta = np.asarray(res["series"]["eta_judged"], float)
    fit = fit_damped_sine(ts, eta, mode["f_damped_Hz"])
    checks = {
        "refit_minus_result_f_damped_Hz": fit.f_damped_Hz - mode["f_damped_Hz"],
        "refit_minus_result_zeta": fit.zeta - mode["zeta_fit"],
        "equilibrium_back_extrapolation_dt_s": t0,
        "s_motor_spread_m": float(np.ptp(a["s_motor"], axis=0).max()),
    }
    # frame plan: 2 periods in slow motion, then stroboscopic samples at positive peaks of the
    # dominant rotation (every m-th cycle)
    obs = rotvec[:, axis]
    period = 1.0 / mode["f_damped_Hz"]
    slow = np.arange(0.0, 2.0 * period, period / 12.0)
    peaks, _ = find_peaks(obs, distance=max(1, int(0.6 * period / np.median(np.diff(run.t)))))
    peaks = peaks[run.t[peaks] > 2.0 * period]
    step = max(1, math.ceil(len(peaks) / 12))
    strobe = peaks[::step]
    plan = [(run.index(t), "slow") for t in slow] + [(int(i), "strobe") for i in strobe]
    if plan[-1][0] != len(run.t) - 1:
        plan.append((len(run.t) - 1, "strobe"))
    checks.update({"slow_frames": len(slow), "strobe_frames": len(strobe) + 1,
                   "strobe_every_cycles": step})
    return V7Case(run, k, axis, label, p0, R0, rotvec, mode, res["modes"], ts, eta, fit, plan,
                  checks)


def v7_pose(case: V7Case, i: int):
    """Exaggerated rigid pose: rotation vector and origin displacement times k."""
    run = case.run
    R = Rotation.from_rotvec(case.k * case.rotvec[i]).as_matrix() @ case.R0
    p = case.p0 + case.k * (run.pos[i] - case.p0)
    return p, R


def mast_top_body(items) -> np.ndarray:
    pts = np.vstack([p for p, *_, kind, _leg in items if kind == "body"])
    top = pts[np.argmax(pts[:, 2])]
    return top


def v7_figure(case: V7Case, limits, mast_top, image0):
    fig = new_figure()
    scene = Scene(fig, V7_BOX, limits, image0)
    header, status, note = header_texts(fig)
    banner = banner_text(fig, x=290, y=120)
    run, mode, fit = case.run, case.mode, case.fit
    cursor = s1.Cursor()
    x0, wbig = 640, 735
    # eta(t) with the fitted and reference envelopes
    ax = axes_box(fig, x0, 112, wbig, 175)
    s1.style_axes(ax, title=f"모드 좌표 η (판정 모드 {MODE_NAMES[mode['mode']]}, "
                  f"η = Φ^T·M·q) [√kg·m]", xlabel="t [s]")
    ax.plot(case.ts, case.eta, color=INK_PRIMARY, lw=0.7)
    t_rel = case.ts - case.ts[0]
    env = fit.amplitude * np.exp(-fit.sigma_1_s * t_rel)
    omega_ref = 2 * np.pi * mode["f_ref_Hz"]
    sigma_ref = (mode["zeta_ref"] + mode["zeta_num_subtracted"]) * omega_ref
    env_ref = fit.amplitude * np.exp(-sigma_ref * t_rel)
    for sign in (1, -1):
        ax.plot(case.ts, fit.offset + sign * env, color=ACCENT, lw=1.3)
        ax.plot(case.ts, fit.offset + sign * env_ref, color=LIN_COLOR, lw=1.3, ls=(0, (4, 2)))
    ax.set_xlim(0, case.ts[-1])
    lim = 1.15 * np.abs(case.eta).max()
    ax.set_ylim(-lim, lim)
    cursor.add_axes(ax)
    eta_on_record = np.interp(run.t, case.ts, case.eta)
    cursor.add_dot(ax, run.t, eta_on_record, ACCENT)
    ax.legend(handles=[Line2D([], [], color=INK_PRIMARY, lw=0.8, label="Chrono η"),
                       Line2D([], [], color=ACCENT, lw=1.3, label=f"맞춘 포락선 ζ {fit.zeta:.5f}"),
                       Line2D([], [], color=LIN_COLOR, lw=1.3, ls=(0, (4, 2)),
                              label=f"기준 ζ {mode['zeta_ref']:.5f} + 수치 ζ "
                                    f"{mode['zeta_num_subtracted']:.2e}")],
              loc="upper right", fontsize=7.4, frameon=True, framealpha=0.9, ncol=3)
    # peak envelope on a log axis
    ax = axes_box(fig, x0, 340, 355, 165)
    s1.style_axes(ax, title="진폭 |η| 봉우리 (로그)  기울기 = -ζω", xlabel="t [s]")
    centred = case.eta - fit.offset
    pk, _ = find_peaks(np.abs(centred))
    ax.semilogy(case.ts[pk], np.abs(centred[pk]), "o", ms=2.4, color=INK_PRIMARY, mew=0)
    ax.semilogy(case.ts, env, color=ACCENT, lw=1.3)
    ax.semilogy(case.ts, env_ref, color=LIN_COLOR, lw=1.3, ls=(0, (4, 2)))
    ax.set_xlim(0, case.ts[-1])
    plain_log_formatter(ax)
    cursor.add_axes(ax)
    # modal content of the run
    ax = axes_box(fig, x0 + 400, 340, 335, 165)
    s1.style_axes(ax, title="모드별 |η| 최대 (이 가진에서, 로그)")
    values = [m["eta_max_abs"] for m in case.modes]
    colours = [ACCENT if m["mode"] == mode["mode"] else BEFORE_COLOR for m in case.modes]
    ax.bar(np.arange(1, 7), values, color=colours, width=0.6)
    ax.set_yscale("log")
    ax.set_xticks(np.arange(1, 7), [f"{i}차" for i in range(1, 7)])
    plain_log_formatter(ax)
    # attitude change
    ax = axes_box(fig, x0, 556, 355, 150)
    s1.style_axes(ax, title="자세 변화 (평형 대비) [1e-3 °]", xlabel="t [s]")
    names = ("roll", "pitch", "yaw")
    tones = ("#24324f", "#5f7fb3", "#a9bfe0")
    for j in range(3):
        y = np.degrees(case.rotvec[:, j]) * 1e3
        ax.plot(run.t, y, color=tones[j], lw=0.9 if j == case.axis else 0.7, label=names[j])
        cursor.add_dot(ax, run.t, y, tones[j])
    ax.set_xlim(0, run.t[-1])
    ax.legend(fontsize=7.2, ncol=3, loc="upper right", frameon=False)
    cursor.add_axes(ax)
    # pad normal force change
    ax = axes_box(fig, x0 + 400, 556, 335, 150)
    s1.style_axes(ax, title="패드 수직력 변화 (기록 평균 대비) [kN]", xlabel="t [s]")
    fn = run.a["F_contact_n"]
    dfn = (fn - fn.mean(axis=0)) / 1e3
    for k_leg, leg in enumerate(LEG_ORDER):
        ax.plot(run.t, dfn[:, k_leg], color=LEG_COLORS[leg], lw=0.8, label=leg)
        cursor.add_dot(ax, run.t, dfn[:, k_leg], LEG_COLORS[leg])
    ax.set_xlim(0, run.t[-1])
    ax.legend(fontsize=7.2, ncol=4, loc="upper right", frameon=False)
    cursor.add_axes(ax)
    # value table
    f_n = mode["f_undamped_Hz"]
    dev_f = (f_n / mode["f_ref_Hz"] - 1) * 100
    dev_z = (mode["zeta_corrected"] / mode["zeta_ref"] - 1) * 100
    lines = [
        f"판정 모드 {MODE_NAMES[mode['mode']]}   (V7: 진동수 ±3 %, ζ ±30 %)",
        f"f_d {mode['f_damped_Hz']:.5f} Hz → f_n {f_n:.5f} Hz   기준 |λ|/2π {mode['f_ref_Hz']:.4f} "
        "Hz"
        f"   차 {dev_f:+.3f} %",
        f"ζ 맞춤 {mode['zeta_fit']:.6f} - 수치 rωΔt/2 {mode['zeta_num_subtracted']:.3g} = "
        f"{mode['zeta_corrected']:.6f}   기준 {mode['zeta_ref']:.5f}   차 {dev_z:+.2f} %",
        f"맞춤 잔차(RMS 상대) {mode['residual_rms_rel']:.1e}, 주기 수 {mode['n_cycles']:.1f}"
        + (f", 봉우리 포락선 ζ {mode['zeta_log_decrement']:.6f}"
           if mode.get("zeta_log_decrement") else ""),
    ]
    text_block(fig, x0, 738, lines, size=8.6)
    text_block(fig, x0, 830, [
        f"출처: 07_results/S2a/{run.name}/record.npz (자세·힘, 1 ms 표본), result.json "
        "(η 시계열·모드 맞춤), verify_S2a_L1.json.",
        "포락선은 판정과 같은 맞춤 함수(verify.metrics.fit_damped_sine)로 다시 맞춘 값. "
        "t = 가진 뒤 시간(스냅숏 시각 15 s 뺌).",
        "가진: S1 상단 정착 상태(스냅숏)에서 초기 각속도만 줌. Δt "
        f"{s1.dt_text(run.result['dt_s'])}, "
        "L1(강체 위치 모터 + "
        "지면 부싱, 작용점 볼 중심)."], size=7.6, colour=INK_SECONDARY)
    (trail,) = scene.ax.plot([], [], color=ACCENT, lw=1.2, alpha=0.8, zorder=6)
    (top_now,) = scene.ax.plot([], [], "o", ms=6, color=ACCENT, mec="white", mew=0.8, zorder=7)
    eq = scr(case.R0 @ mast_top + case.p0)[0]
    scene.ax.plot([eq[0]], [eq[1]], "o", ms=9, mfc="none", mec=INK_PRIMARY, mew=1.2, zorder=6)
    scene.ax.plot([eq[0], eq[0]], [eq[1] - 3.0, eq[1] + 0.5], color=INK_PRIMARY, lw=0.8,
                  ls=(0, (3, 2)), zorder=6)
    scene.ax.text(eq[0] + 0.25, eq[1] + 0.35, "○ 평형 위치(마스트 끝)\n● 현재(확대)",
                  fontsize=7.5, color=INK_PRIMARY, zorder=7,
                  bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    return {"fig": fig, "scene": scene, "cursor": cursor, "header": header, "status": status,
            "note": note, "banner": banner, "trail": trail, "top": top_now}


def render_v7(args, bank, mesh_pickle, summary):
    cases = [load_v7(*spec) for spec in V7_CASES]
    params = cases[0].run.params
    s_motor = cases[0].run.a["s_motor"][-1]
    floor_z = params.ground.crawler_bottom_z_m
    items = bank.items(params, s_motor)
    top_body = mast_top_body(items)
    box = (V7_BOX[2], V7_BOX[3])
    limits = scene_limits_for(items, [(cases[0].p0, cases[0].R0)], box,
                              extra_world=[s1.ground_polygon(floor_z)], margin=(0.9, 0.5))
    tasks, owners = [], []
    for n, case in enumerate(cases):
        for i, _kind in case.plan:
            p, R = v7_pose(case, i)
            tasks.append((p, R, limits, box))
            owners.append((n, i))
    t_start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_v7_worker_init,
                             initargs=(str(mesh_pickle), s_motor.tolist(), floor_z,
                                       args.cpu,
                                       None if args.params is None else str(args.params))) as pool:
        images = [Image.frombytes("RGBA", size, data)
                  for data, size in pool.map(_v7_worker_render, tasks, chunksize=2)]
    render_s = time.perf_counter() - t_start
    print(f"  v7: {len(images)} mesh images in {render_s:.0f} s", flush=True)
    frames, durations, frame_info = [], [], []
    cursor_pos = 0
    for n, case in enumerate(cases):
        run = case.run
        first = images[cursor_pos]
        pieces = v7_figure(case, limits, top_body, first)
        mode = case.mode
        pieces["header"].set_text(
            f"S2a V7 자유 진동 [{n + 1}/3] · {case.label} 가진 → {MODE_NAMES[mode['mode']]} 판정 · "
            f"오거 상단 · L1 · Δt {s1.dt_text(run.result['dt_s'])} · 창 {run.t[-1]:.0f} s")
        pieces["note"].set_text(
            (f"3D: CAD 메시(정점 군집 {args.cluster_mm:g} mm). " if args.cluster_mm > 0
             else "3D: CAD 메시(V5, 단순화 없음). ")
            + f"변위·회전을 ×{case.k:g}로 확대해 그렸다"
            f"(실제 가진 진폭 {run.result['excitation']['amplitude_deg']:g}°). "
            "바닥 = 강체 평지. 빨간 선 = 마스트 끝의 확대 궤적."
            + (" 이 가진은 1차 roll-sway도 크게 가진함(3D = 모든 모드의 합, η = 판정 모드 투영)."
               if max(m["eta_max_abs"] for m in case.modes) > case.mode["eta_max_abs"] else ""))
        trail_pts = []
        for j, (i, kind) in enumerate(case.plan):
            image = images[cursor_pos]
            cursor_pos += 1
            pieces["scene"].set_image(image)
            p, R = v7_pose(case, i)
            top = scr(R @ top_body + p)[0]
            trail_pts.append(top)
            recent = np.array(trail_pts[-14:])
            pieces["trail"].set_data(recent[:, 0], recent[:, 1])
            pieces["top"].set_data([top[0]], [top[1]])
            pieces["cursor"].update(run.t[i], i)
            angles = np.degrees(case.rotvec[i]) * 1e3
            speed = ("슬로모션 (실제의 약 0.2배, 주기당 12장)" if kind == "slow"
                     else f"스트로보: {case.checks['strobe_every_cycles']}주기마다 같은 "
                          "위상(봉우리)")
            pieces["status"].set_text(
                f"t = {run.t[i]:6.3f} s   {speed}   roll {angles[0]:+.2f} · pitch {angles[1]:+.2f}"
                f" · yaw {angles[2]:+.2f} [1e-3 °]   그림 ×{case.k:g} → "
                f"{np.degrees(np.linalg.norm(case.rotvec[i])) * case.k:.2f}°")
            set_banner(pieces["banner"], "")
            frames.append(s1.figure_to_image(pieces["fig"]))
            last = j == len(case.plan) - 1
            durations.append(900 if j == 0 else 1600 if last else 75 if kind == "slow" else 220)
            frame_info.append({"case": run.name, "t_s": round(float(run.t[i]), 4), "kind": kind})
            if args.frames_dir and j in (6, len(case.plan) - 1):
                frames[-1].save(args.frames_dir / f"v7_{case.label}_{j:02d}.png")
        plt.close(pieces["fig"])
    summary["v7_gif"] = write_gif(frames, durations, OUT["v7"])
    summary["v7"] = {
        "mesh_render_s": round(render_s, 1), "workers": args.workers,
        "exaggeration": {c.run.name: c.k for c in cases},
        "limits_screen_m": [list(map(float, limits[0])), list(map(float, limits[1]))],
        "checks": {c.run.name: c.checks for c in cases},
        "mast_top_body_m": top_body.round(3).tolist(),
    }
    return cases


# =============================================================================================
# S2a dt study (PNG)
# =============================================================================================


DT_STUDY_TONES = ("#a9bfe0", "#5f7fb3", "#24324f")
"""Colours of the three dt-study runs, smallest dt first."""
V7_JUDGED_CASES = ("v7_roll", "v7_pitch", "v7_yaw")
"""Unsuffixed V7 judging runs (YAML dt); never part of the dt study."""


def pass_word(ok: bool) -> str:
    return "통과" if ok else "불통과"


def dt_study_rows(study: dict) -> tuple[list[dict] | None, str | None]:
    """Rows of ``verify_S2a_L1.json`` ``v7_yaw_dt_study`` sorted by dt, or ``(None, reason)``.

    The study is drawn only when it is complete with three distinct dt values, each row's case is
    the suffixed folder ``dt_case_name("v7_yaw", dt_s)`` listed in ``folders``, and that folder's
    result.json stores the same ``dt_s`` and ``case`` (the run_S2a.py rule).
    """
    rows = sorted(study.get("rows", []), key=lambda r: r["dt_s"])
    if study.get("status") != "complete":
        return None, f"v7_yaw_dt_study status {study.get('status')!r} (not complete)"
    dts = [float(r["dt_s"]) for r in rows]
    if len(rows) != 3:
        return None, f"{len(rows)} dt-study rows (need 3): {dts}"
    if any(math.isclose(a, b, rel_tol=1e-9) for i, a in enumerate(dts) for b in dts[i + 1:]):
        return None, f"dt values not distinct: {dts}"
    folders = set(study.get("folders", []))
    for r in rows:
        expected = dt_case_name("v7_yaw", r["dt_s"])
        if r["case"] != expected:
            return None, (f"row dt_s {r['dt_s']!r} has case {r['case']!r}, "
                          f"folder name gives {expected}")
        if r["case"] not in folders:
            return None, f"row case {r['case']} not in folders {sorted(folders)}"
        res_path = RES_A / r["case"] / "result.json"
        if not res_path.is_file():
            return None, f"{rel(res_path)} missing"
        res = read_json(res_path)
        same_dt = math.isclose(float(res["dt_s"]), r["dt_s"], rel_tol=1e-9)
        if not same_dt or res.get("case") != r["case"]:
            return None, (f"{rel(res_path)}: stored dt_s {res['dt_s']!r} / case "
                          f"{res.get('case')!r} does not match row dt_s {r['dt_s']!r} / case "
                          f"{r['case']}")
    return rows, None


def judged_v7_dt() -> list[float]:
    """Stored dt_s of the unsuffixed V7 judging runs (one value expected: the YAML dt)."""
    return sorted({float(read_json(RES_A / c / "result.json")["dt_s"]) for c in V7_JUDGED_CASES})


def render_dt_study(summary):
    verify = read_json(VERIFY_A)
    study = verify["v7_yaw_dt_study"]
    rows, skip_reason = dt_study_rows(study)
    if rows is None:
        print(f"dt study not drawn: {skip_reason}", flush=True)
        summary["dt_study"] = {"png": None, "drawn": False, "skip_reason": skip_reason,
                               "stale_png_left": OUT["dt"].exists()}
        return None
    dt = np.array([r["dt_s"] for r in rows])
    cases = [r["case"] for r in rows]
    z_fit = np.array([r["zeta_fit_raw"] for r in rows])
    z_env = np.array([r["zeta_log_decrement"] for r in rows])
    # Every number and sentence below comes from v7_yaw_dt_study (run_S2a.yaw_dt_study);
    # the refit is only a cross-check recorded in S2_gifs.json.
    slope = study["slope_dzeta_ddt_per_s"]
    intercept = study["intercept_zeta"]
    slope_refit, intercept_refit = (float(v) for v in np.polyfit(dt, z_fit, 1))
    slope_env = study["envelope_slope_dzeta_ld_ddt_per_s"]
    env_ratio = study["envelope_slope_ratio"]
    s_pred = study["slope_predicted_implicit_per_s"]
    ratio = study["slope_ratio_measured_over_implicit"]
    ratio_inc = study["increment_ratio"]
    zeta_ref = study["zeta_ref"]
    intercept_rel = study["intercept_rel_diff"]
    ct_scale = float(np.mean([r["prediction_ct_scale"] for r in rows]))  # equal on every row
    ct_excess = ct_scale / zeta_ref - 1.0
    crit = study["criteria"]
    checks = study["checks"]
    passed = all(checks.values())
    band = crit["A1_slope_ratio_band"]
    inc_exp, inc_tol = crit["A2_increment_ratio"]["expected"], crit["A2_increment_ratio"]["rel_tol"]
    a3_max = crit["A3_intercept_rel_max"]
    dt_judge = judged_v7_dt()
    dt_label = " / ".join(f"{d:.0e}" for d in dt)
    verdict_short = ("가설 A 확정, c_t 과대 없음" if passed
                     else "A1~A3 실패: " + ", ".join(k for k, v in checks.items() if not v))
    fig = new_figure(1400, 760)
    W, H = 1400, 760
    fig.text(8 / W, 1 - 10 / H, f"S2a Δt 연구 · V7 yaw 가진 2 s, 3차 yaw-sway 모드의 식별 ζ3 대 Δt "
             f"(Δt {dt_label} s, 오거 상단, L1, 부싱 작용점 볼 중심) · 판정: {pass_word(passed)}",
             fontsize=13, fontweight="bold", va="top", color=INK_PRIMARY)
    subtitle = (
        "가설 A(부싱만 암시 적분 → 수치 감쇠 ζ_num = r3·ω3·Δt/2, Δt에 비례) 대 "
        f"가설 B(명시 적분 + 실효 c_t {ct_excess * 100:.1f} % 과대 → Δt와 무관).\n"
        f"실측 기울기 / A 예측 = {ratio:.3f}, 절편 {intercept:.6f}"
        f"(기준 ζ3 {zeta_ref:.4f} 대비 {intercept_rel * 100:+.2f} %) → {verdict_short}."
    )
    fig.text(8 / W, 1 - 38 / H, subtitle, fontsize=9, va="top", color=INK_SECONDARY)
    ax = axes_box(fig, 70, 90, 640, 560, W, H)
    s1.style_axes(ax, title="ζ3 (식별) [-] 대 Δt", xlabel="Δt [1e-4 s]", ylabel="ζ3")
    x_max = 1.1 * dt[-1]
    xs = np.linspace(0, x_max, 50)
    ax.plot(xs * 1e4, zeta_ref + s_pred * xs, color=ACCENT, lw=1.6,
            label=f"가설 A 예측: {zeta_ref:.4f} + {s_pred:.2f}·Δt  (s_pred = r3ω3/2)")
    ax.plot(xs * 1e4, intercept + slope * xs, color=INK_PRIMARY, lw=1.0, ls=(0, (1, 1.5)),
            label=f"맞춤 3점 최소자승: {intercept:.6f} + {slope:.3f}·Δt")
    ax.axhline(ct_scale, color=LIN_COLOR, lw=1.4, ls=(0, (5, 3)),
               label=f"가설 B(c_t 배율): Δt와 무관 = {ct_scale:.5f} (세 점 평균)")
    ax.axhline(zeta_ref, color="#5f7fb3", lw=0.9, ls=(0, (2, 2)),
               label=f"기준 물리 ζ3 {zeta_ref:.4f} (reference.json rev13)")
    ax.plot(dt * 1e4, z_fit, "o", ms=8, color=ACCENT, mec="white", mew=1, zorder=5,
            label="Chrono 식별 ζ3 (감쇠 정현 맞춤)")
    ax.plot(dt * 1e4, z_env, "s", ms=6, color="#5f7fb3", mec="white", mew=0.8, zorder=5,
            label=f"봉우리 포락선 ζ3 (교차 추정기, 기울기 {slope_env:.2f}, 비 {env_ratio:.2f})")
    for x, y in zip(dt, z_fit, strict=True):
        ax.annotate(f"{y:.5f}", (x * 1e4, y), textcoords="offset points", xytext=(8, -12),
                    fontsize=8, color=ACCENT)
    ax.set_xlim(0, x_max * 1e4)
    y_all = np.concatenate([z_fit, z_env, [zeta_ref, ct_scale, intercept,
                                           zeta_ref + s_pred * x_max, intercept + slope * x_max]])
    y_pad = 0.12 * (y_all.max() - y_all.min())
    # extra headroom above for the upper-left legend (7 entries)
    ax.set_ylim(y_all.min() - y_pad, y_all.max() + 4.5 * y_pad)
    ax.legend(fontsize=8, loc="upper left", frameon=True, framealpha=0.92)
    # eta traces
    ax2 = axes_box(fig, 790, 90, 590, 300, W, H)
    s1.style_axes(ax2, title="η3 시계열 (2 s, result.json series) — 세 Δt", xlabel="t [s]",
                  ylabel="√kg·m")
    peaks_info = []
    t_end = 0.0
    for r, tone in zip(rows, DT_STUDY_TONES, strict=True):
        res = read_json(RES_A / r["case"] / "result.json")
        ts = np.asarray(res["series"]["t_s"])
        eta = np.asarray(res["series"]["eta_judged"])
        t_end = max(t_end, float(ts[-1]))
        ax2.plot(ts, eta, color=tone, lw=0.8, label=f"Δt {r['dt_s']:g} s")
        pk, _ = find_peaks(np.abs(eta - eta[-200:].mean()))
        peaks_info.append((r["dt_s"], tone, ts[pk], np.abs(eta - eta[-200:].mean())[pk]))
    ax2.legend(fontsize=8, loc="upper right", ncol=3, frameon=False)
    ax2.set_xlim(0, t_end)
    ax3 = axes_box(fig, 790, 450, 590, 200, W, H)
    s1.style_axes(ax3, title="|η3| 봉우리 (로그) — Δt가 클수록 빨리 감쇠", xlabel="t [s]")
    for d, tone, tp, ap in peaks_info:
        ax3.semilogy(tp, ap, "o-", ms=3, lw=0.8, color=tone, label=f"Δt {d:g} s")
    plain_log_formatter(ax3)
    ax3.set_xlim(0, t_end)
    ax3.legend(fontsize=8, loc="lower left", ncol=3, frameon=False)
    d1, d2, d3 = (f"{d:.0e}" for d in dt)
    lines = [f"A1 기울기 실측 {slope:.3f} 1/s, 예측 {s_pred:.2f} 1/s → 비 {ratio:.4f} "
             f"(허용 {band[0]:g}~{band[1]:g}): {pass_word(checks['A1'])}",
             f"A2 증분비 (ζ({d3})-ζ({d2}))/(ζ({d2})-ζ({d1})) = {ratio_inc:.4f} "
             f"(기대 {inc_exp:g} ± {inc_tol * 100:.0f} %): {pass_word(checks['A2'])}",
             f"A3 절편(Δt → 0) {intercept:.6f}, 기준 ζ3 {zeta_ref:.4f} 대비 "
             f"{intercept_rel * 100:+.3f} % "
             f"(허용 ±{a3_max * 100:g} %): {pass_word(checks['A3'])}",
             "판정 실행 v7_roll·v7_pitch·v7_yaw의 Δt = "
             + " / ".join(f"{d:g}" for d in dt_judge) + " s(YAML). Δt 연구는 접미사 폴더 3개만 "
                                                        "쓴다."]
    if study.get("validity_warnings"):
        lines.append("경고: " + "; ".join(study["validity_warnings"]))
    text_block(fig, 80, 685, lines, size=9, width=W, height=H)
    fig.text(790 / W, 1 - 690 / H, "출처: verify_S2a_L1.json v7_yaw_dt_study, 07_results/S2a/"
             "{" + ", ".join(cases) + "}/result.json", fontsize=7.8,
             color=INK_SECONDARY, va="top")
    image = s1.figure_to_image(fig)
    plt.close(fig)
    s1.save_atomic(OUT["dt"], image.save)
    summary["dt_study"] = {"png": rel(OUT["dt"]), "drawn": True, "cases": cases,
                           "dt_s": dt.tolist(), "judged_v7_dt_s": dt_judge,
                           "slope_fit_per_s": slope, "intercept": intercept,
                           "refit_minus_json": {"slope_per_s": slope_refit - slope,
                                                "intercept": intercept_refit - intercept},
                           "slope_envelope_per_s": slope_env, "increment_ratio": ratio_inc,
                           "slope_ratio": ratio, "zeta_ref": zeta_ref,
                           "ct_scale_prediction": ct_scale, "checks": checks,
                           "source": "verify_S2a_L1.json v7_yaw_dt_study"}
    return {"dt": dt, "z_fit": z_fit, "s_pred": s_pred, "slope": slope, "intercept": intercept}


# =============================================================================================
# S2a V12 sloped floor
# =============================================================================================

V12_CASES = (("v12_pitch2", "pitch 2°"), ("v12_roll2", "roll 2°"),
             ("v12_rollm2_pitch1.5", "roll -2°, pitch 1.5°"))
V12_BOX = (8, 96, 600, 796)


@dataclass
class V12Case:
    run: Run
    label: str
    normal: np.ndarray
    floor_point: np.ndarray
    s_motor: np.ndarray
    verify: dict
    expected: dict  # reference.json slope_V12 / <case> / L1_plan_A_expected_..._rev13
    diagnosis: list  # verify_S2a_L1.json v12_plan_a_diagnosis / <case>
    before_N: np.ndarray
    before_source: str
    before_label: str
    after_N: np.ndarray
    reference_ft: np.ndarray
    contact: np.ndarray  # (n, 4, 3) contact point world
    T: np.ndarray  # (n, 4, 3) tangential world
    series: dict
    checks: dict

    @property
    def p_delta_N(self) -> np.ndarray:
        return np.array(self.expected[PLAN_A_P_DELTA_KEY], float)

    @property
    def lever_N(self) -> np.ndarray:
        return np.array(self.expected[PLAN_A_REV12_KEY][PLAN_A_LEVER_KEY], float)

    @property
    def diag_vertical_deviation_N(self) -> np.ndarray:
        return np.array(v12_diag_vertical(self.diagnosis)["deviation"], float)


# reference.json slope_V12 / <case> / PLAN_A_EXPECTED_KEY (independent statics, current YAML)
PLAN_A_EXPECTED_KEY = "L1_plan_A_expected_chrono_minus_reference_rev13"
PLAN_A_P_DELTA_KEY = "P_delta_nonlinear_minus_linear_vertical_N"
PLAN_A_REV12_KEY = "rev12_contact_point_bushing (S2a run before plan A)"
PLAN_A_LEVER_KEY = "sphere_lever_part_vertical_N (contact - ball, nonlinear)"
PLAN_A_REV12_MODEL_KEY = "chrono_model_minus_reference_vertical_N"
BEFORE_LABEL_RUN = "안 A 전 Chrono (부싱 작용점 = 구 접촉점, 개정 12)"
BEFORE_LABEL_MODEL = "안 A 전(접촉점 부싱) 독립 모델값"
BACKUP_W_REL_TOL = 1e-5  # reference vertical reactions are stored to ~6 significant digits


def plan_a_expected(reference: dict, verify_case: dict) -> dict:
    return reference["slope_V12"][verify_case["start"]["case"]][PLAN_A_EXPECTED_KEY]


def v12_diag_vertical(diagnosis: list) -> dict:
    """The vertical row (D[0]) of verify v12_plan_a_diagnosis / <case>."""
    rows = [r for r in diagnosis if "vertical" in r["item"]]
    if len(rows) != 1:
        raise SystemExit(f"v12_plan_a_diagnosis: expected one vertical row, got {len(rows)}")
    return rows[0]


def vertical_minus_reference(window: dict, reference: dict) -> np.ndarray:
    return np.array([w[2] - r[2] for w, r in zip(window["reaction_world_mean_N"],
                                                  reference["reaction_world_N"], strict=True)])


def table_rows(verify: dict, check_id: str, item_part: str, cases=None) -> list[dict]:
    """verify_S2a_L1.json table rows of ``check_id`` whose item contains ``item_part``."""
    rows = [r for r in verify["table"] if r["id"] == check_id and item_part in r["item"]
            and (cases is None or r["case"] in cases)]
    if not rows:
        raise SystemExit(f"verify table: no {check_id} row with {item_part!r}")
    return rows


def abs_max(values) -> float:
    return float(np.max(np.abs(np.asarray(values, float))))


def v12_vertical_tol_N(verify: dict) -> float:
    """V12 vertical reaction tolerance per leg (+-1 % W/4) from the verify table (smallest)."""
    rows = table_rows(verify, "V12", "vertical reaction per leg")
    return float(min(np.min(np.asarray(r["tol"], float)) for r in rows))


def _backup_params_sha(backup: dict):
    for holder in (backup, backup.get("record") if isinstance(backup.get("record"), dict)
                   else None, backup.get("start")):
        if isinstance(holder, dict) and holder.get("params_sha256"):
            return holder["params_sha256"]
    return None


def v12_before(name: str, verify_case: dict, reference: dict, before_dir, params_sha=None):
    """Rev-12 (contact-point bushing) vertical Chrono - reference of one case.

    The --before-dir backup (a rev-12 Chrono run) is used only if it was run with the current
    YAML: same params sha when both are known, else the same total weight W (sum of the
    reference vertical reactions, rel. BACKUP_W_REL_TOL). Otherwise the independent
    contact-point model values of reference.json are used.
    Returns (values [N], source text, legend label).
    """
    reason = "백업 없음"
    backup = before_dir / f"S2a_{name}.json" if before_dir else None
    if backup is not None and backup.exists():
        b = read_json(backup)
        if b["ground_bushing"].get("force_point", "contact_point") == "ball_centre":
            raise SystemExit(f"{backup}: not a contact-point (rev 12) result")
        sha_b = _backup_params_sha(b)
        w_b = sum(r[2] for r in b["reference"]["reaction_world_N"])
        w_now = sum(r[2] for r in verify_case["reference"]["reaction_world_N"])
        if sha_b is not None and params_sha is not None:
            same = sha_b == params_sha
            reason = "백업 params sha 다름"
        else:
            same = abs(w_b / w_now - 1) <= BACKUP_W_REL_TOL
            reason = f"백업 W {w_b / 1e3:.1f} kN ≠ 현재 {w_now / 1e3:.1f} kN"
        if same:
            return (vertical_minus_reference(b["window"], b["reference"]),
                    f"rev-12 Chrono 실행 결과 백업 ({backup.name}, 창 평균, 현재 YAML)",
                    BEFORE_LABEL_RUN)
    rev = plan_a_expected(reference, verify_case)[PLAN_A_REV12_KEY]
    return (np.array(rev[PLAN_A_REV12_MODEL_KEY], float),
            f"reference.json slope_V12/<case>/{PLAN_A_EXPECTED_KEY}/rev12_contact_point_bushing "
            f"/ {PLAN_A_REV12_MODEL_KEY} (독립 모델값; --before-dir 미사용: {reason})",
            BEFORE_LABEL_MODEL)


def load_v12(name, label, verify_all, reference, before_dir) -> V12Case:
    run = load_run(RES_A, name)
    res = run.result
    start = res["start"]
    normal = np.array(start["normal_world"])
    point = np.array(start["floor_point_world_m"])
    s_motor = np.asarray(run.a["s_motor"][-1], float)
    verify = verify_all["v12"][name]
    window = verify["window"]
    ref = verify["reference"]
    after = vertical_minus_reference(window, ref)
    before, source, before_label = v12_before(name, verify, reference, before_dir,
                                              run.params.sha256)
    radius = swivel_radius(run.params)
    centres_body = np.array([pad_sphere_centre_body_m(run.params, k, s_motor[k])
                             for k in range(4)])
    centres = np.einsum("nij,kj->nki", run.rot, centres_body) + run.pos[:, None, :]
    contact = centres - radius[None, :, None] * normal[None, None, :]
    T = np.stack([tangential_world(run.a["F_contact_t"][:, k], normal) for k in range(4)], axis=1)
    checks = {
        "s_motor_spread_m": float(np.ptp(run.a["s_motor"], axis=0).max()),
        "window_mean_normal_minus_verify_N": float(np.abs(
            run.a["F_contact_n"][run.t >= window["mean_window_s"][0] - 1e-9].mean(axis=0)
            - np.array(window["normal_mean_N"])).max()),
    }
    return V12Case(run, label, normal, point, s_motor, verify, plan_a_expected(reference, verify),
                   verify_all["v12_plan_a_diagnosis"][name], before, source, before_label, after,
                   np.array(ref["tangential_N"]), contact, T, res["series"], checks)


def window_text(window: dict) -> str:
    """Mean window of verify v12 / <case> / window as "50~53 s"."""
    t0, t1 = window["mean_window_s"]
    return f"{t0:.0f}~{t1:.0f} s"


def v12_release_normal_N(case: V12Case) -> np.ndarray:
    """Recorded pad normal force per leg at its hold release time (verify ground_bushing)."""
    release = case.verify["ground_bushing"]["hold_release_t_s"]
    normal = case.run.a["F_contact_n"]
    return np.array([normal[case.run.index(t), k] for k, t in enumerate(release)], float)


V12_LATE_FRAMES = 5  # log-spaced settling frames from V12_LATE_START_S to the window start
V12_LATE_START_S = 5.0


def v12_late_times(ramp_s: float, window: dict, t_end: float) -> list[float]:
    """Settling frame times after the gravity ramp, inside the recorded run.

    Log-spaced from ``max(V12_LATE_START_S, ramp_s + 0.1)`` to the start of the verify mean
    window (``window["mean_window_s"][0]``), then the window end clipped to the record end
    ``t_end``. Every time is <= ``t_end``, so the last GIF frames never repeat the end sample.
    """
    w0, w1 = (float(v) for v in window["mean_window_s"])
    t_last = min(w1, float(t_end))
    t0 = max(V12_LATE_START_S, ramp_s + 0.1)
    if not t0 < w0 < t_last - 1e-6:
        raise SystemExit(f"V12 frame plan: need ramp end {t0:g} s < window start {w0:g} s "
                         f"< record end {t_last:g} s")
    return [float(t) for t in np.geomspace(t0, w0, V12_LATE_FRAMES)] + [t_last]


def v12_plan(case: V12Case):
    release = case.verify["ground_bushing"]["hold_release_t_s"]
    n_release = v12_release_normal_N(case)
    t_banner = max(release) + 0.004
    times = [(t, None) for t in np.arange(0.02, 0.0701, 0.025)]
    times.append((t_banner, "hold 해제: " + " / ".join(
        f"{leg} {t * 1e3:.1f}" for leg, t in zip(LEG_ORDER, release, strict=True))
        + f" ms\n조건 N > N_th {TOUCH_THRESHOLD_N:g} N · 해제 시 기록 N "
        + " / ".join(f"{n:.0f}" for n in n_release) + " N"))
    times += [(t, None) for t in (0.12, 0.2, 0.35, 0.55, 0.8, 1.1, 1.5, 2.0, 2.5, 3.0)]
    ramp_s = float(case.run.result["ramp_s"])
    window = case.verify["window"]
    times.append((ramp_s + 0.05, f"중력 램프 끝({ramp_s:g} s): 이후 정착 → 판정 창 "
                  f"{window_text(window)}"))
    late = v12_late_times(ramp_s, window, float(case.run.t[-1]))
    times += [(t, None) for t in late[:-2]]
    times.append((late[-2], f"판정 창 시작 {window_text(window)} (창 평균 = verify v12)"))
    times.append((late[-1], None))
    return times


def v12_figure(case: V12Case, limits, image, vertical_tol_N: float):
    fig = new_figure()
    scene = Scene(fig, V12_BOX, limits, image)
    header, status, note = header_texts(fig)
    banner = banner_text(fig, x=310, y=122)
    run = case.run
    cursor = s1.Cursor()
    t = run.t
    t_min, t_max = 0.01, t[-1]
    x0, w, gx = 680, 330, 50
    release = case.verify["ground_bushing"]["hold_release_t_s"]

    def time_axes(ax):
        log_time_axis(ax, t_min, t_max)
        ax.axvspan(case.verify["window"]["mean_window_s"][0], t_max, color="#f1efe9", lw=0,
                   zorder=0)
        ax.axvspan(t_min, max(release), color="#f7e9ef", lw=0, zorder=0)
        cursor.add_axes(ax)

    ax = axes_box(fig, x0, 112, w, 140)
    s1.style_axes(ax, title="중력 배율 (반코사인 램프 3 s)", xlabel="t [s]")
    ts = np.asarray(case.series["t_s"])
    gs = np.asarray(case.series["gravity_scale"])
    ax.plot(ts, gs, color=INK_PRIMARY, lw=1.2)
    time_axes(ax)
    ax.set_ylim(-0.05, 1.1)
    cursor.add_dot(ax, t, np.interp(t, ts, gs), ACCENT)
    ax = axes_box(fig, x0 + w + gx, 112, w, 140)
    s1.style_axes(ax, title="패드 법선력 N [kN] (점선 = 기준)", xlabel="t [s]")
    time_axes(ax)
    fn = run.a["F_contact_n"] / 1e3
    ref_n = np.array(case.verify["reference"]["normal_N"]) / 1e3
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, fn[:, k], color=LEG_COLORS[leg], lw=1.1)
        ax.axhline(ref_n[k], color=LEG_COLORS[leg], lw=0.7, ls=(0, (3, 2)))
        cursor.add_dot(ax, t, fn[:, k], LEG_COLORS[leg])
    ax.set_ylim(-5, 135)
    ax = axes_box(fig, x0, 300, w, 140)
    s1.style_axes(ax, title="부싱 면내력 |T| [kN] (점선 = 기준)", xlabel="t [s]")
    time_axes(ax)
    tmag = np.linalg.norm(case.T, axis=2) / 1e3
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, tmag[:, k], color=LEG_COLORS[leg], lw=1.1)
        ax.axhline(case.reference_ft[k] / 1e3, color=LEG_COLORS[leg], lw=0.7, ls=(0, (3, 2)))
        cursor.add_dot(ax, t, tmag[:, k], LEG_COLORS[leg])
    ax.set_ylim(-0.2, 5.6)
    ax = axes_box(fig, x0 + w + gx, 300, w, 140)
    s1.style_axes(ax, title="마찰 사용률 |T|/N [-] (μ = 0.5)", xlabel="t [s]")
    time_axes(ax)
    util = np.divide(tmag, fn, out=np.zeros_like(tmag), where=fn > 1.0)
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, util[:, k], color=LEG_COLORS[leg], lw=1.1)
        cursor.add_dot(ax, t, util[:, k], LEG_COLORS[leg])
    ax.set_ylim(0, 0.08)
    # final vertical difference bars
    ax = axes_box(fig, x0, 500, 2 * w + gx, 190)
    s1.style_axes(ax, title="정착 수직력 Chrono - 기준 [N] (창 "
                            f"{window_text(case.verify['window'])} 평균, "
                            f"허용 ±{vertical_tol_N:.0f} N)", ylabel="N")
    xs = np.arange(4)
    width = 0.26
    ax.bar(xs - width, case.before_N, width, color=BEFORE_COLOR, hatch="///", edgecolor="white",
           label=case.before_label)
    bars = ax.bar(xs, case.after_N, width, color=[LEG_COLORS[leg] for leg in LEG_ORDER],
                  label="안 A 후 (작용점 = 볼 중심, 이 실행)")
    ax.plot(xs + width, case.p_delta_N, "D", ms=6, color=ACCENT, mec="white", mew=0.6,
            label="독립 비선형 예측 (P-δ, 볼 중심, rev13 현재 YAML)")
    for b, v in zip(bars, case.after_N, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + (12 if v >= 0 else -12), f"{v:+.1f}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=7.6, color=INK_PRIMARY)
    for x, v in zip(xs - width, case.before_N, strict=True):
        ax.text(x, v + (12 if v >= 0 else -12), f"{v:+.0f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=7.2, color=INK_SECONDARY)
    ax.axhline(0, color=INK_PRIMARY, lw=0.7)
    ax.set_ylim(-420, 420)
    leg_ticks(ax)
    ax.legend(fontsize=7.4, loc="upper right", frameon=True, framealpha=0.9, ncol=1)
    gb = case.verify["ground_bushing"]
    win = case.verify["window"]
    lines = [
        f"자세 roll {win['roll_mean_deg']:+.5f}° / pitch {win['pitch_mean_deg']:+.5f}° "
        f"(기준 {case.verify['reference']['attitude_change_deg'][0]:+.5f} / "
        f"{case.verify['reference']['attitude_change_deg'][1]:+.5f})",
        f"부싱 탄성 변위 {' / '.join(f'{v * 1e3:.4f}' for v in win['bushing_disp_mean_m'])} mm, "
        f"미끄럼 0, 항복 {sum(gb['yield_steps'])} 스텝, 부싱 사건 {len(gb['events'])}",
        f"hold 중 최대 접선력 {max(gb['hold_max_tangential_N']):.2f} N (≤ μ·N_th = 50 N)",
        f"안 A 전 값: {case.before_label} (출처는 S2_gifs.json v12.before_source)",
    ]
    text_block(fig, x0, 712, lines, size=8.2)
    text_block(fig, x0, 805, [
        "3D: CAD 메시 실제 크기. 바닥은 실제 경사, 다리는 접면 신장으로 고정(정지).",
        "다리 색 화살표 = 법선력(1 m = 100 kN), 보라 화살표 = 부싱 면내력(1 m = 5 kN, 법선 대비 "
        "×20).",
        f"출처: 07_results/S2a/{run.name}/(record.npz, result.json), verify_S2a_L1.json v12,",
        f"reference.json slope_V12/<case>/{PLAN_A_EXPECTED_KEY}."], size=7.6,
        colour=INK_SECONDARY)
    arrows_n = [scene.arrow(LEG_COLORS[leg]) for leg in LEG_ORDER]
    arrows_t = [scene.arrow(EVENT_COLOR, lw=1.8, head=(5, 3)) for _ in LEG_ORDER]
    labels = [scene.label(LEG_COLORS[leg], size=7.8, ha="center", va="top",
                          fontweight="bold") for leg in LEG_ORDER]
    # downhill direction on the floor
    n = case.normal
    down = -np.array([n[0], n[1], 0.0])
    down = down - (down @ n) * n
    down /= np.linalg.norm(down)
    base = np.array([-3.4, -2.7, 0.0])
    base[2] = floor_polygon(case.floor_point, n)[1](base[0], base[1])
    tip = base + 1.4 * down
    a = scene.arrow(INK_PRIMARY, lw=1.6)
    set_arrow(a, base, tip)
    sb = scr(base)[0]
    scene.ax.text(sb[0], sb[1] - 0.25, f"내리막 방향\n(경사 {np.degrees(np.arccos(n[2])):.2f}°)",
                  fontsize=7.5, color=INK_PRIMARY, ha="center", va="top", zorder=7,
                  bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    return {"fig": fig, "scene": scene, "cursor": cursor, "header": header, "status": status,
            "note": note, "banner": banner, "arrows_n": arrows_n, "arrows_t": arrows_t,
            "labels": labels}


def update_v12(case: V12Case, pieces, i):
    run = case.run
    n = case.normal
    release = case.verify["ground_bushing"]["hold_release_t_s"]
    for k, leg in enumerate(LEG_ORDER):
        c = case.contact[i, k]
        N = run.a["F_contact_n"][i, k]
        set_arrow(pieces["arrows_n"][k], c - n * max(N, 0) * ARROW_N_M_PER_N, c, N > 1.0)
        T = case.T[i, k]
        set_arrow(pieces["arrows_t"][k], c, c + T * ARROW_T_M_PER_N,
                  np.linalg.norm(T) * ARROW_T_M_PER_N > 0.02)
        tail = scr(c - n * max(N, 0) * ARROW_N_M_PER_N)[0]
        pieces["labels"][k].set_position((tail[0], tail[1] - 0.1))
        held = run.t[i] < release[k]
        pieces["labels"][k].set_text(f"{leg} N {N / 1e3:.1f} kN\n|T| {np.linalg.norm(T) / 1e3:.2f}"
                                     " kN" + ("\nhold 중" if held else ""))
    pieces["cursor"].update(run.t[i], i)


def render_v12(bank, args, summary):
    verify = read_json(VERIFY_A)
    reference = read_json(REFERENCE_JSON)
    vertical_tol_N = v12_vertical_tol_N(verify)
    cases = [load_v12(name, label, verify, reference, args.before_dir)
             for name, label in V12_CASES]
    box = (V12_BOX[2], V12_BOX[3])
    params = cases[0].run.params
    pts_items = bank.items(params, cases[0].s_motor)
    floor_pts = [floor_polygon(c.floor_point, c.normal)[0] for c in cases]
    limits = scene_limits_for(pts_items, [(cases[0].run.pos[-1], cases[0].run.rot[-1])], box,
                              extra_world=floor_pts
                              + [c.contact[-1] - 1.4 * c.normal for c in cases],
                              margin=(0.2, 0.2))
    frames, durations, plan_out = [], [], {}
    representative = None
    for n_case, case in enumerate(cases):
        run = case.run
        items = bank.items(run.params, case.s_motor)
        below, above = plane_split(items, run.pos[-1], run.rot[-1], case.floor_point, case.normal)
        t0 = time.perf_counter()
        image = render_scene(below, above, limits, box, floor=(case.floor_point, case.normal))
        print(f"  v12 {run.name}: mesh {time.perf_counter() - t0:.1f} s", flush=True)
        pieces = v12_figure(case, limits, image, vertical_tol_N)
        pieces["header"].set_text(
            f"S2a V12 경사 바닥 정적 [{n_case + 1}/3] · 바닥 {case.label} · 오거 상단 · L1 · "
            f"Δt {s1.dt_text(case.run.result['dt_s'])} · 중력 램프 "
            f"{case.run.result['ramp_s']:g} s + 정착 {case.run.result['settle_after_ramp_s']:g} s "
            "(시간축 로그)")
        release_ms = np.array(case.verify["ground_bushing"]["hold_release_t_s"]) * 1e3
        pieces["note"].set_text(
            "다리 신장 = 구가 경사면에 정확히 닿는 길이(고정). 시작: 무중력·간극 0 → 중력 램프. "
            f"처음 {release_ms.min():.0f}~{release_ms.max():.0f} ms는 hold(부싱 고정점 유지, "
            f"법선력 N ≤ N_th {TOUCH_THRESHOLD_N:g} N 동안).")
        plan = v12_plan(case)
        for j, (t_frame, banner) in enumerate(plan):
            i = run.index(t_frame)
            update_v12(case, pieces, i)
            set_banner(pieces["banner"], banner)
            total = run.a["F_contact_n"][i].sum()
            pieces["status"].set_text(
                f"t = {run.t[i]:7.3f} s   ΣN = {total / 1e3:7.2f} kN   "
                "자세 변화 roll "
                f"{np.degrees(roll_pitch_from_quat(run.a['body_quat_wxyz'][i])[0]) * 1e3:+.2f}"
                " · pitch "
                f"{np.degrees(roll_pitch_from_quat(run.a['body_quat_wxyz'][i])[1]) * 1e3:+.2f}"
                " [1e-3 °] (수평 기체 = 0)")
            frames.append(s1.figure_to_image(pieces["fig"]))
            last = j == len(plan) - 1
            durations.append(500 if j == 0 else 1300 if last else 1000 if banner else
                             110 if t_frame < 3.0 else 260)
            if last and run.name == "v12_rollm2_pitch1.5":
                representative = frames[-1]
        plan_out[run.name] = [round(float(t), 4) for t, _ in plan]
        plt.close(pieces["fig"])
    s1.save_atomic(OUT["v12_frame"], representative.save)
    summary["v12_gif"] = write_gif(frames, durations, OUT["v12"])
    summary["v12"] = {
        "frame_times_s": plan_out,
        "before_source": {c.run.name: c.before_source for c in cases},
        "before_minus_reference_vertical_N": {c.run.name: c.before_N.round(2).tolist()
                                              for c in cases},
        "after_minus_reference_vertical_N": {c.run.name: c.after_N.round(2).tolist()
                                             for c in cases},
        "checks": {c.run.name: c.checks for c in cases},
        "frame_png": rel(OUT["v12_frame"]),
    }
    return cases


def v12_caption_values(verify: dict, reference: dict, names=None) -> dict:
    """V12 caption numbers from verify_S2a_L1.json and reference.json (no literals).

    names: V12 cases (verify v12 keys), default V12_CASES.
    """
    names = [n for n, _ in V12_CASES] if names is None else list(names)
    vc = [verify["v12"][n] for n in names]
    expected = [plan_a_expected(reference, v) for v in vc]
    after = np.array([vertical_minus_reference(v["window"], v["reference"]) for v in vc])
    horizontal = [np.asarray(v["window"]["reaction_world_mean_N"], float)[:, :2]
                  - np.asarray(v["reference"]["reaction_world_N"], float)[:, :2] for v in vc]
    elastic = [np.asarray(v["window"]["bushing_disp_mean_m"], float)
               / (np.asarray(e["expected_bushing_in_plane_displacement_mm"], float) * 1e-3) - 1
               for v, e in zip(vc, expected, strict=True)]
    gb = [v["ground_bushing"] for v in vc]
    lever = np.concatenate([np.abs(np.asarray(e[PLAN_A_REV12_KEY][PLAN_A_LEVER_KEY], float))
                            for e in expected])
    diag = [v12_diag_vertical(verify["v12_plan_a_diagnosis"][n]) for n in names]
    return {
        "tol_N": v12_vertical_tol_N(verify),
        "horizontal_tol_N": float(min(np.min(np.asarray(r["tol"], float)) for r in table_rows(
            verify, "V12", "horizontal reaction", names))),
        "diag_max_N": max(abs_max(d["deviation"]) for d in diag),
        "diag_tol_N": max(float(d["tol"]) for d in diag),
        "spread_max_N": float(np.ptp(after, axis=0).max()),
        "horizontal_max_N": max(abs_max(h) for h in horizontal),
        "elastic_max_pct": max(abs_max(e) for e in elastic) * 100,
        "lever_min_N": float(lever.min()),
        "lever_max_N": float(lever.max()),
        "slip_max_m": max(abs_max(g["slip_total_m"]) for g in gb),
        "yield_steps": int(sum(sum(g["yield_steps"]) for g in gb)),
        "events": int(sum(len(g["events"]) for g in gb)),
        "hold_release_ms": [min(min(g["hold_release_t_s"]) for g in gb) * 1e3,
                            max(max(g["hold_release_t_s"]) for g in gb) * 1e3],
        "hold_max_tangential_N": max(abs_max(g["hold_max_tangential_N"]) for g in gb),
        "pitch_deg": [v["window"]["pitch_mean_deg"] for v in vc],
        "roll_deg": [v["window"]["roll_mean_deg"] for v in vc],
    }


def range_text(values, fmt: str) -> str:
    """One number if all values print the same with ``fmt``, else "min~max"."""
    texts = {format(v, fmt) for v in values}
    if len(texts) == 1:
        return texts.pop()
    return f"{format(min(values), fmt)}~{format(max(values), fmt)}"


def slip_yield_text(cv: dict, with_events: bool) -> str:
    """ "미끄럼·항복(·사건) 0" only when all are zero, else the values."""
    zero = cv["slip_max_m"] == 0 and cv["yield_steps"] == 0 and (
        not with_events or cv["events"] == 0)
    if zero:
        return "미끄럼·항복·사건 0" if with_events else "미끄럼·항복 0"
    text = f"미끄럼 최대 {cv['slip_max_m']:.2e} m, 항복 {cv['yield_steps']} 스텝"
    return text + (f", 사건 {cv['events']}" if with_events else "")


def render_v12_summary(cases, summary, verify):
    cv = v12_caption_values(verify, read_json(REFERENCE_JSON), [c.run.name for c in cases])
    tol = cv["tol_N"]
    W, H = 1400, 820
    fig = new_figure(W, H)
    fig.text(8 / W, 1 - 10 / H, "S2a V12 경사 바닥: 다리별 정착 수직력 Chrono - 기준 [N] · 부싱 "
                                "작용점 "
             "구 접촉점(안 A 전) → 볼 중심(안 A 후)", fontsize=13, fontweight="bold", va="top",
             color=INK_PRIMARY)
    fig.text(8 / W, 1 - 38 / H, "안 A 전 차 = P-δ + 구 지렛대(부싱이 볼 아래 r = 0.06 m에 걸려 "
             "다리마다 r·T 모멘트). 안 A 후에는 P-δ(자중 정착 회전의 무게중심 이동)만 남고,\n"
             f"Chrono는 rev13 독립 예측과 다리별 ≤ {cv['diag_max_N']:.2f} N, "
             f"세 경사 사이 다리별 차 ≤ {cv['spread_max_N']:.1f} N. "
             f"모두 허용 ±{tol:.0f} N(1 % W/4) 안.", fontsize=9, va="top", color=INK_SECONDARY)
    xs = np.arange(4)
    width = 0.2
    for j, case in enumerate(cases):
        ax = axes_box(fig, 70 + j * 445, 100, 400, 430, W, H)
        s1.style_axes(ax, title=f"바닥 {case.label}", ylabel="N" if j == 0 else None)
        lever = case.lever_N
        pd_ = case.p_delta_N
        ax.axhspan(-tol, tol, color=BAND_COLOR, alpha=0.35, lw=0, zorder=0)
        ax.bar(xs - 1.5 * width, case.before_N, width, color=BEFORE_COLOR, hatch="///",
               edgecolor="white", label=case.before_label)
        ax.bar(xs - 0.5 * width, case.after_N, width,
               color=[LEG_COLORS[leg] for leg in LEG_ORDER], label="안 A 후 Chrono")
        ax.bar(xs + 0.5 * width, pd_, width, color="none", edgecolor=ACCENT, lw=1.2,
               label="예측 P-δ (볼 중심, 독립 비선형)")
        ax.bar(xs + 1.5 * width, lever, width, color="none", edgecolor=LIN_COLOR, lw=1.2,
               hatch="..", label="예측 구 지렛대 몫 (접촉점 - 볼)")
        for x, v in zip(xs - 1.5 * width, case.before_N, strict=True):
            ax.text(x, v + (8 if v >= 0 else -8), f"{v:+.0f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=7, color=INK_SECONDARY)
        for x, v in zip(xs - 0.5 * width, case.after_N, strict=True):
            ax.text(x, v + (8 if v >= 0 else -8), f"{v:+.1f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=7, color=INK_PRIMARY)
        ax.axhline(0, color=INK_PRIMARY, lw=0.7)
        ax.set_ylim(-340, 340)
        leg_ticks(ax)
        ax.text(0.02, 0.02, f"음영 = 허용 ±{tol:.0f} N (축 밖까지)", transform=ax.transAxes,
                fontsize=7.4, color=INK_SECONDARY)
        if j == 0:
            ax.legend(fontsize=7.4, loc="upper right", frameon=True, framealpha=0.92)
    # residual panel: verify v12_plan_a_diagnosis / <case> / D[0] (vertical) deviation
    diag_tol = cv["diag_tol_N"]
    ax = axes_box(fig, 70, 590, 700, 170, W, H)
    s1.style_axes(ax, title="안 A 후 Chrono - 독립 비선형 예측(rev13, 현재 YAML) [N]", ylabel="N")
    for j, case in enumerate(cases):
        ax.bar(xs + (j - 1) * 0.25, case.diag_vertical_deviation_N, 0.23,
               color=["#24324f", "#5f7fb3", "#a9bfe0"][j], label=case.label)
    ax.axhspan(-diag_tol, diag_tol, color=BAND_COLOR, alpha=0.4, lw=0, zorder=0)
    ax.axhline(0, color=INK_PRIMARY, lw=0.7)
    ax.set_ylim(-1.2 * diag_tol, 1.2 * diag_tol)
    leg_ticks(ax)
    ax.legend(fontsize=7.6, ncol=3, loc="upper right", frameon=False)
    ax.text(0.01, 0.03, f"음영 = 진단 허용 ±{diag_tol:g} N (verify v12_plan_a_diagnosis)",
            transform=ax.transAxes, fontsize=7.4, color=INK_SECONDARY)
    verdict = verify.get("verdict_by_check", {}).get("V12")
    labels = sorted({c.before_label for c in cases})
    lines = ["독립 확인: reference.json slope_V12/<case>/",
             f"    {PLAN_A_EXPECTED_KEY} (현재 YAML)",
             f"· 안 A 후 Chrono - 기대(P-δ만) ≤ {cv['diag_max_N']:.2f} N (V13 양자 2.5 N 안)",
             f"· 구 지렛대 예측 몫 {cv['lever_min_N']:.0f}~{cv['lever_max_N']:.0f} N이 "
             "Chrono에 없음",
             f"· 수평력 차 ≤ {cv['horizontal_max_N']:.1f} N (허용 {cv['horizontal_tol_N']:.0f} N), "
             f"탄성 변위 차 ≤ {cv['elastic_max_pct']:.2f} %, {slip_yield_text(cv, False)}",
             ("판정: V12 " + (pass_word(verdict) if verdict is not None else "미기록")
              + " (dynamics_model.md 5.5)"),
             "안 A 전 값: " + " / ".join(labels)]
    text_block(fig, 820, 600, lines, size=8.6, width=W, height=H)
    fig.text(820 / W, 1 - 790 / H, "\n".join(sorted({c.before_source for c in cases})),
             fontsize=6.8, va="top", color=INK_SECONDARY, wrap=True)
    image = s1.figure_to_image(fig)
    plt.close(fig)
    s1.save_atomic(OUT["v12png"], image.save)
    summary["v12_summary_png"] = rel(OUT["v12png"])


# =============================================================================================
# S2b V11 stroke (legs in the air)
# =============================================================================================

V11_BOX = (8, 96, 560, 796)


def render_layer_set(bank, params, pos, rot, limits, size, floor_z):
    """Static layers for leg motion as 2D shifts: background (floor), body, per leg rod and
    barrel (legs drawn above the body, far legs first, as render_leg_extension)."""
    s_zero = np.zeros(4)
    all_items = bank.items(params, s_zero)
    background = render_scene([], [], limits, size, floor=((0, 0, floor_z), (0, 0, 1.0)))
    body = [it for it in all_items if it[5] == "body"]
    layers = [("body", None, render_scene(*plane_split(body, pos, rot, (0, 0, floor_z),
                                                       (0, 0, 1.0)), limits, size))]
    toward = VIEWS["oblique"][2]
    depth = {leg.name: float(np.array(leg.pad_bottom_center_retracted_m) @ toward)
             for leg in params.legs}
    for leg in sorted(LEG_ORDER, key=lambda n: depth[n]):
        for kind in ("rod", "barrel"):
            group = [it for it in all_items if it[5] == kind and it[6] == leg]
            layers.append((kind, leg, render_scene(*plane_split(group, pos, rot, (0, 0, floor_z),
                                                                (0, 0, 1.0)), limits, size)))
    return background, layers


def compose_layers(background, layers, shifts_px):
    frame = background.copy()
    for kind, leg, layer in layers:
        if kind == "rod":
            dx, dy = shifts_px[leg]
            moved = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            moved.paste(layer, (dx, dy))
            frame = Image.alpha_composite(frame, moved)
        else:
            frame = Image.alpha_composite(frame, layer)
    return frame


def render_v11(bank, summary):
    run = load_run(RES_B, "v11")
    verify = read_json(VERIFY_B)
    params = run.params
    a = run.a
    pos, rot = run.pos[0], run.rot[0]
    fixed = float(np.abs(run.pos - pos).max())
    box = (V11_BOX[2], V11_BOX[3])
    floor_z = params.ground.crawler_bottom_z_m
    items0 = bank.items(params, np.zeros(4))
    items1 = bank.items(params, np.full(4, params.actuator.stroke_m))
    limits = scene_limits_for(items0 + items1, [(pos, rot)], box,
                              extra_world=[s1.ground_polygon(floor_z)], margin=(0.2, 0.2))
    t0 = time.perf_counter()
    background, layers = render_layer_set(bank, params, pos, rot, limits, box, floor_z)
    print(f"  v11 layers {time.perf_counter() - t0:.1f} s", flush=True)
    scale = box[0] / (limits[0][1] - limits[0][0])
    direction_screen = scr(rot @ extension_direction(params))[0]
    rod_w = verify["v0_motor_sign_and_ramp"]["rod_weight_N"][0]
    m_rod = rod_w / 9.80665
    a_ramp = params.actuator.max_speed_m_s / verify["meta"]["assumptions"]["command_ramp_s"]
    caption = actuator_caption_values(params)
    fig = new_figure()
    scene = Scene(fig, V11_BOX, limits, background)
    header, status, note = header_texts(fig)
    banner = banner_text(fig, x=290, y=122)
    cursor = s1.Cursor()
    t = run.t
    s_mm = a["s_motor"] * 1e3
    u_mm = a["u_applied"] * 1e3
    x0, w, gx = 640, 340, 55
    styles = {"FL": "-", "FR": (0, (5, 3)), "RL": (0, (1, 1.5)), "RR": "-"}
    ax = axes_box(fig, x0, 112, 2 * w + gx, 160)
    s1.style_axes(ax, title=f"모터 위치 = 신장 s [mm] (0 ~ {caption.stroke_mm:.0f} mm, "
                  "끝 넘는 명령 포함)", xlabel="t [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, s_mm[:, k], color=LEG_COLORS[leg], lw=1.4 if leg != "RL" else 1.8,
                ls=styles[leg], label=leg)
        cursor.add_dot(ax, t, s_mm[:, k], LEG_COLORS[leg])
    ax.axhline(caption.stroke_mm, color=LIN_COLOR, lw=0.8, ls=(0, (4, 2)))
    ax.axhline(0, color=LIN_COLOR, lw=0.8, ls=(0, (4, 2)))
    ax.set_xlim(0, t[-1])
    ax.set_ylim(-40, 740)
    ax.legend(fontsize=7.4, ncol=4, loc="center right", frameon=True, framealpha=0.9)
    cursor.add_axes(ax)
    ax = axes_box(fig, x0, 320, 2 * w + gx, 150)
    s1.style_axes(ax, title=f"적용 속도 u [mm/s] (v_max = {caption.v_max_mm_s:.3f} mm/s, "
                  f"명령은 ±1000 / ±{caption.v_max_mm_s:.1f} / ±{2 * caption.v_max_mm_s:.1f} mm/s)",
                  xlabel="t [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, u_mm[:, k], color=LEG_COLORS[leg], lw=1.3, ls=styles[leg])
        cursor.add_dot(ax, t, u_mm[:, k], LEG_COLORS[leg])
    vmax = params.actuator.max_speed_m_s * 1e3
    for v in (vmax, -vmax):
        ax.axhline(v, color=ACCENT, lw=0.8, ls=(0, (4, 2)))
    ax.set_xlim(0, t[-1])
    ax.set_ylim(-28, 28)
    cursor.add_axes(ax)
    # ramp zooms
    t_end_stroke = _stroke_time(verify["v11"]["stroke_times_s"], "FL 0->")
    end_zoom_title = f"끝 {caption.stroke_mm:.0f} mm 도달: 같은 가속 한계로 제동"
    zooms = ((0.0, 0.3, "출발 0~0.3 s: 램프 0.1 s"),
             (t_end_stroke - 0.2, t_end_stroke + 0.1, end_zoom_title))
    for j, (za, zb, title) in enumerate(zooms):
        ax = axes_box(fig, x0 + j * (w + gx), 520, w, 135)
        s1.style_axes(ax, title=title + " [mm/s]", xlabel="t [s]")
        m = (t >= za) & (t <= zb)
        ax.plot(t[m], u_mm[m, 0], "o-", ms=2.5, lw=1.2, color=LEG_COLORS["FL"], label="FL (기록 10 "
                                                                                      "ms)")
        if j == 0:
            tt = np.linspace(0, 0.3, 300)
            ax.plot(tt, np.minimum(tt / 0.1, 1) * vmax, color=INK_PRIMARY, lw=0.8,
                    ls=(0, (2, 2)), label="이상 램프 a = v_max/0.1 s")
        ax.set_xlim(za, zb)
        ax.set_ylim(-2, 25)
        ax.legend(fontsize=7, loc="center right" if j else "lower right", frameon=False)
    ax = axes_box(fig, x0, 708, 2 * w + gx, 110)
    s1.style_axes(ax, title="관성 반력 = 실린더 힘 + 로드 무게 [N] (램프 중 ±m_rod·a = 전방 "
                  f"±{caption.ramp_force_front_N:.2f} N / 후방 ±{caption.ramp_force_rear_N:.2f} N, "
                  "그 밖 0)", xlabel="t [s]")
    dev = a["F_cyl"] + rod_w
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(t, dev[:, k], color=LEG_COLORS[leg], lw=1.0, ls=styles[leg])
    for force_N in (caption.ramp_force_front_N, caption.ramp_force_rear_N):
        for v in (force_N, -force_N):
            ax.axhline(v, color=ACCENT, lw=0.8, ls=(0, (4, 2)))
    ax.set_xlim(0, t[-1])
    ax.set_ylim(-32, 32)
    cursor.add_axes(ax)
    labels = [scene.label(LEG_COLORS[leg], size=8.2, ha="center", va="top", fontweight="bold")
              for leg in LEG_ORDER]
    header.set_text("S2b V11 공중 다리 신장·수축 · 상부체 고정(원점 z 0.839 m) · L1 위치 모터 + "
                    f"속도 한계 + 명령 램프 {caption.ramp_s:g} s · Δt "
                    f"{s1.dt_text(run.result['dt_s'])} · "
                    f"{caption.v11_end_s:g} s")
    note.set_text("3D: CAD 메시 실제 크기, 로드·패드를 기록된 모터 위치만큼 다리 축으로 옮겨 그림"
                  "(층 합성, 화면 이동 1 px 단위). 바닥과 접촉 없음.")
    pads_body = np.array([np.array(leg.pad_bottom_center_retracted_m) for leg in params.legs])
    stroke_t = verify["v11"]["stroke_times_s"]
    times = list(np.arange(0.0, caption.v11_end_s + 1e-3, 1.0))
    half_s = round(caption.v11_half_s, 1)
    stroke_label = f"{caption.stroke_mm:.0f}"
    stroke_banner = (f"0 → {stroke_label} mm 정지-정지 {t_end_stroke:.5f} s "
                     f"(= {stroke_label}/v_max + 램프 {caption.ramp_s:g} s "
                     f"= {caption.full_stroke_time_s:.3f} s)")
    banners = {half_s: f"{half_s:g} s: 명령 반전 (FL·FR·RL 수축, RR 신장 시작)",
               round(t_end_stroke, 1): stroke_banner}
    times = sorted(set([round(x, 1) for x in times] + list(banners)))
    frames, durations = [], []
    for j, t_frame in enumerate(times):
        i = run.index(t_frame)
        shifts = {}
        for k, leg in enumerate(LEG_ORDER):
            d = direction_screen * a["s_motor"][i, k] * scale
            shifts[leg] = (int(round(d[0])), int(round(-d[1])))
        image = compose_layers(background, layers, shifts)
        scene.set_image(image)
        for k, leg in enumerate(LEG_ORDER):
            p = rot @ (pads_body[k] + a["s_motor"][i, k] * extension_direction(params)) + pos
            sp = scr(p)[0]
            labels[k].set_position((sp[0], sp[1] - 0.12))
            labels[k].set_text(f"{leg} {s_mm[i, k]:5.1f} mm\n{u_mm[i, k]:+5.2f} mm/s")
        cursor.update(t[i], i)
        banner_now = banners.get(round(t_frame, 1))
        set_banner(banner, banner_now)
        status.set_text(f"t = {t[i]:5.1f} s   (재생 약 5배속, 1 s/프레임)   FL·FR·RL 명령 "
                        f"{a['u_cmd'][i, 0] * 1e3:+.1f} / {a['u_cmd'][i, 1] * 1e3:+.1f} / "
                        f"{a['u_cmd'][i, 2] * 1e3:+.1f} mm/s, "
                        f"RR {a['u_cmd'][i, 3] * 1e3:+.1f} mm/s")
        frames.append(s1.figure_to_image(fig))
        durations.append(800 if j == 0 else 1800 if j == len(times) - 1 else 1300 if banner_now
                         else 170)
    plt.close(fig)
    summary["v11_gif"] = write_gif(frames, durations, OUT["v11"])
    summary["v11"] = {"body_fixed_max_dev_m": fixed, "rod_mass_kg": m_rod,
                      "ramp_accel_m_s2": a_ramp, "stroke_times_s": stroke_t,
                      "inertial_reaction_max_abs_N": float(np.abs(dev).max()),
                      "screen_scale_px_per_m": scale}


def render_ramp_png(summary):
    verify = read_json(VERIFY_B)
    run = load_run(RES_B, "air_short")
    spikes = {s["name"]: s for s in verify["ramp_spikes"]}
    rod_w = verify["v0_motor_sign_and_ramp"]["rod_weight_N"][0]
    caption = actuator_caption_values(run.params)
    vmax = run.params.actuator.max_speed_m_s
    W, H = 1400, 700
    fig = new_figure(W, H)
    fig.text(8 / W, 1 - 10 / H, "S2b 명령 램프 효과 · 공중에 매달린 로드(전방 "
             f"{caption.rod_mass_front_kg:.2f} kg / 후방 {caption.rod_mass_rear_kg:.2f} kg)에 "
             "+v_max 명령을 줄 때의 관성 반력 (최대 |실린더 힘 + 로드 무게|)",
             fontsize=13, fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(8 / W, 1 - 38 / H, "램프 없음(계단 속도): 한 스텝에 0 → v_max → 반력 m·v_max/Δt, "
             "Δt를 줄이면 "
             f"10배로 커진다(물리량이 아니라 수치 충격). 램프 {caption.ramp_s:g} s: m·a = 전방 "
             f"{caption.ramp_force_front_N:.2f} N / 후방 {caption.ramp_force_rear_N:.2f} N, "
             "Δt와 무관.",
             fontsize=9, va="top", color=INK_SECONDARY)
    ax = axes_box(fig, 80, 90, 640, 520, W, H)
    s1.style_axes(ax, title="최대 관성 반력 [N] (로그 축, 네 다리 중 최대 = 전방)", ylabel="N")
    names = [("ramp0_dt1e-04", "램프 없음\nΔt 1e-4 s"), ("ramp0_dt1e-05", "램프 없음\nΔt 1e-5 s"),
             ("ramp0.1_dt1e-04", "램프 0.1 s\nΔt 1e-4 s"), ("ramp0.1_dt1e-05", "램프 0.1 s\nΔt "
                                                                             "1e-5 s")]
    values = [max(spikes[n]["max_force_dev_N"]) for n, _ in names]
    # expected_N is per leg since the REXOME35 YAML (one value before); the bar is the max leg
    expected = [float(np.max(spikes[n]["expected_N"])) for n, _ in names]
    colours = [BEFORE_COLOR, BEFORE_COLOR, LEG_COLORS["FL"], LEG_COLORS["FL"]]
    xs = np.arange(4)
    ax.bar(xs, values, 0.55, color=colours)
    ax.plot(xs, expected, "_", ms=40, mew=2.2, color=ACCENT)
    for x, v in zip(xs, values, strict=True):
        ax.text(x, v * 1.25, f"{v:,.1f} N" if v < 1e3 else f"{v / 1e3:,.1f} kN", ha="center",
                fontsize=9.5, color=INK_PRIMARY, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(5, 1e6)
    plain_log_formatter(ax)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(s1._short_number))
    ax.set_xticks(xs, [n for _, n in names])
    ax.axhline(rod_w, color=LIN_COLOR, lw=0.9, ls=(0, (4, 2)))
    ax.text(3.45, rod_w * 1.1, f"로드 무게 {rod_w:.0f} N", ha="right", fontsize=8, color=LIN_COLOR)
    ax.legend(handles=[Line2D([], [], color=ACCENT, lw=2.2,
                              label="예측 (m·v_max/Δt 또는 m·a)")],
              fontsize=8.4, loc="upper right", frameon=False)
    # speed profile of the V0 sign test (air_short record)
    ax = axes_box(fig, 800, 90, 570, 250, W, H)
    s1.style_axes(ax, title="V0 부호 시험 (air_short 기록, 10 ms): 적용 속도 [mm/s]",
                  xlabel="t [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(run.t, run.a["u_applied"][:, k] * 1e3, color=LEG_COLORS[leg],
                lw=1.2 + 0.4 * (k == 0))
    ax.axhline(vmax * 1e3, color=ACCENT, lw=0.8, ls=(0, (4, 2)))
    ax.set_ylim(-2, 26)
    ax = axes_box(fig, 800, 390, 570, 220, W, H)
    s1.style_axes(ax, title="같은 기록: 패드 아래 이동 = 모터 이동 [mm]", xlabel="t [s]")
    pad0 = None
    zs = []
    for i in range(len(run.t)):
        c = pad_sphere_centre_body_m(run.params, 0, run.a["s_motor"][i, 0])
        zs.append((run.rot[i] @ c + run.pos[i])[2])
    zs = np.array(zs)
    pad0 = zs[0]
    ax.plot(run.t, (run.a["s_motor"][:, 0] - run.a["s_motor"][0, 0]) * 1e3, color=LEG_COLORS["FL"],
            lw=1.6, label="FL 모터 이동 Δs")
    ax.plot(run.t, -(zs - pad0) * 1e3, color=INK_PRIMARY, lw=1.0, ls=(0, (3, 2)),
            label="FL 패드 하강 -Δz")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    v0 = verify["v0_motor_sign_and_ramp"]
    fig.text(800 / W, 1 - 640 / H, f"V0: 패드 Δz = {v0['pad_dz_m'][0] * 1e3:.4f} mm = -모터 이동, "
             f"램프 기대 이동 {v0['expected_ds_ramp_m'] * 1e3:.4f} mm (차 = 이산 램프 v_max·Δt/2). "
             "출처: verify_S2b_L1.json ramp_spikes, v0_motor_sign_and_ramp; "
             "07_results/S2b/air_short.",
             fontsize=7.8, va="top", color=INK_SECONDARY, wrap=True)
    image = s1.figure_to_image(fig)
    plt.close(fig)
    s1.save_atomic(OUT["ramp"], image.save)
    summary["ramp_png"] = {"png": rel(OUT["ramp"]),
                           "values_N": dict(zip([n for n, _ in names], values, strict=True))}


# =============================================================================================
# S2b crawler settle (3 auger levels)
# =============================================================================================

CR_BOX = (8, 96, 520, 600)


@dataclass
class CrawlerCase:
    run: Run
    level: str
    centres_body: np.ndarray
    radius: float
    roller: np.ndarray
    forces: np.ndarray  # (n, 24) k_n max(delta, 0)
    check: dict
    result: dict
    weight_N: float  # result.json analytic_exact.weight_N (= s2b_crawler_check <level> W_N)
    kn_N_m: float  # result.json analytic_exact.kn_per_sphere_float32_N_m (crawler_kn_N_m)
    settle_s: float  # meta.json run.scenario.settings.settle_s (window start)
    still_s: float  # meta.json run.scenario.settings.still_s (window length)
    active_by_kind: dict  # {"roller": n, "end_shoe": n} from result.json sphere force means
    shoe_spans: list  # crawler_shoe_spans(layout): rear / front x span and gap range


def crawler_key(obj: dict, path: tuple, source: str):
    """``obj[path[0]][path[1]]...``; stop with the file and key path when a key is missing."""
    node = obj
    for k in path:
        if not isinstance(node, dict) or k not in node:
            raise SystemExit(f"{source}: missing key {'.'.join(map(str, path))!r} "
                             f"(at {k!r}); rerun the producer of this file")
        node = node[k]
    return node


def crawler_kn_N_m(result: dict, check_all: dict, case: str) -> float:
    """Per-sphere crawler k_n [N/m] used to rebuild the sphere forces from the Record.

    Source: the run's result.json ``analytic_exact.kn_per_sphere_float32_N_m`` (the float32
    value Chrono's SMC material actually holds); it must equal s2b_crawler_check.json
    ``meta.kn_per_sphere_float32_N_m`` (independent dynamics-dev check) exactly.
    """
    kn = float(crawler_key(result, ("analytic_exact", "kn_per_sphere_float32_N_m"),
                           f"{case}/result.json"))
    kn_check = float(crawler_key(check_all, ("meta", "kn_per_sphere_float32_N_m"),
                                 CRAWLER_CHECK.name))
    if kn != kn_check:
        raise SystemExit(f"{case}: result.json kn_per_sphere_float32_N_m {kn!r} != "
                         f"s2b_crawler_check meta {kn_check!r}")
    return kn


def crawler_window_s(run_dir: Path) -> tuple[float, float]:
    """(settle_s, still_s) of an S2b crawler run.

    Source: the Record's meta.json ``run.scenario.settings.settle_s`` / ``still_s`` (run_S2b
    writes them; its still window is t >= settle_s, length still_s).
    """
    meta = read_json(run_dir / "meta.json")
    src = f"{run_dir.name}/meta.json"
    settle = float(crawler_key(meta, ("run", "scenario", "settings", "settle_s"), src))
    still = float(crawler_key(meta, ("run", "scenario", "settings", "still_s"), src))
    return settle, still


def crawler_active_by_kind(result: dict, labels: list, case: str) -> dict:
    """Active sphere count per kind in the still window.

    Source: the run's result.json ``sphere_force_chrono_mean_N`` (> 0 = active) with
    ``sphere_labels`` (``<side>-<kind>-<k>``), which must match the YAML layout labels; the
    total must equal result.json ``window.active_min`` = ``window.active_max``.
    """
    src = f"{case}/result.json"
    mean = np.asarray(crawler_key(result, ("sphere_force_chrono_mean_N",), src), float)
    names = list(crawler_key(result, ("sphere_labels",), src))
    if names != labels:
        raise SystemExit(f"{case}: result.json sphere_labels differ from the YAML layout labels")
    out = {"roller": 0, "end_shoe": 0}
    for name, f in zip(names, mean, strict=True):
        kind = name.split("-")[1]
        if kind not in out:
            raise SystemExit(f"{case}: unknown sphere kind in label {name!r}")
        out[kind] += int(f > 0.0)
    lo = int(crawler_key(result, ("window", "active_min"), src))
    hi = int(crawler_key(result, ("window", "active_max"), src))
    if not lo == hi == sum(out.values()):
        raise SystemExit(f"{case}: active spheres by kind {out} != window active_min/max "
                         f"{lo}/{hi}")
    return out


def crawler_shoe_spans(layout) -> list:
    """Rear / front end-shoe x spans and gap ranges from the YAML layout.

    Source: YAML ``contact.crawler.sphere_layout`` (``roller_x_m``, ``end_shoe_x_m``,
    ``end_shoe_gap_m`` via scenarios.crawler_settle.crawler_layout). Span inner edge = midpoint
    to the nearest roller, outer edge = outermost shoe + half the shoe pitch.
    """
    x = layout.xy_m[:, 0]
    left = layout.xy_m[:, 1] > 0.0
    roller = layout.is_roller
    rx = np.sort(x[roller & left])
    spans = []
    for end, sel in (("rear", ~roller & left & (x < 0.0)), ("front", ~roller & left & (x > 0.0))):
        sx = np.sort(x[sel])
        gaps = layout.gap_m[sel]
        if sx.size == 0:
            raise SystemExit(f"crawler layout: no {end} end shoes")
        half_pitch = 0.5 * float(np.diff(sx).mean()) if sx.size > 1 else layout.sphere_radius_m
        if end == "rear":
            span = (float(sx[0]) - half_pitch, 0.5 * float(sx[-1] + rx[0]))
        else:
            span = (0.5 * float(sx[0] + rx[-1]), float(sx[-1]) + half_pitch)
        spans.append({"end": end, "x_m": span, "gap_mm": (float(gaps.min()) * 1e3,
                                                          float(gaps.max()) * 1e3)})
    return spans


def crawler_weight_N(result: dict, check_level: dict, case: str) -> float:
    """Weight W carried by the crawler spheres in an S2b crawler run.

    Source: the run's own result.json ``analytic_exact.weight_N`` (run_S2b: composite mass of
    superstructure + 4 leg moving parts of the run's YAML x g, scenarios.crawler_settle), checked
    against the independent dynamics-dev check s2b_crawler_check.json ``<level>.W_N``.
    """
    w = float(result["analytic_exact"]["weight_N"])
    w_check = float(check_level["W_N"])
    if abs(w - w_check) > CRAWLER_W_REL_TOL * abs(w_check):
        raise SystemExit(f"{case}: result.json weight_N {w!r} != s2b_crawler_check W_N "
                         f"{w_check!r} (stale check or run; rerun the one made with the old YAML)")
    return w


def load_crawler(level, check_all) -> CrawlerCase:
    run = load_run(RES_B, f"crawler_{level}", level)
    layout = crawler_layout(run.params)
    floor = run.params.ground.crawler_bottom_z_m
    centres = layout.centres_body_m(floor)
    world_z = np.einsum("nij,kj->nki", run.rot, centres)[..., 2] + run.pos[:, 2:3]
    delta = layout.sphere_radius_m - (world_z - floor)
    res = run.result
    kn = crawler_kn_N_m(res, check_all, run.name)
    forces = kn * np.maximum(delta, 0.0)
    settle_s, still_s = crawler_window_s(RES_B / f"crawler_{level}")
    if abs(run.t[-1] - (settle_s + still_s)) > 1e-6:
        raise SystemExit(f"{run.name}: Record ends at {run.t[-1]!r} s, meta settle + still = "
                         f"{settle_s + still_s!r} s")
    window = run.t >= settle_s - 1e-9  # same window rule as run_S2b (t >= SETTLE_S)
    mean = forces[window].mean(axis=0)
    chrono = np.array(res["sphere_force_chrono_mean_N"])
    check = {"sphere_force_window_mean_minus_result_max_abs_N": float(np.abs(mean - chrono).max()),
             "sum_spring_minus_F_crawler_z_max_abs_N": float(np.abs(
                 forces.sum(axis=1) - run.a["F_crawler"][:, 2]).max()),
             "active_spheres_window": int((mean > 0).sum())}
    weight = crawler_weight_N(res, check_all[level], run.name)
    check["weight_N"] = weight
    active = crawler_active_by_kind(res, layout.labels(), run.name)
    check["active_by_kind_window"] = active
    return CrawlerCase(run, level, centres, layout.sphere_radius_m,
                       np.array([k == "roller" for k in layout.kind]), forces, check, res, weight,
                       kn, settle_s, still_s, active,
                       crawler_shoe_spans(layout))


def crawler_figure(case: CrawlerCase, limits, image, check_all):
    fig = new_figure()
    scene = Scene(fig, CR_BOX, limits, image)
    header, status, note = header_texts(fig)
    run = case.run
    cursor = s1.Cursor()
    t = run.t
    chk = check_all[case.level]
    # footprint (top view)
    ax = axes_box(fig, 30, 712, 500, 170)
    s1.style_axes(ax, title="접지면 평면도 (x 전방, y 좌측): 원 면적 ∝ 구 힘, 빈 원 = 틈 열림")
    ax.set_aspect("equal")
    ax.set_xlim(-1.9, 1.9)
    ax.set_ylim(-1.55, 1.55)
    for yc in (1.045, -1.045):
        ax.add_patch(Rectangle((-1.42, yc - 0.3), 2.84, 0.6, fc="#ecebe7", ec="#b9b8b3", lw=0.6,
                               zorder=0))
    xy = case.centres_body[:, :2]
    dots = ax.scatter(xy[:, 0], xy[:, 1], s=np.zeros(len(xy)), c=ACCENT, edgecolors="white",
                      linewidths=0.5, zorder=3)
    ax.scatter(xy[:, 0], xy[:, 1], s=14, facecolors="none", edgecolors=INK_SECONDARY,
               linewidths=0.6, zorder=2)
    com = np.array(run.params.superstructure.mass_properties.com_m)
    ax.plot(com[0], com[1], "X", ms=8, color=COM_COLOR, mec="white", mew=0.6, zorder=4)
    ax.text(com[0] + 0.08, com[1] + 0.12, "무게중심(상부체)", fontsize=7, color=COM_COLOR)
    ax.tick_params(labelsize=6.5)
    # time series
    x0, w, gx = 590, 375, 45
    ax1 = axes_box(fig, x0, 112, w, 170)
    s1.style_axes(ax1, title="pitch [°] (+ = 앞 숙임)", xlabel="t [s]")
    pitch = np.degrees(roll_pitch_from_quat(run.a["body_quat_wxyz"])[1])
    exact = chk["exact_pdelta"]["pitch_deg"]
    lin = chk["linear_no_pdelta"]["pitch_deg"]
    ax1.plot(t, pitch, color=INK_PRIMARY, lw=1.2)
    ax1.axhline(exact, color=ACCENT, lw=1.2, ls=(0, (1, 1.5)))
    ax1.axhline(lin, color=LIN_COLOR, lw=1.2, ls=(0, (4, 2)))
    ax1.set_ylim(lin - 0.0012, exact + 0.0045)
    ax1.set_xlim(0, t[-1])
    ax1.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.4f"))
    ax1.text(0.99, (exact - ax1.get_ylim()[0]) / np.ptp(ax1.get_ylim()) + 0.05,
             f"독립 정확 해(P-δ 포함) {exact:.6f}°", transform=ax1.transAxes, ha="right",
             fontsize=7.4, color=ACCENT)
    ax1.text(0.99, (lin - ax1.get_ylim()[0]) / np.ptp(ax1.get_ylim()) + 0.05,
             f"선형(P-δ 없음) {lin:.6f}°", transform=ax1.transAxes, ha="right", fontsize=7.4,
             color=LIN_COLOR)
    cursor.add_axes(ax1)
    cursor.add_dot(ax1, t, pitch, ACCENT)
    ax2 = axes_box(fig, x0 + w + gx, 112, w, 170)
    s1.style_axes(ax2, title="원점 높이 u_z [mm] (영 자세 대비)", xlabel="t [s]")
    uz = run.pos[:, 2] * 1e3
    ax2.plot(t, uz, color=INK_PRIMARY, lw=1.2)
    ax2.axhline(chk["exact_pdelta"]["u_z_mm"], color=ACCENT, lw=1.2, ls=(0, (1, 1.5)))
    ax2.axhline(chk["linear_no_pdelta"]["u_z_mm"], color=LIN_COLOR, lw=1.2, ls=(0, (4, 2)))
    # limits from the data and the two reference lines (a fixed range went stale with the YAML)
    uz_refs = (chk["exact_pdelta"]["u_z_mm"], chk["linear_no_pdelta"]["u_z_mm"])
    uz_lo, uz_hi = min(*uz_refs, uz.min()), max(*uz_refs, uz.max())
    uz_pad = 0.15 * max(uz_hi - uz_lo, 1e-3)
    ax2.set_ylim(uz_lo - uz_pad, uz_hi + uz_pad)
    ax2.set_xlim(0, t[-1])
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.4f"))
    cursor.add_axes(ax2)
    cursor.add_dot(ax2, t, uz, ACCENT)
    ax3 = axes_box(fig, x0, 335, 2 * w + gx, 200)
    s1.style_axes(ax3, title="구 접촉력 [kN] 대 구 x 위치 (● 좌 궤도, ■ 우 궤도, "
                  "선 = 독립 정확 해)", xlabel="구 중심 x (기체) [m]")
    exact_f = np.array(case.result["analytic_exact"]["sphere_force_N"]) / 1e3
    order = np.argsort(xy[:, 0])
    for side, sel in (("좌", xy[:, 1] > 0), ("우", xy[:, 1] < 0)):
        idx = np.flatnonzero(sel)
        idx = idx[np.argsort(xy[idx, 0])]
        ax3.plot(xy[idx, 0], exact_f[idx], color=ACCENT if side == "좌" else "#5f7fb3", lw=0.9,
                 ls=(0, (1, 1.5)))
    left = xy[:, 1] > 0
    pts_l, = ax3.plot([], [], "o", ms=6, color=ACCENT, mec="white", mew=0.6)
    pts_r, = ax3.plot([], [], "s", ms=5, color="#5f7fb3", mec="white", mew=0.6)
    # x: end-shoe spans from the YAML layout; y: Record sphere forces (all frames) and the
    # independent exact line, with headroom for the span labels (no fixed range)
    spans = case.shoe_spans
    x_lo = min(spans[0]["x_m"][0], xy[:, 0].min()) - 0.03
    x_hi = max(spans[-1]["x_m"][1], xy[:, 0].max()) + 0.03
    ax3.set_xlim(x_lo, x_hi)
    f_hi = max(float(case.forces.max()) / 1e3, float(exact_f.max()))
    f_lo = min(float(case.forces.min()) / 1e3, float(exact_f.min()), 0.0)
    y_hi = f_hi / 0.85
    ax3.set_ylim(f_lo - 0.05 * y_hi, y_hi)
    for span in spans:
        ax3.axvspan(*span["x_m"], color="#f4f3ef", lw=0, zorder=0)
        g_lo, g_hi = span["gap_mm"]
        ax3.text(0.5 * sum(span["x_m"]), 0.93, f"끝 슈 (틈 {g_lo:.1f}~{g_hi:.1f} mm)",
                 transform=ax3.get_xaxis_transform(), ha="center", fontsize=7.4,
                 color=INK_SECONDARY)
    del order
    ax4 = axes_box(fig, x0, 590, w, 130)
    s1.style_axes(ax4, title=f"ΣF 크롤러 - W [N] (W = {case.weight_N / 1e3:.2f} kN)",
                  xlabel="t [s]")
    fz = run.a["F_crawler"][:, 2] - case.weight_N
    ax4.plot(t, fz, color=INK_PRIMARY, lw=0.8)
    ax4.set_xlim(0, t[-1])
    # symmetric about the reference line ΣF = W (0), from the Record data (no fixed range)
    fz_lim = 1.15 * max(float(np.abs(fz).max()), 1.0)
    ax4.set_ylim(-fz_lim, fz_lim)
    cursor.add_axes(ax4)
    ax5 = axes_box(fig, x0 + w + gx, 590, w, 130)
    s1.style_axes(ax5, title="pitch 변동 (평균 대비) [1e-6 °]", xlabel="t [s]")
    ax5.plot(t, (pitch - pitch.mean()) * 1e6, color=INK_PRIMARY, lw=0.7)
    ax5.set_xlim(0, t[-1])
    cursor.add_axes(ax5)
    mc = {m["mode"]: m for m in case.result["modes_chrono"]}
    # window from meta.json settings; active counts from result.json (crawler_active_by_kind)
    win_txt = f"{case.settle_s:g}~{case.settle_s + case.still_s:g} s"
    act = case.active_by_kind
    lines = [
        f"정착(창 {win_txt}): u_z {case.result['window']['u_z_mm']:.5f} mm, pitch "
        f"{case.result['window']['pitch_deg']:.6f}°, 활성 구 {sum(act.values())}개"
        f" (롤러 {act['roller']} + 끝 슈 {act['end_shoe']})",
        f"Chrono - 독립 정확 해: u_z {chk['chrono_minus_exact']['u_z_mm'] * 1e3:+.2f} μm, pitch "
        f"{chk['chrono_minus_exact']['pitch_deg'] * 1e6:+.2f}e-6°   P-δ 증폭 "
        f"{chk['exact_minus_linear']['pitch_rel'] * 100:+.3f} % (예측 "
        f"{(chk['pdelta_amplification_predicted'] - 1) * 100:+.3f} %)",
        f"크롤러 위 모드 f_n (Chrono 자유 진동 맞춤, 기록 밖 20 s 창): pitch "
        f"{mc['pitch']['f_undamped_Hz']:.4f} / roll {mc['roll']['f_undamped_Hz']:.4f} / heave "
        f"{mc['heave']['f_undamped_Hz']:.4f} Hz",
    ]
    text_block(fig, x0, 760, lines, size=8.3)
    text_block(fig, x0, 830, [
        "구 접촉력 = k_n·max(δ, 0), δ = 기록 자세에서 계산한 구-바닥 겹침 (k_n "
        f"{case.kn_N_m / 1e6:.8g}e6 N/m float32). "
        "창 평균 - result.json 구 힘 ≤ "
        f"{case.check['sphere_force_window_mean_minus_result_max_abs_N']:.2f} N.",
        f"출처: 07_results/S2b/crawler_{case.level}/, verify_S2b_L1.json crawler, "
        "s2b_crawler_check.json."],
        size=7.6, colour=INK_SECONDARY)
    bars = []
    for k in range(len(case.centres_body)):
        arrow = scene.arrow(ACCENT if case.centres_body[k, 1] < 0 else "#e7a0b4", lw=1.6,
                            head=(4, 2.5))
        bars.append(arrow)
    return {"fig": fig, "scene": scene, "cursor": cursor, "header": header, "status": status,
            "note": note, "dots": dots, "pts": (pts_l, pts_r), "left": left, "bars": bars}


def update_crawler(case: CrawlerCase, pieces, i):
    run = case.run
    f = case.forces[i]
    pieces["dots"].set_sizes(f / 1e3 * 7.0)
    xy = case.centres_body[:, :2]
    left = pieces["left"]
    pieces["pts"][0].set_data(xy[left, 0], f[left] / 1e3)
    pieces["pts"][1].set_data(xy[~left, 0], f[~left] / 1e3)
    world = case.centres_body @ run.rot[i].T + run.pos[i]
    for k, arrow in enumerate(pieces["bars"]):
        bottom = world[k] - np.array([0, 0, case.radius])
        set_arrow(arrow, bottom - np.array([0, 0, f[k] * ARROW_N_M_PER_N * 2]), bottom, f[k] > 1.0)
    pieces["cursor"].update(run.t[i], i)


def crawler_compare_frame(cases, check_all):
    fig = new_figure()
    fig.text(8 / FRAME_W, 1 - 10 / FRAME_H, "S2b 크롤러 위 정착 · 오거 3단계 비교 "
             "(다리 0 mm, 강체 평지, 크롤러 D안 구 24개)", fontsize=13, fontweight="bold", va="top",
             color=INK_PRIMARY)
    fig.text(8 / FRAME_W, 1 - 38 / FRAME_H, "pitch는 Chrono와 독립 정확 해(P-δ 포함)가 "
             "6자리까지 같고, 선형 기준해(P-δ 없음)보다 무게중심 높이에 비례해 크다"
             "(상단 +2.47 %). roll 진동수 차 +0.31 %는 기울어진 자세의 관성 축 차이"
             "(Chrono가 맞음).",
             fontsize=9, va="top", color=INK_SECONDARY)
    ax = axes_box(fig, 60, 100, 600, 380)
    s1.style_axes(ax, title="정착 pitch [°]", ylabel="°")
    xs = np.arange(3)
    width = 0.25
    lin = [check_all[c.level]["linear_no_pdelta"]["pitch_deg"] for c in cases]
    exact = [check_all[c.level]["exact_pdelta"]["pitch_deg"] for c in cases]
    chrono = [c.result["window"]["pitch_deg"] for c in cases]
    ax.bar(xs - width, lin, width, color=BEFORE_COLOR, label="선형 기준해 (P-δ 없음)")
    ax.bar(xs, exact, width, color="none", edgecolor=ACCENT, lw=1.4, label="독립 정확 해 (P-δ)")
    ax.bar(xs + width, chrono, width, color="#24324f", label="Chrono (창 평균)")
    for x, v, e in zip(xs, chrono, exact, strict=True):
        ax.text(x + width, v + 0.0003, f"{v:.6f}", ha="center", fontsize=7.6, color=INK_PRIMARY)
        ax.text(x, e + 0.0012, f"+{(e / lin[0] - 1) * 100:.2f} %", ha="center", fontsize=8,
                color=ACCENT)
    ax.set_ylim(0.165, 0.177)
    ax.set_xticks(xs, [LEVEL_LABEL[c.level] for c in cases])
    ax.legend(fontsize=8, loc="upper right", frameon=True, framealpha=0.9)
    ax = axes_box(fig, 740, 100, 620, 380)
    s1.style_axes(ax, title="크롤러 위 모드 f_n [Hz]: Chrono 맞춤 / 독립(세계 축 관성) / 독립(몸체 "
                            "축)",
                  ylabel="Hz")
    names = ("pitch", "roll", "heave")
    tones = ("#24324f", "#5f7fb3", "#a9bfe0")
    for j, case in enumerate(cases):
        chk = check_all[case.level]["modes"]
        world = chk["world_inertia_geo_centre (Chrono model)"]["f_undamped_Hz"]
        body = chk["body_inertia_geo_floor (reference.json convention)"]["f_undamped_Hz"]
        fit = [check_all[case.level]["modes"]["chrono_fit"][n]["f_n_Hz"] for n in names]
        for m in range(3):
            x = m + (j - 1) * 0.27
            ax.bar(x, fit[m], 0.08, color=tones[j],
                   label=LEVEL_LABEL[case.level] if m == 0 else None)
            ax.plot([x - 0.06, x + 0.06], [world[m]] * 2, color=ACCENT, lw=1.6)
            ax.plot([x - 0.06, x + 0.06], [body[m]] * 2, color=INK_PRIMARY, lw=1.0, ls=(0, (2, 1)))
    ax.set_xticks(range(3), names)
    ax.set_ylim(0, 10)
    handles, labels = ax.get_legend_handles_labels()
    handles += [Line2D([], [], color=ACCENT, lw=1.6), Line2D([], [], color=INK_PRIMARY, lw=1.0,
                                                              ls=(0, (2, 1)))]
    labels += ["독립, 세계 축 관성(Chrono와 같은 모델)", "독립, 몸체 축 관성(기준 규약)"]
    ax.legend(handles, labels, fontsize=7.6, loc="upper left", frameon=True, framealpha=0.9)
    cells = []
    for case in cases:
        chk = check_all[case.level]
        fit = chk["modes"]["chrono_fit"]
        world = chk["modes"]["world_inertia_geo_centre (Chrono model)"]["f_undamped_Hz"]
        cells.append([LEVEL_LABEL[case.level],
                      f"{case.result['window']['u_z_mm']:.5f}",
                      f"{chk['chrono_minus_exact']['u_z_mm'] * 1e3:+.2f}",
                      f"{chk['chrono_minus_exact']['pitch_deg'] * 1e6:+.2f}",
                      f"{chk['exact_minus_linear']['pitch_rel'] * 100:+.3f}",
                      " / ".join(f"{fit[n]['f_n_Hz']:.4f}" for n in names),
                      " / ".join(f"{(fit[n]['f_n_Hz'] / world[m] - 1) * 100:+.3f}"
                                 for m, n in enumerate(names)),
                      f"{case.check['sphere_force_window_mean_minus_result_max_abs_N']:.2f}"])
    tax = axes_box(fig, 40, 560, 1320, 200)
    tax.set_axis_off()
    table = tax.table(cellText=cells, colLabels=["단계", "u_z [mm]", "Chrono-정확 u_z [μm]",
                                                 "Chrono-정확 pitch [1e-6 °]", "P-δ 증폭 [%]",
                                                 "f_n pitch/roll/heave [Hz]", "Chrono/독립-1 [%]",
                                                 "구 힘 재계산 차 [N]"],
                      loc="upper center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8.6)
    table.scale(1.0, 1.5)
    for (_, _), cell in table.get_celld().items():
        cell.set_edgecolor("#dcdbd6")
        cell.set_linewidth(0.5)
    text_block(fig, 40, 800, ["판정(dynamics_model.md 5.6): 크롤러 정착 자세·모드 통과(참고 항목, "
                              "V4에서 판정). "
                              "V13 정지 창 자세 변동 ≤ 2.0e-5°, 크롤러 수직력 합 변동 ≤ 72 N(< "
                              "95.6 N).",
                              "출처: s2b_crawler_check.json (독립 확인, dynamics-dev), "
                              "verify_S2b_L1.json, "
                              "07_results/S2b/crawler_<단계>/result.json."], size=8.4)
    image = s1.figure_to_image(fig)
    plt.close(fig)
    return image


def render_crawler(bank, summary):
    check_all = read_json(CRAWLER_CHECK)
    cases = [load_crawler(level, check_all) for level in ("top", "middle", "bottom")]
    box = (CR_BOX[2], CR_BOX[3])
    params = cases[0].run.params
    floor_z = params.ground.crawler_bottom_z_m
    items_all = [bank.items(c.run.params, np.zeros(4)) for c in cases]
    limits = scene_limits_for(items_all[0] + items_all[2], [(cases[0].run.pos[-1],
                                                             cases[0].run.rot[-1])], box,
                              extra_world=[s1.ground_polygon(floor_z)], margin=(0.15, 0.15))
    frames, durations = [], []
    for n, case in enumerate(cases):
        run = case.run
        below, above = plane_split(items_all[n], run.pos[-1], run.rot[-1], (0, 0, floor_z),
                                   (0, 0, 1.0))
        t0 = time.perf_counter()
        image = render_scene(below, above, limits, box, floor=((0, 0, floor_z), (0, 0, 1.0)))
        print(f"  crawler {case.level}: mesh {time.perf_counter() - t0:.1f} s", flush=True)
        pieces = crawler_figure(case, limits, image, check_all)
        pieces["header"].set_text(
            f"S2b 크롤러 위 정착 [{n + 1}/4] · 오거 {LEVEL_LABEL[case.level]} · 다리 0 mm(패드 약 "
            "0.34 m "
            f"위) · 크롤러 D안 구 24개(SMC Hooke) · L1 · Δt {s1.dt_text(case.run.result['dt_s'])} "
            "· 15 s")
        pieces["note"].set_text(
            "시작 = 독립 정확 정착 자세(P-δ 포함) → 15 s 동안 거의 움직이지 않음(자세 변동 ≤ "
            "2e-5°). "
            "3D 화살표 = 구 접촉력(1 m = 50 kN, 진한 = 앞쪽 우 궤도).")
        times = np.linspace(0, run.t[-1], 9)
        for j, t_frame in enumerate(times):
            i = run.index(t_frame)
            update_crawler(case, pieces, i)
            pieces["status"].set_text(
                f"t = {run.t[i]:5.2f} s   pitch "
                f"{np.degrees(roll_pitch_from_quat(run.a['body_quat_wxyz'][i])[1]):.6f}°"
                f"   u_z {run.pos[i, 2] * 1e3:.5f} mm   ΣF 크롤러 "
                f"{run.a['F_crawler'][i, 2] / 1e3:.3f} kN"
                f"   활성 구 {(case.forces[i] > 0).sum()}")
            frames.append(s1.figure_to_image(pieces["fig"]))
            durations.append(1100 if j == 0 else 1500 if j == len(times) - 1 else 330)
        plt.close(pieces["fig"])
    compare = crawler_compare_frame(cases, check_all)
    frames.append(compare)
    durations.append(5000)
    summary["crawler_gif"] = write_gif(frames, durations, OUT["crawler"])
    summary["crawler"] = {c.level: c.check for c in cases}


# =============================================================================================
# S2b contact events (FL)
# =============================================================================================

EV_BOX = (8, 96, 560, 796)
EV_K = 100.0  # inset vertical exaggeration


@dataclass
class EventCase:
    name: str
    run: Run
    run2: Run
    verify: dict
    gap_mm: np.ndarray
    gap2_mm: np.ndarray
    slip_mm: np.ndarray
    contact_pt: np.ndarray
    checks: dict


def pad_gap_mm(run: Run):
    """FL pad bottom (sphere centre - r, level body) above the floor [mm]; < 0 = penetration."""
    r = swivel_radius(run.params)[0]
    floor = run.params.ground.crawler_bottom_z_m
    out = np.empty(len(run.t))
    pts = np.empty((len(run.t), 3))
    for i in range(len(run.t)):
        c = (run.rot[i] @ pad_sphere_centre_body_m(run.params, 0, run.a["s_motor"][i, 0])
             + run.pos[i])
        out[i] = (c[2] - r - floor) * 1e3
        pts[i] = c - np.array([0, 0, r])
    return out, pts


def load_event(name, verify) -> EventCase:
    run = load_run(RES_B, f"event_{name}_dt1e-04")
    run2 = load_run(RES_B, f"event_{name}_dt1e-05")
    gap, pts = pad_gap_mm(run)
    gap2, _ = pad_gap_mm(run2)
    anchor = run.a["bushing_anchor"][:, 0, :]
    # Coulomb slip = anchor movement within a contact episode (a new anchor is placed at every
    # touch, so the jump between episodes is body drift, not slip); summed over the episodes.
    slip = np.full(len(run.t), np.nan)
    offset = np.zeros(2)
    created, previous = None, None
    for i in range(len(run.t)):
        if np.isnan(anchor[i]).any():
            if created is not None:
                offset = offset + (previous[:2] - created[:2])
            created = None
            continue
        if created is None:
            created = anchor[i].copy()
        previous = anchor[i]
        slip[i] = np.linalg.norm(offset + anchor[i, :2] - created[:2]) * 1e3
    total = offset + (previous[:2] - created[:2] if created is not None else 0.0)
    result_slip = np.array(run.result["slip_total_m"][0][:2])
    checks = {"min_gap_mm": float(gap.min()), "slip_end_mm": float(np.linalg.norm(total) * 1e3),
              "slip_result_mm": float(np.linalg.norm(result_slip) * 1e3),
              "slip_vector_minus_result_mm": float(np.abs(total - result_slip).max() * 1e3)}
    return EventCase(name, run, run2, verify["events"][f"event_{name}_dt1e-04"], gap, gap2, slip,
                     pts, checks)


def events_figure(case: EventCase, limits, image, verify_b):
    fig = new_figure()
    scene = Scene(fig, EV_BOX, limits, image)
    header, status, note = header_texts(fig)
    banner = banner_text(fig, x=290, y=868)
    run, run2 = case.run, case.run2
    cursor = s1.Cursor()
    t = run.t
    ev1 = run.result["events"]
    x0, w, gx = 640, 345, 45

    def event_lines(ax):
        for te, _, _kind in ev1:
            ax.axvline(te, color=EVENT_COLOR, lw=0.8, alpha=0.7)
        cursor.add_axes(ax)

    ax = axes_box(fig, x0, 112, 2 * w + gx, 150)
    s1.style_axes(ax, title="FL 패드 바닥 높이 (바닥 위 +, 침투 -) [mm] — 실선 Δt 1e-4, "
                  "점선 Δt 1e-5", xlabel="t [s]")
    ax.plot(t, case.gap_mm, color=LEG_COLORS["FL"], lw=1.4)
    ax.plot(run2.t, case.gap2_mm, color=DT2_COLOR, lw=0.8, ls=(0, (3, 2)))
    ax.axhline(0, color=INK_PRIMARY, lw=0.8)
    ax.set_xlim(0, t[-1])
    event_lines(ax)
    cursor.add_dot(ax, t, case.gap_mm, LEG_COLORS["FL"])
    ax = axes_box(fig, x0, 310, 2 * w + gx, 170)
    s1.style_axes(ax, title="FL 패드 법선력 N [kN] (보라 선 = R15 부싱 사건, "
                            f"N_th {TOUCH_THRESHOLD_N:g} N, t_lift {LIFT_TIME_S * 1e3:g} ms)",
                  xlabel="t [s]")
    ax.plot(t, run.a["F_contact_n"][:, 0] / 1e3, color=LEG_COLORS["FL"], lw=1.4, label="Δt 1e-4 s")
    ax.plot(run2.t, run2.a["F_contact_n"][:, 0] / 1e3, color=DT2_COLOR, lw=0.8, ls=(0, (3, 2)),
            label="Δt 1e-5 s")
    ax.set_xlim(0, t[-1])
    ax.legend(fontsize=7.6, loc="upper right", frameon=False, ncol=2)
    event_lines(ax)
    cursor.add_dot(ax, t, run.a["F_contact_n"][:, 0] / 1e3, LEG_COLORS["FL"])
    ax = axes_box(fig, x0, 528, w, 150)
    s1.style_axes(ax, title="FL 부싱 접선력 |T| [kN]", xlabel="t [s]")
    tmag = np.linalg.norm(run.a["F_contact_t"][:, 0], axis=1) / 1e3
    ax.plot(t, tmag, color=EVENT_COLOR, lw=1.1)
    ax.set_xlim(0, t[-1])
    event_lines(ax)
    cursor.add_dot(ax, t, tmag, EVENT_COLOR)
    ax = axes_box(fig, x0 + w + gx, 528, w, 150)
    s1.style_axes(ax, title="부싱 고정점 누적 이동 (미끄럼) [mm]", xlabel="t [s]")
    ax.plot(t, case.slip_mm, color=INK_PRIMARY, lw=1.2)
    ax.set_xlim(0, t[-1])
    event_lines(ax)
    cursor.add_dot(ax, t, np.nan_to_num(case.slip_mm, nan=0.0), INK_PRIMARY)
    pair = verify_b["event_dt_pairs"][f"{case.name}"]
    kinds = {1: "생성(접지)", 2: "소멸(부상)"}
    cells = []
    for e1, e2, d in zip(pair["events_dt1e-4"], pair["events_dt1e-5"], pair["time_diff_s"],
                         strict=True):
        cells.append([kinds[e1[2]], f"{e1[0]:.4f}", f"{e2[0]:.5f}", f"{d * 1e3:+.2f}"])
    tax = axes_box(fig, x0, 712, 360, 100)
    tax.set_axis_off()
    table = tax.table(cellText=cells, colLabels=["부싱 사건", "Δt 1e-4 [s]", "Δt 1e-5 [s]",
                                                 "차 [ms] (≤ 1)"],
                      loc="upper center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8.2)
    table.scale(1.0, 1.35)
    for (_, _), cell in table.get_celld().items():
        cell.set_edgecolor("#dcdbd6")
        cell.set_linewidth(0.5)
    lt = [lt_[0] for lt_ in pair["lift_timing"]]
    raw = pair["raw_transitions"]
    lines = [f"소멸 지연 {lt[0]['delay_s'] * 1e3:.2f} / {lt[1]['delay_s'] * 1e3:.2f} ms "
             "(= (n_lift - 1)Δt)",
             f"원시 N>0 전환 {raw[0]} / {raw[1]}건 (사건 3건, chatter 0)",
             f"최대 패드 힘 {case.verify['max_pad_force_N'] / 1e3:.2f} kN",
             f"FL 누적 미끄럼 {case.checks['slip_result_mm']:.2f} mm "
             "(R8: 크롤러 접선 0 → 실기에는 없음)"]
    text_block(fig, x0 + 385, 716, lines, size=8.0)
    text_block(fig, x0, 836, [
        f"출처: 07_results/S2b/event_{case.name}_dt1e-04 · _dt1e-05 (record 1 ms 표본, "
        "result.json),",
        "verify_S2b_L1.json events·event_dt_pairs. 높이 = 볼 중심 - r - 바닥(수평 기체 근사)."],
        size=7.6, colour=INK_SECONDARY)
    # 3D overlays
    arrow_n = scene.arrow(LEG_COLORS["FL"], lw=2.6)
    arrow_t = scene.arrow(EVENT_COLOR, lw=2.0, head=(5, 3))
    label = scene.label(LEG_COLORS["FL"], size=8.5, ha="left", va="top", fontweight="bold")
    badge = scene.label(INK_PRIMARY, size=8.5, ha="left", va="bottom")
    # inset: magnified FL pad and floor (side view x-z)
    iax = axes_box(fig, 22, 128, 230, 220)
    s1.style_axes(iax)
    iax.set_title(f"FL 확대도 (측면, 수직 ×{EV_K:g}, x ×{EV_K:g})", fontsize=8, loc="left", pad=2,
                  color=INK_PRIMARY)
    iax.set_xlim(-0.6, 0.6)
    iax.set_ylim(-0.5, 0.75)
    iax.set_xticks([])
    iax.set_yticks([])
    iax.axhspan(-0.5, 0, color=EARTH_COLOR, alpha=0.2, lw=0)
    iax.axhline(0, color=INK_PRIMARY, lw=0.9)
    pad = Rectangle((-0.2, 0), 0.4, 0.08, fc=LEG_COLORS["FL"], ec="white", lw=0.6, zorder=3)
    iax.add_patch(pad)
    (rod,) = iax.plot([], [], color=LEG_COLORS["FL"], lw=4, zorder=2)
    (anchor,) = iax.plot([], [], "x", ms=8, mew=1.6, color=INK_PRIMARY, zorder=4)
    itext = iax.text(0.03, 0.97, "", transform=iax.transAxes, fontsize=7.6, va="top",
                     color=INK_PRIMARY)
    return {"fig": fig, "scene": scene, "cursor": cursor, "header": header, "status": status,
            "note": note, "banner": banner, "arrow_n": arrow_n, "arrow_t": arrow_t,
            "label": label, "badge": badge, "pad": pad, "rod": rod, "anchor": anchor,
            "itext": itext}


def update_events(case: EventCase, pieces, i):
    run = case.run
    c = case.contact_pt[i]
    N = run.a["F_contact_n"][i, 0]
    set_arrow(pieces["arrow_n"], c - np.array([0, 0, max(N, 0) * ARROW_N_M_PER_N]), c, N > 1.0)
    T = tangential_world(run.a["F_contact_t"][i, 0], np.array([0, 0, 1.0]))[0]
    set_arrow(pieces["arrow_t"], c, c + T * ARROW_T_M_PER_N, np.linalg.norm(T) > 50)
    sc = scr(c - np.array([0, 0, max(N, 0) * ARROW_N_M_PER_N]))[0]
    pieces["label"].set_position((sc[0] + 0.1, sc[1]))
    pieces["label"].set_text(f"FL N {N / 1e3:6.2f} kN\n|T| {np.linalg.norm(T) / 1e3:5.2f} kN")
    active = not np.isnan(run.a["bushing_anchor"][i, 0]).any()
    s0 = scr(c)[0]
    pieces["badge"].set_position((s0[0] + 0.15, s0[1] + 0.35))
    pieces["badge"].set_text("부싱 활성 (지면 고정점 있음)" if active else "부싱 없음 (공중)")
    pieces["badge"].get_bbox_patch().set_facecolor("#e9f5ec" if active else "#f6e9e9")
    gap = case.gap_mm[i] * 1e-3 * EV_K
    pieces["pad"].set_y(gap)
    pieces["rod"].set_data([0, 0], [gap + 0.08, 0.75])
    if active:
        anchor = run.a["bushing_anchor"][i, 0]
        j = i
        while j > 0 and not np.isnan(run.a["bushing_anchor"][j - 1, 0, 0]):
            j -= 1
        dx = (anchor[0] - run.a["bushing_anchor"][j, 0, 0]) * EV_K
        pieces["anchor"].set_data([dx], [0.0])
    else:
        pieces["anchor"].set_data([], [])
    ds_mm = (run.a["s_motor"][i, 0] - run.result["touch_extension_m"]) * 1e3
    pieces["itext"].set_text(f"높이 {case.gap_mm[i]:+.3f} mm\ns - s_touch {ds_mm:+.3f} mm")
    pieces["cursor"].update(run.t[i], i)


def render_events(bank, summary):
    CURRENT_VIEW[0] = "oblique_left"  # FL is on the far side of the default camera
    verify = read_json(VERIFY_B)
    cases = [load_event(name, verify) for name in ("fast_FL", "slow_FL")]
    box = (EV_BOX[2], EV_BOX[3])
    run0 = cases[0].run
    params = run0.params
    floor_z = params.ground.crawler_bottom_z_m
    i_max = int(np.argmax(run0.a["F_contact_n"][:, 0]))
    s_draw = run0.a["s_motor"][i_max]
    items = bank.items(params, s_draw)
    limits = scene_limits_for(items, [(run0.pos[i_max], run0.rot[i_max])], box,
                              extra_world=[s1.ground_polygon(floor_z)], margin=(0.15, 0.15))
    below, above = plane_split(items, run0.pos[i_max], run0.rot[i_max], (0, 0, floor_z),
                               (0, 0, 1.0))
    t0 = time.perf_counter()
    image = render_scene(below, above, limits, box, floor=((0, 0, floor_z), (0, 0, 1.0)))
    print(f"  events mesh {time.perf_counter() - t0:.1f} s", flush=True)
    frames, durations, plans = [], [], {}
    representative = None
    kinds = {1: f"접지 → 부싱 생성 (N > {TOUCH_THRESHOLD_N:g} N)",
             2: f"부상 → 부싱 소멸 (N ≤ 0이 {LIFT_TIME_S * 1e3:g} ms 지속)"}
    for n, case in enumerate(cases):
        run = case.run
        ec = case.run.result["event_case"]
        pieces = events_figure(case, limits, image, verify)
        speed = (f"v_max {run.params.actuator.max_speed_m_s * 1e3:.2f} mm/s"
                 if case.name == "fast_FL" else "1 mm/s")
        pieces["header"].set_text(
            f"S2b 접지 사건 R15 [{n + 1}/2] · FL만 하강 → 접지 → 상승(부상) → 재하강(재접지) · "
            f"{speed} · 시작 간극 {ec['start_gap_m'] * 1e3:.1f} mm · 기체는 크롤러 위(상단) · L1")
        pieces["note"].set_text(
            "3D: CAD 메시 실제 크기(FL 신장은 최대 힘 시각의 값). 화살표 = FL 법선력(1 m = 100 "
            "kN), "
            "보라 = 부싱 접선력(1 m = 5 kN). 패드 움직임은 mm라 왼쪽 위 확대도(× = 부싱 고정점)로 "
            "본다.")
        times = list(np.linspace(0, run.t[-1], 34))
        banners = {}
        for te, _leg, kind in run.result["events"]:
            tb = round(te + 0.002, 4)
            times.append(tb)
            banners[tb] = f"t = {te:.4f} s: FL {kinds[kind]}"
        times = sorted(times)
        for j, t_frame in enumerate(times):
            i = run.index(t_frame)
            update_events(case, pieces, i)
            b = banners.get(round(t_frame, 4))
            set_banner(pieces["banner"], b)
            pieces["status"].set_text(
                f"t = {run.t[i]:6.3f} s / {run.t[-1]:.1f} s   FL 명령 "
                f"{run.a['u_cmd'][i, 0] * 1e3:+.2f} mm/s"
                f"   적용 {run.a['u_applied'][i, 0] * 1e3:+.2f} mm/s   나머지 다리 0 mm(힘 0)")
            frames.append(s1.figure_to_image(pieces["fig"]))
            durations.append(700 if j == 0 else 1500 if j == len(times) - 1 else 1200 if b else 110)
            if b and "소멸" in b and case.name == "fast_FL":
                representative = frames[-1]
        plans[case.name] = {"frames": len(times), "events": run.result["events"],
                            "checks": case.checks}
        plt.close(pieces["fig"])
    s1.save_atomic(OUT["events_frame"], representative.save)
    summary["events_gif"] = write_gif(frames, durations, OUT["events"])
    summary["events"] = plans
    summary["events_frame_png"] = rel(OUT["events_frame"])
    summary["events_view_toward_viewer_body"] = VIEWS["oblique_left"][2].round(4).tolist()
    CURRENT_VIEW[0] = "oblique"


# =============================================================================================
# dashboards
# =============================================================================================


def table_axes(ax, cells, col_labels, col_widths=None, size=8.2, pass_col=None):
    ax.set_axis_off()
    table = ax.table(cellText=cells, colLabels=col_labels, loc="upper center", cellLoc="left",
                     colWidths=col_widths)
    table.auto_set_font_size(False)
    table.set_fontsize(size)
    table.scale(1.0, 1.32)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#dcdbd6")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor("#f1efe9")
            cell.get_text().set_fontweight("bold")
        if pass_col is not None and c == pass_col and r > 0:
            cell.get_text().set_color("#1b7a4a")
            cell.get_text().set_fontweight("bold")
    return table


def v7_bushing_shift_text(verify_reference: dict) -> str:
    """ "부싱 작용점 이동 확인" line: judged modes 1 (v7_roll) and 2 (v7_pitch).

    d  = f_damped / f_ref - 1 (result.json, f_ref = rev-13 reference),
    r5 = f_damped / rev-5 f_damped - 1 (springs at the pad bottom, chrono_test_references
         L1_rigid_motor_lumped_contact / levels / top / f_damped_Hz),
    p  = predicted change rev 13 vs rev 5 (V7_ball_centre_bushing_rev13 / change_vs_rev5 /
         f_undamped_rel), all in %.
    """
    top = verify_reference["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"][
        "top"]
    rev5 = top["f_damped_Hz"]
    predicted = top["V7_ball_centre_bushing_rev13"]["change_vs_rev5 (springs at the pad bottom)"][
        "f_undamped_rel"]
    d, r5, p = [], [], []
    for case in ("v7_roll", "v7_pitch"):
        res = read_json(RES_A / case / "result.json")
        m = res["modes"][res["judged_mode"] - 1]
        k = m["mode"] - 1
        d.append((m["f_damped_Hz"] / m["f_ref_Hz"] - 1) * 100)
        r5.append((m["f_damped_Hz"] / rev5[k] - 1) * 100)
        p.append(predicted[k] * 100)
    return [f"부싱 작용점 이동 확인: 1·2차 f_d가 rev13 기준과 {d[0]:+.3f} / {d[1]:+.3f} %,",
            f"     패드 바닥 스프링 기준(rev5) 대비 {r5[0]:+.2f} / {r5[1]:+.2f} % "
            f"(예측 {p[0]:+.2f} / {p[1]:+.2f} %)."]


def v13_caption_values(verify: dict) -> dict:
    """V13 maxima over every case of the verify table."""
    nan_rows = table_rows(verify, "V13", "no NaN")
    normal_rows = table_rows(verify, "V13", "normal force variation")
    return {
        "any_nan": any(bool(r["value"]) for r in nan_rows),
        "motor_violation_m": max(abs_max(r["value"]) for r in table_rows(
            verify, "V13", "motor constraint violation")),
        "attitude_drift_deg": max(abs_max(r["value"]) for r in table_rows(
            verify, "V13", "attitude drift")),
        "normal_variation_N": max(abs_max(r["value"]) for r in normal_rows),
        "normal_variation_tol_N": float(min(np.min(np.asarray(r["tol"], float))
                                            for r in normal_rows)),
    }


def render_summary_a(summary, before_dir=DEFAULT_BEFORE_DIR):
    verify = read_json(VERIFY_A)
    W, H = 1400, 900
    fig = new_figure(W, H)
    fig.text(8 / W, 1 - 10 / H, "S2a 종합 · L1 지면 부싱 동특성(V7)과 경사 바닥 정역학(V12) · "
             "오거 상단 · "
             f"부싱 작용점 = 볼 중심(안 A) · 판정: {pass_word(verify['all_passed'])} "
             "(dynamics_model.md 5.5)", fontsize=13,
             fontweight="bold", va="top", color=INK_PRIMARY)
    v0 = verify.get("v0", {})
    v0_counts = sorted({c["n_checks"] for c in v0.values()})
    v0_failed = sum(len(c["failed"]) for c in v0.values())
    v0_text = (f"V0 {'/'.join(str(n) for n in v0_counts)}항목×{len(v0)}"
               + (f" (실패 {v0_failed})" if v0_failed else ""))
    dt_judge = judged_v7_dt()
    fig.text(8 / W, 1 - 38 / H, "자동 사전 판정 verify_S2a_L1.json all_passed = "
             f"{verify['all_passed']} · {v0_text} · 판정 실행 Δt "
             + " / ".join(f"{d:g}" for d in dt_judge) + " s(YAML; Δt 연구는 접미사 폴더 3개) · "
             "pychrono 10.0.0, EULER_IMPLICIT_LINEARIZED, SPARSE_LU", fontsize=9, va="top",
             color=INK_SECONDARY)
    v7_ok = verify["verdict_by_check"]["V7"]
    cells = []
    f_diff, z_diff = [], []
    for case in V7_JUDGED_CASES:
        res = read_json(RES_A / case / "result.json")
        m = res["modes"][res["judged_mode"] - 1]
        f_diff.append((m["f_undamped_Hz"] / m["f_ref_Hz"] - 1) * 100)
        z_diff.append((m["zeta_corrected"] / m["zeta_ref"] - 1) * 100)
        cells.append([MODE_NAMES[m["mode"]], f"{m['f_undamped_Hz']:.5f}", f"{m['f_ref_Hz']:.4f}",
                      f"{f_diff[-1]:+.3f} %",
                      f"{m['zeta_corrected']:.5f}", f"{m['zeta_ref']:.5f}",
                      f"{z_diff[-1]:+.2f} %", pass_word(v7_ok)])
    ax = axes_box(fig, 20, 80, 760, 150, W, H)
    table_axes(ax, cells, ["V7 모드", "f_n Chrono [Hz]", "기준 [Hz]", "차 (±3 %)", "ζ 보정",
                           "기준 ζ", "차 (±30 %)", "판정"],
               col_widths=[0.2, 0.12, 0.1, 0.1, 0.1, 0.1, 0.11, 0.07], pass_col=7)
    # eta small multiples
    for j, case in enumerate(("v7_roll", "v7_pitch", "v7_yaw")):
        res = read_json(RES_A / case / "result.json")
        m = res["modes"][res["judged_mode"] - 1]
        ts = np.asarray(res["series"]["t_s"])
        eta = np.asarray(res["series"]["eta_judged"])
        fit = fit_damped_sine(ts, eta, m["f_damped_Hz"])
        ax = axes_box(fig, 60 + j * 250, 270, 215, 150, W, H)
        s1.style_axes(ax, title=f"η {MODE_NAMES[m['mode']]}", xlabel="t [s]")
        ax.plot(ts, eta, color=INK_PRIMARY, lw=0.5)
        env = fit.amplitude * np.exp(-fit.sigma_1_s * (ts - ts[0]))
        ax.plot(ts, fit.offset + env, color=ACCENT, lw=1.1)
        ax.plot(ts, fit.offset - env, color=ACCENT, lw=1.1)
        ax.set_xlim(0, ts[-1])
        ax.tick_params(labelsize=6.5)
    # dt mini
    study = verify["v7_yaw_dt_study"]
    rows, dt_skip = dt_study_rows(study)
    study_ok = rows is not None and all(study["checks"].values())
    ax = axes_box(fig, 840, 90, 530, 330, W, H)
    s1.style_axes(ax, title="Δt 연구: ζ3 (yaw 2 s) 대 Δt — 암시 수치 감쇠 확인",
                  xlabel="Δt [1e-4 s]", ylabel="ζ3")
    if rows is None:
        ax.text(0.5, 0.5, f"Δt 연구 그림 생략:\n{dt_skip}", transform=ax.transAxes, ha="center",
                va="center", fontsize=8.5, color=INK_PRIMARY, wrap=True)
        dt_line = f"Δt 연구: 그림 생략 ({dt_skip})."
    else:
        zeta_ref = study["zeta_ref"]
        dts = np.array([r["dt_s"] for r in rows])
        zf = np.array([r["zeta_fit_raw"] for r in rows])
        xs = np.linspace(0, 1.1 * dts[-1], 20)
        ax.plot(xs * 1e4, zeta_ref + study["slope_predicted_implicit_per_s"] * xs, color=ACCENT,
                lw=1.4, label=f"예측 {zeta_ref:.4f} + r3ω3Δt/2")
        ax.axhline(float(np.mean([r["prediction_ct_scale"] for r in rows])), color=LIN_COLOR,
                   lw=1.2, ls=(0, (5, 3)), label="c_t 배율 가설 (Δt 무관)")
        ax.plot(dts * 1e4, zf, "o", ms=8, color=INK_PRIMARY, mec="white", label="Chrono 식별")
        ax.text(0.97, 0.06, f"기울기 비 {study['slope_ratio_measured_over_implicit']:.4f}, 절편 "
                f"{study['intercept_zeta']:.5f} · A1~A3 {pass_word(study_ok)}",
                transform=ax.transAxes, ha="right", fontsize=8.5, color=INK_PRIMARY)
        ax.set_xlim(0, xs[-1] * 1e4)
        ax.legend(fontsize=7.6, loc="upper left", frameon=False)
        dt_line = ("Δt: ζ3이 Δt에 비례(기울기 비 "
                   f"{study['slope_ratio_measured_over_implicit']:.3f}, "
                   f"증분비 {study['increment_ratio']:.3f}) → 가설 A "
                   f"{'확정' if study_ok else '미확정'}; L1 일반 Δt "
                   + " / ".join(f"{d:g}" for d in dt_judge) + " s(YAML).")
    # V12 bars
    reference = read_json(REFERENCE_JSON)
    vertical_tol = v12_vertical_tol_N(verify)
    params_sha = load_params(s1.PARAMS_PATH[0], level="top").sha256
    befores = {name: v12_before(name, verify["v12"][name], reference, before_dir, params_sha)
               for name, _ in V12_CASES}
    before_labels = sorted({b[2] for b in befores.values()})
    ax = axes_box(fig, 60, 485, 760, 300, W, H)
    s1.style_axes(ax, title=f"V12 수직력 Chrono - 기준 [N] (허용 ±{vertical_tol:.0f} N)\n"
                  "회색 빗금 = " + " / ".join(before_labels)
                  + ", 색 = 안 A 후(볼 중심), ◆ = 독립 P-δ 예측(rev13)", ylabel="N")
    labels = []
    for j, (name, label) in enumerate(V12_CASES):
        v = verify["v12"][name]
        after = vertical_minus_reference(v["window"], v["reference"])
        before = befores[name][0]
        pdv = plan_a_expected(reference, v)[PLAN_A_P_DELTA_KEY]
        base = j * 5
        xs = base + np.arange(4)
        ax.bar(xs - 0.2, before, 0.38, color=BEFORE_COLOR, hatch="///", edgecolor="white")
        ax.bar(xs + 0.2, after, 0.38, color=[LEG_COLORS[leg] for leg in LEG_ORDER])
        ax.plot(xs + 0.2, pdv, "D", ms=4.5, color=ACCENT, mec="white", mew=0.5)
        labels += [(x, f"{leg}") for x, leg in zip(xs, LEG_ORDER, strict=True)]
        ax.text(base + 1.5, 330, label, ha="center", fontsize=8.6, color=INK_PRIMARY)
    ax.set_xticks([x for x, _ in labels], [s for _, s in labels], fontsize=7)
    ax.axhline(0, color=INK_PRIMARY, lw=0.7)
    ax.set_ylim(-320, 360)
    cv = v12_caption_values(verify, reference)
    v13 = v13_caption_values(verify)
    hold0, hold1 = cv["hold_release_ms"]
    lines = [
        f"V7: 판정 3개 모드 f_n 차 ≤ {max(abs(v) for v in f_diff):.3f} %, ζ(보정) 차 ≤ "
        f"{max(abs(v) for v in z_diff):.2f} % (허용 ±3 %, ±30 %).",
        f"     3차 ζ(보정) {verify['v7_diagnosis']['zeta3_corrected']:.5f} (기준 "
        f"{study.get('zeta_ref', math.nan):.4f}) → 부싱 감쇠 입력 c_t/2 재확인.",
        *v7_bushing_shift_text(reference),
        "V12: 수직 차 = P-δ(자중 정착 회전 pitch "
        f"{range_text(cv['pitch_deg'], '.4f')}°·roll {range_text(cv['roll_deg'], '.4f')}°의 "
        "무게중심 이동)만 남음:",
        f"     rev13 독립 비선형과 다리별 ≤ {cv['diag_max_N']:.2f} N, "
        f"구 지렛대 몫(≥ {cv['lever_min_N']:.0f} N) 없음.",
        f"     수평 차 ≤ {cv['horizontal_max_N']:.1f} N, {slip_yield_text(cv, True)}, hold 해제 "
        f"{hold0:.1f}~{hold1:.1f} ms, hold 중 접선력 ≤ {cv['hold_max_tangential_N']:.1f} N.",
        f"V13: {'NaN 있음' if v13['any_nan'] else 'NaN 없음'}, 구속 위반 ≤ "
        f"{v13['motor_violation_m']:.1e} m, 정지 창 자세 변동 ≤ {v13['attitude_drift_deg']:.1e}°,",
        f"     수직력 변동 ≤ {v13['normal_variation_N']:.1f} N "
        f"(허용 {v13['normal_variation_tol_N']:.0f} N).",
        dt_line,
    ]
    text_block(fig, 860, 470, lines, size=8.4, width=W, height=H)
    fig.text(860 / W, 1 - 640 / H, "그림: S2a_v7_free_vibration.gif, S2a_dt_study.png, "
             "S2a_v12_slope.gif, S2a_v12_summary.png\n출처: verify_S2a_L1.json, "
             f"07_results/S2a/*/result.json, reference.json (slope_V12/<case>/\n"
             f"{PLAN_A_EXPECTED_KEY}, chrono_test_references)",
             fontsize=7.8, va="top", color=INK_SECONDARY)
    fig.text(20 / W, 1 - 810 / H, "판정 기준과 해석: 00_docs/01_dynamics/dynamics_model.md 5.3~5.5 "
             "(개정 12~14).\n안 A 전 값: "
             + "\n".join(sorted({b[1] for b in befores.values()})),
             fontsize=7.8, va="top", color=INK_SECONDARY)
    image = s1.figure_to_image(fig)
    plt.close(fig)
    s1.save_atomic(OUT["summary_a"], image.save)
    summary["summary_a_png"] = rel(OUT["summary_a"])


def render_summary_b(summary):
    verify = read_json(VERIFY_B)
    check = read_json(CRAWLER_CHECK)
    W, H = 1400, 900
    fig = new_figure(W, H)
    fig.text(8 / W, 1 - 10 / H, "S2b 종합 · 구동기(V0·V11·명령 램프), 크롤러 접촉(D안), 접지 "
                                "사건(R15) · "
             "L1 · 판정: 통과 (dynamics_model.md 5.6)", fontsize=13, fontweight="bold", va="top",
             color=INK_PRIMARY)
    fig.text(8 / W, 1 - 38 / H, "자동 사전 판정 verify_S2b_L1.json all_passed = "
                                f"{verify['all_passed']} "
             f"({', '.join(k for k, v in verify['passed_by_id'].items() if v)}) · "
             f"Δt {s1.dt_text(read_json(RES_B / 'v11' / 'result.json')['dt_s'])}"
             "(이벤트는 1e-4 / 1e-5 s)",
             fontsize=9, va="top", color=INK_SECONDARY)
    v0 = verify["v0_motor_sign_and_ramp"]
    v11 = verify["v11"]
    spikes = {s["name"]: s for s in verify["ramp_spikes"]}
    pairs = verify["event_dt_pairs"]
    run = load_run(RES_B, "v11")
    caption = actuator_caption_values(run.params)
    stroke_label = f"{caption.stroke_mm:.0f}"
    top = verify["crawler"]["top"]
    cells = [
        ["V0 모터 부호", f"패드 Δz {v0['pad_dz_m'][0] * 1e3:+.4f} mm = -모터 이동", "부호 일치",
         "통과"],
        ["V0 매달린 로드 반력", f"{v0['hanging_force_N'][0]:.4f} N", "-m_rod·g ±1 N", "통과"],
        ["램프 관성 반력", f"{max(spikes['ramp0.1_dt1e-04']['max_force_dev_N']):.4f} N",
         f"m_rod·a 전방 {caption.ramp_force_front_N:.4f} / "
         f"후방 {caption.ramp_force_rear_N:.4f} ±1 N",
         "통과"],
        ["V11 최대 속도", f"{max(v11['max_speed_m_s']) * 1e3:.7f} mm/s", "≤ v_max(1+1e-3)", "통과"],
        [f"V11 정지-정지 0↔{stroke_label} mm",
         f"{_stroke_time(v11['stroke_times_s'], 'FL 0->'):.5f} s",
         f"{stroke_label}/v_max + {caption.ramp_s:g} = {caption.full_stroke_time_s:.3f} ±0.05 s",
         "통과"],
        ["V13 축 구속 위반", f"{v11['max_axial_violation_m']:.1e} m (V11)", "≤ 1e-6 m", "통과"],
        ["크롤러 정착 (상단)", f"pitch {top['chrono_window']['pitch_deg']:.6f}°",
         f"독립 정확 해 {top['analytic_exact']['pitch_deg']:.6f}°", "통과"],
        ["R15 사건 순서 (4실행)", "생성 → 소멸 → 생성, chatter 0", "사건 3건", "통과"],
        ["R15 두 Δt 사건 시각 차",
         "빠름 " + " / ".join(f"{d * 1e3:.2f}" for d in pairs["fast_FL"]["time_diff_s"])
         + ", 느림 " + " / ".join(f"{abs(d) * 1e3:.2f}" for d in pairs["slow_FL"]["time_diff_s"])
         + " ms",
         "≤ 1 ms", "통과"],
        ["R16 스냅숏 왕복", "≤ 8.9e-16 m", "≤ 1e-12 m", "통과"],
    ]
    ax = axes_box(fig, 20, 75, 860, 300, W, H)
    table_axes(ax, cells, ["항목", "값 (Chrono)", "기준·허용", "판정"],
               col_widths=[0.2, 0.37, 0.3, 0.07], size=8.2, pass_col=3)
    # ramp bars
    ax = axes_box(fig, 950, 90, 420, 270, W, H)
    s1.style_axes(ax, title="관성 반력 최대 [N] (로그): 램프 없음 vs 0.1 s")
    names = ["ramp0_dt1e-04", "ramp0_dt1e-05", "ramp0.1_dt1e-04", "ramp0.1_dt1e-05"]
    vals = [max(spikes[n]["max_force_dev_N"]) for n in names]
    ax.bar(range(4), vals, color=[BEFORE_COLOR, BEFORE_COLOR, LEG_COLORS["FL"], LEG_COLORS["FL"]])
    ax.set_yscale("log")
    ax.set_ylim(5, 1e6)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(s1._short_number))
    ax.set_xticks(range(4), ["없음\n1e-4", "없음\n1e-5", "0.1 s\n1e-4", "0.1 s\n1e-5"],
                  fontsize=7.6)
    for x, v in enumerate(vals):
        ax.text(x, v * 1.3, f"{v / 1e3:.1f} kN" if v > 1e3 else f"{v:.1f} N", ha="center",
                fontsize=8, color=INK_PRIMARY)
    # V11 stroke
    ax = axes_box(fig, 60, 430, 400, 190, W, H)
    s1.style_axes(ax, title=f"V11 공중 신장 s [mm] ({caption.v11_end_s:g} s)", xlabel="t [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(run.t, run.a["s_motor"][:, k] * 1e3, color=LEG_COLORS[leg], lw=1.2,
                ls="-" if leg in ("FL", "RR") else (0, (3, 2)), label=leg)
    ax.legend(fontsize=7.2, ncol=4, loc="upper right", frameon=False)
    ax.set_xlim(0, caption.v11_end_s)
    # crawler P-delta
    ax = axes_box(fig, 520, 430, 380, 190, W, H)
    s1.style_axes(ax, title="크롤러 정착 pitch [°]: 선형 / 정확(P-δ) / Chrono")
    for j, level in enumerate(("top", "middle", "bottom")):
        c = check[level]
        ax.bar(j - 0.25, c["linear_no_pdelta"]["pitch_deg"], 0.24, color=BEFORE_COLOR,
               label="선형(P-δ 없음)" if j == 0 else None)
        ax.bar(j, c["exact_pdelta"]["pitch_deg"], 0.24, color="none", edgecolor=ACCENT, lw=1.3,
               label="독립 정확 해" if j == 0 else None)
        ax.bar(j + 0.25, c["chrono_window"]["pitch_deg"], 0.24, color="#24324f",
               label="Chrono" if j == 0 else None)
    ax.legend(fontsize=7.4, ncol=3, loc="upper right", frameon=False)
    ax.set_ylim(0.166, 0.1772)
    ax.set_xticks(range(3), [LEVEL_LABEL[x] for x in ("top", "middle", "bottom")])
    # events
    ev = load_run(RES_B, "event_fast_FL_dt1e-04")
    ev2 = load_run(RES_B, "event_fast_FL_dt1e-05")
    ax = axes_box(fig, 960, 430, 410, 190, W, H)
    s1.style_axes(ax, title="R15 FL 법선력 [kN] (v_max): Δt 1e-4 / 1e-5", xlabel="t [s]")
    ax.plot(ev.t, ev.a["F_contact_n"][:, 0] / 1e3, color=LEG_COLORS["FL"], lw=1.3)
    ax.plot(ev2.t, ev2.a["F_contact_n"][:, 0] / 1e3, color=DT2_COLOR, lw=0.8, ls=(0, (3, 2)))
    for te, _, _kind in ev.result["events"]:
        ax.axvline(te, color=EVENT_COLOR, lw=0.8)
    ax.set_xlim(0, ev.t[-1])
    lines = [
        "판단(dynamics-expert, 5.6절): ① ChFunctionConst → ChFunctionRamp 승인(구동기 훅은 매 스텝 "
        "호출 조건). "
        f"② V11 기준을 stroke/v_max + T_r로 바꿈(당시 680 mm: 30.1 s, 지금 {stroke_label} mm: "
        f"{caption.full_stroke_time_s:.3f} s).",
        "③ 스트로크 끝 제동 = 명령 램프: 조건부 수용(소프트 리밋 > 1.13 mm, 하중 받은 다리의 끝 "
        "도달은 기록·판정 제외).",
        "④ 크롤러 접선 구속 없음(R8): 평지 S3 V4에는 문제없음, 경사 바닥 L1 들어 올림 전에 크롤러 "
        "접선 모델 필요(사용자 결정).",
        "⑤ 크롤러 pitch 차는 P-δ 전부, roll +0.31 %는 관성 축 차(Chrono가 맞음). V4 시각 원점 = "
        "모터 출발 + T_r/2.",
        "크롤러 위 모드(상단) f_n Chrono "
        f"{check['top']['modes']['chrono_fit']['pitch']['f_n_Hz']:.4f} / "
        f"{check['top']['modes']['chrono_fit']['roll']['f_n_Hz']:.4f} / "
        f"{check['top']['modes']['chrono_fit']['heave']['f_n_Hz']:.4f} Hz vs 독립 1.32691 / "
        "3.05532 / 8.73106 Hz.",
    ]
    text_block(fig, 40, 680, lines, size=8.4, width=W, height=H)
    fig.text(40 / W, 1 - 840 / H, "그림: S2b_v11_stroke.gif, S2b_ramp_effect.png, "
                                  "S2b_crawler_settle.gif, "
             "S2b_contact_events.gif · 출처: verify_S2b_L1.json, 07_results/S2b/*, "
             "s2b_crawler_check.json",
             fontsize=7.8, va="top", color=INK_SECONDARY)
    image = s1.figure_to_image(fig)
    plt.close(fig)
    s1.save_atomic(OUT["summary_b"], image.save)
    summary["summary_b_png"] = rel(OUT["summary_b"])


# =============================================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", choices=ALL_PARTS, default=list(ALL_PARTS))
    parser.add_argument("--workers", type=int, default=4, help="V7 mesh render processes")
    parser.add_argument("--cluster-mm", type=float, default=0.0,
                        help="vertex-clustering cell of the drawing meshes [CAD mm]; 0 (default "
                             "since 2026-11-09) = undecimated V5 mesh, z-buffer")
    parser.add_argument("--mesh-cache", type=Path, default=None,
                        help="folder for pickled meshes (full + decimated); speeds up reruns")
    parser.add_argument("--before-dir", type=Path, default=DEFAULT_BEFORE_DIR,
                        help="rev-12 S2a result.json backups (S2a_v12_<case>.json)")
    parser.add_argument("--frames-dir", type=Path, default=None)
    parser.add_argument("--cpu", choices=("ecore", "pcore", "os"), default="ecore")
    parser.add_argument("--params", type=Path, default=None,
                        help="YAML the stored Records were run with (default "
                             "02_params/rexome33.yaml)")
    args = parser.parse_args()
    s1.PARAMS_PATH[0] = args.params
    started = time.perf_counter()
    cpu = place_cpu(args.cpu)
    if args.frames_dir:
        args.frames_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_json(OUT["json"]) if OUT["json"].exists() else {}
    summary["meta"] = {
        "script": "04_scripts/02_chrono/render_S2_gifs.py", "cpu": cpu,
        "view_oblique_toward_viewer_body": VIEWS["oblique"][2].round(4).tolist(),
        "arrow_normal_m_per_kN": ARROW_N_M_PER_N * 1e3,
        "arrow_tangential_m_per_kN": ARROW_T_M_PER_N * 1e3,
        "before_dir": str(args.before_dir) if args.before_dir else None,
        "params_file": (args.params.resolve().relative_to(ROOT).as_posix() if args.params
                        else "02_params/rexome33.yaml"),
    }
    need_mesh = {"v7", "v12", "v11", "crawler", "events"} & set(args.only)
    bank = mesh_pickle = None
    if need_mesh:
        cache_dir = args.mesh_cache
        if "v7" in args.only and cache_dir is None:
            raise SystemExit("--mesh-cache is required for v7 (workers read the decimated meshes)")
        parts, render, stats, mesh_pickle = load_drawing_meshes(cache_dir, args.cluster_mm)
        bank = MeshBank.build(parts, render)
        summary["meta"]["meshes"] = stats
        print(f"meshes {stats} {time.perf_counter() - started:.0f} s", flush=True)
    if "v7" in args.only:
        render_v7(args, bank, mesh_pickle, summary)
        print(json.dumps(summary["v7_gif"]), flush=True)
    if "dt" in args.only:
        render_dt_study(summary)
    if "v12" in args.only or "v12png" in args.only:
        if "v12" in args.only:
            cases = render_v12(bank, args, summary)
            print(json.dumps(summary["v12_gif"]), flush=True)
        else:
            cases = [load_v12(n, lab, read_json(VERIFY_A), read_json(REFERENCE_JSON),
                              args.before_dir) for n, lab in V12_CASES]
        if "v12png" in args.only:
            render_v12_summary(cases, summary, read_json(VERIFY_A))
    if "v11" in args.only:
        render_v11(bank, summary)
        print(json.dumps(summary["v11_gif"]), flush=True)
    if "ramp" in args.only:
        render_ramp_png(summary)
    if "crawler" in args.only:
        render_crawler(bank, summary)
        print(json.dumps(summary["crawler_gif"]), flush=True)
    if "events" in args.only:
        render_events(bank, summary)
        print(json.dumps(summary["events_gif"]), flush=True)
    if "summary" in args.only:
        render_summary_a(summary, args.before_dir)
        render_summary_b(summary)
    summary["last_run_s"] = round(time.perf_counter() - started, 1)
    OUT["json"].write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=float),
                           encoding="utf-8")
    print(f"done {summary['last_run_s']} s", flush=True)


if __name__ == "__main__":
    main()
