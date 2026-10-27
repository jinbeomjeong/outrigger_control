"""P-S8-27 candidates (spec rev. 68 356): TOUCH latch hold rule vs the crawler-leg rocking limit cycle.

Harness = rev. 67 PS-7 path (``r67_g1_screen.make_base`` / ``run_base``: reduced 6-DOF plant settled on the crawler,
optional pre-extension of one leg, armed, project C2 R8 preset). The project controller already carries P-S8-26
(the TOUCH free-air cap). Variants (harness subclasses only, the project code is not changed):

* ``proj`` - project controller as it is (P-S8-26);
* ``c1``   - candidate 1: a ``touch_seen`` leg that is a latch candidate keeps its candidate (and stays stopped) over
  ONE sample below the touchdown level; the candidate is dropped only after 2 samples below in a row;
* ``c2``   - candidate 2: a ``touch_seen`` leg latches when the mean touchdown load of the last 0.5 s (5 samples) is
  >= the touchdown level AND every reading in that window is > m_rod g (pad carrying load); while that mean is
  >= the level the leg stays stopped; the project consecutive-hold latch stays as well.

Cases: ref (no pre-grounding), PS7a_RR, PS7a_FL, PS7b_RR, PS7c_RR x top / bottom x F_s 0 / 8 kN x 3 variants = 60.
Per run: D8 gates (as rev. 67), TOUCH record (duration, latch, extra stroke of the pre-grounded leg, max |pitch|,
crawler minimum), the pre-grounded leg's pad-load oscillation in TOUCH (half peak-to-peak per
2 s of the raw load and of the load with its 1001-sample centred moving mean removed; the motor
work on the oscillating load is computed only in the sibling script ``r68_c73_rocking.py``) and
the SHA-256 (16 hex) of the 10 Hz leg command sequence.

Usage (repo root): python -I r68_p27_screen.py <project_root> <out_json> [workers]
Env: R68_AFFINITY = hex mask (default 0FFF0000, E-cores), priority BelowNormal set in the parent (inherited).
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import time
from collections import deque
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
_HERE = ROOT / "04_scripts" / "03_control" / "s8"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np  # noqa: E402

import r51_reapp_closed_loop as r51  # noqa: E402
import r67_g1_screen as r67  # noqa: E402

LEGS = r67.LEGS
VARIANTS = tuple(os.environ.get("R68_VARIANTS", "proj,c1,c2").split(","))
"""``c1b`` = candidate 1 with two tolerated dips (drop after 3 below in a row), added after the Chrono estimate.
``c1c`` = c1b only for legs whose TOUCH free-air reference was capped (P-S8-26 ``free_air_capped_legs``),
added after the V-3 acceptance showed c1b also acting in TOUCH without pre-grounding (spec rev. 68 358)."""
C1_DIPS_TOLERATED = 1
C2_WINDOW_SAMPLES = 5
TREND_WINDOW_SAMPLES = 1001  # 1 s centred moving mean at the 1 ms record step
TREND_EDGE_SAMPLES = 500  # half window: np.convolve(mode="same") is zero-padded there


def set_parent_placement() -> None:
    if sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    h = k32.GetCurrentProcess()
    k32.SetProcessAffinityMask(h, int(os.environ.get("R68_AFFINITY", "0FFF0000"), 16))
    k32.SetPriorityClass(h, 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS


def make_variant_class(c2, variant):
    hold_slack = getattr(c2, "TOUCH_HOLD_SLACK_S", 1e-9)

    class P27Controller(c2.C2Controller):
        p27_variant = variant

        def _touchdown_load_N(self, reading):
            v = super()._touchdown_load_N(reading)
            self._p27_last_load = np.array(v, float)
            self._p27_last_read = np.array(reading.cylinder_force_N, float)
            return v

        def _update_touch_latches(self, bears_touch_load, t_s):
            if self.p27_variant in ("c1", "c1b", "c1c"):
                return self._latch_c1(bears_touch_load, t_s)
            if self.p27_variant == "c2":
                return self._latch_c2(bears_touch_load, t_s)
            return super()._update_touch_latches(bears_touch_load, t_s)

        def _latch_c1(self, bears, t_s):
            st = self._state
            hold_s = self.config.thresholds.touch_hold_s
            miss = getattr(self, "_p27_miss", None)
            if miss is None:
                miss = self._p27_miss = np.zeros(4, dtype=int)
            waiting = np.zeros(4, dtype=bool)
            for leg in range(4):
                if st.touched[leg]:
                    continue
                if not bears[leg]:
                    tolerated = 2 if self.p27_variant in ("c1b", "c1c") else C1_DIPS_TOLERATED
                    in_scope = (self.p27_variant != "c1c"
                                or leg in getattr(st, "free_air_capped_legs", set()))
                    if (in_scope and st.touch_seen[leg] and st.touch_candidate_since_s[leg] is not None
                            and miss[leg] < tolerated):
                        miss[leg] += 1
                        waiting[leg] = True
                        self.p27_used = getattr(self, "p27_used", set()) | {leg}
                        continue
                    st.touch_candidate_since_s[leg] = None
                    miss[leg] = 0
                    continue
                miss[leg] = 0
                since = st.touch_candidate_since_s[leg]
                if since is None:
                    since = st.touch_candidate_since_s[leg] = t_s
                if t_s - since >= hold_s - hold_slack:
                    st.touched[leg] = True
                else:
                    waiting[leg] = True
            return waiting

        def _latch_c2(self, bears, t_s):
            st = self._state
            hist = getattr(self, "_p27_hist", None)
            if hist is None:
                hist = self._p27_hist = deque(maxlen=C2_WINDOW_SAMPLES)
            hist.append((self._p27_last_load.copy(), self._p27_last_read.copy()))
            level = self.config.thresholds.touch_load_factor * self.geometry.F_min_N
            rod = self._touch_rod_weight_N()
            pre_touched = st.touched.copy()
            hold_wait = np.zeros(4, dtype=bool)
            if len(hist) == C2_WINDOW_SAMPLES:
                loads = np.array([h[0] for h in hist])
                reads = np.array([h[1] for h in hist])
                with np.errstate(invalid="ignore"):
                    mean = loads.mean(axis=0)
                for leg in range(4):
                    if pre_touched[leg] or not st.touch_seen[leg] or not np.isfinite(mean[leg]):
                        continue
                    if mean[leg] >= level:
                        if reads[:, leg].min() > rod[leg]:
                            st.touched[leg] = True
                            self.p27_used = getattr(self, "p27_used", set()) | {leg}
                        else:
                            hold_wait[leg] = True
            waiting = super()._update_touch_latches(bears, t_s)
            return (waiting | hold_wait) & ~st.touched

    return P27Controller


def detrend_with_masked_edges(signal: np.ndarray) -> np.ndarray:
    """Return ``signal`` minus its centred moving mean, NaN where the window runs off the ends."""
    trend = np.convolve(signal, np.ones(TREND_WINDOW_SAMPLES) / TREND_WINDOW_SAMPLES, mode="same")
    detrended = signal - trend
    detrended[:TREND_EDGE_SAMPLES] = np.nan
    detrended[-TREND_EDGE_SAMPLES:] = np.nan
    return detrended


def half_pp_ignoring_nan(values: np.ndarray) -> float | None:
    """Half peak-to-peak of the finite entries of ``values``, None if there are none."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return round(float((finite.max() - finite.min()) / 2), 1)


