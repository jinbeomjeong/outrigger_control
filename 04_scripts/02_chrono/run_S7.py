"""S7 runs: L2b-NSC four-leg model (force-law legs, lateral bushings, NSC pads and crawler).

``00_docs/03_chrono/chrono_build_plan.md`` S7; reference values ``06_analysis/00_dynamics/
reference.json / L2b_NSC_reference_rev33`` (``dynamics_model.md`` rev. 33 5.20). Usage
(Chrono-dev python, from any folder)::

    python -I -X utf8 -u run_S7.py list                       # case table + wall estimate
    python -I -X utf8 -u run_S7.py smoke [--level top] [--settle 10]
    python -I -X utf8 -u run_S7.py cost [--seconds 2]        # step cost, P-core pinned, alone
    python -I -X utf8 -u run_S7.py check [--jobs 7]          # every case capped at 0.3 s (code path)
    python -I -X utf8 -u run_S7.py run --approved [--jobs 7] [--only ID ...]

``run`` is the V0-V14 judgement batch: it runs only with ``--approved`` (the user is told before
the S7 main run, coordinator instruction 2026-10-24). The judge (``verify/s7.py``, reference paths
of 5.20.11) reads the case outputs afterwards; this script stores raw series and summaries only.

Cases (id: kind, what it serves):

* ``settle_<level>``: static start (rev. 33 analytic solution, rod side locked at ``dc = 0``),
  settle 10 s + still 5 s, every step stored in the still window: V0, V1, V2 (axial spring
  compression ``F / k_2``), V3, V13(NSC) (0.1 s window means, step std of N and F, 5.20.9 Q3),
  V10 (three levels); pad force cross-check (risk 5) every 0.1 s.
* ``V5_FL_p1mm`` / ``V5_FL_p5mm``: FL +1 / +5 mm at 0.5 mm/s, settle 10 s.
* ``V6_FLp`` / ``V6_RLp`` / ``V6_RLm``: one leg at 0.1 mm/s until a pad lifts (+1 s) or 160 s.
* ``V7_<level>``: initial body velocity (roll, pitch, yaw, heave) from the static start, 25 s at
  1 ms; amplitude ~0.5 kN per leg, below 0.5 x the knee (5.20.4).
* ``V8a_top_dt{1,2}e-4``: as V7 top with every dashpot 0 (axial and lateral), 60 s at dt and 2 dt.
* ``V9_FLp1_dt*``: V5 +1 mm at dt 1e-4 / 5e-5 / 2.5e-5 and the reference 1e-5 s.
* ``V9s_<psor100|rec005>_FLp1_dt*`` (``--only``, not in the default list): V9 (b) PSOR-noise
  sensitivity, the V9 case with PSOR 100 iterations or recovery speed 0.05 m/s.
* ``V11_air``: superstructure fixed in the air, legs hanging, V0 sign test then the V11 schedule.
* ``V11b_FL`` / ``V11b_RL``: single leg, pad locked to the floor (``ChLinkLockLock``, 5.20.9 Q5),
  extend to the 210 bar stop, hold, retract to the pull stop, hold.
* ``V12_<i>``: the ``slope_V12`` cases (floor tilted, zero-force placement, gravity ramp 3 s,
  settle 53 s, mean of the last 3 s; rod side armed only after the settle, 5.20.7).
* ``V4_lift_top``: legs at 0 on the rigid crawler, all legs +v_max to ``e_op`` (lift plan of S3),
  ``dt_transition_s`` in the touch window; per-step touch times.
* ``V14_<case>_RL`` / ``V14_<case>_modes``: V14 cases (level, pitch +4.0599, roll +6.2252, diag
  2.4621 / 2.4621 deg, read from the reference block; V12 procedure, rod side armed after the settle), then RL+ at 0.1 mm/s to
  lift-off, or the initial-velocity modal window (20 s).

Outputs: ``07_results/S7/<batch>/<case>/series.npz`` + ``result.json`` + ``case.json``.
Units SI; angles in deg where named ``*_deg``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

RESULTS = ROOT / "07_results" / "S7"
ANALYSIS_DIR = ROOT / "06_analysis" / "01_chrono" / "17_S7"
MAX_JOBS = 7
"""Coordinator 2026-10-24 (R8 finished, user policy: use the machine): <= 7 P-core workers, one of
the 8 P-cores left free (was 4 while control-expert ran R8 on the reduced plant)."""
V9S_DTS = (1.0e-4, 5.0e-5, 2.5e-5, 1.0e-5)
V9S_VARIANTS = {
    "psor100": {"psor_max_iterations": 100},
    "rec005": {"recovery_speed_m_s": 0.05},
}
"""V9 (b) PSOR-noise sensitivity (``dynamics_model.md`` 5.22.3 (b), 5.20.9 Q3; user approval
2026-10-24): A = PSOR 100 iterations (YAML 50), B = PSOR 50 + ``SetMaxPenetrationRecoverySpeed``
0.05 m/s (Chrono default 0.6 m/s, ``ChSystem.cpp:43``). Not in the default case list (``--only``)."""

REF_BLOCK = "L2b_NSC_reference_rev33"
V14_JUDGED = ("level", "max pitch+", "max roll+", "max diag 45")
"""V14 cases of ``reference.json / L2b_NSC_reference_rev33 / V14 / cases``: slope and extensions
are read from there (rev. 33 supplement 1: sensor end 0.6948 m x 0.999); ``max pitch-`` is not
judged (RL at its stroke end)."""
V14_TAG = {"level": "flat", "max pitch+": "pitchp", "max roll+": "rollp", "max diag 45": "diag"}
CREEP_SPEED_M_S = 1.0e-4
STEP_SPEED_M_S = 5.0e-4
IMPULSE_OMEGA_RAD_S = (1.0e-4, 1.0e-4, 5.0e-5)
"""ASSUMPTION (this script): initial body angular velocity (world x, y, z) of the modal runs;
largest leg force swing about 0.5 kN < 0.5 knee (2 kN at e_op), rule of 5.20.4 / L1-R V7a."""
IMPULSE_HEAVE_M_S = 1.0e-4
SLOPE_RAMP_S = 3.0
SLOPE_SETTLE_S = 53.0
SLOPE_MEAN_S = 3.0
LIFTOFF_EXTRA_S = 1.0
CREEP_MAX_S = 160.0


# --- case table ------------------------------------------------------------------------------


def _refs() -> dict[str, Any]:
    return json.loads((ROOT / "06_analysis" / "00_dynamics" / "reference.json").read_text(
        encoding="utf-8"))


def case_table() -> dict[str, dict[str, Any]]:
    refs = _refs()
    cases: dict[str, dict[str, Any]] = {}
    for level in ("top", "middle", "bottom"):
        cases[f"settle_{level}"] = {"kind": "settle", "level": level, "settle_s": 10.0,
                                    "still_s": 5.0, "V": ["V0", "V1", "V2", "V3", "V10", "V13"]}
    for mm in (1, 5):
        cases[f"V5_FL_p{mm}mm"] = {"kind": "leg_step", "level": "top", "leg": "FL",
                                   "delta_m": mm * 1e-3, "speed_m_s": STEP_SPEED_M_S,
                                   "settle_after_s": 10.0, "V": ["V5"]}
    for tag, leg, sign in (("FLp", "FL", 1.0), ("RLp", "RL", 1.0), ("RLm", "RL", -1.0)):
        cases[f"V6_{tag}"] = {"kind": "leg_creep", "level": "top", "leg": leg,
                              "speed_m_s": sign * CREEP_SPEED_M_S, "max_s": CREEP_MAX_S,
                              "V": ["V6"]}
    for level in ("top", "middle", "bottom"):
        cases[f"V7_{level}"] = {"kind": "impulse", "level": level, "window_s": 25.0,
                                "V": ["V7", "V10"]}
    for dt in (1.0e-4, 2.0e-4):
        cases[f"V8a_top_dt{dt:.0e}"] = {"kind": "impulse", "level": "top", "window_s": 60.0,
                                        "damping": "zero", "lateral_damping_scale": 0.0,
                                        "dt_s": dt, "V": ["V8a"]}
    for dt in (1.0e-4, 5.0e-5, 2.5e-5, 1.0e-5):
        cases[f"V9_FLp1_dt{dt:.1e}"] = {"kind": "leg_step", "level": "top", "leg": "FL",
                                        "delta_m": 1e-3, "speed_m_s": STEP_SPEED_M_S,
                                        "settle_after_s": 10.0, "dt_s": dt, "V": ["V9"]}
    cases["V11_air"] = {"kind": "air_stroke", "level": "top", "V": ["V0", "V11"]}
    for leg in ("FL", "RL"):
        cases[f"V11b_{leg}"] = {"kind": "v11b", "level": "top", "leg": leg, "V": ["V11b"]}
    for i, name in enumerate(k for k in refs["slope_V12"] if k.startswith("ground ")):
        roll, pitch = _parse_slope(name)
        cases[f"V12_{i}"] = {"kind": "slope", "level": "top", "roll_deg": roll,
                             "pitch_deg": pitch, "extensions_ref_m":
                             refs["slope_V12"][name]["extension_exact_m"], "case_name": name,
                             "arm_rod_side_after_settle": False, "then": None, "V": ["V12"]}
    cases["V4_lift_top"] = {"kind": "lift", "level": "top", "V": ["V4"]}
    v14 = refs[REF_BLOCK]["V14"]["cases"]
    for name in V14_JUDGED:
        roll, pitch = (float(a) for a in v14[name]["ground_roll_pitch_deg"])
        ext = v14[name]["extension_m"]
        for then in ("creep_RL", "modes"):
            cases[f"V14_{V14_TAG[name]}_{'RL' if then == 'creep_RL' else 'modes'}"] = {
                "kind": "slope", "level": "top", "roll_deg": roll, "pitch_deg": pitch,
                "extensions_ref_m": ext, "case_name": name, "arm_rod_side_after_settle": True,
                "then": then, "V": ["V14"]}
    return cases


def sensitivity_cases() -> dict[str, dict[str, Any]]:
    """V9 (b) sensitivity cases: ``V9_FLp1_dt*`` with a solver override (``V9S_VARIANTS``).

    Kept out of :func:`case_table` so the default batch and its ids stay as before; select them
    with ``--only``."""
    cases: dict[str, dict[str, Any]] = {}
    for tag, override in V9S_VARIANTS.items():
        for dt in V9S_DTS:
            cases[f"V9s_{tag}_FLp1_dt{dt:.1e}"] = {
                "kind": "leg_step", "level": "top", "leg": "FL", "delta_m": 1e-3,
                "speed_m_s": STEP_SPEED_M_S, "settle_after_s": 10.0, "dt_s": dt,
                "solver_override": dict(override), "V": ["V9s"]}
    return cases


def _apply_solver_override(model, override: dict[str, Any] | None) -> dict[str, Any] | None:
    """Apply a V9 (b) solver override right after the model is built (None: untouched)."""
    if not override:
        return None
    out: dict[str, Any] = {"requested": dict(override)}
    system = model.system
    if "psor_max_iterations" in override:
        iterative = system.GetSolver().AsIterative()
        if iterative is None:
            raise RuntimeError("solver override: the NSC solver is not iterative")
        iterative.SetMaxIterations(int(override["psor_max_iterations"]))
        out["max_iterations_readback"] = int(iterative.GetMaxIterations())
    if "recovery_speed_m_s" in override:
        # ChSystem.h:123 (default 0.6 m/s, used by EULER_IMPLICIT_LINEARIZED); no Python getter.
        system.SetMaxPenetrationRecoverySpeed(float(override["recovery_speed_m_s"]))
        out["recovery_speed_set_m_s"] = float(override["recovery_speed_m_s"])
    unknown = set(override) - {"psor_max_iterations", "recovery_speed_m_s"}
    if unknown:
        raise ValueError(f"solver override: unknown keys {sorted(unknown)}")
    return out


def _parse_slope(name: str) -> tuple[float, float]:
    from outrigger_sim.scenarios.slope import parse_case

    return parse_case(name)


def simulated_seconds(case: dict[str, Any]) -> tuple[float, float]:
    """(simulated time, equivalent steps at 1e-4 s) for the wall estimate."""
    kind = case["kind"]
    dt = case.get("dt_s", 1.0e-4)
    if kind == "settle":
        t = 1.0 * (case["settle_s"] + case["still_s"])
    elif kind == "leg_step":
        t = 1.0 + case["delta_m"] / case["speed_m_s"] + 0.2 + case["settle_after_s"]
    elif kind == "leg_creep":
        t = 1.0 + 13.0e-3 / abs(case["speed_m_s"]) + LIFTOFF_EXTRA_S  # ~ lift-off at 11-13 mm
    elif kind == "impulse":
        t = 1.0 + case["window_s"]
    elif kind == "air_stroke":
        t = 1.2 + 69.0
    elif kind == "v11b":
        t = 3.0
    elif kind == "slope":
        t = SLOPE_RAMP_S + SLOPE_SETTLE_S
        if case["then"] == "creep_RL":
            t += 1.0 + 16.0e-3 / CREEP_SPEED_M_S
        elif case["then"] == "modes":
            t += 20.0
    elif kind == "lift":
        t = 1.0 + 35.4  # lift plan end (top)
        return t, t / 1e-4 + 2.0 / 1e-5 - 2.0 / 1e-4  # ~2 s at 1e-5
    else:
        raise ValueError(kind)
    return t, t / dt


# --- helpers ------------------------------------------------------------------------------------


def _params(level: str):
    from outrigger_sim.params import load_params

    return load_params(level=level, model="L2b_NSC")


def _run_meta(params, model, scenario: str, settings: dict[str, Any], placement: Any):
    from outrigger_sim.record import make_run_meta
    from outrigger_sim.verify.reference import load_references

    return make_run_meta(params, model.meta(), scenario=scenario, scenario_settings=settings,
                         reference_sha256=load_references().sha256_by_file(),
                         extra={"cpu_placement": placement})


class _Series:
    """Per-sample arrays of an L2bModel run."""

    def __init__(self) -> None:
        self.rows: dict[str, list[Any]] = {}

    def add(self, model, probe) -> None:
        import numpy as np

        from outrigger_sim.frames import roll_pitch_from_quat

        n = probe.floor_normal_world
        act = model.actuator
        values = {
            "t_s": probe.t_s,
            "pad_normal_N": probe.pad_normal_force_N,
            "pad_contact_world_N": probe.pad_contact_world_N,
            "cylinder_force_N": probe.motor_force_N,
            "motor_pos_m": probe.motor_pos_m,
            "s_ref_m": act.reference.s_ref_m,
            "u_applied_m_s": act.reference.u_applied_m_s,
            "roll_pitch_deg": np.degrees(roll_pitch_from_quat(probe.body_quat_wxyz)),
            "body_pos_m": probe.body_pos_m,
            "body_vel_m_s": probe.body_vel_m_s,
            "body_omega_rad_s": probe.body_omega_rad_s,
            "crawler_normal_N": float(probe.crawler_contact_world_N @ n),
            "lateral_disp_m": model.bushings.displacement_m(),
            "lateral_force_N": model.bushings.acting_force_on_rod_N,
            "pad_centre_world_m": probe.pad_sphere_centre_world_m,
            "rod_pressure_Pa": (act.rod_side.rod_pressure_Pa if act.rod_side is not None
                                else np.zeros(4)),
            "saturated": act.reference.saturated,
            "n_contacts": probe.n_contacts,
        }
        for k, v in values.items():
            self.rows.setdefault(k, []).append(np.array(v, copy=True))

    def save(self, path: Path) -> dict[str, Any]:
        import numpy as np

        arrays = {k: np.asarray(v) for k, v in self.rows.items()}
        np.savez_compressed(path, **arrays)
        bad = sum(int(np.count_nonzero(~np.isfinite(a))) for a in arrays.values()
                  if a.dtype.kind == "f")
        return {"file": path.name, "samples": int(arrays["t_s"].size) if arrays else 0,
                "nonfinite_values": bad}


def _run(model, seconds: float, series: _Series | None, every: int,
         command_fn=None, stop_fn=None) -> dict[str, Any]:
    """Step ``seconds`` (``command_fn(t_rel)`` may return a command; ``stop_fn(probe)`` ends)."""
    n = round(seconds / model.dt_s)
    t0 = float(model.system.GetChTime())
    wall0 = time.perf_counter()
    k_done = 0
    stopped = False
    for k in range(1, n + 1):
        if command_fn is not None:
            cmd = command_fn(float(model.system.GetChTime()) - t0)
            if cmd is not None:
                model.set_command(cmd)
        capture = series is not None and k % every == 0
        res = model.step(capture=capture or stop_fn is not None and k % every == 0)
        k_done = k
        if res.probe is not None:
            if series is not None:
                series.add(model, res.probe)
            if stop_fn is not None and stop_fn(res.probe):
                stopped = True
                break
    return {"steps": k_done, "wall_s": time.perf_counter() - wall0, "stopped": stopped,
            "sim_s": k_done * model.dt_s}


def _cap(settings: dict[str, Any], seconds: float) -> float:
    cap = settings.get("cap_s")
    return seconds if cap is None else min(seconds, float(cap))


# --- jobs ---------------------------------------------------------------------------------------


def job(case, case_dir: Path):
    """Batch job (module-level, spawn): dispatch on ``settings["kind"]``."""
    from outrigger_sim.batch import CaseResult
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    s = dict(case.settings)
    fn = {"settle": _job_settle, "leg_step": _job_leg_step, "leg_creep": _job_leg_creep,
          "impulse": _job_impulse, "air_stroke": _job_air, "v11b": _job_v11b,
          "slope": _job_slope, "lift": _job_lift}[s["kind"]]
    summary, model, params = fn(s, case_dir)
    act = getattr(model, "actuator", None)
    if act is not None:
        summary["piston_monitor"] = act.piston_monitor()  # 5.20.11: stop violations, expect 0
        if act.rod_side is not None:
            summary["rod_side_lock_table"] = act.rod_side.lock_table()
    run_meta = None if model is None else _run_meta(params, model, f"S7_{s['kind']}", s, placement)
    (case_dir / "result.json").write_text(json.dumps(summary, indent=1, default=float),
                                          encoding="utf-8")
    return CaseResult(summary=json.loads(json.dumps(summary, default=float)), run_meta=run_meta)


def _model(params, **kw):
    from outrigger_sim.chrono.l2b_model import L2bModel

    return L2bModel(params, **kw)


def _window_stats(series: _Series, window: int) -> dict[str, Any]:
    """0.1 s moving-window means (``window`` samples) of N and F, step std (5.20.9 Q3)."""
    import numpy as np

    n = np.asarray(series.rows["pad_normal_N"])
    f = np.asarray(series.rows["cylinder_force_N"])
    rp = np.asarray(series.rows["roll_pitch_deg"])
    kernel = np.ones(window) / window

    def moving(a):
        return np.column_stack([np.convolve(a[:, j], kernel, mode="valid")
                                for j in range(a.shape[1])])

    mn, mf = moving(n), moving(f)
    return {
        "pad_normal_mean_N": n.mean(axis=0).tolist(),
        "pad_normal_window_span_N": np.ptp(mn, axis=0).tolist(),
        "pad_normal_step_std_N": n.std(axis=0).tolist(),
        "cylinder_force_mean_N": f.mean(axis=0).tolist(),
        "cylinder_force_window_span_N": np.ptp(mf, axis=0).tolist(),
        "cylinder_force_step_std_N": f.std(axis=0).tolist(),
        "roll_pitch_mean_deg": rp.mean(axis=0).tolist(),
        "roll_pitch_span_deg": np.ptp(rp, axis=0).tolist(),
    }


def _job_settle(s, case_dir):
    import numpy as np

    from outrigger_sim.chrono.l2b_model import pad_force_crosscheck
    from outrigger_sim.record import save_snapshot

    params = _params(s["level"])
    model = _model(params, crawler=True)
    inventory = model.v0_inventory()
    coarse = _Series()
    r1 = _run(model, _cap(s, s["settle_s"]), coarse, every=100)
    still = _Series()
    cross = []
    n_still = round(_cap(s, s["still_s"]) / model.dt_s)
    every_cross = round(0.1 / model.dt_s)
    wall0 = time.perf_counter()
    for k in range(1, n_still + 1):
        res = model.step(capture=True)
        still.add(model, res.probe)
        if k % every_cross == 0:
            cross.append(pad_force_crosscheck(model))
    wall_still = time.perf_counter() - wall0
    info_coarse = coarse.save(case_dir / "series_settle.npz")
    info_still = still.save(case_dir / "series_still.npz")
    window = min(round(0.1 / model.dt_s), len(still.rows["t_s"]))
    stats = _window_stats(still, window)
    k2 = model.k_ax0_N_m
    stats["axial_spring_compression_mm"] = (
        1e3 * np.asarray(stats["cylinder_force_mean_N"]) / k2).tolist()
    snap = save_snapshot(model.snapshot(), f"S7_L2b_{s['level']}", directory=case_dir,
                         overwrite=True, note={"stage": "S7 settle end"})
    return ({"inventory_V0": inventory, "start_forces_N": model.start_forces_N.tolist(),
             "k_ax0_N_m": k2.tolist(), "still": stats, "crosscheck": cross,
             "series": [info_coarse, info_still], "snapshot": str(snap.name),
             "steps": r1["steps"] + n_still, "wall_s": r1["wall_s"] + wall_still},
            model, params)


def _settled_model(params, solver_override=None, **kw):
    model = _model(params, **kw)
    model.solver_override_applied = _apply_solver_override(model, solver_override)
    _run(model, 1.0, None, every=1)
    return model


def _job_leg_step(s, case_dir):
    import numpy as np

    from outrigger_sim.params import LEG_ORDER

    params = _params(s["level"])
    model = _settled_model(params, solver_override=s.get("solver_override"), dt_s=s.get("dt_s"))
    i = LEG_ORDER.index(s["leg"])
    ref = model.actuator.reference
    hi = ref.soft_limits_m[:, 1].copy()
    lo = ref.soft_limits_m[:, 0].copy()
    if s["delta_m"] > 0:
        hi[i] = ref.s_ref_m[i] + s["delta_m"]
    else:
        lo[i] = ref.s_ref_m[i] + s["delta_m"]
    ref.set_soft_limits(lo, hi)
    cmd = np.zeros(4)
    cmd[i] = math.copysign(abs(s["speed_m_s"]), s["delta_m"])
    model.set_command(cmd)
    series = _Series()
    every = max(1, round(1e-3 / model.dt_s))
    t_move = abs(s["delta_m"]) / abs(s["speed_m_s"]) + 0.2
    r = _run(model, _cap(s, t_move + s["settle_after_s"]), series, every=every)
    info = series.save(case_dir / "series.npz")
    out = {"run": r, "series": info, "leg": s["leg"], "delta_m": s["delta_m"],
           "dt_s": model.dt_s}
    if model.solver_override_applied is not None:
        out["solver_override"] = model.solver_override_applied
    return out, model, params


def _liftoff_stop(model, window: int):
    """Stop function: any pad's 0.1 s mean normal force <= 0 -> end LIFTOFF_EXTRA_S later."""
    import collections

    import numpy as np

    buf: collections.deque = collections.deque(maxlen=window)
    state = {"t_lift": None}

    def stop(probe) -> bool:
        buf.append(probe.pad_normal_force_N.copy())
        if state["t_lift"] is None and len(buf) == window:
            if np.any(np.mean(buf, axis=0) <= 0.0):
                state["t_lift"] = probe.t_s
        return state["t_lift"] is not None and probe.t_s >= state["t_lift"] + LIFTOFF_EXTRA_S

    return stop, state


