"""K1 soil harness phase sweep (sweep_criteria.md). One arm per process: A = c4g2, B = both, Af / Bf = forced hold, off = off.

Usage: python -I -B sweep_run.py <arm> <out.jsonl> [--workers 8] [--limit N]
Env: ACC_WT. The pinned checkout is used through acc_common (preset defaults only, no source change). Forced arms replace
the D_hat samples at TOUCH -> LEVEL inside this process. Each worker caches the base state per row and deep-copies it per phase.
Result rows are appended as they finish; suffix minima go to <out>.npz at the end.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "c4g2k1"))
ARM = os.environ.get("SWEEP_ARM") or (sys.argv[1] if len(sys.argv) > 1 else "B")
COMBO = {"A": "c4g2", "B": "both", "Af": "c4g2", "Bf": "both", "off": "off"}[ARM]
FORCE = ARM in ("Af", "Bf")
os.environ["SWEEP_ARM"] = ARM
os.environ["ACC_COMBO"] = COMBO
os.environ.setdefault("ACC_WT", str(HERE.parent / "cad_c4g2" / "wt"))
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[name] = "1"
import acc_common  # noqa: E402

acc_common.install()
import numpy as np  # noqa: E402

ROOT = Path(os.environ["ACC_WT"])
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))
_argv = sys.argv
sys.argv = [_argv[0], str(ROOT)]
import s9_soil_event_screen as scr  # noqa: E402

sys.argv = _argv

ROWS = {"FLFs0": ("G1", "FL", 0.0), "FLFs8": ("G1", "FL", 8.0), "RRFs0": ("G1", "RR", 0.0)}
PHASES = [round(0.01 * k, 2) for k in range(11)] + [0.2, 0.35, 0.5, 0.7]
FORCED_D_HAT_N = 5169.074268280452
"""Chrono twist_load_estimate_N of the F_s 0 rows."""
LEGS = ("FL", "FR", "RL", "RR")
_CACHE: dict = {}
SUFFIX_S = 8.0


def force_hold(c2) -> None:
    original = c2.C2Controller._start_touch_twist_hold

    def wrapped(self, reading):
        hold = self._state.touch_twist
        if hold is not None:
            n = max(1, len(hold.twist_loads_N))
            hold.twist_loads_N.clear()
            hold.twist_loads_N.extend([FORCED_D_HAT_N] * n)
        return original(self, reading)

    c2.C2Controller._start_touch_twist_hold = wrapped


def base_state(row: str):
    if row in _CACHE:
        return _CACHE[row]
    soil, leg, fs = ROWS[row]
    scr._s8_modules()["r51"].place_worker()
    cl, c2, Meas = scr.sl._imports()
    if FORCE and not getattr(c2.C2Controller, "_sweep_forced", False):
        force_hold(c2)
        c2.C2Controller._sweep_forced = True
    plant, ctrl, info = scr.make_event_base(cl, c2, soil, scr.LEVEL, scr.PAD, fs)
    p2, c_2 = copy.deepcopy(plant), copy.deepcopy(ctrl)
    base = scr.run_base_soil(cl, Meas, p2, c_2, "two", hold_after_ready_s=scr.READY_DELAY_S - scr.PRE_S)
    t_level = base["t_loc"] + 0.5 * (base["t_done"] - base["t_loc"])
    lv = scr.run_base_soil(cl, Meas, plant, ctrl, "two", stop_t=t_level - scr.PRE_S)
    meta = {k: base[k] for k in ("t_lift", "t_loc", "t_done", "t_ready", "commands_sha256", "stroke_max_mm")}
    hold = ctrl._touch_twist_hold_meta()
    meta["hold"] = {k: hold.get(k) for k in ("twist_load_estimate_N", "target_m", "start_t_s", "end_t_s", "end_reason", "end_error_m")}
    meta["t_level"] = t_level
    _CACHE[row] = (cl, c2, Meas, plant, ctrl, lv, meta)
    return _CACHE[row]


def run_one(task):
    row, delta = task
    t0 = time.perf_counter()
    try:
        cl, c2, Meas, plant0, ctrl0, lv, meta = base_state(row)
        soil, leg, fs = ROWS[row]
        plant, ctrl = copy.deepcopy(plant0), copy.deepcopy(ctrl0)
        t_ev = plant.t + scr.PRE_S + delta
        branch = scr.branch_soil(cl, Meas, plant, ctrl, lv["cmd"].copy(), lv["valve"].copy(), "RE1bF", LEGS.index(leg), t_ev, "two")
        judged = scr.judge_soil_event(branch, fs, ctrl.geometry.head_area_m2, lv["stroke_max_mm"])
        rows = branch.rows
        t = rows[:, 0] - t_ev
        F = rows[:, 5:9]
        D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
        keep = (t >= 0.0) & (t <= SUFFIX_S)
        suffix = np.minimum.accumulate(F[::-1], axis=0)[::-1][keep].astype(np.float32)
        d_prof = {f"{x:g}": round(float(D[(t >= x) & (t < x + 0.5)].mean()) / 1e3, 2) for x in (2, 3, 4, 5, 6, 8, 10) if ((t >= x) & (t < x + 0.5)).any()}
        out = {"row": row, "arm": ARM, "delta": delta, "t_ev": t_ev, "commands_sha256": branch.commands_sha256, "wall_s": round(time.perf_counter() - t0, 1), "base": meta,
               "n_deferred_retrigger": sum(1 for _, n in branch.events if n.startswith("leg_reapproach_deferred") and n.endswith(":retrigger")),
               "deferred": [[tt, n] for tt, n in branch.events if n.startswith("leg_reapproach_deferred")], "D_profile_kN": d_prof,
               "F_ev_pre_kN": [round(float(x) / 1e3, 3) for x in F[(t >= -0.3) & (t < 0)].mean(axis=0)], "D_pre_kN": round(float(D[(t >= -0.3) & (t < 0)].mean()) / 1e3, 3),
               "phase_final": str(ctrl.phase), "pid": os.getpid()}
        for k in ("pass", "gates", "lifts", "pair", "pair_union_s", "pair_last_touch_s", "W_end_s", "adj_lift_sum_W_s", "adj_max_gap_W_mm", "adj_lift_outside_W_s", "adj_min_F_in_W_kN", "min_F_after_W_kN", "min_F_after_event_kN", "fault_periods", "fault_events", "final_phase", "t_ready_back_s", "att_end_deg", "max_att_change_deg", "reapproach_starts", "n_late_starts", "sign_changes", "warnings", "flags", "pressure", "crawler", "stroke_max_run_mm", "margins"):
            out[k] = judged.get(k)
        return out, suffix, t[keep].astype(np.float32)
    except Exception as exc:  # noqa: BLE001 - a row keeps its error, the sweep goes on
        import traceback

        return {"row": row, "arm": ARM, "delta": delta, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2500:]}, None, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    me = ap.parse_args()
    scr.set_parent_affinity(os.environ.setdefault("SWEEP_MASK", "0x00FF0000"))
    rows =("FLFs0", "RRFs0") if FORCE else tuple(ROWS)
    tasks = [(r, d) for d in PHASES for r in rows]
    if me.limit:
        tasks = tasks[: me.limit]
    out = Path(me.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    arrays = {}
    t0 = time.perf_counter()
    with out.open("w", encoding="utf-8") as fh, Pool(min(me.workers, len(tasks))) as pool:
        for rec, suf, tt in pool.imap_unordered(run_one, tasks, chunksize=1):
            fh.write(json.dumps(rec, default=float) + "\n")
            fh.flush()
            if suf is not None:
                key = f"{rec['row']}_{rec['delta']:.2f}"
                arrays[key + "_sufmin"] = suf
                arrays[key + "_t"] = tt
            print(rec["row"], rec["delta"], rec.get("error", "ok"), rec.get("wall_s"), round(time.perf_counter() - t0), flush=True)
    np.savez_compressed(out.with_suffix(".npz"), **arrays)
    prov = acc_common.provenance()
    prov.update(arm=ARM, forced=FORCE, n_tasks=len(tasks), wall_s=round(time.perf_counter() - t0, 1), affinity=os.environ.get("SWEEP_MASK"), main_tree_modules=acc_common.main_tree_modules())
    out.with_suffix(".prov.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print("done", prov["wall_s"], flush=True)


if __name__ == "__main__":
    main()
