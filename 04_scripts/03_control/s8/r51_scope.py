"""R51-1 / C-S8-36 scope: episodes of the S8 main ML batch for the re-approach re-trigger rerun.

Spec 00_docs/04_control/s6_control_spec.md rev. 51 225 (C-S8-36) / rev. 52. Reads
06_analysis/02_control/s8/s8_ml_rev51_reapp_scan.json (rev. 51) and the episode case.json files; read only.
Selection (rev. 51 225 C-S8-36): ping-pong episodes (re-approach starts >= 3 after event + 1.5 s) plus
top / middle fast front settlements (front leg, rate > 50 mm/s, depth > 15 mm). Also lists the reduced-harness
condition of each (floor, F_s, beta, per-leg seal, depth, ramp).
Usage: python -I r51_scope.py <project_root> <out_json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
BATCH = ROOT / "07_results" / "S8" / "ml_main_20261025_090131"
scan = json.loads((ROOT / "06_analysis" / "02_control" / "s8" / "s8_ml_rev51_reapp_scan.json").read_text(encoding="utf-8"))
rows = scan["rows"]


def late(r):
    return len(r.get("late_starts") or [])


def case_info(case):
    c = json.loads((BATCH / "episodes" / case / "case.json").read_text(encoding="utf-8"))
    s = c["settings"]
    meta = json.loads((BATCH / "episodes" / case / "record" / "meta.json").read_text(encoding="utf-8"))
    ml = meta["run"]["scenario"]["settings"]["ml_meta"]
    return {"floor_deg": s["base"]["floor_deg"], "fs_kN": s["base"]["fs_kN"], "beta_GPa": s["base"]["beta_GPa"],
            "seal_N": ml["seal_friction_N"], "init_seal_N": ml["initial_seal_state_N"],
            "L0r_m": s["base"]["rod_dead_length_m"], "t_after_branch_s": s["episode"]["t_after_branch_s"]}


pingpong, fastfront = [], []
for r in rows:
    if late(r) >= 3:
        pingpong.append(r["case"])
    if (r["kind"] == "settle" and r["leg"] in ("FL", "FR") and r["level"] in ("top", "middle")
            and r["ramp_s"] and r["depth_mm"] > 15.0 and r["depth_mm"] / r["ramp_s"] > 50.0):
        fastfront.append(r["case"])
def _count(pred):
    return [r["case"] for r in rows if r["kind"] == "settle" and r["ramp_s"] and pred(r)]


variants = {
    "front_any_level_fast": _count(lambda r: r["leg"] in ("FL", "FR") and r["depth_mm"] > 15 and r["depth_mm"] / r["ramp_s"] > 50),
    "any_leg_top_middle_fast": _count(lambda r: r["level"] in ("top", "middle") and r["depth_mm"] > 15 and r["depth_mm"] / r["ramp_s"] > 50),
    "front_top_middle_rate50_any_depth": _count(lambda r: r["leg"] in ("FL", "FR") and r["level"] in ("top", "middle") and r["depth_mm"] / r["ramp_s"] > 50),
    "front_top_middle_depth15_rate20": _count(lambda r: r["leg"] in ("FL", "FR") and r["level"] in ("top", "middle") and r["depth_mm"] > 15 and r["depth_mm"] / r["ramp_s"] > 20),
    "starts_ge2_after_event": [r["case"] for r in rows if late(r) >= 1],
}
for k, v in variants.items():
    print("variant", k, len(v))
scope = list(dict.fromkeys(pingpong + fastfront))
by = {r["case"]: r for r in rows}
out = {"pingpong": pingpong, "fast_front_top_middle": fastfront, "scope": scope, "n_scope": len(scope), "cases": {}}
for case in scope + ["ML24_ep7"]:
    r = by[case]
    out["cases"][case] = {**{k: r[k] for k in ("kind", "leg", "depth_mm", "ramp_s", "level", "fs_kN", "beta_GPa",
                                                "n_starts", "leg_changes")},
                          "late_starts": r.get("late_starts"), **case_info(case)}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print("pingpong", len(pingpong), pingpong)
print("fast front top/middle", len(fastfront))
print("scope", len(scope))
for case in out["cases"]:
    c = out["cases"][case]
    print(case, c["level"], c["leg"], c["depth_mm"], c["ramp_s"], "floor", c["floor_deg"], "Fs", c["fs_kN"],
          "beta", c["beta_GPa"], "late", len(c["late_starts"] or []), "starts", c["n_starts"])
