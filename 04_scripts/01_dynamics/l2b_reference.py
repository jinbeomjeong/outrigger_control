"""L2b-NSC reference block for the REXOME35 cylinders with the rod-side chamber (dynamics_model.md rev. 33, 5.20).

Called by run_reference.py only with an option (no option = main() unchanged):

    run_reference.py --l2b-out <path>   writes this block alone to <path> (reference.json untouched)
    run_reference.py --with-l1r --with-l2b
                                        runs main(), adds the L1-R block and this block to reference.json

Model (S7 plan, chrono_build_plan.md '### S7 L2b-NSC'; per leg, compression of the force law c = s_ref - s > 0):
* rigid NSC pad contact (stick exact, KC_RIGID stands in), the concrete compliance folded into the axial law;
* moving leg (valve open): F = k2(s) c + c_mov (dc/dt), k2(s) = k_h(s) (+) k_out, k_h(s) = beta A_p / (L0h + s);
* locked leg (anchor c_lock, F_lock taken when the leg stops; rod-side chamber = L1-R law of 5.12.4 with the
  column lengths frozen at the locking extension s_lock):
      F = F_lock + k2 dc + (k1 - k2) min(dc, dc_knee),  dc = c - c_lock,
      k1 = (k_h + k_r) (+) k_out, k_r = beta A_ann / (s_max - s_lock + L0r),
      dF_knee = (p_r0 - p_floor_gauge) A_ann (k_h + k_r) / k_r,  dc_knee = dF_knee / k1;
  one locked dashpot c_lock (LOCK basis, zeta 0.03 on k1 at e_op = YAML contact.rigid_floor.L1.cn_per_pad_N_s_m);
* lateral bushing k_t (= L1 kt, concrete tangential compliance in series), x, y of the drive guide freed, rod
  rotation locked to the barrel: with the rod sphere stuck on the floor the lateral spring acts at the contact point
  (pad bottom on a level floor), as in dyn_model.model_10dof.

The statics are linear (small angles) about the levelled pose, superstructure body + 4 rod coordinates, the slope
statics follow dyn_model.static_slope_10dof (same assembly, checked). Units SI, body frame x forward, y left, z up,
level body = world axes, gravity -z (9.80665 m/s^2), leg order FL FR RL RR, forces compression + (cylinder force =
oil force on the body = pressure basis; contact = cylinder + rod weight). Deterministic (no random numbers).
"""
from __future__ import annotations

import math
import time

import dyn_model as dm
import l1r_reference as l1r
import numpy as np
import run_reference as rr
from scipy.integrate import solve_ivp

L2B_KEY = "L2b_NSC_reference_rev33"
KC_RIGID = rr.KC_RIGID
P_WARN_PA = 345e5               # user decision U72 (2026-10-22): 350 bar warning lowered to 345 bar
P_LOCK_PA = 350e5               # YAML actuator.locked_pressure_limit_Pa (checked)
ZETA_MOVING = None              # filled from dm.ASSUMPTIONS["leg_damping_ratio_moving"] (0.1)
V4_SOLVER = dict(rr.V4_DYN_SOLVER)
V14_CASES = (("level", 0), ("max pitch+", 0), ("max pitch-", 180), ("max roll+", 90), ("max diag 45", 45))
V14_TEST = ("RL", +1)
SLOPE_SCALE = 0.999             # same margin as run_actuator_L2_feasibility (max slope x 0.999)

r = rr.r


# ------------------------------------------------------------------ parameters
def leg_parameters(p, geo):
    """L1-R parameters (checked against the YAML by l1r.leg_parameters) + the L2b-only quantities."""
    lp = l1r.leg_parameters(p, geo)
    A_ = dm.ASSUMPTIONS
    act = p["actuator"]
    leg = lambda tbl: np.array([float(tbl[n]) for n in dm.LEG_NAMES])  # noqa: E731
    cyl = lambda key: np.array([float(p["legs"][n]["cylinder"][key]) for n in dm.LEG_NAMES])  # noqa: E731
    g = geo.g
    e_op = lp["e_op"]
    smax = geo.stroke
    d = p["contact"]["rigid_floor"]["L1"]["derivation"]
    m_damp = float(d["damping_mass_kg"])
    zeta = float(d["damping_ratio"])
    zeta_mov = float(A_["leg_damping_ratio_moving"])

    def k_h(s):
        return lp["beta"] * lp["A_p"] / (lp["L0h"] + np.asarray(s, float))

    def k_r(s):
        return lp["beta"] * lp["A_ann"] / (smax - np.asarray(s, float) + lp["L0r"])

    def k2(s):
        return dm.series(k_h(s), lp["k_out"])

    def k1(s):
        return dm.series(k_h(s) + k_r(s), lp["k_out"])

    def knee(s, p_r0):
        rr_ = k_r(s) / (k_h(s) + k_r(s))
        return (p_r0 - lp["p_floor_g"]) * lp["A_ann"] / rr_

    c_lock = 2 * zeta * np.sqrt(k1(e_op) * m_damp / 4)
    c_mov = 2 * zeta_mov * np.sqrt(k2(e_op) * m_damp / 4)
    c_head = 2 * zeta * np.sqrt(k2(e_op) * m_damp / 4)
    L2y = act["L2b_NSC"]
    checks = {
        "k2(e_op) vs YAML actuator.L2b_NSC.axial_stiffness.operating_point_N_m (rel)":
            float(np.abs(k2(e_op) / leg(L2y["axial_stiffness"]["operating_point_N_m"]) - 1).max()),
        "c_lock vs YAML contact.rigid_floor.L1.cn_per_pad_N_s_m (rel)": float(np.abs(c_lock / lp["cn"] - 1).max()),
        "k_t vs YAML actuator.L2b_NSC.lateral_bushing_N_m (rel)": float(np.abs(lp["kt"] / leg(L2y["lateral_bushing_N_m"]) - 1).max()),
        "c_t / 2 vs YAML lateral_bushing_damping_input_N_s_m (rel)":
            float(np.abs(lp["ct"] / 2 / leg(L2y["lateral_bushing_damping_input_N_s_m"]) - 1).max()),
        "F_ext vs 210 bar x A_p (rel)": float(np.abs(cyl("max_force_extend_N") / (210e5 * lp["A_p"]) - 1).max()),
        "F_ret vs 210 bar x A_ann (rel)": float(np.abs(cyl("max_force_retract_N") / (210e5 * lp["A_ann"]) - 1).max()),
        "F_lock vs 350 bar x A_p (rel)": float(np.abs(cyl("locked_force_limit_N") / (P_LOCK_PA * lp["A_p"]) - 1).max()),
    }
    for key, v in checks.items():
        if not v <= 1e-6:
            raise RuntimeError(f"L2b parameter check failed: {key} = {v:.3e}")
    if float(act["locked_pressure_limit_Pa"]) != P_LOCK_PA:
        raise RuntimeError("YAML actuator.locked_pressure_limit_Pa differs from P_LOCK_PA")
    m_rod = geo.rod_mass
    s_tab = {"0": np.zeros(4), "touch": geo.touch_extension, "e_op": np.full(4, 0.0) + e_op,
             "measurable_max 0.6948": np.full(4, float(p["sensors"]["stroke"]["measurable_max_m"])),
             "stroke 0.70": np.full(4, smax)}
    return dict(lp, k_h_f=k_h, k_r_f=k_r, k2_f=k2, k1_f=k1, knee_f=knee, c_lock=c_lock, c_mov=c_mov, c_head=c_head,
                m_damp=m_damp, zeta=zeta, zeta_mov=zeta_mov, m_rod=m_rod, s_tab=s_tab, checks_l2b=checks,
                F_ext=cyl("max_force_extend_N"), F_ret=cyl("max_force_retract_N"), F_lock=cyl("locked_force_limit_N"),
                c_old=leg(L2y["oil_damping_N_s_m"]), c_mov_old=leg(L2y["oil_damping_moving_N_s_m"]), g=g)


