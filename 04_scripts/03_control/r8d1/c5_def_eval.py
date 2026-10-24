"""Evaluate C-5 definitions on c5_series.json (10 Hz harness series)."""
import json
import sys

import numpy as np

D = json.load(open(sys.argv[1]))


def ma(x, n):
    n = max(1, n)
    k = np.ones(n) / n
    return np.column_stack([np.convolve(x[:, j], k, mode="same") for j in range(x.shape[1])])


def bp(t, x):
    dt = float(np.median(np.diff(t)))
    a = int(round(0.5 / dt))
    return ma(ma(x, a), a) - ma(x, int(round(5.0 / dt)))


def runs(g):
    g = np.asarray(g, bool)
    out, i = [], 0
    while i < len(g):
        if g[i]:
            j = i
            while j + 1 < len(g) and g[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def amp_ratio(t, r, iv):
    res = []
    for k, (a, b) in enumerate(iv):
        end = b
        nxt = iv[k + 1][0] if k + 1 < len(iv) else None
        f = (t >= end) & (t <= end + 0.5)
        l = (t >= end + 1.5) & (t <= end + 2.0)
        if not l.any():
            res.append(("ended", None, None)); continue
        a0 = np.abs(r[f]).max(); a2 = np.abs(r[l]).max()
        sup = nxt is not None and nxt <= end + 2.0
        res.append(("sup" if sup else ("ok" if (a0 < 500 or a2 <= 0.5 * a0) else "FAIL"),
                    round(a0 / 1e3, 2), round(a2 / 1e3, 2)))
    return res


for c in D:
    t = np.asarray(c["t"]); F = np.asarray(c["F"]); g = np.asarray(c["guard"])
    att = np.degrees(np.column_stack([c["phi"], c["theta"]]))
    tc = np.asarray(c["tc"])
    iv = [(tc[a], tc[b] + 0.1) for a, b in runs(g)]
    on = np.array([a for a, _ in iv])
    max10 = max((int(np.sum((on >= x) & (on < x + 10))) for x in on), default=0)
    cad = amp_ratio(t, F - ma(F, 10), iv)
    pro = amp_ratio(t, bp(t, F), iv)
    ph = np.asarray(c["phase"])
    rd = (ph == "ready")
    tr = c["t_ready"]
    sel = rd & (t >= (tr or 1e9) + 5.0)
    cadb = float(np.max(np.ptp(att[sel], axis=0)) / 2) if sel.sum() > 10 else None
    ab = bp(t, att)
    prob = float(np.abs(ab[sel]).max()) if sel.sum() > 10 else None
    # quiet READY: >= 5 s after any guard end / leg command
    u = np.abs(np.asarray(c["u"])).max(axis=1)
    last_act = -1e9; quiet = np.zeros(len(t), bool)
    gi = np.interp(t, tc, g.astype(float)) > 0.5
    for i in range(len(t)):
        if u[i] > 1e-6 or gi[i]:
            last_act = t[i]
        quiet[i] = rd[i] and t[i] - last_act >= 5.0
    proq = float(np.abs(ab[quiet]).max()) if quiet.sum() > 10 else None
    uc = np.asarray(c["u"])
    vth = 0.01 * 20.924e-3
    revs = []
    for a, b in iv:
        w = (t >= b) & (t <= b + 4.0)
        r = []
        for j in range(4):
            x = uc[w, j]
            x = x[np.abs(x) > vth]
            r.append(int(np.sum(np.diff(np.sign(x)) != 0)))
        revs.append(r)
    # whole run after the first guard end: max reversals in any 4 s window per leg
    if iv:
        aft = t >= iv[0][1]
        worst = 0
        for x0 in t[aft]:
            w = (t >= x0) & (t <= x0 + 4.0)
            for j in range(4):
                x = uc[w, j]; x = x[np.abs(x) > vth]
                worst = max(worst, int(np.sum(np.diff(np.sign(x)) != 0)))
    else:
        worst = None
    # quiet READY (>= 3 s after READY entry? use 5 s; >= 3 s after last command / guard), linear detrend
    quiet3 = np.zeros(len(t), bool); last = -1e9
    gi2 = np.interp(t, tc, g.astype(float)) > 0.5
    uabs = np.abs(uc).max(axis=1)
    rd2 = np.asarray(c["phase"]) == "ready"
    for i in range(len(t)):
        if uabs[i] > 1e-9 or gi2[i] or not rd2[i]:
            last = t[i]
        quiet3[i] = rd2[i] and t[i] - last >= 3.0 and t[i] >= (c["t_ready"] or 1e9) + 5.0
    hp = []
    idx = np.flatnonzero(quiet3)
    if idx.size:
        segs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        for sg in segs:
            if len(sg) < 20:
                continue
            tt = t[sg]; y = att[sg]
            res = y - np.polyval(np.polyfit(tt, y, 1), tt[:, None]) if False else \
                y - np.column_stack([np.polyval(np.polyfit(tt, y[:, j], 1), tt) for j in range(2)])
            hp.append(round(float(np.max(np.ptp(res, axis=0)) / 2), 5))
    for vt in (0.02, 0.05):
        th = vt * 20.924e-3
        wst = 0
        if iv:
            for x0 in t[t >= iv[0][0]]:
                w = (t >= x0) & (t <= x0 + 4.0)
                for j in range(4):
                    x = uc[w, j]; x = x[np.abs(x) > th]
                    wst = max(wst, int(np.sum(np.diff(np.sign(x)) != 0)))
        print(f"   reversals (|u| > {vt} v_max) worst 4 s after first guard start: {wst}")
    print(f"   quiet-READY detrended half-ptp per window [deg]: {hp}")
    print(f"   cmd reversals in 4 s after each guard end {revs[:6]}; worst any 4 s after first guard {worst}")
    print(f"{c['cid']:32s} guard intervals {len(iv)} max onsets/10 s {max10} READY {tr} sink {c['settle']}")
    print("   cad(a):", cad[:8])
    print("   pro(a):", pro[:8])
    print(f"   cad(b) half-ptp {cadb} deg; pro(b) bp max {prob}; pro(b) quiet-READY bp max {proq} "
          f"(quiet samples {int(quiet.sum())})")
