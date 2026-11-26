"""P8-9 selection (spec v8 draft rev 1, 12) on raw/runs.jsonl of p89_rerun.py main.

Rule (fixed before the run, applied as written):
  a candidate (H3, H1) is eligible when
  (1) the five U keys (bottom FR-Fs0 / FL-Fs4 / FL-Fs2 / FR-Fs2 / FR-Fs4 RE1bF ready o0.0) all pass
      U832 (every ``event_output.gates`` key starting with ``U832`` true),
  (2) the FS24 key (bottom-FR-Fs8-FS24-ready o0.0) passes (``event_output.pass`` true),
  (3) on the phase and regression keys (14) there is no gate failing that did not fail on the A
      arm, no new J7 item against the A arm, and no READY not reached where the A arm reached it.
  Both eligible: fewer of the 20 keys with ``commands_sha256`` different from A; tie -> H-3.
  Neither eligible: reported (the user decides).

Outputs (this folder): p89_metrics.csv, p89_selection.json, p89_analyze_out.txt.
Usage: conda run -n dynamics-dev python -I -B p89_analyze.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p89_rerun", HERE / "p89_rerun.py")
p89 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p89)

ED8 = HERE.parents[1]
STORED = {  # stored A-arm lines of the earlier dynamics reruns (same options, same commit)
    "U8-A": ED8 / "dynamics_u832_o00" / "rerun_raw" / "runs.jsonl",
    "D8": ED8 / "dynamics_d1_d3" / "rerun_raw" / "runs.jsonl",
}
EVENT_CAP = 200
FALLBACK = "WARN_ROD_PRESSURE_FALLBACK"
REASON = "INFO_ROD_PRESSURE_FAULT_REASON"


def jkey(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in ("mask", "t4h_dir", "setting")},
                      sort_keys=True)


def _is_number(text: str) -> bool:
    try:
        return math.isfinite(float(text))
    except ValueError:
        return False


def name_436(name: str) -> str:
    return ":".join(p for p in name.split(":") if not _is_number(p))


def j7_set(rec: dict) -> tuple[set[str], bool]:
    """J7 items of a line as ``jp3_ed7_rules.j7_items_ed7`` reads them (WARN / FAULT names
    without numeric segments, fallbacks as (name, leg, reason)); flag = event list capped."""
    events = [(float(t), str(n)) for t, n in rec.get("events") or []]
    names = {name_436(n) for _, n in events if n.startswith(("WARN", "FAULT"))
             and not n.startswith(FALLBACK)}
    reasons = {}
    for _, n in events:
        parts = n.split(":")
        if parts[0] == REASON and len(parts) >= 3:
            reasons.setdefault(parts[1], ":".join(parts[2:]))
    for _, n in events:
        parts = n.split(":")
        if parts[0] == FALLBACK and len(parts) >= 2:
            names.add(f"{FALLBACK}:{parts[1]} reason {reasons.get(parts[1], 'unknown')}")
    return names, len(events) >= EVENT_CAP


def ready_reached(rec: dict) -> bool:
    if rec.get("t_event_s") is not None:
        v = (rec.get("event_output") or {}).get("t_ready_back_s")
        return v is not None and math.isfinite(float(v))
    v = ((rec.get("values") or {}).get("times") or {}).get("t_first_ready_s")
    return v is not None


def log_of(raw: Path, rec: dict) -> dict:
    return json.loads((raw / "logs" / f"{rec['p89']['stem']}_p89.json").read_text("utf-8"))


def main() -> int:
    raw = HERE / "raw"
    recs = [json.loads(x) for x in (raw / "runs.jsonl").read_text("utf-8").splitlines()]
    by = {}
    for r in recs:
        arm = r["job"]["setting"].split("-")[1]
        by[(jkey(r["job"]), arm)] = r
    lines, notes = [], []
    table = {}
    for group, label, key in p89.KEYS:
        for arm in p89.SELECTION_ARMS:
            job = p89.job_of(key, arm)
            r = by.get((jkey(job), arm))
            if r is None or "error" in r:
                notes.append(f"missing or error: {label} {arm} "
                             f"{None if r is None else r.get('error')}")
                table[(label, arm)] = None
                continue
            if r["p89"]["patched_arm"] != arm or r["p89"]["arm"] != arm:
                notes.append(f"identity mismatch {label} {arm}: {r['p89']}")
            eo = r.get("event_output") or {}
            t_ev = r.get("t_event_s")
            log = log_of(raw, r)
            t0 = t_ev if t_ev is not None else -math.inf
            rel = (lambda t, t_ev=t_ev: round(t - t_ev, 3) if t_ev is not None else round(t, 3))
            starts = [(rel(s["t"]), s["leg"]) for s in log["starts"] if s["t"] >= t0 - 1e-9]
            ends = [(rel(e["t"]), e["leg"], e["outcome"]) for e in log["ends"]
                    if e["t"] >= t0 - 1e-9]
            j7, capped = j7_set(r)
            gates = eo.get("gates") or {}
            mins = eo.get("min_F_after_event_kN") or {}
            row = {
                "group": group, "key": label, "arm": arm, "setting": r["job"]["setting"],
                "commands_sha256": r["commands_sha256"],
                "final_phase": r.get("final_phase"),
                "t_event_s": t_ev,
                "gates_failed": sorted(g for g, ok in gates.items() if not ok),
                "gates": gates,
                "pass": eo.get("pass"),
                "pair_union_s": eo.get("pair_union_s"),
                "pair_last_touch_s": eo.get("pair_last_touch_s"),
                "t_ready_back_s": eo.get("t_ready_back_s"),
                "t_first_ready_s": ((r.get("values") or {}).get("times") or {}).get(
                    "t_first_ready_s"),
                "ready_reached": ready_reached(r),
                "reapproach_starts_rel": starts,
                "reapproach_ends_rel": ends,
                "eo_reapproach_starts": eo.get("reapproach_starts"),
                "j7_items": sorted(j7), "events_capped": capped,
                "min_F_after_event_kN": min(mins.values()) if mins else None,
                "min_F_after_event_by_leg_kN": mins,
                "min_F_after_W_kN": eo.get("min_F_after_W_kN"),
                "lifts": eo.get("lifts"),
                "n_h3_extend": len(log["h3"]),
                "h3_extend_rel": [(rel(h["t"]), h["leg"]) for h in log["h3"]],
                "n_h1_defer": len(log["h1_defer"]),
                "h1_defer_rel": [(rel(h["t"]), h["leg"]) for h in log["h1_defer"]],
                "n_h1_b3_block": len(log["h1_b3_block"]),
                "wall_s": r.get("wall_s"),
            }
            table[(label, arm)] = row
            lines.append(row)

    # A-arm reproduction against stored A lines
    stored = []
    for name, path in STORED.items():
        for x in path.read_text("utf-8").splitlines():
            s = json.loads(x)
            if s["job"]["setting"] == "U8-A" or s["job"]["setting"].endswith("-A"):
                plant = {"U8-A": "VBM", "D8-M-A": "VBM", "D8-LSM4-A": "LSM4",
                         "D8-Mslow-A": "VBMslow"}.get(s["job"]["setting"])
                if plant is None:
                    continue
                stored.append((plant, jkey(s["job"]), s["commands_sha256"], name))
    repro = []
    for group, label, key in p89.KEYS:
        row = table.get((label, "A"))
        k = jkey(p89.job_of(key, "A"))
        for plant, sk, sha, name in stored:
            if plant == key["plant"] and sk == k and row is not None:
                repro.append({"key": label, "source": name, "stored": sha[:12],
                              "now": row["commands_sha256"][:12],
                              "equal": sha == row["commands_sha256"]})

    # selection
    sel = {}
    for cand in ("H3", "H1"):
        c1 = {}
        for group, label, _ in p89.KEYS:
            if group != "U":
                continue
            row = table.get((label, cand))
            c1[label] = None if row is None else all(
                ok for g, ok in row["gates"].items() if g.startswith("U832")) and any(
                g.startswith("U832") for g in row["gates"])
        fs = table.get(("bottom-FR-Fs8-FS24-ready-o0.0", cand))
        c2 = None if fs is None else bool(fs["pass"])
        c3 = {}
        for group, label, _ in p89.KEYS:
            if group not in ("phase", "regression"):
                continue
            a, c = table.get((label, "A")), table.get((label, cand))
            if a is None or c is None:
                c3[label] = {"not_judgeable": True}
                continue
            new_gates = sorted(g for g, ok in c["gates"].items()
                               if not ok and a["gates"].get(g, True))
            new_j7 = sorted(set(c["j7_items"]) - set(a["j7_items"]))
            ready_lost = a["ready_reached"] and not c["ready_reached"]
            c3[label] = {"new_failed_gates": new_gates, "new_j7": new_j7,
                         "ready_lost": ready_lost,
                         "capped": a["events_capped"] or c["events_capped"]}
        n_diff = sum(1 for _, label, _ in p89.KEYS
                     if table.get((label, cand)) and table.get((label, "A"))
                     and table[(label, cand)]["commands_sha256"]
                     != table[(label, "A")]["commands_sha256"])
        ok1 = all(v is True for v in c1.values()) and len(c1) == 5
        ok2 = c2 is True
        ok3 = all(not v.get("not_judgeable") and not v["new_failed_gates"] and not v["new_j7"]
                  and not v["ready_lost"] and not v["capped"] for v in c3.values())
        sel[cand] = {"cond1_U832_by_key": c1, "cond1": ok1, "cond2_FS24_pass": c2, "cond2": ok2,
                     "cond3_by_key": c3, "cond3": ok3, "eligible": ok1 and ok2 and ok3,
                     "n_keys_commands_differ_from_A": n_diff}
    if sel["H3"]["eligible"] and sel["H1"]["eligible"]:
        d3, d1 = sel["H3"]["n_keys_commands_differ_from_A"], sel["H1"]["n_keys_commands_differ_from_A"]
        choice = "H1" if d1 < d3 else "H3"
    elif sel["H3"]["eligible"]:
        choice = "H3"
    elif sel["H1"]["eligible"]:
        choice = "H1"
    else:
        choice = None
    result = {"rule": "spec v8 draft rev 1 12 P8-9 (applied as written)", "selection": sel,
              "choice": choice, "A_reproduction": repro, "notes": notes,
              "n_lines": len(lines)}
    (HERE / "p89_selection.json").write_text(json.dumps(result, indent=1, default=str), "utf-8")

    cols = ["group", "key", "arm", "setting", "commands_sha256", "final_phase", "t_event_s",
            "gates_failed", "pass", "pair_union_s", "pair_last_touch_s", "t_ready_back_s",
            "t_first_ready_s", "ready_reached", "reapproach_starts_rel", "reapproach_ends_rel",
            "j7_items", "events_capped", "min_F_after_event_kN", "min_F_after_event_by_leg_kN",
            "lifts", "n_h3_extend", "h3_extend_rel", "n_h1_defer", "h1_defer_rel",
            "n_h1_b3_block", "wall_s"]
    with (HERE / "p89_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in lines:
            w.writerow([json.dumps(row[c], default=str) if isinstance(row[c], (list, dict))
                        else row[c] for c in cols])

    out = [f"lines {len(lines)}  notes {notes}", "A reproduction:"]
    out += [f"  {x}" for x in repro]
    for cand in ("H3", "H1"):
        s = sel[cand]
        out.append(f"{cand}: eligible {s['eligible']} cond1 {s['cond1']} cond2 {s['cond2']} "
                   f"cond3 {s['cond3']} n_diff {s['n_keys_commands_differ_from_A']}")
        out.append(f"  cond1 {s['cond1_U832_by_key']}")
        for k, v in s["cond3_by_key"].items():
            if v.get("not_judgeable") or v["new_failed_gates"] or v["new_j7"] or v["ready_lost"] \
                    or v["capped"]:
                out.append(f"  cond3 FAIL {k}: {v}")
    out.append(f"choice {choice}")
    out.append("")
    for row in lines:
        out.append(
            f"{row['group']:10s} {row['key']:34s} {row['arm']:3s} {row['commands_sha256'][:8]} "
            f"ph={row['final_phase']} fail={row['gates_failed']} PU={row['pair_union_s']} "
            f"LT={row['pair_last_touch_s']} tRb={row['t_ready_back_s']} "
            f"tR1={row['t_first_ready_s']} Fmin={row['min_F_after_event_kN']} "
            f"st={row['reapproach_starts_rel']} en={row['reapproach_ends_rel']} "
            f"h3={row['h3_extend_rel']} h1={row['h1_defer_rel']} b3blk={row['n_h1_b3_block']} "
            f"j7={row['j7_items']}")
    text = "\n".join(out)
    (HERE / "p89_analyze_out.txt").write_text(text, "utf-8")
    print(text.encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
