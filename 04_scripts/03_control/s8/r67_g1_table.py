"""Spec rev. 67: tables of the r67_g1_screen.py results (read only).

Run (dynamics-dev): python -I r67_g1_table.py <json> [<json> ...] <out_json>
Merges the P / E halves, then writes: gate pass counts per (timing, event), the worst row per (timing, event, leg)
over level / F_s / offset, every failing run, left-right and front-rear differences of the main metrics at matched
conditions, rod-fallback reasons (harness artifacts), and the PS-7 table.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

LEGS = ("FL", "FR", "RL", "RR")
MIRROR_LR = {"FL": "FR", "RL": "RR"}
MIRROR_FR = {"FL": "RL", "FR": "RR"}


def main():
    paths, out = sys.argv[1:-1], Path(sys.argv[-1])
    res = []
    for p in paths:
        res += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    errors = [r for r in res if "error" in r]
    screen = [r for r in res if r["key"].startswith("screen") and "error" not in r]
    ps7 = [r for r in res if r["key"].startswith("ps7") and "error" not in r]
    rows = []
    for r in screen:
        for j in r["runs"]:
            rows.append({"timing": r["timing"], "level": r["level"], "fs": r["fs_kN"], "leg": r["leg"],
                         "branch_phase": r["branch_phase"], **j})
    # pass counts
    counts = defaultdict(lambda: [0, 0])
    gate_fail = defaultdict(lambda: defaultdict(int))
    for x in rows:
        k = f'{x["timing"]}|{x["event"]}'
        counts[k][1] += 1
        counts[k][0] += int(x["pass"])
        for g, v in x["gates"].items():
            if not v:
                gate_fail[k][g] += 1
    # worst per (timing, event, leg)
    worst = {}
    for x in rows:
        k = f'{x["timing"]}|{x["event"]}|{x["leg"]}'
        w = worst.setdefault(k, {"n": 0, "pass": 0, "pair_union_max_s": 0.0, "last_touch_max_s": 0.0,
                                 "adj_sum_max_s": 0.0, "adj_gap_max_mm": 0.0, "adj_outside_max_s": 0.0,
                                 "minF_after_W_min_kN": 1e9, "minF_after_event_min_kN": 1e9,
                                 "att_end_max_deg": 0.0, "bundles_max": 0, "late_starts_max": 0,
                                 "sign_changes_max": 0, "n_starts_max": 0, "max_att_change_deg": 0.0,
                                 "t_ready_back_max_s": 0.0, "crawler_contact_ms_max": 0, "faults": 0,
                                 "worst_union_case": None, "worst_minF_case": None, "phase_at_event": set()})
        w["n"] += 1
        w["pass"] += int(x["pass"])
        tag = f'{x["level"]} Fs{x["fs"]:.0f} off{x["offset_s"]}'
        if x["pair_union_s"] >= w["pair_union_max_s"]:
            w["pair_union_max_s"], w["worst_union_case"] = x["pair_union_s"], tag
        w["last_touch_max_s"] = max(w["last_touch_max_s"], x["pair_last_touch_s"])
        w["adj_sum_max_s"] = max(w["adj_sum_max_s"], x["adj_lift_sum_W_s"])
        w["adj_gap_max_mm"] = max(w["adj_gap_max_mm"], x["adj_max_gap_W_mm"])
        w["adj_outside_max_s"] = max(w["adj_outside_max_s"], x["adj_lift_outside_W_s"])
        mfw = min(x["min_F_after_W_kN"].values())
        if mfw <= w["minF_after_W_min_kN"]:
            w["minF_after_W_min_kN"], w["worst_minF_case"] = mfw, tag
        w["minF_after_event_min_kN"] = min(w["minF_after_event_min_kN"], min(x["min_F_after_event_kN"].values()))
        w["att_end_max_deg"] = max(w["att_end_max_deg"], max(abs(a) for a in x["att_end_deg"]))
        w["bundles_max"] = max(w["bundles_max"], x["twist"]["n_bundles"])
        w["late_starts_max"] = max(w["late_starts_max"], x["n_late_starts"])
        w["sign_changes_max"] = max(w["sign_changes_max"], x["sign_changes"])
        w["n_starts_max"] = max(w["n_starts_max"], len(x["reapproach_starts"]))
        w["max_att_change_deg"] = max(w["max_att_change_deg"], x["max_att_change_deg"])
        w["t_ready_back_max_s"] = max(w["t_ready_back_max_s"], x["t_ready_back_s"] or 0.0)
        w["crawler_contact_ms_max"] = max(w["crawler_contact_ms_max"], x["crawler_contact_after_event_ms"] or 0)
        w["faults"] += int(x["fault_periods"] > 0)
        w["phase_at_event"].add(x["phase_at_event"])
    for w in worst.values():
        w["phase_at_event"] = sorted(w["phase_at_event"])
    fails = [{k: x[k] for k in ("timing", "event", "leg", "level", "fs", "offset_s", "gates", "pair_union_s",
                                "pair_last_touch_s", "adj_lift_sum_W_s", "adj_max_gap_W_mm", "adj_lift_outside_W_s",
                                "min_F_after_W_kN", "min_F_after_event_kN", "att_end_deg", "final_phase",
                                "reapproach_starts", "twist", "lifts", "warnings", "phase_at_event")}
             for x in rows if not x["pass"]]
    # symmetry: same timing / event / level / fs / offset, mirrored leg
    idx = {(x["timing"], x["event"], x["level"], x["fs"], x["offset_s"], x["leg"]): x for x in rows}
    sym = {"left_right": defaultdict(list), "front_rear": defaultdict(list)}
    metrics = ("pair_union_s", "pair_last_touch_s", "adj_lift_sum_W_s", "max_att_change_deg")
    for name, mp in (("left_right", MIRROR_LR), ("front_rear", MIRROR_FR)):
        for (tm, ev, lv, fs, off, leg), x in idx.items():
            if leg not in mp:
                continue
            y = idx.get((tm, ev, lv, fs, off, mp[leg]))
            if y is None:
                continue
            row = {m: round(x[m] - y[m], 3) for m in metrics}
            row["minF_after_W_kN"] = round(min(x["min_F_after_W_kN"].values()) - min(y["min_F_after_W_kN"].values()), 2)
            sym[name][f"{tm}|{ev}|{leg}-{mp[leg]}"].append(row)
    sym_sum = {}
    for name, d in sym.items():
        for k, lst in d.items():
            keys = lst[0].keys()
            sym_sum[f"{name}|{k}"] = {m: {"mean": round(sum(r[m] for r in lst) / len(lst), 3),
                                          "max_abs": round(max(abs(r[m]) for r in lst), 3)} for m in keys}
    # rod fallback reasons and when (relative to READY back)
    rod = defaultdict(int)
    for x in rows:
        for wn in x["warnings"]:
            if wn.startswith("INFO_ROD_PRESSURE_FAULT_REASON"):
                rod[f'{x["timing"]}|{wn.split(":")[-1]}'] += 1
    ps7_rows = []
    for r in sorted(ps7, key=lambda r: r["key"]):
        t = r.get("touch", {})
        ps7_rows.append({"key": r["key"], "pass": r.get("pass"), "gates": r.get("gates"),
                         "touch_s": t.get("duration_s"), "latch_s": t.get("latch_s"),
                         "stroke_end_touch_mm": t.get("stroke_at_end_mm"), "max_abs_att_touch_deg": t.get("max_abs_att_deg"),
                         "min_crawler_touch_kN": t.get("min_crawler_kN"), "max_contact_touch_kN": t.get("max_contact_kN"),
                         "t_ready": r.get("t_ready"), "min_F_after_liftoff_kN": r.get("min_F_after_liftoff_kN"),
                         "att_end_deg": r.get("att_end_deg"), "pre_contact_N": r["info"].get("pre_contact_N"),
                         "warn": sorted({n for _, n in r["events"] if n.startswith(("WARN", "FAULT", "INFO_ROD_PRESSURE_FAULT"))}),
                         "cap_used": r.get("cap_used_legs"), "cmd_sha256": r.get("cmd_sha256")})
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r67_g1_table.py", "inputs": paths,
                                        "n_runs": len(rows), "n_errors": len(errors)},
                               "errors": [{"key": e["key"], "error": e["error"]} for e in errors],
                               "pass_counts": {k: {"pass": v[0], "n": v[1]} for k, v in sorted(counts.items())},
                               "gate_failures": {k: dict(v) for k, v in gate_fail.items()},
                               "worst": dict(sorted(worst.items())), "fails": fails, "symmetry": sym_sum,
                               "rod_fallback_reasons": dict(rod), "ps7": ps7_rows}, indent=1, default=float),
                   encoding="utf-8")
    print("runs", len(rows), "errors", len(errors), "fails", len(fails))
    for k, v in sorted(counts.items()):
        print(k, v, dict(gate_fail[k]))


if __name__ == "__main__":
    main()
