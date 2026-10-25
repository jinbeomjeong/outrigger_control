"""Dead-volume effect of block-to-cylinder steel tubes seen in the site photo.

Formulas follow rod_side_pressure.md 12.2 / 14.2 (linear, beta constant):
  k_h = beta*A_p/(L0h+e), k_r = beta*A_ann/(s_max-e+L0r), r = k_r/(k_h+k_r)
  knee dF = A_ann/r * (p_r0_abs - p_floor_abs)
  lift-off p_r (after extend) ~ p_r0 + r*(F_cyl+m_rod*g)/A_ann
  tail decompression gain dp_r/dx = beta/L_r
Absolute pressures where named p_*_abs-like (p_r0, p_floor include p_atm); printed p_r lift is gauge.
Run: conda run -n hydraulics-dev python -I deadvol_photo_tubes.py   (prints only;
numbers of record: hydraulic_circuit.md 7.4 / 7.7)

Archived 2026-10-25 unchanged (except this docstring) from the 2026-10-22 session scratchpad
(hyd-run/photo3/deadvol.py).
"""
import math

import pint

u = pint.UnitRegistry()
beta = 1.0e9 * u.Pa
s_max = 0.700 * u.m
p_atm = 1.01325e5 * u.Pa
p_r0 = 2e5 * u.Pa + p_atm          # absolute
p_floor = 0.1e5 * u.Pa             # absolute
legs = {
    "front": dict(Ap=1.3273e-2, Aann=3.770e-3, e=0.4015, F=118.099e3, mg=1.047e3),
    "rear": dict(Ap=9.503e-3, Aann=3.142e-3, e=0.3915, F=72.097e3, mg=0.7175e3),
}


def tube_vol(d_mm, L_m):
    return math.pi / 4 * (d_mm * 1e-3) ** 2 * L_m


print("tube volumes [cm3] and equivalent lengths [mm]")
cases_rod = [(8, 0.08), (10, 0.15), (12, 0.23)]
cases_head = [(10, 0.6), (12, 0.75), (13, 0.9), (16, 0.9)]
for name, g in legs.items():
    for d, L in cases_rod:
        V = tube_vol(d, L)
        print(f"{name} rod  ID{d} L{L}: V={V*1e6:.1f} cm3 dL0r={V/g['Aann']*1e3:.2f} mm")
    for d, L in cases_head:
        V = tube_vol(d, L)
        print(f"{name} head ID{d} L{L}: V={V*1e6:.1f} cm3 dL0h={V/g['Ap']*1e3:.2f} mm")


def metrics(g, L0h, L0r):
    Ap = g["Ap"] * u.m**2
    Aa = g["Aann"] * u.m**2
    e = g["e"] * u.m
    Lh = L0h * u.m + e
    Lr = s_max - e + L0r * u.m
    kh = (beta * Ap / Lh).to("N/m")
    kr = (beta * Aa / Lr).to("N/m")
    r = (kr / (kh + kr)).to("").magnitude
    knee = (Aa / r * (p_r0 - p_floor)).to("kN")
    F = (g["F"] + g["mg"]) * u.N
    p_lift = ((p_r0 - p_atm) + r * F / Aa).to("bar")
    tail = (beta / Lr).to("bar/mm")
    return kh, kr, r, knee, p_lift, tail


print()
print("leg  L0h   L0r   k_h[1e7]  k_r[1e7]  r      knee[kN]  p_r lift[bar g]  dp_r/dx[bar/mm]")
for name, g in legs.items():
    for L0h, L0r in [(0.05, 0.05), (0.05, 0.051), (0.05, 0.058), (0.0535, 0.05),
                     (0.069, 0.058), (0.05, 0.02), (0.05, 0.10), (0.05, 0.2), (0.05, 0.6)]:
        kh, kr, r, knee, pl, tail = metrics(g, L0h, L0r)
        print(f"{name:5s} {L0h:.4f} {L0r:.3f} {kh.magnitude/1e7:8.4f} {kr.magnitude/1e7:8.4f} "
              f"{r:.4f} {knee.magnitude:8.3f} {pl.magnitude:10.2f} {tail.magnitude:10.2f}")

# volume needed for the sensitivity cases
print()
for name, g in legs.items():
    for L0r in (0.2, 0.6):
        print(f"{name} L0r={L0r} m -> V0r={g['Aann']*L0r*1e3:.3f} L")
