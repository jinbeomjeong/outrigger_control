"""E3 reuse check (control spec 432.4): would the final controller act on a stored Chrono S9 run?

The final controller (spec 429.11) is the R8 C2 of 05708b2 plus four additions: P-S8-36 SGS
(``soil_stop``, scope ``any_loc``), P-S8-37 R4c30 (flat-soil clearance margin 30 mm),
P-S8-33 L1gs (LOC revocation) and P-S8-35 DSb75 (differential sinkage). All four act only at or
after a confirmed LOC, so a recorded run is the same run under the final controller (class (a),
reuse without re-run) when none of them would have acted. Up to the first LOC the commands are
the same, so the LOC values in the record (``t_P``, ``c_min(t_P)``, settle attitude, soil mode
start) are the values the final controller would have seen.

Per case and feature the check gives ``fires`` (True / False / None = cannot tell), a
``confidence`` and the evidence:

* SGS: a lift-stroke guard period after a LOC stops the run (``any_loc``). Records with the guard
  (``controller_meta.lift_stroke_guard``) give the period count; older records use the bound
  ``max measured stroke in LEVEL after the LOC + v_max * lookahead < s_g`` (a guard period needs
  ``s + u * lookahead >= s_g`` with ``u <= v_max``).
* R4: at a LOC with the soil mode started, P-S8-31 not applied and settle tilt <= 1 deg
  (``C2Controller._is_flat_soil_margin_due``). P-S8-31 comes from the record when it had the
  rule, else from its conditions (``_is_slope_margin_due``).
* L1gs: needs the LOC soil sign (soil mode, or ``c_min(t_P)`` > 10 mm and tilt > 1 deg). Records
  with the rule give its revocations; otherwise a closed gate decides, and an open gate is
  replayed on the 10 Hz record (pressure load sum referred to ``W_hat``, medium confidence).
* DSb75: needs the soil sign and settle tilt <= 1 deg at the first LOC. Records with the rule
  give its holds; otherwise a closed gate decides, and an open gate is replayed (1 s stroke
  slopes and the period-mean gyro roll rate, medium confidence).

Runs without a controller in the loop (P3a open loop, DT model tests, G6-0a lift) are (a) by
definition. A case is (a) when every feature has ``fires`` False, (b) when any is True and
``undecided`` otherwise. The other rules of 05708b2 (P-S8-28 .. 32) are not judged here.

Usage (project interpreter, e.g. dynamics-dev):
    python -I 04_scripts/03_control/s9/final_ctrl_offline.py [--out OUT] [case_dir ...]
Without case directories the E3 list of spec 432.3 / 432.4.1 is checked. Units SI.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "03_src") not in sys.path:  # python -I: the package is not installed
    sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.control.c2 import (  # noqa: E402
    DIFF_SINK_HOLD_EVENT,
    FLAT_SOIL_MARGIN_EVENT,
    LIFT_GUARD_FAULT_EVENT,
    LIFT_GUARD_WARNING_EVENT,
    LOC_REVOKE_EVENT,
    SLOPE_MARGIN_EVENT,
    SOIL_EVENT_LIFTOFF_CONFIRMED,
    SOIL_EVENT_MODE_START,
    STROKE_END_MARGIN_M,
    C2Config,
    C2Geometry,
)
from outrigger_sim.params import load_params  # noqa: E402

RESULTS_ROOT = ROOT / "07_results" / "S9"
DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "rev85" / "e3_reuse_check.json"
FINAL_FLAT_SOIL_MARGIN_M = 0.03
"""R4c30 (spec 429.11)."""
TIME_MATCH_S = 1e-6

LEVEL_PHASE = "level"
DONE_PHASE = "done"

CLASS_REUSE = "(a)"
CLASS_RERUN = "(b)"
CLASS_UNDECIDED = "undecided"

# (label, origin, folder under 07_results/S9). origin "432.3_changed" = (b) -> (a) by the ZIC
# rejection; "existing_a" = (a) from the start (spec 432.1, 431.2).
E3_CASES: tuple[tuple[str, str, str], ...] = (
    *(
        (f"P3b G1 {pad} {level}", "existing_a", f"batch_P3b_20261026_122444/P3b_G1_{pad}_{level}")
        for pad in ("A", "B")
        for level in ("bottom_Fs4", "middle_Fs4", "top_Fs0", "top_Fs4", "top_Fs8")
    ),
    ("P3b G1 A top_Fs0 (rerun record)", "existing_a", "batch_P3b_20261026_193021/P3b_G1_A_top_Fs0"),
    ("P3b G1 A top_Fs8 (rerun record)", "existing_a", "batch_P3b_20261026_201553/P3b_G1_A_top_Fs8"),
    ("G6 G1RR", "existing_a", "batch_G6_20261028_075108/G6_G1_B_top_Fs4_spG1RR"),
    ("D424 2 (x1.2)", "existing_a", "batch_D424_20261030_014908/P3b_J1_B_top_Fs4_m1p2"),
    *(
        (f"P3a {name}", "existing_a", f"batch_P3a_20261026_092653/P3a_{name}")
        for name in ("G1_A", "G1_B", "J1_A", "J1_B")
    ),
    ("DT M14s dashpot", "existing_a", "batch_DT_20261026_122444/DT_G1_B_top_M14s_dashpot8s_dt5e-5"),
    ("DT P3a", "existing_a", "batch_DT_20261026_122444/DT_P3a_G1_B_dt5e-5"),
    ("G6-0a", "existing_a", "batch_G6_20261028_075108/G6-0a_G1_B_lift_spG1RR"),
    ("S9SL C-1", "432.3_changed", "batch_S9SL_20261029_144406/S9SL_C1_G1_B_top_Fs4_r0_p3p2"),
    ("RV1 X4-nd", "432.3_changed", "batch_RV1_20261030_111615/S9SL_X4nd_J1_B_top_Fs4_r0_p2p8"),
    (
        "RV1 X4-ed",
        "432.3_changed",
        "batch_RV1_20261030_111615/S9SL_X4ed_J1_B_top_Fs4_r1p925_p1p4",
    ),
    ("G6 J1@RR (0.6 kN)", "432.3_changed", "batch_G6P_20261029_103815/G6_G1_B_top_Fs4_spJ1RR"),
    ("G6 J1@FL", "432.3_changed", "batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ1FL"),
    ("G6 J2@RR", "432.3_changed", "batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2RR"),
)


# Records that ran L1gs / DSb75 themselves: their recorded events check the two replays
# (a replay is only trusted up to the first recorded action, after which the run differs).
VALIDATION_CASES: tuple[str, ...] = (
    "batch_D424R_20261030_073635/P3b_J1_B_top_Fs4_m1p1",
    "batch_D424R_20261030_073635/P3b_J2_B_middle_Fs4",
    "batch_D424R_20261030_073635/P3b_J2_B_bottom_Fs4",
    "batch_RV1_20261030_111615/P3b_J2_B_top_Fs4_m1p1",
)


@dataclass(frozen=True)
class FinalSettings:
    """Final-controller values the four checks need (from the 03_src preset and the YAML)."""

    period_s: float
    max_speed_m_s: float
    guard_stroke_m: float
    guard_lookahead_s: float
    slope_tilt_min_rad: float
    slope_min_clearance_at_P_m: float | None
    slope_require_soil_use: bool
    revoke_watch_m: float
    revoke_rise_N: float
    revoke_rise_fraction_W: float
    revoke_mean_s: float
    revoke_confirm_periods: int
    revoke_gate_min_clearance_at_P_m: float
    revoke_gate_tilt_min_rad: float
    revoke_stroke_limit_m: float
    sink_threshold_m_s: float
    sink_confirm_periods: int
    sink_gate_max_tilt_rad: float
    sink_stroke_limit_m: float
    sink_track_w_m: tuple[float, float]
    sink_signal_periods: int
    head_area_m2: tuple[float, ...]
    annulus_area_m2: tuple[float, ...]


@dataclass(frozen=True)
class LocFacts:
    """LOC values of a record (the same under the final controller, see the module text)."""

    loc_times_s: tuple[float, ...]
    soil_mode_start_s: float | None
    plateau_start_s: float | None
    clearance_at_P_m: float | None
    settle_tilt_rad: float | None
    weight_estimate_N: float | None
    reference_weight_N: float | None

    @property
    def first_loc_s(self) -> float | None:
        return self.loc_times_s[0] if self.loc_times_s else None

    def soil_mode_before(self, t_loc_s: float) -> bool:
        return (
            self.soil_mode_start_s is not None and self.soil_mode_start_s <= t_loc_s + TIME_MATCH_S
        )


@dataclass
class CaseRecord:
    """One stored case: result.json parts and the 10 Hz record (None without a controller)."""

    case_dir: Path
    result: dict[str, Any]
    events: list[tuple[float, str]]
    controller_meta: dict[str, Any]
    facts: LocFacts
    t_s: np.ndarray | None = None
    phase: np.ndarray | None = None
    stroke_m: np.ndarray | None = None
    gyro_roll_rad_s: np.ndarray | None = None
    head_pressure_Pa: np.ndarray | None = None
    rod_pressure_Pa: np.ndarray | None = None

    @property
    def has_controller(self) -> bool:
        return self.t_s is not None and bool(self.result.get("phases"))


@dataclass
class FeatureCheck:
    """Verdict of one feature on one case."""

    fires: bool | None
    confidence: str
    basis: str
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RevokeReplay:
    fired_t_s: float | None
    kind: str | None
    """``"REVOKE"`` or ``"SKIP"`` (stroke guard: record only, commands unchanged)."""
    peak_rise_N: float
    end_reason: str


@dataclass(frozen=True)
class DiffSinkReplay:
    hold_t_s: float | None
    max_rate_m_s: float
    rate_at_hold_m_s: float | None
    evaluated_periods: int


def final_settings(params_path: Path | None = None) -> FinalSettings:
    """Settings of the final preset ``with_10hz_d1(soil_stop=True, flat_soil_margin_m=0.03)``."""
    config = C2Config().with_10hz_d1(soil_stop=True, flat_soil_margin_m=FINAL_FLAT_SOIL_MARGIN_M)
    geometry = C2Geometry.from_params(load_params(params_path))
    guard = config.lift_stroke_guard
    guard_stroke_m = geometry.stroke_soft_max_m - STROKE_END_MARGIN_M - guard.extra_margin_m
    slope = config.slope_clearance_margin
    revoke = config.loc_revoke
    sink = config.diff_sink
    return FinalSettings(
        period_s=config.period_s,
        max_speed_m_s=geometry.max_speed_m_s,
        guard_stroke_m=guard_stroke_m,
        guard_lookahead_s=guard.lookahead_periods * config.period_s,
        slope_tilt_min_rad=slope.tilt_min_rad,
        slope_min_clearance_at_P_m=slope.min_clearance_at_P_m,
        slope_require_soil_use=slope.require_soil_use,
        revoke_watch_m=revoke.watch_m,
        revoke_rise_N=revoke.rise_N,
        revoke_rise_fraction_W=revoke.rise_fraction_W,
        revoke_mean_s=revoke.mean_s,
        revoke_confirm_periods=revoke.confirm_periods,
        revoke_gate_min_clearance_at_P_m=revoke.gate_min_clearance_at_P_m,
        revoke_gate_tilt_min_rad=revoke.gate_tilt_min_rad,
        revoke_stroke_limit_m=guard_stroke_m - revoke.stroke_margin_m,
        sink_threshold_m_s=sink.threshold_m_s,
        sink_confirm_periods=round(sink.confirm_s / config.period_s),
        sink_gate_max_tilt_rad=sink.gate_max_settle_tilt_rad,
        sink_stroke_limit_m=guard_stroke_m - sink.stroke_margin_m,
        sink_track_w_m=tuple(sink.track_w_m),
        sink_signal_periods=round(1.0 / config.period_s),
        head_area_m2=tuple(float(value) for value in np.broadcast_to(geometry.head_area_m2, 4)),
        annulus_area_m2=tuple(
            float(value) for value in np.broadcast_to(geometry.annulus_area_m2, 4)
        ),
    )


# --- loading ---


def _soil_block(result: dict[str, Any]) -> dict[str, Any]:
    soil = result.get("c2_soil") or (result.get("meta") or {}).get("c2_soil")
    if soil:
        return soil
    return (result.get("controller_meta") or {}).get("soil") or {}


def _loc_facts(result: dict[str, Any], events: list[tuple[float, str]]) -> LocFacts:
    soil = _soil_block(result)
    settle = soil.get("settle_attitude_rad")
    soil_starts = [t_s for t_s, name in events if name == SOIL_EVENT_MODE_START]
    if not soil_starts and soil.get("soil_mode_t_s") is not None:
        soil_starts = [float(soil["soil_mode_t_s"])]
    return LocFacts(
        loc_times_s=tuple(t_s for t_s, name in events if name == SOIL_EVENT_LIFTOFF_CONFIRMED),
        soil_mode_start_s=soil_starts[0] if soil_starts else None,
        plateau_start_s=soil.get("t_P_s"),
        clearance_at_P_m=soil.get("clearance_at_P_m"),
        settle_tilt_rad=None if settle is None else max(abs(settle[0]), abs(settle[1])),
        weight_estimate_N=soil.get("W_hat_N"),
        reference_weight_N=soil.get("W_ref_N"),
    )


def _phase_per_sample(case_dir: Path, result: dict[str, Any], t_s: np.ndarray) -> np.ndarray:
    """``r8_series.npz`` phases when they match the record, else the ``phases`` steps."""
    r8_path = case_dir / "r8_series.npz"
    if r8_path.exists():
        with np.load(r8_path, allow_pickle=False) as r8:
            r8_t = np.asarray(r8["t"])
            if len(r8_t) == len(t_s) and np.allclose(r8_t, t_s, atol=1e-6):
                return np.array([str(name) for name in r8["phase"]])
    starts = [(float(row["t_s"]), str(row["phase"])) for row in result.get("phases") or []]
    phase = np.full(len(t_s), "", dtype=object)
    for start_s, name in starts:
        phase[t_s >= start_s - TIME_MATCH_S] = name
    return phase.astype(str)


def load_case(case_dir: Path) -> CaseRecord:
    """Read one case folder (read only; ``allow_pickle=False``)."""
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    events = [(float(row["t_s"]), str(row["name"])) for row in result.get("events") or []]
    meta = result.get("controller_meta") or (result.get("runner_meta") or {}).get("controller")
    record = CaseRecord(
        case_dir=case_dir,
        result=result,
        events=events,
        controller_meta=meta or {},
        facts=_loc_facts(result, events),
    )
    record_path = case_dir / "record" / "record.npz"
    if not record_path.exists():
        return record
    with np.load(record_path, allow_pickle=False) as data:
        record.t_s = np.asarray(data["t"], dtype=float)
        record.stroke_m = np.asarray(data["meas.stroke"], dtype=float)
        record.gyro_roll_rad_s = np.asarray(data["meas.angular_rate"], dtype=float)[:, 0]
        record.head_pressure_Pa = np.asarray(data["meas.head_pressure"], dtype=float)
        record.rod_pressure_Pa = np.asarray(data["meas.rod_pressure"], dtype=float)
    record.phase = _phase_per_sample(case_dir, result, record.t_s)
    return record


# --- replays (pure functions of arrays, used by the checks and the unit tests) ---


def replay_loc_revoke(
    t_s: np.ndarray,
    phase: np.ndarray,
    stroke_m: np.ndarray,
    load_sum_N: np.ndarray,
    t_loc_s: float,
    weight_estimate_N: float,
    reference_weight_N: float,
    settings: FinalSettings,
) -> RevokeReplay:
    """P-S8-33 watch from the LOC period (``C2Controller._watch_loc_revoke``)."""
    start = int(np.searchsorted(t_s, t_loc_s - TIME_MATCH_S))
    if start >= len(t_s):
        return RevokeReplay(None, None, -math.inf, "no sample at the LOC")
    stroke_at_loc_m = float(np.mean(stroke_m[start]))
    rise_limit_N = max(settings.revoke_rise_N, settings.revoke_rise_fraction_W * reference_weight_N)
    window: deque[tuple[float, float]] = deque()
    periods_above, peak_rise_N = 0, -math.inf
    for i in range(start, len(t_s)):
        if phase[i] != LEVEL_PHASE:
            return RevokeReplay(None, None, peak_rise_N, f"phase {phase[i]} at {t_s[i]:.1f} s")
        if float(np.mean(stroke_m[i])) - stroke_at_loc_m >= settings.revoke_watch_m:
            return RevokeReplay(None, None, peak_rise_N, f"stroke +watch at {t_s[i]:.1f} s")
        window.append((float(t_s[i]), float(load_sum_N[i])))
        while window[0][0] <= t_s[i] - settings.revoke_mean_s + TIME_MATCH_S:
            window.popleft()
        rise_N = float(np.mean([load for _, load in window])) - weight_estimate_N
        peak_rise_N = max(peak_rise_N, rise_N)
        periods_above = periods_above + 1 if rise_N > rise_limit_N else 0
        if periods_above >= settings.revoke_confirm_periods:
            is_guarded = float(np.max(stroke_m[i])) >= settings.revoke_stroke_limit_m
            kind = "SKIP" if is_guarded else "REVOKE"
            return RevokeReplay(float(t_s[i]), kind, peak_rise_N, "confirmed")
    return RevokeReplay(None, None, peak_rise_N, "record end")


def _sink_rates_m_s(
    times_s: np.ndarray, strokes_m: np.ndarray, roll_rate: float, settings: FinalSettings
) -> np.ndarray:
    """``r_a`` (front, rear): stroke slope difference minus ``w_a`` times the roll rate."""
    centred_t = times_s - times_s.mean()
    slopes = centred_t @ (strokes_m - strokes_m.mean(axis=0)) / (centred_t @ centred_t)
    front_w_m, rear_w_m = settings.sink_track_w_m
    return np.array(
        [
            slopes[0] - slopes[1] - front_w_m * roll_rate,
            slopes[2] - slopes[3] - rear_w_m * roll_rate,
        ]
    )


def replay_diff_sink(
    t_s: np.ndarray,
    phase: np.ndarray,
    stroke_m: np.ndarray,
    gyro_roll_rad_s: np.ndarray,
    t_loc_s: float,
    settings: FinalSettings,
) -> DiffSinkReplay:
    """P-S8-35 trigger from the period after the first LOC to the first DONE.

    The controller keeps the strokes of the last LEVEL periods and a 1 s window of 100 Hz gyro
    samples; the record has the period-mean roll rate, so the last ``sink_signal_periods``
    period means stand for that window.
    """
    window_len = settings.sink_signal_periods
    strokes: deque[tuple[float, np.ndarray]] = deque(maxlen=window_len)
    gyro: deque[float] = deque(maxlen=window_len)
    above, evaluated, max_rate = 0, 0, 0.0
    for i in range(len(t_s)):
        gyro.append(float(gyro_roll_rad_s[i]))
        is_after_loc = t_s[i] > t_loc_s + TIME_MATCH_S
        if is_after_loc and phase[i] == DONE_PHASE:
            break
        if phase[i] != LEVEL_PHASE:
            continue
        strokes.append((float(t_s[i]), np.asarray(stroke_m[i], dtype=float)))
        if not is_after_loc or len(strokes) < window_len:
            continue
        times = np.array([t for t, _ in strokes])
        values = np.array([value for _, value in strokes])
        rates = _sink_rates_m_s(times, values, float(np.mean(gyro)), settings)
        evaluated += 1
        max_rate = max(max_rate, float(np.abs(rates).max()))
        if float(np.max(stroke_m[i])) >= settings.sink_stroke_limit_m:
            above = 0
            continue
        above = above + 1 if float(np.abs(rates).max()) > settings.sink_threshold_m_s else 0
        if above >= settings.sink_confirm_periods:
            rate_at_hold = float(rates[int(np.argmax(np.abs(rates)))])
            return DiffSinkReplay(float(t_s[i]), max_rate, rate_at_hold, evaluated)
    return DiffSinkReplay(None, max_rate, None, evaluated)


# --- feature checks ---


def _events_with(events: list[tuple[float, str]], prefix: str) -> list[tuple[float, str]]:
    return [(t_s, name) for t_s, name in events if name.startswith(prefix)]


def soil_sign_reason(facts: LocFacts, t_loc_s: float, settings: FinalSettings) -> str | None:
    """L1-g soil sign at a LOC (``C2Controller._loc_soil_sign_reason``)."""
    if facts.soil_mode_before(t_loc_s):
        return "soil_mode"
    if facts.clearance_at_P_m is None or facts.settle_tilt_rad is None:
        return None
    is_tilted = facts.settle_tilt_rad > settings.revoke_gate_tilt_min_rad
    if facts.clearance_at_P_m > settings.revoke_gate_min_clearance_at_P_m and is_tilted:
        return "clearance_tilt"
    return None


def _post_loc_level_mask(record: CaseRecord) -> np.ndarray:
    first_loc_s = record.facts.first_loc_s
    return (record.phase == LEVEL_PHASE) & (record.t_s >= first_loc_s - TIME_MATCH_S)


def check_sgs(record: CaseRecord, settings: FinalSettings) -> FeatureCheck:
    """P-S8-36 any_loc: any lift-stroke guard period after a LOC."""
    if record.facts.first_loc_s is None:
        return FeatureCheck(False, "high", "no LOC: the guard runs only after a LOC")
    warnings = _events_with(record.events, LIFT_GUARD_WARNING_EVENT)
    faults = _events_with(record.events, LIFT_GUARD_FAULT_EVENT)  # includes the SGS soil stop
    level_after_loc = _post_loc_level_mask(record)
    max_stroke_m = float(np.max(record.stroke_m[level_after_loc])) if level_after_loc.any() else 0.0
    reach_m = max_stroke_m + settings.max_speed_m_s * settings.guard_lookahead_s
    values = {
        "guard_warnings": len(warnings),
        "guard_faults": len(faults),
        "max_stroke_level_after_loc_m": round(max_stroke_m, 5),
        "reach_bound_m": round(reach_m, 5),
        "guard_stroke_m": round(settings.guard_stroke_m, 5),
    }
    guard_meta = record.controller_meta.get("lift_stroke_guard")
    if guard_meta and "periods" in guard_meta:
        periods = int(guard_meta["periods"])
        values["recorded_guard_periods"] = periods
        fires = periods > 0 or bool(warnings) or bool(faults)
        return FeatureCheck(fires, "high", "recorded guard periods and events", values)
    if reach_m < settings.guard_stroke_m:
        return FeatureCheck(
            False, "high", "stroke bound below s_g (record without the guard)", values
        )
    return FeatureCheck(None, "low", "stroke bound reaches s_g (record without the guard)", values)


def _slope_margin_applied(record: CaseRecord, t_loc_s: float, settings: FinalSettings) -> bool:
    """P-S8-31 applied at or before this LOC: recorded, or its conditions on the record."""
    margin_events = _events_with(record.events, SLOPE_MARGIN_EVENT)
    if any(t_s <= t_loc_s + TIME_MATCH_S for t_s, _ in margin_events):
        return True
    if record.controller_meta.get("slope_clearance_margin") is not None:
        return False  # the rule was in the code and did not fire
    facts = record.facts
    if facts.settle_tilt_rad is None or facts.settle_tilt_rad <= settings.slope_tilt_min_rad:
        return False
    if settings.slope_require_soil_use and not facts.soil_mode_before(t_loc_s):
        return False
    min_clearance_m = settings.slope_min_clearance_at_P_m
    if min_clearance_m is None:
        return True
    return facts.clearance_at_P_m is not None and facts.clearance_at_P_m > min_clearance_m


def check_r4(record: CaseRecord, settings: FinalSettings) -> FeatureCheck:
    """R4 at every LOC (``C2Controller._is_flat_soil_margin_due``)."""
    facts = record.facts
    if not facts.loc_times_s:
        return FeatureCheck(False, "high", "no LOC")
    tilt = facts.settle_tilt_rad
    values: dict[str, Any] = {
        "soil_mode_start_s": facts.soil_mode_start_s,
        "loc_times_s": [round(t_s, 2) for t_s in facts.loc_times_s],
        "settle_tilt_deg": None if tilt is None else round(math.degrees(tilt), 4),
        "recorded_flat_margin_events": len(_events_with(record.events, FLAT_SOIL_MARGIN_EVENT)),
    }
    due_at = []
    for t_loc_s in facts.loc_times_s:
        p31 = _slope_margin_applied(record, t_loc_s, settings)
        values.setdefault("p31_applied_at_loc", []).append(p31)
        is_level = tilt is not None and tilt <= settings.slope_tilt_min_rad
        if facts.soil_mode_before(t_loc_s) and not p31 and is_level:
            due_at.append(round(t_loc_s, 2))
    values["due_at_loc_s"] = due_at
    confidence = "high" if len(facts.loc_times_s) == 1 else "medium"
    basis = "soil mode, P-S8-31 and settle tilt at each LOC from the record"
    return FeatureCheck(bool(due_at), confidence, basis, values)


def _load_sum_N(record: CaseRecord, settings: FinalSettings) -> np.ndarray | None:
    """Pressure load sum referred to ``W_hat`` over the S-1 window ``[t_P, t_LOC]``.

    ``None`` when the window is empty: after a recorded revocation ``t_P`` belongs to a later
    LOC (the recorded rule decides those runs anyway).
    """
    head = np.asarray(settings.head_area_m2)
    annulus = np.asarray(settings.annulus_area_m2)
    load_sum = (record.head_pressure_Pa * head - record.rod_pressure_Pa * annulus).sum(axis=1)
    facts = record.facts
    window = (record.t_s >= facts.plateau_start_s - TIME_MATCH_S) & (
        record.t_s <= facts.first_loc_s + TIME_MATCH_S
    )
    if not window.any():
        return None
    return load_sum + (facts.weight_estimate_N - float(load_sum[window].mean()))


def check_l1gs(record: CaseRecord, settings: FinalSettings) -> FeatureCheck:
    """P-S8-33: recorded revocations, a closed gate, or the replay."""
    facts = record.facts
    if facts.first_loc_s is None:
        return FeatureCheck(False, "high", "no LOC")
    reason = soil_sign_reason(facts, facts.first_loc_s, settings)
    values: dict[str, Any] = {"soil_sign": reason}
    has_loc_values = None not in (
        facts.plateau_start_s,
        facts.weight_estimate_N,
        facts.reference_weight_N,
    )
    load_sum_N = _load_sum_N(record, settings) if has_loc_values else None
    if load_sum_N is not None:
        replay = replay_loc_revoke(
            record.t_s,
            record.phase,
            record.stroke_m,
            load_sum_N,
            facts.first_loc_s,
            facts.weight_estimate_N,
            facts.reference_weight_N,
            settings,
        )
        values["replay"] = _rounded(asdict(replay))
    recorded = record.controller_meta.get("loc_revoke")
    if recorded and recorded.get("settings", {}).get("enable"):
        revokes = int(recorded.get("revokes", 0))
        values["recorded_revokes"] = revokes
        values["recorded_skips"] = len(recorded.get("t_skip_s") or [])
        fires = revokes > 0 or bool(_events_with(record.events, LOC_REVOKE_EVENT))
        return FeatureCheck(fires, "high", "rule in the recorded run", values)
    if reason is None:
        return FeatureCheck(False, "high", "soil gate closed at the LOC", values)
    replay_row = values.get("replay")
    if replay_row is None:
        return FeatureCheck(None, "low", "gate open and no LOC window to replay", values)
    fires = replay_row["kind"] == "REVOKE"
    return FeatureCheck(fires, "medium", "gate open: 10 Hz replay", values)


def check_dsb(record: CaseRecord, settings: FinalSettings) -> FeatureCheck:
    """P-S8-35: recorded holds, a closed gate, or the replay."""
    facts = record.facts
    if facts.first_loc_s is None:
        return FeatureCheck(False, "high", "no LOC")
    reason = soil_sign_reason(facts, facts.first_loc_s, settings)
    tilt = facts.settle_tilt_rad
    is_level = tilt is not None and tilt <= settings.sink_gate_max_tilt_rad
    values: dict[str, Any] = {"soil_sign": reason, "settle_level": is_level}
    replay = replay_diff_sink(
        record.t_s,
        record.phase,
        record.stroke_m,
        record.gyro_roll_rad_s,
        facts.first_loc_s,
        settings,
    )
    values["replay"] = _rounded(asdict(replay))
    recorded = record.controller_meta.get("diff_sink")
    if recorded and recorded.get("settings", {}).get("enable"):
        holds = len(_events_with(record.events, DIFF_SINK_HOLD_EVENT))
        values["recorded_gate_open"] = recorded.get("gate_open")
        values["recorded_holds"] = holds
        return FeatureCheck(holds > 0, "high", "rule in the recorded run", values)
    if reason is None or not is_level:
        return FeatureCheck(False, "high", "gate closed at the first LOC", values)
    return FeatureCheck(replay.hold_t_s is not None, "medium", "gate open: 10 Hz replay", values)


def _rounded(row: dict[str, Any]) -> dict[str, Any]:
    """Floats rounded for the report; infinities (no sample) become None (valid JSON)."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, float):
            out[key] = round(value, 6) if math.isfinite(value) else None
        else:
            out[key] = value
    return out


