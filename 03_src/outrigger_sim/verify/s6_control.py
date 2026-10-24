"""S6 stage 2: pre-judgement of the C2 closed-loop checks 1-8, T and R on the L1 Chrono runs.

``00_docs/04_control/s6_control_spec.md`` 3 (decided criteria), 4 (matrix), 6 (G6 pad record),
rev. 2 (K1-K8), rev. 3 sections 16-20 (criteria adjustments J1-J7 and the integrity items I1-I8,
user decision U19 of 2026-10-21). Inputs are the case directories written by
``04_scripts/02_chrono/s6_stage2.job_stage2`` (Record 50 Hz, ``pads.npz`` 1 ms, ``result.json``,
controller events and probe history). Automatic pass / fail is a pre-check; control-expert /
dynamics-expert judge.

Definitions (spec 3, rev. 3):

* crawler lift-off = first Record sample with zero crawler normal force after which it stays
  zero (Record 20 ms; reported with that resolution);
* t_TOUCH = first controller phase after TOUCH (= LEVEL start), t_READY = first READY;
* "last 5 s" = the last 5 s of the run (the run ends 10 s after READY by construction,
  plus the 8 s R5 CHECK allowance ``check_max_s - check_time_s`` of rev. 8 44.6);
* floor-event cases (RE1b, RE1b-F both grades, RE1b-P; spec rev. 7 41.2 decision (a)): the
  whole-run "3 F_min (1 ms)" row is info (intended lift-off); judged instead: F_min before the
  event, F_min after the re-READY, no lift-off of the other legs after the event, no RR
  lift-off after the re-READY, re-READY <= 60 s; RR lift-off time / ratio is reported;
* true attitude = body roll / pitch of the Record truth (ZYX), vs the target of the case;
* true cylinder force minimum = minimum over every physics step of each 1 ms interval
  (``pads.npz`` ``F_cyl_min_interval``) after lift-off; item 8 also without the REANCHOR
  intervals (J4, spec 20.3);
* final loads = mean true cylinder force over the last 5 s; corrective part ``A+ F`` = the
  projection of the leg loads onto the heave / roll / pitch support space, twist ``n^T F``
  with the unit twist vector orthogonal to it;
* spec rev. 27 102 / dynamics 5.17 (2026-10-22): 7c truth = probe start load (one-sided for
  zero-calibration deduction legs), T1 reject leaves out the U71 CHECK round trip, J6 = rear
  pad force after H4 against ``mu (P_stop + m_rod g)`` (the H4 reduction is recorded only);
* spec rev. 28 (2026-10-22): every case carries ``condition`` = ``base`` / ``sensitivity``
  (111); a sensitivity case reports its 7c, D8-margin and one-sided J6 rows. Combined-judge H4
  cases outside G6 get the one-sided J6 row (ratio <= 1.1, 112.1). The row "72.1 (6) no false
  pressure diagnosis" judges zero D5 / E-5 warnings without a drift / offset injection
  (110.1). Settlement / drop cases of an L1-R bundle run with the mechanics off carry
  ``superseded_by`` B2 and are records (109.2);
* spec rev. 29 (2026-10-24, 119.2, 122, 129 ①): only a time-varying injection
  (``head_drift_bar``) makes the 72.1 (6) row a report, a constant ``head_offset_bar`` is
  judged; a case recorded by the pre-110.1 controller (no ``load_reference_settle_s`` in its
  ``two_pressure`` settings) has that row ``superseded`` by the offline replay
  ``verify_S6_L1_diag_load_reference_rev29.json`` (``replay_passed`` from its values).

Row kinds: ``passed`` True / False is judged, ``None`` is a report or not judged (``note``).
Item 5b is a quality metric (U22): a failure reads ``spec shortfall``, not a functional failure
(``kind`` ``"quality"``). The intended failure (normal as-shipped IMU, item 2) is not judged
(I7 / J7). Rows of the RE1c case (controller bypassed, spec 30) carry ``kind`` ``"info"`` and
``passed`` None (raw outcome in ``passed_raw``); a judged row whose value could not be measured
(run ended first) is ``passed`` None, not a failure.

Units SI internally; the JSON uses kN / deg / mm where named.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.frames import roll_pitch_from_quat, roll_pitch_from_specific_force
from outrigger_sim.verify import l1_scope

F_MIN_N = 9453.0
"""Fallback ``F_min`` only for metrics without ``F_min_N`` (older summaries); the checks take
the run's own YAML ``control.F_min_cylinder_N`` (spec rev. 13, 68: thresholds are
``F_min + margin``, never absolute)."""
D8_MARGIN_N = 5000.0
MOUNT_SHARE_DEG = 0.02
ATT_TOL_DEG = 0.2
ROCKING_TOL_DEG = 0.06
FILTER_RESIDUAL_TOL_DEG = 0.005
MOVING_PRESSURE_TOL_BAR = 180.0
PROBE_ATT_TOL_DEG = 0.1
REANCHOR_ATT_TOL_DEG = 0.1
SETTLE_READY_S = 40.0
TARGET_STROKE_MAX_M = 0.670
CRAWLER_CLEARANCE_MIN_M = 0.020
TARGET_CHANGE_READY_S = 50.0
"""J3 (spec 16.5): change -> READY <= 50 s (ASSUMPTION): ramp + LEVEL <= 25 s, REANCHOR <=
20 s, probe <= 12 s (formerly 40 s, before U3 and the trapezoid probe)."""
LEVEL_TIME_TOL = 0.10
"""J2 (spec 16.4): LEVEL start -> true attitude held inside 0.2 deg, +-10 % of the reduced
model."""
CORRECTIVE_TOL_FLAT = 0.01
CORRECTIVE_TOL_SLOPE = 0.02
"""J1 (spec 16.3): +-1 % W/4 on the flat floor; slopes +-2 % W/4 until the pad horizontal-force
couple can be removed on the reduced side (temporary)."""
LEVEL_TREND_FORCE_TOL_KN = 2.0
LEVEL_TREND_TIME_TOL_S = 2.0
"""J4 (spec 16.6 / 20.3): differences between auger levels, Chrono - reduced (ASSUMPTION)."""
TREND_TOLERANCE_N = 1250.0
"""U54 / U64 / J-2 (spec 55.2, 64.3): item 8 ordering ``top <= middle + tol <= bottom + 2 tol``;
1.25 kN = the 3 sigma of one REXOME35 front two-sensor reading (1.24 kN) rounded up
(ASSUMPTION; 1.0 kN before)."""
PROBE_TRUTH_HALF_WINDOW_S = 0.1
"""U53 / J-1 (spec 55.1, 60): half window of the mean true cylinder force around each hold-end
reading; their midpoint is recorded only since spec rev. 27 102.1 (``truth_midpoint_kN``)."""
PROBE_START_LOAD_WINDOW_S = 0.5
"""Spec rev. 27 102.1 (dynamics 5.17.2): the 7c load truth of a probed leg is its probe start
load, the mean true cylinder force over the 0.5 s before its first move starts (the quantity
``ground_contact._stiffness_cue`` estimates); the hold-end midpoint is larger by S_ii d / 2."""


class TransientWindowMode(StrEnum):
    """How the event-transient window of a floor-event case ends (spec 62.2, J-4 / J-5)."""

    PHYSICAL = "physical"
    """``W = [t_event, min(t_RR,last recontact + T_3, t_event + cap)]`` (U57 / U58 decided)."""
    FIXED = "fixed"
    """Legacy provisional windows: 1.0 s for item 3, 2.0 s for items 4 / 5a (spec 55.5-55.6)."""


class MovingPressureSamples(StrEnum):
    """Which moving samples outside the transient window the 180 bar check judges (J-5)."""

    EXTEND_ONLY = "extend_only"
    """``u_applied > 0`` only; retraction samples are reported (spec 62.2)."""
    ALL = "all"
    """Every moving sample (legacy)."""


THREE_POINT_ROCKING_PERIOD_S = {"top": 0.82, "middle": 0.82, "bottom": 0.82}
"""``T_3``: diagonal rocking period of the three-point support without RR (dynamics rev. 28,
top level 0.82 s); the middle and bottom levels use the top value until dynamics-expert gives
theirs (ASSUMPTION, note ``T3_from_top_level``)."""


@dataclass(frozen=True)
class EventTransientSettings:
    """Event-transient window and limits of the floor-event cases (spec 62, U57 / U58).

    Attributes:
        transient_window: ``physical`` (default) or ``fixed`` (legacy 1.0 / 2.0 s windows).
        three_point_rocking_period_s: ``T_3`` per auger level (s).
        transient_window_cap_s: Upper bound of the physical window after the event (s);
            reaching it leaves the note ``transient_window_capped`` (ASSUMPTION 5 s).
        other_lift_allow_s: Item 3: total lift-off time allowed per other leg in the window.
        other_lift_height_allow_m: Item 3: largest rise of an other leg's floor point.
        other_slip_allow_m: Item 3: largest horizontal move of an other leg's ground anchor.
        moving_pressure_samples: Item 4 outside the window: ``extend_only`` or ``all``.
        transient_pressure_limit_bar: Item 4 inside the window: head ``F / A_p`` in any state.
        fixed_lift_window_s: ``fixed`` mode: item 3 window length (legacy U57 1.0 s).
        fixed_pressure_window_s: ``fixed`` mode: items 4 / 5a window length (legacy 2.0 s).
    """

    transient_window: TransientWindowMode = TransientWindowMode.PHYSICAL
    three_point_rocking_period_s: Mapping[str, float] = field(
        default_factory=lambda: dict(THREE_POINT_ROCKING_PERIOD_S)
    )
    transient_window_cap_s: float = 5.0
    other_lift_allow_s: float = 0.5
    other_lift_height_allow_m: float = 0.002
    other_slip_allow_m: float = 0.005
    moving_pressure_samples: MovingPressureSamples = MovingPressureSamples.EXTEND_ONLY
    transient_pressure_limit_bar: float = 350.0
    fixed_lift_window_s: float = 1.0
    fixed_pressure_window_s: float = 2.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "transient_window", TransientWindowMode(self.transient_window))
        object.__setattr__(
            self, "moving_pressure_samples", MovingPressureSamples(self.moving_pressure_samples)
        )

    def to_meta(self) -> dict[str, Any]:
        meta = asdict(self)
        meta["three_point_rocking_period_s"] = dict(self.three_point_rocking_period_s)
        return {key: str(value) if isinstance(value, StrEnum) else value
                for key, value in meta.items()}


EVENT_TRANSIENT = EventTransientSettings()
"""Decided event-transient settings (U57, U58 of 2026-10-22, spec 62)."""
SHADOW_TOL_DEG = 0.03
"""J5 / I6 (spec 16.7): (B) shadow floor estimate - true floor, ideal IMU (report)."""
SENSOR_PATH_TOL_DEG = 0.005
"""I5 (spec 17): last 5 s mean of (IMU filter attitude - true attitude) = grade zero error."""
H4_REDUCTION_EXPECTED = {"fdown3.5": -0.49, "fup3.5": -0.60}
H4_REDUCTION_TOL = 0.10
"""Former J6 / I8 (spec 16.8, 20.4): rear leg-normal force L, H4 on vs off; +-10 %p. REXOME33
values, recorded only since dynamics 5.17.3 (J6 = ``H4_MECHANISM_RATIO_BAND``)."""
REDUCED_LEVEL_TIME_FALLBACK_S = {"roll3": 7.90, "diag3": 11.98}
"""Spec 16.2 table, reduced model: LEVEL start -> held inside 0.2 deg (used until the reduced
reference carries ``t_within_0p2_after_level_s``)."""
W4_N = 382290.66 / 4.0
LEGS = ("FL", "FR", "RL", "RR")
GROUND_SPEC_SHORTFALL = "spec shortfall (quality metric, U22), not a functional failure"
_EVENT_PATTERN = re.compile(r"t_s=([-0-9.eE+]+), name='([^']*)'")


def _deg(x):
    return np.degrees(np.asarray(x, dtype=float))


def load_case(case_dir: Path) -> dict[str, Any]:
    """Result, Record arrays, pad record, events and probe history of one case (and the
    ``settle_velocity.npz`` of a settlement case, ``verify/l1_scope``)."""
    out: dict[str, Any] = {"dir": case_dir}
    out["result"] = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    rec = np.load(case_dir / "record" / "record.npz")
    out["rec"] = {k: rec[k] for k in rec.files}
    pads = case_dir / "pads.npz"
    out["pads"] = None if not pads.exists() else {k: v for k, v in np.load(pads).items()}
    velocity = case_dir / l1_scope.SETTLE_VELOCITY_FILE  # settlement cases only (M4 input)
    if velocity.exists():
        with np.load(velocity, allow_pickle=False) as data:
            out[l1_scope.CASE_KEY] = {k: data[k] for k in data.files}
    ev = case_dir / "controller_events.json"
    out["events"] = json.loads(ev.read_text(encoding="utf-8")) if ev.exists() else []
    ph = case_dir / "probe_history.json"
    out["probes"] = json.loads(ph.read_text(encoding="utf-8")) if ph.exists() else []
    return out


def _times(case: Mapping[str, Any]) -> dict[str, float | None]:
    res = case["result"]
    t0 = float(res["settings"]["start_t_s"])
    phases = [(float(t), p) for t, p in res["phases"]]
    t_touch = None
    for (_t, p), (t2, p2) in zip(phases[:-1], phases[1:], strict=True):
        if p == "touch" and p2 != "touch":
            t_touch = t2
            break
    t_ready = next((t for t, p in phases if p == "ready"), None)
    rec = case["rec"]
    t = rec["t"] - t0
    fz = np.asarray(rec["F_crawler"])[:, 2]
    on = np.flatnonzero(fz > 0.0)
    t_off = float(t[on[-1] + 1]) if on.size and on[-1] + 1 < len(t) else None
    return {"t0": t0, "touch": t_touch, "ready": t_ready, "liftoff": t_off, "end": float(t[-1])}


def _phase_windows(case: Mapping[str, Any], phase: str, end_s: float) -> list[tuple[float, float]]:
    """(start, end) of every interval the controller spent in ``phase``."""
    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    windows = []
    for (t1, p), nxt in zip(phases, [*phases[1:], (end_s, "end")], strict=True):
        if p == phase:
            windows.append((t1, nxt[0]))
    return windows


def _events(case: Mapping[str, Any]) -> list[tuple[float, str]]:
    """(t, name) of the controller events (``str(C2Event)`` lines)."""
    out = []
    for line in case["events"]:
        match = _EVENT_PATTERN.search(str(line))
        if match:
            out.append((float(match.group(1)), match.group(2)))
    return out


def support_projection(params) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """(P, n): projector onto the support space of (heave, roll, pitch) and the unit twist."""
    xy = np.array([leg.pad_bottom_center_retracted_m[:2] for leg in params.legs], dtype=float)
    s = np.vstack([np.ones(4), xy[:, 1], -xy[:, 0]])  # rows: sum, Mx, My (per unit leg load)
    proj = s.T @ np.linalg.solve(s @ s.T, s)
    w, v = np.linalg.eigh(np.eye(4) - proj)
    n = v[:, int(np.argmax(w))]
    return proj, n / np.linalg.norm(n)


def reduced_reference(run: Mapping[str, Any], params) -> dict[str, Any]:
    """Item 1 reference of one reduced-model run (``c2_revision_verify.json`` ``runs`` entry).

    ``t_within_0p2_after_level_s`` (J2) is taken from the run when present
    (``t_within_target_s - t_touch_s``); otherwise :func:`judge` falls back to the spec 16.2
    table.
    """
    proj, n = support_projection(params)
    loads = np.asarray(run["levelled_loads_true_kN"], dtype=float)
    out = {
        "t_level_after_touch_s": run.get("t_level_after_touch_s"),
        "min_true_cyl_force_kN": run.get("min_true_cyl_force_kN"),
        "levelled_loads_kN": loads.tolist(),
        "corrective_kN": (proj @ loads).tolist(),
        "twist_kN": float(n @ loads),
    }
    if run.get("t_within_target_s") is not None and run.get("t_touch_s") is not None:
        out["t_within_0p2_after_level_s"] = run["t_within_target_s"] - run["t_touch_s"]
    return out


# --- per-case quantities ---------------------------------------------------------------------


def _f_min_from_params(params) -> float:
    """``control.F_min_cylinder_N`` of the case parameters (the fallback for a stub)."""
    try:
        return float(params.control.F_min_cylinder_N)
    except AttributeError:
        return F_MIN_N


def _f_min_N(m: Mapping[str, Any]) -> float:
    return float(m.get("F_min_N", F_MIN_N))


def _held_inside_since(t, err_maxabs, start_s: float, limit_deg: float) -> float | None:
    """First time after ``start_s`` from which ``err_maxabs`` stays below ``limit_deg``."""
    after = t >= start_s
    if not after.any():
        return None
    outside = np.flatnonzero(after & (err_maxabs >= limit_deg))
    if outside.size == 0:
        return float(t[np.argmax(after)])
    index = outside[-1] + 1
    return float(t[index]) if index < len(t) else None


def _crawler_clearance_min_m(rec, t, t_from_s: float, params, floor_plane) -> float | None:
    """I4: smallest distance of the crawler box corners from the floor plane after ``t_from_s``.

    ``floor_plane`` = ``{"normal_world": (3,), "offset_m": d}`` with the floor ``n . x = d``
    (world). Corners: C2 crawler box (``CRAWLER_XY_BOX_M``) at the crawler bottom height in body
    axes, moved with the Record body pose (Record 20 ms).
    """
    from outrigger_sim.control.c2 import CRAWLER_XY_BOX_M
    from outrigger_sim.frames import rotate_vector

    if floor_plane is None:
        return None
    normal = np.asarray(floor_plane["normal_world"], dtype=float)
    normal = normal / np.linalg.norm(normal)
    offset = float(floor_plane["offset_m"])
    (x0, x1), (y0, y1) = CRAWLER_XY_BOX_M
    z = float(params.ground.crawler_bottom_z_m)
    corners = [np.array([x, y, z]) for x in (x0, x1) for y in (y0, y1)]
    sel = np.flatnonzero(t >= t_from_s)
    clearances = [
        min(
            float(normal @ (rec["body_pos"][i] + rotate_vector(rec["body_quat_wxyz"][i], c)))
            - offset
            for c in corners
        )
        for i in sel
    ]
    return min(clearances) if clearances else None


def _grade_tilt_deg(grade: str) -> tuple[float, float]:
    """IMU tilt reading of a level body at rest for a sensor grade (bias only)."""
    from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2, imu_config_for_grade

    bias = np.asarray(imu_config_for_grade(grade).accel_bias_m_s2, dtype=float)
    roll, pitch = roll_pitch_from_specific_force(np.array([0, 0, STANDARD_GRAVITY_M_S2]) + bias)
    return math.degrees(roll), math.degrees(pitch)


def _filter_tilt_deg(rec) -> NDArray[np.float64]:
    """IMU tilt through the controller's 2nd-order filter (a = 0.04)."""
    f = np.asarray(rec["meas.specific_force"])
    imu = _deg(np.column_stack(roll_pitch_from_specific_force(f)))
    y1 = imu[0].copy()
    y2 = imu[0].copy()
    filt = np.empty_like(imu)
    for i in range(len(imu)):
        y1 = y1 + 0.04 * (imu[i] - y1)
        y2 = y2 + 0.04 * (y1 - y2)
        filt[i] = y2
    return filt


