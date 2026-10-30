"""Spec 426.3 (study A): reduced closed-loop screen of floor events on SOFT soil (the S8 event
judgement on the S9 soil harness).

Harness: ``s9_soil_closed_loop.py`` (imported, not copied): reduced 6-DoF FlexPlant, L1-R rod-side
law, Coulomb seal friction (rear 0.833 x), valve lag 0.1 s in 1 ms chunks, IMU 10 ms, one SCM
element per pad, settle hook "harness" (flat row ``<soil>|top|0|0``). Controller: the project C2 R8
preset ``preset_config(COMBINED)`` (03_src read only, plain ``C2Controller``, as r67 / r72).
Readings: head and rod pressure from the net oil force (``r64.with_two_pressures``, as r67) by
default; ``head`` = the S9 harness reading (identity tests, sensitivity).

Event model (spec 426.2 (가)): the soil reference surface under the event pad drops as a whole,
``SoilPads.h[i] = h0[i] - d P345(tau)`` (z, s_p, sigma_y untouched); on a rigid floor the kernel
floor offset ``goff[i] = d P345(tau)`` (as r67). ``goff`` cannot carry a soil event: ``soil_floor``
rewrites it every 1 ms chunk.

Branches (as r67): deepcopy 0.5 s before the event, run until the controller has been back in
READY for 3 s and at least 12 s after the event (and at least to the ramp end + 3 s, the slow
pressure window), at most 60 s.
  timing ready = READY + 5 s: G4 11.5 mm / 2 s, SS 11.5 mm / 20 s
  timing level = t_LOC + (t_DONE - t_LOC) / 2 of the same base run: G4, FS24 24 mm / 0.3 s,
                 RE1bF 30 mm / 0.05 s
Judgement per branch (1 ms record): r67 ``judge_event`` plus
  E-1 fast: lift sum per event leg (settled leg and its diagonal) <= 1.8 s and its last
      touch-down <= event + 3.0 s (pair union recorded); slow: no lift on any leg
  E-2 fast: U57 adjacent legs (r67); the U-S8-75 low-friction exception (F_s < 2 kN, lift outside
      W <= 0.1 s with gap <= 0.5 mm) passes with a FLAG
  E-3 F_min after W (fast) / after the event (slow), every leg, 1 ms true F_cyl
  E-4 pressure: in the event window (W; slow: event start to ramp end + 3 s) F_cyl / A_p <= 350
      bar per leg; outside it moving samples (|u| > 1e-6 m/s) <= 180 bar and no saturation
      (harness form: extending sample with F_cyl / A_p >= 210 bar)
  E-5 READY at the end, end attitude <= 0.2 deg, FAULT 0, run-maximum stroke <= 684.8 mm
  E-6 crawler (ASSUMPTION, new row): crawler contact after the event only inside W of a fast event
      (FLAG ``E-6_event_transient_recontact``), none outside W / after a slow event; at the end
      crawler load 0 and every crawler node >= 25 mm above the floor plane
  E-7 twist-work recurrence (r67)
Records: re-approach starts and sign changes, READY return, pad sink before / after the event and
the added sink, soil mode / LOC revocations / P-S8-35 events, warnings, command SHA-256.

Usage (dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I s9_soil_event_screen.py <project_root> <out_json> [workers]
  python -I s9_soil_event_screen.py <project_root> --list
Env: R426A_SET = main (12) | head (4) | j1 (4) | all (main + head, default, 16) | all_j1 (20);
  R426A_FILTER = comma list of job-key substrings; R426A_READINGS = two | head (overrides every
  selected job); R426A_AFFINITY = hex mask set on the parent (inherited by the workers).
Job key: ``A|<soil>|<leg>|Fs<f>|<readings>``. Units SI unless the key says otherwise.
"""

from __future__ import annotations

import contextlib
import copy
import ctypes
import hashlib
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_soil_closed_loop as sl  # noqa: E402

LEGS = sl.LEGS
SETTLE_HOOK = sl.SETTLE_HOOK_HARNESS
LEVEL = "top"
PAD = "B"
READINGS_TWO = "two"
READINGS_HEAD = "head"
READINGS = (READINGS_TWO, READINGS_HEAD)
EVENTS = {
    "G4": {"depth": 0.0115, "ramp": 2.0},
    "SS": {"depth": 0.0115, "ramp": 20.0},
    "FS24": {"depth": 0.024, "ramp": 0.3},
    "RE1bF": {"depth": 0.030, "ramp": 0.05},
}
"""Poly345 floor settlement of one pad: depth [m] over ramp [s]."""
TIMING_EVENTS = {"ready": ("G4", "SS"), "level": ("G4", "FS24", "RE1bF")}
READY_DELAY_S = 5.0
PRE_S = 0.5
"""Branch start before the event (the twist-work row needs D_0 over [-0.5, 0] s)."""
MIN_AFTER_S = 12.0
MAX_AFTER_S = 60.0
READY_HOLD_S = 3.0
SLOW_WINDOW_TAIL_S = 3.0
"""Slow-event pressure window: event start to ramp end + 3 s (spec 426.3 E-4)."""

