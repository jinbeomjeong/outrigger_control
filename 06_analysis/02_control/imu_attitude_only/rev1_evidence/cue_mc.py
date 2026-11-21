"""Monte Carlo of the probe attitude cue (ground_contact.evaluate_probe gates) with an AHRS output quantised at
the CAN resolution, against the current gyro-integral cue.

Per trial (one leg probe, 1-D along J_i, small angles):
* 100 Hz samples h = 10 ms; 10 Hz control period T = 0.1 s.
* true attitude: lifted leg 0; grounded leg J |ds| x trapezoid position (D 0.56 s, ramp 0.36 s, 2 mm), plus optional
  residual rocking A_r sin(2 pi 1.784 t + phase) (true); the AHRS output carries (1 + (G-1) H_acc) of it.
* AHRS: discrete Mahony PI (as design 2.1): e = tilt_acc - x, b -= kI e h, x += (w - b + kP e) h, tilt_acc = true +
  accel noise (sigma = d_a sqrt(1/(2h))), w = true rate + gyro noise (sigma = ARW sqrt(1/(2h))); 5 s burn-in.
  Output quantised round(x / q) q with a random grid offset per trial.
* cue signal per period: B = mean of the period's 10 output samples ("period_mean") or the last one ("last");
  current = gyro rate (bias removed) integrated per period with the period mean rate (c2.py 5465-5473).
* windows: 3 period values before the move start and the last 3 of the 0.4 s hold (ground_contact.py 814-819,
  968-969); spacing = move + hold + T (1033); ripple = detrended ptp, drift = |slope| x spacing, both over the
  expected response; abstain if ripple > 0.15 or drift > 0.25; attitude says grounded if not abstained and
  change / expected >= 0.5.
Usage: python -I -B cue_mc.py <out.json> [trials]
"""
import json
import math
import sys

import numpy as np

DEG = math.pi / 180
H, T = 0.01, 0.1
N_SUB = 10
J_DS = 0.0236 * DEG                      # expected response, rad
D_S, RAMP_S, HOLD_S = 0.56, 0.36, 0.4
MOVE_S = D_S + RAMP_S
F_ROCK, G_ROCK = 1.784, 26.8
GRADES = {"good": (0.15, 15.0), "normal": (0.30, 82.0)}   # ARW deg/sqrt(h), accel ug/sqrt(Hz)
F_C = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
WC = 2 * math.pi * F_C
KP, KI = 2 * WC, WC * WC


def trapezoid_pos(t):
    v = 1.0 / D_S                          # plateau speed per unit depth
    t = np.clip(t, 0.0, MOVE_S)
    return np.where(t <= RAMP_S, v * t * t / (2 * RAMP_S),
                    np.where(t <= D_S, v * (t - 0.5 * RAMP_S),
                             1.0 - v * (MOVE_S - t) ** 2 / (2 * RAMP_S)))


def h_acc_gain():
    s = 2j * math.pi * F_ROCK
    return abs(1 + (G_ROCK - 1) * (KP * s + KI) / (s * s + KP * s + KI))


def windows_gate(vals):
    """vals (trials, 3); returns detrended ptp and slope (per s) of each row."""
    t = np.array([0.0, T, 2 * T])
    tc = t - t.mean()
    slope = (vals - vals.mean(axis=1, keepdims=True)) @ tc / (tc @ tc)
    resid = vals - vals.mean(axis=1, keepdims=True) - slope[:, None] * tc[None, :]
    return np.ptp(resid, axis=1), slope


