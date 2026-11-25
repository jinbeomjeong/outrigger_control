"""Edition 7 hydraulics review hand calculations (Q7-H2 .. Q7-H5), no simulation.

Formulas are the harness P1 ones (``check_open_delay.retract_dead``, VN; the extend line law of
``CheckOpenDelay._extend_step``), written out here with the P1 supplements of the review:
  r      = k_h / (k_h + k_ext)                       head-yield share (k_ext = 0: harness)
  p_b    = (D - r (A_ann (delta + p_r) + F_band) / A_h) / (psi - r A_ann / A_h)  (band exceeded)
           D = p_h + p_cr - p_T, else p_b = D / psi
  p_rod  = max(p_b - delta, p_r)
  V(p_B) = s_L V_line (p_B - p_T)/beta_h + V_rod (p_B - delta - p_r)+ / beta
           + A_ann max(A_ann (p_B - delta - p_r) - F_band, 0) / (k_h + k_ext)
  need   = V(p_b) / A_ann
  V_rod  = A_ann (s_D L0r + s_max - s),  k_h = beta A_h / (s_D L0h + s)
The cross-check against the run-commit ``retract_dead`` (r = 1, s_L = s_D = s_v) is printed.

Units: SI inside (pint for the inputs), bar g / mm / mm/s in the output. Gauge pressures.
Run: hydraulics-dev python.exe -I -B h7r4_calcs.py <worktree> <out.txt>
"""
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pint

U = pint.UnitRegistry()
BAR = 1.0e5


def si(quantity, unit):
    return float(quantity.to(unit).magnitude)


# --- inputs (pint), ASSUMPTION values of the harness unless noted ----------------------------
LEG = {
    "front": {"A_h": si(math.pi / 4 * (130 * U.mm) ** 2, "m**2"),
              "A_ann": si(math.pi / 4 * ((130 * U.mm) ** 2 - (110 * U.mm) ** 2), "m**2"),
              "S_ii": 5.83e6, "k_dyn": 7.94e6, "k_mixed": 6.57e6, "k_b069": 5.78e6,
              "k_b16": 11.55e6},
    "rear": {"A_h": si(math.pi / 4 * (110 * U.mm) ** 2, "m**2"),
             "A_ann": si(math.pi / 4 * ((110 * U.mm) ** 2 - (90 * U.mm) ** 2), "m**2"),
             "S_ii": 6.98e6, "k_dyn": 10.87e6, "k_mixed": 8.79e6, "k_b069": 7.97e6,
             "k_b16": 15.62e6},
}
"""``k_dyn*``: leg-axis outer stiffness of the dynamics review (``dynamics_v7/
d7_dynamics_review.md`` Q7-D2: n_i^2 / (n_i^2 / k_st,i + sum_j n_j^2 / k_j), own head column
excluded, other legs locked; nominal, mixed, beta 0.69, beta 1.6)."""


def k_ext_dyn(plant, leg, kind="dyn"):
    """Dynamics k_ext matched to the corner's beta (nominal value for beta 1.0)."""
    if kind == "mixed":
        return leg["k_mixed"]
    if plant.beta <= 0.7e9:
        return leg["k_b069"]
    if plant.beta >= 1.5e9:
        return leg["k_b16"]
    return leg["k_dyn"]
S_MAX = si(0.70 * U.m, "m")
L0R = si(0.05 * U.m, "m")
L0H = si(0.05 * U.m, "m")
V_LINE = si(285 * U.cm ** 3, "m**3")
BETA_H = si(0.5 * U.GPa, "Pa")
P_T = si(2 * U.bar, "Pa")
V_MAX = si(20.924 * U.mm / U.s, "m/s")
U_HOLD = 0.01 * V_MAX
N_F = 0.05
DP_COMP = si(10 * U.bar, "Pa")
K_TWIST_B3 = 2.17e7


@dataclass(frozen=True)
class Plant:
    beta: float = 1.0e9
    s_line: float = 1.0
    s_dead: float = 1.0
    psi: float = 3.5
    p_cr: float = 3.0e5
    delta: float = 3.0e5
    k_ext: float = 0.0
    uniform: float | None = None
    """Old ``volume_scale`` (all volumes, stroke geometry included); None = split form."""


