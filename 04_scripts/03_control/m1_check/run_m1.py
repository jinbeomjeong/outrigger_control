"""Harness runs of the M1 check-opening delay, flow limit off, current preset (C4G2 and K1 off).

Usage (dynamics-dev, activated): python -I run_m1.py <batch> [--workers N] [--mask HEX]
Output: 06_analysis/03_hydraulic/coupled/pressure_review/m1/<batch>.jsonl (one run per line, appended; runs
already in the file are skipped) and the 10 Hz series in --series-dir. Deterministic (no noise, no random numbers).
Phase: approach speed scale eps until the first touch (steady rows, run_touch_phase) or the event time offset.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from itertools import product
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
OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review" / "m1"
SERIES_DIR = Path(os.environ.get("M1_SERIES_DIR", str(OUT / "series")))
DEFAULT_MASK = 0x00FF0000
"""E cores 16..23 (instruction of this study)."""
for _path in (HERE, TOUCH_DIR, CODE, S9_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

VARIANTS = {
    "OFF": None,
    "ZERO": {"neutral": "vent", "volume_scale": 0.0},
    "V1": {"neutral": "vent", "volume_scale": 1.0},
    "V05": {"neutral": "vent", "volume_scale": 0.5},
    "B1": {"neutral": "block", "volume_scale": 1.0},
    "B05": {"neutral": "block", "volume_scale": 0.5},
    "VE1": {"neutral": "vent", "volume_scale": 1.0, "vent_fraction": 0.0},
    "V2": {"neutral": "vent", "volume_scale": 2.0},
    "B2": {"neutral": "block", "volume_scale": 2.0},
    "V1ext": {"neutral": "vent", "volume_scale": 1.0, "only_side": "extend"},
    "V1ret": {"neutral": "vent", "volume_scale": 1.0, "only_side": "retract"},
    "B1ext": {"neutral": "block", "volume_scale": 1.0, "only_side": "extend"},
    "B1ret": {"neutral": "block", "volume_scale": 1.0, "only_side": "retract"},
}
EPS_ALL = (0.0, 1e-3, 2e-3, 3e-3)
EPS_TWO = (0.0, 2e-3)
OFFSETS = {"R12": (0.0, 0.025, 0.05, 0.075), "R14": (0.0, 0.05), "R15": (0.05, 0.0), "R16": (0.05, 0.0, 0.025, 0.075)}
FOCAL = ("R2", "R2ra", "R3", "R4", "R12", "R16", "S1", "S2", "S4", "S5", "S7", "S8")
OTHER = ("R1", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R14", "R15", "S3")
"""R13 and S6 need a decision and stay out, as in run_touch_phase; R2ra is R2 with REANCHOR on (the Chrono row)."""


def _phase_jobs(case: str, variant: str, *, two: bool = False) -> list[dict]:
    base = {"case": "R2", "decision": "reanchor_on"} if case == "R2ra" else {"case": case}
    if case in OFFSETS:
        return [{**base, "variant": variant, "eps": 0.0, "offset_s": o} for o in OFFSETS[case]]
    return [{**base, "variant": variant, "eps": e} for e in (EPS_TWO if two else EPS_ALL)]


def _grid(variants) -> list[dict]:
    jobs = []
    for variant in variants:
        for case in FOCAL:
            jobs += _phase_jobs(case, variant)
        for case in OTHER:
            jobs += _phase_jobs(case, variant, two=True)
    return jobs


def batch_jobs(name: str) -> list[dict]:
    if name == "hash":
        return [{"case": c, "variant": v, "eps": 0.0} for c, v in product(("R4", "R9", "R16", "S1"), ("OFF", "ZERO"))]
    if name == "smoke":
        return [{"case": "R2", "variant": "V1", "eps": 0.0}, {"case": "S1", "variant": "V1", "eps": 0.0}]
    if name == "main":  # ordered: base and the widest setting first, so a stopped queue still answers
        return _grid(("OFF", "V1", "B1", "V05", "B05"))
    if name == "vent_rule":  # the literal rule "reset only when the law locks": a focal subset
        return [j for c in ("R2", "R2ra", "S1", "S7", "R16") for j in _phase_jobs(c, "VE1", two=True)]
    if name == "r12ve":  # the literal reset rule on the row that changed
        return [{"case": "R12", "variant": "VE1", "eps": 0.0, "offset_s": o} for o in OFFSETS["R12"]]
    if name == "side":  # cause separation on the slow sink row: extend side, retract side, phases of main
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o}
                for v in ("V1ext", "V1ret", "B1ext", "B1ret") for o in OFFSETS["R12"]]
    if name == "g4":  # how wide: slow sink G4 on every leg, F_s 0, 4, 8, top; bottom on two legs
        twins = [("top", leg, fs) for leg in ("FL", "FR", "RL", "RR") for fs in (0.0, 4.0, 8.0)]
        twins += [("bottom", leg, 4.0) for leg in ("FL", "RR")]
        return [{"case": "R12", "variant": v, "eps": 0.0, "offset_s": o, "twin": {"level": t[0], "leg": t[1], "fs_kN": t[2]}}
                for t in twins for v in ("OFF", "V1", "B1") for o in (0.0, 0.05)]
    if name == "overlay":  # with M1_C2_WT: C4G2 + K1 on, few rows
        return [j for v in ("OFF", "V1", "B1") for c in ("R2ra", "R4", "R9", "R16", "R12", "S1", "S7")
                for j in _phase_jobs(c, v, two=True)]
    if name == "large":  # double volume (air, hose): focal rows only
        return [j for v in ("V2", "B2") for c in ("R2", "R2ra", "R4", "S1", "S7", "R16", "R12") for j in _phase_jobs(c, v, two=True)]
    raise ValueError(name)


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k != "mask"}, sort_keys=True)


def command_stats(series: dict) -> dict:
    """Sign changes and starts of the 10 Hz command from the first LEVEL on (criteria sec. 4)."""
    import numpy as np

    phase = series["phase"].astype(str)
    command = series["command"]
    level = np.flatnonzero(phase == "level")
    if level.size == 0:
        return {"n_rev": 0, "n_rev_legs": [0, 0, 0, 0], "n_starts": [0, 0, 0, 0], "retract_periods": [0, 0, 0, 0]}
    u = command[level[0]:]
    n_rev, n_starts, n_retract = [], [], []
    for i in range(4):
        sign = np.sign(np.where(np.abs(u[:, i]) > 1e-6, u[:, i], 0.0))
        nonzero = sign[sign != 0.0]
        n_rev.append(int((nonzero[1:] != nonzero[:-1]).sum()))
        n_starts.append(int(((sign[1:] != 0.0) & (sign[:-1] == 0.0)).sum()))
        n_retract.append(int((sign < 0).sum()))
    return {"n_rev": int(sum(n_rev)), "n_rev_legs": n_rev, "n_starts": n_starts, "retract_periods": n_retract}


def state_at_marks(rows, columns, series, twist) -> dict:
    """True leg force, twist D = n^T F [kN], delivered stroke [mm], attitude [deg] before first DONE, first READY, end."""
    import numpy as np

    c = {str(name): i for i, name in enumerate(columns)}
    t = rows[:, 0]
    force = rows[:, [c[f"true_force_{leg}"] for leg in ("FL", "FR", "RL", "RR")]] / 1e3
    stroke = np.cumsum(rows[:, [c[f"v_{leg}"] for leg in ("FL", "FR", "RL", "RR")]] * 1e-3, axis=0) * 1e3
    attitude = np.degrees(rows[:, [c["roll"], c["pitch"]]])
    phase = series["phase"].astype(str)
    marks = {"end": float(t[-1])}
    for name in ("done", "ready"):
        hits = np.flatnonzero(phase == name)
        if hits.size:
            marks[name] = float(series["t"][hits[0]])
    out = {}
    for name, mark in marks.items():
        k = int(np.searchsorted(t, mark))
        window = slice(max(k - 400, 0), max(k, 1))
        mean_force = force[window].mean(axis=0)
        out[name] = {"t": round(mark, 2), "F": np.round(mean_force, 2).tolist(), "D": round(float(mean_force @ twist), 3),
                     "s": np.round(stroke[max(k - 1, 0)], 3).tolist(),
                     "att": np.round(attitude[window].mean(axis=0), 4).tolist()}
    return out


def event_names(events) -> dict:
    counts: dict = {}
    for _, name in events:
        key = name.split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def install_overlay() -> None:
    """M1_C2_WT set: C2 of the pinned checkout (C4G2, K1 options) with both options on in the preset.

    The package ``outrigger_sim`` is imported from the checkout first, so later path inserts of the harness files
    do not change where its modules resolve. Nothing happens without the variable.
    """
    root = os.environ.get("M1_C2_WT")
    if not root:
        return
    sys.path.insert(0, str(Path(root) / "03_src"))
    from outrigger_sim.control import c2

    if Path(root).resolve() not in Path(c2.__file__).resolve().parents:
        raise RuntimeError(f"c2 from {c2.__file__}")
    original = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *args, touch_twist_hold=True, reapproach_retrigger_two_samples=True, **kwargs):
        return original(self, *args, touch_twist_hold=touch_twist_hold,
                        reapproach_retrigger_two_samples=reapproach_retrigger_two_samples, **kwargs)

    c2.C2Config.with_10hz_d1 = with_10hz_d1


def run_one(job: dict) -> dict:
    t0 = time.perf_counter()
    try:
        install_overlay()
        from run_touch_phase import _twist_vector, pin, summarize

        pin(job["mask"])
        import numpy as np

        import harness_flow
        import m1_plant
        import s9_soil_closed_loop as soil
        import verdict_cases
        import verdict_runs
        from harness_flow import COLUMNS, FlowSetting

        eps = float(job["eps"])
        original_limit = harness_flow.FlowLimiter.limit

        def limit(self, t_s, u, oil_force_N):
            delivered = original_limit(self, t_s, u, oil_force_N)
            touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
            touched |= np.asarray(oil_force_N) > 3000.0
            if eps and not touched.any():
                delivered = delivered * (1.0 - eps)
            return delivered

        if eps:
            harness_flow.FlowLimiter.limit = limit
        settings = VARIANTS[job["variant"]]
        cfg = None if settings is None else m1_plant.M1Config(**settings)
        m1_plant.install(verdict_runs, cfg, soil.C_LOCK)
        decision = job.get("decision")
        case = verdict_cases.resolve_case(job["case"], {job["case"]: decision} if decision else {})
        if job.get("offset_s") is not None:
            from dataclasses import replace as dc_replace

            case = dc_replace(case, twin=dc_replace(case.twin, offset_s=float(job["offset_s"])))
        if job.get("twin"):
            from dataclasses import replace as dc_replace

            case = dc_replace(case, twin=dc_replace(case.twin, **job["twin"]))
        result, series = verdict_runs.execute(case, FlowSetting(is_enabled=False), decision)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"), "wall_s": time.perf_counter() - t0}
        plant = m1_plant.LAST_PLANT[0]
        rows = plant.flow_limiter.rows()
        out = summarize(rows, COLUMNS, series["t"], series["phase"], _twist_vector())
        out["state_at"] = state_at_marks(rows, COLUMNS, series, _twist_vector())
        rows_pass = None
        if result.get("rows"):
            rows_pass = {k: v.get("pass") for k, v in result["rows"].items() if isinstance(v, dict)}
        event_output = result.get("event_output")
        if event_output:
            event_output = {k: v for k, v in event_output.items() if k != "twist"}
        out.update(job=job, wall_s=round(time.perf_counter() - t0, 1),
                   commands_sha256=result["commands_sha256"],
                   harness_commands_sha256=result.get("harness_commands_sha256"),
                   final_phase=result["final_phase"], harness_class=result.get("harness_class"),
                   failed_rows=result.get("failed_rows"), rows_pass=rows_pass,
                   p3_6=(result.get("rows") or {}).get("P3-6"),
                   values=result["values"], event_output=event_output,
                   event_names=event_names(result["events"]),
                   events=[e for e in result["events"]
                           if e[1].startswith(("WARN", "FAULT", "INFO_LOC", "INFO_LIFT", "INFO_TWIST", "INFO_DIFF",
                                               "crawler_liftoff", "leg_reapproach_start", "probe"))][:200],
                   probe_rounds=result.get("probe_rounds"), timeline=result.get("timeline"),
                   command_stats=command_stats(series),
                   max_stroke_reading_mm=result.get("max_motor_stroke_reading_mm"),
                   m1=None if cfg is None else plant.m1.summary())
        SERIES_DIR.mkdir(parents=True, exist_ok=True)
        tag = "_".join(str(job.get(k, "")) for k in ("case", "decision", "variant", "eps", "offset_s"))
        if job.get("twin"):
            tag += "_" + "_".join(str(v) for v in job["twin"].values())
        if os.environ.get("M1_C2_WT"):
            tag += "_overlay"
        np.savez_compressed(SERIES_DIR / f"{tag}.npz", t=series["t"], phase=series["phase"], command=series["command"],
                            filtered_deg=series["filtered_deg"])
        return out
    except Exception as exc:  # keep the batch going, record the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:],
                "wall_s": time.perf_counter() - t0}


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
                state = (f"{rec['final_phase']} {rec.get('harness_class')} ready {rec['values']['times']['t_first_ready_s']} "
                         f"rev {rec['command_stats']['n_rev']} {rec['commands_sha256'][:8]} {rec['wall_s']:.0f}s")
            print(f"{count}/{len(jobs)} {job['case']} {job.get('decision', '')} {job['variant']} {job['eps']} "
                  f"{job.get('offset_s', '')}: {state}", flush=True)
    print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