class CaseCondition(StrEnum):
    """Sensor condition of a case (spec rev. 28 111)."""

    BASE = "base"
    """Ideal sensors, or normal / good grades with the zero calibration (PS-4 cal included:
    +-4 bar is inside the normal-grade maximum error)."""
    SENSITIVITY = "sensitivity"
    """Calibration off (``*_nocal``, IMU ``normal_as_shipped``) or the conservative / old-worst
    pressure grade: 7c and the D8 margin are reported, not judged."""


SENSITIVITY_PRESSURE_GRADES = ("conservative", "old_worst")
STATIC_ERROR_FREE_PRESSURE_GRADES = ("legacy",)
"""Pressure grade without a static error: running it without the calibration is no
sensitivity condition."""
UNCALIBRATED_IMU_GRADES = ("normal_as_shipped",)


def case_condition(settings: Mapping[str, Any]) -> tuple[CaseCondition, list[str]]:
    """``base`` or ``sensitivity`` of a case from its ``result.json`` settings, with reasons.

    Settings without the bundle-B keys (``pressure_grade``, ``zero_calibration``) are read from
    the case id (``*_nocal``, ``conservative``, ``old_worst``); a case id without those tokens is
    a run of the legacy pressure sensors.
    """
    case_id = str(settings.get("case_id", ""))
    grade = settings.get("pressure_grade")
    if grade is None:
        grade = next((g for g in SENSITIVITY_PRESSURE_GRADES if g in case_id), "legacy")
    is_calibrated = settings.get("zero_calibration", not case_id.endswith("_nocal"))
    reasons = []
    if grade in SENSITIVITY_PRESSURE_GRADES:
        reasons.append(f"pressure grade {grade}")
    if not is_calibrated and grade not in STATIC_ERROR_FREE_PRESSURE_GRADES:
        reasons.append("zero calibration off")
    imu_grade = settings.get("grade", "ideal")
    if imu_grade in UNCALIBRATED_IMU_GRADES:
        reasons.append(f"IMU grade {imu_grade} (no field zero)")
    condition = CaseCondition.SENSITIVITY if reasons else CaseCondition.BASE
    return condition, reasons


PRESSURE_DIAGNOSIS_WARNINGS = ("WARN_LOAD_SUM_MISMATCH", "WARN_PRESSURE_DRIFT")
TIME_VARYING_INJECTION_KEYS = ("head_drift_bar",)
"""Spec rev. 29 122: an injection changes after the load baseline is stored (the drift; a future
in-event step offset would join here); its 72.1 (6) row is a report."""
CONSTANT_OFFSET_KEYS = ("head_offset_bar",)
"""Spec rev. 29 122: a constant offset present from the start cancels in the baseline
difference like a grade's static error, so its case stays judged (recorded only)."""

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DIAGNOSTIC_REPLAY_FILE = (
    PROJECT_ROOT / "06_analysis" / "01_chrono" / "16_S6"
    / "verify_S6_L1_diag_load_reference_rev29.json"
)
"""Offline replay of the 110.1 load-baseline logic on the recorded runs (spec rev. 29 119)."""
LOAD_REFERENCE_SETTING_KEY = "load_reference_settle_s"
"""A ``two_pressure`` setting the 110.1 controller records; its absence marks a pre-110.1 run."""
REPLAY_DRIFT_HOLD_S = 30.0
"""E-5 hold (``TwoPressureSettings.drift_hold_s``) applied to the replay's 4 kN runs."""
REPLAY_SUM_HOLD_S = 0.5
"""D5 hold (``TwoPressureSettings.sum_hold_s``). The D5 limit ``4 F_band + 2.5 kN`` is at
least 4 kN for ``F_band`` >= 0.375 kN, so a 4 kN run shorter than this cannot warn D5."""


def _nonzero_keys(settings: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys
            if any(float(value) != 0.0 for value in settings.get(key) or ())]


def _ran_pre_load_reference_code(case: Mapping[str, Any]) -> bool:
    """Spec rev. 29 129 ①: the controller meta has no ``load_reference_settle_s`` (pre-110.1)."""
    controller_meta = case["result"].get("controller_meta") or {}
    two_pressure_settings = (controller_meta.get("two_pressure") or {}).get("settings") or {}
    return LOAD_REFERENCE_SETTING_KEY not in two_pressure_settings


