"""PS-7 regression table: candidate against E on the same keys. T-3 mm, T-4 deg, forces kN, READY s."""
from __future__ import annotations

import json
import sys
from pathlib import Path

TP = Path(__file__).resolve().parents[3] / "06_analysis" / "02_control" / "touch_phase"
cand = sys.argv[1]
base = {r["key"]: r for r in json.loads((TP / "ps7_E.json").read_text(encoding="utf-8"))}
rows = []
for rec in json.loads((TP / f"ps7_{cand}.json").read_text(encoding="utf-8")):
    b = base[rec["key"]]
    tb, tc = b.get("touch", {}), rec.get("touch", {})
    row = {"key": rec["key"], "pass_E": b.get("pass"), "pass_c": rec.get("pass"),
           "min_E": b.get("min_F_after_liftoff_kN"), "min_c": rec.get("min_F_after_liftoff_kN"),
           "ready_E": b.get("t_ready"), "ready_c": rec.get("t_ready"),
           "T3_E": tb.get("extra_stroke_mm"), "T3_c": tc.get("extra_stroke_mm"),
           "T4_E": tb.get("max_abs_att_deg"), "T4_c": tc.get("max_abs_att_deg"),
           "T4_same": tb.get("max_abs_att_deg") == tc.get("max_abs_att_deg"),
           "T1_E": tb.get("duration_s"), "T1_c": tc.get("duration_s"),
           "D_hat": rec["trim"].get("D_hat_kN"), "dtau": rec["trim"].get("delta_tau_mm"),
           "ev_new": [e for e in rec.get("events", []) if e[1] not in [x[1] for x in b.get("events", [])]],
           "err": rec.get("error")}
    rows.append(row)
    print(rec["key"].replace("ps7|", "").replace("|proj", ""), "pass", row["pass_E"], row["pass_c"], "min", row["min_E"], row["min_c"],
          "ready", row["ready_E"], row["ready_c"], "T3", row["T3_E"], row["T3_c"], "T4same", row["T4_same"], row["T4_c"],
          "D", None if row["D_hat"] is None else round(row["D_hat"], 1), "dtau", None if row["dtau"] is None else round(row["dtau"], 2),
          row["ev_new"][:2], row["err"] or "")
(TP / f"ps7_{cand}_compare.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
print("T4 same", sum(r["T4_same"] for r in rows), "of", len(rows), "pass", sum(bool(r["pass_c"]) for r in rows), "E pass", sum(bool(r["pass_E"]) for r in rows))
print("max T4 pitch", max(r["T4_c"][1] for r in rows if r["T4_c"]), "max T3", max((r["T3_c"] or 0) for r in rows))
