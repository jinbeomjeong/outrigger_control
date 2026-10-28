"""Spec rev. 75: P-S8-29 relaxed-completion flicker in a Chrono S9 run (completion_series.npz of run_S9.py).

From the first relaxed sample (twist_relaxed == 1) to the first DONE: share of periods with each completion condition,
relaxed-condition share, the 5 s window "max |D| - |D| at the window start" distribution and the 5 s net drop, and
the delay "first relaxed sample -> DONE" (a steady relaxed condition gives done_hold_s = 1 s). Also an offline replay
of candidate (a) |D| 1 s moving mean and (b) rise tolerance 0.6 kN on the same D series (the other conditions as
recorded) -> the first time the relaxed condition would hold for done_hold_s.

Usage: python -I r76_relax_flicker.py <out_json> <case dir> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

W_S, T_S, RISE, DROP, DREL, HOLD = 5.0, 10.0, 300.0, 0.0, 15e3, 1.0


def relaxed_series(t, Dabs, base_ok, settled_since, rise):
    """V2b relaxed condition on a given |D| series: window W, rise tolerance, |D| <= 15 kN, settled for T."""
    out = np.zeros(len(t), bool)
    for i in range(len(t)):
        if not base_ok[i] or not np.isfinite(settled_since[i]) or t[i] - settled_since[i] < T_S - 1e-9:
            continue
        j0 = np.searchsorted(t, t[i] - W_S - 1e-9)
        if t[i] - t[j0] < W_S - 0.1 - 1e-9:
            continue
        win = Dabs[j0:i + 1]
        out[i] = bool(win[-1] <= win[0] - DROP and win.max() <= win[0] + rise and win[-1] <= DREL)
    return out


def first_hold(t, ok, hold=HOLD):
    run_start = None
    for i in range(len(t)):
        if ok[i]:
            run_start = t[i] if run_start is None else run_start
            if t[i] - run_start >= hold - 1e-9:
                return float(t[i])
        else:
            run_start = None
    return None


def main():
    out = Path(sys.argv[1])
    res = {"script": "04_scripts/03_control/s8/r76_relax_flicker.py", "cases": []}
    for d in sys.argv[2:]:
        z = np.load(Path(d) / "completion_series.npz", allow_pickle=True)
        r = json.loads((Path(d) / "result.json").read_text(encoding="utf-8"))
        t0 = r["p3b"]["t_loop_start_s"]
        t = z["t_s"] - t0
        ph = np.array([str(p) for p in z["phase"]])
        lev = ph == "level"
        relaxed = z["twist_relaxed"] == 1
        done_i = np.flatnonzero(ph == "done")
        t_done = float(t[done_i[0]]) if done_i.size else None
        first_rel = float(t[np.flatnonzero(relaxed & lev)[0]]) if (relaxed & lev).any() else None
        row = {"case": Path(d).name, "t_first_relaxed_s": first_rel, "t_done_s": t_done}
        if first_rel is not None and t_done is not None:
            m = lev & (t >= first_rel) & (t < t_done)
            row["share_in_relaxed_span"] = {k: round(float(np.mean(z[k][m] == 1)), 3) for k in
                                            ("ok_attitude", "ok_clearance", "ok_loc", "twist_relaxed")}
            row["delay_first_relaxed_to_done_s"] = round(t_done - first_rel, 2)
        Dabs = np.abs(z["D_loop_N"].astype(float))
        m2 = lev & (t >= (first_rel - 15.0 if first_rel else 0.0)) & (t < (t_done or t[-1]))
        D2 = Dabs[m2]
        n = int(round(W_S / 0.1))
        if len(D2) > n and np.all(np.isfinite(D2)):
            ex = np.array([D2[i:i + n + 1].max() - D2[i] for i in range(len(D2) - n)]) / 1e3
            dr = (D2[:-n] - D2[n:]) / 1e3
            row["window_rise_kN"] = {"median": round(float(np.median(ex)), 3), "p90": round(float(np.percentile(ex, 90)), 3),
                                     "max": round(float(ex.max()), 3)}
            row["net_drop_5s_kN_median"] = round(float(np.median(dr)), 3)
            row["period_dD_std_kN"] = round(float(np.diff(D2).std() / 1e3), 3)
        else:  # no relaxed span (e.g. the G1 control): null, not NaN
            row["window_rise_kN"] = None
            row["net_drop_5s_kN_median"] = None
            row["period_dD_std_kN"] = None
        # offline replay of the candidates on the recorded series (other conditions as recorded)
        base_ok = lev & (z["ok_attitude"] == 1) & (z["ok_clearance"] == 1) & (z["ok_loc"] == 1)
        settled = z["twist_relax_settled_since_s"].astype(float) - t0
        settled[~np.isfinite(settled) | (z["twist_relax_settled_since_s"] < 0)] = np.nan
        mean1 = np.convolve(Dabs, np.ones(10) / 10, mode="full")[:len(Dabs)]
        mean1[:9] = Dabs[:9]
        rep = {}
        for name, Ds, rise in (("V2b_replay", Dabs, RISE), ("a_mean1s", mean1, RISE), ("b_rise0.6", Dabs, 600.0)):
            ok = relaxed_series(t, Ds, base_ok, settled, rise) & (Dabs >= 3000.0)
            rep[name] = {"first_hold_s": first_hold(t, ok), "share_after_first": None}
            f = np.flatnonzero(ok)
            if f.size and t_done is not None:
                mm = lev & (t >= t[f[0]]) & (t < t_done)
                rep[name]["share_after_first"] = round(float(np.mean(ok[mm])), 3) if mm.any() else None
        row["replay"] = rep
        res["cases"].append(row)
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for row in res["cases"]:
        print(json.dumps(row, default=float))


if __name__ == "__main__":
    main()
