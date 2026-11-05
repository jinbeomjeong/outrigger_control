"""Judge the M1 harness runs against m1_criteria.md (the criteria were written before any M1 run).

Usage (dynamics-dev): python -I aggregate_m1.py [batch ...]   (default: main)
Output: <out>/m1_judgement.json and a text summary on stdout. Hash check values: hash.jsonl vs the stored runs.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1"
STORED_HASH = ROOT / "06_analysis" / "02_control" / "touch_phase" / "hash.jsonl"
F_MIN_KN = 9.415
READY_LIMIT_S = 100.0
ATT_LIMIT_DEG = 0.2
LOST = "lost"


def load(batches) -> list[dict]:
    records = []
    for batch in batches:
        path = OUT / f"{batch}.jsonl"
        if path.exists():
            records += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return records


def row_id(job: dict) -> str:
    return job["case"] + ("ra" if job.get("decision") else "")


def phase_id(job: dict):
    return job.get("offset_s") if job.get("offset_s") is not None else job["eps"]


def hash_check() -> list[dict]:
    stored = {json.loads(line)["job"]["case"]: json.loads(line) for line in STORED_HASH.read_text(encoding="utf-8").splitlines()}
    table = {}
    for rec in load(["hash"]):
        table.setdefault(rec["job"]["case"], {})[rec["job"]["variant"]] = rec["commands_sha256"]
    return [{"case": case, "stored": stored[case]["commands_sha256"], **values,
             "same": values.get("OFF") == stored[case]["commands_sha256"] == values.get("ZERO")}
            for case, values in sorted(table.items())]


def metrics(rec: dict) -> dict:
    """The values the criteria read, in one flat dict."""
    values = rec["values"]
    times = values["times"]
    forces = values["forces"]
    out = {"t_touch_end": times["t_touch_end_s"], "t_lift": forces.get("t_lift_s"),
           "t_done": times["t_first_done_s"], "t_ready": times["t_first_ready_s"],
           "t_loc_first": values["events"]["t_loc_first_s"], "t_loc_last": values["events"]["t_loc_last_s"],
           "reapp": values["events"]["reapproach_starts_after_liftoff"],
           "probe_aborts": values["events"]["probe_aborts"], "probe_rounds": rec.get("probe_rounds"),
           "p5": values["events"]["p5_relevels_after_liftoff"],
           "guard_s": values["guard_active_s"], "n_rev": rec["command_stats"]["n_rev"],
           "n_starts": sum(rec["command_stats"]["n_starts"]),
           "F_after": (forces.get("after_liftoff") or {}).get("min_kN"),
           "F_first8": (forces.get("first_8s") or {}).get("min_kN"),
           "F_after8": (forces.get("after_8s") or {}).get("min_kN"),
           "att_last5": values["attitude"]["max_abs_last_5s_deg"],
           "D_te": rec.get("D_te"), "D_lift": rec.get("D_lift"), "D_done": values["twist"]["abs_at_first_done_kN"],
           "stroke_max": rec.get("max_stroke_reading_mm"), "phase": rec["final_phase"], "class": rec.get("harness_class"),
           "failed": rec.get("failed_rows") or [],
           "bad_events": sorted(k for k in rec["event_names"] if k.startswith(("FAULT", "WARN"))),
           "info_events": sorted(k for k in rec["event_names"] if k.startswith("INFO")),
           "n_loc_revoked": rec["event_names"].get("INFO_LOC_REVOKED", 0), "sha": rec["commands_sha256"][:10]}
    event = rec.get("event_output")
    if event:
        out.update(pass_=event["pass"], gates=[k for k, v in event["gates"].items() if not v],
                   F_after_W=min(event["min_F_after_W_kN"].values()), F_after_event=min(event["min_F_after_event_kN"].values()),
                   pair_union=event["pair_union_s"], last_touch=event["pair_last_touch_s"], adj_sum=event["adj_lift_sum_W_s"],
                   t_back=event["t_ready_back_s"], att_end=max(abs(v) for v in event["att_end_deg"]),
                   n_late=event["n_late_starts"], ev_sign=event["sign_changes"])
    m1 = rec.get("m1")
    if m1:
        out.update(m1_fills=[sum(v) for v in zip(*m1["n_fills"], strict=True)],
                   m1_hold_s=[round(sum(v), 2) for v in zip(*m1["hold_s"], strict=True)],
                   m1_lost_mm=[round(sum(v), 2) for v in zip(*m1["lost_mm"], strict=True)])
    return out


def judge_pair(off: dict, on: dict, off_max_rev: int, off_all: list[dict]) -> list[dict]:
    """Failures of criteria sec. 3, 4; each with a flag: the same failure on another base phase."""
    fails = []

    def add(item, detail, in_base):
        fails.append({"item": item, "detail": detail, "base_has_it_on_other_phase": bool(in_base)})

    if "pass_" in on:  # event row
        for gate in on["gates"]:
            if gate not in off["gates"]:
                add("J1", f"gate {gate}", any(gate in o["gates"] for o in off_all))
        if off["F_after_W"] >= F_MIN_KN > on["F_after_W"]:
            add("J2", f"F_after_W {off['F_after_W']} -> {on['F_after_W']}", any(o["F_after_W"] < F_MIN_KN for o in off_all))
        if off["att_end"] <= ATT_LIMIT_DEG < on["att_end"]:
            add("J4", f"att_end {off['att_end']} -> {on['att_end']}", any(o["att_end"] > ATT_LIMIT_DEG for o in off_all))
    else:
        if off["class"] == "pass" and on["class"] != "pass":
            add("J1", f"class {on['class']}", any(o["class"] != "pass" for o in off_all))
        for row in on["failed"]:
            if row not in off["failed"]:
                add("J1", f"row {row}", any(row in o["failed"] for o in off_all))
        if off["F_after"] is not None and off["F_after"] >= F_MIN_KN and (on["F_after"] is None or on["F_after"] < F_MIN_KN):
            add("J2", f"F_after {off['F_after']} -> {on['F_after']}",
                any((o["F_after"] or 0) < F_MIN_KN for o in off_all))
        if off["att_last5"] is not None and off["att_last5"] <= ATT_LIMIT_DEG and (on["att_last5"] is None or on["att_last5"] > ATT_LIMIT_DEG):
            add("J4", f"att_last5 {off['att_last5']} -> {on['att_last5']}",
                any((o["att_last5"] or 99) > ATT_LIMIT_DEG for o in off_all))
    if off["t_ready"] is not None and (on["t_ready"] is None or on["t_ready"] > READY_LIMIT_S):
        add("J3", f"t_ready {off['t_ready']} -> {on['t_ready']}", any(o["t_ready"] is None or o["t_ready"] > READY_LIMIT_S for o in off_all))
    for name in on["bad_events"]:
        if name not in off["bad_events"]:
            add("J5", name, any(name in o["bad_events"] for o in off_all))
    if on["n_rev"] >= 2 * off_max_rev and on["n_rev"] >= off_max_rev + 6:
        add("J7", f"n_rev {on['n_rev']} vs off max {off_max_rev}", False)
    return fails


EFFECT_KEYS = ("t_touch_end", "t_lift", "t_loc_first", "t_done", "t_ready", "F_after", "F_first8", "F_after8", "F_after_W",
               "F_after_event", "n_rev", "n_starts", "reapp", "guard_s", "D_te", "D_lift", "D_done", "att_last5", "att_end",
               "pair_union", "last_touch", "stroke_max")


def effect_table(off_values: dict, on_values: dict) -> dict:
    """Criteria sec. 5: effect against the base phase scatter, phases paired."""
    table = {}
    phases = [p for p in on_values if p in off_values]
    for key in EFFECT_KEYS:
        pairs = [(off_values[p].get(key), on_values[p].get(key)) for p in phases]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        if not pairs:
            continue
        off_all = [v.get(key) for v in off_values.values() if v.get(key) is not None]
        scatter = max(off_all) - min(off_all)
        effect = statistics.median(b for _, b in pairs) - statistics.median(a for a, _ in pairs)
        deltas = [b - a for a, b in pairs]
        same_sign = all(d > 0 for d in deltas) or all(d < 0 for d in deltas)
        table[key] = {"effect": round(effect, 4), "scatter": round(scatter, 4), "deltas": [round(d, 4) for d in deltas],
                      "separated": bool(abs(effect) > scatter and same_sign), "n": len(pairs)}
    return table


def main() -> None:
    batches = sys.argv[1:] or ["main"]
    records = load(batches)
    errors = [r for r in records if "error" in r]
    by_row: dict = defaultdict(lambda: defaultdict(dict))
    for rec in records:
        if "error" not in rec:
            by_row[row_id(rec["job"])][rec["job"]["variant"]][phase_id(rec["job"])] = metrics(rec)
    report = {"hash": hash_check(), "n_runs": len(records), "n_errors": len(errors),
              "errors": [(e["job"], e["error"][:300]) for e in errors], "rows": {}}
    fail_list = []
    increase_rev = []
    for row, variants in sorted(by_row.items()):
        off = variants.get("OFF", {})
        if not off:
            continue
        off_max_rev = max(v["n_rev"] for v in off.values())
        off_all = list(off.values())
        row_out = {"OFF": off, "variants": {}}
        for variant, values in variants.items():
            if variant == "OFF":
                continue
            effects = effect_table(off, values)
            pair_fails = {}
            for phase, on in values.items():
                if phase not in off:
                    continue
                fails = judge_pair(off[phase], on, off_max_rev, off_all)
                if fails:
                    pair_fails[str(phase)] = fails
                    fail_list += [{"row": row, "variant": variant, "phase": phase, **f} for f in fails]
                if on["n_rev"] > off_max_rev:
                    increase_rev.append({"row": row, "variant": variant, "phase": phase, "n_rev": on["n_rev"],
                                         "off_max": off_max_rev, "off_same_phase": off[phase]["n_rev"]})
            row_out["variants"][variant] = {"values": values, "effects": effects, "fails": pair_fails}
        report["rows"][row] = row_out
    report["fail_list"] = fail_list
    report["rev_increase"] = increase_rev
    (OUT / "m1_judgement.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("runs", len(records), "errors", len(errors))
    print("hash", [(h["case"], h["same"]) for h in report["hash"]])
    print("fails", len(fail_list))
    for fail in fail_list:
        print(" ", fail)
    print("rev increases", len(increase_rev))
    for item in increase_rev:
        print(" ", item)
    keys = ("t_touch_end", "t_lift", "t_loc_first", "t_done", "t_ready", "F_after", "F_after_W", "n_rev", "reapp", "guard_s", "D_done")
    for row, row_out in report["rows"].items():
        for variant, data in row_out["variants"].items():
            line = []
            for key in keys:
                e = data["effects"].get(key)
                if e:
                    line.append(f"{key} {e['effect']:+.2f}/{e['scatter']:.2f}{'*' if e['separated'] else ''}")
            print(f"{row:6s} {variant:4s} " + " ".join(line))


if __name__ == "__main__":
    main()
