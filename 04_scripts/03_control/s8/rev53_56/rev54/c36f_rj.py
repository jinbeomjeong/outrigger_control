"""Selected rows of the rev54 re-judge files (768, MLJ, p1r, rest) and base52 comparison."""
import json
import sys

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
from pathlib import Path as _Path
sys.path.insert(0,str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import rejudge_file  # noqa: E402  (re-judge archive, env S8_REJUDGE_*)
# ---
KEYS = sys.argv[1].split("|")


def short(v, n=700):
    s = json.dumps(v, ensure_ascii=False, default=str) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "..."


for name in ("verify_S8ML_ml768_rev54.json", "verify_S8C_mlj_rev54.json",
             "verify_S8C_p1r_rev54.json", "verify_S8C_rest_rev54.json"):
    d = json.load(open(rejudge_file("rev54", name), encoding="utf-8"))
    print("=====", name, "rows", len(d["rows"]), "failed", d["meta"].get("failed"))
    for r in d["rows"]:
        if any(k in str(r.get("item")) for k in KEYS):
            print(f"  {r.get('kind')} pass={r.get('passed')} | {short(r.get('item'),140)} | case={r.get('case')} | value={short(r.get('value'),300)}")
            if r.get("note"):
                print("     note:", short(r.get("note"), 600))
    fails = [r for r in d["rows"] if r.get("passed") is False]
    print("  failed rows:", [(short(r.get('item'), 80), r.get('case')) for r in fails][:30])
