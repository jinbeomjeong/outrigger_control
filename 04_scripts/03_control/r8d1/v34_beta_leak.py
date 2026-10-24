"""Quantify the beta override leak of run_S6C into the controller geometry and the crawler kt/kn.

Rebuilds the run_S6C beta overrides (kn per pad from the beta reference, oil bulk modulus) and
compares C2Geometry fields and the crawler (kt/kn)_pad mean with the beta 1.0 YAML.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_src"))
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references  # noqa: E402
from outrigger_sim.control.c2 import C2Geometry, C2Config  # noqa: E402

KN_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"
LEGS = ("FL", "FR", "RL", "RR")
BETA_KEYS = {0.69: "beta_6.9e+08", 1.0: "beta_1.0e+09", 1.6: "beta_1.6e+09"}
refs = load_references()
base = None
for beta, key in BETA_KEYS.items():
    over = {}
    if beta != 1.0:
        k = refs.get(BETA_K_L1_N_M, beta=key)
        for leg, v in zip(LEGS, k):
            over[f"{KN_KEY}.{leg}"] = float(v)
        over["actuator.oil_bulk_modulus_eff_Pa"] = float(key.removeprefix("beta_"))
    p = load_params(level="top", overrides=over or None)
    g = C2Geometry.from_params(p)
    kn = p.get(KN_KEY)
    kt = p.get("contact.rigid_floor.L1.kt_per_pad_N_m")
    ratio = np.mean([float(kt[l]) / float(kn[l]) for l in LEGS])
    row = dict(beta=beta, kn=[round(float(kn[l]) / 1e7, 4) for l in LEGS], k_nom=g.nominal_pad_stiffness_N_m,
               S_ii=np.round(g.load_sensitivity_diag_N_m / 1e6, 3).tolist(), oil=g.oil_bulk_modulus_Pa,
               kt_over_kn=round(float(ratio), 4))
    if base is None and beta == 1.0:
        pass
    print(row)
cfg = C2Config().with_10hz_d1()
print("config support_pad_stiffness", cfg.support_pad_stiffness_N_m, "probe_correction", cfg.probe_correction_sensitivity_N_m)
