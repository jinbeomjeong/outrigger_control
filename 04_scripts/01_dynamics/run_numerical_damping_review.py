"""Numerical damping and stability of the Chrono L1 / L2b-NSC time stepping, by mode (S0 item 1 follow-up).

Background (06_analysis/01_chrono/00_conventions/smc_damping.json, 05_tests/chrono/test_smc_damping.py, cad-expert 2026-10-20):
Chrono 10 SMC contact forces are integrated explicitly by EULER_IMPLICIT_LINEARIZED (SetContactStiff(True) changes
nothing): a single pad sphere on the floor behaves like semi-implicit (symplectic) Euler with explicit damping, no
omega dt / 2 numerical damping (gn = 0 -> zeta -1e-5). The rule of 00_docs/01_dynamics/dynamics_model.md 4.3
("zeta_num ~ omega dt / 2 <= 0.1 zeta_1") assumed a fully implicit (backward Euler) treatment of every force.

Discrete model (this script; ASSUMPTION for the bushing part, to be confirmed by V8(a)):
  * explicit:  SMC normal contact (pad spheres, crawler spheres) stiffness K_E incl. the geometric preload term,
               SMC damping C_E (gn); L2b-NSC Python axial force law (motor force set before the step)
  * implicit:  ChLoadBodyBodyBushing* (ChLoad: Jacobians K_I, R_I enter the linearised implicit step), constraints
  M (v' - v) = dt [ -K_E x - C_E v - K_I (x + dt v') - C_I v' ],  x' = x + dt v'
  For a mode with implicit strain-energy share r = phi^T K_I phi / omega^2 the numerical damping is
  zeta_num ~ r omega dt / 2 (backward Euler on the implicit part only); the explicit part is symplectic (no drift).
  Stability of an explicit spring-dashpot mode: dt < (2 / omega) (sqrt(1 + zeta^2) - zeta).

Checks: (1) the map reproduces the cad-expert single-sphere case (70.72 Hz, zeta 0.2884 at dt 1e-4, symplectic);
(2) zeta_num from the 12x12 map eigenvalues vs r omega dt / 2; (3) fully implicit map vs omega dt / 2 (old rule).

Frames/signs: body x fwd, y left, z up; q = [ux, uy, uz, phi, theta, psi] about the CoM of superstructure + 4 rods
at e_op (dyn_model.DOF6). g = -9.80665 z. Writes 06_analysis/00_dynamics/numerical_damping_review.json.

Run (dynamics-dev, activated, project root):
    C:\\ProgramData\\miniforge3\\Scripts\\conda.exe run -n dynamics-dev python -I 04_scripts/01_dynamics/run_numerical_damping_review.py
Deterministic, < 5 s.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "numerical_damping_review.json"
SMC_JSON = dm.PROJECT_ROOT / "06_analysis" / "01_chrono" / "00_conventions" / "smc_damping.json"
DTS = (5e-5, 1e-4, 2e-4, 5e-4, 1e-3)
SHARE = 0.1   # rule: zeta_num <= 10 % of the physical modal zeta (dynamics_model.md 4.3)


def r(x, n=6):
    if isinstance(x, dict):
        return {k: r(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    return x


def step_map(M, KE, CE, KI, CI, dt):
    """12x12 (2n x 2n) one-step map of the mixed explicit/implicit scheme, state [x; v]."""
    n = M.shape[0]
    A = M + dt * CI + dt * dt * KI
    Ainv = np.linalg.inv(A)
    Vv = Ainv @ (M - dt * CE)
    Vx = -dt * Ainv @ (KE + KI)
    T = np.zeros((2 * n, 2 * n))
    T[n:, :n] = Vx
    T[n:, n:] = Vv
    T[:n, :n] = np.eye(n) + dt * Vx
    T[:n, n:] = dt * Vv
    return T


def discrete_modes(T, dt):
    """Oscillatory eigenvalue pairs of the map -> (f_Hz, zeta) sorted by frequency (one per pair)."""
    lam = np.linalg.eigvals(T)
    lam = lam[np.imag(lam) > 1e-12]
    s = np.log(lam) / dt
    wn = np.abs(s)
    z = -np.real(s) / wn
    idx = np.argsort(wn)
    return wn[idx] / (2 * math.pi), z[idx], float(np.max(np.abs(np.linalg.eigvals(T))))


def max_stable_dt(M, KE, CE, KI, CI, lo=1e-6, hi=1.0):
    """Largest dt with spectral radius <= 1 (bisection; the map is stable for small dt)."""
    def rho(dt):
        return float(np.max(np.abs(np.linalg.eigvals(step_map(M, KE, CE, KI, CI, dt)))))
    if rho(hi) <= 1 + 1e-12:
        return float("inf")
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if rho(mid) <= 1 + 1e-12 else (lo, mid)
    return lo


def sdof_limit(omega, zeta):
    """Explicit symplectic Euler with explicit damping: dt < (2/omega)(sqrt(1+zeta^2) - zeta)."""
    return 2.0 / omega * (math.sqrt(1 + zeta * zeta) - zeta)


def l1_level(p, geo, lvl):
    L1 = p["contact"]["rigid_floor"]["L1"]
    kn = np.array([float(L1["kn_per_pad_N_m"][n]) for n in dm.LEG_NAMES])
    kt = np.array([float(L1["kt_per_pad_N_m"][n]) for n in dm.LEG_NAMES])
    cn = np.array([float(L1["cn_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
    ct = np.array([float(L1["ct_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
    e_op = np.array([float(L1["derivation"]["operating_extension_m"][n]) for n in dm.LEG_NAMES])
    bw = dm.body_with_rods(p, geo, lvl, e_op)
    xy = geo.pad_xy
    Fc, _, _ = dm.static_loads(kn, xy, bw.mass * geo.g, bw.com[:2])
    pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
    K = dm.stiffness_6dof(bw, pad_pts, kn, kt, Fc)
    KE = dm.stiffness_6dof(bw, pad_pts, kn, np.zeros(4), Fc)   # SMC normal + geometric preload (explicit)
    KI = K - KE                                                # bushings (implicit)
    M = dm.mass_6dof(bw)
    CE = np.zeros((6, 6)); CI = np.zeros((6, 6))
    for i in range(4):
        ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
        CE += cn[i] * np.outer(az, az)
        CI += ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
    w2, f_u, Phi, cls, orth = dm.modal(M, K, list(dm.DOF6))
    fd, zd = dm.complex_modes(M, K, CE + CI)
    om = np.sqrt(w2[:6])
    share_I = np.array([Phi[:, j] @ KI @ Phi[:, j] / w2[j] for j in range(6)])
    share_cI = np.array([Phi[:, j] @ CI @ Phi[:, j] / (Phi[:, j] @ (CE + CI) @ Phi[:, j]) for j in range(6)])
    out = {"f_undamped_Hz": r(f_u[:6], 6), "mode_content": cls[:6], "zeta_physical": r(zd, 4),
           "implicit_strain_energy_share r (bushing)": r(share_I, 4),
           "implicit_damping_share (bushing c_t)": r(share_cI, 4),
           "mass_orthogonality_max": r(float(orth), 3)}
    per_dt = {}
    for dt in DTS:
        # undamped maps: isolate the numerical damping
        Z = np.zeros((6, 6))
        f_mix, z_mix, _ = discrete_modes(step_map(M, KE, Z, KI, Z, dt), dt)
        f_imp, z_imp, _ = discrete_modes(step_map(M, Z, Z, K, Z, dt), dt)      # old assumption: all implicit
        f_exp, z_exp, _ = discrete_modes(step_map(M, K, Z, Z, Z, dt), dt)      # all explicit (symplectic)
        f_dmp, z_dmp, rho = discrete_modes(step_map(M, KE, CE, KI, CI, dt), dt)
        per_dt[f"{dt:g}"] = {
            "zeta_num_mixed (map, C = 0)": r(z_mix, 4),
            "zeta_num_estimate r omega dt / 2": r(share_I * om * dt / 2, 4),
            "zeta_num_all_implicit (map) / omega dt / 2": [r(z_imp, 4), r(om * dt / 2, 4)],
            "zeta_num_all_explicit (map)": r(z_exp, 3),
            "zeta_num_mixed / zeta_physical": r(z_mix / zd, 4),
            "rule_ok (zeta_num <= 0.1 zeta_phys) per mode": [bool(v) for v in (z_mix <= SHARE * zd)],
            "damped map f_Hz / zeta": [r(f_dmp, 6), r(z_dmp, 4)],
            "spectral_radius": r(rho, 12),
        }
    out["per_dt"] = per_dt
    out["dt_max_rule_per_mode_s (zeta_num <= 0.1 zeta_phys, mixed)"] = r(SHARE * zd / (share_I * om / 2), 4)
    out["dt_max_rule_per_mode_s (old: all implicit)"] = r(SHARE * zd / (om / 2), 4)
    out["stability_limit_dt_s (mixed map, damped)"] = r(max_stable_dt(M, KE, CE, KI, CI), 4)
    return out


def main():
    t0 = time.perf_counter()
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    res = {"meta": {"script": "04_scripts/01_dynamics/run_numerical_damping_review.py",
                    "params": "02_params/rexome33.yaml (read only)",
                    "frame": "body x fwd, y left, z up; q = [ux, uy, uz, phi, theta, psi] about the CoM of superstructure + 4 rods at e_op",
                    "gravity_m_s2": [0.0, 0.0, -geo.g],
                    "scheme": __doc__.split("Discrete model")[1].split("Checks:")[0].strip(),
                    "assumption": ("bushing loads (ChLoadBodyBodyBushing*) are treated implicitly by EULER_IMPLICIT_LINEARIZED "
                                   "(ChLoad Jacobians); not measured yet -> V8(a) confirms (zeta_num of mode 1 ~ r omega dt / 2)")}}

    # ---- (1) single-sphere check against the cad-expert measurement
    smc = json.loads(SMC_JSON.read_text(encoding="utf-8"))
    chk = []
    for c in smc["cases"]:
        if c["name"] not in ("floor_1e9", "gn_x0", "floor_1"):
            continue
        # moving sphere mass (the floor is fixed); the damping is gn m_eff (c_expected)
        m = float(c["mass_kg"]); k = float(c["k_expected_N_m"]); cc = float(c["c_expected_N_s_m"]); dt = float(c["dt_s"])
        M1 = np.array([[m]]); Z = np.zeros((1, 1))
        f_, z_, _ = discrete_modes(step_map(M1, np.array([[k]]), np.array([[cc]]), Z, Z, dt), dt)
        fI, zI, _ = discrete_modes(step_map(M1, Z, Z, np.array([[k]]), np.array([[cc]]), dt), dt)
        chk.append({"case": c["name"], "dt_s": dt,
                    "measured f_Hz / zeta": [r(c["f_measured_Hz"], 6), r(c["zeta_measured"], 5)],
                    "map explicit (symplectic) f_Hz / zeta": [r(float(f_[0]), 6), r(float(z_[0]), 5)],
                    "map implicit (backward Euler) f_Hz / zeta": [r(float(fI[0]), 6), r(float(zI[0]), 5)],
                    "cad-expert f_discrete / zeta_discrete": [r(c["f_discrete_Hz"], 6), r(c["zeta_discrete"], 5)]})
    res["check_single_sphere_vs_smc_damping_json"] = chk

    # ---- (2) L1 modes, three levels
    res["L1"] = {lvl: l1_level(p, geo, lvl) for lvl in dm.LEVELS}
    res["L2b_NSC_note"] = ("in contact the NSC constraint pins each rod vertically, so the 6-DoF body problem is the L1 one "
                           "with the explicit Python axial force law in place of the SMC spring (same k, same bushing): the "
                           "shares r and the dt bounds of L1 apply (L2b-NSC modes differ from L1 by < 0.3 %)")

    # ---- (3) stability limits of explicit local modes (dt < (2/omega)(sqrt(1+zeta^2) - zeta))
    L1 = p["contact"]["rigid_floor"]["L1"]
    m_rod = float(np.mean([p["legs"][n]["moving_part"]["mass_kg"] for n in dm.LEG_NAMES]))
    k_l1 = max(float(L1["kn_per_pad_N_m"][n]) for n in dm.LEG_NAMES)
    c_l1 = max(float(L1["cn_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES)
    act = p["actuator"]
    c_oil = max(float(act["L2b_NSC"]["oil_damping_N_s_m"][n]) for n in dm.LEG_NAMES)
    c_oil_mv = max(float(act["L2b_NSC"]["oil_damping_moving_N_s_m"][n]) for n in dm.LEG_NAMES)
    kc = float(p["contact"]["rigid_floor"]["concrete"]["k_N_m"])
    ko_l2 = 1.0 / (1.0 / k_l1 - 1.0 / kc)   # oil + rod + frame (L1 kn minus the concrete in series)
    cr = p["contact"]["crawler"]
    loc = {}

    def add(name, k, m, c, note):
        om = math.sqrt(k / m); z = c / (2 * math.sqrt(k * m))
        lim = sdof_limit(om, z)
        loc[name] = {"k_N_m": r(k), "m_kg": r(m), "c_N_s_m": r(c), "f_Hz": r(om / 2 / math.pi, 5), "zeta": r(z, 4),
                     "dt_stability_limit_s": r(lim, 4), "omega_dt at 1e-4 / 2e-4": [r(om * 1e-4, 4), r(om * 2e-4, 4)],
                     "dt_for_50_points_per_period_s": r(2 * math.pi / om / 50, 4), "note": note}

    add("pad sphere on floor, free rod (SMC test configuration; not present in L1, where the rod is held by the motor)",
        k_l1, m_rod, c_l1, "cad-expert single-sphere test; in L1 the contact acts on the body (modes <= 8.04 Hz)")
    add("L2b-NSC rod in the air on the explicit axial force law (locked damping)", k_l1, m_rod, c_oil,
        "rod separated from the floor (contact open); dynamics_model.md 4.3 rod rule")
    add("L2b-NSC rod in the air on the explicit axial force law (moving damping)", k_l1, m_rod, c_oil_mv,
        "valve open (zeta 0.10 heave basis -> about 1 on the rod)")
    zeta_rod = 0.3
    add("L2 rod between oil spring and SMC concrete contact (both explicit)", ko_l2 + kc, m_rod,
        2 * zeta_rod * math.sqrt((ko_l2 + kc) * m_rod), "L2 rod local mode, total zeta 0.30 (dynamics_model.md 3.4)")
    for scale in dm.crawler_kn_scales(p):
        xy, kk, cc = dm.crawler_points(p, scale)
        bw0 = dm.body_with_rods(p, geo, "top", np.zeros(4))
        add(f"crawler heave on layout D (kn_total x{scale:g}, all roller spheres, body mass)", float(kk[0]) * int((dm.crawler_gaps(p) <= 0).sum()),
            bw0.mass, float(cc[0]) * int((dm.crawler_gaps(p) <= 0).sum()), "explicit SMC crawler spheres act on the superstructure body")
    res["explicit_local_modes"] = loc
    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps({"check": chk, "top": {k: v for k, v in res["L1"]["top"].items() if k != "per_dt"},
                      "top_1e-4": res["L1"]["top"]["per_dt"]["0.0001"], "top_2e-4": res["L1"]["top"]["per_dt"]["0.0002"],
                      "local": loc}, indent=1, ensure_ascii=False))
    print("written", OUT)


if __name__ == "__main__":
    main()
