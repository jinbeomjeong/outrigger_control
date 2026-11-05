"""Harness runs of M1b on R12 and the G4 width grid, flow limit off, current preset (C4G2 and K1 off).

Usage (dynamics-dev, activated): python -I run_m1b.py <r12|g4|hash> [--workers N] [--mask HEX]
Output: 06_analysis/03_hydraulic/coupled/pressure_review/m1b/<batch>.jsonl and, for R12, the 1 ms force record
m1b/series_r12/*.npz around the event. 10 Hz series go to $M1_SERIES_DIR. Deterministic.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from multiprocessing import get_context
from pathlib import Path

os.environ["MKL_THREADING_LAYER"] = "TBB"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMBA_NUM_THREADS"] = "1"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
TOUCH_DIR = ROOT / "04_scripts" / "03_control" / "touch_phase"
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1b"
SERIES_DIR = Path(os.environ.get("M1_SERIES_DIR", str(OUT / "series")))
DEFAULT_MASK = 0x00FF0000
for _path in (HERE, TOUCH_DIR, CODE, S9_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

OFFSETS_R12 = (0.0, 0.025, 0.05, 0.075)
VR = {"neutral": "vent", "refill": True, "rod_open_low": True, "rod_forward": False}
VN = {"neutral": "vent", "refill": False, "rod_open_low": False, "rod_forward": True}
BL = {"neutral": "block", "refill": False, "rod_open_low": False, "rod_forward": False}


def _b(kind: dict, c_v: float, scale: float, **extra) -> dict:
    return {**kind, "c_v": c_v, "volume_scale": scale, **extra}


M1B = {
    "VR_c2_v1": _b(VR, 0.02, 1.0), "VR_c2_v05": _b(VR, 0.02, 0.5), "VR_c1_v1": _b(VR, 0.01, 1.0), "VR_c1_v05": _b(VR, 0.01, 0.5),
    "VR_c5_v1": _b(VR, 0.05, 1.0), "VR_c5_v05": _b(VR, 0.05, 0.5),
    "VN_c2_v1": _b(VN, 0.02, 1.0), "VN_c2_v05": _b(VN, 0.02, 0.5), "VN_c1_v1": _b(VN, 0.01, 1.0), "VN_c1_v05": _b(VN, 0.01, 0.5),
    "VN_c5_v1": _b(VN, 0.05, 1.0), "VN_c5_v05": _b(VN, 0.05, 0.5),
    "BL_v1": _b(BL, 0.02, 1.0), "BL_v05": _b(BL, 0.02, 0.5),
    # separations and options, R12 only
    "VR_c2_v1_no4": _b({**VR, "rod_open_low": False}, 0.02, 1.0),
    "VR_rodonly": _b(VR, 0.02, 1.0, no_delay=True),
    "VR_c2_v1_o5": _b(VR, 0.02, 1.0, rod_release=True),
    "VN_c2_v1_o5": _b(VN, 0.02, 1.0, rod_release=True),
    "BL_v1_o5": _b(BL, 0.02, 1.0, rod_release=True),
    "VR_c2_v1_re": _b(VR, 0.02, 1.0, rod_early=True), "VR_c2_v05_re": _b(VR, 0.02, 0.5, rod_early=True),
    "VN_c2_v1_re": _b(VN, 0.02, 1.0, rod_early=True), "VN_c2_v05_re": _b(VN, 0.02, 0.5, rod_early=True),
}
OLD = {"V1": {"neutral": "vent", "volume_scale": 1.0}, "B1": {"neutral": "block", "volume_scale": 1.0}}
"""The first M1 rule (m1_plant, retract without the void), for the 1 ms R12 force record only."""
G4_VARIANTS = ("VR_c2_v1", "VN_c2_v1", "BL_v1", "VR_c2_v05", "VN_c2_v05", "BL_v05")


def batch_jobs(name: str) -> list[dict]:
    if name == "hash":
        return [{"case": "R12", "variant": "OFF", "eps": 0.0, "offset_s": o} for o in OFFSETS_R12] + \
            [{"case": "R12", "variant": "OFF", "eps": 0.0, "offset_s": o, "twin": {"level": "top", "leg": "RL", "fs_kN": 4.0}} for o in (0.0, 0.05)]
    if name == "r12":
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o} for v in ("V1", "B1", *M1B) for o in OFFSETS_R12]
    if name == "early":  # rod release at the rod check opening, after the first R12 result
        twins = [("top", leg, fs) for leg in ("FL", "FR", "RL", "RR") for fs in (0.0, 4.0, 8.0)]
        twins += [("bottom", leg, 4.0) for leg in ("FL", "RR")]
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o} for v in ("VR_c2_v1_re", "VR_c2_v05_re", "VN_c2_v1_re", "VN_c2_v05_re") for o in OFFSETS_R12] + \
            [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o, "twin": {"level": t[0], "leg": t[1], "fs_kN": t[2]}}
             for v in ("VR_c2_v1_re", "VN_c2_v1_re") for t in twins for o in (0.0, 0.05)]
    if name == "g4":
        twins = [("top", leg, fs) for leg in ("FL", "FR", "RL", "RR") for fs in (0.0, 4.0, 8.0)]
        twins += [("bottom", leg, 4.0) for leg in ("FL", "RR")]
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o, "twin": {"level": t[0], "leg": t[1], "fs_kN": t[2]}}
                for v in G4_VARIANTS for t in twins for o in (0.0, 0.05)]
    raise ValueError(name)


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k != "mask"}, sort_keys=True)


def run_one(job: dict) -> dict:
    t0 = time.perf_counter()
    try:
        from dataclasses import replace as dc_replace

        from run_m1 import command_stats, event_names, state_at_marks
        from run_touch_phase import _twist_vector, pin, summarize

        pin(job["mask"])
        import m1_plant
        import m1b_plant
        import numpy as np
        import s9_soil_closed_loop as soil
        import verdict_cases
        import verdict_runs
        from harness_flow import COLUMN, COLUMNS, FlowSetting

        variant = job["variant"]
        if variant in OLD:
            m1_plant.install(verdict_runs, m1_plant.M1Config(**OLD[variant]), soil.C_LOCK)
            last, state_name = m1_plant.LAST_PLANT, "m1"
        else:
            cfg = None if variant == "OFF" else m1b_plant.M1bConfig(**M1B[variant])
            m1b_plant.install(verdict_runs, cfg, soil.C_LOCK)
            last, state_name = m1b_plant.LAST_PLANT, "m1b"
        case = verdict_cases.resolve_case(job["case"], {})
        case = dc_replace(case, twin=dc_replace(case.twin, offset_s=float(job["offset_s"])))
        if job.get("twin"):
            case = dc_replace(case, twin=dc_replace(case.twin, **job["twin"]))
        result, series = verdict_runs.execute(case, FlowSetting(is_enabled=False), None)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"), "wall_s": time.perf_counter() - t0}
        plant = last[0]
        rows = plant.flow_limiter.rows()
        out = summarize(rows, COLUMNS, series["t"], series["phase"], _twist_vector())
        out["state_at"] = state_at_marks(rows, COLUMNS, series, _twist_vector())
        t_event = result.get("t_event_s")
        event_output = result.get("event_output") or {}
        event_output = {k: v for k, v in event_output.items() if k != "twist"}
        state = getattr(plant, state_name, None)
        out.update(job=job, wall_s=round(time.perf_counter() - t0, 1), commands_sha256=result["commands_sha256"],
                   harness_commands_sha256=result.get("harness_commands_sha256"), final_phase=result["final_phase"],
                   t_event_s=t_event, values=result["values"], event_output=event_output, event_names=event_names(result["events"]),
                   events=[e for e in result["events"] if e[1].startswith(("WARN", "FAULT", "leg_reapproach"))][:100],
                   command_stats=command_stats(series), m1=None if state is None else state.summary())
        if t_event is not None:
            t = rows[:, 0]
            window = (t >= t_event - 1.0) & (t <= t_event + 6.0)
            force = rows[window][:, [COLUMN[f"true_force_{leg}"] for leg in ("FL", "FR", "RL", "RR")]]
            after = rows[:, 0] >= t_event
            out["rr_min"] = {"leg_min_kN": np.round(rows[after][:, [COLUMN[f"true_force_{leg}"] for leg in ("FL", "FR", "RL", "RR")]].min(axis=0) / 1e3, 3).tolist()}
            if not job.get("twin"):
                OUT.joinpath("series_r12").mkdir(parents=True, exist_ok=True)
                np.savez_compressed(OUT / "series_r12" / f"R12_{variant}_{job['offset_s']}.npz",
                                    t=np.round(t[window] - t_event, 4), F=np.round(force, 1),
                                    u=np.round(rows[window][:, [COLUMN[f"u_{leg}"] for leg in ("FL", "FR", "RL", "RR")]], 7),
                                    v=np.round(rows[window][:, [COLUMN[f"v_{leg}"] for leg in ("FL", "FR", "RL", "RR")]], 7),
                                    oil=np.round(rows[window][:, [COLUMN[f"oil_force_{leg}"] for leg in ("FL", "FR", "RL", "RR")]], 1))
        SERIES_DIR.mkdir(parents=True, exist_ok=True)
        tag = f"{job['case']}_{variant}_{job['offset_s']}" + ("_" + "_".join(str(v) for v in job["twin"].values()) if job.get("twin") else "")
        np.savez_compressed(SERIES_DIR / f"{tag}.npz", t=series["t"], phase=series["phase"], command=series["command"], filtered_deg=series["filtered_deg"])
        return out
    except Exception as exc:  # keep the batch going, record the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:], "wall_s": time.perf_counter() - t0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=hex(DEFAULT_MASK))
    args = parser.parse_args()
    from run_touch_phase import pin

    mask = int(args.mask, 16)
    pin(mask)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.batch}.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            done.add(job_key(json.loads(line)["job"]))
    jobs = [j for j in batch_jobs(args.batch) if job_key(j) not in done]
    print(f"{args.batch}: {len(jobs)} runs to do, {len(done)} done", flush=True)
    for job in jobs:
        job["mask"] = mask
    import verdict_runs

    verdict_runs.warm_numba_cache()
    t0 = time.perf_counter()
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, path.open("a", encoding="utf-8") as handle:
        for count, rec in enumerate(pool.imap_unordered(run_one, jobs), 1):
            handle.write(json.dumps(rec, default=lambda v: v.item() if hasattr(v, "item") else str(v)) + "\n")
            handle.flush()
            job = rec["job"]
            if "error" in rec:
                state = "ERR " + rec["error"][:300]
            else:
                state = f"{rec['final_phase']} pass {rec['event_output'].get('pass')} min {rec.get('rr_min', {}).get('leg_min_kN')} {rec['commands_sha256'][:8]} {rec['wall_s']:.0f}s"
            print(f"{count}/{len(jobs)} {job['variant']} {job['offset_s']} {job.get('twin', '')}: {state}", flush=True)
    print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
