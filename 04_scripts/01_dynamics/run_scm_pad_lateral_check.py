"""S9 pad horizontal restraint on SCM: creep estimate, tangential stiffness, utilisation, rocking modes, swivel tilt.

Doc: 00_docs/01_dynamics/dynamics_model.md 5.33 (rev. 47). Chrono-independent numpy/numba model; the Chrono single-pad
probe is 04_scripts/02_chrono/scm_pad_lateral_probe.py (06_analysis/01_chrono/19_S9/scm_pad_lateral_probe.json).
Run:  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_scm_pad_lateral_check.py     (about 1 min)

Parts
  A. SCM shear replica (SCMTerrain.cpp:1430-1478, PyChrono 10.0.0): per step, force from the step-start velocity
     T = -v_t/|v_t| (|v_t| = 0 -> Normalize gives [1,0,0]), j += |v_t| dt, tau = (c + sigma tan phi)(1 - exp(-j/K_J)),
     applied as an explicit load; semi-implicit Euler v+ = v + dt F/M, x+ = x + dt v+ (EULER_IMPLICIT_LINEARIZED with
     a load that has no Jacobian). 2-D rigid translation. Cases: single pad (Chrono probe replica) and whole machine
     (all pads translate together; drive W sin(alpha) along the slope).
  B. Tangential stiffness for a ground anchor on SCM: rod lateral k_lat (YAML kt with the concrete term removed) in
     series with the soil (Gazetas/Bycroft horizontal = kappa K A, kappa 0.8 nominal) or the Janosi initial slope.
  C. Levelling-end tangential demand vs Mohr-Coulomb capacity c A + N tan(phi) (soil-soil, = saturated SCM shear) and
     an interface variant (delta = 2/3 phi, adhesion 0.5 c).
  D. Rocking modes (10-DoF, legs locked, soil K A vertical) for lateral stiffness: L1 YAML kt / S9 series / 0 / pinned.
  E. Swivel pad tilt stability on SCM: k_r (soil rotational stiffness about the pad centroid) vs N h (ball height h).
Frames / units: body axes x fwd, y left, z up; SI; gravity (0, 0, -g).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import run_pad_bekker_p0 as p0  # noqa: E402  (read-only reuse: params, pad table, leg stiffness, twist-free loads)

OUT = ROOT / "06_analysis" / "00_dynamics" / "scm_pad_lateral_check.json"
SETS = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))["sets"]
G = p0.G
H_BALL = 0.06            # YAML legs.*.pad.swivel_center_above_pad_bottom_m (ASSUMPTION in YAML)
KAPPA = 0.8              # ASSUMPTION: horizontal / vertical elastic footing stiffness, 2(1-nu)/(2-nu) 0.79 ... 0.85
K_CONC = float(p0.P["contact"]["rigid_floor"]["concrete"]["k_N_m"])
LEGS = dm.LEG_NAMES


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- A. replica
@njit(cache=False)
def scm_shear_replica(M, Fx, Fy, Fc_max, KJ, dt, t_end, t_ramp0, t_ramp1, t_fit0):
    n = int(round(t_end / dt))
    x = 0.0; y = 0.0; vx = 0.0; vy = 0.0; j = 0.0
    sx = 0.0; st = 0.0; stt = 0.0; stx = 0.0; nfit = 0
    fmin = 1e30; fmax = -1e30; flips = 0; prev = 0
    for k in range(n):
        t = k * dt
        if t < t_ramp0:
            s = 0.0
        elif t < t_ramp1:
            s = (t - t_ramp0) / (t_ramp1 - t_ramp0)
        else:
            s = 1.0
        sp = math.sqrt(vx * vx + vy * vy)
        if sp > 0.0:
            tx = -vx / sp; ty = -vy / sp
        else:
            tx = 1.0; ty = 0.0
        j += sp * dt
        tau = Fc_max * (1.0 - math.exp(-j / KJ))
        fx = tx * tau; fy = ty * tau
        vx += dt * (s * Fx + fx) / M
        vy += dt * (s * Fy + fy) / M
        x += dt * vx
        y += dt * vy
        if t >= t_fit0:
            sx += x; st += t; stt += t * t; stx += t * x; nfit += 1
            fmin = min(fmin, fx); fmax = max(fmax, fx)
            sg = 1 if fx > 0 else (-1 if fx < 0 else 0)
            if sg != 0 and prev != 0 and sg != prev:
                flips += 1
            if sg != 0:
                prev = sg
    slope = (nfit * stx - st * sx) / (nfit * stt - st * st)
    return slope, x, y, fmin, fmax, flips / (t_end - t_fit0), j


def capacity(soil, N, A, interface=False):
    c, phi = soil["cohesion"], soil["friction"]
    if interface:
        c, phi = 0.5 * c, math.degrees(math.atan(math.tan(math.radians(phi)) * 1.0)) * 2.0 / 3.0
    return c * A + N * math.tan(math.radians(phi))


def part_a(F):
    out = {"model": "2-D rigid translation, explicit SCM shear law (see module docstring)",
           "single_pad": [], "machine": []}
    # single-pad Chrono probe replica (fixed joint): N = RL design load, M = N/g, F along +x
    N = float(F[2])
    for sk in ("G1", "J1"):
        s = SETS[sk]["chrono"]
        for lab in ("A", "B"):
            A = p0.PV[lab]["legs"]["RL"]["area"]
            Fc = capacity(s, N, A)
            for tag, Fh in (("F0", 0.0), ("slope3.5", N * math.sin(math.radians(3.5))),
                            ("slope5.5", N * math.sin(math.radians(5.5))), ("internal20k", 20e3)):
                for dt in (1e-4, 5e-5, 2.5e-5):
                    v, xe, ye, fmn, fmx, fl, j = scm_shear_replica(N / G, Fh, 0.0, Fc, s["Janosi"], dt, 12.5, 2.0,
                                                                  2.5, 4.5)
                    out["single_pad"].append(dict(soil=sk, pad=lab, load=tag, F_N=Fh, dt=dt, Fc_N=Fc,
                                                  drift_velocity_m_s=v, drift_estimate_F_dt_over_M=Fh * dt / (N / G),
                                                  Fx_step_min_N=fmn, Fx_step_max_N=fmx, flips_per_s=fl,
                                                  kshear_end_m=j, y_end_mm=ye * 1e3))
    # whole machine: all four pads translate together, drive W sin(alpha) along the slope (x for pitch, y for roll)
    Mtot = float(p0.body("top").mass)
    W = Mtot * G
    for sk in ("G1", "J1", "J2", "S1"):
        s = SETS[sk]["chrono"]
        for lab in ("A", "B"):
            Fc = sum(capacity(s, float(F[i]), p0.PV[lab]["legs"][leg]["area"]) for i, leg in enumerate(LEGS))
            for ang in (3.2, 3.5, 4.4, 5.5):
                Fd = W * math.sin(math.radians(ang))
                for dt in (2e-4, 1e-4, 5e-5, 1e-5):
                    v, xe, ye, fmn, fmx, fl, j = scm_shear_replica(Mtot, Fd, 0.0, Fc, s["Janosi"], dt, 22.5, 2.0,
                                                                  2.5, 4.5)
                    out["machine"].append(dict(soil=sk, pad=lab, slope_deg=ang, dt=dt, M_kg=Mtot, F_drive_N=Fd,
                                               Fc_total_N=Fc, drift_velocity_m_s=v,
                                               drift_estimate_g_sin_dt=G * math.sin(math.radians(ang)) * dt,
                                               drift_mm_in_25_65_100_600_s=[v * T * 1e3 for T in (25, 65, 100, 600)],
                                               force_square_wave_N=[fmn, fmx],
                                               accel_square_wave_m_s2=[(Fd + fmn) / Mtot, (Fd + fmx) / Mtot],
                                               flips_per_s=fl))
    return out


# ---------------------------------------------------------------------------------------------- B. stiffness
def k_lat_from_yaml():
    kt = p0.KT_YAML
    return 1.0 / (1.0 / kt - 1.0 / K_CONC)


def part_b(F):
    klat = k_lat_from_yaml()
    out = {"k_lat_rod_N_m": dict(zip(LEGS, klat.tolist())), "k_conc_N_m": K_CONC, "kt_L1_yaml_N_m": dict(zip(LEGS, p0.KT_YAML.tolist())),
           "kappa": KAPPA, "sets": {}}
    for sk, d in SETS.items():
        s = d["chrono"]
        row = {}
        for lab in ("A", "B"):
            r = {}
            for i, leg in enumerate(LEGS):
                A = p0.PV[lab]["legs"][leg]["area"]
                k_el = KAPPA * s["elastic_K"] * A
                k_j = capacity(s, float(F[i]), A) / s["Janosi"]
                r[leg] = {"k_soil_elastic_N_m": k_el, "k_soil_janosi_N_m": k_j,
                          "kt_S9_nominal_N_m": dm.series(klat[i], k_el), "kt_S9_janosi_N_m": dm.series(klat[i], k_j),
                          "ratio_to_L1": dm.series(klat[i], k_el) / p0.KT_YAML[i]}
            row[lab] = r
        out["sets"][sk] = row
    return out


# ---------------------------------------------------------------------------------------------- C. utilisation
# L1 (REXOME35) stick-mechanism internal force at the levelling end, dynamics_model.md 5.13.3 (top, rigid support):
# pitch 3.5 deg 22.1 kN (front pair against rear pair), roll 5.5 deg front pair 43.7 kN / rear pair 20.5 kN.
# Scaled by theta^2 (3.10.2) and by the series stiffness of the opposing pads.
L1_INT = {"pitch": 22.1e3, "roll_front": 43.7e3, "roll_rear": 20.5e3}


def part_c(F, b):
    out = {"basis": "demand = |internal (scaled from 5.13.3 by theta^2 and opposing-pair series stiffness) + "
                    "V sin(alpha) along the slope| upper bound (aligned); capacity = c A + N tan(phi) (soil-soil, "
                    "= saturated SCM shear); interface: adhesion 0.5 c, delta = 2/3 phi", "cases": []}
    kt1 = p0.KT_YAML
    for sk in SETS:
        s = SETS[sk]["chrono"]
        for lab in ("A", "B"):
            kt9 = np.array([b["sets"][sk][lab][leg]["kt_S9_nominal_N_m"] for leg in LEGS])
            for kind, ang in (("pitch", 3.2), ("pitch", 3.5), ("roll", 4.4), ("roll", 5.5)):
                sc = (ang / (3.5 if kind == "pitch" else 5.5)) ** 2
                if kind == "pitch":
                    pair1 = kt1[0] * kt1[2] / (kt1[0] + kt1[2]); pair9 = kt9[0] * kt9[2] / (kt9[0] + kt9[2])
                    fint = np.full(4, L1_INT["pitch"] * sc * pair9 / pair1)
                else:
                    fint = np.array([L1_INT["roll_front"] * sc * kt9[0] / kt1[0]] * 2 +
                                    [L1_INT["roll_rear"] * sc * kt9[2] / kt1[2]] * 2)
                slope = F * math.sin(math.radians(ang))
                dem = fint + slope
                row = dict(soil=sk, pad=lab, case=f"{kind} {ang}", internal_N=fint.tolist(), slope_share_N=slope.tolist(),
                           demand_N=dem.tolist())
                for itf in (False, True):
                    cap = np.array([capacity(s, float(F[i]), p0.PV[lab]["legs"][leg]["area"], itf)
                                    for i, leg in enumerate(LEGS)])
                    row["capacity_interface_N" if itf else "capacity_N"] = cap.tolist()
                    row["utilisation_interface" if itf else "utilisation"] = (dem / cap).tolist()
                out["cases"].append(row)
    return out


# ---------------------------------------------------------------------------------------------- D. rocking modes
def part_d(b):
    body = dm.body_from_params(p0.P, "top")
    ko = p0.k_leg(p0.E_OP)
    out = {}
    for sk in ("G1", "J1"):
        s = SETS[sk]["chrono"]
        for lab in ("A", "B"):
            a = np.array([p0.PV[lab]["legs"][n]["area"] for n in LEGS])
            kc = s["elastic_K"] * a
            res = {}
            for tag, kh in (("L1_yaml_kt", p0.KT_YAML),
                            ("S9_series_nominal", np.array([b["sets"][sk][lab][n]["kt_S9_nominal_N_m"] for n in LEGS])),
                            ("rod_only_k_lat", k_lat_from_yaml()),
                            ("pinned_1e11", np.full(4, 1e11)), ("free_0", np.zeros(4))):
                M, K, C, labels, _ = dm.model_10dof(body, p0.GEO, p0.E_OP, ko, kc, kh)
                w2, f, Phi, cls, orth = dm.modal(M, K, labels)
                res[tag] = [{"f_Hz": float(f[k]), "dominant": cls[k]} for k in range(len(f)) if f[k] > 0.05][:6]
            out[f"{sk}_{lab}"] = res
    return out


# ---------------------------------------------------------------------------------------------- E. swivel tilt
def poly_inertia(poly):
    p = np.asarray(poly, float)
    if np.allclose(p[0], p[-1]):
        p = p[:-1]
    x, y = p[:, 0], p[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x * yn - xn * y
    A = cr.sum() / 2
    cx = ((x + xn) * cr).sum() / (6 * A); cy = ((y + yn) * cr).sum() / (6 * A)
    Ixx = ((y ** 2 + y * yn + yn ** 2) * cr).sum() / 12 - A * cy ** 2
    Iyy = ((x ** 2 + x * xn + xn ** 2) * cr).sum() / 12 - A * cx ** 2
    return abs(A), abs(Ixx), abs(Iyy)


def part_e(F):
    out = {"criterion": "pad hanging on the swivel ball, h above the bottom: stable iff k_r > N h, k_r = k_area I "
                        "(Winkler; I = min second moment of the pad polygon about its centroid). k_area: plastic "
                        "(virgin loading, Bekker tangent n p / z), secant p / z, elastic K (unloading/reloading)",
           "h_m": H_BALL, "rows": []}
    for sk, d in SETS.items():
        s = d["chrono"]
        for lab in ("A", "B"):
            for i, leg in enumerate(LEGS):
                pv = p0.PV[lab]["legs"][leg]
                A, Ixx, Iyy = poly_inertia(pv["poly"])
                I = min(Ixx, Iyy)
                N = float(F[i]); p = N / A
                keq = s["Kc"] / pv["b"] + s["Kphi"]
                z = (p / keq) ** (1 / s["n"])
                kr = {"plastic": s["n"] * p / z * I, "secant": p / z * I, "elastic": s["elastic_K"] * I}
                Nh = N * H_BALL
                out["rows"].append(dict(soil=sk, pad=lab, leg=leg, N_N=N, area_m2=A, I_min_m4=I, z_design_mm=z * 1e3,
                                        Nh_Nm_rad=Nh, **{f"kr_{k}_Nm_rad": v for k, v in kr.items()},
                                        **{f"ratio_{k}": v / Nh for k, v in kr.items()},
                                        k_sw_needed_for_2x_Nm_rad=max(0.0, 2 * Nh - kr["plastic"])))
    return out


def main():
    F, _ = p0.twist_free_loads("top")
    a = part_a(F)
    b = part_b(F)
    c = part_c(F, b)
    d = part_d(b)
    e = part_e(F)
    res = {"schema": 1, "generated": _dt.datetime.now().isoformat(timespec="seconds"),
           "generator": {"path": "04_scripts/01_dynamics/run_scm_pad_lateral_check.py", "sha256": sha(Path(__file__))},
           "inputs": {"scm_soil_sets.json": sha(ROOT / "02_params" / "scm_soil_sets.json"),
                      "pad_variants.json": sha(ROOT / "02_params" / "pad_variants.json"),
                      "rexome33.yaml": sha(ROOT / "02_params" / "rexome33.yaml")},
           "doc": "00_docs/01_dynamics/dynamics_model.md 5.33 (rev. 47)",
           "frame": "body axes x fwd, y left, z up; gravity (0,0,-g); SI",
           "design_contact_loads_N": dict(zip(LEGS, F.tolist())),
           "A_replica": a, "B_stiffness": b, "C_utilisation": c, "D_rocking_modes": d, "E_swivel_tilt": e}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    # console summary
    for r in a["single_pad"]:
        if r["dt"] == 1e-4:
            print(f"pad {r['soil']} {r['pad']} {r['load']:11s} v={r['drift_velocity_m_s']:.3e} est={r['drift_estimate_F_dt_over_M']:.3e} "
                  f"Fx=[{r['Fx_step_min_N']:.0f},{r['Fx_step_max_N']:.0f}] flips/s={r['flips_per_s']:.0f} j={r['kshear_end_m']:.3f}")
    for r in a["machine"]:
        if r["pad"] == "B" and r["soil"] in ("G1", "J1"):
            print(f"mach {r['soil']} {r['slope_deg']} dt={r['dt']:.0e} v={r['drift_velocity_m_s']:.3e} est={r['drift_estimate_g_sin_dt']:.3e} "
                  f"mm(25/65/100/600)={[round(v, 2) for v in r['drift_mm_in_25_65_100_600_s']]} acc={[round(v, 2) for v in r['accel_square_wave_m_s2']]}")
    print(json.dumps({k: v for k, v in b.items() if k != "sets"}, indent=0))
    for sk in b["sets"]:
        for lab in ("A", "B"):
            print(sk, lab, {leg: (round(v["kt_S9_nominal_N_m"] / 1e6, 3), round(v["kt_S9_janosi_N_m"] / 1e6, 3),
                                  round(v["ratio_to_L1"], 3)) for leg, v in b["sets"][sk][lab].items()})
    for r in c["cases"]:
        print(r["soil"], r["pad"], r["case"], "dem", [round(x / 1e3, 1) for x in r["demand_N"]], "util",
              [round(x, 2) for x in r["utilisation"]], "itf", [round(x, 2) for x in r["utilisation_interface"]])
    for k, v in d.items():
        print(k, {t: [(round(m["f_Hz"], 3), list(m["dominant"].keys())[0]) for m in ms[:4]] for t, ms in v.items()})
    for r in e["rows"]:
        print(f"{r['soil']} {r['pad']} {r['leg']} z={r['z_design_mm']:.1f} ratio pl/sec/el = {r['ratio_plastic']:.3f} "
              f"{r['ratio_secant']:.3f} {r['ratio_elastic']:.1f} k_sw2x={r['k_sw_needed_for_2x_Nm_rad']:.0f}")


if __name__ == "__main__":
    main()
