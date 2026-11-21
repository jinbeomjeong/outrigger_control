"""Extract per-row design inputs from stored, pre-edition-4a VB rev 4 results.

Allowed inputs only (past committed results): h6_dg3_v4on.json, h8_noise_VB.json,
h8_seedext_VB.json. Writes a compact CSV with key structure, READY time, final
phase, pass flag. No edition-4a outputs are read.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
OUT = Path(sys.argv[1])
FILES = ["h6_dg3_v4on.json", "h8_noise_VB.json", "h8_seedext_VB.json"]


def strip_key(k: str) -> str:
    return k.split("#", 1)[1] if "#" in k else k


def case_id(k: str) -> str:
    toks = strip_key(k).split("|")
    return "|".join([toks[0]] + toks[2:])


def ready_time(base: dict):
    v = base.get("t_ready_s")
    if v is None:
        v = base.get("t_ready")
    return v


rows = []
for name in FILES:
    data = json.loads((ROOT / name).read_text(encoding="utf-8"))
    for r in data["results"]:
        base = r.get("base") or {}
        k = strip_key(r["key"])
        toks = k.split("|")
        r79 = r.get("r79") or {}
        wf = r79.get("warn_fault") or []
        rows.append(
            {
                "file": name,
                "key": k,
                "case": case_id(k),
                "level": r.get("level"),
                "seed_index": r.get("seed_index"),
                "seed_tok": toks[1],
                "family": toks[2] if len(toks) > 2 else "",
                "harness": r.get("harness"),
                "inner": r.get("inner"),
                "case_index": r.get("case_index"),
                "t_ready": ready_time(base),
                "t_done": base.get("t_done_s"),
                "final_phase": base.get("final_phase"),
                "pass": base.get("pass"),
                "n_stroke_end_fault": r79.get("n_stroke_end_fault"),
                "n_warn_fault": len(wf),
                "warn_fault_txt": json.dumps(wf)[:200],
                "error": r.get("error"),
            }
        )

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print("ok", len(rows))
