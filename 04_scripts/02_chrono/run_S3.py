"""S3 runs: V8(a) numerical damping, V4 lift from the crawler, V5, V6, V9 time-step convergence,
open-loop command replay (control item 1).

``00_docs/03_chrono/chrono_build_plan.md`` S3; checks in ``outrigger_sim.verify.s3``.
Usage (Chrono-dev python, from any folder)::

    python -I -u run_S3.py run [--jobs 6] [--only NAME ...]   # cases (batch.run_cases) + summary
    python -I -u run_S3.py replay                             # control item 1 (needs v4_D_w1e-04)
    python -I -u run_S3.py summary                            # rebuild the summary

Cases (L1, top, crawler layout D, actuator with the 0.1 s command ramp):

* ``v8a_pads_dt<dt>`` (dt 1e-4, 2e-4): every physical damping off (pad and crawler ``g_n`` = 0,
  bushing ``c`` = 0, YAML overrides), legs locked at ``e_op``, analytic static start, initial
  velocity along all six rev. 13 modes (5 J each, ASSUMPTION: amplitude), 60 s. Energy
  (kinetic + gravity + contact and bushing springs) and the numerical zeta of modes 1-6.
* ``v8a_crawler_dt<dt>``: same, legs at 0 on the crawler spheres (analytic exact pose), heave /
  roll / pitch crawler modes; energy only (no tangential stiffness on the crawler, R8).
* ``v4_D_w<dt>``: V4 lift from the S2b crawler snapshot; ``dt`` outside the transition window,
  ``simulation.dt_transition_s`` inside (``scenarios/lift``). ``v4_D_wdefault`` runs at the
  YAML ``simulation.L1.dt_s`` (2e-4 s since the 2026-10-21 regeneration) and is the judged V4
  run (``verify.s3.V4_JUDGED_RUN``); ``v4_D_w1e-04``, the judged run of the first S3 batch,
  stays as a comparison record (summary ``v4_judged.comparison``) and as the replay source.
* ``v4_Dx3_w1e-04``: crawler ``k_n`` x3 sensitivity (YAML ``kn_total_sensitivity_range_N_m``,
  ``g_n`` x sqrt(3) for the same heave zeta as the reference block), analytic start + 3 s hold.
* ``v4_D_u<dt>`` (2e-4, 1e-4, 5e-5, 1e-5): V4 at one uniform dt (V9 differences).
* ``v5``: S1 snapshot, FL +1 mm then +5 mm at 0.5 mm/s, 10 s settles (dt 1e-4 s);
  ``v5_default``: the same at the YAML ``simulation.L1.dt_s``.
* ``v6_FLp``, ``v6_FLm`` (0.1 mm/s), ``v6_FLp_fast`` (0.5 mm/s, quasi-static check).
* ``v9_step_dt<dt>``: S1 snapshot, FL +1 mm at v_max (ramped, soft-limit stop), 12 s.
* ``v9_free_dt<dt>``: S1 snapshot, V7 roll initial velocity (0.02 deg), 6 s; mode 1 at 5 s.

Outputs: ``07_results/S3/<batch>/<case>/`` (case.json from the batch runner, result.json,
Record for the main runs), ``07_results/S3/index.json`` (latest directory per case), summary
``06_analysis/01_chrono/verify_S3_L1.json`` and ``verify_S3_L1.png``.
Units SI; angles in deg where named ``*_deg``; V4 times from the equivalent origin (``*_eq``).
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

RESULTS = ROOT / "07_results" / "S3"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states"
SUMMARY = ROOT / "06_analysis" / "01_chrono" / "verify_S3_L1.json"
FIGURE = ROOT / "06_analysis" / "01_chrono" / "verify_S3_L1.png"
LEVEL = "top"
S1_SNAPSHOT = "S1_L1_top"
CRAWLER_SNAPSHOT = "S2b_crawler_top"
MAX_WORKERS = 6
"""Main-session rule for S3: at most 6 Chrono processes at once (of 8 P-cores)."""
CASE_TIMEOUT_S = 1500.0
V9_DTS = (2.0e-4, 1.0e-4, 5.0e-5)
V9_REF_DT = 1.0e-5
V8A_DTS = (1.0e-4, 2.0e-4)
V8A_WINDOW_S = 60.0
V8A_MODE_ENERGY_J = 5.0
"""Initial kinetic energy per mode in V8(a) (ASSUMPTION: small, no yield, energy >> float32
contact-force noise)."""
V8A_CRAWLER_AMPLITUDE = {"pitch": math.radians(0.01), "roll": math.radians(0.01), "heave": 1.0e-4}
"""Crawler-mode amplitudes (ASSUMPTION: every active sphere stays in contact; checked by
``sphere_contact_changes``. Twice these made the rear roller row (lightest, delta 1.15 mm) lose
contact about 320 times in 60 s)."""
V8A_TREND_BLOCK_S = 1.0
"""Energy trend: linear fit of 1-s block means (the semi-implicit Euler energy oscillation of
order omega dt / 2 averages out; recorded for dyn, not the plan's judged quantity)."""
V5_SPEED_M_S = 0.5e-3
V6_SPEED_M_S = 0.1e-3
V6_FAST_SPEED_M_S = 0.5e-3
V6_BEYOND_LIFTOFF_M = 0.6e-3
V6_WINDOW_BEFORE_LIFTOFF_M = 0.3e-3
V9_STEP_HOLD_S = 0.5
V9_STEP_END_S = 12.0
V9_FREE_S = 6.0
V9_FREE_AT_S = 5.0
X3_HOLD_S = 3.0
SAMPLE_S = 1.0e-3
COARSE_SAMPLE_S = 1.0e-2


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
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:  # outside the project (smoke runs)
        return str(p).replace("\\", "/")


def _thin(n_points, *arrays):
    import numpy as np

    n = len(arrays[0])
    idx = np.unique(np.linspace(0, n - 1, min(n, n_points)).round().astype(int))
    return [np.asarray(a)[idx] for a in arrays]


def case_ids() -> list[str]:
    ids = [f"v8a_pads_dt{dt:.0e}" for dt in V8A_DTS]
    ids += [f"v8a_crawler_dt{dt:.0e}" for dt in V8A_DTS]
    ids += ["v4_D_w1e-04", "v4_D_w2e-04", "v4_Dx3_w1e-04"]
    ids += [f"v4_D_u{dt:.0e}" for dt in (*V9_DTS, V9_REF_DT)]
    ids += ["v4_D_wdefault", "v5", "v5_default", "v6_FLp", "v6_FLm", "v6_FLp_fast"]
    ids += [f"v9_step_dt{dt:.0e}" for dt in (*V9_DTS, V9_REF_DT)]
    ids += [f"v9_free_dt{dt:.0e}" for dt in (*V9_DTS, V9_REF_DT)]
    ids += [f"v4touch_dt{dt:.0e}" for dt in (*V9_DTS, V9_REF_DT)]
    return ids


# --- shared helpers ---------------------------------------------------------------------------


def _run_meta(params, model, scenario, settings, extra=None):
    from outrigger_sim.record import make_run_meta
    from outrigger_sim.verify.reference import load_references

    return make_run_meta(
        params,
        model.meta(),
        scenario=scenario,
        scenario_settings=settings,
        reference_sha256=load_references().sha256_by_file(),
        extra=extra or {},
    )


def _attitude_deg(quats):
    import numpy as np

    from outrigger_sim.frames import roll_pitch_from_quat

    r, p = roll_pitch_from_quat(np.asarray(quats))
    return np.degrees(np.column_stack([np.atleast_1d(r), np.atleast_1d(p)]))


def _collector(model, recorder=None):
    """Sample hook collecting copies of the probe values (and a Record if given)."""
    import numpy as np

    from outrigger_sim.signals import Command

    rows = {k: [] for k in ("t", "origin", "quat", "N", "Fcyl", "s_ref", "s_motor", "u_cmd",
                            "Fcrawler", "viol", "bush_t")}

    def sample(probe):
        rows["t"].append(probe.t_s)
        rows["origin"].append(probe.body_pos_m)
        rows["quat"].append(probe.body_quat_wxyz)
        rows["N"].append(probe.pad_normal_force_N)
        rows["Fcyl"].append(probe.motor_force_N)
        rows["s_motor"].append(probe.motor_pos_m)
        rows["Fcrawler"].append(probe.crawler_contact_world_N)
        rows["viol"].append(float(np.abs(probe.leg_offset_in_body_m).max()))
        bf = np.asarray(probe.bushing_force_world_N, dtype=float)
        rows["bush_t"].append(np.where(np.isnan(bf[:, 0]), 0.0, np.hypot(bf[:, 0], bf[:, 1])))
        if model.actuator is not None:
            rows["s_ref"].append(model.actuator.acting_s_ref_m)
            rows["u_cmd"].append(model.actuator.command_m_s)
        if recorder is not None:
            cmd = np.zeros(4) if model.actuator is None else model.actuator.command_m_s
            recorder.append(model.truth(probe), Command(t_s=probe.t_s, leg_speed_m_s=cmd))

    def arrays():
        return {k: np.asarray(v) for k, v in rows.items()}

    return sample, arrays


def _window_mean(t, values, t0, t1):
    import numpy as np

    mask = (t >= t0 - 1e-9) & (t <= t1 + 1e-9)
    if not np.any(mask):
        raise ValueError(f"no samples in [{t0}, {t1}]")
    return np.asarray(values)[mask].mean(axis=0)


def _crawler_model(params, pose, dt_s):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model

    return L1Model(
        params,
        pose=BodyPose(pose.origin_m, pose.quat_wxyz),
        extensions_m=(0.0, 0.0, 0.0, 0.0),
        attach_bushings=False,
        actuator=True,
        dt_s=dt_s,
    )


def _pads_model_from_s1(params, refs, dt_s, *, actuator=True):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt_s, actuator=actuator)
    snap = load_snapshot(S1_SNAPSHOT, params_sha256=params.sha256, directory=STATES)
    t0 = model.restore(snap)
    return model, t0


def _crawler_min_gap_m(model):
    import numpy as np

    sup = model.superstructure
    r = model.crawler_layout.sphere_radius_m
    gaps = []
    for c in model.crawler_centres_local_m:
        import pychrono as ch

        p = sup.TransformPointLocalToParent(ch.ChVector3d(*c))
        gaps.append(p.z - r - model.floor_z_m)
    return float(np.min(gaps))


# --- V8(a) ------------------------------------------------------------------------------------


