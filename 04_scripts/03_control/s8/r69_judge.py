"""Spec rev. 69: judgement tables of the G8 / G5 reduced screens (post-processing of the r69_g8_screen.py /
r69_g5_screen.py JSON; no simulation).

G8 flat: margins per (level, F_s) and per gap (D8 minimum, max stroke at READY, T-3', T-4 change, latch after
  contact, TOUCH length minus ref, over-lift minus ref vs the plane-fit model 3h/4 / d/4).
G8 slope: matrix floor x leg x gap with outcome class
  PASS / STROKE_MARGIN (READY, a leg past 0.6848 m) / NOT_READY (no READY, no FAULT) / FAULT, the leg at the
  stroke end, D8 minimum and lifted legs, final attitude, notable events, over-lift.
G5: rev. 69 F_s 2 / 4 runs re-judged (350.1 per-leg cumulative), failed runs with the 350.3 contact / lift split,
  adjacent-leg lift outside W, late starts, U-S8-75 (b) exception check (front, top, fast; the exception applies
  only to F_s < 2 kN, so it is evaluated as "would pass if in scope").

Crawler clearance: the batch JSON holds the first r69 definition (settle-contact nodes); slope rows are replaced
from ``r69_slope_clearance_v2.json`` (same commands, all-node floor gap) when present.

Usage: python -I r69_judge.py <rev69 dir> <out_json>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

STROKE_OK_MM = 684.8
F_MIN_KN = 9.4146
LEGS = ("FL", "FR", "RL", "RR")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))["results"]


def h_of(r):
    _, _, _, _, leg, kind, val = r["key"].split("|")
    if kind == "raised":
        return round(r["info"]["g0_mm"][LEGS.index(leg)] - r["info"]["g_start_mm"], 1)
    return -float(val)


def outcome(r):
    if r["pass"]:
        return "PASS"
    if r.get("final_phase") in ("fault", "fault_reground"):
        return "FAULT"
    if not r["gates"]["ready"]:
        return "NOT_READY"
    bad = [k for k, v in r["gates"].items() if not v]
    if bad == ["stroke_end"]:
        return "STROKE_MARGIN"
    return "FAIL:" + ",".join(bad) if bad else "FLAG:" + ",".join(r["flags"])


def g8(rows):
    ref = {(r["floor"], r["level"], r["fs_kN"]): r for r in rows if r["leg"] == "ref"}
    flat = defaultdict(lambda: defaultdict(list))
    slope = []
    model = defaultdict(list)
    for r in rows:
        if r["leg"] == "ref":
            continue
        rf = ref[(r["floor"], r["level"], r["fs_kN"])]
        tch = r.get("touch") or {}
        h = h_of(r)
        over = r["crawler_clearance_end_mm"]["true_minus_estimate"] - rf["crawler_clearance_end_mm"]["true_minus_estimate"]
        m = 0.75 * h if h > 0 else -0.25 * h
        kind = "raised" if h > 0 else "lowered"
        if r["floor"] == "flat" and abs(m) > 5:
            model[f"{kind}|{r['leg']}|{r['level']}"].append(round(over / m, 3))
        d8 = min(r["min_F_after_liftoff_kN"].values()) if r.get("min_F_after_liftoff_kN") else None
        smax = max(r.get("stroke_max_run_mm") or r["stroke_end_mm"])  # rev. 72: run maximum where recorded
        row = {"key": r["key"], "h_mm": h, "outcome": outcome(r), "flags": r["flags"], "escalate": r["escalate"],
               "D8_min_kN": d8, "lifted": {k: v for k, v in (r.get("lift_after_liftoff_s") or {}).items() if v > 0},
               "stroke_max_mm": smax,
               "stroke_max_leg": LEGS[(r.get("stroke_max_run_mm") or r["stroke_end_mm"]).index(smax)],
               "stroke_margin_mm": round(STROKE_OK_MM - smax, 1), "att_end_deg": r.get("att_end_deg"),
               "over_lift_minus_ref_mm": round(over, 1), "model_mm": round(m, 1),
               "T3_mm": tch.get("post_contact_stroke_mm"), "T4_deg": max(tch.get("max_abs_att_change_deg") or [0]),
               "latch_after_contact_s": tch.get("latch_after_contact_s"),
               "touch_minus_ref_s": round(tch["duration_s"] - rf["touch"]["duration_s"], 2),
               "pump_J": (tch.get("leg_oscillation") or {}).get("work_on_detrended_load_J"),
               "events": [e for e in r["events"] if e[1].startswith(("WARN", "FAULT", "probe_skipped",
                                                                     "INFO_FLOOR_NONPLANAR", "fault"))][:6],
               "final_phase": r.get("final_phase")}
        if r["floor"] == "flat":
            g = flat[f"{r['level']}|Fs{r['fs_kN']}"]
            for k in ("D8_min_kN", "stroke_max_mm", "T3_mm", "T4_deg", "latch_after_contact_s", "touch_minus_ref_s",
                      "over_lift_minus_ref_mm"):
                if row[k] is not None:
                    g[k].append(row[k])
            g["outcomes"].append(row["outcome"])
            g["rows"].append(row)
        else:
            slope.append(row)
    flat_sum = {}
    for k, g in flat.items():
        worst_d8 = min(g["rows"], key=lambda x: x["D8_min_kN"])
        worst_s = max(g["rows"], key=lambda x: x["stroke_max_mm"])
        flat_sum[k] = {"n": len(g["outcomes"]), "pass": g["outcomes"].count("PASS"),
                       "D8_min_kN": [min(g["D8_min_kN"]), worst_d8["key"]],
                       "stroke_max_mm": [max(g["stroke_max_mm"]), worst_s["key"]],
                       "T3_max_mm": max(g["T3_mm"]), "T4_max_deg": max(g["T4_deg"]),
                       "latch_after_contact_max_s": max(g["latch_after_contact_s"]),
                       "touch_minus_ref_s": [min(g["touch_minus_ref_s"]), max(g["touch_minus_ref_s"])]}
    refs = {"|".join(map(str, k)): {"stroke_max_mm": max(v["stroke_end_mm"]), "cmd": v["cmd_sha256"],
                                    "over_lift_mm": v["crawler_clearance_end_mm"]["true_minus_estimate"],
                                    "D8_min_kN": min(v["min_F_after_liftoff_kN"].values()), "pass": v["pass"]}
            for k, v in ref.items()}
    ratio = {k: [min(v), max(v), round(sum(v) / len(v), 3), len(v)] for k, v in sorted(model.items())}
    return {"refs": refs, "flat": flat_sum, "slope": sorted(slope, key=lambda x: x["key"]), "over_lift_ratio": ratio}


def g5(rows):
    out = []
    count = defaultdict(lambda: [0, 0])
    for r in rows:
        if "error" in r:
            out.append({"key": r["key"], "error": r["error"]})
            continue
        _, lv, fs, tm, leg = r["key"].split("|")
        for x in r["runs"]:
            lifts = x.get("lifts", {})
            per_leg = max((lifts.get(lg, {}).get("sum_s", 0.0) for lg in x["pair"]), default=0.0)
            g = dict(x["gates"])
            if x.get("fast"):
                g.pop("U832_pair_union", None)
                g["U832_per_leg"] = per_leg <= 1.8
            bad = [k for k, v in g.items() if not v]
            c = count[f"{x['event']}|{tm}|{lv}|Fs{fs}"]
            c[0] += 1
            c[1] += int(bool(bad))
            if bad:
                mins = x.get("min_F_after_W_kN") or {}
                m = min(mins.values()) if mins else None
                adj_out = x.get("adj_lift_outside_W_s", 0.0)
                adj = [lg for lg in LEGS if lg not in x["pair"]]
                adj_gap = max((lifts.get(lg, {}).get("max_gap_mm", 0.0) for lg in adj), default=0.0)
                event_lift_after_W = any(
                    lifts.get(lg, {}).get("last_touch_s", 0.0) > x["W_end_s"] + 1e-9 for lg in x["pair"])
                out.append({"key": r["key"], "event": x["event"], "offset_s": x["offset_s"], "fails": bad,
                            "min_after_W_kN": mins, "split": None if m is None else ("contact" if m > -0.5 else "lift"),
                            "adj_lift_outside_W_s": adj_out, "adj_max_gap_mm": adj_gap,
                            "event_leg_lift_after_W": event_lift_after_W,
                            "per_leg_s": per_leg, "union_s": x["pair_union_s"], "late_starts": x["n_late_starts"],
                            "starts": x["reapproach_starts"][:10], "twist_bundles": x["twist"]["bundles"],
                            "att_end_deg": x["att_end_deg"], "phase_at_event": x.get("phase_at_event")})
    return {"counts": {k: {"n": v[0], "fail": v[1]} for k, v in sorted(count.items())}, "fails": out}


def main():
    d = Path(sys.argv[1])
    rows = []
    for p in sorted(d.glob("r69_g8_*.json")):
        if p.name == "r69_g8_xcheck.json":
            continue
        rows += load(p)
    fix = d / "r69_slope_clearance_v2.json"
    n_fixed = 0
    if fix.exists():
        # slope re-run with the corrected crawler clearance (all nodes); commands must be identical
        v2 = {r["key"]: r for r in load(fix)}
        for r in rows:
            if r["key"] in v2:
                if v2[r["key"]]["cmd_sha256"] != r["cmd_sha256"]:
                    raise SystemExit(f"command hash differs for {r['key']}")
                r["crawler_clearance_end_mm"] = v2[r["key"]]["crawler_clearance_end_mm"]
                n_fixed += 1
    g5rows = load(d / "r69_g5_top.json") + load(d / "r69_g5_bottom.json")
    res = {"script": "04_scripts/03_control/s8/r69_judge.py", "n_g8": len(rows),
           "clearance_note": f"slope rows: clearance from r69_slope_clearance_v2.json ({n_fixed} rows, all-node "
                             "floor gap); flat rows: first definition (settle-contact nodes, +6.3 mm constant, "
                             "cancels in the ref-subtracted over-lift)",
           "g8": g8([r for r in rows if "error" not in r]), "g8_errors": [r["key"] for r in rows if "error" in r],
           "g5": g5(g5rows)}
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(res["g8"]["refs"], indent=0))
    print(json.dumps(res["g8"]["flat"], indent=0))
    for r in res["g8"]["slope"]:
        print(r["key"].replace("slope|", ""), r["h_mm"], r["outcome"], r["flags"], r["D8_min_kN"], r["lifted"],
              r["stroke_max_leg"], r["stroke_max_mm"], r["att_end_deg"], r["over_lift_minus_ref_mm"],
              r["T3_mm"], r["latch_after_contact_s"], r["pump_J"], r["events"])
    print(json.dumps(res["g8"]["over_lift_ratio"]))
    print(json.dumps(res["g5"]["counts"]))
    for f in res["g5"]["fails"]:
        print(json.dumps(f))


if __name__ == "__main__":
    main()
