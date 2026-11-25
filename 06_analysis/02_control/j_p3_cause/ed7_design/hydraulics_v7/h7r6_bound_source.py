"""Q7-H1: source of the ③ bound at the H-7 breach reads (read only).

For each breach leg (carry_ext / ext read with rod truth > used bound + 1 Pa) the lock stretch
before the carry is read: the ④ model bound source and inherited flag of its last read, the
locked truth there, and at the breach read the used bound and the carry bound. Counts by source.

Run: hydraulics-dev python.exe -I -B h7r6_bound_source.py <out.txt> <t4h dir> [...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BAR = 1.0e5
LEGS = ["FL", "FR", "RL", "RR"]
SRC = ["extend_bound", "pilot_model", "previous_moving", "retract_hold", "retract_tracker"]


def main() -> None:
    out_path = Path(sys.argv[1])
    lines, sources, margins = [], Counter(), []
    for folder in sys.argv[2:]:
        for path in sorted(Path(folder).glob("*.npz")):
            d = np.load(path, allow_pickle=False)
            if "jp3_t_s" not in d.files:
                continue
            cls = d["jp3_class"]
            ptr = d["jp3_p_tr_Pa"]
            used = d["jp3_used_bound_Pa"]
            for leg in range(4):
                with np.errstate(invalid="ignore"):
                    hit = np.flatnonzero(((cls[:, leg] == 2) | (cls[:, leg] == 4))
                                         & (ptr[:, leg] > used[:, leg] + 1.0))
                for r in hit:
                    start = int(r)
                    while start > 0 and cls[start - 1, leg] == 2:
                        start -= 1
                    lock = start - 1
                    while lock > 0 and d["jp3_model_bound_source"][lock, leg] < 0:
                        lock -= 1
                    code = int(d["jp3_model_bound_source"][lock, leg])
                    name = SRC[code] if code >= 0 else "none"
                    inh = bool(d["jp3_model_bound_inherited"][lock, leg])
                    model = float(d["jp3_model_bound_Pa"][lock, leg])
                    truth = float(ptr[start - 1, leg])
                    sources[(name, inh)] += 1
                    margins.append((used[r, leg] - truth) / BAR)
                    lines.append(
                        f"{path.stem:50s} {LEGS[leg]} breach t {d['jp3_t_s'][r]:6.1f}: lock-read "
                        f"source {name}{' (inherited)' if inh else ''} model {model / BAR:6.2f} "
                        f"truth before carry {truth / BAR:6.2f} | used {used[r, leg] / BAR:6.2f} "
                        f"carry {d['jp3_carry_bound_Pa'][r, leg] / BAR:6.2f} "
                        f"p_tr {ptr[r, leg] / BAR:6.2f}")
    lines.append(f"sources at the lock read before the carry: {dict(sources)}")
    lines.append(f"used bound - locked truth before the carry: min {min(margins):.2f} "
                 f"max {max(margins):.2f} bar over {len(margins)} breach reads")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[-2:]))


if __name__ == "__main__":
    main()
