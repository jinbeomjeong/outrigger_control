"""Grid-768 frame (identifiers and V0 pass status only) for ed. 6 confirmation-stage sampling design.

stats-design-expert, 2026-11-23. Reads the stored c4g2_only grid files (V0 base arm of v5 criteria
section 10, committed 2026-11-05). Writes the run frame: one row per grid run with key fields,
run identifiers (offset, fast flag, pair, event label) and the stored V0 pass flag (the base arm's
own status, needed for the opportunity count of the pass->fail criterion). No ed. 5/6 results are
read. Output: argv[1]/s01_grid_frame.csv and s01_grid_summary.json. stdout: status only.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]


def label(v) -> str:
    if isinstance(v, dict):
        for k in ("name", "kind", "type", "label"):
            if k in v:
                return str(v[k])
        return "dict:" + ",".join(sorted(v)[:4])
    if isinstance(v, list):
        return "|".join(str(x) for x in v)
    return str(v)


def main() -> int:
    out_dir = Path(sys.argv[1])
    rows = []
    for fn in FILES:
        d = json.loads((GRID / fn).read_text(encoding="utf-8"))
        for job in d["results"]:
            runs = job["runs"]
            items = runs.items() if isinstance(runs, dict) else enumerate(runs)
            for rk, run in items:
                rows.append({"file": fn, "key": job["key"], "level": job["level"],
                             "fs_kN": job["fs_kN"], "timing": job["timing"], "leg": job["leg"],
                             "run_id": str(rk), "offset_s": run.get("offset_s"),
                             "fast": label(run.get("fast")), "pair": label(run.get("pair")),
                             "event": label(run.get("event")),
                             "phase_at_event": label(run.get("phase_at_event")),
                             "v0_pass": bool(run.get("pass")),
                             "sha": run.get("commands_sha256")})
    with (out_dir / "s01_grid_frame.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summ = {"n": len(rows), "n_v0_pass": sum(r["v0_pass"] for r in rows),
            "unique_sha": len({r["sha"] for r in rows}),
            "unique_key_run": len({(r["key"], r["run_id"], r["offset_s"]) for r in rows})}
    for f in ("level", "fs_kN", "timing", "leg", "fast", "pair", "event", "phase_at_event",
              "offset_s", "run_id"):
        c = defaultdict(lambda: [0, 0])
        for r in rows:
            c[str(r[f])][0] += 1
            c[str(r[f])][1] += int(r["v0_pass"])
        summ[f] = {k: {"n": v[0], "v0_pass": v[1]} for k, v in sorted(c.items())[:40]}
    (out_dir / "s01_grid_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print("ok", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
