"""Analyse the RR plant trace: rod pressure truth, reading, head pressure, jumps at lock events.

Usage: python -I -B b02_analyze.py <trace_dir> [settings]
"""
import json
import sys
from pathlib import Path

import numpy as np

A_ANN = np.pi / 4 * (0.110 ** 2 - 0.090 ** 2)
A_H = np.pi / 4 * 0.110 ** 2
BAR = 1e5


def load(path):
    z = np.load(path)
    cols = [str(c) for c in z["cols"]]
    d = {c: z["data"][:, k] for k, c in enumerate(cols)}
    return d


def main():
    tdir = Path(sys.argv[1])
    settings = sys.argv[2].split(",") if len(sys.argv) > 2 else ["VB", "LS2", "LS3"]
    summary = {}
    for s in settings:
        d = load(tdir / f"trace_{s}.npz")
        t = d["t"]
        lk = d["locked"] > 0.5
        p_tr = np.where(lk, d["p_r0"] - d["Gr"] / A_ANN, d["p_lag"])
        read_lock = d["p_r0"] - (d["Gr"] - d["Gr_lock"]) / A_ANN
        head = (d["net_N"] + p_tr * A_ANN) / A_H
        # stiffness ratio from the long lock (48.30..48.60): dGr / dnet
        m = (t >= 48.30) & (t <= 48.60) & lk
        ratio = np.polyfit(d["net_N"][m], d["Gr"][m], 1)[0]
        dc = np.polyfit(d["net_N"][m], d["c"][m], 1)[0]  # = 1/(kh+kr)
        kh_plus_kr = 1.0 / dc
        kr = ratio * kh_plus_kr
        kh = kh_plus_kr - kr
        print("=" * 110)
        print(f"{s}: long-lock fit dGr/dF = {ratio:.4f}, k_h = {kh:.4e}, k_r = {kr:.4e} N/m, "
              f"head/rod pressure ratio dp_r/dp_h = {-(kr / A_ANN) / (kh / A_H):.4f}")
        ch = np.flatnonzero(np.diff(lk.astype(int)) != 0) + 1
        events = []
        for k in ch:
            ev = {"t": round(float(t[k]), 4), "locked_after": bool(lk[k]),
                  "p_tr_before_bar": float(p_tr[k - 1] / BAR), "p_tr_after_bar": float(p_tr[k] / BAR),
                  "p_r0_before_bar": float(d["p_r0"][k - 1] / BAR),
                  "p_r0_after_bar": float(d["p_r0"][k] / BAR),
                  "Gr_kN": float(d["Gr"][k] / 1e3), "Gr_lock_kN": float(d["Gr_lock"][k] / 1e3),
                  "r0_kN": float(d["r0"][k] / 1e3), "t_rel": float(d["t_rel"][k]),
                  "head_before_bar": float(head[k - 1] / BAR), "head_after_bar": float(head[k] / BAR),
                  "net_kN": float(d["net_N"][k] / 1e3), "last_dir": float(d["last_dir"][k]),
                  "p_target_bar": float(d["p_target"][k] / BAR)}
            events.append(ev)
            print("  event", json.dumps(ev))
        print("   t[s]   lk dir  u[um/s]   p_r0   Gr[kN] Grlk[kN]  p_lag  p_tgt  p_tr  read_lk  head  F[kN]  c[mm]")
        for k in range(0, len(t)):
            tk = t[k]
            near = any(abs(tk - e["t"]) < 0.0026 for e in events)
            if near or abs((tk * 1000) % 10) < 0.25 or abs((tk * 1000) % 10 - 10) < 0.25:
                if 48.55 <= tk <= 49.15:
                    print(f"  {tk:7.4f} {int(lk[k])} {d['last_dir'][k]:+.0f} {d['u_kernel'][k]*1e6:+8.3f}"
                          f" {d['p_r0'][k]/BAR:6.2f} {d['Gr'][k]/1e3:7.3f} {d['Gr_lock'][k]/1e3:7.3f}"
                          f" {d['p_lag'][k]/BAR:6.2f} {d['p_target'][k]/BAR:6.2f} {p_tr[k]/BAR:6.2f}"
                          f" {read_lock[k]/BAR:6.2f} {head[k]/BAR:6.2f} {d['net_N'][k]/1e3:6.2f}"
                          f" {d['c'][k]*1e3:7.4f}")
        summary[s] = {"kh": kh, "kr": kr, "ratio": ratio, "events": events}
    (tdir / "analysis_events.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
