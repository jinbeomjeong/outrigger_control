"""X6 SGS safe-stop checks (spec 430.4 / 427.12.5 SA-4) on Chrono S9SL case folders.

(a) command identity with a pair case up to the stop period (controller_commands.npz, every array, rows with
    t < t_stop); (b) stop events; (c) after the stop: FAULT_STROKE_END 0, per-leg true F_cyl minimum vs F_min,
    pad lift, crawler true normal at the stop and at the end vs + 0.01 W, max moving head pressure.
Prints the npz keys first so the column names can be checked.

Usage: python -I x6_stop_check.py <out json> <case dir> [<pair case dir>] [<case dir> [<pair>] ...]
       pairs are given as <case>=<pair> or a lone <case>
"""
import json
import sys
from pathlib import Path

import numpy as np

F_MIN_N = 9414.589
W_N = 380112.912
LEGS = ("FL", "FR", "RL", "RR")


def stop_time(case):
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    ev = res.get("events") or []
    t_stop = next((e["t_s"] for e in ev if str(e.get("name", "")).startswith("FAULT_LIFT_STROKE_LIMIT")), None)
    names = [e.get("name") for e in ev]
    return t_stop, names, res.get("t_loop_start_s")


def cmd_identity(case, pair, t_stop):
    a = np.load(case / "controller_commands.npz", allow_pickle=False)
    b = np.load(pair / "controller_commands.npz", allow_pickle=False)
    tk = next((k for k in a.files if k in ("t", "t_s", "time")), None)
    out = {"keys": a.files, "time_key": tk}
    if tk is None:
        return out
    ta, tb = a[tk], b[tk]
    na, nb = int(np.sum(ta < t_stop - 1e-9)), int(np.sum(tb < t_stop - 1e-9))
    same = {}
    for k in a.files:
        if k in b.files and a[k].shape[:1] == ta.shape[:1]:
            same[k] = bool(np.array_equal(a[k][:na], b[k][:nb], equal_nan=True)) if na == nb else False
    first_diff = None
    for k in a.files:
        if k in b.files and a[k].shape[:1] == ta.shape[:1] and b[k].shape[:1] == tb.shape[:1]:
            n = min(len(ta), len(tb))
            d = np.nonzero(~np.isclose(a[k][:n], b[k][:n], rtol=0, atol=0, equal_nan=True).reshape(n, -1).all(axis=1))[0]
            if d.size and (first_diff is None or ta[d[0]] < first_diff[1]):
                first_diff = (k, float(ta[d[0]]))
    out.update(rows_before_stop=(na, nb), all_equal_before_stop=all(same.values()) if same else None,
               per_key=same, first_divergence=first_diff)
    return out


def after_stop(case, t_stop):
    s = np.load(case / "step_series.npz", allow_pickle=False)
    keys = s.files
    tk = next((k for k in keys if k in ("t", "t_s", "time")), keys[0])
    t = s[tk]
    m = t >= t_stop
    out = {"keys": keys}

    def pick(*names):
        for n in names:
            for k in keys:
                if k.lower() == n.lower():
                    return s[k]
        for n in names:
            for k in keys:
                if n.lower() in k.lower():
                    return s[k]
        return None

    f = pick("F_cyl_true", "F_cyl", "Fcyl")
    if f is not None and f.ndim == 2:
        out["F_cyl_min_after_stop_kN"] = dict(zip(LEGS, (f[m].min(axis=0) / 1e3).round(2).tolist()))
        out["F_cyl_min_after_stop_ge_Fmin"] = bool((f[m].min(axis=0) >= F_MIN_N).all())
    cr = pick("crawler_normal_N", "crawler_N", "crawler_normal")
    if cr is not None:
        c = cr if cr.ndim == 1 else cr.sum(axis=1)
        k0 = int(np.argmax(m))
        out["crawler_N_at_stop"] = float(c[k0])
        out["crawler_N_max_after_stop"] = float(c[m].max())
        out["crawler_N_end"] = float(c[-1])
        out["crawler_over_0p01W_at_stop"] = bool(c[k0] > 0.01 * W_N)
        out["crawler_after_stop_le_stop_plus_0p01W"] = bool(c[m].max() <= c[k0] + 0.01 * W_N)
    pn = pick("pad_normal_N", "pad_N", "pad_normal")
    if pn is not None and pn.ndim == 2:
        out["pad_min_after_stop_N"] = dict(zip(LEGS, pn[m].min(axis=0).round(1).tolist()))
    ph = pick("p_head_Pa", "head_pressure", "p_head")
    if ph is not None and ph.ndim == 2:
        out["head_pressure_max_after_stop_bar"] = float(ph[m].max() / 1e5)
        out["head_pressure_max_run_bar"] = float(ph.max() / 1e5)
    return out


args = sys.argv[2:]
out = {}
for a in args:
    case, _, pair = a.partition("=")
    c = Path(case)
    t_stop, names, t0 = stop_time(c)
    r = {"t_stop_abs_s": t_stop, "t_loop_start_s": t0, "stop_events": [n for n in names if "STROKE" in str(n)],
         "fault_stroke_end": sum(1 for n in names if str(n).startswith("FAULT_STROKE_END")),
         "ready_events": sum(1 for n in names if str(n) == "ready" or str(n).startswith("ready_"))}
    if t_stop is not None:
        r["after_stop"] = after_stop(c, t_stop)
        if pair:
            r["identity_vs_pair"] = cmd_identity(c, Path(pair), t_stop)
    out[c.name] = r
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, default=str)[:6000])
