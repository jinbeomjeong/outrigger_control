"""Hand need (s09 formula) at the P7-7 fill start and its sensitivity to the inputs that differ
between the review state and the probe read (p_h, p_r, band, void).

Usage: python -I -B s10_need_sens.py <scratch dir with s09_p77.py>
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("s09", Path(sys.argv[1]) / "s09_p77.py")
s09 = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], "."]  # s09 main loop reads argv[1]; give a dir without the npz
try:
    spec.loader.exec_module(s09)
except FileNotFoundError:
    pass

S = 0.408358
cases = [
    ("review state (p_h 99.39, p_r 5.07, band 0)", 99.39e5, 5.07e5, 0.0, 0.0),
    ("probe read 32.2 s (p_h 99.671, p_r 4.712, band 0)", 99.671e5, 4.712e5, 0.0, 0.0),
    ("probe read 32.1 s (p_h 99.390, p_r 5.074, band 0)", 99.390e5, 5.074e5, 0.0, 0.0),
    ("probe read 32.3 s (p_h 99.825, p_r 4.512, band 0)", 99.825e5, 4.512e5, 0.0, 0.0),
    ("probe read 32.2 s, band 13 kN", 99.671e5, 4.712e5, 13000.0, 0.0),
]
for plant in ("Mslow", "M"):
    print("==", plant, s09.SETS[plant])
    for label, ph, pr, band, void in cases:
        need, p_b, p_rod, parts = s09.retract_dead(ph, pr, band, S, void, **s09.SETS[plant])
        print(f"  {label}: need {need * 1e3:.4f} mm, p_b {p_b / 1e5:.3f}, p_rod {p_rod / 1e5:.3f}, "
              f"rise at opening {(p_rod - pr) / 1e5:.3f} bar, "
              + " ".join(f"{k}={v * 1e3:.4f}" for k, v in parts.items()))
    # d need / d p_r and d need / d p_h (finite difference)
    base, *_ = s09.retract_dead(99.39e5, 5.07e5, 0.0, S, 0.0, **s09.SETS[plant])
    dpr, *_ = s09.retract_dead(99.39e5, 4.07e5, 0.0, S, 0.0, **s09.SETS[plant])
    dph, *_ = s09.retract_dead(100.39e5, 5.07e5, 0.0, S, 0.0, **s09.SETS[plant])
    print(f"  d need / d p_r = {(dpr - base) * 1e3:+.4f} mm per -1 bar p_r; "
          f"d need / d p_h = {(dph - base) * 1e3:+.4f} mm per +1 bar p_h")