def _load_diagnostic_replay(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Replay rows by (batch directory name, case name); empty when the file is missing."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {(row["batch"], row["case"]): row for row in payload["cases"]}


_REPLAY_CACHE: dict[Path, dict[tuple[str, str], dict[str, Any]]] = {}


def _diagnostic_replay_row(case: Mapping[str, Any], path: Path) -> dict[str, Any] | None:
    if path not in _REPLAY_CACHE:
        _REPLAY_CACHE[path] = _load_diagnostic_replay(path)
    case_dir = case.get("dir")
    if case_dir is None:
        return None
    return _REPLAY_CACHE[path].get((Path(case_dir).parent.name, case["result"]["case"]))


def _replay_verdict(row: Mapping[str, Any]) -> dict[str, Any]:
    """``replay_passed`` from the replay values: E-5 needs a 4 kN run of 30 s, D5 a run of
    0.5 s beyond a limit of at least 4 kN; a 4 kN run of 0.5 s or more leaves D5 undecided."""
    longest_s = float(row["longest_run_over_4kN_s"])
    passed: bool | None
    if longest_s >= REPLAY_DRIFT_HOLD_S - 1e-9:
        passed = False  # E-5 would warn
    elif longest_s < REPLAY_SUM_HOLD_S - 1e-9:
        passed = True
    else:
        passed = None  # D5 needs the per-case limit, not in the replay file
    return {
        "source": DIAGNOSTIC_REPLAY_FILE.name,
        "batch": row["batch"],
        "longest_run_over_4kN_s": longest_s,
        "max_abs_dev_kN": row.get("max_abs_dev_kN"),
        "references_t_s_sum_kN": row.get("references_t_s_sum_kN"),
        "replay_passed": passed,
    }


def diagnostic_false_alarm_metrics(
    case: Mapping[str, Any],
    settings: Mapping[str, Any],
    replay_path: Path = DIAGNOSTIC_REPLAY_FILE,
) -> dict[str, Any]:
    """D5 / E-5 warning counts of a case and its injection (spec rev. 28 110.1, rev. 29 122).

    Returns:
        ``counts`` per warning; ``injection`` = the time-varying injections (empty = every
        warning is a false diagnosis); ``constant_offset`` = constant offsets (recorded only);
        ``pre_load_reference_code`` = the run used the pre-110.1 controller; ``replay`` = the
        offline replay verdict of such a run (``None`` when not pre-110.1 or not replayed).
    """
    names = [name for _t, name in _events(case)]
    counts = {warning: names.count(warning) for warning in PRESSURE_DIAGNOSIS_WARNINGS}
    is_pre_load_reference = _ran_pre_load_reference_code(case)
    replay = None
    if is_pre_load_reference:
        row = _diagnostic_replay_row(case, replay_path)
        replay = None if row is None else _replay_verdict(row)
    return {
        "counts": counts,
        "injection": _nonzero_keys(settings, TIME_VARYING_INJECTION_KEYS),
        "constant_offset": _nonzero_keys(settings, CONSTANT_OFFSET_KEYS),
        "pre_load_reference_code": is_pre_load_reference,
        "replay": replay,
    }


GROUND_SETTLEMENT_EVENTS = ("settle_RR", "settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
L1R_SUPERSEDED_SOURCE = "B2 (L1-R on, spec rev. 28 109.2)"
"""Formal source of the settlement / drop judgement; the bundle-B runs of those cases had to
switch the L1-R mechanics off (no ground-settlement legs in ``chrono/rod_chamber_link``)."""


def superseded_by(settings: Mapping[str, Any]) -> str | None:
    """The formal source when this case is an L1-R bundle settlement / drop run with the
    mechanics switched off (spec rev. 28 109.2), else ``None``."""
    l1r = settings.get("l1r") or {}
    is_l1r_bundle = l1r.get("rod_side_mechanics_override") not in (None, "off")
    ran_without_l1r = l1r.get("effective_mechanics") == "off"
    is_settlement = settings.get("event") in GROUND_SETTLEMENT_EVENTS
    if is_settlement and is_l1r_bundle and ran_without_l1r:
        return L1R_SUPERSEDED_SOURCE
    return None


def case_metrics(
    case: Mapping[str, Any],
    params,
    reduced: Mapping[str, Any] | None = None,
    event_settings: EventTransientSettings = EVENT_TRANSIENT,
):
    """All per-case quantities used by the checks (JSON-ready).

    ``event_settings``: event-transient windows of the floor-event cases (U57, U58).

    M4 (``verify/l1_scope``, dynamics_model.md 5.15.2): a fast lift-off window holds the
    leg's cylinder quantities before any metric reads them, and the metrics get
    ``outside_L1_scope`` / ``l1_scope_report`` / ``l1_scope_sanity_M1``. Cases without a
    ``settle_velocity.npz`` or without an event are unchanged.
    """
    case, scope = l1_scope.apply_to_case(case, params)
    res = case["result"]
    s = res["settings"]
    tm = _times(case)
    rec = case["rec"]
    t = rec["t"] - tm["t0"]
    rp = _deg(np.array([roll_pitch_from_quat(q) for q in rec["body_quat_wxyz"]]))
    target = np.asarray(s["target_deg"], dtype=float)
    req = res.get("target_request")
    if s.get("event") == "target_change" and req and "code=<TargetCode.ACCEPTED" in req:
        target = np.array([0.0, 3.0])  # G5 change: the accepted new target (0, +3) deg
    err = rp - target
    last5 = t >= tm["end"] - 5.0
    m: dict[str, Any] = {
        "case": res["case"],
        "group": s["group"],
        "level": s["level"],
        "floor": s["floor"],
        "grade": s.get("grade", "ideal"),
        "event": s.get("event"),
        "times_s": tm,
        "phases": res["phases"],
        "final_phase": res["phases"][-1][1],
    }
    m["F_min_N"] = _f_min_from_params(params)
    if scope is not None:
        m["outside_L1_scope"] = scope["outside_L1_scope"]
        m["l1_scope_report"] = scope["report"]
        m["l1_scope_sanity_M1"] = scope["sanity_M1"]
    m["ready_window_ok"] = tm["ready"] is not None and tm["end"] - tm["ready"] >= 5.0
    m["att_err_last5_maxabs_deg"] = float(np.max(np.abs(err[last5]))) if last5.any() else None
    m["att_err_last5_mean_deg"] = err[last5].mean(axis=0).tolist() if last5.any() else None
    if tm["touch"] is not None:  # J2: LEVEL start -> true attitude held inside 0.2 deg
        held = _held_inside_since(t, np.max(np.abs(err), axis=1), tm["touch"], ATT_TOL_DEG)
        m["t_within_0p2_after_level_s"] = None if held is None else held - tm["touch"]
    _force_metrics(case, tm, m)
    window = event_transient_window(case, tm, event_settings)
    if window is not None:
        m["event_window"] = window
    _pressure_and_rocking_metrics(
        case, rec, t, rp, last5, tm, m, window, event_settings, _head_areas_m2(params)
    )
    # final loads, corrective part and twist (item 1)
    proj, n = support_projection(params)
    if last5.any():
        fin = np.asarray(rec["F_cyl"])[last5].mean(axis=0)
        m["final_cyl_kN"] = (fin / 1e3).tolist()
        m["final_corrective_kN"] = (proj @ fin / 1e3).tolist()
        m["final_twist_kN"] = float(n @ fin) / 1e3
    if tm["touch"] is not None and tm["ready"] is not None:
        m["t_ready_minus_touch_s"] = tm["ready"] - tm["touch"]
    _reanchor_attitude(case, t, rp, tm, m)
    # stroke, H4, acceptance, shadow estimate
    m["stroke"] = res.get("stroke")
    m["h4"] = res.get("h4")
    mechanism = h4_mechanism_metrics(case, tm, params)
    if mechanism is not None:
        m["h4_mechanism"] = mechanism
    acc = res.get("acceptance") or {}
    m["target_code"] = acc.get("target_code")
    m["last_check"] = acc.get("last_check")
    fet = acc.get("floor_estimate_touch")
    m["floor_true_deg"] = acc.get("floor_true_deg")
    if fet and fet.get("floor_rad") is not None and acc.get("floor_true_deg") is not None:
        est = _deg(fet["floor_rad"])
        m["shadow_floor_deg"] = est.tolist()
        m["shadow_minus_true_deg"] = (est - np.asarray(acc["floor_true_deg"])).tolist()
        m["shadow_residual_mm"] = (
            None
            if fet.get("residual_m") is None
            else float(np.max(np.abs(fet["residual_m"]))) * 1e3
        )
        m["shadow_floor_usage"] = fet.get("floor_usage")
    if s["group"] == "G5":
        m["target_T"] = _target_metrics(case, rec, t, tm, params, m)
    if s["group"] == "G4":
        m["item6"] = settle_checks(case, m)
    if _is_floor_event_case(m):
        m["event3"] = event_force_metrics(case, tm, window, event_settings, _pad_kn(params))
        m["event_transient_settings"] = event_settings.to_meta()
    if reduced is not None:
        m["reduced"] = reduced
    # spec rev. 28 (111, 112.1, 110.1, 109.2): condition, judge kind, diagnosis, source
    m["contact"] = s.get("contact")
    condition, reasons = case_condition(s)
    m["condition"] = str(condition)
    m["condition_reasons"] = reasons
    m["diagnostic_check"] = diagnostic_false_alarm_metrics(case, s)
    superseded = superseded_by(s)
    if superseded is not None:
        m["superseded_by"] = superseded
    # events summary
    m["events"] = [
        e
        for e in case["events"]
        if any(
            k in e for k in ("REJ", "FAULT", "WARN", "reanchor", "floor_estimate", "IDLE", "probe_")
        )
    ][:40]
    return m


REAR_LEG_INDICES = (2, 3)
FLOOR_FRICTION_KEY = "contact.rigid_floor.friction"


def _first_level_done_s(case: Mapping[str, Any]) -> float | None:
    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    for (_t, p), (t2, p2) in zip(phases[:-1], phases[1:], strict=False):
        if p == "level" and p2 == "done":
            return t2
    return None


def h4_mechanism_metrics(
    case: Mapping[str, Any], tm: Mapping[str, Any], params
) -> dict[str, Any] | None:
    """J6 (dynamics 5.17.3, spec rev. 27 103.1): rear pad floor-plane force T after H4 against
    the mechanism ``mu (P_stop,last + m_rod g)``.

    T is the pad-record sample at the first LEVEL -> DONE (before H4) and at the first READY
    (after it); ``P_stop,last`` the last entry of ``controller_meta.reanchor.stop_force_N``;
    ``mu`` = YAML ``contact.rigid_floor.friction``; ``m_rod`` = ``legs.<leg>.moving_part.
    mass_kg``. None unless the case has a completed REANCHOR, a pad record and both instants.
    """
    from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

    stop_forces = ((case["result"].get("controller_meta") or {}).get("reanchor") or {}).get(
        "stop_force_N")
    pads = case["pads"]
    t_done, t_ready = _first_level_done_s(case), tm["ready"]
    if not stop_forces or pads is None or t_done is None or t_ready is None:
        return None
    tp = pads["t"] - tm["t0"]
    friction = float(params.get(FLOOR_FRICTION_KEY))
    p_stop_N = float(stop_forces[-1])

    def rear_T_kN(at_s: float) -> list[float]:
        i = int(np.clip(np.searchsorted(tp, at_s), 0, len(tp) - 1))
        return [float(pads["T"][i, leg]) / 1e3 for leg in REAR_LEG_INDICES]

    expected_kN = [
        friction * (p_stop_N + params.legs[leg].moving_part.mass_kg * STANDARD_GRAVITY_M_S2) / 1e3
        for leg in REAR_LEG_INDICES
    ]
    t_done_kN, t_ready_kN = rear_T_kN(t_done), rear_T_kN(t_ready)
    return {
        "legs": [LEGS[leg] for leg in REAR_LEG_INDICES],
        "t_done_s": t_done,
        "t_ready_s": t_ready,
        "T_done_kN": t_done_kN,
        "T_ready_kN": t_ready_kN,
        "P_stop_last_kN": p_stop_N / 1e3,
        "friction": friction,
        "expected_kN": expected_kN,
        "ratio": [t / e for t, e in zip(t_ready_kN, expected_kN, strict=True)],
        "reduction_recorded": [1.0 - r / d for r, d in zip(t_ready_kN, t_done_kN, strict=True)],
    }


def _force_metrics(case, tm, m) -> None:
    """Item 3 / 8: 1 ms minimum true cylinder force after lift-off, with and without REANCHOR."""
    pads = case["pads"]
    if pads is None or tm["liftoff"] is None:
        return
    tp = pads["t"] - tm["t0"]
    after = tp >= tm["liftoff"]
    fmin_all = pads["F_cyl_min_interval"]
    fmin = fmin_all[after]
    if not fmin.size:
        return
    k = np.unravel_index(int(np.argmin(fmin)), fmin.shape)
    m["min_cyl_after_liftoff_kN"] = float(fmin[k]) / 1e3
    m["min_cyl_leg"] = LEGS[k[1]]
    m["min_cyl_t_s"] = float(tp[after][k[0]])
    m["pad_N_min_after_liftoff_kN"] = float(pads["N"][after].min()) / 1e3
    in_reanchor = np.zeros(len(tp), dtype=bool)
    for a, b in _phase_windows(case, "reanchor", tm["end"]):
        in_reanchor |= (tp >= a) & (tp <= b)
    outside = after & ~in_reanchor
    inside = after & in_reanchor
    if outside.any():
        m["min_cyl_excl_reanchor_kN"] = float(fmin_all[outside].min()) / 1e3
    if inside.any():
        m["min_cyl_reanchor_kN"] = float(fmin_all[inside].min()) / 1e3


FLOOR_EVENTS = ("settle_RR_30", "drop_RR_30", "drop_RR_30_probe")
EVENT_READY_S = 60.0
"""RE1b family: re-READY within 60 s of the event (ASSUMPTION, spec 23 / 41.2)."""
EVENT_CASE_NOTE = "event case: intended lift-off (spec 41.2/23)"


def _is_floor_event_case(m: Mapping[str, Any]) -> bool:
    return m.get("event") in FLOOR_EVENTS


def _event_time_s(case: Mapping[str, Any], tm: Mapping[str, Any]) -> float | None:
    """``t_event`` of a floor-event case (``result.json`` ``event_t_s``, first READY + 5 s for
    batches without it); ``None`` for every other case."""
    res = case["result"]
    if res["settings"].get("event") not in FLOOR_EVENTS:
        return None
    t_ev = res.get("event_t_s")
    if t_ev is None and tm["ready"] is not None:
        t_ev = tm["ready"] + 5.0
    return None if t_ev is None else float(t_ev)


def _re_ready_s(phases: list[tuple[float, str]], t_ev: float) -> float | None:
    """First READY entry after ``t_ev``; ``t_ev`` itself for a run that never left READY."""
    re_ready = next((t for t, p in phases if t > t_ev and p == "ready"), None)
    if re_ready is None:
        at = [p for t, p in phases if t <= t_ev]
        if at and at[-1] == "ready" and all(p == "ready" for t, p in phases if t > t_ev):
            re_ready = t_ev  # never left READY
    return re_ready


KN_PER_PAD_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"
"""L1 lumped pad contact stiffness: floor point = contact point + (N / k_n) n (dynamics rev. 27)."""


def _rr_last_recontact_s(pads, tp: NDArray[np.float64], t_ev: float) -> tuple[float | None, bool]:
    """(time RR is back in contact for good after the event, whether it ever lifted).

    ``None`` when RR is still lifted at the end of the pad record."""
    after = tp >= t_ev
    lifted = pads["N"][after, 3] <= 0.0
    if not lifted.any():
        return t_ev, False
    last = int(np.flatnonzero(lifted)[-1])
    times = tp[after]
    return (float(times[last + 1]) if last + 1 < len(times) else None), True


def event_transient_window(
    case: Mapping[str, Any],
    tm: Mapping[str, Any],
    settings: EventTransientSettings = EVENT_TRANSIENT,
) -> dict[str, Any] | None:
    """Event-transient window shared by items 3, 4 and 5a of a floor-event case (spec 62.2).

    ``physical``: ``W = [t_event, min(t_RR,last recontact + T_3, t_event + cap)]``; with RR
    still lifted at the end, or the bound reached, the window ends at the cap and the note
    ``transient_window_capped`` is set. ``fixed`` (legacy): 1.0 s for item 3, 2.0 s for
    items 4 / 5a. ``None`` for a case without a floor event.
    """
    t_ev = _event_time_s(case, tm)
    if t_ev is None:
        return None
    phases = [(float(time_s), p) for time_s, p in case["result"]["phases"]]
    level = case["result"]["settings"]["level"]
    window: dict[str, Any] = {"mode": str(settings.transient_window), "start_s": t_ev,
                              "re_ready_s": _re_ready_s(phases, t_ev), "notes": []}
    if settings.transient_window is TransientWindowMode.FIXED:
        window["lift_end_s"] = t_ev + settings.fixed_lift_window_s
        window["pressure_end_s"] = t_ev + settings.fixed_pressure_window_s
        return window
    t3_s = float(settings.three_point_rocking_period_s[level])
    if level != "top":
        window["notes"].append("T3_from_top_level")
    pads = case["pads"]
    recontact_s, rr_lifted = (None, None)
    if pads is not None:
        recontact_s, rr_lifted = _rr_last_recontact_s(pads, pads["t"] - tm["t0"], t_ev)
    cap_end_s = t_ev + settings.transient_window_cap_s
    end_s = cap_end_s if recontact_s is None else min(recontact_s + t3_s, cap_end_s)
    if end_s >= cap_end_s:
        window["notes"].append("transient_window_capped")
    window.update(three_point_rocking_period_s=t3_s, rr_last_recontact_s=recontact_s,
                  rr_lifted=rr_lifted, lift_end_s=end_s, pressure_end_s=end_s)
    return window


def _pad_kn(params) -> NDArray[np.float64] | None:
    """L1 pad stiffness per leg (YAML ``contact.rigid_floor.L1.kn_per_pad_N_m``)."""
    try:
        kn = params.get(KN_PER_PAD_KEY)
    except (AttributeError, KeyError):
        return None
    return np.array([float(kn[leg]) for leg in LEGS])


def _floor_point_heights_m(pads, kn_N_m: NDArray[np.float64]) -> NDArray[np.float64]:
    """(n, 4) pad floor-point height along the floor normal (dynamics rev. 27)."""
    normal = np.asarray(pads["n_world"], dtype=float)
    if normal.ndim == 2:
        normal = np.repeat(normal[:, None, :], 4, axis=1)
    load = np.clip(np.asarray(pads["N"], dtype=float), 0.0, None)
    floor_point = np.asarray(pads["contact_point_world"], dtype=float) + (
        load / kn_N_m
    )[..., None] * normal
    return np.einsum("tij,tij->ti", floor_point, normal)


def _anchor_moves_m(pads, normal_reference, before, inside) -> dict[str, NDArray[np.float64]]:
    """In-plane ground-anchor moves per leg inside the window (spec 62.2 keys).

    ``net_window_end`` = the move of the last anchored sample of the window against the mean
    just before the event (judged), ``max_excursion`` = the largest such move and
    ``path_total`` = the summed in-plane path (both reported). NaN anchor rows (no bushing,
    lifted) are left out; a leg without anchored samples gives NaN.
    """
    anchors = np.asarray(pads["anchor_world"], dtype=float)
    reference = np.nanmean(anchors[before], axis=0)  # (4, 3)
    moves = anchors[inside] - reference
    moves -= (moves @ normal_reference)[..., None] * normal_reference
    out = {name: np.full(4, np.nan) for name in ("net_window_end", "max_excursion", "path_total")}
    for leg in range(4):
        leg_moves = moves[:, leg]
        leg_moves = leg_moves[np.all(np.isfinite(leg_moves), axis=1)]
        if not len(leg_moves):
            continue
        distance = np.linalg.norm(leg_moves, axis=1)
        steps = np.linalg.norm(np.diff(leg_moves, axis=0), axis=1)
        out["net_window_end"][leg] = float(distance[-1])
        out["max_excursion"][leg] = float(distance.max())
        out["path_total"][leg] = float(distance[0] + steps.sum())
    return out


PRE_EVENT_REFERENCE_S = 0.1
"""Item 3: reference of the floor-point height and anchor = mean over this long before the
event."""


def _other_leg_transient_metrics(pads, tp, t_ev, end_s, kn_N_m, out) -> None:
    """J-4: per other leg, lift-off time, floor-point rise and anchor move inside the window."""
    before = (tp >= t_ev - PRE_EVENT_REFERENCE_S) & (tp < t_ev)
    inside = (tp >= t_ev) & (tp <= end_s)
    if not before.any() or not inside.any():
        out["other_leg_geometry"] = "no pad samples before the event or in the window"
        return
    heights = _floor_point_heights_m(pads, kn_N_m)
    rise = heights[inside] - heights[before].mean(axis=0)
    out["other_legs_rise_max_m"] = rise.max(axis=0)[:3].tolist()
    normal = np.asarray(pads["n_world"], dtype=float)
    normal_reference = normal[before].mean(axis=0) if normal.ndim == 2 else np.array([0, 0, 1.0])
    normal_reference = normal_reference / np.linalg.norm(normal_reference)
    moves = _anchor_moves_m(pads, normal_reference, before, inside)
    for name, values in moves.items():
        out[f"other_slip_{name}_m"] = [None if math.isnan(v) else float(v) for v in values[:3]]


def event_force_metrics(
    case: Mapping[str, Any],
    tm: Mapping[str, Any],
    window: Mapping[str, Any] | None = None,
    settings: EventTransientSettings = EVENT_TRANSIENT,
    kn_N_m: NDArray[np.float64] | None = None,
) -> dict[str, Any]:
    """Item 3 of the floor-event cases (spec rev. 7 41.2, control-expert decision (a)).

    ``t_event`` = ``result.json`` ``event_t_s`` (first READY + 5 s for batches without it);
    re-READY = the first READY entry after ``t_event`` (RE1b-P: the event is in the first
    PROBE, so it is the run's first READY; a run that never leaves READY counts ``t_event``).
    Lift-off = true pad normal force <= 0 on the 1 ms pad record, time = samples x interval.
    J-4 (U57, spec 62.2): the other legs are judged per leg inside ``window`` (lift-off time,
    floor-point rise, anchor move; ``kn_N_m`` = L1 pad stiffness per leg) and must stay down
    after it.
    """
    res = case["result"]
    pads = case["pads"]
    out: dict[str, Any] = {}
    t_ev = _event_time_s(case, tm)
    out["t_event_s"] = t_ev
    if pads is None or t_ev is None or tm["liftoff"] is None:
        out["status"] = "no pad record, event or crawler lift-off"
        return out
    if window is None:
        window = event_transient_window(case, tm, settings)
    phases = [(float(t), p) for t, p in res["phases"]]
    re_ready = _re_ready_s(phases, t_ev)
    out["re_ready_s"] = re_ready
    out["re_ready_after_event_s"] = None if re_ready is None else re_ready - t_ev
    tp = pads["t"] - tm["t0"]
    dt = np.diff(tp, append=tp[-1] + (tp[-1] - tp[-2] if len(tp) > 1 else 0.0))
    fmin = pads["F_cyl_min_interval"]
    lifted = pads["N"] <= 0.0
    before = (tp >= tm["liftoff"]) & (tp < t_ev)
    out["min_cyl_before_event_kN"] = float(fmin[before].min()) / 1e3 if before.any() else None
    after_ev = tp >= t_ev
    other_lifted_s = dt[:, None] * lifted[:, :3]
    out["other_legs_lifted_s"] = float(other_lifted_s[after_ev].sum())
    out["other_legs_lifted_per_leg_s"] = other_lifted_s[after_ev].sum(axis=0).tolist()
    end_s = window["lift_end_s"]
    in_window = after_ev & (tp <= end_s)
    out["transient_window"] = dict(window)
    out["other_lift_limits"] = {"lift_s": settings.other_lift_allow_s,
                                "rise_m": settings.other_lift_height_allow_m,
                                "anchor_move_m": settings.other_slip_allow_m}
    out["other_legs_lifted_transient_per_leg_s"] = other_lifted_s[in_window].sum(axis=0).tolist()
    out["other_legs_lifted_after_transient_s"] = float(other_lifted_s[tp > end_s].sum())
    if kn_N_m is not None:
        _other_leg_transient_metrics(pads, tp, t_ev, end_s, kn_N_m, out)
    if re_ready is not None:
        tail = tp >= re_ready
        out["min_cyl_after_re_ready_kN"] = float(fmin[tail].min()) / 1e3 if tail.any() else None
        out["rr_lifted_after_re_ready_s"] = float(np.sum(dt[tail] * lifted[tail, 3]))
        span = (tp >= t_ev) & (tp < re_ready)
        rr = float(np.sum(dt[span] * lifted[span, 3]))
        out["rr_lifted_event_to_re_ready_s"] = rr
        out["rr_lifted_ratio"] = rr / (re_ready - t_ev) if re_ready > t_ev else None
    else:
        out["min_cyl_after_re_ready_kN"] = None
        out["rr_lifted_after_re_ready_s"] = None
        rr = float(np.sum(dt[after_ev] * lifted[after_ev, 3]))
        out["rr_lifted_event_to_re_ready_s"] = rr
        out["rr_lifted_ratio"] = None
    return out


def _within(value: float | None, limit: float) -> bool | None:
    return None if value is None else value <= limit


def _other_legs_lift_rows(rows: _Rows, e: Mapping[str, Any], cid: str) -> None:
    """J-4 (U57, spec 62.2): inside the transient window each other leg may lift briefly
    (total time, floor-point rise, anchor move within the limits); after it none may lift.
    Event blocks without the window keep the former single row."""
    per_leg = f"FL FR RL [s] {e['other_legs_lifted_per_leg_s']}"
    if "transient_window" not in e:
        rows.add("3 lift-off other legs after the event", cid, e["other_legs_lifted_s"], 0.0,
                 e["other_legs_lifted_s"] == 0.0, note=per_leg)
        return
    window = e["transient_window"]
    limits = e["other_lift_limits"]
    lift_s = e["other_legs_lifted_transient_per_leg_s"]
    rise_m = e.get("other_legs_rise_max_m")
    move_m = e.get("other_slip_net_window_end_m")
    verdicts = [max(lift_s) <= limits["lift_s"]]
    if rise_m is not None:
        verdicts.append(max(rise_m) <= limits["rise_m"])
    if move_m is not None:
        verdicts.extend(v is None or v <= limits["anchor_move_m"] for v in move_m)
    missing = "" if rise_m is not None and move_m is not None else (
        "; rise / anchor move not measured (no pad geometry): lift time only")
    notes = ", ".join(window.get("notes") or []) or "-"
    window_text = f"[{window['start_s']:.3f}, {window['lift_end_s']:.3f}] s"
    rows.add("3 lift-off other legs in the event transient", cid,
             {"lift_s": lift_s, "rise_m": rise_m, "anchor_move_m": move_m,
              "anchor_max_excursion_m": e.get("other_slip_max_excursion_m"),
              "anchor_path_total_m": e.get("other_slip_path_total_m")}, limits,
             all(verdicts),
             note=f"U57 (spec 62.2), {window['mode']} window {window_text}, notes {notes}; "
                  f"FL FR RL{missing}")
    after = e["other_legs_lifted_after_transient_s"]
    rows.add("3 lift-off other legs after the transient", cid, after, 0.0, after == 0.0,
             note=f"U57: window end .. case end; whole run after the event: {per_leg}")


def _event_item3_rows(rows: _Rows, m, cid: str) -> None:
    """Judged item-3 rows of a floor-event case (decision (a))."""
    e = m.get("event3")
    if not e or "status" in e:
        return
    f_min = _f_min_N(m) / 1e3
    v = e["min_cyl_before_event_kN"]
    rows.add("3 F_min before the event", cid, v, f_min, None if v is None else v >= f_min,
             note="crawler lift-off .. t_event")
    v = e["min_cyl_after_re_ready_kN"]
    rows.add("3 F_min after the re-READY", cid, v, f_min, None if v is None else v >= f_min,
             note="re-READY .. end" if e["re_ready_s"] is not None
             else "no re-READY: not judged here (failed in the re-READY row)")
    _other_legs_lift_rows(rows, e, cid)
    v = e["rr_lifted_after_re_ready_s"]
    rows.add("3 lift-off RR after the re-READY", cid, v, 0.0, None if v is None else v == 0.0,
             note="" if v is not None else "no re-READY: not judged here")
    rr, ratio = e["rr_lifted_event_to_re_ready_s"], e["rr_lifted_ratio"]
    no_show = rr == 0.0 and m.get("event") in ("drop_RR_30", "drop_RR_30_probe")
    rows.add("3 lift-off RR time / ratio (report)", cid, [rr, ratio], None, None,
             note="사건 미발현" if no_show else "t_event .. re-READY")
    v = e["re_ready_after_event_s"]
    rows.add("RE1b re-READY <= 60 s", cid, v, EVENT_READY_S,
             False if v is None else v <= EVENT_READY_S,
             note="no re-READY before the run end: failed" if v is None else "")


ROCKING_WINDOW_S = 1.0
"""Item 5a: moving-mean window of the rocking amplitude in seconds (spec rev. 32 163.2 C-R4:
``round(1.0 s x record rate)`` samples, 50 at the 50 Hz Record, 10 at the 10 Hz bundle-C
Record)."""
ROCKING_WINDOW_SAMPLES = 50
"""Item 5a fallback window when no time vector is given (1 s at the 50 Hz Record)."""


def record_rate_hz(t_s: NDArray[np.float64] | None) -> float | None:
    """Sample rate of a Record time vector (median spacing), None for fewer than 2 samples."""
    if t_s is None or len(t_s) < 2:
        return None
    dt = float(np.median(np.diff(np.asarray(t_s, dtype=float))))
    return 1.0 / dt if dt > 0.0 else None


def rocking_window_samples(t_s: NDArray[np.float64] | None) -> int:
    """C-R4: ``round(ROCKING_WINDOW_S x record rate)`` (at least 2), the legacy 50 samples when
    the rate is unknown."""
    rate = record_rate_hz(t_s)
    if rate is None:
        return ROCKING_WINDOW_SAMPLES
    return max(2, int(round(ROCKING_WINDOW_S * rate)))


def _rocking_amp_deg(attitude_deg: NDArray[np.float64],
                     t_s: NDArray[np.float64] | None = None) -> float | None:
    """Largest deviation of roll / pitch from their 1 s moving mean (edges dropped); the window
    in samples follows the rate of ``t_s`` (:func:`rocking_window_samples`)."""
    win = rocking_window_samples(t_s)
    if len(attitude_deg) <= 2 * win:
        return None
    kern = np.ones(win) / win
    mov = np.column_stack([np.convolve(attitude_deg[:, i], kern, mode="same") for i in range(2)])
    return float(np.max(np.abs((attitude_deg - mov)[win : len(attitude_deg) - win])))


HEAD_AREA_M2 = math.pi / 4.0 * 0.115**2
"""Items 4 / 5: head area of the pressure basis ``F_cyl / A_p`` when the case parameters give
none (YAML bore 115 mm)."""


def _head_areas_m2(params) -> NDArray[np.float64]:
    """Items 4 / 5 per leg (spec 64.2: 180 bar x A_p = 238.9 / 171.1 kN with REXOME35): the
    run's own YAML areas (``legs.<leg>.cylinder.*`` or the common bore), the 115 mm area for a
    parameter object without them."""
    from outrigger_sim.params import ParamsError
    from outrigger_sim.sensors.hydraulic import leg_head_areas_from_params

    try:
        return leg_head_areas_from_params(params)
    except (ParamsError, AttributeError, TypeError):
        return np.full(4, HEAD_AREA_M2)


def _motion_state(applied_m_s: float) -> str:
    if applied_m_s > 0.0:
        return "extend"
    if applied_m_s < 0.0:
        return "retract"
    return "locked"


def _transient_peak(case, tm, t, applied, window_s, head_area_m2) -> dict[str, Any] | None:
    """Item 4 inside the window: largest head ``F_cyl / A_p`` in any state, with its leg, time
    and motion state (1 ms pad record when present, else the 50 Hz Record)."""
    start_s, end_s = window_s
    pads = case["pads"]
    if pads is not None:
        times = pads["t"] - tm["t0"]
        forces = np.asarray(pads["F_cyl"])
    else:
        times, forces = t, np.asarray(case["rec"]["F_cyl"])
    inside = (times >= start_s) & (times <= end_s)
    if not inside.any():
        return None
    p_bar = forces[inside] / head_area_m2 / 1e5
    sample, leg = np.unravel_index(int(np.argmax(p_bar)), p_bar.shape)
    t_peak = float(times[inside][sample])
    record_index = min(int(np.searchsorted(t, t_peak)), len(t) - 1)
    return {"max_bar": float(p_bar[sample, leg]), "leg": LEGS[leg], "t_s": t_peak,
            "state": _motion_state(float(applied[record_index, leg])),
            "source": "pads 1 ms" if pads is not None else "Record 50 Hz"}


def _event_transient_metrics(
    case, tm, m, t, rp, p_bar, applied, window, settings, head_area_m2
) -> None:
    """J-5 (U58, spec 62.2): items 4 and 5a of a floor-event case around its transient window.

    Outside the window the 180 bar check judges the extension samples (``extend_only``) and
    reports the retraction samples; inside it the head ``F / A_p`` of every state is judged
    against the locked limit (no ``F - m_rod a``). Item 5a is judged after the re-READY; the
    amplitude inside the window is reported.
    """
    start_s, end_s = window["start_s"], window["pressure_end_s"]
    in_window = (t >= start_s) & (t <= end_s)
    outside = ~in_window[:, None]
    extending = applied > 0.0
    retracting = applied < 0.0
    if settings.moving_pressure_samples is MovingPressureSamples.EXTEND_ONLY:
        judged = outside & extending
    else:
        judged = outside & (extending | retracting)
    m["event_pressure_window_s"] = [start_s, end_s]
    m["moving_pressure_samples"] = str(settings.moving_pressure_samples)
    m["transient_pressure_limit_bar"] = settings.transient_pressure_limit_bar
    m["max_moving_pressure_excl_transient_bar"] = (
        float(p_bar[judged].max()) if judged.any() else None
    )
    retract_outside = outside & retracting
    m["max_retract_pressure_excl_transient_bar"] = (
        float(p_bar[retract_outside].max()) if retract_outside.any() else None
    )
    m["transient_pressure_peak"] = _transient_peak(
        case, tm, t, applied, (start_s, end_s), head_area_m2
    )
    m["max_pressure_transient_bar"] = (
        None if m["transient_pressure_peak"] is None else m["transient_pressure_peak"]["max_bar"]
    )
    m["rocking_amp_transient_deg"] = _rocking_amp_deg(rp[in_window], t)
    re_ready = window["re_ready_s"]
    m["re_ready_s"] = re_ready
    if re_ready is not None:
        m["rocking_amp_after_re_ready_deg"] = _rocking_amp_deg(rp[t >= re_ready], t)


def _pressure_and_rocking_metrics(
    case,
    rec,
    t,
    rp,
    last5,
    tm,
    m,
    window=None,
    settings: EventTransientSettings = EVENT_TRANSIENT,
    head_area_m2: NDArray[np.float64] | None = None,
) -> None:
    """Items 4, 5 and the item 2 sensor path (I5); ``window`` = :func:`event_transient_window`
    of a floor-event case (``None`` otherwise)."""
    mon = case["result"]["monitor"]
    area = np.full(4, HEAD_AREA_M2) if head_area_m2 is None else np.asarray(head_area_m2)
    applied = np.asarray(rec["u_applied"])
    moving = applied != 0.0
    p_bar = np.asarray(rec["F_cyl"]) / area / 1e5
    m["max_moving_pressure_bar"] = float(p_bar[moving].max()) if moving.any() else None
    m["max_pressure_any_step_bar"] = float(
        np.max(np.asarray(mon["cylinder_force_max_N"], dtype=float) / area)
    ) / 1e5
    m["saturation_steps"] = int(sum(mon["saturation_step_count"]))
    m["record_rate_hz"] = record_rate_hz(t)
    m["rocking_window_samples"] = rocking_window_samples(t)
    if tm["liftoff"] is not None:
        amplitude = _rocking_amp_deg(rp[t >= tm["liftoff"]], t)
        if amplitude is not None:
            m["rocking_amp_deg"] = amplitude
    if window is not None:
        _event_transient_metrics(case, tm, m, t, rp, p_bar, applied, window, settings, area)
    filt = _filter_tilt_deg(rec)
    if last5.sum() > 60:
        fl = filt[last5]
        kern = np.ones(50) / 50
        mov = np.column_stack([np.convolve(fl[:, i], kern, mode="same") for i in range(2)])
        m["filter_residual_last5_deg"] = float(np.max(np.abs((fl - mov)[25:-25])))
        f = np.asarray(rec["meas.specific_force"])
        raw = _deg(np.column_stack(roll_pitch_from_specific_force(f)))[last5]
        mov_r = np.column_stack([np.convolve(raw[:, i], kern, mode="same") for i in range(2)])
        true_last5 = rp[last5]
        mov_t = np.column_stack(
            [np.convolve(true_last5[:, i], kern, mode="same") for i in range(2)]
        )
        m["imu_apparent_amp_last5_deg"] = float(np.max(np.abs((raw - mov_r)[25:-25])))
        m["true_amp_last5_deg"] = float(np.max(np.abs((true_last5 - mov_t)[25:-25])))
        # I5: (IMU filter attitude - true attitude) over the last 5 s against the grade tilt
        m["imu_minus_true_last5_deg"] = (fl - true_last5).mean(axis=0).tolist()
        m["grade_tilt_deg"] = list(_grade_tilt_deg(m["grade"]))


def _reanchor_attitude(case, t, rp, tm, m) -> None:
    """I2: true attitude change during REANCHOR (vs the 0.5 s mean before each window)."""
    windows = _phase_windows(case, "reanchor", tm["end"])
    if not windows:
        return
    change = 0.0
    for a, b in windows:
        pre = (t >= a - 0.5) & (t < a)
        inside = (t >= a) & (t <= b)
        if pre.any() and inside.any():
            change = max(change, float(np.max(np.abs(rp[inside] - rp[pre].mean(axis=0)))))
    m["reanchor_att_change_max_deg"] = change


T1_STILL_TRAVEL_M = 1.0e-6
"""T1 (spec 41.1, rev. 27 102.2): largest motor travel that counts as "no motion"."""
T1_CALIBRATION_EXCURSION_M = 0.0035
"""Spec rev. 27 102.2 (c): U71 airborne round trip of 3.0 mm + 0.5 mm, largest leg excursion
from the CHECK start inside CHECK."""
T1_CALIBRATION_NET_M = 0.0001
"""Spec rev. 27 102.2 (c): largest net leg displacement at the CHECK end."""


def _zero_calibration_active(case: Mapping[str, Any]) -> bool:
    """U71 zero calibration on in the run (controller meta, else the case settings)."""
    meta = (case["result"].get("controller_meta") or {}).get("zero_calibration")
    if meta is not None and "is_active" in meta:
        return bool(meta["is_active"])
    return bool(case["result"]["settings"].get("zero_calibration"))


def reject_motion_metrics(
    t: NDArray[np.float64],
    s_motor: NDArray[np.float64],
    check_end_s: float,
    calibration_active: bool,
) -> dict[str, Any]:
    """T1 reject motion split at the CHECK end (spec rev. 27 102.2).

    Args:
        t: Record times (case-relative, s).
        s_motor: Motor positions (n, 4), m.
        check_end_s: End of the first CHECK phase (case-relative, s).
        calibration_active: U71 calibration on; off -> CHECK must be still too.

    Returns:
        ``travel_after_check_m`` (largest per-leg peak-to-peak from the CHECK end on),
        ``check_excursion_m`` (largest per-leg excursion from the first sample inside CHECK),
        ``check_net_m`` (largest per-leg ``|s(CHECK end) - s(start)|``), ``check_travel_m``
        (largest per-leg peak-to-peak inside CHECK), ``check_end_s`` and
        ``calibration_active``.
    """
    inside = t <= check_end_s
    after = t >= check_end_s
    start = s_motor[0]
    end_index = int(np.flatnonzero(after)[0]) if after.any() else len(t) - 1
    within = s_motor[inside] if inside.any() else s_motor[:1]
    return {
        "check_end_s": float(check_end_s),
        "calibration_active": calibration_active,
        "travel_after_check_m": float(np.max(np.ptp(s_motor[after], axis=0)))
        if after.any() else 0.0,
        "check_excursion_m": float(np.max(np.abs(within - start))),
        "check_net_m": float(np.max(np.abs(s_motor[end_index] - start))),
        "check_travel_m": float(np.max(np.ptp(within, axis=0))),
    }


def t1_reject_passed(final_phase: str, row: Mapping[str, Any]) -> bool:
    """T1 (spec rev. 27 102.2): IDLE, still after CHECK, and inside CHECK only the U71 round
    trip (or still when the calibration is off). Rows without the CHECK split (older metrics)
    keep the former whole-run rule."""
    if final_phase != "idle":
        return False
    if "travel_after_check_m" not in row:
        return row["motor_travel_m"] < T1_STILL_TRAVEL_M
    if row["travel_after_check_m"] >= T1_STILL_TRAVEL_M:
        return False
    if not row["calibration_active"]:
        return row["check_travel_m"] < T1_STILL_TRAVEL_M
    return (row["check_excursion_m"] <= T1_CALIBRATION_EXCURSION_M
            and row["check_net_m"] <= T1_CALIBRATION_NET_M)


def _target_metrics(case, rec, t, tm, params, m) -> dict[str, Any]:
    """T1-T3 of a G5 case (I1, I4, J3)."""
    s_motor = np.asarray(rec["s_motor"])
    cid = m["case"]
    row: dict[str, Any] = {"stroke_max_m": float(s_motor.max())}
    if "reject" in cid:
        row["motor_travel_m"] = float(np.max(np.ptp(s_motor, axis=0)))
        check_windows = _phase_windows(case, "check", tm["end"])
        if check_windows:
            row.update(reject_motion_metrics(
                t, s_motor, check_windows[0][1], _zero_calibration_active(case)))
        return row
    if "change" not in cid:
        return row
    phases = [(float(time_s), p) for time_s, p in case["result"]["phases"]]
    t_req = (tm["ready"] or 0.0) + 2.0
    re_ready = next((ts for ts, p in phases if ts > t_req + 0.1 and p == "ready"), None)
    row["change_to_ready_s"] = None if re_ready is None else re_ready - t_req
    row["t_change_s"] = t_req
    row["run_after_change_s"] = tm["end"] - t_req
    breakdown: dict[str, float] = {"ramp_level_s": 0.0, "reanchor_s": 0.0, "probe_s": 0.0}
    end = re_ready if re_ready is not None else tm["end"]
    for (t1, p), nxt in zip(phases, [*phases[1:], (tm["end"], "end")], strict=True):
        a, b = max(t1, t_req), min(nxt[0], end)
        if b <= a:
            continue
        key = {"reanchor": "reanchor_s", "probe": "probe_s"}.get(p, "ramp_level_s")
        breakdown[key] += b - a
    row["breakdown_s"] = breakdown
    row["reanchor_after_change"] = any(
        name == "reanchor_started" and ts >= t_req for ts, name in _events(case)
    )
    floor_plane = case["result"].get("floor_plane")
    row["crawler_clearance_min_m"] = _crawler_clearance_min_m(rec, t, t_req, params, floor_plane)
    return row


class EventClass(StrEnum):
    """Where a probe round or window lies against the floor event (U53, spec 55.1)."""

    PRE = "pre"
    OVERLAP = "overlap"
    """Overlaps the event (also a round cut by it): reported only, kind info."""
    POST = "post"


def _event_class(start_s: float, end_s: float, t_event_s: float | None) -> EventClass | None:
    """``None`` for a case without a floor event."""
    if t_event_s is None:
        return None
    if end_s < t_event_s:
        return EventClass.PRE
    if start_s >= t_event_s:
        return EventClass.POST
    return EventClass.OVERLAP


def _round_intervals(case: Mapping[str, Any], end_s: float) -> list[tuple[float, float]]:
    """(start, end) of the PROBE interval of every stored probe round, oldest first.

    ``result.json`` ``probe_intervals`` tells which PROBE intervals completed a round (a
    round cut by a re-level is not stored); batches without it fall back to the PROBE phase
    windows in order.
    """
    intervals = case["result"].get("probe_intervals")
    if intervals is None:
        return _phase_windows(case, "probe", end_s)
    out = []
    for interval in intervals:
        start_s = float(interval["t_start_s"])
        stop_s = float(interval["t_end_s"]) if interval.get("t_end_s") is not None else end_s
        out.extend([(start_s, stop_s)] * int(interval.get("rounds_completed") or 0))
    return out


def _runs_of(mask: NDArray[np.bool_]) -> list[tuple[int, int]]:
    """(first, last) index of every run of True values."""
    edges = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1, strict=True))


