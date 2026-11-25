"""Ed. 7 Q7-S1 addendum: A(i)-b in the twist coordinate D (dynamics review d7, 2026-11-24).
stats-design-expert, 2026-11-24, design only.

Part A (empirical, public judged rows): dynamics_v7/d2_dwells.csv - every blind-band dwell that
  reached 20 cycles in records B (388 + 184) and counterfactual C (60), with D at the would-be
  trigger and the rank-1 predicted dD of one shot (0.75 mm, dD_one) and of all band legs (dD_all).
  -> share of shots that raise |D|, |D| after one shot vs the strict window 3 kN, the relax
  ceiling 15 kN and the twist-loop blind edge ~24 kN.
Part B (toy closed loop, twist-only state = attitude and gap complete, only twist commands left;
  all four legs in the band with twist signs, as in dynamics 2.3):
  D_{k+1} = D_k unless a shot fires; a shot of the four legs moves D by -sign(D) * kappa * de,
  kappa = 4 x U(10.8, 13.4) kN/mm per leg x U(0.85, 0.94) (rank-1 four-leg 26.88 kN/0.62 mm/4 ..
  one-leg 8.3 kN/0.62 mm; measured/predicted ratio), de ~ lognormal(median 0.62, p90 0.85 mm). Trigger after N cycles of band (+0..2
  cycle witness jitter), motion done t_fill ~ U(1.0, 2.5) s after the trigger, then a new stretch.
  Commands exist only if |D| > 2 kN (twist dead band). Completion (c2.py 7775-7882 per dynamics):
  strict = |D| < 3 kN held 1 s; relax = t >= 10 s and |D| <= 15 kN and |D| rise over the last
  5 s <= 0.6 kN (attitude/gap assumed settled from t = 0, loads >= F_min assumed).
  Variants: V0 spec (condition 3 = LEVEL completion not met -> shots in the twist-only state),
  V1 condition 3 narrowed to attitude-or-gap not complete (no shots in the twist-only state),
  V2 = V0 + latch (same leg opposite-sign triggers > 2 -> A(i)-b off for the LEVEL),
  V3 = V1 but twist-only shots allowed while |D| > 15 kN (relax ceiling), V3L = V3 + latch.
  D0 drawn from Part A (D after one shot, all sets) - the state a shot leaves behind.
Outputs (argv[1]): s11_twist_cycle.json / .txt. stdout: status only.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

SEED = 20261114
SRC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design"
           r"\dynamics_v7\d2_dwells.csv")
T = 0.1
HORIZON = 60.0


def part_a(rows):
    out = {}
    sets = sorted({r["set"] for r in rows}) + ["all"]
    for s in sets:
        rr = [r for r in rows if s == "all" or r["set"] == s]
        D = np.array([float(r["D_kN"]) for r in rr])
        d1 = np.array([float(r["dD_one_kN"]) for r in rr])
        da = np.array([float(r["dD_all_kN"]) for r in rr])
        tw = np.array([r["twist_pattern"] == "True" for r in rr])
        a1, aa = np.abs(D + d1), np.abs(D + da)
        out[s] = {"n_dwells": len(rr), "absD_q50_95": [float(x) for x in np.percentile(np.abs(D), [50, 95])],
                  "share_one_shot_raises_absD": float((a1 > np.abs(D)).mean()),
                  "P_absD_after_one_gt3": float((a1 > 3).mean()),
                  "P_absD_after_one_gt15": float((a1 > 15).mean()),
                  "P_absD_after_one_gt24": float((a1 > 24).mean()),
                  "P_absD_after_all_gt15": float((aa > 15).mean()),
                  "n_twist_pattern": int(tw.sum())}
    D = np.array([float(r["D_kN"]) + float(r["dD_one_kN"]) for r in rows])
    return out, D


def run(rng, D0, n_blind, variant, R=4000, band_edge=24.0):
    D = rng.choice(D0, R).astype(float)
    t = np.zeros(R)
    done = np.full(R, np.nan)
    route = np.zeros(R, int)                     # 1 strict, 2 relax
    shots = np.zeros(R, int)
    rev = np.zeros(R, int)
    last_sign = np.zeros(R)
    latched = np.zeros(R, bool)
    K = int(HORIZON / T)
    hist = np.zeros((R, K + 1))
    next_fire = np.where(np.abs(D) > 2, n_blind + rng.integers(0, 3, R), 10 ** 9).astype(float)
    move_end = np.full(R, -1.0)
    pend = np.zeros(R)
    strict_cnt = np.zeros(R, int)
    for k in range(K + 1):
        hist[:, k] = D
        act = np.isnan(done)
        # completion
        strict_cnt = np.where(np.abs(D) < 3, strict_cnt + 1, 0)
        s_ok = act & (strict_cnt >= 10)
        if k * T >= 10:
            w0 = k - 50
            rise = D[:, None] if w0 < 0 else hist[:, w0:k + 1]
            absw = np.abs(rise)
            r_ok = act & (np.abs(D) <= 15) & ((absw - absw[:, :1]).max(1) <= 0.6) & (move_end < 0)
        else:
            r_ok = np.zeros(R, bool)
        fin = act & (s_ok | r_ok)
        done[fin] = k * T
        route[fin & s_ok] = 1
        route[fin & ~s_ok] = 2
        act &= ~fin
        # motion completion
        mv = act & (move_end >= 0) & (k >= move_end)
        D[mv] = D[mv] + pend[mv]
        move_end[mv] = -1
        next_fire[mv] = k + n_blind + rng.integers(0, 3, int(mv.sum()))
        # fire
        allowed = act & (move_end < 0) & (np.abs(D) > 2) & (k >= next_fire) & ~latched
        if variant == "V1":
            allowed &= False
        if variant in ("V3", "V3L"):                 # twist-only shots only above the relax ceiling
            allowed &= np.abs(D) > 15.0
        if allowed.any():
            n = int(allowed.sum())
            de = np.exp(np.log(0.62) + 0.246 * rng.standard_normal(n))
            # four legs shoot (twist sign pattern): per-leg 10.8 (simultaneous, rank-1 four-leg
            # 26.88 kN / 0.62 mm / 4) to 13.4 kN/mm (staggered, one-leg value), x measured ratio
            kap = 4.0 * rng.uniform(10.8, 13.4, n) * rng.uniform(0.85, 0.94, n)
            sgn = -np.sign(D[allowed])
            pend[allowed] = sgn * kap * de
            move_end[allowed] = k + rng.uniform(1.0, 2.5, n) / T
            shots[allowed] += 1
            rv = (last_sign[allowed] != 0) & (last_sign[allowed] != sgn)
            rev[np.flatnonzero(allowed)[rv]] += 1
            last_sign[allowed] = sgn
            if variant in ("V2", "V3L"):
                latched |= rev > 2
        # a stretch restarts when |D| re-enters the band and no motion is pending
        idle = act & (move_end < 0) & (next_fire > 10 ** 8) & (np.abs(D) > 2)
        next_fire[idle] = k + n_blind
    stuck = np.isnan(done)
    return {"P_done_60s": float((~stuck).mean()),
            "P_strict": float((route == 1).mean()), "P_relax": float((route == 2).mean()),
            "t_done_q50_90": [float(x) for x in np.nanpercentile(done, [50, 90])] if (~stuck).any() else None,
            "shots_q50_95": [float(x) for x in np.percentile(shots, [50, 95])],
            "P_shots_ge4": float((shots >= 4).mean()),
            "P_stuck_absD_gt15": float((stuck & (np.abs(D) > 15)).mean()),
            "mcse_done": float(np.sqrt(max((~stuck).mean() * stuck.mean(), 1e-12) / R))}


def main() -> int:
    out_dir = Path(sys.argv[1])
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    rng = np.random.default_rng(SEED)
    a, D_after = part_a(rows)
    res = {"seed": SEED, "src": str(SRC), "n_rows": len(rows), "part_a": a, "part_b": {}}
    for v in ("V0", "V1", "V2", "V3", "V3L"):
        for n in (20, 25, 30, 40, 50):
            res["part_b"][f"{v}|N{n}"] = run(rng, D_after, n, v)
    # self check: V1 never shoots; |D|<=15 starts finish by relax at 10 s (or strict)
    chk = run(rng, np.array([5.0, -8.0, 12.0]), 25, "V1", R=200)
    res["self_check"] = {"V1_no_shots": chk["shots_q50_95"] == [0.0, 0.0],
                         "V1_all_done": chk["P_done_60s"] == 1.0}
    (out_dir / "s11_twist_cycle.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item()),
                                                  encoding="utf-8")
    L = ["== part A (empirical shots, rank-1 prediction) =="]
    for s, v in a.items():
        L.append(f"{s:<12} {json.dumps(v)}")
    L.append("== part B (twist-only toy loop, D0 = D after one shot) ==")
    for k, v in res["part_b"].items():
        L.append(f"{k:<8} {json.dumps(v)}")
    L.append(f"self_check {json.dumps(res['self_check'])}")
    (out_dir / "s11_twist_cycle.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    ok = all(res["self_check"].values())
    print("ok" if ok else "self_check_failed")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
