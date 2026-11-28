"""Build the job lists of diagnosis 2 (record only).

Usage (python-dev):
  python.exe -I -B d2_make_jobs.py <diag2 folder>

``jobs_gyro.json``  the seven jobs of diagnosis 1 (``../diag_jobs.json``, same labels)
``jobs_sweep.json`` the J1 shape (FR, F_s 0, level, 30 mm / 0.04 s) and the J3 shape (FL,
                    F_s 2, level, 25 mm / 0.05 s) at offsets 0.0845 .. 0.1005 s in 1 ms steps
                    (2 x 17); only the offset differs from J1 / J3. Not key-file jobs.
Refuses files that exist (exit 2).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

SWEEP_FIRST_OFFSET_S = 0.0845
SWEEP_STEP_S = 0.001
SWEEP_COUNT = 17
SWEEP_BASES = {"J1shape": "J1_l179_FR_Fs0_level_30mm004_o0875",
               "J3shape": "J3_l173_FL_Fs2_level_25mm005_o0875"}


def main() -> int:
    folder = Path(sys.argv[1])
    targets = [folder / "jobs_gyro.json", folder / "jobs_sweep.json"]
    if any(path.exists() for path in targets):
        print("refusing to overwrite")
        return 2
    diag1 = json.loads((folder.parent / "diag_jobs.json").read_text(encoding="utf-8"))
    gyro_jobs = [{"label": e["label"], "purpose": e["purpose"], "job": e["job"],
                  "stored": e["stored"]} for e in diag1]
    by_label = {e["label"]: e for e in diag1}
    sweep = []
    for shape, label in SWEEP_BASES.items():
        for index in range(SWEEP_COUNT):
            offset_s = round(SWEEP_FIRST_OFFSET_S + SWEEP_STEP_S * index, 4)
            job = copy.deepcopy(by_label[label]["job"])
            job["offset_s"] = offset_s
            sweep.append({"label": f"{shape}_o{offset_s:.4f}", "base_label": label,
                          "offset_s": offset_s, "job": job})
    targets[0].write_text(json.dumps(gyro_jobs, indent=1), encoding="utf-8")
    targets[1].write_text(json.dumps(sweep, indent=1), encoding="utf-8")
    print(len(gyro_jobs), len(sweep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
