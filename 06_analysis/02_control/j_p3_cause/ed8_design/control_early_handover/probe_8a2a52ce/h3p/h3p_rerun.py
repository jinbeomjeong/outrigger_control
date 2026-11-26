"""H3' check (user decision 2026-11-26, after the P8-9 diagnosis): H-3 applied only to runs that
are not re-triggers (``not run.is_retrigger``), T_r 0.5 s and N_s 4 unchanged.

Runs ``run_v5.run_one`` of the edition 7 run commit worktree (C 8a2a52ce, imported read-only) with
the p89_rerun record wrappers (arm A path, no command change) plus the H3' copy of
``C2Controller._end_finished_reapproaches`` (C 8a2a52ce c2.py 6277-6309 with the H-3 count rule
limited to non re-trigger runs).

Jobs (seen keys only, setting P89-H3p-<plant>):
  the six "run needed" lines of diag/report.md 2.3: R15 o0.0 / o0.05, R16 o0.0 / o0.025 / o0.075,
  R12 top-FL-Fs8-RE1bF-level o0.0;
  check line: R12 bottom-FR-Fs0-RE1bF-ready o0.0 (H3' must equal the stored H3 line 1bf3a48c...,
  its only H-3 extension is on a first run).

Usage (dynamics-dev activated, PowerShell):
  conda run -n dynamics-dev python -I -B h3p_rerun.py <raw_dir> [workers] [mask_hex]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent
NUMBA_CACHE = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba"
                   r"\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\dynamics-p89h3p\numba_cache")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


p89 = _load("p89_rerun", PROBE / "p89_rerun.py")
p89.ARM_PARAMS["H3p"] = {"h3": (p89.T_R_S, p89.N_S), "first_run_only": True}

LABELS = ("R15-o0.0", "R15-o0.05", "R16-o0.0", "R16-o0.025", "R16-o0.075",
          "top-FL-Fs8-RE1bF-level-o0.0", "bottom-FR-Fs0-RE1bF-ready-o0.0")
KEYS = {label: key for _, label, key in p89.KEYS if label in LABELS}
JOBS = [p89.job_of(KEYS[label], "H3p") for label in LABELS]
_H3P_LOG: list = []


def install_h3p() -> None:
    from outrigger_sim.control import c2

    p89.install_patches("A")  # record wrappers only (no command change)
    if getattr(c2, "_h3p_patched", False):
        return
    c2._h3p_patched = True
    c2._p89_arm = "H3p"
    p89._LOG["arm"], p89._LOG["params"] = "H3p", {"h3": [p89.T_R_S, p89.N_S],
                                                  "first_run_only": True}
    tol = c2.REAPPROACH_WINDOW_TOLERANCE_S
    legs = c2.LEG_ORDER
    t_r, n_s = p89.T_R_S, p89.N_S

    def end_finished(self, reading, loads_N, settings):
        # copy of C2Controller._end_finished_reapproaches (C 8a2a52ce c2.py 6277-6309);
        # H3': the H-3 count only on a run that is not a re-trigger
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
            self.__dict__.setdefault("_p89_required", {})[leg] = required
            if (required > settings.exit_samples
                    and settings.exit_samples <= run.exit_samples_seen < required):
                p89._LOG["h3"].append({"ctrl": id(self), "t": float(reading.t_s),
                                       "leg": legs[leg], "start_s": float(run.start_s),
                                       "seen": int(run.exit_samples_seen),
                                       "required": int(required),
                                       "retrigger": bool(run.is_retrigger)})
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


def worker(job: dict) -> dict:
    raw = Path(job.pop("_raw"))
    p89._paths()
    os.chdir(p89.WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(p89._settings())
    install_h3p()
    from outrigger_sim.control import c2

    t0 = time.perf_counter()
    record = run_v5.run_one(job)
    stem = run_v5.t4h_file_name(job)[:-4]
    logs = raw / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{stem}_p89.json").write_text(json.dumps(p89._LOG, default=str), encoding="utf-8")
    import outrigger_sim

    record["p89"] = {"stem": stem, "arm": "H3p", "patched_arm": getattr(c2, "_p89_arm", None),
                     "params": p89._LOG["params"],
                     "end_finished_is_patched": c2.C2Controller._end_finished_reapproaches.__name__,
                     "outrigger_sim_file": str(Path(outrigger_sim.__file__).resolve()),
                     "n_h3": len(p89._LOG["h3"]),
                     "worker_wall_s": round(time.perf_counter() - t0, 1)}
    return record


def main() -> int:
    raw = Path(sys.argv[1]).resolve()
    workers = min(int(sys.argv[2]) if len(sys.argv) > 2 else 7, 8)
    mask = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    os.environ["NUMBA_CACHE_DIR"] = str(NUMBA_CACHE)
    NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    out = raw / "runs.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add(json.dumps({k: v for k, v in r["job"].items()
                                     if k not in ("mask", "t4h_dir")}, sort_keys=True))
    todo = [dict(job, mask=mask, t4h_dir=None, _raw=str(raw)) for job in JOBS
            if json.dumps(job, sort_keys=True) not in done]
    print(f"todo {len(todo)} of {len(JOBS)}", flush=True)
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for n, rec in enumerate(pool.imap_unordered(worker, todo), 1):
            rec["job"] = {k: v for k, v in rec["job"].items() if k != "_raw"}
            handle.write(json.dumps(rec, default=str) + "\n")
            handle.flush()
            state = (rec.get("error") or "")[:300] or f"{rec.get('wall_s')} s"
            print(f"{n}/{len(todo)} {rec['job']['setting']} {rec['job']['case']} "
                  f"{rec['job'].get('offset_s')}: {state}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
