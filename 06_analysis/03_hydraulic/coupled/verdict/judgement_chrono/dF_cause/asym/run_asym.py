"""TOUCH-end twist scatter of Chrono case A_bottom_rpB_Fs0 (R9) under a left-right pad gap offset.

Uses the worktree code (first on sys.path) and the same job as the stored run
(``run_S8C.job_l2b_s8`` through ``outrigger_sim.batch``, placement pcore, one process per case). The
only change per case is ``L2bModel(pad_gap_offsets_m=...)``, set in the case process.

Phase: a common gap delta moves all four contact times by delta / 10.46 mm/s (R-2 touch window speed
0.5 v_max) against the 10 Hz controller; 1.046 mm = one period.

Usage: python -I run_asym.py <max_workers> <duration_s> <id> [<id> ...]
"""
from __future__ import annotations

import json
import os
import sys
import time
from functools import partial
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-ae9039e69988d5282")
OUT = Path(__file__).resolve().parent / "runs"
CASE_ID = "A_bottom_rpB_Fs0"
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def gaps(asym_m: float, delta_m: float) -> list[float]:
    """Offsets (FL, FR, RL, RR): left +asym, right -asym, all + delta [m]."""
    return [asym_m + delta_m, -asym_m + delta_m, asym_m + delta_m, -asym_m + delta_m]


RUNS = {
    "ctrl_none": None,  # option off: must reproduce the stored run bit for bit
    "sym_d035": gaps(0.0, 0.35e-3),
    "asym2_d000": gaps(2.0e-3, 0.0),
    "asym2_d035": gaps(2.0e-3, 0.35e-3),
    "asym2_d070": gaps(2.0e-3, 0.70e-3),
    # Added after the first results: all three +2 mm rows sat on one side (RL load up), so the mirror
    # sign shows the other side; +0.6 mm is the size of the harness R9 gap (L-R 1.15-1.5 mm).
    "mirror2_d000": gaps(-2.0e-3, 0.0),
    "mirror2_d035": gaps(-2.0e-3, 0.35e-3),
    "mirror2_d070": gaps(-2.0e-3, 0.70e-3),
    "asym06_d000": gaps(0.6e-3, 0.0),
    "asym06_d035": gaps(0.6e-3, 0.35e-3),
    "asym06_d070": gaps(0.6e-3, 0.70e-3),
}


def job(case, case_dir):
    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono import l2b_model

    import run_S8C as s8

    offsets = case.settings["pad_gap_offsets_m"]
    if offsets is not None:
        real = l2b_model.L2bModel
        l2b_model.L2bModel = partial(real, pad_gap_offsets_m=tuple(offsets))
    c = s8.case_table()[CASE_ID]
    summary, run_meta = s8.job_l2b_s8(c, Path(case_dir), duration_s=case.settings["duration_s"])
    summary["asym"] = {"pad_gap_offsets_m": offsets, "source_l2b_model": l2b_model.__file__}
    Path(case_dir, "result.json").write_text(
        json.dumps(s8.s6c._plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    keep = {k: summary[k] for k in ("case", "phases", "runner", "asym") if k in summary}
    return CaseResult(summary=s8.s6c._plain(keep), run_meta=s8.s6c._plain(run_meta))


def main() -> None:
    workers, duration = int(sys.argv[1]), float(sys.argv[2])
    ids = sys.argv[3:]
    from outrigger_sim.batch import Case, run_cases

    cases = [Case(i, {"pad_gap_offsets_m": RUNS[i], "duration_s": duration}) for i in ids]
    d = OUT / time.strftime("batch_%H%M%S")
    d.mkdir(parents=True)
    t0 = time.perf_counter()
    report = run_cases(cases, job, d, max_workers=workers, placement="pcore", timeout_s=1500.0)
    print(json.dumps({"dir": str(d), "wall_s": time.perf_counter() - t0,
                      "env": {k: os.environ.get(k) for k in ("OUTRIGGER_ROD_SIDE_MECHANICS", "OPENBLAS_NUM_THREADS")}}))
    print(report if not hasattr(report, "counts") else report.counts)


if __name__ == "__main__":
    main()
