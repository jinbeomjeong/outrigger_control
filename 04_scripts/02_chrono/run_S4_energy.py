"""S4 V8(b) energy budget: settled machine on its pads, large horizontal initial velocity
(ground-bushing yield, pad lift-off), damping and Coulomb yield on, 30 s.

``00_docs/03_chrono/chrono_build_plan.md`` S4 (V8(b), ``energy.*`` Record terms);
``dynamics_model.md`` 5 V8 (b); checks in ``outrigger_sim.verify.s4_energy``; energy terms in
``outrigger_sim.chrono.energy.EnergyBudget``. Usage (Chrono-dev python, from any folder)::

    python -I -u run_S4_energy.py run [--jobs 3] [--only NAME ...]   # cases + summary
    python -I -u run_S4_energy.py summary                            # rebuild the summary

Judged definitions: dyn rev. 19 (``verify.s4_energy`` docstring); ``summary`` recomputes every
check from the stored ``budget.npz`` tables.

Cases (L1, top, YAML damping, legs locked unless ``motor``):

* ``v8b_pitch2_dt2e-04`` (judged run): S2a V12 start of ``ground roll 0 deg, pitch 2 deg``
  (tilted floor, bushings at t = 0 with the initial hold, gravity 0 -> g half-cosine ramp
  3 s, settle 53 s, ``scenarios/slope``), then the initial velocity, 30 s budget.
* ``v8b_pitch2_dt1e-04``, ``v8b_pitch2_dt5e-05``: the same at dt 1e-4 s / 5e-5 s (settle
  included): time-step sensitivity (5e-5 s optional, about 10 min on one P-core).
* ``v8b_rollm2_pitch1.5_dt2e-04``: the combined slope of V12.
* ``v8b_flat_dt2e-04``: level floor, S1 settled snapshot (``S1_L1_top``).
* ``v8b_pitch2_motor_dt2e-04``: actuator model; all legs extend at ``v_max`` for 2 s from the
  kick (0.1 s command ramp), exercising the motor-work term.

Initial velocity (ASSUMPTION: size): a rigid translation of every body, 0.5 m/s along the
projection of world (0.8, 0.6, 0) onto the floor plane (no normal component, so the pads are
not hit into the floor). It needs about 3x the friction capacity ``mu W`` to stop the sway
mode elastically (``m v omega`` ~ 0.57 MN against 0.19 MN), so all four bushings yield; the
rocking it excites lifts pads (R15 events).

Outputs: ``07_results/S4_energy/batch_<stamp>/<case>/`` (case.json, result.json, Record with
the ``energy.*`` fields every 1 ms, ``budget.npz`` with the full budget table),
``07_results/S4_energy/index.json``; summary ``06_analysis/01_chrono/14_S4/
verify_S4_L1_energy.json`` and ``verify_S4_L1_energy.png``. Units SI (J, m, s, N).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S4_energy"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states"
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "14_S4"
SUMMARY = ANALYSIS_DIR / "verify_S4_L1_energy.json"
FIGURE = ANALYSIS_DIR / "verify_S4_L1_energy.png"
LEVEL = "top"
S1_SNAPSHOT = "S1_L1_top"
MAX_WORKERS = 3
"""Main-session rule for this branch: at most 3 Chrono processes (branch A uses 4)."""
CASE_TIMEOUT_S = 1800.0
WINDOW_S = 30.0
"""Budget window after the kick (plan cost table S4 V8(b): 30 s)."""
SAMPLE_S = 1.0e-3
KICK_SPEED_M_S = 0.5
"""ASSUMPTION: initial horizontal speed (module docstring)."""
KICK_DIRECTION = (0.8, 0.6, 0.0)
MOTOR_EXTEND_S = 2.0
"""Motor case: all legs at +v_max for this long after the kick."""
SERIES_POINTS = 1500
JUDGED_CASE = "v8b_pitch2_dt2e-04"
DT_SERIES = ("v8b_pitch2_dt5e-05", "v8b_pitch2_dt1e-04", "v8b_pitch2_dt2e-04")
"""Same case at dt, 2 dt, 4 dt (5e-5 is optional, P-core 1 process, about 10 min)."""

SLOPE_PITCH2 = "ground roll 0 deg, pitch 2 deg"
SLOPE_COMBINED = "ground roll -2 deg, pitch 1.5 deg"
CASES = {
    "v8b_pitch2_dt2e-04": {"floor": SLOPE_PITCH2, "dt": 2.0e-4, "motor": False},
    "v8b_pitch2_dt1e-04": {"floor": SLOPE_PITCH2, "dt": 1.0e-4, "motor": False},
    "v8b_pitch2_dt5e-05": {"floor": SLOPE_PITCH2, "dt": 5.0e-5, "motor": False},
    "v8b_rollm2_pitch1.5_dt2e-04": {"floor": SLOPE_COMBINED, "dt": 2.0e-4, "motor": False},
    "v8b_flat_dt2e-04": {"floor": None, "dt": 2.0e-4, "motor": False},
    "v8b_pitch2_motor_dt2e-04": {"floor": SLOPE_PITCH2, "dt": 2.0e-4, "motor": True},
}


def _plain(value):
    import numpy as np

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _thin(n_points, *arrays):
    step = max(1, len(arrays[0]) // n_points)
    return [a[::step] for a in arrays]


# --- start states ------------------------------------------------------------------------------


def _settled_slope(params, refs, slope_case, dt, actuator):
    """S2a V12 procedure (``run_S2a.run_v12`` without the V13 still window)."""
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.chrono.runs import run_gravity_ramp
    from outrigger_sim.chrono.system import gravity_vector, set_gravity
    from outrigger_sim.scenarios.slope import RAMP_S, gravity_ramp, settle_after_ramp_s, slope_start

    st = slope_start(params, refs, slope_case)
    model = L1Model(
        params,
        pose=BodyPose(st.body_origin_m),
        extensions_m=st.extensions_m,
        attach_bushings=False,
        floor_pose=BodyPose(st.floor_pos_m, st.floor_quat_wxyz),
        dt_s=dt,
        actuator=actuator,
    )
    model.bushing.attach(hold_until_loaded=True)
    g_full = gravity_vector(params)
    set_gravity(model.system, (0.0, 0.0, 0.0))
    settle_s = settle_after_ramp_s(params)
    total = RAMP_S + settle_s
    t0 = time.perf_counter()
    run = run_gravity_ramp(
        model, g_full, gravity_ramp, total, fine_from_s=total + 1.0, hold_deadline_s=RAMP_S
    )
    info = {
        "procedure": "S2a V12: bushings at t = 0 (initial hold), gravity half-cosine ramp, settle",
        "slope_case": slope_case,
        "ramp_s": RAMP_S,
        "settle_after_ramp_s": settle_s,
        "settle_steps": run.steps,
        "settle_wall_s": time.perf_counter() - t0,
        "settle_events": len(run.events),
        "settle_yield_steps": model.bushing.yield_steps.tolist(),
        "hold_release_t_s": model.bushing.hold_release_t_s.tolist(),
        "normal_world": list(st.normal_world),
        "extensions_m": list(st.extensions_m),
    }
    return model, np.asarray(st.normal_world, dtype=float), info


def _settled_flat(params, refs, dt, actuator):
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(
        params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt, actuator=actuator
    )
    snap = load_snapshot(S1_SNAPSHOT, params_sha256=params.sha256, directory=STATES)
    t_restored = model.restore(snap)
    info = {"procedure": f"S1 snapshot {S1_SNAPSHOT} (level floor)", "t_restored_s": t_restored}
    return model, np.array([0.0, 0.0, 1.0]), info


# --- job ---------------------------------------------------------------------------------------


def analyse_budget(cols):
    """``(R(t), remainder(t), budget_summary)`` of a budget table (columns by name); the
    remainder is ``R`` minus every diagnostic share present (older tables lack two)."""
    from outrigger_sim.verify.s4_energy import DIAGNOSTIC_TERMS, budget_summary, residual_series

    r = residual_series(cols)
    remainder = r.copy()
    for k in DIAGNOSTIC_TERMS:
        if k in cols:
            remainder = remainder - (cols[k] - cols[k][0])
    return r, remainder, budget_summary(cols["t_s"], cols)


def job(case, case_dir):
    """Batch job (module level for spawn)."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.energy import BUDGET_FIELDS, EnergyBudget, budget_table
    from outrigger_sim.chrono.runs import set_rigid_velocity
    from outrigger_sim.params import load_params
    from outrigger_sim.record import Recorder, make_run_meta, save_record
    from outrigger_sim.signals import Command
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s4_energy import slip_ratio, v8b_checks

    case_dir = Path(case_dir)
    s = case.settings
    dt = float(s["dt"])
    motor = bool(s["motor"])
    params = load_params(level=LEVEL)
    refs = load_references()
    t_build = time.perf_counter()
    if s["floor"] is None:
        model, normal, start = _settled_flat(params, refs, dt, motor)
    else:
        model, normal, start = _settled_slope(params, refs, s["floor"], dt, motor)
    start["build_and_settle_wall_s"] = time.perf_counter() - t_build
    probe0 = model.probe()
    start["pad_normal_before_kick_N"] = probe0.pad_normal_force_N.tolist()
    start["bushing_tangential_before_kick_N"] = np.linalg.norm(
        probe0.bushing_force_world_N, axis=1
    ).tolist()

    # kick: rigid translation in the floor plane
    d = np.asarray(KICK_DIRECTION, dtype=float)
    d = d - (d @ normal) * normal
    v_kick = KICK_SPEED_M_S * d / np.linalg.norm(d)
    cog = model.superstructure.GetPos()
    set_rigid_velocity(model, v_kick, (0.0, 0.0, 0.0), (cog.x, cog.y, cog.z))
    budget = EnergyBudget(model)
    gb = model.bushing
    yield0 = gb.yield_steps.copy()
    slip0 = gb.slip_total_m.copy()
    events0 = len(gb.events)

    v_max = float(model.actuator.max_speed_m_s) if motor else 0.0
    settings = {
        "case": case.case_id,
        "floor": s["floor"] or "level",
        "dt_s": dt,
        "window_s": WINDOW_S,
        "sample_s": SAMPLE_S,
        "kick_velocity_m_s": v_kick.tolist(),
        "kick_speed_m_s": KICK_SPEED_M_S,
        "motor": {"extend_all_legs_m_s": v_max, "for_s": MOTOR_EXTEND_S} if motor else None,
        "budget": "chrono.energy.EnergyBudget (S4 seven terms), residual verify.s4_energy",
    }
    run_meta = make_run_meta(
        params,
        model.meta(),
        scenario="S4_V8b_energy_budget",
        scenario_settings=settings,
        reference_sha256=refs.sha256_by_file(),
        extra={"start": _plain(start)},
    )
    recorder = Recorder(run_meta)

    def command_now(t_s):
        u = np.zeros(4) if model.actuator is None else model.actuator.command_m_s
        return Command(t_s=t_s, leg_speed_m_s=u)

    rows = [budget.read()]
    probe_kick = model.probe()  # state at t0 with the initial velocity
    recorder.append(model.truth(probe_kick), command_now(rows[0].t_s),
                    energy=rows[0].record_terms())
    n_steps = round(WINDOW_S / dt)
    every = max(1, round(SAMPLE_S / dt))
    stop_motor_at = round(MOTOR_EXTEND_S / dt)
    if motor:
        model.set_command(np.full(4, v_max))
    t_run = time.perf_counter()
    for k in range(1, n_steps + 1):
        if motor and k == stop_motor_at + 1:
            model.set_command(np.zeros(4))
        res = model.step(capture=(k % every == 0))
        budget.after_step(model.dt_s)
        if res.probe is not None:
            e = budget.read()
            rows.append(e)
            recorder.append(model.truth(res.probe), command_now(res.probe.t_s),
                            energy=e.record_terms())
    run_wall = time.perf_counter() - t_run
    window_events = list(gb.events)[events0:]
    for e in window_events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    record_path = save_record(recorder.finish(), case_dir / "record", overwrite=True)

    table = budget_table(rows)
    np.savez_compressed(case_dir / "budget.npz", table=table, columns=np.array(BUDGET_FIELDS))
    cols = {name: table[:, i] for i, name in enumerate(BUDGET_FIELDS)}
    t = cols["t_s"]
    r, remainder, summ = analyse_budget(cols)
    d_slip = float(cols["dissipated_slip"][-1] - cols["dissipated_slip"][0])
    coulomb = float(cols["slip_coulomb_work"][-1] - cols["slip_coulomb_work"][0])
    yield_window = (gb.yield_steps - yield0).tolist()
    checks = v8b_checks(
        case.case_id,
        residual_max_signed_J=summ["residual_max_signed_J"],
        residual_end_J=summ["residual_end_J"],
        dissipation_end_J=summ["dissipation_end_J"],
        e_ref_J=summ["E_ref_J"],
        slip_dissipation_J=d_slip,
        coulomb_work_J=coulomb,
        yield_steps=yield_window,
        crawler_contact_max_N=budget.crawler_contact_max_N,
    )
    kinds = [e.kind for e in window_events]
    from outrigger_sim.chrono.ground_bushing import EVENT_CREATE, EVENT_REMOVE

    tt, rr, kin, mech, dv, ds, wm, rem = _thin(
        SERIES_POINTS, t, r, cols["kinetic"],
        cols["kinetic"] + cols["gravity"] + cols["contact_spring"] + cols["bushing_spring"]
        - (cols["kinetic"][0] + cols["gravity"][0] + cols["contact_spring"][0]
           + cols["bushing_spring"][0]),
        cols["dissipated_viscous"], cols["dissipated_slip"], cols["motor_work"], remainder)
    dev_t, dev_leg = budget.contact_force_check_max_at
    summary = {
        "case": case.case_id,
        "settings": settings,
        "start": start,
        "budget": summ,
        "slip_ratio": slip_ratio(d_slip, coulomb),
        "slip_excess_J": d_slip - coulomb,
        "residual_remainder_max_abs_J": float(np.max(np.abs(remainder))),
        "bushing": {
            "yield_steps_window": yield_window,
            "yield_steps_total_window": int(np.sum(yield_window)),
            "slip_window_m": np.linalg.norm(gb.slip_total_m - slip0, axis=1).tolist(),
            "events_window": len(window_events),
            "created_window": int(sum(1 for k in kinds if k == EVENT_CREATE)),
            "removed_window": int(sum(1 for k in kinds if k == EVENT_REMOVE)),
            "events_per_leg_window": [int(sum(1 for e in window_events if e.leg == i))
                                      for i in range(4)],
            "events_window_list": [[e.t_s, e.leg, e.kind] for e in window_events],
            "in_contact_end": gb.in_contact.tolist(),
        },
        "consistency": {
            "pad_contact_force_model_max_dev_N": budget.contact_force_check_max_N,
            "pad_contact_force_model_max_dev_t_s": dev_t,
            "pad_contact_force_model_max_dev_leg": dev_leg,
            "crawler_contact_max_N": budget.crawler_contact_max_N,
            "pad_contact_damping_N_s_m": list(budget.pad_contact_damping_N_s_m),
            "bushing_damping_actual_N_s_m": list(budget.bushing_damping_actual_N_s_m),
            "steps": budget.steps,
        },
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "series": {"t_s": tt, "residual_J": rr, "kinetic_J": kin, "mech_change_J": mech,
                   "D_visc_J": dv, "D_slip_J": ds, "W_motor_J": wm, "remainder_J": rem},
        "record": _rel(record_path),
        "budget_table": _rel(case_dir / "budget.npz"),
        "timing": {"run_wall_s": run_wall, "us_per_step": run_wall / n_steps * 1e6,
                   "build_and_settle_wall_s": start["build_and_settle_wall_s"]},
    }
    summary = _plain(summary)
    (case_dir / "result.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                                          encoding="utf-8")
    return CaseResult(summary={k: summary[k] for k in ("case", "budget", "slip_ratio",
                                                       "all_passed")}, run_meta=run_meta)


# --- batch driver and summary ---------------------------------------------------------------


def run_batch(ids, jobs):
    from outrigger_sim.batch import Case, run_cases

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    order = sorted(ids, key=lambda c: (0 if "5e-05" in c else 1 if "1e-04" in c else 2, c))
    cases = [Case(c, CASES[c]) for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CASE_TIMEOUT_S)
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += f"\n{(o.error or '')[-2500:]}"
        print(msg, flush=True)
    wall = time.perf_counter() - t0
    print(f"batch wall {wall:.1f} s -> {_rel(batch_dir)}", flush=True)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        if o.status == "ok":
            index[o.case_id] = {"dir": _rel(batch_dir / o.case_id), "wall_s": o.wall_s,
                                "batch_wall_s": wall, "jobs": jobs}
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    return report


def _load_case(cid, entry):
    import numpy as np

    d = ROOT / entry["dir"]
    r = json.loads((d / "result.json").read_text(encoding="utf-8"))
    z = np.load(d / "budget.npz")
    cols = {str(n): z["table"][:, i] for i, n in enumerate(z["columns"])}
    return r, cols


def summarize():
    """Judged summary (dyn rev. 19 definitions) from the stored case results and budget tables
    (no Chrono run)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s4_energy import (
        DIAGNOSTIC_TERMS,
        V8B_CREATION_REL_MAX,
        V8B_DT_RATIO_BAND,
        V8B_END_LOSS_FRACTION_MAX,
        V8B_RICHARDSON_REL_MAX,
        V8B_SLIP_RATIO_BAND,
        dt_ratio_record,
        slip_ratio,
        v8b_checks,
        v8b_pair_checks,
    )

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    res, budgets, series = {}, {}, {}
    for cid, entry in index.items():
        if not (ROOT / entry["dir"] / "budget.npz").exists():
            continue
        r, cols = _load_case(cid, entry)
        rr, remainder, summ = analyse_budget(cols)
        d_slip = float(cols["dissipated_slip"][-1] - cols["dissipated_slip"][0])
        coulomb = float(cols["slip_coulomb_work"][-1] - cols["slip_coulomb_work"][0])
        checks = v8b_checks(
            cid,
            residual_max_signed_J=summ["residual_max_signed_J"],
            residual_end_J=summ["residual_end_J"],
            dissipation_end_J=summ["dissipation_end_J"],
            e_ref_J=summ["E_ref_J"],
            slip_dissipation_J=d_slip,
            coulomb_work_J=coulomb,
            yield_steps=r["bushing"]["yield_steps_window"],
            crawler_contact_max_N=r["consistency"]["crawler_contact_max_N"],
        )
        res[cid] = {
            "dir": entry["dir"],
            "judged": cid == JUDGED_CASE,
            "settings": r["settings"],
            "budget": summ,
            "slip_ratio": slip_ratio(d_slip, coulomb),
            "slip_excess_J": d_slip - coulomb,
            "residual_remainder_max_abs_J": float(np.max(np.abs(remainder))),
            "bushing": {k: v for k, v in r["bushing"].items() if k != "events_window_list"},
            "bushing_events_window": r["bushing"].get("events_window_list"),
            "consistency": r["consistency"],
            "start": r["start"],
            "checks": summary_table(checks),
            "all_passed": all_passed(checks),
            "timing": r["timing"] | {k: entry[k] for k in ("wall_s", "batch_wall_s", "jobs")
                                     if k in entry},
            "record": r["record"],
        }
        budgets[cid] = summ
        series[cid] = (cols["t_s"] - cols["t_s"][0], rr, remainder, cols, r["settings"]["dt_s"])

    # dt series of the same case: pair checks (2), (3) and recorded ratios of every share
    present = [c for c in DT_SERIES if c in res]
    dt_doc = None
    pair_checks = []
    if len(present) >= 2:
        by_dt = {res[c]["settings"]["dt_s"]: c for c in present}
        e_ref = max(budgets[c]["E_ref_J"] for c in present)
        for small in sorted(by_dt):
            large = next((d for d in by_dt if np.isclose(d, 2.0 * small, rtol=1e-9)), None)
            if large is None:
                continue
            pair_checks += v8b_pair_checks(
                "v8b_pitch2", dt_s=small,
                residual_end_dt_J=budgets[by_dt[small]]["residual_end_J"],
                residual_end_2dt_J=budgets[by_dt[large]]["residual_end_J"],
                e_ref_J=e_ref,
            )

        def share(c, name):
            return budgets[c]["diagnostics_end_J"].get(name, float("nan"))

        dt_doc = {
            "cases": present,
            "E_ref_J_used_for_check_3": e_ref,
            "residual_end_J": dt_ratio_record({d: budgets[c]["residual_end_J"]
                                               for d, c in by_dt.items()}),
            "shares": {name: dt_ratio_record({d: share(c, name) for d, c in by_dt.items()})
                       for name in DIAGNOSTIC_TERMS},
            "remainder_end_J": dt_ratio_record({d: budgets[c]["remainder_end_J"]
                                                for d, c in by_dt.items()}),
            "slip_ratio": {d: res[c]["slip_ratio"] for d, c in by_dt.items()},
            "residual_early_over_end": {d: budgets[c]["residual_early_over_end"]
                                        for d, c in by_dt.items()},
            "checks": summary_table(pair_checks),
            "all_passed": all_passed(pair_checks),
        }
    every = [c for r in res.values() for c in r["checks"]]
    doc = {
        "stage": "S4 V8(b) energy budget (cad pre-check with the dyn rev. 19 definitions; "
                 "dyn final ruling 2026-10-21: pass, dynamics_model.md 5.8)",
        "generated_utc": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "definitions": {
            "residual": "R(t) = (E_mech(t) - E_mech(t0)) + D_visc + D_slip - W_motor, "
                        "E_mech = kinetic + gravity + pad contact springs 1/2 kn delta^2 "
                        "(geometric) + bushing springs 1/2 kt |d|^2 (after the return mapping)",
            "E_ref": "max(E_kin(t0), D_visc,end + D_slip,end) (motor work excluded)",
            "check_1": f"max_t R <= {V8B_CREATION_REL_MAX} E_ref (every case)",
            "check_4": f"R_end <= 0 and |R_end| <= {V8B_END_LOSS_FRACTION_MAX} "
                       "(D_visc + D_slip) (every case)",
            "check_5": f"D_slip / sum mu N |delta a| in {list(V8B_SLIP_RATIO_BAND)} (every case)",
            "check_2": f"R_end(2 dt) / R_end(dt) in {list(V8B_DT_RATIO_BAND)} (dt pairs)",
            "check_3": f"|2 R_end(dt) - R_end(2 dt)| <= {V8B_RICHARDSON_REL_MAX} E_ref "
                       "(dt pairs)",
            "recorded": "old max |R| / (E_kin0 + max |W_m|); shares bushing_lag "
                        "(-sum kt (a_new - a_used).dp), bushing_implicit (-sum 1/2 kt |dp|^2), "
                        "kinetic_implicit (-sum 1/2 dv^T M dv), contact_explicit "
                        "(+sum 1/2 kn d_delta^2), remainder = R - shares; R(0.25 s) / R_end; "
                        "bushing events",
            "D_visc": "SMC pads c_n delta_dot_n (delta_n+1 - delta_n) (explicit, clip) + "
                      "bushings c_t,actual |v_t|^2 dt (c_t,actual = 2 x Chrono input, while on)",
            "D_slip": "sum 1/2 kt (|d_trial|^2 - |d|^2) per yielding return mapping",
            "W_motor": "sum F_cyl,n+1 (s_n+1 - s_n)",
            "kick": f"{KICK_SPEED_M_S} m/s rigid translation along the floor-plane projection "
                    f"of {list(KICK_DIRECTION)} (ASSUMPTION)",
        },
        "judged_case": JUDGED_CASE,
        "all_passed": bool(all(c["passed"] for c in every) and (dt_doc is None
                                                                  or dt_doc["all_passed"])),
        "dt_sensitivity": dt_doc,
        "cases": res,
    }
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(_plain(doc), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"summary -> {_rel(SUMMARY)}")

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    if JUDGED_CASE in series:
        t, rr, rem, cols, _ = series[JUDGED_CASE]
        mech = cols["kinetic"] + cols["gravity"] + cols["contact_spring"] + cols["bushing_spring"]
        curves = (("kinetic", cols["kinetic"]), ("E_mech - E_mech,0", mech - mech[0]),
                  ("D_visc", cols["dissipated_viscous"]), ("D_slip", cols["dissipated_slip"]),
                  ("W_motor", cols["motor_work"]))
        for ax, t_max, title in ((axes[0, 0], None, "energy terms"),
                                 (axes[0, 1], 2.0, "first 2 s (yield phase)")):
            m = slice(None) if t_max is None else t <= t_max
            for label, y in curves:
                ax.plot(t[m], np.asarray(y)[m] / 1e3, label=label)
            ax.set_xlabel("time after kick [s]")
            ax.set_ylabel("energy [kJ]")
            ax.set_title(f"{JUDGED_CASE}: {title}")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
    ax = axes[1, 0]
    for cid in sorted(series):
        t, rr, _, _, _ = series[cid]
        ax.plot(t, 100.0 * rr / budgets[cid]["E_ref_J"], label=cid)
    ax.axhline(100 * V8B_CREATION_REL_MAX, color="k", lw=0.8, ls="--")
    ax.set_xlabel("time after kick [s]")
    ax.set_ylabel("residual R / E_ref [%]")
    ax.set_title("energy residual (dashed: creation limit +0.1 %; R < 0 = loss)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax = axes[1, 1]
    for cid in DT_SERIES:
        if cid not in series:
            continue
        t, rr, rem, _, dt = series[cid]
        ax.plot(t, rr * (1e-4 / dt), label=f"R x (1e-4 / dt), dt {dt:.0e} s")
        ax.plot(t, rem * (1e-4 / dt), ls=":", label=f"remainder x (1e-4 / dt), dt {dt:.0e} s")
    ax.set_xlabel("time after kick [s]")
    ax.set_ylabel("residual scaled to dt 1e-4 s [J]")
    ax.set_title("dt sensitivity (overlap = first order in dt; remainder = R - shares)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=110)
    print(f"figure -> {_rel(FIGURE)}")



def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--jobs", type=int, default=MAX_WORKERS)
    p_run.add_argument("--only", nargs="*", default=None)
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "run":
        ids = list(CASES) if not a.only else a.only
        unknown = [c for c in ids if c not in CASES]
        if unknown:
            raise SystemExit(f"unknown cases {unknown}")
        if a.jobs > MAX_WORKERS:
            raise SystemExit(f"--jobs {a.jobs} > {MAX_WORKERS} (branch rule)")
        run_batch(ids, a.jobs)
        summarize()
    else:
        summarize()


if __name__ == "__main__":
    main()
