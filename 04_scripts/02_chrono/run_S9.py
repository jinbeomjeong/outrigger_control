"""S9 SCM soft-soil runner: single-pad (P1 / V16), machine settle and lift (P2 / P3a), C2 levelling (P3b).

``00_docs/03_chrono/chrono_build_plan.md`` S9; ``dynamics_model.md`` 5.32.7 #3, 5.33.7 items 1-9,
5.33.9 (P1-L1 ... L6), 5.33.11; ``s6_control_spec.md`` 284 (P3 keys), 287 (cad row). Model
``outrigger_sim.chrono.scm_model`` (machine) and :func:`build_single_pad` here (P1).

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py plan
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py single-pad --soil G1 --pad-variant dwg_rear250 \
        --leg RL --force 4450 --t-settle 2 --t-end 5 [--scm-shear bprime|native] [--joint spherical|fixed]
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py machine --soil G1 [--gravity-ramp 3 --gravity-hold 2] [--lift-s 0]
        [--crawler-grid 0.04]   # dual terrain (U-S9G-1 M14s: pads on --grid, crawler on --crawler-grid)
    python -I -X utf8 -u 04_scripts/02_chrono/run_S9.py level --soil G1 --approved ...   # P3b, gated

Options common to the SCM runs: ``--soil {J1,J2,G1,S1}`` (``02_params/scm_soil_sets.json``),
``--pad-variant {cad330,dwg_rear250}``, ``--scm-shear {bprime,native}`` (U-S9L-1: bprime =
judgement, native = comparison only), ``--stiffness-mode {series,l1_kt,janosi}`` (U-S9L-2),
``--interface`` (U-S9L-3 sensitivity), ``--k-sw`` (U-S9L-4, 0 = off), ``--grid``, ``--dt``,
``--soil-override KEY=VALUE`` (sensitivities of 5.32.4, e.g. ``elastic_K=7e8``), ``--ray-shape
{mesh,convex}`` (SCM ray targets; mesh = default, P1-V0 5.34.10), ``--crawler-grid`` (dual terrain).

Load ramps (dynamics 5.34.2 / 5.34.3): ``machine`` and ``level`` settle with the gravity magnitude
Poly345 over ``--gravity-ramp`` 3 s and hold ``--gravity-hold`` 2 s (``--gravity-ramp-shape step``
= the former sudden gravity); ``single-pad`` ramps the vertical load (gravity on pad + share body)
Poly345 over ``--load-ramp`` 1 s. Single pad records the SCM nodes inside the pad bottom polygon
(``GetNodeInfo``: contact nodes, node mean sinkage, node - geometric) every 0.1 s and the P1-L6
diagnostics in ``hold.p1_l6``; ``level`` adds the P3 record values (``p3_records``, 5.34.6).

``level`` (P3b) needs ``--approved`` (the user confirms the main runs) and refuses while the
controller has no ``soil`` settings (C2 soil response, control spec rev. 57 285, python-expert);
``--allow-current-c2`` overrides that for a deliberate current-C2 run (expected to fail on J1 B,
J2 B, S1: 281).

Outputs ``07_results/S9/<action>_<tag>_<stamp>/`` (``result.json`` + ``series.npz``). Units SI;
world = body axes at the start, x forward, y left, z up; gravity (0, 0, -9.80665).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

RESULTS = ROOT / "07_results" / "S9"
G = 9.80665
RECORD_S = 1.0e-3
"""Series sampling (every step is too much for the SCM node queries)."""
NODE_SINKAGE_EVERY_S = 0.1
CRAWLER_SETTLE_S = 5.0
"""Machine crawler settle before a lift: gravity Poly345 3 s + hold 2 s (dynamics 5.34.2 P2 rule;
``--gravity-ramp`` / ``--gravity-hold``; the former default was 3 s of sudden gravity)."""

# --- P1 ... P3 case plan (dynamics 5.33.9, 3.11.4; control spec 284) ---------------------------------

P1_COST_US_PER_STEP = 600.0
"""Single pad on SCM, 2 cm (smoke 2026-10-26: 511-626 us/step, P-cores shared with R1-R3)."""
MACHINE_COST_US_PER_STEP = 15500.0
"""Machine on SCM, 2 cm grid, 4 SCM threads (smoke 2026-10-26, P-cores shared: 15.5 ms/step =
ray testing 4.1 + contact-patch flood fill 9.4 (serial) + rest; 1 thread 18.6 ms). The 3.11.4 #4
estimate (4 ms) did not count the patch search. 4 cm grid: 3.2 ms/step. Triangle-mesh ray targets
(2026-10-26, same load, P-cores shared with the main-tree regression): 4 cm 3.81 ms/step against
4.38 ms with the former convex shapes; 2 cm 18.9 ms/step (crawler only, 1 s settle)."""
MACHINE_COST_4CM_US_PER_STEP = 3200.0
SCM_THREADS_FIXED = 4
"""SCM ray-casting threads for every action (machine, single pad, level). Fixed (not the Chrono
default = all processors) because the OpenMP hit-merge order may depend on the thread count and
P3b layouts are compared by judgement values only (dynamics 5.34.12); = scm_model.SCM_THREADS.
Before 2026-10-26 (batch P1/P2) the single-pad action used the Chrono default."""


def case_plan() -> list[dict[str, Any]]:
    """P1 (5.33.9), P2 (5.32.7 #5), P3a / P3b (284) rows with simulated time and wall estimate."""
    rows: list[dict[str, Any]] = []

    def add(group, name, sim_s, kind, note=""):
        us = P1_COST_US_PER_STEP if kind == "single" else MACHINE_COST_US_PER_STEP
        us4 = P1_COST_US_PER_STEP if kind == "single" else MACHINE_COST_4CM_US_PER_STEP
        rows.append({"group": group, "case": name, "sim_s": sim_s, "kind": kind,
                     "wall_est_s": sim_s / 1e-4 * us * 1e-6,
                     "wall_est_4cm_grid_s": sim_s / 1e-4 * us4 * 1e-6, "note": note})

    for soil in ("J1", "G1"):
        for shear in ("native", "bprime_c0phi0"):
            add("P1-L1", f"L1_{soil}_fixed_F0_{shear}", 3.0, "single", "|F_t| = 0, settle diff <= 0.1 %")
    for soil in ("J1", "G1"):
        for F in (4450.0, 6980.0, 20000.0):
            add("P1-L2", f"L2_{soil}_B_RL_F{F:.0f}", 12.5, "single", "drift <= 0.01 mm, F_t = F +-0.5 %")
    for soil in ("J1", "J2"):
        add("P1-L3", f"L3_{soil}_B_RL_1.2limit", 7.5, "single", "F_t / limit = 1 +-2 %")
    for case in ("J1_B_RL", "J1_A_FL", "G1_B_RL", "J1_B_RL_ksw0"):
        add("P1-L4", f"L4_{case}_ramp20s", 22.0, "single", "tilt <= 0.5 deg (ksw0: instability record)")
    for soil in ("J1", "G1"):
        add("P1-L5", f"L5_{soil}_crawler_slope3.5", 13.0, "machine", "10 s drift <= 0.1 mm")
    for dt in ("1e-4", "5e-5"):
        add("P1-L6", f"L6_J1_B_native_dt{dt}", 7.5 * (2 if dt == "5e-5" else 1), "single",
            "drift F dt / M +-5 % (record)")
    for soil in ("J1", "J2", "G1", "S1"):
        add("P2", f"P2_{soil}_crawler_settle", 5.0, "machine", "A_c vs R rule +-10 %")
    for soil in ("J1", "G1"):
        for pad in ("A", "B"):
            add("P3a", f"P3a_{soil}_{pad}_lift_open_loop", 25.0, "machine", "lift V4-type, ~20 s")
    for soil in ("J1", "J2", "G1", "S1"):
        for pad in ("A", "B"):
            for lvl in ("top", "middle", "bottom"):
                add("P3b", f"P3b_{soil}_{pad}_{lvl}_Fs4", 93.0, "machine", "C2 levelling (284), after C2 soil")
    for soil in ("J1", "J2", "G1", "S1"):
        for pad in ("A", "B"):
            for fs in (0, 8):
                add("P3b", f"P3b_{soil}_{pad}_top_Fs{fs}", 93.0, "machine", "C2 levelling (284), after C2 soil")
    return rows


def plan_summary() -> dict[str, Any]:
    rows = case_plan()
    groups: dict[str, dict[str, float]] = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"cases": 0, "wall_serial_s": 0.0, "wall_max_case_s": 0.0})
        g["cases"] += 1
        g["wall_serial_s"] += r["wall_est_s"]
        g["wall_max_case_s"] = max(g["wall_max_case_s"], r["wall_est_s"])
        g["wall_serial_4cm_s"] = g.get("wall_serial_4cm_s", 0.0) + r["wall_est_4cm_grid_s"]
    return {"rows": rows, "groups": groups,
            "basis": f"single pad {P1_COST_US_PER_STEP:g} us/step, machine "
                     f"{MACHINE_COST_US_PER_STEP:g} us/step at dt 1e-4 s (ASSUMPTION, P-core, shared)"}


