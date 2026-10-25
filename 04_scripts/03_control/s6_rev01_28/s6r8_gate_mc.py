"""Monte Carlo for R5 gate (spec 38) open rate and B1' false-skip probability, normal grade.

White gyro noise, per-axis sigma = 0.025 deg/s per 20 ms sample (ARW 0.30 deg/sqrt(h)).
Seeds 0..9, 120 s each (open rate); 20000 trials (B1').
"""
import numpy as np

T = 0.02
SIG = 0.025          # deg/s per sample, per axis
N05, N10 = 25, 50
TH_A, TH_B = 0.02, 0.02


def wmean(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0, axis=0), axis=0)
    return np.concatenate([np.full((n - 1,) + x.shape[1:], np.nan), (c[n:] - c[:-n]) / n])


def run_hold(mask, n):
    out = np.zeros_like(mask)
    c = 0
    for k, m in enumerate(mask):
        c = c + 1 if m else 0
        out[k] = c >= n
    return out


def debounce_false(mask, n):
    """Condition counts as violated only after n consecutive False samples."""
    out = np.ones_like(mask)
    c = 0
    for k, m in enumerate(mask):
        c = 0 if m else c + 1
        out[k] = c < n
    return out


def comp_rms(w, n, about_mean):
    if about_mean:
        var = wmean(w ** 2, n) - wmean(w, n) ** 2
    else:
        var = wmean(w ** 2, n)
    return np.sqrt(np.clip(var - SIG ** 2, 0, None)).max(axis=1)


def runs(gate):
    lens, c = [], 0
    for g in gate:
        if g:
            c += 1
        elif c:
            lens.append(c)
            c = 0
    if c:
        lens.append(c)
    return np.mean(lens) * T if lens else 0.0


variants = {
    "A spec38 (0.5 s RMS, hold restart)": dict(n=N05, th=TH_A, deb=1),
    "B + violation debounce 0.1 s (5 samples)": dict(n=N05, th=TH_A, deb=5),
    "C + violation debounce 0.2 s (10 samples)": dict(n=N05, th=TH_A, deb=10),
    "D RMS window 1.0 s": dict(n=N10, th=TH_A, deb=1),
    "E threshold 0.025": dict(n=N05, th=0.025, deb=1),
}
n = int(120 / T)
for about_mean in (False, True):
    print(f"--- RMS about window mean = {about_mean}")
    for name, v in variants.items():
        rates, rl = [], []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            w = rng.normal(0, SIG, (n, 2))
            a = comp_rms(w, v["n"], about_mean) <= v["th"]
            b = np.abs(wmean(w, N10)).max(axis=1) <= TH_B
            ok = a & b
            ok = np.where(np.isnan(comp_rms(w, v["n"], about_mean)), False, ok)
            if v["deb"] > 1:
                ok = debounce_false(ok, v["deb"])
            g = run_hold(ok, N05)
            rates.append(g[N10:].mean())
            rl.append(runs(g[N10:]))
        print(f"  {name:45s} open {min(rates):.3f}-{max(rates):.3f} (mean {np.mean(rates):.3f}), "
              f"mean open run {np.mean(rl):.1f} s")

# closure delay for a 1.3 Hz rocking that starts at t=0 (amplitude giving 0.05 deg/s RMS), ideal (no noise)
t = np.arange(int(5 / T)) * T
w = np.zeros((len(t) + 200, 2))
amp = 0.05 * np.sqrt(2)
w[200:, 1] = amp * np.sin(2 * np.pi * 1.3 * t)
for name, v in variants.items():
    a = np.sqrt(np.clip(wmean(w ** 2, v["n"]) - 0.0, 0, None)).max(1) <= v["th"]
    b = np.abs(wmean(w, N10)).max(1) <= TH_B
    ok = np.where(np.isnan(a.astype(float)), False, a & b)
    if v["deb"] > 1:
        ok = debounce_false(ok, v["deb"])
    k = np.where(~ok[200:])[0]
    print(f"  closure delay {name:45s} {k[0] * T if len(k) else None:.2f} s")

# B1': 10 s window (500 samples), stationary, compensated RMS about the window mean
rng = np.random.default_rng(20261022)
trials = 20000
w = rng.normal(0, SIG, (trials, 500, 2))
var = w.var(axis=1)  # about the mean
comp = np.sqrt(np.clip(var - SIG ** 2, 0, None))
for th in (0.01, 0.0125, 0.015, 0.02):
    p_skip = np.mean((comp > th).any(axis=1))
    print(f"B1' 10 s stationary false-skip prob, threshold {th:.4f} deg/s: {p_skip:.4f}")
for scale in (1.05, 1.10):
    w2 = w * scale
    comp2 = np.sqrt(np.clip(w2.var(axis=1) - SIG ** 2, 0, None))
    for th in (0.01, 0.02):
        print(f"  sensor noise {scale:.2f} x spec, threshold {th}: skip {np.mean((comp2 > th).any(axis=1)):.4f}")
# 1.3 Hz rocking mean residual bound in 10 s window for RMS 0.02 deg/s
A = 0.02 * np.sqrt(2)
worst = max(abs(np.mean(A * np.sin(2 * np.pi * 1.3 * (np.arange(500) * T) + ph))) for ph in np.linspace(0, 2 * np.pi, 73))
print(f"rocking 1.3 Hz RMS 0.02 deg/s: worst 10 s mean residual {worst * 3600:.2f} deg/h")
worst2 = max(abs(np.mean(A / 2 * np.sin(2 * np.pi * 1.3 * (np.arange(100) * T) + ph))) for ph in np.linspace(0, 2 * np.pi, 73))
print(f"rocking 1.3 Hz RMS 0.01 deg/s: worst 2 s mean residual {worst2 * 3600:.2f} deg/h")