def _job_leg_creep(s, case_dir):
    import numpy as np

    from outrigger_sim.params import LEG_ORDER

    params = _params(s["level"])
    model = _settled_model(params)
    i = LEG_ORDER.index(s["leg"])
    cmd = np.zeros(4)
    cmd[i] = s["speed_m_s"]
    model.set_command(cmd)
    series = _Series()
    every = round(1e-3 / model.dt_s)
    stop, state = _liftoff_stop(model, window=100)
    r = _run(model, _cap(s, s["max_s"]), series, every=every, stop_fn=stop)
    info = series.save(case_dir / "series.npz")
    return ({"run": r, "series": info, "liftoff_t_s": state["t_lift"]}, model, params)


def _kick(model, omega=IMPULSE_OMEGA_RAD_S, heave=IMPULSE_HEAVE_M_S) -> dict[str, Any]:
    from outrigger_sim.chrono.probes import chvec

    sup = model.superstructure
    w = sup.GetAngVelParent()
    v = sup.GetPosDt()
    sup.SetAngVelParent(chvec((w.x + omega[0], w.y + omega[1], w.z + omega[2])))
    sup.SetPosDt(chvec((v.x, v.y, v.z + heave)))
    return {"omega_add_world_rad_s": list(omega), "heave_add_m_s": heave,
            "t_s": float(model.system.GetChTime()),
            "rule": "ASSUMPTION: superstructure COG velocity kick, rods untouched"}


