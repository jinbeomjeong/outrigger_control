"""Row pass-state diff: c36 batch verify files (rev54 judge) vs rev55 re-judge files."""
import json

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import rejudge_file  # noqa: E402  (re-judge archive, env S8_REJUDGE_DIR)
# ---
B = str(REPO / r"07_results\S8\c36_20261025_155317")
PAIRS = [("A_rt\\verify_S8ML.json", "verify_S8ML_A_rev55.json"), ("B_f1only\\verify_S8ML.json", "verify_S8ML_B_rev55.json"),
         ("C_gate\\verify_S8C.json", "verify_S8C_C_rev55.json"), ("D_fs24\\verify_S8C.json", "verify_S8C_D_rev55.json")]
for a, b in PAIRS:
    d4 = json.load(open(B + "\\" + a, encoding="utf-8"))["rows"]
    d5 = json.load(open(rejudge_file("rev55", b), encoding="utf-8"))["rows"]
    k4 = {(str(r["item"]), str(r.get("case"))): (r.get("passed"), json.dumps(r.get("value"), sort_keys=True)) for r in d4}
    k5 = {(str(r["item"]), str(r.get("case"))): (r.get("passed"), json.dumps(r.get("value"), sort_keys=True)) for r in d5}
    ch_pass = [k for k in k5 if k in k4 and k4[k][0] != k5[k][0]]
    ch_val = [k for k in k5 if k in k4 and k4[k][1] != k5[k][1]]
    print(a, "rows", len(d4), "->", len(d5), "| pass changed", len(ch_pass), "| value changed", len(ch_val),
          [x[0][:60] for x in ch_val][:5], "| new", [k[0][:45] for k in k5 if k not in k4],
          "| removed", [k[0][:45] for k in k4 if k not in k5])
