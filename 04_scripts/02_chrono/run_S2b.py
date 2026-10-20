"""S2b runs: actuator (V0 motor sign, V11, command ramp), crawler settle on layout D (3 auger
levels, snapshots), R15 touch / lift events at dt 1e-4 and 1e-5 s.

``00_docs/03_chrono/chrono_build_plan.md`` S2b; checks in ``outrigger_sim.verify.s2b``.
Usage (Chrono-dev python, from any folder)::

    python -I -u run_S2b.py all              # every case (max 4 processes, P-cores) + summary
    python -I -u run_S2b.py case <name>      # one case
    python -I -u run_S2b.py summary          # rebuild the summary from stored case results

Cases (L1, crawler layout D, actuator = ``chrono/actuators.L1SpeedActuator`` with the
0.1 s command ramp; dt 1e-4 s unless named):

* ``air_short`` (top): superstructure fixed, legs in the air (``scenarios/stroke.air_pose``).
  V0 motor sign: +v_max 1 s on every leg; then the inertial reaction of a +v_max command on a
  hanging rod with / without the ramp at dt 1e-4 and 1e-5 s (0.3 s each).
* ``v11`` (top, air): V11 schedule (``scenarios/stroke.v11_schedule``, 62 s): +-1 m/s,
  +-v_max, +-2 v_max, commands beyond both ends; per-step speed, position, axial constraint
  and rod-force tracking; full-stroke times.
* ``crawler_<level>`` (top, middle, bottom): legs at 0, body at the analytic exact settle
  pose on the 24 crawler spheres (``scenarios/crawler_settle``; P-delta included), V0
  inventory (S1 checks + sphere gaps), 10 s settle + 5 s still window (V13), snapshot
  ``07_results/states/S2b_crawler_<level>`` + round trip (1 s), then a 20 s free vibration
  with a small initial velocity on the three crawler modes (frequency / zeta recorded,
  compared with the linear model and, for top, ``crawler_on_floor_modes (layout D, legs at
  0)``).
* ``event_<fast|slow>_FL_dt<1e-04|1e-05>`` (top): FL starts above its touch extension on the
  analytic crawler pose and goes down / up / down (``scenarios/stroke.event_cases``); R15
  events (``t_lift`` 1 ms, ``N_th`` 100 N), raw ``N > 0`` transitions, first-contact time.

Outputs: ``07_results/S2b/<case>/record.npz`` + ``meta.json`` (Record), ``result.json``;
summary ``06_analysis/01_chrono/verify_S2b_L1.json`` and ``verify_S2b_L1.png``. Units SI;
angles in deg where named ``*_deg``.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S2b"
STATES = ROOT / "07_results" / "states"
SUMMARY = ROOT / "06_analysis" / "01_chrono" / "verify_S2b_L1.json"
FIGURE = ROOT / "06_analysis" / "01_chrono" / "verify_S2b_L1.png"
LEVELS = ("top", "middle", "bottom")
EVENT_DTS = (1.0e-4, 1.0e-5)
EVENT_NAMES = ("fast_FL", "slow_FL")
CASES = (
    "air_short",
    "v11",
    *(f"crawler_{lv}" for lv in LEVELS),
    *(f"event_{n}_dt{dt:.0e}" for n in EVENT_NAMES for dt in EVENT_DTS),
)
MAX_PROCESSES = 4
"""Main-session rule: at most 4 Chrono processes at once (half the P-cores)."""
PY = sys.executable
SETTLE_S = 10.0
STILL_S = 5.0
ROUND_TRIP_S = 1.0
MODES_S = 20.0
MODE_AMPLITUDE = {"pitch": math.radians(0.005), "roll": math.radians(0.005), "heave": 5.0e-5}
"""Initial modal amplitudes (ASSUMPTION, small: no sphere changes its contact state)."""


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
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _thin(n_points, *arrays):
    import numpy as np

    n = len(arrays[0])
    idx = np.unique(np.linspace(0, n - 1, min(n, n_points)).round().astype(int))
    return [np.asarray(a)[idx] for a in arrays]


def _recorder(params, model, scenario, settings, placement):
    from outrigger_sim.record import Recorder, make_run_meta
    from outrigger_sim.verify.reference import load_references

    meta = make_run_meta(
        params,
        model.meta(),
        scenario=scenario,
        scenario_settings=settings,
        reference_sha256=load_references().sha256_by_file(),
        extra={"cpu_placement": placement},
    )
    return Recorder(meta)


def _append(recorder, model, probe):
    from outrigger_sim.signals import Command

    recorder.append(
        model.truth(probe), Command(t_s=probe.t_s, leg_speed_m_s=model.actuator.command_m_s)
    )


def _air_model(params, *, ramp_s=None, dt_s=None):
    from outrigger_sim.chrono.actuators import ACCEL_RAMP_S
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model
    from outrigger_sim.scenarios.stroke import air_pose

    model = L1Model(
        params,
        pose=BodyPose(air_pose(params)),
        extensions_m=(0.0, 0.0, 0.0, 0.0),
        attach_bushings=False,
        actuator=True,
        actuator_ramp_s=ACCEL_RAMP_S if ramp_s is None else ramp_s,
        dt_s=dt_s,
    )
    model.superstructure.SetFixed(True)
    return model


def _rod_weight(params):
    import numpy as np

    return np.array([leg.moving_part.mass_kg for leg in params.legs]) * params.meta.gravity_m_s2


# --- cases ---------------------------------------------------------------------------------


def run_air_short() -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.actuators import ACCEL_RAMP_S
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import load_params
    from outrigger_sim.record import save_record
    from outrigger_sim.scenarios.stroke import Schedule, Segment, sign_test_schedule
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s2b import motor_sign_checks, ramp_spike_checks

    params = load_params(level="top")
    weight = _rod_weight(params)
    v = params.actuator.max_speed_m_s
    model = _air_model(params)
    sched = sign_test_schedule(params)
    recorder = _recorder(params, model, "S2b_V0_motor_sign_air", sched.as_dict(), placement)

    def sample(probe):
        _append(recorder, model, probe)

    model.set_command([v, v, v, v])
    first = model.step(capture=True)  # contact-free: the first step gives the hanging force
    p0 = first.probe
    hang = p0.motor_force_N.copy()
    pads0 = p0.pad_sphere_centre_world_m[:, 2].copy()
    s0 = p0.motor_pos_m.copy()
    run = run_commanded(model, 1.0, lambda _t: None, sample_s=1.0e-2, on_sample=sample)
    p1 = model.probe()
    dz = p1.pad_sphere_centre_world_m[:, 2] - pads0
    ds = p1.motor_pos_m - s0
    model.set_command([0.0, 0.0, 0.0, 0.0])
    run2 = run_commanded(model, 0.2, lambda _t: None, sample_s=1.0e-2, on_sample=sample)
    record_path = save_record(recorder.finish(), RESULTS / "air_short", overwrite=True)
    checks = motor_sign_checks(dz, ds, hang, weight)

    spikes = []
    m_rod = float(params.legs[0].moving_part.mass_kg)
    for ramp in (ACCEL_RAMP_S, 0.0):
        for dt in (1.0e-4, 1.0e-5):
            mdl = _air_model(params, ramp_s=ramp, dt_s=dt)
            s = Schedule([Segment(0.0, (v, v, v, v)), Segment(0.15, (0.0, 0.0, 0.0, 0.0))], 0.3)
            r = run_commanded(mdl, 0.3, s, sample_s=1.0e-2, force_ref_N=-weight)
            expected = m_rod * (v / ramp if ramp > 0.0 else v / dt)
            spikes.append(
                {
                    "name": f"ramp{ramp:g}_dt{dt:.0e}",
                    "ramp_s": ramp,
                    "dt_s": dt,
                    "max_force_dev_N": r.max_force_dev_N.tolist(),
                    "expected_N": expected,
                    "max_speed_m_s": r.max_motor_speed_m_s.tolist(),
                    "wall_s": r.wall_s,
                }
            )
    checks += ramp_spike_checks(spikes)
    return {
        "case": "air_short",
        "dt_s": model.dt_s,
        "air_origin_m": list(model.pose.origin_m),
        "sign_test": {
            "pad_dz_m": dz.tolist(),
            "motor_ds_m": ds.tolist(),
            "acting_s_ref_m": model.actuator.acting_s_ref_m.tolist(),
            "hanging_force_N": hang.tolist(),
            "rod_weight_N": weight.tolist(),
            "expected_ds_ramp_m": v * (1.0 - ACCEL_RAMP_S / 2.0),
            "max_speed_m_s": np.maximum(run.max_motor_speed_m_s, run2.max_motor_speed_m_s).tolist(),
            "force_after_stop_N": model.probe().motor_force_N.tolist(),
        },
        "spikes": spikes,
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "record": _rel(record_path),
        "timing": {"cpu_placement": placement, "wall_s": run.wall_s + run2.wall_s},
    }


def run_v11() -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import LEG_ORDER, load_params
    from outrigger_sim.record import save_record
    from outrigger_sim.scenarios.stroke import expected_full_stroke_time_s, v11_schedule
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s2b import v11_checks

    params = load_params(level="top")
    weight = _rod_weight(params)
    model = _air_model(params)
    sched = v11_schedule(params)
    recorder = _recorder(params, model, "S2b_V11_air", sched.as_dict(), placement)
    run = run_commanded(
        model,
        sched.end_s,
        sched,
        sample_s=1.0e-2,
        on_sample=lambda p: _append(recorder, model, p),
        force_ref_N=-weight,
    )
    record_path = save_record(recorder.finish(), RESULTS / "v11", overwrite=True)
    s = run.series
    t = s["t"] - run.t_start_s
    v = params.actuator.max_speed_m_s
    hi = params.actuator.stroke_m
    pos = s["motor_pos"]

    # sample period 10 ms -> refine the crossing time by linear interpolation of the samples
    def crossing_interp(leg, t_from, rising):
        mask = np.flatnonzero(t >= t_from - 1e-9)
        tt, pp = t[mask], pos[mask, leg]
        target = hi - 1.0e-6 if rising else 1.0e-6
        idx = np.flatnonzero(pp >= target) if rising else np.flatnonzero(pp <= target)
        if not idx.size or idx[0] == 0:
            return math.nan
        k = idx[0]
        return float(tt[k - 1] + (target - pp[k - 1]) * (tt[k] - tt[k - 1]) / (pp[k] - pp[k - 1]))

    times = {}
    for leg in (0, 1, 2):
        times[f"{LEG_ORDER[leg]} 0->0.68"] = crossing_interp(leg, 0.0, True)
        times[f"{LEG_ORDER[leg]} 0.68->0"] = crossing_interp(leg, 31.0, False) - 31.0
    times["RR 0->0.68"] = crossing_interp(3, 31.0, True) - 31.0
    ramp = model.actuator.ramp_s
    checks = v11_checks(
        v_max=v,
        max_speed_per_leg=run.max_motor_speed_m_s,
        commanded_at_least_vmax=[True, True, True, True],
        pos_min=run.motor_pos_min_m,
        pos_max=run.motor_pos_max_m,
        stroke_times_s=times,
        expected_time_s=expected_full_stroke_time_s(params, ramp),
        reference_time_s=params.actuator.full_stroke_time_s,
        motor_violation_max_m=run.max_motor_violation_m,
        rod_force_dev_N=run.max_force_dev_N,
        ramp_force_N=float(params.legs[0].moving_part.mass_kg) * v / ramp,
    )
    tt, pp, vv, ff = _thin(1500, t, pos, s["motor_vel"], s["motor_force"])
    return {
        "case": "v11",
        "dt_s": model.dt_s,
        "schedule": sched.as_dict(),
        "stroke_times_s": times,
        "expected_full_stroke_time_s": expected_full_stroke_time_s(params, ramp),
        "reference_full_stroke_time_s": params.actuator.full_stroke_time_s,
        "max_speed_m_s": run.max_motor_speed_m_s.tolist(),
        "motor_pos_min_m": run.motor_pos_min_m.tolist(),
        "motor_pos_max_m": run.motor_pos_max_m.tolist(),
        "max_axial_violation_m": run.max_motor_violation_m,
        "max_force_dev_from_rod_weight_N": run.max_force_dev_N.tolist(),
        "expected_ramp_force_N": float(params.legs[0].moving_part.mass_kg) * v / ramp,
        "leg_offset_max_m": float(s["motor_violation"].max()),
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "series": {"t_s": tt, "motor_pos_m": pp, "motor_vel_m_s": vv, "motor_force_N": ff},
        "record": _rel(record_path),
        "timing": {
            "cpu_placement": placement,
            "wall_s": run.wall_s,
            "steps": run.steps,
            "us_per_step": run.wall_s / run.steps * 1e6,
        },
    }


def _crawler_model(params, pose, extensions, dt_s=None):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model

    return L1Model(
        params,
        pose=BodyPose(pose.origin_m, pose.quat_wxyz),
        extensions_m=extensions,
        attach_bushings=False,
        actuator=True,
        dt_s=dt_s,
    )


def run_crawler(level: str) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.runs import run_commanded, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix, roll_pitch_from_quat
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot, save_record, save_snapshot
    from outrigger_sim.scenarios.crawler_settle import (
        crawler_layout,
        crawler_linear_modes,
        crawler_static_pose,
    )
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import fit_damped_sine, rigid_displacement
    from outrigger_sim.verify.reference import (
        LIFT_V4_CRAWLER_ON_FLOOR_MODES,
        LIFT_V4_LAYOUT_D,
        TOTAL_WEIGHT_INCL_RODS_N,
        load_references,
    )
    from outrigger_sim.verify.s1 import v0_checks
    from outrigger_sim.verify.s2b import (
        crawler_gap_checks,
        crawler_settle_checks,
        snapshot_checks,
    )

    params = load_params(level=level)
    refs = load_references()
    layout = crawler_layout(params)
    pose = crawler_static_pose(params)
    linear_pose = crawler_static_pose(params, linear=True)
    modes_lin = crawler_linear_modes(params, pose)
    zeros = (0.0, 0.0, 0.0, 0.0)
    t_build = time.perf_counter()
    model = _crawler_model(params, pose, zeros)
    inventory = model.v0_inventory()
    checks = v0_checks(params, inventory)
    centres_body = np.asarray(inventory["crawler_layout"]["centres_body_m"])
    sup_shapes = inventory["superstructure"]["collision"]
    built_centres = np.asarray([s["pos_local_m"] for s in sup_shapes]) + np.asarray(
        inventory["superstructure"]["com_body_m"]
    )
    radius = layout.sphere_radius_m
    checks += crawler_gap_checks(
        built_centres[:, 2] - radius - params.ground.crawler_bottom_z_m, layout.gap_m
    )
    build_s = time.perf_counter() - t_build

    recorder = _recorder(
        params,
        model,
        f"S2b_crawler_settle_{level}",
        {
            "start": "analytic exact crawler pose (scenarios/crawler_settle)",
            "settle_s": SETTLE_S,
            "still_s": STILL_S,
        },
        placement,
    )
    win = {k: [] for k in ("t", "uz", "roll", "pitch", "fz", "active", "pads", "viol", "nan")}
    sphere_force_sum = np.zeros(layout.n_points)
    n_sphere_samples = 0
    k_sample = 0

    def sample(probe):
        nonlocal sphere_force_sum, n_sphere_samples, k_sample
        _append(recorder, model, probe)
        if probe.t_s < SETTLE_S - 1e-9:
            return
        k_sample += 1
        roll, pitch = roll_pitch_from_quat(probe.body_quat_wxyz)
        win["t"].append(probe.t_s)
        win["uz"].append(probe.body_pos_m[2] * 1e3)
        win["roll"].append(math.degrees(roll))
        win["pitch"].append(math.degrees(pitch))
        win["fz"].append(probe.crawler_contact_world_N[2])
        win["pads"].append(int(np.sum(probe.pad_normal_force_N != 0.0)))
        win["viol"].append(float(np.abs(probe.leg_offset_in_body_m).max()))
        win["nan"].append(not np.all(np.isfinite(probe.body_pos_m)))
        if k_sample % 10 == 1:  # every 10 ms: per-sphere forces (callback)
            rep = model.crawler_sphere_contacts()
            fz = rep.force_world_N[:, 2]
            win["active"].append(int(np.sum(fz > 0.0)))
            sphere_force_sum += fz
            n_sphere_samples += 1

    sched = lambda _t: None  # noqa: E731 - zero command held
    run = run_commanded(model, SETTLE_S + STILL_S, sched, sample_s=1.0e-3, on_sample=sample)
    w = {k: np.asarray(v) for k, v in win.items()}
    window = {
        "u_z_mm": float(w["uz"].mean()),
        "roll_deg": float(w["roll"].mean()),
        "pitch_deg": float(w["pitch"].mean()),
        "roll_span_deg": float(np.ptp(w["roll"])),
        "pitch_span_deg": float(np.ptp(w["pitch"])),
        "crawler_fz_mean_N": float(w["fz"].mean()),
        "crawler_fz_span_N": float(np.ptp(w["fz"])),
        "active_min": int(w["active"].min()),
        "active_max": int(w["active"].max()),
        "pad_contacts_max": int(w["pads"].max()),
        "motor_violation_max_m": float(w["viol"].max()),
        "any_nan": bool(w["nan"].any()),
        "n_samples": int(w["t"].size),
    }
    sphere_mean = sphere_force_sum / max(n_sphere_samples, 1)
    total_weight = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    analytic = {
        "u_z_mm": pose.u_z_m * 1e3,
        "roll_deg": pose.roll_deg,
        "pitch_deg": pose.pitch_deg,
    }
    checks += crawler_settle_checks(
        level=level, analytic=analytic, window=window, quarter_weight_N=total_weight / 4.0
    )
    # snapshot + round trip
    snap = model.snapshot()
    name = f"S2b_crawler_{level}"
    snap_path = save_snapshot(
        snap,
        name,
        directory=STATES,
        overwrite=True,
        note={
            "stage": "S2b",
            "scenario": "crawler settle, legs at 0, analytic exact pose + 10 s settle + 5 s still",
            "level": level,
            "actuator": "L1SpeedActuator (ramp 0.1 s), zero command",
            "ground_bushing_force_point": model.bushing.force_point,
        },
    )
    loaded = load_snapshot(name, params_sha256=params.sha256, directory=STATES)
    rt_run = run_commanded(model, ROUND_TRIP_S, sched, sample_s=ROUND_TRIP_S)
    pos_cont = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in model.bodies])
    fresh = _crawler_model(params, pose, zeros)
    fresh.restore(loaded)
    run_commanded(fresh, ROUND_TRIP_S, sched, sample_s=ROUND_TRIP_S)
    pos_rest = np.array([[b.GetPos().x, b.GetPos().y, b.GetPos().z] for b in fresh.bodies])
    rt_diff = float(np.abs(pos_cont - pos_rest).max())
    checks += snapshot_checks(name, rt_diff)

    # crawler modes: small initial velocity along the three linear mode shapes, from the
    # restored snapshot (fresh model), free vibration
    p0 = fresh.probe()
    rot0 = quat_to_matrix(p0.body_quat_wxyz)
    com_body = modes_lin.com_body_m
    g_world = p0.body_pos_m + rot0 @ com_body
    qdot = np.zeros(3)
    for k, mode_name in enumerate(modes_lin.names):
        dominant = {"heave": 0, "roll": 1, "pitch": 2}[mode_name]
        phi_k = modes_lin.phi[:, k]
        omega_k = 2.0 * math.pi * modes_lin.f_undamped_Hz[k]
        qdot += phi_k * (omega_k * MODE_AMPLITUDE[mode_name] / abs(phi_k[dominant]))
    set_rigid_velocity(fresh, (0.0, 0.0, qdot[0]), (qdot[1], qdot[2], 0.0), g_world)
    mrec = {"t": [], "origin": [], "quat": []}

    def msample(probe):
        mrec["t"].append(probe.t_s)
        mrec["origin"].append(probe.body_pos_m)
        mrec["quat"].append(probe.body_quat_wxyz)

    mrun = run_commanded(fresh, MODES_S, sched, sample_s=1.0e-3, on_sample=msample)
    tm = np.asarray(mrec["t"]) - p0.t_s
    q6 = rigid_displacement(
        np.asarray(mrec["origin"]),
        np.asarray(mrec["quat"]),
        p0.body_pos_m,
        p0.body_quat_wxyz,
        com_body,
    )
    q3 = q6[:, [2, 3, 4]]
    eta = q3 @ (modes_lin.mass_matrix @ modes_lin.phi)
    fitted = []
    for k in range(3):
        f_lin = float(modes_lin.f_damped_Hz[k])
        tau = 1.0 / (modes_lin.zeta[k] * 2.0 * math.pi * modes_lin.f_undamped_Hz[k])
        t_win = min(MODES_S, 6.0 * tau)
        mask = tm <= t_win
        fit = fit_damped_sine(tm[mask], eta[mask, k], f_lin)
        fitted.append(
            {
                "mode": modes_lin.names[k],
                "window_s": t_win,
                "f_damped_Hz": fit.f_damped_Hz,
                "f_undamped_Hz": fit.f_undamped_Hz,
                "zeta": fit.zeta,
                "residual_rms_rel": fit.residual_rms_rel,
                "linear_f_damped_Hz": f_lin,
                "linear_f_undamped_Hz": float(modes_lin.f_undamped_Hz[k]),
                "linear_zeta": float(modes_lin.zeta[k]),
            }
        )
    record_path = save_record(recorder.finish(), RESULTS / f"crawler_{level}", overwrite=True)

    reference = None
    if level == "top":
        settled = refs.get(LIFT_V4_LAYOUT_D)["settled_on_crawler (legs at 0)"]
        ref_modes = refs.get(LIFT_V4_CRAWLER_ON_FLOOR_MODES)
        q_ref = settled["q_about_origin (uz_mm, roll_deg, pitch_deg)"]
        order = layout.reference_order()
        reference = {
            "key_pose": LIFT_V4_LAYOUT_D.notation()
            + " / settled_on_crawler (legs at 0) / q_about_origin (uz_mm, roll_deg, pitch_deg)",
            "q_ref": q_ref,
            "chrono_minus_ref": [
                window["u_z_mm"] - q_ref[0],
                window["roll_deg"] - q_ref[1],
                window["pitch_deg"] - q_ref[2],
            ],
            "linear_analytic_minus_ref": [
                linear_pose.u_z_m * 1e3 - q_ref[0],
                linear_pose.roll_deg - q_ref[1],
                linear_pose.pitch_deg - q_ref[2],
            ],
            "sphere_force_ref_N": settled["crawler_sphere_forces_N"],
            "sphere_force_chrono_ref_order_N": sphere_mean[order].tolist(),
            "sphere_force_chrono_minus_ref_max_abs_N": float(
                np.abs(sphere_mean[order] - np.asarray(settled["crawler_sphere_forces_N"])).max()
            ),
            "sphere_force_chrono_minus_exact_max_abs_N": float(
                np.abs(sphere_mean - pose.sphere_force_N).max()
            ),
            "key_modes": LIFT_V4_CRAWLER_ON_FLOOR_MODES.notation(),
            "modes_ref": {"f_Hz": ref_modes["f_Hz"], "zeta": ref_modes["zeta"]},
            "note": "reference = linear small-angle (no P-delta); the analytic start and "
            "Chrono use exact geometry (P-delta), so the pitch differs by the P-delta share",
        }
    return {
        "case": f"crawler_{level}",
        "level": level,
        "dt_s": model.dt_s,
        "analytic_exact": {
            **analytic,
            "active": int(pose.active.sum()),
            "sphere_force_N": pose.sphere_force_N.tolist(),
            "weight_N": pose.weight_N,
            "kn_per_sphere_float32_N_m": pose.kn_per_sphere_N_m,
            "newton_residual": pose.residual.tolist(),
        },
        "analytic_linear_no_pdelta": {
            "u_z_mm": linear_pose.u_z_m * 1e3,
            "roll_deg": linear_pose.roll_deg,
            "pitch_deg": linear_pose.pitch_deg,
        },
        "window": window,
        "sphere_force_chrono_mean_N": sphere_mean.tolist(),
        "sphere_labels": layout.labels(),
        "end_horizontal_drift_m": (model.probe().body_pos_m[:2]).tolist(),
        "snapshot": {
            "name": name,
            "path": _rel(snap_path),
            "t_s": snap.time_s,
            "round_trip_max_pos_diff_m": rt_diff,
        },
        "modes_linear": {
            "names": list(modes_lin.names),
            "f_undamped_Hz": modes_lin.f_undamped_Hz.tolist(),
            "f_damped_Hz": modes_lin.f_damped_Hz.tolist(),
            "zeta": modes_lin.zeta.tolist(),
            "f_undamped_plain_inertia_Hz": modes_lin.f_undamped_plain_Hz.tolist(),
            "n_active": modes_lin.n_active,
        },
        "modes_chrono": fitted,
        "reference": reference,
        "v0_inventory_crawler": inventory["crawler_layout"]
        | {"centres_body_m": centres_body.tolist()},
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "record": _rel(record_path),
        "timing": {
            "cpu_placement": placement,
            "build_s": build_s,
            "settle_wall_s": run.wall_s,
            "round_trip_wall_s": rt_run.wall_s,
            "modes_wall_s": mrun.wall_s,
            "us_per_step": run.wall_s / run.steps * 1e6,
        },
    }


def _event_start(params, case):
    from outrigger_sim.scenarios.crawler_settle import crawler_static_pose, pad_touch_extension_m

    ext = [0.0, 0.0, 0.0, 0.0]
    pose = crawler_static_pose(params)
    for _ in range(3):
        touch = pad_touch_extension_m(params, case.leg, pose.origin_m, pose.quat_wxyz)
        ext[case.leg] = touch - case.start_gap_m
        pose = crawler_static_pose(params, tuple(ext))
    touch = pad_touch_extension_m(params, case.leg, pose.origin_m, pose.quat_wxyz)
    return pose, tuple(ext), touch


def run_event(name: str, dt_s: float) -> dict:
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    import numpy as np

    from outrigger_sim.chrono.ground_bushing import EVENT_REMOVE
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import load_params
    from outrigger_sim.record import save_record
    from outrigger_sim.scenarios.stroke import event_cases
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.s2b import event_checks

    params = load_params(level="top")
    case = next(c for c in event_cases(params) if c.name == name)
    pose, ext, touch = _event_start(params, case)
    model = _crawler_model(params, pose, ext, dt_s=dt_s)
    sched = case.schedule()
    case_name = f"event_{name}_dt{dt_s:.0e}"
    recorder = _recorder(
        params,
        model,
        f"S2b_event_{name}",
        {
            "case": case.__dict__,
            "schedule": sched.as_dict(),
            "start_extensions_m": list(ext),
            "touch_extension_m": touch,
        },
        placement,
    )
    run = run_commanded(
        model, sched.end_s, sched, sample_s=1.0e-3, on_sample=lambda p: _append(recorder, model, p)
    )
    for e in run.events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    record_path = save_record(recorder.finish(), RESULTS / case_name, overwrite=True)
    t0 = run.t_start_s
    events = [[e.t_s - t0, e.leg, e.kind] for e in run.events]
    trans = [[t - t0, leg, state] for (t, leg, state) in run.raw_contact_transitions]
    leg_trans = [tr for tr in trans if tr[1] == case.leg]
    # R15 timing: removal vs the last off-transition before it; creation vs N > N_th crossing
    lift = []
    for ev in events:
        if ev[2] == EVENT_REMOVE:
            offs = [tr[0] for tr in leg_trans if tr[2] == 0 and tr[0] <= ev[0] + 1e-12]
            if offs:
                lift.append(
                    {
                        "t_remove_s": ev[0],
                        "t_last_N_le_0_start_s": offs[-1],
                        "delay_s": ev[0] - offs[-1],
                    }
                )
    s = run.series
    t = s["t"] - t0
    f_leg = s["pad_normal"][:, case.leg]
    checks = event_checks(case_name, events, case.expected_events())
    tt, ff, cyl, sr, uu = _thin(
        2000,
        t,
        f_leg,
        s["motor_force"][:, case.leg],
        s["s_ref"][:, case.leg],
        s["u_applied"][:, case.leg],
    )
    return {
        "case": case_name,
        "event_case": case.__dict__,
        "dt_s": model.dt_s,
        "n_lift_steps": model.bushing.n_lift,
        "lift_time_s": model.bushing.lift_time_s,
        "touch_threshold_N": model.bushing.touch_threshold_N,
        "start_extensions_m": list(ext),
        "touch_extension_m": touch,
        "events": events,
        "raw_transitions_leg": leg_trans,
        "n_raw_transitions_leg": len(leg_trans),
        "first_positive_N_s": (run.first_positive_N_t_s - t0).tolist(),
        "lift_timing": lift,
        "max_pad_force_N": float(f_leg.max()),
        "max_cylinder_force_N": float(s["motor_force"][:, case.leg].max()),
        "max_axial_violation_m": run.max_motor_violation_m,
        "max_speed_m_s": run.max_motor_speed_m_s.tolist(),
        "yield_steps": model.bushing.yield_steps.tolist(),
        "slip_total_m": model.bushing.slip_total_m.tolist(),
        "other_legs_max_N": float(
            np.abs(s["pad_normal"][:, [i for i in range(4) if i != case.leg]]).max()
        ),
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "series": {
            "t_s": tt,
            "pad_normal_N": ff,
            "motor_force_N": cyl,
            "s_ref_m": sr,
            "u_applied_m_s": uu,
        },
        "record": _rel(record_path),
        "timing": {
            "cpu_placement": placement,
            "wall_s": run.wall_s,
            "steps": run.steps,
            "us_per_step": run.wall_s / run.steps * 1e6,
        },
    }


def run_case(name: str) -> dict:
    if name == "air_short":
        out = run_air_short()
    elif name == "v11":
        out = run_v11()
    elif name.startswith("crawler_"):
        out = run_crawler(name.removeprefix("crawler_"))
    elif name.startswith("event_"):
        body, dt_text = name.removeprefix("event_").rsplit("_dt", 1)
        out = run_event(body, float(dt_text))
    else:
        raise SystemExit(f"unknown case {name!r}; cases: {CASES}")
    folder = RESULTS / name
    folder.mkdir(parents=True, exist_ok=True)
    out["generated"] = _dt.datetime.now().isoformat(timespec="seconds")
    (folder / "result.json").write_text(
        json.dumps(_plain(out), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{name}: all_passed={out['all_passed']}", flush=True)
    return out


def _run_case_process(name: str) -> str:
    t0 = time.perf_counter()
    done = subprocess.run(
        [PY, "-I", "-u", str(Path(__file__).resolve()), "case", name],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    tail = (done.stdout.strip().splitlines() or [""])[-1]
    msg = f"{name}: rc={done.returncode} {time.perf_counter() - t0:.1f}s {tail}"
    if done.returncode != 0:
        msg += "\n" + done.stderr[-3000:]
    print(msg, flush=True)
    return msg


def run_all(names=CASES) -> None:
    # longest first so the 4 slots stay busy
    order = sorted(names, key=lambda n: (0 if "slow" in n and "1e-05" in n else 1, n))
    with ThreadPoolExecutor(max_workers=MAX_PROCESSES) as pool:
        list(pool.map(_run_case_process, order))
    summarize()


# --- summary ---------------------------------------------------------------------------------


def summarize() -> None:

    from outrigger_sim.chrono.actuators import ACCEL_RAMP_S
    from outrigger_sim.chrono.ground_bushing import LIFT_TIME_S, TOUCH_THRESHOLD_N
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.s2b import event_dt_checks

    results = {}
    for name in CASES:
        p = RESULTS / name / "result.json"
        if p.is_file():
            results[name] = json.loads(p.read_text(encoding="utf-8"))
    extra_checks = []
    event_pairs = {}
    for ev in EVENT_NAMES:
        a = results.get(f"event_{ev}_dt1e-04")
        b = results.get(f"event_{ev}_dt1e-05")
        if a and b:
            extra_checks += event_dt_checks(ev, a["events"], b["events"])
            if len(a["events"]) == len(b["events"]):
                event_pairs[ev] = {
                    "events_dt1e-4": a["events"],
                    "events_dt1e-5": b["events"],
                    "time_diff_s": [
                        x[0] - y[0] for x, y in zip(a["events"], b["events"], strict=True)
                    ],
                    "first_positive_N_s": [a["first_positive_N_s"][0], b["first_positive_N_s"][0]],
                    "raw_transitions": [a["n_raw_transitions_leg"], b["n_raw_transitions_leg"]],
                    "lift_timing": [a["lift_timing"], b["lift_timing"]],
                }
    table = []
    for name, r in results.items():
        for c in r["checks"]:
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
    for c in summary_table(extra_checks):
        table.append(
            {
                "case": "events dt pair",
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
    crawler = {
        r["level"]: {
            "analytic_exact": {
                k: r["analytic_exact"][k] for k in ("u_z_mm", "roll_deg", "pitch_deg", "active")
            },
            "analytic_linear_no_pdelta": r["analytic_linear_no_pdelta"],
            "chrono_window": {
                k: r["window"][k]
                for k in (
                    "u_z_mm",
                    "roll_deg",
                    "pitch_deg",
                    "active_min",
                    "active_max",
                    "roll_span_deg",
                    "pitch_span_deg",
                )
            },
            "modes_linear": r["modes_linear"],
            "modes_chrono": r["modes_chrono"],
            "reference": r["reference"],
            "snapshot": r["snapshot"],
        }
        for name, r in results.items()
        if name.startswith("crawler_")
    }
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S2b (chrono_build_plan.md): actuator (V0 motor sign, V11, command ramp), "
            "crawler contact layout D (V0, settle, snapshots), R15 events",
            "script": "04_scripts/02_chrono/run_S2b.py",
            "model": "outrigger_sim.chrono.model.L1Model(actuator=True), L1SpeedActuator "
            "(position motor + ChFunctionConst.SetConstant(s_ref), rate limit), crawler 24 "
            "spheres, ground bushing GroundBushingCoulomb (ball centre)",
            "assumptions": {
                "command_ramp_s": ACCEL_RAMP_S,
                "ramp_source": "user decision 2026-10-20 (CLAUDE.md), not in the YAML",
                "stroke_end": "braking with the same acceleration limit (target speed <= "
                "sqrt(2 a d)); assumption of this implementation",
                "R15": {"t_lift_s": LIFT_TIME_S, "N_th_N": TOUCH_THRESHOLD_N},
                "event_schedules": "scenarios/stroke.event_cases (test magnitudes)",
                "mode_amplitudes": {k: v for k, v in MODE_AMPLITUDE.items()},
            },
            "judgement": "automatic pre-check; final physical judgement by dynamics-expert",
            "python": platform.python_version(),
            "host": os.environ.get("COMPUTERNAME", ""),
            "raw_data": {
                name: {"record": r["record"], "result": f"07_results/S2b/{name}/result.json"}
                for name, r in results.items()
            },
            "figure": _rel(FIGURE),
        },
        "passed_by_id": by_id,
        "all_passed": all(by_id.values()) if by_id else False,
        "v0_motor_sign_and_ramp": results.get("air_short", {}).get("sign_test"),
        "ramp_spikes": results.get("air_short", {}).get("spikes"),
        "v11": {
            k: results["v11"][k]
            for k in (
                "stroke_times_s",
                "expected_full_stroke_time_s",
                "reference_full_stroke_time_s",
                "max_speed_m_s",
                "motor_pos_min_m",
                "motor_pos_max_m",
                "max_axial_violation_m",
                "max_force_dev_from_rod_weight_N",
                "expected_ramp_force_N",
                "timing",
            )
        }
        if "v11" in results
        else None,
        "crawler": crawler,
        "events": {
            name: {
                k: r[k]
                for k in (
                    "dt_s",
                    "events",
                    "n_raw_transitions_leg",
                    "first_positive_N_s",
                    "lift_timing",
                    "max_pad_force_N",
                    "max_cylinder_force_N",
                    "max_axial_violation_m",
                    "yield_steps",
                    "other_legs_max_N",
                    "touch_extension_m",
                    "timing",
                )
            }
            for name, r in results.items()
            if name.startswith("event_")
        },
        "event_dt_pairs": event_pairs,
        "checks": table,
    }
    SUMMARY.write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    _figure(results)
    print(f"summary: {_rel(SUMMARY)} all_passed={summary['all_passed']} {by_id}", flush=True)


def _figure(results) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)
    ax = axes[0, 0]
    if "v11" in results:
        s = results["v11"]["series"]
        t = np.asarray(s["t_s"])
        pos = np.asarray(s["motor_pos_m"])
        for i, leg in enumerate(("FL", "FR", "RL", "RR")):
            ax.plot(t, pos[:, i] * 1e3, label=leg)
        ax.set_xlabel("time [s]")
        ax.set_ylabel("motor position [mm]")
        ax.set_title("V11: legs in the air, commands beyond v_max and the stroke ends")
        ax.legend(loc="center right")
    ax = axes[0, 1]
    if "air_short" in results:
        sp = results["air_short"]["spikes"]
        labels = [c["name"] for c in sp]
        vals = [max(c["max_force_dev_N"]) for c in sp]
        ax.bar(labels, vals, color=["#4C72B0" if c["ramp_s"] > 0 else "#C44E52" for c in sp])
        ax.set_yscale("log")
        ax.set_ylabel("max |F_motor + m_rod g| [N]")
        ax.set_title("Inertial reaction of a +v_max command (ramp 0.1 s vs step)")
        for k, v in enumerate(vals):
            ax.text(k, v, f"{v:,.0f} N", ha="center", va="bottom", fontsize=8)
    ax = axes[1, 0]
    for name, style in (("event_fast_FL_dt1e-04", "-"), ("event_fast_FL_dt1e-05", "--")):
        if name in results:
            s = results[name]["series"]
            ax.plot(
                np.asarray(s["t_s"]),
                np.asarray(s["pad_normal_N"]) / 1e3,
                style,
                label=f"{name.split('_dt')[1]}: pad normal force",
            )
            for ev in results[name]["events"]:
                ax.axvline(ev[0], color="g" if ev[2] == 1 else "r", ls=style, lw=0.8)
    ax.set_xlabel("time [s]")
    ax.set_ylabel("FL pad normal force [kN]")
    ax.set_title("R15 event test (fast, v_max): green = bushing created, red = removed")
    ax.legend()
    ax = axes[1, 1]
    levels = [lv for lv in LEVELS if f"crawler_{lv}" in results]
    if levels:
        x = np.arange(3)
        width = 0.25
        for k, lv in enumerate(levels):
            r = results[f"crawler_{lv}"]
            f_ch = [m["f_undamped_Hz"] for m in r["modes_chrono"]]
            f_li = r["modes_linear"]["f_undamped_Hz"]
            ax.bar(x + (k - 1) * width, f_ch, width, label=f"{lv} Chrono")
            ax.plot(x + (k - 1) * width, f_li, "k_", markersize=14)
        ax.set_xticks(x, results[f"crawler_{levels[0]}"]["modes_linear"]["names"])
        ax.set_ylabel("frequency [Hz]")
        ax.set_title("Crawler modes, legs at 0 (bars: Chrono fit, black: linear model)")
        ax.legend()
    fig.savefig(FIGURE, dpi=130)
    plt.close(fig)


def main(argv: list[str]) -> None:
    if not argv or argv[0] == "all":
        run_all()
    elif argv[0] == "case" and len(argv) == 2:
        run_case(argv[1])
    elif argv[0] == "cases":
        run_all(tuple(argv[1:]))
    elif argv[0] == "summary":
        summarize()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