# --- common setup -------------------------------------------------------------------------------


def _soil_overrides(items) -> dict[str, float]:
    out = {}
    for item in items or ():
        k, v = item.split("=", 1)
        out[k.strip()] = float(v)
    return out


def load_inputs(args):
    from outrigger_sim.chrono.scm_model import load_soil_set
    from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta
    from outrigger_sim.params import load_params

    params = apply_pad_variant(load_params(level=args.level, model="L2b_NSC"), args.pad_variant)
    pv = pad_variant_meta(args.pad_variant, params=params)
    soil = load_soil_set(args.soil, overrides=_soil_overrides(args.soil_override))
    return params, pv, soil


def place():
    sys.path.insert(0, str(HERE / "solver_benchmark"))
    from step_cost_S0 import place_process  # noqa: PLC0415

    return place_process("pcore")


def out_dir(action: str, tag: str, root: str | None = None) -> Path:
    """``07_results/S9/<action>_<tag>_<stamp>/`` or, with ``root`` (batch folder), ``<root>/<tag>/``."""
    if root:
        d = Path(root) / tag
        d.mkdir(parents=True, exist_ok=True)
        return d
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    d = RESULTS / f"{action}_{tag}_{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return _plain(x.tolist())
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, Path):
        return x.as_posix()
    return x


# --- single pad (P1) --------------------------------------------------------------------------------


def build_single_pad(params, pv, soil, *, leg: str, shear: str, joint: str, k_sw: float,
                     stiffness_mode: str, interface: bool, grid_m: float, dt_s: float,
                     normal_load_N: float | None = None, ray_shape: str = "mesh", num_threads: int = 4,
                     terrain_size_m: tuple[float, float] = (1.2, 1.2)):
    """Single swivel pad (YAML pad body + pad hull) under a 'share' body (mass N/g - m_pad,
    translation free, rotation locked to the ground) on a level SCM plane z = 0 (the 5.33.2 probe
    layout with the project pad body, anchor bushing and swivel stabiliser)."""
    import pychrono as ch

    from outrigger_sim.chrono.ground_bushing import ADHESION_FULL_NORMAL_N, GroundBushingCoulomb, PadBushingSpec
    from outrigger_sim.chrono.scm_model import (
        PAD_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M, PadNormals, ScmForceReader, SwivelStabiliser,
        add_active_domain, add_pad_ray_mesh, initialize_terrain, make_terrain, pad_bottom_outline_local_m,
        pad_tangential_values, split_body_props)
    from outrigger_sim.chrono.sim_shapes import add_pad_hull
    from outrigger_sim.chrono.system import make_system
    from outrigger_sim.params import LEG_ORDER

    i = LEG_ORDER.index(leg)
    bundle = make_system(params, "L1", dt=dt_s, floor_plate=False)
    s, ground = bundle.system, bundle.floor
    if num_threads > 0:  # SCM ray casting = num_threads_chrono (CHANGELOG.md:502); fixed, not the Chrono default
        s.SetNumThreads(int(num_threads), 1, 1)
    m_p, c_p, i_p = split_body_props(params, i, "pad_body")
    above = float(params.get(f"legs.{leg}.pad_body.com_above_pad_bottom_m"))
    h_ball = float(params.legs[i].pad.swivel_center_above_pad_bottom_m)
    z0 = 0.0005  # pad bottom above the SCM plane at the start
    pad = ch.ChBody()
    pad.SetName(f"pad_{leg}")
    pad.SetMass(m_p)
    pad.SetInertiaXX(ch.ChVector3d(i_p[0, 0], i_p[1, 1], i_p[2, 2]))
    pad.SetInertiaXY(ch.ChVector3d(i_p[0, 1], i_p[0, 2], i_p[1, 2]))
    pad.SetPos(ch.ChVector3d(0.0, 0.0, z0 + above))
    pad.EnableCollision(True)
    # OBJ frame = machine body coordinates; pad COG at c_p there -> offset -c_p (pad at x = y = 0)
    if ray_shape == "mesh":
        add_pad_ray_mesh(pad, i, ch.ChContactMaterialSMC(), pad_variant=pv["pad_variant"], offset_m=-c_p)
    else:
        add_pad_hull(pad, params, i, ch.ChContactMaterialSMC(), pad_variant=pv["pad_variant"], offset_m=-c_p)
    s.Add(pad)
    N = soil.design_loads_N[i] if normal_load_N is None else float(normal_load_N)
    share = ch.ChBody()
    share.SetName("share")
    share.SetMass(N / G - m_p)
    share.SetInertiaXX(ch.ChVector3d(1e3, 1e3, 1e3))
    share.SetPos(ch.ChVector3d(0.0, 0.0, z0 + h_ball + 0.3))
    s.Add(share)
    ball = ch.ChVector3d(0.0, 0.0, z0 + h_ball)
    link = ch.ChLinkLockSpherical() if joint == "spherical" else ch.ChLinkLockLock()
    link.Initialize(pad, share, ch.ChFramed(ball, ch.QUNIT))
    s.Add(link)
    mate = ch.ChLinkMateGeneric(False, False, False, True, True, True)
    mate.Initialize(share, ground, ch.ChFramed(share.GetPos(), ch.QUNIT))
    s.Add(mate)
    loads = ch.ChLoadContainer()
    s.Add(loads)
    fload = ch.ChLoadBodyForce(share, ch.ChVector3d(0, 0, 0), False, ch.ChVector3d(0, 0, 0), True)
    loads.Add(fload)
    terrain, tmeta = make_terrain(s, soil, shear, (0.0, 0.0, 0.0), np.eye(3), grid_m=grid_m, size_m=tuple(terrain_size_m))
    # SCM grid indices are bounded by the size (SCMLoader::CheckMeshBounds, SCMTerrain.cpp:747): a sliding
    # pad (P1-L3) needs a long patch
    bottom_local = np.array([0.0, 0.0, -above])
    add_active_domain(terrain, tmeta, pad, bottom_local, (PAD_DOMAIN_XY_M, PAD_DOMAIN_XY_M, ACTIVE_DOMAIN_HEIGHT_M),
                      f"pad_{leg}")
    initialize_terrain(terrain, tmeta)
    reader = ScmForceReader(terrain, [pad], share)
    area = [float(pv["pad_bottom_area_m2"][lg]) for lg in LEG_ORDER]
    values = pad_tangential_values(params, soil, area, stiffness_mode=stiffness_mode, interface=interface)
    bushing = None
    normals = PadNormals(reader, np.array([0.0, 0.0, 1.0]))
    if shear == "bprime":
        spec = PadBushingSpec(name=leg, body=pad, sphere_centre_body_local_m=(0.0, 0.0, h_ball - above),
                              sphere_radius_m=h_ball, stiffness_N_m=values.stiffness_N_m[i],
                              damping_input_N_s_m=values.damping_input_N_s_m[i],
                              adhesion_N=values.adhesion_N[i])
        bushing = GroundBushingCoulomb(
            s, ground, [spec], friction=values.friction,
            slip_damping_reenable_speed_m_s=float(params.contact.rigid_floor.L1.slip_damping_reenable_speed_m_s),
            dt_s=bundle.dt_s, surface_point_floor_local_m=(0.0, 0.0, 0.0), normal_force_source=normals,
            adhesion_full_normal_N=ADHESION_FULL_NORMAL_N)
    swivel = (SwivelStabiliser(s, ground, [pad], np.eye(3), k_sw, [math.degrees(params.legs[i].pad.swivel_tilt_range_rad)])
              if (k_sw > 0.0 and joint == "spherical") else None)
    meta = {"bundle": bundle.meta(), "scm": tmeta, "pad_values": values.meta(), "leg": leg, "leg_index": i,
            "normal_load_N": N, "share_mass_kg": N / G - m_p, "pad_mass_kg": m_p, "joint": joint,
            "k_sw_N_m_rad": k_sw if swivel else 0.0, "pad_bottom_start_z_m": z0,
            "pad_area_m2": area[i], "frame": "world z up, SCM plane z = 0, load along +x", "ray_shape": ray_shape,
            "num_threads_chrono": int(num_threads)}
    outline = pad_bottom_outline_local_m(pv["pad_variant"], i, -c_p)
    obj_offset = float(outline[0, 2] + above)  # OBJ bottom - YAML bottom, pad COG frame z [m]
    meta["obj_bottom_minus_yaml_bottom_m"] = obj_offset
    return {"system": s, "pad": pad, "share": share, "terrain": terrain, "reader": reader, "bushing": bushing,
            "swivel": swivel, "fload": fload, "dt_s": bundle.dt_s, "above": above, "meta": meta,
            "limit_N": None if bushing is None else float(bushing.tangential_limit_N([N])[0]),
            "k_t_N_m": values.stiffness_N_m[i], "outline_local_m": outline, "grid_m": grid_m,
            "bundle": bundle, "obj_bottom_offset_m": obj_offset}


