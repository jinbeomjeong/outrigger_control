"""Ed. 7 stop condition for probe-seen units (spec v7 rev 3, 6.2 sensitivity and 6.3 Q7-U1).
stats-design-expert, 2026-11-24, design only (no ed. 7 results exist or are read).

Part S (sensitivity, model of stats_v7/s31_confirm_rules.py sens_sim, frame of r10 ACTUAL_FRAME):
  4 judged settings x 16 rows (46 units/setting, 10 probe-seen/setting -> 40 seen, 144 unseen).
  Unit fails vs V0 iff c + e < 0, e = sqrt(rho_e) z_row + sqrt(1 - rho_e) eps_phase (rho_e 0.5).
  The probe draw IS the main-run draw for seen units (deterministic harness): a seen failure is
  known at seal; the rate below is the probability that the seal-time table shows the stop.
  Rules (each is "edition sensitivity stage not passed"):
    J   current 6.2 judged rule on unseen phases: a (setting,row) with >= 2 unseen failures, or
        isolated unseen failures summed over the 4 settings > 4.
    A   any seen unit fails (ed. 6 6.2 precedent wording), reported alone and as A|J.
    C1  >= 2 seen units fail, reported as C1|J.
    B   merged stop-only: seen failures are added to the phase counts of the cluster rule
        (>= 2 failing phases seen+unseen in a (setting,row), or rows with exactly 1 failing phase
        summed over the 4 settings > 4); seen passes add nothing. B contains J by construction.
  Harm scenarios (detection): s31 ones (R12 row one setting / all settings), R15 row (all seen),
  spread defect (each (setting,row) defective with pi, its phases fail with q).
Part D (6.3 (da') probe D 12 keys x VBM, V0-relative verdict; r10 G1 model):
  168 counted G1 lines (one unused V0-pass offset per eligible non-U832 cluster, p = draw-averaged
  min(1, f p_margin + p0)) plus the D VBM lines that are V0 opportunities (p proxy = cluster mean
  p_margin of the pool rows). Within-cluster Gaussian copula rho_c between the D line and the G1
  line of the same cluster. Rules: JG count168 > 3; AD = JG | any D line fails; BD = count over
  168 + D lines > 3.
Outputs (argv[1]): q10_stopcond.json / .txt. stdout: status only.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import norm

SEED = 20261114
STATS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\stats_v7")
REPO = Path(r"C:\workspace\outrigger_control")
D_BLOB = "3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json"

# (phases, probe-seen) per row, judged settings (sens_keys_ed7.json, VBMslow; same for all 4)
FRAME = [(4, 1), (2, 0), (2, 1), (2, 1), (2, 0), (2, 0), (2, 1), (2, 0), (2, 0), (2, 2),
         (4, 0), (4, 1), (4, 1), (4, 1), (4, 1), (4, 0)]
ROWS = ["R12", "top-FL-Fs0", "top-FL-Fs8", "top-FR-Fs4", "top-RL-Fs4", "top-RR-Fs4",
        "bottom-FL-Fs4", "bottom-RR-Fs4", "R14", "R15", "R16", "S1", "S4", "S5", "S7", "R2ra"]
S_SET = 4
K_SENS = 4
U832 = {("bottom", 2.0, "ready", "FL", "RE1bF"), ("bottom", 2.0, "ready", "FR", "RE1bF"),
        ("bottom", 4.0, "ready", "FR", "RE1bF")}


def sens_sim(rng, c, n_sim, rho_e=0.5, harm=None):
    nrow = len(FRAME)
    pmax = 4
    z = rng.standard_normal((n_sim, S_SET, nrow, 1))
    eps = rng.standard_normal((n_sim, S_SET, nrow, pmax))
    fail = (c + np.sqrt(rho_e) * z + np.sqrt(1 - rho_e) * eps) < 0
    if harm is not None:
        kind = harm[0]
        if kind == "row":                      # ("row", row_name, settings ('one'|'all'), q)
            r = ROWS.index(harm[1])
            sets = [0] if harm[2] == "one" else list(range(S_SET))
            for s in sets:
                fail[:, s, r, :] |= rng.random((n_sim, pmax)) < harm[3]
        elif kind == "rows_all":               # ("rows_all", [row names], q)
            for name in harm[1]:
                r = ROWS.index(name)
                fail[:, :, r, :] |= rng.random((n_sim, S_SET, pmax)) < harm[2]
        elif kind == "spread":                 # ("spread", pi, q)
            bad = rng.random((n_sim, S_SET, nrow, 1)) < harm[1]
            fail |= bad & (rng.random((n_sim, S_SET, nrow, pmax)) < harm[2])
    seen_m = np.zeros((nrow, pmax), bool)
    valid = np.zeros((nrow, pmax), bool)
    for i, (p, s) in enumerate(FRAME):
        valid[i, :p] = True
        seen_m[i, :s] = True
    unseen_m = valid & ~seen_m
    f_unseen = (fail & unseen_m).sum(3)                       # (n, S, row)
    f_seen = (fail & seen_m).sum(3)
    f_all = f_unseen + f_seen
    n_unseen = unseen_m.sum(1)
    # J: current rule on unseen phases
    clus_u = ((f_unseen >= 2) & (n_unseen[None, None, :] >= 2)).any((1, 2))
    iso_u = (f_unseen == 1).sum((1, 2))
    J = clus_u | (iso_u > K_SENS)
    seen_tot = f_seen.sum((1, 2))
    A = seen_tot >= 1
    C1 = seen_tot >= 2
    clus_a = (f_all >= 2).any((1, 2))
    iso_a = (f_all == 1).sum((1, 2))
    B = clus_a | (iso_a > K_SENS)
    out = {"J": J.mean(), "A": A.mean(), "A|J": (A | J).mean(), "C1|J": (C1 | J).mean(),
           "B": B.mean(), "E_seen_fail": seen_tot.mean(), "E_unseen_fail": f_unseen.sum((1, 2)).mean(),
           "B_contains_J": bool((~J | B).all())}
    return {k: (float(v) if not isinstance(v, bool) else v) for k, v in out.items()}


def mcse(p, n):
    return float(np.sqrt(max(p * (1 - p), 1e-12) / n))


def part_s(rng):
    res = {"frame_rows": ROWS, "frame": FRAME, "seen_units": S_SET * sum(s for _, s in FRAME),
           "unseen_units": S_SET * sum(p - s for p, s in FRAME), "null": {}, "harm": {}}
    n_null = 40000
    for c in (2.5, 2.8, 3.0, 3.5):
        r = sens_sim(rng, c, n_null)
        r["mcse_max"] = mcse(max(r["A|J"], 0.5 if r["A|J"] > 0.5 else r["A|J"]), n_null)
        res["null"][f"c{c}"] = r
    # self checks: rho_e 0 -> A analytic; c = 9 -> ~0 everything
    r0 = sens_sim(rng, 2.8, n_null, rho_e=0.0)
    an = 1 - (1 - norm.cdf(-2.8)) ** res["seen_units"]
    res["check_A_rho0"] = {"mc": r0["A"], "analytic": float(an),
                           "ok": abs(r0["A"] - an) <= 4 * mcse(an, n_null)}
    n_h = 20000
    scen = {
        "R12_one_q0.5": ("row", "R12", "one", 0.5), "R12_one_q1.0": ("row", "R12", "one", 1.0),
        "R12_all_q0.25": ("row", "R12", "all", 0.25), "R12_all_q0.5": ("row", "R12", "all", 0.5),
        "R15_one_q0.5": ("row", "R15", "one", 0.5), "R15_one_q1.0": ("row", "R15", "one", 1.0),
        "S4_one_q0.5": ("row", "S4", "one", 0.5),
        "dwell_rows_all_q0.25": ("rows_all", ["R12", "S4", "S7"], 0.25),
    }
    for pi in (0.02, 0.05, 0.10, 0.20):
        for q in (0.5, 1.0):
            scen[f"spread_pi{pi}_q{q}"] = ("spread", pi, q)
    for name, h in scen.items():
        res["harm"][name] = sens_sim(rng, 3.0, n_h, harm=h)
    res["n_null"], res["n_harm"] = n_null, n_h
    return res


def load_g1():
    cl = defaultdict(list)
    with (STATS / "s30_pool_opp_p.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if float(r["p_np"]) > 0:
                continue
            cl[(r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"])].append(float(r["p_margin"]))
    runs = {}
    with (STATS / "s30_pool_runs.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            runs[(r["level"], float(r["fs_kN"]), r["timing"], r["leg"], r["event"], float(r["offset_s"]))] = r
    return cl, runs


def load_d():
    txt = subprocess.run(["git", "-C", str(REPO), "show", D_BLOB], capture_output=True, text=True,
                         check=True).stdout
    d = json.loads(txt)
    out = []
    for j in d["jobs"]:
        t = j["job"]["twin"]
        out.append((t["level"], float(t["fs_kN"]), t["timing"], t["leg"], t["event"], float(j["job"]["offset_s"])))
    return out


def part_d(rng):
    cl, runs = load_g1()
    keys168 = sorted(k for k in cl if k not in U832)
    dl = load_d()
    info = []
    d_p, d_cl = [], []
    for k in dl:
        r = runs.get(k)
        ck = k[:5]
        row = {"key": "|".join(map(str, k)), "in_runs": r is not None,
               "v0_pass": None if r is None else r["v0_pass"] == "True",
               "used_ed6": None if r is None else r["used_ed6"] == "True",
               "cluster_in_g1": ck in keys168,
               "cluster_mean_p_margin": float(np.mean(cl[ck])) if ck in cl else None}
        info.append(row)
        if row["v0_pass"] and ck in cl:
            d_p.append(row["cluster_mean_p_margin"])
            d_cl.append(keys168.index(ck) if ck in keys168 else -1)
    res = {"d_lines": info, "d_opportunity_lines": len(d_p), "null": {}, "harm": {}}
    n = 60000
    ncl = len(keys168)
    g1_pm = [np.array(cl[k]) for k in keys168]
    d_p = np.array(d_p)
    d_cl = np.array(d_cl)

    def sim(f, p0, rho_c, harm=None, n_sim=n):
        pick_p = np.stack([np.minimum(1.0, f * pm[rng.integers(len(pm), size=n_sim)] + p0) for pm in g1_pm], 1)
        zc = rng.standard_normal((n_sim, ncl))
        zg = np.sqrt(rho_c) * zc + np.sqrt(1 - rho_c) * rng.standard_normal((n_sim, ncl))
        g_fail = zg < norm.ppf(np.clip(pick_p, 1e-15, 1 - 1e-15))
        pd = np.minimum(1.0, f * d_p + p0)
        zc_d = np.where(d_cl[None, :] >= 0, zc[:, np.maximum(d_cl, 0)], rng.standard_normal((n_sim, d_p.size)))
        zd = np.sqrt(rho_c) * zc_d + np.sqrt(1 - rho_c) * rng.standard_normal((n_sim, d_p.size))
        d_fail = zd < norm.ppf(np.clip(pd, 1e-15, 1 - 1e-15))[None, :]
        if harm is not None:
            pi_c, q = harm
            bad = rng.random((n_sim, ncl)) < pi_c
            g_fail |= bad & (rng.random((n_sim, ncl)) < q)
            bad_d = np.where(d_cl[None, :] >= 0, bad[:, np.maximum(d_cl, 0)], rng.random((n_sim, d_p.size)) < pi_c)
            d_fail |= bad_d & (rng.random((n_sim, d_p.size)) < q)
        g = g_fail.sum(1)
        dd = d_fail.sum(1)
        JG = g > 3
        return {"JG": float(JG.mean()), "AD": float((JG | (dd >= 1)).mean()),
                "BD": float(((g + dd) > 3).mean()), "P_any_D": float((dd >= 1).mean())}

    for f in (1, 3):
        for p0 in (0.0, 0.005, 0.01, 0.017):
            for rho in (0.0, 0.9):
                res["null"][f"f{f}|p0{p0}|rho{rho}"] = sim(f, p0, rho)
    for pi_c in (0.02, 0.05):
        for q in (0.6, 1.0):
            res["harm"][f"pi{pi_c}|q{q}"] = sim(1, 0.005, 0.5, harm=(pi_c, q), n_sim=n // 2)
    res["n_null"], res["n_harm"] = n, n // 2
    return res


def main() -> int:
    out = Path(sys.argv[1])
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED, "S": part_s(rng), "D": part_d(rng)}
    # cross-check J against r10 (actual frame, same model): c2.8 2.23 %, c3.0 0.95 %
    r10 = {"c2.8": 0.0223, "c3.0": 0.0095}
    chk = {k: {"J": res["S"]["null"][k]["J"], "r10": v,
               "ok": abs(res["S"]["null"][k]["J"] - v) <= 4 * np.sqrt(2) * mcse(v, 20000)} for k, v in r10.items()}
    chk["A_rho0"] = res["S"]["check_A_rho0"]
    chk["B_contains_J"] = {"ok": all(v["B_contains_J"] for v in res["S"]["null"].values())}
    res["self_check"] = chk
    ok = all(v["ok"] for v in chk.values())
    res["self_check_ok"] = ok
    (out / "q10_stopcond.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                                           encoding="utf-8")
    L = [f"self_check_ok {ok}", json.dumps(chk, default=lambda o: o.item() if hasattr(o, 'item') else str(o)),
         f"== S: seen {res['S']['seen_units']} unseen {res['S']['unseen_units']} (null n {res['S']['n_null']}, harm n {res['S']['n_harm']}) =="]
    for sec in ("null", "harm"):
        for k, v in res["S"][sec].items():
            L.append(f"{sec:<5} {k:<24} J {100*v['J']:6.2f} | A {100*v['A']:6.2f} | A|J {100*v['A|J']:6.2f} | "
                     f"C1|J {100*v['C1|J']:6.2f} | B {100*v['B']:6.2f} | E_seen {v['E_seen_fail']:.3f} E_unseen {v['E_unseen_fail']:.3f}")
    L.append(f"== D: opportunity lines {res['D']['d_opportunity_lines']} ==")
    for r in res["D"]["d_lines"]:
        L.append("  " + json.dumps(r))
    for sec in ("null", "harm"):
        for k, v in res["D"][sec].items():
            L.append(f"{sec:<5} {k:<22} JG {100*v['JG']:6.2f} | AD {100*v['AD']:6.2f} | BD {100*v['BD']:6.2f} | anyD {100*v['P_any_D']:6.2f}")
    (out / "q10_stopcond.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
