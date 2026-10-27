"""S9 SCM ray-hit accuracy check (dynamics_model.md 5.34.10, P1-V0 (i)/(ii)); not a judgement run.

SCM takes the sinkage of every node from ``ChCollisionSystemBullet::RayHit`` (SCMTerrain.cpp:1178/1394), so a ray
that hits a collision shape below its true face is a sinkage error. This script builds the S9 machine exactly as
``run_S9.py machine`` (level start pose, legs hanging), takes one step with zero gravity and then
  (i)  casts vertical rays (bottom-up, as SCM) under the crawler C boxes (left track) and under the four pad hulls
       and reports the hit height minus the nominal face: crawler = block-bottom plane on the flat box and the ramp
       lines on the ramp boxes (``scm_model`` constants); pad = YAML pad bottom. "Bottom face" rays exclude one ray
       spacing at the face edges (crawler: track y edges and x ends; pad: the bottom polygon of the hull OBJ shrunk
       by one spacing), as the P1-V0 rule "except one node at the edges";
  (ii) reports the SCM force of that first step (exact geometry -> 0).
Pass criteria (P1-V0): bottom faces |dev| <= 0.05 mm, |F| <= 100 N.

Usage (Chrono-dev python, project root):
    python -I -X utf8 -u 04_scripts/02_chrono/s9_ray_accuracy_check.py [--grid 0.04] [--ray-shape mesh|convex]
        [--step 0.02] [--pad-step 0.005] [--margin M] [--json out.json]
Units SI, world z up; deviations printed in mm.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_S9 as r9  # noqa: E402  (sets sys.path to 03_src)

import numpy as np  # noqa: E402

DEV_TOL_MM = 0.05
FORCE_TOL_N = 100.0


def crawler_nominal_z(x: float, z0: float) -> float:
    from outrigger_sim.chrono import scm_model as sm

    if x > sm.FRONT_RAMP_X_M[0]:
        return z0 + sm.FRONT_RAMP_SLOPE * (x - sm.FRONT_RAMP_X_M[0])
    if x < sm.REAR_RAMP_X_M[1]:
        return z0 + sm.REAR_RAMP_SLOPE * (sm.REAR_RAMP_X_M[1] - x)
    return z0


def pad_bottom_polygon_local(model, i: int):
    """Bottom polygon of the pad hull OBJ in the pad body (COG) frame (shapely, xy) and its z."""
    from shapely.geometry import MultiPoint

    from outrigger_sim.chrono.sim_shapes import _require_file, pad_shape_entries, read_obj_pieces
    from outrigger_sim.params import LEG_ORDER

    _, hull = pad_shape_entries(LEG_ORDER[i], model.pad_variant_meta["pad_variant"])
    v = np.vstack([p[0] for p in read_obj_pieces(_require_file(hull))]) - np.asarray(model.pad_com_retracted_m[i])
    zmin = float(v[:, 2].min())
    bottom = v[v[:, 2] <= zmin + 1e-4]
    return MultiPoint([tuple(p[:2]) for p in bottom]).convex_hull, zmin


def stats(d_mm: np.ndarray) -> dict:
    if d_mm.size == 0:
        return {"rays": 0}
    return {"rays": int(d_mm.size), "below_0p05mm": int((d_mm < -DEV_TOL_MM).sum()),
            "above_0p05mm": int((d_mm > DEV_TOL_MM).sum()), "dev_min_mm": float(d_mm.min()),
            "dev_median_mm": float(np.median(d_mm)), "dev_max_mm": float(d_mm.max()),
            "abs_max_mm": float(np.abs(d_mm).max())}


def main(argv):
    import pychrono as ch
    from shapely.geometry import Point

    from outrigger_sim.chrono import scm_model as sm

    ap = argparse.ArgumentParser()
    r9._common(ap)
    ap.add_argument("--step", type=float, default=0.02, help="crawler ray spacing [m]")
    ap.add_argument("--pad-step", type=float, default=0.005, help="pad ray spacing [m]")
    ap.add_argument("--floor-roll", type=float, default=0.0)
    ap.add_argument("--floor-pitch", type=float, default=0.0)
    ap.add_argument("--margin", type=float, default=None,
                    help="ChCollisionModel default suggested margin before the build (sensitivity)")
    ap.add_argument("--ray-down", type=float, default=0.45, help="ray start below the face [m]")
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args(argv)
    if args.margin is not None:
        ch.ChCollisionModel.SetDefaultSuggestedMargin(float(args.margin))
    params, pv, soil = r9.load_inputs(args)
    model = r9.build_machine(args, params, pv, soil)
    model.system.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, 0.0))
    t0 = time.perf_counter()
    model.step()
    out = {"ray_shape": args.ray_shape, "grid_m": args.grid, "margin_m": ch.ChCollisionModel.GetDefaultSuggestedMargin(),
           "envelope_m": ch.ChCollisionModel.GetDefaultSuggestedEnvelope(), "first_step_wall_s": time.perf_counter() - t0,
           "first_step_scm_force_N": {"superstructure": model.forces.sup_force_N.tolist(),
                                      "pads": model.forces.pad_force_N.tolist()}}
    f_all = np.vstack([model.forces.sup_force_N, model.forces.pad_force_N])
    out["first_step_force_norm_max_N"] = float(np.linalg.norm(f_all, axis=1).max())
    cs = model.system.GetCollisionSystem()
    res = ch.ChRayhitResult()
    z0 = float(params.ground.crawler_bottom_z_m) + sm.BLOCK_BOTTOM_ABOVE_CRAWLER_BOTTOM_M
    # crawler (left track); world = body axes for the level start (origin 0)
    all_d, face_d, worst = [], [], []
    y_lo, y_hi = sm.TRACK_Y_RANGE_M
    x_lo, x_hi = sm.REAR_RAMP_X_M[0], sm.FRONT_RAMP_X_M[1]
    for x in np.arange(-1.40, 1.40, args.step):
        zn = crawler_nominal_z(float(x), z0)
        for y in np.arange(0.78, 1.31, args.step):
            cs.RayHit(ch.ChVector3d(float(x), float(y), zn - args.ray_down), ch.ChVector3d(float(x), float(y), zn + 0.1),
                      res)
            if not res.hit:
                continue
            d = (res.abs_hitPoint.z - zn) * 1e3
            all_d.append(d)
            inside = (y_lo + args.step <= y <= y_hi - args.step) and (x_lo + args.step <= x <= x_hi - args.step)
            if inside:
                face_d.append(d)
                worst.append((d, float(x), float(y)))
    worst.sort()
    out["crawler_left"] = {"all_rays": stats(np.array(all_d)), "bottom_face": stats(np.array(face_d)),
                           "worst_xy_m_dev_mm": [[w[1], w[2], w[0]] for w in worst[:5]]}
    out["pads"] = {}
    for i, pad in enumerate(model.pads):
        poly, zmin = pad_bottom_polygon_local(model, i)
        inner = poly.buffer(-args.pad_step)
        bot_local = np.asarray(model.pad_bottom_local_pad_m[i])
        all_p, face_p = [], []
        (minx, miny, maxx, maxy) = poly.bounds
        for x in np.arange(minx - 0.02, maxx + 0.02 + 1e-9, args.pad_step):
            for y in np.arange(miny - 0.02, maxy + 0.02 + 1e-9, args.pad_step):
                pl = np.array([x, y, bot_local[2]])
                pw = pad.TransformPointLocalToParent(ch.ChVector3d(*(float(v) for v in pl)))
                cs.RayHit(ch.ChVector3d(pw.x, pw.y, pw.z - 0.3), ch.ChVector3d(pw.x, pw.y, pw.z + 0.02), res)
                if not res.hit:
                    continue
                d = (res.abs_hitPoint.z - pw.z) * 1e3
                all_p.append(d)
                if inner.contains(Point(x, y)):
                    face_p.append(d)
        out["pads"][pad.GetName()] = {"obj_bottom_minus_yaml_bottom_mm": (zmin - bot_local[2]) * 1e3,
                                      "all_rays": stats(np.array(all_p)), "bottom_face": stats(np.array(face_p))}
    faces = [out["crawler_left"]["bottom_face"]] + [v["bottom_face"] for v in out["pads"].values()]
    out["P1_V0"] = {"i_bottom_abs_max_mm": max(f["abs_max_mm"] for f in faces),
                    "i_pass": all(f["abs_max_mm"] <= DEV_TOL_MM for f in faces),
                    "ii_force_max_N": out["first_step_force_norm_max_N"],
                    "ii_pass": out["first_step_force_norm_max_N"] <= FORCE_TOL_N}
    text = json.dumps(out, indent=1)
    print(text)
    if args.json:
        Path(args.json).write_text(text, "utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
