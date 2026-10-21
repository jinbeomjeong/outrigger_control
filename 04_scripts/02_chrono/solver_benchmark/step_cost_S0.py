"""S0 full-scale step-cost measurement (chrono_build_plan.md S0 checklist, section 4).

Usage (Chrono-dev python, from any folder):
  python -I -u step_cost_S0.py run [names...]  all (or the named) cases serially, one process
                                               each (~6 min on the 2026-10-20 PC) + summary
  python -I -u step_cost_S0.py case <cfg.json> one case (started by ``run``)
  python -I -u step_cost_S0.py summary         rebuild the summary from stored case results
  python -I -u step_cost_S0.py hookopt         ground-bushing hook before/after (commit 025e445
                                               vs current, pads dt 1e-4, alternating A B A B);
                                               adds the key "hook_optimization" to the summary
                                               and leaves every other key unchanged (~1 min)
Per-case results: 07_results/step_cost_S0/<case>.json (git-ignored).
Summary: 06_analysis/01_chrono/01_cost/step_cost_S0.json.

Model (full-scale L1, auger level top, current YAML):
  * ``outrigger_sim.chrono.system.make_system`` (SMC, Bullet, explicit gravity, EULER_IMPLICIT_
    LINEARIZED, default SPARSE_LU + locked sparsity pattern; SPARSE_QR as reference case);
  * superstructure body (mass, COM, full inertia tensor from ``superstructure.mass_properties``)
    carrying the 24 crawler spheres of layout D (``contact.crawler.sphere_layout``,
    ``crawler_contact.layout_from_params``; material kn/gn per sphere, kt = gt = mu = 0);
  * 4 leg moving parts on ``ChLinkMotorLinearPosition`` (constant position, i.e. locked
    actuator of L1), one pad sphere each (r = swivel centre height, leg kn/gn);
  * floor body (1e9 kg, fixed) without the default plate; per-leg pad patches with the leg
    material and two crawler strips with the crawler material (R13 patch idea of S1, so that
    the SMC material combination does not mix pad and crawler values);
  * ``outrigger_sim.chrono.ground_bushing.GroundBushingCoulomb`` (R15, return mapping) called
    after every step.

States:
  * ``pads``: legs at ``contact.rigid_floor.L1.derivation.operating_extension_m``, crawler
    raised by ``simulation.crawler_clearance_m``; machine lowered by the uniform static pad
    penetration W / sum(kn) so the start is close to equilibrium; bushings attached at t = 0.
  * ``crawler``: legs fully retracted (pads in the air, no bushings, hook runs its no-contact
    path); machine lowered by W / kn_total on the 12 roller spheres.
  Both start near (not at) the static solution; the warm-up absorbs the start transient. The
  physics is not judged here (cost only); contact count, R15 events and the vertical force
  balance are recorded as plausibility checks.

Timing protocol per case (own process): build -> warm-up -> ``reps`` instrumented windows of
``window_s`` simulated seconds (perf_counter around DoStepDynamics and around the hook for every
step, plus the window wall time) -> one plain window (no per-step timers, wall only) -> one
profiling window reading the Chrono per-step timers and the direct-solver timers.
Units: SI; times in microseconds per step unless stated.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I: the script folder is not on sys.path
import bench_common as bcm  # noqa: E402  (side effect: 03_src and 04_scripts/00_cad on sys.path)

RESULTS = bcm.PROJECT_ROOT / "07_results" / "step_cost_S0"
SUMMARY = bcm.ANALYSIS_DIR / "step_cost_S0.json"
PY = sys.executable

TIMERS = ("Step", "Advance", "LSsetup", "LSsolve", "Setup", "Update", "Jacobian", "Collision")

# Plan section 4 values compared against (chrono_build_plan.md, 2026-10-20 text)
PLAN_UNIT_US = 200.0  # "L1 0.2 ms/step" planning unit
PLAN_BASIS_US = 163.0  # full-scale L1, QR, 4-leg hook, dt 2e-4 (scratchpad 2026-10-19)
BENCH_LU_LOCK_US = 133.0  # solver_benchmark.json, LU + lock, dt 1e-4, 18 crawler spheres

CASES = [
    # name, state, dt, solver, lock, warmup_s, window_s, reps, cpu placement
    ("pads_dt1e-4_LU", "pads", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "pcore"),
    ("crawler_dt1e-4_LU", "crawler", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "pcore"),
    ("pads_dt1e-5_LU", "pads", 1e-5, "SPARSE_LU", True, 0.2, 1.0, 3, "pcore"),
    ("crawler_dt1e-5_LU", "crawler", 1e-5, "SPARSE_LU", True, 0.2, 1.0, 3, "pcore"),
    ("pads_dt1e-4_QR", "pads", 1e-4, "SPARSE_QR", True, 0.5, 1.0, 5, "pcore"),
    ("pads_dt1e-4_LU_repeat", "pads", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "pcore"),
    # placement comparison (i7-14700 hybrid: Windows may run a window-less process on E-cores)
    ("pads_dt1e-4_LU_ecore", "pads", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "ecore"),
    ("pads_dt1e-4_LU_os", "pads", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "os"),
    # cost split: pads state without ground bushings and without the hook (not a valid model)
    ("pads_dt1e-4_LU_nobushing", "pads", 1e-4, "SPARSE_LU", True, 0.5, 1.0, 5, "pcore"),
]
NO_BUSHING_CASES = {"pads_dt1e-4_LU_nobushing"}


# --- CPU placement (hybrid CPU) ----------------------------------------------------------


def cpu_sets() -> list[dict]:
    """Logical processors with their EfficiencyClass (Windows GetSystemCpuSetInformation).

    Higher class = faster core (i7-14700: P-cores 1, E-cores 0). Empty off Windows.
    """
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = k32.GetSystemCpuSetInformation
    fn.argtypes = [ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
                   wintypes.HANDLE, wintypes.ULONG]
    fn.restype = wintypes.BOOL
    need = wintypes.ULONG(0)
    fn(None, 0, ctypes.byref(need), None, 0)
    buf = (ctypes.c_ubyte * need.value)()
    if not fn(buf, need.value, ctypes.byref(need), None, 0):
        return []
    raw = bytes(buf)
    out, off = [], 0
    while off < need.value:
        size = int.from_bytes(raw[off:off + 4], "little")
        typ = int.from_bytes(raw[off + 4:off + 8], "little")
        if typ == 0:  # CpuSetInformation
            out.append({"id": int.from_bytes(raw[off + 8:off + 12], "little"),
                        "group": int.from_bytes(raw[off + 12:off + 14], "little"),
                        "logical": raw[off + 14], "core": raw[off + 15],
                        "efficiency_class": raw[off + 18]})
        off += size
    return out


def place_process(mode: str) -> dict:
    """Pin this process: 'pcore' (highest efficiency class), 'ecore' (lowest), 'os' (no change).

    For 'pcore' and 'ecore' the Windows execution-speed power throttling (EcoQoS) is also
    switched off for this process (SetProcessInformation ProcessPowerThrottling, state 0), so
    the scheduler does not move a window-less background process to the E-cores. Only this
    process is changed; no system setting.
    """
    info: dict = {"mode": mode}
    sets = cpu_sets()
    info["efficiency_classes"] = sorted({s["efficiency_class"] for s in sets})
    if mode == "os" or not sets:
        return info
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    hproc = k32.GetCurrentProcess()
    classes = info["efficiency_classes"]
    want = classes[-1] if mode == "pcore" else classes[0]
    logical = [s["logical"] for s in sets if s["efficiency_class"] == want and s["group"] == 0]
    mask = 0
    for lp in logical:
        mask |= 1 << lp
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    k32.SetProcessAffinityMask.restype = wintypes.BOOL
    info["affinity_ok"] = bool(k32.SetProcessAffinityMask(hproc, mask))
    info["affinity_logical_processors"] = logical

    class PowerThrottlingState(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG),
                    ("StateMask", wintypes.ULONG)]

    state = PowerThrottlingState(1, 0x1, 0x0)  # EXECUTION_SPEED controlled, throttling off
    k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD]
    k32.SetProcessInformation.restype = wintypes.BOOL
    info["power_throttling_off_ok"] = bool(
        k32.SetProcessInformation(hproc, 4, ctypes.byref(state), ctypes.sizeof(state))
    )
    return info


# --- case process ------------------------------------------------------------------------


def run_case(cfg: dict) -> dict:
    placement = place_process(cfg.get("cpu", "os"))
    import numpy as np
    import pychrono as ch
    from crawler_contact import layout_from_params

    from outrigger_sim.chrono.system import make_smc_material, make_system

    if cfg.get("bushing_module_path"):  # an older GroundBushingCoulomb (before/after cost)
        import importlib.util

        spec = importlib.util.spec_from_file_location("ground_bushing_ref",
                                                      cfg["bushing_module_path"])
        module = importlib.util.module_from_spec(spec)
        sys.modules["ground_bushing_ref"] = module  # dataclasses look the module up
        spec.loader.exec_module(module)
        GroundBushingCoulomb = module.GroundBushingCoulomb  # noqa: N806
    else:
        from outrigger_sim.chrono.ground_bushing import GroundBushingCoulomb
    from outrigger_sim.params import load_params

    P = load_params()  # auger level top (default)
    g = P.meta.gravity_m_s2
    dt = float(cfg["dt"])
    state_name = cfg["state"]

    t_build0 = time.perf_counter()
    b = make_system(P, "L1", dt=dt, solver=cfg["solver"], lock_sparsity_pattern=cfg["lock"],
                    floor_plate=False)
    s, floor = b.system, b.floor
    z_floor = P.ground.crawler_bottom_z_m
    mp = P.superstructure.mass_properties
    l1 = P.contact.rigid_floor.L1
    layout = layout_from_params(P)
    m_total = mp.mass_kg + sum(leg.moving_part.mass_kg for leg in P.legs)
    weight = m_total * g

    kn_crawler = float(P.get("contact.crawler.kn_per_sphere_N_m"))
    gn_crawler = float(P.get("contact.crawler.gn_per_sphere_1_s"))
    if state_name == "pads":
        ext = [l1.operating_extension_m[i] for i in range(4)]
        delta = weight / sum(l1.kn_per_pad_N_m[i] for i in range(4))
        lift = P.simulation.crawler_clearance_m - delta
    elif state_name == "crawler":
        ext = [0.0] * 4
        delta = weight / float(P.get("contact.crawler.kn_total_N_m"))
        lift = -delta
    else:
        raise ValueError(state_name)

    # floor patches (R13 idea): pads with the leg material, crawler strips with crawler material
    floor.EnableCollision(True)
    hz = 0.5
    pad_half = 0.4
    patches = []
    for i, leg in enumerate(P.legs):
        mat = make_smc_material(l1.kn_per_pad_N_m[i], l1.gn_per_pad_1_s[i])
        cx, cy = leg.pad_bottom_center_retracted_m[0], leg.pad_bottom_center_retracted_m[1]
        floor.AddCollisionShape(
            ch.ChCollisionShapeBox(mat, 2 * pad_half, 2 * pad_half, 2 * hz),
            ch.ChFramed(ch.ChVector3d(cx, cy, z_floor - hz), ch.QUNIT),
        )
        patches.append(
            ("pad_" + leg.name, [cx - pad_half, cx + pad_half], [cy - pad_half, cy + pad_half])
        )
    cmat_floor = make_smc_material(kn_crawler, gn_crawler)
    x0, x1 = layout.x_extent_m
    margin = 0.25
    yc = layout.track_centre_y_m
    for y in (yc, -yc):
        floor.AddCollisionShape(
            ch.ChCollisionShapeBox(cmat_floor, x1 - x0 + 2 * margin, 2 * margin, 2 * hz),
            ch.ChFramed(ch.ChVector3d(0.5 * (x0 + x1), y, z_floor - hz), ch.QUNIT),
        )
        patches.append(("crawler", [x0 - margin, x1 + margin], [y - margin, y + margin]))
    # patches must not overlap (a sphere would get two contacts)
    for a in range(len(patches)):
        for c in range(a + 1, len(patches)):
            pa, pc = patches[a], patches[c]
            x_overlap = pa[1][0] < pc[1][1] and pc[1][0] < pa[1][1]
            y_overlap = pa[2][0] < pc[2][1] and pc[2][0] < pa[2][1]
            if x_overlap and y_overlap:
                raise RuntimeError(f"floor patches overlap: {pa} / {pc}")

    def inertia_body(mass, inertia, pos):
        body = ch.ChBody()
        body.SetMass(mass)
        body.SetInertiaXX(ch.ChVector3d(inertia[0][0], inertia[1][1], inertia[2][2]))
        body.SetInertiaXY(ch.ChVector3d(inertia[0][1], inertia[0][2], inertia[1][2]))
        body.SetPos(ch.ChVector3d(*pos))
        return body

    com_sup = np.array(mp.com_m) + [0.0, 0.0, lift]
    sup = inertia_body(mp.mass_kg, mp.inertia_kg_m2, com_sup)
    sup.SetName("superstructure")
    sup.EnableCollision(True)
    cmat = make_smc_material(kn_crawler, gn_crawler)
    for centre_world in layout.sphere_centres_m(z_floor, lift):
        sup.AddCollisionShape(
            ch.ChCollisionShapeSphere(cmat, layout.sphere_radius_m),
            ch.ChFramed(ch.ChVector3d(*(centre_world - com_sup)), ch.QUNIT),
        )
    s.Add(sup)

    legs, centres_local = [], []
    for i, leg in enumerate(P.legs):
        mpart = leg.moving_part
        com = np.array(mpart.com_m) + [0.0, 0.0, lift - ext[i]]
        body = inertia_body(mpart.mass_kg, mpart.inertia_kg_m2, com)
        body.SetName(f"leg_{leg.name}")
        r = leg.pad.swivel_center_above_pad_bottom_m
        pad_bottom = np.array(leg.pad_bottom_center_retracted_m) + [0.0, 0.0, lift - ext[i]]
        centre_local = pad_bottom + [0.0, 0.0, r] - com
        body.EnableCollision(True)
        pad_mat = make_smc_material(l1.kn_per_pad_N_m[i], l1.gn_per_pad_1_s[i])
        body.AddCollisionShape(
            ch.ChCollisionShapeSphere(pad_mat, r),
            ch.ChFramed(ch.ChVector3d(*centre_local), ch.QUNIT),
        )
        s.Add(body)
        motor = ch.ChLinkMotorLinearPosition()
        att = np.array(leg.attachment_point_m) + [0.0, 0.0, lift]
        motor.Initialize(body, sup, ch.ChFramed(ch.ChVector3d(*att), ch.QuatFromAngleX(math.pi)))
        motor.SetMotionFunction(ch.ChFunctionConst(0.0))
        s.Add(motor)
        legs.append(body)
        centres_local.append(centre_local)

    gb = GroundBushingCoulomb.from_params(P, s, floor, legs, centres_local, dt_s=dt)
    use_bushing = bool(cfg.get("bushing", True))
    if state_name == "pads" and use_bushing:
        gb.attach()
    build_s = time.perf_counter() - t_build0
    ls = s.GetSolver().AsDirect()

    def forces() -> dict:
        fz = [float(body.GetContactForce().z) for body in legs]
        fc = float(sup.GetContactForce().z)
        return {
            "t_s": float(s.GetChTime()),
            "pad_fz_N": fz,
            "crawler_fz_N": fc,
            "sum_fz_over_weight": (sum(fz) + fc) / weight,
            "contacts": int(s.GetNumContacts()),
            "bushings_in_contact": [bool(v) for v in gb.in_contact],
            "bushing_events": len(gb.events),
            "sup_pos_m": [float(v) for v in (sup.GetPos().x, sup.GetPos().y, sup.GetPos().z)],
        }

    pc = time.perf_counter
    step = s.DoStepDynamics

    def no_hook(_dt: float) -> None:
        return None

    # bushing=False: cost split only (no tangential restraint at all; not a valid L1 model)
    hook = gb.after_step if use_bushing else no_hook

    def plain(n: int) -> float:
        t0 = pc()
        for _ in range(n):
            step(dt)
            hook(dt)
        return pc() - t0

    def instrumented(n: int):
        st = np.empty(n)
        hk = np.empty(n)
        t_start = pc()
        for k in range(n):
            t0 = pc()
            step(dt)
            t1 = pc()
            hook(dt)
            t2 = pc()
            st[k] = t1 - t0
            hk[k] = t2 - t1
        return pc() - t_start, st, hk

    n_warm = round(cfg["warmup_s"] / dt)
    n_win = round(cfg["window_s"] / dt)
    t_warm = plain(n_warm)
    f_warm = forces()
    contacts_min, contacts_max = f_warm["contacts"], f_warm["contacts"]

    windows = []
    all_tot = []
    all_st = []
    all_hk = []
    for _ in range(int(cfg["reps"])):
        wall, st, hk = instrumented(n_win)
        tot = st + hk
        all_tot.append(tot)
        all_st.append(st)
        all_hk.append(hk)
        f = forces()
        contacts_min = min(contacts_min, f["contacts"])
        contacts_max = max(contacts_max, f["contacts"])
        windows.append(
            {
                "wall_s": wall,
                "wall_us_per_step": wall / n_win * 1e6,
                "step_us_median": float(np.median(st) * 1e6),
                "hook_us_median": float(np.median(hk) * 1e6),
                "total_us_median": float(np.median(tot) * 1e6),
                "total_us_p5": float(np.percentile(tot, 5) * 1e6),
                "total_us_p95": float(np.percentile(tot, 95) * 1e6),
                "step_us_mean": float(st.mean() * 1e6),
                "hook_us_mean": float(hk.mean() * 1e6),
                "loop_overhead_us_mean": float((wall - tot.sum()) / n_win * 1e6),
                "end": f,
            }
        )
    tot = np.concatenate(all_tot) * 1e6
    st = np.concatenate(all_st) * 1e6
    hk = np.concatenate(all_hk) * 1e6

    t_plain = plain(n_win)
    f_plain = forces()

    # profiling window (Chrono timers are per step; direct-solver timers accumulate)
    n_prof = round(0.2 / dt)
    acc = dict.fromkeys(TIMERS, 0.0)
    getters = [(name, getattr(s, f"GetTimer{name}")) for name in TIMERS]
    ls.ResetTimers()
    t0 = pc()
    for _ in range(n_prof):
        step(dt)
        hook(dt)
        for name, getter in getters:
            acc[name] += getter()
    prof_wall = (pc() - t0) / n_prof * 1e6
    prof = {k: v / n_prof * 1e6 for k, v in acc.items()}
    lsd = {
        "setup_assembly": ls.GetTimeSetup_Assembly() / n_prof * 1e6,
        "setup_solver_call": ls.GetTimeSetup_SolverCall() / n_prof * 1e6,
        "solve_assembly": ls.GetTimeSolve_Assembly() / n_prof * 1e6,
        "solve_solver_call": ls.GetTimeSolve_SolverCall() / n_prof * 1e6,
        "setup_calls": int(ls.GetNumSetupCalls()),
        "solve_calls": int(ls.GetNumSolveCalls()),
    }
    nnz = None
    try:
        nnz = int(ls.GetMatrix().nonZeros())
    except Exception:  # noqa: BLE001 - optional binding
        pass

    def pct(a, q):
        return float(np.percentile(a, q))

    out = {
        "cfg": {k: v for k, v in cfg.items() if k != "out"},
        "build_s": build_s,
        "cpu_placement": placement,
        "system_meta": b.meta(),
        "model": {
            "n_crawler_spheres": layout.n_points,
            "crawler_layout": layout.summary(),
            "floor_patches": [p[0] for p in patches],
            "total_mass_kg": m_total,
            "initial_lowering_m": delta,
            "leg_extension_m": ext,
        },
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
            "kkt_size": int(s.GetNumCoordsVelLevel()) + int(s.GetNumConstraints()),
            "matrix_nnz": nnz,
            "contacts_range": [contacts_min, contacts_max],
            "collision_shapes": {"crawler_spheres": layout.n_points, "pad_spheres": 4,
                                 "floor_boxes": len(patches)},
        },
        "steps_per_window": n_win,
        "warmup": {"steps": n_warm, "wall_us_per_step": t_warm / n_warm * 1e6, "end": f_warm},
        "windows": windows,
        "pooled": {
            "n_steps": int(tot.size),
            "total_us_median": float(np.median(tot)),
            "total_us_p5": pct(tot, 5),
            "total_us_p95": pct(tot, 95),
            "total_us_mean": float(tot.mean()),
            "step_us_median": float(np.median(st)),
            "step_us_p5": pct(st, 5),
            "step_us_p95": pct(st, 95),
            "step_us_mean": float(st.mean()),
            "hook_us_median": float(np.median(hk)),
            "hook_us_p5": pct(hk, 5),
            "hook_us_p95": pct(hk, 95),
            "hook_us_mean": float(hk.mean()),
            "hook_share_of_mean": float(hk.mean() / tot.mean()),
            "window_wall_us_per_step": [w["wall_us_per_step"] for w in windows],
            "window_wall_us_per_step_median": float(
                np.median([w["wall_us_per_step"] for w in windows])
            ),
        },
        "plain_window": {
            "wall_us_per_step": t_plain / n_win * 1e6,
            "wall_s_per_sim_s": t_plain / (n_win * dt),
            "end": f_plain,
        },
        "profile": {
            "steps": n_prof,
            "wall_us_per_step": prof_wall,
            "chrono_timers_us_per_step": prof,
            "direct_solver_us_per_step": lsd,
        },
        "sim_time_end_s": float(s.GetChTime()),
    }
    return out


# --- driver ------------------------------------------------------------------------------


def cpu_name() -> str:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    except Exception:  # noqa: BLE001
        return platform.processor()


def pychrono_version() -> str:
    meta = Path(sys.prefix) / "conda-meta"
    hits = sorted(meta.glob("pychrono-*.json"))
    if hits:
        d = json.loads(hits[-1].read_text())
        return f"{d['version']} ({d.get('build', '')}, {d.get('channel', '')})"
    return "unknown"


FOREIGN = ("julia", "freecad", "freecadcmd", "gmsh", "ccx", "matlab")


def foreign_processes() -> list[str]:
    """Compute-type processes other than ours (2026-10-20: a Julia precompile of another
    session overlapped a first run; cases are now stamped with this list before and after)."""
    try:
        txt = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=30,
                             check=False).stdout.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ["<tasklist failed>"]
    me = os.getpid()
    out = []
    for line in txt.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) < 2:
            continue
        image, pid = parts[0].lower(), parts[1]
        stem = image.removesuffix(".exe")
        if stem in FOREIGN or (stem == "python" and pid != str(me)):
            out.append(f"{image}:{pid}")
    return out


def run_all() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    t_all = time.perf_counter()
    only = set(sys.argv[2:])
    for name, state, dt, solver, lock, warm, win, reps, cpu in CASES:
        if only and name not in only:
            continue
        before = foreign_processes()
        started = _dt.datetime.now().isoformat(timespec="seconds")
        out = RESULTS / f"{name}.json"
        cfg = {"name": name, "state": state, "dt": dt, "solver": solver, "lock": lock,
               "warmup_s": warm, "window_s": win, "reps": reps, "cpu": cpu,
               "bushing": name not in NO_BUSHING_CASES, "out": str(out)}
        cfg_path = RESULTS / f"{name}.cfg.json"
        cfg_path.write_text(json.dumps(cfg))
        t0 = time.perf_counter()
        try:
            done = subprocess.run(
                [PY, "-I", "-u", str(Path(__file__).resolve()), "case", str(cfg_path)],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600, check=False,
            )
            status = f"rc={done.returncode & 0xFFFFFFFF:#x}"
            tail = (done.stdout.strip().splitlines() or [""])[-1]
            err_lines = (done.stderr.strip().splitlines() or [""])[-3:]
            err = " | ".join(err_lines) if done.returncode else ""
        except subprocess.TimeoutExpired:
            status, tail, err = "TIMEOUT", "", ""
        after = foreign_processes()
        if out.is_file() and status == "rc=0x0":
            r = json.loads(out.read_text())
            r["run_stamp"] = {"started": started,
                              "finished": _dt.datetime.now().isoformat(timespec="seconds"),
                              "foreign_processes_before": before,
                              "foreign_processes_after": after}
            out.write_text(json.dumps(r, indent=1))
        elapsed = time.perf_counter() - t0
        line = f"{name}: {status} {elapsed:.1f}s {tail} {err} foreign={before}/{after}"
        print(line, flush=True)
        with open(RESULTS / "log.txt", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(f"total {time.perf_counter() - t_all:.1f}s", flush=True)
    summarize()


def summarize() -> None:
    cases = {}
    for name, *_ in CASES:
        p = RESULTS / f"{name}.json"
        if p.is_file():
            cases[name] = json.loads(p.read_text())
    rows = []
    for name, r in cases.items():
        dt = r["cfg"]["dt"]
        po = r["pooled"]
        mean_us = po["total_us_mean"]
        plain_us = r["plain_window"]["wall_us_per_step"]
        rows.append(
            {
                "case": name,
                "state": r["cfg"]["state"],
                "dt_s": dt,
                "solver": r["cfg"]["solver"],
                "lock_sparsity_pattern": r["cfg"]["lock"],
                "cpu_placement": r.get("cpu_placement"),
                "us_per_step_median": po["total_us_median"],
                "us_per_step_p5": po["total_us_p5"],
                "us_per_step_p95": po["total_us_p95"],
                "us_per_step_mean": mean_us,
                "chrono_step_us_median": po["step_us_median"],
                "hook_us_median": po["hook_us_median"],
                "hook_us_mean": po["hook_us_mean"],
                "hook_share_of_mean": po["hook_share_of_mean"],
                "window_wall_us_per_step": po["window_wall_us_per_step"],
                "plain_wall_us_per_step": plain_us,
                "wall_s_per_sim_s": plain_us * 1e-6 / dt,
                "ratio_to_plan_unit_200us": plain_us / PLAN_UNIT_US,
                "ratio_to_plan_basis_163us": plain_us / PLAN_BASIS_US,
                "ratio_to_benchmark_LU_lock_133us": plain_us / BENCH_LU_LOCK_US,
                "chrono_timers_us_per_step": r["profile"]["chrono_timers_us_per_step"],
                "direct_solver_us_per_step": r["profile"]["direct_solver_us_per_step"],
                "counts": r["counts"],
                "end_state": r["plain_window"]["end"],
                "run_stamp": r.get("run_stamp"),
            }
        )
    first = next(iter(cases.values()), None)
    by = {row["case"]: row for row in rows}
    derived = {}
    need = ("pads_dt1e-4_LU", "pads_dt1e-5_LU", "crawler_dt1e-4_LU", "crawler_dt1e-5_LU",
            "pads_dt1e-4_LU_nobushing")
    if all(k in by for k in need):
        p4, p5, c4, c5, nb = (by[k] for k in need)
        pads_s5 = p5["wall_s_per_sim_s"]
        crawler_s5 = c5["wall_s_per_sim_s"]
        derived = {
            "cost_split_pads_dt1e-4_us_per_step": {
                "total_plain": p4["plain_wall_us_per_step"],
                "chrono_step_median": p4["chrono_step_us_median"],
                "chrono_step_without_bushings_median": nb["chrono_step_us_median"],
                "chrono_bushing_loads_4": p4["chrono_step_us_median"] - nb["chrono_step_us_median"],
                "python_hook_mean": p4["hook_us_mean"],
                "linear_solver_LSsetup_plus_LSsolve": p4["chrono_timers_us_per_step"]["LSsetup"]
                + p4["chrono_timers_us_per_step"]["LSsolve"],
                "collision": p4["chrono_timers_us_per_step"]["Collision"],
                "loop_and_rest": p4["plain_wall_us_per_step"] - p4["chrono_step_us_median"]
                - p4["hook_us_mean"],
            },
            "ratio_dt1e-5_over_dt1e-4_us_per_step": {
                "pads": p5["plain_wall_us_per_step"] / p4["plain_wall_us_per_step"],
                "crawler": c5["plain_wall_us_per_step"] / c4["plain_wall_us_per_step"],
            },
            "stage_impact_examples": {
                "note": "simulated lengths from chrono_build_plan.md section 4 (lift: first touch "
                "about 15.0 s after motor start, crawler state before it, pad state after); "
                "P-core placement",
                "V9_V4_reference_dt1e-5_wall_s": 15.0 * crawler_s5 + 17.7 * pads_s5,
                "V9_V4_reference_plan_wall_s": 654.0,
                "V4_run_transition_window_only_wall_s": 14.9 * c4["wall_s_per_sim_s"]
                + 3.1 * pads_s5 + 14.7 * p4["wall_s_per_sim_s"],
                "V4_run_plan_wall_s": 60.6 * 2.0,
                "S2b_crawler_settle_3x65.5s_wall_s": 3 * 65.5 * c4["wall_s_per_sim_s"],
                "S2b_crawler_settle_plan_wall_s": 3 * 65.5 * 2.0,
            },
        }
        if "pads_dt1e-4_LU_os" in by and "pads_dt1e-4_LU_ecore" in by:
            derived["placement_factor_vs_pcore"] = {
                "os_default": by["pads_dt1e-4_LU_os"]["plain_wall_us_per_step"]
                / p4["plain_wall_us_per_step"],
                "ecore": by["pads_dt1e-4_LU_ecore"]["plain_wall_us_per_step"]
                / p4["plain_wall_us_per_step"],
            }
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "script": "04_scripts/02_chrono/solver_benchmark/step_cost_S0.py",
            "purpose": "chrono_build_plan.md S0 checklist: full-scale step cost, "
            "crawler layout D",
            "cpu": cpu_name(),
            "logical_cpus": os.cpu_count(),
            "os": platform.platform(),
            "python": platform.python_version(),
            "pychrono": pychrono_version(),
            "model": "L1 full scale, auger level top: superstructure + 4 leg moving parts on "
            "locked "
            "ChLinkMotorLinearPosition + 4 pad spheres + 24 crawler spheres (layout D) + floor "
            "patches (4 pad, 2 crawler strips) + GroundBushingCoulomb (Python after_step)",
            "states": {
                "pads": "legs at operating extension, crawler 50 mm up, bushings attached",
                "crawler": "legs retracted, machine on the crawler spheres, no bushings",
            },
            "timing": "per case own process; warm-up, then reps instrumented windows of 1 s "
            "simulated time (perf_counter around DoStepDynamics and around after_step per step), "
            "then a plain 1 s window (wall only) used for the wall-clock-per-sim-second figure, "
            "then a 0.2 s profiling window (Chrono timers)",
            "plan_reference_us_per_step": {
                "plan_unit": PLAN_UNIT_US,
                "plan_basis_QR_hook_dt2e-4": PLAN_BASIS_US,
                "solver_benchmark_LU_lock_dt1e-4_18_spheres": BENCH_LU_LOCK_US,
            },
            "counts_pads_LU": first["counts"] if first else None,
            "system_settings": first["system_meta"] if first else None,
        },
        "cases": rows,
        "derived": derived,
    }
    if SUMMARY.is_file():  # keep the section written by ``hookopt``
        previous = json.loads(SUMMARY.read_text(encoding="utf-8"))
        if "hook_optimization" in previous:
            summary["hook_optimization"] = previous["hook_optimization"]
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {SUMMARY}")
    for row in rows:
        print(
            f"{row['case']:20s} med {row['us_per_step_median']:7.1f} "
            f"p5 {row['us_per_step_p5']:7.1f} "
            f"p95 {row['us_per_step_p95']:7.1f} plain {row['plain_wall_us_per_step']:7.1f} "
            f"hook {row['hook_us_mean']:5.1f} ({row['hook_share_of_mean']*100:4.1f}%) "
            f"{row['wall_s_per_sim_s']:6.2f} s/s contacts {row['counts']['contacts_range']}"
        )


HOOKOPT_BASE_COMMIT = "025e445"
HOOKOPT_RUNS = ("before", "after", "before", "after")  # alternating to cancel slow drift


def run_hookopt() -> None:
    """Hook optimisation before/after on the pads dt 1e-4 LU case (P-core, own processes).

    "before" = ``chrono/ground_bushing.py`` of commit :data:`HOOKOPT_BASE_COMMIT` (extracted
    with ``git show`` into the results folder), "after" = the current module. The end states
    of the two variants are compared bit for bit (same steps, deterministic). The result is
    merged into the summary under ``hook_optimization``; no other key is touched.
    """
    RESULTS.mkdir(parents=True, exist_ok=True)
    old_path = RESULTS / f"ground_bushing_{HOOKOPT_BASE_COMMIT}.py"
    src = subprocess.run(
        ["git", "-C", str(bcm.PROJECT_ROOT), "show",
         f"{HOOKOPT_BASE_COMMIT}:03_src/outrigger_sim/chrono/ground_bushing.py"],
        capture_output=True, check=True, timeout=60,
    ).stdout
    old_path.write_bytes(src)
    runs = []
    for k, variant in enumerate(HOOKOPT_RUNS):
        name = f"hookopt_{variant}_{k}"
        out = RESULTS / f"{name}.json"
        cfg = {"name": name, "state": "pads", "dt": 1e-4, "solver": "SPARSE_LU", "lock": True,
               "warmup_s": 0.5, "window_s": 1.0, "reps": 5, "cpu": "pcore", "bushing": True,
               "out": str(out)}
        if variant == "before":
            cfg["bushing_module_path"] = str(old_path)
        cfg_path = RESULTS / f"{name}.cfg.json"
        cfg_path.write_text(json.dumps(cfg))
        before = foreign_processes()
        done = subprocess.run(
            [PY, "-I", "-u", str(Path(__file__).resolve()), "case", str(cfg_path)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600, check=False,
        )
        after = foreign_processes()
        if done.returncode != 0 or not out.is_file():
            raise RuntimeError(f"{name}: rc={done.returncode} {done.stderr[-500:]}")
        r = json.loads(out.read_text())
        print(name, f"{r['plain_window']['wall_us_per_step']:.1f} us/step "
              f"hook {r['pooled']['hook_us_mean']:.1f}", flush=True)
        runs.append({
            "run": name,
            "variant": variant,
            "plain_wall_us_per_step": r["plain_window"]["wall_us_per_step"],
            "us_per_step_median": r["pooled"]["total_us_median"],
            "us_per_step_p5": r["pooled"]["total_us_p5"],
            "us_per_step_p95": r["pooled"]["total_us_p95"],
            "chrono_step_us_median": r["pooled"]["step_us_median"],
            "hook_us_mean": r["pooled"]["hook_us_mean"],
            "hook_us_median": r["pooled"]["hook_us_median"],
            "hook_share_of_mean": r["pooled"]["hook_share_of_mean"],
            "end_state": r["plain_window"]["end"],
            "foreign_processes_before_after": [before, after],
        })

    def agg(variant: str, key: str) -> float:
        import statistics

        return statistics.median(x[key] for x in runs if x["variant"] == variant)

    keys = ("plain_wall_us_per_step", "us_per_step_median", "chrono_step_us_median",
            "hook_us_mean")
    before_v = {k: agg("before", k) for k in keys}
    after_v = {k: agg("after", k) for k in keys}
    ends = [x["end_state"] for x in runs]
    identical = all(e == ends[0] for e in ends)
    section = {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "purpose": "S1 step 1: GroundBushingCoulomb.after_step optimisation (result-preserving): "
        "floor normal and anchor world points cached per floor pose, scalar float arithmetic "
        "instead of 3-vector numpy, slip speed only when used, SetDamping only on change",
        "case": "pads_dt1e-4_LU (same model and protocol as the cases above), P-core pinned",
        "before": f"ground_bushing.py of commit {HOOKOPT_BASE_COMMIT}",
        "after": "current ground_bushing.py",
        "runs": runs,
        "median_before": before_v,
        "median_after": after_v,
        "ratio_after_over_before": {k: after_v[k] / before_v[k] for k in keys},
        "end_states_bit_identical": identical,
        "end_state_note": "end_state after warm-up 0.5 s + 5 x 1 s windows + 1 s plain window "
        "(6.5 s simulated): pad contact forces, superstructure position, contact count; "
        "compared as exact floats between all four runs",
    }
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["hook_optimization"] = section
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"before": before_v, "after": after_v, "identical": identical}, indent=1))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "case":
        cfg = json.loads(Path(sys.argv[2]).read_text())
        result = run_case(cfg)
        Path(cfg["out"]).write_text(json.dumps(result, indent=1))
        print("OK", cfg["name"], f"{result['pooled']['total_us_median']:.1f} us/step", flush=True)
    elif mode == "run":
        run_all()
    elif mode == "summary":
        summarize()
    elif mode == "hookopt":
        run_hookopt()
    else:
        raise SystemExit(f"unknown mode {mode!r}")
