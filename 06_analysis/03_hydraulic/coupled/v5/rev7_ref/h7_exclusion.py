"""H-7 follow-up (stage 3, criteria rev. 6 4.3/4.4): apply a proposed exclusion rule and a
sensor-error decomposition to the stored rigid stage 3 records. Read only (no Chrono rerun, no
repository edit; repository modules are imported read only).

Exclusion E (all must hold, per leg and 10 Hz sample k):
  E1 phase[k] == "check"
  E2 k < first calibrated row of that leg (PRESSURE_ZERO_CALIBRATED:<leg> + 1 row)
  E3 law_locked[k] == 0 (tail: lock not closed)
  E4 airborne[k] (pads.npz truth)
  E5 last nonzero acting command of the leg before k is a retraction
Validity guard (checked on every excluded sample, reported): forced lower + seal band < F_min
and truth + seal band < F_min (both BELOW in classify_load), forced lower < 0.

Sensor-error rows (result.bundle_c.sensor_model true): fallback-own excess
  e_own = lower - F_p - max(plain - F_p, 0), plain = replay without any fallback.

Usage (dynamics-dev, project root cwd not needed):
  python -I -B h7_exclusion.py <out_json> [--workers 4]
"""
import argparse
import copy
import json
import sys
from multiprocessing import get_context
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
COUPLED = ROOT / "04_scripts/04_hydraulic/coupled"
S8 = ROOT / "07_results/S8"
LIMIT_N = 600.0
T45_ROWS = {"VB": ("K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0", "K0_top_fdown3.2_Fs0",
                   "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0", "E_RE1bF_Fs0", "E_RE1bF_Fs8",
                   "K8_top_rpB_Fs8", "S_top_fdown3.5_wika_Fs8", "K8_top_fdown3.5_Fs8"),
            "LS1": ("K0V_top_fup3.5_Fs0", "E_G4_Fs8", "E_RE1bF_Fs8"),
            "LS4": ("K0V_top_fup3.5_Fs0", "E_G4_Fs8", "E_RE1bF_Fs8")}


def cases():
    out = []
    for folder in sorted(S8.glob("v5s3_*")):
        setting = folder.name.split("_")[1]
        for d in sorted(p for p in folder.iterdir() if p.is_dir() and (p / "result.json").exists()):
            out.append((str(d), setting, d.name in T45_ROWS.get(setting, ())))
    return out


def last_motion_retract(acting):
    """(n, 4) bool: the last nonzero acting command before row k (inclusive of k-1) is < 0."""
    n, legs = acting.shape
    out = np.zeros((n, legs), bool)
    for leg in range(legs):
        last = 0.0
        for k in range(n):
            out[k, leg] = last < 0.0
            if acting[k, leg] != 0.0:
                last = acting[k, leg]
    return out


def stats(mask_judged, excess):
    sel = excess[mask_judged]
    return {"n": int(mask_judged.sum()), "over": int((sel > LIMIT_N).sum()),
            "max_kN": None if sel.size == 0 else float(sel.max()) / 1e3}