# --- case verdict ---


FEATURES = {"SGS": check_sgs, "R4": check_r4, "L1gs": check_l1gs, "DSb75": check_dsb}


def classify(checks: dict[str, FeatureCheck]) -> str:
    fires = [check.fires for check in checks.values()]
    if any(value is True for value in fires):
        return CLASS_RERUN
    if all(value is False for value in fires):
        return CLASS_REUSE
    return CLASS_UNDECIDED


def judge_case(case_dir: Path, settings: FinalSettings) -> dict[str, Any]:
    """Every feature check of one case and its class."""
    record = load_case(case_dir)
    row: dict[str, Any] = {
        "case": f"{case_dir.parent.name}/{case_dir.name}",
        "action": record.result.get("action"),
        "rules_in_record": {
            key: record.controller_meta.get(key) is not None
            for key in ("lift_stroke_guard", "slope_clearance_margin", "loc_revoke", "diff_sink")
        },
    }
    if not record.has_controller:
        reason = "no controller in the loop (open-loop / model test record)"
        checks = {name: FeatureCheck(False, "high", reason) for name in FEATURES}
    else:
        facts = record.facts
        row["loc"] = {
            "times_s": [round(t_s, 2) for t_s in facts.loc_times_s],
            "soil_mode_start_s": facts.soil_mode_start_s,
            "clearance_at_P_mm": None
            if facts.clearance_at_P_m is None
            else round(facts.clearance_at_P_m * 1e3, 2),
            "settle_tilt_deg": None
            if facts.settle_tilt_rad is None
            else round(math.degrees(facts.settle_tilt_rad), 4),
        }
        checks = {name: check(record, settings) for name, check in FEATURES.items()}
    row["checks"] = {name: asdict(check) for name, check in checks.items()}
    row["class"] = classify(checks)
    confidences = [check.confidence for check in checks.values()]
    row["confidence"] = min(confidences, key=("low", "medium", "high").index)
    return row


