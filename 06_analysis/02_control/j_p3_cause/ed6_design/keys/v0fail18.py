"""Edition 6 confirmation (나): which gates the stored V0 grid rows failed, for the lines of
confirm_b_grid192.json with v0_pass false (stored V0 grid, public reference data).

Usage: python -I -B v0fail18.py <repo root> <keys folder>
Writes confirm_b_v0fail18.csv / .json into the keys folder (never overwrites).
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

root, keys = Path(sys.argv[1]), Path(sys.argv[2])
grid_path = keys / "confirm_b_grid192.json"
grid_bytes = grid_path.read_bytes()
lines = [line for line in json.loads(grid_bytes)["lines"] if not line["v0_pair"]["v0_pass"]]
stored = {}
rows = []
for line in lines:
    pair, job = line["v0_pair"], line["job"]
    if pair["file"] not in stored:
        stored[pair["file"]] = json.loads((root / pair["file"]).read_text(encoding="utf-8"))
    result = next(r for r in stored[pair["file"]]["results"] if r["key"] == pair["key"])
    run = result["runs"][pair["run_id"]]
    gates = run["gates"]
    failed = sorted(name for name, ok in gates.items() if not ok)
    rows.append({
        "t4h_file": line["t4h_file"], "level": job["twin"]["level"], "leg": job["twin"]["leg"],
        "fs_kN": job["twin"]["fs_kN"], "timing": job["twin"]["timing"],
        "event": job["twin"]["event"], "offset_s": job["offset_s"],
        "v0_file": Path(pair["file"]).name, "v0_key": pair["key"], "run_id": pair["run_id"],
        "hash_match": run["commands_sha256"] == pair["v0_commands_sha256"],
        "event_match": run["event"] == job["twin"]["event"]
        and float(run["offset_s"]) == float(job["offset_s"]),
        "pass": run["pass"], "gate_set": "fast" if run.get("fast") else "slow",
        "failed_gates": ";".join(failed), "fault0_failed": "fault0" in failed,
        "fault_events": ";".join(str(e) for e in (run.get("fault_events") or [])),
        "fault_periods": run.get("fault_periods"), "final_phase": run.get("final_phase"),
        "warnings": ";".join(sorted({str(w).split(":", 1)[0] for w in run.get("warnings") or []})),
    })
out_csv, out_json = keys / "confirm_b_v0fail18.csv", keys / "confirm_b_v0fail18.json"
if out_csv.exists() or out_json.exists():
    raise SystemExit("output exists")
with out_csv.open("x", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
summary = {"source": {"confirm_b_grid192.json": hashlib.sha256(grid_bytes).hexdigest(),
                      **{Path(name).name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in stored}},
           "lines": len(rows), "hash_match_all": all(r["hash_match"] for r in rows),
           "event_match_all": all(r["event_match"] for r in rows),
           "pass_false_all": all(r["pass"] is False for r in rows),
           "fault0_failed_lines": sum(r["fault0_failed"] for r in rows),
           "fault_event_lines": sum(bool(r["fault_events"]) for r in rows),
           "failed_gate_counts": {}, "rows": rows,
           "script": "scratchpad v0fail18.py (python-expert, 2026-11-24)"}
for r in rows:
    for gate in filter(None, r["failed_gates"].split(";")):
        summary["failed_gate_counts"][gate] = summary["failed_gate_counts"].get(gate, 0) + 1
with out_json.open("x", encoding="utf-8") as handle:
    handle.write(json.dumps(summary, indent=1) + "\n")
print(json.dumps({k: summary[k] for k in ("lines", "hash_match_all", "event_match_all",
                                          "pass_false_all", "fault0_failed_lines",
                                          "fault_event_lines", "failed_gate_counts")}))
for r in rows:
    print(r["t4h_file"], r["gate_set"], r["failed_gates"], "|F", r["fault_events"],
          r["fault_periods"], r["final_phase"], "|W", r["warnings"])
