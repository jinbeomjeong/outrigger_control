"""Spec rev. 67: second path for the r67_g1_screen.py gate quantities on chosen branches.

The screen judge (r67_g1_screen.judge_event) and r51_reapp_closed_loop.metrics (rev. 52, written independently)
read the same 1 ms record of one branch; compared: event-pair union lift time and last touch-down, adjacent-leg
lift sum and max gap (r51: fixed 8 s window; screen: physical window W, so they agree when no adjacent lift falls
between W end and 8 s), and the minimum true cylinder force over [event, event + 8 s].

Run (dynamics-dev): python -I r67_g1_xcheck.py <project_root> <out_json>
"""
from __future__ import annotations

import copy
import json
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import numpy as np  # noqa: E402

import r51_reapp_closed_loop as r51  # noqa: E402
import r67_g1_screen as g  # noqa: E402

CASES = [("level", "top", 0.0, "FL", "RE1bF", 0.0), ("level", "top", 0.0, "FR", "FS24", 0.025),
         ("ready", "top", 0.0, "FL", "FS24", 0.025), ("ready", "top", 8.0, "RR", "RE1bF", 0.0),
         ("level", "bottom", 8.0, "RR", "G4", 0.0), ("level", "top", 0.0, "RL", "RE1bF", 0.0)]


def job(case):
    timing, level, fs, leg_name, ev_id, off = case
    r51.place_worker()
    cl, c2, Meas = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant, ctrl, _ = g.make_base(cl, c2, level, fs)
    tl = g.run_base(cl, c2, Meas, copy.deepcopy(plant), copy.deepcopy(ctrl))
    t_target = (tl["t_ready"] + 5.0) if timing == "ready" else tl["t_loc"] + 0.5 * (tl["t_done"] - tl["t_loc"])
    st = g.run_base(cl, c2, Meas, plant, ctrl, stop_t=t_target - g.PRE_S)
    t_ev = plant.t + g.PRE_S + off
    leg = g.LEGS.index(leg_name)
    att0 = np.degrees(plant.attitude())
    rec, phases, events, crawler, t_rb, ct = g.branch(cl, Meas, plant, ctrl, st["cmd"].copy(), st["valve"].copy(),
                                                      g.EVENTS[ev_id], leg, t_ev)
    a = g.judge_event(rec, phases, events, crawler, t_ev, t_rb, g.EVENTS[ev_id], leg, ct, att0)
    rec_l = [row for row in rec]
    b = r51.metrics(rec_l, t_ev, ct, 0, leg, att0, None)
    t = rec[:, 0] - t_ev
    w8 = (t >= 0) & (t <= 8.0)
    min8_screen = float(rec[w8, 5:9].min() / 1e3)
    out = {"case": case,
           "screen": {"pair_union_s": a["pair_union_s"], "pair_last_touch_s": a["pair_last_touch_s"],
                      "adj_sum_s": round(a["adj_lift_sum_W_s"] + a["adj_lift_outside_W_s"], 3),
                      "adj_gap_mm": a["adj_max_gap_W_mm"], "min_F_8s_kN": round(min8_screen, 2)},
           "r51": {"pair_union_s": b["pair_union_s"], "pair_last_touch_s": b["pair_last_touch_s"],
                   "adj_sum_s": b["adj_sum_s"], "adj_gap_mm": b["adj_max_gap_mm"], "min_F_8s_kN": b["min_true_kN"]}}
    out["max_abs_diff"] = {k: round(abs(out["screen"][k] - out["r51"][k]), 4) for k in out["screen"]}
    return out


def main():
    with Pool(len(CASES)) as pool:
        res = pool.map(job, CASES)
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for r in res:
        print(r["case"], r["max_abs_diff"], r["screen"], r["r51"])


if __name__ == "__main__":
    main()