def validate_replays(case_dirs: list[Path], settings: FinalSettings) -> list[dict[str, Any]]:
    """Replay vs the recorded first L1gs revocation / DSb75 hold of runs that had the rules."""
    rows = []
    for case_dir in case_dirs:
        record = load_case(case_dir)
        holds = _events_with(record.events, DIFF_SINK_HOLD_EVENT)
        revokes = _events_with(record.events, LOC_REVOKE_EVENT)
        dsb = check_dsb(record, settings).values.get("replay") or {}
        l1gs = check_l1gs(record, settings).values.get("replay") or {}
        rows.append(
            {
                "case": f"{case_dir.parent.name}/{case_dir.name}",
                "recorded_first_hold": None if not holds else [round(holds[0][0], 2), holds[0][1]],
                "replay_hold_t_s": dsb.get("hold_t_s"),
                "replay_rate_at_hold_mm_s": None
                if dsb.get("rate_at_hold_m_s") is None
                else round(dsb["rate_at_hold_m_s"] * 1e3, 2),
                "recorded_first_revoke": None
                if not revokes
                else [round(revokes[0][0], 2), revokes[0][1]],
                "replay_revoke": [l1gs.get("fired_t_s"), l1gs.get("kind"), l1gs.get("end_reason")],
            }
        )
    return rows


