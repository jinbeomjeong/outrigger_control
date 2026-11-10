"""H-F: head-pressure jump detection with 1 kHz mean readings (ideal-sensor stage 1, plan 4.1
and 8.5 of ``06_analysis/03_hydraulic/coupled/v5/las/ideal/ideal_stage1_plan.md``).

Wraps ``r64_g4_closed_loop.py`` (imported, not copied: plant, G4 controller class "py" = the
project FAULT_REGROUND, ``judge``). Differences from that tool:

* the head-sensor jump enters per 1 ms chunk: a chunk-end reading whose time is past the arm
  time (``t_chunk > t_arm + 0.5 ms``, chunks on the 1 ms grid) carries ``+J`` on the faulty
  leg. The arm time is ``t_ev + floor(fault_after / T) T + phi`` (phase ``phi`` in the period),
  so with the mean reading the jump is split ``(1 - phi / T) J`` / ``(phi / T) J`` over two
  periods;
* two arms: ``base`` (the instantaneous period-end reading, as ``r64``) and ``S4`` (head and rod
  readings = the mean of the period's 100 chunk-end readings, from the start of the run);
* rows: 6 cases x phi {1, 20, 33, 50, 67, 90} ms x J {150, 250} bar x 2 arms = 144, event at
  the period grid (offset 0). One job per (case, arm): its base run, the RL lift time of the
  ``rl_mid`` cases (same arm, no fault), then per (phi, J) the FAULT_REGROUND-off run (G4-7) and
  the "py" run.

G-4 (plan 6 / 8.5):
  (ii) every ``base`` row is also run with the old injection (the jump added to the first
       10 Hz reading at or after the arm time, ``r64.simulate``); FAULT time and targets must
       be equal (``g4_ii`` per row);
  (i)  ``g4-old`` re-runs the stored 24-row configuration (``r64.run_job``, variant "py" only)
       and compares it with ``06_analysis/02_control/s8/rev64/r64_g4_closed_loop.json``
       (a difference after the preset changes is recorded, not a failure of this tool).

Tags: ``controller_tag`` of a row = ``v5_options.controller_tag(None, config)`` (base arm) or
that tag + ``_IDEAL-S4``.

Usage (dynamics-dev python.exe, project root, PowerShell, threads 1):
  python -I -B 04_scripts/03_control/s8/r64_g4_ideal_s4.py run [--out <json>] [--workers 12]
      [--affinity HEX] [--cases FS24_FR_Fs0,..] [--phases 1,50] [--jumps 150]
  python -I -B 04_scripts/03_control/s8/r64_g4_ideal_s4.py g4-old [--out <json>] [--workers 12]
      [--affinity HEX]
Default output ``06_analysis/03_hydraulic/coupled/v5/las/ideal/ideal_HF.json`` (new file only).
Exit codes: 0 done, 1 job errors or a G-4 (ii) difference, 2 input error (existing output).
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import dataclasses
import json
import math
import os
import sys
import time
import traceback
from multiprocessing import get_context
from pathlib import Path

for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402

PERIOD_S = 0.1
CHUNK_S = 0.001
PHASES_MS = (1, 20, 33, 50, 67, 90)
JUMPS_BAR = (150, 250)
ARMS = ("base", "S4")
PA_PER_BAR = 1e5
CHUNK_TIME_TOL_S = 0.5e-3
"""A chunk counts as after the arm time when its end time is more than half a chunk later."""
IDEAL_TAG_INFIX = "_IDEAL-"
HEAD_FAULT_EVENT = "FAULT_HEAD_PRESSURE"
HEAD_FAULT_REASON_EVENT = "INFO_HEAD_PRESSURE_FAULT_REASON"
VARIANT = "py"
OUT_PATH = (ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "las" / "ideal"
            / "ideal_HF.json")
STORED_R64_PATH = ROOT / "06_analysis" / "02_control" / "s8" / "rev64" / "r64_g4_closed_loop.json"
PLAN_SHA256_LIST = ("06c9c6b0e90db290b84a96523cbe0570ddcb1bb82d0d5277bb6037f06f260455",
                    "0d3bb1b80a357eeb2bf0a90382ca92f6674322517d721a149ca43f667598a189")


# ------------------------------------------------------------------------------- jump timing
def arm_time_s(t_ev: float, fault_after_s: float, phase_ms: float) -> float:
    """Arm time on the period grid of the branch: start of the period that holds the old arm
    time, plus the phase."""
    period_start = math.floor((fault_after_s + 1e-9) / PERIOD_S) * PERIOD_S
    return t_ev + period_start + phase_ms * 1e-3


def is_jump_active(t_chunk_s: float, t_arm_s: float | None) -> bool:
    return t_arm_s is not None and t_chunk_s > t_arm_s + CHUNK_TIME_TOL_S


def arm_period_index(t_ev: float, t_arm_s: float) -> int:
    """Index (from the branch start, 1 = first period after ``t_ev``) of the period whose
    reading first carries the jump."""
    return math.floor((t_arm_s - t_ev) / PERIOD_S + 1e-9) + 1


@dataclasses.dataclass(frozen=True)
class Jump:
    """One head-sensor jump: leg, size [Pa], arm time [s] (None: no jump)."""

    leg: int
    size_Pa: float
    t_arm_s: float | None


NO_JUMP = Jump(0, 0.0, None)


# ------------------------------------------------------------------------------- modules
@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


_MODULES: dict = {}


def r64():
    """``r64_g4_closed_loop`` (reads the project root from ``sys.argv[1]`` at import)."""
    if "r64" not in _MODULES:
        with _argv_as_root():
            import r64_g4_closed_loop

        _MODULES["r64"] = r64_g4_closed_loop
    return _MODULES["r64"]


# ------------------------------------------------------------------------------- readings
def chunk_reading(plant, head_area, jump: Jump) -> tuple[np.ndarray, np.ndarray]:
    """(head, rod) reading of one chunk end in the arithmetic of ``r64.with_two_pressures``."""
    net = plant.pressure()
    rod = np.asarray(plant.p_r0, float) - np.asarray(plant.Gr, float) / np.asarray(plant.A_ann,
                                                                                  float)
    head = (net + rod * plant.A_ann) / head_area
    if is_jump_active(float(plant.t), jump.t_arm_s):
        head = np.array(head, dtype=float)
        head[jump.leg] += jump.size_Pa
    return np.array(head, float), np.array(rod, float)


def period_readings(cl, measurements_cls, plant, cmd, valve, head_area, period_s, floor_fn,
                    rec, arm: str, jump: Jump):
    """One control period with the chunk readings; the measurements of the arm."""
    module = r64()
    chunks = []
    inner = cl._lagged_step

    def lagged_step(pl, command, valve_state, steps):
        accumulated = inner(pl, command, valve_state, steps)
        chunks.append(chunk_reading(pl, head_area, jump))
        return accumulated

    cl._lagged_step = lagged_step
    try:
        measurements = module.r51.control_period(cl, measurements_cls, plant, cmd, valve,
                                                 head_area, period_s, floor_fn, rec)
    finally:
        cl._lagged_step = inner
    two = module.with_two_pressures(plant, measurements, head_area)
    heads = np.array([head for head, _ in chunks])
    rods = np.array([rod for _, rod in chunks])
    if arm == "S4":
        return dataclasses.replace(two, head_pressure_Pa=heads.mean(axis=0),
                                   rod_pressure_Pa=rods.mean(axis=0))
    if not np.array_equal(rods[-1], two.rod_pressure_Pa):
        raise RuntimeError("chunk rod reading differs from with_two_pressures")
    return dataclasses.replace(two, head_pressure_Pa=heads[-1])


# ------------------------------------------------------------------------------- runs
def prepare_base(cl, c2, measurements_cls, fs_kN: float, arm: str):
    """``r64.prepare_base`` with the arm's readings (no jump)."""
    module = r64()
    r51 = module.r51
    base = r51._reg_base("b", "top", (0.0, 0.0), fs_kN, [])
    plant = r51.make_plant(cl, base)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                              with_reapproach=True)
    ctrl = module.make_controller_class(c2).from_params(cl.PARAMS, config)
    ctrl.reset()
    head_area = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    t_ready = t_lift = None
    while plant.t < r51.BASE_LIMIT_S:
        m = period_readings(cl, measurements_cls, plant, cmd, valve, head_area, ctrl.period_s,
                            None, None, arm, NO_JUMP)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if t_lift is None and plant.acc[15] == 0.0 and ctrl.phase is c2.C2Phase.LEVEL:
            t_lift = plant.t
        if ctrl.phase is c2.C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + module.EVENT_DELAY_S - 1e-9:
            break
    return plant, ctrl, cmd, valve, t_ready, t_lift


