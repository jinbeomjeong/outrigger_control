"""V7 diagnostic: modal damping of the 6 rigid-body modes when the damping inputs are wrong.

Question (S2a, chrono_build_plan.md): can the 1st/2nd rocking-mode zeta identified in Chrono tell a
"bushing damping entered as c_t instead of c_t/2" error (tangential damping x2) apart from the nominal model?

Models (same as run_reference.py, dynamics_model.md 3.4):
  * L1 6-DoF: superstructure + 4 rods rigid with the body (rigid / locked motor, S2a has no motor or crawler),
    pads = vertical spring k_n + dashpot c_n (SMC Hooke) and tangential spring k_t + dashpot c_t (ground bushing).
  * L2b-NSC 10-DoF: superstructure 6 + 4 rod axial DoF, axial force law (k_ax, c_oil locked), lateral bushing
    (k_t, c_t), rigid NSC contact ~ k_c = 1e13 N/m without dashpot.
Damping values are read from reference.json (= YAML rev. 7), stiffness / mass are rebuilt with dyn_model.

Cases: nominal; c_t x2 (bushing input = c_t, R7 violation); c_n x2; c_t x0.5; plus input-error references:
c_t = 0 (bushing damping missing), c_n x m_eff/m_moving with a 1 kg floor (g_n with floor mass 1 kg),
c_n x m_moving (g_n entered as c_n, unit error).

Mode tracking: each complex mode is matched to an undamped mode by mass-weighted MAC of its displacement part.
zeta_i = -Re(lambda)/|lambda|. Light-damping split: zeta_i = zeta_i^n + zeta_i^t (first-order, phi^T C phi / 2 omega).

Run (dynamics-dev, activated):
    C:\\ProgramData\\miniforge3\\Scripts\\conda.exe run -n dynamics-dev python -I 04_scripts/01_dynamics/run_v7_diagnostic.py
Writes 06_analysis/00_dynamics/v7_diagnostic.json. Deterministic. Does not modify reference.json.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eig, eigh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

REF = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "v7_diagnostic.json"
KC_RIGID = 1e13
L1_KEY = "L1_rigid_motor_lumped_contact"
NSC_KEY = "L2b_NSC_force_motor_axial_spring_lateral_bushing"
DT_RUN = 1.0e-4  # s, simulation.L1.dt_s (rev. 7); numerical damping of EULER_IMPLICIT_LINEARIZED ~ omega dt / 2


def r(x, n=6):
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    return x


def tracked_modes(M, K, C, n_keep=6):
    """Damped modes matched to the first n_keep undamped modes. Returns dict of arrays (undamped order)."""
    n = M.shape[0]
    w2, Phi = eigh(K, M)
    f_und = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-np.linalg.solve(M, K), -np.linalg.solve(M, C)]])
    lam, V = eig(A)
    X = V[:n, :]
    out_f, out_fd, out_z, out_mac, out_overdamped = [], [], [], [], []
    for j in range(n_keep):
        ph = Phi[:, j]
        mac = np.abs(ph @ M @ X) ** 2 / ((ph @ M @ ph) * np.real(np.einsum("ij,ik,kj->j", X.conj(), M, X)))
        # among eigenvalues with Im >= 0, pick the best match
        cand = np.where(np.imag(lam) >= -1e-12)[0]
        k = cand[np.argmax(mac[cand])]
        wn = abs(lam[k])
        z = -np.real(lam[k]) / wn
        od = abs(np.imag(lam[k])) < 1e-9
        out_f.append(wn / (2 * np.pi)); out_fd.append(abs(np.imag(lam[k])) / (2 * np.pi))
        out_z.append(z); out_mac.append(mac[k]); out_overdamped.append(bool(od))
    return dict(f_undamped_Hz=f_und[:n_keep], f_n_Hz=np.array(out_f), f_damped_Hz=np.array(out_fd),
                zeta=np.array(out_z), mac=np.array(out_mac), overdamped=out_overdamped, Phi=Phi[:, :n_keep])


def first_order_split(Phi, parts, f_und):
    """zeta_i contribution of each damping matrix: phi^T C phi / (2 omega) (mass-normalised phi)."""
    w = 2 * np.pi * f_und
    return {k: np.array([Phi[:, i] @ Cp @ Phi[:, i] / (2 * w[i]) for i in range(Phi.shape[1])]) for k, Cp in parts.items()}


def main():
    t0 = time.perf_counter()
    ref = json.loads(REF.read_text(encoding="utf-8"))
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    g = geo.g
    A_ = dm.ASSUMPTIONS
    e_op = geo.touch_extension + A_["crawler_clearance_m"]
    xy = geo.pad_xy

    # stiffness (identical construction to run_reference.py)
    kc_nom = dm.k_concrete_westergaard()["k_slab_N_m"]
    ko_eff = dm.series(dm.k_oil(e_op), dm.k_rod(), A_["frame_bracket_stiffness_N_m"])
    kv_H = dm.series(ko_eff, kc_nom)
    kt_L1 = dm.series(dm.k_leg_lateral_legs(geo, e_op, False), kc_nom)

    T1 = ref["chrono_test_references"][L1_KEY]
    TN = ref["chrono_test_references"][NSC_KEY]
    cn0 = np.array(T1["c_pad_N_s_m"]); ct0 = np.array(T1["c_tan_N_s_m"])
    co0 = np.array(TN["c_oil_N_s_m"]); chN0 = np.array(TN["c_tangential_N_s_m"])
    m_moving = float(p["legs"]["FL"]["moving_part"]["mass_kg"])
    m_eff_1kg = m_moving * 1.0 / (m_moving + 1.0)  # Hooke gn per effective mass, floor body 1 kg

    cases_L1 = {
        "nominal (rev. 7)": (1.0, 1.0),
        "c_t x2 (bushing input = c_t, R7 violation)": (1.0, 2.0),
        "c_n x2": (2.0, 1.0),
        "c_t x0.5": (1.0, 0.5),
        "c_t = 0 (bushing damping missing)": (1.0, 0.0),
        "c_n x0.0093 (floor body 1 kg: c_n,actual = g_n m_eff, m_eff 0.991 kg)": (m_eff_1kg / m_moving, 1.0),
        "c_n -> 0 and c_t x2 (both errors)": (m_eff_1kg / m_moving, 2.0),
        "c_n x106.8 (g_n entered as c_n, unit error)": (m_moving, 1.0),
    }
    cases_NSC = {
        "nominal (rev. 7)": (1.0, 1.0),
        "c_t x2 (bushing input = c_t, R7 violation)": (1.0, 2.0),
        "c_oil x2 (axial, analogue of c_n x2)": (2.0, 1.0),
        "c_t x0.5": (1.0, 0.5),
        "c_t = 0 (bushing damping missing)": (1.0, 0.0),
    }

    res = {"meta": {
        "script": "04_scripts/01_dynamics/run_v7_diagnostic.py",
        "reference": "06_analysis/00_dynamics/reference.json (read only)",
        "purpose": "S2a V7 diagnostic: zeta of rocking modes 1-2 (and 3-6) under damping input errors",
        "frame": "body: x forward, y left, z up; reference point = CoM (L1: superstructure + rods; L2b-NSC: superstructure)",
        "gravity_m_s2": [0.0, 0.0, -g],
        "zeta_definition": "-Re(lambda)/|lambda| of the complex mode matched (mass-weighted MAC) to undamped mode i",
        "damping_values_N_s_m": {"L1_c_n": r(cn0), "L1_c_t (actual, Chrono input = c_t/2)": r(ct0),
                                  "NSC_c_oil_locked": r(co0), "NSC_c_t_lateral_bushing (actual)": r(chN0)},
        "m_moving_kg": m_moving,
        "numerical_damping_note": f"Chrono EULER_IMPLICIT_LINEARIZED adds zeta_num ~ omega dt/2 (dt = {DT_RUN} s); listed per mode",
    }, "L1": {}, "L2b_NSC": {}}

    for lvl in dm.LEVELS:
        # ---------------- L1 6-DoF
        bw = dm.body_with_rods(p, geo, lvl, e_op)
        Fb, _, _ = dm.static_loads(kv_H, xy, bw.mass * g, bw.com[:2])
        Fc = Fb  # contact force incl. rod weight (rods rigid with body, as run_reference.py)
        pad_pts = np.column_stack([xy, geo.pad_z_retracted - e_op])
        K = dm.stiffness_6dof(bw, pad_pts, kv_H, kt_L1, Fc)
        M = dm.mass_6dof(bw)
        Cn = np.zeros((6, 6)); Ct = np.zeros((6, 6))
        for i in range(4):
            ax, ay, az = dm.a_vec(pad_pts[i] - bw.com)
            Cn += cn0[i] * np.outer(az, az)
            Ct += ct0[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        lv = {}
        nom = tracked_modes(M, K, Cn + Ct)
        z_nom = nom["zeta"]
        for name, (sn, st) in cases_L1.items():
            m = tracked_modes(M, K, sn * Cn + st * Ct)
            lv[name] = {"f_n_Hz": r(m["f_n_Hz"], 5), "f_damped_Hz": r(m["f_damped_Hz"], 5), "zeta": r(m["zeta"], 4),
                        "ratio_to_nominal": r(m["zeta"] / z_nom, 4),
                        "mac_min": r(float(m["mac"].min()), 4), "overdamped": m["overdamped"]}
        split = first_order_split(nom["Phi"], {"normal c_n": Cn, "tangential c_t": Ct}, nom["f_undamped_Hz"])
        ref_z = np.array(T1["levels"][lvl]["zeta"])
        if lvl == "top":
            # S2a rule (top only): two-mode inversion of (s_n, s_t) multipliers and its sensitivity
            Z = np.column_stack([split["normal c_n"][:2], split["tangential c_t"][:2]])
            Zi = np.linalg.inv(Z)
            sig = {}
            for u in (0.05, 0.10, 0.20):
                cov = Zi @ np.diag((u * z_nom[:2]) ** 2) @ Zi.T
                sig[f"{int(u*100)}%"] = {"sigma_s_n": r(math.sqrt(cov[0, 0]), 3), "sigma_s_t": r(math.sqrt(cov[1, 1]), 3)}
            res["S2a_two_mode_inversion_top_L1"] = {
                "model": "zeta_i ~ s_n zeta_i^n + s_t zeta_i^t (i = 1, 2); s = actual/nominal damping multiplier",
                "matrix [zeta^n, zeta^t] rows mode 1, 2": r(Z, 4),
                "sigma of (s_n, s_t) for independent relative zeta errors u": sig,
                "c_t x2 is s_t = 2 (distance 1 from nominal)": True,
            }
        res["L1"][lvl] = {
            "f_undamped_Hz": r(nom["f_undamped_Hz"], 5),
            "mode_content": T1["levels"][lvl]["mode_content"],
            "cases": lv,
            "first_order_split_nominal": {k: r(v, 4) for k, v in split.items()},
            "tangential_share_nominal": r(split["tangential c_t"] / (split["tangential c_t"] + split["normal c_n"]), 4),
            "zeta_num_dt1e-4": r(2 * np.pi * nom["f_undamped_Hz"] * DT_RUN / 2, 3),
            "check_vs_reference_json": {"reference_zeta (3 sig.)": ref_z.tolist(),
                                        "max_abs_diff": r(float(np.abs(np.array(r(z_nom, 3)) - ref_z).max()), 3)},
        }

        # ---------------- L2b-NSC 10-DoF
        b = dm.body_from_params(p, lvl)
        Mx, Kx, _, labels, _ = dm.model_10dof(b, geo, e_op, ko=kv_H, kc=np.full(4, KC_RIGID), kh=kt_L1)
        _, _, Co, _, _ = dm.model_10dof(b, geo, e_op, ko=kv_H, kc=np.full(4, KC_RIGID), kh=kt_L1, co=co0)
        _, _, Ch, _, _ = dm.model_10dof(b, geo, e_op, ko=kv_H, kc=np.full(4, KC_RIGID), kh=kt_L1, ch=chN0)
        lvN = {}
        nomN = tracked_modes(Mx, Kx, Co + Ch)
        for name, (so, st) in cases_NSC.items():
            m = tracked_modes(Mx, Kx, so * Co + st * Ch)
            lvN[name] = {"f_n_Hz": r(m["f_n_Hz"], 5), "f_damped_Hz": r(m["f_damped_Hz"], 5), "zeta": r(m["zeta"], 4),
                         "ratio_to_nominal": r(m["zeta"] / nomN["zeta"], 4), "mac_min": r(float(m["mac"].min()), 4),
                         "overdamped": m["overdamped"]}
        splitN = first_order_split(nomN["Phi"], {"axial c_oil": Co, "tangential c_t": Ch}, nomN["f_undamped_Hz"])
        refN = np.array(TN["levels"][lvl]["zeta"][:6])
        res["L2b_NSC"][lvl] = {
            "f_undamped_Hz": r(nomN["f_undamped_Hz"], 5),
            "cases": lvN,
            "first_order_split_nominal": {k: r(v, 4) for k, v in splitN.items()},
            "tangential_share_nominal": r(splitN["tangential c_t"] / (splitN["tangential c_t"] + splitN["axial c_oil"]), 4),
            "check_vs_reference_json": {"reference_zeta (3 sig.)": refN.tolist(),
                                        "max_abs_diff": r(float(np.abs(np.array(r(nomN["zeta"], 3)) - refN).max()), 3)},
        }

    res["meta"]["runtime_s"] = r(time.perf_counter() - t0, 3)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---------------- summary
    for mdl in ("L1", "L2b_NSC"):
        for lvl in dm.LEVELS:
            d = res[mdl][lvl]
            print(f"\n== {mdl} {lvl}  f_und {d['f_undamped_Hz']}  t-share {d['tangential_share_nominal']}  check {d['check_vs_reference_json']['max_abs_diff']}")
            for name, c in d["cases"].items():
                print(f"  {name[:48]:48s} z {c['zeta']}  ratio {c['ratio_to_nominal']}  macmin {c['mac_min']} od {any(c['overdamped'])}")
            if mdl == "L1":
                print("  zeta_num(dt=1e-4):", d["zeta_num_dt1e-4"])
    print("\nS2a two-mode inversion:", json.dumps(res["S2a_two_mode_inversion_top_L1"]))
    print(f"\nwrote {OUT}  ({res['meta']['runtime_s']} s)")


if __name__ == "__main__":
    main()
