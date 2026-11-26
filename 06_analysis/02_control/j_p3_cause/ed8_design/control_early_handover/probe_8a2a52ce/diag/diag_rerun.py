"""P8-9 follow-up diagnosis (user decision (가), 2026-11-26): instrumented reruns of the two H-3
condition (3) failures, seen keys only, record-only patches.

Jobs (setting names of ``p89_rerun.py``; the H-3 values are those of P8-9, not changed):
  R12 bottom-FR-Fs4-RE1bF-ready o0.075  x  {P89-A-VBM, P89-H3-VBM, V0}
  R15 o0.05                             x  {P89-A-VBM, P89-H3-VBM, V0}
V0 is the run_v5 ``V0`` setting (the stored-grid / j9_main baseline of both keys).

Records (no command change; ``commands_sha256`` is compared with the p89 main lines):
  * T4h file (run_v5 T4h path; the P89 setting names are added to ``T4H_SETTINGS``);
  * ``d00_instrumented_rerun._install_patches`` (D-1..D-3 way): controller state snapshot every
    period, harness plant snapshot at every 0.1 s (locked, sref, x, f, Fs, line_fill_gate ...);
  * LockStartB: ``apply_floors`` inputs/outputs every period, the A(i)-b trigger predicate parts
    (``_is_blind_trigger``: stretch periods, still, completion open, A(i) floor on, protected),
    shot safety, A(i) / A(i)-b start and end with reason;
  * r67 ``judge_event``: the twist-work dict (``twist``: 0.5 s bins, bundles) and the 1 ms event
    branch rows (t, contact 4, F 4, valve 4, gap 4, att 2) from event - 0.5 s;
  * ``p89_rerun`` record wrappers (re-approach starts / ends, H-3 extensions).

Usage (dynamics-dev activated, PowerShell):
  conda run -n dynamics-dev python -I -B diag_rerun.py <raw_dir> [workers] [mask_hex]
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
ED8 = PROBE.parents[1]
D00 = ED8 / "dynamics_d1_d3" / "d00_instrumented_rerun.py"
NUMBA_CACHE = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba"
                   r"\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\dynamics-p89diag\numba_cache")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


p89 = _load("p89_rerun", PROBE / "p89_rerun.py")

KEY1 = {"case": "R12", "eps": 0.0, "offset_s": 0.075,
        "twin": {"level": "bottom", "leg": "FR", "fs_kN": 4.0, "event": "RE1bF",
                 "timing": "ready"}}
KEY2 = {"case": "R15", "eps": 0.0, "offset_s": 0.05}
JOBS = [{**key, "setting": s} for key in (KEY1, KEY2)
        for s in ("P89-A-VBM", "P89-H3-VBM", "V0")]

_LSB: dict = {"floors": [], "blind_trigger": [], "shot_safe": [], "a1": [], "ib": []}
_JUDGE: dict = {"twist": None, "rows": None, "t_ev": None}


def install_diag() -> None:
    import numpy as np

    import s9_soil_event_screen as study_a
    from outrigger_sim.control import lock_start_b as lsb

    cls = lsb.LockStartB
    if getattr(cls, "_diag_patched", False):
        return
    cls._diag_patched = True

    orig_apply = cls.apply_floors

    def apply_floors(self, inputs):
        out = orig_apply(self, inputs)
        c = inputs.completion
        _LSB["floors"].append({
            "t": float(inputs.t_s), "is_level": bool(inputs.is_level),
            "requested": [float(x) for x in np.asarray(inputs.requested_m_s, float)],
            "acting": [float(x) for x in np.asarray(inputs.acting_m_s, float)],
            "output": [float(x) for x in np.asarray(out, float)],
            "raised": [bool(x) for x in self.last_raised],
            "stroke": [float(x) for x in np.asarray(inputs.stroke_m, float)],
            "protected": [bool(x) for x in np.asarray(inputs.protected)],
            "on_target": None if c is None else bool(c.is_on_target),
            "clearance_done": None if c is None else bool(c.is_clearance_done),
            "complete": None if c is None else bool(c.is_complete),
            "twist_load_N": float(getattr(inputs, "twist_load_N", float("nan"))),
            "twist_limit_N": float(getattr(inputs, "twist_limit_N", float("nan"))),
            "a1_on": [bool(s.is_floor_on) for s in self._deadband],
            "a1_stretch": [int(s.stretch_sign * s.stretch_periods) for s in self._deadband],
            "ib_on": [bool(s.is_floor_on) for s in self._blind],
            "ib_stretch": [int(s.stretch_sign * s.stretch_periods) for s in self._blind],
            "ib_latched": [bool(s.is_latched) for s in self._blind],
            "events": [n for _, n in self.events]})
        return out

    cls.apply_floors = apply_floors

    orig_trig = cls._is_blind_trigger

    def is_trigger(self, state, leg, inputs):
        result = orig_trig(self, state, leg, inputs)
        if state.stretch_sign != 0 and state.stretch_periods >= self.settings.ib_blind_periods:
            try:
                still = float(self._blind_still_m(state))
            except Exception:  # record only
                still = float("nan")
            _LSB["blind_trigger"].append({
                "t": float(inputs.t_s), "leg": leg, "sign": int(state.stretch_sign),
                "periods": int(state.stretch_periods), "still_m": still,
                "still_limit_m": float(self.settings.ib_still_m),
                "completion_open": bool(self._is_completion_open(inputs)),
                "a1_floor_on": bool(self._deadband[leg].is_floor_on),
                "protected": bool(inputs.protected[leg]), "result": bool(result)})
        return result

    cls._is_blind_trigger = is_trigger

    orig_safe = cls._is_shot_safe

    def is_safe(self, leg, sign, inputs):
        result = orig_safe(self, leg, sign, inputs)
        _LSB["shot_safe"].append({"t": float(inputs.t_s), "leg": leg, "sign": int(sign),
                                  "result": bool(result)})
        return result

    cls._is_shot_safe = is_safe

    for name, key, kind in (("_start_deadband", "a1", "start"), ("_end_deadband", "a1", "end"),
                            ("_start_blind", "ib", "start"), ("_end_blind", "ib", "end")):
        orig = getattr(cls, name)

        def wrapped(self, *args, _orig=orig, _key=key, _kind=kind, _name=name):
            info = {"kind": _kind, "fn": _name, "t_last": self._trace_t_s[-1]
                    if self._trace_t_s else None}
            if _name == "_start_deadband":
                state, leg = args[0], args[1]
                info.update(leg=leg, sign=int(state.stretch_sign), requested=float(args[3]),
                            periods=int(state.stretch_periods))
            elif _name == "_start_blind":
                state, leg, inputs = args
                info.update(leg=leg, sign=int(state.stretch_sign), t=float(inputs.t_s),
                            periods=int(state.stretch_periods))
            elif _name == "_end_deadband":
                info.update(leg=args[0], reason=str(args[1]),
                            was_on=bool(self._deadband[args[0]].is_floor_on))
            else:
                info.update(leg=args[0], reason=str(args[1]), t=float(args[2]),
                            was_on=bool(self._blind[args[0]].is_floor_on))
            result = _orig(self, *args)
            if info.get("was_on", True):
                _LSB[_key].append(info)
            return result

        setattr(cls, name, wrapped)

    r67 = study_a._s8_modules()["r67"]
    orig_judge = r67.judge_event

    def judge(rec, phases, events, crawler, t_ev, t_ready_back, ev, leg, ctrl, att0):
        out = orig_judge(rec, phases, events, crawler, t_ev, t_ready_back, ev, leg, ctrl, att0)
        rows = np.asarray(rec)
        w = rows[:, 0] >= t_ev - 0.5
        _JUDGE.update(twist=out.get("twist"), t_ev=float(t_ev), rows=rows[w, :19],
                      phases=[(float(a), str(b)) for a, b in phases])
        return out

    r67.judge_event = judge


def worker(job: dict) -> dict:
    raw = Path(job.pop("_raw"))
    p89._paths()
    os.chdir(p89.WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(p89._settings())
    names = tuple(n for n in p89._settings() if n not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *names)
    import harness_hydraulics  # noqa: F401
    import numpy as np

    d00 = _load("d00_instrumented_rerun", D00)
    d00._install_patches()
    arm = "A" if job["setting"] == "V0" else job["setting"].split("-")[1]
    p89.install_patches(arm)
    install_diag()
    t0 = time.perf_counter()
    record = run_v5.run_one(job)
    stem = run_v5.t4h_file_name(job)[:-4]
    logs = raw / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    d00._dump_series(d00._LOG["plant"], logs / f"{stem}_plant.npz")
    d00._dump_series(d00._LOG["ctrl"], logs / f"{stem}_ctrl.npz")
    (logs / f"{stem}_cue.json").write_text(json.dumps({"cue": d00._LOG["cue"],
                                                       "ratio": d00._LOG["ratio"]}, default=str),
                                           encoding="utf-8")
    (logs / f"{stem}_lsb.json").write_text(json.dumps(_LSB, default=str), encoding="utf-8")
    (logs / f"{stem}_p89.json").write_text(json.dumps(p89._LOG, default=str), encoding="utf-8")
    if _JUDGE["rows"] is not None:
        np.savez_compressed(logs / f"{stem}_rows.npz", rows=_JUDGE["rows"], t_ev=_JUDGE["t_ev"])
        (logs / f"{stem}_judge.json").write_text(
            json.dumps({"twist": _JUDGE["twist"], "t_ev": _JUDGE["t_ev"],
                        "phases": _JUDGE["phases"]}, default=str), encoding="utf-8")
    import outrigger_sim

    record["diag"] = {"stem": stem, "arm": arm, "patched_arm": getattr(
        sys.modules["outrigger_sim.control.c2"], "_p89_arm", None),
        "outrigger_sim_file": str(Path(outrigger_sim.__file__).resolve()),
        "worker_wall_s": round(time.perf_counter() - t0, 1)}
    return record


def main() -> int:
    raw = Path(sys.argv[1]).resolve()
    workers = min(int(sys.argv[2]) if len(sys.argv) > 2 else 6, 8)
    mask = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    os.environ["NUMBA_CACHE_DIR"] = str(NUMBA_CACHE)
    NUMBA_CACHE.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "t4h").mkdir(exist_ok=True)
    out = raw / "runs.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add(json.dumps({k: v for k, v in r["job"].items()
                                     if k not in ("mask", "t4h_dir")}, sort_keys=True))
    todo = [dict(job, mask=mask, t4h_dir=str(raw / "t4h"), _raw=str(raw)) for job in JOBS
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