def simulate(cl, measurements_cls, plant, ctrl, cmd, valve, event, arm: str, jump_leg,
             fault_after_s, phase_ms, jump_Pa, run_s):
    """``r64.simulate`` with the chunk jump (offset 0); returns (rec, log, t_ev, events, t_arm)."""
    module = r64()
    t_ev = plant.t
    t_arm = None if jump_leg is None else arm_time_s(t_ev, fault_after_s, phase_ms)
    jump = NO_JUMP if jump_leg is None else Jump(jump_leg, jump_Pa, t_arm)
    first_event = len(ctrl.events)
    rec, log = [], []

    def floor_fn(pl_):
        if event is None:
            return
        tau = min(1.0, max(0.0, (pl_.t - t_ev) / event["ramp"]))
        pl_.goff[event["leg"]] = event["depth"] * (tau ** 3 * (10 - 15 * tau + 6 * tau ** 2))

    head_area = ctrl.geometry.head_area_m2
    while plant.t < t_ev + run_s - 1e-9:
        m = period_readings(cl, measurements_cls, plant, cmd, valve, head_area, ctrl.period_s,
                            floor_fn, rec, arm, jump)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        log.append(module.snapshot(ctrl, cmd))
    events = [(float(e.t_s), e.name) for e in ctrl.events[first_event:]]
    return np.array(rec), log, t_ev, events, t_arm


