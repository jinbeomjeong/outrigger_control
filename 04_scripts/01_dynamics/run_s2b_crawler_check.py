"""Independent checks for the S2b final judgement (dynamics_model.md 5.6, rev. 15).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s2b_crawler_check.py
Writes 06_analysis/00_dynamics/s2b_crawler_check.json (about 10 s).

Part A - crawler settle pose (independent of 03_src/outrigger_sim/scenarios/crawler_settle.py):
    one rigid body (superstructure level + 4 leg moving parts at e = 0) on the 24 crawler
    spheres of YAML contact.crawler.sphere_layout, flat floor z = ground.crawler_bottom_z_m,
    vertical one-sided springs kn * overlap at the floor point under each sphere centre
    (SMC Hooke, R8 kt = mu = 0). Horizontal position and yaw carry no force -> fixed at 0.
    Unknowns (z0, roll, pitch), R = Rz(0) Ry(pitch) Rx(roll). Variants: exact geometry
    (P-delta), small-angle linear without P-delta (the reference convention), and the
    small-angle linear model plus the geometric stiffness -sum F_i h_i (first-order P-delta).
Part B - crawler modes: 6-DoF linearisation about the exact pose by central finite
    differences of the exact force/moment (about the CoM), M = diag(m I, R0 I_body R0^T),
    zero-stiffness surge/sway/yaw kept in the model (they decouple to zero frequency).
    Variants: inertia in world axes at the tilted pose (what Chrono integrates) vs body axes
    (reference.json convention), geometric stiffness at the sphere centre vs at the floor.
    Damping c = gn * m_eff per active sphere (SMC Hooke rule, m_eff = superstructure body mass
    in series with the 1e9 kg floor).
Part C - V4 with the command ramp: copy of run_reference.dynamic_touch (vertical damped 3-DoF,
    pads + crawler, unilateral) with a leg schedule e(t) argument; reproduces the step-start
    reference first, then the 0.1 s acceleration ramp (start and stop), touch times, crawler
    off and the pad-force peaks through the stops.
Inputs: 02_params/rexome33.yaml, 06_analysis/00_dynamics/reference.json,
    06_analysis/01_chrono/verify_S2b_L1.json (Chrono values, read only). Units SI.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

T0 = time.perf_counter()
P = dm.load_params(ROOT / "02_params" / "rexome33.yaml")
REF = json.load(open(ROOT / "06_analysis/00_dynamics/reference.json", encoding="utf-8"))
CHR = json.load(open(ROOT / "06_analysis/01_chrono/verify_S2b_L1.json", encoding="utf-8"))
G = float(P["meta"]["gravity_m_s2"])
LEGS = dm.LEG_NAMES
ZF = float(P["ground"]["crawler_bottom_z_m"])
LAY = P["contact"]["crawler"]["sphere_layout"]
RAD = float(LAY["sphere_radius_m"])
KN_YAML = float(P["contact"]["crawler"]["kn_per_sphere_N_m"])
KN32 = float(np.float32(KN_YAML))
GN32 = float(np.float32(P["contact"]["crawler"]["gn_per_sphere_1_s"]))
FLOOR_MASS = float(P["contact"]["rigid_floor"]["ground_body_mass_kg"])


def spheres():
    """(n,3) sphere centres in body coordinates: rollers (gap 0) and end shoes (gapped)."""
    yc = float(LAY["track_centre_y_m"])
    pts = []
    for y in (yc, -yc):
        for x in LAY["roller_x_m"]:
            pts.append((x, y, ZF + RAD))
        for x, g in zip(LAY["end_shoe_x_m"], LAY["end_shoe_gap_m"]):
            pts.append((x, y, ZF + g + RAD))
    return np.array(pts, float)


C_B = spheres()


def composite(level):
    """Superstructure level + 4 moving parts at e = 0 (rigid): mass, CoM, inertia about CoM (body axes)."""
    L = P["superstructure"]["auger_levels"][level]
    parts = [(float(L["mass_kg"]), np.array(L["com_m"], float), np.array(L["inertia_kg_m2"], float))]
    for n in LEGS:
        mp = P["legs"][n]["moving_part"]
        parts.append((float(mp["mass_kg"]), np.array(mp["com_retracted_m"], float), np.array(mp["inertia_kg_m2"], float)))
    m = sum(a for a, _, _ in parts)
    c = sum(a * b for a, b, _ in parts) / m
    inertia = np.zeros((3, 3))
    for a, b, i in parts:
        d = b - c
        inertia += i + a * (d @ d * np.eye(3) - np.outer(d, d))
    return m, c, inertia, float(L["mass_kg"])


def rot(roll, pitch, yaw=0.0):
    cr, sr, cp, sp, cy, sy = map(lambda f: f, (np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)))
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def skew(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])


def expm_so3(w):
    th = np.linalg.norm(w)
    if th < 1e-300:
        return np.eye(3)
    k = skew(w / th)
    return np.eye(3) + math.sin(th) * k + (1 - math.cos(th)) * k @ k


# ------------------------------------------------------------------ Part A: static pose
def static_exact(level, kn):
    m, c, _, _ = composite(level)
    W = m * G

    def resid(s):
        z0, ro, pi = s
        R = rot(ro, pi)
        cw = np.array([0, 0, z0]) + C_B @ R.T
        pen = RAD - (cw[:, 2] - ZF)
        F = kn * np.maximum(pen, 0.0)
        g = np.array([0, 0, z0]) + R @ c
        mx = np.sum(F * (cw[:, 1] - g[1]))
        my = -np.sum(F * (cw[:, 0] - g[0]))
        return np.array([(F.sum() - W) / W, mx / W, my / W]), F, pen, cw, g

    s = fsolve(lambda s: resid(s)[0], [-W / (12 * kn), 0.0, 0.0], xtol=1e-15)
    r, F, pen, cw, g = resid(s)
    return dict(q=s, F=F, pen=pen, cw=cw, g=g, W=W, m=m, com=c, resid=float(np.abs(r).max()))


def static_linear(level, kn, geometric=False, F_geo=None, h_geo=None):
    """Small-angle linear statics about the zero pose (moment arms fixed). With geometric=True add the
    first-order P-delta term -sum F_i h_i on roll and pitch (F_i, h_i from a given pose)."""
    m, c, _, _ = composite(level)
    W = m * G
    xy = C_B[:, :2]
    gap = C_B[:, 2] - RAD - ZF
    A = np.column_stack([np.ones(len(xy)), xy[:, 1], -xy[:, 0]])
    w = np.array([W, W * c[1], -W * c[0]])
    act = gap <= 0
    for _ in range(20):
        K = A[act].T @ (kn * A[act])
        rhs = A[act].T @ (kn * -gap[act]) - w
        if geometric:
            Kg = np.zeros((3, 3))
            Kg[1, 1] = Kg[2, 2] = -float(np.sum(F_geo * h_geo))
            # the extra moment from the tilt is taken about the CoM; the linear system is written about the
            # origin, so the P-delta term enters as a rotational stiffness reduction (same to first order)
            K = K + Kg
        q = np.linalg.solve(K, rhs)
        comp = -gap - A @ q
        new = comp > 0
        if (new == act).all():
            break
        act = new
    F = kn * np.maximum(-gap - A @ q, 0.0)
    return dict(q=q, F=F, W=W)


# ------------------------------------------------------------------ Part B: modes
def modes(level, st, kn, inertia_world=True, geo_at="centre", damping=True):
    m, c, Ib, m_sup = composite(level)
    z0, ro, pi = st["q"]
    R0 = rot(ro, pi)
    o0 = np.array([0, 0, z0])
    g0 = o0 + R0 @ c

    def wrench(x):
        # x = (dG (3), small rotation vector (3)) about the CoM; returns force, moment about the displaced CoM
        R = expm_so3(x[3:]) @ R0
        g = g0 + x[:3]
        cw = g + (C_B - c) @ R.T
        pen = RAD - (cw[:, 2] - ZF)
        F = kn * np.maximum(pen, 0.0) * (st["F"] > 0)  # active set of the static pose
        if geo_at == "floor":  # reference.json convention: geometric lever down to the floor point
            arm = cw.copy()
            arm[:, 2] = ZF
        else:  # force acts on the sphere -> vertical line through the sphere centre (Chrono contact)
            arm = cw
        f = np.array([0, 0, F.sum() - m * G])
        mo = np.sum(np.cross(arm - g, np.column_stack([np.zeros_like(F), np.zeros_like(F), F])), axis=0)
        return np.concatenate([f, mo])

    h = np.array([1e-7] * 3 + [1e-8] * 3)
    K = np.zeros((6, 6))
    for j in range(6):
        dx = np.zeros(6)
        dx[j] = h[j]
        K[:, j] = -(wrench(dx) - wrench(-dx)) / (2 * h[j])
    asym = float(np.abs(K - K.T).max() / np.abs(K).max())
    K = 0.5 * (K + K.T)
    I = R0 @ Ib @ R0.T if inertia_world else Ib
    M = np.zeros((6, 6))
    M[:3, :3] = m * np.eye(3)
    M[3:, 3:] = I
    # dashpots: vertical velocity of each active contact = e_z . (v_G + w x r)
    C = np.zeros((6, 6))
    m_eff = m_sup * FLOOR_MASS / (m_sup + FLOOR_MASS)
    cs = GN32 * m_eff
    act = st["F"] > 0
    cw0 = g0 + (C_B - c) @ R0.T
    for i in np.flatnonzero(act):
        r_i = cw0[i] - g0
        a = np.concatenate([[0, 0, 1], np.cross(r_i, [0, 0, 1])])
        C += cs * np.outer(a, a)
    if not damping:
        C[:] = 0
    lam_u = np.linalg.eigvals(np.linalg.solve(M, K))
    fu = np.sort(np.sqrt(np.abs(lam_u.real))) / (2 * np.pi)
    fu = fu[fu > 0.05]
    A = np.block([[np.zeros((6, 6)), np.eye(6)], [-np.linalg.solve(M, K), -np.linalg.solve(M, C)]])
    lam = np.linalg.eigvals(A)
    lam = lam[(lam.imag > 2 * np.pi * 0.05)]
    lam = lam[np.argsort(np.abs(lam))]
    fn = np.abs(lam) / (2 * np.pi)
    fd = lam.imag / (2 * np.pi)
    zeta = -lam.real / np.abs(lam)
    return dict(f_undamped_Hz=fu.tolist(), f_n_abs_lambda_Hz=fn.tolist(), f_d_Hz=fd.tolist(), zeta=zeta.tolist(),
                K_rel_asym=asym, n_active=int(act.sum()), c_per_sphere_N_s_m=cs)


out = {"meta": {"script": "04_scripts/01_dynamics/run_s2b_crawler_check.py", "doc": "dynamics_model.md 5.6 (rev. 15)",
                "kn_per_sphere_float32_N_m": KN32, "kn_per_sphere_yaml_N_m": KN_YAML, "gn_per_sphere_float32_1_s": GN32,
                "gravity_world_m_s2": [0, 0, -G], "euler": "ZYX (yaw 0), roll about x, pitch about y, deg",
                "u_z": "origin height relative to the zero pose (crawler bottom plane on the floor, level), mm"}}
for level in ("top", "middle", "bottom"):
    ex = static_exact(level, KN32)
    ex_yaml = static_exact(level, KN_YAML)
    lin = static_linear(level, KN32)
    heights = ex["g"][2] - ex["cw"][:, 2]  # CoM above each sphere centre (exact pose)
    lin_g = static_linear(level, KN32, geometric=True, F_geo=ex["F"], h_geo=heights)
    ch = CHR["crawler"][level]["chrono_window"]
    deg = np.degrees
    row = {
        "exact_pdelta": {"u_z_mm": ex["q"][0] * 1e3, "roll_deg": deg(ex["q"][1]), "pitch_deg": deg(ex["q"][2]),
                         "active": int((ex["F"] > 0).sum()), "resid_rel_W": ex["resid"]},
        "exact_pdelta_kn_yaml_minus_float32": {"u_z_mm": (ex_yaml["q"][0] - ex["q"][0]) * 1e3,
                                                "pitch_deg": deg(ex_yaml["q"][2] - ex["q"][2])},
        "linear_no_pdelta": {"u_z_mm": lin["q"][0] * 1e3, "roll_deg": deg(lin["q"][1]), "pitch_deg": deg(lin["q"][2])},
        "linear_plus_geometric_stiffness": {"u_z_mm": lin_g["q"][0] * 1e3, "roll_deg": deg(lin_g["q"][1]),
                                            "pitch_deg": deg(lin_g["q"][2])},
        "sum_F_h_N_m": float(np.sum(ex["F"] * heights)),
        "W_N": ex["W"],
        "chrono_window": ch,
        "chrono_minus_exact": {"u_z_mm": ch["u_z_mm"] - ex["q"][0] * 1e3, "roll_deg": ch["roll_deg"] - deg(ex["q"][1]),
                               "pitch_deg": ch["pitch_deg"] - deg(ex["q"][2])},
        "exact_minus_linear": {"u_z_mm": (ex["q"][0] - lin["q"][0]) * 1e3, "pitch_deg": deg(ex["q"][2] - lin["q"][2]),
                               "pitch_rel": float(ex["q"][2] / lin["q"][2] - 1)},
        "linear_geometric_minus_exact": {"pitch_deg": deg(lin_g["q"][2] - ex["q"][2]), "u_z_mm": (lin_g["q"][0] - ex["q"][0]) * 1e3},
    }
    # pitch stiffness of the springs about the y axis through the CoM (linear) and the P-delta ratio
    act = ex["F"] > 0
    xs = ex["cw"][act, 0] - ex["g"][0]
    k_pitch = float(KN32 * np.sum(xs ** 2) - KN32 * np.sum(xs) ** 2 / act.sum())  # heave condensed
    row["k_pitch_springs_heave_condensed_N_m_rad"] = k_pitch
    row["pdelta_ratio_sum_Fh_over_k_pitch"] = row["sum_F_h_N_m"] / k_pitch
    row["pdelta_amplification_predicted"] = 1 / (1 - row["pdelta_ratio_sum_Fh_over_k_pitch"])
    # sphere forces vs Chrono (reference order: left rollers, right rollers, left end shoes, right end shoes)
    if level == "top":
        idx = list(range(0, 6)) + list(range(12, 18)) + list(range(6, 12)) + list(range(18, 24))
        Fch = np.array(CHR["crawler"]["top"]["reference"]["sphere_force_chrono_ref_order_N"])
        row["chrono_minus_exact_sphere_force_max_abs_N"] = float(np.abs(Fch - ex["F"][idx]).max())
        Fref = np.array(CHR["crawler"]["top"]["reference"]["sphere_force_ref_N"])
        row["reference_minus_linear_sphere_force_max_abs_N"] = float(np.abs(Fref - lin["F"][idx]).max())
    # modes
    mo = {
        "world_inertia_geo_centre (Chrono model)": modes(level, ex, KN32, True, "centre"),
        "body_inertia_geo_floor (reference.json convention)": modes(level, ex, KN32, False, "floor"),
        "world_inertia_geo_floor": modes(level, ex, KN32, True, "floor"),
        "body_inertia_geo_centre": modes(level, ex, KN32, False, "centre"),
    }
    chm = CHR["crawler"][level]["modes_chrono"]
    mo["chrono_fit"] = {c["mode"]: {"f_d_Hz": c["f_damped_Hz"], "f_n_Hz": c["f_undamped_Hz"], "zeta": c["zeta"],
                                    "residual_rms_rel": c["residual_rms_rel"]} for c in chm}
    row["modes"] = mo
    out[level] = row

ref_modes = REF["lift_V4_compliant_crawler"]["crawler_on_floor_modes (layout D, legs at 0)"]
out["reference_crawler_modes_top"] = ref_modes

# ------------------------------------------------------------------ Part C: V4 schedule with the command ramp
geo = dm.geometry_from_params(P)
v = geo.v_max
touch = geo.touch_extension if hasattr(geo, "touch_extension") else None
L1y = P["contact"]["rigid_floor"]["L1"]
e_op = np.array([float(L1y["derivation"]["operating_extension_m"][n]) for n in LEGS])
k_pad = np.array([float(L1y["kn_per_pad_N_m"][n]) for n in LEGS])
c_pad = np.array(REF["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["c_pad_N_s_m"], float)
touch = np.asarray(geo.touch_extension, float)  # run_reference: e_op = touch + crawler_clearance
if np.abs(touch + float(P["simulation"]["crawler_clearance_m"]) - e_op).max() > 1e-6:
    raise RuntimeError(f"e_op {e_op} != touch {touch} + clearance")
bw = dm.body_with_rods(P, geo, "top", e_op)
c_tot = dm.crawler_damping_total(float(P["contact"]["crawler"]["kn_total_N_m"]), bw.mass)
xy_cr, k_cr, _ = dm.crawler_points(P)
gap_cr = dm.crawler_gaps(P)
n_rol = int((gap_cr <= 0).sum())
c_cr = np.full(len(xy_cr), c_tot / n_rol)
RAMP = 0.1  # ASSUMPTION mirrored from chrono/actuators.ACCEL_RAMP_S (user decision 2026-10-20)


def sched_step(t):
    e = np.minimum(v * t, e_op)
    ed = np.where(v * t < e_op, v, 0.0)
    return e, ed


def sched_ramp(t, T=RAMP):
    """Accelerate 0 -> v in T, brake v -> 0 in T starting at t_b = e_op / v (ends exactly at e_op)."""
    tb = e_op / v
    e = np.empty(4)
    ed = np.empty(4)
    for i in range(4):
        if t < T:
            e[i], ed[i] = v * t * t / (2 * T), v * t / T
        elif t < tb[i]:
            e[i], ed[i] = v * (t - T / 2), v
        elif t < tb[i] + T:
            s = t - tb[i]
            e[i], ed[i] = v * (tb[i] - T / 2) + v * s - v * s * s / (2 * T), v * (1 - s / T)
        else:
            e[i], ed[i] = e_op[i], 0.0
    return e, ed


def run3(sched, t_from, t_to, max_step=1e-3):
    b0 = dm.body_with_rods(P, geo, "top", np.zeros(4))
    W, cg = b0.mass * G, b0.com[:2]
    a = np.array([1.0, cg[1], -cg[0]])
    M = b0.mass * np.outer(a, a)
    M[1:, 1:] += b0.inertia[:2, :2]
    xy_all = np.vstack([geo.pad_xy, xy_cr])
    A = dm.support_matrix(xy_all)
    k = np.concatenate([k_pad, k_cr])
    cd = np.concatenate([c_pad, c_cr])
    w = np.array([W, W * cg[1], -W * cg[0]])
    n_cr = len(xy_cr)

    def comp(t, y):
        e, ed = sched(t)
        c = np.concatenate([e - touch, -gap_cr]) - A @ y[:3]
        cdot = np.concatenate([ed, np.zeros(n_cr)]) - A @ y[3:]
        return c, cdot

    def force(t, y):
        c, cdot = comp(t, y)
        return np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)

    def rhs(t, y):
        return np.concatenate([y[3:], np.linalg.solve(M, A.T @ force(t, y) - w)])

    evs = [(lambda t, y, i=i: comp(t, y)[0][i]) for i in range(4)] + [lambda t, y: comp(t, y)[0][4:].max()]
    _, q0, _ = dm.static_unilateral(xy_cr, k_cr, -gap_cr, W, cg)
    y0 = np.concatenate([q0, np.zeros(3)])
    sol = solve_ivp(rhs, (t_from, t_to), y0, method="DOP853", rtol=1e-9, atol=1e-12, max_step=max_step,
                    events=evs, dense_output=True)
    touch_s = []
    for i in range(4):
        up = [t for t, y in zip(sol.t_events[i], sol.y_events[i]) if comp(t, y)[1][i] > 0]
        touch_s.append(up[0] if up else math.nan)
    off = [t for t, y in zip(sol.t_events[4], sol.y_events[4]) if comp(t, y)[1][4:][np.argmax(comp(t, y)[0][4:])] < 0]
    tt = np.arange(t_from, t_to, 1e-3)
    Fp = np.array([force(t, sol.sol(t))[:4] for t in tt])
    q_end = sol.sol(t_to)
    late = tt >= float(e_op.min() / v) - 0.01  # from the first (rear) stop on
    v1 = np.array(REF["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"]["top"]["contact_force_N"])
    return dict(touch_s=touch_s, crawler_off_s=off[0] if off else math.nan, peak_pad_N=Fp.max(axis=0).tolist(),
                peak_pad_after_first_stop_minus_V1_N=(Fp[late].max(axis=0) - v1).tolist(),
                t_peak_s=tt[Fp.argmax(axis=0)].tolist(), final_pad_N=Fp[-1].tolist(),
                final_att_deg=np.degrees(q_end[1:3]).tolist())


refD = REF["lift_V4_compliant_crawler"]["layouts"]["D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)"]["dynamic_events_s"]
t_from, t_to = 14.7, float(e_op.max() / v + RAMP + 3.0)
st = run3(sched_step, t_from, t_to)
rp = run3(sched_ramp, t_from, t_to)
rod_w = np.array([float(P["legs"][n]["moving_part"]["mass_kg"]) for n in LEGS]) * G
out["V4_ramp"] = {
    "model": "copy of run_reference.dynamic_touch (vertical damped 3-DoF, plain I_xy, pads L1 kn + YAML cn, crawler D), "
             "DOP853 rtol 1e-9 atol 1e-12 max_step 1 ms, window extended through the stops + 3 s",
    "ramp_s (ASSUMPTION, chrono/actuators.ACCEL_RAMP_S)": RAMP,
    "ramp_schedule": "accelerate 0 -> v_max in ramp_s from t = 0, brake from t_b = e_op / v_max for ramp_s (rest exactly at e_op)",
    "reference_touch_s": refD["touch_s (FL, FR, RL, RR)"], "reference_crawler_off_s": refD["crawler_fully_off_s"],
    "step": st, "ramp": rp,
    "step_minus_reference_touch_s": (np.array(st["touch_s"]) - np.array(refD["touch_s (FL, FR, RL, RR)"])).tolist(),
    "ramp_minus_step_touch_s": (np.array(rp["touch_s"]) - np.array(st["touch_s"])).tolist(),
    "ramp_minus_step_crawler_off_s": rp["crawler_off_s"] - st["crawler_off_s"],
    "peak_cylinder_force_N (pad - rod weight) step / ramp": [(np.array(st["peak_pad_N"]) - rod_w).tolist(),
                                                            (np.array(rp["peak_pad_N"]) - rod_w).tolist()],
}
out["meta"]["runtime_s"] = time.perf_counter() - T0
dst = ROOT / "06_analysis/00_dynamics/s2b_crawler_check.json"
json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
for lev in ("top", "middle", "bottom"):
    r = out[lev]
    print(lev, "exact", [round(r["exact_pdelta"][k], 6) for k in ("u_z_mm", "roll_deg", "pitch_deg")],
          "lin", [round(r["linear_no_pdelta"][k], 6) for k in ("u_z_mm", "roll_deg", "pitch_deg")],
          "lin+geo", [round(r["linear_plus_geometric_stiffness"][k], 6) for k in ("u_z_mm", "roll_deg", "pitch_deg")],
          "ch-ex", {k: f"{v:.2e}" for k, v in r["chrono_minus_exact"].items()},
          "ratio", round(r["pdelta_ratio_sum_Fh_over_k_pitch"], 5), "rel", round(r["exact_minus_linear"]["pitch_rel"], 5))
    for k, m in r["modes"].items():
        if k == "chrono_fit":
            print("   ", k, {a: (round(b["f_n_Hz"], 5), round(b["zeta"], 6)) for a, b in m.items()})
        else:
            print("   ", k, np.round(m["f_n_abs_lambda_Hz"], 5), np.round(m["zeta"], 6), "asym", f"{m['K_rel_asym']:.1e}")
print("top sphere F chrono-exact", out["top"]["chrono_minus_exact_sphere_force_max_abs_N"], "ref-lin", out["top"]["reference_minus_linear_sphere_force_max_abs_N"])
print(json.dumps({k: out["V4_ramp"][k] for k in ("step_minus_reference_touch_s", "ramp_minus_step_touch_s", "ramp_minus_step_crawler_off_s")}))
print("step", st)
print("ramp", rp)
print("runtime", out["meta"]["runtime_s"])
