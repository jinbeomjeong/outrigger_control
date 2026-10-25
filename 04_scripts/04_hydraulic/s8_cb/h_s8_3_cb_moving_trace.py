"""H-S8-3 item 2: CB moving fallback estimate (s8 spec 9.6) on one leg, 10 Hz and 1 ms views.

The 9.6 moving estimate (two_pressure._extend/_retract_rod_estimate_Pa):
    extend  (command > 0): max(p_back, p_set - psi p_h) + 11.4 bar
    retract (command < 0): max(0, (p_set - p_h) / psi) + 0.7 bar
evaluated with the 10 Hz head reading. Optimism = (p_r,true - p_hat) A_ann (> 0: the
fallback lower bound p_h A_p - p_hat A_ann is above the truth by that much).

Usage: python -I h_s8_3_cb_moving_trace.py <case_dir> <leg> <t0> <t1>
Read only. No random numbers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_R = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
EXT_M, RET_M = 11.4 * BAR, 0.7 * BAR


def cb_params(case: Path):
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    cb = meta["run"]["engine"]["actuator"]["s8"]["counterbalance"]["params"]
    return cb["p_set_Pa"], cb["pilot_ratio"], cb["back_pressure_Pa"]


def estimate(sign, head, p_set, psi, back):
    if sign > 0:
        return max(back, p_set - psi * head) + EXT_M
    return max(0.0, (p_set - head) / psi) + RET_M


def main() -> None:
    case, leg = Path(sys.argv[1]), LEGS.index(sys.argv[2])
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    p_set, psi, back = cb_params(case)
    with np.load(case / "pads.npz", allow_pickle=True) as z:
        p = {k: z[k] for k in ("t", "head_pressure", "rod_pressure", "s_motor", "F_pressure",
                               "cb_y", "cb_delta", "f_seal", "seal_stuck")}
    with np.load(case / "r8_series.npz", allow_pickle=True) as z:
        r8 = {k: z[k] for k in ("t", "issued_u", "valve_u")}
    with np.load(case / "record" / "record.npz", allow_pickle=True) as z:
        rec = {k: z[k] for k in ("t", "meas.head_pressure", "meas.rod_pressure", "meas.stroke",
                                 "u_applied", "u_cmd")}
    t = r8["t"]
    ir = np.clip(np.searchsorted(rec["t"], t - 1e-9), 0, rec["t"].size - 1)
    ip = np.clip(np.searchsorted(p["t"], t - 1e-9), 0, p["t"].size - 1)
    cmd = np.r_[0.0, r8["issued_u"][:-1, leg]]
    print(f"{case.name} {LEGS[leg]}  p_set {p_set / BAR:.0f} bar g, psi {psi}, back {back / BAR} bar g")
    print("t[s]  cmd[mm/s] valve_u  u_appl | ph_meas pr_meas | ph_true pr_true | law  p_hat | opt[kN]")
    for k in np.flatnonzero((t >= t0 - 1e-9) & (t <= t1 + 1e-9)):
        hm = rec["meas.head_pressure"][ir[k], leg]
        sign = np.sign(cmd[k])
        est = estimate(sign, hm, p_set, psi, back) if sign != 0 else np.nan
        law = est - (EXT_M if sign > 0 else RET_M) if sign != 0 else np.nan
        prt = p["rod_pressure"][ip[k], leg]
        opt = (prt - est) * A_R[leg] / 1e3 if sign != 0 else np.nan
        print(f"{t[k]:6.2f} {1e3 * cmd[k]:7.2f} {1e3 * r8['valve_u'][k, leg]:7.2f} "
              f"{1e3 * rec['u_applied'][ir[k], leg]:7.2f} | {hm / BAR:7.2f} "
              f"{rec['meas.rod_pressure'][ir[k], leg] / BAR:7.2f} | "
              f"{p['head_pressure'][ip[k], leg] / BAR:7.2f} {prt / BAR:7.2f} | "
              f"{law / BAR:7.2f} {est / BAR:7.2f} | {opt:6.2f}")
    # 1 ms view
    print("\n1 ms: t  u_plant[mm/s] ph pr  F_p[kN] f_seal stuck cb_y")
    j0, j1 = np.searchsorted(p["t"], t0), np.searchsorted(p["t"], t1)
    u_pl = np.r_[0.0, np.diff(p["s_motor"][:, leg]) / np.diff(p["t"])]
    for j in range(j0, j1, 20):
        print(f"{p['t'][j]:7.3f} {1e3 * u_pl[j]:8.4f} {p['head_pressure'][j, leg] / BAR:7.2f} "
              f"{p['rod_pressure'][j, leg] / BAR:7.2f} {p['F_pressure'][j, leg] / 1e3:7.2f} "
              f"{p['f_seal'][j, leg] / 1e3:6.2f} {int(p['seal_stuck'][j, leg])} "
              f"{p['cb_y'][j, leg]:.3g}")


if __name__ == "__main__":
    main()
