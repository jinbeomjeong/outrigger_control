"""Decompose the on-minus-off minimum cylinder force of the harness and of Chrono, same definitions.

Inputs: harness 1 ms records re-run by dump_harness.py (command hash equal to the stored verdict),
Chrono pads.npz, r8_series.npz, record.npz of the coupled and final runs. Read only.

Definitions (F = true cylinder force, kN; D = n^T F, n = controller twist vector, frame-free scalar):
  stored      minimum of any leg from the lift time to the end of the run
  lift time   harness: first 1 ms chunk with crawler force 0 after TOUCH. Chrono: stored = first 10 Hz
              record with crawler force 0; common = 20 ms mean of W - sum F below 3 kN (1 ms)
  win         mean over [lift, lift + 0.4 s]
Terms of d(stored) = a + b + c + d:
  a = d(stored) - d(RL raw minimum, first 8 s)     leg swap and window
  b = n_RL d(D_win)                                twist carried to the lift-off
  c = d(F_RL_win) - b                              mean load, not twist
  d = d(RL raw minimum - F_RL_win)                 ripple and dip in the window

Run: conda run -n dynamics-dev python -I decompose.py <harness folder>
"""
from __future__ import annotations

import ctypes
import csv
import json
import sys
from ctypes import wintypes
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0x0C000000)

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
S8 = ROOT / "07_results/S8"
HARNESS = Path(sys.argv[1])
CASES = {"R4": "K24_top_roll5.5_Fs4", "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0"}
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
K_NOM = 2.2705179e7
WIN = 0.4
NRL = N[2]


def mov(x, n):
    return np.convolve(x, np.ones(n) / n, "valid")


def metrics(t, F, Fmin, tl, tl_stored):
    kl = int(np.searchsorted(t, tl))
    k8 = int(np.searchsorted(t, tl + 8.0))
    ks = int(np.searchsorted(t, tl_stored))
    rl = F[kl:k8, 2]
    m = {"stored": float(Fmin[ks:].min()), "stored_leg": LEGS[int(np.unravel_index(np.argmin(Fmin[ks:]), Fmin[ks:].shape)[1])],
         "common_window_any": float(Fmin[kl:].min()), "RL_raw_8": float(Fmin[kl:k8, 2].min()),
         "RL_20ms_8": float(mov(rl, 20).min()), "RL_1s_8": float(mov(rl, 1000).min()),
         "any_1s_8": float(min(mov(F[kl:k8, i], 1000).min() for i in range(4))),
         "F_RL_win": float(F[kl:kl + int(WIN * 1000), 2].mean()),
         "D_win": float(F[kl:kl + int(WIN * 1000)].mean(axis=0) @ N),
         "after8_any": float(Fmin[k8:].min())}
    for off in (1.0, 2.0, 4.0, 6.0, 8.0):
        k = int(np.searchsorted(t, tl + off))
        m[f"D_{off:g}s"] = float(F[k - 250:k + 250].mean(axis=0) @ N)
    m["base_RL"] = m["F_RL_win"] - NRL * m["D_win"]
    return m


def harness(run):
    z = np.load(HARNESS / f"{run}.npz", allow_pickle=False)
    c = {str(n): i for i, n in enumerate(z["columns"])}
    r = z["rows"]
    t = r[:, 0]
    F = r[:, [c[f"true_force_{l}"] for l in LEGS]] / 1e3
    cr = r[:, c["crawler"]] / 1e3
    s = np.cumsum(r[:, [c[f"v_{l}"] for l in LEGS]] * 1e-3, axis=0) * 1e3
    te = z["t"][np.flatnonzero(~np.isin(z["phase"], ("idle", "check", "touch")))[0]]
    tl = t[(cr == 0.0) & (t > te)][0]
    ke = int(np.searchsorted(t, te))
    m = metrics(t, F, F, tl, tl)
    m.update(t_te=float(te), lift_after_te=float(tl - te), tau_te_mm=float(N @ s[ke]),
             D_te=float(F[ke - 200:ke].mean(axis=0) @ N), crawler_te=float(cr[ke]),
             roll_lift=float(np.degrees(r[int(np.searchsorted(t, tl)), c["roll"]])),
             pitch_lift=float(np.degrees(r[int(np.searchsorted(t, tl)), c["pitch"]])))
    k0 = int(np.argmax(cr[ke:] < 0.9 * cr[ke])) + ke
    k1 = int(np.argmax((cr[ke:] < 0.05 * cr[ke]))) + ke
    m["release_90_5_s"] = float(t[k1] - t[k0])
    return t, F, cr, tl, m


