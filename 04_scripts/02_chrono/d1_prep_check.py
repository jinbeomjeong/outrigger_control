"""D-1 Chrono row preparation checks (cad 2026-11-08; short runs only, no levelling).

* ``c1``: crawler x3 (U6, ``run_S6C.crawler_k_overrides``) -- analytic static pose and linear modes of the x3 crawler
  (``scenarios/crawler_settle``) against the dynamics expectations (u_z -1.27 mm +-5 %, 12 active spheres, heave
  14.0 Hz +-10 %), the x3 crawler material / bushing values, and a 5 s L1-R Chrono settle on the flat floor from the x3
  analytic pose (``s6_stage2.build_crawler_model`` = the snapshot build path): COG drift, active spheres, sphere normal
  sum, heave frequency after a 2 % gravity pulse of 20 ms.
* ``c2``: V0 of the L2b D-1 C2 model (``run_S8C.build_l2b``, middle / bottom, every d1c2 floor builds): superstructure
  body mass, COG (body frame) and inertia about the COG against YAML ``superstructure.auger_levels.<level>``.
* ``c4``: the S-03 / S-04 argv (auger level + ``--soil-patch FL:J1``) through ``run_S9.build_machine``: triple layout,
  patch leg, patch soil, superstructure V0 of the level.

Usage (Chrono-dev, project root): ``python -I -X utf8 -u 04_scripts/02_chrono/d1_prep_check.py c1|c2|c4``.
Writes ``06_analysis/01_chrono/{16_S6,18_S8,19_S9}/d1_<check>.json``. Units SI.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

OUT = ROOT / "06_analysis" / "01_chrono"
EXPECT_C1 = {"u_z_m": -1.27e-3,  # mean active-sphere compression (W / (12 kn)); the origin u_z differs by the pitch
             "u_z_tol": 0.05, "active": 12, "heave_Hz": 14.0, "heave_tol": 0.10}
"""d1_dynamics_check.md 3.1 / 6 C-1 (dynamics-expert independent statics)."""


def _plain(v):
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, np.ndarray):
        return _plain(v.tolist())
    if isinstance(v, np.generic):
        return v.item()
    return v


def body_v0(body, com_body, params) -> dict:
    mp = params.superstructure.mass_properties
    xx, xy = body.GetInertiaXX(), body.GetInertiaXY()  # (Ixx, Iyy, Izz), (Ixy, Ixz, Iyz) about the COG
    inertia = np.array([[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z], [xy.y, xy.z, xx.z]])
    i_yaml = np.asarray(mp.inertia_kg_m2, float)
    m = float(body.GetMass())
    return {"mass_kg": m, "mass_yaml_kg": float(mp.mass_kg), "mass_rel": m / float(mp.mass_kg) - 1.0,
            "com_body_m": list(map(float, com_body)), "com_yaml_m": list(map(float, mp.com_m)),
            "com_abs_diff_m": float(np.max(np.abs(np.asarray(com_body, float) - np.asarray(mp.com_m, float)))),
            "inertia_rel_max": float(np.max(np.abs(inertia - i_yaml)) / np.max(np.abs(i_yaml))),
            "ok_1e-9": bool(abs(m / float(mp.mass_kg) - 1.0) <= 1e-9
                            and np.max(np.abs(inertia - i_yaml)) <= 1e-9 * np.max(np.abs(i_yaml))
                            and np.max(np.abs(np.asarray(com_body, float) - np.asarray(mp.com_m, float))) <= 1e-12),
            "basis": "Chrono superstructure body (COG frame) vs YAML superstructure.auger_levels.<level>; inertia "
                     "about the COG, body axes (x fwd, y left, z up)"}


def check_c1() -> dict:
    import pychrono as ch

    import run_S6C as s6
    import s6_stage2 as st
    from outrigger_sim.chrono.contact import crawler_material_values
    from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values
    from outrigger_sim.chrono.system import set_gravity
    from outrigger_sim.hostcpu import place_process
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.crawler_settle import crawler_linear_modes, crawler_static_pose

    placed = place_process("pcore")
    out: dict = {"check": "D-1 C-1 crawler x3", "placement": placed, "levels": {}}
    for level in ("top", "bottom"):
        base = load_params(level=level)
        over = s6.crawler_k_overrides(level, s6.D1C1_FACTOR)
        p3 = load_params(level=level, overrides=over)
        rows = {}
        for tag, p in (("x1", base), ("x3", p3)):
            pose = crawler_static_pose(p)
            modes = crawler_linear_modes(p, pose)
            pen = pose.sphere_penetration_m[pose.active]
            rows[tag] = {"u_z_mm": pose.u_z_m * 1e3, "mean_active_compression_mm": float(np.mean(pen)) * 1e3,
                         "W_over_kn_total_mm": pose.weight_N / (pose.kn_per_sphere_N_m * int(pose.active.sum())) * 1e3,
                         "pitch_deg": pose.pitch_deg, "roll_deg": pose.roll_deg,
                         "active": int(pose.active.sum()), "kn_float32_N_m": pose.kn_per_sphere_N_m,
                         "modes_Hz": dict(zip(modes.names, map(float, modes.f_undamped_Hz))),
                         "zeta": dict(zip(modes.names, map(float, modes.zeta)))}
        heave3 = rows["x3"]["modes_Hz"]["heave"]
        u3 = -rows["x3"]["mean_active_compression_mm"] * 1e-3  # dynamics u_z = mean crawler compression
        cmv1, cmv3 = crawler_material_values(base), crawler_material_values(p3)
        bv1, bv3 = crawler_bushing_values(base), crawler_bushing_values(p3)
        out["levels"][level] = {
            "overrides": over, "analytic": rows,
            "expect": EXPECT_C1 if level == "top" else "top only (dynamics 3.1); bottom recorded",
            "analytic_pass": None if level != "top" else bool(
                abs(u3 / EXPECT_C1["u_z_m"] - 1.0) <= EXPECT_C1["u_z_tol"]
                and rows["x3"]["active"] == EXPECT_C1["active"]
                and abs(heave3 / EXPECT_C1["heave_Hz"] - 1.0) <= EXPECT_C1["heave_tol"]),
            "material_x1": _plain(getattr(cmv1, "__dict__", str(cmv1))),
            "material_x3": _plain(getattr(cmv3, "__dict__", str(cmv3))),
            "bushing_x1": _plain(bv1.meta()), "bushing_x3": _plain(bv3.meta()),
            "ratios_x3_over_x1": {"kn": float(np.float32(over[s6.CRAWLER_KN_KEY]))
                                  / float(np.float32(base.get(s6.CRAWLER_KN_KEY))),
                                  "gn": over[s6.CRAWLER_GN_KEY] / float(base.get(s6.CRAWLER_GN_KEY)),
                                  "bushing_kt": bv3.kt_N_m / bv1.kt_N_m, "bushing_ct": bv3.ct_N_s_m / bv1.ct_N_s_m},
        }
    # Chrono: 5 s on the flat floor from the x3 analytic pose (top), the snapshot build path without the ramp
    level = "top"
    p3 = load_params(level=level, overrides=s6.crawler_k_overrides(level, s6.D1C1_FACTOR))
    model, pose = st.build_crawler_model(p3, "flat", attach=True)
    sup = model.superstructure
    g = np.array([0.0, 0.0, -p3.meta.gravity_m_s2])
    dt = model.dt_s
    n = round(5.0 / dt)
    pulse = (round(1.0 / dt), round(1.02 / dt))
    z0 = float(sup.GetPos().z)
    zs, ts = [], []
    set_gravity(model.system, tuple(g))
    w0 = time.perf_counter()
    for k in range(n):
        if k == pulse[0]:
            set_gravity(model.system, tuple(1.02 * g))
        if k == pulse[1]:
            set_gravity(model.system, tuple(g))
        model.step()
        zs.append(float(sup.GetPos().z))
        ts.append((k + 1) * dt)
    wall = time.perf_counter() - w0
    z = np.asarray(zs) - z0
    t = np.asarray(ts)
    pre = (t > 0.5) & (t < 1.0)
    post = (t > pulse[1] * dt) & (t < pulse[1] * dt + 0.6)
    zp = z[post] - np.mean(z[(t > 4.0)])
    sgn = np.signbit(zp)
    cross = np.flatnonzero(sgn[1:] != sgn[:-1])
    f_heave = None if len(cross) < 4 else float((len(cross) - 1) / 2.0 / (t[post][cross[-1]] - t[post][cross[0]]))
    normals = np.asarray(model.crawler_normals())
    out["chrono_top_flat"] = {
        "start": "x3 analytic crawler_slope_pose (flat), crawler bushings attached, full gravity at t = 0",
        "cog_z_drift_0.5_1s_mm": float(np.mean(z[pre]) * 1e3),
        "cog_z_drift_end_mm": float(np.mean(z[t > 4.0]) * 1e3),
        "pulse": "gravity x1.02 for 20 ms at t = 1 s",
        "heave_Hz_zero_crossings": f_heave,
        "active_spheres_end": int(np.count_nonzero(normals > 1.0)),
        "sphere_normal_sum_N": float(normals.sum()),
        "weight_N": float(pose.weight_N) if hasattr(pose, "weight_N") else None,
        "wall_s": wall, "steps": n, "us_per_step": wall / n * 1e6}
    c = out["chrono_top_flat"]
    c["pass"] = bool(abs(c["cog_z_drift_end_mm"]) <= 0.05 * abs(EXPECT_C1["u_z_m"]) * 1e3
                     and c["active_spheres_end"] == EXPECT_C1["active"]
                     and f_heave is not None and abs(f_heave / EXPECT_C1["heave_Hz"] - 1.0) <= EXPECT_C1["heave_tol"])
    c["pass_rule"] = ("end COG drift from the analytic pose <= 5 % of |u_z| (0.064 mm), 12 active spheres, heave "
                      "14.0 Hz +-10 %")
    return out


def check_c2() -> dict:
    import run_S8C as s8

    out: dict = {"check": "D-1 C-2 L2b V0", "cases": {}}
    for c in s8.case_set("d1c2"):
        model, patches, params, params_ctrl, over, plant_meta, start = s8.build_l2b(c)
        out["cases"][c.case_id] = {"level": c.scenario.level, "floor": c.floor, "floor_deg": s8.st.FLOORS[c.floor],
                                   "fs_kN": c.fs_kN, "overrides": sorted(over),
                                   "v0": body_v0(model.superstructure, model.sup_com_body_m, params)}
    out["all_v0_ok"] = all(v["v0"]["ok_1e-9"] for v in out["cases"].values())
    return out


def check_c4() -> dict:
    import run_S9 as r9
    import s9_batch as sb

    rows = [r for r in sb.batches()["D1-CHRONO"] if r["d1_id"] in ("S-03", "S-04")]
    out: dict = {"check": "D-1 C-4 auger level + soil patch", "rows": {}}
    for row in rows:
        argv = row["argv"][len(sb.RUN):] + ["--case", row["case"], "--out-root", "X"]
        a = r9.build_parser().parse_args(argv)
        params, pv, soil = r9.load_inputs(a)
        model = r9.build_machine(a, params, pv, soil)
        out["rows"][row["case"]] = {
            "level": a.level, "soil": a.soil, "soil_patch": a.soil_patch,
            "terrains": len(model.terrains), "layout": model.terrain_meta.get("layout"),
            "soil_patch_leg": model.soil_patch_leg, "soil_patch_set": getattr(model.soil_patch_set, "key", None),
            "patch_is_leg_terrain": model.pad_terrain_by_leg[0] is model.terrains[2],
            "v0": body_v0(model.superstructure, getattr(model, "sup_com_body_m",
                                                       params.superstructure.mass_properties.com_m), params)}
    out["ok"] = all(r["layout"] == "triple" and r["soil_patch_leg"] == "FL" and r["patch_is_leg_terrain"]
                    and r["v0"]["ok_1e-9"] for r in out["rows"].values())
    return out


def main(argv) -> None:
    what = argv[0]
    fn, folder = {"c1": (check_c1, "16_S6"), "c2": (check_c2, "18_S8"), "c4": (check_c4, "19_S9")}[what]
    doc = _plain(fn())
    path = OUT / folder / f"d1_{what}_check.json"
    path.write_text(json.dumps(doc, indent=1, default=str), "utf-8")
    print(json.dumps(doc, indent=1, default=str)[:6000])
    print(path)


if __name__ == "__main__":
    main(sys.argv[1:])
