"""Split the injected-jump detection by the period after the event (record only).

Usage (dynamics-dev): python.exe -I -B d1_rule_split.py <control_d1_rule folder>

Bands of ``t - t_event``: pre (< 0), k1 = [0.1, 0.2) s (the period judged against the
lift-instant sample; the C0 detections there can lean on the same timing term that makes the
false faults), k2 = [0.2, 0.3) s, late = [0.3, 2.5) s, tail = >= 2.5 s. Only step candidates
(|dp_h + J| > max_step). Writes injection_by_band.csv (refuses an existing file).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

RULES = ("C0", "Cd", "Ce", "Cf", "Cm", "Cmo", "D1p")


def band(t: float) -> str:
    if t < 0.0:
        return "pre"
    if t < 0.1:
        return "k0"
    if t < 0.2:
        return "k1"
    if t < 0.3:
        return "k2"
    if t < 2.5:
        return "late"
    return "tail"


def main() -> int:
    folder = Path(sys.argv[1])
    out = folder / "injection_by_band.csv"
    if out.exists():
        print("refusing to overwrite")
        return 2
    groups: dict[tuple, list[int]] = {}
    with (folder / "injection_detail.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["threshold_kN"] == "" or row["t_minus_event_s"] == "":
                continue
            key = (band(float(row["t_minus_event_s"])), row["kind"], float(row["jump_bar"]))
            counts = groups.setdefault(key, [0] * (1 + len(RULES)))
            counts[0] += 1
            for n, rule in enumerate(RULES, start=1):
                counts[n] += row[rule] == "True"
    rows = []
    order = {"pre": 0, "k0": 1, "k1": 2, "k2": 3, "late": 4, "tail": 5}
    for (b, kind, jump), counts in sorted(groups.items(), key=lambda kv: (order[kv[0][0]],
                                                                          kv[0][1], kv[0][2])):
        line = {"band": b, "kind": kind, "jump_bar": jump, "n_candidate": counts[0]}
        for n, rule in enumerate(RULES, start=1):
            line[f"{rule}_rate"] = round(counts[n] / counts[0], 5)
        rows.append(line)
    with out.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for line in rows:
        if line["kind"] == "transient":
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
