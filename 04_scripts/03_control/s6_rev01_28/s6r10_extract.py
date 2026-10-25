"""Extract the RE3 judgement essentials into a compact text dump."""

import json
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
ROOT = (REPO / r"06_analysis\01_chrono\16_S6")
OUT = (OUT_DIR / _Path(__file__).name).with_suffix(".txt")
cl = json.loads((ROOT / "verify_S6_L1_closed_loop_re3.json").read_text(encoding="utf-8"))
ge = json.loads((ROOT / "verify_S6_L1_ge1_re3.json").read_text(encoding="utf-8"))
lines = []
w = lines.append
w("META " + json.dumps({k: cl["meta"][k] for k in ("batch", "override_batches", "judgement",
                                                    "c2_revision_by_batch")}, ensure_ascii=False))
w("COUNTS " + json.dumps(cl["counts"]) + " LISTS " + json.dumps(cl["lists"], ensure_ascii=False))
w("ROW KEYS " + json.dumps(list(cl["rows"][0].keys())))
w("--- failed / not-judged rows")
for row in cl["rows"]:
    if row.get("passed") is False or row.get("passed") is None and row.get("kind") != "info":
        w(json.dumps(row, ensure_ascii=False)[:600])
w("--- b1_check")
w(json.dumps(cl["b1_check"], ensure_ascii=False)[:6000])
w("--- event_cases")
w(json.dumps(cl["event_cases_RE1b_RE1c"], ensure_ascii=False)[:8000])
w("--- note_items_6_T")
w(str(cl["note_items_6_T"])[:2000])
w("--- GE1 meta")
w(json.dumps(ge["meta"], ensure_ascii=False)[:3000])
w("--- GE1 promotion_checks")
for item in ge["promotion_checks"]:
    w(json.dumps(item, ensure_ascii=False)[:500])
OUT.write_text("\n".join(lines), encoding="utf-8")
print(OUT, len(lines))
