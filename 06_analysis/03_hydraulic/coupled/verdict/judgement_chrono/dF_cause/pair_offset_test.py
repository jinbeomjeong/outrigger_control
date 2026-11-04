"""Does the extra R4 latch pattern (tau = +0.32 mm) need the flow limit?

The eta 0.85 R4 runs show a pattern the off sweep never showed. With the limit on, the front pair ends
TOUCH 0.125 mm behind the rear pair (E-3: 35.158 vs 35.033 mm). This test gives a flow-off run only that
front-rear offset: front pair approach speed x (1 - 0.125 / 345) until each leg touches, plus the same
common phase sweep eps as phase_on.json. Nothing is saturated in these runs. Also writes the stratified
on-off comparison (same latch pattern tau, |delta tau| <= 0.02 mm).

Run: conda run -n dynamics-dev python -I pair_offset_test.py
Output: pair_offset_test.json, stratified_on_off.json (this folder).
"""
from __future__ import annotations

import json
import sys
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep  # noqa: E402

OFFSET_MM = 0.125
CONTACT_STROKE_MM = 345.0
FRONT = 1.0 - OFFSET_MM / CONTACT_STROKE_MM
EPS = (0.0, 2.5e-4, 5e-4, 1e-3, 1.5e-3, 2e-3)
NRL = -0.5228340347436333
TOL_MM = 0.02


def run_one(job: dict) -> dict:
    sweep.pin(sweep.MASK)
    import numpy as np
    import harness_flow
    import s9_soil_slope as slope
    import verdict_cases
    import verdict_runs
    from harness_flow import COLUMNS, V, FlowSetting

    eps = float(job["eps"])
    scale = np.array(job["c"], float)
    original_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        delivered = original_limit(self, t_s, u, oil_force_N)
        touched = self.__dict__.setdefault("_touched", np.zeros(4, bool))
        touched |= np.asarray(oil_force_N) > sweep.TOUCH_N
        if eps and not touched.any():
            delivered = delivered * (1.0 - eps)
        delivered = np.where(touched, delivered, delivered * scale)
        self._rows[self._count - 1, V] = delivered
        return delivered

    harness_flow.FlowLimiter.limit = limit
    case = verdict_cases.resolve_case(job["case"], {})
    result, series = verdict_runs.execute(case, FlowSetting(is_enabled=False), None)
    out = sweep.summarize(slope._CAP["plant"].flow_limiter.rows(), COLUMNS, series["t"], series["phase"])
    out.update(job=job, t_ready=result["values"]["times"]["t_first_ready_s"], final_phase=result["final_phase"])
    return out


def stratify() -> dict:
    """On minus off inside the same latch pattern, with on eps 0 from the stored-hash run."""
    import numpy as np

    on_runs = json.loads((HERE / "phase_on.json").read_text(encoding="utf-8"))
    off_runs = json.loads((HERE / "phase_off.json").read_text(encoding="utf-8"))
    sync = json.loads((HERE / "sync2.json").read_text(encoding="utf-8"))
    report = {}
    keys = ("F_RL_min_first8", "mean1s_RL_min", "F_RL_win")
    for case in ("R4", "R9"):
        on = [r for r in on_runs if r["job"]["case"] == case]
        on += [r for r in sync if r["job"]["case"] == case and r["job"]["eta"] == 0.85 and r["job"]["stage"] == 0]
        off = [r for r in off_runs if r["job"]["case"] == case]
        strata = []
        for level in sorted({round(r["tau_te"], 2) for r in on}):
            a = [r for r in on if abs(r["tau_te"] - level) <= TOL_MM]
            b = [r for r in off if abs(r["tau_te"] - level) <= TOL_MM]
            row = {"tau_mm": level, "n_on": len(a), "n_off": len(b)}
            for key in keys:
                row[f"{key}_on"] = float(np.mean([r[key] for r in a])) if a else None
                row[f"{key}_off"] = float(np.mean([r[key] for r in b])) if b else None
                row[f"{key}_delta"] = row[f"{key}_on"] - row[f"{key}_off"] if a and b else None
            strata.append(row)
        twist_free = {}
        for key in keys:
            on_v = np.array([r[key] - NRL * r["D_lift"] for r in on])
            off_v = np.array([r[key] - NRL * r["D_lift"] for r in off])
            twist_free[key] = {"on_mean": float(on_v.mean()), "on_std": float(on_v.std(ddof=1)), "off_mean": float(off_v.mean()),
                               "off_std": float(off_v.std(ddof=1)), "shift": float(on_v.mean() - off_v.mean())}
        report[case] = {"strata": strata, "twist_removed_metric": twist_free,
                        "levels_on": sorted({round(r["tau_te"], 2) for r in on}),
                        "levels_off": sorted({round(r["tau_te"], 2) for r in off})}
    return report


def main() -> None:
    sweep.pin(sweep.MASK)
    report = stratify()
    (HERE / "stratified_on_off.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=0))
    import verdict_runs

    verdict_runs.warm_numba_cache()
    jobs = [{"case": "R4", "eps": e, "c": [FRONT, FRONT, 1.0, 1.0]} for e in EPS]
    out = []
    with get_context("spawn").Pool(2, maxtasksperchild=1) as pool:
        for rec in pool.imap_unordered(run_one, jobs):
            out.append(rec)
            print(json.dumps({k: (round(rec[k], 3) if isinstance(rec[k], float) else rec[k]) for k in (
                "job", "F_min", "leg", "F_RL_min_first8", "mean1s_RL_min", "F_RL_win", "D_te", "D_lift", "tau_te",
                "t_contact_rel_te", "t_ready")}), flush=True)
    (HERE / "pair_offset_test.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
