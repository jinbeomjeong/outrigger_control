"""S5 runs: auger three levels -- V0 (auger composition) and V10 (V1 + rocking modes 1-2).

``00_docs/03_chrono/chrono_build_plan.md`` S5; checks in ``outrigger_sim.verify.s5``.
Usage (Chrono-dev python, from any folder)::

    python -I -X utf8 -u run_S5.py run     [--jobs 6] [--only CASE ...]  # batch + summary
    python -I -X utf8 -u run_S5.py summary                               # rebuild the summary
    python -I -X utf8 -u run_S5.py list

Cases (L1, locked legs, YAML ``simulation.L1.dt_s``; every case restores the S1 settled state
``07_results/states/S1_L1_<level>`` (R16, refused if its ``params_sha256`` differs)):

* ``v1_<level>``: continue 10 s + still window 5 s (the S1 procedure, plan cost table "V1
  15 s"); V1 = still-window mean pad contact force per leg (0.1 % W/4).
* ``<level>_roll`` / ``<level>_pitch``: rigid initial angular velocity about world x / y
  through the level mode-shape reference point (``verify.s4.EXCITATIONS``: 0.02 deg x 2 pi f of
  the level reference mode 1 / 2), free vibration 20 s. Modes 1-2 identified by projection on
  the level ``V7_ball_centre_bushing_rev13 / mode_shapes`` (damped-cosine fit) with the
  6-channel ERA as cross-check (``run_S4.identify``, ``verify.s4.judged_value``).

V0 (auger) needs no simulation (YAML only) and is evaluated in the summary.
Outputs: ``07_results/S5/batch_<stamp>/<case>/`` (case.json, case.log, result.json,
series.npz; V1 cases 100 Hz from the next run on), ``07_results/S5/index.json``, ``07_results/S5/batches.json``; summary
``06_analysis/01_chrono/15_S5/verify_S5_L1.json``, figures ``verify_S5_L1.png`` (frequencies
vs reference) and ``verify_S5_L1_loads.png`` (V1 load table).
Units SI; angles in deg where named ``*_deg``; frequencies Hz.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path

# One BLAS thread per case process (set before numpy loads; spawned cases inherit it): six
# cases share the P-core mask, a multi-threaded OpenBLAS SVD / eig would slow all of them.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import run_S4 as _s4  # noqa: E402  (identification and JSON helpers of S4 branch A)

RESULTS = ROOT / "07_results" / "S5"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states"
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "15_S5"
SUMMARY = ANALYSIS_DIR / "verify_S5_L1.json"
FIGURE = ANALYSIS_DIR / "verify_S5_L1.png"
LOAD_FIGURE = ANALYSIS_DIR / "verify_S5_L1_loads.png"
PDELTA_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s1_pdelta_check.json"
"""dyn independent nonlinear statics per level (P-delta share of Chrono - linear reference)."""
MAX_WORKERS = 8
"""P-core count of the host (i7-14700: 8 P-cores); the default batch uses 6."""
DEFAULT_JOBS = 6
CASE_TIMEOUT_S = 1200.0
SAMPLE_S = 1.0e-3
COARSE_SAMPLE_S = 1.0e-2
V1_SETTLE_S = 10.0
V1_STILL_S = 5.0
V1_SERIES_SAMPLE_S = 1.0e-2
"""V1 cases store a 100 Hz series.npz (t, pad contact force x4, cylinder force x4, roll /
pitch, motor constraint violation); added after batch_20261021_173430 (dyn rev. 22)."""
LEGS = ("FL", "FR", "RL", "RR")


def _levels():
    from outrigger_sim.params import load_params

    return tuple(load_params().get("superstructure.auger_level_order"))


def case_ids() -> list[str]:
    from outrigger_sim.verify.s5 import V10_EXCITATIONS

    out = []
    for lv in _levels():
        out += [f"{lv}_{e}" for e in V10_EXCITATIONS]
    out += [f"v1_{lv}" for lv in _levels()]
    return out


def case_settings(case_id: str) -> dict:
    from outrigger_sim.params import load_params

    if case_id.startswith("v1_"):
        level = case_id.removeprefix("v1_")
        kind, exc = "v1", None
    else:
        level, _, exc = case_id.partition("_")
        kind = "modes"
    if level not in _levels():
        raise SystemExit(f"unknown case {case_id!r}")
    dt = float(load_params(level=level).simulation.L1.dt_s)
    return {"kind": kind, "level": level, "exc": exc, "dt": dt,
            "start": f"snapshot S1_L1_{level}"}


# --- jobs ---------------------------------------------------------------------------------------


def _restored_model(params, refs, level, dt):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt, actuator=False)
    snap = f"S1_L1_{level}"
    t0 = model.restore(load_snapshot(snap, params_sha256=params.sha256, directory=STATES))
    return model, t0, {"kind": f"snapshot {snap}", "t_s": t0, "params_sha256": params.sha256}


def _run_meta(params, model, scenario, settings):
    from outrigger_sim.record import make_run_meta
    from outrigger_sim.verify.reference import load_references

    return make_run_meta(params, model.meta(), scenario=scenario, scenario_settings=settings,
                         reference_sha256=load_references().sha256_by_file(), extra={})


def job_v1(case, case_dir):
    """Restore the S1 state, continue 10 s, still window 5 s: V1 / V2 / V3 / V13."""
    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.model import run_settle
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s1 import v1_v3_checks, v13_checks

    s = dict(case.settings)
    params = load_params(level=s["level"])
    refs = load_references()
    import numpy as np

    from outrigger_sim.frames import roll_pitch_from_quat

    model, t0, start = _restored_model(params, refs, s["level"], float(s["dt"]))
    rows = {"t": [], "contact": [], "cylinder": [], "roll_pitch": [], "violation": []}
    last_tick = [None]

    def sample(probe):
        # 100 Hz record (V1_SERIES_SAMPLE_S): the settle samples every 10 ms, the still window
        # every 1 ms; keep the first sample of each 10 ms tick
        tick = round((probe.t_s - t0) / V1_SERIES_SAMPLE_S)
        if tick == last_tick[0]:
            return
        last_tick[0] = tick
        rows["t"].append(probe.t_s - t0)
        rows["contact"].append(np.array(probe.pad_normal_force_N, dtype=float))
        rows["cylinder"].append(np.array(probe.motor_force_N, dtype=float))
        rows["roll_pitch"].append(np.degrees(roll_pitch_from_quat(probe.body_quat_wxyz)))
        rows["violation"].append(float(np.abs(probe.leg_offset_in_body_m).max()))

    run = run_settle(model, V1_SETTLE_S, V1_STILL_S, coarse_sample_s=COARSE_SAMPLE_S,
                     fine_sample_s=SAMPLE_S, on_sample=sample)
    np.savez_compressed(Path(case_dir) / "series.npz", t_s=np.asarray(rows["t"]),
                        pad_contact_N=np.asarray(rows["contact"]),
                        cylinder_force_N=np.asarray(rows["cylinder"]),
                        roll_pitch_deg=np.asarray(rows["roll_pitch"]),
                        motor_violation_m=np.asarray(rows["violation"]))
    stats = _s4._stats_dict(run.stats)
    summary = {
        "case": case.case_id, "settings": s, "params_sha256": params.sha256,
        "params_file_sha256": params.file_sha256, "dt_s": model.dt_s, "start": start,
        "still_window": stats,
        "s1_rule_checks": summary_table(v1_v3_checks(params, refs, run.stats)
                                        + v13_checks(refs, run.stats)),
        "events": [[e.t_s - t0, e.leg, e.kind] for e in run.events],
        "yield_steps": model.bushing.yield_steps.tolist(),
        "timing": {"run_wall_s": run.wall_s, "steps": run.steps,
                   "us_per_step": run.wall_s / run.steps * 1e6},
    }
    return CaseResult(summary=_s4._plain(summary),
                      run_meta=_run_meta(params, model, f"S5_{case.case_id}", s))


def job_modes(case, case_dir):
    """Restore the S1 state, add the rigid initial angular velocity, free vibration 20 s."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import rigid_displacement
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s2a import run_health_checks
    from outrigger_sim.verify.s4 import EXCITATIONS

    s = dict(case.settings)
    level = s["level"]
    params = load_params(level=level)
    refs = load_references()
    modal = modal_reference(refs, level)
    f_ref = np.asarray(modal.f_damped_Hz, dtype=float)
    exc = EXCITATIONS[s["exc"]]
    model, t0, start = _restored_model(params, refs, level, float(s["dt"]))
    zeta_num, zeta_num_src = modal.zeta_num_at(model.dt_s)
    p0 = model.probe()
    point = p0.body_pos_m + quat_to_matrix(p0.body_quat_wxyz) @ modal.reference_point_body_m
    f_target = float(f_ref[exc.target_mode])
    v_exc, w_exc = exc.velocity(f_target)
    residual = {"body_vel_m_s": np.asarray(p0.body_vel_m_s).tolist(),
                "body_omega_rad_s": np.asarray(p0.body_omega_rad_s).tolist(),
                "omega_over_excitation": float(np.linalg.norm(p0.body_omega_rad_s))
                / float(np.linalg.norm(w_exc))}
    set_rigid_velocity(model, v_exc, w_exc, point)
    run = run_free_vibration(model, exc.window_s, sample_s=SAMPLE_S)
    se = run.series
    t = se["t"] - t0
    q = rigid_displacement(se["origin"], se["quat"], p0.body_pos_m, p0.body_quat_wxyz,
                           modal.reference_point_body_m)
    rows, eta, era_overview = _s4.identify(t, q, modal=modal, f_ref=f_ref, zeta_num=zeta_num,
                                           window_s=exc.window_s, phi_valid=True,
                                           f_band_rel=0.15)
    for r, z in zip(rows, modal.zeta, strict=True):
        r["zeta_ref"] = float(z)
    checks = run_health_checks(case.case_id, se, n_events=len(run.events),
                               yield_steps=model.bushing.yield_steps.tolist())
    np.savez_compressed(Path(case_dir) / "series.npz", t=t, q=q, eta=eta, normal=se["normal"],
                        bushing_disp=se["bushing_disp"])
    summary = {
        "case": case.case_id, "settings": s, "params_sha256": params.sha256,
        "params_file_sha256": params.file_sha256, "dt_s": model.dt_s,
        "zeta_num": zeta_num.tolist(), "zeta_num_source": zeta_num_src,
        "excitation": {**exc.__dict__, "f_target_Hz": f_target, "omega_world_rad_s": w_exc,
                       "about_point_world_m": point},
        "start": start, "pre_excitation_residual": residual,
        "f_ref_key": modal.keys["f_damped_Hz"], "phi_key": modal.keys["phi"],
        "modes": rows, "era_overview": era_overview,
        "checks": summary_table(checks), "all_passed": all_passed(checks),
        "extremes": {
            "pad_normal_min_N": se["normal"].min(axis=0),
            "pad_normal_max_N": se["normal"].max(axis=0),
            "bushing_disp_max_mm": np.nanmax(np.linalg.norm(se["bushing_disp"], axis=2),
                                             axis=0) * 1e3,
            "yield_steps": model.bushing.yield_steps.tolist(),
            "events": [[e.t_s - t0, e.leg, e.kind] for e in run.events],
        },
        "timing": {"run_wall_s": run.wall_s, "steps": run.steps,
                   "us_per_step": run.wall_s / run.steps * 1e6},
    }
    return CaseResult(summary=_s4._plain(summary),
                      run_meta=_run_meta(params, model, f"S5_{case.case_id}", s))


