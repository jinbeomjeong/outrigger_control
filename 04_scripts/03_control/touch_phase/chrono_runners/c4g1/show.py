"""Print the rigid values table compactly. Read only.

Usage: python -I -B -X utf8 show.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono")


def r(v, n=3):
    if isinstance(v, float):
        return round(v, n)
    if isinstance(v, list):
        return [r(x, n) for x in v]
    if isinstance(v, dict):
        return {k: r(x, n) for k, x in v.items()}
    return v


def main() -> None:
    doc = json.loads((OUT / "c4g1_rigid_values.json").read_text(encoding="utf-8"))
    for row, v in doc.items():
        on, off = v["on"], v["off"]
        print("=====", row, "wall", r(on["wall_s"], 0), "end", r(on["end_t_s"]), on["final_phase"], "failed", v["meta_failed"], "hold", v["meta_hold"], v["failed_rows"])
        for q in ("t_te_s", "t_lift_s", "t_crawler_zero_s", "tau_te_mm", "tau_lift_mm", "D_te_kN", "D_lift_kN", "ready_t_s", "W_kN", "head_pressure_max_bar"):
            print(f"  {q:24s} on {r(on.get(q))} off {r(off.get(q))}")
        print("  F_win on", r(on["F_win_kN"]), "off", r(off["F_win_kN"]))
        for q in ("F_min_lift8_kN", "F_min_zero_to_cut_kN", "F_min_after_zero_all_kN"):
            print(f"  {q} on", r(on[q]), "off", r(off[q]))
        print("  stroke max on", r(on["stroke_max_mm"], 2), "off", r(off["stroke_max_mm"], 2), "end on", r(on["stroke_end_mm"], 2))
        print("  end att on", r(on["end_attitude_deg"], 4), "off", r(off["end_attitude_deg"], 4))
        print("  rows", r(v["rows"]))
        print("  hold meta", {k: r(x, 6) for k, x in (v["touch_twist_hold"] or {}).items() if k != "settings"})
        print("  ev", v["events_hold"], v["events_warn"][:8])
        s = v["side"]
        print("  side", {k: s[k] for k in ("c2_sha256", "pad_gap_offsets_m", "models_built_offsets", "main_tree_modules_at_end", "config_has_hold", "config_has_clip", "flow_limit", "env")}, s["outrigger_sim"][-60:])


if __name__ == "__main__":
    main()
