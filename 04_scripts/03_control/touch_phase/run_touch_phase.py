"""Harness runs of the TOUCH phase candidates, flow limit off (a phase sweep per candidate).

Phase: the delivered approach speed is scaled by (1 - eps) until the first leg touches, which moves
the contact time by about eps x 25 s against the 10 Hz controller and changes nothing else
(dynamics-expert ``sweep.py``, 2026-11-04). Gaps: floor offsets per leg (+ = lower floor).

Usage (dynamics-dev): python -I run_touch_phase.py <batch> [--workers N] [--mask HEX]
Output: 06_analysis/02_control/touch_phase/<batch>.jsonl, one run per line, appended as they end;
runs already in the file are skipped. Deterministic (no noise, no random numbers).
"""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
import traceback
from ctypes import wintypes
from itertools import product
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
OUT = ROOT / "06_analysis" / "02_control" / "touch_phase"
DEFAULT_MASK = 0x0F000000
"""E cores 24..27: the 2026-11-04 instruction allows at most four E cores."""
LEGS = ("FL", "FR", "RL", "RR")
TOUCH_N = 3000.0
for _path in (HERE, CODE, S9_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

EPS8 = (0.0, 2.5e-4, 5e-4, 1e-3, 1.5e-3, 2e-3, 3e-3, 4e-3)
EPS4 = (0.0, 1e-3, 2e-3, 3e-3)
OFFSETS8 = (0.0, 0.0125, 0.025, 0.0375, 0.05, 0.0625, 0.075, 0.0875)
GAPS = {"none": None,
        "mirror2": (-2e-3, 2e-3, -2e-3, 2e-3),
        "asym2": (2e-3, -2e-3, 2e-3, -2e-3),
        "asym06": (0.6e-3, -0.6e-3, 0.6e-3, -0.6e-3),
        "twist2": (2e-3, -2e-3, -2e-3, 2e-3)}
ALL_CASES = tuple(f"R{i}" for i in range(1, 13)) + ("R14", "R15", "R16", "S1", "S2", "S3", "S4", "S5", "S7", "S8")


def _jobs(cases, cands, gaps, eps, **extra) -> list[dict]:
    return [{"case": c, "cand": k, "gap": g, "eps": e, **extra}
            for c, k, g, e in product(cases, cands, gaps, eps)]


def batch_jobs(name: str) -> list[dict]:
    if name in ("rows_C4", "bias_C4", "full_C4"):
        return []  # C4 alone was dropped for C4G1 after screen2
    if name in ("hash", "hash2"):  # hash2: the same check on the final wrapper code
        return _jobs(("R4", "R9", "R16", "S1"), ("OFF",), ("none",), (0.0,))
    if name == "screen":
        cands = (None, "A1", "A2", "B1", "B2", "C1", "C3", "D1", "F1")
        return _jobs(("R9",), cands, ("none", "mirror2"), EPS8)
    if name == "evphase":  # event phase sweep: event start + offset, on the 10 Hz grid and between
        offsets = (0.0, 0.0125, 0.025, 0.0375, 0.05, 0.0625, 0.075, 0.0875)
        return [{"case": "R12", "cand": None, "gap": "none", "eps": 0.0, "offset_s": o} for o in offsets] + \
            [{"case": "R16", "cand": None, "gap": "mirror2", "eps": e, "offset_s": 0.05} for e in EPS8]
    if name == "extra":  # R2 with the stored decision, soil rows over phases (LOC revoke sensitivity)
        return ([{"case": "R2", "cand": "C4G1", "gap": "none", "eps": 0.0, "decision": "reanchor_on"}]
                + _jobs(("S7", "S1"), (None, "C4G1"), ("none",), (1e-3, 2e-3, 3e-3)))
    if name == "r16pat":  # re-approach sequence behind the RL minimum of the mirror gap
        return _jobs(("R16",), (None, "C4G1"), ("mirror2",), (0.0, 1e-3))
    if name == "g2":  # twist-based ramp rule: symmetric rows keep their hash, slope rows keep the gain
        return (_jobs(("R1", "R10", "R11", "R3", "R12", "R16", "R14", "S2", "S3"), ("C6",), ("none",), (0.0,))
                + _jobs(("R9",), ("C6",), ("none", "mirror2"), EPS8) + _jobs(("R4",), ("C6",), ("none",), EPS8))
    if name == "kglobal":  # two samples on every start: the sink response price
        return ([{"case": "R12", "cand": "K9", "gap": "none", "eps": 0.0, "offset_s": o} for o in OFFSETS8]
                + [{"case": "R16", "cand": "K9", "gap": "mirror2", "eps": 0.0, "offset_s": o} for o in OFFSETS8[::2]])
    if name == "hash4":
        return _jobs(("R12", "R16", "R9", "S1"), ("OFF",), ("none",), (0.0,))
    if name == "kextra":  # R2 with the stored decision, soil rows over phases
        return ([{"case": "R2", "cand": "C4G1K1", "gap": "none", "eps": 0.0, "decision": "reanchor_on"}]
                + _jobs(("S7", "S1", "S2"), ("C4G1K1",), ("none",), (1e-3, 2e-3, 3e-3)))
    if name == "kest":  # load estimates on the re-approach watch, mirror-gap R16, the four corners
        return [{"case": "R16", "cand": c, "gap": "mirror2", "eps": 0.0, "offset_s": 0.05, "log_estimates": True}
                for c in ("OFF", "K1", "C4G1", "C4G1K1")]
    if name == "hash3":
        return _jobs(("R12", "R16", "S1"), ("OFF",), ("none",), (0.0,))
    if name.startswith("kpass1"):  # re-approach rule x TOUCH candidate, event phase sweep
        cands = (None, "K1", "K7", "K2", "C4G1", "C4G1K1", "C4G1K7", "C4G1K2")
        return [{"case": "R16", "cand": c, "gap": "mirror2", "eps": 0.0, "offset_s": o}
                for c in cands for o in OFFSETS8]
    if name.startswith("kpass2_"):  # kpass2_K7: the other event rows, the plain gap, TOUCH phases
        rule = name.split("_", 1)[1]
        cands = (None, rule, "C4G1", f"C4G1{rule}")
        return ([{"case": "R16", "cand": c, "gap": "none", "eps": 0.0, "offset_s": o} for c in cands for o in OFFSETS8]
                + [{"case": k, "cand": c, "gap": "none", "eps": 0.0, "offset_s": o}
                   for k in ("R12", "R14", "R15") for c in cands for o in OFFSETS8[::2]]
                + _jobs(("R16",), cands, ("mirror2", "asym2"), (1e-3, 2e-3, 3e-3)))
    if name.startswith("krows_"):  # every harness row once, for the regression table
        return _jobs(ALL_CASES, (name.split("_", 1)[1],), ("none",), (0.0,))
    if name == "screen2":
        return _jobs(("R9",), ("C4", "C5", "G1", "C4G1", "C5G1"), ("none", "mirror2"), EPS8)
    if name.startswith("full_"):  # full_C1: phase and gap grid of one candidate and the base
        cand = name.split("_", 1)[1]
        cands = (None, cand)
        return (_jobs(("R4", "R8"), cands, ("none", "mirror2"), EPS8)
                + _jobs(("R9",), (cand,), ("none", "mirror2"), EPS8 if cand not in ("C4", "G1", "C4G1") else ())
                + _jobs(("R4", "R8", "R9"), cands, ("asym2",), EPS4) + _jobs(("R9",), cands, ("asym06",), EPS4)
                + _jobs(("R16", "R12"), cands, ("none", "mirror2"), EPS4))
    if name.startswith("rows_"):  # rows_C1: every harness row once, candidate only (base stored)
        return _jobs(ALL_CASES, (name.split("_", 1)[1],), ("none",), (0.0,))
    if name.startswith("bias_"):
        cand = name.split("_", 1)[1]
        return _jobs(("R9",), (cand,), ("mirror2",), EPS4, bias_N=4000.0) + \
            _jobs(("R9",), (cand,), ("mirror2",), EPS4, bias_N=-4000.0) + \
            _jobs(("R7",), (None, cand), ("mirror2",), EPS4)
    raise ValueError(name)


def job_key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job)}, sort_keys=True)


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def summarize(rows, columns, period_t, period_phase, n, F_min_kN=9.415):
    """Twist and force values from the 1 ms record. D = n^T F [kN], tau = n^T s [mm], true force."""
    import numpy as np

    c = {str(name): i for i, name in enumerate(columns)}
    t = rows[:, 0]
    F = rows[:, [c[f"true_force_{leg}"] for leg in LEGS]] / 1e3
    s = np.cumsum(rows[:, [c[f"v_{leg}"] for leg in LEGS]] * 1e-3, axis=0) * 1e3
    crawler = rows[:, c["crawler"]] / 1e3
    attitude = rows[:, [c["roll"], c["pitch"]]]
    later = np.flatnonzero(~np.isin(period_phase, ("idle", "check", "touch")))
    te = float(period_t[later[0]])
    ke = int(np.searchsorted(t, te))
    is_touch_end_reached = ke < t.size
    lifted = np.flatnonzero((crawler == 0.0) & (t > te))
    tl = float(t[lifted[0]]) if lifted.size else None
    out = {"t_touch_end": te, "t_lift": tl,
           "D_te": float(F[max(ke - 200, 0):ke].mean(axis=0) @ n),
           "tau_te": float(n @ s[ke]) if is_touch_end_reached else None,
           "touch_attitude_max": [float(v) for v in np.abs(attitude[:ke]).max(axis=0)],
           "touch_attitude_span": [float(v) for v in np.ptp(attitude[:ke], axis=0)],
           "stroke_te_mm": [float(v) for v in s[ke]],
           "stroke_max_mm": [float(v) for v in s.max(axis=0)],
           "stroke_end_mm": [float(v) for v in s[-1]]}
    first = [int(np.argmax(F[:, i] > F[0, i] + 3.0)) for i in range(4)]
    out["s_contact"] = [round(float(s[first[i], i]), 3) for i in range(4)]
    if tl is None:
        return out
    kl = int(np.searchsorted(t, tl))
    after = F[kl:]
    i, j = np.unravel_index(int(np.argmin(after)), after.shape)
    k8 = int(np.searchsorted(t, tl + 8.0))
    window = F[kl:k8]
    width = 1000
    means = np.column_stack([np.convolve(window[:, q], np.ones(width) / width, "valid") for q in range(4)])
    grid = {}
    for offset in (0.0, 1.0, 3.0, 8.0, 15.0):
        k = int(np.searchsorted(t, tl + offset))
        if k + 200 < t.size:
            grid[f"{offset:g}"] = float(F[k:k + 400].mean(axis=0) @ n)
    i8, j8 = np.unravel_index(int(np.argmin(window)), window.shape)
    out.update(F_min=float(after[i, j]), F_min_leg=LEGS[j], t_min_after_lift=float(t[kl + i] - tl),
               F_min8=float(window.min()), F_min8_leg=LEGS[j8], F_min8_t=float(t[kl + i8] - tl),
               F_RL_min8=float(window[:, 2].min()), mean1s_min8=float(means.min()),
               F_RL_win=float(F[kl:kl + 400, 2].mean()), F_win=[float(v) for v in F[kl:kl + 400].mean(axis=0)],
               D_lift=float(F[kl:kl + 400].mean(axis=0) @ n), D_after_lift=grid,
               tau_lift=float(n @ s[kl]), lift_after_te=tl - te)
    return out