def parameters_block(lp, geo):
    g = geo.g
    tab = {}
    for name, s in lp["s_tab"].items():
        tab[name] = {"s_m": r(s, 5), "k_h_N_m": r(lp["k_h_f"](s)), "k_r_N_m": r(lp["k_r_f"](s)),
                     "k2_axial_head_only_N_m (moving)": r(lp["k2_f"](s)), "k1_axial_lock_N_m": r(lp["k1_f"](s)),
                     "knee_after_extend_N": r(lp["knee_f"](s, lp["p_r0_ext"])),
                     "rod_free_mode_Hz (contact open, k2)": r(np.sqrt(lp["k2_f"](s) / lp["m_rod"]) / (2 * math.pi), 5),
                     "rod_free_mode_zeta (c_moving)": r(lp["c_mov"] / (2 * np.sqrt(lp["k2_f"](s) * lp["m_rod"])), 4),
                     "rod_hanging_stretch_mm (m_rod g / k2)": r(lp["m_rod"] * g / lp["k2_f"](s) * 1e3, 4)}
    A_p, A_ann = lp["A_p"], lp["A_ann"]
    return {
        "head_area_m2": r(A_p), "annulus_area_m2": r(A_ann),
        "beta_Pa": lp["beta"], "head_dead_length_L0h_m": lp["L0h"], "rod_dead_length_L0r_m": lp["L0r"],
        "stroke_m": geo.stroke,
        "k_out_N_m (series rod, frame, concrete)": r(lp["k_out"]),
        "axial_law": "F = k2(s) (s_ref - s) + c (ds_ref - ds) moving; locked: F_lock + k2 dc + (k1 - k2) min(dc, dc_knee)",
        "k_of_s_table": tab,
        "rod_side_lock_rule": ("k_h, k_r frozen at s_lock (L2b; L1-R uses e_op, Q-D7); p_r0 = actuator.rod_side."
                               "p_r0_after_extend_Pa (RULE 2 bar g) after an extension, p_r0_after_retract_Pa after a "
                               "retraction; release lock -> move: dF_R exp(-t / release_tau_s) (0.05 s); "
                               "head-side floor not reached (lift-off leaves p_h > 0, checked in V4 / D2)"),
        "p_r0_after_extend_Pa": r(lp["p_r0_ext"]), "p_r0_after_retract_Pa": r(lp["p_r0_ret"]),
        "p_floor_gauge_Pa": lp["p_floor_g"],
        "c_oil_lock_N_s_m (zeta 0.03 on k1(e_op), = L1 cn LOCK)": r(lp["c_lock"]),
        "c_oil_moving_N_s_m (zeta 0.10 on k2(e_op), concrete in series)": r(lp["c_mov"]),
        "c_oil_head_only_regression_N_s_m (zeta 0.03 on k2(e_op))": r(lp["c_head"]),
        "YAML_before_rev33": {"oil_damping_N_s_m (zeta 0.03 on oil+rod+frame, no concrete)": r(lp["c_old"]),
                              "oil_damping_moving_N_s_m (zeta 0.10, no concrete)": r(lp["c_mov_old"])},
        "damping_mass_kg": r(lp["m_damp"]),
        "saturation_moving_210bar": {"extend_N (A_p)": r(lp["F_ext"]), "retract_N (A_ann)": r(lp["F_ret"]),
                                     "rule": ("per physics step on the force-law output F (no rod inertia in it: the "
                                              "rod is its own body); F >= F_ext and u > 0 -> s_ref decelerates to stop "
                                              "in 2 ms (law C), F <= -F_ret and u < 0 likewise")},
        "locked_limits": {"350bar_force_N": r(lp["F_lock"]), "345bar_warning_force_N (head only, p_r 0)": r(P_WARN_PA * A_p),
                          "pressure_head": "p_h = (F + p_r A_ann) / A_p, p_r = max(p_floor, p_r0 - r dF / A_ann) locked",
                          "rod_side_limit": "p_r <= 350 bar (H-2, ASSUMPTION manufacturer)"},
        "lateral_bushing": {"k_t_N_m (= L1 kt)": r(lp["kt"]), "c_t_actual_N_s_m": r(lp["ct"]),
                            "c_t_chrono_input_N_s_m (= c_t / 2)": r(lp["ct"] / 2),
                            "location": ("between barrel (body) and rod, drive guide x, y freed, rod rotations locked "
                                         "to the barrel; with the NSC sphere stuck on the floor the lateral spring acts "
                                         "at the contact point (pad bottom), not at the ball centre (L1 rev. 13)")},
        "rod_mass_kg": r(lp["m_rod"]),
        "checks_vs_YAML": {k: r(v, 3) for k, v in {**lp["checks"], **lp["checks_l2b"]}.items()},
    }


