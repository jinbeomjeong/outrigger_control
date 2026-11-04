"""Harness interventions without touching any harness file.

phase: the delivered approach speed is scaled by (1 - eps) until the first leg touches. It moves the
       contact time against the 10 Hz controller by about eps x 25 s and changes nothing else.
sync:  each leg's approach speed is scaled by c_i until that leg touches, so the legs of a pair reach
       their own contact stroke in the same period (the Chrono situation, gap L-R = 0 in time), the
       contact strokes staying as they are.

Usage: conda run -n dynamics-dev python -I sweep.py phase_off | phase_on | sync
"""
from __future__ import annotations

import ctypes
import json
import sys
import time
from ctypes import wintypes
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
CODE = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
OUT = Path(__file__).resolve().parent / "sweep"
MASK = 0x0C000000
N = (0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333)
TOUCH_N = 3000.0
for path in (CODE, S9_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def summarize(rows, columns, period_t, period_phase):
    import numpy as np

    c = {str(n): i for i, n in enumerate(columns)}
    legs = ("FL", "FR", "RL", "RR")
    t = rows[:, 0]
    F = rows[:, [c[f"true_force_{l}"] for l in legs]] / 1e3
    s = np.cumsum(rows[:, [c[f"v_{l}"] for l in legs]] * 1e-3, axis=0) * 1e3
    cr = rows[:, c["crawler"]] / 1e3
    n = np.array(N)
    te = period_t[np.flatnonzero(~np.isin(period_phase, ("idle", "check", "touch")))[0]]
    tl = t[(cr == 0.0) & (t > te)][0]
    ke, kl = int(np.searchsorted(t, te)), int(np.searchsorted(t, tl))
    first = [int(np.argmax(F[:, i] > F[0, i] + 3.0)) for i in range(4)]
    after = F[kl:]
    i, j = np.unravel_index(int(np.argmin(after)), after.shape)
    k8 = int(np.searchsorted(t, tl + 8.0))
    win = F[kl:k8]
    w = 1000
    mean1s = np.column_stack([np.convolve(win[:, q], np.ones(w) / w, "valid") for q in range(4)])
    return dict(t_touch_end=float(te), t_lift=float(tl), lift_after_te=float(tl - te),
                F_min=float(after[i, j]), leg=legs[j], t_min_after_lift=float(t[kl + i] - tl),
                F_min_first8=float(win.min()), leg_first8=legs[int(np.unravel_index(int(np.argmin(win)), win.shape)[1])],
                F_RL_min_first8=float(win[:, 2].min()),
                mean1s_min_first8=float(mean1s.min()), mean1s_RL_min=float(mean1s[:, 2].min()),
                F_RL_win=float(F[kl:kl + 400, 2].mean()),
                D_te=float(F[ke - 200:ke].mean(axis=0) @ n), D_lift=float(F[kl:kl + 400].mean(axis=0) @ n),
                tau_te=float(n @ s[ke]), tau_lift=float(n @ s[kl]),
                t_contact_rel_te=[round(float(t[q] - te), 3) for q in first],
                s_contact=[round(float(s[first[q], q]), 3) for q in range(4)],
                gap_front=float(s[first[0], 0] - s[first[1], 1]), gap_rear=float(s[first[2], 2] - s[first[3], 3]))


def run_one(job: dict) -> dict:
    pin(MASK)
    import numpy as np
    import harness_flow
    import s9_soil_slope as slope
    import verdict_cases
    import verdict_runs
    from harness_flow import COLUMNS, FlowSetting

    eps = float(job.get("eps", 0.0))
    scale = np.array(job.get("c", [1.0, 1.0, 1.0, 1.0]), float)
    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > TOUCH_N
        if eps and not touched.any():
            delivered = delivered * (1.0 - eps)
        if not touched.all():
            delivered = np.where(touched, delivered, delivered * scale)
        return delivered

    harness_flow.FlowLimiter.limit = limit
    t0 = time.perf_counter()
    eta = job["eta"]
    setting = FlowSetting(is_enabled=False) if eta is None else FlowSetting(is_enabled=True, eta_v=eta)
    case = verdict_cases.resolve_case(job["case"], {})
    result, series = verdict_runs.execute(case, setting, None)
    rows = slope._CAP["plant"].flow_limiter.rows()
    out = summarize(rows, COLUMNS, series["t"], series["phase"])
    out.update(job=job, wall_s=round(time.perf_counter() - t0, 1),
               verdict_min=result["values"]["forces"]["after_liftoff"]["min_kN"],
               t_ready=result["values"]["times"]["t_first_ready_s"],
               final_phase=result["final_phase"])
    return out


EPS = (0.0, 2.5e-4, 5e-4, 1e-3, 1.5e-3, 2e-3, 3e-3, 4e-3)


def jobs_for(mode: str) -> list[dict]:
    if mode == "phase_off":
        return [{"case": c, "eta": None, "eps": e} for c in ("R4", "R8", "R9") for e in EPS]
    if mode == "phase_on":
        return [{"case": c, "eta": 0.85, "eps": e} for c in ("R9", "R4") for e in EPS[1:6]]
    raise ValueError(mode)


def pair_scale(s_contact: list[float]) -> list[float]:
    front = 0.5 * (s_contact[0] + s_contact[1])
    rear = 0.5 * (s_contact[2] + s_contact[3])
    return [s_contact[0] / front, s_contact[1] / front, s_contact[2] / rear, s_contact[3] / rear]


def run_sync(pool) -> list[dict]:
    """Two OFF passes to find the pair scale of each case, then the on and off pair with it."""
    base = {}
    for rec in pool.imap_unordered(run_one, [{"case": c, "eta": None} for c in ("R4", "R8", "R9")]):
        base[rec["job"]["case"]] = rec
    scales = {c: pair_scale(rec["s_contact"]) for c, rec in base.items()}
    second = {}
    for rec in pool.imap_unordered(run_one, [{"case": c, "eta": None, "c": s} for c, s in scales.items()]):
        second[rec["job"]["case"]] = rec
    out = list(base.values()) + list(second.values())
    for c, rec in second.items():  # rear contact moved once the front pair is synchronised
        scales[c] = pair_scale(rec["s_contact"])
    jobs = [{"case": c, "eta": eta, "c": s} for c, s in scales.items() for eta in (None, 0.85)]
    for rec in pool.imap_unordered(run_one, jobs):
        print(json.dumps(rec), flush=True)
        out.append(rec)
    return out


def main() -> None:
    pin(MASK)
    mode = sys.argv[1]
    import verdict_runs

    verdict_runs.warm_numba_cache()
    OUT.mkdir(exist_ok=True)
    out = []
    with get_context("spawn").Pool(2, maxtasksperchild=1) as pool:
        if mode == "sync":
            out = run_sync(pool)
        else:
            for rec in pool.imap_unordered(run_one, jobs_for(mode)):
                print(json.dumps({k: rec[k] for k in ("job", "F_min", "leg", "F_RL_win", "D_lift", "tau_te", "wall_s")}), flush=True)
                out.append(rec)
    (OUT / f"{mode}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
