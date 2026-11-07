"""Summarize h7_exclusion.json (18 T4/T5 rows and the 5 record rows)."""
import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
tot = {}
for path in ("off", "on"):
    agg = dict(n_b=0, n_a=0, ob=0, oa=0, mb=-1e9, ma=-1e9, excl=0, excl_noE5=0, cp=0, cpg=0, cpl=0,
               exo=0, guard_bad=0, gmaxf=-1e9, gmaxfb=-1e9, gmaxtb=-1e9, t5b=0, t5a=0, t5mb=-1e9, t5ma=-1e9,
               t5x=0, own_o=0, own_m=-1e9, t5own_o=0, t5own_m=-1e9)
    for r in sorted(d["rows"], key=lambda r: (r["setting"], r["case"])):
        if not r["judged_T45"]:
            if path == "off":
                o = r["off"]
                print("REC", r["setting"], r["case"], "excl", o["excluded"], "T4", o["T4_before"]["over"], "->",
                      o["T4_after"]["over"])
            continue
        o = r[path]
        b, a = o["T4_before"], o["T4_after"]
        agg["n_b"] += b["n"]; agg["n_a"] += a["n"]; agg["ob"] += b["over"]; agg["oa"] += a["over"]
        agg["mb"] = max(agg["mb"], b["max_kN"] or -1e9); agg["ma"] = max(agg["ma"], a["max_kN"] or -1e9)
        agg["excl"] += o["excluded"]; agg["excl_noE5"] += o["excluded_no_E5"]
        agg["cp"] += o["judged_check_precal"]; agg["cpg"] += o["judged_check_precal_grounded"]
        agg["cpl"] += o["judged_check_precal_locked"]; agg["exo"] += o["excluded_over"]
        g = o.get("guard")
        if g:
            agg["guard_bad"] += int(not (g["all_below_band"] and g["all_forced_negative"]))
            agg["gmaxf"] = max(agg["gmaxf"], g["forced_max_kN"])
            agg["gmaxfb"] = max(agg["gmaxfb"], g["forced_plus_band_max_kN"])
            agg["gmaxtb"] = max(agg["gmaxtb"], g["truth_plus_band_max_kN"])
        if "T4_own_after" in o:
            agg["own_o"] += o["T4_own_after"]["over"]; agg["own_m"] = max(agg["own_m"], o["T4_own_after"]["max_kN"])
        t5 = o.get("T5")
        if t5:
            agg["t5b"] += t5["before_over"]; agg["t5a"] += t5["after_over"]; agg["t5x"] += t5["excluded_samples"]
            agg["t5mb"] = max(agg["t5mb"], t5["before_max_kN"]); agg["t5ma"] = max(agg["t5ma"], t5["after_max_kN"])
            if o["sensor_model"]:
                agg["t5own_o"] += t5["own_after_over"]; agg["t5own_m"] = max(agg["t5own_m"], t5["own_after_max_kN"])
        if path == "off":
            print(r["setting"], r["case"], "n", b["n"], "->", a["n"], "excl", o["excluded"], "(noE5", o["excluded_no_E5"],
                  ") CHECKpre", o["judged_check_precal"], "grounded", o["judged_check_precal_grounded"],
                  "locked", o["judged_check_precal_locked"], "| T4", b["over"], "->", a["over"],
                  "max", round(b["max_kN"], 3), "->", round(a["max_kN"], 3),
                  "| guard", None if not g else (g["all_below_band"], g["all_forced_negative"],
                                                round(g["forced_max_kN"], 2), round(g["forced_plus_band_max_kN"], 2),
                                                round(g["truth_plus_band_max_kN"], 2), g["t_range_s"]),
                  "| T5", None if not t5 else (t5["before_over"], t5["after_over"], round(t5["before_max_kN"], 3),
                                              round(t5["after_max_kN"], 3), t5["excluded_samples"]),
                  "| own", o.get("T4_own_after"), None if not t5 else (t5["own_after_over"], t5["own_after_max_kN"]),
                  "| plain_after", o.get("T4_plain_after"))
            for s in o["remaining_over"]:
                print("   remain", s)
            if t5:
                ph = {}
                for s in t5["after_over_list"]:
                    ph[(s["leg"], s["phase"], s["law"])] = ph.get((s["leg"], s["phase"], s["law"]), 0) + 1
                print("   T5 remain", ph, "own max", max([s["own_kN"] for s in t5["after_over_list"]], default=None))
    tot[path] = agg
    print(path, agg)
Path(sys.argv[2]).write_text(json.dumps(tot, indent=1), encoding="utf-8")