def _job_impulse(s, case_dir):
    params = _params(s["level"])
    model = _settled_model(params, dt_s=s.get("dt_s"), damping=s.get("damping", "rev33"),
                           lateral_damping_scale=s.get("lateral_damping_scale", 1.0))
    kick = _kick(model)
    series = _Series()
    every = max(1, round(1e-3 / model.dt_s))
    r = _run(model, _cap(s, s["window_s"]), series, every=every)
    info = series.save(case_dir / "series.npz")
    return ({"run": r, "series": info, "kick": kick, "dt_s": model.dt_s,
             "damping": s.get("damping", "rev33")}, model, params)


def _job_air(s, case_dir):
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.scenarios.stroke import air_pose, sign_test_schedule, v11_schedule

    params = _params(s["level"])
    model = _model(params, pose=BodyPose(air_pose(params)), extensions_m=(0.0,) * 4,
                   start="hanging", crawler=False)
    model.fix_superstructure()
    out = {}
    for name, sched in (("sign", sign_test_schedule(params)), ("v11", v11_schedule(params))):
        series = _Series()
        sched.reset()
        r = _run(model, _cap(s, sched.end_s), series, every=10,
                 command_fn=lambda t, sc=sched: sc(t))
        out[name] = {"run": r, "series": series.save(case_dir / f"series_{name}.npz"),
                     "schedule": sched.as_dict()}
        model.set_command([0.0] * 4)
    return out, model, params