MAIN_SOILS = ("G1", "J2", "rigid")
OPTIONAL_SOILS = ("J1",)
HEAD_SOILS = ("rigid",)
JOB_LEGS = ("FL", "RR")
JOB_FS_KN = (0.0, 8.0)

LIFT_SUM_MAX_S = 1.8
LAST_TOUCH_MAX_S = 3.0
LOW_FRICTION_FS_KN = 2.0
LOW_FRICTION_OUTSIDE_SUM_S = 0.1
LOW_FRICTION_OUTSIDE_GAP_MM = 0.5
LOW_FRICTION_FLAG = "U-S8-75 (b) exception"
WINDOW_MAX_BAR = 350.0
MOVING_MAX_BAR = 180.0
RELIEF_BAR = 210.0
MOVING_SPEED_EPS_M_S = 1e-6
STROKE_OK_MM = 684.8
CRAWLER_CLEAR_MIN_MM = 25.0
CRAWLER_RECONTACT_FLAG = "E-6_event_transient_recontact"
FAULT_PHASE = "fault"
FAULT_PHASES = ("fault", "fault_reground")
PA_PER_BAR = 1e5
CHUNK_S = 1e-3
ROW_COLUMNS = ("t", "contact_FL", "contact_FR", "contact_RL", "contact_RR", "Fcyl_FL", "Fcyl_FR",
               "Fcyl_RL", "Fcyl_RR", "valve_FL", "valve_FR", "valve_RL", "valve_RR", "gap_FL",
               "gap_FR", "gap_RL", "gap_RR", "roll_deg", "pitch_deg", "crawler_N")
"""1 ms row of ``control_period_rec`` (the r51 record layout plus the crawler force)."""
CRAWLER_COLUMN = ROW_COLUMNS.index("crawler_N")
RECORDED_INFO_PREFIXES = ("INFO_DIFF_SINK", "INFO_LOC", "soil_mode", "INFO_LIFT_PAUSED")
_S8_MODULES: dict = {}


# ------------------------------------------------------------------------------- data types
@dataclass(frozen=True)
class EventJob:
    """One base run of study A (both timings and their five branches)."""

    soil: str
    leg: str
    fs_kN: float
    readings: str = READINGS_TWO

    @property
    def key(self) -> str:
        return f"A|{self.soil}|{self.leg}|Fs{self.fs_kN:g}|{self.readings}"

    @classmethod
    def from_key(cls, key: str) -> EventJob:
        tag, soil, leg, fs, readings = key.split("|")
        if tag != "A" or leg not in LEGS or not fs.startswith("Fs") or readings not in READINGS:
            raise ValueError(f"not a study A job key: {key!r}")
        return cls(soil, leg, float(fs[2:]), readings)


@dataclass
class BranchResult:
    """State and 1 ms record of one event branch (input of :func:`judge_soil_event`)."""

    event_id: str
    event: dict | None
    leg: int
    t_ev: float
    att0_deg: np.ndarray
    rows: np.ndarray
    phases: list = field(default_factory=list)
    events: list = field(default_factory=list)
    t_ready_back: float | None = None
    commands_sha256: str = ""
    stroke_max_mm: float = 0.0
    sink_before_mm: list | None = None
    sink_end_mm: list | None = None
    crawler_clear_end_mm: float = float("nan")
    controller: object = None


