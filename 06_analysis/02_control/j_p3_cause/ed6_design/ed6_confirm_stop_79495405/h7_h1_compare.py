"""Part D (records_after_stop/D_a1): per grid key and arm the J-P3a breach counts of the line's
③ record (`hydraulics_record.extend_bound_check`, the in-run path 1 computation), and from the
T4h, per leg, the probe-phase `carry_ext` read after the event with the smallest gap
(used bound - rod read; negative = above the bound): rod read, used bound, gap, and the A(ii)
activity / lsb command changes of that leg since the event. No judgement; a comparison."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
         r"\records_after_stop\D_a1")
LEGS = ("FL", "FR", "RL", "RR")


def key_of(job):
    twin = job.get("twin") or {}
    return (f"R12 {twin.get('level')}-{twin.get('leg')}-Fs{twin.get('fs_kN')}-o{job.get('offset_s')}"
            f"-{twin.get('event')}-{twin.get('timing')}")


def first_carry_ext(t4h, t_event):
    with np.load(t4h, allow_pickle=False) as d:
        t, ph = d["t_s"], d["phase"]
        cls = d["jp3_class"]
        names = [str(x) for x in d["jp3_class_names"]]
        rod = d["rod_pressure_Pa"]
        bound = d["jp3_used_bound_Pa"]
        a2 = d["lsb_a2_on"] if "lsb_a2_on" in d.files else np.zeros_like(rod, dtype=bool)
        lin = d["lsb_input_m_s"] if "lsb_input_m_s" in d.files else None
        lout = d["lsb_output_m_s"] if "lsb_output_m_s" in d.files else None
    ce = names.index("carry_ext")
    out = []
    after = t >= t_event
    for leg in range(4):
        idx = [i for i in np.flatnonzero(after) if cls[i, leg] == ce and ph[i] == "probe"]
        if not idx:
            continue
        gaps = [bound[i, leg] - rod[i, leg] for i in idx]
        i = idx[int(np.argmin(gaps))]
        window = after & (t < t[i])
        changed = 0
        if lin is not None:
            changed = int((np.abs(lin[window, leg] - lout[window, leg]) > 1e-9).sum())
        out.append({"leg": LEGS[leg], "t_s": round(float(t[i]), 1),
                    "rod_bar": round(float(rod[i, leg]) / 1e5, 2),
                    "bound_bar": round(float(bound[i, leg]) / 1e5, 2),
                    "gap_bar": round(float(bound[i, leg] - rod[i, leg]) / 1e5, 2),
                    "a2_reads_since_event": int(a2[window, leg].sum()),
                    "lsb_changed_reads_since_event": changed})
    return out


def main(out_csv: Path) -> None:
    table = defaultdict(dict)
    rows_csv = []
    for text in (D / "grid_cause.jsonl").read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row["job"]
        arm = job["setting"]
        ebc = (row.get("hydraulics_record") or {}).get("extend_bound_check") or {}
        a = ebc.get("jp3a_breach_reads") or [0, 0, 0, 0]
        b = ebc.get("jp3b_breach_over_tol_reads") or [0, 0, 0, 0]
        c = ebc.get("jp3c_breach_reads") or [0, 0, 0, 0]
        firsts = first_carry_ext(D / "grid_cause_t4h" / row["t4h_file"], row.get("t_event_s") or 0.0)
        k = key_of(job)
        table[k][arm] = (sum(a), sum(b), sum(c), ebc.get("jp3a_first_breach_t_s"))
        for f in firsts:
            rows_csv.append({"key": k, "arm": arm, **f, "jp3a_breach_leg":
                             (a[LEGS.index(f["leg"])] if isinstance(a, list) else None)})
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_csv[0]))
        writer.writeheader()
        writer.writerows(rows_csv)
    arms = sorted({arm for v in table.values() for arm in v})
    print("arms", arms)
    for k in sorted(table):
        cells = []
        for arm in arms:
            a, b, c, first = table[k].get(arm, (None, None, None, None))
            cells.append(f"{arm}: a{a} b{b} c{c} first{first}")
        print(k, " | ".join(cells))
    totals = {arm: [0, 0] for arm in arms}
    for v in table.values():
        for arm, (a, b, c, _) in v.items():
            totals[arm][0] += a
            totals[arm][1] += 1 if a else 0
    print("totals (jp3a reads, lines with breach):", totals)
    print("first carry_ext reads (all arms):")
    for r in rows_csv:
        print("  ", json.dumps(r))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
