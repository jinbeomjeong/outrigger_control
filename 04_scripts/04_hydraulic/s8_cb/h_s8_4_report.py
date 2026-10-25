"""H-S8-4: report numbers from h_s8_4_release_scan.json + 1 ms detail of the 7 collapse cases.

Usage: h_s8_4_report.py <scan.json> <batch_dir> <out.json>
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1.0e5
V_MAX = 0.020924          # m/s, CLAUDE.md
OVERLAP = 0.02            # spool overlap end delta_ol (11.4, ASSUMPTION)
TAU_ROD = 0.05            # release_tau_s (moving rod pressure lag)
LEGS = ("FL", "FR", "RL", "RR")
SEVEN = [("ML00_ep5", "RL"), ("ML18_ep6", "FR"), ("ML28_ep6", "RL"), ("ML36_ep7", "RR"),
         ("ML39_ep5", "RR"), ("ML81_ep5", "RR"), ("ML88_ep0", "RR")]


def main() -> None:
    scan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    batch = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    rel = scan["releases_big"]
    u_ol = OVERLAP * V_MAX
    small = [r for r in rel if abs(r["u_new_m_s"]) < u_ol]
    jumps = np.array([abs(r["rod_jump_bar"]) for r in rel])
    # settle time of the stale-start error with the model's own lag (to 1 bar)
    settle = np.array([TAU_ROD * math.log(max(j, 1.0)) for j in jumps])
    by_ep = {}
    for r in rel:
        by_ep.setdefault(r["case"], 0)
        by_ep[r["case"]] += 1
    res = {
        "u_overlap_m_s": u_ol,
        "big_jumps": len(rel),
        "big_jumps_with_u_new_below_overlap": len(small),
        "big_jumps_down": int(sum(r["rod_jump_bar"] < 0 for r in rel)),
        "big_jumps_up": int(sum(r["rod_jump_bar"] > 0 for r in rel)),
        "episodes_with_big_jump": len(by_ep),
        "stale_error_settle_to_1bar_s_p50_p90_max": [float(np.percentile(settle, q))
                                                     for q in (50, 90, 100)],
        "u_new_abs_p10_p50_p90_m_s": [float(np.percentile([abs(r["u_new_m_s"]) for r in rel], q))
                                      for q in (10, 50, 90)],
        "seven": [],
    }
    for case, leg_name in SEVEN:
        leg = LEGS.index(leg_name)
        ep = batch / "episodes" / case
        z = np.load(ep / "pads.npz", allow_pickle=True)
        r8 = np.load(ep / "r8_series.npz", allow_pickle=True)
        t = z["t"]
        cands = [r for r in rel if r["case"] == case and r["leg"] == leg_name]
        lift = [x for x in scan["liftoffs_locked"] if x["case"] == case and x["leg"] == leg_name]
        # the release closest to a lift-off
        best = None
        for r in cands:
            for x in lift:
                d = abs(r["t_release_s"] - x["t_s"])
                if best is None or d < best[0]:
                    best = (d, r, x)
        if best is None:
            res["seven"].append({"case": case, "leg": leg_name, "found": False})
            continue
        _, r, x = best
        tb = r["t_boundary_s"]
        k = int(np.argmin(np.abs(r8["t"] - tb)))
        nxt = r8["issued_u"][k + 1, leg] if k + 1 < len(r8["t"]) else math.nan
        i0 = int(np.searchsorted(t, r["t_release_s"]))
        i1 = int(np.searchsorted(t, tb + 0.1))
        n = z["N"][:, leg]
        recon = np.flatnonzero(n[i0 + 1:] > 0.0)
        t_recontact = float(t[i0 + 1 + recon[0]]) if recon.size else math.nan
        res["seven"].append({
            "case": case, "leg": leg_name, "found": True,
            "t_boundary_s": round(tb, 4), "t_liftoff_s": round(x["t_s"], 4),
            "t_release_s": round(r["t_release_s"], 5), "t_x_ms": round(r["t_x_ms"], 3),
            "liftoff_minus_release_ms": round((x["t_s"] - r["t_release_s"]) * 1e3, 2),
            "u_new_m_s": r["u_new_m_s"], "u_new_over_vmax_pct": 100 * r["u_new_m_s"] / V_MAX,
            "next_issued_u_m_s": float(nxt),
            "rod_before_bar": round(r["rod_before_bar"], 2),
            "rod_after_bar": round(r["rod_after_bar"], 2),
            "head_before_bar": round(r["head_before_bar"], 2),
            "head_after_bar": round(r["head_after_bar"], 2),
            "rod_at_lock_bar": r.get("rod_at_lock_bar"),
            "p_r0_ext_bar": r["p_r0_ext_bar"], "p_r0_ret_bar": r["p_r0_ret_bar"],
            "s_link_change_to_next_boundary_mm": float(
                (z["s_link"][i1, leg] - z["s_link"][i0, leg]) * 1e3),
            "s_ref_change_to_next_boundary_mm": float(
                (z["s_motor"][i1, leg] - z["s_motor"][i0, leg]) * 1e3),
            "t_recontact_s": t_recontact,
            "recontact_after_release_s": t_recontact - r["t_release_s"],
        })
    out_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