def single_pad_node_stats(m) -> dict[str, Any]:
    """SCM nodes inside the pad bottom polygon (P1-V0 (iii)): contact node count, node mean sinkage,
    geometric sinkage of the pad bottom (``-z_bottom``, YAML pad bottom) and their difference [m].
    ``sinkage_geometric_obj_m`` / ``node_minus_geometric_obj_m`` use the hull OBJ bottom instead
    (type A rear OBJ bottom is 0.044 mm below the YAML bottom, dynamics 5.34.10; type B 0.0 mm)."""
    from outrigger_sim.chrono.scm_model import node_stats_in_outline

    pad = m["pad"]
    import pychrono as ch

    world = np.array([[v.x, v.y, v.z] for v in (pad.TransformPointLocalToParent(ch.ChVector3d(*map(float, p)))
                                                 for p in m["outline_local_m"])])
    st = node_stats_in_outline(m["terrain"], (0.0, 0.0, 0.0), np.eye(3), m["grid_m"], world)
    geo = -(pad.GetPos().z - m["above"])
    geo_obj = geo - m["obj_bottom_offset_m"]
    st["sinkage_geometric_m"] = float(geo)
    st["sinkage_geometric_obj_m"] = float(geo_obj)
    sc = st["sinkage_mean_contact_m"]
    st["node_minus_geometric_m"] = None if sc is None else float(sc - geo)
    st["node_minus_geometric_obj_m"] = None if sc is None else float(sc - geo_obj)
    st["ray_hits"] = int(m["terrain"].GetNumRayHits())
    st["contact_patches"] = int(m["terrain"].GetNumContactPatches())
    return st


def bekker_tau_s(soil, area_m2: float, b_m: float, load_N: float, unloading: bool) -> float:
    """Settle time constant of a pad load level (dynamics 5.31.8): tau = R A / (dF/dz) on the
    virgin branch F = A (Kc/b + Kphi) z^n (dF/dz = n F / z), tau = R / K on unloading (elastic)."""
    c = soil.chrono
    if unloading:
        return c["damping_R"] / c["elastic_K"]
    k = c["Kc"] / b_m + c["Kphi"]
    z = (load_N / (area_m2 * k)) ** (1.0 / c["n"])
    return c["damping_R"] * area_m2 / (c["n"] * load_N / z)


def load_step_schedule(args, soil, area_m2: float, b_m: float, n_full_N: float) -> list[dict[str, Any]]:
    """Vertical load steps (P1-V16a-c): factors ``--load-steps``; the first ramp is ``--load-ramp``
    (Poly345 from 0), later ramps ``--step-ramp`` (Poly345 between levels); hold per level
    ``--step-hold`` [s] or 'auto' = max(1 s, 5 tau) rounded up to 0.1 s (dynamics 5.31.8 / 5.34.3)."""
    levels = [float(v) for v in args.load_steps.split(",")]
    holds_in = args.step_hold.split(",")
    rows, t, prev, peak = [], 0.0, 0.0, 0.0
    for k, f in enumerate(levels):
        ramp = args.load_ramp if k == 0 else args.step_ramp
        unloading = f < peak
        tau = bekker_tau_s(soil, area_m2, b_m, f * n_full_N, unloading)
        h = holds_in[min(k, len(holds_in) - 1)]
        hold = max(1.0, math.ceil(5.0 * tau * 10.0 - 1e-9) / 10.0) if h == "auto" else float(h)
        rows.append({"level": k, "factor": f, "from_factor": prev, "t_ramp_start_s": t, "ramp_s": ramp,
                     "t_hold_start_s": t + ramp, "hold_s": hold, "t_hold_end_s": t + ramp + hold,
                     "tau_est_s": tau, "unloading": unloading})
        t += ramp + hold
        prev, peak = f, max(peak, f)
    return rows


def load_step_factor(t_s: float, schedule: list[dict[str, Any]]) -> float:
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor

    for row in schedule:
        if t_s < row["t_hold_start_s"]:
            u = gravity_ramp_factor(t_s - row["t_ramp_start_s"], row["ramp_s"], "poly345")
            return row["from_factor"] + (row["factor"] - row["from_factor"]) * u
        if t_s < row["t_hold_end_s"]:
            return row["factor"]
    return schedule[-1]["factor"]