def k_head(plant, leg, s):
    if plant.uniform is not None:  # old volume_scale: the whole head column x scale
        return plant.beta * leg["A_h"] / (L0H + s) / plant.uniform
    return plant.beta * leg["A_h"] / (plant.s_dead * L0H + s)


def ratio_r(plant, leg, s):
    kh = k_head(plant, leg, s)
    return kh / (kh + plant.k_ext)


def p_open(plant, leg, p_h, p_r, band, s):
    r = ratio_r(plant, leg, s)
    drive = max(p_h, 0.0) + plant.p_cr - P_T
    p_free = max(drive / plant.psi, 0.0)
    if leg["A_ann"] * (p_free - plant.delta - p_r) > band:
        return (drive - r * (leg["A_ann"] * (plant.delta + p_r) + band) / leg["A_h"]) / (
            plant.psi - r * leg["A_ann"] / leg["A_h"])
    return p_free


def volume(plant, leg, p_b_line, p_r, band, s):
    """Retract fill volume (m^3) that brings the B line to ``p_b_line``."""
    if plant.uniform is not None:
        s_l = s_d_vol = plant.uniform
        v_rod = leg["A_ann"] * (L0R + S_MAX - s) * s_d_vol
        kh = k_head(plant, leg, s)
    else:
        s_l = plant.s_line
        v_rod = leg["A_ann"] * (plant.s_dead * L0R + S_MAX - s)
        kh = k_head(plant, leg, s)
    dp_rod = max(p_b_line - plant.delta - p_r, 0.0)
    line = s_l * V_LINE * max(p_b_line - P_T, 0.0) / BETA_H
    rod = v_rod * dp_rod / plant.beta
    head = leg["A_ann"] * max(leg["A_ann"] * dp_rod - band, 0.0) / (kh + plant.k_ext)
    return line + rod + head


def need_m(plant, leg, p_h, p_r, band, s):
    p_b = p_open(plant, leg, p_h, p_r, band, s)
    return volume(plant, leg, p_b, p_r, band, s) / leg["A_ann"], p_b


def fill_rise(plant, leg, x_m, p_h, p_r, band, s):
    """(opened, rod rise) after delivering ``x_m`` (A_ann stroke units) into the retract line:
    the rod chamber follows the line minus delta once the line passes p_r + delta (P1
    supplement (a)); capped at the opening."""
    n, p_b = need_m(plant, leg, p_h, p_r, band, s)
    if x_m >= n:
        return True, max(p_b - plant.delta, p_r) - p_r
    target = x_m * leg["A_ann"]
    lo, hi = P_T, p_b
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if volume(plant, leg, mid, p_r, band, s) < target:
            lo = mid
        else:
            hi = mid
    return False, max(lo - plant.delta - p_r, 0.0)


def p_star_ret(leg, force, psi=3.5, p_cr=3.0e5, p_ba=5.0e5):
    """Plant / monitor retract model ``p*_ret(F)`` (``retract_target_rod_pressure_Pa``)."""
    phi = leg["A_h"] / leg["A_ann"]
    thr = (force / leg["A_ann"] + p_cr + p_ba * (1 - 1 / psi)) / (phi - 1 / psi)
    head = max(p_ba, thr)
    return (head * leg["A_h"] - force) / leg["A_ann"]


def u_threshold(c_v, p_open_line, direction_ratio):
    """VN steady release threshold (P1 line law): fill = neutral drain at the opening."""
    s_term = N_F * direction_ratio * math.sqrt(max(p_open_line - P_T, 0.0) / DP_COMP)
    return s_term * V_MAX / (1 + s_term / c_v)


