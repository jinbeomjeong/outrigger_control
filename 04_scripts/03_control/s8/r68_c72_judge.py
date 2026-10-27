"""C-S8-72 Chrono batch: control-side judgement analysis (spec rev. 68, 348-353).

Reads the existing L2b batch records (no simulation) and the cad verdict file, and writes one
JSON with, per fast-event case:

* the F_min row re-computed independently of the judge (S8-A2 judged force = 1 ms
  ``F_cyl_min_interval``, 20 ms mean ``F_cyl_mean_20ms`` on ``airborne`` samples) after the
  U-S8-32 window end W, per leg: minimum, time below F_min, longest run below F_min, time below
  0, trailing 0.5 s mean minimum (full windows inside [W, end], G4-4 form of U-S8-72),
  airborne time and 1 ms pad normal minimum; difference to the verdict value (two paths);
* airborne runs after W with the pad ball rise (gap);
* diagonal rocking D = (F_FL + F_RR) - (F_FR + F_RL) half-cycle peaks, per-cycle damping, and
  the twist-mode actuator work 0.5 (D - D0)(n . ds_motor/dt) per 0.5 s bin (spec 248.3 form);
* the controller view around the worst minimum (10 Hz issued / re-approach / twist / attitude
  components, controller lower bound F_lower);
* harness (rev. 67 screen) vs Chrono on the same quantities: per event leg cumulative lift
  (U-S8-32 gate quantity), pair union (record), adjacent lift outside W, minimum after W;
* the rev. 67 harness screen recounted with the per-leg cumulative quantity.

Times relative to the event start [s], forces kN, gaps mm, work J. Usage (repo root)::

    python -I 04_scripts/03_control/s8/r68_c72_judge.py <batch> <verdict.json> <rev67 dir> <out.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
N_TW = np.array([0.476, -0.476, -0.523, 0.523])  # twist direction (spec 248.3)
F_MIN_KN = 9.41458911  # YAML control.F_min_cylinder_N / 1e3
MEAN_WINDOW_S = 0.5  # G4-4 (U-S8-72) trailing mean window
# case -> (event, leg, level, F_s kN, timing, phase offset s) of the matching harness run
HARNESS_KEY = {
    "G1L_RE1bF_FL_top_Fs0": ("RE1bF", "FL", "top", 0.0, "level", 0.05),
    "G1L_RE1bF_FR_top_Fs0": ("RE1bF", "FR", "top", 0.0, "level", 0.075),
    "G1L_FS24_FR_top_Fs0": ("FS24", "FR", "top", 0.0, "level", 0.025),
    "G1L_FS24_FL_top_Fs0": ("FS24", "FL", "top", 0.0, "level", 0.075),
    "G1L_RE1bF_FL_top_Fs8": ("RE1bF", "FL", "top", 8.0, "level", 0.0),
    "G1R_RE1bF_FL_top_Fs0": ("RE1bF", "FL", "top", 0.0, "ready", 0.0),
    "G1R_FS24_FL_top_Fs0": ("FS24", "FL", "top", 0.0, "ready", 0.025),
    "G1R_RE1bF_FR_top_Fs0": ("RE1bF", "FR", "top", 0.0, "ready", 0.075),
    "G1L_RE1bF_RL_top_Fs0": ("RE1bF", "RL", "top", 0.0, "level", 0.0),
    "G1L_RE1bF_FL_bottom_Fs0": ("RE1bF", "FL", "bottom", 0.0, "level", 0.0),
}


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    e = np.diff(np.concatenate(([0], mask.astype(int), [0])))
    return list(zip(np.flatnonzero(e == 1), np.flatnonzero(e == -1) - 1))


def verdict_info(verdict: dict) -> dict[str, dict]:
    info: dict[str, dict] = {}
    for r in verdict["rows"]:
        it, c = str(r["item"]), r["case"]
        if it.startswith("C-S8-72 U-S8-32 adjacent") and "split" in r:
            info.setdefault(c, {})["split"] = r["split"]
        elif it.startswith("C-S8-72 event state"):
            info.setdefault(c, {})["state"] = r["value"]
        elif it.startswith("C-S8-72 F_min"):
            info.setdefault(c, {})["fmin"] = {"value_kN": r["value"], "passed": r["passed"]}
        elif it.startswith("C-S8-72 record"):
            info.setdefault(c, {})["record"] = r["value"]
    return info


def case_analysis(d: Path, ci: dict) -> dict:
    t0 = float(json.loads((d / "result.json").read_text(encoding="utf-8"))["settings"]
               .get("start_t_s") or 0.0)
    z = np.load(d / "pads.npz")
    t = z["t"] - t0  # run clock (event_t_s is on it)
    dt = float(np.median(np.diff(t)))
    air = z["airborne"].astype(bool)
    fj = np.where(air, z["F_cyl_mean_20ms"], z["F_cyl_min_interval"]) / 1e3
    N = z["N"] / 1e3
    zb = z["ball_centre_world"][:, :, 2]
    t_ev = float(ci["state"]["event_t_s"])
    w_end = t_ev + float(ci["split"]["window_end_rel_s"])
    sel = t >= w_end - 1e-9
    tt = t[sel]
    nwin = int(round(MEAN_WINDOW_S / dt))
    legs = {}
    for j, leg in enumerate(LEGS):
        f = fj[sel, j]
        below = f < F_MIN_KN
        rb = _runs(below)
        c = np.concatenate(([0.0], np.cumsum(f)))
        mov = (c[nwin:] - c[:-nwin]) / nwin
        k = int(np.argmin(f))
        lifts = []
        for a, b in _runs(air[:, j] & sel):
            lifts.append({"from_rel_s": round(float(t[a] - t_ev), 3), "dur_s": round((b - a + 1) * dt, 3),
                          "gap_mm": round(float((zb[a:b + 1, j] - zb[a, j]).max() * 1e3), 2)})
        legs[leg] = {
            "min_kN": round(float(f[k]), 3), "t_min_rel_s": round(float(tt[k] - t_ev), 3),
            "below_Fmin_s": round(float(below.sum() * dt), 3), "below_runs": len(rb),
            "longest_below_s": round(max(((b - a + 1) * dt for a, b in rb), default=0.0), 3),
            "below_zero_s": round(float((f < 0).sum() * dt), 3),
            "mean05_min_kN": round(float(mov.min()), 2),
            "airborne_s": round(float(air[sel, j].sum() * dt), 3),
            "pad_N_min_kN": round(float(N[sel, j].min()), 3), "lifts_after_W": lifts}
    worst = min(legs, key=lambda L: legs[L]["min_kN"])
    # rocking and twist work
    F = z["F_cyl"] / 1e3
    D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    D0 = float(D[(t >= t_ev - 0.5) & (t < t_ev)].mean())
    P = 0.5 * (D - D0) * (np.gradient(z["s_motor"], dt, axis=0) @ N_TW) * 1e3  # W
    work = [round(float(P[(t >= t_ev + 0.5 * k) & (t < t_ev + 0.5 * (k + 1))].sum() * dt), 1)
            for k in range(16)]
    m = (t >= t_ev) & (t <= t_ev + 8.0)
    x, tr = D[m] - D0, t[m] - t_ev
    edges = np.concatenate(([0], np.flatnonzero(np.diff(np.sign(x)) != 0) + 1, [x.size]))
    peaks = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a >= 30:  # ignore sign chatter shorter than 30 ms
            k = a + int(np.argmax(np.abs(x[a:b])))
            peaks.append([round(float(tr[k]), 3), round(float(x[k]), 1)])
    zeta = [[peaks[i][0], round(float(np.log(abs(peaks[i][1]) / abs(peaks[i + 2][1])) / (2 * np.pi)), 3)]
            for i in range(len(peaks) - 2)
            if np.sign(peaks[i][1]) == np.sign(peaks[i + 2][1]) and peaks[i + 2][1] != 0]
    # controller around the worst minimum
    r8 = np.load(d / "r8_series.npz")
    tc = r8["t"] - t0
    tw = t_ev + legs[worst]["t_min_rel_s"]
    ctl = []
    for i in np.flatnonzero((tc >= tw - 1.6) & (tc <= tw + 0.35)):
        ctl.append({"t_rel_s": round(float(tc[i] - t_ev), 3), "phase": str(r8["phase"][i]),
                    "issued_mm_s": np.round(r8["issued_u"][i] * 1e3, 2).tolist(),
                    "reapproach_mm_s": np.round(r8["cmp_reapproach_u"][i] * 1e3, 2).tolist(),
                    "twist_mm_s": np.round(r8["cmp_twist_u"][i] * 1e3, 2).tolist(),
                    "attitude_mm_s": np.round(r8["cmp_attitude_u"][i] * 1e3, 2).tolist(),
                    "F_lower_kN": np.round(r8["F_lower_N"][i] / 1e3, 2).tolist()})
    fv = ci.get("fmin", {}).get("value_kN")
    return {"t_ev_s": t_ev, "W_end_rel_s": round(w_end - t_ev, 3), "legs": legs, "worst_leg": worst,
            "two_path_min_diff_kN": None if fv is None else float(legs[worst]["min_kN"] - fv),
            "D0_kN": round(D0, 2), "D_peaks_rel_s_kN": peaks[:24], "zeta_per_cycle": zeta[:20],
            "twist_work_J_per_0p5s": work, "controller_around_min": ctl}


def harness_runs(rev67: Path) -> list[tuple[str, dict, dict]]:
    out = []
    for name in ("r67_screen_P.json", "r67_screen_E.json", "r67_screen_top_phase4.json"):
        d = json.loads((rev67 / name).read_text(encoding="utf-8"))
        for job in d["results"]:
            for r in job.get("runs") or []:
                out.append((name, job, r))
    return out


def harness_compare(case: str, ci: dict, ca: dict, runs) -> dict | None:
    ev, leg, level, fs, timing, off = HARNESS_KEY[case]
    m = [(n, r) for n, j, r in runs if r.get("event") == ev and j["leg"] == leg and j["level"] == level
         and abs(j["fs_kN"] - fs) < 1e-6 and j["timing"] == timing and abs(r.get("offset_s", -1.0) - off) < 1e-6]
    if not m:
        return None
    n, r = m[0]
    pair = (leg, DIAG[leg])
    h_perleg = max(float(r.get("lifts", {}).get(x, {}).get("sum_s", 0.0)) for x in pair)
    c_perleg = max(float(ci["split"]["cum_lift_s"][x]) for x in pair)
    hmin = r["min_F_after_W_kN"]
    hw = min(hmin, key=hmin.get)
    c_union = float(ci["record"]["event_pair_union_s"])
    return {"harness_file": n,
            "perleg_cum_s": [round(h_perleg, 3), round(c_perleg, 3), round(h_perleg / c_perleg, 3)],
            "pair_union_s": [r["pair_union_s"], round(c_union, 3), round(r["pair_union_s"] / c_union, 3)],
            "harness_union_over_chrono_perleg": round(r["pair_union_s"] / c_perleg, 3),
            "last_touch_s": [r["pair_last_touch_s"], ci["split"]["event_recontact_max_rel_s"]],
            "adj_outside_W_s": [r["adj_lift_outside_W_s"], ci["split"]["adjacent_outside_window_s"]],
            "min_after_W_kN": [[hw, hmin[hw]], [ca["worst_leg"], ca["legs"][ca["worst_leg"]]["min_kN"]]],
            "late_starts": [r.get("n_late_starts"), ci["record"].get("starts_after_1.5_s")]}


def recount(runs) -> dict:
    """Rev. 67 screen fast runs with the per-leg event quantity; F_min failures split into
    'contact' (min after W > -0.5 kN: pad kept, harness F = N - m g) and 'lift'."""
    out: dict[str, dict] = {}
    for group, files in (("main_192", {"r67_screen_P.json", "r67_screen_E.json"}),
                         ("top_phase4_192", {"r67_screen_top_phase4.json"})):
        cnt, fails = Counter(), Counter()
        for n, job, r in runs:
            if n not in files or not str(job.get("key", "")).startswith("screen") or not r.get("fast"):
                continue
            key = f"{job['timing']}|{r['event']}"
            cnt[key] += 1
            leg = job["leg"]
            perleg = max(float(r.get("lifts", {}).get(x, {}).get("sum_s", 0.0)) for x in (leg, DIAG[leg]))
            g = r["gates"]
            tags = []
            if not (perleg <= 1.8 + 1e-9 and r["pair_last_touch_s"] <= 3.0 + 1e-9 and g.get("fault0", True)):
                tags.append("event_leg")
            if not (r["adj_lift_sum_W_s"] <= 0.5 + 1e-9 and r["adj_max_gap_W_mm"] <= 2.0 + 1e-9
                    and r["adj_lift_outside_W_s"] == 0):
                tags.append("u57")
            mw = min(r["min_F_after_W_kN"].values())
            if mw < F_MIN_KN:
                tags.append("Fmin_contact" if mw > -0.5 else "Fmin_lift")
            if not g.get("recurrence", True):
                tags.append("recurrence")
            if not g.get("end_att", True):
                tags.append("end_att")
            if tags:
                fails[key] += 1
                for x in tags:
                    fails[key + "|" + x] += 1
        out[group] = {k: {"runs": cnt[k], "failed_runs": fails.get(k, 0),
                          "by_row": {kk.split("|")[2]: v for kk, v in fails.items()
                                     if kk.count("|") == 2 and kk.startswith(k + "|")}}
                      for k in sorted(cnt)}
    return out


def main() -> None:
    batch, verdict_p, rev67, out_p = (Path(a) for a in sys.argv[1:5])
    verdict = json.loads(verdict_p.read_text(encoding="utf-8"))
    info = verdict_info(verdict)
    runs = harness_runs(rev67)
    res: dict = {"meta": {"batch": str(batch), "verdict": str(verdict_p), "F_min_kN": F_MIN_KN,
                          "spec": "s6_control_spec.md rev. 68 (348-353)"}, "cases": {}}
    for case, ci in sorted(info.items()):
        if "split" not in ci:
            continue
        ca = case_analysis(batch / case, ci)
        if case in HARNESS_KEY:
            ca["harness_vs_chrono"] = harness_compare(case, ci, ca, runs)
        res["cases"][case] = ca
        L = ca["legs"][ca["worst_leg"]]
        print(f"{case:26s} W+{ca['W_end_rel_s']:.3f} worst {ca['worst_leg']} min {L['min_kN']:7.3f} "
              f"(diff {ca['two_path_min_diff_kN']}) below {L['below_Fmin_s']:.3f} s longest "
              f"{L['longest_below_s']:.3f} mean0.5 {L['mean05_min_kN']:.2f} air {L['airborne_s']:.3f} "
              f"Nmin {L['pad_N_min_kN']:.2f}")
    res["harness_recount_perleg"] = recount(runs)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("recount:", json.dumps(res["harness_recount_perleg"], ensure_ascii=False))
    print("wrote", out_p)


if __name__ == "__main__":
    main()
