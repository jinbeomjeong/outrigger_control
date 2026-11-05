"""Traced re-runs of r79 harness keys on the pinned checkout, with per-job preset keywords and setting overrides.

Usage: python -I -B g8trace.py <checkout> <jobs.json> <out.jsonl> [--workers N]
jobs.json: [{"tag": str, "key": "<plain r79 key>", "kwargs": {preset keywords}, "over": {"a.b": value}, "trace": bool}]
Env: ACC_WT = <checkout>; ACC_COMBO = off. Results append to out.jsonl; finished (tag, key) pairs are skipped.
No project file changes; nothing from the main tree is imported (acc_common guard).
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

ACC_DIR = Path(__file__).resolve().parents[1] / "c4g2k1"  # scratch copy, identical to the committed acc_common.py
sys.path.insert(0, str(ACC_DIR))
os.environ.setdefault("ACC_COMBO", "off")
os.environ.setdefault("ACC_WT", sys.argv[1] if len(sys.argv) > 1 else "")
os.environ.setdefault("R72_PATH", "per_leg")
import acc_common  # noqa: E402

acc_common.install()
ROOT = acc_common.wt_root()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import numpy as np  # noqa: E402
from outrigger_sim.control import c2  # noqa: E402

CURRENT: dict = {"kwargs": {}, "over": {}, "cand": {}}
TRACE: list = []
LOC: dict = {}
_base_preset = c2.C2Config.with_10hz_d1
_orig_level = c2.C2Controller._level
_orig_confirm = c2.C2Controller._confirm_liftoff
_orig_scope = c2.C2Controller._is_soil_stop_scope_met
_orig_start_hold = c2.C2Controller._start_touch_twist_hold


def _set_dotted(config, dotted, value):
    head, _, rest = dotted.partition(".")
    if rest:
        return replace(config, **{head: _set_dotted(getattr(config, head), rest, value)})
    return replace(config, **{head: value})


def preset(self, *args, **kwargs):
    merged = {**CURRENT["kwargs"], **kwargs}
    config = _base_preset(self, *args, **merged)
    for dotted, value in CURRENT["over"].items():
        config = _set_dotted(config, dotted, value)
    return config


def _true_clearance_mm():
    """Lowest crawler node above the base floor plane (r69 definition); None when the plant is not available."""
    import r79_sensor_screen as screen
    import r51_reapp_closed_loop as r51

    run = screen._ACTIVE
    plant = None if run is None else run.plant
    if plant is None or not hasattr(plant, "cr_rel"):
        return None
    cl, _, _ = r51._imports()
    rot = cl.rcc._R(plant.q)
    return round(min(float(plant.nrm @ (plant.r + rot @ c)) for c in plant.cr_rel) * 1e3, 2)


def traced_level(self, reading):
    out = _orig_level(self, reading)
    state = self._state
    hold = state.touch_twist
    TRACE.append({
        "cc": _true_clearance_mm(),
        "t": round(float(reading.t_s), 3),
        "ph": str(state.phase),
        "m": np.round(reading.motor_stroke_m * 1e3, 3).tolist(),
        "r": np.round(reading.rod_stroke_m * 1e3, 3).tolist(),
        "F": np.round(reading.cylinder_force_N / 1e3, 2).tolist(),
        "ce": round(float(self._clearance_estimate_m(reading.rod_stroke_m)) * 1e3, 3),
        "tg": round(float(self._clearance_target_m()) * 1e3, 2),
        "u": np.round(np.asarray(out, float) * 1e3, 3).tolist(),
        "att": np.round(np.degrees(np.asarray(self._period_raw_attitude_rad(), float)), 4).tolist(),
        "tw": None if hold is None or not hold.is_holding else round(float(hold.target_m) * 1e3, 3),
        "pz": state.pre_loc_pause_leg,
        "lim": bool(state.lift_stroke_limited),
        "gm": None if state.lift_guard_mode is None else str(state.lift_guard_mode),
    })
    return out


def cand_scope(self):
    """Candidate A: the SGS stop stays disarmed after an anchored LOC without a soil sign (non-planar pad floor)."""
    met = _orig_scope(self)
    if met and CURRENT["cand"].get("sgs_skip_anchor"):
        soil = self._soil_state()
        if soil.is_loc_anchor_applied and self._state.guard_soil_sign is None:
            return False
    return met


def cand_start_hold(self, reading):
    """Candidate C: no C4 hold when the stroke twist at the TOUCH end shows a non-planar pad floor."""
    limit_mm = CURRENT["cand"].get("c4_skip_twist_mm")
    if limit_mm is not None:
        twist_mm = abs(float(self.geometry.twist_vector @ np.asarray(reading.motor_stroke_m, float))) * 1e3
        LOC["touch_stroke_twist_mm"] = round(twist_mm, 2)
        if twist_mm > limit_mm:
            LOC["c4_skipped"] = True
            return None
    return _orig_start_hold(self, reading)


def traced_confirm(self, t_s, tail, mean_load_N):
    if CURRENT["cand"].get("anchor_att") == "tail_mean":  # candidate B: mean raw tilt of the confirming tail
        mean_att = tuple(float(v) for v in np.mean([x.raw_attitude_rad for x in tail], axis=0))
        tail = [replace(tail[0], raw_attitude_rad=mean_att), *tail[1:]]
    settle = self._settle_attitude_rad()
    first, last = tail[0], tail[-1]
    LOC.update({
        "t_loc": float(t_s), "t_P": float(first.t_s), "n_tail": len(tail),
        "tail_t": [round(float(x.t_s), 2) for x in tail],
        "tail_load_kN": [round(float(x.load_sum_N) / 1e3, 2) for x in tail],
        "tail_stroke_mm": [round(float(x.mean_motor_stroke_m) * 1e3, 2) for x in tail],
        "tail_att_deg": [np.round(np.degrees(np.asarray(x.raw_attitude_rad, float)), 4).tolist() for x in tail],
        "settle_deg": None if settle is None else np.round(np.degrees(np.asarray(settle, float)), 4).tolist(),
        "corner_c_tP_mm": np.round(first.corner_clearance_m * 1e3, 2).tolist(),
        "corner_c_tL_mm": np.round(last.corner_clearance_m * 1e3, 2).tolist(),
        "raw_bias_mm": np.round(self._corner_bias_m(first) * 1e3, 2).tolist(),
        "mean_load_kN": round(float(mean_load_N) / 1e3, 2),
    })
    return _orig_confirm(self, t_s, tail, mean_load_N)


c2.C2Config.with_10hz_d1 = preset
c2.C2Controller._level = traced_level
c2.C2Controller._confirm_liftoff = traced_confirm
c2.C2Controller._is_soil_stop_scope_met = cand_scope
c2.C2Controller._start_touch_twist_hold = cand_start_hold


def run(job: dict) -> dict:
    import r79_sensor_screen as screen

    CURRENT["kwargs"] = job.get("kwargs", {})
    CURRENT["over"] = job.get("over", {})
    CURRENT["cand"] = job.get("cand", {})
    TRACE.clear()
    LOC.clear()
    t0 = time.perf_counter()
    try:
        rec = screen.run_job(job["key"])
    except Exception as exc:  # the batch goes on; the error is reported
        return {"tag": job["tag"], "key": job["key"], "error": repr(exc)}
    base = rec.get("base", {})
    q = rec.get("r79", {})
    out = {"tag": job["tag"], "key": job["key"], "error": rec.get("error"),
           "sha": base.get("cmd_sha256") or base.get("commands_sha256"),
           "pass": base.get("pass"), "gates": base.get("gates"), "final": base.get("final_phase"),
           "t_ready": base.get("t_ready", base.get("t_ready_s")), "t_loc": q.get("t_loc_s"), "t_off": q.get("t_off_s"),
           "smax": q.get("max_true_stroke_mm"), "min_F": q.get("min_true_F_after_off_kN"),
           "stroke_max_run_mm": base.get("stroke_max_run_mm"), "stroke_end_mm": base.get("stroke_end_mm"),
           "clear": base.get("crawler_clearance_end_mm"), "minF_legs": base.get("min_F_after_liftoff_kN"),
           "guard": q.get("guard_events"), "warn_fault": q.get("warn_fault"), "c_min": q.get("c_min_tP_mm"),
           "pauses": q.get("lift_pauses"), "loc_minus_off": q.get("loc_minus_off_s"),
           "n_recontact": q.get("n_recontact_after_off"), "att_end": base.get("att_end_deg"),
           "events": [e for e in rec.get("events", []) if not str(e[1]).startswith(("leg_reapproach", "relevel_pred"))][:60],
           "r79": q, "base_keys": {k: base.get(k) for k in ("flags", "touch", "t_lift", "t_loc", "phase_path")},
           "loc": dict(LOC), "wall": round(time.perf_counter() - t0, 1)}
    if job.get("trace"):
        out["trace"] = list(TRACE)
    return out


def main() -> None:
    wt, jobs_path, out_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    if Path(wt).resolve() != ROOT:
        raise SystemExit(f"{wt} is not ACC_WT {ROOT}")
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done.add((row["tag"], row["key"]))
    todo = [j for j in jobs if (j["tag"], j["key"]) not in done]
    print(f"jobs {len(jobs)}, to run {len(todo)}, workers {workers}", flush=True)
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(todo) or 1))) as pool, out_path.open("a", encoding="utf-8") as sink:
        for n, row in enumerate(pool.imap_unordered(run, todo, chunksize=1), 1):
            sink.write(json.dumps(row, default=float) + "\n")
            sink.flush()
            print(f"[{n}/{len(todo)} {time.perf_counter() - t0:.0f} s] {row['tag']} {row['key']} final {row.get('final')} ready {row.get('t_ready')} "
                  f"loc {row.get('t_loc')} smax {row.get('smax')} err {row.get('error')}", flush=True)
    bad = acc_common.main_tree_modules()
    print("main-tree modules:", bad[:5], flush=True)


if __name__ == "__main__":
    main()
