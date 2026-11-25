"""Ed. 7 dynamics review (dynamics-expert, 2026-11-24; analysis only, no simulation).

Part A (Q7-D2): external axial stiffness k_ext that restrains leg i from shortening while its own
head column (k_h) yields under the rod-side fill of a probe retraction (harness P1 ``need`` head
term). Rigid deck on four leg springs (as harness, L1-R, L2b; dynamics_v6 b3 report 0):

    imposed length change at leg i, leg i spring = k'_i (everything in series with the piston
    except its head column: k_rod, k_frame, contact), other legs j = k_j (their state):
    k_ext,i = S'_ii = n_i^2 / ( n_i^2 / k'_i + sum_{j != i} n_j^2 / k_j + c_deck )
    (S' = K' - K'A (A^T K' A)^-1 A^T K'; checked numerically against the 4x4 matrix.)

  The ed. 6 hydraulics review used k_ext = k_tw = 21.7 MN/m (twist stiffness of the D = n.F
  coordinate, all four legs moving, own oil column included); the per-leg value of that same
  quantity is k_tw n_i^2. Part A shows both and the consistent k_ext.

  Then the P1 retract dead stroke (``check_open_delay.retract_dead`` generalised by
  r = k_h / (k_h + k_ext); the formula of ed6 hydraulics ``h4_need_corners.retract``, copied
  unchanged) for the FL state of R12 top-*-Fs0 (p_h 99.39 bar, p_r 5.07 bar, s 408.36 mm,
  delivered 2.098 mm), checked against the harness function of run commit 79495405 for r = 1.

Part B (Q7-D1): what one A(i)-b shot (leg i, Delta e) does to the attitude, heave and twist
load D: q = (A^T K A)^-1 A^T K de, dF = K (de - A q); K with the shooting leg(s) moving and
the others locked. Single legs and pairs.

Conventions: body x fwd, y left, z up; legs FL, FR, RL, RR; z_i = h + phi y_i - theta x_i
(theta > 0 = nose down); compression +; pressures gauge. Units SI, printed MN/m, mm, kN, deg.
Inputs (read only): 02_params/rexome33.yaml, 02_params/scm_soil_sets.json,
ed6_design/dynamics_v6/b3_twist_stiffness.json, worktree ed6-run6 (import, r = 1 check).
Output: JSON at --out. stdout ASCII.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(r"C:\workspace\outrigger_control")
WT = ROOT / ".claude" / "worktrees" / "ed6-run6"
LEGS = ("FL", "FR", "RL", "RR")
BAR = 1e5


def series(*k):
    return 1.0 / sum(1.0 / np.asarray(x, float) for x in k)


def full_S(k, A):
    K = np.diag(k)
    W = A.T @ K
    return K - W.T @ np.linalg.solve(W @ A, W)


def find_key(d, key):
    if isinstance(d, dict):
        if key in d:
            return float(d[key])
        for v in d.values():
            r = find_key(v, key)
            if r is not None:
                return r
    return None


# ---- P1 retract dead stroke with k_ext (copy of ed6 hydraulics h4_need_corners.retract) ----
A_H, A_ANN = 0.013273229, 0.00376991118
S_MAX = 0.7


@dataclass(frozen=True)
class Case:
    name: str
    beta: float = 1.0e9
    l0r: float = 0.05
    l0h: float = 0.05
    v_line: float = 285e-6
    beta_hose: float = 0.5e9
    psi: float = 3.5
    p_cr: float = 3e5
    p_t: float = 2e5
    scale: float = 1.0
    k_ext: float = 0.0


def retract(case: Case, p_h: float, p_r: float, band: float, s: float) -> dict:
    v_head = A_H * (case.l0h + s)
    k_h = case.beta * A_H ** 2 / v_head
    r = k_h / (k_h + case.k_ext)
    delta = case.p_cr
    drive = max(p_h, 0.0) + case.p_cr - case.p_t
    p_free = max(drive / case.psi, 0.0)
    if A_ANN * (p_free - delta - p_r) > band:
        p_b = (drive - r * (A_ANN * (delta + p_r) + band) / A_H) / (case.psi - r * A_ANN / A_H)
    else:
        p_b = p_free
    p_rod = max(p_b - delta, p_r)
    yield_m = max(A_ANN * (p_rod - p_r) - band, 0.0) / (k_h + case.k_ext)
    v_rod = A_ANN * (case.l0r + S_MAX - s)
    line = case.scale * case.v_line * max(p_b - case.p_t, 0.0) / case.beta_hose
    rod = case.scale * v_rod * (p_rod - p_r) / case.beta
    head = case.scale * A_ANN * yield_m
    need = (line + rod + head) / A_ANN
    return {"need_mm": need * 1e3, "head_mm": head / A_ANN * 1e3, "p_b_bar": p_b / BAR,
            "yield_mm": yield_m * 1e3, "dF_leg_kN": -case.k_ext * yield_m / 1e3, "k_h": k_h, "r": r}


def harness_need_r1(case: Case, p_h, p_r, band, s) -> float:
    sys.path.insert(0, str(WT / "03_src"))
    from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa
    cfg = RetractConfig(rod_forward=True, volume_scale=case.scale, v_line_m3=case.v_line,
                        beta_hose_Pa=case.beta_hose, psi=case.psi, p_crack_Pa=case.p_cr)
    out = retract_dead(cfg, p_h, p_r, band, s, 0.0, A_H, A_ANN, S_MAX, case.l0r, case.l0h,
                       case.beta, case.p_t)
    return out["need"] * 1e3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = yaml.safe_load((ROOT / "02_params" / "rexome33.yaml").read_text(encoding="utf-8"))
    soil = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))
    b3 = json.loads((ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "ed6_design"
                     / "dynamics_v6" / "b3_twist_stiffness.json").read_text(encoding="utf-8"))
    act = p["actuator"]
    beta = float(act["oil_bulk_modulus_eff_Pa"])
    L0h, L0r = float(act["oil_dead_length_m"]), float(act["rod_dead_length_m"])
    stroke = float(act["stroke_m"])
    k_frame = float(act["frame_stiffness_N_m"])
    der = p["contact"]["rigid_floor"]["L1"]["derivation"]
    k_rod = np.array([der["k_rod_N_m"][g] for g in LEGS])
    k_conc = float(p["contact"]["rigid_floor"]["concrete"]["k_N_m"])
    Ah = np.array([p["legs"][g]["cylinder"]["head_area_m2"] for g in LEGS])
    Aa = np.array([p["legs"][g]["cylinder"]["annulus_area_m2"] for g in LEGS])
    yx = np.array(b3["pad_xy_m"])          # printed (y, x) in the b3 json
    x, y = yx[:, 1], yx[:, 0]
    A = np.column_stack([np.ones(4), y, -x])
    n = np.linalg.svd(A.T)[2][-1]
    n = n / np.linalg.norm(n) * (1.0 if n[0] > 0 else -1.0)
    assert np.allclose(n, np.array(b3["n"]), atol=1e-6)
    assert np.allclose(A.T @ n, 0.0, atol=1e-12)
    s_h = np.array([0.40863, 0.40827, 0.39622, 0.39600])   # harness R12 strokes (b3 report)
    a_pad = np.array([0.1071, 0.1071, 0.0607, 0.0607])
    out: dict = {"n": n.tolist()}

    def k_oil(b=beta):
        return b * Ah / (L0h + s_h)

    def k_rs(b=beta):
        return b * Aa / (stroke - s_h + L0r)

    def legs(b=beta, k_c=k_conc):
        k_st = series(k_rod, k_frame, k_c)
        return {"st": k_st, "move": series(k_oil(b), k_st), "lock": series(k_oil(b) + k_rs(b), k_st)}

    # ---------------- Part A: k_ext ----------------
    def k_ext_of(i, kk, others, c_d=0.0):
        k = np.array([kk[o][j] if j != i else kk["st"][j] for j, o in enumerate(others)])
        val = n[i] ** 2 / (float(np.sum(n**2 / k)) + c_d)
        if c_d == 0.0:
            S = full_S(k, A)
            assert math.isclose(S[i, i], val, rel_tol=1e-9)
        return val

    rows = {}
    variants = {
        "others_locked (L1-R LOCK, beta 1.0)": (legs(), "lock_all", 0.0),
        "load-gaining legs at rod floor (mixed)": (legs(), "mixed", 0.0),
        "others moving (oil only)": (legs(), "move_all", 0.0),
        "others_locked, beta 0.69": (legs(0.69e9), "lock_all", 0.0),
        "others_locked, beta 1.6": (legs(1.6e9), "lock_all", 0.0),
        "others_locked, deck torsion k_d 1e8": (legs(), "lock_all", 1e-8),
        "others_locked, deck torsion k_d 5e7": (legs(), "lock_all", 2e-8),
    }
    for sname in ("J1", "G1"):
        Ke = find_key(soil["sets"][sname] if "sets" in soil else soil[sname], "elastic_K")
        variants[f"others_locked, SCM {sname} elastic pad"] = (legs(k_c=Ke * a_pad), "lock_all", 0.0)
    for name, (kk, mode, c_d) in variants.items():
        vals = []
        for i in range(4):
            if mode == "lock_all":
                others = ["lock"] * 4
            elif mode == "move_all":
                others = ["move"] * 4
            else:   # legs with n_j of opposite sign to n_i gain load -> rod spring at floor
                others = ["move" if np.sign(n[j]) != np.sign(n[i]) else "lock" for j in range(4)]
            vals.append(k_ext_of(i, kk, others, c_d))
        rows[name] = [round(v / 1e6, 3) for v in vals]
    k_h_leg = beta * Ah / (L0h + s_h)
    out["k_ext_MN_m"] = rows
    out["k_h_head_column_MN_m"] = (k_h_leg / 1e6).round(3).tolist()
    out["k_st_MN_m"] = (legs()["st"] / 1e6).round(3).tolist()
    ktw_move = 1.0 / float(np.sum(n**2 / legs()["move"]))
    out["misuse"] = {"k_tw_all_moving_MN_m": round(ktw_move / 1e6, 3),
                     "k_tw_n_i^2_MN_m": (ktw_move * n**2 / 1e6).round(3).tolist()}

    # need of FL, v15 Fs0 and other cases, k_ext 0 / mixed / locked / 21.7 (ed6 hydraulics)
    kx_lock = rows["others_locked (L1-R LOCK, beta 1.0)"][0] * 1e6
    kx_mix = rows["load-gaining legs at rod floor (mixed)"][0] * 1e6
    kx_scm = rows["others_locked, SCM J1 elastic pad"][0] * 1e6
    p_h, p_r, s = 99.39 * BAR, 5.07 * BAR, 0.40836
    deliv = 2.098
    nominal = Case("nominal")
    cases = [replace(nominal, name="harness volume_scale 1.0"),
             replace(nominal, name="harness volume_scale 1.5 (VBLv15)", scale=1.5),
             replace(nominal, name="(c) dead volumes x1.5 (hose, L0r, L0h)", v_line=427.5e-6,
                     l0r=0.075, l0h=0.075),
             replace(nominal, name="beta 0.69 + hose x2", beta=0.69e9, v_line=570e-6),
             replace(nominal, name="beta 0.69 + hose x2 + L0r 0.1 + L0h 0.08", beta=0.69e9,
                     v_line=570e-6, l0r=0.10, l0h=0.08)]
    need_rows = []
    check = {}
    for c in cases:
        for band in (0.0, 4e3):
            for kname, kx in (("0", 0.0), ("SCM_J1_locked", kx_scm), ("mixed", kx_mix),
                              ("locked", kx_lock), ("ed6_hyd_21.7", 21.7e6)):
                r = retract(replace(c, k_ext=kx), p_h, p_r, band, s)
                need_rows.append({"case": c.name, "band_kN": band / 1e3, "k_ext": kname,
                                  "k_ext_MN_m": round(kx / 1e6, 3),
                                  "need_mm": round(r["need_mm"], 3),
                                  "head_mm": round(r["head_mm"], 3),
                                  "yield_mm": round(r["yield_mm"], 3),
                                  "dF_leg_kN": round(r["dF_leg_kN"], 2),
                                  "delivered_over_need": round(deliv / r["need_mm"], 3)})
            check[f"{c.name} band {band / 1e3:.0f}"] = (
                round(retract(c, p_h, p_r, band, s)["need_mm"], 6),
                round(harness_need_r1(c, p_h, p_r, band, s), 6))
    out["need_FL_R12_Fs0"] = need_rows
    out["r1_check_hand_vs_harness_mm"] = check

    # ---------------- Part B: one shot ----------------
    kk = legs()
    shots = {}
    patterns = {"FL": [1, 0, 0, 0], "FR": [0, 1, 0, 0], "RL": [0, 0, 1, 0], "RR": [0, 0, 0, 1],
                "front pair FL+FR": [1, 1, 0, 0], "left pair FL+RL": [1, 0, 1, 0],
                "pitch round -,-,+,+": [-1, -1, 1, 1], "roll round +,-,+,-": [1, -1, 1, -1],
                "twist round +n": list(np.sign(n))}
    for de_mm in (0.4, 0.62, 0.85):
        for pname, pat in patterns.items():
            pat = np.array(pat, float)
            moving = pat != 0
            k = np.where(moving, kk["move"], kk["lock"])
            K = np.diag(k)
            de = pat * de_mm * 1e-3
            q = np.linalg.solve(A.T @ K @ A, A.T @ K @ de)
            dF = K @ (de - A @ q)
            shots[f"{pname} {de_mm} mm"] = {
                "heave_mm": round(q[0] * 1e3, 4), "roll_deg": round(math.degrees(q[1]), 5),
                "pitch_deg": round(math.degrees(q[2]), 5),
                "dD_kN": round(float(n @ dF) / 1e3, 2),
                "dF_kN": (dF / 1e3).round(2).tolist()}
    out["shots"] = shots
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("k_ext MN/m (FL, FR, RL, RR):")
    for kname, v in rows.items():
        print(f"  {kname:45s} {v}")
    print("k_h head column MN/m:", out["k_h_head_column_MN_m"], " k_st:", out["k_st_MN_m"])
    print("misuse: k_tw all moving", out["misuse"])
    print("r=1 hand vs harness need mm:", check)
    print("need FL (deliv 2.098 mm):")
    for r in need_rows:
        print(f"  {r['case']:44s} band {r['band_kN']:3.0f} k_ext {r['k_ext']:14s} "
              f"{r['k_ext_MN_m']:7.3f}  need {r['need_mm']:.3f} head {r['head_mm']:.3f} "
              f"yield {r['yield_mm']:.3f} dF {r['dF_leg_kN']:6.2f} ratio {r['delivered_over_need']:.3f}")
    print("shots:")
    for k2, v in shots.items():
        print(f"  {k2:32s} heave {v['heave_mm']:8.4f} roll {v['roll_deg']:9.5f} pitch "
              f"{v['pitch_deg']:9.5f} dD {v['dD_kN']:7.2f} dF {v['dF_kN']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
