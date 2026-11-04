"""Sensitivity of the steady circuit to the criteria 8.3 ranges (hand_calc level).

Grid: dp_c 6 / 10 / 20 bar x dp_ls 12 / 20 / 30 bar, law priority / proportional, width x1/2, x2
on a few scenarios at eta_v 0.90 and 0.85. Also the LS margin table: dp_ls minus the MCV
gallery loss (ASSUMPTION 1 bar at full flow) against the drop the compensator needs,
for the highest-load front leg at v_max. Writes sensitivity.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from hand_calc import solve  # noqa: E402
from params import LEGS, OUT_DIR, load_params  # noqa: E402
from scenarios import BY_NAME  # noqa: E402

GALLERY_LOSS = 1e5  # Pa, ASSUMPTION
CASES = ("B90p", "B85p", "B90c", "B85c", "C185p", "C185c", "C285p", "T185p")


def margin_table(p0) -> list[dict]:
    rows = []
    for dpc in (6e5, 10e5, 20e5):
        for dpls in (12e5, 20e5, 30e5):
            p = p0.with_(dp_comp=dpc, dp_unl=dpls)
            K = p.K_spool[0]
            need = dpc * (1.0 + (K / p.X_comp) ** 2)  # D for y_open = dp_c, front leg at v_max
            margin = dpls - GALLERY_LOSS - (need + p.width)
            rows.append({"dp_c_bar": dpc / 1e5, "dp_ls_bar": dpls / 1e5, "need_D_bar": need / 1e5,
                         "margin_bar": margin / 1e5, "reaches_v_max": bool(margin >= 0.0)})
    return rows


def main() -> None:
    p0 = load_params()
    out: dict = {"margin": margin_table(p0), "runs": {}}
    variants = {
        "nominal": {},
        "dpc6_ls12": {"dp_comp": 6e5, "dp_unl": 12e5},
        "dpc6_ls20": {"dp_comp": 6e5, "dp_unl": 20e5},
        "dpc6_ls30": {"dp_comp": 6e5, "dp_unl": 30e5},
        "dpc10_ls12": {"dp_comp": 10e5, "dp_unl": 12e5},
        "dpc10_ls30": {"dp_comp": 10e5, "dp_unl": 30e5},
        "dpc20_ls12": {"dp_comp": 20e5, "dp_unl": 12e5},
        "dpc20_ls20": {"dp_comp": 20e5, "dp_unl": 20e5},
        "dpc20_ls30": {"dp_comp": 20e5, "dp_unl": 30e5},
        "proportional": {"law": "proportional"},
        "width_half": {"width": 0.5e5},
        "width_double": {"width": 2e5},
    }
    for tag, kw in variants.items():
        p = p0.with_(**kw)
        out["runs"][tag] = {}
        for name in CASES:
            r = solve(p, BY_NAME[name])
            out["runs"][tag][name] = {"v_mm_s": dict(zip(LEGS, (r["v"] * 1e3).round(3).tolist())),
                                      "r": dict(zip(LEGS, (r["v"] / (np.array(BY_NAME[name].u) * p.v_max)).round(4).tolist())),
                                      "p_P_bar_g": round(r["p_P"] / 1e5, 2), "Q_byp_L_min": round(r["Q_byp"] * 6e4, 3)}
        row = out["runs"][tag]
        print(f"{tag:14s}", " ".join(f"{n}:{min(row[n]['r'].values()):.3f}" for n in CASES))
    for r in out["margin"]:
        print(r)
    (OUT_DIR / "sensitivity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
