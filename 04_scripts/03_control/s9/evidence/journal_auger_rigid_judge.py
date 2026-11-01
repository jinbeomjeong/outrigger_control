"""JOURNAL-AUGER rigid rows (cad 2026-10-31): collect the judged rows of the s8c rows of an s9_batch folder from the
verify files written by ``run_S8C.py judge`` into <evidence dir> (same reading as final_r_rep_judge.py, with the batch
folder as an argument and rows without ``source_run`` allowed: their ``old_*`` fields stay None).

Per case: failed judged rows (kind judged / None, as final_r_rep_judge.py), failed ``function`` rows (attitude
+-0.2 deg, max moving pressure 180 bar, probe attitude change; listed separately), flags, every judged row (item, kind, passed, value, limit) and, when the row has a
``source_run``, the same item of the source verify file. The controller settings of each case ``result.json``
(final rules: soil_stop / scope, flat_soil_margin_m, loc_revoke, diff_sink, P37t / ZIC absent) are added.

Usage: python -I journal_auger_rigid_judge.py <repo root> <s9 batch folder> <evidence dir with verify_*.json> <out json>
"""
import json
import sys
from pathlib import Path

ROOT, BATCH, EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
cases = [c for c in json.loads((BATCH / "batch.json").read_text(encoding="utf-8"))["cases"] if c.get("s8c_check")]


def rows_of(verify, case):
    d = json.loads(Path(verify).read_text(encoding="utf-8"))
    return [r for r in d.get("rows", []) if r.get("case") == case], d.get("meta", {})


def short(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, list):
        return [short(x) for x in v[:6]]
    if isinstance(v, dict):
        return {k: short(x) for k, x in list(v.items())[:6]}
    return v


def final_rules(case_dir: Path) -> dict:
    p = case_dir / "result.json"
    if not p.is_file():
        return {"error": f"no {p}"}
    cm = json.loads(p.read_text(encoding="utf-8")).get("controller_meta") or {}

    def g(block, key):
        return ((cm.get(block) or {}).get("settings") or {}).get(key)

    out = {"soil.enable": g("soil", "enable"), "loc_revoke.enable": g("loc_revoke", "enable"),
           "diff_sink.enable": g("diff_sink", "enable"), "soil_stop": g("lift_stroke_guard", "soil_stop"),
           "soil_stop_scope": g("lift_stroke_guard", "soil_stop_scope"),
           "flat_soil_margin_m": g("slope_clearance_margin", "flat_soil_margin_m"),
           "floor_twist_ledger": "absent" if "floor_twist_ledger" not in cm else g("floor_twist_ledger", "enable"),
           "attitude_integral_clamp": "absent" if "attitude_integral_clamp" not in cm
           else g("attitude_integral_clamp", "enable")}
    out["final_SGS_R4"] = (out["soil.enable"] is True and out["loc_revoke.enable"] is True
                           and out["diff_sink.enable"] is True and out["soil_stop"] is True
                           and out["soil_stop_scope"] == "any_loc" and out["flat_soil_margin_m"] == 0.03
                           and out["floor_twist_ledger"] in ("absent", False)
                           and out["attitude_integral_clamp"] in ("absent", False))
    return out


out = []
for c in cases:
    case = c["case"]
    run_dir = Path(c["s8c_check"]["batch_dir"])
    newv = sorted(EV.glob(f"verify_*{case}_*.json")) or sorted(EV.glob(f"verify_*{case}*.json"))
    if not newv:
        out.append({"case": case, "error": "no new verify", "final_rules": final_rules(run_dir / case)})
        continue
    nrows, nmeta = rows_of(newv[0], case)
    omap = {}
    if c.get("source_run"):
        src_batch = (ROOT / c["source_run"]).parent
        oldv = [p for p in (src_batch / "verify_S8C.json",) if p.exists()]
        omap = {r["item"]: r for r in (rows_of(oldv[0], case)[0] if oldv else [])}
    items = []
    for r in nrows:
        o = omap.get(r["item"])
        items.append({"item": r["item"][:110], "kind": r.get("kind"), "passed": r.get("passed"),
                      "value": short(r.get("value")), "limit": short(r.get("limit")),
                      "old_passed": None if o is None else o.get("passed"),
                      "old_value": None if o is None else short(o.get("value"))})
    failed = [i["item"] for i in items if i["passed"] is False and i["kind"] in ("judged", None)]
    failed_function = [i["item"] for i in items if i["passed"] is False and i["kind"] == "function"]
    out.append({"case": case, "variable": c.get("rep_variable"), "run_dir": run_dir.as_posix(),
                "verify_new": str(newv[0].relative_to(ROOT)) if newv[0].is_relative_to(ROOT) else str(newv[0]),
                "n_rows": len(items), "failed_judged": failed, "failed_function": failed_function,
                "flags": nmeta.get("flags") or nmeta.get("summary", {}).get("flag_rows"),
                "final_rules": final_rules(run_dir / case), "items": items})
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for o in out:
    print(o["case"], o.get("variable"), "rows", o.get("n_rows"), "failed", o.get("failed_judged"),
          "failed_function", o.get("failed_function"), "flags",
          o.get("flags"), "final_SGS_R4", (o.get("final_rules") or {}).get("final_SGS_R4"), o.get("error", ""))
