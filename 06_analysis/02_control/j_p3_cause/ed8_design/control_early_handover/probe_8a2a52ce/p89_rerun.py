"""P8-9 (edition 8 spec draft revision 1, 12): early-handover candidate selection rerun.

Runs ``run_v5.run_one`` of the edition 7 run commit worktree (``.claude/worktrees/ed7-impl``,
C 8a2a52ce, imported read-only; nothing in it is changed) on the 20 seen keys of
``control_early_handover/report.md`` 7 with three controller arms:

* ``A``  = direction A (U8-A / D8-*-A): the key's sealed edition 7 setting with
  ``probe_d6_settings`` = {witness on, retract_position_target off}.
* ``H3`` = A + H-3 (spec 3.7): a re-approach whose contact exit falls within ``T_R`` (0.5 s) of
  its start needs ``N_S`` (4) consecutive exit samples instead of ``exit_samples`` (3).
* ``H1`` = A + H-1 (spec 3.7): after a re-approach of leg p ends on contact, the diagonal leg d
  of p does not start (re-approach or B3 pre-twist) within ``W_D`` (0.6 s) of that end until a
  sample of d's lower load estimate at or above the start level was seen after the end.

Check arms (patch identity, not part of the selection): ``H3n3`` = the H-3 code path with
``N_S`` = 3 (must equal A), ``H1off`` = the H-1 code path with ``W_D`` < 0 (must equal A).

The candidate rules are monkeypatches of ``C2Controller`` methods inside each spawned worker
(``_end_finished_reapproaches`` replaced by a copy with the H-3 count rule; for H-1 wrappers of
``_start_reapproaches`` (landing-sample bookkeeping), ``_defers_reapproach`` / ``_deferred_event_name``
(the wait and its event ``leg_reapproach_deferred:<leg>:handover``), ``_may_start_pre_twist`` (B3)
and ``_end_reapproach`` (the last end)). Record-only wrappers (``_begin_reapproach``,
``_end_reapproach``) run on every arm and change no command.

Usage (dynamics-dev activated, PowerShell):
  conda run -n dynamics-dev python -I -B p89_rerun.py selftest
  conda run -n dynamics-dev python -I -B p89_rerun.py check <raw_dir> [workers] [mask_hex]
  conda run -n dynamics-dev python -I -B p89_rerun.py main  <raw_dir> [workers] [mask_hex]
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
COUPLED = WT / "04_scripts" / "04_hydraulic" / "coupled"
NUMBA_CACHE = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba"
                   r"\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\dynamics-p89\numba_cache")

T_R_S = 0.5        # H-3 short-run time (ASSUMPTION, spec 3.7)
N_S = 4            # H-3 exit samples inside T_R (ASSUMPTION, spec 3.7)
W_D_S = 0.6        # H-1 diagonal wait window (ASSUMPTION, spec 3.7)
DIAGONAL = {0: 3, 3: 0, 1: 2, 2: 1}  # FL<->RR, FR<->RL (leg order FL FR RL RR)
HANDOVER_REASON = "handover"

ARM_PARAMS = {
    "A": {},
    "H3": {"h3": (T_R_S, N_S)},
    "H1": {"h1": W_D_S},
    "H3n3": {"h3": (T_R_S, 3)},
    "H1off": {"h1": -1.0},
}
SELECTION_ARMS = ("A", "H3", "H1")
PLANTS = ("VBM", "LSM4", "VBMslow")


def _tw(level, leg, fs, event=None, timing=None):
    twin = {"level": level, "leg": leg, "fs_kN": fs}
    if event is not None:
        twin.update(event=event, timing=timing)
    return twin


def _r12(plant, off, twin):
    return {"case": "R12", "eps": 0.0, "offset_s": off, "twin": twin, "plant": plant}


# (group, label, job without setting, plant) - report.md 7, all seen keys
KEYS: list[tuple[str, str, dict]] = [
    *[("U", f"bottom-{leg}-Fs{fs:g}-RE1bF-ready-o0.0",
       _r12("VBM", 0.0, _tw("bottom", leg, fs, "RE1bF", "ready")))
      for leg, fs in (("FR", 0.0), ("FL", 4.0), ("FL", 2.0), ("FR", 2.0), ("FR", 4.0))],
    ("U_FS24", "bottom-FR-Fs8-FS24-ready-o0.0",
     _r12("VBM", 0.0, _tw("bottom", "FR", 8.0, "FS24", "ready"))),
    *[("phase", f"bottom-{leg}-Fs{fs:g}-RE1bF-ready-o{off}",
       _r12("VBM", off, _tw("bottom", leg, fs, "RE1bF", "ready")))
      for leg, fs, off in (("FL", 2.0, 0.025), ("FR", 2.0, 0.075), ("FR", 4.0, 0.075))],
    *[("regression", f"R15-o{off}", {"case": "R15", "eps": 0.0, "offset_s": off, "plant": "VBM"})
      for off in (0.0, 0.05)],
    *[("regression", f"R16-o{off}", {"case": "R16", "eps": 0.0, "offset_s": off, "plant": "VBM"})
      for off in (0.0, 0.025, 0.05, 0.075)],
    ("regression", "LSM4-top-FR-Fs0-o0.05", _r12("LSM4", 0.05, _tw("top", "FR", 0.0))),
    ("regression", "VBMslow-top-FL-Fs0-o0.0", _r12("VBMslow", 0.0, _tw("top", "FL", 0.0))),
    ("regression", "S7-e0.002", {"case": "S7", "eps": 0.002, "plant": "VBM"}),
    ("regression", "top-FR-Fs8-o0.0", _r12("VBM", 0.0, _tw("top", "FR", 8.0))),
    ("regression", "top-FL-Fs8-RE1bF-level-o0.0",
     _r12("VBM", 0.0, _tw("top", "FL", 8.0, "RE1bF", "level"))),
]


def job_of(key: dict, arm: str) -> dict:
    job = {k: v for k, v in key.items() if k != "plant"}
    job["setting"] = f"P89-{arm}-{key['plant']}"
    return job


def main_jobs() -> list[dict]:
    return [job_of(key, arm) for _, _, key in KEYS for arm in SELECTION_ARMS]


def check_jobs() -> list[dict]:
    key = KEYS[0][2]  # U: bottom-FR-Fs0-RE1bF-ready o0.0
    return [job_of(key, arm) for arm in ("A", "H3", "H1", "H3n3", "H1off")]


def _paths() -> None:
    for p in (COUPLED, WT / "03_src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _settings() -> dict:
    import run_v5

    out = {}
    for plant in PLANTS:
        flow_on, options = run_v5.ALL_SETTINGS[plant]
        a_options = {**options, "probe_d6_settings": {"witness": True,
                                                      "retract_position_target": False}}
        for arm in ARM_PARAMS:
            out[f"P89-{arm}-{plant}"] = (flow_on, dict(a_options))
    return out


# ------------------------------------------------------------------ patches
_LOG: dict = {"starts": [], "ends": [], "h3": [], "h1_defer": [], "h1_b3_block": [],
              "h1_land": [], "arm": None, "params": None}


def install_patches(arm: str) -> None:
    """Install the record wrappers (all arms) and the arm's candidate rule in this process."""
    import numpy as np

    from outrigger_sim.control import c2

    if getattr(c2, "_p89_arm", None) is not None:
        if c2._p89_arm != arm:
            raise RuntimeError(f"worker already patched for {c2._p89_arm}, not {arm}")
        return
    c2._p89_arm = arm
    params = ARM_PARAMS[arm]
    _LOG["arm"], _LOG["params"] = arm, {k: list(v) if isinstance(v, tuple) else v
                                        for k, v in params.items()}
    tol = c2.REAPPROACH_WINDOW_TOLERANCE_S
    cls = c2.C2Controller
    leg_names = c2.LEG_ORDER

    orig_begin = cls._begin_reapproach

    def begin(self, leg, reading, settings):
        orig_begin(self, leg, reading, settings)
        run = self._state.active_reapproaches[leg]
        _LOG["starts"].append({"ctrl": id(self), "t": float(reading.t_s), "leg": leg_names[leg],
                               "retrigger": bool(run.is_retrigger)})

    cls._begin_reapproach = begin

    orig_end = cls._end_reapproach

    def end(self, leg, reading, outcome):
        run = self._state.active_reapproaches.get(leg)
        start_s = None if run is None else float(run.start_s)
        seen = None if run is None else int(run.exit_samples_seen)
        orig_end(self, leg, reading, outcome)
        t = float(reading.t_s)
        _LOG["ends"].append({"ctrl": id(self), "t": t, "leg": leg_names[leg], "start_s": start_s,
                             "outcome": str(outcome), "exit_samples_seen": seen,
                             "required": self.__dict__.get("_p89_required", {}).pop(leg, None)})
        # H-1 bookkeeping: the last end (any outcome), as reapproach_last_end_s is
        self.__dict__["_p89_last_end"] = {"leg": leg, "t_end": t,
                                          "contact": outcome == "contact", "landed": False}

    cls._end_reapproach = end

    if "h3" in params:
        t_r, n_s = params["h3"]

        def end_finished(self, reading, loads_N, settings):
            # copy of C2Controller._end_finished_reapproaches (C 8a2a52ce c2.py 6277-6309)
            # with the H-3 required count
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
                if reading.t_s - run.start_s <= t_r + tol:
                    required = n_s
                self.__dict__.setdefault("_p89_required", {})[leg] = required
                if (required > settings.exit_samples
                        and settings.exit_samples <= run.exit_samples_seen < required):
                    _LOG["h3"].append({"ctrl": id(self), "t": float(reading.t_s),
                                       "leg": leg_names[leg], "start_s": float(run.start_s),
                                       "seen": int(run.exit_samples_seen),
                                       "required": int(required)})
                if run.exit_samples_seen >= required:
                    self._end_reapproach(leg, reading, "contact")
                    self._add_event(reading.t_s, f"leg_reapproach_contact:{leg_names[leg]}")
                    if self.config.lock_start_b.is_enabled:
                        self._end_event_order_on_contact(leg, reading.t_s)
                elif travel > settings.max_travel_m or settings.has_run_too_long(
                    reading.t_s, run.start_s
                ):
                    self._end_reapproach(leg, reading, "no_contact")
                    state.is_reapproach_armed[leg] = False
                    self._add_event(
                        reading.t_s,
                        f"WARN_LEG_REAPPROACH_NO_CONTACT:{leg_names[leg]}",
                        is_warning=True,
                    )
            state.is_reapproach_armed |= loads_N >= min_load_N

        cls._end_finished_reapproaches = end_finished

    if "h1" in params:
        w_d = params["h1"]

        def waiting(self, leg, t_s):
            last = self.__dict__.get("_p89_last_end")
            if not last or not last["contact"] or last["landed"]:
                return False
            if leg != DIAGONAL[last["leg"]]:
                return False
            return t_s - last["t_end"] <= w_d + tol

        orig_start = cls._start_reapproaches

        def start(self, reading, loads_N, settings):
            last = self.__dict__.get("_p89_last_end")
            if last and last["contact"] and not last["landed"]:
                d = DIAGONAL[last["leg"]]
                level = settings.load_fraction_of_F_min * self.geometry.F_min_N
                if reading.t_s > last["t_end"] + tol and loads_N[d] >= level:
                    last["landed"] = True
                    _LOG["h1_land"].append({"ctrl": id(self), "t": float(reading.t_s),
                                            "leg": leg_names[d], "t_end": last["t_end"]})
            orig_start(self, reading, loads_N, settings)

        cls._start_reapproaches = start

        orig_defers = cls._defers_reapproach

        def defers(self, leg, t_s, strong_count, settings):
            if orig_defers(self, leg, t_s, strong_count, settings):
                return True
            if waiting(self, leg, t_s):
                _LOG["h1_defer"].append({"ctrl": id(self), "t": float(t_s),
                                         "leg": leg_names[leg]})
                return True
            return False

        cls._defers_reapproach = defers

        orig_name = cls._deferred_event_name

        def name(self, leg, t_s):
            settings = self.config.r8.lifted_reapproach
            state = self._state
            if not self._is_retrigger_waiting(leg, t_s, settings) and waiting(self, leg, t_s):
                leg_sign = float(np.sign(self.geometry.twist_vector[leg]))
                if not settings.needs_strong_confirmation(
                        t_s, state.reapproach_last_end_s, state.reapproach_last_sign, leg_sign):
                    return f"{c2.REAPPROACH_DEFERRED_EVENT}:{leg_names[leg]}:{HANDOVER_REASON}"
            return orig_name(self, leg, t_s)

        cls._deferred_event_name = name

        orig_pre = cls._may_start_pre_twist

        def may_pre(self, leg, reading):
            allowed = orig_pre(self, leg, reading)
            if allowed and waiting(self, leg, reading.t_s):
                _LOG["h1_b3_block"].append({"ctrl": id(self), "t": float(reading.t_s),
                                            "leg": leg_names[leg]})
                return False
            return allowed

        cls._may_start_pre_twist = may_pre