def _job_v11b(s, case_dir):
    import numpy as np
    import pychrono as ch

    from outrigger_sim.chrono.single_leg_l2b import SingleLegL2bModel

    params = _params(s["level"])
    m = SingleLegL2bModel(params, s["leg"], floor=True, preload_N=100.0e3, rod_side=False)
    lock = ch.ChLinkLockLock()  # 5.20.9 Q5: rigid two-sided pad-floor bond (V11b only)
    p = m.rod.GetPos()
    lock.Initialize(m.rod, m.bundle.floor, ch.ChFramed(ch.ChVector3d(p.x, p.y, p.z), ch.QUNIT))
    m.system.Add(lock)
    phases = [(1.0, 1.0), (0.3, 0.0), (1.5, -1.0), (0.3, 0.0)]
    rows: dict[str, list[Any]] = {}
    for duration, cmd in phases:
        m.set_command(cmd)
        for _ in range(round(_cap(s, duration) / m.dt_s)):
            smp = m.step()
            for k, v in smp.__dict__.items():
                rows.setdefault(k, []).append(v)
    arrays = {k: np.asarray(v) for k, v in rows.items()}
    np.savez_compressed(case_dir / "series.npz", **arrays)
    return ({"leg": s["leg"], "phases_s_cmd": phases, "force_max_N": float(arrays["force_N"].max()),
             "force_min_N": float(arrays["force_N"].min()),
             "saturation_starts": m.actuator.reference.saturation_start_count.tolist(),
             "bond": "ChLinkLockLock rod-floor (rigid two-sided)"}, m, params)