def _angular_momentum_z(model, point_world):
    """Vertical angular momentum of every non-fixed body about ``point_world`` [kg m^2/s]."""
    import numpy as np

    from outrigger_sim.frames import quat_to_matrix

    lz = 0.0
    c = np.asarray(point_world, dtype=float)
    for body in model.bodies:
        m = float(body.GetMass())
        p = body.GetPos()
        v = body.GetPosDt()
        r = np.array([p.x, p.y, p.z]) - c
        q = body.GetRot()
        rot = quat_to_matrix(np.array([q.e0, q.e1, q.e2, q.e3]))
        xx = body.GetInertiaXX()
        xy = body.GetInertiaXY()
        inertia = np.array([[xx.x, xy.x, xy.y], [xy.x, xx.y, xy.z], [xy.y, xy.z, xx.z]])
        w = body.GetAngVelLocal()
        h_world = rot @ (inertia @ np.array([w.x, w.y, w.z]))
        lz += float(h_world[2]) + m * float(r[0] * v.y - r[1] * v.x)
    return lz


def _zero_damping_overrides(params):
    over = {"contact.crawler.gn_per_sphere_1_s": 0.0}
    for leg in ("FL", "FR", "RL", "RR"):
        over[f"contact.rigid_floor.L1.gn_per_pad_1_s.{leg}"] = 0.0
        over[f"contact.rigid_floor.L1.bushing_damping_input_per_pad_N_s_m.{leg}"] = 0.0
    return over