def _leg_times_from_commands(
    t: NDArray[np.float64],
    leg_command: NDArray[np.float64],
    window_s: tuple[float, float],
    hold_s: float,
    period_s: float,
) -> tuple[float, float, float] | None:
    """Probe timing of one leg rebuilt from the Record commands (batches before J-0).

    The two moves are the first two same-sign runs of nonzero commands inside the round's
    PROBE interval; each hold ends ``period + hold_s`` after the last command of its move (the
    probe sequencer rule), so the times carry the Record sampling, not an equal split.
    """
    a, b = window_s
    inside = (t >= a) & (t <= b)
    moves = []
    for sign in (1.0, -1.0):
        moves.extend(_runs_of(inside & (np.sign(leg_command) == sign)))
    moves.sort()
    if len(moves) < 2:
        return None
    (first_start, first_end), (_, second_end) = moves[0], moves[1]
    return (
        float(t[first_start]),
        float(t[first_end]) + period_s + hold_s,
        float(t[second_end]) + period_s + hold_s,
    )


def _leg_probe_times(
    result: Mapping[str, Any], t0: float, rebuild
) -> tuple[tuple[float, float, float] | None, str]:
    """Case-relative (move start, first hold end, second hold end) and their source."""
    names = ("t_move_start_s", "t_first_hold_end_s", "t_second_hold_end_s")
    values = [result.get(name) for name in names]
    if all(isinstance(v, int | float) and math.isfinite(v) for v in values):
        start_s, first_s, second_s = (float(v) - t0 for v in values)
        return (start_s, first_s, second_s), "controller (J-0)"
    return rebuild(), "record u_cmd (rebuilt)"