def run_single_pad(args) -> Path:
    import pychrono as ch

    placement = place()
    params, pv, soil = load_inputs(args)
    m = build_single_pad(params, pv, soil, leg=args.leg, shear=args.scm_shear, joint=args.joint, k_sw=args.k_sw,
                         stiffness_mode=args.stiffness_mode, interface=args.interface, grid_m=args.grid,
                         dt_s=args.dt, normal_load_N=args.normal_load, ray_shape=args.ray_shape,
                         num_threads=args.threads, terrain_size_m=tuple(args.terrain_size))
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.chrono.system import gravity_vector, set_gravity

    s, pad, share, reader, bushing, swivel = (m[k] for k in ("system", "pad", "share", "reader", "bushing", "swivel"))
    dt = m["dt_s"]
    if args.force_limit_factor is not None:  # P1-L3: horizontal load = factor x tangential limit at full load
        if m["limit_N"] is None:
            raise SystemExit("--force-limit-factor needs the anchor bushing (--scm-shear bprime)")
        args.force = float(args.force_limit_factor * m["limit_N"])
    schedule = None
    if args.load_steps:
        outline = m["outline_local_m"][:, :2]
        on = np.roll(outline, -1, axis=0)
        a_out = float(0.5 * abs(np.sum(outline[:, 0] * on[:, 1] - on[:, 0] * outline[:, 1])))
        b_out = 2.0 * a_out / float(np.sum(np.hypot(*(on - outline).T)))
        schedule = load_step_schedule(args, soil, m["meta"]["pad_area_m2"], b_out, m["meta"]["normal_load_N"])
        args.t_end = max(args.t_end, schedule[-1]["t_hold_end_s"])
        args.t_settle = max(args.t_settle, schedule[-1]["t_hold_end_s"])  # no horizontal load in a step run
    level_marks = {} if schedule is None else {round(r["t_hold_end_s"] / dt): ("end", r["level"]) for r in schedule}
    if schedule is not None:
        level_marks.update({round(r["t_hold_start_s"] / dt): ("start", r["level"]) for r in schedule})
    level_rows: dict[int, dict[str, Any]] = {}
    ft_scm_abs_max = 0.0
    n_steps = round(args.t_end / dt)
    every = max(1, round(RECORD_S / dt))
    node_every = max(1, round(NODE_SINKAGE_EVERY_S / dt))
    keys = ("t", "x", "y", "z_bottom", "tilt_deg", "Fx_scm", "Fy_scm", "Fz_scm", "Ft_bush_x", "N_bush", "slip_x",
            "Fx_step_min", "Fx_step_max", "g_factor", "omega_x", "omega_y", "omega_z", "v_t_com", "v_rot_rms")
    rec = {k: [] for k in keys}
    node_rows: list[dict[str, Any]] = []
    g_vec = np.asarray(gravity_vector(params), dtype=float)
    # bottom sample points for the node-velocity rotation share (P1-L6): polygon corners + centre
    r_local = np.vstack([m["outline_local_m"], m["outline_local_m"].mean(axis=0)])
    lo, hi = 1e30, -1e30
    t0 = time.perf_counter()
    for k in range(n_steps):
        t = k * dt
        if t < args.t_settle:
            fh = 0.0
        elif t < args.t_settle + args.t_ramp:
            fh = args.force * (t - args.t_settle) / args.t_ramp
        else:
            fh = args.force
        gf = (gravity_ramp_factor(t, args.load_ramp, args.load_ramp_shape) if schedule is None
              else load_step_factor(t, schedule))
        set_gravity(s, gf * g_vec)
        m["fload"].SetForce(ch.ChVector3d(fh, 0, 0), False)
        s.DoStepDynamics(dt)
        reader.refresh()
        ft_scm_abs_max = max(ft_scm_abs_max, float(np.hypot(reader.pad_force_N[0, 0], reader.pad_force_N[0, 1])))
        mark = level_marks.get(k + 1)
        if mark is not None:
            row = level_rows.setdefault(mark[1], {"level": mark[1]})
            row[mark[0]] = {"t_s": (k + 1) * dt, "factor": gf, "load_N": gf * m["meta"]["normal_load_N"],
                            "Fz_scm_N": float(reader.pad_force_N[0, 2]),
                            "z_bottom_m": float(pad.GetPos().z - m["above"]),
                            "nodes": single_pad_node_stats(m)}
        if bushing is not None:
            bushing.after_step(dt)
        if swivel is not None:
            swivel.update(bushing.in_contact if bushing is not None else np.array([reader.pad_force_N[0, 2] > 100.0]),
                          float(s.GetChTime()))
        ft_tot = reader.pad_force_N[0, 0] + (bushing.tangential_force_world_N()[0, 0] if bushing else 0.0)
        lo, hi = min(lo, ft_tot), max(hi, ft_tot)
        if (k + 1) % every == 0:
            p = share.GetPos()
            zax = pad.GetRot().GetAxisZ()
            rec["t"].append((k + 1) * dt)
            rec["x"].append(p.x)
            rec["y"].append(p.y)
            rec["z_bottom"].append(pad.GetPos().z - m["above"])
            rec["tilt_deg"].append(math.degrees(math.acos(max(-1.0, min(1.0, zax.z)))))
            rec["Fx_scm"].append(reader.pad_force_N[0, 0])
            rec["Fy_scm"].append(reader.pad_force_N[0, 1])
            rec["Fz_scm"].append(reader.pad_force_N[0, 2])
            rec["Ft_bush_x"].append(bushing.tangential_force_world_N()[0, 0] if bushing else 0.0)
            rec["N_bush"].append(float(bushing.normal_force_N[0]) if bushing else float(reader.pad_force_N[0, 2]))
            rec["slip_x"].append(float(bushing.slip_total_m[0, 0]) if bushing else 0.0)
            rec["Fx_step_min"].append(lo)
            rec["Fx_step_max"].append(hi)
            lo, hi = 1e30, -1e30
            rec["g_factor"].append(gf)
            w = pad.GetAngVelParent()
            om = np.array([w.x, w.y, w.z])
            v = pad.GetPosDt()
            rec["omega_x"].append(om[0])
            rec["omega_y"].append(om[1])
            rec["omega_z"].append(om[2])
            rec["v_t_com"].append(math.hypot(v.x, v.y))
            rot = pad.GetRotMat()
            rmat = np.array([[rot.GetAxisX().x, rot.GetAxisY().x, rot.GetAxisZ().x],
                             [rot.GetAxisX().y, rot.GetAxisY().y, rot.GetAxisZ().y],
                             [rot.GetAxisX().z, rot.GetAxisY().z, rot.GetAxisZ().z]])
            vr = np.cross(om, r_local @ rmat.T)[:, :2]  # tangential part of omega x r at the bottom points
            rec["v_rot_rms"].append(float(np.sqrt(np.mean(np.sum(vr ** 2, axis=1)))))
        if (k + 1) % node_every == 0:
            node_rows.append({"t_s": (k + 1) * dt, **single_pad_node_stats(m)})
    wall = time.perf_counter() - t0
    r = {k: np.asarray(v) for k, v in rec.items()}
    hold = r["t"] >= args.t_settle + args.t_ramp + 0.5
    settle = r["t"] <= args.t_settle
    ft_total = -(r["Fx_scm"] + r["Ft_bush_x"])  # ground force on the pad, -x when the load pushes +x
    summary: dict[str, Any] = {
        "action": "single-pad", "args": vars(args), "placement": placement, "wall_s": wall,
        "us_per_step": wall / n_steps * 1e6, "meta": m["meta"], "limit_N": m["limit_N"], "k_t_N_m": m["k_t_N_m"],
        "settle_end": {"z_bottom_mm": float(r["z_bottom"][settle][-1] * 1e3),
                       "sinkage_mm": float(-r["z_bottom"][settle][-1] * 1e3),
                       "Fz_scm_N": float(r["Fz_scm"][settle][-1]),
                       "Fz_over_weight": float(r["Fz_scm"][settle][-1] / m["meta"]["normal_load_N"]),
                       "tilt_deg": float(r["tilt_deg"][settle][-1]),
                       "x_mm": float(r["x"][settle][-1] * 1e3), "y_mm": float(r["y"][settle][-1] * 1e3)},
        "swivel": None if swivel is None else swivel.meta(),
        "bushing_events": None if bushing is None else {k: v.tolist() for k, v in bushing.event_table().items()},
        "load_schedule": {"vertical": {"shape": args.load_ramp_shape, "ramp_s": args.load_ramp,
                                       "how": "gravity factor on pad + share body (load = N x factor)"},
                          "horizontal": {"ramp_s": args.t_ramp, "start_s": args.t_settle, "force_N": args.force}},
        "first_step": {"first_record_t_s": float(r["t"][0]) if len(r["t"]) else None,
                       "first_record_Fz_scm_N": float(r["Fz_scm"][0]) if len(r["Fz_scm"]) else None},
        "node_series": node_rows,
        "force_N": args.force,
        "scm_tangential_abs_max_N": ft_scm_abs_max,
        "scm_tangential_abs_max_note": "max over every step of |(Fx, Fy)| of the SCM resultant on the pad (P1-L1)",
        "tilt_deg_max_all": float(r["tilt_deg"].max()) if len(r["tilt_deg"]) else None,
        "tilt_deg_end": float(r["tilt_deg"][-1]) if len(r["tilt_deg"]) else None,
        "z_bottom_end_mm": float(r["z_bottom"][-1] * 1e3) if len(r["z_bottom"]) else None,
        "Fz_scm_end_N": float(r["Fz_scm"][-1]) if len(r["Fz_scm"]) else None,
        "load_steps": None if schedule is None else {
            "schedule": schedule, "levels": [level_rows.get(row["level"]) for row in schedule]},
    }
    settle_nodes = [n for n in node_rows if n["t_s"] <= args.t_settle + 1e-9]
    if settle_nodes:
        summary["settle_end"]["nodes"] = settle_nodes[-1]
    if hold.any():
        th, xh = r["t"][hold], r["x"][hold]
        summary["hold"] = {
            "window_s": [float(th[0]), float(th[-1])],
            "drift_mm": float((xh[-1] - xh[0]) * 1e3),
            # ringing of the share mass on k_t decays slowly; drift judged on 0.5 s window means
            "drift_window_means_mm": float((xh[th >= th[-1] - 0.5].mean() - xh[th <= th[0] + 0.5].mean()) * 1e3),
            "x_window_means_mm": [float(xh[(th >= a) & (th < a + 0.5)].mean() * 1e3)
                                  for a in np.arange(th[0], th[-1] - 0.49, 0.5)],
            "drift_velocity_m_s": float(np.polyfit(th, xh, 1)[0]) if len(th) > 2 else None,
            "x_mean_mm": float(xh.mean() * 1e3),
            "elastic_expected_mm": None if not m["k_t_N_m"] else float(args.force / m["k_t_N_m"] * 1e3),
            "Ft_total_mean_N": float(ft_total[hold].mean()),
            "Ft_over_F": float(ft_total[hold].mean() / args.force) if args.force else None,
            "Ft_over_limit": float(ft_total[hold].mean() / m["limit_N"]) if m["limit_N"] else None,
            "Ft_over_limit_last_1s": (float(ft_total[hold & (r["t"] >= r["t"][-1] - 1.0)].mean() / m["limit_N"])
                                      if m["limit_N"] else None),
            "Ft_step_range_N": [float(-r["Fx_step_max"][hold].max()), float(-r["Fx_step_min"][hold].min())],
            "Fx_scm_abs_max_N": float(np.abs(r["Fx_scm"][hold]).max()),
            "tilt_deg_max": float(r["tilt_deg"][hold].max()),
            "sinkage_change_mm": float(-(r["z_bottom"][hold][-1] - r["z_bottom"][hold][0]) * 1e3),
            "slip_total_x_mm": float(r["slip_x"][-1] * 1e3),
            # P1-L6 diagnostics (dynamics 5.34.4 (ii)): pad angular velocity RMS and the rotation share
            # of the bottom-node slip velocity (|omega x r| tangential RMS over the polygon corners + centre)
            # against the translational (COM tangential) speed RMS; hypothesis: ratio >= 1 with drift
            "p1_l6": {
                "omega_rms_rad_s": [float(np.sqrt(np.mean(r[c][hold] ** 2))) for c in ("omega_x", "omega_y", "omega_z")],
                "v_rot_rms_m_s": float(np.sqrt(np.mean(r["v_rot_rms"][hold] ** 2))),
                "v_trans_rms_m_s": float(np.sqrt(np.mean(r["v_t_com"][hold] ** 2))),
                "rot_over_trans": (float(np.sqrt(np.mean(r["v_rot_rms"][hold] ** 2)) / np.sqrt(np.mean(r["v_t_com"][hold] ** 2)))
                                   if np.any(r["v_t_com"][hold] > 0) else None),
                "Fx_total_step_range_N": [float(r["Fx_step_min"][hold].min()), float(r["Fx_step_max"][hold].max())],
                "sampling": f"every {RECORD_S:g} s (record rate), hold window"},
        }
    tag = args.case or f"{args.soil}_{args.pad_variant}_{args.leg}_{args.scm_shear}_F{args.force:.0f}"
    d = out_dir("single", tag, args.out_root)
    np.savez(d / "series.npz", **r)
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps(_plain({k: summary.get(k) for k in ("settle_end", "first_step", "hold", "us_per_step",
                                                         "limit_N")}),
                     indent=1), flush=True)
    print("->", d, flush=True)
    return d


