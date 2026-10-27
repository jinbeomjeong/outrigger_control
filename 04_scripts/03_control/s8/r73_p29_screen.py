"""Spec rev. 72/73 draft (P-S8-29, user decision 2026-10-27 (a)): completion with an unsettled twist load on a
creeping pad - candidate evaluation on the G6 (r72) and G8 (r69/r70) harnesses, project controller + subclass
(03_src read only).

Rule (candidates differ in T, W, D_relax): in LEVEL after the lift-off confirmation, when the attitude condition
(reference on target, completion deviation < done_attitude) and the clearance condition have held without a break
for T s, and the twist-load magnitude |D| (D = n . F_read) is falling over the last W s
(|D|(now) <= |D|(now - W) - DROP and max |D| in the window <= |D|(now - W) + RISE_TOL), and |D| <= D_relax, and every
leg's lower load estimate >= F_min, the twist condition of the completion counts as met. The normal rule
(|D| < done_twist 3 kN) is unchanged. DONE reached through the relaxed condition raises INFO_TWIST_UNSETTLED:<D kN>.

Variants: proj (project), V1 T10 W5 inf, V2 T10 W5 15 kN, V3 T20 W10 inf, V4 T5 W5 25 kN.
Keys: "g6|<r72 key>|<variant>" or "g8|<r69 key>|<variant>".

Usage (repo root, dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I r73_p29_screen.py <project_root> <out_json> [workers]
  python -I r73_p29_screen.py <project_root> --list
Env: R73_VARIANTS (comma, default proj,V1,V2,V3,V4), R73_SET = g6 | g6r | g8slope | g8wide | g8flat (comma list),
     R73_FILTER (substrings), R73_AFFINITY (hex mask on the parent).
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from collections import deque
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
for _p in (ROOT / "04_scripts" / "03_control" / "s8", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

VARIANTS = {
    "proj": None,
    "V1": {"T_s": 10.0, "W_s": 5.0, "D_relax_N": float("inf")},
    "V2": {"T_s": 10.0, "W_s": 5.0, "D_relax_N": 15e3},
    "V3": {"T_s": 20.0, "W_s": 10.0, "D_relax_N": float("inf")},
    "V4": {"T_s": 5.0, "W_s": 5.0, "D_relax_N": 25e3},
    "V2b": {"T_s": 10.0, "W_s": 5.0, "D_relax_N": 15e3, "drop_N": 0.0},
}
DROP_N = 500.0
RISE_TOL_N = 300.0
_CAP = {}


def make_p29_class(c2, params):
    class P29Controller(c2.C2Controller):
        p29 = params

        def reset(self, *a, **kw):
            out = super().reset(*a, **kw)
            self._p29_settled_since = None
            self._p29_hist = deque()
            self._p29_used = False
            self._p29_record = {"relaxed_done": [], "max_relax_D_kN": None}
            return out

        def _p29_relaxed(self, reading, twist_N, is_on_target, is_clearance_ok):
            p = self.p29
            t = float(reading.t_s)
            if not (is_on_target and is_clearance_ok and self._is_liftoff_confirmed()):
                self._p29_settled_since = None
                self._p29_hist.clear()
                return False
            if self._p29_settled_since is None:
                self._p29_settled_since = t
            h = self._p29_hist
            h.append((t, abs(twist_N)))
            while h and h[0][0] < t - p["W_s"] - 1e-9:
                h.popleft()
            if t - self._p29_settled_since < p["T_s"] - 1e-9 or h[-1][0] - h[0][0] < p["W_s"] - 0.1 - 1e-9:
                return False
            d_old, d_now = h[0][1], h[-1][1]
            falling = d_now <= d_old - p.get("drop_N", DROP_N) and max(d for _, d in h) <= d_old + RISE_TOL_N
            self._p29_last_window = (round(d_old / 1e3, 2), round(d_now / 1e3, 2))
            loads_ok = bool(np.all(self._load_estimate_N(reading.cylinder_force_lower_N) >= self.geometry.F_min_N))
            return bool(falling and d_now <= p["D_relax_N"] and loads_ok)

        def _update_completion(self, reading, filtered_clearance_m):
            state = self._state
            if self.config.soil.enable and not self._is_liftoff_confirmed():
                state.complete_since_s = None
                return False
            th = self.config.thresholds
            twist_load = float(self.geometry.twist_vector @ reading.cylinder_force_N)
            is_on_target = (self._is_reference_on_target()
                            and self._completion_deviation_rad() < th.done_attitude_rad)
            is_clear = self._is_clearance_done(filtered_clearance_m)
            twist_ok = abs(twist_load) < th.done_twist_N
            relaxed = False
            if not twist_ok and state.phase is c2.C2Phase.LEVEL:
                relaxed = self._p29_relaxed(reading, twist_load, is_on_target, is_clear)
                twist_ok = relaxed
            elif state.phase is c2.C2Phase.LEVEL:
                self._p29_relaxed(reading, twist_load, is_on_target, is_clear)  # keep the history running
            if not (is_on_target and is_clear and twist_ok):
                state.complete_since_s = None
                return False
            if state.complete_since_s is None:
                state.complete_since_s = reading.t_s
                return False
            done = reading.t_s - state.complete_since_s >= th.done_hold_s
            if done and relaxed:
                self._add_event(reading.t_s, f"INFO_TWIST_UNSETTLED:{twist_load / 1e3:.1f}")
                self._p29_record["relaxed_done"].append((round(float(reading.t_s), 1), round(twist_load / 1e3, 1),
                                                         getattr(self, "_p29_last_window", None)))
            return done

    return P29Controller


# ---------------------------------------------------------------------------------------------- G6 (r72)
def g6_job(r72_key, var):
    import r72_g6_screen as g6
    orig = g6.make_controller_preset

    def make(cl, c2, variant):
        ctrl = orig(cl, c2, variant)
        if VARIANTS[var] is not None:
            cls = make_p29_class(c2, VARIANTS[var])
            ctrl = cls.from_params(cl.PARAMS, ctrl.config)
            ctrl.reset()
            g6._CAP["ctrl"] = ctrl
        return ctrl

    g6.make_controller_preset = make  # g6.job -> _install() reads this module name
    rec = g6.job(r72_key)
    g6.make_controller_preset = orig
    ctrl = g6._CAP.get("ctrl")
    rec["p29"] = getattr(ctrl, "_p29_record", None)
    return rec


# ---------------------------------------------------------------------------------------------- G8 (r69)
def g8_job(r69_key, var):
    import r69_g8_screen as g8
    import r70_p28_screen as r70
    orig = r70._ORIG_MAKE

    def make(cl, c2, level, fs_kN, floor, leg, gap_spec):
        plant, ctrl, info, node_d0 = orig(cl, c2, level, fs_kN, floor, leg, gap_spec)
        if VARIANTS[var] is not None:
            cls = make_p29_class(c2, VARIANTS[var])
            ctrl = cls.from_params(cl.PARAMS, ctrl.config)
            ctrl.reset()
        _CAP["ctrl"] = ctrl
        return plant, ctrl, info, node_d0

    g8.FLOORS.update(r70.WIDE_FLOORS)
    g8.make_base_g8 = make
    rec = g8.job(r69_key)
    rec["p29"] = getattr(_CAP.get("ctrl"), "_p29_record", None)
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
            keys = g6.all_jobs("all") if s == "g6" else g6.all_jobs("rigid_all")
            base += [f"g6|{k}" for k in keys]
        elif s.startswith("g8"):
            import r70_p28_screen as r70
            name = {"g8slope": "slope", "g8wide": "wide", "g8flat": "flat"}[s]
            base += [f"g8|{k.rsplit('|', 1)[0]}" for k in r70.all_jobs(name, ["x"])]
    return [f"{k}|{v}" for k in base for v in variants]


def set_parent_placement():
    mask = os.environ.get("R73_AFFINITY")
    if not mask or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask, 16))


def main():
    variants = os.environ.get("R73_VARIANTS", "proj,V1,V2,V3,V4").split(",")
    jobs = all_jobs(os.environ.get("R73_SET", "g6").split(","), variants)
    filt = os.environ.get("R73_FILTER")
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
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r73_p29_screen.py",
                                        "variants": {v: VARIANTS[v] for v in variants}, "filter": filt,
                                        "set": os.environ.get("R73_SET", "g6"), "workers": workers,
                                        "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
