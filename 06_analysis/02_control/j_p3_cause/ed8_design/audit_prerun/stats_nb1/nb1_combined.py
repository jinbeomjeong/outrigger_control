"""Q-1 x Q-3 combined with the key-file shape count (m_s = 9 harsher first candidates, all put in N as an
upper case). n_N 300, n_AA 285. Usage: nb1_combined.py <out.json>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# isort: split
import nb1_effects as e  # noqa: E402


def main():
    rows = []
    for p0 in (0.001, 0.002, 0.005):
        base = e.rule_probs(300, 285, p0)
        for qn, q in (("0", 0.0), ("ub2679", e.ub0(2679)), ("ub467", e.ub0(467))):
            for p_s in (None, 0.05, 0.20):
                r = e.rule_probs(300, 285, p0, q=q, m_s=9 if p_s else 0, p_s=p_s)
                rows.append({"p0": p0, "q": qn, "p_s": p_s, "stop_pct": round(100 * r["p_stop"], 2),
                             "ff_pct": round(100 * r["false_fail"], 2),
                             "d_ff_pct": round(100 * (r["false_fail"] - base["false_fail"]), 2),
                             "pow_pct": round(100 * r["power_delta"], 1),
                             "d_pow_pct": round(100 * (r["power_delta"] - base["power_delta"]), 1)})
    json.dump(rows, open(sys.argv[1], "w", encoding="utf-8"), indent=0)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