def chrono(prefix, case):
    d = sorted(S8.glob(f"{prefix}_{case}_2*"))[-1] / case
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    s8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t = p["t"] - off
    F = p["F_cyl"] / 1e3
    Fm = p["F_cyl_min_interval"] / 1e3
    crt = rec["t"] - off
    crf = np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
    pt = s8["t"] - off
    te = pt[np.flatnonzero(~np.isin(s8["phase"], ("idle", "check", "touch")))[0]]
    W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(crf[(crt > te - 8) & (crt < te - 6)]))
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    tl = t[np.flatnonzero((t > te) & (W - sm < 3.0))[0]]
    tz = crt[(crf == 0.0) & (crt > te)][0]
    m = metrics(t, F, Fm, tl, tz)
    ke = int(np.searchsorted(t, te))
    q = p["body_quat_wxyz"][int(np.searchsorted(t, tl))]
    w, x, y, z = q
    m.update(t_te=float(te), lift_after_te=float(tl - te), tau_te_mm=float(N @ p["s_motor"][ke] * 1e3),
             D_te=float(F[ke - 200:ke].mean(axis=0) @ N), crawler_te=float(W - F[ke - 20:ke].sum(axis=1).mean()),
             roll_lift=float(np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))),
             pitch_lift=float(np.degrees(np.arcsin(2 * (w * y - z * x)))))
    cr = W - sm
    ref = cr[ke]
    k0 = int(np.argmax(cr[ke:] < 0.9 * ref)) + ke
    k1 = int(np.argmax(cr[ke:] < 0.05 * ref)) + ke
    m["release_90_5_s"] = float(t[k1] - t[k0])
    return t, F, cr, tl, m


def terms(on, off):
    stored = on["stored"] - off["stored"]
    rl = on["RL_raw_8"] - off["RL_raw_8"]
    b = NRL * (on["D_win"] - off["D_win"])
    win = on["F_RL_win"] - off["F_RL_win"]
    return {"d_stored": stored, "a_leg_window": stored - rl, "b_twist": b, "c_mean_not_twist": win - b,
            "d_ripple_dip": rl - win, "d_RL_raw_8": rl, "d_RL_20ms": on["RL_20ms_8"] - off["RL_20ms_8"],
            "d_RL_1s": on["RL_1s_8"] - off["RL_1s_8"], "d_any_1s": on["any_1s_8"] - off["any_1s_8"],
            "d_common_window": on["common_window_any"] - off["common_window_any"], "d_after8": on["after8_any"] - off["after8_any"],
            "d_D_win": on["D_win"] - off["D_win"], "d_tau_te_mm": on["tau_te_mm"] - off["tau_te_mm"],
            "K_d_tau_kN": K_NOM * (on["tau_te_mm"] - off["tau_te_mm"]) * 1e-6,
            "d_D_te": on["D_te"] - off["D_te"]}


