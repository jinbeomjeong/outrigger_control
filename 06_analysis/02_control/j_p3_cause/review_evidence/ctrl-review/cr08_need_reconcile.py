"""Which inputs reproduce the spec's retract need 0.92 / 1.24 mm (front, p_h 77 bar)? (read only)

Usage: python -I -B cr08_need_reconcile.py <worktree>
Calls the repo M1c ``retract_dead`` (RetractConfig as the gate builds it) on an input grid and
prints need [mm]. Front leg areas, stroke 0.395 m, s_max 0.70 m, p_T 2 bar.
"""

import itertools
import sys

sys.path.insert(0, sys.argv[1] + r"\03_src")

from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402
from outrigger_sim.hydraulics.check_open_delay import CheckValveValues  # noqa: E402

BAR = 1e5
cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=CheckValveValues.v_line_m3,
                    beta_hose_Pa=CheckValveValues.beta_hose_Pa, psi=CheckValveValues.psi,
                    p_crack_Pa=CheckValveValues.p_crack_Pa)
A_H, A_ANN = 1.327e-2, 3.770e-3
rows = []
for p_h, p_r, f_band, (beta, l0r, l0h) in itertools.product(
        (77.0, 86.0), (2.0, -0.91325), (8e3, 0.0),
        ((1.0e9, 0.05, 0.05), (0.69e9, 0.10, 0.08), (0.69e9, 0.05, 0.05), (1.0e9, 0.10, 0.08))):
    r = retract_dead(cfg, p_h * BAR, p_r * BAR, f_band, 0.395, 0.0, A_H, A_ANN, 0.70, l0r, l0h,
                     beta, 2.0 * BAR)
    rows.append((p_h, p_r, f_band / 1e3, beta / 1e9, l0r, l0h, r["need"] * 1e3, r["p_open"] / BAR))
for row in rows:
    print("p_h %5.1f p_r %6.3f Fb %4.1f kN beta %.2f L0r %.2f L0h %.2f -> need %.3f mm, p_open %.2f"
          % row)
