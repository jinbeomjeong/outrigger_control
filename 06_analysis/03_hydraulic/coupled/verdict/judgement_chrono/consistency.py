"""Consistency checks of the interim verdict: re-judged stored runs vs the rev. 85 verify files, settings
difference of each pair, attitude after lift-off, LOC time, F_min row values. Writes consistency.json.

Run: conda run -n dynamics-dev python -I consistency.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
EV = ROOT / "06_analysis/02_control/s9/rev85/evidence/final_r_rep"
S8 = ROOT / "07_results/S8"
CASES = {
    "R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4",
    "R12": "E_G4_Fs4", "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0",
}


def diff(a, b, path="", out=None, limit=12):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diff(a.get(k), b.get(k), f"{path}.{k}", out, limit)
    elif a != b and len(out) < limit:
        out.append([path, str(a)[:80], str(b)[:80]])
    return out


report = {}
for cid, case in CASES.items():
    off_batch = sorted(S8.glob(f"final_{case}_2*"))[-1]
    on_batch = sorted(S8.glob(f"coupled_eta085_{case}_2*"))[-1]
    new = json.loads((HERE / "verify" / f"verify_{off_batch.name}.json").read_text(encoding="utf-8"))
    old = json.loads((EV / f"verify_{off_batch.name}.json").read_text(encoding="utf-8"))
    on = json.loads((HERE / "verify" / f"verify_{on_batch.name}.json").read_text(encoding="utf-8"))
    rows_old = {r["item"]: r for r in old["rows"]}
    changed = [r["item"][:70] for r in new["rows"] if r["item"] in rows_old
               and (r.get("value") != rows_old[r["item"]].get("value") or r.get("passed") != rows_old[r["item"]].get("passed"))]
    ro = json.loads((on_batch / case / "result.json").read_text(encoding="utf-8"))
    rf = json.loads((off_batch / case / "result.json").read_text(encoding="utf-8"))
    judged = [r for r in on["rows"] if r.get("kind") in ("judged", "function", "anomaly")]
    report[cid] = {
        "rejudge_rows": len(new["rows"]), "evidence_rows": len(old["rows"]), "rejudge_changed_rows": changed,
        "judge_rev_same": new["meta"].get("judge_revision") == old["meta"].get("judge_revision"),
        "on_judged_rows": len(judged), "on_judged_passed": sum(r.get("passed") is True for r in judged),
        "settings_diff_s8": diff(ro["settings"].get("s8"), rf["settings"].get("s8")),
        "settings_diff_l2b": diff(ro["settings"].get("l2b_start"), rf["settings"].get("l2b_start")),
        "loc_first_on_off": [next((e for e in json.loads((d / case / "controller_events.json").read_text(encoding="utf-8")) if "crawler_liftoff_confirmed" in e), None)
                             for d in (on_batch, off_batch)],
    }
    m = lambda s: next(x for x in s["metrics"] if x["case"] == case)
    report[cid]["t_within_0p2_after_level_s"] = [m(on).get("t_within_0p2_after_level_s"), m(new).get("t_within_0p2_after_level_s")]
(HERE / "consistency.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
print(json.dumps(report, indent=0, default=str))
