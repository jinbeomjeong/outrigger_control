"""Ed. 7 review (stats-design-expert, 2026-11-24): recompute the G1 and sensitivity cluster rule
error rates for the implemented judged sets (a6fc3dd5 key lists), with the design models of
stats_v7/s31_confirm_rules.py.

(A) G1: one line per cluster, rows independent given the draw -> the per-cluster failure is
    Bernoulli with the draw-averaged probability; the total is Poisson-binomial (exact).
    Null p_i = min(1, f * p_margin + p0); harm: each cluster defective with pi_c, then fails q.
    Sets: design 171 (U832 counted, s31), implemented 168 (U832 out), 168 + FL-Fs4 neighbour risk.
    Cross-check: the exact values against the s31 Monte Carlo numbers in s31_confirm_rules.json.
(B) sensitivity: s31.sens_sim with the actual (phases, probe-seen) frame of the judged settings
    (10 seen units per setting) against the design frame (8 seen).
(C) D6 witness E3 0.3 mm (impl: reference = first three stage reads, max over windows k >= 2)
    false-witness rate on a not-opened round vs the number of stage reads.
Outputs (argv[1]): r10_recompute.json / .txt. stdout: status only.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

STATS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\stats_v7")
SEED = 20261114
U832 = {("bottom", 2.0, "ready", "FL", "RE1bF"), ("bottom", 2.0, "ready", "FR", "RE1bF"),
        ("bottom", 4.0, "ready", "FR", "RE1bF")}
FL4 = ("bottom", 4.0, "ready", "FL", "RE1bF")


def load_s31():
    spec = importlib.util.spec_from_file_location("s31", STATS / "s31_confirm_rules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clusters_keyed():
    cl = defaultdict(list)
    with (STATS / "s30_pool_opp_p.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if float(r["p_np"]) > 0:
                continue
            cl[(r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])].append(
                float(r["p_margin"]))
    return cl


def poisson_binomial(p):
    dist = np.zeros(len(p) + 1)
    dist[0] = 1.0
    for pi in p:
        dist[1:] = dist[1:] * (1 - pi) + dist[:-1] * pi
        dist[0] *= (1 - pi)
    return dist


def marg(cl, keys, f, p0, harm=None):
    out = []
    for c in keys:
        pm = np.minimum(1.0, f * np.array(cl[c]) + p0).mean()
        if harm is not None:
            pi_c, q = harm
            pm = pm + (1 - pm) * pi_c * q
        out.append(pm)
    return np.array(out)


def tail(dist, k):
    return float(dist[k + 1:].sum())


def grid_part(cl):
    keys171 = sorted(cl)
    keys168 = [c for c in keys171 if c not in U832]
    keys167 = [c for c in keys168 if c != FL4]
    res = {"n171": len(keys171), "n168": len(keys168)}
    for f in (1, 3):
        for p0 in (0.0, 0.002, 0.005, 0.01, 0.017):
            for name, keys in (("171", keys171), ("168", keys168)):
                d = poisson_binomial(marg(cl, keys, f, p0))
                res[f"{name}|null|f{f}|p0{p0}"] = {f"k{k}": tail(d, k) for k in (2, 3, 4)} | {
                    "E": float((np.arange(d.size) * d).sum())}
            # FL-Fs4 neighbour of U832: its line fails with q_u (offset-locked 1/3, cluster 0.75, 1)
            d167 = poisson_binomial(marg(cl, keys167, f, p0))
            for q_u in (1 / 3, 0.75, 1.0):
                # FPR = P(N167 + B > 3), B ~ Bern(max(q_u, own null p)) independent
                pown = float(marg(cl, [FL4], f, p0)[0])
                qq = max(q_u, pown)
                res[f"168+FL4|null|f{f}|p0{p0}|qu{q_u:.2f}"] = {
                    f"k{k}": tail(d167, k) + qq * float(d167[k]) for k in (2, 3, 4)}
    for pi_c in (0.01, 0.02, 0.05):
        for q in (0.3, 0.6, 1.0):
            for name, keys in (("171", keys171), ("168", keys168)):
                d = poisson_binomial(marg(cl, keys, 1, 0.005, (pi_c, q)))
                res[f"{name}|harm|pi{pi_c}|q{q}"] = {f"k{k}": tail(d, k) for k in (2, 3, 4)}
    # minimum detectable defect share at q = 1 / 0.6 (power 80 %), p0 0.005
    for q in (0.6, 1.0):
        for name, keys in (("171", keys171), ("168", keys168)):
            lo, hi = 0.0, 0.5
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                d = poisson_binomial(marg(cl, keys, 1, 0.005, (mid, q)))
                lo, hi = (mid, hi) if tail(d, 3) < 0.8 else (lo, mid)
            res[f"mde80|{name}|q{q}|k3"] = hi
    # ed. 6 evidence after the exclusion: 0 non-mechanism failures in 174 - 8 - 3 = 163 lines
    res["p0_upper95_0of163"] = float(1 - 0.05 ** (1 / 163))
    res["p0_upper95_3of174"] = None
    return res


ACTUAL_FRAME = [(4, 1), (2, 0), (2, 1), (2, 1), (2, 0), (2, 0), (2, 1), (2, 0), (2, 0), (2, 2),
                (4, 0), (4, 1), (4, 1), (4, 1), (4, 1), (4, 0)]
# R12, R12 top-FL-Fs0, top-FL-Fs8, top-FR-Fs4, top-RL-Fs4, top-RR-Fs4, bottom-FL-Fs4,
# bottom-RR-Fs4, R14, R15, R16, S1, S4, S5, S7, R2ra (r00_inspect.json, VBMslow)


def sens_part(s31):
    rng = np.random.default_rng(SEED)
    design = s31.sens_frame
    res = {"design_frame_unseen": sum(p - s for p, s in design()),
           "actual_frame_unseen": sum(p - s for p, s in ACTUAL_FRAME)}
    n_sim = 20000
    for label, frame in (("design", design), ("actual", lambda: list(ACTUAL_FRAME))):
        s31.sens_frame = frame
        for c in (2.5, 2.8, 3.0, 3.5):
            res[f"{label}|S4|null|c{c}"] = s31.sens_sim(rng, 4, 4, c, 0.5, n_sim)
        for kind, q in (("one_setting", 0.5), ("one_setting", 1.0), ("all_settings", 0.25),
                        ("all_settings", 0.5)):
            res[f"{label}|S4|harm|{kind}|q{q}"] = s31.sens_sim(rng, 4, 4, 3.0, 0.5, n_sim // 2,
                                                               harm=(kind, q))
    s31.sens_frame = design
    return res


def d6_part():
    rng = np.random.default_rng(SEED + 1)
    res = {}
    R = 200000
    for n_reads in (13, 15, 20, 30, 40):
        x = 0.1 * rng.standard_normal((R, n_reads))
        m = np.stack([x[:, j - 2:j + 1].mean(1) for j in range(2, n_reads)], 1)
        moved = m - m[:, :1]
        for sw in (0.3, 0.4):
            p = float((moved.max(1) >= sw).mean())
            res[f"reads{n_reads}|sw{sw}"] = {"p": p, "mcse": float(np.sqrt(p * (1 - p) / R))}
    return res


def main() -> int:
    out = Path(sys.argv[1])
    s31 = load_s31()
    cl = clusters_keyed()
    res = {"seed": SEED, "grid": grid_part(cl), "sens": sens_part(s31), "d6": d6_part()}
    # cross-check against the design Monte Carlo (s31_confirm_rules.json)
    design = json.loads((STATS / "s31_confirm_rules.json").read_text(encoding="utf-8"))
    chk = {}
    for p0 in (0.0, 0.005, 0.017):
        for f in (1, 3):
            mc = design["grid"][f"G1|null|f{f}|p0{p0}|rho0.0"]["count3"]
            ex = res["grid"][f"171|null|f{f}|p0{p0}"]["k3"]
            se = np.sqrt(max(ex * (1 - ex), 1e-12) / 20000)
            chk[f"f{f}|p0{p0}"] = {"mc": mc, "exact": ex, "ok": abs(mc - ex) <= 4 * se + 1e-4}
    for c in (2.8, 3.0):
        mc = design["sens"][f"S4|null|c{c}"]["clus4"]
        re_ = res["sens"][f"design|S4|null|c{c}"]["clus4"]
        se = np.sqrt(mc * (1 - mc) / 20000) * np.sqrt(2)
        chk[f"sens_c{c}"] = {"design_json": mc, "rerun": re_, "ok": abs(mc - re_) <= 4 * se}
    res["self_check"] = chk
    ok = all(v["ok"] for v in chk.values())
    res["self_check_ok"] = ok
    (out / "r10_recompute.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item()), encoding="utf-8")
    g, s = res["grid"], res["sens"]
    L = [f"self_check_ok {ok}", json.dumps(chk, default=lambda o: o.item()), "== G1 (exact Poisson-binomial) =="]
    for k, v in g.items():
        if isinstance(v, dict):
            L.append(f"{k:<36} " + " ".join(f"{a} {100 * b:.2f}" for a, b in v.items()))
        else:
            L.append(f"{k:<36} {v}")
    L.append("== sensitivity (s31 model) ==")
    for k, v in s.items():
        if isinstance(v, dict):
            L.append(f"{k:<40} unseen {v['n_units_unseen']} E {v['E_fail']:.3f} "
                     + " ".join(f"cl{j} {100 * v[f'clus{j}']:.2f}" for j in (3, 4, 5))
                     + " | " + " ".join(f"xr{j} {100 * v[f'xrow{j}']:.2f}" for j in (3, 4)))
        else:
            L.append(f"{k:<40} {v}")
    L.append("== D6 E3 false witness, not opened ==")
    for k, v in res["d6"].items():
        L.append(f"{k:<20} {100 * v['p']:.3f} % (se {100 * v['mcse']:.3f})")
    (out / "r10_recompute.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
