"""Grid (confirm_b, opened after the stop as a record): for the 11 opportunity failures of
`A_a1/grid_judge.json`, the failing gates, final phase, t_ready_back, minimum force after W, the
longest A(i) blind-band dwell in LEVEL, B3 reads and the stored V0 pass flag; and the failing
gate census of all grid lines (V0 pass and fail)."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405")
GRID = CAUSE / "confirm_a1/confirm_b.jsonl"
T4H = CAUSE / "confirm_a1/confirm_b_t4h"
JUDGE = CAUSE / "records_after_stop/A_a1/grid_judge.json"
KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_design\keys"
            r"\confirm_b_grid192.json")
U_HOLD = 2.09243016e-4


def band(path):
    with np.load(path, allow_pickle=False) as d:
        ph, u, lk = d["phase"], d["command_m_s"], d["locked"]
        pre = d["lsb_pre_twist_leg"]
    level = ph == "level"
    b = lk & (np.abs(u) > 1e-12) & (np.abs(u) <= U_HOLD) & level[:, None]
    longest = 0
    for leg in range(4):
        run = 0
        for flag in b[:, leg]:
            run = run + 1 if flag else 0
            longest = max(longest, run)
    return round(longest * 0.1, 1), int((pre >= 0).sum())


def main():
    failing = set(json.loads(JUDGE.read_text(encoding="utf-8"))["opportunity_failures"])
    v0 = {line["t4h_file"]: line["v0_pair"]["v0_pass"]
          for line in json.loads(KEYS.read_text(encoding="utf-8"))["lines"]}
    census = Counter()
    for text in GRID.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        ev = row.get("event_output") or {}
        gates = [k for k, v in (ev.get("gates") or {}).items() if v is False]
        name = row["t4h_file"]
        census[(v0.get(name), ev.get("pass"))] += 1
        if name in failing:
            fmin = ev.get("min_F_after_W_kN") or {}
            longest, b3 = band(T4H / name)
            print(name, "gates", gates, "final", ev.get("final_phase"), "t_back", ev.get("t_ready_back_s"),
                  "Fmin_W", round(min(fmin.values()), 2) if fmin else None, "band", longest, "b3_reads", b3,
                  "v0_pass", v0.get(name))
    print("census (v0_pass, VBL pass):", dict(census))


if __name__ == "__main__":
    main()