def job(case, case_dir):
    """Batch job (module level for spawn): dispatch on ``case.settings['kind']``."""
    fn = {"v1": job_v1, "modes": job_modes}[case.settings["kind"]]
    out = fn(case, Path(case_dir))
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_s4._plain(dict(out.summary)), indent=1, ensure_ascii=False),
        encoding="utf-8")
    return out


# --- batch --------------------------------------------------------------------------------------


def run_batch(ids, jobs):
    from outrigger_sim.batch import Case, run_cases

    if not 1 <= jobs <= MAX_WORKERS:
        raise SystemExit(f"--jobs must be 1..{MAX_WORKERS}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    # long free-vibration cases first, the short V1 cases fill the slots that free up
    order = sorted(ids, key=lambda c: (c.startswith("v1_"), c))
    cases = [Case(c, case_settings(c)) for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CASE_TIMEOUT_S)
    wall = time.perf_counter() - t0
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += f"\n{(o.error or '')[-2500:]}"
        print(msg, flush=True)
    print(f"batch wall {wall:.1f} s, jobs {jobs} -> {_s4._rel(batch_dir)}", flush=True)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        if o.status == "ok":
            index[o.case_id] = _s4._rel(batch_dir / o.case_id)
    RESULTS.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    log = RESULTS / "batches.json"
    hist = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    hist.append({"batch": _s4._rel(batch_dir), "cases": order, "jobs": jobs, "wall_s": wall,
                 "placement": "pcore (EcoQoS off), outrigger_sim.hostcpu.place_process",
                 "env_threads": {k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS",
                                                                "MKL_NUM_THREADS")},
                 "case_wall_s": {o.case_id: o.wall_s for o in report.outcomes},
                 "status": {o.case_id: o.status for o in report.outcomes}})
    log.write_text(json.dumps(hist, indent=1), encoding="utf-8")
    return report


