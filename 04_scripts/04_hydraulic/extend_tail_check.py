"""R-H4' (U62): extension tail before a long lock. Does POC-B open and does the rod side vent
(about 35 bar after a grounded retraction -> extension back pressure) within the tail?

Lumped quasi-static model per leg (gauge pressures, SI):
  pump / compensated meter-in  : Q_PA = A_p * v_cmd(t)  (flow source into line A)
  line A (hose + passages)      : C_A dp_A/dt = Q_PA - Q_Ah
  POC-A (free flow A -> head)   : Q_Ah = K_A sqrt(p_A - p_h - p_crA) if positive
  head chamber                  : C_h dp_h/dt = Q_Ah - A_p xdot
  rod chamber                   : C_r dp_r/dt = A_ann xdot - Q_rT
  POC-B (pilot from line A)     : open if psi * p_A >= p_r - p_T + p_crB
  B -> T path (prop. notch)     : Q_rT = K_BT(t) sqrt(p_r - p_T), K_BT = A_ann |v_cmd| / sqrt(p_bB)
                                  (steady extension at v_cmd gives p_r = p_bB)
  support                       : p_h A_p - p_r A_ann = F_lock + k_ext (x - x0)   (no friction, no inertia)
Valve closes at the end of the tail command (both neutral variants stop the B venting).
Run: conda run -n hydraulics-dev python -I extend_tail_check.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

BAR = 1e5
BETA = 1.0e9
LEGS = {
    "front": {"A_p": math.pi / 4 * 0.130**2, "A_ann": math.pi / 4 * (0.130**2 - 0.110**2), "L_h": 0.4511,
              "L_r": 0.3489, "F_lock": 118.25e3},
    "rear": {"A_p": math.pi / 4 * 0.110**2, "A_ann": math.pi / 4 * (0.110**2 - 0.090**2), "L_h": 0.4409,
             "L_r": 0.3591, "F_lock": 72.8e3},
}
V_MAX = 22.026e-3
T_RAMP = 0.1  # actuator.command_ramp_s
TAIL = 0.3e-3
V_LINE_A = math.pi / 4 * 9.5e-3**2 * 4.0 + 0.05e-3  # ASSUMPTION 3/8" x 4 m hose + 50 cm3 passages
BETA_HOSE = 0.5e9  # ASSUMPTION effective (hose wall)
PSI, P_CRA, P_CRB, P_BB, P_T = 3.5, 3 * BAR, 3 * BAR, 5 * BAR, 0.0
K_EXT = 4.77e6  # ASSUMPTION incremental support stiffness (probe S_ii)
P_A0 = 2 * BAR  # line A after retraction (A -> T)


def p_r_threshold(c):
    phi = c["A_p"] / c["A_ann"]
    p_h = (c["F_lock"] / c["A_ann"] + P_CRA + 5 * BAR * (1 - 1 / PSI)) / (phi - 1 / PSI)
    return (p_h * c["A_p"] - c["F_lock"]) / c["A_ann"]


def profile(v, tail=TAIL):
    """Ramp 0.1 s up, constant, ramp down; distance TAIL. Returns (T_cmd, v_peak, fn)."""
    a = v / T_RAMP
    if tail >= v * T_RAMP:  # trapezoid
        t_c = (tail - v * T_RAMP) / v
        T = 2 * T_RAMP + t_c
        vp = v

        def fn(t):
            if t < 0 or t > T:
                return 0.0
            if t < T_RAMP:
                return a * t
            if t < T_RAMP + t_c:
                return v
            return a * (T - t)
    else:  # triangle
        vp = math.sqrt(tail * a)
        T = 2 * vp / a

        def fn(t):
            if t < 0 or t > T:
                return 0.0
            return a * t if t < T / 2 else a * (T - t)
    return T, vp, fn


def run(args):
    leg, v_frac, k_ext_mult, beta, psi, tail, p_bb = args
    c = LEGS[leg]
    a_p, a_ann = c["A_p"], c["A_ann"]
    v = v_frac * V_MAX
    T, vp, vcmd = profile(v, tail)
    C_A = V_LINE_A / BETA_HOSE
    C_h = a_p * c["L_h"] / beta
    C_r = a_ann * c["L_r"] / beta
    k_ext = K_EXT * k_ext_mult
    K_A = a_p * V_MAX / math.sqrt(P_CRA)  # generous free-flow check
    p_r = p_r_threshold(c)
    p_h = (c["F_lock"] + p_r * a_ann) / a_p
    p_A = P_A0
    x = 0.0
    dt = 2e-6
    t = 0.0
    t_end = T + 0.2
    t_pocb = None
    t_pr8 = None
    t_pocA = None
    p_r_T = None
    rec = []
    p_r0 = p_r
    while t < t_end:
        vc = vcmd(t)
        q_pa = a_p * vc
        q_ah = K_A * math.sqrt(p_A - p_h - P_CRA) if p_A > p_h + P_CRA else 0.0
        if q_ah > 0 and t_pocA is None:
            t_pocA = t
        open_b = (psi * p_A >= p_r - P_T + P_CRB) and vc > 0
        if open_b and t_pocb is None:
            t_pocb = t
        k_bt = a_ann * vc / math.sqrt(p_bb)
        q_rt = k_bt * math.sqrt(max(p_r - P_T, 0.0)) if open_b else 0.0
        # solve C_h dph = q_ah - A_p xd ; C_r dpr = A_ann xd - q_rt ; k xd = A_p dph - A_ann dpr
        M = np.array([[C_h, 0, a_p], [0, C_r, -a_ann], [-a_p, a_ann, k_ext]])
        rhs = np.array([q_ah, -q_rt, 0.0])
        dph, dpr, xd = np.linalg.solve(M, rhs)
        dpa = (q_pa - q_ah) / C_A
        p_A += dt * dpa
        p_h += dt * dph
        p_r += dt * dpr
        x += dt * xd
        if t_pr8 is None and p_r <= 8 * BAR:
            t_pr8 = t
        if p_r_T is None and t >= T:
            p_r_T = p_r
        t += dt
        if int(round(t / dt)) % 500 == 0:
            rec.append((t, p_A / BAR, p_h / BAR, p_r / BAR, x * 1e3))
    return {"leg": leg, "v_frac": v_frac, "k_ext_mult": k_ext_mult, "beta": beta, "psi": psi,
            "tail_mm": tail * 1e3, "p_bB_bar": p_bb / BAR,
            "T_cmd_s": T, "v_peak_mm_s": vp * 1e3, "p_r0_bar": p_r0 / BAR,
            "t_pocB_open_s": t_pocb, "t_pocA_open_s": t_pocA, "t_pr_le_8bar_s": t_pr8,
            "p_r_at_cmd_end_bar": (p_r_T if p_r_T is not None else p_r) / BAR, "p_r_final_bar": p_r / BAR,
            "piston_out_final_mm": x * 1e3, "dF_pad_kN": k_ext * x / 1e3, "p_h_final_bar": p_h / BAR,
            "pass_pr_le_8_before_close": t_pr8 is not None and t_pr8 <= T,
            "trace": rec[::4]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "06_analysis" / "03_hydraulic")
    args = ap.parse_args()
    jobs = [(leg, vf, 1.0, BETA, PSI, TAIL, P_BB) for leg in LEGS for vf in (0.05, 0.1, 0.25, 0.5, 1.0)]
    jobs += [(leg, 0.1, km, BETA, PSI, TAIL, P_BB) for leg in LEGS for km in (0.5, 2.0)]
    jobs += [(leg, 0.1, 1.0, 0.69e9, PSI, TAIL, P_BB) for leg in LEGS]
    jobs += [(leg, 0.1, 1.0, BETA, p, TAIL, P_BB) for leg in LEGS for p in (3.0, 6.0)]
    # tail-length sweep and B->T notch sensitivity (back pressure at the commanded flow)
    jobs += [(leg, 0.1, 1.0, BETA, PSI, d, P_BB) for leg in LEGS for d in (0.5e-3, 0.75e-3, 1.0e-3, 1.5e-3, 2.0e-3)]
    jobs += [(leg, 0.1, 1.0, BETA, PSI, d, pbb) for leg in LEGS for d in (0.3e-3, 1.0e-3) for pbb in (2 * BAR, 8 * BAR)]
    jobs += [(leg, 0.1, 1.0, 0.69e9, PSI, 1.0e-3, P_BB) for leg in LEGS]
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(run, jobs))
    # analytic: decompression volume and self-extension
    ana = {}
    for leg, c in LEGS.items():
        pr0 = p_r_threshold(c)
        V_r = c["A_ann"] * c["L_r"]
        k_h = BETA * c["A_p"] / c["L_h"]
        dF = (pr0 - P_BB) * c["A_ann"]
        ana[leg] = {"p_r0_bar": pr0 / BAR, "V_r_L": V_r * 1e3, "dV_decomp_cm3": V_r * (pr0 - P_BB) / BETA * 1e6,
                    "rod_force_release_kN": dF / 1e3, "self_extension_mm": dF / (k_h + K_EXT) * 1e3,
                    "pad_force_increase_kN": K_EXT * dF / (k_h + K_EXT) / 1e3,
                    "head_drop_bar": k_h * dF / (k_h + K_EXT) / c["A_p"] / BAR,
                    "pilot_needed_bar": (pr0 + P_CRB) / PSI / BAR}
    out = {"analytic": ana, "cases": res}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "extend_tail_check.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(ana, indent=1))
    for r in res:
        print(f"{r['leg']:5s} d {r['tail_mm']:.2f} pbB {r['p_bB_bar']:.0f} v {r['v_frac']:.2f}vmax"
              f" kext x{r['k_ext_mult']} beta {r['beta']:.2e} psi {r['psi']}"
              f" T {r['T_cmd_s']:.3f}s vpk {r['v_peak_mm_s']:.2f} | B open {r['t_pocB_open_s']} A open {r['t_pocA_open_s']}"
              f" pr<=8 {r['t_pr_le_8bar_s']} | p_r end {r['p_r_at_cmd_end_bar']:.1f} final {r['p_r_final_bar']:.1f}"
              f" x {r['piston_out_final_mm']:.3f} mm dF {r['dF_pad_kN']:.2f} kN p_h {r['p_h_final_bar']:.1f}"
              f" pass {r['pass_pr_le_8_before_close']}")


if __name__ == "__main__":
    main()
