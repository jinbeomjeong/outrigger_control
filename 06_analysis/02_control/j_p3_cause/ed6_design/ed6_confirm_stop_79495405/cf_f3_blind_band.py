"""Counterfactual T4h: post-event LEVEL length, the longest stretch per line in which some leg is
locked with a command inside the A(i) blind band 0 < |u| <= u_hold, the total of such leg-time,
the B3 pre-twist reads, and the first A(i) read after the event. CSV + printed table."""
import csv
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop\C_a2\counterfactual_t4h")
U_HOLD = 2.09243016e-4
PERIOD = 0.1


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def main(out_csv: Path) -> None:
    rows = []
    for path in sorted(T4H.glob("*.npz")):
        with np.load(path, allow_pickle=False) as d:
            t, ph, u, lk = d["t_s"], d["phase"], d["command_m_s"], d["locked"]
            pre = d["lsb_pre_twist_leg"] if "lsb_pre_twist_leg" in d.files else None
            a1 = d["lsb_a1_on"] if "lsb_a1_on" in d.files else None
        levels = [s for s in segments(ph) if s[0] == "level"]
        if len(levels) < 2:
            continue
        _, i0, i1 = levels[-1]
        band = lk[i0:i1 + 1] & (np.abs(u[i0:i1 + 1]) > 1e-12) & (np.abs(u[i0:i1 + 1]) <= U_HOLD)
        longest = 0
        for leg in range(4):
            run = best = 0
            for flag in band[:, leg]:
                run = run + 1 if flag else 0
                best = max(best, run)
            longest = max(longest, best)
        b3_reads = int((pre >= 0).sum()) if pre is not None else 0
        a1_first = None
        if a1 is not None:
            idx = np.flatnonzero(a1[i0:i1 + 1].any(axis=1))
            a1_first = round(float(t[i0 + idx[0]]), 1) if idx.size else None
        name = path.stem
        rows.append({"file": name, "level2_s": round(float(t[i1] - t[i0]), 1),
                     "end_phase": str(ph[-1]),
                     "blind_band_longest_s": round(longest * PERIOD, 1),
                     "blind_band_leg_s": round(float(band.sum()) * PERIOD, 1),
                     "b3_reads": b3_reads, "a1_first_t_s": a1_first})
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['file']:40s} level2 {r['level2_s']:5.1f} end {r['end_phase']:6s} "
              f"band_longest {r['blind_band_longest_s']:5.1f} band_leg_s {r['blind_band_leg_s']:6.1f} "
              f"b3 {r['b3_reads']} a1_first {r['a1_first_t_s']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
