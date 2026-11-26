"""U832 / o0.0 (edition 8 design input): instrumented reruns of seen keys only.

Runs ``run_v5.run_one`` of the edition 7 run commit worktree (``.claude/worktrees/ed7-impl``,
C 8a2a52ce, imported read-only; nothing in it is changed) with record-only patches in each
spawned worker:

* ``C2Controller._update_lifted_reapproach``: per control period the lower load estimate of every
  leg, the start level (``load_fraction_of_F_min F_min``) and exit level (``F_min + exit_margin``),
  the low counts before / after, the active re-approaches (leg, start, exit_samples_seen), touched
  and armed flags, phase;
* ``r67_g1_screen.judge_event``: the 1 ms plant rows of the event branch (t, pad contact force 4,
  true cylinder force 4, valve 4, pad gap 4, attitude 2) from event - 0.5 s to event + 6 s;
* ``harness_flow.FlowLimiter.limit``: the first time each leg's oil force exceeds 3 kN (the eps
  touch criterion of ``run_v5._install_approach_scale``) and the plant time of the call.

No patch changes a command (``commands_sha256`` of the VBM arm is compared with the stored
edition 7 G1 / j9main line in ``u11``).

Jobs (keys already run and published; no held-out candidate is run):
  V0 (run_v5 setting ``V0``)  bottom FL-Fs2 and FR-Fs4 RE1bF ready at the four stored V0 grid
                              offsets 0 / 0.025 / 0.05 / 0.075 s (stored grid r69_bottom).
  VBM (edition 7 a2, sealed)  the three G1 failures (o0.0), the three edition 6 U832 keys (o0.0)
                              and the three G1 lines of the U832 clusters (their G1 offsets).
  U8-A (direction A: VBM with probe_d6 witness on, retract_position_target off)
                              the three G1 failures and the three edition 6 U832 keys only.
  S7 VBM eps 0 / 0.001        (j9main keys) for the eps touch-time shift.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I -B u10_instrumented_rerun.py <scratch_dir> [workers] [mask]
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
COUPLED = WT / "04_scripts" / "04_hydraulic" / "coupled"


def _tw(level, leg, fs, event):
    return {"level": level, "leg": leg, "fs_kN": fs, "event": event, "timing": "ready"}


G1_FAIL = [("bottom", "FR", 0.0, "RE1bF", 0.0), ("bottom", "FL", 4.0, "RE1bF", 0.0),
           ("bottom", "FR", 8.0, "FS24", 0.0)]
ED6_U832 = [("bottom", "FL", 2.0, "RE1bF", 0.0), ("bottom", "FR", 2.0, "RE1bF", 0.0),
            ("bottom", "FR", 4.0, "RE1bF", 0.0)]
G1_U832_CLUSTER = [("bottom", "FL", 2.0, "RE1bF", 0.025), ("bottom", "FR", 2.0, "RE1bF", 0.075),
                   ("bottom", "FR", 4.0, "RE1bF", 0.075)]
V0_KEYS = [("bottom", leg, fs, "RE1bF", off) for leg, fs in (("FL", 2.0), ("FR", 4.0))
           for off in (0.0, 0.025, 0.05, 0.075)]


def _job(k, setting):
    level, leg, fs, event, off = k
    return {"case": "R12", "eps": 0.0, "offset_s": off, "twin": _tw(level, leg, fs, event),
            "setting": setting}


JOBS = ([_job(k, "V0") for k in V0_KEYS]
        + [_job(k, "VBM") for k in G1_FAIL + ED6_U832 + G1_U832_CLUSTER]
        + [_job(k, "U8-A") for k in G1_FAIL + ED6_U832]
        + [{"case": "S7", "eps": e, "setting": "VBM"} for e in (0.0, 0.001)])


def _paths() -> None:
    for p in (COUPLED, WT / "03_src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _settings() -> dict:
    import run_v5

    flow_on, options = run_v5.ALL_SETTINGS["VBM"]
    a_options = {**options, "probe_d6_settings": {"witness": True,
                                                  "retract_position_target": False}}
    return {"U8-A": (flow_on, a_options)}


_LOG: dict = {"reapp": [], "rows": None, "touch": {}, "config": None}


def _install_patches() -> None:
    import harness_flow
    import s9_soil_event_screen as study_a
    from outrigger_sim.control import c2

    if getattr(c2, "_u8_patched", False):
        return
    c2._u8_patched = True
    import numpy as np

    orig = c2.C2Controller._update_lifted_reapproach

    def upd(self, reading):
        st = self._state
        settings = self.config.r8.lifted_reapproach
        if _LOG["config"] is None:
            _LOG["config"] = {k: (v if isinstance(v, int | float | bool | type(None)) else str(v))
                              for k, v in vars(settings).items()}
        before = [int(x) for x in st.reapproach_low_counts]
        orig(self, reading)
        try:
            loads = self._load_estimate_N(reading.cylinder_force_lower_N)
        except Exception:
            loads = np.full(4, np.nan)
        fmin = float(self.geometry.F_min_N)
        _LOG["reapp"].append({
            "t": float(reading.t_s), "phase": str(st.phase), "is_lifted": bool(st.is_lifted),
            "load_lower_N": [float(x) for x in loads],
            "force_lower_N": [float(x) for x in reading.cylinder_force_lower_N],
            "start_level_N": float(settings.load_fraction_of_F_min * fmin),
            "exit_level_N": fmin + float(settings.exit_margin_N),
            "low_before": before, "low_after": [int(x) for x in st.reapproach_low_counts],
            "active": {str(k): {"start_s": float(r.start_s),
                                "exit_seen": int(r.exit_samples_seen),
                                "retrigger": bool(r.is_retrigger)}
                       for k, r in st.active_reapproaches.items()},
            "touched": [bool(x) for x in st.touched],
            "armed": [bool(x) for x in st.is_reapproach_armed]})

    c2.C2Controller._update_lifted_reapproach = upd

    r67 = study_a._s8_modules()["r67"]
    orig_judge = r67.judge_event

    def judge(rec, phases, events, crawler, t_ev, t_ready_back, ev, leg, ctrl, att0):
        rows = np.asarray(rec)
        w = (rows[:, 0] >= t_ev - 0.5) & (rows[:, 0] <= t_ev + 6.0)
        _LOG["rows"] = {"t_ev": float(t_ev), "rows": rows[w, :19]}
        return orig_judge(rec, phases, events, crawler, t_ev, t_ready_back, ev, leg, ctrl, att0)

    r67.judge_event = judge

    orig_limit = harness_flow.FlowLimiter.limit

    def limit(self, t_s, u, oil_force_N):
        f = np.asarray(oil_force_N, float)
        for i in range(4):
            if str(i) not in _LOG["touch"] and f[i] > 3000.0:
                _LOG["touch"][str(i)] = float(t_s)
        return orig_limit(self, t_s, u, oil_force_N)

    harness_flow.FlowLimiter.limit = limit


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    mask = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "runs.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add(json.dumps({k: v for k, v in r["job"].items()
                                     if k not in ("mask", "t4h_dir")}, sort_keys=True))
    todo = [{**job, "mask": mask, "t4h_dir": None} for job in JOBS
            if json.dumps(job, sort_keys=True) not in done]
    # the log folder travels in a separate key so run_v5 writes no T4h file
    for job in todo:
        job["t4h_dir"] = None
    jobs = [dict(j, _scratch=str(scratch)) for j in todo]
    print(f"todo {len(jobs)} of {len(JOBS)}", flush=True)
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for n, rec in enumerate(pool.imap_unordered(_worker_entry, jobs), 1):
            handle.write(json.dumps(rec, default=str) + "\n")
            handle.flush()
            state = (rec.get("error") or "")[:300] or f"{rec.get('wall_s')} s"
            print(f"{n}/{len(jobs)} {rec['job']['setting']} {rec['job']['case']} "
                  f"{rec['job'].get('offset_s')} {rec['job'].get('twin')}: {state}", flush=True)
    return 0


def _worker_entry(job: dict) -> dict:
    scratch = job.pop("_scratch")
    job = dict(job)
    rec_job = dict(job)
    job_for_run = dict(job)
    job_for_run["t4h_dir"] = None
    out = worker_with(job_for_run, Path(scratch))
    out["job"] = {k: v for k, v in rec_job.items() if k != "_scratch"}
    return out


def worker_with(job: dict, scratch: Path) -> dict:
    _paths()
    os.chdir(WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(_settings())
    _install_patches()
    t0 = time.perf_counter()
    record = run_v5.run_one(job)
    stem = run_v5.t4h_file_name(job)[:-4]
    logs = scratch / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    import numpy as np

    payload = {"reapp": _LOG["reapp"], "touch": _LOG["touch"], "config": _LOG["config"]}
    (logs / f"{stem}_reapp.json").write_text(json.dumps(payload, default=str), encoding="utf-8")
    if _LOG["rows"] is not None:
        np.savez_compressed(logs / f"{stem}_rows.npz", t_ev=_LOG["rows"]["t_ev"],
                            rows=_LOG["rows"]["rows"])
    import outrigger_sim
    record["u8"] = {"stem": stem, "outrigger_sim_file": str(Path(outrigger_sim.__file__).resolve()),
                    "worker_wall_s": round(time.perf_counter() - t0, 1)}
    return record


if __name__ == "__main__":
    sys.exit(main())
