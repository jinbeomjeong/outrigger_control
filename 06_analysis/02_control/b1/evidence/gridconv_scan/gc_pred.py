"""Independent re-check of the grid-convergence predictions (Bekker discrete-grid factor f).

z_cont = (F / (A (kc/b_poly + kphi)))**(1/n)
f      = [N d^2 (kc/b_hull + kphi) / (A (kc/b_poly + kphi))]**(-1/n),  z_grid = f z_cont
Inputs: J2 set (02_params/scm_soil_sets.json via P1 dump), offset-0 node census from terra phase_band.txt.
"""
import json
import sys
from pathlib import Path

KC, KPHI, N_EXP = 16430.0, 1724690.0, 0.2
PADS = {  # A_poly [m2], b_poly [m], offset-0 (N_h, b_hull) per grid
    "RL": (0.0607, 0.1306, {0.02: (157, 0.1256), 0.01: (601, 0.1255), 0.005: (2421, 0.1310)}, (72850.0, 74850.0)),
    "FL": (0.1071, 0.1714, {0.02: (261, 0.1616), 0.01: (1073, 0.1714), 0.005: (4285, 0.1716)}, (119590.0, 122010.0)),
}
out = {}
for leg, (a, bp, census, (f1, f2)) in PADS.items():
    kp = KC / bp + KPHI
    zc = [(f / (a * kp)) ** (1.0 / N_EXP) for f in (f1, f2)]
    row = {"z_cont_mm": [1e3 * z for z in zc], "dz_cont_mm": 1e3 * (zc[1] - zc[0])}
    for d, (nh, bh) in census.items():
        fac = (nh * d * d * (KC / bh + KPHI) / (a * kp)) ** (-1.0 / N_EXP)
        row[str(d)] = {"f": fac, "z1_mm": 1e3 * fac * zc[0], "z2_mm": 1e3 * fac * zc[1],
                       "dz_mm": 1e3 * fac * (zc[1] - zc[0]), "dz_over_z2": (zc[1] - zc[0]) / zc[1],
                       "one_node_dz_over_z": d * d / (N_EXP * a)}
    r1, r5 = row["0.01"], row["0.005"]
    row["raw_z2_diff_mm_0.01_minus_0.005"] = r1["z2_mm"] - r5["z2_mm"]
    row["raw_dz_diff_mm"] = r1["dz_mm"] - r5["dz_mm"]
    row["corr_z2_diff_mm"] = r1["z2_mm"] / r1["f"] - r5["z2_mm"] / r5["f"]
    row["load_factor_step1"] = f1 / f2
    out[leg] = row
# P1 V16bp check (RL, 72.814 kN, 2 cm and 1 cm)
a, bp, census, _ = PADS["RL"]
kp = KC / bp + KPHI
zc = (72814.17291553626 / (a * kp)) ** (1.0 / N_EXP)
out["P1_V16bp"] = {str(d): 1e3 * zc * (census[d][0] * d * d * (KC / census[d][1] + KPHI) / (a * kp)) ** (-1.0 / N_EXP)
                   for d in (0.02, 0.01)}
text = json.dumps(out, indent=1) + "\n"
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_bytes(text.encode("ascii"))
print(text, end="")
