"""Per-pad end sinkage and peak pad force of final-harness P3b runs (paper figure D points).

The final harness record ``06_analysis/02_control/s9/rev85/finB2_p0.json`` keeps READY, forces and
the command hash, but not the pad values figure D needs. This script reruns chosen ``p3b`` cases
exactly as finB2_p0 did (``s9_slope_fix_candidates.run_job``, suite ``p3b``, candidate ``current``
= the project R8 preset, settle hook ``p0``) and adds, read only:
    end_sinkage_mm      soil sinkage z per pad (FL, FR, RL, RR) at the run end (READY + 10 s)
    max_pad_normal_N    largest soil normal force per pad over the run (after every 1 ms chunk)
    done_count          DONE entries of the phase path
The hooks only read the plant, so the commands (and their hash) must equal the stored record;
``hash_matches_finB2_p0`` says whether they do.

Run in dynamics-dev (numba; the stored hashes are bit-exact only in the env that made them), with
MKL_THREADING_LAYER=TBB when the env is not activated:
    <dynamics-dev python> -I figD_harness_pads.py --out <json> [--ids "a;b"] [--workers N]
Default ids: the eight top / F_s 4 kN cases ``base|<G1,J1,J2,S1>|<A,B>|top|Fs4``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
S9_DIR = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(S9_DIR))

import s9_slope_fix_candidates as fix  # noqa: E402

SCRIPT_REL = "04_scripts/03_control/s9/evidence/figD_harness_pads.py"
STORED_RECORD_PATH = ROOT / "06_analysis" / "02_control" / "s9" / "rev85" / "finB2_p0.json"
DEFAULT_OUT_PATH = ROOT / "06_analysis" / "02_control" / "s9" / "rev85" / "evidence" / (
    "figD_harness_pads.json")
SUITE = "p3b"
CANDIDATE = "current"
SETTLE_HOOK = "p0"
SOILS = ("G1", "J1", "J2", "S1")
PAD_TYPES = ("A", "B")
DEFAULT_IDS = tuple(f"base|{soil}|{pad}|top|Fs4" for soil in SOILS for pad in PAD_TYPES)
MM_PER_M = 1000.0

_PAD_PEAK: dict[str, np.ndarray] = {}
_RUN_OUT: dict[str, dict] = {}


def _install_pad_hooks() -> None:
    """Wrap ``soil_floor`` (peak pad force) and ``run_case`` (keep its output); read only."""
    import s9_soil_closed_loop as sl

    if getattr(sl.soil_floor, "is_pad_hook", False):
        return
    original_soil_floor = sl.soil_floor
    original_run_case = sl.run_case

    def soil_floor_recorded(cl, plant):
        original_soil_floor(cl, plant)
        if plant.soil is not None:
            _PAD_PEAK["N"] = np.maximum(_PAD_PEAK["N"], plant.soil.force)

    def run_case_recorded(case):
        out = original_run_case(case)
        _RUN_OUT["out"] = out
        return out

    soil_floor_recorded.is_pad_hook = True
    sl.soil_floor = soil_floor_recorded
    sl.run_case = run_case_recorded


def count_done_entries(phase_path: list) -> int:
    """DONE entries in a ``run_case`` phase path [(t_s, "C2Phase.X"), ...]."""
    return sum(1 for _, phase in phase_path if str(phase).lower().endswith("done"))


def run_one(job: dict) -> dict:
    """Worker: one p3b case through ``fix.run_job`` with the pad hooks."""
    _install_pad_hooks()
    _PAD_PEAK["N"] = np.zeros(4)
    _RUN_OUT.clear()
    record = fix.run_job(job)
    out = _RUN_OUT.get("out") or {}
    sink_final_mm = out.get("sink_final_mm")
    return {
        "id": job["id"], "error": record.get("error"), "verdict": record.get("verdict"),
        "commands_sha256": record.get("hash"), "t_ready_s": record.get("t_ready_s"),
        "min_force_kN": record.get("min_force_kN"),
        "final_phase": record.get("final_phase"),
        "done_count": count_done_entries(out.get("phase_path") or []),
        "end_sinkage_mm": sink_final_mm,
        "max_pad_normal_N": [float(value) for value in _PAD_PEAK["N"]],
        "run_end_note": "plant state at READY + S9_HOLD_S (default 10 s) or FAULT",
        "wall_s": record.get("wall_s"),
    }


def stored_hashes() -> dict[str, str]:
    data = json.loads(STORED_RECORD_PATH.read_text(encoding="utf-8"))
    return {row["id"]: row.get("hash") for row in data["records"] if row.get("suite") == SUITE}


def _script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_jobs(ids: list[str]) -> list[dict]:
    """Jobs as finB2_p0 built them (``s9_slope_fix_candidates._run``).

    Raises:
        ValueError: an id is not a p3b case.
    """
    payloads = dict(fix.suite_cases(SUITE))
    unknown = [case_id for case_id in ids if case_id not in payloads]
    if unknown:
        raise ValueError(f"unknown p3b ids {unknown}")
    return [{"suite": SUITE, "id": case_id, "payload": payloads[case_id], "candidate": CANDIDATE,
             "params": {}} for case_id in ids]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--ids", default=";".join(DEFAULT_IDS), help="semicolon list of p3b ids")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    os.environ[fix.SETTLE_HOOK_ENV] = SETTLE_HOOK  # inherited by the pool workers
    ids = [case_id.strip() for case_id in args.ids.split(";") if case_id.strip()]
    jobs = build_jobs(ids)
    started_s = time.perf_counter()
    with Pool(max(1, min(args.workers, len(jobs)))) as pool:
        records = pool.map(run_one, jobs, chunksize=1)
    hashes = stored_hashes()
    for record in records:
        stored = hashes.get(record["id"])
        record["stored_commands_sha256"] = stored
        record["hash_matches_finB2_p0"] = stored is not None and stored == record[
            "commands_sha256"]
    meta = {"script": SCRIPT_REL, "script_sha256": _script_sha256(),
            "harness_sha256": fix.harness_sha256(), "suite": SUITE, "candidate": CANDIDATE,
            "settle_hook": SETTLE_HOOK, "stored_record": "06_analysis/02_control/s9/rev85/"
            "finB2_p0.json", "interpreter": sys.executable, "workers": args.workers,
            "wall_s": round(time.perf_counter() - started_s, 1),
            "units": {"end_sinkage_mm": "mm (soil z)", "max_pad_normal_N": "N"},
            "leg_order": ["FL", "FR", "RL", "RR"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"meta": meta, "records": records}, indent=1),
                        encoding="utf-8")
    for record in records:
        print(record["id"], record["verdict"], "hash_match", record["hash_matches_finB2_p0"],
              "ready", record["t_ready_s"], "done", record["done_count"], "sink",
              np.round(record["end_sinkage_mm"] or [], 2).tolist(), "peakN",
              np.round(record["max_pad_normal_N"]).tolist(), "error", record["error"])
    print("->", args.out)


if __name__ == "__main__":
    main()
