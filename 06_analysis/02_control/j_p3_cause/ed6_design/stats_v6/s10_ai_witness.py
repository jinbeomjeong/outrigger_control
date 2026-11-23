"""Ed. 6 A(i) adaptive LEVEL deadband compensation: noise false-trigger, stall detection delay,
ramp/pulse and false end (stats-design-expert, 2026-11-23, design only).

Model (spec jp3_remedy_spec_v6.md 3.1, harness sensor model):
  - Stroke read every cycle T_s = 0.1 s: s_read = s_true + e, e ~ N(0, 0.1 mm) i.i.d. per read and
    leg (03_src/outrigger_sim/sensors/hydraulic.py:55 REDUCED_MODEL_STROKE_NOISE_M = 1e-4, :402).
    stroke_m (oil coordinate) is not quantized (:407).
  - Constant command |u| over a same-sign streak; D_cmd = k |u| T_s after k cycles.
  - Moving leg: s_true advances f |u| T_s per cycle (f flow factor 1.0 / 0.85 / 0.7).
    Stalled leg (deadband lock): s_true constant.
  - Trigger at cycle k: k >= N_trig, D_cmd >= D_trig, ds_obs < eta * D_cmd.
    Estimators: E1 = read_k - read_0 (spec wording), E3 = mean(read_{k-2..k}) - mean(read_{0..2}).
  - Ramp episode (after trigger): u_k = min(u_{k-1} + du_step, u_cap) from u_hold, applied
    |u| = max(u_ctrl, u_k). Plant opens when |u| > r_th (r_th ~ c_v v_max, hydraulics h1 table:
    c_v 0.005 / 0.01 / 0.02 / 0.04 -> 0.10 / 0.20 / 0.39 / 0.75 mm/s upper values). Open speed:
    "sub" = |u| - r_th (neutral leak keeps r_th, ASSUMPTION) or "full" = |u| (ASSUMPTION).
    End: witness (s_read - ref >= s_w) or N_cap cycles at u_cap.
Writes s10_ai_witness.json next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
SEED = 20261114
TS = 0.1
SIG = 0.1          # mm
U_HOLD = 0.209243  # mm/s
L_STREAK = 100     # cycles checked per streak (10 s)


def reads(rng, s_true: np.ndarray, reps: int) -> np.ndarray:
    return s_true[None, :] + rng.normal(0.0, SIG, (reps, s_true.size))


def ds_est(r: np.ndarray, est: str) -> np.ndarray:
    """Observed displacement since streak start for k = 0..L (NaN where undefined)."""
    if est == "E1":
        return r - r[:, :1]
    c = np.full_like(r, np.nan)
    m = (r[:, :-2] + r[:, 1:-1] + r[:, 2:]) / 3.0     # mean of k-2..k at index k
    c[:, 2:] = m
    return c - c[:, 2:3]


def trigger_first(r, u, n_trig, d_trig, eta, est) -> np.ndarray:
    k = np.arange(r.shape[1])
    d = k * u * TS
    ds = ds_est(r, est)
    elig = (k >= n_trig) & (d >= d_trig - 1e-12)
    trig = elig[None, :] & (ds < eta * d[None, :])
    first = np.where(trig.any(1), trig.argmax(1), -1)
    return first


def sim_trigger(rng, reps=5000) -> dict:
    out = {"false_trigger_moving": [], "stall_delay": []}
    grid = [(n, d, e) for n in (5, 10, 15, 20) for d in (0.3, 0.5, 0.8) for e in (0.25, 0.5)]
    for est in ("E1", "E3"):
        for (n, d, e) in grid:
            row = {"est": est, "N_trig": n, "D_trig": d, "eta": e, "p": {}}
            for u in (0.25, 0.3, 0.4, 0.6):
                for f in (1.0, 0.85, 0.7):
                    s = f * u * TS * np.arange(L_STREAK + 1)
                    first = trigger_first(reads(rng, s, reps), u, n, d, e, est)
                    row["p"][f"u{u}_f{f}"] = float((first >= 0).mean())
            row["max_p"] = max(row["p"].values())
            out["false_trigger_moving"].append(row)
            srow = {"est": est, "N_trig": n, "D_trig": d, "eta": e, "delay": {}}
            for u in (0.22, 0.3, 0.4, 0.6, 0.75):
                first = trigger_first(reads(rng, np.zeros(L_STREAK + 1), reps), u, n, d, e, est)
                ok = first >= 0
                fk = first[ok]
                srow["delay"][f"u{u}"] = {
                    "p_detect_10s": float(ok.mean()),
                    "median_s": float(np.median(fk) * TS) if fk.size else None,
                    "p95_s": float(np.percentile(fk, 95) * TS) if fk.size else None,
                    "floor_s": float(max(n, np.ceil(d / (u * TS) - 1e-9)) * TS)}
            out["stall_delay"].append(srow)
    return out


def episode(rng, reps, u_ctrl, r_th, du, u_cap, s_w, n_cap, speed, est, k_max=120):
    """One A(i) episode from trigger; returns end cycle, witness flag, true pulse at end."""
    k = np.arange(k_max + 1)
    uk = np.minimum(U_HOLD + du * k, u_cap)
    ueff = np.maximum(u_ctrl, uk)
    if speed == "sub":
        v = np.clip(ueff - r_th, 0.0, None)
    else:
        v = np.where(ueff > r_th, ueff, 0.0)
    # displacement realised during cycle k is seen at read k+1
    s_true = np.concatenate([[0.0], np.cumsum(v * TS)])[: k_max + 1]
    r = reads(rng, s_true, reps)
    if est == "E1":
        ds = r - r[:, :1]
    else:
        ds = np.full_like(r, np.nan)
        ds[:, 2:] = (r[:, :-2] + r[:, 1:-1] + r[:, 2:]) / 3.0
        ds = ds - np.nanmean(r[:, :3], axis=1, keepdims=True)  # ref: mean of first 3 reads
    k_cap_reach = int(np.argmax(uk >= u_cap - 1e-12)) if (uk >= u_cap - 1e-12).any() else k_max
    k_end_cap = min(k_cap_reach + n_cap, k_max)
    wit = np.nan_to_num(ds, nan=-1e9) >= s_w
    wit[:, k_end_cap + 1:] = False
    has = wit.any(1)
    kw = np.where(has, wit.argmax(1), k_end_cap)
    pulse = s_true[kw]
    false_end = has & (pulse < 0.5 * s_w)
    return {"p_witness": float(has.mean()), "p_cap_end": float((~has).mean()),
            "end_s_median": float(np.median(kw) * TS), "end_s_p95": float(np.percentile(kw, 95) * TS),
            "pulse_mm_median": float(np.median(pulse)), "pulse_mm_p95": float(np.percentile(pulse, 95)),
            "p_false_end": float(false_end.mean()),
            "open_cycle": int(np.argmax(v > 0)) if (v > 0).any() else None}


def sim_episode(rng, reps=2000) -> list:
    rows = []
    for est in ("E1", "E3"):
        for du in (0.025, 0.05, 0.1):
            for u_cap in (0.8, 1.0):
                for s_w in (0.3, 0.4, 0.5, 0.6):
                    for n_cap in (10, 20, 30):
                        for speed in ("sub", "full"):
                            row = {"est": est, "du_step": du, "u_cap": u_cap, "s_w": s_w,
                                   "N_cap": n_cap, "speed": speed, "by_rth": {}}
                            for r_th in (0.10, 0.20, 0.39, 0.62, 0.75, 1.2):
                                row["by_rth"][str(r_th)] = episode(
                                    rng, reps, 0.3, r_th, du, u_cap, s_w, n_cap, speed, est)
                            rows.append(row)
    return rows


def self_checks(rng) -> dict:
    chk = {}
    # stalled leg, E1, single check at k = N_trig: P(e_k - e_0 < eta D) analytic
    n, d, e, u = 10, 0.0, 0.5, 0.3
    k = np.arange(n + 1)
    r = reads(rng, np.zeros(n + 1), 40000)
    ds = r[:, n] - r[:, 0]
    p_mc = float((ds < e * n * u * TS).mean())
    p_an = float(norm.cdf(e * n * u * TS / (SIG * np.sqrt(2))))
    chk["single_check"] = {"mc": p_mc, "analytic": p_an, "ok": abs(p_mc - p_an) < 4 * np.sqrt(
        p_an * (1 - p_an) / 40000)}
    # huge true motion -> no false trigger
    first = trigger_first(reads(rng, 5.0 * np.arange(L_STREAK + 1), 2000), 0.3, 5, 0.3, 0.5, "E1")
    chk["no_trigger_big_motion"] = bool((first < 0).all())
    # never-open plant (r_th above cap): witness only by noise, pulse 0
    ep = episode(rng, 2000, 0.3, 5.0, 0.05, 0.8, 0.5, 20, "full", "E1")
    chk["never_open_pulse_zero"] = ep["pulse_mm_p95"] == 0.0
    chk["ok"] = chk["single_check"]["ok"] and chk["no_trigger_big_motion"] and \
        chk["never_open_pulse_zero"]
    return chk


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "sigma_mm": SIG, "Ts": TS, "u_hold": U_HOLD, "L_streak": L_STREAK,
           "self_checks": self_checks(rng)}
    out.update(sim_trigger(rng))
    out["episodes"] = sim_episode(rng)
    out["wall_s"] = round(time.time() - t0, 1)
    (HERE / "s10_ai_witness.json").write_text(
        json.dumps(out, indent=1, default=lambda o: o.item()), encoding="utf-8")
    ok = bool(out["self_checks"]["ok"])
    print("ok" if ok else "self_check_failed", out["wall_s"])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