# --- machine (P2 / P3a) -------------------------------------------------------------------------------


def build_machine(args, params, pv, soil):
    from outrigger_sim.chrono.scm_model import S9Model
    from outrigger_sim.scenarios.slope import floor_normal

    normal = None if (args.floor_roll == 0.0 and args.floor_pitch == 0.0) else floor_normal(
        args.floor_roll, args.floor_pitch)
    return S9Model(params, soil, pv, shear=args.scm_shear, floor_normal=normal, dt_s=args.dt,
                   stiffness_mode=args.stiffness_mode, interface=args.interface,
                   swivel_stiffness_N_m_rad=args.k_sw, grid_m=args.grid, num_threads=args.threads,
                   ray_shape=args.ray_shape, crawler_grid_m=args.crawler_grid)


def settle_time_s(args) -> float:
    """Machine settle time: ``--t-settle`` or gravity ramp + hold (P2 rule 3 + 2 s)."""
    if args.t_settle is not None:
        return float(args.t_settle)
    ramp = 0.0 if args.gravity_ramp_shape == "step" else args.gravity_ramp
    return ramp + args.gravity_hold


def gravity_schedule_meta(args) -> dict[str, Any]:
    return {"shape": args.gravity_ramp_shape, "ramp_s": args.gravity_ramp, "hold_s": args.gravity_hold,
            "settle_s": settle_time_s(args),
            "rule": "dynamics_model.md 5.34.2 P2: |g| Poly345 3 s + hold 2 s, judge last 1 s mean"
                    if args.gravity_ramp_shape == "poly345" else "sensitivity / former sudden gravity"}


