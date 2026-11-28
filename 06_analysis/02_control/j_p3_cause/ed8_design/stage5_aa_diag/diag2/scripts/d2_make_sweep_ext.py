"""Build ``jobs_sweep_ext.json``: the sweep shapes at offsets 0.0745 .. 0.0835 s (record only).

The offsets 0.0845 .. 0.1005 s of ``jobs_sweep.json`` put the sample before the step period at
+3 .. -13 ms from the lift (J1 shape); these ten more per shape reach +4 .. +13 ms, so the
requested "sample after the lift" side (+1 .. +10 ms) is covered. Only the offset differs.

Usage (python-dev):
  python.exe -I -B d2_make_sweep_ext.py <diag2 folder>
Refuses an existing file (exit 2).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

EXT_FIRST_OFFSET_S = 0.0745
EXT_STEP_S = 0.001
EXT_COUNT = 10


def main() -> int:
    folder = Path(sys.argv[1])
    target = folder / "jobs_sweep_ext.json"
    if target.exists():
        print("refusing to overwrite")
        return 2
    sweep = json.loads((folder / "jobs_sweep.json").read_text(encoding="utf-8"))
    first_per_shape = {}
    for entry in sweep:
        first_per_shape.setdefault(entry["label"].split("_")[0], entry)
    extended = []
    for shape, entry in first_per_shape.items():
        for index in range(EXT_COUNT):
            offset_s = round(EXT_FIRST_OFFSET_S + EXT_STEP_S * index, 4)
            job = copy.deepcopy(entry["job"])
            job["offset_s"] = offset_s
            extended.append({"label": f"{shape}_o{offset_s:.4f}", "base_label": entry["base_label"],
                             "offset_s": offset_s, "job": job})
    target.write_text(json.dumps(extended, indent=1), encoding="utf-8")
    print(len(extended))
    return 0


if __name__ == "__main__":
    sys.exit(main())
