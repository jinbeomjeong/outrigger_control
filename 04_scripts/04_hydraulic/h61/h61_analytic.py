"""H-61-1 analytic part (real hardware): local beta ratio, dead-volume margins, online R_hat factor.

Locked leg, both chambers sealed (dual PO check on the cylinder). Over a window the pressures move
with the same piston displacement x relative to the barrel:
    dp_h = -A_p x / C_h,  dp_r = A_ann x / C_r,  C_i = V_i / beta_i,tan(p_i)
    R_win = -dp_r/dp_h = (A_ann C_h)/(A_p C_r) = kappa_loc * (L0h + s)/(L0r + s_max - s)
    kappa_loc = beta_r,tan(p_r) / beta_h,tan(p_h)   (friction and inertia cancel: kinematic)
beta model (same as s8 doc 10.2 table 2): K = 1.0 GPa + K1 (p - 100 bar) (K1 = 10), free air x
(1 bar abs reference, polytropic n = 1.4) in series. Gauge pressures [Pa]; air term uses abs.
Usage: python -I h61_analytic.py <out.json>
"""
from __future__ import annotations

import json
import sys

import numpy as np

BAR = 1e5
PATM = 1.01325e5
S_MAX = 0.7
SIDES = {"front": (0.013273229, 0.00376991118), "rear": (0.00950331778, 0.00314159265)}


def beta_tan(p_g, k1=10.0, x_air=0.0, k0=1.0e9):
    p_abs = np.maximum(p_g + PATM, 1.0e3)
    oil = k0 + k1 * (p_g - 100 * BAR)
    air = x_air * (PATM / p_abs) ** (1 / 1.4) / (1.4 * p_abs)
    return 1.0 / (1.0 / oil + air)


def r_col(s, l0h, l0r):
    return (l0h + s) / (l0r + S_MAX - s)


def r_hi(s):
    sp = np.minimum(s + 0.005, S_MAX - 1e-3)
    return r_col(sp, 0.08, 0.02)


def kappa_table():
    """kappa_loc over rod pressure, head = rod/phi + F/A_p for F >= F_lo, air only in head."""
    out = {}
    for side, (a_p, a_r) in SIDES.items():
        phi = a_p / a_r
        rows = []
        for pr in (0, 10, 20, 50, 100, 150, 200, 250, 300, 350):
            ph_min = pr * BAR / phi  # F = 0 (leg unloaded): lowest head for this rod pressure
            row = {"p_r_bar_g": pr, "p_h_min_bar_g (F=0)": round(ph_min / BAR, 1)}
            for lab, k1, xh, xr in (("K1=10, no air", 10.0, 0.0, 0.0),
                                    ("K1=10, head air 0.2%", 10.0, 0.002, 0.0),
                                    ("K1=10, head air 1%", 10.0, 0.01, 0.0),
                                    ("K1=0, head air 0.2%", 0.0, 0.002, 0.0)):
                kap = beta_tan(pr * BAR, k1, xr) / beta_tan(ph_min, k1, xh)
                row[lab] = round(float(kap), 4)
            rows.append(row)
        out[side] = rows
    return out


def kappa_grid():
    """max kappa_loc for head-pressure floor and rod-pressure cap (K1 10, head air <= 0.2 %)."""
    out = {}
    for side, (a_p, a_r) in SIDES.items():
        phi = a_p / a_r
        tab = {}
        for pr_cap in (50, 100, 150, 200, 250, 350):
            for ph_floor in (5, 10, 20, 30, 50):
                pr = np.linspace(0, pr_cap, 141) * BAR
                worst = 0.0
                for p in pr:
                    ph = max(p / phi, ph_floor * BAR)
                    worst = max(worst, float(beta_tan(p, 10.0, 0.0) / beta_tan(ph, 10.0, 0.002)))
                tab[f"p_r<= {pr_cap} bar, p_h>= {ph_floor} bar"] = round(worst, 4)
        out[side] = tab
    return out


def margin_table():
    """M(s) = R_hi(s) / R_col(s; true L0): the dead-volume margin that can absorb kappa_loc."""
    sets = {"0.05/0.05 nominal": (0.05, 0.05), "est. worst 0.076/0.052": (0.076, 0.052),
            "est. mid 0.063/0.065": (0.063, 0.065), "corner 0.08/0.02": (0.08, 0.02),
            "head hose open 0.124/0.05 (front)": (0.124, 0.05),
            "head hose open 0.141/0.05 (rear)": (0.141, 0.05)}
    rows = []
    for s in (0.30, 0.325, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.659, 0.68, 0.6948):
        row = {"s_m": s, "R_hi": round(float(r_hi(s)), 4)}
        for lab, (h, r) in sets.items():
            row[lab] = round(float(r_hi(s) / r_col(s, h, r)), 4)
        rows.append(row)
    return rows


