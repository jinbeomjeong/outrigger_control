"""S4 branch A runs: six-mode identification (V7), beta sensitivity, leg damping sensitivity,
optional rod-side chamber stiffness.

``00_docs/03_chrono/chrono_build_plan.md`` S4; checks in ``outrigger_sim.verify.s4``. Branch B
(V8(b) energy balance) is ``run_S4_energy.py`` and is not touched here.
Usage (Chrono-dev python, from any folder)::

    python -I -u run_S4.py modes   [--jobs 4]   # V7: six initial velocities from the S1 state
    python -I -u run_S4.py beta    [--jobs 4]   # beta 0.69 / 1.0 / 1.6 GPa: statics, V5, V6, ERA
    python -I -u run_S4.py damping [--jobs 4]   # leg zeta 0.01 (dt 5e-5 s) / 0.10 (YAML dt)
    python -I -u run_S4.py rodside [--jobs 4]   # optional: rod-side chamber k_v x 1.10 (record)
    python -I -u run_S4.py all     [--jobs 4]   # every group in one batch + summary
    python -I -u run_S4.py run --only CASE ...  # selected cases + summary
    python -I -u run_S4.py summary | list

Cases (L1, top, YAML ``simulation.L1.dt_s`` unless named):

* ``modes_<exc>`` (exc = roll, pitch, yaw, surge, heave, sway, ``verify.s4.EXCITATIONS``):
  restore the S1 settled state ``07_results/states/S1_L1_top``, add the rigid initial
  velocity about / of the rev. 13 mode-shape reference point, free vibration 20 s (roll,
  pitch) or 2 s. Modal projection ``eta = Phi^T M q`` (``V7_ball_centre_bushing_rev13 /
  mode_shapes``) + one damped cosine per mode; 6-channel ERA on ``q`` as the cross-check.
* ``beta<GPa>_static`` / ``_v6`` / ``_modes_<exc>`` (``beta0.69``, ``beta1.00``, ``beta1.60``
  for ``reference.L1_BETA_CASES``, :func:`beta_tag`): pad
  ``k_n`` overridden with ``L1_beta_sensitivity_top / <b> / k_L1_N_m`` (nothing else, plan rev. 5
  rule); start = linear 3-DoF static solution of that ``k_n`` (``scenarios.settle.
  linear_static_solution``, equal to the reference penetration / pitch to the printed digits),
  settle 10 s + still 5 s (V2 / V3), then: ``static`` FL +1 mm at 0.5 mm/s + 10 s (V5);
  ``v6`` FL+ at 0.1 mm/s through lift-off with ``simulation.dt_transition_s`` from 0.3 mm before
  the reference lift-off (S3 V6 procedure); ``modes_<exc>`` the six excitations, ERA only
  (Phi belongs to the nominal stiffness, plan risk #14).
* ``zeta<z>_modes_<exc>`` (z = 0.01, 0.10): every pad dashpot (``g_n``, bushing ``c_t`` input,
  and the recorded ``c_n`` / ``c_t``) scaled by ``z / 0.03``; start = nominal analytic static
  start + 15 s settle at the run dt. zeta 0.01 runs at 5e-5 s (CLAUDE.md dt rule exception:
  ``r omega dt / 2`` must stay <= 10 % of the reduced physical zeta).
* ``rodside_static`` / ``rodside_modes_<exc>`` (optional): ``k_n`` x
  ``hydraulic_circuit / kv_with_rod_side_over_kv`` (linear, both directions: upper bound).

Outputs: ``07_results/S4/A_modes/batch_<stamp>/<case>/`` (case.json, case.log, result.json,
series.npz), ``07_results/S4/A_modes/index.json``; summary
``06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json``, beta table ``verify_S4_L1_beta.csv``,
figures ``verify_S4_L1_modes.png`` and ``verify_S4_L1_beta.png``.
Units SI; angles in deg where named ``*_deg``; frequencies Hz.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
from pathlib import Path

# One BLAS thread per case process (set before numpy loads; spawned cases inherit it): the
# cases are pinned to the P-cores next to each other and next to branch B, and a multi-threaded
# OpenBLAS SVD / eig under a shared affinity mask slows every process down.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S4" / "A_modes"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states"
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "14_S4"
SUMMARY = ANALYSIS_DIR / "verify_S4_L1_modes.json"
BETA_TABLE = ANALYSIS_DIR / "verify_S4_L1_beta.csv"
FIGURE = ANALYSIS_DIR / "verify_S4_L1_modes.png"
BETA_FIGURE = ANALYSIS_DIR / "verify_S4_L1_beta.png"
S4_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s4_check.json"
"""dyn independent check (expected beta MAC, ``E_beta_mode_shape_MAC``)."""
LEVEL = "top"
S1_SNAPSHOT = "S1_L1_top"
MAX_WORKERS = 4
"""Main-session rule for S4 branch A: at most 4 Chrono processes (branch B uses 3)."""
CASE_TIMEOUT_S = 1500.0
SAMPLE_S = 1.0e-3
COARSE_SAMPLE_S = 1.0e-2
SETTLE_S = 10.0
STILL_S = 5.0
LEG_ZETAS = (0.01, 0.10)
LOW_ZETA_DT_S = 5.0e-5
"""CLAUDE.md dt rule exception for the leg zeta 0.01 runs (c_t reduced)."""
V5_SPEED_M_S = 0.5e-3
V5_HOLD_S = 3.0
V5_SETTLE_S = 10.0
V6_SPEED_M_S = 0.1e-3
V6_BEYOND_LIFTOFF_M = 0.6e-3
V6_WINDOW_BEFORE_LIFTOFF_M = 0.3e-3
ERA_DECIMATE = 5
"""1 ms samples -> 5 ms (Nyquist 100 Hz, modes <= 9.3 Hz)."""
ERA_ORDER = 24
ERA_ORDER_CHECK = 32
ERA_BLOCK_ROWS = 40
STIFFNESS_BAND_REL = 0.25
"""ERA selection band of the runs with another k_n (beta, rod side); see :func:`identify`."""
LEGS = ("FL", "FR", "RL", "RR")


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
    if isinstance(value, complex):
        return [value.real, value.imag]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


# --- case table -----------------------------------------------------------------------------


def _exc_names():
    from outrigger_sim.verify.s4 import EXCITATIONS

    return tuple(EXCITATIONS)


def _beta_cases():
    from outrigger_sim.verify.reference import L1_BETA_CASES

    return L1_BETA_CASES


def beta_tag(beta: str) -> str:
    """Case-id prefix of a reference beta key (beta_6.9e+08 -> beta0.69; case ids
    allow [A-Za-z0-9._-] only)."""
    return f"beta{float(beta.removeprefix('beta_')) / 1e9:.2f}"


def group_ids(group: str) -> list[str]:
    ex = _exc_names()
    if group == "modes":
        return [f"modes_{e}" for e in ex]
    if group == "beta":
        out = []
        for b in _beta_cases():
            tag = beta_tag(b)
            out += [f"{tag}_static", f"{tag}_v6"] + [f"{tag}_modes_{e}" for e in ex]
        return out
    if group == "damping":
        return [f"zeta{z:.2f}_modes_{e}" for z in LEG_ZETAS for e in ex]
    if group == "rodside":
        return ["rodside_static"] + [f"rodside_modes_{e}" for e in ex]
    raise SystemExit(f"unknown group {group!r}")


def case_ids() -> list[str]:
    return [c for g in ("modes", "beta", "damping", "rodside") for c in group_ids(g)]


def _yaml_dt() -> float:
    from outrigger_sim.params import load_params

    return float(load_params(level=LEVEL).simulation.L1.dt_s)


def case_settings(case_id: str) -> dict:
    """Settings of one case (JSON-ready; the job rebuilds everything from them)."""
    dt = _yaml_dt()
    if case_id.startswith("modes_"):
        return {"kind": "modes", "variant": "nominal", "exc": case_id.removeprefix("modes_"),
                "dt": dt, "start": "snapshot"}
    for b in _beta_cases():
        if case_id.startswith(beta_tag(b) + "_"):
            rest = case_id.removeprefix(beta_tag(b) + "_")
            base = {"variant": "beta", "beta": b, "dt": dt, "start": "linear"}
            if rest == "static":
                return {**base, "kind": "static"}
            if rest == "v6":
                return {**base, "kind": "v6"}
            return {**base, "kind": "modes", "exc": rest.removeprefix("modes_")}
    if case_id.startswith("zeta"):
        z_text, rest = case_id.removeprefix("zeta").split("_", 1)
        z = float(z_text)
        return {"kind": "modes", "variant": "damping", "leg_zeta": z,
                "dt": LOW_ZETA_DT_S if z < 0.03 else dt, "start": "analytic",
                "exc": rest.removeprefix("modes_"),
                "dt_source": "CLAUDE.md exception 5e-5 s" if z < 0.03 else "YAML"}
    if case_id.startswith("rodside_"):
        rest = case_id.removeprefix("rodside_")
        base = {"variant": "rodside", "dt": dt, "start": "linear"}
        if rest == "static":
            return {**base, "kind": "static"}
        return {**base, "kind": "modes", "exc": rest.removeprefix("modes_")}
    raise SystemExit(f"unknown case {case_id!r}")


# --- parameters per variant --------------------------------------------------------------------


def variant_overrides(settings: dict) -> dict:
    """YAML overrides of a case (run time only, the YAML is not changed)."""
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references
    from outrigger_sim.verify.s4 import ROD_SIDE_KV_RATIO, damping_scale

    v = settings["variant"]
    if v == "nominal":
        return {}
    refs = load_references()
    base = load_params(level=LEVEL)
    l1 = "contact.rigid_floor.L1"
    if v == "beta":
        k = refs.get(BETA_K_L1_N_M, beta=settings["beta"])
        return {f"{l1}.kn_per_pad_N_m.{leg}": float(x) for leg, x in zip(LEGS, k, strict=True)}
    if v == "rodside":
        ratio = refs.get(ROD_SIDE_KV_RATIO)
        return {f"{l1}.kn_per_pad_N_m.{leg}": float(base.get(f"{l1}.kn_per_pad_N_m.{leg}")) * r
                for leg, r in zip(LEGS, ratio, strict=True)}
    if v == "damping":
        s = damping_scale(float(settings["leg_zeta"]))
        over = {f"{l1}.derivation.damping_ratio": float(settings["leg_zeta"])}
        for leg in LEGS:
            for key in ("gn_per_pad_1_s", "bushing_damping_input_per_pad_N_s_m",
                        "cn_per_pad_N_s_m", "ct_per_pad_N_s_m"):
                over[f"{l1}.{key}.{leg}"] = float(base.get(f"{l1}.{key}.{leg}")) * s
        return over
    raise ValueError(v)


def _linear_start_pose(params):
    """Analytic static start (``scenarios.settle.analytic_static_pose`` logic) with the pose of
    the linear 3-DoF solution of the run's own ``k_n`` instead of the nominal V2 / V3 values."""
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import operating_extensions_m
    from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix
    from outrigger_sim.geometry import pad_sphere_centre_body_m
    from outrigger_sim.scenarios.settle import linear_static_solution

    ext = operating_extensions_m(params)
    lin = linear_static_solution(params, params.contact.rigid_floor.L1.kn_per_pad_N_m)
    roll, pitch = float(lin["q"][1]), float(lin["q"][2])
    pen = np.asarray(lin["penetration_m"], dtype=float)
    quat = quat_from_euler_zyx(0.0, pitch, roll)
    rot = quat_to_matrix(quat)
    floor = params.ground.crawler_bottom_z_m
    radii = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    cz = np.array([(rot @ pad_sphere_centre_body_m(params, i, float(ext[i])))[2]
                   for i in range(len(params.legs))])
    origin_z = float(np.mean(radii - pen - cz + floor))
    info = {"kind": "linear 3-DoF static solution of the run k_n",
            "roll_deg": math.degrees(roll), "pitch_deg": math.degrees(pitch),
            "penetration_mm": (pen * 1e3).tolist(), "origin_z_m": origin_z}
    return BodyPose((0.0, 0.0, origin_z), tuple(float(c) for c in quat)), info