def run_one(job: dict) -> dict:
    t0 = time.perf_counter()
    try:
        pin(job["mask"])
        import numpy as np

        import candidates
        import harness_flow
        import verdict_cases
        import verdict_runs
        from harness_flow import COLUMNS, FlowSetting

        eps = float(job["eps"])
        original_limit = harness_flow.FlowLimiter.limit

        def limit(self, t_s, u, oil_force_N):
            delivered = original_limit(self, t_s, u, oil_force_N)
            touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
            touched |= np.asarray(oil_force_N) > TOUCH_N
            if eps and not touched.any():
                delivered = delivered * (1.0 - eps)
            return delivered

        if eps:
            harness_flow.FlowLimiter.limit = limit
        candidates.LOG_ESTIMATES[0] = bool(job.get("log_estimates"))
        candidates.install_candidate(job["cand"], bias_N=float(job.get("bias_N", 0.0)))
        candidates.install_gap_plant(verdict_runs, GAPS[job["gap"]])
        case = verdict_cases.resolve_case(job["case"], {})
        if job.get("offset_s") is not None:  # event start phase against the 10 Hz controller
            from dataclasses import replace as dc_replace

            case = dc_replace(case, twin=dc_replace(case.twin, offset_s=float(job["offset_s"])))
        decision = job.get("decision")
        if decision:
            case = verdict_cases.resolve_case(job["case"], {job["case"]: decision})
        result, series = verdict_runs.execute(case, FlowSetting(is_enabled=False), decision)
        if "error" in result:
            return {"job": job, "error": result["error"], "tb": result.get("tb"), "wall_s": time.perf_counter() - t0}
        plant = candidates.LAST_PLANT[0]
        rows = plant.flow_limiter.rows()
        from outrigger_sim.control import c2 as _c2  # noqa: F401
        out = summarize(rows, COLUMNS, series["t"], series["phase"], _twist_vector())
        values = result["values"]
        out.update(job=job, wall_s=round(time.perf_counter() - t0, 1),
                   trim=dict(candidates.RECORD),
                   commands_sha256=result["commands_sha256"],
                   harness_commands_sha256=result.get("harness_commands_sha256"),
                   final_phase=result["final_phase"],
                   harness_class=result.get("harness_class"),
                   failed_rows=result.get("failed_rows"),
                   times=values["times"], forces=values["forces"],
                   pressure=values.get("pressure"), twist=values.get("twist"),
                   guard_active_s=values.get("guard_active_s"),
                   events=[e for e in result["events"]
                           if e[1].startswith(("WARN", "FAULT", "INFO_LIFT", "INFO_TOUCH", "INFO_TWIST", "INFO_LOC",
                                               "leg_reapproach"))],
                   max_stroke_reading_mm=result.get("max_motor_stroke_reading_mm"),
                   event_output=result.get("event_output"), timeline=result.get("timeline"),
                   rut_ready_mm=result.get("rut_ready_mm"))
        return out
    except Exception as exc:  # keep the batch going, record the failure
        return {"job": job, "error": repr(exc), "tb": traceback.format_exc()[-3000:],
                "wall_s": time.perf_counter() - t0}


