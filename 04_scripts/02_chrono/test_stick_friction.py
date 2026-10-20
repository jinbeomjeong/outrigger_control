"""Chrono 10 static-friction (stick) check for a single pad-sized block.

Purpose (CLAUDE.md, 00_docs/01_dynamics/actuator_L2_feasibility.md section 4): find out whether
the Chrono 10 SMC contact holds a block on a 2 deg slope (V12: slip < 0.1 mm) and whether a
horizontal tangential spring kt shows up (frequency sqrt(kt/m)), for the tangential models
OneStep / MultiStep / None, and test two alternatives:
  * L1  : SMC normal-only contact + ground-fixed tangential bushing
          (ChLoadBodyBodyBushingPlastic, yield = mu*N updated every step)
  * L2b : ChSystemNSC contact (complementarity friction)

Block: one rigid body, mass = damping_mass_kg / 4 (one leg share, YAML), collision = one sphere
(radius = swivel centre above pad bottom, YAML) like the planned pad contact, rotation locked to the
ground with ChLinkLockAlign so the sphere cannot roll (the real sphere is fixed on the rod body).
Ground: fixed box, tilted about +y by the slope angle; downhill tangent t = (cos a, 0, -sin a).
Units SI, Z-up, gravity (0, 0, -9.80665) set explicitly.

Run:  C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I 04_scripts/02_chrono/test_stick_friction.py
Out:  06_analysis/01_chrono/stick_friction.json, 06_analysis/01_chrono/stick_friction.png
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pychrono as ch
import yaml

ROOT = Path(__file__).resolve().parents[2]
P = yaml.safe_load((ROOT / "02_params" / "rexome33.yaml").read_text(encoding="utf-8"))
L1 = P["contact"]["rigid_floor"]["L1"]
KN = float(L1["kn_per_pad_N_m"]["FL"])
KT = float(L1["kt_per_pad_N_m"]["FL"])
CN = float(L1["cn_per_pad_N_s_m"]["FL"])
CT = float(L1["ct_per_pad_N_s_m"]["FL"])
MU = float(P["contact"]["rigid_floor"]["friction"])
DT = float(P["simulation"]["L1"]["dt_s"])
MASS = float(L1["derivation"]["damping_mass_kg"]) / 4.0  # one leg share of the lifted mass
G = 9.80665
R_SPH = 0.06  # 00_docs/01_dynamics/dynamics_model.md 4.2 (h_b = 0.06 m)
GROUND_MASS = 1.0e9  # fixed ground; Hooke damping uses eff_mass = m1 m2/(m1+m2), a default ChBody (1 kg) kills it
V_STICK = 1.0e-3  # [m/s] ASSUMPTION: re-enable bushing damping when slip velocity drops below this
BUSH_DAMP_FACTOR = 0.5  # measured here: ChLoadBodyBodyBushing* gives twice the input damping (zeta 0.10 for c = ct)

OUT = ROOT / "06_analysis" / "01_chrono"


def build(method, slope_deg, dt, tdm="OneStep", slip_thr=None, nsc_solver="PSOR", nsc_iter=50,
          gt_mode="per_mass", v0=(0.0, 0.0, 0.0), ground_mass=GROUND_MASS, bush_damp=BUSH_DAMP_FACTOR):
    """Return (sys, block, step_hook, frame) for one case."""
    a = math.radians(slope_deg)
    n = np.array([math.sin(a), 0.0, math.cos(a)])   # slope normal
    t = np.array([math.cos(a), 0.0, -math.sin(a)])  # downhill tangent
    q_slope = ch.QuatFromAngleY(a)

    if method == "NSC":
        sys = ch.ChSystemNSC()
        mat = ch.ChContactMaterialNSC()
        mat.SetFriction(MU)
        mat.SetRestitution(0.0)
        sys.SetSolverType(getattr(ch.ChSolver, "Type_" + nsc_solver))
        sys.GetSolver().AsIterative().SetMaxIterations(nsc_iter)
        delta0 = 0.0
    else:
        sys = ch.ChSystemSMC()
        sys.UseMaterialProperties(False)
        sys.SetContactForceModel(ch.ChSystemSMC.Hooke)
        model = {"OneStep": ch.ChSystemSMC.OneStep, "MultiStep": ch.ChSystemSMC.MultiStep,
                 "None": ch.ChSystemSMC._None}[tdm]
        sys.SetTangentialDisplacementModel(model)
        if slip_thr is not None:
            sys.SetSlipVelocityThreshold(slip_thr)
        mat = ch.ChContactMaterialSMC()
        # Chrono Hooke (UseMaterialProperties false): damping input is per unit effective mass
        # (checked below by the measured vertical damping ratio and OneStep creep speed).
        scale = MASS if gt_mode == "per_mass" else 1.0
        mat.SetKn(KN)
        mat.SetGn(CN / scale)
        if method == "bushing":   # contact carries the normal force only
            mat.SetKt(0.0)
            mat.SetGt(0.0)
            mat.SetFriction(0.0)
        else:
            mat.SetKt(KT)
            mat.SetGt(CT / scale)
            mat.SetFriction(MU)
        mat.SetRestitution(0.0)
        sys.SetSolverType(ch.ChSolver.Type_SPARSE_QR)
        delta0 = MASS * G * math.cos(a) / KN  # static penetration
    sys.SetCollisionSystemType(ch.ChCollisionSystem.Type_BULLET)
    sys.SetGravitationalAcceleration(ch.ChVector3d(0, 0, -G))
    sys.SetTimestepperType(ch.ChTimestepper.Type_EULER_IMPLICIT_LINEARIZED)

    ground = ch.ChBody()
    ground.SetFixed(True)
    ground.SetMass(ground_mass)
    ground.SetRot(q_slope)
    ground.EnableCollision(True)
    ground.AddCollisionShape(ch.ChCollisionShapeBox(mat, 60.0, 4.0, 0.4),
                             ch.ChFramed(ch.ChVector3d(0, 0, -0.2), ch.QUNIT))
    sys.Add(ground)

    block = ch.ChBody()
    block.SetMass(MASS)
    block.SetInertiaXX(ch.ChVector3d(1, 1, 1) * MASS / 6.0)  # 1 m cube (rotation is locked anyway)
    c0 = n * (R_SPH - delta0)
    block.SetPos(ch.ChVector3d(*c0))
    block.SetPosDt(ch.ChVector3d(*v0))
    block.EnableCollision(True)
    block.AddCollisionShape(ch.ChCollisionShapeSphere(mat, R_SPH), ch.ChFramed())
    sys.Add(block)

    align = ch.ChLinkLockAlign()
    align.Initialize(block, ground, ch.ChFramed(ch.ChVector3d(*c0), ch.QUNIT))
    sys.Add(align)

    hook = None
    if method in ("bushing", "bushing_plastic"):
        lc = ch.ChLoadContainer()
        sys.Add(lc)
        cp = c0 - n * (R_SPH - delta0)  # initial contact point on the slope surface
        frame = ch.ChFramed(ch.ChVector3d(*cp), q_slope)  # x,y tangential, z normal (free)
        N0 = MASS * G * math.cos(a)
        k3, c3 = ch.ChVector3d(KT, KT, 0.0), ch.ChVector3d(CT, CT, 0.0) * bush_damp
        if method == "bushing_plastic":
            bush = ch.ChLoadBodyBodyBushingPlastic(block, ground, frame, k3, c3,
                                                   ch.ChVector3d(MU * N0, MU * N0, 1e30))
        else:
            bush = ch.ChLoadBodyBodyBushingSpherical(block, ground, frame, k3, c3)
        lc.Add(bush)
        st = {"anchor": cp.copy(), "pA0": c0.copy(), "slip": np.zeros(3), "n_yield": 0}

        def hook():  # called after each step
            f = block.GetContactForce()
            N = max(0.0, f.x * n[0] + f.y * n[1] + f.z * n[2])
            if method == "bushing_plastic":  # box yield per axis, Chrono internal plastic state
                bush.SetYield(ch.ChVector3d(MU * N, MU * N, 1e30))
                return
            # elastic bushing + circular Coulomb return mapping done here (anchor moves on yield)
            pos = block.GetPos()
            pA = cp + (np.array([pos.x, pos.y, pos.z]) - st["pA0"])
            d = pA - st["anchor"]
            d -= (d @ n) * n
            dn = float(np.linalg.norm(d))
            vel = block.GetPosDt()
            vt = np.array([vel.x, vel.y, vel.z])
            vt = float(np.linalg.norm(vt - (vt @ n) * n))
            if KT * dn > MU * N:
                # simple return mapping (spring = mu*N now); the implicit step then overshoots by
                # about kt*|v|*dt while sliding. A velocity predictor made it chatter (tested).
                move = d * (1.0 - MU * N / (KT * dn))
                st["anchor"] += move
                st["slip"] += move
                st["n_yield"] += 1
                pl = ground.TransformPointParentToLocal(ch.ChVector3d(*st["anchor"]))
                bush.SetApplicationFrameB(ch.ChFramed(pl, ch.QUNIT))
                bush.SetDamping(ch.ChVector3d(0, 0, 0))  # no viscous term while sliding
                st["sliding"] = True
            elif st.get("sliding") and vt > V_STICK:
                pass  # keep damping off until the slip velocity has died out
            else:
                st["sliding"] = False
                bush.SetDamping(c3)
        hook.bush, hook.state = bush, st
    return sys, block, hook, (n, t, c0)


def run(name, method, slope_deg, t_end, dt=DT, rec_every=None, **kw):
    sys, block, hook, (n, t, c0) = build(method, slope_deg, dt, **kw)
    nsteps = int(round(t_end / dt))
    rec_every = rec_every or max(1, int(round(1e-3 / dt)))
    T, S, V, Z = [], [], [], []
    t0 = time.perf_counter()
    for k in range(nsteps + 1):
        if k % rec_every == 0:
            pos = block.GetPos()
            p = np.array([pos.x, pos.y, pos.z])
            v = block.GetPosDt()
            T.append(sys.GetChTime())
            S.append(float((p - c0) @ t))
            V.append(float(v.x * t[0] + v.y * t[1] + v.z * t[2]))
            Z.append(float((p - c0) @ n))
        if k == nsteps:
            break
        sys.DoStepDynamics(dt)
        if hook:
            hook()
    wall = time.perf_counter() - t0
    T, S, V, Z = map(np.array, (T, S, V, Z))
    f = block.GetContactForce()
    res = {"name": name, "method": method, "slope_deg": slope_deg, "dt_s": dt, "t_end_s": t_end,
           **{k: v for k, v in kw.items() if k != "v0"},
           "v0_m_s": list(kw.get("v0", (0, 0, 0))),
           "disp_end_m": float(S[-1]), "disp_max_abs_m": float(np.max(np.abs(S))),
           "v_end_m_s": float(V[-1]),
           "v_mean_last2s_m_s": float(np.mean(V[T >= t_end - 2.0])) if t_end > 2 else float(V[-1]),
           "normal_disp_end_m": float(Z[-1]),
           "contact_force_end_N": [f.x, f.y, f.z], "wall_s": wall}
    if method == "bushing_plastic":  # Chrono internal plastic deformation (B frame)
        pd = hook.bush.GetPlasticDeformation()
        res["bushing_plastic_def_m"] = [pd.x, pd.y, pd.z]
    elif method == "bushing":  # true slip = anchor movement; elastic part = disp - slip
        res["bushing_slip_along_slope_m"] = float(hook.state["slip"] @ t)
        res["bushing_yield_steps"] = hook.state["n_yield"]
        res["bushing_elastic_disp_m"] = float(S[-1] - hook.state["slip"] @ t)
    if slope_deg > 20:  # sliding case: effective friction coefficient from the mean acceleration
        acc = 2.0 * S[-1] / t_end ** 2
        a = math.radians(slope_deg)
        res["mu_effective"] = (G * math.sin(a) - acc) / (G * math.cos(a))
    print(f"{name:40s} disp_end={S[-1]*1e3:12.5f} mm  v_end={V[-1]:+.3e} m/s  wall={wall:.1f}s")
    return res, (T, S, V, Z)


def osc_fit(T, X, f_guess):
    """Fit X - X_end = exp(-s t)(A cos wd t + B sin wd t); return (f_n [Hz], zeta)."""
    from scipy.optimize import curve_fit
    x = X - X[-1]
    fun = lambda t, A, B, s, w: np.exp(-s * t) * (A * np.cos(w * t) + B * np.sin(w * t))
    w0 = 2 * math.pi * f_guess
    p, _ = curve_fit(fun, T, x, p0=[x[0], np.max(np.abs(x)), 1.0, w0], maxfev=20000)
    wn = math.hypot(p[2], p[3])
    return wn / (2 * math.pi), p[2] / wn


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    w_t = MASS * G * math.sin(math.radians(2.0))
    ref = {"mass_kg": MASS, "kn_N_m": KN, "kt_N_m": KT, "cn_N_s_m": CN, "ct_N_s_m": CT, "mu": MU,
           "dt_s": DT, "sphere_radius_m": R_SPH, "f_tangential_Hz": math.sqrt(KT / MASS) / (2 * math.pi),
           "zeta_tangential": CT / (2 * math.sqrt(KT * MASS)),
           "f_normal_Hz": math.sqrt(KN / MASS) / (2 * math.pi), "zeta_normal": CN / (2 * math.sqrt(KN * MASS)),
           "slope_2deg_static_tangential_disp_m": w_t / KT,
           "onestep_creep_estimate_m_s": w_t / (KT * DT + CT)}
    cases, hist = [], {}

    def add(name, *a, **k):
        r, h = run(name, *a, **k)
        cases.append(r)
        hist[name] = h
        return r, h

    # 1) SMC slope 2 deg, tangential models and slip threshold
    for tdm in ("OneStep", "MultiStep", "None"):
        add(f"SMC {tdm} 2deg", "SMC", 2.0, 10.0, tdm=tdm)
    for thr in (1e-6, 1e-2):
        add(f"SMC OneStep 2deg thr={thr:g}", "SMC", 2.0, 10.0, tdm="OneStep", slip_thr=thr)
    add("SMC OneStep 2deg gt raw", "SMC", 2.0, 10.0, tdm="OneStep", gt_mode="raw")
    # 2) horizontal tangential vibration (v0 = 10 mm/s along x) and vertical check
    for tdm in ("OneStep", "MultiStep"):
        add(f"SMC {tdm} flat v0", "SMC", 0.0, 3.0, tdm=tdm, v0=(0.01, 0, 0))
    fn0 = ref["f_normal_Hz"]
    ft0 = ref["f_tangential_Hz"]
    for gm in (GROUND_MASS, 1.0):  # Hooke gn is per effective mass -> ground mass matters
        _, hz = add(f"SMC OneStep flat vz0 ground {gm:g} kg", "SMC", 0.0, 2.0, tdm="OneStep",
                    v0=(0, 0, -0.01), ground_mass=gm)
        cases[-1].update(dict(zip(("f_normal_Hz", "zeta_normal"), osc_fit(hz[0], hz[3], fn0))))
    # 3a) L1 alternative: ground-fixed plastic bushing
    add("Bushing 2deg", "bushing", 2.0, 10.0)
    for name, kw in (("Bushing flat v0", {}), ("Bushing flat v0 c=ct (factor 1)", {"bush_damp": 1.0}),
                     ("Bushing flat v0 c=0", {"bush_damp": 0.0})):
        _, hb = add(name, "bushing", 0.0, 3.0, v0=(0.01, 0, 0), **kw)
        cases[-1].update(dict(zip(("f_tangential_Hz", "zeta_tangential"), osc_fit(hb[0], hb[1], ft0))))
    add("Bushing 30deg (tan>mu, must slide)", "bushing", 30.0, 2.0)
    # Chrono's own plastic bushing (box yield, internal plastic state) for comparison
    add("BushingPlastic 2deg", "bushing_plastic", 2.0, 10.0)
    add("BushingPlastic 30deg (must slide)", "bushing_plastic", 30.0, 2.0)
    add("BushingPlastic 30deg c=0 (must slide)", "bushing_plastic", 30.0, 2.0, bush_damp=0.0)
    # 3b) L2b alternative: NSC
    for solver, it in (("PSOR", 50), ("PSOR", 200), ("APGD", 100)):
        add(f"NSC 2deg {solver}{it}", "NSC", 2.0, 10.0, nsc_solver=solver, nsc_iter=it)
    add("NSC 30deg PSOR50 (must slide)", "NSC", 30.0, 2.0)
    add("NSC flat v0 PSOR50", "NSC", 0.0, 3.0, v0=(0.01, 0, 0))
    # 4) dt convergence
    add("Bushing 2deg dt/2", "bushing", 2.0, 10.0, dt=DT / 2)
    _, hb2 = add("Bushing flat v0 dt/2", "bushing", 0.0, 3.0, dt=DT / 2, v0=(0.01, 0, 0))
    cases[-1].update(dict(zip(("f_tangential_Hz", "zeta_tangential"), osc_fit(hb2[0], hb2[1], ft0))))
    add("SMC OneStep 2deg dt/2", "SMC", 2.0, 10.0, dt=DT / 2, tdm="OneStep")
    add("NSC 2deg PSOR50 dt/2", "NSC", 2.0, 10.0, dt=DT / 2)

    out = {"meta": {"script": "04_scripts/02_chrono/test_stick_friction.py", "pychrono": ch.__version__ if hasattr(ch, "__version__") else "10.0.0",
                    "units": "SI, Z-up, g=(0,0,-9.80665)", "slip": "displacement of the block along the downhill tangent from the start [m]",
                    "default_slip_velocity_threshold_m_s": ch.ChSystemSMC().GetSlipVelocityThreshold(),
                    "default_tangential_model": int(ch.ChSystemSMC().GetTangentialDisplacementModel()),
                    "ground_mass_kg": GROUND_MASS},
           "reference": ref, "cases": cases}
    (OUT / "stick_friction.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    lab = {"Bushing 2deg": "Bushing 2deg (elastic only, slip 0)", "NSC 2deg PSOR50": "NSC 2deg PSOR50 (< 1e-6 mm)"}
    for nm, ls in (("SMC OneStep 2deg", "-"), ("SMC MultiStep 2deg", "--"), ("SMC None 2deg", ":"),
                   ("Bushing 2deg", "-"), ("NSC 2deg PSOR50", "-")):
        T, S = hist[nm][0], hist[nm][1]
        ax[0].plot(T, np.maximum(np.abs(S), 1e-9) * 1e3, ls, label=lab.get(nm, nm))
    ax[0].axhline(0.1, color="k", ls="--", lw=0.8, label="V12 slip limit 0.1 mm")
    ax[0].set_yscale("log"); ax[0].set_xlabel("time [s]"); ax[0].set_ylabel("|displacement along slope| [mm]")
    ax[0].set_title("2 deg slope, m = %.0f kg, mu = %.1f, dt = %g s" % (MASS, MU, DT)); ax[0].legend(fontsize=8)
    for nm, ls in (("SMC OneStep flat v0", "-"), ("SMC MultiStep flat v0", "--"), ("Bushing flat v0", "-"),
                   ("NSC flat v0 PSOR50", "-")):
        T, S = hist[nm][0], hist[nm][1]
        ax[1].plot(T, S * 1e3, ls, label=nm)
    ax[1].set_xlim(0, 1.5)
    ax[1].set_xlabel("time [s]"); ax[1].set_ylabel("tangential displacement x [mm]")
    ax[1].set_title("flat floor, v0 = 10 mm/s (stick spring: %.2f Hz)" % ref["f_tangential_Hz"])
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "stick_friction.png", dpi=120)
    print("written", OUT / "stick_friction.json")


if __name__ == "__main__":
    main()