def _settled_model(params, refs, settings, *, actuator):
    """Model at rest in its static equilibrium: S1 snapshot (nominal) or start + settle."""
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m, run_settle
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    dt = float(settings["dt"])
    start = settings["start"]
    if start == "snapshot":
        sp = analytic_static_pose(params, refs, operating_extensions_m(params))
        model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), dt_s=dt,
                        actuator=actuator)
        t0 = model.restore(load_snapshot(S1_SNAPSHOT, params_sha256=params.sha256,
                                         directory=STATES))
        return model, t0, {"kind": f"snapshot {S1_SNAPSHOT}", "t_s": t0}, None
    if start == "linear":
        pose, info = _linear_start_pose(params)
    else:
        sp = analytic_static_pose(params, refs, operating_extensions_m(params))
        pose = BodyPose(sp.origin_m, sp.quat_wxyz)
        info = {"kind": "nominal analytic static start (V2 / V3 reference)"}
    model = L1Model(params, pose=pose, dt_s=dt, actuator=actuator)
    run = run_settle(model, SETTLE_S, STILL_S, coarse_sample_s=COARSE_SAMPLE_S,
                     fine_sample_s=SAMPLE_S)
    t0 = float(model.system.GetChTime())
    info.update(settle_s=SETTLE_S, still_s=STILL_S, settle_events=len(run.events),
                settle_yield_steps=model.bushing.yield_steps.tolist())
    return model, t0, info, run.stats


def _stats_dict(stats):
    if stats is None:
        return None
    return {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in stats.__dict__.items()}


