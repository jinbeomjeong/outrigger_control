"""Context of each J-P3a breach read (record `jp3a_first_breach_t_s` per leg): at the T4h read of
that time, the phase, the leg's command and lsb input / output, A(i) / A(ii) flags, the B3
pre-twist leg, jp3 class name, used bound and head read; plus the grid timing census."""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405")
SOURCES = {"grid": (CAUSE / "confirm_a1/confirm_b.jsonl", CAUSE / "confirm_a1/confirm_b_t4h"),
           "sens": (CAUSE / "records_after_stop/B_a1/sens.jsonl", CAUSE / "records_after_stop/B_a1/sens_t4h")}
LEGS = ("FL", "FR", "RL", "RR")


def main(out_csv: Path) -> None:
    out = []
    timing = Counter()
    for name, (jsonl, t4h_dir) in SOURCES.items():
        for text in jsonl.read_text(encoding="utf-8").splitlines():
            if not text.strip():
                continue
            row = json.loads(text)
            twin = row["job"].get("twin") or {}
            ebc = (row.get("hydraulics_record") or {}).get("extend_bound_check") or {}
            first = ebc.get("jp3a_first_breach_t_s") or [None] * 4
            hit = any(t is not None for t in first)
            if name == "grid":
                timing[(twin.get("timing"), hit)] += 1
            if not hit:
                continue
            t4h = t4h_dir / row["t4h_file"]
            with np.load(t4h, allow_pickle=False) as d:
                t = d["t_s"]
                arrays = {k: d[k] for k in ("phase", "command_m_s", "lsb_input_m_s", "lsb_output_m_s",
                                            "lsb_a1_on", "lsb_a2_on", "lsb_pre_twist_leg",
                                            "jp3_class", "jp3_used_bound_Pa", "rod_pressure_Pa",
                                            "locked") if k in d.files}
                names = list(d["jp3_class_names"]) if "jp3_class_names" in d.files else []
            for leg, tb in enumerate(first):
                if tb is None:
                    continue
                i = int(np.argmin(np.abs(t - tb)))
                cls = int(arrays["jp3_class"][i, leg])
                out.append({
                    "source": name, "setting": row["job"].get("setting"), "file": row["t4h_file"],
                    "timing": twin.get("timing"), "event": twin.get("event"), "leg": LEGS[leg],
                    "t_breach_s": tb, "t_event_s": row.get("t_event_s"), "phase": str(arrays["phase"][i]),
                    "u_mm_s": round(float(arrays["command_m_s"][i, leg]) * 1e3, 3),
                    "u_prev_mm_s": round(float(arrays["command_m_s"][i - 1, leg]) * 1e3, 3),
                    "lsb_in_prev_mm_s": round(float(arrays["lsb_input_m_s"][i - 1, leg]) * 1e3, 3),
                    "lsb_out_prev_mm_s": round(float(arrays["lsb_output_m_s"][i - 1, leg]) * 1e3, 3),
                    "a1_prev": bool(arrays["lsb_a1_on"][i - 1, leg]), "a1_now": bool(arrays["lsb_a1_on"][i, leg]),
                    "a2_prev": bool(arrays["lsb_a2_on"][i - 1, leg]),
                    "pre_twist_leg_prev": int(arrays["lsb_pre_twist_leg"][i - 1]),
                    "pre_twist_any_5s": bool((arrays["lsb_pre_twist_leg"][max(0, i - 50):i + 1] >= 0).any()),
                    "since_event_a1_reads": int(arrays["lsb_a1_on"][(t >= (row.get("t_event_s") or 0)) & (t < tb), leg].sum()),
                    "since_event_a2_reads": int(arrays["lsb_a2_on"][(t >= (row.get("t_event_s") or 0)) & (t < tb), leg].sum()),
                    "since_event_b3_reads": int((arrays["lsb_pre_twist_leg"][(t >= (row.get("t_event_s") or 0)) & (t < tb)] >= 0).sum()),
                    "since_event_lsb_changed_reads": int((np.abs(arrays["lsb_input_m_s"][(t >= (row.get("t_event_s") or 0)) & (t < tb), leg]
                                                                 - arrays["lsb_output_m_s"][(t >= (row.get("t_event_s") or 0)) & (t < tb), leg]) > 1e-9).sum()),
                    "jp3_class": names[cls] if 0 <= cls < len(names) else cls,
                    "locked_prev": bool(arrays["locked"][i - 1, leg]),
                    "rod_bar": round(float(arrays["rod_pressure_Pa"][i, leg]) / 1e5, 2),
                    "used_bound_bar": round(float(arrays["jp3_used_bound_Pa"][i, leg]) / 1e5, 2),
                })
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    print("grid timing census (timing, has breach):", dict(timing))
    for key in ("phase", "jp3_class", "a1_prev", "a2_prev", "pre_twist_any_5s", "locked_prev",
                "since_event_a1_reads", "since_event_a2_reads", "since_event_b3_reads",
                "since_event_lsb_changed_reads", "source"):
        print(key, Counter(r[key] for r in out))
    dt = [r["t_breach_s"] - r["t_event_s"] for r in out if r["t_event_s"] is not None]
    print("t_breach - t_event: min %.1f median %.1f max %.1f" % (min(dt), float(np.median(dt)), max(dt)))
    print("u_prev (mm/s) range", min(r["u_prev_mm_s"] for r in out), max(r["u_prev_mm_s"] for r in out))
    print("lsb changed prev read", sum(1 for r in out if abs(r["lsb_in_prev_mm_s"] - r["lsb_out_prev_mm_s"]) > 1e-6))
    for r in out[:8]:
        print(json.dumps(r))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
