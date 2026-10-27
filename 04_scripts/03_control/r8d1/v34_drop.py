"""Engine-free RE1b-like check: RR floor drop 30 mm / 0.05 s on the reduced plant with the project C2
(R8-D1 preset, 100 Hz IMU path of c2py_r8d1_closed_loop.run_imu_100hz_flat), P-R8-12 variants.

Spec ``00_docs/04_control/s6_control_spec.md`` rev. 34 173.4 / 174 (control-expert harness, moved
from the session scratchpad; results ``06_analysis/02_control/r8_10hz/d1/v34_drop_*.json``).
The harness variants (``cur``, ``tw0.25_s1``, ...) subclass the controller on top of the P-R8-12
leg mode (:meth:`LiftedReapproachSettings.leg_mode`), as they ran before P-R8-13 was in c2.py.
``preset`` is the c2.py P-R8-13 twist mode of ``with_10hz_d1()`` without any override (it should
reproduce ``tw0.25_s1``), ``preset_leg`` the c2.py leg mode alone (it should reproduce ``cur``).
preset_p30off = preset without P-S8-30 (the P-R8-13 reproduction of spec 179.1).

Usage (project root, dynamics-dev for numba, MKL_THREADING_LAYER=TBB):
  python -I 04_scripts/03_control/r8d1/v34_drop.py <out.json> [variant ...]
Environment: V34_MODES (default ``F,P``), V34_LEVEL (default ``top``).
Event modes: F = drop at READY + 3 s; P = drop 0.1 s after the first PROBE entry.
Metrics in the 5 s window after the event (1 ms = 2 plant steps of 5e-4 s are grouped per 1 ms chunk):
FL lift intervals (contact force == 0), max FL pad gap, RR first contact / first contact held >= 1 s,
min / max true cylinder force, max head pressure [bar], max |attitude| deviation, re-READY time.
"""
from __future__ import annotations

import json
import os
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c2py_r8d1_closed_loop as cl  # noqa: E402  (puts 03_src on the path)

from outrigger_sim.control.c2 import (  # noqa: E402
    C2Controller,
    C2Phase,
    ContactJudge,
    LEG_ORDER,
    LiftedReapproachSettings,
)

rmf, rcc = cl.rmf, cl.rcc
_R = rcc._R
DROP_M = 0.03
DROP_S = 0.05
WINDOW_S = 5.0


class Variant(C2Controller):
    """Overrides of the P-R8-12 pieces; flags set per instance before reset()."""

    hold_twist = True          # current P-R8-12: tau_dot = 0 while re-approaching
    lift_twist_fraction = None  # if set: tau_dot = sign(n_leg) f v_max / max|n| while re-approaching
    single_leg = False         # only one re-approach at a time (diagonal partner not started)
    exit_samples = 1           # consecutive samples >= F_min to end
    exit_margin_N = 0.0
    leg_boost = None           # lift twist: the lifted leg at least leg_boost v_max
    extend_only = False        # lift twist: only the extending components (no retraction of grounded legs)

    def _lift_tau(self):
        leg = sorted(self._state.active_reapproaches)[0]
        n = self.geometry.twist_vector
        return math.copysign(1.0, n[leg]) * self.lift_twist_fraction * self.geometry.max_speed_m_s / np.max(np.abs(n))

    def _twist_channel_rate(self, reading, *, is_held):
        rate = super()._twist_channel_rate(reading, is_held=False)
        if not is_held:
            return rate
        if self.lift_twist_fraction is not None:
            return 0.0 if self.extend_only else self._lift_tau()
        return 0.0 if self.hold_twist else rate

    def _apply_reapproach_speeds(self, leg_speeds, reapproaching):
        if self.lift_twist_fraction is not None:
            if self.extend_only and reapproaching.any():
                return leg_speeds + np.clip(self.geometry.twist_vector * self._lift_tau(), 0.0, None)
            if self.leg_boost is not None and reapproaching.any():
                s = leg_speeds.copy()
                s[reapproaching] = np.maximum(s[reapproaching], self.leg_boost * self.geometry.max_speed_m_s)
                return s
            return leg_speeds
        return super()._apply_reapproach_speeds(leg_speeds, reapproaching)

    def _start_reapproaches(self, reading, loads_N, settings):
        if self.single_leg and self._state.active_reapproaches:
            self._state.reapproach_low_counts[:] = 0
            return
        super()._start_reapproaches(reading, loads_N, settings)

    def _end_finished_reapproaches(self, reading, loads_N, settings):
        if self.exit_samples <= 1 and self.exit_margin_N == 0.0:
            return super()._end_finished_reapproaches(reading, loads_N, settings)
        state = self._state
        cnt = getattr(self, "_exit_cnt", {})
        level = self.geometry.F_min_N + self.exit_margin_N
        for leg, run in list(state.active_reapproaches.items()):
            travel = float(reading.motor_stroke_m[leg]) - run.start_motor_stroke_m
            cnt[leg] = cnt.get(leg, 0) + 1 if loads_N[leg] >= level else 0
            if cnt[leg] >= self.exit_samples:
                cnt[leg] = 0
                self._end_reapproach(leg, reading, "contact")
                self._add_event(reading.t_s, f"leg_reapproach_contact:{LEG_ORDER[leg]}")
            elif travel > settings.max_travel_m:
                self._end_reapproach(leg, reading, "no_contact")
                state.is_reapproach_armed[leg] = False
        state.is_reapproach_armed |= loads_N >= self.geometry.F_min_N
        self._exit_cnt = cnt


