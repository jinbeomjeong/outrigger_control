"""Read-only: post-LOC sinkage / stroke budget digest of stored Chrono SCM runs.

For each case folder: LOC time (P3-2), first READY (P3-5), per pad geometric sinkage and
reading stroke (record meas.stroke, 10 Hz) at LOC, at first READY and at the run end, max reading
stroke, guard margin (682.8 mm), and the pad sinkage increments LOC -> READY -> end.
Prints one JSON line per case (units mm, s; times absolute).
"""
import json
import sys
from pathlib import Path

import numpy as np

GUARD_MM = 682.8


def at(t, x, tt):
    if tt is None:
        return None
    i = min(int(np.searchsorted(t, tt - 1e-9)), len(t) - 1)
    return x[i]


def mm(v):
    return None if v is None else [round(float(a) * 1e3, 2) for a in v]


for case in sys.argv[1:]:
    p = Path(case)
    r = json.loads((p / "result.json").read_text(encoding="utf-8"))
    p3 = r["p3b"]
    t_loc = p3["P3-2_loc"].get("t_loc_s")
    t_dep = p3["P3-2_loc"].get("t_departure_s")
    t_rdy = p3["P3-5_clearance_stroke"].get("t_first_ready_s")
    cs = p3.get("creep_stop", {})
    ss = np.load(p / "step_series.npz")
    t1 = ss["t_s"]
    z = ss["pad_sinkage_geometric_m"]
    rec = np.load(p / "record" / "record.npz")
    t10 = rec["t"]
    s = rec["meas.stroke"]
    z_loc, z_rdy, z_end = at(t1, z, t_loc), at(t1, z, t_rdy), z[-1]
    s_loc, s_rdy, s_end = at(t10, s, t_loc), at(t10, s, t_rdy), s[-1]
    smax = np.nanmax(s, axis=0)
    i_max = int(np.nanargmax(np.nanmax(s, axis=1)))
    ev = [e for e in r.get("events", []) if any(k in str(e) for k in (
        "FAULT", "WARN_LIFT", "INFO_LOC", "INFO_DIFF", "LOC_REVOKED", "MARGIN"))]
    out = {
        "case": p.name, "t_dep": t_dep, "t_loc": t_loc, "t_ready": t_rdy, "t_end": round(float(t1[-1]), 2),
        "creep_t_final": cs.get("t_final_s"), "creep_window_s": cs.get("rate_window_s"),
        "sink_loc": mm(z_loc), "sink_ready": mm(z_rdy), "sink_end": mm(z_end),
        "dsink_loc_to_ready": mm(None if z_rdy is None else z_rdy - z_loc),
        "dsink_ready_to_end": mm(None if z_rdy is None else z_end - z_rdy),
        "stroke_loc": mm(s_loc), "stroke_ready": mm(s_rdy), "stroke_end": mm(s_end),
        "dstroke_loc_to_max": mm(smax - s_loc) if s_loc is not None else None,
        "stroke_max": mm(smax), "t_stroke_max": round(float(t10[i_max]), 2),
        "guard_margin_min": round(GUARD_MM - float(np.nanmax(smax)) * 1e3, 2),
        "events": [str(e)[:80] for e in ev][:10],
    }
    print(json.dumps(out, ensure_ascii=False))
