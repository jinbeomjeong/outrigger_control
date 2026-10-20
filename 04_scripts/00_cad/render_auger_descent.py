"""Animated GIF of the auger (drive + tool) descending along the upright mast, top -> bottom.

Same side view, colours and axis limits as the level PNGs of analyze_auger_levels.py
(body x-z seen from -y, x -3.3 ... 6.0 m, z -1.5 ... 12.2 m, aspect 1).

Reads only cached data (no STEP parsing):
    01_cad/01_parts/parts_classified.csv   part rows (classified with analyze_auger_levels.classify)
    01_cad/01_parts/cad_summary.json       leg pad centres
    01_cad/03_auger/auger_levels.json      travel of the three levels, moving-part extents,
                                           CoG of case C
    01_cad/05_meshes/render_mesh.npz       decimated drawing meshes (analyze_mast.render_meshes)

Writes:
    01_cad/03_auger/auger_levels/auger_descent.gif

Method. The moving set translates along body +z only, so its side projection is a
pure vertical shift in screen space. Three layers are rendered once with
matplotlib on identical axes: the fixed parts (opaque background), the moving
parts at the CAD pose (transparent), and per frame a light overlay (ground band,
labels, CoG). Each frame shifts the moving layer by round(delta * px_per_m)
pixels (error <= 0.5 px, about 1 cm at the default size) and composites the
layers. The moving parts are drawn over the fixed ones, as in the PNGs.

Timing. Hold at top, constant-speed descent to the middle, hold, descent to the
bottom, hold; the GIF loops. Holds are single frames with a long duration.

Usage:
    python -I 04_scripts/00_cad/render_auger_descent.py [--fps 12.5] [--descent-s 5.6]
        [--hold-s 0.8] [--width-px 720] [--colors 128]
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
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_auger_levels import (
    AUGER_JSON,
    COG_COLOR,
    COLORS,
    CRAWLER_GROUND_Y_MM,
    FIGURE_DIR,
    FIXED,
    INK,
    INK_SECONDARY,
    LEG_ROD_PAD,
    LEVEL_LABEL,
    LEVEL_NAMES,
    MOVING,
    MOVING_DRIVE,
    MOVING_TOOL,
    PAD_COLOR,
    TOOL_STEEL,
    classify,
    project_side,
)
from analyze_mast import LEG_ORDER, RENDER_NPZ, render_meshes
from analyze_parts import CLASSIFIED_CSV
from cad_common import SUMMARY_JSON
from export_meshes import MESH_INDEX_JSON, load_meshes

GIF_PATH = FIGURE_DIR / "auger_descent.gif"
LIMITS = ((-3.3, 6.0), (-1.5, 12.2))  # same as the level PNGs (analyze_auger_levels.main)
GROUND_Z_M = CRAWLER_GROUND_Y_MM / 1000.0
EARTH_COLOR = "#8a6a45"
# Axes box in figure fractions; height follows from the equal aspect.
AXES_LEFT, AXES_BOTTOM, AXES_WIDTH = 0.105, 0.05, 0.875


def load_render_meshes(instance_paths: list[str]):
    """Decimated drawing meshes (render_mesh.npz) in parts_classified.csv row order.

    The cache is written by analyze_mast / analyze_auger_levels in that row order; it is
    rebuilt from the tessellation cache when it is older than the mesh index.
    """
    cache_valid = (RENDER_NPZ.exists()
                   and RENDER_NPZ.stat().st_mtime > MESH_INDEX_JSON.stat().st_mtime)
    meshes = None
    if not cache_valid:
        by_path = dict(zip(*load_meshes()))
        meshes = [by_path[path] for path in instance_paths]
    render = render_meshes(meshes)
    if len(render) != len(instance_paths):
        raise SystemExit(f"render cache has {len(render)} parts, table {len(instance_paths)}; "
                         "rerun analyze_mast.py")
    return render, cache_valid


def load_render():
    """Drawing meshes (cached) and motion classes, both in parts_classified.csv row order."""
    table = classify(pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig"))
    render, cache_valid = load_render_meshes(table["instance_path"].tolist())
    return render, table["motion"].tolist(), cache_valid


def figure_size(width_px: int, dpi: float) -> tuple[float, float, float]:
    """Figure (w, h) in inches and the axes height fraction for an equal-aspect box."""
    width_in = width_px / dpi
    axes_w_in = AXES_WIDTH * width_in
    axes_h_in = axes_w_in * (LIMITS[1][1] - LIMITS[1][0]) / (LIMITS[0][1] - LIMITS[0][0])
    height_in = axes_h_in / (1.0 - AXES_BOTTOM - 0.075)
    return width_in, height_in, axes_h_in / height_in


def new_axes(size, dpi, transparent: bool):
    figure = plt.figure(figsize=size[:2], dpi=dpi, facecolor="none" if transparent else "white")
    axes = figure.add_axes((AXES_LEFT, AXES_BOTTOM, AXES_WIDTH, size[2]))
    axes.set_xlim(*LIMITS[0])
    axes.set_ylim(*LIMITS[1])
    axes.set_aspect("equal", adjustable="box")
    if transparent:
        axes.set_axis_off()
        axes.patch.set_alpha(0.0)
    return figure, axes


def to_image(figure) -> Image.Image:
    figure.canvas.draw()
    return Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy(), "RGBA")


def legend_handles():
    return [
        Rectangle((0, 0), 1, 1, color=COLORS[MOVING_DRIVE],
                  label="이동: 구동부 DRIVE AUGER ASSY"),
        Rectangle((0, 0), 1, 1, color=COLORS[MOVING_TOOL], label="이동: 오거 공구 AUGER TOOL"),
        Rectangle((0, 0), 1, 1, color=COLORS[FIXED], label="고정 상부체"),
        Rectangle((0, 0), 1, 1, color=COLORS[LEG_ROD_PAD], label="다리 이동부(상부체 제외)"),
        Line2D([], [], ls="none", marker="X", ms=8, mfc=COG_COLOR, mec="white",
               label="상부체 무게중심 (경우 C)"),
        Line2D([], [], ls="none", marker="s", ms=6, mfc=PAD_COLOR, mec=INK,
               label="다리 패드 바닥 중심"),
        Rectangle((0, 0), 1, 1, color=EARTH_COLOR, alpha=0.35,
                  label="지면 아래(크롤러 바닥 아래)"),
    ]


def render_layers(render, motions, pads_body, size, dpi):
    """Background (fixed parts, axes, legend) and the moving layer at the CAD pose (travel 0)."""
    empty = [(v, f[:0]) for v, f in render]
    fixed_render = [e if m in MOVING else r for r, e, m in zip(render, empty, motions)]
    moving_render = [r if m in MOVING else e for r, e, m in zip(render, empty, motions)]

    figure, axes = new_axes(size, dpi, transparent=False)
    polygons, colours = project_side(fixed_render, motions, 0.0)
    axes.add_collection(PolyCollection(polygons, facecolors=colours, edgecolors="none",
                                       antialiased=False))
    axes.plot(pads_body[:, 0], pads_body[:, 2], ls="none", marker="s", ms=5, mfc=PAD_COLOR, mec=INK,
              zorder=7)
    axes.set_xlabel("x 전방 [m] (= CAD Z)", fontsize=8)
    axes.set_ylabel("z 상방 [m] (= CAD Y)", fontsize=8)
    axes.tick_params(labelsize=7)
    axes.grid(True, color="#e0dfda", lw=0.5)
    axes.legend(handles=legend_handles(), loc="upper left", fontsize=6.3, framealpha=0.92)
    background = to_image(figure)
    data_to_px = axes.transData.transform
    origin_px = data_to_px((0.0, 0.0))
    px_per_m = float(data_to_px((0.0, 1.0))[1] - origin_px[1])  # display y grows upward
    plt.close(figure)

    figure, axes = new_axes(size, dpi, transparent=True)
    polygons, colours = project_side(moving_render, motions, 0.0)
    axes.add_collection(PolyCollection(polygons, facecolors=colours, edgecolors="none",
                                       antialiased=False))
    moving = to_image(figure)
    plt.close(figure)
    return background, moving, px_per_m


class Overlay:
    """Per-frame annotations on a transparent figure with the same axes box."""

    def __init__(self, size, dpi, cog0, cog_rate):
        self.figure, self.axes = new_axes(size, dpi, transparent=True)
        axes = self.axes
        axes.axhspan(LIMITS[1][0], GROUND_Z_M, color=EARTH_COLOR, alpha=0.35, lw=0, zorder=1)
        axes.axhline(GROUND_Z_M, color=INK, lw=1.0, zorder=2)
        axes.text(LIMITS[0][0] + 0.1, GROUND_Z_M - 0.28, "지면(크롤러 바닥, CAD 자세)", fontsize=6.5,
                  color=INK, zorder=3)
        self.cog0, self.cog_rate = cog0, cog_rate
        (self.cog_marker,) = axes.plot([], [], marker="X", ms=9, mfc=COG_COLOR, mec="white",
                                       mew=1.1, ls="none", zorder=6)
        self.cog_text = axes.text(0, 0, "", fontsize=6.5, color=COG_COLOR, zorder=6,
                                  bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.0))
        (self.tool_tick,) = axes.plot([], [], color=INK_SECONDARY, lw=0.8, zorder=6)
        self.tool_text = axes.text(4.2, 0, "", fontsize=6.5, va="center", color=INK, zorder=6)
        self.title = self.figure.text(AXES_LEFT, 0.985, "", fontsize=9, va="top", ha="left",
                                      color=INK)
        self.banner = axes.text(-2.95, 7.4, "", fontsize=15, fontweight="bold", va="center",
                                ha="left", color=INK, zorder=8,
                                bbox=dict(fc="white", ec=INK_SECONDARY, lw=0.8,
                                          boxstyle="round,pad=0.4"))
        self.delta_text = axes.text(5.9, 12.0, "", fontsize=8, ha="right", va="top", color=INK,
                                    zorder=8, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))

    def draw(self, travel_mm: float, tool_bottom_z0: float, level: str | None) -> Image.Image:
        travel_m = travel_mm / 1000.0
        cog = self.cog0 + np.array([0.0, 0.0, self.cog_rate * travel_m])
        self.cog_marker.set_data([cog[0]], [cog[2]])
        self.cog_text.set_position((cog[0] + 0.15, cog[2] - 0.35))
        self.cog_text.set_text(f"G_C z = {cog[2]:.3f} m")
        tool_bottom = tool_bottom_z0 + travel_m
        self.tool_tick.set_data([3.95, 4.15], [tool_bottom, tool_bottom])
        below = GROUND_Z_M - tool_bottom
        extra = f"\n(지면 아래 {below:.3f} m)" if below > 0 else ""
        self.tool_text.set_position((4.2, tool_bottom))
        self.tool_text.set_text(f"공구 하단 z={tool_bottom:.3f}{extra}")
        self.delta_text.set_text(f"Δ = {travel_m:+.3f} m")
        self.title.set_text("오거(구동부+공구) 마스트 하강: 상단 → 중단 → 하단, 옆 보기(기체 x-z)\n"
                            "Δ = CAD 자세 대비 기체 z 이동량, 축 범위·축척 고정")
        if level is None:
            self.banner.set_visible(False)
        else:
            self.banner.set_visible(True)
            self.banner.set_text(f"{LEVEL_LABEL[level]}  Δ = {travel_m:+.3f} m")
        return to_image(self.figure)


def timeline(levels: dict, fps: float, descent_s: float, hold_s: float):
    """(travel_mm, level or None, duration_ms) per frame: hold, descend, hold, descend, hold."""
    travels = [levels[n]["travel_mm"] for n in LEVEL_NAMES]
    total = travels[0] - travels[-1]
    frame_ms = 1000.0 / fps
    frames = [(travels[0], LEVEL_NAMES[0], hold_s * 1000.0)]
    for i in range(len(travels) - 1):
        start, end = travels[i], travels[i + 1]
        steps = max(1, round(descent_s * fps * (start - end) / total))
        for k in range(1, steps):
            frames.append((start + (end - start) * k / steps, None, frame_ms))
        frames.append((end, LEVEL_NAMES[i + 1], hold_s * 1000.0))
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fps", type=float, default=12.5,
                        help="frame rate of the moving frames (GIF stores 10 ms units)")
    parser.add_argument("--descent-s", type=float, default=5.6,
                        help="top -> bottom time at constant speed")
    parser.add_argument("--hold-s", type=float, default=0.8, help="pause at each level")
    parser.add_argument("--width-px", type=int, default=720)
    parser.add_argument("--colors", type=int, default=128, help="global GIF palette size")
    parser.add_argument("--output", type=Path, default=GIF_PATH)
    arguments = parser.parse_args()
    started = time.perf_counter()
    dpi = 100.0

    data = json.loads(AUGER_JSON.read_text(encoding="utf-8"))
    levels = data["levels"]
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    pads_body = np.array([summary["legs"][n]["pad_center_body_m"] for n in LEG_ORDER])
    cog0 = np.array(data["current_cad_pose"]["mass"][TOOL_STEEL]["cog_body_m"])
    cog_rate = data["sensitivity"][TOOL_STEEL]["cog_z_shift_per_1m_travel_m"]
    tool_bottom_z0 = data["moving_set"]["y_extent_cad_mm"]["tool"][0] / 1000.0

    render, motions, cache_valid = load_render()
    # Row-order check: the CAD-Y extent of the drawn moving parts must match auger_levels.json.
    extent_check = {}
    for group, key in ((MOVING_DRIVE, "drive"), (MOVING_TOOL, "tool")):
        ys = np.concatenate([v[:, 1] for (v, f), m in zip(render, motions)
                             if m == group and len(f)])
        expected = data["moving_set"]["y_extent_cad_mm"][key]
        drawn = [round(float(ys.min()), 1), round(float(ys.max()), 1)]
        extent_check[key] = {"drawn_mm": drawn, "json_mm": expected}
        if abs(ys.min() - expected[0]) > 10.0 or abs(ys.max() - expected[1]) > 10.0:
            raise SystemExit(f"moving-part extent mismatch ({key}): {extent_check[key]}")
    size = figure_size(arguments.width_px, dpi)
    t0 = time.perf_counter()
    background, moving, px_per_m = render_layers(render, motions, pads_body, size, dpi)
    layer_s = time.perf_counter() - t0
    overlay = Overlay(size, dpi, cog0, cog_rate)

    frames, durations = [], []
    plan = timeline(levels, arguments.fps, arguments.descent_s, arguments.hold_s)
    for travel_mm, level, duration_ms in plan:
        shift_px = int(round(travel_mm / 1000.0 * px_per_m))
        layer = Image.new("RGBA", moving.size, (0, 0, 0, 0))
        layer.paste(moving, (0, -shift_px))  # image rows grow downward; +travel moves up
        frame = Image.alpha_composite(background, layer)
        frame = Image.alpha_composite(frame, overlay.draw(travel_mm, tool_bottom_z0, level))
        frames.append(frame.convert("RGB"))
        durations.append(int(round(duration_ms)))
    plt.close(overlay.figure)

    # One palette for all frames (top and bottom frames cover every colour) -> no palette flicker.
    sample = Image.new("RGB", (frames[0].width * 2, frames[0].height))
    sample.paste(frames[0], (0, 0))
    sample.paste(frames[-1], (frames[0].width, 0))
    palette = sample.quantize(colors=arguments.colors, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(arguments.output, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, optimize=False, disposal=1)
    report = {
        "output": str(arguments.output),
        "size_bytes": arguments.output.stat().st_size,
        "frames": len(indexed),
        "resolution_px": list(indexed[0].size),
        "fps_moving": arguments.fps,
        "loop_s": round(sum(durations) / 1000.0, 2),
        "palette_colors": arguments.colors,
        "px_per_m": round(px_per_m, 3),
        "render_cache_used": cache_valid,
        "moving_extent_check_cad_y": extent_check,
        "layer_render_s": round(layer_s, 1),
        "total_s": round(time.perf_counter() - started, 1),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
