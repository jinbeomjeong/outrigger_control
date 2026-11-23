"""Ed. 6 confirmation stage (6.3 (na)): draft grid-768 extraction, one offset per cluster
(stats-design-expert, 2026-11-23, design draft - the main session fixes the seed at seal).

Rule (proposal, Q6-4):
  1. Frame = stored V0 grid (touch_phase/acceptance/c4g2_only/grid, files r67_main, r67_top,
     r69_bottom, r69_top; v5_criteria.md 10 V0 pair). Runs are identified by
     (level, fs_kN, timing, leg, event, offset_s); exact duplicates (same identifier in two files)
     are kept once, preferring the file listed later (r67_top over r67_main).
  2. Cluster = (level, fs_kN, timing, leg, event): 192 clusters (48 with 2 offsets, 144 with 4).
  3. In each cluster choose one offset uniformly with numpy default_rng(SEED) in sorted cluster
     order, among offsets whose stored V0 run passed (pass->fail opportunity); if none passed,
     among all offsets (the run still checks new FAULT).
Only identifiers and the stored V0 pass flag are read. Writes s50_grid_sample.csv and
s50_grid_sample.json next to this file. stdout: status only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GRID = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance"
            r"\c4g2_only\grid")
FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
SEED = 20261123


def event_name(ev) -> str:
    if isinstance(ev, dict):
        for k in ("name", "kind", "type", "label"):
            if k in ev:
                return str(ev[k])
    return str(ev)


def main() -> int:
    runs = {}
    for fn in FILES:
        d = json.loads((GRID / fn).read_text(encoding="utf-8"))
        for job in d["results"]:
            items = job["runs"].items() if isinstance(job["runs"], dict) else enumerate(job["runs"])
            for rk, run in items:
                ident = (job["level"], float(job["fs_kN"]), job["timing"], job["leg"],
                         event_name(run.get("event")), float(run["offset_s"]))
                runs[ident] = {"file": fn, "key": job["key"], "run_id": str(rk),
                               "v0_pass": bool(run.get("pass")),
                               "v0_commands_sha256": run.get("commands_sha256")}
    clusters = defaultdict(list)
    for ident in sorted(runs):
        clusters[ident[:5]].append(ident)
    rng = np.random.default_rng(SEED)
    rows = []
    for cl in sorted(clusters):
        members = clusters[cl]
        passed = [m for m in members if runs[m]["v0_pass"]]
        pool = passed if passed else members
        pick = pool[int(rng.integers(len(pool)))]
        r = runs[pick]
        rows.append({"level": cl[0], "fs_kN": cl[1], "timing": cl[2], "leg": cl[3],
                     "event": cl[4], "offset_s": pick[5], "n_offsets": len(members),
                     "n_v0_pass_offsets": len(passed), "v0_pass": r["v0_pass"],
                     "file": r["file"], "key": r["key"], "run_id": r["run_id"],
                     "v0_commands_sha256": r["v0_commands_sha256"]})
    out_csv = HERE / "s50_grid_sample.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summ = {"seed": SEED, "n_unique_runs": len(runs), "n_clusters": len(clusters),
            "n_selected": len(rows), "n_selected_v0_pass": sum(r["v0_pass"] for r in rows),
            "n_clusters_no_v0_pass": sum(1 for r in rows if r["n_v0_pass_offsets"] == 0),
            "by_event": {}, "csv_sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest()}
    for r in rows:
        e = summ["by_event"].setdefault(r["event"], {"n": 0, "v0_pass": 0})
        e["n"] += 1
        e["v0_pass"] += int(r["v0_pass"])
    (HERE / "s50_grid_sample.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    ok = len(runs) == 672 and len(clusters) == 192
    print("ok" if ok else "frame_mismatch", len(runs), len(clusters))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
