"""Independent checks for the S3 final judgement (dynamics_model.md 5.7, rev. 17).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s3_lift_check.py
Writes 06_analysis/00_dynamics/s3_lift_check.json (about 1 min). Does not import 03_src.

Part A - V8(a) crawler energy (damping off, free vibration): reads the cad-expert
    07_results/S3/<case>/energy.npz (via 07_results/S3/index.json) and splits E(t) - E0
    (geometric contact energy, double precision) into the 1 s window-mean linear trend, the
    oscillation spectrum and the per-mode energy rates 2 |zeta| omega E_i from the mode fits in
    verify_S3_L1.json (mode energy E_i = omega_i^2 A_i^2 / 2, A_i mass-normalised amplitude).
    Predicted semi-implicit (symplectic) Euler energy oscillation: (omega_i dt / 2) E_i at 2 f_i.
Part B - V5 / V6 exact pad statics: one rigid body (superstructure top + 4 rods at e), exact
    rotation R = Ry(pitch) Rx(roll), 4 pad spheres (radius = swivel ball height, bottom = pad
    bottom, L1 kn per pad), vertical one-sided springs, crawler not in contact, horizontal free
    (bushing forces self-equilibrated). Variant "small_angle" (moment arms fixed, no P-delta)
    reproduces the reference convention.
Part C - V4 quasi-static lift with P-delta: as Part B plus the 24 crawler spheres of YAML
    contact.crawler.sphere_layout (float32 kn); all legs e = v_max t (equivalent time origin =
    start command + ramp / 2); events by root finding. Linear variant = run_reference.lift_reference
    (dm.static_unilateral).
Part D - V4 dynamic lift, nonlinear 6-DoF rigid body (quaternion wxyz, body angular velocity),
    superstructure top + rods at e = 0 (as the reference 3-DoF), crawler and pad spring-dashpots
    max(0, k pen + c pen_dot) (vertical), and - variant "bushing" - the L1 pad bushing: from the
    first touch a horizontal spring-dashpot (kt, ct actual = YAML ct_per_pad_N_s_m) between the
    ball centre and its world anchor at touch (no Coulomb return mapping; the friction use
    |F_t| / (mu N) is recorded). Variant "free" = no bushing (reference 3-DoF physics + P-delta +
    6-DoF inertia). e(t) = min(v_max t, e_op). DOP853 rtol 1e-10 atol 1e-12 max_step 5e-4 s,
    restarted at each pad touch (anchor set there). kn_crawler x1 and x3 (dashpot x sqrt 3).
Gravity (0, 0, -9.80665) m/s^2 world. Units SI; angles in deg in the output. Frames: body
x forward, y left, z up (CLAUDE.md); roll about x, pitch about y (ZYX, yaw 0 in B/C).
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, fsolve

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

T0 = time.perf_counter()
P = dm.load_params(ROOT / "02_params" / "rexome33.yaml")
REF = json.load(open(ROOT / "06_analysis/00_dynamics/reference.json", encoding="utf-8"))
CHR = json.load(open(ROOT / "06_analysis/01_chrono/13_S3/verify_S3_L1.json", encoding="utf-8"))
IDX = json.load(open(ROOT / "07_results/S3/index.json", encoding="utf-8"))
G = float(P["meta"]["gravity_m_s2"])
geo = dm.geometry_from_params(P)
V = geo.v_max
LEGS = dm.LEG_NAMES
ZF = float(P["ground"]["crawler_bottom_z_m"])
LAY = P["contact"]["crawler"]["sphere_layout"]
RAD = float(LAY["sphere_radius_m"])
KN_CR = float(np.float32(P["contact"]["crawler"]["kn_per_sphere_N_m"]))
L1y = P["contact"]["rigid_floor"]["L1"]
K_PAD = np.array([float(L1y["kn_per_pad_N_m"][n]) for n in LEGS])
C_PAD = np.array([float(L1y["cn_per_pad_N_s_m"][n]) for n in LEGS])
K_T = np.array([float(L1y["bushing_stiffness_per_pad_N_m"][n]) for n in LEGS])
C_T = np.array([float(L1y["ct_per_pad_N_s_m"][n]) for n in LEGS])
MU = float(P["contact"]["rigid_floor"]["friction"])
E_OP = np.array([float(L1y["derivation"]["operating_extension_m"][n]) for n in LEGS])
R_PAD = float(P["legs"]["FL"]["pad"]["swivel_center_above_pad_bottom_m"])
ROD_W = np.array([float(P["legs"][n]["moving_part"]["mass_kg"]) for n in LEGS]) * G
F_MIN = float(P["control"]["F_min_cylinder_N"])
TOUCH = np.asarray(geo.touch_extension, float)
X3 = dm.crawler_kn_scales(P)[-1]

# Lift event windows follow v_max (rev. 31: 22.667 -> 20.924 mm/s moved the touches from about 15.0 s to
# 16.3 s and broke the fixed windows). They are anchored on the geometric first touch min(TOUCH) / v_max
# (equivalent time origin) with the offsets the fixed windows had at 22.667 mm/s (anchor 15.04 s):
# Part C 14.0 .. 16.5 s, Part D 14.7 .. 16.4 s. Both must hold every touch and the crawler lift-off.
T_FIRST_TOUCH_GEOMETRIC_S = float(TOUCH.min() / V)
QUASI_STATIC_WINDOW_OFFSET_S = (-1.0, 1.5)
DYNAMIC_WINDOW_OFFSET_S = (-0.35, 1.35)
QUASI_STATIC_GRID_STEP_S = 2e-3
BUSHING_AT_T1_NOTE = ("instantaneous value at the window end t1, not judged; depends on t1 through the phase of "
                      "the about 3 Hz pitch-surge mode after crawler lift-off (zeta 0.014, tau about 3.8 s)")


def lift_window(offset_s):
    """(start, end) s of a lift event window, offset from the geometric first touch."""
    return T_FIRST_TOUCH_GEOMETRIC_S + offset_s[0], T_FIRST_TOUCH_GEOMETRIC_S + offset_s[1]


def first_index(indices, event, window):
    """First index of a found event; a clear error instead of an IndexError when the window misses it."""
    if len(indices) == 0:
        raise RuntimeError(f"Part C: no {event} in the window {window[0]:.3f} .. {window[1]:.3f} s "
                           f"(v_max {V * 1e3:.3f} mm/s)")
    return int(indices[0])


def crawler_centres():
    """(24,3) crawler sphere centres, body coordinates (rollers then end shoes, left track first)."""
    yc = float(LAY["track_centre_y_m"])
    pts = []
    for y in (yc, -yc):
        for x in LAY["roller_x_m"]:
            pts.append((x, y, ZF + RAD))
        for x, g in zip(LAY["end_shoe_x_m"], LAY["end_shoe_gap_m"]):
            pts.append((x, y, ZF + g + RAD))
    return np.array(pts, float)


C_CR = crawler_centres()


def rot(ro, pi):
    """R = Ry(pitch) Rx(roll)."""
    cr, sr, cp, sp = math.cos(ro), math.sin(ro), math.cos(pi), math.sin(pi)
    return np.array([[cp, sp * sr, sp * cr], [0, cr, -sr], [-sp, cp * sr, cp * cr]])


# ------------------------------------------------------------------ Part A: V8(a) crawler energy
def part_a():
    res = {}
    for case in ("v8a_crawler_dt1e-04", "v8a_crawler_dt2e-04"):
        d = ROOT / IDX[case]
        z = np.load(d / "energy.npz")
        cols = [str(c) for c in z["columns"]]
        e = z["energy"]
        cg = z["contact_geometric"]
        ch = CHR["cases"][case]
        ek0 = float(ch["E_kin0_J"])
        dt = float(ch["dt_s"])
        t = e[:, cols.index("t_s")]
        eg = (e[:, cols.index("kinetic_J")] + e[:, cols.index("gravity_J")] + cg[:, 0] + cg[:, 1]
              + e[:, cols.index("bushing_spring_J")])
        rel = (eg - eg[0]) / ek0
        ts = float(np.median(np.diff(t)))
        nw = int(round(1.0 / ts))
        nf = (len(t) // nw) * nw
        tm = t[:nf].reshape(-1, nw).mean(axis=1)
        em = rel[:nf].reshape(-1, nw).mean(axis=1)
        p = np.polyfit(tm, em, 1)
        r = rel - np.polyval(p, t)
        r -= r.mean()
        w = np.hanning(len(r))
        spec = np.abs(np.fft.rfft(r * w)) * 2 / w.sum()
        f = np.fft.rfftfreq(len(r), ts)
        modes = {}
        rate = 0.0
        for m in ch["modes"]:
            om = 2 * math.pi * m["f_damped_Hz"]
            ei = 0.5 * om ** 2 * m["amplitude"] ** 2
            ri = -2 * m["zeta_fit"] * om * ei
            rate += ri
            k2 = int(np.argmin(np.abs(f - 2 * m["f_damped_Hz"])))
            sl = slice(max(k2 - 3, 0), k2 + 4)
            modes[m["mode"]] = {
                "f_Hz": m["f_damped_Hz"], "E_i_J": ei, "zeta_fit_damping_off": m["zeta_fit"],
                "zeta_physical": m["zeta_physical"],
                "zeta_fit_over_zeta_physical": m["zeta_fit"] / m["zeta_physical"],
                "energy_rate_from_zeta_rel_E_kin0_per_s": ri / ek0,
                "line_at_2f_rel_E_kin0": float(spec[sl].max()),
                "predicted_symplectic_line_at_2f_rel_E_kin0 (omega dt/2 E_i / E_kin0)": om * dt / 2 * ei / ek0,
            }
        dt_indep = []
        for k in np.argsort(spec)[::-1]:
            if f[k] < 0.2 or any(abs(f[k] - 2 * mm["f_Hz"]) < 0.15 for mm in modes.values()):
                continue
            if all(abs(f[k] - q[0]) > 0.15 for q in dt_indep):
                dt_indep.append([float(f[k]), float(spec[k])])
            if len(dt_indep) == 6:
                break
        res[case] = {
            "dt_s": dt, "E_kin0_J": ek0, "sample_s": ts,
            "max_rise_rel (plan wording)": float(rel.max()),
            "trend_1s_means_rel_per_s": float(p[0]), "trend_rel_over_window": float(p[0] * (tm[-1] - tm[0])),
            "trend_predicted_from_mode_zeta_rel_per_s": rate / ek0,
            "window_mean_residual_max_rel": float(np.abs(em - np.polyval(p, tm)).max()),
            "p2p_first_5s_rel": float(np.ptp(rel[: int(5 / ts)])),
            "modes": modes,
            "other_lines_not_at_2f (Hz, rel)": dt_indep,
            "crawler_contact_energy_mean_J": float(cg[:, 1].mean()),
        }
    return res


# ------------------------------------------------------------------ Part B: V5 / V6 exact statics
def pads_static(e, exact=True):
    bw = dm.body_with_rods(P, geo, "top", e)
    W = bw.mass * G
    c = bw.com
    pad = np.column_stack([geo.pad_xy, geo.pad_z_retracted - e + R_PAD])

    def f(s):
        z, ro, pi = s
        if exact:
            R = rot(ro, pi)
            pw = np.array([0, 0, z]) + pad @ R.T
            g = np.array([0, 0, z]) + R @ c
        else:
            pw = pad.copy()
            pw[:, 2] = pad[:, 2] + z + ro * pad[:, 1] - pi * pad[:, 0]
            g = c.copy()
        F = K_PAD * np.maximum(R_PAD - (pw[:, 2] - ZF), 0.0)
        return F, pw, g, W

    def res(s):
        F, pw, g, W = f(s)
        return np.array([(F.sum() - W) / W, np.sum(F * (pw[:, 1] - g[1])) / W,
                         -np.sum(F * (pw[:, 0] - g[0])) / W])

    s = fsolve(res, [-0.005, 0.0, 0.0], xtol=1e-13)
    s = fsolve(res, s, xtol=1e-13)
    F, *_ = f(s)
    return F, s, float(np.abs(res(s)).max())


def part_b():
    out = {}
    for exact in (True, False):
        F0, s0, r0 = pads_static(E_OP, exact)
        F1, s1, _ = pads_static(E_OP + np.array([1e-3, 0, 0, 0]), exact)
        F5, s5, _ = pads_static(E_OP + np.array([5e-3, 0, 0, 0]), exact)
        r = {"residual_rel_W": r0, "F0_N": F0.tolist(), "attitude0_deg (roll, pitch)": np.degrees(s0[1:]).tolist(),
             "V5_dF_1mm_N": (F1 - F0).tolist(), "V5_datt_1mm_deg": np.degrees(s1[1:] - s0[1:]).tolist(),
             "V5_dF_5mm_N": (F5 - F0).tolist(), "V5_datt_5mm_deg": np.degrees(s5[1:] - s0[1:]).tolist()}
        for sign, name, leg in ((1, "FL+", 2), (-1, "FL-", 3)):
            def fmin(d, leg=leg, sign=sign):
                return pads_static(E_OP + np.array([sign * d, 0, 0, 0]), exact)[0][leg] - ROD_W[leg] - F_MIN

            def lift(d, leg=leg, sign=sign):
                return pads_static(E_OP + np.array([sign * d, 0, 0, 0]), exact)[0][leg] - 1e-6

            r["V6_" + name] = {"leg": LEGS[leg], "F_min_mm": brentq(fmin, 0, 0.03, xtol=1e-11) * 1e3,
                               "liftoff_mm": brentq(lift, 0, 0.03, xtol=1e-11) * 1e3}
        out["exact_pdelta" if exact else "small_angle_no_pdelta (reference convention)"] = r
    c5 = CHR["cases"]["v5"]
    out["chrono_cases_v5_keys"] = sorted(c5.keys())
    return out


# ------------------------------------------------------------------ Part C: quasi-static lift
def exact_lift_state(e, kn_scale, x0):
    bw = dm.body_with_rods(P, geo, "top", e)
    W = bw.mass * G
    c = bw.com
    pad = np.column_stack([geo.pad_xy, geo.pad_z_retracted - e + R_PAD])
    kcr = KN_CR * kn_scale

    def forces(s):
        z0, ro, pi = s
        R = rot(ro, pi)
        o = np.array([0.0, 0.0, z0])
        cw = o + C_CR @ R.T
        pw = o + pad @ R.T
        Fc = kcr * np.maximum(RAD - (cw[:, 2] - ZF), 0.0)
        Fp = K_PAD * np.maximum(R_PAD - (pw[:, 2] - ZF), 0.0)
        return Fc, Fp, cw, pw, o + R @ c

    def resid(s):
        Fc, Fp, cw, pw, g = forces(s)
        return np.array([(Fc.sum() + Fp.sum() - W) / W,
                         (np.sum(Fc * (cw[:, 1] - g[1])) + np.sum(Fp * (pw[:, 1] - g[1]))) / W,
                         -(np.sum(Fc * (cw[:, 0] - g[0])) + np.sum(Fp * (pw[:, 0] - g[0]))) / W])

    s = fsolve(resid, x0, xtol=1e-14)
    if np.abs(resid(s)).max() > 1e-10:
        raise RuntimeError(f"Part C: no convergence at e = {e}")
    Fc, Fp, cw, pw, _ = forces(s)
    return s, R_PAD - (pw[:, 2] - ZF), RAD - (cw[:, 2] - ZF)


def part_c():
    out = {}
    xy_cr, k_cr, _ = dm.crawler_points(P)
    gap_cr = dm.crawler_gaps(P)
    bw = dm.body_with_rods(P, geo, "top", E_OP)
    W, cg = bw.mass * G, bw.com[:2]
    for name, sc in (("x1", 1.0), ("x3", X3)):
        def lin_flags(t):
            delta = np.concatenate([np.minimum(V * t, E_OP) - TOUCH, -gap_cr])
            _, _, act = dm.static_unilateral(np.vstack([geo.pad_xy, xy_cr]), np.concatenate([K_PAD, k_cr * sc]),
                                             delta, W, cg)
            return np.concatenate([act[:4], [act[4:].any()]])

        window = lift_window(QUASI_STATIC_WINDOW_OFFSET_S)
        tg = np.arange(*window, QUASI_STATIC_GRID_STEP_S)
        fl = np.array([lin_flags(t) for t in tg])
        lin = {}
        for col, lab in enumerate(list(LEGS) + ["crawler_off"]):
            k = first_index(np.where(fl[1:, col] != fl[:-1, col])[0], f"linear {lab} flag change", window)
            lo, hi, f0 = tg[k], tg[k + 1], fl[k, col]
            for _ in range(45):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if lin_flags(mid)[col] == f0 else (lo, mid)
            lin[lab] = 0.5 * (lo + hi)
        x = np.array([-0.003, 0.0, 0.003])
        rows = []
        for t in tg:
            x, pp, pc = exact_lift_state(np.minimum(V * t, E_OP), sc, x)
            rows.append((x.copy(), pp, pc))
        ex = {}
        for i, lab in enumerate(LEGS):
            pp = np.array([r[1][i] for r in rows])
            k = first_index(np.where((pp[1:] > 0) & (pp[:-1] <= 0))[0], f"exact {lab} touch", window)
            ex[lab] = brentq(lambda t: exact_lift_state(np.minimum(V * t, E_OP), sc, rows[k][0])[1][i],
                             tg[k], tg[k + 1], xtol=1e-12)
        pcm = np.array([r[2].max() for r in rows])
        k = first_index(np.where((pcm[1:] <= 0) & (pcm[:-1] > 0))[0], "exact crawler lift-off", window)
        ex["crawler_off"] = brentq(lambda t: exact_lift_state(np.minimum(V * t, E_OP), sc, rows[k][0])[2].max(),
                                   tg[k], tg[k + 1], xtol=1e-12)
        out[name] = {"window_s": list(window), "linear_reference_convention_s": lin, "exact_pdelta_s": ex,
                     "exact_minus_linear_ms": {k2: (ex[k2] - lin[k2]) * 1e3 for k2 in lin}}
    return out


# ------------------------------------------------------------------ Part D: 6-DoF dynamic lift
bw0 = dm.body_with_rods(P, geo, "top", np.zeros(4))
MASS, COM, IB = bw0.mass, bw0.com, bw0.inertia
IB_INV = np.linalg.inv(IB)
C_TOT = dm.crawler_damping_total(float(P["contact"]["crawler"]["kn_total_N_m"]),
                                 dm.body_with_rods(P, geo, "top", E_OP).mass)
N_ROL = int((dm.crawler_gaps(P) <= 0).sum())
CR_B = C_CR - COM
PAD0_B = np.column_stack([geo.pad_xy, geo.pad_z_retracted + R_PAD]) - COM


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def qmul(a, b):
    return np.array([a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
                     a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
                     a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
                     a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]])


class Lift6:
    def __init__(self, scale, bushing):
        self.kcr = KN_CR * scale
        self.ccr = C_TOT / N_ROL * math.sqrt(scale)
        self.bushing = bushing
        self.anchor = np.full((4, 2), np.nan)

    def forces(self, t, y, anchor=None):
        anchor = self.anchor if anchor is None else anchor
        p, q, v, w = y[0:3], y[3:7] / np.linalg.norm(y[3:7]), y[7:10], y[10:13]
        R = qmat(q)
        e = np.minimum(V * t, E_OP)
        ed = np.where(V * t < E_OP, V, 0.0)
        pad_b = PAD0_B - np.column_stack([np.zeros(4), np.zeros(4), e])
        rc, rp = CR_B @ R.T, pad_b @ R.T
        cw, pw = p + rc, p + rp
        wW = R @ w
        vc = v + np.cross(wW, rc)
        vp = v + np.cross(wW, rp) + R[:, 2][None, :] * (-ed[:, None])
        pen_c = RAD - (cw[:, 2] - ZF)
        pen_p = R_PAD - (pw[:, 2] - ZF)
        Fc = np.where(pen_c > 0, np.maximum(self.kcr * pen_c - self.ccr * vc[:, 2], 0.0), 0.0)
        Fp = np.where(pen_p > 0, np.maximum(K_PAD * pen_p - C_PAD * vp[:, 2], 0.0), 0.0)
        Ft = np.zeros((4, 2))
        if self.bushing:
            on = ~np.isnan(anchor[:, 0])
            Ft[on] = -K_T[on, None] * (pw[on, :2] - anchor[on]) - C_T[on, None] * vp[on, :2]
        return R, rc, rp, pw, Fc, Fp, Ft, pen_c, pen_p

    def rhs(self, t, y):
        R, rc, rp, pw, Fc, Fp, Ft, _, _ = self.forces(t, y)
        q, w = y[3:7], y[10:13]
        F = np.array([Ft[:, 0].sum(), Ft[:, 1].sum(), Fc.sum() + Fp.sum() - MASS * G])
        Mw = (np.cross(rc, np.column_stack([0 * Fc, 0 * Fc, Fc])).sum(axis=0)
              + np.cross(rp, np.column_stack([Ft[:, 0], Ft[:, 1], Fp])).sum(axis=0))
        wd = IB_INV @ (R.T @ Mw - np.cross(w, IB @ w))
        qd = 0.5 * qmul(q, np.array([0.0, *w]))
        return np.concatenate([y[7:10], qd, F / MASS, wd])


def settle_on_crawler(scale):
    kcr = KN_CR * scale
    W = MASS * G

    def res(s):
        R = rot(s[1], s[2])
        rc = CR_B @ R.T
        F = kcr * np.maximum(RAD - (s[0] + rc[:, 2] - ZF), 0.0)
        return np.array([(F.sum() - W) / W, np.sum(F * rc[:, 1]) / W, -np.sum(F * rc[:, 0]) / W])

    s = fsolve(res, [COM[2] - 0.003, 0.0, 0.003], xtol=1e-13)
    q = qmul(np.array([math.cos(s[2] / 2), 0, math.sin(s[2] / 2), 0]),
             np.array([math.cos(s[1] / 2), math.sin(s[1] / 2), 0, 0]))
    return np.concatenate([[0.0, 0.0, s[0]], q, np.zeros(6)]), math.degrees(s[2])


def run6(scale, bushing):
    t0, t1 = lift_window(DYNAMIC_WINDOW_OFFSET_S)
    m = Lift6(scale, bushing)
    y, pitch0 = settle_on_crawler(scale)
    t = t0
    touch = [math.nan] * 4
    segs = []
    while True:
        free = [i for i in range(4) if math.isnan(touch[i])]
        evs = []
        for i in free:
            def ev(tt, yy, i=i):
                return m.forces(tt, yy)[8][i]
            ev.terminal, ev.direction = True, 1
            evs.append(ev)
        sol = solve_ivp(m.rhs, (t, t1), y, method="DOP853", rtol=1e-10, atol=1e-12, max_step=5e-4,
                        events=evs or None, dense_output=True)
        segs.append((sol.t[0], sol.t[-1], sol.sol))
        hit = None
        for k, i in enumerate(free):
            if len(sol.t_events[k]):
                hit = (i, float(sol.t_events[k][0]), sol.y_events[k][0])
                break
        if hit is None:
            break
        i, t, y = hit
        touch[i] = t
        m.anchor[i] = m.forces(t, y)[3][i, :2]
    tt = np.arange(t0, t1, 1e-4)
    Fc_pen, Fc_max, Fp_all, Ft_all = [], [], [], []
    for tk in tt:
        sol = next(s for a, b, s in segs if a <= tk <= b)
        anc = np.where((np.array(touch) <= tk)[:, None], m.anchor, np.nan)
        _, _, _, _, Fc, Fp, Ft, pen_c, _ = m.forces(tk, sol(tk), anc)
        Fc_pen.append(pen_c.max())
        Fc_max.append(Fc.max())
        Fp_all.append(Fp)
        Ft_all.append(np.hypot(Ft[:, 0], Ft[:, 1]))
    Fc_pen, Fc_max, Fp_all, Ft_all = map(np.array, (Fc_pen, Fc_max, Fp_all, Ft_all))

    def first_down(a):
        k = np.where((a[1:] <= 0) & (a[:-1] > 0))[0]
        return float(tt[k[0] + 1]) if len(k) else math.nan

    with np.errstate(divide="ignore", invalid="ignore"):
        use = np.where(Fp_all > 0, Ft_all / (MU * Fp_all), 0.0)
    fric = []
    for i in range(4):
        idx = np.where(use[:, i] > 1.0)[0]
        if len(idx):
            k = idx[np.argmax(use[idx, i])]
            fric.append({"first_s": float(tt[idx[0]]), "last_s": float(tt[idx[-1]]), "duration_s": len(idx) * 1e-4,
                         "max_use": float(use[k, i]), "at_s": float(tt[k]), "N_at_max_N": float(Fp_all[k, i]),
                         "Ft_at_max_N": float(Ft_all[k, i])})
        else:
            fric.append({"max_use": float(use[:, i].max())})
    return {"settled_pitch_deg": pitch0, "touch_s": touch,
            "crawler_off_geometric_s": first_down(Fc_pen), "crawler_off_force_zero_s": first_down(Fc_max),
            "crawler_recontacts": int(len(np.where((Fc_pen[1:] > 0) & (Fc_pen[:-1] <= 0))[0])),
            "peak_pad_N": Fp_all.max(axis=0).tolist(), "peak_pad_t_s": tt[Fp_all.argmax(axis=0)].tolist(),
            "peak_cylinder_N": (Fp_all.max(axis=0) - ROD_W).tolist(),
            # instantaneous value at the window end t1, not a judged quantity: after the crawler lift-off it
            # follows the phase of the about 3 Hz pitch-surge mode (zeta 0.014, tau about 3.8 s), so it moves with t1
            "bushing_force_at_t1_N": Ft_all[-1].tolist(), "bushing_force_at_t1_note": BUSHING_AT_T1_NOTE,
            "bushing_force_max_N": Ft_all.max(axis=0).tolist(),
            "friction_use (|Ft| / mu N), no return mapping": fric, "window_s": [t0, t1]}


def part_d():
    out = {}
    for name, sc in (("x1", 1.0), ("x3", X3)):
        for b in (False, True):
            out[f"{name}_{'bushing' if b else 'free'}"] = run6(sc, b)
    ch = {}
    for case, key in (("v4_D_w1e-04", "x1_bushing"), ("v4_Dx3_w1e-04", "x3_bushing")):
        c = CHR["cases"][case]
        d = out[key]
        ch[case] = {"touch_eq_s": c["touch_eq_s"], "crawler_off_eq_s": c["crawler_off_eq_s"],
                    "peak_pad_force_N": c["peak_pad_force_N"],
                    "model_minus_chrono_touch_ms": ((np.array(d["touch_s"]) - np.array(c["touch_eq_s"])) * 1e3).tolist(),
                    "model_minus_chrono_crawler_off_ms (force zero)": (d["crawler_off_force_zero_s"] - c["crawler_off_eq_s"]) * 1e3,
                    "model_minus_chrono_peak_pad_N": (np.array(d["peak_pad_N"]) - np.array(c["peak_pad_force_N"])).tolist()}
    out["chrono_comparison"] = ch
    return out


out = {"meta": {"script": "04_scripts/01_dynamics/run_s3_lift_check.py", "doc": "dynamics_model.md 5.7 (rev. 17)",
                "gravity_world_m_s2": [0, 0, -G], "time_origin": "equivalent start = start command + ramp/2",
                "chrono_summary": "06_analysis/01_chrono/13_S3/verify_S3_L1.json generated " + CHR["generated"],
                "chrono_params_sha256": CHR["params_sha256"], "body_mass_6dof_kg": MASS,
                "crawler_dashpot_per_sphere_N_s_m": C_TOT / N_ROL, "pad_sphere_radius_m": R_PAD}}
out["A_V8a_crawler_energy"] = part_a()
out["B_V5_V6_exact_statics"] = part_b()
out["C_V4_quasi_static_pdelta"] = part_c()
out["D_V4_6dof_dynamic"] = part_d()
out["meta"]["runtime_s"] = time.perf_counter() - T0
dst = ROOT / "06_analysis/00_dynamics/s3_lift_check.json"
dst.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("C_V4_quasi_static_pdelta",)}, indent=1, default=float))
print(json.dumps(out["D_V4_6dof_dynamic"]["chrono_comparison"], indent=1, default=float))
print("runtime", out["meta"]["runtime_s"])
