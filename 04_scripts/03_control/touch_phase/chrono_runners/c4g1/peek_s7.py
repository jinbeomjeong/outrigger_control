"""Print the stored S7 FINAL args, batch command, and stored R4 / R9 end metrics. Read only.

Usage: python -I -B -X utf8 peek_s7.py
"""
from __future__ import annotations

import json
from pathlib import Path

S9 = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_FINAL-REP_20261030_223359")
CASE = "S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0"


def main() -> None:
    d = S9 / CASE
    print([p.name for p in d.iterdir()])
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    print("keys", list(res)[:60])
    print("args", json.dumps(res.get("args"), indent=0, ensure_ascii=False))
    for k in ("code_state", "code", "runner", "git", "run_meta", "threads", "wall_s"):
        if k in res:
            print(k, str(res[k])[:700])
    print([p.name for p in S9.iterdir() if p.is_file()][:40])
    for p in S9.glob("*"):
        if p.is_file() and p.suffix in (".json",) and p.stat().st_size < 400000:
            t = p.read_text(encoding="utf-8", errors="replace")
            if CASE in t:
                i = t.find(CASE)
                print("--", p.name, t[max(0, i - 300):i + 900])
                break
    print((S9.parent / "batch_FINAL-REP_20261030_223359" / f"{CASE}.log").read_text(encoding="utf-8", errors="replace")[:1200])


if __name__ == "__main__":
    main()