def _mean_near(t: NDArray[np.float64], values: NDArray[np.float64], at_s: float) -> float | None:
    sel = np.abs(t - at_s) <= PROBE_TRUTH_HALF_WINDOW_S
    return float(values[sel].mean()) if sel.any() else None


@dataclass(frozen=True)
class LegProbeTruth:
    """Truth of one leg's own probe (U53, spec rev. 27 102.1)."""

    grounded: bool | None
    """True pad normal force > 0 from the first move start to the second hold end."""
    start_load_N: float | None
    """7c truth: mean true cylinder force over the 0.5 s before the first move start."""
    midpoint_load_N: float | None
    """Former 7c truth (spec 55.1), recorded: midpoint of the hold-end means."""


def _kN_or_none(value_N: float | None) -> float | None:
    return None if value_N is None else value_N / 1e3


def _mean_before(t: NDArray[np.float64], values: NDArray[np.float64], at_s: float) -> float | None:
    sel = (t >= at_s - PROBE_START_LOAD_WINDOW_S) & (t < at_s)
    return float(values[sel].mean()) if sel.any() else None


def _leg_truth(
    pads: Mapping[str, NDArray] | None,
    tp: NDArray[np.float64],
    leg: int,
    times_s: tuple[float, float, float] | None,
    fallback_window_s: tuple[float, float],
) -> LegProbeTruth:
    """U53 / spec rev. 27 102.1: grounded and load truth of one leg's own probe.

    A leg without probe times (skipped) takes the grounded truth over the round interval and
    no load truth.
    """
    if pads is None:
        return LegProbeTruth(None, None, None)
    start_s, end_s = fallback_window_s if times_s is None else (times_s[0], times_s[2])
    span = (tp >= start_s) & (tp <= end_s)
    grounded = bool(np.min(pads["N"][span, leg]) > 0.0) if span.any() else None
    if times_s is None:
        return LegProbeTruth(grounded, None, None)
    cylinder_force = pads["F_cyl"][:, leg]
    first = _mean_near(tp, cylinder_force, times_s[1])
    second = _mean_near(tp, cylinder_force, times_s[2])
    midpoint = None if first is None or second is None else 0.5 * (first + second)
    return LegProbeTruth(grounded, _mean_before(tp, cylinder_force, times_s[0]), midpoint)


