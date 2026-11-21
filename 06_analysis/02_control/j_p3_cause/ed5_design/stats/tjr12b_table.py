"""Tabulate tjr12b_sim.json into markdown tables (P(pass), MCSE, MDE80)."""
import json
import sys
from pathlib import Path

j = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lines = [f"reps {j['reps']}, seed {j['seed']}, pi_D2 {j['pi_D2']}", f"source: {j['source']}", ""]
lines.append("substitute overdispersion L3: " + json.dumps(j["substitute_overdispersion_L3"]))
for pname, p in j["pops"].items():
    lines += ["", f"## {pname}: cases {p['n_cases']}, S per stored row {p['p_sub_per_row']:.3f}, "
              f"S per new seed {p['p_sub_new_seed_expected']:.3f}, base no-READY per row {p['base_noready_per_row']:.3f}",
              "checks " + json.dumps(p["checks"])]
    g = p["grid"]
    # table 1: floor-only P(pass) by m x c
    lines += ["", "### floor only (delta 0): P(pass) [mcse]  | E[N_opp] | N_pairs", "| m | " + " | ".join(f"c={c}" for c in (0.0, 0.05, 0.25, 0.5, 1.0)) + " | E[N_opp] (p05) | pairs |", "|---" * 8 + "|"]
    for m in range(1, 7):
        row = [x for x in g if x["m"] == m and x["delta"] == 0.0]
        cells = []
        for c in (0.0, 0.05, 0.25, 0.5, 1.0):
            e = [x for x in row if x["c"] == c][0]
            cells.append(f"{e['p_pass']:.3f} [{e['mcse']:.3f}]")
        e0 = row[0]
        lines.append(f"| {m} | " + " | ".join(cells) + f" | {e0['n_opp_mean']:.1f} ({e0['n_opp_p05']:.0f}) | {e0['n_pairs']} |")
    for model in ("D1", "D2"):
        for c in (0.0, 0.25, 1.0):
            lines += ["", f"### {model}, c={c}: P(pass) by delta (false acceptance when delta>0)",
                      "| m | " + " | ".join(f"d={d*100:g}%" for d in (0.0025, 0.005, 0.01, 0.02, 0.03, 0.05)) + " |", "|---" * 7 + "|"]
            for m in range(1, 7):
                cells = []
                for d in (0.0025, 0.005, 0.01, 0.02, 0.03, 0.05):
                    e = [x for x in g if x["m"] == m and x["c"] == c and x["delta"] == d and x["model"] == model][0]
                    cells.append(f"{e['p_pass']:.3f}")
                lines.append(f"| {m} | " + " | ".join(cells) + " |")
import numpy as np  # noqa: E402

DS = (0.0, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05)


def mde80(g, m, c, model, key):
    xs, ys = [], []
    for d in DS:
        e = [x for x in g if x["m"] == m and x["c"] == c and x["delta"] == d and (x["model"] == model or d == 0.0)][0]
        xs.append(d)
        ys.append(e[key])
    ys = np.array(ys)
    if ys.min() > 0.2:
        return None
    k = int(np.argmax(ys <= 0.2))
    if k == 0:
        return 0.0
    # log-linear interpolation of P(pass) between grid points
    x0, x1, y0, y1 = xs[k - 1], xs[k], max(ys[k - 1], 1e-9), max(ys[k], 1e-9)
    t = (np.log(0.2) - np.log(y0)) / (np.log(y1) - np.log(y0))
    return x0 + t * (x1 - x0)


for pname, p in j["pops"].items():
    g = p["grid"]
    lines += ["", f"## {pname}: MDE80 (P(pass)<=0.2) and floor false rejection, rules k=0 and k<=1"]
    lines += ["| m | rule | " + " | ".join(f"floor rej c={c}" for c in (0.05, 0.25, 1.0)) + " | MDE80 D1 c=0 | MDE80 D1 c=0.25 | MDE80 D1 c=1 | MDE80 D2 c=0.25 |", "|---" * 9 + "|"]
    for m in range(1, 7):
        for rule, key in (("k=0", "p_pass"), ("k<=1", "p_pass_le1")):
            fr = []
            for c in (0.05, 0.25, 1.0):
                e = [x for x in g if x["m"] == m and x["c"] == c and x["delta"] == 0.0][0]
                fr.append(f"{1 - e[key]:.3f}")
            md = []
            for c, model in ((0.0, "D1"), (0.25, "D1"), (1.0, "D1"), (0.25, "D2")):
                v = mde80(g, m, c, model, key)
                md.append("-" if v is None else f"{v * 100:.2f}%")
            lines.append(f"| {m} | {rule} | " + " | ".join(fr) + " | " + " | ".join(md) + " |")

lines += ["", "zero-count helpers: " + json.dumps(j["zero_count"]), "single-case detect (q=1, p_s .267): " + json.dumps(j["single_case_detect"])]
Path(sys.argv[2]).write_text("\n".join(lines), encoding="utf-8")
print("ok")
