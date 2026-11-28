"""Tables over the d1_rule_eval.py outputs (record only).

Usage (dynamics-dev): python.exe -I -B d1_rule_tables.py <control_d1_rule folder>

Writes (refuses existing files):
  injection_conditional.csv  detection among injected jumps that are step candidates
                             (|dp_h + J| > max_step), per scope x jump x rule; the rules differ
                             only in the explanation stage, so this is the rate they change
  false_fault_rows.csv       candidate leg-periods unexplained under C0 (the false faults),
                             with the C-d second comparison and its margin
  cd_loss_rows.csv           injected jumps detected by C0 but not by C-d (where C-d loses)
Prints the Ce rows that stay unexplained.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

RULES = ("C0", "Cd", "Ce", "Cf", "Cm", "Cmo", "D1p")


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def truth(value: str) -> bool:
    return value == "True"


def write(path: Path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(k for r in rows for k in r)) if rows else ["empty"]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    folder = Path(sys.argv[1])
    outs = ["injection_conditional.csv", "false_fault_rows.csv", "cd_loss_rows.csv",
            "cm_loss_rows.csv", "loss_by_period.csv"]
    if any((folder / n).exists() for n in outs):
        print("refusing to overwrite")
        return 2
    detail = read(folder / "injection_detail.csv")
    groups: dict[tuple, list[dict]] = {}
    loss = []
    loss_m = []
    for row in detail:
        if row["threshold_kN"] == "":
            continue
        scopes = ["all", row["kind"]]
        if truth(row["event_0_0p5s"]):
            scopes.append("event_0_0p5s")
        for scope in scopes:
            groups.setdefault((scope, float(row["jump_bar"])), []).append(row)
        if truth(row["C0"]) and not truth(row["Cd"]):
            loss.append(row)
        if truth(row["C0"]) and not truth(row["Cm"]):
            loss_m.append(row)
    table = []
    for (scope, jump), rows in sorted(groups.items()):
        n = len(rows)
        line = {"scope": scope, "jump_bar": jump, "n_candidate": n}
        for rule in RULES:
            hit = sum(truth(r[rule]) for r in rows)
            line[f"{rule}_rate"] = round(hit / n, 5)
            line[f"{rule}_missed"] = n - hit
        table.append(line)
    write(folder / "injection_conditional.csv", table)
    cand = read(folder / "candidate_periods.csv")
    false_rows = [r for r in cand if truth(r["C0"])]
    write(folder / "false_fault_rows.csv", false_rows)
    write(folder / "cd_loss_rows.csv", loss)
    write(folder / "cm_loss_rows.csv", loss_m)
    by_period: dict[tuple, int] = {}
    for name, rows in (("Cd", loss), ("Cm", loss_m)):
        for r in rows:
            key = (name, r["t_minus_event_s"])
            by_period[key] = by_period.get(key, 0) + 1
    write(folder / "loss_by_period.csv",
          [{"rule": k[0], "t_minus_event_s": k[1], "lost_vs_C0": v}
           for k, v in sorted(by_period.items(), key=lambda kv: (kv[0][0], float(kv[0][1])))])
    for r in cand:
        if truth(r["Ce"]):
            print("Ce", r["set"], r["label"], r["t_s"], r["leg"], r["r_jm2_kN"], r["r_jm1_kN"],
                  r["r_j_kN"], r["r_jp1_kN"], r["threshold_kN"])
    print("false-fault leg periods", len(false_rows), "cd loss rows", len(loss))
    return 0


if __name__ == "__main__":
    sys.exit(main())
