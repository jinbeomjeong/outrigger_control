"""P-S9-10 check on recorded runs: longest lifted re-approach (``leg_reapproach_start:<leg>`` to
the next ``leg_reapproach_*`` end event of the same leg, or the run end) in every
``controller_events.json`` below the given folders.

Usage: ``python -I -X utf8 reapproach_durations.py <out.json> <folder>...``
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

EVENT = re.compile(r"t_s=([-0-9.e+]+), name='([^']*)'")


def main(argv: list[str]) -> int:
    out = Path(argv[0])
    rows = []
    names = collections.Counter()
    for folder in argv[1:]:
        for f in sorted(Path(folder).rglob("controller_events.json")):
            events = [EVENT.search(e) for e in json.loads(f.read_text("utf-8"))]
            events = [(float(m.group(1)), m.group(2)) for m in events if m]
            t_end = max((t for t, _ in events), default=0.0)
            r8 = f.parent / "r8_series.npz"
            if r8.exists():
                import numpy as np

                t_end = float(np.load(r8)["t"][-1])
            open_: dict[str, float] = {}
            runs = []
            for t, name in events:
                if "reapproach" not in name and "REAPPROACH" not in name:
                    continue
                kind, _, leg = name.partition(":")
                names[kind] += 1
                if kind == "leg_reapproach_start":
                    open_[leg] = t
                elif leg in open_ and kind != "leg_reapproach_deferred":
                    runs.append({"leg": leg, "start_s": open_[leg], "end_s": t, "end": kind,
                                 "duration_s": t - open_.pop(leg)})
            for leg, t0 in open_.items():
                runs.append({"leg": leg, "start_s": t0, "end_s": t_end, "end": "run_end",
                             "duration_s": t_end - t0})
            if runs:
                rows.append({"run": str(f.parent), "runs": runs,
                             "max_s": max(r["duration_s"] for r in runs)})
    rows.sort(key=lambda r: -r["max_s"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"event_kinds": dict(names), "rows": rows}, indent=1), "utf-8")
    n = sum(len(r["runs"]) for r in rows)
    print(f"runs with re-approach {len(rows)}, re-approaches {n}, kinds {dict(names)}")
    for r in rows[:8]:
        print(f"{r['max_s']:8.2f} s  {r['run']}  {[(x['leg'], round(x['duration_s'], 2), x['end']) for x in r['runs']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