def work(item):
    case_dir, setting, judged_row = item
    for p in (COUPLED, ROOT / "03_src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import chrono_t45_replay as t45
    from outrigger_sim.control.contact_replay import _calibration_rows

    out = {"case": Path(case_dir).name, "setting": setting, "judged_T45": judged_row}
    for key, rule in (("off", None), ("on", "tracked_bound")):
        rec = t45.load_case(Path(case_dir), rule)
        t = np.asarray(rec.episode["t_s"], float)
        phase = np.asarray(rec.episode["phase"]).astype(str)
        band = np.asarray(rec.episode["seal_band_N"], float)
        if band.ndim == 1:
            band = np.repeat(band[:, None], 4, axis=1)
        f_min = float(rec.geometry.F_min_N)
        forced = t45._replay(rec, t45.forced_events(rec, {leg: t[0] for leg in range(4)}))
        plain = t45._replay(rec, t45._without_fallback(rec.events))
        judged = t45._judged(rec)
        cal_rows = _calibration_rows(rec.events, t, rec.config.period_s)
        rows = np.arange(t.size)[:, None]
        retract = last_motion_retract(rec.acting_m_s)
        e1 = (phase == "check")[:, None] & np.ones((1, 4), bool)
        e2 = rows < cal_rows[None, :]
        e3 = rec.law_state == 0
        e4 = rec.airborne
        excl = judged & e1 & e2 & e3 & e4 & retract
        excl_no_e5 = judged & e1 & e2 & e3 & e4
        check_pre = judged & e1 & e2
        # sensor-error rows: result.json settings.bundle_c.sensor_model (fixed 2026-11-08; was top level)
        sensor = bool((((rec.result.get("settings") or {}).get("bundle_c") or {}).get("sensor_model")))
        truth = rec.truth_N
        ex = forced - truth
        plain_ex = plain - truth
        own = ex - np.maximum(plain_ex, 0.0)
        res = {"sensor_model": sensor, "cal_rows_t_s": [float(t[min(r, t.size - 1)]) for r in cal_rows],
               "F_min_kN": f_min / 1e3,
               "T4_before": stats(judged, ex), "T4_after": stats(judged & ~excl, ex),
               "excluded": int(excl.sum()), "excluded_no_E5": int(excl_no_e5.sum()),
               "judged_check_precal": int(check_pre.sum()),
               "judged_check_precal_grounded": int((check_pre & ~e4).sum()),
               "judged_check_precal_locked": int((check_pre & ~e3).sum()),
               "excluded_over": int((excl & (ex > LIMIT_N)).sum()),
               "over_outside_excl": int((judged & ~excl & (ex > LIMIT_N)).sum())}
        if excl.any():
            fx, tr, bd = forced[excl], truth[excl], band[excl]
            res["guard"] = {"forced_max_kN": float(fx.max()) / 1e3, "truth_max_kN": float(tr.max()) / 1e3,
                            "forced_plus_band_max_kN": float((fx + bd).max()) / 1e3,
                            "truth_plus_band_max_kN": float((tr + bd).max()) / 1e3,
                            "all_below_band": bool(np.all(fx + bd < f_min) and np.all(tr + bd < f_min)),
                            "all_forced_negative": bool(np.all(fx < 0.0)),
                            "excess_max_kN": float(ex[excl].max()) / 1e3,
                            "t_range_s": [float(t[np.nonzero(excl)[0]].min()), float(t[np.nonzero(excl)[0]].max())]}
        if sensor:
            res["T4_own_after"] = stats(judged & ~excl, own)
            res["T4_plain_after"] = stats(judged & ~excl, plain_ex)
        # leg detail for the over samples that remain
        rem = judged & ~excl & (ex > LIMIT_N)
        res["remaining_over"] = [{"leg": t45.LEGS[leg], "t_s": float(t[k]), "phase": phase[k],
                                  "law": int(rec.law_state[k, leg]), "excess_kN": float(ex[k, leg]) / 1e3,
                                  "own_kN": float(own[k, leg]) / 1e3}
                                 for k, leg in zip(*np.nonzero(rem))]
        # T5 for the judged rows with F_s 8 (the only rows with T5 over before) and the off path only
        if key == "off" and judged_row and "Fs8" in out["case"]:
            stepper = t45._MonitorStepper(rec, rec.events)
            states = []
            for row in range(len(stepper.t_s)):
                states.append(copy.deepcopy(stepper.monitor))
                stepper.step(row)
            t5 = {"units": 0, "before_over": 0, "after_over": 0, "before_max_kN": -np.inf,
                  "after_max_kN": -np.inf, "excluded_samples": 0, "own_after_over": 0,
                  "own_after_max_kN": -np.inf, "after_over_list": []}
            for leg in range(4):
                for first, last in t45.command_free_stretches(rec.acting_m_s[:, leg]):
                    for start in range(first, last + 1):
                        lower = t45._stepped_lower(stepper, states[start], leg, start, last)
                        t5["units"] += 1
                        for row in range(start, last + 1):
                            if not judged[row, leg]:
                                continue
                            e = lower[row - start] - truth[row, leg]
                            t5["before_over"] += int(e > LIMIT_N)
                            t5["before_max_kN"] = max(t5["before_max_kN"], e / 1e3)
                            if excl[row, leg]:
                                t5["excluded_samples"] += 1
                                continue
                            t5["after_over"] += int(e > LIMIT_N)
                            t5["after_max_kN"] = max(t5["after_max_kN"], e / 1e3)
                            if sensor:
                                o = e - max(plain_ex[row, leg], 0.0)
                                t5["own_after_over"] += int(o > LIMIT_N)
                                t5["own_after_max_kN"] = max(t5["own_after_max_kN"], o / 1e3)
                            if e > LIMIT_N:
                                t5["after_over_list"].append(
                                    {"leg": t45.LEGS[leg], "start_t_s": float(t[start]), "t_s": float(t[row]),
                                     "phase": phase[row], "law": int(rec.law_state[row, leg]),
                                     "excess_kN": e / 1e3, "own_kN": (e - max(plain_ex[row, leg], 0.0)) / 1e3})
            for k in ("before_max_kN", "after_max_kN", "own_after_max_kN"):
                t5[k] = None if t5[k] == -np.inf else float(t5[k])
            res["T5"] = t5
        out[key] = res
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default=None, help="substring of case names to run")
    a = ap.parse_args()
    items = [c for c in cases() if a.only is None or a.only in Path(c[0]).name]
    print(len(items), "cases", flush=True)
    rows = []
    with get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(work, items):
            rows.append(r)
            o = r["off"]
            print(r["setting"], r["case"], "T4", o["T4_before"]["over"], "->", o["T4_after"]["over"],
                  "excl", o["excluded"], "T5", (o.get("T5") or {}).get("before_over"), "->",
                  (o.get("T5") or {}).get("after_over"), flush=True)
    Path(a.out_json).write_text(json.dumps({"rows": rows}, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