def _fault_record(events, t_ev: float, t_arm: float) -> dict:
    head_faults = [t for t, name in events if name.startswith(HEAD_FAULT_EVENT)]
    first = min(head_faults) if head_faults else None
    arm_index = arm_period_index(t_ev, t_arm)
    return {"t_arm_rel_s": round(t_arm - t_ev, 4), "arm_period": arm_index,
            "t_head_fault_rel_s": None if first is None else round(first - t_ev, 4),
            "head_fault_period": None if first is None else round((first - t_ev) / PERIOD_S),
            "delay_periods": None if first is None
            else round((first - t_ev) / PERIOD_S) - arm_index,
            "missed": first is None,
            "fault_reasons": [name for _, name in events
                              if name.startswith(HEAD_FAULT_REASON_EVENT)][:10]}


def _g4_ii(cl, measurements_cls, plant, ctrl, cmd, valve, case, t_arm, t_ev, jump_Pa,
           chunk_judge) -> dict:
    """G-4 (ii): the old injection at the same arm time, base arm."""
    module = r64()
    saved = module.HEAD_JUMP_PA
    module.HEAD_JUMP_PA = jump_Pa
    ctrl_old = copy.deepcopy(ctrl)
    ctrl_old.abort2 = VARIANT
    try:
        rec, log, t_ev_old, events = module.simulate(
            cl, measurements_cls, copy.deepcopy(plant), ctrl_old, cmd.copy(),
            valve.copy(), ctrl.geometry.head_area_m2, case["event"], 0.0, case["fault_leg"],
            t_arm - t_ev, module.RUN_AFTER_EVENT_S)
    finally:
        module.HEAD_JUMP_PA = saved
    meta_run = ctrl_old.meta()["fault_reground"]["run"]
    old_judge, _ = module.judge(rec, log, events, t_ev_old, case["fault_leg"], t_arm - t_ev,
                                meta_run, _geo(ctrl), ctrl.config.fault_reground.to_meta())
    keys = ("t_f_rel_s", "t_fault_rel_s", "targets", "true_targets")
    same = all(old_judge.get(key) == chunk_judge.get(key) for key in keys)
    return {"same": same, "old": {key: old_judge.get(key) for key in keys},
            "chunk": {key: chunk_judge.get(key) for key in keys}}


def _geo(ctrl) -> dict:
    g = ctrl.geometry
    return {"F_min": g.F_min_N, "stroke_soft": g.stroke_soft_max_m,
            "head_force_limit_N": (g.locked_force_limit_N
                                   - ctrl.config.thresholds.locked_pressure_warning_margin_Pa
                                   * g.head_area_m2)}


def controller_tags(config) -> tuple[str, dict[str, str]]:
    from outrigger_sim.hydraulics.v5_options import controller_tag

    base = controller_tag(None, config)
    return base, {"base": base, "S4": f"{base}{IDEAL_TAG_INFIX}S4"}


def run_case_arm(args) -> dict:
    """Worker: one (case, arm): its base run and every (phase, jump) row."""
    case_id, arm, phases, jumps = args
    t_start = time.perf_counter()
    try:
        return _run_case_arm(case_id, arm, phases, jumps, t_start)
    except Exception as exc:  # the batch records the failure
        return {"case": case_id, "arm": arm, "error": repr(exc),
                "tb": traceback.format_exc()[-3000:]}


