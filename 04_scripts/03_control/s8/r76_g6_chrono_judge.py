"""Spec rev. 75 draft: judgement of the G6 Chrono (S9 SCM, soil patch under one pad) runs.

Per case (result.json p3b / p3b_ext of run_S9.py):
  G6-1 = P3-1 (crawler zero READY..+10 s, no re-contact; U-S9-G6d (a): a re-contact recorded in
  p3b.P3-1_crawler.recontact_events (or result_rejudge_U-S9-G6d.json) with pass = true is a FLAG), G6-2 = P3-2 within (LOC before first DONE, not loaded,
  LOC - departure <= limit), G6-3 = P3-3 within (true F_cyl >= F_min after the departure), G6-4 = P3-4 within_0p2,
  G6-5 = P3-5 (rut clearance from the first READY >= 25 mm, stroke <= 684.8 mm), G6-6 = no FAULT and READY reached,
  G6-7 = P3-8 (no re-approach / P5 / probe abort before the LOC) with the decision-2 / U-S9-G6c FLAG rules
  (pre-LOC re-approach: started leg true minimum >= F_min -> P3-8_demoted; < F_min with G6-3 passed and no FAULT ->
  P3-8_preloc_loss), READY <= 120 s after the loop start (P-S8-29 acceptance), P3-6 / P3-7 / P3-9 recorded.
Records: P-S8-28/29/30 event counts, LOC - departure, completion blocking shares, virgin-branch flag, pad sinkage,
settle reference (must equal the P3b reference of the same base: dynamics), and an optional comparison with a
reference run (P3b case): commands (10 Hz issued u) max difference, 1 ms truth max differences (F_cyl, attitude,
z_origin, crawler normal) over the common time, phase times.

Usage: python -I r76_g6_chrono_judge.py <out_json> <case dir> [<case dir> ...] [--ref <case>=<ref dir> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

READY_MAX_S = 120.0


def load(d):
    return json.loads((Path(d) / "result.json").read_text(encoding="utf-8"))


def judge(d):
    r = load(d)
    p, x = r["p3b"], r.get("p3b_ext") or {}
    t0 = p["t_loop_start_s"]
    phases = [ph["phase"] for ph in r.get("phases") or []]
    names = [e["name"] for e in r.get("events") or []]
    fault = any(ph in ("fault", "fault_reground") for ph in phases) or any(n.startswith("FAULT") for n in names)
    ready = p["P3-6_ready"]["t_ready_after_loop_start_s"]
    p38 = p["P3-8_false_triggers"]
    p31 = p["P3-1_crawler"]
    rce = p31.get("recontact_events")
    rejudge = Path(d) / "result_rejudge_U-S9-G6d.json"
    if rce is None and rejudge.exists():
        rce = json.loads(rejudge.read_text(encoding="utf-8"))["p3b"]["P3-1_crawler"].get("recontact_events")
    flags = []
    if p31["recontact_count"] == 0:
        recontact_ok = True
    elif rce is not None:
        # U-S9-G6d (a), 2026-10-28: transient re-contact (<= 0.5 s, ended before the LOC, <= 0.15 W) -> FLAG
        recontact_ok = bool(rce.get("pass"))
        flags += list(rce.get("flags") or [])
    else:
        recontact_ok = False
    g = {
        "G6-1_crawler": bool(p31["crawler_zero"] and recontact_ok),
        "G6-2_loc": bool(p["P3-2_loc"]["within"]),
        "G6-3_Fmin": bool(p["P3-3_leg_force"]["within"]),
        "G6-4_att": bool(p["P3-4_attitude"]["within_0p2"]),
        "G6-5_rut_stroke": bool(p["P3-5_clearance_stroke"]["rut_clearance_min_after_first_ready_m"] >= 0.025
                                and p["P3-5_clearance_stroke"]["stroke_within"]),
        "G6-6_fault_ready": bool(not fault and ready is not None),
        "G6-7_preloc": bool(p38["within"]),
        "READY_le_120s": bool(ready is not None and ready <= READY_MAX_S),
    }
    if not g["G6-7_preloc"]:
        # decision 2 / U-S9-G6c: needs the started leg's true minimum; the runner record lists the events only
        flags.append("P3-8_needs_leg_minimum")
    res = {
        "case": Path(d).name, "gates": g, "pass": all(g.values()), "flags": flags,
        "recontact_events": rce,
        "t_ready_rel_s": ready, "loc_minus_departure_s": p["P3-2_loc"]["loc_minus_departure_s"],
        "loc_limit_s": p["P3-2_loc"]["limit_s"],
        "F_min_after_departure_kN": [round(v / 1e3, 2) for v in p["P3-3_leg_force"]["F_min_after_N"]],
        "attitude_p34_absmax_deg": p["P3-4_attitude"]["p34_absmax_overall_deg"],
        "end_mean_roll_pitch_deg": p["P3-4_attitude"]["end_mean_roll_pitch_deg"],
        "rut_min_after_ready_mm": round(p["P3-5_clearance_stroke"]["rut_clearance_min_after_first_ready_m"] * 1e3, 2),
        "s_motor_max_mm": [round(v * 1e3, 2) for v in p["P3-5_clearance_stroke"]["s_motor_max_m"]],
        "P3-6": p["P3-6_ready"].get("within"), "P3-7": p.get("P3-7_plateau", {}).get("within"),
        "P3-9_flag": p.get("P3-9_deferred", {}).get("flag"),
        "pre_liftoff_flag": p.get("pre_liftoff_min_F_cyl", {}).get("any_flag"),
        "p38_counts": p38.get("counts"),
        "event_counts": x.get("event_counts"), "pause_times_rel_s": (x.get("event_times_rel_s") or {}).get(
            "INFO_LIFT_PAUSED"),
        "c_min_at_P_mm": None if x.get("c_min_at_P_m") is None else round(x["c_min_at_P_m"] * 1e3, 2),
        "loc_anchor_applied": x.get("loc_anchor_applied"),
        "completion": x.get("completion"), "pad_sinkage": x.get("pad_sinkage"),
        "virgin_branch_any": (x.get("virgin_branch") or {}).get("any_in_window"),
        "settle_reference": {k: r["settle_reference"][k] for k in ("roll_pitch_deg", "z_origin_m")},
        "phases_rel_s": [(round(ph["t_s"] - t0, 2), ph["phase"]) for ph in r.get("phases") or []],
        "events": [(round(e["t_s"] - t0, 2), e["name"]) for e in r.get("events") or []
                   if not e["name"].startswith("INFO_PRESSURE_ZERO")],
    }
    return res, r


def compare(d, ref):
    a, b = Path(d), Path(ref)
    ca, cb = np.load(a / "controller_commands.npz"), np.load(b / "controller_commands.npz")
    n = min(len(ca["t_s"]), len(cb["t_s"]))
    du = float(np.max(np.abs(ca["issued_u_m_s"][:n] - cb["issued_u_m_s"][:n])))
    first = np.flatnonzero(np.any(np.abs(ca["issued_u_m_s"][:n] - cb["issued_u_m_s"][:n]) > 1e-12, axis=1))
    sa, sb = np.load(a / "step_series.npz"), np.load(b / "step_series.npz")
    m = min(len(sa["t_s"]), len(sb["t_s"]))
    out = {"ref": b.name, "n_periods": int(n), "commands_max_abs_diff_m_s": du,
           "commands_first_diff_t_s": None if not first.size else float(ca["t_s"][first[0]]),
           "truth_max_abs_diff": {}}
    for k in ("F_cyl_N", "roll_pitch_deg", "z_origin_m", "scm_crawler_normal_N", "s_motor_m"):
        out["truth_max_abs_diff"][k] = float(np.max(np.abs(sa[k][:m] - sb[k][:m])))
    return out


def main():
    out = Path(sys.argv[1])
    cases, refs = [], {}
    it = iter(sys.argv[2:])
    for a in it:
        if a == "--ref":
            k, v = next(it).split("=", 1)
            refs[k] = v
        else:
            cases.append(a)
    res = {"script": "04_scripts/03_control/s8/r76_g6_chrono_judge.py", "cases": []}
    for d in cases:
        j, r = judge(d)
        name = Path(d).name
        if name in refs:
            j["vs_reference"] = compare(d, refs[name])
            rr = load(refs[name])
            j["vs_reference"]["ref_settle_reference"] = {k: rr["settle_reference"][k] for k in ("roll_pitch_deg",
                                                                                              "z_origin_m")}
            j["vs_reference"]["ref_phases"] = [(round(ph["t_s"] - rr["p3b"]["t_loop_start_s"], 2), ph["phase"])
                                               for ph in rr.get("phases") or []]
        res["cases"].append(j)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for j in res["cases"]:
        print(j["case"], "pass", j["pass"], {k: v for k, v in j["gates"].items() if not v}, "READY", j["t_ready_rel_s"],
              "LOC-dep", round(j["loc_minus_departure_s"], 3), "Fmin", j["F_min_after_departure_kN"], "att",
              round(j["attitude_p34_absmax_deg"], 4), "rut", j["rut_min_after_ready_mm"], "events", j["event_counts"])
        print("   settle", j["settle_reference"], "phases", j["phases_rel_s"])
        if "vs_reference" in j:
            v = j["vs_reference"]
            print("   vs", v["ref"], "du_max", v["commands_max_abs_diff_m_s"], "first diff t", v["commands_first_diff_t_s"],
                  "truth", {k: round(x, 6) for k, x in v["truth_max_abs_diff"].items()}, "ref settle",
                  v["ref_settle_reference"])


if __name__ == "__main__":
    main()
