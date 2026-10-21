"""Isometric renders of the whole assembly in the STEP colours (C11 check figure).

Reads only cached data:
    01_cad/01_parts/parts_classified.csv   instance rows (render mesh order)
    01_cad/05_meshes/render_mesh.npz       decimated drawing meshes (render_auger_descent)
    01_cad/08_style/instance_styles.csv    STEP colours (build_style_index.py, via style_index)

Writes in 01_cad/08_style/:
    style_iso.png                two panels, same view from front-right-above:
                                 left  = display colours (Inventor assembly appearance
                                         overrides applied),
                                 right = part colours only (no overrides; what the OCCT XCAF
                                         reader attaches)
    style_iso_rear.png           display colours seen from rear-left-above
    render_style_views.json      view vectors, counts, timings

Method: the painter-sorted shaded mesh of render_layout_views (Lambert shade, depth fade,
hidden-line outlines) with one colour per instance. Parts with several face colours (35
instances) use their dominant colour; transparency (glass) is not drawn. Body frame: x = Z_cad,
y = X_cad, z = Y_cad, metres, CAD origin, auger at the CAD pose.

Usage:
    python -I 04_scripts/00_cad/render_style_views.py [--dpi 130] [--width-px 1800]
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_layout_views as rlv
import style_index
from analyze_parts import CLASSIFIED_CSV, INK_PRIMARY, INK_SECONDARY, SURFACE
from render_auger_descent import load_render_meshes

OUT_DIR = style_index.STYLE_DIR
PNG_ISO = OUT_DIR / "style_iso.png"
PNG_REAR = OUT_DIR / "style_iso_rear.png"
META_JSON = OUT_DIR / "render_style_views.json"
plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def iso_view(toward: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(screen right, screen up, toward viewer) for a viewer at direction ``toward``, z up."""
    toward = toward / np.linalg.norm(toward)
    right = np.cross([0.0, 0.0, 1.0], toward)
    right /= np.linalg.norm(right)
    return right, np.cross(toward, right), toward


VIEW_VECTORS = {
    "iso_front_right": iso_view(np.array([1.0, -1.0, 0.75])),
    "iso_rear_left": iso_view(np.array([-1.0, 1.0, 0.75])),
}


def draw_panels(items_by_panel, view: str, titles, path: Path, width_px: int, dpi: float,
                legend_colours: list[tuple[str, str]], style: rlv.EdgeStyle, note: str) -> dict:
    rlv.VIEWS[view] = VIEW_VECTORS[view]  # shade_scene looks the view up by name
    right, up, _ = VIEW_VECTORS[view]
    points = np.concatenate([item.vertices_m for item in items_by_panel[0]])
    screen = np.stack([points @ right, points @ up], axis=1)
    low, high = screen.min(axis=0), screen.max(axis=0)
    pad = 0.04 * (high - low).max()
    low, high = low - pad, high + pad
    panels = len(items_by_panel)
    aspect = (high[1] - low[1]) / (high[0] - low[0])
    width_in = width_px / dpi
    panel_w = width_in / panels
    height_in = panel_w * aspect + (1.3 if panels > 1 else 1.6)
    figure, axes = plt.subplots(1, panels, figsize=(width_in, height_in), facecolor=SURFACE,
                                squeeze=False)
    counts = {}
    for ax, items, title in zip(axes[0], items_by_panel, titles, strict=True):
        ax.set_xlim(low[0], high[0])
        ax.set_ylim(low[1], high[1])
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(title, fontsize=10, color=INK_PRIMARY, loc="left")
    figure.subplots_adjust(left=0.01, right=0.99, top=1 - 0.55 / height_in,
                           bottom=1.0 / height_in, wspace=0.02)
    for ax, items, title in zip(axes[0], items_by_panel, titles, strict=True):
        scene = rlv.shade_scene(items, view, rlv.px_per_metre(ax), style, dpi)
        counts[title] = {"polygons": int(len(scene[0])), "outline_segments": int(scene[4].sum())}
        ax.add_collection(rlv.scene_collection(scene), autolim=False)
    handles = [Rectangle((0, 0), 1, 1, color=hex_value) for hex_value, _ in legend_colours]
    figure.legend(handles, [label for _, label in legend_colours], loc="lower center",
                  bbox_to_anchor=(0.5, 0.3 / height_in),
                  ncol=min(3 * panels, len(handles)), frameon=False, fontsize=8, labelcolor=INK_SECONDARY)
    figure.text(0.01, 0.005, note, fontsize=7, color=INK_SECONDARY, va="bottom")
    figure.savefig(path, dpi=dpi, facecolor=SURFACE)
    plt.close(figure)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dpi", type=float, default=130.0)
    parser.add_argument("--width-px", type=int, default=2000)
    arguments = parser.parse_args()
    started_s = time.perf_counter()
    table = pd.read_csv(CLASSIFIED_CSV, encoding="utf-8-sig")
    paths = table["instance_path"].tolist()
    render, cache_valid = load_render_meshes(paths)
    topologies = rlv.build_topologies(render)
    display = style_index.colours_for(paths, "display")
    part = style_index.colours_for(paths, "part")
    vertices = [rlv.body_vertices(v) for v, _ in render]

    def items(colours):
        return [rlv.SceneItem(v, topo, colour) for v, topo, colour in
                zip(vertices, topologies, colours, strict=True)]

    names = {"#ff4d06": "주황", "#696969": "진회색", "#e0dfdb": "밝은 회색(실린더 등)",
             "#bfbfbf": "회색(크롤러·오거)", "#404040": "어두운 회색"}
    used = Counter(display)
    legend = [(h, f"{h} {names.get(h, '')} · {n}개") for h, n in used.most_common(6)]
    style = rlv.EdgeStyle(width_px=0.35)
    note = ("STEP COLOUR_RGB 값(인스턴스당 대표색 1개, 투명도 미표시). 기체 좌표 x 전방·y 좌측·z 상방, "
            "오거 CAD 자세. 출처 01_cad/08_style/instance_styles.csv")
    meta = {"generator": "04_scripts/00_cad/render_style_views.py",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "render_mesh_cache_valid": bool(cache_valid), "instances": len(paths),
            "views_body_frame": {k: {"right": v[0].round(4).tolist(), "up": v[1].round(4).tolist(),
                                     "toward_viewer": v[2].round(4).tolist()}
                                 for k, v in VIEW_VECTORS.items()},
            "display_colour_counts": dict(used),
            "part_colour_counts": dict(Counter(part))}
    meta["style_iso"] = draw_panels(
        [items(display), items(part)], "iso_front_right",
        ["STEP 표시색 (조립 외관 재정의 CDORSI 적용)", "부품 자체 색 (재정의 없음, OCCT XCAF가 붙이는 색)"],
        PNG_ISO, arguments.width_px, arguments.dpi, legend, style, note)
    meta["style_iso_rear"] = draw_panels(
        [items(display)], "iso_rear_left", ["STEP 표시색, 후방 좌측 위에서"],
        PNG_REAR, arguments.width_px // 2 + 200, arguments.dpi, legend, style, note)
    meta["elapsed_s"] = round(time.perf_counter() - started_s, 1)
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
