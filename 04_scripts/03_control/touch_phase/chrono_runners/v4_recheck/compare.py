"""Print old vs new values of the 14 recheck cases from expected_before_run.json and recheck_values.json. Read only.

Usage: python -I -B -X utf8 compare.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono\v4_recheck")
LEG_KEYS = ("min_interval_kN", "t_rel_s", "min_sample_1ms_kN", "under_F_min_interval_s", "airborne_s")


def short(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, list):
        return [short(x) for x in v]
    return v


def main() -> None:
    old = json.loads((OUT / "expected_before_run.json").read_text(encoding="utf-8"))["stored_batch_values"]
    doc = json.loads((OUT / "recheck_values.json").read_text(encoding="utf-8"))
    print("meta", {k: doc["meta"][k] for k in ("rows", "failed", "hold")}, "head", doc["code_state"]["main_head"])
    for cid, n in doc["cases"].items():
        o = old[cid]
        print("=====", cid, "wall", round(n["wall_s"], 1), "contact", n["contact"], "flow", n["flow_limit"], "end", n["s8_end"], "phase_at_event", n["phase_at_event"])
        print(" ready old/new", short(o["ready_t_s"]), short(n["ready_t_s"]), "event", short(o["event_t_s"]), short(n["event_t_s"]), "probe", short(o["first_probe_t_s"]), short(n["first_probe_t_s"]))
        print(" first diff", n["first_diff_vs_stored_t_s"])
        for item in sorted(set(o["rows"]) | set(n["rows"])):
            a, b = o["rows"].get(item, {}).get("value"), n["rows"].get(item, {}).get("value")
            mark = "" if a == b else " <-- diff"
            if item.startswith(("3 F_min", "item 9", "6 re-READY", "RE1b re-READY", "SS", "4 max", "C2 REANCHOR", "REANCHOR", "6 min", "G4 item 6")) or "re-READY" in item:
                print(f"  {item[:60]:60s} old {short(a)} new {short(b)} passed {n['rows'].get(item, {}).get('passed')}{mark}")
        print("  note new F3:", n["rows"].get("3 F_min (1 ms)", {}).get("note"))
        if n["legs_after_event"]:
            for leg in n["legs_after_event"]:
                print("  ", leg, "old", [short(o["legs_after_event"][leg][k]) for k in LEG_KEYS], "new", [short(n["legs_after_event"][leg][k]) for k in LEG_KEYS])
        else:
            print("   after READY new", {k: short(v["min_sample_1ms_kN"]) for k, v in n["legs_after_first_ready"].items()})
        print("  dip", n["touch_dip_held"], "warn", n["warn_fault"], "failed", n["failed_rows"])
        print("  events added", [e for e in n["events"] if e.split(" ", 1)[1] not in {x.split(" ", 1)[1] for x in o["events"]}][:12])
        print("  events removed", [e for e in o["events"] if e.split(" ", 1)[1] not in {x.split(" ", 1)[1] for x in n["events"]}][:12])
    print("J_P M1 sum", sum(c["rows"]["item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"]["value"][0] for c in doc["cases"].values()))
    print("J_C M1 sum", sum(c["rows"]["item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)"]["value"][0] for c in doc["cases"].values()))


if __name__ == "__main__":
    main()
