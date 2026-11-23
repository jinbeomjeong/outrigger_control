"""Ed. 6 review of the pre-seal key lists (ed6_design/keys/) - confirmation (ga) frame and P-pred
k_allow seed stability (stats-design-expert, 2026-11-24, design only).

Part 1: margin-scatter model of s40 (imported) on the (ga) frames, 4 sensitivity settings:
  F26 = required rows outside the 6.2 subset (R2 4, R7 4, S8 4, G4 other 7 keys x 2 = 26/setting);
  F54 = F26 + regression rows R1 R5 R6 R8 R9 R10 R11 S3 (2 each), R3 R4 S2 (4 each) = 54/setting;
  F38 = the 6.2 subset minus probe-seen units (the wording of spec 6.3 line 482; duplicates 6.2).
  Rule: cluster rule k = 2 (s40 'clus2'), also zero and count2.
Part 2: P-pred (s70 inner_pred = sealed algorithm) on the ed. 5 VBK0 b1/b2 pattern (erratum 8
  8-1, public design input): k_allow and P(n23 > 9), P(n23 > 10) over seeds and (n_par, n_rep).
Writes s41_keys_review.json / .txt. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# isort: split
import s40_sens_confirm as s40  # noqa: E402
import s70_12b_kallow as s70  # noqa: E402

SEED = 20261124


def frames():
    f26 = [(4, 0)] * 3 + [(2, 0)] * 7                     # R2, R7, S8 ; G4 other 7 keys
    reg = [(2, 0)] * 8 + [(4, 0)] * 3                     # 2-phase x8, 4-phase x3
    f38 = s40.sens_frame(7)                               # seen phases removed inside
    return {"F26": f26 * 4, "F54": (f26 + reg) * 4, "F38_spec482": f38 * 4}


def part1(rng):
    out = {}
    for name, fr in frames().items():
        blk = {"unseen_units": sum(p - s for p, s in fr), "null": {}, "power": {}}
        for c in (2.5, 3.0, 3.5):
            r = s40.simulate(fr, c, 0.5, 20000, rng, k_list=(2,))
            blk["null"][f"c{c}"] = {"zero": r["zero"], "count2": r["count2"], "clus2": r["clus2"]}
        one = len(fr) // 4
        for lab, idx in (("D1_one_row_one_setting", [0]),
                         ("D2_all_rows_one_setting", list(range(one)))):
            for mb in (1.0, 0.0, -1.0):
                r = s40.simulate(fr, 3.0, 0.5, 10000, rng, harm=idx, m_bad=mb, k_list=(2,))
                blk["power"][f"{lab}|mbad{mb}"] = {"clus2": r["clus2"], "count2": r["count2"]}
        out[name] = blk
    return out


def ed5_v():
    st = np.zeros((167, 2), bool)
    st[0] = (1, 1); st[1] = (1, 1); st[2] = (1, 0); st[3] = (0, 1); st[84] = (1, 0)
    return {"q": np.zeros(167), "cell": np.repeat([0, 1], s70.N_CASE), "stall": st, "aa30": 1,
            "n_both": 162}


def part2():
    v = ed5_v()
    out = {}
    for n_par, n_rep in ((1000, 20), (5000, 20), (20000, 10)):
        rows = []
        for sd in (1, 777, 20261114, 20261124, 20261125, 11, 22, 33, 44, 55):
            b = s70.inner_pred(np.random.default_rng(sd), v, n_par=n_par, n_rep=n_rep)
            rows.append({"seed": sd, "k": s70.pick(b, 0.10), "P_gt9": float((b > 9).mean()),
                         "P_gt10": float((b > 10).mean())})
        ks = [r["k"] for r in rows]
        p9 = np.array([r["P_gt9"] for r in rows])
        out[f"npar{n_par}_nrep{n_rep}"] = {
            "rows": rows, "k_values": sorted(set(ks)), "share_k10": ks.count(10) / len(ks),
            "P_gt9_mean": float(p9.mean()), "P_gt9_sd_over_seeds": float(p9.std(ddof=1))}
    return out


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "part1": part1(rng), "part2": part2()}
    (HERE / "s41_keys_review.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                               encoding="utf-8")
    L = []
    for n, b in out["part1"].items():
        L.append(f"== {n}: unseen units {b['unseen_units']}")
        for k, v in b["null"].items():
            L.append(f"  null {k}: zero {100*v['zero']:.1f}% count2 {100*v['count2']:.1f}% "
                     f"clus2 {100*v['clus2']:.1f}%")
        for k, v in b["power"].items():
            L.append(f"  pow {k:<34} clus2 {100*v['clus2']:.1f}% count2 {100*v['count2']:.1f}%")
    for n, b in out["part2"].items():
        L.append(f"== P-pred {n}: k {b['k_values']} share k=10 {b['share_k10']:.1f} "
                 f"P(n23>9) mean {b['P_gt9_mean']:.4f} sd {b['P_gt9_sd_over_seeds']:.4f}")
    (HERE / "s41_keys_review.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