def _run_case_arm(case_id: str, arm: str, phases, jumps, t_start: float) -> dict:
    module = r64()
    module.set_affinity_from_env()
    module.r51.place_worker()
    cl, c2, measurements_cls = module.r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    case = next(item for item in module.CASES if item["id"] == case_id)
    plant, ctrl, cmd, valve, t_ready, t_lift = prepare_base(cl, c2, measurements_cls,
                                                            module.BASES[case["base"]], arm)
    base_tag, tags = controller_tags(ctrl.config)
    head = {"case": case_id, "arm": arm, "controller_tag": tags[arm], "base_tag": base_tag,
            "t_ready_s": t_ready, "t_crawler_liftoff_s": t_lift}
    if t_ready is None or str(ctrl.phase) != "ready":
        return {**head, "error": f"no READY at the branch (phase {ctrl.phase})"}
    fault_after = case["fault"]
    if fault_after == "rl_mid":
        rec0, _, t_ev0, _, _ = simulate(cl, measurements_cls, copy.deepcopy(plant),
                                        copy.deepcopy(ctrl), cmd.copy(), valve.copy(),
                                        case["event"], arm, None, 0.0, 0, 0.0, 3.0)
        tt = rec0[:, 0] - t_ev0
        intervals = module.r51._intervals((rec0[:, 3] <= 0.0) & (tt >= 0.0), tt)
        fault_after = (0.5 * (intervals[0][0] + intervals[0][1]) if intervals
                       else module.FS24_FALLBACK_FAULT_S)
    settings = ctrl.config.fault_reground.to_meta()
    rows = []
    for phase_ms in phases:
        for jump_bar in jumps:
            rows.append(_row(cl, measurements_cls, plant, ctrl, cmd, valve, case, arm,
                             fault_after, phase_ms, jump_bar * PA_PER_BAR, settings, head))
    return {**head, "fault_after_event_s": round(fault_after, 4), "rows": rows,
            "wall_s": round(time.perf_counter() - t_start, 1)}


def _row(cl, measurements_cls, plant, ctrl, cmd, valve, case, arm, fault_after, phase_ms,
         jump_Pa, settings, head) -> dict:
    module = r64()
    geo = _geo(ctrl)
    ctrl_off = copy.deepcopy(ctrl)
    ctrl_off.config = dataclasses.replace(
        ctrl.config, fault_reground=dataclasses.replace(ctrl.config.fault_reground, enable=False))
    rec_off, log_off, t_ev, _, t_arm = simulate(
        cl, measurements_cls, copy.deepcopy(plant), ctrl_off, cmd.copy(), valve.copy(),
        case["event"], arm, case["fault_leg"], fault_after, phase_ms, jump_Pa,
        module.RUN_AFTER_EVENT_S)
    cmds_off = np.array([row["cmd"] for row in log_off])
    ctrl_on = copy.deepcopy(ctrl)
    ctrl_on.abort2 = VARIANT
    rec, log, t_ev, events, t_arm = simulate(
        cl, measurements_cls, copy.deepcopy(plant), ctrl_on, cmd.copy(), valve.copy(),
        case["event"], arm, case["fault_leg"], fault_after, phase_ms, jump_Pa,
        module.RUN_AFTER_EVENT_S)
    meta_run = ctrl_on.meta()["fault_reground"]["run"]
    fault = _fault_record(events, t_ev, t_arm)
    row = {**{key: head[key] for key in ("case", "arm", "controller_tag", "base_tag")},
           "phase_ms": phase_ms, "jump_bar": jump_Pa / PA_PER_BAR, **fault,
           "meta_run": meta_run,
           "events": [(round(t - t_ev, 3), name) for t, name in events
                      if not name.startswith(("INFO_PRESSURE", "shadow_"))][:60]}
    judged, _ = module.judge(rec, log, events, t_ev, case["fault_leg"], t_arm - t_ev, meta_run,
                             geo, settings, cmds_off)
    row["judge"] = judged
    if arm == "base":
        row["g4_ii"] = _g4_ii(cl, measurements_cls, plant, ctrl, cmd, valve, case, t_arm, t_ev,
                              jump_Pa, judged)
    return row


# ------------------------------------------------------------------------------- G-4 (i)
def run_old_job(job):
    """Worker of ``g4-old``: ``r64.run_job`` with the variant "py" only."""
    try:
        return r64().run_job(job)
    except Exception as exc:
        return {"case": job[0]["id"], "offset_s": job[1], "error": repr(exc)}


def g4_old_comparison(results: list[dict], stored: dict) -> list[dict]:
    """Per (case, offset): FAULT entry / FAULT time / targets of variant "py" against the
    stored summary."""
    stored_rows = {(row["case"], row["off"]): row for row in stored["summary"]
                   if row.get("var") == VARIANT}
    out = []
    for result in results:
        key = (result.get("case"), result.get("offset_s"))
        old = stored_rows.get(key)
        variant = (result.get("variants") or {}).get(VARIANT) or {}
        judged = variant.get("judge") or {}
        new = {"t_f": judged.get("t_f_rel_s"), "fault": judged.get("t_fault_rel_s"),
               "targets": judged.get("targets")}
        old_values = None if old is None else {name: old.get(name) for name in new}
        out.append({"case": key[0], "offset_s": key[1], "new": new, "stored": old_values,
                    "same": old_values == new, "error": result.get("error")})
    return out


