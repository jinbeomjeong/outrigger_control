"""h04: pair the h03 leg windows of VBMh15 / VBMslow against VBMh05 / VBMfast / VBM-sens-free
settings (same key, round, leg) and print the distributions (read only, from h03_rows.csv).

Output: h04_out.txt
"""
import csv
import os
from collections import defaultdict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(OUT, "h03_rows.csv"), encoding="utf-8")))
by = defaultdict(dict)
for r in rows:
    if r["reversed"] == "True":
        continue
    by[(r["src"], r["key"], r["round"], r["leg"])][r["setting"]] = r


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


lines = []
SETS = ["VBMh05", "VBMfast", "VBMb069", "VBMd15", "VBMc04", "VBMh15", "VBMslow"]
cols = ["x_open_mm", "open_minus_mid_s", "ds_mid_mm", "ds_half_mm", "dF_half_kN", "Kmot_half_MN_m",
        "Kpist_proxy_MN_m", "net_stroke_after_mm", "ib_extra_mm", "d6_witness_mm", "p_h_start_bar",
        "p_r_start_bar", "dF_first_kN"]
for s in SETS:
    sub = [r for r in rows if r["setting"] == s and r["reversed"] == "False"]
    lines.append(f"== {s} windows {len(sub)}")
    for c in cols:
        v = np.array([f(r[c]) for r in sub])
        v = v[np.isfinite(v)]
        if len(v):
            q = np.percentile(v, [0, 5, 50, 95, 100])
            lines.append(f"  {c:22s} n={len(v):4d} min {q[0]:8.3f} p5 {q[1]:8.3f} med {q[2]:8.3f}"
                         f" p95 {q[3]:8.3f} max {q[4]:8.3f}")
    tr = [r["ib_target_reached"] for r in sub]
    lines.append(f"  ib_target_reached: True {tr.count('True')} False {tr.count('False')}"
                 f" none {tr.count('')}")
    ro = [r["ret_open"] for r in sub]
    lines.append(f"  ret_open True {ro.count('True')} False {ro.count('False')}")
    ls = [r["last_sign"] for r in sub]
    lines.append(f"  last_sign +1 {ls.count('1')} -1 {ls.count('-1')} 0 {ls.count('0')}")
    # warn vs non warn rounds Kmot by leg
    for wflag in (True, False):
        ss = [r for r in sub if (r["round_warn_ratio"] != "") == wflag]
        v = np.array([f(r["Kpist_proxy_MN_m"]) for r in ss])
        v = v[np.isfinite(v)]
        if len(v):
            lines.append(f"  warn_round={wflag}: Kpist med {np.median(v):.3f} p5 {np.percentile(v, 5):.3f}"
                         f" p95 {np.percentile(v, 95):.3f} n {len(v)}")
# pairing h15 vs h05
lines.append("== pairs h15 - h05 (same sens key/round/leg)")
for c in ["x_open_mm", "ds_half_mm", "dF_half_kN", "Kpist_proxy_MN_m", "net_stroke_after_mm",
          "p_h_start_bar", "ib_extra_mm"]:
    dv = []
    for k, m in by.items():
        if "VBMh15" in m and "VBMh05" in m:
            a, b = f(m["VBMh15"][c]), f(m["VBMh05"][c])
            if np.isfinite(a) and np.isfinite(b):
                dv.append(a - b)
    dv = np.array(dv)
    if len(dv):
        lines.append(f"  d {c:22s} n={len(dv)} med {np.median(dv):8.3f} p5 {np.percentile(dv, 5):8.3f}"
                     f" p95 {np.percentile(dv, 95):8.3f}")
# warn ratio table per setting and round number
lines.append("== warn ratios by setting and round index")
for s in SETS:
    rr = defaultdict(list)
    seen = set()
    for r in rows:
        if r["setting"] != s or r["round_warn_ratio"] == "":
            continue
        k = (r["key"], r["round"])
        if k in seen:
            continue
        seen.add(k)
        rr[r["round"]].append(f(r["round_warn_ratio"]))
    for rd, v in sorted(rr.items()):
        v = np.array(v)
        lines.append(f"  {s} round {rd}: n {len(v)} min {v.min():.3f} med {np.median(v):.3f} max {v.max():.3f}"
                     f" low<0.8 {int((v < 0.8).sum())} high>2.3 {int((v > 2.3).sum())}")
with open(os.path.join(OUT, "h04_out.txt"), "w", encoding="utf-8", newline="\n") as fo:
    fo.write("\n".join(lines) + "\n")
print(len(lines))
