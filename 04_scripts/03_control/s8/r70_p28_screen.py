"""Spec rev. 70 draft (P-S8-28, U-S8-78 (a)+(b), U-S8-79): candidate evaluation on the r69 G8 harness.

Candidates are a harness subclass of the project C2 (03_src read only), selected by the variant tag:
  proj  project controller as it is
  R     U-S8-79 only: FAULT_STROKE_END:<legs> event; a stroke-end FAULT in LEVEL first re-grounds the legs that
        read lifted (the FAULT_REGROUND machinery with no faulty sensor), then FAULT
  A     (a) LOC anchor: at the lift-off confirmation the S-3 raw bias b_k = c_k(t_P) - (rho_k - min rho) is applied
        with its sign (raising the corner clearance estimate) when c_min(t_P) < -dz_neg (dz_neg = 20 mm, the
        U-S9-C7 dead zone mirrored); otherwise the S-3 rule as now
  A0    as A without the dead zone (any c_min(t_P) < 0)
  G     (b) stroke budget guard in LEVEL after the LOC: an extending leg that would pass s_g = s_soft - 10 mm
        within (1 + d) periods is held by a uniform down shift of all legs (or, in the crawler zone / clearance
        estimate <= lifted level + 5 mm, by stopping that leg only); WARN_LIFT_STROKE_LIMITED:<legs> once per
        LEVEL entry; while limited, the completion clearance condition becomes "estimate >= lifted level"
  combos: AG = A + G + R, A0G = A0 + G + R, GR = G + R; G2R / AG2 / AG2c5 / AG2c10 / R30 see VARIANTS
  (selected: AG2c5 = A with c_hat_0 = -5 mm + G2 hold guard + R30 re-ground)
Grid = r69 G8 keys (``r69_g8_screen.all_jobs``) plus the slope floors of the widened check (start rule value
0.5 / 0.75 on the edge direction, and the edge value 1.0 mirrored in roll / in pitch).
Key = "<r69 key>|<variant>". Records: the r69 job record (clearance = all-node floor gap) + P-S8-28 events, guard
and anchor values, re-ground run (targets, outcome, end reason), final crawler clearance.

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r70_p28_screen.py <project_root> <out_json> [workers]
  python -I r70_p28_screen.py <project_root> --list
Env: R70_VARIANTS (comma, default AG), R70_SET = slope | wide | flat | flatref | all (default slope),
     R70_FILTER (substrings), R70_AFFINITY (hex mask on the parent, inherited).
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
_HERE = ROOT / "04_scripts" / "03_control" / "s8"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np  # noqa: E402

import r69_g8_screen as g8  # noqa: E402

WIDE_FLOORS = {"r050": (1.1, 0.8), "r075": (1.65, 1.2), "edgeMr": (-2.2, 1.6), "edgeMp": (2.2, -1.6)}
"""Rule value |roll|/4.4 + |pitch|/3.2 = 0.5 / 0.75 (edge direction), 1.0 mirrored in roll / in pitch."""
VARIANTS = {
    "proj": {},
    "R": {"reground": True},
    "A": {"anchor": "dz"},
    "A0": {"anchor": "all"},
    "G": {"guard": True},
    "GR": {"guard": True, "reground": True},
    "AG": {"anchor": "dz", "guard": True, "reground": True},
    "A0G": {"anchor": "all", "guard": True, "reground": True},
    "R30": {"reground": True, "travel_max": True},
    "G2R": {"guard": "hold", "reground": True, "travel_max": True},
    "AG2": {"anchor": "dz", "guard": "hold", "reground": True, "travel_max": True},
    "AG2c5": {"anchor": "dz", "anchor_c0_m": 0.005, "guard": "hold", "reground": True, "travel_max": True},
    "AG2c10": {"anchor": "dz", "anchor_c0_m": 0.010, "guard": "hold", "reground": True, "travel_max": True},
}
"""G (``guard`` True) = first guard (stop the guarded leg only in the crawler zone); G2 (``guard`` "hold") = hold
every leg and the attitude integrators, FAULT_LIFT_STROKE_LIMIT after GUARD_HOLD_LIMIT_S without completion;
R30 = re-ground travel limit 30 mm (not the plane-gap estimate)."""
GUARD_HOLD_LIMIT_S = 3.0
DZ_NEG_M = 0.020
GUARD_LOOKAHEAD_PERIODS = 2  # 1 + d (d = 1)
GUARD_EXTRA_MARGIN_M = 0.002
"""G2 only: the guard stroke is 2 mm below the 684.8 mm end-margin stroke (G2R first run overshot it by 0.07-0.37 mm
through the output increment limit and the valve lag)."""
GUARD_CLEARANCE_MARGIN_M = 0.005

_CURRENT = {}


def make_p28_class(c2):
    from outrigger_sim.control import fault_reground as fr
    from outrigger_sim.params import LEG_ORDER

    class P28Controller(c2.C2Controller):
        p28: dict = {}

        def reset(self, *a, **kw):
            out = super().reset(*a, **kw)
            self._p28_limited = False
            self._p28_warned = False
            self._p28_pending = None
            self._p28_rec = {"anchor": None, "guard_periods": 0, "guard_mode": {}, "stroke_end_fault": None,
                             "reground": None}
            return out

        # (a) LOC anchor -------------------------------------------------------------------------------------
        def _confirm_liftoff(self, t_s, tail, mean_load_N):
            super()._confirm_liftoff(t_s, tail, mean_load_N)
            mode = self.p28.get("anchor")
            if not mode:
                return
            soil = self._soil_state()
            raw = np.asarray(soil.corner_bias_raw_m, float)
            c_min = float(soil.clearance_at_plateau_start_m)
            limit = 0.0 if mode == "all" else -DZ_NEG_M
            applied = c_min < limit
            self._p28_rec["anchor"] = {"t_s": round(float(t_s), 2), "c_min_tP_mm": round(c_min * 1e3, 1),
                                       "raw_bias_mm": (raw * 1e3).round(1).tolist(), "applied": applied}
            if applied:
                # c_hat_0: the lowest-rise corner reads -anchor_c0 at t_P (conservative; AG2 left true 42.5 mm)
                soil.corner_bias_m = raw + float(self.p28.get("anchor_c0_m", 0.0))
                self._add_event(t_s, "INFO_LOC_CLEARANCE_ANCHOR:" + ",".join(f"{1e3 * b:.1f}" for b in raw))

        # (b) guard ------------------------------------------------------------------------------------------
        def _start_relevel(self):
            self._p28_limited = False
            self._p28_warned = False
            return super()._start_relevel()

        def _apply_reapproach_speeds(self, leg_speeds, reapproaching):
            speeds = super()._apply_reapproach_speeds(leg_speeds, reapproaching)
            if not self.p28.get("guard") or self._state.phase is not c2.C2Phase.LEVEL:
                return speeds
            if not self._is_liftoff_confirmed():
                return speeds
            reading = self._p28_reading
            extra = GUARD_EXTRA_MARGIN_M if self.p28.get("guard") == "hold" else 0.0
            s_g = self.geometry.stroke_soft_max_m - c2.STROKE_END_MARGIN_M - extra
            look = GUARD_LOOKAHEAD_PERIODS * self.config.period_s
            guarded = (speeds > 0.0) & (reading.motor_stroke_m + np.maximum(speeds, 0.0) * look >= s_g)
            if not guarded.any():
                return speeds
            clearance = self._clearance_estimate_m(reading.rod_stroke_m)
            lifted = self.config.thresholds.lifted_clearance_m
            out = speeds.copy()
            if self._state.in_crawler_zone or clearance <= lifted + GUARD_CLEARANCE_MARGIN_M:
                if self.p28.get("guard") == "hold":
                    # G2: hold every leg (a stopped single leg lets the attitude loop wind up, GR run 9.8 deg)
                    out[:] = 0.0
                    self._p28_hold = True
                    mode = "hold_all"
                else:
                    out[guarded] = 0.0
                    mode = "stop_leg"
            else:
                out = out - float(speeds[guarded].max())
                mode = "shift_down"
            self._p28_limited = True
            self._p28_guard_legs = [int(i) for i in np.flatnonzero(guarded)]
            self._p28_rec["guard_periods"] += 1
            self._p28_rec["guard_mode"][mode] = self._p28_rec["guard_mode"].get(mode, 0) + 1
            if not self._p28_warned:
                self._p28_warned = True
                legs = ",".join(LEG_ORDER[i] for i in np.flatnonzero(guarded))
                self._add_event(reading.t_s, f"WARN_LIFT_STROKE_LIMITED:{legs}", is_warning=True)
            return out

        def _update_completion(self, reading, filtered_clearance_m):
            if self.p28.get("guard") and self._p28_limited:
                lifted = self.config.thresholds.lifted_clearance_m
                if filtered_clearance_m >= lifted:
                    filtered_clearance_m = self.config.thresholds.clearance_target_m
            return super()._update_completion(reading, filtered_clearance_m)

        def _level(self, reading):
            self._p28_reading = reading
            state = self._state
            saved = (state.roll_integral, state.pitch_integral)
            self._p28_hold = False
            out = super()._level(reading)
            if self._p28_hold:
                # G2: the attitude integrators do not run while the guard holds every leg
                state.roll_integral, state.pitch_integral = saved
                since = getattr(self, "_p28_hold_since", None)
                if since is None:
                    self._p28_hold_since = since = float(reading.t_s)
                if state.phase is c2.C2Phase.LEVEL and reading.t_s - since >= GUARD_HOLD_LIMIT_S - 1e-9:
                    legs = ",".join(LEG_ORDER[i] for i in self._p28_guard_legs)
                    self._add_event(reading.t_s, f"FAULT_LIFT_STROKE_LIMIT:{legs}", is_warning=True)
                    self._p28_rec["stroke_end_fault"] = {"t_s": round(float(reading.t_s), 2), "legs": legs,
                                                         "kind": "guard_hold_limit"}
                    state.phase = c2.C2Phase.FAULT
                    if self.p28.get("reground"):
                        self._p28_pending = (float(reading.t_s), [])
                    return self._zero_speeds()
            else:
                self._p28_hold_since = None
            return out

        # FAULT_STROKE_END + U-S8-79 -------------------------------------------------------------------------
        def _update_stroke_end_fault(self, reading, leg_speeds):
            is_fault = super()._update_stroke_end_fault(reading, leg_speeds)
            if is_fault and self.p28:
                th = self.config.thresholds
                at_end = reading.motor_stroke_m >= self.geometry.stroke_soft_max_m - th.stroke_end_fault_margin_m
                legs = [i for i in range(4) if at_end[i] and leg_speeds[i] > th.stroke_end_fault_speed_m_s]
                names = ",".join(LEG_ORDER[i] for i in legs)
                self._add_event(reading.t_s, f"FAULT_STROKE_END:{names}", is_warning=True)
                self._p28_rec["stroke_end_fault"] = {"t_s": round(float(reading.t_s), 2), "legs": names}
                if self.p28.get("reground"):
                    self._p28_pending = (float(reading.t_s), legs)
            return is_fault

        def _phase_command(self, reading):
            out = super()._phase_command(reading)
            pending, self._p28_pending = self._p28_pending, None
            if pending is not None and self._state.phase is c2.C2Phase.FAULT:
                t_s, end_legs = pending
                state = self._state
                if self.config.fault_reground.enable and state.fault_reground_history:
                    run = self._new_fault_reground_run(t_s, ())
                    if self.p28.get("travel_max"):
                        # R30: the plane-gap estimate sees the floor twist on a non-planar floor; use 30 mm
                        for target in run.targets:
                            target.max_travel_m = fr.MAX_TRAVEL_M
                    state.fault_reground = run
                    rec = {"targets": [LEG_ORDER[t.leg] for t in run.targets],
                           "protected": [LEG_ORDER[i] for i in run.protected_legs]}
                    self._p28_rec["reground"] = rec
                    if run.targets:
                        state.phase = c2.C2Phase.FAULT_REGROUND
                        legs = ",".join(rec["targets"])
                        self._add_event(t_s, f"{fr.START_EVENT}:{legs}", is_warning=True)
                    else:
                        run.end_s, run.end_reason = t_s, fr.RegroundEnd.NO_TARGET
            return out

    return P28Controller


def patched_make_base(cl, c2, level, fs_kN, floor, leg, gap_spec):
    plant, ctrl0, info, node_d0 = _ORIG_MAKE(cl, c2, level, fs_kN, floor, leg, gap_spec)
    var = _CURRENT["variant"]
    if var == "proj":
        ctrl = ctrl0
    else:
        cls = make_p28_class(c2)
        ctrl = cls.from_params(cl.PARAMS, ctrl0.config)
        ctrl.p28 = VARIANTS[var]
        ctrl.reset()
    _CURRENT["ctrl"] = ctrl
    _CURRENT["plant"] = plant
    return plant, ctrl, info, node_d0


_ORIG_MAKE = g8.make_base_g8


def job(key):
    parts = key.split("|")
    r69_key, var = "|".join(parts[:-1]), parts[-1]
    g8.FLOORS.update(WIDE_FLOORS)
    g8.make_base_g8 = patched_make_base
    _CURRENT.clear()
    _CURRENT["variant"] = var
    try:
        res = g8.job(r69_key)
    except Exception as exc:  # keep the batch going
        import traceback
        return {"key": key, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}
    res["r69_key"], res["key"], res["variant"] = r69_key, key, var
    ctrl = _CURRENT.get("ctrl")
    plant = _CURRENT.get("plant")
    if ctrl is not None and plant is not None:
        # the controller's own (S-3 / anchor biased) estimate; the r69 field is the unbiased geometry value
        res["crawler_clearance_end_mm"]["controller_biased"] = round(
            float(ctrl._clearance_estimate_m(np.asarray(plant.x, float))) * 1e3, 1)
    rec = getattr(ctrl, "_p28_rec", None)
    if rec is not None:
        run = ctrl._state.fault_reground
        if rec.get("reground") is not None and run is not None:
            rec["reground"].update({"end_reason": None if run.end_reason is None else str(run.end_reason),
                                    "contact_count": run.contact_count,
                                    "outcomes": [None if t.outcome is None else str(t.outcome) for t in run.targets],
                                    "travel_mm": [None if t.travel_m is None else round(t.travel_m * 1e3, 1)
                                                  for t in run.targets]})
        res["p28"] = rec
    return res


def all_jobs(set_name, variants):
    base = []
    if set_name in ("slope", "all"):
        base += g8.all_jobs("slope")
    if set_name in ("wide", "all"):
        for fl in WIDE_FLOORS:
            base.append(f"slope|{fl}|top|4.0|ref|none|0")
            for lg in g8.LEGS:
                base += [f"slope|{fl}|top|4.0|{lg}|raised|{g}" for g in g8.SLOPE_GAPS_MM]
    if set_name in ("flat", "all"):
        base += g8.all_jobs("main")
    if set_name == "flatref":
        base += [k for k in g8.all_jobs("main") if "|ref|" in k]
    return [f"{k}|{v}" for k in base for v in variants]


def set_parent_placement():
    mask = os.environ.get("R70_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def main():
    variants = os.environ.get("R70_VARIANTS", "AG").split(",")
    jobs = all_jobs(os.environ.get("R70_SET", "slope"), variants)
    filt = os.environ.get("R70_FILTER")
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
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r70_p28_screen.py",
                                        "spec": "rev. 70 draft (P-S8-28 candidates)", "variants": variants,
                                        "set": os.environ.get("R70_SET", "slope"), "filter": filt,
                                        "workers": workers, "affinity": os.environ.get("R70_AFFINITY"),
                                        "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
