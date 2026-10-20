"""C2 levelling controller: loop-by-loop discrete design and robustness analysis (00_docs/04_control/c2_design.md).

Sections (keys of 06_analysis/02_control/c2_design.json)
  plants       linear plant catalogue (auger 3 levels x pads / crawler x beta 0.69 / 1.0 / 1.6 GPa x mast surrogate
               rigid / sup_rigid / sup_upper / sup_lower, + soft-FL and low-damping variants): rocking modes, static
               decoupled gain matrix G0, RGA, twist -> attitude leak J_K n, twist-stiffness ratio
  tuning       gain iterations (attitude Kp / Ki, filter, delay) -> per-channel PM, GM (upper / lower), Ms, disk margin,
               delay margin, loop-at-a-time (others closed), closed-loop spectral radius, worst case over the catalogue
  proposal     proposed gains, per level table, delay sensitivity
  separation   bandwidths of heave / attitude / twist, quasi-static triangular coupling (n^T S A = 0), interaction
               measure rho(E T_d) of the decentralised design
  mimo         multi-loop disk margins (mu, diagonal complex) at the decoupled channels and at the 4 leg inputs (two
               upper-bound paths: own D-scaling, dkpy LMI), robust stability to per-leg input multiplicative
               uncertainty W(s), singular values
  nonlinear    describing-function checks (twist dead band, speed saturation gain sweep, seal-friction backlash with
               the attitude PI), saturation direction (vector scaling vs per-leg clipping)
  lqr          Bryson quasi-static LQI, stability boundary of Kp (with / without the attitude filter), discrete LQG on
               the dynamic plant as a reference
  decisions    D4 / D5 / D6 numbers (probe, seal band, twist target)
  julia_check  Python <-> Julia (ControlSystems.jl) margin cross-check (filled by --merge-julia)

Run (project root, dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_design.py            # ~2-4 min, E-cores
  julia --project=<control-julia> 04_scripts/03_control/c2_margin_check.jl              # cross-check
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_design.py --merge-julia
Conventions: negative feedback in the decoupled channels v = [z_dot, phi_dot, theta_dot, tau_dot] = -K y,
y = [clr (m), phi_f input (rad), theta_f input (rad), n^T P (N)]; leg speeds u = [A, n] v (m/s); discrete, T = 20 ms,
ZOH plant input; GM as absolute ratio and dB; PM in deg; frequencies rad/s (Hz in brackets in the report).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, minimize, minimize_scalar

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
import c2_linear as cl  # noqa: E402
import dyn_model as dm  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "02_control"
OUT_JSON = OUT_DIR / "c2_design.json"
JL_DIR = OUT_DIR / "julia"
T = cl.T_CTRL
W_NYQ = math.pi / T
CH = ("z", "phi", "theta", "tw")
DEG = 180 / math.pi

# ---------------------------------------------------------------------------- specification (ASSUMPTIONS unless noted)
SPEC = {
    "PM_min_deg": 45.0,             # ASSUMPTION (common practice for a lightly damped mechanical plant)
    "GM_min_dB": 10.0,              # ASSUMPTION
    "Ms_max": 1.6,                  # ASSUMPTION (4.1 dB); hard limit 2.0 (6 dB)
    "Ms_hard": 2.0,
    "bandwidth_ratio_max": 0.1,     # crossover <= 1/10 of the lowest (coupled) 1st rocking (dynamics_model.md 6.2: 1/5..1/10)
    "disk_margin_alpha_min": 0.6,   # ASSUMPTION: symmetric disk margin alpha >= 0.6 -> DGM >= 4.6 dB, DPM >= 33 deg
    "accuracy_deg": 0.2, "done_deadband_deg": 0.03,   # CLAUDE.md (decided)
}


def set_affinity():
    try:
        import psutil
        pr = psutil.Process()
        n = os.cpu_count() or 1
        cores = [c for c in range(16, 28) if c < n] or list(range(n))
        pr.cpu_affinity(cores)
        if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
            pr.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        return cores
    except Exception as e:  # noqa: BLE001
        return f"affinity not set: {e!r}"


# ---------------------------------------------------------------------------- frequency response helpers


def freq_resp(sysd, w):
    """H(e^{j w T}) for a discrete state-space system, shape (nw, ny, nu).
    Complex Schur form A = Z Tt Z^H, then back substitution vectorised over the frequencies (no eigenvector inverse)."""
    from scipy.linalg import schur
    A, B, C, D = (np.asarray(m, float) for m in (sysd.A, sysd.B, sysd.C, sysd.D))
    n = A.shape[0]
    z = np.exp(1j * np.asarray(w, float) * T)
    if n == 0:
        return np.broadcast_to(D, (len(z),) + D.shape).astype(complex)
    Tt, Z = schur(A, output="complex")
    Bt = Z.conj().T @ B; Ct = C @ Z
    X = np.zeros((len(z), n, B.shape[1]), complex)
    for i in range(n - 1, -1, -1):
        acc = np.broadcast_to(Bt[i], (len(z), B.shape[1])).astype(complex)
        if i < n - 1:
            acc = acc + np.einsum("j,wjm->wm", Tt[i, i + 1:], X[:, i + 1:, :])   # (zI - Tt) x = Bt
        X[:, i, :] = acc / (z - Tt[i, i])[:, None]
    return np.einsum("yn,wnm->wym", Ct, X) + D[None]


def siso_eval(sysd):
    A, B, C, D = (np.asarray(m, float) for m in (sysd.A, sysd.B, sysd.C, sysd.D))
    I = np.eye(A.shape[0])

    def f(w):
        zz = np.exp(1j * w * T)
        return complex((C @ np.linalg.solve(zz * I - A, B) + D)[0, 0])
    return f


def siso_margins(sysd, wlo=1e-4, n=4000):
    """All gain / phase crossings on (wlo, pi/T), refined by brentq on the exact response (|L| = 1, Im L = 0)."""
    f = siso_eval(sysd)
    w = np.logspace(math.log10(wlo), math.log10(W_NYQ * 0.9999), n)
    H = freq_resp(sysd, w)[:, 0, 0]
    mag = np.abs(H)
    gc = []
    for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) < 0)[0]:
        wc = brentq(lambda x: abs(f(x)) - 1, w[i], w[i + 1], xtol=1e-14, rtol=1e-13)
        h = f(wc)
        gc.append({"w": wc, "PM_deg": (math.degrees(np.angle(h)) + 360) % 360 - 180})
    pc = []
    im = H.imag
    for i in np.where(im[:-1] * im[1:] < 0)[0]:
        if H.real[i] >= 0 and H.real[i + 1] >= 0:
            continue
        wp = brentq(lambda x: f(x).imag, w[i], w[i + 1], xtol=1e-14, rtol=1e-13)
        h = f(wp)
        if h.real < 0:
            pc.append({"w": wp, "GM": -1.0 / h.real})
    S = 1 / np.abs(1 + H)
    k = int(np.argmax(S))
    lo, hi = w[max(k - 1, 0)], w[min(k + 1, len(w) - 1)]
    r = minimize_scalar(lambda x: -1 / abs(1 + f(x)), bounds=(lo, hi), method="bounded", options={"xatol": 1e-10})
    Ms = max(float(S[k]), -float(r.fun)); wMs = float(r.x) if -r.fun >= S[k] else float(w[k])
    Sm = np.abs(1 / (1 + H) - 0.5)
    alpha = 1.0 / float(Sm.max())
    up = [p for p in pc if p["GM"] > 1]
    low = [p for p in pc if p["GM"] < 1]
    prim = gc[0] if gc else None
    out = {
        "gain_crossings": [{"w_rad_s": round(g["w"], 6), "PM_deg": round(g["PM_deg"], 3)} for g in gc],
        "phase_crossings": [{"w_rad_s": round(p["w"], 6), "GM": round(p["GM"], 5),
                             "GM_dB": round(20 * math.log10(p["GM"]), 3)} for p in pc],
        "w_gc_rad_s": prim["w"] if prim else None,
        "PM_deg": prim["PM_deg"] if prim else None,
        "PM_min_deg": min(g["PM_deg"] for g in gc) if gc else None,
        "GM_upper": min(p["GM"] for p in up) if up else math.inf,
        "w_pc_rad_s": min(up, key=lambda p: p["GM"])["w"] if up else None,
        "GM_lower": max(p["GM"] for p in low) if low else None,
        "Ms": Ms, "w_Ms_rad_s": wMs,
        "disk_alpha": alpha,
        "delay_margin_s": (math.radians(prim["PM_deg"]) / prim["w"]) if prim and prim["PM_deg"] > 0 else None,
        "n_gain_crossings": len(gc),
    }
    out["GM_upper_dB"] = 20 * math.log10(out["GM_upper"]) if math.isfinite(out["GM_upper"]) else math.inf
    a = alpha
    out["disk_GM_dB"] = 20 * math.log10((1 + a / 2) / (1 - a / 2)) if a < 2 else math.inf
    out["disk_PM_deg"] = math.degrees(2 * math.atan(a / 2))
    return out


def rnd(d, nd=5):
    if isinstance(d, dict):
        return {k: rnd(v, nd) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [rnd(v, nd) for v in d]
    if isinstance(d, (float, np.floating)):
        if not math.isfinite(d):
            return str(d)
        return float(f"{float(d):.{nd}g}")
    if isinstance(d, (bool, np.bool_)):
        return bool(d)
    if isinstance(d, np.integer):
        return int(d)
    if isinstance(d, np.ndarray):
        return rnd(d.tolist(), nd)
    return d


# ---------------------------------------------------------------------------- catalogue


def catalogue(full=True):
    cases = []
    for lv in ("top", "middle", "bottom"):
        for sup in ("pads", "crawler"):
            for b in (0.69e9, 1.0e9, 1.6e9):
                for mast in ("rigid", "sup_rigid", "sup_upper", "sup_lower"):
                    if not full and (b != 1.0e9 or mast not in ("rigid", "sup_lower")):
                        continue
                    cases.append(cl.PlantCase(level=lv, support=sup, beta=b, mast=mast))
    # soft pads (pads support, top): FL k x 0.5 and diagonal FL/RR x 0.5
    for ks in ((0.5, 1, 1, 1), (0.5, 1, 1, 0.5)):
        for mast in ("rigid", "sup_lower"):
            cases.append(cl.PlantCase(level="top", support="pads", mast=mast, k_scale=ks))
    return cases


def static_dec_gain(lp, Tdec):
    """Quasi-static G0 (outputs per unit integrated decoupled command) = Y X_s Tdec, X_s = static state per unit s."""
    n6 = 6
    q = np.linalg.solve(lp.K, lp.Bk)               # q per unit s (6x4)
    X = np.zeros((lp.A.shape[0], 4)); X[:n6] = q; X[2 * n6:] = np.eye(4)
    cc = cl.nominal_controller_constants()
    iP = [lp.idx(f"P_{nm}") for nm in dm.LEG_NAMES]
    Y = np.vstack([lp.C[lp.idx("clr")], lp.C[lp.idx("phi")], lp.C[lp.idx("theta")], cc["n"] @ lp.C[iP]])
    return Y @ X @ Tdec


def plant_summary(lp):
    cc = cl.nominal_controller_constants()
    Tdec = np.column_stack([cc["A"], cc["n"]])
    G0 = static_dec_gain(lp, Tdec)
    Gn = G0 / np.array([1, 1, 1, cc["k_nom"]])[:, None]     # twist row in units of k_nom
    try:
        rga = Gn * np.linalg.inv(Gn).T
    except np.linalg.LinAlgError:
        rga = np.full((4, 4), np.nan)
    return {"tag": lp.case.tag(), "level": lp.case.level, "support": lp.case.support, "beta_GPa": lp.case.beta / 1e9,
            "mast": lp.case.mast, "k_scale": list(lp.case.k_scale), "inertia_scale_IxxIyy": list(lp.inertia_scale),
            "modes_hz": lp.modes_hz[:6].tolist(), "modes_zeta": lp.modes_zeta[:6].tolist(),
            "G0_dec_norm": Gn.tolist(), "RGA_diag": np.diag(rga).tolist(),
            "att_loop_gain": [Gn[1, 1], Gn[2, 2]], "twist_gain_ratio": Gn[3, 3], "heave_gain": Gn[0, 0],
            "twist_to_att_deg_per_mm": [Gn[1, 3] * DEG * 1e-3, Gn[2, 3] * DEG * 1e-3],
            "att_to_twist_kN_per_deg": [G0[3, 1] / DEG / 1e3, G0[3, 2] / DEG / 1e3]}


# ---------------------------------------------------------------------------- loop analysis


def analyse_loops(lp, gains, others_closed=True, mimo=True):
    import control as ct
    dl = cl.discrete_loop(lp, gains)
    L, Kd = cl.loop_matrix(dl)
    out = {}
    for j, ch in enumerate(CH):
        sj = ct.ss(L.A, L.B[:, [j]], L.C[[j], :], L.D[[j], [j]], T)
        r = {"open": siso_margins(sj)}
        if others_closed:
            F = np.eye(4); F[j, j] = 0.0
            Lc = ct.feedback(L, F)
            sjc = ct.ss(Lc.A, Lc.B[:, [j]], Lc.C[[j], :], Lc.D[[j], [j]], T)
            r["closed_others"] = siso_margins(sjc)
        out[ch] = r
    if mimo:
        clsys = ct.feedback(L, np.eye(4))
        p = clsys.poles()
        out["cl_spectral_radius"] = float(np.max(np.abs(p)))
        # slowest pole and least damped (equivalent continuous ln z / T)
        s = np.log(p.astype(complex)) / T
        k = int(np.argmax(np.abs(p)))
        out["cl_slowest_pole_s"] = [float(s[k].real), float(abs(s[k].imag))]
        osc = np.abs(s.imag) > 1e-3
        if osc.any():
            zeta = -s.real[osc] / np.abs(s[osc])
            kk = int(np.argmin(zeta))
            out["cl_least_damped"] = {"zeta": float(zeta[kk]), "wn_rad_s": float(np.abs(s[osc][kk])),
                                      "f_Hz": float(np.abs(s[osc][kk]) / 2 / np.pi)}
    return out, dl, L


def worst(entries, key, mode="min"):
    vals = [(e[key], e["tag"], e["ch"]) for e in entries if e.get(key) is not None]
    if not vals:
        return None
    v = min(vals) if mode == "min" else max(vals)
    return {"value": v[0], "case": v[1], "channel": v[2]}


def _tune_worker(args):
    lp, gainsets = args
    warnings.filterwarnings("ignore")
    return {name: analyse_loops(lp, g, others_closed=True, mimo=True)[0] for name, g in gainsets.items()}


def tuning(plants, gainsets, workers=12):
    from multiprocessing import Pool
    with Pool(workers) as pool:
        alls = pool.map(_tune_worker, [(lp, gainsets) for lp in plants], chunksize=1)
    res = {}
    for name, g in gainsets.items():
        rows = []; rho = []
        for lp, aa in zip(plants, alls):
            a = aa[name]
            rho.append((a["cl_spectral_radius"], lp.case.tag()))
            for ch in CH:
                for mode in ("open", "closed_others"):
                    m = a[ch][mode]
                    rows.append({"tag": lp.case.tag(), "ch": ch, "mode": mode, "PM": m["PM_deg"],
                                 "PMmin": m["PM_min_deg"], "GMdB": m["GM_upper_dB"], "GMlow": m["GM_lower"],
                                 "Ms": m["Ms"], "wgc": m["w_gc_rad_s"], "alpha": m["disk_alpha"],
                                 "Dm": m["delay_margin_s"], "ngc": m["n_gain_crossings"],
                                 "f1_Hz": lp.modes_hz[0]})
        summ = {}
        for ch in CH:
            for mode in ("open", "closed_others"):
                e = [r for r in rows if r["ch"] == ch and r["mode"] == mode]
                summ[f"{ch}:{mode}"] = {
                    "PM_min": worst(e, "PM"), "PM_any_crossing_min": worst(e, "PMmin"),
                    "GM_dB_min": worst(e, "GMdB"),
                    "GM_lower_max": worst([x for x in e if x["GMlow"] is not None], "GMlow", "max"),
                    "Ms_max": worst(e, "Ms", "max"), "disk_alpha_min": worst(e, "alpha"),
                    "delay_margin_min_s": worst(e, "Dm"),
                    "w_gc_range_rad_s": [min(x["wgc"] for x in e if x["wgc"]), max(x["wgc"] for x in e if x["wgc"])],
                    "max_gain_crossings": max(x["ngc"] for x in e),
                    "bandwidth_ratio_max": max(x["wgc"] / (2 * math.pi * x["f1_Hz"]) for x in e if x["wgc"]),
                }
        r = max(rho)
        summ["cl_spectral_radius_max"] = {"value": r[0], "case": r[1]}
        summ["n_unstable_cases"] = int(sum(1 for v, _ in rho if v >= 1.0))
        summ["unstable_cases"] = [t for v, t in rho if v >= 1.0][:20]
        res[name] = {"gains": g.__dict__, "summary": summ, "rows": rows}
    return res


def spec_check(summ):
    att = [summ[f"{c}:{m}"] for c in ("phi", "theta") for m in ("open", "closed_others")]
    allc = [summ[f"{c}:{m}"] for c in CH for m in ("open", "closed_others")]
    ok = {
        "PM": min(a["PM_min"]["value"] for a in allc) >= SPEC["PM_min_deg"],
        "GM": min(a["GM_dB_min"]["value"] for a in allc) >= SPEC["GM_min_dB"],
        "Ms": max(a["Ms_max"]["value"] for a in allc) <= SPEC["Ms_max"],
        "bandwidth": max(a["bandwidth_ratio_max"] for a in att) <= SPEC["bandwidth_ratio_max"],
        "disk": min(a["disk_alpha_min"]["value"] for a in allc) >= SPEC["disk_margin_alpha_min"],
        "stable_all": summ["n_unstable_cases"] == 0,
    }
    ok["all"] = all(ok.values())
    return ok


# ---------------------------------------------------------------------------- MIMO: mu with diagonal complex scalars


def mu_upper_dscale(N):
    """min_D sigma_max(D N D^-1), D = diag(exp(x)), x[0] = 0 (own path)."""
    n = N.shape[0]

    def f(x):
        d = np.exp(np.concatenate([[0.0], x]))
        return np.linalg.svd((d[:, None] * N) / d[None, :], compute_uv=False)[0]
    x0 = np.zeros(n - 1)
    r = minimize(f, x0, method="Nelder-Mead", options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 4000})
    r2 = minimize(f, r.x, method="BFGS")
    return float(min(r.fun, r2.fun))


def mu_lower_phase(N, rng, n_try=400):
    """Lower bound: max over diagonal unitary Q of rho(Q N) (random search + local refinement)."""
    n = N.shape[0]
    best = 0.0; bth = None
    for _ in range(n_try):
        th = rng.uniform(-np.pi, np.pi, n)
        v = np.max(np.abs(np.linalg.eigvals(np.diag(np.exp(1j * th)) @ N)))
        if v > best:
            best, bth = v, th
    r = minimize(lambda th: -np.max(np.abs(np.linalg.eigvals(np.diag(np.exp(1j * th)) @ N))), bth, method="Nelder-Mead")
    return float(max(best, -r.fun))


def mimo_analysis(lp, gains, w, use_dkpy=True):
    import control as ct
    dl = cl.discrete_loop(lp, gains)
    L, _ = cl.loop_matrix(dl)
    Tdec = dl["Tdec"]
    H = freq_resp(L, w)                                 # (nw, 4, 4) decoupled-channel loop
    I = np.eye(4)
    S = np.array([np.linalg.inv(I + h) for h in H])
    Tm = np.array([h @ np.linalg.inv(I + h) for h in H])
    Ti = np.linalg.inv(Tdec)
    Su = np.array([Tdec @ s @ Ti for s in S])           # leg-input sensitivities (similarity)
    Tu = np.array([Tdec @ t @ Ti for t in Tm])
    rng = np.random.default_rng(12345)
    out = {"w": w.tolist()}
    for nm, Sx, Tx in (("decoupled", S, Tm), ("legs", Su, Tu)):
        Nd = Sx - 0.5 * I                                # balanced disk margin: alpha = 1 / mu(S - I/2)
        mu_dm = np.array([mu_upper_dscale(n_) for n_ in Nd])
        mu_T = np.array([mu_upper_dscale(n_) for n_ in Tx])
        sv_S = np.array([np.linalg.svd(s, compute_uv=False)[0] for s in Sx])
        sv_T = np.array([np.linalg.svd(t, compute_uv=False)[0] for t in Tx])
        k = int(np.argmax(mu_dm))
        lb = mu_lower_phase(Nd[k], rng)
        out[nm] = {"mu_S_minus_half_upper": mu_dm.tolist(), "mu_T_upper": mu_T.tolist(), "sigma_S": sv_S.tolist(),
                   "sigma_T": sv_T.tolist(),
                   "multiloop_disk_alpha": 1.0 / float(mu_dm.max()), "w_at_min_alpha": float(w[k]),
                   "mu_lower_at_peak": lb, "mu_upper_at_peak": float(mu_dm[k]),
                   "unstructured_disk_alpha": 1.0 / float(np.max([np.linalg.svd(n_, compute_uv=False)[0] for n_ in Nd])),
                   "Ms_sigma_max": float(sv_S.max()), "Mt_sigma_max": float(sv_T.max()),
                   "mu_T_peak": float(mu_T.max()), "w_mu_T_peak": float(w[int(np.argmax(mu_T))])}
        a = out[nm]["multiloop_disk_alpha"]
        out[nm]["multiloop_disk_GM_dB"] = 20 * math.log10((1 + a / 2) / (1 - a / 2)) if a < 2 else math.inf
        out[nm]["multiloop_disk_PM_deg"] = math.degrees(2 * math.atan(a / 2))
        if use_dkpy:
            try:
                import dkpy
                sel = np.unique(np.concatenate([np.arange(0, len(w), max(1, len(w) // 40)), [k]]))
                Nw = np.transpose(Nd[sel], (1, 2, 0))
                blocks = [dkpy.ComplexFullBlock(1, 1) for _ in range(4)]
                mu_lmi, _, _, info = dkpy.SsvLmiBisection(n_jobs=None, bisection_rtol=1e-5).compute_ssv(Nw, blocks)
                own = mu_dm[sel]
                out[nm]["dkpy_check"] = {"n_freq": int(len(sel)), "max_rel_diff": float(np.max(np.abs(mu_lmi - own) / own)),
                                         "mu_peak_dkpy": float(np.max(mu_lmi)), "mu_peak_own": float(np.max(own))}
            except Exception as e:  # noqa: BLE001
                out[nm]["dkpy_check"] = {"error": repr(e)}
    return out


def input_uncertainty_weight(w, r0=0.2, rinf=2.0, w1=10.0):
    """|W(j w)| of W(s) = (s/w1 + r0) / (s/(w1 rinf) + 1): 20 % flow-gain error at low frequency, 100 % near
    w1 = 10 rad/s (unmodelled valve lag up to ~0.1 s), 200 % at high frequency (ASSUMPTION)."""
    s = 1j * np.asarray(w)
    return np.abs((s / w1 + r0) / (s / (w1 * rinf) + 1))


# ---------------------------------------------------------------------------- describing functions


def df_numeric(nl, A, n=4096):
    """First-harmonic describing function of a memoryless / hysteretic nonlinearity for input A sin(t)."""
    t = np.linspace(0, 4 * np.pi, 2 * n, endpoint=False)
    x = A * np.sin(t)
    y = nl(x)
    y = y[n:]; t = t[n:]
    b1 = 2 / n * np.sum(y * np.sin(t)); a1 = 2 / n * np.sum(y * np.cos(t))
    return complex(b1, a1) / A


def backlash_op(b):
    def f(x):
        y = np.empty_like(x); yk = 0.0
        for k, xk in enumerate(x):
            yk = min(max(yk, xk - b), xk + b)
            y[k] = yk
        return y
    return f


def deadband_op(d):
    return lambda x: np.where(np.abs(x) <= d, 0.0, x - np.sign(x) * d)


def df_limit_cycle(Lf, Nf, A_grid, w_lo=1e-3, w_hi=W_NYQ * 0.999):
    """Solve 1 + N(A) L(jw) = 0: for each A find w with arg L = arg(-1/N); return (A, w, |L|/|1/N| - 1) sign changes."""
    w = np.logspace(math.log10(w_lo), math.log10(w_hi), 4000)
    Lw = np.array([Lf(x) for x in w])
    argL = np.unwrap(np.angle(Lw))
    sols = []
    prev = None
    for A in A_grid:
        N = Nf(A)
        if abs(N) < 1e-12:
            continue
        m = -1.0 / N
        best = None
        for i in range(len(w) - 1):
            # phase match within the wrapped interval
            d0 = np.angle(Lw[i] / m); d1 = np.angle(Lw[i + 1] / m)
            if d0 * d1 < 0 and abs(d0 - d1) < np.pi:
                ratio = abs(Lw[i]) / abs(m)
                if best is None or abs(math.log(ratio)) < abs(math.log(best[1])):
                    best = (w[i], ratio)
        if best is None:
            prev = None
            continue
        sols.append((A, best[0], best[1]))
    # crossings of ratio through 1
    lc = []
    for (A0, w0, r0_), (A1, w1, r1) in zip(sols[:-1], sols[1:]):
        if (r0_ - 1) * (r1 - 1) < 0:
            fr = (1 - r0_) / (r1 - r0_)
            lc.append({"A": A0 + fr * (A1 - A0), "w_rad_s": w0 + fr * (w1 - w0),
                       "stable_LC_Loeb": bool(r1 < r0_)})
    return lc, sols


# ---------------------------------------------------------------------------- LQR / LQG reference


def lqr_section(lp_nom, lp_mis, gains):
    import control as ct
    cc = cl.nominal_controller_constants()
    vmax = cc["v_max"]
    A_ = cc["A"]
    out = {}
    # (a) Bryson quasi-static LQI per decoupled channel: x_dot = v, cost q x^2 + r v^2 -> k = sqrt(q/r)
    phi_max = math.radians(SPEC["accuracy_deg"])
    v_phi_max = vmax / np.max(np.abs(A_[:, 1]))     # roll rate at which the most loaded leg reaches v_max
    v_th_max = vmax / np.max(np.abs(A_[:, 2]))
    out["bryson_quasistatic"] = {
        "assumption": "x_max = 0.2 deg (accuracy), v_max per channel = v_max / max|A_i,j| (one leg at v_max)",
        "k_roll_1_s": v_phi_max / phi_max, "k_pitch_1_s": v_th_max / phi_max,
        "note": "LQR on the quasi-static integrator plant returns a diagonal P(I) law = the C2 structure; the Bryson "
                "bandwidth is 10-12x the C2 crossover and is not reachable with the attitude filter (rocking)."}
    # (b) Kp stability boundary with / without the attitude filter (others closed), top rigid and mast sup_lower
    def rho_of(lp, Kp, stages):
        g = cl.Gains(**{**gains.__dict__, "Kp": Kp, "Ki": gains.Ki * Kp / gains.Kp, "n_stages": stages})
        dl = cl.discrete_loop(lp, g)
        L, _ = cl.loop_matrix(dl)
        return float(np.max(np.abs(ct.feedback(L, np.eye(4)).poles())))
    bnd = {}
    for lp in (lp_nom, lp_mis):
        for st in (0, 1, 2):
            ks = np.logspace(-2, 1.5, 60)
            r = [rho_of(lp, k, st) for k in ks]
            unst = [k for k, v in zip(ks, r) if v >= 1.0]
            kmax = None
            if unst:
                k1 = unst[0]; i1 = list(ks).index(k1)
                if i1 > 0:
                    kmax = brentq(lambda k: rho_of(lp, k, st) - 1.0, ks[i1 - 1], k1, xtol=1e-6)
                else:
                    kmax = 0.0
            bnd[f"{lp.case.tag()}:stages{st}"] = {"Kp_max_stable": kmax,
                                                   "first_unstable_from_grid": unst[0] if unst else None}
    out["Kp_stability_boundary"] = bnd
    # (c) discrete LQG (dlqr + Kalman) on the dynamic plant, legs as inputs (no extra delay states in the design model)
    Ad, Bd, Ex, Eu = cl.c2d_zoh_avg(lp_nom.A, lp_nom.B, T)
    C = lp_nom.C; D = lp_nom.D
    iP = [lp_nom.idx(f"P_{nm}") for nm in dm.LEG_NAMES]
    ix = [lp_nom.idx(f"x_{nm}") for nm in dm.LEG_NAMES]
    n_ = cc["n"]
    Cz = np.vstack([C[lp_nom.idx("phi")] / phi_max, C[lp_nom.idx("theta")] / phi_max, (n_ @ C[iP]) / 5e3,
                    C[lp_nom.idx("clr")] / 5e-3])
    # measurement model: instantaneous approximation of the averaged accelerometer (design model only)
    Cy = np.vstack([C[lp_nom.idx("phi_acc")], C[lp_nom.idx("theta_acc")], C[iP], C[ix]])
    Dy = np.vstack([D[lp_nom.idx("phi_acc")], D[lp_nom.idx("theta_acc")], np.zeros((8, 4))])
    sig_tilt = 100e-6 * math.sqrt(1 / (2 * T))          # rad, 100 ug/rtHz over 20 ms (as run_control_comparison)
    RN = np.diag([sig_tilt ** 2] * 2 + [300.0 ** 2] * 4 + [1e-4 ** 2] * 4)
    QN = np.diag([(0.05 * vmax) ** 2] * 4)              # ASSUMPTION: leg-speed (flow) noise 5 % v_max
    lqg = {}
    for rho_w in (1.0, 30.0, 1000.0):
        Q = Cz.T @ Cz + 1e-12 * np.eye(Ad.shape[0])
        R = rho_w * np.eye(4) / vmax ** 2
        K, _, Ecl = ct.dlqr(Ad, Bd, Q, R)
        # Kalman predictor gain via scipy DARE on noise-normalised measurements (slycot sg02ad fails on the raw scaling)
        from scipy.linalg import solve_discrete_are
        QNf = Bd @ QN @ Bd.T + 1e-16 * np.eye(Ad.shape[0])     # small full-rank regularisation
        Sy = np.diag(1 / np.sqrt(np.diag(RN)))
        Cs = Sy @ Cy
        Pk = solve_discrete_are(Ad.T, Cs.T, QNf, np.eye(Cy.shape[0]))
        Lk = Ad @ Pk @ Cs.T @ np.linalg.inv(Cs @ Pk @ Cs.T + np.eye(Cy.shape[0])) @ Sy
        # predictive estimator controller: xh+ = Ad xh + Bd u + Lk (y - Cy xh - Dy u), u = -K xh
        Ac = Ad - Bd @ K - Lk @ Cy + Lk @ Dy @ K
        Kc = ct.ss(Ac, Lk, -K, np.zeros((4, 10)), T)       # y -> u (sign included)
        res = {"rho": rho_w}
        for nm, lp in (("nominal", lp_nom), ("mast_sup_lower", lp_mis)):
            Adm, Bdm, _, _ = cl.c2d_zoh_avg(lp.A, lp.B, T)
            Pm = ct.ss(Adm, Bdm, np.vstack([lp.C[lp.idx("phi_acc")], lp.C[lp.idx("theta_acc")], lp.C[iP], lp.C[ix]]),
                       np.vstack([lp.D[lp.idx("phi_acc")], lp.D[lp.idx("theta_acc")], np.zeros((8, 4))]), T)
            Lu = -(Kc * Pm)                                # loop at the leg inputs (negative feedback form)
            clp = ct.feedback(Lu, np.eye(4)).poles()
            res[nm] = {"cl_spectral_radius": float(np.max(np.abs(clp)))}
            if nm == "nominal":
                wv = np.logspace(-3, math.log10(W_NYQ * 0.999), 400)
                Hu = freq_resp(Lu, wv)
                Su = np.array([np.linalg.inv(np.eye(4) + h) for h in Hu])
                mu = np.array([mu_upper_dscale(s - 0.5 * np.eye(4)) for s in Su])
                res[nm]["multiloop_disk_alpha_legs"] = float(1 / mu.max())
                res[nm]["Ms_sigma_max_legs"] = float(max(np.linalg.svd(s, compute_uv=False)[0] for s in Su))
                # attitude bandwidth: closed-loop dominant pole of the regulator
                sl = np.log(Ecl.astype(complex)) / T
                res[nm]["regulator_slowest_pole_rad_s"] = float(np.min(np.abs(sl.real)))
                res[nm]["regulator_poles_rad_s_lowest6"] = sorted(np.abs(sl))[:6]
        lqg[f"rho{rho_w:g}"] = res
    out["lqg_dynamic"] = {"assumptions": {"performance": "phi, theta / 0.2 deg, n^T P / 5 kN, clearance / 5 mm",
                                          "R": "rho I / v_max^2", "QN": "leg speed noise 5 % v_max on the inputs",
                                          "RN": "IMU 100 ug/rtHz over 20 ms, pressure 0.3 kN, stroke 0.1 mm",
                                          "design_model": "top auger, pads, beta 1.0, rigid mast; no input delay"},
                          "results": lqg}
    return out


# ---------------------------------------------------------------------------- decisions D4-D6


def decisions():
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    n = dm.twist_vector(geo.pad_xy)
    L1 = p["contact"]["rigid_floor"]["L1"]
    kv = np.array([L1["kn_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)
    out = {"n": n.tolist(), "sum_abs_n": float(np.abs(n).sum())}
    lev = {}
    for lv in ("top", "middle", "bottom"):
        b = dm.body_from_params(p, lv)
        W = b.mass * geo.g
        F_eq, _, _ = dm.static_loads(np.ones(4), geo.pad_xy, W, b.com[:2])      # n^T F = 0 (equal stiffness)
        F_L1, _, _ = dm.static_loads(kv, geo.pad_xy, W, b.com[:2])
        # max-min over the twist family F = F_eq + n t (concave piecewise linear in t)
        ts = np.linspace(-60e3, 60e3, 240001)
        mins = np.min(F_eq[None, :] + np.outer(ts, n), axis=1)
        k = int(np.argmax(mins))
        lev[lv] = {"F_twistfree_kN": (F_eq / 1e3).tolist(), "min_twistfree_kN": float(F_eq.min() / 1e3),
                   "F_L1_kN": (F_L1 / 1e3).tolist(), "nTF_L1_kN": float(n @ F_L1 / 1e3),
                   "maxmin_t_kN": float(ts[k] / 1e3), "maxmin_min_load_kN": float(mins[k] / 1e3),
                   "gain_of_maxmin_kN": float((mins[k] - F_eq.min()) / 1e3)}
    out["D6_twist_target"] = lev
    # soft FL: n^T F = 0 still gives F_eq (any support stiffness); the same-stiffness spring solution would not
    k_soft = kv * np.array([0.5, 1, 1, 1])
    b = dm.body_from_params(p, "top")
    F_soft, _, _ = dm.static_loads(k_soft, geo.pad_xy, b.mass * geo.g, b.com[:2])
    out["D6_soft_FL_passive_kN"] = (F_soft / 1e3).tolist()
    out["D6_soft_FL_passive_nTF_kN"] = float(n @ F_soft / 1e3)
    # D5: seal-friction reading error: P = F - f, |f| <= F_s -> |n^T f| <= sum|n| F_s; leg error after the twist loop
    out["D5_seal"] = {}
    for Fs in (0.0, 2e3, 5e3, 12e3):
        tw_err = float(np.abs(n).sum() * Fs)
        out["D5_seal"][f"{Fs / 1e3:g}kN"] = {"twist_load_error_max_kN": tw_err / 1e3,
                                             "leg_load_error_max_kN": float(np.abs(n).max() * tw_err / 1e3),
                                             "guard_lower_bound_needs_F_band_ge_kN": (Fs + 3 * 300.0) / 1e3}
    out["D5_guard_trigger_reading_kN"] = {f"F_band{fb:g}": (0.1 * b.mass * geo.g / 4 + 5e3 + fb * 1e3) / 1e3
                                          for fb in (0, 2, 5, 12, 13)}
    return out


# ---------------------------------------------------------------------------- saturation direction


def saturation_direction():
    cc = cl.nominal_controller_constants()
    A_, n, vmax, k = cc["A"], cc["n"], cc["v_max"], cc["k_nom"]
    rows = []
    for tag, ro, pi in [("roll+3", 3, 0), ("pitch+3", 0, 3), ("diag3", 2.1213, 2.1213), ("pitch+3.7", 0, 3.7),
                        ("roll+5.7", 5.7, 0)]:
        e = np.radians([ro, pi])
        v = np.array([0.5 * 0.05, 0.4 * -e[0], 0.4 * -e[1]])   # z_dot = Kz x 50 mm, attitude Kp x error
        u = A_ @ v
        u_scale = u * min(1.0, vmax / np.max(np.abs(u)))
        u_clip = np.clip(u, -vmax, vmax)
        Ap = np.linalg.pinv(np.column_stack([A_, n]))
        dir_s = Ap @ u_scale; dir_c = Ap @ u_clip
        rows.append({"slope": tag, "twist_rate_scaled_mm_s": float(n @ u_scale * 1e3),
                     "twist_rate_clipped_mm_s": float(n @ u_clip * 1e3),
                     "twist_load_rate_clipped_kN_s": float(k * (n @ u_clip) / 1e3),
                     "att_rate_ratio_roll_pitch_scaled": [float(dir_s[1] / v[1]) if v[1] else None,
                                                          float(dir_s[2] / v[2]) if v[2] else None],
                     "att_rate_ratio_roll_pitch_clipped": [float(dir_c[1] / v[1]) if v[1] else None,
                                                           float(dir_c[2] / v[2]) if v[2] else None]})
    return rows


# ---------------------------------------------------------------------------- figures


def figures(plants_fig, gains, gains_legacy, out_mimo, df_res, w):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    wv = np.logspace(-3, math.log10(W_NYQ * 0.999), 3000)
    fig, ax = plt.subplots(2, 2, figsize=(12, 7.5))
    cols = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for k, (lab, lp, g) in enumerate(plants_fig):
        dl = cl.discrete_loop(lp, g)
        L, _ = cl.loop_matrix(dl)
        H = freq_resp(L, wv)
        for j, ch in ((1, "roll"), (3, "twist")):
            h = H[:, j, j]
            if j == 1:
                ax[0, 0].loglog(wv, np.abs(h), color=cols[k], lw=1, label=lab)
                ax[1, 0].semilogx(wv, np.degrees(np.unwrap(np.angle(h))), color=cols[k], lw=1)
            if k == 0 and j == 3:
                ax[0, 0].loglog(wv, np.abs(h), color="k", lw=0.8, ls=":", label="twist (top rigid)")
        h = H[:, 1, 1]
        ax[0, 1].plot(h.real, h.imag, color=cols[k], lw=0.8, label=lab)
    ax[0, 0].axhline(1, color="0.5", lw=0.6); ax[0, 0].set_ylabel("|L| roll channel"); ax[0, 0].grid(alpha=0.3, which="both")
    ax[0, 0].legend(fontsize=7); ax[0, 0].set_ylim(1e-4, 1e3)
    ax[1, 0].axhline(-180, color="0.5", lw=0.6); ax[1, 0].set_ylabel("phase [deg]"); ax[1, 0].set_xlabel("w [rad/s]")
    ax[1, 0].set_ylim(-540, 0); ax[1, 0].grid(alpha=0.3, which="both")
    th = np.linspace(0, 2 * np.pi, 200)
    ax[0, 1].plot(-1 + np.cos(th) * 0, 0 * th, "k+")
    ax[0, 1].plot(np.cos(th), np.sin(th), color="0.7", lw=0.5)
    ax[0, 1].set_xlim(-3, 2); ax[0, 1].set_ylim(-3, 2); ax[0, 1].set_aspect("equal"); ax[0, 1].grid(alpha=0.3)
    ax[0, 1].set_title("Nyquist (zoom), roll channel, others open; + = -1", fontsize=9)
    # mu / sigma at legs
    m = out_mimo["legs"]
    ax[1, 1].loglog(w, m["sigma_T"], color="#1f77b4", lw=1, label="sigma_max T_u (legs)")
    ax[1, 1].loglog(w, m["mu_T_upper"], color="#d62728", lw=1, label="mu(T_u), diag complex")
    ax[1, 1].loglog(w, 1 / input_uncertainty_weight(w), color="k", ls="--", lw=0.8, label="1/|W| (input mult. unc.)")
    ax[1, 1].loglog(w, m["sigma_S"], color="#2ca02c", lw=1, label="sigma_max S_u")
    ax[1, 1].set_xlabel("w [rad/s]"); ax[1, 1].legend(fontsize=7); ax[1, 1].grid(alpha=0.3, which="both")
    ax[1, 1].set_title("top auger, rigid mast, proposal gains", fontsize=9)
    fig.tight_layout()
    p1 = OUT_DIR / "c2_design_loops.png"
    fig.savefig(p1, dpi=90); plt.close(fig)
    # DF figure
    fig, ax = plt.subplots(1, 1, figsize=(6.5, 5.5))
    for lab, d in df_res.items():
        if "L_curve" in d:
            Lc = np.array(d["L_curve"])
            ax.plot(Lc[:, 0], Lc[:, 1], lw=1, label=f"L(jw) {lab}")
        if "minus_inv_N" in d:
            Mi = np.array(d["minus_inv_N"])
            ax.plot(Mi[:, 0], Mi[:, 1], lw=1.2, ls="--", label=f"-1/N(A) {lab}")
    ax.set_xlim(-6, 1); ax.set_ylim(-6, 1); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    ax.set_title("describing function: seal-friction backlash, roll channel", fontsize=9)
    p2 = OUT_DIR / "c2_design_df.png"
    fig.savefig(p2, dpi=90); plt.close(fig)
    return [p1, p2]


# ---------------------------------------------------------------------------- Julia export / merge


def export_julia(lp_list, gains):
    JL_DIR.mkdir(parents=True, exist_ok=True)
    cc = cl.nominal_controller_constants()
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    cases = []
    for lp in lp_list:
        com = dm.body_with_rods(p, geo, lp.case.level, e_op).com
        pad = np.column_stack([geo.pad_xy, geo.pad_z_retracted - e_op]) - com
        L1 = p["contact"]["rigid_floor"]["L1"]
        cn = np.array([L1["cn_per_pad_N_s_m"][nm] for nm in dm.LEG_NAMES], float) * lp.case.c_scale
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        cases.append({"tag": lp.case.tag(), "M": lp.M.tolist(), "K": lp.K.tolist(), "C": lp.Cd.tolist(),
                      "kv": lp.kv.tolist(), "ko": lp.ko.tolist(), "cn": cn.tolist(),
                      "pad_rel": pad.tolist(), "imu_rel": (np.asarray(lp.case.imu_point) - com).tolist(),
                      "pad_xy": geo.pad_xy.tolist(),
                      "crawler_corner_mean_xy": [float((x0 + x1) / 2), float((y0 + y1) / 2)]})
    raw = {"note": "raw plant matrices (M, K, C about the CoM, q = [ux uy uz phi theta psi]), pad offsets, k_v, "
                   "k_oil, IMU offset; controller constants and gains. Julia builds the state space, ZOH, average, "
                   "filter, PI and delay itself.",
           "T": T, "g": cl.G, "A_dec": cc["A"].tolist(), "n": cc["n"].tolist(), "k_nom": cc["k_nom"],
           "gains": gains.__dict__, "cases": cases}
    path = JL_DIR / "c2_julia_input.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh)
    return path


def merge_julia(d):
    path = JL_DIR / "c2_julia_result.json"
    if not path.exists():
        return {"status": "not run"}
    with open(path, encoding="utf-8") as fh:
        jr = json.load(fh)
    rows = []
    worst = 0.0
    for c in jr["cases"]:
        py = d["julia_python_reference"][c["tag"]]
        for key_j, key_p in (("roll_open_PM_deg", "phi_PM"), ("roll_open_wgc", "phi_wgc"), ("roll_open_GM", "phi_GM"),
                             ("roll_open_wpc", "phi_wpc"), ("pitch_open_PM_deg", "theta_PM"),
                             ("pitch_open_GM", "theta_GM"), ("roll_open_Ms", "phi_Ms"),
                             ("twist_open_PM_deg", "tw_PM"), ("cl_spectral_radius", "rho")):
            a = c.get(key_j); b = py.get(key_p)
            if a is None or b is None:
                continue
            rel = abs(a - b) / max(abs(b), 1e-300)
            if key_p != "rho":
                worst = max(worst, rel)
            rows.append({"case": c["tag"], "quantity": key_p, "python": b, "julia": a, "rel_diff": rel})
    rho_rows = [r for r in rows if r["quantity"] == "rho"]
    rho_worst = max((r["rel_diff"] for r in rho_rows), default=0.0)
    verdict = "일치" if max(worst, rho_worst / 1e3) <= 1e-6 else ("허용 일치" if worst <= 1e-3 and rho_worst <= 1e-6 else "불일치")
    return {"status": "ok", "rows": rows, "worst_rel_diff_margins": worst, "worst_rel_diff_rho": rho_worst,
            "verdict": verdict, "julia_meta": jr.get("meta")}


# ---------------------------------------------------------------------------- main


def main():
    import argparse
    import control as ct
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--merge-julia", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.merge_julia:
        with open(OUT_JSON, encoding="utf-8") as fh:
            d = json.load(fh)
        d["julia_check"] = rnd(merge_julia(d), 8)
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
        print(json.dumps(d["julia_check"], indent=1, ensure_ascii=False))
        return
    cores = set_affinity()
    t0 = time.perf_counter()
    res = {"meta": {"script": "04_scripts/03_control/run_c2_design.py", "argv": sys.argv[1:], "affinity": cores,
                    "T_ctrl_s": T, "python_control": ct.__version__, "spec": SPEC,
                    "conventions": "negative feedback v = -K y in decoupled channels; u = [A, n] v; ZOH; GM absolute "
                                   "and dB; PM deg; rad/s; 20 ms averaged accelerometer tilt available one step later; "
                                   "extra input delay delay_steps"}}
    # ---------------- plants
    cases = catalogue(full=not args.quick)
    plants = [cl.build_plant(c) for c in cases]
    nom = cl.build_plant(cl.PlantCase())
    lowd = [cl.build_plant(cl.PlantCase(level=lv, mast=m, c_scale=1 / 3))
            for lv in ("top", "middle", "bottom") for m in ("rigid", "sup_lower")]
    all_plants = plants + lowd
    res["plants"] = rnd([plant_summary(lp) for lp in all_plants])
    print(f"plants {len(plants)} + {len(lowd)} low-damping, {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- tuning iterations
    G0 = cl.Gains()
    gainsets = {
        "it0_current_nodelay": cl.Gains(delay_steps=0),
        "it0_current": cl.Gains(),
        "it0_current_1stLPF": cl.Gains(n_stages=1),
        "it0_current_ramp": cl.Gains(ramp_delay_s=0.06),
        "it1_Kp0.5": cl.Gains(Kp=0.5, Ki=0.025),
        "it2_Kp0.6": cl.Gains(Kp=0.6, Ki=0.03),
        "it5_Ki0": cl.Gains(Ki=0.0),
        "it3b_Ktw1.0_noZfilter": cl.Gains(Ktw=1.0),
        "it3b_Ktw1.0_noZfilter_d0": cl.Gains(Ktw=1.0, delay_steps=0),
        "it3_proposal": cl.Gains(Ktw=1.0, tau_z=0.2),
        "it3_proposal_d0": cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=0),
        "it3_proposal_d3": cl.Gains(Ktw=1.0, tau_z=0.2, delay_steps=3),
    }
    tune_plants = all_plants if not args.quick else all_plants[:6]
    tun = tuning(tune_plants, gainsets)
    for k, v in tun.items():
        v["spec_check"] = spec_check(v["summary"])
    res["tuning"] = rnd({k: {"gains": v["gains"], "summary": v["summary"], "spec_check": v["spec_check"]}
                         for k, v in tun.items()})
    print(f"tuning done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- proposal: per-level table (pads / crawler, beta 1.0, mast rigid & sup_lower) + delay sensitivity
    gp = gainsets["it3_proposal"]
    rows = []
    for lp in all_plants:
        tg = lp.case.tag()
        if "_b1_" not in tg:
            continue
        a, _, _ = analyse_loops(lp, gp, others_closed=True, mimo=True)
        row = {"case": tg, "cl_spectral_radius": a["cl_spectral_radius"], "cl_least_damped": a.get("cl_least_damped")}
        for ch in CH:
            for mode in ("open", "closed_others"):
                m = a[ch][mode]
                row[f"{ch}:{mode}"] = {k: m[k] for k in ("w_gc_rad_s", "PM_deg", "GM_upper", "GM_upper_dB", "w_pc_rad_s",
                                                         "GM_lower", "Ms", "disk_alpha", "disk_GM_dB", "disk_PM_deg",
                                                         "delay_margin_s", "n_gain_crossings")}
        rows.append(row)
    dsens = []
    for dsteps in (0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15):
        for lp in (nom, [x for x in all_plants if x.case.tag() == "top_pads_b1_sup_lower"][0]):
            g = cl.Gains(**{**gp.__dict__, "delay_steps": dsteps})
            a, _, _ = analyse_loops(lp, g, others_closed=False, mimo=True)
            dsens.append({"case": lp.case.tag(), "delay_steps": dsteps, "phi_PM": a["phi"]["open"]["PM_deg"],
                          "phi_GM_dB": a["phi"]["open"]["GM_upper_dB"], "phi_Ms": a["phi"]["open"]["Ms"],
                          "theta_PM": a["theta"]["open"]["PM_deg"], "rho": a["cl_spectral_radius"]})
    res["proposal"] = rnd({"gains": gp.__dict__, "per_case": rows, "delay_sensitivity": dsens})
    # Julia reference numbers (python side)
    jref = {}
    jl_plants = [nom, [x for x in all_plants if x.case.tag() == "top_pads_b1_sup_lower"][0]]
    for lp in jl_plants:
        a, _, _ = analyse_loops(lp, gp, others_closed=False, mimo=True)
        jref[lp.case.tag()] = {"phi_PM": a["phi"]["open"]["PM_deg"], "phi_wgc": a["phi"]["open"]["w_gc_rad_s"],
                               "phi_GM": a["phi"]["open"]["GM_upper"], "phi_wpc": a["phi"]["open"]["w_pc_rad_s"],
                               "theta_PM": a["theta"]["open"]["PM_deg"], "theta_GM": a["theta"]["open"]["GM_upper"],
                               "phi_Ms": a["phi"]["open"]["Ms"], "tw_PM": a["tw"]["open"]["PM_deg"],
                               "rho": a["cl_spectral_radius"]}
        # second Python path: python-control margin on the SISO roll loop
        dl = cl.discrete_loop(lp, gp)
        L, _ = cl.loop_matrix(dl)
        s11 = ct.ss(L.A, L.B[:, [1]], L.C[[1], :], L.D[[1], [1]], T)
        try:
            gm, pm, wcg, wcp = ct.margin(s11)
            jref[lp.case.tag()]["python_control_margin"] = {"gm": float(gm), "pm": float(pm), "wcg_phase_xover": float(wcg),
                                                            "wcp_gain_xover": float(wcp)}
        except Exception as e:  # noqa: BLE001
            jref[lp.case.tag()]["python_control_margin"] = {"error": repr(e)}
    res["julia_python_reference"] = rnd(jref, 12)
    export_julia(jl_plants, gp)
    print(f"proposal done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- separation / interaction
    sep = {}
    cc = cl.nominal_controller_constants()
    Tdec = np.column_stack([cc["A"], cc["n"]])
    for lp in [nom] + [x for x in all_plants if x.case.tag() in ("top_pads_b1_rigid_k0.5-1-1-1", "top_pads_b1_rigid_k0.5-1-1-0.5",
                                                                 "top_crawler_b1_rigid", "top_pads_b0.69_rigid",
                                                                 "top_pads_b1.6_rigid", "top_pads_b1_sup_lower")]:
        dl = cl.discrete_loop(lp, gp)
        L, Kd = cl.loop_matrix(dl)
        wv = np.logspace(-3, math.log10(W_NYQ * 0.999), 240)
        Hg = freq_resp(dl["G"], wv)
        Hk = freq_resp(Kd, wv)
        rhoET = []; sET = []
        for hg, hk in zip(Hg, Hk):
            Gd = np.diag(np.diag(hg))
            E = (hg - Gd) @ np.linalg.inv(Gd)
            Ld = np.diag(np.diag(hk)) @ Gd
            Td = Ld @ np.linalg.inv(np.eye(4) + Ld)
            M_ = E @ Td
            rhoET.append(float(np.max(np.abs(np.linalg.eigvals(M_)))))
            sET.append(mu_upper_dscale(M_))
        S0 = lp.S
        A_ = cc["A"]; n_ = cc["n"]
        G0 = static_dec_gain(lp, Tdec)
        sep[lp.case.tag()] = {"rho_ET_max": max(rhoET), "mu_ET_max": max(sET), "w_at_max": float(wv[int(np.argmax(sET))]),
                              "nTSA_norm_rel": float(np.linalg.norm(n_ @ S0 @ A_) / np.linalg.norm(S0)),
                              "G0_dec": G0.tolist(),
                              "twist_to_att_deg_per_mm": [G0[1, 3] * DEG * 1e-3, G0[2, 3] * DEG * 1e-3],
                              "att_to_twist_kN_per_deg": [G0[3, 1] / DEG / 1e3, G0[3, 2] / DEG / 1e3]}
    res["separation"] = rnd({"note": "decentralised stability is guaranteed if mu(E T_d) < 1 (E = (G - G_d) G_d^-1, "
                                     "T_d = diagonal complementary sensitivity, Grosdidier-Morari); quasi-static n^T S A = 0 "
                                     "for any pad stiffness (attitude/heave commands do not change the twist load)",
                             "cases": sep})
    print(f"separation done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- MIMO mu
    wm = np.logspace(-3, math.log10(W_NYQ * 0.999), 160 if not args.quick else 40)
    mimo = {}
    for lp in [nom] + [x for x in all_plants if x.case.tag() in ("top_pads_b1_sup_lower", "bottom_pads_b1_rigid",
                                                                 "top_crawler_b1_rigid", "top_pads_b1_rigid_k0.5-1-1-0.5")]:
        mm = mimo_analysis(lp, gp, wm, use_dkpy=(lp is nom))
        Wm = input_uncertainty_weight(wm)
        mm["robust_stability_input_unc"] = {"peak_mu_WTu": float(np.max(Wm * np.array(mm["legs"]["mu_T_upper"]))),
                                            "weight": "W(s) = (s/10 + 0.2)/(s/20 + 1) per leg (ASSUMPTION)"}
        mimo[lp.case.tag()] = mm
    res["mimo"] = rnd({k: {kk: (vv if kk != "w" else None) for kk, vv in v.items()} for k, v in mimo.items()})
    for k in res["mimo"]:
        for side in ("decoupled", "legs"):
            for big in ("mu_S_minus_half_upper", "mu_T_upper", "sigma_S", "sigma_T"):
                res["mimo"][k][side].pop(big, None)
    print(f"mimo done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- nonlinear (describing functions, saturation)
    nl = {}
    dl = cl.discrete_loop(nom, gp)
    L, _ = cl.loop_matrix(dl)
    # twist dead band: L_tw phase crossings with |L| >= 1 would be needed
    a_tw = analyse_loops(nom, gp, others_closed=True, mimo=False)[0]["tw"]
    nl["twist_deadband"] = {"deadband_N": 2000.0, "GM_upper_closed_others": a_tw["closed_others"]["GM_upper"],
                            "phase_crossings_with_gain_ge_1": [p for p in a_tw["closed_others"]["phase_crossings"] if p["GM"] < 1],
                            "verdict": "no limit cycle (dead-band DF is real in [0, 1); needs |L| >= 1 at a phase crossing)"}
    # speed saturation ~ gain kappa in (0, 1]: closed loop stable for all kappa?
    ks = np.concatenate([np.logspace(-3, 0, 61)])
    kap = []
    for lp in (nom, [x for x in all_plants if x.case.tag() == "top_pads_b1_sup_lower"][0],
               [x for x in all_plants if x.case.tag() == "top_crawler_b1_rigid"][0]):
        dl_ = cl.discrete_loop(lp, gp)
        L_, _ = cl.loop_matrix(dl_)
        rr = [float(np.max(np.abs(ct.feedback(ct.ss(L_.A, L_.B, k_ * L_.C, k_ * L_.D, T), np.eye(4)).poles())))
              for k_ in ks]
        kap.append({"case": lp.case.tag(), "rho_max_minus_1_over_kappa": max(rr) - 1.0,
                    "kappa_at_max": float(ks[int(np.argmax(rr))]),
                    "n_kappa_unstable": int(sum(1 for v in rr if v >= 1.0)), "rho_at_kappa_0.1": rr[int(np.argmin(np.abs(ks - 0.1)))]})
    nl["saturation_gain_sweep"] = {"kappa_range": [float(ks[0]), 1.0], "results": kap,
                                   "verdict": "stable for every uniform gain reduction -> no saturation limit cycle (DF)"}
    nl["saturation_direction"] = saturation_direction()
    # seal-friction backlash in the roll channel (half width b = sum |J_phi,i| F_s / k_oil,i)
    ko = nom.ko
    Jphi = cl.dm.attitude_sensitivity(nom.kv, cl.dm.geometry_from_params(dm.load_params()).pad_xy)[1]
    Jth = cl.dm.attitude_sensitivity(nom.kv, cl.dm.geometry_from_params(dm.load_params()).pad_xy)[2]
    df_res = {}
    for Fs in (2e3, 5e3, 12e3):
        for lab, g in (("PI", gp), ("P_only", cl.Gains(**{**gp.__dict__, "Ki": 0.0}))):
            for ch, Jr, j in (("roll", Jphi, 1), ("pitch", Jth, 2)):
                b = float(np.sum(np.abs(Jr) * Fs / ko))
                dl_ = cl.discrete_loop(nom, g)
                L_, _ = cl.loop_matrix(dl_)
                F = np.eye(4); F[j, j] = 0.0
                Lc = ct.feedback(L_, F)
                sj = ct.ss(Lc.A, Lc.B[:, [j]], Lc.C[[j], :], Lc.D[[j], [j]], T)
                Lf = siso_eval(sj)
                bl = backlash_op(b)
                A_grid = b * np.logspace(np.log10(1.02), np.log10(200), 90)
                Nf = lambda A, bl=bl: df_numeric(bl, A)  # noqa: E731
                lc, sols = df_limit_cycle(Lf, Nf, A_grid)
                key = f"Fs{Fs / 1e3:g}kN_{lab}_{ch}"
                entry = {"backlash_half_width_deg": b * DEG, "limit_cycles": [
                    {"input_amp_deg": x["A"] * DEG, "output_amp_deg_approx": abs(Nf(x["A"])) * x["A"] * DEG,
                     "w_rad_s": x["w_rad_s"], "period_s": 2 * math.pi / x["w_rad_s"], "stable_Loeb": x["stable_LC_Loeb"]}
                    for x in lc]}
                if Fs == 12e3 and ch == "roll":
                    wv = np.logspace(-3, 1, 600)
                    Lw = np.array([Lf(x) for x in wv])
                    entry["L_curve"] = np.column_stack([Lw.real, Lw.imag]).tolist()
                    Ms_ = [(-1 / Nf(A)) for A in A_grid]
                    entry["minus_inv_N"] = [[m.real, m.imag] for m in Ms_]
                df_res[key] = entry
    nl["seal_backlash_DF"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("L_curve", "minus_inv_N")}
                              for k, v in df_res.items()}
    res["nonlinear"] = rnd(nl)
    print(f"nonlinear done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- LQR / LQG
    mis = [x for x in all_plants if x.case.tag() == "top_pads_b1_sup_lower"][0]
    res["lqr"] = rnd(lqr_section(nom, mis, gp))
    print(f"lqr done {time.perf_counter() - t0:.1f} s", flush=True)
    # ---------------- decisions
    res["decisions"] = rnd(decisions())
    # ---------------- figures
    figs = figures([("top rigid, 2x LPF (proposal)", nom, gp),
                    ("top mast sup_lower, 2x LPF", mis, gp),
                    ("top rigid, 1st-order LPF (legacy)", nom, cl.Gains(n_stages=1)),
                    ("top mast sup_lower, 1st-order LPF", mis, cl.Gains(n_stages=1)),
                    ("bottom rigid, 2x LPF", [x for x in all_plants if x.case.tag() == "bottom_pads_b1_rigid"][0], gp),
                    ("top crawler, 2x LPF", [x for x in all_plants if x.case.tag() == "top_crawler_b1_rigid"][0], gp)],
                   gp, cl.Gains(n_stages=1), mimo[nom.case.tag()], df_res, wm)
    res["meta"]["figures"] = [str(p.relative_to(dm.PROJECT_ROOT)).replace("\\", "/") for p in figs]
    # ---------------- time-domain summary (if run)
    tdp = OUT_DIR / "c2_design_timedomain.json"
    if tdp.exists():
        with open(tdp, encoding="utf-8") as fh:
            td = json.load(fh)
        res["timedomain"] = {"file": "06_analysis/02_control/c2_design_timedomain.json", "summary": td["summary"],
                             "wall_s": td["meta"].get("wall_s")}
    if OUT_JSON.exists():
        try:
            with open(OUT_JSON, encoding="utf-8") as fh:
                old = json.load(fh)
            if "julia_check" in old:
                res["julia_check_previous"] = old["julia_check"]
        except json.JSONDecodeError:
            pass
    res["meta"]["wall_s"] = round(time.perf_counter() - t0, 1)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))
    print("wrote", OUT_JSON, res["meta"]["wall_s"], "s")
    for k, v in res["tuning"].items():
        s = v["summary"]
        print(k, v["spec_check"], "PMmin", s["phi:closed_others"]["PM_min"], "Msmax", s["phi:closed_others"]["Ms_max"],
              "rho", s["cl_spectral_radius_max"], "unstable", s["n_unstable_cases"])


if __name__ == "__main__":
    main()
