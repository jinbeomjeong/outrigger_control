"""Spec rev. 70 draft: acceptance table of the P-S8-28 candidates (r70_p28_screen.py JSON).

Acceptance (spec 364 / rev. 70): per run FAULT 0, no pad lift after the crawler lift-off, D8 (min F after lift-off
>= F_min + 5 kN), READY, stroke at READY <= 684.8 mm, final attitude |roll|, |pitch| <= 0.2 deg, true crawler
clearance (all nodes) >= target - 5 mm = 45 mm. Records per variant: counts, worst values, guard / anchor use,
re-ground runs, command hashes against a baseline (r69 batch JSON: proj).

Stroke gate (rev. 72, spec 366 correction): run maximum of the motor stroke (``stroke_max_run_mm``) where the record
has it, else the end value (records before rev. 72; ``--runmax`` re-runs of the same commands fill it in).

Usage: python -I r70_judge.py <out_json> --runs <r70 json> [...] [--base <r69 json> [...]] [--runmax <json> [...]]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

CLEAR_MIN_MM = 45.0


def load(paths):
    out = []
    for p in paths:
        out += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    return out


def verdict(r):
    g = r.get("gates", {})
    c = (r.get("crawler_clearance_end_mm") or {}).get("true")
    fails = [k for k, v in g.items() if not v]
    if c is not None and c < CLEAR_MIN_MM and r.get("final_phase") == "ready":
        fails.append("clearance_45")
    return fails


def main():
    out = Path(sys.argv[1])
    args = {"--runs": [], "--base": [], "--runmax": []}
    cur = None
    for a in sys.argv[2:]:
        if a in args:
            cur = a
        else:
            args[cur].append(a)
    rows = load(args["--runs"])
    base = {r["key"]: r for r in load(args["--base"])} if args["--base"] else {}
    # spec rev. 72 (366 correction): stroke gate = run maximum. Old records hold only the end value; re-runs given
    # with --runmax (same command hash required) supply the run maximum for those keys.
    override = {r["key"]: r for r in load(args["--runmax"])} if args["--runmax"] else {}
    n_override = 0
    for r in rows:
        o = override.get(r.get("key"))
        if o is None or "error" in r:
            continue
        if o.get("cmd_sha256") != r.get("cmd_sha256"):
            raise SystemExit(f"command hash differs for {r['key']}")
        r["stroke_max_run_mm"] = o["stroke_max_run_mm"]
        r["gates"]["stroke_end"] = o["gates"]["stroke_end"]
        n_override += 1
    for r in rows:
        if "error" not in r:
            r["stroke_basis"] = "run_max" if "stroke_max_run_mm" in r else "end_value"
    by_var = defaultdict(list)
    for r in rows:
        if "error" in r:
            by_var["errors"].append(r["key"])
            continue
        by_var[r["variant"]].append(r)
    res = {"script": "04_scripts/03_control/s8/r70_judge.py", "inputs": args, "variants": {},
           "stroke_gate": "run maximum where recorded (rev. 72), else end value",
           "n_runmax_override": n_override,
           "n_end_value_only": sum(1 for r in rows if r.get("stroke_basis") == "end_value")}
    for var, rs in by_var.items():
        if var == "errors":
            res["errors"] = rs
            continue
        cnt = defaultdict(int)
        fails, worst = [], {"D8_min_kN": None, "stroke_max_mm": None, "att_end_deg": None, "clear_min_mm": None,
                            "clear_max_mm": None}
        guard, anchor, reground, hash_changed, flags = [], 0, [], [], []
        for r in rs:
            f = verdict(r)
            cnt["n"] += 1
            cnt["accept"] += int(not f)
            cnt["fault"] += int(r.get("final_phase") in ("fault", "fault_reground"))
            cnt["lift"] += int(not r["gates"].get("no_lift", True))
            cnt["stroke_margin"] += int(not r["gates"].get("stroke_end", True))
            cnt["flagged"] += int(bool(r.get("flags")))
            if f:
                fails.append({"key": r["r69_key"], "fails": f, "final_phase": r.get("final_phase"),
                              "stroke_max_mm": max(r["stroke_end_mm"]), "att_end_deg": r.get("att_end_deg"),
                              "clearance": r.get("crawler_clearance_end_mm"), "p28": r.get("p28")})
            if r.get("flags"):
                flags.append({"key": r["r69_key"], "flags": r["flags"],
                              "latch_after_contact_s": (r.get("touch") or {}).get("latch_after_contact_s")})
            d8 = min(r["min_F_after_liftoff_kN"].values()) if r.get("min_F_after_liftoff_kN") else None
            vals = {"D8_min_kN": d8, "stroke_max_mm": max(r.get("stroke_max_run_mm") or r["stroke_end_mm"]),
                    "att_end_deg": max(abs(a) for a in r.get("att_end_deg") or [0.0]),
                    "clear_min_mm": (r.get("crawler_clearance_end_mm") or {}).get("true"),
                    "clear_max_mm": (r.get("crawler_clearance_end_mm") or {}).get("true")}
            for k, v in vals.items():
                if v is None:
                    continue
                smaller = k in ("D8_min_kN", "clear_min_mm")
                if worst[k] is None or (v < worst[k][0] if smaller else v > worst[k][0]):
                    worst[k] = (v, r["r69_key"])
            p = r.get("p28") or {}
            if p.get("guard_periods"):
                guard.append({"key": r["r69_key"], "periods": p["guard_periods"], "mode": p["guard_mode"]})
            if (p.get("anchor") or {}).get("applied"):
                anchor += 1
            if p.get("reground"):
                reground.append({"key": r["r69_key"], **p["reground"],
                                 "lift_after_liftoff_s": r.get("lift_after_liftoff_s"),
                                 "att_end_deg": r.get("att_end_deg")})
            b = base.get(r["r69_key"])
            if b is not None and b.get("cmd_sha256") != r.get("cmd_sha256"):
                hash_changed.append(r["r69_key"])
        res["variants"][var] = {"counts": dict(cnt), "worst": worst, "anchor_applied": anchor, "guard": guard,
                                "reground": reground, "fails": fails, "flags": flags,
                                "hash_changed_vs_base": {"n": len(hash_changed), "n_compared": sum(
                                    1 for r in rs if r["r69_key"] in base), "keys": hash_changed}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for var, v in res["variants"].items():
        print(var, json.dumps(v["counts"]), "anchor", v["anchor_applied"], "guard", len(v["guard"]),
              "reground", len(v["reground"]), "hash changed", v["hash_changed_vs_base"]["n"], "/",
              v["hash_changed_vs_base"]["n_compared"])
        print("  worst", json.dumps(v["worst"]))
        for f in v["fails"][:30]:
            print("  FAIL", f["key"], f["fails"], f["final_phase"], f["stroke_max_mm"], f["att_end_deg"],
                  (f["clearance"] or {}).get("true"))
        for g in v["reground"][:30]:
            print("  REGROUND", json.dumps(g))
        for g in v["flags"]:
            print("  FLAG", json.dumps(g))
    print("errors", res.get("errors"))


if __name__ == "__main__":
    main()
