"""Tables of selected verify_S6C rows (value per case)."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
items = [
    "D8 min true cylinder force >= F_min + 5 kN",
    "D8 attitude last 5 s + mount <= 0.2 deg",
    "REANCHOR min >= F_min + 7 kN",
    "R/D8 min force >= F_min + 5 kN",
    "R attitude change during REANCHOR",
    "C-5a command sign reversals (4 s window)",
    "C-5b guard restarts (10 s window)",
    "C-5c quiet READY attitude residual half range [deg]",
    "C-5 guard load oscillation ratio (report)",
    "2 attitude +-0.2 (+mount)",
    "4 max moving pressure",
    "4 max pressure in the event transient",
    "4 max moving pressure outside the event transient",
    "3 lift-off other legs in the event transient",
    "3 lift-off other legs after the transient",
    "3 F_min before the event",
    "3 F_min after the re-READY",
    "RE1b re-READY <= 60 s",
    "7b verdict = truth",
    "7c load estimate error",
    "C-8 no false D5 / E-5 (10 Hz constants, live)",
    "C-8 replay 1.5 s baseline (offline)",
    "5.24.2 unexpected warnings",
    "T2 accuracy (+mount)",
    "T3 change -> READY",
    "6 re-READY <= 40 s",
    "R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g)",
]


def f(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list):
        return "[" + ",".join(f(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}:{f(x)}" for k, x in v.items()) + "}"
    return str(v)


for it in items:
    rs = [r for r in d["rows"] if r["item"] == it]
    if not rs:
        continue
    print(f"\n### {it}  (limit {f(rs[0]['limit'])})")
    for r in rs:
        print(f"  {r['case']:42s} {f(r['value'])[:160]:60s} {r['passed']}  {r.get('note','')[:120]}")
