"""Compare rev. 55 verify files with rev. 54: row counts, failed rows, new rows, changed passed.

Moved from the cad scratchpad (``cad-run/compare55.py``, 2026-10-25); the hard-coded scratchpad
and batch paths are arguments now. A / B / C / D are compared with the verify files inside the
C-S8-36 batch (judge rev. 54), ml768 / mlj / p1r / rest with ``<rev54>/verify_*_rev54.json``.

usage::

    python -I -X utf8 compare55.py --c36 07_results/S8/c36_20261025_155317
        --rev54 <dir with verify_*_rev54.json> --rev55 <dir with verify_*_rev55.json>
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--c36", type=Path, required=True, help="C-S8-36 batch folder (read only)")
ap.add_argument("--rev54", type=Path, required=True)
ap.add_argument("--rev55", type=Path, required=True)
a = ap.parse_args()
PAIRS = {
    "A": (a.c36 / "A_rt" / "verify_S8ML.json", a.rev55 / "verify_S8ML_A_rev55.json"),
    "B": (a.c36 / "B_f1only" / "verify_S8ML.json", a.rev55 / "verify_S8ML_B_rev55.json"),
    "C": (a.c36 / "C_gate" / "verify_S8C.json", a.rev55 / "verify_S8C_C_rev55.json"),
    "D": (a.c36 / "D_fs24" / "verify_S8C.json", a.rev55 / "verify_S8C_D_rev55.json"),
}
for w in ("ml768", "mlj", "p1r", "rest"):
    kind = "S8ML" if w == "ml768" else "S8C"
    PAIRS[w] = (a.rev54 / f"verify_{kind}_{w}_rev54.json", a.rev55 / f"verify_{kind}_{w}_rev55.json")


def key(r):
    return (r["item"], str(r["case"]))


for name, (pa, pb) in PAIRS.items():
    if not (pa.exists() and pb.exists()):
        print(f"===== {name}: missing {pa if not pa.exists() else pb}")
        continue
    da = json.loads(pa.read_text(encoding="utf-8"))
    db = json.loads(pb.read_text(encoding="utf-8"))
    ra = {key(r): r for r in da["rows"]}
    rb = {key(r): r for r in db["rows"]}
    new = [k for k in rb if k not in ra]
    gone = [k for k in ra if k not in rb]
    changed = [k for k in rb if k in ra and rb[k]["passed"] != ra[k]["passed"]]
    vchanged = [k for k in rb if k in ra and json.dumps(rb[k]["value"], default=str)
                != json.dumps(ra[k]["value"], default=str)]
    fa = sum(1 for r in da["rows"] if r["passed"] is False)
    fb = sum(1 for r in db["rows"] if r["passed"] is False)
    print(f"===== {name}: rows {len(ra)} -> {len(rb)}, failed {fa} -> {fb}")
    for k in new:
        r = rb[k]
        print(f"  NEW [{r['kind']}] passed={r['passed']} | {k[0][:95]} | {k[1]}")
        print(f"      value={json.dumps(r['value'], default=str)[:300]}")
        print(f"      note={str(r.get('note'))[:1500]}")
    for k in gone:
        print("  GONE", k)
    for k in changed:
        print("  PASSED CHANGED", k, ra[k]["passed"], "->", rb[k]["passed"])
    for k in vchanged:
        print("  VALUE CHANGED", k[0][:90], k[1])
    print("  summary:", json.dumps(db["meta"].get("summary"), ensure_ascii=False)[:1500])