# ------------------------------------------------------------------ linear slope statics (same as static_slope_10dof)
class SlopeSystem:
    """Levelled superstructure on a sloped rigid floor: body 6 DoF about its CoM + 4 rod vertical DoF.

    Assembly copied from dyn_model.static_slope_10dof (checked in __init__): oil (axial) spring ko between the
    attachment point and the rod, rigid contact (KC_RIGID along the normal, k_t in the plane) at the sphere contact
    point (ball centre - hb n). Rod x, y with the body (guide); the lateral spring therefore acts at the contact point.
    """

    def __init__(self, body, geo, ext, kt, pitch_deg, roll_deg):
        self.body, self.geo, self.ext = body, geo, np.asarray(ext, float)
        sx = -math.tan(math.radians(pitch_deg)); sy = math.tan(math.radians(roll_deg))
        nrm = np.array([-sx, -sy, 1.0]); nrm /= np.linalg.norm(nrm)
        self.nrm, self.pitch, self.roll = nrm, pitch_deg, roll_deg
        P_n = np.outer(nrm, nrm)
        hb = dm.ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"]
        self.Kc_part = np.zeros((10, 10))
        self.b, self.G, self.Kc = [], [], []
        for i in range(4):
            d_att = np.array([*geo.pad_xy[i], geo.attach_z[i]]) - body.com
            d_ball = np.array([*geo.pad_xy[i], geo.pad_z_retracted[i] - self.ext[i] + hb]) - body.com
            _, _, az_att = dm.a_vec(d_att)
            ax_b, ay_b, _ = dm.a_vec(d_ball - hb * nrm)
            b = np.zeros(10); b[:6] = az_att; b[6 + i] = -1.0
            G = np.zeros((3, 10)); G[0, :6] = ax_b; G[1, :6] = ay_b; G[2, 6 + i] = 1.0
            Kc = KC_RIGID * P_n + kt[i] * (np.eye(3) - P_n)
            self.Kc_part += G.T @ Kc @ G
            self.b.append(b); self.G.append(G); self.Kc.append(Kc)
        self.f_grav = np.zeros(10)
        self.f_grav[2] = -body.mass * geo.g
        self.f_grav[6:] = -geo.rod_mass * geo.g

    def K(self, ko):
        K = self.Kc_part.copy()
        for i in range(4):
            K += ko[i] * np.outer(self.b[i], self.b[i])
        return K

    def solve(self, ko, delta=None, f_ext=None):
        """Linear response to the oil prestrain delta (4,) and the generalised force f_ext (10,) (gravity not added)."""
        delta = np.zeros(4) if delta is None else np.asarray(delta, float)
        f = np.zeros(10) if f_ext is None else np.asarray(f_ext, float)
        q = np.linalg.solve(self.K(ko), f + sum(ko[i] * delta[i] * self.b[i] for i in range(4)))
        F = np.array([ko[i] * (delta[i] - self.b[i] @ q) for i in range(4)])
        N = np.array([-(self.Kc[i] @ (self.G[i] @ q)) @ self.nrm for i in range(4)])
        return q, F, N

    def place_and_settle(self, ko):
        return self.solve(ko, f_ext=self.f_grav)

    def vertical_force(self, xy):
        """Generalised force of a unit downward force at body point (x, y) (height irrelevant for a vertical force)."""
        f = np.zeros(10)
        _, _, az = dm.a_vec(np.array([xy[0], xy[1], 0.0]) - self.body.com)
        f[:6] = -az
        return f


def piecewise_path(sysm, lp, k_h, k_r, state, F0, N0, delta_unit=None, f_unit=None, F_min=None, lam_max=1e9,
                   p_r0=None, stop_at_liftoff=True):
    """Piecewise-linear path of the L1-R / L2b statics under lam x (delta_unit, f_unit) from the settled state.

    state per leg: "LOCK" (rod side armed, anchor = start), "HEAD" (locked, rod side off: L1 regression), "MOVE"
    (valve open, head only, p_r = 0 g). Events (first lam each): knee (per leg), F_min (cylinder force), lift-off
    (contact normal 0), p_h = 345 / 350 bar, p_r = 350 bar. Exact for the piecewise-linear model up to lift-off.
    """
    A_p, A_ann, k_out = lp["A_p"], lp["A_ann"], lp["k_out"]
    knee = (p_r0 - lp["p_floor_g"]) * A_ann * (k_h + k_r) / k_r
    ratio = k_r / (k_h + k_r)
    st = list(state)
    lam = 0.0
    F, N = np.array(F0, float), np.array(N0, float)
    dF_lock = np.zeros(4)
    first = {}
    done = set()
    knees = []
    p_r_max = p_r0.copy()

    def pr(i, Fl):
        if st[i] == "LOCK":
            return p_r0[i] - ratio[i] * Fl / A_ann[i]
        if st[i] == "KNEE":
            return lp["p_floor_g"]
        return 0.0

    for _ in range(40):
        ko = np.array([dm.series(k_h[i] + k_r[i], k_out[i]) if st[i] == "LOCK" else dm.series(k_h[i], k_out[i])
                       for i in range(4)])
        _, dF, dN = sysm.solve(ko, delta_unit, f_unit)
        cand = []
        for i in range(4):
            if st[i] == "LOCK" and dF[i] > 0:
                cand.append(((knee[i] - dF_lock[i]) / dF[i], "knee", i))
            if F_min is not None and dF[i] < 0 and F[i] > F_min:
                cand.append(((F[i] - F_min) / -dF[i], "F_min", i))
            if dN[i] < 0:
                cand.append((N[i] / -dN[i], "liftoff", i))
            # head pressure p_h = (F + p_r A_ann) / A_p, linear in lam inside the segment
            ph = (F[i] + pr(i, dF_lock[i]) * A_ann[i]) / A_p[i]
            dph = (dF[i] * (1 - ratio[i]) if st[i] == "LOCK" else dF[i]) / A_p[i]
            if dph > 0:
                for lab, lim in (("p_h_345bar", P_WARN_PA), ("p_h_350bar", P_LOCK_PA)):
                    if ph < lim:
                        cand.append(((lim - ph) / dph, lab, i))
            if st[i] == "LOCK" and dF[i] < 0:
                prr = pr(i, dF_lock[i]); dpr = -ratio[i] * dF[i] / A_ann[i]
                if prr < P_LOCK_PA:
                    cand.append(((P_LOCK_PA - prr) / dpr, "p_r_350bar", i))
        cand = [c for c in cand if c[0] >= -1e-12 and (c[1], c[2]) not in done]
        if not cand:
            break
        dl, lab, i = min(cand, key=lambda c: c[0])
        dl = max(dl, 0.0)
        if lam + dl > lam_max:
            dl = lam_max - lam
            lab = "lam_max"
        lam += dl
        F = F + dl * dF; N = N + dl * dN; dF_lock = dF_lock + dl * dF
        for j in range(4):
            if st[j] == "LOCK":
                p_r_max[j] = max(p_r_max[j], pr(j, dF_lock[j]))
        if lab == "lam_max":
            break
        if lab == "knee":
            st[i] = "KNEE"
            knees.append({"leg": dm.LEG_NAMES[i], "lam": lam})
            continue
        done.add((lab, i))
        if lab not in first:
            first[lab] = {"lam": lam, "leg": dm.LEG_NAMES[i], "F_cyl_N": F.copy(), "N_contact_N": N.copy()}
        if lab == "liftoff" and stop_at_liftoff:
            break
    return {"events": first, "knees": knees, "p_r_max_Pa": p_r_max, "lam_end": lam, "F_end": F, "N_end": N}