# --- summary ------------------------------------------------------------------------------------


def _load_results():
    if not INDEX.exists():
        return {}
    out = {}
    for cid, rel in json.loads(INDEX.read_text(encoding="utf-8")).items():
        p = ROOT / rel / "result.json"
        if p.exists():
            out[cid] = json.loads(p.read_text(encoding="utf-8"))
            out[cid]["_dir"] = rel
    return out


def v0_auger_section():
    """V0 (auger) from the YAML only (no simulation): judged rows, info rows (dyn rev. 22)."""
    import numpy as np

    from outrigger_sim.params import load_params
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.s5 import (
        MassProps,
        auger_travel_check,
        auger_v0_checks,
        auger_v0_residuals,
        compose_auger_level,
        composition_rounding_bound,
    )

    p = load_params()
    auger_json_rel = p.get("meta.sources.auger_levels")
    auger_json = json.loads((ROOT / auger_json_rel).read_text(encoding="utf-8"))
    fixed = MassProps.from_mapping(p.get("superstructure.fixed_part"))
    moving = MassProps.from_mapping(p.get("superstructure.auger_moving_set_at_cad_pose"))
    out, checks, info = {}, [], []
    for lv in _levels():
        block = p.get(f"superstructure.auger_levels.{lv}")
        reference = MassProps.from_mapping(block)
        travel_m = float(block["auger_travel_m"])
        travel_mm_json = float(auger_json["levels"][lv]["travel_mm"])
        composed = compose_auger_level(fixed, moving, travel_m)
        bound = composition_rounding_bound(fixed, moving, travel_m, reference)
        rows = auger_v0_checks(lv, composed, reference, bound,
                               key=f"YAML superstructure.auger_levels.{lv}")
        rows.append(auger_travel_check(lv, travel_m, travel_mm_json,
                                       key=f"{auger_json_rel} levels.{lv}.travel_mm x 1e-3"))
        c = summary_table(rows)
        checks += [x for x in c if x["id"] != "info"]
        info += [x for x in c if x["id"] == "info"]
        res = np.abs(np.array([composed.mass_kg, *composed.com_m,
                               *composed.inertia_kg_m2[np.triu_indices(3)]])
                     - np.array([reference.mass_kg, *reference.com_m,
                                 *reference.inertia_kg_m2[np.triu_indices(3)]]))
        lim = np.array([bound.mass_kg, *bound.com_m, *bound.inertia_kg_m2[np.triu_indices(3)]])
        out[lv] = {"travel_m": travel_m, "travel_mm_json": travel_mm_json,
                   "composed": {"mass_kg": composed.mass_kg, "com_m": composed.com_m.tolist(),
                                "inertia_kg_m2": composed.inertia_kg_m2.tolist()},
                   "residuals": auger_v0_residuals(composed, reference),
                   "rounding_bound": {"mass_kg": bound.mass_kg, "com_m": bound.com_m.tolist(),
                                      "inertia_kg_m2": bound.inertia_kg_m2.tolist()},
                   "residual_over_bound_max": float(np.max(np.where(lim > 0, res / lim, 0.0))),
                   "checks": c}
    out["inputs"] = {"fixed_part": "YAML superstructure.fixed_part",
                     "moving": "YAML superstructure.auger_moving_set_at_cad_pose",
                     "travel_source": auger_json_rel,
                     "frame": "body axes (x fwd, y left, z up), inertia about the CoM",
                     "params_file_sha256": p.file_sha256}
    return out, checks, info


