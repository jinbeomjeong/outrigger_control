"""Print verify JSON structure, summaries, and failed/FLAG rows for c37 bundles."""
import json
import sys
from pathlib import Path

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = Path(str(REPO / r"07_results\S8"))
C37 = ROOT / "c37_20261025_180821"
FILES = {
    "E": C37 / "E_drain" / "verify_S8ML.json",
    "C": C37 / "C_gate" / "verify_S8C.json",
    "D": C37 / "D_fs24" / "verify_S8C.json",
}


def short(v, n=300):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "..."


for tag, f in FILES.items():
    d = json.loads(f.read_text(encoding="utf-8"))
    print("=" * 20, tag, f)
    print("top keys:", list(d.keys()))
    meta = d.get("meta", {})
    print("meta keys:", list(meta.keys()))
    for k in ("judge_revision", "judge_revision_text", "ref_batch", "summary"):
        if k in meta:
            print(f"meta.{k}:", short(meta[k], 4000))
    rows = d.get("rows") or d.get("checks") or []
    print("n rows:", len(rows))
    if rows:
        print("row keys:", list(rows[0].keys()))
    for r in rows:
        st = str(r.get("status", r.get("pass", r.get("result"))))
        txt = short(r, 600)
        if any(w in txt for w in ("FLAG", "fail", "FAIL", "False")) or st.lower() in ("fail", "false"):
            print("  *", txt)