def oscillation(rec, t0, t1, leg):
    """Pad-load oscillation of ``leg`` in [t0, t1]: half peak-to-peak per 2 s bin, kN.

    ``half_pp_per_2s_kN`` uses the raw load (so a slow trend inside a bin adds to it);
    ``half_pp_detrended_per_2s_kN`` uses the load with its 1 s centred moving mean removed and
    the first / last 500 samples masked, over the same bins (None for a bin with no valid sample).
    """
    t = rec[:, 0]
    m = (t >= t0) & (t <= t1)
    if m.sum() < 1200:
        return None
    N = rec[m, 1 + leg] / 1e3
    N_detrended = detrend_with_masked_edges(N)
    tt = t[m] - t0
    amps = []
    amps_detrended = []
    for a in np.arange(0.0, tt[-1], 2.0):
        w = (tt >= a) & (tt < a + 2.0)
        if w.sum() > 100:
            amps.append(round(float((N[w].max() - N[w].min()) / 2), 1))
            amps_detrended.append(half_pp_ignoring_nan(N_detrended[w]))
    return {"half_pp_per_2s_kN": amps, "half_pp_detrended_per_2s_kN": amps_detrended,
            "N_min_kN": round(float(N.min()), 2), "N_max_kN": round(float(N.max()), 1)}


