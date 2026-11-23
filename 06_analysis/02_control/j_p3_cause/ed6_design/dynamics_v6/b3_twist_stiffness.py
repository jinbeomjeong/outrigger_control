"""Ed. 6 B3 (R-5 predicted early twist) - dynamics judgement, part 1: twist-mode stiffness,
load transfer per control period, protection latency, false-R-5 exposure (dynamics-expert,
2026-11-23, analysis only).

Model (rigid deck, 4 vertical leg springs k_i in series chains, A = [1, y, -x]):
  S = K - K A (A^T K A)^-1 A^T K = n n^T / (n^T K^-1 n)   (rank 1, A^T n = 0, |n| = 1)
  -> any leg displacement e gives dF = k_tw n (n^T e), k_tw = 1 / sum(n_i^2 / k_i)
  -> the force pattern is always n (zero net force and moments: no rigid-body excitation).
Deck / frame torsion compliance c_d adds in series on the twist coordinate:
  1 / k_tw = sum(n_i^2 / k_i) + c_d.
Units SI (N, m, s); printed kN, mm. Body axes x fwd, y left, z up; legs FL, FR, RL, RR.
Inputs: 02_params/rexome33.yaml (read only), 02_params/scm_soil_sets.json (read only).
Output: JSON next to --out. stdout ASCII status only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(r"C:\workspace\outrigger_control")
LEGS = ("FL", "FR", "RL", "RR")
T_S = 0.1
V_MAX = 0.0209243016
V_TW = 0.25 * V_MAX                 # fastest leg of the twist re-approach (c2.py 1256)
F_MIN = 9414.58911
PROTECT = F_MIN + 5000.0            # c2.py 1259, 6386


def series(*k):
    return 1.0 / sum(1.0 / np.asarray(x, float) for x in k)


def twist_vector(xy):
    A = np.column_stack([np.ones(4), xy[:, 1], -xy[:, 0]])
    u, s, vt = np.linalg.svd(A.T)
    n = vt[-1]
    n = n / np.linalg.norm(n)
    if n[0] < 0:
        n = -n
    assert np.allclose(A.T @ n, 0.0, atol=1e-12)
    return n, A


def find_key(d, key):
    if isinstance(d, dict):
        if key in d:
            return float(d[key])
        for v in d.values():
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def full_S(k, A):
    K = np.diag(k)
    W = A.T @ K
    return K - W.T @ np.linalg.solve(W @ A, W)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = yaml.safe_load((ROOT / "02_params" / "rexome33.yaml").read_text(encoding="utf-8"))
    soil = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))
    act = p["actuator"]
    beta = float(act["oil_bulk_modulus_eff_Pa"])
    L0h = float(act["oil_dead_length_m"])
    L0r = float(act["rod_dead_length_m"])
    stroke = float(act["stroke_m"])
    k_frame = float(act["frame_stiffness_N_m"])
    L1 = p["contact"]["rigid_floor"]["L1"]
    der = L1["derivation"]
    k_rod = np.array([der["k_rod_N_m"][g] for g in LEGS])
    k_conc = float(p["contact"]["rigid_floor"]["concrete"]["k_N_m"])
    Ah = np.array([p["legs"][g]["cylinder"]["head_area_m2"] for g in LEGS])
    Aa = np.array([p["legs"][g]["cylinder"]["annulus_area_m2"] for g in LEGS])
    xy = np.array([[p["legs"][g]["cylinder_axis_xy_m"][1], p["legs"][g]["cylinder_axis_xy_m"][0]]
                   for g in LEGS])
    # cylinder_axis_xy_m is (y, x) per the YAML comment; pad com_m confirms FL x = +2.294, y = +1.324
    n, A = twist_vector(xy)

    # strokes of the harness at the R-5 read of R12_o0.0_VBJ (T4h, 47.7 s): legs near e_op
    s_h = np.array([0.40863, 0.40827, 0.39622, 0.39600])
    e_op = np.array([der["operating_extension_m"][g] for g in LEGS])
    out = {"n": n.round(6).tolist(), "pad_xy_m": xy.tolist(), "max_abs_n": float(np.abs(n).max())}

    def k_oil(s):
        return beta * Ah / (L0h + s)

    def k_rs(s):
        return beta * Aa / (stroke - s + L0r)

    variants = {}
    for tag, s in (("harness_R12", s_h), ("e_op", e_op)):
        ko, kr = k_oil(s), k_rs(s)
        variants[f"move_{tag}"] = series(ko, k_rod, k_frame, k_conc)            # valve open, rod side released
        variants[f"lock_{tag}"] = series(ko + kr, k_rod, k_frame, k_conc)       # L1-R LOCK (rod-side spring)
        variants[f"move_{tag}_beta0.69"] = series(0.69 / 1.0 * ko, k_rod, k_frame, k_conc)
        variants[f"move_{tag}_beta1.6"] = series(1.6 * ko, k_rod, k_frame, k_conc)
    # mixed: extending legs (FL, RR for a RR twist) moving, retracting legs (FR, RL) still locked (VBJ fill)
    km = variants["move_harness_R12"].copy(); kl = variants["lock_harness_R12"]
    variants["mixed_ext_move_ret_lock"] = np.array([km[0], kl[1], kl[2], km[3]])
    # SCM J1 / J2 / G1: concrete replaced by the elastic (unload / reload) branch K_e * A_pad;
    # pad type B: front 0.1071, rear 0.0607 m^2
    a_pad = np.array([0.1071, 0.1071, 0.0607, 0.0607])
    for sname in ("J1", "J2", "G1"):
        Ke = find_key(soil["sets"][sname] if "sets" in soil else soil[sname], "elastic_K")
        variants[f"soil_{sname}_elastic"] = series(k_oil(s_h), k_rod, k_frame, Ke * a_pad)
    stats_eq = {"stats_1e7": np.full(4, 1e7), "stats_2e7": np.full(4, 2e7), "stats_3e7": np.full(4, 3e7)}

    rows = {}
    for name, k in {**variants, **stats_eq}.items():
        k = np.asarray(k, float)
        S = full_S(k, A)
        k_tw = 1.0 / float(np.sum(n**2 / k))
        assert np.allclose(S, k_tw * np.outer(n, n), rtol=1e-9, atol=1e-3 * k_tw)
        # per control period at the fastest-leg twist speed, all four legs moving
        e = n * (V_TW * T_S / np.abs(n).max())
        dF = S @ e
        rows[name] = {"k_leg_MN_m": (k / 1e6).round(3).tolist(), "k_tw_MN_m": round(k_tw / 1e6, 3),
                      "dF_per_period_kN": (dF / 1e3).round(3).tolist(),
                      "k_equiv_stats_MN_m": (np.abs(dF) / (V_TW * T_S) / 1e6).round(3).tolist(),
                      "net_force_moment_of_dF": float(np.abs(A.T @ dF).max())}
    # deck torsion compliance (unknown on the machine; harness / Chrono deck is rigid)
    k_tw_h = rows["move_harness_R12"]["k_tw_MN_m"] * 1e6
    deck = {}
    for kd in (math.inf, 2e8, 1e8, 5e7, 2.5e7):
        ktw = 1.0 / (1.0 / k_tw_h + (0.0 if math.isinf(kd) else 1.0 / kd))
        deck[str(kd)] = {"k_tw_MN_m": round(ktw / 1e6, 3),
                         "dF_fastest_kN": round(ktw * V_TW * T_S / np.abs(n).max() * np.abs(n).max() / 1e3, 3)}
    out["variants"] = rows
    out["deck_torsion_series"] = deck
    out["notes"] = {"V_TW_mm_s": V_TW * 1e3, "per_period_fastest_mm": V_TW * T_S * 1e3,
                    "protect_level_kN": PROTECT / 1e3}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ok n=", np.round(n, 4).tolist(), "k_tw move/lock MN/m =",
          rows["move_harness_R12"]["k_tw_MN_m"], rows["lock_harness_R12"]["k_tw_MN_m"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
