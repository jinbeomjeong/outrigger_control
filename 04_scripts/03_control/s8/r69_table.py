"""Spec rev. 69 draft: tables of the G8 (``r69_g8_screen.py``) and G5 (``r69_g5_screen.py``) reduced screens.

G8: pass counts per (level, F_s) and per gap, failed gates, FLAGs, Chrono escalation marks, worst rows (D8 minimum,
  TOUCH attitude, post-contact stroke, stroke-end margin), TOUCH length minus the ref run of the same (floor, level,
  F_s), crawler over-lift (true clearance - controller estimate) against the plane-fit model 3h/4 (raised) / d/4
  (lowered), command hash of the ref runs (determinism / harness identity check).
G5: rev. 67 runs re-judged with the current event-leg definition (spec 350.1: per-leg cumulative lift <= 1.8 s,
  union recorded) and the F_min split of 350.3 (min after W > -0.5 kN = "contact", else "lift"); counts per
  (event, timing, F_s); late re-approach starts; same keys at F_s 0 / 8 from rev. 67 for the trend.

Usage: python -I r69_table.py <out_json> --g8 <g8 json> [...] --g5 <g5 json> [...] [--r67 <rev67 json> [...]]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

F_MIN_KN = 9.4146
STROKE_END_OK_MM = 684.8


def load(paths):
    out = []
    for p in paths:
        out += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    return out


def g8_table(rows):
    errors = [r["key"] for r in rows if "error" in r]
    rows = [r for r in rows if "error" not in r]
    ref = {(r["floor"], r["level"], r["fs_kN"]): r for r in rows if r["leg"] == "ref"}
    by_group = defaultdict(lambda: {"n": 0, "pass": 0, "flag": 0, "escalate": 0})
    by_gap = defaultdict(lambda: {"n": 0, "pass": 0, "escalate": 0})
    failed, flagged, escalated, lift_model = [], [], [], []
    worst = {"D8_min_kN": None, "touch_att_deg": None, "post_contact_mm": None, "stroke_margin_mm": None,
             "touch_extra_s": None}

    def upd(name, val, key, smaller_is_worse):
        cur = worst[name]
        if val is None:
            return
        if cur is None or (val < cur[0] if smaller_is_worse else val > cur[0]):
            worst[name] = (val, key)

    for r in rows:
        if r["leg"] == "ref":
            continue
        _, floor, lv, fs, leg, kind, val = r["key"].split("|")
        grp = by_group[f"{floor}|{lv}|{fs}"]
        gap = by_gap[f"{kind}|{val}"]
        for d in (grp, gap):
            d["n"] += 1
            d["pass"] += int(r["pass"])
            d["escalate"] += int(bool(r["escalate"]))
        grp["flag"] += int(bool(r["flags"]))
        bad = [k for k, v in r["gates"].items() if not v]
        if bad:
            failed.append({"key": r["key"], "gates": bad, "events": r.get("events", [])[:8]})
        if r["flags"]:
            flagged.append({"key": r["key"], "flags": r["flags"]})
        if r["escalate"]:
            escalated.append({"key": r["key"], "escalate": r["escalate"]})
        mins = r.get("min_F_after_liftoff_kN") or {}
        upd("D8_min_kN", min(mins.values()) if mins else None, r["key"], True)
        tch = r.get("touch") or {}
        upd("touch_att_deg", max(tch.get("max_abs_att_change_deg") or [0.0]), r["key"], False)
        upd("post_contact_mm", tch.get("post_contact_stroke_mm"), r["key"], False)
        upd("stroke_margin_mm", STROKE_END_OK_MM - max(r["stroke_end_mm"]), r["key"], True)
        rf = ref.get((floor, lv, float(fs)))
        if rf is not None and tch and rf.get("touch"):
            upd("touch_extra_s", round(tch["duration_s"] - rf["touch"]["duration_s"], 2), r["key"], False)
        info = r["info"]
        cl = r.get("crawler_clearance_end_mm") or {}
        if "true_minus_estimate" in cl:
            h = (info["g0_mm"][LEG_I[leg]] - info["g_start_mm"]) if kind == "raised" else -float(val)
            model = 0.75 * h if h > 0 else -0.25 * h
            ref_over = (rf or {}).get("crawler_clearance_end_mm", {}).get("true_minus_estimate", 0.0)
            lift_model.append({"key": r["key"], "h_mm": round(h, 1), "over_lift_mm": cl["true_minus_estimate"],
                               "over_lift_minus_ref_mm": round(cl["true_minus_estimate"] - ref_over, 1),
                               "model_mm": round(model, 1)})
    ratio = [x["over_lift_minus_ref_mm"] / x["model_mm"] for x in lift_model if abs(x["model_mm"]) > 5]
    return {"errors": errors, "ref_hash": {"|".join(map(str, k)): v["cmd_sha256"] for k, v in ref.items()},
            "groups": dict(by_group), "gaps": dict(by_gap), "failed": failed, "flagged": flagged,
            "escalated": escalated, "worst": worst,
            "over_lift_vs_model": {"n": len(ratio), "ratio_min": round(min(ratio), 3) if ratio else None,
                                   "ratio_max": round(max(ratio), 3) if ratio else None, "rows": lift_model}}


LEG_I = {"FL": 0, "FR": 1, "RL": 2, "RR": 3}


def judge_g5_run(x):
    lifts = x.get("lifts", {})
    pair = x["pair"]
    per_leg = max((lifts.get(lg, {}).get("sum_s", 0.0) for lg in pair), default=0.0)
    if not x.get("fast"):
        return {"pass": x["pass"], "fails": [k for k, v in x["gates"].items() if not v], "per_leg_s": per_leg}
    g = dict(x["gates"])
    g.pop("U832_pair_union", None)
    g["U832_per_leg"] = per_leg <= 1.8
    fails = [k for k, v in g.items() if not v]
    split = None
    if "Fmin_after_W" in fails:
        m = min(x["min_F_after_W_kN"].values())
        split = "contact" if m > -0.5 else "lift"
    return {"pass": not fails, "fails": fails, "per_leg_s": per_leg, "Fmin_split": split}


def g5_table(rows, r67_rows):
    errors = [r["key"] for r in rows if "error" in r]
    counts = defaultdict(lambda: {"n": 0, "fail": 0, "late_starts": 0, "min_after_W_kN": None})
    fails = []

    def add(res_rows, tag):
        for r in res_rows:
            if "error" in r or not r["key"].startswith("screen|"):
                continue
            _, lv, fs, tm, leg = r["key"].split("|")
            for x in r["runs"]:
                j = judge_g5_run(x)
                c = counts[f"{tag}|{x['event']}|{tm}|{lv}|Fs{fs}"]
                c["n"] += 1
                c["fail"] += int(not j["pass"])
                c["late_starts"] += x.get("n_late_starts", 0)
                m = min(x.get("min_F_after_W_kN", x.get("min_F_after_event_kN")).values())
                c["min_after_W_kN"] = m if c["min_after_W_kN"] is None else min(c["min_after_W_kN"], m)
                if not j["pass"] and tag == "rev69":
                    fails.append({"key": r["key"], "event": x["event"], "offset_s": x["offset_s"], **j,
                                  "min_after_W_kN": x.get("min_F_after_W_kN"), "U57_out_s": x.get("adj_lift_outside_W_s")})

    add(rows, "rev69")
    add(r67_rows, "rev67")
    return {"errors": errors, "counts": dict(sorted(counts.items())), "fails": fails}


def main():
    out = Path(sys.argv[1])
    args = {"--g8": [], "--g5": [], "--r67": []}
    cur = None
    for a in sys.argv[2:]:
        if a in args:
            cur = a
        else:
            args[cur].append(a)
    res = {"script": "04_scripts/03_control/s8/r69_table.py", "inputs": args}
    if args["--g8"]:
        res["g8"] = g8_table(load(args["--g8"]))
    if args["--g5"]:
        res["g5"] = g5_table(load(args["--g5"]), load(args["--r67"]) if args["--r67"] else [])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    g8 = res.get("g8")
    if g8:
        print("G8 groups", json.dumps(g8["groups"]))
        print("G8 failed", len(g8["failed"]), "flagged", len(g8["flagged"]), "escalated", len(g8["escalated"]))
        print("G8 worst", json.dumps(g8["worst"]))
        print("G8 over-lift / model", g8["over_lift_vs_model"]["ratio_min"], g8["over_lift_vs_model"]["ratio_max"])
    g5 = res.get("g5")
    if g5:
        for k, v in g5["counts"].items():
            print(k, v)
        print("G5 fails (rev69)", len(g5["fails"]))
    print("->", out)


if __name__ == "__main__":
    main()
