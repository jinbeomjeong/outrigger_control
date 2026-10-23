"""S6 stage-2 Chrono closed loop: rocking left by the probe (item 5b) and phase timing (items 1a, 3, T).

Reads 07_results/S6/stage2_20261021_213235/<case>/{result.json, record/record.npz, pads.npz} (roll 5.5 from the
override batch 214443). Per case: phase times; true cylinder-force AC part (minus 1 s moving mean) peak-to-peak and
body pitch/roll-rate AC amplitude in windows (before probe, probe, READY+0..5 s, READY+5..10 s); dominant frequency
and log-decrement damping after READY; pad sliding steps during the probe; probe leg command profile.
Run: conda run -n dynamics-dev python -I s6s2_rocking.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
B1 = ROOT / "07_results" / "S6" / "stage2_20261021_213235"
B2 = ROOT / "07_results" / "S6" / "stage2_20261021_214443"


def movavg(x, n):
    k = np.ones(n) / n
    pad = np.pad(x, ((n // 2, n - 1 - n // 2),) + ((0, 0),) * (x.ndim - 1), mode="edge")
    if x.ndim == 1:
        return np.convolve(pad, k, mode="valid")
    return np.column_stack([np.convolve(pad[:, j], k, mode="valid") for j in range(x.shape[1])])


def quat_rp(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def analyse(cdir):
    r = json.loads((cdir / "result.json").read_text())
    ph = {name: t for t, name in r["phases"]}
    seq = r["phases"]
    z = np.load(cdir / "record" / "record.npz")
    t0 = float(r["settings"].get("start_t_s", 0.0)); t = z["t"] - t0
    dt = float(np.median(np.diff(t)))
    F = z["F_cyl"] / 1e3
    Fac = F - movavg(F, int(round(1.0 / dt)))
    roll, pitch = quat_rp(z["body_quat_wxyz"])
    att = np.column_stack([roll, pitch])
    att_ac = att - movavg(att, int(round(1.0 / dt)))
    om = np.degrees(z["body_omega"])
    out = {"phases": seq, "ready_t_s": r.get("ready_t_s"), "crawler_off_t_s": r.get("crawler_off_t_s")}
    t_touch = next((tt for tt, n in seq if n == "touch"), None)
    t_level = next((tt for tt, n in seq if n == "level"), None)
    out["touch_to_ready_s"] = None if r.get("ready_t_s") is None else round(r["ready_t_s"] - t_level, 2)
    probes = [(tt, seq[i + 1][0]) for i, (tt, n) in enumerate(seq[:-1]) if n == "probe"]
    tr = r.get("ready_t_s")
    wins = {}
    if probes:
        p0, p1 = probes[-1]
        last_done = max(tt for tt, n in seq if n == "done" and tt <= p0)
        wins["before_probe"] = (max(last_done - 3.0, t[0]), p0)
        wins["probe"] = (p0, p1)
    if tr is not None:
        wins["ready_0_5"] = (tr, tr + 5)
        wins["ready_5_10"] = (tr + 5, tr + 10)
        wins["last5"] = (t[-1] - 5, t[-1])
    W = {}
    for k, (a, b) in wins.items():
        m = (t >= a) & (t < b)
        if m.sum() < 5:
            continue
        W[k] = {"F_pp_kN": np.ptp(Fac[m], axis=0).round(2).tolist(),
                "att_ac_pp_deg": np.ptp(att_ac[m], axis=0).round(5).tolist(),
                "omega_y_amp_deg_s": round(float(np.max(np.abs(om[m, 1]))), 4),
                "omega_x_amp_deg_s": round(float(np.max(np.abs(om[m, 0]))), 4)}
    out["windows"] = W
    if tr is not None:
        m = t >= tr
        sig = Fac[m][:, int(np.argmax(np.ptp(Fac[m], axis=0)))]
        n = len(sig)
        f = np.fft.rfftfreq(n, dt)
        S = np.abs(np.fft.rfft(sig * np.hanning(n)))
        sel = f > 0.3
        out["f_dom_Hz"] = round(float(f[sel][np.argmax(S[sel])]), 3)
        # decay: envelope peaks of |sig|, fit log
        tt = t[m] - tr
        pk = [i for i in range(1, n - 1) if sig[i] > sig[i - 1] and sig[i] >= sig[i + 1] and sig[i] > 0]
        if len(pk) > 6:
            a = np.log(sig[pk]); b = tt[pk]
            slope = np.polyfit(b, a, 1)[0]
            fd = out["f_dom_Hz"]
            out["zeta_est"] = round(float(-slope / (2 * math.pi * fd)), 4) if fd > 0 else None
    if probes and (cdir / "pads.npz").exists():
        pz = np.load(cdir / "pads.npz")
        tp = pz["t"] - t0
        p0, p1 = probes[-1]
        mp = (tp >= p0) & (tp < p1)
        out["probe_sliding_samples"] = pz["sliding"][mp].sum(axis=0).astype(int).tolist()
        mr = (tp >= p1) & (tp < p1 + 10)
        out["post_ready_sliding_samples"] = pz["sliding"][mr].sum(axis=0).astype(int).tolist()
        sl = pz["slip_total"]
        def slipnorm(i):
            return np.linalg.norm(sl[i], axis=1)
        i0 = int(np.searchsorted(tp, p0)); i1 = min(int(np.searchsorted(tp, p1)), len(tp) - 1)
        out["probe_slip_mm"] = ((slipnorm(i1) - slipnorm(i0)) * 1e3).round(3).tolist()
        out["probe_util_max"] = pz["utilisation"][mp].max(axis=0).round(3).tolist()
        # probe command profile
        m = (t >= p0) & (t < p1)
        u = z["u_cmd"][m] * 1e3
        out["probe_u_max_mm_s"] = np.abs(u).max(axis=0).round(3).tolist()
        moving = np.abs(u).max(axis=1) > 1e-3
        out["probe_moving_s"] = round(float(moving.sum() * dt), 2)
        # segments of motion
        segs = []
        cur = None
        for i, mv in enumerate(moving):
            if mv and cur is None:
                cur = i
            if not mv and cur is not None:
                segs.append((round(float(t[m][cur] - p0), 2), round(float((i - cur) * dt), 2),
                             int(np.argmax(np.abs(u[cur:i]).max(axis=0)))))
                cur = None
        out["probe_segments_(start,dur,leg)"] = segs
    return out


def main():
    res = {}
    for d in sorted(B1.iterdir()):
        if not d.is_dir():
            continue
        cdir = d
        if (B2 / d.name).is_dir():
            cdir = B2 / d.name
        try:
            res[d.name] = analyse(cdir)
        except Exception as e:  # noqa: BLE001
            res[d.name] = {"error": repr(e)}
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, default=float))
    for k, v in res.items():
        if "error" in v:
            print(k, v["error"]); continue
        w = v["windows"]
        def g(n, key):
            return w.get(n, {}).get(key)
        print(f"{k:44s} L->R {v['touch_to_ready_s']}  f={v.get('f_dom_Hz')} z={v.get('zeta_est')} "
              f"Fpp pre={g('before_probe','F_pp_kN')} probe={g('probe','F_pp_kN')} r0={g('ready_0_5','F_pp_kN')} "
              f"r5={g('ready_5_10','F_pp_kN')} | wy r0={g('ready_0_5','omega_y_amp_deg_s')} "
              f"slide={v.get('probe_sliding_samples')} slip={v.get('probe_slip_mm')} seg={v.get('probe_segments_(start,dur,leg)')}")


if __name__ == "__main__":
    main()
