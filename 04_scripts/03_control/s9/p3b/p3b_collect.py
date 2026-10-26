"""S9 P3b control judgement values for all 24 SCM cases (spec rev. 60, 306~315; criteria 284).

Collects the runner's P3-1 .. P3-9 blocks per case and adds control's own recomputations:

- S-1 plateau window replay (P3-7, spec 307 / 310): the 10 Hz record (pressure readings,
  ``meas.stroke``, ``u_applied``) is replayed through the 285 P-S9-2 rule in the LEVEL phase.
  Four variants (output lag 0 / 1 sample, phase shift 0 / 0.05 s) are tried and the one that
  reproduces the controller meta ``t_P_s`` / ``t_loc_s`` is kept. Reports the minimum load-sum
  rise over windows that end while the crawler still carries load (true SCM crawler normal
  > 1 kN), for the reading and for the truth (``F_cyl``, ``s_motor``).
- Rut clearance minima after departure / first READY / last READY (P3-5, spec 309).

Inputs (git-external raw data): ``07_results/S9/batch_P3b_20261026_122444/P3b_*/``
(``result.json``, ``record/record.npz``, ``step_series.npz``).
Output: ``06_analysis/02_control/s9/p3b/p3b_collect.json`` (default).

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p3b_collect.py
      [<batch_dir> [<out_json>]]
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "p3b" / "p3b_collect.json"

V_MAX = 0.020924  # m/s, YAML actuator.max_speed_m_s
F_MIN = 9415.0  # N
A_P = np.array([math.pi / 4 * 0.13**2] * 2 + [math.pi / 4 * 0.11**2] * 2)  # m^2
A_ROD = np.array([math.pi / 4 * 0.11**2] * 2 + [math.pi / 4 * 0.09**2] * 2)
A_ANN = A_P - A_ROD
WIN = 0.010  # m, S-1 plateau window length (stroke)
SPEED_FRAC = 0.15  # mean applied speed must be >= this fraction of v_max
RISE_MAX = 2000.0  # N, plateau rise limit for LOC
PLAUS = 0.85  # window mean must be >= this fraction of W_ref
LOADED_N = 1000.0  # N, crawler normal above which a window counts as "loaded"


def phase_at(phases, t):
    """Phase in force at time t (last transition with t_s <= t)."""
    cur = None
    for p in phases:
        if p["t_s"] <= t + 1e-9:
            cur = p["phase"]
        else:
            break
    return cur


def reconstruct_s1(t, u_prev, stroke, force_sum, phases, w_ref, crawler_at, shift):
    """Replay S-1 on 10 Hz samples.

    Returns:
        (t_P, t_loc, windows) with windows as (t_end, rise, mean, loaded, t_start) tuples.
    """
    window = []
    windows = []
    t_p = t_loc = None
    for k in range(len(t)):
        if phase_at(phases, t[k] - shift) != "level":
            continue
        u = u_prev[k]
        if not (np.all(u >= 0.0) and float(np.mean(u)) >= SPEED_FRAC * V_MAX):
            window.clear()
            continue
        window.append((t[k], float(np.mean(stroke[k])), float(force_sum[k])))
        last = window[-1][1]
        if last - window[0][1] < WIN:
            continue
        start = len(window) - 1
        while start > 0 and last - window[start][1] < WIN:
            start -= 1
        tail = window[start:]
        e = np.array([s[1] for s in tail])
        f = np.array([s[2] for s in tail])
        if len(tail) >= 3:
            slope = float(np.polyfit(e - e.mean(), f, 1)[0])
        else:
            slope = (f[-1] - f[0]) / max(e[-1] - e[0], 1e-9)
        rise = slope * WIN
        mean = float(f.mean())
        loaded = crawler_at(t[k]) > LOADED_N
        windows.append((float(t[k]), rise, mean, bool(loaded), float(tail[0][0])))
        if t_loc is None and rise <= RISE_MAX and mean >= PLAUS * w_ref:
            t_p, t_loc = float(tail[0][0]), float(t[k])
            break
    return t_p, t_loc, windows


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("out_json", nargs="?", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main():
    args = _parse_args()
    batch = args.batch_dir
    out = {}
    for case in sorted(p for p in batch.iterdir() if p.is_dir() and p.name.startswith("P3b_")):
        r = json.loads((case / "result.json").read_text(encoding="utf-8"))
        p3b = r["p3b"]
        soil = r["c2_soil"]
        phases = r["phases"]
        events = r["events"]
        rec = np.load(case / "record" / "record.npz")
        ss = np.load(case / "step_series.npz")
        t = rec["t"]
        ts = ss["t_s"]
        crawler = ss["scm_crawler_normal_N"]

        def crawler_at(tq, ts=ts, crawler=crawler):
            i = int(np.clip(np.searchsorted(ts, tq), 0, len(ts) - 1))
            return float(crawler[i])

        hp = rec["meas.head_pressure"]
        rp = rec["meas.rod_pressure"]
        f_read = hp * A_P - rp * A_ANN
        f_true = rec["F_cyl"]
        w_ref = soil["W_ref_N"]
        u_app = rec["u_applied"]
        res_variants = {}
        for lag in (0, 1):
            u_prev = np.vstack([np.zeros((lag, 4)), u_app[: len(u_app) - lag]]) if lag else u_app
            for shift in (0.0, 0.05):
                tp, tl, wins = reconstruct_s1(
                    t, u_prev, rec["meas.stroke"], f_read.sum(axis=1), phases, w_ref,
                    crawler_at, shift)
                res_variants[f"lag{lag}_shift{shift}"] = (tp, tl, wins)
        # choose the variant that reproduces meta t_P / t_loc
        best = None
        for key, (tp, tl, _wins) in res_variants.items():
            if tl is not None and soil.get("t_loc_s") is not None:
                err = abs(tl - soil["t_loc_s"]) + abs(tp - soil["t_P_s"])
                if best is None or err < best[1]:
                    best = (key, err)
        key = best[0] if best else "lag1_shift0.0"
        tp, tl, wins = res_variants[key]
        loaded = [w for w in wins if w[3]]
        rise_min_read = min((w[1] for w in loaded), default=None)
        # truth variant (record: true F_cyl and true s_motor at the same 10 Hz samples)
        lag = int(key[3])
        shift = float(key.split("shift")[1])
        u_prev = np.vstack([np.zeros((lag, 4)), u_app[: len(u_app) - lag]]) if lag else u_app
        _, tl_true, wins_true = reconstruct_s1(
            t, u_prev, rec["s_motor"], f_true.sum(axis=1), phases, w_ref, crawler_at, shift)
        loaded_true = [w for w in wins_true if w[3] and (tl is None or w[0] <= tl + 1e-9)]
        rise_min_true = min((w[1] for w in loaded_true), default=None)

        # rut clearance (10 Hz rows)
        rows = r["s9_rows"]
        rt = np.array([row["t_s"] for row in rows])
        rut = np.array([row["rut_clearance_m"] if row["rut_clearance_m"] is not None else np.nan
                        for row in rows])
        ready_entries = [p["t_s"] for p in phases if p["phase"] == "ready"]
        touch = [p["t_s"] for p in phases if p["phase"] == "touch"]
        dones = [p["t_s"] for p in phases if p["phase"] == "done"]
        probes = [p["t_s"] for p in phases if p["phase"] == "probe"]
        dep = p3b["departure"]["t_departure_s"]

        def rut_min(t0, rt=rt, rut=rut):
            m = rt >= t0
            if not np.any(m):
                return None, None
            i = int(np.nanargmin(np.where(m, rut, np.inf)))
            return float(rut[i]), float(rt[i])

        p35 = p3b["P3-5_clearance_stroke"]
        rut_dep = rut_min(dep) if dep is not None else (None, None)
        rut_dep1 = rut_min(dep + 1.0) if dep is not None else (None, None)
        rut_ready_first = rut_min(ready_entries[0]) if ready_entries else (None, None)
        rut_ready_last = rut_min(ready_entries[-1]) if ready_entries else (None, None)
        rut_loc = None
        if soil.get("t_loc_s") is not None:
            i = int(np.argmin(abs(rt - soil["t_loc_s"])))
            rut_loc = float(rut[i])
        p34 = p3b["P3-4_attitude"]
        p33 = p3b["P3-3_leg_force"]
        fmin_after = np.array(p33["F_min_after_N"])
        ev_names = [e["name"] for e in events]
        warn = [e for e in events if e["name"].startswith("WARN") or e["name"].startswith("FAULT")]
        out[case.name] = {
            "t_loop_start_s": r["t_loop_start_s"],
            "phases": phases,
            "n_done": len(dones), "n_probe": len(probes), "n_ready_entries": len(ready_entries),
            "t_touch_s": touch[0] if touch else None,
            "t_ready_first_s": ready_entries[0] if ready_entries else None,
            "ready_from_touch_s": (
                (ready_entries[0] - touch[0]) if ready_entries and touch else None),
            "P3-1": p3b["P3-1_crawler"],
            "P3-2": p3b["P3-2_loc"],
            "departure": p3b["departure"],
            "P3-3_min_ratio": float(fmin_after.min() / F_MIN),
            "P3-3_min_N": float(fmin_after.min()),
            "P3-3_min_leg": int(fmin_after.argmin()),
            "P3-3_transient_min_N": float(min(p33["F_min_transient_N"])),
            "P3-3_late_min_N": float(min(p33["F_min_late_N"])),
            "pre_liftoff": p3b["pre_liftoff_min_F_cyl"],
            "P3-4": {k: p34[k] for k in (
                "p34_absmax_overall_deg", "p34_absmax_deg", "p34_window_s", "p34_window_length_s",
                "end_mean_roll_pitch_deg", "window_short", "creep_vibration_suspect",
                "sensor_allowance_left_deg", "budget_residual_le_0p04", "within_0p2",
                "within_deadband_0p03_record", "post_liftoff_absmax_deg", "creep_stop_basis",
                "t_creep_stop_final_two_sided_s", "t_ready_last_entry_s", "done", "ready_at_end",
                "end_mean_minus_settle_deg")},
            "P3-5": {
                "within": p35["within"],
                "rut_min_after_departure_m": p35["rut_clearance_min_after_departure_m"],
                "rut_end_m": p35["rut_clearance_end_m"],
                "rut_min_dep_rows": rut_dep,
                "rut_min_dep_plus1s": rut_dep1,
                "rut_min_after_first_ready": rut_ready_first,
                "rut_min_after_last_ready": rut_ready_last,
                "rut_at_loc_m": rut_loc,
                "s_motor_max_m": max(p35["s_motor_max_m"]),
                "probe_sinkage": p35["probe_sinkage"],
            },
            "P3-6": p3b["P3-6_ready"],
            "P3-7": {
                "variant": key, "reproduce_err_s": best[1] if best else None,
                "t_P_rec": tp, "t_loc_rec": tl, "t_P_meta": soil.get("t_P_s"),
                "t_loc_meta": soil.get("t_loc_s"),
                "n_windows": len(wins), "n_loaded_windows": len(loaded),
                "rise_min_loaded_read_N": rise_min_read,
                "rise_min_loaded_true_N": rise_min_true,
                "n_loaded_windows_true": len(loaded_true),
                "rise_at_loc_N": wins[-1][1] if wins and tl is not None else None,
                "loaded_rises_read_N": [round(w[1], 1) for w in loaded][:60],
            },
            "P3-8": p3b["P3-8_false_triggers"] if "P3-8_false_triggers" in p3b else None,
            "P3-9": {"n_windows": len(p3b["P3-9_deferred"]["windows"]),
                     "flag": p3b["P3-9_deferred"]["flag"],
                     "windows": p3b["P3-9_deferred"]["windows"]},
            "W61": p3b["W61_watch"],
            "reapproach_limit": {k: p3b["reapproach_limit"][k] for k in ("fired", "by_cause")},
            "soil": {k: soil.get(k) for k in (
                "loc", "soil_mode", "t_P_s", "t_loc_s", "W_ratio", "bias_corner_m",
                "clearance_at_P_m", "clearance_at_loc_m", "soil_mode_t_s", "push_m")},
            "warnings": warn,
            "event_names": sorted(set(n.split(":")[0] for n in ev_names)),
            "track_utilisation_max": p3b["track_utilisation"]["max"],
            "checks": p3b["checks"],
        }
        print(case.name, "done", key, best[1] if best else None, flush=True)
    args.out_json.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
