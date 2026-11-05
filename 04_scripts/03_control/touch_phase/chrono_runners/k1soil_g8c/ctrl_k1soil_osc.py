"""READY tail oscillation of the K1 soil rows: block amplitude of roll and F_cyl, dominant frequency, decay per block, actuator motion, cross terms.
All from step_series after the last nonzero command. Compares the Fs8 on row with its off row and the Fs0 rows. Writes osc.json."""
import json
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
HERE = Path(__file__).resolve().parent
out = {}
for tag in ("FLFs8", "FLFs0", "RRFs0"):
    for s in ("RE1bF_off", "RE1bF_on"):
        d = BATCH / f"S9EV_G1_{tag}_{s}"
        z = np.load(d / "step_series.npz")
        t = np.asarray(z["t_s"], float)
        rp = np.asarray(z["roll_pitch_deg"], float)
        F = np.asarray(z["F_cyl_N"], float)
        sm = np.asarray(z["s_motor_m"], float)
        sink = np.asarray(z["pad_sinkage_geometric_m"], float)
        cc = np.load(d / "controller_commands.npz")
        nz = np.flatnonzero(np.any(np.abs(cc["issued_u_m_s"]) > 1e-12, axis=1))
        t_last = float(cc["t_s"][nz[-1]])
        blocks = []
        for lo in np.arange(np.ceil(t_last), t[-1] - 4.99, 5.0):
            m = (t >= lo) & (t < lo + 5)
            tt = t[m] - t[m].mean()
            roll = rp[m, 0] - np.polyval(np.polyfit(tt, rp[m, 0], 1), tt)
            pitch = rp[m, 1] - np.polyval(np.polyfit(tt, rp[m, 1], 1), tt)
            D = (F[m, 0] + F[m, 3]) - (F[m, 1] + F[m, 2])
            f = np.fft.rfftfreq(m.sum(), 1e-3)
            sp = np.abs(np.fft.rfft(roll * np.hanning(m.sum())))
            k = int(np.argmax(sp[1:])) + 1
            sn = sink[m] - sink[m].mean(axis=0)
            blocks.append({"t_s": float(lo), "roll_pp_mdeg": round(float(np.ptp(roll)) * 1e3, 3), "pitch_pp_mdeg": round(float(np.ptp(pitch)) * 1e3, 3), "f_Hz": round(float(f[k]), 2), "D_mean_kN": round(float(D.mean()) / 1e3, 3), "D_pp_kN": round(float(np.ptp(D)) / 1e3, 3),
                           "F_pp_kN": [round(float(x) / 1e3, 3) for x in np.ptp(F[m], axis=0)], "sink_pp_um": [round(float(x) * 1e6, 2) for x in np.ptp(sn, axis=0)], "s_motor_change_um": [round(float(x) * 1e6, 4) for x in sm[m][-1] - sm[m][0]]})
        ratio = None
        if len(blocks) >= 3 and blocks[0]["roll_pp_mdeg"] > 0:
            ratio = round(blocks[-1]["roll_pp_mdeg"] / blocks[0]["roll_pp_mdeg"], 3)
        out[f"{tag}_{s}"] = {"t_last_command_s": t_last, "blocks": blocks, "roll_pp_last_over_first": ratio}
        print(tag, s, "t_last", round(t_last, 1), "ratio", ratio)
        for b in blocks[:: max(1, len(blocks) // 6)]:
            print("   ", json.dumps(b))
        print("    last", json.dumps(blocks[-1]))
(HERE / "osc.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
