"""J-P3c trapped / fill boundary p*_ret against the P3 (a) / (c) branch switch (read only).

1. Closed form phi p_bA - F / A_ann against the plant function moving_target_rod_pressure_Pa(RET, F)
   over F: where they agree (head clamp at p_bA) and how far apart they are elsewhere.
2. Smallest p*_ret over F (floor clip leak?).
3. Stored R12 RR traces (5e-4 s): plant target of each moving-retract inner step against the target
   recomputed from the net force of the same row and of the next row (read-time recomputation).
4. Retract M1c seed p_rod against p*_ret (seed above target would start in branch (c)).
Gauge pressures; printed bar.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")
sys.path.insert(0, str(Path(__file__).parent))

from outrigger_sim.hydraulics.check_open_delay import RetractConfig, retract_dead  # noqa: E402
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode  # noqa: E402
import hr01_p3_flow_law as h1  # noqa: E402

BAR = 1e5
OUT = Path(__file__).with_suffix(".json")


def main():
    res = {}
    for name in ("front", "rear"):
        leg = h1.leg_consts(name)
        par = leg["params"]
        forces = np.linspace(-20e3, 300e3, 3201)
        true = np.array([par.moving_target_rod_pressure_Pa(RodChamberMode.RET, f) for f in forces])
        closed = leg["phi"] * par.p_head_back_retract_Pa - forces / leg["A_ann"]
        agree = np.abs(true - closed) < 1e-6
        f_switch = float(forces[agree].max()) if agree.any() else None
        res[name] = {
            "clamp_region_F_max_kN": None if f_switch is None else f_switch / 1e3,
            "closed_minus_true_bar_at_F_kN": {
                f"{f:g}": float((np.interp(f * 1e3, forces, closed)
                                 - np.interp(f * 1e3, forces, true)) / BAR)
                for f in (0.0, 2.0, 5.0, 10.0, 25.0, 50.0)},
            "min_p_star_ret_bar": float(true.min() / BAR),
            "F_at_min_kN": float(forces[np.argmin(true)] / 1e3),
            "relief_clip_active_F_below_kN": float(
                forces[true >= par.relief_Pa - 1].max() / 1e3) if (true >= par.relief_Pa - 1).any()
            else None,
        }
        # seed of a retract opening against p*_ret (VN, s 0.395, band 0..16 kN, p_r 2..54 bar)
        cfg = RetractConfig(rod_forward=True, volume_scale=1.0, v_line_m3=285e-6,
                            beta_hose_Pa=0.5e9, psi=3.5, p_crack_Pa=3e5)
        worst = -math.inf
        for p_h in np.array([5, 10, 20, 35, 50, 77, 100, 150, 200, 300]) * BAR:
            for p_r in np.array([-0.9, 2, 5, 13, 30, 54]) * BAR:
                for band in (0.0, 4e3, 8e3, 16e3):
                    force = p_h * leg["A_h"] - p_r * leg["A_ann"]
                    seed = retract_dead(cfg, p_h, p_r, band, 0.395, 0.0, leg["A_h"], leg["A_ann"],
                                        0.70, 0.05, 0.05, 1e9, 2e5)["p_rod"]
                    p_star = par.moving_target_rod_pressure_Pa(RodChamberMode.RET, force)
                    if p_r < p_star:            # seed from a pressure below the target only
                        worst = max(worst, seed - p_star)
        res[name]["seed_minus_p_star_max_bar_when_p_r_below_target"] = worst / BAR
    # stored traces: target of the step vs recomputation from the row's / next row's net force
    rear = h1.leg_consts("rear")["params"]
    trace = {}
    for tag in ("VB", "LS2", "LS3"):
        d = np.load(Path(__file__).parent / "h01_trace" / f"trace_{tag}.npz")
        cols = [str(c) for c in d["cols"]]
        a = d["data"]
        col = {c: a[:, cols.index(c)] for c in cols}
        mov = (col["locked"] < 0.5) & (col["last_dir"] < 0)
        idx = np.flatnonzero(mov[:-1])
        same = np.array([rear.moving_target_rod_pressure_Pa(RodChamberMode.RET, f)
                         for f in col["net_N"][idx]])
        nxt = np.array([rear.moving_target_rod_pressure_Pa(RodChamberMode.RET, f)
                        for f in col["net_N"][idx + 1]])
        side_flip = np.sign(col["p_lag"][idx] - col["p_target"][idx]) != np.sign(
            col["p_lag"][idx] - nxt)
        trace[tag] = {"moving_retract_steps": int(idx.size),
                      "max_abs_target_vs_same_row_bar": float(
                          np.abs(same - col["p_target"][idx]).max() / BAR) if idx.size else None,
                      "max_abs_target_vs_next_row_bar": float(
                          np.abs(nxt - col["p_target"][idx]).max() / BAR) if idx.size else None,
                      "side_flips_with_next_row_target": int(side_flip.sum())}
    res["trace_R12_RR"] = trace
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
