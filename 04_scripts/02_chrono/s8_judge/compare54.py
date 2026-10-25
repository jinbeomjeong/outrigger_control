"""Compare base52 vs rev54 verify files: judged failures, rows whose ``passed`` changed, twist rows.

Moved from the cad scratchpad (``cad-run/compare54.py``, 2026-10-25). Reads
``<dir>/verify_<name>_base52.json`` and ``<dir>/verify_<name>_rev54.json`` (outputs of
``rejudge_batches.py --tag base52`` / ``--tag rev54``). Copies (local only, ``07_results`` is
gitignored): ``07_results/S8/archive/18_S8_extra/rejudge/rev54/`` (mlj, p1r, rest) and
``07_results/S8/archive/rejudge_ml768/rev54/`` (ml768, pass it as a separate ``<dir>`` with
``S8ML_ml768``). Git keeps the ml768 summaries only, in
``06_analysis/01_chrono/18_S8/rejudge/rev54/``.

usage::

    python -I -X utf8 compare54.py <dir> [S8ML_ml768 S8C_mlj S8C_p1r S8C_rest]
"""
import json
import sys
from collections import Counter
from pathlib import Path

d = Path(sys.argv[1])
pairs = sys.argv[2:] or ["S8ML_ml768", "S8C_mlj", "S8C_p1r", "S8C_rest"]


def key(r):
    return (r["item"], str(r["case"]))


for name in pairs:
    a_p, b_p = d / f"verify_{name}_base52.json", d / f"verify_{name}_rev54.json"
    if not b_p.exists():
        print(f"===== {name}: {b_p.name} missing (summary only?)")
        continue
    b = json.loads(b_p.read_text(encoding="utf-8"))
    a = json.loads(a_p.read_text(encoding="utf-8")) if a_p.exists() else None
    print(f"===== {name}: rows {b['meta']['rows']} failed {b['meta']['failed']}"
          + ("" if a is None else f" (base52 rows {a['meta']['rows']} failed {a['meta']['failed']})"))
    for r in b["rows"]:
        if r["passed"] is False:
            print("  FAIL:", r["item"][:110], "|", r["case"], "|", str(r["value"])[:120])
    if a is not None:
        am = {key(r): r for r in a["rows"]}
        bm = {key(r): r for r in b["rows"]}
        ch = [(k, am[k]["passed"], bm[k]["passed"]) for k in am.keys() & bm.keys()
              if am[k]["passed"] != bm[k]["passed"]]
        for k, x, y in sorted(ch):
            print(f"  CHANGED passed {x} -> {y}: {k[0][:100]} | {k[1]}")
        new = Counter(k[0][:60] for k in bm.keys() - am.keys())
        gone = Counter(k[0][:60] for k in am.keys() - bm.keys())
        print("  new row items:", dict(new))
        print("  removed row items:", dict(gone))
        vc = [k for k in am.keys() & bm.keys() if am[k]["kind"] == "judged"
              and am[k]["value"] != bm[k]["value"]]
        print(f"  judged rows with another value (same passed): {len(vc)}")
        for k in sorted(vc)[:25]:
            print(f"    {k[0][:80]} | {k[1]} | {str(am[k]['value'])[:60]} -> {str(bm[k]['value'])[:60]}")
    for r in b["rows"]:
        it = r["item"]
        if it.startswith("C-S8-36") or it.startswith("C-S8-40") or it.startswith("I1 "):
            print("  ROW:", it[:150])
            print("       kind", r["kind"], "passed", r["passed"], "value", str(r["value"])[:300])
            if r.get("note"):
                print("       note", str(r["note"])[:600])
