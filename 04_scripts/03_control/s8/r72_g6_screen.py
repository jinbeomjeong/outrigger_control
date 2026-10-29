"""Spec rev. 72 draft (coverage gap G6): reduced closed-loop screen of a weak soil patch under ONE pad on the S9 soil
harness, project C2 R8 preset as it is (soil response on, P-S8-28 on).

Harness: ``04_scripts/03_control/s9/s9_soil_closed_loop.py`` (imported, not copied): reduced 6-DoF FlexPlant, L1-R
rod-side law, Coulomb seal friction, valve lag 0.1 s, IMU 10 ms, one Chrono-type SCM element per pad (implicit, 1 ms),
crawler on a floor tilted by the P0 settle of the BASE soil. Extension here (wrapper, the s9 file is unchanged):
  * ``SoilPadsPerLeg``: the Bekker / elastic / damping constants per pad (n, K, R as arrays); the pad-surface heights
    h_i and the crawler floor tilt come from the BASE soil (the weak patch is under the pad only, same ground level);
  * ``soil_floor_per_leg``: the s9 ``soil_floor`` with per-pad n, K, R (a numba chunk with arrays). With four equal
    sets it runs the same arithmetic as the s9 path (check: the uniform refs give the s9 command SHA-256);
  * the controller factory returns the project preset ``preset_config(COMBINED)`` (= s9_project_check "preset").
Case soil string: "<base>" (uniform) or "<base>+<weak>@<leg>". Pad type B (dwg_rear250, project default).

Grid: weak J1 / J2 / S1 under FL / FR / RL / RR, base G1, auger top / bottom, F_s 0 / 4 kN (front value, rear 0.833 x)
  = 48; refs: uniform G1, J1, J2, S1 x top / bottom x F_s 0 / 4 = 16. Total 64.
Judgement rows per run (spec 284 P3 rows, rev. 60 corrections, harness form):
  G6-1 (P3-1) crawler load 0 from READY to the run end (READY + 10 s) and (spec 420.2b, U-S9-G6d (가)) no
       ``strict_fail`` recontact after the departure confirmation (``run_S9.recontact_events`` on the 1 ms crawler
       force); a ``transient_flag`` recontact is the FLAG ``P3-1_transient_recontact`` (record ``crawler_recontact``)
  G6-2 (P3-2) LOC before the first DONE and t_LOC - t_off <= 2.9 s (t_off = first crawler-free control period);
       spec 419.8: a delay from the LWa window restart is a FLAG (``G6-2_late_loc_reapproach``, five conditions of
       ``s9/late_loc_rule.py``; record ``late_loc_reapproach``); spec 424.8.1 / 424.9: with a LOC revocation
       (wrapper ``FIX_LOC_REVOKE``) the judged LOC is t_LOC^fin and a delay from the revocations is the FLAG
       ``G6-2_late_loc_revoked`` (six conditions of ``late_loc_rule.late_loc_revoked``, T_lim 2.9 s; records
       ``late_loc_revoked``, ``t_loc_first_s``, ``t_loc_final_s``, ``loc_revokes`` only then). G6-1, G6-7 and the
       pre-LOC records use the same judged LOC
  G6-3 (P3-3) min true F_cyl after the crawler lift-off >= F_min (record: >= F_min + 5 kN)
  G6-4 (P3-4) final attitude |roll|, |pitch| <= 0.2 deg (run end = READY + 10 s; creep state recorded)
  G6-5 (P3-5) rut clearance (crawler nodes in the rut at the settle) at READY and at the end >= 25 mm; motor stroke
       run maximum (10 Hz) <= 684.8 mm
  G6-6 FAULT 0 and READY reached
  G6-7 (P3-8) no re-approach start, probe abort before the LOC
Records: LOC time, t_P, c_min(t_P), anchor applied (INFO_LOC_CLEARANCE_ANCHOR) and bias, guard events, weak-pad
  re-approaches / re-levels, sink per pad (final, max rate), READY time (P3-6 <= 90 s), D8 margin, controller
  clearance estimate at the end, commands SHA-256.

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r72_g6_screen.py <project_root> <out_json> [workers]
  python -I r72_g6_screen.py <project_root> --list
Env: R72_FILTER (substrings), R72_AFFINITY (hex mask on the parent),
  R72_SET = main | ref | all (default all; G1 base, 64) | rigid (48) | rigidref (4) | rigid_all (52),
  R72_PATH = per_leg (default) | s9 (original s9 path, uniform only) | per_leg_force (mixed kernel also for uniform
  rigid: identity check).
  S9_SETTLE_HOOK = p0 (default, results up to rev. 79) | harness (dynamics hook_harness row of the BASE soil:
  floor tilt and pad heights; S9_SETTLE_TABLE overrides the table path). Rigid-base (MixedRigidPads) cases are
  unchanged by the hook (rigid floor, h = 0). The hook and the settle snapshot are recorded per result.
Rigid base (user decision 2026-10-27, ``MixedRigidPads``): soil string "rigid+<weak>@<leg>"; the three rigid legs keep
  the harness rigid pad spring and floor offset 0 every chunk, the weak leg is one soil element on the flat floor
  (surface at the floor level), crawler on the rigid floor.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
for _p in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numba as nb  # noqa: E402
import numpy as np  # noqa: E402

import late_loc_rule  # noqa: E402
import s9_soil_closed_loop as sl  # noqa: E402

LEGS = sl.LEGS
BASE = "G1"
WEAK = ("J1", "J2", "S1")
LEVELS = ("top", "bottom")
FS_KN = (0.0, 4.0)
STROKE_OK_MM = 684.8
LOC_DELAY_MAX_S = 2.9
RUT_MIN_MM = 25.0
COUNTED_INFO_EVENTS = ("INFO_TOUCH_DIP_HELD", "INFO_LIFT_PAUSED", "INFO_CLEARANCE_BIAS", "INFO_LOC_CLEARANCE_ANCHOR",
                       "INFO_TWIST_UNSETTLED")
"""Events counted per result (events_head keeps only the first 40)."""
_CAP = {}


# --------------------------------------------------------------------------------------------- per-pad soil
@nb.njit(cache=True)
def soil_chunk_per_leg(pen, z, sp, sy, area, coef, n, K, R, ks, h, force):
    """s9 ``soil_chunk`` with per-pad n, K, R (arrays)."""
    for i in range(4):
        zp = z[i]
        lo = min(sp[i], zp) - 1e-6
        hi = max(pen[i], zp, sp[i]) + 1e-3
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            fp = ks[i] * max(pen[i] - mid, 0.0)
            g = fp - area[i] * (sl._sigma_s(mid, sp[i], sy[i], coef[i], n[i], K[i]) + R[i] * (mid - zp) / h)
            if g > 0.0:
                lo = mid
            else:
                hi = mid
        zn = 0.5 * (lo + hi)
        zy = sp[i] + sy[i] / K[i]
        if zn > zy and zn > sp[i]:
            s_new = coef[i] * max(zn, 0.0) ** n[i]
            sy[i] = s_new
            sp[i] = zn - s_new / K[i]
        z[i] = zn
        force[i] = ks[i] * max(pen[i] - zn, 0.0)


class SoilPadsPerLeg(sl.SoilPads):
    """Geometry (h_i, crawler tilt) of the base set; Bekker constants per pad."""

    def __init__(self, base, leg_keys, pad_type, pad_xy, ks, k_scale=1.0, settle_row=None):
        super().__init__(base, pad_type, pad_xy, ks, k_scale, settle_row=settle_row)
        legs = next(v for v in sl.PAD_VARIANTS.values() if v["label"] == pad_type)["legs"]
        b = np.array([legs[nm]["bekker_b_m"] for nm in LEGS], float)
        self.leg_keys = tuple(leg_keys)
        self.n_arr = np.empty(4)
        self.K_arr = np.empty(4)
        self.R_arr = np.empty(4)
        for i, key in enumerate(leg_keys):
            s = sl.SOIL_SETS[key]["chrono"]
            self.coef[i] = (s["Kc"] / b[i] + s["Kphi"]) * k_scale
            self.n_arr[i] = float(s["n"])
            self.K_arr[i] = float(max(s["elastic_K"], s["Kphi"] * k_scale))
            self.R_arr[i] = float(s["damping_R"])


class MixedRigidPads(SoilPadsPerLeg):
    """Rigid base (user decision 2026-10-27): rigid legs keep the harness rigid pad spring (``ks_rigid``, concrete
    slab included) and floor offset 0; the weak leg is one soil element (k_s = series(k_rod, k_frame) as the s9 soil
    plant). Crawler on the flat rigid floor; the weak patch surface is at the floor level (h = 0)."""

    def __init__(self, leg_keys, pad_type, pad_xy, ks_soil, ks_rigid, k_scale=1.0):
        weak = next((k for k in leg_keys if k != "rigid"), "J1")
        super().__init__(weak, [weak if k == "rigid" else k for k in leg_keys], pad_type, pad_xy, ks_soil, k_scale)
        self.rigid_mask = np.array([k == "rigid" for k in leg_keys])
        self.ks_rigid = np.asarray(ks_rigid, float).copy()
        self.dtheta = 0.0
        self.h = np.zeros(4)


def soil_floor_per_leg(cl, plant):
    """s9 ``soil_floor`` with per-pad n, K, R (and, for ``MixedRigidPads``, rigid legs held at the rigid spring)."""
    so = plant.soil
    if so is None:
        return
    if not hasattr(so, "n_arr"):
        return _ORIG_SOIL_FLOOR(cl, plant)
    R = cl.rcc._R(plant.q)
    ez = R[:, 2]
    a_n = float(plant.nrm @ ez)
    pen = np.empty(4)
    for i in range(4):
        p0 = plant.r + R @ plant.pad_rel[i]
        g0 = float(plant.nrm @ p0) / a_n
        pen[i] = (plant.x[i] - g0) * a_n + so.h[i]
    f_kernel = plant.ks * np.maximum(pen - (plant.goff + so.h), 0.0)
    z_old = so.z.copy()
    soil_chunk_per_leg(pen, so.z, so.sp, so.sy, so.area, so.coef, so.n_arr, so.K_arr, so.R_arr, so.ks, 1e-3,
                       so.force)
    rigid = getattr(so, "rigid_mask", None)
    if rigid is not None:
        so.z[rigid] = 0.0
        so.sp[rigid] = 0.0
        so.sy[rigid] = 0.0
        so.force[rigid] = 0.0
        f_kernel[rigid] = 0.0
    so.max_force_mismatch = max(getattr(so, "max_force_mismatch", 0.0), float(np.max(np.abs(f_kernel - so.force))))
    so.z_max_rate = np.maximum(so.z_max_rate, (so.z - z_old) / 1e-3)
    ks_eff = np.empty(4)
    z0 = np.empty(4)
    for i in range(4):
        if so.force[i] > 0.0:
            kt = so.area[i] * (sl.soil_tangent(so.z[i], so.sp[i], so.sy[i], so.coef[i], so.n_arr[i], so.K_arr[i])
                               + so.R_arr[i] / 1e-3)
            ks_eff[i] = so.ks[i] * kt / (so.ks[i] + kt)
            z0[i] = pen[i] - so.force[i] / ks_eff[i]
        else:
            kt = so.area[i] * (so.K_arr[i] + so.R_arr[i] / 1e-3)
            ks_eff[i] = so.ks[i] * kt / (so.ks[i] + kt)
            z0[i] = so.z[i]
    if rigid is not None:
        ks_eff[rigid] = so.ks_rigid[rigid]
        z0[rigid] = so.h[rigid]
    plant.ks = ks_eff
    plant.goff[:] = z0 - so.h


def parse_soil(soil):
    """'G1' -> ('G1', ['G1'] * 4); 'G1+J1@FL' -> ('G1', ['J1', 'G1', 'G1', 'G1'])."""
    if "+" not in soil:
        return soil, [soil] * 4
    base, rest = soil.split("+")
    weak, leg = rest.split("@")
    keys = [base] * 4
    keys[LEGS.index(leg)] = weak
    return base, keys


def make_plant_per_leg(cl, level, soil, pad_type, fs_kN, beta=1.0e9, soil_kscale=1.0, slope=(0.0, 0.0),
                       **settle_options):
    """s9 ``make_plant`` of the base soil plus the per-pad soil; ``settle_options`` (settle_hook, settle_table,
    settle_row) go to the s9 factory, the per-pad pads keep its settle row (the weak patch is under the pad only)."""
    import dyn_model as dm
    base, keys = parse_soil(soil)
    plant = _ORIG_MAKE_PLANT(cl, level, base, pad_type, fs_kN, beta, soil_kscale, slope, **settle_options)
    path = os.environ.get("R72_PATH", "per_leg")
    if base == "rigid" and (any(k != "rigid" for k in keys) or path == "per_leg_force"):
        # mixed kernel; "per_leg_force" builds it for uniform rigid too (identity check against the s9 rigid path)
        pad_xy = dm.geometry_from_params(dm.load_params()).pad_xy
        ks_soil = np.broadcast_to(np.asarray(dm.series(dm.k_rod(), dm.ASSUMPTIONS["frame_bracket_stiffness_N_m"]),
                                             float), (4,)).copy()
        ks_rigid = np.asarray(plant.ks, float).copy()
        plant.soil = MixedRigidPads(keys, pad_type, pad_xy, ks_soil, ks_rigid, soil_kscale)
        plant.ks = np.where(plant.soil.rigid_mask, ks_rigid, ks_soil)
        plant.goff[:] = 0.0
    elif base != "rigid" and path in ("per_leg", "per_leg_force"):
        pad_xy = dm.geometry_from_params(dm.load_params()).pad_xy
        plant.soil = SoilPadsPerLeg(base, keys, pad_type, pad_xy, plant.ks.copy(), soil_kscale,
                                    settle_row=plant.soil.settle_row)
        plant.goff[:] = -plant.soil.h
    _CAP["plant"] = plant
    return plant


def make_controller_preset(cl, c2, variant):
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    ctrl.reset()
    _CAP["ctrl"] = ctrl
    # run_case builds the controller right after the settle node heights (same plant state)
    if "plant" in _CAP:
        _CAP["node_d0"] = sl.crawler_node_heights(cl, _CAP["plant"])
    return ctrl


_ORIG_SOIL_FLOOR = sl.soil_floor
_ORIG_MAKE_PLANT = sl.make_plant


def control_period_logged(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens=None):
    """s9 ``control_period`` plus a per-period record of the true leg force minimum (logging only)."""
    m = _ORIG_CONTROL_PERIOD(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens)
    _CAP.setdefault("fmin_log", []).append((float(plant.t), np.asarray(rec["fmin"], float).copy()))
    return m


_ORIG_CONTROL_PERIOD = sl.control_period


def _install():
    sl.soil_floor = soil_floor_per_leg
    sl.make_plant = make_plant_per_leg
    sl.make_controller = make_controller_preset
    sl.control_period = control_period_logged
    late_loc_rule.install_crawler_recorder(sl._imports()[0], lambda: _CAP.get("crawler_series"))


# --------------------------------------------------------------------------------------------- one case
def _late_loc_record(ctrl, plant, t_off, t_loc, t_done, min_off_kN, f_min_kN, out,
                     t_revoke_last=None) -> dict:
    """Spec 419.8 / 419.8.1 record of the run (G6-2 FLAG ``G6-2_late_loc_reapproach``): the
    cad ``run_S9.p32_late_loc_block`` on the 1 ms crawler force, t_off of ``loc_delay_s``.
    With a LOC revocation (spec 424.8.1) ``t_loc`` is t_LOC^fin and ``t_revoke_last`` the last
    revocation; without one the call is the former one."""
    events = [(float(e.t_s), e.name) for e in ctrl.events]
    phases = [tuple(entry) for entry in out.get("phase_path") or []]
    if out.get("final_phase") is not None:  # the stored path is cut at 60 entries
        phases.append((float(plant.t) if plant is not None else math.inf, out["final_phase"]))
    weight_N = None if plant is None else float(plant.m * plant.g)
    return late_loc_rule.late_loc_reapproach(
        events, phases, _CAP.get("crawler_series") or [], weight_N, t_off_s=t_off, t_loc_s=t_loc,
        t_done_s=t_done, min_force_after_off_kN=min_off_kN, f_min_kN=f_min_kN,
        t_revoke_last_s=t_revoke_last)


def _has_fault(ctrl, out) -> bool:
    return (out.get("final_phase") in ("fault", "fault_reground")
            or any(e.name.startswith("FAULT") for e in ctrl.events))


def _late_loc_revoked_record(ctrl, plant, timeline, late_loc, t_off, t_done, min_off_kN, f_min_kN,
                             out) -> dict:
    """Spec 424.8.1 / 424.9 record (G6-2 FLAG ``G6-2_late_loc_revoked``, six conditions of
    ``late_loc_rule.late_loc_revoked``, T_lim 2.9 s) at t_LOC^fin; runs with a revocation only."""
    t_loc = timeline["t_loc_final_s"]
    conditions = late_loc.get("conditions") or {}
    return late_loc_rule.late_loc_revoked(
        t_off_s=t_off, t_loc_final_s=t_loc, t_done_s=t_done,
        revoke_times_s=timeline["revoke_times_s"],
        crawler_loc_period_max_N=late_loc_rule.loc_period_crawler_max_N(
            _CAP.get("crawler_series") or [], t_loc),
        weight_N=None if plant is None else float(plant.m * plant.g),
        min_force_after_off_kN=min_off_kN, f_min_kN=f_min_kN, has_fault=_has_fault(ctrl, out),
        reapproach_restart=bool(conditions.get("1_restart")),
        t_reapproach_end_s=late_loc.get("t_reapproach_end_s"), t_lim_s=LOC_DELAY_MAX_S)


def job(key):
    """key = '<set>|<soil string>|<level>|Fs<f>'."""
    _install()
    _CAP.clear()
    _CAP["crawler_series"] = []  # 1 ms true crawler force (spec 419.8 condition 3, record only)
    tag, soil, level, fs = key.split("|")
    case = {"id": key, "soil": soil, "pad": "B", "level": level, "fs_kN": float(fs[2:]), "variant": {}}
    try:
        out = sl.run_case(case)
    except Exception as exc:  # keep the batch going
        import traceback
        return {"key": key, "error": repr(exc), "tb": traceback.format_exc()[-2000:]}
    ctrl, plant = _CAP.get("ctrl"), _CAP.get("plant")
    cl = sl._imports()[0]
    base, keys = parse_soil(soil)
    weak_leg = next((LEGS[i] for i in range(4) if keys[i] != base), None)
    names = [e.name for e in ctrl.events]
    t_ev = {}
    for e in ctrl.events:
        t_ev.setdefault(e.name.split(":")[0], e.t_s)
    soil_state = ctrl._soil_state()
    # spec 424.8.1: the judged LOC is t_LOC^fin (the first LOC event without a revocation)
    timeline = late_loc_rule.loc_timeline([(float(e.t_s), e.name) for e in ctrl.events])
    has_revoke = bool(timeline["revoke_times_s"])
    t_loc = timeline["t_loc_final_s"] if has_revoke else t_ev.get("crawler_liftoff_confirmed")
    t_done = out.get("t_done_s")
    t_off = out.get("t_crawler_off_first_s")
    pre_loc = [n for e, n in ((e, e.name) for e in ctrl.events)
               if (t_loc is None or e.t_s < t_loc) and n.startswith(("leg_reapproach_start", "probe_aborted"))]
    F_min = ctrl.geometry.F_min_N / 1e3
    rut_end = None
    clear_est_end = None
    if plant is not None:
        # rut clearance at the end with the run_case definition (nodes in the rut at the settle)
        node_d0 = _CAP.get("node_d0")
        if node_d0 is not None and np.any(node_d0 < 0.0):
            d = sl.crawler_node_heights(cl, plant)
            rut_end = float(np.min((d - node_d0)[node_d0 < 0.0])) * 1e3
        clear_est_end = float(ctrl._clearance_estimate_m(np.asarray(plant.x, float))) * 1e3
    att_end = out.get("att_end_deg") or [math.nan, math.nan]
    min_off = out.get("min_true_Fcyl_after_off_kN")
    # spec 420.2b (U-S9-G6d (가)): recontacts after the departure confirmation by the run_S9 classes
    weight_N = None if plant is None else float(plant.m * plant.g)
    # spec 423.3 (Q-G): + threshold chatter just after the LOC (FLAG P3-1_threshold_chatter)
    recontact = late_loc_rule.crawler_recontact_record(_CAP.get("crawler_series"), weight_N, t_loc,
                                                       out.get("t_ready_s"))
    is_crawler_ok, crawler_flags = late_loc_rule.crawler_gate(
        out.get("crawler_N_max_after_ready") == 0.0, recontact, out.get("n_crawler_recontact", 1))
    g = {
        "G6-1_crawler": is_crawler_ok,
        "G6-2_loc": bool(t_loc is not None and (t_done is None or t_loc <= t_done + 1e-9) and t_off is not None
                         and t_loc - t_off <= LOC_DELAY_MAX_S + 1e-9),
        "G6-3_Fmin": bool(min_off is not None and min_off >= F_min),
        "G6-4_att": bool(np.all(np.abs(att_end) <= 0.2)),
        "G6-5_rut_stroke": bool((out.get("clear_true_ready_mm") or -1) >= RUT_MIN_MM
                                and (rut_end is None or rut_end >= RUT_MIN_MM)
                                and out.get("max_motor_stroke_mm", 1e9) <= STROKE_OK_MM),
        # P3 rows do not ask the run to END in READY (a creep re-level after READY is allowed); FAULT never
        "G6-6_fault_ready": bool(out.get("final_phase") not in ("fault", "fault_reground")
                                 and out.get("t_ready_s") is not None),
        "G6-7_preloc": not pre_loc,
    }
    late_loc = _late_loc_record(ctrl, plant, t_off, t_loc, t_done, min_off, F_min, out,
                                timeline["t_revoke_last_s"])
    flags = list(crawler_flags)
    is_raw_g62 = g["G6-2_loc"]
    if not is_raw_g62 and late_loc["is_flag"]:
        g["G6-2_loc"] = True  # spec 419.8: the LWa-delayed LOC is a FLAG, not a failure
        flags.append(late_loc_rule.G62_FLAG)
    revoked = None
    if has_revoke:  # spec 424.8.1 / 424.9: a LOC delayed by revocations is a FLAG (both recorded)
        revoked = _late_loc_revoked_record(ctrl, plant, timeline, late_loc, t_off, t_done, min_off,
                                           F_min, out)
        if not is_raw_g62 and revoked["is_flag"]:
            g["G6-2_loc"] = True
            flags.append(late_loc_rule.G62_REVOKED_FLAG)
    # decision 2 (2026-10-27): a pre-LOC re-approach is demoted to a FLAG when the started leg's true minimum from
    # the start to LOC + 1 s stays >= F_min (no lift) and the run has no FAULT
    flog = _CAP.get("fmin_log") or []
    t_end_w = (t_loc if t_loc is not None else (flog[-1][0] if flog else 0.0)) + 1.0
    preloc_starts = []
    for e in ctrl.events:
        if e.name.startswith("leg_reapproach_start") and (t_loc is None or e.t_s < t_loc):
            leg_i = LEGS.index(e.name.split(":")[1])
            vals = [f[leg_i] for t, f in flog if e.t_s - 0.1 - 1e-9 <= t <= t_end_w + 1e-9]
            preloc_starts.append({"t_s": round(float(e.t_s), 2), "leg": LEGS[leg_i],
                                  "true_min_kN": round(float(min(vals)) / 1e3, 2) if vals else None})
    preloc_flag_ok = bool(preloc_starts) and all(
        p["true_min_kN"] is not None and p["true_min_kN"] >= F_min for p in preloc_starts) and \
        out.get("final_phase") not in ("fault", "fault_reground")
    anchor = [n for n in names if n.startswith("INFO_LOC_CLEARANCE_ANCHOR")]
    weak_events = {}
    if weak_leg is not None:
        weak_events = {"reapproach": sum(1 for n in names if n == f"leg_reapproach_start:{weak_leg}"),
                       "relevel": sum(1 for n in names if "relevel" in n and n.endswith(weak_leg))}
    rec = {
        "key": key, "soil": soil, "base": base, "weak_leg": weak_leg, "level": level, "fs_kN": case["fs_kN"],
        "gates": g, "pass": all(g.values()), "flags": flags, "late_loc_reapproach": late_loc,
        "crawler_recontact": recontact,
        "crawler_N_max_after_ready": out.get("crawler_N_max_after_ready"),
        "t_loc_s": t_loc, "t_off_s": t_off, "t_ready_s": out.get("t_ready_s"), "t_done_s": t_done,
        "loc_delay_s": None if t_loc is None or t_off is None else round(t_loc - t_off, 2),
        "t_P_s": getattr(soil_state, "plateau_start_s", None),
        "c_min_tP_mm": None if getattr(soil_state, "clearance_at_plateau_start_m", None) is None
        else round(soil_state.clearance_at_plateau_start_m * 1e3, 1),
        "corner_bias_mm": (np.asarray(soil_state.corner_bias_m) * 1e3).round(1).tolist(),
        "anchor_events": anchor, "anchor_applied": bool(anchor),
        "guard_events": [n for n in names if n.startswith(("WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT",
                                                           "FAULT_STROKE_END", "fault_reground"))],
        "min_true_Fcyl_after_off_kN": min_off,
        "D8_margin_kN": None if min_off is None else round(min_off - F_min - 5.0, 2),
        "att_end_deg": att_end, "att_max_after_off_deg": out.get("att_max_after_off_deg"),
        "rut_clear_ready_mm": out.get("clear_true_ready_mm"), "rut_clear_end_mm": rut_end,
        "clear_est_end_mm": clear_est_end, "max_motor_stroke_mm": out.get("max_motor_stroke_mm"),
        "sink_final_mm": out.get("sink_final_mm"), "sink_rate_max_mm_s": out.get("sink_rate_max_mm_s"),
        "weak_leg_events": weak_events, "n_reapproach": out.get("n_reapproach"), "n_relevel": out.get("n_relevel"),
        "n_warn": out.get("n_warn"), "pre_loc_events": pre_loc[:6], "final_phase": out.get("final_phase"),
        "preloc_starts": preloc_starts, "preloc_flag_ok": preloc_flag_ok,
        "phase_path": out.get("phase_path"),
        "n_probe_rounds": out.get("n_probe_rounds"),
        "events_head": [ev for ev in out.get("events", []) if not ev.split(" ", 1)[1].startswith(
            ("INFO_PRESSURE", "shadow", "INFO_D1"))][:40],
        "commands_sha256": out.get("commands_sha256"), "wall_s": out.get("wall_s"),
        "settle_hook": out.get("settle_hook"), "settle": out.get("settle"),
        "info_counts": {p: sum(1 for n in names if n.split(":")[0] == p) for p in COUNTED_INFO_EVENTS},
        "twist_unsettled_D_kN": [float(n.split(":")[1]) for n in names if n.startswith("INFO_TWIST_UNSETTLED:")],
        "warnings": sorted({n.split(":")[0] for n in names if n.startswith(("WARN", "FAULT"))}),
    }
    if revoked is not None:  # spec 424.8.1 records (only with a revocation: former records unchanged)
        rec.update(late_loc_revoked=revoked, t_loc_first_s=timeline["t_loc_first_s"],
                   t_loc_final_s=t_loc, loc_revokes=timeline["revoke_times_s"])
    return rec


def all_jobs(set_name):
    jobs = []
    if set_name in ("main", "all"):
        for w in WEAK:
            for lg in LEGS:
                for lv in LEVELS:
                    for fs in FS_KN:
                        jobs.append(f"g6|{BASE}+{w}@{lg}|{lv}|Fs{fs:g}")
    if set_name in ("ref", "all"):
        for s in (BASE,) + WEAK:
            for lv in LEVELS:
                for fs in FS_KN:
                    jobs.append(f"ref|{s}|{lv}|Fs{fs:g}")
    if set_name in ("rigid", "rigid_all"):
        for w in WEAK:
            for lg in LEGS:
                for lv in LEVELS:
                    for fs in FS_KN:
                        jobs.append(f"g6r|rigid+{w}@{lg}|{lv}|Fs{fs:g}")
    if set_name in ("rigidref", "rigid_all"):
        for lv in LEVELS:
            for fs in FS_KN:
                jobs.append(f"ref|rigid|{lv}|Fs{fs:g}")
    return jobs


def set_parent_placement():
    mask = os.environ.get("R72_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def main():
    jobs = all_jobs(os.environ.get("R72_SET", "all"))
    filt = os.environ.get("R72_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        for j in jobs:
            print(j)
        return
    set_parent_placement()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        res = pool.map(job, jobs, chunksize=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r72_g6_screen.py",
                                        "spec": "rev. 72 draft (G6 weak patch under one pad)",
                                        "path": os.environ.get("R72_PATH", "per_leg"), "filter": filt,
                                        "settle_hook": sl.resolve_settle_hook(),
                                        "workers": workers, "affinity": os.environ.get("R72_AFFINITY"),
                                        "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)
    for r in res:
        if "error" in r:
            print(r["key"], r["error"])
            continue
        print(r["key"], "pass", r["pass"], {k: v for k, v in r["gates"].items() if not v}, "anchor",
              r["anchor_applied"], "c_min_tP", r["c_min_tP_mm"], "LOCd", r["loc_delay_s"], "ready",
              r["t_ready_s"], "D8m", r["D8_margin_kN"], "att", r["att_end_deg"], "rut", r["rut_clear_ready_mm"],
              r["rut_clear_end_mm"], "stroke", r["max_motor_stroke_mm"], "sink", r["sink_final_mm"], "weak",
              r["weak_leg_events"], "wall", r["wall_s"], r["commands_sha256"][:16])


if __name__ == "__main__":
    main()
