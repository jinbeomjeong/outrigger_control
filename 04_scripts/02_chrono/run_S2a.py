"""S2a runs: ground-bushing dynamics (V7 diagnosis) and sloped-floor statics (V12), with V13.

``00_docs/03_chrono/chrono_build_plan.md`` S2a; checks in ``outrigger_sim.verify.s2a``.
Usage (Chrono-dev python, from any folder)::

    python -I -u run_S2a.py all            # every case + the yaw dt study (P-core) + summary
    python -I -u run_S2a.py case <name> [dt_s]   # one case (V7 cases accept another dt)
    python -I -u run_S2a.py dt_study       # v7_yaw at dt 2e-4 s and 5e-5 s (own processes)
    python -I -u run_S2a.py summary        # rebuild the summary from stored case results

Cases (top level, L1, dt from the YAML):

* ``v7_roll``, ``v7_pitch`` (20 s), ``v7_yaw`` (2 s): restore the S1 settled state
  ``07_results/states/S1_L1_top`` (analytic start + 15 s), add a rigid initial angular
  velocity about the mode-shape reference point (``scenarios/impulse``), free vibration;
  modal projection ``eta = Phi^T M q`` on the ball-centre bushing mode shapes
  (``V7_ball_centre_bushing_rev13 / mode_shapes``, plan rev. 10) and one damped-cosine fit
  per mode
  (``verify/metrics``); the numerical damping ``r_i omega_i dt / 2`` is subtracted before the
  diagnosis. ``v7_yaw`` is the diagnosis-5 test; it is always run (2 s, cheap) and only
  judged when diagnosis 4 / none applies.
* ``dt_study`` (``dynamics_model.md`` 5.3, dt 2e-4 s condition 1, cheap pre-check): ``v7_yaw``
  again at dt 2e-4 s and 5e-5 s (outputs ``07_results/S2a/v7_yaw_dt<dt>/``). If the excess
  damping over the physical value is the implicit integrator's ``r omega dt / 2`` on the
  bushing, the identified (raw) zeta3 moves in proportion to dt; if the effective ``c_t`` is
  simply larger, it does not move. The numerical damping subtracted is the
  ``V7_ball_centre_bushing_rev13 / zeta_num_r_omega_dt_half`` entry of the run dt (1e-4,
  2e-4 s), else the 1e-4 s entry scaled by ``dt / 1e-4`` (``ModalReference.zeta_num_at``).
* ``v12_pitch2``, ``v12_roll2``, ``v12_rollm2_pitch1.5``: tilted floor, level body at the
  exact plane-touching extensions closest to ``slope_V12 / <case> / extension_m``, bushings
  at t = 0 with zero deformation (initial hold until N > N_th), gravity 0 -> g half-cosine
  ramp 3 s, settle 53 s, still 5 s (V13); V12 means over the last 3 s (``scenarios/slope``).
  Hold safety (``dynamics_model.md`` 5.3 ruling 1): a leg still held at the ramp end aborts
  the run (``HoldNotReleasedError``, non-zero exit); release times and the largest tangential
  force while held (``<= mu N_th``) are judged V12 items.

The ground bushing force acts at the pad ball centre (``ground_bushing`` default, user
decision 2026-10-20, ``dynamics_model.md`` 5.3 ruling 4 option A). The V7 cases restore the
S1 snapshot, so ``run_S1.py`` must have been re-run with the same force point (the restore
refuses a snapshot of another force point).

Outputs: ``07_results/S2a/<case>/record.npz`` + ``meta.json`` (Record),
``07_results/S2a/<case>/result.json``; summary ``06_analysis/01_chrono/verify_S2a_L1.json``
and ``verify_S2a_L1.png``. Units SI; angles in deg where named ``*_deg``.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S2a"
STATES = ROOT / "07_results" / "states"
SUMMARY = ROOT / "06_analysis" / "01_chrono" / "verify_S2a_L1.json"
FIGURE = ROOT / "06_analysis" / "01_chrono" / "verify_S2a_L1.png"
LEVEL = "top"
SNAPSHOT = "S1_L1_top"
V7_CASES = {"v7_roll": "roll", "v7_pitch": "pitch", "v7_yaw": "yaw"}
V12_CASES = {
    "v12_pitch2": "ground roll 0 deg, pitch 2 deg",
    "v12_roll2": "ground roll 2 deg, pitch 0 deg",
    "v12_rollm2_pitch1.5": "ground roll -2 deg, pitch 1.5 deg",
}
CASES = (*V7_CASES, *V12_CASES)
PY = sys.executable
V7_SAMPLE_S = 1.0e-3
SERIES_POINTS = 1500
DT_NOMINAL_S = 1.0e-4
DT_STUDY_S = (2.0e-4, 5.0e-5)
PDELTA_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s2a_slope_pdelta_check.json"


def dt_case_name(name: str, dt_s: float | None) -> str:
    """Output folder of a V7 case run at a non-nominal dt (``v7_yaw_dt2e-04``)."""
    if dt_s is None or math.isclose(dt_s, DT_NOMINAL_S, rel_tol=1e-12):
        return name
    return f"{name}_dt{dt_s:.0e}"


def _plain(value):
    import numpy as np

    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _thin(t, *arrays, n=SERIES_POINTS):
    step = max(1, len(t) // n)
    return [a[::step] for a in (t, *arrays)]


def run_v7(name: str, dt_s: float | None = None) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.record import Recorder, load_snapshot, make_run_meta, save_record
    from outrigger_sim.scenarios.impulse import (
        EXCITATIONS,
        angular_velocity_world,
        modal_reference,
    )
    from outrigger_sim.scenarios.settle import analytic_static_pose
    from outrigger_sim.signals import Command
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import (
        fit_damped_sine,
        log_decrement,
        modal_coordinates,
        rigid_displacement,
    )
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s2a import ModeResult, run_health_checks, v7_mode_checks

    excitation = EXCITATIONS[V7_CASES[name]]
    params = load_params(level=LEVEL)
    refs = load_references()
    modal = modal_reference(refs, LEVEL)
    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    t_build = time.perf_counter()
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt_s)
    zeta_num_per_mode, zeta_num_source = modal.zeta_num_at(model.dt_s)
    out_name = dt_case_name(name, dt_s)
    snap = load_snapshot(SNAPSHOT, params_sha256=params.sha256, directory=STATES)
    t_restored = model.restore(snap)
    build_s = time.perf_counter() - t_build
    p0 = model.probe()
    rot0 = quat_to_matrix(p0.body_quat_wxyz)
    ref_point_world = p0.body_pos_m + rot0 @ modal.reference_point_body_m
    omega = angular_velocity_world(excitation, modal)
    set_rigid_velocity(model, (0.0, 0.0, 0.0), omega, ref_point_world)

    run_meta = make_run_meta(
        params,
        model.meta(),
        scenario=f"S2a_V7_{excitation.name}" + ("" if out_name == name else f"_dt{dt_s:g}"),
        scenario_settings={
            "start": f"snapshot {SNAPSHOT} (t = {t_restored} s)",
            "excitation": excitation.__dict__,
            "omega_world_rad_s": omega.tolist(),
            "about_point_world_m": ref_point_world.tolist(),
            "window_s": excitation.window_s,
            "sample_s": V7_SAMPLE_S,
        },
        reference_sha256=refs.sha256_by_file(),
        extra={"cpu_placement": placement},
    )
    recorder = Recorder(run_meta)
    command = Command(t_s=t_restored, leg_speed_m_s=np.zeros(4))
    run = run_free_vibration(
        model,
        excitation.window_s,
        sample_s=V7_SAMPLE_S,
        on_sample=lambda probe: recorder.append(model.truth(probe), command),
    )
    for e in run.events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    record_path = save_record(recorder.finish(), RESULTS / out_name, overwrite=True)

    s = run.series
    t = s["t"] - t_restored
    q = rigid_displacement(
        s["origin"], s["quat"], p0.body_pos_m, p0.body_quat_wxyz, modal.reference_point_body_m
    )
    eta = modal_coordinates(q, modal.phi, modal.mass_matrix)
    modes = []
    judged = None
    for i in range(6):
        fit = fit_damped_sine(t, eta[:, i], float(modal.f_damped_Hz[i]))
        zeta_num = float(zeta_num_per_mode[i])
        ld = log_decrement(t, eta[:, i], fit.f_damped_Hz) if i == excitation.mode_index else None
        res = ModeResult(
            mode=i + 1,
            fit=fit,
            zeta_num=zeta_num,
            zeta_corrected=fit.zeta - zeta_num,
            zeta_log_decrement=ld,
            f_ref_Hz=float(modal.f_damped_Hz[i]),
            zeta_ref=float(modal.zeta[i]),
        )
        modes.append(res)
        if i == excitation.mode_index:
            judged = res
    assert judged is not None
    checks = v7_mode_checks(name, judged) + run_health_checks(
        name, s, n_events=len(run.events), yield_steps=model.bushing.yield_steps.tolist()
    )
    eta_amp = np.abs(eta).max(axis=0)
    tt, ee = _thin(t, eta[:, excitation.mode_index])
    return {
        "case": out_name,
        "base_case": name,
        "excitation": excitation.__dict__,
        "omega_world_rad_s": omega.tolist(),
        "about_point_world_m": ref_point_world.tolist(),
        "start_snapshot": {"name": SNAPSHOT, "t_s": t_restored},
        "dt_s": model.dt_s,
        "zeta_num_source": f"{modal.keys['zeta_num']} ({zeta_num_source})",
        "ground_bushing_force_point": model.bushing.force_point,
        "steps": run.steps,
        "judged_mode": excitation.mode_index + 1,
        "modes": [
            {
                "mode": m.mode,
                "eta_max_abs": float(eta_amp[m.mode - 1]),
                "f_damped_Hz": m.fit.f_damped_Hz,
                "f_undamped_Hz": m.fit.f_undamped_Hz,
                "zeta_fit": m.fit.zeta,
                "zeta_num_subtracted": m.zeta_num,
                "zeta_corrected": m.zeta_corrected,
                "zeta_log_decrement": m.zeta_log_decrement,
                "f_ref_Hz": m.f_ref_Hz,
                "zeta_ref": m.zeta_ref,
                "residual_rms_rel": m.fit.residual_rms_rel,
                "amplitude": m.fit.amplitude,
                "sigma_1_s": m.fit.sigma_1_s,
                "n_cycles": m.fit.n_cycles,
                "fit_success": m.fit.success,
            }
            for m in modes
        ],
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "extremes": {
            "pad_normal_min_N": s["normal"].min(axis=0).tolist(),
            "pad_normal_max_N": s["normal"].max(axis=0).tolist(),
            "bushing_disp_max_mm": (
                np.nanmax(np.linalg.norm(s["bushing_disp"], axis=2), axis=0) * 1e3
            ).tolist(),
            "yield_steps": model.bushing.yield_steps.tolist(),
            "events": [[e.t_s, e.leg, e.kind] for e in run.events],
        },
        "series": {"t_s": tt, "eta_judged": ee},
        "reference_keys": modal.keys,
        "record": str(record_path.relative_to(ROOT)).replace("\\", "/"),
        "timing": {
            "build_and_restore_s": build_s,
            "run_wall_s": run.wall_s,
            "wall_us_per_step_incl_sampling": run.wall_s / run.steps * 1e6,
            "cpu_placement": placement,
        },
    }


def run_v12(name: str) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.chrono.runs import run_gravity_ramp
    from outrigger_sim.chrono.system import gravity_vector, set_gravity
    from outrigger_sim.params import load_params
    from outrigger_sim.record import Recorder, make_run_meta, save_record
    from outrigger_sim.scenarios.slope import (
        MEAN_WINDOW_S,
        RAMP_S,
        STILL_WINDOW_S,
        gravity_ramp,
        settle_after_ramp_s,
        slope_start,
    )
    from outrigger_sim.signals import Command
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s1 import v0_checks
    from outrigger_sim.verify.s2a import (
        hold_checks,
        slope_v13_checks,
        slope_window_stats,
        v12_checks,
    )

    case = V12_CASES[name]
    params = load_params(level=LEVEL)
    refs = load_references()
    st = slope_start(params, refs, case)
    t_build = time.perf_counter()
    model = L1Model(
        params,
        pose=BodyPose(st.body_origin_m),
        extensions_m=st.extensions_m,
        attach_bushings=False,
        floor_pose=BodyPose(st.floor_pos_m, st.floor_quat_wxyz),
    )
    model.bushing.attach(hold_until_loaded=True)
    inventory = model.v0_inventory()  # full gravity here (V0 compares it with the YAML)
    v0 = v0_checks(params, inventory)
    g_full = gravity_vector(params)
    set_gravity(model.system, (0.0, 0.0, 0.0))
    build_s = time.perf_counter() - t_build
    d0 = model.bushing.tangential_displacement_m()
    start_deformation = float(np.nanmax(np.linalg.norm(d0, axis=1)))
    settle_s = settle_after_ramp_s(params)
    total_s = RAMP_S + settle_s + STILL_WINDOW_S
    still_from = RAMP_S + settle_s
    mean_from = total_s - MEAN_WINDOW_S

    run_meta = make_run_meta(
        params,
        model.meta(),
        scenario="S2a_V12_slope",
        scenario_settings={
            "case": case,
            "ramp": "half-cosine (1 - cos(pi t / T)) / 2, gravity set before each step",
            "ramp_s": RAMP_S,
            "settle_after_ramp_s": settle_s,
            "still_window_s": STILL_WINDOW_S,
            "mean_window_s": MEAN_WINDOW_S,
            "start": st.__dict__,
            "bushing_initial_hold": "until N > N_th (ground_bushing 'Initial hold')",
        },
        reference_sha256=refs.sha256_by_file(),
        extra={"cpu_placement": placement},
    )
    recorder = Recorder(run_meta)
    command = Command(t_s=0.0, leg_speed_m_s=np.zeros(4))
    run = run_gravity_ramp(
        model,
        g_full,
        gravity_ramp,
        total_s,
        fine_from_s=still_from,
        on_sample=lambda probe: recorder.append(model.truth(probe), command),
        hold_deadline_s=RAMP_S,
    )
    for e in run.events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    record_path = save_record(recorder.finish(), RESULTS / name, overwrite=True)

    s = run.series
    stats = slope_window_stats(s, st.normal_world, mean_from_s=mean_from, still_from_s=still_from)
    checks, info = v12_checks(
        params,
        refs,
        case,
        st.normal_world,
        stats,
        slip_total_m=model.bushing.slip_total_m,
        start_deformation_m=start_deformation,
        start_gap_m=st.sphere_gap_m,
    )
    checks += slope_v13_checks(refs, case, stats)
    checks += hold_checks(
        case,
        release_t_s=model.bushing.hold_release_t_s,
        max_tangential_N=model.bushing.hold_max_tangential_N,
        ramp_end_s=RAMP_S,
        friction=params.contact.rigid_floor.friction,
        touch_threshold_N=model.bushing.touch_threshold_N,
    )
    from outrigger_sim.verify.checks import check_equal

    checks.append(check_equal("V12", f"{case}: no bushing event (R15)", len(run.events), 0))
    reaction = s["pad_contact_world"] + s["bushing_force_world"]
    tt, rz, rx, gs = _thin(s["t"], reaction[:, :, 2], reaction[:, :, 0], s["gravity_scale"])
    from outrigger_sim.verify.s2a import slope_reference

    ref = slope_reference(refs, case, st.normal_world)
    return {
        "case": name,
        "slope_case": case,
        "start": st.__dict__,
        "dt_s": model.dt_s,
        "steps": run.steps,
        "ramp_s": RAMP_S,
        "settle_after_ramp_s": settle_s,
        "total_s": total_s,
        "checks": summary_table(checks),
        "info": summary_table(info),
        "all_passed": all_passed(checks),
        "v0": {
            "n_checks": len(v0),
            "failed": [c for c in summary_table(v0) if not c["passed"]],
        },
        "window": _plain(stats.__dict__),
        "reference": _plain(ref),
        "ground_bushing": {
            "yield_steps": model.bushing.yield_steps.tolist(),
            "slip_total_m": model.bushing.slip_total_m.tolist(),
            "hold_release_t_s": model.bushing.hold_release_t_s.tolist(),
            "hold_max_tangential_N": model.bushing.hold_max_tangential_N.tolist(),
            "force_point": model.bushing.force_point,
            "start_deformation_m": start_deformation,
            "events": [[e.t_s, e.leg, e.kind] for e in run.events],
            "kt_N_m": list(params.contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m),
        },
        "series": {
            "t_s": tt,
            "reaction_z_N": rz,
            "reaction_x_N": rx,
            "gravity_scale": gs,
        },
        "record": str(record_path.relative_to(ROOT)).replace("\\", "/"),
        "timing": {
            "build_s": build_s,
            "run_wall_s": run.wall_s,
            "wall_us_per_step_incl_sampling": run.wall_s / run.steps * 1e6,
            "cpu_placement": placement,
        },
    }


def foreign_processes() -> list[str]:
    try:
        txt = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=30, check=False
        ).stdout.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ["<tasklist failed>"]
    out = []
    for line in txt.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower().removesuffix(".exe") in (
            "julia",
            "freecad",
            "freecadcmd",
            "gmsh",
            "ccx",
            "matlab",
        ):
            out.append(f"{parts[0]}:{parts[1]}")
    return out


def _run_case_process(name: str, dt_s: float | None = None) -> None:
    before = foreign_processes()
    t0 = time.perf_counter()
    extra = [] if dt_s is None else [repr(dt_s)]
    done = subprocess.run(
        [PY, "-I", "-u", str(Path(__file__).resolve()), "case", name, *extra],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    tail = (done.stdout.strip().splitlines() or [""])[-1]
    print(
        f"{dt_case_name(name, dt_s)}: rc={done.returncode} {time.perf_counter() - t0:.1f}s "
        f"{tail} foreign={before}/{foreign_processes()}",
        flush=True,
    )
    if done.returncode != 0:
        print(done.stderr[-3000:], flush=True)


def run_dt_study() -> None:
    for dt_s in DT_STUDY_S:
        _run_case_process("v7_yaw", dt_s)


def run_all() -> None:
    for name in CASES:
        _run_case_process(name)
    run_dt_study()
    summarize()


DT_STUDY_RATIO_IMPLICIT = (0.7, 1.3)
"""Measured / predicted slope d zeta3 / d dt in this band -> implicit numerical damping."""
DT_STUDY_RATIO_CONSTANT_MAX = 0.3
"""|measured / predicted slope| below this -> dt independent (c_t scale hypothesis)."""
YAW_ZETA_FIT_BEFORE_FORCE_POINT = 0.0391121
"""Identified zeta3 of v7_yaw at dt 1e-4 s with the contact-point bushing (2026-10-20 run,
``dynamics_model.md`` 5.3 V7 table); predictions 0.04094 / 0.03821 for dt 2e-4 / 5e-5 s."""


def yaw_dt_study(results: dict) -> dict | None:
    """Raw zeta3 of v7_yaw against dt and the two hypotheses (``dynamics_model.md`` 5.3)."""
    import numpy as np

    runs = {}
    if "v7_yaw" in results:
        runs[DT_NOMINAL_S] = results["v7_yaw"]
    for dt_s in DT_STUDY_S:
        p = RESULTS / dt_case_name("v7_yaw", dt_s) / "result.json"
        if p.is_file():
            runs[dt_s] = json.loads(p.read_text(encoding="utf-8"))
    if DT_NOMINAL_S not in runs or len(runs) < 2:
        return None
    rows = []
    for dt_s in sorted(runs):
        r = runs[dt_s]
        m = next(m for m in r["modes"] if m["mode"] == r["judged_mode"])
        rows.append(
            {
                "dt_s": dt_s,
                "case": r["case"],
                "f_damped_Hz": m["f_damped_Hz"],
                "zeta_fit_raw": m["zeta_fit"],
                "zeta_num_subtracted": m["zeta_num_subtracted"],
                "zeta_corrected": m["zeta_corrected"],
                "zeta_log_decrement": m["zeta_log_decrement"],
                "residual_rms_rel": m["residual_rms_rel"],
                "force_point": r.get("ground_bushing_force_point"),
            }
        )
    nominal = next(r for r in rows if r["dt_s"] == DT_NOMINAL_S)
    zeta_num_nominal = nominal["zeta_num_subtracted"]
    dts = np.array([r["dt_s"] for r in rows])
    zetas = np.array([r["zeta_fit_raw"] for r in rows])
    slope = float(np.polyfit(dts, zetas, 1)[0])
    slope_predicted = zeta_num_nominal / DT_NOMINAL_S
    ratio = slope / slope_predicted
    for r in rows:
        r["prediction_implicit"] = nominal["zeta_fit_raw"] + zeta_num_nominal * (
            r["dt_s"] / DT_NOMINAL_S - 1.0
        )
        r["prediction_ct_scale"] = nominal["zeta_fit_raw"]
    if DT_STUDY_RATIO_IMPLICIT[0] <= ratio <= DT_STUDY_RATIO_IMPLICIT[1]:
        verdict = "zeta3 moves with dt as r omega dt / 2: implicit numerical damping on the bushing"
    elif abs(ratio) <= DT_STUDY_RATIO_CONSTANT_MAX:
        verdict = "zeta3 does not move with dt: effective c_t scale (bushing damping larger)"
    else:
        verdict = "undetermined (slope ratio outside both bands)"
    return {
        "purpose": "dynamics_model.md 5.3, dt 2e-4 s condition 1 pre-check (v7_yaw 2 s at three "
        "dt); final judgement by dynamics-expert (S3 V8(a))",
        "rows": rows,
        "slope_dzeta_ddt_per_s": slope,
        "slope_predicted_implicit_per_s": slope_predicted,
        "slope_ratio_measured_over_implicit": ratio,
        "bands": {
            "implicit": list(DT_STUDY_RATIO_IMPLICIT),
            "ct_scale_abs_max": DT_STUDY_RATIO_CONSTANT_MAX,
        },
        "verdict_auto": verdict,
        "before_force_point_change": {
            "zeta_fit_dt1e-4": YAW_ZETA_FIT_BEFORE_FORCE_POINT,
            "prediction_implicit_dt2e-4_dt5e-5": [0.04094, 0.03821],
            "note": "contact-point bushing (pre 2026-10-20 option A); predictions from 5.3",
        },
    }


def v12_vs_pdelta(results: dict) -> dict | None:
    """Chrono - reference vertical vs the dynamics-expert ball-centre prediction (P-delta only).

    ``s2a_slope_pdelta_check.json``: prediction = (ball-centre linear - reference) + (ball-centre
    nonlinear - linear), i.e. the vertical difference expected once the sphere lever is gone.
    """
    import numpy as np

    if not PDELTA_CHECK.is_file():
        return None
    check = json.loads(PDELTA_CHECK.read_text(encoding="utf-8"))
    out = {"source": str(PDELTA_CHECK.relative_to(ROOT)).replace("\\", "/")}
    for name in V12_CASES:
        if name not in results or name not in check:
            continue
        r = results[name]
        c = check[name]
        got = np.asarray(r["window"]["reaction_world_mean_N"], dtype=float)[:, 2]
        ref = np.asarray(r["reference"]["reaction_world_N"], dtype=float)[:, 2]
        pred = np.asarray(c["ball_variant_linear_minus_reference_vertical_N"]) + np.asarray(
            c["ball_variant_nonlinear_minus_linear_vertical_N"]
        )
        before = np.asarray(c["chrono_minus_reference_vertical_N"], dtype=float)
        out[name] = {
            "chrono_minus_reference_vertical_N": (got - ref).tolist(),
            "prediction_ball_centre_N": pred.tolist(),
            "chrono_minus_prediction_N": (got - ref - pred).tolist(),
            "before_contact_point_chrono_minus_reference_N": before.tolist(),
            "sphere_lever_removed_N": (before - (got - ref)).tolist(),
            "sphere_lever_predicted_N": c["contact_minus_ball_nonlinear_vertical_N"],
        }
    return out


def _v7_checks_with_natural_frequency(name: str, result: dict) -> list[dict]:
    """Stored checks of a V7 case with the frequency rows rebuilt from the stored fit.

    The frequency rule compares ``f_n = f_d / sqrt(1 - zeta_fit^2)`` with the reference
    ``|lambda| / 2 pi`` (``verify.s2a.v7_frequency_checks``); results stored before that rule
    compared ``f_d``, so the summary recomputes these rows instead of rerunning the case.
    """
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.s2a import v7_frequency_checks

    mode = next(m for m in result["modes"] if m["mode"] == result["judged_mode"])
    frequency_rows = summary_table(
        v7_frequency_checks(name, mode["mode"], mode["f_undamped_Hz"], mode["f_ref_Hz"])
    )
    other_rows = [c for c in result["checks"] if not (c["id"] == "V7" and "frequency" in c["item"])]
    return frequency_rows + other_rows


def summarize() -> None:
    import numpy as np

    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s2a import (
        v7_diagnosis,
        v7_thresholds,
        v7_yaw_verdict,
        v12_plan_a_diagnosis,
    )

    refs = load_references()
    thresholds = v7_thresholds(refs, LEVEL)
    results = {}
    for name in CASES:
        p = RESULTS / name / "result.json"
        if p.is_file():
            results[name] = json.loads(p.read_text(encoding="utf-8"))

    def judged(name):
        r = results[name]
        return next(m for m in r["modes"] if m["mode"] == r["judged_mode"])

    diagnosis = None
    if "v7_roll" in results and "v7_pitch" in results:
        z1 = judged("v7_roll")["zeta_corrected"]
        z2 = judged("v7_pitch")["zeta_corrected"]
        d = v7_diagnosis(z1, z2, thresholds)
        diagnosis = {
            "zeta1_corrected": z1,
            "zeta2_corrected": z2,
            "code": d.code,
            "text": d.text,
            "yaw_test_required": d.needs_yaw,
            "thresholds_key": thresholds.key,
        }
        if "v7_yaw" in results:
            z3 = judged("v7_yaw")["zeta_corrected"]
            diagnosis["zeta3_corrected"] = z3
            diagnosis["yaw_verdict"] = v7_yaw_verdict(z3, thresholds)
            diagnosis["yaw_used_for_verdict"] = d.needs_yaw
    table = []
    for name, r in results.items():
        checks = _v7_checks_with_natural_frequency(name, r) if name in V7_CASES else r["checks"]
        for c in checks:
            table.append(
                {
                    "case": name,
                    **{
                        k: c[k]
                        for k in (
                            "id",
                            "item",
                            "value",
                            "ref",
                            "tol",
                            "tol_kind",
                            "unit",
                            "passed",
                            "ref_key",
                        )
                    },
                }
            )
    by_id: dict[str, bool] = {}
    for row in table:
        by_id[row["id"]] = by_id.get(row["id"], True) and row["passed"]
    if diagnosis is not None:
        ok = diagnosis["code"] == "1" or (
            diagnosis["yaw_test_required"]
            and diagnosis.get("yaw_verdict", "").startswith("c_t as intended")
        )
        by_id["V7 diagnosis"] = bool(ok)
    v0 = {name: r["v0"] for name, r in results.items() if "v0" in r}
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S2a (chrono_build_plan.md): ground bushing dynamics (V7 diagnosis from "
            "the S1 top state) and sloped-floor statics (V12, 3 cases), V13",
            "script": "04_scripts/02_chrono/run_S2a.py",
            "model": "outrigger_sim.chrono.model.L1Model (top, crawler spheres layout D present, "
            "not in contact), ground bushing GroundBushingCoulomb",
            "judgement": "automatic pre-check; final physical judgement by dynamics-expert",
            "ground_bushing_force_point": sorted(
                {
                    r.get("ground_bushing_force_point")
                    or r.get("ground_bushing", {}).get("force_point")
                    or "contact_point (not recorded)"
                    for r in results.values()
                }
            ),
            "v7_reference": "reference.json V7_ball_centre_bushing_rev13 (plan rev. 10 option A: "
            "f_damped_Hz, zeta, mode_shapes, zeta_num_r_omega_dt_half, V7_diagnostic / "
            "thresholds); the contact-point keys are history",
            "v12_reference": "slope_V12 / <case> / L1 (unchanged); diagnosis against "
            "L1_plan_A_expected_chrono_minus_reference_rev13 (<= 3 N per leg, not judged)",
            "python": platform.python_version(),
            "host": os.environ.get("COMPUTERNAME", ""),
            "raw_data": {
                name: {"record": r["record"], "result": f"07_results/S2a/{name}/result.json"}
                for name, r in results.items()
            },
            "figure": str(FIGURE.relative_to(ROOT)).replace("\\", "/"),
        },
        "verdict_by_check": by_id,
        "all_passed": all(by_id.values()),
        "v7_diagnosis": diagnosis,
        "v7_modes": {name: r["modes"] for name, r in results.items() if name in V7_CASES},
        "v12": {
            name: {
                "start": r["start"],
                "window": r["window"],
                "reference": r["reference"],
                "ground_bushing": r["ground_bushing"],
                "info": r["info"],
            }
            for name, r in results.items()
            if name in V12_CASES
        },
        "table": table,
        "v0": v0,
        "v12_plan_a_diagnosis": {
            name: summary_table(
                v12_plan_a_diagnosis(refs, r["slope_case"], r["window"]["reaction_world_mean_N"])
            )
            for name, r in results.items()
            if name in V12_CASES
        },
        "v7_yaw_dt_study": yaw_dt_study(results),
        "v12_vs_pdelta_prediction": v12_vs_pdelta(results),
        "timing": {name: r["timing"] for name, r in results.items()},
    }
    SUMMARY.write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {SUMMARY}")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.6))
    for j, name in enumerate(V7_CASES):
        ax = axes[0, j]
        if name not in results:
            ax.set_visible(False)
            continue
        r = results[name]
        m = judged(name)
        t = np.asarray(r["series"]["t_s"])
        y = np.asarray(r["series"]["eta_judged"])
        ax.plot(t, y * 1e3, color="#444444", lw=0.6, label="Chrono")
        env = m["amplitude"] * np.exp(-m["sigma_1_s"] * (t - t[0]))
        ax.plot(t, env * 1e3, color="#d62728", lw=1, label="fit envelope")
        ax.plot(t, -env * 1e3, color="#d62728", lw=1)
        ax.set_title(
            f"{name}: mode {m['mode']} f_n {m['f_undamped_Hz']:.4f} Hz "
            f"(ref {m['f_ref_Hz']:.4f}), "
            f"zeta {m['zeta_corrected']:.5f} (ref {m['zeta_ref']:.5f})",
            fontsize=8,
        )
        ax.set_xlabel("time since excitation [s]")
        ax.set_ylabel("modal coordinate eta [1e-3 sqrt(kg) m]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    for j, name in enumerate(V12_CASES):
        ax = axes[1, j]
        if name not in results:
            ax.set_visible(False)
            continue
        r = results[name]
        t = np.asarray(r["series"]["t_s"])
        rx = np.asarray(r["series"]["reaction_x_N"]) / 1e3
        ref = np.asarray(r["reference"]["reaction_world_N"]) / 1e3
        for i, leg in enumerate(("FL", "FR", "RL", "RR")):
            ax.plot(t, rx[:, i], color=colors[i], lw=1, label=leg)
            tol = max(0.1 * abs(ref[i, 0]), 0.2)
            ax.axhspan(ref[i, 0] - tol, ref[i, 0] + tol, color=colors[i], alpha=0.12, lw=0)
            ax.axhline(ref[i, 0], color=colors[i], lw=0.8, ls="--")
        ax.set_title(
            f"{r['slope_case']}: horizontal reaction x\n(dashed = reference, band = V12 tolerance)",
            fontsize=9,
        )
        ax.set_xlabel("time from ramp start [s]")
        ax.set_ylabel("floor reaction on rod, world x [kN]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=110)
    print(f"wrote {FIGURE}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "case":
        case = sys.argv[2]
        if case not in CASES:
            raise SystemExit(f"unknown case {case!r}, expected one of {CASES}")
        dt_arg = float(sys.argv[3]) if len(sys.argv) > 3 else None
        if dt_arg is not None and case not in V7_CASES:
            raise SystemExit("a dt argument is only supported for the V7 cases")
        result = run_v7(case, dt_arg) if case in V7_CASES else run_v12(case)
        out = RESULTS / result["case"] / "result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(_plain(result), indent=1, ensure_ascii=False), encoding="utf-8")
        failed = [c["id"] + ": " + c["item"] for c in result["checks"] if not c["passed"]]
        print(
            "OK",
            result["case"],
            f"{result['timing']['wall_us_per_step_incl_sampling']:.1f} us/step",
            "all_passed" if result["all_passed"] else f"FAILED {failed}",
            flush=True,
        )
    elif mode == "all":
        run_all()
    elif mode == "dt_study":
        run_dt_study()
        summarize()
    elif mode == "summary":
        summarize()
    else:
        raise SystemExit(f"unknown mode {mode!r}")
