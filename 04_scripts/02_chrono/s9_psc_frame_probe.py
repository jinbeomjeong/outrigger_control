"""PS-c feasibility probe on SCM (D-1 C-3, cad 2026-11-08): lowering an SCM terrain's reference frame mid-run.

The production mechanism is ``run_S9.SoilEventDriver`` (A1 / ``--soil-event``): before every step the reference frame
of the event leg's own SCM terrain moves along the plane normal by ``-d P345((t - t_ev) / T)``
(``SCMTerrain::SetReferenceFrame``, SCMTerrain.cpp:110; node levels, sinkage, plastic sinkage and yield stress are
frame-relative, SCMTerrain.h:422, and the ray grid / active-domain range are re-transformed with ``m_frame`` every step,
SCMTerrain.cpp:956 / 1178). This probe drives that very class on the single-pad layout of ``run_S9.build_single_pad``
(project pad body + hull, swivel joint under a 'share' body, anchor bushing, J1 1 cm grid, 4 SCM threads) and checks:

* ``a`` (light pad, constant load): the pad bottom follows the lowered reference surface (criterion +-0.1 mm on
  ``(z_bottom - z_bottom(t_ev)) + offset``);
* ``b_rigid`` (design load, settled, share body then held by a 1e9 N/m spring = near-rigid leg): load drop per mm of
  frame lowering = the SCM elastic unloading slope ``K A`` (J1 K 2e8 Pa/m x pad area; front type B 0.1071 m2 =
  21.4 kN/mm) in series with 1e9 N/m (21.0 kN/mm), +-10 %;
* ``b_series`` (design load, settled, share then held by a vertical spring ``k_leg`` = YAML L1 ``kn_per_pad`` of the leg,
  explicit force on the share body, damping ratio 0.7 on the share mass): load drop per mm = ``1 / (1/(K A) + 1/k_leg)``,
  +-10 %;
* in every mode: plastic sinkage / yield stress of the nodes under the pad unchanged by the frame move (max |change|),
  ray hits / contact patches, Python warnings, wall per step with and without the frame calls.

Usage (Chrono-dev, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_psc_frame_probe.py a|b_rigid|b_series [--leg FL] [--soil J1]

Writes ``06_analysis/01_chrono/19_S9/psc_frame_probe/<mode>_<soil>_<leg>.json``. Units SI (mm in the summary keys
named ``*_mm``). World z up, SCM plane z = 0 at the start.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import run_S9 as r9  # noqa: E402

OUT = ROOT / "06_analysis" / "01_chrono" / "19_S9" / "psc_frame_probe"
DT_S = 1.0e-4
GRID_M = {"J1": 0.01, "J2": 0.01, "G1": 0.02, "S1": 0.02}
"""P3b pad grids (``run_S9.P3B_PAD_GRID_M``)."""
LIGHT_LOAD_N = 10.0e3
"""Mode a: ASSUMPTION 'unloaded' pad = 10 kN (about F_min 9.4 kN); n 0.13 soils bounce at very light loads."""
MODES = {
    # mode: (load, load ramp [s], extra hold [s] or None = 5 tau, depth [m], ramp [s], hold after [s])
    "a": ("light", 1.0, 1.0, 0.010, 1.3, 0.4),  # 10 mm / 1.3 s: P345 peak 14.4 mm/s (c-fast 14.1 mm/s)
    "b_rigid": ("design", 1.0, None, 0.002, 1.0, 0.4),
    "b_series": ("design", 1.0, None, 0.002, 1.0, 0.6),
}
LOCK_HOLD_S = 0.3
SERIES_ZETA = 0.7
K_RIGID_N_M = 1.0e9
"""b_rigid: near-rigid leg = explicit share spring 1e9 N/m (about 47 x K A; omega dt 0.03 on the share mass). A fixed
share (SetFixed) with the share-ground mate made SparseLU singular (zero diagonal), so the rigid case uses this spring
and its own series expectation."""
TRACK_TOL_M = 1.0e-4
SLOPE_TOL = 0.10


def node_probe(terrain, outline_world: np.ndarray, grid: float) -> dict:
    """Node records at the grid points at least one grid inside the pad outline (convex polygon)."""
    import pychrono as ch

    poly = outline_world[:, :2]
    c = poly.mean(axis=0)
    inner = c + (poly - c) * (1.0 - 1.5 * grid / np.max(np.linalg.norm(poly - c, axis=1)))
    lo, hi = inner.min(axis=0), inner.max(axis=0)
    xs = np.arange(math.ceil(lo[0] / grid), math.floor(hi[0] / grid) + 1) * grid
    ys = np.arange(math.ceil(lo[1] / grid), math.floor(hi[1] / grid) + 1) * grid
    nxt = np.roll(inner, -1, axis=0)
    pts = []
    for x in xs:
        for y in ys:
            cross = (nxt[:, 0] - inner[:, 0]) * (y - inner[:, 1]) - (nxt[:, 1] - inner[:, 1]) * (x - inner[:, 0])
            if np.all(cross >= 0) or np.all(cross <= 0):
                pts.append((x, y))
    rows = []
    for x, y in pts:
        ni = terrain.GetNodeInfo(ch.ChVector3d(float(x), float(y), 0.0))
        rows.append((ni.sinkage, ni.sinkage_plastic, ni.sinkage_elastic, ni.sigma, ni.sigma_yield))
    return {"n": len(rows), "arr": np.asarray(rows, float)}


def outline_world(m) -> np.ndarray:
    import pychrono as ch

    pad = m["pad"]
    return np.array([[v.x, v.y, v.z] for v in (pad.TransformPointLocalToParent(ch.ChVector3d(*map(float, p)))
                                                for p in m["outline_local_m"])])


def run(mode: str, soil_name: str, leg: str) -> dict:
    import pychrono as ch

    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.chrono.system import gravity_vector, set_gravity
    from outrigger_sim.params import LEG_ORDER

    placement = r9.place()
    load_kind, load_ramp, hold, depth, ramp, hold_after = MODES[mode]
    params, pv, soil = r9.load_inputs(SimpleNamespace(level="top", pad_variant="dwg_rear250", soil=soil_name,
                                                      soil_override=None, fs_kN=0.0))
    i = LEG_ORDER.index(leg)
    n_load = LIGHT_LOAD_N if load_kind == "light" else float(soil.design_loads_N[i])
    grid = GRID_M[soil_name]
    m = r9.build_single_pad(params, pv, soil, leg=leg, shear="bprime", joint="spherical", k_sw=1.5e4,
                            stiffness_mode="series", interface=False, grid_m=grid, dt_s=DT_S, normal_load_N=n_load,
                            ray_shape="mesh", num_threads=r9.SCM_THREADS_FIXED)
    s, pad, share, terrain, reader, bushing, swivel = (m[k] for k in ("system", "pad", "share", "terrain", "reader",
                                                                      "bushing", "swivel"))
    area = float(pv["pad_bottom_area_m2"][leg])
    k_soil = float(soil.chrono["elastic_K"])
    ka = k_soil * area
    k_leg = float(params.get(f"contact.rigid_floor.L1.kn_per_pad_N_m.{leg}"))
    if hold is None:  # settle hold = max(1 s, 5 tau) of the virgin branch at the full load (run_S9.bekker_tau_s)
        outline = m["outline_local_m"][:, :2]
        on = np.roll(outline, -1, axis=0)
        a_out = float(0.5 * abs(np.sum(outline[:, 0] * on[:, 1] - on[:, 0] * outline[:, 1])))
        b_out = 2.0 * a_out / float(np.sum(np.hypot(*(on - outline).T)))
        tau = r9.bekker_tau_s(soil, area, b_out, n_load, False)
        hold = max(1.0, math.ceil(5.0 * tau * 10.0 - 1e-9) / 10.0)
    else:
        tau = None
    t_lock = load_ramp + hold
    locked = mode != "a"
    t_ev = t_lock + (LOCK_HOLD_S if locked else 0.0)
    t_end = t_ev + ramp + hold_after
    driver = r9.SoilEventDriver(terrain, (0.0, 0.0, 0.0), np.eye(3), depth, ramp)
    g_vec = np.asarray(gravity_vector(params), float)
    m_share = float(share.GetMass())
    k_hold = K_RIGID_N_M if mode == "b_rigid" else k_leg
    c_series = 2.0 * SERIES_ZETA * math.sqrt(k_hold * m_share)
    z_lock = None
    n_steps = round(t_end / DT_S)
    k_lock, k_ev = round(t_lock / DT_S), round(t_ev / DT_S)
    rec = {k: [] for k in ("t", "z_bottom", "offset", "Fz_scm", "share_z", "spring_N", "ray_hits", "patches")}
    wall_step = np.zeros(n_steps)
    wall_driver = 0.0
    nodes_before = None
    caught: list[str] = []
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        for k in range(n_steps):
            t = k * DT_S
            set_gravity(s, gravity_ramp_factor(t, load_ramp, "poly345") * g_vec)
            if k == k_lock and locked:
                z_lock = float(share.GetPos().z)
            if k == k_ev:
                nodes_before = node_probe(terrain, outline_world(m), grid)
                driver.set_event_time(t_ev)
            f_up = 0.0
            if z_lock is not None:
                f_up = k_hold * (z_lock - share.GetPos().z) - c_series * share.GetPosDt().z
            m["fload"].SetForce(ch.ChVector3d(0.0, 0.0, f_up), False)
            w0 = time.perf_counter()
            s.DoStepDynamics(DT_S)
            reader.refresh()
            if bushing is not None:
                bushing.after_step(DT_S)
            if swivel is not None:
                swivel.update(bushing.in_contact if bushing is not None else np.array([reader.pad_force_N[0, 2] > 100.0]),
                              float(s.GetChTime()))
            w1 = time.perf_counter()
            driver.update(float(s.GetChTime()))  # frame of the next step (production order: after the step)
            w2 = time.perf_counter()
            wall_step[k] = w2 - w0
            wall_driver += w2 - w1
            if (k + 1) % 10 == 0:
                rec["t"].append((k + 1) * DT_S)
                rec["z_bottom"].append(pad.GetPos().z - m["above"])
                rec["offset"].append(driver.offset_m)
                rec["Fz_scm"].append(float(reader.pad_force_N[0, 2]))
                rec["share_z"].append(float(share.GetPos().z))
                rec["spring_N"].append(f_up)
                rec["ray_hits"].append(int(terrain.GetNumRayHits()))
                rec["patches"].append(int(terrain.GetNumContactPatches()))
        caught = [f"{w.category.__name__}: {w.message}" for w in wlist]
    nodes_after = node_probe(terrain, outline_world(m), grid)
    r = {k: np.asarray(v, float) for k, v in rec.items()}
    ev = r["t"] >= t_ev - 1e-12
    pre = (r["t"] >= t_ev - 0.1) & (r["t"] < t_ev)
    end = r["t"] >= t_end - 0.1 - 1e-12
    z_ev = float(np.mean(r["z_bottom"][pre]))
    f_ev = float(np.mean(r["Fz_scm"][pre]))
    out: dict = {
        "probe": "D-1 C-3 PS-c frame lowering (run_S9.SoilEventDriver on the single-pad layout)",
        "mode": mode, "soil": soil_name, "leg": leg, "pad_variant": "dwg_rear250", "grid_m": grid, "dt_s": DT_S,
        "scm_threads": r9.SCM_THREADS_FIXED, "placement": placement,
        "normal_load_N": n_load, "load_kind": load_kind, "load_ramp_s": load_ramp, "settle_hold_s": hold,
        "virgin_tau_s": tau, "t_lock_s": t_lock if locked else None, "t_ev_s": t_ev, "t_end_s": t_end,
        "frame_profile": {"depth_m": depth, "ramp_s": ramp, "shape": "P345", "peak_speed_m_s": 1.875 * depth / ramp},
        "driver": driver.meta(),
        "values": {"elastic_K_Pa_m": k_soil, "pad_area_m2": area, "KA_N_m": ka, "k_leg_N_m": k_leg,
                   "k_series_N_m": 1.0 / (1.0 / ka + 1.0 / k_leg), "share_mass_kg": m_share,
                   "series_damping_N_s_m": c_series if mode == "b_series" else None},
        "before_event": {"z_bottom_mm": z_ev * 1e3, "Fz_scm_N": f_ev, "Fz_over_load": f_ev / n_load},
    }
    if mode == "a":
        err = (r["z_bottom"][ev] - z_ev) + r["offset"][ev]
        out["check_a"] = {"rule": "pad bottom follows the lowered surface: |(z_bottom - z_bottom(t_ev)) + offset| "
                                  f"<= {TRACK_TOL_M * 1e3:g} mm over t >= t_ev (constant load)",
                          "max_abs_err_mm": float(np.max(np.abs(err)) * 1e3),
                          "end_err_mm": float(np.mean(err[end[ev]]) * 1e3),
                          "offset_end_mm": float(r["offset"][-1] * 1e3),
                          "Fz_end_over_load": float(np.mean(r["Fz_scm"][end]) / n_load),
                          "pass": bool(np.max(np.abs(err)) <= TRACK_TOL_M)}
    else:
        f_end = float(np.mean(r["Fz_scm"][end]))
        drop = f_ev - f_end
        expect = 1.0 / (1.0 / ka + 1.0 / k_hold)
        slope = drop / depth
        fit = (r["offset"] > 0.2e-3) & (r["offset"] < 1.0e-3) & ev
        fit_slope = (float(-np.polyfit(r["offset"][fit], r["Fz_scm"][fit], 1)[0]) if np.count_nonzero(fit) > 5
                     else None)
        out["check_b"] = {"rule": f"load drop per frame metre (end hold mean vs pre-event mean) within "
                                  f"+-{SLOPE_TOL:.0%} of 1/(1/KA + 1/k_hold), k_hold = "
                          f"{'1e9 N/m (near-rigid leg)' if mode == 'b_rigid' else 'k_leg'}",
                          "k_hold_N_m": k_hold, "KA_alone_N_per_mm": ka * 1e-3,
                          "expected_N_per_mm": expect * 1e-3, "drop_N": drop, "depth_mm": depth * 1e3,
                          "slope_N_per_mm": slope * 1e-3, "rel_err": slope / expect - 1.0,
                          "fit_slope_0.2_1mm_N_per_mm": None if fit_slope is None else fit_slope * 1e-3,
                          "fit_note": "during the ramp (share inertia / damping lag included); the judged value is the "
                                      "end-hold chord",
                          "share_drop_mm": float((z_lock - r["share_z"][-1]) * 1e3) if z_lock is not None else None,
                          "pass": bool(abs(slope / expect - 1.0) <= SLOPE_TOL)}
    nb, na = nodes_before["arr"], nodes_after["arr"]
    contact_b = nb[:, 3] > 0.0
    out["plastic_memory"] = {
        "rule": "node sinkage_plastic / sigma_yield under the pad before t_ev vs the run end (frame-relative records)",
        "n_nodes_probe": nodes_before["n"], "n_nodes_contact_before": int(np.count_nonzero(contact_b)),
        "contact_area_nodes_m2": float(np.count_nonzero(contact_b) * grid * grid),
        "sinkage_plastic_mean_before_mm": float(np.mean(nb[:, 1]) * 1e3),
        "sinkage_plastic_max_abs_change_mm": float(np.max(np.abs(na[:, 1] - nb[:, 1])) * 1e3),
        "sigma_yield_mean_before_Pa": float(np.mean(nb[:, 4])),
        "sigma_yield_max_abs_change_Pa": float(np.max(np.abs(na[:, 4] - nb[:, 4]))),
        "sigma_mean_before_Pa": float(np.mean(nb[:, 3])), "sigma_mean_after_Pa": float(np.mean(na[:, 3])),
        "unchanged": bool(np.max(np.abs(na[:, 1] - nb[:, 1])) <= 1e-9
                          and np.max(np.abs(na[:, 4] - nb[:, 4])) <= 1e-3 * max(1.0, float(np.max(nb[:, 4]))))}
    pre_w, ev_w = wall_step[: round(t_ev / DT_S)], wall_step[round(t_ev / DT_S): round((t_ev + ramp) / DT_S)]
    out["ray"] = {"ray_hits_pre": int(np.mean(r["ray_hits"][pre])), "ray_hits_end": int(np.mean(r["ray_hits"][end])),
                  "patches_pre": int(np.max(r["patches"][pre])), "patches_end": int(np.max(r["patches"][end])),
                  "window": "SCM ray test +0.1 m / -0.5 m along the frame normal (SCMLoader defaults), pad active "
                            "domain height 0.40 m (scm_model.ACTIVE_DOMAIN_HEIGHT_M)"}
    out["python_warnings"] = caught
    out["cost"] = {"wall_s": float(np.sum(wall_step)), "steps": n_steps,
                   "us_per_step_before_event": float(np.mean(pre_w[len(pre_w) // 2:]) * 1e6),
                   "us_per_step_during_ramp": float(np.mean(ev_w) * 1e6),
                   "driver_update_us_per_step": wall_driver / n_steps * 1e6,
                   "driver_frame_calls": driver.n_updates,
                   "us_per_frame_call": wall_driver / max(1, driver.n_updates) * 1e6}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{mode}_{soil_name}_{leg}.json"
    path.write_text(json.dumps(out, indent=1, default=float), "utf-8")
    np.savez_compressed(path.with_suffix(".npz"), **r)
    print(json.dumps({k: out.get(k) for k in ("check_a", "check_b", "plastic_memory", "ray", "cost",
                                              "python_warnings")}, indent=1, default=float))
    print(path)
    return out


def main(argv) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=tuple(MODES))
    ap.add_argument("--soil", default="J1", choices=tuple(GRID_M))
    ap.add_argument("--leg", default="FL", choices=("FL", "FR", "RL", "RR"))
    a = ap.parse_args(argv)
    run(a.mode, a.soil, a.leg)


if __name__ == "__main__":
    main(sys.argv[1:])
