"""Print c4g2_values.json compactly. Read only.

Usage: python -I -B -X utf8 show.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono")
JC, JP = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)", "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"
M5 = "item 9 M5 closed loop: min true / under F_min [s] / lifted [s]"


def r(v, n=2):
    if isinstance(v, float):
        return round(v, n)
    if isinstance(v, (list, tuple)):
        return [r(x, n) for x in v]
    if isinstance(v, dict):
        return {k: r(x, n) for k, x in v.items()}
    return v


def side(m: dict) -> str:
    q = {k: r(m.get(k), 3) for k in ("t_te_s", "tau_te_mm", "D_te_kN", "t_lift_s", "tau_lift_mm", "D_lift_kN", "ready_t_s", "end_t_s", "final_phase", "re_ready_after_event_s", "head_pressure_max_bar", "u_cmd_max_over_vmax", "u_applied_max_over_vmax", "wall_s")}
    return json.dumps(q)


def main() -> None:
    doc = json.loads((OUT / "c4g2_values.json").read_text(encoding="utf-8"))
    for row, v in doc.items():
        on = v["on"]
        off = v.get("off")
        print("=====", row, "failed", v["meta_failed"], "hold", v["meta_hold"], v["failed_rows"])
        print(" ON ", side(on))
        if off:
            print(" OFF", side(off))
        print(" lift8 on", r(on["F_min_lift8_kN"]), "off", r(off["F_min_lift8_kN"]) if off else None)
        print(" zero on", r(on["F_min_zero_kN"]), "off", r(off["F_min_zero_kN"]) if off else None)
        print(" zero40 on", r(on["F_min_zero_to40_kN"]), "off", r(off["F_min_zero_to40_kN"]) if off else None)
        if on.get("after_event"):
            print(" ev", r(on["event_t_s"]), on["phase_at_event"], "on", {g: [r(x["min_interval_kN"]), r(x["t_rel_s"]), r(x["under_F_min_s"], 3), r(x["airborne_s"], 3)] for g, x in on["after_event"].items()})
            if off:
                print("    off", {g: [r(x["min_interval_kN"]), r(x["t_rel_s"]), r(x["under_F_min_s"], 3), r(x["airborne_s"], 3)] for g, x in off["after_event"].items()})
        print(" stroke max", r(on["stroke_max_mm"]), "off", r(off["stroke_max_mm"]) if off else None, "end att", r(on["end_attitude_deg"], 4))
        rr = v["rows"]
        for k in rr:
            if k in (JC, JP, M5) or k.startswith(("3 F_min", "2 attitude", "4 max", "run")) or "re-READY" in k:
                print("  row", k[:44], r(rr[k]["value"], 3), rr[k]["passed"])
        print(" hold", r(on["hold_meta"], 6), on["hold_events"], "achieved", r(on.get("achieved_tau_hold_mm"), 3))
        print(" reapp", [(r(a, 1), b) for a, b in on["reapproach_starts"]], "defer", [(r(a, 1), b) for a, b in on["retrigger_deferred"]], "paused", [(r(a, 1), b) for a, b in on["lift_paused"]], "warn", [(r(a, 1), b) for a, b in on["warn_fault"]])
        if off:
            print(" off reapp", [(r(a, 1), b) for a, b in off["reapproach_starts"]], "paused", [(r(a, 1), b) for a, b in off["lift_paused"]])
        print(" first diff", v.get("first_diff_vs_off"), "sampling", {k[:20]: x for k, x in v["sampling_only_rows"].items() if x["count"]})
        if "bit_vs_stored_40s" in v:
            print(" bit", {k: (x["different"], x["arrays"], x["values"]) for k, x in v["bit_vs_stored_40s"].items()})
            print(" vs c4g1 on first diff", v["first_diff_vs_c4g1_on"], "c4g1 on", side(v["c4g1_on"]))
        print(" last3", r(on["touch_last3"], 3))
        s = v["side"]
        print(" side", s["c2_sha256"][:12], s["main_tree_modules_at_end"], s["config_retrigger_samples"], s["config_clip"], s["fs_kN"], s["flow_limit"], s["models_built_offsets"], s["outrigger_sim"][-46:])


if __name__ == "__main__":
    main()
