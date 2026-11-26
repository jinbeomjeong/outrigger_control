"""e02: footprint bounds of the early-handover candidates on the stored edition 6 / 7 lines.

Input: ``../dynamics_u832_o00/u01_scan_ed6.csv`` / ``u01_scan_ed7.csv`` (``reapproach_starts``).
Per (scan, src, setting):
* lines with any re-approach start (upper bound of every candidate: no start -> no change);
* H-1 (diagonal waits for its rocking lift to end): lines with a diagonal handover (k10/e01
  showed the diagonal reads L < 0 at every handover of the re-run lines, so H-1 / H-2 act at
  every diagonal handover);
* H-3 (short-run exit needs one more sample): lower bound = lines with two consecutive starts
  <= 0.5 s apart (the earlier run then ended within 0.5 s of its start); the exact count needs the
  run end times (record key Y8-7 d), not in the scan.

Usage: conda run -n dynamics-dev python -I -B e02_footprint.py
Output: e02_out.txt (this folder).
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "dynamics_u832_o00"
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
T_R = 0.5


def main() -> int:
    tally = Counter()
    for name in ("u01_scan_ed6.csv", "u01_scan_ed7.csv"):
        for r in csv.DictReader((SRC / name).open(encoding="utf-8")):
            starts = (json.loads(r["reapproach_starts"]) if r["reapproach_starts"] else None) or []
            key = (name[-7:-4], r["src"], r["setting"])
            tally[key + ("lines",)] += 1
            tally[key + ("any_start",)] += bool(starts)
            pairs = list(zip(starts, starts[1:]))
            tally[key + ("diag_handover",)] += any(DIAG.get(a[1]) == b[1] for a, b in pairs)
            tally[key + ("short_gap",)] += any(float(b[0]) - float(a[0]) <= T_R + 1e-9 for a, b in pairs)
    groups = sorted({k[:3] for k in tally})
    lines = ["scan | src | setting | lines | any_start | diag_handover (H-1/H-2) | short_gap<=0.5s (H-3 lower bound)"]
    for g in groups:
        lines.append(" | ".join(map(str, g)) + " | " + " | ".join(
            str(tally[g + (m,)]) for m in ("lines", "any_start", "diag_handover", "short_gap")))
    (HERE / "e02_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