def slope_pose(params, roll_deg: float, pitch_deg: float, ext_ref):
    """Floor pose, level body origin and exact plane-touching extensions closest to ``ext_ref``
    (same algorithm as ``scenarios.slope.slope_start``, any roll / pitch)."""
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.frames import matrix_to_quat
    from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m
    from outrigger_sim.scenarios.slope import floor_normal, floor_rotation

    n = floor_normal(roll_deg, pitch_deg)
    rot = floor_rotation(n)
    z_floor = float(params.ground.crawler_bottom_z_m)
    p0 = np.array([0.0, 0.0, z_floor])
    d = extension_direction(params)
    radii = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    c0 = np.array([pad_sphere_centre_body_m(params, i, 0.0) for i in range(4)])
    base = radii - (c0 - p0) @ n
    e_ref = np.asarray(ext_ref, dtype=float)
    z_o = float(np.mean(base - e_ref * float(n @ d)) / n[2])
    ext = (base - n[2] * z_o) / float(n @ d)
    floor = BodyPose(tuple(p0 - rot @ p0), tuple(float(v) for v in matrix_to_quat(rot)))
    return floor, BodyPose((0.0, 0.0, z_o)), tuple(float(e) for e in ext), n


def _job_slope(s, case_dir):
    import numpy as np

    from outrigger_sim.chrono.system import set_gravity
    from outrigger_sim.params import LEG_ORDER
    from outrigger_sim.scenarios.slope import gravity_ramp

    params = _params(s["level"])
    floor, pose, ext, normal = slope_pose(params, s["roll_deg"], s["pitch_deg"],
                                          s["extensions_ref_m"])
    model = _model(params, pose=pose, extensions_m=ext, start=[0.0] * 4, floor_pose=floor,
                   rod_side_armed=False)
    g = params.meta.gravity_m_s2
    ramp = _cap(s, SLOPE_RAMP_S)
    set_gravity(model.system, (0.0, 0.0, 0.0))

    def ramp_cmd(t):
        set_gravity(model.system, (0.0, 0.0, -g * gravity_ramp(t, ramp)))
        return None

    series = _Series()
    r1 = _run(model, ramp, series, every=10, command_fn=ramp_cmd)
    set_gravity(model.system, (0.0, 0.0, -g))
    r2 = _run(model, _cap(s, SLOPE_SETTLE_S), series, every=10)
    n_mean = round(min(SLOPE_MEAN_S, r2["sim_s"]) / (10 * model.dt_s))
    mean = {k: np.asarray(series.rows[k][-n_mean:]).mean(axis=0).tolist()
            for k in ("pad_normal_N", "pad_contact_world_N", "cylinder_force_N",
                      "roll_pitch_deg", "lateral_force_N")}
    slip = (np.asarray(series.rows["pad_centre_world_m"][-1])
            - np.asarray(series.rows["pad_centre_world_m"][0]))
    out: dict[str, Any] = {"case_name": s["case_name"], "floor_normal": normal.tolist(),
                           "extensions_m": list(ext), "ramp": r1, "settle": r2,
                           "mean_last_s": mean, "pad_slip_m": slip.tolist()}
    then = s.get("then")
    if s.get("arm_rod_side_after_settle"):
        model.actuator.rod_side.arm()
        out["rod_side_armed_t_s"] = float(model.system.GetChTime())
    if then == "creep_RL":
        i = LEG_ORDER.index("RL")
        cmd = np.zeros(4)
        cmd[i] = CREEP_SPEED_M_S
        model.set_command(cmd)
        stop, state = _liftoff_stop(model, window=100)
        tail = _Series()
        out["creep"] = _run(model, _cap(s, CREEP_MAX_S), tail, every=10, stop_fn=stop)
        out["liftoff_t_s"] = state["t_lift"]
        out["series_creep"] = tail.save(case_dir / "series_creep.npz")
    elif then == "modes":
        _run(model, _cap(s, 1.0), None, every=1)  # lock with the law armed
        out["kick"] = _kick(model)
        tail = _Series()
        out["modes"] = _run(model, _cap(s, 20.0), tail, every=10)
        out["series_modes"] = tail.save(case_dir / "series_modes.npz")
    out["series"] = series.save(case_dir / "series.npz")
    return out, model, params