def settle_judgement(rows: list[dict[str, Any]], w_total: float, window_s: float = 1.0) -> dict[str, Any]:
    """P2 settle values over the last ``window_s`` (5.34.2): pitch / roll mean and p-p, origin z
    mean, SCM normal sum / weight (crawler + pads, along the plane normal)."""
    t_end = rows[-1]["t_s"]
    win = [r for r in rows if r["t_s"] >= t_end - window_s - 1e-12]
    pitch = np.array([r["roll_pitch_deg"][1] for r in win])
    roll = np.array([r["roll_pitch_deg"][0] for r in win])
    z = np.array([r["body_pos_m"][2] for r in win])
    x = np.array([r["body_pos_m"][0] for r in win])
    n_sum = np.array([r["scm_crawler_normal_N"] + float(np.sum(r["scm_pad_normal_N"])) for r in win])
    return {"window_s": [float(win[0]["t_s"]), float(t_end)], "pitch_mean_deg": float(pitch.mean()),
            "pitch_pp_deg": float(np.ptp(pitch)), "roll_mean_deg": float(roll.mean()), "roll_pp_deg": float(np.ptp(roll)),
            "z_origin_mean_mm": float(z.mean() * 1e3), "x_origin_pp_mm": float(np.ptp(x) * 1e3),
            "normal_over_weight": float(n_sum.mean() / w_total)}


def run_machine(args) -> Path:
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.frames import roll_pitch_from_quat

    placement = place()
    params, pv, soil = load_inputs(args)
    tb = time.perf_counter()
    model = build_machine(args, params, pv, soil)
    build_s = time.perf_counter() - tb
    dt = model.dt_s
    every = max(1, round(RECORD_S / dt))
    node_every = max(1, round(NODE_SINKAGE_EVERY_S / dt))
    w_total = (params.superstructure.mass_properties.mass_kg
               + sum(leg.moving_part.mass_kg for leg in params.legs)) * G
    rows: list[dict[str, Any]] = []
    node_rows: list[dict[str, Any]] = []
    t_settle = settle_time_s(args)
    t_settle_steps = round(t_settle / dt)
    t_lift_steps = round(args.lift_s / dt)
    v_lift = float(params.actuator.max_speed_m_s) * args.lift_speed_fraction
    rut = None
    first_step = None
    t0 = time.perf_counter()
    for k in range(t_settle_steps + t_lift_steps):
        if k == t_settle_steps:
            rut = model.mark_rut_reference()
            if t_lift_steps:
                model.set_command([v_lift] * 4)
        model.set_gravity_factor(gravity_ramp_factor(k * dt, args.gravity_ramp, args.gravity_ramp_shape))
        p = model.step(capture=((k + 1) % every == 0))
        if k == 0:
            first_step = {"gravity_factor": model.gravity_factor,
                          "scm_crawler_force_N": model.forces.sup_force_N.tolist(),
                          "scm_pad_force_N": model.forces.pad_force_N.tolist(),
                          "force_norm_max_N": float(np.linalg.norm(np.vstack([model.forces.sup_force_N,
                                                                              model.forces.pad_force_N]),
                                                                   axis=1).max())}
        if p is not None:
            row = model.s9_record()
            rp = roll_pitch_from_quat(p.body_quat_wxyz)
            row.update(body_pos_m=p.body_pos_m.tolist(), roll_pitch_deg=[math.degrees(a) for a in rp],
                       s_motor_m=p.motor_pos_m.tolist(), F_cyl_N=p.motor_force_N.tolist())
            rows.append(row)
        if (k + 1) % node_every == 0:
            node_rows.append({"t_s": float(model.system.GetChTime()), "pad_nodes": model.pad_node_stats()})
    wall = time.perf_counter() - t0
    if rut is None:  # settle only: reference at the end (clearance 0 by definition)
        rut = model.mark_rut_reference()
        rows[-1]["rut_clearance_m"] = model.rut_clearance_m()
    n_steps = t_settle_steps + t_lift_steps
    last = rows[-1]
    win = [r for r in rows if r["t_s"] >= rows[-1]["t_s"] - 0.1]
    crawler_n = float(np.mean([r["scm_crawler_normal_N"] for r in win]))
    pads_n = np.mean([r["scm_pad_normal_N"] for r in win], axis=0)
    total_n = crawler_n + float(np.sum(pads_n))
    summary = {
        "action": "machine", "args": vars(args), "placement": placement, "build_s": build_s, "wall_s": wall,
        "n_steps": n_steps, "us_per_step": wall / max(n_steps, 1) * 1e6,
        "meta": model.meta(), "rut_reference": rut,
        "end": {"t_s": last["t_s"], "roll_pitch_deg": last["roll_pitch_deg"], "body_pos_m": last["body_pos_m"],
                "window_s": 0.1, "scm_crawler_normal_mean_N": crawler_n, "scm_pad_normal_mean_N": pads_n.tolist(),
                "total_normal_N": total_n, "weight_N": w_total,
                "equilibrium_rel_error": (total_n - w_total) / w_total,
                "contact_patches": last["scm_contact_patches"], "track_normal_raw_N": last["scm_track_normal_raw_N"],
                "pad_sinkage_geometric_m": last["pad_sinkage_geometric_m"], "rut_clearance_m": last["rut_clearance_m"],
                "pad_tilt_deg": last["pad_tilt_deg"], "track_utilisation": last.get("track_utilisation"),
                "s_motor_m": last["s_motor_m"], "F_cyl_N": last["F_cyl_N"]},
        "node_sinkage": node_rows[-3:],
        "gravity_schedule": gravity_schedule_meta(args),
        "first_step": first_step,
        "start_rise": {"z_origin_max_mm": float(max(r["body_pos_m"][2] for r in rows) * 1e3),
                       "z_origin_start_mm": float(rows[0]["body_pos_m"][2] * 1e3)},
        "settle_last_1s": settle_judgement([r for r in rows if r["t_s"] <= t_settle + 1e-9], w_total)
        if t_settle >= 1.0 else None,
        "swivel": None if model.swivel is None else model.swivel.meta(),
        "pad_bushing_events": None if model.pad_bushing is None else {
            k: v.tolist() for k, v in model.pad_bushing.event_table().items()},
        "crawler_bushing_events": None if model.crawler_bushing is None else {
            k: v.tolist() for k, v in model.crawler_bushing.event_table().items()},
    }
    # P1-L5: origin drift over the last args.drift_window seconds of the settle (in the plane and
    # along the plane normal, world frame), and the track anchor slip
    settle_rows = [r for r in rows if r["t_s"] <= t_settle + 1e-9]
    if settle_rows and args.drift_window > 0.0 and settle_rows[-1]["t_s"] - settle_rows[0]["t_s"] >= args.drift_window:
        t_a = settle_rows[-1]["t_s"] - args.drift_window
        ra = min(settle_rows, key=lambda r: abs(r["t_s"] - t_a))
        rb = settle_rows[-1]
        dp = np.asarray(rb["body_pos_m"]) - np.asarray(ra["body_pos_m"])
        nrm = model.floor_normal_world()
        dn = float(dp @ nrm)
        dpl = dp - dn * nrm
        summary["settle_drift"] = {
            "window_s": [float(ra["t_s"]), float(rb["t_s"])], "d_origin_world_m": dp.tolist(),
            "d_in_plane_mm": float(np.linalg.norm(dpl) * 1e3), "d_normal_mm": float(dn * 1e3),
            "d_pitch_deg": float(rb["roll_pitch_deg"][1] - ra["roll_pitch_deg"][1]),
            "d_roll_deg": float(rb["roll_pitch_deg"][0] - ra["roll_pitch_deg"][0]),
            "criterion_mm": 0.1, "note": "P1-L5 (dynamics 5.33.9): 10 s drift <= 0.1 mm (in plane)"}
    summary["num_threads_chrono"] = model.num_threads
    grids = f"{args.grid * 100:g}cm" + ("" if args.crawler_grid is None else f"_c{args.crawler_grid * 100:g}cm")
    tag = args.case or (f"{args.soil}_{args.pad_variant}_{args.scm_shear}_{grids}_{args.gravity_ramp_shape}"
                        f"{args.gravity_ramp:g}_lift{args.lift_s:g}")
    d = out_dir("machine", tag, args.out_root)
    series = {key: np.asarray([r[key] for r in rows], dtype=float) for key in
              ("t_s", "scm_crawler_normal_N", "scm_pad_normal_N", "pad_sinkage_geometric_m", "body_pos_m",
               "roll_pitch_deg", "s_motor_m", "F_cyl_N", "scm_contact_patches", "body_omega_world_rad_s",
               "gravity_factor", "scm_ray_hits")}
    np.savez(d / "series.npz", **series)
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps(_plain({k: summary[k] for k in ("end", "first_step", "start_rise", "settle_last_1s",
                                                     "us_per_step", "build_s")}), indent=1), flush=True)
    print("->", d, flush=True)
    return d


