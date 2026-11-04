"""Event rows of the re-approach rule batches: spread over phases per case, gap and candidate.

Usage: python -I view_k.py <batch> [...]. Forces kN (true cylinder force), times s after the event.
Writes <batch>_view.json. Event reading rows come from event_output (r67 judge).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

TP = Path(__file__).resolve().parents[3] / "06_analysis" / "02_control" / "touch_phase"
LEGS = ("FL", "FR", "RL", "RR")


def span(values, digits=2):
    vals = [v for v in values if v is not None]
    return "-" if not vals else f"{min(vals):.{digits}f}..{max(vals):.{digits}f}"


def summarize(group: list[dict]) -> dict:
    out = {"n": len(group), "errors": sum("error" in r for r in group)}
    good = [r for r in group if "error" not in r]
    mins = {leg: [r["event_output"]["min_F_after_event_kN"][leg] for r in good] for leg in LEGS}
    out["min"] = {leg: (min(v), max(v)) for leg, v in mins.items() if v}
    out["adj_W"] = [min(r["event_output"]["adj_min_F_in_W_kN"].values()) for r in good]
    out["union"] = [r["event_output"]["pair_union_s"] for r in good]
    out["adj_lift"] = [r["event_output"]["adj_lift_sum_W_s"] for r in good]
    out["leg_lift"] = [max((v["sum_s"] for v in r["event_output"]["lifts"].values()), default=0.0) for r in good]
    out["last_touch"] = [r["event_output"]["pair_last_touch_s"] for r in good]
    out["after_W"] = [min(r["event_output"]["min_F_after_W_kN"].values()) for r in good]
    out["ready"] = [r["times"]["t_first_ready_s"] for r in good]
    out["phases"] = sorted({r["final_phase"] for r in good})
    ends, counts, first = Counter(), [], []
    for r in good:
        starts = [e for e in r["events"] if e[1].startswith("leg_reapproach_start")]
        counts.append(len(starts))
        ends[starts[-1][1].split(":")[1] if starts else "none"] += 1
        event_s = r["event_output"].get("t_event_s")
        if starts:
            first.append(starts[0][0])
    out["ends"] = dict(ends)
    out["n_starts"] = counts
    out["held"] = [r["trim"].get("n_retrigger_held", 0) for r in good]
    out["warn"] = sorted({e[1].split(":")[0] for r in good for e in r["events"] if e[1].startswith(("WARN", "FAULT")) and "D1_IMU" not in e[1] and "ROD_PRESSURE" not in e[1]})
    return out


def main() -> None:
    for batch in sys.argv[1:]:
        groups = defaultdict(list)
        for line in (TP / f"{batch}.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            job = rec["job"]
            sweep = "offs" if job.get("offset_s") is not None else "eps"
            groups[(job["case"], job["gap"], sweep, job["cand"] or "E")].append(rec)
        print("==", batch)
        table = {}
        for key in sorted(groups):
            s = summarize(groups[key])
            table["|".join(key)] = s
            m = s["min"]
            print(" ".join(key), f"n{s['n']} err{s['errors']}",
                  "RL", span(m.get("RL", ())), "RR", span(m.get("RR", ())), "FL", span(m.get("FL", ())), "FR", span(m.get("FR", ())),
                  "adjW", span(s["adj_W"]), "afterW", span(s["after_W"]), "legLift", span(s["leg_lift"]), "lastTouch", span(s["last_touch"]),
                  "adjLift", span(s["adj_lift"], 3), "ready", span(s["ready"], 1),
                  "ends", s["ends"], "starts", span(s["n_starts"], 0), "held", span(s["held"], 0), s["phases"], s["warn"])
        (TP / f"{batch}_view.json").write_text(json.dumps(table, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
