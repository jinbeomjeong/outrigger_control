"""Independent re-implementation of the E-2 signature (rules draft r11, section 4.2.1) on the public
A2 check-run T4h records, under two definitions:

  impl : the candidate implementation as described in r11 4.2.1 (any >= 1 inclinometer reading in the
         (iv) window is enough; the (vi) window past the record end is read as 'no event')
  r11  : the two r11 changes adopted by the user (n == 21 readings in the (iv) window, else
         not evaluable; t_L + 0.5 s after t_s[-1] -> not evaluable)

No project module is imported. Inputs are the public check runs used by the rules only as
interpretation aids (r11 section 1 last bullet). Also reports, for every control cycle of every
record, how many inclinometer readings fall in a +-0.1 s window (grid alignment check for n == 21),
and the time from the last READY entry / t_L to the record end.

Usage: python -I -B e2_def_check.py <A2 T4h folder> <R0 T4h folder> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

TOL = 1e-9
WIN_INCL = 0.1
N_INCL = 21
EV_PRE = ("relevel_predicted", "probe_aborted_low_load", "WARN_SUPPORT_CHANGED", "target_changed")
EV_REAP = ("leg_reapproach_start",)
POSITIVE = {"S3_e0.0_VB-eta0.85", "S3_e0.002_VB-eta0.85", "S5_e0.001_VB-eta0.8",
            "S5_e0.002_VB-eta0.8", "S4_e0.0_VB"}
E2_ARRAYS = ("attitude_filtered_deg", "attitude_true_rad", "inclinometer_t_s", "inclinometer_rad",
             "attitude_true_at_inclinometer_rad", "true_force_min_N")


def entries(phase: np.ndarray, name: str) -> list[int]:
    return [k for k in range(len(phase)) if phase[k] == name and (k == 0 or phase[k - 1] != name)]


def classify(z, meta: dict, variant: str) -> dict:
    t = np.asarray(z["t_s"], float)
    ph = np.asarray(z["phase"]).astype(str)
    rec: dict = {"variant": variant}
    ready = entries(ph, "ready")
    if not ready:
        return rec | {"result": "not_target", "why": "no READY entry"}
    k_r = ready[-1]
    k_l = next((k for k in range(k_r + 1, len(ph)) if ph[k - 1] == "ready" and ph[k] == "level"), None)
    if k_l is None:
        return rec | {"result": "not_target", "why": "no READY->LEVEL after last READY entry"}
    t_r, t_l = float(t[k_r]), float(t[k_l])
    rec |= {"t_R": t_r, "t_L": t_l, "t_end": float(t[-1]), "end_minus_tL": float(t[-1] - t_l)}
    if any(a not in z.files for a in E2_ARRAYS):
        return rec | {"result": "not_evaluable", "why": "array missing"}
    dones = [k for k in entries(ph, "done") if k <= k_r]
    if not dones:
        return rec | {"result": "not_evaluable", "why": "no DONE"}
    k_d = dones[-1]
    t_d = float(t[k_d])
    rec["t_D"] = t_d
    f_min = float(meta["F_min_N"])
    att_f = np.asarray(z["attitude_filtered_deg"], float)
    att_t = np.asarray(z["attitude_true_rad"], float)
    ti = np.asarray(z["inclinometer_t_s"], float)
    inc = np.asarray(z["inclinometer_rad"], float)
    inc_t = np.asarray(z["attitude_true_at_inclinometer_rad"], float)
    fmin = np.asarray(z["true_force_min_N"], float)
    gap = t_l - t_r
    c1 = (0.3 - TOL) <= gap <= (3.0 + TOL)
    v2 = float(np.max(np.abs(att_f[k_l])))
    v3 = float(np.degrees(np.max(np.abs(att_t[k_r] - att_t[k_d]))))
    win = np.abs(ti - t_l) <= WIN_INCL + TOL
    n = int(win.sum())
    err = np.degrees(np.abs(inc[win] - inc_t[win])) if n else np.zeros((0, 2))
    v4 = float(err.max()) if n else float("nan")
    v5 = float(np.min(fmin[k_r:k_l + 1]))
    ev = meta.get("events") or []
    hits = [(float(te), str(nm)) for te, nm in ev
            if ((t_r - 0.5 - TOL) <= float(te) <= (t_l + 0.5 + TOL) and str(nm).startswith(EV_PRE))
            or ((t_d - TOL) <= float(te) <= (t_l + 0.5 + TOL) and str(nm).startswith(EV_REAP))]
    rec |= {"gap_s": gap, "ii_filt_deg": v2, "iii_true_change_deg": v3, "iv_n": n, "iv_err_max_deg": v4,
            "v_force_min_N": v5, "vi_hits": hits, "vi_window_past_end": bool(t_l + 0.5 > t[-1] + TOL)}
    nan_vals = [not np.isfinite(x) for x in (v2, v3, v5)] + ([bool(np.isnan(err).any())] if n else [])
    if any(nan_vals):
        return rec | {"result": "not_evaluable", "why": "NaN"}
    if variant == "r11":
        if n != N_INCL:
            return rec | {"result": "not_evaluable", "why": f"iv n={n}"}
        if rec["vi_window_past_end"]:
            return rec | {"result": "not_evaluable", "why": "vi window past record end"}
    conds = {"i": c1, "ii": v2 >= 0.065, "iii": v3 >= 0.05, "iv": n >= 1 and v4 <= 0.03,
             "v": v5 >= f_min + 7500.0, "vi": not hits}
    rec["conds"] = conds
    return rec | {"result": "holds" if all(conds.values()) else "fails"}


def window_counts(z) -> Counter:
    t = np.asarray(z["t_s"], float)
    ti = np.asarray(z["inclinometer_t_s"], float)
    lo = np.searchsorted(ti, t - WIN_INCL - TOL, side="left")
    hi = np.searchsorted(ti, t + WIN_INCL + TOL, side="right")
    return Counter((hi - lo).tolist())


def end_gaps(folder: Path) -> dict:
    gaps = []
    for f in sorted(folder.glob("*.npz")):
        z = np.load(f, allow_pickle=False)
        ph = np.asarray(z["phase"]).astype(str)
        t = np.asarray(z["t_s"], float)
        r = entries(ph, "ready")
        if r:
            gaps.append(float(t[-1] - t[r[-1]]))
    g = np.asarray(gaps)
    return {"files_with_ready": int(g.size), "end_minus_last_ready_entry_s":
            {"min": float(g.min()), "p10": float(np.percentile(g, 10)), "median": float(np.median(g)),
             "max": float(g.max())} if g.size else None}


def main(a2_dir: str, r0_dir: str, out: str) -> int:
    a2 = Path(a2_dir)
    res, counts, shas = {}, Counter(), {}
    edge = Counter()
    for f in sorted(a2.glob("*.npz")):
        shas[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        z = np.load(f, allow_pickle=False)
        meta = json.loads(str(z["meta_json"]))
        res[f.stem] = {v: classify(z, meta, v) for v in ("impl", "r11")}
        wc = window_counts(z)
        t = np.asarray(z["t_s"], float)
        counts.update(wc)
        # cycles at least 0.1 s away from both record ends must all have 21 readings
        ti = np.asarray(z["inclinometer_t_s"], float)
        inner = (t - WIN_INCL >= ti[0] - TOL) & (t + WIN_INCL <= ti[-1] + TOL)
        lo = np.searchsorted(ti, t - WIN_INCL - TOL, side="left")
        hi = np.searchsorted(ti, t + WIN_INCL + TOL, side="right")
        edge.update((hi - lo)[inner].tolist())
    targets = {k: v for k, v in res.items() if v["impl"]["result"] != "not_target"}
    summary = {
        "files": len(res), "e2_targets": sorted(targets),
        "positives_expected": sorted(POSITIVE),
        "impl_holds": sorted(k for k, v in res.items() if v["impl"]["result"] == "holds"),
        "r11_holds": sorted(k for k, v in res.items() if v["r11"]["result"] == "holds"),
        "changed_by_r11": {k: [v["impl"]["result"], v["r11"]["result"], v["r11"].get("why")]
                           for k, v in res.items() if v["impl"]["result"] != v["r11"]["result"]},
        "positives_match_impl": sorted(POSITIVE) == sorted(k for k, v in res.items()
                                                           if v["impl"]["result"] == "holds"),
        "positives_match_r11": sorted(POSITIVE) == sorted(k for k, v in res.items()
                                                          if v["r11"]["result"] == "holds"),
        "incl_window_counts_all_cycles": dict(sorted(counts.items())),
        "incl_window_counts_inner_cycles": dict(sorted(edge.items())),
        "targets_end_minus_tL_s": {k: v["impl"].get("end_minus_tL") for k, v in targets.items()},
        "a2_end_gaps": end_gaps(a2), "r0_end_gaps": end_gaps(Path(r0_dir)),
    }
    Path(out).write_text(json.dumps({"summary": summary, "per_file": res, "sha16": shas}, indent=1,
                                    ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "ok", "positives_match_impl": summary["positives_match_impl"],
                      "positives_match_r11": summary["positives_match_r11"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
