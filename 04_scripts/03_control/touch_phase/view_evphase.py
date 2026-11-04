"""Event phase sweep on the harness: R12 event start offset, R16 mirror-gap TOUCH phase. Minima in kN.
Output: stdout and evphase_table.json."""
from __future__ import annotations

import json
from pathlib import Path

TP = Path(__file__).resolve().parents[3] / "06_analysis" / "02_control" / "touch_phase"
rows = []
for line in (TP / "evphase.jsonl").read_text(encoding="utf-8").splitlines():
    rec = json.loads(line)
    job = rec["job"]
    if "error" in rec:
        print(job, rec["error"][:200])
        continue
    eo = rec["event_output"]
    row = {"case": job["case"], "gap": job["gap"], "eps": job["eps"], "offset_s": job.get("offset_s"),
           "t_event": rec.get("timeline"), "min_after_event": eo["min_F_after_event_kN"],
           "adj_min_W": eo["adj_min_F_in_W_kN"], "after_W": eo["min_F_after_W_kN"],
           "D_te": rec["D_te"], "tau_te": rec["tau_te"], "hash": rec["commands_sha256"][:12]}
    rows.append(row)
rows.sort(key=lambda r: (r["case"], r["offset_s"], r["eps"]))
for r in rows:
    print(r["case"], r["gap"], "eps", r["eps"], "offs", r["offset_s"], "min", r["min_after_event"], "adjW", r["adj_min_W"], "D_te", round(r["D_te"], 1), "tau", round(r["tau_te"], 3))
(TP / "evphase_table.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
