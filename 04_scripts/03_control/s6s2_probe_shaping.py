"""S6 spec revision 3: probe motion profile vs residual rocking (item 5b).

Part 1 (analytic): residual-vibration ratio of one probe move for an undamped mode at f (1.5-3.2 Hz),
  R(f) = |V(w)| / d, V = Fourier transform of the leg velocity profile (ZOH 20 ms, actuator slew 0.1 s per v_max),
  R = 1 for a step of the same depth. Profiles: current (0.25 v_max rectangle, 2 mm), slower rectangles,
  shaped trapezoid (duration D between ramp mid-points, ramp tau).
Part 2 (reduced 6-DoF closed loop, s6_target_sim.run_tgt by import, combined verdict = probe on):
  top/middle/bottom x fdown 3.5 / flat, probe_speed_frac 0.25 (current) / 0.157 (D = 0.56 s) / 0.10;
  post-READY true cylinder-force AC peak-to-peak (minus 1 s mean) and the 5b-type residual of the 2nd-order
  filtered attitude over the last 5 s (minus 1 s moving mean).
Run: conda run -n dynamics-dev python -I s6s2_probe_shaping.py <project_root> <out_json> [workers]
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control"))
import s6_target_sim as sts  # noqa: E402

T = 0.02
VMAX = 0.68 / 30.0
SLEW = VMAX / 0.1          # actuator command ramp 0.1 s per v_max
DEPTH = 2e-3


def profile_rect(vfrac):
    v = vfrac * VMAX
    n = int(math.ceil(DEPTH / v / T))
    cmd = np.full(n, v)
    cmd[-1] = DEPTH / T - v * (n - 1)          # last period trims to the exact depth
    return cmd


def profile_trap(D, tau):
    """Trapezoid: plateau speed d / D, linear ramps of tau (ramp mid-points D apart), sampled at T (ZOH)."""
    v = DEPTH / D
    tt = (np.arange(int(round((D + tau) / T))) + 0.5) * T
    up = np.clip(tt / tau, 0, 1); dn = np.clip((D + tau - tt) / tau, 0, 1)
    cmd = v * np.minimum(up, dn)
    return cmd * DEPTH / (cmd.sum() * T)


def applied(cmd, dt=1e-3):
    """ZOH at T then slew-rate limit (actuator ramp) on a fine grid."""
    fine = np.repeat(cmd, int(round(T / dt)))
    fine = np.concatenate([fine, np.zeros(int(1.0 / dt))])
    out = np.zeros_like(fine); u = 0.0
    for i, c in enumerate(fine):
        u += np.clip(c - u, -SLEW * dt, SLEW * dt); out[i] = u
    return out, dt


def ratio(cmd, f):
    v, dt = applied(cmd)
    t = np.arange(len(v)) * dt
    w = 2 * math.pi * f
    return float(abs(np.sum(v * np.exp(-1j * w * t)) * dt) / DEPTH)


def part1():
    prof = {"rect 0.25 (current)": profile_rect(0.25), "rect 0.157 (D 0.56 s)": profile_rect(0.157),
            "rect 0.10": profile_rect(0.10), "trap D 0.56 tau 0.36": profile_trap(0.56, 0.36),
            "trap D 0.56 tau 0.44": profile_trap(0.56, 0.44), "trap D 0.80 tau 0.40": profile_trap(0.80, 0.40)}
    fs = np.round(np.arange(1.5, 3.21, 0.05), 3)
    res = {}
    for k, c in prof.items():
        r = [ratio(c, f) for f in fs]
        band = [x for f, x in zip(fs, r) if 1.70 <= f <= 2.95]
        res[k] = {"move_s": round(len(c) * T, 2), "R": dict(zip(map(float, fs), np.round(r, 4).tolist())),
                  "R_at": {f: round(ratio(c, f), 4) for f in (1.78, 2.30, 2.84)},
                  "R_max_1.70_2.95": round(max(band), 4)}
        print(f"{k:24s} move {len(c) * T:.2f} s  R(1.78/2.30/2.84 Hz) = {res[k]['R_at']}  max band {max(band):.4f}")
    return res


_LAST = {}


def run(case):
    import run_c2_timedomain as c2t
    orig = c2t.run_case

    def wrapped(*a, **k):
        r = orig(*a, **k)
        _LAST["S"] = r.get("_series")
        return r
    c2t.run_case = wrapped
    sts.rcc.CA["probe_speed_frac"] = case["probe_speed_frac"]
    try:
        out = sts.run_tgt(case)
    finally:
        c2t.run_case = orig
    S = _LAST.get("S")
    if S is None or "error" in out:
        return out
    t = np.asarray(S["t"]); F = np.asarray(S["Ftrue"]) / 1e3
    tr = out.get("t_ready_s")
    n = int(round(1.0 / sts.rcc.T_CTRL))
    k = np.ones(n) / n

    def ac(x):
        return x - np.convolve(np.pad(x, (n // 2, n - 1 - n // 2), mode="edge"), k, mode="valid")
    if tr is not None:
        m0 = (t >= tr) & (t < tr + 5); m1 = (t >= tr + 5) & (t < tr + 10)
        out["F_pp_ready0_5_kN"] = round(float(max(np.ptp(ac(F[:, j])[m0]) for j in range(4))), 2)
        out["F_pp_ready5_10_kN"] = round(float(max(np.ptp(ac(F[:, j])[m1]) for j in range(4))), 2)
    # 5b-type residual: 2nd-order filtered measured attitude, last 5 s, minus 1 s moving mean
    a = sts.rcc.T_CTRL / 0.5
    last = t >= t[-1] - 5.0
    worst = 0.0
    for key in ("phi_m", "theta_m"):
        x = np.degrees(np.asarray(S[key]))
        y1 = np.empty_like(x); y2 = np.empty_like(x); y1[0] = y2[0] = x[0]
        for i in range(1, len(x)):
            y1[i] = y1[i - 1] + a * (x[i] - y1[i - 1]); y2[i] = y2[i - 1] + a * (y1[i] - y2[i - 1])
        worst = max(worst, float(np.max(np.abs(ac(y2)[last]))))
    out["res5b_deg"] = round(worst, 5)
    out["probe_speed_frac"] = case["probe_speed_frac"]
    return out


def cases():
    C = []
    for lvl in ("top", "middle", "bottom"):
        for nm, fl in (("fdown3.5", (0.0, 3.5)), ("flat", (0.0, 0.0))):
            for vf in (0.25, 0.157, 0.10):
                C.append(dict(id=f"{lvl}|{nm}|v{vf}", group="probe", floor_deg=fl, level=lvl, contact="combined",
                              probe_speed_frac=vf, tgt={"target_deg": (0.0, 0.0), "ra_mode": "rel"}, t_hold=10.0))
    return C


def main():
    out_json = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    t0 = time.time()
    P1 = part1()
    import run_c2_timedomain as c2t
    c2t.set_affinity()
    import multiprocessing as mp
    C = cases()
    res = []
    with mp.get_context("spawn").Pool(min(workers, len(C))) as pool:
        for r in pool.imap_unordered(run, C):
            res.append(r)
            print(f"{time.time() - t0:6.1f} s {r['id']:24s} ready={r.get('t_ready_s')} probe_t={r.get('probe_time_s')} "
                  f"Fpp0-5={r.get('F_pp_ready0_5_kN')} Fpp5-10={r.get('F_pp_ready5_10_kN')} res5b={r.get('res5b_deg')} "
                  f"Fmin={r.get('min_true_cyl_force_kN')} {r.get('error', '')}", flush=True)
    order = {c["id"]: i for i, c in enumerate(C)}
    res.sort(key=lambda r: order[r["id"]])
    keep = ("id", "probe_speed_frac", "t_touch_s", "t_ready_s", "min_true_cyl_force_kN", "F_pp_ready0_5_kN",
            "F_pp_ready5_10_kN", "res5b_deg", "fails", "error")
    out_json.write_text(json.dumps({"part1": P1, "part2": [{k: r.get(k) for k in keep} for r in res],
                                    "runtime_s": time.time() - t0}, indent=1, default=float))
    print("written", out_json)


if __name__ == "__main__":
    main()