def _probe_window_attitude_changes(
    t, rp, windows, t_event_s
) -> list[dict[str, Any]]:
    """Item 7a per PROBE window: largest true attitude change against the 0.5 s mean before."""
    out = []
    for a, b in windows:
        pre = (t >= a - 0.5) & (t < a)
        inw = (t >= a) & (t <= b)
        change = None
        if pre.any() and inw.any():
            change = float(np.max(np.abs(rp[inw] - rp[pre].mean(axis=0))))
        event_class = _event_class(a, b, t_event_s)
        out.append({"window_s": [a, b], "att_change_deg": change,
                    "event_class": None if event_class is None else str(event_class)})
    return out


def _load_error_kN(row: Mapping[str, Any]) -> float:
    """7c error of one row against its limit (<= 0 passes).

    Two-sided ``|estimate - truth| - max(5 kN, 10 %)``; a leg with the zero-calibration
    deduction (E-6, spec 76.2) only on the dangerous side, ``estimate - truth - limit``
    (spec rev. 27 102.1: its low bias is by design).
    """
    error = row["load_estimate_kN"] - row["truth_cyl_kN"]
    limit = max(5.0, 0.1 * abs(row["truth_cyl_kN"]))
    if row.get("zero_cal_deduction"):
        return error - limit
    return abs(error) - limit


def _load_error_margin_kN(rows: list[dict[str, Any]]) -> float | None:
    errs = [
        _load_error_kN(r) for r in rows if r["truth_cyl_kN"] is not None and not r["is_skipped"]
    ]
    return max(errs) if errs else None


def _verdict_match(rows: list[dict[str, Any]]) -> bool | None:
    judged = [r for r in rows if r["truth_grounded"] is not None]
    if not judged:
        return None
    return all(r["is_grounded"] == r["truth_grounded"] for r in judged)


