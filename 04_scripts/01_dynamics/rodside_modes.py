"""Independent 6-DoF reference for the S4 'rodside' Chrono case (k_n x kv_with_rod_side_over_kv, both directions).

Same L1 matrices as run_reference._l1_matrices (vertical spring + preload and tangential spring at the swivel ball
centre), top auger level, k_n scaled per leg. Also the one-sided bound: k_n scaled only where the mode unloads.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import run_reference as rr  # noqa: E402

p = dm.load_params()
geo = dm.geometry_from_params(p)
ref = json.load(open(ROOT / "06_analysis/00_dynamics/reference.json", encoding="utf-8"))
cfg = ref["chrono_test_references"]["L1_rigid_motor_lumped_contact"]
kv = np.array(cfg["k_vertical_N_m"])
kh = np.array(cfg["k_horizontal_N_m"])
ratio = None
for blk in ref.values():
    if isinstance(blk, dict) and "kv_with_rod_side_over_kv" in blk:
        ratio = np.array(blk["kv_with_rod_side_over_kv"])
print("ratio", ratio)
e_op = geo.touch_extension + dm.ASSUMPTIONS["crawler_clearance_m"]
bw = dm.body_with_rods(p, geo, "top", e_op)
g, xy = geo.g, geo.pad_xy
z_pad = geo.pad_z_retracted - e_op
z_ball = z_pad + rr._ball_heights(p)
M = dm.mass_6dof(bw)
zero = np.zeros(4)
chrono = json.load(open(ROOT / "06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json", encoding="utf-8"))["rodside"]


def freqs(k):
    Fc, _, _ = dm.static_loads(k, xy, bw.mass * g, bw.com[:2])
    K = rr._l1_matrices(bw, xy, z_ball, z_ball, k, kh, zero, zero, Fc)[0]
    w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
    return np.asarray(f[:6]), Fc, cls


f0, F0, c0 = freqs(kv)
f1, F1, c1 = freqs(kv * ratio)
fc = np.array(chrono["f_era_Hz"])
print("labels", c0)
print("nominal  f", np.round(f0, 4))
print("rodside  f", np.round(f1, 4), "rel vs nominal", np.round(f1 / f0 - 1, 4))
print("chrono   f", np.round(fc, 4), "chrono/model - 1", np.round(fc / f1 - 1, 5))
print("chrono static contact", chrono["linear_static"]["contact_N"], "model", np.round(F1, 1))
# penetration check: F / k
print("penetration model mm", np.round(F1 / (kv * ratio) * 1e3, 4), "chrono", np.round(chrono["penetration_mm"], 4))
