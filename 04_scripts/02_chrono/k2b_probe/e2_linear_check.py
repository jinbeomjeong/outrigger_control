"""K-2b E2 diagnosis: vertical linear static S model on the Chrono L1-R geometry with per-leg stiffness choices.

Rigid deck, 3 DOF (heave w, roll a, pitch b; vertical displacement at (x, y) = w + a y - b x, world x forward,
y left), vertical springs only: 4 pads (stiffness k_i, compression s_i - u(x_i, y_i)) and the loaded crawler spheres
(kn_sphere, compression -u). No tangential bushings, no geometric stiffness (ASSUMPTION of this check).
Geometry from the restored ``S6_crawler_top_flat`` L1-R snapshot (pad sphere centres, loaded crawler spheres).

Variants: ``kn`` (all pads YAML ``kn_per_pad`` = series(k_oil, ...), the harness k_leg), ``mode`` (pads by their
L1-R mode in the E2 base state: FLOOR -> kn, LOCK -> ``derivation.k_lock_N_m``; the stepped leg kn), ``lock``
(all k_lock). Prints S per variant (kN/mm) and writes ``E2/e2_linear_check.json``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"] = "one_sided_parallel"
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import numpy as np  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
STATES = Path(r"C:\workspace\outrigger_control\07_results\states_L1R")


def s_matrix(xy_pad, k_pad_cols, xy_cr, k_cr):
    """S[i, j] = dF_i / ds_j; k_pad_cols[j] = the 4 pad stiffnesses used for column j."""
    S = np.zeros((4, 4))
    for j in range(4):
        k = np.asarray(k_pad_cols[j], float)
        pts = np.vstack([xy_pad, xy_cr])
        kk = np.concatenate([k, np.full(len(xy_cr), k_cr)])
        B = np.column_stack([np.ones(len(pts)), pts[:, 1], -pts[:, 0]])  # u = B q
        K = B.T @ (kk[:, None] * B)
        f = B[j] * k[j]  # load of the unit extension of leg j (s_j = 1)
        q = np.linalg.solve(K, f)
        u = B[:4] @ q
        s = np.zeros(4)
        s[j] = 1.0
        S[:, j] = k * (s - u)
    return S * 1e-6  # N/m -> kN/mm


def main() -> None:
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot

    import s6_stage2 as st

    params = load_params(level="top")
    model, _ = st.build_crawler_model(params, "flat", attach=False)
    model.restore(load_snapshot("S6_crawler_top_flat", params_sha256=params.sha256, directory=STATES))
    pr = model.probe()
    xy_pad = np.asarray(pr.pad_sphere_centre_world_m)[:, :2]
    sup = model.superstructure
    import pychrono as ch

    cr_world = np.array([[v.x, v.y, v.z] for v in (sup.TransformPointLocalToParent(ch.ChVector3d(*c))
                                                  for c in model.crawler_centres_local_m)])
    normals = np.asarray(model.crawler_normals(), float)
    geom = ROOT / "06_analysis/02_control/k2/k2b_probe/E2_geom/RR/result.json"
    if geom.exists():  # loaded spheres of the E2 base state (pads at ~22-28 kN), not of the unloaded-leg snapshot
        g = json.loads(geom.read_text(encoding="utf-8"))
        normals = np.asarray(g["base_crawler_normals_N"], float)
    loaded = normals > 0
    xy_cr = cr_world[loaded, :2]
    k_cr = float(model.crawler_bushing_values.meta()["kn_sphere_N_m"])
    kn = np.array([params.get("contact.rigid_floor.L1.kn_per_pad_N_m")[n] for n in LEGS])
    klock = np.array([params.get("contact.rigid_floor.L1.derivation.k_lock_N_m")[n] for n in LEGS])
    base_mode = np.array([4, 4, 3, 3])  # E2 base: FL, FR FLOOR; RL, RR LOCK (result.json base_l1r_mode)
    k_mode = np.where(base_mode == 3, klock, kn)
    variants = {"kn": [kn] * 4, "lock": [klock] * 4,
                "mode": [np.where(np.arange(4) == j, kn[j], k_mode) for j in range(4)]}
    e2 = json.loads((ROOT / "06_analysis/02_control/k2/k2b_probe/E2/e2_summary.json").read_text(encoding="utf-8"))
    S_chrono = np.asarray(e2["S_chrono_kN_per_mm"])
    out = {"geometry": {"pad_xy_world_m": xy_pad.tolist(), "crawler_loaded_xy_world_m": xy_cr.tolist(),
                        "crawler_loaded_count": int(loaded.sum()), "crawler_normal_sum_N": float(normals.sum()),
                        "cog_world_m": np.asarray(pr.cog_pos_m).tolist(), "kn_sphere_N_m": k_cr},
           "kn_per_pad_N_m": kn.tolist(), "k_lock_N_m": klock.tolist(), "variants": {}}
    np.set_printoptions(precision=2, suppress=True)
    for name, cols in variants.items():
        S = s_matrix(xy_pad, cols, xy_cr, k_cr)
        err = S - S_chrono
        out["variants"][name] = {"S_kN_per_mm": S.tolist(), "minus_chrono": err.tolist(),
                                 "rms_minus_chrono": float(np.sqrt(np.mean(err**2)))}
        print(name, "\n", S, "\n minus chrono rms", np.sqrt(np.mean(err**2)))
    (ROOT / "06_analysis/02_control/k2/k2b_probe/E2/e2_linear_check.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["geometry"], indent=0)[:1500])


if __name__ == "__main__":
    main()
