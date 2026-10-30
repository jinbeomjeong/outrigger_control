"""Feasibility smoke for spec 426 (control-expert 2026-10-30), scratch only, project files read only.

Moved 2026-10-30 unchanged from session scratchpad ctrl-426/smoke_soil_offsets.py (paths are arguments).

Mode "event": J2 (or given soil) flat top pad B F_s 4, project preset; run to READY + 5 s, deepcopy, then
  branch a: soil reference surface under the event pad lowered (SoilPads.h -= depth * poly345)
  branch b: SCM sinkage offset (z, sp of the event pad += depth * poly345, sy kept)
  branch n: no event
  each 15 s; per period: event-leg min true F_cyl, min pad contact, crawler max, phase.
Mode "bump": same soil, one pad surface raised so the zero-stroke pad gap after the settle is g_start
  (SoilPads.h += gap_target - g_start, before the settle: pads airborne, settle unchanged); closed loop
  via s9 run_case with the project preset controller.
Usage: python -I smoke_soil_offsets.py <root> <mode> <soil> <out_json> [leg] [depth_or_gstart_mm] [ramp_s]
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
import numpy as np  # noqa: E402
import s9_soil_closed_loop as sl  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")


def preset_controller(cl, c2, variant=None):
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    ctrl.reset()
    return ctrl


def poly345(tau):
    tau = min(1.0, max(0.0, tau))
    return tau ** 3 * (10 - 15 * tau + 6 * tau ** 2)


_EVENT = {}
_ORIG_SOIL_FLOOR = sl.soil_floor


def soil_floor_event(cl, plant):
    ev = _EVENT.get("ev")
    if ev is not None:
        i, depth, ramp, t0, mode = ev
        f = depth * poly345((plant.t - t0) / ramp)
        df = f - _EVENT["applied"]
        _EVENT["applied"] = f
        so = plant.soil
        if mode == "a":
            so.h[i] -= df
        elif mode == "b":
            so.z[i] += df
            so.sp[i] += df
    _ORIG_SOIL_FLOOR(cl, plant)
    c = np.asarray(plant.acc[11:15], float) if getattr(plant, "acc", None) is not None else None
    if c is not None:
        _EVENT["cmin"] = np.minimum(_EVENT.get("cmin", np.full(4, np.inf)), c)


def run_periods(cl, Meas, plant, ctrl, cmd, valve, ha, t_end, log=None):
    rec = {}
    while plant.t < t_end - 1e-9:
        _EVENT["cmin"] = np.full(4, np.inf)
        m = sl.control_period(cl, Meas, plant, cmd, valve, ha, ctrl.period_s, rec)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if log is not None:
            log.append([round(plant.t, 2), *np.round(rec["fmin"] / 1e3, 2), *np.round(_EVENT["cmin"] / 1e3, 2),
                        round(rec["crmax"] / 1e3, 2), str(ctrl.phase),
                        *(np.round(plant.soil.z * 1e3, 2) if plant.soil is not None else [0] * 4)])
    return cmd


def event_mode(soil, out, leg, depth_mm, ramp_s):
    sl.soil_floor = soil_floor_event
    cl, c2, Meas = sl._imports()
    cl.rmf.CONFIG.clear(); cl.rpt.RCFG.clear()
    plant = sl.make_plant(cl, "top", soil, "B", 4.0, settle_hook="harness" if soil != "rigid" else None)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    ctrl = preset_controller(cl, c2)
    ha = ctrl.geometry.head_area_m2
    cmd, valve = np.zeros(4), np.zeros(4)
    rec = {}
    t_ready = None
    t0 = time.perf_counter()
    while plant.t < 240.0:
        m = sl.control_period(cl, Meas, plant, cmd, valve, ha, ctrl.period_s, rec)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        if str(ctrl.phase) == "ready" and t_ready is None:
            t_ready = plant.t
        if t_ready is not None and plant.t >= t_ready + 5.0 - 1e-9:
            break
        if str(ctrl.phase) == "fault":
            break
    res = {"soil": soil, "t_ready": t_ready, "base_wall_s": round(time.perf_counter() - t0, 1), "branches": {}}
    if t_ready is None:
        json.dump(res, open(out, "w"), indent=1)
        return
    i = LEGS.index(leg)
    for mode in ("n", "a", "b"):
        pl, ct = copy.deepcopy(plant), copy.deepcopy(ctrl)
        n0 = len(ct.events)
        _EVENT.clear(); _EVENT["applied"] = 0.0
        _EVENT["ev"] = None if mode == "n" or soil == "rigid" and mode == "b" else (i, depth_mm * 1e-3, ramp_s,
                                                                                     pl.t, mode)
        if soil == "rigid" and mode == "a":
            _EVENT["ev"] = None
            # rigid analogue: goff (as r67 / b5)
            t_ev = pl.t

            def rigid_floor(cl_, plant_, _orig=_ORIG_SOIL_FLOOR):
                plant_.goff[i] = depth_mm * 1e-3 * poly345((plant_.t - t_ev) / ramp_s)
                _orig(cl_, plant_)
            sl.soil_floor = rigid_floor
        log = []
        tb = time.perf_counter()
        z0 = None if pl.soil is None else (pl.soil.z * 1e3).round(2).tolist()
        run_periods(cl, Meas, pl, ct, cmd.copy(), valve.copy(), ha, pl.t + 15.0, log)
        sl.soil_floor = soil_floor_event
        arr = np.array([r[1:10] for r in log], float)
        res["branches"][mode] = {
            "wall_s": round(time.perf_counter() - tb, 1),
            "event_leg_min_Fcyl_kN": float(arr[:, 1 + i - 1 + 0].min()) if False else float(arr[:, i].min()),
            "min_Fcyl_all_kN": arr[:, 0:4].min(axis=0).round(2).tolist(),
            "min_contact_kN": arr[:, 4:8].min(axis=0).round(2).tolist(),
            "periods_event_leg_contact_le0": int(np.sum(arr[:, 4 + i] <= 0.0)),
            "crawler_max_kN": float(arr[:, 8].max()),
            "phases": sorted({r[10] for r in log}),
            "final_phase": log[-1][10],
            "z_start_mm": z0, "z_end_mm": log[-1][11:15],
            "events": [f"{e.t_s - plant.t:.1f} {e.name}" for e in ct.events[n0:]][:30],
        }
    json.dump(res, open(out, "w"), indent=1, default=float)


def bump_mode(soil, out, leg, g_start_mm):
    cl, c2, Meas = sl._imports()
    i = LEGS.index(leg)
    orig_make = sl.make_plant
    info = {}

    def make_plant_bump(cl_, level, soil_, pad, fs, *a, **k):
        plant = orig_make(cl_, level, soil_, pad, fs, *a, **k)
        row = plant.soil.settle_row
        g0 = float(row["gap_target_mm"][i]) * 1e-3
        dh = g0 - g_start_mm * 1e-3
        plant.soil.h[i] += dh
        plant.goff[:] = -plant.soil.h
        info.update(g0_mm=g0 * 1e3, dh_mm=dh * 1e3)
        return plant

    sl.make_plant = make_plant_bump
    sl.make_controller = preset_controller
    case = {"id": f"bump|{soil}|{leg}|g{g_start_mm:g}", "soil": soil, "pad": "B", "level": "top", "fs_kN": 4.0,
            "settle_hook": "harness", "variant": {}}
    r = sl.run_case(case)
    r.update(info)
    r.pop("events", None)
    keep = {k: r.get(k) for k in ("id", "g0_mm", "dh_mm", "settle", "t_ready_s", "final_phase", "crawler_N_at_ready",
                                  "min_true_Fcyl_after_off_kN", "att_end_deg", "max_motor_stroke_mm",
                                  "clear_true_ready_mm", "clear_est_ready_mm", "sink_final_mm", "n_reapproach",
                                  "n_warn", "phase_path", "commands_sha256", "wall_s", "n_crawler_recontact")}
    json.dump(keep, open(out, "w"), indent=1, default=float)


if __name__ == "__main__":
    mode, soil, out = sys.argv[2], sys.argv[3], sys.argv[4]
    leg = sys.argv[5] if len(sys.argv) > 5 else "RR"
    val = float(sys.argv[6]) if len(sys.argv) > 6 else 11.5
    ramp = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
    if mode == "event":
        event_mode(soil, out, leg, val, ramp)
    else:
        bump_mode(soil, out, leg, val)
