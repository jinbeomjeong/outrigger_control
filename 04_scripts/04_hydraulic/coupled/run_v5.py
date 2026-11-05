"""v5 acceptance runs on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 3.3).

Batches: ``main`` (required 72 rows x 15 settings + L2 8 rows + regression 28 rows x 4 = 1,200),
``smoke`` (V0 R12 phase 0, compared with the golden hash), ``w2`` (spec W-2: L1 and L2 on the 8
rows).
One JSON line per run in ``06_analysis/03_hydraulic/coupled/v5/<batch>.jsonl`` (appended; runs
already in the file are skipped). Each run has its own spawned worker (``maxtasksperchild=1``): the
harness patches stay in the process. Deterministic (no noise). Values only; the verdict is
``v5_criteria.md``.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/run_v5.py <batch> [--workers N] [--mask HEX] [--list]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path

for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
GOLDEN_DIR = OUT_DIR / "golden_off"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
M1_DIR = ROOT / "04_scripts" / "03_control" / "m1_check"
for _path in (HERE, S9_DIR, M1_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

ETA_V = 0.85
OVERLAP_RATIO, CLOSING_DELAY_S = 0.02, 0.05
EPS_ALL = (0.0, 1e-3, 2e-3, 3e-3)
EPS_TWO = (0.0, 2e-3)
OFFSETS = {"R12": (0.0, 0.025, 0.05, 0.075), "R14": (0.0, 0.05), "R15": (0.05, 0.0),
           "R16": (0.05, 0.0, 0.025, 0.075)}
"""``run_m1.OFFSETS`` (spec 3.3 rows)."""
G4_TWINS = ([("top", leg, fs) for leg in ("FL", "FR", "RL", "RR") for fs in (0.0, 4.0, 8.0)]
            + [("bottom", leg, 4.0) for leg in ("FL", "RR")])
G4_OFFSETS = (0.0, 0.05)
REQUIRED_STEADY_FOUR = ("S1", "S4", "S5", "S7", "S8", "R2", "R2ra", "R7")
REGRESSION_TWO = ("R1", "R5", "R6", "R8", "R9", "R10", "R11", "S3")
REGRESSION_FOUR = ("R3", "R4", "S2")
L2_ROWS = ("R12", "R14", "R16", "S1", "S7", "R2", "R7", "S8")
"""Spec 3.3 L2 (W-2): these rows at their first phase."""
REQUIRED_SETTINGS = ("V0", "V1", "V2", "V3", "L1", "VB", "V4", "V5", "V6", "V7", "V8",
                     "LS1", "LS2", "LS3", "LS4")
REGRESSION_SETTINGS = ("V0", "VB", "V4", "V5")


def _lc(ratio: float = OVERLAP_RATIO, delay_s: float = CLOSING_DELAY_S) -> dict:
    return {"overlap_ratio": ratio, "closing_delay_s": delay_s}


def _vn(scale: float) -> dict:
    return {"kind": "VN", "volume_scale": scale, "c_v": 0.02}


def _bl(scale: float) -> dict:
    return {"kind": "BL", "volume_scale": scale, "c_v": 0.02}


_M2 = {"rod_release_force": True}
_VB = {**_M2, "lock_closure": _lc(), "lock_window_follows_plant": True}
SETTINGS: dict[str, tuple[bool, dict]] = {
    "V0": (False, {}),
    "V1": (False, _M2),
    "V2": (True, {}),
    "V3": (True, _M2),
    "L1": (False, {"lock_closure": _lc()}),
    "L2": (False, {"lock_closure": _lc(), "lock_window_follows_plant": True}),
    "VB": (True, _VB),
    "V4": (True, {**_M2, "check_delay": _vn(1.0)}),
    "V5": (True, {**_M2, "check_delay": _bl(1.0)}),
    "V6": (True, {**_M2, "check_delay": _vn(0.5)}),
    "V7": (True, {**_M2, "check_delay": _bl(0.5)}),
    "V8": (True, {**_VB, "check_delay": _vn(1.0)}),
    "LS1": (True, {**_VB, "lock_closure": _lc(0.01, 0.05)}),
    "LS2": (True, {**_VB, "lock_closure": _lc(0.05, 0.05)}),
    "LS3": (True, {**_VB, "lock_closure": _lc(0.02, 0.02)}),
    "LS4": (True, {**_VB, "lock_closure": _lc(0.02, 0.10)}),
}
"""Spec 3.3: (flow limit at eta_v 0.85, plant options as ``HydraulicOptions.to_dict`` keys)."""


def _phase_jobs(case: str, *, two: bool = False) -> list[dict]:
    base = {"case": "R2", "decision": "reanchor_on"} if case == "R2ra" else {"case": case}
    if case in OFFSETS:
        return [{**base, "eps": 0.0, "offset_s": offset} for offset in OFFSETS[case]]
    return [{**base, "eps": eps} for eps in (EPS_TWO if two else EPS_ALL)]


def required_rows() -> list[dict]:
    rows = _phase_jobs("R12")
    rows += [{"case": "R12", "eps": 0.0, "offset_s": offset,
              "twin": {"level": level, "leg": leg, "fs_kN": fs}}
             for level, leg, fs in G4_TWINS for offset in G4_OFFSETS]
    for case in ("R14", "R15", "R16", *REQUIRED_STEADY_FOUR):
        rows += _phase_jobs(case)
    return rows


def regression_rows() -> list[dict]:
    rows = [job for case in REGRESSION_TWO for job in _phase_jobs(case, two=True)]
    return rows + [job for case in REGRESSION_FOUR for job in _phase_jobs(case)]


def l2_rows() -> list[dict]:
    return [_phase_jobs(case)[0] for case in L2_ROWS]


def batch_jobs(name: str) -> list[dict]:
    if name == "main":
        jobs = [{**row, "setting": s} for s in REQUIRED_SETTINGS for row in required_rows()]
        jobs += [{**row, "setting": "L2"} for row in l2_rows()]
        return jobs + [{**row, "setting": s} for s in REGRESSION_SETTINGS
                       for row in regression_rows()]
    if name == "smoke":
        return [{**_phase_jobs("R12")[0], "setting": "V0"}]
    if name == "w2":
        return [{**row, "setting": s} for s in ("L1", "L2") for row in l2_rows()]
    raise ValueError(f"unknown batch {name!r}")


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k != "mask"}, sort_keys=True)


def _install_approach_scale(eps: float) -> None:
    """``run_m1``: approach speed scale until the first touch (the phase of the steady rows)."""
    import harness_flow
    import numpy as np

    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > 3000.0
        return delivered * (1.0 - eps) if not touched.any() else delivered

    harness_flow.FlowLimiter.limit = limit


def _case_of(job: dict):
    import verdict_cases

    decision = job.get("decision")
    decisions = {"R13": "ss_fs4"} | ({job["case"]: decision} if decision else {})
    case = verdict_cases.resolve_case(job["case"], decisions)
    if job.get("offset_s") is not None:
        case = replace(case, twin=replace(case.twin, offset_s=float(job["offset_s"])))
    if job.get("twin"):
        case = replace(case, twin=replace(case.twin, **job["twin"]))
    return case, decision


def options_of(setting: str):
    """(``FlowSetting``, ``HydraulicOptions`` or None) of a setting name."""
    from harness_flow import FlowSetting

    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    is_flow_on, plant = SETTINGS[setting]
    flow = FlowSetting(is_enabled=True, eta_v=ETA_V) if is_flow_on else FlowSetting(
        is_enabled=False)
    return flow, (HydraulicOptions.from_dict(plant) if plant else None)


def run_one(job: dict) -> dict:
    """One run in this worker; the record line."""
    t_start = time.perf_counter()
    try:
        import verdict_runs
        from run_m1 import command_stats, event_names

        if job.get("mask") is not None:
            import s9_soil_slope as slope

            slope.set_parent_affinity(int(job["mask"]))
        if job.get("eps"):
            _install_approach_scale(float(job["eps"]))
        flow, options = options_of(job["setting"])
        case, decision = _case_of(job)
        result, series = verdict_runs.execute(case, flow, decision, hydraulics=options)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"),
                    "wall_s": round(time.perf_counter() - t_start, 1)}
        events = result["events"]
        return {"job": job, "wall_s": round(time.perf_counter() - t_start, 1),
                "commands_sha256": result["commands_sha256"],
                "final_phase": result["final_phase"], "values": result["values"],
                "t_event_s": result.get("t_event_s"), "event_output": {
                    k: v for k, v in (result.get("event_output") or {}).items() if k != "twist"},
                "event_names": event_names(events),
                "events": [e for e in events
                           if e[1].startswith(("WARN", "FAULT", "INFO_ROD"))][:200],
                "command_stats": command_stats(series),
                "harness_class": result.get("harness_class"),
                "hydraulic_options": result.get("hydraulic_options"),
                "hydraulics_record": result.get("hydraulics_record")}
    except Exception as exc:  # the batch goes on; the line records the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}


def _done_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if "error" not in record:
            done.add(job_key(record["job"]))
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    jobs = batch_jobs(args.batch)
    path = OUT_DIR / f"{args.batch}.jsonl"
    done = _done_keys(path)
    todo = [job for job in jobs if job_key(job) not in done]
    print(f"{args.batch}: {len(jobs)} runs, {len(todo)} to do", flush=True)
    if args.list:
        return
    mask = None if args.mask is None else int(args.mask, 16)
    for job in todo:
        job["mask"] = mask
    import verdict_runs

    verdict_runs.warm_numba_cache()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            path.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_one, todo), 1):
            record["job"].pop("mask", None)
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            handle.flush()
            state = record.get("error", "")[:200] or (
                f"{record['final_phase']} {record['commands_sha256'][:8]} {record['wall_s']}s")
            print(f"{count}/{len(todo)} {record['job']}: {state}", flush=True)


if __name__ == "__main__":
    main()
