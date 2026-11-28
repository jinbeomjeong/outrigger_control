"""E-1 (READY delay) and E-2 (READY lost after declaration) expected counts and 97.5 % predictive
upper bounds for the v5 paper A-type rules (draft r11, section 4.2 'expected counts', fixed before
any A-type result exists). stats-design-expert, stats review 4, 2026-11-28.

Inputs (all public / stored before the A-type run; no A-type output is read):
  --inputs   v5paper_imua_stats/inputs.json (stats review 1; check runs A-v5 / A2 per-row table and
             436.8 H-1 READY records), sha256 prefix checked
  --h1       06_analysis/03_hydraulic/coupled/v5/resume_k1/h1_d1.jsonl (436.8 H-1 D-1), record items
             read: job.{setting,eps,d1.key}, d1.t_ready_s, d1.t_ready_limit_s, final_phase,
             values.probe_attitude_change_deg. No verdict / fail-item field is read.
  --las-dir  06_analysis/02_control/v5_rerun/las_k1 (436.8 H-3 U-3 stored files), record items
             read: id / key, t_ready_s, and for study D only rows.P3-6.limit_s (limit cross-check).
  --map      v5paper_imua_stats/u3_cluster_map_r1.csv (cluster 376 / resample_unit 284), sha checked

Model
  E-1  A-type first READY = 436.8 pair first READY + delay d. Delay pool = A-v5 check-run
       (A - R0) first-READY differences, V0 pool for V0 lines, VB pool (VB-eta + normal VB) for VB
       lines. Per replicate the check clusters (case x eta) are bootstrapped, then each sharing unit
       of the target bundle draws one cluster and one row delay; all its lines share that d.
       An 'explained E-1' line: pair READY <= limit (condition 1), d > limit - pair READY
       (signature (i)) and d <= cap (30 s V0, 45 s VB; condition 4).
       D-1 sharing unit = key (eps pair). U-3 sharing unit = cluster (main), resample_unit (sens.).
       U-3 line limit = rules 4.3 / s9_soil_slope.ready_limit_s: non-flat 120 s, flat with pad B on
       J1 / J2 / S1 100 s, other flat 90 s, derived from the key; g6 and C (120 s, not a judged or
       FLAG item) are a sensitivity only; g8 has no limit.
  E-2  Opportunity = 436.8 pair line with READY reached and probe_attitude_change_deg > 0.07
       (rules 4.2). Rate from the A-v5 check run: opportunity rows = R0 READY reached and R0
       probe change > 0.07; event = A reached READY and did not end in READY. Cluster level:
       event cluster share pi; within an event cluster each opportunity row is an event with q.
       Main: bootstrap of the check opportunity clusters (pi_b, q_b from the resample), then
       D-1 keys are event keys with pi_b and each of their opportunity rows fails with q_b.
       Sensitivities: Jeffreys beta-binomial, q pooled with A2 (6/10), VB-only clusters.
       P(signature holds | event) = 1 (upper side; A2 positives 5/5).
  OC   P(observed > upper) when the true delay pool is the fixed check pool scaled by s (E-1), with
       the cap (explained count) and without it (signature (i) count = explained + size exceeded),
       and for true (pi, q) grids (E-2). 2,000 / 4,000 draws.
Seed 20261114 (section seeds spawned from it), B = 4000.

Usage: python -I -B e1e2_expected.py --inputs <inputs.json> --h1 <h1_d1.jsonl> --las-dir <las_k1>
         --map <u3_cluster_map_r1.csv> --q2 <q2_result.json> --out <out.json>
Exit 0 = written, all self-checks pass; 1 = written, a self-check failed; 2 = input / sha error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20261114
B = 4000
CAP = {"V0": 30.0, "VB": 45.0}
OPP_DEG = 0.07
SOFT = ("J1", "J2", "S1")
EXPECT_SHA = {"inputs": "8ac93ff6", "h1": "412e5b36", "map": "baf8aaa6", "q2": "dd2bcd8d"}
U3_LIMIT_STUDIES = ("slope", "h6", "h9", "x426b", "D", "p3b")
U3_SENS_STUDIES = ("g6", "C")
U3_ALL = ("slope", "h6", "h9", "x426b", "D", "p3b", "g6", "C", "g8")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def q(a, levels=(2.5, 50, 97.5)):
    return [float(np.percentile(a, x)) for x in levels]


def summ(a) -> dict:
    """Mean with its MC standard error, 2.5/50/97.5 % quantiles, the 97.5 % upper bound and its MC
    band (empirical quantiles at 97.5 % +- 2 binomial SE of the quantile position, B draws)."""
    a = np.asarray(a, float)
    h = 2 * 100 * np.sqrt(0.975 * 0.025 / a.size)
    return {"mean": float(a.mean()), "mcse_mean": float(a.std(ddof=1) / np.sqrt(a.size)),
            "q2_5_50_97_5": q(a), "upper_97_5": float(np.percentile(a, 97.5)),
            "upper_mc_band": [float(np.percentile(a, 97.5 - h)), float(np.percentile(a, 97.5 + h))],
            "p_zero": float((a == 0).mean())}


# ---------------------------------------------------------------- pools
def delay_pools(rows: list[dict], inf_for_a_none: bool) -> dict:
    """Check-cluster delay pools per setting. inf_for_a_none: rows where R0 reached READY and A did
    not get d = +inf (never explained) instead of being dropped."""
    pools = {"V0": defaultdict(list), "VB": defaultdict(list)}
    for r in rows:
        s = "V0" if r["setting"] == "V0" else "VB"
        if r["delta"] is not None:
            pools[s][r["cluster"]].append(float(r["delta"]))
        elif inf_for_a_none and r["t_ready_R0"] is not None and r["t_ready_A"] is None:
            pools[s][r["cluster"]].append(float("inf"))
    return {k: [np.asarray(v) for v in d.values()] for k, d in pools.items()}


def e1_counts(units: list[list[float]], pool: list[np.ndarray], cap: float, rng, n_rep: int,
              boot: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """units: per sharing unit, the margins (limit - pair READY) of its eligible lines (>= 0).
    Returns per-replicate explained line counts and unit counts."""
    rows_c = np.empty(n_rep)
    unit_c = np.empty(n_rep)
    n_u = len(units)
    for b in range(n_rep):
        src = [pool[i] for i in rng.integers(0, len(pool), len(pool))] if boot else pool
        ci = rng.integers(0, len(src), n_u)
        d = np.array([src[i][rng.integers(0, len(src[i]))] for i in ci])
        hit = [int(((m < dd) & (dd <= cap)).sum()) for m, dd in zip(units, d, strict=True)]
        rows_c[b] = sum(hit)
        unit_c[b] = sum(1 for h in hit if h)
    return rows_c, unit_c


def legacy_q2(inp: dict) -> dict:
    """Exact replay of q2_sim.py section 2 for arm A-v5 (regression check of the published D-1 values)."""
    rng = np.random.default_rng(SEED)
    pools = delay_pools(inp["check"]["A-v5"]["rows"], inf_for_a_none=False)
    by_key = defaultdict(list)
    for x in inp["d1"]["recs"]:
        if x["t_ready"] is None or x["t_ready_limit"] is None:
            continue
        by_key[(x["setting"], x["key"])].append(x["t_ready_limit"] - x["t_ready"])
    out = {}
    for setting in ("V0", "VB"):
        keys = [k for k in by_key if k[0] == setting]
        pos = [np.asarray(by_key[k])[np.asarray(by_key[k]) >= 0] for k in keys]
        cl = pools[setting]
        cr = np.empty(B)
        for b in range(B):
            boot = [cl[i] for i in rng.integers(0, len(cl), len(cl))]
            ci = rng.integers(0, len(boot), len(pos))
            d = np.array([boot[i][rng.integers(0, len(boot[i]))] for i in ci])
            cr[b] = sum(int((p < dd).sum()) for p, dd in zip(pos, d, strict=True))
        out[setting] = q(cr)
    return out


# ---------------------------------------------------------------- U-3
def flat_of(study: str, key: str) -> tuple[bool, str, str]:
    """(flat, soil, pad) from the U-3 key (identifier formats of u3_cluster_map_r1.csv)."""
    f = key.split("|")
    if study in ("slope", "h6", "h9", "x426b", "D"):
        return f[4].split("@")[0] == "flat", f[1], f[2]
    if study == "p3b":
        if f[1] == "rigid":
            return f[2] == "0,0", "rigid", "B"
        return True, f[1], f[2]          # soil cases of s9_runs.soil_cases are flat
    raise ValueError(study)


def u3_limit(study: str, key: str) -> float | None:
    if study in U3_SENS_STUDIES:
        return 120.0
    if study == "g8":
        return None
    flat, soil, pad = flat_of(study, key)
    if not flat:
        return 120.0
    return 100.0 if (pad == "B" and soil in SOFT) else 90.0


def load_u3(las: Path) -> tuple[list[dict], dict]:
    lines, chk = [], {"D_limit_checked": 0, "D_limit_mismatch": [], "records_with_reuse_field": 0}
    for st in U3_ALL:
        for setting in ("V0", "VB"):
            obj = json.loads((las / f"u3_{st}_{setting}.json").read_text(encoding="utf-8"))
            for r in obj.get("records") or obj.get("results") or []:
                key = str(r.get("id") if "id" in r else r.get("key"))
                t = r.get("t_ready_s")
                t = float(t) if isinstance(t, (int, float)) and not isinstance(t, bool) else None
                if "reuse" in r or "reuse" in (r.get("v5") or {}):
                    chk["records_with_reuse_field"] += 1
                lim = u3_limit(st, key)
                if st == "D":
                    stored = ((r.get("rows") or {}).get("P3-6") or {}).get("limit_s")
                    chk["D_limit_checked"] += 1
                    if stored is None or abs(float(stored) - lim) > 1e-9:
                        chk["D_limit_mismatch"].append(key)
                lines.append({"study": st, "setting": setting, "key": key, "t_ready": t, "limit": lim})
    return lines, chk


def e1_u3(lines, cmap, umap, pools, rng, studies, unit_col) -> dict:
    out = {}
    for setting in ("V0", "VB"):
        sel = [x for x in lines if x["setting"] == setting and x["study"] in studies]
        n_lines = len(sel)
        elig = [x for x in sel if x["t_ready"] is not None and x["limit"] is not None
                and x["limit"] - x["t_ready"] >= 0]
        units = defaultdict(list)
        study_of_unit = defaultdict(set)
        for x in elig:
            u = (cmap if unit_col == "cluster" else umap)[(x["study"], x["key"])]
            units[u].append((x["study"], x["limit"] - x["t_ready"]))
            study_of_unit[u].add(x["study"])
        ukeys = sorted(units)
        margins = [np.asarray([m for _, m in units[u]]) for u in ukeys]
        studies_u = [[s for s, _ in units[u]] for u in ukeys]
        pool = pools[setting]
        tot = np.empty(B)
        per_st = {s: np.empty(B) for s in studies}
        ucount = np.empty(B)
        for b in range(B):
            src = [pool[i] for i in rng.integers(0, len(pool), len(pool))]
            ci = rng.integers(0, len(src), len(ukeys))
            d = np.array([src[i][rng.integers(0, len(src[i]))] for i in ci])
            acc = dict.fromkeys(studies, 0)
            n_u = 0
            total = 0
            for m, sts, dd in zip(margins, studies_u, d, strict=True):
                hit = (m < dd) & (dd <= CAP[setting])
                if hit.any():
                    n_u += 1
                for h, s in zip(hit, sts, strict=True):
                    if h:
                        acc[s] += 1
                        total += 1
            tot[b] = total
            ucount[b] = n_u
            for s in studies:
                per_st[s][b] = acc[s]
        marg = np.asarray([x["limit"] - x["t_ready"] for x in elig])
        out[setting] = {
            "lines": n_lines, "lines_pair_ready_within_limit": len(elig),
            "lines_pair_no_ready_or_no_limit": n_lines - len([x for x in sel if x["t_ready"] is not None
                                                             and x["limit"] is not None]),
            "lines_pair_over_limit": len([x for x in sel if x["t_ready"] is not None and x["limit"] is not None
                                          and x["limit"] - x["t_ready"] < 0]),
            "sharing_units": len(ukeys), "unit_col": unit_col,
            "margin_s_le": {str(c): int((marg <= c).sum()) for c in (10, 20, 30, 45)},
            "explained_rows": summ(tot), "explained_units": summ(ucount),
            "per_study": {s: summ(per_st[s]) | {"eligible": sum(1 for x in elig if x["study"] == s)}
                          for s in studies},
        }
    return out


# ---------------------------------------------------------------- E-2
# Corrected E-2 event rows of the public reviews (imua_check_review.md 50-53; imua_check_a2_review.md 1),
# equal to the phase-based 4.2.1 targets on the T4h records (review4 e2_targets_check.json).
CORRECTED_E2 = {"A-v5": {("S5", "VB", 0.8, 0.002), ("S5", "VB", 0.8, 0.003)},
                "A2": {("S3", "VB", 0.85, 0.0), ("S3", "VB", 0.85, 0.002), ("S5", "VB", 0.8, 0.001),
                       ("S5", "VB", 0.8, 0.002), ("S4", "VB", None, 0.0)}}


def e2_event(r: dict) -> bool:
    """A reached READY and the run did not end in READY. inputs.json ``ready_lost_A`` is NOT used: it
    compares the lower-case jsonl final phase with 'READY' and so flags every READY row."""
    return r["t_ready_A"] is not None and str(r["final_phase_A"]).lower() != "ready"


def check_opportunity(rows: list[dict], settings: tuple[str, ...]) -> list[dict]:
    """Per check cluster: opportunity rows and event rows."""
    cl = defaultdict(lambda: {"opp": 0, "ev": 0})
    for r in rows:
        s = "V0" if r["setting"] == "V0" else "VB"
        if s not in settings:
            continue
        pac = r["probe_att_change_R0"]
        if r["t_ready_R0"] is None or pac is None or not pac > OPP_DEG:
            continue
        cl[r["cluster"]]["opp"] += 1
        cl[r["cluster"]]["ev"] += int(e2_event(r))
    return [{"cluster": k} | v for k, v in sorted(cl.items())]


def load_h1(p: Path) -> list[dict]:
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        d1 = r.get("d1") or {}
        pac = (r.get("values") or {}).get("probe_attitude_change_deg")
        out.append({"setting": r["job"]["setting"], "key": r["job"]["d1"]["key"], "eps": float(r["job"]["eps"]),
                    "t_ready": d1.get("t_ready_s"), "limit": d1.get("t_ready_limit_s"),
                    "final_phase": r.get("final_phase"),
                    "pac": float(pac) if isinstance(pac, (int, float)) and not isinstance(pac, bool) else None})
    return out


def d1_opportunity(h1: list[dict], require_final_ready: bool) -> dict:
    by = {"V0": defaultdict(int), "VB": defaultdict(int)}
    for x in h1:
        if x["t_ready"] is None or x["pac"] is None or not x["pac"] > OPP_DEG:
            continue
        if require_final_ready and str(x["final_phase"]).upper() != "READY":
            continue
        by[x["setting"]][x["key"]] += 1
    return {s: [n for _, n in sorted(d.items())] for s, d in by.items()}


def e2_predict(opp_keys: list[int], clusters: list[dict], rng, mode: str, q_prior=None) -> dict:
    """Predictive counts of explained E-2 rows / keys over D-1 opportunity keys."""
    n_keys = len(opp_keys)
    m = np.asarray(opp_keys, int)
    rows_c = np.empty(B)
    keys_c = np.empty(B)
    x_cl = sum(1 for c in clusters if c["ev"] > 0)
    n_cl = len(clusters)
    ev_rows = sum(c["ev"] for c in clusters if c["ev"] > 0)
    opp_rows_ev = sum(c["opp"] for c in clusters if c["ev"] > 0)
    for b in range(B):
        if mode == "bootstrap":
            res = [clusters[i] for i in rng.integers(0, n_cl, n_cl)]
            xe = [c for c in res if c["ev"] > 0]
            pi = len(xe) / n_cl
            qq = (sum(c["ev"] for c in xe) / sum(c["opp"] for c in xe)) if xe else 0.0
            if q_prior is not None:
                qq = rng.beta(*q_prior)
        else:  # Jeffreys beta-binomial
            pi = rng.beta(x_cl + 0.5, n_cl - x_cl + 0.5)
            qa, qb = q_prior if q_prior is not None else (ev_rows + 0.5, opp_rows_ev - ev_rows + 0.5)
            qq = rng.beta(qa, qb)
        ev_key = rng.random(n_keys) < pi
        r = rng.binomial(m, qq) * ev_key
        rows_c[b] = r.sum()
        keys_c[b] = (r > 0).sum()
    return {"opportunity_keys": n_keys, "opportunity_rows": int(m.sum()),
            "check_clusters": n_cl, "check_event_clusters": x_cl,
            "check_event_rows_in_event_clusters": f"{ev_rows}/{opp_rows_ev}",
            "explained_rows": summ(rows_c), "explained_keys": summ(keys_c)}


# ---------------------------------------------------------------- self-checks
def self_checks(rng) -> dict:
    res = {}
    # E-1: delay far above cap -> 0; delay just above every margin and under cap -> all lines
    units = [np.array([1.0, 2.0]), np.array([5.0])]
    r, _ = e1_counts(units, [np.array([1000.0])], 30.0, rng, 50)
    res["e1_cap_excludes"] = bool((r == 0).all())
    r, _ = e1_counts(units, [np.array([10.0])], 30.0, rng, 50)
    res["e1_all_lines"] = bool((r == 3).all())
    # E-2: pi = 1, q = 1 -> every opportunity row; pi = 0 -> 0
    cl1 = [{"cluster": "a", "opp": 2, "ev": 2}]
    p = e2_predict([2, 1, 2], cl1, rng, "bootstrap")
    res["e2_all_rows"] = p["explained_rows"]["q2_5_50_97_5"] == [5.0, 5.0, 5.0]
    cl0 = [{"cluster": "a", "opp": 2, "ev": 0}, {"cluster": "b", "opp": 1, "ev": 0}]
    p = e2_predict([2, 1, 2], cl0, rng, "bootstrap")
    res["e2_zero"] = p["explained_rows"]["upper_97_5"] == 0.0
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--inputs", "--h1", "--las-dir", "--map", "--q2", "--out"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    paths = {"inputs": Path(a.inputs), "h1": Path(a.h1), "map": Path(a.map), "q2": Path(a.q2)}
    shas = {}
    for k, p in paths.items():
        if not p.is_file():
            print(json.dumps({"status": "input_missing", "path": str(p)}))
            return 2
        shas[k] = sha(p)
        if not shas[k].startswith(EXPECT_SHA[k]):
            print(json.dumps({"status": "sha_mismatch", "input": k, "sha": shas[k][:16]}))
            return 2
    inp = json.loads(paths["inputs"].read_text(encoding="utf-8"))
    q2 = json.loads(paths["q2"].read_text(encoding="utf-8"))
    rows = inp["check"]["A-v5"]["rows"]
    ss = np.random.SeedSequence(SEED).spawn(8)
    out: dict = {"seed": SEED, "B": B, "inputs_sha256": shas, "cap_s": CAP, "opportunity_deg": OPP_DEG}

    # 1. regression: exact replay of the published D-1 E-1 numbers
    leg = legacy_q2(inp)
    pub = {s: q2["E1_D1_predicted"]["A-v5"][s]["pred_fail_rows_q"] for s in ("V0", "VB")}
    out["regression_q2_D1"] = {"replay": leg, "published": pub, "equal": leg == pub}

    # 2. E-1 D-1 with the cap and the A-no-READY sensitivity
    by_key = defaultdict(list)
    for x in inp["d1"]["recs"]:
        if x["t_ready"] is None or x["t_ready_limit"] is None:
            continue
        mg = x["t_ready_limit"] - x["t_ready"]
        if mg >= 0:
            by_key[(x["setting"], x["key"])].append(mg)
    e1d1 = {}
    for tag, inf in (("cap", False), ("cap_inf_A_no_ready", True)):
        rng = np.random.default_rng(ss[0] if tag == "cap" else ss[1])
        pools = delay_pools(rows, inf)
        e1d1[tag] = {}
        for s in ("V0", "VB"):
            units = [np.asarray(v) for k, v in by_key.items() if k[0] == s]
            rc, uc = e1_counts(units, pools[s], CAP[s], rng, B)
            e1d1[tag][s] = {"keys": len(units), "rows": int(sum(len(u) for u in units)),
                            "explained_rows": summ(rc), "explained_keys": summ(uc),
                            "pool_clusters": len(pools[s])}
    out["E1_D1"] = e1d1

    # 3. E-1 U-3
    cm = list(csv.DictReader(paths["map"].open(encoding="utf-8")))
    cmap = {(r["study"], r["key"]): r["cluster"] for r in cm}
    umap = {(r["study"], r["key"]): r["resample_unit"] for r in cm}
    lines, chk = load_u3(Path(a.las_dir))
    out["U3_input_checks"] = chk | {"lines": len(lines),
                                    "lines_per_setting": {s: sum(1 for x in lines if x["setting"] == s)
                                                          for s in ("V0", "VB")},
                                    "limit_hist": {s: {str(k): sum(1 for x in lines if x["setting"] == s
                                                                   and x["limit"] == k)
                                                       for k in (90.0, 100.0, 120.0, None)}
                                                   for s in ("V0", "VB")}}
    pools = delay_pools(rows, False)
    pools_inf = delay_pools(rows, True)
    out["E1_U3"] = {
        "main_cluster_6studies": e1_u3(lines, cmap, umap, pools, np.random.default_rng(ss[2]),
                                       U3_LIMIT_STUDIES, "cluster"),
        "sens_resample_unit_6studies": e1_u3(lines, cmap, umap, pools, np.random.default_rng(ss[3]),
                                             U3_LIMIT_STUDIES, "resample_unit"),
        "sens_cluster_8studies_incl_g6_C": e1_u3(lines, cmap, umap, pools, np.random.default_rng(ss[4]),
                                                 U3_LIMIT_STUDIES + U3_SENS_STUDIES, "cluster"),
        "sens_cluster_6studies_inf_A_no_ready": e1_u3(lines, cmap, umap, pools_inf,
                                                      np.random.default_rng(ss[5]), U3_LIMIT_STUDIES,
                                                      "cluster"),
    }

    # 4. E-2 D-1
    h1 = load_h1(paths["h1"])
    opp_all = check_opportunity(rows, ("V0", "VB"))
    opp_vb = check_opportunity(rows, ("VB",))
    out["E2_check_opportunity_A-v5"] = {"pooled": opp_all, "VB_only": opp_vb}
    a2_rows = inp["check"]["A2"]["rows"]
    out["E2_check_opportunity_A2_record"] = check_opportunity(a2_rows, ("V0", "VB"))
    rng = np.random.default_rng(ss[6])
    e2 = {}
    for req in (True, False):
        opp = d1_opportunity(h1, req)
        tag = "final_ready" if req else "ready_reached"
        e2[tag] = {}
        for s in ("V0", "VB"):
            e2[tag][s] = {
                "main_bootstrap_pooled": e2_predict(opp[s], opp_all, rng, "bootstrap"),
                "sens_jeffreys_pooled": e2_predict(opp[s], opp_all, rng, "jeffreys"),
                "sens_bootstrap_q_A2pooled_6of10": e2_predict(opp[s], opp_all, rng, "bootstrap",
                                                               q_prior=(6.5, 4.5)),
                "sens_bootstrap_VB_only": e2_predict(opp[s], opp_vb, rng, "bootstrap"),
            }
        both = opp["V0"] + opp["VB"]
        e2[tag]["V0+VB"] = {"main_bootstrap_pooled": e2_predict(both, opp_all, rng, "bootstrap")}
    out["E2_D1"] = e2
    out["E2_D1_opportunity_counts"] = {
        tag: {s: {"keys": len(v), "rows": int(sum(v))} for s, v in d1_opportunity(h1, req).items()}
        for tag, req in (("final_ready", True), ("ready_reached", False))}
    # one-sided Clopper-Pearson for the check rate (record)
    x = sum(1 for c in opp_all if c["ev"] > 0)
    n = len(opp_all)
    out["E2_check_cluster_rate_CP95"] = [float(stats.beta.ppf(0.025, x, n - x + 1)) if x else 0.0,
                                         float(stats.beta.ppf(0.975, x + 1, n - x))]

    # 5. operating characteristics of the 'larger than expected' disclosure (observed > upper)
    oc_rng = np.random.default_rng(ss[7].spawn(1)[0])
    oc: dict = {"E1_U3": {}, "E2_D1": {}}
    main_u3 = out["E1_U3"]["main_cluster_6studies"]
    for s in ("V0", "VB"):
        u_up = main_u3[s]["explained_rows"]["upper_97_5"]
        elig = [x for x in lines if x["setting"] == s and x["study"] in U3_LIMIT_STUDIES
                and x["t_ready"] is not None and x["limit"] is not None and x["limit"] - x["t_ready"] >= 0]
        units = defaultdict(list)
        for x in elig:
            units[cmap[(x["study"], x["key"])]].append(x["limit"] - x["t_ready"])
        um = [np.asarray(v) for _, v in sorted(units.items())]
        res = {"upper": u_up, "flag_prob_by_delay_scale": {}}
        for scale in (0.75, 1.0, 1.25, 1.5, 2.0):
            pool = [p * scale for p in pools[s]]
            # cap stays at the rule value: scaled delays above the cap are 'size exceeded', not explained
            c, _ = e1_counts(um, pool, CAP[s], oc_rng, 2000, boot=False)
            c_i, _ = e1_counts(um, pool, np.inf, oc_rng, 2000, boot=False)
            res["flag_prob_by_delay_scale"][f"{scale:g}"] = {
                "p_flag": float((c > u_up).mean()), "mean_count": float(c.mean()),
                "p_flag_sig_i_only": float((c_i > u_up).mean()), "mean_count_sig_i_only": float(c_i.mean())}
        oc["E1_U3"][s] = res
    oc["E1_D1"] = {}
    for s in ("V0", "VB"):
        u_up = {"V0": 41.0, "VB": 72.0}[s]          # published D-1 bounds (rules 4.2, stats review 1)
        um = [np.asarray(v) for k, v in by_key.items() if k[0] == s]
        res = {"upper": u_up, "flag_prob_by_delay_scale": {}}
        for scale in (0.75, 1.0, 1.25, 1.5, 2.0):
            pool = [p * scale for p in pools[s]]
            c, _ = e1_counts(um, pool, CAP[s], oc_rng, 2000, boot=False)
            c_i, _ = e1_counts(um, pool, np.inf, oc_rng, 2000, boot=False)
            res["flag_prob_by_delay_scale"][f"{scale:g}"] = {
                "p_flag": float((c > u_up).mean()), "mean_count": float(c.mean()),
                "p_flag_sig_i_only": float((c_i > u_up).mean()), "mean_count_sig_i_only": float(c_i.mean())}
        oc["E1_D1"][s] = res
    for s in ("V0", "VB"):
        w = out["E2_D1"]["ready_reached"][s]["main_bootstrap_pooled"]
        u_up = w["explained_rows"]["upper_97_5"]
        m = np.asarray(d1_opportunity(h1, False)[s], int)
        res = {"upper": u_up, "opportunity_rows": int(m.sum()), "flag_prob": {}}
        for pi in (0.1, 1 / 3, 0.5, 2 / 3, 1.0):
            for qq in (0.5, 0.75, 1.0):
                n = 4000
                ev = oc_rng.random((n, m.size)) < pi
                cnt = (oc_rng.binomial(np.broadcast_to(m, (n, m.size)), qq) * ev).sum(axis=1)
                res["flag_prob"][f"pi{pi:.3f}_q{qq:g}"] = float((cnt > u_up).mean())
        oc["E2_D1"][s] = res
    out["OC_larger_than_expected"] = oc

    sc = self_checks(np.random.default_rng(ss[7]))
    for arm in ("A-v5", "A2"):
        got = {(r["case"], r["setting"], r["eta"], float(r["eps"])) for r in inp["check"][arm]["rows"] if e2_event(r)}
        sc[f"e2_events_equal_corrected_{arm}"] = got == CORRECTED_E2[arm]
    out["self_checks"] = sc
    ok = all(sc.values()) and out["regression_q2_D1"]["equal"] and not chk["D_limit_mismatch"]
    out["status"] = "ok" if ok else "self_check_failed"
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": out["status"], "regression_equal": out["regression_q2_D1"]["equal"],
                      "D_limit_mismatch": len(chk["D_limit_mismatch"]), "self_checks": sc}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