def main() -> None:
    worktree, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(worktree / "03_src"))
    from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead

    out = []
    w = out.append
    front, rear = LEG["front"], LEG["rear"]
    w("# units: bar gauge, mm, mm/s, kN unless noted")
    w(f"areas: front A_h {front['A_h'] * 1e4:.2f} cm2 A_ann {front['A_ann'] * 1e4:.2f} cm2; "
      f"rear A_h {rear['A_h'] * 1e4:.2f} A_ann {rear['A_ann'] * 1e4:.2f}")

    # ---- cross-check against the run-commit retract_dead ---------------------------------
    w("\n## X. hand need vs run-commit retract_dead (r = 1)")
    for scale in (0.5, 1.0, 1.5):
        for band in (0.0, 4e3):
            cfg = RetractConfig(rod_forward=True, volume_scale=scale, v_line_m3=V_LINE,
                                beta_hose_Pa=BETA_H, psi=3.5, p_crack_Pa=3e5)
            code = retract_dead(cfg, 99.39e5, 5.07e5, band, 0.40836, 0.0, front["A_h"],
                                front["A_ann"], S_MAX, L0R, L0H, 1.0e9, P_T)
            hand, _ = need_m(Plant(uniform=scale), front, 99.39e5, 5.07e5, band, 0.40836)
            w(f"  scale {scale} band {band / 1e3:.0f} kN: code {code['need'] * 1e3:.4f} mm, "
              f"hand {hand * 1e3:.4f} mm")

    # ---- H4 / P7-7: corners at the ed6 FL v15 state --------------------------------------
    corners = {
        "nominal": Plant(),
        "old v15 (uniform 1.5)": Plant(uniform=1.5),
        "beta 0.69": Plant(beta=0.69e9),
        "beta 1.6": Plant(beta=1.6e9),
        "line x1.5": Plant(s_line=1.5),
        "line x0.5": Plant(s_line=0.5),
        "dead x1.5": Plant(s_dead=1.5),
        "dead x0.5": Plant(s_dead=0.5),
        "slow (b0.69 L1.5 D1.5)": Plant(beta=0.69e9, s_line=1.5, s_dead=1.5),
        "fast (b1.6 L0.5 D0.5)": Plant(beta=1.6e9, s_line=0.5, s_dead=0.5),
    }
    w("\n## H4. FL state of ed6 v15 Fs0 (p_h 99.39, p_r 5.07, s 408.36 mm), delivered 2.098 mm")
    w("  corner | k_ext | need | ratio | opened | rod rise (trapped at VN) | p_b")
    for name, base in corners.items():
        options = (("0", 0.0), ("dyn", k_ext_dyn(base, front)),
                   ("mixed", k_ext_dyn(base, front, "mixed")), ("b3*", K_TWIST_B3))
        for k_name, k_ext in options:
            plant = replace(base, k_ext=k_ext)
            n, p_b = need_m(plant, front, 99.39e5, 5.07e5, 0.0, 0.40836)
            opened, rise = fill_rise(plant, front, 2.098e-3, 99.39e5, 5.07e5, 0.0, 0.40836)
            w(f"  {name:24s} | {k_name:4s} | {n * 1e3:5.3f} | {2.098e-3 / n:4.2f} | "
              f"{'Y' if opened else 'n'} | {rise / BAR:5.2f} | {p_b / BAR:5.2f}")

    # ---- H3: need over probe states and corners ------------------------------------------
    w("\n## H3. retract need [mm] over probe states (p_r 5 bar, F_band 0), worst corner")
    states_ph = (40e5, 60e5, 80e5, 100e5, 120e5, 140e5)
    strokes = (0.10, 0.25, 0.40, 0.55, 0.68)
    for leg_name, leg in LEG.items():
        for name in ("nominal", "slow (b0.69 L1.5 D1.5)"):
            for k_name, k_ext in (("0", 0.0), ("dyn", k_ext_dyn(corners[name], leg))):
                plant = replace(corners[name], k_ext=k_ext)
                row = []
                for s in strokes:
                    row.append(max(need_m(plant, leg, p_h, 5e5, 0.0, s)[0] for p_h in states_ph))
                w(f"  {leg_name:5s} {name:24s} k_ext {k_name:4s} max over p_h<=140 bar at s "
                  + " ".join(f"{s * 1e3:.0f}:{v * 1e3:.2f}" for s, v in zip(strokes, row)))
    w("  conservative tracker need_ub (LineFillGateParams: beta 0.69, L0r 0.10, L0h 0.08, "
      "p_r floor, F_band 0) for comparison:")
    for leg_name, leg in LEG.items():
        cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=V_LINE,
                            beta_hose_Pa=BETA_H, psi=3.5, p_crack_Pa=3e5)
        row = []
        for s in strokes:
            row.append(max(retract_dead(cfg, p_h + 9e5, 0.1e5 - 1.01325e5, 0.0, s, 0.0,
                                        leg["A_h"], leg["A_ann"], S_MAX, 0.10, 0.08, 0.69e9,
                                        P_T)["need"] for p_h in states_ph))
        w(f"  {leg_name:5s} need_ub max over p_h<=140 (+e_h 9) at s "
          + " ".join(f"{s * 1e3:.0f}:{v * 1e3:.2f}" for s, v in zip(strokes, row)))

    w("  head pressure above which a 2.098 mm probe retract does not open (p_r 5 bar, "
      "F_band 0, k_ext 0):")
    for leg_name, leg in LEG.items():
        for name in ("nominal", "slow (b0.69 L1.5 D1.5)"):
            row = []
            for s in (0.25, 0.40, 0.55):
                lo, hi = 5e5, 400e5
                if need_m(corners[name], leg, lo, 5e5, 0.0, s)[0] > 2.098e-3:
                    row.append(f"{s * 1e3:.0f}: all")
                    continue
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    if need_m(corners[name], leg, mid, 5e5, 0.0, s)[0] < 2.098e-3:
                        lo = mid
                    else:
                        hi = mid
                row.append(f"{s * 1e3:.0f}: {lo / BAR:.1f} bar")
            w(f"    {leg_name:5s} {name:24s} " + ", ".join(row))

    # ---- (a) coverage: trapped rod pressure vs the monitor retract candidate -------------
    w("\n## H1/H4(a). trapped fill pressure p_rod,open vs R5-2 candidate p*_ret(F) (psi 3.5)")
    w("  leg p_h | p_rod,open(F_band 0, r 1) | p*_ret(F) | margin")
    worst = math.inf
    for leg_name, leg in LEG.items():
        for p_h in (20e5, 40e5, 60e5, 80e5, 100e5, 140e5, 200e5):
            p_r = 5e5
            force = p_h * leg["A_h"] - p_r * leg["A_ann"]
            p_b = p_open(Plant(), leg, p_h, p_r, 0.0, 0.40)
            p_rod = max(p_b - 3e5, p_r)
            cand = p_star_ret(leg, force)
            worst = min(worst, cand - p_rod)
            w(f"  {leg_name:5s} {p_h / BAR:5.0f} | {p_rod / BAR:6.2f} | {cand / BAR:6.2f} | "
              f"{(cand - p_rod) / BAR:6.2f}")
    w(f"  smallest margin {worst / BAR:.2f} bar")

    # ---- H2: D6 requirement ---------------------------------------------------------------
    w("\n## H2. D6: lower-bound rise and requirement (p_r,ext 5 bar read)")
    w("  dp_lb = p_b,lb - delta_ub - (p_r,ext + e_r); p_b,lb: psi_ub, p_cr,lb 1 bar, "
      "p_h - e_h (4 bar), F_band_ub (16 / 13.3 kN)")
    w("  leg p_h | old p_h/12 | dp_lb(psi 6, d 3) | dp_lb(psi 6, d 5) | req 0.5 dp_lb | "
      "physical rise psi 3.5 (band 0 / F_s 8k) | psi 4.5 | psi 6")
    bands = {"front": 16e3, "rear": 13.328e3}
    for leg_name, leg in LEG.items():
        for p_h in (40e5, 60e5, 80e5, 100e5, 120e5, 140e5):
            lb_plant = Plant(psi=6.0, p_cr=1e5, delta=3e5)
            pb_lb = p_open(lb_plant, leg, p_h - 4e5, 5e5 + 4e5, bands[leg_name], 0.40)
            dp_lb3 = pb_lb - 3e5 - (5e5 + 4e5)
            dp_lb5 = pb_lb - 5e5 - (5e5 + 4e5)
            phys = []
            for psi, band in ((3.5, 0.0), (3.5, 8e3 if leg_name == "front" else 6.66e3),
                              (4.5, 0.0), (6.0, 0.0)):
                pl = Plant(psi=psi)
                p_b = p_open(pl, leg, p_h, 5e5, band, 0.40)
                phys.append(max(p_b - 3e5, 5e5) - 5e5)
            w(f"  {leg_name:5s} {p_h / BAR:4.0f} | {max(3, p_h / BAR / 12):5.2f} | "
              f"{dp_lb3 / BAR:6.2f} | {dp_lb5 / BAR:6.2f} | {0.5 * dp_lb3 / BAR:5.2f} | "
              f"{phys[0] / BAR:5.2f} / {phys[1] / BAR:5.2f} | {phys[2] / BAR:5.2f} | "
              f"{phys[3] / BAR:5.2f}")

    # ---- H5: P1 dead zone and E3 still witness ----------------------------------------------
    w("\n## H5. P1 VN steady release threshold u_thr [mm/s] (u_hold = "
      f"{U_HOLD * 1e3:.4f} mm/s)")
    for c_v in (0.005, 0.0115, 0.02, 0.04):
        row = []
        for p_h in (20e5, 60e5, 100e5, 140e5):
            ext = u_threshold(c_v, p_h + 3e5, 1.0)
            pb = p_open(Plant(), front, p_h, 5e5, 0.0, 0.40)
            ret = u_threshold(c_v, pb, front["A_h"] / front["A_ann"])
            row.append(f"p_h {p_h / BAR:.0f}: ext {ext * 1e3:.3f} ret {ret * 1e3:.3f}")
        w(f"  c_v {c_v}: c_v v_max {c_v * V_MAX * 1e3:.3f}; " + "; ".join(row))
    w("  extension line fill to p_h + p_cr at u_hold with no drain (c_v v_max < u_hold):")
    for p_h in (20e5, 60e5, 100e5, 140e5):
        x = (p_h + 3e5 - P_T) * V_LINE / (front["A_h"] * BETA_H)
        w(f"    front p_h {p_h / BAR:.0f}: x {x * 1e3:.3f} mm, time at u_hold {x / U_HOLD:.2f} s")
    sigma = 0.1e-3
    sd_e3 = sigma * math.sqrt(2.0 / 3.0)
    w(f"  E3 (3-read means) difference sigma for read sigma 0.1 mm: {sd_e3 * 1e3:.4f} mm")
    for s_still in (0.1e-3, 0.15e-3):
        p_still_fail = 0.5 * math.erfc((s_still / sd_e3) / math.sqrt(2))
        w(f"   s_still {s_still * 1e3:.2f} mm: truly still stretch fails the test "
          f"{p_still_fail:.3f} per evaluation")
        for speed in (0.10e-3, 0.15e-3, U_HOLD):
            travel = speed * 1.7
            p_false = 0.5 * math.erfc(((travel - s_still) / sd_e3) / math.sqrt(2))
            w(f"     leg moving at {speed * 1e3:.3f} mm/s (E3 span 1.7 s, {travel * 1e3:.3f} mm): "
              f"called still {p_false:.4f}")
    w("  piston coordinate: head column motion (L0h + s) dp_h / beta = "
      f"{(0.05 + 0.40) / 1e9 * 1e5 * 1e3:.4f} mm per bar (front, s 0.40 m, beta 1 GPa)")
    w("  single-read witness (D6): read-difference sigma "
      f"{sigma * math.sqrt(2) * 1e3:.4f} mm; P(any of n reads > T) ~ n Q(T / sigma_d)")
    for t_w in (0.3e-3, 0.5e-3, 0.6e-3, 1.0e-3):
        q = 0.5 * math.erfc((t_w / (sigma * math.sqrt(2))) / math.sqrt(2))
        w(f"   T {t_w * 1e3:.1f} mm: Q {q:.2e}, n = 12 reads ~ {min(12 * q, 1.0):.3f}")

    out_path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
