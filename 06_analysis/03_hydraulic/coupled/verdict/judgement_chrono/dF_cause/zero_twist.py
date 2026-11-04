"""Harness counterfactual: remove the twist left by the TOUCH latches, then let the run go on.

Chrono enters LEVEL with D = 0 (tau = 0). Here each run gets a one-shot stroke correction along the
twist vector over the 0.2 s after TOUCH end (the commands are zero then): delta s = -(n^T F / K) n.
Nothing else changes. If the on-minus-off force gap comes from the twist of the latches, it must
collapse in these pairs. te comes from the unperturbed run of the same pair (bit-identical up to te).

Output: sweep/zero_twist.json.
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

OUT = HERE / "sweep"
K_NOM = 2.2705179e7
RAMP_S = 0.2
TE = {("R4", 0.85): 22.1, ("R4", None): 20.3, ("R8", 0.85): 21.7, ("R8", None): 20.2,
      ("R9", 0.85): 21.6, ("R9", None): 20.2}


def run_one(job: dict) -> dict:
    sweep.pin(sweep.MASK)
    import numpy as np
    import harness_flow
    import s9_soil_slope as slope
    import verdict_cases
    import verdict_runs
    from harness_flow import COLUMNS, V, FlowSetting

    n = np.array(sweep.N)
    te = TE[(job["case"], job["eta"])]
    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        if te <= t_s < te + RAMP_S:
            state = self.__dict__
            if "_tw_rate" not in state:
                state["_tw_D"] = float(n @ np.asarray(oil_force_N))
                state["_tw_rate"] = -state["_tw_D"] / K_NOM / RAMP_S * n
                _RECORD["D_removed_kN"] = state["_tw_D"] / 1e3
            delivered = delivered + state["_tw_rate"]
            self._rows[self._count - 1, V] = delivered
        return delivered

    _RECORD = {}
    harness_flow.FlowLimiter.limit = limit
    t0 = time.perf_counter()
    eta = job["eta"]
    setting = FlowSetting(is_enabled=False) if eta is None else FlowSetting(is_enabled=True, eta_v=eta)
    case = verdict_cases.resolve_case(job["case"], {})
    result, series = verdict_runs.execute(case, setting, None)
    rows = slope._CAP["plant"].flow_limiter.rows()
    out = sweep.summarize(rows, COLUMNS, series["t"], series["phase"])
    c = {str(name): i for i, name in enumerate(COLUMNS)}
    F = rows[:, [c[f"true_force_{l}"] for l in ("FL", "FR", "RL", "RR")]] / 1e3
    k = int(np.searchsorted(rows[:, 0], te + 0.35))
    out["D_after_correction_kN"] = float(F[k - 50:k + 50].mean(axis=0) @ n)
    out.update(job=job, wall_s=round(time.perf_counter() - t0, 1), t_ready=result["values"]["times"]["t_first_ready_s"],
               final_phase=result["final_phase"], **_RECORD)
    return out


def main() -> None:
    sweep.pin(sweep.MASK)
    import verdict_runs

    verdict_runs.warm_numba_cache()
    jobs = [{"case": c, "eta": eta} for c in ("R9", "R8", "R4") for eta in (None, 0.85)]
    out = []
    with get_context("spawn").Pool(2, maxtasksperchild=1) as pool:
        for rec in pool.imap_unordered(run_one, jobs):
            out.append(rec)
            print(json.dumps({k: (round(rec[k], 3) if isinstance(rec[k], float) else rec[k]) for k in (
                "job", "F_min", "leg", "F_min_first8", "leg_first8", "F_RL_min_first8", "mean1s_RL_min", "F_RL_win",
                "D_removed_kN", "D_after_correction_kN", "D_lift", "t_touch_end", "t_ready", "final_phase")}), flush=True)
    (OUT / "zero_twist.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
