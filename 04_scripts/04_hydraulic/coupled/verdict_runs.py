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

from harness_flow import (  # noqa: E402
    CommandClipRecord,
    FlowSetting,
    install_command_clip,
    make_flow_plant_class,
)
from params import load_params  # noqa: E402
from verdict_cases import REANCHOR_ON, EventTwin, SteadyTwin, VerdictCase  # noqa: E402
from verdict_metrics import run_values  # noqa: E402

READY_DELAY_S = 5.0
SKIPPED_EVENT_PREFIXES = ("INFO_PRESSURE", "shadow", "INFO_D1")
RUN_180S_LIMIT_S = 180.0
RUN_180S_HOLD_S = 1.0e9
"""``S6=run_180s``: the run ends at 180 s, whatever the READY time."""
SS_EVENT = {"depth": 0.0115, "ramp": 20.0}
SLOW_EVENT_TAIL_S = 3.0
"""Slow event branch: at least to ramp end + 3 s (study A rule, ``s9_soil_event_screen``)."""

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
        """Project C2 and a list of (t, phase, command, integrals, filtered attitude, guard)."""

        def update(self, measurements):
            output = super().update(measurements)
            state = self._state
            log = self.__dict__.setdefault("period_log", [])
            log.append((float(measurements.t_s), str(self.phase),
                        np.array(output.leg_speed_m_s, float),
                        (state.roll_integral, state.pitch_integral),
                        tuple(self.filtered_attitude_rad),
                        state.guard_m_s is not None and bool(np.any(state.guard_m_s != 0.0))))
            return output

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
            "guard": np.array([row[5] for row in log], bool)}


def _stored_events(controller) -> list[tuple[float, str]]:
    return [(float(event.t_s), event.name) for event in controller.events
            if not event.name.startswith(SKIPPED_EVENT_PREFIXES)]


def _finish(plant, controller, extra: dict) -> tuple[dict, dict]:
    """Result dict and the 10 Hz arrays saved with it."""
    limiter = plant.flow_limiter
    period = period_arrays(controller)
    events = _stored_events(controller)
    thresholds = controller.config.thresholds
    values = run_values(limiter.rows(), period, events, limiter,
                        controller.geometry.twist_vector, controller.geometry.head_area_m2,
                        thresholds.integrator_limit_rad_s)
    result = {**extra, "commands_sha256": _command_digest(period["command"]),
              "final_phase": str(controller.phase),
              "max_motor_stroke_reading_mm": limiter.max_stroke_reading_m * 1e3,
              "values": values, "events": [(round(t, 3), name) for t, name in events][:400]}
    series = {"t": period["t"], "phase": period["phase"].astype(str),
              "command": period["command"], "integral": period["integral"],
              "filtered_deg": period["filtered_deg"]}
    return result, series


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


def _run_steady(case: VerdictCase, decision: str | None) -> tuple[dict, dict]:
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
    finished, series = _finish(captured["plant"], captured["ctrl"], extra)
    finished["harness_commands_sha256"] = result["run"]["commands_sha256"]
    return finished, series


# -------------------------------------------------------------------------------- event cases
def _run_event(twin: EventTwin) -> tuple[dict, dict]:
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
    plant, controller, _ = r67.make_base(cl, c2, twin.level, twin.fs_kN)
    timeline = r67.run_base(cl, c2, measurements, copy.deepcopy(plant), copy.deepcopy(controller))
    target = _event_time(timeline, twin)
    extra = {"harness_class": None, "timeline": {key: timeline[key] for key in
                                                 ("t_lift", "t_loc", "t_done", "t_ready")}}
    if target is None:  # the base run has no event time: report what it did
        base_plant, base_controller = plant, controller
        r67.run_base(cl, c2, measurements, base_plant, base_controller)
        extra["event_skipped"] = "base run without the READY / LOC / DONE of the event time"
        return _finish(base_plant, base_controller, extra)
    hasher = hashlib.sha256()
    state = r67.run_base(cl, c2, measurements, plant, controller, stop_t=target - r67.PRE_S,
                         hasher=hasher)
    t_event = plant.t + r67.PRE_S + twin.offset_s
    attitude_before = np.degrees(plant.attitude())
    rows, phases, events, crawler, t_ready_back, controller = r67.branch(
        cl, measurements, plant, controller, state["cmd"].copy(), state["valve"].copy(), event,
        leg, t_event, hasher=hasher)
    judged = r67.judge_event(rows, phases, events, crawler, t_event, t_ready_back, event, leg,
                             controller, attitude_before)
    window_end = judged["W_end_s"] if r67.is_fast(event) else event["ramp"] + SLOW_EVENT_TAIL_S
    judged["pressure"] = study_a._pressure_rows(rows[:, 0] - t_event, rows[:, 5:9], rows[:, 9:13],
                                                controller.geometry.head_area_m2, window_end)
    phase_at_event = next((phase for t, phase in phases if t >= 0.0), None)
    extra.update(event=twin.event, leg=twin.leg, timing=twin.timing, offset_s=twin.offset_s,
                 t_event_s=round(t_event, 3), phase_at_event=phase_at_event,
                 event_output=judged)
    finished, series = _finish(plant, controller, extra)
    finished["harness_commands_sha256"] = hasher.hexdigest()
    return finished, series


def _event_time(timeline: dict, twin: EventTwin) -> float | None:
    if timeline["t_ready"] is None:
        return None
    if twin.timing == "ready":
        return timeline["t_ready"] + READY_DELAY_S
    if timeline["t_loc"] is None or timeline["t_done"] is None:
        return None
    return timeline["t_loc"] + 0.5 * (timeline["t_done"] - timeline["t_loc"])


# ---------------------------------------------------------------------------------- public API
def execute(case: VerdictCase, setting: FlowSetting, decision: str | None,
            clip_command: bool = False) -> tuple[dict, dict]:
    """Run one case with one flow setting in this process.

    Args:
        case: The evaluation case, its decision applied.
        setting: Pump and compensator values.
        decision: The ``--decide`` choice of the case.
        clip_command: Clip the leg command to +-v_max before the valve path. It stays in force for
            the rest of the process, so a worker runs one such case.

    Returns:
        The result dict (``error`` set on a harness failure) and the 10 Hz arrays. The logged
        commands are the controller's, before the clip.
    """
    install_flow_plant(setting)
    install_logged_controller()
    clip_record = install_harness_command_clip() if clip_command else None
    if isinstance(case.twin, EventTwin):
        result, series = _run_event(case.twin)
    else:
        result, series = _run_steady(case, decision)
    if clip_record is not None:
        result["command_clip"] = asdict(clip_record)
    return result, series


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
