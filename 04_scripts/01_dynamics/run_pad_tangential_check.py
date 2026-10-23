"""Pad tangential (rod lateral) forces on slopes with the revised C2 (R1) on the reduced 6-DoF model, the mu-N
clipping question at pitch +3.7 deg, and a post-levelling pad re-anchoring action (dynamics_model.md 3.10, rev. 18).

Hand-off from cad-expert (00_docs/00_cad/leg_rod_lateral_check.md section 11):
  1. pad tangential force at roll 5.5 deg and on the diagonal D8 boundary (levelling end value and dynamic maximum),
  2. is the 36 kN at nose-down 3.7 deg clipped by mu N of the rear pads (slip) or a stick value,
  3. per-leg maximum tangential force inside the provisional limits (pitch 3.2 / roll 4.4 deg),
  4. re-anchoring action after levelling: unload a pad for a moment so that it slips and re-anchors; effect on the
     internal tangential force, F_min and attitude (+/-0.1 deg).

Models
  * Reduced 6-DoF plant with optional 1-mode equivalent flexible mast: run_mast_flex_c2_check.FlexPlant (import only).
    Pad tangential element = ground-fixed bushing k_t, c_t at the pad bottom with circular Coulomb cap mu N
    (mu 0.5, YAML), anchored at first contact. Controller = C2 revision R1 (run_c2_revision.C2R, gain set
    'R:BS_hold' = final option set of c2_design.md 16.5; 'R:it3' = original proposal), loop / delay / ramp / metrics =
    run_c2_timedomain.run_case (import only). Nothing in those files is modified; this script subclasses them.
  * k_t: 'yaml' = YAML L1 kt_per_pad (beam at the flat operating extension ~0.40 m, as all previous runs);
    'ext' = secant k_t(e) = series(dyn_model.k_leg_lateral(e, swivel), k_concrete) at the levelled extension of
    the slope (the cantilever gets much softer when the rod is extended: FL 8.7e6 N/m at 0.40 m, 3.9e6 at 0.67 m).
  * Independent quasi-static check (stage 'kin'): exact rotations, pads anchored at the settled crawler pose,
    final pose level, planar rigid DOF (x, y, yaw) from minimum spring energy, optional mu N return mapping.

Conventions: body x fwd, y left, z up; roll > 0 left side up, pitch > 0 nose down (floor slope = attitude on the
crawler); forces = force from the ground on the body/rod, body-axis x/y components at the pad (= rod lateral load,
perpendicular to the rod axis); legs FL, FR, RL, RR; SI units (kN / mm / deg only in the outputs).
Quaternions in the plant: (w, x, y, z), scalar first.

Run (project root, dynamics-dev activated; E-cores 16-27, below-normal priority, BLAS 1 thread):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_pad_tangential_check.py --stage <name> [--workers 12]
  stages: kin (s), checks (~1 min), clip (~1 min), main (~6 min), robust_d0 (~6 min), robust_seed (~4 min),
          ktext (~3 min), stick (~2 min), reanchor (~4 min), report (tables + figures, ~1 min)
Each stage updates its own key of 06_analysis/00_dynamics/pad_tangential_check.json; 'report' builds the tables and
pad_tangential_check_{timeseries,boundary,reanchor}.png.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "03_control"))
import dyn_model as dm  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402  (patches rcc.Plant = FlexPlant in this process)
import run_control_comparison as rcc  # noqa: E402
import run_c2_timedomain as c2t  # noqa: E402
import run_c2_revision as rcr  # noqa: E402  (registers the 'R:*' gain sets, SensorsS, C2R)
import run_mast_bending_check as mbc  # noqa: E402

ROOT = dm.PROJECT_ROOT
OUT_DIR = ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "pad_tangential_check.json"
CAD_JSON = ROOT / "01_cad" / "02_legs" / "leg_rod_lateral_check.json"
LEGS = dm.LEG_NAMES
DEG = math.pi / 180
F_MIN = float(dm.load_params()["control"]["F_min_cylinder_N"])  # YAML (rev. 30; was the literal 9452.55)
R1 = "R:BS_hold"          # C2 revision R1 final option set (c2_design.md 16.5)
IT3 = "R:it3"             # original proposal (dynamics_model.md 3.9.7 basis of the 36 kN value)
MASTS = ("rigid", "stiff", "upper", "lower")
RCFG: dict = {}           # per-run options of this script (kt per pad, re-anchoring spec, case id)
T_HOLD_DEFAULT = rcc.T_HOLD

# ------------------------------------------------------------------------------------------------ D8 diamonds


def diamond_points(Phi, Theta, prefix):
    """Boundary points of |phi|/Phi + |theta|/Theta = 1 (roll, pitch in deg)."""
    pts = [(f"{prefix}:pitch+{Theta:g}", 0.0, Theta), (f"{prefix}:pitch-{Theta:g}", 0.0, -Theta),
           (f"{prefix}:roll+{Phi:g}", Phi, 0.0), (f"{prefix}:roll-{Phi:g}", -Phi, 0.0)]
    for s in (0.25, 0.5, 0.75):
        pts.append((f"{prefix}:r+p+{s:g}", round(s * Phi, 4), round((1 - s) * Theta, 4)))
        pts.append((f"{prefix}:r+p-{s:g}", round(s * Phi, 4), round(-(1 - s) * Theta, 4)))
    pts.append((f"{prefix}:r-p+0.5", round(-0.5 * Phi, 4), round(0.5 * Theta, 4)))
    pts.append((f"{prefix}:r-p-0.5", round(-0.5 * Phi, 4), round(-0.5 * Theta, 4)))
    return pts


VER = diamond_points(5.5, 3.5, "V")      # verification range (D8 Theta 3.5 / Phi 5.5)
PRO = diamond_points(4.4, 3.2, "P")      # provisional operating limits (rod bending, C45)
ALL_PTS = VER + PRO
PT = {t: (r, p) for t, r, p in ALL_PTS}
PT["pitch+3.7"] = (0.0, 3.7)

# ------------------------------------------------------------------------------------------------ geometry helpers


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def floor_normal(roll_deg, pitch_deg):
    """Same convention as run_control_comparison.Plant: sx = -tan(pitch), sy = tan(roll), n = (-sx, -sy, 1)/|.|."""
    sx = -math.tan(math.radians(pitch_deg)); sy = math.tan(math.radians(roll_deg))
    n = np.array([-sx, -sy, 1.0])
    return n / np.linalg.norm(n)


_GEO = {}


def geo_ctx():
    if not _GEO:
        p = dm.load_params()
        geo = dm.geometry_from_params(p)
        kc = dm.k_concrete_westergaard()["k_slab_N_m"]
        L1 = p["contact"]["rigid_floor"]["L1"]
        _GEO.update(p=p, geo=geo, kc=float(p["contact"]["rigid_floor"]["concrete"]["k_N_m"]), kc_w=kc,
                    kt_yaml=np.array([L1["kt_per_pad_N_m"][n] for n in LEGS], float),
                    e_op=geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"],
                    mu=float(p["contact"]["rigid_floor"]["friction"]),
                    loads={lv: np.array([p["superstructure"]["auger_levels"][lv]["static_leg_loads_N"][n] for n in LEGS])
                           for lv in dm.LEVELS})
    return _GEO


def kt_of_ext(ext):
    """Secant pad tangential stiffness at extensions ext (4,): swivel cantilever (dyn_model) in series with concrete."""
    G_ = geo_ctx()
    kl = dm.k_leg_lateral_legs(G_["geo"], np.asarray(ext, float), guided_tip=False)
    return np.asarray(dm.series(kl, G_["kc"]), float)


# ------------------------------------------------------------------------------------------------ stage kin


def touch_pose(level, roll, pitch, settle=True):
    """Settled crawler pose exactly as run_control_comparison.Plant.__init__ (R = R_floor R_settle)."""
    G_ = geo_ctx(); p = G_["p"]; geo = G_["geo"]
    n = floor_normal(roll, pitch)
    phi = math.asin(-n[1]); th = math.atan2(n[0], n[2])
    R = _ry(th) @ _rx(phi)
    body = dm.body_with_rods(p, geo, level, G_["e_op"])
    qs = np.zeros(3)
    if settle:
        cxy, kcr, _ = dm.crawler_points(p)
        cgap = dm.crawler_gaps(p)
        _, qs, _ = dm.static_unilateral(cxy, kcr, -cgap, body.mass * geo.g, body.com[:2])
        R = R @ (_ry(qs[2]) @ _rx(qs[1]))
    O = n * (-geo.crawler_bottom_z + qs[0])
    return n, R, O, qs


def kin_internal(level, roll, pitch, kt_mode="yaml", mu=None, settle=True, final_att=(0.0, 0.0)):
    """Quasi-static pad tangential forces after levelling (independent of the time-domain model).
    Pads anchored at the settled crawler pose (pad bottom on the floor, legs along body -z); final pose = attitude
    final_att (roll, pitch rad), crawler clearance 50 mm (normal distance of the lowest crawler corner), planar DOF
    (X, Y, yaw) from minimum tangential spring energy (= in-plane force and yaw-moment equilibrium). mu: optional
    circular Coulomb cap with N = (static cylinder load + rod weight) * n_z, return mapping on the anchors."""
    from scipy.optimize import least_squares
    G_ = geo_ctx(); geo = G_["geo"]
    n, Rt, Ot, qs = touch_pose(level, roll, pitch, settle)
    b0 = np.column_stack([geo.pad_xy, geo.pad_z_retracted])
    ez_t = Rt[:, 2]
    e_t = np.array([n @ (Ot + Rt @ b0[i]) / (n @ ez_t) for i in range(4)])
    anc = np.array([Ot + Rt @ (b0[i] - np.array([0, 0, e_t[i]])) for i in range(4)])
    Pt = np.eye(3) - np.outer(n, n)
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0, geo.crawler_bottom_z], [x0, y1, geo.crawler_bottom_z],
                        [x1, y0, geo.crawler_bottom_z], [x1, y1, geo.crawler_bottom_z]])
    clr = dm.ASSUMPTIONS["crawler_clearance_m"]

    def pose(z):
        X, Y, psi = z
        Rf = _rz(psi) @ _ry(final_att[1]) @ _rx(final_att[0])
        O0 = np.array([X, Y, 0.0])
        Z = clr - min(n @ (O0 + Rf @ c) for c in corners)       # normal clearance of the lowest corner = 50 mm
        Z = Z / n[2]
        O = np.array([X, Y, Z])
        ez = Rf[:, 2]
        e = np.array([n @ (O + Rf @ b0[i]) / (n @ ez) for i in range(4)])
        pp = np.array([O + Rf @ (b0[i] - np.array([0, 0, e[i]])) for i in range(4)])
        return Rf, e, pp

    def solve(anc_, k_):
        def res(z):
            _, _, pp = pose(z)
            return np.concatenate([math.sqrt(k_[i]) * (Pt @ (pp[i] - anc_[i])) for i in range(4)])
        z0 = np.array([Ot[0], Ot[1], 0.0])
        sol = least_squares(res, z0, xtol=1e-15, ftol=1e-15, gtol=1e-15, method="lm")
        Rf, e, pp = pose(sol.x)
        F = np.array([-k_[i] * (Pt @ (pp[i] - anc_[i])) for i in range(4)])
        return sol, Rf, e, pp, F

    k = G_["kt_yaml"].copy()
    sol, Rf, e, pp, F = solve(anc, k)
    if kt_mode == "ext":                      # secant k_t at the levelled extension (fixed point, 3 passes)
        for _ in range(3):
            k = kt_of_ext(e)
            sol, Rf, e, pp, F = solve(anc, k)
    out = {"touch_ext_m": e_t.round(5).tolist(), "levelled_ext_m": e.round(5).tolist(), "kt_N_m": k.round(0).tolist(),
           "settle_qs": [float(qs[0]), float(qs[1] / DEG), float(qs[2] / DEG)]}
    Fb = (Rf.T @ F.T).T
    out["stick_body_xy_kN"] = (Fb[:, :2] / 1e3).round(3).tolist()
    out["stick_kN"] = (np.linalg.norm(Fb[:, :2], axis=1) / 1e3).round(3).tolist()
    out["stick_rel_disp_mm"] = (np.linalg.norm(F, axis=1) / k * 1e3).round(3).tolist()
    out["sum_F_kN"] = (F.sum(axis=0) / 1e3).round(6).tolist()
    out["yaw_deg"] = float(sol.x[2] / DEG)
    if mu is not None:
        N = (G_["loads"][level] + geo.rod_mass * geo.g) * n[2]
        anc2 = anc.copy()
        it = 0
        for it in range(200):
            over = np.linalg.norm(F, axis=1) > mu * N * (1 + 1e-12)
            if not over.any():
                break
            for i in np.where(over)[0]:
                Fc = F[i] * (mu * N[i] / np.linalg.norm(F[i]))
                anc2[i] = pp[i] + Fc / k[i]          # tangential part only (pp and anchor both on the floor plane)
            sol, Rf, e, pp, F = solve(anc2, k)
        Fb = (Rf.T @ F.T).T
        out["capped_body_xy_kN"] = (Fb[:, :2] / 1e3).round(3).tolist()
        out["capped_kN"] = (np.linalg.norm(Fb[:, :2], axis=1) / 1e3).round(3).tolist()
        out["muN_kN"] = (mu * N / 1e3).round(3).tolist()
        out["capped_iterations"] = it
    return out


def stage_kin():
    res = {"note": "quasi-static stick model, settled crawler pose -> level, planar equilibrium; kN, body axes"}
    G_ = geo_ctx()
    pts = ALL_PTS + [("pitch+3.7", 0.0, 3.7)]
    for lv in dm.LEVELS:
        for tag, ro, pi in pts:
            d = {}
            for km in ("yaml", "ext"):
                d[km] = kin_internal(lv, ro, pi, km, mu=G_["mu"])
            d["no_settle_yaml"] = kin_internal(lv, ro, pi, "yaml", settle=False)["stick_kN"]
            res[f"{lv}|{tag}"] = d
    # theta^2 scaling of the stick force (top, yaml)
    a = kin_internal("top", 0, 3.5, "yaml", settle=False)["stick_kN"][0]
    b = kin_internal("top", 0, 3.7, "yaml", settle=False)["stick_kN"][0]
    res["theta_sq_check"] = {"F3.5_over_F3.7_no_settle": a / b, "(3.5/3.7)^2": (3.5 / 3.7) ** 2}
    return res


# ------------------------------------------------------------------------------------------------ plant / controller


class TPlant(rmf.FlexPlant):
    """FlexPlant + optional per-pad k_t (RCFG['kt_per_pad'], c_t scaled to keep zeta) + anchor-slip bookkeeping."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        kp = RCFG.get("kt_per_pad")
        if kp is not None:
            kp = np.asarray(kp, float)
            self.ct = self.ct * np.sqrt(kp / self.kt)
            self.kt = kp.copy()
        self.case_id = RCFG.get("case_id")
        self.slip_cum = np.zeros(4); self.slip_hist = []
        if "dt_override" in RCFG and abs(self.dt - RCFG["dt_override"]) > 1e-15:
            raise RuntimeError("dt override not applied")

    def step(self, u, nsteps):
        pa = self.panc.copy(); pf = self.pflag.copy()
        a = super().step(u, nsteps)
        if nsteps > 1000:
            self.slip_cum[:] = 0.0; self.slip_hist = []
            return a
        both = (pf == 1) & (self.pflag == 1)
        self.slip_cum += np.where(both, np.linalg.norm(self.panc - pa, axis=1), 0.0)
        self.slip_hist.append(self.slip_cum.copy())
        return a