def run(grade, q_deg, grounded, rock_deg, sampling, n, rng):
    arw, acc_ug = GRADES[grade]
    sg = arw / 60.0 * DEG * math.sqrt(1 / (2 * H))
    sa = acc_ug * 1e-6 * math.sqrt(1 / (2 * H))
    burn = 500
    pre = 3 * N_SUB
    move = int(round(MOVE_S / T)) * N_SUB
    hold = int(round(HOLD_S / T)) * N_SUB
    steps = burn + pre + move + hold
    tt = (np.arange(steps) - burn - pre + 1) * H          # move starts at t = 0
    resp = J_DS * trapezoid_pos(tt) if grounded else np.zeros(steps)
    resp_rate = np.gradient(resp, H)
    phase = rng.uniform(0, 2 * math.pi, n)
    rock = rock_deg * DEG * np.sin(2 * math.pi * F_ROCK * tt[None, :] + phase[:, None])
    rock_rate = rock_deg * DEG * 2 * math.pi * F_ROCK * np.cos(2 * math.pi * F_ROCK * tt[None, :] + phase[:, None])
    true = resp[None, :] + rock
    rate = resp_rate[None, :] + rock_rate
    acc_tilt = resp[None, :] + G_ROCK * rock + sa * rng.standard_normal((n, steps))
    gyro = rate + sg * rng.standard_normal((n, steps))
    x = np.zeros(n); b = np.zeros(n)
    out = np.empty((n, steps))
    for k in range(steps):
        e = acc_tilt[:, k] - x
        b = b - KI * e * H
        x = x + (gyro[:, k] - b + KP * e) * H
        out[:, k] = x
    if q_deg > 0:
        q = q_deg * DEG
        off = rng.uniform(0, q, n)[:, None]
        out = np.round((out + off) / q) * q - off
    # current cue: integral of gyro (bias removed exactly), per period with the period mean rate
    seg = slice(burn, steps)
    o = out[:, seg].reshape(n, -1, N_SUB)
    g = gyro[:, seg].reshape(n, -1, N_SUB)
    per_B = o.mean(axis=2) if sampling == "period_mean" else o[:, :, -1]
    per_cur = np.cumsum(g.mean(axis=2) * T, axis=1)
    res = {}
    spacing = MOVE_S + HOLD_S + T
    for name, per in (("B", per_B), ("current", per_cur)):
        before = per[:, 0:3]
        after = per[:, -3:]
        change = after.mean(axis=1) - before.mean(axis=1)
        ratio = change / J_DS
        r1, s1 = windows_gate(before)
        r2, s2 = windows_gate(after)
        ripple = np.maximum(r1, r2) / J_DS
        drift = np.maximum(np.abs(s1), np.abs(s2)) * spacing / J_DS
        abst = (ripple > 0.15) | (drift > 0.25)
        says = (~abst) & (ratio >= 0.5)
        res[name] = {"abstain_rate": float(abst.mean()), "abstain_ripple": float((ripple > 0.15).mean()),
                     "abstain_drift": float((drift > 0.25).mean()), "says_grounded_rate": float(says.mean()),
                     "ratio_mean": float(ratio.mean()), "ratio_std": float(ratio.std())}
    return res


def main():
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    rng = np.random.default_rng(20261122)
    full = F_C == 0.05
    out = {"assumptions": {"f_c_hz": F_C, "expected_deg": 0.0236, "rock_gain_B": h_acc_gain(), "trials": n,
                           "seed": 20261122}, "rows": []}
    for grade in ("good", "normal"):
        for q in ((0.0, 0.001, 0.002, 0.0057, 0.0078, 0.01) if full else (0.0, 0.0057, 0.01)):
            for rock in ((0.0, 0.003) if full else (0.0,)):
                for sampling in (("period_mean", "last") if full else ("period_mean",)):
                    for grounded in (False, True):
                        r = run(grade, q, grounded, rock, sampling, n, rng)
                        row = {"grade": grade, "lsb_deg": q, "rock_true_deg": rock, "sampling": sampling,
                               "grounded": grounded, **r}
                        out["rows"].append(row)
                        print(grade, q, rock, sampling, "grounded" if grounded else "lifted",
                              "B abst %.3f says %.4f | cur abst %.3f says %.4f" % (
                                  r["B"]["abstain_rate"], r["B"]["says_grounded_rate"],
                                  r["current"]["abstain_rate"], r["current"]["says_grounded_rate"]), flush=True)
    json.dump(out, open(sys.argv[1], "w"), indent=1)


if __name__ == "__main__":
    main()
