"""L1-R Chrono cases of dynamics_model.md rev. 32 5.14.6-5.14.8 (V7a, V7b, V5 +0.3 mm) and the
redefined V9-2 (5.14.8 last item), L1-R on (rod_side_mechanics one_sided_parallel).

Usage (Chrono-dev, from any folder)::

    python -I -u run_L1R_checks.py run [--jobs 7] [--only CASE ...] [--candidate PATH]
    python -I -u run_L1R_checks.py list | summary | judge

Cases (definitions read from the candidate block ``L1R_rod_side_reference_rev32``, file
``06_analysis/00_dynamics/reference_L1R_candidate.json`` until reference.json carries it):

* ``v7a_<level>_<exc>`` (18): S1 settled snapshot of the level from ``07_results/states_L1R``
  (built with L1-R on; an old snapshot without L1-R keys may be restored with the module default
  - the 5.14.6 exception - and ``l1r_state_defaulted`` is recorded), legs locked (no actuator,
  command 0), YAML dt, predictor on; the rigid initial velocity of the table (absolute values,
  ``V7a_cases/<level>/runs/<exc>``) about the reference point (superstructure + rods CoM at e_op,
  ``modal_reference(refs, level).reference_point_body_m``, ASSUMPTION: the same point), free
  vibration for the table window. Recorded: q (1 ms), module elastic N / state per step (stats:
  max |dN| vs the start, non-LOCK steps, knee crossings), bushing yield steps.
* ``v7b_<exc>_dt<dt>`` (heave / roll / pitch x 2e-4 / 1e-5): top, as V7a with the V7b table;
  per-step module N / state series saved.
* ``v5p3_l1r_dt<dt>`` (2e-4 / 1e-4 / 5e-5 / 1e-5) and ``v5p3_l1r_nopred_dt<dt>`` (2e-4 / 1e-4):
  top S1 snapshot, actuator on: hold 0.5 s, FL +0.5 mm/s with the FL soft end s0 + 0.3 mm
  (braking at the actuator acceleration limit), to 12.0 s; per-step module N / state, s_motor,
  attitude; FL lock time.
* ``v9free_l1r_dt<dt>`` (2e-4 / 1e-4 / 5e-5 / 1e-5): V9-2 redefined = V7a top roll (0.0046 deg),
  6 s; eta_1 (LOCK Phi) amplitude / phase at 5 s is left to the verify step (raw q saved).

Outputs: ``07_results/L1R_checks/batch_<stamp>/<case>/`` (result.json, series.npz),
``07_results/L1R_checks/index.json``; raw summary
``06_analysis/01_chrono/14_S4/verify_L1R_V7_V5_raw.json`` (no judgement) and the judgement
summary ``verify_L1R_V7_V5.json`` next to it (``outrigger_sim.verify.l1r``: V7a gate + LOCK
f / zeta, V7b record judgement, V5 +0.3 mm end values, V9-1 with / without the predictor, V9-2;
5.14.11). ``summary`` writes both; ``judge`` writes only the judgement (the raw file is left as
it is).
Units SI; angles in deg where named ``*_deg``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] if (HERE.parents[1] / "03_src").exists() else Path(r"C:\workspace\outrigger_control")
"""Project root (also when the file is run from its staging copy)."""
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

RESULTS = ROOT / "07_results" / "L1R_checks"
INDEX = RESULTS / "index.json"
STATES = ROOT / "07_results" / "states_L1R"
OLD_STATES = ROOT / "07_results" / "states"
OUT = ROOT / "06_analysis" / "01_chrono" / "14_S4" / "verify_L1R_V7_V5_raw.json"
JUDGED = OUT.with_name("verify_L1R_V7_V5.json")
"""Judgement summary (verify.l1r checks); the raw summary :data:`OUT` stays as it is."""
CANDIDATE = ROOT / "06_analysis" / "00_dynamics" / "reference_L1R_candidate.json"
REF_KEY = "L1R_rod_side_reference_rev32"
MECHANICS = "one_sided_parallel"
LEVELS = ("top", "middle", "bottom")
EXCS = ("roll", "pitch", "yaw", "surge", "heave", "sway")
V7B = ("heave", "roll", "pitch")
V7B_DTS = (2.0e-4, 1.0e-5)
V5_DTS = (2.0e-4, 1.0e-4, 5.0e-5, 1.0e-5)
V5_NOPRED_DTS = (2.0e-4, 1.0e-4)
V5_HOLD_S, V5_SPEED_M_S, V5_TRAVEL_M, V5_END_S = 0.5, 0.5e-3, 0.3e-3, 12.0
V9_DTS = (2.0e-4, 1.0e-4, 5.0e-5, 1.0e-5)
V9_FREE_S = 6.0
SAMPLE_S = 1.0e-3
CASE_TIMEOUT_S = 3600.0
MAX_WORKERS = 7


def _plain(v):
    import numpy as np

    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_plain(x) for x in v]
    if isinstance(v, np.ndarray):
        return _plain(v.tolist())
    if isinstance(v, np.generic):
        return _plain(v.item())
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _dt_tag(dt: float) -> str:
    return f"{dt:.0e}"


def case_ids() -> list[str]:
    ids = [f"v7a_{lv}_{e}" for lv in LEVELS for e in EXCS]
    ids += [f"v7b_{e}_dt{_dt_tag(dt)}" for e in V7B for dt in V7B_DTS]
    ids += [f"v5p3_l1r_dt{_dt_tag(dt)}" for dt in V5_DTS]
    ids += [f"v5p3_l1r_nopred_dt{_dt_tag(dt)}" for dt in V5_NOPRED_DTS]
    ids += [f"v9free_l1r_dt{_dt_tag(dt)}" for dt in V9_DTS]
    return ids


def _candidate(path: Path | None = None) -> dict:
    """The L1-R block: reference.json when it carries the key, else the candidate file."""
    ref_path = ROOT / "06_analysis" / "00_dynamics" / "reference.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    if path is None and REF_KEY in ref:
        return {"source": _rel(ref_path), "block": ref[REF_KEY]}
    p = path or CANDIDATE
    return {"source": _rel(p), "block": json.loads(p.read_text(encoding="utf-8"))[REF_KEY]}


def case_settings(case_id: str, cand: dict) -> dict:
    b = cand["block"]
    yaml_dt = None
    if case_id.startswith("v7a_"):
        _, lv, exc = case_id.split("_")
        run = b["V7a_cases"][lv]["runs"][exc]
        return {"kind": "free", "group": "V7a", "level": lv, "exc": exc, "dt": yaml_dt,
                "v": run["initial_velocity_point_m_s (of the reference point)"],
                "w": run["initial_angular_velocity_rad_s"], "window_s": run["window_s"],
                "amplitude": run["amplitude (deg rotation | m translation)"],
                "series": False, "source": cand["source"]}
    if case_id.startswith("v7b_"):
        _, exc, dtt = case_id.split("_")
        run = b["V7b_cases"][exc]
        return {"kind": "free", "group": "V7b", "level": run.get("level", "top"), "exc": exc,
                "dt": float(dtt.removeprefix("dt")), "v": run["initial_velocity_point_m_s"],
                "w": run["initial_angular_velocity_rad_s"], "window_s": run["window_s"],
                "amplitude": run["amplitude (deg rotation | m translation)"], "series": True,
                "source": cand["source"]}
    if case_id.startswith("v9free_l1r_"):
        run = b["V7a_cases"]["top"]["runs"]["roll"]
        return {"kind": "free", "group": "V9-2 (L1-R)", "level": "top", "exc": "roll",
                "dt": float(case_id.removeprefix("v9free_l1r_dt")),
                "v": run["initial_velocity_point_m_s (of the reference point)"],
                "w": run["initial_angular_velocity_rad_s"], "window_s": V9_FREE_S,
                "amplitude": run["amplitude (deg rotation | m translation)"], "series": True,
                "source": cand["source"]}
    if case_id.startswith("v5p3_l1r_"):
        nopred = "_nopred_" in case_id
        return {"kind": "v5p3", "group": "V5 +0.3 mm / V9-1 (L1-R)", "level": "top",
                "dt": float(case_id.split("_dt")[-1]), "predictor": not nopred,
                "hold_s": V5_HOLD_S, "speed_m_s": V5_SPEED_M_S, "travel_m": V5_TRAVEL_M,
                "end_s": V5_END_S, "series": True, "source": cand["source"]}
    raise SystemExit(f"unknown case {case_id!r}")


# --- model ------------------------------------------------------------------------------------


def _model(params, refs, level: str, dt: float | None, *, actuator: bool):
    """L1-R model restored from the level's S1 settled snapshot (states_L1R; old states with the
    module default as the 5.14.6 exception)."""
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.chrono.model import L1Model, operating_extensions_m
    from outrigger_sim.record import load_snapshot
    from outrigger_sim.scenarios.settle import analytic_static_pose

    sp = analytic_static_pose(params, refs, operating_extensions_m(params))
    kw = {} if dt is None else {"dt_s": dt}
    model = L1Model(params, pose=BodyPose(sp.origin_m, sp.quat_wxyz), actuator=actuator,
                    rod_side_mechanics=MECHANICS, **kw)
    name = f"S1_L1_{level}"
    src = STATES if (STATES / f"{name}.npz").exists() else OLD_STATES
    t0 = model.restore(load_snapshot(name, params_sha256=params.sha256, directory=src))
    link = model.rod_chamber
    return model, t0, {"snapshot": f"{_rel(src)}/{name}", "l1r_state_defaulted":
                       bool(getattr(link, "state_defaulted", False))}


def _set_predictor(model, on: bool) -> None:
    from dataclasses import replace

    link = model.rod_chamber
    machine = link.machine
    opts = replace(machine.options, predictor=on)
    machine.options = opts
    for leg in machine.legs:
        leg.options = opts
    if hasattr(link, "options"):
        link.options = replace(link.options, predictor=on)


class _ModuleLog:
    """Step observer of the L1-R link: module elastic N and state of every step."""

    def __init__(self, model, keep_series: bool) -> None:
        import numpy as np

        from outrigger_sim.hydraulics.rod_chamber import RodChamberMode

        self.np = np
        self.lock = int(RodChamberMode.LOCK)
        self.floor = int(RodChamberMode.FLOOR)
        self.lift = int(RodChamberMode.LIFT)
        self.floor_lift = np.zeros(4, dtype=int)
        self.keep = keep_series
        self.model = model
        self.t, self.n, self.mode = [], [], []
        self.n0 = None
        self.n_min = self.n_max = None
        self.non_lock = np.zeros(4, dtype=int)
        self.floor_steps = np.zeros(4, dtype=int)
        self.prev = None
        self.crossings: list[tuple[float, int, str]] = []
        model.rod_chamber.step_observers.append(self)

    def __call__(self, step) -> None:
        np = self.np
        n = np.asarray(step.normal_force_N, dtype=float)
        m = np.asarray(step.mode, dtype=int)
        t = float(self.model.system.GetChTime())
        if self.n0 is None:
            self.n0 = n.copy()
            self.n_min = n.copy()
            self.n_max = n.copy()
        self.n_min = np.minimum(self.n_min, n)
        self.n_max = np.maximum(self.n_max, n)
        self.non_lock += m != self.lock
        self.floor_steps += m == self.floor
        self.floor_lift += (m == self.floor) | (m == self.lift)
        if self.prev is not None:
            for i in np.flatnonzero(m != self.prev):
                self.crossings.append((t, int(i), f"{int(self.prev[i])}->{int(m[i])}"))
        self.prev = m.copy()
        if self.keep:
            self.t.append(t)
            self.n.append(n.copy())
            self.mode.append(m.astype(np.int8))

    def stats(self, t0: float, dt: float, params) -> dict:
        np = self.np
        knee = _knee_N(params)
        dn = np.maximum(self.n_max - self.n0, self.n0 - self.n_min)
        first = {}
        for t, i, tr in self.crossings:
            first.setdefault(i, (t - t0, tr))
        return {"N_start_N": self.n0, "dN_max_N": self.n_max - self.n0, "dN_min_N": self.n_min - self.n0,
                "abs_dN_max_over_knee": dn / knee, "knee_after_extend_N": knee,
                "non_LOCK_steps": self.non_lock, "FLOOR_steps": self.floor_steps,
                "FLOOR_or_LIFT_steps": self.floor_lift,
                "FLOOR_time_s": self.floor_steps * dt, "n_state_changes": len(self.crossings),
                "first_state_change_per_leg": {str(k): v for k, v in first.items()},
                "last_state_change_s": None if not self.crossings else self.crossings[-1][0] - t0,
                "lock_mode_value": self.lock, "floor_mode_value": self.floor}

    def series(self, t0: float) -> dict:
        np = self.np
        return {"t_step": np.asarray(self.t) - t0, "N_step": np.asarray(self.n, dtype=np.float32),
                "mode_step": np.asarray(self.mode, dtype=np.int8)}


def _knee_N(params):
    """Knee after an extension per leg (module params, the 5.14.3 values)."""
    import numpy as np

    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    p_r0 = [float(params.get(f"actuator.rod_side.p_r0_after_extend_Pa.{leg}"))
            for leg in ("FL", "FR", "RL", "RR")]
    legs, _ = leg_params_from_params(params)
    return np.array([lp.knee_force_increment_N(p) for lp, p in zip(legs, p_r0, strict=True)])


# --- jobs -------------------------------------------------------------------------------------


def job_free(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_free_vibration, set_rigid_velocity
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.params import load_params
    from outrigger_sim.scenarios.impulse import modal_reference
    from outrigger_sim.verify.metrics import rigid_displacement
    from outrigger_sim.verify.reference import load_references

    s = dict(case.settings)
    params = load_params(level=s["level"])
    refs = load_references()
    modal = modal_reference(refs, s["level"])
    model, t0, start = _model(params, refs, s["level"], s["dt"], actuator=False)
    log = _ModuleLog(model, keep_series=bool(s["series"]))
    p0 = model.probe()
    point = p0.body_pos_m + quat_to_matrix(p0.body_quat_wxyz) @ modal.reference_point_body_m
    set_rigid_velocity(model, s["v"], s["w"], point)
    tr = {"t": [], "o": [], "q": []}

    def on_sample(p):
        tr["t"].append(p.t_s)
        tr["o"].append(p.body_pos_m)
        tr["q"].append(p.body_quat_wxyz)

    wall0 = time.perf_counter()
    run = run_free_vibration(model, float(s["window_s"]), sample_s=SAMPLE_S, on_sample=on_sample)
    wall = time.perf_counter() - wall0
    t = np.asarray(tr["t"]) - t0
    q = rigid_displacement(np.asarray(tr["o"]), np.asarray(tr["q"]), p0.body_pos_m,
                           p0.body_quat_wxyz, modal.reference_point_body_m)
    st = log.stats(t0, model.dt_s, params)
    arrays = {"t": t, "q": q, "reference_point_world_m": point}
    if s["series"]:
        arrays.update(log.series(t0))
    np.savez_compressed(case_dir / "series.npz", **arrays)
    summary = {"case": case.case_id, "settings": s, "dt_s": model.dt_s, "params_sha256": params.sha256,
               "start": start, "reference_point_world_m": point,
               "reference_point_note": "modal_reference(refs, level).reference_point_body_m (rev. 13); "
                                       "5.14.6 point = CoM of superstructure + rods at e_op (ASSUMPTION same)",
               "module": st, "validity_inputs": {
                   "FLOOR_or_LIFT_steps_total": int(st["FLOOR_or_LIFT_steps"].sum()),
                   "non_LOCK_steps_total": int(st["non_LOCK_steps"].sum()),
                   "abs_dN_max_over_knee_max": float(np.max(st["abs_dN_max_over_knee"])),
                   "yield_steps": model.bushing.yield_steps.tolist()},
               "rod_chamber_meta": model.rod_chamber.meta() if hasattr(model.rod_chamber, "meta") else None,
               "events": [[e.t_s - t0, e.leg, e.kind] for e in run.events],
               "timing": {"wall_s": wall, "steps": run.steps, "us_per_step": wall / max(run.steps, 1) * 1e6}}
    return CaseResult(summary=_plain(summary), run_meta=None)


def job_v5p3(case, case_dir):
    import numpy as np

    from outrigger_sim.batch import CaseResult
    from outrigger_sim.chrono.runs import run_commanded
    from outrigger_sim.frames import roll_pitch_from_quat
    from outrigger_sim.params import load_params
    from outrigger_sim.verify.reference import load_references

    s = dict(case.settings)
    params = load_params(level="top")
    refs = load_references()
    model, t0, start = _model(params, refs, "top", s["dt"], actuator=True)
    _set_predictor(model, bool(s["predictor"]))
    log = _ModuleLog(model, keep_series=True)
    s0 = model.actuator.s_ref_m.copy()
    hi = model.actuator.stroke_range_m[:, 1].copy()
    hi[0] = s0[0] + float(s["travel_m"])
    model.actuator.set_soft_limits(hi_m=hi)
    rows = {"t": [], "s": [], "quat": []}

    def on_sample(p):
        rows["t"].append(p.t_s)
        rows["s"].append(np.asarray(p.motor_pos_m, float).copy())
        rows["quat"].append(np.asarray(p.body_quat_wxyz, float).copy())

    wall0 = time.perf_counter()
    run_commanded(model, float(s["hold_s"]), lambda _t: None, sample_s=SAMPLE_S, on_sample=on_sample)
    model.set_command([float(s["speed_m_s"]), 0.0, 0.0, 0.0])
    run = run_commanded(model, float(s["end_s"]) - float(s["hold_s"]), lambda _t: None,
                        sample_s=SAMPLE_S, on_sample=on_sample)
    wall = time.perf_counter() - wall0
    t = np.asarray(rows["t"]) - t0
    sm = np.asarray(rows["s"])
    att = np.degrees(np.array([roll_pitch_from_quat(q) for q in rows["quat"]]))
    ser = log.series(t0)
    lock_t = None
    fl_mode = ser["mode_step"][:, 0]
    moving = np.flatnonzero(fl_mode != log.lock)
    if moving.size:
        after = np.flatnonzero((np.arange(len(fl_mode)) > moving[0]) & (fl_mode == log.lock))
        lock_t = float(ser["t_step"][after[0]]) if after.size else None
    np.savez_compressed(case_dir / "series.npz", t=t, s_motor=sm, att_deg=att, **ser)
    summary = {"case": case.case_id, "settings": s, "dt_s": model.dt_s, "params_sha256": params.sha256,
               "start": start, "predictor": bool(s["predictor"]), "module": log.stats(t0, model.dt_s, params),
               "FL_travel_mm": float(sm[-1, 0] - s0[0]) * 1e3, "FL_lock_t_s": lock_t,
               "final_attitude_deg": att[-1], "events": len(run.events),
               "yield_steps": model.bushing.yield_steps.tolist(),
               "timing": {"wall_s": wall}}
    return CaseResult(summary=_plain(summary), run_meta=None)


def m1_status() -> str:
    """``after_M1`` when the L1-R link applies the one-sided extra force (rod_side_pressure.md
    17.1 M1), else ``before_M1`` (coordinator 2026-10-22: mark the B / B2 results)."""
    import outrigger_sim.chrono.rod_chamber_link as rcl

    return "after_M1" if "one_sided_extra_force_N" in vars(rcl) else "before_M1"


def job(case, case_dir):
    fn = {"free": job_free, "v5p3": job_v5p3}[case.settings["kind"]]
    out = fn(case, Path(case_dir))
    out.summary["m1"] = m1_status()
    (Path(case_dir) / "result.json").write_text(json.dumps(_plain(dict(out.summary)), indent=1),
                                                encoding="utf-8")
    return out


# --- batch / summary ---------------------------------------------------------------------------


def run_batch(ids, jobs, cand):
    from outrigger_sim.batch import Case, run_cases

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = RESULTS / f"batch_{stamp}"
    cases = [Case(c, case_settings(c, cand)) for c in ids]
    report = run_cases(cases, job, batch_dir, max_workers=jobs, placement="pcore",
                       timeout_s=CASE_TIMEOUT_S)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    for o in report.outcomes:
        print(f"{o.case_id}: {o.status} {o.wall_s:.1f}s", flush=True)
        if o.status == "ok":
            index[o.case_id] = _rel(batch_dir / o.case_id)
    RESULTS.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1), encoding="utf-8")
    return batch_dir


def summarize(cand):
    import hashlib

    idx = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    res = {}
    for cid, rel in idx.items():
        p = ROOT / rel / "result.json"
        if p.exists():
            r = json.loads(p.read_text(encoding="utf-8"))
            res[cid] = {k: r.get(k) for k in ("settings", "dt_s", "start", "module",
                                              "validity_inputs", "FL_travel_mm", "FL_lock_t_s",
                                              "final_attitude_deg", "yield_steps", "events", "timing",
                                              "m1")}
            res[cid]["dir"] = rel
    yaml = ROOT / "02_params" / "rexome33.yaml"
    doc = {"meta": {"generated": _dt.datetime.now().isoformat(timespec="seconds"),
                    "script": "04_scripts/02_chrono/run_L1R_checks.py",
                    "definition": "dynamics_model.md rev. 32 5.14.6-5.14.8 (+ V9-2 redefinition)",
                    "reference_source": cand["source"],
                    "yaml_sha256": hashlib.sha256(yaml.read_bytes()).hexdigest(),
                    "judgement": "none here (raw records); dynamics-expert / verify L1-R functions",
                    "m1": m1_status()},
           "cases": res}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(_plain(doc), indent=1), encoding="utf-8")
    print(f"summary -> {_rel(OUT)} ({len(res)} cases)")


# --- judgement (verify.l1r) --------------------------------------------------------------------


V9_REF_DT = 1.0e-5
"""Reference time step of V9-1 / V9-2 (5.14.8)."""
JUDGEMENT_DECISIONS = (
    "V7a gate (2) uses the per-leg maximum module elastic N increase (the side that approaches "
    "the knee); |dN| (both signs) is recorded in the case record",
    "V7a modes: identification of run_S4.identify (projection fit + ERA, judged value of "
    "verify.s4.judged_value) on the LOCK Phi of the level; judged run per mode = the block "
    "judged_run_per_mode; zeta_num = LOCK r omega dt / 2 at the run dt",
    "V7b first knee crossing = end time of the first module step with a LOCK <-> FLOOR change",
    "V5 / V9-1: start value = module N of the first step and attitude of the first sample; end "
    "window = last 3 LOCK first-mode periods (12 s - 3 / f1); transient window [0.5, 3.6] s",
    "V9-1 order: successive differences of the three coarse dt (verify.s3.order_ratio, as S3); "
    "the ratio of the errors against 1e-5 s is recorded; the judged value is read from the "
    "float32 series N_step (quantum 2**-7 N), the float64 whole-run minimum of result.json is "
    "recorded next to it",
    "V9-1 order rule of 5.14.12 (rev. 32 suppl. 5): when the 2e-4 s transient error against "
    "1e-5 s is <= 0.1 x 1 %, the successive ratio is recorded and the predictor-off two-dt "
    "ratio (e(2e-4) / e(1e-4) against the predictor-on 1e-5 s run, 2 +- 20 %) is judged with "
    "the V9-2 ratio confirming the order; the predictor-off ratio is judged whenever both "
    "predictor-off runs exist",
    "V9-2: mode-1 amplitude error ratio judged (2 +- 20 %, as S3 V9-2); amplitude difference "
    "to 1e-5 s (1 % flag) and phase recorded",
)


def _plain_keys(value):
    """``_plain`` with float dict keys written as ``%g`` text (dt keys)."""
    if isinstance(value, dict):
        return {(f"{k:g}" if isinstance(k, float) else str(k)): _plain_keys(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_keys(v) for v in value]
    return _plain(value)


def _references(cand):
    from outrigger_sim.verify.reference import ReferenceFile, load_references

    return load_references({ReferenceFile.REFERENCE: ROOT / cand["source"]})


def _load_case(index: dict, case_id: str):
    """``(result.json, series arrays)`` of an indexed case, or ``(None, None)``."""
    import numpy as np

    rel = index.get(case_id)
    if rel is None or not (ROOT / rel / "result.json").exists():
        return None, None
    result = json.loads((ROOT / rel / "result.json").read_text(encoding="utf-8"))
    with np.load(ROOT / rel / "series.npz", allow_pickle=False) as z:
        series = {k: z[k] for k in z.files}
    return result, series


def _module_record(result, series):
    from outrigger_sim.verify.l1r import ModuleRecord

    return ModuleRecord.from_arrays(series["t_step"], series["N_step"], series["mode_step"],
                                    result["dt_s"])


def _zeta_num_lock(refs, level: str, dt_s: float):
    from outrigger_sim.verify.reference import L1R_LOCK_ZETA_NUM_R_OMEGA_DT_HALF

    by_dt = refs.get(L1R_LOCK_ZETA_NUM_R_OMEGA_DT_HALF, level=level)
    key = next((k for k in by_dt if f"{float(k):g}" == f"{dt_s:g}"), None)
    if key is None:
        raise SystemExit(f"no LOCK zeta_num for dt {dt_s:g} s (have {list(by_dt)})")
    return list(by_dt[key])


def _lock_modal(refs, level: str):
    from types import SimpleNamespace

    import numpy as np

    from outrigger_sim.verify.reference import L1R_LOCK_MODE_MASS_MATRIX, L1R_LOCK_MODE_PHI

    return SimpleNamespace(phi=np.asarray(refs.get(L1R_LOCK_MODE_PHI, level=level), dtype=float),
                           mass_matrix=np.asarray(refs.get(L1R_LOCK_MODE_MASS_MATRIX,
                                                           level=level), dtype=float))


def _mode_row(row, run, assignment, zeta_ref):
    from outrigger_sim.verify.s4 import CLOSE_RUNNER_UP_RATIO, ModeRow

    era = row.get("era") or {}
    close = (assignment.get("runner_up_ratio") or 0.0) >= CLOSE_RUNNER_UP_RATIO
    return ModeRow(mode=row["mode"], run=run, f_proj_Hz=row.get("f_proj_Hz"),
                   zeta_proj=row.get("zeta_proj"),
                   fit_residual_rms_rel=row.get("fit_residual_rms_rel"),
                   f_era_Hz=era.get("f_Hz"), zeta_era=era.get("zeta"), leakage=era.get("leakage"),
                   zeta_num=row["zeta_num"], f_ref_Hz=row["f_ref_Hz"], zeta_ref=float(zeta_ref),
                   runner_up=assignment.get("runner_up") if close else None,
                   runner_up_amplitude_ratio=assignment.get("runner_up_ratio") if close else None)


def _judge_v7a_level(refs, index, level):
    """Gate checks per run and the six LOCK mode checks of one level."""
    import numpy as np
    from run_S4 import identify

    from outrigger_sim.verify.l1r import floor_distance_record, v7a_gate_checks, v7a_mode_checks
    from outrigger_sim.verify.reference import (
        L1R_FLOOR_F_DAMPED_HZ,
        L1R_KNEE_DF_AFTER_EXTEND_N,
        L1R_LOCK_F_DAMPED_HZ,
        L1R_LOCK_ZETA,
        L1R_V7A_JUDGED_RUN_PER_MODE,
        L1R_V7A_RUNS,
    )
    from outrigger_sim.verify.s4 import judged_value, mode_info_checks

    knee = list(refs.get(L1R_KNEE_DF_AFTER_EXTEND_N))
    f_lock = list(refs.get(L1R_LOCK_F_DAMPED_HZ, level=level))
    zeta_lock = list(refs.get(L1R_LOCK_ZETA, level=level))
    runs = refs.get(L1R_V7A_RUNS, level=level)
    modal = _lock_modal(refs, level)
    tagged, info, rows_by_run, cases = [], [], {}, {}
    for exc in EXCS:
        cid = f"v7a_{level}_{exc}"
        result, series = _load_case(index, cid)
        if result is None:
            continue
        module = result["module"]
        gate = v7a_gate_checks(cid, non_lock_steps=module["non_LOCK_steps"],
                               dN_max_N=module["dN_max_N"], knee_N=knee,
                               yield_steps=result["validity_inputs"]["yield_steps"],
                               predicted_peak_N=runs[exc]["predicted_peak_elastic_dN_N (k1 ddelta, "
                                                          "max over t)"])
        tagged += [(cid, c) for c in gate]
        rows, _, _ = identify(series["t"], series["q"], modal=modal, f_ref=np.asarray(f_lock),
                              zeta_num=np.asarray(_zeta_num_lock(refs, level, result["dt_s"])),
                              window_s=float(result["settings"]["window_s"]), phi_valid=True)
        rows_by_run[exc] = rows
        cases[cid] = {"gate_passed": all(c.passed for c in gate),
                      "abs_dN_max_over_knee": module["abs_dN_max_over_knee"],
                      "dN_max_N": module["dN_max_N"], "dN_min_N": module["dN_min_N"],
                      "l1r_state_defaulted": result["start"]["l1r_state_defaulted"]}
    assignment = refs.get(L1R_V7A_JUDGED_RUN_PER_MODE, level=level)
    mode_rows, owners = [], []
    for i in range(6):
        a = assignment[f"mode {i + 1}"]
        if a["run"] in rows_by_run:
            mode_rows.append(_mode_row(rows_by_run[a["run"]][i], a["run"], a, zeta_lock[i]))
            owners.append(f"v7a_{level}_{a['run']}")
    checks = v7a_mode_checks(mode_rows, level=level,
                             ref_key_f=L1R_LOCK_F_DAMPED_HZ.resolve(level=level).notation(),
                             ref_key_zeta=L1R_LOCK_ZETA.resolve(level=level).notation())
    for owner, pair in zip(owners, zip(checks[::2], checks[1::2], strict=True), strict=True):
        tagged += [(owner, c) for c in pair]
    info += mode_info_checks(mode_rows, f"V7a {level}")
    judged = [judged_value(r) for r in mode_rows]
    record = {
        "cases": cases,
        "judged_modes": [{"mode": r.mode, "run": r.run, "f_Hz": j.f_Hz, "zeta": j.zeta,
                          "source": j.source, "reason": j.reason, "f_ref_Hz": r.f_ref_Hz,
                          "zeta_ref": r.zeta_ref, "zeta_num": r.zeta_num,
                          "runner_up": r.runner_up,
                          "runner_up_amplitude_ratio": r.runner_up_amplitude_ratio}
                         for r, j in zip(mode_rows, judged, strict=True)],
        "floor_distance_rel (record)": floor_distance_record(
            [j.f_Hz for j in judged],
            [refs.get(L1R_FLOOR_F_DAMPED_HZ, level=level)[r.mode - 1] for r in mode_rows]),
    }
    return tagged, info, record


def _judge_v7b(refs, index):
    from outrigger_sim.verify.l1r import V7B_REPLICA_BY_DT, knee_record, modal_record, v7b_checks
    from outrigger_sim.verify.metrics import modal_coordinates
    from outrigger_sim.verify.reference import L1R_V7B_CASES

    modal = _lock_modal(refs, "top")
    cases_ref = refs.get(L1R_V7B_CASES)
    tagged, record = [], {}
    for exc in V7B:
        for dt in V7B_DTS:
            cid = f"v7b_{exc}_dt{_dt_tag(dt)}"
            result, series = _load_case(index, cid)
            if result is None:
                continue
            variant = V7B_REPLICA_BY_DT[dt]
            replica = cases_ref[exc]["replica"][variant]
            dominant = int(replica["dominant_LOCK_mode (1-based)"]) - 1
            eta = modal_coordinates(series["q"], modal.phi, modal.mass_matrix)[:, dominant]
            knee = knee_record(_module_record(result, series))
            modal_rec = modal_record(series["t"], eta)
            key = f"{L1R_V7B_CASES.notation()} / {exc} / replica / {variant}"
            checks = v7b_checks(cid, knee=knee, modal=modal_rec, replica=replica,
                                yield_steps=result["validity_inputs"]["yield_steps"], ref_key=key)
            tagged += [(cid, c) for c in checks]
            record[cid] = {"replica_variant": variant, "knee": knee.__dict__,
                           "modal": modal_rec.__dict__}
    return tagged, record


def _smooth_records(refs, index, prefix, dts):
    from outrigger_sim.verify.l1r import V5P3_END_PERIODS, smooth_step_record
    from outrigger_sim.verify.reference import L1R_LOCK_F_DAMPED_HZ

    period_s = 1.0 / float(refs.get(L1R_LOCK_F_DAMPED_HZ, level="top")[0])
    window = (V5_END_S - V5P3_END_PERIODS * period_s, V5_END_S)
    out, results = {}, {}
    for dt in dts:
        result, series = _load_case(index, f"{prefix}{_dt_tag(dt)}")
        if result is None:
            continue
        out[dt] = smooth_step_record(_module_record(result, series), t_s=series["t"],
                                     attitude_deg=series["att_deg"], end_window_s=window)
        results[dt] = result
    return out, results


def _float64_order(records, results):
    """Error ratio of the RL minimum from the float64 run statistics (result.json
    ``module.dN_min_N``, whole run) - the series ``N_step`` is float32 (quantum 2**-7 N near
    72 kN), which limits the judged series value; information only. ``same_extreme`` tells
    whether the whole-run minimum is the transient one (within two float32 quanta)."""
    import numpy as np

    from outrigger_sim.verify.l1r import RL
    from outrigger_sim.verify.s3 import order_ratio

    whole = {dt: float(results[dt]["module"]["dN_min_N"][RL]) for dt in records}
    quantum = {dt: float(np.spacing(np.float32(results[dt]["module"]["N_start_N"][RL])))
               for dt in records}
    coarse = {dt: v for dt, v in whole.items() if dt != V9_REF_DT}
    return {"dN_min_RL_N": whole, "order": order_ratio(coarse),
            "same_extreme": {dt: abs(whole[dt] - records[dt].transient_min_dN_RL_N)
                             <= 2.0 * quantum[dt] for dt in records},
            "float32_quantum_N": quantum}


def _judge_v5(refs, index):
    """V5 +0.3 mm validity, V9-1 (predictor on), V5 end values and the predictor-off record."""
    from outrigger_sim.verify.l1r import (
        predictor_off_record,
        smooth_validity_checks,
        transient_match_record,
        v5_smooth_checks,
        v9_smooth_checks,
    )
    from outrigger_sim.verify.reference import (
        L1R_KNEE_DF_AFTER_EXTEND_N,
        L1R_V5_SMOOTH_FINAL,
        L1R_V5_SMOOTH_TRANSIENT,
        TOTAL_WEIGHT_INCL_RODS_N,
    )

    knee = list(refs.get(L1R_KNEE_DF_AFTER_EXTEND_N))
    on, on_results = _smooth_records(refs, index, "v5p3_l1r_dt", V5_DTS)
    off, off_results = _smooth_records(refs, index, "v5p3_l1r_nopred_dt", V5_NOPRED_DTS)
    tagged = []
    for prefix, records in (("v5p3_l1r_dt", on), ("v5p3_l1r_nopred_dt", off)):
        for dt, rec in records.items():
            cid = f"{prefix}{_dt_tag(dt)}"
            tagged += [(cid, c) for c in smooth_validity_checks(cid, rec, knee)]
    record = {"cases": {}}
    for label, records, results in (("on", on, on_results), ("off", off, off_results)):
        for dt, rec in records.items():
            record["cases"][f"predictor {label}, dt {dt:g} s"] = {
                **{k: v for k, v in rec.__dict__.items() if k != "knee"}, "knee": rec.knee.__dict__,
                "FL_lock_t_s": results[dt].get("FL_lock_t_s"),
                "FL_travel_mm": results[dt].get("FL_travel_mm"),
                "yield_steps": results[dt].get("yield_steps"),
                "transient_match (record)": transient_match_record(
                    rec, refs.get(L1R_V5_SMOOTH_TRANSIENT))}
    if len(on) == len(V5_DTS):
        checks, v9_record = v9_smooth_checks(
            "V9-1 L1-R FL +0.3 mm at 0.5 mm/s (predictor on)", on, ref_dt_s=V9_REF_DT,
            total_weight_N=float(refs.get(TOTAL_WEIGHT_INCL_RODS_N)),
            predictor_off_by_dt=off if len(off) == len(V5_NOPRED_DTS) else None)
        tagged += [("v5p3_l1r (V9-1)", c) for c in checks]
        record["V9-1"] = v9_record
        record["V9-1"]["order_float64_whole_run_min (information)"] = _float64_order(on, on_results)
        final_ref = refs.get(L1R_V5_SMOOTH_FINAL)
        for dt in (V9_REF_DT, 2.0e-4):
            tagged += [(f"v5p3_l1r_dt{_dt_tag(dt)}", c) for c in v5_smooth_checks(
                dt, on[dt], final_ref=final_ref, ref_key=L1R_V5_SMOOTH_FINAL.notation())]
        if off:
            record["V9-1 predictor off (record)"] = predictor_off_record(off, on,
                                                                         ref_dt_s=V9_REF_DT)
    return tagged, record


def _judge_v9_free(refs, index):
    from outrigger_sim.verify.l1r import knee_record, mode_amplitude_phase_at, v9_free_checks
    from outrigger_sim.verify.metrics import modal_coordinates
    from outrigger_sim.verify.reference import L1R_LOCK_F_DAMPED_HZ

    modal = _lock_modal(refs, "top")
    f1 = float(refs.get(L1R_LOCK_F_DAMPED_HZ, level="top")[0])
    fits, knees = {}, {}
    for dt in V9_DTS:
        result, series = _load_case(index, f"v9free_l1r_dt{_dt_tag(dt)}")
        if result is None:
            continue
        eta1 = modal_coordinates(series["q"], modal.phi, modal.mass_matrix)[:, 0]
        fits[dt] = mode_amplitude_phase_at(series["t"], eta1, f1)
        knees[dt] = knee_record(_module_record(result, series)).__dict__
    record = {"fits": fits, "knee": knees}
    if len(fits) < len(V9_DTS):
        return [], record
    checks, v9_record = v9_free_checks(
        "V9-2 L1-R mode-1 free vibration t = 5 s (V7a top roll 0.0046 deg)",
        {dt: f["amplitude_at_s"] for dt, f in fits.items()},
        {dt: f["phase_at_s_rad_unwrapped"] for dt, f in fits.items()}, ref_dt_s=V9_REF_DT)
    record.update(v9_record)
    return [("v9free_l1r (V9-2)", c) for c in checks], record


def _case_table(tagged):
    """Per case (or V9 group): number of checks, failed items, all passed."""
    table: dict[str, dict] = {}
    for owner, check in tagged:
        row = table.setdefault(owner, {"n_checks": 0, "failed": [], "ids": []})
        row["n_checks"] += 1
        if check.id not in row["ids"]:
            row["ids"].append(check.id)
        if not check.passed:
            row["failed"].append(check.item)
    for row in table.values():
        row["passed"] = not row["failed"]
    return dict(sorted(table.items()))


def judge(cand):
    """Judgement summary of the indexed cases (verify.l1r) -> :data:`JUDGED`."""
    import hashlib

    from outrigger_sim.verify.checks import summary_table

    refs = _references(cand)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    tagged, info, v7a = [], [], {}
    for level in LEVELS:
        level_tagged, level_info, v7a[level] = _judge_v7a_level(refs, index, level)
        tagged += level_tagged
        info += level_info
    v7b_tagged, v7b = _judge_v7b(refs, index)
    v5_tagged, v5 = _judge_v5(refs, index)
    v9_tagged, v9 = _judge_v9_free(refs, index)
    tagged += v7b_tagged + v5_tagged + v9_tagged
    rows = []
    for owner, check in tagged:
        rows.append({"case": owner, **check.as_dict()})
    yaml = ROOT / "02_params" / "rexome33.yaml"
    doc = {"meta": {"generated": _dt.datetime.now().isoformat(timespec="seconds"),
                    "script": "04_scripts/02_chrono/run_L1R_checks.py judge",
                    "definition": "dynamics_model.md rev. 32 5.14.6-5.14.8 (+ V9-2 redefinition)"
                                  ", 5.14.12 V9-1 order rule",
                    "verify_module": "outrigger_sim.verify.l1r",
                    "reference_source": cand["source"],
                    "reference_sha256": refs.sha256_by_file(),
                    "yaml_sha256": hashlib.sha256(yaml.read_bytes()).hexdigest(),
                    "raw_summary": _rel(OUT), "index": _rel(INDEX), "m1": m1_status(),
                    "judgement": "automatic pre-check; final judgement dynamics-expert. Ids: "
                                 "'V7a gate', 'V7a', 'V5p3 gate', 'V9', 'V5' judged; 'V7b' "
                                 "record judgement (5.12.5); 'info' identification cross-check",
                    "decisions_of_this_module (definition left open)": list(JUDGEMENT_DECISIONS)},
           "case_table": _case_table(tagged),
           "checks": rows, "info": summary_table(info),
           "records": {"V7a": v7a, "V7b": v7b, "V5_V9-1": v5, "V9-2": v9}}
    JUDGED.parent.mkdir(parents=True, exist_ok=True)
    JUDGED.write_text(json.dumps(_plain_keys(doc), indent=1), encoding="utf-8")
    failed = sum(not c.passed for _, c in tagged)
    print(f"judgement -> {_rel(JUDGED)} ({len(tagged)} checks, {failed} failed)")
    return doc


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("run", "list", "summary", "judge"))
    ap.add_argument("--jobs", type=int, default=MAX_WORKERS)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--candidate", type=Path, default=None,
                    help="L1-R block file (default: reference.json if it has the key, else the candidate)")
    a = ap.parse_args(argv)
    if a.action == "list":
        print("\n".join(case_ids()))
        return
    cand = _candidate(a.candidate)
    if a.action == "judge":
        judge(cand)
        return
    if a.action == "run":
        ids = a.only or case_ids()
        bad = [c for c in ids if c not in case_ids()]
        if bad:
            raise SystemExit(f"unknown cases {bad}")
        run_batch(ids, min(a.jobs, MAX_WORKERS), cand)
    summarize(cand)
    judge(cand)


if __name__ == "__main__":
    main(sys.argv[1:])
