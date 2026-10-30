"""Spec 426.9.B1 M1 / M3 trace (control-expert 2026-10-30): re-run study-B cases on the s9_soil_slope path
(project preset, settle table hook_harness) with a per-period log of controller internals. Read only.

Usage: python -I m13_trace.py <root> <out_json> <workers> <case_id[@mass]> ...
Moved 2026-10-30 unchanged from session scratchpad ctrl-426/m13_trace.py (paths are arguments). Its output
m13_trace.json (2.75 MB) was not moved.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402
import s9_soil_slope as ss  # noqa: E402

TABLE = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"


def build(case_spec: str) -> dict:
    cid, _, mass = case_spec.partition("#")
    cases = ss.build_cases(("H1", "H3"))
    rows = json.loads(TABLE.read_text(encoding="utf-8"))["hook_harness"]
    cases = ss.attach_settle_table([c for c in cases if c.case_id == cid], rows)
    if mass:
        cases = [replace(c, mass_scale=float(mass)) for c in cases]
    return cases[0].to_dict()


def job(case_spec: str) -> dict:
    case = build(case_spec)
    sl = ss._install_patches()
    cl = sl._imports()[0]
    base_cp = sl.control_period
    log = []

    def cp(cl_, Meas, plant, cmd, valve, ha, period_s, rec, sens=None):
        m = base_cp(cl_, Meas, plant, cmd, valve, ha, period_s, rec, sens)
        ctrl = ss._CAP["ctrl"]
        st = ctrl._state
        soil = ctrl._soil_state()
        tail = None
        rise = None
        mean_load = None
        if soil.window:
            try:
                tail = ctrl._plateau_tail()
            except Exception:  # noqa: BLE001
                tail = None
            if tail is not None:
                rise = ctrl._plateau_rise_N(tail)
                mean_load = float(np.mean([s.load_sum_N for s in tail]))
        F_read = np.asarray(m.head_pressure_Pa, float) * ha
        lg = ss._CAP["log"]
        log.append({
            "t": round(float(plant.t), 2), "ph": str(ctrl.phase),
            "cr_kN": round(float(rec["crmax"]) / 1e3, 2),
            "rut_mm": round(lg["rut_clear_mm"][-1], 1), "est_mm": round(lg["clear_est_mm"][-1], 1),
            "target_mm": round(ctrl._clearance_target_m() * 1e3, 1),
            "guard": bool(st.lift_stroke_limited), "guard_mode": str(getattr(st, "lift_guard_mode", None)),
            "loc": bool(soil.is_liftoff_confirmed), "soilmode": bool(soil.is_soil_mode),
            "win_n": len(soil.window), "rise_kN": None if rise is None else round(rise / 1e3, 2),
            "tail_load_ratio": None if mean_load is None else round(mean_load / ctrl._reference_weight_N(), 4),
            "plateau_ok": bool(ctrl._is_plateau_period()),
            "applied_mm_s": np.round(np.asarray(st.applied_output_m_s, float) * 1e3, 2).tolist(),
            "sum_read_over_Wref": round(float(F_read.sum()) / ctrl._reference_weight_N(), 4),
            "stroke_mm": np.round(np.asarray(plant.sref, float) * 1e3, 1).tolist(),
            "sink_mm": None if plant.soil is None else np.round(plant.soil.z * 1e3, 1).tolist(),
            "reapp": sorted(int(x) for x in st.active_reapproaches),
            "fmin_kN": np.round(np.asarray(rec["fmin"], float) / 1e3, 1).tolist(),
        })
        return m

    sl.control_period = cp
    ss._CAP.clear()
    ss._CAP["crawler_series"] = []
    ss._CAP["settle"] = None
    ss._CAP["settle_table"] = ss.SettleTableRow(**case["settle_table"]) if case.get("settle_table") else None
    ss._CAP["case"] = case
    out = sl.run_case(ss.run_case_input(case))
    ctrl = ss._CAP["ctrl"]
    return {"spec": case_spec, "id": case["id"], "t_ready": out["t_ready_s"], "t_done": out["t_done_s"],
            "final": out["final_phase"], "events": out["events"], "hash": out["commands_sha256"], "log": log,
            "soil_meta": json.loads(json.dumps(ctrl._soil_meta(), default=str)) if hasattr(ctrl, "_soil_meta") else None}


if __name__ == "__main__":
    out_path = Path(sys.argv[2])
    workers = int(sys.argv[3])
    specs = sys.argv[4:]
    with Pool(min(workers, len(specs))) as pool:
        res = pool.map(job, specs, chunksize=1)
    out_path.write_text(json.dumps(res, default=float), encoding="utf-8")
    for r in res:
        print(r["id"], r["spec"], r["t_ready"], r["final"], r["hash"][:16])