# --------------------------------------------------------------------------- private helpers
@contextlib.contextmanager
def _argv_as_root():
    """The s8 screens read ``sys.argv[1]`` as the project root at import."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def _s8_modules():
    """r51 / r64 / r67 of the S8 harness, imported once (they read ``sys.argv[1]`` at import)."""
    if not _S8_MODULES:
        with _argv_as_root():
            import r51_reapp_closed_loop as r51
            import r64_g4_closed_loop as r64
            import r67_g1_screen as r67
        _S8_MODULES.update(r51=r51, r64=r64, r67=r67)
    return _S8_MODULES


def poly345(tau: float) -> float:
    """Quintic 0 -> 1 ramp with zero slope and curvature at both ends (clipped to [0, 1])."""
    tau = min(1.0, max(0.0, tau))
    return tau ** 3 * (10.0 - 15.0 * tau + 6.0 * tau ** 2)


def kernel_pad_gaps_m(cl, plant) -> np.ndarray:
    """Pad gap to the kernel floor per leg [m] (``r51.pad_gaps``: (n.p + goff) / a_n - x); on soil
    the kernel floor is the deformed soil surface that ``soil_floor`` wrote into ``goff``."""
    rotation = cl.rcc._R(plant.q)
    a_n = float(plant.nrm @ rotation[:, 2])
    gaps = np.zeros(4)
    for i in range(4):
        pad_point = plant.r + rotation @ plant.pad_rel[i]
        gaps[i] = (plant.nrm @ pad_point + plant.goff[i]) / a_n - plant.x[i]
    return gaps


def _chunk_row(cl, plant, accumulated, valve) -> np.ndarray:
    contact = np.asarray(accumulated[11:15], float)
    return np.r_[plant.t, contact, contact - plant.Wr, valve, kernel_pad_gaps_m(cl, plant),
                 np.degrees(plant.attitude()), float(accumulated[15])]


def crawler_floor_clearance_mm(cl, plant) -> float:
    """Lowest crawler node above the harness floor plane [mm] (P3-5 / G8 definition)."""
    return float(np.min(sl.crawler_node_heights(cl, plant))) * 1e3


def _sink_mm(plant) -> list | None:
    return None if plant.soil is None else (np.asarray(plant.soil.z, float) * 1e3).tolist()


def _is_ready_held(plant, t_ev: float, ready_since: float | None, min_after_s: float) -> bool:
    return (plant.t >= t_ev + min_after_s - 1e-9 and ready_since is not None
            and plant.t - ready_since >= READY_HOLD_S - 1e-9)


# --------------------------------------------------------------------------------- public API
def preset_controller(cl, c2, variant: dict | None = None):
    """Project C2 R8 preset of the harness (as r67 / r72 ``make_controller_preset``)."""
    del variant
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True,
                              with_reapproach=True)
    controller = c2.C2Controller.from_params(cl.PARAMS, config)
    controller.reset()
    return controller


def make_event_base(cl, c2, soil: str, level: str, pad: str, fs_kN: float,
                    settle_hook: str = SETTLE_HOOK):
    """Plant settled on the crawler and armed, a fresh project preset controller, settle info.

    Same construction as ``s9_soil_closed_loop.run_case`` without a case dict (T-2 identity).

    Returns:
        (plant, controller, info); info = settle snapshot and the pad-surface heights h0 [m].
    """
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = sl.make_plant(cl, level, soil, pad, fs_kN, settle_hook=settle_hook)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    plant.t = 0.0
    plant.arm()
    info = {"settle": sl.settle_snapshot(cl, plant),
            "h0_m": None if plant.soil is None else plant.soil.h.tolist()}
    return plant, preset_controller(cl, c2), info


def control_period_rec(cl, Meas, plant, cmd, valve, ha, period_s, rec, floor_fn=None, rows=None,
                       readings=READINGS_TWO):
    """``s9_soil_closed_loop.control_period`` (ideal sensors) with an event hook and a 1 ms record.

    Args:
        floor_fn: called with the plant before every 1 ms chunk, before ``soil_floor`` (event).
        rows: list that receives one ``ROW_COLUMNS`` row per chunk (None: no record).
        readings: "two" = head and rod pressure (``r64.with_two_pressures``), "head" = the S9
            harness reading (head pressure = net force / A_p). With "head" and no ``floor_fn``
            the arithmetic is that of ``control_period`` (T-1).

    Raises:
        ValueError: unknown ``readings``.
    """
    if readings not in READINGS:
        raise ValueError(f"readings must be one of {READINGS}, got {readings!r}")
    lag_steps = round(cl.LAG_CHUNK_S / plant.dt)
    chunks_per_sample = round(cl.IMU_SAMPLE_S / cl.LAG_CHUNK_S)
    samples_per_period = round(period_s / cl.IMU_SAMPLE_S)
    imu = []
    fmin = np.full(4, np.inf)
    crawler_max = 0.0
    for _ in range(samples_per_period):
        force_sum = np.zeros(3)
        for _ in range(chunks_per_sample):
            if floor_fn is not None:
                floor_fn(plant)
            sl.soil_floor(cl, plant)
            plant.cn = np.where(np.abs(valve) > 1e-6, sl.C_MOVE, sl.C_LOCK)
            accumulated = cl._lagged_step(plant, cmd, valve, lag_steps)
            force_sum += accumulated[0:3]
            fmin = np.minimum(fmin, np.asarray(accumulated[11:15], float) - plant.Wr)
            crawler_max = max(crawler_max, float(accumulated[15]))
            if rows is not None:
                rows.append(_chunk_row(cl, plant, accumulated, valve))
        imu.append(force_sum / (lag_steps * chunks_per_sample))
    measurements = Meas(
        t_s=plant.t, specific_force_m_s2=np.mean(imu, axis=0),
        angular_rate_rad_s=np.asarray(plant.w, float), head_pressure_Pa=plant.pressure() / ha,
        stroke_m=np.asarray(plant.sref, float), stroke_corrected_m=np.asarray(plant.x, float),
        imu_specific_force_samples_m_s2=np.array(imu))
    rec["fmin"] = fmin
    rec["crmax"] = crawler_max
    if readings == READINGS_TWO:
        measurements = _s8_modules()["r64"].with_two_pressures(plant, measurements, ha)
    return measurements


class SoilEventFloor:
    """Floor hook of one Poly345 settlement (spec 426.2 (가)), see :func:`soil_event_floor`."""

    def __init__(self, leg: int, depth_m: float, ramp_s: float, t_ev: float):
        self.leg = leg
        self.depth_m = depth_m
        self.ramp_s = ramp_s
        self.t_ev = t_ev
        self.h0: np.ndarray | None = None
        """Pad-surface heights at the first call (the branch start, before the event)."""

    def offset_m(self, t_s: float) -> float:
        return self.depth_m * poly345((t_s - self.t_ev) / self.ramp_s)

    def __call__(self, plant) -> None:
        offset = self.offset_m(plant.t)
        soil = plant.soil
        if soil is None:  # rigid floor: the r67 kernel offset
            plant.goff[self.leg] = offset
            return
        if self.h0 is None:
            self.h0 = np.array(soil.h, float)
        soil.h[self.leg] = self.h0[self.leg] - offset


def soil_event_floor(leg: int, depth_m: float, ramp_s: float, t_ev: float) -> SoilEventFloor:
    """Floor hook of one event: soil ``h[leg] = h0[leg] - d P345``, rigid ``goff[leg] = d P345``.

    The soil element state (z, s_p, sigma_y) is not touched: the whole soil block under the pad
    drops (spec 426.2 (가)). Call it before ``soil_floor`` in every 1 ms chunk."""
    return SoilEventFloor(leg, depth_m, ramp_s, t_ev)


def run_base_soil(cl, Meas, plant, ctrl, readings=READINGS_TWO, stop_t=None,
                  hold_after_ready_s=sl.HOLD_AFTER_READY_S) -> dict:
    """Closed loop from the start (``run_case`` loop: run limit, stop at FAULT).

    Stops before the period that starts at or after ``stop_t``, else ``hold_after_ready_s`` after
    READY. Returns the timeline (t_lift, t_LOC first, t_DONE, t_READY), the last command and valve
    output, the command SHA-256 and the run-maximum motor stroke [mm]."""
    ha = ctrl.geometry.head_area_m2
    cmd, valve, rec = np.zeros(4), np.zeros(4), {}
    hasher = hashlib.sha256()
    timeline, last_phase = [], None
    t_lift = t_loc = t_ready = None
    stroke_max = np.zeros(4)
    while plant.t < sl.RUN_LIMIT_S:
        if stop_t is not None and plant.t >= stop_t - 1e-9:
            break
        measurements = control_period_rec(cl, Meas, plant, cmd, valve, ha, ctrl.period_s, rec,
                                          readings=readings)
        cmd = np.array(ctrl.update(measurements).leg_speed_m_s)
        hasher.update(cmd.tobytes())
        phase = str(ctrl.phase)
        if phase != last_phase:
            timeline.append((round(plant.t, 3), phase))
            last_phase = phase
        stroke_max = np.maximum(stroke_max, np.asarray(plant.sref, float))
        if t_lift is None and plant.acc[15] == 0.0 and phase == "level":
            t_lift = plant.t
        if t_loc is None and ctrl._is_liftoff_confirmed():
            t_loc = plant.t
        if phase == "ready" and t_ready is None:
            t_ready = plant.t
        if phase == FAULT_PHASE:
            break
        is_hold_over = t_ready is not None and plant.t >= t_ready + hold_after_ready_s - 1e-9
        if stop_t is None and is_hold_over:
            break
    t_done = next((t for t, phase in timeline if phase == "done"), None)
    return {"timeline": timeline, "t_lift": t_lift, "t_loc": t_loc, "t_done": t_done,
            "t_ready": t_ready, "final_phase": last_phase, "cmd": cmd, "valve": valve,
            "commands_sha256": hasher.hexdigest(), "stroke_max_mm": float(stroke_max.max() * 1e3)}


def branch_soil(cl, Meas, plant, ctrl, cmd, valve, event_id: str | None, leg: int, t_ev: float,
                readings: str = READINGS_TWO) -> BranchResult:
    """One event branch from a deepcopied state 0.5 s before ``t_ev`` (r67 ``branch``).

    Runs until READY has held 3 s and at least max(12 s, ramp + 3 s) after the event, at most
    60 s; ``event_id`` None runs the same branch without an event."""
    event = None if event_id is None else EVENTS[event_id]
    floor_fn = None if event is None else soil_event_floor(leg, event["depth"], event["ramp"], t_ev)
    min_after_s = MIN_AFTER_S if event is None else max(MIN_AFTER_S,
                                                        event["ramp"] + SLOW_WINDOW_TAIL_S)
    ha = ctrl.geometry.head_area_m2
    result = BranchResult(event_id, event, leg, t_ev, np.degrees(plant.attitude()), np.empty(0),
                          sink_before_mm=_sink_mm(plant), controller=ctrl)
    rows, rec, n_events_before = [], {}, len(ctrl.events)
    hasher = hashlib.sha256()
    ready_since, has_left_ready = None, False
    stroke_max = np.zeros(4)
    while plant.t < t_ev + MAX_AFTER_S - 1e-9:
        measurements = control_period_rec(cl, Meas, plant, cmd, valve, ha, ctrl.period_s, rec,
                                          floor_fn, rows, readings)
        cmd = np.array(ctrl.update(measurements).leg_speed_m_s)
        hasher.update(cmd.tobytes())
        stroke_max = np.maximum(stroke_max, np.asarray(plant.sref, float))
        phase = str(ctrl.phase)
        result.phases.append((round(plant.t - t_ev, 3), phase))
        if plant.t > t_ev:
            if phase != "ready":
                has_left_ready, ready_since = True, None
            elif ready_since is None:
                ready_since = plant.t
                if result.t_ready_back is None and has_left_ready:
                    result.t_ready_back = plant.t
        if _is_ready_held(plant, t_ev, ready_since, min_after_s):
            break
    result.rows = np.array(rows)
    result.events = [(round(e.t_s - t_ev, 3), e.name) for e in ctrl.events[n_events_before:]]
    result.commands_sha256 = hasher.hexdigest()
    result.stroke_max_mm = float(stroke_max.max() * 1e3)
    result.sink_end_mm = _sink_mm(plant)
    result.crawler_clear_end_mm = crawler_floor_clearance_mm(cl, plant)
    return result


# -------------------------------------------------------------------------------- judgement
def _event_window_end_s(judged: dict, event: dict, is_fast: bool) -> float:
    """End of the event window [s after the event]: W (fast) or ramp end + 3 s (slow)."""
    return judged["W_end_s"] if is_fast else event["ramp"] + SLOW_WINDOW_TAIL_S


def _per_leg_lift_rows(judged: dict, pair: list[str]) -> dict:
    """E-1 (U-S8-32, 350.1 gate): lift sum and last touch-down of each event leg."""
    lifts = judged["lifts"]
    per_leg = {leg: {"sum_s": lifts.get(leg, {}).get("sum_s", 0.0),
                     "last_touch_s": lifts.get(leg, {}).get("last_touch_s", 0.0)} for leg in pair}
    return {"per_leg": per_leg,
            "sum_ok": all(v["sum_s"] <= LIFT_SUM_MAX_S for v in per_leg.values()),
            "last_touch_ok": all(v["last_touch_s"] <= LAST_TOUCH_MAX_S for v in per_leg.values())}


def _adjacent_outside_lift(t, contact, gap, adjacent: list[int], w_end_s: float) -> dict:
    outside = (t > w_end_s)[:, None] & (contact[:, adjacent] <= 0.0)
    gaps = gap[:, adjacent][outside]
    return {"sum_s": float(outside.sum() * CHUNK_S),
            "max_gap_mm": float(gaps.max() * 1e3) if gaps.size else 0.0}


def _pressure_rows(t, force, valve, head_area_m2, w_end_s: float) -> dict:
    """E-4: head-equivalent pressure F_cyl / A_p in and outside the event window."""
    pressure_bar = force / np.asarray(head_area_m2, float) / PA_PER_BAR
    after = t >= 0.0
    in_window = after & (t <= w_end_s)
    outside = after & (t > w_end_s)
    moving = np.abs(valve) > MOVING_SPEED_EPS_M_S
    extending = valve > MOVING_SPEED_EPS_M_S
    window_peak = pressure_bar[in_window].max(axis=0) if in_window.any() else np.zeros(4)
    moving_out = outside[:, None] & moving
    moving_peak = float(pressure_bar[moving_out].max()) if moving_out.any() else 0.0
    saturated = outside[:, None] & extending & (pressure_bar >= RELIEF_BAR)
    return {"window_max_bar": {LEGS[i]: round(float(window_peak[i]), 1) for i in range(4)},
            "moving_outside_max_bar": round(moving_peak, 1),
            "saturation_outside_ms": int(saturated.sum()),
            "saturation_in_window_ms": int((in_window[:, None] & extending
                                            & (pressure_bar >= RELIEF_BAR)).sum())}


def _crawler_rows(t, crawler, w_end_s: float, is_fast: bool, branch: BranchResult) -> dict:
    """E-6 (ASSUMPTION): crawler contact after the event and the crawler state at the end."""
    loaded = (t >= 0.0) & (crawler > 0.0)
    in_window_ms = int((loaded & (t <= w_end_s)).sum())
    outside_ms = int((loaded & (t > w_end_s)).sum())
    is_window_ok = is_fast or in_window_ms == 0  # a slow event allows no contact at all
    is_end_ok = bool(crawler[-1] == 0.0
                     and branch.crawler_clear_end_mm >= CRAWLER_CLEAR_MIN_MM)
    return {"contact_in_window_ms": in_window_ms, "contact_outside_window_ms": outside_ms,
            "max_after_event_kN": round(float(crawler[t >= 0.0].max()) / 1e3, 2),
            "end_load_N": float(crawler[-1]), "clear_end_mm": round(branch.crawler_clear_end_mm, 1),
            "pass": bool(outside_ms == 0 and is_window_ok and is_end_ok),
            "flag": bool(is_fast and in_window_ms > 0)}


def _soil_records(branch: BranchResult) -> dict:
    """Pad sink before / after the event and the controller's soil-rule events after it."""
    soil = branch.controller._soil_state()
    added = None
    if branch.sink_before_mm is not None:
        added = [round(b - a, 2) for a, b in zip(branch.sink_before_mm, branch.sink_end_mm,
                                                 strict=True)]
    after_event = [name for t, name in branch.events if t >= 0.0]
    return {"sink_before_mm": branch.sink_before_mm, "sink_end_mm": branch.sink_end_mm,
            "sink_added_mm": added, "soil_mode_start_s": soil.soil_mode_start_s,
            "loc_revokes_after_event": sum(1 for n in after_event
                                           if n.startswith("INFO_LOC_REVOKED")),
            "diff_sink_events_after_event": [n for n in after_event
                                             if n.startswith("INFO_DIFF_SINK")][:10],
            "info_events_after_event": [n for n in after_event
                                        if n.startswith(RECORDED_INFO_PREFIXES)][:40]}


