"""Harness runs of M1c on R12 and the G4 width grid, flow limit off, current preset (C4G2 and K1 off).

The results are reference data, not a verdict: the units missed their criteria (m1_criteria.md, M1c section, user decision).
Usage (dynamics-dev, activated): python -I run_m1c.py <hash|r12|g4> [--workers N] [--mask HEX]
Output: 06_analysis/03_hydraulic/coupled/pressure_review/m1c/<batch>.jsonl, series_r12/*.npz (1 ms force, delivered speed,
rod pressure; 10 Hz requested commands), series_g4/*.npz (10 Hz requested commands, rod pressure every 10 ms). Deterministic.
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
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1c"
DEFAULT_MASK = 0x00FF0000
for _path in (HERE, TOUCH_DIR, CODE, S9_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

OFFSETS_R12 = (0.0, 0.025, 0.05, 0.075)
LEGS = ("FL", "FR", "RL", "RR")


def _c(kind: str, c_v: float, scale: float, **extra) -> dict:
    return {"kind": kind, "c_v": c_v, "volume_scale": scale, **extra}


VARIANTS = {
    "VN_c1_v1": _c("VN", 0.01, 1.0), "VN_c1_v05": _c("VN", 0.01, 0.5), "VN_c2_v1": _c("VN", 0.02, 1.0), "VN_c2_v05": _c("VN", 0.02, 0.5),
    "VN_c5_v1": _c("VN", 0.05, 1.0), "VN_c5_v05": _c("VN", 0.05, 0.5),
    "BL_v1": _c("BL", 0.02, 1.0), "BL_v05": _c("BL", 0.02, 0.5),
    "VR_c2_v1": _c("VR", 0.02, 1.0), "VR_c2_v05": _c("VR", 0.02, 0.5),
    # sensitivities: E2 (rod release law, not reproduced on Hopsan), E4 (self opening), the instant release rule alone
    "VN_c2_v1_E2": _c("VN", 0.02, 1.0, e2=True), "BL_v1_E2": _c("BL", 0.02, 1.0, e2=True), "VR_c2_v1_E2": _c("VR", 0.02, 1.0, e2=True),
    "VN_c2_v1_E4": _c("VN", 0.02, 1.0, e4=True), "BL_v1_E4": _c("BL", 0.02, 1.0, e4=True), "VR_c2_v1_E4": _c("VR", 0.02, 1.0, e4=True),
    "OFF_E2": _c("VN", 0.02, 1.0, e2=True, no_delay=True),
}
G4_VARIANTS = ("VN_c2_v1", "VN_c2_v05", "BL_v1", "BL_v05", "VR_c2_v1")


def batch_jobs(name: str) -> list[dict]:
    if name == "hash":
        return [{"case": "R12", "variant": "OFF", "eps": 0.0, "offset_s": o} for o in OFFSETS_R12] + \
            [{"case": "R12", "variant": "OFF", "eps": 0.0, "offset_s": o, "twin": {"level": "top", "leg": "RL", "fs_kN": 4.0}} for o in (0.0, 0.05)]
    if name == "hash2":  # off path against the stored m1/hash.jsonl (steady) and R16 at its own offset
        return [{"case": c, "variant": "OFF", "eps": 0.0} for c in ("R4", "R9", "S1", "R16")]
    if name == "main":  # the rows of the M1 main grid other than R12, phases as there; OFF is reused from m1/main.jsonl
        from run_m1 import FOCAL, OTHER, _phase_jobs

        rows = [(c, False) for c in FOCAL if c != "R12"] + [(c, True) for c in OTHER]
        return [j for v in ("VN_c2_v1", "BL_v1", "VN_c2_v05", "BL_v05") for c, two in rows for j in _phase_jobs(c, v, two=two)]
    if name == "r12":
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o} for v in VARIANTS for o in OFFSETS_R12]
    if name == "g4":
        twins = [("top", leg, fs) for leg in LEGS for fs in (0.0, 4.0, 8.0)]
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
        import m1c_plant
        import numpy as np
        import s9_soil_closed_loop as soil
        import verdict_cases
        import verdict_runs
        from harness_flow import COLUMN, COLUMNS, FlowSetting

        variant = job["variant"]
        cfg = None if variant == "OFF" else m1c_plant.M1cConfig(**VARIANTS[variant])
        m1c_plant.install(verdict_runs, cfg, soil.C_LOCK)
        eps = float(job.get("eps", 0.0))
        if eps:  # approach speed scale until the first touch, as run_touch_phase and run_m1
            import harness_flow

            original_limit = harness_flow.FlowLimiter.limit

            def limit(self, t_s, u, oil_force_N):
                delivered = original_limit(self, t_s, u, oil_force_N)
                touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
                touched |= np.asarray(oil_force_N) > 3000.0
                return delivered * (1.0 - eps) if not touched.any() else delivered

            harness_flow.FlowLimiter.limit = limit
        decision = job.get("decision")
        case = verdict_cases.resolve_case(job["case"], {job["case"]: decision} if decision else {})
        if job.get("offset_s") is not None:
            case = dc_replace(case, twin=dc_replace(case.twin, offset_s=float(job["offset_s"])))
        if job.get("twin"):
            case = dc_replace(case, twin=dc_replace(case.twin, **job["twin"]))
        result, series = verdict_runs.execute(case, FlowSetting(is_enabled=False), decision)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"), "wall_s": time.perf_counter() - t0}
        plant = m1c_plant.LAST_PLANT[0]
        rows = plant.flow_limiter.rows()
        out = summarize(rows, COLUMNS, series["t"], series["phase"], _twist_vector())
        out["state_at"] = state_at_marks(rows, COLUMNS, series, _twist_vector())
        t_event = result.get("t_event_s")
        event_output = result.get("event_output") or {}
        event_output = {k: v for k, v in event_output.items() if k != "twist"}
        state = getattr(plant, "m1c", None)
        out.update(job=job, wall_s=round(time.perf_counter() - t0, 1), commands_sha256=result["commands_sha256"],
                   harness_commands_sha256=result.get("harness_commands_sha256"), final_phase=result["final_phase"],
                   t_event_s=t_event, values=result["values"], event_output=event_output, event_names=event_names(result["events"]),
                   events=[e for e in result["events"] if e[1].startswith(("WARN", "FAULT", "leg_reapproach"))][:100],
                   command_stats=command_stats(series), m1=None if state is None else state.summary(),
                   harness_class=result.get("harness_class"), failed_rows=result.get("failed_rows"),
                   probe_rounds=result.get("probe_rounds"),
                   p3_6=(result.get("rows") or {}).get("P3-6"), max_stroke_reading_mm=result.get("max_motor_stroke_reading_mm"))
        pr_t = np.array(plant.pr_log_t)
        pr = np.array(plant.pr_log)
        tag = f"{variant}_{job.get('offset_s')}" + ("_" + "_".join(str(v) for v in job["twin"].values()) if job.get("twin") else "")
        if t_event is not None and job.get("case") == "R12":
            t = rows[:, 0]
            window = (t >= t_event - 1.0) & (t <= t_event + 6.0)
            pick = lambda prefix, n=4: rows[:, [COLUMN[f"{prefix}_{leg}"] for leg in LEGS]]  # noqa: E731
            after = t >= t_event
            out["leg_min_kN"] = np.round(pick("true_force")[after].min(axis=0) / 1e3, 3).tolist()
            pr_on_rows = np.column_stack([np.interp(t, pr_t, pr[:, i]) for i in range(4)])
            if not job.get("twin"):
                OUT.joinpath("series_r12").mkdir(parents=True, exist_ok=True)
                np.savez_compressed(OUT / "series_r12" / f"R12_{tag}.npz", t=np.round(t[window] - t_event, 4), F=np.round(pick("true_force")[window], 1),
                                    delivered=np.round(pick("u")[window], 7), oil=np.round(pick("oil_force")[window], 1), p_r=np.round(pr_on_rows[window], 0),
                                    t10=np.round(series["t"] - t_event, 3), command=series["command"], phase=series["phase"], filtered_deg=series["filtered_deg"])
            else:
                OUT.joinpath("series_g4").mkdir(parents=True, exist_ok=True)
                sel = np.flatnonzero(window)[::10]
                np.savez_compressed(OUT / "series_g4" / f"G4_{tag}.npz", t=np.round(t[sel] - t_event, 3), p_r=np.round(pr_on_rows[sel], 0), F=np.round(pick("true_force")[sel], 1),
                                    t10=np.round(series["t"] - t_event, 3), command=series["command"], phase=series["phase"])
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
                state = f"{rec['final_phase']} pass {rec['event_output'].get('pass')} min {rec.get('leg_min_kN')} {rec['commands_sha256'][:8]} {rec['wall_s']:.0f}s"
            print(f"{count}/{len(jobs)} {job['case']} {job.get('decision', '')} {job['variant']} {job.get('eps')} {job.get('offset_s', '')} {job.get('twin', '')}: {state}", flush=True)
    print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
