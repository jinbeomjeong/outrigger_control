"""Spec rev. 72 (366 correction): re-run the G8 / P-S8-28 harness runs whose recorded END stroke is within
``R70_RUNMAX_BAND_MM`` (default 10) of the 684.8 mm end-margin stroke, to get the run maximum
(``stroke_max_run_mm``) for ``r70_judge.py --runmax``. Pass-band runs only matter (a run already over 684.8 at the
end fails either way, it is re-run too for the record).

Inputs: r70 JSON files (keys "<r69 key>|<variant>"). Rows without a variant (r69 batch, project controller before
P-S8-28) are skipped: that controller is no longer the project one, so they are not re-run.

Usage (dynamics-dev): python -I r70_runmax_rerun.py <project_root> <out_json> <workers> <r70 json> [...]
Env: R70_AFFINITY (hex mask on the parent), R70_RUNMAX_BAND_MM.
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import r70_p28_screen as r70  # noqa: E402

OK_MM = 684.8


def main():
    band = float(os.environ.get("R70_RUNMAX_BAND_MM", "10"))
    keys = []
    for p in sys.argv[4:]:
        for r in json.loads(Path(p).read_text(encoding="utf-8"))["results"]:
            if "error" in r or "variant" not in r:
                continue
            if max(r["stroke_end_mm"]) >= OK_MM - band:
                keys.append(r["key"])
    keys = sorted(set(keys))
    print("re-run", len(keys), "runs")
    r70.set_parent_placement()
    t0 = time.perf_counter()
    with Pool(max(1, min(int(sys.argv[3]), len(keys)))) as pool:
        res = pool.map(r70.job, keys, chunksize=1)
    Path(sys.argv[2]).write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r70_runmax_rerun.py",
                                                      "band_mm": band, "inputs": sys.argv[4:], "n": len(keys),
                                                      "wall_s": round(time.perf_counter() - t0, 1)},
                                             "results": res}, indent=1, default=float), encoding="utf-8")
    for r in res:
        if "error" in r:
            print(r["key"], r["error"])
            continue
        print(r["key"], "end", max(r["stroke_end_mm"]), "run max", max(r["stroke_max_run_mm"]),
              "gate", r["gates"]["stroke_end"], r["cmd_sha256"])


if __name__ == "__main__":
    main()
