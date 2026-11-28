"""Edition 9 R3 pre-check (control-expert, 2026-11-28; record replay, not a judgement).

Why the harness trace injection of ``control_d1_rule/scripts/d1_rule_eval.py`` gives C-m = C0 in
band k0 (stats ``stats_r3_check/report.md`` 2.3): for every injection row of that script (same
loop, same row filter) this tallies, by band of ``t - t_event``, whether the C-m median reference
exists (three valid earlier periods) and how far the previous residual ``r_{j-1}`` lies from the
median (``|r_{j-1} - med| / thr``). With a valid reference and ``r_{j-1} = med`` C-m equals C0
by construction (the two tests compare the same number). It also writes, per trace, the event
time against the start of D1'' (first period with ``is_crawler_lifted``).

Reads the stage 5 diagnosis traces only (job definitions, trace rows); prints counts only.

Usage (dynamics-dev ``python -I -B``)::

    python harness_k0_check.py <stage5_aa_diag folder> <d1_rule_eval.py folder> <out json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

BANDS = (("k0", 0.0, 0.1), ("k1", 0.1, 0.2), ("k2", 0.2, 0.3), ("late", 0.3, 2.5),
         ("tail", 2.5, math.inf))
TOL = 1e-6


def band_of(dt: float | None) -> str:
    if dt is None:
        return "no_event"
    if dt < -TOL:
        return "before"
    for name, low, high in BANDS:
        if low - TOL <= dt < high - TOL:
            return name
    return "tail"


def main() -> int:
    diag, tool_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    if out.exists():
        print(json.dumps({"status": "input_error", "reason": f"{out} exists"}))
        return 2
    sys.path.insert(0, str(tool_dir))
    import d1_rule_eval as ev

    tallies: dict = {}
    traces_info = []
    for set_name, sub, jsonl, trace_dir in ev.SETS:
        base = diag / sub
        for record in ev.read_jsonl(base / jsonl):
            trace = json.loads((base / trace_dir / f"trace_{record['label']}.json")
                               .read_text(encoding="utf-8"))
            meta, rows = ev.primary(trace)
            area = meta["head_area_m2"]
            max_step = meta["settings"]["max_step_Pa"]
            t_event = record.get("t_event_s")
            lifted_t = next((r["t_s"] for r in rows if r.get("is_crawler_lifted")), None)
            traces_info.append({"set": set_name, "label": record["label"], "t_event_s": t_event,
                                "first_d1pp_lifted_t_s": lifted_t,
                                "event_minus_d1pp_start_s": None if (t_event is None or lifted_t
                                                                     is None)
                                else round(t_event - lifted_t, 3)})
            first_fault = next((i for i, r in enumerate(rows) if r.get("head_fault_reasons")),
                               None)
            end = len(rows) if first_fault is None else first_fault
            for j in range(2, end):
                row = rows[j]
                if not ev.ready(row) or not ev.valid_ref(rows[j - 1]):
                    continue
                dp = row.get("dp_head_Pa")
                if dp is None:
                    continue
                mass = row["mass_kg"]
                r_j, r_1 = ev.residual(row, mass), ev.residual(rows[j - 1], mass)
                r_med = ev.median_ref(rows, j, mass)
                max_dp_bar = max(abs(v) for v in dp) / ev.BAR
                kind = "quiet" if max_dp_bar <= ev.QUIET_DP_BAR else "transient"
                band = band_of(None if t_event is None else row["t_s"] - t_event)
                for i in range(4):
                    for jump_bar in ev.JUMPS_BAR:
                        jump = jump_bar * ev.BAR
                        step = dp[i] + jump
                        if abs(step) <= max_step:
                            continue
                        thr = ev.RATIO * abs(step) * area[i]
                        add = jump * area[i]
                        c0 = abs(r_j + add - r_1) >= thr
                        cm = c0 and (r_med is None or abs(r_j + add - r_med) >= thr)
                        key = f"{kind}|{band}"
                        cell = tallies.setdefault(key, {
                            "candidates": 0, "median_missing": 0, "median_valid": 0,
                            "prev_equals_median": 0, "c0": 0, "cm": 0, "c0_not_cm": 0,
                            "max_prev_off_median_over_thr": 0.0})
                        cell["candidates"] += 1
                        cell["c0"] += c0
                        cell["cm"] += cm
                        cell["c0_not_cm"] += c0 and not cm
                        if r_med is None:
                            cell["median_missing"] += 1
                        else:
                            cell["median_valid"] += 1
                            off = abs(r_1 - r_med) / thr
                            cell["prev_equals_median"] += off == 0.0
                            cell["max_prev_off_median_over_thr"] = max(
                                cell["max_prev_off_median_over_thr"], round(off, 4))
    event_lags = [t["event_minus_d1pp_start_s"] for t in traces_info
                  if t["event_minus_d1pp_start_s"] is not None]
    report = {"tool": str(tool_dir / "d1_rule_eval.py"), "diag": str(diag),
              "bands_s": {name: [low, high] for name, low, high in BANDS},
              "tallies": dict(sorted(tallies.items())),
              "event_minus_d1pp_start_s": {"n": len(event_lags),
                                           "min": min(event_lags) if event_lags else None,
                                           "max": max(event_lags) if event_lags else None},
              "traces": traces_info}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": "ok", "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
