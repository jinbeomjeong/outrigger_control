"""v5 acceptance runs on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 3.3).

Batches: ``main`` (required 72 rows x 15 settings + L2 8 rows + regression 28 rows x 4 = 1,200),
``smoke`` (V0 R12 phase 0, compared with the golden hash), ``w2`` (spec W-2: L1 and L2 on the 8
rows), ``item8`` (criteria 13.1 (1): R6 / R8 / R9 x V0, VB x eps 1e-3, 3e-3 = 12; the eps 0 and
2e-3 phases are the regression rows of ``main``), ``overlap`` (criteria 13.3 (③): R12 G4 at the
VB reference time t_a + 0 / 0.025 / 0.05 / 0.075 s x V0, V3, VB = 12; t_a comes from one VB base
run first, stored in ``overlap_t_a.json`` and used by every setting; lines carry
``overlap_found``), ``pressure_only`` (criteria 13.4 (⑥): R12 4 offsets + G4 width grid 28 x V0,
V4, V5 with the pressure-only judge = 96; lines carry ``contact_judge`` and ``unit_status``, the
event output ``lower_bound_miss``; the combined pairs are the same rows of ``main``).
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
for _path in (HERE, S9_DIR, M1_DIR, ROOT / "03_src"):
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
ITEM8_ROWS = ("R6", "R8", "R9")
"""Criteria 13.1 (1): item 8 rows top / middle / bottom (rpB, F_s 0)."""
ITEM8_EXTRA_EPS = (1e-3, 3e-3)
"""Criteria 13.1: the phases the regression batch (eps 0, 2e-3) does not run."""
ITEM8_SETTINGS = ("V0", "VB")
OVERLAP_CASE = "R12"
"""Criteria 13.3 (③): the R12 G4 event (RR 11.5 mm / 2 s, F_s 4, top)."""
OVERLAP_SETTINGS = ("V0", "V3", "VB")
OVERLAP_OFFSETS = (0.0, 0.025, 0.05, 0.075)
OVERLAP_REFERENCE_SETTING = "VB"
OVERLAP_TIMING = "flow_saturation"
OVERLAP_REFERENCE_PATH = OUT_DIR / "overlap_t_a.json"
"""t_a of the VB reference run, written before the 12 runs and read by every worker (one
absolute time for V0, V3 and VB)."""
PRESSURE_ONLY_SETTINGS = ("V0", "V4", "V5")
"""Criteria 13.4 (⑥): V0, M1c VN x1, M1c BL x1; the combined pairs are the same rows of
``main``."""
PRESSURE_ONLY_ROW_COUNT = 32
"""R12 4 phases + G4 width grid 28: the first rows of :func:`required_rows`."""
PRESSURE_ONLY_JUDGE = "PRESSURE"
UNIT_STATUS = "below_criteria_reference_only"
"""Criteria 13.4: every ⑥ table carries this (M1c below its unit criteria, reference only)."""


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


def pressure_only_rows() -> list[dict]:
    """Criteria 13.4 rows: R12 at its 4 offsets and the G4 width grid (28)."""
    rows = required_rows()[:PRESSURE_ONLY_ROW_COUNT]
    if any(row["case"] != "R12" for row in rows):
        raise RuntimeError("the first required rows are no longer the R12 / G4 rows")
    return rows


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
    if name == "item8":
        return [{"case": case, "eps": eps, "setting": s}
                for s in ITEM8_SETTINGS for case in ITEM8_ROWS for eps in ITEM8_EXTRA_EPS]
    if name == "overlap":
        return [{"case": OVERLAP_CASE, "eps": 0.0, "offset_s": offset, "timing": OVERLAP_TIMING,
                 "setting": s} for s in OVERLAP_SETTINGS for offset in OVERLAP_OFFSETS]
    if name == "pressure_only":
        return [{**row, "contact": PRESSURE_ONLY_JUDGE, "setting": s}
                for s in PRESSURE_ONLY_SETTINGS for row in pressure_only_rows()]
    raise ValueError(f"unknown batch {name!r}")


RUNTIME_JOB_KEYS = ("mask", "t4h_dir")
"""Job entries ``main`` adds for the worker only (not part of the job identity)."""
T4H_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")
"""Criteria 9 T4h (control-expert B): the runs that write a T4h record."""


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k not in RUNTIME_JOB_KEYS},
                      sort_keys=True)


def t4h_file_name(job: dict) -> str:
    """``<row>_<phase>_<setting>.npz`` of a job (phase as in ``aggregate_v5``, file-safe)."""
    row = "R2ra" if job.get("decision") == "reanchor_on" else job["case"]
    if job.get("twin"):
        twin = job["twin"]
        phase = f"{twin['level']}-{twin['leg']}-Fs{twin['fs_kN']:g}-o{job.get('offset_s')}"
    elif job.get("offset_s") is not None:
        phase = f"o{job['offset_s']}"
    else:
        phase = f"e{job.get('eps', 0.0)}"
    if job.get("timing"):
        phase += f"-{job['timing']}"
    return f"{row}_{phase}_{job['setting']}.npz"


def _t4h_request(job: dict, flow, options) -> dict | None:
    """The T4h path and meta of a VB / LS job of a batch run (None otherwise)."""
    if job.get("t4h_dir") is None or job["setting"] not in T4H_SETTINGS:
        return None
    meta = {"job": {k: v for k, v in job.items() if k not in RUNTIME_JOB_KEYS},
            "flow_setting": flow.to_dict(),
            "hydraulic_options": None if options is None else options.to_dict()}
    return {"path": Path(job["t4h_dir"]) / t4h_file_name(job), "meta": meta}


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
    if job.get("timing") == OVERLAP_TIMING:
        t_a = overlap_reference()["t_a_s"]
        case = replace(case, twin=replace(case.twin, timing=OVERLAP_TIMING, event_time_s=t_a))
    return case, decision


def overlap_reference() -> dict:
    """The stored t_a record of the ``overlap`` batch.

    Raises:
        RuntimeError: No reference yet, or it has no t_a.
    """
    if not OVERLAP_REFERENCE_PATH.exists():
        raise RuntimeError(f"no t_a reference {OVERLAP_REFERENCE_PATH} (run_v5 overlap writes it)")
    reference = json.loads(OVERLAP_REFERENCE_PATH.read_text(encoding="utf-8"))
    if reference.get("t_a_s") is None:
        raise RuntimeError(f"t_a reference without a time: {reference.get('basis')}")
    return reference


def run_overlap_reference(job: dict) -> dict:
    """Worker: t_a of the VB base run of the overlap case (criteria 13.3)."""
    import verdict_cases
    import verdict_runs

    flow, options = options_of(job["setting"])
    case = verdict_cases.resolve_case(job["case"], {"R13": "ss_fs4"})
    return verdict_runs.flow_saturation_reference(case, flow, options)


def write_overlap_reference() -> dict:
    """Run the VB reference in one spawned worker (its plant patches stay there) and store t_a."""
    job = {"case": OVERLAP_CASE, "setting": OVERLAP_REFERENCE_SETTING}
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        reference = pool.apply(run_overlap_reference, (job,))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OVERLAP_REFERENCE_PATH.write_text(json.dumps(reference, indent=1), encoding="utf-8")
    return reference


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
        contact = job.get("contact")
        t4h = _t4h_request(job, flow, options)
        result, series = verdict_runs.execute(case, flow, decision, hydraulics=options,
                                              contact=contact, t4h=t4h)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"),
                    "wall_s": round(time.perf_counter() - t_start, 1)}
        events = result["events"]
        judge_record = {} if contact is None else {"contact_judge": result.get("contact_judge"),
                                                   "unit_status": UNIT_STATUS}
        return {"job": job, "wall_s": round(time.perf_counter() - t_start, 1),
                **judge_record,
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
                "hydraulics_record": result.get("hydraulics_record"),
                "review_record": result.get("review_record"),
                **{key: result[key] for key in ("overlap_found", "soil_stop_crawler",
                                                "lock_window_alignment") if key in result},
                **({} if t4h is None else {"t4h_file": t4h["path"].name})}
    except Exception as exc:  # the batch goes on; the line records the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}


def _done_keys(path: Path) -> set[str]:
    """Job keys of the finished runs in ``path``.

    Raises:
        RuntimeError: The file holds an M2 run of another M2 law (the job key has no law: it
            would count as done). Archive the file first (``*_m2r3`` precedent).
    """
    from outrigger_sim.hydraulics.rod_release import FLOW_LIMITED_LAW

    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        stored_law = (record.get("hydraulic_options") or {}).get("m2_law", FLOW_LIMITED_LAW)
        if stored_law != FLOW_LIMITED_LAW:
            raise RuntimeError(f"{path.name}: M2 law {stored_law!r} is not {FLOW_LIMITED_LAW!r}; "
                               "archive the file before running this law")
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
        job["t4h_dir"] = str(OUT_DIR / args.batch / "t4h")
    import verdict_runs

    verdict_runs.warm_numba_cache()
    if args.batch == "overlap" and not OVERLAP_REFERENCE_PATH.exists():
        reference = write_overlap_reference()
        print(f"overlap t_a {reference['t_a_s']} s ({reference['basis']})", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            path.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_one, todo), 1):
            for key in RUNTIME_JOB_KEYS:
                record["job"].pop(key, None)
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            handle.flush()
            state = record.get("error", "")[:200] or (
                f"{record['final_phase']} {record['commands_sha256'][:8]} {record['wall_s']}s")
            print(f"{count}/{len(todo)} {record['job']}: {state}", flush=True)


if __name__ == "__main__":
    main()
