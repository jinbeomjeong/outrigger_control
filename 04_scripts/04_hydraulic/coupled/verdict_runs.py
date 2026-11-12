"""One coupling-verdict run on the reduced harness (imported harness paths, nothing copied).

Steady cases go through ``s9_soil_slope.run_one`` (the P3 rows), event cases through the
``r67_g1_screen`` functions with one branch instead of the six of its ``screen_job``. The flow
limit enters by replacing ``s8_g4_rodside_check.make_plant_class`` in this worker process, and
the 10 Hz controller log by subclassing ``c2.C2Controller``; neither changes a harness file.
With the limit off the command hash must equal the stored harness hash
(``aggregate_verdict.py`` checks it).
"""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
SETTLE_TABLE_PATH = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
SETTLE_TABLE_KEY = "hook_harness"
for _path in (HERE, S9_DIR, ROOT / "04_scripts" / "01_dynamics"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from harness_flow import COLUMN as FLOW_COLUMN  # noqa: E402
from harness_flow import (  # noqa: E402
    OIL_FORCE,
    CommandClipRecord,
    FlowSetting,
    install_command_clip,
    make_flow_plant_class,
)
from lock_window_alignment import PlantLockHistory, lock_window_alignment  # noqa: E402
from params import load_params  # noqa: E402
from verdict_cases import REANCHOR_ON, EventTwin, SteadyTwin, VerdictCase  # noqa: E402
from verdict_metrics import (  # noqa: E402
    after_window_force_values,
    chunk_phases,
    flow_saturation_time,
    hold_period_values,
    lower_bound_miss_values,
    overlap_in_window,
    ref_10hz_episode_values,
    run_values,
    stop_crawler_values,
    u9_values,
)

READY_DELAY_S = 5.0
FLOW_SATURATION_TIMING = "flow_saturation"
"""v5 criteria 13.3 (③, X-4): the event at an absolute reference time t_a (``event_time_s``)."""
CONTROL_PERIOD_S = 0.1
SKIPPED_EVENT_PREFIXES = ("INFO_PRESSURE", "shadow", "INFO_D1")
RUN_180S_LIMIT_S = 180.0
RUN_180S_HOLD_S = 1.0e9
"""``S6=run_180s``: the run ends at 180 s, whatever the READY time."""
SS_EVENT = {"depth": 0.0115, "ramp": 20.0}
T4H_TIME_TOL_S = 1e-9
SLOW_EVENT_TAIL_S = 3.0
"""Slow event branch: at least to ramp end + 3 s (study A rule, ``s9_soil_event_screen``)."""

HEAD_ONLY_DECLARED_KEY = "head_only_declared"
"""Criteria revision 9 3.1 declaration (result line and T4h meta): True = the run was set up
without rod-side readings (steady path, readings ``head``); record only, the commands do not
change."""

LOGGED_READINGS = ("applied_output_m_s", "head_pressure_Pa", "rod_pressure_Pa",
                   "motor_stroke_m", "seal_band_N")
"""Per-period arrays of ``LoggedController._logged_readings`` (v5 X-10), in that order."""

_ORIGINALS: dict = {}


def install_flow_plant(setting: FlowSetting) -> None:
    """Every plant built from now on in this process carries ``setting``."""
    import s8_g4_rodside_check as rodside
    import s9_soil_closed_loop  # noqa: F401  (puts the harness folders on sys.path)

    original = _ORIGINALS.setdefault("make_plant_class", rodside.make_plant_class)

    def make_plant_class_with_flow(cl):
        return make_flow_plant_class(original(cl), setting)

    rodside.make_plant_class = make_plant_class_with_flow


def install_logged_controller():
    """``c2.C2Controller`` with a record-only log of every period; returns the c2 module."""
    from outrigger_sim.control import c2

    base = _ORIGINALS.setdefault("controller", c2.C2Controller)

    class LoggedController(base):
        """Project C2 and a list of (t, phase, command, integrals, filtered attitude, guard,
        lower load estimate, readings); readings = (applied output, head and rod pressure
        readings, motor stroke reading, seal band after the update), record only (X-10)."""

        def update(self, measurements):
            output = super().update(measurements)
            state = self._state
            log = self.__dict__.setdefault("period_log", [])
            log.append((float(measurements.t_s), str(self.phase),
                        np.array(output.leg_speed_m_s, float),
                        (state.roll_integral, state.pitch_integral),
                        tuple(self.filtered_attitude_rad),
                        state.guard_m_s is not None and bool(np.any(state.guard_m_s != 0.0)),
                        self._logged_lower_estimate_N(), self._logged_readings(measurements)))
            return output

        def _logged_readings(self, measurements) -> tuple:
            rod_Pa = measurements.rod_pressure_Pa
            return (np.array(self._state.applied_output_m_s, float),
                    np.array(measurements.head_pressure_Pa, float),
                    np.full(4, np.nan) if rod_Pa is None else np.array(rod_Pa, float),
                    np.array(measurements.stroke_m, float),
                    np.array(self._leg_seal_bands_N(), float))

        def _logged_lower_estimate_N(self) -> np.ndarray:
            """The lower load estimate the judge compares with F_min (v5 X-6, record only)."""
            forces = self._state.last_forces
            if forces is None:
                return np.full(4, np.nan)
            return np.array(self._load_estimate_N(forces.lower), float)

    c2.C2Controller = LoggedController
    return c2


def install_harness_command_clip() -> CommandClipRecord:
    """Commands of this process are clipped to the YAML v_max before the valve path."""
    import s9_soil_closed_loop as soil

    closed_loop = soil._imports()[0]
    return install_command_clip(closed_loop, load_params().v_max)


def period_arrays(controller) -> dict:
    """The controller log as arrays."""
    log = controller.__dict__.get("period_log", [])
    return {"t": np.array([row[0] for row in log], float),
            "phase": np.array([row[1] for row in log], dtype=object),
            "command": np.array([row[2] for row in log], float).reshape(-1, 4),
            "integral": np.array([row[3] for row in log], float).reshape(-1, 2),
            "filtered_deg": np.degrees(np.array([row[4] for row in log], float).reshape(-1, 2)),
            "guard": np.array([row[5] for row in log], bool),
            "lower_estimate_N": np.array([row[6] for row in log], float).reshape(-1, 4),
            **{name: np.array([row[7][index] for row in log], float).reshape(-1, 4)
               for index, name in enumerate(LOGGED_READINGS)}}


def _stored_events(controller) -> list[tuple[float, str]]:
    return [(float(event.t_s), event.name) for event in controller.events
            if not event.name.startswith(SKIPPED_EVENT_PREFIXES)]


def _finish(plant, controller, extra: dict, t4h: dict | None = None, *,
            u9_metrics: bool = False) -> tuple[dict, dict]:
    """Result dict and the 10 Hz arrays saved with it; ``t4h`` = {"path", "meta"} also writes
    the T4h record (v5 X-10); ``u9_metrics`` adds ``values["U9"]`` (U-9 targeted runs)."""
    limiter = plant.flow_limiter
    period = period_arrays(controller)
    events = _stored_events(controller)
    _LAST_FINISHED_CONFIG[0] = getattr(controller, "config", None)  # plant_options_record tag
    # v5 X-10 (criteria J11): only plants with the v5 lock record (LC) have lock_events
    if getattr(plant, "lock_events", None) is not None:
        extra = {**extra, "lock_window_alignment": lock_window_record(
            plant, controller, period)}
        if t4h is not None:
            write_t4h_record(t4h["path"], plant, controller, period,
                             {**_meta_with_controller_tag(t4h["meta"], _LAST_FINISHED_CONFIG[0]),
                              "commands_sha256": _command_digest(period["command"])})
    thresholds = controller.config.thresholds
    values = run_values(limiter.rows(), period, events, limiter,
                        controller.geometry.twist_vector, controller.geometry.head_area_m2,
                        thresholds.integrator_limit_rad_s)
    if u9_metrics:  # u9_targeted_rules_rev1.md 3.2 P-3: only the jobs that ask for it
        rows = limiter.rows()
        values["U9"] = u9_values(rows, chunk_phases(rows, period["t"], period["phase"]), period,
                                 is_flow_on=limiter.setting.is_enabled)
    result = {**extra, "commands_sha256": _command_digest(period["command"]),
              "final_phase": str(controller.phase),
              "max_motor_stroke_reading_mm": limiter.max_stroke_reading_m * 1e3,
              "values": values, "events": [(round(t, 3), name) for t, name in events][:400],
              "review_record": review_record_of(controller)}
    import resume_k1_record  # 436.8 rules 4.2 / 7.2: record only, after the run

    result[resume_k1_record.RECORD_KEY] = resume_k1_record.controller_record(controller)
    stop_values = _soil_stop_values(plant, limiter, events)
    if stop_values is not None:  # v5 X-12, criteria 6: runs with a soil-guard stop only
        result["soil_stop_crawler"] = stop_values
    series = {"t": period["t"], "phase": period["phase"].astype(str),
              "command": period["command"], "integral": period["integral"],
              "filtered_deg": period["filtered_deg"]}
    return result, series


_LAST_FINISHED_CONFIG: list = [None]
"""C2 config of the last :func:`_finish` of this process (one run per worker process)."""


def _meta_with_controller_tag(meta: dict, config) -> dict:
    """T4h meta whose ``controller_tag`` names the switches of the run's controller (LAS-b
    ``_LAS``, K1 order gate ``_K1``; the request meta is built before the run, from the options
    only); unchanged with both off."""
    from outrigger_sim.hydraulics.v5_options import with_switch_tags

    tag = with_switch_tags(meta.get("controller_tag"), config)
    if tag == meta.get("controller_tag"):
        return meta
    return {**meta, "controller_tag": tag}


def review_record_of(controller) -> dict | None:
    """Criteria rev. 6 14.5 records of the run (``two_pressure.review_record``: tension
    sub-steps and D2 violation-start ratios; record only, not a judged value)."""
    return meta_for_json(controller.meta()["two_pressure"].get("review_record"))


def _all_events(controller) -> list[tuple[float, str]]:
    return [(float(event.t_s), event.name) for event in controller.events]


def lock_window_record(plant, controller, period: dict) -> dict:
    """Criteria J11 n_late of the run (``lock_window_alignment``; control-expert A).

    ``period`` needs ``t`` (update times) and ``applied_output_m_s`` (after each update), as
    :func:`period_arrays`; shared with ``r79_sensor_screen``."""
    t_s = period["t"]
    return lock_window_alignment(
        t_s, period["applied_output_m_s"], plant.lock_events,
        controller.meta()["two_pressure"], controller.config.period_s,
        _all_events(controller), float(t_s[-1]) if t_s.size else 0.0)


def _true_force_at_samples(rows: np.ndarray, t_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """T4h truth from the 1 ms limiter rows: ``oil_force`` of the row at t_k (NaN if none) and
    its minimum over (t_k-1, t_k] (the first sample: up to t_0)."""
    row_t = rows[:, FLOW_COLUMN["t"]]
    oil = rows[:, OIL_FORCE]
    at_sample = np.full((len(t_s), 4), np.nan)
    window_min = np.full((len(t_s), 4), np.nan)
    index = np.searchsorted(row_t, t_s - T4H_TIME_TOL_S, side="left")
    starts = np.r_[-np.inf, t_s[:-1]]
    first = np.searchsorted(row_t, starts + T4H_TIME_TOL_S, side="left")
    last = np.searchsorted(row_t, t_s + T4H_TIME_TOL_S, side="right")
    for k in range(len(t_s)):
        if index[k] < len(row_t) and abs(row_t[index[k]] - t_s[k]) <= T4H_TIME_TOL_S:
            at_sample[k] = oil[index[k]]
        if last[k] > first[k]:
            window_min[k] = oil[first[k]:last[k]].min(axis=0)
    return at_sample, window_min


def write_t4h_record(path, plant, controller, period: dict, meta: dict,
                     extra_arrays: dict | None = None) -> None:
    """T4h record of one run (control-expert B): 10 Hz controller inputs and outputs from the
    arm to the end, the 1 ms truth taken at the samples, the plant lock state and events.
    ``extra_arrays`` are saved beside them (the r79 Dg-3 record adds the run's own lower
    readings, ``r79_sensor_screen`` ``R79_T4H_DIR``)."""
    import json

    t_s = period["t"]
    true_force, true_force_min = _true_force_at_samples(plant.flow_limiter.rows(), t_s)
    history = PlantLockHistory(plant.lock_events)
    locked = np.array([[history.is_locked_at(leg, float(t)) for leg in range(4)] for t in t_s],
                      bool).reshape(-1, 4)
    controller_meta = controller.meta()
    monitor = controller_meta["two_pressure"]
    full_meta = {**meta, "zero_offset_N": monitor.get("zero_offsets_N"),
                 **offset_allowance_record(controller_meta),
                 "two_pressure_settings": monitor.get("settings"),
                 "F_min_N": float(controller.geometry.F_min_N),
                 "period_s": controller.config.period_s,
                 "events": _all_events(controller),
                 # premise ① truth of the ③ bound (tension_premise.md S-2), record only
                 "tension_truth": (None if getattr(plant, "tension_truth", None) is None
                                   else plant.tension_truth.record()),
                 # the ③ bound against the plant at the reads (5.5; None = option off)
                 "extend_bound_check": (
                     None if getattr(plant, "extend_bound_check", None) is None
                     else plant.extend_bound_check.record()),
                 "true_force_rule": "limiter oil_force at the 1 ms row t == t_k (NaN without "
                                    "one) and its minimum over (t_k-1, t_k]; not true_force_*"}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path, t_s=t_s, head_pressure_Pa=period["head_pressure_Pa"],
        rod_pressure_Pa=period["rod_pressure_Pa"], motor_stroke_m=period["motor_stroke_m"],
        command_m_s=period["command"], phase=period["phase"].astype(str),
        seal_band_N=period["seal_band_N"], true_force_N=true_force,
        true_force_min_N=true_force_min, locked=locked,
        lock_events=np.array(plant.lock_events, float).reshape(-1, 3),
        meta_json=np.array(json.dumps(meta_for_json(full_meta))), **(extra_arrays or {}))


def offset_allowance_record(controller_meta: dict) -> dict:
    """E-6 pressure-zero allowance of a run, record only (user decision 2026-11-08).

    ``pressure_offset_allowance_N``: the per-leg lower-bound deduction the monitor holds at the
    end of the run (``zero_calibration.pressure_offset_allowance_N``);
    ``pressure_offset_allowance_from_s``: the update that set it, i.e. the end of the zero
    calibration (``zero_calibration.result.t_end_s``; None without a calibration). The
    deduction acts on the reads after that update (``contact_replay.replay_fallback_monitor``
    ``offset_allowance_from_s``). Read from the controller meta after the run, so the commands
    do not change.
    """
    calibration = controller_meta.get("zero_calibration") or {}
    allowance = calibration.get("pressure_offset_allowance_N")
    return {"pressure_offset_allowance_N": None if allowance is None else list(allowance),
            "pressure_offset_allowance_from_s": (calibration.get("result") or {}).get("t_end_s")}


def meta_for_json(value):
    """Plain JSON values (numpy scalars and arrays, tuples, enums as strings)."""
    if isinstance(value, dict):
        return {str(key): meta_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [meta_for_json(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _soil_stop_values(plant, limiter, events: list[tuple[float, str]]) -> dict | None:
    """Criteria 6 (S8 F-5) crawler values around the soil-guard stop; None without a stop."""
    import soil_guard_stop_rule

    stop_t_s = soil_guard_stop_rule.soil_stop_time_s(events)
    if stop_t_s is None:
        return None
    return stop_crawler_values(limiter.rows(), stop_t_s, float(plant.m * plant.g))


def _command_digest(commands: np.ndarray) -> str:
    """SHA-256 over the commands in order (the harness hashes the same bytes period by period)."""
    return hashlib.sha256(commands.tobytes()).hexdigest()


# ------------------------------------------------------------------------------- steady cases
def _steady_case_dict(twin: SteadyTwin, slope, is_reanchor: bool) -> dict:
    """The ``run_one`` input of a stored id: a table row for H* ids, the p0 settle for base ids."""
    if twin.stored_id.startswith("base|"):
        case = slope.SlopeCase("base", twin.soil, twin.pad, twin.level, "stored", twin.roll_deg,
                               twin.pitch_deg, fs_kN=twin.fs_kN, reanchor=is_reanchor)
        return case.to_dict()
    import json

    group = twin.stored_id.split("|")[0]
    table = json.loads(SETTLE_TABLE_PATH.read_text(encoding="utf-8"))[SETTLE_TABLE_KEY]
    groups = (group,) if group in ("H6", slope.H9_GROUP) else ("H1", "H3")
    cases = [c for c in slope.attach_settle_table(slope.build_cases(groups), table)
             if c.case_id == twin.stored_id]
    if len(cases) != 1:
        raise ValueError(f"stored id {twin.stored_id!r} matches {len(cases)} cases")
    return replace(cases[0], reanchor=is_reanchor).to_dict()


def _run_steady(case: VerdictCase, decision: str | None, t4h: dict | None = None, *,
                u9_metrics: bool = False) -> tuple[dict, dict]:
    import s9_soil_closed_loop as sl
    import s9_soil_slope as slope

    if decision == "run_180s":
        sl.RUN_LIMIT_S, sl.HOLD_AFTER_READY_S = RUN_180S_LIMIT_S, RUN_180S_HOLD_S
    payload = _steady_case_dict(case.twin, slope, decision == REANCHOR_ON)
    result = slope.run_one(payload)
    if "error" in result:
        return {"error": result["error"], "tb": result.get("tb")}, {}
    captured = slope._CAP
    extra = {"harness_class": result["verdict"], "failed_rows": result["failed_rows"],
             "rows": result["rows"], "run": result["run"], "warnings": result["warnings"],
             "rut_ready_mm": result["rut_ready_mm"], "rut_end_mm": result["rut_end_mm"],
             "moving_pressure": captured["moving_pressure"].to_dict(),
             "probe_rounds": result["probe_rounds"]}
    if result["run"].get("commands_sha256") is None:
        raise RuntimeError("harness run without a command hash")
    finished, series = _finish(captured["plant"], captured["ctrl"], extra, t4h,
                               u9_metrics=u9_metrics)
    finished["harness_commands_sha256"] = result["run"]["commands_sha256"]
    return finished, series


# -------------------------------------------------------------------------------- event cases
def _run_event(twin: EventTwin, contact: str | None = None, t4h: dict | None = None, *,
               u9_metrics: bool = False) -> tuple[dict, dict]:
    import copy

    import s9_soil_event_screen as study_a

    modules = study_a._s8_modules()
    r51, r67 = modules["r51"], modules["r67"]
    r51.place_worker()
    cl, c2, measurements = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    leg = r67.LEGS.index(twin.leg)
    event = SS_EVENT if twin.event == "SS" else r67.EVENTS[twin.event]
    r67.MIN_AFTER_S = max(r67.MIN_AFTER_S, event["ramp"] + SLOW_EVENT_TAIL_S)
    judge = None if contact is None else c2.ContactJudge[contact]
    plant, controller, _ = r67.make_base(cl, c2, twin.level, twin.fs_kN, contact=judge)
    timeline = r67.run_base(cl, c2, measurements, copy.deepcopy(plant), copy.deepcopy(controller))
    target = _event_time(timeline, twin)
    extra = {"harness_class": None, "timeline": {key: timeline[key] for key in
                                                 ("t_lift", "t_loc", "t_done", "t_ready")}}
    if target is None:  # the base run has no event time: report what it did
        base_plant, base_controller = plant, controller
        r67.run_base(cl, c2, measurements, base_plant, base_controller)
        extra["event_skipped"] = "base run without the READY / LOC / DONE of the event time"
        return _finish(base_plant, base_controller, extra, t4h, u9_metrics=u9_metrics)
    hasher = hashlib.sha256()
    is_absolute = twin.timing == FLOW_SATURATION_TIMING
    # absolute t_a: branch one control period early so that t_a + offset is exact (>= PRE_S
    # after the branch); the other timings keep the branch-relative event time
    stop_t = target - r67.PRE_S - (CONTROL_PERIOD_S if is_absolute else 0.0)
    state = r67.run_base(cl, c2, measurements, plant, controller, stop_t=stop_t, hasher=hasher)
    t_event = (target if is_absolute else plant.t + r67.PRE_S) + twin.offset_s
    attitude_before = np.degrees(plant.attitude())
    rows, phases, events, crawler, t_ready_back, controller = r67.branch(
        cl, measurements, plant, controller, state["cmd"].copy(), state["valve"].copy(), event,
        leg, t_event, hasher=hasher)
    judged = r67.judge_event(rows, phases, events, crawler, t_event, t_ready_back, event, leg,
                             controller, attitude_before)
    window_end = judged["W_end_s"] if r67.is_fast(event) else event["ramp"] + SLOW_EVENT_TAIL_S
    judged["pressure"] = study_a._pressure_rows(rows[:, 0] - t_event, rows[:, 5:9], rows[:, 9:13],
                                                controller.geometry.head_area_m2, window_end)
    # v5 X-8 (criteria 3.1, ⑦): 1 ms minimum, trailing 0.5 s mean and lift after the window
    judged["after_window_force"] = after_window_force_values(
        rows[:, 0] - t_event, rows[:, 5:9], rows[:, 1:5], window_end, r67.F_MIN_N)
    # v5 X-6 (criteria 13.4, ⑥): misses of the run's judge, lower estimate held on the 1 ms rows,
    # and the Chrono-style 10 Hz reference value (control-expert definition C, not judged)
    period = period_arrays(controller)
    lower_held = hold_period_values(rows[:, 0], period["t"], period["lower_estimate_N"])
    judged["lower_bound_miss"] = lower_bound_miss_values(
        rows[:, 0] - t_event, rows[:, 5:9], lower_held, window_end, r67.F_MIN_N)
    judged["ref_10hz_episodes"] = ref_10hz_episode_values(
        rows[:, 0] - t_event, rows[:, 1:5], rows[:, 5:9], period["t"] - t_event,
        period["lower_estimate_N"], window_end, r67.F_MIN_N, controller.config.contact.name)
    phase_at_event = next((phase for t, phase in phases if t >= 0.0), None)
    extra.update(event=twin.event, leg=twin.leg, timing=twin.timing, offset_s=twin.offset_s,
                 t_event_s=round(t_event, 3), phase_at_event=phase_at_event,
                 contact_judge=controller.config.contact.name, event_output=judged)
    if is_absolute:  # criteria 13.3 record; the other timings keep their former result keys
        limiter = plant.flow_limiter
        extra["overlap_found"] = {
            **overlap_in_window(limiter.rows(), limiter.supply_m3_s, t_event,
                                t_event + window_end),
            "flow_limit_on": limiter.setting.is_enabled, "t_a_s": target}
    finished, series = _finish(plant, controller, extra, t4h, u9_metrics=u9_metrics)
    finished["harness_commands_sha256"] = hasher.hexdigest()
    return finished, series


def _event_time(timeline: dict, twin: EventTwin) -> float | None:
    if twin.timing == FLOW_SATURATION_TIMING:
        if twin.event_time_s is None:
            raise ValueError("timing flow_saturation needs the reference time event_time_s")
        return twin.event_time_s
    if timeline["t_ready"] is None:
        return None
    if twin.timing == "ready":
        return timeline["t_ready"] + READY_DELAY_S
    if timeline["t_loc"] is None or timeline["t_done"] is None:
        return None
    return timeline["t_loc"] + 0.5 * (timeline["t_done"] - timeline["t_loc"])


# ---------------------------------------------------------------------------------- public API
def execute(case: VerdictCase, setting: FlowSetting, decision: str | None,
            clip_command: bool = False, hydraulics=None,
            contact: str | None = None, t4h: dict | None = None,
            u9_metrics: bool = False) -> tuple[dict, dict]:
    """Run one case with one flow setting in this process.

    Args:
        case: The evaluation case, its decision applied.
        setting: Pump and compensator values.
        decision: The ``--decide`` choice of the case.
        clip_command: Clip the leg command to +-v_max before the valve path. It stays in force for
            the rest of the process, so a worker runs one such case.
        hydraulics: v5 plant options (``HydraulicOptions``, spec v5 2.0); None or all off = the
            plant of this module bit for bit. Also in force for the rest of the process.
        contact: ``c2.ContactJudge`` member name of an event case (v5 X-6, criteria 13.4:
            ``"PRESSURE"``), resolved on the harness' own c2 module; None = the screen's
            COMBINED judge, bit for bit.
        t4h: ``{"path": npz path, "meta": dict}``: write the T4h record (v5 X-10) of a run
            whose plant has the lock record (LC); None = no file.
        u9_metrics: Add ``values["U9"]`` (``verdict_metrics.u9_values``,
            ``u9_targeted_rules_rev1.md`` 3.3); False = the values as before. Record only:
            the commands do not change.

    Returns:
        The result dict (``error`` set on a harness failure) and the 10 Hz arrays. The logged
        commands are the controller's, before the clip.

    Raises:
        ValueError: ``contact`` given for a steady case (its judge comes from the P3 runner).
    """
    is_event = isinstance(case.twin, EventTwin)
    if contact is not None and not is_event:
        raise ValueError(f"{case.case_id}: the contact judge is an event-case option")
    install_plant_options(setting, hydraulics)
    install_logged_controller()
    clip_record = install_harness_command_clip() if clip_command else None
    # criteria revision 9 3.1: the steady path never gives the controller a rod reading
    is_head_only = not is_event
    if t4h is not None:
        t4h = {**t4h, "meta": {**t4h["meta"], HEAD_ONLY_DECLARED_KEY: is_head_only}}
    if is_event:
        result, series = _run_event(case.twin, contact, t4h, u9_metrics=u9_metrics)
    else:
        result, series = _run_steady(case, decision, t4h, u9_metrics=u9_metrics)
    if clip_record is not None:
        result["command_clip"] = asdict(clip_record)
    t_lift_s = ((result.get("values") or {}).get("forces") or {}).get("t_lift_s")
    result.update(plant_options_record(hydraulics, t_lift_s))
    result[HEAD_ONLY_DECLARED_KEY] = is_head_only
    return result, series


def flow_saturation_reference(case: VerdictCase, setting: FlowSetting,
                              hydraulics=None) -> dict:
    """Criteria 13.3 (③, X-4): t_a of the base run (no event) of an event case with this flow
    setting and these plant options (the VB reference run). In force for the rest of the
    process, like :func:`execute`.

    Raises:
        ValueError: ``case`` is not an event case.
    """
    if not isinstance(case.twin, EventTwin):
        raise ValueError(f"{case.case_id}: t_a needs an event case")
    install_plant_options(setting, hydraulics)
    install_logged_controller()
    import s9_soil_event_screen as study_a

    modules = study_a._s8_modules()
    r51, r67 = modules["r51"], modules["r67"]
    r51.place_worker()
    cl, c2, measurements = r51._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant, controller, _ = r67.make_base(cl, c2, case.twin.level, case.twin.fs_kN)
    timeline = r67.run_base(cl, c2, measurements, plant, controller)
    period = period_arrays(controller)
    limiter = plant.flow_limiter
    reference = flow_saturation_time(limiter.rows(), period["t"], period["phase"],
                                     limiter.supply_m3_s)
    return {**reference, "case": case.case_id, "flow_setting": setting.to_dict(),
            "hydraulic_options": None if hydraulics is None else hydraulics.to_dict(),
            "timeline": {key: timeline[key] for key in ("t_lift", "t_loc", "t_done", "t_ready")},
            "commands_sha256": _command_digest(period["command"])}


def install_plant_options(setting: FlowSetting, hydraulics=None) -> None:
    """Every plant built from now on in this process carries the flow setting and the v5 plant
    options (``HydraulicOptions``; None or all off = no v5 patch). Shared with the screen
    runners (``r67_g1_screen``, ``r69_g8_screen``, v5 X-3)."""
    if hydraulics is not None and hydraulics.is_any_on:
        import harness_hydraulics

        harness_hydraulics.install(sys.modules[__name__], hydraulics)
    install_flow_plant(setting)


def plant_options_record(hydraulics=None, t_lift_s: float | None = None) -> dict:
    """After a run: the criteria P-4 window check and the v5 record (empty without options).

    ``t_lift_s`` = the first crawler lift-off of the run (``values.forces.t_lift_s``): the M2
    clipped steps are split before / after it (criteria rev. 2 2.1; None = all after).

    The ``controller_tag`` follows the controller of the last :func:`_finish` of this process
    (LAS-b switch 2026-11-08: ``final_C4G2_LAS`` / ``final_C4G2_P3_LAS``; K1 switch:
    ``final_C4G2_LAS_K1`` / ``final_C4G2_P3_LAS_K1``; a run without options then gets only that
    key).

    Raises:
        RuntimeError: The lock window of the built preset differs from the options.
    """
    from outrigger_sim.hydraulics.v5_options import controller_tag

    config = _LAST_FINISHED_CONFIG[0]
    if hydraulics is None or not hydraulics.is_any_on:
        tag = controller_tag(None, config)
        return {} if tag is None else {"controller_tag": tag}
    import harness_hydraulics

    if hydraulics.lock_window_follows_plant:
        harness_hydraulics.check_last_lock_window(hydraulics, load_params().v_max)
    harness_hydraulics.check_last_extend_start(hydraulics)
    record = {"hydraulic_options": hydraulics.to_dict(),
              "hydraulics_record": harness_hydraulics.last_armed_record(t_lift_s)}
    tag = controller_tag(hydraulics, config)
    if tag is not None:  # criteria revision 8: key only with ③ (or LAS-b) on
        record["controller_tag"] = tag
    return record


def warm_numba_cache() -> None:
    """Load the numba kernels once before the spawn pool (the harness' numba cache lesson)."""
    import s9_soil_closed_loop as sl

    cl = sl._imports()[0]
    import s8_g4_rodside_check as rodside

    plant = rodside.make_plant_class(cl)("top", 0.0, 0.0, Fs=0.0)
    plant.step(np.zeros(4), 2)
    plant.arm()
    plant.step(np.zeros(4), 2)
    zeros = np.zeros(4)
    sl.soil_chunk(zeros, zeros.copy(), zeros.copy(), zeros.copy(), np.ones(4), np.ones(4), 1.0, 1.0,
                  1.0, np.ones(4), 1e-3, zeros.copy())
