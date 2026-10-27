"""Spec rev. 72/73 draft: P-S8-29 candidate acceptance on G6 (r73_p29_screen.py "g6" rows).

Per variant: r72_judge.py judgement (G6-1..7 with the decision-2 P3-8 demotion) on the re-keyed rows, plus the
P-S8-29 acceptance row READY <= READY_MAX_S (default 120 s), relaxed-DONE count and |D| at the relaxed DONE, and the
command hashes against the project rows (rev72 r72_g6*.json: unchanged list / changed list).

Usage: python -I r73_judge.py <out_dir> <tag> --runs <r73 json> [...] --base <r72 json> [...]
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r72_judge  # noqa: E402

READY_MAX_S = float(os.environ.get("R73_READY_MAX_S", "120"))


def main():
    out_dir, tag = Path(sys.argv[1]), sys.argv[2]
    args = {"--runs": [], "--base": []}
    cur = None
    for a in sys.argv[3:]:
        if a in args:
            cur = a
        else:
            args[cur].append(a)
    rows = []
    for p in args["--runs"]:
        rows += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    base = {}
    for p in args["--base"]:
        for r in json.loads(Path(p).read_text(encoding="utf-8"))["results"]:
            base[r["key"]] = r.get("commands_sha256")
    by_var = defaultdict(list)
    for r in rows:
        if r.get("harness") != "g6":
            continue
        rr = dict(r)
        rr["key"] = r["inner_key"]
        by_var[r["variant"]].append(rr)
    summary = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for var, rs in sorted(by_var.items()):
        tmp = out_dir / f"_{tag}_{var}_rows.json"
        tmp.write_text(json.dumps({"results": rs}, default=float), encoding="utf-8")
        jpath = out_dir / f"{tag}_{var}_judgement.json"
        argv = sys.argv
        sys.argv = ["r72_judge.py", str(jpath), str(tmp)]
        try:
            r72_judge.main()
        finally:
            sys.argv = argv
        tmp.unlink()
        j = json.loads(jpath.read_text(encoding="utf-8"))
        slow = [t["key"] for t in j["table"] if (t["t_ready_s"] or 1e9) > READY_MAX_S]
        relaxed = [(r["key"], (r.get("p29") or {}).get("relaxed_done")) for r in rs
                   if (r.get("p29") or {}).get("relaxed_done")]
        changed = [r["key"] for r in rs if r["key"] in base and base[r["key"]] != r.get("commands_sha256")]
        unchanged = [r["key"] for r in rs if r["key"] in base and base[r["key"]] == r.get("commands_sha256")]
        d_relax = [abs(v[0][1]) for _, v in relaxed]
        summary[var] = {"n": j["n"], "pass_G6": j["n_pass"], "gate_fail": j["gate_fail"],
                        "ready_over_max": len(slow), "ready_over_max_keys": slow,
                        "accept": sum(1 for t in j["table"] if not t["fails"] and (t["t_ready_s"] or 1e9) <= READY_MAX_S),
                        "n_relaxed": len(relaxed), "relaxed_D_kN": [min(d_relax), max(d_relax)] if d_relax else None,
                        "n_changed_vs_proj": len(changed), "n_unchanged_vs_proj": len(unchanged),
                        "unchanged_keys": unchanged,
                        "att_end_max_deg": max(max(abs(a) for a in (t["att_end_deg"] or [0])) for t in j["table"]),
                        "min_F_kN": min(t["min_F_kN"] for t in j["table"] if t["min_F_kN"] is not None),
                        "ready_s_max": max((t["t_ready_s"] or 0) for t in j["table"])}
    (out_dir / f"{tag}_summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    for var, s in summary.items():
        print(var, {k: v for k, v in s.items() if k not in ("ready_over_max_keys", "unchanged_keys")})
        print("   ready>max:", s["ready_over_max_keys"][:20])


if __name__ == "__main__":
    main()