# ------------------------------------------------------------------ worker
def worker(job: dict) -> dict:
    raw = Path(job.pop("_raw"))
    _paths()
    os.chdir(WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(_settings())
    arm = job["setting"].split("-")[1]
    install_patches(arm)
    from outrigger_sim.control import c2

    t0 = time.perf_counter()
    record = run_v5.run_one(job)
    stem = run_v5.t4h_file_name(job)[:-4]
    logs = raw / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{stem}_p89.json").write_text(json.dumps(_LOG, default=str), encoding="utf-8")
    import outrigger_sim

    record["p89"] = {"stem": stem, "arm": arm, "patched_arm": getattr(c2, "_p89_arm", None),
                     "params": _LOG["params"],
                     "end_finished_is_patched": c2.C2Controller._end_finished_reapproaches.__name__,
                     "outrigger_sim_file": str(Path(outrigger_sim.__file__).resolve()),
                     "n_h3": len(_LOG["h3"]), "n_h1_defer": len(_LOG["h1_defer"]),
                     "n_h1_b3_block": len(_LOG["h1_b3_block"]),
                     "worker_wall_s": round(time.perf_counter() - t0, 1)}
    return record


def run_batch(jobs: list[dict], raw: Path, workers: int, mask: int | None,
              limit: int | None = None) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    out = raw / "runs.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add(json.dumps({k: v for k, v in r["job"].items()
                                     if k not in ("mask", "t4h_dir")}, sort_keys=True))
    todo = [dict(job, mask=mask, t4h_dir=None, _raw=str(raw)) for job in jobs
            if json.dumps(job, sort_keys=True) not in done]
    print(f"todo {len(todo)} of {len(jobs)}", flush=True)
    if limit is not None:  # chunked foreground runs (the runner resumes from runs.jsonl)
        todo = todo[:limit]
    if not todo:
        return
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for n, rec in enumerate(pool.imap_unordered(worker, todo), 1):
            rec["job"] = {k: v for k, v in rec["job"].items() if k != "_raw"}
            handle.write(json.dumps(rec, default=str) + "\n")
            handle.flush()
            state = (rec.get("error") or "")[:300] or f"{rec.get('wall_s')} s"
            print(f"{n}/{len(todo)} {rec['job']['setting']} {rec['job']['case']} "
                  f"{rec['job'].get('offset_s')} {rec['job'].get('eps')} "
                  f"{rec['job'].get('twin')}: {state}", flush=True)


