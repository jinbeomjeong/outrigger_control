"""Dead-volume increment of the new sensor block (between cylinder ports and the dual POC block).

Cases per side (head / rod): passage bore x length + G 1/4 sensor port + bleed port (ASSUMPTION).
Combined with the photo-based tube increments (hydraulic_circuit.md 7.4 upper bound).
Gauge pressures. Run: conda run -n hydraulics-dev python -I deadvol_sensor_block.py
(prints only; numbers of record: hydraulic_circuit.md 7.8)

Archived 2026-10-25 unchanged (except this docstring) from the 2026-10-22 session scratchpad
(hyd-run/sensor_block/deadvol_block.py).
"""
import math

BETA, S_MAX = 1.0e9, 0.70
LEGS = {"front": (0.130, 0.110, 0.4015, 118.10e3), "rear": (0.110, 0.090, 0.3915, 72.10e3)}
FLOOR = 0.1e5 - 1.01325e5
G14_PORT_CM3 = 1.5  # G 1/4 port (about 11.4 mm thread minor dia x 14 mm) + drill to the gallery
BLEED_CM3 = 0.5
CASES = {  # passage diameter [m], length [m], extra fitting / adapter volume [cm3]
    "low": (0.010, 0.060, 0.0),
    "nominal": (0.012, 0.100, 2.0),
    "high": (0.016, 0.150, 10.0),
    "high+tube": (0.016, 0.150, 10.0 + math.pi / 4 * 0.010**2 * 0.30 * 1e6),  # block not direct: +0.3 m x 10 mm tube
}
PHOTO_UP = {"front": (0.0090 + 0.0045, 0.0069), "rear": (0.0126 + 0.0064, 0.0083)}  # (head, rod) upper, 7.4


def block_volume_cm3(d, length, extra):
    return math.pi / 4 * d * d * length * 1e6 + G14_PORT_CM3 + BLEED_CM3 + extra


def metrics(leg, l0h, l0r):
    b, r_d, e, F = LEGS[leg]
    a_p = math.pi / 4 * b * b
    a_ann = math.pi / 4 * (b * b - r_d * r_d)
    k_h = BETA * a_p / (l0h + e)
    l_r = S_MAX - e + l0r
    k_r = BETA * a_ann / l_r
    r = k_r / (k_h + k_r)
    knee_ext = (2e5 - FLOOR) * a_ann / r
    lift_pr = 2e5 + r * (F + 1.0e3) / a_ann  # m g about 0.7-1.05 kN, 1 kN used
    tail_gain = BETA / l_r / 1e5 / 1e3  # bar per mm of rod-side volume change / A_ann
    return {"k_h": k_h, "k_r": k_r, "r": r, "knee_ext_kN": knee_ext / 1e3, "lift_pr_bar": lift_pr / 1e5,
            "tail_gain_bar_mm": tail_gain}


for leg in LEGS:
    b, r_d, e, F = LEGS[leg]
    a_p = math.pi / 4 * b * b
    a_ann = math.pi / 4 * (b * b - r_d * r_d)
    base = metrics(leg, 0.05, 0.05)
    print(leg, "base", {k: round(v, 5) for k, v in base.items()})
    for name, (d, length, extra) in CASES.items():
        v = block_volume_cm3(d, length, extra)
        dlh = v * 1e-6 / a_p
        dlr = v * 1e-6 / a_ann
        for with_photo in (False, True):
            ph, pr = PHOTO_UP[leg] if with_photo else (0.0, 0.0)
            l0h, l0r = 0.05 + dlh + ph, 0.05 + dlr + pr
            m = metrics(leg, l0h, l0r)
            rel = {k: (m[k] / base[k] - 1) * 100 for k in m}
            print(f"  {name:10s} photo={with_photo!s:5s} V/side {v:6.1f} cm3  dL0h {dlh*1e3:5.2f} mm dL0r {dlr*1e3:5.2f} mm"
                  f" -> L0h {l0h:.4f} L0r {l0r:.4f} | r {m['r']:.4f} ({rel['r']:+.1f}%) k_h {rel['k_h']:+.1f}%"
                  f" knee {m['knee_ext_kN']:.2f} kN ({rel['knee_ext_kN']:+.1f}%) lift p_r {m['lift_pr_bar']:.1f}"
                  f" ({rel['lift_pr_bar']:+.1f}%) tail gain {rel['tail_gain_bar_mm']:+.1f}%")
