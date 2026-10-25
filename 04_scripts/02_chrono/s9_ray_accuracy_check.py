"""S9 SCM ray-hit accuracy check (dynamics_model.md 5.34.10, P1-V0 (i)/(ii)); not a judgement run.

SCM takes the sinkage of every node from ``ChCollisionSystemBullet::RayHit`` (SCMTerrain.cpp:1178/1394), so a ray
that hits a collision shape below its true face is a sinkage error. This script builds the S9 machine exactly as
``run_S9.py machine`` (level start pose, legs hanging), takes one step with zero gravity and then
  (i)  casts vertical rays under the crawler C boxes (left track) and under the four pad hulls and reports the hit
       height minus the nominal face (block-bottom plane / YAML pad bottom),
  (ii) reports the SCM force of that first step (exact geometry -> 0).
Pass criteria (P1-V0): bottom faces |dev| <= 0.05 mm (except one node at the edges), |F| <= 100 N.

Usage (Chrono-dev python, worktree root):
    python -I -X utf8 -u 04_scripts/02_chrono/s9_ray_accuracy_check.py [--grid 0.04] [--step 0.02] [--pad-step 0.005]
Units SI, world z up; deviations printed in mm.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_S9 as r9  # noqa: E402  (sets sys.path to 03_src)

import numpy as np  # noqa: E402


def main(argv):
    import pychrono as ch

    ap = argparse.ArgumentParser()
    r9._common(ap)
    ap.add_argument("--step", type=float, default=0.02, help="crawler ray spacing [m]")
    ap.add_argument("--pad-step", type=float, default=0.005, help="pad ray spacing [m]")
    ap.add_argument("--floor-roll", type=float, default=0.0)
    ap.add_argument("--floor-pitch", type=float, default=0.0)
    args = ap.parse_args(argv)
    params, pv, soil = r9.load_inputs(args)
    model = r9.build_machine(args, params, pv, soil)
    model.system.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, 0.0))
    model.step()
    out = {"first_step_scm_force_N": {"superstructure": model.forces.sup_force_N.tolist(),
                                      "pads": model.forces.pad_force_N.tolist()}}
    cs = model.system.GetCollisionSystem()
    res = ch.ChRayhitResult()
    z_plane = float(params.ground.crawler_bottom_z_m) + 0.004
    dev = []
    for x in np.arange(-1.40, 1.40, args.step):
        for y in np.arange(0.78, 1.31, args.step):
            cs.RayHit(ch.ChVector3d(float(x), float(y), z_plane - 0.45), ch.ChVector3d(float(x), float(y), z_plane + 0.1), res)
            if res.hit:
                dev.append((res.abs_hitPoint.z - z_plane, float(x), float(y)))
    d = np.array([v[0] for v in dev]) * 1e3
    worst = sorted(dev)[:5]
    out["crawler_left"] = {"rays_hit": int(d.size), "below_0p05mm": int((d < -0.05).sum()),
                           "dev_min_mm": float(d.min()), "dev_median_mm": float(np.median(d)),
                           "worst_xy_m": [[w[1], w[2], w[0] * 1e3] for w in worst]}
    out["pads"] = {}
    for i, pad in enumerate(model.pads):
        bot = pad.TransformPointLocalToParent(ch.ChVector3d(*(float(v) for v in model.pad_bottom_local_pad_m[i])))
        leg = ("FL", "FR", "RL", "RR")[i]
        half = 0.215 if float(pv["pad_bottom_area_m2"][leg]) > 0.08 else 0.135  # 330 / 250 pad half width + margin
        dd = []
        for x in np.arange(-half, half + 1e-9, args.pad_step):
            for y in np.arange(-half, half + 1e-9, args.pad_step):
                cs.RayHit(ch.ChVector3d(bot.x + x, bot.y + y, bot.z - 0.3), ch.ChVector3d(bot.x + x, bot.y + y, bot.z + 0.02), res)
                if res.hit:
                    dd.append(res.abs_hitPoint.z - bot.z)
        dd = np.array(dd) * 1e3
        out["pads"][pad.GetName()] = {"rays_hit": int(dd.size), "below_0p05mm": int((dd < -0.05).sum()),
                                      "dev_min_mm": float(dd.min()), "dev_median_mm": float(np.median(dd)),
                                      "dev_max_mm": float(dd.max())}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
