"""Post-event LEVEL of the confirmation (가) R12 G4 rows: for each T4h file the post-event LEVEL
duration, the end phase, the A(i) activity per leg (reads with lsb_a1_on, A(i) cap events),
the command size and the oil-coordinate stroke range in the last 20 s of that LEVEL, and the
stall signature (4 legs |u| <= 1.05 mm/s and stroke range < 1 mm in the last 20 s). CSV out."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

T4H = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\confirm_a1\confirm_a_t4h")
LEGS = ("FL", "FR", "RL", "RR")


def segments(phase):
    out, start = [], 0
    for i in range(1, len(phase) + 1):
        if i == len(phase) or phase[i] != phase[start]:
            out.append((str(phase[start]), start, i - 1))
            start = i
    return out


def main(out_csv: Path) -> None:
    rows = []
    for path in sorted(T4H.glob("R12_*.npz")):
        with np.load(path, allow_pickle=False) as d:
            t = d["t_s"]
            ph = d["phase"]
            u = d["command_m_s"]
            s = d["motor_stroke_m"]
            a1 = d["lsb_a1_on"]
            a1f = d["lsb_a1_floor_m_s"]
            meta = json.loads(str(d["meta_json"]))
        segs = segments(ph)
        levels = [sg for sg in segs if sg[0] == "level"]
        if len(levels) < 2:
            continue
        _, i0, i1 = levels[-1]
        dur = t[i1] - t[i0]
        tail = (t >= t[i1] - 20.0) & (np.arange(len(t)) >= i0) & (np.arange(len(t)) <= i1)
        u_tail = np.abs(u[tail]) * 1e3
        s_rng = (s[tail].max(axis=0) - s[tail].min(axis=0)) * 1e3
        caps = [e for e in meta["events"] if "LSB_CAP" in e[1]]
        a1_reads = a1[i0:i1 + 1].sum(axis=0)
        stall = bool((u_tail.max(axis=0) <= 1.05 + 1e-9).all() and (s_rng < 1.0).all())
        rows.append({
            "file": path.name, "end_phase": str(ph[-1]), "t_end_s": round(float(t[-1]), 1),
            "level2_start_s": round(float(t[i0]), 1), "level2_dur_s": round(float(dur), 1),
            **{f"a1_reads_{leg}": int(a1_reads[k]) for k, leg in enumerate(LEGS)},
            "a1_cap_events": len(caps),
            **{f"u_tail_max_{leg}_mm_s": round(float(u_tail.max(axis=0)[k]), 3)
               for k, leg in enumerate(LEGS)},
            **{f"s_tail_range_{leg}_mm": round(float(s_rng[k]), 3) for k, leg in enumerate(LEGS)},
            "a1_floor_max_mm_s": round(float(np.nanmax(np.abs(a1f[i0:i1 + 1])) * 1e3), 3),
            "stall_signature_tail20": stall,
        })
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        if r["level2_dur_s"] > 35 or r["end_phase"] != "ready":
            print(json.dumps(r))
    print("rows", len(rows))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