def _twist_vector():
    import numpy as np

    return np.array((0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mask", default=hex(DEFAULT_MASK))
    args = parser.parse_args()
    mask = int(args.mask, 16)
    pin(mask)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.batch}.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done.add(job_key({k: v for k, v in rec["job"].items() if k != "mask"}))
    jobs = [j for j in batch_jobs(args.batch) if job_key(j) not in done]
    print(f"{args.batch}: {len(jobs)} runs to do, {len(done)} done", flush=True)
    for job in jobs:
        job["mask"] = mask
    import verdict_runs

    verdict_runs.warm_numba_cache()
    t0 = time.perf_counter()
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, path.open("a", encoding="utf-8") as handle:
        for count, rec in enumerate(pool.imap_unordered(run_one, jobs), 1):
            handle.write(json.dumps(rec) + "\n")
            handle.flush()
            job = rec["job"]
            state = "ERR " + rec["error"][:200] if "error" in rec else (
                f"te {rec['t_touch_end']:.1f} D_lift {rec.get('D_lift', float('nan')):.1f} "
                f"Fmin {rec.get('F_min8', float('nan')):.1f} {rec['final_phase']} "
                f"ready {rec['times'].get('t_first_ready_s')} {rec['wall_s']:.0f}s")
            print(f"{count}/{len(jobs)} {job['case']} {job['cand']} {job['gap']} {job['eps']}: {state}", flush=True)
    print(f"done in {time.perf_counter() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
