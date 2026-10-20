"""Levelling controller candidate comparison on a reduced 6-DoF model (00_docs/04_control/control_candidates_comparison.md).

Reduced plant (L1 basis, read-only use of dyn_model.py and 02_params/rexome33.yaml)
  * Rigid body = superstructure (auger level) + 4 rod moving parts lumped at the operating extension
    (dyn_model.body_with_rods). Nonlinear 6-DoF, quaternion (w, x, y, z scalar first), body angular velocity.
  * Gravity g = -9.80665 z_hat (world). Rigid planar floor z = sx x + sy y, sx = -tan(pitch_g), sy = tan(roll_g)
    (same sign convention as run_reference.levelled_extension: a machine resting on the floor gets body
    roll = roll_g, pitch = pitch_g; pitch > 0 nose down, roll > 0 left side up).
  * Leg i (axis = body -z): commanded oil volume -> reference stroke s_ref (speed |u| <= v_max, 0..0.68 m,
    210 bar force saturation checked every physics step). Oil spring k_oil(e_op; beta) in parallel with a Coulomb
    seal-friction element |f| <= F_s, in series with rod+frame+concrete k_s (massless rod, quasi-static solve
    every step, as actuator_L2_feasibility.py section C). F_s = 0 reproduces the L1 lumped pad stiffness k_n.
    Pressure reading P = k_oil (s_ref - x) = (contact force - rod weight) - f (cylinder-force basis).
    Normal damping c_n (L1 value) on the total leg compression rate, ground-fixed tangential bushing k_t, c_t
    (L1 values) with circular Coulomb cap mu N (mu 0.5).
  * Crawler: 2 x 9 unilateral contact points (dyn_model.crawler_points), k total 1e8 N/m, heave zeta 0.05 (concrete),
    tangential stick bushing per point (ASSUMPTION k_t = k_n per point) with mu 0.5.
  * Symplectic (semi-implicit) Euler, dt 5e-4 s (stability margin: max omega dt ~ 0.08).
Sensors: IMU accelerometer tilt at an ASSUMED point, averaged over the 20 ms control period, bias + white noise,
  attitude low-pass in the controller (order 1 or 2, each stage first-order tau_f 0.5 s); pressure (cylinder force)
  noise sigma 0.3 kN; stroke x noise sigma 0.1 mm. Controllers run every 20 ms (zero-order hold of the 4 leg speed
  commands).

Defaults follow the user decisions of 2026-10-20 (CLAUDE.md, 00_docs/05_sensors/imu_cabin_and_accuracy_review.md):
  accuracy target +/-0.2 deg, IMU on the upper frame under the cab at C1 (0.31, 0.88, 0.040) m
  (IMU_POINT_C1_BODY_M; before 2026-10-20 C1 decision the assumed cab-floor point (0.20, 0.88, 0.30) m),
  attitude filter 2nd order (2 x first-order tau 0.5 s). The original 2026-10-20 comparison
  (control_comparison.json, target 0.1 deg, IMU (0.45, 0, 0.30) m, 1st-order filter) is reproduced with --legacy.

Run (project root):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_control_comparison.py [options]
    --legacy              original assumptions; writes control_comparison.json / *_timeseries.png / *_matrix.png
    (default)             new assumptions; writes control_comparison_rev6.json and *_rev6 PNGs (full matrix)
    --quick               7 candidates, top, diag 3 deg only
    --regress             C2, top auger, flat / pitch+3 / roll+3 / diag3; new settings plus a legacy re-run compared
                          against the existing control_comparison.json (read only); writes
                          control_comparison_c2_regress_c1.json (IMU C1; the _rev6 file holds the earlier
                          assumed cab-floor point run), no figures
    --target-deg X        steady-state attitude accuracy target [deg] (default 0.2)
    --imu-lpf-order {1,2} attitude low-pass order (default 2)
    --imu-point X Y Z     IMU point in body axes [m]
    --out-stem NAME       override the output file stem in 06_analysis/00_dynamics/
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(os.environ.get("TEMP", "."), "numba_cache_outrigger"))

import numba as nb  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402

OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "control_comparison.json"

DT = 5e-4
T_CTRL = 0.02
N_SUB = int(round(T_CTRL / DT))
T_MAX = 150.0
T_HOLD = 10.0           # run on this long after the controller declares "done"
DEG = math.pi / 180

# ---------------------------------------------------------------------------- IMU mounting point (single source)
# Body frame (x fwd, y left, z up, origin = slewing-ring PCD axis x deck underside), metres.
# User decision 2026-10-20: candidate C1 = top face of the 15 mm cross plate in the BASE DECK left pontoon
# (structure side, below the cab isolation mounts). Source: 00_docs/00_cad/cad_origin_mass_imu.md section 4,
# 01_cad/01_parts/origin_mass_imu.json. Point = box bottom-face centre on the plate top face.
IMU_POINT_C1_BODY_M = (0.31, 0.88, 0.040)
# Previous ASSUMED point (cab floor centre, no mounting face exists there in CAD), kept for comparison only.
IMU_POINT_CAB_ASSUMED_BODY_M = (0.20, 0.88, 0.30)
# Alternative candidate C2 = inner face of the left pontoon C-channel web (vertical mount), same source.
IMU_POINT_C2_BODY_M = (0.17, 1.296, 0.12)

# ---------------------------------------------------------------------------- ASSUMPTIONS (this study)
CA = {
    # user decision 2026-10-20: IMU at C1 on the upper frame under the cab (see IMU_POINT_C1_BODY_M)
    "imu_point_body_m": list(IMU_POINT_C1_BODY_M),
    "imu_lpf_tau_s": 0.5,                         # per first-order stage
    "imu_lpf_order": 2,                           # user decision 2026-10-20: 2 x first-order tau 0.5 s (legacy: 1)
    "accuracy_target_deg": 0.2,                   # user decision 2026-10-20: +/-0.2 deg (legacy: 0.1)
    "imu_nominal": {"bias_mg": [0.5, -0.5], "noise_ug_rtHz": 100.0},
    "imu_worst": {"bias_mg": [1.7, 1.7], "noise_ug_rtHz": 150.0},
    "pressure_noise_N": 300.0,
    "stroke_noise_m": 1e-4,
    "crawler_kt_per_point_equals_kn": True,
    "P_touch_N": 1.5 * 9452.55,                   # touchdown detection: pressure >= 1.5 F_min (pad preload)
    "P_reground_N": 1.5 * 9452.55,                # C3/C7/C8 re-grounding / minimum-pressure switch
    "clearance_target_m": 0.05,                   # crawler clearance after levelling (00_docs/01_dynamics/dynamics_model.md 1.3)
    "done_att_deg": 0.03, "relevel_att_deg": 0.07, "done_hold_s": 1.0,
    "Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "twist_deadband_N": 2000.0,
    "C6_passive_leg": "RR", "C6_force_target": "sum(P)/4", "Kf_1_s": 1.0,
    "C3_coarse_tol_deg": 0.15, "C3_fine_speed_frac": 0.25, "K_fine_1_s": 0.5,
    "C4_preview_s": 1.0, "C4_Fmin_margin_N": 3000.0, "C4_Fmax_N": 200e3,
    "Fs_band_N": 12e3,                            # combined judge: seal-friction band until a probe measures F_s
    "rod_weight_N": 1047.2,
    "done_filter_tau_s": 1.0,                     # second low-pass for completion / stage checks
    "trim_deadband_deg": 0.02,
    "probe_speed_frac": 0.25, "probe_depth_m": 2e-3, "probe_hold_s": 0.4,
    "settle_scenario": {"leg": "RR", "depth_m": 0.0115, "start_after_ready_s": 2.0, "ramp_s": 2.0},
    "seed": 12345,
}

# original assumptions of the 2026-10-20 comparison (00_docs/04_control/control_candidates_comparison.md, control_comparison.json)
LEGACY_CA = {"imu_point_body_m": [0.45, 0.0, 0.30], "imu_lpf_order": 1, "accuracy_target_deg": 0.1}


def target_deg():
    return float(CA["accuracy_target_deg"])


def ss_fail_label():
    """Failure label for the steady-state accuracy check, e.g. 'ss_err>0.2'."""
    return f"ss_err>{target_deg():g}"

# ---------------------------------------------------------------------------- numba physics core


@nb.njit(cache=True)
def _R(q):
    w, x, y, z = q[0], q[1], q[2], q[3]
    R = np.empty((3, 3))
    R[0, 0] = 1 - 2 * (y * y + z * z); R[0, 1] = 2 * (x * y - w * z); R[0, 2] = 2 * (x * z + w * y)
    R[1, 0] = 2 * (x * y + w * z); R[1, 1] = 1 - 2 * (x * x + z * z); R[1, 2] = 2 * (y * z - w * x)
    R[2, 0] = 2 * (x * z - w * y); R[2, 1] = 2 * (y * z + w * x); R[2, 2] = 1 - 2 * (x * x + y * y)
    return R


@nb.njit(cache=True)
def _cross(a, b):
    return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


@nb.njit(cache=True)
def physics(nsteps, dt, u_cmd, r, v, q, w, sref, x, f, panc, pflag, canc, cflag,
            m, Ib, Ibinv, pad_rel, cr_rel, imu_rel, nrm, g,
            ko, ks, cn, kt, ct, Wr, Fs, kcr, ccr, ktcr, ctcr, mu, smax, Fext, Fret, goff, acc):
    """Advance nsteps. acc[0:3] += specific force at the IMU (body axes); acc[3:7] += extend-saturation steps;
    acc[7:11] += stroke-limit steps; acc[11:15] = last contact force (pads); acc[15] = last crawler total normal force;
    acc[16:20] = max pressure seen; acc[20:24] = min pressure seen."""
    gv = np.array([0.0, 0.0, -g])
    for _ in range(nsteps):
        R = _R(q)
        ez = R[:, 2]
        a_n = nrm[0] * ez[0] + nrm[1] * ez[1] + nrm[2] * ez[2]
        ww = R @ w
        F = m * gv
        T = np.zeros(3)
        for i in range(4):
            # --- actuator: force saturation per step (uses current pressure), stroke limits
            P = ko[i] * (sref[i] - x[i])
            ui = u_cmd[i]
            if ui > 0 and P >= Fext:
                ui = 0.0
                acc[3 + i] += 1
            if ui < 0 and P <= -Fret:
                ui = 0.0
            s_new = sref[i] + ui * dt
            if s_new > smax:
                s_new = smax; ui = 0.0; acc[7 + i] += 1
            if s_new < 0.0:
                s_new = 0.0; ui = 0.0; acc[7 + i] += 1
            sref[i] = s_new
            # --- geometry: pad bottom at zero extension, gap along the leg axis
            d0 = R @ pad_rel[i]
            p0 = r + d0
            gax = (nrm[0] * p0[0] + nrm[1] * p0[1] + nrm[2] * p0[2] + goff[i]) / a_n   # goff: local floor sink [m]
            # --- rod position x with seal friction (massless rod, return mapping)
            Fel = ks[i] * max(x[i] - gax, 0.0)
            ftr = Fel - ko[i] * (sref[i] - x[i]) - Wr[i]
            if abs(ftr) <= Fs[i] and Fs[i] > 0:
                f[i] = ftr
            else:
                fs = Fs[i] * (1.0 if ftr > 0 else -1.0)
                rhs = ko[i] * sref[i] + Wr[i] + fs
                x1 = rhs / ko[i]
                if x1 <= gax:
                    x[i] = x1
                else:
                    x[i] = (rhs + ks[i] * gax) / (ks[i] + ko[i])
                f[i] = fs
            c = x[i] - gax
            Pn = ko[i] * (sref[i] - x[i])
            if Pn > acc[16 + i]:
                acc[16 + i] = Pn
            if Pn < acc[20 + i]:
                acc[20 + i] = Pn
            dp = d0 - x[i] * ez
            pp = r + dp
            vp = v + _cross(ww, dp)
            if c > 0:
                Fel = ks[i] * c
                vn = vp[0] * nrm[0] + vp[1] * nrm[1] + vp[2] * nrm[2]
                Fl = Fel + cn[i] * (ui - vn / a_n)
                if Fl < 0:
                    Fl = 0.0
                Fv = Fl * ez
                # tangential bushing
                if pflag[i] == 0:
                    panc[i, :] = pp
                    pflag[i] = 1
                dd = pp - panc[i]
                dn = dd[0] * nrm[0] + dd[1] * nrm[1] + dd[2] * nrm[2]
                dt_ = dd - dn * nrm
                vt = vp - vn * nrm
                Ft = -kt[i] * dt_
                Nn = Fl * a_n
                fe = math.sqrt(Ft[0] ** 2 + Ft[1] ** 2 + Ft[2] ** 2)
                if fe > mu * Nn:
                    sc = mu * Nn / fe if fe > 0 else 0.0
                    Ft = Ft * sc
                    panc[i, :] = pp + Ft / kt[i]
                else:
                    Ft = Ft - ct[i] * vt
                Fi = Fv + Ft
                acc[11 + i] = Fl
            else:
                pflag[i] = 0
                Fi = np.zeros(3)
                acc[11 + i] = 0.0
            F += Fi
            T += _cross(dp, Fi)
        Fc_tot = 0.0
        for j in range(cr_rel.shape[0]):
            dp = R @ cr_rel[j]
            pp = r + dp
            dn0 = pp[0] * nrm[0] + pp[1] * nrm[1] + pp[2] * nrm[2]
            if dn0 < 0:
                vp = v + _cross(ww, dp)
                vn = vp[0] * nrm[0] + vp[1] * nrm[1] + vp[2] * nrm[2]
                N = -kcr[j] * dn0 - ccr[j] * vn
                if N < 0:
                    N = 0.0
                if cflag[j] == 0:
                    canc[j, :] = pp
                    cflag[j] = 1
                dd = pp - canc[j]
                dn = dd[0] * nrm[0] + dd[1] * nrm[1] + dd[2] * nrm[2]
                dt_ = dd - dn * nrm
                vt = vp - vn * nrm
                Ft = -ktcr[j] * dt_
                fe = math.sqrt(Ft[0] ** 2 + Ft[1] ** 2 + Ft[2] ** 2)
                if fe > mu * N:
                    sc = mu * N / fe if fe > 0 else 0.0
                    Ft = Ft * sc
                    canc[j, :] = pp + Ft / ktcr[j]
                else:
                    Ft = Ft - ctcr[j] * vt
                Fj = N * nrm + Ft
                Fc_tot += N
                F += Fj
                T += _cross(dp, Fj)
            else:
                cflag[j] = 0
        acc[15] = Fc_tot
        # --- integrate (symplectic Euler)
        a_lin = F / m
        Tb = R.T @ T
        wd = Ibinv @ (Tb - _cross(w, Ib @ w))
        # IMU specific force (body axes), uses the accelerations of this step
        rho = imu_rel
        a_imu_b = R.T @ a_lin + _cross(wd, rho) + _cross(w, _cross(w, rho))
        fb = a_imu_b - R.T @ gv
        acc[0] += fb[0]; acc[1] += fb[1]; acc[2] += fb[2]
        v += dt * a_lin
        w += dt * wd
        r += dt * v
        qw, qx, qy, qz = q[0], q[1], q[2], q[3]
        p_, q_, r_ = w[0], w[1], w[2]
        q[0] += dt * 0.5 * (-qx * p_ - qy * q_ - qz * r_)
        q[1] += dt * 0.5 * (qw * p_ + qy * r_ - qz * q_)
        q[2] += dt * 0.5 * (qw * q_ + qz * p_ - qx * r_)
        q[3] += dt * 0.5 * (qw * r_ + qx * q_ - qy * p_)
        nq = math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2)
        q /= nq


# ---------------------------------------------------------------------------- plant wrapper


class Plant:
    def __init__(self, level="top", slope_roll_deg=0.0, slope_pitch_deg=0.0, beta=1.0e9, Fs=0.0,
                 soft_FL=False, dt=DT, init_ext=None):
        p = dm.load_params()
        geo = dm.geometry_from_params(p)
        self.geo = geo
        A_ = dm.ASSUMPTIONS
        self.e_op = geo.touch_extension + A_["crawler_clearance_m"]
        body = dm.body_with_rods(p, geo, level, self.e_op)
        self.body = body
        self.m = body.mass
        self.Ib = body.inertia.copy()
        self.Ibinv = np.linalg.inv(self.Ib)
        com = body.com
        self.pad_rel = np.column_stack([geo.pad_xy, geo.pad_z_retracted]) - com
        cxy, kcr, ccr = dm.crawler_points(p)
        kn_tot = float(p["contact"]["crawler"]["kn_total_N_m"])
        c_tot = dm.crawler_damping_total(kn_tot, self.m)
        self.cr_rel = np.column_stack([cxy, np.full(len(cxy), geo.crawler_bottom_z)]) - com
        nc = len(cxy)
        self.kcr = np.full(nc, kn_tot / nc); self.ccr = np.full(nc, c_tot / nc)
        self.ktcr = self.kcr.copy(); self.ctcr = self.ccr.copy()
        self.imu_rel = np.array(CA["imu_point_body_m"]) - com
        kc = dm.k_concrete_westergaard()["k_slab_N_m"]
        ks = float(dm.series(dm.k_rod(), A_["frame_bracket_stiffness_N_m"], kc))
        self.ko = np.asarray(dm.k_oil(self.e_op, beta=beta), float)
        self.ks = np.full(4, ks)
        if soft_FL:   # ASSUMPTION scenario: FL ground/pad half as stiff (k_n,FL x 0.5)
            kv = 1 / (1 / self.ko[0] + 1 / ks)
            self.ks[0] = 1 / (2 / kv - 1 / self.ko[0])
        L1 = p["contact"]["rigid_floor"]["L1"]
        self.cn = np.array([L1["cn_per_pad_N_s_m"][nm] for nm in dm.LEG_NAMES], float)
        self.kt = np.array([L1["kt_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)
        self.ct = np.array([L1["ct_per_pad_N_s_m"][nm] for nm in dm.LEG_NAMES], float)
        self.kn_L1 = np.array([L1["kn_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)
        self.Wr = geo.rod_mass * geo.g
        self.Fs = np.full(4, float(Fs))
        self.mu = float(p["contact"]["rigid_floor"]["friction"])
        self.g = geo.g
        self.Ap = dm.piston_area()
        self.Fext = 210e5 * self.Ap
        self.Fret = 210e5 * 8.84e-4
        self.dt = dt
        # floor
        sx = -math.tan(math.radians(slope_pitch_deg)); sy = math.tan(math.radians(slope_roll_deg))
        n = np.array([-sx, -sy, 1.0]); self.nrm = n / np.linalg.norm(n)
        # initial attitude: R e_z = n, yaw 0 (ZYX): sin(phi) = -n_y, tan(theta) = n_x / n_z
        phi = math.asin(-self.nrm[1]); th = math.atan2(self.nrm[0], self.nrm[2])
        qr = np.array([math.cos(phi / 2), math.sin(phi / 2), 0, 0]); qp = np.array([math.cos(th / 2), 0, math.sin(th / 2), 0])
        self.q = _qmul(qp, qr)
        R = _R(self.q)
        sink = self.m * self.g / kn_tot
        if init_ext is None:
            O = self.nrm * (-geo.crawler_bottom_z - sink)        # body origin, crawler bottom just below the floor
            self.sref = np.zeros(4)
        else:  # start on the pads at extensions init_ext (flat floor tests)
            O = np.array([0, 0, -(geo.pad_z_retracted[0] - init_ext[0])])
            self.sref = np.array(init_ext, float)
        self.r = O + R @ com
        self.v = np.zeros(3); self.w = np.zeros(3)
        self.x = self.sref.copy(); self.f = np.zeros(4)
        self.panc = np.zeros((4, 3)); self.pflag = np.zeros(4, np.int64)
        self.canc = np.zeros((nc, 3)); self.cflag = np.zeros(nc, np.int64)
        self.acc = np.zeros(24)
        self.goff = np.zeros(4)
        self.t = 0.0

    def step(self, u, nsteps):
        a = self.acc
        a[:11] = 0.0
        a[16:20] = -1e12; a[20:24] = 1e12
        physics(nsteps, self.dt, np.asarray(u, float), self.r, self.v, self.q, self.w, self.sref, self.x, self.f,
                self.panc, self.pflag, self.canc, self.cflag, self.m, self.Ib, self.Ibinv, self.pad_rel, self.cr_rel,
                self.imu_rel, self.nrm, self.g, self.ko, self.ks, self.cn, self.kt, self.ct, self.Wr, self.Fs,
                self.kcr, self.ccr, self.ktcr, self.ctcr, self.mu, self.geo.stroke, self.Fext, self.Fret, self.goff, a)
        self.t += nsteps * self.dt
        return a

    # true quantities
    def attitude(self):
        R = _R(self.q)
        return math.atan2(R[2, 1], R[2, 2]), -math.asin(max(-1.0, min(1.0, R[2, 0])))

    def pressure(self):
        return self.ko * (self.sref - self.x)

    def true_cyl_force(self):
        return self.acc[11:15] - self.Wr       # contact force (incl. damping) - rod weight

    def crawler_clearance(self):
        R = _R(self.q)
        com = self.body.com
        (x0, x1), (y0, y1) = self.geo.crawler_xy_box
        cs = np.array([[x0, y0, 0], [x0, y1, 0], [x1, y0, 0], [x1, y1, 0]], float)
        cs[:, 2] = self.geo.crawler_bottom_z
        d = [(self.r + R @ (c - com)) @ self.nrm for c in cs]
        return min(d)


def _qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


# ---------------------------------------------------------------------------- sensors


class Sensors:
    def __init__(self, imu, rng, g):
        self.bias = np.array(imu["bias_mg"] + [0.0]) * 1e-3 * g
        self.sig = imu["noise_ug_rtHz"] * 1e-6 * g * math.sqrt(1 / (2 * T_CTRL))
        self.rng = rng
        self.g = g

    def read(self, plant, acc, nsub):
        fb = acc[0:3] / nsub + self.bias + self.rng.normal(0, self.sig, 3)
        phi = math.atan2(fb[1], fb[2]); th = math.atan2(-fb[0], math.hypot(fb[1], fb[2]))
        P = plant.pressure() + self.rng.normal(0, CA["pressure_noise_N"], 4)
        x = plant.x + self.rng.normal(0, CA["stroke_noise_m"], 4)
        return {"phi": phi, "theta": th, "P": P, "x": x, "sat_ext": acc[3:7] > 0}


# ---------------------------------------------------------------------------- controllers


class Ctx:
    def __init__(self, geo, W_nom, k_nom):
        self.xy = geo.pad_xy
        self.zp = geo.pad_z_retracted
        self.A = dm.support_matrix(geo.pad_xy)
        self.Ap = np.linalg.pinv(self.A)
        self.n = dm.twist_vector(geo.pad_xy)
        self.vmax = geo.v_max
        self.smax = geo.stroke
        self.F_min = 0.1 * W_nom / 4
        self.k_nom = k_nom                    # nominal L1 pad stiffness (beta 1.0 GPa) used by the controllers
        self.S_nom = dm.load_sensitivity(np.full(4, k_nom), geo.pad_xy)
        (x0, x1), (y0, y1) = geo.crawler_xy_box
        self.corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
        self.zcb = geo.crawler_bottom_z
        self.M = np.column_stack([np.ones(4), self.xy])

    def clearance_est(self, x):
        z = self.zp - x
        coef = np.linalg.lstsq(self.M, z, rcond=None)[0]
        return float(np.min(self.zcb - (coef[0] + self.corners @ coef[1:])))

    def heights(self, phi, th):
        return phi * self.xy[:, 1] - th * self.xy[:, 0]


def _sat_scale(u, vmax):
    m = np.max(np.abs(u))
    return u * (vmax / m) if m > vmax else u


def _stroke_clip(u, x, smax):
    u = u.copy()
    u[(x >= smax - 1e-4) & (u > 0)] = 0.0
    u[(x <= 1e-4) & (u < 0)] = 0.0
    return u


class Controller:
    """Common sequence: touchdown search -> candidate-specific levelling (level()) -> done -> [combined contact judge:
    probe every leg] -> ready -> monitoring (re-level on attitude or low-load triggers).

    contact = "pressure": every load decision uses the raw pressure reading P (cylinder-force basis).
    contact = "combined" (simple form of the physics-based judge, user decision 2026-10-20):
      * touchdown: load above the free-air reading recorded while extending in air (removes the seal-friction offset),
      * load decisions use the lower bound P - F_band (F_band = 12 kN design band until a probe measures F_s),
      * after levelling, a probe on every leg (+2 mm, hold, -2 mm, hold): incremental stiffness dP/dx says
        grounded / floating, the extend/retract midpoint corrected by S_ii dx gives the true load and F_s,
      * a leg judged floating or below F_min + 5 kN is extended until the probe confirms, then the attitude is
        re-levelled and all legs are probed again (max 3 rounds).
    """
    name = "base"

    def __init__(self, ctx, contact="pressure"):
        self.c = ctx
        self.contact = contact
        self.phase = "touch"
        self.touched = np.zeros(4, bool)
        self.phi_f = None; self.th_f = None; self.phi_s = None; self.th_s = None
        self.phi_1 = None; self.th_1 = None      # first stage of the 2nd-order attitude low-pass
        self.done = False; self.t_done = None; self.ok_since = None
        self.ready = False; self.t_ready = None; self.t_ready_first = None
        self.lifted = False      # latched when the stroke-based crawler clearance estimate exceeds 10 mm
        self.events = []
        self.t = 0.0
        self.fs_band = CA["Fs_band_N"]
        self.air = []
        self.P_air = None
        self.probe = None; self.probe_rounds = 0; self.probe_time = 0.0; self.probe_log = []
        self.rg = None

    # ------------------------------------------------------------------ helpers
    def filt(self, m):
        """Attitude filters (forward-Euler discrete first-order stages at T_CTRL).
        phi_f/th_f: control signal = imu_lpf_order cascaded stages of tau imu_lpf_tau_s.
        phi_s/th_s: completion / stage-check signal = one more stage of tau done_filter_tau_s on phi_f."""
        a = T_CTRL / CA["imu_lpf_tau_s"]; b = T_CTRL / CA["done_filter_tau_s"]
        order = int(CA["imu_lpf_order"])
        if order not in (1, 2):
            raise ValueError("imu_lpf_order must be 1 or 2")
        if self.phi_f is None:
            self.phi_f, self.th_f = m["phi"], m["theta"]
            self.phi_1, self.th_1 = m["phi"], m["theta"]
            self.phi_s, self.th_s = m["phi"], m["theta"]
        else:
            if order == 2:
                self.phi_1 += a * (m["phi"] - self.phi_1); self.th_1 += a * (m["theta"] - self.th_1)
                self.phi_f += a * (self.phi_1 - self.phi_f); self.th_f += a * (self.th_1 - self.th_f)
            else:
                self.phi_f += a * (m["phi"] - self.phi_f); self.th_f += a * (m["theta"] - self.th_f)
            self.phi_s += b * (self.phi_f - self.phi_s); self.th_s += b * (self.th_f - self.th_s)

    def load_est(self, m):
        """Lower bound (combined) or raw reading (pressure) of the cylinder force [N]."""
        return m["P"] if self.contact == "pressure" else m["P"] - self.fs_band

    def ev(self, s):
        if len(self.events) < 12:
            self.events.append((round(self.t, 2), s))

    # ------------------------------------------------------------------ main
    def update(self, m, t):
        self.t = t
        self.filt(m)
        c = self.c
        if self.phase == "touch":
            if self.contact == "pressure":
                self.touched |= m["P"] >= CA["P_touch_N"]
            else:
                if t < 5.0:
                    self.air.append(m["P"].copy())
                    self.P_air = np.median(np.array(self.air), axis=0)
                # true cylinder force = P - P_air - W_rod (seal friction offset removed)
                self.touched |= (m["P"] - self.P_air - CA["rod_weight_N"]) >= CA["P_touch_N"]
            u = np.where(self.touched, 0.0, c.vmax)
            if self.touched.all():
                self.phase = "level"; self.t_touch = t
                self.on_touch(m)
            return u
        if self.done:
            low = self.lifted and self.ready and float(self.load_est(m).min()) < c.F_min + 3e3
            if max(abs(self.phi_s), abs(self.th_s)) > CA["relevel_att_deg"] * DEG or low:
                self.done = False; self.ready = False; self.ok_since = None; self.probe = None
                self.ev("relevel" + ("_lowload" if low else ""))
                self.on_relevel()
            else:
                if self.contact == "combined" and not self.ready:
                    return self.probe_step(m)
                if not self.ready:
                    self.ready = True; self.t_ready = t
                    if self.t_ready_first is None:
                        self.t_ready_first = t
                return np.zeros(4)
        if not self.lifted and c.clearance_est(m["x"]) > 0.01:
            self.lifted = True
        u = self.level(m)
        if c.clearance_est(m["x"]) < 0.02:   # crawler may still bear load: no retraction (avoids pad lift-off)
            u = _sat_scale(u + max(0.0, -float(u.min())), c.vmax)   # add pure heave (ones vector) instead of clipping
        # stroke-end fault: a leg at its end still asked to extend for > 2 s -> alarm, hold all legs (not levellable)
        at_end = (m["x"] >= c.smax - 1e-3) & (u > 1e-5)
        self.end_cnt = getattr(self, "end_cnt", 0) + 1 if at_end.any() else 0
        if self.end_cnt * T_CTRL > 2.0:
            if not getattr(self, "fault", False):
                self.ev("stroke_end_fault")
            self.fault = True
        if getattr(self, "fault", False):
            return np.zeros(4)
        return _stroke_clip(u, m["x"], c.smax)

    # ------------------------------------------------------------------ probe (combined judge)
    def probe_step(self, m):
        c = self.c
        vp = CA["probe_speed_frac"] * c.vmax; dl = CA["probe_depth_m"]; th = CA["probe_hold_s"]
        self.probe_time += T_CTRL
        if self.rg is not None:                        # re-grounding a leg after a failed probe
            i, xt = self.rg
            if m["x"][i] < xt:
                u = np.zeros(4); u[i] = vp
                return u
            self.rg = None
            self.on_reground(m)
            self.done = False; self.ok_since = None    # re-level the attitude, then probe again
            return np.zeros(4)
        if self.probe is None:
            self.probe = {"leg": 0, "st": "ext", "t0": self.t, "x0": m["x"].copy(), "P0": m["P"].copy(),
                          "res": [], "att0": (self.phi_f, self.th_f)}
            self.probe_rounds += 1
        pr = self.probe
        i = pr["leg"]
        u = np.zeros(4)
        dt_move = dl / vp
        tt = self.t - pr["t0"]
        if pr["st"] == "ext":
            if tt < dt_move:
                u[i] = vp
            elif tt < dt_move + th:
                pass
            else:
                pr["Pe"] = m["P"][i]; pr["xe"] = m["x"][i]; pr["st"] = "ret"; pr["t0"] = self.t
        elif pr["st"] == "ret":
            if tt < dt_move:
                u[i] = -vp
            elif tt < dt_move + th:
                pass
            else:
                Pr = m["P"][i]; xr = m["x"][i]
                Sii = c.S_nom[i, i]
                dxe = pr["xe"] - pr["x0"][i]
                kinc = (pr["Pe"] - pr["P0"][i]) / dxe if dxe > 2e-4 else float("nan")
                est = 0.5 * (pr["Pe"] + Pr) - 0.5 * Sii * (pr["xe"] - xr)
                fs = 0.5 * (pr["Pe"] - Pr - Sii * (pr["xe"] - xr))
                grounded = bool(dxe > 2e-4 and kinc > 0.3 * Sii)
                pr["res"].append({"leg": dm.LEG_NAMES[i], "load_est_kN": round(est / 1e3, 2),
                                  "Fs_est_kN": round(fs / 1e3, 2), "k_inc_N_m": round(kinc, -3) if kinc == kinc else None,
                                  "grounded": grounded})
                pr["leg"] += 1; pr["st"] = "ext"; pr["t0"] = self.t
                if pr["leg"] == 4:
                    self.probe_log.append({"t": round(self.t, 2), "res": pr["res"]})
                    fs_meas = max(r["Fs_est_kN"] for r in pr["res"]) * 1e3
                    self.fs_band = max(1e3, fs_meas + 1e3)
                    bad = [k for k, r in enumerate(pr["res"])
                           if (not r["grounded"]) or r["load_est_kN"] * 1e3 < c.F_min + 5e3]
                    self.probe = None
                    if bad and self.probe_rounds < 3:
                        k = bad[0]
                        need = c.F_min + 15e3 - pr["res"][k]["load_est_kN"] * 1e3
                        self.rg = (k, m["x"][k] + max(need, 5e3) / c.S_nom[k, k])
                        self.ev(f"probe_reground_{dm.LEG_NAMES[k]}")
                    else:
                        self.ready = True; self.t_ready = self.t
                        if self.t_ready_first is None:
                            self.t_ready_first = self.t
                        if bad:
                            self.ev("probe_unresolved")
        return u

    def check_done(self, cond):
        if cond:
            if self.ok_since is None:
                self.ok_since = self.t
            elif self.t - self.ok_since >= CA["done_hold_s"]:
                self.done = True
                if self.t_done is None:
                    self.t_done = self.t
        else:
            self.ok_since = None

    def att_small(self, lim=None):
        lim = CA["done_att_deg"] * DEG if lim is None else lim
        return abs(self.phi_s) < lim and abs(self.th_s) < lim

    def on_touch(self, m):
        pass

    def on_relevel(self):
        pass

    def on_reground(self, m):
        pass


class C1(Controller):
    """Kinematic decomposition + PI on roll/pitch, heave from the stroke-based clearance estimate, twist held at
    its touchdown value by the stroke sensors."""
    name = "C1"

    def on_touch(self, m):
        self.tau_ref = float(self.c.n @ m["x"])
        self.Iphi = 0.0; self.Ith = 0.0

    def on_reground(self, m):
        self.tau_ref = float(self.c.n @ m["x"])   # keep the re-grounded twist (otherwise the stroke twist hold undoes it)

    def outer(self, m):
        c = self.c
        e_phi, e_th = -self.phi_f, -self.th_f
        db = 0.01 * DEG
        if db < abs(e_phi) < 0.2 * DEG:   # conditional integration (anti-windup)
            self.Iphi = np.clip(self.Iphi + e_phi * T_CTRL, -0.02, 0.02)
        if db < abs(e_th) < 0.2 * DEG:
            self.Ith = np.clip(self.Ith + e_th * T_CTRL, -0.02, 0.02)
        phid = CA["Kp_att_1_s"] * e_phi + CA["Ki_att_1_s2"] * self.Iphi
        thd = CA["Kp_att_1_s"] * e_th + CA["Ki_att_1_s2"] * self.Ith
        clr = c.clearance_est(m["x"])
        zd = float(np.clip(CA["Kz_1_s"] * (CA["clearance_target_m"] - clr), -c.vmax, c.vmax))
        return zd, phid, thd, clr

    def twist_rate(self, m):
        return CA["Ktw_1_s"] * (self.tau_ref - float(self.c.n @ m["x"]))

    def extra_done(self, m):
        return True

    def level(self, m):
        c = self.c
        zd, phid, thd, clr = self.outer(m)
        u = c.A @ np.array([zd, phid, thd]) + c.n * self.twist_rate(m)
        u = _sat_scale(u, c.vmax)
        self.check_done(self.att_small() and abs(clr - CA["clearance_target_m"]) < 2e-3 and self.extra_done(m))
        return u


class C2(C1):
    """C1 + pressure-based twist loop: drive n^T P -> 0 (equal-stiffness, twist-free load split; needs no CoM),
    plus an F_min guard."""
    name = "C2"

    def twist_rate(self, m):
        c = self.c
        tw = float(c.n @ m["P"])
        db = CA["twist_deadband_N"]
        e = 0.0 if abs(tw) < db else (tw - math.copysign(db, tw))
        rate = -CA["Ktw_1_s"] * e / c.k_nom
        lo = c.F_min + 5e3
        L = self.load_est(m)
        i = int(np.argmin(L))
        if L[i] < lo:
            rate += math.copysign(1.0, c.n[i]) * CA["Ktw_1_s"] * (lo - L[i]) / c.k_nom
        return rate

    def extra_done(self, m):
        return abs(float(self.c.n @ m["P"])) < CA["twist_deadband_N"] + 1e3


class C4(C2):
    """Constrained QP every cycle (proxsuite): track C2's desired rates with attitude priority, subject to speed,
    stroke (preview) and predicted cylinder-force limits F_min + margin <= P + S_nom u T <= F_max."""
    name = "C4"

    def level(self, m):
        import proxsuite
        c = self.c
        zd, phid, thd, clr = self.outer(m)
        tdot = self.twist_rate(m)
        B = np.vstack([c.Ap, c.n])                      # [heave; roll; pitch; twist] rates per leg speed
        r = np.array([zd, phid, thd, tdot])
        wts = np.array([0.3, 1.0, 1.0, 1.0])
        # scaled QP: decision variable v = u in mm/s, rates in mrad/s and mm/s, forces in kN
        Bw = B * wts[:, None]
        H = 2 * (Bw.T @ Bw + 1e-6 * np.eye(4))           # (1e3 r)^2 = (B v)^2 -> same H
        g = -2 * Bw.T @ (r * wts) * 1e3
        Th = 0.5
        lo = np.maximum(-c.vmax, (0.0 - m["x"]) / Th) * 1e3
        hi = np.minimum(c.vmax, (c.smax - m["x"]) / Th) * 1e3
        Cs = [np.eye(4)]; ls = [lo]; us = [hi]
        if True:   # force limits from touchdown on (also while the crawler still bears load)
            Tp = CA["C4_preview_s"]
            L = self.load_est(m)
            Cs.append(c.S_nom * Tp * 1e-6)                # kN per (mm/s)
            ls.append((np.full(4, c.F_min + CA["C4_Fmin_margin_N"]) - L) * 1e-3)
            us.append((np.full(4, CA["C4_Fmax_N"]) - m["P"]) * 1e-3)
        C = np.vstack(Cs); l = np.concatenate(ls); uu = np.concatenate(us)
        l = np.minimum(l, uu)
        res = proxsuite.proxqp.dense.solve(H=H, g=g, A=None, b=None, C=C, l=l, u=uu, eps_abs=1e-7)
        if str(res.info.status).endswith("SOLVED"):
            u = np.clip(res.x * 1e-3, -c.vmax, c.vmax)
        else:
            self.events.append((round(self.t, 2), "qp_fail " + str(res.info.status).split(".")[-1])) if len(self.events) < 10 else None
            u = _sat_scale(c.A @ np.array([zd, phid, thd]) + c.n * tdot, c.vmax)
        self.check_done(self.att_small() and abs(clr - CA["clearance_target_m"]) < 2e-3 and self.extra_done(m))
        return u



class C6(C1):
    """Statically determinate: FL, FR, RL position-controlled by the exact 3-leg kinematics; RR force-controlled
    to sum(P)/4."""
    name = "C6"

    def on_touch(self, m):
        super().on_touch(m)
        self.A3 = self.c.A[:3]
        self.S_pp = self.c.k_nom * self.c.n[3] ** 2

    def level(self, m):
        c = self.c
        if not self.lifted:     # crawler still bears load: the passive force loop would only tilt the body
            return C1.level(self, m)
        zd, phid, thd, clr = self.outer(m)
        qd = np.array([zd, phid, thd])
        ua = self.A3 @ qd                      # leg rates of the 3 active legs (u = A q_dot)
        Ft = float(m["P"].sum()) / 4
        e = Ft - m["P"][3]
        e = 0.0 if abs(e) < 1e3 else e - math.copysign(1e3, e)
        # passive leg: rigid-body feed-forward (moves with the plane of the 3 active legs) + force trim to the target
        up = float(c.A[3] @ qd) + CA["Kf_1_s"] * e / self.S_pp
        u = _sat_scale(np.array([*ua, up]), c.vmax)
        self.check_done(self.att_small() and abs(clr - CA["clearance_target_m"]) < 2e-3
                        and abs(Ft - m["P"][3]) < 3e3)
        return u


class Rule(Controller):
    """Common pieces of the rule-based extend-only family (C3, C7, C8)."""

    def lift_equal(self, m):
        clr = self.c.clearance_est(m["x"])
        return clr >= CA["clearance_target_m"], np.full(4, self.c.vmax)

    def reground(self, m):
        low = self.load_est(m) < CA["P_reground_N"]
        return low, np.where(low, 0.2 * self.c.vmax, 0.0)

    def highest_ref(self, speed_frac, prop=True):
        c = self.c
        z = c.heights(self.phi_f, self.th_f)
        de = z.max() - z                         # extension needed to bring each leg up to the highest one
        if prop and self.att_small(CA["trim_deadband_deg"] * DEG):
            return np.zeros(4), de               # trim dead band (on the slow filter): avoids a rocking limit cycle
        if prop:
            u = np.minimum(CA["K_fine_1_s"] * de, speed_frac * c.vmax)
            u[de < 2e-4] = 0.0
        else:
            u = np.where(de > 3e-3, speed_frac * c.vmax, 0.0)
        return u, de


class C3(Rule):
    """Highest-point following, extend-only: equal lift to clearance -> coarse (on/off v_max) -> fine (proportional,
    0.25 v_max) -> re-ground legs below P_reground -> done."""
    name = "C3"

    def on_touch(self, m):
        self.st = "lift"

    def on_relevel(self):
        self.st = "fine"

    def level(self, m):
        if self.st == "lift":
            ok, u = self.lift_equal(m)
            if ok:
                self.st = "coarse"
            return u if not ok else np.zeros(4)
        if self.st == "coarse":
            # 2-axis rule (Sany type): larger axis error first, extend the low-side PAIR on/off at v_max.
            # (Extending legs individually on/off at the same speed lifts the opposite leg off: tested, see doc.)
            tol = CA["C3_coarse_tol_deg"] * DEG
            u = np.zeros(4)
            if max(abs(self.phi_f), abs(self.th_f)) <= tol:
                self.st = "fine"
                return u
            ax = getattr(self, "axis", None)        # hysteresis: stay on one axis until it is within tol
            if ax is None or (ax == "pitch" and abs(self.th_f) <= tol) or (ax == "roll" and abs(self.phi_f) <= tol):
                ax = "pitch" if abs(self.th_f) >= abs(self.phi_f) else "roll"
            self.axis = ax
            if ax == "pitch":
                pair = [0, 1] if self.th_f > 0 else [2, 3]     # nose down -> front pair is low
            else:
                pair = [1, 3] if self.phi_f > 0 else [0, 2]    # left up -> right pair is low
            u[pair] = self.c.vmax
            return u
        if self.st == "fine":
            u, de = self.highest_ref(CA["C3_fine_speed_frac"], prop=True)
            if self.att_small():
                self.st = "reground"
            return u
        if self.st == "reground":
            low, u = self.reground(m)
            if not low.any():
                if self.att_small():
                    self.check_done(True)
                else:
                    self.st = "fine"
            return u
        return np.zeros(4)


class C7(Rule):
    """Diagonal decomposition, extend-only: pair (FL, RR) and (FR, RL) each extend their lower leg proportionally
    to the diagonal height difference; minimum-pressure switch on every leg."""
    name = "C7"

    def on_touch(self, m):
        self.st = "lift"

    def on_relevel(self):
        self.st = "level"

    def level(self, m):
        c = self.c
        if self.st == "lift":
            ok, u = self.lift_equal(m)
            if ok:
                self.st = "level"
            return u if not ok else np.zeros(4)
        z = c.heights(self.phi_f, self.th_f)
        u = np.zeros(4)
        for a, b in ((0, 3), (1, 2)):
            d = z[a] - z[b]
            lo = b if d > 0 else a
            if abs(d) > 2e-4:
                u[lo] = min(c.vmax, CA["K_fine_1_s"] * abs(d))
        low, ur = self.reground(m)
        # minimum-pressure interlock with hysteresis: pause levelling, re-load the light leg(s) to P_reg + 10 kN
        lock = getattr(self, "lock", np.zeros(4, bool))
        lock = (lock & (self.load_est(m) < CA["P_reground_N"] + 10e3)) | low
        self.lock = lock
        if lock.any():
            if not getattr(self, "_was_locked", False) and len(self.events) < 10:
                self.events.append((round(self.t, 2), "interlock"))
            u = np.where(lock, 0.2 * c.vmax, 0.0)
        self._was_locked = bool(lock.any())
        self.check_done(self.att_small() and not low.any())
        return u


class C8(Rule):
    """Two-phase: attitude first (highest-leg reference, proportional, extend-only) -> parallel lift (equal speed)
    -> re-ground floating legs -> fine trim."""
    name = "C8"

    def on_touch(self, m):
        self.st = "attitude"

    def on_relevel(self):
        self.st = "trim"

    def level(self, m):
        if self.st == "attitude":
            _, de = self.highest_ref(1.0, prop=True)
            u = _sat_scale(CA["K_fine_1_s"] * de, self.c.vmax)   # synchronised proportional (same arrival time)
            if self.att_small(0.05 * DEG):
                self.st = "lift"
            return u
        if self.st == "lift":
            ok, u = self.lift_equal(m)
            if ok:
                self.st = "reground"
            return u if not ok else np.zeros(4)
        if self.st == "reground":
            low, u = self.reground(m)
            if not low.any():
                self.st = "trim"
            return u
        if self.st == "trim":
            u, de = self.highest_ref(CA["C3_fine_speed_frac"], prop=True)
            low, ur = self.reground(m)
            self.check_done(self.att_small() and not low.any())
            return np.maximum(u, ur)
        return np.zeros(4)


CANDIDATES = {"C1": C1, "C2": C2, "C3": C3, "C4": C4, "C6": C6, "C7": C7, "C8": C8}

# ---------------------------------------------------------------------------- one run


def run_case(cand, level="top", roll=0.0, pitch=0.0, beta=1.0e9, Fs=0.0, imu="nominal", soft_FL=False,
             contact="pressure", settle=False, dt=DT, keep_series=False, seed=None):
    plant = Plant(level, roll, pitch, beta=beta, Fs=Fs, soft_FL=soft_FL, dt=dt)
    nsub = int(round(T_CTRL / dt))
    # settle on the crawler for 3 s (not recorded)
    plant.step(np.zeros(4), int(round(3.0 / dt)))
    plant.t = 0.0
    rng = np.random.default_rng(CA["seed"] if seed is None else seed)
    sens = Sensors(CA["imu_" + imu], rng, plant.g)
    W_nom = dm.body_from_params(dm.load_params(), level).mass * plant.g
    k_nom = float(np.mean(Plant.k_nom_cache()))
    ctx = Ctx(plant.geo, W_nom, k_nom)
    ctrl = CANDIDATES[cand](ctx, contact=contact)
    sc = CA["settle_scenario"]; sleg = dm.LEG_NAMES.index(sc["leg"])
    u = np.zeros(4)
    ser = {k: [] for k in ("t", "phi", "theta", "phi_m", "theta_m", "P", "Ftrue", "x", "u", "crawler_N", "clr",
                           "Pmax", "Pmin")}
    sat_steps = np.zeros(4); stroke_steps = np.zeros(4)
    t_lift = None; t_sink = None
    t_end = T_MAX
    while plant.t < t_end - 1e-9:
        if settle and ctrl.t_ready_first is not None:
            t_sink = ctrl.t_ready_first + sc["start_after_ready_s"]
            plant.goff[sleg] = sc["depth_m"] * min(1.0, max(0.0, (plant.t - t_sink) / sc["ramp_s"]))
        a = plant.step(u, nsub)
        sat_steps += a[3:7]; stroke_steps += a[7:11]
        m = sens.read(plant, a, nsub)
        phi, th = plant.attitude()
        if t_lift is None and a[15] == 0.0 and ctrl.phase == "level":
            t_lift = plant.t
        ser["t"].append(plant.t); ser["phi"].append(phi); ser["theta"].append(th)
        ser["phi_m"].append(ctrl.phi_f if ctrl.phi_f is not None else m["phi"])
        ser["theta_m"].append(ctrl.th_f if ctrl.th_f is not None else m["theta"])
        ser["P"].append(plant.pressure().copy()); ser["Ftrue"].append(plant.true_cyl_force().copy())
        ser["x"].append(plant.x.copy()); ser["u"].append(u.copy()); ser["crawler_N"].append(a[15])
        ser["clr"].append(plant.crawler_clearance())
        ser["Pmax"].append(a[16:20].copy()); ser["Pmin"].append(a[20:24].copy())
        u = ctrl.update(m, plant.t)
        if ctrl.t_ready_first is not None:
            t_end = min(T_MAX, ctrl.t_ready_first + (40.0 if settle else T_HOLD))
        if getattr(ctrl, "fault", False) and t_end == T_MAX:
            t_end = plant.t + T_HOLD
    S = {k: np.array(v) for k, v in ser.items()}
    res = metrics(S, ctrl, plant, t_lift, sat_steps, stroke_steps, t_sink)
    res.update({"cand": cand, "level": level, "roll_g": roll, "pitch_g": pitch, "beta_GPa": beta / 1e9,
                "Fs_kN": Fs / 1e3, "imu": imu, "soft_FL": soft_FL, "contact": contact, "settle": settle, "dt": dt})
    if keep_series:
        res["_series"] = S
    return res


def _kn_cache():
    p = dm.load_params()
    L1 = p["contact"]["rigid_floor"]["L1"]
    return np.array([L1["kn_per_pad_N_m"][nm] for nm in dm.LEG_NAMES], float)


Plant.k_nom_cache = staticmethod(_kn_cache)


def metrics(S, ctrl, plant, t_lift, sat_steps, stroke_steps, t_sink=None):
    t = S["t"]
    att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
    attm = np.degrees(np.column_stack([S["phi_m"], S["theta_m"]]))
    F_min = ctrl.c.F_min
    r2 = lambda v: None if v is None else round(float(v), 2)  # noqa: E731
    out = {"t_touch_s": r2(getattr(ctrl, "t_touch", None)), "t_crawler_liftoff_s": r2(t_lift),
           "t_done_s": r2(ctrl.t_done), "t_ready_s": r2(ctrl.t_ready_first),
           "probe_time_s": round(ctrl.probe_time, 2), "probe_rounds": ctrl.probe_rounds,
           "events": ctrl.events[:12]}
    if ctrl.probe_log:
        out["probe_first"] = ctrl.probe_log[0]["res"]
        out["probe_last"] = ctrl.probe_log[-1]["res"]
    out["accuracy_target_deg"] = target_deg()
    t_stop = t_sink if t_sink is not None else t[-1] + 1
    pre = t < t_stop
    if t_lift is not None:
        post = (t >= t_lift) & pre
        att_max = np.max(np.abs(att), axis=1)
        # time after which the true attitude stays inside a band (legacy key fixed at 0.1 deg; target key at the target)
        for key, lim in (("t_within_0p1deg_s", 0.1), ("t_within_target_s", target_deg())):
            bad = np.where(post & ~(att_max <= lim))[0]
            idx = (bad[-1] + 1) if len(bad) else int(np.argmax(post))
            out[key] = round(float(t[idx]), 2) if idx < len(t) and ctrl.t_done is not None else None
        Ft = S["Ftrue"][post]; P = S["P"][post]
        out["min_true_cyl_force_kN"] = round(float(Ft.min()) / 1e3, 2)
        out["min_true_leg"] = dm.LEG_NAMES[int(np.argmin(Ft.min(axis=0)))]
        out["min_pressure_reading_kN"] = round(float(P.min()) / 1e3, 2)
        out["t_below_Fmin_true_s"] = round(float(np.sum(Ft.min(axis=1) < F_min)) * T_CTRL, 2)
        out["t_below_Fmin_pressure_s"] = round(float(np.sum(P.min(axis=1) < F_min)) * T_CTRL, 2)
        out["pad_liftoff_after_crawler_off"] = bool((Ft + plant.Wr <= 1.0).any())
        hp = att[post] - _movavg(att[post], 50)
        out["rocking_peak_deg"] = round(float(np.max(np.abs(hp))), 4)
        if ctrl.t_done is not None and ctrl.t_ready_first is not None and ctrl.t_ready_first > ctrl.t_done:
            w = (t >= ctrl.t_done) & (t <= ctrl.t_ready_first)
            out["probe_window_max_true_att_deg"] = round(float(np.abs(att[w]).max()), 4)
    else:
        out.update({"t_within_0p1deg_s": None, "t_within_target_s": None, "min_true_cyl_force_kN": None, "min_pressure_reading_kN": None,
                    "t_below_Fmin_true_s": None, "t_below_Fmin_pressure_s": None, "rocking_peak_deg": None,
                    "pad_liftoff_after_crawler_off": None})
    out["max_pressure_bar"] = round(float(S["Pmax"].max()) / plant.Ap / 1e5, 1)
    out["max_true_cyl_force_kN"] = round(float(S["Ftrue"].max()) / 1e3, 1)
    if ctrl.t_ready_first is not None:
        fin = (t >= min(t[-1], t_stop) - 5.0) & pre
        out["ss_true_att_deg_mean"] = [round(float(v), 4) for v in att[fin].mean(axis=0)]
        out["ss_true_att_deg_maxabs"] = round(float(np.abs(att[fin]).max()), 4)
        out["ss_meas_att_deg_mean"] = [round(float(v), 4) for v in attm[fin].mean(axis=0)]
        j = int(np.where(pre)[0][-1])
        out["levelled_loads_true_kN"] = [round(float(v) / 1e3, 2) for v in S["Ftrue"][j]]
        out["levelled_pressure_kN"] = [round(float(v) / 1e3, 2) for v in S["P"][j]]
        out["final_clearance_mm"] = round(float(S["clr"][j]) * 1e3, 1)
        out["levelled_twist_load_kN"] = round(float(ctrl.c.n @ S["Ftrue"][j]) / 1e3, 2)
    if t_sink is not None:
        aft = t >= t_sink
        out["settle_result"] = {"t_sink_s": round(t_sink, 2),
                         "final_true_kN": [round(float(v) / 1e3, 2) for v in S["Ftrue"][-1]],
                         "final_pressure_kN": [round(float(v) / 1e3, 2) for v in S["P"][-1]],
                         "final_att_deg": [round(float(v), 4) for v in att[-1]],
                         "t_below_Fmin_true_after_sink_s": round(float(np.sum(S["Ftrue"][aft].min(axis=1) < F_min)) * T_CTRL, 2),
                         "final_below_Fmin_true": bool(S["Ftrue"][-1].min() < F_min),
                         "final_below_Fmin_pressure": bool(S["P"][-1].min() < F_min)}
    out["final_stroke_mm"] = [round(float(v) * 1e3, 1) for v in S["x"][-1]]
    out["max_stroke_mm"] = round(float(S["x"].max()) * 1e3, 1)
    dx = np.abs(np.diff(S["x"][pre], axis=0)).sum()
    out["total_extension_travel_mm"] = round(float(dx) * 1e3, 1)
    out["force_sat_210bar_steps"] = int(sat_steps.sum())
    out["stroke_limit_steps"] = int(stroke_steps.sum())
    fails = []
    if ctrl.t_ready_first is None:
        fails.append("stroke_end_fault" if getattr(ctrl, "fault", False) else "not_done_150s")
    if out.get("t_below_Fmin_true_s"):
        fails.append("Fmin_true")
    if out.get("pad_liftoff_after_crawler_off"):
        fails.append("pad_liftoff")
    if ctrl.t_ready_first is not None and out["ss_true_att_deg_maxabs"] > target_deg():
        fails.append(ss_fail_label())
    if out["max_pressure_bar"] >= 210:
        fails.append("210bar")
    if t_sink is not None and out["settle_result"]["final_below_Fmin_true"]:
        fails.append("settle_Fmin_missed")
    out["fails"] = fails
    return out




def _movavg(a, n):
    k = np.ones(n) / n
    pad = np.pad(a, ((n // 2, n - 1 - n // 2), (0, 0)), mode="edge")
    return np.column_stack([np.convolve(pad[:, j], k, mode="valid") for j in range(a.shape[1])])


# ---------------------------------------------------------------------------- plant checks


def plant_checks():
    out = {}
    p = dm.load_params(); geo = dm.geometry_from_params(p)
    e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
    pl = Plant("top", init_ext=e_op)
    # place with analytic penetration to shorten settling: start pads touching, settle 40 s with extra damping?
    pl.step(np.zeros(4), int(40 / DT))
    F_c = pl.acc[11:15].copy()
    ref = np.array([119.292, 117.318, 73.758, 71.922]) * 1e3
    out["V1_static_contact_kN"] = {"model": (F_c / 1e3).round(3).tolist(), "reference_L1": (ref / 1e3).tolist(),
                                   "max_abs_diff_kN": round(float(np.abs(F_c - ref).max()) / 1e3, 3)}
    phi, th = pl.attitude()
    out["V3_settled_att_deg"] = {"model": [round(math.degrees(phi), 4), round(math.degrees(th), 4)],
                                 "reference_L1": [-0.0021, 0.0266]}
    # FL +1 mm at 0.5 mm/s, others locked
    F0 = F_c.copy()
    pl.step(np.array([5e-4, 0, 0, 0]), int(2.0 / DT))
    pl.step(np.zeros(4), int(40 / DT))
    dF = pl.acc[11:15] - F0
    out["V5_FL_plus_1mm_dF_kN"] = {"model": (dF / 1e3).round(3).tolist(), "reference": [4.77, -4.77, -5.24, 5.24]}
    # free vibration: roll and pitch initial angular velocity
    pl2 = Plant("top", init_ext=e_op)
    pl2.step(np.zeros(4), int(40 / DT))
    pl2.w[:] = [2e-4, 3e-4, 0]
    rec = []
    for _ in range(int(20 / (10 * DT))):
        pl2.step(np.zeros(4), 10)
        rec.append(pl2.attitude())
    rec = np.array(rec); rec -= rec.mean(axis=0)
    fs = 1 / (10 * DT)
    out["V7_rocking_Hz"] = {"model_fft_peaks": _fft_peaks(rec, fs), "reference_L1": [1.785, 2.984]}
    return out


def _fft_peaks(rec, fs):
    peaks = []
    for j in range(rec.shape[1]):
        y = rec[:, j] * np.hanning(len(rec))
        Y = np.abs(np.fft.rfft(y, n=8 * len(y)))
        fr = np.fft.rfftfreq(8 * len(y), 1 / fs)
        sel = (fr > 0.5) & (fr < 6)
        peaks.append(round(float(fr[sel][np.argmax(Y[sel])]), 3))
    return peaks


# ---------------------------------------------------------------------------- study


def case_list(quick=False):
    slopes = [("flat", 0, 0), ("pitch+1", 0, 1), ("roll+1", 1, 0), ("diag1", 0.7071, 0.7071),
              ("pitch+3", 0, 3), ("pitch-3", 0, -3), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213),
              ("pitch+3.7", 0, 3.7), ("roll+5.7", 5.7, 0), ("diag3.2", 2.2627, 2.2627)]
    cands = list(CANDIDATES)
    cases = []
    if quick:
        return [dict(cand=c, level="top", roll=2.1213, pitch=2.1213, tag="diag3") for c in cands]
    for c in cands:
        for lv in ("top", "bottom"):
            for tag, ro, pi in slopes:
                cases.append(dict(cand=c, level=lv, roll=ro, pitch=pi, tag=tag, group="base"))
        for tag, ro, pi in [("diag3", 2.1213, 2.1213), ("roll+3", 3, 0)]:
            for b in (0.69e9, 1.6e9):
                cases.append(dict(cand=c, level="top", roll=ro, pitch=pi, beta=b, tag=tag, group="beta"))
        for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0)]:
            for fs in (0.0, 5e3, 12e3):
                for ct in ("pressure", "combined"):
                    if fs == 0.0 and ct == "pressure":
                        continue          # = base case
                    cases.append(dict(cand=c, level="top", roll=ro, pitch=pi, Fs=fs, contact=ct, tag=tag, group="seal"))
        for fs in (0.0, 12e3):
            for ct in ("pressure", "combined"):
                cases.append(dict(cand=c, level="top", Fs=fs, contact=ct, settle=True, tag="flat", group="settle"))
        for tag, ro, pi in [("flat", 0, 0), ("diag3", 2.1213, 2.1213)]:
            cases.append(dict(cand=c, level="top", roll=ro, pitch=pi, imu="worst", tag=tag, group="imu_worst"))
            cases.append(dict(cand=c, level="top", roll=ro, pitch=pi, soft_FL=True, tag=tag, group="soft_FL"))
    return cases


def _run(kw):
    kw = dict(kw)
    tag = kw.pop("tag"); grp = kw.pop("group", "base")
    ov = kw.pop("ca", None)          # CA overrides travel with the case (Windows Pool workers re-import this module)
    if ov:
        CA.update(ov)
    t0 = time.perf_counter()
    try:
        r = run_case(**kw)
    except Exception as e:  # keep the sweep going, report the failure
        r = {"cand": kw["cand"], "error": repr(e)}
    r["slope"] = tag; r["group"] = grp; r["wall_s"] = round(time.perf_counter() - t0, 1)
    return r




KEEP = ("cand", "group", "slope", "level", "beta_GPa", "Fs_kN", "imu", "soft_FL", "contact", "settle", "t_touch_s",
        "t_crawler_liftoff_s", "t_done_s", "t_ready_s", "probe_time_s", "probe_rounds", "probe_window_max_true_att_deg",
        "t_within_0p1deg_s", "t_within_target_s", "ss_true_att_deg_mean", "ss_true_att_deg_maxabs", "min_true_cyl_force_kN", "min_true_leg",
        "min_pressure_reading_kN", "t_below_Fmin_true_s", "t_below_Fmin_pressure_s", "max_pressure_bar",
        "max_true_cyl_force_kN", "levelled_loads_true_kN", "levelled_pressure_kN", "levelled_twist_load_kN",
        "final_clearance_mm", "max_stroke_mm", "total_extension_travel_mm", "rocking_peak_deg",
        "force_sat_210bar_steps", "settle_result", "probe_last", "fails", "events", "error")


def compact(r):
    out = {k: r[k] for k in KEEP if k in r and r[k] not in (None, [], {})}
    if "events" in out:
        out["events"] = out["events"][:6]
    if out.get("group") not in ("seal", "settle"):
        out.pop("probe_last", None)
        out.pop("levelled_pressure_kN", None)
    if out.get("group") == "base":
        for k in ("events", "probe_time_s", "probe_rounds", "contact", "settle", "imu", "soft_FL", "Fs_kN", "beta_GPa",
                  "t_crawler_liftoff_s", "t_done_s", "ss_true_att_deg_mean"):
            out.pop(k, None)
    return out


def summarise(runs):
    summ = {}
    for c in CANDIDATES:
        base = [r for r in runs if r.get("cand") == c and r.get("group") == "base"]
        ok = [r for r in base if not r.get("fails")]
        tr = [r["t_ready_s"] - r["t_touch_s"] for r in ok if r.get("t_ready_s") is not None]
        summ[c] = {
            "base_runs": len(base), "base_pass": len(ok),
            "base_fail_cases": sorted({f"{r['level']}:{r['slope']}:{'/'.join(r.get('fails', []))}" for r in base
                                       if r.get("fails")}),
            "levelling_time_after_touchdown_s_median": round(float(np.median(tr)), 1) if tr else None,
            "levelling_time_after_touchdown_s_max": round(float(np.max(tr)), 1) if tr else None,
            "min_true_cyl_force_kN_over_passed": round(min(r["min_true_cyl_force_kN"] for r in ok), 1) if ok else None,
            "max_pressure_bar_over_passed": max(r["max_pressure_bar"] for r in ok) if ok else None,
            "rocking_peak_deg_max_over_passed": max(r["rocking_peak_deg"] for r in ok) if ok else None,
            "ss_true_att_deg_max_over_passed": max(r["ss_true_att_deg_maxabs"] for r in ok) if ok else None,
            "travel_mm_median_over_passed": round(float(np.median([r["total_extension_travel_mm"] for r in ok])), 0)
            if ok else None,
            "clearance_mm_median_over_passed": round(float(np.median([r["final_clearance_mm"] for r in ok])), 1)
            if ok else None,
        }
    return summ


def figures(runs, stem="control_comparison"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Fig 1: time histories, top level, ground roll +3 deg
    cols = {"C1": "#1f77b4", "C2": "#2ca02c", "C3": "#d62728", "C4": "#9467bd", "C6": "#8c564b", "C7": "#e377c2",
            "C8": "#ff7f0e"}
    fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    for c in ("C1", "C2", "C3", "C6", "C7", "C8"):
        r = run_case(c, "top", 3.0, 0.0, keep_series=True)
        S = r["_series"]
        t = S["t"]
        ax[0].plot(t, np.degrees(S["phi"]), color=cols[c], lw=1.0, label=f"{c} roll")
        ax[1].plot(t, S["Ftrue"].min(axis=1) / 1e3, color=cols[c], lw=1.0, label=c)
    tg = target_deg()
    ax[0].axhspan(-tg, tg, color="0.85", zorder=0)
    ax[0].set_ylim(-0.3, 3.2); ax[0].set_ylabel("true roll [deg] (ZYX)")
    ax[0].set_title(f"top auger, ground roll +3 deg, beta 1.0 GPa, F_s 0, IMU nominal, LPF order "
                    f"{CA['imu_lpf_order']} (grey = +/-{tg:g} deg)", fontsize=10)
    ax[0].legend(ncol=3, fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].axhline(9.4525, color="k", ls="--", lw=0.8); ax[1].text(1, 12, "F_min 9.45 kN", fontsize=8)
    ax[1].set_ylim(-5, 130); ax[1].set_ylabel("min true cylinder force [kN]"); ax[1].set_xlabel("time from leg start [s]")
    ax[1].set_xlim(10, 60); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{stem}_timeseries.png", dpi=90)
    plt.close(fig)

    # Fig 2: base matrix (levelling time after touchdown, or failure code)
    slopes = ["flat", "pitch+1", "roll+1", "diag1", "pitch+3", "pitch-3", "roll+3", "diag3", "pitch+3.7", "roll+5.7",
              "diag3.2"]
    cands = list(CANDIDATES)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for k, lv in enumerate(("top", "bottom")):
        M = np.full((len(cands), len(slopes)), np.nan)
        for i, c in enumerate(cands):
            for j, s in enumerate(slopes):
                rr = [r for r in runs if r.get("cand") == c and r.get("group") == "base" and r.get("level") == lv
                      and r.get("slope") == s]
                if not rr:
                    continue
                r = rr[0]
                txt = ""
                if r.get("fails"):
                    M[i, j] = -1
                    f = r["fails"]
                    txt = "END" if "stroke_end_fault" in f else ("LIFT" if "pad_liftoff" in f else ("NDONE" if "not_done_150s" in f else
                                                                ("Fmin" if "Fmin_true" in f else f[0][:5])))
                else:
                    M[i, j] = r["t_ready_s"] - r["t_touch_s"]
                    txt = f"{M[i, j]:.0f}"
                axs[k].text(j, i, txt, ha="center", va="center", fontsize=7,
                            color="w" if M[i, j] == -1 else "k")
        Mm = np.ma.masked_where(~(M >= 0), M)
        axs[k].imshow(np.where(M == -1, 1, np.nan), cmap="Reds", vmin=0, vmax=1.3, aspect="auto")
        im = axs[k].imshow(Mm, cmap="Blues", vmin=0, vmax=40, aspect="auto")
        axs[k].set_xticks(range(len(slopes)), slopes, rotation=45, fontsize=8)
        axs[k].set_yticks(range(len(cands)), cands)
        axs[k].set_title(f"{lv}: levelling time after touchdown [s] / failure", fontsize=9)
    fig.colorbar(im, ax=axs, shrink=0.8, label="s")
    fig.savefig(OUT_DIR / f"{stem}_matrix.png", dpi=90, bbox_inches="tight")
    plt.close(fig)


REGRESS_SLOPES = [("flat", 0, 0), ("pitch+3", 0, 3), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213)]
REGRESS_KEYS = ("t_touch_s", "t_ready_s", "ss_true_att_deg_maxabs", "ss_true_att_deg_mean", "min_true_cyl_force_kN",
                "max_pressure_bar", "rocking_peak_deg", "levelled_loads_true_kN", "final_clearance_mm",
                "t_within_0p1deg_s", "t_within_target_s", "fails")


def regress(ov_new, ov_legacy, stem):
    """C2, top auger, 4 slopes: new settings + legacy re-run; legacy compared with the stored control_comparison.json."""
    from multiprocessing import Pool
    cases = []
    for mode, ov in (("new", ov_new), ("legacy", ov_legacy)):
        for tag, ro, pi in REGRESS_SLOPES:
            cases.append(dict(cand="C2", level="top", roll=ro, pitch=pi, tag=tag, group="base", ca=dict(ov),
                              _mode=mode))
    modes = [c.pop("_mode") for c in cases]
    t0 = time.perf_counter()
    # compile / cache numba in the main process first (a cache written by a spawned worker refers to '__mp_main__'
    # and cannot be loaded later by a main process)
    _run(dict(cases[-1]))
    with Pool(min(8, os.cpu_count() or 4)) as pool:
        runs = pool.map(_run, cases, chunksize=1)
    for r, md in zip(runs, modes):
        r["mode"] = md
    stored = {}
    if OUT_JSON.exists():
        with open(OUT_JSON, encoding="utf-8") as fh:
            for r in json.load(fh)["runs"]:
                if r.get("cand") == "C2" and r.get("group") == "base" and r.get("level") == "top":
                    stored[r["slope"]] = r
    cmp = {}
    for r in runs:
        if r["mode"] != "legacy" or r["slope"] not in stored:
            continue
        s = stored[r["slope"]]
        diffs = {}
        for k in REGRESS_KEYS:
            if k in s and k in r and k not in ("fails", "t_within_target_s", "ss_true_att_deg_mean"):
                a, b = np.asarray(s[k], float), np.asarray(r[k], float)
                diffs[k] = float(np.max(np.abs(a - b)))
        diffs["fails_equal"] = list(s.get("fails", [])) == list(r.get("fails", []))
        cmp[r["slope"]] = diffs
    out = {"meta": {"script": "04_scripts/01_dynamics/run_control_comparison.py --regress", "dt_s": DT, "T_ctrl_s": T_CTRL,
                    "new_overrides": ov_new, "legacy_overrides": ov_legacy, "assumptions_new": {**CA, **ov_new},
                    "wall_s": round(time.perf_counter() - t0, 1),
                    "note": "C2 top auger, IMU nominal, beta 1.0 GPa, F_s 0, pressure-only judge. legacy rows "
                            "are compared with the stored control_comparison.json (read only)."},
           "runs": [{"mode": r["mode"], "slope": r["slope"], **{k: r.get(k) for k in REGRESS_KEYS},
                     "wall_s": r.get("wall_s"), "error": r.get("error")} for r in runs],
           "legacy_vs_stored_maxabs_diff": cmp}
    path = OUT_DIR / f"{stem}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("wrote", path, out["meta"]["wall_s"], "s")
    print(json.dumps(out["runs"], indent=1, default=float))
    print(json.dumps(cmp, indent=1))


def _parse_args(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Levelling controller comparison (reduced 6-DoF model)")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--legacy", action="store_true", help="original 2026-10-20 assumptions (0.1 deg, old IMU point, 1st order)")
    ap.add_argument("--regress", action="store_true", help="C2 top 4-slope regression (new settings + legacy check)")
    ap.add_argument("--target-deg", type=float, default=None)
    ap.add_argument("--imu-lpf-order", type=int, choices=(1, 2), default=None)
    ap.add_argument("--imu-point", type=float, nargs=3, metavar=("X", "Y", "Z"), default=None)
    ap.add_argument("--out-stem", default=None)
    return ap.parse_args(argv)


def main():
    args = _parse_args(sys.argv[1:])
    ov = {k: CA[k] for k in LEGACY_CA}                      # current defaults (decision 2026-10-20)
    if args.legacy:
        ov.update(LEGACY_CA)
    if args.target_deg is not None:
        ov["accuracy_target_deg"] = args.target_deg
    if args.imu_lpf_order is not None:
        ov["imu_lpf_order"] = args.imu_lpf_order
    if args.imu_point is not None:
        ov["imu_point_body_m"] = list(args.imu_point)
    if args.regress:
        regress(ov, dict(LEGACY_CA), args.out_stem or "control_comparison_c2_regress_c1")
        return
    CA.update(ov)
    stem = args.out_stem or ("control_comparison" if ov == LEGACY_CA else "control_comparison_rev6")
    quick = args.quick
    if quick and not args.out_stem:
        stem += "_quick"                         # never overwrite the full-matrix results with a quick run
    t0 = time.perf_counter()
    res = {"meta": {"script": "04_scripts/01_dynamics/run_control_comparison.py", "argv": sys.argv[1:], "dt_s": DT,
                    "T_ctrl_s": T_CTRL,
                    "T_max_s": T_MAX, "assumptions": CA,
                    "frames": "body x fwd, y left, z up; ZYX Euler (roll phi about x, pitch theta about y, theta>0 "
                              "nose down); quaternion wxyz; gravity (0,0,-9.80665) m/s^2; leg order FL FR RL RR",
                    "force_basis": "cylinder force = contact force - rod weight; pressure reading = cylinder force - "
                                   "seal friction f",
                    "slopes": "ground roll/pitch in deg; diagN = N deg along the 45 deg diagonal (roll = pitch = N/sqrt2)"}}
    res["plant_checks"] = plant_checks()
    print(json.dumps(res["plant_checks"]))
    cases = case_list(quick)
    for c in cases:
        c["ca"] = dict(ov)                       # Pool workers re-import the module: pass the overrides explicitly
    from multiprocessing import Pool
    _run(dict(cases[0]))  # compile numba cache once
    with Pool(min(20, os.cpu_count() or 4)) as pool:
        runs = pool.map(_run, cases, chunksize=1)
    # dt convergence on one case (dt and dt/2)
    a = _run(dict(cand="C2", level="top", roll=2.1213, pitch=2.1213, tag="diag3", group="dt_check"))
    b = _run(dict(cand="C2", level="top", roll=2.1213, pitch=2.1213, tag="diag3", group="dt_check", dt=DT / 2))
    keys = ("t_ready_s", "min_true_cyl_force_kN", "max_pressure_bar", "ss_true_att_deg_mean", "levelled_loads_true_kN",
            "rocking_peak_deg")
    res["dt_check"] = {"dt_5e-4": {k: a.get(k) for k in keys}, "dt_2.5e-4": {k: b.get(k) for k in keys}}
    res["summary_base"] = summarise(runs)
    res["runs"] = [compact(r) for r in runs]
    figures(runs, stem)
    res["meta"]["wall_s"] = round(time.perf_counter() - t0, 1)
    out_json = OUT_DIR / f"{stem}.json"
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, separators=(",", ":"), default=float)
    print("wrote", out_json, res["meta"]["wall_s"], "s,", len(runs), "runs")
    print(json.dumps(res["summary_base"], indent=1))
    print(json.dumps(res["dt_check"]))


if __name__ == "__main__":
    main()