def job(key):
    _, case, level, fs, var = key.split("|")
    fs = float(fs)
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    t_start = time.perf_counter()
    plant, ctrl0, info = r67.make_base(cl, c2, level, fs, pre=r67.PS7[case])
    if var == "proj":
        ctrl = ctrl0
    else:
        ctrl = make_variant_class(c2, var).from_params(cl.PARAMS, ctrl0.config)
        ctrl.reset()
    cap_cfg = getattr(ctrl.config.r8, "touch_free_air_cap_excess_N", None)
    rec, crawler, log = [], [], []
    tl = r67.run_base(cl, c2, Meas, plant, ctrl, rec=rec, crawler=crawler, log=log)
    rec = np.array(rec)
    t = rec[:, 0]
    contact, F, att = rec[:, 1:5], rec[:, 5:9], rec[:, 17:19]
    res = {"key": key, "case": case, "level": level, "fs_kN": fs, "variant": var, "info": info,
           "cap_config_N": None if cap_cfg is None else list(cap_cfg),
           "t_ready": tl["t_ready"], "t_lift": tl["t_lift"]}
    res["cmd_sha256"] = hashlib.sha256(np.array([q[3] for q in log]).tobytes()).hexdigest()[:16]
    res["p27_used_legs"] = sorted(LEGS[i] for i in getattr(ctrl, "p27_used", set()))
    pre_leg = r67.PS7[case][0]
    tt = np.array([q[0] for q in log])
    is_touch = np.array([q[1] == "touch" for q in log])
    if is_touch.any():
        k0, k_end = int(np.flatnonzero(is_touch)[0]), int(np.flatnonzero(is_touch)[-1])
        latched = np.array([q[7] for q in log])
        lat = {LEGS[i]: (round(float(tt[np.flatnonzero(latched[:, i])[0]] - tt[k0]), 2)
                         if latched[:, i].any() else None) for i in range(4)}
        atts = np.array([q[4] for q in log])[is_touch]
        s0, s1 = log[k0][2] * 1e3, log[k_end][2] * 1e3
        res["touch"] = {"duration_s": round(float(tt[k_end] - tt[k0]), 2), "latch_rel_s": lat,
                        "extra_stroke_mm": None if pre_leg is None else round(float(s1[pre_leg] - s0[pre_leg]), 1),
                        "stroke_delta_mm": np.round(s1 - s0, 1).tolist(),
                        "max_abs_att_deg": np.abs(atts).max(axis=0).round(3).tolist(),
                        "min_crawler_kN": round(min(q[5] for q, m in zip(log, is_touch) if m) / 1e3, 1)}
        if pre_leg is not None:
            res["touch"]["pre_leg_oscillation"] = oscillation(rec, float(tt[k0]), float(tt[k_end]), pre_leg)
    if tl["t_lift"] is not None:
        w = t >= tl["t_lift"]
        mins = F[w].min(axis=0)
        lifts = {LEGS[i]: round(float((w & (contact[:, i] <= 0)).sum() * 1e-3), 3) for i in range(4)}
        att_end = att[t >= t[-1] - 1.0].mean(axis=0)
        g = {"Fmin_plus5": bool(mins.min() >= r67.F_MIN_N + 5e3), "no_lift": all(v == 0 for v in lifts.values()),
             "end_att": bool(np.all(np.abs(att_end) <= 0.2)), "ready": tl["t_ready"] is not None}
        res.update({"min_F_after_liftoff_kN": round(float(mins.min()) / 1e3, 2), "gates": g,
                    "pass": bool(all(g.values())), "att_end_deg": [round(float(a), 4) for a in att_end]})
    res["events"] = [(round(e.t_s, 2), e.name) for e in ctrl.events
                     if e.name.startswith(("INFO_TOUCH", "WARN_PROBE", "WARN_TOUCH"))][:20]
    res["wall_s"] = round(time.perf_counter() - t_start, 1)
    return res


def run_job(key):
    try:
        return job(key)
    except Exception as exc:  # keep the batch going
        import traceback
        return {"key": key, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}


def main():
    set_parent_placement()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    jobs = [f"ps7|{c}|{lv}|{fs}|{v}" for c in r67.PS7 for lv in r67.LEVELS for fs in r67.FS_KN for v in VARIANTS]
    filt = os.environ.get("R68_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        res = pool.map(run_job, jobs, chunksize=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r68_p27_screen.py",
                                        "spec": "rev. 68 356 (P-S8-27 candidates)", "workers": workers,
                                        "affinity": os.environ.get("R68_AFFINITY", "0FFF0000"),
                                        "wall_s": round(time.perf_counter() - t0, 1), "n_jobs": len(jobs)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
