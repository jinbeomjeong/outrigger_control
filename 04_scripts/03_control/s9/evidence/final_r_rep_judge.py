"""FINAL-R-REP (spec 432.6.2): collect the judged rows of the final-controller rigid runs (verify files written by
run_S8C.py judge / run_S6C.py judge-g8 into <evidence dir>) and the same items of the source runs' verify files.

Per case: failed rows, flags, and the value of every judged row next to the source value (same item text).
Usage: python -I final_r_rep_judge.py <repo root> <evidence dir with verify_*.json> <out json>
"""
import json
import sys
from pathlib import Path

ROOT, EV, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BATCH = ROOT / "07_results/S9/batch_FINAL-R-REP_20261030_223425"
cases = json.loads((BATCH / "batch.json").read_text(encoding="utf-8"))["cases"]


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


out = []
for c in cases:
    case = c["case"]
    src_batch = (ROOT / c["source_run"]).parent
    newv = sorted(EV.glob(f"verify_*{case}_*.json")) or sorted(EV.glob(f"verify_*{case}*.json"))
    if not newv:
        out.append({"case": case, "error": "no new verify"})
        continue
    nrows, nmeta = rows_of(newv[0], case)
    oldv = [p for p in (src_batch / "verify_S8C.json", src_batch / "verify_S6_c76_g8.json") if p.exists()]
    orows = rows_of(oldv[0], case)[0] if oldv else []
    omap = {r["item"]: r for r in orows}
    items = []
    for r in nrows:
        o = omap.get(r["item"])
        items.append({"item": r["item"][:110], "kind": r.get("kind"), "passed": r.get("passed"),
                      "value": short(r.get("value")), "limit": short(r.get("limit")),
                      "old_passed": None if o is None else o.get("passed"),
                      "old_value": None if o is None else short(o.get("value"))})
    failed = [i["item"] for i in items if i["passed"] is False and i["kind"] in ("judged", None)]
    out.append({"case": case, "variable": c.get("rep_variable"), "verify_new": str(newv[0].relative_to(ROOT)),
                "verify_old": str(oldv[0].relative_to(ROOT)) if oldv else None, "n_rows": len(items),
                "n_old_rows_matched": sum(i["old_value"] is not None for i in items),
                "failed_judged": failed, "flags": nmeta.get("flags") or nmeta.get("summary", {}).get("flag_rows"),
                "items": items})
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for o in out:
    print(o["case"], o.get("variable"), "rows", o.get("n_rows"), "matched", o.get("n_old_rows_matched"),
          "failed", o.get("failed_judged"), "flags", o.get("flags"))
