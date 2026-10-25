"""S8 V15 Chrono batch, part 2: proposed revised rows (dynamics_model.md rev. 42 5.29) evaluated
on the existing records, and the mechanical ledger residual without the dashpot channel.

Window W1 = from the true F_min crossing (judge value) to the 1e-5 s window start
(``timeline.fine_start_t_s``, RL 20 ms mean contact force 1.5 kN), i.e. before the NSC
near-zero-contact chatter. Rows:
 * A-slide: per leg mean edge deficit ``F_s,i - sign_i f_i`` and net piston slip direction;
 * A-read: RL ``G - (F + F_s,RL)`` mean in W1; at lift-off ``G <= F + F_s,RL + 300 N`` and
   ``G >= F - F_s,RL``; ``F_RL`` at lift-off vs ``-m g`` (+-300 N);
 * ledger: ``R_mech = R - D_visc`` (dashpot channel removed) at the W1 end and run end, max.

Run (Chrono-dev, numpy only): python -I s8_v15_chrono_judge_windows.py
Writes ``06_analysis/00_dynamics/s8/s8_v15_chrono_judge_windows.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "07_results" / "S8" / "v15_20261025_132215"
REF = ROOT / "06_analysis" / "00_dynamics" / "s8_v15_reference.json"
OUT = ROOT / "06_analysis" / "00_dynamics" / "s8" / "s8_v15_chrono_judge_windows.json"
SIGN = np.array([-1.0, -1.0, -1.0, 1.0])
SLIP_SIGN = np.array([1.0, 1.0, 1.0, -1.0])  # piston slides opposite to f
REAR = 0.8333
LEDGER = ("E_kin_J", "E_grav_J", "U_lat_J", "U_ax_J", "D_visc_J", "D_f_J", "W_m_J", "W_L_J",
          "W_res_J", "W_switch_J")


def one(cid: str, fs: float, ref: dict) -> dict:
    z = np.load(BATCH / cid / "series.npz")
    res = json.loads((BATCH / cid / "result.json").read_text(encoding="utf-8"))
    tl = res["timeline"]
    met = res["judge"]["metrics"]
    t = z["t_s"]
    lim = np.array([fs, fs, REAR * fs, REAR * fs])
    t1 = met["F_min_true"]["t_s"]
    t2 = tl["fine_start_t_s"]
    w = (t >= t1) & (t < t2)
    f, F, G, sp = z["f_N"][w], z["F_N"][w], z["Fp_N"][w], z["s_p_m"][w]
    out: dict = {"W1_s": [t1, t2], "W1_lam_mm": [1e3 * float(z["lam_m"][w][0]),
                                                  1e3 * float(z["lam_m"][w][-1])]}
    if fs > 0:
        dfc = lim - SIGN * f
        out["edge_deficit_mean_N"] = dfc.mean(axis=0).round(1).tolist()
        out["edge_deficit_max_1ms_N"] = dfc.max(axis=0).round(1).tolist()
        out["edge_deficit_mean_over_F_s"] = (dfc.mean(axis=0) / lim).round(4).tolist()
        slip = 1e6 * (sp[-1] - sp[0])
        out["piston_slip_um"] = slip.round(2).tolist()
        out["slip_direction_ok"] = bool(np.all(np.sign(slip) == SLIP_SIGN))
        out["RL_G_minus_edge_track_mean_N"] = float(np.mean(G[:, 2] - (F[:, 2] + lim[2])))
    ra = met["at_liftoff"]
    g, tr = ra["net_N"][2], ra["true_N"][2]
    mg = -ref["at_liftoff"]["true_cyl_force_N (= -m_rod g)"]
    out["at_liftoff"] = {"G_RL_N": g, "F_RL_N": tr, "F_RL_plus_mg_N": tr + mg,
                         "upper_bound_ok (G <= F + F_s + 300)": bool(g <= tr + lim[2] + 300.0),
                         "lower_bound_ok (G >= F - F_s)": bool(g >= tr - lim[2] - 1e-6),
                         "deficit_vs_upper_N": tr + lim[2] - g}
    # ledger without the dashpot channel
    ok = np.isfinite(z["E_kin_J"])
    i0 = int(np.flatnonzero(ok)[0])
    c = {k: z[k] - z[k][i0] for k in LEDGER}
    e = c["E_kin_J"] + c["E_grav_J"] + c["U_lat_J"] + c["U_ax_J"]
    r_mech = e + c["D_f_J"] - c["W_m_J"] - c["W_L_J"] - c["W_res_J"] - c["W_switch_J"]
    k2 = int(np.flatnonzero(t < t2)[-1])
    last = int(np.flatnonzero(ok)[-1])
    d_f = float(c["D_f_J"][last])
    out["ledger_mech"] = {
        "R_mech_at_fine_start_J": float(r_mech[k2]),
        "R_mech_end_J": float(r_mech[last]),
        "R_mech_max_J": float(np.nanmax(r_mech[ok])),
        "R_mech_min_J": float(np.nanmin(r_mech[ok])),
        "R_mech_change_in_fine_window_J": float(r_mech[last] - r_mech[k2]),
        "D_f_J": d_f,
        "R_mech_end_over_D_f": float(r_mech[last] / d_f) if d_f > 0 else None,
        "D_visc_at_fine_start_J": float(c["D_visc_J"][k2]),
        "D_visc_end_J": float(c["D_visc_J"][last]),
    }
    return out


def main() -> None:
    ref = json.loads(REF.read_text(encoding="utf-8"))["V15_rev39"]["rod_side"]["a_upsweep_unilateral"]
    out = {}
    for cid, fs in (("V15a_L0", 0.0), ("V15a_L2", 2000.0), ("V15a_L4", 4000.0),
                    ("V15a_L8", 8000.0), ("V15a_L8_v005", 8000.0)):
        out[cid] = one(cid, fs, ref[f"L{int(fs / 1000)}"])
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