CODE_FILES = (
    "04_scripts/02_chrono/run_S5.py",
    "04_scripts/02_chrono/run_S4.py",
    "03_src/outrigger_sim/verify/s5.py",
    "03_src/outrigger_sim/verify/s4.py",
    "03_src/outrigger_sim/verify/metrics.py",
    "03_src/outrigger_sim/verify/checks.py",
)
"""Files whose sha256 the summary records (dyn rev. 22 specification)."""


def code_sha256() -> dict[str, str]:
    """sha256 of the script and judgement modules at summary time."""
    import hashlib

    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}


def summarize():
    import numpy as np

    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.reference import (
        L1_BALL_CENTRE_REV13_F_UNDAMPED_HZ,
        L1_CONTACT_FORCE_N,
        TOTAL_WEIGHT_INCL_RODS_N,
        load_references,
    )
    from outrigger_sim.verify.s4 import ModeRow, assign_modes, judged_value, mode_info_checks
    from outrigger_sim.verify.s5 import (
        V10_LINEAR_FRACTION_OF_QUARTER_WEIGHT,
        V10_MODES,
        V10_PDELTA_FRACTION_OF_QUARTER_WEIGHT,
        pdelta_contact_forces_N,
        summarize_check_ids,
        v10_health_checks,
        v10_load_checks,
        v10_mode_checks,
        v10_order_checks,
    )

    refs = load_references()
    res = _load_results()
    v0, checks, info = v0_auger_section()
    pdelta_check = json.loads(PDELTA_CHECK.read_text(encoding="utf-8"))
    total_w = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    levels_out, f_judged = {}, {}
    for lv in _levels():
        modal = modal_reference(refs, lv)
        lvo = {}
        # V1
        r1 = res.get(f"v1_{lv}")
        ref_c = np.asarray(refs.get(L1_CONTACT_FORCE_N, level=lv), dtype=float)
        if r1:
            got = np.asarray(r1["still_window"]["contact_force_mean_N"], dtype=float)
            pdelta_N = pdelta_contact_forces_N(pdelta_check, lv)
            c = summary_table(v10_load_checks(
                lv, contact_mean_N=got, pdelta_contact_N=pdelta_N, ref_contact_N=ref_c,
                total_weight_N=total_w,
                pdelta_key=f"06_analysis/00_dynamics/s1_pdelta_check.json {lv}.nonlinear_contact_N",
                ref_key=L1_CONTACT_FORCE_N.resolve(level=lv).notation(),
                weight_key=TOTAL_WEIGHT_INCL_RODS_N.resolve().notation()))
            checks += [x for x in c if x["id"] != "info"]
            info += [x for x in c if x["id"] == "info"]
            lvo["V1"] = {
                "rule": "dyn rev. 22 U2 = B: judged vs P-delta nonlinear solution "
                        "(0.01 % W/4), linear reference recorded (1 % W/4)",
                "contact_mean_N": got.tolist(),
                "pdelta_nonlinear_contact_N": pdelta_N.tolist(),
                "diff_vs_pdelta_N": (got - pdelta_N).tolist(),
                "tol_N": V10_PDELTA_FRACTION_OF_QUARTER_WEIGHT * total_w / 4.0,
                "reference_N": ref_c.tolist(), "diff_vs_linear_N": (got - ref_c).tolist(),
                "linear_record_tol_N": V10_LINEAR_FRACTION_OF_QUARTER_WEIGHT * total_w / 4.0,
                "cylinder_mean_N": r1["still_window"].get("cylinder_force_mean_N"),
                "s1_rule_checks": r1["s1_rule_checks"], "checks": c,
                "yield_steps": r1["yield_steps"], "events": r1["events"],
                "us_per_step": r1["timing"]["us_per_step"]}
            info += [dict(x, id="info", item="S1 rule: " + x["item"])
                     for x in r1["s1_rule_checks"]]
        # modes 1-2
        assignment = assign_modes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
        f_und = np.asarray(refs.get(L1_BALL_CENTRE_REV13_F_UNDAMPED_HZ, level=lv), dtype=float)
        mrows, judged = [], []
        yields, n_events = [], 0
        for i in V10_MODES:
            run = assignment[i]
            r = res.get(f"{lv}_{run}")
            if not r:
                judged.append(None)
                continue
            row = r["modes"][i]
            era = row.get("era") or {}
            mr = ModeRow(mode=row["mode"], run=run, f_proj_Hz=row.get("f_proj_Hz"),
                         zeta_proj=row.get("zeta_proj"),
                         fit_residual_rms_rel=row.get("fit_residual_rms_rel"),
                         f_era_Hz=era.get("f_Hz"), zeta_era=era.get("zeta"),
                         leakage=era.get("leakage"), zeta_num=row["zeta_num"],
                         f_ref_Hz=row["f_ref_Hz"], zeta_ref=row["zeta_ref"])
            mrows.append(mr)
            j = judged_value(mr)
            judged.append({"mode": i + 1, "run": run, "f_Hz": j.f_Hz, "zeta": j.zeta,
                           "source": j.source, "reason": j.reason,
                           "f_ref_Hz": row["f_ref_Hz"], "f_rel": j.f_Hz / row["f_ref_Hz"] - 1,
                           "f_undamped_ref_Hz": float(f_und[i]),
                           "f_rel_vs_undamped": j.f_Hz / float(f_und[i]) - 1,
                           "zeta_ref": row["zeta_ref"], "zeta_num": row["zeta_num"],
                           "f_proj_Hz": row.get("f_proj_Hz"), "zeta_proj": row.get("zeta_proj"),
                           "fit_residual_rms_rel": row.get("fit_residual_rms_rel"),
                           "f_era_Hz": era.get("f_Hz"), "zeta_era": era.get("zeta"),
                           "era_mac_vs_phi": era.get("mac_vs_phi"),
                           "era_leakage": era.get("leakage"),
                           "era_order_spread": row.get("era_order_spread"),
                           "n_cycles": row.get("n_cycles")})
        for e in ("roll", "pitch"):
            r = res.get(f"{lv}_{e}")
            if r:
                yields.append(r["extremes"]["yield_steps"])
                n_events += len(r["extremes"]["events"])
                info_h = [dict(x, id="V13") for x in r["checks"]]
                checks += info_h
        if mrows:
            c = summary_table(v10_mode_checks(lv, mrows, ref_key_f=modal.keys["f_damped_Hz"],
                                              ref_key_zeta=modal.keys["zeta"]))
            checks += [x for x in c if x["id"] != "info"]
            info += [x for x in c if x["id"] == "info"]
            info += summary_table(mode_info_checks(mrows, f"V10 {lv}"))
            checks += summary_table(v10_health_checks(lv, yields, n_events))
        if all(j is not None for j in judged):
            f_judged[lv] = [j["f_Hz"] for j in judged]
        lvo["modes"] = judged
        lvo["mode_assignment"] = {f"mode {i + 1}": assignment[i] for i in V10_MODES}
        lvo["identification"] = (
            "projection on the level mode shapes (reference.json .../levels/" + lv
            + "/V7_ball_centre_bushing_rev13/mode_shapes, eta = Phi^T M q) + damped-cosine "
            "fit; 6-channel ERA cross-check; judged value per verify.s4.judged_value")
        lvo["runs"] = {e: {"dir": (res.get(f"{lv}_{e}") or {}).get("_dir"),
                           "us_per_step": ((res.get(f"{lv}_{e}") or {}).get("timing") or {})
                           .get("us_per_step"),
                           "pre_excitation_residual": (res.get(f"{lv}_{e}") or {})
                           .get("pre_excitation_residual"),
                           "pad_normal_min_N": ((res.get(f"{lv}_{e}") or {}).get("extremes")
                                                or {}).get("pad_normal_min_N"),
                           "bushing_disp_max_mm": ((res.get(f"{lv}_{e}") or {}).get("extremes")
                                                   or {}).get("bushing_disp_max_mm")}
                       for e in ("roll", "pitch")}
        levels_out[lv] = lvo
    if len(f_judged) == len(_levels()):
        checks += summary_table(v10_order_checks(f_judged, _levels()))
    by_id = summarize_check_ids(checks)
    batches = json.loads((RESULTS / "batches.json").read_text(encoding="utf-8")) \
        if (RESULTS / "batches.json").exists() else []
    params = load_params()
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S5 auger three levels (chrono_build_plan.md S5): V0 (auger), V10",
            "script": "04_scripts/02_chrono/run_S5.py", "checks_module": "outrigger_sim.verify.s5",
            "judgement": "cad-expert pre-check; physical judgement by dynamics-expert",
            "dt_yaml_s": float(params.simulation.L1.dt_s),
            "params_file_sha256": params.file_sha256,
            "reference_sha256": refs.sha256_by_file(),
            "code_sha256": code_sha256(),
            "era": {"order": _s4.ERA_ORDER, "order_check": _s4.ERA_ORDER_CHECK,
                    "block_rows": _s4.ERA_BLOCK_ROWS, "decimate": _s4.ERA_DECIMATE},
            "batches": batches,
            "raw": {cid: r["_dir"] for cid, r in res.items()},
        },
        "verdict_by_check": by_id,
        "all_passed": all(by_id.values()) if by_id else False,
        "V0_auger": v0,
        "V10": levels_out,
        "V10_f_judged_Hz": f_judged,
        "checks": checks,
        "checks_failed": [c for c in checks if not c["passed"]],
        "info_checks": info,
        "info_checks_failed": [c for c in info if not c["passed"]],
    }
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(_s4._plain(summary), indent=1, ensure_ascii=False),
                       encoding="utf-8")
    print(f"wrote {_s4._rel(SUMMARY)}")
    _figures(levels_out)
    print(json.dumps(by_id, indent=1))


