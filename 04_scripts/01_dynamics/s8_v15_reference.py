"""S8 V15 reference: seal friction (Coulomb) on the L2b-NSC legs with the rod-side law (dynamics_model.md rev. 39).

Replaces actuator_L2_feasibility.json / C_seal_friction / V15_rev5 for S8 (user decision U-S8-6, 2026-10-24).
Chrono-independent reduced model (no pychrono, no 03_src):

* statics: l2b_reference.SlopeSystem (superstructure 6 DoF + 4 rod DoF, rigid NSC contact = KC_RIGID, lateral
  bushing k_t at the contact point), level floor, top auger level, settled at e_op with the head-only k2 (gravity
  ramp), then every leg LOCKed at rest (rod side armed, dc = 0) and the friction armed (f = 0, stick);
* leg axial element (hydraulics s8_seal_friction_counterbalance.md 2.1): oil law G(c_oil) in parallel with a
  Coulomb element |f| <= F_s (static = kinetic, rigid stick), both in series with k_out (rod, frame, concrete),
  massless piston; F = k_out (s_p - s) = G + f, two-sensor net reading = G (= F - f);
* oil law (oil-only form of L2bRodSide, k_out -> inf): moving leg G = k_h(s_ref) c_oil (head only); locked leg
  G = G_lock + k_h dc + k_r min(dc, dc_knee), dc_knee = (p_r0 - p_floor) A_ann / k_r, k_h, k_r frozen at s_lock =
  e_op ("rod_side"); variant "head_only": locked G = G_lock + k_h dc (Chrono rod_side=False);
* F_s per leg: front = level L, rear = 0.833 L (U-S8-H2), constant in the run (U-S8-H1/H3).

The quasi-static path is piecewise linear between events (stick -> slip, slip -> stick, knee, F_min crossings,
lift-off); it is solved exactly segment by segment (active set per segment), the only approximation being the
moving leg's k_h(s_ref) (updated per segment, segment <= SEG_MAX; 'kh_fixed' turns the tracking off and then the
path is exact). Test (V15): FL s_ref extended at 0.1 mm/s (quasi-static), the other three legs locked.
  (a) up-sweep until the first pad contact force reaches 0 (unilateral contact, stop);
  (b) round trip 0 -> 10 mm -> 0 (reported with the lift-off margin along the path).
Also: F_s sweep for the pressure-only miss threshold (D-2), pressure-dependent friction at lift-off (spec 2.4),
rear = front sensitivity, F_s = 0 regression against reference.json / L2b_NSC_reference_rev33 single-leg thresholds.

Conventions: body x forward, y left, z up; gravity -9.80665 z; leg order FL FR RL RR; forces compression + (cylinder
force on the body = rod axial force); contact force N = F + rod weight; f + pushes the piston outward (piston sliding
inward -> f = +F_s); reading error eps = G - F = -f. Units SI inside, mm / kN / bar g in the report.
Run (project root, dynamics-dev activated): conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s8_v15_reference.py
Writes 06_analysis/00_dynamics/s8_v15_reference.json. Deterministic (no random numbers).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dyn_model as dm  # noqa: E402
import l2b_reference as l2b  # noqa: E402

OUT = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "s8_v15_reference.json"
LEVELS_KN = (0.0, 2.0, 4.0, 8.0)
REAR_SCALE = 0.8333            # U-S8-H2 (hydraulics 2.3: (110 + 90) / (130 + 110))
SEG_MAX = 1e-5                 # m of FL s_ref per segment (k_h(s_ref) update)
TOL = 1e-9                     # N, band-edge tolerance
SPEED = 1e-4                   # m/s, V15 FL speed (quasi-static here; the dashpot term is reported only)


def r(x, n=6):
    if isinstance(x, dict):
        return {k: r(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


class Model:
    def __init__(self, level="top"):
        p = dm.load_params()
        geo = dm.geometry_from_params(p)
        lp = l2b.leg_parameters(p, geo)
        self.p, self.geo, self.lp = p, geo, lp
        self.e_op = np.zeros(4) + np.asarray(lp["e_op"], float)
        self.body = dm.body_from_params(p, level)
        self.sysm = l2b.SlopeSystem(self.body, geo, self.e_op, lp["kt"], 0.0, 0.0)
        self.kh = lp["k_h_f"](self.e_op)
        self.kr = lp["k_r_f"](self.e_op)
        self.k2 = lp["k2_f"](self.e_op)
        self.k1 = lp["k1_f"](self.e_op)
        self.kout = np.asarray(lp["k_out"], float)
        self.A_p, self.A_ann = np.asarray(lp["A_p"], float), np.asarray(lp["A_ann"], float)
        self.p_r0 = np.asarray(lp["p_r0_ext"], float)
        self.p_floor = float(lp["p_floor_g"])
        self.share = self.kr / (self.kh + self.kr)
        self.knee_G = (self.p_r0 - self.p_floor) * self.A_ann / self.share     # oil-force increment at the knee
        self.F_min = float(p["control"]["F_min_cylinder_N"])
        self.Wr = geo.rod_mass * geo.g
        q0, F0, N0 = self.sysm.place_and_settle(self.k2)
        self.F0, self.N0 = F0, N0
        self.beta, self.L0h = float(lp["beta"]), float(lp["L0h"])
        self.c_mov, self.c_lock = np.asarray(lp["c_mov"], float), np.asarray(lp["c_lock"], float)

    def kh_of(self, s):
        return self.beta * self.A_p[0] / (self.L0h + s)


def oil_tangent(m, mode, s_ref_fl):
    k = np.empty(4)
    for i in range(4):
        if mode[i] == "MOVE":
            k[i] = m.kh_of(s_ref_fl)
        elif mode[i] == "LOCK":
            k[i] = m.kh[i] + m.kr[i]
        else:                         # KNEE (rod side at its floor) or HEAD (rod side off)
            k[i] = m.kh[i]
    return k


def run_path(m, Fs_front, rear_scale=REAR_SCALE, variant="rod_side", targets=(0.02,), stop_at_liftoff=True,
             kh_track=True, seg_max=SEG_MAX, test_leg=0, record_every=None):
    """Quasi-static FL s_ref path through the 'targets' (m, relative to the settled s_ref)."""
    Fs = np.array([Fs_front, Fs_front, rear_scale * Fs_front, rear_scale * Fs_front], float)
    lock_mode = "LOCK" if variant == "rod_side" else "HEAD"
    mode = [lock_mode] * 4
    mode[test_leg] = "MOVE"
    F = m.F0.copy(); N = m.N0.copy(); G = m.F0.copy(); f = np.zeros(4)
    dG_lock = np.zeros(4)
    stick = np.ones(4, bool); sgn = np.zeros(4)
    sp = np.zeros(4)                       # piston displacement (outward +) since arming
    s_ref = float(m.e_op[test_leg])        # absolute FL s_ref
    c_fl = m.F0[test_leg] / m.kh_of(s_ref)  # absolute FL oil compression (G = k_h c)
    lam = 0.0
    first = {}
    first_slip = [None] * 4
    knees = []
    hist = []
    p_r_track = {"max": np.full(4, -np.inf)}
    min_N_path = np.inf

    def p_rod(i, Gi, dGl):
        if mode[i] == "LOCK":
            return max(m.p_floor, m.p_r0[i] - m.share[i] * dGl / m.A_ann[i])
        if mode[i] == "KNEE":
            return m.p_floor
        return 0.0                          # MOVE (valve open, return) / HEAD (rod side off): 0 g

    def head_reading(i):
        return G[i] + p_rod(i, G[i], dG_lock[i]) * m.A_ann[i]

    def snapshot(tag=None):
        return {"lam_mm": lam * 1e3, "F_N": F.copy(), "G_N": G.copy(), "f_N": f.copy(), "N_N": N.copy(),
                "stick": stick.copy(), "mode": list(mode), "sp_um": sp * 1e6,
                "head_reading_N": np.array([head_reading(i) for i in range(4)]), "tag": tag}

    start = snapshot("start")
    ended = False
    for target in targets:
        d = 1.0 if target > lam else -1.0
        guard = 0
        while (target - lam) * d > 1e-15 and not ended:
            guard += 1
            if guard > 2_000_000:
                raise RuntimeError("path did not finish")
            # ---- active set for this segment
            h_nom = min((target - lam) * d, seg_max)
            s_eval = s_ref + 0.5 * d * h_nom          # midpoint of the nominal segment (2nd order in seg_max)
            for _it in range(40):
                ko_o = oil_tangent(m, mode, s_eval if kh_track else float(m.e_op[test_leg]))
                a = d * ((1.0 - c_fl / (m.L0h + s_eval)) if kh_track else 1.0)   # dG/dlam at fixed s_p, / k_h
                ko_e = np.where(stick, m.kout, 1.0 / (1.0 / ko_o + 1.0 / m.kout))
                delta = np.zeros(4)
                if not stick[test_leg]:
                    delta[test_leg] = a
                _, dF, dN = m.sysm.solve(ko_e, delta)
                ds = (delta - dF / ko_e)                      # link extension increment s = b.q (per unit lam)
                dG = np.where(stick, 0.0, dF)
                if stick[test_leg]:
                    dG[test_leg] = ko_o[test_leg] * a
                dfr = np.where(stick, dF - dG, 0.0)
                dsp = np.where(stick, 0.0, ds + dF / m.kout)
                changed = False
                for i in range(4):
                    if Fs[i] <= 0.0:
                        if stick[i]:
                            stick[i] = False; sgn[i] = 0.0; changed = True
                        continue
                    if not stick[i] and sgn[i] * dsp[i] > 1e-15:            # friction would do positive work
                        stick[i] = True; changed = True
                    elif stick[i] and abs(abs(f[i]) - Fs[i]) <= TOL and np.sign(dfr[i]) == np.sign(f[i]) \
                            and abs(dfr[i]) > 0:
                        stick[i] = False; sgn[i] = np.sign(f[i]); f[i] = sgn[i] * Fs[i]; changed = True
                        if first_slip[i] is None:
                            first_slip[i] = lam * 1e3
                if not changed:
                    break
            else:
                raise RuntimeError("active set did not converge")
            # ---- events
            rem = (target - lam) * d
            cand = [(min(rem, seg_max if kh_track else rem), "seg", -1)]
            for i in range(4):
                if stick[i] and Fs[i] > 0 and abs(dfr[i]) > 0:
                    edge = np.sign(dfr[i]) * Fs[i]
                    t = (edge - f[i]) / dfr[i]
                    if t >= -1e-15:
                        cand.append((max(t, 0.0), "slip", i))
                if mode[i] == "LOCK" and dG[i] > 0:
                    cand.append(((m.knee_G[i] - dG_lock[i]) / dG[i], "knee", i))
                if mode[i] == "KNEE" and dG[i] < 0:
                    cand.append(((m.knee_G[i] - dG_lock[i]) / dG[i], "unknee", i))
                if dF[i] < 0 and F[i] > m.F_min and "F_min_true" not in first:
                    cand.append(((F[i] - m.F_min) / -dF[i], "F_min_true", i))
                if dG[i] < 0 and G[i] > m.F_min and "F_min_net" not in first:
                    cand.append(((G[i] - m.F_min) / -dG[i], "F_min_net", i))
                hr = head_reading(i)
                dhr = dG[i] * (1.0 - m.share[i]) if mode[i] == "LOCK" else dG[i]
                if dhr < 0 and hr > m.F_min and "F_min_head" not in first:
                    cand.append(((hr - m.F_min) / -dhr, "F_min_head", i))
                if dN[i] < 0 and N[i] > 0 and "liftoff" not in first:
                    cand.append((N[i] / -dN[i], "liftoff", i))
            cand = [c for c in cand if c[0] >= -1e-15]
            t, lab, i_ev = min(cand, key=lambda c: c[0])
            t = max(t, 0.0)
            # ---- advance
            F = F + t * dF; N = N + t * dN
            Gn = G + t * dG
            dG_lock = dG_lock + np.where([mo in ("LOCK", "KNEE", "HEAD") for mo in mode], t * dG, 0.0)
            G = Gn
            f = np.where(stick, f + t * dfr, sgn * Fs)
            sp = sp + t * dsp
            c_fl = c_fl + t * (d - dsp[test_leg])
            s_ref = s_ref + t * d
            lam = lam + t * d
            min_N_path = min(min_N_path, float(N.min()))
            # coincident crossings (several quantities reach their threshold at the same lam)
            for key, arr, thr_ in (("F_min_true", F, m.F_min), ("F_min_net", G, m.F_min),
                                   ("F_min_head", np.array([head_reading(j) for j in range(4)]), m.F_min),
                                   ("liftoff", N, 0.0)):
                if key not in first and key != lab and float(arr.min()) <= thr_ + 1e-6:
                    snap = snapshot(key)
                    snap["leg"] = dm.LEG_NAMES[int(np.argmin(arr))]
                    first[key] = snap
                    if key == "liftoff" and stop_at_liftoff:
                        ended = True
            for j in range(4):
                if mode[j] == "LOCK":
                    p_r_track["max"][j] = max(p_r_track["max"][j], p_rod(j, G[j], dG_lock[j]))
            if record_every is not None and (not hist or abs(lam - hist[-1]["lam_mm"] * 1e-3) >= record_every):
                hist.append(snapshot())
            # ---- event actions
            if lab == "slip":
                stick[i_ev] = False; sgn[i_ev] = np.sign(dfr[i_ev]); f[i_ev] = sgn[i_ev] * Fs[i_ev]
                if first_slip[i_ev] is None:
                    first_slip[i_ev] = lam * 1e3
            elif lab == "knee":
                mode[i_ev] = "KNEE"; knees.append([dm.LEG_NAMES[i_ev], lam * 1e3, "knee"])
            elif lab == "unknee":
                mode[i_ev] = "LOCK"; knees.append([dm.LEG_NAMES[i_ev], lam * 1e3, "back"])
            elif lab in ("F_min_true", "F_min_net", "F_min_head", "liftoff"):
                if lab not in first:
                    snap = snapshot(lab)
                    snap["leg"] = dm.LEG_NAMES[i_ev]
                    first[lab] = snap
                if lab == "liftoff" and stop_at_liftoff:
                    ended = True
        if ended:
            break
    return {"Fs_N": Fs, "first": first, "first_slip_mm": first_slip, "knees": knees, "end": snapshot("end"),
            "start": start,
            "p_r_max_Pa": p_r_track["max"], "min_N_path_N": min_N_path, "hist": hist}


def summarise_a(m, res):
    fi = res["first"]

    def ev(key):
        if key not in fi:
            return None
        return {"mm": fi[key]["lam_mm"], "leg": fi[key]["leg"]}

    out = {"F_s_front_rear_N": [res["Fs_N"][0], res["Fs_N"][2]],
           "F_min_true": ev("F_min_true"), "F_min_net_reading": ev("F_min_net"),
           "F_min_head_only_reading": ev("F_min_head"), "liftoff": ev("liftoff")}
    if "liftoff" in fi:
        s = fi["liftoff"]
        j = dm.LEG_NAMES.index(s["leg"])
        out["at_liftoff"] = {
            "lifting_leg": s["leg"],
            "true_cyl_force_N (= -m_rod g)": s["F_N"][j],
            "net_reading_N (G = F - f)": s["G_N"][j],
            "head_only_reading_N (p_h A_p)": s["head_reading_N"][j],
            "friction_N": s["f_N"][j],
            "expected_F_s_minus_m_g_N": res["Fs_N"][j] - m.Wr[j],
            "net_reading_minus_F_min_N": s["G_N"][j] - m.F_min,
            "all_legs_true_N": s["F_N"], "all_legs_net_N": s["G_N"], "all_legs_f_N": s["f_N"],
            "all_legs_stick": s["stick"], "modes": s["mode"]}
    out["first_slip_mm"] = res["first_slip_mm"]
    out["knees (leg, mm, kind)"] = res["knees"]
    out["p_r_max_locked_bar_g"] = res["p_r_max_Pa"] / 1e5
    return out


def summarise_b(m, res_rt, res_up10, res_1mm):
    e = res_rt["end"]
    out = {"F_s_front_rear_N": [res_rt["Fs_N"][0], res_rt["Fs_N"][2]],
           "residual_true_load_change_after_return_N": e["F_N"] - m.F0,
           "residual_net_reading_change_after_return_N": e["G_N"] - m.F0,
           "residual_head_reading_change_after_return_N": e["head_reading_N"] - res_rt["start"]["head_reading_N"],
           "friction_after_return_N": e["f_N"], "stick_after_return": e["stick"],
           "piston_residual_um": e["sp_um"],
           "min_contact_force_along_path_N": res_rt["min_N_path_N"],
           "F_min_reached_on_the_way (true, net) [mm, leg]": [
               None if "F_min_true" not in res_up10["first"] else
               [res_up10["first"]["F_min_true"]["lam_mm"], res_up10["first"]["F_min_true"]["leg"]],
               None if "F_min_net" not in res_up10["first"] else
               [res_up10["first"]["F_min_net"]["lam_mm"], res_up10["first"]["F_min_net"]["leg"]]],
           "at_+10mm": {"true_N": res_up10["end"]["F_N"], "net_N": res_up10["end"]["G_N"],
                        "f_N": res_up10["end"]["f_N"], "N_N": res_up10["end"]["N_N"]},
           "RL_change_at_+1mm_true_N": res_1mm["end"]["F_N"][2] - m.F0[2],
           "RL_change_at_+1mm_net_N": res_1mm["end"]["G_N"][2] - m.F0[2],
           "first_slip_mm (up)": res_up10["first_slip_mm"],
           "knees (leg, mm, kind)": res_rt["knees"]}
    return out


def pressure_dependent_Fs(m, res, level_N):
    """Spec 2.4 option evaluated at the lift-off state of a constant-F_s run (F_s(p) of the lifting leg)."""
    fi = res["first"].get("liftoff")
    if fi is None:
        return None
    j = dm.LEG_NAMES.index(fi["leg"])
    D = (0.130, 0.130, 0.110, 0.110)[j]; dd = (0.110, 0.110, 0.090, 0.090)[j]
    F0 = 1.27e3; kappa = (3.72e3 - F0) / (math.pi * 0.130 * 120.0 + math.pi * 0.110 * 165.0)   # N/(m bar)

    def phi(ph, pr):
        return F0 * (D + dd) / 0.240 + kappa * (math.pi * D * abs(ph - pr) + math.pi * dd * pr)

    p_ref_h = (89.0, 89.0, 76.0, 76.0)[j]
    pr_bar = (fi["head_reading_N"][j] - fi["G_N"][j]) / m.A_ann[j] / 1e5
    ph_bar = fi["head_reading_N"][j] / m.A_p[j] / 1e5
    scale = (1.0 if j < 2 else REAR_SCALE)
    Fs_p = level_N * scale * phi(ph_bar, pr_bar) / phi(p_ref_h, 2.0)
    return {"leg": fi["leg"], "p_h_bar_g": ph_bar, "p_r_bar_g": pr_bar,
            "phi_ratio_vs_operating": phi(ph_bar, pr_bar) / phi(p_ref_h, 2.0),
            "F_s_at_liftoff_N": Fs_p, "reading_F_s_minus_m_g_N": Fs_p - m.Wr[j],
            "kappa_N_per_m_bar": kappa}


def main():
    t0 = time.perf_counter()
    m = Model("top")
    res = {"meta": {
        "script": "04_scripts/01_dynamics/s8_v15_reference.py", "params": "02_params/rexome33.yaml",
        "params_sha256": dm.params_sha256() if hasattr(dm, "params_sha256") else None,
        "frame": "body x fwd, y left, z up; g = -9.80665 z; leg order FL FR RL RR",
        "force_basis": ("true = rod axial force F = k_out (s_p - s) (compression +, F_min basis); net reading = G = F - f "
                        "(two sensors p_h A_p - p_r A_ann); head-only reading = G + p_r A_ann; contact N = F + m_rod g"),
        "model": __doc__.split("\n\n")[1],
        "level": "top", "e_op_m": m.e_op, "F_min_N": m.F_min, "rear_scale": REAR_SCALE,
        "k_h_N_m": m.kh, "k_r_N_m": m.kr, "k_out_N_m": m.kout, "k2_N_m": m.k2, "k1_N_m": m.k1,
        "stick_over_lock_stiffness": m.kout / m.k1, "knee_oil_force_N": m.knee_G,
        "p_r0_after_extend_Pa": m.p_r0, "p_floor_gauge_Pa": m.p_floor, "rod_weight_N": m.Wr,
        "settled_cyl_force_N": m.F0, "settled_contact_N": m.N0,
        "assumptions": ("initial friction f = 0 (stick) at arming after the settle (spec 2.6); rigid stick (k_st = inf); "
                        "static = kinetic (r_s 1); FL valve open (moving law, rod side released with R0 = 0, p_r 0 g); "
                        "locked legs p_r0 2 bar g (RULE, after an extension); quasi-static (dashpot c_mov u = "
                        f"{float(m.c_mov[0] * SPEED):.1f} N on FL at 0.1 mm/s and inertia not included)")}}
    # ---- F_s = 0 regression vs reference.json L2b block (k_h fixed = same model as l2b_reference)
    ref = json.loads((dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json").read_text(encoding="utf-8"))
    thr = ref["L2b_NSC_reference_rev33"]["levels"]["top"]["single_leg_thresholds_mm (V5 / V6 / V14 level)"]["FL+"]
    reg = {}
    for var, key in (("rod_side", "L1R_after_extend"), ("head_only", "head_only")):
        a0 = run_path(m, 0.0, variant=var, kh_track=False)
        mine = (a0["first"]["F_min_true"]["lam_mm"], a0["first"]["liftoff"]["lam_mm"])
        theirs = (thr[key]["F_min_mm"]["value"], thr[key]["liftoff_mm"]["value"])
        reg[var] = {"mine_F_min_liftoff_mm": mine, "reference_json_mm": theirs,
                    "max_abs_diff_mm": max(abs(mine[0] - theirs[0]), abs(mine[1] - theirs[1])),
                    "legs": (a0["first"]["F_min_true"]["leg"], a0["first"]["liftoff"]["leg"])}
        if reg[var]["max_abs_diff_mm"] > 2e-3:
            raise RuntimeError(f"F_s = 0 regression failed ({var}): {reg[var]}")
    res["regression_Fs0_vs_reference_json_kh_fixed"] = reg
    # ---- V15 (a), (b) for both oil variants
    v15 = {}
    for var in ("rod_side", "head_only"):
        blk = {"a_upsweep_unilateral": {}, "b_roundtrip_10mm": {}, "kh_fixed_sensitivity (a)": {}}
        for L in LEVELS_KN:
            lab = f"L{L:g}"
            ra = run_path(m, L * 1e3, variant=var)
            blk["a_upsweep_unilateral"][lab] = summarise_a(m, ra)
            pd = pressure_dependent_Fs(m, ra, L * 1e3)
            blk["a_upsweep_unilateral"][lab]["pressure_dependent_option_at_liftoff (spec 2.4)"] = pd
            rk = run_path(m, L * 1e3, variant=var, kh_track=False)
            blk["kh_fixed_sensitivity (a)"][lab] = {
                k: (None if k not in rk["first"] else rk["first"][k]["lam_mm"] - ra["first"][k]["lam_mm"]
                    if k in ra["first"] else None) for k in ("F_min_true", "F_min_net", "liftoff")}
            rt = run_path(m, L * 1e3, variant=var, targets=(0.010, 0.0), stop_at_liftoff=False)
            up = run_path(m, L * 1e3, variant=var, targets=(0.010,), stop_at_liftoff=False)
            one = run_path(m, L * 1e3, variant=var, targets=(0.001,), stop_at_liftoff=False)
            blk["b_roundtrip_10mm"][lab] = summarise_b(m, rt, up, one)
        # segment-cap convergence (k_h tracking): halve SEG_MAX for L8
        ra1 = run_path(m, 8e3, variant=var)
        ra2 = run_path(m, 8e3, variant=var, seg_max=SEG_MAX / 4)
        blk["seg_cap_convergence_L8_mm"] = {k: ra2["first"][k]["lam_mm"] - ra1["first"][k]["lam_mm"]
                                            for k in ra1["first"]}
        v15[var] = blk
    res["V15_rev39"] = v15
    # ---- D-2: miss threshold (net reading at lift-off = F_min), rear 0.833 and rear = front
    d2 = {}
    for rs in (REAR_SCALE, 1.0):
        rows = []
        for L in (8, 9, 10, 10.5, 11, 11.5, 12, 12.5, 13, 14):
            ra = run_path(m, L * 1e3, rear_scale=rs)
            s = summarise_a(m, ra)
            al = s.get("at_liftoff", {})
            rows.append({"level_kN": L, "liftoff": s["liftoff"], "F_min_net": s["F_min_net_reading"],
                         "net_reading_at_liftoff_N": al.get("net_reading_N (G = F - f)"),
                         "head_reading_at_liftoff_N": al.get("head_only_reading_N (p_h A_p)")})
        # interpolate the level where the lifting-leg net reading = F_min
        Ls = np.array([x["level_kN"] for x in rows]); P = np.array([x["net_reading_at_liftoff_N"] for x in rows])
        k = np.flatnonzero(P >= m.F_min)
        L_star = float(np.interp(m.F_min, P, Ls)) if k.size else None
        d2[f"rear_scale_{rs:g}"] = {"rows": rows, "level_where_net_reading_at_liftoff_eq_F_min_kN": L_star}
    d2["analytic_bound"] = {
        "lifted_leg_reading_max_N (F_s - m g)": "front 8 kN: %.1f, rear 0.833 x 8 kN: %.1f" % (
            8e3 - m.Wr[0], REAR_SCALE * 8e3 - m.Wr[2]),
        "F_s_needed_for_a_miss_N (F_min + m g)": {"front": m.F_min + m.Wr[0], "rear": m.F_min + m.Wr[2]},
        "front_level_for_a_rear_miss (0.833)": (m.F_min + m.Wr[2]) / REAR_SCALE}
    res["D2_pressure_only_miss_threshold"] = d2
    res["meta"]["runtime_s"] = time.perf_counter() - t0
    OUT.write_text(json.dumps(r(res), indent=1, ensure_ascii=False, default=lambda o: r(np.asarray(o))),
                   encoding="utf-8")
    print("wrote", OUT, f"{res['meta']['runtime_s']:.1f} s")


if __name__ == "__main__":
    main()