def _job_lift(s, case_dir):
    import numpy as np

    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.scenarios.lift import lift_plan

    params = _params(s["level"])
    refs = _refs()[REF_BLOCK]
    touch_ref = refs["V4_NSC"]["L2b_dynamic"]["touch_s (FL, FR, RL, RR)"]
    f1 = refs["levels"][s["level"]]["modes"]["LOCK"]["f_damped_Hz (first 6)"][0]
    plan = lift_plan(params, reference_touch_eq_s=touch_ref, first_rocking_Hz=f1)
    model = _model(params, pose=BodyPose((0.0, 0.0, 0.0)), extensions_m=(0.0,) * 4,
                   start="hanging", crawler=True)
    _run(model, _cap(s, 1.0), None, every=1)  # settle on the rigid crawler
    ref = model.actuator.reference
    ref.set_soft_limits(None, np.asarray(plan.e_op_m))
    sched = plan.schedule()
    t_cmd0 = float(model.system.GetChTime())
    w0, w1 = plan.transition_window_s
    dt_fine = float(params.get("simulation.dt_transition_s"))
    dt_coarse = model.dt_s
    series = _Series()
    touch = [None] * 4
    end = _cap(s, plan.end_s)
    wall0 = time.perf_counter()
    steps = 0
    while float(model.system.GetChTime()) - t_cmd0 < end - 1e-12:
        t_rel = float(model.system.GetChTime()) - t_cmd0
        model.set_dt(dt_fine if w0 - 1e-12 <= t_rel < w1 - 1e-12 else dt_coarse)
        cmd = sched(t_rel)
        if cmd is not None:
            model.set_command(cmd)
        res = model.step(capture=True)
        steps += 1
        p = res.probe
        for i in range(4):
            if touch[i] is None and p.pad_normal_force_N[i] > 0.0:
                touch[i] = p.t_s - t_cmd0 - plan.equivalent_origin_s
        if steps % 10 == 0 or dt_fine == model.dt_s and steps % 100 == 0:
            series.add(model, p)
    return ({"plan": plan.as_dict(), "touch_eq_s": touch, "reference_touch_eq_s": touch_ref,
             "steps": steps, "wall_s": time.perf_counter() - wall0,
             "series": series.save(case_dir / "series.npz")}, model, params)