def _summarise_probe_rows(out: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """7b / 7c over the rounds that do not overlap the event; the overlap rounds apart."""
    judged = [r for r in rows if r["event_class"] != EventClass.OVERLAP]
    overlap = [r for r in rows if r["event_class"] == EventClass.OVERLAP]
    if judged:
        out["verdict_match"] = _verdict_match(judged)
        out["load_error_margin_kN"] = _load_error_margin_kN(judged)
    if overlap:
        out["overlap_verdict_match"] = _verdict_match(overlap)
        out["overlap_load_error_margin_kN"] = _load_error_margin_kN(overlap)


def probe_metrics(case: Mapping[str, Any]) -> dict[str, Any]:
    """Item 7: attitude change during probes, verdict vs truth, load estimate error.

    U53 / J-1 (spec 55.1): the truth is taken per round and per leg over that leg's own probe
    interval (controller times of J-0, or rebuilt from the Record commands for older batches).
    In a floor-event case each round and PROBE window is ``pre`` / ``overlap`` / ``post`` the
    event; ``overlap`` ones are reported apart and left out of 7a-7c.
    """
    tm = _times(case)
    windows = _phase_windows(case, "probe", tm["end"])
    rec = case["rec"]
    t = rec["t"] - tm["t0"]
    rp = _deg(np.array([roll_pitch_from_quat(q) for q in rec["body_quat_wxyz"]]))
    t_event_s = _event_time_s(case, tm)
    out: dict[str, Any] = {"windows_s": windows, "rounds": len(case["probes"]),
                           "t_event_s": t_event_s}
    if not windows:
        return out
    per_window = _probe_window_attitude_changes(t, rp, windows, t_event_s)
    out["windows"] = per_window
    judged = [w["att_change_deg"] for w in per_window
              if w["event_class"] != EventClass.OVERLAP and w["att_change_deg"] is not None]
    overlap = [w["att_change_deg"] for w in per_window
               if w["event_class"] == EventClass.OVERLAP and w["att_change_deg"] is not None]
    out["att_change_max_deg"] = max(judged) if judged else None
    if overlap:
        out["att_change_overlap_max_deg"] = max(overlap)
    deduction_legs = zero_cal_deduction_legs(case)
    out["legs"] = _probe_leg_rows(case, tm, t, t_event_s, deduction_legs)
    _summarise_probe_rows(out, out["legs"])
    if deduction_legs:
        out["zero_cal_deduction_warning_event"] = deduction_legs
    return out


ZERO_CAL_WARNING_PREFIXES = ("WARN_PRESSURE_ZERO_IMPLAUSIBLE:", "WARN_PRESSURE_ZERO_SKIPPED:")
ZERO_CAL_SKIPPED_ALL = "WARN_PRESSURE_ZERO_SKIPPED:all:"
"""``zero_calibration.events``: per-leg warnings and the one for every leg (no CHECK)."""


def _has_zero_cal_warning(event_names: list[str], leg: str) -> bool:
    for name in event_names:
        if name.startswith(ZERO_CAL_SKIPPED_ALL):
            return True
        for prefix in ZERO_CAL_WARNING_PREFIXES:
            if name.startswith(prefix) and name[len(prefix):].split(":")[0] == leg:
                return True
    return False


def zero_cal_deduction_legs(case: Mapping[str, Any]) -> dict[str, bool]:
    """Legs with the zero-calibration deduction (E-6, spec 76.2) -> whether the case has the
    leg's ``WARN_PRESSURE_ZERO_IMPLAUSIBLE`` / ``..._SKIPPED`` event (spec rev. 27 102.1).

    A deduction leg is one whose ``controller_meta.zero_calibration.result.legs.<leg>``
    ``allowance_N`` is above 0. Empty for cases without the calibration meta.
    """
    meta = (case["result"].get("controller_meta") or {}).get("zero_calibration") or {}
    legs = (meta.get("result") or {}).get("legs") or {}
    event_names = [name for _t, name in _events(case)]
    out = {}
    for leg in LEGS:
        allowance_N = (legs.get(leg) or {}).get("allowance_N") or 0.0
        if allowance_N > 0.0:
            out[leg] = _has_zero_cal_warning(event_names, leg)
    return out


def _probe_leg_rows(case, tm, t, t_event_s, deduction_legs) -> list[dict[str, Any]]:
    """One row per stored probe result (round, leg) with its own truth."""
    pads = case["pads"]
    tp = None if pads is None else pads["t"] - tm["t0"]
    probe_meta = (case["result"].get("controller_meta") or {}).get("probe") or {}
    hold_s = float(probe_meta.get("hold_s", 0.4))
    period_s = float((case["result"].get("controller_meta") or {}).get("period_s", 0.02))
    commands = np.asarray(case["rec"]["u_cmd"])
    intervals = _round_intervals(case, tm["end"])
    rows = []
    for round_index, rnd in enumerate(case["probes"]):
        window = intervals[round_index] if round_index < len(intervals) else (0.0, tm["end"])
        legs = [r for r in rnd if isinstance(r, dict)]
        timed = []
        for r in legs:
            leg = int(r["leg_index"])

            def rebuild(leg=leg, window=window):
                return _leg_times_from_commands(t, commands[:, leg], window, hold_s, period_s)

            times_s, source = _leg_probe_times(r, tm["t0"], rebuild)
            timed.append((r, leg, times_s, source))
        span = [x for _, _, times_s, _ in timed if times_s is not None for x in times_s]
        round_span = (min(span), max(span)) if span else window
        event_class = _event_class(*round_span, t_event_s)
        for r, leg, times_s, source in timed:
            truth = LegProbeTruth(None, None, None) if tp is None else _leg_truth(
                pads, tp, leg, times_s, window)
            rows.append(
                {
                    "round": round_index,
                    "leg": LEGS[leg],
                    "is_grounded": r.get("is_grounded"),
                    "truth_grounded": truth.grounded,
                    "attitude_response_ratio": r.get("attitude_response_ratio"),
                    "load_estimate_kN": float(r["load_estimate_N"]) / 1e3,
                    "truth_cyl_kN": _kN_or_none(truth.start_load_N),
                    "truth_midpoint_kN": _kN_or_none(truth.midpoint_load_N),
                    "zero_cal_deduction": LEGS[leg] in deduction_legs,
                    "seal_friction_estimate_kN": float(r.get("seal_friction_estimate_N", math.nan))
                    / 1e3,
                    "is_skipped": r.get("is_skipped", False),
                    "probe_times_s": None if times_s is None else list(times_s),
                    "timing_source": source,
                    "event_class": None if event_class is None else str(event_class),
                }
            )
    return rows


# --- judgement rows ----------------------------------------------------------------------------


class _Rows:
    """Row collector (item, case, value, limit, passed, note, kind)."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, item, case, value, limit, passed, note="", kind="function"):
        self.rows.append(
            {
                "item": item,
                "case": case,
                "value": value,
                "limit": limit,
                "passed": bool(passed) if passed is not None else None,
                "note": note,
                "kind": kind,
            }
        )


def _item1_rows(rows: _Rows, m, cid: str) -> None:
    red = m["reduced"]
    chrono_s = m.get("t_within_0p2_after_level_s")
    ref_s = red.get("t_within_0p2_after_level_s")
    source = "reduced reference"
    if ref_s is None:
        ref_s = REDUCED_LEVEL_TIME_FALLBACK_S.get(m["floor"])
        source = "spec 16.2 table (reduced reference lacks t_within_0p2_after_level_s)"
    if chrono_s is not None and ref_s is not None:
        rows.add(
            "1a LEVEL -> held in 0.2 deg",
            cid,
            chrono_s,
            f"{ref_s} +-10 %",
            abs(chrono_s - ref_s) <= LEVEL_TIME_TOL * ref_s,
            note=f"J2; {source}",
        )
    else:
        rows.add(
            "1a LEVEL -> held in 0.2 deg",
            cid,
            chrono_s,
            "+-10 %",
            None,
            note="J2: no reduced reference for this floor",
        )
    tr = m.get("t_ready_minus_touch_s")
    rows.add(
        "1a touch -> READY (report)",
        cid,
        tr,
        red.get("t_level_after_touch_s"),
        None,
        note="J2: reported only (sensitive to the 0.03 deg completion dead band)",
    )
    if m.get("min_cyl_after_liftoff_kN") is not None and red.get("min_true_cyl_force_kN"):
        ref = red["min_true_cyl_force_kN"]
        tol = max(5.0, 0.1 * ref)
        rows.add(
            "1b min true force",
            cid,
            m["min_cyl_after_liftoff_kN"],
            f"{ref} +- {tol:.1f}",
            abs(m["min_cyl_after_liftoff_kN"] - ref) <= tol,
        )
    if m.get("final_corrective_kN") and red.get("corrective_kN"):
        dev = float(np.max(np.abs(np.asarray(m["final_corrective_kN"]) - red["corrective_kN"])))
        is_flat = m["floor"] == "flat"
        fraction = CORRECTIVE_TOL_FLAT if is_flat else CORRECTIVE_TOL_SLOPE
        rows.add(
            "1c final corrective A+F",
            cid,
            dev,
            fraction * W4_N / 1e3,
            dev <= fraction * W4_N / 1e3,
            note=""
            if is_flat
            else "J1 temporary +-2 % W/4: pad horizontal-force couple "
            "not removed (reduced horizontal force record missing)",
        )
    if m.get("final_twist_kN") is not None:
        rows.add(
            "1d final twist",
            cid,
            m["final_twist_kN"],
            "+-3 kN",
            abs(m["final_twist_kN"]) <= 3.0,
            note=f"reduced {red.get('twist_kN')}",
        )


def _item2_rows(rows: _Rows, m, cid: str) -> None:
    if not m["ready_window_ok"] and "reject" not in cid:
        rows.add(
            "2/5b window",
            cid,
            m["times_s"]["ready"],
            "READY >= 5 s before the end",
            None,
            note="run ended before 5 s of READY: items 2 and 5b not judged (run too short)",
        )
        return
    if "reject" in cid:
        return
    shipped = "as_shipped" in cid
    if m.get("att_err_last5_maxabs_deg") is not None:
        v = m["att_err_last5_maxabs_deg"] + MOUNT_SHARE_DEG
        rows.add(
            "2 attitude +-0.2 (+mount)",
            cid,
            v,
            ATT_TOL_DEG,
            None if shipped else v <= ATT_TOL_DEG,
            note="normal_as_shipped: intended failure, not judged (I7 / J7)" if shipped else "",
        )
    path = m.get("imu_minus_true_last5_deg")
    if path is not None and m.get("grade_tilt_deg") is not None:
        dev = float(np.max(np.abs(np.asarray(path) - np.asarray(m["grade_tilt_deg"]))))
        rows.add(
            "2 sensor path filter - true = grade tilt",
            cid,
            dev,
            SENSOR_PATH_TOL_DEG,
            dev <= SENSOR_PATH_TOL_DEG,
            note=f"I5 / J7; grade tilt {m['grade_tilt_deg']}",
        )


def _items_3_to_5_rows(rows: _Rows, m, cid: str) -> None:
    if m.get("min_cyl_after_liftoff_kN") is not None:
        v = m["min_cyl_after_liftoff_kN"]
        note = (f"{m['min_cyl_leg']} at {m['min_cyl_t_s']:.2f} s; D8 margin "
                f"{'ok' if v >= (_f_min_N(m) + D8_MARGIN_N) / 1e3 else 'spec shortfall'}")
        if _is_floor_event_case(m):
            rows.add("3 F_min (1 ms)", cid, v, _f_min_N(m) / 1e3, None,
                     note=f"{EVENT_CASE_NOTE}; {note}", kind="info")
            _event_item3_rows(rows, m, cid)
        else:
            f_min = _f_min_N(m) / 1e3
            rows.add("3 F_min (1 ms)", cid, v, f_min, v >= f_min, note=note)
    rows.add("4 saturation steps", cid, m["saturation_steps"], 0, m["saturation_steps"] == 0)
    if "event_pressure_window_s" in m:
        _event_transient_rows(rows, m, cid)
    else:
        if m.get("max_moving_pressure_bar") is not None:
            rows.add(
                "4 max moving pressure",
                cid,
                m["max_moving_pressure_bar"],
                MOVING_PRESSURE_TOL_BAR,
                m["max_moving_pressure_bar"] <= MOVING_PRESSURE_TOL_BAR,
            )
        if m.get("rocking_amp_deg") is not None:
            rows.add(
                "5a rocking amplitude",
                cid,
                m["rocking_amp_deg"],
                ROCKING_TOL_DEG,
                m["rocking_amp_deg"] <= ROCKING_TOL_DEG,
                note=f"1 s moving mean = {m.get('rocking_window_samples')} samples "
                     f"(Record {m.get('record_rate_hz') or float('nan'):.0f} Hz, C-R4)",
            )
    residual = m.get("filter_residual_last5_deg")
    if residual is not None and "reject" not in cid and m["ready_window_ok"]:
        ok = residual <= FILTER_RESIDUAL_TOL_DEG
        rows.add(
            "5b filter residual last 5 s",
            cid,
            residual,
            FILTER_RESIDUAL_TOL_DEG,
            ok,
            note="" if ok else GROUND_SPEC_SHORTFALL,
            kind="quality",
        )


def _event_transient_rows(rows: _Rows, m, cid: str) -> None:
    """J-5 (U58, spec 62.2): items 4 and 5a of a floor-event case around its window."""
    start_s, end_s = m["event_pressure_window_s"]
    window = f"[{start_s:.3f}, {end_s:.3f}] s"
    samples = m["moving_pressure_samples"]
    value = m.get("max_moving_pressure_excl_transient_bar")
    rows.add("4 max moving pressure outside the event transient", cid, value,
             MOVING_PRESSURE_TOL_BAR, _within(value, MOVING_PRESSURE_TOL_BAR),
             note=f"U58: {samples} samples outside {window}; retraction maximum "
                  f"{m.get('max_retract_pressure_excl_transient_bar')} bar (report)")
    peak = m.get("transient_pressure_peak")
    value = None if peak is None else peak["max_bar"]
    limit = m["transient_pressure_limit_bar"]
    rows.add("4 max pressure in the event transient", cid, value, limit, _within(value, limit),
             note=f"U58: head F/A_p in any state in {window} (no F - m_rod a); peak {peak}")
    value = m.get("rocking_amp_after_re_ready_deg")
    rows.add("5a rocking amplitude after the re-READY", cid, value, ROCKING_TOL_DEG,
             _within(value, ROCKING_TOL_DEG),
             note="U58" if value is not None
             else "U58: no re-READY or too short a window, not judged")
    rows.add("5a rocking amplitude in the event transient (report)", cid,
             m.get("rocking_amp_transient_deg"), ROCKING_TOL_DEG, None,
             note=f"U58: {window}", kind="info")


PROBE_LOAD_LIMIT = "<= 0 (max(5 kN,10 %))"
PROBE_LOAD_TRUTH_NOTE = (
    "truth = probe start load (0.5 s mean before the first move, spec rev. 27 102.1); "
    "zero-calibration deduction legs one-sided (estimate - truth)"
)
ZERO_CAL_DEDUCTION_NOTE = (
    "spec rev. 27 102.1 / 103.3: a leg judged one-sided in 7c must carry its calibration "
    "warning event"
)
OVERLAP_NOTE = "U53: probe overlapping the floor event, reported only (spec 55.1)"


def _item7_rows(rows: _Rows, pr: Mapping[str, Any], cid: str) -> None:
    """Items 7a-7c (J-1, U53): judged on the probes outside the event, overlap reported."""
    is_event_case = pr.get("t_event_s") is not None
    note = "per round and leg (U53)" + ("; probes overlapping the event left out"
                                       if is_event_case else "")
    change = pr.get("att_change_max_deg")
    rows.add("7a probe attitude change", cid, change, PROBE_ATT_TOL_DEG,
             None if change is None else change <= PROBE_ATT_TOL_DEG,
             note=note if change is not None else "every probe window overlaps the event")
    if pr.get("verdict_match") is not None:
        rows.add("7b verdict = truth", cid, pr["verdict_match"], True, pr["verdict_match"],
                 note=note)
    if pr.get("load_error_margin_kN") is not None:
        margin = pr["load_error_margin_kN"]
        rows.add("7c load estimate error", cid, margin, PROBE_LOAD_LIMIT, margin <= 0.0,
                 note=f"{note}; {PROBE_LOAD_TRUTH_NOTE}")
    deduction_events = pr.get("zero_cal_deduction_warning_event")
    if deduction_events:
        rows.add("7c zero-calibration deduction legs: warning event", cid, deduction_events,
                 "WARN_PRESSURE_ZERO_IMPLAUSIBLE / _SKIPPED per deduction leg",
                 all(deduction_events.values()), note=ZERO_CAL_DEDUCTION_NOTE)
    overlap_rows = (
        ("7a probe attitude change (event overlap)", pr.get("att_change_overlap_max_deg"),
         PROBE_ATT_TOL_DEG),
        ("7b verdict = truth (event overlap)", pr.get("overlap_verdict_match"), True),
        ("7c load estimate error (event overlap)", pr.get("overlap_load_error_margin_kN"),
         PROBE_LOAD_LIMIT),
    )
    for item, value, limit in overlap_rows:
        if value is not None:
            rows.add(item, cid, value, limit, None, note=OVERLAP_NOTE, kind="info")


def _item6_rows(rows: _Rows, m, cid: str) -> None:
    """I1: item 6 (G4 settlement) in the judgement rows."""
    item6 = m.get("item6")
    if not item6 or "min_cyl_after_start_kN" not in item6:
        return
    rows.add(
        "6 min after settlement",
        cid,
        item6["min_cyl_after_start_kN"],
        _f_min_N(m) / 1e3,
        item6["pass_min"],
    )
    rows.add(
        "6 re-READY <= 40 s", cid, item6["re_ready_within_s"], SETTLE_READY_S, item6["pass_ready"]
    )
    rows.add(
        "6 final >= F_min + 5 kN",
        cid,
        item6["final_cyl_kN"],
        (_f_min_N(m) + D8_MARGIN_N) / 1e3,
        item6["pass_final"],
    )
    rows.add(
        "6 attitude <= 0.2 deg (+mount)",
        cid,
        item6["final_att_maxabs_deg"],
        ATT_TOL_DEG,
        item6["pass_att"],
    )


def _t1_reject_row(rows: _Rows, m, cid: str, row: Mapping[str, Any]) -> None:
    passed = t1_reject_passed(m["final_phase"], row)
    if "travel_after_check_m" not in row:
        rows.add("T1 reject", cid, row["motor_travel_m"], "IDLE, no motion", passed,
                 note="no CHECK phase in the record: whole-run travel")
        return
    value = {key: row[key] for key in ("travel_after_check_m", "check_excursion_m",
                                       "check_net_m", "check_travel_m", "calibration_active")}
    value["motor_travel_m"] = row["motor_travel_m"]
    if row["calibration_active"]:
        limit = (f"IDLE; after CHECK < {T1_STILL_TRAVEL_M:g} m; in CHECK excursion <= "
                 f"{T1_CALIBRATION_EXCURSION_M:g} m, net <= {T1_CALIBRATION_NET_M:g} m")
    else:
        limit = f"IDLE; no motion (< {T1_STILL_TRAVEL_M:g} m, calibration off)"
    rows.add("T1 reject", cid, value, limit, passed,
             note="spec rev. 27 102.2: the U71 CHECK round trip is not a reject motion")


def _target_rows(rows: _Rows, m, cid: str) -> None:
    """I1 / I4 / J3: T1-T3 of the G5 cases."""
    row = m.get("target_T")
    if row is None:
        return
    if "reject" in cid:
        _t1_reject_row(rows, m, cid, row)
        return
    rows.add(
        "T2 stroke",
        cid,
        row["stroke_max_m"],
        TARGET_STROKE_MAX_M,
        row["stroke_max_m"] <= TARGET_STROKE_MAX_M,
    )
    if m.get("att_err_last5_maxabs_deg") is not None:
        v = m["att_err_last5_maxabs_deg"] + MOUNT_SHARE_DEG
        rows.add("T2 accuracy (+mount)", cid, v, ATT_TOL_DEG, v <= ATT_TOL_DEG)
    if "change_to_ready_s" not in row:
        return
    v = row["change_to_ready_s"]
    after = row.get("run_after_change_s")
    tail = (f"J3; breakdown {row['breakdown_s']}; REANCHOR after the change: "
            f"{row['reanchor_after_change']}")
    if v is not None:
        rows.add("T3 change -> READY", cid, v, TARGET_CHANGE_READY_S,
                 v <= TARGET_CHANGE_READY_S, note=tail)
    elif after is not None and after >= TARGET_CHANGE_READY_S:
        # spec rev. 7 41.1: the run went past t_change + 50 s without READY -> failed
        rows.add("T3 change -> READY", cid, f"no READY in {after:.2f} s after the change",
                 TARGET_CHANGE_READY_S, False,
                 note="run ended after t_change + 50 s without READY: failed (spec rev. 7 41.1); "
                 + tail)
    else:
        rows.add("T3 change -> READY", cid, None, TARGET_CHANGE_READY_S, None,
                 note="run ended before t_change + 50 s without READY: not judged (spec rev. 7 "
                 "41.1); " + tail)
    clearance = row.get("crawler_clearance_min_m")
    rows.add(
        "T3 crawler clearance",
        cid,
        clearance,
        CRAWLER_CLEARANCE_MIN_M,
        None if clearance is None else clearance >= CRAWLER_CLEARANCE_MIN_M,
        note=""
        if clearance is not None
        else "I4: result.json has no floor_plane (normal_world, offset_m): not judged",
    )


def _reanchor_rows(rows: _Rows, m, cid: str) -> None:
    change = m.get("reanchor_att_change_max_deg")
    if change is not None:
        rows.add(
            "R attitude change during REANCHOR",
            cid,
            change,
            REANCHOR_ATT_TOL_DEG,
            change <= REANCHOR_ATT_TOL_DEG,
            note="I2",
        )
    if m.get("h4") and m["h4"].get("status") and "not possible" in m["h4"]["status"]:
        rows.add(
            "R H4", cid, m["h4"]["status"], "applied", None, note="judgement not possible (K4)"
        )


def _shadow_rows(rows: _Rows, m, cid: str) -> None:
    error = m.get("shadow_minus_true_deg")
    if error is None or m.get("grade") != "ideal":
        return
    value = float(np.max(np.abs(error)))
    rows.add(
        "K8 shadow (B) - true floor",
        cid,
        value,
        SHADOW_TOL_DEG,
        None,
        note=f"J5 / I6 report: {'within' if value <= SHADOW_TOL_DEG else 'beyond'} "
        f"{SHADOW_TOL_DEG} deg",
    )


def _level_trend_rows(rows: _Rows, by_id, reduced_level_times) -> None:
    """Item 8 (J4, spec 20.3): REANCHOR-excluded minimum force ordering, REANCHOR minimum,
    time differences between levels against the reduced model."""
    for floor in ("flat", "roll5.5", "fdown3.5", "fup3.5"):
        levels = {}
        for m in by_id.values():
            if m["group"] in ("G2", "G2-R") and m["floor"] == floor:
                levels[m["level"]] = m
        if set(levels) != {"top", "middle", "bottom"}:
            continue
        excl = {
            lv: levels[lv].get(
                "min_cyl_excl_reanchor_kN", levels[lv].get("min_cyl_after_liftoff_kN")
            )
            for lv in levels
        }
        if None not in excl.values():
            tol_kN = TREND_TOLERANCE_N / 1e3
            order = excl["top"] <= excl["middle"] + tol_kN and (
                excl["middle"] <= excl["bottom"] + tol_kN
            )
            rows.add(
                "8 level trend min force (excl. REANCHOR)",
                floor,
                excl,
                f"top <= middle + {tol_kN:g} kN, middle <= bottom + {tol_kN:g} kN",
                order,
                note="J4 (spec 20.3); U54 tolerance (spec 55.2): a difference within the "
                "tolerance reads 'same trend within the reading resolution'",
            )
        inside = {lv: levels[lv].get("min_cyl_reanchor_kN") for lv in levels}
        if any(v is not None for v in inside.values()):
            limit = (max(_f_min_N(levels[lv]) for lv in levels) + D8_MARGIN_N) / 1e3
            ok = all(v is None or v >= limit for v in inside.values())
            rows.add("8 REANCHOR min force", floor, inside, limit, ok, note="J4 (spec 20.3)")
        times = {lv: levels[lv].get("t_ready_minus_touch_s") for lv in levels}
        reduced = (reduced_level_times or {}).get(floor)
        if reduced and None not in times.values():
            diffs = []
            for a, b in (("top", "middle"), ("middle", "bottom")):
                diffs.append(abs((times[b] - times[a]) - (reduced[b] - reduced[a])))
            rows.add(
                "8 level trend time",
                floor,
                max(diffs),
                LEVEL_TREND_TIME_TOL_S,
                max(diffs) <= LEVEL_TREND_TIME_TOL_S,
                note="J4 / I3: Chrono - reduced",
            )
        else:
            rows.add(
                "8 level trend time",
                floor,
                times,
                LEVEL_TREND_TIME_TOL_S,
                None,
                note="J4 / I3: no reduced per-level times passed (judge(reduced_level_times))",
            )


def _h4_reduction_rows(rows: _Rows, slope_r) -> None:
    """J6 / I8: H4 reduction of the rear leg-normal force L, recorded only since dynamics 5.17.3
    (the spec 6 values -49 % / -60 % are REXOME33 numbers; J6 is :func:`_h4_mechanism_rows`)."""
    for floor, expected in H4_REDUCTION_EXPECTED.items():
        entry = (slope_r or {}).get(f"H4_reduction_{floor}")
        if not entry or entry.get("reduction") is None:
            continue
        reduction = -float(entry["reduction"])  # stored as 1 - on / off
        rows.add(
            "R H4 reduction (L basis)",
            floor,
            reduction,
            f"{expected:+.0%} +-10 %p (REXOME33, recorded)",
            None,
            note="recorded only (dynamics 5.17.3, spec rev. 27 103.1); J6 is the 'R H4 "
            "mechanism' row",
            kind="report",
        )


H4_MECHANISM_RATIO_BAND = (0.9, 1.1)
"""J6 (dynamics 5.17.3, spec rev. 27 103.1): ``T_rear,READY / [mu (P_stop,last + m_rod g)]``."""
H4_MECHANISM_JUDGED_GROUP = "G6"
"""J6 is judged on the H4 cases of spec 16.8 (group G6); other cases with a completed REANCHOR
are reported (dynamics judged G6 and G2-R top only)."""


def _h4_mechanism_rows(rows: _Rows, m, cid: str) -> None:
    """J6: rear T after H4 = mechanism +-10 %, and smaller than before H4 (per rear leg)."""
    mech = m.get("h4_mechanism")
    if mech is None:
        return
    low, high = H4_MECHANISM_RATIO_BAND
    in_band = all(low <= r <= high for r in mech["ratio"])
    decreased = all(a < b for a, b in zip(mech["T_ready_kN"], mech["T_done_kN"], strict=True))
    judged = m["group"] == H4_MECHANISM_JUDGED_GROUP
    value = {key: mech[key] for key in ("legs", "ratio", "T_done_kN", "T_ready_kN",
                                        "expected_kN", "P_stop_last_kN", "reduction_recorded")}
    rows.add(
        "R H4 mechanism T_READY / mu(P_stop + m_rod g)",
        cid,
        value,
        f"[{low:g}, {high:g}] and T_READY < T_DONE (rear legs)",
        (in_band and decreased) if judged else None,
        note="J6 (dynamics 5.17.3, spec rev. 27 103.1); reduction recorded only"
        + ("" if judged else f"; reported (J6 judged on group {H4_MECHANISM_JUDGED_GROUP})"),
        kind="function" if judged else "report",
    )


H4_ONE_SIDED_RATIO_MAX = 1.1
"""Spec rev. 28 112.1: combined-judge H4 cases judge only the risky side of J6 (the probe after
H4 relaxes the pad further, so a ratio below 0.9 is the safe side and recorded)."""


def _h4_one_sided_rows(rows: _Rows, m, cid: str) -> None:
    """J6 one-sided (112.1): a completed H4 outside group G6 under the combined judge (G2-R,
    G3, PS1) -> rear ratio <= 1.1 and T_READY < T_DONE; the existing two-sided row stays a
    report there."""
    mech = m.get("h4_mechanism")
    if mech is None or m["group"] == H4_MECHANISM_JUDGED_GROUP:
        return
    is_combined = m.get("contact") == "combined"
    below_max = all(r <= H4_ONE_SIDED_RATIO_MAX for r in mech["ratio"])
    decreased = all(a < b for a, b in zip(mech["T_ready_kN"], mech["T_done_kN"], strict=True))
    value = {key: mech[key] for key in ("legs", "ratio", "T_done_kN", "T_ready_kN")}
    note = "J6 one-sided (spec rev. 28 112.1); ratio below 0.9 = safe side, recorded"
    if not is_combined:
        note += f"; contact {m.get('contact')!r} is not 'combined': reported"
    rows.add(
        "R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g)",
        cid,
        value,
        f"<= {H4_ONE_SIDED_RATIO_MAX:g} and T_READY < T_DONE (rear legs)",
        (below_max and decreased) if is_combined else None,
        note=note,
        kind="function" if is_combined else "report",
    )


DIAGNOSTIC_FALSE_ALARM_ITEM = "72.1 (6) no false pressure diagnosis"


PRE_LOAD_REFERENCE_NOTE = (
    "pre-110.1 record; judged by offline replay verify_S6_L1_diag_load_reference_rev29.json "
    "(spec rev. 29 119)"
)


def _diagnostic_false_alarm_row(rows: _Rows, m, cid: str) -> None:
    """Spec rev. 28 110.1 / rev. 29 122 (72.1 (6)): no D5 / E-5 warning without a
    time-varying injection; injected cases are recorded (PS-5: one warning when the injection
    passes the threshold). A pre-110.1 record is ``superseded`` by the offline replay."""
    check = m.get("diagnostic_check")
    if check is None:
        return
    total = sum(check["counts"].values())
    injected = check["injection"]
    note = "spec rev. 28 110.1, rev. 29 122"
    if injected:
        note += f"; injection {injected}: recorded"
    if check.get("constant_offset"):
        note += f"; constant offset {check['constant_offset']}: judged"
    rows.add(
        DIAGNOSTIC_FALSE_ALARM_ITEM,
        cid,
        check["counts"],
        "0 warnings",
        None if injected else total == 0,
        note=note,
        kind="report" if injected else "function",
    )
    if check.get("pre_load_reference_code"):
        _supersede_by_replay(rows.rows[-1], check.get("replay"))


def _supersede_by_replay(row: dict[str, Any], replay: Mapping[str, Any] | None) -> None:
    """Spec rev. 29 129 ①: keep the recorded outcome in ``passed_raw``, judge nothing."""
    row["passed_raw"] = row["passed"]
    row["passed"] = None
    row["kind"] = "superseded"
    row["superseded_by"] = DIAGNOSTIC_REPLAY_FILE.name
    row["replay_passed"] = None if replay is None else replay["replay_passed"]
    if replay is None:
        replay_note = "case not in the replay file: replay_passed None"
    else:
        replay_note = (f"replay longest run > 4 kN {replay['longest_run_over_4kN_s']:g} s, "
                       f"max |d sum F| {replay['max_abs_dev_kN']} kN")
    row["note"] = f"{PRE_LOAD_REFERENCE_NOTE}; {replay_note}; {row['note']}"


SENSITIVITY_REPORT_ITEMS = frozenset({
    "7c load estimate error",
    "R/D8 min force >= F_min + 5 kN",
    "6 final >= F_min + 5 kN",
    "R H4 mechanism one-sided T_READY / mu(P_stop + m_rod g)",
})
"""Spec rev. 28 111 / 112.1: rows a sensitivity case reports instead of judging (7c, the D8
margin F_min + 5 kN, the one-sided J6). F_min itself, lift-off, READY, saturation and 350 bar
stay judged in every condition."""


def _report_sensitivity_rows(rows: list[dict[str, Any]], by_id) -> None:
    for row in rows:
        m = by_id.get(row["case"])
        if m is None or m.get("condition") != str(CaseCondition.SENSITIVITY):
            continue
        if row["item"] not in SENSITIVITY_REPORT_ITEMS or row["passed"] is None:
            continue
        reasons = ", ".join(m.get("condition_reasons", []))
        row["passed_raw"] = row["passed"]
        row["passed"] = None
        row["kind"] = "report"
        row["condition"] = str(CaseCondition.SENSITIVITY)
        note = f"sensitivity condition ({reasons}): reported (spec rev. 28 111)"
        row["note"] = f"{note}; {row['note']}" if row["note"] else note


def _mark_superseded_rows(rows: list[dict[str, Any]], by_id) -> None:
    """Spec rev. 28 109.2: the settlement / drop rows of an L1-R bundle case that ran with the
    mechanics off are records; the formal judgement is the B2 run (L1-R on)."""
    for row in rows:
        m = by_id.get(row["case"])
        if m is None or m.get("superseded_by") is None:
            continue
        row["superseded_by"] = m["superseded_by"]
        if row["passed"] is not None:
            row["passed_raw"] = row["passed"]
            row["passed"] = None
        row["kind"] = "superseded"


def judge(
    metrics: list[dict[str, Any]],
    probes: dict[str, dict[str, Any]],
    reduced_level_times: Mapping[str, Mapping[str, float]] | None = None,
    slope_r: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Pre-judgement rows (item, case, value, limit, passed, note, kind).

    Args:
        metrics: :func:`case_metrics` of every case.
        probes: :func:`probe_metrics` by case.
        reduced_level_times: Reduced-model touch -> READY time per floor and level (item 8
            time trend, J4); without it that row is not judged.
        slope_r: The summary's H4 / friction block (``H4_reduction_<floor>`` with
            ``reduction``) for the J6 rows.
    """
    rows = _Rows()
    by_id = {m["case"]: m for m in metrics}
    for m in metrics:
        cid = m["case"]
        ok_run = m["final_phase"] == "ready" or m["group"] == "G5" and "reject" in cid
        rows.add("run", cid, m["final_phase"], "ready", ok_run)
        if m["group"] == "G1" and m.get("reduced"):
            _item1_rows(rows, m, cid)
        _item2_rows(rows, m, cid)
        _items_3_to_5_rows(rows, m, cid)
        _item6_rows(rows, m, cid)
        pr = probes.get(cid)
        if pr and pr.get("windows_s"):
            _item7_rows(rows, pr, cid)
        if m["floor"] in ("fdown3.5", "fup3.5", "roll5.5") and m.get("min_cyl_after_liftoff_kN"):
            v = m["min_cyl_after_liftoff_kN"]
            rows.add(
                "R/D8 min force >= F_min + 5 kN",
                cid,
                v,
                (_f_min_N(m) + D8_MARGIN_N) / 1e3,
                v >= (_f_min_N(m) + D8_MARGIN_N) / 1e3,
            )
            if m.get("pad_N_min_after_liftoff_kN") is not None:
                rows.add(
                    "R/D8 no pad lift-off",
                    cid,
                    m["pad_N_min_after_liftoff_kN"],
                    "> 0",
                    m["pad_N_min_after_liftoff_kN"] > 0.0,
                )
        _reanchor_rows(rows, m, cid)
        _h4_mechanism_rows(rows, m, cid)
        _h4_one_sided_rows(rows, m, cid)
        _target_rows(rows, m, cid)
        _shadow_rows(rows, m, cid)
        _diagnostic_false_alarm_row(rows, m, cid)
    _level_trend_rows(rows, by_id, reduced_level_times)
    _h4_reduction_rows(rows, slope_r)
    _report_sensitivity_rows(rows.rows, by_id)
    _mark_superseded_rows(rows.rows, by_id)
    info_cases = {cid for cid, m in by_id.items() if _is_info_case(m)}
    for row in rows.rows:
        if row["case"] in info_cases:
            row["passed_raw"] = row["passed"]
            row["passed"] = None
            row["kind"] = "info"
            row["note"] = (INFO_CASE_NOTE + "; " + row["note"]) if row["note"] else INFO_CASE_NOTE
    return rows.rows


INFO_CASE_NOTE = "RE1c: controller bypassed (forced retraction), not a judged case (spec 30)"


def _is_info_case(m: Mapping[str, Any]) -> bool:
    """RE1c (forced RR retraction with the controller bypassed, control spec 30) is a GE1
    observation case: its rows are reported with ``kind`` ``"info"`` and ``passed`` None
    (the raw outcome kept in ``passed_raw``)."""
    return m.get("group") == "RE1c" or str(m.get("case", "")).startswith("RE1c")


def settle_checks(case: Mapping[str, Any], metrics: Mapping[str, Any]) -> dict[str, Any]:
    """Item 6 (G4): after the settlement start (first READY + 5 s + the bundle-C phase offset
    ``settings.bundle_c.settle_offset_s``, spec rev. 32 163.2 C-R7; 0 when absent)."""
    tm = metrics["times_s"]
    if tm["ready"] is None:
        return {"status": "no READY before the settlement"}
    bundle = case["result"]["settings"].get("bundle_c") or {}
    t_start = tm["ready"] + 5.0 + float(bundle.get("settle_offset_s") or 0.0)
    pads = case["pads"]
    tp = pads["t"] - tm["t0"]
    after = tp >= t_start
    fmin = float(pads["F_cyl_min_interval"][after].min()) / 1e3
    phases = [(float(t), p) for t, p in case["result"]["phases"]]
    left = [t for t, p in phases if t > t_start and p != "ready"]
    re_ready = None
    if left:
        re_ready = next((t for t, p in phases if t > left[0] and p == "ready"), None)
    rec = case["rec"]
    t = rec["t"] - tm["t0"]
    fin = np.asarray(rec["F_cyl"])[t >= tm["end"] - 1.0].mean(axis=0) / 1e3
    rp = _deg(np.array([roll_pitch_from_quat(q) for q in rec["body_quat_wxyz"]]))
    att = float(np.max(np.abs(rp[t >= tm["end"] - 5.0])))
    return {
        "settlement_start_s": t_start,
        "min_cyl_after_start_kN": fmin,
        "left_ready_s": left[0] if left else None,
        "re_ready_s": re_ready,
        "re_ready_within_s": None if re_ready is None else re_ready - t_start,
        "final_cyl_kN": fin.tolist(),
        "final_att_maxabs_deg": att,
        "pass_min": fmin >= _f_min_N(metrics) / 1e3,
        "pass_ready": (not left) or (re_ready is not None and re_ready - t_start <= SETTLE_READY_S),
        "pass_final": bool(np.all(fin >= (_f_min_N(metrics) + D8_MARGIN_N) / 1e3)),
        "pass_att": att + MOUNT_SHARE_DEG <= ATT_TOL_DEG,
    }


__all__ = [
    "CaseCondition",
    "case_condition",
    "case_metrics",
    "diagnostic_false_alarm_metrics",
    "judge",
    "load_case",
    "probe_metrics",
    "reduced_reference",
    "settle_checks",
    "superseded_by",
    "support_projection",
]