class C2RA(rcr.C2R):
    """C2 R1 + optional post-levelling re-anchoring sequence (RCFG['reanchor']):
    mode 'twist' : all four legs move along the twist vector n (no rigid attitude change) in the direction that
                   unloads the target pad's diagonal, at speed_frac v_max for the largest leg;
    mode 'single': only the target leg retracts at speed_frac v_max.
    Each step: move until the target pressure reading <= P_stop (or stroke cap, or another leg < F_min + 5 kN) ->
    hold hold_s -> return the commanded strokes to zero (integrated command) -> hold hold2_s -> next target.
    The C2 update keeps running (filters, relevel checks); its command is replaced while the sequence is active."""
    name = "C2RA"

    def __init__(self, ctx, contact="pressure"):
        super().__init__(ctx, contact=contact)
        self.ra = None; self.ra_log = []; self.ra_done = False

    def _log(self, t, what, **kw):
        self.ra_log.append(dict(t=round(float(t), 4), what=what, **kw))

    def update(self, m, t):
        was_done = self.done
        u = super().update(m, t)
        if self.ra is not None and was_done and not self.done:
            self._log(t, "relevel_triggered", during=not self.ra_done)
        spec = RCFG.get("reanchor")
        if not spec or self.ra_done or self.t_ready_first is None or t < self.t_ready_first + spec["wait_s"]:
            return u
        if self.ra is None:
            self.ra = {"k": 0, "st": "move", "t0": t, "cum": np.zeros(4)}
            self._log(t, "start", k=0)
        return self._ra(m, t, spec)

    def _ra(self, m, t, spec):
        ra = self.ra; c = self.c
        steps = spec["steps"]
        if ra["k"] >= len(steps):
            self.ra_done = True; self._log(t, "end")
            return np.zeros(4)
        tgt = LEGS.index(steps[ra["k"]])
        v = spec["speed_frac"] * c.vmax
        if spec["mode"] == "twist":
            n = np.asarray(c.n, float)
            dirv = -math.copysign(1.0, n[tgt]) * n / np.max(np.abs(n))
        else:
            dirv = np.zeros(4); dirv[tgt] = -1.0
        P = m["P"]
        ps = spec["P_stop_N"]
        P_stop = float(ps[min(ra["k"], len(ps) - 1)]) if isinstance(ps, (list, tuple)) else float(ps)
        st = ra["st"]
        if st == "move":
            others = [j for j in range(4) if j != tgt]
            low = min(P[j] for j in others) < c.F_min + 5e3
            cap = np.max(np.abs(ra["cum"])) >= spec["max_stroke_m"]
            if P[tgt] <= P_stop or cap or low:
                ra["st"] = "hold"; ra["t0"] = t
                self._log(t, "hold", k=ra["k"], leg=LEGS[tgt], P_kN=round(float(P[tgt]) / 1e3, 2),
                          reason="P_stop" if P[tgt] <= P_stop else ("cap" if cap else "guard"),
                          cum_mm=(ra["cum"] * 1e3).round(3).tolist())
                return np.zeros(4)
            u = dirv * v
            ra["cum"] = ra["cum"] + u * rcc.T_CTRL
            return u
        if st == "hold":
            if t - ra["t0"] >= spec["hold_s"] - 1e-9:
                ra["st"] = "return"; self._log(t, "return", k=ra["k"])
            return np.zeros(4)
        if st == "return":
            mx = float(np.max(np.abs(ra["cum"])))
            if mx < 1e-10:
                ra["st"] = "hold2"; ra["t0"] = t; self._log(t, "hold2", k=ra["k"])
                return np.zeros(4)
            lam = min(1.0, mx / (v * rcc.T_CTRL))
            u = -ra["cum"] / mx * v * lam
            ra["cum"] = ra["cum"] + u * rcc.T_CTRL
            return u
        if st == "hold2":
            if t - ra["t0"] >= spec["hold2_s"] - 1e-9:
                ra["k"] += 1; ra["st"] = "move"; ra["cum"] = np.zeros(4); ra["t0"] = t
                self._log(t, "next", k=ra["k"])
            return np.zeros(4)
        raise RuntimeError(st)


