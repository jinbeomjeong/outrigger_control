"""M-4 (control spec rev. 59 295): offline LOC check of recorded Chrono R8 rigid-floor runs.

For every run directory with ``r8_series.npz`` + ``record/record.npz`` the soil-response rules
S-1 (load-sum plateau, P-S9-2) and the crawler-zone latch release (``_update_crawler_zone``) are
re-evaluated on the recorded 10 Hz samples with the installed ``C2Geometry`` / filter objects:

* period k is a LEVEL call when the recorded phase after call k-1 is ``level``
  (``r8_series.phase`` is the phase after the call);
* applied output of the previous period = ``r8_series.issued_u[k-1]`` (what ``C2.command``
  returned, i.e. ``_state.applied_output_m_s``);
* reading: motor stroke = ``meas.stroke``, rod stroke = ``meas.stroke_corrected``, load =
  ``p_h A_h - p_r A_ann`` from ``meas.head_pressure`` / ``meas.rod_pressure`` (no zero-offset
  correction: a constant offset shifts the 0.85 W_ref check only, not the plateau slope);
* slow clearance = ``min_k c_k(s_motor - P_bar / k_oil(s_motor))`` with ``P_bar`` the
  crawler-rule low-pass (time constant from the preset) run on every period.

A run "keeps its commands with the soil response on" (spec 285 end paragraph) when the LOC is
confirmed (1) no later than the first latch release (slow clearance >= 20 mm) and (2) no later
than the first DONE, and (3) ``c_min(t_P)`` <= 20 mm (no S-3 bias). Up to the first period
where one of these fails the recorded run is what the soil-on controller would also have done,
so the offline verdict is exact up to that period (apart from the YAML difference below).

Limits (reported): the controller geometry is built from the *current* YAML (the S7 / S8 runs
used the YAML before the 2026-10-25 regeneration); sensor-model runs carry their pressure
offsets in the load sum.

Usage::

    python -I -X utf8 04_scripts/02_chrono/s9_merge/m4_offline.py <out.json> <run dir or batch>...
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

from outrigger_sim.control.c2 import C2Config, C2Controller  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.sensors.attitude import CascadedLowPass  # noqa: E402

_CTRL: dict[str, C2Controller] = {}


def controller(level: str) -> C2Controller:
    if level not in _CTRL:
        params = load_params(level=level)
        config = C2Config().with_10hz_d1()
        rise = os.environ.get("M4_RISE_MAX_N")  # sensitivity only (default: the preset 2 kN)
        if rise:
            config = replace(config, soil=replace(config.soil, plateau_rise_max_N=float(rise)))
        _CTRL[level] = C2Controller.from_params(params, config)
    return _CTRL[level]


def find_runs(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        p = Path(p)
        if (p / "r8_series.npz").exists():
            out.append(p)
        else:
            out.extend(sorted(q.parent for q in p.rglob("r8_series.npz")))
    return out


def analyse(run: Path) -> dict:
    r8 = np.load(run / "r8_series.npz", allow_pickle=False)
    rec = np.load(run / "record" / "record.npz", allow_pickle=False)
    res = json.loads((run / "result.json").read_text("utf-8"))
    settings = res.get("settings", {})
    level = settings.get("level") or "top"
    c2 = controller(level)
    geo = c2.geometry
    cfg = c2.config
    soil = cfg.soil
    thr = cfg.thresholds
    t = np.asarray(r8["t"], float)
    if rec["t"].shape != t.shape or np.max(np.abs(rec["t"] - t)) > 1e-9:
        return {"run": str(run), "status": "time_mismatch"}
    phase = [str(p) for p in r8["phase"]]
    issued = np.asarray(r8["issued_u"], float)
    s_motor = np.asarray(rec["meas.stroke"], float)
    s_rod = np.asarray(rec["meas.stroke_corrected"], float)
    p_h = np.asarray(rec["meas.head_pressure"], float)
    p_r = np.asarray(rec["meas.rod_pressure"], float) if "meas.rod_pressure" in rec.files \
        else np.zeros_like(p_h)
    p_r = np.nan_to_num(p_r)
    force = p_h * geo.head_area_m2 - p_r * geo.annulus_area_m2
    lp = CascadedLowPass(cfg.filters.crawler_rule_pressure_time_constant_s, 1, cfg.period_s)
    v_max = float(geo.max_speed_m_s)
    w_ref = float(c2._reference_weight_N())
    in_zone = True
    window: list[tuple[float, float, float, np.ndarray]] = []
    loc = None
    release_t = None
    release_clear = None
    first_level = None
    first_done = None
    max_slow_before_loc = -math.inf
    best_rise = math.inf
    reasons = {"retract": 0, "slow": 0}
    n_level = 0
    for k in range(len(t)):
        p_bar = lp.update(force[k])
        if phase[k] == "done" and first_done is None:
            first_done = float(t[k])
        if k == 0 or phase[k - 1] != "level":
            continue
        n_level += 1
        if first_level is None:
            first_level = float(t[k])
        # S-1 window (only before the LOC)
        if loc is None:
            applied = issued[k - 1]
            if np.all(applied >= 0.0) and float(np.mean(applied)) >= \
                    soil.plateau_mean_speed_fraction * v_max:
                window.append((float(t[k]), float(np.mean(s_motor[k])), float(np.sum(force[k])),
                               geo.clearance_corners_m(s_rod[k])))
                last = window[-1][1]
                if last - window[0][1] >= soil.plateau_window_m:
                    start = len(window) - 1
                    while start > 0 and last - window[start][1] < soil.plateau_window_m:
                        start -= 1
                    tail = window[start:]
                    e = np.array([w[1] for w in tail])
                    f = np.array([w[2] for w in tail])
                    if len(tail) >= 3:
                        slope = float(np.polyfit(e - e.mean(), f, 1)[0])
                    else:
                        slope = (f[-1] - f[0]) / max(e[-1] - e[0], 1e-9)
                    rise = slope * soil.plateau_window_m
                    mean_f = float(f.mean())
                    best_rise = min(best_rise, rise)
                    if rise <= soil.plateau_rise_max_N and \
                            mean_f >= soil.plausibility_fraction * w_ref:
                        loc = {"t_P_s": tail[0][0], "t_loc_s": tail[-1][0],
                               "rise_N": rise, "W_hat_N": mean_f, "W_ratio": mean_f / w_ref,
                               "clearance_at_P_m": float(tail[0][3].min()),
                               "clearance_at_loc_m": float(tail[-1][3].min()),
                               "n_tail": len(tail)}
            else:
                reasons["retract" if np.any(applied < 0.0) else "slow"] += 1
                window.clear()
        # crawler-zone latch (after S-1 in the same call)
        comp = p_bar / geo.oil_stiffness_N_m(s_motor[k])
        slow_clear = float(np.min(geo.clearance_corners_m(s_motor[k] - comp)))
        if loc is None:
            max_slow_before_loc = max(max_slow_before_loc, slow_clear)
        if in_zone and slow_clear >= thr.crawler_zone_release_m:
            in_zone = False
            if release_t is None:
                release_t = float(t[k])
                release_clear = slow_clear
        elif not in_zone and slow_clear < thr.crawler_zone_rearm_m:
            in_zone = True
    t_loc = None if loc is None else loc["t_loc_s"]
    ok_release = loc is not None and (release_t is None or t_loc <= release_t + 1e-9)
    ok_done = loc is not None and (first_done is None or t_loc < first_done - 1e-9)
    bias = loc is not None and loc["clearance_at_P_m"] > soil.corner_bias_deadzone_m
    if loc is None:
        why = "no LOC" + ("" if n_level else " (no LEVEL period)")
    elif not ok_release:
        why = "LOC after latch release"
    elif not ok_done:
        why = "LOC after first DONE"
    elif bias:
        why = "S-3 bias on (c_min(t_P) > 20 mm)"
    else:
        why = ""
    return {
        "run": str(run), "status": "ok", "case": res.get("case"), "level": level,
        "floor": settings.get("floor"), "n_periods": len(t), "first_phase": phase[0],
        "n_level_calls": n_level, "first_level_t_s": first_level, "first_done_t_s": first_done,
        "release_t_s": release_t, "release_slow_clearance_m": release_clear,
        "max_slow_clearance_before_loc_m": None if not math.isfinite(max_slow_before_loc)
        else max_slow_before_loc,
        "loc": loc, "best_rise_N": None if not math.isfinite(best_rise) else best_rise,
        "window_breaks": reasons, "W_ref_N": w_ref,
        "loc_before_release": ok_release, "loc_before_done": ok_done, "bias_applied": bias,
        "unchanged": bool(loc is not None and ok_release and ok_done and not bias),
        "reason": why,
    }


def main(argv: list[str]) -> int:
    out = Path(argv[0])
    runs = find_runs(argv[1:])
    rows = []
    for run in runs:
        try:
            rows.append(analyse(run))
        except Exception as exc:  # noqa: BLE001 - record and continue
            rows.append({"run": str(run), "status": f"error: {type(exc).__name__}: {exc}"})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, default=float), encoding="utf-8")
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"runs {len(rows)} ok {len(ok)} unchanged {sum(r['unchanged'] for r in ok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
