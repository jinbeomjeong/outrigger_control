"""Base rates of 'no READY' and long LEVEL in the VBK0-type lines of run 606f8713 (read-only).

Populations (VBK lines are never read):
  12b VBK0 b1/b2 (rod fault, plant_truth, P1-P4, rev 6 off) by anchor;
  c dry VBK0 c92/c93 (same setting, seeds 90/91, outside the judged set);
  Dg-3 VBJ0 (same plant, rev 6 off, no rod fault) by level;
  stored fault-free h8_noise_VB.json L2 (VB rev 4, 5 seeds per case; the A/A floor basis,
  ed5_design/stats_b/l2_floor.json).
For tau_R lines without READY: the time from the first LEVEL to the fault and whether the
strokes were already static (|d stroke| < 1 mm over the 20 s before the fault).
Also a Monte Carlo of the A/A count under the observed per-line no-READY rate with a
per-case propensity (beta-binomial fitted by moments to the b1/b2 cases), seed fixed.
Writes ``aa_baserate.json``.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
J9 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713")
H8 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1"
          r"\h8_noise_VB.json")
SEED = 20261123


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def ready(row: dict):
    b = row.get("base") or {}
    return b.get("t_ready_s", b.get("t_ready"))


def rows_of(path: Path) -> list:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["results"] if isinstance(doc, dict) else doc


def tally(rows: list, by=None) -> dict:
    groups: dict[str, list] = {}
    for r in rows:
        g = by(r) if by else "all"
        groups.setdefault(g, []).append(r)
    out = {}
    for g, rs in sorted(groups.items()):
        t = [ready(r) for r in rs]
        tr = np.array([x for x in t if x is not None], float)
        out[g] = {"n": len(rs), "no_ready": sum(x is None for x in t),
                  "final_phase": dict(Counter((r.get("base") or {}).get("final_phase")
                                              for r in rs)),
                  "t_ready_q": ({q: round(float(np.quantile(tr, q)), 1)
                                 for q in (0.5, 0.9, 0.99, 1.0)} if tr.size else {}),
                  "t_ready_gt_150": int((tr > 150).sum())}
    return out


def anchor(r: dict) -> str:
    return (r.get("rod_fault") or {}).get("anchor", "none")


def pre_fault_static(block: str, row: dict) -> dict:
    with np.load(J9 / "12b_vbk0_base_a1" / f"VBK0_{block}_t4h" / row["t4h_file"],
                 allow_pickle=False) as d:
        t = np.asarray(d["t_s"], float)
        s = np.asarray(d["motor_stroke_m"], float)
        phase = np.asarray(d["phase"]).astype(str)
    tf = row["rod_fault"]["first_applied_t_s"]
    t_lev = float(t[np.flatnonzero(phase == "level")[0]])
    m = (t >= tf - 20.0) & (t < tf)
    ds = (np.abs(s[m][-1] - s[m][0]) * 1e3).round(2).tolist() if m.sum() > 1 else None
    return {"t_first_level": round(t_lev, 1), "t_fault": round(tf, 1),
            "level_before_fault_s": round(tf - t_lev, 1),
            "abs_d_stroke_mm_20s_before_fault": ds,
            "static_before_fault": bool(ds is not None and max(ds) < 1.0)}


def aa_mc(b1: dict, b2: dict, n_sim: int = 200_000) -> dict:
    """A/A one-sided count under a per-case stall propensity (beta-binomial by moments)."""
    cases = list(b1)
    k = np.array([(ready(b1[c]) is None) + (ready(b2[c]) is None) for c in cases])
    p = k.mean() / 2
    var_k = k.var(ddof=1)
    # beta-binomial n=2: var = 2 p (1-p) (1 + rho), rho = 1/(a+b+1)
    rho = max(var_k / (2 * p * (1 - p)) - 1.0, 1e-6)
    ab = 1.0 / rho - 1.0
    a, b = p * ab, (1 - p) * ab
    rng = np.random.default_rng(SEED)
    q = rng.beta(a, b, size=(n_sim, len(cases)))
    x1 = rng.random((n_sim, len(cases))) < q
    x2 = rng.random((n_sim, len(cases))) < q
    one_sided = (x1 != x2).sum(axis=1)
    ind = rng.random((n_sim, len(cases))) < p
    ind2 = rng.random((n_sim, len(cases))) < p
    one_ind = (ind != ind2).sum(axis=1)
    return {"p_line": p, "rho": rho, "beta_a": a, "beta_b": b, "n_sim": n_sim, "seed": SEED,
            "E_one_sided": float(one_sided.mean()),
            "P_one_sided_ge3": float((one_sided >= 3).mean()),
            "independent_E_one_sided": float(one_ind.mean()),
            "independent_P_ge3": float((one_ind >= 3).mean()),
            "note": "A/A count = one-sided no-READY + |dREADY|>30 s; the MC covers the first term"}


def main() -> None:
    out = {}
    b = {blk: {case_of(r["key"]): r for r in rows_of(J9 / "12b_vbk0_base_a1" /
                                                      f"VBK0_{blk}.json")}
         for blk in ("b1", "b2")}
    out["12b_vbk0"] = {blk: tally(list(rows.values()), anchor) for blk, rows in b.items()}
    out["12b_tau_R_no_ready_pre_fault"] = {
        f"{blk}:{c}": pre_fault_static(blk, r) for blk, rows in b.items()
        for c, r in rows.items() if ready(r) is None and anchor(r).startswith("retract")}
    out["12b_tau_R_long_level"] = {
        f"{blk}:{c}": pre_fault_static(blk, r) for blk, rows in b.items()
        for c, r in rows.items() if anchor(r).startswith("retract")
        and r["rod_fault"].get("first_applied_t_s") is not None
        and r["rod_fault"]["first_applied_t_s"] > 90.0}
    cd = []
    for name in ("VBK0_c92.json", "VBK0_c93.json"):
        cd += rows_of(J9 / "cdry_a1" / name)
    out["cdry_vbk0"] = tally(cd, anchor)
    dg = rows_of(J9 / "dg3_a1" / "dg3_VBJ0.json")
    out["dg3_vbj0_no_fault"] = tally(dg, lambda r: str(r.get("level")))
    h8 = [r for r in rows_of(H8) if r.get("level") == "L2"]
    out["h8_VB_rev4_L2_fault_free"] = tally(h8)
    out["aa_mc"] = aa_mc(b["b1"], b["b2"])
    (HERE / "aa_baserate.json").write_text(json.dumps(out, indent=1, ensure_ascii=False,
                                                      default=str), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
