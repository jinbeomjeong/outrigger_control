"""Reference values of the C and D cases in the rev54 re-judge (p1r, MLJ) for regression compare."""
import json

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import rejudge_file  # noqa: E402  (re-judge archive, env S8_REJUDGE_DIR)
# ---
ITEMS = ("RE1b re-READY", "3 lift-off other legs in the event transient", "3 F_min after the re-READY",
         "3 F_min (1 ms)", "C1 D8", "U-S8-32 event legs", "U-S8-32 adjacent", "3 F_min window end",
         "2 attitude", "item 9 M5", "5a rocking amplitude after", "4 max pressure in the event",
         "re-approach starts", "MLJ FAULT", "I1 J_C", "MLJ U-S8-32")
for name, cases in (("verify_S8C_p1r_rev54.json", ("E_RE1bF_Fs0", "E_RE1bP_Fs0")),
                    ("verify_S8C_mlj_rev54.json", ("MLJ_FS24_Fs0", "MLJ_FS24_Fs8"))):
    d = json.load(open(rejudge_file("rev54", name), encoding="utf-8"))
    print("=====", name)
    for r in d["rows"]:
        if r.get("case") in cases + ("*",) and any(str(r.get("item")).startswith(i) for i in ITEMS):
            v = json.dumps(r.get("value"), default=str)[:200]
            print(f"  {r.get('case')} | {str(r.get('item'))[:70]} | {v} | pass={r.get('passed')}")
            if r.get("case") != "*" and r.get("note") and ("U-S8-32" in str(r.get("item")) or "lift-off other" in str(r.get("item"))):
                print("      note:", str(r.get("note"))[:400])