# ------------------------------------------------------------------------------------------------ one run

_EQS = {}


def eqs():
    if not _EQS:
        mast = mbc.load_mast(); boom = rmf.load_boom()
        for lv in dm.LEVELS:
            for sup in rmf.SUPPORTS:
                _EQS[(lv, sup)] = rmf.public(rmf.equivalent_mast(lv, sup, boom, mast))
    return _EQS


def _hist(pl):
    t = np.array(pl.hist_t); H = np.array(pl.hist); C = np.array(pl.slip_hist)
    if len(C) != len(t):
        raise RuntimeError("slip history length mismatch")
    return t, H, C


def tang_metrics(S, r, pl):
    """Pad tangential metrics from the 1 ms plant record (hist rows = acc[11:45]: Fl 0:4, Fmin 13:17, Ft_x 17:21,
    Ft_y 21:25, crawler Ftx 25, alpha 26:28, slip flag 30:34)."""
    t, H, C = _hist(pl)
    Fl = H[:, 0:4]; Fx = H[:, 17:21]; Fy = H[:, 21:25]; flag = H[:, 30:34]
    Fm = np.hypot(Fx, Fy)
    mu = pl.mu_pad; an = float(pl.nrm[2])
    out = {}
    touched = Fl > 0
    if not touched.any():
        return {"tang_error": "no pad contact"}
    t_first = float(t[np.argmax(touched.any(axis=1))])
    out["t_first_touch_s"] = round(t_first, 3)
    tl = r.get("t_crawler_liftoff_s"); tr = r.get("t_ready_s")
    dtc = float(np.median(np.diff(t))) if len(t) > 1 else 0.0

    def at(tq):
        return int(np.clip(np.searchsorted(t, tq - 1e-9), 0, len(t) - 1))

    def leg_vals(j):
        return {"Ft_kN": (Fm[j] / 1e3).round(2).tolist(), "Ft_xy_kN": (np.column_stack([Fx[j], Fy[j]]) / 1e3).round(2).tolist(),
                "Fl_kN": (Fl[j] / 1e3).round(2).tolist(),
                "util": (Fm[j] / np.maximum(mu * Fl[j] * an, 1.0)).round(4).tolist(),
                "sum_Ft_xy_kN": [round(float(Fx[j].sum()) / 1e3, 3), round(float(Fy[j].sum()) / 1e3, 3)]}
    if tr is not None:
        out["ready"] = leg_vals(at(tr))
    out["end"] = leg_vals(len(t) - 1)
    post = t >= t_first
    jm = np.argmax(np.where(post[:, None], Fm, -1.0), axis=0)
    out["dyn_max_kN"] = [round(float(Fm[jm[i], i]) / 1e3, 2) for i in range(4)]
    out["dyn_max_t_s"] = [round(float(t[jm[i]]), 3) for i in range(4)]
    out["dyn_max_Fl_kN"] = [round(float(Fl[jm[i], i]) / 1e3, 2) for i in range(4)]
    out["dyn_max_phase"] = [("lift" if (tl is None or t[jm[i]] < tl) else
                             ("levelling" if (tr is None or t[jm[i]] < tr) else "levelled")) for i in range(4)]
    if tl is not None:
        pl_ = t >= tl
        out["dyn_max_post_liftoff_kN"] = [round(float(Fm[pl_, i].max()) / 1e3, 2) for i in range(4)]
        jj = np.argmax(np.where(pl_[:, None], Fm, -1.0), axis=0)
        out["dyn_max_post_liftoff_Fl_kN"] = [round(float(Fl[jj[i], i]) / 1e3, 2) for i in range(4)]
        out["slip_mm_post_liftoff"] = ((C[-1] - C[at(tl)]) * 1e3).round(3).tolist()
    out["Fl_max_kN"] = (Fl.max(axis=0) / 1e3).round(2).tolist()
    out["slip_mm_total"] = (C[-1] * 1e3).round(3).tolist()
    out["slip_time_s"] = (flag.sum(axis=0) * dtc).round(3).tolist()
    last = [float(t[np.where(flag[:, i] > 0)[0][-1]]) if (flag[:, i] > 0).any() else None for i in range(4)]
    out["t_last_slip_s"] = [None if v is None else round(v, 3) for v in last]
    if tr is not None:
        out["slip_after_ready"] = bool((flag[t >= tr] > 0).any())
    out["mu"] = mu
    return out


