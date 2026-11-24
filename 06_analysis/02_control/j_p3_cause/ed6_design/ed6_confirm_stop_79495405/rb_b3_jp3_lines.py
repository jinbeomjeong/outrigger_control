"""Lines with J-P3a breach reads (record `hydraulics_record.extend_bound_check`) in the record-only
runs: B_a1 sens / j9_main and the grid lines (confirm_a1/confirm_b.jsonl, opened after the stop as
a record). Prints the record keys of one breaching line once, then per breaching line the key,
setting, breach counts and any per-leg / time fields found."""
import json
import sys
from pathlib import Path

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405")
FILES = {"sens": CAUSE / "records_after_stop/B_a1/sens.jsonl",
         "j9main": CAUSE / "records_after_stop/B_a1/j9_main.jsonl",
         "grid": CAUSE / "confirm_a1/confirm_b.jsonl"}


def tag(job):
    twin = job.get("twin") or {}
    if twin:
        return (f"{job.get('case')} {twin.get('level')}-{twin.get('leg')}-Fs{twin.get('fs_kN')}"
                f"-o{job.get('offset_s')}-{twin.get('event', '')}-{twin.get('timing', '')}")
    return f"{job.get('case')} o{job.get('offset_s')} e{job.get('eps')}"


def main(show_keys: bool) -> None:
    shown = False
    for name, path in FILES.items():
        n = hits = 0
        for text in path.read_text(encoding="utf-8").splitlines():
            if not text.strip():
                continue
            row = json.loads(text)
            n += 1
            ebc = ((row.get("hydraulics_record") or {}).get("extend_bound_check") or {})
            a = ebc.get("jp3a_breach_reads") or [0]
            if not sum(a if isinstance(a, list) else [a]):
                continue
            hits += 1
            if show_keys and not shown:
                print("record keys:", sorted(ebc))
                shown = True
            extra = {k: ebc.get(k) for k in ("jp3a_first_breach_t_s", "jp3a_min_gap_bar",
                                             "jp3a_min_gap_t_s", "jp3a_by_plant_state",
                                             "jp3a_reads", "jp3_judged_row")}
            ev = row.get("event_output") or {}
            print(name, row["job"].get("setting"), tag(row["job"]), "jp3a", a,
                  "t_event", row.get("t_event_s"), "pass", ev.get("pass"),
                  json.dumps(extra, ensure_ascii=False)[:500])
        print(f"== {name}: lines {n}, lines with jp3a breach {hits}")


if __name__ == "__main__":
    main(len(sys.argv) > 1)
