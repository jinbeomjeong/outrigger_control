"""S9 machine crawler settle with a gravity ramp (dynamics check, dynamics_model.md 5.34; not a judgement run).

Builds the S9 machine exactly as ``run_S9.py machine`` (S9Model, b-prime, anchors, swivel stabilisers) and
ramps the gravity magnitude from 0 to g with a Poly345 (or linear) shape over ``--ramp`` s, then holds.
Purpose: show that the ~1 Hz pitch-surge ringing of the sudden-gravity smoke run is the crawler rocking
mode excited by the step load (dynamics 5.34.1) and that a smooth ramp removes it (P2 settle rule).

Usage (Chrono-dev python, worktree root):
    python -I -X utf8 -u 04_scripts/02_chrono/s9_settle_ramp_probe.py --soil G1 --grid 0.04 --ramp 3 --t-end 5
Output 07_results/S9/settle_ramp_<soil>_<grid>_<ramp>_<stamp>/ (result.json + series.npz). SI, world z up,
x forward, pitch > 0 nose down, gravity (0, 0, -g ramp(t)), g = 9.80665.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_S9 as r9  # noqa: E402  (sets sys.path to 03_src)

import numpy as np  # noqa: E402


def ramp_factor(t: float, T: float, shape: str) -> float:
    if T <= 0.0:
        return 1.0
    u = min(max(t / T, 0.0), 1.0)
    return u if shape == "linear" else 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5


def main(argv):
    import pychrono as ch

    from outrigger_sim.frames import roll_pitch_from_quat

    ap = argparse.ArgumentParser()
    r9._common(ap)
    ap.add_argument("--ramp", type=float, default=3.0)
    ap.add_argument("--shape", choices=("poly345", "linear"), default="poly345")
    ap.add_argument("--t-end", type=float, default=5.0)
    ap.add_argument("--z0", type=float, default=0.0,
                    help="start gap of all bodies above the SCM plane [m] (> SCM ray-hit offset; 0 = runner pose)")
    ap.add_argument("--floor-roll", type=float, default=0.0)
    ap.add_argument("--floor-pitch", type=float, default=0.0)
    args = ap.parse_args(argv)
    placement = r9.place()
    params, pv, soil = r9.load_inputs(args)
    model = r9.build_machine(args, params, pv, soil)
    if args.z0 != 0.0:  # rigid shift of every body along the plane normal (start gap above the SCM plane)
        n_w = model.normal_world
        for b in model.bodies:
            b.SetPos(b.GetPos() + ch.ChVector3d(*(float(v) * args.z0 for v in n_w)))
    dt = model.dt_s
    g = r9.G
    every = max(1, round(r9.RECORD_S / dt))
    rows = []
    n = round(args.t_end / dt)
    t0 = time.perf_counter()
    for k in range(n):
        t = k * dt
        f = ramp_factor(t, args.ramp, args.shape)
        model.system.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, -g * f))
        p = model.step(capture=((k + 1) % every == 0))
        if p is not None:
            rec = model.s9_record()
            rp = roll_pitch_from_quat(p.body_quat_wxyz)
            rows.append(dict(t_s=rec["t_s"], g_factor=f, roll_pitch_deg=[math.degrees(a) for a in rp],
                             body_pos_m=p.body_pos_m.tolist(), scm_crawler_normal_N=rec["scm_crawler_normal_N"],
                             scm_contact_patches=rec["scm_contact_patches"],
                             track_utilisation=rec.get("track_utilisation")))
    wall = time.perf_counter() - t0
    T = np.array([r["t_s"] for r in rows])
    th = np.array([r["roll_pitch_deg"][1] for r in rows])
    pos = np.array([r["body_pos_m"] for r in rows])
    fz = np.array([r["scm_crawler_normal_N"] for r in rows])
    last = T >= T[-1] - 1.0
    w_total = (params.superstructure.mass_properties.mass_kg + sum(leg.moving_part.mass_kg for leg in params.legs)) * g
    summary = dict(
        doc="dynamics check: gravity ramp crawler settle (not a judgement run)", args=vars(args), placement=placement,
        wall_s=wall, us_per_step=wall / n * 1e6,
        last_1s=dict(pitch_mean_deg=float(th[last].mean()), pitch_pp_deg=float(np.ptp(th[last])),
                     roll_mean_deg=float(np.mean([r["roll_pitch_deg"][0] for r, m in zip(rows, last) if m])),
                     z_origin_mean_mm=float(pos[last, 2].mean() * 1e3), x_origin_mean_mm=float(pos[last, 0].mean() * 1e3),
                     x_pp_mm=float(np.ptp(pos[last, 0]) * 1e3),
                     normal_over_weight=float(fz[last].mean() / w_total)),
        start=dict(first_record_normal_N=float(fz[0]), z_origin_max_mm=float(pos[:, 2].max() * 1e3),
                   t_z_max_s=float(T[int(np.argmax(pos[:, 2]))])),
        after_ramp=dict(pitch_pp_deg=float(np.ptp(th[T >= args.ramp + 0.2])) if (T >= args.ramp + 0.2).any() else None),
        meta=model.meta())
    tag = f"{args.soil}_{args.grid * 100:g}cm_{args.shape}{args.ramp:g}_z{args.z0 * 1e3:g}mm"
    d = r9.out_dir("settle_ramp", tag)
    np.savez(d / "series.npz", t_s=T, pitch_deg=th, roll_deg=np.array([r["roll_pitch_deg"][0] for r in rows]),
             body_pos_m=pos, scm_crawler_normal_N=fz, g_factor=np.array([r["g_factor"] for r in rows]))
    (d / "result.json").write_text(json.dumps(r9._plain(summary), indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps(r9._plain({k: summary[k] for k in ("start", "last_1s", "after_ramp", "us_per_step", "wall_s")}), indent=1))
    print("->", d, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
