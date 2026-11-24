"""Counterfactual record run (79495405 records_after_stop/C_a2): per line the plant, arm, key,
final phase, t_ready_back, gate pass, minimum force after W, rod fallbacks with reason, and the
A(i) / B3 activity from the line's lsb record when present. Prints a table, writes CSV."""
import csv
import json
import re
import sys
from pathlib import Path

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
           r"\records_after_stop\C_a2\counterfactual.jsonl")
REASON = re.compile(r"INFO_ROD_PRESSURE_FAULT_REASON:(\w+):(\w+)")


def main(out_csv: Path) -> None:
    rows = []
    for text in RUN.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row.get("job", {})
        twin = job.get("twin") or {}
        setting = job.get("setting", "")
        ev = row.get("event_output") or {}
        events = row.get("events") or []
        reasons = sorted({f"{m.group(1)}:{m.group(2)}" for e in events
                          for m in [REASON.search(str(e[1]))] if m})
        fb_t = sorted({round(float(e[0]), 1) for e in events if "WARN_ROD_PRESSURE_FALLBACK" in str(e[1])})
        fmin = ev.get("min_F_after_W_kN") or {}
        rows.append({
            "setting": setting, "key": f"{twin.get('level')}-{twin.get('leg')}-Fs{twin.get('fs_kN')}",
            "offset": job.get("offset_s"), "final": ev.get("final_phase"),
            "t_back": ev.get("t_ready_back_s"), "pass": ev.get("pass"),
            "failed_gates": ",".join(k for k, v in (ev.get("gates") or {}).items() if v is False),
            "Fmin_W_kN": round(min(fmin.values()), 2) if fmin else None,
            "fallback": ";".join(reasons), "fallback_t": ";".join(str(t) for t in fb_t),
            "commands_sha256": (row.get("commands_sha256") or "")[:10],
            "error": row.get("error"),
        })
    rows.sort(key=lambda r: (r["key"], r["offset"], r["setting"]))
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['key']:16s} o{r['offset']:<5} {r['setting']:16s} final {str(r['final']):6s} "
              f"t_back {str(r['t_back']):6s} pass {str(r['pass']):5s} gates[{r['failed_gates']}] "
              f"Fmin {r['Fmin_W_kN']} fb[{r['fallback']}@{r['fallback_t']}] {r['commands_sha256']}"
              + (f" ERROR {r['error']}" if r["error"] else ""))
    print("lines", len(rows))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
