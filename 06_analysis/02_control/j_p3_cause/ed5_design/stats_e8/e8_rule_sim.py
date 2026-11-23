"""Erratum 8 design: false-failure rate and power of revised 6.3.7 (2)(3) rules (T-JR-12b, ed. 5).

Design-only simulation (stats-design-expert, 2026-11-23). No VBK output is read; inputs are
counts from the VBK0 A/A stop evidence (hard-coded below with sources).

Pair structure (judged set at run 606f8713, VBK0 classification):
  167 cases x 2 blocks (b1 seed 40, b2 seed 41) = 334 pairs; cell = leg x phase, phase tau_C 84 /
  tau_R 83 cases (aa_baserate.json "12b_vbk0" n). 327 opportunity pairs (VBK0 READY reached),
  7 VBK0-unreached pairs (aa_inspect.json "categories", "no_ready_b1/b2"). No trigger-none,
  pre-trigger fallback or unlatched pairs.

Null model (rev 6 harmless):
  - A pair whose VBK commands equal VBK0 commands gives an identical line (deterministic plant,
    same seed, same fault plan). A pair "diverges" with probability c (command change).
  - A diverged pair's VBK outcome is a fresh draw from the case's VBK0 outcome distribution:
    stall (no READY) with probability q_i, q_i ~ Beta(a, b) per cell, posterior given the case's
    two observed VBK0 outcomes (k_i of 2 stalled). Cross-seed A/A is the fully diverged limit.
  - Both reached and diverged: d = READY_VBK - READY_VBK0 exceeds +30 s with probability r2 and
    -30 s with probability r2 (symmetric).
Harm model: each opportunity pair in the targeted cells independently gets an extra VBK READY loss
with probability delta (on top of the null).

Rules (fail = gate fails):
  A_k   : B2 + B3 > k                     (fixed allowance on the VBK-worse count)
  A_sep : B3 > k3 or B2 > k2
  A_cell: B_tauC > kC or B_tauR > kR
  B     : one-sided exact sign test on (B, C), B = B2 + B3 (VBK worse), C = C2 + C3 (VBK0 worse),
          fail if P(Bin(B + C, 1/2) >= B) <= alpha (alpha 0.05)
  B_sep : sign tests on (B3, C3) and (B2, C2), alpha 0.025 each, fail if either
  B_cell: sign tests per phase cell, alpha 0.025 each
  H     : B or (B > k_cap)                (sign test plus an absolute cap)
Writes e8_rule_sim.json next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist
from scipy.stats import binom

HERE = Path(__file__).resolve().parent
SEED = 20261123
N_SIM = 20_000

# ---- observed counts (sources in module docstring) -------------------------------------------
N_CASE = {"tau_C": 84, "tau_R": 83}
# stalled-case pattern: (cell, k_i, which blocks stalled)
STALL_CASES = [
    ("tau_C", 2, (1, 1)),  # L2|g6|56|ref|J2|top|Fs0
    ("tau_C", 2, (1, 1)),  # L2|g8|30|slope|rpB|top|4.0|RR|raised|140.0
    ("tau_C", 1, (1, 0)),  # L2|g6|52|ref|J1|top|Fs0 (b1 stalled)
    ("tau_C", 1, (0, 1)),  # L2|ref|16|J1|B|0,0 (b2 stalled)
    ("tau_R", 1, (1, 0)),  # L2|g6|59|ref|J2|bottom|Fs4 (b1 stalled)
]
AA_DREADY_GT30 = (1, 162)  # both-reached A/A pairs with |dREADY| > 30 s (L2|g6|61, tau_R)
C_DRY = (20, 158)          # dry c: changed opportunity pairs (cdry_a1/judge/dry_c.json)


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    return float(beta_dist.ppf(conf + (1 - conf) / 2, k + 1, n - k)) if k < n else 1.0


def mom_rho(cell: str) -> tuple[float, float]:
    """Line stall rate p and beta-binomial (n=2) rho by moments for one cell."""
    n = N_CASE[cell]
    ks = np.zeros(n)
    j = 0
    for c, k, _ in STALL_CASES:
        if c == cell:
            ks[j] = k
            j += 1
    p = ks.mean() / 2
    var_k = ks.var(ddof=1)
    rho = var_k / (2 * p * (1 - p)) - 1.0
    return float(p), float(rho)


def build_pairs(p_cell: dict, rho_cell: dict) -> dict:
    """Per-pair arrays: cell (0 tau_C, 1 tau_R), VBK0 reached, posterior stall prob, stall-prone."""
    cells, reached, post, prone = [], [], [], []
    for ci, cell in enumerate(("tau_C", "tau_R")):
        p, rho = p_cell[cell], rho_cell[cell]
        if rho <= 0:
            ab = None
        else:
            ab = 1.0 / rho - 1.0
        stalled = [s for s in STALL_CASES if s[0] == cell]
        patterns = [s[2] for s in stalled] + [(0, 0)] * (N_CASE[cell] - len(stalled))
        for pat in patterns:
            k = sum(pat)
            if ab is None:
                pi = p
            else:
                a, b = p * ab, (1 - p) * ab
                pi = (a + k) / (a + b + 2)
            for blk in (0, 1):
                cells.append(ci)
                reached.append(pat[blk] == 0)
                post.append(pi)
                prone.append(k > 0)
    return {"cell": np.array(cells), "reached": np.array(reached), "post": np.array(post),
            "prone": np.array(prone)}


def simulate(pairs: dict, c_gen: float, c_prone: float, r2: float, delta: float,
             harm_cells: tuple[int, ...], fix: float, rng: np.random.Generator,
             n_sim: int = N_SIM) -> dict:
    n = pairs["cell"].size
    c = np.where(pairs["prone"], c_prone, c_gen)
    div = rng.random((n_sim, n)) < c
    vbk_stall = rng.random((n_sim, n)) < pairs["post"]
    reached0 = pairs["reached"][None, :]
    # (3) direction: VBK0 reached, VBK stalled
    b3 = div & reached0 & vbk_stall
    # VBK0 stalled, VBK reached (null) or fixed by rev 6 (fix scenario)
    c3 = div & ~reached0 & ~vbk_stall
    if fix > 0:
        c3 |= (~reached0) & (rng.random((n_sim, n)) < fix)
    both = div & reached0 & ~vbk_stall
    u = rng.random((n_sim, n))
    b2 = both & (u < r2)
    c2 = both & (u > 1 - r2)
    if delta > 0:
        tgt = np.isin(pairs["cell"], harm_cells)[None, :] & reached0
        harm = tgt & (rng.random((n_sim, n)) < delta)
        b3 = b3 | harm
        b2 = b2 & ~harm
        c2 = c2 & ~harm
    out = {"B3": b3.sum(1), "C3": c3.sum(1), "B2": b2.sum(1), "C2": c2.sum(1)}
    for ci, name in ((0, "C"), (1, "R")):
        m = (pairs["cell"] == ci)[None, :]
        out[f"B_{name}"] = ((b3 | b2) & m).sum(1)
        out[f"Cc_{name}"] = ((c3 | c2) & m).sum(1)
    return out


def sign_fail(b: np.ndarray, c: np.ndarray, alpha: float) -> np.ndarray:
    m = b + c
    p = np.where(b > 0, binom.sf(b - 1, m, 0.5), 1.0)
    return p <= alpha


def rules(o: dict, k_list, k_cap: int) -> dict:
    B = o["B2"] + o["B3"]
    C = o["C2"] + o["C3"]
    res = {}
    for k in k_list:
        res[f"A_k{k}"] = B > k
    for k3, k2 in ((2, 1), (3, 1), (4, 2), (5, 3), (6, 2), (6, 3), (7, 3), (8, 3)):
        res[f"A_sep_k3{k3}_k2{k2}"] = (o["B3"] > k3) | (o["B2"] > k2)
    for kc, kr in ((4, 2), (5, 3), (6, 2), (6, 3), (7, 2), (7, 3), (8, 3), (10, 4)):
        res[f"A_cell_kC{kc}_kR{kr}"] = (o["B_C"] > kc) | (o["B_R"] > kr)
    sb = sign_fail(B, C, 0.05)
    res["B_sign_a05"] = sb
    res["B_sign_a10"] = sign_fail(B, C, 0.10)
    res["B_sep_a025"] = sign_fail(o["B3"], o["C3"], 0.025) | sign_fail(o["B2"], o["C2"], 0.025)
    res["B_cell_a025"] = (sign_fail(o["B_C"], o["Cc_C"], 0.025)
                          | sign_fail(o["B_R"], o["Cc_R"], 0.025))
    for d in (3, 4, 5):
        res[f"D_diff_ge{d}"] = (B - C) >= d
    res[f"H_sign_or_B_gt{k_cap}"] = sb | (B > k_cap)
    res["H_sign_or_B_gt8"] = sb | (B > 8)
    res["H_sign_or_B_gt10"] = sb | (B > 10)
    return res


def self_checks(rng: np.random.Generator, pairs: dict) -> dict:
    chk = {}
    # c = 0: no discordance, all rules pass
    o = simulate(pairs, 0.0, 0.0, 0.05, 0.0, (0, 1), 0.0, rng, 2000)
    chk["c0_all_zero"] = bool(all((o[k] == 0).all() for k in ("B2", "B3", "C2", "C3")))
    # delta = 1: every opportunity pair fails -> power 1 for A_k10 and sign test
    o = simulate(pairs, 0.127, 0.127, 0.003, 1.0, (0, 1), 0.0, rng, 2000)
    r = rules(o, [10], 10)
    chk["delta1_power_A_k10"] = float(r["A_k10"].mean())
    chk["delta1_power_sign"] = float(r["B_sign_a05"].mean())
    # analytic: homogeneous model (rho=0), c=1, r2=0 -> B3 ~ Binomial(n_C_reached, pC) +
    # Binomial(n_R_reached, pR); compare P(B3 > 6) with MC
    pc, pr = 6 / 168, 1 / 166
    ph = build_pairs({"tau_C": pc, "tau_R": pr}, {"tau_C": 0.0, "tau_R": 0.0})
    o = simulate(ph, 1.0, 1.0, 0.0, 0.0, (0, 1), 0.0, rng, 40_000)
    nC = int((ph["reached"] & (ph["cell"] == 0)).sum())
    nR = int((ph["reached"] & (ph["cell"] == 1)).sum())
    pmf = np.convolve(binom.pmf(np.arange(nC + 1), nC, pc), binom.pmf(np.arange(nR + 1), nR, pr))
    exact = float(pmf[7:].sum())
    mc = float((o["B3"] > 6).mean())
    se = float(np.sqrt(exact * (1 - exact) / 40_000))
    chk["analytic_P_B3_gt6"] = {"exact": exact, "mc": mc, "se": se,
                                "ok": abs(mc - exact) < 4 * se}
    chk["ok"] = (chk["c0_all_zero"] and chk["delta1_power_A_k10"] == 1.0
                 and chk["delta1_power_sign"] == 1.0 and chk["analytic_P_B3_gt6"]["ok"])
    return chk


def main(n_sim: int = N_SIM) -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    pC, rhoC = mom_rho("tau_C")
    pR, _ = mom_rho("tau_R")
    rho_pool = 0.5716654297399295  # aa_baserate.json aa_mc.rho (pooled b1/b2 cases)
    c_pt = C_DRY[0] / C_DRY[1]
    c_up = cp_upper(*C_DRY)
    r2_pt = 0.5 * AA_DREADY_GT30[0] / AA_DREADY_GT30[1]
    r2_up = 0.5 * cp_upper(*AA_DREADY_GT30)
    pC_up = cp_upper(8, 248)   # tau_C VBK0 lines b1+b2+cdry (aa_falsefail.json)
    pR_up = cp_upper(1, 246)
    base = build_pairs({"tau_C": pC, "tau_R": pR}, {"tau_C": rhoC, "tau_R": rho_pool})
    upper = build_pairs({"tau_C": pC_up, "tau_R": pR_up}, {"tau_C": rhoC, "tau_R": rho_pool})
    homog = build_pairs({"tau_C": pC, "tau_R": pR}, {"tau_C": 0.0, "tau_R": 0.0})
    scen = {
        "F0_c_dry": (base, c_pt, c_pt, r2_pt),
        "F1_c_dry_up": (base, c_up, c_up, r2_pt),
        "F2_c_dry_up_prone1": (base, c_up, 1.0, r2_pt),
        "F2u_c_dry_up_prone1_upper": (upper, c_up, 1.0, r2_up),
        "F2h_c_dry_up_prone1_rho0": (homog, c_up, 1.0, r2_pt),
        "F3_c1_point": (base, 1.0, 1.0, r2_pt),
        "F3h_c1_homog_rho0": (homog, 1.0, 1.0, r2_pt),
        "F4_c1_upper": (upper, 1.0, 1.0, r2_up),
        "F5_c05_point": (base, 0.5, 0.5, r2_pt),
    }
    k_list = list(range(0, 16))
    k_cap = 12
    deltas = [0.0, 0.0025, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07]
    out = {"seed": SEED, "n_sim": n_sim,
           "inputs": {"pC_line": pC, "rhoC_mom": rhoC, "pR_line": pR, "rho_pool": rho_pool,
                      "c_point": c_pt, "c_cp95_upper": c_up, "r2_point": r2_pt,
                      "r2_upper": r2_up, "pC_upper": pC_up, "pR_upper": pR_up,
                      "n_pairs": int(base["cell"].size),
                      "n_opportunity": int(base["reached"].sum()),
                      "post_by_k": {}},
           "self_checks": self_checks(rng, base), "scenarios": {}}
    for name, pr in (("base", base), ("upper", upper)):
        out["inputs"]["post_by_k"][name] = sorted({round(float(x), 5) for x in pr["post"]})
    harm_sets = {"all": (0, 1), "tau_R": (1,), "tau_C": (0,)}
    for sname, (pairs, cg, cp_, r2) in scen.items():
        sres = {"c_gen": cg, "c_prone": cp_, "r2": r2, "null_means": {}, "by_harm": {}}
        for hname, hcells in harm_sets.items():
            if hname != "all" and sname not in ("F0_c_dry", "F2_c_dry_up_prone1", "F3_c1_point"):
                continue
            rows = []
            for d in deltas:
                if hname != "all" and d == 0.0:
                    continue
                o = simulate(pairs, cg, cp_, r2, d, hcells, 0.0, rng, n_sim)
                if d == 0.0:
                    sres["null_means"] = {k: float(v.mean()) for k, v in o.items()}
                    sres["null_dist_B"] = np.bincount(o["B2"] + o["B3"], minlength=16)[:16]\
                        .tolist()
                r = rules(o, k_list, k_cap)
                rows.append({"delta": d, "expected_harm_pairs": d * int(
                    (np.isin(pairs["cell"], hcells) & pairs["reached"]).sum()),
                    "fail_rate": {k: float(v.mean()) for k, v in r.items()}})
            sres["by_harm"][hname] = rows
        # rev 6 fixes VBK0 stalls (masking check for sign tests), null otherwise and delta 2 %
        fx = []
        for fix in (0.5, 1.0):
            for d in (0.0, 0.02, 0.03):
                o = simulate(pairs, cg, cp_, r2, d, (0, 1), fix, rng, n_sim)
                r = rules(o, [7, 10], k_cap)
                fx.append({"fix": fix, "delta": d,
                           "fail_rate": {k: float(r[k].mean()) for k in
                                         ("A_k7", "A_k10", "B_sign_a05", "H_sign_or_B_gt10")}})
        sres["fix_masking"] = fx
        out["scenarios"][sname] = sres
    out["wall_s"] = round(time.time() - t0, 1)
    (HERE / "e8_rule_sim.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ok" if out["self_checks"]["ok"] else "self_check_failed", out["wall_s"])
    return 0 if out["self_checks"]["ok"] else 3


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else N_SIM))
