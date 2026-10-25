"""Generate 02_params/scm_soil_sets.json: S9 SCM soil sets (J1, J2, G1, S1) and Chrono SetSoilParameters inputs.

Generated table (do not edit by hand). Separate from 02_params/rexome33.yaml: no YAML key, no fingerprint effect.
Doc: 00_docs/01_dynamics/dynamics_model.md 5.32 (rev. 46); literature record 00_docs/01_dynamics/scm_soil_parameter_survey.md.
Run:  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/export_scm_soil_sets.py      (about 1 min)

Contents
  1. survey check: imperial -> SI conversion of the Wong / Bekker rows (typos), 1 MPa sinkage and bearing capacity
     recomputed with the survey definitions and with the P0 definitions (b = 2A/perimeter per pad type, Vesic).
  2. sets: Chrono SetSoilParameters(Kphi, Kc, n, cohesion, friction, Janosi, elastic_K, damping_R) in SI / Chrono units
     (Kphi N/m^(n+2), Kc N/m^(n+1), cohesion Pa, friction deg, Janosi m, K Pa/m, R Pa s/m), sensitivity values, basis.
  3. elastic_K checks: Chrono clamp max(K, Kphi) (n = 1 meaning only), loading-tangent condition K >= n p / z at the
     design load, virgin crossover sinkage (n < 1).
  4. damping_R: 3.11.3 rule (crawler heave zeta 0.2 on the elastic branch, A_c from the P0 crawler settle), Lysmer
     analogue, demo value; soil-damping zeta of the levelled machine (10-DoF, legs locked, pads on K A || R A).
Frames / units: body axes x fwd, y left, z up; SI; gravity (0, 0, -g) with g from YAML meta.gravity_m_s2.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import run_pad_bekker_p0 as p0  # noqa: E402  (read-only reuse: crawler model, pad table, leg stiffness)

OUT = ROOT / "02_params" / "scm_soil_sets.json"
SURVEY = ROOT / "00_docs" / "01_dynamics" / "scm_soil_parameter_survey.md"
YAML = ROOT / "02_params" / "rexome33.yaml"
PADV = ROOT / "02_params" / "pad_variants.json"

LBF = 4.4482216152605          # N
INCH = 0.0254                  # m
PSI = LBF / INCH ** 2          # Pa
GAMMA = 18e3                   # ASSUMPTION soil unit weight [N/m^3] (same as P0 / survey)
ZETA_CRAWLER = 0.2             # YAML contact.crawler... damping_ratio_heave_soil (user decision 2026-10-20)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- 1. survey check
# imperial originals (survey table 1 col. 2, Bekker 1969 via Mason et al. [3]): n, kc [lb/in^(n+1)], kphi [lb/in^(n+2)],
# c [psi], phi [deg]; claimed SI (survey col. 3 = NASA TM [1]) n, kc [kN/m^(n+1)], kphi [kN/m^(n+2)], c [kPa], phi
IMPERIAL = {
    "lean_clay_22": ((0.20, 45, 120, 10, 20), (0.2, 16.43, 1724.69, 68.95, 20)),
    "lean_clay_32": ((0.15, 5, 10, 2, 11), (0.15, 1.52, 119.61, 13.79, 11)),
    "heavy_clay_40": ((0.11, 7, 10, 3, 6), (0.11, 1.84, 103.27, 20.69, 6)),
    "heavy_clay_25": ((0.13, 45, 140, 10, 34), (0.13, 12.70, 1555.95, 68.95, 34)),
    "sandy_loam_LLL_22": ((0.20, 7, 3, 0.2, 38), (0.2, 2.56, 43.12, 1.38, 38)),
    "sandy_loam_Michigan_11": ((0.9, 11, 6, 0.7, 20), (0.9, 52.53, 1127.97, 4.83, 20)),
    "sandy_loam_Hanamoto_26": ((0.3, 5.3, 6.8, 2, 22), (0.3, 2.79, 141.11, 13.79, 22)),
    "sandy_loam_Hanamoto_32": ((0.5, 0.7, 1.2, 0.75, 11), (0.5, 0.77, 51.91, 5.17, 11)),
    "dry_sand_LLL": ((1.1, 0.1, 3.9, 0.15, 28), (1.1, 0.99, 1528.43, 1.04, 28)),
    "WES_lean_clay_CI207": ((0.365, 75, 133, None, None), (0.365, 50, 3.50e3, None, None)),
}
TYPOS = {  # survey: secondary-source values claimed to be typos -> (key, wrong value, source)
    "heavy_clay_25": ("c_kPa", 69.95, "NASA TM-20250006958 [1]"),
    "sandy_loam_Michigan_11": ("kphi", 11127.97, "NASA TM-20250006958 [1]"),
    "dry_sand_LLL": ("kc", 0.95, "Kasetsart Univ. e-book p.457 [2]"),
}


def imperial_to_si(n, kc, kphi, c):
    """kc [lb/in^(n+1)] -> kN/m^(n+1), kphi [lb/in^(n+2)] -> kN/m^(n+2), c [psi] -> kPa."""
    kc_si = kc * LBF / INCH ** (n + 1) / 1e3
    kphi_si = kphi * LBF / INCH ** (n + 2) / 1e3
    c_si = None if c is None else c * PSI / 1e3
    return kc_si, kphi_si, c_si


def conversion_check():
    rows = {}
    for name, ((n, kc, kphi, c, phi), (n2, kc2, kphi2, c2, phi2)) in IMPERIAL.items():
        kc_si, kphi_si, c_si = imperial_to_si(n, kc, kphi, c)
        r = {"imperial": {"n": n, "kc_lb_in^(n+1)": kc, "kphi_lb_in^(n+2)": kphi, "c_psi": c, "phi_deg": phi},
             "computed_SI": {"kc_kN_m^(n+1)": kc_si, "kphi_kN_m^(n+2)": kphi_si, "c_kPa": c_si},
             "claimed_SI": {"n": n2, "kc": kc2, "kphi": kphi2, "c_kPa": c2, "phi_deg": phi2},
             "rel_diff": {"kc": kc_si / kc2 - 1, "kphi": kphi_si / kphi2 - 1,
                          "c": None if c_si is None else c_si / c2 - 1}}
        if name in TYPOS:
            key, wrong, src = TYPOS[name]
            ref = {"c_kPa": c_si, "kphi": kphi_si, "kc": kc_si}[key]
            r["typo_check"] = {"key": key, "secondary_value": wrong, "source": src, "computed": ref,
                               "secondary_rel_diff": wrong / ref - 1, "confirmed_typo": abs(wrong / ref - 1) > 0.01}
        r["max_abs_rel_diff_vs_claimed"] = max(abs(v) for v in r["rel_diff"].values() if v is not None)
        rows[name] = r
    return rows


# soils of survey section 3 (SI, kN units -> N here) for the 1 MPa / bearing recomputation
S3 = {
    "heavy_clay_25": dict(n=0.13, kc=12.70e3, kphi=1555.95e3, c=68.95e3, phi=34.0, survey_z_m=0.024, survey_q_MPa=4.8),
    "lean_clay_22": dict(n=0.20, kc=16.43e3, kphi=1724.69e3, c=68.95e3, phi=20.0, survey_z_m=0.05, survey_q_MPa=1.6),
    "WES_CI207": dict(n=0.365, kc=50.2e3, kphi=3502e3, c=None, phi=None, survey_z_m=0.026, survey_q_MPa=None),
    "chrono_hard": dict(n=1.1, kc=0.0, kphi=2e7, c=None, phi=None, survey_z_m=0.066, survey_q_MPa=None),
    "LETE_sand": dict(n=0.79, kc=102e3, kphi=5301e3, c=1.3e3, phi=31.1, survey_z_m=0.11, survey_q_MPa=0.12),
    "Grenville_loam": dict(n=1.01, kc=0.06e3, kphi=5880e3, c=3.1e3, phi=29.8, survey_z_m=0.17, survey_q_MPa=0.19),
    "sandy_loam_LLL_15": dict(n=0.7, kc=5.27e3, kphi=1515.04e3, c=1.72e3, phi=29.0, survey_z_m=0.54, survey_q_MPa=0.11),
    "chrono_soft": dict(n=1.1, kc=0.0, kphi=2e6, c=None, phi=None, survey_z_m=0.53, survey_q_MPa=None),
    "dry_sand_LLL": dict(n=1.1, kc=0.99e3, kphi=1528.43e3, c=1.04e3, phi=28.0, survey_z_m=0.68, survey_q_MPa=0.07),
    "lean_clay_32": dict(n=0.15, kc=1.52e3, kphi=119.61e3, c=13.79e3, phi=11.0, survey_z_m=None, survey_q_MPa=0.19),
    "heavy_clay_40": dict(n=0.11, kc=1.84e3, kphi=103.27e3, c=20.69e3, phi=6.0, survey_z_m=None, survey_q_MPa=0.21),
    "North_Gower": dict(n=0.73, kc=41.6e3, kphi=2471e3, c=6.1e3, phi=26.6, survey_z_m=None, survey_q_MPa=0.25),
    "K30_147_linear": dict(n=1.0, kc=0.0, kphi=147.1e6, c=None, phi=None, survey_z_m=0.007, survey_q_MPa=None),
}


def regular_octagon_b(area):
    """Survey assumption: regular octagon of the given area -> b = 2A/perimeter."""
    a = math.sqrt(area / (2 * (1 + math.sqrt(2))))
    return 2 * area / (8 * a)


def bekker_z(p, n, kc, kphi, b):
    return (p / (kc / b + kphi)) ** (1.0 / n)


def terzaghi_square(c, phi_deg, B, gamma=GAMMA):
    """Terzaghi square surface footing q = 1.3 c Nc + 0.4 gamma B Ngamma (Df = 0); Ngamma: Coduto approximation."""
    ph = math.radians(phi_deg)
    if ph < 1e-9:
        return 1.3 * 5.7 * c
    a = math.exp((0.75 * math.pi - ph / 2) * math.tan(ph))
    Nq = a * a / (2 * math.cos(math.pi / 4 + ph / 2) ** 2)
    Nc = (Nq - 1) / math.tan(ph)
    Ng = 2 * (Nq + 1) * math.tan(ph) / (1 + 0.4 * math.sin(4 * ph))
    return 1.3 * c * Nc + 0.4 * gamma * B * Ng


def survey_section3_check():
    pv = p0.PV
    b330 = pv["B"]["legs"]["FL"]["b"]
    b250 = pv["B"]["legs"]["RL"]["b"]
    B330 = pv["B"]["legs"]["FL"]["B_sq"]
    B250 = pv["B"]["legs"]["RL"]["B_sq"]
    b_oct = regular_octagon_b(0.1071)
    out = {"b_m": {"survey_regular_octagon_0.1071": b_oct, "P0_330": b330, "P0_250": b250},
           "B_sq_m": {"survey": 0.3, "P0_330": B330, "P0_250": B250}, "rows": {}}
    for name, s in S3.items():
        r = {}
        z_sv = bekker_z(1e6, s["n"], s["kc"], s["kphi"], b_oct)
        r["z_1MPa_m"] = {"survey_def_recomputed": z_sv, "P0_330": bekker_z(1e6, s["n"], s["kc"], s["kphi"], b330),
                         "P0_250": bekker_z(1e6, s["n"], s["kc"], s["kphi"], b250), "survey_value": s["survey_z_m"]}
        if s["survey_z_m"]:
            r["z_1MPa_m"]["survey_rel_diff"] = s["survey_z_m"] / z_sv - 1
        if s["c"] is not None:
            qt = terzaghi_square(s["c"], s["phi"], 0.3)
            r["q_ult_MPa"] = {"terzaghi_square_B0.3_recomputed": qt / 1e6, "survey_value": s["survey_q_MPa"],
                              "P0_vesic_330": p0.bearing_drained(s["c"], s["phi"], B330) / 1e6,
                              "P0_vesic_250": p0.bearing_drained(s["c"], s["phi"], B250) / 1e6,
                              "undrained_(pi+2)1.2c": p0.bearing_undrained(s["c"]) / 1e6}
            if s["survey_q_MPa"]:
                r["q_ult_MPa"]["survey_rel_diff_vs_terzaghi"] = s["survey_q_MPa"] / (qt / 1e6) - 1
        out["rows"][name] = r
    return out


# ---------------------------------------------------------------------------------------------- 2. sets
CHRONO_DEMO = {   # chrono-rag, PyChrono 10.0.0 sources (file:line)
    "SCMLoader ctor default": dict(Kphi=2e6, Kc=0, n=1.1, c=50, phi=20, J=0.01, K=5e7, R=0,
                                   src="src/chrono_vehicle/terrain/SCMTerrain.cpp:392"),
    "SynSCM Soft": dict(Kphi=0.2e6, Kc=0, n=1.1, c=0, phi=30, J=0.01, K=4e7, R=3e4,
                        src="src/chrono_synchrono/agent/SynSCMTerrainAgent.h:152"),
    "SynSCM Mid": dict(Kphi=2e6, Kc=0, n=1.1, c=0, phi=30, J=0.01, K=2e8, R=3e4,
                       src="src/chrono_synchrono/agent/SynSCMTerrainAgent.h:162"),
    "SynSCM Hard (= LETE sand)": dict(Kphi=5301e3, Kc=102e3, n=0.793, c=1.3e3, phi=31.1, J=1.2e-2, K=4e8, R=3e4,
                                      src="src/chrono_synchrono/agent/SynSCMTerrainAgent.h:172"),
    "RigidTire demo": dict(Kphi=0.2e6, Kc=0, n=1.1, c=0, phi=30, J=0.01, K=4e7, R=3e4,
                           src="src/demos/vehicle/terrain/demo_VEH_SCMTerrain_RigidTire.cpp:207"),
    "Curiosity demo": dict(Kphi=0.82e6, Kc=0.14e4, n=1.0, c=0.017e4, phi=35, J=1.78e-2, K=2e8, R=3e4,
                           src="src/demos/robot/curiosity/demo_ROBOT_Curiosity_SCM_Sensor.cpp:102"),
}

SETS = {
    "J1": dict(
        name="heavy_clay_25", label="J1 judgement: heavy clay (WES) 25 % moisture",
        role="judgement (drained c-phi interpretation only)",
        n=0.13, Kc=12.70e3, Kphi=1555.95e3, c=68.95e3, phi=34.0, J=0.01, K=2e8,
        sens={"K_Pa_m": [5e7, 7e8], "Janosi_m": [0.005, 0.025]},
        source="Wong, Theory of Ground Vehicles (Bekker 1969 WES data), survey table 1; imperial n 0.13 / kc 45 / "
               "kphi 140 / c 10 psi / phi 34 deg re-converted here (c 68.95 kPa; NASA TM 69.95 is a typo)",
        basis_K="2e8 Pa/m: P0 / S0 demo level (SynSCM Mid, Wheeled/Tracked demos); Lysmer analogue Vs 100 m/s "
                "gives 1.8e8; no measurement for this clay. Sensitivity 5e7 (low, still >> loading tangent) / 7e8 "
                "(Lysmer Vs 200 m/s, small-strain upper bound)",
        basis_J="ASSUMPTION 0.01 m (Chrono demos / comment 'few mm or cm'); stationary pads: affects only the lateral "
                "force build-up, sensitivity 5 / 25 mm (bevameter range 5 ... 56 mm, survey [10])",
        conditions=["c, phi are bevameter shear-ring values, not geotechnical c', phi' or c_u (survey [3][10])",
                    "p / q_ult <= 1/2 only with the drained reading (c = 68.95 kPa, phi = 34 deg); undrained "
                    "(phi_u = 0, c as c_u) fails (p/q_u 2.6 / 2.8)",
                    "n = 0.13: 1 % pressure -> 7.7 % sinkage; Bekker plate data at <= 0.2 MPa, 1.1 ... 1.2 MPa is "
                    "an extrapolation"]),
    "J2": dict(
        name="lean_clay_22", label="J2 boundary: lean clay (WES) 22 % moisture",
        role="boundary (p/q_ult 0.75 / 0.82 drained: <= 1 but > 1/2)",
        n=0.20, Kc=16.43e3, Kphi=1724.69e3, c=68.95e3, phi=20.0, J=0.01, K=2e8,
        sens={"K_Pa_m": [5e7, 7e8], "Janosi_m": [0.005, 0.025]},
        source="Wong / Bekker WES lean clay 22 %, imperial n 0.20 / kc 45 / kphi 120 / c 10 psi / phi 20 deg "
               "re-converted here (agrees with NASA TM and [4])",
        basis_K="as J1", basis_J="as J1",
        conditions=["as J1 (bevameter c, phi; drained reading only)",
                    "boundary set: shows behaviour near bearing failure that SCM cannot represent"]),
    "G1": dict(
        name="compacted_gravel_K30", label="G1 compacted gravel / work platform (linear, K30-based)",
        role="judgement candidate for stiffness (bearing to be confirmed by a field plate test)",
        n=1.0, Kc=0.0, Kphi=1.5e8, c=0.0, phi=40.0, J=0.01, K=3.5e8,
        sens={"Kphi_K_pairs_Pa_m": [[1.0e8, 2.3e8], [3.0e8, 6.9e8]], "K_Pa_m": [2.5e8, 7e8],
              "phi_deg": [35.0, 45.0], "Janosi_m": [0.005, 0.025]},
        source="NOT a Bekker measurement. Substitute basis: plate-load modulus K30 (KS F 2310, 0.3 m plate) "
               "acceptance values (survey [16], secondary source): subgrade >= 147.1 / 196.1 MN/m^3, "
               "sub-base >= 294 MN/m^3, embankment >= 98.1 MN/m^3; Bowles k_s dense sand 64 ... 128 MN/m^3 [14]. "
               "SCM mapping n = 1, kc = 0, kphi = K30 (survey section 5, investigator's inference)",
        basis_K="ASSUMPTION K = 2.3 kphi (reload / first-load ratio Ev2/Ev1 about 2.0 ... 2.5 for compacted granular "
                "layers, plate-test practice; general knowledge, not from the survey). K must exceed kphi for "
                "n = 1, otherwise Chrono silently sets K = kphi and the soil becomes elastic (no rut). "
                "Sensitivity 2.5e8 (1.7 kphi) / 7e8 (Lysmer Vs 200 m/s)",
        basis_J="ASSUMPTION 0.01 m (no gravel value found)",
        conditions=["K30 is a secant at 1.25 / 2.5 mm settlement (about 0.18 ... 0.5 MPa); 1.1 ... 1.2 MPa with "
                    "n = 1 is a linear extrapolation (real curve softens -> sinkage underestimated)",
                    "plate size: K30 plate 0.30 m vs pads B_sq 0.33 / 0.25 m; Terzaghi size factor for granular soil "
                    "0.92 / 1.23, inside the kphi sensitivity range (kc kept 0)",
                    "c = 0, phi 40 deg are ASSUMPTIONS for SCM shear only (dense gravel phi' 35 ... 45 deg)",
                    "bearing: presumed allowable dense gravel > 600 kPa (CPA, FS 2 in its example), compacted gravel "
                    "400 kPa (CICA), gravel 300 kPa long-term / 450 short-term (Korean rule, appendix 8): "
                    "p 1.11 / 1.20 MPa is at or above q_ult implied by these tables -> field plate test to "
                    ">= 1.5 MPa or a pad mat is required before G1 can be a judgement soil"]),
    "S1": dict(
        name="LETE_sand", label="S1 sensitivity: LETE sand (outside judgement)",
        role="sensitivity only (p/q_ult 9.5 / 11.4: bearing failure in reality, SCM gives finite sinkage)",
        n=0.79, Kc=102e3, Kphi=5301e3, c=1.3e3, phi=31.1, J=0.012, K=2e8,
        sens={"K_Pa_m": [6e7, 4e8], "Janosi_m": [0.005, 0.025]},
        source="Wong LETE sand (NASA TM [1]); same values as Chrono SynSCM 'Hard' preset except n 0.793 "
               "(SynSCMTerrainAgent.h:172)",
        basis_K="2e8 nominal (P0 continuity); 4e8 = Chrono 'Hard' (LETE) preset; 6e7 = Wong repetitive-load "
                "unloading slope k_u = A_u z_u (A_u 503,000 kN/m^4 [24], search excerpt only) at the pad sinkage "
                "0.12 m",
        basis_J="0.012 m: Chrono 'Hard' (LETE) preset / RigidTire demo comment",
        conditions=["not a judgement soil (bearing)", "kept for continuity with 3.11.2 / 5.30.4 / 5.31"]),
}
SANDY_LOAM_NOTE = ("'Sandy loam' names six rows (LLL 15 / 22 %, Michigan 11 / 23 %, Hanamoto 26 / 32 %). None is in the "
                   "sets. If a sandy loam is wanted as a further sensitivity, use 'sandy loam Michigan 23 %' "
                   "(n 0.4, kc 11.42 kN/m^1.4, kphi 808.96 kN/m^2.4, c 9.65 kPa, phi 35 deg), the row already "
                   "screened in P0 (p/q_ult 1.31 / 1.44: fails)")


# ---------------------------------------------------------------------------------------------- 3./4. checks
def design_loads():
    F, _ = p0.twist_free_loads("top")       # contact forces FL FR RL RR (twist-free), N
    return F


def k_checks(s, F):
    out = {}
    for v in ("A", "B"):
        legs = p0.PV[v]["legs"]
        row = {}
        for i, leg in enumerate(dm.LEG_NAMES):
            a, b = legs[leg]["area"], legs[leg]["b"]
            keq = s["Kc"] / b + s["Kphi"]
            z = (F[i] / (a * keq)) ** (1 / s["n"])
            p = F[i] / a
            tangent = s["n"] * p / z
            sx = (keq / s["K"]) ** (1 / (1 - s["n"])) if s["n"] < 1 else None
            row[leg] = {"p_kPa": p / 1e3, "z_mm": z * 1e3, "loading_tangent_Pa_m": tangent,
                        "K_over_tangent": s["K"] / tangent, "virgin_crossover_mm": None if sx is None else sx * 1e3,
                        "elastic_rebound_mm": p / s["K"] * 1e3}
        out[v] = row
    clamp = max(s["K"], s["Kphi"])
    out["chrono_clamp"] = {"K_effective_in_Chrono": clamp, "clamped": clamp != s["K"],
                           "comparison_meaningful": s["n"] == 1.0,
                           "n1_full_condition_K_gt_kc_over_b_plus_kphi": (s["K"] > s["Kc"] / 0.1305 + s["Kphi"])
                           if s["n"] == 1.0 else None}
    return out


def bearing(s, F):
    out = {}
    for v in ("A", "B"):
        legs = p0.PV[v]["legs"]
        p = np.array([F[i] / legs[n]["area"] for i, n in enumerate(dm.LEG_NAMES)])
        qd = np.array([p0.bearing_drained(s["c"], s["phi"], legs[n]["B_sq"]) for n in dm.LEG_NAMES])
        out[v] = {"p_max_kPa": float(p.max() / 1e3), "q_ult_drained_kPa": (qd / 1e3).tolist(),
                  "p_over_qult_drained_max": float((p / qd).max()),
                  "p_over_qult_undrained_max": float(p.max() / p0.bearing_undrained(s["c"])) if s["c"] > 0 else None}
    return out


G1_BEARING_TABLES = {   # survey section 7 (presumed / allowable values, kPa) -> implied q_ult with the stated FS
    "CPA 1402 Annex B dense gravel (allowable, > 600; FS 2 in its example)": {"q_allow_kPa": 600, "FS": 2.0},
    "CPA 1402 medium dense gravel (200 ... 600)": {"q_allow_kPa": 600, "FS": 2.0},
    "CICA/CANZ compacted gravel (max allowable 400; FS not stated, 2 assumed)": {"q_allow_kPa": 400, "FS": 2.0},
    "KR building rule appendix 8 gravel long-term 300 (FS 3 assumed)": {"q_allow_kPa": 300, "FS": 3.0},
    "KR building rule appendix 8 gravel short-term 450 (= 1.5 x long-term, FS 2 implied)": {"q_allow_kPa": 450, "FS": 2.0},
}


def g1_bearing_sweep(F):
    """Vesic surface square footing, c = 0: p/q_ult vs phi per pad type; phi needed for p/q_ult = 1/2 and 1;
    and the q_ult implied by the presumed-bearing tables."""
    out = {"vesic": {}, "tables": {}}
    for v in ("A", "B"):
        legs = p0.PV[v]["legs"]
        p = np.array([F[i] / legs[n]["area"] for i, n in enumerate(dm.LEG_NAMES)])
        B = np.array([legs[n]["B_sq"] for n in dm.LEG_NAMES])

        def ratio(phi):
            return float(max(p[i] / p0.bearing_drained(0.0, phi, B[i]) for i in range(4)))

        row = {f"phi_{ph:.0f}": ratio(ph) for ph in (35.0, 40.0, 45.0, 50.0)}
        for target in (0.5, 1.0):
            lo, hi = 30.0, 60.0
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if ratio(mid) > target else (lo, mid)
            row[f"phi_for_p_over_q_{target}"] = 0.5 * (lo + hi)
        out["vesic"][v] = row
        out["tables"][v] = {k: {"q_ult_implied_kPa": t["q_allow_kPa"] * t["FS"],
                                "p_max_over_q_ult": float(p.max() / 1e3 / (t["q_allow_kPa"] * t["FS"]))}
                            for k, t in G1_BEARING_TABLES.items()}
    return out


def crawler_settle_area(key, s):
    """Crawler settle (legs retracted) on the set, P0 model; returns contact area A_c, mass, z0, pitch."""
    p0.SOILS[key] = dict(n=s["n"], kc=s["Kc"], kphi=s["Kphi"], c=s["c"], phi=s["phi"], role=key, src="sets")
    p0.K_ELASTIC = s["K"]
    m = p0.Model("top", "B", key)
    q = m.settle()
    m.commit(q, np.zeros(4))
    sc = -(m.A_cr @ q + m.chb_flat)
    con = sc > m.c_sp
    A_c = float(con.sum() * p0.H_GRID ** 2)
    # elastic-branch heave stiffness of the crawler contact = K A_c (all contact nodes on the elastic branch)
    return dict(A_c_m2=A_c, mass_kg=m.W / p0.G, z0_mm=q[0] * 1e3, pitch_deg=math.degrees(q[2]),
                roll_deg=math.degrees(q[1]), resid=m.settle_resid,
                crawler_heave_Hz=math.sqrt(s["K"] * A_c / (m.W / p0.G)) / (2 * math.pi))


def lysmer(Vs, nu, R_eq, rho=1800.0):
    G = rho * Vs ** 2
    return {"K_Pa_m": 4 * G / (math.pi * R_eq * (1 - nu)), "R_Pa_s_m": 3.4 * rho * Vs / (math.pi * (1 - nu))}


def soil_damping_modes(s, R):
    """Levelled machine on pads (top level, operating extension): 10-DoF, oil+rod+frame spring (locked leg, no leg
    damping) in series with soil K A || R A; lateral = YAML kt (undamped). Returns lowest modes (f_n, zeta)."""
    P, GEO = p0.P, p0.GEO
    body = dm.body_from_params(P, "top")
    out = {}
    for v in ("A", "B"):
        a = np.array([p0.PV[v]["legs"][n]["area"] for n in dm.LEG_NAMES])
        ko = p0.k_leg(p0.E_OP)
        M, K, C, labels, _ = dm.model_10dof(body, GEO, p0.E_OP, ko, s["K"] * a, p0.KT_YAML, cc=R * a)
        f, z = dm.complex_modes(M, K, C)
        out[v] = {"f_Hz": [float(x) for x in f[:10]], "zeta": [float(x) for x in z[:10]]}
    return out


def main():
    F = design_loads()
    res = {
        "schema": 1,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "generator": {"path": "04_scripts/01_dynamics/export_scm_soil_sets.py",
                      "sha256": sha(Path(__file__))},
        "doc": "00_docs/01_dynamics/dynamics_model.md 5.32 (rev. 46); survey 00_docs/01_dynamics/scm_soil_parameter_survey.md",
        "decision": "user decision 2026-10-25 (soil sets for S9, U-PAD-5: judgement 1 ... 2 + soft 1 sensitivity); "
                    "sets are a PROPOSAL until the user confirms (rev. 46 5.32.8)",
        "inputs": {"survey_md": {"path": str(SURVEY.relative_to(ROOT)), "sha256": sha(SURVEY)},
                   "params_yaml": {"path": str(YAML.relative_to(ROOT)), "sha256": sha(YAML), "use": "read only"},
                   "pad_variants": {"path": str(PADV.relative_to(ROOT)), "sha256": sha(PADV)}},
        "use": "S9 SCM runs: SCMTerrain.SetSoilParameters(Kphi, Kc, n, cohesion, friction, Janosi, elastic_K, "
               "damping_R) with the 'chrono' block of one set. Not part of the YAML / L1 / L2b fingerprints.",
        "units": {"Kphi": "N/m^(n+2)", "Kc": "N/m^(n+1)", "n": "-", "cohesion": "Pa", "friction": "deg",
                  "Janosi": "m", "elastic_K": "Pa/m", "damping_R": "Pa s/m",
                  "note": "Chrono SI: Wong kN-based table x 1000 (Chrono forum 'SCM Terrain Parameter Units', survey [9b])"},
        "frame": "SCM plane = crawler block-bottom plane (z = ground.crawler_bottom_z_m + 0.004, 3.11.2), normal +z body",
        "chrono_source_checks": {
            "elastic_K_clamp": "SetSoilParameters: m_elastic_K = max(elastic_K, Bekker_Kphi) (SCMTerrain.cpp:148-165); "
                               "silent, no warning; numbers compared in different units unless n = 1; Kc/b not included. "
                               "SoilParametersCallback values are used per hit node without this clamp "
                               "(SCMTerrain.cpp:1394-1413)",
            "normal_law": "elastic trial sigma = K (s - s_p); if sigma > sigma_yield: sigma = (oob Kc + Kphi) s^n, "
                          "sigma_yield = sigma, s_p = s - sigma / K (SCMTerrain.cpp:1430-1458); then sigma += -Vn R "
                          "(not clamped; the 'if (Vn < 0)' guard is commented out, 1459-1465)",
            "patch_b": "hit nodes flood-filled into patches with 4-neighbours; per patch ChConvexHull2D of the node "
                       "points m_delta (i, j): oob = perimeter / (2 area), oob = 0 if area < 1e-6 m^2 "
                       "(SCMTerrain.cpp:1316-1378); matches rev. 45 (5.31.2)",
            "tangential": "T = -(v - Vn N) normalised; zero tangential speed -> ChVector3::Normalize sets [1, 0, 0] "
                          "(ChVector3.h:193); kshear += |v_t| dt, never decreases; tau = (c + sigma tan phi)"
                          "(1 - exp(-kshear / Janosi)) along T: no static friction on pads/crawler",
            "chrono_demo_values": CHRONO_DEMO,
        },
        "survey_check": {"conversion": conversion_check(), "section3": survey_section3_check()},
        "design_loads_N": {"FL_FR_RL_RR_contact_twist_free_top": F.tolist()},
        "sets": {},
        "sandy_loam_note": SANDY_LOAM_NOTE,
        "lysmer_reference": {},
    }
    for v in ("A", "B"):
        for leg in ("FL", "RL"):
            R_eq = p0.PV[v]["legs"][leg]["area"]
            R_eq = math.sqrt(R_eq / math.pi)
            for Vs in (100.0, 150.0, 200.0):
                for nu in (0.3, 0.35):
                    res["lysmer_reference"][f"{v}_{leg}_Vs{Vs:.0f}_nu{nu}"] = {"R_eq_m": R_eq, **lysmer(Vs, nu, R_eq)}
    for key, s in SETS.items():
        st = crawler_settle_area(key, s)
        R_rule = 2 * ZETA_CRAWLER * math.sqrt(s["K"] * st["mass_kg"] / st["A_c_m2"])
        R_sens = [3e4, 3e5, 6e5]
        modes = {f"R_{R:.3g}": soil_damping_modes(s, R) for R in [3e4, 3e5, R_rule]}
        entry = {k: v for k, v in s.items() if k not in ("sens",)}
        entry["chrono"] = {"Kphi": s["Kphi"], "Kc": s["Kc"], "n": s["n"], "cohesion": s["c"], "friction": s["phi"],
                           "Janosi": s["J"], "elastic_K": s["K"], "damping_R": float(round(R_rule, -3))}
        entry["chrono_call"] = ("terrain.SetSoilParameters({Kphi:.6g}, {Kc:.6g}, {n}, {cohesion:.6g}, {friction}, "
                                "{Janosi}, {elastic_K:.6g}, {damping_R:.6g})").format(**entry["chrono"])
        entry["sensitivity"] = {**s["sens"], "damping_R_Pa_s_m": R_sens}
        entry["basis_R"] = ("rule 3.11.3: R = 2 zeta sqrt(K m / A_c), zeta 0.2 (YAML damping_ratio_heave_soil) on the "
                            "crawler elastic heave branch, A_c from the P0 crawler settle on this set (C envelope, "
                            "20 mm, hull b); sensitivity 3e4 (Chrono demos), 3e5 / 6e5 (Lysmer analogue Vs 100 / 200 m/s)")
        entry["crawler_settle_P0"] = st
        entry["K_checks"] = k_checks(s, F)
        entry["bearing"] = bearing(s, F)
        if key == "G1":
            entry["bearing_G1"] = g1_bearing_sweep(F)
        entry["explicit_dt_check"] = {
            leg: {"m_moving_part_kg": float(p0.GEO.rod_mass[i]),
                  "dt_stiffness_limit_s_typeA": 2 / math.sqrt(s["K"] * p0.PV["A"]["legs"][leg]["area"] / p0.GEO.rod_mass[i]),
                  "dt_damping_limit_2m_over_RA_s_typeA": 2 * p0.GEO.rod_mass[i] / (R_rule * p0.PV["A"]["legs"][leg]["area"]),
                  "note": "SCM node forces are applied as loads (no Jacobian): explicit; pad body + rod move together "
                          "axially through the swivel; dt 1e-4 s (L2b-NSC) must be below both limits"}
            for i, leg in enumerate(dm.LEG_NAMES)}
        entry["soil_damping_levelled_modes"] = modes
        res["sets"][key] = entry
        print(key, entry["chrono_call"], "A_c", round(st["A_c_m2"], 3), flush=True)
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("wrote", OUT, sha(OUT)[:8].upper())


if __name__ == "__main__":
    main()
