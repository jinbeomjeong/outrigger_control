"""First contact and latch per leg on both paths; stroke twist tau = n^T s at LEVEL start and lift-off.

Harness stroke = integral of delivered v over 1 ms chunks from the arm time. Chrono stroke = s_motor.
Contact: force above rest + 3 kN. Latch: first 10 Hz period from which the leg command stays 0 in TOUCH.
"""
from __future__ import annotations

import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

import numpy as np

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0x0C000000)

ROOT = Path(r"C:\workspace\outrigger_control")
S8 = ROOT / "07_results/S8"
H = Path(__file__).resolve().parent / "harness"
CASES = {"R4": "K24_top_roll5.5_Fs4", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0"}
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
K = 2.2705179e7
LEGS = ("FL", "FR", "RL", "RR")
np.set_printoptions(precision=3, suppress=True, linewidth=200)
out = {}
for cid, case in CASES.items():
    out[cid] = {}
    for tag, run, pre in (("on", f"A_{cid}_eta0.85", "coupled_eta085"), ("off", f"OFF_{cid}", "final")):
        z = np.load(H / f"{run}.npz", allow_pickle=False)
        c = {str(n): i for i, n in enumerate(z["columns"])}
        r = z["rows"]
        t = r[:, 0]
        F = r[:, [c[f"true_force_{l}"] for l in LEGS]] / 1e3
        v = r[:, [c[f"v_{l}"] for l in LEGS]]
        s = np.cumsum(v * 1e-3, axis=0)
        cr = r[:, c["crawler"]] / 1e3
        ph = z["phase"]
        pt = z["t"]
        cmd = z["command"]
        te = pt[np.flatnonzero(~np.isin(ph, ("idle", "check", "touch")))[0]]
        tl = t[(cr == 0.0) & (t > te)][0]
        first = [int(np.argmax(F[:, i] > F[0, i] + 3.0)) for i in range(4)]
        h = {"t_contact_rel_te": (t[first] - te).round(3).tolist(),
             "s_contact_mm": (s[first, range(4)] * 1e3).round(2).tolist(),
             "gap_LR_front_mm": float((s[first[0], 0] - s[first[1], 1]) * 1e3),
             "gap_LR_rear_mm": float((s[first[2], 2] - s[first[3], 3]) * 1e3)}
        ke = int(np.searchsorted(t, te))
        kl = int(np.searchsorted(t, tl))
        h["tau_mm_te"] = float(N @ s[ke] * 1e3)
        h["tau_mm_lift"] = float(N @ s[kl] * 1e3)
        h["D_te"] = float(F[ke - 200:ke].mean(axis=0) @ N)
        h["D_lift_win"] = float(F[kl: kl + 400].mean(axis=0) @ N)
        h["tau_contact_mm"] = float(N @ s[first, range(4)] * 1e3)
        h["F_RL_lift_win"] = float(F[kl: kl + 400, 2].mean())
        out[cid][tag + "_H"] = h
        d = sorted(S8.glob(f"{pre}_{case}_2*"))[-1] / case
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        p = np.load(d / "pads.npz", allow_pickle=False)
        rec = np.load(d / "record" / "record.npz", allow_pickle=False)
        s8 = np.load(d / "r8_series.npz", allow_pickle=False)
        off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
        t = p["t"] - off
        F = p["F_cyl"] / 1e3
        sm = p["s_motor"]
        crt = rec["t"] - off
        crf = np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
        pt8 = s8["t"] - off
        ph = s8["phase"]
        te = pt8[np.flatnonzero(~np.isin(ph, ("idle", "check", "touch")))[0]]
        W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(crf[(crt > te - 8) & (crt < te - 6)]))
        kernel20 = np.ones(20) / 20
        sumF = np.convolve(F.sum(axis=1), kernel20, "same")
        after = np.flatnonzero((t > te) & (W - sumF < 3.0))
        tl = t[after[0]] if after.size else np.nan
        tz10 = crt[(crf == 0.0) & (crt > te)][0]
        first = [int(np.argmax(np.convolve(F[:, i], np.ones(5) / 5, "same") > F[10, i] + 3.0)) for i in range(4)]
        ke = int(np.searchsorted(t, te))
        kl = int(np.searchsorted(t, tl))
        g = {"t_contact_rel_te": (t[first] - te).round(3).tolist(),
             "s_contact_mm": (sm[first, range(4)] * 1e3).round(2).tolist(),
             "gap_LR_front_mm": float((sm[first[0], 0] - sm[first[1], 1]) * 1e3),
             "gap_LR_rear_mm": float((sm[first[2], 2] - sm[first[3], 3]) * 1e3),
             "tau_mm_te": float(N @ sm[ke] * 1e3), "tau_mm_lift": float(N @ sm[kl] * 1e3),
             "D_te": float(F[ke - 200:ke].mean(axis=0) @ N),
             "D_lift_win": float(F[kl: kl + 400].mean(axis=0) @ N),
             "F_RL_lift_win": float(F[kl: kl + 400, 2].mean()),
             "t_lift_rel_te": float(tl - te), "t_zero10Hz_rel_te": float(tz10 - te), "W": W, "t0_s_motor_mm": (sm[0] * 1e3).round(2).tolist()}
        out[cid][tag + "_C"] = g
    print(cid)
    for k, v2 in out[cid].items():
        print(" ", k, json.dumps(v2))
(Path(__file__).resolve().parent / "gaps.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
