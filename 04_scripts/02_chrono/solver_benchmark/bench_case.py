"""One solver-benchmark case in its own process (driver: run_benchmark.py).

Usage: python -I -u bench_case.py <config.json>   (started by run_benchmark.py)
The config names the model ("l1", "scm", "grid", "chain"), the solver ("SPARSE_QR",
"SPARSE_LU", "PARDISO_MKL"), the sparsity lock flag, dt and step counts. MKL_NUM_THREADS is
set by the driver in this process environment only. Result JSON goes to config["out"].

Timing protocol: build -> warm-up (fixed step count, identical for all solvers so the state
after warm-up can be compared) -> `reps` timing windows of `steps` steps, wall clock only
(perf_counter around the loop, includes the Python bushing hook where present) -> one
profiling window of the same length that reads the per-step Chrono timers (they are reset
inside every DoStepDynamics) and the direct-solver timers (accumulated, reset before).
Units: SI; times reported in microseconds per step.

Crawler contact: the stored measurements in 07_results/solver_benchmark/ (and the summary
06_analysis/01_chrono/solver_benchmark.json) were taken with the old 2 x 9 crawler layout
(18 spheres, "n_crawler_spheres": 18 in every result). The builder now follows the current
YAML layout D (24 spheres: 12 rollers + 12 gapped end shoes, crawler_contact.py); the step
cost with layout D is measured again in the S0 cost measurement (not re-run here).
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I: the script folder is not on sys.path
import bench_common  # noqa: E402, F401  (side effect: 03_src and 04_scripts/00_cad on sys.path)
import numpy as np  # noqa: E402
import pychrono as ch  # noqa: E402
from crawler_contact import layout_from_params  # noqa: E402

from outrigger_sim.chrono.system import make_system  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

P = load_params()  # default auger level = top
G = P.meta.gravity_m_s2

TIMERS = ("Step", "Advance", "LSsetup", "LSsolve", "Setup", "Update", "Jacobian", "Collision")


def vec(v) -> list[float]:
    return [float(v.x), float(v.y), float(v.z)]


def new_system(cfg: dict, floor_plate: bool = True):
    b = make_system(P, "L1", dt=cfg["dt"], solver=cfg["solver"], floor_plate=floor_plate)
    ls = b.system.GetSolver().AsDirect()
    ls.LockSparsityPattern(bool(cfg.get("lock", False)))
    return b


def smc_material(kn: float, gn: float) -> ch.ChContactMaterialSMC:
    m = ch.ChContactMaterialSMC()
    m.SetKn(kn)
    m.SetGn(gn)
    m.SetKt(0.0)
    m.SetGt(0.0)
    m.SetFriction(0.0)
    m.SetRestitution(0.0)
    return m


def inertia_body(mass: float, inertia, pos) -> ch.ChBody:
    body = ch.ChBody()
    body.SetMass(mass)
    body.SetInertiaXX(ch.ChVector3d(inertia[0][0], inertia[1][1], inertia[2][2]))
    body.SetInertiaXY(ch.ChVector3d(inertia[0][1], inertia[0][2], inertia[1][2]))
    body.SetPos(ch.ChVector3d(*pos))
    return body


# --- full-scale L1 / SCM machine ---------------------------------------------------------


def build_machine(cfg: dict, scm: bool):
    """Superstructure (top level) + 4 leg moving parts on locked position motors.

    L1: pad spheres (SMC, YAML kn/gn), crawler spheres of the YAML layout D on the
    superstructure (contact.crawler.*: 12 roller spheres with the bottom on the floor + 12
    end-shoe spheres raised by end_shoe_gap_m, unilateral), ground bushings with Python
    circular Coulomb return mapping.
    SCM: no floor plate; pad = cylinder of the pad bottom area; SCM terrain under the machine.
    Levelled state: pads at the operating extension, pad bottoms at the floor, crawler 50 mm up.
    """
    b = new_system(cfg, floor_plate=not scm)
    s = b.system
    lift = P.simulation.crawler_clearance_m
    z_floor = P.ground.crawler_bottom_z_m
    mp = P.superstructure.mass_properties
    sup = inertia_body(mp.mass_kg, mp.inertia_kg_m2, np.array(mp.com_m) + [0, 0, lift])
    sup.SetName("superstructure")
    s.Add(sup)

    # crawler spheres (on the superstructure body)
    get = P.get
    layout = layout_from_params(P)
    yc = layout.track_centre_y_m
    x0, x1 = layout.x_extent_m
    rs = layout.sphere_radius_m
    cmat = smc_material(
        float(get("contact.crawler.kn_per_sphere_N_m")),
        float(get("contact.crawler.gn_per_sphere_1_s")),
    )
    sup.EnableCollision(True)
    com_sup = np.array(mp.com_m) + [0, 0, lift]
    for centre_world in layout.sphere_centres_m(z_floor, lift):
        centre = centre_world - com_sup
        sup.AddCollisionShape(
            ch.ChCollisionShapeSphere(cmat, rs), ch.ChFramed(ch.ChVector3d(*centre), ch.QUNIT)
        )

    l1 = P.contact.rigid_floor.L1
    legs, contact_pts = [], []
    for i, leg in enumerate(P.legs):
        e = l1.operating_extension_m[i]
        mpart = leg.moving_part
        com = np.array(mpart.com_m) + [0, 0, lift - e]
        body = inertia_body(mpart.mass_kg, mpart.inertia_kg_m2, com)
        body.SetName(f"leg_{leg.name}")
        pad_bottom = np.array(leg.pad_bottom_center_retracted_m) + [0, 0, lift - e]
        body.EnableCollision(True)
        if scm:
            r_eq = math.sqrt(leg.pad.bottom_area_m2 / math.pi)
            h = leg.pad.thickness_m
            # ChCollisionShapeCylinder axis is local z
            body.AddCollisionShape(
                ch.ChCollisionShapeCylinder(b.floor_material, r_eq, h),
                ch.ChFramed(ch.ChVector3d(*(pad_bottom + [0, 0, h / 2] - com)), ch.QUNIT),
            )
        else:
            r = leg.pad.swivel_center_above_pad_bottom_m
            mat = smc_material(l1.kn_per_pad_N_m[i], l1.gn_per_pad_1_s[i])
            body.AddCollisionShape(
                ch.ChCollisionShapeSphere(mat, r),
                ch.ChFramed(ch.ChVector3d(*(pad_bottom + [0, 0, r] - com)), ch.QUNIT),
            )
        s.Add(body)
        motor = ch.ChLinkMotorLinearPosition()
        att = np.array(leg.attachment_point_m) + [0, 0, lift]
        motor.Initialize(body, sup, ch.ChFramed(ch.ChVector3d(*att), ch.QuatFromAngleX(math.pi)))
        motor.SetMotionFunction(ch.ChFunctionConst(0.0))
        s.Add(motor)
        legs.append(body)
        contact_pts.append(pad_bottom)

    hook = None
    terrain = None
    if not scm:
        hook = make_bushing_hook(s, b.floor, legs, contact_pts)
    else:
        import pychrono.vehicle as veh

        terrain = veh.SCMTerrain(s, False)
        terrain.SetReferenceFrame(ch.ChCoordsysd(ch.ChVector3d(0.5, 0.0, z_floor), ch.QUNIT))
        sp = cfg["scm_params"]
        terrain.SetSoilParameters(
            sp["Kphi"],
            sp["Kc"],
            sp["n"],
            sp["cohesion_Pa"],
            sp["friction_deg"],
            sp["janosi_m"],
            sp["elastic_K"],
            sp["damping_R"],
        )
        if cfg.get("scm_domains", True):
            for body, pb in zip(legs, contact_pts, strict=True):
                centre = body.TransformPointParentToLocal(ch.ChVector3d(*pb))
                terrain.AddActiveDomain(body, centre, ch.ChVector3d(0.6, 0.6, 0.4))
            for y in (yc, -yc):  # crawler track strips (rays only where the tracks could touch)
                centre = sup.TransformPointParentToLocal(
                    ch.ChVector3d(0.5 * (x0 + x1), y, z_floor + lift)
                )
                terrain.AddActiveDomain(sup, centre, ch.ChVector3d(x1 - x0 + 0.4, 0.4, 0.4))
        terrain.Initialize(cfg["scm_size"][0], cfg["scm_size"][1], cfg["scm_delta"])
    total_mass = mp.mass_kg + sum(leg.moving_part.mass_kg for leg in P.legs)

    def state() -> dict:
        out = {
            "sup_pos_m": vec(sup.GetPos()),
            "sup_quat": [
                float(sup.GetRot().e0),
                float(sup.GetRot().e1),
                float(sup.GetRot().e2),
                float(sup.GetRot().e3),
            ],
            "sup_vel_m_s": vec(sup.GetPosDt()),
        }
        if scm:
            fz = []
            for body in legs:
                f, t = ch.ChVector3d(0, 0, 0), ch.ChVector3d(0, 0, 0)
                terrain.GetContactForceBody(body, f, t)
                fz.append(float(f.z))
            fs, ts = ch.ChVector3d(0, 0, 0), ch.ChVector3d(0, 0, 0)
            terrain.GetContactForceBody(sup, fs, ts)
            out["leg_fz_N"] = fz
            out["crawler_fz_N"] = float(fs.z)
            out["sum_fz_over_weight"] = (sum(fz) + float(fs.z)) / (total_mass * G)
            out["pad_sinkage_m"] = [
                z_floor - (float(body.GetPos().z) - (mpart_com_above(i)))
                for i, body in enumerate(legs)
            ]
        else:
            fz = [float(body.GetContactForce().z) for body in legs]
            crawler = float(sup.GetContactForce().z)
            out["leg_fz_N"] = fz
            out["crawler_fz_N"] = crawler
            out["sum_fz_over_weight"] = (sum(fz) + crawler) / (total_mass * G)
            out["bushing_slip_m"] = [float(np.linalg.norm(st["slip"])) for st in hook.states]
        return out

    def mpart_com_above(i: int) -> float:
        leg = P.legs[i]
        return leg.moving_part.com_m[2] - leg.pad_bottom_center_retracted_m[2]

    extra = {
        "total_mass_kg": total_mass,
        "n_crawler_spheres": layout.n_points,
        "crawler_layout_scheme": layout.scheme,
    }

    def scm_timers() -> dict:
        if terrain is None:
            return {}
        return {
            "active_domains": float(terrain.GetTimerActiveDomains()),
            "ray_testing": float(terrain.GetTimerRayTesting()),
            "ray_casting": float(terrain.GetTimerRayCasting()),
            "contact_patches": float(terrain.GetTimerContactPatches()),
            "contact_forces": float(terrain.GetTimerContactForces()),
            "bulldozing": float(terrain.GetTimerBulldozing()),
            "num_ray_casts": float(terrain.GetNumRayCasts()),
            "num_ray_hits": float(terrain.GetNumRayHits()),
            "num_contact_patches": float(terrain.GetNumContactPatches()),
        }

    return b, state, hook, extra, scm_timers, terrain


def make_bushing_hook(s, floor, legs, contact_pts):
    """Ground bushings (ChLoadBodyBodyBushingSpherical, A = leg, B = floor) at the pad contact
    points + circular Coulomb return mapping after each step (test_stick_friction.py convention;
    normal = world +z, N = pad contact force z)."""
    l1 = P.contact.rigid_floor.L1
    mu = P.contact.rigid_floor.friction
    v_stick = l1.slip_damping_reenable_speed_m_s
    lc = ch.ChLoadContainer()
    s.Add(lc)
    n = np.array([0.0, 0.0, 1.0])
    bushes, states = [], []
    for i, (body, cp) in enumerate(zip(legs, contact_pts, strict=True)):
        kt = l1.bushing_stiffness_per_pad_N_m[i]
        ct = l1.bushing_damping_input_per_pad_N_s_m[i]
        k3, c3 = ch.ChVector3d(kt, kt, 0.0), ch.ChVector3d(ct, ct, 0.0)
        bush = ch.ChLoadBodyBodyBushingSpherical(
            body, floor, ch.ChFramed(ch.ChVector3d(*cp), ch.QUNIT), k3, c3
        )
        lc.Add(bush)
        p0 = body.GetPos()
        bushes.append(bush)
        states.append(
            {
                "anchor": cp.copy(),
                "pA0": np.array([p0.x, p0.y, p0.z]),
                "cp": cp.copy(),
                "slip": np.zeros(3),
                "sliding": False,
                "kt": kt,
                "c3": c3,
            }
        )

    def hook():
        for body, bush, st in zip(legs, bushes, states, strict=True):
            f = body.GetContactForce()
            N = max(0.0, float(f.z))
            pos = body.GetPos()
            pA = st["cp"] + (np.array([pos.x, pos.y, pos.z]) - st["pA0"])
            d = pA - st["anchor"]
            d -= (d @ n) * n
            dn = float(np.linalg.norm(d))
            vel = body.GetPosDt()
            vt = math.hypot(vel.x, vel.y)
            if st["kt"] * dn > mu * N:
                move = d * (1.0 - mu * N / (st["kt"] * dn)) if dn > 0 else d
                st["anchor"] += move
                st["slip"] += move
                pl = floor.TransformPointParentToLocal(ch.ChVector3d(*st["anchor"]))
                bush.SetApplicationFrameB(ch.ChFramed(pl, ch.QUNIT))
                bush.SetDamping(ch.ChVector3d(0, 0, 0))
                st["sliding"] = True
            elif st["sliding"] and vt > v_stick:
                pass
            elif st["sliding"]:
                st["sliding"] = False
                bush.SetDamping(st["c3"])

    hook.states = states
    return hook


# --- synthetic scaling models ------------------------------------------------------------


def build_grid(cfg: dict):
    """N bodies on a near-square grid (1 m pitch). Each body: ChLinkMotorLinearPosition to the
    fixed floor (spherical guide: x, y locked, z driven by a phased sine 1 mm, 2 Hz), rotations
    free. Grid neighbours coupled by ChLoadBodyBodyBushingSpherical at the mid point (k 1e6 N/m,
    c 1e3 N s/m). Bushing Jacobians couple neighbours in the KKT matrix (2-D fill pattern)."""
    b = new_system(cfg, floor_plate=False)
    s = b.system
    N = int(cfg["N"])
    nx = int(math.ceil(math.sqrt(N)))
    m, a = 100.0, 0.5
    i_box = m * a * a / 6
    bodies = []
    lc = ch.ChLoadContainer()
    s.Add(lc)
    for k in range(N):
        ix, iy = k % nx, k // nx
        body = ch.ChBody()
        body.SetMass(m)
        body.SetInertiaXX(ch.ChVector3d(i_box, i_box * 1.1, i_box * 1.2))
        body.SetPos(ch.ChVector3d(ix * 1.0, iy * 1.0, 1.0))
        s.Add(body)
        motor = ch.ChLinkMotorLinearPosition()
        motor.SetGuideConstraint(ch.ChLinkMotorLinear.GuideConstraint_SPHERICAL)
        motor.Initialize(
            body, b.floor, ch.ChFramed(ch.ChVector3d(ix * 1.0, iy * 1.0, 1.0), ch.QUNIT)
        )
        motor.SetMotionFunction(ch.ChFunctionSine(1e-3, 2.0, 0.37 * k))
        s.Add(motor)
        bodies.append(body)
    kk, cc = ch.ChVector3d(1e6, 1e6, 1e6), ch.ChVector3d(1e3, 1e3, 1e3)
    n_bush = 0
    for k in range(N):
        ix, iy = k % nx, k // nx
        for j in (k + 1 if ix + 1 < nx else None, k + nx):
            if j is None or j >= N:
                continue
            pa, pb = bodies[k].GetPos(), bodies[j].GetPos()
            mid = ch.ChVector3d(0.5 * (pa.x + pb.x), 0.5 * (pa.y + pb.y), 1.0)
            lc.Add(
                ch.ChLoadBodyBodyBushingSpherical(
                    bodies[k], bodies[j], ch.ChFramed(mid, ch.QUNIT), kk, cc
                )
            )
            n_bush += 1

    def state() -> dict:
        q = np.array(
            [[float(bd.GetRot().e1), float(bd.GetRot().e2), float(bd.GetRot().e3)] for bd in bodies]
        )
        z = np.array([float(bd.GetPos().z) for bd in bodies])
        return {
            "z_m": z.tolist() if N <= 20 else None,
            "z_sum_m": float(z.sum()),
            "z_vec_digest": float(np.sum(z * np.arange(1, N + 1))),
            "quat_vec_abs_max": float(np.abs(q).max()),
            "_z": z.tolist(),
            "_q": q.ravel().tolist(),
        }

    return b, state, None, {"N": N, "nx": nx, "n_bushings": n_bush}, lambda: {}, None


def build_chain(cfg: dict):
    """N bodies in a horizontal chain (0.5 m links along x) joined by ChLinkLockSpherical at
    the link ends; body 0 spherical to the floor. Each body has a ground bushing at its COM
    (k 1e6 N/m, c 1e3 N s/m) and gravity acts (sag). Constraint Jacobians couple neighbours
    (banded pattern)."""
    b = new_system(cfg, floor_plate=False)
    s = b.system
    N = int(cfg["N"])
    m, L = 50.0, 0.5
    lc = ch.ChLoadContainer()
    s.Add(lc)
    bodies = []
    prev = b.floor
    for k in range(N):
        body = ch.ChBody()
        body.SetMass(m)
        body.SetInertiaXX(ch.ChVector3d(0.1, m * L * L / 12, m * L * L / 12 * 1.05))
        body.SetPos(ch.ChVector3d((k + 0.5) * L, 0.0, 1.0))
        s.Add(body)
        joint = ch.ChLinkLockSpherical()
        joint.Initialize(body, prev, ch.ChFramed(ch.ChVector3d(k * L, 0.0, 1.0), ch.QUNIT))
        s.Add(joint)
        lc.Add(
            ch.ChLoadBodyBodyBushingSpherical(
                body,
                b.floor,
                ch.ChFramed(ch.ChVector3d((k + 0.5) * L, 0.0, 1.0), ch.QUNIT),
                ch.ChVector3d(1e6, 1e6, 1e6),
                ch.ChVector3d(1e3, 1e3, 1e3),
            )
        )
        bodies.append(body)
        prev = body

    def state() -> dict:
        z = np.array([float(bd.GetPos().z) for bd in bodies])
        q = np.array(
            [[float(bd.GetRot().e1), float(bd.GetRot().e2), float(bd.GetRot().e3)] for bd in bodies]
        )
        return {
            "z_min_m": float(z.min()),
            "z_sum_m": float(z.sum()),
            "_z": z.tolist(),
            "_q": q.ravel().tolist(),
        }

    return b, state, None, {"N": N}, lambda: {}, None


# --- runner ------------------------------------------------------------------------------


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text())
    t_build0 = time.perf_counter()
    model = cfg["model"]
    if model == "l1":
        b, state, hook, extra, scm_timers, terrain = build_machine(cfg, scm=False)
    elif model == "scm":
        b, state, hook, extra, scm_timers, terrain = build_machine(cfg, scm=True)
    elif model == "grid":
        b, state, hook, extra, scm_timers, terrain = build_grid(cfg)
    elif model == "chain":
        b, state, hook, extra, scm_timers, terrain = build_chain(cfg)
    else:
        raise ValueError(model)
    s, dt = b.system, cfg["dt"]
    ls = s.GetSolver().AsDirect()
    build_s = time.perf_counter() - t_build0

    def step_n(n: int) -> float:
        t0 = time.perf_counter()
        if hook is None:
            for _ in range(n):
                s.DoStepDynamics(dt)
        else:
            for _ in range(n):
                s.DoStepDynamics(dt)
                hook()
        return time.perf_counter() - t0

    # warm-up (fixed count, the comparison state)
    w = int(cfg["warmup"])
    t_w = step_n(w)
    st_warm = state()
    # adaptive window length for the large synthetic cases
    steps = int(cfg["steps"])
    if cfg.get("target_s"):
        per = t_w / max(w, 1)
        steps = int(min(steps, max(cfg.get("min_steps", 50), cfg["target_s"] / max(per, 1e-9))))
    walls = [step_n(steps) / steps * 1e6 for _ in range(int(cfg["reps"]))]

    # profiling window
    acc = dict.fromkeys(TIMERS, 0.0)
    scm_acc: dict[str, float] = {}
    ls.ResetTimers()
    getters = [(name, getattr(s, f"GetTimer{name}")) for name in TIMERS]
    t0 = time.perf_counter()
    for _ in range(steps):
        s.DoStepDynamics(dt)
        if hook is not None:
            hook()
        for name, g in getters:
            acc[name] += g()
        if terrain is not None:
            for key, val in scm_timers().items():
                scm_acc[key] = scm_acc.get(key, 0.0) + val
    prof_wall = (time.perf_counter() - t0) / steps * 1e6
    prof = {k: v / steps * 1e6 for k, v in acc.items()}
    lsd = {
        "setup_assembly": ls.GetTimeSetup_Assembly() / steps * 1e6,
        "setup_solver_call": ls.GetTimeSetup_SolverCall() / steps * 1e6,
        "solve_assembly": ls.GetTimeSolve_Assembly() / steps * 1e6,
        "solve_solver_call": ls.GetTimeSolve_SolverCall() / steps * 1e6,
        "setup_calls": int(ls.GetNumSetupCalls()),
        "solve_calls": int(ls.GetNumSolveCalls()),
    }
    scm_per = {k: v / steps for k, v in scm_acc.items()}

    nnz = None
    try:
        nnz = int(ls.GetMatrix().nonZeros())
    except Exception:  # noqa: BLE001 - optional binding
        pass
    st_end = state()
    out = {
        "cfg": {k: v for k, v in cfg.items() if k != "out"},
        "env_MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
        "build_s": build_s,
        "solver_type": int(s.GetSolverType()),
        "lock_sparsity": bool(cfg.get("lock", False)),
        "threads": {
            "chrono": int(s.GetNumThreadsChrono()),
            "eigen": int(s.GetNumThreadsEigen()),
            "collision": int(s.GetNumThreadsCollision()),
        },
        "counts": {
            "bodies": int(s.GetNumBodies()),
            "links": int(s.GetNumLinks()),
            "other_items": int(s.GetNumOtherPhysicsItems()),
            "coords_vel": int(s.GetNumCoordsVelLevel()),
            "constraints_bilateral": int(s.GetNumConstraintsBilateral()),
            "constraints": int(s.GetNumConstraints()),
            "contacts": int(s.GetNumContacts()),
            "kkt_size": int(s.GetNumCoordsVelLevel()) + int(s.GetNumConstraints()),
            "matrix_nnz": nnz,
        },
        "extra": extra,
        "warmup_steps": w,
        "warmup_us_per_step": t_w / max(w, 1) * 1e6,
        "steps": steps,
        "wall_us_per_step_reps": walls,
        "wall_us_per_step_median": statistics.median(walls),
        "profile_wall_us_per_step": prof_wall,
        "chrono_timers_us_per_step": prof,
        "direct_solver_us_per_step": lsd,
        "scm_timers_per_step": scm_per,
        "state_after_warmup": st_warm,
        "state_end": {k: v for k, v in st_end.items() if not k.startswith("_")},
        "sim_time_end_s": float(s.GetChTime()),
    }
    Path(cfg["out"]).write_text(json.dumps(out, indent=1))
    print("OK", model, cfg["solver"], f"{out['wall_us_per_step_median']:.1f} us/step", flush=True)


if __name__ == "__main__":
    main()