# --- P3 record keys (dynamics 5.34.6) -------------------------------------------------------------------


def model_weight_N(params) -> float:
    return (params.superstructure.mass_properties.mass_kg + sum(leg.moving_part.mass_kg for leg in params.legs)) * G


P3_CRAWLER_OFF_FRACTION = 0.01
"""Crawler counted as departed when its SCM normal force < 1 % of the machine weight (record rule)."""
P3_HOLD_WINDOW_S = 10.0
TOUCH_TILT_ROWS = 10


def p3_records(rows: list[dict[str, Any]], weight_N: float) -> dict[str, Any]:
    """P3 record values from the 10 Hz S9 rows (dynamics 5.34.6 P3-S1 ... S4, crawler rocking, pad
    tilt). Records only: the Bekker prediction of P3-S1 (node formula of P1 V16a) and every pass /
    fail decision are dynamics-expert's. Node sinkage = mean of the contact nodes inside the pad
    polygon (``pad_node_stats``)."""
    if not rows:
        return {"rows": 0}
    t = np.array([r["t_s"] for r in rows])
    phase = [str(r.get("c2_phase")) for r in rows]
    rp = np.array([r["roll_pitch_deg"] for r in rows])
    crawler_n = np.array([r["scm_crawler_normal_N"] for r in rows])
    pad_n = np.array([r["scm_pad_normal_N"] for r in rows])

    def node_sink(r):
        return [np.nan if s["sinkage_mean_contact_m"] is None else s["sinkage_mean_contact_m"] for s in r["pad_nodes"]]

    sink = np.array([node_sink(r) for r in rows])
    out: dict[str, Any] = {"rows": len(rows), "basis": "10 Hz rows of run_S9 level; SI, deg for angles"}
    # crawler rocking at TOUCH: first 10 control periods of raw (truth) tilt
    touch = [k for k, p in enumerate(phase) if p == "touch"]
    if touch:
        k0 = touch[0]
        seg = rp[k0:k0 + TOUCH_TILT_ROWS]
        settle = rp[max(k0 - 1, 0)]
        out["touch_rocking"] = {"t_start_s": float(t[k0]), "roll_pp_deg": float(np.ptp(seg[:, 0])),
                                "pitch_pp_deg": float(np.ptp(seg[:, 1])),
                                "mean_minus_settle_deg": (seg.mean(axis=0) - settle).tolist(),
                                "note": "dynamics 5.34.6: ignore when <= 0.02 deg"}
    dep = np.nonzero(crawler_n < P3_CRAWLER_OFF_FRACTION * weight_N)[0]
    kd = int(dep[0]) if dep.size else None
    if kd is not None:
        f_loc = pad_n[kd]
        f_max = pad_n[kd:].max(axis=0)
        out["S1_after_departure"] = {"t_departure_s": float(t[kd]), "F_LOC_N": f_loc.tolist(), "F_max_N": f_max.tolist(),
                                     "dF_N": (f_max - f_loc).tolist(),
                                     "node_sinkage_departure_m": sink[kd].tolist(), "node_sinkage_end_m": sink[-1].tolist(),
                                     "dz_node_m": (sink[-1] - sink[kd]).tolist()}
        clear = [r["rut_clearance_m"] for r in rows[kd:] if r.get("rut_clearance_m") is not None]
        out["S4_rut_clearance"] = {"min_after_departure_m": float(min(clear)) if clear else None,
                                   "end_m": rows[-1].get("rut_clearance_m"),
                                   "pad_node_sinkage_end_m": sink[-1].tolist(), "criterion_m": 0.025}
    done = [k for k, p in enumerate(phase) if p == "done"]
    if done:
        kq = done[0]
        out["S3_attitude_after_done"] = {"t_done_s": float(t[kq]), "d_roll_deg": float(rp[-1, 0] - rp[kq, 0]),
                                         "d_pitch_deg": float(rp[-1, 1] - rp[kq, 1]), "criterion_deg": 0.03}
        hold = t >= t[-1] - P3_HOLD_WINDOW_S
        if t[-1] - t[kq] >= P3_HOLD_WINDOW_S:
            before = pad_n[:np.argmax(hold)].max(axis=0) if np.argmax(hold) > 0 else pad_n[0]
            out["S2_hold_settlement"] = {"window_s": [float(t[hold][0]), float(t[-1])],
                                         "dz_node_m": (sink[-1] - sink[hold][0]).tolist(),
                                         "F_max_in_window_N": pad_n[hold].max(axis=0).tolist(),
                                         "F_max_before_window_N": before.tolist(), "criterion_m_per_10s": 1e-4}
        else:
            out["S2_hold_settlement"] = {"note": f"less than {P3_HOLD_WINDOW_S:g} s after DONE"}
    tilt = [r.get("pad_tilt_max_deg") for r in rows if r.get("pad_tilt_max_deg") is not None]
    out["pad_tilt_max_deg"] = tilt[-1] if tilt else None
    out["pad_tilt_criterion_deg"] = 0.5
    return out


# --- C2 levelling (P3b), gated ------------------------------------------------------------------------