def reanchor_metrics(S, r, pl, ctrl):
    log = ctrl.ra_log
    if not log:
        return {"ra_error": "sequence did not start"}
    t, H, C = _hist(pl)
    Fl = H[:, 0:4]; Fx = H[:, 17:21]; Fy = H[:, 21:25]; fmin = H[:, 13:17]
    Fm = np.hypot(Fx, Fy)
    Wr = pl.Wr
    ts = np.asarray(S["t"]); att = np.degrees(np.column_stack([S["phi"], S["theta"]]))

    def at(tq):
        return int(np.clip(np.searchsorted(t, tq - 1e-9), 0, len(t) - 1))

    t0 = log[0]["t"]
    pre = (ts >= t0 - 0.5) & (ts <= t0)
    att0 = att[pre].mean(axis=0)
    j0 = at(t0)
    out = {"log": log, "att0_deg": att0.round(5).tolist(), "Ft0_kN": (Fm[j0] / 1e3).round(2).tolist(),
           "Ft0_xy_kN": (np.column_stack([Fx[j0], Fy[j0]]) / 1e3).round(2).tolist(),
           "Fcyl0_kN": ((Fl[j0] - Wr) / 1e3).round(2).tolist()}
    starts = [e for e in log if e["what"] in ("start", "next")]
    ends = [e for e in log if e["what"] in ("next", "end")]
    steps = []
    for k, (a, b) in enumerate(zip(starts, ends, strict=False)):
        ta, tb = a["t"], b["t"]
        w = (t >= ta) & (t <= tb)
        ws = (ts >= ta) & (ts <= tb)
        hold = [e for e in log if e["what"] == "hold" and e.get("k") == k]
        jh = at(hold[0]["t"]) if hold else None
        tret = [e["t"] for e in log if e["what"] == "return" and e.get("k") == k]
        th2 = [e["t"] for e in log if e["what"] == "hold2" and e.get("k") == k]
        bounds = [ta, hold[0]["t"] if hold else tb, tret[0] if tret else tb, th2[0] if th2 else tb, tb]
        by_phase = {}
        for nm, (p0, p1) in zip(("move", "hold", "return", "hold2"), zip(bounds[:-1], bounds[1:], strict=True), strict=True):
            wp = (t >= p0) & (t <= p1)
            if wp.any():
                fm = fmin[wp] - Wr
                by_phase[nm] = {"min_kN": round(float(fm.min()) / 1e3, 2), "leg": LEGS[int(np.argmin(fm.min(axis=0)))]}
        steps.append({"k": k, "leg": hold[0]["leg"] if hold else None, "reason": hold[0]["reason"] if hold else None,
                      "P_stop_reading_kN": hold[0]["P_kN"] if hold else None,
                      "stroke_mm": hold[0]["cum_mm"] if hold else None,
                      "duration_s": round(tb - ta, 3),
                      "Ft_after_kN": (Fm[at(tb)] / 1e3).round(2).tolist(),
                      "Ft_at_hold_kN": None if jh is None else (Fm[jh] / 1e3).round(2).tolist(),
                      "min_true_cyl_kN": round(float((fmin[w] - Wr).min()) / 1e3, 2) if w.any() else None,
                      "min_true_cyl_per_leg_kN": ((fmin[w] - Wr).min(axis=0) / 1e3).round(2).tolist() if w.any() else None,
                      "max_true_cyl_kN": round(float((Fl[w] - Wr).max()) / 1e3, 2) if w.any() else None,
                      "min_cyl_by_phase": by_phase,
                      "max_att_dev_deg": (np.abs(att[ws] - att0).max(axis=0)).round(4).tolist() if ws.any() else None,
                      "slip_mm": ((C[at(tb)] - C[at(ta)]) * 1e3).round(3).tolist()})
    out["steps"] = steps
    endev = [e for e in log if e["what"] == "end"]
    tend = endev[0]["t"] if endev else log[-1]["t"]
    w = (t >= t0) & (t <= tend); ws = (ts >= t0) & (ts <= tend)
    out["min_true_cyl_kN"] = round(float((fmin[w] - Wr).min()) / 1e3, 2)
    out["max_true_cyl_kN"] = round(float((Fl[w] - Wr).max()) / 1e3, 2)
    out["max_att_dev_deg"] = (np.abs(att[ws] - att0).max(axis=0)).round(4).tolist()
    out["Ft_max_during_kN"] = (Fm[w].max(axis=0) / 1e3).round(2).tolist()
    out["final_att_deg"] = att[-1].round(4).tolist()
    out["Ft_final_kN"] = (Fm[-1] / 1e3).round(2).tolist()
    out["Fcyl_final_kN"] = ((Fl[-1] - Wr) / 1e3).round(2).tolist()
    out["stroke_return_err_mm"] = None
    out["duration_s"] = round(tend - t0, 2)
    out["completed"] = bool(endev)
    out["relevel_events"] = [e for e in log if e["what"] == "relevel_triggered"]
    return out


def run_one(case):
    """One closed-loop case. case: dict(id, group, level, slope, mast, gainset, seed, beta, Fs, contact, cfg, rcfg)."""
    case = dict(case)
    cfg = dict(case.get("cfg", {})); cfg["record"] = True
    mast = case.get("mast", "rigid")
    if mast != "rigid":
        cfg["mast_eq"] = eqs()[(case["level"], mast)]
    rmf.CONFIG.clear(); rmf.CONFIG.update(cfg)
    RCFG.clear(); RCFG.update(case.get("rcfg", {})); RCFG["case_id"] = case["id"]
    # re-assert the patches with THIS module's classes (spawned workers import this file as __mp_main__)
    rcc.Plant = TPlant; rcc.Sensors = rcr.SensorsS; c2t.C2D = C2RA
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[case["gainset"]])
    rcc.T_HOLD = float(case.get("t_hold", T_HOLD_DEFAULT))
    dt_old = rcc.DT
    if "dt_override" in RCFG:
        rcc.DT = float(RCFG["dt_override"])
    ro, pi = PT[case["slope"]] if case["slope"] in PT else case["angles"]
    t0 = time.perf_counter()
    try:
        r = c2t.run_case(level=case["level"], roll=ro, pitch=pi, beta=case.get("beta", 1.0e9), Fs=case.get("Fs", 0.0),
                         contact=case.get("contact", "pressure"), seed=case.get("seed", 12345), keep_series=True)
        pl = rmf.LAST["plant"]; ctrl = rmf.LAST["ctrl"]
        if not isinstance(pl, TPlant) or pl.case_id != case["id"]:
            raise RuntimeError("plant identity check failed (patch not applied in this worker)")
        if type(ctrl) is not C2RA:
            raise RuntimeError("controller identity check failed")
        if pl.flex != (0 if mast == "rigid" else 1):
            raise RuntimeError("mast flag mismatch")
        if RCFG.get("kt_per_pad") is not None and not np.allclose(pl.kt, RCFG["kt_per_pad"]):
            raise RuntimeError("kt override not applied")
        if abs(pl.mu_pad - float(cfg.get("mu_pad", pl.mu))) > 1e-12:
            raise RuntimeError("mu_pad not applied")
        S = r.pop("_series")
        out = {k: r.get(k) for k in ("t_touch_s", "t_crawler_liftoff_s", "t_ready_s", "min_true_cyl_force_kN",
                                     "min_true_leg", "ss_true_att_deg_maxabs", "max_pressure_bar", "fails",
                                     "levelled_loads_true_kN", "final_clearance_mm")}
        out.update(rmf.extra_metrics(S, r, pl))
        out["tang"] = tang_metrics(S, r, pl)
        out["kt_N_m"] = pl.kt.round(0).tolist()
        if r.get("t_ready_s") is not None:      # true attitude (roll, pitch) at the levelling end [deg]
            j = int(np.clip(np.searchsorted(np.asarray(S["t"]), r["t_ready_s"] - 1e-9), 0, len(S["t"]) - 1))
            out["att_ready_deg"] = [float(np.degrees(S["phi"][j])), float(np.degrees(S["theta"][j]))]
        if RCFG.get("reanchor"):
            out["reanchor"] = reanchor_metrics(S, r, pl, ctrl)
            out["reanchor"]["stroke_return_err_mm"] = None
        if case.get("keep_series"):
            t, H, C = _hist(pl)
            out["_series"] = {"t": t, "H": H, "C": C, "S": S}
    except Exception as e:  # noqa: BLE001
        import traceback
        out = {"error": repr(e), "tb": traceback.format_exc()[-1500:]}
    finally:
        rcc.DT = dt_old
        rcc.T_HOLD = T_HOLD_DEFAULT
    out.update({k: case.get(k) for k in ("id", "group", "level", "slope", "mast", "gainset", "seed")})
    out["mu_pad"] = cfg.get("mu_pad", 0.5); out["kt_mode"] = case.get("kt_mode", "yaml")
    out["beta_GPa"] = case.get("beta", 1.0e9) / 1e9; out["Fs_kN"] = case.get("Fs", 0.0) / 1e3
    out["wall_s"] = round(time.perf_counter() - t0, 1)
    return out


