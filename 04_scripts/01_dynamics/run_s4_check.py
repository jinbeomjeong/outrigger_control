"""Independent checks for the S4 final judgement (dynamics_model.md 5.8, rev. 19).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s4_check.py
Writes 06_analysis/00_dynamics/s4_check.json (about 1 min). Does not import 03_src.

Part A - V8(b) residual structure, 1-DoF block: mass m on a ground bushing (k_t, c_t; linear spring
    and dashpot integrated implicitly as Chrono EULER_IMPLICIT_LINEARIZED does for a linear load),
    radial Coulomb return mapping in a post-step hook, Chrono using the anchor / damping state set
    one hook earlier (one-step lag, dynamics_model.md 4.6); optional explicit spring k_e (stands in
    for the explicit SMC pad contact, semi-implicit). Bookkeeping copies chrono/energy.py. Exact
    discrete identity checked: R = lag + implicit - 1/2 sum m dv^2 + 1/2 sum k_e dx^2.
    Parameters are of the S4 size (ASSUMPTION: one quarter of the machine per pad).
Part B - Chrono V8(b) 'remainder' estimate from the 1 ms records (07_results/S4_energy/<batch>):
    -1/2 sum dv^T M dv ~ -dt/2 int (m |a|^2 + alpha^T I alpha) dt (superstructure; m, I fitted to
    energy.kinetic, omega taken in body axes) and +1/2 sum k_n d_delta^2 ~ dt/2 int k_n delta_dot^2
    (delta_dot ~ d/dt (F_n / k_n), k_n = V2 value 119.29 kN / 5.73 mm). Order-of-magnitude check only.
Part C - beta sensitivity V5 / V6 against exact pad statics (P-delta): Part B of
    run_s3_lift_check.py (definitions executed up to part_b) with the pad k_n of
    reference.json L1_beta_sensitivity_top / beta_* / k_L1_N_m (k_n only, as the Chrono runs).
Part D - damping sensitivity: complex modes of the rev. 13 L1 6-DoF reference (ball centre, top)
    with all pad dashpots (c_n, c_t) scaled by zeta_leg / 0.03 (0.01, 0.10), against the first-order
    expectation zeta_nominal x scale.
Part E - beta mode shapes: mass-weighted MAC of the beta-specific reference modes against the
    nominal (1.0 GPa) modes; frequency order vs best match (mode crossing at 1.6 GPa).
Gravity (0, 0, -9.80665) m/s^2 world. Units SI. Quaternions wxyz (record) -> scipy xyzw.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.linalg as sla
from scipy.optimize import brentq

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import run_reference as rr  # noqa: E402

T0 = time.perf_counter()
P = dm.load_params(ROOT / "02_params" / "rexome33.yaml")
REF = json.load(open(ROOT / "06_analysis/00_dynamics/reference.json", encoding="utf-8"))
BATCH = ROOT / "07_results/S4_energy/batch_20261021_114627"
CHR_E = json.load(open(ROOT / "06_analysis/01_chrono/14_S4/verify_S4_L1_energy.json", encoding="utf-8"))
geo = dm.geometry_from_params(P)
LEGS = dm.LEG_NAMES
L1 = P["contact"]["rigid_floor"]["L1"]
KN = np.array([float(L1["kn_per_pad_N_m"][n]) for n in LEGS])
KT = np.array([float(L1["bushing_stiffness_per_pad_N_m"][n]) for n in LEGS])
CN = np.array([float(L1["cn_per_pad_N_s_m"][n]) for n in LEGS])
CT = np.array([float(L1["ct_per_pad_N_s_m"][n]) for n in LEGS])
E_OP = np.array([float(L1["derivation"]["operating_extension_m"][n]) for n in LEGS])
MU = float(P["contact"]["rigid_floor"]["friction"])


def r(x, n=6):
    return np.round(np.asarray(x, float), n).tolist() if np.ndim(x) else round(float(x), n)


# ------------------------------------------------------------------ Part A
def block(dt, m, kt, ct, muN, v0, ke=0.0, T=3.0, lag=True):
    x, v, a_book, a_used = 0.0, v0, 0.0, 0.0
    damp_off, prev_sl = False, False
    D_visc = D_slip = W_mu = lagE = impl = dv2 = dx2e = 0.0
    E0 = 0.5 * m * v * v
    for _ in range(int(round(T / dt))):
        c = 0.0 if damp_off else ct
        v1 = (m * v - dt * (kt * (x - a_used) + ke * x)) / (m + c * dt + kt * dt * dt)
        x1 = x + dt * v1
        dx = x1 - x
        D_visc += c * v1 * v1 * dt
        impl -= 0.5 * kt * dx * dx
        if a_book != a_used:
            lagE -= kt * (a_book - a_used) * dx
        dv2 += 0.5 * m * (v1 - v) ** 2
        dx2e += 0.5 * ke * dx * dx
        x, v = x1, v1
        prev_book = a_book
        d_tr = x - a_book
        dmax = muN / kt
        sl = abs(d_tr) > dmax
        if sl:
            d = np.sign(d_tr) * dmax
            D_slip += 0.5 * kt * (d_tr * d_tr - d * d)
            W_mu += muN * abs(d_tr - d)
            a_book = x - d
        a_used = prev_book if lag else a_book
        damp_off = prev_sl if lag else sl
        prev_sl = sl
    E = 0.5 * m * v * v + 0.5 * kt * (x - a_book) ** 2 + 0.5 * ke * x * x
    R = E - E0 + D_visc + D_slip
    return dict(dt_s=dt, R_J=R, R_rel_E0=R / E0, lag_J=lagE, implicit_J=impl, remainder_J=R - lagE - impl,
                minus_half_m_dv2_J=-dv2, plus_half_ke_dx2_J=dx2e,
                identity_error_J=R - (lagE + impl - dv2 + dx2e), slip_ratio=D_slip / W_mu,
                R_over_dissipation=R / (D_visc + D_slip))


def part_a():
    W = 382.29e3  # V1 total pad force [N]
    m = 38556.0 / 4 + float(P["legs"]["FL"]["moving_part"]["mass_kg"])
    par = dict(m=m, kt=float(KT.mean()), ct=float(CT.mean()), muN=MU * W / 4, v0=0.5)
    out = {"params (ASSUMPTION: quarter machine per pad)": {k: r(v) for k, v in par.items()}}
    for ke in (0.0, float(KN.mean())):
        rows = [block(dt, ke=ke, **par) for dt in (4e-4, 2e-4, 1e-4, 5e-5)]
        for a, b in zip(rows[:-1], rows[1:]):
            b["ratio_R(2dt)/R(dt)"] = a["R_J"] / b["R_J"]
        nolag = [block(dt, ke=ke, lag=False, **par) for dt in (2e-4, 1e-4)]
        out[f"k_e={ke:.4g}"] = {"one_step_lag": [{k: r(v, 6) for k, v in row.items()} for row in rows],
                                "no_lag": [{k: r(v, 6) for k, v in row.items()} for row in nolag]}
    return out


# ------------------------------------------------------------------ Part B
def part_b():
    out = {}
    kn = 119.29e3 / 5.73e-3
    for case, dt in (("v8b_pitch2_dt2e-04", 2e-4), ("v8b_pitch2_dt1e-04", 1e-4), ("v8b_flat_dt2e-04", 2e-4)):
        z = np.load(BATCH / case / "record" / "record.npz")
        t, v, w, q, ke = z["t"], z["body_vel"], z["body_omega"], z["body_quat_wxyz"], z["energy.kinetic"]
        cols = [0.5 * (v ** 2).sum(1)] + [0.5 * w[:, i] ** 2 for i in range(3)] + \
               [w[:, i] * w[:, j] for i, j in ((0, 1), (0, 2), (1, 2))]
        A = np.stack(cols, 1)
        c, *_ = np.linalg.lstsq(A, ke, rcond=None)
        I = np.array([[c[1], c[4], c[5]], [c[4], c[2], c[6]], [c[5], c[6], c[3]]])
        h = np.diff(t)
        acc = np.diff(v, axis=0) / h[:, None]
        alp = np.diff(w, axis=0) / h[:, None]
        mterm = -0.5 * dt * np.sum((c[0] * (acc ** 2).sum(1) + np.einsum("ni,ij,nj->n", alp, I, alp)) * h)
        F = z["F_contact_n"]
        inc = z["pad_in_contact"][:-1] & z["pad_in_contact"][1:]
        ddot = np.diff(F / kn, axis=0) / h[:, None]
        kterm = 0.5 * dt * np.sum(kn * ddot ** 2 * inc * h[:, None])
        chrono_rem = CHR_E["cases"][case]["residual_decomposition_end_J"]["remainder"]
        out[case] = {"fitted_mass_kg": r(c[0], 1), "kinetic_fit_max_rel_err": r(np.max(np.abs(A @ c - ke)) / ke.max(), 4),
                     "minus_half_dvMdv_J": r(mterm, 3), "plus_half_kn_ddelta2_J": r(kterm, 3),
                     "estimate_remainder_J": r(mterm + kterm, 3), "chrono_remainder_J": r(chrono_rem, 3)}
    return out


# ------------------------------------------------------------------ Part C
def part_c():
    src = (ROOT / "04_scripts/01_dynamics/run_s3_lift_check.py").read_text(encoding="utf-8")
    src = src[: src.index("def part_b")]
    argv = sys.argv
    sys.argv = [argv[0], str(ROOT)]
    g = {"__name__": "s3lift_defs"}
    exec(compile(src, "run_s3_lift_check_defs", "exec"), g)
    sys.argv = argv
    import csv
    ch = {}
    with open(ROOT / "06_analysis/01_chrono/14_S4/verify_S4_L1_beta.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ch.setdefault(row["beta"], {})[row["item"].split(": ", 1)[1]] = json.loads(row["chrono"])
    out = {}
    for key, c in ch.items():
        g["K_PAD"] = np.array(REF["L1_beta_sensitivity_top"][key]["k_L1_N_m"], float)
        ps, E = g["pads_static"], g["E_OP"]
        res = {}
        for exact in (True, False):
            F0 = ps(E, exact)[0]
            F1 = ps(E + np.array([1e-3, 0, 0, 0]), exact)[0]
            fm = brentq(lambda d: ps(E + np.array([d, 0, 0, 0]), exact)[0][2] - g["ROD_W"][2] - g["F_MIN"], 0, 0.04, xtol=1e-11)
            lo = brentq(lambda d: ps(E + np.array([d, 0, 0, 0]), exact)[0][2] - 1e-6, 0, 0.04, xtol=1e-11)
            res["exact" if exact else "small"] = (F1 - F0, fm * 1e3, lo * 1e3)
        (dFe, fme, loe), (dFs, fms, los) = res["exact"], res["small"]
        dFc = np.array(c["FL +1 mm contact force change"])
        fmc, loc = c["FL+ travel at F_min"], c["FL+ travel at lift-off"]
        out[key] = {"pdelta_rel (exact/small - 1)": {"dF": r(dFe / dFs - 1, 5), "F_min": r(fme / fms - 1, 5), "liftoff": r(loe / los - 1, 5)},
                    "chrono_rel_small (chrono/small - 1)": {"dF": r(dFc / dFs - 1, 5), "F_min": r(fmc / fms - 1, 5), "liftoff": r(loc / los - 1, 5)},
                    "chrono_minus_exact": {"dF_N": r(dFc - dFe, 2), "F_min_mm": r(fmc - fme, 5), "liftoff_mm": r(loc - loe, 5)}}
    return out


# ------------------------------------------------------------------ Part D / E
def l1_matrices(kn, c_scale):
    bw = dm.body_with_rods(P, geo, "top", E_OP)
    Fc, _, _ = dm.static_loads(kn, geo.pad_xy, bw.mass * geo.g, bw.com[:2])
    zb = geo.pad_z_retracted - E_OP + rr._ball_heights(P)
    K, Cn, Ct, _ = rr._l1_matrices(bw, geo.pad_xy, zb, zb, kn, KT, CN * c_scale, CT * c_scale, Fc)
    return dm.mass_6dof(bw), K, Cn + Ct


def part_d():
    M, K, C = l1_matrices(KN, 1.0)
    f0, z0 = dm.complex_modes(M, K, C)
    zl0 = float(dm.ASSUMPTIONS["modal_damping_ratio_body"])
    out = {"nominal": {"zeta_leg": zl0, "f_n_Hz": r(f0, 5), "zeta": r(z0, 6)}}
    for zl in (0.01, 0.10):
        s = zl / zl0
        f, z = dm.complex_modes(M, K, s * C)
        out[f"zeta_leg_{zl}"] = {"scale": r(s, 6), "f_n_Hz": r(f, 5), "zeta": r(z, 6),
                                 "zeta / (scale x zeta_nominal)": r(z / (s * z0), 5),
                                 "f_n / f_n_nominal - 1": r(f / f0 - 1, 6),
                                 "f_damped_Hz": r(f * np.sqrt(1 - z ** 2), 5)}
    return out


def part_e():
    sh = {}
    for key in ("beta_6.9e+08", "beta_1.0e+09", "beta_1.6e+09"):
        M, K, _ = l1_matrices(np.array(REF["L1_beta_sensitivity_top"][key]["k_L1_N_m"], float), 0.0)
        w2, Phi = sla.eigh(K, M)
        sh[key] = (np.sqrt(w2) / (2 * np.pi), Phi, M)
    _, P0, M0 = sh["beta_1.0e+09"]
    out = {}
    for key, (f, Ph, M) in sh.items():
        num = (P0.T @ M @ Ph) ** 2
        mac = num / np.outer(np.diag(P0.T @ M @ P0), np.diag(Ph.T @ M @ Ph))
        out[key] = {"f_Hz (frequency order)": r(f, 4), "MAC_vs_nominal_same_index": r(np.diag(mac), 3),
                    "best_nominal_index": mac.argmax(0).tolist(), "best_MAC": r(mac.max(0), 3)}
    return out


res = {"meta": {"script": "04_scripts/01_dynamics/run_s4_check.py", "doc": "00_docs/01_dynamics/dynamics_model.md 5.8 (rev. 19)",
                "gravity_m_s2": [0, 0, -float(P["meta"]["gravity_m_s2"])], "units": "SI"}}
res["A_block_lag_budget"] = part_a()
res["B_chrono_remainder_estimate"] = part_b()
res["C_beta_pdelta_exact_statics"] = part_c()
res["D_damping_scaled_complex_modes"] = part_d()
res["E_beta_mode_shape_MAC"] = part_e()
res["meta"]["wall_s"] = r(time.perf_counter() - T0, 1)
out = ROOT / "06_analysis/00_dynamics/s4_check.json"
json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("wrote", out, res["meta"]["wall_s"], "s")