def run_level(args) -> Path:
    """C2 closed loop on the S9 model (P3b, control spec 284). Not run without ``--approved``."""
    if not args.approved:
        raise SystemExit("P3b C2 levelling is a main run: the user confirms it first (--approved)")
    from outrigger_sim.control.c2 import C2Config, C2Controller

    config = C2Config().with_10hz_d1()
    if getattr(config, "soil", None) is None and not args.allow_current_c2:
        raise SystemExit("C2 has no soil settings yet (control spec rev. 57 285, python-expert); the current C2 "
                         "is expected to fail on J1 B, J2 B, S1 (281). Use --allow-current-c2 to run it anyway")
    from outrigger_sim.chrono.scm_engine import S9Engine
    from outrigger_sim.params import load_params
    from outrigger_sim.record import make_run_meta, save_record
    from outrigger_sim.runner import run_closed_loop
    from outrigger_sim.sensors.hydraulic import LegSensorConfig
    from outrigger_sim.sensors.imu import imu_config_for_grade
    from outrigger_sim.sensors.suite import SensorSuite

    placement = place()
    params, pv, soil = load_inputs(args)
    params_ctrl = load_params(level=args.level)
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor

    model = build_machine(args, params, pv, soil)
    for k in range(round(settle_time_s(args) / model.dt_s)):
        model.set_gravity_factor(gravity_ramp_factor(k * model.dt_s, args.gravity_ramp, args.gravity_ramp_shape))
        model.step()
    model.set_gravity_factor(1.0)
    rut = model.mark_rut_reference()
    engine = S9Engine(model, imu_method="chrono_point")
    c2 = C2Controller.from_params(params_ctrl, config)
    suite = SensorSuite(imu_config_for_grade("G2", sample_period_s=0.01), LegSensorConfig(), seed=args.seed)
    soil_rows: list[dict[str, Any]] = []

    def observe(meas, command):  # 10 Hz S9 keys + C2 soil block when present
        from outrigger_sim.frames import roll_pitch_from_quat

        row = model.s9_record()
        row["c2_phase"] = str(getattr(c2, "phase", None))
        q = model.superstructure.GetRot()
        row["roll_pitch_deg"] = [math.degrees(a) for a in roll_pitch_from_quat(np.array([q.e0, q.e1, q.e2, q.e3]))]
        row["pad_nodes"] = model.pad_node_stats()
        soil_rows.append(row)

    run_meta = make_run_meta(params, engine.meta(), scenario=f"S9_P3b_{args.soil}_{args.pad_variant}",
                             scenario_settings={"args": vars(args), "rut_reference": rut}, sensors=suite.setup())
    res = run_closed_loop(engine, c2, suite, args.duration, run_meta=run_meta, on_control=observe,
                          command_delay_periods=0, placement=None)
    d = out_dir("level", f"{args.soil}_{args.pad_variant}_{args.level}")
    save_record(res.record, d / "record")
    ctl_meta = c2.meta()
    summary = {"action": "level", "args": vars(args), "placement": placement, "meta": engine.meta(),
               "c2_soil": ctl_meta.get("soil"), "s9_rows": soil_rows, "monitor": engine.step_monitor(),
               "events": [str(e) for e in c2.events], "gravity_schedule": gravity_schedule_meta(args),
               "p3_records": p3_records(soil_rows, model_weight_N(params))}
    (d / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), "utf-8")
    engine.close()
    print("->", d, flush=True)
    return d


# --- CLI ------------------------------------------------------------------------------------------------


def _common(p: argparse.ArgumentParser) -> None:
    from outrigger_sim.pad_variants import add_pad_variant_argument

    p.add_argument("--soil", choices=("J1", "J2", "G1", "S1"), default="G1")
    add_pad_variant_argument(p)
    p.add_argument("--level", choices=("top", "middle", "bottom"), default="top")
    p.add_argument("--scm-shear", choices=("bprime", "native"), default="bprime")
    p.add_argument("--stiffness-mode", choices=("series", "l1_kt", "janosi"), default="series")
    p.add_argument("--interface", action="store_true")
    p.add_argument("--k-sw", type=float, default=1.5e4)
    p.add_argument("--grid", type=float, default=0.02)
    p.add_argument("--dt", type=float, default=1.0e-4)
    p.add_argument("--soil-override", nargs="*")
    p.add_argument("--threads", type=int, default=SCM_THREADS_FIXED,
                   help=f"SCM ray-casting OpenMP threads (num_threads_chrono), fixed default {SCM_THREADS_FIXED} "
                        "for every S9 action (dynamics 5.34.12: P3b with one thread count); 0 = Chrono default "
                        "(all processors, comparison only)")
    p.add_argument("--case", default=None, help="case name (output folder name; batch runs)")
    p.add_argument("--out-root", default=None, help="batch folder: write to <out-root>/<case>/ instead of a stamp")
    p.add_argument("--ray-shape", choices=("mesh", "convex"), default="mesh",
                   help="SCM ray targets: static triangle meshes (default, P1-V0) or the former convex box / hull")
    p.add_argument("--crawler-grid", type=float, default=None,
                   help="dual terrain: crawler terrain grid [m] (pads on --grid); default one terrain")


def _gravity_ramp_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--t-settle", type=float, default=None,
                   help="settle time [s]; default gravity ramp + hold (P2 rule 3 + 2 s)")
    p.add_argument("--gravity-ramp", type=float, default=3.0, help="gravity ramp time [s] (5.34.2 P2)")
    p.add_argument("--gravity-hold", type=float, default=2.0, help="hold after the ramp [s]")
    p.add_argument("--gravity-ramp-shape", choices=("poly345", "linear", "step"), default="poly345",
                   help="step = the former sudden gravity (comparison only)")


def main(argv) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("plan")
    sp = sub.add_parser("single-pad")
    _common(sp)
    sp.add_argument("--leg", choices=("FL", "FR", "RL", "RR"), default="RL")
    sp.add_argument("--joint", choices=("spherical", "fixed"), default="spherical")
    sp.add_argument("--force", type=float, default=0.0, help="horizontal load +x on the share body [N]")
    sp.add_argument("--normal-load", type=float, default=None, help="default: design load of the leg")
    sp.add_argument("--t-settle", type=float, default=2.0, help="vertical load ramp + hold before the horizontal load")
    sp.add_argument("--t-ramp", type=float, default=0.5, help="horizontal load ramp [s]")
    sp.add_argument("--t-end", type=float, default=5.0)
    sp.add_argument("--load-ramp", type=float, default=1.0, help="vertical load (gravity) ramp [s] (5.34.3 P1-V0)")
    sp.add_argument("--load-ramp-shape", choices=("poly345", "linear", "step"), default="poly345",
                    help="step = the former sudden load (P1-V16d record only)")
    sp.add_argument("--load-steps", default=None,
                    help="vertical load factors, e.g. 0.25,0.5,0.75,1.0,0.5 (P1-V16a-c); replaces --load-ramp-shape")
    sp.add_argument("--step-ramp", type=float, default=0.5, help="Poly345 ramp between load steps [s]")
    sp.add_argument("--step-hold", default="auto",
                    help="hold per step [s], comma list or 'auto' = max(1 s, 5 tau) (dynamics 5.31.8)")
    sp.add_argument("--terrain-size", type=float, nargs=2, default=(1.2, 1.2),
                    help="SCM patch size x y [m] centred on the pad start (P1-L3 sliding: 6 1.2)")
    sp.add_argument("--force-limit-factor", type=float, default=None,
                    help="horizontal load = factor x anchor tangential limit at the full normal load (P1-L3)")
    mp = sub.add_parser("machine")
    _common(mp)
    _gravity_ramp_args(mp)
    mp.add_argument("--drift-window", type=float, default=10.0,
                    help="settle drift record over the last window [s] (P1-L5), when the settle is long enough")
    mp.add_argument("--lift-s", type=float, default=0.0, help="open-loop extension time after the settle")
    mp.add_argument("--lift-speed-fraction", type=float, default=1.0)
    mp.add_argument("--floor-roll", type=float, default=0.0)
    mp.add_argument("--floor-pitch", type=float, default=0.0)
    lp = sub.add_parser("level")
    _common(lp)
    _gravity_ramp_args(lp)
    lp.add_argument("--duration", type=float, default=90.0)
    lp.add_argument("--floor-roll", type=float, default=0.0)
    lp.add_argument("--floor-pitch", type=float, default=0.0)
    lp.add_argument("--seed", type=int, default=20261026)
    lp.add_argument("--approved", action="store_true")
    lp.add_argument("--allow-current-c2", action="store_true")
    args = ap.parse_args(argv)
    if args.action == "plan":
        print(json.dumps(_plain(plan_summary()), indent=1))
    elif args.action == "single-pad":
        run_single_pad(args)
    elif args.action == "machine":
        run_machine(args)
    else:
        run_level(args)


if __name__ == "__main__":
    main(sys.argv[1:])