def _run_meta(params, model, scenario, settings, extra=None):
    from outrigger_sim.record import make_run_meta
    from outrigger_sim.verify.reference import load_references

    return make_run_meta(params, model.meta(), scenario=scenario, scenario_settings=settings,
                         reference_sha256=load_references().sha256_by_file(), extra=extra or {})


# --- identification -----------------------------------------------------------------------------


def _mode_reference(refs, settings):
    """Reference frequencies / zeta of the variant and whether Phi is valid for it."""
    import numpy as np

    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.verify.reference import BETA_F_HZ_TOP_BALL_CENTRE_REV13
    from outrigger_sim.verify.s4 import damping_scale, first_order_zeta

    modal = modal_reference(refs, LEVEL)
    v = settings["variant"]
    f_ref = np.asarray(modal.f_damped_Hz, dtype=float)
    zeta_ref = np.asarray(modal.zeta, dtype=float)
    f_key = modal.keys["f_damped_Hz"]
    phi_valid = v in ("nominal", "damping")
    if v == "beta":
        f_ref = np.asarray(refs.get(BETA_F_HZ_TOP_BALL_CENTRE_REV13, beta=settings["beta"]),
                           dtype=float)
        f_key = BETA_F_HZ_TOP_BALL_CENTRE_REV13.resolve(beta=settings["beta"]).notation()
        zeta_ref = np.full(6, np.nan)
    elif v == "damping":
        zeta_ref = first_order_zeta(modal.zeta, damping_scale(float(settings["leg_zeta"])))
    elif v == "rodside":
        zeta_ref = np.full(6, np.nan)
    return modal, f_ref, zeta_ref, f_key, phi_valid


def identify(t, q, *, modal, f_ref, zeta_num, window_s, phi_valid, f_band_rel=0.15):
    """Projection fits (if Phi is valid) and ERA (two orders) of every mode of one run.

    ERA mode ``i`` = the pole whose largest modal coordinate (nominal Phi) is ``eta_i`` and
    that puts the most into ``eta_i``, within ``f_ref_i (1 +- f_band_rel)``
    (``metrics.select_era_mode``). Runs with another stiffness use a wider band, because
    their frequency-sorted reference list can swap labels (beta 1.6 GPa: heave-type mode 5
    rises above mode 6)."""
    import numpy as np

    from outrigger_sim.verify.metrics import (
        era_free_decay,
        fit_damped_sine,
        log_decrement,
        mass_mac,
        modal_amplitudes,
        modal_coordinates,
        projection_leakage,
        select_era_mode,
    )
    from outrigger_sim.verify.s4 import SHORT_WINDOW_S, fit_window_s

    phi, mm = modal.phi, modal.mass_matrix
    eta = modal_coordinates(q, phi, mm)
    scale = np.sqrt(np.diag(mm))
    eras = {}
    for label, win in (("long", window_s), ("short", min(window_s, SHORT_WINDOW_S))):
        mask = t <= win + 1e-9
        eras[label] = {order: era_free_decay(t[mask], q[mask], order=order,
                                             n_block_rows=ERA_BLOCK_ROWS,
                                             decimate=ERA_DECIMATE, channel_scale=scale)
                       for order in (ERA_ORDER, ERA_ORDER_CHECK)}
        if win >= window_s:
            eras["short" if label == "long" else "long"] = eras[label]
            break
    rows = []
    for i in range(6):
        win = fit_window_s(i, window_s)
        mask = t <= win + 1e-9
        row = {"mode": i + 1, "fit_window_s": win, "f_ref_Hz": float(f_ref[i]),
               "zeta_num": float(zeta_num[i]), "eta_max_abs": float(np.abs(eta[mask, i]).max())}
        if phi_valid:
            fit = fit_damped_sine(t[mask], eta[mask, i], float(f_ref[i]))
            row.update(
                f_proj_Hz=fit.f_undamped_Hz, f_damped_proj_Hz=fit.f_damped_Hz,
                zeta_fit=fit.zeta, zeta_proj=fit.zeta - float(zeta_num[i]),
                fit_residual_rms_rel=fit.residual_rms_rel, n_cycles=fit.n_cycles,
                amplitude=fit.amplitude, sigma_1_s=fit.sigma_1_s, fit_success=fit.success,
                zeta_log_decrement=log_decrement(t[mask], eta[mask, i], fit.f_damped_Hz),
            )
        label = "long" if win >= window_s else "short"
        era_rows = {}
        for order, era in eras[label].items():
            k = select_era_mode(era, i, phi, mm, float(f_ref[i]), f_band_rel=f_band_rel)
            if k is None:
                era_rows[str(order)] = None
                continue
            m = era.modes[k]
            era_rows[str(order)] = {
                "f_Hz": m.f_undamped_Hz, "f_damped_Hz": m.f_damped_Hz, "zeta_raw": m.zeta,
                "zeta": m.zeta - float(zeta_num[i]),
                "mac_vs_phi": mass_mac(m.shape, phi[:, i], mm),
                "eta_start_amplitude": float(modal_amplitudes(era, phi, mm)[i, k]),
                "leakage": projection_leakage(era, i, k, phi, mm),
                "window_s": list(era.window_s), "residual_rms_rel": era.residual_rms_rel,
                "n_oscillatory_modes": len(era.modes),
            }
        main, chk = era_rows[str(ERA_ORDER)], era_rows[str(ERA_ORDER_CHECK)]
        row["era"] = main
        row["era_order_check"] = chk
        if main and chk:
            row["era_order_spread"] = {
                "f_rel": abs(chk["f_Hz"] / main["f_Hz"] - 1.0),
                "zeta_rel": abs(chk["zeta_raw"] / main["zeta_raw"] - 1.0)
                if main["zeta_raw"] else None,
            }
        rows.append(row)
    era_overview = {
        label: [{"f_Hz": m.f_undamped_Hz, "zeta_raw": m.zeta,
                 "rms_mass_weighted": float(np.linalg.norm(m.rms_per_channel * scale))}
                for m in eras[label][ERA_ORDER].modes]
        for label in ("long", "short")
    }
    return rows, eta, era_overview


# --- jobs -----------------------------------------------------------------------------------------


