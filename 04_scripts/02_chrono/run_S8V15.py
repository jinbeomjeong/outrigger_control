"""S8 V15 on L2b-NSC: seal friction, FL up-sweep to lift-off (a) and 0 -> 10 -> 0 mm round trip (b).

``00_docs/01_dynamics/dynamics_model.md`` rev. 39 5.26 (5.26.2 reference, 5.26.8 ledger, 5.26.9 rows);
reference ``06_analysis/00_dynamics/s8_v15_reference.json / V15_rev39`` and
``s8_v15_dynamic_check.json``. Judge ``outrigger_sim.verify.s8_v15``, recorder
``outrigger_sim.chrono.s8_v15_recorder`` (both new 2026-10-25; no existing module is changed).

Usage (Chrono-dev python, any folder)::

    python -I -X utf8 -u run_S8V15.py list [--cost-us 420]          # case table + wall estimate
    python -I -X utf8 -u run_S8V15.py smoke [--case V15a_L4] [--speed 5e-3] [--cap 6]
    python -I -X utf8 -u run_S8V15.py run --approved [--jobs 7] [--only ID ...] [--with-head-only]
    python -I -X utf8 -u run_S8V15.py judge --batch 07_results/S8/v15_<stamp>
    python -I -X utf8 -u run_S8V15.py rejudge --batch 07_results/S8/v15_<stamp>

``rejudge`` (2026-10-25, rev. 42 5.29.7, U-S8-48) recomputes every case judge from the saved
``series.npz`` + ``result.json`` (timeline, case) with the current judge module and writes
``<case>/judge.json`` (``result.json`` is not changed); ``judge`` then prefers ``judge.json``.
The first rejudge of a batch moves the old ``v15_summary.json`` to ``v15_summary_v1.json``
(never overwritten). No Chrono run.

Case procedure (5.26.9 run conditions; top level, level floor, beta 1.0 GPa (YAML), L_0h = L_0r
(YAML), p_r0 2 bar g, dt 1e-4 s):

1. ``L2bModel`` static start at the operating extensions (pads touching, crawler spheres present
   and lifted, rigid NSC crawler, pilot check), rod-side law **not armed** (head only ``k_2``), seal
   friction disabled until the rod-side arming (``L2bForceActuator`` rule); settle
   :data:`SETTLE_S`.
2. Arm the rod-side law (``rod_side.arm()``; the friction re-arms with ``f = 0``, stuck) and
   re-arm the friction explicitly (``seal_friction.reset()``, head-only variant); hold
   :data:`HOLD_S` with every leg locked (the residual "before" window of (b) = its last
   :data:`MEAN_S`).
3. Ledger start, FL command ``+v`` (``SpeedReference`` acceleration limit = v_max / command ramp,
   stroke-end braking at the soft limit).
   (a) soft limit ``s0 + 20 mm``; 1e-5 s window from the first 20 ms mean pad force below
   :data:`FINE_N` until the end; the run ends :data:`AFTER_LIFT_S` after the 20 ms mean of a pad
   force reaches 0 (event time recorded; the judged threshold is the interpolated crossing).
   (b) soft limit ``s0 + 10 mm``; at the stop, command ``-v`` back to ``s0`` (soft lower limit),
   then hold :data:`HOLD_B_S`; residual = mean of the last :data:`MEAN_S` minus the mean before
   the motion.

Outputs ``07_results/S8/v15_<stamp>/<case>/series.npz`` (1 ms block means, ledger columns),
``result.json`` (metrics, checks, ledger summary), ``case.json``; ``judge`` writes
``v15_summary.json`` in the batch folder (speed pair rows included).

ASSUMPTIONS of this script: settle 2 s / hold 1.5 s / (b) hold 10 s (the time-domain check used a
10 s hold), fine-window start 1.5 kN, end 0.1 s after the lift-off event; FL speed reaches ``v``
within ``v / a`` (0.5 ms at 0.1 mm/s) instead of the 0.1 s trapezoid of the reduced check.
Units SI (mm / kN only in names).
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S8"
MAX_JOBS = 7
DT_S = 1.0e-4
DT_FINE_S = 1.0e-5
SPEED_M_S = 1.0e-4
SPEED_SLOW_M_S = 5.0e-5
SETTLE_S = 2.0
HOLD_S = 1.5
MEAN_S = 1.0
HOLD_B_S = 10.0
FINE_N = 1500.0
AFTER_LIFT_S = 0.1
A_TARGET_M = 0.020
B_TARGET_M = 0.010
A_MAX_EXTRA_S = 10.0
LEVEL = "top"
FS_LEVELS_N = (0.0, 2000.0, 4000.0, 8000.0)
RL_SLOPE_N_PER_M = 6.5e6
"""Cost estimate only: RL contact-force slope near lift-off (5.26.2 (b): about 6.1-8 kN/mm)."""
LIFT_REF_MM = {0.0: 11.737, 2000.0: 11.609, 4000.0: 11.482, 8000.0: 11.228}
LIFT_REF_HEAD_MM = {0.0: 13.481, 2000.0: 13.310, 4000.0: 13.140, 8000.0: 12.799}
POOL_FACTOR = 1.5
"""ASSUMPTION (cost): wall per step with 7 P-core workers / single process (S8 p1r: 1.5x)."""


# --- cases ------------------------------------------------------------------------------------


def case_table(with_head_only: bool = False) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for fs in FS_LEVELS_N:
        tag = f"L{fs / 1000:g}"
        for kind in ("a", "b"):
            cases[f"V15{kind}_{tag}"] = {"kind": kind, "fs_N": fs, "variant": "rod_side",
                                         "speed_m_s": SPEED_M_S, "group": "main"}
    for kind in ("a", "b"):
        cases[f"V15{kind}_L8_v005"] = {"kind": kind, "fs_N": 8000.0, "variant": "rod_side",
                                       "speed_m_s": SPEED_SLOW_M_S, "group": "speed",
                                       "pair": f"V15{kind}_L8"}
    if with_head_only:
        for kind in ("a", "b"):
            cases[f"V15{kind}_L4_head"] = {"kind": kind, "fs_N": 4000.0, "variant": "head_only",
                                           "speed_m_s": SPEED_M_S, "group": "head_only"}
    return cases


def simulated(case: dict[str, Any]) -> tuple[float, float, float]:
    """(simulated s, steps at 1e-4 s, steps at 1e-5 s) for the wall estimate."""
    v = case["speed_m_s"]
    pre = SETTLE_S + HOLD_S
    if case["kind"] == "a":
        lift = (LIFT_REF_MM if case["variant"] == "rod_side" else LIFT_REF_HEAD_MM)[case["fs_N"]]
        t_fine = FINE_N / RL_SLOPE_N_PER_M / v + AFTER_LIFT_S
        t_coarse = pre + lift * 1e-3 / v - FINE_N / RL_SLOPE_N_PER_M / v
        return t_coarse + t_fine, t_coarse / DT_S, t_fine / DT_FINE_S
    t = pre + 2.0 * B_TARGET_M / v + HOLD_B_S
    return t, t / DT_S, 0.0


# --- job --------------------------------------------------------------------------------------


def _params(case: dict[str, Any]):
    from outrigger_sim.chrono import s8_plant_adapter as plant
    from outrigger_sim.params import load_params

    yaml = load_params(level=LEVEL, model="L2b_NSC")
    over = plant.seal_friction_overrides(yaml, case["fs_N"])
    params = load_params(level=LEVEL, model="L2b_NSC", overrides=over) if over else yaml
    return params, over


def _run(model, rec, seconds: float, *, stop=None, on_block=None) -> dict[str, Any]:
    t_end = float(model.system.GetChTime()) + seconds
    steps = 0
    wall0 = time.perf_counter()
    n_rows = len(rec.rows.get("t_s", []))
    while float(model.system.GetChTime()) < t_end - 1e-12:
        model.step()
        steps += 1
        n = len(rec.rows.get("t_s", []))
        if n != n_rows:
            n_rows = n
            if on_block is not None:
                on_block()
        if stop is not None and stop():
            break
    return {"steps": steps, "wall_s": time.perf_counter() - wall0,
            "t_end_s": float(model.system.GetChTime())}


def build(case: dict[str, Any]):
    import numpy as np

    from outrigger_sim.chrono import s8_plant_adapter as plant
    from outrigger_sim.chrono.l2b_model import L2bModel
    from outrigger_sim.chrono.s8_v15_recorder import V15Recorder

    params, over = _params(case)
    model = L2bModel(params, crawler=True, dt_s=DT_S, rod_side=(case["variant"] == "rod_side"),
                     rod_side_armed=False)
    plant_meta = plant.check_model(model, case["fs_N"], "pilot_check")
    rec = V15Recorder(model)
    rec.start_recording()
    meta = {"overrides": over, "plant": plant_meta, "start_s_ref_m": list(model.start_s_ref_m),
            "start_forces_N": np.asarray(model.start_forces_N).tolist(),
            "crawler_contact": model.crawler_contact}
    return params, model, rec, meta


def run_case(case: dict[str, Any], case_dir: Path, *, cap_s: float | None = None) -> dict[str, Any]:
    import numpy as np

    from outrigger_sim.verify import s8_v15 as v15

    params, model, rec, meta = build(case)
    act = model.actuator
    ref = act.reference
    timeline: dict[str, Any] = {}
    r_settle = _run(model, rec, SETTLE_S)
    if act.rod_side is not None:
        act.rod_side.arm()
    if act.seal_friction is not None:
        act.seal_friction.reset()
    timeline["armed_t_s"] = float(model.system.GetChTime())
    r_hold = _run(model, rec, HOLD_S)
    rec.start_ledger()
    rec.start_motion()
    s0 = float(ref.s_ref_m[0])
    t_motion = float(model.system.GetChTime())
    timeline["motion_start_t_s"] = t_motion
    v = float(case["speed_m_s"])
    lo = ref.soft_limits_m[:, 0].copy()
    hi = ref.soft_limits_m[:, 1].copy()
    cmd = np.zeros(4)
    runs: dict[str, Any] = {"settle": r_settle, "hold": r_hold}
    budget = (lambda t: t if cap_s is None else min(t, max(cap_s - (t_motion), 0.0)))
    if case["kind"] == "a":
        hi[0] = s0 + A_TARGET_M
        ref.set_soft_limits(lo, hi)
        cmd[0] = v
        model.set_command(cmd)
        win: collections.deque = collections.deque(maxlen=round(v15.SMOOTH_S / rec.block_s))
        state: dict[str, Any] = {"fine_t": None, "lift_t": None}

        def on_block():
            win.append(rec.last_block("N_N"))
            if len(win) < win.maxlen:
                return
            n_mean = np.mean(win, axis=0)
            t = float(model.system.GetChTime())
            if state["fine_t"] is None and n_mean.min() < FINE_N:
                state["fine_t"] = t
                model.set_dt(DT_FINE_S)
            if state["lift_t"] is None and n_mean.min() <= 0.0:
                state["lift_t"] = t

        def stop():
            return (state["lift_t"] is not None
                    and float(model.system.GetChTime()) >= state["lift_t"] + AFTER_LIFT_S)

        t_max = A_TARGET_M / v + A_MAX_EXTRA_S
        runs["motion"] = _run(model, rec, budget(t_max), stop=stop, on_block=on_block)
        timeline.update(fine_start_t_s=state["fine_t"], liftoff_event_t_s=state["lift_t"])
    else:
        lo[0] = s0
        hi[0] = s0 + B_TARGET_M
        ref.set_soft_limits(lo, hi)
        cmd[0] = v
        model.set_command(cmd)

        def at(target: float):
            return lambda: (abs(float(ref.s_ref_m[0]) - target) <= 1e-9
                            and abs(float(ref.u_applied_m_s[0])) <= 1e-9)

        t_leg = B_TARGET_M / v + 2.0
        runs["out"] = _run(model, rec, budget(t_leg), stop=at(s0 + B_TARGET_M))
        timeline["at_top_t_s"] = float(model.system.GetChTime())
        cmd[0] = -v
        model.set_command(cmd)
        runs["back"] = _run(model, rec, budget(t_leg), stop=at(s0))
        timeline["back_t_s"] = float(model.system.GetChTime())
        model.set_command(np.zeros(4))
        runs["hold_b"] = _run(model, rec, budget(HOLD_B_S))
    timeline["end_t_s"] = float(model.system.GetChTime())
    arrays = rec.arrays()
    np.savez_compressed(case_dir / "series.npz", **arrays)
    out = {"case": case, "meta": meta, "timeline": timeline, "runs": runs,
           "ledger_steps": rec.ledger_steps, "switch_events": rec.switch_events[:50],
           "n_switch_events": len(rec.switch_events),
           "piston_monitor": act.piston_monitor(),
           "s8_record": act.s8_record(),
           "rod_side_lock_table": None if act.rod_side is None else act.rod_side.lock_table(),
           "crawler_N_max": float(np.nanmax(arrays["crawler_N"])),
           "nonfinite": int(sum(np.count_nonzero(~np.isfinite(a)) for k, a in arrays.items()
                                if a.dtype.kind == "f" and k not in v15_ledger_keys()))}
    out["judge"] = judge_case(case, arrays, timeline, params)
    return out


def v15_ledger_keys() -> tuple[str, ...]:
    from outrigger_sim.chrono.s8_v15_recorder import LEDGER_KEYS

    return LEDGER_KEYS


def judge_case(case: dict[str, Any], arrays: dict[str, Any], timeline: dict[str, Any],
               params) -> dict[str, Any]:
    """Metrics and checks of one case (motion window = from the motion start)."""
    import numpy as np

    from outrigger_sim.verify import s8_v15 as v15

    refs = v15.load_reference(ROOT)
    dyn = v15.load_dynamic_check(ROOT)
    t = arrays["t_s"]
    t0 = timeline["motion_start_t_s"]
    m = t >= t0
    series = {k: a[m] for k, a in arrays.items() if a.shape[:1] == t.shape}
    f_min = params.control.F_min_cylinder_N
    lim = (np.zeros(4) if params.l2b.seal_friction is None
           else np.array([1.0, 1.0, params.l2b.seal_friction.rear_scale,
                          params.l2b.seal_friction.rear_scale]) * case["fs_N"])
    out: dict[str, Any] = {"F_min_N": f_min, "limits_N": lim.tolist()}
    led_cols = {k: series[k] for k in v15_ledger_keys() if k in series}
    ok = np.all(np.isfinite(np.column_stack(list(led_cols.values()))), axis=1)
    checks: list[Any] = []
    full = timeline.get("end_t_s") is not None
    if case["kind"] == "a":
        ma = v15.metrics_a(series, f_min, lim, fine_start_t_s=timeline.get("fine_start_t_s"))
        out["metrics"] = ma
        if ma.get("liftoff") is not None:
            checks += v15.judge_a(ma, v15.reference_a(refs, case["variant"], case["fs_N"]), lim)
            t_l = ma["liftoff"]["t_s"]
            df = float(np.interp(t_l, series["t_s"][ok], led_cols["D_f_J"][ok])
                       - led_cols["D_f_J"][ok][0])
        else:
            out["note"] = "no lift-off in the run (capped run or failure)"
            df = float(led_cols["D_f_J"][ok][-1] - led_cols["D_f_J"][ok][0])
    else:
        t_end = timeline["end_t_s"]
        # the "before" window lies in the hold before the motion start: use the full arrays
        mb = v15.metrics_b(arrays, f_min, t_start_s=t0, t_end_s=t_end, mean_s=MEAN_S)
        out["metrics"] = mb
        # 1 ms block mean of lam at the top sits up to v * block / 2 under +10 mm (rev. 42 fix:
        # the old 1e-6 mm test skipped every (b) residual row of v15_20261025_132215)
        if full and v15.round_trip_complete(mb, B_TARGET_M):
            checks += v15.judge_b(mb, v15.reference_b(refs, case["variant"], case["fs_N"]))
        else:
            out["note"] = "round trip not completed (capped run): residual not judged"
        df = float(led_cols["D_f_J"][ok][-1] - led_cols["D_f_J"][ok][0])
    ref_df = (v15.dynamic_df_J(dyn, case["variant"], case["fs_N"], case["kind"],
                               case["speed_m_s"]) if case["fs_N"] > 0 else None)
    out["D_f_J"] = df
    checks.append(v15.judge_df(df, ref_df, f"D_f ({case['kind']}) [J]"))
    out["ledger"] = v15.ledger_summary(series["t_s"][ok], {k: c[ok] for k, c in led_cols.items()},
                                       judged=case["fs_N"] > 0, dt_s=series["dt_s"][ok])
    checks += v15.judge_ledger(out["ledger"])  # L-2: ledger rows count in the summary
    out["judge_rule"] = "rev. 42 5.29.7 (A-1..A-4, L-1..L-2)"
    out["checks"] = [c.as_dict() for c in checks]
    out["summary"] = v15.summarize(checks)
    return out


def job(case_obj, case_dir: Path):
    """Batch job (module level, spawn)."""
    from outrigger_sim.batch import CaseResult
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    case = dict(case_obj.settings)
    wall0 = time.perf_counter()
    out = run_case(case, case_dir, cap_s=case.get("cap_s"))
    out["wall_s"] = time.perf_counter() - wall0
    out["placement"] = placement
    (case_dir / "result.json").write_text(json.dumps(out, indent=1, default=_plain),
                                          encoding="utf-8")
    return CaseResult(summary={"judge_summary": out["judge"]["summary"], "wall_s": out["wall_s"]},
                      run_meta=None)


def _plain(x: Any) -> Any:
    import numpy as np

    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    return str(x)


# --- actions ----------------------------------------------------------------------------------


def action_list(cost_us: float, with_head_only: bool) -> None:
    total = 0.0
    longest = 0.0
    for cid, c in case_table(with_head_only).items():
        sim, n1, n2 = simulated(c)
        wall = (n1 + n2) * cost_us * 1e-6
        total += wall
        longest = max(longest, wall)
        print(f"{cid:18s} sim {sim:7.1f} s  steps 1e-4 {n1:9.0f}  1e-5 {n2:8.0f}  "
              f"wall ~{wall / 60:6.1f} min")
    print(f"serial ~{total / 60:.1f} min at {cost_us:.0f} us/step; {MAX_JOBS} workers: makespan "
          f"~{max(total / MAX_JOBS, longest) / 60:.1f} min (longest case {longest / 60:.1f} min)")


def action_smoke(case_id: str, speed: float | None, cap: float | None, out_dir: Path) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    case = dict(case_table(True)[case_id])
    if speed is not None:
        case["speed_m_s"] = float(speed)
        case["smoke_speed_override"] = True
    out_dir.mkdir(parents=True, exist_ok=True)
    wall0 = time.perf_counter()
    out = run_case(case, out_dir, cap_s=cap)
    out["wall_s"] = time.perf_counter() - wall0
    out["placement"] = placement
    steps = sum(r["steps"] for r in out["runs"].values())
    run_wall = sum(r["wall_s"] for r in out["runs"].values())
    out["us_per_step_incl_record"] = run_wall / steps * 1e6
    (out_dir / "result.json").write_text(json.dumps(out, indent=1, default=_plain),
                                         encoding="utf-8")
    return out


def action_batch(ids: list[str] | None, jobs: int, out: Path, with_head_only: bool) -> None:
    from outrigger_sim.batch import Case, run_cases

    if jobs > MAX_JOBS:
        raise SystemExit(f"--jobs {jobs} > {MAX_JOBS}")
    table = case_table(True)
    chosen = ids or list(case_table(with_head_only))
    unknown = [c for c in chosen if c not in table]
    if unknown:
        raise SystemExit(f"unknown case ids {unknown}")
    cases = [Case(cid, table[cid]) for cid in chosen]
    cases.sort(key=lambda c: -sum(simulated(dict(c.settings))[1:]))
    report = run_cases(cases, job, out, max_workers=jobs, placement="pcore", timeout_s=None)
    for o in report.outcomes:
        print(f"{o.case_id:20s} {o.status}  {o.wall_s:8.1f} s  {(o.error or '')[:200]}")
    print("batch:", out)


def action_rejudge(batch: Path) -> None:
    """Recompute each case judge from ``series.npz`` + ``result.json`` (no Chrono run) and
    write ``<case>/judge.json``."""
    import numpy as np

    old, keep = batch / "v15_summary.json", batch / "v15_summary_v1.json"
    if old.exists() and not keep.exists():  # first rejudge: keep the rev. 39 summary
        old.replace(keep)
    for f in sorted(batch.glob("*/result.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        case = r["case"]
        with np.load(f.parent / "series.npz") as z:
            arrays = {k: z[k] for k in z.files}
        params, _ = _params(case)
        j = judge_case(case, arrays, r["timeline"], params)
        j["rejudged"] = {"date": _dt.datetime.now().isoformat(timespec="seconds"),
                         "from": "series.npz + result.json (timeline, case)",
                         "result_json_summary_before": r["judge"]["summary"]}
        (f.parent / "judge.json").write_text(json.dumps(j, indent=1, default=_plain),
                                             encoding="utf-8")
        print(f"{f.parent.name:18s} checks {j['summary']['n_checks']:3d}  "
              f"failed {j['summary']['n_failed']}")


def _case_judge(case_dir: Path, r: dict[str, Any]) -> dict[str, Any]:
    p = case_dir / "judge.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else r["judge"]


def action_judge(batch: Path) -> dict[str, Any]:
    from outrigger_sim.verify import s8_v15 as v15

    results = {}
    for f in sorted(batch.glob("*/result.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        r["judge"] = _case_judge(f.parent, r)
        results[f.parent.name] = r
    rows: dict[str, Any] = {}
    n_fail = 0
    n_checks = 0
    for cid, r in results.items():
        j = r["judge"]
        rows[cid] = {"summary": j["summary"], "metrics": j["metrics"], "D_f_J": j["D_f_J"],
                     "ledger": j["ledger"], "checks": j["checks"],
                     "judge_rule": j.get("judge_rule", "rev. 39 5.26.9 (before U-S8-48)")}
        n_fail += j["summary"]["n_failed"]
        n_checks += j["summary"]["n_checks"]
    speed: list[dict[str, Any]] = []
    for cid, c in case_table(True).items():
        if c.get("group") != "speed" or cid not in results or c["pair"] not in results:
            continue
        fast = results[c["pair"]]["judge"]["metrics"]
        slow = results[cid]["judge"]["metrics"]
        checks = (v15.judge_speed_a(fast, slow) if c["kind"] == "a"
                  else v15.judge_speed_b(fast, slow))
        speed += [x.as_dict() for x in checks]
        n_fail += sum(1 for x in checks if x.passed is False)
        n_checks += sum(1 for x in checks if x.passed is not None)
    out = {"batch": str(batch), "cases": rows, "speed_pair_checks": speed, "n_checks": n_checks,
           "n_failed": n_fail, "date": _dt.datetime.now().isoformat(timespec="seconds")}
    (batch / "v15_summary.json").write_text(json.dumps(out, indent=1, default=_plain),
                                            encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=("list", "smoke", "run", "judge", "rejudge"))
    ap.add_argument("--case", default="V15a_L4")
    ap.add_argument("--speed", type=float, default=None,
                    help="smoke only: FL speed override (code-path check, values not judged)")
    ap.add_argument("--cap", type=float, default=None, help="smoke: max time after the start [s]")
    ap.add_argument("--cost-us", type=float, default=420.0)
    ap.add_argument("--jobs", type=int, default=MAX_JOBS)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--with-head-only", action="store_true")
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--batch", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.action == "list":
        action_list(args.cost_us, args.with_head_only)
    elif args.action == "smoke":
        out = action_smoke(args.case, args.speed, args.cap,
                           args.out or RESULTS / f"v15_smoke_{stamp}")
        print(json.dumps({k: out[k] for k in ("timeline", "wall_s", "us_per_step_incl_record",
                                              "crawler_N_max", "nonfinite")}, indent=1,
                         default=_plain))
        print(json.dumps(out["judge"], indent=1, default=_plain)[:6000])
    elif args.action == "run":
        if not args.approved:
            raise SystemExit("V15 main run needs --approved (after the ML 768 batch)")
        action_batch(args.only, args.jobs, args.out or RESULTS / f"v15_{stamp}",
                     args.with_head_only)
    else:
        if args.batch is None:
            raise SystemExit(f"{args.action} needs --batch")
        if args.action == "rejudge":
            action_rejudge(args.batch)
        out = action_judge(args.batch)
        print(json.dumps({"n_checks": out["n_checks"], "n_failed": out["n_failed"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
