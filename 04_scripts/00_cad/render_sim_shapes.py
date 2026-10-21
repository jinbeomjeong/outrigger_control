"""Irrlicht snapshots of the C8 shapes on the L1 model (no simulation step is taken).

Builds ``outrigger_sim.chrono.model.L1Model`` (top auger level, operating extensions, pads
just touching), attaches the default visuals with ``chrono.sim_shapes.attach_model_visuals``
and writes (01_cad/09_sim_shapes/):
    sim_shapes_irrlicht_overview.png    whole machine, oblique front-left view
    sim_shapes_irrlicht_collision.png   front-left close-up: collision candidates (CoACD track
                                        pieces at 45 % opacity, pad hull) + the current
                                        contact spheres (pads, crawler layout D) in red
    sim_shapes_upper_roller.png         left-track side close-up: upper (carrier) roller drawn as
                                        separate shapes (orange), crawler without upper rollers
    sim_shapes_render.json              camera, sizes, timings

A window opens for a few frames (Irrlicht has no off-screen mode in pychrono 10).

Usage (project root): python -I 04_scripts/00_cad/render_sim_shapes.py [--only overview collision upper_roller]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

import pychrono as ch  # noqa: E402
import pychrono.irrlicht as irr  # noqa: E402

from outrigger_sim.chrono import sim_shapes  # noqa: E402
from outrigger_sim.chrono.model import L1Model  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

OUT = ROOT / "01_cad" / "09_sim_shapes"
SIZE = (1600, 1000)
PIECE_COLORS = [(0.90, 0.35, 0.20), (0.20, 0.60, 0.90), (0.95, 0.75, 0.20), (0.35, 0.75, 0.35),
                (0.70, 0.40, 0.85), (0.15, 0.80, 0.75)]


def mesh_from_arrays(vertices, faces) -> ch.ChTriangleMeshConnected:
    mesh = ch.ChTriangleMeshConnected()
    for a, b, c in faces:
        mesh.AddTriangle(*(ch.ChVector3d(*map(float, vertices[k])) for k in (a, b, c)))
    return mesh


def add_floor(model: L1Model, half=(7.0, 5.0)) -> None:
    box = ch.ChVisualShapeBox(2 * half[0], 2 * half[1], 0.02)
    box.SetColor(ch.ChColor(0.55, 0.54, 0.52))
    model.floor.AddVisualShape(box, ch.ChFramed(ch.ChVector3d(0, 0, model.floor_z_m - 0.0101), ch.QUNIT))


def add_collision_visuals(model: L1Model, index: sim_shapes.SimShapeIndex) -> dict:
    """Collision candidates drawn as visuals (pieces coloured) + current contact spheres."""
    params = model.params
    counts = {}
    for name in ("track_L_coacd", "track_R_coacd"):
        entry = index.collision(name)
        offset = sim_shapes.shape_offset_m(params, entry)
        pieces = sim_shapes.read_obj_pieces(entry.file)
        for k, (v, f) in enumerate(pieces):
            shape = ch.ChVisualShapeTriangleMesh()
            shape.SetMesh(mesh_from_arrays(v + offset, f))
            shape.SetColor(ch.ChColor(*PIECE_COLORS[k % len(PIECE_COLORS)]))
            shape.SetOpacity(0.45)
            model.superstructure.AddVisualShape(shape, ch.ChFramed())
        counts[name] = len(pieces)
    for i, leg in enumerate(model.legs):
        entry = index.collision(f"pad_{params.legs[i].name}_hull")
        v, f = sim_shapes.read_obj_pieces(entry.file)[0]
        shape = ch.ChVisualShapeTriangleMesh()
        shape.SetMesh(mesh_from_arrays(v + sim_shapes.shape_offset_m(params, entry), f))
        shape.SetColor(ch.ChColor(0.11, 0.69, 0.48))
        leg.AddVisualShape(shape, ch.ChFramed())
        rod = index.visual(f"rod_{params.legs[i].name}")
        sim_shapes.add_visual(leg, rod, params)
        sphere = ch.ChVisualShapeSphere(model.sphere_radii_m[i])
        sphere.SetColor(ch.ChColor(0.89, 0.14, 0.36))
        leg.AddVisualShape(sphere, ch.ChFramed(ch.ChVector3d(*model.sphere_centres_local_m[i]), ch.QUNIT))
    radius = model.crawler_layout.sphere_radius_m if model.crawler_layout else 0.0
    for c in model.crawler_centres_local_m:
        sphere = ch.ChVisualShapeSphere(radius)
        sphere.SetColor(ch.ChColor(0.89, 0.14, 0.36))
        model.superstructure.AddVisualShape(sphere, ch.ChFramed(ch.ChVector3d(*map(float, c)), ch.QUNIT))
    counts["crawler_spheres"] = len(model.crawler_centres_local_m)
    return counts


def snapshot(model: L1Model, path: Path, eye, target, title: str) -> dict:
    vis = irr.ChVisualSystemIrrlicht()
    vis.AttachSystem(model.system)
    vis.SetWindowSize(*SIZE)
    vis.SetWindowTitle(title)
    vis.SetCameraVertical(ch.CameraVerticalDir_Z)
    vis.SetBackgroundColor(ch.ChColor(1.0, 1.0, 1.0)) if hasattr(vis, "SetBackgroundColor") else None
    vis.Initialize()
    vis.AddTypicalLights()
    vis.AddCamera(ch.ChVector3d(*eye), ch.ChVector3d(*target))
    started = time.perf_counter()
    for _ in range(5):
        vis.BeginScene()
        vis.Render()
        vis.EndScene()
    vis.WriteImageToFile(str(path))
    for _ in range(2):  # the screenshot is taken from the back buffer of the next frame
        vis.BeginScene()
        vis.Render()
        vis.EndScene()
    vis.GetDevice().closeDevice()
    return {"file": path.relative_to(ROOT).as_posix(), "eye_m": list(eye), "target_m": list(target),
            "render_s": time.perf_counter() - started}


def render_upper_roller(params, index) -> dict:
    """Left-track side close-up: crawler without upper rollers + upper rollers (orange) on the
    superstructure (attach_model_visuals(upper_rollers=True)); the primitive cylinders of the
    roller coincide with its treads and flange and are not drawn."""
    model = L1Model(params)
    report = sim_shapes.attach_model_visuals(
        model, index, superstructure_visuals=["crawler", "deck", "barrel_FL", "barrel_RL"], upper_rollers=True)
    add_floor(model)
    axis = np.asarray(index.visual("upper_roller_L").raw["axis_body_m"])
    world_axis = model.pose.to_world(axis)
    eye = world_axis + np.array([0.40, 0.75, 0.03])
    out = snapshot(model, OUT / "sim_shapes_upper_roller.png", tuple(eye), tuple(world_axis + [0.0, -0.05, 0.0]),
                   "C8 sim shapes - upper roller (left track)")
    out["visuals"] = report.visual
    out["axis_world_m"] = world_axis.tolist()
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", choices=("overview", "collision", "upper_roller"))
    only = set(parser.parse_args().only or ("overview", "collision", "upper_roller"))
    params = load_params()
    index = sim_shapes.SimShapeIndex.load()
    path = OUT / "sim_shapes_render.json"
    record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    record.update({"level": str(params.level), "window_px": SIZE})
    if "overview" in only:
        started = time.perf_counter()
        model = L1Model(params)
        report = sim_shapes.attach_model_visuals(model, index)
        add_floor(model)
        record["attach_s"] = time.perf_counter() - started
        record["visuals"] = report.visual
        record["overview"] = snapshot(model, OUT / "sim_shapes_irrlicht_overview.png",
                                      (10.5, 9.0, 5.0), (0.5, 0.0, 4.2), "C8 sim shapes - overview")
    if "collision" in only:
        model2 = L1Model(params)
        sim_shapes.attach_superstructure(model2.superstructure, params, index,
                                         visuals=["deck", "barrel_FL", "barrel_FR"])
        record["collision_counts"] = add_collision_visuals(model2, index)
        add_floor(model2)
        record["collision"] = snapshot(model2, OUT / "sim_shapes_irrlicht_collision.png",
                                       (4.6, 4.2, 0.6), (1.6, 1.1, -0.6), "C8 sim shapes - collision candidates")
    if "upper_roller" in only:
        record["upper_roller"] = render_upper_roller(params, index)
    path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: record.get(k) for k in ("overview", "collision", "upper_roller")}, default=str))


if __name__ == "__main__":
    main()
