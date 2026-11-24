"""Hand calculation (no simulation): retract dead stroke of a locked front leg against the 2 mm
probe retraction, over physically separate sensitivity corners, and the D6 rise of an opened
retraction against max(3 bar, p_h / 12).

Formula: check_open_delay.retract_dead (P1 gate, VN circuit), generalised by one factor
r = k_h / (k_h + k_ext) on the piston yield (head compression): k_h = beta A_h^2 / V_h is the
head column stiffness, k_ext the stiffness that restrains the leg from shortening. The harness
formula is r = 1 (k_ext = 0: the leg load stays constant while the piston yields). k_ext =
21.7 MN/m is the twist stiffness per leg of the harness (LockStartBSettings.b3_twist_stiffness,
dynamics review; ASSUMPTION for this use).

All pressures gauge [Pa]; output in bar and mm (stroke units of the annulus).
Inputs: FL state at the probe retract start of R12 top-*-Fs0 (p_h 99.39 bar, p_r 5.07 bar,
s 408.36 mm), delivered retract oil 2.098 mm (h2_retract_need.txt)."""
from dataclasses import dataclass, replace

A_H, A_ANN = 0.013273229, 0.00376991118  # front leg [m2]
S_MAX = 0.7
BAR = 1e5
DELIVERED_MM = 2.098


@dataclass(frozen=True)
class Case:
    name: str
    beta: float = 1.0e9          # cylinder oil (YAML 1.0 GPa, sensitivity 0.69-1.6)
    l0r: float = 0.05            # rod dead length (YAML 0.05, sensitivity 0.02-0.1)
    l0h: float = 0.05            # head dead length (YAML 0.05, sensitivity 0.05-0.08)
    v_line: float = 285e-6       # B hose (params V_hose 2.85e-4, range 1.4e-4 .. 5.7e-4)
    beta_hose: float = 0.5e9     # ASSUMPTION (check_open_delay CheckValveValues)
    psi: float = 3.5             # pilot ratio ASSUMPTION (V-6)
    p_cr: float = 3e5            # check cracking ASSUMPTION
    p_t: float = 2e5             # tank back pressure (params p_tank 2 bar)
    scale: float = 1.0           # harness volume_scale on every term
    k_ext: float = 0.0           # leg restraint against shortening [N/m]


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
    dp_h = k_h * yield_m / A_H
    v_rod = A_ANN * (case.l0r + S_MAX - s)
    line = case.scale * case.v_line * max(p_b - case.p_t, 0.0) / case.beta_hose
    rod = case.scale * v_rod * (p_rod - p_r) / case.beta
    head = case.scale * A_ANN * yield_m
    need = (line + rod + head) / A_ANN
    return {"need_mm": need * 1e3, "line_mm": line / A_ANN * 1e3, "rod_mm": rod / A_ANN * 1e3,
            "head_mm": head / A_ANN * 1e3, "p_b": p_b / BAR, "p_rod": p_rod / BAR,
            "dp_h": dp_h / BAR, "r": r}


def corners() -> None:
    nominal = Case("nominal")
    cases = [
        nominal,
        replace(nominal, name="harness volume_scale 1.5", scale=1.5),
        replace(nominal, name="harness volume_scale 0.5", scale=0.5),
        replace(nominal, name="beta_eff 0.69 GPa", beta=0.69e9),
        replace(nominal, name="B hose x2 (570 cm3)", v_line=570e-6),
        replace(nominal, name="L0r 0.10, L0h 0.08", l0r=0.10, l0h=0.08),
        replace(nominal, name="B hose x1.5 + L0r 0.075 + L0h 0.075 (dead volumes x1.5)",
                v_line=427.5e-6, l0r=0.075, l0h=0.075),
        replace(nominal, name="beta 0.69 + hose x1.5", beta=0.69e9, v_line=427.5e-6),
        replace(nominal, name="beta 0.69 + hose x2", beta=0.69e9, v_line=570e-6),
        replace(nominal, name="beta 0.69 + hose x2 + L0r 0.1 + L0h 0.08", beta=0.69e9,
                v_line=570e-6, l0r=0.10, l0h=0.08),
        replace(nominal, name="pilot ratio 6 (robust set of A(ii))", psi=6.0),
        replace(nominal, name="pilot ratio 6 + volume_scale 1.5", psi=6.0, scale=1.5),
    ]
    p_h, p_r, s = 99.39 * BAR, 5.07 * BAR, 0.40836
    print(f"FL retract dead stroke (need) vs delivered {DELIVERED_MM} mm (probe depth 2 mm)")
    print(f"{'case':58s} {'band':>5s} {'k_ext':>6s} {'need':>6s} {'line':>6s} {'rod':>6s}"
          f" {'head':>6s} {'p_b':>6s} {'p_rod':>6s} {'dp_h':>5s} {'deliv/need':>10s}")
    for case in cases:
        for band in (0.0, 4e3):
            for k_ext in (0.0, 21.7e6):
                out = retract(replace(case, k_ext=k_ext), p_h, p_r, band, s)
                print(f"{case.name:58s} {band / 1e3:5.1f} {k_ext / 1e6:6.1f} {out['need_mm']:6.3f}"
                      f" {out['line_mm']:6.3f} {out['rod_mm']:6.3f} {out['head_mm']:6.3f}"
                      f" {out['p_b']:6.2f} {out['p_rod']:6.2f} {out['dp_h']:5.2f}"
                      f" {DELIVERED_MM / out['need_mm']:10.3f}")
    print()
    print("critical harness volume_scale s* = delivered / need(scale 1), k_ext 0:")
    for band in (0.0, 4e3, 8e3):
        need1 = retract(nominal, p_h, p_r, band, s)["need_mm"]
        print(f"  band {band / 1e3:4.1f} kN: need(1) {need1:.3f} mm, s* {DELIVERED_MM / need1:.3f}")


def d6_rise() -> None:
    """Rise p_rod - p_r of an OPENED retraction (volume independent) against max(3, p_h/12)."""
    print()
    print("D6 on an opened retraction: rise = p_rod - p_r (p_r 5 bar), required max(3, p_h/12)")
    print(f"{'psi':>4s} {'band kN':>7s} {'p_h':>5s} {'rise':>6s} {'req':>5s} {'rise/req':>8s}")
    for psi in (3.5, 4.5, 6.0):
        for band in (0.0, 8e3):
            for p_h_bar in (40, 60, 80, 100, 120):
                case = Case("d6", psi=psi)
                out = retract(case, p_h_bar * BAR, 5 * BAR, band, 0.40836)
                rise = out["p_rod"] - 5.0
                req = max(3.0, (p_h_bar + out["dp_h"]) / 12.0)
                print(f"{psi:4.1f} {band / 1e3:7.1f} {p_h_bar:5d} {rise:6.2f} {req:5.2f}"
                      f" {rise / req:8.2f}")
    print("p_h at which rise = p_h/12 (band large, dp_h 0): p_h* = (p_r + p_cr - (p_cr - p_t)/psi)"
          " / (1/psi - 1/12); D6 passes an opened retraction only above p_h*")
    for psi in (3.5, 4.0, 4.5, 5.0, 6.0):
        p_star = (5.0 + 3.0 - (3.0 - 2.0) / psi) / (1.0 / psi - 1.0 / 12.0)
        print(f"  psi {psi:3.1f}: p_h* = {p_star:6.1f} bar")


if __name__ == "__main__":
    corners()
    d6_rise()