# ------------------------------------------------------------------------------------------------ case lists

_EXT = {}


def levelled_ext(tag):
    if tag not in _EXT:
        ro, pi = PT[tag]
        _EXT[tag] = kin_internal("top", ro, pi, "ext")["levelled_ext_m"]
    return _EXT[tag]


def mk(cid, group, level, slope, mast="rigid", gainset=R1, seed=12345, kt_mode="yaml", mu=None, **kw):
    c = {"id": cid, "group": group, "level": level, "slope": slope, "mast": mast, "gainset": gainset, "seed": seed,
         "kt_mode": kt_mode, "cfg": {}, "rcfg": {}}
    if mu is not None:
        c["cfg"]["mu_pad"] = mu
    if kt_mode == "ext":
        c["rcfg"]["kt_per_pad"] = kt_of_ext(levelled_ext(slope)).tolist()
    for k, v in kw.items():
        if k in ("rcfg_extra",):
            c["rcfg"].update(v)
        else:
            c[k] = v
    return c


def cases_for(stage):
    pts = [t for t, _, _ in ALL_PTS]
    C = []
    if stage == "clip":
        for gs in (IT3, R1):
            for mu in (0.5, 5.0):
                for km in ("yaml", "ext"):
                    for mast in ("rigid", "stiff"):
                        C.append(mk(f"clip|{gs}|mu{mu}|{km}|{mast}", "clip", "top", "pitch+3.7", mast, gs, kt_mode=km, mu=mu))
    elif stage == "main":
        for lv in dm.LEVELS:
            for mast in MASTS:
                for tg in pts:
                    C.append(mk(f"main|{lv}|{mast}|{tg}", "main", lv, tg, mast))
    elif stage == "robust_d0":
        for mast in MASTS:
            for tg in pts:
                for s in range(3):
                    C.append(mk(f"d0|{mast}|{tg}|{s}", "robust_d0", "top", tg, mast, R1 + "_d0", seed=12345 + s))
    elif stage == "robust_seed":
        for mast in MASTS:
            for tg in pts:
                for s in (1, 2):
                    C.append(mk(f"seed|{mast}|{tg}|{s}", "robust_seed", "top", tg, mast, R1, seed=12345 + s))
        for mast in ("rigid", "stiff"):
            for tg in ("V:pitch+3.5", "V:roll+5.5", "V:r+p+0.5", "P:pitch+3.2", "P:roll+4.4"):
                for b in (0.69e9, 1.6e9):
                    C.append(mk(f"beta|{mast}|{tg}|{b:g}", "robust_beta", "top", tg, mast, R1, beta=b))
    elif stage == "ktext":
        for lv in dm.LEVELS:
            for mast in ("rigid", "stiff"):
                for tg in pts:
                    C.append(mk(f"ktext|{lv}|{mast}|{tg}", "ktext", lv, tg, mast, kt_mode="ext"))
    elif stage == "stick":
        for km in ("yaml", "ext"):
            for tg in pts:
                C.append(mk(f"stick|top|{km}|{tg}", "stick", "top", tg, "rigid", kt_mode=km, mu=5.0))
        for lv in ("middle", "bottom"):
            for tg in pts:
                C.append(mk(f"stick|{lv}|yaml|{tg}", "stick", lv, tg, "rigid", kt_mode="yaml", mu=5.0))
    elif stage in ("reanchor", "reanchor2", "reanchor3"):
        base = {"wait_s": 2.0, "speed_frac": 0.25, "P_stop_N": 20e3, "hold_s": 1.0, "hold2_s": 1.0,
                "max_stroke_m": 0.02, "steps": ["RR", "RL", "RR", "RL", "RR", "RL"], "mode": "twist"}

        def ra(cid, tg, mast="rigid", km="yaml", lv="top", mu=None, Fs=0.0, **spec):
            sp = dict(base); sp.update(spec)
            th = 55.0 if sp["speed_frac"] >= 0.2 else 2.0 + len(sp["steps"]) * (
                2 * 0.004 / (sp["speed_frac"] * round(float(dm.load_params()["actuator"]["max_speed_m_s"]), 6)) + sp["hold_s"] + sp["hold2_s"]) + 15.0
            c = mk(cid, stage, lv, tg, mast, kt_mode=km, mu=mu, t_hold=th, Fs=Fs, rcfg_extra={"reanchor": sp})
            return c
        if stage == "reanchor3":      # descending stop-threshold staircase (limits the load picked up by the other pads)
            stair = [45e3, 45e3, 30e3, 30e3, 20e3, 20e3]
            for tg in ("V:pitch+3.5", "V:pitch-3.5", "P:pitch-3.2", "V:roll+5.5", "V:roll-5.5", "V:r+p-0.5"):
                for km in ("yaml", "ext"):
                    C.append(ra(f"ra3|twist|{tg}|rigid|{km}|v0.1|stair", tg, km=km, speed_frac=0.1, P_stop_N=stair))
                    if tg in ("V:pitch-3.5", "P:pitch-3.2"):
                        C.append(ra(f"ra3|twist|{tg}|rigid|{km}|v0.1|Pstop20", tg, km=km, speed_frac=0.1))
            C.append(ra("ra3|twist|V:pitch-3.5|stiff|yaml|v0.1|stair", "V:pitch-3.5", "stiff", speed_frac=0.1,
                        P_stop_N=stair))
            return C
        if stage == "reanchor2":      # slow unloading: speed and stop-threshold sensitivity (2nd pass)
            for tg in ("V:pitch+3.5", "V:roll+5.5", "V:roll-5.5", "V:r+p+0.5", "P:pitch+3.2", "P:roll+4.4"):
                for sf in (0.1, 0.05):
                    for ps in (20e3, 25e3):
                        C.append(ra(f"ra2|twist|{tg}|rigid|yaml|v{sf:g}|Pstop{ps / 1e3:g}", tg, speed_frac=sf,
                                    P_stop_N=ps))
            for tg in ("V:pitch+3.5", "V:roll+5.5"):
                for mast in ("stiff",):
                    C.append(ra(f"ra2|twist|{tg}|{mast}|yaml|v0.05|Pstop20", tg, mast, speed_frac=0.05))
                C.append(ra(f"ra2|twist|{tg}|rigid|ext|v0.05|Pstop20", tg, km="ext", speed_frac=0.05))
                for ps in (30e3, 35e3):
                    C.append(ra(f"ra2|twist|{tg}|rigid|yaml|Fs12|v0.05|Pstop{ps / 1e3:g}", tg, Fs=12e3,
                                speed_frac=0.05, P_stop_N=ps))
                C.append(ra(f"ra2|twist|{tg}|rigid|yaml|v0.05|Pstop20|2steps", tg, speed_frac=0.05,
                            steps=["RR", "RL"]))
                c = ra(f"ra2|twist|{tg}|rigid|yaml|v0.05|Pstop20|d0", tg, speed_frac=0.05)
                c["gainset"] = R1 + "_d0"; C.append(c)
            return C
        sl = ("V:pitch+3.5", "V:pitch-3.5", "V:roll+5.5", "V:roll-5.5", "V:r+p+0.5", "V:r+p-0.5", "P:pitch+3.2",
              "P:roll+4.4")
        for tg in sl:
            for mast in ("rigid", "stiff"):
                for km in ("yaml", "ext"):
                    C.append(ra(f"ra|twist|{tg}|{mast}|{km}", tg, mast, km))
            C.append(ra(f"ra|single|{tg}|rigid|yaml", tg, mode="single"))
            C.append(ra(f"ra|single|{tg}|rigid|ext", tg, km="ext", mode="single"))
        for tg in ("V:pitch+3.5", "V:roll+5.5", "V:r+p+0.5"):
            for ps in (15e3, 30e3):
                C.append(ra(f"ra|twist|{tg}|rigid|yaml|Pstop{ps / 1e3:g}", tg, P_stop_N=ps))
            for mu in (0.3, 0.7):
                C.append(ra(f"ra|twist|{tg}|rigid|yaml|mu{mu}", tg, mu=mu))
            for ps in (20e3, 30e3):
                C.append(ra(f"ra|twist|{tg}|rigid|yaml|Fs12|Pstop{ps / 1e3:g}", tg, Fs=12e3, P_stop_N=ps))
            for mast in ("upper", "lower"):
                C.append(ra(f"ra|twist|{tg}|{mast}|yaml", tg, mast))
        for lv in ("middle", "bottom"):
            for tg in ("V:pitch+3.5", "V:roll+5.5"):
                C.append(ra(f"ra|twist|{tg}|rigid|yaml|{lv}", tg, lv=lv))
        for tg in ("V:pitch+3.5", "V:roll+5.5"):
            C.append(ra(f"ra|twist|{tg}|rigid|yaml|d0", tg))
            C[-1]["gainset"] = R1 + "_d0"
    else:
        raise ValueError(stage)
    return C


