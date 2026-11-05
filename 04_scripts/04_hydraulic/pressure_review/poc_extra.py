"""Retract limit cycle of the single-leg POC circuit: frequency, 10 Hz readings, meter-out land sensitivity."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import poc_reversal as pr
from common import SCRATCH, dump, pin_two_cores
from hopsan_run import run_hopsan
from params import load_params

LOG = ["Rod#P2#Velocity", "POCA#P2#Pressure", "POCB#P2#Pressure", "POCA#P1#Pressure", "POCB#P1#Pressure", "Kg#P1#Force"]


def dominant_hz(t, y):
    y = y - y.mean()
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
    freq = np.fft.rfftfreq(len(y), t[1] - t[0])
    return float(freq[int(np.argmax(spec[1:])) + 1])


def main() -> None:
    pin_two_cores()
    p = load_params()
    out = {"meta": {"dimensions": "current REXOME35, FL", "pressure": "bar gauge", "poc": "Hopsan binary pilot check, no hysteresis",
                    "meter_out_ratio": "A->T land / P->A land; 0.284 = A_r/A_h (symmetric meter-in/out flow areas), 1 = asymmetric"},
           "cases": {}}
    for ratio in (1.0, 0.5, 0.284):
        pr.METER_OUT_RATIO = ratio
        for alpha in (0.05, 0.25, 1.0):
            case = f"mo{ratio:g}_a{alpha:g}"
            folder = SCRATCH / "poc2" / case
            model, grid, u, seq, f0, a_h, a_r = pr.build(case, folder, p, alpha, True, pr.BETA_HOSE, pr.P_R0)
            df, _un, info = run_hopsan(model, folder, sim=(0.0, pr.TS, float(grid[-1])), log_only=LOG,
                                       num_log_samples=int(grid[-1] / 2e-4) + 1, timeout=250.0)
            rows = pr.metrics(df, grid, u, seq, f0)
            t = df.index.to_numpy()
            name, on, off, _s = seq[0]
            win = (t > on + 0.6 * (off - on)) & (t < off)
            v = df["Rod#P2#Velocity"].to_numpy()
            p_h = df["POCA#P2#Pressure"].to_numpy() / 1e5 - 1.0
            p_r = df["POCB#P2#Pressure"].to_numpy() / 1e5 - 1.0
            force = df["Kg#P1#Force"].to_numpy()
            t10 = np.arange(on, off, 0.1)
            net = a_h * np.interp(t10, t, p_h) * 1e5 - a_r * np.interp(t10, t, p_r) * 1e5
            out["cases"][case] = {
                "ratio": ratio, "alpha": alpha, "wall_s": info["wall_s"],
                "rows": [{k: r[k] for k in ("motion", "t_move_after_cmd_s", "t_move_ideal_s", "stroke_lag_at_hold_end_mm", "peak_abs_dF_kN",
                                             "p_r_cmd_end_bar_g", "p_h_cmd_end_bar_g", "p_r_max_bar_g", "v_ripple_mm_s_in_cmd")} for r in rows],
                "retract_window": {"v_mean_mm_s": float(v[win].mean() * 1e3), "v_std_mm_s": float(v[win].std() * 1e3),
                                   "v_dom_Hz": dominant_hz(t[win], v[win]),
                                   "force_ptp_kN": float(np.ptp(force[win]) / 1e3), "p_r_min": float(p_r[win].min()), "p_r_max": float(p_r[win].max()),
                                   "p_h_min": float(p_h[win].min()), "p_h_max": float(p_h[win].max()),
                                   "net_force_10Hz_std_kN": float(np.std(net) / 1e3) if len(net) > 1 else float("nan")},
            }
            rw = out["cases"][case]["retract_window"]
            print(case, "wall", info["wall_s"], "ret t_move", round(rows[0]["t_move_after_cmd_s"], 3), "lag", round(rows[0]["stroke_lag_at_hold_end_mm"], 3),
                  "dF", round(rows[0]["peak_abs_dF_kN"], 2), "| v", round(rw["v_mean_mm_s"], 2), "+-", round(rw["v_std_mm_s"], 2), "@", round(rw["v_dom_Hz"], 1), "Hz",
                  "ptpF", round(rw["force_ptp_kN"], 1), "p_r", round(rw["p_r_min"], 1), round(rw["p_r_max"], 1), "p_h", round(rw["p_h_min"], 1), round(rw["p_h_max"], 1))
    dump("poc_chatter.json", out)


if __name__ == "__main__":
    main()
