"""Write k1soil/expected_before_run.json: table values, stored P3b timing that bears on the 60 s base length, cost basis. No acceptance rule. Read only otherwise.

Usage: python -I -B -X utf8 write_expected.py
"""
from __future__ import annotations

import json
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono/k1soil"
P3B = MAIN / "07_results/S9/batch_P3b_20261026_122444"
ACCEPT = MAIN / "06_analysis/02_control/touch_phase/acceptance"


def stored(case: str) -> dict:
    res = json.loads((P3B / case / "result.json").read_text(encoding="utf-8"))
    t0 = float(res["t_loop_start_s"])
    return {"t_loop_start_s": t0, "phases_loop_s": [[round(float(p["t_s"]) - t0, 2), p["phase"]] for p in res["phases"]], "wall_s": res.get("wall_s"), "us_per_step": res.get("us_per_step"), "note": "no soil patch, older controller; timing guide only"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = {"written_before_run": True, "note": "Harness table values and expectations; control-expert judges.", "code": {"commit": "74032beae72c7e44858e41384bc54c263e724fd3", "c2_sha256": "28482b8d5678c3e1079c9dd89046013bd60cac718e0e8efa195101a36236df67"},
           "table": "touch_phase/chrono/next_soil_rows.md section 1 rows 1, 2, 5",
           "harness_values": {"1": {"key": "A|G1|FL|Fs0 RE1bF", "adjacent_min_on_off_kN": [35.16, 35.16], "RL_on_off_kN": [54.93, 40.38], "event_leg_lift_sum_s": 1.075, "reapproach_on_off": [4, 5], "re_ready_on_off_s": [25.8, 26.1]},
                              "2": {"key": "A|G1|FL|Fs8 RE1bF", "adjacent_min_on_off_kN": [38.71, 38.71], "RL_on_off_kN": [60.99, 48.93], "event_leg_lift_sum_s": 0.966, "reapproach_on_off": [3, 4], "re_ready_on_off_s": [27.7, 24.2]},
                              "3": {"key": "A|G1|RR|Fs0 RE1bF", "adjacent_min_on_off_kN": [71.80, 71.80], "FR_on_off_kN": [107.76, 106.93], "event_leg_lift_sum_s": 0.304, "reapproach_on_off": [2, 2], "re_ready_on_off_s": [28.2, 28.1]}},
           "expected": {"base": "60 s loop reaches LOC and the first DONE, else that row stops (no rerun guessed).", "pairs": "On and off use the same event time; on `t<loop s>` equals off `mid@base` within float rounding, one step difference possible; report t_ev_s of both.",
                        "before_event": "G1 rows have a flat floor: D_hat within the 1 kN band gives no hold, then commands equal off until K1 acts after the event (first difference after t_ev). A hold, if any, shows as INFO_TOUCH_TWIST_HOLD and an earlier first difference.",
                        "K1": "RE1bF rows on: re-approach starts one sample later, `leg_reapproach_deferred:*:retrigger` present, start count per the table. Chrono may be worse than the harness on soft events (paper v4 4.2).",
                        "item_9": "The checkout has no ce21ffa; the item-9 replay is rejudged with ce21ffa afterwards."},
           "stored_timing": {c: stored(c) for c in ("P3b_G1_B_top_Fs0", "P3b_G1_B_top_Fs8")},
           "cost": "Per table: events 2.6 to 4.1 h, bases 1.3 to 2 h; base 68 s sim x G1 5.5 ms/step upper = 1.04 h on a free pool."}
    (OUT / "expected_before_run.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(doc["stored_timing"], ensure_ascii=False))
    print("acceptance folder", ACCEPT.exists(), [p.name for p in ACCEPT.glob("*")][:10] if ACCEPT.exists() else None)


if __name__ == "__main__":
    main()