def _first_or_none(ev, key, scale=1.0, nd=5):
    if key not in ev:
        return None
    return {"value": r(ev[key]["lam"] * scale, nd), "leg": ev[key]["leg"]}


# ------------------------------------------------------------------ levels: statics, modes, single-leg thresholds
def levels_block(p, geo, lp, ref_l2b):
    g = geo.g
    e_op = lp["e_op"]
    out = {}
    F_min = float(p["control"]["F_min_cylinder_N"])
    k_h, k_r = lp["k_h_f"](e_op), lp["k_r_f"](e_op)
    k2, k1 = lp["k2_f"](e_op), lp["k1_f"](e_op)
    for lvl in dm.LEVELS:
        b = dm.body_from_params(p, lvl)
        bw = dm.body_with_rods(p, geo, lvl, np.full(4, 0.0) + e_op)
        W_tot = bw.mass * g
        sysm = SlopeSystem(b, geo, np.full(4, 0.0) + e_op, lp["kt"], 0.0, 0.0)
        q0, F0, N0 = sysm.place_and_settle(k2)
        ref = ref_l2b["levels"][lvl]
        d_cf = float(np.abs(N0 - np.array(ref["contact_force_N"])).max())
        d_cy = float(np.abs(F0 - np.array(ref["cylinder_force_N"])).max())
        if d_cf > 1.0 or d_cy > 1.0:
            raise RuntimeError(f"{lvl}: statics differ from reference.json L2b-NSC block ({d_cf}, {d_cy} N)")
        ent = {"contact_force_N (V1)": r(N0), "cylinder_force_N": r(F0),
               "axial_spring_compression_mm (V2, F / k2(e_op))": r(F0 / k2 * 1e3),
               "static_attitude_deg (roll, pitch) (V3)": r(np.degrees(q0[3:5]), 4),
               "check_vs_reference_L2b_NSC_block_max_abs_diff_N": r(max(d_cf, d_cy), 3)}
        # modes: LOCK (k1, judged) and FLOOR (k2, head only, reported); damping c_lock in both (Q-D3 analogue)
        ch = lp["ct"]
        modes = {}
        for st_name, ko in (("LOCK", k1), ("FLOOR", k2)):
            M, K, C, labels, _ = dm.model_10dof(b, geo, np.full(4, 0.0) + e_op, ko=ko, kc=np.full(4, KC_RIGID),
                                                kh=lp["kt"], co=lp["c_lock"], cc=np.zeros(4), ch=ch)
            _, f_und, Phi, cls, orth = dm.modal(M, K, labels)
            fd, zd = dm.complex_modes(M, K, C)
            modes[st_name] = {"f_undamped_Hz (first 6)": r(f_und[:6], 5), "f_damped_Hz (first 6)": r(fd[:6], 5),
                              "zeta (first 6)": r(zd[:6], 3), "mode_content": cls[:6],
                              "orthogonality_err": r(orth, 3)}
            if st_name == "LOCK":
                Ph = Phi[:, :6].copy()
                for jm in range(6):
                    imax = int(np.argmax(np.abs(Ph[:6, jm])))
                    if Ph[imax, jm] < 0:
                        Ph[:, jm] *= -1.0
                modes["LOCK"]["mode_shapes"] = {
                    "coordinates": labels,
                    "reference_point_m (superstructure CoM)": r(b.com),
                    "units": "translations m, rotations rad, per sqrt(kg); rod rows = absolute vertical rod displacement (up +)",
                    "Phi (rows = coordinates, cols = first 6 modes)": r(Ph, 12),
                    "mass_matrix": r(M, 12),
                    "projection": "eta = Phi^T M q from the static equilibrium; sign: largest body component positive"}
            if st_name == "FLOOR":
                d_f = float(np.max(np.abs(np.array(f_und[:6]) / np.array(ref["f_undamped_Hz"][:6]) - 1)))
                if d_f > 1e-4:
                    raise RuntimeError(f"{lvl}: FLOOR modes differ from reference.json L2b-NSC block ({d_f})")
                modes["FLOOR"]["check_vs_reference_L2b_NSC_f_undamped (rel)"] = r(d_f, 3)
        # ball-centre lateral variant (information: free-swivel pad), LOCK
        M, K, C, labels, _ = _model_10dof_ball(b, geo, e_op, k1, lp["kt"], lp["c_lock"], ch)
        _, f_b, _, _, _ = dm.modal(M, K, labels)
        fdb, zdb = dm.complex_modes(M, K, C)
        modes["LOCK_lateral_at_ball_centre (information)"] = {"f_undamped_Hz (first 6)": r(f_b[:6], 5),
                                                             "zeta (first 6)": r(zdb[:6], 3)}
        ent["modes"] = modes
        # single-leg thresholds: head only (= reference.json L2b block) and L1-R (tested leg moving, others LOCK)
        thr = {}
        for i, nm in enumerate(dm.LEG_NAMES):
            for sgn, lab in ((1, "+"), (-1, "-")):
                du = np.zeros(4); du[i] = sgn * 1e-3   # per mm
                res = {}
                for case, state in (("head_only", ["HEAD"] * 4),
                                    ("L1R_after_extend", ["LOCK" if j != i else "MOVE" for j in range(4)])):
                    pw = piecewise_path(sysm, lp, k_h, k_r, state, F0, N0, delta_unit=du, F_min=F_min,
                                        p_r0=lp["p_r0_ext"])
                    ev = pw["events"]
                    res[case] = {"F_min_mm": _first_or_none(ev, "F_min"), "liftoff_mm": _first_or_none(ev, "liftoff"),
                                 "knees (leg, mm)": [[k["leg"], r(k["lam"], 4)] for k in pw["knees"]]}
                thr[nm + lab] = res
        ent["single_leg_thresholds_mm (V5 / V6 / V14 level)"] = thr
        # small-signal FL+ sensitivity (V5): FL moving, others LOCK
        _, dF_h, _ = sysm.solve(k2, np.array([1e-3, 0, 0, 0]))
        ko_l = np.array([k2[0], k1[1], k1[2], k1[3]])
        _, dF_l, _ = sysm.solve(ko_l, np.array([1e-3, 0, 0, 0]))
        ent["dF_cyl_per_mm_FL_N"] = {"head_only": r(dF_h), "L1R_small_signal (FL moving, others LOCK)": r(dF_l)}
        ent["F_min_cylinder_N"] = F_min
        ent["mass_for_damping_kg (superstructure + 4 rods)"] = r(bw.mass)
        ent["W_total_N"] = r(W_tot)
        out[lvl] = ent
    return out