def _fast_gates(judged, per_leg, outside, low_friction_ok, pressure, end_ok, crawler) -> dict:
    gates = {"E-1_lift_sum_per_leg": per_leg["sum_ok"],
             "E-1_last_touch_per_leg": per_leg["last_touch_ok"],
             "E-2_adj_sum": judged["adj_lift_sum_W_s"] <= 0.5,
             "E-2_adj_gap": judged["adj_max_gap_W_mm"] <= 2.0,
             "E-2_adj_outside": outside["sum_s"] == 0.0 or low_friction_ok,
             "E-3_Fmin_after_W": judged["gates"]["Fmin_after_W"]}
    return {**gates, **_common_gates(judged, pressure, end_ok, crawler)}


def _slow_gates(judged, pressure, end_ok, crawler) -> dict:
    gates = {"E-1_no_lift": judged["gates"]["no_lift"],
             "E-3_Fmin_after_event": judged["gates"]["Fmin_after_event"]}
    return {**gates, **_common_gates(judged, pressure, end_ok, crawler)}


def _common_gates(judged, pressure, end_ok, crawler) -> dict:
    return {"E-4_window_350bar": max(pressure["window_max_bar"].values()) <= WINDOW_MAX_BAR,
            "E-4_moving_180bar": pressure["moving_outside_max_bar"] <= MOVING_MAX_BAR,
            "E-4_saturation0": pressure["saturation_outside_ms"] == 0,
            "E-5_end_ready_att": judged["gates"]["end_att"],
            "E-5_fault0": judged["gates"]["fault0"],
            "E-5_stroke": end_ok,
            "E-6_crawler": crawler["pass"],
            "E-7_recurrence": judged["gates"]["recurrence"]}


