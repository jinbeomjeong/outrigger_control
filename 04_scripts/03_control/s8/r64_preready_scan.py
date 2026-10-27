"""Rev. 64 (b)-2 / (b)-3: head-pressure steps before the first READY and crawler re-contact.

For every 10 Hz case folder under the given roots (record/record.npz):
  * the one-period change of the head reading (``meas.head_pressure``, what the monitor sees),
    steps > 50 bar and > 100 bar, before / after the first READY (r8 ``phase``, else
    ``t_ready_s`` of result.json; ML episodes start in READY and have no "before");
  * for each step > 50 bar the D1' sum ratio |d sum F| / (|dp_h| A_p) and the D1'' ratio
    |d(sum F - M f_z)| / (|dp_h| A_p) for three masses: the YAML mass, the LOC weight W_hat / g
    (mean reading sum over the 1 s before ``crawler_liftoff_confirmed``) and the first-READY
    median sum F / f_z; plus the crawler load at the step;
  * crawler re-contact: crawler normal force > 2 kN after the LOC (else after the first
    READY), first time and maximum.
Usage: python -I r64_preready_scan.py <out_json> <workers> <root> [<root> ...]
Read only; no random numbers.
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r64_common import (A_P, G, LEGS, YAML_MASS_KG, case_dirs, events, find_key,  # noqa: E402
                        imu_fz, load_json, net_sum_N, phase_names)

BAR = 1e5
RECONTACT_N = 2000.0


def scan(case: Path) -> dict:
    out: dict = {"case": str(case)}
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    t = np.asarray(rec["t"], float)
    if len(t) < 3:
        return {**out, "skip": "short"}
    dt = float(np.median(np.diff(t)))
    out["dt"] = round(dt, 4)
    if abs(dt - 0.1) > 1e-3:
        return {**out, "skip": f"dt {dt:.3f}"}
    r8 = np.load(case / "r8_series.npz", allow_pickle=True) if (case / "r8_series.npz").exists() else None
    result = load_json(case / "result.json")
    ev = events(case, result)
    ph = phase_names(r8)
    if ph is not None and len(ph) != len(t):
        ph = None
    t_ready = None
    starts_ready = False
    if ph is not None:
        idx = np.flatnonzero(ph == "READY")
        t_ready = float(t[idx[0]]) if len(idx) else None
        starts_ready = bool(ph[0] == "READY")
    elif result is not None:
        v = find_key(result, "t_ready_s")
        t_ready = float(v) if isinstance(v, (int, float)) else None
    t_loc = next((ts for ts, n in ev if n.startswith("crawler_liftoff_confirmed")), None)
    out.update(t_ready=t_ready, starts_in_ready=starts_ready, t_loc=t_loc)
    head = np.asarray(rec["meas.head_pressure"], float)
    rod = np.asarray(rec["meas.rod_pressure"], float)
    ssum = net_sum_N(head, rod)
    fz = imu_fz(r8, rec)
    crawler = np.asarray(rec["F_crawler"], float)
    crawler_n = np.abs(crawler[:, 2]) if crawler.ndim == 2 and crawler.shape[1] >= 3 else np.zeros(len(t))
    # candidate masses
    masses = {"yaml": YAML_MASS_KG}
    if t_loc is not None:
        w_hat = find_key(result, "weight_estimate_N") if result is not None else None
        if isinstance(w_hat, (int, float)) and w_hat > 0:
            masses["loc"] = float(w_hat) / G  # the controller's S-5 W_hat
            out["loc_mass_source"] = "controller W_hat"
        else:
            w = (t > t_loc - 1.0 - 1e-9) & (t <= t_loc + 1e-9)
            if w.any():
                masses["loc"] = float(np.mean(ssum[w]) / G)
                out["loc_mass_source"] = "record 1 s mean"
    if t_ready is not None:
        ready = (ph == "READY") if ph is not None else (t >= t_ready)
        first = np.flatnonzero(ready)
        if len(first):
            stay = first[: max(3, min(len(first), 600))]
            ok = fz[stay] > 0
            if ok.sum() >= 3:
                masses["ready"] = float(np.median(ssum[stay][ok] / fz[stay][ok]))
    out["masses_kg"] = masses
    dph = np.diff(head, axis=0) / BAR
    steps = []
    for k, leg in zip(*np.nonzero(np.abs(dph) > 50.0)):
        i = k + 1
        before_ready = (not starts_ready) and (t_ready is None or t[i] < t_ready - 1e-9)
        jforce = abs(dph[k, leg]) * BAR * A_P[leg]
        row = {"t": round(float(t[i]), 2), "leg": LEGS[leg], "dp_bar": round(float(dph[k, leg]), 1),
               "phase": None if ph is None else str(ph[i]), "before_ready": bool(before_ready),
               "after_loc": bool(t_loc is not None and t[i] >= t_loc),
               "crawler_kN": round(float(crawler_n[i]) / 1e3, 1),
               "crawler_prev_kN": round(float(crawler_n[i - 1]) / 1e3, 1),
               "ratio_sum": round(float(abs(ssum[i] - ssum[i - 1]) / jforce), 3)}
        for name, m in masses.items():
            r = abs((ssum[i] - m * fz[i]) - (ssum[i - 1] - m * fz[i - 1])) / jforce
            row[f"ratio_imu_{name}"] = round(float(r), 3)
        steps.append(row)
    out["steps50"] = steps
    out["n_pre100"] = sum(1 for s in steps if s["before_ready"] and abs(s["dp_bar"]) > 100)
    out["n_pre50"] = sum(1 for s in steps if s["before_ready"])
    out["n_post100"] = sum(1 for s in steps if not s["before_ready"] and abs(s["dp_bar"]) > 100)
    pre = (~np.zeros(len(t), bool)) if t_ready is None else (t < t_ready - 1e-9)
    if starts_ready:
        pre[:] = False
    out["max_pre_step_bar"] = round(float(np.abs(dph[pre[1:]]).max()), 1) if pre[1:].any() else None
    # crawler re-contact
    ref = t_loc if t_loc is not None else t_ready
    if ref is not None and not starts_ready:
        after = t > ref + 1.0
        hit = after & (crawler_n > RECONTACT_N)
        out["recontact"] = None if not hit.any() else {
            "t_first": round(float(t[np.flatnonzero(hit)[0]]), 2),
            "max_kN": round(float(crawler_n[after].max()) / 1e3, 1),
            "samples": int(hit.sum()), "ref": "loc" if t_loc is not None else "ready"}
    elif starts_ready:
        hit = crawler_n > RECONTACT_N
        out["recontact"] = None if not hit.any() else {
            "t_first": round(float(t[np.flatnonzero(hit)[0]]), 2),
            "max_kN": round(float(crawler_n.max()) / 1e3, 1), "samples": int(hit.sum()),
            "ref": "episode_start"}
    return out


def safe(case: Path) -> dict:
    try:
        return scan(case)
    except Exception as exc:  # report, continue
        return {"case": str(case), "skip": f"error {exc!r}"}


def main() -> None:
    out_path, workers, roots = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    cases = list(case_dirs(roots))
    with Pool(workers) as pool:
        rows = pool.map(safe, cases, chunksize=4)
    used = [r for r in rows if "skip" not in r]
    skipped = [r for r in rows if "skip" in r]
    pre_rows = [r for r in used if not r["starts_in_ready"]]
    summary = {
        "cases": len(rows), "used": len(used), "skipped": len(skipped),
        "skip_reasons": sorted({r["skip"].split(" ")[0] for r in skipped}),
        "full_runs": len(pre_rows),
        "full_runs_with_ready": sum(r["t_ready"] is not None for r in pre_rows),
        "full_runs_with_loc": sum(r["t_loc"] is not None for r in pre_rows),
        "pre_ready_steps_gt100": sum(r["n_pre100"] for r in used),
        "pre_ready_steps_gt50": sum(r["n_pre50"] for r in used),
        "pre_ready_runs_gt100": [r["case"] for r in used if r["n_pre100"]],
        "max_pre_ready_step_bar": max((r["max_pre_step_bar"] or 0) for r in pre_rows) if pre_rows else None,
        "post_ready_steps_gt100": sum(r["n_post100"] for r in used),
        "recontact_runs": [{"case": r["case"], **r["recontact"]} for r in used if r.get("recontact")],
    }
    steps_pre = [dict(case=r["case"], **s) for r in used for s in r["steps50"] if s["before_ready"]]
    steps_post100 = [dict(case=r["case"], **s) for r in used for s in r["steps50"]
                     if not s["before_ready"] and abs(s["dp_bar"]) > 100]
    for name in ("sum", "imu_yaml", "imu_loc", "imu_ready"):
        key = f"ratio_{name}"
        for label, rows_ in (("pre50", steps_pre), ("post100", steps_post100)):
            vals = [s[key] for s in rows_ if key in s]
            summary[f"{label}_{key}_max"] = max(vals) if vals else None
            summary[f"{label}_{key}_ge0p5"] = sum(v >= 0.5 for v in vals)
            summary[f"{label}_{key}_n"] = len(vals)
    mass = [r["masses_kg"] for r in pre_rows]
    for name in ("loc", "ready"):
        vals = [m[name] for m in mass if name in m]
        if vals:
            summary[f"mass_{name}_kg_min_max"] = [round(min(vals), 1), round(max(vals), 1)]
            summary[f"mass_{name}_n"] = len(vals)
    pairs = [(m["loc"], m["ready"]) for m in mass if "loc" in m and "ready" in m]
    if pairs:
        d = [(a - b) / b for a, b in pairs]
        summary["mass_loc_vs_ready_rel_min_max"] = [round(min(d), 4), round(max(d), 4)]
    Path(out_path).write_text(json.dumps({"summary": summary, "steps_pre_ready_gt50": steps_pre,
                                          "steps_post_ready_gt100": steps_post100,
                                          "skipped": skipped,
                                          "runs": [{k: v for k, v in r.items() if k != "steps50"}
                                                   for r in used]},
                                         indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
