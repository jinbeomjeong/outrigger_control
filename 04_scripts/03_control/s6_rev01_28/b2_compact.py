"""Compact per-case view of selected verify rows."""
import json
import sys

# migrated 2026-10-25 from session scratchpad a06eea4a ctrl-run; repository-relative
ROOT = (__import__("pathlib").Path(__file__).resolve().parents[3] / "06_analysis" / "01_chrono" / "16_S6").as_posix() + "/"
fn = sys.argv[1]
pat = sys.argv[2].split("|") if len(sys.argv) > 2 else None
casepat = sys.argv[3] if len(sys.argv) > 3 else ""
d = json.load(open(ROOT + fn, encoding="utf-8"))


def fmt(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, list):
        return "[" + ",".join(fmt(x) for x in v) + "]"
    return str(v)[:50]


cur = None
for r in d["rows"]:
    if casepat and casepat not in r["case"]:
        continue
    if pat and not any(p in r["item"] for p in pat):
        continue
    if r["case"] != cur:
        cur = r["case"]
        print("--", cur)
    flag = {True: "ok", False: "FAIL", None: "rep"}[r["passed"]]
    print(f"   {r['item'][:45]:45s} {fmt(r['value']):45s} lim={fmt(r['limit']):22s} {flag} | {r.get('note','')[:70]}")