def judge_soil_event(branch: BranchResult, fs_kN: float, head_area_m2,
                     prefix_stroke_max_mm: float = 0.0) -> dict:
    """Spec 426.3 rows E-1 .. E-7 of one branch (r67 ``judge_event`` plus E-1 per leg, E-4,
    E-6 and the run-maximum stroke of E-5).

    Args:
        branch: the branch record (:func:`branch_soil`).
        fs_kN: front seal friction of the run (U-S8-75 low-friction exception below 2 kN).
        head_area_m2: A_p per leg (head-equivalent pressure).
        prefix_stroke_max_mm: run-maximum motor stroke of the base run up to the branch.
    """
    r67 = _s8_modules()["r67"]
    rows, event, leg = branch.rows, branch.event, branch.leg
    judged = r67.judge_event(rows, branch.phases, branch.events, rows[:, CRAWLER_COLUMN],
                             branch.t_ev, branch.t_ready_back, event, leg, branch.controller,
                             branch.att0_deg)
    is_fast = r67.is_fast(event)
    t = rows[:, 0] - branch.t_ev
    contact, force, valve, gap = rows[:, 1:5], rows[:, 5:9], rows[:, 9:13], rows[:, 13:17]
    w_end_s = _event_window_end_s(judged, event, is_fast)
    pressure = _pressure_rows(t, force, valve, head_area_m2, w_end_s)
    crawler = _crawler_rows(t, rows[:, CRAWLER_COLUMN], w_end_s, is_fast, branch)
    stroke_max_mm = max(prefix_stroke_max_mm, branch.stroke_max_mm)
    is_stroke_ok = stroke_max_mm <= STROKE_OK_MM
    flags = []
    out = {**judged, "gates_r67": judged["gates"], "fast": is_fast, "event_window_end_s": w_end_s,
           "pressure": pressure, "crawler": crawler, "stroke_max_run_mm": round(stroke_max_mm, 2),
           "soil": _soil_records(branch), "commands_sha256": branch.commands_sha256}
    if is_fast:
        pair = [LEGS[leg], LEGS[r67.DIAG[leg]]]
        adjacent = [i for i in range(4) if LEGS[i] not in pair]
        per_leg = _per_leg_lift_rows(judged, pair)
        outside = _adjacent_outside_lift(t, contact, gap, adjacent, w_end_s)
        low_friction_ok = (fs_kN < LOW_FRICTION_FS_KN and 0.0 < outside["sum_s"]
                           <= LOW_FRICTION_OUTSIDE_SUM_S
                           and outside["max_gap_mm"] <= LOW_FRICTION_OUTSIDE_GAP_MM)
        if low_friction_ok:
            flags.append(LOW_FRICTION_FLAG)
        out.update(lift_per_leg=per_leg["per_leg"], adj_outside_W=outside)
        gates = _fast_gates(judged, per_leg, outside, low_friction_ok, pressure, is_stroke_ok,
                            crawler)
    else:
        gates = _slow_gates(judged, pressure, is_stroke_ok, crawler)
    if crawler["flag"]:
        flags.append(CRAWLER_RECONTACT_FLAG)
    out.update(gates=gates, flags=flags, sample="out")  # spec 426.1: every A run is out of sample
    out["pass"] = bool(all(gates.values()))
    return out


