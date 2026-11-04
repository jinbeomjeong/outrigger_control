"""Pair-synchronised contact counterfactual on the harness (corrected).

Each leg's approach speed is scaled by c_i until that leg touches, so the two legs of a pair reach
their own contact stroke at the same time, with the contact strokes unchanged. Pass 1 finds the true
contact strokes, pass 2 and 3 refine the pair scale for the rear pair, whose gap moves once the front
pair is synchronised. Delivered speeds are written back to the record, so stroke integrals are true.

Output: sweep/sync2.json. The first attempt (sweep.py sync) integrated recorded speeds without the
scale and inverted c; it counts only as a perturbation test.
"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep  # noqa: E402

TOUCH_N = sweep.TOUCH_N
OUT = HERE / "sweep"


def run_one(job: dict) -> dict:
    sweep.pin(sweep.MASK)
    import numpy as np
    import harness_flow
    import s9_soil_slope as slope
    import verdict_cases
    import verdict_runs
    from harness_flow import COLUMNS, V, FlowSetting

    scale = np.array(job.get("c", [1.0, 1.0, 1.0, 1.0]), float)
    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > TOUCH_N
        delivered = np.where(touched, delivered, delivered * scale)
        self._rows[self._count - 1, V] = delivered
        return delivered

    harness_flow.FlowLimiter.limit = limit
    t0 = time.perf_counter()
    eta = job["eta"]
    setting = FlowSetting(is_enabled=False) if eta is None else FlowSetting(is_enabled=True, eta_v=eta)
    case = verdict_cases.resolve_case(job["case"], {})
    result, series = verdict_runs.execute(case, setting, None)
    rows = slope._CAP["plant"].flow_limiter.rows()
    out = sweep.summarize(rows, COLUMNS, series["t"], series["phase"])
    out.update(job=job, wall_s=round(time.perf_counter() - t0, 1), t_ready=result["values"]["times"]["t_first_ready_s"],
               final_phase=result["final_phase"])
    return out


def pair_scale(rec: dict) -> list[float]:
    s = rec["s_contact"]
    front, rear = 0.5 * (s[0] + s[1]), 0.5 * (s[2] + s[3])
    return [s[0] / front, s[1] / front, s[2] / rear, s[3] / rear]


def main() -> None:
    sweep.pin(sweep.MASK)
    import verdict_runs

    verdict_runs.warm_numba_cache()
    keys = [(c, eta) for c in ("R9", "R8", "R4") for eta in (None, 0.85)]
    out = []
    scales = {k: [1.0, 1.0, 1.0, 1.0] for k in keys}
    with get_context("spawn").Pool(2, maxtasksperchild=1) as pool:
        for stage in range(3):
            jobs = [{"case": k[0], "eta": k[1], "c": scales[k], "stage": stage} for k in keys]
            for rec in pool.imap_unordered(run_one, jobs):
                key = (rec["job"]["case"], rec["job"]["eta"])
                out.append(rec)
                scales[key] = pair_scale(rec)
                print(json.dumps({k: (round(rec[k], 3) if isinstance(rec[k], float) else rec[k]) for k in (
                    "job", "F_min", "leg", "F_RL_win", "D_te", "D_lift", "tau_te", "gap_front", "gap_rear",
                    "t_contact_rel_te", "mean1s_RL_min")}), flush=True)
            (OUT / "sync2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