# ------------------------------------------------------------------------------- CLI
def _set_parent_affinity(mask: str | None) -> None:
    if mask:
        os.environ["R64_AFFINITY"] = mask
        r64().set_affinity_from_env()


def _write_new(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1, default=float)


def _run_rows(args) -> int:
    module = r64()
    cases = args.cases.split(",") if args.cases else [case["id"] for case in module.CASES]
    phases = [float(v) for v in args.phases.split(",")] if args.phases else list(PHASES_MS)
    jumps = [float(v) for v in args.jumps.split(",")] if args.jumps else list(JUMPS_BAR)
    jobs = [(case, arm, phases, jumps) for case in cases for arm in ARMS]
    t_start = time.perf_counter()
    with get_context("spawn").Pool(min(args.workers, len(jobs)), maxtasksperchild=1) as pool:
        results = pool.map(run_case_arm, jobs, chunksize=1)
    rows = [row for result in results for row in result.get("rows", [])]
    errors = [{k: result.get(k) for k in ("case", "arm", "error", "tb")} for result in results
              if "error" in result]
    g4_ii = [row["g4_ii"]["same"] for row in rows if "g4_ii" in row]
    document = {"meta": {"script": "04_scripts/03_control/s8/r64_g4_ideal_s4.py",
                         "plan_sha256": list(PLAN_SHA256_LIST), "phases_ms": phases,
                         "jumps_bar": jumps, "arms": list(ARMS), "cases": cases,
                         "variant": VARIANT, "rows": len(rows),
                         "wall_s": round(time.perf_counter() - t_start, 1),
                         "workers": args.workers, "affinity": args.affinity,
                         "chunk_rule": "chunk end time > arm time + 0.5 ms"},
                "g4_ii": {"rows": len(g4_ii), "same": sum(g4_ii)},
                "errors": errors, "runs": [{k: v for k, v in result.items() if k != "rows"}
                                           for result in results],
                "rows": rows}
    _write_new(args.out, document)
    print(json.dumps({"rows": len(rows), "errors": len(errors),
                      "g4_ii_same": f"{sum(g4_ii)}/{len(g4_ii)}", "out": str(args.out)}))
    return 1 if errors or sum(g4_ii) != len(g4_ii) else 0


def _run_old(args) -> int:
    os.environ["R64_VARIANTS"] = VARIANT  # read by r64 at import (parent and workers)
    module = r64()
    jobs = [(case, offset) for case in module.CASES for offset in module.OFFSETS]
    with get_context("spawn").Pool(min(args.workers, len(jobs)), maxtasksperchild=1) as pool:
        results = pool.map(run_old_job, jobs, chunksize=1)
    stored = json.loads(STORED_R64_PATH.read_text(encoding="utf-8"))
    comparison = g4_old_comparison(results, stored)
    same = sum(row["same"] for row in comparison)
    _write_new(args.out, {"meta": {"stored": str(STORED_R64_PATH), "variant": VARIANT,
                                   "rows": len(comparison), "same": same},
                          "comparison": comparison})
    print(json.dumps({"rows": len(comparison), "same": same, "out": str(args.out)}))
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="the 144 H-F rows")
    run.add_argument("--out", type=Path, default=OUT_PATH)
    run.add_argument("--cases", default=None)
    run.add_argument("--phases", default=None, help="ms, comma-separated")
    run.add_argument("--jumps", default=None, help="bar, comma-separated")
    old = sub.add_parser("g4-old", help="G-4 (i): the stored 24-row configuration again")
    old.add_argument("--out", type=Path, default=OUT_PATH.with_name("ideal_HF_g4_old.json"))
    for command in (run, old):
        command.add_argument("--workers", type=int, default=12)
        command.add_argument("--affinity", default=None, help="hex mask (inherited)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.out.exists():
        print(f"input error: {args.out} exists (new files only)")
        print(json.dumps({"stop": "input", "reason": "output exists"}))
        return 2
    if args.command == "g4-old":
        os.environ["R64_VARIANTS"] = VARIANT
    _set_parent_affinity(args.affinity)
    return _run_old(args) if args.command == "g4-old" else _run_rows(args)


if __name__ == "__main__":
    sys.exit(main())
