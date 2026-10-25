"""Rev55 re-judge files: summary block, failed rows, ML-0 gate and C-S8-41 rows; diff of row
pass states vs the rev54 files where both exist."""
import json

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import find_rejudge_file, rejudge_file, verify_dir  # noqa: E402
# ---
# The rev. 55 re-judge wrote one folder; the archive splits it into the verify folder and
# the ml768 folder (which also holds verify_S8ML_ml768_pre55.json, not part of this set).
REV55_FILES = {p.name: p for p in verify_dir("rev55").glob("*.json")}
ML768_REV55 = rejudge_file("rev55", "verify_S8ML_ml768_rev55.json")
REV55_FILES[ML768_REV55.name] = ML768_REV55
for f in sorted(REV55_FILES):
    d = json.load(open(REV55_FILES[f], encoding="utf-8"))
    rows = d["rows"]
    fails = [(str(r["item"])[:90], r.get("case")) for r in rows if r.get("passed") is False]
    print("=====", f, "rows", len(rows), "failed", len(fails), "| meta.judge_revision:",
          str(d["meta"].get("judge_revision"))[:60])
    print("   summary:", json.dumps(d["meta"].get("summary") or d.get("summary"), ensure_ascii=False)[:900])
    for r in rows:
        it = str(r.get("item", ""))
        if it.startswith("ML-0 no rod") or it.startswith("C-S8-41") or it.startswith("ML-1 runs with a rod"):
            print("   ROW", it[:80], "| pass", r.get("passed"), "| value", json.dumps(r.get("value"))[:200],
                  "| note", str(r.get("note"))[:300])
    print("   failed:", fails[:25])
    f54 = find_rejudge_file("rev54", f.replace("rev55", "rev54"))
    if f54 is not None:
        d4 = json.load(open(f54, encoding="utf-8"))
        k4 = {(str(r["item"]), str(r.get("case"))): r.get("passed") for r in d4["rows"]}
        k5 = {(str(r["item"]), str(r.get("case"))): r.get("passed") for r in rows}
        ch = [(k[0][:70], k[1], k4[k], v) for k, v in k5.items() if k in k4 and k4[k] != v]
        new = [k for k in k5 if k not in k4]
        gone = [k for k in k4 if k not in k5]
        print("   vs rev54: changed", ch[:10], "| new rows", len(new), [n[0][:50] for n in new][:6],
              "| removed", len(gone))