report = {}
fig, axes = plt.subplots(len(CASES), 4, figsize=(15, 11), sharex="col", constrained_layout=True)
for row, (cid, case) in enumerate(CASES.items()):
    th, Fh, crh, tlh, mh = harness(f"A_{cid}_eta0.85")
    thf, Fhf, crhf, tlhf, mhf = harness(f"OFF_{cid}")
    tc, Fc, crc, tlc, mc = chrono("coupled_eta085", case)
    tcf, Fcf, crcf, tlcf, mcf = chrono("final", case)
    # Chrono noise floor: on minus off 1 ms difference, lift-aligned, lift + 2 .. 6 s, RL
    grid = np.arange(2.0, 6.0, 0.001)
    diff = np.interp(grid, tc - tlc, Fc[:, 2]) - np.interp(grid, tcf - tlcf, Fcf[:, 2])
    hd = np.interp(grid, th - tlh, Fh[:, 2]) - np.interp(grid, thf - tlhf, Fhf[:, 2])
    dec = []
    for a, b in ((mh, mhf),):
        for off in (1.0, 2.0, 4.0, 6.0, 8.0):
            dec.append((off, a[f"D_{off:g}s"] - b[f"D_{off:g}s"]))
    arr = np.array([x for x in dec if abs(x[1]) > 0.02])
    rate = float(-np.polyfit(arr[:, 0], np.log(np.abs(arr[:, 1])), 1)[0]) if len(arr) >= 2 else None
    report[cid] = {"harness": {"on": mh, "off": mhf, "terms": terms(mh, mhf), "dD_decay": dec, "dD_rate_1_s": rate},
                   "chrono": {"on": mc, "off": mcf, "terms": terms(mc, mcf),
                              "RL_on_minus_off_rms_2_6s": float(np.sqrt(np.mean((diff - diff.mean()) ** 2))),
                              "RL_on_minus_off_mean_2_6s": float(diff.mean())},
                   "harness_RL_on_minus_off_rms_2_6s": float(np.sqrt(np.mean((hd - hd.mean()) ** 2))),
                   "harness_RL_on_minus_off_mean_2_6s": float(hd.mean())}
    for col, (tt, F, tl, tof, Fof, tlof, name) in enumerate(((th, Fh, tlh, thf, Fhf, tlhf, "reduced"), (tc, Fc, tlc, tcf, Fcf, tlcf, "Chrono"))):
        ax = axes[row, 2 * col]
        for tv, Fv, tv0, color, lab in ((tt, F, tl, "C3", "on"), (tof, Fof, tlof, "C0", "off")):
            sel = (tv - tv0 > -2.0) & (tv - tv0 < 8.0)
            ax.plot(tv[sel] - tv0, Fv[sel, 2], color=color, lw=0.6, label=lab)
        ax.set_ylabel(f"{cid} {name}\nF_RL [kN]")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right", fontsize=7)
        ax2 = axes[row, 2 * col + 1]
        for tv, Fv, tv0, color, lab in ((tt, F, tl, "C3", "on"), (tof, Fof, tlof, "C0", "off")):
            sel = (tv - tv0 > -2.0) & (tv - tv0 < 8.0)
            ax2.plot(tv[sel] - tv0, Fv[sel] @ N, color=color, lw=0.6, label=lab)
        ax2.set_ylabel("D = n'F [kN]")
        ax2.grid(alpha=0.3)
for ax in axes[-1]:
    ax.set_xlabel("time from lift-off [s]")
fig.suptitle("Left leg force and twist around lift-off. eta_v 0.85 (on) vs flow limit off, rigid floor")
fig.savefig(HERE / "lift_traces.png", dpi=130)
(HERE / "decomposition.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
with (HERE / "decomposition.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    keys = list(report["R4"]["harness"]["terms"])
    w.writerow(["row", "path", *keys])
    for cid, r in report.items():
        for path in ("harness", "chrono"):
            w.writerow([cid, path, *[round(r[path]["terms"][k], 3) for k in keys]])
np.set_printoptions(precision=3, suppress=True)
for cid, r in report.items():
    print(cid)
    for path in ("harness", "chrono"):
        print(" ", path, {k: round(v, 2) for k, v in r[path]["terms"].items()})
        print("    on ", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r[path]["on"].items()})
        print("    off", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r[path]["off"].items()})
    print("  decay", r["harness"]["dD_decay"], r["harness"]["dD_rate_1_s"])
    print("  noise chrono rms", round(r["chrono"]["RL_on_minus_off_rms_2_6s"], 3), "mean", round(r["chrono"]["RL_on_minus_off_mean_2_6s"], 3),
          "harness rms", round(r["harness_RL_on_minus_off_rms_2_6s"], 3), "mean", round(r["harness_RL_on_minus_off_mean_2_6s"], 3))
