"""Q-3 refinement: harsher-candidate shape pairs only (sealed keys: first candidate differs in 24/48 b_shape
slots, 9 with a harsher candidate), N layer, plus E-layer A/A stop (x_AA,E >= 2) with shape pairs.
Reuses the exact-sum rule functions of nb1_effects.py (same folder). Usage: nb1_q3b.py <out.json>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# isort: split
import nb1_effects as e  # noqa: E402
import numpy as np  # noqa: E402


def main():
    out = {"n_layer": [], "e_layer": []}
    for naa in (300, 285):
        for p0 in (0.001, 0.002, 0.005):
            base = e.rule_probs(300, naa, p0)
            for m_s in (7, 9):
                for p_s in (0.02, 0.05, 0.10, 0.20):
                    r = e.rule_probs(300, naa, p0, m_s=m_s, p_s=p_s)
                    out["n_layer"].append({"n_N": 300, "n_AA": naa, "p0": p0, "m_s": m_s, "p_s": p_s,
                                           "E_x": round(r["E_x_AA"], 3),
                                           "stop_pct": round(100 * r["p_stop"], 2),
                                           "d_stop_pct": round(100 * (r["p_stop"] - base["p_stop"]), 2),
                                           "ff_pct": round(100 * r["false_fail"], 3),
                                           "pow_pct": round(100 * r["power_delta"], 2),
                                           "d_pow_pct": round(100 * (r["power_delta"] - base["power_delta"]), 2)})
    for naa_e in (16, 20, 26):
        for p0 in (0.005, 0.01, 0.02):
            for m_s in (0, 2, 5):
                for p_s in (0.05, 0.10, 0.20):
                    pm = e.pmf_x(naa_e, p0, m_s, p_s)
                    stop = float(np.sum(pm[2:]))
                    out["e_layer"].append({"n_AA_E": naa_e, "p0": p0, "m_s": m_s, "p_s": p_s,
                                           "P_stop_E_pct": round(100 * stop, 2)})
                    if m_s == 0:
                        break
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