# ------------------------------------------------------------------------------------------------ checks


def stage_checks():
    out = {}
    G_ = geo_ctx()
    # (c1) beam k_t at the operating extension reproduces the YAML value
    k_op = kt_of_ext(G_["e_op"])
    out["kt_beam_vs_yaml_rel"] = ((k_op - G_["kt_yaml"]) / G_["kt_yaml"]).tolist()
    # (c2) levelled extensions vs cad table (leg_rod_lateral_check.md 2)
    cad = {"V:pitch+3.5": [0.654, 0.654, 0.347, 0.347], "V:roll+5.5": [0.405, 0.660, 0.410, 0.642],
           "V:pitch-3.5": [0.374, 0.374, 0.660, 0.660]}
    out["levelled_ext_vs_cad_m"] = {k: {"this": levelled_ext(k), "cad": v,
                                        "max_abs_diff": float(np.max(np.abs(np.array(levelled_ext(k)) - v)))}
                                    for k, v in cad.items()}
    out["kt_ext_N_m"] = {k: kt_of_ext(levelled_ext(k)).round(0).tolist() for k in ("V:pitch+3.5", "V:roll+5.5",
                                                                                   "P:pitch+3.2", "P:roll+4.4")}
    # (c3) recorder subclass is non-intrusive: TPlant (yaml kt) vs FlexPlant, same case, series bitwise
    case = mk("chk|tplant", "check", "top", "V:pitch+3.5", "rigid", keep_series=True)
    a = run_one(case)
    rmf.CONFIG.clear(); rmf.CONFIG["record"] = True
    rcc.Plant = rmf.FlexPlant; rcc.Sensors = rcr.SensorsS; c2t.C2D = rcr.C2R
    rcc.CA.update(c2t.OPTION_DEFAULTS); rcc.CA.update(c2t.GAINSETS[R1])
    rb = c2t.run_case(level="top", roll=0.0, pitch=3.5, seed=12345, keep_series=True)
    Sb = rb.pop("_series"); plb = rmf.LAST["plant"]
    Sa = a["_series"]["S"]
    d = max(float(np.max(np.abs(np.asarray(Sa[k]) - np.asarray(Sb[k])))) for k in ("u", "Ftrue", "P", "x", "phi", "theta"))
    Hb = np.array(plb.hist)
    dH = float(np.max(np.abs(a["_series"]["H"] - Hb)))
    out["tplant_vs_flexplant_max_abs_diff"] = {"series": d, "record": dH}
    # (c4) equilibrium of the recorded pad forces at the levelled state: sum of body-x/y components ~ 0
    out["sum_Ft_ready_body_xy_kN"] = a["tang"]["ready"]["sum_Ft_xy_kN"]
    out["Ft_ready_kN"] = a["tang"]["ready"]["Ft_kN"]
    # (c5) time-step convergence of the tangential metrics (dt 5e-4 vs 2.5e-4), two cases
    conv = {}
    for tg in ("V:pitch+3.5", "V:roll+5.5"):
        r1 = run_one(mk(f"chk|dt1|{tg}", "check", "top", tg))
        r2 = run_one(mk(f"chk|dt2|{tg}", "check", "top", tg, rcfg_extra={"dt_override": 2.5e-4}))
        conv[tg] = {"dt5e-4": {"ready": r1["tang"]["ready"]["Ft_kN"], "dyn": r1["tang"]["dyn_max_kN"],
                               "min_kN": r1.get("min_true_cyl_force_kN")},
                    "dt2.5e-4": {"ready": r2["tang"]["ready"]["Ft_kN"], "dyn": r2["tang"]["dyn_max_kN"],
                                 "min_kN": r2.get("min_true_cyl_force_kN")}}
        conv[tg]["max_rel_ready"] = float(np.max(np.abs(np.array(r1["tang"]["ready"]["Ft_kN"]) -
                                                        r2["tang"]["ready"]["Ft_kN"]) / np.array(r2["tang"]["ready"]["Ft_kN"])))
        conv[tg]["max_rel_dyn"] = float(np.max(np.abs(np.array(r1["tang"]["dyn_max_kN"]) - r2["tang"]["dyn_max_kN"])
                                               / np.array(r2["tang"]["dyn_max_kN"])))
    out["dt_convergence"] = conv
    return out


# ------------------------------------------------------------------------------------------------ io


def load_out():
    if OUT_JSON.exists():
        return json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return {}


def save_out(d):
    OUT_JSON.write_text(json.dumps(d, indent=1, default=float), encoding="utf-8")


def run_pool(cases, workers):
    r0 = run_one(dict(cases[0]))     # compile numba in the main process first (spawn workers reuse the cache)
    if len(cases) == 1:
        return [r0]
    from multiprocessing import Pool
    with Pool(workers) as pool:
        rest = pool.map(run_one, cases[1:], chunksize=1)
    return [r0] + rest


# ------------------------------------------------------------------------------------------------ report


def _runs(d, *stages):
    out = []
    for s in stages:
        out += d.get(s, {}).get("runs", [])
    return [r for r in out if "error" not in r]


def boundary_table(runs, prefix, field):
    """Per point and leg: max over runs of tang[field] (field = 'ready' -> Ft_kN, or 'dyn_max_kN')."""
    tab = {}
    for r in runs:
        if not str(r["slope"]).startswith(prefix):
            continue
        tg = r["slope"]
        v = r["tang"]["ready"]["Ft_kN"] if field == "ready" else r["tang"].get(field)
        if v is None:
            continue
        e = tab.setdefault(tg, {"max_kN": [0.0] * 4, "n": 0, "argmax": [None] * 4})
        e["n"] += 1
        for i in range(4):
            if v[i] > e["max_kN"][i]:
                e["max_kN"][i] = v[i]
                e["argmax"][i] = f"{r['level']}|{r['mast']}|{r['gainset']}|{r['seed']}"
    return tab


def envelope(tab):
    mx = [0.0] * 4; arg = [None] * 4
    for tg, e in tab.items():
        for i in range(4):
            if e["max_kN"][i] > mx[i]:
                mx[i] = e["max_kN"][i]; arg[i] = f"{tg} ({e['argmax'][i]})"
    return {"per_leg_max_kN": [round(v, 2) for v in mx], "where": arg}


