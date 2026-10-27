"""Spec rev. 72/73 draft: P-S8-29 on the G8 harness - command hashes against the project baseline.

Rows of r73_p29_screen.py ("g8|<r69 key>|<variant>") are matched to baseline rows by the r69 key (baseline JSON of
r70_p28_screen.py: key "<r69 key>|<variant>", any variant name). A changed run is attributed to P-S8-29 when its
record shows a relaxed DONE (``p29.relaxed_done``); a changed run without one is listed as "unexplained".
Also: acceptance rows of the changed runs (r70_judge-style gates: FAULT 0, no lift, D8, READY, stroke, attitude).

Usage: python -I r73_g8_compare.py <out_json> --runs <r73 json> [...] --base <r70-style json> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    out = Path(sys.argv[1])
    args = {"--runs": [], "--base": []}
    cur = None
    for a in sys.argv[2:]:
        if a in args:
            cur = a
        else:
            args[cur].append(a)
    base = {}
    for p in args["--base"]:
        for r in json.loads(Path(p).read_text(encoding="utf-8"))["results"]:
            if "error" not in r:
                base[r.get("r69_key") or r["key"].rsplit("|", 1)[0]] = r
    rows = []
    for p in args["--runs"]:
        rows += [r for r in json.loads(Path(p).read_text(encoding="utf-8"))["results"] if r.get("harness") == "g8"]
    same, changed, unexplained, missing, errors = [], [], [], [], []
    for r in rows:
        if "error" in r:
            errors.append(r["key"])
            continue
        b = base.get(r["inner_key"])
        if b is None:
            missing.append(r["inner_key"])
            continue
        if b["cmd_sha256"] == r["cmd_sha256"]:
            same.append(r["inner_key"])
            continue
        rel = (r.get("p29") or {}).get("relaxed_done")
        row = {"key": r["inner_key"], "relaxed_done": rel, "gates": r["gates"], "pass": r["pass"],
               "t_ready_base": b.get("t_ready"), "t_ready": r.get("t_ready"),
               "D8_min_base": min(b["min_F_after_liftoff_kN"].values()) if b.get("min_F_after_liftoff_kN") else None,
               "D8_min": min(r["min_F_after_liftoff_kN"].values()) if r.get("min_F_after_liftoff_kN") else None,
               "att_end": r.get("att_end_deg")}
        (changed if rel else unexplained).append(row)
    res = {"script": "04_scripts/03_control/s8/r73_g8_compare.py", "inputs": args, "n": len(rows),
           "n_same": len(same), "n_changed_relaxed": len(changed), "n_unexplained": len(unexplained),
           "missing": missing, "errors": errors, "changed": changed, "unexplained": unexplained,
           "changed_fail": [c["key"] for c in changed + unexplained if not all(c["gates"].values())]}
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print({k: res[k] for k in ("n", "n_same", "n_changed_relaxed", "n_unexplained", "changed_fail")},
          "missing", len(missing), "errors", errors)
    for c in changed + unexplained:
        print(c["key"], "relaxed", c["relaxed_done"], "ready", c["t_ready_base"], "->", c["t_ready"], "D8",
              c["D8_min_base"], "->", c["D8_min"], "pass", c["pass"])


if __name__ == "__main__":
    main()
