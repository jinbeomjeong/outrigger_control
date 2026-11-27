"""G' window shift, part 2: 1 ms traces of the stored instrumented reruns (seen keys only, RE1bF
30 mm / 0.05 s, bottom front, ready; dynamics_u832_o00/rerun_raw) -> event-leg airborne
trajectory, re-contact, contact pulse and its end.

rows columns (r51_reapp_closed_loop.control_period): t, contact(4), F = contact - W_rod (4),
valve(4), pad gap(4) (= floor-plane distance gax - x, > 0 airborne), attitude roll/pitch (deg).
Times are relative to the event start t_ev. F_exit = F_min + 5 kN = 14.4146 kN (true F column).
Output: g02_traces.csv (one row per run), g02_traces.npz (event-leg t, F, gap, valve 0..0.8 s per run),
g02_traces.png.
Usage: python -I -B g02_traces.py <rerun_dir> <out_folder>
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
F_EXIT = 9414.6 + 5000.0
rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
logs = rerun / "logs"
res, store = [], {}
fig, ax = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
for p in sorted(logs.glob("R12_bottom-F*-RE1bF-ready_*_rows.npz")):
    stem = p.name[:-len("_rows.npz")]
    parts = stem.split("_")[1].split("-")
    setting = stem.split("_")[-1]
    leg_name, fs, off = parts[1], float(parts[2][2:]), float(parts[3][1:])
    leg = LEGS.index(leg_name)
    dg = DIAG[leg]
    z = np.load(p)
    rows, t_ev = z["rows"], float(z["t_ev"])
    t = rows[:, 0] - t_ev
    c, F, valve, gap = rows[:, 1:5], rows[:, 5:9], rows[:, 9:13], rows[:, 13:17]
    w = (t > -0.05) & (t < 0.8)
    tt, Fe, ge, ve, ce = t[w], F[w, leg], gap[w, leg], valve[w, leg], c[w, leg]
    Fd, gd = F[w, dg], gap[w, dg]
    air = ce <= 0.0
    i_lift = int(np.flatnonzero((tt >= 0) & air)[0])
    i_back = int(np.flatnonzero((tt > tt[i_lift]) & ~air)[0])          # first re-contact (contact > 0)
    i_rel = int(np.flatnonzero((tt > tt[i_back]) & (Fe >= F_EXIT))[0])  # reload to exit level
    i_relift = int(np.flatnonzero((tt > tt[i_rel]) & air)[0])
    m = (tt > tt[i_rel]) & (tt < tt[i_relift]) & (Fe >= F_EXIT)
    i_hold = int(np.flatnonzero(m)[-1])
    i_pk = i_back + int(np.argmax(Fe[i_back:i_relift]))
    # impact velocity: gap slope over the last 5 ms before contact (gap closing, m/s)
    k0 = max(i_back - 6, 0)
    v_imp = float((ge[k0] - ge[i_back - 1]) / (tt[i_back - 1] - tt[k0]))
    # valve (event leg extension command) at re-contact
    d_air = np.flatnonzero((tt > 0) & (gd > 0))
    first_d = (float(tt[d_air[0]]), None)
    dl = np.flatnonzero((tt > first_d[0]) & (gd <= 0))
    first_d = (first_d[0], float(tt[dl[0]]) if dl.size else None)
    F0 = float(np.mean(Fe[(tt < 0) & (tt > -0.02)]))
    rec = {"run": stem, "setting": setting, "leg": leg_name, "fs_kN": fs, "offset_s": off,
           "F0_kN": round(F0 / 1e3, 2),
           "t_lift_s": round(float(tt[i_lift]), 4), "t_contact_s": round(float(tt[i_back]), 4),
           "t_reload_exit_s": round(float(tt[i_rel]), 4), "t_hold_end_s": round(float(tt[i_hold]), 4),
           "t_relift_s": round(float(tt[i_relift]), 4), "t_peak_s": round(float(tt[i_pk]), 4),
           "F_peak_kN": round(float(Fe[i_pk]) / 1e3, 2), "v_impact_m_s": round(v_imp, 4),
           "gap_max_mm": round(float(ge[i_lift:i_back].max()) * 1e3, 2),
           "t_gap_max_s": round(float(tt[i_lift + int(np.argmax(ge[i_lift:i_back]))]), 4),
           "valve_at_contact_mm_s": round(float(ve[i_back]) * 1e3, 3),
           "contact_s": round(float(tt[i_relift] - tt[i_back]), 4),
           "diag_first_lift": first_d}
    res.append(rec)
    store[stem] = np.vstack([tt, Fe, ge, ve, Fd, gd])
    if setting == "V0":
        ax[0].plot(tt, Fe / 1e3, lw=0.8, label=f"{leg_name} Fs{fs:g} o{off}")
        ax[1].plot(tt, ge * 1e3, lw=0.8)
        ax[2].plot(tt, ve * 1e3, lw=0.8)
ax[0].axhline(F_EXIT / 1e3, color="k", ls=":", lw=0.8)
ax[0].set_ylabel("event leg F = contact - W_rod [kN]")
ax[1].set_ylabel("event pad gap [mm] (>0 airborne)")
ax[2].set_ylabel("event leg valve [mm/s]")
ax[2].set_xlabel("t - t_ev [s]")
ax[0].legend(fontsize=7, ncol=2)
for a in ax:
    a.grid(alpha=0.3)
fig.suptitle("V0 reruns, bottom front RE1bF 30 mm / 0.05 s (seen keys)")
fig.tight_layout()
fig.savefig(out / "g02_traces.png", dpi=120)
with (out / "g02_traces.csv").open("w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(res[0]))
    wr.writeheader()
    for r in res:
        r = dict(r)
        r["diag_first_lift"] = json.dumps(r["diag_first_lift"])
        wr.writerow(r)
np.savez_compressed(out / "g02_traces.npz", **store)
for r in res:
    print(json.dumps(r))
print(json.dumps({"status": "ok", "runs": len(res)}))
