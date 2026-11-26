"""D-1..D-3 (edition 8 design input): instrumented reruns of edition 7 harness lines.

Runs ``run_v5.run_one`` of the edition 7 run commit worktree (``.claude/worktrees/ed7-impl``,
C 8a2a52ce, imported read-only, nothing in it is changed) for a few j9main / sensitivity keys,
with record-only patches in each spawned worker:

* ``ground_contact._stiffness_cue``: every probe K1 sample (start / mid / extended force and
  piston (rod) / motor strokes, stiffness, grounded flag) and the result;
* ``C2Controller._update_twist_stiffness_scale``: the per-round per-leg K1 / k_nom ratios;
* the harness plant (``harness_hydraulics.make_hydraulics_plant_class`` subclass): a snapshot of
  every numeric per-leg (4,) array and numeric scalar of the plant (and of its attribute objects,
  one level) at every 0.1 s plant-time boundary;
* ``C2Controller.update``: a snapshot of the numeric controller state after every period.

None of the patches changes a command (``commands_sha256`` of the a2 arm is compared with the
stored j9main / sens line in ``d01``).

Arms (controller, edition 7 tag ``final_C4G2_P3X_LAS_K1_LSB``, components A_i A_ib A_ii B3):
  a2 = edition 7 sealed (D6 witness + (i-b) retract position target)
  A  = direction A of edition 8: witness on (record only), (i-b) off
  c2 = witness and (i-b) off (the probe control arm)
Plants: M (VBM), L (edition 6 VBL plant), Mslow (VBMslow), LSM4 (VBM + LS closure 4),
Mh15 (VBMh15). Two batches (17 + 6 jobs; the runner skips the jobs already in runs.jsonl).

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I -B d00_instrumented_rerun.py <scratch_dir> [workers] [mask]
Output: <scratch_dir>/runs.jsonl (run_one lines + log paths), <scratch_dir>/logs/*.npz|json,
<scratch_dir>/t4h/*.npz. Deterministic harness (no seeded noise in these settings).
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

PLANTS = ("M", "L", "Mslow", "LSM4", "Mh15")
ARMS = ("a2", "A", "c2")

JOBS = [
    # D-1: R12 top-FR-Fs8 o0.0 (first-round probe K1)
    *[{"case": "R12", "eps": 0.0, "offset_s": 0.0,
       "twin": {"level": "top", "leg": "FR", "fs_kN": 8.0}, "setting": f"D8-{p}-{a}"}
      for p in ("M", "L") for a in ("a2", "A")],
    # D-2: S7 phases (VBM long e0.002, short e0.003 / e0.0), VBMslow long e0.0, short e0.002
    *[{"case": "S7", "eps": e, "setting": f"D8-M-{a}"} for e in (0.002, 0.003) for a in ("a2", "A")],
    {"case": "S7", "eps": 0.0, "setting": "D8-M-a2"},
    *[{"case": "S7", "eps": e, "setting": f"D8-Mslow-{a}"} for e in (0.0, 0.002) for a in ("a2", "A")],
    # D-3: F3 tails
    *[{"case": "R12", "eps": 0.0, "offset_s": 0.05,
       "twin": {"level": "top", "leg": "FR", "fs_kN": 0.0}, "setting": f"D8-LSM4-{a}"}
      for a in ("a2", "A")],
    *[{"case": "R12", "eps": 0.0, "offset_s": 0.0,
       "twin": {"level": "top", "leg": "FL", "fs_kN": 0.0}, "setting": f"D8-Mslow-{a}"}
      for a in ("a2", "A")],
    # D-1 follow-up (second batch): F_s 8 keys on the slow / h15 plants and R7
    *[{"case": "R12", "eps": 0.0, "offset_s": 0.0,
       "twin": {"level": "top", "leg": "FR", "fs_kN": 8.0}, "setting": f"D8-{p}-{a}"}
      for p in ("Mslow", "Mh15") for a in ("a2", "A")],
    *[{"case": "R7", "eps": 0.0, "setting": f"D8-M-{a}"} for a in ("a2", "A")],
]


def _paths() -> None:
    for p in (COUPLED, WT / "03_src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _settings() -> dict:
    import run_v5

    settings = {}
    for plant in PLANTS:
        if plant == "M":
            plant_options = run_v5.ed7_plant()
        elif plant == "Mslow":
            plant_options = run_v5.ed7_plant("slow")
        elif plant == "Mh15":
            plant_options = run_v5.ed7_plant("h15")
        elif plant == "L":
            plant_options = run_v5.ed6_plant()
        else:
            plant_options = {**run_v5.ed7_plant(), "lock_closure": run_v5._lc(*run_v5.LS_CLOSURES["4"])}
        for arm in ARMS:
            options = {**plant_options, **run_v5._P3X,
                       "lsb_components": list(run_v5.LSB_COMPONENTS_ED7)}
            if arm == "a2":
                options["probe_d6_settings"] = {"witness": True, "retract_position_target": True}
            elif arm == "A":
                options["probe_d6_settings"] = {"witness": True, "retract_position_target": False}
            settings[f"D8-{plant}-{arm}"] = (True, options)
    return settings


# ------------------------------------------------------------------ record-only patches
_LOG: dict = {"cue": [], "ratio": [], "plant": {}, "ctrl": {}}


def _numeric(obj, prefix: str = "", depth: int = 0) -> dict:
    import numpy as np

    out = {}
    try:
        items = list(vars(obj).items())
    except TypeError:
        try:
            import dataclasses
            items = [(f.name, getattr(obj, f.name)) for f in dataclasses.fields(obj)]
        except Exception:
            return out
    for k, v in items:
        name = prefix + k
        if isinstance(v, bool | np.bool_):
            out[name] = float(v)
        elif isinstance(v, int | float | np.integer | np.floating):
            out[name] = float(v)
        elif isinstance(v, np.ndarray) and v.shape == (4,) and v.dtype.kind in "fiub":
            out[name] = v.astype(float).tolist()
        elif isinstance(v, tuple | list) and len(v) in (2, 4) and all(
                isinstance(x, int | float | np.floating | np.integer) and not isinstance(x, bool)
                for x in v):
            out[name] = [float(x) for x in v]
        elif depth == 0 and hasattr(v, "__dict__") and not isinstance(v, type) \
                and type(v).__module__ not in ("builtins",) and not callable(v):
            out.update(_numeric(v, name + ".", 1))
    return out


def _install_patches() -> None:
    import harness_hydraulics
    from outrigger_sim.control import c2, ground_contact

    if getattr(ground_contact, "_d8_patched", False):
        return
    ground_contact._d8_patched = True
    orig_cue = ground_contact._stiffness_cue

    def cue(sample, load_sensitivity_N_m, settings, correction_sensitivity_N_m=None):
        result = orig_cue(sample, load_sensitivity_N_m, settings, correction_sensitivity_N_m)
        row = {k: (float(v) if isinstance(v, int | float) and not isinstance(v, bool) else v)
               for k, v in vars(sample).items()
               if isinstance(v, int | float | bool) or v is None}
        row.update(stiffness_N_m=float(result.incremental_stiffness_N_m),
                   is_grounded=bool(result.is_grounded), has_moved=bool(result.has_moved),
                   load_estimate_N=float(result.load_estimate_N),
                   seal_friction_estimate_N=float(result.seal_friction_estimate_N),
                   load_sensitivity_N_m=float(load_sensitivity_N_m))
        _LOG["cue"].append(row)
        return result

    ground_contact._stiffness_cue = cue

    orig_scale = c2.C2Controller._update_twist_stiffness_scale

    def scale(self, results, t_s):
        nominal = self.geometry.load_sensitivity_diag_N_m
        rows = [{"leg": int(r.leg_index), "K1_N_m": float(r.incremental_stiffness_N_m),
                 "k_nom_N_m": float(nominal[r.leg_index]),
                 "ratio": float(r.incremental_stiffness_N_m / nominal[r.leg_index]),
                 "grounded": bool(r.is_grounded_by_stiffness), "skipped": bool(r.is_skipped)}
                for r in results]
        orig_scale(self, results, t_s)
        _LOG["ratio"].append({"t_s": float(t_s), "legs": rows,
                              "raw_ratio": self._state.twist_stiffness_raw_ratio,
                              "scale": self._state.twist_stiffness_scale,
                              "k_nom_pad_N_m": float(self.geometry.nominal_pad_stiffness_N_m)})

    c2.C2Controller._update_twist_stiffness_scale = scale

    orig_update = c2.C2Controller.update

    def update(self, measurements):
        command = orig_update(self, measurements)
        snap = _numeric(self._state, "s.")
        snap.update(_numeric(measurements, "m.", 0))
        snap["cmd"] = [float(x) for x in command.leg_speed_m_s]
        snap["phase_name"] = str(getattr(self._state, "phase", ""))
        _LOG["ctrl"].setdefault(id(self), []).append(snap)
        return command

    c2.C2Controller.update = update

    orig_make = harness_hydraulics.make_hydraulics_plant_class

    def make(base, options, damping_N_s_m=None):
        cls = orig_make(base, options, damping_N_s_m)

        class Recorded(cls):
            def step(self, u, nsteps):
                out = super().step(u, nsteps)
                t = float(getattr(self, "t", math.nan))
                if math.isfinite(t):
                    tick = int(math.floor(t / 0.1 + 1e-6))
                    if self.__dict__.get("_d8_tick") != tick:
                        self.__dict__["_d8_tick"] = tick
                        snap = _numeric(self)
                        snap.pop("_d8_tick", None)
                        snap["t"] = t
                        _LOG["plant"].setdefault(id(self), []).append(snap)
                return out

        Recorded.__name__ = cls.__name__
        Recorded.__qualname__ = cls.__qualname__
        return Recorded

    harness_hydraulics.make_hydraulics_plant_class = make


def _dump_series(series_by_id: dict, path: Path) -> list[str]:
    """One npz per object id: key -> (n,) or (n, 4) float arrays (NaN where absent)."""
    import numpy as np

    names = []
    arrays = {}
    for n_obj, (oid, snaps) in enumerate(series_by_id.items()):
        keys = sorted({k for s in snaps for k in s if k != "phase_name"})
        for k in keys:
            width = max((len(s[k]) if isinstance(s.get(k), list) else 1) for s in snaps if k in s)
            arr = np.full((len(snaps), width), np.nan)
            for i, s in enumerate(snaps):
                v = s.get(k)
                if v is None:
                    continue
                try:
                    arr[i, :] = v if isinstance(v, list) else [v]
                except (ValueError, TypeError):
                    pass
            arrays[f"o{n_obj}|{k}"] = arr if width > 1 else arr[:, 0]
        if any("phase_name" in s for s in snaps):
            arrays[f"o{n_obj}|phase_name"] = np.array([s.get("phase_name", "") for s in snaps])
        names.append(f"o{n_obj}")
    np.savez_compressed(path, **arrays)
    return names


def worker(job: dict) -> dict:
    _paths()
    os.chdir(WT)
    import run_v5

    run_v5.ALL_SETTINGS.update(_settings())
    names = tuple(n for n in _settings() if n not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *names)
    import harness_hydraulics  # noqa: F401  (after run_v5: harness folders on sys.path)

    _install_patches()
    t0 = time.perf_counter()
    record = run_v5.run_one(job)
    scratch = Path(job["t4h_dir"]).parent
    stem = run_v5.t4h_file_name(job)[:-4]
    logs = scratch / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{stem}_cue.json").write_text(
        json.dumps({"cue": _LOG["cue"], "ratio": _LOG["ratio"]}, default=str), encoding="utf-8")
    plant_ids = _dump_series(_LOG["plant"], logs / f"{stem}_plant.npz")
    ctrl_ids = _dump_series(_LOG["ctrl"], logs / f"{stem}_ctrl.npz")
    import outrigger_sim
    record["d8"] = {"stem": stem, "plant_objects": plant_ids, "ctrl_objects": ctrl_ids,
                    "outrigger_sim_file": str(Path(outrigger_sim.__file__).resolve()),
                    "worker_wall_s": round(time.perf_counter() - t0, 1)}
    return record


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
    todo = []
    for job in JOBS:
        key = json.dumps(job, sort_keys=True)
        if key in done:
            continue
        todo.append({**job, "mask": mask, "t4h_dir": str(scratch / "t4h")})
    if len(sys.argv) > 4:  # optional limit (smoke run of the first jobs)
        todo = todo[:int(sys.argv[4])]
    print(f"todo {len(todo)} of {len(JOBS)}", flush=True)
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for n, rec in enumerate(pool.imap_unordered(worker, todo), 1):
            handle.write(json.dumps(rec, default=str) + "\n")
            handle.flush()
            state = rec.get("error", "")[:300] or f"{rec.get('wall_s')} s"
            print(f"{n}/{len(todo)} {rec['job']['setting']} {rec['job']['case']} "
                  f"{rec['job'].get('eps')} {rec['job'].get('offset_s')} "
                  f"{rec['job'].get('twin')}: {state}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
