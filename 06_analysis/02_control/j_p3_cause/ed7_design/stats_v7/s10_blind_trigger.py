"""Ed. 7 Q7-S1: A(i)-b blind-band trigger (spec v7 3.1) - false trigger on moving legs, detection
and resolution time on locked legs, pulse cadence. stats-design-expert, 2026-11-24, design only.

Command/plant pipeline (vectorised over Monte Carlo replicates):
  cycle T_s 0.1 s. At cycle k: read stroke s(t_k) + N(0, sigma_read); controller computes u_out[k]
  from reads <= k; u_out[k] is applied to the valve over [t_{k+1}, t_{k+2}) (output delay d = 1:
  the first read showing it is k + 2). Increment limit |u_out[k] - u_out[k-1]| <= 0.25 v_max
  (both ways). Valve ramp: symmetric, full scale in 0.1 s (rate v_max / 0.1 s), 10 sub-steps.
  Plant (P1 proxy): threshold r_th = c_v v_max; flow 'sub' = sign(u)(|u| - r_th)+ or 'full' =
  u if |u| > r_th. From lock a fill x integrates the flow until x >= need (line-fill gate), then
  the leg moves with the flow; two consecutive cycles with |valve| <= r_th relock (x reset).
  Stroke coordinate = oil coordinate (harness stroke_m); no load-induced drift (real piston
  coordinate: see report).
A(i)-b (spec v7 3.1): stretch = consecutive cycles whose output u_out is 0 < |u| <= u_hold with
  one sign; when the count >= N_blind and the stillness witness E3 ds < s_still (sign-multiplied)
  holds (LEVEL completion assumed false) -> trigger. Then floor u_0 = max(|u|, u_hold) + 0.2,
  +0.2 mm/s per cycle up to 1.05; end on E3 ds >= 0.4 mm from the trigger anchor, or 50 cycles at
  cap. After the end the band command resumes and a new stretch starts.
Witness baseline variants for ds = mean(reads[k-2..k]) - baseline:
  'anchor' = mean(reads[k_s..k_s+2]) (spec text, k_s = first band output cycle)
  'flush'  = mean(reads[k_s+2..k_s+4]) (skip the d = 1 pipeline)
  'slide'  = mean(reads[k-N+1..k-N+3]) (fixed N-cycle window)
Outputs (argv[1]): s10_blind_trigger.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

SEED = 20261114
T = 0.1
VMAX = 20.924
U_HOLD = 0.209243
INC = 0.25 * VMAX
SIG = 0.1
SUB = 10
RAMP = VMAX / 0.1                     # mm/s per s
STEP, CAP, NCAP, SW_END = 0.2, 1.05, 50, 0.4


def simulate(R, rng, *, n_blind, s_still, witness, u_pre, n_pre, u_b, c_v, flow, need,
             locked0, horizon_s, sigma=SIG, max_trig=None):
    K = int(round(horizon_s / T)) + n_pre
    r_th = c_v * VMAX
    pos = np.zeros(R)
    locked = np.full(R, locked0)
    fill = np.zeros(R)
    below = np.zeros(R, int)
    valve = np.full(R, u_pre if not locked0 else 0.0)
    reads = np.zeros((R, K + 1))
    u_out = np.full(R, u_pre if not locked0 else 0.0)
    u_prev_applied = u_out.copy()
    # stretch / A_ib state
    ks = np.full(R, -1)
    cnt = np.zeros(R, int)
    active = np.zeros(R, bool)
    floor = np.zeros(R)
    capc = np.zeros(R, int)
    anchor = np.zeros(R)
    trig_pos = np.zeros(R)
    first_trig = np.full(R, -1)
    first_end = np.full(R, -1)
    end_reason = np.zeros(R, int)            # 1 moved, 2 cap
    n_trig = np.zeros(R, int)
    first_move = np.full(R, -1)
    disp_after_first_end = np.full(R, np.nan)
    pos_first_trig = np.full(R, np.nan)
    k_band0 = n_pre                          # cycle of the first band output
    for k in range(K):
        reads[:, k] = pos + sigma * rng.standard_normal(R)
        u_des = u_pre if k < n_pre else u_b
        base = np.clip(np.full(R, u_des), u_out - INC, u_out + INC)
        out = base.copy()
        # A_ib end checks for active replicates
        if active.any():
            ds = (reads[:, max(k - 2, 0):k + 1].mean(1) - anchor)
            moved = active & (ds >= SW_END)
            capped = active & (capc >= NCAP)
            done = moved | capped
            if done.any():
                newly = done & (first_end < 0)
                first_end[newly] = k
                end_reason[newly & moved] = 1
                end_reason[newly & capped & ~moved] = 2
                active[done] = False
                ks[done] = -1
                cnt[done] = 0
        # stretch counter on the output (band, one sign)
        inband = (np.abs(base) > 1e-12) & (np.abs(base) <= U_HOLD) & ~active
        new = inband & (ks < 0)
        ks[new] = k
        cnt[inband] += 1
        cnt[~inband & ~active] = 0
        ks[~inband & ~active] = -1
        # trigger check
        cand = (~active) & (cnt >= n_blind)
        if cand.any():
            cur = reads[:, max(k - 2, 0):k + 1].mean(1)
            ar = np.arange(R)
            if witness == "anchor":
                j0 = np.clip(ks, 0, None)
            elif witness == "flush":
                j0 = np.clip(ks + 2, 0, None)
            else:
                j0 = np.full(R, max(k - n_blind + 1, 0))
            j0 = np.minimum(j0, k - 2)
            b0 = (reads[ar, j0] + reads[ar, j0 + 1] + reads[ar, j0 + 2]) / 3.0
            trig = cand & ((cur - b0) * np.sign(u_b) < s_still)
            if max_trig is not None:
                trig &= n_trig < max_trig
            if trig.any():
                active[trig] = True
                floor[trig] = np.maximum(np.abs(base[trig]), U_HOLD)
                capc[trig] = 0
                anchor[trig] = cur[trig]
                trig_pos[trig] = pos[trig]
                newt = trig & (first_trig < 0)
                first_trig[newt] = k
                pos_first_trig[newt] = pos[newt]
                n_trig[trig] += 1
        if active.any():
            floor[active] = np.minimum(floor[active] + STEP, CAP)
            capc[active & (floor >= CAP - 1e-12)] += 1
            out[active] = np.sign(u_b) * np.maximum(np.abs(base[active]), floor[active])
            out = np.clip(out, u_out - INC, u_out + INC)
        # plant over [t_k, t_{k+1}) with the command computed at k-1 (d = 1)
        target = u_prev_applied
        dt = T / SUB
        moved_flag = np.zeros(R, bool)
        for _ in range(SUB):
            valve = valve + np.clip(target - valve, -RAMP * dt, RAMP * dt)
            a = np.abs(valve)
            if flow == "sub":
                f = np.maximum(a - r_th, 0.0)
            else:
                f = np.where(a > r_th, a, 0.0)
            filling = locked & (f > 0)
            fill[filling] += f[filling] * dt
            opened = locked & (fill >= need)
            locked[opened] = False
            mv = (~locked) & (f > 0)
            pos[mv] += np.sign(valve[mv]) * f[mv] * dt
            moved_flag |= mv
        stopped = np.abs(valve) <= r_th
        below = np.where(stopped, below + 1, 0)
        relock = below >= 2
        locked[relock] = True
        fill[relock] = 0.0
        u_prev_applied = out.copy()
        u_out = out
        # first move after first trigger (true displacement >= 0.05 mm)
        fm = (first_trig >= 0) & (first_move < 0) & (np.abs(pos - pos_first_trig) >= 0.05)
        first_move[fm] = k + 1
        # displacement 3 cycles after first end (pipeline flushed)
        ready = (first_end >= 0) & np.isnan(disp_after_first_end) & (k >= first_end + 3)
        disp_after_first_end[ready] = (pos[ready] - pos_first_trig[ready]) * np.sign(u_b)
    return {"first_trig": first_trig, "first_move": first_move, "first_end": first_end,
            "end_reason": end_reason, "n_trig": n_trig, "disp": disp_after_first_end,
            "pos_end": pos, "k_band0": k_band0, "K": K}


def q(x, ps=(50, 95)):
    x = x[np.isfinite(x)]
    return [round(float(v), 3) for v in np.percentile(x, ps)] if x.size else None


def false_trigger(rng, R=2000):
    """Moving leg inside the band (low-threshold plants): P(trigger within 5 s / 30 s)."""
    out = {}
    for c_v, flow in ((0.0, "full"), (0.005, "full"), (0.005, "sub")):
        for u_b in (0.06, 0.10, 0.15, 0.20):
            v = u_b if flow == "full" else max(u_b - c_v * VMAX, 0.0)
            if c_v > 0 and u_b <= c_v * VMAX:
                continue
            for n in (15, 20, 25, 30, 40):
                for s in (0.05, 0.10, 0.15):
                    for w in ("anchor", "flush", "slide"):
                        r = simulate(R, rng, n_blind=n, s_still=s, witness=w, u_pre=u_b, n_pre=0,
                                     u_b=u_b, c_v=c_v, flow=flow, need=0.0, locked0=False,
                                     horizon_s=30.0, max_trig=1)
                        t = (r["first_trig"] - r["k_band0"]) * T
                        p5 = float(((r["first_trig"] >= 0) & (t <= 5.0)).mean())
                        p30 = float((r["first_trig"] >= 0).mean())
                        out[f"cv{c_v}|{flow}|u{u_b}|v{v:.3f}|N{n}|s{s}|{w}"] = {
                            "v_mm_s": v, "P_trig_5s": p5, "P_trig_30s": p30,
                            "mcse_30s": float(np.sqrt(max(p30 * (1 - p30), 1e-12) / R))}
    return out


def detection(rng, R=1000):
    """Locked leg with a band command: trigger time, first motion, end, pulse size."""
    out = {}
    plants = (("cv0.005|sub", 0.005, "sub"), ("cv0.02|sub", 0.02, "sub"),
              ("cv0.02|full", 0.02, "full"), ("cv0.04|sub", 0.04, "sub"))
    for pname, c_v, flow in plants:
        for need in (0.2, 1.5, 3.1):
            for u_pre in (0.0, 1.05, 3.0):
                for n in (20, 25, 30):
                    for w in ("anchor", "flush"):
                        locked0 = u_pre == 0.0
                        r = simulate(R, rng, n_blind=n, s_still=0.10, witness=w, u_pre=u_pre,
                                     n_pre=10, u_b=0.10, c_v=c_v, flow=flow, need=need,
                                     locked0=locked0, horizon_s=20.0, max_trig=1)
                        kb = r["k_band0"]
                        ft = np.where(r["first_trig"] >= 0, (r["first_trig"] - kb) * T, np.nan)
                        fm = np.where(r["first_move"] >= 0, (r["first_move"] - kb) * T, np.nan)
                        fe = np.where(r["first_end"] >= 0, (r["first_end"] - kb) * T, np.nan)
                        out[f"{pname}|need{need}|pre{u_pre}|N{n}|{w}"] = {
                            "P_trig_by_10s": float(np.nanmean(np.where(np.isnan(ft), 0, ft <= 10))),
                            "t_trig_q50_95": q(ft), "t_move_q50_95": q(fm), "t_end_q50_95": q(fe),
                            "P_end_cap": float((r["end_reason"] == 2).mean()),
                            "pulse_mm_q50_95": q(r["disp"])}
    return out


def cadence(rng, R=500):
    """Steady band command 0.05-0.20 mm/s on a locked leg for 30 s: pulses and mean speed."""
    out = {}
    for c_v, flow, need in ((0.02, "sub", 0.2), (0.02, "sub", 1.5), (0.04, "sub", 0.2),
                            (0.005, "sub", 0.2)):
        for u_b in (0.05, 0.10, 0.20):
            for n in (20, 25, 30, 40):
                r = simulate(R, rng, n_blind=n, s_still=0.10, witness="flush", u_pre=0.0,
                             n_pre=1, u_b=u_b, c_v=c_v, flow=flow, need=need, locked0=True,
                             horizon_s=30.0)
                out[f"cv{c_v}|{flow}|need{need}|u{u_b}|N{n}"] = {
                    "pulses_q50": float(np.median(r["n_trig"])),
                    "mean_speed_mm_s": float(np.median(r["pos_end"]) / 30.0),
                    "ratio_to_command": float(np.median(r["pos_end"]) / 30.0 / u_b)}
    return out


def self_checks(rng) -> dict:
    chk = {}
    # (1) noise-free locked leg, need large: trigger exactly when the count reaches N
    r = simulate(50, rng, n_blind=20, s_still=0.1, witness="anchor", u_pre=0.0, n_pre=1, u_b=0.1,
                 c_v=0.02, flow="sub", need=1e9, locked0=True, horizon_s=5.0, sigma=0.0,
                 max_trig=1)
    chk["noise_free_trigger_at_N"] = bool(np.all(r["first_trig"] - r["k_band0"] == 19))
    # (2) fast motion in a no-threshold plant (u 0.2, N 40 -> 0.8 mm): no trigger (anchor)
    r = simulate(500, rng, n_blind=40, s_still=0.1, witness="anchor", u_pre=0.2, n_pre=0,
                 u_b=0.2, c_v=0.0, flow="full", need=0.0, locked0=False, horizon_s=10.0,
                 max_trig=1)
    chk["fast_no_trigger"] = float((r["first_trig"] >= 0).mean()) < 0.01
    # (3) slide witness, stationary per-look probability vs analytic Phi((s - mu)/sigma_E3)
    v, n = 0.05, 20
    mu = v * (n - 3) * T                 # mean(reads[n-3..n-1]) - mean(reads[0..2])
    an = norm.cdf((0.10 - mu) / (SIG * np.sqrt(2 / 3)))
    r = simulate(4000, rng, n_blind=n, s_still=0.10, witness="slide", u_pre=v, n_pre=0, u_b=v,
                 c_v=0.0, flow="full", need=0.0, locked0=False, horizon_s=(n + 6) * T,
                 max_trig=1)
    first_look = float((r["first_trig"] - r["k_band0"] == n - 1).mean())
    chk["slide_first_look"] = {"mc": first_look, "analytic_approx": float(an),
                               "ok": abs(first_look - an) < 0.05}
    chk["ok"] = bool(chk["noise_free_trigger_at_N"] and chk["fast_no_trigger"]
                     and chk["slide_first_look"]["ok"])
    return chk


def main() -> int:
    out_dir = Path(sys.argv[1])
    rng = np.random.default_rng(SEED)
    quick = len(sys.argv) > 2 and sys.argv[2] == "quick"
    sc = 0.05 if quick else 1.0
    res = {"seed": SEED, "model": __doc__.splitlines()[0], "self_checks": self_checks(rng),
           "replicates": {"false_trigger": int(2000 * sc), "detection": int(1000 * sc),
                          "cadence": int(500 * sc)}}
    res["false_trigger"] = false_trigger(rng, R=int(2000 * sc))
    res["detection"] = detection(rng, R=int(1000 * sc))
    res["cadence"] = cadence(rng, R=int(500 * sc))
    (out_dir / "s10_blind_trigger.json").write_text(
        json.dumps(res, indent=1, default=lambda o: o.item()), encoding="utf-8")
    L = [f"self_checks {json.dumps(res['self_checks'], default=lambda o: o.item())}",
         "== false trigger (moving leg) =="]
    for k, v in res["false_trigger"].items():
        L.append(f"{k:<45} P5s {100*v['P_trig_5s']:5.1f}%  P30s {100*v['P_trig_30s']:5.1f}%")
    L.append("== detection (locked leg, u_b 0.10, s_still 0.1) ==")
    for k, v in res["detection"].items():
        L.append(f"{k:<38} P10s {v['P_trig_by_10s']:.3f} trig {v['t_trig_q50_95']} move "
                 f"{v['t_move_q50_95']} end {v['t_end_q50_95']} cap {v['P_end_cap']:.3f} "
                 f"pulse {v['pulse_mm_q50_95']}")
    L.append("== cadence (flush witness) ==")
    for k, v in res["cadence"].items():
        L.append(f"{k:<34} pulses {v['pulses_q50']:.0f} mean speed {v['mean_speed_mm_s']:.3f} "
                 f"ratio {v['ratio_to_command']:.2f}")
    (out_dir / "s10_blind_trigger.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = res["self_checks"]["ok"]
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
