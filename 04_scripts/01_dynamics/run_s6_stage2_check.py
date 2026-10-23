"""S6 stage-2 C2 closed-loop physics checks (dynamics_model.md 3.14, rev. 25).

Reads the cad-expert Chrono stage-2 batch (07_results/S6/stage2_20261021_213235, override batch
stage2_20261021_214443 for the three G2 roll 5.5 cases) and the verify summary
06_analysis/01_chrono/16_S6/verify_S6_L1_closed_loop.json. Independent of 03_src (numpy + dyn_model + YAML only).

  1  Rocking after READY: decaying-sine fit (f, zeta, amplitude at READY and at the end) of every leg's 1 ms cylinder
     force and of the body roll / pitch (20 ms record); linear 6-DoF L1 reference at the levelled state of each case
     (rigid body + rods at the final extension, four pad springs at the ball centres: k_n along the floor normal,
     k_t in the floor plane, YAML L1 values; dashpots c_n, c_t; preload geometric stiffness of the pad forces).
     Check of the reference against dynamics_model.md 3.4 (ball centre, top, flat).
     Filter residual model: apparent IMU tilt amplitude x |H(j w)| of the 2-stage Euler filter (tau 0.5 s, T 20 ms).
  2  Stroke headroom: maxima per leg from the 1 ms record vs 3.12 / 3.13 quasi-static predictions.
  3  Pad friction decomposition (G6 H4 off / on): rod lateral L, floor tangential T, utilisation, slip at READY / end.
  4  G4 pressure-only settlement: time history of the RR cylinder force and the twist around the minimum.
  5  Auger level trend of the minimum force on the nose-down floor: when / which leg / which phase.

Run:  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s6_stage2_check.py      (~1 min)
Output: 06_analysis/00_dynamics/s6_stage2_check.json
Conventions: body x forward, y left, z up; roll + left up, pitch + nose down (ZYX); quaternions wxyz (Chrono record);
cylinder force + = pushes the pad down; SI units, deg / kN / mm only in outputs.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import eig
from scipy.optimize import curve_fit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dyn_model as dm  # noqa: E402

ROOT = dm.PROJECT_ROOT
STROKE_M = 0.68  # stroke of the batch B1 runs (pre-REXOME35 YAML); set to the batch's actuator.stroke_m (0.70) for a new batch (rev. 30)
B1 = ROOT / "07_results/S6/stage2_20261021_213235"
B2 = ROOT / "07_results/S6/stage2_20261021_214443"
VER = ROOT / "06_analysis/01_chrono/16_S6/verify_S6_L1_closed_loop.json"
OUT = ROOT / "06_analysis/00_dynamics/s6_stage2_check.json"
LEGS = dm.LEG_NAMES
T_CTRL = 0.02
TAU_F = 0.5
SLOPES = {"flat": (0.0, 0.0), "fdown3.5": (0.0, 3.5), "fup3.5": (0.0, -3.5), "roll5.5": (5.5, 0.0),
          "roll3": (3.0, 0.0), "diag3": (2.1213203435596424, 2.1213203435596424)}


def case_dir(name):
    d2 = B2 / name
    return d2 if d2.is_dir() else B1 / name


def quat_rp(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


# --------------------------------------------------------------------------------------------- 1 identification
def fit_decay(t, y, f_guess=None):
    """y = c0 + c1 t + A exp(-s t) cos(2 pi f t + ph); returns dict or None."""
    t = t - t[0]
    yd = y - np.polyval(np.polyfit(t, y, 1), t)
    if f_guess is None:
        n = len(t); dt = float(np.median(np.diff(t)))
        F = np.abs(np.fft.rfft(yd * np.hanning(n))); fr = np.fft.rfftfreq(n, dt)
        m = (fr > 0.5) & (fr < 6.0)
        f_guess = float(fr[m][np.argmax(F[m])])
    A0 = float(np.max(np.abs(yd[: max(5, len(yd) // 8)])))

    def fn(tt, c0, c1, A, s, f, ph):
        return c0 + c1 * tt + A * np.exp(-s * tt) * np.cos(2 * np.pi * f * tt + ph)
    best = None
    for ph0 in (0.0, 1.57, 3.14, -1.57):
        try:
            p, _ = curve_fit(fn, t, y, p0=[float(np.mean(y)), 0.0, A0, 0.05, f_guess, ph0], maxfev=20000)
        except RuntimeError:
            continue
        r = float(np.sqrt(np.mean((fn(t, *p) - y) ** 2)))
        if best is None or r < best[1]:
            best = (p, r)
    if best is None:
        return None
    p, r = best
    A, s, f = abs(p[2]), p[3], abs(p[4])
    return {"f_Hz": float(f), "zeta": float(s / math.hypot(s, 2 * np.pi * f)), "sigma_1_s": float(s),
            "amp_start": float(A), "amp_end": float(A * math.exp(-s * t[-1])), "rms_resid": r,
            "rms_detrended": float(np.std(yd)), "window_s": float(t[-1])}


# --------------------------------------------------------------------------------------------- 1 linear reference
_P = {}


def P():
    if not _P:
        p = dm.load_params(); geo = dm.geometry_from_params(p)
        L1 = p["contact"]["rigid_floor"]["L1"]
        _P.update(p=p, geo=geo, kn=np.array([L1["kn_per_pad_N_m"][n] for n in LEGS], float),
                  kt=np.array([L1["kt_per_pad_N_m"][n] for n in LEGS], float),
                  cn=np.array([L1["cn_per_pad_N_s_m"][n] for n in LEGS], float),
                  ct=np.array([L1["ct_per_pad_N_s_m"][n] for n in LEGS], float),
                  hb=float(p["legs"]["FL"]["pad"]["swivel_center_above_pad_bottom_m"]))
    return _P


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


def l1_modes(level, ext, n_body=(0.0, 0.0, 1.0), P_body=None, geo_stiff=True):
    """Damped modes of the 6-DoF L1 model about the CoM. ext (4,) leg extensions [m]; n_body floor normal (body);
    P_body (4,3) pad forces on the body (default: static vertical share). Returns list of (f_d Hz, zeta)."""
    c = P(); p = c["p"]; geo = c["geo"]
    body = dm.body_with_rods(p, geo, level, np.asarray(ext, float))
    m, com, I = body.mass, body.com, body.inertia
    n = np.asarray(n_body, float); n = n / np.linalg.norm(n)
    Pn = np.outer(n, n); Pt = np.eye(3) - Pn
    K = np.zeros((6, 6)); Cm = np.zeros((6, 6)); Kg = np.zeros((3, 3))
    for i in range(4):
        b = np.array([geo.pad_xy[i, 0], geo.pad_xy[i, 1], geo.pad_z_retracted[i] + c["hb"] - ext[i]])
        d = b - com
        A = np.hstack([np.eye(3), -skew(d)])
        Ki = c["kn"][i] * Pn + c["kt"][i] * Pt
        Ci = c["cn"][i] * Pn + c["ct"][i] * Pt
        K += A.T @ Ki @ A; Cm += A.T @ Ci @ A
        if geo_stiff:
            Pi = P_body[i] if P_body is not None else None
            if Pi is None:
                Pi = np.array([0.0, 0.0, m * geo.g / 4])
            G = -(np.outer(d, Pi) - (d @ Pi) * np.eye(3))
            Kg += 0.5 * (G + G.T)
    K[3:, 3:] += Kg
    M = np.zeros((6, 6)); M[:3, :3] = m * np.eye(3); M[3:, 3:] = I
    Aa = np.block([[np.zeros((6, 6)), np.eye(6)], [-np.linalg.solve(M, K), -np.linalg.solve(M, Cm)]])
    lam = eig(Aa)[0]
    lam = lam[np.imag(lam) > 0]
    out = sorted(((float(abs(lv) / (2 * np.pi)), float(-np.real(lv) / abs(lv)), float(np.imag(lv) / (2 * np.pi)))
                  for lv in lam), key=lambda x: x[2])
    return [{"f_n_Hz": a, "zeta": z, "f_d_Hz": fd} for a, z, fd in out]


def filter_gain(f):
    """|H| of the 2-stage Euler low-pass y_k = y_{k-1} + (T/tau)(x_k - y_{k-1}) at frequency f (control rate)."""
    a = T_CTRL / TAU_F
    z = np.exp(1j * 2 * np.pi * f * T_CTRL)
    H1 = a / (1 - (1 - a) / z)
    return float(abs(H1) ** 2)


# --------------------------------------------------------------------------------------------- main
def main():
    ver = json.loads(VER.read_text(encoding="utf-8"))
    cases = ver["cases"]
    out = {"meta": {"script": "04_scripts/01_dynamics/run_s6_stage2_check.py", "batches": [str(B1), str(B2)]}}
    c = P(); geo = c["geo"]
    # reference check: flat, level, static loads, top / middle / bottom at e_op
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    out["ref_check_flat_e_op"] = {}
    for lv in dm.LEVELS:
        Fz = np.array([c["p"]["superstructure"]["auger_levels"][lv]["static_leg_loads_N"][nm] for nm in LEGS])
        Pb = [np.array([0, 0, F + geo.rod_mass[i] * geo.g]) for i, F in enumerate(Fz)]
        md = l1_modes(lv, np.full(4, e_op), P_body=Pb)
        out["ref_check_flat_e_op"][lv] = [(round(x["f_d_Hz"], 4), round(x["zeta"], 4)) for x in md]
    out["filter_gain"] = {f"{f:.2f}": filter_gain(f) for f in (1.0, 1.5, 1.8, 1.83, 2.3, 2.9, 3.0, 3.5)}
    # -------- per case
    R1, R2, R3 = {}, {}, {}
    for name, cs in cases.items():
        d = case_dir(name)
        if not (d / "pads.npz").exists():
            continue
        z = np.load(d / "pads.npz")
        rec = np.load(d / "record" / "record.npz")
        t = z["t"]; t0 = float(cs["times_s"]["t0"])
        tt = t - t0 if t[0] > 1.0 else t
        tr = rec["t"] - t0 if rec["t"][0] > 1.0 else rec["t"]
        ready = cs["times_s"].get("ready"); end = cs["times_s"]["end"]
        roll, pitch = quat_rp(rec["body_quat_wxyz"])
        Fc = z["F_cyl"]; sm = z["s_motor"]
        o = {"level": cs["level"], "floor": cs["floor"], "ready_s": ready, "end_s": end,
             "phases": cs["phases"], "group": cs["group"]}
        # ---- 1 rocking
        if ready is not None and end - ready > 4.0:
            w = (tt >= ready + 0.3) & (tt <= end)
            wr = (tr >= ready + 0.3) & (tr <= end)
            o["fit_F"] = {LEGS[i]: fit_decay(tt[w], Fc[w, i] / 1e3) for i in range(4)}
            fg = np.median([v["f_Hz"] for v in o["fit_F"].values() if v])
            o["fit_roll"] = fit_decay(tr[wr], roll[wr], fg)
            o["fit_pitch"] = fit_decay(tr[wr], pitch[wr], fg)
            # last-5 s window and ready+10 s spans
            w5 = tt >= end - 5.0
            o["F_ptp_last5_kN"] = (np.ptp(Fc[w5], axis=0) / 1e3).tolist()
            w10 = (tt >= ready) & (tt <= ready + 1.0)
            o["F_ptp_ready_first1s_kN"] = (np.ptp(Fc[w10], axis=0) / 1e3).tolist()
            # linear L1 reference at the final state
            j = np.flatnonzero(tt >= end - 1.0)
            ext = z["stroke_true"][j].mean(axis=0)
            Rw = z["R_world"][j].mean(axis=0)
            qend = rec["body_quat_wxyz"][-1]
            w_, x_, y_, z_ = qend
            Rb = np.array([[1 - 2 * (y_ * y_ + z_ * z_), 2 * (x_ * y_ - z_ * w_), 2 * (x_ * z_ + y_ * w_)],
                           [2 * (x_ * y_ + z_ * w_), 1 - 2 * (x_ * x_ + z_ * z_), 2 * (y_ * z_ - x_ * w_)],
                           [2 * (x_ * z_ - y_ * w_), 2 * (y_ * z_ + x_ * w_), 1 - 2 * (x_ * x_ + y_ * y_)]])
            nb = Rb.T @ z["n_world"][j].mean(axis=0)
            Pb = [Rb.T @ Rw[i] for i in range(4)]
            o["ext_end_m"] = ext.tolist(); o["n_body"] = nb.tolist(); o["P_body_kN"] = (np.array(Pb) / 1e3).tolist()
            o["l1_modes"] = l1_modes(cs["level"], ext, nb, Pb)[:3]
            o["l1_modes_flat_same_ext"] = l1_modes(cs["level"], ext, (0, 0, 1), Pb)[:3]
            o["imu_apparent_amp_last5_deg"] = cs.get("imu_apparent_amp_last5_deg")
            o["true_amp_last5_deg"] = cs.get("true_amp_last5_deg")
            o["filter_residual_last5_deg"] = cs.get("filter_residual_last5_deg")
            R1[name] = o
        # ---- 2 stroke
        R2[name] = {"level": cs["level"], "floor": cs["floor"], "h4": cs.get("h4", {}).get("enabled"),
                    "h4_outcome": cs.get("h4", {}).get("outcome"),
                    "s_motor_max_mm": (sm.max(axis=0) * 1e3).tolist(),
                    "margin_mm": ((STROKE_M - sm.max(axis=0)) * 1e3).tolist(),
                    "margin_end_mm": ((STROKE_M - sm[-1]) * 1e3).tolist(),
                    "t_of_max_s": [float(tt[k]) for k in sm.argmax(axis=0)],
                    "F_cyl_end_kN": (Fc[-1] / 1e3).tolist(),
                    "s_motor_at_ready_mm": None if ready is None else
                    (sm[np.searchsorted(tt, ready)] * 1e3).tolist(),
                    "stroke_true_max_mm": (z["stroke_true"].max(axis=0) * 1e3).tolist()}
        # crawler clearance at the end: box corners (C2 definition) and physical spheres, normal distance to the floor
        fr, fp = SLOPES.get(cs["floor"], (0.0, 0.0))
        nf = np.array([math.tan(math.radians(fp)), -math.tan(math.radians(fr)), 1.0]); nf /= np.linalg.norm(nf)
        q = rec["body_quat_wxyz"][-1]; pos = rec["body_pos"][-1]
        w_, x_, y_, z_ = q
        Rb = np.array([[1 - 2 * (y_ * y_ + z_ * z_), 2 * (x_ * y_ - z_ * w_), 2 * (x_ * z_ + y_ * w_)],
                       [2 * (x_ * y_ + z_ * w_), 1 - 2 * (x_ * x_ + z_ * z_), 2 * (y_ * z_ - x_ * w_)],
                       [2 * (x_ * z_ - y_ * w_), 2 * (y_ * z_ + x_ * w_), 1 - 2 * (x_ * x_ + y_ * y_)]])
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        box = np.array([[xx, yy, geo.crawler_bottom_z] for xx in (x0, x1) for yy in (y0, y1)])
        p0 = np.array([0.0, 0.0, geo.crawler_bottom_z])
        R2[name]["clr_box_end_mm"] = float(np.min(((pos + box @ Rb.T) - p0) @ nf) * 1e3)
        R2[name]["body_origin_end_m"] = pos.tolist()
        # ---- 3 friction decomposition at READY / end
        if cs["floor"] in ("fdown3.5", "fup3.5"):
            def at(tq):
                return int(np.clip(np.searchsorted(tt, tq), 0, len(tt) - 1))
            row = {}
            for lab, tq in (("ready", ready), ("end", end - 1e-3)):
                if tq is None:
                    continue
                k = at(tq)
                row[lab] = {"L_kN": (z["L"][k] / 1e3).tolist(), "T_kN": (z["T"][k] / 1e3).tolist(),
                            "N_kN": (z["N"][k] / 1e3).tolist(), "util": z["utilisation"][k].tolist(),
                            "F_cyl_kN": (Fc[k] / 1e3).tolist(),
                            "slip_mm": (np.linalg.norm(z["slip_total"][k], axis=1) * 1e3).tolist(),
                            "sliding": z["sliding"][k].tolist(),
                            "L_minus_T_kN": ((z["L"][k] - z["T"][k]) / 1e3).tolist()}
            row["sliding_fraction_after_ready"] = (z["sliding"][tt >= (ready or end)].mean(axis=0)).tolist()
            # reduced-plant decomposition check: T_red = |L_floor-plane part| capped by mu F_ax (a.n); Chrono:
            # N along n, cap mu N on T. Recompute both from the record at READY
            k = at(ready if ready is not None else end - 1e-3)
            a = z["a_world"][k]; nn = z["n_world"][k]
            Rw = z["R_world"][k]
            Fax = Rw @ a
            Lvec = Rw - np.outer(Fax, a)
            Nn = Rw @ nn
            Tvec = Rw - np.outer(Nn, nn)
            mu = float(z["mu"])
            row["decomp_at_ready"] = {
                "chrono_util": (np.linalg.norm(Tvec, axis=1) / (mu * Nn)).tolist(),
                "reduced_util": (np.linalg.norm(Lvec, axis=1) / (mu * Fax * (a @ nn))).tolist(),
                "L_kN": (np.linalg.norm(Lvec, axis=1) / 1e3).tolist(), "T_kN": (np.linalg.norm(Tvec, axis=1) / 1e3).tolist(),
                "F_ax_kN": (Fax / 1e3).tolist(), "N_kN": (Nn / 1e3).tolist(), "a_dot_n": float(a @ nn)}
            R3[name] = row
    out["rocking"] = R1; out["stroke"] = R2; out["friction"] = R3
    # ---- 4 G4 settlement
    R4 = {}
    for name in ("G4_top_flat_settleRR_pressure", "G4_top_flat_settleRR_combined"):
        cs = cases[name]; d = case_dir(name)
        z = np.load(d / "pads.npz"); t = z["t"]; t0 = float(cs["times_s"]["t0"]); tt = t - t0 if t[0] > 1 else t
        Fc = z["F_cyl"]; st = ver["settlement_item6"][name]
        after = np.flatnonzero(tt >= st["settlement_start_s"])
        j = int(after[np.argmin(Fc[after].min(axis=1))])
        tw = np.array([0.476, -0.476, -0.523, 0.523])
        sel = (tt >= st["settlement_start_s"] - 1) & (tt <= st["re_ready_s"] + 2)
        sub = np.flatnonzero(sel)[::50]
        u_rr = np.gradient(z["s_motor"][:, 3], tt)
        wj = (tt >= tt[j] - 2.0) & (tt <= tt[j])
        R4[name] = {"settlement": st, "t_min_s": float(tt[j]), "F_min_kN": float(Fc[j].min() / 1e3),
                    "leg_min": LEGS[int(np.argmin(Fc[j]))], "F_min_RR_kN": float(Fc[j, 3] / 1e3),
                    "RR_motor_speed_2s_before_min_mm_s": [float(u_rr[wj].min() * 1e3), float(u_rr[wj].max() * 1e3)],
                    "F_at_min_kN": (Fc[j] / 1e3).tolist(), "twist_at_min_kN": float(tw @ Fc[j] / 1e3),
                    "series_t_s": tt[sub].round(3).tolist(), "series_F_kN": (Fc[sub] / 1e3).round(2).tolist(),
                    "series_twist_kN": (Fc[sub] @ tw / 1e3).round(2).tolist(),
                    "s_motor_RR_mm": (z["s_motor"][sub, 3] * 1e3).round(3).tolist(),
                    "stroke_true_RR_mm": (z["stroke_true"][sub, 3] * 1e3).round(3).tolist(),
                    "phases": cs["phases"]}
    out["settlement"] = R4
    # ---- 5 level trend nose-down: time / leg / phase of the minimum, and the minimum per phase
    R5 = {}
    for lv in ("top", "middle", "bottom"):
        for fl in ("fdown3.5", "fup3.5"):
            name = f"G2-R_{lv}_{fl}"; cs = cases[name]; d = case_dir(name)
            z = np.load(d / "pads.npz"); t = z["t"]; t0 = float(cs["times_s"]["t0"]); tt = t - t0 if t[0] > 1 else t
            Fc = z["F_cyl"]
            lift = cs["times_s"]["liftoff"]
            ph = cs["phases"] + [[cs["times_s"]["end"], "end"]]
            per = {}
            for (ta, na), (tb, _) in zip(ph[:-1], ph[1:], strict=True):
                w = (tt >= max(ta, lift)) & (tt < tb)
                if w.any():
                    k = np.argmin(Fc[w].min(axis=1))
                    per[f"{na}@{ta:.1f}"] = {"min_kN": float(Fc[w].min() / 1e3), "leg": LEGS[int(np.argmin(Fc[w][k]))],
                                             "t_s": float(tt[w][k])}
            R5[name] = {"min_cyl_kN": cs["min_cyl_after_liftoff_kN"], "leg": cs["min_cyl_leg"], "t_s": cs["min_cyl_t_s"],
                        "per_phase": per}
    out["level_trend"] = R5
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    # ---- print
    print("ref check flat e_op (f_d, zeta):", out["ref_check_flat_e_op"])
    print("filter gain:", {k: round(v, 4) for k, v in out["filter_gain"].items()})
    for k, o in R1.items():
        fF = [v for v in o["fit_F"].values() if v]
        fr = o["fit_roll"] or {}; fp = o["fit_pitch"] or {}
        print(f"{k:46s} F fit f {np.median([v['f_Hz'] for v in fF]):.3f} z {np.median([v['zeta'] for v in fF]):.4f}"
              f" A {max(v['amp_start'] for v in fF):6.2f}->{max(v['amp_end'] for v in fF):6.2f} kN"
              f" | roll f {fr.get('f_Hz', 0):.3f} z {fr.get('zeta', 0):.4f} a {fr.get('amp_start', 0):.4f}"
              f" | pitch f {fp.get('f_Hz', 0):.3f} z {fp.get('zeta', 0):.4f} a {fp.get('amp_start', 0):.4f}"
              f" | L1 {[(round(m['f_d_Hz'], 3), round(m['zeta'], 4)) for m in o['l1_modes']]}"
              f" flatn {[(round(m['f_d_Hz'], 3), round(m['zeta'], 4)) for m in o['l1_modes_flat_same_ext'][:2]]}"
              f" | res {o['filter_residual_last5_deg']:.4f} app {o['imu_apparent_amp_last5_deg']:.3f}"
              f" true {o['true_amp_last5_deg']:.4f} win {o['end_s'] - o['ready_s']:.1f}")
    for k, o in R2.items():
        print(f"{k:46s} h4 {o['h4']} {o['h4_outcome']} margin {np.round(o['margin_mm'], 1)} clr_box_end {o['clr_box_end_mm']:.1f} end {np.round(o['margin_end_mm'], 1)} tmax {np.round(o['t_of_max_s'], 1)} Fend {np.round(o['F_cyl_end_kN'], 1)}")
    for k, o in R3.items():
        r = o.get("ready", {}); e = o.get("end", {}); dc = o["decomp_at_ready"]
        print(f"{k:46s} ready L {np.round(r.get('L_kN', []), 1)} T {np.round(r.get('T_kN', []), 1)} "
              f"util {np.round(r.get('util', []), 3)} slip {np.round(e.get('slip_mm', []), 2)} "
              f"| chrono_util {np.round(dc['chrono_util'], 3)} red_util {np.round(dc['reduced_util'], 3)} "
              f"N {np.round(dc['N_kN'], 1)} Fax {np.round(dc['F_ax_kN'], 1)} slidefrac {np.round(o['sliding_fraction_after_ready'], 3)}")
    for k, o in R4.items():
        print(k, "leg", o["leg_min"], "uRR", np.round(o["RR_motor_speed_2s_before_min_mm_s"], 2), "tmin", round(o["t_min_s"], 3), "Fmin RR", round(o["F_min_RR_kN"], 2), "F", np.round(o["F_at_min_kN"], 1),
              "twist", round(o["twist_at_min_kN"], 1), o["settlement"])
    for k, o in R5.items():
        print(k, o["min_cyl_kN"], o["leg"], o["t_s"], {kk: (round(v["min_kN"], 1), v["leg"], round(v["t_s"], 1))
                                                        for kk, v in o["per_phase"].items()})


if __name__ == "__main__":
    main()
