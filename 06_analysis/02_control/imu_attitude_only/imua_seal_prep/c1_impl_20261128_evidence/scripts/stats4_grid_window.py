"""stats review 4 check on the C-1 attitude records (read only, no code change).

1. Grid: every inclinometer time equals t_k - (9 - i) * 0.01 s for period k (10 readings per period, i = 0..9), and
   consecutive readings are 10 ms apart; max |error| <= 1e-9 s.
2. Window: for each period t_L more than 0.1 s from both record ends, the number of readings with
   |t - t_L| <= 0.1 s (+ eps) is exactly 21; share of such periods (eps 1e-9 s and, as a sensitivity, 1e-6 s).
3. End rule of the C-5 rows: run_S8C ``end_rule`` of each C-5 L2b case (anchor, offset, upper bound) and the stored
   argv of the SCM rows (run_S9 ``level``: fixed ``--duration``); the G-d record's own end vs first READY + 10 s.

Usage (Chrono-dev, -I -B): python stats4_grid_window.py <worktree> <evidence dir> <436.8 manifest json> <out json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PERIOD_S, SAMPLE_S, PER_PERIOD = 0.1, 0.01, 10
RECORDS = ("gd_v0_full", "imua_l2b_vb20", "imua_scm_vb")


def grid_window(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        t = np.asarray(z["t_s"], float)
        ti = np.asarray(z["inclinometer_t_s"], float)
    out = {"periods": int(t.size), "readings": int(ti.size), "t_first_s": float(t[0]), "t_last_s": float(t[-1])}
    ok_shape = ti.size == PER_PERIOD * t.size
    out["readings_per_period_ok"] = bool(ok_shape)
    if ok_shape:
        want = t[:, None] - (PER_PERIOD - 1 - np.arange(PER_PERIOD))[None, :] * SAMPLE_S
        out["grid_max_abs_err_s"] = float(np.max(np.abs(ti.reshape(-1, PER_PERIOD) - want)))
    steps = np.diff(ti)
    out["step_max_abs_err_s"] = float(np.max(np.abs(steps - SAMPLE_S)))
    out["grid_ok_1e-9"] = bool(ok_shape and out["grid_max_abs_err_s"] <= 1e-9 and out["step_max_abs_err_s"] <= 1e-9)
    inner = t[(t - t[0] > PERIOD_S + 1e-9) & (t[-1] - t > PERIOD_S + 1e-9)]
    out["inner_periods"] = int(inner.size)
    for eps in (1e-9, 1e-6):
        counts = np.array([int(np.sum(np.abs(ti - tl) <= PERIOD_S + eps)) for tl in inner])
        values, freq = np.unique(counts, return_counts=True)
        out[f"window_eps_{eps:g}"] = {"share_exactly_21": float(np.mean(counts == 21)) if counts.size else None,
                                      "count_histogram": {str(int(v)): int(f) for v, f in zip(values, freq)}}
    return out


def end_rules(worktree: Path, manifest: Path) -> dict:
    sys.path.insert(0, str(worktree / "03_src"))
    sys.path.insert(0, str(worktree / "04_scripts" / "02_chrono"))
    import run_S8C

    table = run_S8C.case_table()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    rows = doc["batches"]["V5-RESUME-K1-C5"]["rows"]
    out = {"rule_source": "run_S8C.end_rule / job_l2b_s8 (state['ready_t'] = FIRST READY only); run_S9 level: "
                          "fixed --duration, no end rule", "l2b": {}, "scm": {}}
    for r in rows:
        tail = r.get("argv_tail") or []
        if tail and tail[0] == "run":
            cid = tail[tail.index("--only") + 1]
            c = table[cid]
            rule = run_S8C.end_rule(c)
            out["l2b"][r["case"]] = {"s8c_case": cid, "event": c.event, "anchor": rule["anchor"],
                                     "after_s": rule["after_s"], "cap_after_event_s": rule.get("cap_after_event_s"),
                                     "upper_s": rule["upper_s"]}
        else:
            out["scm"][r["case"]] = {"duration_s": float(tail[tail.index("--duration") + 1]),
                                     "rule": "fixed duration (run_S9 level)"}
    return out


def main() -> int:
    wt, ev, manifest, out_path = (Path(a) for a in sys.argv[1:5])
    rep = {"records": {n: grid_window(ev / "runs" / n / "imua_attitude.npz") for n in RECORDS}}
    gd = json.loads((ev / "runs" / "gd_v0_full" / "result.json").read_text(encoding="utf-8"))
    first_ready = next(t for t, p in gd["phases"] if p == "ready")
    last_ready = [t for t, p in gd["phases"] if p == "ready"][-1]
    rep["gd_end"] = {"first_ready_rel_s": first_ready, "last_ready_entry_rel_s": last_ready,
                     "ready_entries": sum(1 for _, p in gd["phases"] if p == "ready"),
                     "end_rel_s": gd["s8_end"]["end_t_s"], "end_minus_first_ready_s": gd["s8_end"]["end_t_s"] - first_ready,
                     "stopped_at_target": gd["s8_end"]["stopped_at_target"], "anchor": gd["s8_end"]["anchor"],
                     "after_s": gd["s8_end"]["after_s"]}
    rep["c5_end_rules"] = end_rules(wt, manifest)
    out_path.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