# --- actions ------------------------------------------------------------------------------------


def action_list(cost_us: float, sensitivity: bool = False) -> None:
    table = sensitivity_cases() if sensitivity else case_table()
    total = 0.0
    for cid, c in table.items():
        sim, steps = simulated_seconds(c)
        wall = steps * cost_us * 1e-6
        total += wall
        print(f"{cid:28s} {c['kind']:10s} sim {sim:7.1f} s  steps {steps:10.0f}  "
              f"wall ~{wall / 60:6.1f} min  {','.join(c['V'])}")
    print(f"{len(table)} cases, serial ~{total / 60:.1f} min at {cost_us:.0f} us/step; "
          f"{MAX_JOBS} workers ~{total / 60 / MAX_JOBS:.1f} min (lower bound, longest case "
          f"{max(simulated_seconds(c)[1] for c in table.values()) * cost_us * 1e-6 / 60:.1f} min)")


def action_smoke(level: str, settle_s: float, out_dir: Path) -> dict[str, Any]:
    import numpy as np

    from outrigger_sim.chrono.l2b_model import pad_force_crosscheck
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    params = _params(level)
    model = _model(params)
    series = _Series()
    t0 = time.perf_counter()
    r = _run(model, settle_s, series, every=1)
    cross = pad_force_crosscheck(model)
    window = round(0.1 / model.dt_s)
    last = _Series()
    last.rows = {k: v[-window:] for k, v in series.rows.items()}
    stats = _window_stats(last, window)
    n_all = np.asarray(series.rows["pad_normal_N"])
    f_all = np.asarray(series.rows["cylinder_force_N"])
    crawler = np.asarray(series.rows["crawler_normal_N"])
    w_total = (params.superstructure.mass_properties.mass_kg
               + sum(leg.moving_part.mass_kg for leg in params.legs)) * params.meta.gravity_m_s2
    sum_window = float(np.mean(n_all[-window:].sum(axis=1) + crawler[-window:]))
    out = {
        "level": level, "settle_s": settle_s, "dt_s": model.dt_s, "placement": placement,
        "steps": r["steps"], "wall_s": r["wall_s"],
        "us_per_step_incl_record": r["wall_s"] / r["steps"] * 1e6,
        "nonfinite": int(np.count_nonzero(~np.isfinite(n_all)) + np.count_nonzero(
            ~np.isfinite(f_all))),
        "weight_N": w_total,
        "pads_plus_crawler_last_0p1s_mean_N": sum_window,
        "sum_rel_error": (sum_window - w_total) / w_total,
        "last_0p1s": stats,
        "crosscheck_last_step": cross,
        "start_forces_N": model.start_forces_N.tolist(),
        "rod_side_mode": model.actuator.rod_side.mode(),
        "max_abs_motor_drift_m": float(np.abs(np.asarray(series.rows["motor_pos_m"])[-1]
                                              - np.asarray(model.extensions_m)).max()),
        "roll_pitch_drift_deg": (np.asarray(series.rows["roll_pitch_deg"])[-1]
                                 - np.asarray(series.rows["roll_pitch_deg"])[0]).tolist(),
        "build_to_end_wall_s": time.perf_counter() - t0,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"smoke_{level}.json").write_text(json.dumps(out, indent=1, default=float),
                                                 encoding="utf-8")
    return out


