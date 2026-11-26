"""k05: candidate summary from k02 (per arm: a2 = edition 7 sealed, A = (i-b) off, witness on).

Per candidate: rounds with a defined median (>= 3 scale legs), warnings (outside (0.8, 2.3) and
the high bounds 3.0 / 3.3 / 3.6), largest median, rounds whose clipped scale differs from the
current window, largest change of the round's largest seal-friction estimate (F_band source),
and per leg the residual seal-band term ``(K1 - K_pad) / S_ii`` (harness truth) and the legs whose
seal is still stuck at the (new) mid reading. Round 1 is exact, later rounds approximate (k02).

Usage: conda run -n dynamics-dev python -I -B k05_summary.py
Output: k05_summary.json, k05_out.txt (this folder).
"""
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = ("k1_old", "a0.02_k1", "a0.05_k1", "a0.1_k1", "a0.2_k1",
         "dec0.02_k1", "dec0.05_k1", "dec0.1_k1", "b_k1", "c0.1_k1", "kpad_old")


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x


def main() -> int:
    rounds = list(csv.DictReader((HERE / "k02_rounds.csv").open(encoding="utf-8")))
    legs = [g for g in csv.DictReader((HERE / "k02_legs.csv").open(encoding="utf-8"))
            if g.get("reversed") != "True"]
    out = {}
    lines = []
    for arm in ("a2", "A"):
        rr = [r for r in rounds if r["run"].endswith(f"-{arm}")]
        lg = [g for g in legs if g["run"].endswith(f"-{arm}")]
        out[arm] = {}
        lines.append(f"## arm {arm}: rounds {len(rr)} (round 1: {sum(1 for r in rr if r['round'] == '1')}), legs {len(lg)}")
        for c in CANDS:
            meds = [num(r[f"{c}_median"]) for r in rr]
            defined = [m for m in meds if math.isfinite(m)]
            old_sc = [num(r["k1_old_scale"]) for r in rr]
            new_sc = [num(r[f"{c}_scale"]) for r in rr]
            sc_diff = sum(1 for a, b in zip(old_sc, new_sc)
                          if not ((math.isnan(a) and math.isnan(b)) or abs(a - b) < 1e-9))
            sc_diff_r1 = sum(1 for r, a, b in zip(rr, old_sc, new_sc) if r["round"] == "1"
                             and not ((math.isnan(a) and math.isnan(b)) or abs(a - b) < 1e-9))
            seal_d = []
            if c != "kpad_old":
                seal_d = [abs(num(r[f"{c}_seal_max_kN"]) - num(r["k1_old_seal_max_kN"])) for r in rr]
            rec = {
                "rounds_defined": len(defined),
                "warn_2.3": sum(1 for r in rr if r[f"{c}_warn2.3"] == "True"),
                "warn_high_2.3": sum(1 for m in defined if m > 2.3),
                "warn_low_0.8": sum(1 for m in defined if m < 0.8),
                "warn_high_3.0": sum(1 for m in defined if m > 3.0),
                "warn_high_3.6": sum(1 for m in defined if m > 3.6),
                "max_median": max(defined) if defined else None,
                "min_median": min(defined) if defined else None,
                "scale_differs_rounds": sc_diff, "scale_differs_round1": sc_diff_r1,
                "max_seal_max_change_kN": max(seal_d) if seal_d else None,
            }
            if c.startswith("a") and c[1].isdigit():
                tag = c[1:].split("_")[0]
                kb = [abs(num(g[f"a{tag}_kband_ratio"])) for g in lg]
                kb = [v for v in kb if math.isfinite(v)]
                rec["legs_mid_shifted"] = sum(1 for g in lg if g[f"a{tag}_mid_shift"] not in ("", "0", "None"))
                rec["legs_k1_nan"] = sum(1 for g in lg if not math.isfinite(num(g[f"a{tag}_k1"])))
                rec["legs_stuck_at_new_mid"] = sum(1 for g in lg if g[f"a{tag}_stuck_at_mid"] == "True")
                rec["legs_residual_band_gt_0.1"] = sum(1 for v in kb if v > 0.1)
                rec["max_residual_band_ratio"] = max(kb) if kb else None
            if c == "k1_old":
                kb = [abs(num(g["kband_old_ratio"])) for g in lg if math.isfinite(num(g["kband_old_ratio"]))]
                rec["legs_stuck_at_mid"] = sum(1 for g in lg if g["stuck_at_mid"] == "True")
                rec["legs_residual_band_gt_0.1"] = sum(1 for v in kb if v > 0.1)
                rec["max_residual_band_ratio"] = max(kb) if kb else None
            out[arm][c] = rec
            lines.append(f"{c}: " + ", ".join(f"{k}={(round(v, 3) if isinstance(v, float) else v)}" for k, v in rec.items()))
    (HERE / "k05_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (HERE / "k05_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