def _figures(levels_out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    lvs = [lv for lv in levels_out if all(levels_out[lv].get("modes") or [None])]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    x = np.arange(len(lvs))
    for i, ax in enumerate(axes):
        ref = np.array([levels_out[lv]["modes"][i]["f_ref_Hz"] for lv in lvs])
        got = np.array([levels_out[lv]["modes"][i]["f_Hz"] for lv in lvs])
        ax.fill_between(x, ref * 0.97, ref * 1.03, color="#bbbbbb", alpha=0.5,
                        label="reference +-3 %")
        ax.plot(x, ref, "--", color="#555555", lw=1, label="reference |lambda|/2pi")
        ax.plot(x, got, "o", color="#1f77b4", ms=7, label="Chrono judged f_n")
        for k, lv in enumerate(lvs):
            m = levels_out[lv]["modes"][i]
            ax.annotate(f"{m['f_Hz']:.4f} Hz\n{m['f_rel'] * 100:+.3f} %\n({m['source']}, "
                        f"{m['run']})", (k, got[k]), textcoords="offset points", xytext=(8, -6),
                        fontsize=7)
        ax.set_xticks(x, lvs)
        ax.set_xlabel("auger level")
        ax.set_ylabel("natural frequency [Hz]")
        ax.set_title(f"V10 mode {i + 1}", fontsize=9)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=110)
    plt.close(fig)

    lvs = [lv for lv in levels_out if "V1" in levels_out[lv]]
    if not lvs:
        return
    fig, ax = plt.subplots(figsize=(14, 1.0 + 0.45 * (len(lvs) + 1)))
    ax.axis("off")
    head = (["level"] + [f"{g} Chrono / P-delta / diff [N]" for g in LEGS]
            + ["tol [N]", "vs linear ref (record) [N]"])
    cells = []
    for lv in lvs:
        v = levels_out[lv]["V1"]
        cells.append([lv] + [f"{a:,.1f} / {b:,.1f} / {d:+.2f}" for a, b, d in
                             zip(v["contact_mean_N"], v["pdelta_nonlinear_contact_N"],
                                 v["diff_vs_pdelta_N"], strict=True)]
                     + [f"{v['tol_N']:.3f}",
                        " / ".join(f"{d:+.1f}" for d in v["diff_vs_linear_N"])
                        + f" (<= {v['linear_record_tol_N']:.0f})"])
    tab = ax.table(cellText=cells, colLabels=head, loc="center", cellLoc="center")
    tab.auto_set_font_size(False)
    tab.set_fontsize(7)
    tab.scale(1.0, 1.4)
    ax.set_title("V10 / V1: still-window mean pad contact force vs P-delta nonlinear solution "
                 "(s1_pdelta_check.json, tol 0.01 % W/4); linear reference.json contact_force_N "
                 "recorded (1 % W/4)", fontsize=8)
    fig.tight_layout()
    fig.savefig(LOAD_FIGURE, dpi=130)
    plt.close(fig)
    print(f"wrote {_s4._rel(FIGURE)}, {_s4._rel(LOAD_FIGURE)}")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("run", "summary", "list"))
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if args.action == "list":
        print("\n".join(case_ids()))
        return
    if args.action == "summary":
        summarize()
        return
    ids = args.only or case_ids()
    for c in ids:
        case_settings(c)
    run_batch(ids, args.jobs)
    summarize()


if __name__ == "__main__":
    main(sys.argv[1:])