def _model_10dof_ball(body, geo, e_op, ko, kh, co, ch):
    """dm.model_10dof with the lateral spring at the ball centre instead of the pad bottom (rigid contact)."""
    hb = dm.ASSUMPTIONS["swivel_ball_height_above_pad_bottom_m"]
    ext = np.full(4, 0.0) + e_op
    M, K, C, labels, Fc = dm.model_10dof(body, geo, ext, ko=ko, kc=np.full(4, KC_RIGID), kh=np.zeros(4),
                                         co=co, cc=np.zeros(4), ch=np.zeros(4))
    for i in range(4):
        d = np.array([*geo.pad_xy[i], geo.pad_z_retracted[i] - ext[i] + hb]) - body.com
        ax, ay, _ = dm.a_vec(d)
        for a in (ax, ay):
            aa = np.zeros(10); aa[:6] = a
            K += kh[i] * np.outer(aa, aa); C += ch[i] * np.outer(aa, aa)
    return M, K, C, labels, Fc


# ------------------------------------------------------------------ V4 (NSC): lift with a rigid crawler
def v4_block(p, geo, lp, ref_res):
    """Dynamic touch times of the L2b-NSC lift (rigid crawler limit kn_total x1e3, layout D).

    Same damped vertical 3-DoF as run_reference.dynamic_touch, with the L2b leg: pad spring k2(e(t)) (moving, head
    only), dashpot c_moving, and the hanging-rod stretch m_rod g / k2(e) (rod lower by it before the touch).
    """
    g, v, touch, xy = geo.g, geo.v_max, geo.touch_extension, geo.pad_xy
    e_op = lp["e_op"]
    lay = ref_res["lift_V4_compliant_crawler"]["layouts"][rr.V4_LAYOUT_D_RIGID]
    ref_dyn = np.array(lay["dynamic_events_s"]["touch_s (FL, FR, RL, RR)"])
    ref_qs = np.array(lay["quasi_static_events_s"]["touch_s (FL, FR, RL, RR)"])
    t_from, t_to = lay["dynamic_events_s"]["meta"]["window_s"]
    xy_d, k_d, _ = dm.crawler_points(p); gap = dm.crawler_gaps(p); n_rol = int((gap <= 0).sum())
    bw = dm.body_with_rods(p, geo, "top", np.full(4, 0.0) + e_op)
    c_tot = dm.crawler_damping_total(float(p["contact"]["crawler"]["kn_total_N_m"]), bw.mass)
    kc = k_d * rr.RIGID_CRAWLER_SCALE
    cc = np.full(len(xy_d), c_tot * math.sqrt(rr.RIGID_CRAWLER_SCALE) / n_rol)
    b0 = dm.body_with_rods(p, geo, "top", np.zeros(4))
    W, cg = b0.mass * g, b0.com[:2]
    a = np.array([1.0, cg[1], -cg[0]])
    M = b0.mass * np.outer(a, a); M[1:, 1:] += b0.inertia[:2, :2]
    A = dm.support_matrix(np.vstack([xy, xy_d]))
    w = np.array([W, W * cg[1], -W * cg[0]])
    n_cr = len(xy_d)

    def run(k_fun, c_pad, hang, method="DOP853", max_step=1e-3):
        def comp(t, y):
            e = np.minimum(v * t, e_op)
            ed = np.where(v * t < e_op, v, 0.0)
            off = lp["m_rod"] * g / k_fun(e) if hang else 0.0
            c = np.concatenate([e + off - touch, -gap]) - A @ y[:3]
            cdot = np.concatenate([ed, np.zeros(n_cr)]) - A @ y[3:]
            return c, cdot, e

        def rhs(t, y):
            c, cdot, e = comp(t, y)
            k = np.concatenate([k_fun(e), kc]); cd = np.concatenate([c_pad, cc])
            Fz = np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)
            return np.concatenate([y[3:], np.linalg.solve(M, A.T @ Fz - w)])

        evs = [(lambda t, y, i=i: comp(t, y)[0][i]) for i in range(4)]
        _, q0, _ = dm.static_unilateral(xy_d, kc, -gap, W, cg)
        y0 = np.concatenate([q0, np.zeros(3)])
        sol = solve_ivp(rhs, (t_from, t_to), y0, method=method, rtol=V4_SOLVER["rtol"], atol=V4_SOLVER["atol"],
                        max_step=max_step, events=evs)
        if sol.status != 0:
            raise RuntimeError(sol.message)
        out = []
        for i in range(4):
            up = [t for t, y in zip(sol.t_events[i], sol.y_events[i], strict=True) if comp(t, y)[1][i] > 0]
            out.append(up[0] if up else float("nan"))
        return np.array(out)

    def quasi_static(k_fun, hang):
        allxy = np.vstack([xy, xy_d])

        def act(t):
            e = np.minimum(v * t, e_op)
            off = lp["m_rod"] * g / k_fun(e) if hang else 0.0
            _, _, a_ = dm.static_unilateral(allxy, np.concatenate([k_fun(e), kc]),
                                            np.concatenate([e + off - touch, -gap]), W, cg)
            return a_[:4]

        tg = np.arange(t_from, t_to, 1e-3)
        flags = np.array([act(t) for t in tg])
        res = []
        for i in range(4):
            ch = np.where(flags[1:, i] & ~flags[:-1, i])[0]
            lo, hi = tg[ch[0]], tg[ch[0] + 1]
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                lo, hi = (lo, mid) if act(mid)[i] else (mid, hi)
            res.append(0.5 * (lo + hi))
        return np.array(res)

    k_L1 = lp["k2"]
    c_L1 = lp["cn"]
    t0 = time.perf_counter()
    rep = run(lambda e: k_L1, c_L1, False)
    l2b = run(lp["k2_f"], lp["c_mov"], True)
    l2b_h = run(lp["k2_f"], lp["c_mov"], True, max_step=5e-4)
    l2b_r = run(lp["k2_f"], lp["c_mov"], True, method="Radau")
    l2b_nohang = run(lp["k2_f"], lp["c_mov"], False)
    sens = {f"moving_zeta_{z:g}": run(lp["k2_f"], lp["c_mov"] * z / lp["zeta_mov"], True) for z in (0.05, 0.2)}
    qs = quasi_static(lp["k2_f"], True)
    wall = time.perf_counter() - t0
    if np.abs(np.array(r(rep, 5)) - ref_dyn).max() > 0:   # reference.json printed to 5 significant digits
        raise RuntimeError(f"V4 replica differs from reference.json dynamic_events_s: {rep} vs {ref_dyn}")
    return {
        "basis": ("L2b-NSC V4 basis (rev. 33): touch_s of 'L2b_dynamic' per leg +- 0.05 s; quasi-static reference "
                  "only. Layout D, rigid crawler limit (kn_total x1e3) as reference.json lift_V4_compliant_crawler"),
        "L2b_dynamic": {"touch_s (FL, FR, RL, RR)": r(l2b, 5), "first_touch_leg": dm.LEG_NAMES[int(np.argmin(l2b))],
                        "pad_dashpot_N_s_m (c_moving)": r(lp["c_mov"]),
                        "pad_spring": "k2(e(t)) head only (moving legs), hanging-rod stretch m_rod g / k2(e) included",
                        "max_abs_diff_vs_max_step_5e-4_s": r(float(np.abs(l2b - l2b_h).max()), 3),
                        "max_abs_diff_vs_Radau_s": r(float(np.abs(l2b - l2b_r).max()), 3)},
        "L2b_quasi_static_touch_s (FL, FR, RL, RR)": r(qs, 5),
        "L2b_without_rod_hanging_stretch_touch_s": r(l2b_nohang, 5),
        "moving_zeta_sensitivity_touch_s": {k: r(v_, 5) for k, v_ in sens.items()},
        "L1_basis_replica_touch_s (= reference.json dynamic_events_s)": r(rep, 5),
        "reference.json_quasi_static_touch_s": r(ref_qs, 5),
        "L2b_minus_L1_basis_s": r(l2b - rep, 3),
        "leg_stop_s (FL, FR, RL, RR)": r(e_op / v, 5),
        "integrator": dict(V4_SOLVER, events="pad compression zero crossings", window_s=[t_from, t_to]),
        "wall_s": r(wall, 3),
    }


