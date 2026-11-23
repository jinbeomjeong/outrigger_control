"""Read-only inspection of the 12b VBK0 A/A stop (run 606f8713, step 12b_vbk0_base_a1).

Reads the VBK0 b1/b2 result files and T4h folders only (no VBK output exists or is opened).
Writes ``aa_inspect.json`` next to this script (or to argv[1]) with:
  - the A/A recount (spec 6.3.8 rule, same as jp3_12b_judge.aa_floor),
  - the per-pair READY difference distribution over all 167 pairs,
  - for every counted pair: both lines' READY, final phase, pass, rod_fault record,
    the FAULT/WARN event names of the T4h meta_json, and the phase sequence summary,
  - the 6.3.2 VBK0 categories per block (as in classify_line) for context,
  - a near-threshold count (pairs with |dREADY| in (20, 30] s).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\606f8713\12b_vbk0_base_a1")
SEL = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9"
           r"\ed5_inputs\x11\selection.json")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("aa_inspect.json")


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def ready(row: dict):
    b = row["base"]
    return b.get("t_ready_s", b.get("t_ready"))


def load(block: str):
    doc = json.loads((RUN / f"VBK0_{block}.json").read_text(encoding="utf-8"))
    rows = doc["results"] if isinstance(doc, dict) else doc
    return {case_of(r["key"]): r for r in rows}, doc


def injected(rec: dict) -> bool:
    a = rec.get("applied_periods")
    return bool(rec.get("is_armed")) and isinstance(a, int) and a > 0 and \
        rec.get("first_applied_t_s") is not None


def classify(row: dict) -> str:
    rec = row["rod_fault"]
    if not injected(rec):
        return "no_trigger"
    if rec.get("pre_trigger_fallback"):
        return "pre_trigger_fallback"
    if not bool((rec.get("latched") or {}).get("is_same_read_d1")):
        return "unlatched"
    if ready(row) is None:
        return "vbk0_ready_unreached"
    return "opportunity"


def t4h_summary(block: str, row: dict) -> dict:
    path = RUN / f"VBK0_{block}_t4h" / row["t4h_file"]
    with np.load(path, allow_pickle=False) as d:
        meta = json.loads(str(d["meta_json"]))
        phase = np.asarray(d["phase"]).astype(str)
        applied = np.asarray(d["rod_fault_applied"]) if "rod_fault_applied" in d.files else None
        names = list(d.files)
    # phase run-length (update index, phase)
    runs = []
    for i, p in enumerate(phase):
        if not runs or runs[-1][1] != p:
            runs.append([i, p, 1])
        else:
            runs[-1][2] += 1
    events = meta.get("events") or []
    ev_names = Counter(str(e).split(":", 1)[0] for e in events)
    fault_events = [str(e) for e in events if str(e).startswith("FAULT")]
    first_applied = None
    if applied is not None:
        idx = np.flatnonzero(np.asarray(applied).astype(bool).any(axis=-1)
                             if np.asarray(applied).ndim > 1 else np.asarray(applied).astype(bool))
        first_applied = int(idx[0]) if idx.size else None
    return {"t4h_file": row["t4h_file"], "arrays": names, "n_updates": int(phase.size),
            "phase_runs": [(int(a), str(b), int(c)) for a, b, c in runs][:60],
            "n_phase_runs": len(runs),
            "event_name_counts": dict(ev_names), "fault_events": fault_events[:40],
            "first_applied_update": first_applied}


def brief(row: dict) -> dict:
    b = row.get("base") or {}
    rec = row.get("rod_fault") or {}
    keep_base = {k: b.get(k) for k in ("t_ready_s", "t_ready", "pass", "final_phase",
                                       "t_end_s", "fault", "fault_reason", "end_reason",
                                       "stopped_reason") if k in b}
    return {"key": row["key"], "t_ready": ready(row), "base": keep_base,
            "base_keys": sorted(b.keys()),
            "rod_fault": {k: rec.get(k) for k in rec if k not in ("pre_trigger_commands",)},
            "commands_sha256": row.get("commands_sha256"),
            "events_head": (row.get("events") or [])[:30],
            "warn_fault": row.get("warn_fault"),
            "category": classify(row)}


def main() -> None:
    sel = json.loads(SEL.read_text(encoding="utf-8"))
    cases = [r["case"] for r in sel["cell_table"]]
    cell = {r["case"]: r for r in sel["cell_table"]}
    b1, doc1 = load("b1")
    b2, doc2 = load("b2")
    counted, diffs = [], []
    for c in cases:
        r1, r2 = ready(b1[c]), ready(b2[c])
        if (r1 is None) != (r2 is None):
            counted.append((c, "one_side_no_ready", r1, r2))
        elif r1 is not None:
            d = round(abs(r1 - r2), 6)
            diffs.append((c, d, r1, r2))
            if d > 30.0:
                counted.append((c, "dready_gt_30", r1, r2))
    both_none = [c for c in cases if ready(b1[c]) is None and ready(b2[c]) is None]
    darr = np.array([d for _, d, _, _ in diffs])
    out = {
        "run": str(RUN),
        "aa_recount": {"pairs": len(cases), "counted": len(counted),
                       "items": [{"case": c, "why": w, "t_ready_b1": a, "t_ready_b2": b,
                                  "cell": cell[c]} for c, w, a, b in counted]},
        "both_no_ready": both_none,
        "dready_quantiles_s": {q: float(np.quantile(darr, q)) for q in
                               (0.5, 0.9, 0.95, 0.99, 1.0)} if darr.size else {},
        "dready_bins": {">1": int((darr > 1).sum()), ">5": int((darr > 5).sum()),
                        ">10": int((darr > 10).sum()), ">20": int((darr > 20).sum()),
                        ">30": int((darr > 30).sum())},
        "top10_dready": sorted(diffs, key=lambda x: -x[1])[:10],
        "no_ready_b1": [c for c in cases if ready(b1[c]) is None],
        "no_ready_b2": [c for c in cases if ready(b2[c]) is None],
        "categories": {blk: dict(Counter(classify(rows[c]) for c in cases))
                       for blk, rows in (("b1", b1), ("b2", b2))},
        "doc_meta": {blk: {k: v for k, v in d.items() if k != "results"}
                     if isinstance(d, dict) else None for blk, d in (("b1", doc1), ("b2", doc2))},
        "detail": {},
    }
    # category cross table for the counted ones and for all
    out["category_pair_table"] = dict(Counter(
        f"{classify(b1[c])}|{classify(b2[c])}" for c in cases))
    for c, *_ in counted:
        out["detail"][c] = {"b1": brief(b1[c]), "b2": brief(b2[c]),
                            "b1_t4h": t4h_summary("b1", b1[c]),
                            "b2_t4h": t4h_summary("b2", b2[c])}
    # same-case final phase / ready none rows
    OUT.write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"counted": len(counted), "out": str(OUT)}))


if __name__ == "__main__":
    main()
