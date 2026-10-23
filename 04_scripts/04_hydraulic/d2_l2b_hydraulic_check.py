"""Hydraulic check of the L2b s_lock rule, the L0r sensitivity of V14 / D2 and the D2 step dynamics.

Document: 00_docs/02_hydraulic/rod_side_pressure.md section 19 (2026-10-24), answering dynamics_model.md rev. 33,
5.20.2 / 5.21.5.

Run (hydraulics-dev, activated):
    conda run -n hydraulics-dev python -I 04_scripts/04_hydraulic/d2_l2b_hydraulic_check.py

Writes 06_analysis/03_hydraulic/d2_l2b_hydraulic_check.json. Deterministic (no random numbers).

Reuses the dynamics statics (04_scripts/01_dynamics: dyn_model, l2b_reference.SlopeSystem / piecewise_path /
v14_block) unchanged; only the per-leg oil stiffness functions are rebuilt here for L0r, L0h, beta variants.

Parts
  A  D2 static first events (top level, base point x 3.2027 m) over L0r {0.02 .. 0.1} x L0h {0.05, 0.08} x
     beta {0.69, 1.0, 1.6} GPa, L2b (k at the levelled extension) and L1-R (k at e_op), after_extend / after_retract.
  B  Decomposition of the roll 4.4 deg L2b drop: k_h(e_i) only / k_r(e_i) only.
  C  V14 RL+ thresholds (L1-R after extend, k at e_i) over L0r.
  D  Nonlinear check of "k frozen at s_lock": incremental statics with the column lengths following the piston
     (exact log law of a trapped volume) and optionally beta(p) = beta0 + K' (p - p_ref).
  E  D2 step / ramp dynamic amplification on the 10-DoF linear model (loaded legs head only past the knee, unloaded
     legs LOCK k1), beta 0.69 / 1.0 / 1.6 GPa: dynamic first-event P, time to peak, head pressure rise rate.

Units SI inside; pressures gauge (Pa g) unless stated; forces compression +; body x fwd, y left, z up.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import l2b_reference as l2  # noqa: E402

OUT = ROOT / "06_analysis" / "03_hydraulic" / "d2_l2b_hydraulic_check.json"
FLOORS = {"level": (0.0, 0.0), "pitch +3.2": (0.0, 3.2), "pitch -3.2": (0.0, -3.2),
          "roll +4.4": (4.4, 0.0), "roll -4.4": (-4.4, 0.0)}
XY_BASE = (3.2027, 0.0028)
L0R_GRID = (0.02, 0.035, 0.05, 0.075, 0.10)
L0H_GRID = (0.05, 0.08)
BETA_GRID = (0.69e9, 1.0e9, 1.6e9)
P_WARN, P_LOCK = 345e5, 350e5
KPRIME = 10.0           # ASSUMPTION: tangent-modulus pressure slope of mineral oil (dK/dp), liquid only
P_REF_BETA = 100e5      # ASSUMPTION: pressure at which beta_eff = beta0 (mid locked range)
KC_DYN = 1.0e10         # vertical contact stiffness for the dynamic model (rigid w.r.t. k_out ~2e8)
R = lambda x, n=4: (np.round(np.asarray(x, float), n).tolist() if np.ndim(x) else round(float(x), n))  # noqa: E731


def patched(lp0, geo, L0r=None, L0h=None, beta=None):
    lp = dict(lp0)
    L0r = lp0["L0r"] if L0r is None else L0r
    L0h = lp0["L0h"] if L0h is None else L0h
    beta = lp0["beta"] if beta is None else beta
    A_p, A_ann, k_out, smax = lp0["A_p"], lp0["A_ann"], lp0["k_out"], geo.stroke
    lp.update(L0r=L0r, L0h=L0h, beta=beta)
    lp["k_h_f"] = lambda s: beta * A_p / (L0h + np.asarray(s, float))
    lp["k_r_f"] = lambda s: beta * A_ann / (smax - np.asarray(s, float) + L0r)
    lp["k2_f"] = lambda s: dm.series(lp["k_h_f"](s), k_out)
    lp["k1_f"] = lambda s: dm.series(lp["k_h_f"](s) + lp["k_r_f"](s), k_out)
    return lp


def setup():
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    lp0 = l2.leg_parameters(p, geo)
    body = dm.body_from_params(p, "top")
    F_min = float(p["control"]["F_min_cylinder_N"])
    clr = dm.ASSUMPTIONS["crawler_clearance_m"]
    return p, geo, lp0, body, F_min, clr


def first_events(sysm, lp, k_h, k_r, F0, N0, p_r0, F_min, xy=XY_BASE):
    pw = l2.piecewise_path(sysm, lp, k_h, k_r, ["LOCK"] * 4, F0, N0, f_unit=sysm.vertical_force(xy), F_min=F_min,
                           lam_max=5e6, p_r0=np.array(p_r0, float))
    ev = pw["events"]
    out = {k: ([R(v["lam"] * 1e-3, 2), v["leg"]]) for k, v in ev.items()}
    first = min(((v["lam"], k) for k, v in ev.items()), default=None)
    out["first"] = None if first is None else [first[1], R(first[0] * 1e-3, 2)]
    out["p_r_max_bar"] = R(pw["p_r_max_Pa"] * 1e-5, 2)
    return out


# ---------------------------------------------------------------- A, B
def part_A_B(p, geo, lp0, body, F_min, clr):
    res, dec = {}, {}
    e_op = np.full(4, 0.0) + lp0["e_op"]
    for fname, (ro, pi) in FLOORS.items():
        ext = l2.levelled_extension(geo, ro, pi, clr)
        sysm = l2.SlopeSystem(body, geo, ext, lp0["kt"], pi, ro)
        res[fname] = {"extension_m": R(ext, 4), "cases": {}}
        for beta in BETA_GRID:
            for L0h in L0H_GRID:
                for L0r in L0R_GRID:
                    if (beta != 1.0e9 or L0h != 0.05) and L0r not in (0.02, 0.05, 0.10):
                        continue
                    lp = patched(lp0, geo, L0r, L0h, beta)
                    for model, s_k in (("L2b", ext), ("L1-R", e_op)):
                        if model == "L1-R" and not (beta == 1.0e9 and L0h == 0.05):
                            continue
                        k_h, k_r = lp["k_h_f"](s_k), lp["k_r_f"](s_k)
                        _, F0, N0 = sysm.place_and_settle(dm.series(k_h, lp["k_out"]))
                        for lock, pr0 in (("after_extend", lp0["p_r0_ext"]), ("after_retract", lp0["p_r0_ret"])):
                            if lock == "after_retract" and not (beta == 1.0e9 and L0h == 0.05):
                                continue
                            key = f"{model} | {lock} | beta {beta * 1e-9:.2f} | L0h {L0h:.3f} | L0r {L0r:.3f}"
                            res[fname]["cases"][key] = first_events(sysm, lp, k_h, k_r, F0, N0, pr0, F_min)
        # B: decomposition (beta 1.0, L0h 0.05, L0r 0.05, after_extend)
        if fname.startswith("roll") or fname == "level":
            lp = patched(lp0, geo)
            d = {}
            for lab, sh, sr in (("k_h(e_i), k_r(e_i) = L2b", ext, ext), ("k_h(e_op), k_r(e_op) = L1-R", e_op, e_op),
                                ("k_h(e_i), k_r(e_op)", ext, e_op), ("k_h(e_op), k_r(e_i)", e_op, ext)):
                k_h, k_r = lp["k_h_f"](sh), lp["k_r_f"](sr)
                _, F0, N0 = sysm.place_and_settle(dm.series(lp["k_h_f"](ext), lp["k_out"]))
                d[lab] = first_events(sysm, lp, k_h, k_r, F0, N0, lp0["p_r0_ext"], F_min)
                d[lab]["k_h_1e7"] = R(k_h * 1e-7, 3)
                d[lab]["k_r_1e7"] = R(k_r * 1e-7, 3)
            # head-only rod side (rod chamber off) with k_h(e_i)
            k_h = lp["k_h_f"](ext)
            _, F0, N0 = sysm.place_and_settle(dm.series(k_h, lp["k_out"]))
            pw = l2.piecewise_path(sysm, lp, k_h, lp["k_r_f"](ext), ["HEAD"] * 4, F0, N0,
                                   f_unit=sysm.vertical_force(XY_BASE), F_min=F_min, lam_max=5e6,
                                   p_r0=np.array(lp0["p_r0_ext"], float))
            d["head only k_h(e_i) (rod side off)"] = {k: [R(v["lam"] * 1e-3, 2), v["leg"]] for k, v in pw["events"].items()}
            dec[fname] = d
    return res, dec


# ---------------------------------------------------------------- C
def part_C(p, geo, lp0):
    out = {}
    for L0r in L0R_GRID:
        lp = patched(lp0, geo, L0r=L0r)
        blk = l2.v14_block(p, geo, lp, {"cases": {}})
        for case, c in blk["cases"].items():
            a = c["RL+"]["L1R_after_extend"]; h = c["RL+"]["head_only"]
            out.setdefault(case, {"extension_m": c["extension_m"], "head_only": {
                "F_min_mm": h["F_min_threshold_mm"]["value"], "liftoff_mm": h["liftoff_threshold_mm"]["value"]}})
            out[case][f"L0r {L0r:.3f}"] = {
                "secant_+1mm_dF_RL_kN": R(a["dF_cyl_secant_+1mm_N (judged, crosses the knees)"][2] * 1e-3, 3),
                "F_min_mm": a["F_min_threshold_mm"]["value"], "F_min_leg": a["F_min_threshold_mm"]["leg"],
                "liftoff_mm": a["liftoff_threshold_mm"]["value"],
                "liftoff_vs_head_only_%": R(100 * (a["liftoff_threshold_mm"]["value"] /
                                                   h["liftoff_threshold_mm"]["value"] - 1), 1),
                "f_LOCK_Hz_first6": c["f_Hz_LOCK (first 6, rocking judged +-3 %)"]}
    return out


# ---------------------------------------------------------------- D
def nonlinear_path(sysm, lp, ext, p_r0, F_min, mode, dP=250.0, P_max=1.2e6, kprime=KPRIME):
    """Incremental statics; mode 'frozen' (k at s_lock), 'geom' (columns follow the piston), 'geom+beta(p)'."""
    A_p, A_ann, k_out, smax = lp["A_p"], lp["A_ann"], lp["k_out"], sysm.geo.stroke
    b0 = lp["beta"]
    Lh0, Lr0 = lp["L0h"] + ext, smax - ext + lp["L0r"]
    p_floor = lp["p_floor_g"]
    _, F0, N0 = sysm.place_and_settle(dm.series(b0 * A_p / Lh0, k_out))
    p_r = np.array(p_r0, float).copy()
    p_h = (F0 + p_r * A_ann) / A_p
    x = np.zeros(4)                   # piston travel into the head chamber [m]
    cav = np.zeros(4)                 # rod-side cavity volume [m^3] (state KNEE)
    F, N = F0.copy(), N0.copy()
    f_u = sysm.vertical_force(XY_BASE)
    ev, P = {}, 0.0

    def beta_of(pp):
        if mode != "geom+beta(p)":
            return np.full_like(pp, b0)
        return np.maximum(b0 + kprime * (pp - P_REF_BETA), 0.3e9)

    while P < P_max:
        if mode == "frozen":
            Lh, Lr = Lh0, Lr0
        else:
            Lh, Lr = Lh0 - x, Lr0 + x
        kh = beta_of(p_h) * A_p / Lh
        kr = np.where(cav > 0, 0.0, beta_of(np.maximum(p_r, 0.0)) * A_ann / Lr)
        if mode == "frozen":
            kr = np.where(cav > 0, 0.0, b0 * A_ann / Lr0)
            kh = b0 * A_p / Lh0
        ko = dm.series(kh + kr, k_out)
        _, dF, dN = sysm.solve(ko, None, f_u * dP)
        dx = dF / (kh + kr)
        F_new, N_new = F + dF, N + dN
        for i in range(4):
            if cav[i] > 0:
                cav[i] += A_ann[i] * dx[i]
                if cav[i] <= 0:
                    cav[i] = 0.0
            else:
                p_r[i] -= kr[i] / A_ann[i] * dx[i]
                if p_r[i] <= p_floor:
                    cav[i] = 1e-12; p_r[i] = p_floor
            p_h[i] += kh[i] / A_p[i] * dx[i]
        x += dx
        P += dP
        for i in range(4):
            if "F_min" not in ev and F_new[i] <= F_min < F[i]:
                ev["F_min"] = [R(P * 1e-3, 2), dm.LEG_NAMES[i]]
            if "liftoff" not in ev and N_new[i] <= 0 < N[i]:
                ev["liftoff"] = [R(P * 1e-3, 2), dm.LEG_NAMES[i]]
            if "p_h_345bar" not in ev and p_h[i] >= P_WARN:
                ev["p_h_345bar"] = [R(P * 1e-3, 2), dm.LEG_NAMES[i]]
        F, N = F_new, N_new
        if "liftoff" in ev:
            break
    first = min(((v[0], k) for k, v in ev.items()), default=None)
    ev["first"] = None if first is None else [first[1], first[0]]
    ev["piston_travel_at_end_mm"] = R(x * 1e3, 3)
    ev["k_h_change_at_end_% (geometry)"] = R(100 * (Lh0 / (Lh0 - x) - 1), 2)
    ev["k_r_change_at_end_% (geometry)"] = R(100 * (Lr0 / (Lr0 + x) - 1), 2)
    return ev


def part_D(geo, lp0, body, F_min, clr):
    out = {}
    for fname in ("level", "roll +4.4", "roll -4.4", "pitch +3.2"):
        ro, pi = FLOORS[fname]
        ext = l2.levelled_extension(geo, ro, pi, clr)
        sysm = l2.SlopeSystem(body, geo, ext, lp0["kt"], pi, ro)
        for L0r in (0.02, 0.05, 0.10):
            lp = patched(lp0, geo, L0r=L0r)
            for mode in ("frozen", "geom", "geom+beta(p)"):
                out[f"{fname} | L0r {L0r:.2f} | {mode}"] = nonlinear_path(sysm, lp, ext, lp0["p_r0_ext"], F_min, mode)
    return out


# ---------------------------------------------------------------- E
def dyn_case(geo, lp, body, ext, roll, pitch, F_min, t_end=4.0, dt=5e-4):
    """Linear 10-DoF step / ramp response per unit P; leg state from the static increment sign."""
    sysm = l2.SlopeSystem(body, geo, ext, lp["kt"], pitch, roll)
    k_h, k_r = lp["k_h_f"](ext), lp["k_r_f"](ext)
    k2 = dm.series(k_h, lp["k_out"]); k1 = dm.series(k_h + k_r, lp["k_out"])
    _, F0, N0 = sysm.place_and_settle(k2)
    _, dF1, _ = sysm.solve(k1, None, sysm.vertical_force(XY_BASE))
    ko = np.where(dF1 > 0, k2, k1)            # loaded legs pass the knee within 4-7 kN -> head only
    rat = np.where(dF1 > 0, 0.0, k_r / (k_h + k_r))
    M, K, C, _, _ = dm.model_10dof(body, geo, ext, ko=ko, kc=np.full(4, KC_DYN), kh=lp["kt"], co=lp["c_lock"],
                                   cc=np.zeros(4), ch=lp["ct"])
    f = np.zeros(10)
    _, _, az = dm.a_vec(np.array([XY_BASE[0], XY_BASE[1], 0.0]) - body.com)
    f[:6] = -az
    bvec = []
    for i in range(4):
        d_att = np.array([*geo.pad_xy[i], geo.attach_z[i]]) - body.com
        bb = np.zeros(10); bb[:6] = dm.a_vec(d_att)[2]; bb[6 + i] = -1.0
        bvec.append(bb)
    Bm = np.array(bvec)
    n = 10
    Minv = np.linalg.inv(M)
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-Minv @ K, -Minv @ C]])
    Bc = np.concatenate([np.zeros(n), Minv @ f])
    Ad = expm(A * dt)
    Bd = np.linalg.solve(A, (Ad - np.eye(2 * n)) @ Bc)
    q_st = np.linalg.solve(K, f)
    g_st = -ko * (Bm @ q_st)                  # static leg force per unit P (N/N)
    nt = int(round(t_end / dt)) + 1
    t = np.arange(nt) * dt
    out = {"leg_state": ["head only (knee passed)" if s > 0 else "LOCK k1" for s in dF1],
           "g_static_N_per_N": R(g_st, 4), "modes": None, "shapes": {}}
    fz, zz = dm.complex_modes(M, K, C)
    out["modes"] = {"f_Hz": R(fz[:6], 3), "zeta": R(zz[:6], 4)}
    A_p, A_ann = lp["A_p"], lp["A_ann"]
    p_h0 = (F0 + lp["p_r0_ext"] * A_ann) / A_p
    for tr in (0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0):
        u = np.minimum(t / tr, 1.0) if tr > 0 else np.ones(nt)
        z = np.zeros(2 * n); G = np.zeros((nt, 4))
        for k in range(1, nt):
            z = Ad @ z + Bd * u[k - 1]       # ZOH on the sampled ramp (dt 0.5 ms)
            G[k] = -ko * (Bm @ z[:n])
        res = {}
        # event P: increasing legs -> 345 / 350 bar head; decreasing legs -> F_min (cylinder force)
        cands = []
        for i in range(4):
            gmax, gmin = G[:, i].max(), G[:, i].min()
            if g_st[i] > 0:
                for lab, lim in (("p_h_345bar", P_WARN), ("p_h_350bar", P_LOCK)):
                    # p_h = (F + p_r A_ann) / A_p; loaded leg p_r at the floor after the knee
                    Fl = lim * A_p[i] - lp["p_floor_g"] * A_ann[i]
                    Pev = (Fl - F0[i]) / gmax
                    cands.append((Pev, lab, i, float(t[G[:, i].argmax()]), gmax / g_st[i]))
            else:
                Pev = (F0[i] - F_min) / -gmin
                cands.append((Pev, "F_min", i, float(t[G[:, i].argmin()]), gmin / g_st[i]))
        cands.sort()
        for Pev, lab, i, tpk, daf in cands:
            key = f"{lab} {dm.LEG_NAMES[i]}"
            if lab in [k.split()[0] for k in res]:
                continue
            res[key] = {"P_kN": R(Pev * 1e-3, 1), "t_peak_s": R(tpk, 3), "DAF": R(daf, 3)}
        Pf, labf, i_f, _, _ = cands[0]
        # head pressure rise rate of the first-event leg at that P
        Fi = F0[i_f] + Pf * G[:, i_f]
        dpdt = np.gradient((Fi * (1 - rat[i_f])) / A_p[i_f], dt)
        res["first"] = [f"{labf} {dm.LEG_NAMES[i_f]}", R(Pf * 1e-3, 1)]
        res["first_leg_max_dp_h_dt_bar_per_s"] = R(float(np.abs(dpdt).max()) * 1e-5, 0)
        res["first_leg_p_h_start_bar"] = R(p_h0[i_f] * 1e-5, 1)
        res["static_same_linear_model_P_kN"] = R(
            min(((lim * A_p[i] - lp["p_floor_g"] * A_ann[i] - F0[i]) / g_st[i]) if g_st[i] > 0 else
                ((F0[i] - F_min) / -g_st[i]) for i in range(4) for lim in (P_WARN,)) * 1e-3, 1)
        out[f"t_r {tr:.2f} s"] = res
    return out


def part_E(geo, lp0, body, F_min, clr):
    out = {}
    for fname in ("level", "roll +4.4", "pitch +3.2"):
        ro, pi = FLOORS[fname]
        ext = l2.levelled_extension(geo, ro, pi, clr)
        for beta in BETA_GRID:
            lp = patched(lp0, geo, beta=beta)
            out[f"{fname} | beta {beta * 1e-9:.2f}"] = dyn_case(geo, lp, body, ext, ro, pi, F_min)
    return out


def main():
    t0 = time.perf_counter()
    p, geo, lp0, body, F_min, clr = setup()
    res = {"meta": {"script": "04_scripts/04_hydraulic/d2_l2b_hydraulic_check.py",
                    "document": "00_docs/02_hydraulic/rod_side_pressure.md section 19",
                    "params": "02_params/rexome33.yaml (read only)",
                    "pressure": "gauge (Pa g / bar g); floor 0.1 bar abs",
                    "assumptions": {"KPRIME_dK_dp": KPRIME, "P_REF_BETA_Pa": P_REF_BETA, "KC_DYN_N_m": KC_DYN,
                                    "D2_point_xy_m": XY_BASE},
                    "baseline": {"beta_Pa": lp0["beta"], "L0h_m": lp0["L0h"], "L0r_m": lp0["L0r"],
                                 "p_r0_ext_bar": R(np.asarray(lp0["p_r0_ext"]) * 1e-5, 3),
                                 "p_r0_ret_bar": R(np.asarray(lp0["p_r0_ret"]) * 1e-5, 3), "F_min_N": F_min}}}
    res["A_D2_static"], res["B_decomposition"] = part_A_B(p, geo, lp0, body, F_min, clr)
    res["C_V14_RLplus"] = part_C(p, geo, lp0)
    res["D_nonlinear_s_lock"] = part_D(geo, lp0, body, F_min, clr)
    res["E_D2_dynamic"] = part_E(geo, lp0, body, F_min, clr)
    res["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("written", OUT, "runtime", res["meta"]["runtime_s"], "s")


if __name__ == "__main__":
    main()