# ------------------------------------------------------------------ slope cases (V12 rule, V14)
def levelled_extension(geo, roll_deg, pitch_deg, clearance):
    """Copy of run_reference.levelled_extension (nested there)."""
    sx = -math.tan(math.radians(pitch_deg)); sy = math.tan(math.radians(roll_deg))
    (x0, x1), (y0, y1) = geo.crawler_xy_box
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    H = np.max(sx * corners[:, 0] + sy * corners[:, 1]) + clearance - geo.crawler_bottom_z
    return geo.pad_z_retracted + H - (sx * geo.pad_xy[:, 0] + sy * geo.pad_xy[:, 1])


def max_slope(geo, direction_deg, clearance, stroke=None):
    stroke = geo.stroke if stroke is None else stroke
    lo, hi = 0.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        e = levelled_extension(geo, mid * math.sin(math.radians(direction_deg)), mid * math.cos(math.radians(direction_deg)),
                               clearance)
        lo, hi = (mid, hi) if (e.min() >= 0 and e.max() <= stroke) else (lo, mid)
    return lo


def v14_block(p, geo, lp, ref_v14):
    A_ = dm.ASSUMPTIONS
    clr = A_["crawler_clearance_m"]
    b = dm.body_from_params(p, "top")
    F_min = float(p["control"]["F_min_cylinder_N"])
    i_t, sgn = dm.LEG_NAMES.index(V14_TEST[0]), V14_TEST[1]
    out = {"method": ("L2b-NSC linear statics on the sloped floor (V12 rule: place and settle with the head-only "
                      "k2(e_i), then lock with dc = 0), then the tested leg RL moves (head only, s_ref +) and the other "
                      "three are LOCK after an extension (rod side armed, p_r0 2 bar, k_h, k_r at their own e_i); "
                      "piecewise-linear exact up to the first lift-off. head_only = rev. 5 method (rod side off)."),
           "V14_test_leg": "RL+", "slope_limits_deg": {}, "cases": {}}
    smeas = float(p["sensors"]["stroke"]["measurable_max_m"])
    for c_mm in (0.0, clr):
        out["slope_limits_deg"][f"clearance_{int(round(c_mm * 1e3))}mm"] = {
            "stroke_0.70": {"pitch+": r(max_slope(geo, 0, c_mm), 4), "pitch-": r(max_slope(geo, 180, c_mm), 4),
                            "roll+": r(max_slope(geo, 90, c_mm), 4), "diag45": r(max_slope(geo, 45, c_mm), 4)},
            "sensor_max_0.6948": {"pitch+": r(max_slope(geo, 0, c_mm, smeas), 4),
                                  "pitch-": r(max_slope(geo, 180, c_mm, smeas), 4),
                                  "roll+": r(max_slope(geo, 90, c_mm, smeas), 4),
                                  "diag45": r(max_slope(geo, 45, c_mm, smeas), 4)}}
    out["slope_basis"] = (f"rev. 33 suppl. 1: V14 slope = max levelling slope with every extension <= the stroke "
                          f"sensor end {smeas} m (sensors.stroke.measurable_max_m, = software stroke-end basis), "
                          f"x {SLOPE_SCALE}; was the mechanical stroke 0.70 m (piston-stop margin, 5.20.8)")
    out["column_length_rule"] = ("k_h = beta A_p / (L0h + s_lock), k_r = beta A_ann / (s_max - s_lock + L0r) with "
                                 "s_lock = s_ref at the locking instant (= placement extension of place-and-settle); "
                                 "not the rod-body coordinate s = s_ref - F / k2 (that gives f1 -0.7..-1.7 %, f6 -1.6..-2.4 %)")
    for name, d in V14_CASES:
        s = 0.0 if name == "level" else max_slope(geo, d, clr, smeas) * SLOPE_SCALE
        ro, pi = s * math.sin(math.radians(d)), s * math.cos(math.radians(d))
        ext = levelled_extension(geo, ro, pi, clr)
        sysm = SlopeSystem(b, geo, ext, lp["kt"], pi, ro)
        k_h, k_r = lp["k_h_f"](ext), lp["k_r_f"](ext)
        k2 = dm.series(k_h, lp["k_out"])
        _, F0, N0 = sysm.place_and_settle(k2)
        chk = dm.static_slope_10dof(b, geo, ext, k2, np.full(4, KC_RIGID), lp["kt"], slope_pitch_deg=pi, slope_roll_deg=ro)
        d_chk = float(max(np.abs(chk["F_cyl"] - F0).max(), np.abs(chk["N"] - N0).max()))
        if d_chk > 0.5:
            raise RuntimeError(f"{name}: SlopeSystem differs from dm.static_slope_10dof ({d_chk} N)")
        du = np.zeros(4); du[i_t] = sgn * 1e-3
        res = {}
        for case, state in (("head_only", ["HEAD"] * 4),
                            ("L1R_after_extend", ["LOCK" if j != i_t else "MOVE" for j in range(4)])):
            pw = piecewise_path(sysm, lp, k_h, k_r, state, F0, N0, delta_unit=du, F_min=F_min, p_r0=lp["p_r0_ext"])
            ev = pw["events"]
            ko0 = np.array([dm.series(k_h[j] + k_r[j], lp["k_out"][j]) if state[j] == "LOCK" else k2[j] for j in range(4)])
            _, dF0, _ = sysm.solve(ko0, du)
            pw1 = piecewise_path(sysm, lp, k_h, k_r, state, F0, N0, delta_unit=du, lam_max=1.0, p_r0=lp["p_r0_ext"])
            res_sec = pw1["F_end"] - F0
            res[case] = {"S_own_small_signal_kN_per_mm": r(float(dF0[i_t] * sgn * 1e-3), 5),
                         "dF_cyl_secant_+1mm_N (judged, crosses the knees)": r(res_sec),
                         "dF_cyl_per_mm_small_signal_N": r(dF0 * sgn),
                         "F_min_threshold_mm": _first_or_none(ev, "F_min"),
                         "liftoff_threshold_mm": _first_or_none(ev, "liftoff"),
                         "knees (leg, mm)": [[k["leg"], r(k["lam"], 4)] for k in pw["knees"]]}
        old = ref_v14["cases"].get(name, {}).get("single_leg", {}).get("RL+", {})
        if old:
            # regression of the code path: head-only RL+ on the old slope (stroke 0.70 basis) = V14_rev5
            s_o = 0.0 if name == "level" else max_slope(geo, d, clr) * SLOPE_SCALE
            ro_o, pi_o = s_o * math.sin(math.radians(d)), s_o * math.cos(math.radians(d))
            ext_o = levelled_extension(geo, ro_o, pi_o, clr)
            sys_o = SlopeSystem(b, geo, ext_o, lp["kt"], pi_o, ro_o)
            kh_o, kr_o = lp["k_h_f"](ext_o), lp["k_r_f"](ext_o)
            _, F0_o, N0_o = sys_o.place_and_settle(dm.series(kh_o, lp["k_out"]))
            ev_o = piecewise_path(sys_o, lp, kh_o, kr_o, ["HEAD"] * 4, F0_o, N0_o, delta_unit=du, F_min=F_min,
                                  p_r0=lp["p_r0_ext"])["events"]
            dd = max(abs(r(ev_o["F_min"]["lam"], 5) - old["F_min_threshold_mm"]),
                     abs(r(ev_o["liftoff"]["lam"], 5) - old["liftoff_threshold_mm"]))
            if dd > 2e-3:
                raise RuntimeError(f"{name}: head-only RL+ differs from actuator_L2_feasibility V14_rev5 ({dd} mm)")
            res["head_only"]["check_vs_V14_rev5_on_its_slope_max_abs_diff_mm"] = r(dd, 3)
        # piston-stop margin of the locked legs (stop at s_max): two placement conventions, and the largest
        # piston travel toward the stop (unloading, LOCK pre-knee dx = -dF / (k_h + k_r)) up to lift-off
        pwL = piecewise_path(sysm, lp, k_h, k_r, ["LOCK" if j != i_t else "MOVE" for j in range(4)], F0, N0,
                             delta_unit=du, F_min=F_min, p_r0=lp["p_r0_ext"])
        dFl = pwL["F_end"] - F0
        to_stop = np.where(dFl < 0, -dFl / (k_h + k_r), 0.0)
        to_stop[i_t] = 0.0
        res["piston_stop_margin_mm"] = {
            "model_convention (piston = s_ref - F / k_h, s_ref = placement extension)": r((geo.stroke - ext + F0 / k_h) * 1e3, 4),
            "exact_geometric_pose (piston = ext + F / k_out)": r((geo.stroke - ext - F0 / lp["k_out"]) * 1e3, 4),
            "piston_travel_toward_stop_at_liftoff (upper bound, pre-knee)": r(to_stop * 1e3, 4),
            "note": "stop not reached if travel < margin in both conventions"}
        if np.any(to_stop * 1e3 >= (geo.stroke - ext - F0 / lp["k_out"]) * 1e3):
            raise RuntimeError(f"{name}: piston reaches the stroke stop before lift-off")
        # rod dead length L0r sensitivity (record only; judged at the YAML L0r)
        sens = {}
        for L0r in (0.02, 0.035, 0.05, 0.075, 0.10):
            kr_s = lp["beta"] * lp["A_ann"] / (geo.stroke - ext + L0r)
            st_l = ["LOCK" if j != i_t else "MOVE" for j in range(4)]
            ev_s = piecewise_path(sysm, lp, k_h, kr_s, st_l, F0, N0, delta_unit=du, F_min=F_min, p_r0=lp["p_r0_ext"])
            pw1s = piecewise_path(sysm, lp, k_h, kr_s, st_l, F0, N0, delta_unit=du, lam_max=1.0, p_r0=lp["p_r0_ext"])
            kL_s = dm.series(k_h + kr_s, lp["k_out"])
            Ms, Ks, _, lab_s, _ = dm.model_10dof(b, geo, ext, ko=kL_s, kc=np.full(4, KC_RIGID), kh=lp["kt"])
            f_s = dm.modal(Ms, Ks, lab_s)[1][:6]
            sens[f"L0r_{L0r:g}"] = {"secant_+1mm_RL_kN": r(float(pw1s["F_end"][i_t] - F0[i_t]) * 1e-3, 4),
                                    "F_min_mm": _first_or_none(ev_s["events"], "F_min"),
                                    "liftoff_mm": _first_or_none(ev_s["events"], "liftoff"),
                                    "f_Hz (first 6, undamped)": r(f_s, 5)}
        res["L0r_sensitivity (record only)"] = sens
        kL = dm.series(k_h + k_r, lp["k_out"])
        M, K, C, labels, _ = dm.model_10dof(b, geo, ext, ko=kL, kc=np.full(4, KC_RIGID), kh=lp["kt"],
                                            co=lp["c_lock"], cc=np.zeros(4), ch=lp["ct"])
        f_lock = dm.modal(M, K, labels)[1][:6]
        M2, K2, _, labels2, _ = dm.model_10dof(b, geo, ext, ko=k2, kc=np.full(4, KC_RIGID), kh=lp["kt"])
        f_head = dm.modal(M2, K2, labels2)[1][:6]
        room = (geo.stroke - ext) if sgn > 0 else ext
        out["cases"][name] = {
            "ground_roll_pitch_deg": r([ro, pi], 5), "extension_m": r(ext, 5),
            "stroke_room_RL+_mm": r(float(room[i_t] * 1e3), 5),
            "F_cyl_place_and_settle_N": r(F0), "N_contact_normal_N": r(N0),
            "RL+": res,
            "f_Hz_LOCK (first 6, rocking judged +-3 %)": r(f_lock, 5), "f_Hz_head_only (first 6)": r(f_head, 5),
            "check_vs_static_slope_10dof_N": r(d_chk, 3)}
    return out


