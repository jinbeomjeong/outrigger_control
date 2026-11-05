"""Spec C-5: the M1c port on the harness reproduces the stored M1c command hashes.

The stored rows (``pressure_review/m1c/{hash,r12,g4,main}.jsonl``) ran on the preset before the C4G2
switch, so run this file through ``05_tests/unit/pre_c4g2_preset_runner.py``. The off rows of
``hash.jsonl`` come first: if they differ, the preset or the harness changed and nothing else is
compared. Writes one JSON line per row and a summary to ``--out``.

Usage (dynamics-dev, project root):
  python -I -B 05_tests/unit/pre_c4g2_preset_runner.py \
      04_scripts/04_hydraulic/coupled/check_m1c_repro.py --out <file.json> [--workers N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path

for _name in ("MKL_THREADING_LAYER",):
    os.environ.setdefault(_name, "TBB")
for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STORED = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1c"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

VARIANTS = {"VN_c2_v1": ("VN", 1.0, 0.02), "BL_v1": ("BL", 1.0, 0.02),
            "VN_c2_v05": ("VN", 0.5, 0.02), "BL_v05": ("BL", 0.5, 0.02)}
"""``run_m1c.VARIANTS`` rows of spec C-5 (kind, volume scale, c_v)."""
OFFSETS_R12 = (0.0, 0.025, 0.05, 0.075)


def _stored(name: str) -> dict[str, str]:
    rows = {}
    for line in (STORED / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if "commands_sha256" in record:
            rows[_key(record["job"])] = record["commands_sha256"]
    return rows


def _key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k != "mask"}, sort_keys=True)


def _first_matching(stored: dict, **wanted) -> dict:
    for key in stored:
        job = json.loads(key)
        if all(job.get(name) == value for name, value in wanted.items()):
            return job
    raise KeyError(f"no stored row with {wanted}")


def build_jobs() -> tuple[list[dict], list[dict]]:
    """(off rows of hash.jsonl, the C-5 rows) with their stored hashes."""
    hash_rows, r12, g4, main = (_stored(name) for name in ("hash", "r12", "g4", "main"))
    off = [{"job": json.loads(key), "stored": value} for key, value in hash_rows.items()
           if json.loads(key)["variant"] == "OFF"]
    rows = [{"job": json.loads(key), "stored": value} for key, value in r12.items()
            if json.loads(key)["variant"] in VARIANTS]
    g4_wanted = ({"variant": "VN_c2_v1", "offset_s": 0.0}, {"variant": "BL_v1", "offset_s": 0.05})
    for wanted in g4_wanted:
        job = _first_matching(g4, **wanted)
        rows.append({"job": job, "stored": g4[_key(job)]})
    for case in ("S7", "R15"):
        job = _first_matching(main, case=case, variant="VN_c2_v1")
        rows.append({"job": job, "stored": main[_key(job)]})
    return off, rows


def _install_approach_scale(eps: float) -> None:
    """``run_m1c.run_one``: approach speed scale until the first touch (steady rows)."""
    import harness_flow
    import numpy as np

    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > 3000.0
        return delivered * (1.0 - eps) if not touched.any() else delivered

    harness_flow.FlowLimiter.limit = limit


def run_job(item: dict) -> dict:
    """One row in this worker (one row per worker: the patches stay in the process)."""
    import verdict_cases
    import verdict_runs
    from harness_flow import FlowSetting

    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions

    job = item["job"]
    if job.get("eps"):
        _install_approach_scale(float(job["eps"]))
    decision = job.get("decision")
    case = verdict_cases.resolve_case(job["case"], {job["case"]: decision} if decision else {})
    if job.get("offset_s") is not None:
        case = replace(case, twin=replace(case.twin, offset_s=float(job["offset_s"])))
    if job.get("twin"):
        case = replace(case, twin=replace(case.twin, **job["twin"]))
    options = None
    if job["variant"] != "OFF":
        kind, scale, c_v = VARIANTS[job["variant"]]
        options = HydraulicOptions(check_delay=CheckDelaySetting(kind, scale, c_v))
    t_start = time.perf_counter()
    result, _ = verdict_runs.execute(case, FlowSetting(is_enabled=False), decision,
                                     hydraulics=options)
    commands = result.get("commands_sha256")
    return {"job": job, "stored": item["stored"], "commands_sha256": commands,
            "equal": commands == item["stored"], "error": result.get("error"),
            "wall_s": round(time.perf_counter() - t_start, 1)}


def _run_all(items: list[dict], workers: int) -> list[dict]:
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        return list(pool.imap_unordered(run_job, items))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    off, rows = build_jobs()
    import verdict_runs

    verdict_runs.warm_numba_cache()
    off_results = _run_all(off, args.workers)
    report = {"off": off_results, "off_equal": all(r["equal"] for r in off_results)}
    if report["off_equal"]:
        report["rows"] = _run_all(rows, args.workers)
        report["rows_equal"] = sum(r["equal"] for r in report["rows"])
        report["rows_total"] = len(rows)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("off", "rows")}))


if __name__ == "__main__":
    main()