def job_modes(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.checks import all_passed, summary_table
    from outrigger_sim.verify.metrics import rigid_displacement
    from outrigger_sim.verify.reference import load_references
    from outrigger_sim.verify.s2a import run_health_checks
    from outrigger_sim.verify.s4 import EXCITATIONS, zeta_num_share

    s = dict(case.settings)
    overrides = variant_overrides(s)
    params = load_params(level=LEVEL, overrides=overrides)
    refs = load_references()
    modal, f_ref, zeta_ref, f_key, phi_valid = _mode_reference(refs, s)
    exc = EXCITATIONS[s["exc"]]
    t_w0 = time.perf_counter()
    model, t0, start_info, stats = _settled_model(params, refs, s, actuator=False)
    settle_wall = time.perf_counter() - t_w0
    zeta_num, zeta_num_src = modal.zeta_num_at(model.dt_s)
    p0 = model.probe()
    rot0 = quat_to_matrix(p0.body_quat_wxyz)
    point = p0.body_pos_m + rot0 @ modal.reference_point_body_m
    f_target = float(f_ref[exc.target_mode])
    v_exc, w_exc = exc.velocity(f_target)
    residual = {"body_vel_m_s": np.asarray(p0.body_vel_m_s).tolist(),
                "body_omega_rad_s": np.asarray(p0.body_omega_rad_s).tolist(),
                "vel_over_excitation": float(np.linalg.norm(p0.body_vel_m_s))
                / max(float(np.linalg.norm(v_exc + np.cross(w_exc, p0.body_pos_m - point))),
                      1e-30),
                "omega_over_excitation": float(np.linalg.norm(p0.body_omega_rad_s))
                / max(float(np.linalg.norm(w_exc)), 1e-30)
                if np.linalg.norm(w_exc) > 0 else None}
    set_rigid_velocity(model, v_exc, w_exc, point)
    run = run_free_vibration(model, exc.window_s, sample_s=SAMPLE_S)
    se = run.series
    t = se["t"] - t0
    q = rigid_displacement(se["origin"], se["quat"], p0.body_pos_m, p0.body_quat_wxyz,
                           modal.reference_point_body_m)
    rows, eta, era_overview = identify(t, q, modal=modal, f_ref=f_ref, zeta_num=zeta_num,
                                       window_s=exc.window_s, phi_valid=phi_valid,
                                       f_band_rel=0.15 if phi_valid else STIFFNESS_BAND_REL)
    for r, z in zip(rows, zeta_ref, strict=True):
        r["zeta_ref"] = float(z)
    checks = run_health_checks(case.case_id, se, n_events=len(run.events),
                               yield_steps=model.bushing.yield_steps.tolist())
    np.savez_compressed(case_dir / "series.npz", t=t, q=q, eta=eta, normal=se["normal"],
                        bushing_disp=se["bushing_disp"])
    phys = zeta_ref if s["variant"] != "beta" else modal.zeta
    summary = {
        "case": case.case_id, "settings": s, "overrides": overrides,
        "params_sha256": params.sha256, "dt_s": model.dt_s,
        "zeta_num": zeta_num.tolist(), "zeta_num_source": zeta_num_src,
        "zeta_num_over_physical": zeta_num_share(zeta_num, phys),
        "excitation": {**exc.__dict__, "f_target_Hz": f_target, "v_point_world_m_s": v_exc,
                       "omega_world_rad_s": w_exc, "about_point_world_m": point},
        "start": start_info, "still_window": _stats_dict(stats),
        "pre_excitation_residual": residual,
        "phi_valid": phi_valid, "f_ref_key": f_key, "modes": rows, "era_overview": era_overview,
        "checks": summary_table(checks), "all_passed": all_passed(checks),
        "extremes": {
            "pad_normal_min_N": se["normal"].min(axis=0), "pad_normal_max_N": se["normal"].max(axis=0),
            "bushing_disp_max_mm": np.nanmax(np.linalg.norm(se["bushing_disp"], axis=2), axis=0) * 1e3,
            "yield_steps": model.bushing.yield_steps.tolist(),
            "events": [[e.t_s - t0, e.leg, e.kind] for e in run.events],
        },
        "timing": {"settle_wall_s": settle_wall, "run_wall_s": run.wall_s, "steps": run.steps,
                   "us_per_step": run.wall_s / run.steps * 1e6},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S4_{case.case_id}", s))


def _window_mean(t, values, t0, t1):
    import numpy as np

    mask = (t >= t0 - 1e-9) & (t <= t1 + 1e-9)
    return np.asarray(values)[mask].mean(axis=0)


def job_static(case, case_dir):
    """Statics (V2, V3) after the settle, then FL +1 mm (V5)."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.settle import linear_static_solution
    from outrigger_sim.verify.reference import BETA_F_HZ_TOP_BALL_CENTRE_REV13, load_references

    s = dict(case.settings)
    overrides = variant_overrides(s)
    params = load_params(level=LEVEL, overrides=overrides)
    refs = load_references()
    t_w0 = time.perf_counter()
    model, t0, start_info, stats = _settled_model(params, refs, s, actuator=True)
    f1 = (float(refs.get(BETA_F_HZ_TOP_BALL_CENTRE_REV13, beta=s["beta"])[0])
          if s["variant"] == "beta" else 1.8)
    t1 = 1.0 / f1
    s0 = model.actuator.s_ref_m.copy()
    rows = {"t": [], "N": [], "Fcyl": [], "s_motor": []}

    def sample(p):
        rows["t"].append(p.t_s)
        rows["N"].append(p.pad_normal_force_N.copy())
        rows["Fcyl"].append(p.motor_force_N.copy())
        rows["s_motor"].append(p.motor_pos_m.copy())

    run_commanded(model, V5_HOLD_S, lambda _t: None, sample_s=COARSE_SAMPLE_S, on_sample=sample)
    t_base = float(model.system.GetChTime())
    hi = model.actuator.stroke_range_m[:, 1].copy()
    hi[0] = s0[0] + 1.0e-3
    model.actuator.set_soft_limits(hi_m=hi)
    model.set_command([V5_SPEED_M_S, 0.0, 0.0, 0.0])
    run = run_commanded(model, 1.0e-3 / V5_SPEED_M_S + 0.2 + V5_SETTLE_S, lambda _t: None,
                        sample_s=COARSE_SAMPLE_S, on_sample=sample)
    model.set_command([0.0, 0.0, 0.0, 0.0])
    t_end = float(model.system.GetChTime())
    a = {k: np.asarray(v) for k, v in rows.items()}
    base_n = _window_mean(a["t"], a["N"], t_base - 3 * t1, t_base)
    end_n = _window_mean(a["t"], a["N"], t_end - 3 * t1, t_end)
    travel_mm = float(a["s_motor"][-1, 0] - s0[0]) * 1e3
    lin = linear_static_solution(params, params.contact.rigid_floor.L1.kn_per_pad_N_m)
    summary = {
        "case": case.case_id, "settings": s, "overrides": overrides,
        "params_sha256": params.sha256, "dt_s": model.dt_s, "start": start_info,
        "still_window": _stats_dict(stats),
        "v5": {"travel_mm": travel_mm, "dF_N": (end_n - base_n).tolist(),
               "base_contact_N": base_n.tolist(), "window_3T1_s": 3 * t1,
               "events": len(run.events)},
        "linear_static": {"penetration_mm": (lin["penetration_m"] * 1e3).tolist(),
                          "roll_pitch_deg": np.degrees(lin["q"][1:]).tolist(),
                          "contact_N": lin["contact_N"].tolist()},
        "yield_steps": model.bushing.yield_steps.tolist(),
        "timing": {"wall_s": time.perf_counter() - t_w0},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S4_{case.case_id}", s))


def job_v6(case, case_dir):
    """FL+ at 0.1 mm/s through lift-off (S3 V6 procedure, beta reference distances)."""
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import DtWindow, run_windowed
    from outrigger_sim.params import LEG_ORDER, load_params
    from outrigger_sim.scenarios.lift import LegStep, crossing
    from outrigger_sim.verify.reference import (
        BETA_FL_PLUS_F_MIN_MM,
        BETA_FL_PLUS_LIFTOFF_MM,
        load_references,
    )

    s = dict(case.settings)
    overrides = variant_overrides(s)
    params = load_params(level=LEVEL, overrides=overrides)
    refs = load_references()
    lift_mm = float(refs.get(BETA_FL_PLUS_LIFTOFF_MM, beta=s["beta"]))
    fmin_ref_mm = float(refs.get(BETA_FL_PLUS_F_MIN_MM, beta=s["beta"]))
    t_w0 = time.perf_counter()
    model, t0, start_info, stats = _settled_model(params, refs, s, actuator=True)
    step = LegStep(name=case.case_id, leg=0, speed_m_s=V6_SPEED_M_S,
                   delta_m=lift_mm * 1e-3 + V6_BEYOND_LIFTOFF_M,
                   hold_before_s=0.5, hold_after_s=0.5,
                   transition_from_delta_m=lift_mm * 1e-3 - V6_WINDOW_BEFORE_LIFTOFF_M)
    s0 = model.actuator.s_ref_m.copy()
    lo, hi = step.soft_limits(s0, model.actuator.stroke_range_m)
    model.actuator.set_soft_limits(lo_m=lo, hi_m=hi)
    ramp = params.actuator.command_ramp_s
    win = step.transition_window_s(ramp)
    dt_tr = float(params.get("simulation.dt_transition_s"))
    windows = [DtWindow(win[0], min(win[1], step.end_s(ramp)), dt_tr, SAMPLE_S)]
    rows = {"t": [], "Fcyl": [], "N": [], "s_motor": []}

    def sample(p):
        rows["t"].append(p.t_s)
        rows["Fcyl"].append(p.motor_force_N.copy())
        rows["N"].append(p.pad_normal_force_N.copy())
        rows["s_motor"].append(p.motor_pos_m.copy())

    run = run_windowed(model, step.end_s(ramp), step.schedule(ramp), windows=windows,
                       base_dt_s=float(s["dt"]), sample_s=COARSE_SAMPLE_S, on_sample=sample)
    a = {k: np.asarray(v) for k, v in rows.items()}
    travel_mm = np.abs(a["s_motor"][:, 0] - s0[0]) * 1e3
    f_min = float(params.get("control.F_min_cylinder_N"))
    hits = {}
    for leg in range(1, 4):
        tc = crossing(a["t"], a["Fcyl"][:, leg], f_min, falling=True)
        if tc is not None:
            hits[LEG_ORDER[leg]] = float(np.interp(tc, a["t"], travel_mm))
    f_leg = min(hits, key=hits.get) if hits else None
    offs = [(tt, leg) for (tt, leg, st) in run.raw_contact_transitions if st == 0]
    lift_leg = LEG_ORDER[offs[0][1]] if offs else None
    lift_sim = float(np.interp(offs[0][0], a["t"], travel_mm)) if offs else None
    summary = {
        "case": case.case_id, "settings": s, "overrides": overrides,
        "params_sha256": params.sha256, "dt_s": float(s["dt"]), "dt_segments": run.dt_segments,
        "start": start_info, "still_window": _stats_dict(stats), "step": step.as_dict(),
        "F_min_N": f_min, "F_min_crossings_travel_mm": hits, "F_min_leg": f_leg,
        "F_min_travel_mm": None if f_leg is None else hits[f_leg],
        "liftoff_leg": lift_leg, "liftoff_travel_mm": lift_sim,
        "reference": {"FL+_F_min_mm": fmin_ref_mm, "FL+_liftoff_mm": lift_mm},
        "events": [[e.t_s - t0, LEG_ORDER[e.leg], e.kind] for e in run.events],
        "yield_steps": model.bushing.yield_steps.tolist(),
        "slip_total_mm": (model.bushing.slip_total_m * 1e3).tolist(),
        "timing": {"wall_s": time.perf_counter() - t_w0, "steps": run.steps},
    }
    return CaseResult(summary=_plain(summary),
                      run_meta=_run_meta(params, model, f"S4_{case.case_id}", s))


def job(case, case_dir):
    """Batch job (module level for spawn): dispatch on ``case.settings['kind']``."""
    fn = {"modes": job_modes, "static": job_static, "v6": job_v6}[case.settings["kind"]]
    out = fn(case, Path(case_dir))
    (Path(case_dir) / "result.json").write_text(
        json.dumps(_plain(dict(out.summary)), indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# --- batch ---------------------------------------------------------------------------------------


def _update_index(report, batch_dir):
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        if o.status == "ok":
            index[o.case_id] = _rel(Path(batch_dir) / o.case_id)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")


def _cost_rank(case_id: str) -> int:
    s = case_settings(case_id)
    if s["kind"] == "v6":
        return 0
    if s["kind"] == "modes" and s["exc"] in ("roll", "pitch"):
        return 1 if s["dt"] < 1e-4 else 2
    return 3


def run_batch(ids, jobs):
    from outrigger_sim.batch import Case, run_cases

    if jobs > MAX_WORKERS:
        raise SystemExit(f"--jobs <= {MAX_WORKERS}")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    order = sorted(ids, key=lambda c: (_cost_rank(c), c))
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
    print(f"batch wall {wall:.1f} s, jobs {jobs} -> {_rel(batch_dir)}", flush=True)
    _update_index(report, batch_dir)
    log = RESULTS / "batches.json"
    hist = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    hist.append({"batch": _rel(batch_dir), "cases": order, "jobs": jobs, "wall_s": wall,
                 "case_wall_s": {o.case_id: o.wall_s for o in report.outcomes}})
    log.write_text(json.dumps(hist, indent=1), encoding="utf-8")
    return report


# --- summary -------------------------------------------------------------------------------------


def _load_results():
    if not INDEX.exists():
        return {}
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    out = {}
    for cid, rel in index.items():
        p = ROOT / rel / "result.json"
        if p.exists():
            out[cid] = json.loads(p.read_text(encoding="utf-8"))
            out[cid]["_dir"] = rel
    return out


def _mode_matrix(res, prefix):
    """{exc: rows} of the six mode runs with the case-id prefix."""
    return {e: res[f"{prefix}{e}"]["modes"] for e in _exc_names() if f"{prefix}{e}" in res}


def _judged_rows(matrix, assignment):
    out = []
    for i, exc in enumerate(assignment):
        if exc not in matrix:
            out.append(None)
            continue
        out.append({"run": exc, **matrix[exc][i]})
    return out


def _spread(matrix, key, sub=None, min_rel_amp=0.2):
    """Per mode: min / max of ``key`` over the runs whose eta amplitude is >= min_rel_amp of
    the largest (weakly excited runs are left out)."""
    import numpy as np

    out = []
    for i in range(6):
        amps = {e: rows[i]["eta_max_abs"] for e, rows in matrix.items()}
        top = max(amps.values()) if amps else 0.0
        vals = []
        for e, rows in matrix.items():
            if amps[e] < min_rel_amp * top:
                continue
            v = rows[i].get(key) if sub is None else (rows[i].get(sub) or {}).get(key)
            if v is not None:
                vals.append((e, v))
        out.append({"runs": [e for e, _ in vals],
                    "min": float(np.min([v for _, v in vals])) if vals else None,
                    "max": float(np.max([v for _, v in vals])) if vals else None})
    return out


def summarize():
    import numpy as np

    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.verify.checks import summary_table
    from outrigger_sim.verify.reference import (
        BETA_DF_PER_MM_FL_N,
        BETA_FL_PLUS_F_MIN_MM,
        BETA_FL_PLUS_LIFTOFF_MM,
        BETA_F_HZ_TOP_BALL_CENTRE_REV13,
        BETA_PENETRATION_MM,
        BETA_STATIC_PITCH_DEG,
        load_references,
    )
    from outrigger_sim.verify.s4 import (
        ModeRow,
        assign_modes,
        beta_frequency_checks,
        beta_static_checks,
        beta_v5_checks,
        beta_mac_checks,
        beta_v6_checks,
        damping_mode_checks,
        judged_value,
        mode_info_checks,
        predicted_modal_amplitudes,
        summarize_check_ids,
        v7_six_mode_checks,
    )

    def mode_row(row):
        era = row.get("era") or {}
        return ModeRow(mode=row["mode"], run=row["run"], f_proj_Hz=row.get("f_proj_Hz"),
                       zeta_proj=row.get("zeta_proj"),
                       fit_residual_rms_rel=row.get("fit_residual_rms_rel"),
                       f_era_Hz=era.get("f_Hz"), zeta_era=era.get("zeta"),
                       leakage=era.get("leakage"), zeta_num=row["zeta_num"],
                       f_ref_Hz=row["f_ref_Hz"], zeta_ref=row["zeta_ref"])

    def judged_dict(r):
        j = judged_value(r)
        return {"f_Hz": j.f_Hz, "zeta": j.zeta, "source": j.source, "reason": j.reason}

    s4_check = json.loads(S4_CHECK.read_text(encoding="utf-8")) if S4_CHECK.exists() else {}
    mac_expect = s4_check.get("E_beta_mode_shape_MAC", {})
    info = []

    refs = load_references()
    modal = modal_reference(refs, LEVEL)
    assignment = assign_modes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
    res = _load_results()
    checks = []
    health = []
    for cid, r in res.items():
        for c in r.get("checks", []):
            health.append({"case": cid, **c})
    # --- V7 nominal
    nominal = _mode_matrix(res, "modes_")
    judged = _judged_rows(nominal, assignment)
    v7_rows = [mode_row(row) for row in judged if row is not None]
    v7_checks = summary_table(v7_six_mode_checks(
        v7_rows, ref_key_f=modal.keys["f_damped_Hz"], ref_key_zeta=modal.keys["zeta"]))
    checks += v7_checks
    info += summary_table(mode_info_checks(v7_rows, "V7"))
    for row, r in zip([x for x in judged if x is not None], v7_rows, strict=True):
        row["judged_value"] = judged_dict(r)
    # --- beta
    beta_out = {}
    csv_rows = []
    for b in _beta_cases():
        tag = beta_tag(b)
        st = res.get(f"{tag}_static")
        v6 = res.get(f"{tag}_v6")
        mat = _mode_matrix(res, f"{tag}_modes_")
        keys = {"penetration": BETA_PENETRATION_MM.resolve(beta=b).notation(),
                "pitch": BETA_STATIC_PITCH_DEG.resolve(beta=b).notation(),
                "f_min": BETA_FL_PLUS_F_MIN_MM.resolve(beta=b).notation(),
                "liftoff": BETA_FL_PLUS_LIFTOFF_MM.resolve(beta=b).notation()}
        ref = {"penetration_mm": list(refs.get(BETA_PENETRATION_MM, beta=b)),
               "static_pitch_deg": float(refs.get(BETA_STATIC_PITCH_DEG, beta=b)),
               "dF_per_mm_FL_N": list(refs.get(BETA_DF_PER_MM_FL_N, beta=b)),
               "FL+_F_min_mm": float(refs.get(BETA_FL_PLUS_F_MIN_MM, beta=b)),
               "FL+_liftoff_mm": float(refs.get(BETA_FL_PLUS_LIFTOFF_MM, beta=b)),
               "f_Hz_top_ball_centre_rev13": list(
                   refs.get(BETA_F_HZ_TOP_BALL_CENTRE_REV13, beta=b))}
        bc = []
        got = {}
        if st:
            w = st["still_window"]
            got.update(penetration_mm=w["penetration_mean_mm"], static_pitch_deg=w["pitch_mean_deg"],
                       static_roll_deg=w["roll_mean_deg"], contact_N=w["contact_force_mean_N"],
                       dF_FL_plus1mm_N=st["v5"]["dF_N"], v5_travel_mm=st["v5"]["travel_mm"])
            bc += beta_static_checks(b, penetration_mm=got["penetration_mm"],
                                     pitch_deg=got["static_pitch_deg"],
                                     ref_penetration_mm=ref["penetration_mm"],
                                     ref_pitch_deg=ref["static_pitch_deg"], keys=keys)
            bc += beta_v5_checks(b, dF_N=got["dF_FL_plus1mm_N"],
                                 ref_dF_per_mm_N=ref["dF_per_mm_FL_N"],
                                 key=BETA_DF_PER_MM_FL_N.resolve(beta=b).notation())
        if v6:
            got.update(F_min_mm=v6["F_min_travel_mm"], F_min_leg=v6["F_min_leg"],
                       liftoff_mm=v6["liftoff_travel_mm"], liftoff_leg=v6["liftoff_leg"],
                       v6_yield_steps_before_liftoff_record_only=v6["yield_steps"],
                       v6_slip_total_mm_record_only=v6["slip_total_mm"])
            bc += beta_v6_checks(b, f_min_mm=v6["F_min_travel_mm"],
                                 liftoff_mm=v6["liftoff_travel_mm"],
                                 ref_f_min_mm=ref["FL+_F_min_mm"],
                                 ref_liftoff_mm=ref["FL+_liftoff_mm"], keys=keys)
        if len(mat) == 6:
            jr = _judged_rows(mat, assignment)
            f_label = [(row.get("era") or {}).get("f_Hz") for row in jr]
            # the reference list is sorted by frequency (eigenvalue order); the ERA poles carry
            # nominal-Phi labels, so they are compared in frequency order as well
            f_era = sorted(f_label) if all(f is not None for f in f_label) else f_label
            got["f_era_Hz"] = f_era
            got["f_era_by_nominal_label_Hz"] = f_label
            got["label_order_of_sorted"] = (
                [f_label.index(f) + 1 for f in f_era] if f_era is not f_label else None
            )
            got["f_era_runs"] = assignment
            got["zeta_era_info"] = [(row.get("era") or {}).get("zeta") for row in jr]
            got["mac_vs_nominal_phi"] = [(row.get("era") or {}).get("mac_vs_phi") for row in jr]
            got["f_era_spread"] = _spread(mat, "f_Hz", sub="era")
            bc += beta_frequency_checks(b, f_era, ref["f_Hz_top_ball_centre_rev13"],
                                        BETA_F_HZ_TOP_BALL_CENTRE_REV13.resolve(beta=b).notation())
            exp = mac_expect.get(b)
            if exp and got["label_order_of_sorted"]:
                bc += beta_mac_checks(
                    b, mac_by_label=got["mac_vs_nominal_phi"],
                    label_of_sorted=got["label_order_of_sorted"],
                    expected_index=exp["best_nominal_index"], expected_mac=exp["best_MAC"],
                    key=f"s4_check.json / E_beta_mode_shape_MAC / {b}")
                got["mac_expected"] = exp
        bct = summary_table(bc)
        checks += bct
        beta_out[b] = {"reference": ref, "chrono": got, "checks": bct}
        for c in bct:
            csv_rows.append([b, c["id"], c["item"], c["value"], c["ref"], c["tol"], c["tol_kind"],
                             c["unit"], c["passed"]])
    # --- damping sensitivity (judged, dyn rev. 19)
    damping = {}
    for z in LEG_ZETAS:
        mat = _mode_matrix(res, f"zeta{z:.2f}_modes_")
        if not mat:
            continue
        jr = _judged_rows(mat, assignment)
        d_rows = [mode_row(row) for row in jr if row is not None]
        dc = summary_table(damping_mode_checks(d_rows, z, ref_key_f=modal.keys["f_damped_Hz"]))
        checks += dc
        info += summary_table(mode_info_checks(d_rows, f"leg zeta {z:g}"))
        any_case = res[f"zeta{z:.2f}_modes_{next(iter(mat))}"]
        damping[f"{z:.2f}"] = {
            "dt_s": any_case["dt_s"], "dashpot_scale": z / 0.03,
            "zeta_num": any_case["zeta_num"], "zeta_num_source": any_case["zeta_num_source"],
            "zeta_num_over_first_order_physical": any_case["zeta_num_over_physical"],
            "modes": [None if row is None else {
                "mode": row["mode"], "run": row["run"], "f_proj_Hz": row.get("f_proj_Hz"),
                "f_ref_nominal_Hz": row["f_ref_Hz"],
                "f_rel_vs_nominal_ref": None if row.get("f_proj_Hz") is None
                else row["f_proj_Hz"] / row["f_ref_Hz"] - 1.0,
                "zeta_proj": row.get("zeta_proj"),
                "zeta_first_order_expectation": row["zeta_ref"],
                "zeta_proj_over_expectation": None if row.get("zeta_proj") is None
                else row["zeta_proj"] / row["zeta_ref"],
                "fit_residual_rms_rel": row.get("fit_residual_rms_rel"),
                "f_era_Hz": (row.get("era") or {}).get("f_Hz"),
                "zeta_era": (row.get("era") or {}).get("zeta"),
                "leakage": (row.get("era") or {}).get("leakage"),
                "judged_value": judged_dict(mode_row(row)),
            } for row in jr],
            "checks": dc,
            "judgement": "judged (dyn ruling, dynamics_model.md rev. 19, 5.8): reference zeta = "
            "nominal zeta x (leg zeta / 0.03) +-30 %, f_n = nominal f_n +-3 %; ERA value where "
            "the fit residual > 0.05 or the ERA cross-check fails",
        }
    # --- rod side (record)
    rodside = None
    rs = res.get("rodside_static")
    mat = _mode_matrix(res, "rodside_modes_")
    if rs or mat:
        nominal_st = None
        rodside = {"note": "k_n x kv_with_rod_side_over_kv, linear in both directions (upper "
                   "bound; the locked rod-side chamber only stiffens on unloading, "
                   "dynamics_model.md 2.3); recorded as model uncertainty only (dyn ruling "
                   "rev. 19, 5.8)"}
        if rs:
            w = rs["still_window"]
            rodside.update(penetration_mm=w["penetration_mean_mm"], pitch_deg=w["pitch_mean_deg"],
                           dF_FL_plus1mm_N=rs["v5"]["dF_N"], linear_static=rs["linear_static"])
        if len(mat) == 6:
            jr = _judged_rows(mat, assignment)
            rodside["f_era_Hz"] = [(row.get("era") or {}).get("f_Hz") for row in jr]
            rodside["f_rel_vs_nominal_ref"] = [
                None if f is None else f / float(modal.f_damped_Hz[i]) - 1.0
                for i, f in enumerate(rodside["f_era_Hz"])]
        del nominal_st
    # --- summary
    by_id = summarize_check_ids(checks)
    by_id["health (V13, no yield / event)"] = all(c["passed"] for c in health)
    batches = json.loads((RESULTS / "batches.json").read_text(encoding="utf-8")) \
        if (RESULTS / "batches.json").exists() else []
    pred = predicted_modal_amplitudes(modal.phi, modal.mass_matrix, modal.f_damped_Hz)
    params = load_params(level=LEVEL)
    summary = {
        "meta": {
            "generated": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": "S4 branch A (chrono_build_plan.md S4): V7 six modes (projection + ERA), "
            "beta sensitivity, leg damping sensitivity, optional rod-side k_v",
            "script": "04_scripts/02_chrono/run_S4.py", "checks_module": "outrigger_sim.verify.s4",
            "judgement": "dyn final ruling: pass (dynamics_model.md rev. 19, 5.8; independent "
            "check 06_analysis/00_dynamics/s4_check.json); this file applies that judgement "
            "specification to the stored runs",
            "dt_yaml_s": float(params.simulation.L1.dt_s),
            "era": {"order": ERA_ORDER, "order_check": ERA_ORDER_CHECK,
                    "block_rows": ERA_BLOCK_ROWS, "decimate": ERA_DECIMATE,
                    "sample_s": SAMPLE_S * ERA_DECIMATE,
                    "channels": "q (surge, sway, heave, roll, pitch, yaw) of the reference point, "
                    "weighted by sqrt(diag M) for the SVD",
                    "mode_selection": "largest start amplitude in eta_i within f_ref +-15 % "
                    "(nominal Phi as the label, also for beta)"},
            "mode_assignment": {f"mode {i + 1}": e for i, e in enumerate(assignment)},
            "predicted_start_amplitude_sqrtkg_m": pred,
            "v7_reference": modal.keys,
            "batches": batches,
            "raw": {cid: r["_dir"] for cid, r in res.items()},
        },
        "verdict_by_check": by_id,
        "all_passed": all(by_id.values()),
        "v7": {"judged": judged, "checks": v7_checks,
               "cross_runs_f_proj": _spread(nominal, "f_proj_Hz"),
               "cross_runs_zeta_proj": _spread(nominal, "zeta_proj"),
               "all_runs": nominal},
        "beta": beta_out,
        "damping": damping,
        "rodside": rodside,
        "health_checks_failed": [c for c in health if not c["passed"]],
        "info_checks": info,
        "info_checks_failed": [c for c in info if not c["passed"]],
        "case_overview": {
            cid: {"dt_s": r.get("dt_s"), "wall_s": (r.get("timing") or {}).get("run_wall_s",
                                                                              (r.get("timing") or {}).get("wall_s")),
                  "yield_steps": r.get("yield_steps") or (r.get("extremes") or {}).get("yield_steps"),
                  "pre_excitation_residual": r.get("pre_excitation_residual"),
                  "pad_normal_min_N": (r.get("extremes") or {}).get("pad_normal_min_N"),
                  "bushing_disp_max_mm": (r.get("extremes") or {}).get("bushing_disp_max_mm")}
            for cid, r in res.items()},
    }
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    import csv

    with BETA_TABLE.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["beta", "id", "item", "chrono", "reference", "tol", "tol_kind", "unit",
                     "passed"])
        for row in csv_rows:
            wr.writerow([json.dumps(_plain(x)) if isinstance(x, (list, tuple)) else x
                         for x in row])
    print(f"wrote {_rel(SUMMARY)}, {_rel(BETA_TABLE)}")
    _figures(res, judged, beta_out, modal)
    print(json.dumps(by_id, indent=1))


def _figures(res, judged, beta_out, modal):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 3, figsize=(15, 7.6))
    for i, ax in enumerate(axes.flat):
        row = judged[i] if i < len(judged) else None
        if row is None or f"modes_{row['run']}" not in res:
            ax.set_visible(False)
            continue
        d = np.load(ROOT / res[f"modes_{row['run']}"]["_dir"] / "series.npz")
        t, eta = d["t"], d["eta"][:, i]
        mask = t <= row["fit_window_s"] + 1e-9
        ax.plot(t[mask], eta[mask] * 1e3, color="#444444", lw=0.6, label="Chrono eta")
        if row.get("amplitude") is not None:
            tt = t[mask] - t[mask][0]
            env = row["amplitude"] * np.exp(-row["sigma_1_s"] * tt)
            ax.plot(t[mask], env * 1e3, color="#d62728", lw=1, label="fit envelope")
            ax.plot(t[mask], -env * 1e3, color="#d62728", lw=1)
        era = row.get("era") or {}
        ax.set_title(f"mode {i + 1} ({row['run']} run): f_n {row.get('f_proj_Hz', 0):.4f} Hz "
                     f"(ref {row['f_ref_Hz']:.4f}), zeta {row.get('zeta_proj', 0):.5f} "
                     f"(ref {row['zeta_ref']:.5f})\nERA {era.get('f_Hz', 0):.4f} Hz / "
                     f"{era.get('zeta', 0):.5f}, leakage {era.get('leakage', 0):.3f}", fontsize=8)
        ax.set_xlabel("time since excitation [s]")
        ax.set_ylabel("modal coordinate eta [1e-3 sqrt(kg) m]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=110)
    plt.close(fig)

    betas = [b for b in beta_out if beta_out[b]["chrono"].get("f_era_Hz")]
    if not betas:
        return
    bval = np.array([float(b.removeprefix("beta_")) for b in betas]) / 1e9
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    colors = plt.cm.tab10(np.arange(6))
    for i in range(6):
        ref = [beta_out[b]["reference"]["f_Hz_top_ball_centre_rev13"][i] for b in betas]
        got = [beta_out[b]["chrono"]["f_era_Hz"][i] for b in betas]
        axes[0].plot(bval, ref, "--", color=colors[i], lw=1)
        axes[0].plot(bval, got, "o", color=colors[i], label=f"mode {i + 1}")
    axes[0].set_xlabel("oil bulk modulus beta_eff [GPa]")
    axes[0].set_ylabel("natural frequency [Hz]")
    axes[0].set_title("ERA (dots) vs reference (dashed)", fontsize=9)
    axes[0].legend(fontsize=7, ncol=2)
    axes[0].grid(alpha=0.3)
    for j, (key, rkey, label, unit) in enumerate((
            ("penetration_mm", "penetration_mm", "pad penetration (FL)", "mm"),
            ("F_min_mm", "FL+_F_min_mm", "FL+ travel at F_min / lift-off", "mm"))):
        ax = axes[j + 1]
        if key == "penetration_mm":
            for leg in range(4):
                got = [beta_out[b]["chrono"].get(key, [np.nan] * 4)[leg] for b in betas]
                ref = [beta_out[b]["reference"][rkey][leg] for b in betas]
                ax.plot(bval, ref, "--", color=colors[leg], lw=1)
                ax.plot(bval, got, "o", color=colors[leg], label=LEGS[leg])
            ax.set_title("pad penetration: Chrono (dots) vs reference (dashed)", fontsize=9)
        else:
            for k2, r2, c in (("F_min_mm", "FL+_F_min_mm", colors[0]),
                              ("liftoff_mm", "FL+_liftoff_mm", colors[1])):
                got = [beta_out[b]["chrono"].get(k2) or np.nan for b in betas]
                ref = [beta_out[b]["reference"][r2] for b in betas]
                ax.plot(bval, ref, "--", color=c, lw=1)
                ax.plot(bval, got, "o", color=c, label=k2)
            ax.set_title(label + ": Chrono (dots) vs reference (dashed)", fontsize=9)
        ax.set_xlabel("oil bulk modulus beta_eff [GPa]")
        ax.set_ylabel(f"[{unit}]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(BETA_FIGURE, dpi=110)
    plt.close(fig)
    print(f"wrote {_rel(FIGURE)}, {_rel(BETA_FIGURE)}")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("modes", "beta", "damping", "rodside", "all", "run",
                                       "summary", "list"))
    ap.add_argument("--jobs", type=int, default=MAX_WORKERS)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    if args.action == "list":
        print("\n".join(case_ids()))
        return
    if args.action == "summary":
        summarize()
        return
    if args.action == "run":
        ids = args.only or []
    elif args.action == "all":
        ids = case_ids()
    else:
        ids = group_ids(args.action)
    for c in ids:
        case_settings(c)
    run_batch(ids, args.jobs)
    summarize()


if __name__ == "__main__":
    main(sys.argv[1:])