# ------------------------------------------------------------------ time step
def time_step_block(lp, levels):
    top = levels["top"]["modes"]["LOCK"]
    f = np.array(top["f_damped_Hz (first 6)"]); z = np.array(top["zeta (first 6)"])
    bound = 0.2 * z / (2 * math.pi * f)
    s0 = lp["s_tab"]["0"]; f_rod0 = np.sqrt(lp["k2_f"](s0) / lp["m_rod"]) / (2 * math.pi)
    f_rodop = np.sqrt(lp["k2_f"](lp["e_op"]) / lp["m_rod"]) / (2 * math.pi)
    return {
        "rule": ("smaller of (a) T/50 of the rod on the axial spring with the contact open and (b) omega_i dt / 2 <= "
                 "0.1 zeta_i of modes 1-6 (LOCK, top; with the explicit / lagged force law the same size enters as "
                 "negative damping unless the predictor F(c_n + dc_n dt) is used)"),
        "rod_free_mode_Hz (s = 0, max)": r(f_rod0, 4), "rod_free_mode_Hz (e_op)": r(f_rodop, 4),
        "dt_T50_at_s0_s": r(float(1 / f_rod0.max() / 50), 4), "dt_T50_at_e_op_s": r(float(1 / f_rodop.max() / 50), 4),
        "numerical_damping_bound_per_mode_s (LOCK top)": r(bound, 4),
        "numerical_damping_bound_min_s": r(float(bound.min()), 4),
        "recommended_dt_s": 1e-4,
        "note": ("YAML simulation.L2b_NSC.dt_s 1e-4 s stays: (a) needs <= 1.0e-4 s while a rod hangs near s = 0 "
                 "(lift start) and (b) gives the bound above; transitions / references 1e-5 s"),
    }