def stage_report(d):
    rep = {}
    # --- item 2: clipping at pitch +3.7
    clip = {}
    for r in _runs(d, "clip"):
        tr = r["tang"]
        clip[r["id"]] = {"ready_Ft_kN": tr["ready"]["Ft_kN"] if "ready" in tr else None,
                         "ready_util": tr["ready"]["util"] if "ready" in tr else None,
                         "ready_Fl_kN": tr["ready"]["Fl_kN"] if "ready" in tr else None,
                         "dyn_max_kN": tr["dyn_max_kN"], "dyn_max_phase": tr["dyn_max_phase"],
                         "slip_mm_post_liftoff": tr.get("slip_mm_post_liftoff"), "slip_time_s": tr["slip_time_s"],
                         "t_last_slip_s": tr["t_last_slip_s"], "t_liftoff": r.get("t_crawler_liftoff_s"),
                         "t_ready": r.get("t_ready_s"), "min_true_cyl_force_kN": r.get("min_true_cyl_force_kN"),
                         "kt_N_m": r["kt_N_m"]}
    rep["clip_pitch3.7"] = clip
    # --- independent check: quasi-static stick model (with the simulated levelled attitude) vs mu 5 runs
    cmp = {}; worst = 0.0
    for r in _runs(d, "stick"):
        if r["level"] != "top" or "att_ready_deg" not in r or "ready" not in r["tang"]:
            continue
        ro, pi = PT[r["slope"]]
        att = tuple(math.radians(v) for v in r["att_ready_deg"])
        kv = np.array(kin_internal("top", ro, pi, r["kt_mode"], final_att=att)["stick_kN"])
        k0 = np.array(d["kin"][f"top|{r['slope']}"][r["kt_mode"]]["stick_kN"])
        sim = np.array(r["tang"]["ready"]["Ft_kN"])
        rel = float(np.max(np.abs(sim - kv)) / max(kv.max(), 1e-9))
        rel0 = float(np.max(np.abs(sim - k0)) / max(k0.max(), 1e-9))
        cmp[r["id"]] = {"sim_kN": sim.tolist(), "kin_sim_att_kN": kv.round(2).tolist(), "kin_level_kN": k0.tolist(),
                        "att_ready_deg": [round(v, 4) for v in r["att_ready_deg"]],
                        "max_abs_diff_over_max_kin": round(rel, 4), "same_vs_level_kin": round(rel0, 4)}
        worst = max(worst, rel)
    rep["kin_vs_stick_sim"] = {"cases": cmp, "worst_rel": round(worst, 4),
                               "note": "difference / largest kinematic pad force; the simulation anchors each pad at its "
                                       "own first contact and keeps the crawler until lift-off"}
    # --- item 1/3: boundary envelopes
    base = _runs(d, "main", "robust_d0", "robust_seed")
    for prefix, name in (("V:", "verification_5.5_3.5"), ("P:", "provisional_4.4_3.2")):
        sub = {}
        for lab, runs in (("kt_yaml_all", base), ("kt_ext", _runs(d, "ktext")),
                          ("stick_mu5", _runs(d, "stick"))):
            tr = boundary_table(runs, prefix, "ready"); td = boundary_table(runs, prefix, "dyn_max_kN")
            tp = boundary_table(runs, prefix, "dyn_max_post_liftoff_kN")
            sub[lab] = {"ready": tr, "dyn": td, "dyn_post_liftoff": tp,
                        "env_ready": envelope(tr), "env_dyn": envelope(td), "env_dyn_post_liftoff": envelope(tp)}
        rep[name] = sub
    # failures / force minima in the boundary runs (sanity: C2 R1 must still pass)
    fails = [(r["id"], r.get("fails")) for r in base + _runs(d, "ktext") if r.get("fails")]
    rep["boundary_runs_fails"] = fails
    rep["boundary_runs_min_cyl_kN"] = min((r["min_true_cyl_force_kN"] for r in base if r.get("min_true_cyl_force_kN") is not None),
                                          default=None)
    errs = [(r.get("id"), r.get("error")) for s in ("clip", "main", "robust_d0", "robust_seed", "ktext", "stick", "reanchor", "reanchor2", "reanchor3")
            for r in d.get(s, {}).get("runs", []) if "error" in r]
    rep["errors"] = errs
    # slip summary in the base boundary runs
    sl = {}
    for r in base:
        tr = r["tang"]
        if tr.get("slip_after_ready"):
            sl.setdefault("slip_after_ready", []).append(r["id"])
        s = tr.get("slip_mm_post_liftoff")
        if s is not None:
            k = r["slope"]
            e = sl.setdefault(k, [0.0] * 4)
            sl[k] = [max(e[i], s[i]) for i in range(4)]
    rep["slip_post_liftoff_max_mm"] = sl
    # --- item 4: re-anchoring
    ra = {}
    for r in _runs(d, "reanchor", "reanchor2", "reanchor3"):
        a = r.get("reanchor", {})
        if "steps" not in a:
            ra[r["id"]] = a
            continue
        ra[r["id"]] = {"Ft0_kN": a["Ft0_kN"], "Ft_final_kN": a["Ft_final_kN"], "Ft_max_during_kN": a.get("Ft_max_during_kN"),
                       "Ft_after_step_kN": [s["Ft_after_kN"] for s in a["steps"]],
                       "P_stop_kN": [s["P_stop_reading_kN"] for s in a["steps"]],
                       "reason": [s["reason"] for s in a["steps"]],
                       "stroke_mm": [s["stroke_mm"] for s in a["steps"]],
                       "min_true_cyl_kN": a["min_true_cyl_kN"], "max_true_cyl_kN": a["max_true_cyl_kN"],
                       "max_att_dev_deg": a["max_att_dev_deg"], "final_att_deg": a["final_att_deg"],
                       "Fcyl0_kN": a["Fcyl0_kN"], "Fcyl_final_kN": a["Fcyl_final_kN"], "duration_s": a["duration_s"],
                       "completed": a["completed"], "relevel_events": a["relevel_events"],
                       "step_min_cyl_kN": [s["min_true_cyl_kN"] for s in a["steps"]],
                       "step_att_dev_deg": [s["max_att_dev_deg"] for s in a["steps"]],
                       "step_min_by_phase": [s.get("min_cyl_by_phase") for s in a["steps"]],
                       "kt_mode": r["kt_mode"], "mast": r["mast"], "level": r["level"]}
    rep["reanchor"] = ra
    return rep


