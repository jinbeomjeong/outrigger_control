"""S9 pre-check: lateral (tangential) behaviour of a single swivel pad on Chrono SCM under a constant horizontal load.

Purpose (dynamics_model.md rev. 47, 5.33): Chrono 10 SCM shear has no stick (force along the sliding velocity only,
Janosi slip j accumulated monotonically, SCMTerrain.cpp:1430-1478). This probe measures, on one pad:
  * drift velocity of the supported mass under a constant horizontal load (slope share / internal-force level),
  * the step-to-step chatter of the SCM tangential force and of the supported-mass acceleration,
  * pad tilt about the swivel,
  * whether SetSoilParameters(cohesion 0, friction 0) removes the SCM shear exactly (normal force unchanged),
  * whether SCMContactableData can be attached from Python (ChContactable.SetUserData, shared_ptr<void>).
Model: rigid "share" body (mass N/g - m_pad, translation free, rotation locked to ground by a mate) + pad body
(22.404 kg, convex hull of the pad polygon from 02_params/pad_variants.json) on a spherical joint at the ball centre
0.06 m above the pad bottom. SCM plane level (z = 0), gravity (0, 0, -9.80665). Horizontal load +x on the share body
(ChLoadBodyForce at the COM, ramped 0 -> F in 0.5 s after a 2 s settle). Body axes = world axes (x, y, z up).
Not a project model: no YAML key, not a judgement run. Chrono-dev env, P-cores (place_process).

Run (Chrono-dev):  C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I 04_scripts/02_chrono/scm_pad_lateral_probe.py
                   [--jobs 8] [--out 06_analysis/01_chrono/19_S9/scm_pad_lateral_probe.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
G = 9.80665
M_PAD = 22.404          # dynamics_model.md 2.6 (pad body incl. ribs)
H_BALL = 0.06           # swivel centre above pad bottom (YAML legs.*.pad.swivel_center_above_pad_bottom_m)
N_REAR = 72814.17       # twist-free contact force RL, top level (scm_soil_sets.json design_loads_N)
N_FRONT = 119146.29     # FL
T_SETTLE, T_RAMP, T_END = 2.0, 0.5, 12.5
T_FIT0 = 4.5            # drift fit window start (2 s after the ramp)


def pad_polygon(variant: str, leg: str) -> np.ndarray:
    pv = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))
    leg_d = pv["variants"][variant]["legs"][leg]
    poly = np.asarray(leg_d["polygon_xy_m"], float)
    if np.allclose(poly[0], poly[-1]):
        poly = poly[:-1]
    return poly - poly.mean(axis=0), float(leg_d["bottom_area_m2"])


def soil(key: str) -> dict:
    sets = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))["sets"]
    return dict(sets[key]["chrono"])


def run_case(case: dict) -> dict:
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono" / "solver_benchmark"))
    from step_cost_S0 import place_process  # noqa: PLC0415
    place = place_process("pcore")
    import pychrono as ch  # noqa: PLC0415
    import pychrono.vehicle as veh  # noqa: PLC0415

    dt = case["dt"]
    s = ch.ChSystemSMC()
    s.SetCollisionSystemType(ch.ChCollisionSystem.Type_BULLET)
    s.SetGravitationalAcceleration(ch.ChVector3d(0, 0, -G))
    s.SetTimestepperType(ch.ChTimestepper.Type_EULER_IMPLICIT_LINEARIZED)
    s.SetSolverType(ch.ChSolver.Type_SPARSE_LU)

    ground = ch.ChBody()
    ground.SetFixed(True)
    s.Add(ground)

    poly, area = pad_polygon(case["variant"], case["leg"])
    thick = 0.03
    pad = ch.ChBody()
    pad.SetMass(M_PAD)
    pad.SetInertiaXX(ch.ChVector3d(0.25, 0.25, 0.45))
    pad.SetPos(ch.ChVector3d(0, 0, thick / 2 + 0.0005))
    pts = ch.vector_ChVector3d()
    for z in (-thick / 2, thick / 2):
        for x, y in poly:
            pts.append(ch.ChVector3d(float(x), float(y), z))
    mat = ch.ChContactMaterialSMC()
    pad.AddCollisionShape(ch.ChCollisionShapeConvexHull(mat, pts), ch.ChFramed())
    pad.EnableCollision(True)
    s.Add(pad)

    m_share = case["N"] / G - M_PAD
    share = ch.ChBody()
    share.SetMass(m_share)
    share.SetInertiaXX(ch.ChVector3d(1e3, 1e3, 1e3))
    share.SetPos(ch.ChVector3d(0, 0, H_BALL + 0.3))
    s.Add(share)

    ball = ch.ChVector3d(0, 0, H_BALL + 0.0005)
    # pad_joint "spherical" = swivel (S9 plan); "fixed" = pad rotation locked to the share body (isolates the
    # SCM shear law from the swivel tilt mode)
    sph = ch.ChLinkLockSpherical() if case.get("pad_joint", "spherical") == "spherical" else ch.ChLinkLockLock()
    sph.Initialize(pad, share, ch.ChFramed(ball, ch.QUNIT))
    s.Add(sph)
    mate = ch.ChLinkMateGeneric(False, False, False, True, True, True)
    mate.Initialize(share, ground, ch.ChFramed(share.GetPos(), ch.QUNIT))
    s.Add(mate)

    loads = ch.ChLoadContainer()
    s.Add(loads)
    fload = ch.ChLoadBodyForce(share, ch.ChVector3d(0, 0, 0), False, ch.ChVector3d(0, 0, 0), True)
    loads.Add(fload)

    sp = soil(case["soil"])
    if case.get("shear_off"):
        sp["cohesion"], sp["friction"] = 0.0, 0.0
    terrain = veh.SCMTerrain(s, False)
    terrain.SetReferenceFrame(ch.ChCoordsysd(ch.ChVector3d(0, 0, 0), ch.QUNIT))
    terrain.SetSoilParameters(sp["Kphi"], sp["Kc"], sp["n"], sp["cohesion"], sp["friction"], sp["Janosi"],
                              sp["elastic_K"], sp["damping_R"])
    terrain.AddActiveDomain(pad, ch.ChVector3d(0, 0, 0), ch.ChVector3d(0.6, 0.6, 0.4))
    terrain.Initialize(1.2, 1.2, case.get("delta", 0.01))

    userdata = None
    if case.get("userdata"):
        try:
            cd = veh.SCMContactableData(1.0, 0.0, 0.0, 0.01)
            pad.SetUserData(cd)
            userdata = {"attached": True, "HasData": bool(pad.HasData())}
            case["_cd_keepalive"] = cd
        except Exception as exc:  # SWIG type mismatch expected (shared_ptr<void>)
            userdata = {"attached": False, "error": f"{type(exc).__name__}: {exc}"[:400]}

    F_target = case["F"]
    t_end = case.get("t_end", T_END)
    n_steps = int(round(t_end / dt))
    rec_every = max(1, int(round(1e-3 / dt)))
    rec = {k: [] for k in ("t", "x", "y", "z_pad", "tilt_y_deg", "Fx", "Fy", "Fz", "ax_min", "ax_max",
                           "Fx_min", "Fx_max", "flips")}
    ax_lo, ax_hi, fx_lo, fx_hi, flips, prev_sign = 1e30, -1e30, 1e30, -1e30, 0, 0
    f, tq = ch.ChVector3d(0, 0, 0), ch.ChVector3d(0, 0, 0)
    t0 = time.perf_counter()
    for k in range(n_steps):
        t = k * dt
        if t < T_SETTLE:
            Fh = 0.0
        elif t < T_SETTLE + T_RAMP:
            Fh = F_target * (t - T_SETTLE) / T_RAMP
        else:
            Fh = F_target
        fload.SetForce(ch.ChVector3d(Fh, 0, 0), False)
        s.DoStepDynamics(dt)
        terrain.GetContactForceBody(pad, f, tq)
        fx = f.x
        a = share.GetPosDt2().x
        ax_lo, ax_hi = min(ax_lo, a), max(ax_hi, a)
        fx_lo, fx_hi = min(fx_lo, fx), max(fx_hi, fx)
        sg = (fx > 0) - (fx < 0)
        if sg != 0 and prev_sign != 0 and sg != prev_sign:
            flips += 1
        if sg != 0:
            prev_sign = sg
        if (k + 1) % rec_every == 0:
            p = share.GetPos()
            q = pad.GetRot()
            zax = q.Rotate(ch.ChVector3d(0, 0, 1))
            rec["t"].append((k + 1) * dt)
            rec["x"].append(p.x)
            rec["y"].append(p.y)
            rec["z_pad"].append(pad.GetPos().z - thick / 2)
            rec["tilt_y_deg"].append(math.degrees(math.atan2(zax.x, zax.z)))
            rec["Fx"].append(fx)
            rec["Fy"].append(f.y)
            rec["Fz"].append(f.z)
            rec["ax_min"].append(ax_lo)
            rec["ax_max"].append(ax_hi)
            rec["Fx_min"].append(fx_lo)
            rec["Fx_max"].append(fx_hi)
            rec["flips"].append(flips)
            ax_lo, ax_hi, fx_lo, fx_hi, flips = 1e30, -1e30, 1e30, -1e30, 0
    wall = time.perf_counter() - t0

    r = {k: np.asarray(v) for k, v in rec.items()}
    w = r["t"] >= T_FIT0
    hold = r["t"] >= T_SETTLE + T_RAMP
    slope = float(np.polyfit(r["t"][w], r["x"][w], 1)[0])
    node = terrain.GetNodeInfo(ch.ChVector3d(0.0, 0.0, 0.0))
    out = {
        "case": {k: v for k, v in case.items() if not k.startswith("_")},
        "place_process": place,
        "wall_s": wall, "us_per_step": wall / n_steps * 1e6,
        "m_share_kg": m_share, "pad_area_m2": area,
        "settle_end": {"z_pad_bottom_mm": float(r["z_pad"][r["t"] <= T_SETTLE][-1] * 1e3),
                       "Fz_N": float(r["Fz"][r["t"] <= T_SETTLE][-1])},
        "hold": {
            "drift_velocity_m_s": slope,
            "x_at_ramp_end_mm": float(r["x"][hold][0] * 1e3), "x_end_mm": float(r["x"][-1] * 1e3),
            "drift_10s_mm": float((r["x"][-1] - r["x"][hold][0]) * 1e3),
            "Fx_mean_N": float(r["Fx"][w].mean()), "Fz_mean_N": float(r["Fz"][w].mean()),
            "Fx_step_min_N": float(r["Fx_min"][w].min()), "Fx_step_max_N": float(r["Fx_max"][w].max()),
            "ax_step_min_m_s2": float(r["ax_min"][w].min()), "ax_step_max_m_s2": float(r["ax_max"][w].max()),
            "sign_flips_per_s": float(r["flips"][w].sum() / (r["t"][w][-1] - r["t"][w][0] + 1e-3)),
            "tilt_y_deg_mean": float(r["tilt_y_deg"][w].mean()),
            "tilt_y_deg_ptp": float(np.ptp(r["tilt_y_deg"][w])),
            "z_pad_change_mm": float((r["z_pad"][-1] - r["z_pad"][hold][0]) * 1e3),
            "y_drift_mm": float((r["y"][-1] - r["y"][hold][0]) * 1e3),
        },
        "node_centre_end": {"kshear_m": node.kshear, "tau_Pa": node.tau, "sigma_Pa": node.sigma,
                            "sinkage_mm": node.sinkage * 1e3},
        "userdata": userdata,
        "series_1ms": {k: [float(v) for v in r[k][::10]] for k in ("t", "x", "Fx", "Fz", "tilt_y_deg")},
    }
    return out


def cases() -> list[dict]:
    out = []
    a35, a55 = math.radians(3.5), math.radians(5.5)
    # batch 2: SCM shear law with the pad rotation locked (fixed joint)
    for soil_key in ("G1", "J1"):
        for variant in ("cad330", "dwg_rear250"):
            for tag, F in (("F0", 0.0), ("slope3.5", N_REAR * math.sin(a35)), ("slope5.5", N_REAR * math.sin(a55)),
                           ("internal20k", 20e3)):
                out.append(dict(name=f"fix_{soil_key}_{variant}_RL_{tag}", soil=soil_key, variant=variant, leg="RL",
                                N=N_REAR, F=F, dt=1e-4, pad_joint="fixed"))
    for dt in (5e-5, 2.5e-5):
        out.append(dict(name=f"fix_J1_dwg_rear250_RL_slope3.5_dt{dt:g}", soil="J1", variant="dwg_rear250", leg="RL",
                        N=N_REAR, F=N_REAR * math.sin(a35), dt=dt, pad_joint="fixed"))
    out.append(dict(name="fix_G1_dwg_rear250_RL_slope3.5_dt5e-05", soil="G1", variant="dwg_rear250", leg="RL",
                    N=N_REAR, F=N_REAR * math.sin(a35), dt=5e-5, pad_joint="fixed"))
    # batch 2: swivel stability (spherical joint) on the stiff set and on the front pad
    for variant in ("cad330", "dwg_rear250"):
        out.append(dict(name=f"sph_G1_{variant}_RL_F0", soil="G1", variant=variant, leg="RL", N=N_REAR, F=0.0,
                        dt=1e-4))
    out.append(dict(name="sph_J1_cad330_RL_F0", soil="J1", variant="cad330", leg="RL", N=N_REAR, F=0.0, dt=1e-4))
    out.append(dict(name="sph_J1_cad330_FL_F0", soil="J1", variant="cad330", leg="FL", N=N_FRONT, F=0.0, dt=1e-4))
    out.append(dict(name="sph_G1_cad330_FL_slope5.5", soil="G1", variant="cad330", leg="FL", N=N_FRONT,
                    F=N_FRONT * math.sin(a55), dt=1e-4))
    # batch 1 (already run, kept for reproduction)
    out.append(dict(name="J1_dwg_rear250_RL_shear_off_slope3.5", soil="J1", variant="dwg_rear250", leg="RL",
                    N=N_REAR, F=N_REAR * math.sin(a35), dt=1e-4, shear_off=True))
    out.append(dict(name="J1_dwg_rear250_RL_shear_off_F0", soil="J1", variant="dwg_rear250", leg="RL",
                    N=N_REAR, F=0.0, dt=1e-4, shear_off=True))
    out.append(dict(name="J1_dwg_rear250_RL_F0", soil="J1", variant="dwg_rear250", leg="RL",
                    N=N_REAR, F=0.0, dt=1e-4))
    out.append(dict(name="J1_dwg_rear250_RL_userdata_slope3.5", soil="J1", variant="dwg_rear250", leg="RL",
                    N=N_REAR, F=N_REAR * math.sin(a35), dt=1e-4, userdata=True))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only", default="")
    ap.add_argument("--names", default="", help="comma-separated exact case names")
    ap.add_argument("--t-end", type=float, default=T_END)
    ap.add_argument("--out", default=str(ROOT / "06_analysis" / "01_chrono" / "19_S9" / "scm_pad_lateral_probe.json"))
    a = ap.parse_args()
    names = [n for n in a.names.split(",") if n]
    cs = [c for c in cases() if (c["name"] in names if names else a.only in c["name"])]
    for c in cs:
        c["t_end"] = a.t_end
    t0 = time.perf_counter()
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    res = []
    with get_context("spawn").Pool(min(a.jobs, len(cs))) as pool:
        for r in pool.imap_unordered(run_case, cs, chunksize=1):   # write after every case (partial results kept)
            res.append(r)
            out = {"doc": "00_docs/01_dynamics/dynamics_model.md 5.33 (rev. 47)",
                   "script": "04_scripts/02_chrono/scm_pad_lateral_probe.py",
                   "frame": "world = body axes, x fwd (load direction), z up; SCM plane z = 0; gravity (0,0,-9.80665)",
                   "wall_total_s": time.perf_counter() - t0, "n_done": len(res), "n_cases": len(cs), "cases": res}
            p.write_text(json.dumps(out, indent=1), encoding="utf-8")
            print("done", r["case"]["name"], round(r["wall_s"], 1), flush=True)
    for r in res:
        h = r["hold"]
        print(f"{r['case']['name']:44s} v={h['drift_velocity_m_s']:.3e} m/s  drift10={h['drift_10s_mm']:8.3f} mm  "
              f"Fx={h['Fx_mean_N']:9.1f} [{h['Fx_step_min_N']:9.1f},{h['Fx_step_max_N']:9.1f}]  "
              f"ax=[{h['ax_step_min_m_s2']:.2f},{h['ax_step_max_m_s2']:.2f}]  flips/s={h['sign_flips_per_s']:.0f}  "
              f"tilt={h['tilt_y_deg_mean']:.3f}  us/step={r['us_per_step']:.0f}  ud={r['userdata']}")


if __name__ == "__main__":
    main()
