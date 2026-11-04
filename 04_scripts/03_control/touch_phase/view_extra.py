"""Extra rows: R2 with its stored decision, S7 and S1 over TOUCH phases, base and candidate."""
from __future__ import annotations

import json
from pathlib import Path

TP = Path(__file__).resolve().parents[3] / "06_analysis" / "02_control" / "touch_phase"
rows = []
for line in (TP / "extra.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    job = r["job"]
    if "error" in r:
        print(job, r["error"][:200])
        continue
    rows.append(dict(case=job["case"], cand=job["cand"] or "E", eps=job["eps"], phase=r["final_phase"], cls=r.get("harness_class"),
                     fail=r.get("failed_rows"), Fmin=r["forces"]["after_liftoff"]["min_kN"], ready=r["times"]["t_first_ready_s"],
                     stroke=round(r["max_stroke_reading_mm"], 1), rut=r.get("rut_ready_mm"),
                     ev=[e for e in r["events"] if e[1].startswith(("INFO_LOC_REVOKED", "WARN", "FAULT"))][:4]))
rows.sort(key=lambda x: (x["case"], x["cand"], x["eps"]))
for x in rows:
    print(x)
(TP / "extra_table.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