# ------------------------------------------------------------------------------------- jobs
def _branch_record(cl, Meas, plant, ctrl, base, event_id, job, t_ev, timing, prefix_mm) -> dict:
    branch = branch_soil(cl, Meas, copy.deepcopy(plant), copy.deepcopy(ctrl), base["cmd"].copy(),
                         base["valve"].copy(), event_id, LEGS.index(job.leg), t_ev, job.readings)
    judged = judge_soil_event(branch, job.fs_kN, ctrl.geometry.head_area_m2, prefix_mm)
    phase_at_event = next((p for t, p in branch.phases if t >= 0.0), None)
    judged.update(event=event_id, timing=timing, t_ev_s=round(t_ev, 3),
                  phase_at_event=phase_at_event)
    return judged


def _timing_branches(cl, Meas, plant, ctrl, job, base, timing) -> list[dict]:
    """Branches of one timing from the state ``plant`` / ``ctrl`` 0.5 s before the event."""
    t_ev = plant.t + PRE_S
    return [_branch_record(cl, Meas, plant, ctrl, base, event_id, job, t_ev, timing,
                           base["stroke_max_mm"]) for event_id in TIMING_EVENTS[timing]]


def run_job(key: str) -> dict:
    """Worker entry: base run, READY + 5 s branches and LEVEL branches of one job."""
    job = EventJob.from_key(key)
    _s8_modules()["r51"].place_worker()
    cl, c2, Meas = sl._imports()
    t_wall = time.perf_counter()
    plant, ctrl, info = make_event_base(cl, c2, job.soil, LEVEL, PAD, job.fs_kN)
    result = {"key": key, "soil": job.soil, "leg": job.leg, "fs_kN": job.fs_kN,
              "readings": job.readings, "settle_hook": SETTLE_HOOK, **info, "runs": []}
    ready_plant, ready_ctrl = copy.deepcopy(plant), copy.deepcopy(ctrl)
    base = run_base_soil(cl, Meas, ready_plant, ready_ctrl, job.readings,
                         hold_after_ready_s=READY_DELAY_S - PRE_S)
    result["base"] = {k: base[k] for k in ("timeline", "t_lift", "t_loc", "t_done", "t_ready",
                                           "final_phase", "stroke_max_mm")}
    if base["t_ready"] is None:
        result["error"] = "base run without READY"
        return result
    result["runs"] += _timing_branches(cl, Meas, ready_plant, ready_ctrl, job, base, "ready")
    if base["t_loc"] is None or base["t_done"] is None:
        result["level_skipped"] = "base run without LOC / DONE"
    else:
        t_level = base["t_loc"] + 0.5 * (base["t_done"] - base["t_loc"])
        level_base = run_base_soil(cl, Meas, plant, ctrl, job.readings, stop_t=t_level - PRE_S)
        result["level_branch_t_s"] = round(plant.t, 3)
        result["runs"] += _timing_branches(cl, Meas, plant, ctrl, job, level_base, "level")
    result["wall_s"] = round(time.perf_counter() - t_wall, 1)
    return result