def run_check(case_rows: list[tuple[str, str, Path]], settings: FinalSettings) -> dict[str, Any]:
    """All cases -> the report dictionary."""
    cases = []
    for label, origin, case_dir in case_rows:
        try:
            row = judge_case(case_dir, settings)
        except (OSError, KeyError, ValueError) as exc:  # keep the other cases, mark this one
            row = {"case": str(case_dir), "class": CLASS_UNDECIDED, "error": repr(exc)}
        cases.append({"label": label, "origin": origin, **row})
    counts = {
        name: sum(row["class"] == name for row in cases)
        for name in (CLASS_REUSE, CLASS_RERUN, CLASS_UNDECIDED)
    }
    return {
        "meta": {
            "spec": "s6_control_spec.md 432.4 E3 (final controller 429.11)",
            "final_controller": "R8 C2 + L1gs + DSb75 + SGS(P36sa, any_loc) + R4c30",
            "tool": "04_scripts/03_control/s9/final_ctrl_offline.py",
            "generated": datetime.now().isoformat(timespec="seconds"),
            "settings": asdict(settings),
            "rule": "(a) = no feature fires; (b) = any fires; undecided = a check cannot tell",
            "not_judged": "05708b2 rules P-S8-28 .. 32 (outside E3)",
        },
        "summary": {
            "counts": counts,
            "rerun_cases": [row["label"] for row in cases if row["class"] == CLASS_RERUN],
            "undecided_cases": [row["label"] for row in cases if row["class"] == CLASS_UNDECIDED],
        },
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "case_dirs", nargs="*", type=Path, help="case folders (default: the E3 list of spec 432)"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="report JSON")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.case_dirs:
        case_rows = [(path.name, "argument", path) for path in args.case_dirs]
    else:
        case_rows = [(label, origin, RESULTS_ROOT / rel) for label, origin, rel in E3_CASES]
    settings = final_settings()
    report = run_check(case_rows, settings)
    report["replay_validation"] = validate_replays(
        [RESULTS_ROOT / rel for rel in VALIDATION_CASES], settings
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    for row in report["cases"]:
        fires = {name: check["fires"] for name, check in (row.get("checks") or {}).items()}
        print(f"{row['class']:9s} {row.get('confidence', '-'):6s} {row['case']} {fires}")
    print(json.dumps(report["summary"]["counts"]))


if __name__ == "__main__":
    main()
