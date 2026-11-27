"""Q-1 extra anchor: q upper bound if census (allowance 0, J9/J11 counted) passes on ~467 VBN units,
and the q at which the N-layer false failure reaches 5 % / 10 %. Usage: nb1_qcensus.py <out.json>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# isort: split
import nb1_effects as e  # noqa: E402


def main():
    out = {"q_ub_census_467": e.ub0(467), "rows": [], "q_at_ff": []}
    for naa in (300, 285):
        for p0 in (0.001, 0.002, 0.005):
            r0 = e.rule_probs(300, naa, p0)
            r = e.rule_probs(300, naa, p0, q=e.ub0(467))
            out["rows"].append({"n_AA": naa, "p0": p0, "ff0_pct": round(100 * r0["false_fail"], 2),
                                "ff_pct": round(100 * r["false_fail"], 2),
                                "pow0_pct": round(100 * r0["power_delta"], 1),
                                "pow_pct": round(100 * r["power_delta"], 1)})
            for target in (0.05, 0.10):
                lo, hi = 0.0, 0.05
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if e.rule_probs(300, naa, p0, q=mid)["false_fail"] >= target:
                        hi = mid
                    else:
                        lo = mid
                out["q_at_ff"].append({"n_AA": naa, "p0": p0, "ff_target": target, "q_pct": round(100 * hi, 3)})
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
