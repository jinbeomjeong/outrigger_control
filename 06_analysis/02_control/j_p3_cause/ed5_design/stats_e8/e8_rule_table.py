"""Tables from e8_rule_sim.json: null means, false-failure rate per scenario, power and MDE80.

Writes e8_rule_tables.txt next to this file. stdout: status only.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY_RULES = ["A_k3", "A_k4", "A_k5", "A_k6", "A_k7", "A_k8", "A_k10", "A_k12", "A_sep_k36_k23",
             "A_sep_k37_k23", "A_cell_kC6_kR3", "A_cell_kC7_kR3", "A_cell_kC8_kR3", "B_sign_a05", "B_sign_a10", "B_sep_a025", "B_cell_a025",
             "D_diff_ge4", "H_sign_or_B_gt8", "H_sign_or_B_gt10", "H_sign_or_B_gt12"]


def mde80(rows: list, rule: str) -> str:
    pts = [(r["delta"], r["fail_rate"][rule]) for r in rows]
    for (d0, p0), (d1, p1) in zip(pts, pts[1:]):
        if p0 < 0.8 <= p1:
            return f"{100 * (d0 + (0.8 - p0) * (d1 - d0) / (p1 - p0)):.2f}"
    return ">7" if pts[-1][1] < 0.8 else "<=" + f"{100 * pts[0][0]:.2f}"


def main() -> None:
    doc = json.loads((HERE / "e8_rule_sim.json").read_text(encoding="utf-8"))
    n = doc["n_sim"]
    lines = [f"seed {doc['seed']}, n_sim {n}, MCSE(p) = sqrt(p(1-p)/{n}) (max 0.35 %p)",
             "inputs: " + json.dumps(doc["inputs"]), "self_checks: " + json.dumps(
                 doc["self_checks"]), ""]
    lines.append("== null means (delta 0) ==")
    for s, v in doc["scenarios"].items():
        m = v["null_means"]
        lines.append(f"{s:22s} c_gen {v['c_gen']:.3f} c_prone {v['c_prone']:.3f} r2 {v['r2']:.4f} | "
                     + " ".join(f"{k} {m[k]:.2f}" for k in ("B3", "C3", "B2", "C2", "B_C", "B_R"))
                     + " | P(B=j) j=0..8 " + " ".join(
                         f"{x / n:.3f}" for x in v["null_dist_B"][:9]))
    lines.append("")
    lines.append("== false-failure rate (delta 0), % ==")
    lines.append(f"{'rule':24s}" + "".join(f"{s[:12]:>13s}" for s in doc["scenarios"]))
    first = next(iter(doc["scenarios"].values()))["by_harm"]["all"][0]["fail_rate"]
    for rule in first:
        row = []
        for v in doc["scenarios"].values():
            fr = v["by_harm"]["all"][0]["fail_rate"].get(rule)
            row.append(f"{100 * fr:13.2f}" if fr is not None else f"{'-':>13s}")
        lines.append(f"{rule:24s}" + "".join(row))
    lines.append("")
    for s, v in doc["scenarios"].items():
        for h, rows in v["by_harm"].items():
            lines.append(f"== power, scenario {s}, harm cells {h} (delta %, expected harm pairs) ==")
            lines.append(f"{'rule':24s}" + "".join(
                f"{100 * r['delta']:>7.2f}" for r in rows) + "   MDE80%")
            lines.append(f"{'E[harm pairs]':24s}" + "".join(
                f"{r['expected_harm_pairs']:>7.1f}" for r in rows))
            for rule in KEY_RULES:
                lines.append(f"{rule:24s}" + "".join(
                    f"{100 * r['fail_rate'][rule]:>7.1f}" for r in rows) + f"   {mde80(rows, rule)}")
            lines.append("")
        lines.append(f"-- fix masking, scenario {s} --")
        for f in v["fix_masking"]:
            lines.append(f"fix {f['fix']} delta {100 * f['delta']:.1f}% : " + " ".join(
                f"{k} {100 * x:.1f}" for k, x in f["fail_rate"].items()))
        lines.append("")
    (HERE / "e8_rule_tables.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
