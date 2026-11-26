"""d02: phase timelines of the d00 reruns (T4h ``phase`` at 10 Hz).

Per run: the phase segments (name, start, end, length), the first READY time, every PROBE
segment and the LEVEL segment right after each PROBE (the re-level), the net motor-stroke change
of each leg over each PROBE segment, and the first command after it.

Usage: conda run -n dynamics-dev python -I -B d02_timelines.py <d00 scratch dir>
Output: d02_timelines.json, d02_relevel.csv (this folder).
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")


def segments(phase: np.ndarray, t: np.ndarray) -> list[dict]:
    segs = []
    start = 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            segs.append({"phase": str(phase[start]), "i0": start, "i1": i - 1,
                         "t0": round(float(t[start]), 2), "t1": round(float(t[i - 1]), 2),
                         "len_s": round(float(t[i - 1] - t[start] + 0.1), 2)})
            start = i
    return segs


def main() -> int:
    scratch = Path(sys.argv[1])
    out, rows = {}, []
    for path in sorted((scratch / "t4h").glob("*.npz")):
        z = np.load(path, allow_pickle=False)
        t = z["t_s"]
        ph = np.char.lower(z["phase"].astype(str))
        segs = segments(ph, t)
        ready = [s["t0"] for s in segs if s["phase"] == "ready"]
        stroke = z["motor_stroke_m"]
        cmd = z["command_m_s"]
        rec = {"segments": [{k: v for k, v in s.items() if k not in ("i0", "i1")} for s in segs],
               "t_first_ready_s": ready[0] if ready else None, "t_end_s": round(float(t[-1]), 2)}
        n_probe = 0
        for k, s in enumerate(segs):
            if s["phase"] != "probe":
                continue
            n_probe += 1
            nxt = segs[k + 1] if k + 1 < len(segs) else None
            i0, i1 = s["i0"], s["i1"]
            net = (stroke[i1] - stroke[max(i0 - 1, 0)]) * 1e3
            row = {"run": path.stem, "probe_round": n_probe, "probe_t0": s["t0"],
                   "probe_len_s": s["len_s"],
                   "next_phase": None if nxt is None else nxt["phase"],
                   "next_len_s": None if nxt is None else nxt["len_s"],
                   **{f"net_{leg}_mm": round(float(net[j]), 3) for j, leg in enumerate(LEGS)}}
            if nxt is not None:
                first = cmd[nxt["i0"]] * 1e3
                row.update({f"cmd0_{leg}_mm_s": round(float(first[j]), 3)
                            for j, leg in enumerate(LEGS)})
            rows.append(row)
        out[path.stem] = rec
    (OUT / "d02_timelines.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    with (OUT / "d02_relevel.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({k for r in rows for k in r}, key=lambda k: (k != "run", k))
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    for stem, rec in out.items():
        print(stem, "ready", rec["t_first_ready_s"], "end", rec["t_end_s"])
    for r in rows:
        print(r["run"], r["probe_round"], r["probe_t0"], r["probe_len_s"], r["next_phase"],
              r["next_len_s"], [r.get(f"net_{l}_mm") for l in LEGS],
              [r.get(f"cmd0_{l}_mm_s") for l in LEGS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
