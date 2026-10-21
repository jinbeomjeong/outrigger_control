"""Upper roller vs neighbouring crawler solids: interference check and figure (C8, 2026-10-21).

Answers "does the upper roller overlap the track frame?" from the B-rep cache only:
    * BRepExtrema distance and BRepAlgoAPI_Common volume between the roller solid (234 / 1900)
      and its neighbours (frame 8 / 1674, seat plate 22 / 1688, link-rail solids, bracket
      fasteners, centre frame 1379);
    * frame material just below its top (Y_cad -381 / -391 mm) at the roller station
      (BRepClass3d_SolidClassifier grid): is the frame top continuous under the roller?
    * planar sections at X_cad = 1045 mm (roller mid-plane, Y-Z view) and Z_cad = 0 (Y-X view);
    * Irrlicht views from the same camera: (a) the default ``crawler`` visual (roller inside),
      (b) ``crawler_no_upper_rollers`` + ``upper_roller_L`` (orange), as in
      ``sim_shapes_upper_roller.png``; and the vertex distance between the roller part in the
      crawler visual and ``upper_roller_L.obj``.

Writes 01_cad/09_sim_shapes/upper_roller_overlap_check.{png,json}.
CPU: one process pinned to the P-cores (logical 0-15).

Usage (project root): python -I -X utf8 04_scripts/00_cad/check_upper_roller_overlap.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))

import brep_cache  # noqa: E402
from build_sim_shapes import VISUAL_DIR, read_obj, rel, source_record  # noqa: E402

OUT_PNG = ROOT / "01_cad" / "09_sim_shapes" / "upper_roller_overlap_check.png"
OUT_JSON = OUT_PNG.with_suffix(".json")
SOLIDS_CSV = ROOT / "01_cad" / "06_brep" / "derived" / "crawler" / "crawler_solids.csv"
ROLLER = {"L": 234, "R": 1900}
LEFT_NEIGHBOURS = {8: "frame", 22: "seat plate", 50: "frame rib", 1379: "centre frame", 833: "link",
                   834: "link", 859: "link", 860: "link", 1553: "bolt", 1554: "washer", 1555: "bolt",
                   1556: "washer", 1557: "bolt", 1558: "washer", 1559: "bolt", 1560: "washer"}
SECTION_SOLIDS = {234: ("roller", "#e8701a"), 8: ("frame 8", "#4d4d4d"), 22: ("seat plate 22", "#2a78d6"),
                  50: ("rib 50", "#8a8a8a"), 1379: ("centre frame", "#b0b0b0"), 833: ("link", "#7a3db8"),
                  834: ("link", "#7a3db8"), 859: ("link", "#b48ad6"), 860: ("link", "#b48ad6"),
                  **{k: ("bolt/washer", "#1baf7a") for k in range(1553, 1561)}}
X_SECTION_MM = 1045.0
Z_SECTION_MM = 0.0


def place_pcore() -> dict:
    try:
        import psutil

        psutil.Process().cpu_affinity(list(range(0, 16)))
        return {"affinity": "0-15"}
    except Exception as error:  # noqa: BLE001
        return {"error": repr(error)}


def crawler_solids():
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer

    instance = [i for i in brep_cache.instances() if i.prototype_entry == "0:1:1:746"][0]
    shape = brep_cache.load_part(instance.instance_path)
    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(explorer.Current())
        explorer.Next()
    return solids


def volume(shape) -> float:
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    return props.Mass()


def mirror_index(table, k: int) -> int | None:
    r = table.loc[k]
    m = table[np.isclose(table.bbox_min_x_mm, -r.bbox_max_x_mm, atol=0.01)
              & np.isclose(table.bbox_min_y_mm, r.bbox_min_y_mm, atol=0.01)
              & np.isclose(table.bbox_min_z_mm, r.bbox_min_z_mm, atol=0.01)
              & np.isclose(table.volume_mm3, r.volume_mm3, rtol=1e-4)]
    return int(m.solid.iloc[0]) if len(m) else None


def pair_checks(solids, table) -> dict:
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape

    out = {}
    for side, roller in ROLLER.items():
        for k, role in LEFT_NEIGHBOURS.items():
            other = k if side == "L" or k == 1379 else mirror_index(table, k)
            if other is None:
                continue
            dist = BRepExtrema_DistShapeShape(solids[roller], solids[other])
            p = dist.PointOnShape1(1)
            common = volume(BRepAlgoAPI_Common(solids[roller], solids[other]).Shape()) if dist.Value() < 1e-6 else 0.0
            out[f"{side}:{roller}-{other}"] = {"role": role, "distance_mm": dist.Value(), "common_mm3": common,
                                              "closest_point_on_roller_cad_mm": [p.X(), p.Y(), p.Z()]}
    return out


def frame_grid(solids) -> dict:
    """Frame material just below its top at the roller station (classifier, CAD mm)."""
    from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier
    from OCC.Core.gp import gp_Pnt
    from OCC.Core.TopAbs import TopAbs_IN

    def inside(solid, x, y, z):
        return BRepClass3d_SolidClassifier(solid, gp_Pnt(x, y, z), 1e-6).State() == TopAbs_IN

    zs = np.arange(-300.0, 301.0, 5.0)
    xs = np.arange(855.0, 1236.0, 5.0)
    out = {}
    for frame, sx in ((8, 1.0), (1674, -1.0)):
        along_z = [inside(solids[frame], sx * 1045.0, -381.0, z) for z in zs]
        gaps = [float(zs[i]) for i in range(1, len(zs)) if along_z[i] != along_z[i - 1]]
        along_x = [inside(solids[frame], sx * x, -381.0, 0.0) for x in xs]
        column = [inside(solids[frame], sx * 1045.0, y, 0.0) for y in np.arange(-381.0, -720.0, -3.0)]
        out[str(frame)] = {"y_probe_mm": -381.0, "z_transitions_at_x1045_mm": gaps,
                           "material_points_at_z0_over_x855_1235": int(sum(along_x)),
                           "material_points_below_top_at_x1045_z0_down_to_y_minus_720": int(sum(column))}
    return out


def section_polylines(solid, plane_point, plane_normal, deflection=0.2):
    from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCC.Core.GCPnts import GCPnts_QuasiUniformDeflection
    from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt
    from OCC.Core.TopAbs import TopAbs_EDGE
    from OCC.Core.TopExp import TopExp_Explorer

    section = BRepAlgoAPI_Section(solid, gp_Pln(gp_Pnt(*plane_point), gp_Dir(*plane_normal)), False)
    section.ComputePCurveOn1(True)
    section.Approximation(True)
    section.Build()
    lines = []
    explorer = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
    while explorer.More():
        curve = BRepAdaptor_Curve(explorer.Current())
        explorer.Next()
        sampler = GCPnts_QuasiUniformDeflection(curve, deflection)
        if sampler.IsDone() and sampler.NbPoints() > 1:
            pts = [sampler.Value(i) for i in range(1, sampler.NbPoints() + 1)]
            lines.append(np.array([[p.X(), p.Y(), p.Z()] for p in pts]))
    return lines


def render_views(tmp: Path) -> dict:
    import pychrono as ch  # noqa: F401
    from render_sim_shapes import add_floor, snapshot

    from outrigger_sim.chrono import sim_shapes
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.params import load_params

    params = load_params()
    index = sim_shapes.SimShapeIndex.load()
    axis = np.asarray(index.visual("upper_roller_L").raw["axis_body_m"])
    out = {}
    for tag, names, rollers in (("a_crawler", ["crawler", "deck", "barrel_FL", "barrel_RL"], False),
                                ("b_no_rollers_plus_roller", ["crawler", "deck", "barrel_FL", "barrel_RL"], True)):
        model = L1Model(params)
        sim_shapes.attach_model_visuals(model, index, superstructure_visuals=names, upper_rollers=rollers)
        add_floor(model)
        world_axis = model.pose.to_world(axis)
        eye = world_axis + np.array([0.40, 0.75, 0.03])
        out[tag] = snapshot(model, tmp / f"{tag}.png", tuple(eye), tuple(world_axis + [0.0, -0.05, 0.0]),
                            f"upper roller check {tag}")
        out[tag]["png"] = str(tmp / f"{tag}.png")
    return out


def vertex_distance_check() -> dict:
    """Roller components of the crawler visual vs upper_roller_L.obj (body m)."""
    import trimesh

    from build_sim_shapes import components, load_work, used_bbox

    roller_v, roller_f = read_obj(VISUAL_DIR / "upper_roller_L.obj")[0]
    roller = trimesh.Trimesh(roller_v, roller_f, process=False)
    v, f = load_work("crawler")
    box = np.array([roller_v.min(0), roller_v.max(0)])
    comps = components(trimesh.Trimesh(v, f, process=False))
    dists = []
    for c in comps:
        b = used_bbox(v, f[c])
        if np.all(b[0] >= box[0] - 0.002) and np.all(b[1] <= box[1] + 0.002):
            pts = v[np.unique(f[c])]
            _, d, _ = trimesh.proximity.closest_point(roller, pts)
            dists.append(float(d.max()))
    return {"components_in_roller_bbox": len(dists), "max_vertex_distance_mm_per_component":
            sorted(round(d * 1e3, 3) for d in dists)}


def main() -> None:
    import pandas as pd
    from PIL import Image

    started = time.perf_counter()
    cpu = place_pcore()
    table = pd.read_csv(SOLIDS_CSV, encoding="utf-8-sig")
    solids = crawler_solids()
    for k in (8, 22, 234, 1674, 1688, 1900):
        if abs(volume(solids[k]) / table.volume_mm3[k] - 1) > 1e-9:
            raise SystemExit(f"solid index {k} does not match crawler_solids.csv")
    result = {"cpu": cpu, "pairs": pair_checks(solids, table), "frame_below_top": frame_grid(solids)}
    sections = {}
    for k in SECTION_SOLIDS:
        sections[k] = {"x": section_polylines(solids[k], (X_SECTION_MM, 0, 0), (1, 0, 0)),
                       "z": section_polylines(solids[k], (0, 0, Z_SECTION_MM), (0, 0, 1))}
    result["vertex_check"] = vertex_distance_check()
    tmp = ROOT / "01_cad" / "09_sim_shapes" / "work" / "upper_roller_check"  # inside ROOT (snapshot paths)
    tmp.mkdir(parents=True, exist_ok=True)
    result["renders"] = render_views(tmp)

    fig = plt.figure(figsize=(16, 11), dpi=110)
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    for i, tag in enumerate(("a_crawler", "b_no_rollers_plus_roller")):
        ax = fig.add_axes((0.02 + 0.49 * i, 0.50, 0.47, 0.42))
        ax.imshow(Image.open(result["renders"][tag]["png"]))
        ax.set_axis_off()
        ax.set_title({"a_crawler": "(a) 기본 crawler 시각 메시만 (롤러 포함)",
                      "b_no_rollers_plus_roller": "(b) crawler_no_upper_rollers + upper_roller_L (주황)"}[tag],
                      fontsize=10)
    panels = (("x", "X_cad = 1045 mm 단면 (롤러 가운데, 트랙 길이 방향 Z_cad)", 2, 1, (-300, 300), (-470, -150)),
              ("z", "Z_cad = 0 단면 (롤러 축 포함, 트랙 폭 방향 X_cad)", 0, 1, (840, 1250), (-470, -150)))
    for i, (key, title, hcol, vcol, xlim, ylim) in enumerate(panels):
        ax = fig.add_axes((0.06 + 0.49 * i, 0.06, 0.42, 0.40))
        seen = set()
        for k, (label, colour) in SECTION_SOLIDS.items():
            for line in sections[k][key]:
                ax.plot(line[:, hcol], line[:, vcol], color=colour, lw=1.4 if k in (234, 8, 22) else 0.9,
                        label=None if label in seen else label)
                seen.add(label)
        ax.axhline(-380.105, color="#4d4d4d", lw=0.6, ls=":")
        ax.axhline(-392.719, color="#e8701a", lw=0.6, ls=":")
        ax.axhline(-389.719, color="#2a78d6", lw=0.6, ls=":")
        ax.axhline(-272.719, color="#7a3db8", lw=0.6, ls=":")
        ax.text(xlim[0] + 5, -378.5, "프레임 8 최상단 Y −380.1", fontsize=7, color="#4d4d4d")
        ax.text(xlim[0] + 5, -398.5, "답면 바닥 Y −392.7 / 받침판 윗면 −389.7", fontsize=7, color="#e8701a")
        ax.text(xlim[0] + 5, -270.5, "답면 꼭대기 Y −272.7 = 링크 레일 하면", fontsize=7, color="#7a3db8")
        if key == "x":
            ax.annotate("프레임 8 윗판의 구멍(단면 Z_cad ±75)\n롤러가 이 구멍을 지난다", xy=(0, -385),
                        xytext=(110, -440), fontsize=8, arrowprops={"arrowstyle": "->", "lw": 0.8})
        else:
            ax.annotate("프레임 8 경사판(롤러 아래 틈)\n롤러까지 최소 9.18 mm", xy=(1112, -400), xytext=(1080, -452),
                        fontsize=8, arrowprops={"arrowstyle": "->", "lw": 0.8})
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.grid(lw=0.3, color="#dddddd")
        ax.set_xlabel("Z_cad [mm]" if key == "x" else "X_cad [mm]")
        ax.set_ylabel("Y_cad [mm] (위 +)")
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=7, loc="upper right", ncol=2)
    d8 = result["pairs"]["L:234-8"]["distance_mm"]
    fig.suptitle(f"상부 롤러 간섭 점검 (왼쪽 트랙): 롤러–프레임 8 최소 거리 {d8:.2f} mm, 공통 부피 0 — "
                 "프레임 윗면은 롤러 아래가 뚫려 있다(Z_cad −75…+75)", fontsize=11, y=0.985)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG)
    plt.close(fig)
    for tag in result["renders"]:
        result["renders"][tag].pop("png", None)
    result["sources"] = [source_record(SOLIDS_CSV), source_record(ROOT / "01_cad" / "06_brep" / "prototypes" / "0_1_1_746.bbrep")]
    result["figure"] = rel(OUT_PNG)
    result["time_s"] = time.perf_counter() - started
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"pairs_with_contact": {k: v for k, v in result["pairs"].items() if v["distance_mm"] < 1e-6},
                      "frame": result["frame_below_top"], "vertex": result["vertex_check"],
                      "time_s": result["time_s"]}, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