def build_block(p=None, ref_res=None):
    t0 = time.perf_counter()
    p = dm.load_params() if p is None else p
    geo = dm.geometry_from_params(p)
    lp = leg_parameters(p, geo)
    ref_l2b = ref_res["chrono_test_references"]["L2b_NSC_force_motor_axial_spring_lateral_bushing"]
    out = {"meta": {
        "script": "04_scripts/01_dynamics/l2b_reference.py (via run_reference.py --with-l2b / --l2b-out)",
        "document": "00_docs/01_dynamics/dynamics_model.md rev. 33, 5.20",
        "frame": "body x forward, y left, z up; level body = world axes; gravity -z 9.80665 m/s^2",
        "forces": "cylinder force = oil force on the body (compression +); contact normal = cylinder + rod weight",
        "leg_order": list(dm.LEG_NAMES),
        "assumptions": ("beta 1.0 GPa, L0h 0.05 m, L0r 0.05 m, frame 1e9 N/m, Westergaard slab, p_r0 2 bar g after an "
                        "extension (RULE), p_floor 0.1 bar abs, zeta 0.03 locked (on k1) / 0.10 moving (on k2), "
                        "lateral bushing = L1 kt at the contact point, mu 0.5, rigid NSC contact (1e13 N/m)")}}
    out["leg_parameters"] = parameters_block(lp, geo)
    out["levels"] = levels_block(p, geo, lp, ref_l2b)
    # independent path: l1r_reference.quasi_static (L1-R V6, level floor) must give the same FL+- thresholds
    v6 = ref_res.get(l1r.L1R_KEY, {}).get("V5_V6_quasi_static", {}).get("top", {}).get("L1R (FL moving, others LOCK)")
    if v6:
        mine = out["levels"]["top"]["single_leg_thresholds_mm (V5 / V6 / V14 level)"]
        diffs = [abs(mine[f"FL{s}"]["L1R_after_extend"][k]["value"] - v6[f"V6 FL{s} {lab}"]["travel_mm"])
                 for s in ("+", "-") for k, lab in (("F_min_mm", "F_min"), ("liftoff_mm", "lift"))]
        if max(diffs) > 2e-3:
            raise RuntimeError(f"L1-R V6 thresholds differ from {l1r.L1R_KEY}: {diffs}")
        out["meta"]["cross_check_L1R_V6_max_abs_diff_mm"] = r(max(diffs), 3)
    out["time_step"] = time_step_block(lp, out["levels"])
    out["V4_NSC"] = v4_block(p, geo, lp, ref_res)
    out["V12_rule"] = ("reference = reference.json slope_V12/<case>/L2b_NSC (rev. 35: S7 Chrono topology, "
                       "dyn_model.static_slope_l2b_chrono_topology, axial ko = series(oil head, rod, frame, concrete) "
                       "at the levelled extension, kt barrel-rod horizontal, place and settle); "
                       "the rod-side law is armed (anchor taken) only after the gravity ramp and settle, so the V12 "
                       "values do not change")
    import json
    from pathlib import Path
    fe = json.loads((Path(dm.PROJECT_ROOT) / "06_analysis" / "00_dynamics" / "actuator_L2_feasibility.json")
                    .read_text(encoding="utf-8"))
    out["V14"] = v14_block(p, geo, lp, fe["A_extension_dependence"]["V14_rev5"])
    out["meta"]["runtime_s"] = round(time.perf_counter() - t0, 2)
    return out
