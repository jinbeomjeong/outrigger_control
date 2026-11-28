"""One shortened (or full) run_S8C L2b row through ``job_l2b_s8``, written to a given folder.

Mirrors ``run_S8C.job_case`` for an L2b case: the v5 / flow keywords come from the same parser
parts as ``run_S8C.main`` (``add_flow_limit_arguments`` + ``add_hydraulic_arguments(with_valve_tau=
False)``) applied to ``s9_batch.v5_rigid_argv(setting)``. ``--imu-model`` / ``--imu-gains`` (only
after the C-1 change) go to ``job_l2b_s8(imu_a=...)``.

Usage (Chrono-dev, -I -B):
  python l2b_row.py <worktree> <out case dir> <case id> <V0|VB> [--duration S] [--expect TAG]
      [--imu-model inclinometer --imu-gains v5_A]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("out")
    ap.add_argument("case_id")
    ap.add_argument("setting", choices=("V0", "VB"))
    ap.add_argument("--duration", type=float, default=None, help="None = the row end rule (full row)")
    ap.add_argument("--expect", default=None)
    ap.add_argument("--imu-model", default=None)
    ap.add_argument("--imu-gains", default=None)
    a = ap.parse_args()
    wt = Path(a.worktree).resolve()
    sys.path.insert(0, str(wt / "03_src"))
    sys.path.insert(0, str(wt / "04_scripts" / "02_chrono"))
    import run_S8C
    import s9_batch
    from outrigger_sim.hydraulics.flow_limit_run import add_flow_limit_arguments, flow_setting_from_args
    from outrigger_sim.hydraulics.v5_options import add_hydraulic_arguments, hydraulic_options_from_args

    os.environ[run_S8C.CRAWLER_ENV] = "yaml"  # run_S8C.main default --crawler yaml
    p = argparse.ArgumentParser()
    add_flow_limit_arguments(p)
    add_hydraulic_arguments(p, with_valve_tau=False)
    v5_argv = s9_batch.v5_rigid_argv(a.setting)
    pa = p.parse_args(v5_argv)
    flow = flow_setting_from_args(pa)
    opts = hydraulic_options_from_args(pa).without_flow()
    kw = {}
    if flow is not None:
        kw["flow_limit"] = flow.to_dict()
    if opts.is_any_on:
        kw["hydraulics"] = opts.to_dict()
    if a.expect:
        kw["expect_controller"] = a.expect
    if a.imu_model is not None:
        kw["imu_a"] = {"model": a.imu_model, "gains": a.imu_gains}
    case = run_S8C.case_table()[a.case_id]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.perf_counter()
    summary, run_meta = run_S8C.job_l2b_s8(case, out, duration_s=a.duration, **kw)
    (out / "result.json").write_text(json.dumps(run_S8C.s6c._plain(summary), indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    (out / "driver.json").write_text(json.dumps({"argv": sys.argv, "v5_argv": v5_argv, "kw": kw,
                                                 "wall_s": time.perf_counter() - t0,
                                                 "pid": os.getpid()}, indent=1, default=str),
                                     encoding="utf-8")
    print("done", a.case_id, a.setting, f"{time.perf_counter() - t0:.1f} s", summary.get("controller_tag"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