def action_cost(seconds: float, out_dir: Path) -> dict[str, Any]:
    """Pure step cost (no recording), P-core pinned, EcoQoS off; pads (static start) and
    crawler (legs hanging at 0) at 1e-4 s, pads at 1e-5 s."""
    from outrigger_sim.chrono.bodies import BodyPose
    from outrigger_sim.hostcpu import place_process

    placement = place_process("pcore")
    params = _params("top")
    rows = []
    for label, kw, dt in (
        ("pads_static_1e-4", {}, 1e-4),
        ("pads_static_1e-5", {}, 1e-5),
        ("crawler_legs0_1e-4", {"pose": BodyPose((0.0, 0.0, 0.0)), "extensions_m": (0.0,) * 4,
                                "start": "hanging"}, 1e-4),
    ):
        model = _model(params, dt_s=dt, **kw)
        n_warm = round(0.05 / dt)
        for _ in range(n_warm):
            model.step()
        n = round(min(seconds, 0.5 if dt < 1e-4 else seconds) / dt)
        t0 = time.perf_counter()
        for _ in range(n):
            model.step()
        wall = time.perf_counter() - t0
        t1 = time.perf_counter()
        for _ in range(min(n, 2000)):
            model.step(capture=True)
        cap_us = (time.perf_counter() - t1) / min(n, 2000) * 1e6
        rows.append({"case": label, "dt_s": dt, "steps": n, "wall_s": wall,
                     "us_per_step": wall / n * 1e6, "us_per_step_with_capture": cap_us,
                     "n_contacts": int(model.system.GetNumContacts())})
    out = {"placement": placement, "rows": rows,
           "date": _dt.datetime.now().isoformat(timespec="seconds"),
           "note": "single process, run alone (no other Chrono job); hook + force law + "
                   "lateral bushing + rod-side law included"}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "step_cost_S7.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def action_batch(ids: list[str] | None, jobs: int, cap_s: float | None, out: Path) -> None:
    from outrigger_sim.batch import Case, run_cases

    if jobs > MAX_JOBS:
        raise SystemExit(f"--jobs {jobs} > {MAX_JOBS} (one P-core stays free)")
    table = case_table()
    chosen = ids or list(table)  # default: the V0-V14 table only (sensitivity cases by --only)
    table.update(sensitivity_cases())
    unknown = [c for c in chosen if c not in table]
    if unknown:
        raise SystemExit(f"unknown case ids {unknown}")
    cases = [Case(cid, {**table[cid], **({"cap_s": cap_s} if cap_s else {})}) for cid in chosen]
    # longest first
    cases.sort(key=lambda c: -simulated_seconds(dict(c.settings))[1] if cap_s is None else 0)
    report = run_cases(cases, job, out, max_workers=jobs, placement="pcore",
                       timeout_s=None if cap_s is None else 900.0)
    for o in report.outcomes:
        print(f"{o.case_id:28s} {o.status}  {o.wall_s:8.1f} s  {(o.error or '')[:200]}")
    print("batch:", out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=("list", "smoke", "cost", "check", "run"))
    ap.add_argument("--level", default="top")
    ap.add_argument("--settle", type=float, default=10.0)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--jobs", type=int, default=MAX_JOBS)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--approved", action="store_true",
                    help="user approved the S7 main run (required for 'run')")
    ap.add_argument("--cost-us", type=float, default=None,
                    help="step cost for 'list' (default: 06_analysis/01_chrono/17_S7/"
                         "step_cost_S7.json pads 1e-4 row, else 300)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sensitivity", action="store_true",
                    help="'list': show the V9 (b) sensitivity cases instead of the V0-V14 table")
    args = ap.parse_args(argv)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.action == "list":
        cost = args.cost_us
        if cost is None:
            f = ANALYSIS_DIR / "step_cost_S7.json"
            cost = (json.loads(f.read_text(encoding="utf-8"))["rows"][0]["us_per_step"]
                    if f.exists() else 300.0)
        action_list(cost, args.sensitivity)
    elif args.action == "smoke":
        print(json.dumps(action_smoke(args.level, args.settle, args.out or ANALYSIS_DIR),
                         indent=1, default=float))
    elif args.action == "cost":
        print(json.dumps(action_cost(args.seconds, args.out or ANALYSIS_DIR), indent=1))
    elif args.action == "check":
        action_batch(args.only, args.jobs, 0.3, args.out or RESULTS / f"check_{stamp}")
    else:
        if not args.approved:
            raise SystemExit("S7 main run needs --approved (tell the user first)")
        action_batch(args.only, args.jobs, None, args.out or RESULTS / f"run_{stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
