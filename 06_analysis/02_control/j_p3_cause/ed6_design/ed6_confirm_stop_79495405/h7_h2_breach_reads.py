"""Check that every recorded J-P3a breach read in Part D is a probe-phase carry_ext read with the
rod read above the used bound: count such reads from T4h per arm/line/leg and compare with the
record `jp3a_breach_reads`; print the rod and bound ranges of those reads. No judgement."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
         r"\records_after_stop\D_a1")


def main() -> None:
    mismatch = 0
    rods, bounds, gaps, phases = [], [], [], defaultdict(int)
    per_arm = defaultdict(int)
    for text in (D / "grid_cause.jsonl").read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        arm = row["job"]["setting"]
        rec = ((row.get("hydraulics_record") or {}).get("extend_bound_check") or {})
        rec_a = rec.get("jp3a_breach_reads") or [0, 0, 0, 0]
        with np.load(D / "grid_cause_t4h" / row["t4h_file"], allow_pickle=False) as d:
            cls, names = d["jp3_class"], [str(x) for x in d["jp3_class_names"]]
            rod, bound, ph = d["rod_pressure_Pa"], d["jp3_used_bound_Pa"], d["phase"]
        ce = names.index("carry_ext")
        for leg in range(4):
            over = (rod[:, leg] > bound[:, leg]) & np.isfinite(bound[:, leg])
            ce_over = over & (cls[:, leg] == ce)
            n = int(ce_over.sum())
            per_arm[arm] += n
            if n != rec_a[leg]:
                mismatch += 1
                print("mismatch", arm, row["t4h_file"], leg, n, rec_a[leg],
                      {names[c]: int((over & (cls[:, leg] == c)).sum()) for c in range(len(names))})
            for i in np.flatnonzero(ce_over):
                rods.append(rod[i, leg] / 1e5)
                bounds.append(bound[i, leg] / 1e5)
                gaps.append((bound[i, leg] - rod[i, leg]) / 1e5)
                phases[str(ph[i])] += 1
    print("carry_ext over-bound reads per arm:", dict(per_arm), "mismatch legs:", mismatch)
    print("phases:", dict(phases))
    print(f"rod {min(rods):.2f}..{max(rods):.2f} bar, bound {min(bounds):.2f}..{max(bounds):.2f} bar,"
          f" gap {min(gaps):.2f}..{max(gaps):.2f} bar")


if __name__ == "__main__":
    main()