VARIANTS = {
    "preset": dict(project=True),
    "preset_p30off": dict(project=True, p30_off=True),
    "preset_leg": dict(project=True, settings=LiftedReapproachSettings.leg_mode()),
    "off": dict(enable=False),
    "cur": dict(),
    "keep_twist": dict(hold_twist=False),
    "cur_v0.5": dict(speed=0.5),
    "cur_single_hyst": dict(single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "keep_twist_single_hyst": dict(hold_twist=False, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "lifttw0.25": dict(lift_twist_fraction=0.25, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "lifttw0.5": dict(lift_twist_fraction=0.5, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "lifttw0.35": dict(lift_twist_fraction=0.35, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "lifttw0.4": dict(lift_twist_fraction=0.4, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "tw0.25_s1": dict(lift_twist_fraction=0.25, samples=1, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "tw0.3_s1": dict(lift_twist_fraction=0.3, samples=1, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "tw0.25_b0.5": dict(lift_twist_fraction=0.25, leg_boost=0.5, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "tw0.25_b0.5_s1": dict(lift_twist_fraction=0.25, leg_boost=0.5, samples=1, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "tw0.3": dict(lift_twist_fraction=0.3, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "ext0.25": dict(lift_twist_fraction=0.25, extend_only=True, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "ext0.4": dict(lift_twist_fraction=0.4, extend_only=True, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "ext0.5": dict(lift_twist_fraction=0.5, extend_only=True, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
    "ext0.75": dict(lift_twist_fraction=0.75, extend_only=True, single_leg=True, exit_samples=3, exit_margin_N=5000.0),
}


def make_controller(name: str) -> C2Controller:
    v = VARIANTS[name]
    config = cl.preset_config(ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=v.get("enable", True))
    if v.get("project"):
        if "settings" in v:
            config = replace(config, r8=replace(config.r8, lifted_reapproach=v["settings"]))
        if v.get("p30_off"):
            config = replace(config, pre_loc_lift_pause=replace(config.pre_loc_lift_pause, enable=False))
        ctl = C2Controller.from_params(cl.PARAMS, config)
        ctl.reset()
        return ctl
    if v.get("enable", True):
        # The harness overrides were written on P-R8-12 (rev. 33), now the c2.py leg mode.
        config = replace(config, r8=replace(config.r8, lifted_reapproach=LiftedReapproachSettings.leg_mode()))
    if "samples" in v:
        r8 = config.r8
        config = replace(config, r8=replace(r8, lifted_reapproach=replace(r8.lifted_reapproach, samples=v["samples"])))
    if "speed" in v:
        r8 = config.r8
        config = replace(config, r8=replace(r8, lifted_reapproach=replace(r8.lifted_reapproach, speed_fraction=v["speed"])))
    ctl = Variant.from_params(cl.PARAMS, config)
    for k in ("leg_boost", "extend_only", "hold_twist", "lift_twist_fraction", "single_leg", "exit_samples", "exit_margin_N"):
        if k in v:
            setattr(ctl, k, v[k])
    ctl.reset()
    return ctl


def pad_gaps(plant) -> np.ndarray:
    """Axial gap per pad (> 0 = lifted) [m], same geometry as the kernel."""
    R = _R(plant.q)
    ez = R[:, 2]
    a_n = float(plant.nrm @ ez)
    out = np.zeros(4)
    for i in range(4):
        p0 = plant.r + R @ plant.pad_rel[i]
        gax = (plant.nrm @ p0 + plant.goff[i]) / a_n
        out[i] = gax - plant.x[i]
    return out


def run(name: str, mode: str) -> dict:
    rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = rmf.FlexPlant(os.environ.get("V34_LEVEL", "top"), 0.0, 0.0)
    plant.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    ctl = make_controller(name)
    head_area = ctl.geometry.head_area_m2
    lag_steps = round(cl.LAG_CHUNK_S / plant.dt)
    command = np.zeros(4)
    valve = np.zeros(4)
    t_ready = t_event = t_probe = None
    rec = []  # 1 ms: t, contact(4), gap(4), cylforce(4), pressure(4)
    att = []
    phases = []
    t_reready = None
    while plant.t < 200.0:
        imu = []
        for _ in range(10):
            fs = np.zeros(3)
            for _ in range(10):
                if t_event is not None:
                    depth, ramp = {"F": (DROP_M, DROP_S), "P": (DROP_M, DROP_S), "S": (0.03, 2.0), "G": (0.0115, 2.0)}[mode]
                    plant.goff[3] = depth * min(1.0, max(0.0, (plant.t - t_event) / ramp))
                acc = cl._lagged_step(plant, command, valve, lag_steps)
                fs += acc[0:3]
                if t_event is not None and plant.t <= t_event + WINDOW_S + 3.0:
                    rec.append(np.r_[plant.t, acc[11:15], pad_gaps(plant), plant.true_cyl_force(), plant.pressure()])
            imu.append(fs / (lag_steps * 10))
        from outrigger_sim.signals import Measurements
        m = Measurements(
            t_s=plant.t, specific_force_m_s2=np.mean(imu, axis=0), angular_rate_rad_s=np.asarray(plant.w, float),
            head_pressure_Pa=plant.pressure() / head_area, stroke_m=np.asarray(plant.sref, float),
            stroke_corrected_m=np.asarray(plant.x, float), imu_specific_force_samples_m_s2=np.array(imu))
        command = np.array(ctl.update(m).leg_speed_m_s)
        ph = ctl.phase
        phases.append((round(plant.t, 2), str(ph)))
        if ph is C2Phase.READY and t_ready is None:
            t_ready = plant.t
        if ph is C2Phase.PROBE and t_probe is None:
            t_probe = plant.t
        if t_event is None:
            if mode in ("F", "S", "G") and t_ready is not None and plant.t >= t_ready + 3.0:
                t_event = plant.t
            if mode == "P" and t_probe is not None and plant.t >= t_probe + 0.1 - 1e-9:
                t_event = plant.t
        if t_event is not None:
            att.append((plant.t - t_event, *np.degrees(plant.attitude())))
            if t_reready is None and ph is C2Phase.READY and plant.t > t_event + 0.5:
                t_reready = plant.t - t_event
            if plant.t > t_event + 70 or (t_reready is not None and plant.t > t_event + t_reready + 2):
                break
    if t_event is None:
        return {"variant": name, "mode": mode, "error": "no event", "phase": str(ctl.phase), "t_ready": t_ready, "t_probe": t_probe}
    r = np.array(rec)
    t = r[:, 0] - t_event
    w = (t >= 0) & (t <= WINDOW_S)
    out = {"variant": name, "mode": mode, "t_event_s": t_event, "t_ready_s": t_ready}
    lifts = {}
    for i, leg in enumerate(LEG_ORDER):
        lifted = w & (r[:, 1 + i] <= 0)
        if not lifted.any():
            continue
        idx = np.flatnonzero(lifted)
        br = np.flatnonzero(np.diff(idx) > 1)
        st = np.r_[idx[0], idx[br + 1]]
        en = np.r_[idx[br], idx[-1]]
        lifts[leg] = {"sum_s": round(float(lifted.sum() * cl.LAG_CHUNK_S), 3),
                      "episodes": [(round(float(t[a]), 3), round(float(t[b] - t[a] + 1e-3), 3),
                                    round(float(r[a:b + 1, 5 + i].max() * 1e3), 2)) for a, b in zip(st, en)]}
    out["lifts"] = lifts
    rr_c = (r[:, 4] > 0) & (t > 0.02)
    idx = np.flatnonzero(rr_c)
    out["RR_first_contact_s"] = round(float(t[idx[0]]), 3) if idx.size else None
    # first time RR stays in contact for >= 1 s
    firm = None
    if idx.size:
        br = np.flatnonzero(np.diff(idx) > 1)
        st = np.r_[idx[0], idx[br + 1]]
        en = np.r_[idx[br], idx[-1]]
        for a, b in zip(st, en):
            if t[b] - t[a] >= 1.0:
                firm = round(float(t[a]), 3)
                break
    out["RR_firm_contact_s"] = firm
    ww = (t >= 0) & (t <= WINDOW_S + 3)
    out["max_cyl_force_kN"] = np.round(r[ww, 9:13].max(axis=0) / 1e3, 1).tolist()
    out["max_head_bar"] = np.round(r[ww, 13:17].max(axis=0) / head_area / 1e5, 1).tolist()
    a = np.array(att)
    aw = a[(a[:, 0] >= 0) & (a[:, 0] <= WINDOW_S + 3)]
    out["max_abs_att_deg"] = np.round(np.abs(aw[:, 1:]).max(axis=0), 4).tolist()
    out["min_cyl_force_kN_after_event"] = np.round(r[(t >= 0), 9:13].min(axis=0) / 1e3, 2).tolist()
    out["t_reready_s"] = None if t_reready is None else round(t_reready, 2)
    out["pre_event_reapproach"] = [f"{e.t_s:.2f} {e.name}" for e in ctl.events
                                   if e.t_s < t_event and "reapproach" in e.name.lower()]
    print("   pre-event reapproach events:", out["pre_event_reapproach"], flush=True)
    out["events"] = [f"{e.t_s - t_event:.2f} {e.name}" for e in ctl.events if -0.5 < e.t_s - t_event < 8]
    return out


def main() -> None:
    out_path = Path(sys.argv[1])
    names = sys.argv[2:] or list(VARIANTS)
    res = []
    modes = os.environ.get("V34_MODES", "F,P").split(",")
    for mode in modes:
        for n in names:
            o = run(n, mode)
            res.append(o)
            lf = o.get("lifts", {}).get("FL", {})
            print(mode, n, "FL sum", lf.get("sum_s"), "eps", lf.get("episodes"), "RR first/firm",
                  o.get("RR_first_contact_s"), o.get("RR_firm_contact_s"), "maxbar", o.get("max_head_bar"),
                  "att", o.get("max_abs_att_deg"), "minF", o.get("min_cyl_force_kN_after_event"), "reREADY", o.get("t_reready_s"), o.get("error", ""), flush=True)
            other = {k: v["sum_s"] for k, v in o.get("lifts", {}).items() if k not in ("FL", "RR")}
            if other:
                print("   other lifts", other)
    out_path.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
