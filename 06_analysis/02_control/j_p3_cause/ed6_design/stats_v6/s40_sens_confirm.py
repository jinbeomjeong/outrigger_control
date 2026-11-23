"""Ed. 6 sensitivity rows (6.2, k_sens), confirmation stage (6.3, grid 768 sample) and probe
component rule (4.2) - false-failure and power (stats-design-expert, 2026-11-23, design only).

Margin-scatter model (deterministic harness, phase = offset/eps realisation):
  each judged unit (setting s, row r, phase p) passes iff mu_sr + e_srp >= 0, in units of the
  phase scatter sd. e_srp = sqrt(rho_e) z_sr + sqrt(1 - rho_e) eps_srp (within-cluster phase
  correlation rho_e). Null "robust": every cluster at mu = c (worst case: all rows exactly at the
  null margin). Harm: chosen clusters at mu = m_bad.
  Phase-scatter anchors (public V0 values, v5_criteria.md:94-108): R12 min force 12.01-13.75 kN
  over 4 phases, R16 19.28-26.97, R2ra 24.1-25.6, S5 READY 85.1-85.2 s.
Unit frames:
  sensitivity subset per setting (spec 6.2 / Q6-2 proposal): R12 4, G4 g keys x 2 offsets,
  R14 2, R15 2, R16 4, S1 4, S4 4, S5 4, S7 4, R2ra 4; 4 settings. Probe-seen units (D0 8 keys,
  spec 4.2, all 4 sensitivity plants are probe plants): R12 o0.0, 3 G4 keys at offset 0,
  R15 both phases, S5 e0.0, S1 e0.003.
  grid 768 (s01_grid_frame.csv): 672 unique runs = 192 clusters (key x event), 48 clusters with
  2 offsets and 144 with 4 offsets.
Rules:
  count(k): fail iff failing unseen units > k
  clus(k): fail iff some cluster has >= 2 failing unseen phases (2-phase clusters: both) or
           isolated single-phase failures > k
  zero: fail iff any failing unit (v5_criteria 10 grid rule)
Writes s40_sens_confirm.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
SEED = 20261114
N_SIM = 20000


def sens_frame(g_keys: int) -> list[tuple[int, int]]:
    """(n_phases, n_seen) per cluster for ONE setting."""
    rows = [(4, 1)]                                   # R12, o0.0 seen
    rows += [(2, 1)] * min(3, g_keys) + [(2, 0)] * max(0, g_keys - 3)   # G4 keys
    rows += [(2, 0), (2, 2), (4, 0), (4, 1), (4, 0), (4, 1), (4, 0), (4, 0)]
    # R14, R15 (both seen), R16, S1 (1 seen), S4, S5 (1 seen), S7, R2ra
    return rows


def simulate(frame, c, rho_e, n_sim, rng, harm=None, m_bad=0.0, k_list=(0, 1, 2, 3, 4, 6, 8)):
    """frame: list of (n_phases, n_seen); harm: index list of clusters set to m_bad."""
    ncl = len(frame)
    pmax = max(p for p, _ in frame)
    mu = np.full(ncl, c, dtype=float)
    if harm is not None:
        mu[list(harm)] = m_bad
    z = rng.standard_normal((n_sim, ncl, 1))
    eps = rng.standard_normal((n_sim, ncl, pmax))
    e = np.sqrt(rho_e) * z + np.sqrt(1 - rho_e) * eps
    fail = (mu[None, :, None] + e) < 0
    valid = np.zeros((ncl, pmax), bool)
    for i, (p, s) in enumerate(frame):
        valid[i, s:p] = True                           # unseen phases only
    fail &= valid[None]
    nf_cl = fail.sum(2)
    tot = nf_cl.sum(1)
    n_unseen = np.array([p - s for p, s in frame])
    clustered = (nf_cl >= 2) & (n_unseen[None, :] >= 2)
    iso = tot - (nf_cl * clustered).sum(1)
    anyclus = clustered.any(1)
    res = {"zero": float((tot > 0).mean()), "E_fail_units": float(tot.mean())}
    for k in k_list:
        res[f"count{k}"] = float((tot > k).mean())
        res[f"clus{k}"] = float((anyclus | (iso > k)).mean())
    return res


def sens_block(rng) -> dict:
    out = {}
    for g in (3, 7, 14):
        one = sens_frame(g)
        frame = one * 4                                # 4 settings, clusters independent
        n_unseen = sum(p - s for p, s in frame)
        blk = {"n_clusters": len(frame), "n_unseen_units": n_unseen,
               "n_seen_units": sum(s for _, s in frame), "null": {}, "power": {}}
        for c in (2.0, 2.5, 3.0, 3.5):
            for rho in (0.0, 0.5, 0.8):
                blk["null"][f"c{c}|rho{rho}"] = simulate(frame, c, rho, N_SIM, rng)
        # harm scenarios at c = 3, rho 0.5
        r16 = 1 + g + 2                                # index of R16 in setting 0
        scen = {
            "D1_one_4phase_row_one_setting": [r16],
            "D3_one_4phase_row_all_settings": [r16 + j * len(one) for j in range(4)],
            "D2_all_rows_one_setting": list(range(len(one))),
        }
        for name, idx in scen.items():
            for mb in (1.0, 0.0, -1.0):
                blk["power"][f"{name}|mbad{mb}"] = simulate(frame, 3.0, 0.5, N_SIM // 2, rng,
                                                            harm=idx, m_bad=mb)
        out[f"G4_{g}"] = blk
    return out


def grid_block(rng) -> dict:
    out = {}
    designs = {"Da_192x1": [(1, 0)] * 192, "Db_192x2": [(2, 0)] * 192,
               "Dc_all_672": [(2, 0)] * 48 + [(4, 0)] * 144, "Dd_96x2": [(2, 0)] * 96}
    for name, frame in designs.items():
        blk = {"n_runs": sum(p for p, _ in frame), "null": {}, "power": {}}
        for c in (2.5, 3.0, 3.5, 4.0):
            for rho in (0.5, 0.8):
                blk["null"][f"c{c}|rho{rho}"] = simulate(frame, c, rho, N_SIM // 2, rng,
                                                         k_list=(0, 1, 2))
        for frac in (0.01, 0.02, 0.05, 0.10):
            nh = max(1, int(round(frac * len(frame))))
            for mb in (0.0, -1.0):
                idx = rng.choice(len(frame), nh, replace=False)
                blk["power"][f"frac{frac}|mbad{mb}"] = simulate(
                    frame, 3.5, 0.5, N_SIM // 4, rng, harm=idx, m_bad=mb, k_list=(0, 1, 2))
        out[name] = blk
    return out


def probe_block() -> dict:
    """P(component needed on a fraction pi of population units shows no effect on probe)."""
    out = {}
    for pi in (0.01, 0.02, 0.05, 0.10, 0.20):
        out[f"pi{pi}"] = {"units_indep_40": float((1 - pi) ** 40),
                          "key_property_8": float((1 - pi) ** 8),
                          "plant_property_5": float((1 - pi) ** 5)}
    # chance that two equally good arms differ (arm without X has >= 1 more failing unit)
    from scipy.stats import binom
    for p in (0.01, 0.02, 0.05):
        n = 40
        pm = binom.pmf(np.arange(n + 1), n, p)
        diff = float(sum(pm[i] * pm[j] for i in range(n + 1) for j in range(n + 1) if i > j))
        out[f"chance_keep_p{p}"] = diff
    return out


def self_checks(rng) -> dict:
    chk = {}
    frame = [(1, 0)] * 100
    r = simulate(frame, 2.0, 0.0, 40000, rng)
    an = 1.0 - (1.0 - norm.cdf(-2.0)) ** 100
    chk["zero_rule_indep"] = {"mc": r["zero"], "analytic": float(an),
                              "ok": abs(r["zero"] - an) < 4 * np.sqrt(an * (1 - an) / 40000)}
    r2 = simulate([(4, 0)] * 10, 50.0, 0.5, 2000, rng)
    chk["huge_margin_no_fail"] = r2["zero"] == 0.0
    r3 = simulate([(4, 0)] * 10, -50.0, 0.5, 2000, rng)
    chk["neg_margin_all_fail"] = r3["clus8"] == 1.0
    chk["ok"] = bool(chk["zero_rule_indep"]["ok"] and chk["huge_margin_no_fail"]
                     and chk["neg_margin_all_fail"])
    return chk


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "n_sim": N_SIM, "self_checks": self_checks(rng),
           "sensitivity": sens_block(rng), "grid": grid_block(rng), "probe": probe_block()}
    (HERE / "s40_sens_confirm.json").write_text(
        json.dumps(out, indent=1, default=lambda o: o.item()), encoding="utf-8")
    L = [f"self_checks {out['self_checks']}"]
    for g, blk in out["sensitivity"].items():
        L.append(f"== sensitivity {g}: clusters {blk['n_clusters']}, unseen units "
                 f"{blk['n_unseen_units']}, seen {blk['n_seen_units']} ==")
        for k, v in blk["null"].items():
            L.append(f" null {k:<12} E[f] {v['E_fail_units']:.3f} zero {100*v['zero']:5.1f} "
                     + " ".join(f"cnt{j} {100*v[f'count{j}']:5.1f}" for j in (1, 2, 3, 4))
                     + " | " + " ".join(f"cl{j} {100*v[f'clus{j}']:5.1f}" for j in (0, 1, 2, 3)))
        for k, v in blk["power"].items():
            L.append(f" pow  {k:<40} zero {100*v['zero']:5.1f} "
                     + " ".join(f"cnt{j} {100*v[f'count{j}']:5.1f}" for j in (1, 2, 3, 4))
                     + " | " + " ".join(f"cl{j} {100*v[f'clus{j}']:5.1f}" for j in (0, 1, 2, 3)))
    for d, blk in out["grid"].items():
        L.append(f"== grid {d}: runs {blk['n_runs']} ==")
        for k, v in blk["null"].items():
            L.append(f" null {k:<12} E[f] {v['E_fail_units']:.3f} zero {100*v['zero']:5.1f} "
                     f"cnt1 {100*v['count1']:5.1f} cl0 {100*v['clus0']:5.1f} cl1 {100*v['clus1']:5.1f}")
        for k, v in blk["power"].items():
            L.append(f" pow  {k:<18} zero {100*v['zero']:5.1f} cnt1 {100*v['count1']:5.1f} "
                     f"cl0 {100*v['clus0']:5.1f} cl1 {100*v['clus1']:5.1f}")
    L.append(f"== probe == {json.dumps(out['probe'])}")
    (HERE / "s40_sens_confirm.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = bool(out["self_checks"]["ok"])
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
