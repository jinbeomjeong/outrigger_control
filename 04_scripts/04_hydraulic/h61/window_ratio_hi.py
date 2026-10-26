"""H-61-1 (1): secant ratio -dp_r/dp_h over n controller periods (0.1 s) on locked L2b legs.

Records only (read only): 1 ms pads.npz truth sampled at the 10 Hz record instants
(searchsorted), and the 10 Hz controller readings meas.*.

For every window [t_{k-n}, t_k] fully inside one 1 ms lock run (s_ref constant, skip 5 ms after
the lock step), rod pressure above floor + 1 bar at both ends:
    R_sec   = -(p_r(k) - p_r(k-n)) / (p_h(k) - p_h(k-n))        (truth)
    R_model = (L0h + s_lock) / (L0r + s_max - s_lock)            (static column ratio)
    excess  = A_ann * (-(dp_r) - R_model * (-dp_h))              [N]  rod-term excess over static
Head pressure truth in L2b = (F_p + p_r A_ann) / A_p with F_p containing the locked dashpot
c (u - ds/dt) (l2b_actuator law); the rod law uses the spring part only. A second head series
removes the dashpot term:  p_h,spring = p_h + c_lock * ds_link/dt / A_p  (u = 0 while locked).

Usage: python -I window_ratio.py <out.json> <batch_dir> [...]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
S_MAX = 0.7
FLOOR_G = 1.0e4 - 1.01325e5
A_P = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_R = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
BINS = [(0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 1e9)]
NS = (1, 3)


def find_cases(batch: Path):
    for p in sorted(batch.rglob("pads.npz")):
        c = p.parent
        if (c / "record" / "meta.json").exists():
            yield c


def lock_runs(sm):
    still = np.abs(np.diff(sm)) <= 1.0e-9
    locked = np.r_[False, still]
    idx = np.flatnonzero(locked)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]]
    return [(int(a), int(b)) for a, b in zip(starts, ends, strict=True) if b - a >= 200]


def analyse(c: Path):
    meta = json.loads((c / "record" / "meta.json").read_text(encoding="utf-8"))
    act = meta.get("run", {}).get("engine", {}).get("actuator", {})
    s8 = act.get("s8") if isinstance(act.get("s8"), dict) else {}
    law = (s8 or {}).get("oil_law") or act.get("rod_side")
    if not isinstance(law, dict) or law.get("mechanics") != "one_sided_parallel":
        return None
    damp = np.array(act.get("damping_locked_N_s_m", [np.nan] * 4), float)
    l0h = float(law["head_dead_length_m"])
    l0r = np.array(law["rod_dead_length_m"], float)
    fs = 0.0
    if s8 and isinstance(s8.get("seal_friction"), dict):
        fs = float(max(s8["seal_friction"].get("limits_N", [0.0])))
    lock_valve = (s8 or {}).get("lock_valve", "pilot_check")
    beta = float(act.get("bulk_modulus_Pa", math.nan))
    with np.load(c / "pads.npz", allow_pickle=True) as z:
        t = z["t"]
        ph, pr, sm, sl = z["head_pressure"], z["rod_pressure"], z["s_motor"], z["s_link"]
    with np.load(c / "record" / "record.npz", allow_pickle=True) as z:
        tr = z["t"]
        mh, mr = z["meas.head_pressure"], z["meas.rod_pressure"]
    dt = np.gradient(t)
    vlink = np.gradient(sl, axis=0) / dt[:, None]
    j = np.clip(np.searchsorted(t, tr - 1e-9), 0, t.size - 1)
    ok_t = np.abs(t[j] - tr) < 6e-4
    rows = []
    for leg in range(4):
        runs = lock_runs(sm[:, leg])
        run_id = np.full(t.size, -1)
        for q, (a, b) in enumerate(runs):
            run_id[a + 5:b + 1] = q
        rid = run_id[j]
        php = ph[j, leg]
        prp = pr[j, leg]
        phs = php + damp[leg] * vlink[j, leg] / A_P[leg]
        for n in NS:
            for k in range(n, tr.size):
                if not (ok_t[k] and ok_t[k - n]) or rid[k] < 0 or rid[k] != rid[k - n]:
                    continue
                if prp[k] < FLOOR_G + BAR or prp[k - n] < FLOOR_G + BAR:
                    continue
                a, _b = runs[rid[k]]
                s_lock = sm[a, leg]
                rm = (l0h + s_lock) / (l0r[leg] + S_MAX - s_lock)
                dh = php[k - n] - php[k]          # head drop (+ = load loss)
                dr = prp[k] - prp[k - n]          # rod rise
                dhs = phs[k - n] - phs[k]
                dmh = mh[k - n, leg] - mh[k, leg]
                dmr = mr[k, leg] - mr[k - n, leg] if np.all(np.isfinite(mr[[k, k - n], leg])) else math.nan
                rows.append((leg, n, s_lock, rm, dh, dr, dhs, dmh, dmr,
                             A_R[leg] * (dr - rm * dh), A_R[leg] * (dr - rm * dhs)))
    return {"name": c.name, "batch": c.parent.name, "Fs_N": fs, "lock_valve": lock_valve,
            "beta": beta, "rows": rows}


def summarise(allrows):
    arr = np.array(allrows, float)
    out = {}
    if arr.size == 0:
        return out
    for n in NS:
        for side, legs in (("front", (0, 1)), ("rear", (2, 3))):
            m0 = (arr[:, 1] == n) & np.isin(arr[:, 0], legs)
            for lo, hi in BINS:
                m = m0 & (arr[:, 4] >= lo * BAR) & (arr[:, 4] < hi * BAR)
                if not m.any():
                    continue
                q = arr[m]
                ratio = (q[:, 5] / q[:, 4]) / q[:, 3]
                ms = m0 & (arr[:, 6] >= lo * BAR) & (arr[:, 6] < hi * BAR)
                qs = arr[ms]
                ratio_s = (qs[:, 5] / qs[:, 6]) / qs[:, 3] if ms.any() else np.array([np.nan])
                mm = m & np.isfinite(arr[:, 8])
                qm = arr[mm]
                ratio_m = ((qm[:, 8] / qm[:, 7]) / qm[:, 3]) if mm.any() else np.array([np.nan])
                key = f"n{n}_{side}_dh{lo:g}-{hi:g}bar"
                out[key] = {
                    "count": int(m.sum()),
                    "Rsec/Rmodel truth p50/p99/max": [round(float(np.percentile(ratio, p)), 4)
                                                      for p in (50, 99)] + [round(float(ratio.max()), 4)],
                    "Rsec/Rmodel truth min": round(float(ratio.min()), 4),
                    "Rsec/Rmodel spring-head p50/max/min": [round(float(np.nanpercentile(ratio_s, 50)), 4),
                                                           round(float(np.nanmax(ratio_s)), 4),
                                                           round(float(np.nanmin(ratio_s)), 4)],
                    "Rsec/Rmodel readings p50/max/min": [round(float(np.nanpercentile(ratio_m, 50)), 4),
                                                        round(float(np.nanmax(ratio_m)), 4),
                                                        round(float(np.nanmin(ratio_m)), 4)],
                    "excess_kN truth max": round(float(q[:, 9].max()) / 1e3, 3),
                    "excess_kN spring-head max(abs)": round(float(np.abs(arr[m, 10]).max()) / 1e3, 4),
                    "s_lock range": [round(float(q[:, 2].min()), 3), round(float(q[:, 2].max()), 3)],
                }
    return out


def r_hi(s):
    """R_hi = R_ub / kappa: worst static column ratio (L0h 0.08, L0r 0.02, s' = s + 5 mm)."""
    sp = np.minimum(s + 0.005, S_MAX - 1e-3)
    return (0.08 + sp) / (0.02 + S_MAX - sp)


def hi_summary(allrows):
    """Windows against R_hi (n = 3): exceedance count, force excess, factor needed."""
    arr = np.array(allrows, float)
    arr = arr[arr[:, 1] == 3]
    out = {}
    for side, legs in (("front", (0, 1)), ("rear", (2, 3))):
        a = arr[np.isin(arr[:, 0], legs)]
        rh = r_hi(a[:, 2])
        g_hi = A_P[legs[0]] + rh * A_R[legs[0]]
        dd = a[:, 6] - a[:, 4]  # spring-head drop minus truth drop (dashpot change) [Pa]
        for lab, m in (("dh>=1bar", a[:, 4] >= 1 * BAR), ("dh>=2bar", a[:, 4] >= 2 * BAR),
                       ("dh>=5bar", a[:, 4] >= 5 * BAR),
                       ("rate>20kN/s (G(R_hi)dh>6kN)", g_hi * a[:, 4] > 6.0e3)):
            if not m.any():
                continue
            q = a[m]
            ratio_hi = (q[:, 5] / q[:, 4]) / rh[m]
            exc = A_R[legs[0]] * (q[:, 5] - rh[m] * q[:, 4])
            ratio_plant = (q[:, 5] / q[:, 4]) / q[:, 3]
            ratio_hi_s = (q[:, 5] / np.maximum(q[:, 6], 1.0)) / rh[m]
            mult = {}
            for kf in (1.0, 1.03, 1.05, 1.08, 1.10, 1.13):
                e = A_R[legs[0]] * (q[:, 5] - kf * rh[m] * q[:, 4])
                mult[f"x{kf:g}"] = [int((e > 0).sum()), round(float(e.max()) / 1e3, 3)]
            out[f"{side}_{lab}_multiplier [count, max excess kN]"] = mult
            out[f"{side}_{lab}"] = {
                "windows": int(m.sum()),
                "R_sec > R_hi count": int((ratio_hi > 1.0).sum()),
                "max R_sec/R_hi": round(float(ratio_hi.max()), 4),
                "max R_sec/R_plant": round(float(ratio_plant.max()), 4),
                "max force excess over R_hi [kN]": round(float(exc.max()) / 1e3, 3),
                "max R_sec/R_hi with spring head": round(float(ratio_hi_s.max()), 4),
                "max |dashpot head change| [bar]": round(float(np.abs(dd[m]).max()) / BAR, 3),
                "p99 |dashpot head change| [bar]": round(float(np.percentile(np.abs(dd[m]), 99)) / BAR, 3),
            }
    return out


def main():
    out_path = Path(sys.argv[1])
    cases, allrows, worst, hi_hits = [], [], [], []
    for b in sys.argv[2:]:
        for c in find_cases(Path(b)):
            r = analyse(c)
            if r is None:
                continue
            cases.append({k: r[k] for k in ("name", "batch", "Fs_N", "lock_valve", "beta")}
                         | {"windows": len(r["rows"])})
            for row in r["rows"]:
                allrows.append(row)
                if row[1] == 3 and row[4] >= 1 * BAR and row[5] > r_hi(row[2]) * row[4]:
                    hi_hits.append({"case": r["name"], "batch": r["batch"], "Fs_N": r["Fs_N"],
                                    "beta": r["beta"], "leg": int(row[0]),
                                    "s_lock": round(row[2], 4), "R_plant": round(row[3], 3),
                                    "R_hi": round(float(r_hi(row[2])), 3),
                                    "dh_bar": round(row[4] / BAR, 3), "dr_bar": round(row[5] / BAR, 3),
                                    "dh_spring_bar": round(row[6] / BAR, 3)})
                if row[1] == 3 and row[4] >= 1 * BAR:
                    worst.append((row[9], r["name"], row))
    worst.sort(key=lambda x: -x[0])
    res = {"cases": len(cases), "by_case_meta": cases[:400], "summary": summarise(allrows),
           "worst_excess_n3_dh_ge1bar": [
               {"excess_kN": round(w[0] / 1e3, 3), "case": w[1], "leg": int(w[2][0]),
                "s_lock": round(w[2][2], 4), "R_model": round(w[2][3], 3),
                "dh_bar": round(w[2][4] / BAR, 3), "dr_bar": round(w[2][5] / BAR, 3),
                "dh_spring_bar": round(w[2][6] / BAR, 3)} for w in worst[:15]]}
    by = {}
    for cm in cases:
        by.setdefault((cm["Fs_N"] > 0, cm["lock_valve"], cm["beta"]), 0)
        by[(cm["Fs_N"] > 0, cm["lock_valve"], cm["beta"])] += 1
    res["case_groups"] = {str(k): v for k, v in by.items()}
    res["vs_R_hi_n3"] = hi_summary(allrows)
    res["R_hi_exceed_windows_n3_dh_ge1bar"] = hi_hits
    for h in hi_hits:
        print("HIT", h)
    out_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("cases", len(cases))
    for k, v in res["vs_R_hi_n3"].items():
        print(k, v)


if __name__ == "__main__":
    main()