def figures(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    paths = []
    # (1) time series
    fig, ax = plt.subplots(3, 2, figsize=(13, 9), sharex="col")
    for jc, tg in enumerate(("V:pitch+3.5", "V:roll+5.5")):
        r = run_one(mk(f"fig|{tg}", "fig", "top", tg, keep_series=True))
        s = r["_series"]; t = s["t"]; H = s["H"]; C = s["C"]
        Fm = np.hypot(H[:, 17:21], H[:, 21:25])
        for i in range(4):
            ax[0, jc].plot(t, Fm[:, i] / 1e3, color=cols[i], lw=0.8, label=LEGS[i])
            ax[0, jc].plot(t, r["mu_pad"] * H[:, i] / 1e3,
                           color=cols[i], lw=0.6, ls=":")
            ax[1, jc].plot(t, H[:, i] / 1e3, color=cols[i], lw=0.8)
            ax[2, jc].plot(t, C[:, i] * 1e3, color=cols[i], lw=0.8)
        for a in ax[:, jc]:
            for key, ls in (("t_crawler_liftoff_s", "--"), ("t_ready_s", "-.")):
                if r.get(key) is not None:
                    a.axvline(r[key], color="k", ls=ls, lw=0.7)
            a.grid(alpha=0.3)
        ax[0, jc].set_title(f"top auger, rigid mast, C2 R1, {tg} (dashed: crawler lift-off, dash-dot: ready)", fontsize=9)
        ax[0, jc].set_ylabel("pad tangential |F| [kN]\n(dotted: mu N along leg)")
        ax[1, jc].set_ylabel("pad contact force (leg axis) [kN]")
        ax[2, jc].set_ylabel("cumulative anchor slip [mm]")
        ax[2, jc].set_xlabel("time from leg start [s]")
        ax[0, jc].legend(fontsize=8, ncol=4)
        ax[0, jc].set_ylim(0, 80)
        lo = (r.get("tang", {}).get("t_first_touch_s") or 0) - 1
        ax[2, jc].set_xlim(max(0, lo), (r.get("t_ready_s") or t[-1]) + 10)
    fig.tight_layout()
    p = OUT_DIR / "pad_tangential_check_timeseries.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    # (2) boundary
    rep = d["report"]
    cad = json.loads(CAD_JSON.read_text(encoding="utf-8")) if CAD_JSON.exists() else None
    fig, ax = plt.subplots(2, 2, figsize=(14, 8))
    for jc, (_prefix, name, pts) in enumerate((("V:", "verification_5.5_3.5", VER), ("P:", "provisional_4.4_3.2", PRO))):
        tags = [t for t, _, _ in pts]
        xs = np.arange(len(tags))
        for jr, lab in enumerate(("kt_yaml_all", "kt_ext")):
            sub = rep[name][lab]
            for i in range(4):
                rd = [sub["ready"].get(tg, {}).get("max_kN", [np.nan] * 4)[i] for tg in tags]
                dy = [sub["dyn"].get(tg, {}).get("max_kN", [np.nan] * 4)[i] for tg in tags]
                ax[jr, jc].plot(xs + (i - 1.5) * 0.08, rd, "o", color=cols[i], ms=4, label=f"{LEGS[i]} levelled")
                ax[jr, jc].plot(xs + (i - 1.5) * 0.08, dy, "^", color=cols[i], ms=4, mfc="none",
                                label=f"{LEGS[i]} dynamic max")
            st = rep[name]["stick_mu5"]["ready"]
            sm = [max(st.get(tg, {}).get("max_kN", [np.nan] * 4)) for tg in tags]
            if lab == "kt_yaml_all":
                ax[jr, jc].plot(xs, sm, "k_", ms=14, mew=2, label="stick demand (mu 5), max leg")
            kin = [max(d["kin"].get(f"top|{tg}", {}).get("yaml" if lab == "kt_yaml_all" else "ext", {}).get("stick_kN", [np.nan]))
                   for tg in tags]
            ax[jr, jc].plot(xs, kin, "x", color="grey", ms=8, label="quasi-static stick (indep.), max leg")
            if cad is not None and lab == "kt_yaml_all":
                cv = []
                for tg in tags:
                    ro, pi = PT[tg]
                    best = min(cad["d8_boundary_scan"], key=lambda e: (e["phi_deg"] - ro) ** 2 + (e["theta_deg"] - pi) ** 2)
                    ok = (best["phi_deg"] - ro) ** 2 + (best["theta_deg"] - pi) ** 2 < 0.05 ** 2
                    cv.append(max(best["F_design_kN"]) if ok else np.nan)
                ax[jr, jc].plot(xs, cv, "s", color="purple", mfc="none", ms=8, label="cad estimate (calibrated), max leg")
            ax[jr, jc].set_xticks(xs); ax[jr, jc].set_xticklabels([t.split(":")[1] for t in tags], rotation=45, fontsize=7)
            ax[jr, jc].set_ylabel("pad tangential force [kN]")
            ax[jr, jc].set_title(f"{name}: k_t {'YAML (flat extension)' if lab == 'kt_yaml_all' else 'secant k_t(e)'}; "
                                 "max over levels / masts / seeds / delay", fontsize=8)
            ax[jr, jc].grid(alpha=0.3)
        ax[0, jc].legend(fontsize=6, ncol=3)
    fig.tight_layout()
    p = OUT_DIR / "pad_tangential_check_boundary.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    # (3) re-anchoring time series (top, rigid, pitch +3.5, twist)
    fig, ax = plt.subplots(4, 2, figsize=(13, 10), sharex="col")
    for jc, (tg, mode) in enumerate((("V:pitch+3.5", "twist"), ("V:roll+5.5", "twist"))):
        case = [c for c in cases_for("reanchor2") if c["id"] == f"ra2|{mode}|{tg}|rigid|yaml|v0.1|Pstop20"][0]
        case = dict(case); case["keep_series"] = True; case["id"] += "|fig"
        r = run_one(case)
        s = r["_series"]; t = s["t"]; H = s["H"]; S = s["S"]
        Fm = np.hypot(H[:, 17:21], H[:, 21:25])
        Wr = geo_ctx()["geo"].rod_mass * geo_ctx()["geo"].g   # per leg (4,): front / rear moving parts differ
        log = r["reanchor"]["log"]; t0 = log[0]["t"]; t1 = log[-1]["t"]
        w = (t >= t0 - 2) & (t <= t1 + 2); ws = (S["t"] >= t0 - 2) & (S["t"] <= t1 + 2)
        att0 = np.array(r["reanchor"]["att0_deg"])
        for i in range(4):
            ax[0, jc].plot(t[w], Fm[w, i] / 1e3, color=cols[i], lw=0.8, label=LEGS[i])
            ax[1, jc].plot(t[w], (H[w, 13 + i] - Wr[i]) / 1e3, color=cols[i], lw=0.8)
            ax[3, jc].plot(S["t"][ws], (np.asarray(S["x"])[ws, i] - np.asarray(S["x"])[ws][0, i]) * 1e3, color=cols[i], lw=0.8)
        ax[1, jc].axhline(F_MIN / 1e3, color="k", ls="--", lw=0.7)
        ax[2, jc].plot(S["t"][ws], np.degrees(np.asarray(S["phi"])[ws]) - att0[0], "k", lw=0.8, label="roll - roll0")
        ax[2, jc].plot(S["t"][ws], np.degrees(np.asarray(S["theta"])[ws]) - att0[1], "m", lw=0.8, label="pitch - pitch0")
        ax[2, jc].axhline(0.1, color="r", ls=":", lw=0.7); ax[2, jc].axhline(-0.1, color="r", ls=":", lw=0.7)
        ax[0, jc].set_title(f"re-anchoring (twist, 0.1 v_max, P_stop 20 kN), top, rigid mast, {tg}", fontsize=9)
        ax[0, jc].set_ylabel("pad tangential |F| [kN]"); ax[0, jc].legend(fontsize=8, ncol=4)
        ax[1, jc].set_ylabel("true cylinder force [kN]\n(dashed F_min)")
        ax[2, jc].set_ylabel("attitude change [deg]"); ax[2, jc].legend(fontsize=8)
        ax[3, jc].set_ylabel("rod position change [mm]"); ax[3, jc].set_xlabel("time from leg start [s]")
        for a in ax[:, jc]:
            a.grid(alpha=0.3)
    fig.tight_layout()
    p = OUT_DIR / "pad_tangential_check_reanchor.png"; fig.savefig(p, dpi=90); plt.close(fig); paths.append(p)
    return [str(x.relative_to(ROOT)) for x in paths]


# ------------------------------------------------------------------------------------------------ main


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("kin", "checks", "clip", "main", "robust_d0", "robust_seed", "reanchor2", "reanchor3",
                                                       "ktext", "stick", "reanchor", "report"))
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    cores = c2t.set_affinity()
    t0 = time.perf_counter()
    d = load_out()
    d.setdefault("meta", {}).update({
        "script": "04_scripts/01_dynamics/run_pad_tangential_check.py", "doc": "00_docs/01_dynamics/dynamics_model.md 3.10",
        "frame": "body x fwd, y left, z up; roll > 0 left up, pitch > 0 nose down; forces from ground on body at the pad",
        "controller": f"C2 revision R1 = gain set {R1} (run_c2_revision.C2R), original proposal = {IT3}",
        "plant": "run_mast_flex_c2_check.FlexPlant (reduced 6-DoF, L1, crawler layout D, dt 5e-4 s), record every 1 ms",
        "F_min_N": F_MIN, "mu_pad_yaml": geo_ctx()["mu"], "kt_yaml_N_m": geo_ctx()["kt_yaml"].tolist(),
        "affinity": cores})
    if args.stage == "kin":
        d["kin"] = stage_kin()
    elif args.stage == "checks":
        d["checks"] = stage_checks()
    elif args.stage == "report":
        d["report"] = stage_report(d)
        save_out(d)
        d["meta"]["figures"] = figures(d)
    else:
        cases = cases_for(args.stage)
        runs = run_pool(cases, args.workers)
        for r in runs:
            r.pop("_series", None)
        d[args.stage] = {"n": len(runs), "wall_s": round(time.perf_counter() - t0, 1), "runs": runs}
        ne = sum("error" in r for r in runs)
        print(f"stage {args.stage}: {len(runs)} runs, {ne} errors")
    d["meta"].setdefault("stage_wall_s", {})[args.stage] = round(time.perf_counter() - t0, 1)
    save_out(d)
    print("wrote", OUT_JSON, round(time.perf_counter() - t0, 1), "s")


if __name__ == "__main__":
    main()
