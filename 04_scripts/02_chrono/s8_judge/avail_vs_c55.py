"""Compare the judge rev. 56 availability rows (``per_run`` of ``verify_S8ML_A_new56.json``) with
the control ``c55_avail.py`` output on the same ids.

Moved from the cad scratchpad (``cad-run55/avail_vs_c55.py``, 2026-10-25); the source tree, the
judge output and the control JSON are arguments now (the scratchpad ``proj_new56`` tree no longer
exists; use a tree holding the rev. 56 judge, e.g. the project ``03_src`` at commit dd29aae).
Copies: ``07_results/S8/archive/18_S8_extra/rejudge/rev56/verify_S8ML_A_new56.json`` (local
only, gitignored) and ``06_analysis/01_chrono/18_S8/rejudge/rev56/inputs_logs/c55_avail_A17.json``.

usage::

    python -I -X utf8 avail_vs_c55.py --src <03_src> --c55 <c55_avail json>
        --verify <verify_S8ML_A_new56.json>
"""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--src", type=Path, required=True, help="03_src tree with the rev. 56 judge")
ap.add_argument("--c55", type=Path, required=True, help="control c55_avail output JSON")
ap.add_argument("--verify", type=Path, required=True, help="judge rev. 56 verify_S8ML_A file")
a = ap.parse_args()
sys.path.insert(0, str(a.src.resolve()))
from outrigger_sim.verify import s8_control as v  # noqa: E402

c55 = json.loads(a.c55.read_text(encoding="utf-8"))
doc = json.loads(a.verify.read_text(encoding="utf-8"))
(row,) = [r for r in doc["rows"] if r["item"].startswith("C-S8-42 re-READY")]
per = row["per_run"]
ids = c55["ids"]
bad = 0
for c in ids:
    x, y = c55["runs"][c], per[c]
    for side in ("new", "ref"):
        if json.dumps(x[side], sort_keys=True) != json.dumps(y[side], sort_keys=True):
            bad += 1
            print("DIFF", c, side, x[side], y[side])
mine = v.availability_compare({c: per[c]["new"] for c in ids}, {c: per[c]["ref"] for c in ids})
s = c55["summary"]
for k in s:
    same = json.dumps(s[k]) == json.dumps(mine.get(k) if not isinstance(mine.get(k), tuple)
                                          else list(mine[k]))
    if not same:
        bad += 1
    print(f"{k}: c55={s[k]} judge={mine.get(k)} {'OK' if same else 'DIFF'}")
print("per-run records compared:", len(ids), "differences:", bad)