def job_v8a(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.energy import ENERGY_COLUMNS, EnergyMeter
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.crawler_settle import crawler_linear_modes, crawler_static_pose
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.scenarios.settle import analytic_static_pose
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import fit_damped_sum, modal_coordinates, rigid_displacement
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s3 import v8a_checks, v8a_crawler_checks

    s = case.settings
    dt = float(s["dt"])
    where = s["where"]
    base = load_params(level=LEVEL)
    params = load_params(level=LEVEL, overrides=_zero_damping_overrides(base))
    refs = load_references()
    modal = modal_reference(refs, LEVEL)
    if where == "pads":
        sp = analytic_static_pose(params, refs, operating_extensions_m(params))
        model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt)
        p0 = model.probe()
        rot0 = quat_to_matrix(p0.body_quat_wxyz)
        point = p0.body_pos_m + rot0 @ modal.reference_point_body_m
        qdot = modal.phi @ np.full(6, math.sqrt(2.0 * V8A_MODE_ENERGY_J))
        set_rigid_velocity(model, qdot[:3], qdot[3:], point)
        excitation = {"modal_energy_J_each": V8A_MODE_ENERGY_J, "qdot_ref_point": qdot.tolist(),
                      "ref_point_world_m": point.tolist()}
    else:
        pose = crawler_static_pose(params)
        model = L1Model(
            params,
            pose=BodyPose(pose.origin_m, pose.quat_wxyz),
            extensions_m=(0.0, 0.0, 0.0, 0.0),
            attach_bushings=False,
            dt_s=dt,
        )
        modes = crawler_linear_modes(params, pose)
        p0 = model.probe()
        rot0 = quat_to_matrix(p0.body_quat_wxyz)
        g_world = p0.body_pos_m + rot0 @ modes.com_body_m
        q3 = np.zeros(3)
        for k, name in enumerate(modes.names):
            dom = {"heave": 0, "roll": 1, "pitch": 2}[name]
            phi_k = modes.phi[:, k]
            om = 2.0 * math.pi * modes.f_undamped_Hz[k]
            q3 += phi_k * (om * V8A_CRAWLER_AMPLITUDE[name] / abs(phi_k[dom]))
        set_rigid_velocity(model, (0.0, 0.0, q3[0]), (q3[1], q3[2], 0.0), g_world)
        # zero vertical angular momentum: roll rate alone carries L_z = I_zx w_x, and with no
        # yaw stiffness on the crawler (R8) the machine would yaw steadily (0.38 deg/s here)
        # until spheres leave the crawler strips (diverged after ~26 s in the first run)
        lz0 = _angular_momentum_z(model, g_world)
        set_rigid_velocity(model, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0e-3), g_world)
        lz1 = _angular_momentum_z(model, g_world)
        wz = -1.0e-3 * lz0 / (lz1 - lz0)
        set_rigid_velocity(model, (0.0, 0.0, 0.0), (0.0, 0.0, wz - 1.0e-3), g_world)
        excitation = {"crawler_mode_amplitudes": V8A_CRAWLER_AMPLITUDE, "qdot": q3.tolist(),
                      "yaw_rate_for_zero_Lz_rad_s": wz,
                      "Lz_after_kg_m2_s": _angular_momentum_z(model, g_world)}
    meter = EnergyMeter(model, crawler=(where == "crawler"))
    rows = []
    geo = []
    track = {"t": [], "origin": [], "quat": []}
    contact_state = {"prev": None, "changes": 0}

    def on_sample(probe):
        e = meter.read(probe)
        rows.append(e.as_row())
        geo.append(meter.contact_energy_geometric(probe))
        if where == "crawler":
            st = meter.crawler_penetrations_m() > 0.0
            if contact_state["prev"] is not None:
                contact_state["changes"] += int(np.sum(st != contact_state["prev"]))
            contact_state["prev"] = st
        track["t"].append(probe.t_s)
        track["origin"].append(probe.body_pos_m)
        track["quat"].append(probe.body_quat_wxyz)

    t_build = time.perf_counter()
    run = run_free_vibration(model, V8A_WINDOW_S, sample_s=SAMPLE_S, on_sample=on_sample)
    wall = time.perf_counter() - t_build
    e = np.asarray(rows)
    g = np.asarray(geo)
    total_force = e[:, -1]
    # geometric contact spring energy (double precision) instead of F^2 / 2k (float32 noise)
    total_geo = e[:, 1] + e[:, 2] + g[:, 0] + g[:, 1] + e[:, 5]
    kin0 = float(e[0, 1])
    rise_force = float(np.max(total_force - total_force[0]) / kin0)
    rise_geo = float(np.max(total_geo - total_geo[0]) / kin0)
    drop_geo = float((total_geo[-1] - total_geo[0]) / kin0)
    t_e = e[:, 0] - e[0, 0]
    n_blk = int(V8A_WINDOW_S / V8A_TREND_BLOCK_S)
    blk = np.array([((total_geo - total_geo[0])[(t_e >= i * V8A_TREND_BLOCK_S)
                                               & (t_e < (i + 1) * V8A_TREND_BLOCK_S)]).mean()
                    for i in range(n_blk)]) / kin0
    trend_slope = float(np.polyfit((np.arange(n_blk) + 0.5) * V8A_TREND_BLOCK_S, blk, 1)[0])
    osc_p2p_first5 = float(np.ptp((total_geo - total_geo[0])[t_e < 5.0]) / kin0)
    np.savez_compressed(case_dir / "energy.npz", energy=e, contact_geometric=g,
                        columns=np.array(ENERGY_COLUMNS))
    zeta_fit = None
    modes_out = None
    t = np.asarray(track["t"]) - track["t"][0]
    rots = quat_to_matrix(np.asarray(track["quat"]))
    yaw_deg = np.degrees(np.arctan2(rots[:, 1, 0], rots[:, 0, 0]))
    excitation["yaw_max_abs_deg"] = float(np.max(np.abs(yaw_deg - yaw_deg[0])))
    if where == "pads":
        q = rigid_displacement(np.asarray(track["origin"]), np.asarray(track["quat"]),
                               p0.body_pos_m, p0.body_quat_wxyz, modal.reference_point_body_m)
        eta = modal_coordinates(q, modal.phi, modal.mass_matrix)
        np.savez_compressed(case_dir / "modal.npz", t=t, eta=eta)
        pred, _src = modal.zeta_num_at(dt)
        zeta_fit = []
        modes_out = []
        for k in range(6):
            om = 2.0 * math.pi * modal.f_damped_Hz[k]
            win = min(V8A_WINDOW_S, 4.0 / (max(pred[k], 1e-6) * om))
            mask = np.flatnonzero(t <= win)[::2]  # 2 ms: >= 60 samples per period of mode 6
            fit = fit_damped_sum(t[mask], eta[mask, k], modal.f_damped_Hz, np.maximum(pred, 1e-5))
            # the dominant component near this mode's frequency (the free fit may let another
            # component take the mode and leave a small one at the guess)
            near = [c for c in fit.components
                    if abs(c.f_damped_Hz / float(modal.f_damped_Hz[k]) - 1.0) < 0.02]
            comp = max(near, key=lambda c: c.amplitude) if near else fit.components[k]
            zeta_fit.append(comp.zeta)
            modes_out.append({
                "mode": k + 1,
                "window_s": win,
                "f_damped_Hz": comp.f_damped_Hz,
                "zeta_num_fit": comp.zeta,
                "zeta_num_pred": float(pred[k]),
                "ratio_to_pred": comp.zeta / float(pred[k]),
                "limit_0p1_zeta": 0.1 * float(modal.zeta[k]),
                "amplitude": comp.amplitude,
                "leakage_amplitudes": [c.amplitude for c in fit.components],
                "residual_rms_rel": fit.residual_rms_rel,
                "fit_success": fit.success,
            })
    else:
        # crawler: modal decay with every physical damping off; zeta < 0 = energy gain
        # (explicit SMC contact should give zeta ~ 0, dynamics_model.md 5.5 (1))
        q6 = rigid_displacement(np.asarray(track["origin"]), np.asarray(track["quat"]),
                                p0.body_pos_m, p0.body_quat_wxyz, modes.com_body_m)
        q3c = q6[:, [2, 3, 4]]
        eta_c = q3c @ (modes.mass_matrix @ modes.phi)
        modes_out = []
        mask = np.flatnonzero(t >= 0.0)[::2]
        for k, name in enumerate(modes.names):
            fit = fit_damped_sum(t[mask], eta_c[mask, k], modes.f_undamped_Hz,
                                 np.full(len(modes.names), 1.0e-5))
            comp = fit.components[k]
            modes_out.append({
                "mode": name,
                "f_damped_Hz": comp.f_damped_Hz,
                "f_linear_Hz": float(modes.f_undamped_Hz[k]),
                "zeta_fit": comp.zeta,
                "energy_rate_rel_per_s": -2.0 * comp.zeta * 2.0 * math.pi * comp.f_damped_Hz,
                "amplitude": comp.amplitude,
                "residual_rms_rel": fit.residual_rms_rel,
                "fit_success": fit.success,
            })
    recorded = None
    if where == "pads":
        checks = v8a_checks(
            case.case_id,
            dt_s=dt,
            energy_rise_rel=rise_geo,
            zeta_num_fit=zeta_fit or [0.0] * 6,
            zeta_ref=modal.zeta,
            zeta_pred=None if zeta_fit is None else modal.zeta_num_at(dt)[0],
            key_zeta=modal.keys["zeta"],
            yield_steps=model.bushing.yield_steps.tolist(),
            n_events=len(run.events),
        )
    else:
        # dynamics_model.md 5.7 (a): modal zeta + 1-s mean trend judged, max(E - E0) recorded
        phys = crawler_linear_modes(base, crawler_static_pose(base))
        zeta_phys = {n: float(z) for n, z in zip(phys.names, phys.zeta, strict=True)}
        for m_out in modes_out:
            m_out["zeta_physical"] = zeta_phys[m_out["mode"]]
        checks, recorded = v8a_crawler_checks(
            case.case_id,
            dt_s=dt,
            energy_rise_rel=rise_geo,
            energy_trend_rel_over_window=trend_slope * V8A_WINDOW_S,
            window_s=V8A_WINDOW_S,
            modes=modes_out,
            zeta_physical=zeta_phys,
            n_events=len(run.events),
        )
    tt, et, ef = _thin(3000, t, total_geo - total_geo[0], total_force - total_force[0])
    summary = {
        "case": case.case_id,
        "where": where,
        "dt_s": dt,
        "overrides": dict(params.overrides),
        "excitation": excitation,
        "E_kin0_J": kin0,
        "energy_rise_rel_geometric": rise_geo,
        "energy_rise_rel_force_based": rise_force,
        "energy_change_end_rel_geometric": drop_geo,
        "energy_span_J": float(np.ptp(total_geo)),
        "energy_trend_rel_per_s": trend_slope,
        "energy_trend_rel_over_window": trend_slope * V8A_WINDOW_S,
        "energy_oscillation_p2p_rel_first5s": osc_p2p_first5,
        "sphere_contact_changes": contact_state["changes"] if where == "crawler" else None,
        "modes": modes_out,
        "recorded_only": recorded,
        "yield_steps": model.bushing.yield_steps.tolist(),
        "events": len(run.events),
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "series": {"t_s": tt, "dE_geometric_J": et, "dE_force_J": ef},
        "timing": {"wall_s": wall, "steps": run.steps, "us_per_step": wall / run.steps * 1e6},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S3_{case.case_id}", dict(s)))


# --- V4 ---------------------------------------------------------------------------------------


def _x3_overrides(params):
    kn_lo, kn_hi = params.get("contact.crawler.kn_total_sensitivity_range_N_m")
    scale = float(kn_hi) / float(kn_lo)
    kn = float(params.get("contact.crawler.kn_per_sphere_N_m")) * scale
    gn = float(params.get("contact.crawler.gn_per_sphere_1_s")) * math.sqrt(scale)
    return {"contact.crawler.kn_per_sphere_N_m": kn, "contact.crawler.gn_per_sphere_1_s": gn}


def job_v4(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import DtWindow, run_commanded, run_windowed
    from outrigger_sim.params import LEG_ORDER, load_params
    from outrigger_sim.record import Recorder, load_snapshot, save_record
    from outrigger_sim.scenarios.crawler_settle import crawler_static_pose
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.scenarios.lift import equivalent_origin_from_trajectory, lift_plan
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import fit_damped_sine, modal_coordinates, rigid_displacement
    from outrigger_sim.verify.reference import (
        HYDRAULIC_MAX_HEAD_FORCE_N,
        L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
        L1_CONTACT_FORCE_N,
        L1_STATIC_ATTITUDE_DEG,
        LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N,
        LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
        LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3,
        LIFT_V4_LAYOUT_D,
        LIFT_V4_LAYOUT_D_KN_X3,
        LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D,
        LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3,
        TOTAL_WEIGHT_INCL_RODS_N,
        load_references,
    )
    from outrigger_sim.verify.s3 import v4_checks, v4_record_items

    s = case.settings
    dt = float(s["dt"])
    windowed = bool(s["windowed"])
    x3 = bool(s.get("x3", False))
    record = bool(s.get("record", False))
    base = load_params(level=LEVEL)
    params = load_params(level=LEVEL, overrides=_x3_overrides(base)) if x3 else base
    refs = load_references()
    touch_key = LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3 if x3 else LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D
    qs_key = (LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3 if x3
              else LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D)
    layout_key = LIFT_V4_LAYOUT_D_KN_X3 if x3 else LIFT_V4_LAYOUT_D
    touch_ref = [float(v) for v in refs.get(touch_key)]
    f1 = float(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=LEVEL)[0])
    plan = lift_plan(params, reference_touch_eq_s=touch_ref, first_rocking_Hz=f1)
    pose = crawler_static_pose(params)
    model = _crawler_model(params, pose, dt)
    if x3:
        run_commanded(model, X3_HOLD_S, lambda _t: None, sample_s=1.0)  # settle (analytic start)
        start = f"analytic exact crawler pose (kn x3) + {X3_HOLD_S} s hold"
    else:
        snap = load_snapshot(CRAWLER_SNAPSHOT, params_sha256=params.sha256, directory=STATES)
        model.restore(snap)
        start = f"snapshot {CRAWLER_SNAPSHOT}"
    t_run0 = float(model.system.GetChTime())
    model.actuator.set_soft_limits(hi_m=plan.e_op_m)
    dt_tr = float(params.get("simulation.dt_transition_s"))
    windows = [DtWindow(*plan.transition_window_s, dt_tr)] if windowed else []
    settings = {**dict(s), "start": start, "plan": plan.as_dict(),
                "soft_limits_hi_m": list(plan.e_op_m),
                "windows": [w.__dict__ for w in windows]}
    recorder = None
    if record:
        recorder = Recorder(_run_meta(params, model, f"S3_{case.case_id}", settings))
    sample, arrays = _collector(model, recorder)
    t0w = time.perf_counter()
    run = run_windowed(model, plan.end_s, plan.schedule(), windows=windows, base_dt_s=dt,
                       sample_s=SAMPLE_S, on_sample=sample)
    wall = time.perf_counter() - t0w
    a = arrays()
    t = a["t"] - t_run0
    v = params.actuator.max_speed_m_s
    t_eq = equivalent_origin_from_trajectory(t, a["s_ref"][:, 0], v, 1.0, 14.0)
    touch_eq = (run.first_positive_N_t_s - t_run0 - t_eq).tolist()
    # crawler fully off: last sample with a crawler force, then never again
    fz = a["Fcrawler"][:, 2]
    on = np.flatnonzero(fz > 0.0)
    t_off_eq = float(t[on[-1] + 1] - t_eq) if on.size and on[-1] + 1 < len(t) else math.nan
    gaps_on = int(np.sum(np.diff((fz > 0.0).astype(int)) == 1))
    # contact losses after touch (raw per-step transitions)
    losses = [0, 0, 0, 0]
    for _t, leg, state in run.raw_contact_transitions:
        if state == 0:
            losses[leg] += 1
    att = _attitude_deg(a["quat"])
    mw0, mw1 = plan.mean_window_s
    n_mean = _window_mean(t, a["N"], mw0, mw1)
    fcyl_mean = _window_mean(t, a["Fcyl"], mw0, mw1)
    att_mean = _window_mean(t, att, mw0, mw1)
    r0, r1 = plan.residual_window_s
    rmask = (t >= r0) & (t <= r1)
    resid = 0.5 * np.ptp(att[rmask], axis=0)
    att_ref = [float(x) for x in refs.get(L1_STATIC_ATTITUDE_DEG, level=LEVEL)]
    resid_dev = np.max(np.abs(att[rmask] - np.asarray(att_ref)), axis=0)
    # residual rocking envelope: modal projection after the last stop about the final mean pose
    modal = modal_reference(refs, LEVEL)
    after = t >= plan.last_stop_s + 1.0
    org_ref = _window_mean(t, a["origin"], mw0, mw1)
    q_mean = _window_mean(t, a["quat"], mw0, mw1)
    q_mean = q_mean / np.linalg.norm(q_mean)
    q6 = rigid_displacement(a["origin"][after], a["quat"][after], org_ref, q_mean,
                            modal.reference_point_body_m)
    eta = modal_coordinates(q6, modal.phi, modal.mass_matrix)
    zn, _ = modal.zeta_num_at(dt)
    envelope = {}
    env_detail = []
    for k in (0, 1):
        fit = fit_damped_sine(t[after], eta[:, k], float(modal.f_damped_Hz[k]))
        corr = fit.zeta - float(zn[k])
        env_detail.append({"mode": k + 1, "zeta_fit": fit.zeta, "zeta_num": float(zn[k]),
                           "zeta_corrected": corr, "zeta_ref": float(modal.zeta[k]),
                           "f_damped_Hz": fit.f_damped_Hz, "amplitude": fit.amplitude,
                           "residual_rms_rel": fit.residual_rms_rel})
        envelope[f"mode {k + 1}"] = (corr, float(modal.zeta[k]))
    w_total = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    peak_ref = [float(refs.get(LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N, leg=lg)) for lg in LEG_ORDER]
    events = [[e.t_s - t_run0, e.leg, e.kind] for e in run.events]
    checks = v4_checks(
        case.case_id,
        touch_eq_s=touch_eq,
        touch_ref_s=touch_ref,
        key_touch=touch_key.notation(),
        max_cylinder_force_N=run.max_motor_force_N,
        force_limit_N=float(refs.get(HYDRAULIC_MAX_HEAD_FORCE_N)),
        key_force_limit=HYDRAULIC_MAX_HEAD_FORCE_N.notation(),
        contact_force_mean_N=n_mean,
        contact_force_ref_N=[float(x) for x in refs.get(L1_CONTACT_FORCE_N, level=LEVEL)],
        key_contact=L1_CONTACT_FORCE_N.resolve(level=LEVEL).notation(),
        total_weight_N=w_total,
        attitude_mean_deg=att_mean,
        attitude_ref_deg=att_ref,
        key_attitude=L1_STATIC_ATTITUDE_DEG.resolve(level=LEVEL).notation(),
        residual_amplitude_deg=resid,
        envelope_zeta=envelope,
        motor_violation_max_m=run.max_motor_violation_m,
        events=events,
        any_nan=bool(not np.all(np.isfinite(a["N"])) or not np.all(np.isfinite(a["quat"]))),
    )
    layout = refs.get(layout_key)
    dyn = layout["dynamic_events_s"]
    end_probe = model.probe()
    bf = np.asarray(end_probe.bushing_force_world_N, dtype=float)
    record_rel = None
    if recorder is not None:
        for e in run.events:
            recorder.add_bushing_event(e.t_s, e.leg, e.kind)
        record_rel = _rel(save_record(recorder.finish(), case_dir / "record", overwrite=True))
    np.savez_compressed(case_dir / "series.npz", t=t, N=a["N"], Fcyl=a["Fcyl"], s_ref=a["s_ref"],
                        s_motor=a["s_motor"], att=att, Fcrawler=a["Fcrawler"],
                        bush_t=a["bush_t"], u_cmd=a["u_cmd"])
    # compact series for the figure: lift transition region + whole run (thinned)
    tr = (t >= 14.8) & (t <= 18.4)
    tt, nn, ff = _thin(1500, t[tr], a["N"][tr], a["Fcyl"][tr])
    ta, aa = _thin(1500, t, att)
    summary = {
        "case": case.case_id,
        "dt_s": dt,
        "windowed": windowed,
        "dt_segments": run.dt_segments,
        "x3": x3,
        "start": start,
        "plan": plan.as_dict(),
        "equivalent_origin_s": {"measured": t_eq, "nominal_ramp_half": plan.equivalent_origin_s,
                                "measured_minus_nominal": t_eq - plan.equivalent_origin_s,
                                "expected_discrete_offset_dt_half": dt / 2.0},
        "touch_eq_s": touch_eq,
        "touch_ref_dynamic_s": touch_ref,
        "touch_minus_ref_s": (np.asarray(touch_eq) - np.asarray(touch_ref)).tolist(),
        "touch_ref_quasi_static_s": [float(x) for x in refs.get(qs_key)],
        "crawler_off_eq_s": t_off_eq,
        "crawler_off_ref_dynamic_s": float(dyn["crawler_fully_off_s"]),
        "crawler_recontacts_sampled": max(gaps_on - 0, 0),
        "crawler_min_gap_end_mm": _crawler_min_gap_m(model) * 1e3,
        "crawler_min_gap_ref_mm": float(layout["end_state (after the last stop)"][
            "crawler_min_clearance_mm"]),
        "pad_contact_losses_raw": losses,
        "peak_pad_force_N": run.max_pad_normal_N.tolist(),
        "peak_pad_force_t_eq_s": (run.max_pad_normal_t_s - t_run0 - t_eq).tolist(),
        "peak_cylinder_force_N": run.max_motor_force_N.tolist(),
        "peak_cylinder_force_t_eq_s": (run.max_motor_force_t_s - t_run0 - t_eq).tolist(),
        "peak_record": v4_record_items(peak_pad_force_N=run.max_pad_normal_N, peak_ref_N=peak_ref),
        "final": {
            "mean_window_s": [mw0, mw1],
            "contact_force_N": n_mean.tolist(),
            "cylinder_force_N": fcyl_mean.tolist(),
            "attitude_deg": att_mean.tolist(),
            "s_motor_m": a["s_motor"][-1].tolist(),
            "residual_window_s": [r0, r1],
            "residual_half_p2p_deg": resid.tolist(),
            "residual_max_dev_from_V3_ref_deg": resid_dev.tolist(),
            "envelope": env_detail,
        },
        "recorded_only": {
            "slip_total_mm": (model.bushing.slip_total_m * 1e3).tolist(),
            "yield_steps": model.bushing.yield_steps.tolist(),
            "bushing_tangential_preload_end_N": np.where(np.isnan(bf[:, 0]), 0.0,
                                                         np.hypot(bf[:, 0], bf[:, 1])).tolist(),
            "note": "crawler has no tangential model (R8); pad slip and bushing pre-load are "
            "recorded only (dynamics_model.md 5.6 ruling 4)",
        },
        "events": events,
        "max_axial_violation_m": run.max_motor_violation_m,
        "checks": summary_table(checks),
        "all_passed": all_passed(checks),
        "series": {"t_s": tt, "pad_normal_N": nn, "cylinder_force_N": ff, "t_att_s": ta,
                   "attitude_deg": aa},
        "record": record_rel,
        "timing": {"wall_s": wall, "steps": run.steps, "us_per_step": wall / run.steps * 1e6},
    }
    meta = _run_meta(params, model, f"S3_{case.case_id}", settings,
                     extra={"dt_windows": [w.__dict__ for w in windows]})
    return CaseResult(summary=_plain(summary), run_meta=meta)


# --- V5 / V9 step / V9 free / V6 --------------------------------------------------------------


def job_v5(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import load_params
    from outrigger_sim.record import Recorder, save_record
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.reference import (
        L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
        L1_DF_PER_MM_FL_N,
        L1_DROLL_DPITCH_PER_MM_FL_DEG,
        load_references,
    )
    from outrigger_sim.verify.s3 import v5_checks

    params = load_params(level=LEVEL)
    refs = load_references()
    dt = float(case.settings["dt"])
    model, t0 = _pads_model_from_s1(params, refs, dt)
    T1 = 1.0 / float(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=LEVEL)[0])
    s0 = model.actuator.s_ref_m.copy()
    rng = model.actuator.stroke_range_m
    settings = {**dict(case.settings), "start": f"snapshot {S1_SNAPSHOT}",
                "speed_m_s": V5_SPEED_M_S,
                "steps_mm": [1.0, 5.0], "hold_before_s": 3.0, "settle_s": 10.0}
    recorder = Recorder(_run_meta(params, model, "S3_V5", settings))
    sample, arrays = _collector(model, recorder)
    t_w = time.perf_counter()
    run_commanded(model, 3.0, lambda _t: None, sample_s=COARSE_SAMPLE_S, on_sample=sample)
    marks = {"base": float(model.system.GetChTime())}
    for delta_mm, move_s in ((1.0, 1.0e-3 / V5_SPEED_M_S), (5.0, 4.0e-3 / V5_SPEED_M_S)):
        hi = rng[:, 1].copy()
        hi[0] = s0[0] + delta_mm * 1e-3
        model.actuator.set_soft_limits(hi_m=hi)
        model.set_command([V5_SPEED_M_S, 0.0, 0.0, 0.0])
        run_commanded(model, move_s + 0.2 + 10.0, lambda _t: None, sample_s=COARSE_SAMPLE_S,
                      on_sample=sample)
        model.set_command([0.0, 0.0, 0.0, 0.0])
        marks[f"{delta_mm:g}"] = float(model.system.GetChTime())
    wall = time.perf_counter() - t_w
    a = arrays()
    att = _attitude_deg(a["quat"])
    base_n = _window_mean(a["t"], a["N"], marks["base"] - 3 * T1, marks["base"])
    base_a = _window_mean(a["t"], att, marks["base"] - 3 * T1, marks["base"])
    out = {}
    checks = []
    for key in ("1", "5"):
        tend = marks[key]
        n_m = _window_mean(a["t"], a["N"], tend - 3 * T1, tend)
        a_m = _window_mean(a["t"], att, tend - 3 * T1, tend)
        travel = float(a["s_motor"][np.argmin(np.abs(a["t"] - tend)), 0] - s0[0]) * 1e3
        d_f = n_m - base_n
        d_a = a_m - base_a
        out[f"+{key} mm"] = {"travel_mm": travel, "dF_N": d_f.tolist(),
                             "dattitude_deg": d_a.tolist(),
                             "window_end_s": tend - t0}
        checks += v5_checks(
            float(key),
            dF_N=d_f,
            dF_per_mm_ref_N=refs.get(L1_DF_PER_MM_FL_N, level=LEVEL),
            key_dF=L1_DF_PER_MM_FL_N.resolve(level=LEVEL).notation(),
            dattitude_deg=d_a,
            dattitude_per_mm_ref_deg=refs.get(L1_DROLL_DPITCH_PER_MM_FL_DEG, level=LEVEL),
            key_att=L1_DROLL_DPITCH_PER_MM_FL_DEG.resolve(level=LEVEL).notation(),
        )
    rec = save_record(recorder.finish(), case_dir / "record", overwrite=True)
    summary = {
        "case": case.case_id, "dt_s": dt, "baseline": {"contact_force_N": base_n.tolist(),
                                                       "attitude_deg": base_a.tolist()},
        "results": out,
        "reference": {"dF_per_mm_FL_N": list(refs.get(L1_DF_PER_MM_FL_N, level=LEVEL)),
                      "droll_dpitch_per_mm_FL_deg": list(
                          refs.get(L1_DROLL_DPITCH_PER_MM_FL_DEG, level=LEVEL))},
        "yield_steps": model.bushing.yield_steps.tolist(),
        "checks": summary_table(checks), "all_passed": all_passed(checks),
        "record": _rel(rec), "timing": {"wall_s": wall},
    }
    return CaseResult(summary=_plain(summary), run_meta=_run_meta(params, model, "S3_V5", settings))


def job_v6(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import DtWindow, run_windowed
    from outrigger_sim.params import LEG_ORDER, load_params
    from outrigger_sim.record import Recorder, save_record
    from outrigger_sim.scenarios.lift import LegStep, crossing
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.reference import (
        L1_F_MIN_THRESHOLD_SINGLE_LEG,
        L1_LIFTOFF_THRESHOLD_SINGLE_LEG,
        load_references,
    )
    from outrigger_sim.verify.s3 import v6_checks

    params = load_params(level=LEVEL)
    refs = load_references()
    s = case.settings
    dt = float(s["dt"])
    direction = s["direction"]
    speed = float(s["speed"])
    ref_fmin = refs.get(L1_F_MIN_THRESHOLD_SINGLE_LEG, level=LEVEL)[direction]
    ref_lift = refs.get(L1_LIFTOFF_THRESHOLD_SINGLE_LEG, level=LEVEL)[direction]
    lift_mm = float(ref_lift["delta_mm"])
    sign = 1.0 if direction.endswith("+") else -1.0
    step = LegStep(
        name=case.case_id, leg=0, speed_m_s=speed,
        delta_m=sign * (lift_mm * 1e-3 + V6_BEYOND_LIFTOFF_M),
        hold_before_s=0.5, hold_after_s=0.5,
        transition_from_delta_m=lift_mm * 1e-3 - V6_WINDOW_BEFORE_LIFTOFF_M,
    )
    model, t0 = _pads_model_from_s1(params, refs, dt)
    s0 = model.actuator.s_ref_m.copy()
    lo, hi = step.soft_limits(s0, model.actuator.stroke_range_m)
    model.actuator.set_soft_limits(lo_m=lo, hi_m=hi)
    ramp = params.actuator.command_ramp_s
    win = step.transition_window_s(ramp)
    dt_tr = float(params.get("simulation.dt_transition_s"))
    windows = [DtWindow(win[0], min(win[1], step.end_s(ramp)), dt_tr, SAMPLE_S)]
    settings = {**dict(s), "start": f"snapshot {S1_SNAPSHOT}", "step": step.as_dict(),
                "windows": [w.__dict__ for w in windows]}
    recorder = Recorder(_run_meta(params, model, f"S3_{case.case_id}", settings))
    sample, arrays = _collector(model, recorder)
    t_w = time.perf_counter()
    run = run_windowed(model, step.end_s(ramp), step.schedule(ramp),
                       windows=windows, base_dt_s=dt, sample_s=COARSE_SAMPLE_S, on_sample=sample)
    wall = time.perf_counter() - t_w
    a = arrays()
    travel_mm = np.abs(a["s_motor"][:, 0] - s0[0]) * 1e3
    f_min = float(params.get("control.F_min_cylinder_N"))
    fmin_hits = {}
    for leg in range(1, 4):
        tc = crossing(a["t"], a["Fcyl"][:, leg], f_min, falling=True)
        if tc is not None:
            fmin_hits[LEG_ORDER[leg]] = float(np.interp(tc, a["t"], travel_mm))
    f_leg = min(fmin_hits, key=fmin_hits.get) if fmin_hits else None
    offs = [(tt, leg) for (tt, leg, st) in run.raw_contact_transitions if st == 0]
    lift_leg = LEG_ORDER[offs[0][1]] if offs else None
    lift_mm_sim = float(np.interp(offs[0][0], a["t"], travel_mm)) if offs else None
    checks = v6_checks(
        direction,
        f_min_leg=f_leg, f_min_delta_mm=None if f_leg is None else fmin_hits[f_leg],
        liftoff_leg=lift_leg, liftoff_delta_mm=lift_mm_sim,
        ref_f_min=ref_fmin, ref_liftoff=ref_lift,
        key_f_min=L1_F_MIN_THRESHOLD_SINGLE_LEG.resolve(level=LEVEL).notation(),
        key_liftoff=L1_LIFTOFF_THRESHOLD_SINGLE_LEG.resolve(level=LEVEL).notation(),
    )
    for e in run.events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    rec = save_record(recorder.finish(), case_dir / "record", overwrite=True)
    tt, tv, fc, nn = _thin(2000, a["t"] - t0, travel_mm, a["Fcyl"], a["N"])
    summary = {
        "case": case.case_id, "direction": direction, "speed_m_s": speed, "dt_s": dt,
        "dt_segments": run.dt_segments, "F_min_N": f_min,
        "F_min_crossings_travel_mm": fmin_hits, "F_min_leg": f_leg,
        "liftoff_leg": lift_leg, "liftoff_travel_mm": lift_mm_sim,
        "reference": {"F_min": dict(ref_fmin), "liftoff": dict(ref_lift)},
        "events": [[e.t_s - t0, LEG_ORDER[e.leg], e.kind] for e in run.events],
        "yield_steps": model.bushing.yield_steps.tolist(),
        "slip_total_mm": (model.bushing.slip_total_m * 1e3).tolist(),
        "checks": summary_table(checks), "all_passed": all_passed(checks),
        "series": {"t_s": tt, "travel_mm": tv, "cylinder_force_N": fc, "pad_normal_N": nn},
        "record": _rel(rec), "timing": {"wall_s": wall, "steps": run.steps,
                                        "us_per_step": wall / run.steps * 1e6},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S3_{case.case_id}", settings))


def job_v9_step(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.reference import L1_BALL_CENTRE_REV13_F_DAMPED_HZ, load_references

    params = load_params(level=LEVEL)
    refs = load_references()
    dt = float(case.settings["dt"])
    v = params.actuator.max_speed_m_s
    model, t0 = _pads_model_from_s1(params, refs, dt)
    T1 = 1.0 / float(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ, level=LEVEL)[0])
    s0 = model.actuator.s_ref_m.copy()
    hi = model.actuator.stroke_range_m[:, 1].copy()
    hi[0] = s0[0] + 1.0e-3
    model.actuator.set_soft_limits(hi_m=hi)
    collect, arrays = _collector(model)
    z_pad = []

    def sample(probe):
        collect(probe)
        z_pad.append(np.asarray(probe.pad_sphere_centre_world_m, dtype=float)[:, 2].copy())

    t_w = time.perf_counter()
    run_commanded(model, V9_STEP_HOLD_S, lambda _t: None, sample_s=SAMPLE_S, on_sample=sample)
    model.set_command([v, 0.0, 0.0, 0.0])
    run = run_commanded(model, V9_STEP_END_S - V9_STEP_HOLD_S, lambda _t: None,
                        sample_s=SAMPLE_S, on_sample=sample)
    wall = time.perf_counter() - t_w
    a = arrays()
    t = a["t"] - t0
    att = _attitude_deg(a["quat"])
    base = _window_mean(t, a["N"], 0.0, V9_STEP_HOLD_S)
    dN = a["N"] - base
    trans = (t >= V9_STEP_HOLD_S) & (t <= V9_STEP_HOLD_S + 2.5)
    k_rl = int(np.argmin(dN[trans, 2]))
    peak_rl = float(dN[trans, 2][k_rl])
    # noise-free companion: elastic load k_n delta with delta from the sphere-centre height in
    # double precision (the Chrono contact force carries Bullet's float32 distance noise)
    from outrigger_sim.chrono.contact import pad_material_values

    kn = np.array([float(np.float32(pad_material_values(params, i).kn_N_m)) for i in range(4)])
    radii = np.asarray(model.sphere_radii_m, dtype=float)
    delta = radii - (np.asarray(z_pad) - model.floor_z_m)
    f_el = kn * delta
    d_el = f_el - _window_mean(t, f_el, 0.0, V9_STEP_HOLD_S)
    k_el = int(np.argmin(d_el[trans, 2]))
    hold = t <= V9_STEP_HOLD_S
    noise_rl = float(np.std(a["N"][hold, 2] - f_el[hold, 2]))
    final_n = _window_mean(t, a["N"], V9_STEP_END_S - 3 * T1, V9_STEP_END_S)
    final_a = _window_mean(t, att, V9_STEP_END_S - 3 * T1, V9_STEP_END_S)
    np.savez_compressed(case_dir / "series.npz", t=t, N=a["N"], att=att, s_motor=a["s_motor"])
    summary = {
        "case": case.case_id, "dt_s": dt,
        "transient_min_dF_RL_N": peak_rl,
        "transient_min_dF_RL_t_s": float(t[trans][k_rl]),
        "transient_min_dF_elastic_RL_N": float(d_el[trans, 2][k_el]),
        "transient_min_dF_elastic_RL_t_s": float(t[trans][k_el]),
        "contact_force_noise_RL_std_N": noise_rl,
        "note": "elastic = k_n(float32) x delta(sphere-centre height, double); contact force "
        "minus elastic load in the hold window = Bullet distance noise (+ damping term)",
        "transient_extremes_dF_N": {"min": dN[trans].min(axis=0).tolist(),
                                    "max": dN[trans].max(axis=0).tolist()},
        "final_contact_force_N": final_n.tolist(),
        "final_attitude_deg": final_a.tolist(),
        "final_travel_mm": float(a["s_motor"][-1, 0] - s0[0]) * 1e3,
        "events": len(run.events), "yield_steps": model.bushing.yield_steps.tolist(),
        "timing": {"wall_s": wall},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S3_{case.case_id}", dict(case.settings)))


def job_v9_free(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.impulse import EXCITATIONS, angular_velocity_world, modal_reference
    from outrigger_sim.verify.metrics import fit_damped_sine, modal_coordinates, rigid_displacement
    from outrigger_sim.verify.reference import load_references

    params = load_params(level=LEVEL)
    refs = load_references()
    dt = float(case.settings["dt"])
    modal = modal_reference(refs, LEVEL)
    model, t0 = _pads_model_from_s1(params, refs, dt, actuator=False)
    p0 = model.probe()
    rot0 = quat_to_matrix(p0.body_quat_wxyz)
    point = p0.body_pos_m + rot0 @ modal.reference_point_body_m
    exc = EXCITATIONS["roll"]
    set_rigid_velocity(model, (0.0, 0.0, 0.0), angular_velocity_world(exc, modal), point)
    tr = {"t": [], "o": [], "q": []}

    def on_sample(p):
        tr["t"].append(p.t_s)
        tr["o"].append(p.body_pos_m)
        tr["q"].append(p.body_quat_wxyz)

    t_w = time.perf_counter()
    run = run_free_vibration(model, V9_FREE_S, sample_s=SAMPLE_S, on_sample=on_sample)
    wall = time.perf_counter() - t_w
    t = np.asarray(tr["t"]) - t0
    q = rigid_displacement(np.asarray(tr["o"]), np.asarray(tr["q"]), p0.body_pos_m,
                           p0.body_quat_wxyz, modal.reference_point_body_m)
    eta = modal_coordinates(q, modal.phi, modal.mass_matrix)
    fit = fit_damped_sine(t, eta[:, 0], float(modal.f_damped_Hz[0]))
    # fit time origin = first sample
    tau = V9_FREE_AT_S - t[0]
    amp5 = fit.amplitude * math.exp(-fit.sigma_1_s * tau)
    phase5 = fit.phase_rad + 2.0 * math.pi * fit.f_damped_Hz * tau
    k5 = int(np.argmin(np.abs(t - V9_FREE_AT_S)))
    summary = {
        "case": case.case_id, "dt_s": dt, "excitation": exc.__dict__,
        "fit": {"f_damped_Hz": fit.f_damped_Hz, "zeta": fit.zeta, "amplitude": fit.amplitude,
                "phase_rad": fit.phase_rad, "residual_rms_rel": fit.residual_rms_rel},
        "amplitude_at_5s": amp5, "phase_at_5s_rad_unwrapped": phase5,
        "eta1_sample_at_5s": float(eta[k5, 0]), "t_sample_5s": float(t[k5]),
        "events": len(run.events), "timing": {"wall_s": wall},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S3_{case.case_id}", dict(case.settings)))


V4TOUCH_END_S = 15.40
"""Touch-time diagnosis runs end here (command time; every reference touch + ramp/2 is
before 15.25 s)."""


def job_v4touch(case, case_dir):
    """V9 V4 touch-time diagnosis: per step, the R15 touch (first step with N > 0) and the
    geometric touch (pad sphere bottom crossing the floor, linear interpolation between step
    ends, double precision), from the measured equivalent origin."""
    import numpy as np
    import pychrono as ch

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.crawler_settle import crawler_static_pose
    from outrigger_sim.scenarios.lift import lift_plan
    from outrigger_sim.verify.reference import (
        L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
        LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
        load_references,
    )

    params = load_params(level=LEVEL)
    refs = load_references()
    dt = float(case.settings["dt"])
    plan = lift_plan(params,
                     reference_touch_eq_s=refs.get(LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D),
                     first_rocking_Hz=float(refs.get(L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
                                                     level=LEVEL)[0]))
    model = _crawler_model(params, crawler_static_pose(params), dt)
    model.restore(load_snapshot(CRAWLER_SNAPSHOT, params_sha256=params.sha256, directory=STATES))
    model.actuator.set_soft_limits(hi_m=plan.e_op_m)
    v = params.actuator.max_speed_m_s
    model.set_command([v] * 4)
    t0 = float(model.system.GetChTime())
    centres = [ch.ChVector3d(*map(float, c)) for c in model.sphere_centres_local_m]
    radii = np.asarray(model.sphere_radii_m)
    floor = model.floor_z_m

    def gaps():
        return np.array([leg.TransformPointLocalToParent(c).z for leg, c in
                         zip(model.legs, centres, strict=True)]) - radii - floor

    g_prev = gaps()
    t_prev = 0.0
    geo = np.full(4, np.nan)
    r15 = np.full(4, np.nan)
    t_eq = None
    n = round(V4TOUCH_END_S / dt)
    t_w = time.perf_counter()
    for _ in range(n):
        model.step()
        t = float(model.system.GetChTime()) - t0
        g = gaps()
        crossed = np.isnan(geo) & (g <= 0.0) & (g_prev > 0.0)
        for i in np.flatnonzero(crossed):
            geo[i] = t_prev + (t - t_prev) * g_prev[i] / (g_prev[i] - g[i])
        nr = model.bushing.normal_force_raw_N
        new = np.isnan(r15) & (nr > 0.0)
        r15[new] = t
        if t_eq is None and t >= 1.0:
            t_eq = t - float(model.actuator.acting_s_ref_m[0]) / v
        g_prev, t_prev = g, t
    wall = time.perf_counter() - t_w
    summary = {
        "case": case.case_id, "dt_s": dt, "equivalent_origin_s": t_eq,
        "touch_geometric_eq_s": (geo - t_eq).tolist(),
        "touch_r15_eq_s": (r15 - t_eq).tolist(),
        "r15_minus_geometric_s": (r15 - geo).tolist(),
        "r15_minus_geometric_in_dt": ((r15 - geo) / dt).tolist(),
        "timing": {"wall_s": wall, "steps": n},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S3_{case.case_id}", dict(case.settings)))


def job(case, case_dir):
    """Batch job (module level for spawn): dispatch on ``case.settings['kind']``."""
    kind = case.settings["kind"]
    fn = {"v8a": job_v8a, "v4": job_v4, "v5": job_v5, "v6": job_v6, "v9_step": job_v9_step,
          "v9_free": job_v9_free, "replay": job_replay, "v4touch": job_v4touch}[kind]
    out = fn(case, Path(case_dir))
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(dict(out.summary)), indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def _yaml_l1_dt() -> float:
    """General-run time step of the YAML (``simulation.L1.dt_s``)."""
    from outrigger_sim.params import load_params

    return float(load_params(level=LEVEL).simulation.L1.dt_s)


def case_settings(case_id: str) -> dict:
    def dt_of(text):
        return float(text)

    if case_id.startswith("v8a_"):
        where, dtx = case_id.removeprefix("v8a_").split("_dt")
        return {"kind": "v8a", "where": where, "dt": dt_of(dtx)}
    if case_id == "v4_D_wdefault":
        return {"kind": "v4", "dt": _yaml_l1_dt(), "windowed": True, "x3": False,
                "record": True, "dt_source": "YAML simulation.L1.dt_s"}
    if case_id.startswith("v4_"):
        body = case_id.removeprefix("v4_")
        layout, mode = body.split("_")
        windowed = mode.startswith("w")
        return {"kind": "v4", "dt": dt_of(mode[1:]), "windowed": windowed, "x3": layout == "Dx3",
                "record": windowed}
    if case_id == "v5":
        return {"kind": "v5", "dt": 1.0e-4}
    if case_id == "v5_default":
        return {"kind": "v5", "dt": _yaml_l1_dt(), "dt_source": "YAML simulation.L1.dt_s"}
    if case_id.startswith("v6_"):
        fast = case_id.endswith("_fast")
        direction = "FL+" if "FLp" in case_id else "FL-"
        return {"kind": "v6", "direction": direction, "dt": 1.0e-4,
                "speed": V6_FAST_SPEED_M_S if fast else V6_SPEED_M_S}
    if case_id.startswith("v9_step_dt"):
        return {"kind": "v9_step", "dt": dt_of(case_id.removeprefix("v9_step_dt"))}
    if case_id.startswith("v9_free_dt"):
        return {"kind": "v9_free", "dt": dt_of(case_id.removeprefix("v9_free_dt"))}
    if case_id.startswith("v4touch_dt"):
        return {"kind": "v4touch", "dt": dt_of(case_id.removeprefix("v4touch_dt"))}
    if case_id == "ctrl1_replay":
        # The stored replay result was made from the first-batch Record; pointing it at the
        # judged run (v4_D_wdefault, also a Record) needs a re-run of ctrl1_replay.
        return {"kind": "replay", "source": "v4_D_w1e-04", "period_s": 0.02}
    raise SystemExit(f"unknown case {case_id!r}")


# --- control item 1: open-loop replay --------------------------------------------------------


def job_replay(case, case_dir):
    """Control item 1 (plan 3.5, S3): replay the u_cmd stream of the judged V4 Record at the
    20 ms control period (zero-order hold) on the same start state and scenario set-up; the
    trajectory must be reproduced, and the Record must be self-consistent."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import DtWindow, run_windowed
    from outrigger_sim.params import load_params
    from outrigger_sim.record import Recorder, load_record, save_record
    from outrigger_sim.scenarios.crawler_settle import crawler_static_pose
    from outrigger_sim.signals import RECORD_FIELDS

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    src_dir = ROOT / index[case.settings["source"]]
    params = load_params(level=LEVEL)
    rec = load_record(src_dir / "record", params_sha256=params.sha256)
    meta = rec.run_meta
    plan = meta["scenario"]["settings"]["plan"]
    windows = [DtWindow(**w) for w in meta["scenario"]["settings"]["windows"]]
    dt = float(meta["scenario"]["settings"]["dt"])
    period = float(case.settings["period_s"])
    t_rec = np.asarray(rec.arrays["t"])
    u_rec = np.asarray(rec.arrays["u_cmd"])
    t_rec0 = t_rec[0] - SAMPLE_S  # first sample is one sample after the start
    # command held over [k P, (k+1) P): the value recorded at the first sample after k P
    n_per = int(round(plan["end_s"] / period))
    grid = np.arange(n_per) * period
    idx = np.searchsorted(t_rec - t_rec0, grid + 0.5 * SAMPLE_S)
    idx = np.clip(idx, 0, len(t_rec) - 1)
    cmd_grid = u_rec[idx]
    # u_cmd recorded at a sample is the command held during that step; a command set at t_n
    # (start of step n+1) is recorded from the sample after it: the grid value at k P is the
    # command set at k P.
    origin = {"t": None}

    def player(t_now):
        if origin["t"] is None:
            origin["t"] = t_now
        k = int(math.floor((t_now - origin["t"]) / period + 1e-9))
        if k >= len(cmd_grid):
            return None
        if abs((t_now - origin["t"]) - k * period) < 0.5 * dt:
            return cmd_grid[k]
        return None

    pose = crawler_static_pose(params)
    model = _crawler_model(params, pose, dt)
    from outrigger_sim.record import load_snapshot

    model.restore(load_snapshot(CRAWLER_SNAPSHOT, params_sha256=params.sha256, directory=STATES))
    model.actuator.set_soft_limits(hi_m=meta["scenario"]["settings"]["soft_limits_hi_m"])
    settings = {**dict(case.settings), "source_record": _rel(src_dir / "record"),
                "windows": [w.__dict__ for w in windows]}
    recorder = Recorder(_run_meta(params, model, "S3_control1_replay", settings))
    sample, arrays = _collector(model, recorder)
    t_w = time.perf_counter()
    run = run_windowed(model, plan["end_s"], player, windows=windows, base_dt_s=dt,
                       sample_s=SAMPLE_S, on_sample=sample)
    wall = time.perf_counter() - t_w
    for e in run.events:
        recorder.add_bushing_event(e.t_s, e.leg, e.kind)
    new = recorder.finish()
    rec_path = save_record(new, case_dir / "record", overwrite=True)
    a = new.arrays
    n = min(len(a["t"]), len(t_rec))
    diffs = {
        "t_s": float(np.max(np.abs(np.asarray(a["t"][:n]) - t_rec[:n]))),
        "body_pos_m": float(np.max(np.abs(np.asarray(a["body_pos"][:n]) -
                                          np.asarray(rec.arrays["body_pos"][:n])))),
        "F_contact_n_N": float(np.max(np.abs(np.asarray(a["F_contact_n"][:n]) -
                                             np.asarray(rec.arrays["F_contact_n"][:n])))),
        "s_motor_m": float(np.max(np.abs(np.asarray(a["s_motor"][:n]) -
                                         np.asarray(rec.arrays["s_motor"][:n])))),
        "u_cmd": float(np.max(np.abs(np.asarray(a["u_cmd"][:n]) - u_rec[:n]))),
    }
    events_same = (np.array_equal(new.bushing_events["leg"], rec.bushing_events["leg"])
                   and np.array_equal(new.bushing_events["kind"], rec.bushing_events["kind"]))
    t_ev_diff = (float(np.max(np.abs(new.bushing_events["t"] - rec.bushing_events["t"])))
                 if events_same and len(rec.bushing_events["t"]) else math.nan)
    # Record self-consistency
    names = {f.name for f in RECORD_FIELDS if not f.is_optional}
    tt = np.asarray(a["t"])
    s_ref = np.asarray(a["s_ref"])
    s_mot = np.asarray(a["s_motor"])
    record_checks = {
        "required_fields_present": sorted(names - set(a)) == [],
        "same_sample_count": len(a["t"]) == len(t_rec),
        "t_strictly_increasing": bool(np.all(np.diff(tt) > 0.0)),
        "s_motor_equals_s_ref_max_m": float(np.max(np.abs(s_mot - s_ref))),
        "u_applied_within_v_max": bool(np.all(np.abs(np.asarray(a["u_applied"])) <=
                                              params.actuator.max_speed_m_s * (1 + 1e-9))),
        "run_meta_input_lag_steps": new.run_meta.get("input_lag_steps"),
        "events_same_sequence": bool(events_same),
        "event_time_max_diff_s": t_ev_diff,
        "command_changes_on_grid": int(np.sum(np.any(np.diff(cmd_grid, axis=0) != 0.0, axis=1))),
    }
    passed = (diffs["body_pos_m"] <= 1e-12 and diffs["s_motor_m"] <= 1e-12 and events_same
              and record_checks["required_fields_present"] and record_checks["same_sample_count"]
              and record_checks["t_strictly_increasing"]
              and record_checks["s_motor_equals_s_ref_max_m"] <= 1e-9)
    summary = {"case": case.case_id, "source": case.settings["source"], "period_s": period,
               "max_abs_diff_vs_source": diffs, "record_checks": record_checks,
               "all_passed": bool(passed), "record": _rel(rec_path),
               "note": "runner.py (S6, python-expert) does not exist yet: the zero-order-hold "
               "player above stands in for it; Controller/Measurements are not exercised",
               "timing": {"wall_s": wall, "steps": run.steps}}
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, "S3_control1_replay", settings))


# --- batch driver ------------------------------------------------------------------------------


def _update_index(report, batch_dir):
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        if o.status == "ok":
            index[o.case_id] = _rel(Path(batch_dir) / o.case_id)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")


def reindex():
    """Rebuild ``index.json`` from every ``batch_*`` directory (latest result per case wins);
    used when a batch parent was stopped before writing its index entry."""
    index = {}
    for batch_dir in sorted(RESULTS.glob("batch_*")):
        for case_dir in sorted(p for p in batch_dir.iterdir() if p.is_dir()):
            meta = case_dir / "case.json"
            if not (case_dir / "result.json").exists() or not meta.exists():
                continue
            doc = json.loads(meta.read_text(encoding="utf-8"))
            if (doc.get("runner") or {}).get("status") == "ok":
                index[case_dir.name] = _rel(case_dir)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"index: {len(index)} cases")


def run_batch(ids, jobs):
    from outrigger_sim.batch import Case, run_cases

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    # longest first so the slots stay busy
    order = sorted(ids, key=lambda c: (0 if c in ("v4_D_u1e-05",) else 1 if "1e-05" in c else
                                       2 if c.startswith("v6") and "fast" not in c else 3, c))
    cases = [Case(c, case_settings(c)) for c in order]
    t0 = time.perf_counter()
    report = run_cases(cases, job, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CASE_TIMEOUT_S)
    for o in report.outcomes:
        msg = f"{o.case_id}: {o.status} {o.wall_s:.1f}s"
        if o.status != "ok":
            msg += f"\n{(o.error or '')[-2500:]}"
        print(msg, flush=True)
    print(f"batch wall {time.perf_counter() - t0:.1f} s -> {_rel(batch_dir)}", flush=True)
    _update_index(report, batch_dir)
    return report


def _load_results():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    out = {}
    for cid, rel in index.items():
        p = ROOT / rel / "result.json"
        if p.exists():
            out[cid] = json.loads(p.read_text(encoding="utf-8"))
            out[cid]["_dir"] = rel
    return out


def _case_params_sha(rel_dir):
    p = ROOT / rel_dir / "case.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return ((doc.get("run_meta") or {}).get("params_sha256") or "")[:16] or None


def summarize():
    import numpy as np

    from outrigger_sim.params import load_params
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.reference import TOTAL_WEIGHT_INCL_RODS_N, load_references
    from outrigger_sim.verify.s3 import (
        V4_JUDGED_RUN,
        V4_PREVIOUS_JUDGED_RUN,
        order_ratio,
        v4_judged_run_comparison,
        v8a_crawler_checks,
        v9_checks,
        v9_v4_checks,
        v9_v4_r15_touch_record,
    )

    res = _load_results()
    refs = load_references()
    params = load_params(level=LEVEL)
    w = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    v9 = []
    v9_detail = {}
    # V9 smooth 1: step response
    steps = {r["dt_s"]: r for cid, r in res.items() if cid.startswith("v9_step")}
    if len(steps) == 4:
        peak = {dt: r["transient_min_dF_RL_N"] for dt, r in steps.items()}
        stat = {dt: r["final_contact_force_N"] for dt, r in steps.items()}
        att = {dt: r["final_attitude_deg"] for dt, r in steps.items()}
        order_raw = order_ratio({dt: peak[dt] for dt in V9_DTS})
        el = {dt: r.get("transient_min_dF_elastic_RL_N") for dt, r in steps.items()}
        order_el = (order_ratio({dt: el[dt] for dt in V9_DTS})
                    if all(el[dt] is not None for dt in V9_DTS) else None)
        # judged: the elastic load (Bullet float32 distance noise removed); the raw contact
        # force ratio is recorded (its smallest difference is near the noise level)
        v9 += v9_checks("V9-1 FL +1 mm step (v_max)", dts_s=[*V9_DTS, V9_REF_DT],
                        static_force_N=stat, total_weight_N=w, final_attitude_deg=att,
                        transient_peak_N=peak, ref_dt_s=V9_REF_DT,
                        order=None if order_el is None else
                        {"transient min dF_RL, elastic k_n delta": order_el})
        v9_detail["step"] = {
            "peak_dF_RL_N": peak, "order_raw_contact_force_recorded": order_raw,
            "peak_minus_ref_N": {dt: peak[dt] - peak[V9_REF_DT] for dt in peak},
            "peak_elastic_dF_RL_N": el, "order_elastic_judged": order_el,
            "noise_RL_std_N": {dt: r.get("contact_force_noise_RL_std_N")
                               for dt, r in steps.items()},
        }
    frees = {r["dt_s"]: r for cid, r in res.items() if cid.startswith("v9_free")}
    if len(frees) == 4:
        amp = {dt: r["amplitude_at_5s"] for dt, r in frees.items()}
        ph = {dt: r["phase_at_5s_rad_unwrapped"] for dt, r in frees.items()}
        o_amp = order_ratio({dt: amp[dt] for dt in V9_DTS})
        o_ph = order_ratio({dt: ph[dt] for dt in V9_DTS})
        v9 += v9_checks("V9-2 mode-1 free vibration t = 5 s", dts_s=[*V9_DTS, V9_REF_DT],
                        static_force_N=None, total_weight_N=w, final_attitude_deg=None,
                        transient_peak_N=None, ref_dt_s=V9_REF_DT,
                        order={"mode-1 amplitude at 5 s": o_amp})
        rel_amp = {dt: amp[dt] / amp[V9_REF_DT] - 1.0 for dt in amp}
        v9_detail["free"] = {"amplitude_at_5s": amp, "phase_at_5s_rad": ph,
                             "amplitude_rel_to_ref": rel_amp, "order_amplitude": o_amp,
                             "order_phase_recorded": o_ph,
                             "phase_minus_ref_rad": {dt: ph[dt] - ph[V9_REF_DT] for dt in ph}}
    touch_geo = {r["dt_s"]: r["touch_geometric_eq_s"] for cid, r in res.items()
                 if cid.startswith("v4touch_dt")}
    geo_diff_max = None
    if V9_REF_DT in touch_geo and len(touch_geo) > 1:
        from outrigger_sim.verify.s3 import touch_geometric_checks

        v9 += touch_geometric_checks(touch_geo, V9_REF_DT)
        gref = np.asarray(touch_geo[V9_REF_DT], dtype=float)
        geo_diff_max = max(float(np.max(np.abs(np.asarray(g, dtype=float) - gref)))
                           for g in touch_geo.values())
        v9_detail["v4_touch_geometric"] = {
            dt: {"touch_geometric_eq_s": r["touch_geometric_eq_s"],
                 "r15_minus_geometric_in_dt": r["r15_minus_geometric_in_dt"]}
            for dt, r in ((r["dt_s"], r) for cid, r in res.items()
                          if cid.startswith("v4touch_dt"))}
    v4u = {r["dt_s"]: r for cid, r in res.items() if cid.startswith("v4_D_u")}
    v4w = {cid: r for cid, r in res.items() if cid.startswith("v4_D_w")}
    if V9_REF_DT in v4u:
        touch = {dt: r["touch_eq_s"] for dt, r in v4u.items()}
        peakc = {dt: r["peak_cylinder_force_N"] for dt, r in v4u.items()}
        fin = {dt: r["final"]["contact_force_N"] for dt, r in v4u.items()}
        fatt = {dt: r["final"]["attitude_deg"] for dt, r in v4u.items()}
        labels = {dt: f"uniform dt {dt:g} s" for dt in v4u}
        dt_touch = {dt: dt for dt in v4u}
        # windowed runs compared with the same reference (keys: negative dummy dt per case)
        for k, (cid, r) in enumerate(sorted(v4w.items())):
            key = -(k + 1.0)
            touch[key] = r["touch_eq_s"]
            peakc[key] = r["peak_cylinder_force_N"]
            fin[key] = r["final"]["contact_force_N"]
            fatt[key] = r["final"]["attitude_deg"]
            labels[key] = f"{cid} (windowed {r['dt_s']:g} / 1e-05 s)"
            dt_touch[key] = float(params.get("simulation.dt_transition_s"))
        v9 += v9_v4_checks(touch_eq_by_dt=touch, ref_dt_s=V9_REF_DT, peak_cyl_by_dt=peakc,
                           final_force_by_dt=fin, final_attitude_by_dt=fatt, total_weight_N=w,
                           label_by_dt=labels)
        v9_detail["v4_r15_touch_recorded"] = v9_v4_r15_touch_record(
            touch_eq_by_dt=touch, ref_dt_s=V9_REF_DT, dt_at_touch_by_key=dt_touch,
            geometric_diff_max_s=geo_diff_max, label_by_dt=labels)
        v9_detail["v4"] = {labels[k]: {"touch_eq_s": touch[k],
                                       "touch_minus_ref_ms": (1e3 * (np.asarray(touch[k]) -
                                                              np.asarray(touch[V9_REF_DT])))
                                       .tolist(),
                                       "peak_cyl_N": peakc[k], "final_contact_N": fin[k],
                                       "final_attitude_deg": fatt[k]} for k in touch}
    all_checks = []
    per_case = {}
    rejudged = {}
    for cid, r in sorted(res.items()):
        case_checks = r.get("checks", [])
        if cid.startswith("v8a_crawler") and r.get("modes"):
            # dynamics_model.md 5.7 (a) applied to the stored values (no re-run needed)
            new, recorded = v8a_crawler_checks(
                cid, dt_s=r["dt_s"], energy_rise_rel=r["energy_rise_rel_geometric"],
                energy_trend_rel_over_window=r["energy_trend_rel_over_window"],
                window_s=V8A_WINDOW_S, modes=r["modes"],
                zeta_physical={m["mode"]: m["zeta_physical"] for m in r["modes"]},
                n_events=r["events"])
            case_checks = summary_table(new)
            r["all_passed"] = all(c["passed"] for c in case_checks)
            rejudged[cid] = {"recorded_only": recorded,
                             "previous_checks_failed": [c["item"] for c in r.get("checks", [])
                                                        if not c["passed"]]}
        per_case[cid] = {"all_passed": r.get("all_passed"), "dir": r["_dir"],
                         "params_sha256": _case_params_sha(r["_dir"])}
        for c in case_checks:
            all_checks.append({**c, "case": cid})
    v9_tab = summary_table(v9)
    all_checks += [{**c, "case": "V9"} for c in v9_tab]
    failed = [c for c in all_checks if not c["passed"]]
    judged = res.get(V4_JUDGED_RUN)
    previous = res.get(V4_PREVIOUS_JUDGED_RUN)
    v4_judged = {
        "case": V4_JUDGED_RUN,
        "dir": judged["_dir"] if judged else None,
        "all_passed": judged.get("all_passed") if judged else None,
        "comparison_case": V4_PREVIOUS_JUDGED_RUN,
        "comparison": (v4_judged_run_comparison(judged, previous) if judged and previous else None),
    }
    if judged is None:
        print(f"WARNING judged V4 run {V4_JUDGED_RUN} missing from {_rel(INDEX)}")
    summary = {
        "stage": "S3",
        "model": "L1",
        "level": LEVEL,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "params_sha256": params.sha256,
        "reference_sha256": refs.sha256_by_file(),
        "per_case": per_case,
        "v4_judged": v4_judged,
        "v8a_crawler_rejudged_rev17": rejudged,
        "v9": {"checks": v9_tab, "detail": _plain(v9_detail),
               "all_passed": all(c["passed"] for c in v9_tab) if v9_tab else None},
        "n_checks": len(all_checks),
        "n_failed": len(failed),
        "failed": failed,
        "cases": {cid: {k: v for k, v in r.items() if k not in ("series", "checks")}
                  for cid, r in res.items()},
        "checks": all_checks,
        "notes": {
            "v4_time_origin": "touch / crawler-off times from the measured equivalent start "
            "(t - s_ref / v_max in the constant-speed phase) = start command + ramp/2 + dt/2 "
            "(discrete ramp); dynamics_model.md 5 V4 rev. 15",
            "v9_v4_touch": "judged on the geometric touch time <= 1e-4 s for every dt; the R15 "
            "touch (first N > 0 step) is recorded with its structural bound 2 dt - dt_ref + "
            "geometric difference (dynamics_model.md 5.7 (b), rev. 17)",
            "v8a_crawler": "judged on modal zeta >= -1 % physical zeta and the 1-s mean trend "
            "<= +1 % E_kin0; max(E - E0) recorded (dynamics_model.md 5.7 (a), rev. 17); "
            "re-judged here from the stored result.json values",
            "yaml": "regenerated 2026-10-21 (simulation.L1.dt_s 2e-4 s, actuator.command_ramp_s "
            "0.1 s; user decision 2026-10-21). Cases run before it keep their params_sha256 "
            "(per_case); their dt and ramp were explicit, so the judgements stand "
            "(dynamics_model.md 5.7 rerun list)",
            "v4_judged": f"judged V4 run {V4_JUDGED_RUN} (YAML simulation.L1.dt_s + 1e-5 s "
            f"transition window) since 2026-10-21; {V4_PREVIOUS_JUDGED_RUN} (first S3 batch) "
            "is kept as a comparison record (v4_judged.comparison = judged - previous); every "
            "V4 run keeps its own checks; ctrl1_replay still replays the "
            f"{V4_PREVIOUS_JUDGED_RUN} Record",
        },
    }
    SUMMARY.write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"summary -> {_rel(SUMMARY)}: {len(all_checks)} checks, {len(failed)} failed")
    for c in failed:
        print("  FAIL", c["case"], c["id"], c["item"], c["value"], c["ref"], c["tol"])
    try:
        _figure(res)
    except Exception as exc:  # figure is secondary
        print(f"figure failed: {exc!r}")


def _figure(res):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(2, 3, figsize=(17, 9.5))
    legs = ("FL", "FR", "RL", "RR")
    colors = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728")
    from outrigger_sim.verify.s3 import V4_JUDGED_RUN

    main = res.get(V4_JUDGED_RUN)
    if main:
        s = main["series"]
        t = np.asarray(s["t_s"]) - main["equivalent_origin_s"]["measured"]
        n = np.asarray(s["pad_normal_N"]) / 1e3
        for i in range(4):
            ax[0, 0].plot(t, n[:, i], color=colors[i], label=legs[i])
            ax[0, 0].axvline(main["touch_ref_dynamic_s"][i], color=colors[i], ls=":", lw=0.8)
        ax[0, 0].set(xlabel="t from equivalent start (start command + ramp/2) [s]",
                     ylabel="pad contact force [kN]",
                     title=f"V4 lift {V4_JUDGED_RUN}, layout D, dt {main['dt_s']:.0e} s + "
                     "1e-5 s window\ndotted: dynamic reference touch times")
        ax[0, 0].legend(loc="lower right")
        ta = np.asarray(s["t_att_s"]) - main["equivalent_origin_s"]["measured"]
        aa = np.asarray(s["attitude_deg"])
        ax[0, 1].plot(ta, aa[:, 0], label="roll")
        ax[0, 1].plot(ta, aa[:, 1], label="pitch")
        ax[0, 1].axvline(main["plan"]["last_stop_s"] - main["equivalent_origin_s"]["measured"],
                         color="k", ls=":", lw=0.8, label="last stop")
        ax[0, 1].set(xlabel="t from equivalent start [s]", ylabel="attitude [deg]",
                     title="V4 attitude (crawler pose -> pads)")
        ax[0, 1].legend()
    ax2 = ax[0, 2].twinx()
    for cid, r in sorted(res.items()):
        if cid.startswith("v8a_") and "series" in r:
            s = r["series"]
            y = np.asarray(s["dE_geometric_J"]) / r["E_kin0_J"] * 100
            if r.get("where") == "crawler":
                ax[0, 2].plot(s["t_s"], y, lw=0.6, alpha=0.8,
                              color="#555555" if "1e-04" in cid else "#9467bd",
                              label=f"{cid} (left axis)")
            else:
                ax2.plot(s["t_s"], y, lw=1.4, ls="--",
                         color="#1f77b4" if "1e-04" in cid else "#d62728",
                         label=f"{cid} (right axis)")
    ax[0, 2].axhline(1.0, color="k", ls=":", lw=0.8)
    ax[0, 2].set(xlabel="t [s]", ylabel="crawler: (E - E0) / E_kin0 [%]",
                 title="V8(a) energy, all physical damping 0\n"
                 "crawler: explicit SMC only; pads: implicit bushing r omega dt/2")
    ax2.set_ylabel("pads: (E - E0) / E_kin0 [%]")
    h1, l1 = ax[0, 2].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax[0, 2].legend(h1 + h2, l1 + l2, fontsize=7, loc="center right")
    for cid, ls in (("v6_FLp", "-"), ("v6_FLm", "--")):
        r = res.get(cid)
        if not r or "series" not in r:
            continue
        s = r["series"]
        fc = np.asarray(s["cylinder_force_N"]) / 1e3
        for i in range(4):
            ax[1, 0].plot(s["travel_mm"], fc[:, i], color=colors[i], ls=ls, lw=1.0,
                          label=f"{r['direction']} {legs[i]}")
    ax[1, 0].axhline(9.45254751, color="k", ls=":", lw=0.8, label="F_min")
    ax[1, 0].set(xlabel="|FL travel| [mm]", ylabel="cylinder force [kN]",
                 title="V6: FL+ (solid) / FL- (dashed) at 0.1 mm/s")
    ax[1, 0].legend(fontsize=7, ncol=2)
    v4u = sorted((r["dt_s"], r["touch_eq_s"]) for cid, r in res.items()
                 if cid.startswith("v4_D_u"))
    geo = sorted((r["dt_s"], r["touch_geometric_eq_s"]) for cid, r in res.items()
                 if cid.startswith("v4touch_dt"))
    if v4u:
        ref = np.asarray(v4u[0][1])
        for dt, tch in v4u:
            ax[1, 1].semilogx([dt] * 4, (np.asarray(tch) - ref) * 1e3, "o", color="#1f77b4",
                              label="R15 touch (first N > 0 step)" if dt == v4u[0][0] else None)
    if geo:
        gref = np.asarray(geo[0][1])
        for dt, tch in geo:
            ax[1, 1].semilogx([dt] * 4, (np.asarray(tch) - gref) * 1e3, "x", color="#d62728",
                              label="geometric touch (interpolated)" if dt == geo[0][0] else None)
    dts = np.array([1e-5, 2e-4])
    ax[1, 1].plot(dts, dts * 1e3, "k:", lw=0.8, label="1 dt")
    ax[1, 1].plot(dts, 2 * dts * 1e3, "k--", lw=0.8, label="2 dt")
    ax[1, 1].set(xlabel="dt [s]", ylabel="touch time - dt 1e-5 s run [ms]",
                 title="V9: V4 touch times (4 legs per dt)")
    ax[1, 1].legend(fontsize=8)
    st = sorted((r["dt_s"], r.get("transient_min_dF_elastic_RL_N")) for cid, r in res.items()
                if cid.startswith("v9_step"))
    fr = sorted((r["dt_s"], r["amplitude_at_5s"]) for cid, r in res.items()
                if cid.startswith("v9_free"))
    if st and fr and st[0][1] is not None:
        ref_s = st[0][1]
        ref_f = fr[0][1]
        ax[1, 2].loglog([d for d, _ in st[1:]], [abs(v - ref_s) for _, v in st[1:]], "o-",
                        label="|peak elastic dF_RL - ref| [N] (FL +1 mm step)")
        ax[1, 2].loglog([d for d, _ in fr[1:]], [abs(v / ref_f - 1) * 1e4 for _, v in fr[1:]],
                        "s-", label="|A1(5 s) / ref - 1| x 1e4 (mode-1 free vibration)")
        ax[1, 2].set(xlabel="dt [s]", ylabel="error vs dt 1e-5 s run",
                     title="V9 smooth tests: first order (slope 1)")
        ax[1, 2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=110)
    plt.close(fig)
    print(f"figure -> {_rel(FIGURE)}")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("run", "replay", "summary", "list", "reindex"))
    ap.add_argument("--jobs", type=int, default=MAX_WORKERS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if args.jobs > MAX_WORKERS:
        raise SystemExit(f"--jobs <= {MAX_WORKERS}")
    if args.action == "reindex":
        reindex()
        return
    if args.action == "list":
        print("\n".join(case_ids()))
        return
    if args.action == "run":
        ids = args.only or case_ids()
        run_batch(ids, args.jobs)
        summarize()
    elif args.action == "replay":
        run_batch(["ctrl1_replay"], 1)
        summarize()
    else:
        summarize()


if __name__ == "__main__":
    main(sys.argv[1:])