def nominal_band():
    """Q2: R_nom(0.05/0.05) against the block/tube estimate band (cylinder base 0.05 assumed)."""
    rows = []
    for s in (0.35, 0.40, 0.50, 0.60, 0.65, 0.659):
        lo = r_col(s, 0.0505, 0.079)
        hi = r_col(s, 0.076, 0.052)
        mid = r_col(s, 0.063, 0.065)
        rows.append({"s_m": s, "R_nom 0.05/0.05": round(r_col(s, 0.05, 0.05), 3),
                     "band low (0.0505/0.079)": round(lo, 3), "band high (0.076/0.052)": round(hi, 3),
                     "mid (0.063/0.065)": round(mid, 3),
                     "R_nom/mid": round(r_col(s, 0.05, 0.05) / mid, 3),
                     "head hose open front (0.094/0.05)": round(r_col(s, 0.094, 0.05), 3),
                     "head hose open rear (0.111/0.05)": round(r_col(s, 0.111, 0.05), 3)})
    return rows


def leakage():
    """Cross-piston leak head -> rod: secant factor 1 + (phi - 1) eps, eps = dh_leak / dh."""
    out = []
    for side, (a_p, a_r) in SIDES.items():
        phi = a_p / a_r
        for beta in (0.69e9, 1.0e9, 1.6e9):
            for s in (0.35, 0.66):
                c_h = a_p * (0.05 + s) / beta
                q_1pct = 0.01 * 5 * BAR * c_h / 0.3  # eps 1 % at dh 5 bar over 0.3 s
                out.append({"side": side, "phi": round(phi, 3), "beta_GPa": beta / 1e9, "s": s,
                            "factor at eps 1%": round(1 + (phi - 1) * 0.01, 4),
                            "leak for eps 1% @ dh 5 bar [cm3/min]": round(q_1pct * 6e7, 2)})
    return out


def stroke_transfer():
    """Worst R_col(s + d)/R_col(s) over L0h 0.05..0.08, L0r 0.02..0.10 for d = 5 mm."""
    rows = []
    for s in (0.35, 0.40, 0.50, 0.60, 0.65, 0.66, 0.68):
        worst = 0.0
        for h in (0.05, 0.08):
            for r in (0.02, 0.05, 0.10):
                worst = max(worst, r_col(s + 0.005, h, r) / r_col(s, h, r))
        rows.append({"s_m": s, "k_stroke(5 mm)": round(worst, 4)})
    return rows


def sensor_factor():
    """Online R_hat = -dr_read/dh_read.  k_sens = max R_true/R_hat over reading errors.
    Random per-reading bound e (bar), gain error g per sensor (after zero calibration)."""
    out = []
    for lab, e, g in (("spec worst (nonrep 0.4 + noise 0.8; gain 4.5 %)", 1.2, 0.045),
                      ("spec, gain only 2.5 % (no temp. span drift)", 1.2, 0.025),
                      ("measured 4 sigma (0.2 bar) + nonrep 0.4; gain 4.5 %", 1.2 * 0 + 0.8 + 0.4, 0.045),
                      ("regression N>=20 samples (e/sqrt(N/2)); gain 4.5 %", 1.2 / np.sqrt(10), 0.045)):
            for dh in (5, 10, 20, 30):
                for rr in (1.0, 2.0, 7.8):
                    dr = rr * dh
                    if dh - 2 * e <= 0:
                        k = float("inf")
                    else:
                        k = ((dr + 2 * e) / dr) * (dh / (dh - 2 * e)) * ((1 + g) / (1 - g))
                    out.append({"case": lab, "dh_read_bar": dh, "R": rr, "k_sens": round(k, 3)})
    return out


def main():
    res = {"kappa_loc_F0": kappa_table(), "kappa_max_grid": kappa_grid(),
           "margin_R_hi_over_true": margin_table(), "q2_nominal_band": nominal_band(),
           "leakage": leakage(), "stroke_transfer": stroke_transfer(),
           "sensor_factor": sensor_factor()}
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for k, v in res.items():
        print("==", k)
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(kk)
                for row in (vv if isinstance(vv, list) else [vv]):
                    print("  ", row)
        else:
            for row in v:
                print("  ", row)


if __name__ == "__main__":
    main()
