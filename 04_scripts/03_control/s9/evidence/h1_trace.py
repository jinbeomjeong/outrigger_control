"""Spec 428 H-1 trace (control-expert 2026-10-30): study-A J2 LEVEL RE1bF F_s 0 branch on one leg, with a per-period
log of the true crawler clearance, the controller stroke-plane estimate, strokes and pad sink. Read only.

Usage: python -I h1_trace.py <root> <out_json> <leg>
Moved 2026-10-30 unchanged from session scratchpad ctrl-426/h1_trace.py (paths are arguments).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
import numpy as np  # noqa: E402
import s9_soil_event_screen as ses  # noqa: E402

LOG: list = []
_ORIG = ses.control_period_rec


def control_period_logged(cl, Meas, plant, cmd, valve, ha, period_s, rec, floor_fn=None, rows=None, readings="two"):
    m = _ORIG(cl, Meas, plant, cmd, valve, ha, period_s, rec, floor_fn, rows, readings)
    ctrl = _CTRL.get("ctrl")
    if ctrl is not None and _CTRL.get("on"):
        soil = ctrl._soil_state()
        F = np.asarray(m.head_pressure_Pa, float) * np.asarray(ha, float)
        LOG.append({
            "t": round(float(plant.t), 2), "ph": str(ctrl.phase),
            "rut_mm": round(ses.crawler_floor_clearance_mm(cl, plant), 1),
            "est_mm": round(ctrl._clearance_estimate_m(np.asarray(plant.x, float)) * 1e3, 1),
            "corners_mm": np.round(ctrl._clearance_corners_m(np.asarray(plant.x, float)) * 1e3, 1).tolist(),
            "target_mm": round(ctrl._clearance_target_m() * 1e3, 1),
            "sref_mm": np.round(np.asarray(plant.sref, float) * 1e3, 1).tolist(),
            "x_mm": np.round(np.asarray(plant.x, float) * 1e3, 1).tolist(),
            "h_mm": None if plant.soil is None else np.round(plant.soil.h * 1e3, 1).tolist(),
            "sink_mm": None if plant.soil is None else np.round(plant.soil.z * 1e3, 1).tolist(),
            "crawler_kN": round(float(rows[-1][ses.CRAWLER_COLUMN]) / 1e3, 2) if rows else None,
            "sumF_over_What": None if not soil.weight_estimate_N else round(float(F.sum()) / soil.weight_estimate_N, 4),
            "reapp": sorted(int(x) for x in ctrl._state.active_reapproaches),
            "att_deg": np.round(np.degrees(plant.attitude()), 3).tolist(),
        })
    return m


_CTRL: dict = {}


def main():
    out_path, leg = Path(sys.argv[2]), sys.argv[3]
    ses.control_period_rec = control_period_logged
    ses._s8_modules()
    cl, c2, Meas = ses.sl._imports()
    plant, ctrl, info = ses.make_event_base(cl, c2, "J2", ses.LEVEL, ses.PAD, 0.0)
    base0 = ses.run_base_soil(cl, Meas, copy.deepcopy(plant), copy.deepcopy(ctrl), "two",
                              hold_after_ready_s=ses.READY_DELAY_S - ses.PRE_S)
    t_level = base0["t_loc"] + 0.5 * (base0["t_done"] - base0["t_loc"])
    lb = ses.run_base_soil(cl, Meas, plant, ctrl, "two", stop_t=t_level - ses.PRE_S)
    t_ev = plant.t + ses.PRE_S
    pl, ct = copy.deepcopy(plant), copy.deepcopy(ctrl)
    _CTRL.update(ctrl=ct, on=True)
    br = ses.branch_soil(cl, Meas, pl, ct, lb["cmd"].copy(), lb["valve"].copy(), "RE1bF", ses.LEGS.index(leg), t_ev, "two")
    judged = ses.judge_soil_event(br, 0.0, ct.geometry.head_area_m2, base0["stroke_max_mm"])
    out = {"leg": leg, "t_ev": t_ev, "base_timeline": base0["timeline"], "hash": br.commands_sha256,
           "pass": judged["pass"], "gates": judged["gates"], "crawler": judged.get("crawler"),
           "events": br.events, "log": LOG}
    out_path.write_text(json.dumps(out, default=float), encoding="utf-8")
    print(leg, "hash", br.commands_sha256[:16], "pass", judged["pass"], "clr_end", br.crawler_clear_end_mm)


if __name__ == "__main__":
    main()
