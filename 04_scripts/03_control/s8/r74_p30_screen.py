"""Spec rev. 73 draft (P-S8-30, user decision 2026-10-28 (C)): a diagonal rear leg lifts while a weak FRONT pad
punches in during the lift (rigid base + S1 front: RR lifted 21.4..23.8 s). Candidate rules on the G6 (r72) and G8
(r69/r70) harnesses, project controller + subclass (03_src read only; the base class is imported in each worker).

Pre-LOC = LEVEL with the soil response on and the lift-off not yet confirmed (the window of the event).
  A   lift pause: pre-LOC, while the lowest lower-load estimate of the four legs is below k_on F_min (on) until it is
      back above k_off F_min (off), the common positive heave of the leg command is removed
      (u <- u - max(0, min u)): the attitude, twist and re-approach parts stay, no leg is pushed down; the crawler
      keeps its share, so the weak pad is not loaded further while the lifted corner is re-closed.
      k_on 2.0, k_off 2.5 (ASSUMPTION). Event INFO_LIFT_PAUSED:<leg> once per pause.
  B   pre-LOC re-approach speed x 2 (twist and leg mode; the speed limit still scales the vector).
  AB  A + B.
  A15 A with k_on 1.5, k_off 2.0.
Variants: proj, A, B, AB, A15.  Keys: "g6|<r72 key>|<variant>" or "g8|<r69 key>|<variant>".

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r74_p30_screen.py <project_root> <out_json> [workers]
  python -I r74_p30_screen.py <project_root> --list
Env: R74_VARIANTS (default proj,A,B,AB,A15), R74_SET = g6 | g6r | g8slope | g8wide | g8flat (comma list),
     R74_FILTER (substrings), R74_AFFINITY (hex mask on the parent).
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
for _p in (ROOT / "04_scripts" / "03_control" / "s8", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

VARIANTS = {
    "proj": None,
    "A": {"pause": (2.0, 2.5)},
    "B": {"speed": 2.0},
    "AB": {"pause": (2.0, 2.5), "speed": 2.0},
    "A15": {"pause": (1.5, 2.0)},
    "Af": {"pause": (2.0, 2.5), "falling_N": 2000.0, "max_pause_s": 3.0},
    "Af3": {"pause": (3.0, 3.5), "falling_N": 2000.0, "max_pause_s": 3.0},
    "Af3B": {"pause": (3.0, 3.5), "falling_N": 2000.0, "max_pause_s": 3.0, "speed": 2.0},
    "Af3N": {"pause": (3.0, 3.5), "falling_N": 2000.0, "max_pause_s": 3.0, "speed": 2.0, "lower_frac": 0.05},
    "Af4B": {"pause": (4.0, 4.5), "falling_N": 2000.0, "max_pause_s": 3.0, "speed": 2.0},
    "Af3B4": {"pause": (3.0, 3.5), "falling_N": 2000.0, "max_pause_s": 3.0, "speed": 4.0},
}
"""Af*: the pause starts only on a leg whose lower estimate is below k_on F_min AND fell by >= falling_N since the last
sample (a leg being unloaded, not the weak pad itself, which reads low but rises); it ends at k_off F_min or after
max_pause_s (so the LOC plateau window is not held off for long)."""
_CAP = {}


def make_p30_class(c2, params):
    from outrigger_sim.params import LEG_ORDER

    class P30Controller(c2.C2Controller):
        p30 = params

        def reset(self, *a, **kw):
            out = super().reset(*a, **kw)
            self._p30_paused = False
            self._p30_rec = {"pause_periods": 0, "pauses": 0, "speedup_periods": 0}
            return out

        def _p30_pre_loc(self):
            return (self.config.soil.enable and self._state.phase is c2.C2Phase.LEVEL
                    and not self._is_liftoff_confirmed())

        def _level(self, reading):
            self._p30_reading = reading
            return super()._level(reading)

        def _apply_reapproach_speeds(self, leg_speeds, reapproaching):
            speeds = super()._apply_reapproach_speeds(leg_speeds, reapproaching)
            pause = self.p30.get("pause")
            if pause is None or not self._p30_pre_loc():
                self._p30_paused = False
                return speeds
            reading = self._p30_reading
            loads = self._load_estimate_N(reading.cylinder_force_lower_N)
            prev = getattr(self, "_p30_prev_loads", None)
            self._p30_prev_loads = loads.copy()
            f_min = self.geometry.F_min_N
            k_on, k_off = pause
            falling_N = self.p30.get("falling_N")
            if falling_N is None:
                cand = loads
            else:
                drop = np.zeros(4) if prev is None else prev - loads
                cand = np.where(drop >= falling_N, loads, np.inf)
            low = float(np.min(cand))
            t = float(reading.t_s)
            if not self._p30_paused and low < k_on * f_min:
                self._p30_paused = True
                self._p30_pause_leg = int(np.argmin(cand))
                self._p30_pause_t = t
                self._p30_rec["pauses"] += 1
                self._add_event(reading.t_s, f"INFO_LIFT_PAUSED:{LEG_ORDER[self._p30_pause_leg]}")
            elif self._p30_paused:
                watched = loads[self._p30_pause_leg] if falling_N is not None else float(np.min(loads))
                too_long = (self.p30.get("max_pause_s") is not None
                            and t - self._p30_pause_t >= self.p30["max_pause_s"] - 1e-9)
                if watched >= k_off * f_min or too_long:
                    self._p30_paused = False
            if not self._p30_paused:
                return speeds
            self._p30_rec["pause_periods"] += 1
            out = speeds - max(0.0, float(np.min(speeds)))
            if self.p30.get("lower_frac"):
                # give load back to the crawler: lower the deck uniformly (pre-LOC only, the crawler still bears)
                out = out - float(self.p30["lower_frac"]) * self.geometry.max_speed_m_s
            return out

        def _reapproach_speed_factor(self, leg):
            factor = super()._reapproach_speed_factor(leg)
            if self.p30.get("speed") and self._p30_pre_loc():
                self._p30_rec["speedup_periods"] += 1
                return factor * float(self.p30["speed"])
            return factor

    return P30Controller


def g6_job(r72_key, var):
    import r72_g6_screen as g6
    orig = g6.make_controller_preset

    def make(cl, c2, variant):
        ctrl = orig(cl, c2, variant)
        if VARIANTS[var] is not None:
            ctrl = make_p30_class(c2, VARIANTS[var]).from_params(cl.PARAMS, ctrl.config)
            ctrl.reset()
            g6._CAP["ctrl"] = ctrl
        return ctrl

    g6.make_controller_preset = make
    try:
        rec = g6.job(r72_key)
    finally:
        g6.make_controller_preset = orig
    rec["p30"] = getattr(g6._CAP.get("ctrl"), "_p30_rec", None)
    return rec


def g8_job(r69_key, var):
    import r69_g8_screen as g8
    import r70_p28_screen as r70
    orig = r70._ORIG_MAKE

    def make(cl, c2, level, fs_kN, floor, leg, gap_spec):
        plant, ctrl, info, node_d0 = orig(cl, c2, level, fs_kN, floor, leg, gap_spec)
        if VARIANTS[var] is not None:
            ctrl = make_p30_class(c2, VARIANTS[var]).from_params(cl.PARAMS, ctrl.config)
            ctrl.reset()
        _CAP["ctrl"] = ctrl
        return plant, ctrl, info, node_d0

    g8.FLOORS.update(r70.WIDE_FLOORS)
    g8.make_base_g8 = make
    rec = g8.job(r69_key)
    rec["p30"] = getattr(_CAP.get("ctrl"), "_p30_rec", None)
    return rec


def job(key):
    parts = key.split("|")
    harness, var, inner = parts[0], parts[-1], "|".join(parts[1:-1])
    try:
        rec = g6_job(inner, var) if harness == "g6" else g8_job(inner, var)
    except Exception as exc:  # keep the batch going
        import traceback
        return {"key": key, "error": repr(exc), "tb": traceback.format_exc()[-2000:]}
    rec["key"], rec["inner_key"], rec["variant"], rec["harness"] = key, inner, var, harness
    return rec


def all_jobs(sets, variants):
    base = []
    for s in sets:
        if s in ("g6", "g6r"):
            import r72_g6_screen as g6
            base += [f"g6|{k}" for k in (g6.all_jobs("all") if s == "g6" else g6.all_jobs("rigid_all"))]
        elif s.startswith("g8"):
            import r70_p28_screen as r70
            name = {"g8slope": "slope", "g8wide": "wide", "g8flat": "flat"}[s]
            base += [f"g8|{k.rsplit('|', 1)[0]}" for k in r70.all_jobs(name, ["x"])]
    return [f"{k}|{v}" for k in base for v in variants]


def set_parent_placement():
    mask = os.environ.get("R74_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def main():
    variants = os.environ.get("R74_VARIANTS", "proj,A,B,AB,A15").split(",")
    jobs = all_jobs(os.environ.get("R74_SET", "g6r").split(","), variants)
    filt = os.environ.get("R74_FILTER")
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
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r74_p30_screen.py",
                                        "variants": {v: VARIANTS[v] for v in variants}, "filter": filt,
                                        "set": os.environ.get("R74_SET", "g6r"), "workers": workers,
                                        "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)
    for r in res:
        if "error" in r:
            print(r["key"], r["error"])
            continue
        if r.get("harness") == "g6":
            pre = [(p["leg"], p["true_min_kN"]) for p in r.get("preloc_starts") or []]
            print(r["key"], "pass", r["pass"], {k: v for k, v in r["gates"].items() if not v}, "ready",
                  r.get("t_ready_s"), "minF", r.get("min_true_Fcyl_after_off_kN"), "pre", pre, "p30", r.get("p30"))


if __name__ == "__main__":
    main()
