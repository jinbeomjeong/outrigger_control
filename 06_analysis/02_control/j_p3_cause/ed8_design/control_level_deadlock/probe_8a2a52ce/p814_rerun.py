"""P8-14 (spec v8 draft, 12): LEVEL completion deadlock fix selection rerun, seen keys only.

Runs the edition 7 run commit worktree (``.claude/worktrees/ed7-impl``, C 8a2a52ce, imported
read-only; nothing in it is changed) with monkeypatches in each spawned worker.

Arms (``control_level_deadlock/report.md`` 2, 6; spec 3.8):
  B   = A + H3' (A: the key's edition 7 setting with probe_d6 {witness on, retract target off};
        H3': H-3 count 4 within T_r 0.5 s of the start, only on a run that is not a re-trigger,
        the same copy of ``C2Controller._end_finished_reapproaches`` as h3p_rerun.py).
  L1  = B + L-1: A(i)-b condition 3 (da) also opens when |D|(t) - |D|(t - W_r) > x_r,
        W_r 5 s, x_r 600 N (|D| history of the LEVEL periods kept on the LockStartB object,
        cleared outside LEVEL; wrapper of ``LockStartB._is_completion_open``).
  L2  = B + L-2: in the twist relax test the "not rising" condition is waived when some leg
        met A(i)-b conditions 1 and 2 (same-sign sub-hold command, stroke still < ib_still_m)
        for the whole window (consecutive LEVEL periods >= window_s / period_s, counted after
        each ``apply_floors``), the window rise (max - start) <= 2.5 kN and |D| + 0.5 kN <= 15 kN
        (wrapper of ``C2Controller._has_twist_load_stopped_rising``).
Record-only wrappers on every arm: re-approach starts / ends (p89_rerun), H-3 extensions, A(i)-b
shots (``_start_blind``), LEVEL -> DONE (``note_level_done``), L-1 openings, L-2 waivers.

Keys (report 6): (ga) G1 R12 bottom-FR-Fs4-RE1bF-ready o0.075 (VBM); (na) LSM4 R12 top-FR-Fs0
o0.05, VBMslow R12 top-FL-Fs0 o0.0; (da) four edition 5 VBK0 deadlock keys (r79 12b L2 lines,
plant VBKM0 with the stored rod fault entries; run through r79_L3L4_final.run_one with
R79_ROD_MODEL plant_truth); (ra) the other 17 P8-9 keys + VBM S4 e0.002, R2 e0.001, S8 e0.0.
Check job: the stored edition 5 setting VBK0 on L2|s40|g6|52 (expect the stored 606f8713
commands_sha256 d8ffb27c...).

Usage (dynamics-dev activated, PowerShell):
  conda run -n dynamics-dev python -I -B p814_rerun.py <raw_dir> [workers] [mask_hex] [limit]
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ED8 = HERE.parents[1]
P89_DIR = ED8 / "control_early_handover" / "probe_8a2a52ce"
NUMBA_CACHE = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba"
                   r"\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\dynamics-p814\numba_cache")
W_R_S, X_R_N = 5.0, 600.0                   # L-1 (ASSUMPTION, report 2)
WAIVER_RISE_N, WAIVER_MARGIN_N = 2500.0, 500.0   # L-2 (ASSUMPTION, report 2)
ARMS = ("B", "L1", "L2")
PLANTS = ("VBM", "LSM4", "VBMslow", "VBKM0")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


p89 = _load("p89_rerun", P89_DIR / "p89_rerun.py")

# ------------------------------------------------------------------ keys
VBK_FAULTS = {  # edition 5 606f8713 rod fault entries (ed5_design/aa_stop_606f8713/aa_inspect.json,
    # aa_detail.json); plan schema r79_rod_fault_plan/1
    "cand=current#L2|s40|g6|52|ref|J1|top|Fs0": ("12b-b1-s40-r044-RL-tau_C", "RL", "phase_exit:CHECK"),
    "cand=current#L2|s40|g6|56|ref|J2|top|Fs0": ("12b-b1-s40-r048-FL-tau_C", "FL", "phase_exit:CHECK"),
    "cand=current#L2|s40|g6|59|ref|J2|bottom|Fs4": ("12b-b1-s40-r051-FR-tau_R", "FR",
                                                    "retract_start_after:LEVEL"),
    "cand=current#L2|s41|ref|16|J1|B|0,0": ("12b-b2-s41-r164-RL-tau_C", "RL", "phase_exit:CHECK"),
}
VBK0_REPRO = ("cand=current#L2|s40|g6|52|ref|J1|top|Fs0",
              "d8ffb27c6a1bdd419283626e8ea34f8cb1903271f27010958629beb44671770a")


def _r12(plant, off, twin):
    return {"case": "R12", "eps": 0.0, "offset_s": off, "twin": twin, "plant": plant}


KEYS: list[tuple[str, str, dict]] = [
    ("ga", "bottom-FR-Fs4-RE1bF-ready-o0.075",
     _r12("VBM", 0.075, {"level": "bottom", "leg": "FR", "fs_kN": 4.0, "event": "RE1bF",
                         "timing": "ready"})),
    ("na", "LSM4-top-FR-Fs0-o0.05", _r12("LSM4", 0.05, {"level": "top", "leg": "FR", "fs_kN": 0.0})),
    ("na", "VBMslow-top-FL-Fs0-o0.0",
     _r12("VBMslow", 0.0, {"level": "top", "leg": "FL", "fs_kN": 0.0})),
    *[("da", k.split("#", 1)[1], {"r79_key": k, "plant": "VBKM0"}) for k in VBK_FAULTS],
    *[("ra", label, key) for group, label, key in p89.KEYS
      if label not in ("bottom-FR-Fs4-RE1bF-ready-o0.075", "LSM4-top-FR-Fs0-o0.05",
                       "VBMslow-top-FL-Fs0-o0.0")],
    ("ra", "S4-e0.002", {"case": "S4", "eps": 0.002, "plant": "VBM"}),
    ("ra", "R2-e0.001", {"case": "R2", "eps": 0.001, "plant": "VBM"}),
    ("ra", "S8-e0.0", {"case": "S8", "eps": 0.0, "plant": "VBM"}),
]


def job_of(key: dict, arm: str) -> dict:
    job = {k: v for k, v in key.items() if k != "plant"}
    job["setting"] = f"P814-{arm}-{key['plant']}"
    return job


def all_jobs() -> list[dict]:
    jobs = [job_of(key, arm) for _, _, key in KEYS for arm in ARMS]
    jobs.append({"r79_key": VBK0_REPRO[0], "setting": "VBK0"})
    return jobs


# ------------------------------------------------------------------ settings
def _settings() -> dict:
    import run_v5

    out = {}
    for plant in PLANTS:
        flow_on, options = run_v5.ALL_SETTINGS[plant]
        a_options = {**options, "probe_d6_settings": {"witness": True,
                                                      "retract_position_target": False}}
        for arm in ARMS:
            out[f"P814-{arm}-{plant}"] = (flow_on, dict(a_options))
    return out


# ------------------------------------------------------------------ patches
_LOG: dict = {"rise_open": [], "shots": [], "level_done": [], "waivers": [], "h3": [],
              "arm": None}


def install(arm: str) -> None:
    import numpy as np

    from outrigger_sim.control import c2
    from outrigger_sim.control import lock_start_b as lsb

    p89.install_patches("A")  # re-approach start / end record wrappers (no command change)
    if getattr(c2, "_p814_arm", None) is not None:
        return
    c2._p814_arm = arm
    _LOG["arm"] = arm
    tol = c2.REAPPROACH_WINDOW_TOLERANCE_S
    legs = c2.LEG_ORDER
    t_r, n_s = p89.T_R_S, p89.N_S

    # --- H3' (all arms of this probe)
    def end_finished(self, reading, loads_N, settings):
        # copy of C2Controller._end_finished_reapproaches (C 8a2a52ce c2.py 6277-6309), H3'
        state = self._state
        min_load_N = self.geometry.F_min_N
        exit_level_N = min_load_N + settings.exit_margin_N
        for leg, run in list(state.active_reapproaches.items()):
            travel = float(reading.motor_stroke_m[leg]) - run.start_motor_stroke_m
            if loads_N[leg] >= exit_level_N:
                run.exit_samples_seen += 1
            else:
                run.exit_samples_seen = 0
            required = settings.exit_samples
            if not run.is_retrigger and reading.t_s - run.start_s <= t_r + tol:
                required = n_s
            if (required > settings.exit_samples
                    and settings.exit_samples <= run.exit_samples_seen < required):
                _LOG["h3"].append({"t": float(reading.t_s), "leg": legs[leg]})
            if run.exit_samples_seen >= required:
                self._end_reapproach(leg, reading, "contact")
                self._add_event(reading.t_s, f"leg_reapproach_contact:{legs[leg]}")
                if self.config.lock_start_b.is_enabled:
                    self._end_event_order_on_contact(leg, reading.t_s)
            elif travel > settings.max_travel_m or settings.has_run_too_long(
                reading.t_s, run.start_s
            ):
                self._end_reapproach(leg, reading, "no_contact")
                state.is_reapproach_armed[leg] = False
                self._add_event(
                    reading.t_s,
                    f"WARN_LEG_REAPPROACH_NO_CONTACT:{legs[leg]}",
                    is_warning=True,
                )
        state.is_reapproach_armed |= loads_N >= min_load_N

    c2.C2Controller._end_finished_reapproaches = end_finished

    cls = lsb.LockStartB

    # --- record wrappers (all arms)
    orig_start_blind = cls._start_blind

    def start_blind(self, state, leg, inputs):
        _LOG["shots"].append({"t": float(inputs.t_s), "leg": legs[leg],
                              "sign": int(state.stretch_sign),
                              "D_N": float(getattr(inputs, "twist_load_N", math.nan))})
        return orig_start_blind(self, state, leg, inputs)

    cls._start_blind = start_blind

    orig_done = cls.note_level_done

    def note_done(self, t_s, path, twist_load_N):
        _LOG["level_done"].append({"t": float(t_s), "path": str(path),
                                   "D_N": float(twist_load_N)})
        return orig_done(self, t_s, path, twist_load_N)

    cls.note_level_done = note_done

    # --- per-period bookkeeping (all arms; record for B, used by L-1 / L-2)
    orig_apply = cls.apply_floors

    def apply_floors(self, inputs):
        hist = self.__dict__.setdefault("_p814_hist", [])
        twist = float(getattr(inputs, "twist_load_N", math.nan))
        if inputs.is_level and math.isfinite(twist):
            t = float(inputs.t_s)
            hist.append((t, abs(twist)))
            while hist and hist[0][0] < t - W_R_S - tol:
                hist.pop(0)
        else:
            hist.clear()
        out = orig_apply(self, inputs)
        counts = self.__dict__.setdefault("_p814_still", [0, 0, 0, 0])
        skip = self.settings.ib_reference_skip_reads
        for leg, state in enumerate(self._blind):
            ok = False
            if inputs.is_level and state.stretch_sign != 0 and len(state.stretch_reads) >= skip + 3:
                ok = self._blind_still_m(state) < self.settings.ib_still_m
            counts[leg] = counts[leg] + 1 if ok else 0
        return out

    cls.apply_floors = apply_floors

    if arm == "L1":
        orig_open = cls._is_completion_open

        def is_open(self, inputs):
            if orig_open(self, inputs):
                return True
            condition = lsb.BlindCondition(self.settings.ib_condition)
            if condition in (lsb.BlindCondition.LEVEL_INCOMPLETE,
                             lsb.BlindCondition.ATTITUDE_CLEARANCE):
                return False  # the rise clause belongs to (da), the with-twist condition
            hist = self.__dict__.get("_p814_hist") or []
            if not hist:
                return False
            t_now, d_now = hist[-1]
            t0, d0 = hist[0]
            if t_now - t0 < W_R_S - tol:
                return False
            if d_now - d0 > X_R_N:
                _LOG["rise_open"].append({"t": float(t_now), "absD_N": d_now,
                                          "rise_N": d_now - d0})
                return True
            return False

        cls._is_completion_open = is_open

    if arm == "L2":
        orig_rise = c2.C2Controller._has_twist_load_stopped_rising

        def stopped_rising(self, history):
            if orig_rise(self, history):
                return True
            lsb_state = self._state.lock_start_b
            if lsb_state is None:
                return False
            counts = lsb_state.__dict__.get("_p814_still") or [0, 0, 0, 0]
            settings = self.config.twist_completion_relax
            need = int(round(settings.window_s / self.config.period_s))
            start_N = history[0][1]
            newest_N = history[-1][1]
            rise_N = max(d for _, d in history) - start_N
            legs_ok = [legs[i] for i, c in enumerate(counts) if c >= need]
            if (legs_ok and rise_N <= WAIVER_RISE_N
                    and newest_N + WAIVER_MARGIN_N <= settings.max_twist_N):
                _LOG["waivers"].append({"t": float(history[-1][0]), "absD_N": newest_N,
                                        "rise_N": rise_N, "legs": legs_ok,
                                        "counts": [int(c) for c in counts]})
                return True
            return False

        c2.C2Controller._has_twist_load_stopped_rising = stopped_rising
    _ = np  # numpy imported for the patched module context


# ------------------------------------------------------------------ worker
def worker(job: dict) -> dict:
    raw = Path(job.pop("_raw"))
    mask = job.pop("mask", None)
    p89._paths()
    os.chdir(p89.WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(_settings())
    names = tuple(n for n in _settings() if n not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *names)
    run_v5.ROD_FAULT_SETTINGS = (*run_v5.ROD_FAULT_SETTINGS,
                                 *(n for n in _settings() if n.endswith("-VBKM0")))
    setting = job["setting"]
    arm = setting.split("-")[1] if setting.startswith("P814-") else "B0"
    t0 = time.perf_counter()
    if "r79_key" in job:
        key = job["r79_key"]
        plan = raw / "plans" / f"{setting}.json"
        tag = setting.replace("-", "_")
        os.environ.update({"R79_V5_SETTING": setting, "R79_ROD_MODEL": "plant_truth",
                           "R79_T4H_DIR": str(raw / f"t4h_r79_{tag}"),
                           "R79_ROD_FAULT_PLAN": str(plan)})
        (raw / f"t4h_r79_{tag}").mkdir(parents=True, exist_ok=True)
        s8 = p89.WT / "04_scripts" / "03_control" / "s8"
        if str(s8) not in sys.path:
            sys.path.insert(0, str(s8))
        # r51_reapp_closed_loop reads the project root from sys.argv[1] (the r79 CLI passes it):
        # the run worktree, as the r79 runner is started from it
        sys.argv = [sys.argv[0], str(p89.WT)]
        if mask is not None:  # as run_v5.run_one does for its jobs
            import s9_soil_slope as slope

            slope.set_parent_affinity(int(mask))
        if arm != "B0":
            install(arm)
        else:
            p89.install_patches("A")  # record wrappers only (VBK0 check job)
        import r79_L3L4_final as final

        record = final.run_one(key)
        stem = tag + "__" + key.split("#", 1)[1].replace("|", "_").replace(",", "_")
    else:
        install(arm)
        record = run_v5.run_one(dict(job, t4h_dir=str(raw / "t4h"), mask=mask))
        record["job"] = {k: v for k, v in job.items() if k != "t4h_dir"}
        stem = run_v5.t4h_file_name(job)[:-4]
    logs = raw / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{stem}_p814.json").write_text(
        json.dumps({"p814": _LOG, "reapp": {"starts": p89._LOG["starts"],
                                            "ends": p89._LOG["ends"]}}, default=str),
        encoding="utf-8")
    from outrigger_sim.control import c2

    record["p814"] = {"stem": stem, "arm": arm, "setting": setting,
                      "patched_arm": getattr(c2, "_p814_arm", None),
                      "end_finished": c2.C2Controller._end_finished_reapproaches.__name__,
                      "n_rise_open": len(_LOG["rise_open"]), "n_waivers": len(_LOG["waivers"]),
                      "n_shots": len(_LOG["shots"]), "n_h3": len(_LOG["h3"]),
                      "worker_wall_s": round(time.perf_counter() - t0, 1)}
    record["p814_job"] = {k: v for k, v in job.items() if k != "t4h_dir"}
    return record


def write_plans(raw: Path) -> None:
    plans = raw / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    faults = {k: {"fault_id": f, "leg": leg, "kind": "STUCK", "value_bar": -100.0,
                  "anchor": anchor, "delay_reads": 0} for k, (f, leg, anchor) in VBK_FAULTS.items()}
    names = [f"P814-{arm}-VBKM0" for arm in ARMS] + ["VBK0"]
    for name in names:
        path = plans / f"{name}.json"
        text = json.dumps({"schema": "r79_rod_fault_plan/1", "faults": faults}, indent=1) + "\n"
        if not path.exists():
            path.write_text(text, encoding="utf-8")


def main() -> int:
    raw = Path(sys.argv[1]).resolve()
    workers = min(int(sys.argv[2]) if len(sys.argv) > 2 else 8, 8)
    mask = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    os.environ["NUMBA_CACHE_DIR"] = str(NUMBA_CACHE)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    write_plans(raw)
    out = raw / "runs.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add(json.dumps(r["p814_job"], sort_keys=True))
    todo = [j for j in all_jobs() if json.dumps(j, sort_keys=True) not in done]
    # long r79 lines first
    todo.sort(key=lambda j: 0 if "r79_key" in j else 1)
    print(f"todo {len(todo)} of {len(all_jobs())}", flush=True)
    if limit is not None:
        todo = todo[:limit]
    jobs = [dict(j, _raw=str(raw), mask=mask) for j in todo]
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for n, rec in enumerate(pool.imap_unordered(worker, jobs), 1):
            handle.write(json.dumps(rec, default=str) + "\n")
            handle.flush()
            state = (rec.get("error") or "")[:300] or f"{rec.get('wall_s')} s"
            print(f"{n}/{len(jobs)} {rec['p814_job']['setting']} "
                  f"{rec['p814_job'].get('r79_key') or rec['p814_job'].get('case')} "
                  f"{rec['p814_job'].get('offset_s')} {rec['p814_job'].get('eps')}: {state}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
