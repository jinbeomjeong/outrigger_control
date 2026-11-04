"""Verdict record of the 10 coupled Chrono rows: T / F / D-5 status plus the Python-Julia comparison of the judged values.

Inputs: final10.json, s8_stop_detail.json, xcheck_julia.json (raw series recomputed in Julia, no Python result read).
Output: final10_verdict.json. The status strings apply the criteria text; nothing here changes a limit.

Run: conda run -n dynamics-dev python -I final10_verdict.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono")
SOIL_ORDER = ("S1", "S6", "S8")


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12)


d = json.loads((HERE / "final10.json").read_text(encoding="utf-8"))
jl = json.loads((HERE / "xcheck_julia.json").read_text(encoding="utf-8"))
x = {}
for cid in SOIL_ORDER:
    row = d["soil"][cid]
    for i, side in enumerate(("on", "off")):
        x[f"{cid}_{side}_F_min_after_dep"] = rel(jl[f"{cid}_{side}"]["F_min_after_dep_kN"], row["F_min_kN"][i])
sa = d["soil"]["S8"]["SA4"]
for side in ("on", "off"):
    x[f"S8_{side}_crawler_at_stop"] = rel(jl[f"S8_{side}"]["crawler_at_stop_kN"], sa[side]["crawler_at_stop_kN"])
    x[f"S8_{side}_crawler_max_after"] = rel(jl[f"S8_{side}"]["crawler_max_after_kN"], sa[side]["crawler_max_after_kN"])
    x[f"S8_{side}_F_min_after_stop"] = rel(min(jl[f"S8_{side}"]["F_min_after_stop_kN"]), sa[side]["F_min_after_stop_kN"])
clause = {side: [jl[f"S8_{side}"]["clause_pass"], sa[side]["clause_pass"]] for side in ("on", "off")}
worst = max(x.values())
t1_rigid = sum(len(v["T1_flips"]) for v in d["rigid"].values())
t1_soil = sum(len(v["T1_flips"]) for v in d["soil"].values())
out = {
    "criteria_sha256": d["criteria_sha256"],
    "status": "HOLD_USER_DECISION",
    "status_reason": "S8 clause 'crawler after the stop <= crawler at the stop + 0.01 W' (criteria 9.1) passes off and fails on: T-2 and F-5 candidate; criteria 9.1 rev. 6 says stop and ask before the conclusion",
    "T1_flips": {"rigid_7": t1_rigid, "soil_3": t1_soil},
    "T2_candidates": [{"row": "S8", "kind": "safe stop -> SA-4 clause violated", "on": sa["on"], "off": sa["off"]}],
    "T3": "not applicable to Chrono rows (reduced-model rows only); clipped harness: see clip_verdict in final10.json, no change in 14 pairs",
    "F_candidates": [{"id": "F-5", "row": "S8", "basis": "criteria 10.2 lists SA-4 violation; 10.1 conditions 1-5 met as written"}],
    "D5_auto_switch": {"no_failure_in_10_rows": False, "reason": "S8 candidate open; switch not started"},
    "xcheck_python_julia": {"relative_diff": x, "worst": worst, "clause_same": clause, "grade": "match" if worst <= 1e-9 else ("allowed" if worst <= 1e-6 else "mismatch")},
}
(HERE / "final10_verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print(json.dumps({"xcheck": out["xcheck_python_julia"], "T1": out["T1_flips"]}, indent=0, default=float))
print("rigid sets", {k: v["sets_s"] for k, v in d["rigid"].items()})
print("rigid V5", {k: v["V5"] for k, v in d["rigid"].items()})
print("rigid E", {k: [v["E1_s"], v["E_min_r"], v["E_long93_s"], v["E3_between_mm"], v["E3_max_mm"], v["E4_swaps"]] for k, v in d["rigid"].items()})
print("item8", {k: [v["F_top_mid_bot_kN"], v["ordering_pass"]] for k, v in d["item8"].items()})
print("rigid bar", {k: [v["bar"], v["F_min_kN"], v["ready_s"], v["att_last5_deg"], v["gap_mm"], v["stroke_mm"], v["leg"]] for k, v in d["rigid"].items()})
