"""S6 branch A final judgement support (dynamics_model.md 5.10, rev. 23).

Usage (project root, dynamics-dev):
    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_s6_check.py \
        --batch 07_results/S6/<batch_dir> \
        --verify 06_analysis/01_chrono/16_S6/verify_S6_L1_infra.json \
        [params.yaml [out.json [reference.json]]]
--batch (folder with v11b_*/series.npz) and --verify (the S6 verify JSON of that batch) are
required on purpose, so that an old batch is never analysed silently. The positional arguments
are optional: params (default 02_params/rexome33.yaml), output (default
06_analysis/00_dynamics/s6_check.json) and reference (default 06_analysis/00_dynamics/
reference.json). Relative paths are taken from the current directory.
Runs about 25 s. Independent of 03_src: reads the YAML text, the S6 verify JSON, the raw V11b
series and s1_pdelta_check.json only.
Reproducing s6_check.json for batch_20261021_190700 (pre-REXOME35):
    --batch 07_results/S6/batch_20261021_190700 --verify <its verify JSON>
    02_params/history/rexome33_2026-10-22_before_rexome35.yaml

Leg axis convention: + = extend = pad pushed down; gravity g = 9.80665 m/s^2 acts along +.
Cylinder force F_cyl (+ = pushes the pad down) = Chrono motor force (R4). For the rod
    m_rod a = F_cyl + m_rod g - F_spring    ->  F_cyl = m_rod a - m_rod g + F_spring.

A  Raw V11b series: creep after the first saturated step, time of the last motor motion, the
   settled spring force, and the inertial part of the force reading
   m_rod a_chrono = F_cyl + m_rod g - F_spring compared with m_rod du_applied/dt (shift 0 / 1),
   which tells which acceleration a stateless correction must use.
B  1-DoF replica of the single-leg test (rigid position motor, motor position exact at step
   end, rod speed = applied speed of the step, two-way spring k_n / damper c_n) with three
   saturation-stop laws:
     A  one-step cut u -> 0 (current code)
     B  stop ramp t_sat, decision on the raw reading F_cyl
     C  stop ramp t_sat, decision on F_cyl - m_rod a (a of the step just taken)
   t_sat = 2 ms (ASSUMPTION, relief / compensator response order), lag 0 / 1 extra step.
C  Physical reference: oil column k_oil(e_op) in series with the outside stiffness
   k_out = 1 / (1/k_n - 1/k_oil), ideal relief valve (head force clamped at F_ext), flow =
   ramped speed command (pressure-compensated), damping c_n on the outside spring
   (ASSUMPTION: damping location). dt 1e-6 s semi-implicit Euler.
D  V17: settled maxima vs P-delta nonlinear statics (s1_pdelta_check.json nonlinear_cyl_N) and
   vs the linear reference; tolerances 0.01 % W/4 (U2 = B) and 1 % / 0.1 % W/4.
E  k_oil(e) = beta A_head / (L0 + e) with the L1 lumped k_n fixed: stroke_true difference and
   the implied outside compliance 1/k_n - 1/k_oil(e).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
PDELTA = ROOT / "06_analysis/00_dynamics/s1_pdelta_check.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="S6 branch A judgement support (dynamics_model.md 5.10).")
    parser.add_argument("--batch", type=Path, required=True,
                        help="S6 batch folder holding v11b_<case>/series.npz (no default: never use an old batch silently)")
    parser.add_argument("--verify", type=Path, required=True,
                        help="S6 verify JSON of the same batch (v11b / v17 blocks)")
    parser.add_argument("params", type=Path, nargs="?", default=ROOT / "02_params/rexome33.yaml",
                        help="params YAML (default: project YAML)")
    parser.add_argument("out", type=Path, nargs="?", default=ROOT / "06_analysis/00_dynamics/s6_check.json",
                        help="output JSON (default: 06_analysis/00_dynamics/s6_check.json)")
    parser.add_argument("reference", type=Path, nargs="?", default=ROOT / "06_analysis/00_dynamics/reference.json",
                        help="reference JSON (default: 06_analysis/00_dynamics/reference.json)")
    args = parser.parse_args()
    if not args.batch.is_dir():
        parser.error(f"--batch is not a folder: {args.batch}")
    if not args.verify.is_file():
        parser.error(f"--verify is not a file: {args.verify}")
    return args


ARGS = _parse_args()
BATCH = ARGS.batch
VERIFY = ARGS.verify
REFERENCE = ARGS.reference
OUT = ARGS.out

G = 9.80665
T_SAT = 2.0e-3  # ASSUMPTION: saturation stop time (relief / compensator response order)

# rev. 30: the params YAML must match the batch (batch_20261021_190700 ran on the pre-REXOME35 YAML
# 02_params/history/rexome33_2026-10-22_before_rexome35.yaml). Force limits and v_max come per case from the run
# metadata (model.force_limits_N, model.max_speed_m_s, model.ramp_s); head areas per leg from legs.<leg>.cylinder
# (pi/4 bore^2) or the old common actuator.bore_diameter_m.
PARAMS = ARGS.params
params = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
act = params["actuator"]
LEG_NAMES = ("FL", "FR", "RL", "RR")
A_HEAD_LEGS = np.array([math.pi / 4.0 * float(((params["legs"][n].get("cylinder") or {}).get("bore_diameter_m",
                                                                                            act["bore_diameter_m"]))) ** 2
                        for n in LEG_NAMES])
A_HEAD = float(A_HEAD_LEGS[0])  # FL (the V11b / physical reference leg)
BETA = float(act["oil_bulk_modulus_eff_Pa"])
L0 = float(act["oil_dead_length_m"])

verify = json.loads(VERIFY.read_text(encoding="utf-8"))
pdelta = json.loads(PDELTA.read_text(encoding="utf-8"))
reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
W = float(pdelta["top"]["W_N"])
_m_fl = verify["v11b"]["v11b_FL_dt2e-4"]["model"]
V_MAX = float(_m_fl["max_speed_m_s"])
RAMP = float(_m_fl["ramp_s"])
F_EXT, F_RET = (float(x) for x in _m_fl["force_limits_N"])  # FL limits; per case below where the leg differs


def _per_leg(a):
    """Scalar while all legs are equal (old output format), else the per-leg list."""
    a = np.asarray(a, float)
    return float(a[0]) if np.all(a == a[0]) else a.tolist()

res: dict = {
    "meta": {
        "script": "04_scripts/01_dynamics/run_s6_check.py",
        "t_sat_s_assumed": T_SAT,
        "gravity_m_s2": G,
        "axis": "+ = extend = pad down",
        "A_head_m2": _per_leg(A_HEAD_LEGS),
        "params": str(PARAMS),
        "batch": str(BATCH),
        "verify": str(VERIFY),
    }
}

PHASES = {"extend": (0.1, 3.0, 1.0, F_EXT), "retract": (3.0, 5.5, -1.0, F_RET)}

# ---------------------------------------------------------------- A raw V11b series
raw = {}
for case in ["v11b_FL_dt2e-4", "v11b_RL_dt2e-4", "v11b_FL_dt1e-5"]:
    mdl = verify["v11b"][case]["model"]
    m_rod, k, c, dt = (
        mdl["rod_mass_kg"],
        mdl["spring"]["k_N_m"],
        mdl["spring"]["c_N_s_m"],
        mdl["dt_s"],
    )
    _fe, _fr = (float(x) for x in mdl["force_limits_N"])  # this case's leg (rev. 30)
    PHASES = {"extend": (0.1, 3.0, 1.0, _fe), "retract": (3.0, 5.5, -1.0, _fr)}
    z = np.load(BATCH / case / "series.npz")
    t, F, s, Fs, ua, sat = (
        z[n] for n in ["t", "F_cyl", "s_motor", "F_spring", "u_applied", "saturated"]
    )
    sat = sat.astype(bool)
    inertia = F + m_rod * G - Fs  # m_rod a seen in the reading
    du = np.diff(ua, prepend=ua[0]) / dt
    fit = {}
    for shift in (0, 1):
        pred = m_rod * np.roll(du, shift)
        fit[f"shift{shift}"] = float(np.max(np.abs(inertia[2:] - pred[2:])))
    out = {
        "k_N_m": k,
        "c_N_s_m": c,
        "dt_s": dt,
        "creep_pred_um": c * V_MAX / k * 1e6,
        "inertia_reading_max_abs_N": float(np.max(np.abs(inertia))),
        "inertia_minus_m_du_dt_max_abs_N": fit,
    }
    for name, (t0, t1, sign, lim) in PHASES.items():
        idx = np.flatnonzero((t > t0) & (t <= t1) & (sign * ua >= 0.0))
        idx = idx[t[idx] > t[idx[0]] + 0.05]  # skip the leftover flag of the previous phase
        j = idx[sat[idx]][0]
        seg = idx[idx >= j]
        pos = s[seg] * sign
        mv = np.flatnonzero(np.abs(np.diff(s[seg])) > 1e-12)
        last = seg[t[seg] > t1 - 0.5]
        out[name] = {
            "t_first_sat_s": float(t[j]),
            "creep_from_first_um": float((pos.max() - pos[0]) * 1e6),
            "creep_over_pred": float((pos.max() - pos[0]) / (c * V_MAX / k)),
            "last_motion_after_first_s": float(t[seg][mv[-1] + 1] - t[j]) if mv.size else 0.0,
            "settled_window_motion_um": float(
                (
                    (s[seg] * sign)[t[seg] >= t[j] + 0.5].max()
                    - (s[seg] * sign)[t[seg] >= t[j] + 0.5][0]
                )
                * 1e6
            ),
            "cut_steps": int(sat[seg].sum()),
            "cut_onsets": int(np.sum(np.diff(sat[seg].astype(int)) == 1) + 1),
            "F_cyl_last0p5s_over_limit": float(sign * F[last].mean() / lim),
            "pad_force_last0p5s_N": float(Fs[last].mean()),
            "pad_minus_cyl_last0p5s_N": float(Fs[last].mean() - F[last].mean()),
            "reading_min_max_N": [float(F[seg].min()), float(F[seg].max())],
            "peak_over_limit": float((sign * F[seg]).max() / lim),
        }
    raw[case] = out
res["A_raw_v11b"] = raw


# ---------------------------------------------------------------- B replica
def replica(
    dt: float, law: str, k: float, c: float, m_rod: float, lag: int = 0, t_end: float = 6.0
):
    n = int(round(t_end / dt))
    a_cmd = V_MAX / RAMP
    a_sat = V_MAX / T_SAT
    x = 0.0
    u = 0.0
    hist = [0.0, 0.0] + [0.0] * lag
    F = -m_rod * G
    acc_last = 0.0
    T = np.empty(n)
    FF = np.empty(n)
    X = np.empty(n)
    for i in range(n):
        t = i * dt
        cmd = 0.0
        if 0.1 - 1e-12 <= t < 3.0 - 1e-12:
            cmd = V_MAX
        elif 3.0 - 1e-12 <= t < 5.5 - 1e-12:
            cmd = -V_MAX
        elif t >= 5.5 - 1e-12:
            cmd = V_MAX
        u_new = u + float(np.clip(cmd - u, -a_cmd * dt, a_cmd * dt))
        if law == "A":
            if (F >= F_EXT and u_new > 0) or (F <= -F_RET and u_new < 0):
                u_new = 0.0
        else:
            Fd = F - m_rod * acc_last if law == "C" else F
            if (Fd >= F_EXT and u > 0) or (Fd <= -F_RET and u < 0):
                u_new = math.copysign(max(abs(u) - a_sat * dt, 0.0), u)
            elif (Fd >= F_EXT and u_new > 0) or (Fd <= -F_RET and u_new < 0):
                u_new = 0.0
        u = u_new
        hist.append(u)
        u_act, u_prev = hist[-1 - lag], hist[-2 - lag]
        x += u_act * dt
        acc_last = (u_act - u_prev) / dt
        F = m_rod * acc_last - m_rod * G + k * x + c * u_act
        T[i], FF[i], X[i] = t + dt, F, x
        hist = hist[-(lag + 3) :]
    out = {}
    for name, (t0, t1, sign, lim) in PHASES.items():
        idx = np.flatnonzero((T > t0) & (T <= t1))
        hit = idx[(sign * FF[idx]) >= lim]
        j = hit[0]
        seg = idx[idx >= j]
        pos = X[seg] * sign
        st = seg[T[seg] >= T[j] + 0.5]
        x_end = X[seg[-1]]
        out[name] = {
            "creep_from_first_um": float((pos.max() - pos[0]) * 1e6),
            "settled_window_motion_um": float(((X[st] * sign).max() - X[st[0]] * sign) * 1e6),
            "peak_over_limit": float((sign * FF[seg]).max() / lim),
            "reading_dip_below_limit_N": float(lim - (sign * FF[seg]).min()),
            "static_cyl_force_end_over_limit": float(sign * (k * x_end - m_rod * G) / lim),
        }
    return out


rep = {}
PHASES = {"extend": (0.1, 3.0, 1.0, F_EXT), "retract": (3.0, 5.5, -1.0, F_RET)}  # FL limits for the FL replica
mdl = verify["v11b"]["v11b_FL_dt2e-4"]["model"]
kFL, cFL, mROD = mdl["spring"]["k_N_m"], mdl["spring"]["c_N_s_m"], mdl["rod_mass_kg"]
for dt in (2e-4, 1e-5):
    for law in ("A", "B", "C"):
        for lag in (0, 1):
            rep[f"dt{dt:g}_law{law}_lag{lag}"] = replica(dt, law, kFL, cFL, mROD, lag)
res["B_replica_FL"] = rep
res["B_expected"] = {
    "creep_c_v_over_k_um": cFL * V_MAX / kFL * 1e6,
    "one_step_inertia_N": {"2e-4": mROD * V_MAX / 2e-4, "1e-5": mROD * V_MAX / 1e-5},
    "t_sat_inertia_N": mROD * V_MAX / T_SAT,
    "t_sat_static_overshoot_without_damping_N": kFL * V_MAX * T_SAT / 2,
    "damping_force_at_vmax_N": cFL * V_MAX,
    "t_sat_no_static_overshoot_bound_s": 2 * cFL / kFL,
    "ramp_0p1s_overshoot_N": kFL * V_MAX * RAMP / 2,
    "ramp_0p1s_overshoot_over_limits": [
        kFL * V_MAX * RAMP / 2 / F_EXT,
        kFL * V_MAX * RAMP / 2 / F_RET,
    ],
}

# ---------------------------------------------------------------- C physical reference
e_FL = float(verify["v11b"]["v11b_FL_dt2e-4"]["model"]["extension0_m"])
k_oil = BETA * A_HEAD / (L0 + e_FL)
k_out = 1.0 / (1.0 / kFL - 1.0 / k_oil)


def physical(dt: float = 1e-6, t_end: float = 2.0) -> dict:
    n = int(t_end / dt)
    a_cmd = V_MAX / RAMP
    x = v = u = 0.0
    y = -mROD * G / k_oil
    Fp_all = np.empty(n)
    X = np.empty(n)
    Y = np.empty(n)
    clamp = np.zeros(n, dtype=bool)
    for i in range(n):
        t = i * dt
        cmd = V_MAX if 0.1 <= t < 3.0 else 0.0
        u += float(np.clip(cmd - u, -a_cmd * dt, a_cmd * dt))
        y += u * dt
        Fp = k_oil * (y - x)
        if Fp > F_EXT:
            y = x + F_EXT / k_oil
            Fp = F_EXT
            clamp[i] = True
        acc = (Fp + mROD * G - k_out * x - cFL * v) / mROD
        v += acc * dt
        x += v * dt
        Fp_all[i], X[i], Y[i] = Fp, x, y
    t = np.arange(1, n + 1) * dt
    j = int(np.flatnonzero(clamp)[0])
    return {
        "k_oil_N_m": k_oil,
        "k_out_N_m": k_out,
        "t_first_relief_s": float(t[j]),
        "piston_creep_from_first_um": float((X[j:].max() - X[j]) * 1e6),
        "oil_coordinate_creep_from_first_um": float((Y[j:].max() - Y[j]) * 1e6),
        "creep_pred_c_v_over_k_out_um": cFL * V_MAX / k_out * 1e6,
        "head_force_max_over_limit": float(Fp_all.max() / F_EXT),
        "head_force_min_after_first_N": float(Fp_all[j:].min()),
        "rod_natural_frequency_Hz": math.sqrt((k_oil + k_out) / mROD) / (2 * math.pi),
    }


res["C_physical_relief_FL"] = physical()

# ---------------------------------------------------------------- D V17
lin = reference["chrono_test_references"]["L1_rigid_motor_lumped_contact"]["levels"]
v17 = {
    "tol_pdelta_N": 1e-4 * W / 4,
    "tol_pdelta_Pa": _per_leg(1e-4 * W / 4 / A_HEAD_LEGS),
    "tol_linear_1pct_Pa": _per_leg(1e-2 * W / 4 / A_HEAD_LEGS),
    "tol_linear_0p1pct_Pa": _per_leg(1e-3 * W / 4 / A_HEAD_LEGS),
    # scalar (common bore, FL value) or per-leg list (rev. 30 reference.json, NUMBER_ARRAY)
    "ref_max_static_head_pressure_Pa": _per_leg(np.atleast_1d(np.asarray(
        reference["hydraulic_circuit"]["max_static_head_pressure_Pa"], float))),
}
for lvl in ("top", "middle", "bottom"):
    case = verify["v17"][f"v17_{lvl}"]
    fmax = np.array(case["monitor"]["cylinder_force_max_N"])
    fmean = np.array(case["cylinder_force"]["mean_N"])
    pdf = np.array(pdelta[lvl]["nonlinear_cyl_N"])
    lnf = np.array(lin[lvl]["cylinder_force_N"])
    pmax = case["v17"]["true_pressure"]["locked_only"]["max_pressure_Pa"]
    v17[lvl] = {
        "max_minus_pdelta_N": (fmax - pdf).tolist(),
        "mean_minus_pdelta_N": (fmean - pdf).tolist(),
        "max_minus_linear_N": (fmax - lnf).tolist(),
        "pmax_Pa": pmax,
        "pmax_minus_pdelta_Pa": pmax - float(np.max(pdf / A_HEAD_LEGS)),
        "pmax_minus_linear_Pa": pmax - float(np.max(lnf / A_HEAD_LEGS)),
        "pdelta_head_pressure_max_Pa": float(np.max(pdf / A_HEAD_LEGS)),
    }
res["D_v17"] = v17

# ---------------------------------------------------------------- E k_oil(e)
ko = {}
for case, Fop in (
    ("v11b_FL_dt2e-4", verify["v17"]["v17_top"]["cylinder_force"]["mean_N"][0]),
    ("v11b_RL_dt2e-4", verify["v17"]["v17_top"]["cylinder_force"]["mean_N"][2]),
):
    mdl = verify["v11b"][case]["model"]
    kn, e_op = mdl["spring"]["k_N_m"], mdl["extension0_m"]
    A_leg = float(A_HEAD_LEGS[LEG_NAMES.index(mdl["leg"])])  # this case's leg (rev. 30)
    k_op = BETA * A_leg / (L0 + e_op)
    rows = []
    for de in (-0.3, -0.1, -0.05, 0.05, 0.1, 0.2):
        ke = BETA * A_leg / (L0 + e_op + de)
        inv_out = 1 / kn - 1 / ke
        rows.append(
            {
                "de_m": de,
                "k_oil_e_N_m": ke,
                "stroke_true_shift_mm": (Fop / ke - Fop / k_op) * 1e3,
                "implied_outside_compliance_m_N": inv_out,
                "implied_outside_stiffness_N_m": 1 / inv_out if inv_out > 0 else None,
            }
        )
    ko[mdl["leg"]] = {
        "e_op_m": e_op,
        "k_n_N_m": kn,
        "k_oil_op_N_m": k_op,
        "k_out_N_m": 1 / (1 / kn - 1 / k_op),
        "oil_share_of_lumped_compliance": kn / k_op,
        "F_op_N": Fop,
        "F_over_k_oil_op_mm": Fop / k_op * 1e3,
        "e_where_k_oil_eq_kn_m": BETA * A_leg / kn - L0,
        "rows": rows,
    }
res["E_k_oil"] = ko

OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False))