# ------------------------------------------------------------------ selftest
def selftest() -> int:
    """Synthetic unit checks of the H-3 copy (report.md 8 tests (2)..(4)) and the H-1 wait."""
    _paths()
    from types import SimpleNamespace

    import numpy as np

    from outrigger_sim.control import c2

    install_patches("H3")
    settings = c2.R8_D1_SETTINGS.lifted_reapproach
    assert settings.exit_samples == 3, settings.exit_samples
    f_min = 9415.0
    exit_level = f_min + settings.exit_margin_N
    results = []

    class Fake:
        _end_finished_reapproaches = c2.C2Controller._end_finished_reapproaches
        _end_reapproach = c2.C2Controller._end_reapproach

        def __init__(self, start_s):
            self.geometry = SimpleNamespace(F_min_N=f_min,
                                            twist_vector=np.array([0.48, -0.48, -0.52, 0.52]))
            self.config = SimpleNamespace(lock_start_b=SimpleNamespace(is_enabled=False))
            self._state = SimpleNamespace(
                active_reapproaches={1: c2._Reapproach(1, start_s, 0.0, settings.mode)},
                is_reapproach_armed=np.zeros(4, bool), reapproach_last_end_s=None,
                reapproach_last_sign=0.0)
            self.events = []

        def _add_event(self, t, name, is_warning=False):
            self.events.append((round(t, 6), name))

    def run_case(name, start_s, highs, t_last, expect_end):
        ctrl = Fake(start_s)
        t = round(start_s + 0.1, 6)
        while t <= t_last + 1e-9 and ctrl._state.active_reapproaches:
            loads = np.full(4, 50e3)
            loads[1] = 50e3 if any(abs(t - h) < 1e-6 for h in highs) else 0.0
            reading = SimpleNamespace(t_s=t, motor_stroke_m=np.zeros(4))
            ctrl._end_finished_reapproaches(reading, loads, settings)
            t = round(t + 0.1, 6)
        ended = [e for e in ctrl.events if e[1].startswith("leg_reapproach_contact")]
        got = ended[0][0] if ended else None
        ok = (got is None and expect_end is None) or (
            got is not None and expect_end is not None and abs(got - expect_end) < 1e-6)
        results.append({"case": name, "end": got, "expect": expect_end, "ok": ok})

    # (2) start 0.1, highs 0.2 0.3 0.4: off ends 0.4; H-3 needs 0.5 too
    run_case("start0.1_high0.2-0.5", 0.1, (0.2, 0.3, 0.4, 0.5), 1.0, 0.5)
    run_case("start0.1_high0.2-0.4_low0.5", 0.1, (0.2, 0.3, 0.4), 0.9, None)
    run_case("start0.1_high0.2-0.4_low0.5_high0.6-0.9", 0.1, (0.2, 0.3, 0.4, 0.6, 0.7, 0.8),
             1.0, 0.8)
    # (3) late run: start 0.075 (as 0.1-grid offset), highs 0.775 .. 0.975 -> same as off
    run_case("start0.075_high0.775-0.975", 0.075, (0.775, 0.875, 0.975), 1.2, 0.975)
    # (4) boundary: start 0.1, highs 0.4 0.5 0.6 (t-start at 0.6 = 0.5 exactly -> needs 4)
    run_case("boundary_start0.1_high0.4-0.6", 0.1, (0.4, 0.5, 0.6), 0.9, None)
    run_case("boundary_start0.1_high0.4-0.7", 0.1, (0.4, 0.5, 0.6, 0.7), 0.9, 0.7)
    # the count rule is taken at the sample that would end the run (t - start 0.6 > T_r: 3)
    run_case("after_Tr_start0.1_high0.5-0.7", 0.1, (0.5, 0.6, 0.7, 0.8), 0.9, 0.7)
    run_case("after_Tr_start0.1_high0.7-0.9", 0.1, (0.7, 0.8, 0.9), 1.0, 0.9)
    print(json.dumps(results, indent=1))
    ok = all(r["ok"] for r in results)
    print("SELFTEST", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    mode = sys.argv[1]
    if mode == "selftest":
        return selftest()
    raw = Path(sys.argv[2]).resolve()
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    mask = int(sys.argv[4], 16) if len(sys.argv) > 4 else None
    limit = int(sys.argv[5]) if len(sys.argv) > 5 else None
    os.environ["NUMBA_CACHE_DIR"] = str(NUMBA_CACHE)
    NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
    jobs = check_jobs() if mode == "check" else main_jobs()
    run_batch(jobs, raw, min(workers, 8), mask, limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
