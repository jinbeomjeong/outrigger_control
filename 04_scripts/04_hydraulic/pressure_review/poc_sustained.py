"""Is the slow retract oscillation sustained? One long retract, statistics over the last half of the command. Current REXOME35."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import poc_numpy as pn
import poc_reversal as pr
from common import SCRATCH, dump, pin_two_cores
from hopsan_run import run_hopsan
from params import LEGS, load_params

LOG = ["Rod#P2#Velocity", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure", "POCB#P1#Pressure", "Kg#P1#Force", "POCA#x#Value"]
STROKES = {0.05: 0.010, 0.1: 0.020, 0.25: 0.040, 1.0: 0.060}
REAR = 0.833
HOLD_END = 0.5
LOG_DT = 2.0e-4


def one_retract(alpha: float, v_max: float):
    dur = STROKES[alpha] / (alpha * v_max)
    t_on = 0.5
    grid = np.arange(0.0, t_on + dur + HOLD_END + 1e-9, 1.0e-3)
    cmd = np.zeros_like(grid)
    cmd[(grid >= t_on) & (grid < t_on + dur)] = -alpha * v_max
    return grid, cmd, [("ret_long", t_on, t_on + dur, -1)]


def stats(t, v, force, p_h, p_r, on, off):
    win = (t >= 0.5 * (on + off)) & (t < off)
    y = v[win] - v[win].mean()
    tt = t[win]
    if y.std() > 1e-6:
        ups = np.flatnonzero((y[:-1] < 0) & (y[1:] >= 0))
        freq = (len(ups) - 1) / (tt[ups[-1]] - tt[ups[0]]) if len(ups) > 1 else 0.0
    else:
        freq = 0.0
    t10 = np.arange(tt[0], off, 0.1)
    return {"window_s": float(off - 0.5 * (on + off)), "v_mean_mm_s": float(v[win].mean() * 1e3), "v_std_mm_s": float(v[win].std() * 1e3), "up_crossing_Hz": float(freq),
            "force_ptp_kN": float(np.ptp(force[win]) / 1e3), "force_std_kN": float(force[win].std() / 1e3), "p_h_min": float(p_h[win].min()), "p_h_max": float(p_h[win].max()),
            "p_r_min": float(p_r[win].min()), "p_r_max": float(p_r[win].max()),
            "p_r_10Hz_ptp": float(np.ptp(np.interp(t10, t, p_r))), "p_h_10Hz_ptp": float(np.ptp(np.interp(t10, t, p_h)))}


def main() -> None:
    pin_two_cores()
    p = load_params()
    out = {"meta": {"dimensions": "current REXOME35", "pressure": "bar gauge", "window": "last half of one long retract command, single leg, A,B->T neutral, Hopsan binary check, ts 1e-5 s",
                    "strokes_m": {f"{k:g}": v for k, v in STROKES.items()}, "note": "the earlier 3 mm table used a short window that can contain the opening transient"}, "hopsan": {}, "numpy": {}}
    pr.motions = one_retract
    pn.motions = one_retract
    for i, fs_list in ((0, (0.0, 2e3, 4e3, 8e3)), (2, (0.0, 4e3))):
        pr.LEG_INDEX = i
        pr.C_LOCK = 34403.5 if i < 2 else 30348.5
        for fs0 in fs_list:
            pr.ROD_FS = fs0 * (1.0 if i < 2 else REAR)
            for alpha in STROKES:
                case = f"{LEGS[i]}_Fs{fs0 / 1e3:g}_a{alpha:g}"
                folder = SCRATCH / "pocl" / case
                model, grid, _u, seq, _f0, _ah, _ar = pr.build(case, folder, p, alpha, True, pr.BETA_HOSE, pr.P_R0)
                df, _un, info = run_hopsan(model, folder, sim=(0.0, pr.TS, float(grid[-1])), log_only=LOG, num_log_samples=int(grid[-1] / LOG_DT) + 1, timeout=250.0)
                t = df.index.to_numpy()
                r = stats(t, df["Rod#P2#Velocity"].to_numpy(), df["Kg#P1#Force"].to_numpy(), df["POCA#P2#Pressure"].to_numpy() / 1e5 - 1.0,
                          df["POCB#P2#Pressure"].to_numpy() / 1e5 - 1.0, seq[0][1], seq[0][2])
                r["wall_s"] = info["wall_s"]
                out["hopsan"][case] = r
                print(case, {k: round(v, 2) for k, v in r.items() if k in ("v_mean_mm_s", "v_std_mm_s", "up_crossing_Hz", "force_ptp_kN", "p_r_min", "p_r_max", "p_r_10Hz_ptp", "wall_s")}, flush=True)
    pr.LEG_INDEX, pr.ROD_FS, pr.C_LOCK = 0, 0.0, 34403.5
    for fs0, alpha in ((0.0, 0.25), (4e3, 0.25), (4e3, 0.05)):
        rows, grid, _u, seq, _f0 = pn.run_two_chamber(p, alpha, 0.02, 10e5, True, fs=fs0)
        r = stats(rows[:, 0], rows[:, 2], rows[:, 7], rows[:, 3] / 1e5, rows[:, 4] / 1e5, seq[0][1], seq[0][2])
        key = f"FL_Fs{fs0 / 1e3:g}_a{alpha:g}_tau0.02_band10"
        out["numpy"][key] = r
        print("numpy", key, {k: round(v, 2) for k, v in r.items() if k in ("v_mean_mm_s", "v_std_mm_s", "up_crossing_Hz", "force_ptp_kN", "p_r_min", "p_r_max")}, flush=True)
    dump("poc_sustained.json", out)


if __name__ == "__main__":
    main()