def safe_run_job(key: str) -> dict:
    try:
        return run_job(key)
    except Exception as exc:  # keep the batch going; the error is reported
        return {"key": key, "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()[-2000:]}


def all_jobs(set_name: str = "all") -> list[str]:
    """Job keys of a named set (spec 426.3 grid: 16 = 12 two-pressure + 4 head-reading jobs)."""
    def grid(soils, readings):
        return [EventJob(s, leg, fs, readings).key for s in soils for leg in JOB_LEGS
                for fs in JOB_FS_KN]

    sets = {"main": grid(MAIN_SOILS, READINGS_TWO), "head": grid(HEAD_SOILS, READINGS_HEAD),
            "j1": grid(OPTIONAL_SOILS, READINGS_TWO)}
    sets["all"] = sets["main"] + sets["head"]
    sets["all_j1"] = sets["all"] + sets["j1"]
    if set_name not in sets:
        raise ValueError(f"unknown set {set_name!r}, expected {sorted(sets)}")
    return sets[set_name]


def select_jobs(set_name: str, filter_text: str = "", readings: str = "") -> list[str]:
    """Jobs of a set, kept if any filter substring matches, readings overridden when given."""
    keys = all_jobs(set_name)
    if readings:
        keys = [replace(EventJob.from_key(k), readings=readings).key for k in keys]
        keys = list(dict.fromkeys(keys))  # duplicates (main + head on rigid) run once
    needles = [n for n in filter_text.split(",") if n]
    if needles:
        keys = [k for k in keys if any(n in k for n in needles)]
    return keys


def set_parent_affinity(mask_hex: str | None) -> None:
    if not mask_hex or sys.platform != "win32":
        return
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    k32.SetProcessAffinityMask(k32.GetCurrentProcess(), int(mask_hex, 16))


def _print_summary(results: list[dict]) -> None:
    for res in results:
        if "error" in res:
            print(res["key"], "ERROR", res["error"])
            continue
        for run in res["runs"]:
            failed = [k for k, v in run["gates"].items() if not v]
            print(res["key"], run["timing"], run["event"], "pass", run["pass"], failed or "-",
                  "flags", run["flags"] or "-",
                  "crawler_max_kN", run["crawler"]["max_after_event_kN"],
                  "ready_back", run["t_ready_back_s"])


def main() -> None:
    jobs = select_jobs(os.environ.get("R426A_SET", "all"), os.environ.get("R426A_FILTER", ""),
                       os.environ.get("R426A_READINGS", ""))
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        for key in jobs:
            print(key)
        print(len(jobs), "jobs,", 5 * len(jobs), "branches")
        return
    set_parent_affinity(os.environ.get("R426A_AFFINITY"))
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        results = pool.map(safe_run_job, jobs, chunksize=1)
    meta = {"script": "04_scripts/03_control/s9/s9_soil_event_screen.py",
            "spec": "426.3 study A (soft-soil floor events)", "settle_hook": SETTLE_HOOK,
            "set": os.environ.get("R426A_SET", "all"), "filter": os.environ.get("R426A_FILTER"),
            "readings_override": os.environ.get("R426A_READINGS"),
            "affinity": os.environ.get("R426A_AFFINITY"), "workers": workers,
            "n_jobs": len(jobs), "row_columns": ROW_COLUMNS,
            "wall_s": round(time.perf_counter() - t0, 1)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "results": results}, indent=1, default=float),
                   encoding="utf-8")
    _print_summary(results)
    print("done", meta["wall_s"], "s ->", out)


if __name__ == "__main__":
    main()
