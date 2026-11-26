"""h08: rebuild the round stiffness ratio median_i(K1_i / k_nom_i) from the T4h windows of h03
and check it against the recorded WARN ratios (read only).

K1_i = dF / (ds_oil - dF / k_h(s)), k_h = beta A_h / (L0h + s) (piston reading = oil stroke minus
the oil column compression; beta 1 GPa, L0h a fit choice). k_nom front / rear are fitted on the
warned rounds (recorded ratio), then the classification (warn / no warn) is checked on every
round of every setting. The rebuilt ratio is a PROXY (no piston reading or k_nom in T4h).

Output: h08_out.txt, h08_rounds.csv
"""
import csv
import math
import os
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8"))
        if r["reversed"] == "False"]
A_H = {"FL": math.pi / 4 * 0.13 ** 2, "FR": math.pi / 4 * 0.13 ** 2,
       "RL": math.pi / 4 * 0.11 ** 2, "RR": math.pi / 4 * 0.11 ** 2}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


rounds = defaultdict(list)
for r in rows:
    rounds[(r["src"], r["setting"], r["key"], r["round"])].append(r)


def k1(r, L0h):
    dF = f(r["dF_half_kN"]) * 1e3
    ds = f(r["ds_half_mm"]) * 1e-3
    s = f(r["s_start_mm"]) * 1e-3
    if not (np.isfinite(dF) and np.isfinite(ds) and np.isfinite(s)):
        return float("nan")
    kh = 1.0e9 * A_H[r["leg"]] / (L0h + s)
    dp = ds - dF / kh
    return dF / dp if abs(dp) > 1e-7 else float("nan")


def predict(rs, kf, kr, L0h):
    vals = []
    for r in rs:
        k = k1(r, L0h)
        if np.isfinite(k) and k > 0.0:
            vals.append(k / (kf if r["leg"].startswith("F") else kr))
    return float(np.median(vals)) if len(vals) >= 2 else float("nan")


warned = [(k, rs) for k, rs in rounds.items() if rs[0]["round_warn_ratio"] != ""
          and k[0] in ("sens", "j9main")]
best = None
for L0h in (0.05, 0.08):
    for kf in np.arange(2.0, 8.01, 0.1):
        for kr in np.arange(2.0, 8.01, 0.1):
            err = []
            for _, rs in warned:
                p = predict(rs, kf * 1e6, kr * 1e6, L0h)
                if np.isfinite(p):
                    err.append(math.log(p / f(rs[0]["round_warn_ratio"])))
            if not err:
                continue
            e = float(np.median(np.abs(err)))
            if best is None or e < best[0]:
                best = (e, L0h, kf, kr)
e, L0h, kf, kr = best
lines = [f"fit on {len(warned)} warned rounds: median |log err| {e:.3f}, L0h {L0h}, "
         f"k_nom front {kf:.1f} MN/m, rear {kr:.1f} MN/m (PROXY)"]
out = []
conf = defaultdict(lambda: defaultdict(int))
for k, rs in sorted(rounds.items()):
    p = predict(rs, kf * 1e6, kr * 1e6, L0h)
    rec = rs[0]["round_warn_ratio"]
    pred_warn = np.isfinite(p) and not (0.8 <= p <= 2.3)
    conf[(k[0], k[1])][("rec_warn" if rec else "rec_ok") + ("|pred_warn" if pred_warn else "|pred_ok")] += 1
    per_leg = {r["leg"]: round(k1(r, L0h) / ((kf if r["leg"][0] == "F" else kr) * 1e6), 3)
               for r in rs}
    out.append({"src": k[0], "setting": k[1], "key": k[2], "round": k[3],
                "recorded": rec, "rebuilt": None if not np.isfinite(p) else round(p, 3),
                **{f"r_{lg}": per_leg.get(lg) for lg in ("FL", "FR", "RL", "RR")},
                **{f"x_open_{r['leg']}": r["x_open_mm"] for r in rs}})
for (src, s), c in sorted(conf.items()):
    lines.append(f"{src}:{s} " + ", ".join(f"{a} {b}" for a, b in sorted(c.items())))
with open(os.path.join(OUT, "h08_rounds.csv"), "w", newline="", encoding="utf-8") as fo:
    fields = []
    for o in out:
        for kk in o:
            if kk not in fields:
                fields.append(kk)
    w = csv.DictWriter(fo, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
with open(os.path.join(OUT, "h08_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print("\n".join(lines))
