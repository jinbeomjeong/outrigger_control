"""Tables of the touch_phase batches: per case, gap and candidate, the spread over the phase sweep.

Usage: python -I aggregate.py <batch> [<batch> ...]; prints a table and writes <batch>_table.json.
D [kN], tau [mm], forces [kN], cylinder force (true), times [s]. Spread = max - min over phases.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[3] / "06_analysis" / "02_control" / "touch_phase"


def spread(values) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"min": None, "max": None, "width": None}
    return {"min": round(min(vals), 3), "max": round(max(vals), 3), "width": round(max(vals) - min(vals), 3)}


def table(records: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for rec in records:
        job = rec["job"]
        groups[(job["case"], job["gap"], job["cand"] or "E", job.get("bias_N", 0.0))].append(rec)
    rows = []
    for (case, gap, cand, bias), runs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][3]), kv[0][2])):
        good = [r for r in runs if "error" not in r]
        adj = []
        for r in good:
            eo = r.get("event_output") or {}
            legs = eo.get("adj_min_F_in_W_kN") or {}
            adj.append(min(legs.values()) if legs else None)
        warn = sorted({e[1].split(":")[0] for r in good for e in r["events"] if e[1].startswith(("WARN", "FAULT"))})
        info = sorted({e[1].split(":")[0] for r in good for e in r["events"] if e[1].startswith("INFO_LIFT")})
        row = {"case": case, "gap": gap, "cand": cand, "bias_N": bias, "n": len(runs), "errors": len(runs) - len(good),
               "tau_te": spread([r.get("tau_te") for r in good]), "D_te": spread([r.get("D_te") for r in good]),
               "tau_lift": spread([r.get("tau_lift") for r in good]),
               "D_lift": spread([r.get("D_lift") for r in good]),
               "F_RL_win": spread([r.get("F_RL_win") for r in good]),
               "F_min8": spread([r.get("F_min8") for r in good]),
               "mean1s_min8": spread([r.get("mean1s_min8") for r in good]),
               "te": spread([r.get("t_touch_end") for r in good]),
               "t_lift": spread([r.get("t_lift") for r in good]),
               "t_ready": spread([r["times"].get("t_first_ready_s") for r in good]),
               "pressure_max_bar": spread([_pressure(r) for r in good]),
               "stroke_max_mm": spread([max(r["stroke_max_mm"]) for r in good]),
               "phases": sorted({r["final_phase"] for r in good}),
               "failed_rows": sorted({str(x) for r in good for x in (r.get("failed_rows") or [])}),
               "warnings": warn, "info": info, "adj_min_W": spread(adj),
               "trim_time": spread([r.get("trim", {}).get("trim_time_s") for r in good]),
               "delta_tau": spread([r.get("trim", {}).get("delta_tau_mm") for r in good])}
        rows.append(row)
    return rows


def _pressure(rec: dict):
    pressure = rec.get("pressure") or {}
    for key in ("max_head_bar", "head_max_bar", "max_bar"):
        if key in pressure:
            value = pressure[key]
            return max(value) if isinstance(value, list) else value
    return None


def fmt(cell: dict, digits: int = 2) -> str:
    if cell["min"] is None:
        return "-"
    return f"{cell['min']:.{digits}f}..{cell['max']:.{digits}f}({cell['width']:.{digits}f})"


def main() -> None:
    for batch in sys.argv[1:]:
        records = [json.loads(line) for line in (OUT / f"{batch}.jsonl").read_text(encoding="utf-8").splitlines()]
        rows = table(records)
        (OUT / f"{batch}_table.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"== {batch}: {len(records)} runs")
        for r in rows:
            bias = f" b{r['bias_N']:+.0f}" if r["bias_N"] else ""
            print(f"{r['case']:4s} {r['gap']:7s} {r['cand']:5s}{bias} n{r['n']} err{r['errors']} "
                  f"tau_te {fmt(r['tau_te'])} D_te {fmt(r['D_te'], 1)} D_lift {fmt(r['D_lift'], 1)} "
                  f"Fmin8 {fmt(r['F_min8'], 1)} mean1s {fmt(r['mean1s_min8'], 1)} te {fmt(r['te'], 1)} "
                  f"ready {fmt(r['t_ready'], 1)} adjW {fmt(r['adj_min_W'], 1)} trim_t {fmt(r['trim_time'], 1)} "
                  f"{r['phases']} fail{r['failed_rows']} {r['warnings']} {r['info']}")


if __name__ == "__main__":
    main()
