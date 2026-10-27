"""Spec rev. 72: judgement table of the G6 screen (r72_g6_screen.py JSON).

Per gate G6-1..7 counts, failed runs, Chrono escalation marks (spec rev. 72 376.3 / report 2.6: min F after the
crawler lift-off - F_min < 10 kN, final attitude > 0.1 deg, rut clearance < 35 mm, stroke > 674.8 mm, READY > 120 s,
LOC anchor fired), LEVEL duration (first LEVEL -> first DONE) by weak soil / leg / level / F_s, pre-LOC events.

Decision 2 (2026-10-27): G6-7 (P3-8) is demoted to a FLAG ("P3-8_demoted") when every pre-LOC started leg kept its
true minimum >= F_min up to LOC + 1 s and the run has no FAULT (records ``preloc_starts`` / ``preloc_flag_ok``; for
records without them pass ``--recheck=<json>`` with re-runs of the same commands, else "P3-8_unchecked").

Usage: python -I r72_judge.py <out_json> <r72 json> [...] [--recheck=<json>]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

F_MIN_KN = 9.4146


def level_time(r):
    pp = r.get("phase_path") or []
    t_l = next((t for t, p in pp if p == "level"), None)
    t_d = next((t for t, p in pp if p == "done"), None)
    return None if t_l is None or t_d is None else round(t_d - t_l, 1)


def marks(r):
    m = []
    mn = r.get("min_true_Fcyl_after_off_kN")
    if mn is not None and mn - F_MIN_KN < 10.0:
        m.append("Fmin_margin<10")
    if max(abs(a) for a in r.get("att_end_deg") or [0]) > 0.1:
        m.append("att>0.1")
    rut = [x for x in (r.get("rut_clear_ready_mm"), r.get("rut_clear_end_mm")) if x is not None]
    if rut and min(rut) < 35.0:
        m.append("rut<35")
    if (r.get("max_motor_stroke_mm") or 0) > 674.8:
        m.append("stroke>674.8")
    if (r.get("t_ready_s") or 1e9) > 120.0:
        m.append("ready>120")
    if r.get("anchor_applied"):
        m.append("anchor")
    return m


def main():
    rows = []
    override = {}
    for p in sys.argv[2:]:
        if p.startswith("--recheck="):
            # re-runs with the pre-LOC record (same commands): fields preloc_starts / preloc_flag_ok
            for r in json.loads(Path(p.split("=", 1)[1]).read_text(encoding="utf-8"))["results"]:
                override[r["key"]] = r
            continue
        rows += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    errors = [r["key"] for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    n_recheck = 0
    for r in rows:
        o = override.get(r["key"])
        if o is None:
            continue
        if o.get("commands_sha256") != r.get("commands_sha256"):
            raise SystemExit(f"command hash differs for {r['key']}")
        r["preloc_starts"], r["preloc_flag_ok"] = o.get("preloc_starts"), o.get("preloc_flag_ok")
        n_recheck += 1
    # decision 2 (2026-10-27): G6-7 (P3-8) is demoted to a FLAG when every pre-LOC started leg kept its true
    # minimum >= F_min up to LOC + 1 s and the run has no FAULT
    # decision U-S9-G6c (2026-10-28, (a)): a pre-LOC load loss of the started leg (true minimum < F_min) is also a
    # FLAG ("P3-8_preloc_loss") when the run passes G6-3 (no lift and >= F_min after the crawler lift-off, strict)
    # and has no FAULT: before the lift-off the crawler still bears load (>= 0.01 W window of the decision; the
    # harness G6-3 window starts at the first crawler-free period, so the loss is judged strictly from there on).
    for r in rows:
        r["flags_p38"] = []
        if not r["gates"].get("G6-7_preloc", True):
            no_fault = r.get("final_phase") not in ("fault", "fault_reground")
            if r.get("preloc_flag_ok") is True:
                r["gates"]["G6-7_preloc"] = True
                r["flags_p38"] = ["P3-8_demoted"]
            elif r.get("preloc_flag_ok") is False and r["gates"].get("G6-3_Fmin") and no_fault:
                r["gates"]["G6-7_preloc"] = True
                r["flags_p38"] = ["P3-8_preloc_loss"]
            elif r.get("preloc_flag_ok") is None:
                r["flags_p38"] = ["P3-8_unchecked"]
    gate_fail = defaultdict(int)
    by_group = defaultdict(lambda: {"n": 0, "pass": 0, "level_s": [], "ready_s": [], "min_F_kN": [], "sink_weak": []})
    table, fails = [], []
    for r in rows:
        bad = [k for k, v in r["gates"].items() if not v]
        for k in bad:
            gate_fail[k] += 1
        w = r["soil"].split("+")[1].split("@")[0] if "+" in r["soil"] else "uniform"
        key = f"{r['base']}|{w}|{r['level']}|Fs{r['fs_kN']:g}" if w != "uniform" else f"ref|{r['soil']}|{r['level']}|Fs{r['fs_kN']:g}"
        g = by_group[key]
        g["n"] += 1
        g["pass"] += int(not bad)
        lt = level_time(r)
        if lt is not None:
            g["level_s"].append(lt)
        if r.get("t_ready_s") is not None:
            g["ready_s"].append(round(r["t_ready_s"], 1))
        if r.get("min_true_Fcyl_after_off_kN") is not None:
            g["min_F_kN"].append(round(r["min_true_Fcyl_after_off_kN"], 2))
        wl = r.get("weak_leg")
        sink = r.get("sink_final_mm")
        if wl and sink:
            g["sink_weak"].append(round(sink["FL FR RL RR".split().index(wl)], 1))
        row = {"key": r["key"], "fails": bad, "marks": marks(r), "level_s": lt,
               "t_ready_s": None if r.get("t_ready_s") is None else round(r["t_ready_s"], 1),
               "min_F_kN": r.get("min_true_Fcyl_after_off_kN"), "att_end_deg": r.get("att_end_deg"),
               "rut_mm": [r.get("rut_clear_ready_mm"), r.get("rut_clear_end_mm")],
               "stroke_max_mm": r.get("max_motor_stroke_mm"), "c_min_tP_mm": r.get("c_min_tP_mm"),
               "anchor": r.get("anchor_applied"), "loc_delay_s": r.get("loc_delay_s"),
               "pre_loc": r.get("pre_loc_events"), "sink_mm": sink, "final_phase": r.get("final_phase"),
               "n_reapproach": r.get("n_reapproach"), "warnings": r.get("warnings"),
               "flags_p38": r.get("flags_p38"), "preloc_starts": r.get("preloc_starts")}
        table.append(row)
        if bad:
            fails.append(row)
    res = {"script": "04_scripts/03_control/s8/r72_judge.py", "inputs": sys.argv[2:], "n": len(rows),
           "n_recheck": n_recheck, "n_p38_demoted": sum(1 for t in table if "P3-8_demoted" in (t["flags_p38"] or [])),
           "n_p38_unchecked": sum(1 for t in table if "P3-8_unchecked" in (t["flags_p38"] or [])),
           "n_p38_preloc_loss": sum(1 for t in table if "P3-8_preloc_loss" in (t["flags_p38"] or [])),
           "errors": errors, "n_pass": sum(1 for t in table if not t["fails"]), "gate_fail": dict(gate_fail),
           "groups": {k: {"n": v["n"], "pass": v["pass"],
                          "level_s": [min(v["level_s"]), max(v["level_s"])] if v["level_s"] else None,
                          "ready_s": [min(v["ready_s"]), max(v["ready_s"])] if v["ready_s"] else None,
                          "min_F_kN": min(v["min_F_kN"]) if v["min_F_kN"] else None,
                          "sink_weak_mm": [min(v["sink_weak"]), max(v["sink_weak"])] if v["sink_weak"] else None}
                      for k, v in sorted(by_group.items())},
           "fails": fails, "marked": [t for t in table if t["marks"]], "anchor_runs": [t["key"] for t in table if t["anchor"]],
           "table": table}
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("n", res["n"], "pass", res["n_pass"], "errors", errors, "gate_fail", res["gate_fail"])
    for k, v in res["groups"].items():
        print(k, v)
    print("anchor runs", res["anchor_runs"])
    for f in fails:
        print("FAIL", f["key"], f["fails"], "ready", f["t_ready_s"], "minF", f["min_F_kN"], "pre", f["pre_loc"],
              "sink", f["sink_mm"], "phase", f["final_phase"])
    from collections import Counter
    print("marks", Counter(m for t in table for m in t["marks"]))


if __name__ == "__main__":
    main()
